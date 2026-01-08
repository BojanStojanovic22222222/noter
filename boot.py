# =========================
# IMPORTS
# =========================

import network   # MicroPython-modul til netværk (Wi-Fi)
import time      # Bruges til delay (sleep)


# =========================
# WIFI KONFIGURATION
# =========================

# Navn på Wi-Fi-netværket (SSID)
WIFI_SSID = "7D"

# Adgangskode til Wi-Fi-netværket
WIFI_PASS = "Gruppe7d"


# =========================
# WIFI FORBINDELSE
# =========================

def connect_wifi():
    """
    Opretter forbindelse til et Wi-Fi-netværk.
    Denne funktion køres ved opstart af enheden.
    """

    # Opretter WLAN-objekt i station mode (STA_IF)
    # STA_IF betyder at enheden opfører sig som klient
    wlan = network.WLAN(network.STA_IF)

    # Aktiverer Wi-Fi-modulet
    wlan.active(True)

    # Forsøger at forbinde til Wi-Fi
    wlan.connect(WIFI_SSID, WIFI_PASS)

    # Timeout på 15 sekunder
    timeout = 15

    # Vent indtil der er forbindelse eller timeout udløber
    while not wlan.isconnected() and timeout > 0:
        print("Forbinder til Wi-Fi...", timeout)
        time.sleep(1)   # Vent 1 sekund
        timeout -= 1

    # Tjek om forbindelsen lykkedes
    if wlan.isconnected():
        # ifconfig() returnerer IP, subnet, gateway, DNS
        print("Wi-Fi forbundet:", wlan.ifconfig())
    else:
        # Hvis forbindelsen fejler
        print("Kunne ikke forbinde til Wi-Fi")


# =========================
# KØR WIFI-FUNKTION
# =========================

# Kører Wi-Fi-forbindelsen automatisk ved boot
connect_wifi()


# =========================
# BOOT FLOW
# =========================

# Denne print vises når boot.py er færdig
# main.py starter automatisk bagefter
print("boot.py færdig – starter main.py...")
