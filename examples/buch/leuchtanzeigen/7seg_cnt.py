# 7seg_cnt.py - Zählen mit 7-Segment-Anzeige
from time import sleep_ms
from machine import Pin

# Anschlusspins der sieben Segmente A bis G und DP
leds = { "A":  4, "B": 15, "C": 12,  "D": 14, 
         "E": 27, "F":  5, "G": 18, "DP": 13 }

# Segmente aus denen die Ziffern 0 bis 9 sowie die
# Buchstaben A bis F bestehen
segments = { 0:  "ABCDEF", 1: "BC",   2: "ABGED",
             3:  "ABGCD",  4: "FBGC", 5: "AFGCD",
             6:  "AFGECD", 7: "ABC",  8: "ABCDEFG",
             9:  "AFBGCD", 
            'A': "AFBGEC", 'B': "FGECD", 'C': "AFED",
            'D': "BGECD",  'E': "AFGED", 'F': "AFGE" }

# Initialisiere Pins
for l in leds:
    leds[l] = Pin(leds[l],Pin.OUT)

def digit(s, dot=False):
    for l in leds:
        leds[l].value(0 if l in segments[s] else 1)
    leds["DP"].value(0 if dot else 1)

while True:
    for d in segments:   # alle Ziffern durchgehen
        digit(d, True)   # Ziffer mit Punkt anzeigen
        sleep_ms(25)     # sehr kurz warten
        digit(d, False)  # Ziffer ohne Punkt anzeigen
        sleep_ms(225)    # warten
