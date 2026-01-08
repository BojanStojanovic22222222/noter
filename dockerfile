# =========================
# BASE IMAGE
# =========================

# Bruger officiel Python 3.11 image i slim-version
# Slim = mindre image, hurtigere download og mere sikker
FROM python:3.11-slim


# =========================
# SYSTEMAFHÆNGIGHEDER
# =========================

# Opdaterer pakkelisten og installerer nødvendige systempakker
# build-essential:
#   - Kræves for at kompilere Python-pakker med C-udvidelser
# libpq-dev:
#   - PostgreSQL-klientbiblioteker
#   - Nødvendig for psycopg2 (PostgreSQL-driver)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && apt-get clean


# =========================
# WORKING DIRECTORY
# =========================

# Sætter arbejdsbiblioteket inde i containeren
# Alle efterfølgende kommandoer køres herfra
WORKDIR /app


# =========================
# PYTHON DEPENDENCIES
# =========================

# Kopierer requirements.txt først
# (Docker cache-optimering)
COPY requirements.txt .

# Installerer Python-pakker
# --no-cache-dir reducerer image-størrelse
RUN pip install --no-cache-dir -r requirements.txt


# =========================
# APPLIKATIONSKODE
# =========================

# Kopierer resten af projektet ind i containeren
COPY . .


# =========================
# NETVÆRK
# =========================

# Dokumenterer at applikationen lytter på port 5000
EXPOSE 5000


# =========================
# STARTKOMMANDO
# =========================

# Starter Flask-applikationen
CMD ["python", "app.py"]
