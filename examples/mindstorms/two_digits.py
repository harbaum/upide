# Import the low level hub module
import hub
# Import for time.sleep_ms
import time

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
    hub.display.show( hub.Image(str) )

# Demo of all numbers 0..99
for ix in range(100) :
    decdigits(ix)
    time.sleep_ms(200)
