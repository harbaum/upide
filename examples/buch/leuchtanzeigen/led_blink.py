# led_blink.py - blinkende LED
from time import sleep_ms
from machine import Pin

# richte LED an Pin 15 ein
led = Pin(15, Pin.OUT)

while True:
    led.value(1)    # schalte LED für 50ms an
    sleep_ms(50)

    led.value(0)    # schalte LED für 950ms aus
    sleep_ms(950)