"""Room bounds, furnishings, and doors aligned to the supplied mansion art.

Geometry uses the source image's coordinates. Room.point converts them to the
current room's fixed canvas view, including the vertical axis change.
"""
from dataclasses import dataclass

from sprite import ASSETS, image_for

SCREEN_W, SCREEN_H = 960, 640
VIEW_W, VIEW_H = 920, 490
VIEW_Y = 338
FOYER_START = (233, 357)


@dataclass(frozen=True)
class Door:
    label: str
    point: tuple
    direction: tuple
    span: int
    target: str
    arrival: tuple = ()

    def reached(self, room, x, y, dx, dy):
        px, py = room.point(*self.point)
        nx, ny = self.direction
        if dx * nx + dy * ny <= 0:
            return False
        depth = (x - px) * nx + (y - py) * ny
        sideways = abs((x - px) * ny - (y - py) * nx)
        return -25 <= depth <= 10 and sideways <= self.span * room.scale


@dataclass(frozen=True)
class Room:
    label: str
    crop: tuple
    floor: tuple
    furniture: tuple
    doors: tuple

    @property
    def scale(self):
        x0, y0, x1, y1 = self.crop
        return min(VIEW_W / (x1 - x0), VIEW_H / (y1 - y0))

    @property
    def size(self):
        x0, y0, x1, y1 = self.crop
        return (x1 - x0) * self.scale, (y1 - y0) * self.scale

    def point(self, x, y):
        x0, y0, x1, y1 = self.crop
        return (SCREEN_W / 2 + (x - (x0 + x1) / 2) * self.scale,
                VIEW_Y - (y - (y0 + y1) / 2) * self.scale)

    def rect(self, box):
        x0, y0, x1, y1 = box
        left, bottom = self.point(x0, y1)
        right, top = self.point(x1, y0)
        return left, bottom, right, top


ROOMS = {
    'foyer': Room('현관', (47, 59, 419, 497), (63, 157, 402, 464),
                  ((76, 157, 117, 188), (347, 157, 392, 188),
                   (92, 194, 185, 264), (283, 194, 375, 264),
                   (75, 379, 121, 441), (127, 400, 176, 449),
                   (295, 400, 338, 449), (347, 382, 395, 446)),
                  (Door('연회장', (233, 157), (0, 1), 24, 'banquet', (758, 442)),
                   Door('저택 밖', (233, 464), (0, -1), 24, 'outside'))),
    'banquet': Room('연회장', (444, 59, 1063, 501), (469, 162, 1036, 467),
                    ((523, 162, 570, 189), (655, 158, 700, 203),
                     (708, 162, 825, 204), (835, 158, 880, 203),
                     (943, 162, 987, 189), (963, 202, 1020, 254),
                     (607, 273, 934, 363), (650, 223, 879, 274),
                     (648, 358, 884, 418), (566, 288, 595, 344),
                     (940, 283, 979, 345), (470, 364, 507, 460),
                     (985, 387, 1032, 460)),
                    (Door('현관', (757, 467), (0, -1), 24, 'foyer', (233, 183)),
                     Door('주방', (469, 296), (-1, 0), 22, 'kitchen', (1457, 309)),
                     Door('복도', (1036, 296), (1, 0), 22, 'hall', (538, 780)))),
    'kitchen': Room('주방', (1088, 59, 1512, 485), (1106, 224, 1485, 462),
                    ((1106, 224, 1187, 296), (1219, 285, 1325, 356),
                     (1112, 390, 1244, 462)),
                    (Door('연회장', (1485, 310), (1, 0), 20, 'banquet', (493, 296)),)),
    'study': Room('서재', (30, 549, 463, 965), (47, 674, 444, 924),
                   # The chair and desk have separate footprints so the
                   # exposed rug behind and beside the chair stays walkable.
                   ((72, 674, 176, 693), (188, 670, 220, 693),
                    (277, 670, 307, 693), (317, 674, 420, 693),
                    (73, 701, 112, 809), (234, 723, 266, 752),
                    (193, 751, 311, 824), (73, 856, 114, 910),
                    (338, 873, 365, 902), (386, 856, 428, 910)),
                   (Door('복도', (245, 924), (0, -1), 23, 'hall', (761, 748)),)),
    'hall': Room('복도', (482, 608, 1037, 917), (510, 722, 1008, 899), (),
                 (Door('연회장', (510, 779), (-1, 0), 25, 'banquet', (1010, 294)),
                  Door('서재', (761, 722), (0, 1), 24, 'study', (245, 898)),
                  Door('금고실', (1008, 779), (1, 0), 25, 'vault', (1108, 779)))),
    'vault': Room('금고실', (1049, 549, 1508, 951), (1081, 711, 1475, 901),
                  ((1081, 711, 1146, 725), (1149, 711, 1312, 722),
                   (1340, 711, 1452, 749), (1082, 859, 1124, 900),
                   (1387, 829, 1471, 900)),
                  (Door('복도', (1081, 779), (-1, 0), 23, 'hall', (979, 779)),)),
}


class MansionMap:
    def __init__(self, stage):
        self.stage = stage

    def update(self, dt):
        pass

    def draw(self):
        name = self.stage.current_room
        image = image_for(ASSETS / 'rooms' / f'{name}.png')
        image.draw(SCREEN_W / 2, VIEW_Y, *ROOMS[name].size)
