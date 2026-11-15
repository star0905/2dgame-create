from pico2d import clear_canvas, update_canvas, get_events, draw_rectangle, SDL_KEYDOWN, SDL_QUIT
from sdl2 import SDLK_ESCAPE, SDLK_RETURN, SDLK_SPACE
from sprite import ASSETS, image_for
from rooms import SCREEN_W, SCREEN_H
import game_framework


def init():
    global background
    background = image_for(ASSETS / 'title.png')


def finish():
    pass


def handle_events():
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit_game()
        elif event.type == SDL_KEYDOWN:
            if event.key == SDLK_ESCAPE:
                game_framework.quit_game()
            elif event.key in (SDLK_RETURN, SDLK_SPACE):
                import intro_mode
                game_framework.change_mode(intro_mode)
                return


def update():
    pass


def draw():
    clear_canvas()
    draw_rectangle(0, 0, SCREEN_W - 1, SCREEN_H - 1, 8, 8, 9, 255, filled=True)
    background.draw(SCREEN_W / 2, SCREEN_H / 2, SCREEN_W, SCREEN_W * 572 / 1024)
    update_canvas()
