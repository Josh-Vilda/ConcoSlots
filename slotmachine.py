#!/usr/bin/env python3
"""
Raspberry Pi 5 Slot Machine - PRO Arcade Build (lgpio Edition)
MIDDLE REEL PERFECTLY CENTERED + Wide Outer Spacing
Infinite spin → Individual stops → 3-of-a-kind wins
GPIO/lgpio: Idle=0, Pulled=1 (external pull-up wiring)
"""

import sys
import os
import random
import time
import pygame

# lgpio (Pi-only, desktop fallback)
RUNNING_ON_PI = False
lgpio = None
GPIO_HANDLE = None
PINCRANK = 24
PINBUTTONSPIN = 25
PINBUTTONALT = 22

try:
    import lgpio
    RUNNING_ON_PI = True
    GPIO_HANDLE = lgpio.gpiochip_open(0)  # RPi chip 0
    # Setup inputs: INPUT mode, no internal pull (external handles idle=0)
    lgpio.gpio_claim_input(GPIO_HANDLE, PINCRANK)
    lgpio.gpio_set_pullup(GPIO_HANDLE, PINCRANK, lgpio.NO_PULLUPDOWN)
    lgpio.gpio_claim_input(GPIO_HANDLE, PINBUTTONSPIN)
    lgpio.gpio_set_pullup(GPIO_HANDLE, PINBUTTONSPIN, lgpio.NO_PULLUPDOWN)
    # Alt reserved
    # lgpio.gpio_claim_input(GPIO_HANDLE, PINBUTTONALT)
    # lgpio.gpio_set_pullup(GPIO_HANDLE, PINBUTTONALT, lgpio.NO_PULLUPDOWN)
    print(f"lgpio setup OK: Crank={PINCRANK}, Spin={PINBUTTONSPIN} (idle=0, pulled=1)")
except ImportError:
    print("Desktop mode: lgpio unavailable, use SPACEBAR or SPIN button")
except Exception as e:
    print(f"lgpio setup failed ({e}): Falling back to keyboard/mouse")
    RUNNING_ON_PI = False

# Display & Visuals
FULLSCREEN = True
SYMBOLFOLDER = ".symbols"
SYMBOLSIZE = (256, 256)
REELCOUNT = 3
SPINSPEEDINITIAL = 55
FPS = 60
BG_COLOR = (0, 64, 133)
BONUSSYMBOLS = ["concordia.png", "uqat.png", "ottawa.png"]
BOUNCETIME = 0.05  # Debounce in seconds
last_crank_time = 0
last_spin_time = 0

def load_symbols():
    if not os.path.exists(SYMBOLFOLDER):
        raise FileNotFoundError(f"mkdir '{SYMBOLFOLDER}' && add 3+ PNGs/JPGs")
    symbols = []
    for f in os.listdir(SYMBOLFOLDER):
        if f.lower().endswith(('.png', '.jpg', '.jpeg')):
            path = os.path.join(SYMBOLFOLDER, f)
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, SYMBOLSIZE)
            symbols.append((f, img))
    if len(symbols) < 3:
        raise ValueError(f"Need 3+ symbols (got {len(symbols)})")
    print(f"Loaded symbols: {[n for n, _ in symbols]}")
    return symbols

class Reel:
    def __init__(self, symbols, x, y):
        self.symbols = symbols
        self.x, self.y = x, y
        self.spinning = False
        self.index = 0
        self.offset = 0.0

    def start_spin(self):
        self.spinning = True
        self.index = random.randint(0, len(self.symbols) - 1)

    def force_stop(self):
        self.spinning = False
        self.offset = 0.0

    def update(self, dt):
        if not self.spinning:
            return
        speed = SPINSPEEDINITIAL / 16.67 / FPS * 167
        self.offset += speed * dt
        while self.offset >= 1.0:
            self.offset -= 1.0
            self.index = (self.index + 1) % len(self.symbols)

    def draw(self, surface):
        img = self.symbols[self.index][1]
        rect = img.get_rect(center=(self.x, self.y))
        
        if self.spinning:
            scroll_surf = pygame.Surface(SYMBOLSIZE, pygame.SRCALPHA)
            scroll_y = int(self.offset * SYMBOLSIZE[1])
            scroll_surf.blit(img, (0, -scroll_y))
            next_img = self.symbols[(self.index + 1) % len(self.symbols)][1]
            scroll_surf.blit(next_img, (0, SYMBOLSIZE[1] - scroll_y))
            surface.blit(scroll_surf, rect)
        else:
            surface.blit(img, rect)
        
        color = (0, 255, 100) if not self.spinning else (255, 255, 100)
        pygame.draw.rect(surface, color, rect.inflate(24, 24), 6)

    def result_name(self):
        return self.symbols[self.index][0]

def evaluate_result(reels, symbols):
    names = [r.result_name() for r in reels]
    if all(n == names[0] for n in names):
        bonus_set = {s[0] for s in symbols if s[0] in BONUSSYMBOLS}
        return True, "BONUS WINNER!" if names[0] in bonus_set else "WINNER!"
    return False, ""

def check_gpio_trigger(pin):
    """Debounced rising edge detect: idle=0 → pulled=1"""
    global last_crank_time, last_spin_time
    now = time.time()
    
    if pin == PINCRANK and (now - last_crank_time) < BOUNCETIME:
        return False
    if pin == PINBUTTONSPIN and (now - last_spin_time) < BOUNCETIME:
        return False
    
    if RUNNING_ON_PI and lgpio:
        state = lgpio.gpio_read(GPIO_HANDLE, pin)
        if state == 1:  # Pulled high
            if pin == PINCRANK:
                last_crank_time = now
            else:
                last_spin_time = now
            return True
    return False

def main():
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN if FULLSCREEN else 0)
    pygame.display.set_caption("PRO Slot Machine (lgpio)")
    clock = pygame.time.Clock()
    
    symbols = load_symbols()
    width, height = screen.get_size()
    
    center_x = width // 2
    left_x = center_x - 380
    right_x = center_x + 380
    reel_x = [left_x, center_x, right_x]
    reels = [Reel(symbols, reel_x[i], height // 2) for i in range(REELCOUNT)]
    
    spins = wins = 0
    result_label = ""
    next_stop = 0
    
    def lever_pull():
        nonlocal next_stop, spins, wins, result_label
        
        if next_stop == 0:  # SPIN ALL
            if any(r.spinning for r in reels):
                return
            spins += 1
            result_label = ""
            for reel in reels:
                reel.start_spin()
            next_stop = 1
            return
        
        if 1 <= next_stop <= REELCOUNT:  # STOP ONE
            reels[next_stop - 1].force_stop()
            next_stop += 1
        
        if next_stop > REELCOUNT:  # WIN CHECK & LOOP
            is_win, label = evaluate_result(reels, symbols)
            if is_win:
                wins += 1
            result_label = label
            next_stop = 0
    
    # UI
    btn_rect = pygame.Rect(center_x - 140, height - 160, 280, 90)
    font_lg = pygame.font.Font(None, 52)
    font_sm = pygame.font.Font(None, 38)
    
    print("🎰 PRO SLOT MACHINE (lgpio) | GPIO Crank/Buttons (0→1), SPACE, CLICK | ESC=Quit")
    
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        
        # GPIO Polling (non-blocking)
        if RUNNING_ON_PI:
            if check_gpio_trigger(PINCRANK) or check_gpio_trigger(PINBUTTONSPIN):
                lever_pull()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    lever_pull()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if btn_rect.collidepoint(event.pos):
                    lever_pull()
        
        for reel in reels:
            reel.update(dt)
        
        screen.fill(BG_COLOR)
        for reel in reels:
            reel.draw(screen)
        
        # HUD
        hud = [f"SPINS: {spins} | WINS: {wins}", result_label]
        for i, txt in enumerate(hud):
            clr = (255, 215, 0) if "WIN" in txt else (230, 230, 255)
            surf = font_sm.render(txt, True, clr)
            screen.blit(surf, (30, 35 + i * 42))
        
        # SPIN Button
        if next_stop == 0:
            btn_txt, btn_clr = "SPIN ALL!", (0, 255, 80)
        elif 1 <= next_stop <= REELCOUNT:
            btn_txt, btn_clr = f"STOP REEL {next_stop}", (255, 180, 0)
        
        pygame.draw.rect(screen, btn_clr, btn_rect)
        pygame.draw.rect(screen, (255, 255, 255), btn_rect, 6)
        btn_surf = font_lg.render(btn_txt, True, (25, 25, 25))
        screen.blit(btn_surf, (btn_rect.centerx - btn_surf.get_width() // 2,
                               btn_rect.centery - btn_surf.get_height() // 2))
        
        pygame.display.flip()
    
    # Cleanup lgpio
    if RUNNING_ON_PI and lgpio and GPIO_HANDLE:
        lgpio.gpiochip_close(GPIO_HANDLE)
    pygame.quit()

if __name__ == "__main__":
    main()
