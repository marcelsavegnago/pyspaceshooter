import pygame
import sys
import math
import random
import numpy as np
import os

# Initialize Pygame
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2)  # Using stereo

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
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
ORANGE = (255, 165, 0)

# Fonts
title_font = pygame.font.SysFont(None, 74)
menu_font = pygame.font.SysFont(None, 50)
game_font = pygame.font.SysFont(None, 30)

# Sampling frequency (samples per second)
SAMPLE_RATE = 44100


def apply_envelope(wave, attack, decay, sustain, release):
    """Apply ADSR envelope to the wave.

    Args:
        wave (numpy.ndarray): The wave to which the envelope is applied.
        attack (float): Duration of the attack phase (fraction of total duration).
        decay (float): Duration of the decay phase (fraction of total duration).
        sustain (float): Sustain level (0 to 1).
        release (float): Duration of the release phase (fraction of total duration).

    Returns:
        numpy.ndarray: The wave after applying the envelope.
    """
    n_samples = len(wave)
    envelope = np.ones(n_samples)

    # Calculate transition points
    attack_point = int(attack * n_samples)
    decay_point = int((attack + decay) * n_samples)
    release_point = int((1 - release) * n_samples)

    # Envelope segments
    if attack_point > 0:
        envelope[:attack_point] = np.linspace(0, 1, attack_point)
    if decay_point > attack_point:
        envelope[attack_point:decay_point] = np.linspace(1, sustain, decay_point - attack_point)
    envelope[decay_point:release_point] = sustain
    if release_point < n_samples:
        envelope[release_point:] = np.linspace(sustain, 0, n_samples - release_point)

    # Apply envelope to wave
    wave *= envelope
    return wave


def generate_sound(frequency, duration, volume=0.5, waveform='sine', attack=0.01, decay=0.1, sustain=0.7, release=0.1):
    """Generate a sound with ADSR envelope.

    Args:
        frequency (float): Frequency of the sound in Hz.
        duration (float): Duration of the sound in seconds.
        volume (float): Volume level (0.0 to 1.0).
        waveform (str): Type of waveform ('sine', 'square', 'noise').
        attack (float): Attack time (fraction of total duration).
        decay (float): Decay time (fraction of total duration).
        sustain (float): Sustain level (0.0 to 1.0).
        release (float): Release time (fraction of total duration).

    Returns:
        pygame.mixer.Sound: The generated sound.
    """
    n_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n_samples, False)

    if waveform == 'sine':
        wave = np.sin(frequency * t * 2 * np.pi)
    elif waveform == 'square':
        wave = np.sign(np.sin(frequency * t * 2 * np.pi))
    elif waveform == 'noise':
        wave = np.random.uniform(-1, 1, n_samples)
    else:
        wave = np.sin(frequency * t * 2 * np.pi)  # Default to sine

    # Apply ADSR envelope
    wave = apply_envelope(wave, attack, decay, sustain, release)

    wave *= volume

    # Convert to appropriate data type
    wave = np.int16(wave * 32767)

    # Check number of mixer channels
    channels = pygame.mixer.get_init()[2]
    if channels == 2:
        # Duplicate array for stereo
        wave = np.column_stack((wave, wave))

    sound = pygame.sndarray.make_sound(wave)
    return sound


def save_score(name, score):
    """Save player's score to a file.

    Args:
        name (str): Player's initials.
        score (int): Player's score.
    """
    with open("ranking.txt", "a") as file:
        file.write(f"{name}:{score}\n")


def load_ranking():
    """Load rankings from a file.

    Returns:
        list: Sorted list of tuples (name, score).
    """
    ranking = []
    if os.path.exists("ranking.txt"):
        with open("ranking.txt", "r") as file:
            for line in file:
                name, points = line.strip().split(":")
                ranking.append((name, int(points)))
    return sorted(ranking, key=lambda x: x[1], reverse=True)


class Game:
    """Main game class to encapsulate the game logic and state."""

    def __init__(self):
        """Initialize the game."""
        self.clock = pygame.time.Clock()
        self.playing = True
        self.running = True
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
        self.starry_background = StarryBackground(50)
        self.player_initials = ""
        self.player = Player()
        self.all_sprites.add(self.player)

        # Generate sounds for events with ADSR envelope and adjustments
        self.shot_sound = generate_sound(
            frequency=600,
            duration=0.2,
            volume=0.3,
            waveform='sine',
            attack=0.01,
            decay=0.05,
            sustain=0.5,
            release=0.2
        )

        self.explosion_sound = generate_sound(
            frequency=100,
            duration=0.5,
            volume=0.4,
            waveform='noise',
            attack=0.0,
            decay=0.2,
            sustain=0.3,
            release=0.3
        )

        self.powerup_sound = generate_sound(
            frequency=800,
            duration=0.4,
            volume=0.3,
            waveform='sine',
            attack=0.01,
            decay=0.1,
            sustain=0.7,
            release=0.2
        )

        self.life_loss_sound = generate_sound(
            frequency=400,
            duration=0.5,
            volume=0.3,
            waveform='sine',
            attack=0.01,
            decay=0.1,
            sustain=0.5,
            release=0.3
        )

    def new(self):
        """Start a new game."""
        self.all_sprites.empty()
        self.enemies.empty()
        self.projectiles.empty()
        self.enemy_projectiles.empty()
        self.powerups.empty()
        self.explosions.empty()
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
            self.clock.tick(60)
            self.events()
            self.update()
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

    def update(self):
        """Update game state."""
        self.all_sprites.update()
        self.starry_background.update()
        self.level_counter += 1

        if self.level_counter >= 1000:
            self.level_counter = 0
            self.level += 1

        if random.randint(1, max(60 - self.level * 2, 10)) == 1:
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

        # Collision detection
        collision = pygame.sprite.groupcollide(self.enemies, self.projectiles, True, True)
        if collision:
            for enemy in collision:
                self.score += 10
                enemy_explosion = Explosion(enemy.rect.center)
                self.all_sprites.add(enemy_explosion)
                self.explosions.add(enemy_explosion)
                self.explosion_sound.play()

        if pygame.sprite.spritecollide(self.player, self.enemy_projectiles, True):
            if self.player.shield > 0:
                self.player.shield -= 1
            else:
                self.player.lives -= 1
                self.life_loss_sound.play()
                if self.player.lives <= 0:
                    self.playing = False

        player_collision = pygame.sprite.spritecollide(self.player, self.enemies, True)
        if player_collision:
            if self.player.shield > 0:
                self.player.shield -= 1
            else:
                self.player.lives -= 1
                self.life_loss_sound.play()
                if self.player.lives <= 0:
                    self.playing = False

        powerup_collision = pygame.sprite.spritecollide(self.player, self.powerups, True)
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
        while menu_active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    menu_active = False
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        menu_active = False
                    if event.key == pygame.K_ESCAPE:
                        menu_active = False
                        self.running = False

            SCREEN.fill(BLACK)
            title_text = title_font.render("Py Space Shooter", True, WHITE)
            start_text = menu_font.render("Press Enter to Start", True, WHITE)
            quit_text = menu_font.render("Press Esc to Exit", True, WHITE)

            SCREEN.blit(title_text, ((WIDTH - title_text.get_width()) / 2, HEIGHT / 4))
            SCREEN.blit(start_text, ((WIDTH - start_text.get_width()) / 2, HEIGHT / 2))
            SCREEN.blit(quit_text, ((WIDTH - quit_text.get_width()) / 2, HEIGHT / 2 + 50))

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
            for i, (name, points) in enumerate(ranking[:5]):
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
            title_text = menu_font.render("Enter your initials (3 letters)", True, WHITE)
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
                speed = (i + 1) * 0.5  # Different speeds for each layer
                stars.append([x, y, size, speed])
            self.layers.append(stars)

    def update(self):
        """Update star positions."""
        for stars in self.layers:
            for star in stars:
                star[1] += star[3] * star[2]
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
        self.image_orig = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.polygon(self.image_orig, BLUE, [(20, 0), (0, 40), (40, 40)])
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect(center=(WIDTH / 2, HEIGHT / 2))
        self.pos = pygame.math.Vector2(self.rect.center)
        self.speed = 0
        self.angle = 0
        self.lives = 3
        self.weapon_level = 1
        self.powerup_timer = 0
        self.shield = 0

    def update(self):
        """Update player position and rotation."""
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.angle += 3
        if keys[pygame.K_RIGHT]:
            self.angle -= 3
        if keys[pygame.K_UP]:
            self.speed += 0.5
        elif keys[pygame.K_DOWN]:
            self.speed -= 0.5
        else:
            self.speed *= 0.95

        self.speed = max(min(self.speed, 10), -10)
        rad = math.radians(self.angle)
        self.pos.x += -self.speed * math.sin(rad)
        self.pos.y += -self.speed * math.cos(rad)

        self.pos.x %= WIDTH
        self.pos.y %= HEIGHT

        self.rect.center = self.pos
        self.image = pygame.transform.rotate(self.image_orig, self.angle)
        self.rect = self.image.get_rect(center=self.rect.center)

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
        front_tip = self.pos + direction * 20

        if self.weapon_level == 1:
            projectile = Projectile(front_tip, direction * 15)
            game.all_sprites.add(projectile)
            game.projectiles.add(projectile)
        elif self.weapon_level == 2:
            angles = [-10, 0, 10]
            for a in angles:
                rad_offset = math.radians(self.angle + a)
                direction_offset = pygame.math.Vector2(-math.sin(rad_offset), -math.cos(rad_offset))
                projectile = Projectile(front_tip, direction_offset * 15)
                game.all_sprites.add(projectile)
                game.projectiles.add(projectile)
        elif self.weapon_level >= 3:
            angles = [-20, -10, 0, 10, 20]
            for a in angles:
                rad_offset = math.radians(self.angle + a)
                direction_offset = pygame.math.Vector2(-math.sin(rad_offset), -math.cos(rad_offset))
                projectile = Projectile(front_tip, direction_offset * 15)
                game.all_sprites.add(projectile)
                game.projectiles.add(projectile)

        game.shot_sound.play()


class Projectile(pygame.sprite.Sprite):
    """Class for projectiles."""

    def __init__(self, position, velocity):
        """Initialize the projectile.

        Args:
            position (tuple): Starting position of the projectile.
            velocity (pygame.math.Vector2): Velocity vector of the projectile.
        """
        super().__init__()
        self.image = pygame.Surface((5, 5))
        self.image.fill(RED)
        self.rect = self.image.get_rect(center=position)
        self.pos = pygame.math.Vector2(position)
        self.velocity = velocity

    def update(self):
        """Update projectile position."""
        self.pos += self.velocity
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
        self.image_orig = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.polygon(self.image_orig, GREEN, [(20, 40), (0, 0), (40, 0)])
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect()
        self.pos = pygame.math.Vector2(random.randrange(WIDTH), -50)
        self.rect.center = self.pos
        base_speed = random.uniform(2, 5)
        self.velocity = pygame.math.Vector2(0, base_speed + level * 0.5)
        self.level = level

    def update(self):
        """Update enemy position."""
        self.pos += self.velocity
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
        pygame.draw.polygon(self.image_orig, MAGENTA, [(20, 40), (0, 0), (40, 0)])
        self.image = self.image_orig.copy()
        self.shoot_timer = random.randint(60, 120)
        self.player = player
        self.game = game

    def update(self):
        """Update shooter enemy position and check if it should shoot."""
        super().update()
        self.shoot_timer -= 1
        if self.shoot_timer <= 0:
            self.shoot()
            self.shoot_timer = random.randint(60, 120)

    def shoot(self):
        """Fire a projectile toward the player."""
        direction = (self.player.pos - self.pos).normalize()
        projectile = EnemyProjectile(self.pos, direction * 5)
        self.game.all_sprites.add(projectile)
        self.game.enemy_projectiles.add(projectile)


class EnemyProjectile(pygame.sprite.Sprite):
    """Class for enemy projectiles."""

    def __init__(self, position, velocity):
        """Initialize the enemy projectile.

        Args:
            position (tuple): Starting position of the projectile.
            velocity (pygame.math.Vector2): Velocity vector of the projectile.
        """
        super().__init__()
        self.image = pygame.Surface((5, 5))
        self.image.fill(CYAN)
        self.rect = self.image.get_rect(center=position)
        self.pos = pygame.math.Vector2(position)
        self.velocity = velocity

    def update(self):
        """Update enemy projectile position."""
        self.pos += self.velocity
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
        self.image = pygame.Surface((30, 30), pygame.SRCALPHA)
        self.angle = 0  # Angle for rotation
        self.rect = self.image.get_rect(center=position)
        self.velocity = pygame.math.Vector2(0, 2)

        if self.type == 'weapon':
            self.draw_star()
        elif self.type == 'bomb':
            self.draw_hexagon()
        elif self.type == 'shield':
            self.draw_polygon()

    def update(self):
        """Update power-up position."""
        self.rect.move_ip(self.velocity)
        if self.rect.top > HEIGHT:
            self.kill()

        self.angle = (self.angle + 5) % 360
        self.image = pygame.transform.rotate(self.image_orig, self.angle)
        self.rect = self.image.get_rect(center=self.rect.center)

    def draw_star(self):
        """Draw a star shape for the power-up."""
        self.image_orig = pygame.Surface((30, 30), pygame.SRCALPHA)
        color = RED
        points = []
        for n in range(5):
            x = 15 + 12 * math.cos(math.radians(72 * n - 90))
            y = 15 + 12 * math.sin(math.radians(72 * n - 90))
            points.append((x, y))
            x = 15 + 5 * math.cos(math.radians(72 * n - 54))
            y = 15 + 5 * math.sin(math.radians(72 * n - 54))
            points.append((x, y))
        pygame.draw.polygon(self.image_orig, color, points)

    def draw_hexagon(self):
        """Draw a hexagon shape for the power-up."""
        self.image_orig = pygame.Surface((30, 30), pygame.SRCALPHA)
        color = YELLOW
        points = []
        for n in range(6):
            x = 15 + 12 * math.cos(math.radians(60 * n))
            y = 15 + 12 * math.sin(math.radians(60 * n))
            points.append((x, y))
        pygame.draw.polygon(self.image_orig, color, points)

    def draw_polygon(self):
        """Draw a polygon shape for the power-up."""
        self.image_orig = pygame.Surface((30, 30), pygame.SRCALPHA)
        color = CYAN
        points = []
        for n in range(8):
            radius = 12 if n % 2 == 0 else 6
            x = 15 + radius * math.cos(math.radians(45 * n))
            y = 15 + radius * math.sin(math.radians(45 * n))
            points.append((x, y))
        pygame.draw.polygon(self.image_orig, color, points)


class Explosion(pygame.sprite.Sprite):
    """Class for explosions."""

    def __init__(self, position):
        """Initialize the explosion.

        Args:
            position (tuple): Position of the explosion.
        """
        super().__init__()
        self.radius = 1
        self.alpha = 255
        self.position = position
        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=position)

    def update(self):
        """Update explosion state."""
        self.radius += 10
        self.alpha -= 20
        if self.alpha <= 0:
            self.kill()
            return
        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 165, 0, self.alpha), (self.radius, self.radius), self.radius)
        self.rect = self.image.get_rect(center=self.position)


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
