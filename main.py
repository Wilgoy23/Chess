import pygame
from board import Board

SQUARE_SIZE = 100
WINDOW_SIZE = SQUARE_SIZE * 8  # 800x800

pygame.init()
screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
pygame.display.set_caption("Chess")
clock = pygame.time.Clock()

board = Board(square_size=SQUARE_SIZE)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            board.handle_click(*pygame.mouse.get_pos())

    board.draw(screen)
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
