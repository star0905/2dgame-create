"""Room bounds, furnishings, and doors aligned to the supplied mansion art.

Geometry uses the source image's coordinates. Room.point converts them to the
current room's fixed canvas view, including the vertical axis change.
"""
from dataclasses import dataclass, replace
from math import hypot

from sprite import ASSETS, image_for
from pico2d import draw_rectangle

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

    def opening_bounds(self, room):
        """Door art and the lateral trigger use the same source-map half-span."""
        x, y = room.point(*self.point)
        half_span = self.span * room.scale
        if self.direction[0]:
            return x - 13, y - half_span, x + 13, y + half_span
        return x - half_span, y - 13, x + half_span, y + 13

    def caption_position(self, room):
        x, y = room.point(*self.point)
        # Put text above the doorway, leaving the walking opening visible.
        offset = self.span * room.scale + 22 if self.direction[0] else 35
        return x, min(555, y + offset)

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
                     Door('주방', (469, 296), (-1, 0), 36, 'kitchen', (1457, 309)),
                     Door('복도', (1036, 296), (1, 0), 22, 'hall', (538, 780)))),
    'kitchen': Room('주방', (1088, 59, 1512, 485), (1106, 224, 1485, 462),
                    ((1106, 224, 1187, 296, 0), (1221, 308, 1320, 356, 4),
                     (1112, 416, 1158, 457, 0), (1162, 437, 1191, 460, 0),
                     (1195, 435, 1241, 460, 2)),
                    (Door('연회장', (1485, 310), (1, 0), 36, 'banquet', (493, 296)),)),
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


# New rooms use local coordinates; the existing source-art rooms keep theirs.
ROOMS.update({
    'service': Room('사용인 복도', (0, 0, 800, 420), (20, 90, 780, 400),
                    ((270, 90, 350, 265, 3), (490, 225, 570, 400, 3)),
                    (Door('주방 작업구역', (780, 245), (1, 0), 27, 'kitchen', (1135, 350)),
                     Door('서재 보조문', (20, 245), (-1, 0), 27, 'study', (416, 840)))),
    'security_lobby': Room('금고실 앞 경비 구역', (0, 0, 800, 420), (20, 90, 780, 400),
                    ((360, 185, 440, 300, 8),),
                    (Door('복도', (20, 245), (-1, 0), 27, 'hall', (979, 779)),
                     Door('금고실', (780, 245), (1, 0), 27, 'vault', (1108, 779)),
                     Door('보안실', (400, 90), (0, 1), 27, 'security_room', (400, 370)))),
    'security_room': Room('보안실', (0, 0, 800, 420), (20, 90, 780, 400),
                    ((125, 90, 315, 155, 0), (475, 90, 675, 155, 0),
                     (360, 235, 440, 285, 5)),
                    (Door('경비 구역', (400, 400), (0, -1), 27, 'security_lobby', (400, 120)),)),
})
# Opposing door faces keep held movement pointing into the destination room.
ROOMS['kitchen'] = replace(ROOMS['kitchen'], doors=ROOMS['kitchen'].doors + (
    Door('사용인 복도', (1106, 350), (-1, 0), 23, 'service', (750, 245)),))
ROOMS['study'] = replace(ROOMS['study'], doors=ROOMS['study'].doors + (
    Door('사용인 복도', (444, 840), (1, 0), 23, 'service', (50, 245)),))
ROOMS['hall'] = replace(ROOMS['hall'], doors=ROOMS['hall'].doors[:-1] + (
    Door('경비 구역 · 출입 제한', (1008, 779), (1, 0), 25, 'security_lobby', (50, 245)),))
ROOMS['vault'] = replace(ROOMS['vault'], doors=(
    Door('경비 구역', (1081, 779), (-1, 0), 23, 'security_lobby', (750, 245)),))


# The same transform is used for the banquet art and all its dining furniture.
DINING_AREA = (560, 220, 980, 424)
DINING_SCALE = 0.78
DINING_CENTER = (770, 320)
DINING_OFFSET_Y = -12


def dining_point(x, y):
    cx, cy = DINING_CENTER
    return (cx + (x - cx) * DINING_SCALE,
            cy + (y - cy) * DINING_SCALE + DINING_OFFSET_Y)


banquet = ROOMS['banquet']
dining = list(banquet.furniture[6:19])
# Include the tabletop as a solid surface so walking behind the table cannot
# look like walking over the upper half of the table.
dining[0] = (609, 273, 930, 364, 6)
resized_dining = []
for left, top, right, bottom, corner in dining:
    x0, y0 = dining_point(left, top)
    x1, y1 = dining_point(right, bottom)
    resized_dining.append((x0, y0, x1, y1, corner * DINING_SCALE))
ROOMS['banquet'] = Room(banquet.label, banquet.crop, banquet.floor,
                       banquet.furniture[:6] + tuple(resized_dining) + banquet.furniture[19:],
                       banquet.doors)


class MansionMap:
    def __init__(self, stage):
        self.stage = stage

    def update(self, dt):
        pass

    def draw(self):
        name = self.stage.current_room
        room = ROOMS[name]
        if name in ('service', 'security_lobby', 'security_room'):
            self.draw_extension(name, room)
            self.draw_doors(room)
            return
        image = image_for(ASSETS / 'rooms' / f'{name}.png')
        image.draw(SCREEN_W / 2, VIEW_Y, *room.size)
        if name == 'banquet':
            self.draw_dining_area(image, room)
        self.draw_doors(room)

    def draw_doors(self, room):
        for door in room.doors:
            closed = door.target == 'service' and not self.stage.service_discovered
            left, bottom, right, top = map(int, door.opening_bounds(room))
            # A wood frame surrounds a dark opening; the floor threshold marks
            # exactly where the player's feet should cross, rather than its label.
            draw_rectangle(left - 4, bottom - 4, right + 4, top + 4,
                           43, 28, 20, filled=True)
            draw_rectangle(left - 2, bottom - 2, right + 2, top + 2,
                           165, 125, 72, filled=True)
            draw_rectangle(left + 2, bottom + 2, right - 2, top - 2,
                           25, 24, 22, filled=True)
            if closed:
                draw_rectangle(left + 3, bottom + 3, right - 3, top - 3,
                               112, 76, 43, filled=True)
                draw_rectangle(left + 6, bottom + 9, right - 6, top - 9,
                               147, 103, 58)
                cx, cy = int((left + right) / 2), int((bottom + top) / 2)
                draw_rectangle(cx + 3, cy - 2, cx + 6, cy + 2,
                               224, 188, 111, filled=True)
            elif door.direction[0]:
                cy = int((bottom + top) / 2)
                draw_rectangle(left + 2, cy - 4, right - 2, cy + 4,
                               135, 107, 70, filled=True)
                # The open door leaf is folded against the outer side wall.
                edge = left - 7 if door.direction[0] < 0 else right + 3
                draw_rectangle(edge, bottom, edge + 4, top,
                               117, 78, 42, filled=True)
                for yy in (bottom + 7, top - 7):
                    draw_rectangle(left - 3, yy - 2, right + 3, yy + 2,
                                   201, 163, 102, filled=True)
            else:
                cy = int((bottom + top) / 2)
                draw_rectangle(left + 4, cy - 3, right - 4, cy + 3,
                               135, 107, 70, filled=True)
                edge = bottom - 7 if door.direction[1] < 0 else top + 3
                draw_rectangle(left, edge, right, edge + 4,
                               117, 78, 42, filled=True)
                for xx in (left + 7, right - 7):
                    draw_rectangle(xx - 2, bottom - 3, xx + 2, top + 3,
                                   201, 163, 102, filled=True)

    def draw_extension(self, name, room):
        # Reuse parquet/stone textures from the supplied mansion, with furniture
        # footprints shared by rendering, patrol routing and player collision.
        x0, bottom, x1, top = room.rect((0, 0, 800, 420))
        draw_rectangle(int(x0), int(bottom), int(x1), int(top), 43, 36, 32, filled=True)
        image = image_for(ASSETS / 'rooms' / 'banquet.png')
        for y in range(90, 400, 40):
            for x in range(20, 780, 40):
                w, h = min(40, 780 - x), min(40, 400 - y)
                px, py = room.point(x + w / 2, y + h / 2)
                image.clip_draw(31, 201, w, h, px, py, w * room.scale + 1, h * room.scale + 1)
        wall = image_for(ASSETS / 'rooms' / 'vault.png')
        for x in range(20, 780, 40):
            px, py = room.point(x + 20, 55)
            wall.clip_draw(10, 330, 40, 55, px, py, 40 * room.scale + 1, 70 * room.scale)
        for box in room.furniture:
            left, low, right, high = room.rect(box[:4])
            draw_rectangle(int(left), int(low), int(right), int(high), 39, 28, 23, filled=True)
            draw_rectangle(int(left + 4), int(low + 5), int(right - 4), int(high - 4),
                           103, 72, 47, filled=True)
            draw_rectangle(int(left + 8), int(high - 14), int(right - 8), int(high - 10),
                           171, 135, 83, filled=True)
        if name == 'service':
            for x, y in ((310, 120), (310, 230), (530, 255), (530, 355)):
                px, py = room.point(x, y)
                draw_rectangle(int(px - 32), int(py - 3), int(px + 32), int(py + 3),
                               182, 149, 99, filled=True)
                image_for(ASSETS / 'items' / 'coffee.png').draw(px - 15, py + 18, 24, 24)
                draw_rectangle(int(px + 4), int(py + 10), int(px + 27), int(py + 16),
                               206, 202, 179, filled=True)
        if name == 'security_room':
            for x in (180, 250, 530, 600):
                px, py = room.point(x, 118)
                draw_rectangle(int(px - 25), int(py - 5), int(px + 25), int(py + 27),
                               21, 40, 43, filled=True)
                draw_rectangle(int(px - 19), int(py), int(px + 19), int(py + 20),
                               72, 143, 143, filled=True)

    def draw_dining_area(self, image, room):
        left, top, right, bottom = DINING_AREA
        ox, oy, _, image_bottom = room.crop
        # Cover the old dining area with a clean parquet patch from the same
        # room. Draw slightly overlapping tiles to avoid sampling seams.
        for y in range(top, bottom, 40):
            for x in range(left, right, 40):
                width = min(40, right - x)
                height = min(40, bottom - y)
                sx, sy = room.point(x + width / 2, y + height / 2)
                image.clip_draw(475 - ox, image_bottom - 300, width, height,
                                sx, sy, width * room.scale + 1, height * room.scale + 1)
        x0, y0 = dining_point(left, top)
        x1, y1 = dining_point(right, bottom)
        sx, sy = room.point((x0 + x1) / 2, (y0 + y1) / 2)
        image.clip_draw(left - ox, image_bottom - bottom, right - left, bottom - top,
                        sx, sy, (x1 - x0) * room.scale, (y1 - y0) * room.scale)

        # The source crop touches the service trolley. Remove that fragment
        # from the scaled crop, then restore the full trolley at its old spot.
        ax, ay = dining_point(962, 220)
        bx, by = dining_point(980, 256)
        sx, sy = room.point((ax + bx) / 2, (ay + by) / 2)
        image.clip_draw(475 - ox, image_bottom - 300, 20, 40, sx, sy,
                        (bx - ax) * room.scale + 1, (by - ay) * room.scale + 1)
        sx, sy = room.point(991, 229)
        image.clip_draw(960 - ox, image_bottom - 258, 62, 58,
                        sx, sy, 62 * room.scale, 58 * room.scale)
