# ampel_za_tab.py - Tabellenautomat gesteuerte Verkehrsampel
from time import ticks_ms
from machine import Pin

# richte LEDS an Pin 15, 4 und 5 ein
# und schalte sie zunächst aus (value = 0)
gruen = Pin(15, Pin.OUT, value=0)
gelb  = Pin(4, Pin.OUT, value=0)
rot   = Pin(5, Pin.OUT, value=0)

# beginnen im Zustand "rot"
rot.on()
zustand = "rot"
umschaltzeit = ticks_ms() + 5000  # weiterschalten in 5000ms

# die Zustandstabelle mit den jeweiligen Folgezuständen
tabelle = {      # Name,     Zeit,  Schaltvorgänge
    "rot":     [ "gelbrot", 1000, [ gelb.on ] ],
    "gelbrot": [ "gruen",   5000, [ rot.off, gelb.off, gruen.on ] ],
    "gruen":   [ "gelb",    1000, [ gruen.off, gelb.on ] ],
    "gelb":    [ "rot",     5000, [ gelb.off, rot.on ] ] }

def naechster_zustand(zustand):
    naechster = tabelle[zustand]      # Zeile des aktuellen Zustands lesen
    for p in naechster[2]: p()        # Leuchten an/ausschalten
    return naechster[0], naechster[1] # nächster Zustandsname und -Zeit
        
while True:
    # Zeit zum Umschalten schon erreicht?
    if ticks_ms() > umschaltzeit:
        # ja -> Ampel umschalten und Zeit zum nächsten Wechsel berechnen
        zustand, zeit_differenz = naechster_zustand(zustand)
        umschaltzeit = ticks_ms() + zeit_differenz 