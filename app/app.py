from flask import Flask, request, render_template, jsonify
import psycopg2
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText

# Load environment variables (for local testing)
load_dotenv()

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
ALERT_EMAIL = os.getenv("ALERT_EMAIL")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# --- Helper: connect to DB ---
def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

# --- Helper: send email alert ---
def send_alert_email(message):
    if not ALERT_EMAIL:
        print("⚠️ ALERT_EMAIL not set")
        return
    try:
        msg = MIMEText(message)
        msg["Subject"] = "Smart Wheelchair Alert 🚨"
        msg["From"] = SENDER_EMAIL
        msg["To"] = ALERT_EMAIL

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print("✅ Alert email sent!")
    except Exception as e:
        print("❌ Failed to send email:", e)

# --- Create table if not exists ---
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
        return jsonify({"error": "No data"}), 400

    # Match your ESP32 JSON keys
    pitch = data.get("pitch")
    roll = data.get("roll")
    gasLevel = data.get("gasLevel")
    uvIndex = data.get("uvIndex")
    alertFlag = data.get("alertFlag", False)

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

        cur.execute("""
            INSERT INTO wheelchair_data (pitch, roll, gas_level, uv_index, alert)
            VALUES (%s, %s, %s, %s, %s);
        """, (pitch, roll, gasLevel, uvIndex, alertFlag))
        conn.commit()

    if alertFlag:
        send_alert_email(f"⚠️ Alert Triggered!\nPitch: {pitch}, Roll: {roll}, Gas: {gasLevel}, UV: {uvIndex}")

    return jsonify({"message": "Data stored"}), 200

# --- Route: view dashboard ---
@app.route("/")
def dashboard():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM wheelchair_data ORDER BY timestamp DESC LIMIT 10;")
        rows = cur.fetchall()
    return render_template("index.html", data=rows)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
