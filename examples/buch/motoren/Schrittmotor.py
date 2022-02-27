# Schrittmotor.py - Ansteuerung eines Schrittmotors
from machine import Pin
from time import sleep

pins = [ 18, 5, 4, 15 ]   # die vier Pins für die vier Motoranschlüsse

# Pin-Objekte erzeugen
for l in range(len(pins)):
    pins[l] = Pin(pins[l], Pin.OUT, value=0)

while True:
    # 512 x die Pins 18, 5, 4, 15, 18, 5, ... einzeln aktivieren
    for x in range(512):
        for pin in pins:               # normale Reihenfolge
            pin.on()                   # Pin einschalten (high)
            sleep(1/120)               # 1/120 Sekunde warten
            pin.off()                  # Pin wieder ausschalten  

    # 512 x die Pins 15, 4, 5, 18, 15, 4  ... einzeln aktivieren
    for x in range(512):
        for pin in reversed(pins):     # umgekehrte Reihenfolge
            pin.on()
            sleep(1/120)               # s.o.
            pin.off()    
