#!/usr/bin/env python3
"""
Raspberry Pi 5 Slot Machine - FINAL PRODUCTION VERSION (lgpio FIXED)
MIDDLE REEL PERFECTLY CENTERED + Wide Outer Spacing
Infinite Free Spins → Sequential Stops → 3-of-a-Kind Wins + Bonus
GPIO/lgpio: Idle=0, Pressed=1 → WAITING_FOR_RELEASE FIXED
Desktop/Keyboard Fallback Included
"""

import sys
import os
import random
import time
import pygame

# ========================================
# LGPIO GPIO SETUP (Edge-Triggered: Press→Release)
# ========================================
RUNNING_ON_PI = False
lgpio = None
GPIO_HANDLE = None
PINCRANK = 24        
PINBUTTONSPIN = 25   
PINBUTTONALT = 22    

# State tracking: Wait for 0→1→0 cycle
crank_pressed = False
spin_pressed = False
waiting_for_release_crank = False
waiting_for_release_spin = False

def init_lgpio():
    """Initialize lgpio for complete press-release cycle"""
    global RUNNING_ON_PI, lgpio, GPIO_HANDLE
    
    try:
        import lgpio
        RUNNING_ON_PI = True
        GPIO_HANDLE = lgpio.gpiochip_open(0)
        
        lgpio.gpio_claim_input(GPIO_HANDLE, PINCRANK)
        lgpio.gpio_set_pullup(GPIO_HANDLE, PINCRANK, lgpio.NO_PULLUPDOWN)
        lgpio.gpio_claim_input(GPIO_HANDLE, PINBUTTONSPIN)
        lgpio.gpio_set_pullup(GPIO_HANDLE, PINBUTTONSPIN, lgpio.NO_PULLUPDOWN)
        
        print(f"✅ lgpio EDGE-TRIGGER: Crank={PINCRANK}, Spin={PINBUTTONSPIN}")
        print("   (0→1→0 cycle required per trigger)")
        return True
    except Exception as e:
        print(f"⚠️  lgpio unavailable ({e}) → Keyboard fallback")
        return False

def check_gpio():
    """Detect complete 0→1→0 cycle (ignores hold)"""
    global crank_pressed, spin_pressed, waiting_for_release_crank, waiting_for_release_spin
    
    if not RUNNING_ON_PI or GPIO_HANDLE is None:
        return False
    
    # Read current states
    crank_state = lgpio.gpio_read(GPIO_HANDLE, PINCRANK)
    spin_state = lgpio.gpio_read(GPIO_HANDLE, PINBUTTONSPIN)
    
    # CRANK: 0→1 (rising edge)
    if not crank_pressed and crank_state == 1:
        crank_pressed = True
        waiting_for_release_crank = True
    
    # CRANK: 1→0 (falling edge = complete press)
    elif crank_pressed and crank_state == 0 and waiting_for_release_crank:
        crank_pressed = False
        waiting_for_release_crank = False
        return True  # TRIGGER!
    
    # SPIN BUTTON: Same logic
    if not spin_pressed and spin_state == 1:
        spin_pressed = True
        waiting_for_release_spin = True
    
    elif spin_pressed and spin_state == 0 and waiting_for_release_spin:
        spin_pressed = False
        waiting_for_release_spin = False
        return True  # TRIGGER!
    
    return False

def cleanup_lgpio():
    global GPIO_HANDLE
    if RUNNING_ON_PI and GPIO_HANDLE:
        lgpio.gpiochip_close(GPIO_HANDLE)

# ========================================
# GAME CONSTANTS (Unchanged)
# ========================================
FULLSCREEN = True
SYMBOLFOLDER = ".symbols"
SYMBOLSIZE = (256, 256)
REELCOUNT = 3
SPINSPEEDINITIAL = 55
FPS = 60
BG_COLOR = (0, 64, 133)
BONUSSYMBOLS = ["concordia.png", "uqat.png", "ottawa.png"]

def load_symbols():
    if not os.path.exists(SYMBOLFOLDER):
        raise FileNotFoundError(f"❌ Create '{SYMBOLFOLDER}' with 3+ PNG/JPGs")
    
    symbols = []
    for f in os.listdir(SYMBOLFOLDER):
        if f.lower().endswith(('.png', '.jpg', '.jpeg')):
            path = os.path.join(SYMBOLFOLDER, f)
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.smoothscale(img, SYMBOLSIZE)
                symbols.append((f, img))
            except:
                print(f"⚠️  Skipping: {f}")
    
    if len(symbols) < 3:
        raise ValueError(f"❌ Need 3+ symbols (got {len(symbols)})")
    print(f"✅ {len(symbols)} symbols loaded")
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
        if not self.spinning: return
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

# ========================================
# MAIN LOOP
# ========================================
def main():
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN if FULLSCREEN else 0)
    pygame.display.set_caption("🎰 PRO ARCADE SLOT (Press-Release Fixed)")
    clock = pygame.time.Clock()
    
    symbols = load_symbols()
    width, height = screen.get_size()
    
    center_x = width // 2
    reel_positions = [center_x - 380, center_x, center_x + 380]
    reels = [Reel(symbols, reel_positions[i], height // 2) for i in range(REELCOUNT)]
    
    spins = wins = 0
    result_label = ""
    next_stop = 0
    
    def lever_pull():
        nonlocal next_stop, spins, wins, result_label
        
        if next_stop == 0:  # SPIN!
            if any(r.spinning for r in reels): return
            spins += 1
            result_label = ""
            for reel in reels: reel.start_spin()
            next_stop = 1
            return
        
        if 1 <= next_stop <= REELCOUNT:  # STOP ONE BY ONE
            reels[next_stop - 1].force_stop()
            next_stop += 1
        
        if next_stop > REELCOUNT:  # WIN CHECK → LOOP
            is_win, label = evaluate_result(reels, symbols)
            if is_win: wins += 1
            result_label = label
            next_stop = 0
    
    # UI
    btn_rect = pygame.Rect(center_x - 140, height - 160, 280, 90)
    font_lg = pygame.font.Font(None, 52)
    font_sm = pygame.font.Font(None, 38)
    
    init_lgpio()
    print("🚀 FIXED: Complete press-release cycle required!")
    
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        
        # GPIO: Only triggers after full 0→1→0
        if check_gpio():
            lever_pull()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
                elif event.key == pygame.K_SPACE: lever_pull()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if btn_rect.collidepoint(event.pos): lever_pull()
        
        # Update
        for reel in reels: reel.update(dt)
        
        # Render
        screen.fill(BG_COLOR)
        for reel in reels: reel.draw(screen)
        
        # HUD
        hud = [f"SPINS: {spins} | WINS: {wins}", result_label]
        for i, txt in enumerate(hud):
            color = (255, 215, 0) if "WIN" in txt else (230, 230, 255)
            surf = font_sm.render(txt, True, color)
            screen.blit(surf, (30, 35 + i * 42))
        
        # Button
        if next_stop == 0:
            btn_text, btn_color = "SPIN ALL!", (0, 255, 80)
        else:
            btn_text, btn_color = f"STOP {next_stop}!", (255, 180, 0)
        
        pygame.draw.rect(screen, btn_color, btn_rect)
        pygame.draw.rect(screen, (255, 255, 255), btn_rect, 6)
        btn_surf = font_lg.render(btn_text, True, (25, 25, 25))
        screen.blit(btn_surf, (btn_rect.centerx - btn_surf.get_width() // 2,
                               btn_rect.centery - btn_surf.get_height() // 2))
        
        pygame.display.flip()
    
    cleanup_lgpio()
    pygame.quit()

if __name__ == "__main__":
    main()
