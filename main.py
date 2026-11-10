from kivy.config import Config
Config.set('graphics', 'multisamples', '0')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.core.text import Label as CoreLabel
from kivy.metrics import dp, sp
import math
import random
import os
import json
from enum import Enum, auto

# ---------- Пути для сохранений ----------
def get_save_path():
    app = App.get_running_app()
    base = app.user_data_dir if app else os.path.expanduser("~")
    try: os.makedirs(base, exist_ok=True)
    except Exception: base = os.path.expanduser("~")
    return os.path.join(base, "save.json")

# ---------- Константы ----------
CELL = 28
SNAKE_SPEED_BASE = 6.0
SNAKE_SPEED_PER_BOOST = 0.25
MAX_BOOSTERS = 10
MAX_HEALS = 10
HEAD_MAX_HP = 100

COLOR_BG = (14/255, 16/255, 24/255)
COLOR_HEAD = (140/255, 255/255, 180/255)
COLOR_BODY = (60/255, 170/255, 100/255)
COLOR_BODY_DARK = (40/255, 120/255, 70/255)
COLOR_ENEMY = (230/255, 80/255, 80/255)
COLOR_ENEMY_FAST = (255/255, 140/255, 60/255)
COLOR_ENEMY_TANK = (160/255, 60/255, 200/255)
COLOR_ENEMY_SHOOTER = (255/255, 80/255, 200/255)
COLOR_ENEMY_BULLET = (255/255, 100/255, 100/255)
COLOR_BULLET = (255/255, 240/255, 120/255)
COLOR_STATION = (255/255, 200/255, 60/255)
COLOR_TEXT = (230/255, 230/255, 230/255)
COLOR_GOLD = (255/255, 210/255, 80/255)

UNLOCKED_ENEMIES = set()
UNLOCKED_MODULES = set()

class ModType(Enum):
    PISTOL = auto(); RIFLE = auto(); SNIPER = auto(); SHIELD = auto(); HEAL = auto(); BOOSTER = auto(); AXES = auto(); TESLA = auto(); GRENADE = auto(); DRONE = auto()

MOD_DATA = {
    ModType.PISTOL:  {"name": "Пистолет", "hp": 40, "color": (100/255, 200/255, 255/255), "rarity": 1},
    ModType.RIFLE:   {"name": "Автомат", "hp": 35, "color": (100/255, 255/255, 200/255), "rarity": 2},
    ModType.SNIPER:  {"name": "Снайперка", "hp": 45, "color": (200/255, 120/255, 255/255), "rarity": 3},
    ModType.SHIELD:  {"name": "Щит", "hp": 60, "color": (255/255, 220/255, 100/255), "rarity": 3},
    ModType.HEAL:    {"name": "Хилка", "hp": 25, "color": (100/255, 255/255, 120/255), "rarity": 4},
    ModType.BOOSTER: {"name": "Ускоритель", "hp": 25, "color": (255/255, 140/255, 255/255), "rarity": 4},
    ModType.AXES:    {"name": "Два топора", "hp": 80, "color": (255/255, 255/255, 255/255), "rarity": 5},
    ModType.TESLA:   {"name": "Тесла", "hp": 30, "color": (150/255, 255/255, 255/255), "rarity": 3},
    ModType.GRENADE: {"name": "Гранатомет", "hp": 40, "color": (200/255, 100/255, 50/255), "rarity": 4},
    ModType.DRONE:   {"name": "Дрон", "hp": 50, "color": (180/255, 180/255, 180/255), "rarity": 5},
}
GUN_STATS = {ModType.PISTOL: (12, 340, 0.55), ModType.RIFLE: (6, 300, 0.13), ModType.SNIPER: (40, 620, 1.4), ModType.TESLA: (15, 250, 0.8), ModType.GRENADE: (30, 400, 1.2), ModType.DRONE: (8, 300, 0.4)}

class PlayerData:
    def __init__(self):
        self.money = 0; self.snake_skin = 0; self.gun_skin = 0
        self.owned_snake_skins = [0]; self.owned_gun_skins = [0]
        self.upg_legs = False; self.upg_skin = False; self.upg_start_heal = False; self.high_score = 0
        self.load()
    def load(self):
        global UNLOCKED_ENEMIES, UNLOCKED_MODULES
        path = get_save_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    UNLOCKED_ENEMIES = set(data.get("enemies", []))
                    for m_name in data.get("modules", []):
                        for m_enum in ModType:
                            if m_enum.name == m_name: UNLOCKED_MODULES.add(m_enum)
                    self.money = data.get("money", 0); self.snake_skin = data.get("snake_skin", 0); self.gun_skin = data.get("gun_skin", 0)
                    self.owned_snake_skins = data.get("owned_snake_skins", [0]); self.owned_gun_skins = data.get("owned_gun_skins", [0])
                    self.upg_legs = data.get("upg_legs", False); self.upg_skin = data.get("upg_skin", False); self.upg_start_heal = data.get("upg_start_heal", False)
                    self.high_score = data.get("high_score", 0)
            except Exception as e: print(f"Load error: {e}")
    def save(self):
        data = {"enemies": list(UNLOCKED_ENEMIES), "modules": [m.name for m in UNLOCKED_MODULES], "money": self.money, "snake_skin": self.snake_skin, "gun_skin": self.gun_skin, "owned_snake_skins": self.owned_snake_skins, "owned_gun_skins": self.owned_gun_skins, "upg_legs": self.upg_legs, "upg_skin": self.upg_skin, "upg_start_heal": self.upg_start_heal, "high_score": self.high_score}
        try:
            with open(get_save_path(), "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e: print(f"Save error: {e}")

PLAYER = PlayerData()

class Module:
    def __init__(self, mtype):
        self.mtype = mtype; self.hp = MOD_DATA[mtype]["hp"]; self.max_hp = self.hp; self.level = 1; self.cooldown = 0.0; self.phase = 0.0
    def is_gun(self): return self.mtype in GUN_STATS

class Enemy:
    def __init__(self, x, y, hp, speed, radius, damage, color, xp, money, kind, shoot_cd=0):
        self.x, self.y = x, y; self.hp, self.max_hp = hp, hp; self.speed, self.radius, self.damage = speed, radius, damage
        self.color, self.reward_xp, self.reward_money, self.kind = color, xp, money, kind; self.shoot_cd = shoot_cd

class Bullet:
    def __init__(self, x, y, vx, vy, dmg, life=1.2, radius=4, enemy=False, is_grenade=False):
        self.x, self.y, self.vx, self.vy, self.damage = x, y, vx, vy, dmg; self.life, self.radius, self.enemy, self.is_grenade = life, radius, enemy, is_grenade

class Pickup:
    def __init__(self, x, y, mtype): self.x, self.y, self.mtype, self.radius = x, y, mtype, 16
class Station:
    def __init__(self, x, y): self.x, self.y, self.radius, self.used = x, y, 26, False
class Explosion:
    def __init__(self, x, y, radius): self.x, self.y, self.radius, self.life = x, y, radius, 0.5

class Snake:
    def __init__(self):
        self.head = [0.0, 0.0]; self.dir = [1.0, 0.0]
        self.speed = SNAKE_SPEED_BASE * CELL * (1.05 if PLAYER.upg_legs else 1.0)
        hp = HEAD_MAX_HP + (20 if PLAYER.upg_skin else 0); self.head_hp, self.head_max_hp = hp, hp
        self.body = []; self.body_size = 1; self.modules = []; self.lost_modules = []; self.had_modules = False
        self.money, self.xp, self.level, self.xp_to_next = 0, 0, 1, 10; self.boosters, self.heals = 0, 0
        self.drone_pos = [0.0, 0.0]; self._init_body(); self.add_module(ModType.PISTOL)
        if PLAYER.upg_start_heal: self.add_module(ModType.HEAL)
    def _init_body(self):
        self.body.clear()
        for i in range(1, self.body_size + 1): self.body.append([self.head[0] - self.dir[0]*CELL*i, self.head[1] - self.dir[1]*CELL*i])
    def _grow_body(self):
        if self.body:
            last, prev = self.body[-1], self.body[-2] if len(self.body) >= 2 else self.head
            d = [last[0]-prev[0], last[1]-prev[1]]; l = math.hypot(*d) or 1
            self.body.append([last[0] + d[0]/l*CELL, last[1] + d[1]/l*CELL])
        else: self.body.append([self.head[0] - self.dir[0]*CELL, self.head[1] - self.dir[1]*CELL])
        self.body_size = len(self.body)
    def module_positions(self):
        res = []
        for i in range(len(self.modules)):
            if i < len(self.body): res.append(self.body[i])
            elif self.body: res.append(self.body[-1])
            else: res.append(self.head)
        return res
    def add_module(self, mtype):
        if mtype == ModType.BOOSTER and self.boosters >= MAX_BOOSTERS: return False
        if mtype == ModType.HEAL and self.heals >= MAX_HEALS: return False
        self.modules.append(Module(mtype)); UNLOCKED_MODULES.add(mtype)
        if mtype == ModType.BOOSTER: self.boosters += 1
        if mtype == ModType.HEAL: self.heals += 1
        self.had_modules = True
        if mtype == ModType.DRONE: self.drone_pos = list(self.head)
        while len(self.body) < len(self.modules): self._grow_body()
        return True
    def damage_chain(self, idx):
        removed = self.modules[idx:]; self.modules = self.modules[:idx]
        for m in removed:
            self.lost_modules.append(m.mtype)
            if m.mtype == ModType.BOOSTER: self.boosters = max(0, self.boosters-1)
            if m.mtype == ModType.HEAL: self.heals = max(0, self.heals-1)

# ---------- Игровой виджет ----------
class GameWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.reset()
        # ВАЖНО: Запускаем таймер только после того, как виджет получит размеры
        self.bind(size=self._start_clock, pos=self._start_clock)
        self.menu_btns = []
        for i in range(4):
            btn = Button(text="", size_hint=(None, None), size=(10, 10), background_color=(0,0,0,0), opacity=0)
            btn.bind(on_press=lambda inst, idx=i: self.menu_action(idx)); self.menu_btns.append(btn); self.add_widget(btn)
        self.pause_button = Button(text="II", size_hint=(None, None), background_color=(0.3, 0.3, 0.3, 0.7), font_size=sp(20))
        self.pause_button.bind(on_press=self.toggle_pause); self.add_widget(self.pause_button)

    def _start_clock(self, *args):
        if self.width > 0 and self.height > 0 and not hasattr(self, '_clock_started'):
            self._clock_started = True
            Clock.schedule_interval(self.update, 1/60)
            self._layout_static_widgets()

    def _layout_static_widgets(self, *args):
        if not self.width or not self.height: return
        size = dp(50); margin = dp(10)
        self.pause_button.size = (size, size); self.pause_button.pos = (margin, self.height - size - margin)

    def reset(self):
        self.snake = Snake(); self.enemies, self.bullets, self.pickups, self.stations = [], [], [], []
        self.lightning_lines, self.explosions = [], []
        self.wave, self.wave_timer = 0, 2.0; self.pickup_timer, self.station_timer = 6.0, 25.0
        self.paused, self.game_over, self.show_upgrade = False, False, False
        self.station_menu, self.reorder_mode = False, False; self.upgrade_options = []
        self.message, self.message_timer = "", 0.0; self.cam_x, self.cam_y = 0.0, 0.0

    def msg(self, t, dur=2.0): self.message, self.message_timer = t, dur
    def toggle_pause(self, instance):
        if not self.game_over: self.paused = not self.paused
    def menu_action(self, idx):
        if self.show_upgrade: self.apply_upgrade(idx)
        elif self.station_menu:
            if idx == 0: self.station_repair()
            elif idx == 1: self.station_menu = False; self.reorder_mode = True; self._layout_menu_buttons(min(6, len(self.snake.modules)), 0.85, True)
            elif idx == 2: self.station_heal()
            elif idx == 3: self.close_menu()
        elif self.reorder_mode:
            if idx < len(self.snake.modules) - 1:
                mods = self.snake.modules; mods[idx], mods[idx+1] = mods[idx+1], mods[idx]
    def close_menu(self):
        self.station_menu = False; self.reorder_mode = False; self.show_upgrade = False
        for btn in self.menu_btns: btn.opacity = 0
    def open_upgrade(self):
        self.show_upgrade = True; opts, existing = [], {m.mtype for m in self.snake.modules}
        for t in existing: opts.append((f"Усилить: {MOD_DATA[t]['name']}", ('upgrade', t)))
        pool = []
        for m, data in MOD_DATA.items():
            if m in existing: continue
            if m == ModType.HEAL and self.snake.heals >= MAX_HEALS: continue
            if m == ModType.BOOSTER and self.snake.boosters >= MAX_BOOSTERS: continue
            weight = 1 if data["rarity"] == 5 else (3 if data["rarity"] == 4 else (5 if data["rarity"] == 3 else (10 if data["rarity"] == 2 else 20)))
            pool.extend([m] * weight)
        random.shuffle(pool)
        for t in pool[:3]: opts.append((f"Новый: {MOD_DATA[t]['name']}", ('add', t)))
        random.shuffle(opts); self.upgrade_options = opts[:3]; self._layout_menu_buttons(len(self.upgrade_options), 0.55)
    def apply_upgrade(self, idx):
        if 0 <= idx < len(self.upgrade_options):
            _, (kind, t) = self.upgrade_options[idx]; s = self.snake
            if kind == 'upgrade':
                for m in s.modules:
                    if m.mtype == t: m.level += 1; m.max_hp *= 1.2; m.hp = m.max_hp; break
            else: s.add_module(t)
        self.show_upgrade = False
    def open_station(self, st): self.station_menu, st.used = True, True; self._layout_menu_buttons(4, 0.62)
    def station_repair(self):
        s = self.snake
        if not s.lost_modules: self.msg("Нет потерянных"); self.close_menu(); return
        cost = len(s.lost_modules)*8
        if s.money < cost: self.msg(f"Нужно {cost}$"); self.close_menu(); return
        s.money -= cost; restored, s.lost_modules = s.lost_modules[:], []; cnt = 0
        for t in restored:
            if s.add_module(t): cnt += 1
        self.msg(f"Восстановлено: {cnt}"); self.close_menu()
    def station_heal(self): self.snake.head_hp = min(self.snake.head_max_hp, self.snake.head_hp + self.snake.head_max_hp*0.25); self.msg("Хил 25%"); self.close_menu()
    def _layout_menu_buttons(self, count, center_y_ratio=0.55, from_top=False):
        btn_w = self.width * 0.8; btn_h = dp(50); x = (self.width - btn_w) / 2
        for i in range(4):
            if i < count:
                y = self.height * center_y_ratio - i * (btn_h + dp(10)) - btn_h/2 if not from_top else self.height * center_y_ratio - i * (btn_h + dp(10))
                self.menu_btns[i].size = (btn_w, btn_h); self.menu_btns[i].pos = (x, y); self.menu_btns[i].opacity = 1
            else: self.menu_btns[i].opacity = 0

    def update(self, dt):
        if self.width <= 0 or self.height <= 0: return  # Защита от нулевых размеров
        if self.message_timer > 0: self.message_timer -= dt
        if self.game_over or self.paused or self.show_upgrade or self.station_menu or self.reorder_mode: self.redraw(); return
        
        # ... (ОСТАЛЬНАЯ ЛОГИКА ИГРЫ БЕЗ ИЗМЕНЕНИЙ) ...
        s = self.snake
        speed = s.speed * (1 + SNAKE_SPEED_PER_BOOST * s.boosters)
        s.head[0] += s.dir[0] * speed * dt; s.head[1] += s.dir[1] * speed * dt
        target = s.head
        for i in range(len(s.body)):
            to = [target[0]-s.body[i][0], target[1]-s.body[i][1]]; d = math.hypot(*to)
            if d > CELL: s.body[i] = [target[0]-to[0]/d*CELL, target[1]-to[1]/d*CELL]
            target = s.body[i]
        for m in s.modules: m.cooldown = max(0, m.cooldown-dt); m.phase += dt
        mpos = s.module_positions()
        for i, m in enumerate(s.modules):
            if not m.is_gun() or m.cooldown > 0: continue
            pos = mpos[i]
            if m.mtype == ModType.DRONE:
                snake_len = len(s.body) * CELL; radius = max(50, snake_len / 2)
                nearest_e, best_d = None, float('inf')
                for e in self.enemies:
                    d = (s.head[0]-e.x)**2 + (s.head[1]-e.y)**2
                    if d < best_d: best_d, nearest_e = d, e
                target_pos = [nearest_e.x, nearest_e.y] if nearest_e else s.head
                dir_to = [target_pos[0]-s.drone_pos[0], target_pos[1]-s.drone_pos[1]]; dl = math.hypot(*dir_to)
                if dl > 5: s.drone_pos = [s.drone_pos[0]+dir_to[0]/dl*400*dt, s.drone_pos[1]+dir_to[1]/dl*400*dt]
                dist_from_head = [s.drone_pos[0]-s.head[0], s.drone_pos[1]-s.head[1]]; dl2 = math.hypot(*dist_from_head)
                if dl2 > radius: s.drone_pos = [s.head[0]+dist_from_head[0]/dl2*radius, s.head[1]+dist_from_head[1]/dl2*radius]
                pos = s.drone_pos
            best, target_e = None, None; rng = GUN_STATS[m.mtype][1]
            for e in self.enemies:
                d = (pos[0]-e.x)**2 + (pos[1]-e.y)**2
                if d <= rng*rng and (best is None or d < best): best, target_e = d, e
            if target_e:
                dmg, _, cd = GUN_STATS[m.mtype]; dmg *= 1 + 0.25*(m.level-1); ang = math.atan2(target_e.y-pos[1], target_e.x-pos[0])
                if m.mtype == ModType.GRENADE: self.bullets.append(Bullet(pos[0], pos[1], math.cos(ang)*600, math.sin(ang)*600, dmg, 1.5, 6, False, True))
                elif m.mtype == ModType.TESLA:
                    chain = [target_e]; cur = target_e
                    for _ in range(3):
                        bd, nt = 150**2, None
                        for e in self.enemies:
                            if e not in chain:
                                d = (cur.x-e.x)**2 + (cur.y-e.y)**2
                                if d < bd: bd, nt = d, e
                        if nt: chain.append(nt); cur = nt
                        else: break
                    for ct in chain:
                        ct.hp -= dmg; self.lightning_lines.append((pos[0], pos[1], ct.x, ct.y, 0.1))
                else: self.bullets.append(Bullet(pos[0], pos[1], math.cos(ang)*900, math.sin(ang)*900, dmg))
                m.cooldown = cd
        for i, m in enumerate(s.modules):
            if m.mtype == ModType.HEAL and m.cooldown <= 0:
                m.cooldown = 1.5; heal = 0.5 + 0.3*m.level; s.head_hp = min(s.head_max_hp, s.head_hp+heal); mp = mpos[i]
                for j, other in enumerate(s.modules):
                    if other is m: continue
                    p = mpos[j]
                    if (mp[0]-p[0])**2 + (mp[1]-p[1])**2 <= (70+5*m.level)**2: other.hp = min(other.max_hp, other.hp+heal*0.4)
        for i, m in enumerate(s.modules):
            if m.mtype == ModType.AXES:
                mp = mpos[i]; orbit = 55 + 5*m.level
                for k in range(2):
                    a = m.phase*3.0 + k*math.pi; ax, ay = mp[0]+math.cos(a)*orbit, mp[1]+math.sin(a)*orbit
                    for e in self.enemies:
                        if (ax-e.x)**2 + (ay-e.y)**2 <= (e.radius+14)**2 and m.cooldown <= 0:
                            e.hp -= 8 + 4*m.level; dx, dy = e.x-ax, e.y-ay; dl = math.hypot(dx, dy) or 1
                            e.x += dx/dl*18; e.y += dy/dl*18; m.cooldown = 0.25
        for i, m in enumerate(s.modules):
            p = mpos[i]
            for e in self.enemies:
                if (p[0]-e.x)**2 + (p[1]-e.y)**2 <= (e.radius+12)**2: m.hp -= e.damage*dt*0.8
            if m.hp <= 0: s.damage_chain(i); break
        if s.had_modules and not s.modules: self.game_over = True
        for e in list(self.enemies):
            ang = math.atan2(s.head[1]-e.y, s.head[0]-e.x); d = math.hypot(s.head[0]-e.x, s.head[1]-e.y)
            if e.kind == "shooter" and d < 280: ang += math.pi
            e.x += math.cos(ang)*e.speed*dt; e.y += math.sin(ang)*e.speed*dt
            if e.kind == "shooter":
                e.shoot_cd -= dt
                if e.shoot_cd <= 0 and d < 500:
                    e.shoot_cd = 2.0; a = math.atan2(s.head[1]-e.y, s.head[0]-e.x)
                    self.bullets.append(Bullet(e.x, e.y, math.cos(a)*350, math.sin(a)*350, e.damage, 2.0, 5, True))
            hit_mod = False
            for i, m in enumerate(s.modules):
                if (e.x-mpos[i][0])**2 + (e.y-mpos[i][1])**2 <= (e.radius+CELL*0.5)**2:
                    m.hp -= e.damage*dt*2.5; hit_mod = True
                    dx, dy = e.x-mpos[i][0], e.y-mpos[i][1]; dl = math.hypot(dx,dy) or 1
                    e.x += dx/dl*10; e.y += dy/dl*10; break
            if not hit_mod and (e.x-s.head[0])**2 + (e.y-s.head[1])**2 <= (e.radius+CELL*0.6)**2:
                s.head_hp -= e.damage*dt*2.5; dx, dy = e.x-s.head[0], e.y-s.head[1]; dl = math.hypot(dx,dy) or 1
                e.x += dx/dl*10; e.y += dy/dl*10
        if s.head_hp <= 0: self.game_over = True
        for b in list(self.bullets):
            b.x += b.vx*dt; b.y += b.vy*dt; b.life -= dt
            if b.life <= 0:
                if b.is_grenade:
                    self.explosions.append(Explosion(b.x, b.y, 80))
                    for e in self.enemies:
                        if (b.x-e.x)**2 + (b.y-e.y)**2 <= (80+e.radius)**2: e.hp -= b.damage
                self.bullets.remove(b); continue
            hit = False
            if b.enemy:
                if (b.x-s.head[0])**2 + (b.y-s.head[1])**2 <= (b.radius+CELL*0.6)**2: s.head_hp -= b.damage; hit = True
                if not hit:
                    for i, m in enumerate(s.modules):
                        if (b.x-mpos[i][0])**2 + (b.y-mpos[i][1])**2 <= (b.radius+CELL*0.5)**2: m.hp -= b.damage; hit = True; break
            else:
                for e in list(self.enemies):
                    if (b.x-e.x)**2 + (b.y-e.y)**2 <= (e.radius+b.radius)**2:
                        if b.is_grenade:
                            self.explosions.append(Explosion(b.x, b.y, 80))
                            for ee in self.enemies:
                                if (b.x-ee.x)**2 + (b.y-ee.y)**2 <= (80+ee.radius)**2: ee.hp -= b.damage
                        else: e.hp -= b.damage
                        hit = True; break
            if hit: self.bullets.remove(b)
        for e in list(self.enemies):
            if e.hp <= 0:
                self.enemies.remove(e); s.xp += e.reward_xp; s.money += e.reward_money
                if s.xp >= s.xp_to_next:
                    s.xp -= s.xp_to_next; s.level += 1; s.xp_to_next = int(s.xp_to_next*1.35+4); self.open_upgrade()
                    if self.show_upgrade: return
        for p in list(self.pickups):
            touch = (p.x-s.head[0])**2 + (p.y-s.head[1])**2 <= (p.radius+CELL)**2
            if not touch:
                for b in s.body:
                    if (p.x-b[0])**2 + (p.y-b[1])**2 <= (p.radius+CELL*0.7)**2: touch = True; break
            if touch:
                if s.add_module(p.mtype): self.pickups.remove(p); self.msg(f"+{MOD_DATA[p.mtype]['name']}")
                else: self.msg("Лимит типа достигнут", 1.0)
        for st in self.stations:
            if not st.used and (st.x-s.head[0])**2 + (st.y-s.head[1])**2 <= (st.radius+CELL)**2: self.open_station(st); return
        self.wave_timer -= dt
        if self.wave_timer <= 0: self.spawn_wave(); self.wave_timer = max(6.0, 12.0-self.wave*0.3)
        self.pickup_timer -= dt
        if self.pickup_timer <= 0: self.spawn_pickup(); self.pickup_timer = random.uniform(6,11)
        self.station_timer -= dt
        if self.station_timer <= 0: self.spawn_station(); self.station_timer = random.uniform(30,50)
        self.cam_x += (s.head[0] - self.width/2 - self.cam_x) * 0.15; self.cam_y += (s.head[1] - self.height/2 - self.cam_y) * 0.15
        self.lightning_lines = [(x1,y1,x2,y2,l-dt) for x1,y1,x2,y2,l in self.lightning_lines if l > 0]
        self.explosions = [ex for ex in self.explosions if ex.life > 0]
        for ex in self.explosions: ex.life -= dt
        self.redraw()

    # ... (ОСТАЛЬНЫЕ МЕТОДЫ SPWAN, REDRAW, ON_TOUCH БЕЗ ИЗМЕНЕНИЙ) ...
    def _random_ring_pos(self, rmin, rmax):
        ang = random.uniform(0, math.tau); r = random.uniform(rmin, rmax)
        return self.snake.head[0]+math.cos(ang)*r, self.snake.head[1]+math.sin(ang)*r
    def spawn_wave(self):
        self.wave += 1; count = min(3+self.wave*2, 30); base_hp = 12+self.wave*6
        for _ in range(count):
            x, y = self._random_ring_pos(280, 600); roll, w = random.random(), self.wave
            if w >= 2 and roll < 0.15: e = Enemy(x, y, base_hp*2.5, 40+w*1.5, 18, 14, COLOR_ENEMY_TANK, 4, 4, "tank"); UNLOCKED_ENEMIES.add("TANK")
            elif w >= 3 and roll < 0.30: e = Enemy(x, y, base_hp*0.9, 55+w*2, 13, 6, COLOR_ENEMY_SHOOTER, 3, 3, "shooter", 1.5); UNLOCKED_ENEMIES.add("SHOOTER")
            elif roll < 0.55: e = Enemy(x, y, base_hp*0.7, 100+w*3, 10, 6, COLOR_ENEMY_FAST, 2, 2, "fast"); UNLOCKED_ENEMIES.add("FAST")
            else: e = Enemy(x, y, base_hp, 60+w*2, 13, 8, COLOR_ENEMY, 1, 1, "normal"); UNLOCKED_ENEMIES.add("NORMAL")
            self.enemies.append(e)
        self.msg(f"Волна {self.wave}")
    def spawn_pickup(self):
        if len(self.pickups) > 5: return
        pool = []
        for m, data in MOD_DATA.items():
            if m == ModType.HEAL and self.snake.heals >= MAX_HEALS: continue
            if m == ModType.BOOSTER and self.snake.boosters >= MAX_BOOSTERS: continue
            weight = 1 if data["rarity"] == 5 else (3 if data["rarity"] == 4 else (5 if data["rarity"] == 3 else (10 if data["rarity"] == 2 else 20)))
            pool.extend([m] * weight)
        if not pool: return
        x, y = self._random_ring_pos(140, 450); self.pickups.append(Pickup(x, y, random.choice(pool)))
    def spawn_station(self):
        if any(not s.used for s in self.stations): return
        self.stations = [s for s in self.stations if not s.used]
        x, y = self._random_ring_pos(200, 500); self.stations.append(Station(x, y))
    def on_touch_down(self, touch):
        if self.show_upgrade or self.station_menu or self.reorder_mode: return super().on_touch_down(touch)
        jx = self.width * 0.82; jy = self.height * 0.15
        if (touch.x - jx)**2 + (touch.y - jy)**2 <= (min(self.width, self.height) * 0.14)**2:
            touch.ud['joystick'] = True; self._handle_joystick(touch.x, touch.y, jx, jy); return True
        return super().on_touch_down(touch)
    def on_touch_move(self, touch):
        if touch.ud.get('joystick'): self._handle_joystick(touch.x, touch.y, self.width * 0.82, self.height * 0.15); return True
        return super().on_touch_move(touch)
    def _handle_joystick(self, x, y, cx, cy):
        dx, dy = x-cx, y-cy
        if math.hypot(dx, dy) > 30:
            l = math.hypot(dx, dy); self.snake.dir = [dx/l, dy/l]
    def redraw(self):
        self.canvas.clear()
        with self.canvas:
            Color(*COLOR_BG); Rectangle(pos=(0,0), size=(self.width, self.height))
            Color(1, 1, 1, 0.03)
            for i in range(-100, 100):
                x = (i * 100 - self.cam_x) % (self.width + 200) - 100; y = (i * 100 - self.cam_y) % (self.height + 200) - 100
                Line(points=[x, 0, x, self.height], width=1); Line(points=[0, y, self.width, y], width=1)
            def screen(x, y): return x - self.cam_x, y - self.cam_y
            for st in self.stations:
                if not st.used:
                    sx, sy = screen(st.x, st.y); Color(*COLOR_STATION); Ellipse(pos=(sx-st.radius, sy-st.radius), size=(st.radius*2, st.radius*2))
            for p in self.pickups:
                sx, sy = screen(p.x, p.y); Color(*MOD_DATA[p.mtype]["color"]); Ellipse(pos=(sx-p.radius, sy-p.radius), size=(p.radius*2, p.radius*2))
            for e in self.enemies:
                sx, sy = screen(e.x, e.y); Color(*e.color); Ellipse(pos=(sx-e.radius, sy-e.radius), size=(e.radius*2, e.radius*2))
                Color(0.23, 0, 0); Rectangle(pos=(sx-14, sy-e.radius-8), size=(28, 4))
                Color(0, 0.86, 0.24); Rectangle(pos=(sx-14, sy-e.radius-8), size=(28*max(0,min(1,e.hp/e.max_hp)), 4))
            for b in self.bullets:
                sx, sy = screen(b.x, b.y); Color(*(COLOR_ENEMY_BULLET if b.enemy else (0.78, 0.39, 0.19) if b.is_grenade else COLOR_BULLET)); Ellipse(pos=(sx-b.radius, sy-b.radius), size=(b.radius*2, b.radius*2))
            s = self.snake; head_c, body_c, dark_c = COLOR_HEAD, COLOR_BODY, COLOR_BODY_DARK
            if PLAYER.snake_skin == 1: head_c, body_c, dark_c = (1, 0.4, 0.4), (0.78, 0.2, 0.2), (0.58, 0.1, 0.1)
            elif PLAYER.snake_skin == 2: head_c, body_c, dark_c = (0.4, 0.4, 1), (0.2, 0.2, 0.78), (0.1, 0.1, 0.58)
            elif PLAYER.snake_skin == 3: head_c, body_c, dark_c = (1, 1, 0.4), (1, 0.78, 0.2), (0.78, 0.58, 0.1)
            for b in s.body:
                sx, sy = screen(b[0], b[1]); Color(*dark_c); Rectangle(pos=(sx-CELL*0.45, sy-CELL*0.45), size=(CELL*0.9, CELL*0.9))
                Color(*body_c); Rectangle(pos=(sx-CELL*0.38, sy-CELL*0.38), size=(CELL*0.76, CELL*0.76))
            hx, hy = screen(s.head[0], s.head[1]); Color(*body_c); Ellipse(pos=(hx-CELL*0.8, hy-CELL*0.8), size=(CELL*1.6, CELL*1.6)); Color(*head_c); Ellipse(pos=(hx-CELL*0.7, hy-CELL*0.7), size=(CELL*1.4, CELL*1.4))
            mpos = s.module_positions()
            for i, m in enumerate(s.modules):
                if i >= len(mpos): continue
                mx, my = screen(mpos[i][0], mpos[i][1]); col = MOD_DATA[m.mtype]["color"]
                if PLAYER.gun_skin == 1: col = (min(1, col[0]*1.5), min(1, col[1]*1.5), min(1, col[2]*1.5))
                elif PLAYER.gun_skin == 2: col = (1, 0.78, 0.2)
                Color(0,0,0); Rectangle(pos=(mx-CELL*0.32, my-CELL*0.32), size=(CELL*0.64, CELL*0.64)); Color(*col); Rectangle(pos=(mx-CELL*0.3, my-CELL*0.3), size=(CELL*0.6, CELL*0.6))
                if m.mtype == ModType.SHIELD:
                    for k in range(2):
                        a = m.phase*2.5 + k*math.pi; shx, shy = mx+math.cos(a)*30, my+math.sin(a)*30
                        Color(1, 0.94, 0.7); Ellipse(pos=(shx-10, shy-10), size=(20, 20)); Color(1, 0.7, 0); Line(circle=(shx, shy, 10), width=2)
                elif m.mtype == ModType.AXES:
                    for k in range(2):
                        a = m.phase*3.0 + k*math.pi; ax, ay = mx+math.cos(a)*55, my+math.sin(a)*55
                        Color(0.55, 0.27, 0.07); Line(points=[ax, ay, ax+math.cos(a+1.57)*15, ay+math.sin(a+1.57)*15], width=4); Color(0.78, 0.78, 0.78); Ellipse(pos=(ax-8, ay-8), size=(16, 16))
                elif m.mtype == ModType.DRONE:
                    dx, dy = screen(s.drone_pos[0], s.drone_pos[1]); Color(0.6, 0.6, 0.6); Rectangle(pos=(dx-10, dy-10), size=(20, 20)); Color(1, 1, 1); Line(rectangle=(dx-10, dy-10, 20, 20), width=2)
                Color(0.23, 0, 0); Rectangle(pos=(mx-14, my+CELL*0.5), size=(28, 4)); Color(0, 0.86, 0.24); Rectangle(pos=(mx-14, my+CELL*0.5), size=(28*max(0,min(1,m.hp/m.max_hp)), 4))
            for x1,y1,x2,y2,l in self.lightning_lines:
                sx1, sy1 = screen(x1,y1); sx2, sy2 = screen(x2,y2); Color(0.6, 1, 1); Line(points=[sx1,sy1, sx1+(sx2-sx1)/2+random.randint(-10,10), sy1+(sy2-sy1)/2+random.randint(-10,10), sx2,sy2], width=2)
            for ex in self.explosions:
                sx, sy = screen(ex.x, ex.y); r = ex.radius * (ex.life/0.5); Color(1, 0.39, 0.19, ex.life/0.5); Ellipse(pos=(sx-r, sy-r), size=(r*2, r*2))
            jx, jy = self.width*0.82, self.height*0.15; r = min(self.width, self.height)*0.14
            Color(0.2, 0.25, 0.35, 0.5); Ellipse(pos=(jx-r, jy-r), size=(r*2, r*2)); Color(0.6, 0.7, 0.8); Line(circle=(jx, jy, r), width=4); Color(0.9, 0.9, 0.3); Ellipse(pos=(jx+s.dir[0]*r*0.5-30, jy+s.dir[1]*r*0.5-30), size=(60, 60))
            if self.show_upgrade or self.station_menu or self.reorder_mode:
                Color(0, 0, 0, 0.8); Rectangle(pos=(0,0), size=(self.width, self.height))
                title_text = "УРОВЕНЬ!" if self.show_upgrade else "СТАНЦИЯ" if self.station_menu else "ПЕРЕСТАНОВКА"
                lbl = CoreLabel(text=title_text, font_size=sp(24), bold=True, color=COLOR_GOLD); lbl.refresh(); Color(1,1,1); Rectangle(texture=lbl.texture, pos=(self.width/2-lbl.texture.width/2, self.height*0.75), size=lbl.texture.size)
                opts = []
                if self.show_upgrade: opts = [o[0] for o in self.upgrade_options]
                elif self.station_menu: opts = [f"1. Восстановить ({len(s.lost_modules)*8}$)", "2. Переставить", "3. Лечение", "4. Выйти"]
                else: opts = [f"{i+1}. {MOD_DATA[m.mtype]['name']} L{m.level}" for i,m in enumerate(s.modules)]
                for i, text in enumerate(opts):
                    if i >= 4: break
                    btn = self.menu_btns[i]; bx, by = btn.pos; bw, bh = btn.size
                    Color(1, 1, 1, 0.2); Rectangle(pos=(bx, by), size=(bw, bh)); Color(1, 1, 1); Line(rectangle=(bx, by, bw, bh), width=2)
                    lbl2 = CoreLabel(text=text, font_size=sp(16), color=(1,1,1,1)); lbl2.refresh(); Color(1,1,1); Rectangle(texture=lbl2.texture, pos=(bx+bw/2-lbl2.texture.width/2, by+bh/2-lbl2.texture.height/2), size=lbl2.texture.size)
            if self.paused:
                Color(0, 0, 0, 0.6); Rectangle(pos=(0,0), size=(self.width, self.height)); lbl = CoreLabel(text="ПАУЗА", font_size=sp(40), bold=True, color=(1,1,1,1)); lbl.refresh(); Color(1,1,1); Rectangle(texture=lbl.texture, pos=(self.width/2-lbl.texture.width/2, self.height/2), size=lbl.texture.size)
            if self.message_timer > 0:
                lbl = CoreLabel(text=self.message, font_size=sp(20), bold=True, color=COLOR_GOLD); lbl.refresh(); Color(1,1,1); Rectangle(texture=lbl.texture, pos=(self.width/2-lbl.texture.width/2, self.height*0.85), size=lbl.texture.size)

# ---------- ГЛАВНОЕ МЕНЮ (переделано на BoxLayout) ----------
class MainMenu(BoxLayout):
    def __init__(self, start_callback, **kwargs):
        super().__init__(orientation='vertical', padding=dp(50), spacing=dp(20), **kwargs)
        
        with self.canvas.before:
            Color(*COLOR_BG); self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        
        # Заголовок
        title = Label(text="ЗМЕЙКА-РОГАЛИК", font_size=sp(40), bold=True, color=COLOR_GOLD, size_hint_y=0.2)
        self.add_widget(title)
        
        # Пустое место для отступа
        self.add_widget(Widget(size_hint_y=0.1))
        
        # Кнопка Играть
        btn_start = Button(text="ИГРАТЬ", size_hint=(None, None), size=(dp(250), dp(70)), 
                           pos_hint={'center_x': 0.5}, background_color=(0.2, 0.7, 0.4, 1), font_size=sp(24))
        btn_start.bind(on_press=start_callback)
        self.add_widget(btn_start)
        
        # Кнопка Выйти
        btn_exit = Button(text="ВЫЙТИ", size_hint=(None, None), size=(dp(250), dp(70)), 
                          pos_hint={'center_x': 0.5}, background_color=(0.8, 0.2, 0.2, 1), font_size=sp(24))
        btn_exit.bind(on_press=self.exit_app)
        self.add_widget(btn_exit)
        
        # Статистика внизу
        stats_text = f"Баланс: {PLAYER.money} $\nРекорд: {PLAYER.high_score} волн"
        stats = Label(text=stats_text, font_size=sp(14), color=COLOR_TEXT, size_hint_y=0.2)
        self.add_widget(stats)
    
    def update_bg(self, *args): 
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
    def exit_app(self, instance): 
        App.get_running_app().stop()

# ---------- Приложение ----------
class SnakeApp(App):
    def build(self):
        self.root = FloatLayout()
        self.menu = MainMenu(start_callback=self.start_game)
        self.root.add_widget(self.menu)
        return self.root

    def start_game(self, instance):
        if self.menu in self.root.children:
            self.root.remove_widget(self.menu)
        
        self.game = GameWidget(size_hint=(1,1), pos_hint={'x':0, 'y':0})
        self.root.add_widget(self.game)

        self.hud = Label(text="", pos_hint={'right': 0.98, 'top': 0.98}, size_hint=(0.4, 0.1), font_size=sp(16), bold=True, halign='right', valign='top')
        self.hud.bind(size=self.hud.setter('text_size')); self.root.add_widget(self.hud)

        self.module_list = Label(text="", pos_hint={'right': 0.98, 'top': 0.85}, size_hint=(0.4, 0.4), font_size=sp(12), bold=True, halign='right', valign='top')
        self.module_list.bind(size=self.module_list.setter('text_size')); self.root.add_widget(self.module_list)

        Clock.schedule_interval(self.update_hud, 0.1)

    def update_hud(self, dt):
        if not hasattr(self, 'game') or not self.game: return
        g = self.game; s = g.snake
        self.hud.text = f"HP: {int(s.head_hp)}/{int(s.head_max_hp)} | Lvl: {s.level}\nWave: {g.wave} | $: {s.money}"
        mod_text = "Модули:\n"
        for i, m in enumerate(s.modules):
            mod_text += f"{i+1}. {MOD_DATA[m.mtype]['name']} L{m.level}\n"
        self.module_list.text = mod_text

    def on_stop(self):
        if hasattr(self, 'game') and self.game:
            PLAYER.money += self.game.snake.money
            if self.game.wave > PLAYER.high_score: PLAYER.high_score = self.game.wave
            PLAYER.save()

if __name__ == '__main__':
    SnakeApp().run()
