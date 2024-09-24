# plugins/shields/main.py

import pygame
import random
import os
from plugins.powerup_system.main import Effect

def register(game):
    powerup_system = getattr(game, 'powerup_system', None)
    if powerup_system:
        powerup_system.register_powerup('shield', ShieldPowerUp)
        print("Shield power-up registered with PowerUpSystem.")
    else:
        print("PowerUpSystem not found. Ensure 'powerup_system' plugin is loaded before 'powerup_shield'.")

class ShieldPowerUp(pygame.sprite.Sprite):
    def __init__(self, position, game):
        super().__init__()
        self.game = game
        # Carregar a imagem do escudo
        image_path = os.path.join(os.path.dirname(__file__), 'images', 'powerup_shield.png')
        if not os.path.exists(image_path):
            image_path = 'images/powerup_shield.png'
        self.image_orig = pygame.image.load(image_path).convert_alpha()
        self.image_orig = pygame.transform.scale(self.image_orig, (30, 30))
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect(center=position)
        self.velocity = pygame.math.Vector2(0, 100)
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, delta_time):
        """Atualiza a posição do power-up."""
        self.rect.move_ip(0, self.velocity.y * delta_time)
        if self.rect.top > self.game.HEIGHT:
            self.kill()

    def apply(self, game):
        """Aplica o efeito de power-up de escudo ao jogador."""
        shield_effect = ShieldEffect(duration=10, uses=3)  # Duração de 10 segundos com 3 usos
        game.player.add_effect(shield_effect)
        print("Shield power-up applied to player.")

class ShieldEffect(Effect):
    def __init__(self, duration, uses=3):
        super().__init__(duration)
        self.uses = uses

    def apply(self, player):
        """Ativa o escudo do player com um número específico de usos."""
        player.custom_attributes['shield_active'] = True
        player.custom_attributes['shield_uses'] = self.uses
        print(f"Shield activated with {self.uses} uses")

    def remove(self, player):
        """Desativa o escudo do player."""
        player.custom_attributes['shield_active'] = False
        player.custom_attributes.pop('shield_uses', None)
        print("Shield deactivated")
