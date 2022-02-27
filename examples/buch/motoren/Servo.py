# Servo.py - Ansteuerung eines Servo-Motors
from machine import Pin, PWM
import time 

# PWM mit 50 Hertz an Pin 13, Servo
# zunächst in Mittelposition
servo = PWM(Pin(13), freq=50, duty=77)

while True:
    servo.duty(51)  # minimale Position anfahren
    time.sleep(1)
    servo.duty(102) # maximale Position anfahren
    time.sleep(1)

