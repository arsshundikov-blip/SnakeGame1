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
        self.gun_skin = 0
        self.owned_snake_skins = [0]
        self.owned_gun_skins = [0]
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
                    self.gun_skin = d.get("gun_skin", 0)
                    self.owned_snake_skins = d.get("owned_snake_skins", [0])
                    self.owned_gun_skins = d.get("owned_gun_skins", [0])
                    self.upg_legs = d.get("upg_legs", False)
                    self.upg_skin = d.get("upg_skin", False)
            except: pass

    def save(self):
        d = {
            "money": self.money, "high_score": self.high_score,
            "snake_skin": self.snake_skin, "gun_skin": self.gun_skin,
            "owned_snake_skins": self.owned_snake_skins, "owned_gun_skins": self.owned_gun_skins,
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

# ---------- Игровые классы ----------
class Enemy:
    def __init__(self, x, y, hp, speed, radius, color, dmg):
        self.x, self.y = x, y; self.hp, self.max_hp = hp, hp
        self.speed, self.radius, self.color, self.damage = speed, radius, color, dmg

class Bullet:
    def __init__(self, x, y, vx, vy, dmg, enemy=False):
        self.x, self.y, self.vx, self.vy, self.dmg, self.enemy = x, y, vx, vy, dmg, enemy

class Pickup:
    def __init__(self, x, y, mtype): self.x, self.y, self.mtype = x, y, mtype

class Snake:
    def __init__(self):
        self.x, self.y = 0.0, 0.0; self.dx, self.dy = 1.0, 0.0
        self.speed = 200 * (1.2 if PLAYER.upg_legs else 1.0)
        self.hp, self.max_hp = 100 + (30 if PLAYER.upg_skin else 0), 100 + (30 if PLAYER.upg_skin else 0)
        self.body = []; self.mods = []; self.lost_mods = []
        self.level, self.xp, self.xp_next = 1, 0, 10
        self.money, self.boosters, self.heals = 0, 0, 0
        self.cooldown = 0.0
        
        self._grow(); self._grow(); self._grow()
        self.add_mod(ModType.PISTOL)

    def _grow(self):
        if not self.body: self.body.append([self.x - self.dx*25, self.y - self.dy*25])
        else:
            last = self.body[-1]; self.body.append([last[0], last[1]])

    def add_mod(self, mtype):
        self.mods.append({"type": mtype, "hp": MOD_DATA[mtype]["hp"], "max_hp": MOD_DATA[mtype]["hp"], "lvl": 1, "cd": 0.0})
        self._grow()

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
        self.wave, self.wave_timer = 0, 2.0
        self.pickup_timer = 5.0
        self.game_over, self.paused, self.upgrading = False, False, False
        self.upg_opts = []
        self.msg_timer, self.msg_text = 0, ""

    def msg(self, text, t=2.0): self.msg_text, self.msg_timer = text, t

    def update(self, dt):
        if self.game_over or self.paused or self.upgrading or self.width <= 0: return
        if self.msg_timer > 0: self.msg_timer -= dt

        s = self.snake
        # Движение
        s.x += s.dx * s.speed * dt; s.y += s.dy * s.speed * dt
        target = [s.x, s.y]
        for i in range(len(s.body)):
            dx, dy = target[0] - s.body[i][0], target[1] - s.body[i][1]
            d = math.hypot(dx, dy)
            if d > 25: s.body[i] = [target[0] - dx/d*25, target[1] - dy/d*25]
            target = s.body[i]

        # Модули
        for i, m in enumerate(s.mods):
            m["cd"] = max(0, m["cd"] - dt)
            if m["type"] in GUN_STATS and m["cd"] <= 0:
                pos = s.body[i] if i < len(s.body) else s.body[-1]
                best, tgt = 999999, None
                for e in self.enemies:
                    d = (pos[0]-e.x)**2 + (pos[1]-e.y)**2
                    if d < 400**2 and d < best: best, tgt = d, e
                if tgt:
                    ang = math.atan2(tgt.y-pos[1], tgt.x-pos[0])
                    dmg, _, cd = GUN_STATS[m["type"]]
                    if m["type"] == ModType.TESLA:
                        tgt.hp -= dmg * (1 + 0.2*m["lvl"])
                        m["cd"] = cd
                    else:
                        self.bullets.append(Bullet(pos[0], pos[1], math.cos(ang)*600, math.sin(ang)*600, dmg*(1+0.2*m["lvl"])))
                        m["cd"] = cd

        # Пули
        for b in self.bullets[:]:
            b.x += b.vx * dt; b.y += b.vy * dt
            hit = False
            if not b.enemy:
                for e in self.enemies[:]:
                    if (b.x-e.x)**2 + (b.y-e.y)**2 < (e.radius+8)**2:
                        e.hp -= b.dmg; hit = True; break
            if hit or (b.x-s.x)**2 + (b.y-s.y)**2 > 1500**2: self.bullets.remove(b)

        # Враги
        for e in self.enemies[:]:
            ang = math.atan2(s.y-e.y, s.x-e.x)
            e.x += math.cos(ang) * e.speed * dt; e.y += math.sin(ang) * e.speed * dt
            if (e.x-s.x)**2 + (e.y-s.y)**2 < (e.radius+15)**2:
                s.hp -= e.damage * dt * 2
            if e.hp <= 0:
                self.enemies.remove(e); s.money += 5; s.xp += 3
                if s.xp >= s.xp_next:
                    s.xp -= s.xp_next; s.level += 1; s.xp_next = int(s.xp_next * 1.5)
                    self.open_upgrade()

        # Подбор
        for p in self.pickups[:]:
            if (p.x-s.x)**2 + (p.y-s.y)**2 < (20+15)**2:
                self.pickups.remove(p)
                s.add_mod(p.mtype); self.msg(f"+{MOD_DATA[p.mtype]['name']}")

        # Таймеры
        self.wave_timer -= dt
        if self.wave_timer <= 0:
            self.wave += 1; self.wave_timer = 10.0
            for _ in range(min(5 + self.wave*2, 30)):
                a = random.uniform(0, math.tau); r = random.uniform(300, 600)
                self.enemies.append(Enemy(s.x+math.cos(a)*r, s.y+math.sin(a)*r, 10+self.wave*5, 60+self.wave*2, 15, (1, 0.3, 0.3), 10))
        
        self.pickup_timer -= dt
        if self.pickup_timer <= 0 and len(self.pickups) < 5:
            a = random.uniform(0, math.tau); r = random.uniform(100, 400)
            self.pickups.append(Pickup(s.x+math.cos(a)*r, s.y+math.sin(a)*r, random.choice(list(ModType))))
            self.pickup_timer = 6.0

        if s.hp <= 0: self.game_over = True
        self.redraw()

    def open_upgrade(self):
        self.upgrading = True
        self.upg_opts = random.sample(list(ModType), 3)

    def apply_upgrade(self, idx):
        s = self.snake
        t = self.upg_opts[idx]
        for m in s.mods:
            if m["type"] == t: m["lvl"] += 1; self.upgrading = False; return
        s.add_mod(t); self.upgrading = False

    def redraw(self):
        self.canvas.clear()
        with self.canvas:
            Color(0.1, 0.1, 0.15); Rectangle(pos=(0,0), size=(self.width, self.height))
            def scr(x, y): return x - self.snake.x + self.width/2, y - self.snake.y + self.height/2
            
            # Враги
            for e in self.enemies:
                sx, sy = scr(e.x, e.y)
                if -50 < sx < self.width+50 and -50 < sy < self.height+50:
                    Color(*e.color); Ellipse(pos=(sx-e.radius, sy-e.radius), size=(e.radius*2, e.radius*2))
            
            # Пикапы
            for p in self.pickups:
                sx, sy = scr(p.x, p.y)
                if -50 < sx < self.width+50 and -50 < sy < self.height+50:
                    Color(*MOD_DATA[p.mtype]["color"]); Ellipse(pos=(sx-12, sy-12), size=(24, 24))

            # Пули
            for b in self.bullets:
                sx, sy = scr(b.x, b.y)
                if -50 < sx < self.width+50 and -50 < sy < self.height+50:
                    Color(1, 0.9, 0.2); Ellipse(pos=(sx-4, sy-4), size=(8, 8))

            # Змея
            s = self.snake
            c_head, c_body = (0.2, 0.8, 0.4), (0.1, 0.6, 0.3)
            if PLAYER.snake_skin == 1: c_head, c_body = (0.8, 0.2, 0.2), (0.6, 0.1, 0.1)
            elif PLAYER.snake_skin == 2: c_head, c_body = (0.2, 0.2, 0.8), (0.1, 0.1, 0.6)
            
            for b in s.body:
                sx, sy = scr(b[0], b[1])
                if -50 < sx < self.width+50 and -50 < sy < self.height+50:
                    Color(*c_body); Rectangle(pos=(sx-10, sy-10), size=(20, 20))
            
            hx, hy = scr(s.x, s.y)
            Color(*c_head); Ellipse(pos=(hx-15, hy-15), size=(30, 30))

            # Модули
            for i, m in enumerate(s.mods):
                if i < len(s.body):
                    sx, sy = scr(s.body[i][0], s.body[i][1])
                    Color(*MOD_DATA[m["type"]]["color"])
                    Rectangle(pos=(sx-7, sy-7), size=(14, 14))

            # Джойстик
            jx, jy = self.width * 0.85, self.height * 0.15
            r = min(self.width, self.height) * 0.12
            Color(0.3, 0.3, 0.4, 0.5); Ellipse(pos=(jx-r, jy-r), size=(r*2, r*2))
            Color(0.8, 0.8, 0.2); Ellipse(pos=(jx+s.dx*r*0.6-15, jy+s.dy*r*0.6-15), size=(30, 30))

    def on_touch_down(self, touch):
        if self.upgrading: return super().on_touch_down(touch)
        jx, jy = self.width * 0.85, self.height * 0.15
        if (touch.x-jx)**2 + (touch.y-jy)**2 < (min(self.width, self.height)*0.15)**2:
            touch.ud['joy'] = True; return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.ud.get('joy'):
            jx, jy = self.width * 0.85, self.height * 0.15
            dx, dy = touch.x-jx, touch.y-jy
            d = math.hypot(dx, dy)
            if d > 20: self.snake.dx, self.snake.dy = dx/d, dy/d
            return True
        return super().on_touch_move(touch)

# ---------- Меню ----------
class MainMenu(BoxLayout):
    def __init__(self, start_cb, shop_cb, best_cb, **kwargs):
        super().__init__(orientation='vertical', padding=dp(30), spacing=dp(15), **kwargs)
        
        title = Label(text="ЗМЕЙКА-РОГАЛИК", font_size=sp(30), bold=True, color=(1, 0.8, 0.2), size_hint_y=0.3)
        self.add_widget(title)
        
        btn_play = Button(text="ИГРАТЬ", font_size=sp(20), size_hint=(None, None), size=(dp(250), dp(60)), pos_hint={'center_x': 0.5})
        btn_play.bind(on_press=start_cb); self.add_widget(btn_play)
        
        btn_shop = Button(text="МАГАЗИН", font_size=sp(20), size_hint=(None, None), size=(dp(250), dp(60)), pos_hint={'center_x': 0.5})
        btn_shop.bind(on_press=shop_cb); self.add_widget(btn_shop)
        
        btn_best = Button(text="БЕСТИАРИЙ", font_size=sp(20), size_hint=(None, None), size=(dp(250), dp(60)), pos_hint={'center_x': 0.5})
        btn_best.bind(on_press=best_cb); self.add_widget(btn_best)
        
        btn_exit = Button(text="ВЫЙТИ", font_size=sp(20), size_hint=(None, None), size=(dp(250), dp(60)), pos_hint={'center_x': 0.5}, background_color=(0.8,0.2,0.2,1))
        btn_exit.bind(on_press=App.get_running_app().stop); self.add_widget(btn_exit)

class ShopMenu(BoxLayout):
    def __init__(self, back_cb, **kwargs):
        super().__init__(orientation='vertical', padding=dp(20), spacing=dp(10), **kwargs)
        self.add_widget(Label(text=f"Баланс: {PLAYER.money} $", font_size=sp(20), color=(1, 0.8, 0.2), size_hint_y=0.2))
        
        # Скины змеи
        row1 = BoxLayout(size_hint_y=0.2)
        row1.add_widget(Label(text="Змея:", font_size=sp(16)))
        btn_s1 = Button(text="Зеленая", font_size=sp(14)); btn_s1.bind(on_press=lambda x: self.buy_skin('snake', 0, 0))
        btn_s2 = Button(text="Красная (100)", font_size=sp(14)); btn_s2.bind(on_press=lambda x: self.buy_skin('snake', 1, 100))
        btn_s3 = Button(text="Синяя (100)", font_size=sp(14)); btn_s3.bind(on_press=lambda x: self.buy_skin('snake', 2, 100))
        row1.add_widget(btn_s1); row1.add_widget(btn_s2); row1.add_widget(btn_s3)
        self.add_widget(row1)
        
        # Апгрейды
        row2 = BoxLayout(size_hint_y=0.2)
        row2.add_widget(Label(text="Улучшения:", font_size=sp(16)))
        btn_u1 = Button(text="Скорость (200)", font_size=sp(14)); btn_u1.bind(on_press=self.buy_upg_legs)
        btn_u2 = Button(text="HP (300)", font_size=sp(14)); btn_u2.bind(on_press=self.buy_upg_skin)
        row2.add_widget(btn_u1); row2.add_widget(btn_u2)
        self.add_widget(row2)
        
        self.add_widget(Widget(size_hint_y=0.2))
        
        btn_back = Button(text="НАЗАД", font_size=sp(20), size_hint=(None, None), size=(dp(200), dp(50)), pos_hint={'center_x': 0.5})
        btn_back.bind(on_press=back_cb); self.add_widget(btn_back)

    def buy_skin(self, typ, sid, cost):
        if typ == 'snake':
            if sid not in PLAYER.owned_snake_skins and PLAYER.money >= cost:
                PLAYER.money -= cost; PLAYER.owned_snake_skins.append(sid)
            if sid in PLAYER.owned_snake_skins: PLAYER.snake_skin = sid
            PLAYER.save()
            App.get_running_app().update_shop_ui()

    def buy_upg_legs(self, inst):
        if not PLAYER.upg_legs and PLAYER.money >= 200:
            PLAYER.money -= 200; PLAYER.upg_legs = True; PLAYER.save(); App.get_running_app().update_shop_ui()

    def buy_upg_skin(self, inst):
        if not PLAYER.upg_skin and PLAYER.money >= 300:
            PLAYER.money -= 300; PLAYER.upg_skin = True; PLAYER.save(); App.get_running_app().update_shop_ui()

class BestiaryMenu(BoxLayout):
    def __init__(self, back_cb, **kwargs):
        super().__init__(orientation='vertical', padding=dp(20), **kwargs)
        self.add_widget(Label(text="БЕСТИАРИЙ", font_size=sp(24), bold=True, color=(1, 0.8, 0.2), size_hint_y=0.2))
        
        scroll = BoxLayout(orientation='vertical', size_hint_y=0.7)
        for m, data in MOD_DATA.items():
            row = BoxLayout(size_hint_y=None, height=dp(40))
            row.add_widget(Label(text=data["name"], color=RARITY_COLORS[data["rarity"]], font_size=sp(14)))
            scroll.add_widget(row)
        self.add_widget(scroll)
        
        btn_back = Button(text="НАЗАД", font_size=sp(20), size_hint=(None, None), size=(dp(200), dp(50)), pos_hint={'center_x': 0.5})
        btn_back.bind(on_press=back_cb); self.add_widget(btn_back)

# ---------- Приложение ----------
class SnakeApp(App):
    def build(self):
        self.root = FloatLayout()
        self.show_menu()
        return self.root

    def show_menu(self):
        self.root.clear_widgets()
        self.menu = MainMenu(start_cb=self.start_game, shop_cb=self.show_shop, best_cb=self.show_bestiary)
        self.root.add_widget(self.menu)

    def show_shop(self, inst):
        self.root.clear_widgets()
        self.shop = ShopMenu(back_cb=lambda x: self.show_menu())
        self.root.add_widget(self.shop)

    def update_shop_ui(self):
        self.show_shop(None)

    def show_bestiary(self, inst):
        self.root.clear_widgets()
        self.bestiary = BestiaryMenu(back_cb=lambda x: self.show_menu())
        self.root.add_widget(self.bestiary)

    def start_game(self, inst):
        self.root.clear_widgets()
        self.game = GameWidget()
        self.root.add_widget(self.game)
        
        # HUD поверх игры
        self.hud = Label(text="", pos_hint={'x': 0.02, 'top': 0.98}, size_hint=(0.5, 0.2), font_size=sp(14), bold=True)
        self.root.add_widget(self.hud)
        Clock.schedule_interval(self.update_hud, 0.1)

    def update_hud(self, dt):
        if hasattr(self, 'game') and self.game:
            g = self.game; s = g.snake
            self.hud.text = f"HP: {int(s.hp)}/{s.max_hp}\nУр: {s.level} | Волна: {g.wave}\n$: {s.money}"

    def on_stop(self):
        if hasattr(self, 'game') and self.game:
            PLAYER.money += self.game.snake.money
            if self.game.wave > PLAYER.high_score: PLAYER.high_score = self.game.wave
            PLAYER.save()

if __name__ == '__main__':
    SnakeApp().run()
