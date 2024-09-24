# plugins/powerup_bomb/main.py

import pygame
import os

def register(game):
    powerup_system = getattr(game, 'powerup_system', None)
    if powerup_system:
        powerup_system.register_powerup('bomb', BombPowerUp)
        print("Bomb power-up registered with BombPowerUp.")
    else:
        print("PowerUpSystem not found. Ensure 'powerup_system' plugin is loaded before 'powerup_bomb'.")

class BombPowerUp(pygame.sprite.Sprite):
    def __init__(self, position, game):
        super().__init__()
        self.game = game
        image_path = os.path.join(os.path.dirname(__file__), 'images', 'powerup_bomb.png')
        if not os.path.exists(image_path):
            image_path = os.path.join('images', 'powerup.png')  # Imagem padrão no diretório principal
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
        for enemy in game.enemies:
            enemy_explosion = game.Explosion(enemy.rect.center)
            game.all_sprites.add(enemy_explosion)
            game.explosions.add(enemy_explosion)
            enemy.kill()
            game.score += 10
        # Criar uma explosão na posição do jogador
        explosion = game.Explosion(game.player.rect.center)
        game.all_sprites.add(explosion)
        game.explosions.add(explosion)
        game.explosion_sound.play()
        # Iniciar a vibração da tela com intensidade máxima
        game.shake_timer = 0.5
        game.shake_intensity = 10
