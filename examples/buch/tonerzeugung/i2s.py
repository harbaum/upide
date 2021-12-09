# dac.py - Ton-Ausgabe mit dem Digital Analog Converter
import machine, time

from machine import I2S
from machine import Pin

sck_pin = Pin(14, Pin.OUT)   # Serial clock output
ws_pin = Pin(13, Pin.OUT)    # Word clock output
sd_pin = Pin(12, Pin.OUT)    # Serial data output

with open("/snd/hallo_micropython_s16.raw", "rb") as f:
    sample = f.read()

audio_out = I2S(1,
     sck=sck_pin, ws=ws_pin, sd=sd_pin,
     mode=I2S.TX,
     bits=16,
     format=I2S.MONO,
     rate=8000,
     ibuf=20000)

while True:
    print("Hallo!")
    audio_out.write(sample) 
