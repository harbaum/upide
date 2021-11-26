# led_rgb.py - RGB LED
from time import sleep_ms
from machine import Pin

# richte LED an Pin 15, 4 und 5 ein
led_b = Pin(15, Pin.OUT)
led_g = Pin(4, Pin.OUT)
led_r = Pin(5, Pin.OUT)

while True:
    led_r.value(1)   # Rot aus
    led_g.value(1)   # Grün aus
    led_b.value(1)   # Blau aus
    sleep_ms(1000)

    led_r.value(0)   # Rot an
    led_g.value(1)   # Grün aus
    led_b.value(1)   # Blau aus
    sleep_ms(1000)

    led_r.value(1)   # Rot aus
    led_g.value(0)   # Grün an
    led_b.value(1)   # Blau aus
    sleep_ms(1000)

    led_r.value(1)   # Rot aus
    led_g.value(1)   # Grün aus
    led_b.value(0)   # Blau an
    sleep_ms(1000)

    led_r.value(0)   # Rot an
    led_g.value(0)   # Grün an
    led_b.value(1)   # Blau aus
    sleep_ms(1000)

    led_r.value(0)   # Rot an
    led_g.value(1)   # Grün aus
    led_b.value(0)   # Blau an
    sleep_ms(1000)

    led_r.value(1)   # Rot aus
    led_g.value(0)   # Grün an
    led_b.value(0)   # Blau an
    sleep_ms(1000)

    led_r.value(0)   # Rot an
    led_g.value(0)   # Grün an
    led_b.value(0)   # Blau an
    sleep_ms(1000)