import pygame
import math
import random
import sys
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple

# ---------- Константы ----------
WIDTH, HEIGHT = 1280, 720
FPS = 60
CELL = 28

SNAKE_SPEED_BASE = 6.0
SNAKE_SPEED_PER_BOOST = 0.25
MAX_BOOSTERS = 10
MAX_HEALS = 10

HEAD_MAX_HP = 100

COLOR_BG = (14, 16, 24)
COLOR_GRID = (24, 28, 38)
COLOR_GRID_MAJOR = (36, 42, 56)
COLOR_HEAD = (140, 255, 180)
COLOR_HEAD_GLOW = (60, 200, 120)
COLOR_BODY = (60, 170, 100)
COLOR_BODY_DARK = (40, 120, 70)
COLOR_ENEMY = (230, 80, 80)
COLOR_ENEMY_FAST = (255, 140, 60)
COLOR_ENEMY_TANK = (160, 60, 200)
COLOR_ENEMY_SHOOTER = (255, 80, 200)
COLOR_ENEMY_BULLET = (255, 100, 100)
COLOR_BULLET = (255, 240, 120)
COLOR_STATION = (255, 200, 60)
COLOR_TEXT = (230, 230, 230)
COLOR_DIM = (150, 150, 160)
COLOR_GOLD = (255, 210, 80)

# ---------- Утилиты ----------
def clamp(v, a, b):
    return max(a, min(b, v))

def dist2(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy

def angle_to(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0])

def draw_circle_glow(surface, color, center, radius, glow=10):
    for i in range(glow, 0, -1):
        a = int(40 * (1 - i / glow))
        glow_color = (color[0], color[1], color[2], a)
        s = pygame.Surface((radius * 2 + glow * 2, radius * 2 + glow * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, glow_color, (radius + glow, radius + glow), radius + i)
        surface.blit(s, (center[0] - radius - glow, center[1] - radius - glow))
    pygame.draw.circle(surface, color, center, radius)

# ---------- Модули ----------
class ModType(Enum):
    PISTOL = auto()
    RIFLE = auto()
    SNIPER = auto()
    SHIELD = auto()
    HEAL = auto()
    BOOSTER = auto()
    AXES = auto()

MOD_NAMES = {
    ModType.PISTOL: "Пистолет",
    ModType.RIFLE: "Автомат",
    ModType.SNIPER: "Снайперка",
    ModType.SHIELD: "Щит",
    ModType.HEAL: "Хилка",
    ModType.BOOSTER: "Ускоритель",
    ModType.AXES: "Два топора",
}

MOD_BASE_HP = {
    ModType.PISTOL: 40,
    ModType.RIFLE: 35,
    ModType.SNIPER: 45,
    ModType.SHIELD: 60,
    ModType.HEAL: 25,
    ModType.BOOSTER: 25,
    ModType.AXES: 80,
}

MOD_COLORS = {
    ModType.PISTOL: (100, 200, 255),
    ModType.RIFLE: (100, 255, 200),
    ModType.SNIPER: (200, 120, 255),
    ModType.SHIELD: (255, 220, 100),
    ModType.HEAL: (100, 255, 120),
    ModType.BOOSTER: (255, 140, 255),
    ModType.AXES: (255, 100, 100),
}

GUN_STATS = {
    ModType.PISTOL: (12, 340, 0.55),
    ModType.RIFLE: (6, 300, 0.13),
    ModType.SNIPER: (40, 620, 1.4),
}

@dataclass
class Module:
    mtype: ModType
    hp: float
    max_hp: float
    level: int = 1
    cooldown: float = 0.0
    phase: float = 0.0

    def is_gun(self):
        return self.mtype in GUN_STATS

# ---------- Враги ----------
class EnemyKind(Enum):
    NORMAL = auto()
    FAST = auto()
    TANK = auto()
    SHOOTER = auto()

@dataclass
class Enemy:
    x: float
    y: float
    hp: float
    max_hp: float
    speed: float
    radius: float
    damage: float
    kind: EnemyKind
    color: Tuple[int, int, int]
    reward_xp: int
    reward_money: int
    shoot_cooldown: float = 0.0

@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    damage: float
    life: float = 1.2
    radius: float = 4.0
    enemy: bool = False

@dataclass
class Station:
    x: float
    y: float
    radius: float = 26.0
    used: bool = False

@dataclass
class Pickup:
    x: float
    y: float
    mtype: ModType
    radius: float = 16.0

# ---------- Змея ----------
class Snake:
    def __init__(self):
        self.head_pos = pygame.Vector2(0, 0)
        self.dir = pygame.Vector2(1, 0)
        self.dir_target = pygame.Vector2(1, 0)
        self.speed = SNAKE_SPEED_BASE * CELL
        self.head_hp = HEAD_MAX_HP
        self.head_max_hp = HEAD_MAX_HP
        self.body: List[pygame.Vector2] = []
        self.body_size = 3
        self._init_body()

        self.modules: List[Module] = []
        self.lost_modules: List[ModType] = []
        self.had_modules = False
        self.money = 0
        self.xp = 0
        self.level = 1
        self.xp_to_next = 10
        self.boosters = 0
        self.heals = 0
        self.alive = True

        # стартовый модуль — займёт первый блок тела
        self.add_module(ModType.PISTOL)

    def _init_body(self):
        self.body.clear()
        back = -self.dir
        for i in range(1, self.body_size + 1):
            self.body.append(self.head_pos + back * (CELL * i))

    def _grow_body(self):
        if self.body:
            last = self.body[-1]
            prev = self.body[-2] if len(self.body) >= 2 else self.head_pos
            d = last - prev
            if d.length_squared() < 1e-6:
                d = -self.dir
            d = d.normalize()
            self.body.append(last + d * CELL)
        else:
            self.body.append(self.head_pos - self.dir * CELL)
        self.body_size = len(self.body)

    def total_speed(self):
        return self.speed * (1.0 + SNAKE_SPEED_PER_BOOST * self.boosters)

    def module_positions(self):
        # модули лежат на блоках тела: i-й модуль на i-м блоке
        res = []
        for i in range(len(self.modules)):
            if i < len(self.body):
                res.append(self.body[i])
            elif self.body:
                res.append(self.body[-1])
            else:
                res.append(self.head_pos)
        return res

    def update(self, dt, game):
        if not self.alive:
            return
        self.dir = self.dir.lerp(self.dir_target, clamp(12 * dt, 0, 1))
        if self.dir.length_squared() < 1e-6:
            self.dir = pygame.Vector2(1, 0)
        self.dir = self.dir.normalize()

        speed = self.total_speed()
        self.head_pos += self.dir * speed * dt

        target = self.head_pos
        seg_dist = CELL
        for i in range(len(self.body)):
            to = target - self.body[i]
            d = to.length()
            if d > seg_dist:
                self.body[i] = target - to.normalize() * seg_dist
            target = self.body[i]

        for m in self.modules:
            m.cooldown = max(0.0, m.cooldown - dt)
            m.phase += dt
        self._handle_guns(game)
        self._handle_heals(game)
        self._handle_shield_axes(game, dt)

    def _handle_guns(self, game):
        mpos = self.module_positions()
        for i, m in enumerate(self.modules):
            if not m.is_gun():
                continue
            if m.cooldown > 0:
                continue
            pos = mpos[i]
            target = None
            best = None
            for e in game.enemies:
                d = dist2((pos.x, pos.y), (e.x, e.y))
                rng = GUN_STATS[m.mtype][1]
                if d <= rng * rng:
                    if best is None or d < best:
                        best = d
                        target = e
            if target is None:
                continue
            dmg, rng, cd = GUN_STATS[m.mtype]
            lvl_mult = 1.0 + 0.25 * (m.level - 1)
            dmg *= lvl_mult
            ang = angle_to((pos.x, pos.y), (target.x, target.y))
            speed = 900
            b = Bullet(pos.x, pos.y, math.cos(ang) * speed, math.sin(ang) * speed, dmg)
            game.bullets.append(b)
            m.cooldown = cd

    def _handle_heals(self, game):
        for idx, m in enumerate(self.modules):
            if m.mtype != ModType.HEAL:
                continue
            if m.cooldown > 0:
                continue
            m.cooldown = 1.5
            heal = 0.5 + 0.3 * m.level
            if self.head_hp < self.head_max_hp:
                self.head_hp = min(self.head_max_hp, self.head_hp + heal)
            mpos = self.module_positions()
            mp = mpos[idx]
            radius = 70 + 5 * m.level
            for j, other in enumerate(self.modules):
                if other is m:
                    continue
                p = mpos[j]
                if dist2((mp.x, mp.y), (p.x, p.y)) <= radius * radius:
                    other.hp = min(other.max_hp, other.hp + heal * 0.4)

    def _handle_shield_axes(self, game, dt):
        mpos = self.module_positions()
        for i, m in enumerate(self.modules):
            if m.mtype != ModType.AXES:
                continue
            mp = mpos[i]
            orbit = 55 + 5 * m.level
            ang = m.phase * 3.0
            for k in range(2):
                a = ang + k * math.pi
                ax = mp.x + math.cos(a) * orbit
                ay = mp.y + math.sin(a) * orbit
                for e in game.enemies:
                    if dist2((ax, ay), (e.x, e.y)) <= (e.radius + 14) ** 2:
                        if m.cooldown <= 0:
                            e.hp -= 8 + 4 * m.level
                            dx, dy = e.x - ax, e.y - ay
                            dl = math.hypot(dx, dy) or 1
                            e.x += dx / dl * 18
                            e.y += dy / dl * 18
                            m.cooldown = 0.25

    def add_module(self, mtype: ModType, grow_body=True):
        if mtype == ModType.BOOSTER and self.boosters >= MAX_BOOSTERS:
            return False
        if mtype == ModType.HEAL and self.heals >= MAX_HEALS:
            return False
        m = Module(mtype, MOD_BASE_HP[mtype], MOD_BASE_HP[mtype])
        if mtype == ModType.BOOSTER:
            self.boosters += 1
        if mtype == ModType.HEAL:
            self.heals += 1
        self.modules.append(m)
        self.had_modules = True
        if grow_body:
            self._grow_body()
        return True

    def damage_module_chain(self, index: int):
        # удалить модули index..end; тело не сокращается
        removed = self.modules[index:]
        self.modules = self.modules[:index]
        for m in removed:
            self.lost_modules.append(m.mtype)
            if m.mtype == ModType.BOOSTER:
                self.boosters = max(0, self.boosters - 1)
            if m.mtype == ModType.HEAL:
                self.heals = max(0, self.heals - 1)

    def update_module_hp(self, dt, game):
        mpos = self.module_positions()
        for i, m in enumerate(self.modules):
            p = mpos[i]
            for e in game.enemies:
                if dist2((p.x, p.y), (e.x, e.y)) <= (e.radius + 12) ** 2:
                    m.hp -= e.damage * dt * 0.8
            if m.hp <= 0:
                self.damage_module_chain(i)
                return True
        return False

# ---------- Игра ----------
class Game:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        self.big_font = pygame.font.SysFont("consolas", 36, bold=True)
        self.small_font = pygame.font.SysFont("consolas", 14)
        self.reset()

    def reset(self):
        self.snake = Snake()
        self.enemies: List[Enemy] = []
        self.bullets: List[Bullet] = []
        self.pickups: List[Pickup] = []
        self.stations: List[Station] = []
        self.wave = 0
        self.wave_timer = 2.0
        self.spawn_pickup_timer = 6.0
        self.spawn_station_timer = 25.0
        self.paused = False
        self.game_over = False
        self.show_upgrade = False
        self.upgrade_options: List[Tuple[str, object]] = []
        self.message = ""
        self.message_timer = 0.0
        self.station_menu = False
        self.station_menu_ref: Optional[Station] = None
        self.reorder_mode = False
        self.reorder_selected = -1
        self.cam = pygame.Vector2(0, 0)

    def msg(self, text, t=2.0):
        self.message = text
        self.message_timer = t

    def _random_ring_pos(self, r_min, r_max):
        ang = random.uniform(0, math.tau)
        r = random.uniform(r_min, r_max)
        return (self.snake.head_pos.x + math.cos(ang) * r,
                self.snake.head_pos.y + math.sin(ang) * r)

    # --- Спавн ---
    def spawn_wave(self):
        self.wave += 1
        count = min(3 + self.wave * 2, 30)
        base_hp = 12 + self.wave * 6
        for _ in range(count):
            self.spawn_enemy(base_hp)
        self.msg(f"Волна {self.wave}")

    def spawn_enemy(self, base_hp):
        x, y = self._random_ring_pos(280, 600)
        roll = random.random()
        w = self.wave
        if w >= 2 and roll < 0.15:
            hp = base_hp * 2.5
            e = Enemy(x, y, hp, hp, 40 + w * 1.5, 18, 14, EnemyKind.TANK,
                      COLOR_ENEMY_TANK, 4, 4)
        elif w >= 3 and roll < 0.30:
            hp = base_hp * 0.9
            e = Enemy(x, y, hp, hp, 55 + w * 2, 13, 6, EnemyKind.SHOOTER,
                      COLOR_ENEMY_SHOOTER, 3, 3, shoot_cooldown=1.5)
        elif roll < 0.55:
            hp = base_hp * 0.7
            e = Enemy(x, y, hp, hp, 100 + w * 3, 10, 6, EnemyKind.FAST,
                      COLOR_ENEMY_FAST, 2, 2)
        else:
            e = Enemy(x, y, base_hp, base_hp, 60 + w * 2, 13, 8, EnemyKind.NORMAL,
                      COLOR_ENEMY, 1, 1)
        self.enemies.append(e)

    def spawn_pickup(self):
        if len(self.pickups) > 5:
            return
        roll = random.random()
        if roll < 0.04:
            mtype = ModType.AXES
        elif roll < 0.40:
            mtype = random.choice([ModType.PISTOL, ModType.RIFLE, ModType.SNIPER])
        elif roll < 0.60:
            mtype = ModType.SHIELD
        elif roll < 0.85:
            mtype = random.choice([ModType.HEAL, ModType.BOOSTER])
        else:
            mtype = random.choice([ModType.PISTOL, ModType.RIFLE, ModType.SNIPER])
        if mtype == ModType.HEAL and self.snake.heals >= MAX_HEALS:
            return
        if mtype == ModType.BOOSTER and self.snake.boosters >= MAX_BOOSTERS:
            return
        x, y = self._random_ring_pos(140, 450)
        self.pickups.append(Pickup(x, y, mtype))

    def spawn_station(self):
        if any(not s.used for s in self.stations):
            return
        self.stations = [s for s in self.stations if not s.used]
        x, y = self._random_ring_pos(200, 500)
        self.stations.append(Station(x, y))

    # --- Камера ---
    def update_camera(self):
        target_x = self.snake.head_pos.x - WIDTH / 2
        target_y = self.snake.head_pos.y - HEIGHT / 2
        self.cam.x += (target_x - self.cam.x) * 0.15
        self.cam.y += (target_y - self.cam.y) * 0.15

    def world_to_screen(self, x, y):
        return int(x - self.cam.x), int(y - self.cam.y)

    # --- Обновление ---
    def update(self, dt):
        if self.game_over or self.paused or self.show_upgrade or self.station_menu or self.reorder_mode:
            return
        s = self.snake

        s.update(dt, self)
        if s.head_hp <= 0:
            s.alive = False
            self.game_over = True
            return
        if s.had_modules and not s.modules:
            self.game_over = True
            return

        if s.update_module_hp(dt, self):
            if s.had_modules and not s.modules:
                self.game_over = True
                return

        for e in list(self.enemies):
            ang = angle_to((e.x, e.y), s.head_pos)
            d = math.sqrt(dist2((e.x, e.y), s.head_pos))
            if e.kind == EnemyKind.SHOOTER and d < 280:
                ang += math.pi
            e.x += math.cos(ang) * e.speed * dt
            e.y += math.sin(ang) * e.speed * dt
            if e.kind == EnemyKind.SHOOTER:
                e.shoot_cooldown -= dt
                if e.shoot_cooldown <= 0 and d < 500:
                    e.shoot_cooldown = 2.0
                    a = angle_to((e.x, e.y), s.head_pos)
                    self.bullets.append(Bullet(e.x, e.y,
                                               math.cos(a) * 350, math.sin(a) * 350,
                                               e.damage, life=2.0, radius=5, enemy=True))
            if dist2((e.x, e.y), s.head_pos) <= (e.radius + CELL * 0.6) ** 2:
                s.head_hp -= e.damage * dt * 2.5
                dx, dy = e.x - s.head_pos.x, e.y - s.head_pos.y
                dl = math.hypot(dx, dy) or 1
                e.x += dx / dl * 10
                e.y += dy / dl * 10
                s.head_hp = max(0, s.head_hp)

        for b in list(self.bullets):
            b.x += b.vx * dt
            b.y += b.vy * dt
            b.life -= dt
            if b.life <= 0:
                self.bullets.remove(b)
                continue
            if b.enemy:
                hit = False
                if dist2((b.x, b.y), s.head_pos) <= (b.radius + CELL * 0.6) ** 2:
                    s.head_hp = max(0, s.head_hp - b.damage)
                    hit = True
                if not hit:
                    for bb in s.body:
                        if dist2((b.x, b.y), (bb.x, bb.y)) <= (b.radius + CELL * 0.5) ** 2:
                            s.head_hp = max(0, s.head_hp - b.damage * 0.5)
                            hit = True
                            break
                if hit:
                    self.bullets.remove(b)
            else:
                hit = False
                for e in list(self.enemies):
                    if dist2((b.x, b.y), (e.x, e.y)) <= (e.radius + b.radius) ** 2:
                        e.hp -= b.damage
                        hit = True
                        break
                if hit:
                    self.bullets.remove(b)

        for e in list(self.enemies):
            if e.hp <= 0:
                self.enemies.remove(e)
                s.xp += e.reward_xp
                s.money += e.reward_money
                self.check_levelup()

        for p in list(self.pickups):
            touch = False
            if dist2((p.x, p.y), s.head_pos) <= (p.radius + CELL) ** 2:
                touch = True
            if not touch:
                for b in s.body:
                    if dist2((p.x, p.y), (b.x, b.y)) <= (p.radius + CELL * 0.7) ** 2:
                        touch = True
                        break
            if touch:
                if s.add_module(p.mtype):
                    self.pickups.remove(p)
                    self.msg(f"+{MOD_NAMES[p.mtype]}")
                else:
                    self.msg("Лимит данного типа достигнут", 1.0)

        for st in self.stations:
            if st.used:
                continue
            if dist2((st.x, st.y), s.head_pos) <= (st.radius + CELL) ** 2:
                self.open_station_menu(st)
                break

        self.wave_timer -= dt
        if self.wave_timer <= 0:
            self.spawn_wave()
            self.wave_timer = max(6.0, 12.0 - self.wave * 0.3)

        self.spawn_pickup_timer -= dt
        if self.spawn_pickup_timer <= 0:
            self.spawn_pickup()
            self.spawn_pickup_timer = random.uniform(6, 11)

        self.spawn_station_timer -= dt
        if self.spawn_station_timer <= 0:
            self.spawn_station()
            self.spawn_station_timer = random.uniform(30, 50)

        if self.message_timer > 0:
            self.message_timer -= dt

        self.update_camera()

    def check_levelup(self):
        s = self.snake
        while s.xp >= s.xp_to_next:
            s.xp -= s.xp_to_next
            s.level += 1
            s.xp_to_next = int(s.xp_to_next * 1.35 + 4)
            self.open_upgrade_menu()
            break

    def open_upgrade_menu(self):
        self.show_upgrade = True
        opts: List[Tuple[str, object]] = []
        existing_types = {m.mtype for m in self.snake.modules}
        for t in existing_types:
            opts.append((f"Усилить: {MOD_NAMES[t]}", ('upgrade', t)))
        for t in [ModType.PISTOL, ModType.RIFLE, ModType.SNIPER, ModType.SHIELD,
                  ModType.HEAL, ModType.BOOSTER]:
            if t not in existing_types:
                if t == ModType.HEAL and self.snake.heals >= MAX_HEALS:
                    continue
                if t == ModType.BOOSTER and self.snake.boosters >= MAX_BOOSTERS:
                    continue
                opts.append((f"Новый модуль: {MOD_NAMES[t]}", ('add', t)))
        random.shuffle(opts)
        self.upgrade_options = opts[:3]

    def apply_upgrade(self, idx):
        if 0 <= idx < len(self.upgrade_options):
            label, (kind, t) = self.upgrade_options[idx]
            s = self.snake
            if kind == 'upgrade':
                for m in s.modules:
                    if m.mtype == t:
                        m.level += 1
                        m.max_hp *= 1.2
                        m.hp = m.max_hp
                        break
                self.msg(f"Усилен {MOD_NAMES[t]}")
            else:
                if s.add_module(t):
                    self.msg(f"Новый модуль: {MOD_NAMES[t]}")
                else:
                    self.msg("Лимит типа достигнут")
        self.show_upgrade = False
        self.upgrade_options = []

    # --- Станция ---
    def open_station_menu(self, st: Station):
        self.station_menu = True
        self.station_menu_ref = st
        st.used = True

    def close_station_menu(self):
        self.station_menu = False
        self.station_menu_ref = None

    def station_repair(self):
        s = self.snake
        if not s.lost_modules:
            self.msg("Нет потерянных модулей")
            return
        cost = len(s.lost_modules) * 8
        if s.money < cost:
            self.msg(f"Нужно {cost} валюты, у тебя {s.money}")
            return
        s.money -= cost
        restored = s.lost_modules[:]
        s.lost_modules.clear()
        count = 0
        for t in restored:
            if t == ModType.HEAL and s.heals >= MAX_HEALS:
                continue
            if t == ModType.BOOSTER and s.boosters >= MAX_BOOSTERS:
                continue
            if s.add_module(t):
                count += 1
        self.msg(f"Восстановлено модулей: {count}")

    def station_heal(self):
        s = self.snake
        heal = s.head_max_hp * 0.25
        s.head_hp = min(s.head_max_hp, s.head_hp + heal)
        self.msg("Голова восстановлена на 25%")

    def station_reorder_start(self):
        if len(self.snake.modules) < 2:
            self.msg("Нечего переставлять (нужно 2+ модуля)")
            return
        self.station_menu = False
        self.reorder_mode = True
        self.reorder_selected = 0

    # --- Отрисовка ---
    def draw(self):
        self.screen.fill(COLOR_BG)
        self.draw_grid()
        self.draw_stations()
        self.draw_pickups()
        self.draw_enemies()
        self.draw_bullets()
        self.draw_snake()
        self.draw_hud()
        if self.paused:
            self.draw_overlay("ПАУЗА", "Пробел — продолжить")
        if self.show_upgrade:
            self.draw_upgrade()
        if self.station_menu:
            self.draw_station_menu()
        if self.reorder_mode:
            self.draw_reorder()
        if self.game_over:
            self.draw_game_over()
        if self.message_timer > 0:
            surf = self.font.render(self.message, True, COLOR_GOLD)
            self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT - 60))

    def draw_grid(self):
        offset_x = -self.cam.x % CELL
        offset_y = -self.cam.y % CELL
        x = offset_x
        while x < WIDTH:
            pygame.draw.line(self.screen, COLOR_GRID, (x, 0), (x, HEIGHT))
            x += CELL
        y = offset_y
        while y < HEIGHT:
            pygame.draw.line(self.screen, COLOR_GRID, (0, y), (WIDTH, y))
            y += CELL
        offset_x5 = -self.cam.x % (CELL * 5)
        offset_y5 = -self.cam.y % (CELL * 5)
        x = offset_x5
        while x < WIDTH:
            pygame.draw.line(self.screen, COLOR_GRID_MAJOR, (x, 0), (x, HEIGHT))
            x += CELL * 5
        y = offset_y5
        while y < HEIGHT:
            pygame.draw.line(self.screen, COLOR_GRID_MAJOR, (0, y), (WIDTH, y))
            y += CELL * 5

    def _visible(self, x, y, margin=80):
        sx, sy = self.world_to_screen(x, y)
        return -margin <= sx <= WIDTH + margin and -margin <= sy <= HEIGHT + margin

    def draw_stations(self):
        for st in self.stations:
            if st.used:
                continue
            if not self._visible(st.x, st.y, 100):
                continue
            sx, sy = self.world_to_screen(st.x, st.y)
            draw_circle_glow(self.screen, COLOR_STATION, (sx, sy), int(st.radius), glow=12)
            pygame.draw.circle(self.screen, (60, 40, 10), (sx, sy), int(st.radius) - 6, 2)
            label = self.small_font.render("ST", True, (30, 20, 0))
            self.screen.blit(label, (sx - label.get_width() // 2, sy - label.get_height() // 2))

    def draw_pickups(self):
        for p in self.pickups:
            if not self._visible(p.x, p.y):
                continue
            sx, sy = self.world_to_screen(p.x, p.y)
            color = MOD_COLORS[p.mtype]
            phase = (pygame.time.get_ticks() / 300.0) % 1.0
            r = int(p.radius + math.sin(phase * math.tau) * 2)
            draw_circle_glow(self.screen, color, (sx, sy), r, glow=8)
            pygame.draw.circle(self.screen, (255, 255, 255), (sx, sy), r, 1)

    def draw_enemies(self):
        for e in self.enemies:
            if not self._visible(e.x, e.y):
                continue
            sx, sy = self.world_to_screen(e.x, e.y)
            draw_circle_glow(self.screen, e.color, (sx, sy), int(e.radius), glow=6)
            if e.kind == EnemyKind.TANK:
                pygame.draw.circle(self.screen, (60, 20, 80), (sx, sy), int(e.radius) - 4, 2)
            elif e.kind == EnemyKind.SHOOTER:
                pygame.draw.circle(self.screen, (80, 20, 60), (sx, sy), int(e.radius) - 4, 2)
            ratio = clamp(e.hp / e.max_hp, 0, 1)
            pygame.draw.rect(self.screen, (60, 0, 0), (sx - 14, sy - e.radius - 8, 28, 4))
            pygame.draw.rect(self.screen, (0, 220, 60), (sx - 14, sy - e.radius - 8, 28 * ratio, 4))

    def draw_bullets(self):
        for b in self.bullets:
            if not self._visible(b.x, b.y, 20):
                continue
            sx, sy = self.world_to_screen(b.x, b.y)
            color = COLOR_ENEMY_BULLET if b.enemy else COLOR_BULLET
            pygame.draw.circle(self.screen, color, (sx, sy), int(b.radius))
            pygame.draw.circle(self.screen, (255, 255, 255), (sx, sy), int(b.radius), 1)

    def draw_snake(self):
        s = self.snake
        # тело от хвоста к голове
        for i in range(len(s.body) - 1, -1, -1):
            b = s.body[i]
            sx, sy = self.world_to_screen(b.x, b.y)
            size = CELL * 0.95
            rect = pygame.Rect(sx - size / 2, sy - size / 2, size, size)
            pygame.draw.rect(self.screen, COLOR_BODY_DARK, rect, border_radius=8)
            inner = rect.inflate(-4, -4)
            pygame.draw.rect(self.screen, COLOR_BODY, inner, border_radius=6)
        # голова
        hx, hy = self.world_to_screen(s.head_pos.x, s.head_pos.y)
        draw_circle_glow(self.screen, COLOR_HEAD_GLOW, (hx, hy), int(CELL * 0.8), glow=10)
        pygame.draw.circle(self.screen, COLOR_HEAD, (hx, hy), int(CELL * 0.7))
        perp = pygame.Vector2(-s.dir.y, s.dir.x)
        for side in (-1, 1):
            ex = hx + s.dir.x * 6 + perp.x * 6 * side
            ey = hy + s.dir.y * 6 + perp.y * 6 * side
            pygame.draw.circle(self.screen, (20, 20, 30), (int(ex), int(ey)), 3)

        # модули — на блоках тела
        mpos = s.module_positions()
        for i, m in enumerate(s.modules):
            if i >= len(mpos):
                continue
            p = mpos[i]
            sx, sy = self.world_to_screen(p.x, p.y)
            color = MOD_COLORS[m.mtype]
            r = CELL * 0.65
            pygame.draw.rect(self.screen, (0, 0, 0), (sx - r / 2 + 2, sy - r / 2 + 2, r, r), border_radius=5)
            pygame.draw.rect(self.screen, color, (sx - r / 2, sy - r / 2, r, r), border_radius=5)
            pygame.draw.rect(self.screen, (255, 255, 255), (sx - r / 2, sy - r / 2, r, r), 1, border_radius=5)
            if m.is_gun():
                target = None
                best = None
                for e in self.enemies:
                    d = dist2((p.x, p.y), (e.x, e.y))
                    if best is None or d < best:
                        best = d
                        target = e
                if target:
                    ang = angle_to((p.x, p.y), (target.x, target.y))
                    ex = sx + math.cos(ang) * (CELL * 0.8)
                    ey = sy + math.sin(ang) * (CELL * 0.8)
                    pygame.draw.line(self.screen, (255, 255, 255), (sx, sy), (ex, ey), 3)
            if m.mtype == ModType.SHIELD:
                for k in range(2):
                    a = m.phase * 2.5 + k * math.pi
                    shx = sx + math.cos(a) * 30
                    shy = sy + math.sin(a) * 30
                    pygame.draw.circle(self.screen, (255, 240, 180), (int(shx), int(shy)), 10)
                    pygame.draw.circle(self.screen, (255, 180, 0), (int(shx), int(shy)), 10, 2)
            if m.mtype == ModType.AXES:
                for k in range(2):
                    a = m.phase * 3.0 + k * math.pi
                    ax = sx + math.cos(a) * 55
                    ay = sy + math.sin(a) * 55
                    pygame.draw.circle(self.screen, (220, 60, 60), (int(ax), int(ay)), 11)
                    pygame.draw.circle(self.screen, (255, 180, 180), (int(ax), int(ay)), 11, 2)
            ratio = clamp(m.hp / m.max_hp, 0, 1)
            pygame.draw.rect(self.screen, (60, 0, 0), (sx - 14, sy + 14, 28, 4))
            pygame.draw.rect(self.screen, (0, 220, 60), (sx - 14, sy + 14, 28 * ratio, 4))

    def draw_hud(self):
        s = self.snake
        panel = pygame.Surface((300, 160), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 130))
        self.screen.blit(panel, (0, 0))
        lines = [
            f"HP головы: {int(s.head_hp)}/{s.head_max_hp}",
            f"Уровень: {s.level}  XP: {s.xp}/{s.xp_to_next}",
            f"Волна: {self.wave}",
            f"Валюта: {s.money}",
            f"Модули: {len(s.modules)}  Потеряно: {len(s.lost_modules)}",
            f"Ускорители: {s.boosters}/{MAX_BOOSTERS}  Хилки: {s.heals}/{MAX_HEALS}",
        ]
        y = 8
        for line in lines:
            surf = self.font.render(line, True, COLOR_TEXT)
            self.screen.blit(surf, (10, y))
            y += 22
        y = 8
        for i, m in enumerate(s.modules):
            txt = f"{i+1}. {MOD_NAMES[m.mtype]} L{m.level}  {int(m.hp)}/{int(m.max_hp)}"
            color = MOD_COLORS[m.mtype]
            surf = self.small_font.render(txt, True, color)
            self.screen.blit(surf, (WIDTH - surf.get_width() - 10, y))
            y += 18

    def draw_overlay(self, title, sub):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        t = self.big_font.render(title, True, COLOR_TEXT)
        self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 60))
        s = self.font.render(sub, True, COLOR_TEXT)
        self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, HEIGHT // 2))

    def draw_upgrade(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))
        title = self.big_font.render("УРОВЕНЬ! Выбери усиление (1/2/3)", True, COLOR_GOLD)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))
        for i, (label, _) in enumerate(self.upgrade_options):
            txt = f"{i+1}. {label}"
            surf = self.font.render(txt, True, COLOR_TEXT)
            self.screen.blit(surf, (WIDTH // 2 - 250, 220 + i * 60))

    def draw_station_menu(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        title = self.big_font.render("СТАНЦИЯ", True, COLOR_STATION)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))
        lost = len(self.snake.lost_modules)
        opts = [
            f"1. Вернуть потерянные модули (есть: {lost}, цена: {lost * 8})",
            "2. Переставить порядок модулей (бесплатно)",
            "3. Хил 25% от макс. HP головы",
            "Esc. Выйти",
        ]
        for i, line in enumerate(opts):
            surf = self.font.render(line, True, COLOR_TEXT)
            self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, 200 + i * 45))
        hint = self.small_font.render("Нажми 1/2/3 для выбора, Esc — выход", True, COLOR_DIM)
        self.screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 60))

    def draw_reorder(self):
        s = self.snake
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        title = self.big_font.render("ПЕРЕСТАНОВКА МОДУЛЕЙ", True, COLOR_GOLD)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 50))
        top = 160
        for i, m in enumerate(s.modules):
            selected = (i == self.reorder_selected)
            color = (255, 255, 0) if selected else COLOR_DIM
            prefix = "> " if selected else "  "
            txt = f"{prefix}{i+1}. {MOD_NAMES[m.mtype]} L{m.level}"
            surf = self.font.render(txt, True, color)
            self.screen.blit(surf, (WIDTH // 2 - 250, top + i * 30))
        lines = [
            "W — вверх, S — вниз: выбрать модуль",
            "Enter — поменять местами выбранный со следующим (сдвиг к хвосту)",
            "Esc — выйти",
        ]
        y = HEIGHT - 140
        for line in lines:
            surf = self.small_font.render(line, True, COLOR_TEXT)
            self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))
            y += 22

    def draw_game_over(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))
        t = self.big_font.render("ИГРА ОКОНЧЕНА", True, (255, 80, 80))
        self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 80))
        reason = "Голова уничтожена" if self.snake.head_hp <= 0 else "Не осталось модулей"
        r = self.font.render(reason, True, COLOR_TEXT)
        self.screen.blit(r, (WIDTH // 2 - r.get_width() // 2, HEIGHT // 2 - 20))
        s = self.font.render("R — рестарт", True, COLOR_GOLD)
        self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, HEIGHT // 2 + 30))

    def reorder_move(self, delta):
        if not self.snake.modules:
            return
        n = len(self.snake.modules)
        self.reorder_selected = clamp(self.reorder_selected + delta, 0, n - 1)

    def reorder_confirm(self):
        mods = self.snake.modules
        if len(mods) < 2:
            self.reorder_mode = False
            return
        i = self.reorder_selected
        if i < len(mods) - 1:
            mods[i], mods[i + 1] = mods[i + 1], mods[i]
            self.reorder_selected = i + 1
            self.msg("Сдвинуто")
        else:
            self.msg("Это последний модуль, дальше некуда")

    # --- Управление ---
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self.reset()
                return True
            if self.game_over:
                return True
            if self.show_upgrade:
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    idx = event.key - pygame.K_1
                    self.apply_upgrade(idx)
                return True
            if self.reorder_mode:
                if event.key == pygame.K_w:
                    self.reorder_move(-1)
                elif event.key == pygame.K_s:
                    self.reorder_move(1)
                elif event.key == pygame.K_RETURN:
                    self.reorder_confirm()
                elif event.key == pygame.K_ESCAPE:
                    self.reorder_mode = False
                    self.msg("Перестановка завершена")
                return True
            if self.station_menu:
                if event.key == pygame.K_1:
                    self.station_repair()
                elif event.key == pygame.K_2:
                    self.station_reorder_start()
                elif event.key == pygame.K_3:
                    self.station_heal()
                elif event.key == pygame.K_ESCAPE:
                    self.close_station_menu()
                return True
            if event.key == pygame.K_SPACE:
                if not self.game_over:
                    self.paused = not self.paused
                return True
            if self.paused:
                return True
            if event.key == pygame.K_w:
                self.snake.dir_target = pygame.Vector2(0, -1)
            elif event.key == pygame.K_s:
                self.snake.dir_target = pygame.Vector2(0, 1)
            elif event.key == pygame.K_a:
                self.snake.dir_target = pygame.Vector2(-1, 0)
            elif event.key == pygame.K_d:
                self.snake.dir_target = pygame.Vector2(1, 0)
        return True

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            for event in pygame.event.get():
                if not self.handle_event(event):
                    running = False
            self.update(dt)
            self.draw()
            pygame.display.flip()
        return

# ---------- Точка входа ----------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Рогалик-змейка: волны, модули, станции")
    game = Game(screen)
    game.run()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
