"""Player entity with shared sprite animation + keyboard handling."""
from math import hypot
from pico2d import SDL_KEYDOWN, SDL_KEYUP
from sdl2 import (SDLK_w, SDLK_a, SDLK_s, SDLK_d, SDLK_UP,
                  SDLK_DOWN, SDLK_LEFT, SDLK_RIGHT)
from rooms import FOYER_START
from sprite import SpriteAnimator, ASSETS, image_for

MOVE = {'up': (SDLK_w, SDLK_UP), 'down': (SDLK_s, SDLK_DOWN),
        'left': (SDLK_a, SDLK_LEFT), 'right': (SDLK_d, SDLK_RIGHT)}


class Player:
    def __init__(self, stage, character='culprit'):
        self.stage = stage
        self.character = character
        self.x, self.y = stage.room.point(*FOYER_START)
        self.speed = 185.0
        self.sprite = SpriteAnimator(character, fps=7.5)
        self.keys = set()
        self.held_item = None
        self.last_move = (0, 0)

    def handle_event(self, event):
        if event.type == SDL_KEYDOWN:
            self.keys.add(event.key)
        elif event.type == SDL_KEYUP:
            self.keys.discard(event.key)

    def update(self, dt):
        vx = int(any(key in self.keys for key in MOVE['right'])) - int(any(key in self.keys for key in MOVE['left']))
        vy = int(any(key in self.keys for key in MOVE['up'])) - int(any(key in self.keys for key in MOVE['down']))
        length = hypot(vx, vy)
        moving = length > 0
        if moving:
            vx, vy = vx / length, vy / length
            # Keep last facing when standing still; orient based on dominant axis.
            if abs(vx) > abs(vy): self.sprite.set_facing('right' if vx > 0 else 'left')
            elif abs(vy) > 0: self.sprite.set_facing('up' if vy > 0 else 'down')
            before = self.x, self.y
            nx = self.x + vx * self.speed * dt
            ny = self.y + vy * self.speed * dt
            # Separate axes for natural sliding against furniture.
            if self.stage.can_move(nx, self.y): self.x = nx
            if self.stage.can_move(self.x, ny): self.y = ny
            crossed = self.stage.cross_door(self, vx, vy)
            moving = crossed or before != (self.x, self.y)
        self.last_move = (vx, vy)
        self.sprite.update(dt, moving)

    def draw(self):
        self.sprite.draw(self.x, self.y, 52, 74)
        if self.held_item:
            image_for(ASSETS / 'items' / f'{self.held_item}.png').draw(self.x + 26, self.y + 35, 29, 29)

    def pickup(self, item_name):
        if self.held_item is not None:
            return False
        self.held_item = item_name
        return True

    def drop(self):
        item = self.held_item
        self.held_item = None
        return item
