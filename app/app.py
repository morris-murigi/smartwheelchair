from flask import Flask, request, render_template, jsonify
import psycopg2
import os
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import datetime

# Load environment variables (for local testing)
load_dotenv()

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
ALERT_PHONE_NUMBER = os.getenv("ALERT_PHONE_NUMBER")

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None
print("DEBUG: twilio_client initialized =", twilio_client is not None)

# --- Helper: connect to DB ---
def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require" if "localhost" not in DATABASE_URL else "disable")

# --- Helper: send WhatsApp alert ---
def send_whatsapp_alert(message):
    if not all([twilio_client, TWILIO_WHATSAPP_NUMBER, ALERT_PHONE_NUMBER]):
        print("⚠️ Twilio configuration incomplete")
        return
    try:
        twilio_client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,  # e.g., whatsapp:+14155238886
            to=ALERT_PHONE_NUMBER  # e.g., whatsapp:+254792902821
        )
        print("✅ WhatsApp alert sent!")
    except TwilioRestException as e:
        print("❌ Failed to send WhatsApp alert:", e)

# --- Create table if not exists (only once at startup) ---
with get_connection() as conn:
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wheelchair_data (
            id SERIAL PRIMARY KEY,
            pitch FLOAT,
            roll FLOAT,
            gas_level FLOAT,
            uv_index FLOAT,
            alert BOOLEAN DEFAULT FALSE,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

# --- Route: receive data from ESP ---
@app.route("/api/data", methods=["POST"])
def receive_data():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Extract values with defaults/fallbacks for robustness
    pitch = data.get("pitch")
    roll = data.get("roll")
    gas_level = data.get("gasLevel")  # Match ESP32 key
    uv_index = data.get("uvIndex")    # Match ESP32 key
    alert_flag = data.get("alertFlag", False)

    # Validate required fields
    if None in [pitch, roll, gas_level, uv_index]:
        return jsonify({"error": "Missing required sensor data"}), 400

    # Check for critical conditions
    alert_messages = []
    if abs(pitch) > 10 or abs(roll) > 10:
        alert_messages.append(f"High Tilt: Pitch {pitch:.2f}°, Roll {roll:.2f}°")
    if gas_level > 100:
        alert_messages.append(f"High Gas Level: {gas_level:.2f}")
    if uv_index > 3:
        alert_messages.append(f"High UV Index: {uv_index:.2f}")
    if alert_flag:
        alert_messages.append("ESP32 Alert Triggered")

    # Store data in DB
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO wheelchair_data (pitch, roll, gas_level, uv_index, alert)
                VALUES (%s, %s, %s, %s, %s);
            """, (pitch, roll, gas_level, uv_index, alert_flag))
            conn.commit()
    except Exception as e:
        return jsonify({"error": f"Database insertion failed: {str(e)}"}), 500

    # Send WhatsApp alert if critical conditions exist
    if alert_messages:
        message = f"🚨 Wheelchair Alert at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:\n{', '.join(alert_messages)}"
        send_whatsapp_alert(message)

    return jsonify({"message": "Data stored successfully"}), 200

# --- Route: view dashboard ---
@app.route("/")
def dashboard():
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM wheelchair_data ORDER BY timestamp DESC LIMIT 100;")
            rows = cur.fetchall()
    except Exception as e:
        print("❌ Dashboard DB query failed:", e)
        rows = []  # Fallback to empty data
    return render_template("index.html", data=rows)

# --- Route: get latest data as JSON for polling ---
@app.route("/api/latest")
def get_latest_data():
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM wheelchair_data ORDER BY timestamp DESC LIMIT 100;")
            rows = cur.fetchall()
        # Convert rows to list of dicts for JSON
        data = [
            {
                "id": row[0],
                "pitch": row[1],
                "roll": row[2],
                "gas_level": row[3],
                "uv_index": row[4],
                "alert": row[5],
                "timestamp": row[6].isoformat()  # Convert timestamp to string
            }
            for row in rows
        ]
        return jsonify({"data": data})
    except Exception as e:
        print("❌ Latest data query failed:", e)
        return jsonify({"data": []}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)