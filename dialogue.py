"""Speaker-labelled scenes shared by reconstruction and investigation."""
import textwrap
from pico2d import draw_rectangle
from ui import text

WELCOME = (
    ('김재현 (집주인)', '어서 오게. 파티에 와 줘서 고맙네. 오늘은 이 저택에서 함께 즐겨 주게.'),
    ('김재현 (집주인)', '손님들에게 보여 주려고 귀한 보석도 준비해 뒀지. 지금은 복도 끝 금고실에 보관하고 있네.'),
    ('김재현 (집주인)', '음식과 음료는 연회장에 있으니 편히 이용하게. 그럼 안에서 보세.'),
)
ATHLETE_REQUEST = (
    ('박준혁 (운동선수)', '안에만 있으니 답답해서 좀 뛰었더니 목이 메이네. 마실 거 없어?'),
)
ATHLETE_DRINK = (
    ('박준혁 (운동선수)', '고마워. 마침 목이 말랐는데 잘됐네.'),
)
ATHLETE_SLEEP = ATHLETE_DRINK + (
    ('박준혁 (운동선수)', '근데 왠지 좀 졸리네…… 잠깐만 눈 좀 붙여야겠어.'),
    ('상황', '박준혁이 잠들었다. 복도의 순찰이 멈췄다.'),
)
ATHLETE_TESTIMONY = (
    ('박준혁 (사건 이후 증언)', '이런 일이 일어날 줄 몰랐네요. 몸 상태가 정상이었다면 말렸을 거 같은데 왠지 잠이 오더라고요.'),
    ('윤시현 (탐정)', '선수가 마신 음료와 남아 있는 약 포장지를 함께 확인해야겠군.'),
)
SECURITY = (
    ('상황', '보안 전문가는 보안 장치를 보며 짜증이 난 듯한 표정을 짓고 있다.'),
    ('주인공', '왜 그래?'),
    ('이도현 (보안 전문가)', '직업병이라고 해야 하려나. 저번에 김재현 씨가 보안 장치 설치를 도와달라고 했거든.'),
    ('이도현 (보안 전문가)', '그때는 싸게 해줄 수 없느냐고 하더니, 관리를 이렇게 해 놓은 걸 보니 짜증이 나서.'),
    ('주인공', '어느 점에서?'),
    ('이도현 (보안 전문가)', '점검용 조작부가 밖에 드러나 있잖아. 손님이 다니는 곳인데 덮개도 제대로 닫지 않았어.'),
    ('이도현 (보안 전문가)', '내가 상태를 확인해 볼게. 점검하는 동안 경보는 테스트 모드로 바꿔 두겠어.'),
)


class Dialogue:
    def __init__(self):
        self.pages = []
        self.index = 0

    @property
    def active(self):
        return self.index < len(self.pages)

    def start(self, lines):
        self.pages = []
        for speaker, speech in lines:
            wrapped = textwrap.wrap(speech, width=37)
            for offset in range(0, len(wrapped), 3):
                self.pages.append((speaker, wrapped[offset:offset + 3]))
        self.index = 0

    def advance(self):
        self.index += 1

    def draw(self):
        speaker, lines = self.pages[self.index]
        draw_rectangle(30, 115, 930, 320, 26, 22, 24, filled=True)
        draw_rectangle(30, 115, 930, 320, 168, 127, 81)
        text(54, 290, speaker, 23, (255, 220, 158))
        for number, line in enumerate(lines):
            text(54, 245 - number * 33, line, 21, (250, 244, 232))
        text(54, 145, 'Enter / Space / E 다음', 16, (209, 194, 176))
