# ws2812_rainbox.py - Regenbogenfarben auf dem ws2812-Ring
import machine, neopixel, time

np = neopixel.NeoPixel(machine.Pin(13), 8)

def wheel(pos):
    # Diese Funktion wandelt eine Zahl von 0 bis 255
    # in eine Farbe des Regenbogens um
    if pos < 85:
        # 0 ... 84 -> rot bis gruen
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        # 85 ... 169 -> gruen -> blau
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    # 170 ... 255 -> blau -> rot
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)

while True:
    for j in range(256):
        for i in range(8):
            rc_index = (i * 32 + j) % 256 # Regenbogenfarbe bestimmen
            np[i] = wheel(rc_index)          
        np.write()                        # Leuchtdioden aktualisieren
        time.sleep_ms(5)                  # fünf Millisekunden Pause