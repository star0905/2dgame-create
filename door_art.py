"""Upright door sprites, never rotated into floor steps or ladders."""
import json
from functools import lru_cache
from pico2d import draw_rectangle
from sprite import ASSETS, image_for


@lru_cache(None)
def door_manifest():
    return json.loads((ASSETS / 'doors' / 'manifest.json').read_text(encoding='utf-8'))


def sprite_layout(door, room, closed=False):
    x, y = room.point(*door.point)
    orientation = 'side' if door.direction[0] else 'front'
    name = orientation + ('_closed' if closed else '_open')
    clip = door_manifest()[name]['clip']
    if orientation == 'side':
        half_span = door.span * room.scale
        height = min(142.0, max(104.0, 2 * half_span + 58))
        bottom = y - half_span
        width = height * clip[2] / clip[3]
        # Keep the outer jamb on the side wall, with the leaf opening inward.
        center_x = x - door.direction[0] * width / 2
    else:
        bottom = y
        height = min(100.0, max(76.0, 555 - bottom))
        width = height * clip[2] / clip[3]
        center_x = x
    return name, clip, (center_x, bottom + height / 2, width, height)


def draw_door(door, room, closed=False):
    name, clip, (x, y, width, height) = sprite_layout(door, room, closed)
    image = image_for(ASSETS / 'doors' / (name + '.png'))
    if name == 'front_open':
        # The original open-door cutout has a transparent central aperture.
        # Fill only that aperture so a stone wall cannot show through it.
        bottom = y - height / 2
        draw_rectangle(int(x - width * .24), int(bottom + height * .14),
                       int(x + width * .24), int(bottom + height * .91),
                       16, 14, 13, filled=True)
    if door.direction[0] < 0:
        image.clip_composite_draw(*clip, 0, 'h', x, y, width, height)
    else:
        image.clip_draw(*clip, x, y, width, height)
