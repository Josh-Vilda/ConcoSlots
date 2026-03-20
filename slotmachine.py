#!/usr/bin/env python3
"""
Raspberry Pi 5 Slot Machine - PORTRAIT MODE Arcade Build
Reels stacked VERTICALLY for tall screens (e.g., rotated monitor)
GPIO crank/button support + desktop fallback (SPACEBAR)
Infinite free-play spins with 3-of-a-kind wins/bonus.
"""

import sys
import os
import random
import pygame

# GPIO (Windows safe)
try:
    from gpiozero import Button
    RUNNING_ON_PI = True
except ImportError:
    RUNNING_ON_PI = False
    Button = None

# Pins - GPIO BCM
PINCRANK = 24
PINBUTTONSPIN = 25

# Portrait Optimized
FULLSCREEN = True
SYMBOLFOLDER = ".symbols"
SYMBOLSIZE = (280, 280)  # Square, fits portrait height
REELCOUNT = 3
SPINSPEEDINITIAL = 50
FPS = 60
BG_COLOR = (0, 64, 133)
BONUSSYMBOLS = ["concordia.png", "uqat.png", "ottawa.png"]

def setup_inputs(callback):
    if not RUNNING_ON_PI: 
        print("Desktop mode: Use SPACEBAR or mouse button")
        return []
    try:
        crank = Button(PINCRANK, pull_up=True, bounce_time=0.1)
        crank.when_pressed = callback
        spin_btn = Button(PINBUTTONSPIN, pull_up=True, bounce_time=0.1)
        spin_btn.when_pressed = callback
        print("GPIO buttons active on pins 24/25")
        return [crank, spin_btn]
    except Exception as e:
        print(f"GPIO setup failed: {e}")
        return []

def load_symbols():
    if not os.path.exists(SYMBOLFOLDER):
        raise FileNotFoundError(f"mkdir '{SYMBOLFOLDER}' & add 3+ PNGs")
    symbols = []
    for f in os.listdir(SYMBOLFOLDER):
        if f.lower().endswith(('.png','.jpg','.jpeg')):
            path = os.path.join(SYMBOLFOLDER, f)
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, SYMBOLSIZE)
            symbols.append((f, img))
    if len(symbols) < 3:
        raise ValueError(f"Need 3+ symbols (got {len(symbols)})")
    print(f"Loaded symbols: {[n for n,_ in symbols]}")
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
        self.index = random.randint(0, len(self.symbols)-1)

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
        
        # Glow border
        color = (0, 255, 100) if not self.spinning else (255, 255, 100)
        pygame.draw.rect(surface, color, rect.inflate(20, 20), 6)

    def result_name(self):
        return self.symbols[self.index][0]

def evaluate_result(reels, symbols):
    names = [r.result_name() for r in reels]
    if all(n == names[0] for n in names):
        bonus = any(s[0] in BONUSSYMBOLS for s in symbols)
        return True, "BONUS WIN!" if bonus else "WIN!"
    return False, ""

def main():
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("Portrait Slot Machine")
    clock = pygame.time.Clock()
    
    symbols = load_symbols()
    width, height = screen.get_size()
    print(f"Portrait mode: {width}x{height}")
    
    # VERTICAL reel stack - portrait optimized
    center_x = width // 2
    reel_spacing = height * 0.22  # ~22% per reel section
    reel_y = [reel_spacing * 1.1, reel_spacing * 2.1, reel_spacing * 3.1]  # Top, mid, bottom
    reels = [Reel(symbols, center_x, reel_y[i]) for i in range(REELCOUNT)]
    
    spins = wins = 0
    result_label = ""
    next_stop = 0
    
    def lever_pull():
        nonlocal next_stop, spins, wins, result_label
        if next_stop == 0:
            if any(r.spinning for r in reels): return
            spins += 1
            result_label = ""
            for reel in reels: reel.start_spin()
            next_stop = 1
            return
        if 1 <= next_stop <= REELCOUNT:
            reels[next_stop-1].force_stop()
            next_stop += 1
        if next_stop > REELCOUNT:
            is_win, label = evaluate_result(reels, symbols)
            if is_win: wins += 1
            result_label = label
            next_stop = 0
    
    controls = setup_inputs(lever_pull)
    
    # Portrait UI - bottom heavy
    btn_rect = pygame.Rect(center_x - 160, height - 140, 320, 100)
    font_lg = pygame.font.Font(None, 60)
    font_sm = pygame.font.Font(None, 45)
    
    print("🎰 Portrait Slot Machine | SPACE: Spin/Stop sequence | ESC: Quit")
    
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: running = False
                elif event.key == pygame.K_SPACE: lever_pull()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if btn_rect.collidepoint(event.pos): lever_pull()
        
        for reel in reels: reel.update(dt)
        
        screen.fill(BG_COLOR)
        for reel in reels: reel.draw(screen)
        
        # HUD - top left
        hud = [f"SPINS: {spins}  WINS: {wins}", result_label]
        for i, txt in enumerate(hud):
            clr = (255,215,0) if "WIN" in txt else (230,230,255)
            surf = font_sm.render(txt, True, clr)
            screen.blit(surf, (30, 30 + i*55))
        
        # Big bottom button
        if next_stop == 0:
            btn_txt, btn_clr = "SPIN ALL!", (0, 255, 80)
        elif 1 <= next_stop <= REELCOUNT:
            btn_txt, btn_clr = f"STOP REEL {next_stop}", (255, 180, 0)
        
        pygame.draw.rect(screen, btn_clr, btn_rect)
        pygame.draw.rect(screen, (255,255,255), btn_rect, 8)
        btn_surf = font_lg.render(btn_txt, True, (30,30,30))
        screen.blit(btn_surf, (btn_rect.centerx - btn_surf.get_width()//2,
                               btn_rect.centery - btn_surf.get_height()//2))
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()
