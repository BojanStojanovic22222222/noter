# =========================
# TEST KONFIGURATION
# =========================

import os

# Sætter TESTING-miljøvariablen til "1"
# Det gør, at appen bruger SQLite (test.db)
# i stedet for PostgreSQL
os.environ["TESTING"] = "1"


# =========================
# IMPORTS
# =========================

import json                      # Bruges til at sende JSON i requests
from datetime import datetime    # Bruges til tidsstempel
import pytest                    # Test-framework
from app import app, db, Measurement
# Importerer Flask-app, database og modellen der testes


# =========================
# PYTEST FIXTURE
# =========================

@pytest.fixture(autouse=True)
def setup_database():
    """
    Denne fixture køres AUTOMATISK før hver test.
    Den sikrer, at databasen altid er tom og ens
    før hver test køres.
    """

    with app.app_context():
        # Sletter alle tabeller
        db.drop_all()

        # Opretter tabeller igen
        db.create_all()

    # yield betyder:
    # "kør testen nu"
    yield

    # (Her kunne man rydde op efter testen,
    # men det er ikke nødvendigt her)


# =========================
# TEST: POST /api/data
# =========================

def test_api_data_post():
    """
    Tester at API'et kan modtage måledata via POST
    """

    # Opretter test-klient (simulerer en HTTP-klient)
    client = app.test_client()

    # Data der sendes til API'et
    payload = {
        "patient_id": 1,
        "bpm": 75,
        "spo2": 99,
        "temperature": 36.5,
        "timestamp": int(datetime.utcnow().timestamp())
    }

    # Sender POST-request til /api/data
    response = client.post(
        "/api/data",
        data=json.dumps(payload),             # Konverterer dict → JSON
        content_type="application/json"       # Fortæller at det er JSON
    )

    # Tjekker at HTTP-status er 200 (OK)
    assert response.status_code == 200

    # Tjekker at API'et returnerer korrekt JSON-svar
    assert response.json["status"] == "OK"


# =========================
# TEST: GET /api/history
# =========================

def test_api_history_get():
    """
    Tester at /api/history endpointet virker
    og returnerer en liste
    """

    client = app.test_client()

    # Sender GET-request
    response = client.get("/api/history")

    # Skal returnere HTTP 200
    assert response.status_code == 200

    # Svaret skal være en liste (JSON-array)
    assert isinstance(response.json, list)


# =========================
# TEST: DATABASE INDSÆTNING
# =========================

def test_database_insert():
    """
    Tester at Measurement-objekter kan gemmes
    korrekt i databasen
    """

    # app_context er nødvendigt for database-adgang
    with app.app_context():

        # Opretter et Measurement-objekt
        m = Measurement(
            patient_id=1,
            bpm=70,
            spo2=98,
            temperature=36.7
        )

        # Gemmer objektet i databasen
        db.session.add(m)
        db.session.commit()

        # Henter første række fra databasen
        found = Measurement.query.first()

        # Tjekker at der findes en måling
        assert found is not None

        # Tjekker at data er korrekt gemt
        assert found.bpm == 70
