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
    def clip_composite_draw(self, *args): self.drawn.append(('composite',args))
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
sdl.SDL_MOUSEBUTTONDOWN = 1001
sdl.SDL_MOUSEMOTION = 1002
sdl.SDL_BUTTON_LEFT = 1
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
guard.set_patrol([])
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
assert expert.room == 'security_room'
play_mode.stage.current_room = expert.room
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
print('PASS: distributed expert, surface pickups, all-room clues and equipment dialogue')

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
    assert 'foyer' in visited and len(visited) >= 2, visited

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
assert result_mode.victory and '현관으로 빠져나갔을 겁니다.' in result_mode.reason
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

# Expanded room graph has a real kitchen/study loop and reciprocal walkable doors.
from pursuit import next_door
assert len(ROOMS) == 9
assert next_door('kitchen', 'study').target == 'service'
assert next_door('hall', 'vault').target == 'security_lobby'
for room_name, room in ROOMS.items():
    for door in room.doors:
        if door.target not in ROOMS:
            continue
        assert any(d.target == room_name for d in ROOMS[door.target].doors)
        x, y = room.point(*door.point)
        approach = x - door.direction[0] * 20, y - door.direction[1] * 20
        assert walkable(room_name, *approach), (room_name, door.label)
        assert walkable(door.target, *ROOMS[door.target].point(*door.arrival))
        # Every usable door is connected to every other exit in that room.
        for other in room.doors:
            ox, oy = room.point(*other.point)
            endpoint = ox - other.direction[0] * 20, oy - other.direction[1] * 20
            assert path_to(room_name, approach, endpoint), (room_name, door.label, other.label)

# All scheduled NPCs actually reach their rooms, pause, and remain on walkable floor.
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
for npc in play_mode.npcs[1:]:
    visited, paused = {npc.room}, False
    for _ in range(1800):
        before = npc.room, npc.x, npc.y
        npc.update(0.05)
        visited.add(npc.room)
        paused |= npc.patrol_wait > 0
        assert walkable(npc.room, npc.x, npc.y), (npc.character, npc.room, npc.x, npc.y)
        if before[0] == npc.room:
            assert clear_segment(npc.room, before[1:], (npc.x, npc.y))
    assert {stop[0] for stop in npc.patrol} <= visited, (npc.character, visited)
    assert paused, npc.character

# Camera warning, repeated detection, public access, blindness behind furniture.
from surveillance import Surveillance, sight_clear, WARNING_SECONDS
from math import atan2
s = Stage(current_room='hall')
actor = Player(s)
actor.x, actor.y = ROOMS['hall'].point(840, 820)
actor.held_item = 'knife'
monitor = Surveillance()
camera = monitor.cameras[0]
camera.sweep = 0
camera.base_angle = atan2(actor.y - camera.y, actor.x - camera.x)
assert camera.sees(actor)
monitor.update(0.5, s, actor)
assert s.suspicion == 0 and camera.exposure == 0.5
monitor.update(0.5, s, actor)
assert s.suspicion == 1
s.update(2.5)
monitor.update(0.01, s, actor)
assert s.suspicion == 2
# Ordinary guests under the corridor camera incur no suspicion.
actor.held_item = None
monitor.update(2, s, actor)
assert s.suspicion == 2 and camera.exposure == 0
# Brief exposure can be escaped before it produces any penalty.
actor.held_item = 'knife'
s.invulnerability_timer = 0
monitor.update(0.5, s, actor)
camera.base_angle += 3.14
monitor.update(0.1, s, actor)
assert camera.exposure == 0 and s.suspicion == 2
# The central lobby pillar is both cover and a collision obstacle.
room = ROOMS['security_lobby']
assert not sight_clear('security_lobby', room.point(735, 245), room.point(220, 245))
assert sight_clear('security_lobby', room.point(735, 340), room.point(220, 340))
# Restricted-area detection does not depend on knife/jewel or alarm bypass.
s.current_room = 'security_lobby'
s.security_disabled = True
actor.held_item = None
actor.x, actor.y = room.point(620, 160)
camera = monitor.cameras[1]
camera.sweep = 0
camera.base_angle = atan2(actor.y - camera.y, actor.x - camera.x)
s.invulnerability_timer = 0
monitor.update(1, s, actor)
assert s.suspicion == 3
monitor.disable()
remaining = monitor.disabled_remaining
monitor.update(2, s, actor)
assert s.suspicion == 3 and monitor.disabled_remaining == remaining - 2
assert all(c.exposure == 0 for c in monitor.cameras)

# Expert only bypasses the alarm; the separate console stops cameras temporarily.
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
expert = play_mode.npcs[2]
play_mode._interact_npc(expert)
assert play_mode.stage.security_disabled and play_mode.surveillance.disabled_remaining == 0
play_mode.dialogue.pages = []
console = next(p for p in play_mode.props if p.name == 'camera_console')
play_mode.stage.current_room = console.room
play_mode.player.x, play_mode.player.y = console.x, console.y
press(sdl.SDLK_e)
assert play_mode.surveillance.disabled_remaining == 45
# Notebook/aftermath/dialogue pause camera movement and shutdown timer alike.
play_mode.investigation.notebook = True
old_angle = play_mode.surveillance.cameras[0].angle
play_mode.update()
assert play_mode.surveillance.disabled_remaining == 45
assert play_mode.surveillance.cameras[0].angle == old_angle
play_mode.investigation.notebook = False
play_mode.stage.finish_preparation()
play_mode.surveillance.disabled_remaining = 0
press(sdl.SDLK_e)
assert play_mode.surveillance.disabled_remaining == 0

# Photographer returns to their normal route after the diversion expires.
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
play_mode._interact_npc(play_mode.npcs[4])
assert play_mode.stage.photographer_busy
play_mode.dialogue.pages = []
play_mode.stage.photographer_remaining = 0.1
game_framework.frame_time = 0.2
play_mode.update()
assert not play_mode.stage.photographer_busy
assert play_mode.npcs[4].patrol and play_mode.npcs[4].patrol[0][0] == 'banquet'
for name in ROOMS:
    play_mode.stage.current_room = name
    play_mode.draw()
# Restart clears camera alert, shutdown timer and new NPC states.
game_framework.change_mode(play_mode)
assert play_mode.surveillance.disabled_remaining == 0
assert all(c.exposure == 0 for c in play_mode.surveillance.cameras)
print('PASS: nine-room loop, reciprocal doors, multi-room patrols, camera warning/occlusion/cooldown, independent console, pause and reset')

# LEC18 BT semantics: reactive priority, interruption and per-NPC blackboards.
import py_trees
from py_trees.common import Status

game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
expert, planner = play_mode.npcs[2], play_mode.npcs[5]
assert isinstance(expert.bt, py_trees.trees.BehaviourTree)
assert not expert.bt.root.memory
assert next(n for n in expert.bt.root.iterate() if n.name == 'Patrol').memory
assert not next(n for n in expert.bt.root.iterate() if n.name == 'Chase').memory
# Start a long patrol segment, then interrupt it before reaching its destination.
expert.set_patrol([('security_lobby', (620, 340), 2), ('security_room', (720, 220), 2)])
expert.update(0.1)
index = expert.patrol_index
assert index == 0
original_destination = expert.brain.blackboard.target
planner.update(0.1)
planner_destination = planner.brain.blackboard.target
assert expert.brain.namespace != planner.brain.namespace
assert 'Move To Patrol Location' in expert.brain.snapshot()
# A normal/code-route run cannot enable Chase even if the player is nearby.
play_mode.stage.current_room = expert.room
play_mode.player.x, play_mode.player.y = expert.x, expert.y
assert not play_mode.pursuit.start(play_mode.stage, play_mode.npcs)
assert not expert.pursuing
play_mode.stage.robbery_triggered = True
assert play_mode.pursuit.start(play_mode.stage, play_mode.npcs)
play_mode.pursuit.delay = 0
play_mode.pursuit.pursuers = [expert]
play_mode.stage.current_room = 'hall'
play_mode.player.x, play_mode.player.y = ROOMS['hall'].point(840, 820)
play_mode.pursuit.update(0.05, play_mode.stage, play_mode.player)
assert next(n for n in expert.bt.root.iterate() if n.name == 'Chase').status == Status.RUNNING
assert expert.patrol_index == index
assert planner.brain.blackboard.target == planner_destination
# A disabled/sleeping actor preempts Chase without moving or catching anyone.
expert.sleeping = True
before = expert.room, expert.x, expert.y
assert play_mode.pursuit.update(0.2, play_mode.stage, play_mode.player) is None
assert (expert.room, expert.x, expert.y) == before
assert next(n for n in expert.bt.root.iterate() if n.name == 'Unavailable').status == Status.SUCCESS
# Chase condition is checked again immediately; patrol resumes the same stop.
expert.sleeping = False
expert.pursuing = False
play_mode.pursuit.active = False
expert.update(0.05)
assert expert.patrol_index == index
assert expert.brain.blackboard.target == original_destination
assert next(n for n in expert.bt.root.iterate() if n.name == 'Patrol').status == Status.RUNNING
# Index is advanced only after reaching the intended stop and looking around.
for _ in range(1200):
    expert.update(0.05)
    if expert.patrol_index != index:
        break
assert expert.patrol_index == 1
assert expert.room == 'security_lobby'
assert hypot(expert.x - original_destination[0], expert.y - original_destination[1]) < 3
# Reset/mode change unregisters AI targets rather than leaving stale global state.
namespace = expert.brain.namespace
play_mode.finish()
assert not any(key.startswith(namespace + '/') for key in py_trees.blackboard.Blackboard.storage)
print('PASS: py_trees priorities, memory settings, isolated blackboards, sleep interruption, patrol resume and cleanup')

# The quiet route's date can be inferred from ordinary records, without H charges.
import re
from investigation import PUZZLE_RECORDS, SceneRecord

game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
case = play_mode.investigation
assert case.charges == 0 and not case.records
actor = play_mode.player
actor.pickup('coffee')
for document in case.documents:
    play_mode.stage.current_room = document.room
    actor.x, actor.y = document.x, document.y
    assert walkable(document.room, document.x, document.y)
    assert play_mode._nearest_interactable() is document
    assert '[E]' in play_mode._interaction_hint(document)
    press(sdl.SDLK_e)
    assert document.record_id in case.records
    assert actor.held_item == 'coffee' and case.charges == 0
    assert document.visible and play_mode.dialogue.active
    remaining = play_mode.stage.preparation_remaining
    play_mode.update()
    assert play_mode.stage.preparation_remaining == remaining
    play_mode.draw()
    while play_mode.dialogue.active:
        play_mode.dialogue.advance()
    count = len(case.records)
    press(sdl.SDLK_e)
    assert len(case.records) == count
    while play_mode.dialogue.active:
        play_mode.dialogue.advance()
# A conversation no longer gives either the full date or its safe-code relation.
play_mode._interact_npc(play_mode.npcs[5])
spoken = ' '.join(' '.join(lines) for _, lines in play_mode.dialogue.pages)
assert '개관' in spoken and '금고' not in spoken
assert not re.search(r'\d', spoken)
play_mode.dialogue.pages = []
# Ordinary records and H findings coexist; neither overwrites the other.
case.notes['foyer'] = ('시험 흔적', ('기록', '유지'))
assert len(case.notebook_entries()) == len(case.documents) + 1
press(ord('n'))
assert case.notebook
for page in range(len(case.notebook_entries())):
    case.note_page = page
    play_mode.draw()
press(sdl.SDLK_ESCAPE)
assert not case.notebook
# Safe inspection records the inscription and shows month/day entry, without spending H.
actor.drop()
play_mode.stage.current_room = 'vault'
safe = play_mode.props[0]
actor.x, actor.y = safe.x, safe.y
press(sdl.SDLK_e)
assert play_mode.input_code_mode and 'opening_plaque' in case.records
assert case.charges == 0
while play_mode.dialogue.active:
    play_mode.dialogue.advance()
play_mode.draw()
press(sdl.SDLK_ESCAPE)
press(ord('n'))
assert case.notebook and len(case.notebook_entries()) == len(case.documents) + 2
press(sdl.SDLK_ESCAPE)
# Derive month and day independently rather than obtain a complete answer from one NPC.
month_lines = ' '.join(case.records['event_month'][2])
day_lines = ' '.join(case.records['entry_day'][2])
assert '저택 개관 행사 · 표식: 월계수' in month_lines and '저택 개관 행사 · 표식: 월계수' in day_lines
code = re.search(r'(\d+)월', month_lines).group(1).zfill(2) + re.search(r'(\d+)일', day_lines).group(1).zfill(2)
assert code == play_mode.DEMO_SAFE_CODE
press(sdl.SDLK_e)
assert play_mode.input_code_mode and not play_mode.dialogue.active
for key in [*map(ord, '0000'), sdl.SDLK_RETURN]:
    press(key)
assert not play_mode.stage.safe_open
press(sdl.SDLK_e)
for key in [*map(ord, code), sdl.SDLK_RETURN]:
    press(key)
assert play_mode.stage.safe_open and not play_mode.stage.robbery_triggered
press(sdl.SDLK_e)
assert actor.held_item == 'jewel' and not play_mode.pursuit.active
# Finish the code route and ensure the same ending and reset contracts remain.
play_mode.stage.current_room = 'foyer'
actor.x, actor.y = ROOMS['foyer'].point(233, 440)
play_mode.stage.exit_attempted = True
play_mode.update()
assert result_mode.victory
assert '사람들의 눈을 피해' in result_mode.reason
# Retry resets ordinary records, H notes and paper visibility together.
game_framework.change_mode(play_mode)
assert not play_mode.investigation.records and not play_mode.investigation.notes
assert all(d.visible for d in play_mode.investigation.documents)
# Reading papers after preparation expires remains possible and doesn't reopen preparation.
play_mode.dialogue.pages = []
play_mode.stage.finish_preparation()
document = play_mode.investigation.documents[0]
play_mode.stage.current_room = document.room
play_mode.player.x, play_mode.player.y = document.x, document.y
press(sdl.SDLK_e)
assert document.record_id in play_mode.investigation.records
assert not play_mode.stage.can_prepare
print('PASS: separate E records, free/repeatable reading, notebook coexistence, inscription, inferred date, manual safe input, code ending and reset')

# Mouse keypad and keyboard share one safe input path; SDL y is top-origin.
from safe_keypad import BUTTONS, button_at
from rooms import SCREEN_H
for action, (left, bottom, right, top) in BUTTONS.items():
    assert button_at((left + right) / 2, (bottom + top) / 2) == action
    assert button_at(left, bottom) == action
    assert button_at(right, top) == action
assert button_at(10, 10) is None

def open_keypad():
    play_mode.stage.current_room = 'vault'
    safe = play_mode.props[0]
    play_mode.player.x, play_mode.player.y = safe.x, safe.y
    press(sdl.SDLK_e)
    while play_mode.dialogue.active:
        play_mode.dialogue.advance()
    assert play_mode.input_code_mode

def click_key(action, button=1, event_type=None):
    left, bottom, right, top = BUTTONS[action]
    event = SimpleNamespace(type=sdl.SDL_MOUSEBUTTONDOWN if event_type is None else event_type,
                            button=button, x=int((left + right) / 2),
                            y=SCREEN_H - 1 - int((bottom + top) / 2))
    play_mode.get_events = lambda: [event]
    play_mode.handle_events()

game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
open_keypad()
click_key('1', button=3)
assert play_mode.entered_code == ''
click_key('1', event_type=sdl.SDL_MOUSEMOTION)
assert play_mode.hovered_safe_key == '1' and play_mode.entered_code == ''
click_key('delete')
click_key('confirm')
assert play_mode.input_code_mode and not play_mode.stage.safe_open
assert play_mode.safe_feedback
click_key('1')
press(ord('1'))
click_key('2')
press(ord('5'))
click_key('9')
assert play_mode.entered_code == '1125'
remaining = play_mode.stage.preparation_remaining
npc_positions = [(n.room, n.x, n.y) for n in play_mode.npcs]
play_mode.update()
assert remaining == play_mode.stage.preparation_remaining
assert npc_positions == [(n.room, n.x, n.y) for n in play_mode.npcs]
play_mode.draw()
click_key('confirm')
assert play_mode.stage.safe_open and not play_mode.input_code_mode
assert not play_mode.pursuit.active
# An incorrect attempt stays open, clears digits and offers another attempt.
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
open_keypad()
for digit in '0000':
    click_key(digit)
click_key('confirm')
assert play_mode.input_code_mode and not play_mode.stage.safe_open
assert play_mode.entered_code == '' and play_mode.safe_feedback
play_mode.draw()
click_key('7')
assert not play_mode.safe_feedback
click_key('delete')
assert play_mode.entered_code == ''
click_key('8')
press(sdl.SDLK_BACKSPACE)
assert play_mode.entered_code == ''
# Background clicks do not leak to world interaction or close the modal.
play_mode.get_events = lambda: [SimpleNamespace(type=sdl.SDL_MOUSEBUTTONDOWN, button=1, x=10, y=10)]
play_mode.handle_events()
assert play_mode.input_code_mode and play_mode.entered_code == ''
click_key('2')
click_key('close')
assert not play_mode.input_code_mode and play_mode.entered_code == ''
open_keypad()
assert play_mode.entered_code == '' and not play_mode.safe_feedback
for digit in '1125':
    click_key(digit)
press(sdl.SDLK_RETURN)
assert play_mode.stage.safe_open and not play_mode.input_code_mode
print('PASS: keypad geometry, SDL mouse coordinates, hover, mixed input, length cap, retry, delete, cancel and paused world')


# Service passage portals must not bounce a player back while a direction is held.
# Test real Player.update movement, not just walkable endpoints or graph links.
for source, start, key, destination in (
        ('kitchen', (1135, 350), sdl.SDLK_a, 'service'),
        ('service', (750, 245), sdl.SDLK_d, 'kitchen'),
        ('study', (416, 840), sdl.SDLK_d, 'service'),
        ('service', (50, 245), sdl.SDLK_a, 'study')):
    portal_stage = Stage(current_room=source, service_discovered=True)
    walker = Player(portal_stage)
    walker.x, walker.y = ROOMS[source].point(*start)
    walker.keys.add(key)
    transitions = []
    previous_room = source
    for _ in range(12):
        walker.update(0.05)
        assert portal_stage.can_move(walker.x, walker.y)
        if portal_stage.current_room != previous_room:
            transitions.append(portal_stage.current_room)
            previous_room = portal_stage.current_room
    assert transitions == [destination], (source, key, transitions)
    assert portal_stage.current_room == destination
print('PASS: held-key kitchen/service/study crossings in both directions without bounce-back')

# The staff route must be discovered, not entered by silently walking into a wall.
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
assert not play_mode.stage.service_discovered
play_mode.stage.current_room = 'kitchen'
actor = play_mode.player
actor.x, actor.y = ROOMS['kitchen'].point(1135, 350)
actor.keys.add(sdl.SDLK_a)
for _ in range(12):
    actor.update(0.05)
assert play_mode.stage.current_room == 'kitchen'
actor.keys.clear()
# Captions reveal a work door, not its destination, until it has been investigated.
captions = []
original_text = play_mode.text
play_mode.text = lambda x, y, value, *args: captions.append(value)
play_mode.draw()
assert '작업용 문' in captions and '사용인 복도' not in captions
play_mode.text = original_text
# Door investigation itself is a valid discovery clue; no consumable is required.
actor.x, actor.y = ROOMS['kitchen'].point(1125, 350)
assert play_mode._nearest_interactable().name == 'work_door_kitchen'
press(sdl.SDLK_e)
assert play_mode.stage.service_discovered and play_mode.investigation.charges == 0
assert play_mode.dialogue.active
while play_mode.dialogue.active:
    play_mode.dialogue.advance()
actor.keys.add(sdl.SDLK_a)
for _ in range(12):
    actor.update(0.05)
assert play_mode.stage.current_room == 'service'
actor.keys.clear()
# The delivery memo is outside the passage and independently unlocks knowledge.
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
case = play_mode.investigation
memo = next(d for d in case.documents if d.record_id == 'delivery_memo')
assert memo.room == 'kitchen'
play_mode.stage.current_room = memo.room
play_mode.player.x, play_mode.player.y = memo.x, memo.y
assert play_mode._nearest_interactable() is memo
press(sdl.SDLK_e)
assert play_mode.stage.service_discovered and 'delivery_memo' in case.records
assert case.charges == 0
while play_mode.dialogue.active:
    play_mode.dialogue.advance()
captions = []
play_mode.text = lambda x, y, value, *args: captions.append(value)
play_mode.draw()
assert '사용인 복도' in captions
play_mode.text = original_text
# Shelves prevent a straight run and provide genuine camera occlusion.
room = ROOMS['service']
a, b = room.point(750, 245), room.point(50, 245)
assert not clear_segment('service', a, b)
route = path_to('service', a, b)
assert route and len(route) > 1
for point in route:
    assert clear_segment('service', a, point)
    a = point
monitor = Surveillance()
camera = next(c for c in monitor.cameras if c.room == 'service')
s = Stage(current_room='service', service_discovered=True)
actor = Player(s)
actor.x, actor.y = room.point(400, 245)
camera.sweep = 0
camera.base_angle = atan2(actor.y - camera.y, actor.x - camera.x)
assert actor.held_item is None and camera.sees(actor)
monitor.update(1.0, s, actor)
assert s.suspicion == 1  # The staff-only corridor is monitored even without a tool.
actor.x, actor.y = room.point(450, 310)
assert walkable('service', actor.x, actor.y)
assert not sight_clear('service', (camera.x, camera.y), (actor.x, actor.y))
monitor.update(0.1, s, actor)
assert camera.exposure == 0 and s.suspicion == 1
monitor.disable()
actor.x, actor.y = room.point(400, 245)
s.invulnerability_timer = 0
monitor.update(1.0, s, actor)
assert s.suspicion == 1 and monitor.disabled_remaining == 44.0
# NPCs know the staff route and can pursue through it before player discovery.
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
expert = play_mode.npcs[2]
expert.move_to_room('kitchen', [(1135, 350)])
play_mode.stage.robbery_triggered = True
play_mode.stage.current_room = 'study'
actor = play_mode.player
actor.x, actor.y = ROOMS['study'].point(350, 840)
assert not play_mode.stage.service_discovered
chase = play_mode.pursuit
chase.start(play_mode.stage, play_mode.npcs)
chase.pursuers = [expert]
chase.delay = 0
visited = {expert.room}
for _ in range(600):
    caught = chase.update(0.05, play_mode.stage, actor)
    visited.add(expert.room)
    assert walkable(expert.room, expert.x, expert.y)
    if caught:
        break
assert caught is expert and {'service', 'study'} <= visited
assert not play_mode.stage.service_discovered
# Retry resets discovery while keeping both ways to discover the route available.
game_framework.change_mode(play_mode)
assert not play_mode.stage.service_discovered
assert any(d.record_id == 'delivery_memo' for d in play_mode.investigation.documents)
print('PASS: staff-door discovery, outside memo, closed boundary, shelf detour, camera cover/shutdown and undiscovered NPC pursuit')

# Use actual held movement across the entire banquet/kitchen doorway, not just its centre.
for source, destination, key in (('banquet', 'kitchen', sdl.SDLK_a),
                                  ('kitchen', 'banquet', sdl.SDLK_d)):
    room = ROOMS[source]
    door = next(d for d in room.doors if d.target == destination)
    assert door.span == 36
    left, bottom, right, top = door.opening_bounds(room)
    assert abs((top - bottom) / 2 - door.span * room.scale) < 0.001
    _, caption_y = door.caption_position(room)
    assert caption_y > top
    for offset in (-34, -26, -13, 0, 13, 26, 34):
        for dt in (0.01, 0.05):
            passage_stage = Stage(current_room=source)
            walker = Player(passage_stage)
            x, y = room.point(door.point[0], door.point[1] + offset)
            walker.x, walker.y = x - door.direction[0] * 44, y
            assert passage_stage.can_move(walker.x, walker.y)
            walker.keys.add(key)
            transitions = []
            previous_room = source
            for _ in range(round(0.65 / dt)):
                walker.update(dt)
                assert passage_stage.can_move(walker.x, walker.y)
                if passage_stage.current_room != previous_room:
                    transitions.append(passage_stage.current_room)
                    previous_room = passage_stage.current_room
            assert transitions == [destination], (source, offset, dt, transitions)
    # A wider trigger must still reject movement into the wall outside its frame.
    for offset in (-45, 45):
        passage_stage = Stage(current_room=source)
        walker = Player(passage_stage)
        x, y = room.point(door.point[0], door.point[1] + offset)
        walker.x, walker.y = x - door.direction[0] * 44, y
        walker.keys.add(key)
        for _ in range(15):
            walker.update(0.05)
        assert passage_stage.current_room == source
# Every connection has an explicit renderable frame in the same coordinate space.
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
for name, room in ROOMS.items():
    play_mode.stage.current_room = name
    for door in room.doors:
        left, bottom, right, top = door.opening_bounds(room)
        px, py = room.point(*door.point)
        assert left < px < right and bottom < py < top
    play_mode.draw()
print('PASS: full-width banquet/kitchen crossings at two frame rates, wall rejection, visible frames and non-overlapping captions')

# Existing painted passages must never receive an open-door overlay.
from sprite import ASSETS, image_for
from mansion_art import SPRITES, furniture_image, draw_extension
for name in SPRITES:
    texture = furniture_image(name)
    with Image.open(texture.src) as image:
        assert image.mode == 'RGBA'
        assert image.getchannel('A').getextrema() == (0, 255)
        assert sum(image.getchannel('A').histogram()[1:]) > image.width * image.height * .25
for discovered in (False, True):
    game_framework.change_mode(play_mode)
    play_mode.stage.service_discovered = discovered
    textures = [image_for(ASSETS / 'doors' / (name + '.png')) for name in ('front_open', 'side_open')]
    before = [len(t.drawn) for t in textures]
    for name in ROOMS:
        play_mode.stage.current_room = name
        play_mode.draw()
    assert [len(t.drawn) for t in textures] == before
    closed_image = image_for(ASSETS / 'doors' / 'side_closed.png')
    before = len(closed_image.drawn)
    play_mode.stage.current_room = 'kitchen'
    play_mode.draw()
    assert len(closed_image.drawn) == before + (0 if discovered else 1)
for name in ('service', 'security_lobby', 'security_room'):
    textures = [image_for(ASSETS / 'rooms' / (n + '.png')) for n in ('banquet', 'foyer', 'hall')]
    before = [len(t.drawn) for t in textures]
    draw_extension(ROOMS[name], name)
    for texture, count in zip(textures, before):
        assert all(args[-2] > 0 and args[-1] > 0 for _, args in texture.drawn[count:])
print('PASS: native passages have no open-door overlays, secret gate state, furniture masks and positive room texture sizes')
