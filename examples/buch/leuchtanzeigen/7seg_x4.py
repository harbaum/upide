# 7seg_cnt.py - Zählen mit 7-Segment-Anzeige
from time import sleep_ms
from machine import Pin

# Anschlusspins der sieben Segmente A bis G und DP
leds = { "A": 19, "B":  15, "C": 14,  "D": 26, 
         "E": 25, "F":  18, "G": 12, "DP": 27 }

# Segmente aus denen die Ziffern 0 bis 9 sowie die
# Buchstaben A bis F bestehen
segments = { 0:  "ABCDEF", 1: "BC",   2: "ABGED",
             3:  "ABGCD",  4: "FBGC", 5: "AFGCD",
             6:  "AFGECD", 7: "ABC",  8: "ABCDEFG",
             9:  "AFBGCD", 
            'A': "AFBGEC", 'B': "FGECD", 'C': "AFED",
            'D': "BGECD",  'E': "AFGED", 'F': "AFGE" }

# Anschluss-Pin der Anode jeder Ziffer
digits = [ 21, 5, 4, 13 ]

# Initialisiere Pins

# acht Kathodenanschlüsse
for l in leds:
    leds[l] = Pin(leds[l],Pin.OUT)

# vier Anodenanschlüsse
for d in range(len(digits)):
    digits[d] = Pin(digits[d], Pin.OUT)

# Zeige eine der vier Ziffern an
def digit(d, s, dot=False):
    # alle Ziffern aus
    for i in digits:
        i.value(0) 

    for l in leds:
        leds[l].value(0 if l in segments[s] else 1)
    leds["DP"].value(0 if dot else 1)

    # nur die Anode der ausgewählten Ziffer einschalten
    for i in range(len(digits)):
        digits[i].value(1 if i == d else 0) 

    # sehr kurz warten, damit die Ziffer sichtbar bleibt
    sleep_ms(3)

cnt = 1234  # ab 1234 zählen
while True:
    for i in range(5):
        # Ziffern der vier Stellen berechnen
        digit(0, int((cnt/1000)%10))
        digit(1, int((cnt/100)%10))
        digit(2, int((cnt/10)%10))
        digit(3, int((cnt/1)%10))

    cnt = cnt + 1   # einen Schritt weiter zählen