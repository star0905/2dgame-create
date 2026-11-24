"""Visible sweeping cameras with warning time, occlusion and separate controls."""
from math import atan2, cos, sin, pi, hypot
from pico2d import draw_rectangle
from rooms import ROOMS
from ui import text

WARNING_SECONDS = 1.0
CAMERA_SHUTDOWN_SECONDS = 45.0


def sight_clear(room_name, start, target):
    # Optics ignore the player's radius; desks and solid furniture block rays.
    distance = hypot(target[0] - start[0], target[1] - start[1])
    count = max(1, int(distance / 5))
    room = ROOMS[room_name]
    return all(not room.blocks_furniture(start[0] + (target[0] - start[0]) * i / count,
                                        start[1] + (target[1] - start[1]) * i / count, 0.5)
               for i in range(1, count + 1))


class Camera:
    def __init__(self, room, point, angle, sweep=0.65, phase=0):
        self.room = room
        self.x, self.y = ROOMS[room].point(*point)
        self.base_angle = angle
        self.sweep = sweep
        self.phase = phase
        self.time = 0.0
        self.exposure = 0.0
        self.range = 310
        self.half_angle = pi / 7

    @property
    def angle(self):
        return self.base_angle + self.sweep * sin(self.time * 0.55 + self.phase)

    def sees(self, player):
        dx, dy = player.x - self.x, player.y - self.y
        if hypot(dx, dy) > self.range:
            return False
        difference = (atan2(dy, dx) - self.angle + pi) % (2 * pi) - pi
        return (abs(difference) <= self.half_angle and
                sight_clear(self.room, (self.x, self.y), (player.x, player.y)))

    def draw(self, disabled):
        color = (74, 101, 99) if disabled else ((231, 111, 75) if self.exposure else (101, 171, 176))
        if not disabled:
            room = ROOMS[self.room]
            left, bottom, right, top = room.rect(room.floor)
            # Dotted floor rays stay below actors and show both the sweep and
            # blind areas behind the same furniture that blocks detection.
            for offset in (-self.half_angle, -self.half_angle / 2, 0,
                           self.half_angle / 2, self.half_angle):
                angle = self.angle + offset
                for distance in range(22, self.range, 16):
                    x, y = self.x + cos(angle) * distance, self.y + sin(angle) * distance
                    if room.blocks_furniture(x, y, 0.5):
                        break
                    if left <= x <= right and bottom <= y <= top:
                        draw_rectangle(int(x - 2), int(y - 2), int(x + 2), int(y + 2), *color, filled=True)
        draw_rectangle(int(self.x - 4), int(self.y + 5), int(self.x + 4), int(self.y + 32),
                       68, 69, 65, filled=True)
        draw_rectangle(int(self.x - 18), int(self.y + 10), int(self.x + 18), int(self.y + 27),
                       188, 187, 172, filled=True)
        draw_rectangle(int(self.x - 10), int(self.y + 8), int(self.x + 10), int(self.y + 14),
                       28, 37, 38, filled=True)
        draw_rectangle(int(self.x + 10), int(self.y + 17), int(self.x + 14), int(self.y + 21),
                       *color, filled=True)
        label = '감시 정지' if disabled else ('감지 중!' if self.exposure else '감시 카메라')
        text(int(self.x - 42), int(self.y + 45), label, 14, color)
        if self.exposure and not disabled:
            draw_rectangle(int(self.x - 25), int(self.y - 13),
                           int(self.x - 25 + 50 * min(1, self.exposure / WARNING_SECONDS)),
                           int(self.y - 8), 240, 132, 90, filled=True)


class Surveillance:
    def __init__(self):
        self.cameras = [
            Camera('hall', (920, 745), -pi / 2, 0.8),
            Camera('security_lobby', (735, 125), -2.4, 0.65, 1.0),
        ]
        self.disabled_remaining = 0.0

    def disable(self):
        self.disabled_remaining = CAMERA_SHUTDOWN_SECONDS
        for camera in self.cameras:
            camera.exposure = 0.0

    def update(self, dt, stage, player):
        self.disabled_remaining = max(0.0, self.disabled_remaining - dt)
        notice = None
        for camera in self.cameras:
            camera.time += dt
            danger = (player.held_item in ('knife', 'jewel') or
                      stage.current_room in ('security_lobby', 'security_room', 'vault'))
            if (self.disabled_remaining > 0 or camera.room != stage.current_room or
                    not danger or not camera.sees(player)):
                camera.exposure = 0.0
                continue
            previous = camera.exposure
            camera.exposure += max(0.0, dt)
            if previous == 0:
                notice = '카메라가 수상한 행동을 감지 중입니다! 시야를 벗어나세요.'
            if camera.exposure >= WARNING_SECONDS and stage.invulnerability_timer <= 0:
                stage.suspicion = min(4, stage.suspicion + 1)
                stage.invulnerability_timer = 2.5
                stage.warning_timer = 1.8
                stage.warning_message = '감시 카메라에 기록되었습니다!'
                notice = '감시 카메라에 수상한 행동이 기록되었습니다. (의심도 +1)'
        return notice

    def draw(self, room):
        for camera in self.cameras:
            if camera.room == room:
                camera.draw(self.disabled_remaining > 0)
