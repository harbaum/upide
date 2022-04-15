# Import the MindStorms Hub module (works on Spike Prime too)
from mindstorms import MSHub
# Import wait_for_seconds()
from mindstorms.control import wait_for_seconds


# Beep for welcome
hub = MSHub()
hub.speaker.beep()


# Font for the characters 0..9. 
# Each character is two stripes on the 5x5 display
font = [ 
    "99999:99999", "90090:99999", "99909:90999", "90909:99999", "00990:99999", # chars 0,1,2,3,4
    "90999:99909", "99999:99909", "99909:00099", "99099:99099", "90999:99999"  # chars 5,6,7,8,9
]


# Puts `num` (must be 0..99) on the display
# The output is 90 rotated
def decdigits(num) :
    # Split num in two digits and lookup font
    char0 = font[num%10]
    char1 = font[num//10]
    # Create string from two chars with a space (empty stripe) in between
    str = char1 + ":00000:" + char0
    # Put `str` on display
    if hasattr(hub.light_matrix, 'show') :
        hub.light_matrix.show( str )
    else :
        # Robot Inventor has show() but Spike Prime not, so work-around
        for y in range(5) :
            for x in range(5) :
                level = int(str[y*6+x])*11
                hub.light_matrix.set_pixel(x,y,brightness=level)


# List of colors for the status light around the center button
colors = ['azure','blue','cyan','green','orange','pink','red','violet','white','yellow'] # 'black'

# Demo of all numbers 0..99
for ix in range(100) :
    # Print progress to console
    print(ix)
    # Status light maps "tens" to a color
    hub.status_light.on( colors[ix//10] )
    # Show the number 
    decdigits(ix)
    # Beep when ix ends with 9
    if ix%10==9 :
        hub.speaker.beep(note=100, seconds=0.02) # Inventor supports: volume=100
    # Wait till next number
    wait_for_seconds(0.1)
