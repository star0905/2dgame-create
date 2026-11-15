"""LEC14_Game_World의 3개 레이어 방식 유지."""
world = [[], [], []]  # 0: background, 1: characters/items, 2: foreground


def add_object(obj, depth):
    if not (0 <= depth < len(world)):
        raise ValueError('Invalid world layer')
    world[depth].append(obj)


def remove_object(obj):
    for layer in world:
        if obj in layer:
            layer.remove(obj)
            return
    raise ValueError('Object not found')


def clear():
    for layer in world:
        layer.clear()


def update(dt):
    # Snapshot: safe if an object removes itself or spawns an item during update.
    for layer in world:
        for obj in list(layer):
            if obj in layer:
                obj.update(dt)


def render():
    for layer in world:
        for obj in list(layer):
            obj.draw()
