"""No external window or pico2d needed. Run from project root."""
from pathlib import Path
import sys
import types
from PIL import Image

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

# Minimal stubs for logic/render contract tests in CI/headless environments.
lib = types.ModuleType('pico2d')
class TestImage:
    def __init__(self, src):
        assert Path(src).is_file(), src
        self.src = src
        self.drawn = []
    def clip_draw(self, *args): self.drawn.append(('clip',args))
    def draw(self,*args): self.drawn.append(('draw',args))
class TestFont:
    def draw(self, *args): pass
lib.load_image = TestImage
lib.load_font = lambda *args: TestFont()
lib.SDL_KEYDOWN = 1
lib.SDL_KEYUP = 2
lib.SDL_QUIT = 3
lib.open_canvas = lambda *args: None
lib.close_canvas = lambda *args: None
lib.clear_canvas = lambda *args: None
lib.update_canvas = lambda *args: None
lib.draw_rectangle = lambda *args, **kwargs: None
lib.get_events = lambda: []
lib.delay = lambda *args: None
sys.modules['pico2d'] = lib

sdl = types.ModuleType('sdl2')
for i,name in enumerate(['w','a','s','d','UP','DOWN','LEFT','RIGHT',
                         'ESCAPE','RETURN','SPACE','r','e','q','BACKSPACE'], start=11):
    setattr(sdl,'SDLK_'+name,i)
sys.modules['sdl2'] = sdl

from sprite import SpriteAnimator
from stage import Stage
from player import Player
import play_mode
import title_mode
from rooms import ROOMS

character_files=list((BASE/'assets'/'characters').glob('*.png'))
assert len(character_files)==8, f'expected 8 chars, got {character_files}'
for fn in character_files:
    im=Image.open(fn)
    assert im.mode=='RGBA', fn
    assert im.size == (512, 512), (fn,im.size)
    assert im.getpixel((0,0))[3]==0, fn
    for row in range(4):
        for col in range(4):
            a=im.crop((128*col,128*row,128*(col+1),128*(row+1))).getchannel('A')
            assert a.getbbox() is not None, (fn, row, col)

spr=SpriteAnimator('culprit')
for direction,bottom in [('down',384),('up',256),('left',128),('right',0)]:
    spr.set_facing(direction)
    spr.update(0.2, True)
    spr.draw(20,30)
    _,args=spr.image.drawn[-1]
    assert args[1]==bottom, (direction,args)
assert spr.frame in range(4)
spr.update(0.01,False)
assert spr.frame==0

stage=Stage()
p=Player(stage)
x=p.x
p.keys.add(sdl.SDLK_d)
p.update(.1)
assert p.x>x and p.sprite.facing=='right'
p.keys.clear()
p.update(.1)
assert p.sprite.frame==0
p.held_item='knife'
hazard=stage.hazard_of(p)
assert hazard==('knife_outside_kitchen',2)
p.held_item='jewel'
assert stage.hazard_of(p)[1]==2
assert stage.robbery_outcome()[0]==False
assert stage.robbery_triggered
stage.athlete_unavailable=True
stage.security_disabled=True
stage.photographer_busy=True
assert stage.robbery_outcome()[0]==True and stage.safe_open

title_mode.init()
title_mode.draw()
play_mode.init()
play_mode.dialogue.pages = []
assert len(play_mode.npcs)==6
assert play_mode.stage.current_room == 'foyer'
for name, room in ROOMS.items():
    for door in room.doors:
        if door.target != 'outside':
            other = ROOMS[door.target]
            play_mode.stage.current_room = door.target
            assert play_mode.stage.can_move(*other.point(*door.arrival)), (name, door)
            assert any(back.target == name for back in other.doors), (name, door)
play_mode.stage.current_room = 'foyer'
assert not play_mode.stage.can_move(*ROOMS['foyer'].point(155, 148))
play_mode.player.x, play_mode.player.y = ROOMS['foyer'].point(233, 174)
play_mode.player.keys.add(sdl.SDLK_w)
play_mode.update()
assert play_mode.stage.current_room == 'banquet'
assert play_mode._nearest_interactable() is None
play_mode.player.keys.clear()
play_mode.draw()

assert len(play_mode.items)==3
assert play_mode.player.character=='culprit'
# Ensure every actor and item has a readable sprite/image.
for o in play_mode.npcs + play_mode.items + play_mode.props + [play_mode.player]:
    o.draw()
# Changing direction and moving world objects also executes without exceptions.
for i in range(10):
    play_mode.player.keys.add(sdl.SDLK_w)
    play_mode.update()
play_mode.finish()
print('PASS: 8 RGBA sheets, 16 frames each, direction clipping, movement, interactions, stage branching, scene init/render')

# Empty carpet beside the study chair is reachable, while the chair and desk
# still block the player's feet.
study = ROOMS['study']
stage.current_room = 'study'
assert stage.can_move(*study.point(213, 733))
assert stage.can_move(*study.point(288, 733))
assert not stage.can_move(*study.point(250, 737))
assert not stage.can_move(*study.point(250, 786))

# Send E through the normal event handler, including competing targets.
from types import SimpleNamespace

play_mode.init()
play_mode.dialogue.pages = []
player = play_mode.player
coffee = play_mode.items[2]
play_mode.stage.current_room = coffee.room
player.x, player.y = coffee.x, coffee.y
player.sprite.set_facing('right')
assert play_mode._nearest_interactable() is coffee
assert '커피' in play_mode._interaction_hint(coffee)
press_e = SimpleNamespace(type=lib.SDL_KEYDOWN, key=sdl.SDLK_e)
play_mode.get_events = lambda: [press_e]
play_mode.handle_events()
assert player.held_item == 'coffee' and not coffee.visible

play_mode.stage.current_room = 'vault'
safe, alarm = play_mode.props[:2]
player.x, player.y = safe.x, safe.y - 60
player.sprite.set_facing('up')
assert play_mode._nearest_interactable() is safe
play_mode.handle_events()
assert play_mode.input_code_mode

play_mode.init()
play_mode.dialogue.pages = []
play_mode.stage.current_room = 'banquet'
npc = play_mode.npcs[0]
npc.room = 'banquet'  # Controlled fixture for facing-priority comparison.
coffee = play_mode.items[2]
play_mode.player.x, play_mode.player.y = 450, 375
npc.x, npc.y = 450, 318
coffee.x, coffee.y = 450, 435
play_mode.player.sprite.set_facing('up')
assert play_mode._nearest_interactable() is coffee
play_mode.player.sprite.set_facing('down')
assert play_mode._nearest_interactable() is npc
play_mode.finish()
print('PASS: study furniture edges, E pickup, E safe input, facing preference')

# Starting in the foyer, holding Down reaches the exit without a jewel.
import game_framework
import result_mode

game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
play_mode.player.keys.add(sdl.SDLK_s)
for _ in range(60):
    if game_framework.current_mode is result_mode:
        break
    play_mode.update()
assert game_framework.current_mode is result_mode
assert result_mode.withdrawal_ending and not result_mode.victory
assert '이럴 용기' in result_mode.reason
result_mode.draw()

# Retry starts a fresh game, and exiting with a jewel still wins.
result_mode.get_events = lambda: [SimpleNamespace(type=lib.SDL_KEYDOWN, key=sdl.SDLK_r)]
result_mode.handle_events()
play_mode.dialogue.pages = []
assert game_framework.current_mode is play_mode and play_mode.stage.current_room == 'foyer'
assert play_mode.player.pickup('jewel')
play_mode.stage.jewel_taken = True
play_mode.player.keys.add(sdl.SDLK_s)
for _ in range(60):
    if game_framework.current_mode is result_mode:
        break
    play_mode.update()
assert game_framework.current_mode is result_mode
assert result_mode.victory and not result_mode.withdrawal_ending
print('PASS: withdrawal ending, retry, and jewel exit')

# Distinguish walkable floor near furniture from the solid footprints.
for room_name, walkable, solid in (
    ('banquet', ((765, 225), (615, 405)), ((765, 316), (765, 373))),
    ('vault', ((1402, 843), (1368, 740)), ((1402, 887), (1445, 882), (1406, 737))),
    ('kitchen', ((1180, 402), (1265, 293)), ((1178, 449), (1265, 337))),
    ('study', ((214, 735), (289, 735)), ((250, 737), (250, 788))),
    ('foyer', ((77, 196),), ((97, 176),)),
):
    stage.current_room = room_name
    for point in walkable:
        assert stage.can_move(*stage.room.point(*point)), (room_name, point)
    for point in solid:
        assert not stage.can_move(*stage.room.point(*point)), (room_name, point)

# The corridor rug is walkable, but its side wall still stops the player.
stage.current_room = 'hall'
assert stage.can_move(*stage.room.point(750, 780))
assert not stage.can_move(*stage.room.point(504, 850))
print('PASS: furniture footprints, open floor, and corridor wall')

# Cooldown ticks through the play loop and the same NPC can notice again.
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
play_mode.stage.current_room = 'vault'
guard = play_mode.npcs[2]
# A controlled observer in the restricted room tests the cooldown independently
# of the expert's production placement in the study.
guard.move_to_room('vault', [(1174, 760)])
assert play_mode.stage.can_move(guard.x, guard.y)
play_mode.player.x, play_mode.player.y = guard.x, guard.y - 40
visible_to_guard = True
guard.can_see = lambda player: visible_to_guard
game_framework.frame_time = 0.5
play_mode.update()
assert play_mode.stage.suspicion == 1
for _ in range(4):
    play_mode.update()
assert play_mode.stage.suspicion == 1
play_mode.update()
assert play_mode.stage.suspicion == 2
visible_to_guard = False
for _ in range(5):
    play_mode.update()
assert play_mode.stage.suspicion == 2
visible_to_guard = True
play_mode.stage.security_disabled = True
play_mode.update()
assert play_mode.stage.suspicion == 2
assert play_mode.player.pickup('jewel')
play_mode.update()
assert game_framework.current_mode is result_mode
assert not result_mode.victory and not result_mode.withdrawal_ending
print('PASS: repeated witnessing, breaking line of sight, alarm bypass and jewel penalty')

# Pick up case files while holding an ordinary item. Investigations spend
# a charge once per room, freeze the reconstruction, and preserve its state.
from investigation import EVIDENCE
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
case = play_mode.investigation
assert play_mode.player.pickup('knife')
packet = case.files[0]
play_mode.player.x, play_mode.player.y = packet.x, packet.y
def press(key):
    while play_mode.dialogue.active:
        play_mode.dialogue.advance()
    play_mode.get_events = lambda: [SimpleNamespace(type=lib.SDL_KEYDOWN, key=key)]
    play_mode.handle_events()
press(sdl.SDLK_e)
assert case.charges == 1 and not packet.visible
press(ord('h'))
assert case.active and case.charges == 0
press(ord('h'))
assert not case.active
case.charges = 1
play_mode.stage.current_room = 'banquet'
play_mode.player.x, play_mode.player.y = ROOMS['banquet'].point(765, 425)
press(ord('h'))
assert case.active and case.charges == 0
position = play_mode.player.x, play_mode.player.y
npc_positions = [(n.x, n.y) for n in play_mode.npcs]
play_mode.stage.invulnerability_timer = 1.5
play_mode.player.keys.add(sdl.SDLK_w)
play_mode.update()
assert (play_mode.player.x, play_mode.player.y) == position
assert [(n.x, n.y) for n in play_mode.npcs] == npc_positions
assert play_mode.stage.invulnerability_timer == 1.5
assert play_mode.player.held_item == 'knife'
case.x, case.y = ROOMS['banquet'].point(*EVIDENCE['banquet'][1])
press(sdl.SDLK_e)
assert 'banquet' in case.notes
play_mode.draw()
press(ord('n'))
assert case.notebook
play_mode.draw()
press(sdl.SDLK_ESCAPE)
assert case.active and not case.notebook
press(ord('h'))
assert not case.active
assert not play_mode.player.keys
press(ord('h'))
assert case.charges == 0
press(ord('h'))
# Unlock another room and inspect every evidence marker at reachable coordinates.
play_mode.stage.current_room = 'hall'
play_mode.player.x, play_mode.player.y = ROOMS['hall'].point(750, 800)
press(ord('h'))
assert case.charges == 0 and not case.active
play_mode.stage.current_room = 'vault'
press(ord('h'))
assert not case.active and case.charges == 0
for room_name, (_, point, _) in EVIDENCE.items():
    play_mode.stage.current_room = room_name
    assert play_mode.stage.can_move(*ROOMS[room_name].point(*point)), room_name
    case.x, case.y = ROOMS[room_name].point(*point)
    case.inspect(room_name)
assert set(case.notes) == set(ROOMS)
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
assert play_mode.investigation.charges == 0
assert not play_mode.investigation.notes
assert all(f.visible for f in play_mode.investigation.files)
print('PASS: files, consumption, frozen reconstruction, notebook, all evidence and reset')

# Combining works in either order and consumes each ingredient once.
for first_index, second_index in ((2, 1), (1, 2)):
    game_framework.change_mode(play_mode)
    play_mode.dialogue.pages = []
    actor = play_mode.player
    first, second = play_mode.items[first_index], play_mode.items[second_index]
    for ingredient in (first, second):
        play_mode.stage.current_room = ingredient.room
        actor.x, actor.y = ingredient.x, ingredient.y
        assert play_mode._nearest_interactable() is ingredient
        press(sdl.SDLK_e)
    assert actor.held_item == 'sleeping_coffee'
    assert not first.visible and not second.visible
    actor.draw()
    press(sdl.SDLK_q)
    dropped = play_mode.items[-1]
    assert actor.held_item is None and dropped.item_name == 'sleeping_coffee'
    dropped.draw()
    press(sdl.SDLK_e)
    assert actor.held_item == 'sleeping_coffee' and not dropped.visible
    guard = play_mode.npcs[1]
    play_mode.stage.current_room = guard.room
    actor.x, actor.y = guard.x, guard.y
    press(sdl.SDLK_e)
    assert guard.sleeping and guard.visible and not guard.working
    assert play_mode.stage.athlete_unavailable and actor.held_item is None
    assert not guard.can_see(actor)
    guard.draw()
    actor.pickup('knife')
    press(sdl.SDLK_e)
    assert actor.held_item == 'knife'
    # Other preparations still gate the existing robbery outcome.
    play_mode.stage.security_disabled = True
    play_mode.stage.photographer_busy = True
    owner = play_mode.npcs[0]
    play_mode.stage.current_room = owner.room
    actor.x, actor.y = owner.x, owner.y
    press(sdl.SDLK_e)
    assert play_mode.stage.safe_open and play_mode.stage.robbery_triggered

# Neither ingredient alone nor protein disables the athlete.
for item in ('protein', 'sleeping_pills', 'coffee'):
    game_framework.change_mode(play_mode)
    play_mode.dialogue.pages = []
    actor = play_mode.player
    guard = play_mode.npcs[1]
    actor.pickup(item)
    play_mode.stage.current_room = guard.room
    actor.x, actor.y = guard.x, guard.y
    press(sdl.SDLK_e)
    assert actor.held_item == (None if item == 'coffee' else item) and guard.working
    assert not guard.sleeping and not play_mode.stage.athlete_unavailable
print('PASS: both ingredient orders, drop/recovery, sleep, robbery and invalid gifts')

# Scripted scenes use explicit advancement and pause reconstruction updates.
from dialogue import WELCOME, ATHLETE_SLEEP, ATHLETE_TESTIMONY, SECURITY
game_framework.change_mode(play_mode)
assert play_mode.dialogue.active
assert play_mode.dialogue.pages[0][0] == '김재현 (집주인)'
old = play_mode.player.x, play_mode.player.y
play_mode.player.keys.add(sdl.SDLK_d)
play_mode.update()
assert (play_mode.player.x, play_mode.player.y) == old
play_mode.draw()
play_mode.get_events = lambda: [SimpleNamespace(type=lib.SDL_KEYDOWN, key=sdl.SDLK_RETURN)]
while play_mode.dialogue.active:
    play_mode.handle_events()
assert not play_mode.player.keys
# Directing E to the expert opens a speaker-labelled conversation.
expert = play_mode.npcs[2]
play_mode.stage.current_room = expert.room
play_mode.player.x, play_mode.player.y = expert.x, expert.y
play_mode.get_events = lambda: [SimpleNamespace(type=lib.SDL_KEYDOWN, key=sdl.SDLK_e)]
play_mode.handle_events()
assert play_mode.dialogue.active and play_mode.stage.security_disabled
assert any('밖에' in ' '.join(lines) for _, lines in play_mode.dialogue.pages)
play_mode.dialogue.pages = []
# Coffee remains obtainable even if the ordinary serving has been consumed.
chef = play_mode.npcs[3]
play_mode.stage.current_room = chef.room
play_mode.player.x, play_mode.player.y = chef.x, chef.y
play_mode.handle_events()
assert play_mode.player.held_item == 'coffee'
assert play_mode.dialogue.active
print('PASS: greeting, paused dialogue, expert script and coffee refill')

# Surface items have accessible pickup spots distinct from their display spots.
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
expert = play_mode.npcs[2]
assert expert.room == 'study'
play_mode.stage.current_room = 'study'
assert all(play_mode.stage.can_move(*point) for point in expert.path)
for index in (0, 1, 2):
    obj = play_mode.items[index]
    play_mode.stage.current_room = obj.room
    assert obj.display_position is not None
    assert play_mode.stage.can_move(obj.x, obj.y)
    play_mode.player.x, play_mode.player.y = obj.x, obj.y
    assert play_mode._nearest_interactable() is obj
assert set(EVIDENCE) == set(ROOMS)
from investigation import Investigation
for room_name, (_, point, _) in EVIDENCE.items():
    case = Investigation()
    play_mode.investigation = case
    play_mode.stage.current_room = room_name
    play_mode.player.x, play_mode.player.y = ROOMS[room_name].point(*point)
    # No free first inspection; every room follows the same resource rule.
    press(ord('h'))
    assert not case.active and case.charges == 0
    case.charges = 1
    press(ord('h'))
    assert case.active and case.charges == 0
    press(sdl.SDLK_e)
    assert room_name in case.notes
    play_mode.draw()
    press(ord('n'))
    assert case.notebook
    play_mode.draw()
    press(sdl.SDLK_ESCAPE)
    press(ord('h'))
    assert not case.active
    press(ord('h'))
    assert case.active and case.charges == 0
    press(ord('h'))
# Photographer checks equipment instead of taking pictures in another room.
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
photographer = play_mode.npcs[4]
play_mode.stage.current_room = photographer.room
play_mode.player.x, play_mode.player.y = photographer.x, photographer.y
press(sdl.SDLK_e)
assert photographer.room == 'study' and play_mode.stage.photographer_busy
assert play_mode.dialogue.active
assert any('장비' in ' '.join(lines) for _, lines in play_mode.dialogue.pages)
play_mode.dialogue.pages = []
# The table itself blocks, the new south/north approach lanes stay open.
play_mode.stage.current_room = 'banquet'
for point in ((770, 220), (770, 427), (585, 298), (992, 298)):
    assert play_mode.stage.can_move(*ROOMS['banquet'].point(*point)), point
print('PASS: study expert, surface pickup points, six room clues, charge/revisit rules, equipment dialogue and dining lanes')

assert not any(obj.room == 'foyer' for obj in play_mode.items)
print('PASS: no loose item bottles in the foyer')

# Title settings flow into the new run and retry uses the same selection.
import game_settings
game_framework.change_mode(title_mode)
def title_key(key):
    title_mode.get_events = lambda: [SimpleNamespace(type=lib.SDL_KEYDOWN, key=key)]
    title_mode.handle_events()
assert game_settings.difficulty == 'normal'
title_key(sdl.SDLK_RIGHT)
assert game_settings.difficulty == 'hard' and game_settings.preparation_seconds == 60
title_key(sdl.SDLK_DOWN)
title_key(sdl.SDLK_LEFT)
assert game_settings.preparation_seconds == 45
for _ in range(40):
    title_key(sdl.SDLK_LEFT)
assert game_settings.preparation_seconds == 30
for _ in range(40):
    title_key(sdl.SDLK_RIGHT)
assert game_settings.preparation_seconds == 300
title_key(sdl.SDLK_UP)
title_key(sdl.SDLK_LEFT)
assert game_settings.difficulty == 'normal' and game_settings.preparation_seconds == 180
game_settings.select_difficulty('hard')
game_settings.adjust_time(-1)
game_framework.change_mode(play_mode)
assert play_mode.stage.preparation_remaining == 45
assert play_mode.stage.difficulty == 'hard'
play_mode.update()
assert play_mode.stage.preparation_remaining == 45  # Welcome scene pauses.
play_mode.dialogue.pages = []
game_framework.frame_time = 0.5
play_mode.update()
assert play_mode.stage.preparation_remaining == 44.5
play_mode.investigation.notebook = True
play_mode.update()
assert play_mode.stage.preparation_remaining == 44.5
play_mode.investigation.notebook = False
play_mode.stage.preparation_remaining = 0.25
play_mode.update()
assert not play_mode.stage.can_prepare and play_mode.stage.preparation_remaining == 0
expert = play_mode.npcs[2]
play_mode.stage.current_room = expert.room
play_mode.player.x, play_mode.player.y = expert.x, expert.y
press(sdl.SDLK_e)
assert not play_mode.stage.security_disabled
play_mode.dialogue.pages = []
# The code route still opens the safe after the preparation timeout.
play_mode.stage.current_room = 'vault'
safe = play_mode.props[0]
play_mode.player.x, play_mode.player.y = safe.x, safe.y
press(sdl.SDLK_e)
for key in [*map(ord, '1125'), sdl.SDLK_RETURN]:
    play_mode._handle_safe_input(SimpleNamespace(type=lib.SDL_KEYDOWN, key=key))
assert play_mode.stage.safe_open
game_framework.change_mode(play_mode)
assert play_mode.stage.preparation_remaining == 45 and play_mode.stage.can_prepare
play_mode.dialogue.pages = []
play_mode.stage.finish_preparation()
play_mode.update()
assert play_mode.stage.preparation_remaining == 45
game_settings.select_difficulty('normal')
print('PASS: difficulty UI, custom times, limits, pause, expiration, code route and reset')

# Dropping an already obtained tool after timeout must not destroy access to it.
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
play_mode.stage.finish_preparation()
play_mode.player.pickup('knife')
press(sdl.SDLK_q)
assert play_mode.items[-1].dropped
press(sdl.SDLK_e)
assert play_mode.player.held_item == 'knife'
print('PASS: previously obtained tools can be dropped and recovered after preparation')

# Robbery escape starts on actual jewel pickup, not just safe opening.
from pursuit import Pursuit, path_to, clear_segment, walkable
from math import hypot

def ready_robbery():
    game_framework.change_mode(play_mode)
    play_mode.dialogue.pages = []
    owner = play_mode.npcs[0]
    assert owner.room == 'vault'
    assert all(walkable('vault', *point) for point in owner.path)
    play_mode.stage.athlete_unavailable = True
    play_mode.stage.security_disabled = True
    photographer = play_mode.npcs[4]
    play_mode._interact_npc(photographer)
    play_mode.dialogue.pages = []
    play_mode.player.pickup('knife')
    play_mode.stage.current_room = owner.room
    play_mode.player.x, play_mode.player.y = owner.x, owner.y
    press(sdl.SDLK_e)
    assert play_mode.stage.safe_open and not play_mode.pursuit.active
    safe = play_mode.props[0]
    play_mode.player.x, play_mode.player.y = safe.x, safe.y
    press(sdl.SDLK_e)
    assert play_mode.player.held_item == 'jewel'
    assert play_mode.pursuit.active
    assert {n.character for n in play_mode.pursuit.pursuers} == {'it_expert', 'planner', 'photographer'}
    return play_mode.pursuit

chase = ready_robbery()
assert chase.delay == 1.5
positions = [(n.room, n.x, n.y) for n in chase.pursuers]
# Ordinary NPC updates must not also move pursuers along their old patrol.
for n in chase.pursuers:
    n.update(0.5)
assert positions == [(n.room, n.x, n.y) for n in chase.pursuers]
play_mode.investigation.notebook = True
play_mode.update()
assert chase.delay == 1.5
play_mode.investigation.notebook = False
play_mode._speak((('상황', '잠시 정지'),))
play_mode.update()
assert chase.delay == 1.5
play_mode.dialogue.pages = []
# Dropping the jewel never cancels pursuit or restarts the reaction timer.
press(sdl.SDLK_q)
assert chase.active
press(sdl.SDLK_e)
assert chase.delay == 1.5

# Each study NPC follows doors all the way to the foyer, never through furniture.
for character in ('it_expert', 'planner', 'photographer'):
    chase = ready_robbery()
    npc = next(n for n in chase.pursuers if n.character == character)
    chase.pursuers = [npc]
    play_mode.stage.current_room = 'foyer'
    actor = play_mode.player
    actor.x, actor.y = ROOMS['foyer'].point(233, 357)
    visited = {npc.room}
    caught = None
    for _ in range(600):
        before = npc.room, npc.x, npc.y
        caught = chase.update(0.05, play_mode.stage, actor)
        visited.add(npc.room)
        assert walkable(npc.room, npc.x, npc.y), (character, npc.room, npc.x, npc.y)
        if before[0] == npc.room:
            assert clear_segment(npc.room, before[1:], (npc.x, npc.y))
        if caught:
            break
    assert caught is npc, (character, npc.room, visited)
    assert visited == {'study', 'hall', 'banquet', 'foyer'}, visited

# A route around the banquet table contains collision-free bends.
room = ROOMS['banquet']
a, b = room.point(600, 290), room.point(940, 290)
route = path_to('banquet', a, b)
assert route and len(route) > 1
for destination in route:
    assert clear_segment('banquet', a, destination)
    a = destination

# Capturing switches to failure; a legitimate exit still produces detective speech.
chase = ready_robbery()
chase.delay = 0
captor = chase.pursuers[0]
play_mode.stage.current_room = captor.room
play_mode.player.x, play_mode.player.y = captor.x, captor.y
play_mode.update()
assert game_framework.current_mode is result_mode and not result_mode.victory
assert '붙잡혔습니다' in result_mode.reason
result_mode.draw()
chase = ready_robbery()
play_mode.stage.current_room = 'foyer'
play_mode.player.x, play_mode.player.y = ROOMS['foyer'].point(233, 440)
play_mode.stage.exit_attempted = True
play_mode.update()
assert result_mode.victory and '진행되었을 것입니다' in result_mode.reason
result_mode.draw()
# Retry and the code route keep study actors on their normal schedules.
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
assert not play_mode.pursuit.active and not any(n.pursuing for n in play_mode.npcs)
play_mode.stage.current_room = 'vault'
play_mode.entered_code = '1125'
play_mode.input_code_mode = True
play_mode._handle_safe_input(SimpleNamespace(type=lib.SDL_KEYDOWN, key=sdl.SDLK_RETURN))
safe = play_mode.props[0]
play_mode.player.x, play_mode.player.y = safe.x, safe.y
press(sdl.SDLK_e)
assert play_mode.player.held_item == 'jewel' and not play_mode.pursuit.active
assert not any(n.pursuing for n in play_mode.npcs)
print('PASS: vault owner, jewel-triggered pursuit, pause, collision-safe multi-room chase, capture, endings and quiet code route')
