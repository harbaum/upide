# joystick_simple.py - Einfache Abfrage eines analogen Joysticks
from machine import Pin, ADC
import time

# nur die Pins 32-39 sind unter Micropython für 
# Analogauswertung nutzbar
x = ADC(Pin(32))
y = ADC(Pin(33))
fire = Pin(15, Pin.IN, Pin.PULL_UP)

x.atten(ADC.ATTN_11DB)       # ganzer 0 bis 3.3-Volt-Bereich
y.atten(ADC.ATTN_11DB)       # -"-

while True:
    # alle Achsen lesen und ausgeben
    print("X/Y/Fire:", x.read(), y.read(), fire.value())
    time.sleep(0.1)