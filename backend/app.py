from flask import Flask, jsonify, render_template, request
import paho.mqtt.client as mqtt
import json
import MySQLdb
import os
import ssl

# ================== Database Connection ==================
def get_db_connection():
    return MySQLdb.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "root"),
        passwd=os.environ.get("DB_PASS", ""),
        db=os.environ.get("DB_NAME", "iot"),
        port=int(os.environ.get("DB_PORT", 3306)),
        charset="utf8mb4"
    )

app = Flask(__name__)

# ================== MQTT Configuration ==================
MQTT_BROKER = "af0dd70346c947d69803d51eb5952f8e.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "Naufal"
MQTT_PASS = "Febrianz123"
MQTT_TOPIC_SENSOR = "hidroponik/sensor"
MQTT_TOPIC_CONTROL = "hidroponik/pompa"

# ================== MQTT Callbacks ==================
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(MQTT_TOPIC_SENSOR)
    else:
        print("Connection failed. Code:", rc)

def on_message(client, userdata, msg):
    print(f"Message on {msg.topic}: {msg.payload.decode()}")
    try:
        data = json.loads(msg.payload.decode())
        suhu = data.get("suhu")
        humidity = data.get("humidity")

        if suhu is not None and humidity is not None:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO data_sensor (suhu, humidity) VALUES (%s, %s)", (suhu, humidity))
            conn.commit()
            cur.close()
            conn.close()
            print("Data saved to database.")
        else:
            print("Incomplete data:", data)
    except Exception as e:
        print("Error processing message:", e)

# ================== MQTT Client Setup ==================
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
mqtt_client.tls_set(tls_version=ssl.PROTOCOL_TLS)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# ================== Flask Routes ==================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/data", methods=["GET"])
def get_data():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, suhu, humidity, timestamp FROM data_sensor ORDER BY id DESC LIMIT 20")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    result = [
        {"id": row[0], "suhu": row[1], "humidity": row[2], "timestamp": str(row[3])}
        for row in rows
    ]
    return jsonify(result)

@app.route("/statistik", methods=["GET"])
def statistik():
    conn = get_db_connection()
    cur = conn.cursor()

    # --- ambil nilai suhu tertinggi, terendah, dan rata-rata ---
    cur.execute("SELECT MAX(suhu), MIN(suhu), AVG(suhu) FROM data_sensor")
    result = cur.fetchone()
    suhumax, suhumin, suhurata = result[0], result[1], round(result[2], 2)

    # --- ambil hanya 2 data unik dengan suhu dan humidity maksimum ---
    cur.execute("""
        SELECT id, suhu, humidity, timestamp
        FROM data_sensor
        WHERE suhu = (SELECT MAX(suhu) FROM data_sensor)
          AND humidity = (SELECT MAX(humidity) FROM data_sensor)
        ORDER BY timestamp ASC
        LIMIT 2
    """)
    rows = cur.fetchall()
    nilai_suhu_max_humid_max = [
        {
            "idx": row[0],
            "suhu": row[1],
            "humid": row[2],
            "timestamp": str(row[3])
        } for row in rows
    ]

    # --- ambil hanya bulan & tahun unik ---
    month_year_set = set()
    for row in rows:
        ts = str(row[3])
        month = ts.split("-")[1]  # ambil bulan
        year = ts.split("-")[0]   # ambil tahun
        month_year_set.add(f"{int(month)}-{year}")

    month_year_max = [{"month_year": val} for val in month_year_set]

    cur.close()
    conn.close()

    # --- hasil akhir ---
    result_json = {
        "suhumax": suhumax,
        "suhumin": suhumin,
        "suhurata": suhurata,
        "nilai_suhu_max_humid_max": nilai_suhu_max_humid_max,
        "month_year_max": month_year_max
    }

    return jsonify(result_json)

@app.route("/control", methods=["POST"])
def control_pump():
    data = request.json
    status = data.get("status")
    if status in ["ON", "OFF"]:
        mqtt_client.publish(MQTT_TOPIC_CONTROL, status)
        print(f"Sent MQTT message: {status}")
        return jsonify({"message": f"Pompa {status}"})
    else:
        return jsonify({"error": "Status tidak valid"}), 400

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
