from threading import Lock, Thread
import os
import time
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from config import TOKEN, PASSWORD, INITIAL_IMAGE_PATH
from data_handler import fetch_data
from graph_utils import create_graph
from report_generator import generate_daily_report, fixed_metrics
import qrcode
from io import BytesIO

bot = TeleBot(TOKEN)
user_access = {}
user_access_lock = Lock()

# Monitor State Dictionary to Track Users' Monitoring Preferences
monitoring_state = {}

def toggle_monitoring_for_user(user_id):
    """
    Toggles the monitoring state for a given user ID.
    """
    if user_id in monitoring_state:
        monitoring_state[user_id] = not monitoring_state[user_id]
    else:
        monitoring_state[user_id] = True

    return monitoring_state[user_id]

def cleanup_pdf_files():
    """
    Continuously monitors and deletes PDF files related to daily reports
    in the current directory every 30 seconds.
    """
    while True:
        current_directory = os.path.dirname(os.path.abspath(__file__))
        for filename in os.listdir(current_directory):
            if filename.endswith(".pdf") and "daily_reports" in filename:
                file_path = os.path.join(current_directory, filename)
                try:
                    os.remove(file_path)
                    print(f"Deleted: {filename}")
                except Exception as e:
                    print(f"Error deleting {filename}: {e}")
        time.sleep(30)

# Start the cleanup thread
cleanup_thread = Thread(target=cleanup_pdf_files)
cleanup_thread.daemon = True
cleanup_thread.start()

@bot.message_handler(commands=['start'])
def handle_start(message):
    """
    Handles the '/start' command, prompting the user to authenticate with a password.
    """
    with user_access_lock:
        if message.chat.id in user_access:
            del user_access[message.chat.id]
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Access smact.cc", url="https://smact.cc"))
    
    bot.send_message(message.chat.id, "https://smact.cc", reply_markup=markup)
    
    bot.send_chat_action(message.chat.id, 'upload_photo')
    with open(INITIAL_IMAGE_PATH, 'rb') as photo:
        bot.send_photo(message.chat.id, photo=photo, caption="🎉 Welcome! Please enter the password to access the bot's features:")

@bot.message_handler(func=lambda message: message.text and message.chat.id not in user_access)
def handle_password(message):
    """
    Handles user input for password authentication.
    """
    with user_access_lock:
        if message.text == PASSWORD:
            user_access[message.chat.id] = True
            send_welcome(message)
        else:
            bot.send_message(message.chat.id, "🚫 Incorrect password. Please try again.")

def send_welcome(message):
    """
    Sends a welcome message along with a keyboard of options if the user is authenticated.
    """
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton('🔧 Modbus'),
        KeyboardButton('📊 OPCUA'),
        KeyboardButton('🌐 API Request'),
        KeyboardButton('📝 Daily Report'),
        KeyboardButton('🔔 Monitor Variable'),
        KeyboardButton('❓ Help'),
        KeyboardButton('🗑️ Delete Chat'),
        KeyboardButton('🔗 Share Chat')
    )
    with open(INITIAL_IMAGE_PATH, 'rb') as photo:
        bot.send_photo(message.chat.id, photo=photo, caption="✅ Access granted! Choose a category or option:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ['🔧 Modbus', '📊 OPCUA', '🌐 API Request'])
def handle_category(message):
    """
    Presents the user with metric options for the selected category.
    """
    category_mapping = {
        '🔧 Modbus': 'modbus',
        '📊 OPCUA': 'opcua',
        '🌐 API Request': 'api_request'
    }
    category = category_mapping.get(message.text)
    if category:
        markup = InlineKeyboardMarkup(row_width=2)
        for metric in fixed_metrics[category]:
            markup.add(
                InlineKeyboardButton(f"{metric} 📈 (Graph)", callback_data=f'{category}|{metric}|graph'),
                InlineKeyboardButton(f"{metric} 📊 (Data)", callback_data=f'{category}|{metric}|data'),
                InlineKeyboardButton(f"{metric} 📚 (Data & Graph)", callback_data=f'{category}|{metric}|data_graph')
            )
        markup.add(InlineKeyboardButton("🔙 Back", callback_data="back_to_categories"))
        bot.send_message(message.chat.id, "📋 Select a metric to view:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    """
    Handles inline query selections and presents the user with the most recent data point.
    """
    try:
        parts = call.data.split('|')
        if len(parts) != 3:
            bot.send_message(call.message.chat.id, "⚠️ Unexpected data format received. Please try again.")
            return

        category, metric, view_type = parts
        df = fetch_data(category, metric)
        if df.empty:
            bot.send_message(call.message.chat.id, f"❌ No data available for {metric}.")
            return

        # Fetch the most recent data point
        latest_data = df.iloc[-1]  # The last row, assuming the dataframe is time-sorted
        timestamp = latest_data['_time']
        current_value = latest_data['_value']

        if view_type == 'graph':
            img = create_graph(df, f"{metric} Graph", metric, current_value)
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            bot.send_photo(call.message.chat.id, photo=buffer, caption=f"📈 {metric} Graph\nCurrent Value: {current_value}\nTimestamp: {timestamp}")
        
        elif view_type == 'data':
            # Send only the latest data point
            bot.send_message(call.message.chat.id, f"📊 Latest {metric} Data:\nTimestamp: {timestamp}\nValue: {current_value}")
        
        elif view_type == 'data_graph':
            img = create_graph(df, f"{metric} Data & Graph", metric, current_value)
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            bot.send_photo(call.message.chat.id, photo=buffer, caption=f"📚 {metric} Data & Graph\nCurrent Value: {current_value}\nTimestamp: {timestamp}")
            bot.send_message(call.message.chat.id, f"📊 Latest {metric} Data:\nTimestamp: {timestamp}\nValue: {current_value}")
        
        else:
            bot.send_message(call.message.chat.id, f"❓ Unknown view type: {view_type}")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"⚠️ An error occurred: {str(e)}")

@bot.message_handler(func=lambda message: message.text == '🔔 Monitor Variable')
def handle_monitor_toggle(message):
    """
    Toggles monitoring for the user and sends confirmation.
    """
    user_id = message.chat.id
    is_enabled = toggle_monitoring_for_user(user_id)
    status_message = "enabled" if is_enabled else "disabled"
    bot.send_message(user_id, f"🔔 Monitoring has been {status_message}.")

@bot.message_handler(func=lambda message: message.text == '📝 Daily Report')
def handle_daily_report(message):
    """
    Generates and sends the daily report to the user.
    """
    report, pdf_path = generate_daily_report()
    bot.send_message(message.chat.id, report)
    with open(pdf_path, 'rb') as pdf_file:
        bot.send_document(message.chat.id, pdf_file, caption="📊 Ecco il report giornaliero.")
        print(pdf_path)

@bot.message_handler(func=lambda message: message.text == '❓ Help')
def handle_help(message):
    """
    Displays help information for the user.
    """
    help_text = """
    Available Commands:
    
    - /start - Start the bot and request the password.
    - 🔧 Modbus - View available metrics in Modbus.
    - 📊 OPCUA - View available metrics in OPCUA.
    - 🌐 API Request - View available metrics in API requests.
    - 📝 Daily Report - Receive a daily report with statistics.
    - 🔔 Monitor Variable - Toggle alerts for variable updates.
    - 🗑️ Delete Chat - Delete the current chat.
    - 🔗 Share Chat - Get an invite link to share the chat.
    - ❓ Help - Show this help message.

    Note: Some features may still be under development.
    """
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '🗑️ Delete Chat')
def handle_delete_chat(message):
    """
    Deletes all messages in the current chat.
    """
    chat_id = message.chat.id
    try:
        current_message_id = message.message_id
        deleted_count = 0
        failed_count = 0
        for batch in range(10):
            for i in range(current_message_id - (batch * 100), current_message_id - ((batch + 1) * 100), -1):
                try:
                    bot.delete_message(chat_id, i)
                    deleted_count += 1
                except Exception as e:
                    if "message to delete not found" in str(e) or "message can't be deleted" in str(e):
                        failed_count += 1
                        continue
                    else:
                        raise
            if failed_count >= 100:
                break
            failed_count = 0
        with user_access_lock:
            if chat_id in user_access:
                del user_access[chat_id]
        bot.send_message(chat_id, f"🗑️ Deletion complete. {deleted_count} messages were deleted. Please restart the bot with /start.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ An error occurred while deleting the chat: {str(e)}")

@bot.message_handler(func=lambda message: message.text == '🔗 Share Chat')
def handle_share_chat(message):
    """
    Sends a QR code and link for sharing the bot chat.
    """
    invite_link = f"https://t.me/{bot.get_me().username}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(invite_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    bot.send_photo(message.chat.id, photo=buffer, caption=f"📲 Scan this QR code or share this link to invite others to chat with me: {invite_link}")

if __name__ == "__main__":
    bot.polling(none_stop=True)
