# melodie.py - Spielen einer kurzen Melodie
from machine import Pin, PWM
import time

# eine kurze Melodie aus 7 Tönen
MELODY = [
    (262, 4),  # c4
    (196, 8),  # g3
    (196, 8),  # g3
    (220, 4),  # a3
    (196, 4),  # g3
    (0,   4),
    (247, 4),  # b3
    (262, 4)   # c4
]

def beep(freq=440, duration=0.1):
    pwm.freq(freq)        # spiele gegebene Frequenz
    time.sleep(duration)  # warte Notenlänge
    pwm.freq(0)           # aus

# Pin 15 als Ausgang mit PWN-Fähigkeit
pwm = PWM(Pin(15, Pin.OUT))
# 50% an/aus-Verhältnis
pwm.duty(512)

# alle Töne der Melodie spielen
for ton in MELODY:
    beep(ton[0], 2/ton[1])

# PWN wieder deaktivieren
pwm.deinit()
