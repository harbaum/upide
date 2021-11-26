# ledmatrix_dot.py - blinkender Punkt auf 8x8 LED matrix
from time import sleep_ms
from machine import Pin

# richte LED an Pin 15 ein
led = Pin(15, Pin.OUT)

while True:
    led.value(0)    # schalte LED an
    sleep_ms(500)

    led.value(1)    # schalte LED aus
    sleep_ms(500)