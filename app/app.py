from flask import Flask, request, render_template, jsonify
import psycopg2
import os
from dotenv import load_dotenv
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
ALERT_PHONE_NUMBER = os.getenv("ALERT_PHONE_NUMBER")

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None

# Thresholds (universal with ESP32)
PITCH_THRESHOLD = 45.0  # degrees
ROLL_THRESHOLD = 45.0   # degrees
AIR_QUALITY_THRESHOLD = 80.0  # % (poor air quality)
UV_INDEX_THRESHOLD = 3.0      # UV index

def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require" if "localhost" not in DATABASE_URL else "disable")

def send_whatsapp_alert(message):
    if not all([twilio_client, TWILIO_WHATSAPP_NUMBER, ALERT_PHONE_NUMBER]):
        print("⚠️ Twilio configuration incomplete")
        return
    try:
        twilio_client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=ALERT_PHONE_NUMBER
        )
        print("✅ WhatsApp alert sent!")
    except TwilioRestException as e:
        print("❌ Failed to send WhatsApp alert:", e)

@app.route('/api/data', methods=['POST'])
def data():
    try:
        data = request.get_json()
        pitch = float(data.get('pitch', 0))
        roll = float(data.get('roll', 0))
        air_quality = float(data.get('airQuality', 0))
        uv_index = float(data.get('uvIndex', 0))
        alert_flag = data.get('alertFlag', False)

        # Alert logic (same as ESP32)
        message = []
        if abs(pitch) > PITCH_THRESHOLD:
            message.append(f"High Tilt: Pitch {pitch:.2f}°")
        if abs(roll) > ROLL_THRESHOLD:
            message.append(f"Roll {roll:.2f}°")
        if air_quality > AIR_QUALITY_THRESHOLD:
            message.append(f"Poor Air Quality: {air_quality:.2f}%")
        if uv_index > UV_INDEX_THRESHOLD:
            message.append(f"High UV Index: {uv_index:.2f}")
        if alert_flag:
            message.append("ESP32 Alert Triggered")

        if message:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Only for WhatsApp
            alert_message = f"🚨 Wheelchair Alert at {timestamp} EAT: {', '.join(message)}"
            send_whatsapp_alert(alert_message)

        # Insert into database - let timestamp auto-generate
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO wheelchair_data (pitch, roll, air_quality, uv_index, alert_flag)
            VALUES (%s, %s, %s, %s, %s)
        """, (pitch, roll, air_quality, uv_index, alert_flag))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": "Data received and processed"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/latest', methods=['GET'])
def latest():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM wheelchair_data ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return jsonify({
                "id": row[0],
                "pitch": row[1],
                "roll": row[2],
                "air_quality": row[3],
                "uv_index": row[4],
                "alert_flag": row[5],
                "timestamp": row[6]
            }), 200
        return jsonify({"status": "no data"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)