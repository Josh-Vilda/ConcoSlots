#!/usr/bin/env python3
"""
Raspberry Pi 5 Slot Machine - NATIVE LGPIO w/ PULL-UP (Complete Refactor)
MIDDLE REEL PERFECTLY CENTERED + Wide Outer Spacing
Infinite spin → Individual stops → 3-of-a-kind wins
GPIO24/25: 1=Idle, 0=Pressed (Pull-up enabled)
"""
import sys
import os
import random
import pygame
import lgpio  # Native Pi5 GPIO library

# GPIO Pins
PIN_CRANK = 24
PIN_BUTTON_SPIN = 25
gpio_handle = None

# Visuals & Game
FULLSCREEN = True
SYMBOL_FOLDER = ".symbols"
SYMBOL_SIZE = (256, 256)
REEL_COUNT = 3
SPIN_SPEED_INITIAL = 55
FPS = 60
BG_COLOR = (0, 64, 133)
BONUS_SYMBOLS = ["concordia.png", "uqat.png", "ottawa.png"]

def setup_gpio():
    """Setup lgpio with hardware pull-ups (1=idle, 0=pressed)."""
    global gpio_handle
    gpio_handle = lgpio.gpiochip_open(0)
    lgpio.gpio_claim_input(gpio_handle, PIN_CRANK, flags=lgpio.SET_PULL_UP)
    lgpio.gpio_claim_input(gpio_handle, PIN_BUTTON_SPIN, flags=lgpio.SET_PULL_UP)
    print("✓ LGPIO ready: Pins 24(crank)/25(spin) w/ pull-up")

def load_symbols():
    """Load PNG symbols from .symbols/ folder."""
    if not os.path.exists(SYMBOL_FOLDER):
        raise FileNotFoundError(f"mkdir '{SYMBOL_FOLDER}' && add 3+ PNGs")
    symbols = []
    for f in os.listdir(SYMBOL_FOLDER):
        if f.lower().endswith(('.png', '.jpg', '.jpeg')):
            path = os.path.join(SYMBOL_FOLDER, f)
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, SYMBOL_SIZE)
            symbols.append((f, img))
    if len(symbols) < 3:
        raise ValueError(f"Need 3+ symbols (got {len(symbols)})")
    print(f"✓ Loaded symbols: {[n for n, _ in symbols]}")
    return symbols

class Reel:
    """Individual spinning reel with blur effect."""
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
        speed = SPIN_SPEED_INITIAL / 16.67 / FPS * 167
        self.offset += speed * dt
        while self.offset >= 1.0:
            self.offset -= 1.0
            self.index = (self.index + 1) % len(self.symbols)

    def draw(self, surface):
        img = self.symbols[self.index][1]
        rect = img.get_rect(center=(self.x, self.y))
        
        if self.spinning:
            # Seamless spinning blur effect
            scroll_surf = pygame.Surface(SYMBOL_SIZE, pygame.SRCALPHA)
            scroll_y = int(self.offset * SYMBOL_SIZE[1])
            scroll_surf.blit(img, (0, -scroll_y))
            next_img = self.symbols[(self.index + 1) % len(self.symbols)][1]
            scroll_surf.blit(next_img, (0, SYMBOL_SIZE[1] - scroll_y))
            surface.blit(scroll_surf, rect)
        else:
            surface.blit(img, rect)
        
        # Glowing frame
        color = (0, 255, 100) if not self.spinning else (255, 255, 100)
        pygame.draw.rect(surface, color, rect.inflate(24, 24), 6)

    def result_name(self):
        return self.symbols[self.index][0]

def evaluate_result(reels, symbols):
    """Check for 3-of-a-kind wins."""
    names = [r.result_name() for r in reels]
    if all(n == names[0] for n in names):
        bonus = {s[0] for s in symbols if s[0] in BONUS_SYMBOLS}
        return True, "BONUS WINNER!" if names[0] in bonus else "WINNER!"
    return False, ""

def main():
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("🎰 PRO Arcade Slot Machine")
    clock = pygame.time.Clock()
    
    # Setup
    setup_gpio()
    symbols = load_symbols()
    width, height = screen.get_size()
    
    # Perfectly centered reels (wide outer spacing)
    center_x = width // 2
    left_x = center_x - 380
    right_x = center_x + 380
    reel_x = [left_x, center_x, right_x]
    reels = [Reel(symbols, reel_x[i], height // 2) for i in range(REEL_COUNT)]
    
    # Game state
    spins = wins = 0
    result_label = ""
    next_stop = 0
    prev_crank = 1
    prev_spin = 1
    
    def lever_pull():
        nonlocal next_stop, spins, wins, result_label
        
        if next_stop == 0:  # SPIN ALL (infinite spin)
            if any(r.spinning for r in reels):
                return
            spins += 1
            result_label = ""
            for reel in reels:
                reel.start_spin()
            next_stop = 1
            return
        
        if 1 <= next_stop <= REEL_COUNT:  # STOP ONE BY ONE
            reels[next_stop - 1].force_stop()
            next_stop += 1
        
        if next_stop > REEL_COUNT:  # EVALUATE WIN
            is_win, label = evaluate_result(reels, symbols)
            if is_win:
                wins += 1
            result_label = label
            next_stop = 0
    
    # UI Elements
    btn_rect = pygame.Rect(center_x - 140, height - 160, 280, 90)
    font_lg = pygame.font.Font(None, 52)
    font_sm = pygame.font.Font(None, 38)
    
    print("🎰 PRO SLOT READY | GPIO24(crank)/25(spin):1=idle,0=press | SPACE/Mouse works too!")
    
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        
        # LGPIO POLLING (1→0 edge detect)
        crank = lgpio.gpio_read(gpio_handle, PIN_CRANK)
        spin_btn = lgpio.gpio_read(gpio_handle, PIN_BUTTON_SPIN)
        if crank == 0 and prev_crank == 1:
            lever_pull()
        if spin_btn == 0 and prev_spin == 1:
            lever_pull()
        prev_crank = crank
        prev_spin = spin_btn
        
        # Pygame events (keyboard/mouse fallback)
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
        hud = [f"SPINS: {spins} | WINS: {wins}",
               result_label]
        for i, txt in enumerate(hud):
            clr = (255, 215, 0) if "WIN" in txt else (230, 230, 255)
            surf = font_sm.render(txt, True, clr)
            screen.blit(surf, (30, 35 + i * 42))
        
        # Control Button
        if next_stop == 0:
            btn_txt, btn_clr = "SPIN ALL!", (0, 255, 80)
        else:
            btn_txt, btn_clr = f"STOP REEL {next_stop}", (255, 180, 0)
        
        pygame.draw.rect(screen, btn_clr, btn_rect)
        pygame.draw.rect(screen, (255, 255, 255), btn_rect, 6)
        btn_surf = font_lg.render(btn_txt, True, (25, 25, 25))
        screen.blit(btn_surf, (
            btn_rect.centerx - btn_surf.get_width() // 2,
            btn_rect.centery - btn_surf.get_height() // 2
        ))
        
        # GPIO Debug (remove after testing)
        gpio_debug = f"GPIO:24={crank},25={spin_btn}"
        screen.blit(font_sm.render(gpio_debug, True, (0, 255, 0)), (30, height - 100))
        
        pygame.display.flip()
    
    # Cleanup
    pygame.quit()
    if gpio_handle:
        lgpio.gpiochip_close(gpio_handle)
    print("Game over!")

if __name__ == "__main__":
    main()
