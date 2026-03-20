#!/usr/bin/env python3
"""
Raspberry Pi 5 Slot Machine - PRO Arcade Build (GPIO Fixed)
MIDDLE REEL PERFECTLY CENTERED + Wide Outer Spacing
Infinite spin → Individual stops → 3-of-a-kind wins
GPIO: Idle=0, Pulled=1 (external pull-up wiring)
"""

import sys
import os
import random
import pygame

# GPIO (Windows/Desktop safe fallback)
try:
    from gpiozero import Button
    RUNNING_ON_PI = True
except ImportError:
    RUNNING_ON_PI = False
    Button = None

# GPIO Pins (BCM numbering)
PINCRANK = 24
PINBUTTONSPIN = 25
PINBUTTONALT = 22  # Reserved

# Display & Visuals
FULLSCREEN = True
SYMBOLFOLDER = ".symbols"
SYMBOLSIZE = (256, 256)
REELCOUNT = 3
SPINSPEEDINITIAL = 55
FPS = 60
BG_COLOR = (0, 64, 133)
BONUSSYMBOLS = ["concordia.png", "uqat.png", "ottawa.png"]

def setup_inputs(callback):
    """Setup GPIO buttons for external pull-up wiring: idle low=0, active high=1"""
    if not RUNNING_ON_PI:
        print("Desktop mode: Use SPACEBAR or on-screen SPIN button")
        return []
    try:
        # pull_up=False: No internal pull-up (matches external wiring)
        # active_state='active_high': Triggers when pin=1 (pulled)
        crank = Button(PINCRANK, pull_up=False, bounce_time=0.1, active_state='active_high')
        crank.when_activated = callback  # Fires on active (high=1)

        spin_btn = Button(PINBUTTONSPIN, pull_up=False, bounce_time=0.1, active_state='active_high')
        spin_btn.when_activated = callback

        # Alt button reserved
        # alt_btn = Button(PINBUTTONALT, pull_up=False, bounce_time=0.1, active_state='active_high')
        # alt_btn.when_activated = callback

        print(f"GPIO setup: Crank={PINCRANK}, Spin={PINBUTTONSPIN} (idle=0, pulled=1)")
        return [crank, spin_btn]
    except Exception as e:
        print(f"GPIO setup failed ({e}): Falling back to keyboard/mouse")
        return []

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
        # Infinite fast spin with deceleration simulation
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
        
        # Dynamic frame glow
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

def main():
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN if FULLSCREEN else 0)
    pygame.display.set_caption("PRO Slot Machine")
    clock = pygame.time.Clock()
    
    symbols = load_symbols()
    width, height = screen.get_size()
    
    # Perfectly centered reels with wide spacing
    center_x = width // 2
    left_x = center_x - 380
    right_x = center_x + 380
    reel_x = [left_x, center_x, right_x]
    reels = [Reel(symbols, reel_x[i], height // 2) for i in range(REELCOUNT)]
    
    spins = wins = 0
    result_label = ""
    next_stop = 0
    
    def lever_pull(btn=None):
        nonlocal next_stop, spins, wins, result_label
        
        # GPIO filter: only act if active (pin=1)
        if RUNNING_ON_PI and btn and not btn.is_active:
            return
        
        if next_stop == 0:  # SPIN ALL (infinite free play)
            if any(r.spinning for r in reels):
                return
            spins += 1
            result_label = ""
            for reel in reels:
                reel.start_spin()
            next_stop = 1
            return
        
        if 1 <= next_stop <= REELCOUNT:  # Sequential stops
            reels[next_stop - 1].force_stop()
            next_stop += 1
        
        if next_stop > REELCOUNT:  # Evaluate win
            is_win, label = evaluate_result(reels, symbols)
            if is_win:
                wins += 1
            result_label = label
            next_stop = 0  # Auto-loop to next spin
    
    controls = setup_inputs(lever_pull)
    
    # UI Elements
    btn_rect = pygame.Rect(center_x - 140, height - 160, 280, 90)
    font_lg = pygame.font.Font(None, 52)
    font_sm = pygame.font.Font(None, 38)
    
    print("🎰 PRO SLOT MACHINE | Controls: GPIO Crank/Buttons, SPACEBAR, CLICK SPIN | ESC=Quit")
    
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        
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
        
        # Update reels
        for reel in reels:
            reel.update(dt)
        
        # Render
        screen.fill(BG_COLOR)
        for reel in reels:
            reel.draw(screen)
        
        # HUD
        hud = [f"SPINS: {spins} | WINS: {wins}", result_label]
        for i, txt in enumerate(hud):
            clr = (255, 215, 0) if "WIN" in txt else (230, 230, 255)
            surf = font_sm.render(txt, True, clr)
            screen.blit(surf, (30, 35 + i * 42))
        
        # On-screen SPIN button (fallback)
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
    
    # Cleanup
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
