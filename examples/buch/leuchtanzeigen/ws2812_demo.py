# ws2812_demo.py - ws2812-Demonstration
import machine, neopixel, time

# der Ring ist an Pin 13 angeschlossen
np = neopixel.NeoPixel(machine.Pin(13), 8)

while True:
    for i in range(8):      # alle acht Leuchdioden durchgehen
        np[i] = (255, 0, 0) # Farbe auf 100% rot
        np.write()          # Ausgabe aktualisieren
        time.sleep(0.10)    # warten
        np[i] = (0, 0, 0)   # vorige Leuchdiode wieder aus