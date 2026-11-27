"""Collect case files, then inspect the aftermath of the current room."""
from math import hypot

from pico2d import draw_rectangle
from rooms import ROOMS
from sprite import ASSETS, SpriteAnimator, image_for
from ui import text

# Coordinates are in the original mansion sheet, like rooms.py.
EVIDENCE = {
    'foyer': ('출입문 앞의 구두 자국', (233, 410), (
        '출입문 앞에 바깥쪽으로 이어지는 구두 자국이 남아 있다.',
        '침입 흔적은 없다. 범인은 손님처럼 들어와 현관으로 나간 듯하다.',
    )),
    'banquet': ('빈 커피 받침', (994, 270), (
        '음료대에 커피잔 하나가 빠지고 받침만 남아 있다.',
        '요리사는 손님 한 명이 커피를 들고 연회장을 나갔다고 말했다.',
    )),
    'kitchen': ('비어 있는 칼 자리', (1260, 372), (
        '요리사는 조리대에 두었던 칼 한 자루가 없어졌다고 말했다.',
        '설거지할 식기 사이에도 없다. 누군가 밖으로 가져간 모양이다.',
    )),
    'study': ('뜯긴 약 포장지', (332, 786), (
        '책상 옆에 뜯긴 수면제 포장지가 남아 있다.',
        '약을 먹었다는 사람은 없다. 다른 용도로 사용된 것은 아닐까?',
    )),
    'hall': ('선수 옆의 빈 커피잔', (750, 830), (
        '선수는 커피를 마신 뒤 갑자기 졸렸다고 증언했다.',
        '평소와 달리 깊이 잠들었다. 커피에 무언가 섞였을 가능성이 있다.',
    )),
    'service': ('행사 기록의 흔적', (400, 245), (
        '남은 행사 기록들은 모두 같은 개관 행사를 가리킨다.',
        '한 장에서 빠진 날짜 부분을 다른 기록으로 채울 수 있을 것이다.',
    )),
    'security_lobby': ('기둥 뒤의 신발 자국', (400, 340), (
        '기둥 뒤 바닥에 누군가 멈춰 섰던 신발 자국이 남아 있다.',
        '카메라가 돌아가는 동안 이곳에서 기다렸을 가능성이 있다.',
    )),
    'security_room': ('출입 기록의 여백', (575, 190), (
        '행사 출입 기록에는 날짜 중 일에 해당하는 부분이 남아 있다.',
        '행사명과 표식이 같은 문서들을 대조해 봐야겠다.',
    )),
    'vault': ('금고 명판의 흔적', (1325, 785), (
        '명판의 첫 손님은 저택의 개관 행사를 뜻하는 듯하다.',
        '개관한 월 두 자리와 일 두 자리를 차례로 연결해 보자.',
    )),
}


EVIDENCE_ICONS = {
    'foyer': 'magnifier', 'banquet': 'coffee', 'kitchen': 'magnifier',
    'study': 'sleeping_pills', 'hall': 'coffee', 'vault': 'alarm',
    'service': 'magnifier', 'security_lobby': 'magnifier', 'security_room': 'camera',
}


# Ordinary records: readable with E, independently of consumable H investigations.
# Shared event name/mark links the partial dates without exposing a full code.
PUZZLE_RECORDS = {
    'opening_plaque': ('vault', '금고 명판', (
        '이 집이 처음 손님을 맞은 날을 기억하며.',
        '명판 아래에는 월 / 일 표시가 새겨져 있다.',
    )),
    'event_month': ('service', '개관 행사 준비표', (
        '저택 개관 행사 · 표식: 월계수',
        '행사 개최 월: 11월. 일자 항목은 찢겨 나갔다.',
    )),
    'entry_day': ('security_room', '최초 행사 출입 기록', (
        '저택 개관 행사 · 표식: 월계수',
        '25일, 방문객 출입 개시. 월 항목은 지워져 있다.',
    )),
}


class SceneRecord:
    def __init__(self, record_id, point, display_point):
        self.record_id = record_id
        self.room, self.label, self.lines = PUZZLE_RECORDS[record_id]
        self.x, self.y = ROOMS[self.room].point(*point)
        self.display_x, self.display_y = ROOMS[self.room].point(*display_point)
        self.visible = True

    def draw(self):
        x, y = int(self.display_x), int(self.display_y)
        draw_rectangle(x - 12, y, x + 12, y + 22, 215, 201, 167, filled=True)
        for offset in (6, 11, 16):
            draw_rectangle(x - 7, y + offset, x + 7, y + offset, 85, 70, 49)
        text(x - 7 * len(self.label), y + 40, self.label, 14, (255, 231, 177))


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
        self.documents = [
            SceneRecord('event_month', (240, 185), (285, 185)),
            SceneRecord('entry_day', (245, 195), (245, 130)),
        ]
        self.records = {}
        self.charges = 0
        self.unlocked = set()
        self.notes = {}
        self.active = False
        self.notebook = False
        self.note_page = 0
        self.detective = SpriteAnimator('detective')
        self.x = self.y = 0.0

    def collect_record(self, record_id):
        """Reading never consumes a charge, an item slot or the paper itself."""
        value = PUZZLE_RECORDS[record_id]
        self.records[record_id] = value
        return value

    def notebook_entries(self):
        entries = [('일반 기록', room, label, lines)
                   for room, label, lines in self.records.values()]
        entries += [('현장 조사', room, label, lines)
                    for room, (label, lines) in self.notes.items()]
        return entries

    def open_scene(self, room_name, player):
        if room_name not in EVIDENCE:
            return '현재는 현장 조사를 시작할 수 없습니다.'
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
        entries = self.notebook_entries()
        if entries:
            self.note_page %= len(entries)
            category, room, label, lines = entries[self.note_page]
            text(95, 440, category, 16, (207, 190, 160))
            text(95, 400, f'{ROOMS[room].label} · {label}', 23)
            for i, line in enumerate(lines):
                text(95, 350 - i * 40, line, 18)
            text(95, 230, f'{self.note_page + 1} / {len(entries)}   방향키로 넘기기', 17)
        else:
            text(95, 380, '아직 조사한 흔적이 없습니다.', 21)
        text(95, 170, 'N / Esc 닫기', 18)
