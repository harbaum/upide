# eingang.py - Abfrage eines Eingangs
from machine import Pin
import time

# richte Eingang an Pin 15 ein
pin = Pin(15, Pin.IN)

while True:
    # Zustand des Eingangs lesen und ausgeben
    print("Pin 15 ist:", pin.value())
    time.sleep(1)