"""All mansion NPCs use the same animated class with different data."""
from math import hypot
from sprite import SpriteAnimator
from ui import text
from rooms import ROOMS
from pursuit import path_to, next_door, clear_segment


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
        self.patrol = []
        self.patrol_index = 0
        self.patrol_wait = 0.0
        self.patrol_route = []
        self.move_to_room(room, path)

    def move_to_room(self, room, path):
        self.room = room
        self.path = [ROOMS[room].point(*point) for point in path]
        self.x, self.y = self.path[0]
        self.path_index = 0

    def update(self, dt):
        if self.pursuing:
            return  # Pursuit owns movement and animation during the escape.
        if self.patrol and self.working and not self.sleeping:
            self.update_patrol(dt)
            return
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

    def set_patrol(self, stops):
        """Stops are (room, original-map point, seconds spent looking around)."""
        self.patrol = list(stops)
        self.patrol_index = 0
        self.patrol_wait = 0.0
        self.patrol_route = []

    def update_patrol(self, dt):
        if self.patrol_wait > 0:
            self.patrol_wait = max(0, self.patrol_wait - dt)
            # Look around while stopped, creating predictable gaps in coverage.
            facing = ('left', 'up', 'right', 'down')[int(self.patrol_wait) % 4]
            self.sprite.set_facing(facing)
            self.sprite.update(dt, False)
            return
        target_room, point, wait = self.patrol[self.patrol_index]
        door = next_door(self.room, target_room)
        if door:
            x, y = ROOMS[self.room].point(*door.point)
            goal = x - door.direction[0] * 20, y - door.direction[1] * 20
        else:
            goal = ROOMS[self.room].point(*point)
        if not self.patrol_route:
            self.patrol_route = path_to(self.room, (self.x, self.y), goal)
        budget, moving = self.speed * max(0.0, dt), False
        while self.patrol_route and budget > 0:
            tx, ty = self.patrol_route[0]
            dx, dy = tx - self.x, ty - self.y
            distance = hypot(dx, dy)
            if distance < 0.01:
                self.patrol_route.pop(0)
                continue
            step = min(distance, budget, 8)
            nx, ny = self.x + dx / distance * step, self.y + dy / distance * step
            if not clear_segment(self.room, (self.x, self.y), (nx, ny)):
                self.patrol_route = []
                break
            self.x, self.y = nx, ny
            budget -= step
            moving = True
            self.sprite.set_facing(('right' if dx > 0 else 'left') if abs(dx) > abs(dy)
                                   else ('up' if dy > 0 else 'down'))
            if step >= distance:
                self.patrol_route.pop(0)
        self.sprite.update(dt, moving)
        if hypot(self.x - goal[0], self.y - goal[1]) < 3:
            if door:
                self.move_to_room(door.target, [door.arrival])
                self.patrol_route = []
            else:
                self.patrol_wait = wait
                self.patrol_index = (self.patrol_index + 1) % len(self.patrol)
                self.patrol_route = []

    def can_see(self, player):
        if not self.working:
            return False
        dx, dy = player.x - self.x, player.y - self.y
        dist = hypot(dx, dy)
        if dist > 165 or dist < 0.001:
            return False
        if not clear_segment(self.room, (self.x, self.y), (player.x, player.y)):
            return False
        dx, dy = dx / dist, dy / dist
        vec = {'down': (0, -1), 'up': (0, 1),
               'left': (-1, 0), 'right': (1, 0)}[self.sprite.facing]
        return dx * vec[0] + dy * vec[1] >= 0.1

    def draw(self):
        self.sprite.draw(self.x, self.y, 52, 74)
        name = self.display_name + (' · 추적 중!' if self.pursuing else (' · 수면 중 Zzz' if self.sleeping else ''))
        text(int(self.x - 52), int(self.y + 86), name, 14, (253, 249, 239))
