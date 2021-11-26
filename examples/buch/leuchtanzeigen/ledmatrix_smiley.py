# ledmatrix_smiley.py - Smiley auf 8x8 LED matrix
from time import sleep_ms
from machine import Pin

# Anschlüsse der Spalten
LED_COLS = [ 5, 14, 12, 15, 13, 4, 18, 19 ]
col = [ ]

# Anschlüsse der Reihen
LED_ROWS = [ 21, 23, 27, 22, 32, 26, 33, 25 ]
row = [ ]

# Initialisiere Pins
for l in LED_COLS:
    col.append(Pin(l,Pin.OUT))

for r in LED_ROWS:
    row.append(Pin(r,Pin.OUT))

# alle Spalteń und Zeile erstmal aus
for c in col:
    c.value(1)

for r in row:
    r.value(0)

# die acht Zeilen des Smiley-Bildes
SMILEY = [
    0b01111110,
    0b11011011,
    0b10011001,
    0b10011001,
    0b11111111,
    0b10111101,
    0b11000011,
    0b01111110
]   

while True:   
    # die acht Zeilen werden nacheinander dargestellt
    for r in range(8):       
        # alle Spalten einer Zeile werden eingestellt
        for c in range(8):
            if SMILEY[r] & 128>>c:
                col[c].value(0)
            else:
                col[c].value(1)                

        row[r].value(1)   # Zeile einschalten

        # die Verzögerungszeit bestimmt die Zeichenrate
        # hz = 1000/8/Zeit, z.B.:
        # 1: 1000/8/1 = 125 Hz
        # 2: 1000/8/2 = 62.5 Hz
        # 3: 1000/8/3 = 41.6 Hz
        # 4: 1000/8/4 = 31.25 Hz
        # ...
        sleep_ms(2)  # 62.5 Hz

        row[r].value(0)    # Zeile ausschalten
