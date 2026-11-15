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
        text(157, 339, reason, 28, (241, 238, 232))
        text(340, 80, '[R] 다시 시도    [Esc] 종료', 18, (165, 162, 158))
        update_canvas()
        return

    draw_rectangle(0, 0, 959, 639, 12, 11, 13, 255, filled=True)
    if victory:
        text(310, 426, '사건 재현 성공', 36, (130, 230, 168))
        text(200, 358, reason, 20)
    else:
        text(305, 426, '사건 재현 실패', 36, (244, 137, 145))
        text(180, 358, reason, 20)
    text(302, 180, '[R] 다시 시도    [Esc] 종료', 23)
    update_canvas()
