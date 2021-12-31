# ampel_za.py - Durch Zustandsautomat gesteuerte Verkehrsampel
from time import ticks_ms
from machine import Pin

# richte LEDS an Pin 15, 4 und 5 ein
# und schalte sie zunächst aus (value = 0)
gruen = Pin(15, Pin.OUT, value=0)
gelb  = Pin(4, Pin.OUT, value=0)
rot   = Pin(5, Pin.OUT, value=0)

# Taster mit Pullup an Pin 13
taste = Pin(13, Pin.IN, Pin.PULL_UP)

# beginnen im Zustand "rot"
rot.on()
zustand = "rot"
umschaltzeit = ticks_ms() + 5000  # weiterschalten in 5000ms

def naechster_zustand(zustand):
    if zustand == "rot":
        gelb.on()                # zusätzlich gelb an
        return "gelbrot", 1000   # neuer zustand "gelbrot" für 1000ms

    elif zustand == "gelbrot":
        rot.off()                # rot und 
        gelb.off()               # gelb aus,
        gruen.on()               # gruen an
        return "gruen", 5000     # neuer zustand "gruen" für 5000ms
    
    elif zustand == "gruen":
        gruen.off()              # grün aus,  
        gelb.on()                # gelb an
        return "gelb", 1000      # neuer zustand "gelb" für 1000ms

    else:
        gelb.off()               # gelb aus, 
        rot.on()                 # rot an
        return "gelb", 5000      # neuer zustand "rot" für 5000ms
        
ist_losgelassen = taste.value()
while True:
    # Zeit zum Umschalten schon erreicht?
    if ticks_ms() > umschaltzeit:
        # ja -> Ampel umschalten und Zeit zum nächsten Wechsel berechnen
        zustand, zeit_differenz = naechster_zustand(zustand)
        umschaltzeit = ticks_ms() + zeit_differenz 

    # hier kann jetzt alles mögliche andere gemacht werden, da
    # das Programm nicht mehr in time.sleep()-Befehlen wartet.
    # Man kann z.B. den Taster abfragen:
    if taste.value() != ist_losgelassen:
        ist_losgelassen = taste.value()
        print("Taste", "losgelassen" if ist_losgelassen else "gedrückt")
