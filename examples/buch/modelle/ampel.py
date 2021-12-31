# ampel.py - Verkehrsampel
from time import sleep
from machine import Pin

# richte LEDS an Pin 15, 4 und 5 ein
# und schalte sie zunächst aus (value = 0)
gruen = Pin(15, Pin.OUT, value=0)
gelb  = Pin(4, Pin.OUT, value=0)
rot   = Pin(5, Pin.OUT, value=0)

# Taster mit Pullup an Pin 13
taste = Pin(13, Pin.IN, Pin.PULL_UP)

while True:
    # 1. Phase: rot
    rot.on()
    gelb.off()
    sleep(5)

    # 2. Phase: rot+gelb
    gelb.on()
    sleep(1)

    # 3. Phase: grün
    rot.off()
    gelb.off()
    gruen.on()

    # fünf Sekunden grün
    sleep(5)

    # Alternative: die Grünphase wird nicht nach einer festen
    # Zeit verlassen
    # while taste.value():
    #    pass

    # 4. Phase: gelb
    gruen.off()
    gelb.on()
    sleep(1)
