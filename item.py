"""Items belong to a specific room and retain their state between visits."""
from sprite import ASSETS, image_for
from ui import text

ITEM_LABELS = {
    'knife': '주방칼', 'sleeping_pills': '수면제', 'protein': '프로틴',
    'coffee': '커피', 'jewel': '보석',
}


class WorldItem:
    def __init__(self, item_name, room, x, y):
        self.item_name = item_name
        self.room = room
        self.x, self.y = x, y
        self.image = image_for(ASSETS / 'items' / f'{item_name}.png')
        self.visible = True

    def draw(self):
        self.image.draw(self.x, self.y + 12, 35, 35)


class FixedProp:
    def __init__(self, name, room, x, y, label):
        self.name = name
        self.room = room
        self.x, self.y = x, y
        self.label = label
        self.visible = True

    def draw(self):
        text(int(self.x - 7 * len(self.label)), int(self.y + 15), self.label, 15, (255, 236, 179))
