"""Safe keypad layout shared by drawing and mouse hit testing."""
from pico2d import draw_rectangle
from ui import text

PANEL = (275, 98, 685, 558)
BUTTONS = {}
for row, keys in enumerate((('1', '2', '3'), ('4', '5', '6'),
                            ('7', '8', '9'), ('delete', '0', 'confirm'))):
    for column, key in enumerate(keys):
        left, bottom = 320 + column * 110, 350 - row * 70
        BUTTONS[key] = (left, bottom, left + 100, bottom + 52)
BUTTONS['close'] = (612, 512, 666, 545)


def button_at(x, y):
    """Coordinates use the game's bottom-left canvas origin."""
    for key, (left, bottom, right, top) in BUTTONS.items():
        if left <= x <= right and bottom <= y <= top:
            return key
    return None


def draw_keypad(code, feedback='', hovered=None):
    draw_rectangle(*PANEL, 29, 25, 28, filled=True)
    draw_rectangle(*PANEL, 175, 133, 83)
    text(302, 528, '금고 암호', 26, (255, 235, 181))
    text(438, 495, '월 / 일', 18, (205, 192, 169))
    for index, left in enumerate((321, 382, 494, 555)):
        draw_rectangle(left, 430, left + 56, 478, 15, 18, 21, filled=True)
        draw_rectangle(left, 430, left + 56, 478, 109, 91, 70)
        text(left + 17, 443, code[index] if index < len(code) else '_', 32,
             (255, 239, 196))
    text(463, 443, '/', 30, (181, 158, 122))
    if feedback:
        text(320, 410, feedback, 16, (249, 151, 145))
    labels = {'delete': '지우기', 'confirm': '확인', 'close': '닫기'}
    for key, box in BUTTONS.items():
        complete = key != 'confirm' or len(code) == 4
        color = (109, 85, 57) if key == hovered else (58, 49, 44)
        if not complete:
            color = (41, 39, 38)
        draw_rectangle(*box, *color, filled=True)
        draw_rectangle(*box, 133, 105, 75)
        left, bottom, right, top = box
        label = labels.get(key, key)
        size = 19 if key in labels else 26
        x = int((left + right) / 2 - (len(label) * size / 2 if key in labels else 8))
        text(x, int((bottom + top) / 2 - 8), label, size,
             (255, 230, 173) if complete else (132, 127, 115))
    text(305, 118, '클릭 / 숫자키 입력 · Enter 확인 · Esc 닫기', 14, (207, 193, 174))
