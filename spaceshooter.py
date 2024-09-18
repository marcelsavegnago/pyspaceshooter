import pygame
import sys
import math
import random
import json
import os

# Initialize Pygame
pygame.init()
pygame.mixer.init()  # Initialize the mixer for sounds and music

# Screen settings
WIDTH = 800
HEIGHT = 600
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Py Space Shooter")

# Color definitions
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

# Fonts
# Replace 'fonts/space_font.ttf' with the path to your custom font
title_font = pygame.font.Font('fonts/space_font.ttf', 54)
menu_font = pygame.font.Font('fonts/space_font.ttf', 40)
game_font = pygame.font.Font('fonts/space_font.ttf', 24)

def save_score(name, score):
    """Save player's score to a JSON file.

    Args:
        name (str): Player's initials.
        score (int): Player's score.
    """
    try:
        data = []
        if os.path.exists('ranking.json'):
            with open('ranking.json', 'r') as file:
                data = json.load(file)
        data.append({'name': name, 'score': score})
        with open('ranking.json', 'w') as file:
            json.dump(data, file)
    except Exception as e:
        print(f"Error saving score: {e}")

def load_ranking():
    """Load rankings from a JSON file.

    Returns:
        list: Sorted list of dictionaries with keys 'name' and 'score'.
    """
    try:
        if os.path.exists('ranking.json'):
            with open('ranking.json', 'r') as file:
                data = json.load(file)
                return sorted(data, key=lambda x: x['score'], reverse=True)
        else:
            return []
    except Exception as e:
        print(f"Error loading ranking: {e}")
        return []

class Game:
    """Main game class to encapsulate the game logic and state."""

    def __init__(self):
        """Initialize the game."""
        self.clock = pygame.time.Clock()
        self.playing = True
        self.running = True
        self.score = 0
        self.level = 1
        self.level_counter = 0
        self.next_powerup_time = random.randint(500, 1000)
        self.starry_background = StarryBackground(50)
        self.player_initials = ""
        self.difficulty = 'Normal'  # Default difficulty

        # Load sounds
        # Ensure the sound files are in the 'sounds' directory
        self.shot_sound = pygame.mixer.Sound('sounds/shot.ogg')
        self.explosion_sound = pygame.mixer.Sound('sounds/explosion.ogg')
        self.powerup_sound = pygame.mixer.Sound('sounds/powerup.ogg')
        self.life_loss_sound = pygame.mixer.Sound('sounds/life_loss.ogg')

        # Set sound volumes
        self.shot_sound.set_volume(0.5)
        self.explosion_sound.set_volume(0.5)
        self.powerup_sound.set_volume(0.5)
        self.life_loss_sound.set_volume(0.5)

        # Load background music
        # Ensure the music file is in the 'music' directory
        pygame.mixer.music.load('music/background.wav')
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)  # Loop indefinitely

    def new(self):
        """Start a new game."""
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.enemy_projectiles = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()
        self.explosions = pygame.sprite.Group()
        self.score = 0
        self.level = 1
        self.level_counter = 0
        self.next_powerup_time = random.randint(500, 1000)
        self.player = Player()
        self.all_sprites.add(self.player)
        self.starry_background = StarryBackground(50)
        self.run()

    def run(self):
        """Game loop."""
        self.playing = True
        while self.playing:
            delta_time = self.clock.tick(60) / 1000  # Convert milliseconds to seconds
            self.events()
            self.update(delta_time)
            self.draw()
        self.game_over()

    def events(self):
        """Handle game events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.playing = False
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.player.shoot(self)
                elif event.key == pygame.K_ESCAPE:
                    self.pause_menu()

    def update(self, delta_time):
        """Update game state."""
        self.all_sprites.update(delta_time)
        self.starry_background.update(delta_time)
        self.level_counter += 1

        if self.level_counter >= 1000:
            self.level_counter = 0
            self.level += 1

        # Adjust enemy spawn rate based on difficulty
        if self.difficulty == 'Easy':
            spawn_rate = max(80 - self.level * 2, 20)
        elif self.difficulty == 'Hard':
            spawn_rate = max(40 - self.level * 2, 5)
        else:  # Normal
            spawn_rate = max(60 - self.level * 2, 10)

        if random.randint(1, spawn_rate) == 1:
            enemy_type = random.choice(['normal', 'shooter']) if self.level >= 3 else 'normal'
            if enemy_type == 'normal':
                enemy = Enemy(self.level)
            else:
                enemy = ShooterEnemy(self, self.level, self.player)
            self.all_sprites.add(enemy)
            self.enemies.add(enemy)

        self.next_powerup_time -= 1
        if self.next_powerup_time <= 0:
            powerup_type = random.choice(['weapon', 'bomb', 'shield'])
            position = (random.randint(20, WIDTH - 20), -20)
            powerup = PowerUp(powerup_type, position)
            self.all_sprites.add(powerup)
            self.powerups.add(powerup)
            self.next_powerup_time = random.randint(500, 1000)

        # Collision detection with masks for pixel-perfect collisions
        collision = pygame.sprite.groupcollide(
            self.enemies, self.projectiles, True, True, pygame.sprite.collide_mask)
        if collision:
            for enemy in collision:
                self.score += 10
                enemy_explosion = Explosion(enemy.rect.center)
                self.all_sprites.add(enemy_explosion)
                self.explosions.add(enemy_explosion)
                self.explosion_sound.play()

        if pygame.sprite.spritecollide(self.player, self.enemy_projectiles, True, pygame.sprite.collide_mask):
            if self.player.shield > 0:
                self.player.shield -= 1
            else:
                self.player.lives -= 1
                self.life_loss_sound.play()
                if self.player.lives <= 0:
                    self.playing = False

        player_collision = pygame.sprite.spritecollide(
            self.player, self.enemies, True, pygame.sprite.collide_mask)
        if player_collision:
            if self.player.shield > 0:
                self.player.shield -= 1
            else:
                self.player.lives -= 1
                self.life_loss_sound.play()
                if self.player.lives <= 0:
                    self.playing = False

        powerup_collision = pygame.sprite.spritecollide(
            self.player, self.powerups, True, pygame.sprite.collide_mask)
        for powerup in powerup_collision:
            self.powerup_sound.play()
            if powerup.type == 'weapon':
                self.player.weapon_level += 1
                self.player.powerup_timer = 600
            elif powerup.type == 'bomb':
                for enemy in self.enemies:
                    enemy_explosion = Explosion(enemy.rect.center)
                    self.all_sprites.add(enemy_explosion)
                    self.explosions.add(enemy_explosion)
                    enemy.kill()
                    self.score += 10
                explosion = Explosion(self.player.rect.center)
                self.all_sprites.add(explosion)
                self.explosions.add(explosion)
                self.explosion_sound.play()
            elif powerup.type == 'shield':
                self.player.shield = 3

    def draw(self):
        """Draw everything on the screen."""
        SCREEN.fill(BLACK)
        self.starry_background.draw(SCREEN)
        self.all_sprites.draw(SCREEN)

        score_text = game_font.render(f"Score: {self.score}", True, WHITE)
        lives_text = game_font.render(f"Lives: {self.player.lives}", True, WHITE)
        level_text = game_font.render(f"Level: {self.level}", True, WHITE)
        SCREEN.blit(score_text, (10, 10))
        SCREEN.blit(lives_text, (10, 40))
        SCREEN.blit(level_text, (10, 70))

        x_offset = WIDTH - 200
        if self.player.weapon_level > 1:
            weapon_text = game_font.render(f"Weapon Lv{self.player.weapon_level}", True, WHITE)
            weapon_time = game_font.render(f"Time: {self.player.powerup_timer // 60}s", True, WHITE)
            SCREEN.blit(weapon_text, (x_offset, 10))
            SCREEN.blit(weapon_time, (x_offset, 30))
        if self.player.shield > 0:
            shield_text = game_font.render(f"Shield: {self.player.shield}", True, WHITE)
            SCREEN.blit(shield_text, (x_offset, 60))

        pygame.display.flip()

    def show_start_screen(self):
        """Display the initial menu."""
        menu_active = True
        selected_option = 0
        options = ["Start Game", "High Scores", "Settings", "Exit"]
        while menu_active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    menu_active = False
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if selected_option == 0:
                            menu_active = False
                        elif selected_option == 1:
                            self.show_high_scores()
                        elif selected_option == 2:
                            self.show_settings()
                        elif selected_option == 3:
                            menu_active = False
                            self.running = False
                    elif event.key == pygame.K_ESCAPE:
                        menu_active = False
                        self.running = False
                    elif event.key == pygame.K_UP:
                        selected_option = (selected_option - 1) % len(options)
                    elif event.key == pygame.K_DOWN:
                        selected_option = (selected_option + 1) % len(options)

            SCREEN.fill(BLACK)
            title_text = title_font.render("Py Space Shooter", True, WHITE)
            SCREEN.blit(title_text, ((WIDTH - title_text.get_width()) / 2, HEIGHT / 4))

            for i, option in enumerate(options):
                color = WHITE if i == selected_option else GRAY
                text = menu_font.render(option, True, color)
                SCREEN.blit(text, ((WIDTH - text.get_width()) / 2, HEIGHT / 2 + i * 60))

            pygame.display.flip()
            self.clock.tick(60)

    def show_high_scores(self):
        """Display the high scores screen."""
        high_scores_active = True
        while high_scores_active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    high_scores_active = False
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        high_scores_active = False

            SCREEN.fill(BLACK)
            title_text = title_font.render("High Scores", True, WHITE)
            SCREEN.blit(title_text, ((WIDTH - title_text.get_width()) / 2, 50))

            ranking = load_ranking()
            if ranking:
                for i, entry in enumerate(ranking[:10]):
                    name = entry['name']
                    points = entry['score']
                    ranking_line = game_font.render(f"{i + 1}. {name} - {points}", True, WHITE)
                    SCREEN.blit(ranking_line, (WIDTH // 4, 150 + i * 40))
            else:
                no_scores_text = game_font.render("No high scores yet.", True, WHITE)
                SCREEN.blit(no_scores_text, ((WIDTH - no_scores_text.get_width()) / 2, HEIGHT / 2))

            back_text = game_font.render("Press ESC to return", True, GRAY)
            SCREEN.blit(back_text, ((WIDTH - back_text.get_width()) / 2, HEIGHT - 50))

            pygame.display.flip()
            self.clock.tick(60)

    def show_settings(self):
        """Display the settings menu."""
        settings_active = True
        selected_option = 0
        options = ["Volume", "Difficulty", "Back"]
        volume_level = int(pygame.mixer.music.get_volume() * 10)
        difficulties = ["Easy", "Normal", "Hard"]
        difficulty_index = difficulties.index(self.difficulty)

        while settings_active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    settings_active = False
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        settings_active = False
                    elif event.key == pygame.K_RETURN:
                        if selected_option == 2:
                            settings_active = False
                    elif event.key == pygame.K_UP:
                        selected_option = (selected_option - 1) % len(options)
                    elif event.key == pygame.K_DOWN:
                        selected_option = (selected_option + 1) % len(options)
                    elif event.key == pygame.K_LEFT:
                        if selected_option == 0 and volume_level > 0:
                            volume_level -= 1
                            pygame.mixer.music.set_volume(volume_level / 10)
                        elif selected_option == 1:
                            difficulty_index = (difficulty_index - 1) % len(difficulties)
                            self.difficulty = difficulties[difficulty_index]
                    elif event.key == pygame.K_RIGHT:
                        if selected_option == 0 and volume_level < 10:
                            volume_level += 1
                            pygame.mixer.music.set_volume(volume_level / 10)
                        elif selected_option == 1:
                            difficulty_index = (difficulty_index + 1) % len(difficulties)
                            self.difficulty = difficulties[difficulty_index]

            SCREEN.fill(BLACK)
            title_text = title_font.render("Settings", True, WHITE)
            SCREEN.blit(title_text, ((WIDTH - title_text.get_width()) / 2, 50))

            for i, option in enumerate(options):
                color = WHITE if i == selected_option else GRAY
                if option == "Volume":
                    text = menu_font.render(f"{option}: {volume_level}", True, color)
                elif option == "Difficulty":
                    text = menu_font.render(f"{option}: {self.difficulty}", True, color)
                else:
                    text = menu_font.render(option, True, color)
                SCREEN.blit(text, ((WIDTH - text.get_width()) / 2, HEIGHT / 2 + i * 60))

            pygame.display.flip()
            self.clock.tick(60)

    def pause_menu(self):
        """Display the pause menu."""
        paused = True
        selected_option = 0
        options = ["Continue", "Exit"]
        while paused:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        paused = False
                    elif event.key == pygame.K_RETURN:
                        if selected_option == 0:
                            paused = False
                        elif selected_option == 1:
                            pygame.quit()
                            sys.exit()
                    elif event.key == pygame.K_UP:
                        selected_option = (selected_option - 1) % len(options)
                    elif event.key == pygame.K_DOWN:
                        selected_option = (selected_option + 1) % len(options)

            SCREEN.fill(BLACK)
            title_text = title_font.render("PAUSE", True, WHITE)
            SCREEN.blit(title_text, ((WIDTH - title_text.get_width()) / 2, HEIGHT / 4))

            for i, option in enumerate(options):
                color = WHITE if i == selected_option else GRAY
                text = menu_font.render(option, True, color)
                SCREEN.blit(text, ((WIDTH - text.get_width()) / 2, HEIGHT / 2 + i * 50))

            pygame.display.flip()
            self.clock.tick(60)

    def game_over(self):
        """Display the game over screen and save score."""
        save_score(self.player_initials, self.score)
        ranking = load_ranking()

        game_over_active = True
        while game_over_active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        game_over_active = False
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()

            SCREEN.fill(BLACK)

            # Game Over Title
            game_over_text = title_font.render("GAME OVER", True, RED)
            score_text = menu_font.render(f"Your Score: {self.score}", True, WHITE)
            restart_text = menu_font.render("Press Enter to Restart", True, WHITE)
            quit_text = menu_font.render("Press Esc to Exit", True, WHITE)

            # Display title and options on screen
            SCREEN.blit(game_over_text, ((WIDTH - game_over_text.get_width()) / 2, 50))
            SCREEN.blit(score_text, ((WIDTH - score_text.get_width()) / 2, 150))
            SCREEN.blit(restart_text, ((WIDTH - restart_text.get_width()) / 2, 500))
            SCREEN.blit(quit_text, ((WIDTH - quit_text.get_width()) / 2, 550))

            # Ranking Title
            ranking_title = menu_font.render("Ranking - Top 5", True, WHITE)
            SCREEN.blit(ranking_title, (WIDTH // 4, 200))

            # Display ranking with highlight for the player
            for i, entry in enumerate(ranking[:5]):
                name = entry['name']
                points = entry['score']
                color = WHITE if name != self.player_initials else YELLOW  # Highlight for current player
                ranking_line = game_font.render(f"{i + 1}. {name} - {points}", True, color)
                SCREEN.blit(ranking_line, (WIDTH // 4, 250 + i * 40))  # Space between lines

            pygame.display.flip()
            self.clock.tick(60)

    def capture_initials(self):
        """Capture player's initials."""
        initials = ""
        capturing = True
        while capturing:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and len(initials) == 3:
                        capturing = False
                    elif event.key == pygame.K_BACKSPACE:
                        initials = initials[:-1]
                    elif len(initials) < 3 and event.unicode.isalpha():
                        initials += event.unicode.upper()

            SCREEN.fill(BLACK)
            title_text = menu_font.render("Enter your initials", True, WHITE)
            initials_text = menu_font.render(initials, True, WHITE)
            SCREEN.blit(title_text, ((WIDTH - title_text.get_width()) / 2, HEIGHT / 2 - 50))
            SCREEN.blit(initials_text, ((WIDTH - initials_text.get_width()) / 2, HEIGHT / 2))

            pygame.display.flip()
            self.clock.tick(60)

        self.player_initials = initials

class StarryBackground:
    """Class for the starry background with parallax effect."""

    def __init__(self, num_stars):
        """Initialize the starry background.

        Args:
            num_stars (int): Number of stars per layer.
        """
        self.layers = []
        for i in range(3):  # Three layers for the parallax effect
            stars = []
            for _ in range(num_stars):
                x = random.randrange(0, WIDTH)
                y = random.randrange(0, HEIGHT)
                size = random.choice([1, 2])
                speed = (i + 1) * 0.1  # Different speeds for each layer
                stars.append([x, y, size, speed])
            self.layers.append(stars)

    def update(self, delta_time):
        """Update star positions."""
        for stars in self.layers:
            for star in stars:
                star[1] += star[3] * delta_time * 60
                if star[1] > HEIGHT:
                    star[0] = random.randrange(0, WIDTH)
                    star[1] = -star[2]
                    star[2] = random.choice([1, 2])

    def draw(self, screen):
        """Draw stars on the screen.

        Args:
            screen (pygame.Surface): The screen to draw on.
        """
        for stars in self.layers:
            for star in stars:
                pygame.draw.circle(screen, WHITE, (int(star[0]), int(star[1])), star[2])

class Player(pygame.sprite.Sprite):
    """Class for the player."""

    def __init__(self):
        """Initialize the player."""
        super().__init__()
        # Replace 'images/player_ship.png' with the path to your player ship image
        self.image_orig = pygame.image.load('images/player_ship.png').convert_alpha()
        self.image_orig = pygame.transform.scale(self.image_orig, (50, 50))
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect(center=(WIDTH / 2, HEIGHT / 2))
        self.pos = pygame.math.Vector2(self.rect.center)
        self.speed = 0
        self.angle = 0
        self.lives = 3
        self.weapon_level = 1
        self.powerup_timer = 0
        self.shield = 0
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, delta_time):
        """Update player position and rotation."""
        keys = pygame.key.get_pressed()
        rotation_speed = 200  # Degrees per second
        acceleration = 300     # Pixels per second squared
        max_speed = 300        # Pixels per second
        friction = 0.95

        if keys[pygame.K_LEFT]:
            self.angle += rotation_speed * delta_time
        if keys[pygame.K_RIGHT]:
            self.angle -= rotation_speed * delta_time
        if keys[pygame.K_UP]:
            self.speed += acceleration * delta_time
        elif keys[pygame.K_DOWN]:
            self.speed -= acceleration * delta_time
        else:
            self.speed *= friction

        self.speed = max(min(self.speed, max_speed), -max_speed)
        rad = math.radians(self.angle)
        self.pos.x += -self.speed * math.sin(rad) * delta_time
        self.pos.y += -self.speed * math.cos(rad) * delta_time

        self.pos.x %= WIDTH
        self.pos.y %= HEIGHT

        self.rect.center = self.pos
        self.image = pygame.transform.rotate(self.image_orig, self.angle)
        self.rect = self.image.get_rect(center=self.rect.center)
        self.mask = pygame.mask.from_surface(self.image)

        if self.powerup_timer > 0:
            self.powerup_timer -= 1
            if self.powerup_timer == 0:
                self.weapon_level = 1

    def shoot(self, game):
        """Fire a projectile.
    
        Args:
            game (Game): The game instance to access sounds and sprite groups.
        """
        rad = math.radians(self.angle)
        direction = pygame.math.Vector2(-math.sin(rad), -math.cos(rad))
        front_tip = self.pos + direction * 25
    
        if self.weapon_level == 1:
            projectile = Projectile(front_tip, direction * 500, self.angle)
            game.all_sprites.add(projectile)
            game.projectiles.add(projectile)
        elif self.weapon_level == 2:
            angles = [-10, 0, 10]
            for a in angles:
                rad_offset = math.radians(self.angle + a)
                direction_offset = pygame.math.Vector2(-math.sin(rad_offset), -math.cos(rad_offset))
                projectile = Projectile(front_tip, direction_offset * 500, self.angle + a)
                game.all_sprites.add(projectile)
                game.projectiles.add(projectile)
        elif self.weapon_level >= 3:
            angles = [-20, -10, 0, 10, 20]
            for a in angles:
                rad_offset = math.radians(self.angle + a)
                direction_offset = pygame.math.Vector2(-math.sin(rad_offset), -math.cos(rad_offset))
                projectile = Projectile(front_tip, direction_offset * 500, self.angle + a)
                game.all_sprites.add(projectile)
                game.projectiles.add(projectile)
    
        game.shot_sound.play()

class Projectile(pygame.sprite.Sprite):
    """Class for projectiles."""

    def __init__(self, position, velocity, angle):
        """Initialize the projectile.

        Args:
            position (tuple): Starting position of the projectile.
            velocity (pygame.math.Vector2): Velocity vector of the projectile.
            angle (float): Angle at which the projectile is fired.
        """
        super().__init__()
        # Load the projectile image
        self.image_orig = pygame.image.load('images/laser.png').convert_alpha()
        self.image_orig = pygame.transform.scale(self.image_orig, (10, 30))
        # Rotate the image by the angle
        self.image = pygame.transform.rotate(self.image_orig, angle)
        self.rect = self.image.get_rect(center=position)
        self.pos = pygame.math.Vector2(position)
        self.velocity = velocity
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, delta_time):
        """Update projectile position."""
        self.pos += self.velocity * delta_time
        self.rect.center = self.pos

        if (self.rect.right < 0 or self.rect.left > WIDTH or
                self.rect.bottom < 0 or self.rect.top > HEIGHT):
            self.kill()

class Enemy(pygame.sprite.Sprite):
    """Class for enemies."""

    def __init__(self, level):
        """Initialize the enemy.

        Args:
            level (int): Current game level.
        """
        super().__init__()
        # Replace 'images/enemy_ship.png' with the path to your enemy image
        self.image_orig = pygame.image.load('images/enemy_ship.png').convert_alpha()
        self.image_orig = pygame.transform.scale(self.image_orig, (50, 50))
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect()
        self.pos = pygame.math.Vector2(random.randrange(WIDTH), -50)
        self.rect.center = self.pos
        base_speed = random.uniform(100, 200)
        self.velocity = pygame.math.Vector2(0, base_speed + level * 10)
        self.level = level
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, delta_time):
        """Update enemy position."""
        self.pos += self.velocity * delta_time
        self.rect.center = self.pos

        if self.rect.top > HEIGHT:
            self.kill()

class ShooterEnemy(Enemy):
    """Class for enemies that shoot projectiles."""

    def __init__(self, game, level, player):
        """Initialize the shooter enemy.

        Args:
            game (Game): The game instance.
            level (int): Current game level.
            player (Player): The player object to target.
        """
        super().__init__(level)
        # Replace 'images/shooter_enemy.png' with the path to your shooter enemy image
        self.image_orig = pygame.image.load('images/shooter_enemy.png').convert_alpha()
        self.image_orig = pygame.transform.scale(self.image_orig, (50, 50))
        self.image = self.image_orig.copy()
        self.shoot_timer = random.randint(60, 120)
        self.player = player
        self.game = game
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, delta_time):
        """Update shooter enemy position and check if it should shoot."""
        super().update(delta_time)
        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self.shoot()
            self.shoot_timer = random.randint(60, 120)

    def shoot(self):
        """Fire a projectile toward the player."""
        direction = (self.player.pos - self.pos).normalize()
        angle = math.degrees(math.atan2(-direction.y, -direction.x)) + 90
        projectile = EnemyProjectile(self.pos, direction * 300, angle)
        self.game.all_sprites.add(projectile)
        self.game.enemy_projectiles.add(projectile)


class EnemyProjectile(pygame.sprite.Sprite):
    """Class for enemy projectiles."""

    def __init__(self, position, velocity, angle):
        """Initialize the enemy projectile.

        Args:
            position (tuple): Starting position of the projectile.
            velocity (pygame.math.Vector2): Velocity vector of the projectile.
            angle (float): Angle at which the projectile is fired.
        """
        super().__init__()
        # Load the projectile image
        self.image_orig = pygame.image.load('images/enemy_laser.png').convert_alpha()
        self.image_orig = pygame.transform.scale(self.image_orig, (9, ))
        # Rotate the image by the angle
        self.image = pygame.transform.rotate(self.image_orig, angle)
        self.rect = self.image.get_rect(center=position)
        self.pos = pygame.math.Vector2(position)
        self.velocity = velocity
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, delta_time):
        """Update enemy projectile position."""
        self.pos += self.velocity * delta_time
        self.rect.center = self.pos

        if (self.rect.right < 0 or self.rect.left > WIDTH or
                self.rect.bottom < 0 or self.rect.top > HEIGHT):
            self.kill()

class PowerUp(pygame.sprite.Sprite):
    """Class for power-ups."""

    def __init__(self, type_, position):
        """Initialize the power-up.

        Args:
            type_ (str): Type of power-up ('weapon', 'bomb', 'shield').
            position (tuple): Starting position of the power-up.
        """
        super().__init__()
        self.type = type_
        # Load the appropriate image based on the power-up type
        if self.type == 'weapon':
            image_path = 'images/powerup_weapon.png'
        elif self.type == 'bomb':
            image_path = 'images/powerup_bomb.png'
        elif self.type == 'shield':
            image_path = 'images/powerup_shield.png'
        else:
            image_path = 'images/powerup.png'  # Default power-up image

        self.image_orig = pygame.image.load(image_path).convert_alpha()
        self.image_orig = pygame.transform.scale(self.image_orig, (30, 30))
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect(center=position)
        self.velocity = pygame.math.Vector2(0, 100)
        self.angle = 0  # For rotation animation
        self.rotation_speed = 100  # Degrees per second
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, delta_time):
        """Update power-up position."""
        self.rect.move_ip(self.velocity.x * delta_time, self.velocity.y * delta_time)
        if self.rect.top > HEIGHT:
            self.kill()

        self.angle = (self.angle + self.rotation_speed * delta_time) % 360
        self.image = pygame.transform.rotate(self.image_orig, self.angle)
        self.rect = self.image.get_rect(center=self.rect.center)
        self.mask = pygame.mask.from_surface(self.image)

class Explosion(pygame.sprite.Sprite):
    """Class for explosions."""

    def __init__(self, position):
        """Initialize the explosion.

        Args:
            position (tuple): Position of the explosion.
        """
        super().__init__()
        # Load explosion animation frames
        self.frames = []
        for i in range(9):  # Assuming you have 9 frames named explosion0.png to explosion8.png
            frame = pygame.image.load(f'images/explosion{i}.png').convert_alpha()
            frame = pygame.transform.scale(frame, (75, 75))
            self.frames.append(frame)
        self.current_frame = 0
        self.image = self.frames[self.current_frame]
        self.rect = self.image.get_rect(center=position)
        self.frame_rate = 15  # Adjust as needed
        self.last_update = pygame.time.get_ticks()

    def update(self, delta_time):
        now = pygame.time.get_ticks()
        if now - self.last_update > 1000 // self.frame_rate:
            self.last_update = now
            self.current_frame += 1
            if self.current_frame >= len(self.frames):
                self.kill()
            else:
                center = self.rect.center
                self.image = self.frames[self.current_frame]
                self.rect = self.image.get_rect(center=center)

# Run the game
if __name__ == "__main__":
    game = Game()
    game.show_start_screen()
    if game.running:
        game.capture_initials()
    while game.running:
        game.new()
    pygame.quit()
    sys.exit()

