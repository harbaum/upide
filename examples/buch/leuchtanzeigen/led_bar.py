# led_bar.py - Laufende Linie auf LED bar
from time import sleep_ms
from machine import Pin

# Die Anschlusspins der zehn Leuchtdioden
LEDS = [ 12, 13, 23, 22, 21, 19, 18, 5, 4, 15 ]
led = [ ]

# Initialisiere Pins
for l in LEDS:
    led.append(Pin(l,Pin.OUT))

# Alle Leuchtdioden aus
for l in led:
    l.value(0)

while True:
    # schalte alle LEDs nacheinander an
    for l in led:
        l.value(1)
        sleep_ms(100)

    # schalte alle LEDs nacheinander wieder aus
    for l in reversed(led):
        l.value(0)      
        sleep_ms(100)