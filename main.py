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
from kivy.metrics import dp, sp
import math
import random
import os
import json
from enum import Enum, auto

# ---------- Сохранения ----------
def get_save_path():
    app = App.get_running_app()
    base = app.user_data_dir if app else os.path.expanduser("~")
    try: os.makedirs(base, exist_ok=True)
    except: base = os.path.expanduser("~")
    return os.path.join(base, "save.json")

class PlayerData:
    def __init__(self):
        self.money = 0
        self.high_score = 0
        self.snake_skin = 0
        self.owned_snake_skins = [0]
        self.upg_legs = False
        self.upg_skin = False
        self.load()

    def load(self):
        if os.path.exists(get_save_path()):
            try:
                with open(get_save_path(), "r", encoding="utf-8") as f:
                    d = json.load(f)
                    self.money = d.get("money", 0)
                    self.high_score = d.get("high_score", 0)
                    self.snake_skin = d.get("snake_skin", 0)
                    self.owned_snake_skins = d.get("owned_snake_skins", [0])
                    self.upg_legs = d.get("upg_legs", False)
                    self.upg_skin = d.get("upg_skin", False)
            except Exception as e:
                print("LOAD ERR:", e)

    def save(self):
        d = {
            "money": self.money, "high_score": self.high_score,
            "snake_skin": self.snake_skin, "owned_snake_skins": self.owned_snake_skins,
            "upg_legs": self.upg_legs, "upg_skin": self.upg_skin
        }
        try:
            with open(get_save_path(), "w", encoding="utf-8") as f:
                json.dump(d, f)
            print("SAVED to", get_save_path())
        except Exception as e:
            print("SAVE ERR:", e)

PLAYER = PlayerData()

# ---------- Данные ----------
class ModType(Enum):
    PISTOL = auto(); RIFLE = auto(); SNIPER = auto(); SHIELD = auto(); HEAL = auto(); BOOSTER = auto(); AXES = auto(); TESLA = auto(); GRENADE = auto(); DRONE = auto()

MOD_DATA = {
    ModType.PISTOL:  {"name": "Пистолет", "hp": 40, "color": (0.4, 0.8, 1), "rarity": 1},
    ModType.RIFLE:   {"name": "Автомат", "hp": 35, "color": (0.4, 1, 0.8), "rarity": 2},
    ModType.SNIPER:  {"name": "Снайперка", "hp": 45, "color": (0.8, 0.5, 1), "rarity": 3},
    ModType.SHIELD:  {"name": "Щит", "hp": 60, "color": (1, 0.9, 0.4), "rarity": 3},
    ModType.HEAL:    {"name": "Хилка", "hp": 25, "color": (0.4, 1, 0.5), "rarity": 4},
    ModType.BOOSTER: {"name": "Ускоритель", "hp": 25, "color": (1, 0.6, 1), "rarity": 4},
    ModType.AXES:    {"name": "Топоры", "hp": 80, "color": (1, 1, 1), "rarity": 5},
    ModType.TESLA:   {"name": "Тесла", "hp": 30, "color": (0.6, 1, 1), "rarity": 3},
    ModType.GRENADE: {"name": "Гранатомет", "hp": 40, "color": (0.8, 0.4, 0.2), "rarity": 4},
    ModType.DRONE:   {"name": "Дрон", "hp": 50, "color": (0.7, 0.7, 0.7), "rarity": 5},
}
GUN_STATS = {
    ModType.PISTOL: (12, 340, 0.55), ModType.RIFLE: (6, 300, 0.13), ModType.SNIPER: (40, 620, 1.4),
    ModType.TESLA: (15, 250, 0.8), ModType.GRENADE: (30, 400, 1.2), ModType.DRONE: (8, 300, 0.4)
}
RARITY_COLORS = {1: (0.8, 0.8, 0.8), 2: (0.4, 0.8, 1), 3: (0.7, 0.4, 1), 4: (1, 0.4, 0.8), 5: (1, 0.8, 0.2)}

CELL = 25
MAX_BULLETS = 60
MAX_ENEMIES = 30
MAX_PICKUPS = 3

# ---------- Игровые классы ----------
class Enemy:
    def __init__(self, x, y, hp, speed, radius, color, dmg, kind="melee"):
        self.x, self.y = x, y; self.hp, self.max_hp = hp, hp
        self.speed, self.radius, self.color, self.damage = speed, radius, color, dmg
        self.kind = kind  # melee / shooter / tank / fast
        self.shoot_cd = 1.5
        self.tesla_hit = 0.0

class Bullet:
    def __init__(self, x, y, vx, vy, dmg, is_grenade=False, life=1.5, is_enemy=False):
        self.x, self.y, self.vx, self.vy, self.dmg = x, y, vx, vy, dmg
        self.is_grenade = is_grenade
        self.life = life
        self.is_enemy = is_enemy

class Pickup:
    def __init__(self, x, y, mtype): self.x, self.y, self.mtype = x, y, mtype

class Station:
    def __init__(self, x, y): self.x, self.y = x, y; self.used = False

class Explosion:
    def __init__(self, x, y, radius, life=0.3):
        self.x, self.y = x, y
        self.radius = radius
        self.life = life
        self.max_life = life

class TeslaLine:
    def __init__(self, points): self.points = points; self.life = 0.15

class Snake:
    def __init__(self):
        self.x, self.y = 0.0, 0.0
        self.dx, self.dy = 1.0, 0.0
        self.speed = 180 * (1.2 if PLAYER.upg_legs else 1.0)
        self.hp = 100 + (30 if PLAYER.upg_skin else 0)
        self.max_hp = self.hp
        self.body = [[self.x - CELL, self.y]]
        self.mods = []          # [{"type": ModType, "hp": ..., "max_hp": ..., "lvl":..., "cd":...}]
        self.level, self.xp, self.xp_next = 1, 0, 10
        self.money = 0
        self.drone_angle = 0.0
        self.drone_x, self.drone_y = 0.0, 0.0
        self.add_mod(ModType.PISTOL)

    def add_mod(self, mtype):
        self.mods.append({
            "type": mtype, "hp": MOD_DATA[mtype]["hp"], "max_hp": MOD_DATA[mtype]["hp"],
            "lvl": 1, "cd": 0.0
        })
        last = self.body[-1] if self.body else [self.x, self.y]
        self.body.append([last[0], last[1]])

    def total_body_hp(self):
        return self.hp + sum(m["hp"] for m in self.mods)

# ---------- Меню улучшений ----------
class UpgradeMenu(FloatLayout):
    def __init__(self, options, callback, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 0.7); self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        layout = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(20),
                           size_hint=(0.8, 0.8), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        layout.add_widget(Label(text="УРОВЕНЬ ПОВЫШЕН!", font_size=sp(24), bold=True,
                                color=(1, 0.8, 0.2), size_hint_y=0.2))
        for i, mtype in enumerate(options):
            btn = Button(text=MOD_DATA[mtype]['name'], font_size=sp(18), size_hint_y=0.2,
                         background_color=(*MOD_DATA[mtype]['color'], 1))
            btn.bind(on_press=lambda inst, idx=i: callback(idx))
            layout.add_widget(btn)
        self.add_widget(layout)
    def update_bg(self, *a):
        self.bg.pos = self.pos; self.bg.size = self.size

# ---------- Меню паузы ----------
class PauseMenu(FloatLayout):
    def __init__(self, resume_cb, menu_cb, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 0.7); self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        layout = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(20),
                           size_hint=(0.6, 0.4), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        layout.add_widget(Label(text="ПАУЗА", font_size=sp(28), bold=True,
                                color=(1, 0.8, 0.2), size_hint_y=0.3))
        b = Button(text="ПРОДОЛЖИТЬ", font_size=sp(18), background_color=(0.2, 0.7, 0.3, 1))
        b.bind(on_press=resume_cb); layout.add_widget(b)
        b = Button(text="В ГЛАВНОЕ МЕНЮ", font_size=sp(18), background_color=(0.7, 0.3, 0.3, 1))
        b.bind(on_press=menu_cb); layout.add_widget(b)
        self.add_widget(layout)
    def update_bg(self, *a):
        self.bg.pos = self.pos; self.bg.size = self.size

# ---------- Игровой виджет ----------
class GameWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self.start_game_loop, pos=self.start_game_loop)
        self.reset()

    def start_game_loop(self, *args):
        if self.width > 0 and not hasattr(self, '_started'):
            self._started = True
            Clock.schedule_interval(self.update, 1/60)

    def reset(self):
        self.snake = Snake()
        self.enemies, self.bullets, self.pickups = [], [], []
        self.stations = []
        self.explosions, self.tesla_lines = [], []
        self.wave, self.wave_timer = 0, 3.0
        self.pickup_timer, self.station_timer = 6.0, 20.0
        self.game_over, self.upgrading, self.paused = False, False, False
        self.upg_opts = []
        self.msg_timer, self.msg_text = 0, ""

    def msg(self, text, t=2.0): self.msg_text, self.msg_timer = text, t

    def update(self, dt):
        if self.msg_timer > 0: self.msg_timer -= dt

        for ex in self.explosions[:]:
            ex.life -= dt
            if ex.life <= 0: self.explosions.remove(ex)
        for tl in self.tesla_lines[:]:
            tl.life -= dt
            if tl.life <= 0: self.tesla_lines.remove(tl)
        for e in self.enemies:
            if e.tesla_hit > 0: e.tesla_hit -= dt

        if self.game_over or self.upgrading or self.paused or self.width <= 0:
            self.redraw(); return

        s = self.snake

        # --- ДВИЖЕНИЕ ---
        s.x += s.dx * s.speed * dt
        s.y += s.dy * s.speed * dt
        tx, ty = s.x, s.y
        for i in range(len(s.body)):
            dx = tx - s.body[i][0]; dy = ty - s.body[i][1]
            d = math.hypot(dx, dy)
            if d > CELL:
                if d < 0.001: d = 0.001
                s.body[i][0] = tx - (dx / d) * CELL
                s.body[i][1] = ty - (dy / d) * CELL
            tx, ty = s.body[i][0], s.body[i][1]

        # --- ДРОН ---
        drone_active = any(m["type"] == ModType.DRONE for m in s.mods)
        if drone_active:
            s.drone_angle += dt * 2.0
            orbit_r = max(60, len(s.body) * CELL * 0.6)
            s.drone_x = s.x + math.cos(s.drone_angle) * orbit_r
            s.drone_y = s.y + math.sin(s.drone_angle) * orbit_r

        # --- СТРЕЛЬБА МОДУЛЕЙ ---
        for i in range(min(len(s.mods), len(s.body))):
            m = s.mods[i]
            m["cd"] = max(0.0, m["cd"] - dt)
            if m["type"] in GUN_STATS and m["cd"] <= 0:
                mx, my = s.body[i][0], s.body[i][1]
                if m["type"] == ModType.DRONE:
                    mx, my = s.drone_x, s.drone_y
                # Цель
                best_d, tgt = GUN_STATS[m["type"]][1]**2, None
                for e in self.enemies:
                    d2 = (mx - e.x)**2 + (my - e.y)**2
                    if d2 < best_d: best_d, tgt = d2, e
                if tgt:
                    ang = math.atan2(tgt.y - my, tgt.x - mx)
                    dmg = GUN_STATS[m["type"]][0] * (1 + 0.2 * m["lvl"])
                    cd = GUN_STATS[m["type"]][2]

                    if m["type"] == ModType.TESLA:
                        chain = [tgt]; cur = tgt
                        for _ in range(3):
                            bd, nt = 200**2, None
                            for e in self.enemies:
                                if e in chain: continue
                                d2 = (cur.x - e.x)**2 + (cur.y - e.y)**2
                                if d2 < bd: bd, nt = d2, e
                            if nt: chain.append(nt); cur = nt
                            else: break
                        for ct in chain:
                            ct.hp -= dmg; ct.tesla_hit = 0.15
                        pts = [(mx, my)] + [(c.x, c.y) for c in chain]
                        self.tesla_lines.append(TeslaLine(pts))
                    elif m["type"] == ModType.GRENADE:
                        if len(self.bullets) < MAX_BULLETS:
                            self.bullets.append(Bullet(mx, my, math.cos(ang)*500, math.sin(ang)*500,
                                                       dmg, is_grenade=True, life=1.2))
                    else:
                        if len(self.bullets) < MAX_BULLETS:
                            self.bullets.append(Bullet(mx, my, math.cos(ang)*700, math.sin(ang)*700, dmg))
                    m["cd"] = cd

            # --- ХИЛКА ---
            elif m["type"] == ModType.HEAL and m["cd"] <= 0:
                m["cd"] = 1.5
                heal = 0.5 + 0.3 * m["lvl"]
                s.hp = min(s.max_hp, s.hp + heal)
                for other in s.mods:
                    if other is not m:
                        other["hp"] = min(other["max_hp"], other["hp"] + heal * 0.4)

        # --- ТОПОРЫ / ЩИТ (эффект-отрисовка, без урона) ---
        # (визуал мы добавим в redraw по позициям модулей)

        # --- ПУЛИ ---
        for b in self.bullets[:]:
            b.x += b.vx * dt; b.y += b.vy * dt; b.life -= dt
            hit = False
            if b.is_enemy:
                # Враг стреляет по голове/модулям
                if (b.x - s.x)**2 + (b.y - s.y)**2 < (8 + CELL*0.5)**2:
                    s.hp -= b.dmg; hit = True
                else:
                    for i in range(min(len(s.mods), len(s.body))):
                        if (b.x - s.body[i][0])**2 + (b.y - s.body[i][1])**2 < (8 + CELL*0.4)**2:
                            s.mods[i]["hp"] -= b.dmg; hit = True; break
            else:
                for e in self.enemies[:]:
                    if (b.x - e.x)**2 + (b.y - e.y)**2 < (e.radius + 8)**2:
                        if b.is_grenade:
                            self.explosions.append(Explosion(b.x, b.y, 90, 0.4))
                            for ee in self.enemies[:]:
                                if (b.x - ee.x)**2 + (b.y - ee.y)**2 < 90**2:
                                    ee.hp -= b.dmg
                        else:
                            e.hp -= b.dmg
                        hit = True; break
            if hit or b.life <= 0 or (b.x - s.x)**2 + (b.y - s.y)**2 > 2000**2:
                if b.is_grenade and not hit:
                    self.explosions.append(Explosion(b.x, b.y, 90, 0.4))
                    for ee in self.enemies[:]:
                        if (b.x - ee.x)**2 + (b.y - ee.y)**2 < 90**2:
                            ee.hp -= b.dmg
                if b in self.bullets: self.bullets.remove(b)

        # --- ВРАГИ ---
        for e in self.enemies[:]:
            # Ищут ближайшую цель: голова или модуль
            targets = [(s.x, s.y, "head")]
            for i in range(min(len(s.mods), len(s.body))):
                targets.append((s.body[i][0], s.body[i][1], i))
            # Ближайшая
            best = None; bd = 999999**2
            for tx_t, ty_t, tag in targets:
                d2 = (e.x - tx_t)**2 + (e.y - ty_t)**2
                if d2 < bd: bd = d2; best = (tx_t, ty_t, tag)
            tx_t, ty_t, tag = best
            ang = math.atan2(ty_t - e.y, tx_t - e.x)
            # Стрелок держит дистанцию
            if e.kind == "shooter":
                if bd < 250**2: ang += math.pi
                e.shoot_cd -= dt
                if e.shoot_cd <= 0 and bd < 500**2:
                    e.shoot_cd = 2.0
                    a = math.atan2(s.y - e.y, s.x - e.x)
                    self.bullets.append(Bullet(e.x, e.y, math.cos(a)*350, math.sin(a)*350,
                                               e.damage, is_enemy=True, life=2.0))
            e.x += math.cos(ang) * e.speed * dt
            e.y += math.sin(ang) * e.speed * dt
            # Урон при касании
            if (e.x - s.x)**2 + (e.y - s.y)**2 < (e.radius + CELL*0.5)**2:
                s.hp -= e.damage * dt * 2.0
            else:
                for i in range(min(len(s.mods), len(s.body))):
                    if (e.x - s.body[i][0])**2 + (e.y - s.body[i][1])**2 < (e.radius + CELL*0.5)**2:
                        s.mods[i]["hp"] -= e.damage * dt * 2.0
                        break
            if e.hp <= 0:
                self.enemies.remove(e)
                s.money += 5; s.xp += 3
                if s.xp >= s.xp_next:
                    s.xp -= s.xp_next; s.level += 1
                    s.xp_next = int(s.xp_next * 1.5)
                    self.open_upgrade(); return

        # --- СМЕРТЬ МОДУЛЕЙ ---
        for i in range(len(s.mods)-1, -1, -1):
            if s.mods[i]["hp"] <= 0:
                s.mods.pop(i)
                # сдвигаем тело
                while len(s.body) > len(s.mods) + 1:
                    s.body.pop()

        # --- ПОДБОР ---
        for p in self.pickups[:]:
            if (p.x - s.x)**2 + (p.y - s.y)**2 < (20 + 15)**2:
                self.pickups.remove(p)
                s.add_mod(p.mtype); self.msg(f"+{MOD_DATA[p.mtype]['name']}")

        # --- СТАНЦИИ ---
        for st in self.stations:
            if not st.used and (st.x - s.x)**2 + (st.y - s.y)**2 < (30 + 15)**2:
                st.used = True
                s.hp = min(s.max_hp, s.hp + s.max_hp * 0.5)
                for m in s.mods: m["hp"] = m["max_hp"]
                self.msg("Станция: HP восстановлено")

        # --- ТАЙМЕРЫ ---
        self.wave_timer -= dt
        if self.wave_timer <= 0:
            self.wave += 1
            self.wave_timer = max(8.0, 15.0 - self.wave * 0.3)
            if len(self.enemies) < MAX_ENEMIES:
                count = min(3 + self.wave, 12)
                for _ in range(count):
                    a = random.uniform(0, math.tau); r = random.uniform(350, 600)
                    ex = s.x + math.cos(a)*r; ey = s.y + math.sin(a)*r
                    hp = 10 + self.wave * 6
                    # Типы врагов
                    roll = random.random()
                    if self.wave >= 4 and roll < 0.25:
                        # Стрелок
                        self.enemies.append(Enemy(ex, ey, hp*0.9, 60 + self.wave*2, 15, (1, 0.3, 0.8), 6, "shooter"))
                    elif self.wave >= 3 and roll < 0.45:
                        # Танк
                        self.enemies.append(Enemy(ex, ey, hp*2.0, 40 + self.wave*1.5, 20, (0.6, 0.2, 0.8), 15, "tank"))
                    elif self.wave >= 2 and roll < 0.65:
                        # Быстрый
                        self.enemies.append(Enemy(ex, ey, hp*0.6, 100 + self.wave*3, 12, (1, 0.5, 0.2), 8, "fast"))
                    else:
                        self.enemies.append(Enemy(ex, ey, hp, 60 + self.wave*2, 15, (1, 0.3, 0.3), 10, "melee"))
            self.msg(f"Волна {self.wave}")

        self.pickup_timer -= dt
        if self.pickup_timer <= 0 and len(self.pickups) < MAX_PICKUPS:
            a = random.uniform(0, math.tau); r = random.uniform(150, 400)
            self.pickups.append(Pickup(s.x + math.cos(a)*r, s.y + math.sin(a)*r, random.choice(list(ModType))))
            self.pickup_timer = 8.0

        self.station_timer -= dt
        if self.station_timer <= 0:
            self.stations = [st for st in self.stations if not st.used]
            if len(self.stations) == 0:
                a = random.uniform(0, math.tau); r = random.uniform(300, 500)
                self.stations.append(Station(s.x + math.cos(a)*r, s.y + math.sin(a)*r))
            self.station_timer = 25.0

        if s.hp <= 0:
            self.game_over = True

        self.redraw()

    def open_upgrade(self):
        self.upgrading = True
        self.upg_opts = random.sample(list(ModType), min(3, len(ModType)))
        App.get_running_app().root.add_widget(UpgradeMenu(self.upg_opts, self.apply_upgrade))

    def apply_upgrade(self, idx):
        app = App.get_running_app()
        for ch in app.root.children[:]:
            if isinstance(ch, UpgradeMenu): app.root.remove_widget(ch)
        if 0 <= idx < len(self.upg_opts):
            t = self.upg_opts[idx]
            s = self.snake
            for m in s.mods:
                if m["type"] == t:
                    m["lvl"] += 1; m["hp"] = m["max_hp"] * 1.2; m["max_hp"] *= 1.2
                    self.upgrading = False; self.redraw(); return
            s.add_mod(t)
        self.upgrading = False; self.redraw()

    def toggle_pause(self, inst):
        if self.game_over or self.upgrading: return
        self.paused = not self.paused
        app = App.get_running_app()
        for ch in app.root.children[:]:
            if isinstance(ch, PauseMenu): app.root.remove_widget(ch)
        if self.paused:
            def resume(i):
                self.paused = False
                for c in app.root.children[:]:
                    if isinstance(c, PauseMenu): app.root.remove_widget(c)
                self.redraw()
            def to_menu(i):
                for c in app.root.children[:]:
                    if isinstance(c, PauseMenu): app.root.remove_widget(c)
                app.stop_game()
            app.root.add_widget(PauseMenu(resume_cb=resume, menu_cb=to_menu))
        self.redraw()

    def redraw(self):
        self.canvas.clear()
        with self.canvas:
            Color(0.1, 0.1, 0.15)
            Rectangle(pos=(0, 0), size=(self.width, self.height))
            def scr(x, y): return x - self.snake.x + self.width/2, y - self.snake.y + self.height/2

            # Станции
            for st in self.stations:
                if st.used: continue
                sx, sy = scr(st.x, st.y)
                if -50 < sx < self.width+50 and -50 < sy < self.height+50:
                    Color(1, 0.8, 0.2); Ellipse(pos=(sx-20, sy-20), size=(40, 40))
                    Color(0.5, 0.3, 0); Line(circle=(sx, sy, 20), width=2)
                    Color(1, 0.8, 0.2); Rectangle(pos=(sx-3, sy-15), size=(6, 30))
                    Rectangle(pos=(sx-15, sy-3), size=(30, 6))

            # Враги
            for e in self.enemies:
                sx, sy = scr(e.x, e.y)
                if -50 < sx < self.width+50 and -50 < sy < self.height+50:
                    Color(*e.color)
                    Ellipse(pos=(sx-e.radius, sy-e.radius), size=(e.radius*2, e.radius*2))
                    if e.tesla_hit > 0:
                        Color(0.6, 1, 1, 0.8); Ellipse(pos=(sx-e.radius-5, sy-e.radius-5),
                                                       size=((e.radius+5)*2, (e.radius+5)*2))
                    # HP-полоска
                    Color(0.3, 0, 0); Rectangle(pos=(sx-14, sy-e.radius-8), size=(28, 4))
                    Color(0, 0.8, 0); Rectangle(pos=(sx-14, sy-e.radius-8),
                                                size=(28*max(0, e.hp/e.max_hp), 4))

            # Пикапы
            for p in self.pickups:
                sx, sy = scr(p.x, p.y)
                if -50 < sx < self.width+50 and -50 < sy < self.height+50:
                    Color(*MOD_DATA[p.mtype]["color"]); Ellipse(pos=(sx-12, sy-12), size=(24, 24))

            # Взрывы
            for ex in self.explosions:
                sx, sy = scr(ex.x, ex.y)
                t = ex.life / ex.max_life
                r = ex.radius * (1.2 - t * 0.6)
                Color(1, 0.5, 0.1, t); Ellipse(pos=(sx-r, sy-r), size=(r*2, r*2))

            # Пули
            for b in self.bullets:
                sx, sy = scr(b.x, b.y)
                if -50 < sx < self.width+50 and -50 < sy < self.height+50:
                    if b.is_enemy: Color(1, 0.3, 0.3)
                    elif b.is_grenade: Color(0.8, 0.5, 0.2)
                    else: Color(1, 0.9, 0.2)
                    Ellipse(pos=(sx-4, sy-4), size=(8, 8))

            # Молнии Теслы
            for tl in self.tesla_lines:
                pts = []
                for px, py in tl.points:
                    sx, sy = scr(px, py); pts.extend([sx, sy])
                if len(pts) >= 4:
                    Color(0.4, 1, 1, tl.life / 0.15)
                    Line(points=pts, width=2)

            # Змея
            s = self.snake
            c_head, c_body = (0.2, 0.8, 0.4), (0.1, 0.6, 0.3)
            if PLAYER.snake_skin == 1: c_head, c_body = (0.8, 0.2, 0.2), (0.6, 0.1, 0.1)
            elif PLAYER.snake_skin == 2: c_head, c_body = (0.2, 0.2, 0.8), (0.1, 0.1, 0.6)

            for b in s.body:
                sx, sy = scr(b[0], b[1])
                if -50 < sx < self.width+50 and -50 < sy < self.height+50:
                    Color(*c_body)
                    Rectangle(pos=(sx-CELL*0.4, sy-CELL*0.4), size=(CELL*0.8, CELL*0.8))

            hx, hy = scr(s.x, s.y)
            Color(*c_head)
            Ellipse(pos=(hx-CELL*0.6, hy-CELL*0.6), size=(CELL*1.2, CELL*1.2))

            # Модули + эффекты (топоры, щит)
            for i, m in enumerate(s.mods):
                if m["type"] == ModType.DRONE: continue
                if i >= len(s.body): break
                mx, my = scr(s.body[i][0], s.body[i][1])
                if not (-50 < mx < self.width+50 and -50 < my < self.height+50): continue
                Color(*MOD_DATA[m["type"]]["color"])
                Rectangle(pos=(mx-CELL*0.3, my-CELL*0.3), size=(CELL*0.6, CELL*0.6))

                # Полоска HP модуля
                Color(0.3, 0, 0); Rectangle(pos=(mx-12, my+CELL*0.55), size=(24, 3))
                hp_ratio = max(0, m["hp"] / m["max_hp"])
                Color(0, 0.85, 0.3); Rectangle(pos=(mx-12, my+CELL*0.55), size=(24*hp_ratio, 3))

                # ТОПОРЫ — два крутящихся круга вокруг модуля
                if m["type"] == ModType.AXES:
                    t = Clock.get_boottime() * 3.0
                    for k in range(2):
                        ang = t + k * math.pi
                        ax = mx + math.cos(ang) * 40
                        ay = my + math.sin(ang) * 40
                        Color(0.7, 0.7, 0.7); Ellipse(pos=(ax-8, ay-8), size=(16, 16))
                        Color(0.5, 0.35, 0.1); Ellipse(pos=(ax-4, ay-4), size=(8, 8))

                # ЩИТ — два круга вокруг модуля
                if m["type"] == ModType.SHIELD:
                    t = Clock.get_boottime() * 2.5
                    for k in range(2):
                        ang = t + k * math.pi
                        sx2 = mx + math.cos(ang) * 35
                        sy2 = my + math.sin(ang) * 35
                        Color(1, 0.9, 0.5); Ellipse(pos=(sx2-12, sy2-12), size=(24, 24))
                        Color(1, 0.7, 0); Line(circle=(sx2, sy2, 12), width=2)

            # Дрон
            if any(m["type"] == ModType.DRONE for m in s.mods):
                dx, dy = scr(s.drone_x, s.drone_y)
                if -50 < dx < self.width+50 and -50 < dy < self.height+50:
                    Color(0.7, 0.7, 0.7); Rectangle(pos=(dx-10, dy-10), size=(20, 20))
                    Color(0.4, 0.9, 0.9); Rectangle(pos=(dx-5, dy-5), size=(10, 10))

            # Джойстик
            jx, jy = self.width * 0.85, self.height * 0.15
            r = min(self.width, self.height) * 0.12
            Color(0.3, 0.3, 0.4, 0.5); Ellipse(pos=(jx-r, jy-r), size=(r*2, r*2))
            Color(0.8, 0.8, 0.2); Ellipse(pos=(jx+s.dx*r*0.6-15, jy+s.dy*r*0.6-15), size=(30, 30))

    def on_touch_down(self, touch):
        if self.upgrading or self.game_over or self.paused: return super().on_touch_down(touch)
        jx, jy = self.width * 0.85, self.height * 0.15
        if (touch.x-jx)**2 + (touch.y-jy)**2 < (min(self.width, self.height)*0.15)**2:
            touch.ud['joy'] = True; return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.ud.get('joy'):
            jx, jy = self.width * 0.85, self.height * 0.15
            dx, dy = touch.x-jx, touch.y-jy
            d = math.hypot(dx, dy)
            if d > 20:
                self.snake.dx, self.snake.dy = dx/d, dy/d
            return True
        return super().on_touch_move(touch)

# ---------- Меню ----------
class MainMenu(BoxLayout):
    def __init__(self, start_cb, shop_cb, **kwargs):
        super().__init__(orientation='vertical', padding=dp(30), spacing=dp(15), **kwargs)
        self.add_widget(Label(text="ЗМЕЙКА-РОГАЛИК", font_size=sp(30), bold=True,
                              color=(1, 0.8, 0.2), size_hint_y=0.3))
        b = Button(text="ИГРАТЬ", font_size=sp(20), size_hint=(None, None),
                   size=(dp(250), dp(60)), pos_hint={'center_x': 0.5})
        b.bind(on_press=start_cb); self.add_widget(b)
        b = Button(text="МАГАЗИН", font_size=sp(20), size_hint=(None, None),
                   size=(dp(250), dp(60)), pos_hint={'center_x': 0.5})
        b.bind(on_press=shop_cb); self.add_widget(b)
        b = Button(text="ВЫЙТИ", font_size=sp(20), size_hint=(None, None),
                   size=(dp(250), dp(60)), pos_hint={'center_x': 0.5},
                   background_color=(0.8, 0.2, 0.2, 1))
        b.bind(on_press=App.get_running_app().stop); self.add_widget(b)

class ShopMenu(BoxLayout):
    def __init__(self, back_cb, **kwargs):
        super().__init__(orientation='vertical', padding=dp(20), spacing=dp(10), **kwargs)
        self.add_widget(Label(text=f"Баланс: {PLAYER.money} $", font_size=sp(20),
                              color=(1, 0.8, 0.2), size_hint_y=0.2))
        row1 = BoxLayout(size_hint_y=0.2)
        row1.add_widget(Label(text="Змея:", font_size=sp(16)))
        for nm, sid, cost in [("Зеленая",0,0), ("Красная (100)",1,100), ("Синяя (100)",2,100)]:
            b = Button(text=nm, font_size=sp(14))
            b.bind(on_press=lambda x, s=sid, c=cost: self.buy_skin(s, c))
            row1.add_widget(b)
        self.add_widget(row1)
        row2 = BoxLayout(size_hint_y=0.2)
        row2.add_widget(Label(text="Улучшения:", font_size=sp(16)))
        b = Button(text="Скорость (200)", font_size=sp(14)); b.bind(on_press=self.buy_legs)
        row2.add_widget(b)
        b = Button(text="HP (300)", font_size=sp(14)); b.bind(on_press=self.buy_skin_hp)
        row2.add_widget(b)
        self.add_widget(row2)
        self.add_widget(Widget(size_hint_y=0.2))
        b = Button(text="НАЗАД", font_size=sp(20), size_hint=(None, None),
                   size=(dp(200), dp(50)), pos_hint={'center_x': 0.5})
        b.bind(on_press=back_cb); self.add_widget(b)

    def buy_skin(self, sid, cost):
        if sid not in PLAYER.owned_snake_skins and PLAYER.money >= cost:
            PLAYER.money -= cost; PLAYER.owned_snake_skins.append(sid)
        if sid in PLAYER.owned_snake_skins: PLAYER.snake_skin = sid
        PLAYER.save(); App.get_running_app().update_shop_ui()

    def buy_legs(self, inst):
        if not PLAYER.upg_legs and PLAYER.money >= 200:
            PLAYER.money -= 200; PLAYER.upg_legs = True
            PLAYER.save(); App.get_running_app().update_shop_ui()

    def buy_skin_hp(self, inst):
        if not PLAYER.upg_skin and PLAYER.money >= 300:
            PLAYER.money -= 300; PLAYER.upg_skin = True
            PLAYER.save(); App.get_running_app().update_shop_ui()

# ---------- App ----------
class SnakeApp(App):
    def build(self):
        self.root = FloatLayout()
        self.show_menu()
        return self.root

    def show_menu(self):
        self.root.clear_widgets()
        self.root.add_widget(MainMenu(start_cb=self.start_game, shop_cb=self.show_shop))

    def show_shop(self, inst):
        self.root.clear_widgets()
        self.root.add_widget(ShopMenu(back_cb=lambda x: self.show_menu()))

    def update_shop_ui(self):
        self.show_shop(None)

    def start_game(self, inst):
        self.root.clear_widgets()
        self.game = GameWidget()
        self.root.add_widget(self.game)

        # HUD справа сверху
        self.hud = Label(text="", pos_hint={'right': 0.98, 'top': 0.98},
                         size_hint=(0.5, 0.3), font_size=sp(14), bold=True,
                         halign='right', valign='top')
        self.hud.bind(size=self.hud.setter('text_size'))
        self.root.add_widget(self.hud)

        # Кнопка паузы
        self.pause_btn = Button(text="II", size_hint=(None, None), size=(dp(50), dp(50)),
                                pos_hint={'x': 0.02, 'top': 0.9},
                                background_color=(0.3, 0.3, 0.3, 0.7))
        self.pause_btn.bind(on_press=self.game.toggle_pause)
        self.root.add_widget(self.pause_btn)

        Clock.schedule_interval(self.update_hud, 0.1)

    def stop_game(self):
        if hasattr(self, 'game') and self.game:
            PLAYER.money += self.game.snake.money
            if self.game.wave > PLAYER.high_score:
                PLAYER.high_score = self.game.wave
            PLAYER.save()
        try: Clock.unschedule(self.update_hud)
        except: pass
        self.show_menu()

    def update_hud(self, dt):
        if hasattr(self, 'game') and self.game:
            g = self.game; s = g.snake
            status = " (ПАУЗА)" if g.paused else ""
            self.hud.text = (f"HP: {int(s.hp)}/{s.max_hp}{status}\n"
                             f"Ур: {s.level}\n"
                             f"Волна: {g.wave}\n"
                             f"$: {s.money}")

    def on_stop(self):
        if hasattr(self, 'game') and self.game:
            PLAYER.money += self.game.snake.money
            if self.game.wave > PLAYER.high_score:
                PLAYER.high_score = self.game.wave
        PLAYER.save()

if __name__ == '__main__':
    SnakeApp().run()
