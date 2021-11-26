# ledmatrix_banner.py - Banner auf 8x8 LED matrix
from time import sleep_ms
from machine import Pin, freq
import gc

# Spalten
LED_COLS = [ 5, 14, 12, 15, 13, 4, 18, 19 ]
col = [ ]

# Reihen
LED_ROWS = [ 21, 23, 27, 22, 32, 26, 33, 25 ]
row = [ ]

# Initialisiere Pins
for l in LED_COLS:
    col.append(Pin(l,Pin.OUT))

for r in LED_ROWS:
    row.append(Pin(r,Pin.OUT))

for c in col:
    c.value(1)

for r in row:
    r.value(0)

# die acht Zeilen des Banner-Bildes
WIDTH = 56  # Anzahl Spalten
BANNER = [
    0b01100110000110000110000001100000000110000110011000000000,
    0b01100110001111000110000001100000001111000110011000000000,
    0b01100110001111000110000001100000011001100110011000000000,
    0b01111110011001100110000001100000011001100110011000000000,
    0b01111110011111100110000001100000011001100110011000000000,
    0b01100110011111100110000001100000011001100000000000000000,
    0b01100110011001100111111001111110001111000110011000000000,
    0b01100110011001100111111001111110000110000110011000000000
]   

gc.disable()   # keine automatische Speicherverwaltung

def draw_image(offset):
    # die Zeilen werden nacheinander dargestellt
    for r in range(8):        
        # alle Spalten einer Zeile werden eingestellt
        for c in range(8):
            if BANNER[r] & 1<<((c+offset)%WIDTH):
                col[7-c].value(0)
            else:
                col[7-c].value(1)                

        row[r].value(1)  # Zeile einschalten
        sleep_ms(1)      # 125 Hz
        row[r].value(0)  # Zeile ausschalten

while True:
    for offset in range(WIDTH):
        for delay in range(3):
            draw_image(WIDTH-1-offset)

    gc.collect()  # Speicherverwaltung