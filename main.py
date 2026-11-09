from kivy.config import Config
Config.set('graphics', 'multisamples', '0')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.core.text import Label as CoreLabel
import math
import random
import os
import json

# ---------- Константы ----------
CELL = 24
SNAKE_SPEED_BASE = 6.0
SNAKE_SPEED_PER_BOOST = 0.25
MAX_BOOSTERS = 10
MAX_HEALS = 10
HEAD_MAX_HP = 100

C_BG = (0.05, 0.06, 0.09)
C_HEAD = (0.55, 1.0, 0.7)
C_BODY = (0.23, 0.67, 0.39)
C_ENEMY = (0.9, 0.31, 0.31)
C_ENEMY_FAST = (1.0, 0.55, 0.23)
C_ENEMY_TANK = (0.63, 0.23, 0.78)
C_ENEMY_SHOOTER = (1.0, 0.31, 0.78)
C_BULLET = (1.0, 0.94, 0.47)
C_ENEMY_BULLET = (1.0, 0.39, 0.39)
C_STATION = (1.0, 0.78, 0.23)
C_RED = (0.6, 0, 0)
C_GREEN = (0, 0.86, 0.24)
C_SHIELD = (1.0, 0.86, 0.39)
C_AXES = (1.0, 0.39, 0.39)

MOD_PISTOL, MOD_RIFLE, MOD_SNIPER = "Pistol", "Rifle", "Sniper"
MOD_SHIELD, MOD_HEAL, MOD_BOOSTER, MOD_AXES = "Shield", "Heal", "Booster", "Axes"

MOD_NAMES = {MOD_PISTOL: "Пистолет", MOD_RIFLE: "Автомат", MOD_SNIPER: "Снайперка",
             MOD_SHIELD: "Щит", MOD_HEAL: "Хилка", MOD_BOOSTER: "Ускоритель", MOD_AXES: "Топоры"}
MOD_BASE_HP = {MOD_PISTOL: 40, MOD_RIFLE: 35, MOD_SNIPER: 45, MOD_SHIELD: 60, MOD_HEAL: 25, MOD_BOOSTER: 25, MOD_AXES: 80}
MOD_COLORS = {MOD_PISTOL: (0.39, 0.78, 1.0), MOD_RIFLE: (0.39, 1.0, 0.78), MOD_SNIPER: (0.78, 0.47, 1.0),
              MOD_SHIELD: (1.0, 0.86, 0.39), MOD_HEAL: (0.39, 1.0, 0.47), MOD_BOOSTER: (1.0, 0.55, 1.0), MOD_AXES: (1.0, 0.39, 0.39)}
GUN_STATS = {MOD_PISTOL: (12, 340, 0.55), MOD_RIFLE: (6, 300, 0.13), MOD_SNIPER: (40, 620, 1.4)}


def get_save_path():
    app = App.get_running_app()
    base = app.user_data_dir if app else os.path.expanduser("~")
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        base = os.path.expanduser("~")
    return os.path.join(base, "save.json")


class Module:
    def __init__(self, mtype):
        self.mtype = mtype
        self.hp = MOD_BASE_HP[mtype]
        self.max_hp = self.hp
        self.level = 1
        self.cooldown = 0.0
        self.phase = 0.0
    def is_gun(self): return self.mtype in GUN_STATS


class Enemy:
    def __init__(self, x, y, hp, speed, radius, damage, color, xp, money, kind="normal"):
        self.x, self.y = x, y
        self.hp, self.max_hp = hp, hp
        self.speed, self.radius, self.damage = speed, radius, damage
        self.color, self.reward_xp, self.reward_money, self.kind = color, xp, money, kind
        self.shoot_cd = 1.5


class Bullet:
    def __init__(self, x, y, vx, vy, dmg, life=1.2, radius=4, enemy=False):
        self.x, self.y, self.vx, self.vy, self.damage = x, y, vx, vy, dmg
        self.life, self.radius, self.enemy = life, radius, enemy


class Pickup:
    def __init__(self, x, y, mtype): self.x, self.y, self.mtype, self.radius = x, y, mtype, 16


class Station:
    def __init__(self, x, y): self.x, self.y, self.radius, self.used = x, y, 26, False


class Snake:
    def __init__(self):
        self.head = [0.0, 0.0]
        self.dir = [1.0, 0.0]
        self.speed = SNAKE_SPEED_BASE * CELL
        self.head_hp = HEAD_MAX_HP
        self.head_max_hp = HEAD_MAX_HP
        self.body = []
        self.body_size = 3
        self.modules = []
        self.lost_modules = []
        self.had_modules = False
        self.money, self.xp, self.level, self.xp_to_next = 0, 0, 1, 10
        self.boosters, self.heals = 0, 0
        self.alive = True
        self._init_body()
        self.add_module(MOD_PISTOL)

    def _init_body(self):
        for i in range(1, self.body_size + 1):
            self.body.append([self.head[0] - self.dir[0]*CELL*i, self.head[1] - self.dir[1]*CELL*i])

    def _grow_body(self):
        if self.body:
            last, prev = self.body[-1], self.body[-2] if len(self.body) >= 2 else self.head
            d = [last[0]-prev[0], last[1]-prev[1]]
            l = math.hypot(*d) or 1
            self.body.append([last[0] + d[0]/l*CELL, last[1] + d[1]/l*CELL])
        else:
            self.body.append([self.head[0] - self.dir[0]*CELL, self.head[1] - self.dir[1]*CELL])
        self.body_size = len(self.body)

    def module_positions(self):
        return [self.body[i] if i < len(self.body) else (self.body[-1] if self.body else self.head) for i in range(len(self.modules))]

    def add_module(self, mtype):
        if mtype == MOD_BOOSTER and self.boosters >= MAX_BOOSTERS: return False
        if mtype == MOD_HEAL and self.heals >= MAX_HEALS: return False
        self.modules.append(Module(mtype))
        if mtype == MOD_BOOSTER: self.boosters += 1
        if mtype == MOD_HEAL: self.heals += 1
        self.had_modules = True
        self._grow_body()
        return True

    def damage_chain(self, idx):
        removed = self.modules[idx:]
        self.modules = self.modules[:idx]
        for m in removed:
            self.lost_modules.append(m.mtype)
            if m.mtype == MOD_BOOSTER: self.boosters = max(0, self.boosters-1)
            if m.mtype == MOD_HEAL: self.heals = max(0, self.heals-1)


class GameWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.snake = None
        self.enemies, self.bullets, self.pickups, self.stations = [], [], [], []
        self.wave, self.wave_timer = 0, 2.0
        self.pickup_timer, self.station_timer = 6.0, 25.0
        self.paused, self.game_over = False, False
        self.show_upgrade, self.upgrade_options = False, []
        self.message, self.message_timer = "", 0.0
        self.station_menu = False
        self.station_ref = None
        self.reorder_mode = False

        self.reset()
        Clock.schedule_interval(self.update, 1/60)

        self.menu_btns = []
        for i in range(4):
            btn = Button(text="", size_hint=(None, None), size=(10, 10),
                         pos=(0, 0), background_color=(0, 0, 0, 0), opacity=0)
            btn.bind(on_press=lambda inst, idx=i: self.menu_action(idx))
            self.menu_btns.append(btn)
            self.add_widget(btn)

        self.pause_button = Button(text="II", size_hint=(None, None),
                                   size=(100, 100),
                                   background_color=(0.3, 0.3, 0.3, 0.5),
                                   font_size='30sp')
        self.pause_button.bind(on_press=self.toggle_pause)
        self.add_widget(self.pause_button)

        self.save_button = Button(text="SAVE", size_hint=(None, None),
                                  size=(100, 100),
                                  background_color=(0.2, 0.5, 0.2, 0.7),
                                  font_size='18sp')
        self.save_button.bind(on_press=self._on_save_pressed)
        self.add_widget(self.save_button)

        self.bind(size=self._layout_static_widgets, pos=self._layout_static_widgets)
        self._layout_static_widgets()

    def _layout_static_widgets(self, *args):
        if not self.width or not self.height:
            return
        size = min(self.width, self.height) * 0.08
        margin = self.height * 0.02
        self.pause_button.size = (size, size)
        self.pause_button.pos = (self.width * 0.02, self.height - size - margin)
        self.save_button.size = (size, size)
        self.save_button.pos = (self.width * 0.02 + size + 10, self.height - size - margin)

    def toggle_pause(self, instance):
        if not self.game_over:
            self.paused = not self.paused

    def _on_save_pressed(self, instance):
        if self.game_over:
            return
        self.save_game()

    def menu_action(self, idx):
        if self.show_upgrade:
            self.apply_upgrade(idx)
        elif self.station_menu:
            if idx == 0: self.station_repair()
            elif idx == 1: self.start_reorder()
            elif idx == 2: self.station_heal()
            elif idx == 3: self.close_station()
        elif self.reorder_mode:
            self.confirm_reorder(idx)

    def reset(self):
        self.snake = Snake()
        self.enemies, self.bullets, self.pickups, self.stations = [], [], [], []
        self.wave, self.wave_timer, self.pickup_timer, self.station_timer = 0, 2.0, 6.0, 25.0
        self.paused, self.game_over, self.show_upgrade = False, False, False
        self.station_menu, self.reorder_mode = False, False

    def msg(self, t, dur=2.0): self.message, self.message_timer = t, dur

    def to_dict(self):
        s = self.snake
        return {
            "snake": {
                "head": list(s.head), "dir": list(s.dir),
                "head_hp": s.head_hp, "head_max_hp": s.head_max_hp,
                "body": [list(b) for b in s.body],
                "body_size": s.body_size,
                "modules": [{"mtype": m.mtype, "hp": m.hp, "max_hp": m.max_hp,
                             "level": m.level, "cooldown": m.cooldown, "phase": m.phase}
                            for m in s.modules],
                "lost_modules": list(s.lost_modules),
                "had_modules": s.had_modules,
                "money": s.money, "xp": s.xp, "level": s.level,
                "xp_to_next": s.xp_to_next,
                "boosters": s.boosters, "heals": s.heals,
            },
            "wave": self.wave,
            "wave_timer": self.wave_timer,
            "pickup_timer": self.pickup_timer,
            "station_timer": self.station_timer,
        }

    def load_from_dict(self, data):
        try:
            sd = data["snake"]
            s = Snake()
            s.head = list(sd["head"])
            s.dir = list(sd["dir"])
            s.head_hp = sd["head_hp"]
            s.head_max_hp = sd["head_max_hp"]
            s.body = [list(b) for b in sd["body"]]
            s.body_size = sd["body_size"]
            s.modules = []
            for md in sd["modules"]:
                m = Module(md["mtype"])
                m.hp = md["hp"]; m.max_hp = md["max_hp"]
                m.level = md["level"]; m.cooldown = md["cooldown"]; m.phase = md["phase"]
                s.modules.append(m)
            s.lost_modules = list(sd["lost_modules"])
            s.had_modules = sd["had_modules"]
            s.money = sd["money"]; s.xp = sd["xp"]; s.level = sd["level"]
            s.xp_to_next = sd["xp_to_next"]
            s.boosters = sd["boosters"]; s.heals = sd["heals"]
            self.snake = s
            self.wave = data.get("wave", 0)
            self.wave_timer = data.get("wave_timer", 2.0)
            self.pickup_timer = data.get("pickup_timer", 6.0)
            self.station_timer = data.get("station_timer", 25.0)
            self.enemies, self.bullets, self.pickups, self.stations = [], [], [], []
            self.paused = False; self.game_over = False; self.show_upgrade = False
            self.station_menu = False; self.reorder_mode = False
            return True
        except Exception as e:
            print("LOAD ERROR:", e)
            return False

    def save_game(self):
        try:
            path = get_save_path()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, ensure_ascii=False)
            print("SAVED:", path)
            self.msg("Сохранено")
        except Exception as e:
            print("SAVE ERROR:", e)
            self.msg("Ошибка сохранения")

    def update(self, dt):
        if self.game_over:
            if self.message_timer > 0:
                self.message_timer -= dt
            else:
                App.get_running_app().go_to_menu()
            self.redraw()
            return

        if self.show_upgrade or self.station_menu or self.reorder_mode or self.paused:
            self.pause_button.opacity = 0
            self.save_button.opacity = 0
            self.redraw()
            return

        self.pause_button.opacity = 1
        self.save_button.opacity = 1

        s = self.snake
        s.head[0] += s.dir[0] * s.speed * (1 + SNAKE_SPEED_PER_BOOST*s.boosters) * dt
        s.head[1] += s.dir[1] * s.speed * (1 + SNAKE_SPEED_PER_BOOST*s.boosters) * dt

        target = s.head
        for i in range(len(s.body)):
            to = [target[0]-s.body[i][0], target[1]-s.body[i][1]]
            d = math.hypot(*to)
            if d > CELL: s.body[i] = [target[0]-to[0]/d*CELL, target[1]-to[1]/d*CELL]
            target = s.body[i]

        for m in s.modules:
            m.cooldown = max(0, m.cooldown - dt)
            m.phase += dt

        mpos = s.module_positions()
        for i, m in enumerate(s.modules):
            if not m.is_gun() or m.cooldown > 0: continue
            pos = mpos[i]; best, target_e = None, None
            for e in self.enemies:
                d = (pos[0]-e.x)**2 + (pos[1]-e.y)**2
                rng = GUN_STATS[m.mtype][1]
                if d <= rng*rng and (best is None or d < best): best, target_e = d, e
            if target_e:
                dmg, rng, cd = GUN_STATS[m.mtype]
                dmg *= 1 + 0.25*(m.level-1)
                ang = math.atan2(target_e.y-pos[1], target_e.x-pos[0])
                self.bullets.append(Bullet(pos[0], pos[1], math.cos(ang)*900, math.sin(ang)*900, dmg))
                m.cooldown = cd

        for idx, m in enumerate(s.modules):
            if m.mtype != MOD_HEAL or m.cooldown > 0: continue
            m.cooldown = 1.5; heal = 0.5 + 0.3*m.level
            if s.head_hp < s.head_max_hp: s.head_hp = min(s.head_max_hp, s.head_hp+heal)
            mp = mpos[idx]
            for j, other in enumerate(s.modules):
                if other is m: continue
                p = mpos[j]
                if (mp[0]-p[0])**2 + (mp[1]-p[1])**2 <= (70+5*m.level)**2:
                    other.hp = min(other.max_hp, other.hp+heal*0.4)

        for i, m in enumerate(s.modules):
            if m.mtype != MOD_AXES: continue
            mp = mpos[i]; orbit = 55 + 5*m.level
            for k in range(2):
                a = m.phase*3.0 + k*math.pi
                ax, ay = mp[0]+math.cos(a)*orbit, mp[1]+math.sin(a)*orbit
                for e in self.enemies:
                    if (ax-e.x)**2 + (ay-e.y)**2 <= (e.radius+14)**2 and m.cooldown <= 0:
                        e.hp -= 8 + 4*m.level
                        dx, dy = e.x-ax, e.y-ay; dl = math.hypot(dx, dy) or 1
                        e.x += dx/dl*18; e.y += dy/dl*18
                        m.cooldown = 0.25

        for i, m in enumerate(s.modules):
            p = mpos[i]
            for e in self.enemies:
                if (p[0]-e.x)**2 + (p[1]-e.y)**2 <= (e.radius+12)**2:
                    m.hp -= e.damage * dt * 0.8
            if m.hp <= 0:
                s.damage_chain(i)
                if s.had_modules and not s.modules:
                    self.game_over = True; self.msg("ИГРА ОКОНЧЕНА", 2.0); return
                break

        for e in list(self.enemies):
            ang = math.atan2(s.head[1]-e.y, s.head[0]-e.x); d = math.hypot(s.head[0]-e.x, s.head[1]-e.y)
            if e.kind == "shooter" and d < 280: ang += math.pi
            e.x += math.cos(ang)*e.speed*dt; e.y += math.sin(ang)*e.speed*dt
            if e.kind == "shooter":
                e.shoot_cd -= dt
                if e.shoot_cd <= 0 and d < 500:
                    e.shoot_cd = 2.0; a = math.atan2(s.head[1]-e.y, s.head[0]-e.x)
                    self.bullets.append(Bullet(e.x, e.y, math.cos(a)*350, math.sin(a)*350, e.damage, 2.0, 5, True))
            if (e.x-s.head[0])**2 + (e.y-s.head[1])**2 <= (e.radius+CELL*0.6)**2:
                s.head_hp -= e.damage * dt * 2.5
                dx, dy = e.x-s.head[0], e.y-s.head[1]; dl = math.hypot(dx, dy) or 1
                e.x += dx/dl*10; e.y += dy/dl*10

        if s.head_hp <= 0:
            self.game_over = True; self.msg("ИГРА ОКОНЧЕНА", 2.0); return

        for b in list(self.bullets):
            b.x += b.vx*dt; b.y += b.vy*dt; b.life -= dt
            if b.life <= 0: self.bullets.remove(b); continue
            if b.enemy:
                if (b.x-s.head[0])**2 + (b.y-s.head[1])**2 <= (b.radius+CELL*0.6)**2:
                    s.head_hp = max(0, s.head_hp-b.damage); self.bullets.remove(b); continue
                for bb in s.body:
                    if (b.x-bb[0])**2 + (b.y-bb[1])**2 <= (b.radius+CELL*0.5)**2:
                        s.head_hp = max(0, s.head_hp-b.damage*0.5); self.bullets.remove(b); break
            else:
                for e in list(self.enemies):
                    if (b.x-e.x)**2 + (b.y-e.y)**2 <= (e.radius+b.radius)**2:
                        e.hp -= b.damage; self.bullets.remove(b); break

        for e in list(self.enemies):
            if e.hp <= 0:
                self.enemies.remove(e)
                s.xp += e.reward_xp; s.money += e.reward_money
                if s.xp >= s.xp_to_next:
                    s.xp -= s.xp_to_next; s.level += 1; s.xp_to_next = int(s.xp_to_next*1.35+4)
                    self.open_upgrade()
                    if self.show_upgrade: return

        for p in list(self.pickups):
            touch = (p.x-s.head[0])**2 + (p.y-s.head[1])**2 <= (p.radius+CELL)**2
            if not touch:
                for b in s.body:
                    if (p.x-b[0])**2 + (p.y-b[1])**2 <= (p.radius+CELL*0.7)**2: touch=True; break
            if touch:
                if s.add_module(p.mtype):
                    self.pickups.remove(p); self.msg(f"Получен: {MOD_NAMES[p.mtype]}")
                else: self.msg("Лимит достигнут", 1.0)

        for st in self.stations:
            if not st.used and (st.x-s.head[0])**2 + (st.y-s.head[1])**2 <= (st.radius+CELL)**2:
                self.open_station(st); return

        self.wave_timer -= dt
        if self.wave_timer <= 0: self.spawn_wave(); self.wave_timer = max(6.0, 12.0-self.wave*0.3)
        self.pickup_timer -= dt
        if self.pickup_timer <= 0: self.spawn_pickup(); self.pickup_timer = random.uniform(6,11)
        self.station_timer -= dt
        if self.station_timer <= 0: self.spawn_station(); self.station_timer = random.uniform(30,50)
        if self.message_timer > 0: self.message_timer -= dt

        self.redraw()

    def _random_ring_pos(self, rmin, rmax):
        ang = random.uniform(0, math.tau); r = random.uniform(rmin, rmax)
        return self.snake.head[0]+math.cos(ang)*r, self.snake.head[1]+math.sin(ang)*r

    def spawn_wave(self):
        self.wave += 1; count = min(3+self.wave*2, 30); base_hp = 12+self.wave*6
        for _ in range(count):
            x, y = self._random_ring_pos(280, 600); roll, w = random.random(), self.wave
            if w >= 2 and roll < 0.15: e = Enemy(x, y, base_hp*2.5, 40+w*1.5, 18, 14, C_ENEMY_TANK, 4, 4, "tank")
            elif w >= 3 and roll < 0.30: e = Enemy(x, y, base_hp*0.9, 55+w*2, 13, 6, C_ENEMY_SHOOTER, 3, 3, "shooter")
            elif roll < 0.55: e = Enemy(x, y, base_hp*0.7, 100+w*3, 10, 6, C_ENEMY_FAST, 2, 2, "fast")
            else: e = Enemy(x, y, base_hp, 60+w*2, 13, 8, C_ENEMY, 1, 1)
            self.enemies.append(e)
        self.msg(f"Волна {self.wave}")

    def spawn_pickup(self):
        if len(self.pickups) > 5: return
        roll = random.random()
        if roll < 0.04: mtype = MOD_AXES
        elif roll < 0.40: mtype = random.choice([MOD_PISTOL, MOD_RIFLE, MOD_SNIPER])
        elif roll < 0.60: mtype = MOD_SHIELD
        elif roll < 0.85: mtype = random.choice([MOD_HEAL, MOD_BOOSTER])
        else: mtype = random.choice([MOD_PISTOL, MOD_RIFLE, MOD_SNIPER])
        if mtype == MOD_HEAL and self.snake.heals >= MAX_HEALS: return
        if mtype == MOD_BOOSTER and self.snake.boosters >= MAX_BOOSTERS: return
        x, y = self._random_ring_pos(140, 450); self.pickups.append(Pickup(x, y, mtype))

    def spawn_station(self):
        if any(not s.used for s in self.stations): return
        self.stations = [s for s in self.stations if not s.used]
        x, y = self._random_ring_pos(200, 500); self.stations.append(Station(x, y))

    def open_upgrade(self):
        self.show_upgrade = True
        opts, existing = [], {m.mtype for m in self.snake.modules}
        for t in existing: opts.append((f"Усилить: {MOD_NAMES[t]}", ('upgrade', t)))
        for t in [MOD_PISTOL, MOD_RIFLE, MOD_SNIPER, MOD_SHIELD, MOD_HEAL, MOD_BOOSTER]:
            if t not in existing:
                if t == MOD_HEAL and self.snake.heals >= MAX_HEALS: continue
                if t == MOD_BOOSTER and self.snake.boosters >= MAX_BOOSTERS: continue
                opts.append((f"Новый: {MOD_NAMES[t]}", ('add', t)))
        random.shuffle(opts); self.upgrade_options = opts[:3]
        self._layout_menu_buttons(len(self.upgrade_options), top_offset=0.55)

    def apply_upgrade(self, idx):
        if 0 <= idx < len(self.upgrade_options):
            _, (kind, t) = self.upgrade_options[idx]; s = self.snake
            if kind == 'upgrade':
                for m in s.modules:
                    if m.mtype == t: m.level += 1; m.max_hp *= 1.2; m.hp = m.max_hp; break
            else: s.add_module(t)
        self.show_upgrade = False; self.upgrade_options = []
        for btn in self.menu_btns: btn.opacity = 0

    def open_station(self, st):
        self.station_menu, self.station_ref = True, st; st.used = True
        self._layout_menu_buttons(4, top_offset=0.62)

    def close_station(self):
        self.station_menu = False
        for btn in self.menu_btns: btn.opacity = 0

    def station_repair(self):
        s = self.snake
        if not s.lost_modules: self.msg("Нет потерянных"); self.close_station(); return
        cost = len(s.lost_modules)*8
        if s.money < cost: self.msg(f"Нужно {cost}"); self.close_station(); return
        s.money -= cost
        restored, s.lost_modules = s.lost_modules[:], []; cnt = 0
        for t in restored:
            if t == MOD_HEAL and s.heals >= MAX_HEALS: continue
            if t == MOD_BOOSTER and s.boosters >= MAX_BOOSTERS: continue
            if s.add_module(t): cnt += 1
        self.msg(f"Восстановлено: {cnt}")
        self.close_station()

    def station_heal(self):
        heal = self.snake.head_max_hp * 0.25
        self.snake.head_hp = min(self.snake.head_max_hp, self.snake.head_hp + heal)
        self.msg("Хил 25%")
        self.close_station()

    def start_reorder(self):
        self.close_station()
        if len(self.snake.modules) < 2:
            self.msg("Мало модулей"); return
        self.reorder_mode = True
        self._layout_menu_buttons(min(4, len(self.snake.modules)), top_offset=0.85, from_top=True)

    def confirm_reorder(self, idx):
        if idx < len(self.snake.modules) - 1:
            mods = self.snake.modules
            mods[idx], mods[idx+1] = mods[idx+1], mods[idx]
        self.reorder_mode = False
        for btn in self.menu_btns: btn.opacity = 0

    def _layout_menu_buttons(self, count, top_offset=0.55, from_top=False):
        btn_w = self.width * 0.7
        btn_h = self.height * 0.09
        x = (self.width - btn_w) / 2
        for i in range(4):
            if i < count:
                if from_top:
                    y = self.height * top_offset - i * (btn_h + 10)
                else:
                    start_center_y = self.height * top_offset
                    y = start_center_y - (i - (count - 1) / 2) * (btn_h + 10) - btn_h / 2
                self.menu_btns[i].size = (btn_w, btn_h)
                self.menu_btns[i].pos = (x, y)
                self.menu_btns[i].opacity = 1
            else:
                self.menu_btns[i].opacity = 0

    def on_touch_down(self, touch):
        if self.show_upgrade or self.station_menu or self.reorder_mode:
            return super().on_touch_down(touch)

        jx = self.width * 0.82
        jy = self.height * 0.15
        r = min(self.width, self.height) * 0.14
        if (touch.x - jx)**2 + (touch.y - jy)**2 <= r**2:
            touch.ud['joystick'] = True
            self._handle_joystick(touch.x, touch.y, jx, jy)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.ud.get('joystick'):
            jx = self.width * 0.82
            jy = self.height * 0.15
            self._handle_joystick(touch.x, touch.y, jx, jy)
            return True
        return super().on_touch_move(touch)

    def _handle_joystick(self, x, y, cx, cy):
        dx, dy = x - cx, y - cy
        if math.hypot(dx, dy) > 30:
            l = math.hypot(dx, dy)
            self.snake.dir = [dx/l, dy/l]
            self.redraw()

    def redraw(self):
        self.canvas.clear()
        with self.canvas:
            Color(*C_BG); Rectangle(pos=(0, 0), size=(self.width, self.height))

            ox = self.snake.head[0] - self.width / 2
            oy = self.snake.head[1] - self.height / 2
            def screen(x, y): return x - ox, y - oy

            for st in self.stations:
                if not st.used:
                    sx, sy = screen(st.x, st.y)
                    Color(*C_STATION); Ellipse(pos=(sx-st.radius, sy-st.radius), size=(st.radius*2, st.radius*2))

            for p in self.pickups:
                sx, sy = screen(p.x, p.y)
                Color(*MOD_COLORS[p.mtype]); Ellipse(pos=(sx-p.radius, sy-p.radius), size=(p.radius*2, p.radius*2))

            for e in self.enemies:
                sx, sy = screen(e.x, e.y)
                Color(*e.color); Ellipse(pos=(sx-e.radius, sy-e.radius), size=(e.radius*2, e.radius*2))
                Color(*C_RED); Rectangle(pos=(sx-28, sy-e.radius-16), size=(56, 8))
                Color(*C_GREEN); Rectangle(pos=(sx-28, sy-e.radius-16), size=(56*max(0,min(1,e.hp/e.max_hp)), 8))

            for b in self.bullets:
                sx, sy = screen(b.x, b.y)
                Color(*(C_ENEMY_BULLET if b.enemy else C_BULLET))
                Ellipse(pos=(sx-b.radius, sy-b.radius), size=(b.radius*2, b.radius*2))

            s = self.snake
            for b in s.body:
                sx, sy = screen(b[0], b[1])
                Color(*C_BODY); Rectangle(pos=(sx-CELL*0.45, sy-CELL*0.45), size=(CELL*0.9, CELL*0.9))

            mpos = s.module_positions()
            for i, m in enumerate(s.modules):
                if i >= len(mpos): continue
                mx, my = screen(mpos[i][0], mpos[i][1])
                Color(*MOD_COLORS[m.mtype]); Rectangle(pos=(mx-CELL*0.3, my-CELL*0.3), size=(CELL*0.6, CELL*0.6))
                Color(*C_RED); Rectangle(pos=(mx-24, my-CELL*0.8), size=(48, 8))
                Color(*C_GREEN); Rectangle(pos=(mx-24, my-CELL*0.8), size=(48*max(0,min(1,m.hp/m.max_hp)), 8))

                if m.mtype == MOD_SHIELD:
                    for k in range(2):
                        a = m.phase*3.0 + k*math.pi
                        shx, shy = mx + math.cos(a) * 45, my + math.sin(a) * 45
                        Color(*C_SHIELD); Line(circle=(shx, shy, 20), width=6)
                if m.mtype == MOD_AXES:
                    for k in range(2):
                        a = m.phase*3.0 + k*math.pi
                        ax, ay = mx + math.cos(a) * 55, my + math.sin(a) * 55
                        Color(*C_AXES); Ellipse(pos=(ax-15, ay-15), size=(30, 30))

            hx, hy = screen(s.head[0], s.head[1])
            Color(*C_HEAD); Ellipse(pos=(hx-CELL*0.7, hy-CELL*0.7), size=(CELL*1.4, CELL*1.4))

            jx = self.width * 0.82
            jy = self.height * 0.15
            r = min(self.width, self.height) * 0.14
            Color(0.2, 0.25, 0.35); Ellipse(pos=(jx-r, jy-r), size=(r*2, r*2))
            Color(0.6, 0.7, 0.8); Line(circle=(jx, jy, r), width=6)
            knob_x = jx + s.dir[0] * (r * 0.5)
            knob_y = jy + s.dir[1] * (r * 0.5)
            Color(0.9, 0.9, 0.3); Ellipse(pos=(knob_x - 40, knob_y - 40), size=(80, 80))

            if self.show_upgrade:
                Color(0, 0, 0, 0.8); Rectangle(pos=(0, 0), size=(self.width, self.height))
                lbl_title = CoreLabel(text="УРОВЕНЬ! Выбери усиление:", font_size=int(min(self.width, self.height)*0.04),
                                      bold=True, color=(1, 0.8, 0.3, 1))
                lbl_title.refresh()
                Color(1, 1, 1); Rectangle(texture=lbl_title.texture,
                                          pos=(self.width/2 - lbl_title.texture.width/2, self.height*0.7),
                                          size=lbl_title.texture.size)
                for i, (label, _) in enumerate(self.upgrade_options):
                    btn = self.menu_btns[i]
                    bx, by = btn.pos
                    bw, bh = btn.size
                    Color(1, 1, 1); Line(rectangle=(bx, by, bw, bh), width=4)
                    lbl = CoreLabel(text=f"{i+1}. {label}", font_size=int(min(self.width, self.height)*0.03),
                                    color=(1, 1, 1, 1))
                    lbl.refresh()
                    Color(1, 1, 1); Rectangle(texture=lbl.texture,
                                              pos=(bx + 20, by + bh/2 - lbl.texture.height/2),
                                              size=lbl.texture.size)

            if self.station_menu:
                Color(0, 0, 0, 0.8); Rectangle(pos=(0, 0), size=(self.width, self.height))
                lbl_title = CoreLabel(text="СТАНЦИЯ", font_size=int(min(self.width, self.height)*0.04),
                                      bold=True, color=(1, 0.8, 0.3, 1))
                lbl_title.refresh()
                Color(1, 1, 1); Rectangle(texture=lbl_title.texture,
                                          pos=(self.width/2 - lbl_title.texture.width/2, self.height*0.85),
                                          size=lbl_title.texture.size)
                opts = [f"1. Восстановить ({len(s.lost_modules)*8}$)", "2. Переставить модули",
                        "3. Лечение (25%)", "4. Выйти"]
                for i, text in enumerate(opts):
                    btn = self.menu_btns[i]
                    bx, by = btn.pos
                    bw, bh = btn.size
                    Color(1, 1, 1); Line(rectangle=(bx, by, bw, bh), width=4)
                    lbl = CoreLabel(text=text, font_size=int(min(self.width, self.height)*0.03),
                                    color=(1, 1, 1, 1))
                    lbl.refresh()
                    Color(1, 1, 1); Rectangle(texture=lbl.texture,
                                              pos=(bx + 20, by + bh/2 - lbl.texture.height/2),
                                              size=lbl.texture.size)

            if self.reorder_mode:
                Color(0, 0, 0, 0.8); Rectangle(pos=(0, 0), size=(self.width, self.height))
                lbl_title = CoreLabel(text="ПЕРЕСТАНОВКА (Кликни для сдвига)",
                                      font_size=int(min(self.width, self.height)*0.035),
                                      bold=True, color=(1, 0.8, 0.3, 1))
                lbl_title.refresh()
                Color(1, 1, 1); Rectangle(texture=lbl_title.texture,
                                          pos=(self.width/2 - lbl_title.texture.width/2, self.height*0.92),
                                          size=lbl_title.texture.size)
                for i, m in enumerate(s.modules):
                    if i >= len(self.menu_btns): break
                    btn = self.menu_btns[i]
                    bx, by = btn.pos
                    bw, bh = btn.size
                    Color(1, 1, 1); Line(rectangle=(bx, by, bw, bh), width=2)
                    lbl = CoreLabel(text=f"{i+1}. {MOD_NAMES[m.mtype]} L{m.level}",
                                    font_size=int(min(self.width, self.height)*0.03),
                                    color=(1, 1, 1, 1))
                    lbl.refresh()
                    Color(1, 1, 1); Rectangle(texture=lbl.texture,
                                              pos=(bx + 20, by + bh/2 - lbl.texture.height/2),
                                              size=lbl.texture.size)


class MainMenu(FloatLayout):
    def __init__(self, start_callback, continue_callback, exit_callback, has_save=False, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(0.05, 0.06, 0.09, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        title = Label(text="ЗМЕЙКА-РОГАЛИК",
                      pos_hint={'center_x': 0.5, 'center_y': 0.82},
                      font_size='72sp', bold=True, color=(1, 0.8, 0.3, 1))
        self.add_widget(title)

        btn_start = Button(text="НОВАЯ ИГРА",
                           size_hint=(None, None), size=(600, 140),
                           pos_hint={'center_x': 0.5, 'center_y': 0.6},
                           background_color=(0.2, 0.7, 0.4, 1), font_size='40sp')
        btn_start.bind(on_press=start_callback)
        self.add_widget(btn_start)

        y = 0.45
        if has_save:
            btn_cont = Button(text="ПРОДОЛЖИТЬ",
                              size_hint=(None, None), size=(600, 140),
                              pos_hint={'center_x': 0.5, 'center_y': y},
                              background_color=(0.2, 0.5, 0.8, 1), font_size='40sp')
            btn_cont.bind(on_press=continue_callback)
            self.add_widget(btn_cont)
            y -= 0.15

        btn_exit = Button(text="ВЫЙТИ",
                          size_hint=(None, None), size=(600, 140),
                          pos_hint={'center_x': 0.5, 'center_y': y},
                          background_color=(0.8, 0.2, 0.2, 1), font_size='40sp')
        btn_exit.bind(on_press=exit_callback)
        self.add_widget(btn_exit)

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


class SnakeApp(App):
    def build(self):
        self.root = FloatLayout()
        self._show_menu()
        return self.root

    def _has_save(self):
        return os.path.exists(get_save_path())

    def _show_menu(self):
        self.menu = MainMenu(
            start_callback=self.start_game,
            continue_callback=self.continue_game,
            exit_callback=self.stop,
            has_save=self._has_save()
        )
        self.root.add_widget(self.menu)

    def _clear_menu(self):
        if self.menu in self.root.children:
            self.root.remove_widget(self.menu)

    def _build_hud(self):
        self.hud = Label(text="",
                         pos_hint={'x': 0.01, 'top': 0.99}, size_hint=(0.5, 0.1),
                         color=(1, 1, 1, 1), font_size='40sp', bold=True, halign='left')
        self.hud.bind(size=self.hud.setter('text_size'))
        self.root.add_widget(self.hud)

        self.module_list = Label(text="",
                                 pos_hint={'right': 0.99, 'top': 0.99}, size_hint=(0.4, 0.3),
                                 color=(0.8, 0.8, 0.8, 1), font_size='24sp', bold=True, halign='right')
        self.module_list.bind(size=self.module_list.setter('text_size'))
        self.root.add_widget(self.module_list)

        self.notify_label = Label(text="",
                                  pos_hint={'x': 0.01, 'top': 0.85}, size_hint=(0.5, 0.1),
                                  color=(1, 0.8, 0.3, 1), font_size='36sp', bold=True, halign='left')
        self.notify_label.bind(size=self.notify_label.setter('text_size'))
        self.root.add_widget(self.notify_label)

        Clock.schedule_interval(self.update_hud, 0.1)

    def start_game(self, instance):
        self._clear_menu()
        self.game = GameWidget(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        self.root.add_widget(self.game)
        self._build_hud()

    def continue_game(self, instance):
        save_path = get_save_path()
        if not os.path.exists(save_path):
            self.start_game(instance)
            return
        try:
            with open(save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print("LOAD ERROR:", e)
            self.start_game(instance)
            return

        self._clear_menu()
        self.game = GameWidget(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        self.game.load_from_dict(data)
        self.root.add_widget(self.game)
        self._build_hud()

    def go_to_menu(self):
        if hasattr(self, 'game'):
            try: self.root.remove_widget(self.game)
            except Exception: pass
        for attr in ('hud', 'module_list', 'notify_label'):
            if hasattr(self, attr):
                try: self.root.remove_widget(getattr(self, attr))
                except Exception: pass
        Clock.unschedule(self.update_hud)
        self._show_menu()

    def update_hud(self, dt):
        g = getattr(self, 'game', None)
        if not g: return
        s = g.snake
        text = f"HP: {int(s.head_hp)} | Lvl: {s.level}\nWave: {g.wave} | $: {s.money}"
        self.hud.text = text

        mod_text = "Модули:\n"
        for i, m in enumerate(s.modules):
            mod_text += f"{i+1}. {MOD_NAMES[m.mtype]} L{m.level}\n"
        self.module_list.text = mod_text

        if g.message_timer > 0:
            self.notify_label.text = g.message
        else:
            self.notify_label.text = ""

    def on_stop(self):
        if hasattr(self, 'game') and self.game and not self.game.game_over:
            self.game.save_game()


if __name__ == '__main__':
    SnakeApp().run()
