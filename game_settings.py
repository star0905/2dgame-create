"""Session settings selected before the detective briefing."""
PRESETS = {'normal': 180, 'hard': 60}
LABELS = {'normal': '노멀', 'hard': '하드'}
MIN_PREPARATION = 30
MAX_PREPARATION = 300
TIME_STEP = 15

difficulty = 'normal'
preparation_seconds = PRESETS[difficulty]


def select_difficulty(name):
    global difficulty, preparation_seconds
    difficulty = name
    preparation_seconds = PRESETS[name]


def adjust_time(direction):
    global preparation_seconds
    preparation_seconds = max(MIN_PREPARATION,
                              min(MAX_PREPARATION, preparation_seconds + direction * TIME_STEP))


def clock(seconds):
    rounded = max(0, int(seconds + 0.999999))
    return f'{rounded // 60:02d}:{rounded % 60:02d}'
