import pygame
import sys
import math
import random
import json
import os
import importlib.util
from collections import defaultdict

# Initialize Pygame
pygame.init()
pygame.mixer.init()

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
title_font = pygame.font.Font('fonts/space_font.ttf', 54)
menu_font = pygame.font.Font('fonts/space_font.ttf', 40)
game_font = pygame.font.Font('fonts/space_font.ttf', 24)

def save_score(name, score):
    """Save the player's score to a JSON file."""
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
    """Load the ranking from a JSON file."""
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

def load_plugins(game):
    """Load plugins from the 'plugins' directory, respecting dependencies."""
    plugins_dir = 'plugins'
    if not os.path.exists(plugins_dir):
        os.makedirs(plugins_dir)

    # Step 1: Scan plugin directories and read manifests
    plugin_manifests = {}
    plugin_dirs = [d for d in os.listdir(plugins_dir) if os.path.isdir(os.path.join(plugins_dir, d))]

    for plugin_name in plugin_dirs:
        manifest_path = os.path.join(plugins_dir, plugin_name, 'manifest.json')
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                manifest['path'] = os.path.join(plugins_dir, plugin_name)
                plugin_manifests[plugin_name] = manifest
        else:
            print(f"Manifest file missing for plugin '{plugin_name}'. Skipping.")

    # Step 2: Build dependency graph
    dependency_graph = defaultdict(list)
    plugins_to_remove = []
    for plugin_name, manifest in plugin_manifests.items():
        dependencies = manifest.get('dependencies', [])
        for dep in dependencies:
            if dep in plugin_manifests:
                dependency_graph[dep].append(plugin_name)
            else:
                print(f"Dependency '{dep}' for plugin '{plugin_name}' not found. Skipping plugin '{plugin_name}'.")
                plugins_to_remove.append(plugin_name)
                break

    # Remove plugins with missing dependencies
    for plugin_name in plugins_to_remove:
        del plugin_manifests[plugin_name]

    # Step 3: Determine loading order using topological sort
    loading_order = []
    visited = {}
    temp_mark = set()

    def visit(n):
        if n in temp_mark:
            raise Exception(f"Circular dependency detected: {n}")
        if n not in visited:
            temp_mark.add(n)
            for m in dependency_graph.get(n, []):
                visit(m)
            temp_mark.remove(n)
            visited[n] = True
            loading_order.append(n)

    try:
        for plugin_name in plugin_manifests.keys():
            visit(plugin_name)
    except Exception as e:
        print(f"Error determining plugin loading order: {e}")
        sys.exit(1)

    # Reverse loading order to load dependencies first
    loading_order.reverse()

    # Step 4: Load plugins in order
    for plugin_name in loading_order:
        manifest = plugin_manifests[plugin_name]
        plugin_path = manifest['path']
        main_py_path = os.path.join(plugin_path, 'main.py')
        spec = importlib.util.spec_from_file_location(plugin_name, main_py_path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            if hasattr(module, 'register'):
                module.register(game)
                print(f"Loaded plugin: {plugin_name}")
            else:
                print(f"Plugin '{plugin_name}' does not have a 'register' function.")
        except Exception as e:
            print(f"Error loading plugin '{plugin_name}': {e}")

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
        self.starry_background = StarryBackground(50)
        self.player_initials = ""
        self.difficulty = 'Normal'  # Default difficulty

        # Variables for screen shake effect
        self.shake_timer = 0
        self.shake_intensity = 0

        # Load sounds
        self.shot_sound = pygame.mixer.Sound('sounds/shot.ogg')
        self.explosion_sound = pygame.mixer.Sound('sounds/explosion.ogg')
        self.life_loss_sound = pygame.mixer.Sound('sounds/life_loss.ogg')
        self.powerup_sound = pygame.mixer.Sound('sounds/powerup.ogg')  # Adicione um som para power-ups

        # Set sound volumes
        self.shot_sound.set_volume(0.5)
        self.explosion_sound.set_volume(0.5)
        self.life_loss_sound.set_volume(0.5)
        self.powerup_sound.set_volume(0.5)

        # Load background music
        pygame.mixer.music.load('music/background.wav')
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)  # Loop indefinitely

        # Plugins list and callbacks
        self.plugins = []
        self.plugin_updates = []
        self.plugin_events = []
        self.plugin_draws = []

        # Expose screen dimensions and resources
        self.WIDTH = WIDTH
        self.HEIGHT = HEIGHT
        self.title_font = title_font
        self.menu_font = menu_font
        self.game_font = game_font
        self.BLACK = BLACK
        self.WHITE = WHITE
        self.GRAY = GRAY
        self.RED = RED
        self.YELLOW = YELLOW

        # Event handlers
        self.event_handlers = {
            'on_player_hit': [self.handle_player_hit],
            'on_player_collide_enemy': [self.handle_player_collide_enemy]
        }

    def register_plugin(self, plugin):
        """Register a plugin and its callbacks."""
        self.plugins.append(plugin)
        if hasattr(plugin, 'update'):
            self.plugin_updates.append(plugin.update)
        if hasattr(plugin, 'handle_event'):
            self.plugin_events.append(plugin.handle_event)
        if hasattr(plugin, 'draw'):
            self.plugin_draws.append(plugin.draw)

    def register_event_handler(self, event_name, handler):
        """Register an event handler."""
        if event_name in self.event_handlers:
            self.event_handlers[event_name].append(handler)
        else:
            self.event_handlers[event_name] = [handler]

    def trigger_event(self, event_name, *args, **kwargs):
        """Trigger an event."""
        for handler in self.event_handlers.get(event_name, []):
            handler(*args, **kwargs)

    def new(self):
        """Start a new game."""
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.enemy_projectiles = pygame.sprite.Group()
        self.explosions = pygame.sprite.Group()
        self.score = 0
        self.level = 1
        self.level_counter = 0
        self.player = Player()
        self.all_sprites.add(self.player)
        self.starry_background = StarryBackground(50)
        self.Explosion = Explosion  # Expose Explosion class to plugins

        # Load plugins after initializing player and other attributes
        load_plugins(self)
        self.run()

    def run(self):
        """Main game loop."""
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
                    if not self.player.invulnerable:
                        self.player.shoot(self)
                elif event.key == pygame.K_ESCAPE:
                    self.pause_menu()
            # Call plugin event handlers
            for plugin_event in self.plugin_events:
                plugin_event(self, event)

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

        # Decrease screen shake timer
        if self.shake_timer > 0:
            self.shake_timer -= delta_time
            if self.shake_timer <= 0:
                self.shake_timer = 0
                self.shake_intensity = 0  # Reset intensity when shake ends

        # Collision detection with masks for pixel-perfect collisions
        if not self.player.invulnerable:
            collision = pygame.sprite.groupcollide(
                self.enemies, self.projectiles, True, True, pygame.sprite.collide_mask)
            if collision:
                for enemy in collision:
                    self.score += 10
                    enemy_explosion = Explosion(enemy.rect.center)
                    self.all_sprites.add(enemy_explosion)
                    self.explosions.add(enemy_explosion)
                    self.explosion_sound.play()
                    # Start screen shake with reduced intensity
                    if self.shake_intensity < 7:
                        self.shake_intensity = 7
                    if self.shake_timer < 0.3:
                        self.shake_timer = 0.3

            # Collision com projéteis inimigos
            if pygame.sprite.spritecollide(self.player, self.enemy_projectiles, True, pygame.sprite.collide_mask):
                self.trigger_event('on_player_hit')

            # Collision com inimigos
            player_collision = pygame.sprite.spritecollide(
                self.player, self.enemies, True, pygame.sprite.collide_mask)
            if player_collision:
                self.trigger_event('on_player_collide_enemy')

        # Call plugin update functions
        for plugin_update in self.plugin_updates:
            plugin_update(self, delta_time)

    def draw(self):
        """Draw everything on the screen."""
        # Create a temporary surface
        temp_surface = pygame.Surface((WIDTH, HEIGHT))
        temp_surface.fill(BLACK)

        # Desenhar a fundo estrelado e sprites na superfície temporária
        self.starry_background.draw(temp_surface)

        # Desenhar o jogador com efeito de piscar se estiver invulnerável
        if self.player.invulnerable:
            if (pygame.time.get_ticks() // 100) % 2 == 0:
                self.all_sprites.remove(self.player)
            else:
                if self.player not in self.all_sprites:
                    self.all_sprites.add(self.player)
        else:
            if self.player not in self.all_sprites:
                self.all_sprites.add(self.player)

        # Desenhar todos os sprites
        self.all_sprites.draw(temp_surface)

        # Aplicar efeito de tremor de tela
        if self.shake_timer > 0:
            shake_offset_x = random.randint(-self.shake_intensity, self.shake_intensity)
            shake_offset_y = random.randint(-self.shake_intensity, self.shake_intensity)
        else:
            shake_offset_x = 0
            shake_offset_y = 0

        # Blit a superfície temporária na tela principal com offset
        SCREEN.blit(temp_surface, (shake_offset_x, shake_offset_y))

        # Desenhar elementos de UI
        score_text = self.game_font.render(f"Score: {self.score}", True, self.WHITE)
        lives_text = self.game_font.render(f"Lives: {self.player.lives}", True, self.WHITE)
        level_text = self.game_font.render(f"Level: {self.level}", True, self.WHITE)
        SCREEN.blit(score_text, (10, 10))
        SCREEN.blit(lives_text, (10, 40))
        SCREEN.blit(level_text, (10, 70))

        # Mostrar escudos restantes
        if self.player.custom_attributes.get('shield_active', False):
            shield_uses = self.player.custom_attributes.get('shield_uses', 0)
            shield_text = self.game_font.render(f"Shields: {shield_uses}", True, self.WHITE)
            SCREEN.blit(shield_text, (10, 100))

        # Call plugin draw functions
        for plugin_draw in self.plugin_draws:
            plugin_draw(self, SCREEN)

        pygame.display.flip()

    def handle_player_hit(self):
        """Handler para quando o player é atingido por um projétil."""
        if self.player.custom_attributes.get('shield_active', False):
            self.player.custom_attributes['shield_uses'] -= 1
            print(f"Shield absorbed the hit! Remaining uses: {self.player.custom_attributes['shield_uses']}")
            if self.player.custom_attributes['shield_uses'] <= 0:
                self.player.custom_attributes['shield_active'] = False
                self.player.custom_attributes.pop('shield_uses', None)
                print("Shield deactivated")
        else:
            self.player.lives -= 1
            self.life_loss_sound.play()
            if self.player.lives <= 0:
                self.playing = False  # Termina o jogo
            else:
                # Ativar invulnerabilidade temporária
                self.player.invulnerable = True
                self.player.invulnerable_timer = 2  # Invulnerabilidade por 2 segundos
                print("Player hit! Invulnerable for 2 seconds.")

    def handle_player_collide_enemy(self):
        """Handler para quando o player colide com um inimigo."""
        if self.player.custom_attributes.get('shield_active', False):
            self.player.custom_attributes['shield_uses'] -= 1
            print(f"Shield absorbed the collision! Remaining uses: {self.player.custom_attributes['shield_uses']}")
            if self.player.custom_attributes['shield_uses'] <= 0:
                self.player.custom_attributes['shield_active'] = False
                self.player.custom_attributes.pop('shield_uses', None)
                print("Shield deactivated")
        else:
            self.player.lives -= 1
            self.explosion_sound.play()
            if self.player.lives <= 0:
                self.playing = False  # Termina o jogo
            else:
                # Ativar invulnerabilidade temporária
                self.player.invulnerable = True
                self.player.invulnerable_timer = 2  # Invulnerabilidade por 2 segundos
                print("Player collided with enemy! Invulnerable for 2 seconds.")

    def register_plugin(self, plugin):
        """Register a plugin and its callbacks."""
        self.plugins.append(plugin)
        if hasattr(plugin, 'update'):
            self.plugin_updates.append(plugin.update)
        if hasattr(plugin, 'handle_event'):
            self.plugin_events.append(plugin.handle_event)
        if hasattr(plugin, 'draw'):
            self.plugin_draws.append(plugin.draw)

    def register_event_handler(self, event_name, handler):
        """Register an event handler."""
        if event_name in self.event_handlers:
            self.event_handlers[event_name].append(handler)
        else:
            self.event_handlers[event_name] = [handler]

    def trigger_event(self, event_name, *args, **kwargs):
        """Trigger an event."""
        for handler in self.event_handlers.get(event_name, []):
            handler(*args, **kwargs)

    def new(self):
        """Start a new game."""
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.enemy_projectiles = pygame.sprite.Group()
        self.explosions = pygame.sprite.Group()
        self.score = 0
        self.level = 1
        self.level_counter = 0
        self.player = Player()
        self.all_sprites.add(self.player)
        self.starry_background = StarryBackground(50)
        self.Explosion = Explosion  # Expose Explosion class to plugins

        # Load plugins after initializing player and other attributes
        load_plugins(self)
        self.run()

    def run(self):
        """Main game loop."""
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
            # Call plugin event handlers
            for plugin_event in self.plugin_events:
                plugin_event(self, event)

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

        # Decrease screen shake timer
        if self.shake_timer > 0:
            self.shake_timer -= delta_time
            if self.shake_timer <= 0:
                self.shake_timer = 0
                self.shake_intensity = 0  # Reset intensity when shake ends

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
                # Start screen shake with reduced intensity
                if self.shake_intensity < 7:
                    self.shake_intensity = 7
                if self.shake_timer < 0.3:
                    self.shake_timer = 0.3

        # Collision with enemy projectiles
        if pygame.sprite.spritecollide(self.player, self.enemy_projectiles, True, pygame.sprite.collide_mask):
            self.trigger_event('on_player_hit')

        # Collision with enemies
        player_collision = pygame.sprite.spritecollide(
            self.player, self.enemies, True, pygame.sprite.collide_mask)
        if player_collision:
            self.trigger_event('on_player_collide_enemy')

        # Call plugin update functions
        for plugin_update in self.plugin_updates:
            plugin_update(self, delta_time)

    def draw(self):
        """Draw everything on the screen."""
        # Create a temporary surface
        temp_surface = pygame.Surface((WIDTH, HEIGHT))
        temp_surface.fill(BLACK)

        # Draw the starry background and sprites on the temporary surface
        self.starry_background.draw(temp_surface)
        self.all_sprites.draw(temp_surface)

        # Apply screen shake effect
        if self.shake_timer > 0:
            shake_offset_x = random.randint(-self.shake_intensity, self.shake_intensity)
            shake_offset_y = random.randint(-self.shake_intensity, self.shake_intensity)
        else:
            shake_offset_x = 0
            shake_offset_y = 0

        # Blit the temporary surface onto the main screen with offset
        SCREEN.blit(temp_surface, (shake_offset_x, shake_offset_y))

        # Draw UI elements directly on the main screen
        score_text = self.game_font.render(f"Score: {self.score}", True, self.WHITE)
        lives_text = self.game_font.render(f"Lives: {self.player.lives}", True, self.WHITE)
        level_text = self.game_font.render(f"Level: {self.level}", True, self.WHITE)
        SCREEN.blit(score_text, (10, 10))
        SCREEN.blit(lives_text, (10, 40))
        SCREEN.blit(level_text, (10, 70))

        # Mostrar escudos restantes
        if self.player.custom_attributes.get('shield_active', False):
            shield_uses = self.player.custom_attributes.get('shield_uses', 0)
            shield_text = self.game_font.render(f"Shields: {shield_uses}", True, self.WHITE)
            SCREEN.blit(shield_text, (10, 100))

        # Call plugin draw functions
        for plugin_draw in self.plugin_draws:
            plugin_draw(self, SCREEN)

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
            title_text = self.title_font.render("Py Space Shooter", True, WHITE)
            SCREEN.blit(title_text, ((WIDTH - title_text.get_width()) / 2, HEIGHT / 4))

            for i, option in enumerate(options):
                color = WHITE if i == selected_option else GRAY
                text = self.menu_font.render(option, True, color)
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
            title_text = self.title_font.render("High Scores", True, WHITE)
            SCREEN.blit(title_text, ((WIDTH - title_text.get_width()) / 2, 50))

            ranking = load_ranking()
            if ranking:
                for i, entry in enumerate(ranking[:10]):
                    name = entry['name']
                    points = entry['score']
                    ranking_line = self.game_font.render(f"{i + 1}. {name} - {points}", True, WHITE)
                    SCREEN.blit(ranking_line, (WIDTH // 4, 150 + i * 40))
            else:
                no_scores_text = self.game_font.render("No high scores yet.", True, WHITE)
                SCREEN.blit(no_scores_text, ((WIDTH - no_scores_text.get_width()) / 2, HEIGHT / 2))

            back_text = self.game_font.render("Press ESC to return", True, GRAY)
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
            title_text = self.title_font.render("Settings", True, WHITE)
            SCREEN.blit(title_text, ((WIDTH - title_text.get_width()) / 2, 50))

            for i, option in enumerate(options):
                color = WHITE if i == selected_option else GRAY
                if option == "Volume":
                    text = self.menu_font.render(f"{option}: {volume_level}", True, color)
                elif option == "Difficulty":
                    text = self.menu_font.render(f"{option}: {self.difficulty}", True, color)
                else:
                    text = self.menu_font.render(option, True, color)
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
            title_text = self.title_font.render("PAUSE", True, WHITE)
            SCREEN.blit(title_text, ((WIDTH - title_text.get_width()) / 2, HEIGHT / 4))

            for i, option in enumerate(options):
                color = WHITE if i == selected_option else GRAY
                text = self.menu_font.render(option, True, color)
                SCREEN.blit(text, ((WIDTH - text.get_width()) / 2, HEIGHT / 2 + i * 50))

            pygame.display.flip()
            self.clock.tick(60)

    def game_over(self):
        """Display the game over screen and save the score."""
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
            game_over_text = self.title_font.render("GAME OVER", True, RED)
            score_text = self.menu_font.render(f"Your Score: {self.score}", True, WHITE)
            restart_text = self.menu_font.render("Press Enter to Restart", True, WHITE)
            quit_text = self.menu_font.render("Press Esc to Exit", True, WHITE)

            # Display title and options on the screen
            SCREEN.blit(game_over_text, ((WIDTH - game_over_text.get_width()) / 2, 50))
            SCREEN.blit(score_text, ((WIDTH - score_text.get_width()) / 2, 150))
            SCREEN.blit(restart_text, ((WIDTH - restart_text.get_width()) / 2, 500))
            SCREEN.blit(quit_text, ((WIDTH - quit_text.get_width()) / 2, 550))

            # Ranking Title
            ranking_title = self.menu_font.render("Ranking - Top 5", True, WHITE)
            SCREEN.blit(ranking_title, (WIDTH // 4, 200))

            # Display the ranking with highlight for the player
            for i, entry in enumerate(ranking[:5]):
                name = entry['name']
                points = entry['score']
                color = WHITE if name != self.player_initials else YELLOW  # Highlight current player
                ranking_line = self.game_font.render(f"{i + 1}. {name} - {points}", True, color)
                SCREEN.blit(ranking_line, (WIDTH // 4, 250 + i * 40))  # Space between lines

            pygame.display.flip()
            self.clock.tick(60)

    def capture_initials(self):
        """Capture the player's initials."""
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
            title_text = self.menu_font.render("Enter your initials", True, WHITE)
            initials_text = self.menu_font.render(initials, True, WHITE)
            SCREEN.blit(title_text, ((WIDTH - title_text.get_width()) / 2, HEIGHT / 2 - 50))
            SCREEN.blit(initials_text, ((WIDTH - initials_text.get_width()) / 2, HEIGHT / 2))

            pygame.display.flip()
            self.clock.tick(60)

        self.player_initials = initials

class StarryBackground:
    """Class for the starry background with parallax effect."""

    def __init__(self, num_stars):
        """Initialize the starry background."""
        self.layers = []
        for i in range(3):  # Three layers for parallax effect
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
        """Draw the stars on the screen."""
        for stars in self.layers:
            for star in stars:
                pygame.draw.circle(screen, WHITE, (int(star[0]), int(star[1])), star[2])

class Player(pygame.sprite.Sprite):
    """Class for the player."""

    def __init__(self):
        """Initialize the player."""
        super().__init__()
        self.image_orig = pygame.image.load('images/player_ship.png').convert_alpha()
        self.image_orig = pygame.transform.scale(self.image_orig, (50, 50))
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect(center=(WIDTH / 2, HEIGHT / 2))
        self.pos = pygame.math.Vector2(self.rect.center)
        self.speed = 0
        self.angle = 0
        self.lives = 3
        self.mask = pygame.mask.from_surface(self.image)
        self.custom_attributes = {'weapon_level': 1}  # Inicializa com nível 1
        self.effects = []  # Lista de efeitos ativos

        # Invulnerabilidade
        self.invulnerable = False
        self.invulnerable_timer = 0

    def update(self, delta_time):
        """Update the player's position and rotation."""
        keys = pygame.key.get_pressed()
        rotation_speed = 200  # Degrees per second
        acceleration = 300    # Pixels per second squared
        max_speed = 300       # Pixels per second
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

        # Atualizar invulnerabilidade
        if self.invulnerable:
            self.invulnerable_timer -= delta_time
            if self.invulnerable_timer <= 0:
                self.invulnerable = False

        # Atualizar efeitos ativos
        self.effects = [effect for effect in self.effects if not effect.update(delta_time, self)]

    def shoot(self, game):
        """Fire a projectile considering the weapon level."""
        weapon_level = self.custom_attributes.get('weapon_level', 1)
        rad = math.radians(self.angle)
        direction = pygame.math.Vector2(-math.sin(rad), -math.cos(rad))
        front_tip = self.pos + direction * 25

        # Base projectile
        projectile = Projectile(front_tip, direction * 500, self.angle)
        game.all_sprites.add(projectile)
        game.projectiles.add(projectile)

        # Projetos adicionais com base no weapon_level
        if weapon_level >= 2:
            # Exemplo: dispara duas balas em ângulos ligeiramente diferentes
            offset_angle = 10  # Ângulo de desvio
            rad_left = math.radians(self.angle + offset_angle)
            direction_left = pygame.math.Vector2(-math.sin(rad_left), -math.cos(rad_left))
            front_tip_left = self.pos + direction_left * 25
            projectile_left = Projectile(front_tip_left, direction_left * 500, self.angle + offset_angle)
            game.all_sprites.add(projectile_left)
            game.projectiles.add(projectile_left)

            rad_right = math.radians(self.angle - offset_angle)
            direction_right = pygame.math.Vector2(-math.sin(rad_right), -math.cos(rad_right))
            front_tip_right = self.pos + direction_right * 25
            projectile_right = Projectile(front_tip_right, direction_right * 500, self.angle - offset_angle)
            game.all_sprites.add(projectile_right)
            game.projectiles.add(projectile_right)

        # Adicione mais condições para níveis superiores, se desejar

        game.shot_sound.play()

    def add_effect(self, effect):
        """Add an effect to the player."""
        self.effects.append(effect)
        effect.apply(self)

class Effect:
    """Class representing a generic effect applied to the player."""
    
    def __init__(self, duration):
        """
        Initialize the effect.
        
        Args:
            duration (int): Duration of the effect in seconds.
        """
        self.duration = duration * 60  # Convert to frames (assuming 60 FPS)
        self.remaining_time = self.duration

    def update(self, player, delta_time):
        """Update the effect's state."""
        self.remaining_time -= delta_time * 60
        if self.remaining_time <= 0:
            self.end(player)

    def is_active(self):
        """Check if the effect is still active."""
        return self.remaining_time > 0

    def apply(self, player):
        """Apply the effect to the player. Should be overridden by subclasses."""
        pass

    def end(self, player):
        """Remove the effect from the player. Should be overridden by subclasses."""
        pass

class Projectile(pygame.sprite.Sprite):
    """Class for projectiles."""

    def __init__(self, position, velocity, angle):
        """Initialize the projectile."""
        super().__init__()
        self.image_orig = pygame.image.load('images/laser.png').convert_alpha()
        self.image_orig = pygame.transform.scale(self.image_orig, (10, 30))
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
        """Initialize the enemy."""
        super().__init__()
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
        """Initialize the shooter enemy."""
        super().__init__(level)
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
        """Initialize the enemy projectile."""
        super().__init__()
        self.image_orig = pygame.image.load('images/enemy_laser.png').convert_alpha()
        self.image_orig = pygame.transform.scale(self.image_orig, (9, 30))
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

class Explosion(pygame.sprite.Sprite):
    """Class for explosions."""

    def __init__(self, position):
        """Initialize the explosion."""
        super().__init__()
        self.frames = []
        for i in range(9):  # Ensure you have 9 frames named explosion0.png to explosion8.png
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