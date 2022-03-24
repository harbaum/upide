# See https://lego.github.io/MINDSTORMS-Robot-Inventor-hub-API/
import hub
import time

# Three ways to set the center button LED
print("LED")
hub.led(7) # orange
time.sleep(1)
hub.led(0,128,128) # R,G,B
time.sleep(1)
rgb=(64,0,64)
hub.led( rgb ) # R,G,B tuple
time.sleep(1)

# Do some beeps
print("SOUND")
hub.sound.volume(10) # 0..10
hub.sound.beep(freq=1000, time=100, waveform=hub.sound.SOUND_SIN) 
time.sleep_ms(200) # wait 100 for beep plus 100 pause
hub.sound.beep(1000,100) 
time.sleep_ms(200)
hub.sound.beep(500,100) 
time.sleep_ms(200)

# Run motor on port A
print("MOTOR")
m = hub.port.A.motor
print( '\n  '.join(dir(m)) ) # print all methods
m.run_at_speed(50) # -100..+100
time.sleep(1)
m.run_at_speed(0)
m.run_for_time(2000) # ms
time.sleep_ms(2500)
m.run_for_degrees(90,speed=20)
time.sleep(1)
m.run_to_position(270,speed=20)

# Color sensor on port F
print("COLOR")
c = hub.port.F.device
for _ in range(25) :
    print('  ',c.get()) #black=0, yellow=7, red=9 etc
    time.sleep_ms(500)

print("DONE")
