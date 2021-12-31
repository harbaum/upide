# senso_test.py - Senso Hardware-Test
from time import sleep
from machine import Pin, PWM

# richte LEDs an Pin 18, 5, 4 und 15 ein
# und schalte sie zunächst aus (value = 0)
leds = [ 18, 5, 4, 15 ]

for l in range(4):
    leds[l] = Pin(leds[l], Pin.OUT, value=0)

# richte Tasteneingänge an Pins 27, 14, 12 und 13 ein
tasten = [ 27, 14, 12, 13 ]
for t in range(4):
    tasten[t] = Pin(tasten[t], Pin.IN, Pin.PULL_UP)

# Pin 19 als Ton-Ausgang mit PWM-Fähigkeit
ton = PWM(Pin(19, Pin.OUT))
# 50% an/aus-Verhältnis
ton.duty(512)

# Frequenzen der vier Töne
freq = [ 330, 352, 395, 440 ]

try:
    while True:
        # alle vier Tasten abfragen und deren Zustand an
        # den LEDs sichtbar machen und erste gedrückte Taste
        # merken
        taste = None
        for i in range(4):
            if tasten[i].value() == 0:
                leds[i].on()

                if taste == None:
                    taste = i
            else:
                leds[i].off()

        # erste gedrückte Taste löst zusätzlich Ton aus
        if taste != None:
            if ton.freq() <= 1:
                ton.freq(freq[taste])
        else:
            ton.freq(0)
            
except:
    # PWM bei Programmabbruch beenden
    ton.deinit()
    