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

assert len(play_mode.items)==4
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
protein = play_mode.items[2]
player.x, player.y = protein.x - 65, protein.y
player.sprite.set_facing('right')
assert play_mode._nearest_interactable() is protein
assert '프로틴' in play_mode._interaction_hint(protein)
press_e = SimpleNamespace(type=lib.SDL_KEYDOWN, key=sdl.SDLK_e)
play_mode.get_events = lambda: [press_e]
play_mode.handle_events()
assert player.held_item == 'protein' and not protein.visible

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
coffee = play_mode.items[3]
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
assert not case.active and case.charges == 1
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
assert len(case.notes) == 3
game_framework.change_mode(play_mode)
play_mode.dialogue.pages = []
assert play_mode.investigation.charges == 0
assert not play_mode.investigation.notes
assert all(f.visible for f in play_mode.investigation.files)
print('PASS: files, consumption, frozen reconstruction, notebook, all evidence and reset')

# Combining works in either order and consumes each ingredient once.
for first_index, second_index in ((3, 1), (1, 3)):
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
for index in (0, 1, 3):
    obj = play_mode.items[index]
    play_mode.stage.current_room = obj.room
    assert obj.display_position is not None
    assert play_mode.stage.can_move(obj.x, obj.y)
    play_mode.player.x, play_mode.player.y = obj.x, obj.y
    assert play_mode._nearest_interactable() is obj
assert len(EVIDENCE) == 3
case = play_mode.investigation
for room_name in ('foyer', 'kitchen', 'study'):
    case.charges = 1
    case.open_scene(room_name, play_mode.player)
    assert not case.active and case.charges == 1
# The table itself blocks, the new south/north approach lanes stay open.
play_mode.stage.current_room = 'banquet'
for point in ((770, 220), (770, 427), (585, 298), (992, 298)):
    assert play_mode.stage.can_move(*ROOMS['banquet'].point(*point)), point
print('PASS: study expert, surface pickup points, three clues and dining lanes')
