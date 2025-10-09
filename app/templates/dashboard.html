from flask import Flask, request, jsonify, render_template
import psycopg2
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Database connection
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# Create table if not exists
cur.execute("""
CREATE TABLE IF NOT EXISTS wheelchair_data (
    id SERIAL PRIMARY KEY,
    angle_x FLOAT,
    angle_y FLOAT,
    uvi FLOAT,
    smoke FLOAT,
    alert_flag BOOLEAN,
    alert_email TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")
conn.commit()

# Keep track of last values (for change detection)
last_values = {"angle_x": None, "angle_y": None, "uvi": None, "smoke": None}

def send_email_alert(to_email, subject, body):
    """Send alert email using SMTP"""
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = os.getenv("EMAIL_USER")
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
            server.send_message(msg)
        print("✅ Email alert sent.")
    except Exception as e:
        print("❌ Failed to send email:", e)

@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/data", methods=["POST"])
def receive_data():
    """Receive ESP32 data only if values change"""
    data = request.get_json()

    angle_x = data.get("angle_x")
    angle_y = data.get("angle_y")
    uvi = data.get("uvi")
    smoke = data.get("smoke")
    alert_email = data.get("alert_email")

    global last_values
    changed = any([
        last_values["angle_x"] != angle_x,
        last_values["angle_y"] != angle_y,
        last_values["uvi"] != uvi,
        last_values["smoke"] != smoke
    ])

    if changed:
        last_values.update({
            "angle_x": angle_x,
            "angle_y": angle_y,
            "uvi": uvi,
            "smoke": smoke
        })

        # Alert condition example
        alert_flag = uvi > 8 or smoke > 500 or abs(angle_x) > 45

        cur.execute("""
        INSERT INTO wheelchair_data (angle_x, angle_y, uvi, smoke, alert_flag, alert_email)
        VALUES (%s, %s, %s, %s, %s, %s)
        """, (angle_x, angle_y, uvi, smoke, alert_flag, alert_email))
        conn.commit()

        if alert_flag and alert_email:
            send_email_alert(
                alert_email,
                "🚨 Wheelchair Alert",
                f"Abnormal condition detected:\nAngle X: {angle_x}\nAngle Y: {angle_y}\nUVI: {uvi}\nSmoke: {smoke}"
            )

        return jsonify({"message": "Data updated and alert processed"}), 201
    else:
        return jsonify({"message": "No change detected"}), 200

@app.route("/query", methods=["GET"])
def query_data():
    """Return recent data for dashboard"""
    cur.execute("SELECT * FROM wheelchair_data ORDER BY id DESC LIMIT 10;")
    rows = cur.fetchall()
    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "angle_x": r[1],
            "angle_y": r[2],
            "uvi": r[3],
            "smoke": r[4],
            "alert_flag": r[5],
            "alert_email": r[6],
            "timestamp": r[7].strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
