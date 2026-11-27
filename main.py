from kivy.config import Config
Config.set('graphics', 'multisamples', '0')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.metrics import dp, sp
from kivy.core.window import Window
import math
import random
import os
import json
from enum import Enum, auto

# ---------- Масштабирование под экран ----------
BASE_CELL = 25
CELL = 25
SCALE = 1.0

def update_scale():
    """Пересчитывает CELL и SCALE под текущий размер окна.
    Опорное разрешение — 720p (ландшафт), всё масштабируется пропорционально."""
    global CELL, SCALE
    try:
        w, h = Window.size
        if w > 0 and h > 0:
            SCALE = max(0.8, min(2.5, min(w, h) / 720.0))
    except Exception:
        SCALE = 1.0
    CELL = max(20, int(BASE_CELL * SCALE))

# ---------- Сохранения ----------
def get_save_path():
    app = App.get_running_app()
    if app:
        base = app.user_data_dir
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    try: os.makedirs(base, exist_ok=True)
    except: base = "/sdcard"
    return os.path.join(base, "save.json")

class PlayerData:
    def __init__(self):
        self.money = 0
        self.high_score = 0
        self.snake_skin = 0
        self.owned_snake_skins = [0]
        self.upg_legs = False
        self.upg_skin = False
        self.encountered_enemies = []
        self.obtained_modules = ["PISTOL"]
        self._save_path = None
        self.load()

    def load(self):
        path = get_save_path()
        self._save_path = path
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    # Явное приведение типов — защита от повреждённых данных
                    self.money = int(d.get("money", 0))
                    self.high_score = int(d.get("high_score", 0))
                    self.snake_skin = int(d.get("snake_skin", 0))
                    skins = d.get("owned_snake_skins", [0])
                    self.owned_snake_skins = [int(x) for x in skins] if isinstance(skins, list) else [0]
                    self.upg_legs = bool(d.get("upg_legs", False))
                    self.upg_skin = bool(d.get("upg_skin", False))
                    ee = d.get("encountered_enemies", [])
                    self.encountered_enemies = list(ee) if isinstance(ee, list) else []
                    om = d.get("obtained_modules", ["PISTOL"])
                    self.obtained_modules = list(om) if isinstance(om, list) else ["PISTOL"]
            except Exception as e:
                print("LOAD ERR:", e)
        else:
            # Первый запуск — сохраняем сразу, чтобы файл существовал
            self.save()

    def save(self):
        path = self._save_path or get_save_path()
        self._save_path = path
        d = {
            "money": self.money,
            "high_score": self.high_score,
            "snake_skin": self.snake_skin,
            "owned_snake_skins": self.owned_snake_skins,
            "upg_legs": self.upg_legs,
            "upg_skin": self.upg_skin,
            "encountered_enemies": self.encountered_enemies,
            "obtained_modules": self.obtained_modules
        }
        try:
            # Атомарная запись: пишем во временный файл, затем переименовываем
            tmp_path = path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False)
                f.flush()
            os.replace(tmp_path, path)
        except Exception as e:
            print("SAVE ERR:", e, "path:", path)
            # Запасной вариант — прямая запись без атомарности
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(d, f, ensure_ascii=False)
            except Exception as e2:
                print("SAVE FALLBACK ERR:", e2)

    def register_enemy(self, kind):
        if kind not in self.encountered_enemies:
            self.encountered_enemies.append(kind)

    def register_module(self, mtype):
        name = mtype.name if hasattr(mtype, 'name') else str(mtype)
        if name not in self.obtained_modules:
            self.obtained_modules.append(name)

PLAYER = None # Создадим в App.build()

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

# ---------- Данные для бестиария ----------
ENEMY_DATA = {
    "melee":   {"name": "Боец",    "color": (1, 0.3, 0.3),   "desc": "Базовый враг. Идёт прямо на змею. HP = 10 + волна*6, урон 10."},
    "fast":    {"name": "Быстрый", "color": (1, 0.5, 0.2),   "desc": "Быстрый и хрупкий. Появляется с 2 волны. HP = 60% от базового, урон 8."},
    "tank":    {"name": "Танк",    "color": (0.6, 0.2, 0.8), "desc": "Медленный и живучий. Появляется с 3 волны. HP = 200% от базового, урон 15."},
    "shooter": {"name": "Стрелок", "color": (1, 0.3, 0.8),   "desc": "Стреляет по змее, держит дистанцию. Появляется с 4 волны. Урон 6."},
    "boss":    {"name": "Босс",    "color": (0.9, 0.1, 0.1), "desc": "Появляется каждые 10 волн. Стреляет веером из 3 пуль. Большое здоровье. Награда 50$ и 30 XP."},
}

MOD_DESC = {
    ModType.PISTOL:  "Базовая пушка. Стреляет по ближайшему врагу. Скорость средняя.",
    ModType.RIFLE:   "Автомат. Высокая скорострельность, низкий урон за выстрел.",
    ModType.SNIPER:  "Снайперка. Большая дальность и урон, долгая перезарядка.",
    ModType.SHIELD:  "Защитные сферы вращаются вокруг модуля.",
    ModType.HEAL:    "Пассивно лечит змею и соседние модули каждые 1.5 сек.",
    ModType.BOOSTER: "Ускоритель. Мощный модуль с большим запасом прочности.",
    ModType.AXES:    "Вращающиеся лезвия вокруг модуля. Высокая прочность.",
    ModType.TESLA:   "Цепная молния бьёт до 4 врагов подряд.",
    ModType.GRENADE: "Гранатомёт. Взрыв с уроном по площади.",
    ModType.DRONE:   "Дрон летает вокруг змеи и стреляет по врагам.",
}

CELL = 25
MAX_BULLETS = 60
MAX_ENEMIES = 30
MAX_PICKUPS = 3

# ---------- Игровые классы ----------
class Enemy:
    def __init__(self, x, y, hp, speed, radius, color, dmg, kind="melee"):
        self.x, self.y = x, y; self.hp, self.max_hp = hp, hp
        self.speed, self.radius, self.color, self.damage = speed, radius, color, dmg
        self.kind = kind
        self.shoot_cd = 1.5
        self.tesla_hit = 0.0

class Bullet:
    def __init__(self, x, y, vx, vy, dmg, is_grenade=False, life=1.5, is_enemy=False):
        self.x, self.y, self.vx, self.vy, self.dmg = x, y, vx, vy, dmg
        self.is_grenade, self.life, self.is_enemy = is_grenade, life, is_enemy

class Pickup:
    def __init__(self, x, y, mtype): self.x, self.y, self.mtype = x, y, mtype

class Station:
    def __init__(self, x, y): self.x, self.y = x, y; self.used = False

class Explosion:
    def __init__(self, x, y, radius, life=0.3):
        self.x, self.y = x, y; self.radius, self.life, self.max_life = radius, life, life

class TeslaLine:
    def __init__(self, points): self.points = points; self.life = 0.15

class Snake:
    def __init__(self):
        self.x, self.y = 0.0, 0.0
        self.dx, self.dy = 1.0, 0.0
        self.speed = 180 * SCALE * (1.2 if PLAYER.upg_legs else 1.0)
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
        self.mods.append({
            "type": mtype, "hp": MOD_DATA[mtype]["hp"], "max_hp": MOD_DATA[mtype]["hp"],
            "lvl": 1, "cd": 0.0
        })
        last = self.body[-1] if self.body else [self.x, self.y]
        self.body.append([last[0], last[1]])
        PLAYER.register_module(mtype)

# ---------- Меню станции ----------
class StationMenu(FloatLayout):
    """Станция с 5 функциями: Лечение, Продажа, Покупка, Перестановка, Выход.
    Каждое подменю имеет свою кнопку «Назад» для возврата к главному меню станции."""
    def __init__(self, game_ref, **kwargs):
        super().__init__(**kwargs)
        self.game_ref = game_ref
        self.mode = "main"
        with self.canvas.before:
            Color(0, 0, 0, 0.75); self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        self._rebuild()

    # ---------- Построение UI ----------
    def _clear_content(self):
        for child in self.children[:]:
            self.remove_widget(child)

    def _rebuild(self):
        self._clear_content()
        if self.mode == "main":
            self._build_main()
        elif self.mode == "sell":
            self._build_sell()
        elif self.mode == "buy":
            self._build_buy()
        elif self.mode == "rearrange":
            self._build_rearrange()

    def _make_layout(self, title):
        layout = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(15),
                           size_hint=(0.85, 0.88), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        layout.add_widget(Label(text=title, font_size=sp(24), bold=True, color=(1, 0.8, 0.2), size_hint_y=0.08))
        return layout

    def _add_back_btn(self, layout):
        b = Button(text="Назад", font_size=sp(16), size_hint_y=0.1,
                   background_color=(0.4, 0.4, 0.5, 1))
        b.bind(on_press=lambda inst: self._set_mode("main"))
        layout.add_widget(b)

    # ---------- Главное меню станции ----------
    def _build_main(self):
        layout = self._make_layout("СТАНЦИЯ")
        btns = [
            ("Лечение (+25% HP)", self._action_heal, (0.2, 0.7, 0.3, 1)),
            ("Продажа модулей", self._action_sell, (0.8, 0.6, 0.2, 1)),
            ("Покупка модулей", self._action_buy, (0.2, 0.5, 0.8, 1)),
            ("Перестановка модулей", self._action_rearrange, (0.6, 0.4, 0.8, 1)),
        ]
        for text, cb, color in btns:
            b = Button(text=text, font_size=sp(16), size_hint_y=0.15, background_color=color)
            b.bind(on_press=cb)
            layout.add_widget(b)
        b = Button(text="Выход", font_size=sp(16), size_hint_y=0.15, background_color=(0.7, 0.3, 0.3, 1))
        b.bind(on_press=self.close)
        layout.add_widget(b)
        self.add_widget(layout)

    # ---------- Подменю: Продажа ----------
    def _build_sell(self):
        layout = self._make_layout("ПРОДАЖА МОДУЛЕЙ")
        s = self.game_ref.snake
        scroll = ScrollView(size_hint=(1, 0.72))
        mod_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        mod_list.bind(minimum_height=mod_list.setter('height'))

        if s.mods:
            for i, m in enumerate(s.mods):
                sell_price = 10 + m["lvl"] * 5
                name = MOD_DATA[m["type"]]["name"]
                btn = Button(text=f"{name} L{m['lvl']}  ->  +{sell_price}$",
                             font_size=sp(13), size_hint_y=None, height=dp(42),
                             background_color=(*MOD_DATA[m["type"]]["color"], 1))
                btn.bind(on_press=lambda inst, idx=i: self._sell_mod(idx))
                mod_list.add_widget(btn)
        else:
            mod_list.add_widget(Label(text="Нет модулей для продажи", font_size=sp(14),
                                      color=(0.5, 0.5, 0.5), size_hint_y=None, height=dp(42)))
        scroll.add_widget(mod_list)
        layout.add_widget(scroll)
        self._add_back_btn(layout)
        self.add_widget(layout)

    # ---------- Подменю: Покупка ----------
    def _build_buy(self):
        layout = self._make_layout("ПОКУПКА МОДУЛЕЙ")
        lost = self.game_ref.lost_modules
        scroll = ScrollView(size_hint=(1, 0.72))
        mod_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        mod_list.bind(minimum_height=mod_list.setter('height'))

        if lost:
            for i, lm in enumerate(lost):
                mtype = lm["type"]
                lvl = lm["lvl"]
                buy_price = MOD_DATA[mtype]["rarity"] * 15 + lvl * 5
                name = MOD_DATA[mtype]["name"]
                btn = Button(text=f"{name} L{lvl}  <-  {buy_price}$",
                             font_size=sp(13), size_hint_y=None, height=dp(42),
                             background_color=(*MOD_DATA[mtype]["color"], 1))
                btn.bind(on_press=lambda inst, idx=i: self._buy_mod(idx))
                mod_list.add_widget(btn)
        else:
            mod_list.add_widget(Label(text="Нет потерянных модулей", font_size=sp(14),
                                      color=(0.5, 0.5, 0.5), size_hint_y=None, height=dp(42)))
        scroll.add_widget(mod_list)
        layout.add_widget(scroll)
        self._add_back_btn(layout)
        self.add_widget(layout)

    # ---------- Подменю: Перестановка ----------
    def _build_rearrange(self):
        layout = self._make_layout("ПЕРЕСТАНОВКА МОДУЛЕЙ")
        s = self.game_ref.snake
        scroll = ScrollView(size_hint=(1, 0.72))
        mod_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        mod_list.bind(minimum_height=mod_list.setter('height'))

        layout.add_widget(Label(text="Нажмите на модуль, чтобы поменять его местами со следующим",
                                font_size=sp(12), color=(0.7, 0.7, 0.7), size_hint_y=0.06))

        if s.mods:
            for i, m in enumerate(s.mods):
                name = MOD_DATA[m["type"]]["name"]
                if i < len(s.mods) - 1:
                    next_name = MOD_DATA[s.mods[i+1]["type"]]["name"]
                    label_text = f"{i+1}. {name} L{m['lvl']}  <->  {i+2}. {next_name}"
                else:
                    label_text = f"{i+1}. {name} L{m['lvl']}  (последний)"
                btn = Button(text=label_text,
                             font_size=sp(13), size_hint_y=None, height=dp(42),
                             background_color=(*MOD_DATA[m["type"]]["color"], 1))
                btn.bind(on_press=lambda inst, idx=i: self._swap_mods(idx))
                mod_list.add_widget(btn)
        else:
            mod_list.add_widget(Label(text="Нет модулей", font_size=sp(14),
                                      color=(0.5, 0.5, 0.5), size_hint_y=None, height=dp(42)))
        scroll.add_widget(mod_list)
        layout.add_widget(scroll)
        self._add_back_btn(layout)
        self.add_widget(layout)

    # ---------- Действия ----------
    def _set_mode(self, mode):
        self.mode = mode
        self._rebuild()

    def _action_heal(self, inst):
        s = self.game_ref.snake
        s.hp = min(s.max_hp, s.hp + s.max_hp * 0.25)
        for m in s.mods:
            m["hp"] = min(m["max_hp"], m["hp"] + m["max_hp"] * 0.5)
        App.get_running_app().toast("HP +25%!")
        self.close()

    def _action_sell(self, inst):
        self._set_mode("sell")

    def _action_buy(self, inst):
        self._set_mode("buy")

    def _action_rearrange(self, inst):
        self._set_mode("rearrange")

    def _sell_mod(self, idx):
        s = self.game_ref.snake
        if 0 <= idx < len(s.mods):
            m = s.mods[idx]
            sell_price = 10 + m["lvl"] * 5
            s.money += sell_price
            s.mods.pop(idx)
            if idx < len(s.body):
                s.body.pop(idx)
            self._rebuild()
            App.get_running_app().toast(f"Продано: +{sell_price}$")

    def _buy_mod(self, idx):
        lost = self.game_ref.lost_modules
        s = self.game_ref.snake
        if 0 <= idx < len(lost):
            lm = lost[idx]
            mtype = lm["type"]
            lvl = lm["lvl"]
            buy_price = MOD_DATA[mtype]["rarity"] * 15 + lvl * 5
            if s.money >= buy_price:
                s.money -= buy_price
                # Возвращаем модуль с сохранением уровня
                s.mods.append({
                    "type": mtype, "hp": MOD_DATA[mtype]["hp"] * (1.2 ** (lvl-1)),
                    "max_hp": MOD_DATA[mtype]["hp"] * (1.2 ** (lvl-1)),
                    "lvl": lvl, "cd": 0.0
                })
                last = s.body[-1] if s.body else [s.x, s.y]
                s.body.append([last[0], last[1]])
                lost.pop(idx)
                self._rebuild()
                App.get_running_app().toast(f"Куплено: {MOD_DATA[mtype]['name']} L{lvl}")
            else:
                App.get_running_app().toast("Недостаточно денег!")

    def _swap_mods(self, idx):
        s = self.game_ref.snake
        if 0 <= idx < len(s.mods) - 1:
            s.mods[idx], s.mods[idx+1] = s.mods[idx+1], s.mods[idx]
            self._rebuild()
            App.get_running_app().toast("Модули поменяны местами")

    def close(self, inst=None):
        try:
            App.get_running_app().root.remove_widget(self)
        except Exception: pass
        self.game_ref.station_menu_open = False
        self.game_ref.paused = False

    def update_bg(self, *a): self.bg.pos = self.pos; self.bg.size = self.size

# ---------- Меню улучшений ----------
class UpgradeMenu(FloatLayout):
    def __init__(self, options, callback, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 0.7); self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        layout = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(20),
                           size_hint=(0.8, 0.8), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        layout.add_widget(Label(text="УРОВЕНЬ ПОВЫШЕН!", font_size=sp(24), bold=True, color=(1, 0.8, 0.2), size_hint_y=0.2))
        for i, mtype in enumerate(options):
            btn = Button(text=MOD_DATA[mtype]['name'], font_size=sp(18), size_hint_y=0.2,
                         background_color=(*MOD_DATA[mtype]['color'], 1))
            btn.bind(on_press=lambda inst, idx=i: callback(idx))
            layout.add_widget(btn)
        self.add_widget(layout)
    def update_bg(self, *a): self.bg.pos = self.pos; self.bg.size = self.size

# ---------- Меню паузы ----------
class PauseMenu(FloatLayout):
    def __init__(self, resume_cb, menu_cb, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 0.7); self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        layout = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(20),
                           size_hint=(0.6, 0.4), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        layout.add_widget(Label(text="ПАУЗА", font_size=sp(28), bold=True, color=(1, 0.8, 0.2), size_hint_y=0.3))
        b = Button(text="ПРОДОЛЖИТЬ", font_size=sp(18), background_color=(0.2, 0.7, 0.3, 1)); b.bind(on_press=resume_cb); layout.add_widget(b)
        b = Button(text="В ГЛАВНОЕ МЕНЮ", font_size=sp(18), background_color=(0.7, 0.3, 0.3, 1)); b.bind(on_press=menu_cb); layout.add_widget(b)
        self.add_widget(layout)
    def update_bg(self, *a): self.bg.pos = self.pos; self.bg.size = self.size

# ---------- Меню проигрыша ----------
class GameOverMenu(FloatLayout):
    def __init__(self, restart_cb, menu_cb, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 0.8); self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)
        layout = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(20),
                           size_hint=(0.6, 0.4), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        layout.add_widget(Label(text="ИГРА ОКОНЧЕНА", font_size=sp(28), bold=True, color=(1, 0.2, 0.2), size_hint_y=0.3))
        b = Button(text="ЗАНОВО", font_size=sp(18), background_color=(0.2, 0.7, 0.3, 1)); b.bind(on_press=restart_cb); layout.add_widget(b)
        b = Button(text="В МЕНЮ", font_size=sp(18), background_color=(0.7, 0.3, 0.3, 1)); b.bind(on_press=menu_cb); layout.add_widget(b)
        self.add_widget(layout)
    def update_bg(self, *a): self.bg.pos = self.pos; self.bg.size = self.size

# ---------- Бестиарий ----------
class BestiaryMenu(FloatLayout):
    def __init__(self, back_cb, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 0.85); self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_bg, size=self.update_bg)

        outer = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(15),
                          size_hint=(0.9, 0.9), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        outer.add_widget(Label(text="БЕСТИАРИЙ", font_size=sp(24), bold=True, color=(1, 0.8, 0.2), size_hint_y=0.07))

        scroll = ScrollView(size_hint=(1, 0.85))
        content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(8), padding=dp(5))
        content.bind(minimum_height=content.setter('height'))

        # --- Раздел: Враги ---
        content.add_widget(self._section_label("— ВРАГИ —", (0.9, 0.4, 0.4)))
        enemy_order = ["melee", "fast", "tank", "shooter", "boss"]
        for kind in enemy_order:
            if kind in PLAYER.encountered_enemies:
                data = ENEMY_DATA[kind]
                text = f"[b]{data['name']}[/b]\n{data['desc']}"
                content.add_widget(self._entry_label(text, data['color']))
            else:
                content.add_widget(self._locked_label())

        # --- Раздел: Модули ---
        content.add_widget(self._section_label("— МОДУЛИ —", (0.4, 0.9, 0.4)))
        for mtype in ModType:
            if mtype.name in PLAYER.obtained_modules:
                data = MOD_DATA[mtype]
                desc = MOD_DESC.get(mtype, "")
                text = f"[b]{data['name']}[/b] (HP:{data['hp']}, редкость:{data['rarity']})\n{desc}"
                content.add_widget(self._entry_label(text, data['color']))
            else:
                content.add_widget(self._locked_label())

        scroll.add_widget(content)
        outer.add_widget(scroll)

        b = Button(text="НАЗАД", font_size=sp(18), size_hint_y=0.08, background_color=(0.3, 0.3, 0.6, 1))
        b.bind(on_press=back_cb)
        outer.add_widget(b)

        self.add_widget(outer)

    def _section_label(self, text, color):
        lbl = Label(text=text, font_size=sp(18), bold=True, color=color,
                    size_hint_y=None, height=dp(32))
        return lbl

    def _entry_label(self, text, color):
        lbl = Label(text=text, markup=True, font_size=sp(13), color=color,
                    size_hint_y=None, halign='left', valign='top',
                    padding=(dp(10), dp(6)))
        lbl.bind(width=lambda inst, w: setattr(inst, 'text_size', (w, None)))
        lbl.bind(texture_size=lambda inst, ts: setattr(inst, 'height', ts[1] + dp(12)))
        return lbl

    def _locked_label(self):
        return Label(text="???  (не обнаружено)", font_size=sp(13), color=(0.35, 0.35, 0.35),
                     size_hint_y=None, height=dp(28), italic=True)

    def update_bg(self, *a): self.bg.pos = self.pos; self.bg.size = self.size

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
        update_scale()
        self.joy_active = False
        self.snake = Snake()
        self.enemies, self.bullets, self.pickups = [], [], []
        self.stations = []
        self.explosions, self.tesla_lines = [], []
        self.lost_modules = []  # Модули, уничтоженные врагами — можно купить на станции
        self.wave, self.wave_timer = 0, 3.0
        self.pickup_timer, self.station_timer = 6.0, 20.0
        self.game_over, self.upgrading, self.paused = False, False, False
        self.station_menu_open = False
        self.upg_opts = []
        self.autosave_t = 0.0

    def update(self, dt):
        for ex in self.explosions[:]:
            ex.life -= dt
            if ex.life <= 0: self.explosions.remove(ex)
        for tl in self.tesla_lines[:]:
            tl.life -= dt
            if tl.life <= 0: self.tesla_lines.remove(tl)
        for e in self.enemies:
            if e.tesla_hit > 0: e.tesla_hit -= dt

        self.autosave_t += dt
        if self.autosave_t > 10.0:
            PLAYER.money += self.snake.money
            self.snake.money = 0
            if self.wave > PLAYER.high_score: PLAYER.high_score = self.wave
            PLAYER.save()
            self.autosave_t = 0.0

        # Если игра на паузе, открыто меню станции или уровня — только перерисовываем
        if self.game_over or self.upgrading or self.paused or self.station_menu_open or self.width <= 0:
            self.redraw(); return

        s = self.snake
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

        drone_active = any(m["type"] == ModType.DRONE for m in s.mods)
        if drone_active:
            s.drone_angle += dt * 2.0
            orbit_r = max(60, len(s.body) * CELL * 0.6)
            s.drone_x = s.x + math.cos(s.drone_angle) * orbit_r
            s.drone_y = s.y + math.sin(s.drone_angle) * orbit_r

        for i in range(min(len(s.mods), len(s.body))):
            m = s.mods[i]
            m["cd"] = max(0.0, m["cd"] - dt)
            if m["type"] in GUN_STATS and m["cd"] <= 0:
                mx, my = (s.drone_x, s.drone_y) if m["type"] == ModType.DRONE else (s.body[i][0], s.body[i][1])
                best_d, tgt = (GUN_STATS[m["type"]][1]*SCALE)**2, None
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
                            bd, nt = (200*SCALE)**2, None
                            for e in self.enemies:
                                if e in chain: continue
                                d2 = (cur.x - e.x)**2 + (cur.y - e.y)**2
                                if d2 < bd: bd, nt = d2, e
                            if nt: chain.append(nt); cur = nt
                            else: break
                        for ct in chain: ct.hp -= dmg; ct.tesla_hit = 0.15
                        self.tesla_lines.append(TeslaLine([(mx, my)] + [(c.x, c.y) for c in chain]))
                    elif m["type"] == ModType.GRENADE:
                        if len(self.bullets) < MAX_BULLETS:
                            self.bullets.append(Bullet(mx, my, math.cos(ang)*500*SCALE, math.sin(ang)*500*SCALE, dmg, is_grenade=True, life=1.2))
                    else:
                        if len(self.bullets) < MAX_BULLETS:
                            self.bullets.append(Bullet(mx, my, math.cos(ang)*700*SCALE, math.sin(ang)*700*SCALE, dmg))
                    m["cd"] = cd
            elif m["type"] == ModType.HEAL and m["cd"] <= 0:
                m["cd"] = 1.5
                heal = 0.5 + 0.3 * m["lvl"]
                s.hp = min(s.max_hp, s.hp + heal)
                for other in s.mods:
                    if other is not m: other["hp"] = min(other["max_hp"], other["hp"] + heal * 0.4)

        for b in self.bullets[:]:
            b.x += b.vx * dt; b.y += b.vy * dt; b.life -= dt
            hit = False
            if b.is_enemy:
                if (b.x - s.x)**2 + (b.y - s.y)**2 < (8*SCALE + CELL*0.5)**2: s.hp -= b.dmg; hit = True
                else:
                    for i in range(min(len(s.mods), len(s.body))):
                        if (b.x - s.body[i][0])**2 + (b.y - s.body[i][1])**2 < (8*SCALE + CELL*0.4)**2:
                            s.mods[i]["hp"] -= b.dmg; hit = True; break
            else:
                for e in self.enemies[:]:
                    if (b.x - e.x)**2 + (b.y - e.y)**2 < (e.radius + 8*SCALE)**2:
                        if b.is_grenade:
                            self.explosions.append(Explosion(b.x, b.y, 90*SCALE, 0.4))
                            for ee in self.enemies[:]:
                                if (b.x - ee.x)**2 + (b.y - ee.y)**2 < (90*SCALE)**2: ee.hp -= b.dmg
                        else: e.hp -= b.dmg
                        hit = True; break
            if hit or b.life <= 0 or (b.x - s.x)**2 + (b.y - s.y)**2 > (2000*SCALE)**2:
                if b.is_grenade and not hit:
                    self.explosions.append(Explosion(b.x, b.y, 90*SCALE, 0.4))
                    for ee in self.enemies[:]:
                        if (b.x - ee.x)**2 + (b.y - ee.y)**2 < (90*SCALE)**2: ee.hp -= b.dmg
                if b in self.bullets: self.bullets.remove(b)

        for e in self.enemies[:]:
            targets = [(s.x, s.y)] + [(bb[0], bb[1]) for bb in s.body]
            best = None; bd = 999999**2
            for tx_t, ty_t in targets:
                d2 = (e.x - tx_t)**2 + (e.y - ty_t)**2
                if d2 < bd: bd = d2; best = (tx_t, ty_t)
            tx_t, ty_t = best
            ang = math.atan2(ty_t - e.y, tx_t - e.x)
            if e.kind == "shooter":
                if bd < (250*SCALE)**2: ang += math.pi
                e.shoot_cd -= dt
                if e.shoot_cd <= 0 and bd < (500*SCALE)**2 and len(self.bullets) < MAX_BULLETS:
                    e.shoot_cd = 2.0; a = math.atan2(s.y - e.y, s.x - e.x)
                    self.bullets.append(Bullet(e.x, e.y, math.cos(a)*350*SCALE, math.sin(a)*350*SCALE, e.damage, is_enemy=True, life=2.0))
            elif e.kind == "boss":
                # Босс идёт к змее и стреляет веером из 3 пуль
                e.shoot_cd -= dt
                if e.shoot_cd <= 0 and bd < (600*SCALE)**2 and len(self.bullets) < MAX_BULLETS:
                    e.shoot_cd = 1.0
                    base_a = math.atan2(s.y - e.y, s.x - e.x)
                    for angle_offset in [-0.3, 0, 0.3]:
                        a = base_a + angle_offset
                        if len(self.bullets) < MAX_BULLETS:
                            self.bullets.append(Bullet(e.x, e.y, math.cos(a)*400*SCALE, math.sin(a)*400*SCALE, e.damage, is_enemy=True, life=2.5))
            e.x += math.cos(ang) * e.speed * dt
            e.y += math.sin(ang) * e.speed * dt
            if (e.x - s.x)**2 + (e.y - s.y)**2 < (e.radius + CELL*0.5)**2: s.hp -= e.damage * dt * 2.0
            else:
                for i in range(min(len(s.mods), len(s.body))):
                    if (e.x - s.body[i][0])**2 + (e.y - s.body[i][1])**2 < (e.radius + CELL*0.5)**2:
                        s.mods[i]["hp"] -= e.damage * dt * 2.0; break
            if e.hp <= 0:
                self.enemies.remove(e)
                if e.kind == "boss":
                    s.money += 50; s.xp += 30
                    App.get_running_app().toast("БОСС ПОВЕРЖЕН! +50$")
                else:
                    s.money += 5; s.xp += 3
                if s.xp >= s.xp_next:
                    s.xp -= s.xp_next; s.level += 1; s.xp_next = int(s.xp_next * 1.5)
                    self.open_upgrade(); return

        for i in range(len(s.mods)-1, -1, -1):
            if s.mods[i]["hp"] <= 0:
                # Запоминаем потерянный модуль — его можно купить на станции
                self.lost_modules.append({"type": s.mods[i]["type"], "lvl": s.mods[i]["lvl"]})
                s.mods.pop(i)
                while len(s.body) > len(s.mods) + 1: s.body.pop()

        for p in self.pickups[:]:
            if (p.x - s.x)**2 + (p.y - s.y)**2 < (20*SCALE + 15*SCALE)**2:
                self.pickups.remove(p); s.add_mod(p.mtype)

        # СТАНЦИИ
        for st in self.stations:
            if st.used: continue
            hit = False
            if (st.x - s.x)**2 + (st.y - s.y)**2 < (40*SCALE + CELL)**2: hit = True
            if not hit:
                for bb in s.body:
                    if (st.x - bb[0])**2 + (st.y - bb[1])**2 < (40*SCALE + CELL)**2: hit = True; break
            if hit:
                st.used = True
                self.station_menu_open = True
                self.paused = True  # ВАЖНО: ставим игру на паузу перед меню
                App.get_running_app().root.add_widget(StationMenu(game_ref=self))
                self.redraw()
                return

        self.wave_timer -= dt
        if self.wave_timer <= 0:
            self.wave += 1; self.wave_timer = max(8.0, 15.0 - self.wave * 0.3)
            if len(self.enemies) < MAX_ENEMIES:
                if self.wave % 10 == 0:
                    # ВОЛНА БОССА
                    a = random.uniform(0, math.tau); r = 400 * SCALE
                    ex = s.x + math.cos(a)*r; ey = s.y + math.sin(a)*r
                    boss_hp = 200 + self.wave * 10
                    self.enemies.append(Enemy(ex, ey, boss_hp, (30 + self.wave)*SCALE, 35*SCALE, (0.9, 0.1, 0.1), 20, "boss"))
                    PLAYER.register_enemy("boss")
                    # Несколько миньонов
                    for _ in range(3):
                        a2 = random.uniform(0, math.tau); r2 = random.uniform(350, 500) * SCALE
                        ex2 = s.x + math.cos(a2)*r2; ey2 = s.y + math.sin(a2)*r2
                        mh = 10 + self.wave * 6
                        self.enemies.append(Enemy(ex2, ey2, mh, (60+self.wave*2)*SCALE, 15*SCALE, (1, 0.3, 0.3), 10, "melee"))
                        PLAYER.register_enemy("melee")
                else:
                    for _ in range(min(3 + self.wave, 12)):
                        a = random.uniform(0, math.tau); r = random.uniform(350, 600) * SCALE
                        ex = s.x + math.cos(a)*r; ey = s.y + math.sin(a)*r
                        hp = 10 + self.wave * 6
                        roll = random.random()
                        if self.wave >= 4 and roll < 0.25:
                            self.enemies.append(Enemy(ex, ey, hp*0.9, (60+self.wave*2)*SCALE, 15*SCALE, (1, 0.3, 0.8), 6, "shooter"))
                            PLAYER.register_enemy("shooter")
                        elif self.wave >= 3 and roll < 0.45:
                            self.enemies.append(Enemy(ex, ey, hp*2.0, (40+self.wave*1.5)*SCALE, 20*SCALE, (0.6, 0.2, 0.8), 15, "tank"))
                            PLAYER.register_enemy("tank")
                        elif self.wave >= 2 and roll < 0.65:
                            self.enemies.append(Enemy(ex, ey, hp*0.6, (100+self.wave*3)*SCALE, 12*SCALE, (1, 0.5, 0.2), 8, "fast"))
                            PLAYER.register_enemy("fast")
                        else:
                            self.enemies.append(Enemy(ex, ey, hp, (60+self.wave*2)*SCALE, 15*SCALE, (1, 0.3, 0.3), 10, "melee"))
                            PLAYER.register_enemy("melee")

        self.pickup_timer -= dt
        if self.pickup_timer <= 0 and len(self.pickups) < MAX_PICKUPS:
            a = random.uniform(0, math.tau); r = random.uniform(150, 400) * SCALE
            self.pickups.append(Pickup(s.x + math.cos(a)*r, s.y + math.sin(a)*r, random.choice(list(ModType))))
            self.pickup_timer = 8.0

        self.station_timer -= dt
        if self.station_timer <= 0:
            self.stations = [st for st in self.stations if not st.used]
            if len(self.stations) == 0:
                a = random.uniform(0, math.tau); r = random.uniform(300, 500) * SCALE
                self.stations.append(Station(s.x + math.cos(a)*r, s.y + math.sin(a)*r))
            self.station_timer = 25.0

        if s.hp <= 0:
            self.game_over = True
            App.get_running_app().show_game_over()

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
            t = self.upg_opts[idx]; s = self.snake
            found = False
            for m in s.mods:
                if m["type"] == t:
                    m["lvl"] += 1; m["hp"] = m["max_hp"] * 1.2; m["max_hp"] *= 1.2; found = True; break
            if not found: s.add_mod(t)
        self.upgrading = False; self.redraw()

    def toggle_pause(self, inst):
        if self.game_over or self.upgrading or self.station_menu_open: return
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
            def to_menu(i): app.stop_game()
            app.root.add_widget(PauseMenu(resume_cb=resume, menu_cb=to_menu))
        self.redraw()

    def redraw(self):
        self.canvas.clear()
        with self.canvas:
            Color(0.1, 0.1, 0.15)
            Rectangle(pos=(0, 0), size=(self.width, self.height))
            def scr(x, y): return x - self.snake.x + self.width/2, y - self.snake.y + self.height/2

            st_r = 20 * SCALE
            for st in self.stations:
                if st.used: continue
                sx, sy = scr(st.x, st.y)
                if -50 < sx < self.width+50 and -50 < sy < self.height+50:
                    Color(1, 0.8, 0.2); Ellipse(pos=(sx-st_r, sy-st_r), size=(st_r*2, st_r*2))
                    Color(0.5, 0.3, 0); Line(circle=(sx, sy, st_r), width=2*SCALE)

            for e in self.enemies:
                sx, sy = scr(e.x, e.y)
                if -50 < sx < self.width+50 and -50 < sy < self.height+50:
                    if e.kind == "boss":
                        # Босс — крупный враг с золотой обводкой и короной
                        Color(*e.color); Ellipse(pos=(sx-e.radius, sy-e.radius), size=(e.radius*2, e.radius*2))
                        if e.tesla_hit > 0:
                            Color(0.6, 1, 1, 0.8); Ellipse(pos=(sx-e.radius-5*SCALE, sy-e.radius-5*SCALE), size=((e.radius+5*SCALE)*2, (e.radius+5*SCALE)*2))
                        Color(1, 0.8, 0); Line(circle=(sx, sy, e.radius), width=3*SCALE)
                        # Коронные шипы
                        Color(1, 0.85, 0.2)
                        for k in range(3):
                            cax = sx + (k-1) * e.radius * 0.6
                            cay = sy + e.radius + 6*SCALE
                            Ellipse(pos=(cax-4*SCALE, cay-4*SCALE), size=(8*SCALE, 8*SCALE))
                        # Крупная HP-полоска
                        bhw = 25 * SCALE
                        Color(0.3, 0, 0); Rectangle(pos=(sx-bhw, sy-e.radius-12*SCALE), size=(bhw*2, 6*SCALE))
                        Color(0, 0.8, 0); Rectangle(pos=(sx-bhw, sy-e.radius-12*SCALE), size=(bhw*2*max(0, e.hp/e.max_hp), 6*SCALE))
                    else:
                        Color(*e.color); Ellipse(pos=(sx-e.radius, sy-e.radius), size=(e.radius*2, e.radius*2))
                        if e.tesla_hit > 0:
                            Color(0.6, 1, 1, 0.8); Ellipse(pos=(sx-e.radius-5*SCALE, sy-e.radius-5*SCALE), size=((e.radius+5*SCALE)*2, (e.radius+5*SCALE)*2))
                        Color(0.3, 0, 0); Rectangle(pos=(sx-14*SCALE, sy-e.radius-8*SCALE), size=(28*SCALE, 4*SCALE))
                        Color(0, 0.8, 0); Rectangle(pos=(sx-14*SCALE, sy-e.radius-8*SCALE), size=(28*SCALE*max(0, e.hp/e.max_hp), 4*SCALE))

            pk = 12 * SCALE
            for p in self.pickups:
                sx, sy = scr(p.x, p.y)
                if -50 < sx < self.width+50 and -50 < sy < self.height+50:
                    Color(*MOD_DATA[p.mtype]["color"]); Ellipse(pos=(sx-pk, sy-pk), size=(pk*2, pk*2))

            for ex in self.explosions:
                sx, sy = scr(ex.x, ex.y)
                t = ex.life / ex.max_life
                r = ex.radius * (1.2 - t * 0.6)
                Color(1, 0.5, 0.1, t); Ellipse(pos=(sx-r, sy-r), size=(r*2, r*2))

            bs = 4 * SCALE
            for b in self.bullets:
                sx, sy = scr(b.x, b.y)
                if -50 < sx < self.width+50 and -50 < sy < self.height+50:
                    if b.is_enemy: Color(1, 0.3, 0.3)
                    elif b.is_grenade: Color(0.8, 0.5, 0.2)
                    else: Color(1, 0.9, 0.2)
                    Ellipse(pos=(sx-bs, sy-bs), size=(bs*2, bs*2))

            for tl in self.tesla_lines:
                pts = []
                for px, py in tl.points:
                    sx, sy = scr(px, py); pts.extend([sx, sy])
                if len(pts) >= 4:
                    Color(0.4, 1, 1, tl.life / 0.15); Line(points=pts, width=2*SCALE)

            s = self.snake
            c_head, c_body = (0.2, 0.8, 0.4), (0.1, 0.6, 0.3)
            if PLAYER.snake_skin == 1: c_head, c_body = (0.8, 0.2, 0.2), (0.6, 0.1, 0.1)
            elif PLAYER.snake_skin == 2: c_head, c_body = (0.2, 0.2, 0.8), (0.1, 0.1, 0.6)

            for bb in s.body:
                sx, sy = scr(bb[0], bb[1])
                if -50 < sx < self.width+50 and -50 < sy < self.height+50:
                    Color(*c_body); Rectangle(pos=(sx-CELL*0.4, sy-CELL*0.4), size=(CELL*0.8, CELL*0.8))

            hx, hy = scr(s.x, s.y)
            Color(*c_head); Ellipse(pos=(hx-CELL*0.6, hy-CELL*0.6), size=(CELL*1.2, CELL*1.2))

            hpw = 12 * SCALE
            for i, m in enumerate(s.mods):
                if m["type"] == ModType.DRONE: continue
                if i >= len(s.body): break
                mx, my = scr(s.body[i][0], s.body[i][1])
                if not (-50 < mx < self.width+50 and -50 < my < self.height+50): continue
                Color(*MOD_DATA[m["type"]]["color"]); Rectangle(pos=(mx-CELL*0.3, my-CELL*0.3), size=(CELL*0.6, CELL*0.6))
                Color(0.3, 0, 0); Rectangle(pos=(mx-hpw, my+CELL*0.55), size=(hpw*2, 3*SCALE))
                hp_ratio = max(0, m["hp"] / m["max_hp"])
                Color(0, 0.85, 0.3); Rectangle(pos=(mx-hpw, my+CELL*0.55), size=(hpw*2*hp_ratio, 3*SCALE))

                if m["type"] == ModType.AXES:
                    t = Clock.get_boottime() * 3.0
                    ax_r = 40 * SCALE
                    ax_sz = 8 * SCALE
                    for k in range(2):
                        ang = t + k * math.pi
                        ax = mx + math.cos(ang) * ax_r; ay = my + math.sin(ang) * ax_r
                        Color(0.7, 0.7, 0.7); Ellipse(pos=(ax-ax_sz, ay-ax_sz), size=(ax_sz*2, ax_sz*2))

                if m["type"] == ModType.SHIELD:
                    t = Clock.get_boottime() * 2.5
                    sh_r = 35 * SCALE
                    sh_sz = 12 * SCALE
                    for k in range(2):
                        ang = t + k * math.pi
                        sx2 = mx + math.cos(ang) * sh_r; sy2 = my + math.sin(ang) * sh_r
                        Color(1, 0.9, 0.5); Ellipse(pos=(sx2-sh_sz, sy2-sh_sz), size=(sh_sz*2, sh_sz*2))
                        Color(1, 0.7, 0); Line(circle=(sx2, sy2, sh_sz), width=2*SCALE)

            if any(m["type"] == ModType.DRONE for m in s.mods):
                dx, dy = scr(s.drone_x, s.drone_y)
                if -50 < dx < self.width+50 and -50 < dy < self.height+50:
                    dr_sz = 10 * SCALE
                    Color(0.7, 0.7, 0.7); Rectangle(pos=(dx-dr_sz, dy-dr_sz), size=(dr_sz*2, dr_sz*2))
                    Color(0.4, 0.9, 0.9); Rectangle(pos=(dx-dr_sz*0.5, dy-dr_sz*0.5), size=(dr_sz, dr_sz))

            jx, jy = self.width * 0.85, self.height * 0.15
            r = min(self.width, self.height) * 0.12
            knob = 15 * SCALE
            Color(0.3, 0.3, 0.4, 0.5); Ellipse(pos=(jx-r, jy-r), size=(r*2, r*2))
            if getattr(self, 'joy_active', False):
                Color(0.8, 0.8, 0.2); Ellipse(pos=(jx+s.dx*r*0.6-knob, jy+s.dy*r*0.6-knob), size=(knob*2, knob*2))
            else:
                Color(0.6, 0.6, 0.2); Ellipse(pos=(jx-knob, jy-knob), size=(knob*2, knob*2))

    def on_touch_down(self, touch):
        if self.upgrading or self.game_over or self.paused or self.station_menu_open: return super().on_touch_down(touch)
        jx, jy = self.width * 0.85, self.height * 0.15
        if (touch.x-jx)**2 + (touch.y-jy)**2 < (min(self.width, self.height)*0.15)**2:
            touch.ud['joy'] = True; self.joy_active = True; return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.ud.get('joy'):
            jx, jy = self.width * 0.85, self.height * 0.15
            dx, dy = touch.x-jx, touch.y-jy
            d = math.hypot(dx, dy)
            if d > 20*SCALE: self.snake.dx, self.snake.dy = dx/d, dy/d
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.ud.get('joy'):
            self.joy_active = False
            return True
        return super().on_touch_up(touch)

# ---------- Меню ----------
class MainMenu(BoxLayout):
    def __init__(self, start_cb, shop_cb, save_cb, bestiary_cb, **kwargs):
        super().__init__(orientation='vertical', padding=dp(30), spacing=dp(15), **kwargs)
        self.add_widget(Label(text="ЗМЕЙКА-РОГАЛИК", font_size=sp(30), bold=True, color=(1, 0.8, 0.2), size_hint_y=0.25))
        
        b = Button(text="ИГРАТЬ", font_size=sp(20), size_hint=(None, None), size=(dp(250), dp(55)), pos_hint={'center_x': 0.5})
        b.bind(on_press=start_cb); self.add_widget(b)
        
        b = Button(text="МАГАЗИН", font_size=sp(20), size_hint=(None, None), size=(dp(250), dp(55)), pos_hint={'center_x': 0.5})
        b.bind(on_press=shop_cb); self.add_widget(b)

        b = Button(text="БЕСТИАРИЙ", font_size=sp(20), size_hint=(None, None), size=(dp(250), dp(55)), pos_hint={'center_x': 0.5}, background_color=(0.4, 0.3, 0.6, 1))
        b.bind(on_press=bestiary_cb); self.add_widget(b)

        b = Button(text="СОХРАНИТЬ ПРОГРЕСС", font_size=sp(16), size_hint=(None, None), size=(dp(250), dp(45)), pos_hint={'center_x': 0.5}, background_color=(0.2, 0.5, 0.7, 1))
        b.bind(on_press=save_cb); self.add_widget(b)

        b = Button(text="ВЫЙТИ", font_size=sp(20), size_hint=(None, None), size=(dp(250), dp(55)), pos_hint={'center_x': 0.5}, background_color=(0.8, 0.2, 0.2, 1))
        b.bind(on_press=App.get_running_app().stop); self.add_widget(b)

class ShopMenu(BoxLayout):
    def __init__(self, back_cb, **kwargs):
        super().__init__(orientation='vertical', padding=dp(20), spacing=dp(10), **kwargs)
        self.add_widget(Label(text=f"Баланс: {PLAYER.money} $", font_size=sp(20), color=(1, 0.8, 0.2), size_hint_y=0.2))
        row1 = BoxLayout(size_hint_y=0.2)
        row1.add_widget(Label(text="Змея:", font_size=sp(16)))
        for nm, sid, cost in [("Зеленая",0,0), ("Красная (100)",1,100), ("Синяя (100)",2,100)]:
            b = Button(text=nm, font_size=sp(14))
            b.bind(on_press=lambda x, s=sid, c=cost: self.buy_skin(s, c))
            row1.add_widget(b)
        self.add_widget(row1)
        row2 = BoxLayout(size_hint_y=0.2)
        row2.add_widget(Label(text="Улучшения:", font_size=sp(16)))
        b = Button(text="Скорость (200)", font_size=sp(14)); b.bind(on_press=self.buy_legs); row2.add_widget(b)
        b = Button(text="HP (300)", font_size=sp(14)); b.bind(on_press=self.buy_skin_hp); row2.add_widget(b)
        self.add_widget(row2)
        self.add_widget(Widget(size_hint_y=0.2))
        b = Button(text="НАЗАД", font_size=sp(20), size_hint=(None, None), size=(dp(200), dp(50)), pos_hint={'center_x': 0.5})
        b.bind(on_press=back_cb); self.add_widget(b)

    def buy_skin(self, sid, cost):
        if sid not in PLAYER.owned_snake_skins and PLAYER.money >= cost:
            PLAYER.money -= cost; PLAYER.owned_snake_skins.append(sid)
        if sid in PLAYER.owned_snake_skins: PLAYER.snake_skin = sid
        PLAYER.save(); App.get_running_app().update_shop_ui()
    def buy_legs(self, inst):
        if not PLAYER.upg_legs and PLAYER.money >= 200:
            PLAYER.money -= 200; PLAYER.upg_legs = True; PLAYER.save(); App.get_running_app().update_shop_ui()
    def buy_skin_hp(self, inst):
        if not PLAYER.upg_skin and PLAYER.money >= 300:
            PLAYER.money -= 300; PLAYER.upg_skin = True; PLAYER.save(); App.get_running_app().update_shop_ui()

# ---------- App ----------
class SnakeApp(App):
    def build(self):
        global PLAYER
        PLAYER = PlayerData()
        self.root = FloatLayout()
        self.show_menu()
        return self.root

    def toast(self, text):
        if hasattr(self, 'toast_lbl'):
            try: self.root.remove_widget(self.toast_lbl)
            except: pass
        self.toast_lbl = Label(text=text, size_hint=(None, None),
                               pos_hint={'center_x': 0.5, 'top': 0.95},
                               font_size=sp(16), color=(0.2, 1, 0.2), bold=True,
                               halign='center', valign='middle',
                               padding=(dp(20), dp(10)))
        self.toast_lbl.bind(texture_size=self.toast_lbl.setter('size'))
        self.root.add_widget(self.toast_lbl)
        Clock.schedule_once(lambda dt: self._remove_toast(), 2.5)

    def _remove_toast(self):
        if hasattr(self, 'toast_lbl'):
            try: self.root.remove_widget(self.toast_lbl)
            except: pass

    def show_menu(self):
        self.root.clear_widgets()
        self.root.add_widget(MainMenu(start_cb=self.start_game, shop_cb=self.show_shop, save_cb=self.manual_save, bestiary_cb=self.show_bestiary))

    def show_bestiary(self, inst):
        self.root.clear_widgets()
        self.root.add_widget(BestiaryMenu(back_cb=lambda x: self.show_menu()))

    def manual_save(self, inst):
        PLAYER.save()
        self.toast("ПРОГРЕСС СОХРАНЁН!")

    def show_shop(self, inst):
        self.root.clear_widgets()
        self.root.add_widget(ShopMenu(back_cb=lambda x: self.show_menu()))

    def update_shop_ui(self):
        self.show_shop(None)

    def start_game(self, inst):
        # Останавливаем игровой цикл старой сессии, чтобы не было утечки CPU
        if hasattr(self, 'game') and self.game:
            try: Clock.unschedule(self.game.update)
            except: pass
        self.root.clear_widgets()
        self.game = GameWidget()
        self.root.add_widget(self.game)

        self.hud = Label(text="", pos_hint={'right': 0.98, 'top': 0.98},
                         size_hint=(0.32, None), font_size=sp(11), bold=True,
                         halign='right', valign='top')
        # Авто-высота: текст переносится по ширине, высота подстраивается под содержимое
        self.hud.bind(width=lambda inst, w: setattr(inst, 'text_size', (w, None)))
        self.hud.bind(texture_size=lambda inst, ts: setattr(inst, 'height', ts[1]))
        self.root.add_widget(self.hud)

        self.pause_btn = Button(text="II", size_hint=(None, None), size=(dp(50), dp(50)),
                                pos_hint={'x': 0.02, 'top': 0.9}, background_color=(0.3, 0.3, 0.3, 0.7))
        self.pause_btn.bind(on_press=self.game.toggle_pause)
        self.root.add_widget(self.pause_btn)

        Clock.schedule_interval(self.update_hud, 0.1)

    def show_game_over(self):
        def restart(i):
            for c in self.root.children[:]:
                if isinstance(c, GameOverMenu): self.root.remove_widget(c)
            self.start_game(None)
        def to_menu(i):
            for c in self.root.children[:]:
                if isinstance(c, GameOverMenu): self.root.remove_widget(c)
            self.stop_game()
        self.root.add_widget(GameOverMenu(restart_cb=restart, menu_cb=to_menu))

    def stop_game(self):
        if hasattr(self, 'game') and self.game:
            try: Clock.unschedule(self.game.update)
            except: pass
            if self.game.snake.money > 0:
                PLAYER.money += self.game.snake.money
                self.game.snake.money = 0
            if self.game.wave > PLAYER.high_score: PLAYER.high_score = self.game.wave
            PLAYER.save()
        try: Clock.unschedule(self.update_hud)
        except: pass
        self.show_menu()

    def update_hud(self, dt):
        if hasattr(self, 'game') and self.game:
            g = self.game; s = g.snake
            wave_str = f"Волна: {g.wave}"
            if g.wave % 10 == 0: wave_str += " [BOSS!]"
            lines = [f"HP: {int(s.hp)}/{s.max_hp}",
                     f"Ур: {s.level} | {wave_str} | $: {s.money}",
                     "— Модули —"]
            for i, m in enumerate(s.mods):
                lines.append(f"{i+1}. {MOD_DATA[m['type']]['name']} L{m['lvl']}")
            self.hud.text = "\n".join(lines)

    def on_stop(self):
        if hasattr(self, 'game') and self.game:
            try: Clock.unschedule(self.game.update)
            except: pass
            if self.game.snake.money > 0:
                PLAYER.money += self.game.snake.money
                self.game.snake.money = 0
            if self.game.wave > PLAYER.high_score: PLAYER.high_score = self.game.wave
        PLAYER.save()

if __name__ == '__main__':
    SnakeApp().run()
