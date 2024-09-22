# plugins/powerup_shield/main.py

import pygame
import os

def register(game):
    powerup_system = getattr(game, 'powerup_system', None)
    if powerup_system:
        powerup_system.register_powerup('shield', ShieldPowerUp)
    else:
        print("PowerUpSystem not found. Ensure 'powerup_system' plugin is loaded before 'powerup_shield'.")

class ShieldPowerUp(pygame.sprite.Sprite):
    def __init__(self, position, game):
        super().__init__()
        self.game = game
        image_path = os.path.join(os.path.dirname(__file__), 'images', 'powerup_shield.png')
        if not os.path.exists(image_path):
            image_path = os.path.join('images', 'powerup.png')  # Default image in main images directory
        self.image_orig = pygame.image.load(image_path).convert_alpha()
        self.image_orig = pygame.transform.scale(self.image_orig, (30, 30))
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect(center=position)
        self.velocity = pygame.math.Vector2(0, 100)
        self.angle = 0
        self.rotation_speed = 100
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, delta_time):
        self.rect.move_ip(0, self.velocity.y * delta_time)
        if self.rect.top > self.game.HEIGHT:
            self.kill()
        self.angle = (self.angle + self.rotation_speed * delta_time) % 360
        self.image = pygame.transform.rotate(self.image_orig, self.angle)
        self.rect = self.image.get_rect(center=self.rect.center)
        self.mask = pygame.mask.from_surface(self.image)

    def apply(self, game):
        game.player.shield = 3
