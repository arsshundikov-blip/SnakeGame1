import kivy
kivy.require('2.0.0')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.core.window import Window
import math
import random

# ---------- Константы ----------
WIDTH, HEIGHT = 800, 600
CELL = 24
SNAKE_SPEED_BASE = 6.0
SNAKE_SPEED_PER_BOOST = 0.25
MAX_BOOSTERS = 10
MAX_HEALS = 10
HEAD_MAX_HP = 100

# Цвета (нормализованные для Kivy)
C_BG = (0.05, 0.06, 0.09)
C_GRID = (0.09, 0.11, 0.15)
C_HEAD = (0.55, 1.0, 0.7)
C_BODY = (0.23, 0.67, 0.39)
C_BODY_DARK = (0.15, 0.47, 0.27)
C_ENEMY = (0.9, 0.31, 0.31)
C_ENEMY_FAST = (1.0, 0.55, 0.23)
C_ENEMY_TANK = (0.63, 0.23, 0.78)
C_ENEMY_SHOOTER = (1.0, 0.31, 0.78)
C_BULLET = (1.0, 0.94, 0.47)
C_ENEMY_BULLET = (1.0, 0.39, 0.39)
C_STATION = (1.0, 0.78, 0.23)
C_GOLD = (1.0, 0.82, 0.31)

MOD_PISTOL, MOD_RIFLE, MOD_SNIPER = "Pistol", "Rifle", "Sniper"
MOD_SHIELD, MOD_HEAL, MOD_BOOSTER, MOD_AXES = "Shield", "Heal", "Booster", "Axes"

MOD_NAMES = {MOD_PISTOL: "Пистолет", MOD_RIFLE: "Автомат", MOD_SNIPER: "Снайперка",
             MOD_SHIELD: "Щит", MOD_HEAL: "Хилка", MOD_BOOSTER: "Ускоритель", MOD_AXES: "Топоры"}
MOD_BASE_HP = {MOD_PISTOL: 40, MOD_RIFLE: 35, MOD_SNIPER: 45, MOD_SHIELD: 60, MOD_HEAL: 25, MOD_BOOSTER: 25, MOD_AXES: 80}
MOD_COLORS = {MOD_PISTOL: (0.39, 0.78, 1.0), MOD_RIFLE: (0.39, 1.0, 0.78), MOD_SNIPER: (0.78, 0.47, 1.0),
              MOD_SHIELD: (1.0, 0.86, 0.39), MOD_HEAL: (0.39, 1.0, 0.47), MOD_BOOSTER: (1.0, 0.55, 1.0), MOD_AXES: (1.0, 0.39, 0.39)}
GUN_STATS = {MOD_PISTOL: (12, 340, 0.55), MOD_RIFLE: (6, 300, 0.13), MOD_SNIPER: (40, 620, 1.4)}

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

# ---------- Главный виджет игры ----------
class GameWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self._update_canvas)
        self.snake = None
        self.enemies, self.bullets, self.pickups, self.stations = [], [], [], []
        self.wave, self.wave_timer = 0, 2.0
        self.pickup_timer, self.station_timer = 6.0, 25.0
        self.paused, self.game_over = False, False
        self.show_upgrade, self.upgrade_options = False, []
        self.message, self.message_timer = "", 0.0
        self.station_menu = False
        self.reorder_mode, self.reorder_sel = False, 0
        self.cam_x, self.cam_y = 0.0, 0.0
        self.reset()
        Clock.schedule_interval(self.update, 1/60)

    def reset(self):
        self.snake = Snake()
        self.enemies, self.bullets, self.pickups, self.stations = [], [], [], []
        self.wave, self.wave_timer, self.pickup_timer, self.station_timer = 0, 2.0, 6.0, 25.0
        self.paused, self.game_over, self.show_upgrade = False, False, False
        self.station_menu, self.reorder_mode = False, False
        self.cam_x = self.cam_y = 0.0

    def msg(self, t, dur=2.0): self.message, self.message_timer = t, dur

    def update(self, dt):
        if self.game_over or self.paused or self.show_upgrade or self.station_menu or self.reorder_mode:
            self.redraw()
            return
        s = self.snake
        # Движение змеи
        s.head[0] += s.dir[0] * s.speed * (1 + SNAKE_SPEED_PER_BOOST*s.boosters) * dt
        s.head[1] += s.dir[1] * s.speed * (1 + SNAKE_SPEED_PER_BOOST*s.boosters) * dt
        # Тело
        target = s.head
        for i in range(len(s.body)):
            to = [target[0]-s.body[i][0], target[1]-s.body[i][1]]
            d = math.hypot(*to)
            if d > CELL: s.body[i] = [target[0]-to[0]/d*CELL, target[1]-to[1]/d*CELL]
            target = s.body[i]
        # Кулдауны
        for m in s.modules:
            m.cooldown = max(0, m.cooldown - dt)
            m.phase += dt
            
        mpos = s.module_positions()
        # Стрельба
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
                
        # Хилки
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
                    
        # Топоры
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
                        
        # Урон модулям
        for i, m in enumerate(s.modules):
            p = mpos[i]
            for e in self.enemies:
                if (p[0]-e.x)**2 + (p[1]-e.y)**2 <= (e.radius+12)**2:
                    m.hp -= e.damage * dt * 0.8
            if m.hp <= 0:
                s.damage_chain(i)
                if s.had_modules and not s.modules: self.game_over = True; return
                break
                
        # Враги
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
                
        if s.head_hp <= 0: self.game_over = True; return
        
        # Пули
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
                        
        # Смерть врагов
        for e in list(self.enemies):
            if e.hp <= 0:
                self.enemies.remove(e)
                s.xp += e.reward_xp; s.money += e.reward_money
                if s.xp >= s.xp_to_next:
                    s.xp -= s.xp_to_next; s.level += 1; s.xp_to_next = int(s.xp_to_next*1.35+4)
                    self.open_upgrade()
                    if self.show_upgrade: return
                    
        # Подбор модулей
        for p in list(self.pickups):
            touch = (p.x-s.head[0])**2 + (p.y-s.head[1])**2 <= (p.radius+CELL)**2
            if not touch:
                for b in s.body:
                    if (p.x-b[0])**2 + (p.y-b[1])**2 <= (p.radius+CELL*0.7)**2: touch=True; break
            if touch:
                if s.add_module(p.mtype): self.pickups.remove(p); self.msg(f"+{MOD_NAMES[p.mtype]}")
                else: self.msg("Лимит достигнут", 1.0)
                
        # Станции
        for st in self.stations:
            if not st.used and (st.x-s.head[0])**2 + (st.y-s.head[1])**2 <= (st.radius+CELL)**2:
                self.open_station(st); return
                
        # Таймеры
        self.wave_timer -= dt
        if self.wave_timer <= 0: self.spawn_wave(); self.wave_timer = max(6.0, 12.0-self.wave*0.3)
        self.pickup_timer -= dt
        if self.pickup_timer <= 0: self.spawn_pickup(); self.pickup_timer = random.uniform(6,11)
        self.station_timer -= dt
        if self.station_timer <= 0: self.spawn_station(); self.station_timer = random.uniform(30,50)
        if self.message_timer > 0: self.message_timer -= dt
        
        # Камера
        tx, ty = s.head[0]-self.width/2, s.head[1]-self.height/2
        self.cam_x += (tx-self.cam_x)*0.15; self.cam_y += (ty-self.cam_y)*0.15
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
        self.show_upgrade = True; opts, existing = [], {m.mtype for m in self.snake.modules}
        for t in existing: opts.append((f"Усилить: {MOD_NAMES[t]}", ('upgrade', t)))
        for t in [MOD_PISTOL, MOD_RIFLE, MOD_SNIPER, MOD_SHIELD, MOD_HEAL, MOD_BOOSTER]:
            if t not in existing:
                if t == MOD_HEAL and self.snake.heals >= MAX_HEALS: continue
                if t == MOD_BOOSTER and self.snake.boosters >= MAX_BOOSTERS: continue
                opts.append((f"Новый: {MOD_NAMES[t]}", ('add', t)))
        random.shuffle(opts); self.upgrade_options = opts[:3]

    def apply_upgrade(self, idx):
        if 0 <= idx < len(self.upgrade_options):
            _, (kind, t) = self.upgrade_options[idx]; s = self.snake
            if kind == 'upgrade':
                for m in s.modules:
                    if m.mtype == t: m.level += 1; m.max_hp *= 1.2; m.hp = m.max_hp; break
            else: s.add_module(t)
        self.show_upgrade = False; self.upgrade_options = []

    def open_station(self, st):
        self.station_menu, self.station_ref = True, st; st.used = True

    def station_repair(self):
        s = self.snake
        if not s.lost_modules: self.msg("Нет потерянных"); return
        cost = len(s.lost_modules)*8
        if s.money < cost: self.msg(f"Нужно {cost}"); return
        s.money -= cost; restored, s.lost_modules = s.lost_modules[:], []; cnt = 0
        for t in restored:
            if t == MOD_HEAL and s.heals >= MAX_HEALS: continue
            if t == MOD_BOOSTER and s.boosters >= MAX_BOOSTERS: continue
            if s.add_module(t): cnt += 1
        self.msg(f"Восстановлено: {cnt}")

    def station_heal(self):
        heal = self.snake.head_max_hp * 0.25
        self.snake.head_hp = min(self.snake.head_max_hp, self.snake.head_hp + heal)
        self.msg("Хил 25%")

    def station_reorder_start(self):
        if len(self.snake.modules) < 2: self.msg("Мало модулей"); return
        self.station_menu, self.reorder_mode, self.reorder_sel = False, True, 0

    def reorder_confirm(self):
        mods = self.snake.modules; i = self.reorder_sel
        if i < len(mods)-1:
            mods[i], mods[i+1] = mods[i+1], mods[i]; self.reorder_sel = i+1; self.msg("Сдвинуто")

    def on_touch_down(self, touch):
        if self.width == 0 or self.height == 0: return
        # Координаты джойстика (в правом нижнем углу)
        joy_x, joy_y = self.width - 120, 120
        if (touch.x - joy_x)**2 + (touch.y - joy_y)**2 <= 100**2:
            touch.ud['joystick'] = True
            self._handle_joystick(touch.x, touch.y, joy_x, joy_y)

    def on_touch_move(self, touch):
        if touch.ud.get('joystick'):
            joy_x, joy_y = self.width - 120, 120
            self._handle_joystick(touch.x, touch.y, joy_x, joy_y)

    def _handle_joystick(self, x, y, cx, cy):
        dx, dy = x - cx, y - cy
        if math.hypot(dx, dy) > 15: # Мертвая зона
            l = math.hypot(dx, dy)
            self.snake.dir = [dx/l, dy/l]
            self.redraw()

    def redraw(self):
        self.canvas.clear()
        with self.canvas:
            # Фон
            Color(*C_BG); Rectangle(pos=(0, 0), size=(self.width, self.height))
            
            # Отрисовка объектов (камера)
            ox, oy = self.cam_x, self.cam_y
            def screen(x, y): return x - ox + self.width/2, y - oy + self.height/2

            # Станции
            for st in self.stations:
                if not st.used:
                    sx, sy = screen(st.x, st.y)
                    Color(*C_STATION); Ellipse(pos=(sx-st.radius, sy-st.radius), size=(st.radius*2, st.radius*2))

            # Подборы
            for p in self.pickups:
                sx, sy = screen(p.x, p.y)
                Color(*MOD_COLORS[p.mtype]); Ellipse(pos=(sx-p.radius, sy-p.radius), size=(p.radius*2, p.radius*2))

            # Враги
            for e in self.enemies:
                sx, sy = screen(e.x, e.y)
                Color(*e.color); Ellipse(pos=(sx-e.radius, sy-e.radius), size=(e.radius*2, e.radius*2))
                # HP бар
                Color(0.4, 0, 0); Rectangle(pos=(sx-14, sy-e.radius-8), size=(28, 4))
                Color(0, 0.86, 0.24); Rectangle(pos=(sx-14, sy-e.radius-8), size=(28*max(0,min(1,e.hp/e.max_hp)), 4))

            # Пули
            for b in self.bullets:
                sx, sy = screen(b.x, b.y)
                Color(*(C_ENEMY_BULLET if b.enemy else C_BULLET))
                Ellipse(pos=(sx-b.radius, sy-b.radius), size=(b.radius*2, b.radius*2))

            # Змея (тело и модули)
            s = self.snake
            for b in s.body:
                sx, sy = screen(b[0], b[1])
                Color(*C_BODY); Rectangle(pos=(sx-CELL*0.45, sy-CELL*0.45), size=(CELL*0.9, CELL*0.9))
            
            # Модули
            mpos = s.module_positions()
            for i, m in enumerate(s.modules):
                if i >= len(mpos): continue
                mx, my = screen(mpos[i][0], mpos[i][1])
                Color(*MOD_COLORS[m.mtype]); Rectangle(pos=(mx-CELL*0.3, my-CELL*0.3), size=(CELL*0.6, CELL*0.6))
            
            # Голова
            hx, hy = screen(s.head[0], s.head[1])
            Color(*C_HEAD); Ellipse(pos=(hx-CELL*0.7, hy-CELL*0.7), size=(CELL*1.4, CELL*1.4))

            # HUD (текст рисуется через Label поверх, здесь только элементы)
            # В данном виджете текст не рисуем, чтобы не грузить Canvas

            # Джойстик (рисуем всегда)
            jx, jy = self.width - 120, 120
            Color(0.2, 0.25, 0.35); Ellipse(pos=(jx-60, jy-60), size=(120, 120))
            Color(0.6, 0.7, 0.8); Line(circle=(jx, jy, 60), width=2)
            
            # Кнопка OK
            Color(0.2, 0.3, 0.2); Rectangle(pos=(20, 60), size=(80, 80))
            Color(1, 1, 1); Line(rectangle=(20, 60, 80, 80), width=2)


class SnakeApp(App):
    def build(self):
        # Главный слой
        self.root = BoxLayout(orientation='vertical')
        
        # Игровое поле
        self.game = GameWidget()
        self.root.add_widget(self.game)
        
        # Обработка кнопки OK (взаимодействие с меню)
        # Так как мы не можем сделать нормальную кнопку поверх Canvas в Kivy без сложных ухищрений,
        # мы ловим нажатия на левый нижний угол прямо в методе on_touch_down (добавим ниже).
        
        return self.root

    def on_start(self):
        # Таймер для обновления HUD (текст)
        Clock.schedule_interval(self.update_hud, 0.1)

    def update_hud(self, dt):
        # Вывод текста через заголовок окна (на телефоне будет не видно, но на ПК работает)
        g = self.game; s = g.snake
        text = f"HP:{int(s.head_hp)} Lvl:{s.level} Wave:{g.wave} $:{s.money}"
        if g.show_upgrade: text += " | УРОВЕНЬ! (Жми OK)"
        if g.game_over: text += " | ИГРА ОКОНЧЕНА (Жми OK)"
        if g.message_timer > 0: text += f" | {g.message}"
        Window.set_title(text)

    def on_touch_down(self, touch):
        # Обработка нажатий на кнопки меню (вне джойстика)
        g = self.game
        if not g: return
        jx, jy = g.width - 120, 120
        
        # Если нажали не на джойстик, а на кнопку OK (левый нижний угол)
        if touch.x < 120 and touch.y < 160:
            if g.game_over: g.reset(); return
            if g.show_upgrade: g.apply_upgrade(0); return
            if g.station_menu: g.station_heal(); g.station_menu = False; return
            g.paused = not g.paused
            return
        return super().on_touch_down(touch)

if __name__ == '__main__':
    Window.size = (800, 600) # Размер окна для ПК
    SnakeApp().run()
