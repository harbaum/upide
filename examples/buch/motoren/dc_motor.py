# dc_motor.py - Ansteuerung eines einfachen Gleichspannungs-Motors
from machine import Pin, PWM
import time

# PWM an Pins 12 und 13 einrichten. Beide mit
# einer Frequenz von 200 Hertz
def init():
    global pwm1, pwm2

    pwm1 = PWM(Pin(12, Pin.OUT)) # "Input 1" an Pin 12
    pwm1.freq(200)               # 200 Hz
    pwm1.duty(0)                 # Ausgang 0% an (also ganz aus)
    pwm2 = PWM(Pin(13, Pin.OUT)) # "Input 2" an Pin 13 
    pwm2.freq(200)               # 200 Hz
    pwm2.duty(0)                 # Ausgang 0% an (also ganz aus)

# Motor zu X Prozent in gegebene Richtung laufen lassen
def motor(richtung, prozent=0):
    global pwm1, pwm2

    if richtung == None:
        # nicht drehen: beide Ausgänge aus (auf Masse)
        pwm1.duty(0)
        pwm2.duty(0)
        return

    # PWM-Verhältnis den Prozent entsprechend einstellen,
    # je nach Drehrichtung den einen oder den anderen Pin
    # aktiveren und den jeweils anderen aus (auf Masse)
    if richtung:
        pwm1.duty(1023*prozent//100)
        pwm2.duty(0)
    else:
        pwm1.duty(0)
        pwm2.duty(1023*prozent//100)

# PWM abschalten
def deinit():
    global pwm1, pwm2

    pwm1.deinit()
    pwm2.deinit()
    
# Motor langsamn aus dem Stillstand starten und dann
# langsam wieder zum Stillstand bremsen
def rauf_runter(richtung):

    # erst langsam die Drehzahl erhöhen ...
    for i in range(101):
        motor(richtung, i)
        time.sleep(.05)

    # ... und dann wieder absenken
    for i in reversed(range(101)):
        motor(richtung, i)
        time.sleep(.05)

# PWM für beider Motorausgänge einrichten
init()

rauf_runter(False)  # rauf-runter in die eine Richtung
rauf_runter(True)   # rauf-runter in die andere Richtung

# PWN wieder deaktivieren
deinit()
