"""Robbery escape: collision-aware pursuit across the mansion's room graph."""
from collections import deque
from functools import lru_cache
from heapq import heappop, heappush
from math import hypot

from rooms import ROOMS

GRID = 16
RADIUS = 11
CATCH_DISTANCE = 22


def walkable(room_name, x, y):
    room = ROOMS[room_name]
    left, bottom, right, top = room.rect(room.floor)
    return (left + RADIUS <= x <= right - RADIUS and
            bottom + RADIUS <= y <= top - RADIUS and
            not room.blocks_furniture(x, y, RADIUS))


def clear_segment(room_name, a, b):
    steps = max(1, int(hypot(b[0] - a[0], b[1] - a[1]) / 4) + 1)
    return all(walkable(room_name, a[0] + (b[0] - a[0]) * i / steps,
                        a[1] + (b[1] - a[1]) * i / steps)
               for i in range(steps + 1))


@lru_cache(None)
def grid_for(room_name):
    left, bottom, right, top = ROOMS[room_name].rect(ROOMS[room_name].floor)
    nodes = {}
    for ix in range(int((right - left - 2 * RADIUS) / GRID) + 1):
        for iy in range(int((top - bottom - 2 * RADIUS) / GRID) + 1):
            point = left + RADIUS + ix * GRID, bottom + RADIUS + iy * GRID
            if walkable(room_name, *point):
                nodes[ix, iy] = point
    edges = {}
    for key, point in nodes.items():
        edges[key] = [other for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                                            (1, 1), (1, -1), (-1, 1), (-1, -1))
                      if (other := (key[0] + dx, key[1] + dy)) in nodes
                      and clear_segment(room_name, point, nodes[other])]
    return nodes, edges


def path_to(room_name, start, goal):
    if not walkable(room_name, *goal):
        return []
    if clear_segment(room_name, start, goal):
        return [goal]
    nodes, edges = grid_for(room_name)
    def nearest(point):
        for key in sorted(nodes, key=lambda k: hypot(nodes[k][0] - point[0], nodes[k][1] - point[1])):
            if clear_segment(room_name, point, nodes[key]):
                return key
        return None
    first, last = nearest(start), nearest(goal)
    if first is None or last is None:
        return []
    frontier = [(0, first)]
    costs, previous = {first: 0}, {}
    while frontier:
        _, key = heappop(frontier)
        if key == last:
            route = [key]
            while key in previous:
                key = previous[key]
                route.append(key)
            return [nodes[k] for k in reversed(route)] + [goal]
        for other in edges[key]:
            cost = costs[key] + hypot(nodes[key][0] - nodes[other][0], nodes[key][1] - nodes[other][1])
            if cost < costs.get(other, float('inf')):
                costs[other], previous[other] = cost, key
                priority = cost + hypot(nodes[other][0] - goal[0], nodes[other][1] - goal[1])
                heappush(frontier, (priority, other))
    return []


def next_door(source, target):
    queue = deque([(source, None)])
    visited = {source}
    while queue:
        room_name, first = queue.popleft()
        if room_name == target:
            return first
        for door in ROOMS[room_name].doors:
            if door.target in ROOMS and door.target not in visited:
                visited.add(door.target)
                queue.append((door.target, first or door))
    return None


class Pursuit:
    def __init__(self):
        self.active = False
        self.pursuers = []
        self.delay = 0.0
        self.routes = {}
        self.replan = {}
        self.crossing_grace = {}

    def start(self, stage, npcs):
        # A quiet code theft leaves everyone on their normal schedule.
        if self.active or not stage.robbery_triggered:
            return False
        self.active = True
        self.delay = 1.5
        self.pursuers = [npc for npc in npcs if npc.character in ('it_expert', 'planner', 'photographer')
                         and npc.visible and not npc.sleeping]
        for npc in self.pursuers:
            npc.pursuing = True
            npc.working = True
            self.routes[npc] = []
            self.replan[npc] = 0.0
            self.crossing_grace[npc] = 0.0
        return True

    def update(self, dt, stage, player):
        if not self.active:
            return None
        if self.delay > 0:
            self.delay = max(0.0, self.delay - dt)
            return None
        for npc in self.pursuers:
            self.crossing_grace[npc] = max(0.0, self.crossing_grace[npc] - dt)
            captor = npc.brain.tick(dt, stage, player, self)
            if captor is not None:
                return captor
        return None
