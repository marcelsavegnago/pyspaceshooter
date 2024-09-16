import pygame
import sys
import math
import random
import numpy as np
import os

# Inicialização do Pygame
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2)  # Usando estéreo

# Configurações da tela
LARGURA = 800
ALTURA = 600
TELA = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Py Space Shooter")

# Definição de cores
PRETO = (0, 0, 0)
BRANCO = (255, 255, 255)
CINZA = (100, 100, 100)
VERMELHO = (255, 0, 0)
VERDE = (0, 255, 0)
AZUL = (0, 0, 255)
AMARELO = (255, 255, 0)
CIANO = (0, 255, 255)
MAGENTA = (255, 0, 255)
LARANJA = (255, 165, 0)

# Fonte
fonte_titulo = pygame.font.SysFont(None, 74)
fonte_menu = pygame.font.SysFont(None, 50)
fonte_jogo = pygame.font.SysFont(None, 30)

# Frequência de amostragem (samples per second)
FREQ_AMOSTRAGEM = 44100

# Função para gerar envelope ADSR
def aplicar_envelope(onda, ataque, decaimento, sustentacao, liberacao):
    n_amostras = len(onda)
    envelope = np.ones(n_amostras)
    
    # Calcula os pontos de transição
    ponto_ataque = int(ataque * n_amostras)
    ponto_decaimento = int((ataque + decaimento) * n_amostras)
    ponto_liberacao = int((1 - liberacao) * n_amostras)
    
    # Segmentos do envelope
    if ponto_ataque > 0:
        envelope[:ponto_ataque] = np.linspace(0, 1, ponto_ataque)
    if ponto_decaimento > ponto_ataque:
        envelope[ponto_ataque:ponto_decaimento] = np.linspace(1, sustentacao, ponto_decaimento - ponto_ataque)
    envelope[ponto_decaimento:ponto_liberacao] = sustentacao
    if ponto_liberacao < n_amostras:
        envelope[ponto_liberacao:] = np.linspace(sustentacao, 0, n_amostras - ponto_liberacao)
    
    # Aplica o envelope à onda
    onda *= envelope
    return onda

# Função para gerar sons
def gerar_som(frequencia, duracao, volume=0.5, waveform='sine', ataque=0.01, decaimento=0.1, sustentacao=0.7, liberacao=0.1):
    n_amostras = int(FREQ_AMOSTRAGEM * duracao)
    t = np.linspace(0, duracao, n_amostras, False)

    if waveform == 'sine':
        onda = np.sin(frequencia * t * 2 * np.pi)
    elif waveform == 'square':
        onda = np.sign(np.sin(frequencia * t * 2 * np.pi))
    elif waveform == 'noise':
        onda = np.random.uniform(-1, 1, n_amostras)
    else:
        onda = np.sin(frequencia * t * 2 * np.pi)  # Padrão para seno

    # Aplica o envelope ADSR
    onda = aplicar_envelope(onda, ataque, decaimento, sustentacao, liberacao)

    onda *= volume

    # Converte para tipo de dados adequado
    onda = np.int16(onda * 32767)

    # Verifica o número de canais do mixer
    canais = pygame.mixer.get_init()[2]
    if canais == 2:
        # Duplicar o array para estéreo
        onda = np.column_stack((onda, onda))

    som = pygame.sndarray.make_sound(onda)
    return som

# Gerar sons para eventos com envelope ADSR e ajustes
som_tiro = gerar_som(
    frequencia=600,
    duracao=0.2,
    volume=0.3,
    waveform='sine',
    ataque=0.01,
    decaimento=0.05,
    sustentacao=0.5,
    liberacao=0.2
)

som_explosao = gerar_som(
    frequencia=100,
    duracao=0.5,
    volume=0.4,
    waveform='noise',
    ataque=0.0,
    decaimento=0.2,
    sustentacao=0.3,
    liberacao=0.3
)

som_powerup = gerar_som(
    frequencia=800,
    duracao=0.4,
    volume=0.3,
    waveform='sine',
    ataque=0.01,
    decaimento=0.1,
    sustentacao=0.7,
    liberacao=0.2
)

som_perda_vida = gerar_som(
    frequencia=400,
    duracao=0.5,
    volume=0.3,
    waveform='sine',
    ataque=0.01,
    decaimento=0.1,
    sustentacao=0.5,
    liberacao=0.3
)

# Função para salvar pontuações no arquivo
def salvar_pontuacao(nome, pontuacao):
    with open("ranking.txt", "a") as arquivo:
        arquivo.write(f"{nome}:{pontuacao}\n")

# Função para carregar o ranking
def carregar_ranking():
    ranking = []
    if os.path.exists("ranking.txt"):
        with open("ranking.txt", "r") as arquivo:
            for linha in arquivo:
                nome, pontos = linha.strip().split(":")
                ranking.append((nome, int(pontos)))
    return sorted(ranking, key=lambda x: x[1], reverse=True)

# Classe para o fundo estrelado com efeito de parallax
class FundoEstrelado:
    def __init__(self, num_estrelas):
        self.camadas = []
        for i in range(3):  # Três camadas para o efeito de parallax
            estrelas = []
            for _ in range(num_estrelas):
                x = random.randrange(0, LARGURA)
                y = random.randrange(0, ALTURA)
                tamanho = random.choice([1, 2])
                velocidade = (i + 1) * 0.5  # Diferentes velocidades para cada camada
                estrelas.append([x, y, tamanho, velocidade])
            self.camadas.append(estrelas)

    def update(self):
        for estrelas in self.camadas:
            for estrela in estrelas:
                estrela[1] += estrela[3] * estrela[2]
                if estrela[1] > ALTURA:
                    estrela[0] = random.randrange(0, LARGURA)
                    estrela[1] = -estrela[2]
                    estrela[2] = random.choice([1, 2])

    def draw(self, tela):
        for estrelas in self.camadas:
            for estrela in estrelas:
                pygame.draw.circle(tela, BRANCO, (int(estrela[0]), int(estrela[1])), estrela[2])

# Classe para o jogador
class Jogador(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image_orig = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.polygon(self.image_orig, AZUL, [(20, 0), (0, 40), (40, 40)])
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect(center=(LARGURA / 2, ALTURA / 2))
        self.pos = pygame.math.Vector2(self.rect.center)
        self.velocidade = 0
        self.angulo = 0
        self.vidas = 3
        self.nivel_arma = 1
        self.temporizador_powerup = 0
        self.escudo = 0

    def update(self):
        teclas = pygame.key.get_pressed()
        if teclas[pygame.K_LEFT]:
            self.angulo += 3
        if teclas[pygame.K_RIGHT]:
            self.angulo -= 3
        if teclas[pygame.K_UP]:
            self.velocidade += 0.5
        elif teclas[pygame.K_DOWN]:
            self.velocidade -= 0.5
        else:
            self.velocidade *= 0.95

        self.velocidade = max(min(self.velocidade, 10), -10)
        rad = math.radians(self.angulo)
        self.pos.x += -self.velocidade * math.sin(rad)
        self.pos.y += -self.velocidade * math.cos(rad)

        self.pos.x %= LARGURA
        self.pos.y %= ALTURA

        self.rect.center = self.pos
        self.image = pygame.transform.rotate(self.image_orig, self.angulo)
        self.rect = self.image.get_rect(center=self.rect.center)

        if self.temporizador_powerup > 0:
            self.temporizador_powerup -= 1
            if self.temporizador_powerup == 0:
                self.nivel_arma = 1

    def disparar(self):
        rad = math.radians(self.angulo)
        direcao = pygame.math.Vector2(-math.sin(rad), -math.cos(rad))
        ponta_frontal = self.pos + direcao * 20

        if self.nivel_arma == 1:
            projetil = Projetil(ponta_frontal, direcao * 15)
            todos_sprites.add(projetil)
            projeteis.add(projetil)
        elif self.nivel_arma == 2:
            angulos = [-10, 0, 10]
            for a in angulos:
                rad_offset = math.radians(self.angulo + a)
                direcao_offset = pygame.math.Vector2(-math.sin(rad_offset), -math.cos(rad_offset))
                projetil = Projetil(ponta_frontal, direcao_offset * 15)
                todos_sprites.add(projetil)
                projeteis.add(projetil)
        elif self.nivel_arma >= 3:
            angulos = [-20, -10, 0, 10, 20]
            for a in angulos:
                rad_offset = math.radians(self.angulo + a)
                direcao_offset = pygame.math.Vector2(-math.sin(rad_offset), -math.cos(rad_offset))
                projetil = Projetil(ponta_frontal, direcao_offset * 15)
                todos_sprites.add(projetil)
                projeteis.add(projetil)

        som_tiro.play()

# Classe para os projéteis
class Projetil(pygame.sprite.Sprite):
    def __init__(self, posicao, velocidade):
        super().__init__()
        self.image = pygame.Surface((5, 5))
        self.image.fill(VERMELHO)
        self.rect = self.image.get_rect(center=posicao)
        self.pos = pygame.math.Vector2(posicao)
        self.velocidade = velocidade

    def update(self):
        self.pos += self.velocidade
        self.rect.center = self.pos

        if (self.rect.right < 0 or self.rect.left > LARGURA or
                self.rect.bottom < 0 or self.rect.top > ALTURA):
            self.kill()

# Classe para os inimigos
class Inimigo(pygame.sprite.Sprite):
    def __init__(self, nivel):
        super().__init__()
        self.image_orig = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.polygon(self.image_orig, VERDE, [(20, 40), (0, 0), (40, 0)])
        self.image = self.image_orig.copy()
        self.rect = self.image.get_rect()
        self.pos = pygame.math.Vector2(random.randrange(LARGURA), -50)
        self.rect.center = self.pos
        velocidade_base = random.uniform(2, 5)
        self.velocidade = pygame.math.Vector2(0, velocidade_base + nivel * 0.5)
        self.nivel = nivel

    def update(self):
        self.pos += self.velocidade
        self.rect.center = self.pos

        if self.rect.top > ALTURA:
            self.kill()

# Classe para inimigos que disparam projéteis
class InimigoAtirador(Inimigo):
    def __init__(self, nivel):
        super().__init__(nivel)
        pygame.draw.polygon(self.image_orig, MAGENTA, [(20, 40), (0, 0), (40, 0)])
        self.image = self.image_orig.copy()
        self.temporizador_tiro = random.randint(60, 120)

    def update(self):
        super().update()
        self.temporizador_tiro -= 1
        if self.temporizador_tiro <= 0:
            self.disparar()
            self.temporizador_tiro = random.randint(60, 120)

    def disparar(self):
        direcao = (jogador.pos - self.pos).normalize()
        projetil = ProjetilInimigo(self.pos, direcao * 5)
        todos_sprites.add(projetil)
        projeteis_inimigos.add(projetil)

# Classe para os projéteis dos inimigos
class ProjetilInimigo(pygame.sprite.Sprite):
    def __init__(self, posicao, velocidade):
        super().__init__()
        self.image = pygame.Surface((5, 5))
        self.image.fill(CIANO)
        self.rect = self.image.get_rect(center=posicao)
        self.pos = pygame.math.Vector2(posicao)
        self.velocidade = velocidade

    def update(self):
        self.pos += self.velocidade
        self.rect.center = self.pos

        if (self.rect.right < 0 or self.rect.left > LARGURA or
                self.rect.bottom < 0 or self.rect.top > ALTURA):
            self.kill()

# Classe para os power-ups aprimorados
class PowerUp(pygame.sprite.Sprite):
    def __init__(self, tipo, posicao):
        super().__init__()
        self.tipo = tipo
        self.image = pygame.Surface((30, 30), pygame.SRCALPHA)
        self.angle = 0  # Ângulo para rotação
        self.rect = self.image.get_rect(center=posicao)
        self.velocidade = pygame.math.Vector2(0, 2)

        if self.tipo == 'arma':
            self.desenhar_estrela()
        elif self.tipo == 'bomba':
            self.desenhar_hexagono()
        elif self.tipo == 'escudo':
            self.desenhar_poligono()

    def update(self):
        self.rect.move_ip(self.velocidade)
        if self.rect.top > ALTURA:
            self.kill()

        self.angle = (self.angle + 5) % 360
        self.image = pygame.transform.rotate(self.image_orig, self.angle)
        self.rect = self.image.get_rect(center=self.rect.center)

    def desenhar_estrela(self):
        self.image_orig = pygame.Surface((30, 30), pygame.SRCALPHA)
        cor = VERMELHO
        pontos = []
        for n in range(5):
            x = 15 + 12 * math.cos(math.radians(72 * n - 90))
            y = 15 + 12 * math.sin(math.radians(72 * n - 90))
            pontos.append((x, y))
            x = 15 + 5 * math.cos(math.radians(72 * n - 54))
            y = 15 + 5 * math.sin(math.radians(72 * n - 54))
            pontos.append((x, y))
        pygame.draw.polygon(self.image_orig, cor, pontos)

    def desenhar_hexagono(self):
        self.image_orig = pygame.Surface((30, 30), pygame.SRCALPHA)
        cor = AMARELO
        pontos = []
        for n in range(6):
            x = 15 + 12 * math.cos(math.radians(60 * n))
            y = 15 + 12 * math.sin(math.radians(60 * n))
            pontos.append((x, y))
        pygame.draw.polygon(self.image_orig, cor, pontos)

    def desenhar_poligono(self):
        self.image_orig = pygame.Surface((30, 30), pygame.SRCALPHA)
        cor = CIANO
        pontos = []
        for n in range(8):
            raio = 12 if n % 2 == 0 else 6
            x = 15 + raio * math.cos(math.radians(45 * n))
            y = 15 + raio * math.sin(math.radians(45 * n))
            pontos.append((x, y))
        pygame.draw.polygon(self.image_orig, cor, pontos)

# Classe para a explosão
class Explosao(pygame.sprite.Sprite):
    def __init__(self, posicao):
        super().__init__()
        self.image = pygame.Surface((50, 50), pygame.SRCALPHA)
        self.radius = 1
        self.alpha = 255
        self.posicao = posicao
        self.rect = self.image.get_rect(center=posicao)

    def update(self):
        self.radius += 10
        self.alpha -= 20
        if self.alpha <= 0:
            self.kill()
            return
        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 165, 0, self.alpha), (self.radius, self.radius), self.radius)
        self.rect = self.image.get_rect(center=self.posicao)

# Função para exibir o menu inicial
def menu_inicial():
    menu_ativo = True
    while menu_ativo:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_RETURN:
                    menu_ativo = False
                if evento.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        TELA.fill(PRETO)
        titulo_texto = fonte_titulo.render("3D Space Shooter", True, BRANCO)
        start_texto = fonte_menu.render("Pressione Enter para Iniciar", True, BRANCO)
        quit_texto = fonte_menu.render("Pressione Esc para Sair", True, BRANCO)

        TELA.blit(titulo_texto, ((LARGURA - titulo_texto.get_width()) / 2, ALTURA / 4))
        TELA.blit(start_texto, ((LARGURA - start_texto.get_width()) / 2, ALTURA / 2))
        TELA.blit(quit_texto, ((LARGURA - quit_texto.get_width()) / 2, ALTURA / 2 + 50))

        pygame.display.flip()
        pygame.time.Clock().tick(60)

# Função para exibir o menu de pausa
def menu_pausa():
    pausado = True
    opcao_selecionada = 0
    opcoes = ["Continuar", "Sair"]
    while pausado:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    pausado = False
                elif evento.key == pygame.K_RETURN:
                    if opcao_selecionada == 0:
                        pausado = False
                    elif opcao_selecionada == 1:
                        pygame.quit()
                        sys.exit()
                elif evento.key == pygame.K_UP:
                    opcao_selecionada = (opcao_selecionada - 1) % len(opcoes)
                elif evento.key == pygame.K_DOWN:
                    opcao_selecionada = (opcao_selecionada + 1) % len(opcoes)

        TELA.fill(PRETO)
        titulo_texto = fonte_titulo.render("PAUSA", True, BRANCO)
        TELA.blit(titulo_texto, ((LARGURA - titulo_texto.get_width()) / 2, ALTURA / 4))

        for i, opcao in enumerate(opcoes):
            cor = BRANCO if i == opcao_selecionada else CINZA
            texto = fonte_menu.render(opcao, True, cor)
            TELA.blit(texto, ((LARGURA - texto.get_width()) / 2, ALTURA / 2 + i * 50))

        pygame.display.flip()
        pygame.time.Clock().tick(60)

# Função para exibir a tela de Game Over
def game_over(tela, pontuacao, iniciais):
    salvar_pontuacao(iniciais, pontuacao)
    ranking = carregar_ranking()
    
    game_over_ativo = True
    while game_over_ativo:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_RETURN:
                    game_over_ativo = False
                if evento.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        tela.fill(PRETO)
        
        # Título de Game Over
        game_over_texto = fonte_titulo.render("GAME OVER", True, VERMELHO)
        pontuacao_texto = fonte_menu.render(f"Sua Pontuação: {pontuacao}", True, BRANCO)
        restart_texto = fonte_menu.render("Pressione Enter para Reiniciar", True, BRANCO)
        quit_texto = fonte_menu.render("Pressione Esc para Sair", True, BRANCO)
        
        # Exibe o título e as opções na tela
        tela.blit(game_over_texto, ((LARGURA - game_over_texto.get_width()) / 2, 50))
        tela.blit(pontuacao_texto, ((LARGURA - pontuacao_texto.get_width()) / 2, 150))
        tela.blit(restart_texto, ((LARGURA - restart_texto.get_width()) / 2, 500))
        tela.blit(quit_texto, ((LARGURA - quit_texto.get_width()) / 2, 550))
        
        # Título do Ranking
        ranking_titulo = fonte_menu.render("Ranking - Top 5", True, BRANCO)
        tela.blit(ranking_titulo, (LARGURA // 4, 200))
        
        # Exibição do ranking com destaque para o jogador
        for i, (nome, pontos) in enumerate(ranking[:5]):
            cor = BRANCO if nome != iniciais else AMARELO  # Destaque para o jogador atual
            ranking_linha = fonte_jogo.render(f"{i + 1}. {nome} - {pontos}", True, cor)
            tela.blit(ranking_linha, (LARGURA // 4, 250 + i * 40))  # Espaçamento entre as linhas

        pygame.display.flip()
        pygame.time.Clock().tick(60)

# Função para capturar as iniciais do jogador
def capturar_iniciais():
    iniciais = ""
    capturando = True
    while capturando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_RETURN and len(iniciais) == 3:
                    capturando = False
                elif evento.key == pygame.K_BACKSPACE:
                    iniciais = iniciais[:-1]
                elif len(iniciais) < 3 and evento.unicode.isalpha():
                    iniciais += evento.unicode.upper()

        TELA.fill(PRETO)
        titulo_texto = fonte_menu.render("Digite suas iniciais (3 letras)", True, BRANCO)
        iniciais_texto = fonte_menu.render(iniciais, True, BRANCO)
        TELA.blit(titulo_texto, ((LARGURA - titulo_texto.get_width()) / 2, ALTURA / 2 - 50))
        TELA.blit(iniciais_texto, ((LARGURA - iniciais_texto.get_width()) / 2, ALTURA / 2))

        pygame.display.flip()
        pygame.time.Clock().tick(60)
    
    return iniciais

# Chama o menu inicial
menu_inicial()

# Captura as iniciais do jogador antes do jogo começar
iniciais_jogador = capturar_iniciais()

# Variável para controlar o loop do jogo
jogando = True

while jogando:
    jogador = Jogador()
    todos_sprites = pygame.sprite.Group()
    inimigos = pygame.sprite.Group()
    projeteis = pygame.sprite.Group()
    projeteis_inimigos = pygame.sprite.Group()
    powerups = pygame.sprite.Group()
    explosoes = pygame.sprite.Group()
    todos_sprites.add(jogador)

    fundo_estrelado = FundoEstrelado(50)

    pontuacao = 0
    nivel = 1
    contador_nivel = 0
    tempo_proximo_powerup = random.randint(500, 1000)

    relogio = pygame.time.Clock()
    rodando = True

    while rodando:
        relogio.tick(60)

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
                jogando = False
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_SPACE:
                    jogador.disparar()
                elif evento.key == pygame.K_ESCAPE:
                    menu_pausa()

        todos_sprites.update()
        fundo_estrelado.update()
        contador_nivel += 1

        if contador_nivel >= 1000:
            contador_nivel = 0
            nivel += 1
            frequencia_spawn = max(500 - nivel * 50, 100)
            velocidade_inimigo = 2 + nivel * 0.5

        if random.randint(1, max(60 - nivel * 2, 10)) == 1:
            tipo_inimigo = random.choice(['normal', 'atirador']) if nivel >= 3 else 'normal'
            if tipo_inimigo == 'normal':
                inimigo = Inimigo(nivel)
            else:
                inimigo = InimigoAtirador(nivel)
            todos_sprites.add(inimigo)
            inimigos.add(inimigo)

        tempo_proximo_powerup -= 1
        if tempo_proximo_powerup <= 0:
            tipo_powerup = random.choice(['arma', 'bomba', 'escudo'])
            posicao = (random.randint(20, LARGURA - 20), -20)
            powerup = PowerUp(tipo_powerup, posicao)
            todos_sprites.add(powerup)
            powerups.add(powerup)
            tempo_proximo_powerup = random.randint(500, 1000)

        colisao = pygame.sprite.groupcollide(inimigos, projeteis, True, True)
        if colisao:
            for inimigo in colisao:
                pontuacao += 10
                explosao_inimigo = Explosao(inimigo.rect.center)
                todos_sprites.add(explosao_inimigo)
                explosoes.add(explosao_inimigo)
                som_explosao.play()

        if pygame.sprite.spritecollide(jogador, projeteis_inimigos, True):
            if jogador.escudo > 0:
                jogador.escudo -= 1
            else:
                jogador.vidas -= 1
                som_perda_vida.play()
                if jogador.vidas <= 0:
                    rodando = False

        colisao_jogador = pygame.sprite.spritecollide(jogador, inimigos, True)
        if colisao_jogador:
            if jogador.escudo > 0:
                jogador.escudo -= 1
            else:
                jogador.vidas -= 1
                som_perda_vida.play()
                if jogador.vidas <= 0:
                    rodando = False

        colisao_powerup = pygame.sprite.spritecollide(jogador, powerups, True)
        for powerup in colisao_powerup:
            som_powerup.play()
            if powerup.tipo == 'arma':
                jogador.nivel_arma += 1
                jogador.temporizador_powerup = 600
            elif powerup.tipo == 'bomba':
                for inimigo in inimigos:
                    explosao_inimigo = Explosao(inimigo.rect.center)
                    todos_sprites.add(explosao_inimigo)
                    explosoes.add(explosao_inimigo)
                    inimigo.kill()
                    pontuacao += 10
                explosao = Explosao(jogador.rect.center)
                todos_sprites.add(explosao)
                explosoes.add(explosao)
                som_explosao.play()
            elif powerup.tipo == 'escudo':
                jogador.escudo = 3

        TELA.fill(PRETO)
        fundo_estrelado.draw(TELA)
        todos_sprites.draw(TELA)

        pontuacao_texto = fonte_jogo.render(f"Pontuação: {pontuacao}", True, BRANCO)
        vidas_texto = fonte_jogo.render(f"Vidas: {jogador.vidas}", True, BRANCO)
        nivel_texto = fonte_jogo.render(f"Nível: {nivel}", True, BRANCO)
        TELA.blit(pontuacao_texto, (10, 10))
        TELA.blit(vidas_texto, (10, 40))
        TELA.blit(nivel_texto, (10, 70))

        x_offset = LARGURA - 200
        if jogador.nivel_arma > 1:
            arma_texto = fonte_jogo.render(f"Arma Lv{jogador.nivel_arma}", True, BRANCO)
            tempo_arma = fonte_jogo.render(f"Tempo: {jogador.temporizador_powerup // 60}s", True, BRANCO)
            TELA.blit(arma_texto, (x_offset, 10))
            TELA.blit(tempo_arma, (x_offset, 30))
        if jogador.escudo > 0:
            escudo_texto = fonte_jogo.render(f"Escudo: {jogador.escudo}", True, BRANCO)
            TELA.blit(escudo_texto, (x_offset, 60))

        pygame.display.flip()

    todos_sprites.empty()
    inimigos.empty()
    projeteis.empty()
    projeteis_inimigos.empty()
    powerups.empty()
    explosoes.empty()

    game_over(TELA, pontuacao, iniciais_jogador)

pygame.quit()
sys.exit()
