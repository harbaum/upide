# leds.py - PyBoard led demo
import pyb

leds = [pyb.LED(i) for i in range(1,5)]
n = 3
try:
    while True:
        n = (n + 1) % 4
        leds[n].toggle()
        pyb.delay(50)
except:
    for i in range(4):
        leds[i].off()
