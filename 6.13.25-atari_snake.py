import pygame
import random
import math
import numpy as np

# Initialize Pygame
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# Constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
GRID_SIZE = 20
CELL_SIZE = WINDOW_WIDTH // GRID_SIZE
FPS = 60

# Colors - Retro palette
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
DARK_GREEN = (0, 180, 0)
RED = (255, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
BLUE = (0, 100, 255)
PURPLE = (255, 0, 255)
CYAN = (0, 255, 255)
ORANGE = (255, 165, 0)

# Game states
STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_GAME_OVER = "game_over"

# Sound generation functions
def generate_beep(frequency, duration):
    sample_rate = 22050
    samples = int(sample_rate * duration)
    waves = np.zeros((samples, 2), dtype=np.int16)
    
    for i in range(samples):
        t = float(i) / sample_rate
        # Square wave for that Atari sound
        value = 32767 if math.sin(2 * math.pi * frequency * t) > 0 else -32767
        # Add some envelope
        envelope = 1.0
        if i < samples * 0.1:
            envelope = i / (samples * 0.1)
        elif i > samples * 0.9:
            envelope = (samples - i) / (samples * 0.1)
        value = int(value * envelope * 0.3)
        waves[i][0] = value  # Left channel
        waves[i][1] = value  # Right channel
    
    sound = pygame.sndarray.make_sound(waves)
    return sound

# Generate game sounds
eat_sound = generate_beep(440, 0.1)  # A4 note
death_sound = generate_beep(110, 0.5)  # A2 note (lower, longer)
move_sound = generate_beep(220, 0.02)  # A3 note (quick tick)
level_up_sound = generate_beep(880, 0.3)  # A5 note
menu_sound = generate_beep(660, 0.15)  # E5 note
select_sound = generate_beep(523, 0.2)  # C5 note

class Snake:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.positions = [(GRID_SIZE // 2, GRID_SIZE // 2)]
        self.direction = (1, 0)
        self.grow_count = 0
        self.rainbow_mode = False
        
    def move(self):
        head = self.positions[0]
        new_head = (head[0] + self.direction[0], head[1] + self.direction[1])
        
        # Check if snake leaves screen
        if (new_head[0] < 0 or new_head[0] >= GRID_SIZE or 
            new_head[1] < 0 or new_head[1] >= GRID_SIZE):
            return None  # Signal that snake left screen
        
        self.positions.insert(0, new_head)
        
        if self.grow_count > 0:
            self.grow_count -= 1
        else:
            self.positions.pop()
            
        # Play move sound (very quiet)
        move_sound.set_volume(0.05)
        move_sound.play()
            
        return new_head
        
    def grow(self, amount=1):
        self.grow_count += amount
        
    def check_collision(self):
        head = self.positions[0]
        return head in self.positions[1:]
        
    def change_direction(self, new_direction):
        # Prevent going back into yourself
        if (new_direction[0] * -1, new_direction[1] * -1) != self.direction:
            self.direction = new_direction

class Food:
    def __init__(self):
        self.position = None
        self.type = "normal"
        self.timer = 0
        self.lifespan = 0
        self.spawn()
        
    def spawn(self):
        self.position = (random.randint(0, GRID_SIZE - 1), 
                        random.randint(0, GRID_SIZE - 1))
        
        # Different food types with different rarities
        rand = random.random()
        if rand < 0.6:  # 60% normal apple
            self.type = "apple"
            self.lifespan = -1  # Never expires
        elif rand < 0.8:  # 20% golden apple
            self.type = "golden"
            self.lifespan = -1
        elif rand < 0.9:  # 10% speed fruit
            self.type = "speed"
            self.lifespan = 300  # 5 seconds at 60 FPS
        elif rand < 0.95:  # 5% ghost fruit
            self.type = "ghost"
            self.lifespan = 180  # 3 seconds
        else:  # 5% bomb (avoid this!)
            self.type = "bomb"
            self.lifespan = 240  # 4 seconds
            
        self.timer = 0
        
    def update(self):
        if self.lifespan > 0:
            self.timer += 1
            if self.timer >= self.lifespan:
                return True  # Signal to respawn
        return False
        
    @property
    def special(self):
        return self.type != "apple"
        
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("SNAKE - ATARI VIBES")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.big_font = pygame.font.Font(None, 72)
        self.title_font = pygame.font.Font(None, 96)
        
        self.state = STATE_MENU
        self.menu_selection = 0  # 0 = Start, 1 = Quit
        
        self.snake = Snake()
        self.food = Food()
        self.score = 0
        self.high_score = 0
        self.move_timer = 0
        self.move_delay = 100  # milliseconds
        self.particle_effects = []
        self.speed_boost_timer = 0
        self.ghost_mode_timer = 0
        
    def handle_menu_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_UP, pygame.K_w]:
                self.menu_selection = 0
                menu_sound.play()
            elif event.key in [pygame.K_DOWN, pygame.K_s]:
                self.menu_selection = 1
                menu_sound.play()
            elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                if self.menu_selection == 0:
                    self.state = STATE_PLAYING
                    self.reset_game()
                    select_sound.play()
                else:
                    return False  # Quit game
        return True
        
    def handle_game_input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.snake.change_direction((0, -1))
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.snake.change_direction((0, 1))
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.snake.change_direction((-1, 0))
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.snake.change_direction((1, 0))
            
    def handle_game_over_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_y:
                self.reset_game()
                self.state = STATE_PLAYING
                select_sound.play()
            elif event.key == pygame.K_n:
                self.state = STATE_MENU
                self.menu_selection = 0
                menu_sound.play()
                
    def update(self, dt):
        if self.state != STATE_PLAYING:
            return
            
        self.move_timer += dt
        
        if self.move_timer >= self.move_delay:
            self.move_timer = 0
            
            # Move snake
            head = self.snake.move()
            
            # Check if snake left screen
            if head is None:
                self.state = STATE_GAME_OVER
                death_sound.play()
                if self.score > self.high_score:
                    self.high_score = self.score
                return
            
            # Check food collision
            if head == self.food.position:
                if self.food.type == "apple":
                    self.snake.grow()
                    self.score += 10
                    eat_sound.play()
                elif self.food.type == "golden":
                    self.snake.grow(3)
                    self.score += 50
                    level_up_sound.play()
                    self.snake.rainbow_mode = True
                    # Add particles
                    for _ in range(20):
                        self.particle_effects.append({
                            'pos': [head[0] * CELL_SIZE + CELL_SIZE // 2, 
                                   head[1] * CELL_SIZE + CELL_SIZE // 2],
                            'vel': [random.uniform(-5, 5), random.uniform(-5, 5)],
                            'color': random.choice([YELLOW, CYAN, PURPLE, GREEN]),
                            'life': 1.0
                        })
                elif self.food.type == "speed":
                    self.score += 25
                    self.speed_boost_timer = 300  # 5 seconds of boost
                    menu_sound.play()
                    # Blue particles for speed
                    for _ in range(15):
                        self.particle_effects.append({
                            'pos': [head[0] * CELL_SIZE + CELL_SIZE // 2, 
                                   head[1] * CELL_SIZE + CELL_SIZE // 2],
                            'vel': [random.uniform(-8, 8), random.uniform(-8, 8)],
                            'color': CYAN,
                            'life': 1.0
                        })
                elif self.food.type == "ghost":
                    self.score += 30
                    self.ghost_mode_timer = 180  # 3 seconds of ghost mode
                    select_sound.play()
                    # White particles for ghost
                    for _ in range(10):
                        self.particle_effects.append({
                            'pos': [head[0] * CELL_SIZE + CELL_SIZE // 2, 
                                   head[1] * CELL_SIZE + CELL_SIZE // 2],
                            'vel': [random.uniform(-3, 3), random.uniform(-3, 3)],
                            'color': WHITE,
                            'life': 1.5
                        })
                elif self.food.type == "bomb":
                    # Bomb hurts! Lose score and length
                    self.score = max(0, self.score - 20)
                    death_sound.play()
                    # Remove snake segments if possible
                    if len(self.snake.positions) > 3:
                        self.snake.positions = self.snake.positions[:len(self.snake.positions)//2]
                    # Red explosion particles
                    for _ in range(30):
                        self.particle_effects.append({
                            'pos': [head[0] * CELL_SIZE + CELL_SIZE // 2, 
                                   head[1] * CELL_SIZE + CELL_SIZE // 2],
                            'vel': [random.uniform(-10, 10), random.uniform(-10, 10)],
                            'color': RED,
                            'life': 0.8
                        })
                    
                self.food.spawn()
                
                # Spawn food away from snake
                while self.food.position in self.snake.positions:
                    self.food.spawn()
                    
                # Speed up game (except for bombs)
                if self.food.type != "bomb":
                    self.move_delay = max(50, self.move_delay - 2)
                
            # Check self collision (unless in ghost mode)
            if self.ghost_mode_timer <= 0 and self.snake.check_collision():
                self.state = STATE_GAME_OVER
                death_sound.play()
                if self.score > self.high_score:
                    self.high_score = self.score
                    
        # Update food timer
        if self.food.update():
            self.food.spawn()
            while self.food.position in self.snake.positions:
                self.food.spawn()
                
        # Update power-up timers
        if self.speed_boost_timer > 0:
            self.speed_boost_timer -= 1
            # Temporarily increase speed
            if self.move_timer >= self.move_delay * 0.5:  # Double speed
                self.move_timer = self.move_delay * 0.5
                
        if self.ghost_mode_timer > 0:
            self.ghost_mode_timer -= 1
                    
        # Update particles
        for particle in self.particle_effects[:]:
            particle['pos'][0] += particle['vel'][0]
            particle['pos'][1] += particle['vel'][1]
            particle['vel'][1] += 0.5  # gravity
            particle['life'] -= 0.02
            if particle['life'] <= 0:
                self.particle_effects.remove(particle)
                
    def draw_menu(self):
        self.screen.fill(BLACK)
        
        # Title
        title_text = self.title_font.render("SNAKE", True, GREEN)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, 150))
        self.screen.blit(title_text, title_rect)
        
        # Subtitle
        subtitle_text = self.font.render("ATARI VIBES", True, CYAN)
        subtitle_rect = subtitle_text.get_rect(center=(WINDOW_WIDTH // 2, 220))
        self.screen.blit(subtitle_text, subtitle_rect)
        
        # Menu options
        start_color = YELLOW if self.menu_selection == 0 else WHITE
        quit_color = YELLOW if self.menu_selection == 1 else WHITE
        
        start_text = self.big_font.render("START", True, start_color)
        start_rect = start_text.get_rect(center=(WINDOW_WIDTH // 2, 350))
        self.screen.blit(start_text, start_rect)
        
        quit_text = self.big_font.render("QUIT", True, quit_color)
        quit_rect = quit_text.get_rect(center=(WINDOW_WIDTH // 2, 450))
        self.screen.blit(quit_text, quit_rect)
        
        # Instructions
        inst_text = self.font.render("Use ARROWS/WASD to select, ENTER to confirm", True, WHITE)
        inst_rect = inst_text.get_rect(center=(WINDOW_WIDTH // 2, 550))
        self.screen.blit(inst_text, inst_rect)
        
        # High score
        if self.high_score > 0:
            hs_text = self.font.render(f"HIGH SCORE: {self.high_score}", True, PURPLE)
            hs_rect = hs_text.get_rect(center=(WINDOW_WIDTH // 2, 280))
            self.screen.blit(hs_text, hs_rect)
                
    def draw_game(self):
        self.screen.fill(BLACK)
        
        # Draw border
        pygame.draw.rect(self.screen, RED, (0, 0, WINDOW_WIDTH, WINDOW_HEIGHT), 3)
        
        # Draw grid lines (subtle)
        for x in range(0, WINDOW_WIDTH, CELL_SIZE):
            pygame.draw.line(self.screen, (20, 20, 20), (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, CELL_SIZE):
            pygame.draw.line(self.screen, (20, 20, 20), (0, y), (WINDOW_WIDTH, y))
        
        # Draw snake
        for i, pos in enumerate(self.snake.positions):
            rect = pygame.Rect(pos[0] * CELL_SIZE, pos[1] * CELL_SIZE, 
                              CELL_SIZE - 2, CELL_SIZE - 2)
            
            # Ghost mode makes snake translucent
            if self.ghost_mode_timer > 0:
                ghost_surf = pygame.Surface((CELL_SIZE - 2, CELL_SIZE - 2), pygame.SRCALPHA)
                alpha = 100 + int(155 * abs(math.sin(pygame.time.get_ticks() * 0.01)))
                
            if self.snake.rainbow_mode:
                # Rainbow effect
                hue = (i * 20 + pygame.time.get_ticks() / 10) % 360
                color = pygame.Color(0)
                color.hsla = (hue, 100, 50, 100)
            else:
                # Gradient from head to tail
                color = GREEN if i == 0 else DARK_GREEN
                
            if self.ghost_mode_timer > 0:
                ghost_surf.fill((*color[:3], alpha))
                self.screen.blit(ghost_surf, rect)
            else:
                pygame.draw.rect(self.screen, color, rect)
            
            # Draw eyes on head
            if i == 0:
                eye_size = CELL_SIZE // 5
                eye_color = WHITE if self.ghost_mode_timer <= 0 else (*WHITE, alpha)
                if self.snake.direction == (1, 0):  # Right
                    pygame.draw.circle(self.screen, eye_color, 
                                     (rect.right - eye_size, rect.top + eye_size), eye_size // 2)
                    pygame.draw.circle(self.screen, eye_color, 
                                     (rect.right - eye_size, rect.bottom - eye_size), eye_size // 2)
                elif self.snake.direction == (-1, 0):  # Left
                    pygame.draw.circle(self.screen, eye_color, 
                                     (rect.left + eye_size, rect.top + eye_size), eye_size // 2)
                    pygame.draw.circle(self.screen, eye_color, 
                                     (rect.left + eye_size, rect.bottom - eye_size), eye_size // 2)
                elif self.snake.direction == (0, -1):  # Up
                    pygame.draw.circle(self.screen, eye_color, 
                                     (rect.left + eye_size, rect.top + eye_size), eye_size // 2)
                    pygame.draw.circle(self.screen, eye_color, 
                                     (rect.right - eye_size, rect.top + eye_size), eye_size // 2)
                else:  # Down
                    pygame.draw.circle(self.screen, eye_color, 
                                     (rect.left + eye_size, rect.bottom - eye_size), eye_size // 2)
                    pygame.draw.circle(self.screen, eye_color, 
                                     (rect.right - eye_size, rect.bottom - eye_size), eye_size // 2)
        
        # Draw food
        food_rect = pygame.Rect(self.food.position[0] * CELL_SIZE, 
                               self.food.position[1] * CELL_SIZE,
                               CELL_SIZE - 2, CELL_SIZE - 2)
        
        if self.food.type == "apple":
            # Normal red apple
            pygame.draw.rect(self.screen, RED, food_rect)
        elif self.food.type == "golden":
            # Pulsing golden apple
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.005))
            size = int(CELL_SIZE - 2 - pulse * 10)
            offset = (CELL_SIZE - size) // 2
            food_rect = pygame.Rect(self.food.position[0] * CELL_SIZE + offset,
                                   self.food.position[1] * CELL_SIZE + offset,
                                   size, size)
            pygame.draw.rect(self.screen, YELLOW, food_rect)
            pygame.draw.rect(self.screen, PURPLE, food_rect, 3)
        elif self.food.type == "speed":
            # Blue lightning bolt shape for speed
            pygame.draw.rect(self.screen, CYAN, food_rect)
            # Draw lightning bolt
            bolt_points = [
                (food_rect.centerx - 5, food_rect.top + 5),
                (food_rect.centerx + 2, food_rect.centery - 2),
                (food_rect.centerx - 2, food_rect.centery + 2),
                (food_rect.centerx + 5, food_rect.bottom - 5)
            ]
            pygame.draw.lines(self.screen, WHITE, False, bolt_points, 3)
        elif self.food.type == "ghost":
            # White ghost shape with fade effect
            fade = abs(math.sin(pygame.time.get_ticks() * 0.01)) * 0.5 + 0.5
            ghost_surf = pygame.Surface((CELL_SIZE - 2, CELL_SIZE - 2), pygame.SRCALPHA)
            alpha = int(255 * fade)
            pygame.draw.circle(ghost_surf, (*WHITE, alpha), 
                             ((CELL_SIZE - 2) // 2, (CELL_SIZE - 2) // 2), 
                             (CELL_SIZE - 2) // 2)
            self.screen.blit(ghost_surf, food_rect)
        elif self.food.type == "bomb":
            # Red bomb with fuse
            pygame.draw.circle(self.screen, (80, 0, 0), food_rect.center, CELL_SIZE // 2 - 2)
            pygame.draw.circle(self.screen, RED, food_rect.center, CELL_SIZE // 2 - 2, 2)
            # Sparking fuse
            if self.food.timer % 10 < 5:
                spark_pos = (food_rect.centerx + CELL_SIZE // 3, food_rect.top)
                pygame.draw.circle(self.screen, YELLOW, spark_pos, 3)
                pygame.draw.circle(self.screen, ORANGE, spark_pos, 2)
            
        # Draw timer bar for expiring foods
        if self.food.lifespan > 0:
            time_left = (self.food.lifespan - self.food.timer) / self.food.lifespan
            bar_width = int(CELL_SIZE * time_left)
            bar_rect = pygame.Rect(self.food.position[0] * CELL_SIZE,
                                  self.food.position[1] * CELL_SIZE - 5,
                                  bar_width, 3)
            bar_color = GREEN if time_left > 0.5 else YELLOW if time_left > 0.25 else RED
            pygame.draw.rect(self.screen, bar_color, bar_rect)
            
        # Draw particles
        for particle in self.particle_effects:
            alpha = int(particle['life'] * 255)
            size = int(particle['life'] * 10)
            if size > 0:
                surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*particle['color'], alpha), (size, size), size)
                self.screen.blit(surf, (particle['pos'][0] - size, particle['pos'][1] - size))
        
        # Draw score
        score_text = self.font.render(f"SCORE: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))
        
        high_score_text = self.font.render(f"HIGH: {self.high_score}", True, CYAN)
        self.screen.blit(high_score_text, (10, 50))
        
        # Draw active power-ups
        y_offset = 90
        if self.speed_boost_timer > 0:
            speed_text = self.font.render(f"SPEED: {self.speed_boost_timer // 60 + 1}s", True, CYAN)
            self.screen.blit(speed_text, (10, y_offset))
            y_offset += 30
            
        if self.ghost_mode_timer > 0:
            ghost_text = self.font.render(f"GHOST: {self.ghost_mode_timer // 60 + 1}s", True, WHITE)
            self.screen.blit(ghost_text, (10, y_offset))
        
    def draw_game_over(self):
        self.draw_game()  # Draw the game state underneath
        
        # Dark overlay
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        # Game over text
        game_over_text = self.big_font.render("GAME OVER", True, RED)
        text_rect = game_over_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 50))
        pygame.draw.rect(self.screen, BLACK, text_rect.inflate(20, 20))
        pygame.draw.rect(self.screen, RED, text_rect.inflate(20, 20), 3)
        self.screen.blit(game_over_text, text_rect)
        
        # Score
        score_text = self.font.render(f"FINAL SCORE: {self.score}", True, YELLOW)
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 20))
        self.screen.blit(score_text, score_rect)
        
        # Y/N prompt
        prompt_text = self.font.render("Play again? Y/N", True, WHITE)
        prompt_rect = prompt_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 80))
        self.screen.blit(prompt_text, prompt_rect)
        
        # Blinking cursor
        if pygame.time.get_ticks() % 1000 < 500:
            cursor_text = self.font.render("_", True, WHITE)
            cursor_rect = cursor_text.get_rect(left=prompt_rect.right + 10, centery=prompt_rect.centery)
            self.screen.blit(cursor_text, cursor_rect)
            
    def reset_game(self):
        self.snake.reset()
        self.food.spawn()
        self.score = 0
        self.move_delay = 100
        self.particle_effects = []
        self.speed_boost_timer = 0
        self.ghost_mode_timer = 0
        
    def run(self):
        running = True
        
        while running:
            dt = self.clock.tick(FPS)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif self.state == STATE_MENU:
                    running = self.handle_menu_input(event)
                elif self.state == STATE_GAME_OVER:
                    self.handle_game_over_input(event)
                    
            if self.state == STATE_PLAYING:
                self.handle_game_input()
                self.update(dt)
                
            # Draw based on state
            if self.state == STATE_MENU:
                self.draw_menu()
            elif self.state == STATE_PLAYING:
                self.draw_game()
            elif self.state == STATE_GAME_OVER:
                self.draw_game_over()
            
            pygame.display.flip()
            
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
