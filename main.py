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
            except: pass

    def save(self):
        d = {
            "money": self.money, "high_score": self.high_score,
            "snake_skin": self.snake_skin, "owned_snake_skins": self.owned_snake_skins,
            "upg_legs": self.upg_legs, "upg_skin": self.upg_skin
        }
        try:
            with open(get_save_path(), "w", encoding="utf-8") as f: json.dump(d, f)
        except: pass

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
GUN_STATS = {ModType.PISTOL: (12, 340, 0.55), ModType.RIFLE: (6, 300, 0.13), ModType.SNIPER: (40, 620, 1.4), ModType.TESLA: (15, 250, 0.8), ModType.GRENADE: (30, 400, 1.2), ModType.DRONE: (8, 300, 0.4)}
RARITY_COLORS = {1: (0.8, 0.8, 0.8), 2: (0.4, 0.8, 1), 3: (0.7, 0.4, 1), 4: (1, 0.4, 0.8), 5: (1, 0.8, 0.2)}

CELL = 25
MAX_BULLETS = 60
MAX_ENEMIES = 30
MAX_PICKUPS = 3

# ---------- Игровые классы ----------
class Enemy:
    def __init__(self, x, y, hp, speed, radius, color, dmg):
        self.x, self.y = x, y; self.hp, self.max_hp = hp, hp
        self.speed, self.radius, self.color, self.damage = speed, radius, color, dmg

class Bullet:
    def __init__(self, x, y, vx, vy, dmg, is_grenade=False, life=1.5):
        self.x, self.y, self.vx, self.vy, self.dmg = x, y, vx, vy, dmg
        self.is_grenade = is_grenade
        self.life = life

class Pickup:
    def __init__(self, x, y, mtype): self.x, self.y, self.mtype = x, y, mtype

class Explosion:
    def __init__(self, x, y, radius, life=0.3):
        self.x, self.y = x, y
        self.radius = radius
        self.life = life
        self.max_life = life

class Snake:
    def __init__(self):
        self.x, self.y = 0.0, 0.0
        self.dx, self.dy = 1.0, 0.0
        self.speed = 180 * (1.2 if PLAYER.upg_legs else 1.0)
        self.hp = 100 + (30 if PLAYER.upg_skin else 0)
        self.max_hp = self.hp
        self.body = [[self.x - CELL, self.y]]
        self.mods = []
        self.level, self.xp, self.xp_next = 1, 0, 10
        self.money = 0
        self.drone_angle = 0.0
        self.drone_x, self.drone_y = 0.0, 0.0
        self.add_mod(ModType.PISTOL)

    def add_mod(self, mtype):
        self.mods.append({"type": mtype, "lvl": 1, "cd": 0.0})
        last = self.body[-1] if self.body else [self.x, self.y]
        self.body.append([last[0], last[1]])

# ---------- Меню улучшений ----------
class UpgradeMenu(FloatLayout):
    def __init__(self, options, callback, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 0.7)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        layout = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(20),
                           size_hint=(0.8, 0.8), pos_hint={'center_x': 0.5, 'center_y': 0.5})

        title = Label(text="УРОВЕНЬ ПОВЫШЕН!", font_size=sp(24), bold=True, color=(1, 0.8, 0.2), size_hint_y=0.2)
        layout.add_widget(title)

        for i, opt in enumerate(options):
            mtype = opt
            btn = Button(text=f"{MOD_DATA[mtype]['name']}", font_size=sp(18),
                         size_hint_y=0.2, background_color=(*MOD_DATA[mtype]['color'], 1))
            btn.bind(on_press=lambda inst, idx=i: callback(idx))
            layout.add_widget(btn)

        self.add_widget(layout)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

# ---------- Главный Игровой Виджет ----------
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
        self.explosions, self.lightning = [], []
        self.wave, self.wave_timer = 0, 3.0
        self.pickup_timer = 6.0
        self.game_over, self.upgrading, self.paused = False, False, False
        self.upg_opts = []

    def update(self, dt):
        # --- ЭФФЕКТЫ (обновляются всегда) ---
        for ex in self.explosions[:]:
            ex.life -= dt
            if ex.life <= 0:
                self.explosions.remove(ex)
        for l in self.lightning[:]:
            l[4] -= dt
            if l[4] <= 0:
                self.lightning.remove(l)

        if self.game_over or self.upgrading or self.paused or self.width <= 0:
            self.redraw()
            return

        s = self.snake
        s.x += s.dx * s.speed * dt
        s.y += s.dy * s.speed * dt

        tx, ty = s.x, s.y
        for i in range(len(s.body)):
            dx = tx - s.body[i][0]
            dy = ty - s.body[i][1]
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

                # Дрон стреляет со своей позиции
                if m["type"] == ModType.DRONE:
                    mx, my = s.drone_x, s.drone_y

                best_dist, target_enemy = 350**2, None
                for e in self.enemies:
                    d2 = (mx - e.x)**2 + (my - e.y)**2
                    if d2 < best_dist:
                        best_dist, target_enemy = d2, e

                if target_enemy:
                    ang = math.atan2(target_enemy.y - my, target_enemy.x - mx)
                    dmg, _, cd = GUN_STATS[m["type"]]
                    dmg_lvl = dmg * (1 + 0.2 * m["lvl"])

                    if m["type"] == ModType.TESLA:
                        # Цепочка до 4 целей
                        chain = [target_enemy]
                        cur = target_enemy
                        for _ in range(3):
                            bd, nt = 200**2, None
                            for e in self.enemies:
                                if e in chain: continue
                                d2 = (cur.x - e.x)**2 + (cur.y - e.y)**2
                                if d2 < bd:
                                    bd, nt = d2, e
                            if nt:
                                chain.append(nt)
                                cur = nt
                            else:
                                break
                        for ct in chain:
                            ct.hp -= dmg_lvl
                        # визуальная молния
                        if chain:
                            pts = [(mx, my)]
                            for ct in chain:
                                pts.append((ct.x, ct.y))
                            self.lightning.append([pts, 0.15])
                    elif m["type"] == ModType.GRENADE:
                        # Снаряд-граната
                        if len(self.bullets) < MAX_BULLETS:
                            self.bullets.append(Bullet(mx, my,
                                                       math.cos(ang) * 500,
                                                       math.sin(ang) * 500,
                                                       dmg_lvl, is_grenade=True, life=1.2))
                    else:
                        if len(self.bullets) < MAX_BULLETS:
                            self.bullets.append(Bullet(mx, my,
                                                       math.cos(ang) * 700,
                                                       math.sin(ang) * 700,
                                                       dmg_lvl))
                    m["cd"] = cd

        # --- ПУЛИ ---
        for b in self.bullets[:]:
            b.x += b.vx * dt
            b.y += b.vy * dt
            b.life -= dt

            hit = False
            for e in self.enemies[:]:
                if (b.x - e.x)**2 + (b.y - e.y)**2 < (e.radius + 8)**2:
                    if b.is_grenade:
                        # Взрыв
                        self.explosions.append(Explosion(b.x, b.y, 90, 0.4))
                        for ee in self.enemies[:]:
                            if (b.x - ee.x)**2 + (b.y - ee.y)**2 < 90**2:
                                ee.hp -= b.dmg
                    else:
                        e.hp -= b.dmg
                    hit = True
                    break

            if hit or b.life <= 0 or (b.x - s.x)**2 + (b.y - s.y)**2 > 1500**2:
                if b.is_grenade and not hit:
                    # Граната упала сама — взрыв
                    self.explosions.append(Explosion(b.x, b.y, 90, 0.4))
                    for ee in self.enemies[:]:
                        if (b.x - ee.x)**2 + (b.y - ee.y)**2 < 90**2:
                            ee.hp -= b.dmg
                if b in self.bullets:
                    self.bullets.remove(b)

        # --- ВРАГИ ---
        for e in self.enemies[:]:
            ang = math.atan2(s.y - e.y, s.x - e.x)
            e.x += math.cos(ang) * e.speed * dt
            e.y += math.sin(ang) * e.speed * dt
            if (e.x - s.x)**2 + (e.y - s.y)**2 < (e.radius + 15)**2:
                s.hp -= e.damage * dt * 2.0
            if e.hp <= 0:
                self.enemies.remove(e)
                s.money += 5
                s.xp += 3
                if s.xp >= s.xp_next:
                    s.xp -= s.xp_next
                    s.level += 1
                    s.xp_next = int(s.xp_next * 1.5)
                    self.open_upgrade()
                    return

        # --- ПОДБОР ---
        for p in self.pickups[:]:
            if (p.x - s.x)**2 + (p.y - s.y)**2 < (20 + 15)**2:
                self.pickups.remove(p)
                s.add_mod(p.mtype)

        # --- ТАЙМЕРЫ ---
        self.wave_timer -= dt
        if self.wave_timer <= 0:
            self.wave += 1
            self.wave_timer = 15.0
            if len(self.enemies) < MAX_ENEMIES:
                count = min(3 + self.wave, 10)
                for _ in range(count):
                    a = random.uniform(0, math.tau)
                    r = random.uniform(350, 600)
                    ex = s.x + math.cos(a) * r
                    ey = s.y + math.sin(a) * r
                    hp = 10 + self.wave * 5
                    spd = 50 + self.wave * 3
                    self.enemies.append(Enemy(ex, ey, hp, spd, 15, (1, 0.3, 0.3), 10))

        self.pickup_timer -= dt
        if self.pickup_timer <= 0 and len(self.pickups) < MAX_PICKUPS:
            a = random.uniform(0, math.tau)
            r = random.uniform(150, 400)
            px = s.x + math.cos(a) * r
            py = s.y + math.sin(a) * r
            self.pickups.append(Pickup(px, py, random.choice(list(ModType))))
            self.pickup_timer = 10.0

        if s.hp <= 0:
            self.game_over = True

        self.redraw()

    def open_upgrade(self):
        self.upgrading = True
        available_mods = list(ModType)
        self.upg_opts = random.sample(available_mods, min(3, len(available_mods)))
        app = App.get_running_app()
        menu = UpgradeMenu(options=self.upg_opts, callback=self.apply_upgrade)
        app.root.add_widget(menu)

    def apply_upgrade(self, idx):
        app = App.get_running_app()
        for child in app.root.children[:]:
            if isinstance(child, UpgradeMenu):
                app.root.remove_widget(child)

        if 0 <= idx < len(self.upg_opts):
            t = self.upg_opts[idx]
            s = self.snake
            found = False
            for m in s.mods:
                if m["type"] == t:
                    m["lvl"] += 1
                    found = True
                    break
            if not found:
                s.add_mod(t)

        self.upgrading = False
        self.redraw()

    def toggle_pause(self, inst):
        if not self.game_over and not self.upgrading:
            self.paused = not self.paused
            self.redraw()

    def redraw(self):
        self.canvas.clear()
        with self.canvas:
            Color(0.1, 0.1, 0.15)
            Rectangle(pos=(0, 0), size=(self.width, self.height))

            def scr(x, y):
                return x - self.snake.x + self.width / 2, y - self.snake.y + self.height / 2

            # Враги
            for e in self.enemies:
                sx, sy = scr(e.x, e.y)
                if -50 < sx < self.width + 50 and -50 < sy < self.height + 50:
                    Color(*e.color)
                    Ellipse(pos=(sx - e.radius, sy - e.radius), size=(e.radius * 2, e.radius * 2))

            # Пикапы
            for p in self.pickups:
                sx, sy = scr(p.x, p.y)
                if -50 < sx < self.width + 50 and -50 < sy < self.height + 50:
                    Color(*MOD_DATA[p.mtype]["color"])
                    Ellipse(pos=(sx - 12, sy - 12), size=(24, 24))

            # Взрывы
            for ex in self.explosions:
                sx, sy = scr(ex.x, ex.y)
                if -150 < sx < self.width + 150 and -150 < sy < self.height + 150:
                    t = ex.life / ex.max_life
                    r = ex.radius * (1.2 - t * 0.6)
                    Color(1, 0.5, 0.1, t)
                    Ellipse(pos=(sx - r, sy - r), size=(r * 2, r * 2))

            # Пули
            for b in self.bullets:
                sx, sy = scr(b.x, b.y)
                if -50 < sx < self.width + 50 and -50 < sy < self.height + 50:
                    if b.is_grenade:
                        Color(0.8, 0.5, 0.2)
                        Ellipse(pos=(sx - 7, sy - 7), size=(14, 14))
                    else:
                        Color(1, 0.9, 0.2)
                        Ellipse(pos=(sx - 4, sy - 4), size=(8, 8))

            # Молнии
            for item in self.lightning:
                pts, _ = item
                screen_pts = []
                for p in pts:
                    sx, sy = scr(p[0], p[1])
                    screen_pts.extend([sx, sy])
                if len(screen_pts) >= 4:
                    Color(0.5, 1, 1)
                    Line(points=screen_pts, width=2)

            # Змея
            s = self.snake
            c_head, c_body = (0.2, 0.8, 0.4), (0.1, 0.6, 0.3)
            if PLAYER.snake_skin == 1: c_head, c_body = (0.8, 0.2, 0.2), (0.6, 0.1, 0.1)
            elif PLAYER.snake_skin == 2: c_head, c_body = (0.2, 0.2, 0.8), (0.1, 0.1, 0.6)

            for b in s.body:
                sx, sy = scr(b[0], b[1])
                if -50 < sx < self.width + 50 and -50 < sy < self.height + 50:
                    Color(*c_body)
                    Rectangle(pos=(sx - CELL * 0.4, sy - CELL * 0.4), size=(CELL * 0.8, CELL * 0.8))

            hx, hy = scr(s.x, s.y)
            Color(*c_head)
            Ellipse(pos=(hx - CELL * 0.6, hy - CELL * 0.6), size=(CELL * 1.2, CELL * 1.2))

            # Модули
            for i, m in enumerate(s.mods):
                if m["type"] == ModType.DRONE:
                    continue  # Дрон рисуем отдельно
                if i < len(s.body):
                    mx, my = scr(s.body[i][0], s.body[i][1])
                    if -50 < mx < self.width + 50 and -50 < my < self.height + 50:
                        Color(*MOD_DATA[m["type"]]["color"])
                        Rectangle(pos=(mx - CELL * 0.25, my - CELL * 0.25), size=(CELL * 0.5, CELL * 0.5))

            # Дрон
            if any(m["type"] == ModType.DRONE for m in s.mods):
                dx, dy = scr(s.drone_x, s.drone_y)
                if -50 < dx < self.width + 50 and -50 < dy < self.height + 50:
                    Color(0.7, 0.7, 0.7)
                    Rectangle(pos=(dx - 10, dy - 10), size=(20, 20))
                    Color(0.4, 0.9, 0.9)
                    Rectangle(pos=(dx - 5, dy - 5), size=(10, 10))

            # Джойстик
            jx, jy = self.width * 0.85, self.height * 0.15
            r = min(self.width, self.height) * 0.12
            Color(0.3, 0.3, 0.4, 0.5)
            Ellipse(pos=(jx - r, jy - r), size=(r * 2, r * 2))
            Color(0.8, 0.8, 0.2)
            Ellipse(pos=(jx + s.dx * r * 0.6 - 15, jy + s.dy * r * 0.6 - 15), size=(30, 30))

            # Пауза — затемнение
            if self.paused:
                Color(0, 0, 0, 0.6)
                Rectangle(pos=(0, 0), size=(self.width, self.height))

    def on_touch_down(self, touch):
        if self.upgrading or self.game_over:
            return super().on_touch_down(touch)

        jx, jy = self.width * 0.85, self.height * 0.15
        if (touch.x - jx)**2 + (touch.y - jy)**2 < (min(self.width, self.height) * 0.15)**2:
            touch.ud['joy'] = True
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.ud.get('joy'):
            jx, jy = self.width * 0.85, self.height * 0.15
            dx, dy = touch.x - jx, touch.y - jy
            d = math.hypot(dx, dy)
            if d > 20:
                self.snake.dx = dx / d
                self.snake.dy = dy / d
            return True
        return super().on_touch_move(touch)

# ---------- Меню ----------
class MainMenu(BoxLayout):
    def __init__(self, start_cb, shop_cb, **kwargs):
        super().__init__(orientation='vertical', padding=dp(30), spacing=dp(15), **kwargs)

        title = Label(text="ЗМЕЙКА-РОГАЛИК", font_size=sp(30), bold=True, color=(1, 0.8, 0.2), size_hint_y=0.3)
        self.add_widget(title)

        btn_play = Button(text="ИГРАТЬ", font_size=sp(20), size_hint=(None, None),
                          size=(dp(250), dp(60)), pos_hint={'center_x': 0.5})
        btn_play.bind(on_press=start_cb)
        self.add_widget(btn_play)

        btn_shop = Button(text="МАГАЗИН", font_size=sp(20), size_hint=(None, None),
                          size=(dp(250), dp(60)), pos_hint={'center_x': 0.5})
        btn_shop.bind(on_press=shop_cb)
        self.add_widget(btn_shop)

        btn_exit = Button(text="ВЫЙТИ", font_size=sp(20), size_hint=(None, None),
                          size=(dp(250), dp(60)), pos_hint={'center_x': 0.5},
                          background_color=(0.8, 0.2, 0.2, 1))
        btn_exit.bind(on_press=App.get_running_app().stop)
        self.add_widget(btn_exit)

class ShopMenu(BoxLayout):
    def __init__(self, back_cb, **kwargs):
        super().__init__(orientation='vertical', padding=dp(20), spacing=dp(10), **kwargs)
        self.add_widget(Label(text=f"Баланс: {PLAYER.money} $", font_size=sp(20), color=(1, 0.8, 0.2), size_hint_y=0.2))

        row1 = BoxLayout(size_hint_y=0.2)
        row1.add_widget(Label(text="Змея:", font_size=sp(16)))
        btn_s1 = Button(text="Зеленая", font_size=sp(14)); btn_s1.bind(on_press=lambda x: self.buy_skin(0, 0))
        btn_s2 = Button(text="Красная (100)", font_size=sp(14)); btn_s2.bind(on_press=lambda x: self.buy_skin(1, 100))
        btn_s3 = Button(text="Синяя (100)", font_size=sp(14)); btn_s3.bind(on_press=lambda x: self.buy_skin(2, 100))
        row1.add_widget(btn_s1); row1.add_widget(btn_s2); row1.add_widget(btn_s3)
        self.add_widget(row1)

        row2 = BoxLayout(size_hint_y=0.2)
        row2.add_widget(Label(text="Улучшения:", font_size=sp(16)))
        btn_u1 = Button(text="Скорость (200)", font_size=sp(14)); btn_u1.bind(on_press=self.buy_upg_legs)
        btn_u2 = Button(text="HP (300)", font_size=sp(14)); btn_u2.bind(on_press=self.buy_upg_skin)
        row2.add_widget(btn_u1); row2.add_widget(btn_u2)
        self.add_widget(row2)

        self.add_widget(Widget(size_hint_y=0.2))

        btn_back = Button(text="НАЗАД", font_size=sp(20), size_hint=(None, None),
                          size=(dp(200), dp(50)), pos_hint={'center_x': 0.5})
        btn_back.bind(on_press=back_cb)
        self.add_widget(btn_back)

    def buy_skin(self, sid, cost):
        if sid not in PLAYER.owned_snake_skins and PLAYER.money >= cost:
            PLAYER.money -= cost
            PLAYER.owned_snake_skins.append(sid)
        if sid in PLAYER.owned_snake_skins:
            PLAYER.snake_skin = sid
        PLAYER.save()
        App.get_running_app().update_shop_ui()

    def buy_upg_legs(self, inst):
        if not PLAYER.upg_legs and PLAYER.money >= 200:
            PLAYER.money -= 200
            PLAYER.upg_legs = True
            PLAYER.save()
            App.get_running_app().update_shop_ui()

    def buy_upg_skin(self, inst):
        if not PLAYER.upg_skin and PLAYER.money >= 300:
            PLAYER.money -= 300
            PLAYER.upg_skin = True
            PLAYER.save()
            App.get_running_app().update_shop_ui()

# ---------- Приложение ----------
class SnakeApp(App):
    def build(self):
        self.root = FloatLayout()
        self.show_menu()
        return self.root

    def show_menu(self):
        self.root.clear_widgets()
        self.menu = MainMenu(start_cb=self.start_game, shop_cb=self.show_shop)
        self.root.add_widget(self.menu)

    def show_shop(self, inst):
        self.root.clear_widgets()
        self.shop = ShopMenu(back_cb=lambda x: self.show_menu())
        self.root.add_widget(self.shop)

    def update_shop_ui(self):
        self.show_shop(None)

    def start_game(self, inst):
        self.root.clear_widgets()
        self.game = GameWidget()
        self.root.add_widget(self.game)

        self.hud = Label(text="", pos_hint={'x': 0.02, 'top': 0.98}, size_hint=(0.5, 0.2),
                         font_size=sp(14), bold=True)
        self.root.add_widget(self.hud)

        self.pause_btn = Button(text="II", size_hint=(None, None), size=(dp(50), dp(50)),
                                pos_hint={'x': 0.02, 'top': 0.9}, background_color=(0.3, 0.3, 0.3, 0.7))
        self.pause_btn.bind(on_press=self.game.toggle_pause)
        self.root.add_widget(self.pause_btn)

        Clock.schedule_interval(self.update_hud, 0.1)

    def update_hud(self, dt):
        if hasattr(self, 'game') and self.game:
            g = self.game
            s = g.snake
            status = "ПАУЗА" if g.paused else ""
            self.hud.text = f"HP: {int(s.hp)}/{s.max_hp}\nУр: {s.level} | Волна: {g.wave}\n$: {s.money} {status}"

    def on_stop(self):
        if hasattr(self, 'game') and self.game:
            PLAYER.money += self.game.snake.money
            if self.game.wave > PLAYER.high_score:
                PLAYER.high_score = self.game.wave
            PLAYER.save()

if __name__ == '__main__':
    SnakeApp().run()
