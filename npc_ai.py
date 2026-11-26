"""LEC18-style py_trees: reactive chase selection and remembered patrol tasks."""
from math import hypot
import py_trees
from py_trees.common import Access, Status
from py_trees.composites import Selector, Sequence
from pursuit import CATCH_DISTANCE, clear_segment, next_door, path_to
from rooms import ROOMS


class NPCNode(py_trees.behaviour.Behaviour):
    def __init__(self, name, brain, access=None):
        super().__init__(name)
        self.brain = brain
        self.npc = brain.npc
        if access is not None:
            self.blackboard = self.attach_blackboard_client(namespace=brain.namespace)
            for key in ('target_room', 'target', 'target_door'):
                self.blackboard.register_key(key=key, access=access)


class IsUnavailable(NPCNode):
    def update(self):
        return Status.SUCCESS if self.npc.sleeping or not self.npc.working else Status.FAILURE


class Rest(NPCNode):
    def update(self):
        self.npc.sprite.update(self.brain.dt, False)
        return Status.SUCCESS


class CanChase(NPCNode):
    def update(self):
        b = self.brain
        allowed = (b.pursuit is not None and b.pursuit.active and b.pursuit.delay <= 0
                   and b.stage is not None and b.stage.robbery_triggered
                   and self.npc in b.pursuit.pursuers and self.npc.pursuing
                   and self.npc.visible)
        return Status.SUCCESS if allowed else Status.FAILURE


class CanCapture(NPCNode):
    def update(self):
        b, n = self.brain, self.npc
        allowed = (n.room == b.stage.current_room and b.pursuit.crossing_grace[n] == 0
                   and hypot(n.x - b.player.x, n.y - b.player.y) < CATCH_DISTANCE
                   and clear_segment(n.room, (n.x, n.y), (b.player.x, b.player.y)))
        return Status.SUCCESS if allowed else Status.FAILURE


class Capture(NPCNode):
    def update(self):
        self.brain.captor = self.npc
        self.npc.sprite.update(self.brain.dt, False)
        return Status.SUCCESS


class SetChaseTarget(NPCNode):
    def __init__(self, brain):
        super().__init__('Set Chase Target', brain, Access.WRITE)

    def update(self):
        b, n = self.brain, self.npc
        door = next_door(n.room, b.stage.current_room)
        if n.room != b.stage.current_room and door is None:
            return Status.FAILURE
        if door:
            x, y = ROOMS[n.room].point(*door.point)
            goal = x - door.direction[0] * 20, y - door.direction[1] * 20
        else:
            goal = b.player.x, b.player.y
        # Re-evaluate the target every tick, including after the player changes rooms.
        if b.chase_destination != (n.room, b.stage.current_room, door):
            b.pursuit.replan[n] = 0.0
        b.chase_destination = n.room, b.stage.current_room, door
        self.blackboard.target_room = n.room
        self.blackboard.target = goal
        self.blackboard.target_door = door
        return Status.SUCCESS


class MoveToChaseTarget(NPCNode):
    def __init__(self, brain):
        super().__init__('Move To Chase Target', brain, Access.READ)

    def update(self):
        b, n = self.brain, self.npc
        goal = self.blackboard.target
        b.pursuit.replan[n] -= b.dt
        if b.pursuit.replan[n] <= 0:
            b.pursuit.routes[n] = path_to(n.room, (n.x, n.y), goal)
            b.pursuit.replan[n] = 0.35
        status = b.move_along(b.pursuit.routes[n], goal, 150.0)
        if status == Status.FAILURE:
            b.pursuit.replan[n] = 0.0
        return status


class EnterChaseDoor(NPCNode):
    def __init__(self, brain):
        super().__init__('Enter Chase Door', brain, Access.READ)

    def update(self):
        b, n = self.brain, self.npc
        door = self.blackboard.target_door
        if door is not None:
            n.move_to_room(door.target, [door.arrival])
            b.pursuit.routes[n] = []
            b.pursuit.replan[n] = 0.0
            b.pursuit.crossing_grace[n] = 0.65
        # The chase continues next frame, at the new door or beside the player.
        return Status.RUNNING


class HasPatrol(NPCNode):
    def update(self):
        return Status.SUCCESS if self.npc.patrol else Status.FAILURE


class SetPatrolLocation(NPCNode):
    def __init__(self, brain):
        super().__init__('Set Patrol Location', brain, Access.WRITE)

    def update(self):
        n = self.npc
        if not n.patrol:
            return Status.FAILURE
        room, point, wait = n.patrol[n.patrol_index]
        self.blackboard.target_room = room
        self.blackboard.target = ROOMS[room].point(*point)
        self.blackboard.target_door = None
        self.brain.patrol_wait_seconds = wait
        # The index stays here until arrival and observation finish.
        n.patrol_route = []
        return Status.SUCCESS


class MoveToPatrolLocation(NPCNode):
    def __init__(self, brain):
        super().__init__('Move To Patrol Location', brain, Access.READ)

    def update(self):
        b, n = self.brain, self.npc
        room = self.blackboard.target_room
        door = next_door(n.room, room)
        if n.room != room and door is None:
            return Status.FAILURE
        if door:
            x, y = ROOMS[n.room].point(*door.point)
            goal = x - door.direction[0] * 20, y - door.direction[1] * 20
        else:
            goal = self.blackboard.target
        if not n.patrol_route:
            n.patrol_route = path_to(n.room, (n.x, n.y), goal)
        status = b.move_along(n.patrol_route, goal, n.speed)
        if status == Status.SUCCESS and door:
            n.move_to_room(door.target, [door.arrival])
            n.patrol_route = []
            return Status.RUNNING
        return status

    def terminate(self, new_status):
        if new_status == Status.INVALID:
            # A chase may interrupt a patrol. Do not reuse an old-room path on return.
            self.npc.patrol_route = []


class LookAround(NPCNode):
    def initialise(self):
        self.npc.patrol_wait = self.brain.patrol_wait_seconds

    def update(self):
        n = self.npc
        n.patrol_wait = max(0.0, n.patrol_wait - self.brain.dt)
        n.sprite.set_facing(('left', 'up', 'right', 'down')[int(n.patrol_wait) % 4])
        n.sprite.update(self.brain.dt, False)
        if n.patrol_wait > 0:
            return Status.RUNNING
        n.patrol_index = (n.patrol_index + 1) % len(n.patrol)
        return Status.SUCCESS


class LocalMovement(NPCNode):
    def update(self):
        self.npc.update_local_movement(self.brain.dt)
        return Status.RUNNING


class NPCBrain:
    def __init__(self, npc):
        self.npc = npc
        self.namespace = f'/npc/{npc.character}/{id(npc)}'
        self.dt = 0.0
        self.stage = self.player = self.pursuit = self.captor = None
        self.chase_destination = None
        self.patrol_wait_seconds = 0.0
        self.debug = False
        self.last_snapshot = ''
        self.blackboard = py_trees.blackboard.Client(name=npc.display_name, namespace=self.namespace)
        for key in ('target_room', 'target', 'target_door'):
            self.blackboard.register_key(key=key, access=Access.WRITE)
            self.blackboard.set(key, None)
        rest = Sequence('Unavailable', memory=False, children=[
            IsUnavailable('Sleeping or Disabled?', self), Rest('Rest', self)])
        capture = Sequence('Capture', memory=False, children=[
            CanCapture('Within Catch Range?', self), Capture('Capture Player', self)])
        follow = Sequence('Follow Across Rooms', memory=False, children=[
            SetChaseTarget(self), MoveToChaseTarget(self), EnterChaseDoor(self)])
        chase = Sequence('Chase', memory=False, children=[
            CanChase('Robbery Pursuit Active?', self),
            Selector('Capture or Follow', memory=False, children=[capture, follow])])
        patrol = Sequence('Patrol', memory=True, children=[
            HasPatrol('Has Patrol Route?', self), SetPatrolLocation(self),
            MoveToPatrolLocation(self), LookAround('Look Around', self)])
        root = Selector('NPC Behaviour', memory=False, children=[
            rest, chase, patrol, LocalMovement('Local Movement or Idle', self)])
        self.tree = py_trees.trees.BehaviourTree(root)
        self.tree.setup()

    def tick(self, dt, stage=None, player=None, pursuit=None):
        self.dt = max(0.0, dt)
        self.stage, self.player, self.pursuit = stage, player, pursuit
        self.captor = None
        self.tree.tick()
        if self.debug:
            snapshot = self.snapshot()
            if snapshot != self.last_snapshot:
                print(snapshot)
                self.last_snapshot = snapshot
        return self.captor

    def snapshot(self):
        return py_trees.display.unicode_tree(self.tree.root, show_status=True)

    def reset(self):
        self.tree.root.stop(Status.INVALID)
        self.npc.patrol_route = []
        self.npc.patrol_wait = 0.0

    def close(self):
        self.tree.root.stop(Status.INVALID)
        for node in self.tree.root.iterate():
            for client in node.blackboards:
                client.unregister_all_keys(clear=True)
        self.blackboard.unregister_all_keys(clear=True)

    def move_along(self, route, goal, speed):
        n = self.npc
        budget, moving = speed * self.dt, False
        while route and budget > 0:
            tx, ty = route[0]
            dx, dy = tx - n.x, ty - n.y
            distance = hypot(dx, dy)
            if distance < 0.01:
                route.pop(0)
                continue
            step = min(distance, budget, 8.0)
            nx, ny = n.x + dx / distance * step, n.y + dy / distance * step
            if not clear_segment(n.room, (n.x, n.y), (nx, ny)):
                route.clear()
                break
            n.x, n.y = nx, ny
            budget -= step
            moving = True
            n.sprite.set_facing(('right' if dx > 0 else 'left') if abs(dx) > abs(dy)
                                else ('up' if dy > 0 else 'down'))
            if step >= distance:
                route.pop(0)
        n.sprite.update(self.dt, moving)
        if hypot(n.x - goal[0], n.y - goal[1]) < 3:
            return Status.SUCCESS
        return Status.RUNNING if route else Status.FAILURE
