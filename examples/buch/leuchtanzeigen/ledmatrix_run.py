# ledmatrix_run.py
#
# running light on 8x8 LED matrix
# Lauflicht auf 8x8 LED matrix

from time import sleep_ms
from machine import Pin

# Columns/Spalten
LED_COLS = [ 5, 14, 12, 15, 13, 4, 18, 19 ]
col = [ ]

# Rows/Reihen
LED_ROWS = [ 21, 23, 27, 22, 32, 26, 33, 25 ]
row = [ ]

# Initialize pins/Initialisiere Pins
for l in LED_COLS:
    col.append(Pin(l,Pin.OUT))

for r in LED_ROWS:
    row.append(Pin(r,Pin.OUT))

for c in range(len(col)):
    col[c].value(1)

for r in range(len(row)):
    row[r].value(0)

DELAY=100

while True:
    for c in range(len(col)):
        col[c].value(0)

        for r in range(len(row)):
            row[r].value(1)
            sleep_ms(DELAY)
            row[r].value(0)

        col[c].value(1)      

    sleep_ms(1000)
