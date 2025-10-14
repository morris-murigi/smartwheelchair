from flask import Flask, request, render_template, jsonify
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables (for local testing)
load_dotenv()

app = Flask(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

# --- Helper: connect to DB ---
def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require" if "localhost" not in DATABASE_URL else "disable")

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

    return jsonify({"message": "Data stored successfully"}), 200

# --- Route: view dashboard ---
@app.route("/")
def dashboard():
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM wheelchair_data ORDER BY timestamp DESC LIMIT 100;")  # Increased limit for graphs
            rows = cur.fetchall()
    except Exception as e:
        print("❌ Dashboard DB query failed:", e)
        rows = []  # Fallback to empty data
    return render_template("index.html", data=rows)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)  # Added debug=True for local dev