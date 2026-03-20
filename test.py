from gpiozero import Button
import signal
import sys

def pressed(pin_name):
    print(f"{pin_name} pressed!")

crank = Button(24, pull_up=True, bounce_time=0.1)
crank.when_pressed = lambda: pressed("Crank")

spin = Button(25, pull_up=True, bounce_time=0.1)
spin.when_pressed = lambda: pressed("Spin")

print("Test GPIO 24/25 - press switches, Ctrl+C quit")
signal.pause()
