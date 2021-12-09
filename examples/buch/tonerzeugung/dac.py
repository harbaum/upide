# dac.py - Ton-Ausgabe mit dem Digital Analog Converter
import machine, time

# Pin 25 für DAC-Ausgabe vorbereiten
dac = machine.DAC(machine.Pin(25))

with open("/snd/hallo_micropython_u8.raw", "rb") as f:
    sample = f.read()

while True:
    print("Hallo!")
    # alle Bytes nacheinander auf dem DAC ausgeben
    for byte in sample:
        dac.write(byte)
        # bei 8kHz dauert jeder Wert 125us. Da die 
        # Schleife und das Ausgeben auf dem DAC auch
        # etwas Zeit benötigt passt hier 100 us besser
        time.sleep_us(100)
