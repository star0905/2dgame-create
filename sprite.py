"""All 8 characters share one four-direction, four-frame animator."""
from pathlib import Path
from pico2d import load_image

ASSETS = Path(__file__).resolve().parent / 'assets'
CELL = 128
FRAME_COUNT = 4
DIRECTION_TO_TOP_ROW = {'down': 0, 'up': 1, 'left': 2, 'right': 3}
_cache = {}


def image_for(path):
    path = str(path)
    if path not in _cache:
        _cache[path] = load_image(path)
    return _cache[path]


class SpriteAnimator:
    def __init__(self, character, fps=7.0):
        self.image = image_for(ASSETS / 'characters' / f'{character}.png')
        self.fps = fps
        self.facing = 'down'
        self.elapsed = 0.0
        self.frame = 0
        self.moving = False

    def set_facing(self, facing):
        if facing not in DIRECTION_TO_TOP_ROW:
            raise ValueError(f'Unknown direction: {facing}')
        self.facing = facing

    def update(self, dt, moving):
        self.moving = moving
        if not moving:
            self.frame = 0
            self.elapsed = 0.0
            return
        self.elapsed += max(0.0, dt)
        self.frame = int(self.elapsed * self.fps) % FRAME_COUNT

    def draw(self, x, foot_y, width=70, height=100):
        # Pillow sheet rows are ordered from the top. pico2d clip_draw
        # counts its clip origin from the *bottom* of the texture.
        row_top = DIRECTION_TO_TOP_ROW[self.facing]
        clip_bottom = (3 - row_top) * CELL
        # Foot placement is stable across animation frames.
        center_y = foot_y + height / 2
        self.image.clip_draw(self.frame * CELL, clip_bottom,
                             CELL, CELL, x, center_y, width, height)
