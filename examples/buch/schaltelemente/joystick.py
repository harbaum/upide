# joystick.py - Abfrage eines analogen Joysticks
from machine import Pin, ADC
import time

# nur die Pins 32-39 sind unter Micropython für 
# Analogauswertung nutzbar
x = ADC(Pin(32))
y = ADC(Pin(33))
fire = Pin(15, Pin.IN, Pin.PULL_UP)

x.atten(ADC.ATTN_11DB)       # ganzer 0 bis 3.3-Volt-Bereich
y.atten(ADC.ATTN_11DB)       # -"-

# 10 Messwerte in Ruhelage einlesen und Mittelwert bilden
mitte = [ 0, 0 ]
for i in range(10):
    mitte[0] += x.read()
    mitte[1] += y.read()
mitte[0] //= 10
mitte[1] //= 10

# Funktion, um aus rohen Messwerten brauchbare Werte für
# Joystick-Achsen zu machen
def joystick(v, m):
    # v ist der Messwert 0 ... 4095
    # m ist der Mittelwert

    wert = v - m   # Werte um Null erzeugen

    # Totbereich +/- 100    
    if wert > -100 and wert < 100:
        return 0

    # Werte außerhalb des Totbereichs anpassen
    if wert >  0: wert -= 100
    if wert <  0: wert += 100

    # Werte auf Bereich +/- 100 skalieren
    # max = (4095 - m) - 100
    if wert > 0: wert = 100 * wert // (4095-m-100)
    # min = - m + 50
    if wert < 0: wert = 100 * wert // (m-100)

    return wert

while True:
    # alle Achsen lesen und ausgeben
    x_wert = joystick(x.read(), mitte[0])
    y_wert = joystick(y.read(), mitte[1])
    print("X/Y/Fire:", x_wert, y_wert, fire.value())
    time.sleep(0.1)