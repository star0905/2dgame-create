from pico2d import clear_canvas, update_canvas, get_events, draw_rectangle, SDL_KEYDOWN, SDL_QUIT
from sdl2 import (SDLK_ESCAPE, SDLK_RETURN, SDLK_SPACE, SDLK_LEFT,
                  SDLK_RIGHT, SDLK_UP, SDLK_DOWN)
from sprite import ASSETS, image_for
from rooms import SCREEN_W, SCREEN_H
from ui import text
import game_framework
import game_settings


def init():
    global background, selected_row
    background = image_for(ASSETS / 'title.png')
    selected_row = 0


def finish():
    pass


def handle_events():
    global selected_row
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit_game()
            return
        if event.type != SDL_KEYDOWN:
            continue
        if event.key == SDLK_ESCAPE:
            game_framework.quit_game()
            return
        if event.key in (SDLK_UP, SDLK_DOWN):
            selected_row = 1 - selected_row
        elif event.key in (SDLK_LEFT, SDLK_RIGHT):
            if selected_row == 0:
                name = 'hard' if game_settings.difficulty == 'normal' else 'normal'
                game_settings.select_difficulty(name)
            else:
                game_settings.adjust_time(1 if event.key == SDLK_RIGHT else -1)
        elif event.key in (SDLK_RETURN, SDLK_SPACE):
            import intro_mode
            game_framework.change_mode(intro_mode)
            return


def update():
    pass


def draw():
    clear_canvas()
    draw_rectangle(0, 0, SCREEN_W - 1, SCREEN_H - 1, 8, 8, 9, filled=True)
    background.draw(SCREEN_W / 2, SCREEN_H / 2, SCREEN_W, SCREEN_W * 572 / 1024)
    draw_rectangle(170, 20, 790, 277, 27, 22, 23, filled=True)
    draw_rectangle(170, 20, 790, 277, 157, 114, 72)
    for row, y in enumerate((231, 176)):
        if selected_row == row:
            draw_rectangle(192, y - 28, 768, y + 20, 60, 43, 33, filled=True)
    text(215, 240, '난이도', 22, (245, 225, 192))
    text(455, 240, f'<  {game_settings.LABELS[game_settings.difficulty]}  >', 24)
    text(215, 185, '준비 시간', 22, (245, 225, 192))
    text(455, 185, f'<  {game_settings.clock(game_settings.preparation_seconds)}  >', 24)
    text(215, 128, '노멀 3분 / 하드 1분 · 난이도는 준비 시간 기준', 17, (211, 196, 179))
    text(215, 91, '↑↓ 항목 선택   ←→ 변경   시간은 15초씩 조정', 17)
    text(292, 51, 'Enter / Space  사건 재현 시작', 21, (255, 221, 151))
    update_canvas()
