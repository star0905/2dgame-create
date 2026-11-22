"""Collect case files, then inspect the aftermath of the current room."""
from math import hypot

from pico2d import draw_rectangle
from rooms import ROOMS
from sprite import ASSETS, SpriteAnimator, image_for
from ui import text

# Coordinates are in the original mansion sheet, like rooms.py.
EVIDENCE = {
    'banquet': ('촬영 기록', (900, 440), (
        '파티 사진의 촬영 방향이 도중에 바뀌었다.',
        '사진작가에게 다른 장소에서 촬영하도록 부탁했을 가능성이 있다.',
    )),
    'hall': ('선수 옆의 빈 커피잔', (750, 830), (
        '선수는 음료를 마신 뒤 갑자기 졸렸다고 증언했다.',
        '연회장의 커피와 서재의 수면제를 조합해 건넨 것으로 보인다.',
    )),
    'vault': ('보안 점검 기록', (1325, 785), (
        '범행 무렵 경보가 점검 모드로 전환된 기록이 있다.',
        '서재의 보안 전문가에게 장치 관리 상태와 점검에 대해 물어보자.',
    )),
}


EVIDENCE_ICONS = {
    'banquet': 'camera', 'hall': 'coffee', 'vault': 'alarm',
}


class CaseFile:
    def __init__(self, room, point):
        self.room = room
        self.x, self.y = ROOMS[room].point(*point)
        self.visible = True

    def draw(self):
        x, y = int(self.x), int(self.y)
        draw_rectangle(x - 13, y, x + 13, y + 24, 232, 216, 170, filled=True)
        for offset in (7, 13, 19):
            draw_rectangle(x - 8, y + offset, x + 7, y + offset, 89, 76, 58)
        text(x - 25, y + 43, '자료 ×1', 14, (255, 231, 160))


class Investigation:
    def __init__(self):
        self.files = [
            CaseFile('foyer', (233, 410)),
            CaseFile('kitchen', (1396, 373)),
            CaseFile('study', (152, 831)),
        ]
        self.charges = 0
        self.unlocked = set()
        self.notes = {}
        self.active = False
        self.notebook = False
        self.note_page = 0
        self.detective = SpriteAnimator('detective')
        self.x = self.y = 0.0

    def open_scene(self, room_name, player):
        if room_name not in EVIDENCE:
            return '이 방에는 현장 조사 단서가 없습니다. 연회장·복도·금고실에서 사용하세요.'
        if room_name not in self.unlocked:
            if self.charges == 0:
                return '현장 조사 자료가 필요합니다. 종이 묶음을 [E]로 주워 보세요.'
            self.charges -= 1
            self.unlocked.add(room_name)
        self.active = True
        self.x, self.y = player.x, player.y
        player.keys.clear()
        return '사건 이후 현장입니다. 흔적 가까이에서 [E]로 조사하세요.'

    def close(self, player):
        self.active = self.notebook = False
        player.keys.clear()

    def inspect(self, room_name):
        label, point, lines = EVIDENCE[room_name]
        x, y = ROOMS[room_name].point(*point)
        if hypot(self.x - x, self.y - y) > 80:
            return '흔적에 가까이 가서 [E]로 조사하세요.'
        self.notes[room_name] = (label, lines)
        return '흔적을 수첩에 기록했습니다. [N]으로 다시 볼 수 있습니다.'

    def draw_scene(self, room_name):
        room = ROOMS[room_name]
        draw_rectangle(20, 95, 940, 584, 92, 157, 186)
        label, point, lines = EVIDENCE[room_name]
        x, y = room.point(*point)
        icon = image_for(ASSETS / 'items' / f'{EVIDENCE_ICONS[room_name]}.png')
        icon.draw(x, y + 12, 35, 35)
        draw_rectangle(int(x - 17), int(y - 3), int(x + 17), int(y + 24),
                       154, 222, 243)
        text(int(x - 65), int(y + 46), label, 16, (183, 236, 255))
        self.detective.draw(self.x, self.y, 52, 74)
        if room_name in self.notes:
            draw_rectangle(45, 112, 915, 227, 20, 32, 41, filled=True)
            for i, line in enumerate(lines):
                text(65, 200 - i * 35, line, 19, (223, 237, 245))

    def draw_notebook(self):
        draw_rectangle(65, 130, 895, 520, 35, 29, 26, filled=True)
        text(95, 480, '탐정 수첩', 27, (255, 228, 176))
        entries = list(self.notes.items())
        if entries:
            self.note_page %= len(entries)
            room, (label, lines) = entries[self.note_page]
            text(95, 410, f'{ROOMS[room].label} · {label}', 23)
            for i, line in enumerate(lines):
                text(95, 350 - i * 40, line, 18)
            text(95, 230, f'{self.note_page + 1} / {len(entries)}   방향키로 넘기기', 17)
        else:
            text(95, 380, '아직 조사한 흔적이 없습니다.', 21)
        text(95, 170, 'N / Esc 닫기', 18)
