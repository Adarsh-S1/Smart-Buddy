from gpiozero import LED
import time

# Define LEDs
#cam_light = LED(17)
headlight_right = LED(18)
headlight_left = LED(27)
#sp_light = LED(9)

# Blink LEDs
while True:
    #cam_light.on()
    headlight_right.on()
    headlight_left.on()
    #sp_light.on()
    print("LEDs ON")
    time.sleep(1)

    #cam_light.off()
    headlight_right.off()
    headlight_left.off()
    #sp_light.off()
    print("LEDs OFF")
    time.sleep(1)

