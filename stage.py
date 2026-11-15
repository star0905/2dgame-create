"""Room/background + small amount of stage geometry and game flags."""
from dataclasses import dataclass
from rooms import ROOMS


@dataclass
class Stage:
    suspicion: int = 0
    security_disabled: bool = False
    athlete_unavailable: bool = False
    photographer_busy: bool = False
    safe_open: bool = False
    robbery_triggered: bool = False
    jewel_taken: bool = False
    current_room: str = 'foyer'
    exit_attempted: bool = False
    warning_timer: float = 0.0
    invulnerability_timer: float = 0.0
    warning_message: str = ''

    def update(self, dt):
        self.warning_timer = max(0.0, self.warning_timer - dt)
        self.invulnerability_timer = max(0.0, self.invulnerability_timer - dt)

    @property
    def room(self):
        return ROOMS[self.current_room]

    def can_move(self, x, y, radius=11):
        left, bottom, right, top = self.room.rect(self.room.floor)
        if not (left + radius <= x <= right - radius and
                bottom + radius <= y <= top - radius):
            return False
        return not self.room.blocks_furniture(x, y, radius)

    def cross_door(self, player, dx, dy):
        for door in self.room.doors:
            if door.reached(self.room, player.x, player.y, dx, dy):
                if door.target == 'outside':
                    self.exit_attempted = True
                    return False
                self.current_room = door.target
                player.x, player.y = self.room.point(*door.arrival)
                return True
        return False

    @property
    def vault_restricted(self):
        return not (self.safe_open or self.security_disabled)

    def hazard_of(self, player):
        # A visitor is not suspicious just for being visible.
        if player.held_item == 'jewel':
            return ('stolen_jewel_visible', 2)
        if player.held_item == 'knife' and self.current_room != 'kitchen':
            return ('knife_outside_kitchen', 2)
        if self.current_room == 'vault' and self.vault_restricted:
            return ('restricted_study', 1)
        return None

    def notice(self, npc, player):
        if npc.room != self.current_room:
            return None
        if self.invulnerability_timer > 0:
            return None
        if self.photographer_busy and npc.character == 'photographer':
            return None
        hazard = self.hazard_of(player)
        if hazard is None or not npc.can_see(player):
            return None
        value = hazard[1]
        self.suspicion = min(4, self.suspicion + value)
        self.warning_timer = 1.8
        self.invulnerability_timer = 2.5
        self.warning_message = f'{npc.display_name}에게 목격되었습니다!'
        return f'{npc.display_name}: 수상한 행동을 목격했습니다. (의심도 +{value})'

    def robbery_outcome(self):
        # Independent event after the threat starts; no normal suspicion logic here.
        self.robbery_triggered = True
        if not self.athlete_unavailable:
            return False, '태권도 선수가 달려와 강도를 저지했습니다.'
        if not self.security_disabled:
            return False, '금고를 여는 도중 경보가 작동했습니다.'
        if not self.photographer_busy:
            return False, '사진작가의 촬영에 범행 장면이 남았습니다.'
        self.safe_open = True
        return True, '주인이 금고를 열었습니다. 보석을 가져가세요.'
