# analogeingang.py - Abfrage eines analogen Eingangs
from machine import Pin, ADC
import time

# nur die Pins 32-39 sind unter Micropython für 
# Analogauswertung nutzbar
pin = ADC(Pin(32))
pin.atten(ADC.ATTN_11DB)       # ganzer 0 bis 3.3-Volt-Bereich

while True:
    # Analogwert lesen und ausgeben
    print("Analogwert:", pin.read())
    time.sleep(0.1)