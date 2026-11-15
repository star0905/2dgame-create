"""타이틀과 첫 플레이 사이에 나오는 탐정 윤시현의 사건 브리핑."""

import game_framework
from pico2d import (
    SDL_KEYDOWN, SDL_QUIT, clear_canvas, draw_rectangle, get_events, update_canvas,
)
from rooms import SCREEN_H, SCREEN_W
from sdl2 import SDLK_ESCAPE, SDLK_RETURN, SDLK_SPACE
from sprite import ASSETS, SpriteAnimator, image_for
from ui import text


# 한 항목이 대사 한 장이다. 각 문자열은 화면에 표시할 한 줄이다.
DIALOGUE = (
    (
        '윤시현입니다. 의뢰를 받아 사건을 조사하는 탐정이죠.',
        '오늘 들여다볼 건 파티가 열렸던 저택의 보석 도난 사건입니다.',
    ),
    (
        '범인은 나중에 붙잡혔습니다. 그런데 파티가 끝날 때까지',
        '보석이 사라진 줄 아는 사람은 아무도 없었어요.',
    ),
    (
        '진술서만 읽어서는 왜 아무도 눈치채지 못했는지 알 수 없었습니다.',
        '그래서 이번엔 범인의 입장에서 그날 밤을 재현해 보려 합니다.',
    ),
    (
        '나라면 누구에게 먼저 말을 걸었을까요?',
        '금고를 열려면 무엇부터 준비해야 했을까요?',
        '현관에서 시작합니다. 보석을 손에 넣고 저택을 빠져나가 보죠.',
    ),
)


def init():
    global page, detective, background
    page = 0
    detective = SpriteAnimator('detective')
    background = image_for(ASSETS / 'rooms' / 'foyer.png')


def finish():
    pass


def update():
    pass


def handle_events():
    global page
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit_game()
            return
        if event.type != SDL_KEYDOWN:
            continue
        if event.key == SDLK_ESCAPE:
            import title_mode

            game_framework.change_mode(title_mode)
            return
        if event.key in (SDLK_RETURN, SDLK_SPACE):
            if page + 1 < len(DIALOGUE):
                page += 1
            else:
                import play_mode

                game_framework.change_mode(play_mode)
            return


def draw():
    clear_canvas()
    draw_rectangle(0, 0, SCREEN_W - 1, SCREEN_H - 1, 12, 11, 13, filled=True)
    background.draw(480, 406, 790, 478)
    detective.draw(480, 300, 126, 180)

    draw_rectangle(36, 30, 924, 263, 31, 24, 24, filled=True)
    draw_rectangle(36, 30, 924, 263, 155, 112, 72)
    text(63, 239, '탐정 윤시현', 26, (255, 218, 151))
    text(744, 233, f'{page + 1} / {len(DIALOGUE)}', 16, (229, 210, 185))
    for index, line in enumerate(DIALOGUE[page]):
        text(64, 185 - index * 35, line, 22, (255, 247, 227))

    action = '재현 시작' if page == len(DIALOGUE) - 1 else '다음'
    text(64, 62, f'Enter / Space  {action}      Esc  타이틀로', 16, (225, 207, 187))
    update_canvas()
