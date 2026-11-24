import textwrap

from pico2d import clear_canvas, update_canvas, get_events, draw_rectangle, SDL_QUIT, SDL_KEYDOWN
from sdl2 import SDLK_ESCAPE, SDLK_r
from ui import text
import game_framework

victory = False
withdrawal_ending = False
reason = ''


def configure(won, why, *, abandoned=False):
    global victory, reason, withdrawal_ending
    victory, reason, withdrawal_ending = bool(won), why, abandoned


def init(): pass

def finish(): pass

def update(): pass


def handle_events():
    for event in get_events():
        if event.type == SDL_QUIT or (event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE):
            game_framework.quit_game()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_r:
            import play_mode
            game_framework.change_mode(play_mode)


def draw():
    clear_canvas()
    if withdrawal_ending:
        draw_rectangle(0, 0, 959, 639, 0, 0, 0, filled=True)
        text(90, 410, '윤시현 (탐정)', 23, (255, 220, 158))
        for index, line in enumerate(textwrap.wrap(reason, width=35)):
            text(90, 350 - index * 36, line, 25, (241, 238, 232))
        text(340, 80, '[R] 다시 시도    [Esc] 종료', 18, (165, 162, 158))
        update_canvas()
        return

    draw_rectangle(0, 0, 959, 639, 12, 11, 13, 255, filled=True)
    title = '사건 재현 성공' if victory else '사건 재현 실패'
    color = (130, 230, 168) if victory else (244, 137, 145)
    text(310, 480, title, 36, color)
    text(90, 405, '윤시현 (탐정)', 23, (255, 220, 158))
    speech = reason if victory else reason + ' 이 재현을 다시 검토해 봐야겠군요.'
    for index, line in enumerate(textwrap.wrap(speech, width=38)):
        text(90, 350 - index * 34, line, 22)
    text(302, 100, '[R] 다시 시도    [Esc] 종료', 23)
    update_canvas()
