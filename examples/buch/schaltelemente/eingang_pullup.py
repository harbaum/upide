# eingang_pullup.py - Abfrage eines Eingangs mit Pullup
from machine import Pin
import time

# richte Eingang mit Pullup an Pin 15 ein
pin = Pin(15, Pin.IN, Pin.PULL_UP)

while True:
    # Zustand des Eingangs lesen und ausgeben
    print("Pin 15 ist:", pin.value())
    time.sleep(1)