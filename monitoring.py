# monitoring.py

import time
from data_handler import fetch_data
from bot_handlers import bot, user_access

def monitor_variable():
    last_value = None
    while True:
        try:
            df = fetch_data("opcua", "udiRiempitrice1Cnt", period='-1m')
            if not df.empty:
                current_value = df['_value'].iloc[-1]
                if last_value is not None and current_value != last_value:
                    notification_message = f"The value of udiRiempitrice1Cnt has changed from {last_value} to {current_value}."
                    for chat_id in user_access.keys():
                        bot.send_message(chat_id, notification_message)
                last_value = current_value
        except Exception as e:
            print(f"Error in monitoring thread: {str(e)}")
        time.sleep(60)
