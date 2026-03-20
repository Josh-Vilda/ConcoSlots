#!/usr/bin/env python3
"""
Raspberry Pi 5 Slot Machine - PRO Arcade Build
MIDDLE REEL PERFECTLY CENTERED + Wide Outer Spacing
Infinite spin → Individual stops → 3-of-a-kind wins
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

# Pins
PINCRANK = 17
PINBUTTONSPIN = 27

# Visuals
FULLSCREEN = True 
SYMBOLFOLDER = ".symbols"
SYMBOLSIZE = (256, 256)  # 200% bigger
REELCOUNT = 3
SPINSPEEDINITIAL = 55    # Fast for big reels
FULLSCREEN = False
FPS = 60
BG_COLOR = (0, 64, 133)
BONUSSYMBOLS = ["concordia.png", "uqat.png", "ottawa.png"]

def setup_inputs(callback):
    if not RUNNING_ON_PI: return []
    try:
        crank = Button(PINCRANK, pull_up=True, bounce_time=0.1)
        crank.when_pressed = callback
        spin_btn = Button(PINBUTTONSPIN, pull_up=True, bounce_time=0.1)
        spin_btn.when_pressed = callback
        return [crank, spin_btn]
    except: return []

def load_symbols():
    if not os.path.exists(SYMBOLFOLDER):
        raise FileNotFoundError(f"mkdir '{SYMBOLFOLDER}' && add 3+ PNGs")
    symbols = []
    for f in os.listdir(SYMBOLFOLDER):
        if f.lower().endswith(('.png','.jpg','.jpeg')):
            path = os.path.join(SYMBOLFOLDER, f)
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, SYMBOLSIZE)
            symbols.append((f, img))
    if len(symbols) < 3:
        raise ValueError(f"Need 3+ symbols (got {len(symbols)})")
    print(f"Loaded: {[n for n,_ in symbols]}")
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
        # FAST INFINITE SPIN
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
        bonus = {s[0] for s in symbols if s[0] in BONUSSYMBOLS}
        return True, "BONUS WINNER!" if names[0] in bonus else "WINNER!"
    return False, ""

def main():
    pygame.init()
    info = pygame.display.Info()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    clock = pygame.time.Clock()
    
    symbols = load_symbols()
    width, height = screen.get_size()
    
    # MIDDLE REEL CENTERED + WIDE OUTER SPACING
    center_x = width // 2
    left_x = center_x - 380
    right_x = center_x + 380
    reel_x = [left_x, center_x, right_x]
    reels = [Reel(symbols, reel_x[i], height//2) for i in range(REELCOUNT)]
    
    spins = wins = 0
    result_label = ""
    next_stop = 0
    
    def lever_pull():
        nonlocal next_stop, spins, wins, result_label
        
        if next_stop == 0:  # SPIN ALL INFINITE
            if any(r.spinning for r in reels): return
            spins += 1
            result_label = ""
            for reel in reels:
                reel.start_spin()
            next_stop = 1
            return
        
        if 1 <= next_stop <= REELCOUNT:  # STOP ONE
            reels[next_stop-1].force_stop()
            next_stop += 1
        
        if next_stop > REELCOUNT:  # WIN CHECK
            is_win, label = evaluate_result(reels, symbols)
            if is_win: wins += 1
            result_label = label
            next_stop = 0
    
    controls = setup_inputs(lever_pull)
    
    # UI
    btn_rect = pygame.Rect(center_x - 140, height - 160, 280, 90)
    font_lg = pygame.font.Font(None, 52)
    font_sm = pygame.font.Font(None, 38)
    
    print("🎰 PRO SLOT MACHINE | SPACE x4: SPIN→STOP1→STOP2→STOP3")
    
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
        
        for reel in reels:
            reel.update(dt)
        
        screen.fill(BG_COLOR)
        for reel in reels:
            reel.draw(screen)
        
        # HUD
        hud = [f"SPINS: {spins} | WINS: {wins}",
               result_label]
        for i, txt in enumerate(hud):
            clr = (255,215,0) if "WIN" in txt else (230,230,255)
            surf = font_sm.render(txt, True, clr)
            screen.blit(surf, (30, 35 + i*42))
        
        # PERFECTLY CENTERED BUTTON
        if next_stop == 0:
            btn_txt, btn_clr = "SPIN ALL!", (0, 255, 80)
        elif 1 <= next_stop <= REELCOUNT:
            btn_txt, btn_clr = f"STOP REEL", (255, 180, 0)

        
        pygame.draw.rect(screen, btn_clr, btn_rect)
        pygame.draw.rect(screen, (255,255,255), btn_rect, 6)
        btn_surf = font_lg.render(btn_txt, True, (25,25,25))
        screen.blit(btn_surf, (btn_rect.centerx-btn_surf.get_width()//2,
                              btn_rect.centery-btn_surf.get_height()//2))
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()
