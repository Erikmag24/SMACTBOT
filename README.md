# Documentazione SmactBot

## Indice
1. [Panoramica](#panoramica)
2. [Requisiti](#requisiti)
3. [Configurazione](#configurazione)
4. [Struttura del Progetto](#struttura-del-progetto)
5. [Descrizione Dettagliata dei File](#descrizione-dettagliata-dei-file)
6. [Funzionalità Principali](#funzionalità-principali)
7. [Comandi del Bot](#comandi-del-bot)
8. [Variabili e Configurazioni](#variabili-e-configurazioni)
9. [Avvio del Progetto](#avvio-del-progetto)
10. [Personalizzazione](#personalizzazione)
11. [Risoluzione dei Problemi](#risoluzione-dei-problemi)
12. [Contribuire](#contribuire)
13. [Licenza](#licenza)

## Panoramica
SmactBot è un bot Telegram avanzato progettato per interagire con varie fonti di dati, generare report e fornire monitoraggio e avvisi in tempo reale. Il bot supporta il recupero di dati da Modbus, OPCUA e richieste API, e può generare report giornalieri in formato PDF. È ideale per ambienti industriali o di monitoraggio che richiedono una supervisione costante e report dettagliati.

## Requisiti
Per eseguire SmactBot, assicurati di avere installato Python 3.7 o versioni successive. Inoltre, è necessario installare i seguenti pacchetti Python. Crea un file `requirements.txt` nella directory principale del progetto con il seguente contenuto:

```
pyTelegramBotAPI==4.12.0
pandas==2.0.3
influxdb-client==1.26.0
plotly==5.12.0
numpy==1.24.4
Pillow==10.0.0
reportlab==3.6.0
qrcode==7.3.1
```

Per installare tutte le dipendenze, esegui il seguente comando nella directory del progetto:

```bash
pip install -r requirements.txt
```

## Configurazione
La configurazione di SmactBot avviene principalmente attraverso il file `config.py`. Crea questo file nella directory principale del progetto con il seguente contenuto:

```python
INFLUXDB_URL = "http://192.168.175.183:8086"
INFLUXDB_TOKEN = "fromfarmtofork"
INFLUXDB_ORG = "smact-org"
INFLUXDB_BUCKET = "smact-bucket"
TOKEN = 'IL_TUO_TOKEN_BOT_TELEGRAM'
PASSWORD = 'la_tua_password'

INITIAL_IMAGE_PATH = "percorso/dell/immagine_iniziale.png"
BACKGROUND_IMAGE_PATH = "percorso/dell/immagine_sfondo.png"
ICON_PATH = "percorso/dell/immagine_icona.png"
```

Assicurati di sostituire 'IL_TUO_TOKEN_BOT_TELEGRAM' con il token effettivo del tuo bot Telegram e 'la_tua_password' con una password sicura per l'autenticazione degli utenti.

## Struttura del Progetto
Il progetto SmactBot è organizzato nei seguenti file Python:

```
SmactBot/
│
├── main.py
├── data_handler.py
├── graph_utils.py
├── report_generator.py
├── monitoring.py
├── config.py
├── requirements.txt
└── README.md
```

## Descrizione Dettagliata dei File

### main.py
Questo è lo script principale che inizializza ed esegue il bot. Include vari gestori per diversi comandi e funzionalità come autenticazione, recupero dati, generazione di grafici, invio di report e monitoraggio delle variabili.

Funzioni principali:
- `handle_start(message)`: Gestisce il comando '/start'.
- `handle_password(message)`: Gestisce l'autenticazione dell'utente.
- `handle_category(message)`: Presenta le opzioni per le categorie di dati.
- `handle_query(call)`: Gestisce le query inline per la visualizzazione dei dati.
- `handle_daily_report(message)`: Genera e invia il report giornaliero.
- `handle_monitor_toggle(message)`: Attiva/disattiva il monitoraggio per l'utente.

```python
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

# Dizionario dello Stato di Monitoraggio per Tracciare le Preferenze di Monitoraggio degli Utenti
monitoring_state = {}

def toggle_monitoring_for_user(user_id):
    """
    Attiva/disattiva lo stato di monitoraggio per un dato ID utente.
    """
    if user_id in monitoring_state:
        monitoring_state[user_id] = not monitoring_state[user_id]
    else:
        monitoring_state[user_id] = True

    return monitoring_state[user_id]

def cleanup_pdf_files():
    """
    Monitora continuamente ed elimina i file PDF relativi ai report giornalieri
    nella directory corrente ogni 30 secondi.
    """
    while True:
        current_directory = os.path.dirname(os.path.abspath(__file__))
        for filename in os.listdir(current_directory):
            if filename.endswith(".pdf") and "daily_reports" in filename:
                file_path = os.path.join(current_directory, filename)
                try:
                    os.remove(file_path)
                    print(f"Eliminato: {filename}")
                except Exception as e:
                    print(f"Errore nell'eliminazione di {filename}: {e}")
        time.sleep(30)

# Avvia il thread di pulizia
cleanup_thread = Thread(target=cleanup_pdf_files)
cleanup_thread.daemon = True
cleanup_thread.start()

@bot.message_handler(commands=['start'])
def handle_start(message):
    """
    Gestisce il comando '/start', invitando l'utente ad autenticarsi con una password.
    """
    with user_access_lock:
        if message.chat.id in user_access:
            del user_access[message.chat.id]
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Accedi a smact.cc", url="https://smact.cc"))
    
    bot.send_message(message.chat.id, "https://smact.cc", reply_markup=markup)
    
    bot.send_chat_action(message.chat.id, 'upload_photo')
    with open(INITIAL_IMAGE_PATH, 'rb') as photo:
        bot.send_photo(message.chat.id, photo=photo, caption="🎉 Benvenuto! Inserisci la password per accedere alle funzionalità del bot:")

@bot.message_handler(func=lambda message: message.text and message.chat.id not in user_access)
def handle_password(message):
    """
    Gestisce l'input dell'utente per l'autenticazione della password.
    """
    with user_access_lock:
        if message.text == PASSWORD:
            user_access[message.chat.id] = True
            send_welcome(message)
        else:
            bot.send_message(message.chat.id, "🚫 Password errata. Riprova.")

def send_welcome(message):
    """
    Invia un messaggio di benvenuto insieme a una tastiera di opzioni se l'utente è autenticato.
    """
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        KeyboardButton('🔧 Modbus'),
        KeyboardButton('📊 OPCUA'),
        KeyboardButton('🌐 Richiesta API'),
        KeyboardButton('📝 Report Giornaliero'),
        KeyboardButton('🔔 Monitora Variabile'),
        KeyboardButton('❓ Aiuto'),
        KeyboardButton('🗑️ Elimina Chat'),
        KeyboardButton('🔗 Condividi Chat')
    )
    with open(INITIAL_IMAGE_PATH, 'rb') as photo:
        bot.send_photo(message.chat.id, photo=photo, caption="✅ Accesso concesso! Scegli una categoria o un'opzione:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ['🔧 Modbus', '📊 OPCUA', '🌐 Richiesta API'])
def handle_category(message):
    """
    Presenta all'utente le opzioni metriche per la categoria selezionata.
    """
    category_mapping = {
        '🔧 Modbus': 'modbus',
        '📊 OPCUA': 'opcua',
        '🌐 Richiesta API': 'api_request'
    }
    category = category_mapping.get(message.text)
    if category:
        markup = InlineKeyboardMarkup(row_width=2)
        for metric in fixed_metrics[category]:
            markup.add(
                InlineKeyboardButton(f"{metric} 📈 (Grafico)", callback_data=f'{category}|{metric}|graph'),
                InlineKeyboardButton(f"{metric} 📊 (Dati)", callback_data=f'{category}|{metric}|data'),
                InlineKeyboardButton(f"{metric} 📚 (Dati & Grafico)", callback_data=f'{category}|{metric}|data_graph')
            )
        markup.add(InlineKeyboardButton("🔙 Indietro", callback_data="back_to_categories"))
        bot.send_message(message.chat.id, "📋 Seleziona una metrica da visualizzare:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    """
    Gestisce le selezioni di query inline e presenta all'utente il punto dati più recente.
    """
    try:
        parts = call.data.split('|')
        if len(parts) != 3:
            bot.send_message(call.message.chat.id, "⚠️ Formato dati inatteso ricevuto. Riprova.")
            return

        category, metric, view_type = parts
        df = fetch_data(category, metric)
        if df.empty:
            bot.send_message(call.message.chat.id, f"❌ Nessun dato disponibile per {metric}.")
            return

        # Recupera il punto dati più recente
        latest_data = df.iloc[-1]  # L'ultima riga, assumendo che il dataframe sia ordinato per tempo
        timestamp = latest_data['_time']
        current_value = latest_data['_value']

        if view_type == 'graph':
            img = create_graph(df, f"Grafico {metric}", metric, current_value)
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            bot.send_photo(call.message.chat.id, photo=buffer, caption=f"📈 Grafico {metric}\nValore Attuale: {current_value}\nTimestamp: {timestamp}")
        
        elif view_type == 'data':
            # Invia solo il punto dati più recente
            bot.send_message(call.message.chat.id, f"📊 Dati più recenti di {metric}:\nTimestamp: {timestamp}\nValore: {current_value}")
        
        elif view_type == 'data_graph':
            img = create_graph(df, f"Dati & Grafico {metric}", metric, current_value)
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            bot.send_photo(call.message.chat.id, photo=buffer, caption=f"📚 Dati & Grafico {metric}\nValore Attuale: {current_value}\nTimestamp: {timestamp}")
            bot.send_message(call.message.chat.id, f"📊 Dati più recenti di {metric}:\nTimestamp: {timestamp}\nValore: {current_value}")
        
        else:
            bot.send_message(call.message.chat.id, f"❓ Tipo di visualizzazione sconosciuto: {view_type}")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"⚠️ Si è verificato un errore: {str(e)}")

@bot.message_handler(func=lambda message: message.text == '🔔 Monitora Variabile')
def handle_monitor_toggle(message):
    """
    Attiva/disattiva il monitoraggio per l'utente e invia una conferma.
    """
    user_id = message.chat.id
    is_enabled = toggle_monitoring_for_user(user_id)
    status_message = "attivato" if is_enabled else "disattivato"
    bot.send_message(user_id, f"🔔 Il monitoraggio è stato {status_message}.")

@bot.message_handler(func=lambda message: message.text == '📝 Report Giornaliero')
def handle_daily_report(message):
    """
    Genera e invia il report giornaliero all'utente.
    """
    report, pdf_path = generate_daily_report()
    bot.send_message(message.chat.id, report)
    with open(pdf_path, 'rb') as pdf_file:
        bot.send_document(message.chat.id, pdf_file, caption="📊 Ecco il report giornaliero.")
        print(pdf_path)

@bot.message_handler(func=lambda message: message.text == '❓ Aiuto')
def handle_help(message):
    """
    Visualizza le informazioni di aiuto per l'utente.
    """
    help_text = """
    Comandi Disponibili:
    
    - /start - Avvia il bot e richiedi la password.
    - 🔧 Modbus - Visualizza le metriche disponibili in Modbus.
    - 📊 OPCUA - Visualizza le metriche disponibili in OPCUA.
    - 🌐 Richiesta API - Visualizza le metriche disponibili nelle richieste API.
    - 📝 Report Giornaliero - Ricevi un report giornaliero con statistiche.
    - 🔔 Monitora Variabile - Attiva/disattiva gli avvisi per gli aggiornamenti delle variabili.
    - 🗑️ Elimina Chat - Elimina la chat corrente.
    - 🔗 Condividi Chat - Ottieni un link di invito per condividere la chat.
    - ❓ Aiuto - Mostra questo messaggio di aiuto.

    Nota: Alcune funzionalità potrebbero essere ancora in fase di sviluppo.
    """
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '🗑️ Elimina Chat')
def handle_delete_chat(message):
    """
    Elimina tutti i messaggi nella chat corrente.
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
        bot.send_message(chat_id, f"🗑️ Eliminazione completata. {deleted_count} messaggi sono stati eliminati. Riavvia il bot con /start.")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Si è verificato un errore durante l'eliminazione della chat: {str(e)}")

@bot.message_handler(func=lambda message: message.text == '🔗 Condividi Chat')
def handle_share_chat(message):
    """
    Invia un codice QR e un link per condividere la chat del bot.
    """
    invite_link = f"https://t.me/{bot.get_me().username}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(invite_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    bot.send_photo(message.chat.id, photo=buffer, caption=f"📲 Scansiona questo codice QR o condividi questo link per invitare altri a chattare con me: {invite_link}")

if __name__ == "__main__":
    bot.polling(none_stop=True)
```

### data_handler.py
Questo script gestisce il recupero dei dati da InfluxDB. Utilizza la libreria influxdb-client per interrogare i dati in base alla categoria e alla metrica specificate.

Funzioni principali:
- `fetch_data(category, metric, period='-1h')`: Recupera i dati da InfluxDB in base alla categoria e alla metrica specificate.

```python
from influxdb_client import InfluxDBClient
from config import INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET
import pandas as pd

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()

def fetch_data(category, metric, period='-1h'):
    """
    Recupera i dati da InfluxDB in base alla categoria e alla metrica.
    """
    query = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: {period})
      |> filter(fn: (r) => r["_measurement"] == "{category}" and r["_field"] == "{metric}")
      |> sort(columns: ["_time"], desc: true)
    """
    tables = query_api.query(query)
    records = []
    for table in tables:
        for record in table.records:
            records.append((record.get_time(), record.get_value()))

    if records:
        df = pd.DataFrame(records, columns=['_time', '_value'])
        return df
    else:
        return pd.DataFrame(columns=['_time', '_value'])
```

### graph_utils.py
Questo script crea grafici dai dati utilizzando la libreria plotly.

Funzioni principali:
- `create_graph(dataframe, title, metric, current_value)`: Crea un grafico utilizzando Plotly e lo restituisce come immagine.

```python
import plotly.graph_objects as go
from PIL import Image
import io

def create_graph(dataframe, title, metric, current_value):
    """
    Crea un grafico utilizzando Plotly e lo restituisce come immagine.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dataframe['_time'], y=dataframe['_value'], mode='lines', name=metric))
    fig.update_layout(title=title, xaxis_title='Tempo', yaxis_title='Valore')

    buffer = io.BytesIO()
    fig.write_image(buffer, format='png')
    buffer.seek(0)
    img = Image.open(buffer)
    return img
```
### report_generator.py
Questo script genera report giornalieri in formato PDF utilizzando la libreria reportlab.

Funzioni principali:
- `generate_daily_report()`: Genera un report giornaliero PDF e restituisce il contenuto del report e il percorso del file.

```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from config import BACKGROUND_IMAGE_PATH, ICON_PATH
from datetime import datetime
import os

fixed_metrics = {
    'modbus': ['metrica1', 'metrica2'],
    'opcua': ['udiRiempitrice1Cnt', 'metrica4'],
    'api_request': ['metrica5', 'metrica6']
}

def generate_daily_report():
    """
    Genera un report giornaliero PDF e restituisce il contenuto del report e il percorso del file.
    """
    report_content = "Report Giornaliero\n\n"
    for category, metrics in fixed_metrics.items():
        report_content += f"Metriche {category}:\n"
        for metric in metrics:
            report_content += f"- {metric}\n"
        report_content += "\n"
    
    report_path = f"report_giornaliero_{datetime.now().strftime('%Y%m%d')}.pdf"
    c = canvas.Canvas(report_path, pagesize=letter)
    width, height = letter
    
    c.drawImage(BACKGROUND_IMAGE_PATH, 0, 0, width=width, height=height)
    c.drawImage(ICON_PATH, width - 50, height - 50, width=40, height=40)
    
    c.setFont("Helvetica", 12)
    textobject = c.beginText(50, height - 100)
    for line in report_content.split("\n"):
        textobject.textLine(line)
    c.drawText(textobject)
    
    c.showPage()
    c.save()
    
    return report_content, report_path
```

### monitoring.py
Questo script contiene una funzione di monitoraggio che controlla continuamente le modifiche in una variabile specifica e invia notifiche agli utenti.

Funzioni principali:
- `monitor_variable()`: Monitora continuamente una variabile specifica e invia notifiche in caso di cambiamenti.

```python
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
                    notification_message = f"Il valore di udiRiempitrice1Cnt è cambiato da {last_value} a {current_value}."
                    for chat_id in user_access.keys():
                        bot.send_message(chat_id, notification_message)
                last_value = current_value
        except Exception as e:
            print(f"Errore nel thread di monitoraggio: {str(e)}")
        time.sleep(60)
```

### Autenticazione
Il bot richiede agli utenti di autenticarsi con una password prima di accedere alle funzionalità. Questo è gestito nella funzione `handle_password` in `bot_handler.py`.

### Recupero Dati
I dati vengono recuperati da InfluxDB utilizzando la funzione `fetch_data` in `data_handler.py`. Questa funzione supporta diverse categorie di dati (Modbus, OPCUA, API) e metriche specifiche.

### Generazione di Grafici
I grafici vengono creati utilizzando la funzione `create_graph` in `graph_utils.py`. Questa funzione utilizza Plotly per generare grafici interattivi che vengono poi convertiti in immagini.

### Report Giornalieri
I report giornalieri vengono generati utilizzando la funzione `generate_daily_report` in `report_generator.py`. Questa funzione crea un PDF con un riepilogo delle metriche e lo salva localmente.

### Monitoraggio in Tempo Reale
Il monitoraggio in tempo reale è gestito dalla funzione `monitor_variable` in `monitoring.py`. Questa funzione controlla continuamente le modifiche in una variabile specifica e invia notifiche agli utenti quando vengono rilevate variazioni.

## Comandi del Bot
Il bot supporta i seguenti comandi:

- `/start`: Avvia il bot e richiede la password.
- `🔧 Modbus`: Visualizza le metriche disponibili in Modbus.
- `📊 OPCUA`: Visualizza le metriche disponibili in OPCUA.
- `🌐 Richiesta API`: Visualizza le metriche disponibili nelle richieste API.
- `📝 Report Giornaliero`: Genera e invia un report giornaliero.
- `🔔 Monitora Variabile`: Attiva/disattiva il monitoraggio delle variabili.
- `❓ Aiuto`: Mostra un messaggio di aiuto con tutti i comandi disponibili.
- `🗑️ Elimina Chat`: Elimina tutti i messaggi nella chat corrente.
- `🔗 Condividi Chat`: Genera un codice QR e un link per invitare altri utenti.

## Variabili e Configurazioni
Le principali variabili di configurazione sono definite nel file `config.py`:

- `INFLUXDB_URL`: L'URL del server InfluxDB.
- `INFLUXDB_TOKEN`: Il token di autenticazione per InfluxDB.
- `INFLUXDB_ORG`: Il nome dell'organizzazione in InfluxDB.
- `INFLUXDB_BUCKET`: Il nome del bucket in InfluxDB dove sono memorizzati i dati.
- `TOKEN`: Il token del bot Telegram.
- `PASSWORD`: La password per l'autenticazione degli utenti.
- `INITIAL_IMAGE_PATH`: Il percorso dell'immagine iniziale mostrata all'avvio del bot.
- `BACKGROUND_IMAGE_PATH`: Il percorso dell'immagine di sfondo utilizzata nei report PDF.
- `ICON_PATH`: Il percorso dell'icona utilizzata nei report PDF.

Altre variabili importanti:
- In `report_generator.py`, il dizionario `fixed_metrics` definisce le metriche disponibili per ogni categoria di dati.

## Avvio del Progetto
Per avviare SmactBot, segui questi passaggi:

1. Assicurati di aver installato tutte le dipendenze elencate in `requirements.txt`.
2. Configura correttamente il file `config.py` con le tue impostazioni specifiche.
3. Posizionati nella directory principale del progetto.
4. Esegui il seguente comando:

```bash
python main.py
```

Il bot si avvierà e attenderà le interazioni dell'utente. Puoi interagire con il bot utilizzando i comandi e le opzioni fornite nell'interfaccia Telegram.

## Personalizzazione
Puoi personalizzare il comportamento del bot modificando le seguenti parti:

- Aggiungi nuove metriche nel dizionario `fixed_metrics` in `report_generator.py`.
- Modifica la frequenza di monitoraggio cambiando il valore di `time.sleep()` in `monitoring.py`.
- Personalizza il layout del report PDF modificando la funzione `generate_daily_report` in `report_generator.py`.
- Aggiungi nuovi comandi o funzionalità modificando `main.py` e aggiungendo nuovi gestori di messaggi.

## Risoluzione dei Problemi
Se incontri problemi durante l'esecuzione del bot:

1. Verifica che tutte le dipendenze siano installate correttamente eseguendo `pip list` e confrontando con `requirements.txt`.
2. Controlla che il token del bot Telegram in `config.py` sia valido provando a crearne uno nuovo con BotFather su Telegram.
3. Assicurati che l'URL e le credenziali di InfluxDB in `config.py` siano corretti tentando una connessione manuale al database.
4. Controlla i log per eventuali errori specifici. Puoi aggiungere più stampe di debug nei vari file per tracciare il flusso di esecuzione.
5. Se il monitoraggio non funziona, verifica che la funzione `monitor_variable` in `monitoring.py` sia chiamata correttamente e che la connessione a InfluxDB sia stabile.
6. Per problemi con la generazione di grafici, assicurati che Plotly sia installato correttamente e che i dati recuperati da InfluxDB siano nel formato atteso.

## Contribuire
Se desideri contribuire al progetto SmactBot, segui questi passaggi:

1. Forkare il repository su GitHub.
2. Clonare il fork sul tuo computer locale.
3. Creare un nuovo branch per le tue modifiche:
   ```
   git checkout -b feature/nuova-funzionalita
   ```
4. Apportare le modifiche e committarle:
   ```
   git commit -am 'Aggiunta nuova funzionalità'
   ```
5. Pushare il branch sul tuo fork:
   ```
   git push origin feature/nuova-funzionalita
   ```
6. Creare una Pull Request dal tuo fork al repository originale su GitHub.

Assicurati di seguire le best practices di codifica e di documentare adeguatamente qualsiasi nuova funzionalità o modifica.

## Licenza
Questo progetto è distribuito sotto la licenza MIT. Vedi il file `LICENSE` nella directory principale del progetto per ulteriori dettagli.

La licenza MIT permette l'uso, la copia, la modifica, la fusione, la pubblicazione, la distribuzione, la sublicenza e/o la vendita di copie del software, a condizione che l'avviso di copyright e questa nota di permesso siano inclusi in tutte le copie o parti sostanziali del software.











