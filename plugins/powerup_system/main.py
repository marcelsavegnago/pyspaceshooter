# plugins/powerup_system/main.py

import pygame
import random

class Effect:
    """Base class for effects applied to the player."""
    def __init__(self, duration):
        self.duration = duration  # Duration of the effect in seconds
        self.remaining_time = duration

    def apply(self, player):
        """Apply the effect to the player."""
        pass

    def update(self, delta_time, player):
        """Update the effect, decreasing the remaining time."""
        self.remaining_time -= delta_time
        if self.remaining_time <= 0:
            self.remove(player)
            return False
        return True

    def remove(self, player):
        """Remove the effect from the player."""
        pass

def register(game):
    powerup_system = PowerUpSystem(game)
    game.register_plugin(powerup_system)
    game.powerup_system = powerup_system

class PowerUpSystem:
    def __init__(self, game):
        self.game = game
        self.powerups = pygame.sprite.Group()
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
            if hasattr(game, 'powerup_sound'):
                game.powerup_sound.play()

    def handle_event(self, game, event):
        pass

    def draw(self, game, screen):
        pass
