#!/usr/bin/env python3
"""
GPIO Pin Scanner - Detects EXACT pin for lever/button presses
Monitors all BCM GPIO 0-27. Prints pin # on state change (LOW = pressed).
Press Ctrl+C to quit.
"""

import time
import RPi.GPIO as GPIO  # sudo required

# BCM numbering
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Monitor pins 0-27 (common GPIOs)
MONITOR_PINS = list(range(28))

# Setup all as inputs with pull-up
for pin in MONITOR_PINS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("🔍 GPIO Scanner Active (BCM pins 0-27)")
print("Pull lever/press button → sees LOW on that pin!")
print("Expected: ~24 (crank), ~25 (button) or spec 17/27")
print("Ctrl+C to quit\n")

last_states = {pin: GPIO.input(pin) for pin in MONITOR_PINS}

try:
    while True:
        for pin in MONITOR_PINS:
            current = GPIO.input(pin)
            if current != last_states[pin]:
                edge = "PRESSED" if current == 0 else "RELEASED"
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] GPIO {pin:2d} {edge} (state={current})")
                last_states[pin] = current
        time.sleep(0.01)  # 100Hz poll, low CPU
except KeyboardInterrupt:
    print("\n👋 Scanner stopped")

GPIO.cleanup()
