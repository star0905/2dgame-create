"""Room bounds, furnishings, and doors aligned to the supplied mansion art.

Geometry uses the source image's coordinates. Room.point converts them to the
current room's fixed canvas view, including the vertical axis change.
"""
from dataclasses import dataclass
from math import hypot

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
    # Each footprint is (left, top, right, bottom, corner_radius) in map
    # pixels. A zero corner radius keeps straight edges for square furniture.
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

    def blocks_furniture(self, x, y, player_radius):
        for left, top, right, bottom, corner in self.furniture:
            x0, y0, x1, y1 = self.rect((left, top, right, bottom))
            corner *= self.scale
            # A rounded rectangle is an inset box plus a round margin.
            cx = max(x0 + corner, min(x, x1 - corner))
            cy = max(y0 + corner, min(y, y1 - corner))
            if hypot(x - cx, y - cy) < player_radius + corner:
                return True
        return False


ROOMS = {
    'foyer': Room('현관', (47, 59, 419, 497), (63, 157, 402, 464),
                  ((80, 160, 116, 191, 13), (352, 160, 389, 190, 13),
                   (94, 223, 184, 263, 0), (285, 223, 375, 263, 0),
                   (77, 410, 117, 444, 15), (130, 422, 175, 449, 0),
                   (296, 422, 337, 449, 0), (353, 413, 394, 444, 14)),
                  (Door('연회장', (233, 157), (0, 1), 24, 'banquet', (758, 442)),
                   Door('저택 밖', (233, 464), (0, -1), 24, 'outside'))),
    'banquet': Room('연회장', (444, 59, 1063, 501), (469, 162, 1036, 467),
                    ((529, 159, 568, 190, 14), (656, 169, 699, 204, 10),
                     (710, 164, 824, 200, 0), (837, 169, 880, 204, 10),
                     (949, 159, 985, 189, 13), (965, 220, 1021, 254, 3),
                     # Dining table and individual chairs use their floor footprints.
                     (609, 306, 930, 364, 6),
                     (656, 247, 694, 273, 8), (702, 247, 740, 273, 8),
                     (748, 247, 786, 273, 8), (795, 247, 833, 273, 8),
                     (841, 247, 878, 273, 8),
                     (651, 386, 691, 419, 9), (699, 386, 740, 419, 9),
                     (747, 386, 788, 419, 9), (795, 386, 836, 419, 9),
                     (843, 386, 884, 419, 9),
                     (569, 305, 598, 344, 8), (944, 305, 976, 344, 8),
                     (470, 383, 506, 462, 0), (986, 418, 1030, 460, 0)),
                    (Door('현관', (757, 467), (0, -1), 24, 'foyer', (233, 183)),
                     Door('주방', (469, 296), (-1, 0), 22, 'kitchen', (1457, 309)),
                     Door('복도', (1036, 296), (1, 0), 22, 'hall', (538, 780)))),
    'kitchen': Room('주방', (1088, 59, 1512, 485), (1106, 224, 1485, 462),
                    ((1106, 224, 1187, 296, 0), (1221, 308, 1320, 356, 4),
                     (1112, 416, 1158, 457, 0), (1162, 437, 1191, 460, 0),
                     (1195, 435, 1241, 460, 2)),
                    (Door('연회장', (1485, 310), (1, 0), 20, 'banquet', (493, 296)),)),
    'study': Room('서재', (30, 549, 463, 965), (47, 674, 444, 924),
                   # The chair and desk have separate footprints so the
                   # exposed rug behind and beside the chair stays walkable.
                   ((72, 674, 176, 693, 0), (187, 668, 220, 694, 11),
                    (277, 668, 307, 694, 11), (317, 674, 420, 693, 0),
                    (73, 715, 112, 809, 0), (234, 723, 266, 752, 7),
                    (193, 751, 311, 824, 3), (73, 862, 114, 910, 9),
                    (335, 875, 367, 902, 11), (386, 862, 428, 910, 9)),
                   (Door('복도', (245, 924), (0, -1), 23, 'hall', (761, 748)),)),
    'hall': Room('복도', (482, 608, 1037, 917), (510, 722, 1008, 899), (),
                 (Door('연회장', (510, 779), (-1, 0), 25, 'banquet', (1010, 294)),
                  Door('서재', (761, 722), (0, 1), 24, 'study', (245, 898)),
                  Door('금고실', (1008, 779), (1, 0), 25, 'vault', (1108, 779)))),
    'vault': Room('금고실', (1049, 549, 1508, 951), (1081, 711, 1475, 901),
                  ((1081, 711, 1146, 725, 0), (1149, 711, 1312, 722, 0),
                   (1344, 702, 1452, 726, 0), (1392, 722, 1422, 749, 7),
                   (1088, 877, 1125, 899, 0), (1388, 878, 1422, 897, 0),
                   (1426, 863, 1472, 898, 0)),
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
