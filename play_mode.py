"""Mansion case with a fixed camera for each room."""
from math import hypot
from investigation import Investigation, CaseFile, SceneRecord
from pursuit import Pursuit
from result_mode import SUSPICION_FAILURE
from surveillance import Surveillance
from dialogue import (Dialogue, WELCOME, ATHLETE_REQUEST, ATHLETE_DRINK,
                      ATHLETE_SLEEP, ATHLETE_TESTIMONY, SECURITY)
from pico2d import clear_canvas, update_canvas, get_events, draw_rectangle, SDL_KEYDOWN, SDL_QUIT
from sdl2 import (SDLK_ESCAPE, SDLK_e, SDLK_q, SDLK_SPACE, SDLK_RETURN, SDLK_BACKSPACE,
                  SDLK_LEFT, SDLK_RIGHT, SDLK_UP, SDLK_DOWN)
import game_world
import game_framework
import game_settings
from stage import Stage
from rooms import MansionMap, ROOMS
from player import Player, MOVE
from npc import NPC
from item import WorldItem, FixedProp, ITEM_LABELS
from sprite import ASSETS, image_for
from ui import text

# Opening-event month/day inferred from ordinary records; entered manually.
DEMO_SAFE_CODE = '1125'
INTERACT_RANGE = 74
FACING_VECTORS = {'up': (0, 1), 'down': (0, -1), 'left': (-1, 0), 'right': (1, 0)}


def init():
    global stage, player, npcs, items, props, message, input_code_mode, entered_code, msg_timer
    global notice_text, notice_timer, investigation, dialogue, pursuit, surveillance
    investigation = Investigation()
    pursuit = Pursuit()
    surveillance = Surveillance()
    dialogue = Dialogue()
    dialogue.start(WELCOME)
    game_world.clear()
    stage = Stage(preparation_remaining=float(game_settings.preparation_seconds),
                  difficulty=game_settings.difficulty)
    game_world.add_object(MansionMap(stage), 0)
    player = Player(stage)
    npcs = [
        NPC('owner', '김재현 (부자)', 'vault', [(1330, 805), (1350, 805)], 24),
        NPC('athlete', '박준혁 (태권도 선수)', 'hall', [(752, 870)], 82),
        NPC('it_expert', '이도현 (보안 전문가)', 'security_room', [(720, 220)], 68),
        NPC('chef', '서유진 (요리사)', 'kitchen', [(1360, 244)], 66),
        NPC('photographer', '정수빈 (사진작가)', 'banquet', [(907, 210)], 63),
        NPC('planner', '한지우 (파티 총무)', 'banquet', [(585, 220)], 72),
    ]
    npcs[1].set_patrol([('hall', (750, 870), 3), ('foyer', (233, 330), 4)])
    npcs[2].set_patrol([('security_room', (720, 220), 4), ('security_lobby', (620, 340), 4)])
    npcs[3].set_patrol([('kitchen', (1360, 250), 4), ('banquet', (994, 270), 3)])
    _resume_photographer()
    npcs[5].set_patrol([('banquet', (585, 220), 4), ('study', (350, 820), 5)])
    items = [
        WorldItem('knife', 'kitchen', *ROOMS['kitchen'].point(1260, 372),
                  display_position=ROOMS['kitchen'].point(1260, 313)),
        WorldItem('sleeping_pills', 'study', *ROOMS['study'].point(332, 786),
                  display_position=ROOMS['study'].point(285, 782)),
        WorldItem('coffee', 'banquet', *ROOMS['banquet'].point(994, 270),
                  display_position=ROOMS['banquet'].point(993, 217)),
    ]
    props = [
        FixedProp('safe', 'vault', *ROOMS['vault'].point(1231, 734), '금고'),
        FixedProp('alarm', 'vault', *ROOMS['vault'].point(1419, 764), '경보 장치'),
        FixedProp('cake', 'banquet', *ROOMS['banquet'].point(910, 300), '케이크'),
        FixedProp('camera_console', 'security_room', *ROOMS['security_room'].point(575, 190), '카메라 점검 단말'),
    ]
    for obj in npcs + [player]:
        game_world.add_object(obj, 1)
    message = '종이 묶음을 [E]로 획득하고 [H]로 현장을 조사해 보세요. 목표는 보석 확보와 탈출입니다.'
    msg_timer = 15
    notice_text = ''
    notice_timer = 0
    input_code_mode = False
    entered_code = ''


def finish():
    for npc in npcs:
        npc.brain.close()
    game_world.clear()


def _say(value, seconds=6):
    global message, msg_timer
    message, msg_timer = value, seconds


def _speak(lines):
    player.keys.clear()
    dialogue.start(lines)


def _end(won, reason, *, abandoned=False):
    import result_mode
    result_mode.configure(won, reason, abandoned=abandoned)
    game_framework.change_mode(result_mode)


def _nearest_interactable():
    facing_x, facing_y = FACING_VECTORS[player.sprite.facing]
    candidates = []
    for obj in npcs + items + props + investigation.files + investigation.documents:
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
    if isinstance(target, CaseFile):
        return '[E] 현장 조사 자료 획득'
    if isinstance(target, NPC):
        return f'[E] {target.display_name} 대화'
    if isinstance(target, WorldItem):
        if {player.held_item, target.item_name} == {'coffee', 'sleeping_pills'}:
            return '[E] 상호작용'
        return f'[E] {ITEM_LABELS[target.item_name]} 줍기'
    return f'[E] {target.label} 조사'


def _interact_npc(npc):
    if not stage.can_prepare and npc.character in ('athlete', 'it_expert', 'photographer', 'chef'):
        _speak((('상황', '준비가 종료되었습니다. 남은 준비 상태로 범행을 진행해야 합니다.'),))
        return
    if npc.character == 'athlete':
        if npc.sleeping:
            _speak((('상황', '박준혁은 잠들어 있다. 말을 걸어도 대답하지 않는다.'),))
        elif player.held_item == 'sleeping_coffee':
            player.drop()
            npc.sleeping = True
            npc.working = False
            stage.athlete_unavailable = True
            _speak(ATHLETE_SLEEP)
        elif player.held_item == 'sleeping_pills':
            _speak((('박준혁 (운동선수)', '약은 필요 없어. 마실 거 있으면 좀 부탁할게.'),))
        elif player.held_item == 'coffee':
            player.drop()
            _speak(ATHLETE_DRINK + (('상황', '박준혁은 커피를 마시고 다시 복도를 지킨다.'),))
        elif player.held_item == 'protein':
            _speak((('박준혁 (운동선수)', '프로틴은 괜찮아. 지금은 마실 게 좀 필요해.'),))
        else:
            _speak(ATHLETE_REQUEST)
    elif npc.character == 'it_expert':
        stage.security_disabled = True
        _speak(SECURITY)
    elif npc.character == 'photographer':
        stage.photographer_busy = True
        stage.photographer_remaining = 45.0
        npc.set_patrol([])
        npc.move_to_room('study', [(156, 739), (158, 758)])
        npc.working = True
        _speak((('주인공', '아까부터 카메라가 이상해 보이는데, 확인해 보는 게 어때?'),
                ('정수빈 (사진작가)', '초점이 자꾸 어긋나네. 서재에서 45초 정도 장비를 살펴볼게.'),
                ('상황', '정수빈은 촬영을 멈추고 서재로 향했다.')))
    elif npc.character == 'planner':
        _speak((('한지우 (파티 총무)', '개관 행사 때는 손님이 정말 많았지. 그때 준비하던 기록도 아직 여기저기 남아 있을 거야.'),))
    elif npc.character == 'chef':
        if player.held_item is None:
            player.pickup('coffee')
            _speak((('서유진 (요리사)', '커피 한 잔 준비해 드릴게요. 더 필요하면 다시 말씀하세요.'),))
        else:
            _speak((('서유진 (요리사)', '커피가 필요하시면 손을 비우고 말씀해 주세요. 주방 기구는 제자리에 두세요.'),))
    elif npc.character == 'owner':
        if player.held_item == 'knife':
            # The threat is a separate game event, not a regular suspicion trigger.
            player.drop()
            stage.finish_preparation()
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
                _jewel_acquired()
            else:
                _say('보석을 들려면 현재 물건을 [Q]로 내려놓으세요.')
        else:
            input_code_mode = True
            entered_code = ''
            player.keys.clear()
            _say('월 / 일 네 자리를 입력하고 Enter를 누르세요.')
            if 'opening_plaque' not in investigation.records:
                _, label, lines = investigation.collect_record('opening_plaque')
                _speak(tuple((label, line) for line in lines) +
                       (('상황', '명판의 문구를 수첩에 기록했다.'),))
    elif prop.name == 'camera_console':
        if stage.can_prepare:
            surveillance.disable()
            _say('감시 카메라가 45초 동안 정지합니다. 금고 경보와는 별개입니다.', 8)
        else:
            _say('준비가 끝나 카메라 점검 설정을 바꿀 수 없습니다.', 5)
    elif prop.name == 'alarm':
        _say('경보 장치의 점검용 덮개가 열려 있다.')
    elif prop.name == 'cake':
        _say('테이블 위에 케이크와 접시들이 준비되어 있다.')


def interact():
    target = _nearest_interactable()
    if target is None:
        _say('대상에게 조금 더 가까이 가세요. 상호작용할 수 있으면 [E]가 표시됩니다.', 2.5)
        return
    if isinstance(target, SceneRecord):
        _, label, lines = investigation.collect_record(target.record_id)
        _speak(tuple((label, line) for line in lines) +
               (('상황', '내용을 수첩에 기록했다. [N]으로 다시 볼 수 있다.'),))
    elif isinstance(target, CaseFile):
        target.visible = False
        investigation.charges += 1
        _say('현장 조사 자료 1개 획득. 원하는 방에서 [H]로 사용하세요.', 9)
    elif isinstance(target, NPC):
        _interact_npc(target)
    elif isinstance(target, WorldItem):
        if not stage.can_prepare and target.item_name != 'jewel' and not target.dropped:
            _say('준비가 종료되어 도구를 얻거나 조합할 수 없습니다.', 5)
            return
        if {player.held_item, target.item_name} == {'coffee', 'sleeping_pills'}:
            if not stage.can_prepare:
                _say('준비가 종료되어 새 조합을 만들 수 없습니다.', 5)
                return
            player.held_item = 'sleeping_coffee'
            target.visible = False
            _say('커피와 수면제를 조합했습니다.', 8)
        elif player.pickup(target.item_name):
            target.visible = False
            if target.item_name == 'jewel':
                stage.jewel_taken = True
                _jewel_acquired()
            else:
                _say(f'{ITEM_LABELS[target.item_name]} 획득.')
        else:
            _say('손에는 물건을 하나만 들 수 있습니다. [Q]로 내려놓으세요.')
    else:
        _interact_prop(target)


def _resume_photographer():
    npcs[4].set_patrol([('banquet', (910, 215), 4), ('banquet', (600, 400), 3),
                        ('banquet', (910, 400), 4)])


def _jewel_acquired():
    if pursuit.start(stage, npcs):
        player.keys.clear()
        _say('보석을 가져가자 저택 곳곳에서 다급한 발소리가 들립니다! 현관으로 탈출하세요.', 10)
    else:
        _say('보석 획득! 현관을 거쳐 저택 밖으로 나가세요.', 9)


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
            stage.finish_preparation()
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
        if dialogue.active:
            if event.type == SDL_KEYDOWN and event.key in (SDLK_RETURN, SDLK_SPACE, SDLK_e):
                dialogue.advance()
                player.keys.clear()
            continue
        if investigation.notebook:
            if event.type == SDL_KEYDOWN:
                if event.key in (ord('n'), SDLK_ESCAPE):
                    investigation.notebook = False
                    player.keys.clear()
                elif event.key in (ord('a'), ord('w'), SDLK_LEFT, SDLK_UP):
                    investigation.note_page -= 1
                elif event.key in (ord('d'), ord('s'), SDLK_RIGHT, SDLK_DOWN):
                    investigation.note_page += 1
            continue
        if investigation.active:
            player.handle_event(event)
            if event.type == SDL_KEYDOWN:
                if event.key in (ord('h'), SDLK_ESCAPE):
                    investigation.close(player)
                elif event.key == ord('n'):
                    investigation.notebook = True
                    player.keys.clear()
                elif event.key == SDLK_e:
                    response = investigation.inspect(stage.current_room)
                    _say(response, 8)
                    if stage.current_room == 'hall' and response.startswith('흔적을 수첩'):
                        _speak(ATHLETE_TESTIMONY)
            continue
        if input_code_mode:
            _handle_safe_input(event)
            continue
        player.handle_event(event)
        if event.type == SDL_KEYDOWN:
            if event.key == ord('h'):
                _say(investigation.open_scene(stage.current_room, player), 8)
                continue
            if event.key == ord('n'):
                investigation.notebook = True
                player.keys.clear()
                continue
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
                    items.append(WorldItem(old, stage.current_room, player.x, player.y, dropped=True))
                    _say(f'{ITEM_LABELS[old]} 내려놓음')


def update():
    global msg_timer, notice_text, notice_timer
    dt = game_framework.frame_time
    if dialogue.active:
        return
    if investigation.notebook or input_code_mode:
        return
    if investigation.active:
        # The detective moves independently within this room.
        x, y = investigation.x, investigation.y
        vx = int(any(k in player.keys for k in MOVE['right'])) - int(any(k in player.keys for k in MOVE['left']))
        vy = int(any(k in player.keys for k in MOVE['up'])) - int(any(k in player.keys for k in MOVE['down']))
        distance = max(1, hypot(vx, vy))
        nx = x + vx / distance * player.speed * dt
        ny = y + vy / distance * player.speed * dt
        if stage.can_move(nx, y):
            x = nx
        if stage.can_move(x, ny):
            y = ny
        if vx:
            investigation.detective.set_facing('right' if vx > 0 else 'left')
        elif vy:
            investigation.detective.set_facing('up' if vy > 0 else 'down')
        investigation.detective.update(dt, bool(vx or vy))
        investigation.x, investigation.y = x, y
        return
    was_preparing = stage.can_prepare
    photographer_was_busy = stage.photographer_busy
    stage.update(dt)
    if photographer_was_busy and not stage.photographer_busy and not pursuit.active:
        _resume_photographer()
        _say('사진작가가 장비 점검을 마치고 연회장으로 돌아옵니다.', 6)
    if was_preparing and not stage.can_prepare:
        _say('준비 시간이 끝났습니다. 이제 남은 상황에서 행동해야 합니다.', 10)
    room_before = stage.current_room
    game_world.update(dt)
    msg_timer = max(0, msg_timer - dt)
    notice_timer = max(0, notice_timer - dt)
    if stage.current_room != room_before:
        notice_timer = 0
    if stage.exit_attempted:
        stage.exit_attempted = False
        if player.held_item == 'jewel':
            _end(True, '범인은 주인을 위협해 금고를 열게 한 뒤, 보석을 챙겨 뒤쫓는 사람들을 피해 현관으로 빠져나갔을 겁니다.' if stage.robbery_triggered else '범인은 사람들의 눈을 피해 금고를 열고, 보석을 챙겨 현관으로 빠져나갔을 겁니다.')
        else:
            _end(False, '만약 범인에게 이럴 용기가 있었더라면 좋았을 텐데.', abandoned=True)
        return
    camera_notice = surveillance.update(dt, stage, player)
    if camera_notice:
        notice_text, notice_timer = camera_notice, 4
    if stage.suspicion >= 4:
        _end(False, SUSPICION_FAILURE)
        return
    captor = pursuit.update(dt, stage, player)
    if captor is not None:
        _end(False, f'{captor.display_name}에게 붙잡혔습니다. 이 동선이었다면 범인은 현관에 도착하지 못했겠군요. 다른 탈출 방법을 생각해 봐야겠습니다.')
        return
    if not stage.robbery_triggered:
        for npc in npcs:
            notice = stage.notice(npc, player)
            if notice:
                notice_text = notice
                notice_timer = 4
                if stage.suspicion >= 4:
                    _end(False, SUSPICION_FAILURE)
                    return


def draw():
    clear_canvas()
    draw_rectangle(0, 0, 959, 639, 12, 11, 13, 255, filled=True)
    game_world.world[0][0].draw()
    objects = [obj for obj in npcs + items + props + investigation.files + investigation.documents
               if obj.room == stage.current_room and obj.visible]
    if investigation.active:
        investigation.draw_scene(stage.current_room)
    else:
        surveillance.draw(stage.current_room)
        for obj in sorted(objects + [player], key=lambda actor: actor.y, reverse=True):
            obj.draw()

    for door in stage.room.doors:
        x, y = stage.room.point(*door.point)
        restricted = door.target in ('vault', 'security_lobby', 'security_room') and stage.vault_restricted
        label = ROOMS[door.target].label + ' · 출입 제한' if restricted else door.label
        label_color = (255, 169, 151) if restricted else (251, 223, 153)
        width = 39 + 13 * len(label)
        x = max(22 + width / 2, min(938 - width / 2, x))
        draw_rectangle(int(x - width / 2), int(y - 12), int(x + width / 2),
                       int(y + 13), 31, 24, 23, 245, filled=True)
        text(int(x - 7 * len(label)), int(y + 7), label, 15, label_color)

    image_for(ASSETS / 'rooms' / 'trim.png').draw(480, 590, 920, 6)
    period = '사건 이후' if investigation.active else '범행 재현'
    text(24, 624, f'{period}  ·  {stage.room.label}', 22, (255, 243, 207))
    text(765, 623, f'의심도  {stage.suspicion} / 4', 19,
         (249, 151, 154) if stage.suspicion >= 3 else (253, 240, 190))
    phase = '추적 중 · 탈출' if pursuit.active else ('준비 ' + game_settings.clock(stage.preparation_remaining) if stage.can_prepare else '준비 종료')
    text(390, 622, f'{game_settings.LABELS[stage.difficulty]} · {phase}', 19,
         (255, 159, 137) if stage.can_prepare and stage.preparation_remaining <= 30 else (255, 231, 177))
    if surveillance.disabled_remaining > 0:
        text(24, 590, f'카메라 정지 {surveillance.disabled_remaining:.0f}초', 15, (153, 215, 188))
    if notice_timer > 0:
        text(280, 590, notice_text, 14, (249, 151, 145))
    draw_rectangle(0, 0, 959, 93, 29, 23, 22, 255, filled=True)
    held = ITEM_LABELS.get(player.held_item, '없음')
    text(24, 82, f'소지품  {held}', 17, (251, 222, 157))
    if not input_code_mode and not investigation.active:
        target = _nearest_interactable()
        if target is not None:
            text(310, 82, _interaction_hint(target), 17, (255, 230, 160))
    text(24, 53, message if msg_timer > 0 else '보석을 확보해 현관으로 돌아가세요.', 17)
    text(24, 22, f'이동 WASD / 방향키   E 조사   Q 내려놓기   H 현장 조사 ({investigation.charges})   N 수첩', 14, (205, 192, 180))
    if investigation.active:
        text(310, 82, '[E] 흔적 조사    [H / Esc] 재현으로 복귀', 17, (173, 228, 250))
    if investigation.notebook:
        investigation.draw_notebook()
    if input_code_mode:
        draw_rectangle(235, 250, 725, 411, 32, 23, 25, 255, filled=True)
        draw_rectangle(235, 250, 725, 411, 180, 135, 82)
        text(285, 384, '금고 비밀번호  ·  월 / 일', 25, (255, 239, 182))
        text(285, 342, ' '.join(entered_code.ljust(4, '_')[:2]) + ' / ' + ' '.join(entered_code.ljust(4, '_')[2:]), 27)
        text(285, 290, '숫자 입력     Enter 확인     Esc 취소', 17)
    if dialogue.active:
        dialogue.draw()
    update_canvas()
