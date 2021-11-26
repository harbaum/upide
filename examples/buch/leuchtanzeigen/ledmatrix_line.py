# ledmatrix_line.py - Laufende Linie auf 8x8 LED matrix
from time import sleep_ms
from machine import Pin

# Spalten
LED_COLS = [ 5, 14, 12, 15, 13, 4, 18, 19 ]
col = [ ]

# Initialisiere Pins
for l in LED_COLS:
    col.append(Pin(l,Pin.OUT))

for c in col:        # alle LEDs erstmal aus
    c.value(1)

while True:
    for c in col:    # schalte alle LEDs nacheinander an
        c.value(0)
        sleep_ms(100)

    for c in col:    # schalte alle LEDs nacheinander aus
        c.value(1)      
        sleep_ms(100)