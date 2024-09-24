# plugins/powerup_weapon/main.py

import pygame
import os
from plugins.powerup_system.main import Effect

def register(game):
    powerup_system = getattr(game, 'powerup_system', None)
    if powerup_system:
        powerup_system.register_powerup('weapon', WeaponPowerUp)
        print("Weapon power-up registered with PowerUpSystem.")
    else:
        print("PowerUpSystem not found. Ensure 'powerup_system' plugin is loaded before 'powerup_weapon'.")

class WeaponPowerUp(pygame.sprite.Sprite):
    def __init__(self, position, game):
        super().__init__()
        self.game = game
        # Carregar a imagem do power-up de arma
        image_path = os.path.join(os.path.dirname(__file__), 'images', 'powerup_weapon.png')
        if not os.path.exists(image_path):
            image_path = 'images/powerup_weapon.png'  # Caminho padrão
        self.image_orig = pygame.image.load(image_path).convert_alpha()
        self.image_orig = pygame.transform.scale(self.image_orig, (30, 30))
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect(center=position)
        self.velocity = pygame.math.Vector2(0, 100)
        self.angle = 0  # Para animação de rotação
        self.rotation_speed = 100  # Graus por segundo
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, delta_time):
        """Atualiza a posição e rotação do power-up."""
        self.rect.move_ip(0, self.velocity.y * delta_time)
        if self.rect.top > self.game.HEIGHT:
            self.kill()
        self.angle = (self.angle + self.rotation_speed * delta_time) % 360
        self.image = pygame.transform.rotate(self.image_orig, self.angle)
        self.rect = self.image.get_rect(center=self.rect.center)
        self.mask = pygame.mask.from_surface(self.image)

    def apply(self, game):
        """Aplica o efeito de power-up de arma ao jogador."""
        weapon_effect = WeaponEffect(duration=10)  # Duração de 10 segundos
        game.player.add_effect(weapon_effect)
        print("Weapon power-up applied to player.")

class WeaponEffect(Effect):
    def __init__(self, duration):
        super().__init__(duration)
        self.weapon_level_increased = False

    def apply(self, player):
        """Aumenta o nível da arma do jogador."""
        player.custom_attributes['weapon_level'] = player.custom_attributes.get('weapon_level', 1) + 1
        self.weapon_level_increased = True
        print(f"Weapon level increased to {player.custom_attributes['weapon_level']}")

    def remove(self, player):
        """Reseta o nível da arma do jogador para o nível anterior."""
        if self.weapon_level_increased:
            player.custom_attributes['weapon_level'] = max(player.custom_attributes.get('weapon_level', 1) - 1, 1)
            print(f"Weapon level reverted to {player.custom_attributes['weapon_level']}")
