from gpiozero import Motor, LED
import os, time
from gpiozero.pins.native import NativeFactory
from gpiozero import Device

# edgetpu remains for reference (if Coral USB Accelerator is connected)
edgetpu = 0

# Motor pin definitions:
# Motor1: forward -> pin 8, backward -> pin 11.
# Motor2: to match your original code, we define forward as pin 15 and backward as pin 14.
motor1 = Motor(forward=8, backward=11)
motor2 = Motor(forward=15, backward=14)

# LED definitions for various lights
cam_light = LED(17)
headlight_right = LED(18)
headlight_left = LED(27)
sp_light = LED(9)
forward_indicator = LED(22)  

def init_gpio():
    # With gpiozero, device initialization is done upon object creation.
    # This function is retained for compatibility.
    print("Initializing GPIOs")
    sp_light.off()
    cam_light.off()
    headlight_left.off()
    headlight_right.off()

def back():
    print("moving back!!!!!!")
    motor1.backward()
    motor2.backward()

def forward():
    motor1.forward()
    motor2.forward()

def right():
    # Right turn: Motor1 goes forward and Motor2 goes backward.
    motor1.forward()
    motor2.backward()

def left():
    # Left turn: Motor1 goes backward and Motor2 goes forward.
    motor1.backward()
    motor2.forward()

def stop():
    motor1.stop()
    motor2.stop()

def speak_tts(text, gender):
    cmd = "python /var/www/html/earthrover/speaker/speaker_tts.py '" + text + "' " + gender + " &"
    os.system(cmd)

def camera_light(state):
    if state == "ON":
        cam_light.on()
    else:
        cam_light.off()

def left_light(state):
    if state=="ON":
        headlight_left.on()
    else:
        headlight_left.off()

def right_light(state):
    if state=="ON":
        headlight_right.on()
    else:
        headlight_right.off()

# def head_lights(state):
#     if state == "ON":
#         headlight_left.on()
#         headlight_right.off()
#     else:
#         headlight_left.off()
#         headlight_right.on()

def red_light(state):
    if state == "ON":
        sp_light.on()
    else:
        sp_light.off()
        
def forward_light(state):
    if state=="ON":
        forward_indicator.on()
    else:
        forward_indicator.off()
