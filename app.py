# =========================
# IMPORTS
# =========================

import os                 # Bruges til at læse miljøvariabler (fx API_TOKEN, TESTING)
import re                 # Bruges til regulære udtryk (validering af tal)
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from dotenv import load_dotenv  # Indlæser .env-fil med hemmelige værdier


# =========================
# MILJØVARIABLER
# =========================

# Indlæser miljøvariabler fra .env-filen
load_dotenv()

# API-token bruges til at sikre API'et (kun autoriserede enheder må sende data)
API_TOKEN = os.getenv("API_TOKEN")


# =========================
# FLASK APP
# =========================

# Opretter Flask-applikationen
app = Flask(__name__)


# =========================
# REGEX VALIDERING
# =========================

# Regex der kun tillader tal, evt. med decimal
# Eksempler: 123, 98.6, 37.5
number_pattern = re.compile(r"^\d+(\.\d+)?$")


# =========================
# DATABASE KONFIGURATION
# =========================

# Hvis vi er i test-mode (fx til eksamen eller udvikling)
if os.getenv("TESTING") == "1":
    # SQLite bruges ofte til test
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
else:
    # PostgreSQL bruges i produktion (fx Docker)
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://iot_user:iot_password@db:5432/iot_db"

# Deaktiverer unødvendige ændrings-notifikationer
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialiserer SQLAlchemy (ORM)
db = SQLAlchemy(app)


# =========================
# DATABASE MODEL
# =========================

class Measurement(db.Model):
    """
    Denne klasse repræsenterer én måling i databasen.
    SQLAlchemy laver automatisk en tabel ud fra klassen.
    """

    id = db.Column(db.Integer, primary_key=True)          # Unikt ID
    patient_id = db.Column(db.Integer, nullable=False)   # Patientens ID
    bpm = db.Column(db.Integer, nullable=False)           # Puls (beats per minute)
    spo2 = db.Column(db.Integer, nullable=False)          # Iltmætning i %
    temperature = db.Column(db.Float, nullable=False)     # Kropstemperatur
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Tidspunkt

    def to_dict(self):
        """
        Konverterer objektet til et dictionary
        så det nemt kan returneres som JSON
        """
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "bpm": self.bpm,
            "spo2": self.spo2,
            "temperature": self.temperature,
            "timestamp": self.timestamp.isoformat()
        }


# =========================
# STATUS-EVALUERING
# =========================

def evaluate_status(m):
    """
    Vurderer patientens status ud fra seneste måling
    Returnerer:
    - status (Normal / Advarsel / Kritisk)
    - liste med problemer
    """

    status = "Normal"
    issues = []

    # SpO2 vurdering
    if m.spo2 < 92:
        status = "Kritisk"
        issues.append("Meget lav iltmætning")
    elif m.spo2 < 95:
        status = "Advarsel"
        issues.append("Lav SpO₂")

    # Puls vurdering
    if m.bpm < 50 or m.bpm > 120:
        status = "Kritisk"
        issues.append("Unormal puls")

    # Temperatur vurdering
    if m.temperature > 38.0:
        if status != "Kritisk":
            status = "Advarsel"
        issues.append("Feber")

    return status, issues


# =========================
# ROUTES / ENDPOINTS
# =========================

@app.route("/")
def index():
    """
    Forside – viser index.html
    """
    return render_template("index.html")


# =========================
# MODTAG DATA (POST)
# =========================

@app.route("/api/data", methods=["POST"])
def receive_data():
    """
    Modtager måledata fra IoT-enhed
    Kræver Bearer Token
    """

    # Tjek Authorization-header
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Missing bearer token"}), 401

    # Tjek om token er korrekt
    if auth.replace("Bearer ", "") != API_TOKEN:
        return jsonify({"error": "Invalid token"}), 403

    # Hent JSON-data
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON"}), 400

    # Valider BPM
    if not number_pattern.match(str(data.get("bpm", ""))):
        return jsonify({"error": "Invalid BPM"}), 400

    # Valider SpO2
    if not number_pattern.match(str(data.get("spo2", ""))):
        return jsonify({"error": "Invalid SpO2"}), 400

    # Valider temperatur
    if not number_pattern.match(str(data.get("temperature", ""))):
        return jsonify({"error": "Invalid temperature"}), 400

    # Opret Measurement-objekt
    m = Measurement(
        patient_id=data.get("patient_id", 1),  # Default patient ID
        bpm=int(data["bpm"]),
        spo2=int(data["spo2"]),
        temperature=float(data["temperature"]),
        timestamp=datetime.utcnow()
    )

    # Gem i databasen
    db.session.add(m)
    db.session.commit()

    return jsonify({"status": "OK"}), 200


# =========================
# HISTORIK (GET)
# =========================

@app.route("/api/history")
def history():
    """
    Returnerer historiske målinger
    Parametre:
    - limit: antal målinger
    - minutes: filtrér på tid
    """

    limit = int(request.args.get("limit", 100))
    minutes = request.args.get("minutes")

    query = Measurement.query.order_by(Measurement.timestamp.desc())

    if minutes:
        since = datetime.utcnow() - timedelta(minutes=int(minutes))
        query = query.filter(Measurement.timestamp >= since)

    data = list(reversed(query.limit(limit).all()))
    return jsonify([m.to_dict() for m in data])


# =========================
# STATISTIK (GET)
# =========================

@app.route("/api/stats")
def stats():
    """
    Returnerer:
    - Seneste måling
    - Gennemsnit over 10 minutter
    - Patientstatus
    """

    last = Measurement.query.order_by(Measurement.timestamp.desc()).first()
    if not last:
        return jsonify({"error": "no data"}), 404

    last_10 = Measurement.query.filter(
        Measurement.timestamp >= datetime.utcnow() - timedelta(minutes=10)
    ).all()

    if last_10:
        avg_bpm = sum(m.bpm for m in last_10) / len(last_10)
        avg_spo2 = sum(m.spo2 for m in last_10) / len(last_10)
        avg_temp = sum(m.temperature for m in last_10) / len(last_10)
    else:
        avg_bpm = avg_spo2 = avg_temp = 0

    status, issues = evaluate_status(last)

    return jsonify({
        "last_measurement": last.to_dict(),
        "avg_bpm_10min": avg_bpm,
        "avg_spo2_10min": avg_spo2,
        "avg_temp_10min": avg_temp,
        "status": status,
        "issues": issues
    })


# =========================
# START PROGRAMMET
# =========================

if __name__ == "__main__":
    # Opretter database-tabeller hvis de ikke findes
    with app.app_context():
        db.create_all()

    # Starter Flask-serveren
    app.run(host="0.0.0.0", port=5000)
