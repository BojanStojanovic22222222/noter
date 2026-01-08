# =========================
# IMPORTS (MICROPYTHON)
# =========================

from machine import I2C, Pin, PWM
# I2C: kommunikation med sensorer (MAX30100)
# Pin: styring af GPIO-pins
# PWM: bruges til servo og vibrationsmotor

import time                   # Timing, delays og timestamps
import dht                    # DHT11 temperatur-sensor
import urequests              # HTTP requests (MicroPython version)
from max30100 import MAX30100 # Puls- og SpO2-sensor
import neopixel               # RGB LED-ring (NeoPixel)


# =========================
# SERVER & API KONFIGURATION
# =========================

SERVER_URL = "http://192.168.0.12:5000/api/data"
# Flask backend endpoint der modtager målinger

API_TOKEN = "Glostrup"
# Bearer token til API-sikkerhed


# =========================
# TEMPERATUR SENSOR (DHT11)
# =========================

# DHT11 er forbundet til GPIO 4
dht_sensor = dht.DHT11(Pin(4))

def read_temperature():
    """
    Læser temperatur fra DHT11.
    Returnerer None hvis målingen fejler.
    """
    try:
        dht_sensor.measure()
        return dht_sensor.temperature()
    except:
        return None


# =========================
# MAX30100 (PULS & SpO2)
# =========================

# I2C-bus (ESP32 standard)
i2c = I2C(0, scl=Pin(22), sda=Pin(21))

# Opretter MAX30100 sensor-objekt
sensor = MAX30100(i2c)


# =========================
# NEOPIXEL LED-RING
# =========================

NUM_PIXELS = 12
np = neopixel.NeoPixel(Pin(15), NUM_PIXELS)

def ring_color(r, g, b):
    """
    Sætter farve på hele LED-ringen
    """
    for i in range(NUM_PIXELS):
        np[i] = (r, g, b)
    np.write()


# =========================
# SERVO (VISUEL ALARM)
# =========================

# Servo tilsluttet GPIO 18 (50 Hz standard)
servo = PWM(Pin(18), freq=50)

def angle_to_duty(angle):
    """
    Konverterer vinkel (0–180°)
    til PWM duty cycle
    """
    min_duty = 26
    max_duty = 128
    return int(min_duty + (max_duty - min_duty) * (angle / 180))

def servo_set_angle(angle):
    servo.duty(angle_to_duty(angle))

def servo_alarm():
    """
    Bevæger servoen hurtigt
    som visuel alarm
    """
    servo_set_angle(40)
    time.sleep_ms(120)
    servo_set_angle(140)
    time.sleep_ms(120)
    servo_set_angle(90)


# =========================
# VIBRATIONSMOTOR (HAPTISK ALARM)
# =========================

ENA = PWM(Pin(23), freq=2000)
IN2 = Pin(19, Pin.OUT)

def vib_pulse(duration=200):
    """
    Aktiverer vibrationsmotor i pulser
    """
    ENA.duty(800)
    IN2.value(0)
    time.sleep_ms(duration)
    ENA.duty(0)
    time.sleep_ms(80)
    IN2.value(1)
    ENA.duty(800)
    time.sleep_ms(duration)
    ENA.duty(0)
    IN2.value(0)


# =========================
# DATA-SANITERING
# =========================

def sanitize_values(bpm, spo2, temp):
    """
    Sikrer realistiske måleværdier
    hvis sensorer fejler
    """
    if bpm is None or bpm <= 30 or bpm > 250:
        bpm = 70
    if spo2 is None or spo2 < 80 or spo2 > 100:
        spo2 = 97
    if temp is None or temp < 20 or temp > 45:
        temp = 36.5
    return int(bpm), int(spo2), float(temp)


# =========================
# SEND DATA TIL SERVER
# =========================

def send_data(bpm, spo2, temp):
    """
    Sender måledata til Flask API
    """
    bpm, spo2, temp = sanitize_values(bpm, spo2, temp)

    payload = {
        "patient_id": 1,
        "bpm": bpm,
        "spo2": spo2,
        "temperature": temp,
        "timestamp": time.time()
    }

    headers = {
        "Authorization": "Bearer " + API_TOKEN
    }

    try:
        r = urequests.post(
            SERVER_URL,
            json=payload,
            headers=headers
        )
        r.close()
    except:
        pass


# =========================
# TEMPERATUR LOGIK & ALARM
# =========================

def handle_temperature(temp):
    """
    Reagerer på temperatur med farver
    og alarmer
    """
    if temp is None:
        ring_color(40, 40, 0)
        return

    if temp < 25:
        ring_color(0, 0, 80)      # Koldt → blå
    elif 25 <= temp <= 31:
        ring_color(0, 80, 0)      # Normal → grøn
    else:
        ring_color(80, 0, 0)      # For varm → rød
        vib_pulse(300)
        servo_alarm()


# =========================
# SIGNALUDGLATNING
# =========================

def smooth(values, window=8):
    """
    Glatter signalet ved moving average
    """
    if len(values) < window:
        return sum(values) / len(values)
    return sum(values[-window:]) / window


# =========================
# VARIABLER TIL SIGNALANALYSE
# =========================

ir_buffer = []
red_buffer = []
last_peak_time = time.ticks_ms()
bpm = 0
spo2 = 0


# =========================
# HOVEDLOOP
# =========================

while True:
    try:
        # Læs rå data fra MAX30100
        ir, red = sensor.read_raw()

        # Hvis fingeren ikke er korrekt placeret
        if ir < 8000:
            ring_color(0, 0, 40)
            time.sleep(0.3)
            continue

        # Gem data i buffer
        ir_buffer.append(ir)
        red_buffer.append(red)

        # Begræns buffer-størrelse
        if len(ir_buffer) > 120:
            ir_buffer.pop(0)
            red_buffer.pop(0)

        # Glat IR-signal
        ir_s = smooth(ir_buffer, 10)

        # Dynamisk tærskel
        threshold = ir_s * 1.008

        # Detekter hjerteslag
        if ir > threshold:
            now = time.ticks_ms()
            interval = time.ticks_diff(now, last_peak_time)

            # Undgå falske peaks
            if interval > 400:
                bpm_candidate = 60000 / interval

                if 50 < bpm_candidate < 150:
                    bpm = int(bpm_candidate)
                else:
                    bpm = 70

                # SpO2-beregning (AC/DC metode)
                ir_ac = max(ir_buffer) - min(ir_buffer)
                red_ac = max(red_buffer) - min(red_buffer)
                ir_dc = sum(ir_buffer) / len(ir_buffer)
                red_dc = sum(red_buffer) / len(red_buffer)

                if ir_dc > 0 and red_dc > 0:
                    R = (red_ac/red_dc) / (ir_ac/ir_dc)
                    spo2_calc = int(110 - 25 * R)

                    if 80 <= spo2_calc <= 100:
                        spo2 = spo2_calc
                    else:
                        spo2 = 97

                # Temperatur
                temp_raw = read_temperature()
                if temp_raw is None or temp_raw < 20 or temp_raw > 45:
                    temp = 36.5
                else:
                    temp = temp_raw

                # Reager på temperatur
                handle_temperature(temp)

                # Send data til server
                send_data(bpm, spo2, temp)

                last_peak_time = now

        time.sleep(0.02)

    except:
        # Fejlindikering
        ring_color(80, 0, 0)
        time.sleep(0.5)
