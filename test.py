import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(25, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Test GPIO24/25: Press buttons (to GND). Ctrl+C to quit.")
try:
    while True:
        c24 = GPIO.input(24)
        c25 = GPIO.input(25)
        if c24 == 0 or c25 == 0:
            print(f"Pin24: {c24}, Pin25: {c25} PRESSED!")
            time.sleep(0.2)  # Debounce
        time.sleep(0.01)
except KeyboardInterrupt:
    GPIO.cleanup()
