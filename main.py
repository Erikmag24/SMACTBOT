import logging
import os
import signal
from bot_handlers import bot, monitoring_state, toggle_monitoring_for_user
from monitoring import monitor_variable
import threading

# Definizione della funzione per cancellare i PDF
def delete_pdfs():
    """
    Cancella tutti i file PDF nella cartella corrente.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for filename in os.listdir(current_dir):
        if filename.endswith(".pdf"):
            file_path = os.path.join(current_dir, filename)
            try:
                os.remove(file_path)
                logging.info(f"Cancellato: {file_path}")
            except Exception as e:
                logging.error(f"Errore durante la cancellazione di {file_path}: {e}")

# Gestore del segnale SIGINT
def signal_handler(sig, frame):
    """
    Gestisce il segnale di interruzione (Ctrl+C) per cancellare i PDF e uscire.
    """
    logging.info("Interruzione rilevata. Cancellazione dei PDF...")
    delete_pdfs()
    logging.info("Cancellazione completata. Uscita...")
    exit(0)

def monitoring_with_notification():
    """
    Monitors the variable and notifies users if they have enabled notifications.
    """
    while True:
        variable_value = monitor_variable()  # This function should return the current state of the variable
        logging.info(f"Monitored Variable: {variable_value}")

        # Notify users if they have enabled monitoring
        for user_id, is_monitoring_enabled in monitoring_state.items():
            if is_monitoring_enabled:
                bot.send_message(user_id, f"🔔 Variable Update: {variable_value}")

        time.sleep(5)  # Adjust the monitoring interval as needed

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Registrazione del gestore del segnale
    signal.signal(signal.SIGINT, signal_handler)
    
    # Avvio del thread di monitoraggio
    monitoring_thread = threading.Thread(target=monitoring_with_notification, daemon=True)
    monitoring_thread.start()
    
    # Esecuzione del bot
    try:
        logging.info("Avvio del bot...")
        bot.polling(none_stop=True)
    except Exception as e:
        logging.error(f"Errore durante l'esecuzione del bot: {e}")
    finally:
        # Pulizia finale nel caso il bot si fermi per altri motivi
        delete_pdfs()
