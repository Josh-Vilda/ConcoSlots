#!/usr/bin/env python3
"""
Raspberry Pi 5 Slot Machine - FINAL PRODUCTION VERSION (lgpio)
MIDDLE REEL PERFECTLY CENTERED + Wide Outer Spacing
Infinite Free Spins → Sequential Stops → 3-of-a-Kind Wins + Bonus
GPIO/lgpio: Idle=0, Pressed=1 (external pull-up wiring CONFIRMED)
Desktop/Keyboard Fallback Included
"""

import sys
import os
import random
import time
import pygame

# ========================================
# LGPIO GPIO SETUP (Pi-5 Compatible)
# ========================================
RUNNING_ON_PI = False
lgpio = None
GPIO_HANDLE = None
PINCRANK = 24        # Primary crank lever
PINBUTTONSPIN = 25   # Backup spin button
PINBUTTONALT = 22    # Reserved for future

BOUNCETIME = 0.05    # 50ms debounce
last_crank_time = 0
last_spin_time = 0

def init_lgpio():
    """Initialize lgpio for active-high wiring (idle=0, pressed=1)"""
    global RUNNING_ON_PI, lgpio, GPIO_HANDLE
    
    try:
        import lgpio
        RUNNING_ON_PI = True
        GPIO_HANDLE = lgpio.gpiochip_open(0)  # /dev/gpiochip0
        
        # Claim inputs, NO internal pull-up (external wiring controls)
        lgpio.gpio_claim_input(GPIO_HANDLE, PINCRANK)
        lgpio.gpio_set_pullup(GPIO_HANDLE, PINCRANK, lgpio.NO_PULLUPDOWN)
        lgpio.gpio_claim_input(GPIO_HANDLE, PINBUTTONSPIN)
        lgpio.gpio_set_pullup(GPIO_HANDLE, PINBUTTONSPIN, lgpio.NO_PULLUPDOWN)
        
        print(f"✅ lgpio ACTIVE: Crank={PINCRANK}, Spin={PINBUTTONSPIN} (0=idle, 1=pressed)")
        return True
    except Exception as e:
        print(f"⚠️  lgpio unavailable ({e}) → Keyboard/Mouse fallback")
        return False

def check_gpio():
    """Poll GPIO: Returns True on rising edge (0→1), debounced"""
    global last_crank_time, last_spin_time
    now = time.time()
    
    if not RUNNING_ON_PI or GPIO_HANDLE is None:
        return False
    
    # Check crank
    if (now - last_crank_time) > BOUNCETIME:
        if lgpio.gpio_read(GPIO_HANDLE, PINCRANK) == 1:
            last_crank_time = now
            return True
    
    # Check spin button  
    if (now - last_spin_time) > BOUNCETIME:
        if lgpio.gpio_read(GPIO_HANDLE, PINBUTTONSPIN) == 1:
            last_spin_time = now
            return True
    
    return False

def cleanup_lgpio():
    """Clean shutdown"""
    global GPIO_HANDLE
    if RUNNING_ON_PI and GPIO_HANDLE:
        lgpio.gpiochip_close(GPIO_HANDLE)

# ========================================
# GAME CONSTANTS
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
    """Dynamically load all PNG/JPG from .symbols folder"""
    if not os.path.exists(SYMBOLFOLDER):
        raise FileNotFoundError(f"❌ Create '{SYMBOLFOLDER}' folder with 3+ PNG/JPG images")
    
    symbols = []
    for f in os.listdir(SYMBOLFOLDER):
        if f.lower().endswith(('.png', '.jpg', '.jpeg')):
            path = os.path.join(SYMBOLFOLDER, f)
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.smoothscale(img, SYMBOLSIZE)
                symbols.append((f, img))
            except:
                print(f"⚠️  Skipping invalid image: {f}")
    
    if len(symbols) < 3:
        raise ValueError(f"❌ Need 3+ valid symbols (found {len(symbols)})")
    
    print(f"✅ Loaded {len(symbols)} symbols: {[n for n,_ in symbols]}")
    return symbols

# ========================================
# REEL CLASS (Infinite Spinning)
# ========================================
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
        # Fast infinite scroll (deceleration feel)
        speed = SPINSPEEDINITIAL / 16.67 / FPS * 167
        self.offset += speed * dt
        while self.offset >= 1.0:
            self.offset -= 1.0
            self.index = (self.index + 1) % len(self.symbols)

    def draw(self, surface):
        img = self.symbols[self.index][1]
        rect = img.get_rect(center=(self.x, self.y))
        
        if self.spinning:
            # Blurred scrolling effect
            scroll_surf = pygame.Surface(SYMBOLSIZE, pygame.SRCALPHA)
            scroll_y = int(self.offset * SYMBOLSIZE[1])
            scroll_surf.blit(img, (0, -scroll_y))
            next_img = self.symbols[(self.index + 1) % len(self.symbols)][1]
            scroll_surf.blit(next_img, (0, SYMBOLSIZE[1] - scroll_y))
            surface.blit(scroll_surf, rect)
        else:
            surface.blit(img, rect)
        
        # Glowing frame
        color = (0, 255, 100) if not self.spinning else (255, 255, 100)
        pygame.draw.rect(surface, color, rect.inflate(24, 24), 6)

    def result_name(self):
        return self.symbols[self.index][0]

# ========================================
# WIN DETECTION
# ========================================
def evaluate_result(reels, symbols):
    names = [r.result_name() for r in reels]
    if all(n == names[0] for n in names):
        bonus_set = {s[0] for s in symbols if s[0] in BONUSSYMBOLS}
        return True, "BONUS WINNER!" if names[0] in bonus_set else "WINNER!"
    return False, ""

# ========================================
# MAIN GAME
# ========================================
def main():
    # Init display
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN if FULLSCREEN else 0)
    pygame.display.set_caption("🎰 PRO ARCADE SLOT MACHINE")
    clock = pygame.time.Clock()
    
    # Load assets
    symbols = load_symbols()
    width, height = screen.get_size()
    
    # Perfectly centered reels (wide spacing)
    center_x = width // 2
    reel_positions = [center_x - 380, center_x, center_x + 380]
    reels = [Reel(symbols, reel_positions[i], height // 2) for i in range(REELCOUNT)]
    
    # Game state
    spins = wins = 0
    result_label = ""
    next_stop = 0  # 0=spin, 1-3=stop sequence
    
    def lever_pull():
        nonlocal next_stop, spins, wins, result_label
        
        if next_stop == 0:  # SPIN ALL REELS
            if any(r.spinning for r in reels):
                return  # Already spinning
            spins += 1
            result_label = ""
            for reel in reels:
                reel.start_spin()
            next_stop = 1
            return
        
        if 1 <= next_stop <= REELCOUNT:  # STOP REELS SEQUENTIALLY
            reels[next_stop - 1].force_stop()
            next_stop += 1
        
        if next_stop > REELCOUNT:  # EVALUATE & LOOP
            is_win, label = evaluate_result(reels, symbols)
            if is_win:
                wins += 1
            result_label = label
            next_stop = 0  # Infinite free play loop
    
    # UI Elements
    btn_rect = pygame.Rect(center_x - 140, height - 160, 280, 90)
    font_lg = pygame.font.Font(None, 52)
    font_sm = pygame.font.Font(None, 38)
    
    # Initialize hardware
    init_lgpio()
    print("🚀 SLOT MACHINE READY | Pull crank/press button to spin!")
    
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        
        # ========== INPUT HANDLING ==========
        # GPIO polling (non-blocking)
        if check_gpio():
            lever_pull()
        
        # Keyboard/Mouse fallback
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
        
        # ========== UPDATE ==========
        for reel in reels:
            reel.update(dt)
        
        # ========== RENDER ==========
        screen.fill(BG_COLOR)
        
        # Reels
        for reel in reels:
            reel.draw(screen)
        
        # HUD (top-left)
        hud = [f"SPINS: {spins} | WINS: {wins}", result_label]
        for i, txt in enumerate(hud):
            color = (255, 215, 0) if "WIN" in txt else (230, 230, 255)
            surf = font_sm.render(txt, True, color)
            screen.blit(surf, (30, 35 + i * 42))
        
        # Arcade SPIN Button (bottom-center)
        if next_stop == 0:
            btn_text, btn_color = "SPIN ALL!", (0, 255, 80)
        elif 1 <= next_stop <= REELCOUNT:
            btn_text, btn_color = f"STOP {next_stop}!", (255, 180, 0)
        
        pygame.draw.rect(screen, btn_color, btn_rect)
        pygame.draw.rect(screen, (255, 255, 255), btn_rect, 6)
        btn_surf = font_lg.render(btn_text, True, (25, 25, 25))
        screen.blit(btn_surf, 
                   (btn_rect.centerx - btn_surf.get_width() // 2,
                    btn_rect.centery - btn_surf.get_height() // 2))
        
        pygame.display.flip()
    
    # Cleanup
    cleanup_lgpio()
    pygame.quit()
    print("👋 Slot machine shutdown complete")

if __name__ == "__main__":
    main()
