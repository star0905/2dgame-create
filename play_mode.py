"""Mansion case with a fixed camera for each room."""
from math import hypot
from pico2d import clear_canvas, update_canvas, get_events, draw_rectangle, SDL_KEYDOWN, SDL_QUIT
from sdl2 import SDLK_ESCAPE, SDLK_e, SDLK_q, SDLK_SPACE, SDLK_RETURN, SDLK_BACKSPACE
import game_world
import game_framework
from stage import Stage
from rooms import MansionMap, ROOMS
from player import Player
from npc import NPC
from item import WorldItem, FixedProp, ITEM_LABELS
from sprite import ASSETS, image_for
from ui import text

# Training/demo value only, not a canonically finalized puzzle answer.
DEMO_SAFE_CODE = '1125'
INTERACT_RANGE = 74
FACING_VECTORS = {'up': (0, 1), 'down': (0, -1), 'left': (-1, 0), 'right': (1, 0)}


def init():
    global stage, player, npcs, items, props, message, input_code_mode, entered_code, msg_timer
    global notice_text, notice_timer
    game_world.clear()
    stage = Stage()
    game_world.add_object(MansionMap(stage), 0)
    player = Player(stage)
    npcs = [
        NPC('owner', '김재현 (부자)', 'banquet', [(547, 200), (549, 212)], 24),
        NPC('athlete', '박준혁 (태권도 선수)', 'hall', [(752, 870), (764, 881)], 32),
        NPC('it_expert', '이도현 (IT 전문가)', 'vault', [(1433, 787), (1434, 804)], 30),
        NPC('chef', '서유진 (요리사)', 'kitchen', [(1360, 244), (1391, 251)], 30),
        NPC('photographer', '정수빈 (사진작가)', 'banquet', [(907, 195), (912, 211)], 28),
        NPC('planner', '한지우 (파티 총무)', 'study', [(348, 718), (359, 743)], 26),
    ]
    items = [
        WorldItem('knife', 'kitchen', *ROOMS['kitchen'].point(1357, 312)),
        WorldItem('sleeping_pills', 'study', *ROOMS['study'].point(151, 808)),
        WorldItem('protein', 'foyer', *ROOMS['foyer'].point(306, 309)),
        WorldItem('coffee', 'banquet', *ROOMS['banquet'].point(928, 211)),
    ]
    props = [
        FixedProp('safe', 'vault', *ROOMS['vault'].point(1231, 734), '금고'),
        FixedProp('alarm', 'vault', *ROOMS['vault'].point(1419, 764), '경보 장치'),
        FixedProp('cake', 'banquet', *ROOMS['banquet'].point(919, 378), '케이크'),
    ]
    for obj in npcs + [player]:
        game_world.add_object(obj, 1)
    message = '목표: 보석을 확보해 현장을 빠져나가세요. [E] 조사/대화  [Q] 내려놓기'
    msg_timer = 15
    notice_text = ''
    notice_timer = 0
    input_code_mode = False
    entered_code = ''


def finish():
    game_world.clear()


def _say(value, seconds=6):
    global message, msg_timer
    message, msg_timer = value, seconds


def _end(won, reason, *, abandoned=False):
    import result_mode
    result_mode.configure(won, reason, abandoned=abandoned)
    game_framework.change_mode(result_mode)


def _nearest_interactable():
    facing_x, facing_y = FACING_VECTORS[player.sprite.facing]
    candidates = []
    for obj in npcs + items + props:
        if obj.room != stage.current_room or not obj.visible:
            continue
        dx, dy = obj.x - player.x, obj.y - player.y
        distance = hypot(dx, dy)
        if distance <= INTERACT_RANGE:
            # A modest preference for facing the target helps with nearby
            # objects without making interactions depend on an exact angle.
            alignment = (dx * facing_x + dy * facing_y) / max(1, distance)
            candidates.append((distance - 16 * alignment, obj))
    return min(candidates, key=lambda candidate: candidate[0])[1] if candidates else None


def _interaction_hint(target):
    if isinstance(target, NPC):
        action = '협박' if target.character == 'owner' and player.held_item == 'knife' else '대화'
        return f'[E] {target.display_name} {action}'
    if isinstance(target, WorldItem):
        return f'[E] {ITEM_LABELS[target.item_name]} 줍기'
    return f'[E] {target.label} 조사'


def _interact_npc(npc):
    if npc.character == 'athlete':
        if player.held_item == 'protein':
            player.drop()
            npc.working = False
            npc.visible = False
            stage.athlete_unavailable = True
            _say('박준혁: 프로틴 고맙다! 잠깐 자리 좀 비울게.')
        elif player.held_item == 'sleeping_pills':
            # Fictional, abstract state transition. No real-world administration details.
            player.drop()
            npc.working = False
            npc.visible = False
            stage.athlete_unavailable = True
            _say('복도 휴식 이벤트 완료: 박준혁은 당분간 개입하지 않습니다.')
        else:
            _say('박준혁: 지금은 복도에 있을 거야. 주인에게 무슨 일이 생기면 바로 달려갈걸?')
    elif npc.character == 'it_expert':
        stage.security_disabled = True
        _say('이도현: 시연 점검을 해볼게. 경보 시스템이 잠시 테스트 모드로 바뀌었다.')
    elif npc.character == 'photographer':
        stage.photographer_busy = True
        npc.move_to_room('study', [(156, 739), (158, 758)])
        npc.working = True
        _say('정수빈: 단체 사진 촬영? 좋아. 지금부터 다른 곳을 촬영하고 있을게.')
    elif npc.character == 'planner':
        _say('한지우: 저택 완공을 기념한 날짜는 11월 25일이야. 금고 번호도 그날에 맞췄다고 하더라.')
    elif npc.character == 'chef':
        _say('서유진: 필요한 음식은 거실에 있습니다. 주방 기구는 제자리에 두세요.')
    elif npc.character == 'owner':
        if player.held_item == 'knife':
            # The threat is a separate game event, not a regular suspicion trigger.
            player.drop()
            passed, explanation = stage.robbery_outcome()
            if passed:
                _say('강도 이벤트 성공: ' + explanation, 10)
            else:
                _end(False, explanation)
        else:
            _say('김재현: 보석은 복도 끝 금고실에 있어. 함부로 들어가지는 마.')


def _interact_prop(prop):
    global input_code_mode, entered_code
    if prop.name == 'safe':
        if stage.safe_open:
            if stage.jewel_taken:
                _say('금고는 열려 있고 보석은 이미 가져갔습니다.')
            elif player.pickup('jewel'):
                stage.jewel_taken = True
                _say('보석 획득! 현관을 거쳐 저택 밖으로 나가세요.', 9)
            else:
                _say('보석을 들려면 현재 물건을 [Q]로 내려놓으세요.')
        else:
            input_code_mode = True
            entered_code = ''
            player.keys.clear()
            _say('금고 비밀번호 4자리를 입력하고 Enter를 누르세요. 단서는 저택 안에 있습니다.')
    elif prop.name == 'alarm':
        _say('전자 보안 장치: IT 전문가에게 시스템에 대해 물어볼 수 있을 것 같다.')
    elif prop.name == 'cake':
        _say('생일 케이크가 준비되어 있다. 손님들이 거실에 모이는 시기를 알 수 있다.')


def interact():
    target = _nearest_interactable()
    if target is None:
        _say('대상에게 조금 더 가까이 가세요. 상호작용할 수 있으면 [E]가 표시됩니다.', 2.5)
        return
    if isinstance(target, NPC):
        _interact_npc(target)
    elif isinstance(target, WorldItem):
        if player.pickup(target.item_name):
            target.visible = False
            if target.item_name == 'jewel':
                stage.jewel_taken = True
            _say(f'{ITEM_LABELS[target.item_name]} 획득. 소지한 물건에 따라 목격 위험이 달라집니다.')
        else:
            _say('손에는 물건을 하나만 들 수 있습니다. [Q]로 내려놓으세요.')
    else:
        _interact_prop(target)


def _handle_safe_input(event):
    global input_code_mode, entered_code
    if event.type != SDL_KEYDOWN:
        return
    key = event.key
    if ord('0') <= key <= ord('9') and len(entered_code) < 4:
        entered_code += chr(key)
    elif key == SDLK_BACKSPACE:
        entered_code = entered_code[:-1]
    elif key in (SDLK_RETURN, SDLK_SPACE):
        if entered_code == DEMO_SAFE_CODE:
            stage.safe_open = True
            _say('비밀번호가 일치합니다. 금고가 열렸습니다. [E]로 보석을 가져가세요.')
        else:
            _say('비밀번호가 맞지 않습니다. 파티의 단서를 다시 조사해 보세요.')
        entered_code = ''
        input_code_mode = False
    elif key == SDLK_ESCAPE:
        input_code_mode = False


def handle_events():
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit_game()
            return
        if input_code_mode:
            _handle_safe_input(event)
            continue
        player.handle_event(event)
        if event.type == SDL_KEYDOWN:
            if event.key == SDLK_ESCAPE:
                game_framework.quit_game()
                return
            if event.key == SDLK_e:
                interact()
                if game_framework.current_mode is not None and game_framework.current_mode.__name__ == 'result_mode':
                    return
            elif event.key == SDLK_q:
                old = player.drop()
                if old:
                    items.append(WorldItem(old, stage.current_room, player.x, player.y))
                    _say(f'{ITEM_LABELS[old]} 내려놓음')


def update():
    global msg_timer, notice_text, notice_timer
    dt = game_framework.frame_time
    room_before = stage.current_room
    game_world.update(dt)
    msg_timer = max(0, msg_timer - dt)
    notice_timer = max(0, notice_timer - dt)
    if stage.current_room != room_before:
        notice_timer = 0
    if stage.exit_attempted:
        stage.exit_attempted = False
        if player.held_item == 'jewel':
            _end(True, '보석을 확보하고 현장에서 탈출했습니다. 범인은 이후 별도의 수사로 체포되었습니다.')
        else:
            _end(False, '만약 범인에게 이럴 용기가 있었더라면 좋았을 텐데.', abandoned=True)
        return
    if not stage.robbery_triggered:
        for npc in npcs:
            notice = stage.notice(npc, player)
            if notice:
                notice_text = notice
                notice_timer = 4
                if stage.suspicion >= 4:
                    _end(False, 'NPC의 목격으로 의심도가 최대치에 도달했습니다.')
                    return


def draw():
    clear_canvas()
    draw_rectangle(0, 0, 959, 639, 12, 11, 13, 255, filled=True)
    game_world.world[0][0].draw()
    objects = [obj for obj in npcs + items + props
               if obj.room == stage.current_room and obj.visible]
    for obj in sorted(objects + [player], key=lambda actor: actor.y, reverse=True):
        obj.draw()

    for door in stage.room.doors:
        x, y = stage.room.point(*door.point)
        width = 39 + 13 * len(door.label)
        draw_rectangle(int(x - width / 2), int(y - 12), int(x + width / 2),
                       int(y + 13), 31, 24, 23, 245, filled=True)
        text(int(x - 8 * len(door.label)), int(y + 7), door.label, 15, (251, 223, 153))

    image_for(ASSETS / 'rooms' / 'trim.png').draw(480, 590, 920, 6)
    text(24, 624, f'CASE 01  ·  {stage.room.label}', 22, (255, 243, 207))
    text(765, 623, f'의심도  {stage.suspicion} / 4', 19,
         (249, 151, 154) if stage.suspicion >= 3 else (253, 240, 190))
    if notice_timer > 0:
        text(280, 620, notice_text, 14, (249, 151, 145))
    draw_rectangle(0, 0, 959, 93, 29, 23, 22, 255, filled=True)
    held = ITEM_LABELS.get(player.held_item, '없음')
    text(24, 82, f'소지품  {held}', 17, (251, 222, 157))
    if not input_code_mode:
        target = _nearest_interactable()
        if target is not None:
            text(310, 82, _interaction_hint(target), 17, (255, 230, 160))
    text(24, 53, message if msg_timer > 0 else '보석을 확보해 현관으로 돌아가세요.', 17)
    text(24, 22, 'WASD / 방향키 이동     E 대화·조사     Q 내려놓기     Esc 종료', 14, (205, 192, 180))
    if input_code_mode:
        draw_rectangle(235, 250, 725, 411, 32, 23, 25, 255, filled=True)
        draw_rectangle(235, 250, 725, 411, 180, 135, 82)
        text(285, 384, '금고 비밀번호', 25, (255, 239, 182))
        text(285, 342, ' '.join(entered_code.ljust(4, '_')), 27)
        text(285, 290, '숫자 입력     Enter 확인     Esc 취소', 17)
    update_canvas()
