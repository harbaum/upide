# 7seg_run.py - Laufende Linie auf 7-Segment-Anzeige
from time import sleep_ms
from machine import Pin

# Anschlusspins der sieben Segmente A bis G und DP
LEDS = [ 4, 15, 12, 14, 27, 5, 18, 13 ]
led = [ ]

# Initialisiere Pins
for l in LEDS:
    led.append(Pin(l,Pin.OUT))

for l in led:   # alle Segemente aus
    l.value(1)

while True:
    for l in led[:6]:     # nur die sechs Segmente A-F
        l.value(0)        # schalte LED ein
        sleep_ms(100)
        l.value(1)        # schalte LED wieder aus