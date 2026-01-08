# =========================
# IMPORTS
# =========================

from machine import I2C   # I2C bruges til kommunikation med MAX30100
import time               # Bruges til små delays ved initialisering


# =========================
# I2C ADRESSE
# =========================

# MAX30100 har fast I2C-adresse: 0x57
MAX30100_ADDRESS = 0x57


# =========================
# REGISTER ADRESSER
# =========================
# Disse adresser bruges til at konfigurere sensoren

REG_INTR_STATUS   = 0x00  # Interrupt status (ikke brugt her)
REG_INTR_ENABLE   = 0x01  # Interrupt enable (ikke brugt her)
REG_FIFO_WR_PTR   = 0x02  # FIFO write pointer
REG_OVF_COUNTER   = 0x03  # FIFO overflow counter
REG_FIFO_RD_PTR   = 0x04  # FIFO read pointer
REG_FIFO_DATA     = 0x05  # FIFO data register (rå sensordata)
REG_MODE_CONFIG   = 0x06  # Mode configuration (reset + mode)
REG_SPO2_CONFIG   = 0x07  # SpO2 konfiguration (sample rate, pulse width)
REG_LED_CONFIG    = 0x09  # LED strømstyrke (IR + RED)


# =========================
# MAX30100 KLASSE
# =========================

class MAX30100:
    """
    Denne klasse fungerer som en simpel driver
    til MAX30100 pulsoximeter-sensoren.
    """

    def init(self, i2c):
        """
        Initialiserer MAX30100 sensoren
        """

        # Gem I2C-objekt
        self.i2c = i2c

        # Gem sensorens I2C-adresse
        self.addr = MAX30100_ADDRESS


        # =========================
        # RESET SENSOR
        # =========================

        # Skriv 0x40 til MODE_CONFIG
        # Bit 6 = reset
        self.i2c.writeto_mem(self.addr, REG_MODE_CONFIG, b'\x40')

        # Vent kort så reset kan gennemføres
        time.sleep(0.1)


        # =========================
        # AKTIVER SPO2 MODE
        # =========================

        # 0x03 = SpO2 mode
        # Sensoren måler både puls og iltmætning
        self.i2c.writeto_mem(self.addr, REG_MODE_CONFIG, b'\x03')


        # =========================
        # LED STRØM
        # =========================

        # 0xFF = maksimal strøm til både IR og RED LED
        # Giver stærkere signal (men højere strømforbrug)
        self.i2c.writeto_mem(self.addr, REG_LED_CONFIG, b'\xFF')


        # =========================
        # SPO2 KONFIGURATION
        # =========================

        # 0x27:
        # - Sample rate
        # - Pulse width
        # - ADC range
        self.i2c.writeto_mem(self.addr, REG_SPO2_CONFIG, b'\x27')


    def read_raw(self):
        """
        Læser rå IR- og RED-data fra sensoren
        """

        # Læser 4 bytes fra FIFO data register
        # Byte 0–1: IR værdi
        # Byte 2–3: RED værdi
        data = self.i2c.readfrom_mem(self.addr, REG_FIFO_DATA, 4)

        # Sammensætter 16-bit værdier
        ir  = (data[0] << 8) | data[1]
        red = (data[2] << 8) | data[3]

        # Returnerer rå værdier
        return ir, red
