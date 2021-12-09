# tastermatrix.py - Abfrage einer 4x4 Matrix aus Tastern
from machine import Pin
import time

rows = [ 23, 22, 21, 19 ]
cols = [ 18, 5, 4, 15 ]

# Spalten sind Eingänge mit Pullups
for c in range(len(cols)):
    cols[c] = Pin(cols[c], Pin.IN, Pin.PULL_UP)

# Zeilen sind zunächst normale Eingänge
for r in range(len(rows)):
    Pin(rows[r], Pin.IN)

while True:
    BTNMAP = [
     '1', '2', '3', 'A',
     '4', '5', '6', 'B',
     '7', '8', '9', 'C',
     '*', '0', '#', 'D'
    ]

    # starten mit leerer Liste gedrückter Tasten
    but = [ ]
    # alle Zeilen einzeln abfragen
    for r in range(len(rows)):
        # Zeile aktiv auf Masse schalten
        Pin(rows[r], Pin.OUT).value(0)

        # alle Spalten abfragen, wenn der Eingang
        # 0 ist, dann ist die Taste Nr 4*Zeile+Spalte
        # gedrückt
        for c in range(len(cols)):
            if cols[c].value() == 0:
                but.append(BTNMAP[4*r+c])

        # Zeile wieder auf "offen" schalten, indem sie
        # zum Eingang gemacht wird
        Pin(rows[r], Pin.IN)

    
    print("Tasten:", but)
    time.sleep(1)