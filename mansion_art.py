"""Compose extension rooms from the original mansion room textures.

Only existing repository assets are required. Furniture cutouts are prepared
as cached temporary game textures; the original paintings stay unchanged.
"""
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw
from sprite import ASSETS, image_for

_textures = TemporaryDirectory(prefix='crimegame-mansion-')
SPRITES = {
    'bookcase': ('study', (42, 32, 146, 145)),
    'cupboard': ('study', (162, 174, 284, 277)),
    'console_desk': ('foyer', (47, 141, 137, 204)),
}


@lru_cache(None)
def furniture_image(name):
    room_name, crop = SPRITES[name]
    with Image.open(ASSETS / 'rooms' / (room_name + '.png')) as source:
        image = source.convert('RGBA').crop(crop)
    width, height = image.size
    mask = Image.new('L', image.size, 0)
    if name == 'cupboard':
        # Keep the tabletop, legs, chair and objects, leaving the rug behind.
        outline = [(45, 0), (97, 0), (97, 23), (120, 23), (120, 98),
                   (111, 98), (111, 83), (10, 83), (10, 98), (2, 98),
                   (2, 23), (32, 23), (32, 9), (45, 9)]
    else:
        outline = [(2, 1), (width - 3, 1), (width - 3, height - 10),
                   (width - 6, height - 1), (width - 12, height - 1),
                   (width - 12, height - 5), (12, height - 5),
                   (12, height - 1), (5, height - 1), (2, height - 10)]
    ImageDraw.Draw(mask).polygon(outline, fill=255)
    image.putalpha(mask)
    path = Path(_textures.name) / (name + '.png')
    image.save(path)
    return image_for(path)


@lru_cache(None)
def texture_height(name):
    with Image.open(ASSETS / 'rooms' / (name + '.png')) as image:
        return image.height


def patch(room, source, area):
    name, (sx, sy, sw, sh) = source
    left, bottom, right, top = room.rect(area)
    image_for(ASSETS / 'rooms' / (name + '.png')).clip_draw(
        sx, texture_height(name) - sy - sh, sw, sh,
        (left + right) / 2, (top + bottom) / 2, right - left, top - bottom)


def tile(room, source, area, step=80):
    left, top, right, bottom = area
    for y in range(top, bottom, step):
        for x in range(left, right, step):
            patch(room, source, (x, y, min(x + step, right), min(y + step, bottom)))


def furniture(room, name, footprint, rise=20):
    left, top, right, bottom = footprint[:4]
    x, y = room.point((left + right) / 2, bottom)
    width = (right - left) * room.scale
    height = (bottom - top + rise) * room.scale
    furniture_image(name).draw(x, y + height / 2, width, height)


WOOD_FLOOR = ('banquet', (31, 201, 40, 40))
WALL = ('banquet', (31, 15, 48, 88))
TRIM = ('foyer', (16, 405, 80, 11))
RUG = ('hall', (130, 140, 310, 100))


def draw_extension(room, name):
    tile(room, WOOD_FLOOR, (20, 90, 780, 400))
    tile(room, WALL, (0, 0, 800, 90), step=100)
    patch(room, TRIM, (0, 83, 800, 94))
    patch(room, TRIM, (0, 400, 800, 412))
    patch(room, TRIM, (0, 90, 20, 412))
    patch(room, TRIM, (780, 90, 800, 412))
    # Exits are breaks in the room boundary, with no floating door overlays.
    for door in room.doors:
        x, y = door.point
        if door.direction[0]:
            area = (0 if door.direction[0] < 0 else 780, y - door.span,
                    20 if door.direction[0] < 0 else 800, y + door.span)
        elif door.direction[1] > 0:
            area = (x - door.span, 0, x + door.span, 94)
        else:
            area = (x - door.span, 400, x + door.span, 420)
        tile(room, WOOD_FLOOR, area)
    if name == 'security_lobby':
        patch(room, RUG, (300, 145, 500, 350))
    elif name == 'security_room':
        patch(room, RUG, (325, 210, 475, 320))
    for i, box in enumerate(room.furniture):
        if name == 'service':
            left, top, right, bottom = box[:4]
            middle = (top + bottom) / 2
            furniture(room, 'bookcase', (left, top, right, middle), rise=12)
            furniture(room, 'bookcase', (left, middle, right, bottom), rise=12)
        elif name == 'security_room' and i < 2:
            furniture(room, 'console_desk', box, rise=10)
        else:
            furniture(room, 'cupboard', box)
    if name == 'security_room':
        # Reuse the framed terminal from the foyer, on the cabinet tops.
        terminal = image_for(ASSETS / 'rooms' / 'foyer.png')
        for x in (185, 255, 535, 605):
            px, py = room.point(x, 92)
            terminal.clip_draw(85, 438 - 365, 43, 32, px, py,
                               43 * room.scale, 32 * room.scale)


def work_passage(room, door):
    x, y = door.point
    source = ('kitchen', (230, 300, 40, 40)) if room.label == '주방' else WOOD_FLOOR
    tile(room, source, (x - 14, y - door.span, x + 14, y + door.span))
