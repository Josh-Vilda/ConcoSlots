#!/usr/bin/env python3
import lgpio
import time

h = lgpio.gpiochip_open(0)  # /dev/gpiochip0
lgpio.gpio_claim_input(h, 24)  # Pin24
lgpio.gpio_claim_input(h, 25)  # Pin25

print("LGPIO Test: Press buttons on GPIO24/25 (to GND). Ctrl+C quit.")
try:
    while True:
        val24 = lgpio.gpio_read(h, 24)
        val25 = lgpio.gpio_read(h, 25)
        print(f"GPIO24: {val24}, GPIO25: {val25}", end='\r')
        time.sleep(0.1)
except KeyboardInterrupt:
    lgpio.gpiochip_close(h)
