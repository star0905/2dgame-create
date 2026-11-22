"""Items belong to a specific room and retain their state between visits."""
from sprite import ASSETS, image_for
from ui import text

ITEM_LABELS = {
    'knife': '주방칼', 'sleeping_pills': '수면제', 'protein': '프로틴',
    'coffee': '커피', 'jewel': '보석', 'sleeping_coffee': '수면제가 든 커피',
}


def item_image(item_name):
    image_name = 'coffee' if item_name == 'sleeping_coffee' else item_name
    return image_for(ASSETS / 'items' / f'{image_name}.png')


class WorldItem:
    def __init__(self, item_name, room, x, y, display_position=None, dropped=False):
        self.item_name = item_name
        self.room = room
        self.x, self.y = x, y
        self.dropped = dropped
        self.display_position = display_position
        self.image = item_image(item_name)
        self.visible = True

    def draw(self):
        x, y = self.display_position or (self.x, self.y + 12)
        self.image.draw(x, y, 35, 35)
        if self.item_name == 'sleeping_coffee':
            text(int(self.x - 38), int(self.y + 43), '수면 커피', 14, (210, 186, 255))


class FixedProp:
    def __init__(self, name, room, x, y, label):
        self.name = name
        self.room = room
        self.x, self.y = x, y
        self.label = label
        self.visible = True

    def draw(self):
        text(int(self.x - 7 * len(self.label)), int(self.y + 15), self.label, 15, (255, 236, 179))
