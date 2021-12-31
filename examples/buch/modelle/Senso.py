# senso.py - Senso-Spiel
from time import sleep, ticks_ms
from machine import Pin, PWM
from random import randint
import sys

# vier Leuchtdioden, vier Tasten und der Tonausgang
leds = [ 18, 5, 4, 15 ]
tasten = [ 27, 14, 12, 13 ]
lautsprecher = None

# Frequenzen der vier Töne
freq = [ 330, 352, 395, 440 ]

# aktuelle Sequenz
sequenz = None
zustand = None
zeit    = None

TONLAENGE = 250    # Zeit in ms, die Ton gespielt wird
TON_PAUSE = 100    # Zeit in ms zwischen Tönen

BEDENKZEIT = 3000  # Timeout für Tastendruck

DEBUG = False      # Hilfsausgaben an/aus

def ton(freq=0):
    # Ton einschalten mit gegebener Frequenz 
    # bzw. ausschalten, wenn Frequenz 0 ist
    global lautsprecher
    if freq == 0:
        lautsprecher.duty(0)
    else:
        # 50% an/aus-Verhältnis
        lautsprecher.duty(512)
        lautsprecher.freq(freq)

def init():
    global leds, tasten, lautsprecher

    # richte LEDs an Pin 18, 5, 4 und 15 ein
    # und schalte sie zunächst aus (value = 0)
    for l in range(4):
        leds[l] = Pin(leds[l], Pin.OUT, value=0)

    # richte Tasteneingänge an Pins 27, 14, 12 und 13 ein
    for t in range(4):
        tasten[t] = Pin(tasten[t], Pin.IN, Pin.PULL_UP)

    # Pin 19 als Ton-Ausgang mit PWM-Fähigkeit, zunächst kein Ton
    lautsprecher = PWM(Pin(19, Pin.OUT))
    lautsprecher.duty(0)
    lautsprecher.freq(0)
    lautsprecher.duty(0)

def erweitere_sequenz():
    global sequenz, zustand, zeit

    # erweitere die Ton/Licht-Sequenz um zufälliges Element
    sequenz.append(randint(0, 3))

    zustand = [ "ton", 0 ]     # als nächstes ersten Ton in Sequenz abspielen
    zeit = ticks_ms() + 1000   # aber erst in einer Sekunde abspielen

def lies_taste():
    # Zustand aller Tasten einlesen und nur dann eine
    # gedrückte Taste melden, wenn wirklich nur eine Taste
    # gedrückt ist
    taste = None
    for t in range(4):
        if tasten[t].value() == 0:
            if taste != None:   # bereits andere Taste gedrückt? -> Fehler
                return None
            taste = t
    return taste      

def spielen():
    global zeit, zustand, sequenz

    if DEBUG: print(ticks_ms(), zeit, zustand)

    # Spieler sollte eine Taste drücken ...
    if zustand[0] == "warte auf taste":
        taste = lies_taste()
        if taste != None:
            # LED noch nicht eingeschaltet (Taste war nicht
            # bereits gedrückt)?
            if leds[taste].value() == 0:
                leds[taste].on()    # LED einschalten
                ton(freq[taste])    # Ton spielen

                # testen ob Taste korrekt
                if taste == sequenz[zustand[1]]:
                    # warte auf das Loslassen der Taste. Der Benutzer kann die Taste
                    # sofort drücken, hat aber maximal "BDENKZEIT" Millisekunden Zeit dafür
                    zeit = ticks_ms() + BEDENKZEIT
                    zustand = [ "warte auf loslassen", zustand[1], taste ]
                else:
                    # falsche Taste -> Spielende
                    zeit = ticks_ms()
                    zustand = [ "ende", 0 ]

    elif zustand[0] == "warte auf loslassen":
        taste = lies_taste() 
        if taste == None:
            # LED eingeschaltet?
            if leds[zustand[2]].value() != 0:
                leds[zustand[2]].off()   # LED ausschalten
                ton()                    # Ton aus

                # testen, ob Sequenz vollständig
                if zustand[1]+1 < len(sequenz):
                    # nein, auf nächste Taste warten
                    zeit = ticks_ms() + BEDENKZEIT
                    zustand = [ "warte auf taste", zustand[1]+1 ]
                else:
                    # ja, sequenz erweitern
                    erweitere_sequenz()

    elif zustand[0] == "warte auf start":
        # teste, ob Spieler eine Taste gedrückt hat, um zu spielen
        taste = lies_taste() 
        if taste != None:
            for i in range(4): leds[i].off()
            sequenz = []
            erweitere_sequenz()                   

    # Zeit für den nächsten Spielschritt?
    if zeit < ticks_ms():
        if zustand[0] == "warte auf start":
            # Geräte spielt die "Startanimation"
            leds[zustand[1]].off()
            leds[(zustand[1]+1)&3].on()            

            zeit = ticks_ms() + 100
            zustand = [ "warte auf start", (zustand[1]+1)&3 ]

        elif zustand[0] == "ton":
            # Gerät spielt einen Ton aus der Sequenz
            effekt = sequenz[zustand[1]]
            # Leuchte und Ton einschalten
            leds[effekt].on()
            ton(freq[effekt])

            zeit = ticks_ms() + TONLAENGE
            zustand = [ "ton ende", zustand[1], TON_PAUSE ]

        elif zustand[0] == "ton ende":
            effekt = sequenz[zustand[1]]
            # Leuchte und Ton ausschalten
            leds[effekt].off()
            ton()        

            # ist da ein weiterer Ton in der Sequenz?
            if zustand[1]+1 < len(sequenz):
                zeit = ticks_ms() + TON_PAUSE
                zustand = [ "ton", zustand[1]+1 ]
            else:
                if DEBUG: print("sequenz beendet")
                zeit = ticks_ms() + BEDENKZEIT
                zustand = [ "warte auf taste", 0 ]

        elif zustand[0] == "warte auf taste" or zustand[0] == "warte auf loslassen":
            if DEBUG: print("timeout!")
            # Taste nicht schnell genug gedrückt
            zeit = ticks_ms()
            zustand = [ "ende", 0 ]

        elif zustand[0] == "ende":
            # Ende, dreimal alle Leuchten blinken und tiefen Ton spielen
            if zustand[1] & 1:
                for i in range(4): leds[i].on()
                ton(100)
            else:
                for i in range(4): leds[i].off()
                ton()

            if zustand[1] < 6:
                # Ende-blinken insgesamt dreimal (6 x an/aus)
                zeit = ticks_ms() + 250
                zustand = [ "ende", zustand[1] + 1 ]
            else:
                # Endeblinke fertig, wieder in Startzustand gehen
                zeit = ticks_ms()
                zustand = [ "warte auf start", 3 ]

def start():
    global leds, sequenz

    # starte mit leerer Sequenz
    sequenz = [ ]
    erweitere_sequenz()
        
try:
    init()            # Hardware einrichten

    zustand = [ "warte auf start", 3 ]
    zeit = ticks_ms()

    while True:
        spielen()     # Spielfortschritt berechnen
        sleep(.01)

except Exception as e:
    sys.print_exception(e)
except:
    print("Exception")

# PWM bei Programmabbruch beenden
lautsprecher.deinit()