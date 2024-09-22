# plugins/powerup_system/main.py

import pygame
import random

def register(game):
    powerup_system = PowerUpSystem(game)
    game.register_plugin(powerup_system)
    # Expose the powerup_system instance for other plugins
    game.powerup_system = powerup_system

class PowerUpSystem:
    def __init__(self, game):
        self.game = game
        self.powerups = pygame.sprite.Group()
        self.game.all_sprites.add(self.powerups)
        self.powerup_types = {}
        self.next_powerup_time = random.randint(500, 1000)

    def register_powerup(self, name, powerup_class):
        """Register a new power-up type."""
        self.powerup_types[name] = powerup_class

    def update(self, game, delta_time):
        """Update the power-up system."""
        self.next_powerup_time -= 1
        if self.next_powerup_time <= 0:
            if self.powerup_types:
                powerup_type_name = random.choice(list(self.powerup_types.keys()))
                powerup_class = self.powerup_types[powerup_type_name]
                position = (random.randint(20, game.WIDTH - 20), -20)
                powerup = powerup_class(position, game)
                self.powerups.add(powerup)
                game.all_sprites.add(powerup)
            self.next_powerup_time = random.randint(500, 1000)

        self.powerups.update(delta_time)

        # Handle collisions with the player
        powerup_collision = pygame.sprite.spritecollide(
            game.player, self.powerups, True, pygame.sprite.collide_mask)
        for powerup in powerup_collision:
            powerup.apply(game)
            game.powerup_sound.play()

    def handle_event(self, game, event):
        pass  # Implement if needed

    def draw(self, game, screen):
        pass  # Implement if needed
