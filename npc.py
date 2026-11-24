"""All mansion NPCs use the same animated class with different data."""
from math import hypot
from sprite import SpriteAnimator
from ui import text
from rooms import ROOMS


class NPC:
    def __init__(self, character, display_name, room, path, speed=55):
        self.character = character
        self.display_name = display_name
        self.speed = speed
        self.sprite = SpriteAnimator(character, fps=6)
        self.working = True
        self.visible = True
        self.sleeping = False
        self.pursuing = False
        self.move_to_room(room, path)

    def move_to_room(self, room, path):
        self.room = room
        self.path = [ROOMS[room].point(*point) for point in path]
        self.x, self.y = self.path[0]
        self.path_index = 0

    def update(self, dt):
        if self.pursuing:
            return  # Pursuit owns movement and animation during the escape.
        if not self.working or not self.path:
            self.sprite.update(dt, False)
            return
        tx, ty = self.path[self.path_index]
        dx, dy = tx - self.x, ty - self.y
        dist = hypot(dx, dy)
        if dist < max(3, self.speed * dt):
            self.x, self.y = tx, ty
            self.path_index = (self.path_index + 1) % len(self.path)
            self.sprite.update(dt, False)
            return
        dx, dy = dx / dist, dy / dist
        self.x += dx * self.speed * dt
        self.y += dy * self.speed * dt
        self.sprite.set_facing('right' if dx > 0 else 'left') if abs(dx) > abs(dy) else self.sprite.set_facing('up' if dy > 0 else 'down')
        self.sprite.update(dt, True)

    def can_see(self, player):
        if not self.working:
            return False
        dx, dy = player.x - self.x, player.y - self.y
        dist = hypot(dx, dy)
        if dist > 138 or dist < 0.001:
            return False
        dx, dy = dx / dist, dy / dist
        vec = {'down': (0, -1), 'up': (0, 1),
               'left': (-1, 0), 'right': (1, 0)}[self.sprite.facing]
        return dx * vec[0] + dy * vec[1] >= 0.1

    def draw(self):
        self.sprite.draw(self.x, self.y, 52, 74)
        name = self.display_name + (' · 추적 중!' if self.pursuing else (' · 수면 중 Zzz' if self.sleeping else ''))
        text(int(self.x - 52), int(self.y + 86), name, 14, (253, 249, 239))
