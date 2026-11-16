# -*- coding: utf-8 -*-
"""
==============================================================================
  БУНКЕР-13  —  2D хоррор с видом сверху (Top-Down), весь в одном файле
==============================================================================

УСТАНОВКА:
    pip install pygame            (нужен pygame 2.x и Python 3.8+)

ЗАПУСК:
    python bunker13.py

УПРАВЛЕНИЕ:
    WASD / Стрелки  — движение
    SHIFT           — бег (быстро, но ШУМНО — монстр слышит)
    МЫШЬ            — направление луча фонарика (без мыши луч смотрит по ходу движения)
    F / Левая кнопка мыши — включить / выключить фонарик
    M               — показать / скрыть карту (туман войны)
    E               — спрятаться в шкафчик / выйти из него (внутри монстр не видит, но может заглянуть)
    Q / ПКМ         — бросить бутылку: шум отвлекает монстра (бутылки лежат в лабиринте)
    F2              — качество графики (высокое / низкое, если игра тормозит); F11 — полный экран
    F3              — щадящий режим (меньше тряски и вспышек), N — звук вкл/выкл
    ФИНАЛЬНЫЙ БОС: ПКМ — выстрел в такт (кольцо = цель), Q — перезарядка, ПРОБЕЛ — парирование атаки
    F8 / F9 / F10   — ЧИТЫ: F8 — следующий этаж, F9 — все ключи + заряд + телепорт к двери, F10 — сразу финал
    TAB             — архив прочитанных записок
    ВНИЗ НА -10     — на этаже -3 лифт срывается и падает в шахту: найди динамит и взорви завал (секретная концовка)
    АВАНПОСТ -6     — полноценный этаж (казарма, пост связи, арсенал, столовая, лаборатория, лазарет), у лифта сцена с солдатами и Леной;
                      консоль дальней связи (вызови вертолёт и дождись его; монстра на аванпосте нет), антидот и ампула сыворотки:
                      три новые концовки (эвакуация, «Новая плоть», «Все живы» — антидот в финальном выборе, клавиша 3)
    ПРОБЕЛ x10      — когда монстр схватил: 10 нажатий за 3 секунды, чтобы вырваться (иначе — скример)
    P или ESC       — пауза

ЦЕЛЬ:
    Подняться с этажа -3 на -1: на каждом найди ключи (2, 3 и 3), читай записки с историей
    проекта «ГЛУБИНА», не попадись монстру и доберись до лифта. За последней дверью — финал.
    Последний ключ этажа включает сирену — монстр бежит на звук. Сложность: ←/→ или 1-2-3 в меню.
    Батарейки подзаряжают фонарик. Чем слабее заряд — тем тусклее и
    нестабильнее свет. Монстр видит, слышит и преследует тебя.

АРХИТЕКТУРА (принцип единственной ответственности, SRP):
    У каждого класса ровно одна причина для изменения. Данные забега лежат в Session,
    а классы-системы работают с ним и общаются через события (Session.emit / drain):

    Данные        Session (состояние забега), Level/LevelBuilder (этаж), FLOORS, StoryBook (сюжет), Player,
                  Monster (поведение ИИ)
    Логика        PlayerController (движение), Flashlight (заряд/свет), ThreatSystem (монстр, поимка),
                  PickupSystem (предметы, выход), StealthSystem (шкафчики, бутылки, сирена),
                  Atmosphere (опасность, мерцание, шаги, пыль), Cheats, FinalCutscene (таймлайн финала),
                  BossFight (правила финального боя: тайминг выстрела, перезарядка, парирование),
                  RadioSystem (сюжетные реплики по событиям), AchievementTracker (достижения),
                  StruggleFight (схватка: QTE), PrologueSystem (вступительная кат-сцена),
                  CinematicSystem (падение лифта, подрыв завала), CinematicRenderer (их рисование),
                  PounceSystem / PounceRenderer (бросок монстра на камеру в момент поимки, как у Фокси),
                  EvacSystem (эвакуация с аванпоста)
    Ресурсы       Textures (процедурные картинки), SoundBank (синтез звуков)
    Отрисовка     TextRenderer, Camera, WorldPainter, LightingRenderer, SpriteRenderer, PostFX, Hud, Minimap,
                  ScreenRenderer (меню/пауза/поимка/итоги), PlayView (порядок слоёв кадра),
                  MonsterRenderer (вид монстра), JumpscareRenderer (скример: монстр рвёт героя на клочки), CutsceneRenderer (финал),
                  BossRenderer (рисование боя), RadioRenderer (рация на экране),
                  AchievementRenderer (плашки достижений), StruggleRenderer (схватка),
                  PrologueRenderer (вступительная кат-сцена)
    Сервисы       Audio (воспроизведение), MusicDirector (саундтрек), Settings, Notifier, ScoreBoard, FrameClock
    Ввод          InputRouter (события pygame -> команды, никакой логики игры)
    Приложение    Game (окно, цикл, конечный автомат состояний, связывание компонентов)

Графика полностью процедурная (никаких внешних файлов): текстуры кирпича и
металла, трещины, кровь, туман, пыль, лучи света с настоящими тенями (raycasting),
зерно киноплёнки, виньетка, дрожь камеры. Звуки тоже синтезируются кодом.
"""

import math
import random
import sys

import pygame

# ------------------------------------------------------------------ КОНСТАНТЫ
SW, SH = 1024, 720          # размер окна
FPS = 60
TILE = 56                   # размер тайла в пикселях
MW, MH = 19, 13             # размер лабиринта в «клетках»
GW, GH = MW * 2 + 1, MH * 2 + 1   # размер сетки в тайлах (стены + проходы)
WW, WH = GW * TILE, GH * TILE     # размер мира в пикселях
LS = 2                      # масштаб слоя тьмы (рендерим тьму в половинном разрешении)
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))

NL = 16                     # количество уровней радиуса фонарика (кэш масок)
LMIN, LMAX = 70, 450        # радиус света в мировых пикселях
CONE_HALF = 33              # половина угла конуса фонарика, градусы
AMB_R = 54                  # радиус слабого «собственного» свечения вокруг игрока
RAYS = 240                  # число лучей для расчёта теней
EXT = 13                    # на сколько пикселей свет «заходит» на лицевую грань стены
MM = 4                      # масштаб миникарты (пикселей на тайл)

DIFFS = [
    {"name": "ЛЁГКО", "mspeed": 0.85, "drain": 0.50, "bats": 9, "hear": 0.8, "hunt": 0.15},
    {"name": "НОРМА", "mspeed": 1.00, "drain": 0.60, "bats": 7, "hear": 1.0, "hunt": 0.30},
    {"name": "КОШМАР", "mspeed": 1.15, "drain": 0.75, "bats": 5, "hear": 1.25, "hunt": 0.45},
]

EVAC_TIME = 60.0      # секунд ждать вертолёт после вызова с аванпоста

FLOORS = [   # маршрут: -3 -> (лифт падает) -> -10 -> -8 -> -6 АВАНПОСТ -> -4 -> -2 -> -1 -> финал
    {"name": "ЭТАЖ -3", "title": "ЛАБОРАТОРНЫЙ КОРПУС", "keys": 2, "mspeed": 0.90, "broken": 0.35, "bats_d": 1, "next": 3},
    {"name": "ЭТАЖ -2", "title": "ОПЫТНЫЙ СЕКТОР", "keys": 3, "mspeed": 1.00, "broken": 0.50, "bats_d": 0, "next": 2},
    {"name": "ЭТАЖ -1", "title": "ШЛЮЗ ГЛУБИНЫ", "keys": 3, "mspeed": 1.12, "broken": 0.65, "bats_d": -1, "next": None, "final": True},
    {"name": "ЭТАЖ -10", "title": "ЗАБРОШЕННАЯ ШАХТА", "keys": 2, "mspeed": 1.05, "broken": 0.85, "bats_d": 0, "next": 4,
     "secret": True, "notes": 0},
    {"name": "ЭТАЖ -8", "title": "РЕАКТОРНАЯ", "keys": 3, "mspeed": 1.08, "broken": 0.80, "bats_d": 1, "next": 5, "notes": 0,
     "tint": (255, 205, 170), "metal": True},
    {"name": "ЭТАЖ -6", "title": "АВАНПОСТ «СЕНТИНЕЛ»", "keys": 2, "mspeed": 0.90, "broken": 0.30, "bats_d": 3, "next": 6, "notes": 6,
     "outpost": True, "safe": True, "tint": (205, 218, 238), "metal": True},
    {"name": "ЭТАЖ -4", "title": "СКЛАДЫ", "keys": 3, "mspeed": 1.10, "broken": 0.60, "bats_d": 0, "next": 1, "notes": 0,
     "tint": (208, 228, 198)},
]

RAY_COS = [math.cos(2 * math.pi * i / RAYS) for i in range(RAYS)]
RAY_SIN = [math.sin(2 * math.pi * i / RAYS) for i in range(RAYS)]


# ------------------------------------------------------------------ УТИЛИТЫ
def clamp(v, a, b):
    return a if v < a else b if v > b else v


def angle_diff(a, b):
    """Кратчайшая разность углов a-b в диапазоне [-pi, pi]."""
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def shade(c, d):
    return (clamp(c[0] + d, 0, 255), clamp(c[1] + d, 0, 255), clamp(c[2] + d, 0, 255))


# ------------------------------------------------------------------ ЛАБИРИНТ
def generate_maze():
    """Лабиринт (DFS) + петли + несколько комнат. 1 = стена, 0 = пол."""
    grid = [[1] * GW for _ in range(GH)]
    stack = [(0, 0)]
    seen = {(0, 0)}
    grid[1][1] = 0
    while stack:
        cx, cy = stack[-1]
        nb = []
        for dx, dy in DIRS:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < MW and 0 <= ny < MH and (nx, ny) not in seen:
                nb.append((nx, ny, dx, dy))
        if nb:
            nx, ny, dx, dy = random.choice(nb)
            seen.add((nx, ny))
            grid[2 * ny + 1][2 * nx + 1] = 0
            grid[2 * cy + 1 + dy][2 * cx + 1 + dx] = 0
            stack.append((nx, ny))
        else:
            stack.pop()
    # петли — чтобы монстра нельзя было заманить в один тупик
    for _ in range(MW * MH // 3):
        x = random.randint(1, GW - 2)
        y = random.randint(1, GH - 2)
        if grid[y][x] == 1 and ((x % 2 == 1 and y % 2 == 0) or (x % 2 == 0 and y % 2 == 1)):
            grid[y][x] = 0
    # комнаты 3x3
    for _ in range(6):
        cx = random.randrange(1, MW - 1) * 2 + 1
        cy = random.randrange(1, MH - 1) * 2 + 1
        for yy in range(cy - 1, cy + 2):
            for xx in range(cx - 1, cx + 2):
                grid[yy][xx] = 0
    return grid


def bfs_map(grid, sx, sy):
    """Карта расстояний (в тайлах) от точки (sx, sy)."""
    dist = [[-1] * GW for _ in range(GH)]
    dist[sy][sx] = 0
    q = [(sx, sy)]
    i = 0
    while i < len(q):
        x, y = q[i]
        i += 1
        d = dist[y][x] + 1
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < GW and 0 <= ny < GH and grid[ny][nx] == 0 and dist[ny][nx] < 0:
                dist[ny][nx] = d
                q.append((nx, ny))
    return dist


# ------------------------------------------------------------------ ФИЗИКА / ЛУЧИ
def push_out(grid, x, y, r):
    """Выталкивает круг радиуса r из стен (скольжение вдоль стен)."""
    for ty in range(max(0, int((y - r) // TILE)), min(GH - 1, int((y + r) // TILE)) + 1):
        for tx in range(max(0, int((x - r) // TILE)), min(GW - 1, int((x + r) // TILE)) + 1):
            if grid[ty][tx]:
                cx = min(max(x, tx * TILE), tx * TILE + TILE)
                cy = min(max(y, ty * TILE), ty * TILE + TILE)
                dx, dy = x - cx, y - cy
                d2 = dx * dx + dy * dy
                if d2 < r * r:
                    if d2 > 1e-6:
                        d = math.sqrt(d2)
                        k = (r - d) / d
                        x += dx * k
                        y += dy * k
                    else:
                        x += r
    return x, y


def cast_dir(grid, ox, oy, dx, dy, maxd):
    """Луч по сетке (DDA). Возвращает (расстояние, попал_в_стену)."""
    px, py = ox / TILE, oy / TILE
    mx, my = int(px), int(py)
    ddx = 1e30 if dx == 0 else abs(1.0 / dx)
    ddy = 1e30 if dy == 0 else abs(1.0 / dy)
    if dx < 0:
        sx = -1
        sdx = (px - mx) * ddx
    else:
        sx = 1
        sdx = (mx + 1 - px) * ddx
    if dy < 0:
        sy = -1
        sdy = (py - my) * ddy
    else:
        sy = 1
        sdy = (my + 1 - py) * ddy
    maxt = maxd / TILE
    while True:
        if sdx < sdy:
            t = sdx
            sdx += ddx
            mx += sx
        else:
            t = sdy
            sdy += ddy
            my += sy
        if t > maxt:
            return maxd, False
        if mx < 0 or my < 0 or mx >= GW or my >= GH:
            return t * TILE, True
        if grid[my][mx]:
            return t * TILE, True


def line_clear(grid, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    d = math.hypot(dx, dy)
    if d < 1:
        return True
    _, hit = cast_dir(grid, x0, y0, dx / d, dy / d, d)
    if hit:
        return False
    _, hit = cast_dir(grid, x1, y1, -dx / d, -dy / d, d)     # симметрично: луч по углам тайлов не зависит от направления
    return not hit


def line_clear_thick(grid, x0, y0, x1, y1, w=11):
    """Прямая видимость с учётом толщины тела (три параллельных луча)."""
    dx, dy = x1 - x0, y1 - y0
    d = math.hypot(dx, dy)
    if d < 1:
        return True
    nx, ny = -dy / d, dx / d
    for o in (0, w, -w):
        if not line_clear(grid, x0 + nx * o, y0 + ny * o, x1 + nx * o, y1 + ny * o):
            return False
    return True


# ------------------------------------------------------------------ ПРОЦЕДУРНЫЕ ТЕКСТУРЫ
def add_grain(s, amt):
    """Зернистый шум по всем пикселям тайла (ПРОЦЕДУРНЫЙ ШУМ)."""
    w, h = s.get_size()
    for y in range(h):
        for x in range(w):
            c = s.get_at((x, y))
            n = random.randint(-amt, amt)
            s.set_at((x, y), (clamp(c[0] + n, 0, 255), clamp(c[1] + n, 0, 255), clamp(c[2] + n, 0, 255)))


def blotch(s, color, count, rmin, rmax):
    """Мягкие пятна (плесень, ржавчина, сырость): рисуем и размываем масштабированием."""
    w, h = s.get_size()
    ov = pygame.Surface((w, h), pygame.SRCALPHA)
    for _ in range(count):
        pygame.draw.circle(ov, color, (random.randint(0, w), random.randint(0, h)), random.randint(rmin, rmax))
    ov = pygame.transform.smoothscale(pygame.transform.smoothscale(ov, (max(2, w // 4), max(2, h // 4))), (w, h))
    s.blit(ov, (0, 0))


def draw_crack(s, color):
    """Трещина — случайное блуждание с ответвлениями."""
    x = random.randint(8, TILE - 8)
    y = random.randint(8, TILE - 8)
    a = random.uniform(0, 6.28)
    for _ in range(random.randint(5, 11)):
        a += random.uniform(-0.8, 0.8)
        l = random.randint(3, 7)
        nx, ny = x + math.cos(a) * l, y + math.sin(a) * l
        pygame.draw.line(s, color, (x, y), (nx, ny), 1)
        if random.random() < 0.22:
            b = a + random.choice((-1, 1)) * random.uniform(0.6, 1.2)
            pygame.draw.line(s, color, (x, y), (x + math.cos(b) * 5, y + math.sin(b) * 5), 1)
        x, y = nx, ny


def make_wall_tile(kind=0):
    """
    Стена. Виды: 0 — кирпич (градиент на каждом кирпиче, сколы, фаски), 1 — кирпич с трубой
    (труба на одной высоте — стыкуется с соседними), 2 — бетонная панель с болтами,
    3 — кирпич с предупреждающим знаком. Поверх: потёки воды, плесень, ржавчина, трещины, зерно.
    """
    s = pygame.Surface((TILE, TILE))
    base = random.randint(50, 64)
    s.fill((22, 23, 26))                            # раствор между кирпичами
    if kind == 2:
        c = (base + 6, base + 8, base + 11)
        s.fill(c)
        for _ in range(170):                        # крупинки бетона
            s.set_at((random.randrange(TILE), random.randrange(TILE)), shade(c, random.randint(-15, 15)))
        pygame.draw.rect(s, (18, 19, 22), (0, 0, TILE, TILE), 2)
        pygame.draw.rect(s, shade(c, 16), (2, 2, TILE - 4, TILE - 4), 1)
        for bx, by in ((7, 7), (TILE - 8, 7), (7, TILE - 8), (TILE - 8, TILE - 8)):
            pygame.draw.circle(s, (14, 14, 16), (bx + 1, by + 1), 3)
            pygame.draw.circle(s, (92, 96, 104), (bx, by), 3)
            pygame.draw.circle(s, (150, 154, 160), (bx - 1, by - 1), 1)
        blotch(s, (110, 60, 28, 70), random.randint(1, 3), 4, 9)
    else:
        bh, bw = TILE // 4, TILE // 2
        for row in range(4):
            off = 0 if row % 2 == 0 else bw // 2    # кладка вразбежку
            y0 = row * bh
            x = -off
            while x < TILE:
                sh = random.randint(-9, 9)
                col = (clamp(base + sh, 0, 255), clamp(base + sh + 2, 0, 255), clamp(base + sh + 7, 0, 255))
                for yy in range(bh - 2):            # вертикальный градиент: объём кирпича
                    v = int(9 - 18 * yy / (bh - 3))
                    pygame.draw.line(s, shade(col, v), (x + 1, y0 + 1 + yy), (x + bw - 2, y0 + 1 + yy))
                pygame.draw.line(s, shade(col, 20), (x + 1, y0 + 1), (x + bw - 2, y0 + 1))     # верхняя фаска
                pygame.draw.line(s, shade(col, 10), (x + 1, y0 + 1), (x + 1, y0 + bh - 2))     # левая фаска
                pygame.draw.line(s, shade(col, -22), (x + 1, y0 + bh - 2), (x + bw - 2, y0 + bh - 2))
                if random.random() < 0.32:          # скол на углу
                    cx = x + random.choice((1, bw - 4))
                    cy = y0 + random.choice((1, bh - 4))
                    pygame.draw.rect(s, (22, 23, 26), (cx, cy, random.randint(2, 3), random.randint(2, 3)))
                x += bw
    if kind == 1:                                   # труба
        py0 = 19
        for i in range(12):
            v = int(34 + 66 * math.sin(i / 11.0 * math.pi))
            pygame.draw.line(s, (v, v + 3, v + 8), (0, py0 + i), (TILE, py0 + i))
        pygame.draw.rect(s, (24, 26, 30), (24, py0 - 3, 8, 18))
        pygame.draw.rect(s, (96, 102, 110), (25, py0 - 2, 6, 16))
        pygame.draw.circle(s, (170, 174, 180), (28, py0), 1)
        pygame.draw.circle(s, (170, 174, 180), (28, py0 + 11), 1)
        for i in range(18):                         # ржавый подтёк под фланцем
            pygame.draw.line(s, (max(20, 112 - i * 4), max(12, 56 - i * 2), 22), (28, py0 + 15 + i), (28, py0 + 16 + i))
    elif kind == 3:                                 # знак «Опасность»
        pts = [(28, 9), (47, 43), (9, 43)]
        pygame.draw.polygon(s, (176, 148, 30), pts)
        pygame.draw.polygon(s, (18, 18, 18), pts, 3)
        pygame.draw.line(s, (18, 18, 18), (28, 20), (28, 33), 3)
        pygame.draw.circle(s, (18, 18, 18), (28, 38), 2)
        blotch(s, (70, 44, 14, 110), 2, 4, 9)
    ov = pygame.Surface((TILE, TILE), pygame.SRCALPHA)    # потёки воды
    for _ in range(random.randint(1, 4)):
        x, y, l = random.randint(2, TILE - 3), random.randint(0, 20), random.randint(12, 40)
        for i in range(l):
            a = int(52 * (1 - i / l))
            yy = min(TILE - 1, y + i)
            ov.set_at((x, yy), (0, 0, 0, a))
            ov.set_at((x + 1, yy), (0, 0, 0, a // 2))
    s.blit(ov, (0, 0))
    blotch(s, (40, 70, 38, 70), random.randint(0, 2), 5, 11)       # плесень
    blotch(s, (118, 62, 28, 60), random.randint(0, 2), 4, 9)       # ржавчина
    blotch(s, (0, 0, 0, 90), random.randint(1, 2), 6, 13)          # сырость
    blotch(s, (200, 200, 190, 36), random.randint(0, 1), 5, 10)    # высолы (белёсые налёты)
    for _ in range(random.randint(0, 2)):
        draw_crack(s, (12, 12, 14))
    add_grain(s, 6)
    return s


def make_floor_tile(kind):
    """
    Пол. Виды: 0 — металлическая плита, 1 — решётка, 2 — царапины, 3 — масло/ржавчина,
    4 — предупреждающая разметка, 5 — рифлёный лист «ёлочкой», 6 — бетон с крупой,
    7 — лужа с бликом, 8 — кабель-канал (стыкуется между тайлами).
    """
    s = pygame.Surface((TILE, TILE))
    base = random.randint(30, 40)
    col = (base, base + 3, base + 4)
    if kind == 6:
        c = (base + 5, base + 5, base + 4)
        s.fill(c)
        for _ in range(240):
            s.set_at((random.randrange(TILE), random.randrange(TILE)), shade(c, random.randint(-16, 16)))
        pygame.draw.rect(s, shade(c, -14), (0, 0, TILE, TILE), 1)
        blotch(s, (0, 0, 0, 70), 2, 6, 14)
    else:
        for y in range(TILE):                       # мягкий градиент плиты
            pygame.draw.line(s, shade(col, int(5 - 10 * y / TILE)), (0, y), (TILE, y))
        pygame.draw.rect(s, (base - 11, base - 9, base - 8), (0, 0, TILE, TILE), 2)
        pygame.draw.rect(s, (base + 9, base + 12, base + 13), (2, 2, TILE - 4, TILE - 4), 1)
        for cx, cy in ((6, 6), (TILE - 7, 6), (6, TILE - 7), (TILE - 7, TILE - 7)):
            pygame.draw.circle(s, (base - 14, base - 12, base - 12), (cx + 1, cy + 1), 2)
            pygame.draw.circle(s, (base + 22, base + 24, base + 26), (cx, cy), 2)
            s.set_at((cx - 1, cy - 1), (base + 46, base + 48, base + 50))
    if kind == 1:        # вентиляционная решётка
        for y in range(11, TILE - 10, 5):
            pygame.draw.line(s, (10, 11, 12), (10, y), (TILE - 11, y), 2)
            pygame.draw.line(s, (base + 12, base + 14, base + 15), (10, y + 2), (TILE - 11, y + 2), 1)
    elif kind == 2:      # потёртости и царапины
        for _ in range(8):
            x, y = random.randint(4, TILE - 8), random.randint(4, TILE - 8)
            a = random.uniform(0, 6.28)
            l = random.randint(5, 18)
            pygame.draw.line(s, (base + random.randint(14, 28),) * 3, (x, y),
                             (x + math.cos(a) * l, y + math.sin(a) * l), 1)
    elif kind == 3:      # пятна масла / ржавчины
        blotch(s, (90, 50, 24, 90), random.randint(1, 3), 5, 12)
        blotch(s, (0, 0, 0, 110), random.randint(1, 2), 6, 14)
    elif kind == 4:      # остатки предупреждающей разметки
        for i in range(-TILE, TILE, 10):
            pygame.draw.polygon(s, (78, 68, 24), [(i, TILE), (i + 5, TILE), (i + 17, TILE - 11), (i + 12, TILE - 11)])
    elif kind == 5:      # рифление «ёлочкой»
        for i in range(4):
            for j in range(4):
                cx, cy = 7 + i * 14, 7 + j * 14
                if (i + j) % 2 == 0:
                    a, b = (cx - 4, cy + 4), (cx + 4, cy - 4)
                else:
                    a, b = (cx - 4, cy - 4), (cx + 4, cy + 4)
                pygame.draw.line(s, (base - 9, base - 8, base - 7), (a[0] + 1, a[1] + 1), (b[0] + 1, b[1] + 1), 3)
                pygame.draw.line(s, (base + 24, base + 27, base + 29), a, b, 2)
    elif kind == 7:      # лужа с бликом
        ov = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        pygame.draw.ellipse(ov, (8, 14, 24, 190), (7, 13, 42, 30))
        ov = pygame.transform.smoothscale(pygame.transform.smoothscale(ov, (TILE // 4, TILE // 4)), (TILE, TILE))
        s.blit(ov, (0, 0))
        pygame.draw.arc(s, (100, 124, 148), (14, 18, 28, 18), 3.4, 5.1, 1)
        pygame.draw.line(s, (150, 172, 194), (20, 22), (27, 20), 1)
    elif kind == 8:      # кабель-канал поперёк тайла (линия на одной высоте — стыкуется)
        for i in range(5):
            v = int(20 + 36 * math.sin(i / 4.0 * math.pi))
            pygame.draw.line(s, (v, v - 4, v - 6), (0, 38 + i), (TILE, 38 + i))
        for x in (10, TILE - 12):
            pygame.draw.rect(s, (18, 18, 20), (x, 34, 5, 13))
            pygame.draw.rect(s, (88, 92, 98), (x + 1, 35, 3, 11))
    if random.random() < 0.25:
        draw_crack(s, (base - 16, base - 16, base - 15))
    add_grain(s, 5)
    return s


def make_ao_strips():
    """Затемнение пола у стен (имитация окклюзии) — 4 полоски градиента."""
    h = 14
    top = pygame.Surface((TILE, h), pygame.SRCALPHA)
    for y in range(h):
        a = int(175 * (1 - y / h) ** 2)
        pygame.draw.line(top, (0, 0, 0, a), (0, y), (TILE, y))
    return {
        "top": top,
        "bottom": pygame.transform.flip(top, False, True),
        "left": pygame.transform.rotate(top, 90),
        "right": pygame.transform.rotate(top, -90),
        "h": h,
    }


def add_blood(world, grid, count=24, gw=GW, gh=GH):
    """Лужи, брызги и следы волочения на полу мира."""
    floors = [(x, y) for y in range(gh) for x in range(gw) if grid[y][x] == 0]
    for _ in range(count):
        fx, fy = random.choice(floors)
        cx = fx * TILE + random.randint(8, TILE - 8)
        cy = fy * TILE + random.randint(8, TILE - 8)
        size = random.choice((46, 64, 90))
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        for _ in range(random.randint(10, 26)):
            ang = random.uniform(0, 6.28)
            rr = abs(random.gauss(0, size * 0.33))
            col = (random.randint(70, 118), random.randint(2, 10), random.randint(2, 10), random.randint(120, 200))
            pygame.draw.circle(s, col, (size + math.cos(ang) * rr, size + math.sin(ang) * rr), random.randint(2, 8))
        s = pygame.transform.smoothscale(pygame.transform.smoothscale(s, (size, size)), (size * 2, size * 2))
        world.blit(s, (cx - size, cy - size))
        if random.random() < 0.45:     # след волочения
            ang = random.choice((0, math.pi / 2, math.pi, -math.pi / 2)) + random.uniform(-0.2, 0.2)
            x, y = cx, cy
            for i in range(random.randint(12, 30)):
                x += math.cos(ang) * 4
                y += math.sin(ang) * 4
                rr = max(1, int(5 - i * 0.12))
                pygame.draw.circle(world, (random.randint(64, 96), 4, 6), (int(x), int(y)), rr)


def add_litter(world, grid, gw, gh, count=70):
    """Мусор на полу: листы бумаги, осколки стекла, гайки."""
    floors = [(x, y) for y in range(gh) for x in range(gw) if grid[y][x] == 0]
    for _ in range(count):
        fx, fy = random.choice(floors)
        x = fx * TILE + random.randint(6, TILE - 6)
        y = fy * TILE + random.randint(6, TILE - 6)
        k = random.random()
        a = random.uniform(0, 6.28)
        ca, sa = math.cos(a), math.sin(a)
        if k < 0.45:                         # лист бумаги с «текстом»
            w, h = random.randint(6, 9), random.randint(8, 12)
            pts = [(x + ca * dx - sa * dy, y + sa * dx + ca * dy) for dx, dy in ((-w, -h), (w, -h), (w, h), (-w, h))]
            pygame.draw.polygon(world, (10, 10, 12), [(px + 2, py + 2) for px, py in pts])
            g = random.randint(150, 190)
            pygame.draw.polygon(world, (g, g - 4, g - 14), pts)
            for i in range(-2, 3):
                x0, y0 = x - ca * w * 0.7 - sa * i * 3, y - sa * w * 0.7 + ca * i * 3
                x1, y1 = x + ca * w * 0.7 - sa * i * 3, y + sa * w * 0.7 + ca * i * 3
                pygame.draw.line(world, (90, 88, 84), (x0, y0), (x1, y1), 1)
        elif k < 0.8:                        # осколки стекла
            for _ in range(random.randint(3, 6)):
                sx, sy = x + random.randint(-9, 9), y + random.randint(-9, 9)
                b = random.uniform(0, 6.28)
                pts = [(sx + math.cos(b + i * 2.1) * random.randint(1, 4),
                        sy + math.sin(b + i * 2.1) * random.randint(1, 4)) for i in range(3)]
                pygame.draw.polygon(world, (random.randint(110, 160), random.randint(140, 180),
                                            random.randint(150, 190)), pts)
        else:                                # гайка
            pygame.draw.circle(world, (10, 10, 12), (x + 1, y + 1), 3)
            pygame.draw.circle(world, (96, 100, 106), (x, y), 3)
            pygame.draw.circle(world, (30, 30, 34), (x, y), 1)


def make_glow(radius, color, max_a=140):
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for i in range(radius, 0, -1):
        a = int(max_a * (1 - i / radius) ** 2)
        pygame.draw.circle(s, (color[0], color[1], color[2], a), (radius, radius), i)
    return s


def make_vignette(w, h, color, max_alpha, power, inner=0.45):
    """Виньетка: считаем в малом разрешении и растягиваем (быстро и мягко)."""
    sw, sh = 64, 45
    s = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for y in range(sh):
        for x in range(sw):
            nx = (x / (sw - 1)) * 2 - 1
            ny = (y / (sh - 1)) * 2 - 1
            d = math.sqrt(nx * nx * 0.8 + ny * ny)
            a = clamp((d - inner) / 0.85, 0, 1) ** power
            s.set_at((x, y), (color[0], color[1], color[2], int(max_alpha * a)))
    return pygame.transform.smoothscale(s, (w, h))


def make_noise_gray(w, h):
    s = pygame.Surface((w, h))
    for y in range(h):
        for x in range(w):
            v = random.randint(0, 255)
            s.set_at((x, y), (v, v, v))
    return s


def make_fog(w, h, strength):
    """Туман: два слоя сглаженного шума, складываются в мягкие облака."""
    a = pygame.transform.smoothscale(make_noise_gray(14, 10), (w, h))
    b = pygame.transform.smoothscale(make_noise_gray(5, 4), (w, h))
    a.fill((127, 127, 127), special_flags=pygame.BLEND_RGB_MULT)
    b.fill((127, 127, 127), special_flags=pygame.BLEND_RGB_MULT)
    a.fill((255, 255, 255), special_flags=pygame.BLEND_RGB_MULT)
    a.blit(b, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    a.fill(strength, special_flags=pygame.BLEND_RGB_MULT)   # итоговая яркость и оттенок
    return a


def make_skin_texture(w, h, base, veins=8, vein=(120, 30, 40), spots=6, spot=(70, 60, 50)):
    """Процедурная «кожа»: зернистый шум, мягкие пятна, ветвящиеся вены."""
    s = pygame.Surface((w, h))
    s.fill(base)
    for y in range(h):
        for x in range(w):
            if random.random() < 0.6:
                s.set_at((x, y), shade(base, random.randint(-13, 13)))
    ov = pygame.Surface((w, h), pygame.SRCALPHA)
    for _ in range(spots):
        pygame.draw.circle(ov, (spot[0], spot[1], spot[2], 100), (random.randint(0, w), random.randint(0, h)),
                           random.randint(max(2, w // 12), max(3, w // 5)))
    ov = pygame.transform.smoothscale(pygame.transform.smoothscale(ov, (max(2, w // 4), max(2, h // 4))), (w, h))
    s.blit(ov, (0, 0))
    for _ in range(veins):
        x, y, a = random.uniform(0, w), random.uniform(0, h), random.uniform(0, 6.28)
        for _ in range(random.randint(5, 12)):
            a += random.uniform(-0.7, 0.7)
            nx, ny = x + math.cos(a) * random.uniform(3, 8), y + math.sin(a) * random.uniform(3, 8)
            pygame.draw.line(s, vein, (x, y), (nx, ny), 1)
            x, y = nx, ny
    return s


def make_fabric(color, size=64):
    """Ткань: переплетение нитей и зерно."""
    s = pygame.Surface((size, size))
    s.fill(color)
    for i in range(0, size, 2):
        pygame.draw.line(s, shade(color, 7), (0, i), (size, i))
        pygame.draw.line(s, shade(color, -7), (i, 0), (i, size))
    for _ in range(size * 6):
        s.set_at((random.randrange(size), random.randrange(size)), shade(color, random.randint(-10, 10)))
    return s


def textured(size, draw_mask, tex):
    """Фигура, залитая текстурой: рисуем белую маску и умножаем на текстуру (альфа остаётся от маски)."""
    mask = pygame.Surface(size, pygame.SRCALPHA)
    draw_mask(mask)
    t = tex if tex.get_size() == tuple(size) else pygame.transform.smoothscale(tex, size)
    mask.blit(t, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    return mask


def screen_glitch(scr, k, allow_negative=True):
    """Цифровой сбой кадра: RGB-сдвиг каналов, горизонтальные разрывы, редкие негативные вспышки. k — сила 0..1."""
    if k <= 0.02:
        return
    tmp = scr.copy()
    off = int(2 + 14 * k)
    red = tmp.copy()
    red.fill((255, 0, 0), special_flags=pygame.BLEND_RGB_MULT)
    cyan = tmp.copy()
    cyan.fill((0, 255, 255), special_flags=pygame.BLEND_RGB_MULT)
    scr.fill((0, 0, 0))
    scr.blit(red, (-off, 0), special_flags=pygame.BLEND_RGB_ADD)
    scr.blit(cyan, (off, 0), special_flags=pygame.BLEND_RGB_ADD)
    for _ in range(int(2 + 8 * k)):
        y = random.randint(0, SH - 40)
        scr.blit(tmp, (int(random.uniform(-60, 60) * k), y), pygame.Rect(0, y, SW, random.randint(4, 40)))
    if allow_negative and random.random() < 0.12 * k:                       # негатив на один кадр
        inv = pygame.Surface((SW, SH))
        inv.fill((255, 255, 255))
        inv.blit(scr, (0, 0), special_flags=pygame.BLEND_RGB_SUB)
        scr.blit(inv, (0, 0))


_rr = random.Random(4)
RUBBLE = [(_rr.uniform(-1, 1), _rr.uniform(-1, 1), _rr.uniform(0.35, 0.8), _rr.randint(62, 120), _rr.uniform(0, 6.283)) for _ in range(16)]


def draw_rubble(scr, cx, cy, sc=1.0):
    """Завал: груда серых камней с тёмной каймой и бликами."""
    for (ox, oy, r, g, a) in RUBBLE:
        x, y, rr = cx + ox * 34 * sc, cy + oy * 28 * sc, r * 30 * sc
        pts = [(x + math.cos(a + i * 1.25) * rr * (0.7 + 0.3 * ((i * 3) % 2)), y + math.sin(a + i * 1.25) * rr * (0.7 + 0.3 * ((i * 3) % 2)))
               for i in range(5)]
        pygame.draw.polygon(scr, (22, 22, 24), pts)
        pygame.draw.polygon(scr, (g, g - 4, g - 8), [(x + (px - x) * 0.82, y + (py - y) * 0.82) for px, py in pts])
        pygame.draw.line(scr, (g + 40, g + 36, g + 30), pts[0], pts[1], 2)


def draw_dynamite(scr, x, y, sc=1.0, t=0.0, lit=False):
    """Пучок динамита: три красные шашки, чёрная стяжка, фитиль (искра мигает; lit — горит)."""
    for ox in (-8, 0, 8):
        pygame.draw.rect(scr, (60, 8, 8), (int(x + (ox - 5) * sc), int(y - 14 * sc), int(10 * sc), int(28 * sc)))
        pygame.draw.rect(scr, (200, 34, 34), (int(x + (ox - 4) * sc), int(y - 13 * sc), int(8 * sc), int(26 * sc)))
        pygame.draw.line(scr, (240, 120, 110), (int(x + (ox - 2) * sc), int(y - 12 * sc)), (int(x + (ox - 2) * sc), int(y + 10 * sc)), 1)
    pygame.draw.rect(scr, (18, 18, 20), (int(x - 14 * sc), int(y - 3 * sc), int(28 * sc), int(6 * sc)))
    fx, fy = x + 6 * sc, y - 16 * sc
    pygame.draw.lines(scr, (110, 96, 70), False, [(fx, fy), (fx + 8 * sc, fy - 8 * sc), (fx + 4 * sc, fy - 16 * sc)], max(1, int(2 * sc)))
    if lit or int(t * 3) % 2 == 0:
        pygame.draw.circle(scr, (255, 220, 90), (int(fx + 4 * sc), int(fy - 16 * sc)), max(2, int(4 * sc)))


def make_tiled_room(tex):
    """Пол комнаты из тех же процедурных тайлов (для кат-сцен)."""
    room = pygame.Surface((SW + TILE, SH + TILE))
    for ty in range(0, SH + TILE, TILE):
        for tx_ in range(0, SW + TILE, TILE):
            room.blit(random.choice(tex.floor_tiles), (tx_, ty))
    return room


OUTPOST_ROOMS = (("КАЗАРМА", 4, 4, 12, 10), ("ПОСТ СВЯЗИ", 14, 4, 24, 10), ("АРСЕНАЛ", 26, 4, 34, 10),
                 ("СТОЛОВАЯ", 4, 16, 12, 22), ("ЛАБОРАТОРИЯ", 14, 16, 24, 22), ("ЛАЗАРЕТ", 26, 16, 34, 22))


def generate_outpost():
    """
    Аванпост «Сентинел» (не лабиринт, а спроектированный этаж): кольцевой коридор по периметру, главный зал
    через весь этаж и шесть комнат (казарма, пост связи, арсенал, столовая, лаборатория, лазарет) с двумя-тремя
    дверями каждая — есть где прятаться и где убегать по кругу. Внутри комнат — одиночные ящики-укрытия.
    """
    grid = [[1] * GW for _ in range(GH)]

    def carve(x0, y0, x1, y1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                grid[y][x] = 0

    carve(1, 1, GW - 2, 2)
    carve(1, GH - 3, GW - 2, GH - 2)
    carve(1, 1, 2, GH - 2)
    carve(GW - 3, 1, GW - 2, GH - 2)
    carve(1, 12, GW - 2, 14)
    rooms = []
    for name, x0, y0, x1, y1 in OUTPOST_ROOMS:
        carve(x0, y0, x1, y1)
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        top = y0 < 12
        grid[11 if top else 15][mx] = 0                       # дверь в главный зал
        grid[3 if top else 23][mx] = 0                        # дверь в кольцевой коридор
        rooms.append({"name": name, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "mid": (mx, my)})
    for y in (7, 19):                                         # двери между комнатами и в боковые коридоры
        for x in (3, 13, 25, 35):
            grid[y][x] = 0
    for r in rooms:                                           # ящики-укрытия: одиночные, не на проходах — проходимость не страдает
        cand = [(x, y) for y in range(r["y0"] + 1, r["y1"]) for x in range(r["x0"] + 1, r["x1"])
                if x != r["mid"][0] and y != r["mid"][1]]
        random.shuffle(cand)
        placed = 0
        for (x, y) in cand:
            if placed >= 4:
                break
            if any(grid[y + dy][x + dx] == 1 for dx, dy in DIRS + ((1, 1), (-1, -1), (1, -1), (-1, 1))):
                continue
            grid[y][x] = 1
            placed += 1
    return grid, rooms


def paint_outpost(world, rooms, font):
    """Обстановка аванпоста поверх пола: койки, столы, стеллажи, лазаретные кровати, разметка и подписи комнат."""
    T = TILE
    tints = {"КАЗАРМА": (60, 80, 50), "ПОСТ СВЯЗИ": (40, 70, 90), "АРСЕНАЛ": (90, 70, 40),
             "СТОЛОВАЯ": (80, 70, 60), "ЛАБОРАТОРИЯ": (50, 90, 80), "ЛАЗАРЕТ": (100, 50, 50)}

    def bed(x, y, blanket):
        pygame.draw.rect(world, (24, 26, 24), (x - 2, y - 2, 52, 30))
        pygame.draw.rect(world, blanket, (x, y, 48, 26))
        pygame.draw.rect(world, (204, 204, 194), (x + 2, y + 3, 11, 20))

    for r in rooms:
        x0, y0 = r["x0"] * T, r["y0"] * T
        w, h = (r["x1"] - r["x0"] + 1) * T, (r["y1"] - r["y0"] + 1) * T
        ov = pygame.Surface((w, h), pygame.SRCALPHA)
        ov.fill(tints[r["name"]] + (46,))
        world.blit(ov, (x0, y0))
        n = r["name"]
        if n == "КАЗАРМА":
            for i in range(4):
                bed(x0 + 30 + i * 110, y0 + 14, (70, 86, 60))
                bed(x0 + 30 + i * 110, y0 + h - 44, (70, 86, 60))
        elif n == "ПОСТ СВЯЗИ":
            pygame.draw.rect(world, (24, 20, 16), (x0 + 26, y0 + 10, w - 52, 30))
            pygame.draw.rect(world, (84, 70, 52), (x0 + 28, y0 + 12, w - 56, 26))
            for i in range(5):
                pygame.draw.rect(world, (12, 50, 44), (x0 + 44 + i * 96, y0 + 14, 34, 18))
                pygame.draw.line(world, (80, 230, 170), (x0 + 48 + i * 96, y0 + 20), (x0 + 70 + i * 96, y0 + 20), 2)
            pygame.draw.line(world, (120, 126, 134), (x0 + w - 30, y0 + 12), (x0 + w - 30, y0 - 14), 3)
        elif n == "АРСЕНАЛ":
            for i in range(5):
                pygame.draw.rect(world, (28, 30, 34), (x0 + 22 + i * 56, y0 + 8, 46, 20))
                for j in range(3):
                    pygame.draw.line(world, (90, 94, 100), (x0 + 28 + i * 56 + j * 14, y0 + 10), (x0 + 28 + i * 56 + j * 14, y0 + 26), 3)
            for i in range(3):
                pygame.draw.rect(world, (60, 46, 26), (x0 + 24 + i * 64, y0 + h - 38, 52, 28))
                pygame.draw.rect(world, (120, 94, 52), (x0 + 26 + i * 64, y0 + h - 36, 48, 24))
        elif n == "СТОЛОВАЯ":
            for j in range(2):
                pygame.draw.rect(world, (30, 24, 18), (x0 + 40, y0 + 52 + j * 150, w - 80, 34))
                pygame.draw.rect(world, (112, 92, 66), (x0 + 42, y0 + 54 + j * 150, w - 84, 30))
                for i in range(6):
                    pygame.draw.rect(world, (60, 50, 38), (x0 + 50 + i * 60, y0 + 90 + j * 150, 40, 8))
        elif n == "ЛАБОРАТОРИЯ":
            for i in range(5):
                pygame.draw.rect(world, (30, 36, 38), (x0 + 22 + i * 56, y0 + 8, 46, 26))
                pygame.draw.rect(world, (150, 176, 180), (x0 + 24 + i * 56, y0 + 10, 42, 22))
                pygame.draw.rect(world, (60, 200, 170), (x0 + 30 + i * 56, y0 + 14, 30, 6))
            pygame.draw.rect(world, (30, 36, 38), (x0 + w - 84, y0 + h - 60, 64, 44))
            pygame.draw.rect(world, (90, 200, 220), (x0 + w - 80, y0 + h - 56, 56, 36))
        elif n == "ЛАЗАРЕТ":
            for i in range(3):
                bed(x0 + 34 + i * 120, y0 + 14, (200, 204, 210))
            pygame.draw.rect(world, (170, 30, 34), (x0 + w // 2 - 6, y0 + h - 74, 12, 40))
            pygame.draw.rect(world, (170, 30, 34), (x0 + w // 2 - 20, y0 + h - 60, 40, 12))
        lab = font.render(n, True, (150, 162, 150))
        world.blit(lab, (x0 + 8, y0 + h - 22))
    for x in range(2 * T, (GW - 2) * T, 64):                  # разметка главного зала: жёлтый пунктир
        pygame.draw.rect(world, (190, 168, 40), (x, 13 * T + T // 2 - 2, 34, 4))


MASK_W = (255, 255, 255, 255)


def radial_gray(r, peak):
    """RGB-градиент (центр ярче) для подсветки/затенения через BLEND_RGB_ADD / SUB."""
    s = pygame.Surface((r * 2, r * 2))
    for i in range(r, 0, -1):
        v = int(peak * (1 - i / r) ** 1.6)
        pygame.draw.circle(s, (v, v, v), (r, r), i)
    return s

def light_pass(base, spots):
    """spots: (cx, cy, r, peak, sign). Объём: блики ADD, тени SUB. Альфа спрайта не меняется — вне фигуры ничего не видно."""
    for cx, cy, r, peak, sign in spots:
        g = radial_gray(r, peak)
        base.blit(g, (cx - r, cy - r), special_flags=pygame.BLEND_RGB_ADD if sign > 0 else pygame.BLEND_RGB_SUB)

def outlined(base, col=(10, 10, 12), w=2):
    """Тёмный контур по силуэту (силуэт чернится и смещается по 8 направлениям под спрайт)."""
    sil = base.copy()
    sil.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGB_MULT)
    sil.fill((col[0], col[1], col[2], 255), special_flags=pygame.BLEND_RGB_ADD)
    out = pygame.Surface(base.get_size(), pygame.SRCALPHA)
    for dx, dy in ((-w, 0), (w, 0), (0, -w), (0, w), (-w, -w), (w, w), (-w, w), (w, -w)):
        out.blit(sil, (dx, dy))
    out.blit(base, (0, 0))
    return out

def knit(base, cx, cy, r0, r1, col, rings, spokes):
    """Вязка: кольца из мелких «галочек»."""
    for k in range(rings):
        r = r0 + (r1 - r0) * k / max(1, rings - 1)
        n = int(spokes * (0.4 + 0.6 * r / r1))
        for i in range(n):
            a = 2 * math.pi * i / n + (k % 2) * math.pi / n
            x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
            tx, ty = -math.sin(a), math.cos(a)
            pygame.draw.line(base, col, (x - tx * 2 + math.cos(a) * 1.5, y - ty * 2 + math.sin(a) * 1.5), (x, y), 1)
            pygame.draw.line(base, col, (x + tx * 2 + math.cos(a) * 1.5, y + ty * 2 + math.sin(a) * 1.5), (x, y), 1)

def make_player_hi():
    """Марк сверху (смотрит вправо), 128x128: рюкзак с клапаном и пряжками, куртка с швами, плечами и светоотражающими полосами,
    капюшон-воротник, вязаная шапка с отворотом и помпоном, уши, пряди. Освещение сверху-слева, контур, объём."""
    S = 128
    base = pygame.Surface((S, S), pygame.SRCALPHA)
    # --- рюкзак
    pk = textured((S, S), lambda m: pygame.draw.rect(m, MASK_W, (6, 34, 42, 60), border_radius=10), make_fabric((96, 72, 46), S))
    base.blit(pk, (0, 0))
    pygame.draw.rect(base, (70, 50, 30), (6, 34, 42, 20), border_radius=9)                    # клапан
    pygame.draw.rect(base, (108, 82, 54), (9, 36, 36, 15), border_radius=7)
    for x in (16, 36):
        pygame.draw.rect(base, (40, 30, 22), (x, 52, 7, 9), border_radius=2)                    # пряжки
        pygame.draw.rect(base, (186, 170, 110), (x + 1, 54, 5, 5), border_radius=1)
    for y in (66, 78):
        pygame.draw.line(base, (52, 38, 24), (9, y), (46, y), 2)                                # стяжки
    for y in (50, 74):
        pygame.draw.rect(base, (82, 60, 38), (2, y, 8, 18), border_radius=4)                    # боковые карманы
    pygame.draw.rect(base, (30, 22, 14), (6, 34, 42, 60), 2, border_radius=10)
    for (x1, y1, x2, y2) in ((12, 38, 12, 52), (40, 38, 40, 52)):                                 # швы клапана
        pygame.draw.line(base, (58, 42, 28), (x1, y1), (x2, y2), 1)
    # --- плечи/рукава и торс
    jf = make_fabric((52, 76, 94), S)
    for (cx, cy) in ((64, 21), (64, 107)):
        sl = textured((S, S), lambda m, cx=cx, cy=cy: pygame.draw.ellipse(m, MASK_W, (cx - 22, cy - 11, 44, 22)), jf)
        base.blit(sl, (0, 0))
        pygame.draw.ellipse(base, (22, 34, 44), (cx - 22, cy - 11, 44, 22), 2)
    torso = textured((S, S), lambda m: pygame.draw.ellipse(m, MASK_W, (30, 16, 66, 96)), jf)
    base.blit(torso, (0, 0))
    pygame.draw.ellipse(base, (22, 34, 44), (30, 16, 66, 96), 3)
    for (cx, cy) in ((72, 22), (72, 106)):                                                       # светоотражающие полосы на рукавах
        pygame.draw.rect(base, (44, 60, 74), (cx - 6, cy - 8, 12, 16), border_radius=2)
        pygame.draw.rect(base, (226, 214, 110), (cx - 3, cy - 8, 3, 16))
        pygame.draw.rect(base, (226, 214, 110), (cx + 2, cy - 8, 3, 16))
    pygame.draw.line(base, (26, 40, 52), (34, 64), (70, 64), 2)                                   # центральный шов спины
    pygame.draw.arc(base, (30, 46, 60), (36, 22, 52, 84), -1.2, 1.2, 2)                           # кокетка
    for (x1, y1, x2, y2) in ((44, 34, 58, 38), (44, 94, 58, 90), (50, 50, 60, 54), (50, 78, 60, 74)):   # складки ткани
        pygame.draw.line(base, (36, 54, 68), (x1, y1), (x2, y2), 2)
    # --- воротник-капюшон
    pygame.draw.circle(base, (28, 42, 54), (79, 64), 22)
    col = textured((S, S), lambda m: pygame.draw.circle(m, MASK_W, (79, 64), 20), make_fabric((60, 86, 104), S))
    base.blit(col, (0, 0))
    pygame.draw.circle(base, (24, 38, 50), (79, 64), 20, 2)
    pygame.draw.circle(base, (24, 38, 50), (79, 64), 15, 1)
    # --- уши, шапка
    for sd in (-1, 1):
        pygame.draw.ellipse(base, (150, 112, 92), (76, 64 + sd * 17 - 5, 10, 11))
        pygame.draw.ellipse(base, (206, 166, 140), (78, 64 + sd * 17 - 3, 5, 7))
    hat = textured((S, S), lambda m: pygame.draw.circle(m, MASK_W, (81, 64), 16), make_fabric((150, 48, 44), S))
    base.blit(hat, (0, 0))
    pygame.draw.circle(base, (62, 18, 18), (81, 64), 16, 2)
    pygame.draw.circle(base, (92, 28, 28), (81, 64), 12, 1)
    knit(base, 81, 64, 4, 12, (100, 30, 30), 5, 22)
    pygame.draw.arc(base, (112, 34, 32), (65, 48, 32, 32), math.pi * 0.55, math.pi * 1.45, 5)       # отворот сзади
    for k in range(7):                                                                              # помпон
        a = k * 0.9
        pygame.draw.line(base, (214, 196, 188), (81, 64), (81 + math.cos(a) * 4, 64 + math.sin(a) * 4), 2)
    pygame.draw.circle(base, (236, 222, 214), (81, 64), 3)
    for k in range(6):                                                                              # выбившиеся пряди
        a = math.pi * (0.78 + 0.07 * k)
        pygame.draw.line(base, (46, 32, 24), (81 + math.cos(a) * 15, 64 + math.sin(a) * 15), (81 + math.cos(a) * 19, 64 + math.sin(a) * 19 - 1), 1)
    # --- объём: блики сверху-слева, тени снизу-справа
    light_pass(base, [(52, 40, 34, 70, 1), (78, 52, 22, 78, 1), (22, 48, 26, 40, 1),
                      (78, 94, 30, 52, -1), (60, 108, 26, 44, -1), (30, 86, 24, 36, -1), (100, 66, 22, 30, -1)])
    return outlined(base, (8, 10, 12), 2)

def jag_poly(cx, cy, rw, rh, n, jit, rnd):
    """Рваный контур (края содранной кожи)."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1.0 + rnd.uniform(-jit, jit)
        pts.append((cx + math.cos(a) * rw * k, cy + math.sin(a) * rh * k))
    return pts

def make_monster_hi():
    """Тело и череп монстра сверху (смотрит вправо), 224x224: кожа с венами и пятнами, содранная кожа с мышечными волокнами,
    рёбра-дуги с суставами, позвоночник с отростками, лопатки, рана со швами, череп с надбровьями, скулами и красным светом в глазницах."""
    rnd = random.Random(11)
    S = 224
    base = pygame.Surface((S, S), pygame.SRCALPHA)
    flesh = make_skin_texture(S, S, (138, 124, 114), veins=22, vein=(112, 28, 38), spots=14, spot=(62, 48, 46))
    neck = textured((S, S), lambda m: pygame.draw.ellipse(m, MASK_W, (116, 90, 48, 44)), flesh)
    base.blit(neck, (0, 0))
    pygame.draw.ellipse(base, (30, 16, 16), (116, 90, 48, 44), 3)
    torso = textured((S, S), lambda m: pygame.draw.ellipse(m, MASK_W, (46, 40, 112, 144)), flesh)
    base.blit(torso, (0, 0))
    pygame.draw.ellipse(base, (30, 14, 14), (46, 40, 112, 144), 4)
    # лопатки
    for sd in (-1, 1):
        cy = 112 + sd * 46
        pts = [(86, cy - 16), (112, cy - 12), (118, cy + 6), (96, cy + 18), (82, cy + 4)]
        pygame.draw.polygon(base, (50, 36, 32), pts)
        pygame.draw.polygon(base, (206, 196, 172), [(100 + (x - 100) * 0.82, cy + (y - cy) * 0.78) for x, y in pts])
        pygame.draw.line(base, (150, 138, 118), (92, cy - 4), (112, cy + 2), 2)
    # содранная кожа: мышечные пласты с волокнами, мокрыми бликами и рваным краем
    for (cx, cy, rw, rh, ang) in ((92, 78, 22, 14, 0.2), (122, 148, 24, 16, -0.3), (80, 134, 15, 12, 0.1), (126, 84, 12, 10, 0.4)):
        edge = [(x, y) for x, y in jag_poly(cx, cy, rw + 4, rh + 4, 14, 0.16, rnd)]
        pygame.draw.polygon(base, (60, 14, 18), edge)
        pygame.draw.polygon(base, (132, 28, 34), jag_poly(cx, cy, rw, rh, 12, 0.08, rnd))
        for k in range(-rw + 3, rw - 2, 4):
            pygame.draw.line(base, (88, 14, 22), (cx + k, cy - rh + 3), (cx + k + 2, cy + rh - 3), 2)
            pygame.draw.line(base, (166, 54, 58), (cx + k + 1, cy - rh + 4), (cx + k + 3, cy + rh - 5), 1)
        pygame.draw.circle(base, (244, 186, 176), (cx - rw // 2, cy - rh // 2), 2)
    # рёбра: изогнутые костяные дуги, длина зависит от ширины торса в этой точке; сустав у позвоночника
    for i in range(8):
        x = 60 + i * 12
        half = 72 * math.sqrt(max(0.0, 1 - ((x - 102) / 58.0) ** 2))
        for sd in (-1, 1):
            ln = half * (0.80 - 0.04 * ((i + (sd > 0)) % 3))
            p1 = (x, 112 + sd * 4)
            p2 = (x + 4, 112 + sd * ln * 0.55)
            p3 = (x - 5, 112 + sd * ln)
            pygame.draw.lines(base, (60, 42, 38), False, [p1, p2, p3], 6)
            pygame.draw.lines(base, (206, 196, 172), False, [(p1[0] + 1, p1[1]), (p2[0] + 1, p2[1]), (p3[0] + 1, p3[1] - sd)], 4)
            pygame.draw.lines(base, (246, 238, 216), False, [(p1[0] + 1, p1[1] + sd * 2), (p2[0] + 2, p2[1]), (p3[0] + 1, p3[1] - sd * 4)], 1)
            pygame.draw.circle(base, (66, 50, 42), (int(p3[0]), int(p3[1])), 4)
            pygame.draw.circle(base, (190, 178, 152), (int(p3[0]), int(p3[1])), 3)
    # позвоночник: позвонки с отростками
    for i in range(10):
        x = 56 + i * 10
        pygame.draw.line(base, (60, 44, 38), (x, 112), (x - 8, 112 + (i % 2) * 2), 5)
        pygame.draw.circle(base, (34, 22, 20), (x + 1, 113), 7)
        pygame.draw.circle(base, (226, 216, 190), (x, 112), 6)
        pygame.draw.circle(base, (176, 164, 140), (x + 1, 114), 3)
        pygame.draw.circle(base, (255, 250, 232), (x - 2, 110), 1)
    # рана со швами
    wound = [(104, 120), (120, 112), (136, 120), (132, 140), (112, 144)]
    pygame.draw.polygon(base, (66, 8, 12), wound)
    pygame.draw.polygon(base, (138, 26, 32), [(110, 124), (120, 117), (131, 124), (127, 136), (114, 138)])
    for k in range(5):
        pygame.draw.line(base, (18, 12, 10), (108 + k * 6, 114), (110 + k * 6, 144), 2)
        pygame.draw.line(base, (18, 12, 10), (106 + k * 6, 122), (114 + k * 6, 130), 1)
    # череп
    bone = make_skin_texture(S, S, (210, 202, 176), veins=5, vein=(124, 102, 90), spots=8, spot=(126, 104, 82))
    skull = textured((S, S), lambda m: pygame.draw.ellipse(m, MASK_W, (132, 84, 76, 56)), bone)
    base.blit(skull, (0, 0))
    pygame.draw.ellipse(base, (44, 30, 28), (132, 84, 76, 56), 3)
    pygame.draw.arc(base, (150, 134, 112), (138, 88, 56, 22), 0.4, 2.7, 3)                           # надбровья
    pygame.draw.arc(base, (150, 134, 112), (138, 106, 56, 22), -2.7, -0.4, 3)
    for (x1, y1, x2, y2) in ((144, 92, 160, 104), (192, 100, 180, 116), (152, 132, 168, 120), (150, 112, 164, 114)):   # трещины
        pygame.draw.line(base, (60, 44, 38), (x1, y1), (x2, y2), 2)
    pygame.draw.line(base, (30, 22, 20), (170, 86), (170, 138), 1)                                    # шов черепа
    for k in range(7):
        pygame.draw.line(base, (30, 22, 20), (168, 90 + k * 7), (172, 93 + k * 7), 1)
    for yy in (94, 118):                                                                              # глазницы с красным огнём
        pygame.draw.ellipse(base, (4, 0, 0), (164, yy - 8, 28, 20))
        pygame.draw.ellipse(base, (110, 16, 18), (164, yy - 8, 28, 20), 2)
        pygame.draw.ellipse(base, (170, 24, 22), (174, yy - 3, 11, 9))
        pygame.draw.circle(base, (255, 176, 120), (178, yy - 1), 2)
    pygame.draw.line(base, (30, 18, 16), (200, 106), (206, 112), 3)                                   # ноздри
    pygame.draw.line(base, (30, 18, 16), (200, 118), (206, 112), 3)
    light_pass(base, [(82, 62, 46, 64, 1), (170, 96, 30, 60, 1), (70, 120, 30, 36, 1),
                      (110, 168, 44, 58, -1), (150, 150, 26, 40, -1), (186, 130, 22, 36, -1), (60, 160, 26, 34, -1)])
    return outlined(base, (8, 4, 4), 3)

PERSONS = {
    "soldier": {"coat": (84, 98, 66)}, "lena": {"coat": (196, 120, 64)}, "scientist": {"coat": (222, 224, 230)},
    "kessler": {"coat": (34, 34, 42)}, "guard": {"coat": (66, 70, 80)},
}

def make_person_hi(kind):
    """Человек сверху (смотрит вправо), 96x96: плечи/куртка из ткани, голова с волосами/шлемом/фуражкой, детали по роли
    (разгрузка и автомат, шарф и хвост, халат с бейджем, костюм, форма). Свет сверху-слева, контур."""
    S = 96
    rnd = random.Random({"soldier": 1, "lena": 2, "scientist": 3, "kessler": 4, "guard": 5}[kind])
    base = pygame.Surface((S, S), pygame.SRCALPHA)
    coat = PERSONS[kind]["coat"]
    cf = make_fabric(coat, S)
    if kind == "soldier":                                    # камуфляж: пятна поверх ткани
        for _ in range(26):
            pygame.draw.ellipse(cf, shade(coat, rnd.choice((-30, -18, 16))), (rnd.randint(0, S - 12), rnd.randint(0, S - 8), rnd.randint(6, 16), rnd.randint(4, 10)))
    sk, sk_d = (206, 168, 140), (150, 112, 92)

    def body(rect, col=None, tex=None):
        t = textured((S, S), lambda m: pygame.draw.ellipse(m, MASK_W, rect), tex or cf)
        base.blit(t, (0, 0))
        pygame.draw.ellipse(base, shade(col or coat, -55), rect, 2)

    # --- рюкзак/сумка (за спиной)
    if kind == "soldier":
        bp = textured((S, S), lambda m: pygame.draw.rect(m, MASK_W, (4, 28, 24, 40), border_radius=6), make_fabric((60, 70, 50), S))
        base.blit(bp, (0, 0)); pygame.draw.rect(base, (28, 34, 24), (4, 28, 24, 40), 2, border_radius=6)
        for y in (36, 48, 58): pygame.draw.line(base, (40, 48, 34), (6, y), (26, y), 1)
    if kind == "lena":
        pygame.draw.rect(base, (60, 40, 24), (26, 66, 26, 18), border_radius=4)               # сумка на бедре
        pygame.draw.rect(base, (126, 86, 52), (28, 68, 22, 14), border_radius=3)
        pygame.draw.rect(base, (176, 134, 84), (36, 70, 6, 5))
    # --- руки (рукава)
    arm_col = shade(coat, -22)
    if kind == "soldier":
        for sy_, hy in ((18, 42), (78, 54)):
            pygame.draw.line(base, shade(coat, -60), (44, sy_), (66 if hy == 42 else 76, hy), 12)
            pygame.draw.line(base, arm_col, (44, sy_), (66 if hy == 42 else 76, hy), 9)
    elif kind in ("lena", "scientist", "guard"):
        for sd in (-1, 1):
            pygame.draw.line(base, shade(coat, -60), (44, 48 + sd * 26), (66, 48 + sd * 30), 12)
            pygame.draw.line(base, arm_col, (44, 48 + sd * 26), (66, 48 + sd * 30), 9)
            pygame.draw.circle(base, (36, 30, 28) if kind != "scientist" else (200, 150, 128), (67, 48 + sd * 30), 5)
    # --- торс
    body((22, 12, 50, 72))
    # --- детали торса
    if kind == "soldier":                                    # разгрузочный жилет с подсумками и пластиной
        pygame.draw.ellipse(base, (50, 58, 44), (32, 20, 34, 56))
        pygame.draw.ellipse(base, (22, 28, 20), (32, 20, 34, 56), 2)
        for y in (26, 38, 52, 64):
            pygame.draw.rect(base, (36, 42, 32), (50, y, 10, 8), border_radius=2)
            pygame.draw.rect(base, (74, 84, 62), (51, y + 1, 8, 4), border_radius=1)
        pygame.draw.rect(base, (28, 32, 26), (30, 44, 8, 8))
    elif kind == "scientist":
        pygame.draw.line(base, (170, 174, 184), (28, 48), (60, 48), 2)                         # шов спины
        for (x1, y1, x2, y2) in ((30, 24, 44, 28), (30, 74, 44, 70), (36, 36, 48, 40), (36, 62, 48, 58)):
            pygame.draw.line(base, (186, 190, 200), (x1, y1), (x2, y2), 2)                       # складки халата
        pygame.draw.rect(base, (60, 150, 90), (56, 62, 7, 9), border_radius=1)                  # бейдж
        pygame.draw.line(base, (30, 80, 170), (60, 60), (60, 62), 1)
    elif kind == "kessler":
        for sd in (-1, 1):
            pygame.draw.polygon(base, (60, 60, 72), [(60, 48 + sd * 4), (70, 48 + sd * 14), (62, 48 + sd * 17)])   # лацканы
        pygame.draw.rect(base, (200, 28, 36), (54, 66, 8, 5))                                   # платок
        pygame.draw.line(base, (52, 52, 62), (28, 48), (54, 48), 2)
    elif kind == "guard":
        for sd in (-1, 1):
            pygame.draw.rect(base, (170, 150, 70), (54, 48 + sd * 28 - 3, 10, 6), border_radius=1)  # погоны
        pygame.draw.rect(base, (18, 18, 22), (44, 62, 9, 12), border_radius=2)                  # рация
        pygame.draw.line(base, (60, 60, 66), (48, 62), (50, 52), 2)
    elif kind == "lena":
        pygame.draw.line(base, (160, 92, 46), (28, 48), (56, 48), 2)
        pygame.draw.rect(base, (84, 56, 32), (40, 14, 12, 7), border_radius=2)                  # заклёпки/карман
    # --- шарф/воротник
    if kind == "lena":
        pygame.draw.circle(base, (22, 70, 76), (56, 48), 19)
        sc = textured((S, S), lambda m: pygame.draw.circle(m, MASK_W, (56, 48), 17), make_fabric((40, 130, 138), S))
        base.blit(sc, (0, 0))
        for a in range(0, 360, 40):
            pygame.draw.line(base, (24, 90, 96), (56 + math.cos(math.radians(a)) * 9, 48 + math.sin(math.radians(a)) * 9),
                             (56 + math.cos(math.radians(a)) * 17, 48 + math.sin(math.radians(a)) * 17), 1)
    elif kind == "scientist":
        for sd in (-1, 1):
            pygame.draw.polygon(base, (246, 248, 252), [(58, 48 + sd * 3), (66, 48 + sd * 11), (58, 48 + sd * 14)])
            pygame.draw.polygon(base, (150, 154, 166), [(58, 48 + sd * 3), (66, 48 + sd * 11), (58, 48 + sd * 14)], 1)
    elif kind == "kessler":
        pygame.draw.ellipse(base, (240, 240, 244), (54, 38, 16, 20))
    # --- голова
    hx, hy = 58, 48
    if kind == "soldier":
        pygame.draw.circle(base, (20, 26, 18), (hx, hy), 17)
        hm = textured((S, S), lambda m: pygame.draw.circle(m, MASK_W, (hx, hy), 15), cf)
        base.blit(hm, (0, 0))
        for k in range(-3, 4):                                                                  # сетка маскировки
            pygame.draw.line(base, shade(coat, -40), (hx - 12, hy + k * 4), (hx + 12, hy + k * 4), 1)
            pygame.draw.line(base, shade(coat, -40), (hx + k * 4, hy - 12), (hx + k * 4, hy + 12), 1)
        pygame.draw.circle(base, (20, 26, 18), (hx, hy), 15, 2)
        pygame.draw.rect(base, (26, 28, 30), (hx + 11, hy - 6, 7, 12), border_radius=2)       # крепление ПНВ
        pygame.draw.circle(base, (60, 180, 110), (hx + 17, hy), 2)
        pygame.draw.arc(base, (30, 36, 26), (hx - 12, hy - 16, 24, 32), 1.7, 4.6, 2)           # ремешок
    elif kind == "guard":
        pygame.draw.circle(base, (22, 22, 28), (hx, hy), 16)
        pygame.draw.circle(base, (44, 46, 56), (hx, hy), 14)                                    # фуражка
        pygame.draw.circle(base, (170, 150, 70), (hx, hy), 5)
        pygame.draw.polygon(base, (14, 14, 18), [(hx + 8, hy - 11), (hx + 20, hy - 7), (hx + 20, hy + 7), (hx + 8, hy + 11)])   # козырёк
        pygame.draw.circle(base, (22, 22, 28), (hx, hy), 14, 2)
    else:
        pygame.draw.ellipse(base, sk_d, (hx - 6, hy - 18, 9, 10)); pygame.draw.ellipse(base, sk_d, (hx - 6, hy + 8, 9, 10))   # уши
        hair = {"lena": (104, 64, 38), "scientist": (150, 148, 150), "kessler": (156, 156, 164)}[kind]
        pygame.draw.circle(base, shade(hair, -50), (hx, hy), 14)
        ht = textured((S, S), lambda m: pygame.draw.circle(m, MASK_W, (hx, hy), 13), make_fabric(hair, S))
        base.blit(ht, (0, 0))
        if kind == "lena":
            pygame.draw.line(base, shade(hair, -40), (hx - 12, hy), (hx + 8, hy), 1)             # пробор
            pts = [(hx - 12, hy), (hx - 22, hy + 6), (hx - 30, hy + 4), (hx - 36, hy + 12)]     # хвост
            pygame.draw.lines(base, shade(hair, -45), False, pts, 8)
            pygame.draw.lines(base, hair, False, pts, 5)
            pygame.draw.circle(base, (30, 140, 150), (hx - 14, hy + 1), 3)                       # резинка
        elif kind == "kessler":
            for k in range(-3, 4):
                pygame.draw.line(base, (210, 210, 218), (hx - 11, hy + k * 3), (hx + 6, hy + k * 3 + 1), 1)   # зализанные волосы
        elif kind == "scientist":
            for k in range(6):
                a = k * 1.05
                pygame.draw.line(base, (186, 184, 188), (hx, hy), (hx + math.cos(a) * 11, hy + math.sin(a) * 11), 1)
    # --- автомат (поверх рук)
    if kind == "soldier":
        pygame.draw.rect(base, (14, 14, 16), (34, 47, 14, 10), border_radius=2)                 # приклад
        pygame.draw.rect(base, (46, 46, 52), (36, 48, 11, 7), border_radius=2)
        pygame.draw.rect(base, (14, 14, 16), (46, 45, 26, 12), border_radius=2)                 # ствольная коробка и цевьё
        pygame.draw.rect(base, (52, 52, 58), (47, 46, 24, 9), border_radius=2)
        pygame.draw.rect(base, (14, 14, 16), (70, 48, 22, 6))                                    # ствол
        pygame.draw.rect(base, (70, 72, 80), (71, 49, 20, 3))
        pygame.draw.rect(base, (22, 22, 26), (88, 46, 6, 10), border_radius=1)                  # пламегаситель
        pygame.draw.circle(base, (26, 28, 30), (56, 51), 4)                                      # прицел
        pygame.draw.circle(base, (90, 190, 220), (56, 51), 2)
        for hx2, hy2 in ((64, 43), (76, 55)):                                                     # перчатки на рукоятях
            pygame.draw.circle(base, (22, 22, 24), (hx2, hy2), 5)
    light_pass(base, [(34, 30, 26, 60, 1), (54, 38, 16, 50, 1), (50, 74, 24, 46, -1), (70, 56, 14, 28, -1)])
    return outlined(base, (8, 8, 10), 2)

SKIN = (206, 168, 140)

def _part(size, draw):
    s = pygame.Surface(size, pygame.SRCALPHA)
    draw(s)
    return s

def make_side_rig(kind):
    """
    Боковой «скелет» человека для кат-сцен: части запечены в 2x и рисуются повёрнутыми (голова, торс, рукав, штанина с ботинком,
    автомат, рюкзак). kind: mark | lena | soldier. Все части смотрят вправо; для взгляда влево части отражаются.
    """
    rnd = random.Random({"mark": 1, "lena": 2, "soldier": 3}[kind])
    coat = {"mark": (52, 76, 94), "lena": (196, 120, 64), "soldier": (84, 98, 66)}[kind]
    pants = {"mark": (40, 46, 62), "lena": (62, 56, 48), "soldier": (62, 72, 52)}[kind]
    cf = make_fabric(coat, 160)
    pf = make_fabric(pants, 160)
    if kind == "soldier":
        for _ in range(40):
            pygame.draw.ellipse(cf, shade(coat, rnd.choice((-28, -16, 14))), (rnd.randint(0, 140), rnd.randint(0, 140), rnd.randint(8, 22), rnd.randint(6, 14)))
        for _ in range(40):
            pygame.draw.ellipse(pf, shade(pants, rnd.choice((-24, -14, 12))), (rnd.randint(0, 140), rnd.randint(0, 140), rnd.randint(8, 22), rnd.randint(6, 14)))
    rig = {}

    # ---------------- голова 80x84 (центр головы (40,38); шея снизу)
    def head(s):
        pygame.draw.rect(s, (150, 112, 92), (22, 56, 26, 28))                                      # шея
        pygame.draw.rect(s, (24, 18, 16), (22, 56, 26, 28), 1)
        pygame.draw.ellipse(s, (20, 14, 12), (8, 6, 64, 62))
        pygame.draw.ellipse(s, SKIN, (10, 8, 60, 58))
        pygame.draw.polygon(s, SKIN, [(66, 38), (78, 48), (66, 54)])                               # нос
        pygame.draw.lines(s, (150, 112, 92), False, [(66, 38), (78, 48), (66, 54)], 1)
        pygame.draw.ellipse(s, (248, 248, 246), (50, 32, 14, 9))                                   # глаз
        pygame.draw.circle(s, (46, 40, 36), (60, 36), 3)
        pygame.draw.circle(s, (255, 255, 255), (59, 35), 1)
        pygame.draw.line(s, (60, 44, 34), (48, 27), (64, 28), 3)                                   # бровь
        pygame.draw.line(s, (136, 80, 76), (56, 56), (68, 55), 2)                                  # рот
        pygame.draw.ellipse(s, (172, 130, 108), (22, 34, 13, 18))                                  # ухо
        pygame.draw.ellipse(s, (132, 90, 74), (25, 38, 6, 10))
        if kind == "mark":                                                                         # вязаная шапка с отворотом и помпоном
            hat = textured((80, 84), lambda m: pygame.draw.ellipse(m, MASK_W, (8, 0, 62, 40)), make_fabric((150, 48, 44), 80))
            s.blit(hat, (0, 0))
            pygame.draw.ellipse(s, (62, 18, 18), (8, 0, 62, 40), 2)
            pygame.draw.rect(s, (118, 34, 32), (9, 24, 60, 12), border_radius=4)                   # отворот
            pygame.draw.rect(s, (62, 18, 18), (9, 24, 60, 12), 1, border_radius=4)
            for x in range(14, 66, 5):
                pygame.draw.line(s, (96, 28, 28), (x, 4), (x - 2, 24), 1)
                pygame.draw.line(s, (84, 24, 24), (x + 2, 26), (x + 2, 34), 1)
            pygame.draw.circle(s, (214, 196, 188), (38, 2), 6)
            pygame.draw.circle(s, (240, 228, 220), (36, 0), 2)
        elif kind == "soldier":                                                                    # шлем с ремешком и креплением ПНВ
            hm = textured((80, 84), lambda m: pygame.draw.ellipse(m, MASK_W, (4, -4, 70, 46)), cf)
            s.blit(hm, (0, 0))
            pygame.draw.ellipse(s, (20, 26, 18), (4, -4, 70, 46), 2)
            pygame.draw.rect(s, (40, 48, 34), (6, 28, 68, 8), border_radius=3)                     # кромка
            for k in range(4):
                pygame.draw.line(s, shade(coat, -40), (10 + k * 14, 4), (6 + k * 14, 28), 1)
            pygame.draw.rect(s, (24, 26, 28), (60, 8, 12, 16), border_radius=2)                    # ПНВ
            pygame.draw.circle(s, (70, 200, 120), (70, 16), 3)
            pygame.draw.line(s, (30, 36, 26), (34, 38), (44, 64), 2)                               # ремешок
            pygame.draw.line(s, (30, 36, 26), (44, 64), (56, 54), 2)
        else:                                                                                      # Лена: каштановые волосы, чёлка, хвост
            hair = (104, 64, 38)
            hr = textured((80, 84), lambda m: pygame.draw.ellipse(m, MASK_W, (6, 0, 60, 44)), make_fabric(hair, 80))
            s.blit(hr, (0, 0))
            pygame.draw.polygon(s, hair, [(12, 30), (24, 56), (30, 40), (22, 22)])                 # пряди сзади
            pygame.draw.polygon(s, hair, [(46, 6), (70, 18), (66, 30), (52, 22)])                  # чёлка
            pygame.draw.lines(s, shade(hair, 36), False, [(20, 6), (40, 2), (62, 12)], 2)          # блик
            pygame.draw.polygon(s, shade(hair, -30), [(10, 22), (2, 44), (8, 66), (16, 70), (14, 44)])   # хвост
            pygame.draw.polygon(s, hair, [(12, 24), (5, 44), (10, 64), (15, 62), (14, 44)])
            pygame.draw.rect(s, (30, 140, 150), (8, 28, 10, 6), border_radius=2)                   # резинка
    rig["head"] = outlined(_part((80, 84), head), (10, 8, 8), 2)

    # ---------------- торс 76x136
    def torso(s):
        t = textured((76, 136), lambda m: pygame.draw.rect(m, MASK_W, (4, 4, 68, 128), border_radius=18), cf)
        s.blit(t, (0, 0))
        pygame.draw.rect(s, shade(coat, -60), (4, 4, 68, 128), 2, border_radius=18)
        pygame.draw.line(s, shade(coat, -50), (44, 20), (44, 128), 2)                              # молния/планка
        for y in (30, 60, 90):
            pygame.draw.line(s, shade(coat, -40), (42, y), (46, y), 1)
        for (x1, y1, x2, y2) in ((16, 40, 28, 46), (14, 76, 28, 82), (20, 100, 32, 104)):          # складки
            pygame.draw.line(s, shade(coat, -30), (x1, y1), (x2, y2), 2)
        pygame.draw.rect(s, shade(coat, -28), (10, 120, 56, 10), border_radius=3)                  # подол/ремень
        if kind == "mark":
            for y in (28, 108):
                pygame.draw.rect(s, (44, 60, 74), (4, y, 68, 8))                                    # светоотражающие полосы
                pygame.draw.rect(s, (226, 214, 110), (4, y + 2, 68, 2))
                pygame.draw.rect(s, (226, 214, 110), (4, y + 6, 68, 1))
            pygame.draw.rect(s, (36, 52, 66), (46, 60, 20, 24), border_radius=3)                   # карман
            pygame.draw.line(s, (26, 40, 52), (46, 66), (66, 66), 2)
        if kind == "soldier":
            pygame.draw.rect(s, (22, 28, 20), (14, 14, 52, 92), border_radius=10)                  # разгрузка
            pygame.draw.rect(s, (52, 60, 46), (16, 16, 48, 88), border_radius=9)
            for (x, y) in ((20, 70), (36, 70), (52, 70)):
                pygame.draw.rect(s, (30, 36, 26), (x, y, 12, 22), border_radius=2)                  # подсумки
                pygame.draw.rect(s, (84, 94, 70), (x + 1, y + 1, 10, 6), border_radius=1)
            pygame.draw.rect(s, (36, 42, 32), (22, 24, 34, 34), border_radius=3)                    # пластина
            pygame.draw.rect(s, (70, 78, 60), (24, 26, 30, 30), 1, border_radius=3)
        if kind == "lena":
            pygame.draw.ellipse(s, (214, 196, 168), (8, -2, 60, 26))                                # меховой капюшон
            for k in range(14):
                a = k * 0.45
                pygame.draw.line(s, (240, 228, 206), (38 + math.cos(a) * 12, 11 + math.sin(a) * 6), (38 + math.cos(a) * 28, 11 + math.sin(a) * 10), 2)
            pygame.draw.rect(s, (22, 70, 76), (14, 14, 48, 16), border_radius=7)                    # шарф
            pygame.draw.rect(s, (40, 130, 138), (16, 16, 44, 12), border_radius=6)
            pygame.draw.rect(s, (126, 86, 52), (40, 94, 28, 24), border_radius=4)                   # сумка на бедре
            pygame.draw.rect(s, (176, 134, 84), (46, 98, 16, 6))
    rig["torso"] = outlined(_part((76, 136), torso), (10, 8, 8), 2)
    light_pass(rig["torso"], [(24, 36, 40, 54, 1), (62, 110, 34, 46, -1)])

    # ---------------- рукав 28x124 (шарнир сверху по центру)
    def arm(s):
        sl = textured((28, 124), lambda m: pygame.draw.rect(m, MASK_W, (3, 0, 22, 96), border_radius=9), cf)
        s.blit(sl, (0, 0))
        pygame.draw.rect(s, shade(coat, -60), (3, 0, 22, 96), 2, border_radius=9)
        pygame.draw.rect(s, shade(coat, -45), (3, 88, 22, 10), border_radius=3)                    # манжета
        gl = (26, 26, 30) if kind != "lena" else (120, 80, 60)
        pygame.draw.ellipse(s, (10, 10, 12), (2, 94, 24, 28))
        pygame.draw.ellipse(s, gl, (4, 96, 20, 24))
        pygame.draw.line(s, shade(gl, 50), (8, 100), (8, 114), 2)
        pygame.draw.line(s, shade(coat, 28), (7, 8), (7, 84), 1)
    rig["arm"] = outlined(_part((28, 124), arm), (10, 8, 8), 2)

    # ---------------- нога 34x140 (шарнир сверху по центру); ботинок смотрит вправо
    def leg(s):
        pt = textured((34, 140), lambda m: pygame.draw.rect(m, MASK_W, (4, 0, 26, 114), border_radius=8), pf)
        s.blit(pt, (0, 0))
        pygame.draw.rect(s, shade(pants, -55), (4, 0, 26, 114), 2, border_radius=8)
        for y in (40, 70):
            pygame.draw.line(s, shade(pants, -35), (6, y), (28, y + 4), 2)                         # складки на колене
        bt = [(3, 104), (29, 104), (30, 118), (40 - 6, 130), (34, 138), (2, 138)]
        pygame.draw.polygon(s, (10, 10, 12), [(x, y) for x, y in bt])
        pygame.draw.polygon(s, (34, 34, 38) if kind != "lena" else (88, 56, 36), [(x + (2 if x < 10 else -1), y + (2 if y < 120 else -3)) for x, y in bt])
        pygame.draw.rect(s, (16, 16, 18), (2, 134, 32, 6))                                           # подошва
        pygame.draw.line(s, (100, 100, 108), (6, 108), (26, 108), 1)
        for k in range(3):
            pygame.draw.line(s, (170, 170, 176), (10 + k * 5, 112 + k), (14 + k * 5, 115 + k), 1)   # шнуровка
    rig["leg"] = outlined(_part((34, 140), leg), (10, 8, 8), 2)
    light_pass(rig["leg"], [(14, 30, 16, 36, 1)])

    # ---------------- автомат 220x56 (приклад слева, дуло справа)
    if kind == "soldier":
        def rifle(s):
            K, M = (14, 14, 16), (52, 54, 60)
            pygame.draw.polygon(s, K, [(2, 14), (46, 20), (46, 40), (8, 44), (2, 30)])                   # приклад
            pygame.draw.polygon(s, M, [(5, 18), (44, 23), (44, 37), (10, 41), (5, 30)])
            pygame.draw.rect(s, K, (44, 16, 70, 28), border_radius=4)                                    # ствольная коробка
            pygame.draw.rect(s, M, (46, 18, 66, 22), border_radius=3)
            pygame.draw.rect(s, (36, 38, 42), (56, 18, 20, 5))
            pygame.draw.rect(s, K, (66, 4, 30, 14), border_radius=3)                                     # прицел
            pygame.draw.rect(s, (40, 42, 48), (68, 6, 26, 9), border_radius=2)
            pygame.draw.circle(s, (80, 180, 220), (93, 10), 4)
            pygame.draw.rect(s, K, (112, 20, 70, 18), border_radius=3)                                   # цевьё
            pygame.draw.rect(s, M, (114, 22, 66, 12), border_radius=2)
            for x in range(120, 176, 9):
                pygame.draw.line(s, (30, 32, 36), (x, 23), (x, 33), 2)
            pygame.draw.rect(s, K, (180, 25, 34, 8))                                                     # ствол
            pygame.draw.rect(s, (96, 98, 106), (182, 26, 30, 3))
            pygame.draw.rect(s, K, (206, 21, 12, 16), border_radius=2)                                   # пламегаситель
            pygame.draw.polygon(s, K, [(70, 40), (92, 40), (96, 56), (76, 56)])                          # магазин
            pygame.draw.polygon(s, (60, 62, 68), [(73, 41), (90, 41), (92, 54), (78, 54)])
            pygame.draw.line(s, (130, 134, 142), (50, 19), (108, 19), 1)
        rig["rifle"] = outlined(_part((220, 58), rifle), (8, 8, 10), 2)

    # ---------------- рюкзак (вид сбоку) 56x112
    if kind in ("mark", "soldier"):
        def pack(s):
            col = (96, 72, 46) if kind == "mark" else (62, 72, 52)
            t = textured((56, 112), lambda m: pygame.draw.rect(m, MASK_W, (4, 4, 48, 104), border_radius=12), make_fabric(col, 112))
            s.blit(t, (0, 0))
            pygame.draw.rect(s, shade(col, -60), (4, 4, 48, 104), 2, border_radius=12)
            for y in (36, 60, 84):
                pygame.draw.line(s, shade(col, -45), (6, y), (50, y), 2)
            pygame.draw.rect(s, (186, 170, 110), (22, 22, 8, 8))
        rig["pack"] = outlined(_part((56, 112), pack), (10, 8, 8), 2)
        light_pass(rig["pack"], [(18, 30, 24, 40, 1)])
    rig["flip"] = {k: pygame.transform.flip(v, True, False) for k, v in rig.items() if k != "flip"}
    return rig

_SCALED = {}

def _scaled(surf, k):
    """Уменьшенная копия запечённой части (кэш: масштабируем один раз, а не каждый кадр)."""
    key = (id(surf), round(k, 3))
    r = _SCALED.get(key)
    if r is None:
        r = _SCALED[key] = pygame.transform.rotozoom(surf, 0, k)
    return r

def _limb(scr, surf, pivot, ang_deg, k, anchor_y):
    """Конечность на шарнире: surf висит вниз от pivot; ang_deg>0 отводит нижний конец вправо (против часовой)."""
    r = pygame.transform.rotozoom(surf, ang_deg, k)
    L = (surf.get_height() / 2.0 - anchor_y) * k
    a = math.radians(ang_deg)
    c = (pivot[0] + math.sin(a) * L, pivot[1] + math.cos(a) * L)
    scr.blit(r, r.get_rect(center=(int(c[0]), int(c[1]))))

def side_person_rig(scr, rig, x, gy, face, sc=1.0, walk=0.0, aim=None, hands_up=0.0, rifle=False, lean=0.0):
    """Человек сбоку из запечённых частей. face=+1 вправо, -1 влево; aim 0..1 — автомат от опущенного до нацеленного."""
    P = rig if face > 0 else rig["flip"]
    f = face
    k = 0.5 * sc
    hip = (x + lean * 4 * sc, gy - 66 * sc)
    sw = math.sin(walk)
    if "pack" in P:
        pk = _scaled(P["pack"], k)
        scr.blit(pk, pk.get_rect(center=(int(x - f * 24 * sc + lean * 6 * sc), int(gy - 96 * sc))))
    for sd, order in ((-1, 0), (1, 1)):                                                      # ноги: задняя темнее
        ang = math.degrees(math.asin(clamp(sw * 20 * sd / 66.0, -0.9, 0.9))) * f
        _limb(scr, P["leg"], hip, ang, k, 12)
    sh = (x + f * 2 * sc + lean * 8 * sc, gy - 108 * sc)
    if not rifle:                                                                             # дальняя рука — за торсом
        _limb(scr, P["arm"], sh, math.degrees(math.asin(clamp(sw * 14 / 62.0, -0.9, 0.9))) * f, k * 0.92, 10)
    tor = _scaled(P["torso"], k)
    scr.blit(tor, tor.get_rect(center=(int(x + lean * 8 * sc + f * 2 * sc), int(gy - 90 * sc))))
    if rifle:
        a = (1.0 - (aim or 0.0)) * 0.95
        d = (f * math.cos(a), math.sin(a))
        butt = (sh[0] - d[0] * 14 * sc, sh[1] - d[1] * 14 * sc + 6 * sc)
        rf = P["rifle"]
        r = pygame.transform.rotozoom(rf, -math.degrees(a) * f, k)
        mid = (butt[0] + d[0] * 55 * sc, butt[1] + d[1] * 55 * sc)
        scr.blit(r, r.get_rect(center=(int(mid[0]), int(mid[1]))))
        for hnd in ((butt[0] + d[0] * 24 * sc, butt[1] + d[1] * 24 * sc), (butt[0] + d[0] * 64 * sc, butt[1] + d[1] * 64 * sc)):
            dx, dy = hnd[0] - sh[0], hnd[1] - sh[1]
            ang = math.degrees(math.atan2(dx, dy))
            _limb(scr, P["arm"], sh, ang, k * clamp(math.hypot(dx, dy) / (62 * sc), 0.55, 1.2), 10)
    else:
        hu = hands_up
        if hu > 0.05:                                                                         # ближняя рука поднята вперёд
            hand = (sh[0] + f * (8 + 34 * hu) * sc, sh[1] + (48 - 66 * hu) * sc)
            dx, dy = hand[0] - sh[0], hand[1] - sh[1]
            _limb(scr, P["arm"], sh, math.degrees(math.atan2(dx, dy)), k * clamp(math.hypot(dx, dy) / (62 * sc), 0.55, 1.2), 10)
        else:
            _limb(scr, P["arm"], sh, math.degrees(math.asin(clamp(-sw * 14 / 62.0, -0.9, 0.9))) * f, k, 10)
    hd = _scaled(P["head"], k)
    scr.blit(hd, hd.get_rect(center=(int(x + f * 4 * sc + lean * 10 * sc), int(gy - 140 * sc))))


def make_maw_texture():
    """
    Череп чудовища сверху (смотрит вправо, 380x280) для скримера: кожистая кость с венами и пятнами, швы и ветвящиеся трещины,
    надбровья и скулы с объёмом, глубокие глазницы (красные глаза рисуются поверх них), ноздри, рваные раны со швами,
    свет сверху-слева, тени вокруг глазниц, контур. Расположение глазниц и ноздрей не менять: на них опирается draw_jaws.
    """
    W, H = 380, 280
    rnd = random.Random(5)
    bone = make_skin_texture(W, H, (176, 164, 140), veins=26, vein=(112, 30, 44), spots=22, spot=(96, 80, 62))
    base = pygame.Surface((W, H), pygame.SRCALPHA)
    sk = textured((W, H), lambda m: pygame.draw.ellipse(m, MASK_W, (0, 30, W, H - 60)), bone)
    base.blit(sk, (0, 0))

    def crack(x, y, ang, ln, wd):
        """Ветвящаяся трещина: сужается и ветвится."""
        if ln < 8 or wd < 1:
            return
        x2, y2 = x + math.cos(ang) * ln, y + math.sin(ang) * ln
        pygame.draw.line(base, (34, 22, 20), (x, y), (x2, y2), wd)
        pygame.draw.line(base, (214, 200, 172), (x + 1, y - 1), (x2 + 1, y2 - 1), 1)
        crack(x2, y2, ang + rnd.uniform(-0.5, 0.5), ln * 0.72, wd if ln < 24 else wd - 1)
        if rnd.random() < 0.55:
            crack(x2, y2, ang + rnd.choice((-1, 1)) * rnd.uniform(0.6, 1.1), ln * 0.55, max(1, wd - 1))

    # швы черепа: зигзаг вдоль оси и поперёк свода
    sut = [(40 + k * 14, 140 + (6 if k % 2 else -6)) for k in range(12)]
    pygame.draw.lines(base, (52, 38, 32), False, sut, 3)
    pygame.draw.lines(base, (200, 186, 158), False, [(x, y + 2) for x, y in sut], 1)
    sut2 = [(150 + (5 if k % 2 else -5), 56 + k * 14) for k in range(14)]
    pygame.draw.lines(base, (52, 38, 32), False, sut2, 3)
    pygame.draw.lines(base, (200, 186, 158), False, [(x + 2, y) for x, y in sut2], 1)
    for (x, y, a, ln) in ((100, 80, 0.7, 54), (110, 210, -0.6, 50), (210, 130, 3.6, 40), (60, 120, 2.2, 46), (190, 236, -1.9, 36)):
        crack(x, y, a, ln, 3)
    # кожистые складки
    for (cx, cy, rw, rh, a0, a1) in ((120, 100, 60, 34, 3.3, 5.9), (130, 190, 66, 36, 0.4, 2.9), (260, 140, 40, 60, -1.3, 1.3)):
        pygame.draw.arc(base, (96, 76, 62), (cx - rw, cy - rh, rw * 2, rh * 2), a0, a1, 3)
    # рваные раны с мышцей и швами
    for (cx, cy, rw, rh) in ((80, 84, 34, 22), (92, 200, 28, 18)):
        pygame.draw.polygon(base, (58, 12, 16), jag_poly(cx, cy, rw + 5, rh + 5, 14, 0.2, rnd))
        pygame.draw.polygon(base, (136, 28, 34), jag_poly(cx, cy, rw, rh, 12, 0.1, rnd))
        for k in range(-rw + 4, rw - 3, 5):
            pygame.draw.line(base, (88, 14, 22), (cx + k, cy - rh + 4), (cx + k + 2, cy + rh - 4), 2)
            pygame.draw.line(base, (176, 60, 64), (cx + k + 1, cy - rh + 5), (cx + k + 3, cy + rh - 6), 1)
        for k in range(-rw + 6, rw - 4, 9):
            pygame.draw.line(base, (20, 14, 12), (cx + k, cy - rh - 3), (cx + k + 2, cy + rh + 3), 2)       # швы
        pygame.draw.ellipse(base, (248, 196, 188), (cx - rw // 2, cy - rh // 2, 10, 5))                     # влажный блик
    # надбровья и скулы: толстые дуги с тенью и бликом
    for yy, sgn in ((88, 1), (192, -1)):
        pygame.draw.arc(base, (60, 44, 36), (214, yy - 40, 118, 62), 0.2 if sgn > 0 else -2.9, 2.9 if sgn > 0 else -0.2, 7)
        pygame.draw.arc(base, (222, 208, 180), (216, yy - 38, 114, 58), 0.3 if sgn > 0 else -2.8, 2.8 if sgn > 0 else -0.3, 3)
    # глазницы (положение и размер сохраняются!)
    for yy in (88, 192):
        pygame.draw.ellipse(base, (52, 30, 26), (234, yy - 29, 82, 58))                                     # скос кости вокруг
        pygame.draw.ellipse(base, (6, 0, 0), (240, yy - 24, 70, 48))
        pygame.draw.ellipse(base, (96, 12, 16), (240, yy - 24, 70, 48), 3)
        pygame.draw.arc(base, (226, 212, 186), (236, yy - 28, 78, 56), 3.4, 5.4, 2)                          # блик на кромке
        pygame.draw.arc(base, (30, 8, 8), (244, yy - 20, 62, 40), 0.3, 2.9, 3)
    # носовая кость и ноздри
    pygame.draw.polygon(base, (40, 28, 24), [(300, 130), (356, 136), (356, 144), (300, 150)])
    pygame.draw.polygon(base, (214, 200, 172), [(300, 133), (352, 138), (352, 141), (300, 146)])
    for yy in (126, 154):
        pygame.draw.line(base, (10, 4, 4), (350, yy), (372, 140), 5)
        pygame.draw.line(base, (120, 40, 40), (350, yy + (2 if yy < 140 else -2)), (368, 140), 1)
    pygame.draw.ellipse(base, (22, 12, 10), (0, 30, W, H - 60), 4)
    clip = pygame.Surface((W, H), pygame.SRCALPHA)                      # всё, что вылезло за силуэт черепа (трещины, швы), срезается
    pygame.draw.ellipse(clip, (255, 255, 255, 255), (0, 30, W, H - 60))
    base.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    light_pass(base, [(120, 80, 96, 66, 1), (200, 126, 50, 40, 1), (110, 200, 52, 30, 1),
                      (275, 88, 54, 70, -1), (275, 192, 54, 70, -1), (330, 230, 80, 50, -1), (60, 230, 70, 44, -1), (350, 140, 30, 40, -1)])
    return outlined(base, (14, 8, 8), 4)


def radial_surface(radius, power):
    """Круглый градиент света (значение пишется во все 4 канала — для BLEND_SUB)."""
    size = int(radius * 2) + 2
    c = size // 2
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    steps = max(6, int(radius / 2.5))
    for i in range(steps):
        r = radius * (1 - i / steps)
        v = int(255 * ((i + 1) / steps) ** power)
        pygame.draw.circle(s, (v, v, v, v), (c, c), max(1, int(r)))
    return s


# ------------------------------------------------------------------ ЗВУК
class SoundBank:
    """Синтез: превращает формулы в звуки. Ничего не воспроизводит и не знает про микшер игры."""

    def __init__(self, rate, channels, progress=None):
        self.rate = rate
        self.ch = channels
        self.sounds = {}
        tau = 2 * math.pi
        tau = 2 * math.pi
        self.sounds["drone"] = self.make(3.0, lambda t: 0.5 * math.sin(tau * 48 * t)
                                    + 0.3 * math.sin(tau * 72 * t + 2 * math.sin(tau * t / 3))
                                    + 0.12 * math.sin(tau * 96 * t) * (0.5 + 0.5 * math.sin(tau * t / 3))
                                    + random.uniform(-0.03, 0.03), 0.5)
        self.sounds["heart"] = self.make(0.6, lambda t: math.sin(tau * 55 * t) * math.exp(-t * 22)
                                    + (0.8 * math.sin(tau * 48 * (t - 0.2)) * math.exp(-(t - 0.2) * 26)
                                       if t > 0.2 else 0), 0.9)
        self.sounds["pickup"] = self.make(0.25, lambda t: (math.sin(tau * 880 * t) + 0.5 * math.sin(tau * 1320 * t))
                                     * math.exp(-t * 14), 0.35)
        self.sounds["key"] = self.make(0.7, lambda t: sum(math.sin(tau * f * t) * math.exp(-(t - d) * 6)
                                                     for f, d in ((660, 0), (880, 0.12), (1320, 0.24)) if t >= d),
                                  0.3)
        self.sounds["click"] = self.make(0.05, lambda t: random.uniform(-1, 1) * math.exp(-t * 90), 0.4)
        self.sounds["scare"] = self.make(2.6, lambda t: (
            0.55 * math.sin(tau * (1500 * t + 260 * math.sin(tau * 7.3 * t))) * min(1.0, t * 40)
            + 0.40 * math.sin(tau * (2650 * t + 420 * math.sin(tau * 11 * t)))
            + 0.55 * random.uniform(-1, 1) * math.exp(-max(0.0, t - 0.1) * 1.2)
            + 1.00 * math.sin(tau * 36 * t) * math.exp(-t * 3.0))
            * min(1.0, t * 60) * math.exp(-max(0.0, t - 1.7) * 3.0), 0.95, echo=((0.10, 0.28), (0.24, 0.16)))
        # --- атмосфера и интерфейс
        self.sounds["whisper"] = self.make(2.4, lambda t: (random.uniform(-1, 1) * (0.5 + 0.5 * math.sin(tau * 6.5 * t))
                                                           * (0.4 + 0.6 * abs(math.sin(tau * 1.1 * t))) * 0.55
                                                           + 0.12 * math.sin(tau * (310 + 40 * math.sin(tau * 3 * t)) * t))
                                           * math.sin(math.pi * t / 2.4), 0.55)
        self.sounds["bang"] = self.make(1.2, lambda t: math.sin(tau * 130 * t) * math.exp(-t * 7)
                                        + 0.7 * math.sin(tau * 410 * t) * math.exp(-t * 11)
                                        + random.uniform(-1, 1) * 0.4 * math.exp(-t * 20), 0.8, echo=((0.10, 0.35), (0.23, 0.20)))
        self.sounds["scratch"] = self.make(1.6, lambda t: random.uniform(-1, 1) * (0.5 + 0.5 * math.sin(tau * 14 * t))
                                           * abs(math.sin(tau * 2.2 * t)) * math.sin(math.pi * t / 1.6), 0.45)
        self.sounds["breath"] = self.make(1.9, lambda t: (random.uniform(-1, 1) * (0.6 + 0.4 * math.sin(tau * 5 * t))
                                                          + 0.35 * math.sin(tau * 62 * t)) * math.sin(math.pi * t / 1.9) ** 2, 0.6)
        self.sounds["ding"] = self.make(1.4, lambda t: (math.sin(tau * 988 * t) + 0.5 * math.sin(tau * 1976 * t))
                                        * math.exp(-t * 3.2), 0.4, echo=((0.17, 0.35), (0.34, 0.20)))
        self.sounds["door"] = self.make(1.2, lambda t: (random.uniform(-1, 1) * 0.5 * (0.5 + 0.5 * math.sin(tau * 28 * t))
                                                        + 0.4 * math.sin(tau * (90 + 60 * t) * t)) * math.sin(math.pi * t / 1.2), 0.55, echo=((0.10, 0.25), (0.22, 0.15)))
        self.sounds["rustle"] = self.make(0.5, lambda t: random.uniform(-1, 1) * math.sin(math.pi * t / 0.5)
                                          * (0.5 + 0.5 * math.sin(tau * 40 * t)), 0.4)
        self.sounds["beep"] = self.make(0.35, lambda t: math.sin(tau * 1760 * t) * (1.0 if (t * 12) % 2 < 1 else 0.0), 0.3)
        self.sounds["whoosh"] = self.make(0.45, lambda t: random.uniform(-1, 1) * math.sin(math.pi * t / 0.45) ** 1.5, 0.45)
        self.sounds["swipe"] = self.make(0.5, lambda t: (random.uniform(-1, 1) * (0.4 + 1.2 * t)
                                                         + 0.4 * math.sin(tau * (300 + 900 * t) * t)) * math.sin(math.pi * t / 0.5), 0.55)
        self.sounds["step2"] = self.make(0.12, lambda t: (math.sin(tau * 95 * t) * 0.8 + random.uniform(-1, 1) * 0.3)
                                         * math.exp(-t * 34), 0.5)
        self.sounds["roar"] = self.make(2.2, lambda t: ((((t * 52) % 1.0) * 2 - 1) * 0.5 * (0.7 + 0.3 * math.sin(tau * 11 * t))
                                                        + math.sin(tau * (180 + 60 * math.sin(tau * 5 * t)) * t) * 0.35
                                                        + random.uniform(-1, 1) * 0.35)
                                        * min(1.0, t * 12) * math.exp(-max(0.0, t - 1.2) * 2.2), 0.9, echo=((0.12, 0.30), (0.27, 0.18)))
        self.sounds["hum"] = self.make(2.0, lambda t: math.sin(tau * 55 * t) * 0.5
                                       + math.sin(tau * 110 * t + 1.3 * math.sin(tau * 2 * t)) * 0.3
                                       + random.uniform(-1, 1) * 0.05, 0.35)
        self.sounds["shriek"] = self.make(1.3, lambda t: (math.sin(tau * (3400 + 500 * math.sin(tau * 19 * t)) * t) * 0.55
                                                          + math.sin(tau * 5200 * t) * math.sin(tau * 230 * t) * 0.4
                                                          + random.uniform(-1, 1) * 0.35)
                                          * min(1.0, t * 80) * math.exp(-max(0.0, t - 0.5) * 2.5), 0.7, echo=((0.09, 0.30), (0.20, 0.18)))
        self.sounds["sub"] = self.make(1.0, lambda t: math.sin(tau * (60 - 25 * t) * t) * math.exp(-t * 2.5), 1.0)
        # музыка боя: пульсирующий бас + диссонанс (233 и 247 Гц) + тихие «хэты»; ровно 4 с — зацикливается без щелчка
        self.sounds["boss_music"] = self.make(4.0, lambda t: 0.55 * math.sin(tau * 55 * t)
                                              * (0.35 + 0.65 * math.exp(-((t * 4) % 1.0) * 4))
                                              + 0.22 * math.sin(tau * 233 * t) * math.sin(tau * 0.25 * t) ** 2
                                              + 0.20 * math.sin(tau * 247 * t) * math.sin(tau * 0.25 * t + 1.0) ** 2
                                              + 0.25 * random.uniform(-1, 1) * (min(1.0, ((t * 8) % 1.0) * 40) if (t * 8) % 1.0 < 0.08 else 0.0), 0.5)
        # ================== САУНДТРЕК: зацикленные дорожки (длины подобраны так, чтобы петля не щёлкала) ==================
        if progress:
            progress("ЗАГРУЗКА...  музыка")
        mel = (440.0, 523.25, 659.25, 523.25, 783.99, 659.25, 523.25, 440.0)

        def music_menu(t):                       # главная тема: тёмный пэд и музыкальная шкатулка
            pad = (0.30 * math.sin(tau * 55 * t) + 0.22 * math.sin(tau * 82.5 * t + 0.8 * math.sin(tau * 0.125 * t))
                   + 0.12 * math.sin(tau * 110 * t)) * (0.7 + 0.3 * math.sin(tau * 0.25 * t))
            ph = t % 1.0
            f = mel[int(t) % 8]
            bell = (math.sin(tau * f * ph) + 0.35 * math.sin(tau * 2 * f * ph)) * math.exp(-ph * 3.2) * 0.22
            return pad + bell

        def music_floor0(t):                     # этаж -3: лаборатория — гул, далёкий колокол, глухие удары
            drone = 0.32 * math.sin(tau * 49 * t) + 0.20 * math.sin(tau * 73.5 * t + math.sin(tau * 0.25 * t))
            swell = random.uniform(-1, 1) * 0.10 * math.sin(math.pi * t / 4.0) ** 2
            ph = t % 4.0
            bell = math.sin(tau * 880 * ph) * math.exp(-ph * 2.2) * 0.12 * (1.0 if int(t / 4) % 2 == 0 else 0.6)
            q = t % 2.0
            return drone + swell + bell + math.sin(tau * 46 * q) * math.exp(-q * 9) * 0.35

        def music_floor1(t):                     # этаж -2: тритон, скрежет металла, пульс
            pad = (0.28 * math.sin(tau * 55 * t) + 0.22 * math.sin(tau * 77.5 * t + 0.6 * math.sin(tau * 0.5 * t))
                   + 0.10 * math.sin(tau * 165 * t) * math.sin(tau * 0.125 * t) ** 2)
            ph = t % 2.0
            scrape = random.uniform(-1, 1) * 0.16 * math.exp(-ph * 5) * (1.0 if math.sin(tau * 90 * ph) > 0 else 0.0)
            q = t % 1.0
            return pad + scrape + 0.3 * math.sin(tau * 40 * q) * math.exp(-q * 6)

        def music_floor2(t):                     # этаж -1: кластер полутонов, тиканье часов, низкий гул
            cl = 0.16 * (math.sin(tau * 110 * t) + math.sin(tau * 116.5 * t) + math.sin(tau * 123.5 * t)) \
                * (0.6 + 0.4 * math.sin(tau * 0.25 * t))
            q = t % 0.5
            low = 0.3 * math.sin(tau * 36.5 * t) * (0.5 + 0.5 * math.sin(tau * 0.125 * t))
            return cl + math.sin(tau * 1200 * q) * math.exp(-q * 60) * 0.10 + low

        def music_tension(t):                    # слой напряжения: дрожащие высокие струны + удары сердца
            tr = 0.5 + 0.5 * math.sin(tau * 6 * t)
            hi = (0.18 * math.sin(tau * 880 * t) + 0.16 * math.sin(tau * 932 * t)
                  + 0.10 * math.sin(tau * 1244.5 * t)) * tr * (0.6 + 0.4 * math.sin(tau * 0.25 * t))
            q = t % 0.5
            return hi + 0.30 * math.sin(tau * 45 * q) * math.exp(-q * 7)

        bass = (55.0, 55.0, 65.4, 55.0, 49.0, 55.0, 73.4, 65.4)

        def music_chase(t):                      # погоня: 120 BPM — бочка, малый, хэт, бас-остинато, диссонансные аккорды
            kp = t % 0.5
            kick = math.sin(tau * (50 + 110 * math.exp(-kp * 30)) * kp) * math.exp(-kp * 10) * 0.55
            sp = (t + 0.5) % 1.0
            snare = random.uniform(-1, 1) * math.exp(-sp * 14) * 0.35
            hp = t % 0.25
            hat = random.uniform(-1, 1) * math.exp(-hp * 60) * 0.16 * min(1.0, hp * 500)     # короткая атака: без щелчка на стыке петли
            bp = t % 0.25
            bs = math.sin(tau * bass[int(t / 0.25) % 8] * bp) * math.exp(-bp * 8) * 0.40
            st = t % 2.0
            stab = 0.16 * (math.sin(tau * 233 * st) + math.sin(tau * 247 * st)) * math.exp(-st * 5)
            return kick + snare + hat + bs + stab

        def music_finale(t):                     # финал: хоровой пэд с вибрато и колокол
            vib = 1 + 0.01 * math.sin(tau * 5 * t)
            pad = (0.22 * math.sin(tau * 55 * t * vib) + 0.18 * math.sin(tau * 82.5 * t * vib)
                   + 0.14 * math.sin(tau * 110 * t) + 0.10 * math.sin(tau * 165 * t)) \
                * (0.55 + 0.45 * math.sin(tau * 0.125 * t - 1.0))
            bp = t % 4.0
            return pad + (math.sin(tau * 392 * bp) + 0.5 * math.sin(tau * 784 * bp)) * math.exp(-bp * 1.6) * 0.20

        win_notes = (220.0, 277.18, 329.63, 440.0, 554.37, 659.25, 880.0, 659.25, 554.37, 440.0)

        def music_win(t):                        # победа: светлое арпеджио над тёплым пэдом (играет один раз)
            ph = t % 1.0
            f = win_notes[int(t) % 10]
            arp = (math.sin(tau * f * ph) + 0.4 * math.sin(tau * 2 * f * ph)) * math.exp(-ph * 2.4) * 0.28
            pad = (0.16 * math.sin(tau * 110 * t) + 0.12 * math.sin(tau * 138.6 * t)
                   + 0.10 * math.sin(tau * 164.8 * t)) * math.sin(math.pi * t / 10) ** 0.5
            return (arp + pad) * min(1.0, (10 - t) / 2.0)

        def music_lose(t):                       # поражение: опускающийся минорный пэд и тусклый колокол (один раз)
            f = 98.0 - 6.0 * t
            pad = (math.sin(tau * f * t) * 0.35 + math.sin(tau * f * 1.0595 * t) * 0.25) * min(1.0, t * 2) * min(1.0, (6 - t) / 2.0)
            q = t % 3.0
            return pad + math.sin(tau * 329.63 * q) * math.exp(-q * 1.5) * 0.18

        for name, dur, fn, vol in (("mus_menu", 8.0, music_menu, 0.7), ("mus_floor0", 8.0, music_floor0, 0.7),
                                   ("mus_floor1", 8.0, music_floor1, 0.7), ("mus_floor2", 8.0, music_floor2, 0.7),
                                   ("mus_tension", 4.0, music_tension, 0.7), ("mus_chase", 4.0, music_chase, 0.75),
                                   ("mus_finale", 8.0, music_finale, 0.7), ("mus_win", 10.0, music_win, 0.75),
                                   ("mus_lose", 6.0, music_lose, 0.7)):
            self.sounds[name] = self.make_music(dur, fn, vol)
        # ================== НОВЫЕ ТРЕКИ: пещера, реактор, аванпост, склады, эвакуация, финалы ==================
        def music_floor3(t):                     # -10: пещера — низкие дроны, хор, редкие капли
            drone = 0.30 * math.sin(tau * 41 * t) + 0.22 * math.sin(tau * 61.5 * t + 0.8 * math.sin(tau * 0.25 * t))
            choir = 0.07 * (math.sin(tau * 220 * t) + math.sin(tau * 277.5 * t) + math.sin(tau * 330 * t)) \
                * (0.5 + 0.5 * math.sin(tau * 0.125 * t - 1.2)) ** 2
            q = t % 2.0
            return drone + choir + math.sin(tau * (1500 - 700 * q) * q) * math.exp(-q * 28) * 0.16

        def music_floor4(t):                     # -8: реактор — тяжёлый пульс, шипение пара, удары металла
            q = t % 1.0
            hp = t % 2.0
            cp = t % 4.0
            return (math.sin(tau * 36 * q) * math.exp(-q * 5) * 0.5
                    + 0.18 * math.sin(tau * 55 * t) * (0.6 + 0.4 * math.sin(tau * 0.25 * t)) + 0.10 * math.sin(tau * 110.5 * t)
                    + random.uniform(-1, 1) * math.exp(-hp * 3.0) * 0.12 * (1.0 if hp < 1.2 else 0.0)
                    + (math.sin(tau * 312 * cp) + 0.6 * math.sin(tau * 541 * cp)) * math.exp(-cp * 5) * 0.14)

        arp5 = (220.0, 262.0, 330.0, 262.0, 196.0, 247.0, 294.0, 247.0)

        def music_outpost(t):                    # -6: аванпост — холодное арпеджио, пад, редкие писки рации
            ph = t % 0.5
            f = arp5[int(t / 0.5) % 8]
            pluck = (math.sin(tau * f * ph) + 0.3 * math.sin(tau * 2 * f * ph)) * math.exp(-ph * 7) * 0.22
            pad = (0.16 * math.sin(tau * 55 * t) + 0.12 * math.sin(tau * 82.5 * t + 0.6 * math.sin(tau * 0.125 * t))
                   + 0.08 * math.sin(tau * 131 * t)) * (0.7 + 0.3 * math.sin(tau * 0.25 * t))
            q = t % 4.0
            return pluck + pad + math.sin(tau * 1500 * q) * 0.10 * (1.0 if (q < 0.06 or 0.22 < q < 0.28) else 0.0)

        def music_floor5(t):                     # -4: склады — тиканье, сквозняк, звон металла
            q = t % 1.0
            cp = t % 4.0
            return (math.sin(tau * 900 * q) * math.exp(-q * 70) * 0.12 * (1.0 if int(t) % 2 == 0 else 0.6)
                    + 0.30 * math.sin(tau * 36.5 * t) * (0.5 + 0.5 * math.sin(tau * 0.125 * t))
                    + random.uniform(-1, 1) * 0.06 * (0.5 + 0.5 * math.sin(tau * 0.25 * t + 1.0)) ** 2
                    + math.sin(tau * 1175 * cp) * math.exp(-cp * 2.2) * 0.12 + math.sin(tau * 1760 * cp) * math.exp(-cp * 3) * 0.06)

        bass_ev = (55.0, 55.0, 49.0, 58.3)

        def music_evac(t):                       # эвакуация: быстрый ритм, бас-ход, сирена
            kp = t % 0.5
            hp = t % 0.25
            sp = (t + 0.5) % 1.0
            bp = t % 0.25
            return (math.sin(tau * (45 + 120 * math.exp(-kp * 35)) * kp) * math.exp(-kp * 9) * 0.6
                    + random.uniform(-1, 1) * math.exp(-hp * 55) * 0.14 * min(1.0, hp * 500) + random.uniform(-1, 1) * math.exp(-sp * 13) * 0.3 * min(1.0, sp * 500)
                    + math.sin(tau * bass_ev[int(t) % 4] * bp) * math.exp(-bp * 6) * 0.38
                    + 0.10 * math.sin(tau * 520 * t + 140 * math.sin(tau * 0.5 * t)))

        def music_win_dark(t):                   # концовки «Тишина» и «Новая плоть»: минорный пад и колокол
            q = t % 2.0
            pad = (0.20 * math.sin(tau * 55 * t) + 0.16 * math.sin(tau * 65.5 * t + 0.4 * math.sin(tau * 0.125 * t))
                   + 0.10 * math.sin(tau * 131 * t)) * math.sin(math.pi * t / 8.0) ** 0.5
            return (pad + (math.sin(tau * 220 * q) + 0.5 * math.sin(tau * 330.5 * q)) * math.exp(-q * 1.4) * 0.18) * min(1.0, (8.0 - t) / 2.0)

        warm = (220.0, 277.2, 329.6, 440.0, 554.4, 440.0, 329.6, 277.2, 220.0, 329.6)

        def music_win_warm(t):                   # «Искупление», «Все живы», «Эвакуация»: тёплое мажорное арпеджио
            ph = t % 1.0
            f = warm[int(t) % 10]
            arp = (math.sin(tau * f * ph) + 0.5 * math.sin(tau * 2 * f * ph) + 0.2 * math.sin(tau * 3 * f * ph)) * math.exp(-ph * 2.0) * 0.26
            pad = (0.17 * math.sin(tau * 110 * t) + 0.13 * math.sin(tau * 138.6 * t) + 0.11 * math.sin(tau * 165 * t)
                   + 0.07 * math.sin(tau * 220 * t)) * math.sin(math.pi * t / 10.0) ** 0.5
            return (arp + pad) * min(1.0, (10.0 - t) / 2.0)

        brass = (196.0, 196.0, 261.6, 329.6, 392.0, 392.0, 329.6, 392.0)

        def music_win_blast(t):                  # «Взрывной побег»: фанфары и литавры
            ph = t % 1.0
            kp = t % 2.0
            f = brass[int(t) % 8]
            horn = (((f * ph) % 1.0 * 2 - 1) * 0.5 + math.sin(tau * f * ph) * 0.5) * 0.28 * min(1.0, ph * 12) * math.exp(-ph * 1.1)
            return (horn + math.sin(tau * (70 - 25 * kp) * kp) * math.exp(-kp * 3.0) * 0.5) * min(1.0, (8.0 - t) / 1.5)

        for name, dur, fn, vol in (("mus_floor3", 8.0, music_floor3, 0.7), ("mus_floor4", 8.0, music_floor4, 0.7),
                                   ("mus_outpost", 8.0, music_outpost, 0.7), ("mus_floor5", 8.0, music_floor5, 0.7),
                                   ("mus_evac", 4.0, music_evac, 0.75), ("mus_win_dark", 8.0, music_win_dark, 0.7),
                                   ("mus_win_warm", 10.0, music_win_warm, 0.75), ("mus_win_blast", 8.0, music_win_blast, 0.75)):
            self.sounds[name] = self.make_music(dur, fn, vol)

        # --- фоновая «комнатная» атмосфера каждого типа этажа (6 секунд, считается через 3 отсчёта)
        def amb_lab(t):                          # лаборатория: гул ламп и вентиляции
            return (0.12 * math.sin(tau * 50 * t) + 0.05 * math.sin(tau * 100 * t)
                    + 0.03 * math.sin(tau * 120 * t) * (0.6 + 0.4 * math.sin(tau * t / 2.0))
                    + random.uniform(-1, 1) * 0.035 * (0.5 + 0.5 * math.sin(tau * t / 6.0)))

        def amb_shaft(t):                        # шахта: ветер и капли
            q = t % 3.0
            return (random.uniform(-1, 1) * 0.07 * (0.5 + 0.5 * math.sin(tau * t / 6.0 + 0.5)) ** 2
                    + 0.06 * math.sin(tau * 42 * t) * (0.5 + 0.5 * math.sin(tau * t / 3.0))
                    + math.sin(tau * (1300 - 500 * q) * q) * math.exp(-q * 30) * 0.10)

        def amb_reactor(t):                      # реактор: низкий гул и шипение пара
            q = t % 3.0
            return (0.20 * math.sin(tau * 28 * t) + 0.10 * math.sin(tau * 56.5 * t)
                    + random.uniform(-1, 1) * 0.07 * math.exp(-q * 2.0) * (1.0 if q < 1.5 else 0.4))

        def amb_outpost(t):                      # аванпост: генератор и обрывки радио
            gate = 1.0 if int(t * 7) % 5 < 2 else 0.0
            return (0.10 * math.sin(tau * 60 * t) + 0.04 * math.sin(tau * 180 * t)
                    + random.uniform(-1, 1) * 0.05 * gate * (0.5 + 0.5 * math.sin(tau * 3 * t)))

        def amb_warehouse(t):                    # склады: сквозняк и скрип стеллажей
            q = t % 3.0
            return (random.uniform(-1, 1) * 0.04 * (0.5 + 0.5 * math.sin(tau * t / 6.0)) + 0.06 * math.sin(tau * 33 * t)
                    + math.sin(tau * (180 - 50 * q) * q + 3 * math.sin(tau * 8 * q)) * math.sin(math.pi * q / 3.0) ** 3 * 0.08)

        for name, fn in (("amb_lab", amb_lab), ("amb_shaft", amb_shaft), ("amb_reactor", amb_reactor),
                         ("amb_outpost", amb_outpost), ("amb_warehouse", amb_warehouse)):
            self.sounds[name] = self.make_music(6.0, fn, 0.8, True, 3)

        # --- новые эффекты
        self.sounds["rotor"] = self.make(1.0, lambda t: (random.uniform(-1, 1) * 0.35 + math.sin(tau * 70 * t) * 0.5
                                                         + math.sin(tau * 140 * t) * 0.2) * (0.45 + 0.55 * abs(math.sin(math.pi * 11 * t))), 0.55)
        self.sounds["gulp"] = self.make(0.7, lambda t: math.sin(tau * (160 - 100 * t) * t) * math.exp(-t * 5)
                                        + (0.6 * math.sin(tau * (180 - 110 * (t - 0.3)) * (t - 0.3)) * math.exp(-(t - 0.3) * 9) if t > 0.3 else 0.0), 0.8)
        self.sounds["transform"] = self.make(2.6, lambda t: (((t * 38) % 1.0) * 2 - 1) * 0.35 * min(1.0, t * 3) * (0.6 + 0.4 * math.sin(tau * 9 * t))
                                             + math.sin(tau * (200 + 900 * t / 2.6) * t) * 0.35 * min(1.0, t)
                                             + random.uniform(-1, 1) * 0.4 * abs(math.sin(tau * 13 * t)), 0.9)
        self.sounds["keypad"] = self.make(0.14, lambda t: math.sin(tau * 1320 * t) * math.exp(-t * 28) * 0.7
                                          + (math.sin(tau * 1760 * t) * math.exp(-t * 26) * 0.5 if t > 0.06 else 0.0), 0.5)
        self.sounds["console_on"] = self.make(0.8, lambda t: sum(math.sin(tau * f * t) * math.exp(-(t - d) * 14)
                                                                 for f, d in ((880, 0.0), (1175, 0.12), (1480, 0.24), (1760, 0.4)) if t >= d) * 0.4, 0.5)
        self.sounds["step_metal"] = self.make(0.14, lambda t: (math.sin(tau * 160 * t) * 0.5 + math.sin(tau * 2200 * t) * 0.35 * math.exp(-t * 60)
                                                               + random.uniform(-1, 1) * 0.25) * math.exp(-t * 30), 0.55,
                                              echo=((0.05, 0.3), (0.11, 0.15)))
        self.sounds["step_metal2"] = self.make(0.14, lambda t: (math.sin(tau * 120 * t) * 0.5 + math.sin(tau * 1800 * t) * 0.35 * math.exp(-t * 55)
                                                                + random.uniform(-1, 1) * 0.25) * math.exp(-t * 28), 0.55,
                                               echo=((0.06, 0.3), (0.12, 0.15)))
        self.sounds["crunch"] = self.make(1.1, lambda t: math.sin(tau * 62 * t) * math.exp(-t * 9)
                                          + random.uniform(-1, 1) * (math.exp(-t * 18) + 0.8 * math.exp(-abs(t - 0.16) * 30)
                                                                     + 0.6 * math.exp(-abs(t - 0.32) * 30)), 0.95)
        self.sounds["squelch"] = self.make(1.6, lambda t: (random.uniform(-1, 1) * (0.5 + 0.5 * math.sin(tau * 9 * t)) ** 2 * 0.8
                                                           + 0.3 * math.sin(tau * 48 * t)) * math.sin(math.pi * t / 1.6), 0.6)
        self.sounds["rip"] = self.make(1.0, lambda t: random.uniform(-1, 1) * (0.35 + 0.65 * abs(math.sin(tau * (16 + 34 * t) * t)))
                                       * math.exp(-t * 2.6) + math.sin(tau * 52 * t) * math.exp(-t * 5)
                                       + (random.uniform(-1, 1) * 0.9 if int(t * 50) % 7 == 0 and t < 0.5 else 0.0), 0.95)
        self.sounds["flatline"] = self.make(2.2, lambda t: math.sin(tau * 880 * t) * 0.45 * min(1.0, t * 30)
                                            * min(1.0, (2.2 - t) / 0.5), 0.5)
        self.sounds["sting"] = self.make(0.9, lambda t: (math.sin(tau * 2093 * t) + math.sin(tau * 2217 * t)
                                                         + 0.5 * random.uniform(-1, 1)) * math.exp(-t * 4.5) * 0.5
                                         + math.sin(tau * 50 * t) * math.exp(-t * 6), 0.7, echo=((0.13, 0.30), (0.28, 0.16)))
        self.sounds["static"] = self.make(0.3, lambda t: random.uniform(-1, 1) * math.exp(-t * 9), 0.5)
        self.sounds["pounce"] = self.make(0.95, lambda t: (math.sin(tau * (700 + 2600 * t) * t) * 0.5
                                                         + math.sin(tau * 90 * t) * math.sin(tau * (1500 + 900 * math.sin(tau * 30 * t)) * t) * 0.5
                                                         + random.uniform(-1, 1) * 0.55)
                                          * min(1.0, t * 25) * max(0.0, min(1.0, (0.95 - t) / 0.25)), 0.9, echo=((0.08, 0.30), (0.19, 0.18)))
        self.sounds["radio"] = self.make(0.5, lambda t: random.uniform(-1, 1) * 0.5 * math.exp(-t * 4)
                                         + (math.sin(tau * 1400 * t) * 0.4 if t < 0.07 else 0.0), 0.45)
        self.sounds["reload"] = self.make(0.45, lambda t: math.sin(tau * 2100 * t) * math.exp(-t * 70)
                                          + (math.sin(tau * 1300 * (t - 0.2)) * math.exp(-(t - 0.2) * 55) if t > 0.2 else 0.0)
                                          + random.uniform(-1, 1) * 0.15 * math.exp(-t * 30), 0.6)
        self.sounds["parry"] = self.make(0.55, lambda t: (math.sin(tau * 1650 * t) + 0.6 * math.sin(tau * 2490 * t)
                                                          + random.uniform(-1, 1) * 0.3) * math.exp(-t * 11), 0.7)
        self.sounds["hit"] = self.make(0.3, lambda t: (math.sin(tau * 85 * t) + random.uniform(-1, 1) * 0.5)
                                       * math.exp(-t * 16), 0.9)
        self.sounds["dread"] = self.make(0.6, lambda t: math.sin(tau * (38 + 90 * t) * t) * (0.4 + t / 0.6)
                                         + 0.2 * math.sin(tau * 5 * t), 0.7)
        self.sounds["growl"] = self.make(0.9, lambda t: (((t * 70) % 1.0) * 2 - 1) * 0.5
                                    * (0.6 + 0.4 * math.sin(tau * 14 * t)) * math.exp(-t * 2.2)
                                    + random.uniform(-0.2, 0.2) * math.exp(-t * 3), 0.7)
        self.sounds["win"] = self.make(1.6, lambda t: sum(math.sin(tau * f * t) * math.exp(-(t - d) * 3)
                                                     for f, d in ((440, 0), (554, 0.25), (659, 0.5), (880, 0.75))
                                                     if t >= d) * 0.5, 0.4)
        self.sounds["step"] = self.make(0.12, lambda t: (math.sin(tau * 70 * t) * 0.8 + random.uniform(-1, 1) * 0.35)
                                   * math.exp(-t * 38), 0.5)
        self.sounds["mstep"] = self.make(0.22, lambda t: (math.sin(tau * 45 * t) + random.uniform(-1, 1) * 0.3)
                                    * math.exp(-t * 20), 0.9)
        self.sounds["shot"] = self.make(0.7, lambda t: random.uniform(-1, 1) * math.exp(-t * 18)
                                   + 0.9 * math.sin(tau * (160 - 120 * t) * t) * math.exp(-t * 8), 0.95, echo=((0.06, 0.40), (0.14, 0.25), (0.26, 0.12)))
        self.sounds["rumble"] = self.make(2.6, lambda t: (random.uniform(-1, 1) * 0.5 + math.sin(tau * 38 * t) * 0.7
                                                     + math.sin(tau * 23 * t) * 0.5) * min(1.0, t * 3)
                                     * math.exp(-max(0.0, t - 1.5) * 2), 0.9, echo=((0.20, 0.30), (0.45, 0.18)))
        self.sounds["crash"] = self.make(1.4, lambda t: (random.uniform(-1, 1) * 0.9
                                                    + math.sin(tau * 40 * t) * 0.8 * math.exp(-t * 5))
                                    * math.exp(-t * 3.2), 1.0, echo=((0.09, 0.40), (0.21, 0.25), (0.37, 0.12)))
        self.sounds["alarm"] = self.make(2.0, lambda t: math.sin(tau * 520 * t + 110 * math.sin(tau * 1.5 * t)) * 0.6, 0.35)
        self.sounds["creak"] = self.make(1.0, lambda t: math.sin(tau * (150 - 40 * t) * t + 3 * math.sin(tau * 9 * t))
                                    * 0.5 * math.sin(math.pi * t) + random.uniform(-0.08, 0.08), 0.5)
        self.sounds["clunk"] = self.make(0.18, lambda t: (math.sin(tau * 95 * t) + random.uniform(-1, 1) * 0.4)
                                    * math.exp(-t * 28), 0.7)
        self.sounds["glass"] = self.make(0.55, lambda t: (random.uniform(-1, 1) * math.exp(-t * 16)
                                                     + math.sin(tau * 3100 * t) * 0.5 * math.exp(-t * 26)
                                                     + math.sin(tau * 4700 * t) * 0.3 * math.exp(-t * 40)), 0.8)

    def make(self, dur, fn, vol, echo=None):
        """Синтез по формуле fn(t). echo — [(задержка_с, громкость)...]: затухающее эхо, звук «стоит в помещении»."""
        n = int(self.rate * dur)
        vals = [clamp(fn(i / self.rate), -1.0, 1.0) * vol for i in range(n)]
        if echo:
            vals += [0.0] * int(max(d for d, _ in echo) * self.rate)
            out = list(vals)
            for d, g in echo:
                k = int(d * self.rate)
                for i in range(k, len(vals)):
                    out[i] += vals[i - k] * g
            vals = [clamp(v, -1.0, 1.0) for v in out]
        buf = bytearray()
        for v in vals:
            buf += int(v * 32767).to_bytes(2, "little", signed=True) * self.ch
        return pygame.mixer.Sound(buffer=bytes(buf))

    def make_music(self, dur, fn, vol, reverb=True, decim=2):
        """
        Музыка и фоны: функция считается через decim отсчётов, остальное интерполируется (быстрее).
        reverb — три круговых эха («зал»): петля остаётся бесшовной.
        """
        n = int(self.rate * dur)
        step = decim / self.rate
        loop = n // decim
        vals = [fn(k * step) for k in range(loop + 2)]
        if reverb:
            out = list(vals)
            for d, g in ((0.19, 0.30), (0.37, 0.20), (0.61, 0.12)):
                k = int(d * self.rate / decim)
                for i in range(loop + 2):
                    out[i] += vals[(i - k) % loop] * g
            vals = [v * 0.8 for v in out]
        buf = bytearray()
        for i in range(n):
            k, f = divmod(i, decim)
            v = vals[k] if f == 0 else vals[k] + (vals[k + 1] - vals[k]) * (f / decim)
            buf += int(clamp(v, -1.0, 1.0) * vol * 32767).to_bytes(2, "little", signed=True) * self.ch
        return pygame.mixer.Sound(buffer=bytes(buf))

class Audio:
    """Воспроизведение: микшер, громкость, выключение звука, музыкальные слои. Звуки берёт у SoundBank."""

    def __init__(self, progress=None):
        self.ok = False
        self.muted = False
        self.bank = None
        self.layers = {}                       # музыкальные слои: имя -> канал
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            info = pygame.mixer.get_init()
            if info is None or info[1] != -16:
                return
            pygame.mixer.set_num_channels(24)  # запас: музыка держит несколько каналов, эффекты не должны глохнуть
            self.bank = SoundBank(info[0], info[2], progress)
            self.ok = True
            self.bank.sounds["drone"].set_volume(0.35)
        except (pygame.error, Exception):
            self.ok = False

    def play(self, name, loops=0, vol=None):
        if self.ok and not self.muted and name in self.bank.sounds:
            ch = self.bank.sounds[name].play(loops)
            if ch is not None and vol is not None:
                ch.set_volume(clamp(vol, 0.0, 1.0))

    def set_muted(self, m):
        self.muted = m
        if self.ok:
            self.bank.sounds["drone"].set_volume(0.0 if m else 0.35)   # фоновый гул крутится, просто тихо
            if m:
                for ch in self.layers.values():
                    if ch is not None:
                        ch.set_volume(0.0)

    def stop(self, name):
        if self.ok and name in self.bank.sounds:
            self.bank.sounds[name].stop()

    def silence(self):
        """Мёртвая тишина перед скримером: гасит фоновый гул (музыку гасит MusicDirector)."""
        if self.ok:
            self.bank.sounds["drone"].set_volume(0.0)

    def restore(self):
        if self.ok:
            self.bank.sounds["drone"].set_volume(0.0 if self.muted else 0.35)

    def music(self, name, vol, loops=-1):
        """Музыкальный слой: включает, если ещё не играет, и выставляет громкость (при mute — тишина)."""
        if not self.ok or name not in self.bank.sounds:
            return
        snd = self.bank.sounds[name]
        v = 0.0 if self.muted else clamp(vol, 0.0, 1.0)
        ch = self.layers.get(name)
        if name not in self.layers or (loops == -1 and (ch is None or not ch.get_busy())):
            ch = snd.play(loops)
            self.layers[name] = ch
        if ch is not None and ch.get_sound() is snd:        # канал мог уйти под другой звук — его не трогаем
            ch.set_volume(v)

    def music_stop(self, name):
        ch = self.layers.pop(name, None)
        if ch is not None:
            ch.stop()


# ------------------------------------------------------------------ СУЩНОСТИ
class Player:
    r = 11

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.angle = 0.0
        self.battery = 100.0
        self.stamina = 100.0
        self.exhausted = False
        self.light_on = True
        self.keys = 0
        self.noise = 0.0
        self.moving = False
        self.sprinting = False
        self.regen_wait = 0.0


class Monster:
    r = 15
    SEE_ON = 540        # дальность зрения, если игрок светит фонарём
    SEE_OFF = 260       # ... если фонарь выключен
    SPEED = {"patrol": 88, "investigate": 135, "search": 0, "chase": 188}

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.facing = random.uniform(0, 6.28)
        self.state = "patrol"
        self.dmap = None
        self.goal = None
        self.timer = 0.0
        self.repath = 0.0
        self.last_seen = None
        self.anim = 0.0
        self.hear_cd = 0.0
        self.lost = 0.0
        self.stun = 0.0                    # оглушён после того, как игрок вырвался
        self.active = True                 # False — монстра на этаже нет (аванпост): не двигается, не рисуется, не ловит

    # --- навигация
    def set_goal(self, g, cx, cy):
        self.goal = (cx, cy)
        self.dmap = bfs_map(g.grid, cx, cy)

    def move_toward(self, g, tx, ty, speed, dt):
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d < 0.5:
            return
        ux, uy = dx / d, dy / d
        self.facing += angle_diff(math.atan2(dy, dx), self.facing) * min(1.0, dt * 8)
        self.x += ux * speed * dt
        self.y += uy * speed * dt
        self.x, self.y = push_out(g.grid, self.x, self.y, self.r)

    def follow(self, g, dt, speed):
        """Идёт по карте расстояний к цели. Возвращает True, когда дошёл."""
        cx, cy = int(self.x // TILE), int(self.y // TILE)
        d0 = self.dmap[cy][cx]
        if d0 < 0:
            return True
        if d0 == 0:
            gx, gy = (self.goal[0] + 0.5) * TILE, (self.goal[1] + 0.5) * TILE
            if math.hypot(gx - self.x, gy - self.y) < 10:
                return True
            self.move_toward(g, gx, gy, speed, dt)
            return False
        for dx, dy in DIRS:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < GW and 0 <= ny < GH and self.dmap[ny][nx] == d0 - 1:
                self.move_toward(g, (nx + 0.5) * TILE, (ny + 0.5) * TILE, speed, dt)
                break
        return False

    def new_patrol_goal(self, g):
        cx, cy = int(self.x // TILE), int(self.y // TILE)
        if random.random() < g.dc["hunt"]:       # охотничье чутьё: тянется в район, где бродит игрок
            p = g.player
            px, py = int(p.x // TILE), int(p.y // TILE)
            near = [c for c in g.floors if 3 <= abs(c[0] - px) + abs(c[1] - py) <= 14]
            if near:
                c = random.choice(near)
                self.set_goal(g, c[0], c[1])
                return
        best = None
        for _ in range(6):
            c = random.choice(g.floors)
            score = abs(c[0] - cx) + abs(c[1] - cy)
            if best is None or score > best[0]:
                best = (score, c)
        self.set_goal(g, best[1][0], best[1][1])

    # --- ИИ
    def update(self, g, dt):
        if not self.active:
            return
        if self.stun > 0:                    # оглушён: стоит и дёргается
            self.stun -= dt
            self.anim += dt
            return
        p = g.player
        dx, dy = p.x - self.x, p.y - self.y
        d = math.hypot(dx, dy)
        self.anim += dt
        self.hear_cd = max(0.0, self.hear_cd - dt)

        los = line_clear(g.grid, self.x, self.y, p.x, p.y)
        see = False
        if los:                                   # ЗРЕНИЕ: прямая видимость + конус обзора
            rng = self.SEE_ON if (p.light_on and p.battery > 0) else self.SEE_OFF
            if d < 85:
                see = True
            elif d < rng and abs(angle_diff(math.atan2(dy, dx), self.facing)) < math.radians(70):
                see = True
        heard = (d if los else d * 1.7) < p.noise * g.dc["hear"]  # СЛУХ: шум игрока, стены приглушают
        if g.hidden:                              # игрок в шкафчике: не виден и не слышен
            see = heard = False
        if g.lure is not None and self.state != "chase" and self.hear_cd <= 0:   # бутылка разбилась
            lx, ly = g.lure
            if math.hypot(lx - self.x, ly - self.y) < 800:
                self.state = "investigate"
                self.set_goal(g, int(lx // TILE), int(ly // TILE))
                self.hear_cd = 1.0

        if see:
            if self.state != "chase":
                g.emit("monster_alert")
            self.state = "chase"
            self.lost = 0.0
            self.last_seen = (p.x, p.y)
        elif self.state == "chase":
            self.lost += dt
            if self.lost > 6.0:
                self.state, self.timer = "search", 3.0
        elif heard and self.hear_cd <= 0 and self.state in ("patrol", "search", "investigate"):
            self.state = "investigate"
            self.set_goal(g, int(p.x // TILE), int(p.y // TILE))
            self.hear_cd = 0.7

        sp = self.SPEED[self.state] * g.dc["mspeed"] * g.plan["mspeed"]
        if self.state == "chase":
            self.repath -= dt
            if see and line_clear_thick(g.grid, self.x, self.y, p.x, p.y):
                self.move_toward(g, p.x, p.y, sp, dt)         # видит и путь свободен — бросок напрямую
            else:
                tgt = (p.x, p.y) if see else self.last_seen
                tc = (int(tgt[0] // TILE), int(tgt[1] // TILE))
                if self.goal != tc and (self.repath <= 0 or self.dmap is None):
                    self.set_goal(g, tc[0], tc[1])
                    self.repath = 0.25
                if self.dmap is not None and self.follow(g, dt, sp) and not see:
                    self.state, self.timer = "search", 3.5
        elif self.state == "investigate":
            if self.follow(g, dt, sp):
                self.state, self.timer = "search", 3.0
        elif self.state == "search":
            self.facing += 1.9 * dt
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.goal = "patrol", None
        else:
            if self.goal is None or self.follow(g, dt, sp):
                self.new_patrol_goal(g)

        # поиск у шкафчика: монстр может заглянуть внутрь
        if g.hidden and self.state == "search" and d < 95:
            g.locker_timer += dt
            if g.locker_risk and g.locker_timer > 2.0:
                g.pending_catch = True


# ------------------------------------------------------------------ СЮЖЕТ
class StoryBook:
    """
    Сюжет (только текст, ничего не рисует). Герои: Марк (ты, образец №12, иммунный), Томас Бранд (образец №13,
    твой друг), Лена (его сестра, на связи по рации), доктор Вейра, инженер Лиза Рау, охранник Громов, директор Кесслер.
    """

    PROLOGUE = [        # (длительность, слова рассказчика) — шесть сцен вступительной кат-сцены
        (5.0, ["1987 год. Подземный комплекс «БУНКЕР-13».", "Проект «ГЛУБИНА» обещал людям вторую жизнь."]),
        (5.0, ["Директор Кесслер приказал начать испытания на людях.", "«Вторая волна. Без отступлений»."]),
        (5.0, ["Марку, технику комплекса, сказали: «Просто витамины»."]),
        (6.0, ["Но образец №13 не выдержал. Стекло треснуло.", "Он вышел из-под контроля."]),
        (4.5, ["Кесслер запечатал этажи и сбежал на поверхность.", "Лифты — единственный путь наверх."]),
        (5.0, ["Ты очнулся один в темноте. В кармане — фонарик и рация.", "В эфире кто-то шепчет твоё имя."]),
    ]
    FLOOR_LINES = [
        ("Лабораторный корпус: стерильно, тихо — и всё в крови.",
         "Здесь начинались испытания. Ищи ключи от лифта и записки: кто-то оставил тебе правду.",
         "Рация шипит. Кто-то зовёт тебя по имени — и это не монстр."),
        ("Опытный сектор: здесь держали подопытных.",
         "Лифт застрял между этажами. Что-то ходит по вентиляции — следом за тобой.",
         "Лена говорит: «Томми звонил мне в последний раз три месяца назад»."),
        ("Шлюз глубины — последний рубеж перед поверхностью.",
         "Над шлюзом арсенал. Но сначала придётся пройти мимо того, кто знает твоё имя.",
         "Чем выше ты поднимаешься, тем яснее: он не охотится на тебя. Он ждёт тебя."),
        ("Заброшенная шахта: сюда не должны были попасть живые.",
         "Трос оборвался, и лифт рухнул на самое дно. Здесь остался динамит рабочих — для обвалов.",
         "Два пути: найти ключи и подняться на лифте — или взорвать завал и выйти прямо на поверхность."),
        ("Реакторная: стены дрожат, а воздух пахнет озоном.",
         "Здесь питание всего комплекса. Ржавые трубы шипят паром — и шипят громче шагов.",
         "Монстр плохо слышит в этом шуме. Но и ты не услышишь его."),
        ("Аванпост «Сентинел»: казарма, арсенал, лаборатория и лазарет под одной крышей.",
         "Солдаты держат периметр, Лена сидит у рации в посте связи, а в холодильниках — образцы доктора Вейры.",
         "Монстр сюда не проникает: гермоворота заперты наглухо. Можно перевести дух — и сделать выбор."),
        ("Склады: лабиринт ящиков, бочек и стеллажей.",
         "Сквозняк разносит звук шагов по всему этажу.",
         "Один лифт отделяет тебя от этажей, где всё началось."),
    ]
    TOTAL_NOTES = 24
    NOTES = {
        0: [("ЖУРНАЛ ИССЛЕДОВАТЕЛЯ, день 41",
             "Проект «ГЛУБИНА» задумывался как лекарство от старения. Сыворотку получили из грибницы под шахтой. "
             "Образец №13 принял её лучше всех. Слишком хорошо. Он больше не спит."),
            ("ЗАПИСКА НА ДВЕРИ",
             "Не включайте сирену. Он реагирует на звук так же, как на запах крови. "
             "Если услышите шаги в вентиляции — не бегите. Спрячьтесь в шкафчик и считайте до ста."),
            ("ЛИЧНОЕ ДЕЛО №13",
             "Томас Бранд, 29 лет, лаборант. Вызвался добровольцем: деньги на лечение младшей сестры Лены. "
             "Директор Кесслер обещал выплату и «безопасный протокол»."),
            ("ПИСЬМО В ЯЩИКЕ СТОЛА",
             "Марк, если найдёшь это — мы оба влипли. Кесслер записал нас во «вторую волну». "
             "Тебе я ввела половинную дозу, поэтому ты ещё человек. Прости. — Вейра"),
            ("ТАБЛО ДЕЖУРНОГО ИНЖЕНЕРА",
             "Лиза Рау, инженер: «Вентиляция шумит по ночам. Кто-то ходит по шахтам и считает шаги. "
             "Охрана говорит, что мне показалось. Громов запретил открывать люки»."),
            ("РАСПИСАНИЕ ИСПЫТАНИЙ",
             "Волна 1: образец №13. Волна 2: образцы №12 и №14. Рядом от руки: «№12 — Ковальски. Дозу снизить "
             "вдвое — Вейра». Ниже чужим почерком: «Не снижать. К.»")],
        1: [("ПИСЬМО ДОКТОРА ВЕЙРЫ",
             "Мы не смогли его остановить. Томас ещё помнит своё имя: я слышала, как он шепчет его в темноте. "
             "Не называйте его монстром. Он просто очень одинок."),
            ("ИНСТРУКЦИЯ ПО ЭВАКУАЦИИ",
             "Шлюзы открываются ключами. Фонарь привлекает его, но без света вы не найдёте выход. "
             "Бутылка, разбитая вдали, отвлечёт его ненадолго. Лифты работают только вверх."),
            ("ПРОТОКОЛ ИСПЫТАНИЯ №13",
             "Сутки 3: образец ходит следом, не нападая. Сутки 6: кожа меняется. "
             "Образец реагирует на имя «Марк» — единственное, что он произносит. Причина неизвестна."),
            ("ЗАПИСЬ ДИРЕКТОРА КЕССЛЕРА",
             "Если образец вырвется — задействовать «Печать»: обрушить шлюз на нижние этажи. "
             "Люди выше важнее людей ниже. Это приказ. Персонал не эвакуировать."),
            ("ДНЕВНИК ОХРАНЫ",
             "Громов, начальник охраны: «Мы заперли образец на нижнем уровне. Он не рвался — просто стоял "
             "у двери и повторял одно слово. Я не стал слушать. Я знаю это слово»."),
            ("ЗАПИСКА НА ХОЛОДИЛЬНИКЕ",
             "«Томас просил передать: покормите кошку Лены. Он думает, что всё ещё вернётся домой». "
             "Кошку никто не покормил. Миска стоит нетронутой.")],
        2: [("ПОСЛЕДНЯЯ ЗАПИСЬ ВЕЙРЫ",
             "В арсенале над шлюзом есть пистолет. Пули его не берут — но потолок над шлюзом давно треснул. "
             "Если обрушить плиту, он останется внизу. Навсегда. Прости, Томас."),
            ("НАЦАРАПАНО НА СТЕНЕ",
             "ОН НЕ ХОЧЕТ ТЕБЯ УБИТЬ. ОН ХОЧЕТ, ЧТОБЫ ТЫ ОСТАЛСЯ. ОН ТАК ОДИНОК. ОН ПОМНИТ МАРКА."),
            ("РАДИОЖУРНАЛ",
             "Лена Бранд звонит каждый день: «Томми не выходит на связь». Директор запретил говорить ей правду. "
             "Мы лжём девочке по рации. Она всё равно ловит нас."),
            ("ПОСЛЕДНЕЕ ПИСЬМО ТОМАСА",
             "Марк, если дошёл — я слышу тебя сквозь стены. Я не хочу тебя трогать. "
             "Хочу, чтобы ты помнил: меня зовут Томас. Скажи Лене, что я не боялся."),
            ("ОБРЫВОК ОТЧЁТА КЕССЛЕРУ",
             "Сыворотку вывезли на поверхность до «Печати». Образцов внизу не осталось — кроме одного. "
             "Если №12 дойдёт до выхода, его нужно изолировать: он единственный иммунный."),
            ("КАРТОЧКА ОБРАЗЦА №12",
             "Марк Ковальски. Иммунитет к грибнице: полный. Побочный эффект: слышит образца №13 через рацию. "
             "Рекомендовано наблюдение. Не сообщать образцу о его состоянии.")],
        5: [("ЖУРНАЛ КОМАНДИРА АВАНПОСТА",
             "Аванпост «Сентинел» держит дальнюю связь с поверхностью. Нам приказали ждать эвакуации, но борт так и не пришёл. "
             "Я начинаю думать, что нас просто списали."),
            ("ЗАПИСКА НА КОНСОЛИ",
             "Рация работает, если есть питание и ключ-карта оператора. Нажмёшь вызов — вертолёт прилетит через минуту. "
             "Гермоворота держат: сюда ничего не пролезет, так что просто жди."),
            ("ХОЛОДИЛЬНИК №2",
             "Здесь лежит антидот доктора Вейры. Один шприц. Она писала: это единственный шанс вернуть Томаса, если он ещё слышит. "
             "Рядом — ампула сыворотки. НЕ ТРОГАТЬ."),
            ("ПОСЛЕДНЯЯ ЗАПИСЬ СЕРЖАНТА",
             "Я выпил сыворотку. Хотел стать сильным, чтобы выжить. Теперь я слышу всех на этажах — и они слышат меня. "
             "Не повторяй моей ошибки."),
            ("ЖУРНАЛ ДЕЖУРНОГО",
             "Три недели ни одного сигнала с нижних этажей. Только скрежет в вентиляции и, по ночам, голос, который зовёт по именам. "
             "Сержант перестал спать."),
            ("ПРИКАЗ №7 ОТ КЕССЛЕРА",
             "Аванпост не покидать. Лифты глушить. Если кто-то поднимется снизу — считать заражённым. Огонь на поражение. "
             "Вопросы не обсуждаются.")],
    }
    RADIO = {      # реплики по рации; каждая группа звучит один раз за прохождение
        "floor_start_0": [("ЛЕНА", "Эй... ты слышишь? Я Лена, поймала сигнал вашего бункера. Найди ключи от лифта — я на связи.")],
        "floor_start_1": [("ЛЕНА", "Ты ведь Марк? Томми говорил о тебе. Он пропал там внизу... Читай записки, ищи его следы.")],
        "floor_start_2": [("ЛЕНА", "Последний этаж. Если встретишь Томми... не стреляй сразу. Прошу. Просто послушай."),
                          ("ЛЕНА", "Вейра писала про арсенал над шлюзом и трещину в потолке. Береги патроны.")],
        "first_key": [("ЛЕНА", "Первый ключ у тебя. Дальше тише: он слышит шаги, особенно бег.")],
        "all_keys": [("ЛЕНА", "Все ключи! Но сирена его разбудила... Беги к лифту, скорее!")],
        "monster_first": [("ЛЕНА", "Он увидел тебя! Прячься в шкафчик (E) или брось бутылку (Q)! Не беги по прямой!")],
        "first_hide": [("ЛЕНА", "Правильно! Сиди тихо и слушай шаги. Он проходит мимо... но иногда заглядывает внутрь.")],
        "first_throw": [("ЛЕНА", "Умно: шум уводит его в сторону. Но ненадолго — бутылки не бесконечны.")],
        "note_first": [("ЛЕНА", "Это записка из бункера. Читай внимательно — каждая приближает нас к правде. TAB — архив.")],
        "notes_half": [("ЛЕНА", "Ты нашёл половину записок. Картина складывается жуткая... Не останавливайся, Марк.")],
        "all_notes": [("ЛЕНА", "Ты прочёл всё... Теперь ты знаешь, кем был Томми. Помни об этом, когда увидишь его.")],
        "low_battery": [("ЛЕНА", "Батарейка садится! Ищи зелёные огоньки — они светятся в темноте.")],
        "note_0_2": [("ЛЕНА", "«Добровольцем ради сестры»... Он говорил, что подрабатывает ночами. Он делал это для меня.")],
        "note_0_3": [("ЛЕНА", "Вейра ввела тебе половину дозы?.. Значит, вы с Томми были вместе в этом. Он тебе доверял.")],
        "note_0_5": [("ЛЕНА", "«Не снижать»... Кесслер знал, что делает. Я найду его, Марк. Клянусь.")],
        "note_1_2": [("ЛЕНА", "Он повторял твоё имя?.. Марк, он тебя помнит. Он сопротивляется изнутри.")],
        "note_1_3": [("ЛЕНА", "«Печать»?! Они собирались похоронить вас всех? Люди выше важнее?.. Какая мерзость.")],
        "note_1_4": [("ЛЕНА", "Какое слово он повторял? Марк... я знаю. Я знаю, что он говорил. «Лена»...")],
        "note_1_5": [("ЛЕНА", "Кошка... Она ждёт его дома. Он правда думал, что вернётся. Господи.")],
        "note_2_2": [("ЛЕНА", "Меня обманывали каждый день... Значит, Томми слышал мои звонки? Он слышал!")],
        "note_2_3": [("ЛЕНА", "Он писал это тебе: «Скажи Лене, что я не боялся». Не оставляй его там, Марк.")],
        "note_2_4": [("ЛЕНА", "Они вывезли сыворотку наверх... Значит, Кесслер уже на поверхности. И он знает про тебя.")],
        "note_2_5": [("ЛЕНА", "Ты слышишь его через рацию — поэтому в эфире этот шёпот. Он зовёт нас обоих.")],
        "floor_start_4": [("ЛЕНА", "Реакторная... Осторожнее: трубы шипят паром, а в шуме ты не услышишь шаги. Держись подальше от горячих секций.")],
        "floor_start_5": [("ЛЕНА", "Здесь безопасно: гермоворота держат монстра снаружи. Возьми ключ-карту и нажми вызов на консоли в посте связи.")],
        "floor_start_6": [("ЛЕНА", "Склады. Тихо: сквозняк разносит шаги по всему этажу. Скоро ты будешь на этаже, с которого всё началось.")],
        "evac_start": [("ЛЕНА", "Вызов принят! Вертолёт будет через минуту! Жди на аванпосте, Марк — скоро всё закончится!")],
        "evac_half": [("ЛЕНА", "Тридцать секунд! Они уже над лесом! Ещё немного, Марк!")],
        "antidote_found": [("ЛЕНА", "Антидот Вейры?! Береги его, Марк. Если Томми ещё слышит нас — это шанс вернуть его живым.")],
        "serum_seen": [("ЛЕНА", "Не пей это, Марк! Из этой ампулы ничего хорошего не выходит. Просто обойди.")],
        "console_hint": [("ЛЕНА", "Это консоль дальней связи. Нужна ключ-карта оператора — возьми хоть один ключ, и я вызову вертолёт.")],
        "floor_start_3": [("ЛЕНА", "Марк?! Связь рвётся... Лифт упал на -10? Там старые шахты. Ищи динамит — рабочие оставляли его для обвалов.")],
        "dynamite_found": [("ЛЕНА", "Динамит! Занеси его к завалу в конце шахты — взрыв пробьёт путь наверх. Или найди ключи и поднимайся на лифте.")],
        "blast_hint": [("ЛЕНА", "Это завал — тупик старой шахты. Подорвёшь его — выйдешь прямо на поверхность. Но взрыв услышит всё живое...")],
        "boss_start": [("ЛЕНА", "Он выбрался! Стреляй, когда круг совпадёт! Q — перезарядка, ПРОБЕЛ — отбей удар!")],
        "choice": [("ЛЕНА", "Томми...? Это ты? Томми, пожалуйста... Марк, я слышу — он говорит!")],
    }
    WHISPERS = ["...Марк...", "...не уходи...", "...мне холодно...", "...ты слышишь меня?...", "...помоги мне...",
                "...Лена...?", "...я помню тебя...", "...останься...", "...кошка...", "...я не боялся..."]
    CHOICE = {
        "title": "ТОМАС ЗАМЕР",
        "lines": ["Он опускается на колени. Чёрные глаза гаснут.", "Он шепчет: «Марк... это ты?»"],
        "spare": "[1]  ПОЩАДИТЬ — опустить пистолет",
        "kill": "[2]  ДОБИТЬ — выстрелить",
    }
    ENDINGS = {
        "evac": ("ЭВАКУАЦИЯ", (120, 200, 255),
                 ["Ты нажал вызов и ждал минуту, которая показалась годом. Сквозь шум пробился рокот винтов.",
                  "Вертолёт сел у люка. Солдаты втащили тебя внутрь и закрыли дверь.",
                  "Лена ждала на базе. Но вопросы о «ГЛУБИНЕ» засекретили, а тебя отправили на карантин.",
                  "Ты спасён. Но никто так и не узнал, что осталось на нижних этажах."]),
        "serum": ("НОВАЯ ПЛОТЬ", (210, 60, 60),
                  ["Ты выпил сыворотку. Боль была короткой, потом пришла ясность. Тьма внизу перестала быть тьмой.",
                   "Ты слышишь каждого на этаже. И все они слышат тебя.",
                   "Лена зовёт по рации: «Марк? Марк, ответь!» — а ты уже не можешь говорить.",
                   "Скоро кто-то спустится сюда. И «Бункер-13» получит нового хозяина."]),
        "cure": ("ВСЕ ЖИВЫ", (150, 255, 190),
                 ["Ты ввёл антидот. Томас вздрогнул, и чёрные глаза стали обычными. Он заплакал, как человек.",
                  "Вы вместе поднялись наверх. Лена ждала у лифта. Она обняла брата и не отпускала всю ночь.",
                  "Кесслера нашли по записи рации. «Проект ГЛУБИНА» закрыли, «Бункер-13» залили бетоном.",
                  "Единственная концовка, где не остался ни один монстр. Только трое людей и кошка, которую наконец покормили."]),
        "blast": ("ВЗРЫВНОЙ ПОБЕГ", (255, 170, 70),
                  ["Ты зажёг фитиль и укрылся за ящиками. Грохот прокатился по шахте — и сверху хлынул настоящий дневной свет.",
                   "Ты выбрался на поверхность в обход лифтов, этажей и монстра. Рация шипела от помех.",
                   "Наверху уже выла сирена: взрыв услышали за километры. Лена нашла тебя первой и записала каждое твоё слово.",
                   "Кесслер не успел улететь. Правда о «ГЛУБИНЕ» всплыла вместе с тобой. Томас так и остался там, внизу, один."]),
        "normal": ("ВЫ СБЕЖАЛИ", (80, 220, 120),
                   ["Плита рухнула, и чудовище больше не встало.",
                    "Ты поднялся на поверхность. Рация молчит.",
                    "Кесслер давно улетел — а сыворотка осталась в его чемодане.",
                    "Лена так и не узнала, что стало с братом. А ты — кем был ты сам."]),
        "kill": ("ТИШИНА", (200, 200, 215),
                 ["Ты выстрелил. Томас узнал тебя в последний миг — и будто улыбнулся.",
                  "На другом конце эфира Лена плачет и не отключается.",
                  "Иммунитет в твоей крови — единственный шанс остановить Кесслера. Ты знаешь, что делать.",
                  "Но каждую ночь рация шепчет твоё имя."]),
        "spare": ("ИСКУПЛЕНИЕ", (255, 220, 140),
                  ["Ты опустил пистолет. Томас поднялся — человеком.",
                   "Он удержал рухнувшую плиту, пока ты уходил: «Скажи Лене, что я не боялся».",
                   "На поверхности Лена ждала у рации. Ты рассказал ей всё, и вы вместе записали каждое слово Кесслера.",
                   "Через неделю «Проект ГЛУБИНА» перестал быть тайной. Томас остался в её памяти — героем."]),
    }


# ------------------------------------------------------------------ УРОВЕНЬ
class Level:
    """Готовый уровень: сетка и расстановка предметов (только данные)."""

    def __init__(self, grid, floors, exit_cell, keys, bats, botts, lockers, lamps, monster_cell, notes, dynamite, blast_cell, extras):
        self.grid = grid
        self.floors = floors
        self.exit_cell = exit_cell
        self.keys = keys
        self.bats = bats
        self.botts = botts
        self.lockers = lockers
        self.lamps = lamps
        self.monster_cell = monster_cell
        self.notes = notes
        self.dynamite = dynamite
        self.blast_cell = blast_cell
        self.extras = extras


class LevelBuilder:
    """Генерация уровня: лабиринт + расстановка ключей, батареек, бутылок, шкафчиков, ламп и монстра."""

    def __init__(self, dc, plan):
        self.dc = dc
        self.plan = plan

    @staticmethod
    def far_enough(c, others, sep):
        return all(abs(c[0] - o[0]) + abs(c[1] - o[1]) >= sep for o in others)

    @staticmethod
    def item(c):
        return {"x": (c[0] + 0.5) * TILE, "y": (c[1] + 0.5) * TILE, "alive": True, "ph": random.uniform(0, 6.28)}

    def build(self):
        grid, rooms = generate_outpost() if self.plan.get("outpost") else (generate_maze(), [])
        floors = [(x, y) for y in range(GH) for x in range(GW) if grid[y][x] == 0]
        dist = bfs_map(grid, 1, 1)
        maxd = max(dist[y][x] for x, y in floors)
        dead = [(x, y) for x, y in floors
                if sum(1 for dx, dy in DIRS if grid[y + dy][x + dx] == 0) == 1 and (x, y) != (1, 1)]
        exit_cell = max(dead or floors, key=lambda c: dist[c[1]][c[0]])
        ex, ey = exit_cell
        far_enough = self.far_enough

        # 3 ключа — далеко от старта, от выхода и друг от друга
        cands = [c for c in floors if dist[c[1]][c[0]] >= 12 and abs(c[0] - ex) + abs(c[1] - ey) > 6]
        nk = self.plan["keys"]
        keys, sep, tries = [], 14, 0
        while len(keys) < nk and tries < 600 and cands:
            tries += 1
            c = random.choice(cands)
            if far_enough(c, keys, sep):
                keys.append(c)
            if tries % 100 == 0:
                sep -= 3
        while len(keys) < nk:
            keys.append(random.choice(floors))

        taken = set(keys) | {exit_cell, (1, 1)}
        bats, sep, tries = [], 7, 0
        bcands = [c for c in floors if dist[c[1]][c[0]] >= 5 and c not in taken]
        while len(bats) < max(3, self.dc["bats"] + self.plan["bats_d"]) and tries < 600 and bcands:
            tries += 1
            c = random.choice(bcands)
            if far_enough(c, bats, sep):
                bats.append(c)
            if tries % 120 == 0:
                sep -= 2

        bt = [c for c in floors if dist[c[1]][c[0]] >= 4 and c not in taken and c not in set(bats)]
        random.shuffle(bt)
        botts = []
        for c in bt:
            if len(botts) >= 5:
                break
            if far_enough(c, [(int(o["x"] // TILE), int(o["y"] // TILE)) for o in botts], 6):
                botts.append(self.item(c))

        nt = [c for c in floors if dist[c[1]][c[0]] >= 6 and c not in taken and c not in set(bats)]
        random.shuffle(nt)
        notes, sep, tries = [], 8, 0
        while len(notes) < self.plan.get("notes", 6) and tries < 1800 and nt:          # шесть записок с историей на каждом этаже
            tries += 1
            c = random.choice(nt)
            others = [(int(o["x"] // TILE), int(o["y"] // TILE)) for o in notes] + list(keys)
            if far_enough(c, others, sep):
                it = self.item(c)
                it["idx"] = len(notes)
                notes.append(it)
            if tries % 150 == 0 and sep > 2:
                sep -= 2

        mc = [c for c in floors if 0.5 * maxd <= dist[c[1]][c[0]] <= 0.85 * maxd and c != exit_cell]
        monster_cell = random.choice(mc or floors)

        # шкафчики у стен (E — спрятаться) и потолочные лампы (часть сломана и мигает)
        used = set(keys) | set(bats) | {exit_cell, (1, 1)}
        lc = [c for c in floors if grid[c[1] - 1][c[0]] == 1 and c not in used and dist[c[1]][c[0]] >= 4]
        random.shuffle(lc)
        lockers = []
        for c in lc:
            if len(lockers) >= 10:
                break
            if all(abs(c[0] - o["tx"]) + abs(c[1] - o["ty"]) >= 6 for o in lockers):
                lockers.append({"tx": c[0], "ty": c[1], "x": (c[0] + 0.5) * TILE, "y": c[1] * TILE + 19})
        lcells = [c for c in floors if dist[c[1]][c[0]] >= 3]
        random.shuffle(lcells)
        lamps = []
        for c in lcells:
            if len(lamps) >= 14:
                break
            if all(abs(c[0] - (o["x"] / TILE - 0.5)) + abs(c[1] - (o["y"] / TILE - 0.5)) >= 5 for o in lamps):
                lamps.append({"x": (c[0] + 0.5) * TILE, "y": (c[1] + 0.5) * TILE,
                              "ph": random.uniform(0, 6.28), "broken": random.random() < self.plan["broken"], "idx": 2})

        dyn, blast_cell = [], None
        if self.plan.get("secret"):                       # секретный этаж: динамит и завал в разных дальних углах
            far = [c for c in dead if c != exit_cell and dist[c[1]][c[0]] >= 10 and c not in set(keys)]
            pool = far or [c for c in floors if dist[c[1]][c[0]] >= 12 and c != exit_cell]
            blast_cell = random.choice(pool or floors)
            dc = [c for c in floors if dist[c[1]][c[0]] >= 14 and c not in taken and c != blast_cell
                  and far_enough(c, [blast_cell, exit_cell], 10)] or [random.choice(floors)]
            dyn = [self.item(random.choice(dc))]
        extras = {"console": None, "antidote": [], "serum": [], "npcs": [], "rooms": rooms}
        if self.plan.get("outpost"):                       # аванпост: консоль в посте связи, антидот в лазарете, сыворотка в лаборатории
            R = {r["name"]: r for r in rooms}

            def room_cell(r, dx, dy):
                tx_, ty_ = r["mid"][0] + dx, r["mid"][1] + dy
                return min((c for c in floors if r["x0"] <= c[0] <= r["x1"] and r["y0"] <= c[1] <= r["y1"]),
                           key=lambda c: (c[0] - tx_) ** 2 + (c[1] - ty_) ** 2)

            console = room_cell(R["ПОСТ СВЯЗИ"], 0, -2)
            lena = room_cell(R["ПОСТ СВЯЗИ"], -3, -1)
            ant = room_cell(R["ЛАЗАРЕТ"], 3, 2)
            ser = room_cell(R["ЛАБОРАТОРИЯ"], -3, 2)
            npcs = [{"kind": "lena", "x": (lena[0] + 0.5) * TILE, "y": (lena[1] + 0.5) * TILE, "ang": 0.3}]
            for tx_, ty_, ang in ((4, 1, math.pi), (8, 1, 0.0), (33, 24, math.pi), (19, 12, math.pi / 2)):       # караулы
                npcs.append({"kind": "soldier", "x": (tx_ + 0.5) * TILE, "y": (ty_ + 0.5) * TILE, "ang": ang})
            extras = {"console": console, "antidote": [self.item(ant)], "serum": [self.item(ser)], "npcs": npcs, "rooms": rooms}
        return Level(grid, floors, exit_cell, [self.item(c) for c in keys], [self.item(c) for c in bats],
                     botts, lockers, lamps, monster_cell, notes, dyn, blast_cell, extras)


class Session:
    """
    Состояние текущего забега (модель данных). Не рисует, не слушает ввод, не играет звуки:
    системы читают и меняют его поля, а о важных моментах сообщают событиями (emit / drain).
    """

    def __init__(self):
        self.dc = DIFFS[1]
        self.events = []
        self.grid = None
        self.floors = []
        self.exit_cell = (1, 1)
        self.keys, self.bats, self.botts, self.lockers, self.lamps = [], [], [], [], []
        self.notes = []
        self.dynamite = []
        self.blast_cell = None
        self.console_cell = None
        self.antidote = []
        self.serum = []
        self.npcs = []
        self.rooms = []
        self.cin_name = ""
        self.floor = 0
        self.player = None
        self.monster = None
        self.reset_flags()

    def reset_flags(self):
        self.play_time = 0.0
        self.hidden = False
        self.hid_L = None
        self.locker_risk = False
        self.locker_timer = 0.0
        self.pending_catch = False
        self.alarm_t = 0.0
        self.cheated = False
        self.has_gun = False
        self.bottles = 2
        self.thrown = []
        self.lure = None
        self.stats = {"lockers": 0, "bottles": 0}
        self.finish_time = 0.0
        self.exit_warn = 0.0
        self.low_warned = False
        self.exit_open = 0.0
        self.grace = 0.0                  # секунды неуязвимости после побега из хватки
        self.has_dynamite = False
        self.blast_warn = 0.0
        self.has_antidote = False         # переносится между этажами
        self.evac_t = None                # секунды до вертолёта (None — вызова не было)
        self.evac_done = False
        self.console_warn = 0.0
        self.notes_read = set()          # (этаж, номер) прочитанных записок — переносится между этажами
        self.radio_seen = set()          # какие радиосцены уже прозвучали
        self.ending = "normal"          # normal | kill | spare

    def emit(self, name, data=None):
        self.events.append((name, data))

    def drain(self):
        ev, self.events = self.events, []
        return ev

    @property
    def plan(self):
        return FLOORS[self.floor]

    @property
    def keys_needed(self):
        return self.plan["keys"]

    @property
    def all_notes_read(self):
        return len(self.notes_read) >= StoryBook.TOTAL_NOTES

    def carry(self):
        """Что игрок уносит на следующий этаж."""
        p = self.player
        return {"battery": p.battery, "stamina": p.stamina, "bottles": self.bottles, "stats": dict(self.stats),
                "play_time": self.play_time, "cheated": self.cheated,
                "notes_read": set(self.notes_read), "radio_seen": set(self.radio_seen),
                "has_antidote": self.has_antidote}

    def start(self, dc, floor=0, carry=None):
        """Новый этаж floor по сложности dc. carry — вещи и счётчики с предыдущего этажа."""
        self.floor = floor
        level = LevelBuilder(dc, FLOORS[floor]).build()
        self.dc = dc
        self.grid, self.floors, self.exit_cell = level.grid, level.floors, level.exit_cell
        self.keys, self.bats, self.botts, self.notes = level.keys, level.bats, level.botts, level.notes
        self.dynamite, self.blast_cell = level.dynamite, level.blast_cell
        self.console_cell, self.antidote, self.serum = level.extras["console"], level.extras["antidote"], level.extras["serum"]
        self.npcs, self.rooms = level.extras["npcs"], level.extras["rooms"]
        self.lockers, self.lamps = level.lockers, level.lamps
        self.reset_flags()
        self.events = []
        self.player = Player(1.5 * TILE, 1.5 * TILE)
        self.monster = Monster((level.monster_cell[0] + 0.5) * TILE, (level.monster_cell[1] + 0.5) * TILE)
        self.monster.active = not self.plan.get("safe")      # на безопасном этаже (аванпост) монстра нет
        if carry:
            self.player.battery, self.player.stamina = carry["battery"], carry["stamina"]
            self.bottles, self.stats = carry["bottles"], carry["stats"]
            self.play_time, self.cheated = carry["play_time"], carry["cheated"]
            self.notes_read, self.radio_seen = set(carry["notes_read"]), set(carry["radio_seen"])
            self.has_antidote = carry.get("has_antidote", False)
        if self.monster.active:
            self.monster.new_patrol_goal(self)


# ------------------------------------------------------------------ СЕРВИСЫ ПРИЛОЖЕНИЯ
class FrameClock:
    """Время: кадровая задержка и накопленные секунды (больше ничего)."""

    def __init__(self):
        self._clock = pygame.time.Clock()
        self.t = 0.0
        self.raw = 0.0
        self.dt = 0.0

    def tick(self):
        self.raw = self._clock.tick(FPS) / 1000.0
        self.dt = min(self.raw, 0.05)
        self.t += self.dt
        return self.dt


class Settings:
    """Настройки игрока: сложность, качество графики, щадящий режим, показ карты."""

    def __init__(self):
        self.diff = 1
        self.quality = 1
        self.gentle = False
        self.show_map = True
        self.auto_q = False
        self.slow_t = 0.0

    @property
    def dc(self):
        return DIFFS[self.diff]

    def cycle_diff(self, delta):
        self.diff = (self.diff + delta) % len(DIFFS)

    def set_diff(self, i):
        self.diff = int(clamp(i, 0, len(DIFFS) - 1))

    def watch_frame(self, raw):
        """Следит за FPS. Возвращает True в момент, когда качество было автоматически снижено."""
        if not self.quality or self.auto_q:
            return False
        self.slow_t = self.slow_t + raw if raw > 0.026 else max(0.0, self.slow_t - raw)
        if self.slow_t > 3.0:                    # долго < 38 FPS — упрощаем графику
            self.quality, self.auto_q = 0, True
            return True
        return False


class Notifier:
    """Короткие сообщения для игрока (хранит текст и таймер; рисует их Hud)."""

    def __init__(self):
        self.clear()

    def clear(self):
        self.msg, self.msg_t, self.msg_max = "", 0.0, 1.0

    def say(self, s, secs=3.0):
        self.msg, self.msg_t, self.msg_max = s, secs, secs

    def tick(self, dt):
        if self.msg_t > 0:
            self.msg_t -= dt


class ScoreBoard:
    """Лучшие времена по сложностям (только в памяти, читеры рекорд не получают)."""

    def __init__(self):
        self.best = {i: None for i in range(len(DIFFS))}
        self.new_record = False

    def submit(self, finish_time, diff, cheated):
        b = self.best[diff]
        self.new_record = (not cheated) and (b is None or finish_time < b)
        if self.new_record:
            self.best[diff] = finish_time


# ------------------------------------------------------------------ РЕСУРСЫ: ТЕКСТУРЫ
class Textures:
    """Генерация всех процедурных картинок: плитки, тени у стен, виньетка, зерно, туман, свечения."""

    def __init__(self, progress=None):
        report = progress or (lambda text: None)
        random.seed()
        self.wall_tiles = [make_wall_tile(k) for k in (0, 0, 0, 0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3)]
        report("ЗАГРУЗКА...  текстуры")
        kinds = [0, 0, 0, 0, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6, 7, 8]
        self.floor_tiles = [make_floor_tile(k) for k in kinds]
        self.ao = make_ao_strips()

        report("ЗАГРУЗКА...  эффекты")
        # виньетка + линии развёртки — одним слоем
        overlay = make_vignette(SW, SH, (0, 0, 0), 225, 1.7)
        lines = pygame.Surface((SW, SH), pygame.SRCALPHA)
        for y in range(0, SH, 3):
            pygame.draw.line(lines, (0, 0, 0, 34), (0, y), (SW, y))
        overlay.blit(lines, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self.overlay = overlay
        self.red_vig = make_vignette(SW, SH, (150, 0, 0), 255, 1.2, 0.2)

        # зерно киноплёнки: несколько кадров, на каждом кадре случайный
        self.grain = []
        for _ in range(6):
            s = pygame.Surface((SW // 2, SH // 2), pygame.SRCALPHA)
            for _ in range(22000):
                c = 255 if random.random() < 0.5 else 0
                s.set_at((random.randrange(SW // 2), random.randrange(SH // 2)), (c, c, c, random.randint(8, 34)))
            self.grain.append(pygame.transform.scale(s, (SW, SH)))

        # туман: один слой привязан к миру, второй дрейфует по экрану
        self.fog_world = make_fog(WW, WH, (16, 22, 26))
        self.fog_drift = make_fog(SW * 2, SH * 2, (14, 20, 24))

        self.glow_red = make_glow(10, (255, 30, 20), 230)
        self.glow_key = make_glow(30, (255, 210, 70), 150)
        self.glow_bat = make_glow(22, (90, 255, 120), 130)
        self.glow_exit_r = make_glow(46, (255, 40, 30), 150)
        self.glow_exit_g = make_glow(46, (60, 255, 90), 150)
        self.glow_lamp = make_glow(70, (255, 170, 80), 90)
        self.glow_note = make_glow(22, (170, 200, 255), 130)
        self.dust_sprites = [make_glow(r, (165, 156, 142), 120) for r in (30, 48, 70)]
        report("ЗАГРУЗКА...  персонажи")
        self.player_hi = make_player_hi()                   # 128 px: для крупных планов
        self.player_base = pygame.transform.smoothscale(self.player_hi, (64, 64))      # игровой размер (сглажен усреднением)
        self.monster_hi = make_monster_hi()                 # 224 px
        self.monster_base = pygame.transform.smoothscale(self.monster_hi, (112, 112))
        self.persons = {k: make_person_hi(k) for k in PERSONS}      # люди сверху: солдат, Лена, учёный, Кесслер, охранник
        self.rigs = {k: make_side_rig(k) for k in ("mark", "lena", "soldier")}   # боковые фигуры для кат-сцен



class Atmosphere:
    """Настроение этажа (ответственность: эффекты опасности, мерцание, шаги, скрипы, пыль)."""
    def __init__(self, audio, cfg, s):
        self.audio = audio
        self.cfg = cfg
        self.s = s
        self.dust = []
        self.shake = (0, 0)
        self.danger = 0.0
        self.pulse = 0.0
        self.flick_t = 0.0
        self.flick_depth = 0
        self.jit = 0
        self.jit_t = 0.0
        self.heart_t = 0.0
        self.creak_t = 0.0
        self.step_t = 0.0
        self.mstep_t = 0.0
        self.step_alt = False
        self.breath_t = 0.0
        self.glitch_t = 0.0
        self.seen_cd = 0.0
        self.was_vis = False
        self.eyes = []


    def reset(self):
        """Новый забег: обнуляет таймеры и заново рассыпает пыль."""
        self.step_t = 0.0
        self.mstep_t = 0.0
        self.creak_t = random.uniform(10, 25)
        self.breath_t = 0.0
        self.glitch_t = 0.0
        self.seen_cd = 0.0
        self.was_vis = False
        far = [c for c in self.s.floors if abs(c[0] - 1) + abs(c[1] - 1) >= 8]       # красные глаза во тьме коридоров
        random.shuffle(far)
        self.eyes = [{"x": (c[0] + 0.5) * TILE, "y": (c[1] + 0.5) * TILE, "ph": random.uniform(0, 7), "alive": True} for c in far[:(0 if self.s.plan.get("safe") else 5)]]
        self.flick_t = 0.0
        self.flick_depth = 0
        self.jit = 0
        self.jit_t = 0.0
        self.heart_t = 0.0
        self.pulse = 0.0
        self.shake = (0, 0)
        self.danger = 0.0
        self.dust = []
        for _ in range(420):
            fx, fy = random.choice(self.s.floors)
            self.dust.append([fx * TILE + random.uniform(0, TILE), fy * TILE + random.uniform(0, TILE),
                              random.uniform(-6, 6), random.uniform(-6, 6), random.uniform(0, 6.28)])

    def update(self, dt):
        """Настроение этажа: опасность, пульс, дрожь, мерцание ламп, шаги, скрипы, пыль."""
        p, m = self.s.player, self.s.monster
        d = math.hypot(m.x - p.x, m.y - p.y) if m.active else 1e9           # нет монстра — нет опасности, шагов и дыхания
        self.glitch_t = max(0.0, self.glitch_t - dt)
        self.seen_cd = max(0.0, self.seen_cd - dt)
        vis = (d < 430 and p.light_on and p.battery > 0 and not self.s.hidden
               and abs(angle_diff(math.atan2(m.y - p.y, m.x - p.x), p.angle)) < 0.75
               and line_clear(self.s.grid, p.x, p.y, m.x, m.y))
        if vis and not self.was_vis and self.seen_cd <= 0:        # монстр вдруг вышел из тьмы прямо в луч
            self.s.emit("monster_seen")
            self.glitch_t = 0.45
            self.seen_cd = 9.0
        self.was_vis = vis
        for e in self.eyes:                                         # наблюдатели исчезают, стоит подойти
            if e["alive"] and math.hypot(e["x"] - p.x, e["y"] - p.y) < 130:
                e["alive"] = False
                self.s.emit("watcher")
                self.glitch_t = max(self.glitch_t, 0.3)
        self.danger = clamp(1 - d / 520, 0, 1)
        if m.state == "chase":
            self.danger = max(self.danger, 0.35)

        # --- пульс, дрожь камеры
        self.pulse = max(0.0, self.pulse - dt * 3)
        if self.danger > 0.12:
            self.heart_t -= dt
            if self.heart_t <= 0:
                self.audio.play("heart")
                self.pulse = 1.0
                self.heart_t = 1.15 - 0.75 * self.danger
        amp = 7 * self.danger ** 2 + (2.0 if m.state == "chase" else 0) + 3.0 * self.pulse * self.danger
        if self.cfg.gentle:
            amp *= 0.35
        self.shake = (random.uniform(-amp, amp), random.uniform(-amp, amp)) if amp > 0.2 else (0, 0)

        # --- мерцание лампы (чаще при низком заряде и рядом с монстром)
        if self.flick_t > 0:
            self.flick_t -= dt
        else:
            rate = 0.12 + (1.8 if p.battery < 25 else 0) * (1 - p.battery / 25 if p.battery < 25 else 0) \
                + self.danger * 2.2
            if random.random() < rate * dt * (0.3 if self.cfg.gentle else 1.0):
                self.flick_t = random.uniform(0.04, 0.3)
                self.flick_depth = 99 if random.random() < 0.3 else random.randint(3, 9)
        self.jit_t -= dt
        if self.jit_t <= 0:
            self.jit = random.choice((-1, 0, 0, 0, 1))
            self.jit_t = 0.08


        # --- шаги, скрипы, сирена
        if p.moving:
            self.step_t -= dt
            if self.step_t <= 0:
                metal = self.s.plan.get("metal")                 # железный пол звучит иначе
                snd = ("step_metal" if self.step_alt else "step_metal2") if metal else ("step" if self.step_alt else "step2")
                self.audio.play(snd, vol=0.55 if p.sprinting else 0.28)
                self.step_alt = not self.step_alt
                self.step_t = 0.26 if p.sprinting else 0.42
        if d < 650 and m.state != "search":
            self.mstep_t -= dt
            if self.mstep_t <= 0:
                self.audio.play("mstep", vol=clamp(1 - d / 650, 0.04, 1.0) ** 1.4)
                self.mstep_t = 0.42 if m.state == "chase" else 0.8
        self.breath_t -= dt
        if d < 340 and m.state != "chase" and self.breath_t <= 0:       # слышно дыхание рядом
            self.audio.play("breath", vol=clamp(1 - d / 340, 0.1, 1.0))
            self.breath_t = random.uniform(1.8, 3.0)
        self.creak_t -= dt
        if self.creak_t <= 0:
            amb = random.choice(("creak", "creak", "bang") if self.s.plan.get("safe") else ("creak", "creak", "whisper", "bang", "scratch", "roar"))
            self.audio.play(amb, vol=0.16 if amb == "roar" else random.uniform(0.2, 0.55))     # «roar» — далёкий рёв
            if amb == "whisper":
                self.s.emit("whisper")                     # монстр шепчет имя героя — реплика появится на экране
            self.creak_t = random.uniform(14, 34)

        # --- пыль
        for q in self.dust:
            q[4] += dt
            q[0] += (q[2] + math.sin(q[4] * 0.8) * 5) * dt
            q[1] += (q[3] + math.cos(q[4] * 0.7) * 5) * dt
            if q[0] < 0 or q[0] > WW or q[1] < 0 or q[1] > WH:
                q[0], q[1] = min(max(q[0], 0), WW), min(max(q[1], 0), WH)
                q[2], q[3] = -q[2], -q[3]


class PlayerController:
    """Управление игроком (ответственность: движение, стамина, шум, поворот фонаря)."""
    def __init__(self, camera, s):
        self.camera = camera
        self.s = s

    def update(self, dt, ix, iy, sprint, mouse_pos, mouse_recent):
        """Движение с коллизиями, стамина, шум и прицеливание фонаря (ввод приходит параметрами)."""
        p = self.s.player
        if self.s.hidden:
            ix = iy = 0
        p.moving = ix != 0 or iy != 0
        want_sprint = sprint and p.moving and not p.exhausted
        p.sprinting = bool(want_sprint)
        if p.sprinting:
            p.stamina -= 38 * dt
            p.regen_wait = 0.8
            if p.stamina <= 0:
                p.stamina, p.exhausted = 0.0, True
                p.sprinting = False
        else:
            p.regen_wait = max(0.0, p.regen_wait - dt)
            if p.regen_wait <= 0:
                p.stamina = min(100.0, p.stamina + 17 * dt)
            if p.exhausted and p.stamina > 30:
                p.exhausted = False
        speed = 255 if p.sprinting else 165
        if p.moving:
            n = math.hypot(ix, iy)
            vx, vy = ix / n * speed, iy / n * speed
            p.x += vx * dt
            p.y += vy * dt
            p.x, p.y = push_out(self.s.grid, p.x, p.y, p.r)
            p.x, p.y = push_out(self.s.grid, p.x, p.y, p.r)
        # шум: бег — громко, шаги — тихо, стояние — бесшумно
        p.noise = 400 if p.sprinting else (150 if p.moving else 0)

        # --- направление фонаря: мышь (если двигалась недавно) или по ходу движения
        mx, my = mouse_pos
        camx, camy = self.camera.base()
        if self.s.hidden:
            target = math.pi / 2
        elif mouse_recent:
            target = math.atan2(my - (p.y - camy), mx - (p.x - camx))
        elif p.moving:
            target = math.atan2(iy, ix)
        else:
            target = p.angle
        p.angle += angle_diff(target, p.angle) * min(1.0, dt * 14)


class Flashlight:
    """Фонарик (ответственность: заряд, переключатель, уровень света с учётом мерцания)."""
    def __init__(self, atmo, audio, note, s):
        self.atmo = atmo
        self.audio = audio
        self.note = note
        self.s = s

    def update(self, dt):
        """Расход заряда батареи и предупреждения о низком заряде."""
        p = self.s.player
        # --- батарея
        if p.light_on and p.battery > 0:
            p.battery -= self.s.dc["drain"] * dt
            if p.battery <= 0:
                p.battery, p.light_on = 0.0, False
                self.note.say("Фонарик погас! Ищи батарейки...", 3.5)
            elif p.battery < 15 and not self.s.low_warned:
                self.s.low_warned = True
                self.note.say("Заряд на исходе!", 2.0)
                self.audio.play("beep")
                self.s.emit("low_battery")
        if p.battery > 20:
            self.s.low_warned = False

    def toggle(self):
        p = self.s.player
        if p.battery > 0:
            p.light_on = not p.light_on
            self.audio.play("click")
        else:
            self.note.say("Батарейка села...", 2.0)

    def state(self):
        """Возвращает (уровень света или None, дальность лучей) с учётом заряда и мерцания."""
        p = self.s.player
        if not p.light_on or p.battery <= 0:
            return None, AMB_R + 30
        frac = p.battery / 100.0
        r = 120 + (LMAX - 120) * frac ** 0.6
        lvl = int((r - LMIN) / (LMAX - LMIN) * (NL - 1) + 0.5)
        lvl += self.atmo.jit if p.battery < 40 else 0
        if self.atmo.flick_t > 0:
            lvl = -1 if self.atmo.flick_depth >= 99 else lvl - self.atmo.flick_depth
        if lvl < 0:
            return None, AMB_R + 30
        lvl = int(clamp(lvl, 0, NL - 1))
        return lvl, LMIN + (LMAX - LMIN) * lvl / (NL - 1)


class ThreatSystem:
    """Угроза (ответственность: обновление монстра и проверка поимки)."""
    def __init__(self, s):
        self.s = s

    def update(self, dt):
        """Двигает монстра и фиксирует поимку (сам игрок и звук его не интересуют)."""
        s = self.s
        p, m = s.player, s.monster
        m.update(s, dt)
        s.lure = None                      # приманка действует один кадр
        if s.grace > 0:
            s.grace -= dt
        d = math.hypot(m.x - p.x, m.y - p.y)
        if m.active and ((d < p.r + m.r + 2 and not s.hidden) or s.pending_catch) and s.grace <= 0:
            s.emit("caught")               # дальше — схватка (StruggleFight), а при проигрыше — скример


class PickupSystem:
    """Предметы (ответственность: подбор ключей/батареек/бутылок, проверка выхода)."""
    def __init__(self, audio, note, s):
        self.audio = audio
        self.note = note
        self.s = s

    def update(self, dt):
        """Подбор ключей, батареек, бутылок, записок и проверка двери выхода."""
        s = self.s
        p = s.player
        need = s.keys_needed
        for it in s.bats:
            if it["alive"] and math.hypot(it["x"] - p.x, it["y"] - p.y) < 24:
                it["alive"] = False
                p.battery = min(100.0, p.battery + 35)
                self.audio.play("pickup")
                self.note.say("Батарейка: +35% заряда", 2.5)
        for it in s.keys:
            if it["alive"] and math.hypot(it["x"] - p.x, it["y"] - p.y) < 24:
                it["alive"] = False
                p.keys += 1
                s.emit("key", p.keys)
                self.audio.play("key")
                self.note.say("Ключ найден: %d / %d" % (p.keys, need) + ("  —  беги к лифту!" if p.keys == need else ""), 3.5)
                if p.keys == need:
                    s.emit("third_key")
        for it in s.botts:
            if it["alive"] and math.hypot(it["x"] - p.x, it["y"] - p.y) < 24:
                it["alive"] = False
                s.bottles = min(6, s.bottles + 1)
                self.audio.play("pickup")
                self.note.say("Бутылка: Q или ПКМ — бросить и отвлечь монстра", 3.0)
        for it in s.notes:
            if it["alive"] and math.hypot(it["x"] - p.x, it["y"] - p.y) < 24:
                it["alive"] = False
                self.audio.play("rustle")
                s.notes_read.add((s.floor, it["idx"]))
                s.emit("note", (s.floor, it["idx"]))

        for it in s.dynamite:                              # секретный этаж: динамит и завал
            if it["alive"] and math.hypot(it["x"] - p.x, it["y"] - p.y) < 26:
                it["alive"] = False
                s.has_dynamite = True
                self.audio.play("pickup")
                self.note.say("ДИНАМИТ! Занеси его к завалу — взрыв пробьёт путь на поверхность", 4.0)
                s.emit("dynamite")
        s.blast_warn = max(0.0, s.blast_warn - dt)
        if s.blast_cell is not None:
            bx, by = (s.blast_cell[0] + 0.5) * TILE, (s.blast_cell[1] + 0.5) * TILE
            if math.hypot(bx - p.x, by - p.y) < 36:
                if s.has_dynamite:
                    s.emit("secret_blast")
                elif s.blast_warn <= 0:
                    self.note.say("Завал. Нужна взрывчатка — динамит где-то на этом этаже", 3.0)
                    s.blast_warn = 3.0
                    s.emit("blast_seen")

        for it in s.antidote:                              # аванпост: антидот доктора Вейры
            if it["alive"] and math.hypot(it["x"] - p.x, it["y"] - p.y) < 26:
                it["alive"] = False
                s.has_antidote = True
                self.audio.play("pickup")
                self.note.say("АНТИДОТ! Единственный шанс вернуть Томасу человеческий облик", 4.0)
                s.emit("antidote")
        for it in s.serum:                                 # ампула сыворотки: предлагает выбор
            if it["alive"] and not it.get("asked") and math.hypot(it["x"] - p.x, it["y"] - p.y) < 28:
                it["asked"] = True
                s.emit("serum_offer")
        s.console_warn = max(0.0, s.console_warn - dt)
        if s.console_cell is not None and s.evac_t is None and not s.evac_done:
            cx_, cy_ = (s.console_cell[0] + 0.5) * TILE, (s.console_cell[1] + 0.5) * TILE
            if math.hypot(cx_ - p.x, cy_ - p.y) < 38:
                if p.keys >= 1:                            # ключ-карта оператора есть — вызов эвакуации
                    s.evac_t = EVAC_TIME
                    s.emit("evac_start")
                elif s.console_warn <= 0:
                    self.note.say("Консоль мертва. Нужна ключ-карта оператора (хотя бы один ключ)", 3.0)
                    s.console_warn = 3.0
                    s.emit("console_seen")

        # --- дверь лифта: плавно открывается, когда собраны все ключи
        was_open = s.exit_open
        s.exit_open = clamp(s.exit_open + (dt * 1.2 if p.keys >= need else -dt * 2.0), 0.0, 1.0)
        if was_open <= 0.0 < s.exit_open:                  # створки лифта поехали
            self.audio.play("door")
            self.audio.play("ding", vol=0.6)
        ex, ey = (s.exit_cell[0] + 0.5) * TILE, (s.exit_cell[1] + 0.5) * TILE
        s.exit_warn = max(0.0, s.exit_warn - dt)
        if math.hypot(ex - p.x, ey - p.y) < 30:
            if p.keys >= need:
                nxt = s.plan["next"]
                if nxt is None:
                    s.finish_time = s.play_time
                    s.emit("exit_reached")
                else:
                    s.emit("floor_cleared", nxt)
            elif s.exit_warn <= 0:
                self.note.say("Дверь заперта. Нужно ключей: %d (есть %d)" % (need, p.keys), 2.5)
                s.exit_warn = 2.6


class StealthSystem:
    """Скрытность и отвлечение (ответственность: шкафчики, бутылки, сирена)."""
    def __init__(self, audio, note, s):
        self.audio = audio
        self.note = note
        self.s = s

    def try_hide(self):
        """E: спрятаться в шкафчик / выйти. Внутри монстр не видит и не слышит, но может заглянуть."""
        p, m = self.s.player, self.s.monster
        if self.s.hidden:
            self.s.hidden = False
            self.s.hid_L = None
            self.audio.play("clunk")
            return
        near, bd = None, 46
        for L in self.s.lockers:
            d = math.hypot(L["x"] - p.x, L["y"] - p.y)
            if d < bd:
                near, bd = L, d
        if near is None:
            return
        dm = math.hypot(m.x - p.x, m.y - p.y)
        if m.state == "chase" and dm < 420 and line_clear(self.s.grid, m.x, m.y, p.x, p.y):
            self.note.say("Он смотрит прямо на тебя!", 2.0)
            return
        self.s.hidden = True
        self.s.hid_L = near
        self.s.stats["lockers"] += 1
        self.s.emit("hide")
        p.x, p.y = near["x"], near["y"]
        self.s.locker_risk = random.random() < 0.4
        self.s.locker_timer = 0.0
        self.audio.play("clunk")

    def throw_bottle(self):
        """Q / ПКМ: бросок бутылки по лучу фонарика. Разбившись, она шумит — монстр идёт проверять."""
        p = self.s.player
        if self.s.hidden:
            return
        if self.s.bottles <= 0:
            self.note.say("Бутылок нет", 1.5)
            return
        ca, sa = math.cos(p.angle), math.sin(p.angle)
        d, hit = cast_dir(self.s.grid, p.x, p.y, ca, sa, 300)
        d = max(40.0, d - 16) if hit else 300.0
        self.s.bottles -= 1
        self.s.stats["bottles"] += 1
        self.s.emit("throw")
        self.s.thrown.append({"x0": p.x, "y0": p.y, "tx": p.x + ca * d, "ty": p.y + sa * d, "t": 0.0, "life": 0.55})
        self.audio.play("whoosh", vol=0.6)

    def trigger_alarm(self):
        """Третий ключ включает сирену: монстр идёт на звук."""
        p, m = self.s.player, self.s.monster
        if not m.active:                                  # сирена зовёт монстра, а его здесь нет
            return
        self.s.alarm_t = 10.0
        self.audio.play("alarm", 4)
        if m.state != "chase":
            m.state = "investigate"
            m.set_goal(self.s, int(p.x // TILE), int(p.y // TILE))
        self.note.say("СИРЕНА! Монстр идёт на звук — беги к выходу!", 4.0)

    def update(self, dt):
        """Полёт брошенных бутылок и обратный отсчёт сирены."""
        keep = []
        for b in self.s.thrown:
            b["t"] += dt
            if b["t"] >= b["life"]:
                self.audio.play("glass", vol=0.85)
                self.s.lure = (b["tx"], b["ty"])
            else:
                keep.append(b)
        self.s.thrown = keep
        if self.s.alarm_t > 0:
            self.s.alarm_t -= dt


class Cheats:
    """Читы (ответственность: F9 / F10, ничего больше)."""
    def __init__(self, note, s):
        self.note = note
        self.s = s

    def boost(self):
        """F9 (чит): все ключи, полный заряд, телепорт к двери выхода."""
        p = self.s.player
        self.s.cheated = True
        for it in self.s.keys:
            it["alive"] = False
        p.keys = self.s.keys_needed
        for it in self.s.dynamite:
            it["alive"] = False
            self.s.has_dynamite = True
        p.battery, p.light_on = 100.0, True
        self.s.hidden, self.s.hid_L = False, None
        ex, ey = self.s.exit_cell
        for dx, dy in DIRS:
            if self.s.grid[ey + dy][ex + dx] == 0:
                p.x, p.y = (ex + dx + 0.5) * TILE, (ey + dy + 0.5) * TILE
                break
        self.note.say("ЧИТ: все ключи, полный заряд, ты у двери", 3.0)

    def floor(self):
        """F8: перейти на следующий этаж (на последнем — сразу к выходу)."""
        s = self.s
        s.cheated = True
        if s.plan["next"] is not None:
            s.emit("floor_cleared", s.plan["next"])
        else:
            s.finish_time = s.play_time
            s.emit("exit_reached")

    def win(self):
        """F10: мгновенное прохождение — сразу финальная кат-сцена."""
        self.s.cheated = True
        self.s.finish_time = self.s.play_time
        self.s.emit("exit_reached")


class Minimap:
    """Миникарта (ответственность: хранение открытых клеток и её отрисовка)."""
    def __init__(self, clock, s, screen):
        self.clock = clock
        self.s = s
        self.screen = screen
        self.mm = None
        self.explored = set()
        self.last_cell = None


    def reset(self):
        self.mm = pygame.Surface((GW * MM, GH * MM), pygame.SRCALPHA)
        self.mm.fill((0, 0, 0, 120))
        self.explored = set()
        self.last_cell = None

    def update(self):
        """Открывает клетки вокруг игрока (туман войны)."""
        p = self.s.player
        cell = (int(p.x // TILE), int(p.y // TILE))
        if cell != self.last_cell:
            self.last_cell = cell
            self.explore(*cell)

    def mark(self, x, y):
        if 0 <= x < GW and 0 <= y < GH and (x, y) not in self.explored:
            self.explored.add((x, y))
            col = (34, 40, 46, 235) if self.s.grid[y][x] else (90, 104, 112, 235)
            pygame.draw.rect(self.mm, col, (x * MM, y * MM, MM, MM))

    def explore(self, cx, cy):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                self.mark(cx + dx, cy + dy)
        for dx, dy in DIRS:
            x, y = cx, cy
            for _ in range(8):
                x += dx
                y += dy
                self.mark(x, y)
                self.mark(x + dy, y + dx)
                self.mark(x - dy, y - dx)
                if self.s.grid[y][x]:
                    break

    def draw(self, mx, my):
        p, scr = self.s.player, self.screen
        scr.blit(self.mm, (mx, my))
        pygame.draw.rect(scr, (90, 90, 90), (mx - 1, my - 1, GW * MM + 2, GH * MM + 2), 1)
        if self.s.exit_cell in self.explored:
            pygame.draw.rect(scr, (60, 220, 90) if p.keys >= self.s.keys_needed else (220, 50, 40),
                             (mx + self.s.exit_cell[0] * MM - 1, my + self.s.exit_cell[1] * MM - 1, MM + 2, MM + 2))
        if int(self.clock.t * 3) % 2 == 0:
            pygame.draw.rect(scr, (255, 255, 255), (mx + int(p.x / TILE * MM) - 1, my + int(p.y / TILE * MM) - 1, 3, 3))


class TextRenderer:
    """Текст (ответственность: шрифты, кэш отрисованных строк, вывод с тенью)."""
    def __init__(self, screen):
        self.screen = screen
        names = "dejavusansmono,couriernew,consolas,liberationmono,menlo,monospace"
        self.f_title = pygame.font.SysFont(names, 92, bold=True)
        self.f_big = pygame.font.SysFont(names, 44, bold=True)
        self.f_mid = pygame.font.SysFont(names, 26, bold=True)
        self.f_small = pygame.font.SysFont(names, 17, bold=True)
        self.txt_cache = {}


    def _cached(self, font, s, color):
        key = (id(font), s, color)
        r = self.txt_cache.get(key)
        if r is None:
            if len(self.txt_cache) > 400:
                self.txt_cache.clear()
            r = font.render(s, True, color)
            self.txt_cache[key] = r
        return r

    @staticmethod
    def wrap(font, s, width):
        """Разбивает текст на строки не шире width пикселей."""
        lines, cur = [], ""
        for w in s.split(" "):
            test = (cur + " " + w).strip()
            if font.size(test)[0] <= width or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def draw_text(self, font, s, color, pos, center=True, shadow=True):
        img = self._cached(font, s, color)
        rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
        if shadow:
            sh = self._cached(font, s, (0, 0, 0))
            self.screen.blit(sh, rect.move(2, 2))
        self.screen.blit(img, rect)


class Camera:
    """Камера (ответственность: положение окна в мире, дрожь)."""
    def __init__(self, atmo, s):
        self.atmo = atmo
        self.s = s

    def base(self):
        p = self.s.player
        return (int(clamp(p.x - SW / 2, 0, WW - SW)), int(clamp(p.y - SH / 2, 0, WH - SH)))

    def view(self):
        p = self.s.player
        cx = int(clamp(p.x - SW / 2 + self.atmo.shake[0], 0, WW - SW))
        cy = int(clamp(p.y - SH / 2 + self.atmo.shake[1], 0, WH - SH))
        return cx, cy


class WorldPainter:
    """Художник мира (ответственность: сборка поверхности уровня из текстур)."""
    def __init__(self, tex):
        self.tex = tex

    def render(self, grid, gw, gh, blood=24):
        """Собирает поверхность мира из процедурных тайлов + тени у стен + кромки + кровь."""
        world = pygame.Surface((gw * TILE, gh * TILE))
        for y in range(gh):
            for x in range(gw):
                tile = random.choice(self.tex.wall_tiles) if grid[y][x] else random.choice(self.tex.floor_tiles)
                world.blit(tile, (x * TILE, y * TILE))

        # крупная «грязь»: плавный шум умножается на весь мир — убирает видимое повторение тайлов
        dirt = pygame.transform.smoothscale(make_noise_gray(gw * 3, gh * 3), (gw * TILE, gh * TILE))
        dirt.fill((85, 85, 85), special_flags=pygame.BLEND_RGB_MULT)
        dirt.fill((170, 170, 170), special_flags=pygame.BLEND_RGB_ADD)
        world.blit(dirt, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        def wall(x, y):
            return x < 0 or y < 0 or x >= gw or y >= gh or grid[y][x] == 1

        ao, h = self.tex.ao, self.tex.ao["h"]
        for y in range(gh):
            for x in range(gw):
                px, py = x * TILE, y * TILE
                if grid[y][x] == 0:
                    # тень от стен на полу
                    if wall(x, y - 1):
                        world.blit(ao["top"], (px, py))
                    if wall(x, y + 1):
                        world.blit(ao["bottom"], (px, py + TILE - h))
                    if wall(x - 1, y):
                        world.blit(ao["left"], (px, py))
                    if wall(x + 1, y):
                        world.blit(ao["right"], (px + TILE - h, py))
                else:
                    # светлая кромка стены, обращённая к проходу
                    rim, dark = (104, 110, 120), (14, 14, 16)
                    if not wall(x, y + 1):
                        pygame.draw.rect(world, rim, (px, py + TILE - 3, TILE, 2))
                        pygame.draw.rect(world, dark, (px, py + TILE - 1, TILE, 1))
                    if not wall(x, y - 1):
                        pygame.draw.rect(world, rim, (px, py + 1, TILE, 2))
                        pygame.draw.rect(world, dark, (px, py, TILE, 1))
                    if not wall(x - 1, y):
                        pygame.draw.rect(world, rim, (px + 1, py, 2, TILE))
                        pygame.draw.rect(world, dark, (px, py, 1, TILE))
                    if not wall(x + 1, y):
                        pygame.draw.rect(world, rim, (px + TILE - 3, py, 2, TILE))
                        pygame.draw.rect(world, dark, (px + TILE - 1, py, 1, TILE))
        if blood:
            add_blood(world, grid, blood, gw, gh)
            add_litter(world, grid, gw, gh, 80 if gw > 20 else 22)
        return world


class LightingRenderer:
    """Освещение (ответственность: маски света, тени от стен, слой тьмы, лампы)."""
    def __init__(self, cfg, clock, s, screen):
        self.cfg = cfg
        self.clock = clock
        self.s = s
        self.screen = screen
        hw, hh = SW // LS, SH // LS                 # тьма рендерится в половинном разрешении
        self.dark = pygame.Surface((hw, hh), pygame.SRCALPHA)
        self.light = pygame.Surface((hw, hh), pygame.SRCALPHA)
        self.vis = pygame.Surface((hw, hh), pygame.SRCALPHA)
        self.dark_big = pygame.Surface((SW, SH), pygame.SRCALPHA)
        self.tint = pygame.Surface((hw, hh), pygame.SRCALPHA)
        self.tint_big = pygame.Surface((SW, SH), pygame.SRCALPHA)
        self.masks = {}
        self.amb_mask = radial_surface(AMB_R / LS * 0.9, 1.2)
        self.rmasks = [radial_surface(r / LS, 1.3) for r in (90, 120, 150, 180, 220, 280, 340)]


    def cone_mask(self, level):
        """
        МАСКА ФОНАРИКА (кэшируется по уровню заряда).
        Конус из ~24 вложенных клиньев (мягкий край) × радиальный спад яркости
        + слабое свечение вокруг игрока. Затем размытие сжатием/растяжением.
        Смотрит вправо (+x) — при отрисовке поворачивается на нужный угол.
        """
        m = self.masks.get(level)
        if m is not None:
            return m
        radius_world = LMIN + (LMAX - LMIN) * level / (NL - 1)
        rh = radius_world / LS
        rad = radial_surface(rh, 1.15)
        size = rad.get_width()
        c = size // 2
        cone = pygame.Surface((size, size), pygame.SRCALPHA)
        bands = 24
        for k in range(bands):
            t = k / (bands - 1)
            half = math.radians(CONE_HALF * (1.85 - 1.45 * t))   # от широкого тусклого к узкому яркому
            v = int(255 * (0.10 + 0.90 * t ** 1.2))
            far = rh * 3
            pts = [(c, c)] + [(c + math.cos(-half + 2 * half * j / 4) * far,
                               c + math.sin(-half + 2 * half * j / 4) * far) for j in range(5)]
            pygame.draw.polygon(cone, (v, v, v, v), pts)
        cone.blit(rad, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        amb = radial_surface(AMB_R / LS, 1.0)
        cone.blit(amb, (c - amb.get_width() // 2, c - amb.get_height() // 2), special_flags=pygame.BLEND_RGBA_MAX)
        small = pygame.transform.smoothscale(cone, (size // 2, size // 2))
        cone = pygame.transform.smoothscale(small, (size, size))
        self.masks[level] = cone
        return cone

    def visibility_polygon(self, ox, oy, rng, camx, camy):
        """
        ТЕНИ: из позиции игрока пускаем RAYS лучей по сетке (DDA). Конец каждого луча —
        вершина многоугольника видимости. Всё, что вне него, закрыто стенами.
        """
        pts = []
        grid = self.s.grid
        for i in range(RAYS):
            ca, sa = RAY_COS[i], RAY_SIN[i]
            d, hit = cast_dir(grid, ox, oy, ca, sa, rng)
            if hit:
                d = min(d + EXT, rng + EXT)
            pts.append(((ox + ca * d - camx) / LS, (oy + sa * d - camy) / LS))
        return pts

    def render_darkness(self, hx, hy, angle, level, poly=None, base_alpha=240, extra=None,
                        tint=(160, 115, 50)):
        """
        ДИНАМИЧЕСКОЕ ОСВЕЩЕНИЕ:
          1) берём предрассчитанную маску конуса и поворачиваем по направлению луча,
          2) умножаем на многоугольник видимости (стены отбрасывают тень),
          3) вычитаем результат из сплошного тёмного слоя (BLEND_RGBA_SUB «вырезает» свет),
          4) растягиваем слой из половинного разрешения (smoothscale) — края получаются мягкими.
        """
        light = self.light
        light.fill((0, 0, 0, 0))
        if level is None:
            mask = self.amb_mask
            light.blit(mask, mask.get_rect(center=(int(hx), int(hy))), special_flags=pygame.BLEND_RGBA_ADD)
        else:
            rot = pygame.transform.rotate(self.cone_mask(level), -math.degrees(angle))
            light.blit(rot, rot.get_rect(center=(int(hx), int(hy))), special_flags=pygame.BLEND_RGBA_ADD)
        if extra:                      # дополнительные источники (лампы, вспышки)
            for ex, ey, sf in extra:
                light.blit(sf, sf.get_rect(center=(int(ex), int(ey))), special_flags=pygame.BLEND_RGBA_MAX)
        if poly is not None:
            self.vis.fill((0, 0, 0, 0))
            pygame.draw.polygon(self.vis, (255, 255, 255, 255), poly)
            light.blit(self.vis, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        if self.cfg.quality and tint is not None:
            # ТЁПЛЫЙ ОТТЕНОК ЛУЧА: берём яркость света как альфу, красим в тёплый цвет и подмешиваем до тьмы
            tn = self.tint
            tn.fill((0, 0, 0, 0))
            tn.blit(light, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            tn.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGB_MULT)
            tn.fill((tint[0], tint[1], tint[2], 0), special_flags=pygame.BLEND_RGB_ADD)
            tn.fill((255, 255, 255, 44), special_flags=pygame.BLEND_RGBA_MULT)
            pygame.transform.smoothscale(tn, (SW, SH), self.tint_big)
            self.screen.blit(self.tint_big, (0, 0))
        self.dark.fill((5, 4, 10, base_alpha))
        self.dark.blit(light, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        pygame.transform.smoothscale(self.dark, (SW, SH), self.dark_big)
        self.screen.blit(self.dark_big, (0, 0))

    def lamp_idx(self, L):
        """Индекс радиуса света лампы: -1 выключена, 1..2 — мерцание."""
        t = self.clock.t + L["ph"]
        if L["broken"]:
            v = math.sin(t * 13) + math.sin(t * 7.3) + math.sin(t * 2.1)
            return -1 if v < -1.1 else (1 if v < 0.5 else 2)
        return 2 if math.sin(t * 23) > -0.97 else 1

    def lamp_lights(self, camx, camy):
        """Дополнительные источники света (потолочные лампы) для render_darkness."""
        out = []
        for L in self.s.lamps:
            sx, sy = L["x"] - camx, L["y"] - camy
            if sx < -260 or sx > SW + 260 or sy < -260 or sy > SH + 260:
                continue
            idx = self.lamp_idx(L)
            L["idx"] = idx
            if idx >= 0:
                out.append((sx / LS, sy / LS, self.rmasks[idx]))
        return out


class SpriteRenderer:
    """Спрайты (ответственность: рисование игрока, монстра, предметов, шкафчиков, ламп и свечений)."""
    def __init__(self, atmo, clock, s, screen, tex, text):
        self.atmo = atmo
        self.clock = clock
        self.s = s
        self.screen = screen
        self.tex = tex
        self.text = text
        self.exit_label = self.text.f_small.render("ВЫХОД", True, (210, 220, 210))


    def draw_player(self, sx, sy, target=None, zoom=1.0):
        """
        Игрок: текстурный корпус (рюкзак, куртка, шапка), шагающие ноги в ботинках, рукава, перчатки, фонарик, пистолет.
        zoom > 1 — крупный план (скример, схватка): все размеры растут, корпус берётся из текстуры высокого разрешения.
        """
        z = zoom
        w = lambda v: max(1, int(round(v * z)))
        p, scr = self.s.player, (self.screen if target is None else target)
        ca, sa = math.cos(p.angle), math.sin(p.angle)
        px, py = -sa, ca
        moving = p.moving and not self.s.hidden
        bob = math.sin(self.clock.t * (19 if p.sprinting else 11)) if moving else 0.0
        pygame.draw.circle(scr, (10, 10, 12), (sx + 2 * z, sy + 3 * z), 13 * z)
        for side in (-1, 1):                                       # ботинки: шаг вперёд-назад
            sw = bob * 7 * side * z
            fx, fy = sx + px * 5 * side * z + ca * sw, sy + py * 5 * side * z + sa * sw
            pygame.draw.circle(scr, (16, 18, 22), (fx, fy), 4.5 * z)
            pygame.draw.circle(scr, (46, 50, 58), (fx + ca * 1.5 * z, fy + sa * 1.5 * z), 3 * z)
            pygame.draw.circle(scr, (92, 98, 108), (fx + ca * 2.4 * z - 0.6 * z, fy + sa * 2.4 * z - 0.6 * z), max(1.0, 1 * z))
        breath = 1 + 0.025 * abs(bob)
        tex, kk = (self.tex.player_hi, 0.31 * z * breath) if z > 1.5 else (self.tex.player_base, 0.62 * z * breath)
        body = pygame.transform.rotozoom(tex, -math.degrees(p.angle), kk)
        scr.blit(body, body.get_rect(center=(int(sx), int(sy))))
        hx, hy = sx + ca * 15 * z + px * 6 * z + ca * bob * 1.5 * z, sy + sa * 15 * z + py * 6 * z + sa * bob * 1.5 * z
        pygame.draw.line(scr, (22, 34, 44), (sx + px * 8 * z, sy + py * 8 * z), (hx, hy), w(6))           # рукав с фонариком
        pygame.draw.line(scr, (52, 78, 96), (sx + px * 8 * z, sy + py * 8 * z - 0.8 * z), (hx, hy - 0.8 * z), w(3))
        if z > 1.5:                                                # на крупном плане: светоотражающая полоса и манжета
            mx, my = sx + (hx - sx) * 0.55 + px * 8 * z * 0.45, sy + (hy - sy) * 0.55 + py * 8 * z * 0.45
            pygame.draw.line(scr, (226, 214, 110), (mx - px * 3 * z, my - py * 3 * z), (mx + px * 3 * z, my + py * 3 * z), w(1.6))
            pygame.draw.line(scr, (14, 22, 30), (hx - px * 3.4 * z, hy - py * 3.4 * z), (hx + px * 3.4 * z, hy + py * 3.4 * z), w(1.4))
        pygame.draw.circle(scr, (26, 26, 30), (hx, hy), 3.5 * z)                                       # перчатка
        lit = p.light_on and p.battery > 0
        pygame.draw.line(scr, (44, 46, 52), (hx, hy), (hx + ca * 8 * z, hy + sa * 8 * z), w(5))          # корпус фонаря
        pygame.draw.line(scr, (96, 100, 108), (hx, hy - z), (hx + ca * 8 * z, hy + sa * 8 * z - z), w(1))
        pygame.draw.circle(scr, (255, 244, 200) if lit else (80, 80, 76), (hx + ca * 9 * z, hy + sa * 9 * z), 3 * z)  # линза
        if self.s.has_gun:                                         # пистолет во второй руке
            gx0, gy0 = sx - px * 8 * z, sy - py * 8 * z
            gx1, gy1 = sx - px * 4 * z + ca * 19 * z, sy - py * 4 * z + sa * 19 * z
            pygame.draw.line(scr, (22, 34, 44), (gx0, gy0), (sx - px * 4 * z + ca * 11 * z, sy - py * 4 * z + sa * 11 * z), w(6))
            pygame.draw.circle(scr, (26, 26, 30), (sx - px * 4 * z + ca * 11 * z, sy - py * 4 * z + sa * 11 * z), 3.5 * z)
            pygame.draw.line(scr, (18, 18, 22), (sx - px * 4 * z + ca * 10 * z, sy - py * 4 * z + sa * 10 * z), (gx1, gy1), w(5))
            pygame.draw.line(scr, (120, 120, 128), (gx1 - ca * 3 * z, gy1 - sa * 3 * z), (gx1 + ca * 5 * z, gy1 + sa * 5 * z), w(3))
            pygame.draw.line(scr, (170, 170, 178), (sx - px * 4 * z + ca * 10 * z, sy - py * 4 * z + sa * 10 * z - z), (gx1, gy1 - z), w(1))

    def draw_pickups(self, camx, camy):
        scr, t = self.screen, self.clock.t
        for it in self.s.bats:
            if not it["alive"]:
                continue
            sx, sy = int(it["x"] - camx), int(it["y"] - camy + math.sin(t * 3 + it["ph"]) * 2)
            if -30 < sx < SW + 30 and -30 < sy < SH + 30:
                pygame.draw.rect(scr, (20, 24, 20), (sx - 6, sy - 9, 14, 20), border_radius=2)
                pygame.draw.rect(scr, (60, 190, 90), (sx - 7, sy - 9, 14, 19), border_radius=2)
                pygame.draw.rect(scr, (200, 190, 80), (sx - 3, sy - 12, 6, 3))
                pygame.draw.line(scr, (220, 255, 220), (sx - 4, sy - 5), (sx - 4, sy + 5), 2)
        for it in self.s.keys:
            if not it["alive"]:
                continue
            sx, sy = int(it["x"] - camx), int(it["y"] - camy + math.sin(t * 3 + it["ph"]) * 2)
            if -30 < sx < SW + 30 and -30 < sy < SH + 30:
                pygame.draw.circle(scr, (230, 190, 60), (sx - 5, sy), 6, 3)
                pygame.draw.line(scr, (230, 190, 60), (sx + 1, sy), (sx + 13, sy), 3)
                pygame.draw.line(scr, (230, 190, 60), (sx + 9, sy), (sx + 9, sy + 5), 2)
                pygame.draw.line(scr, (230, 190, 60), (sx + 13, sy), (sx + 13, sy + 4), 2)

    def draw_exit(self, camx, camy):
        """Дверь лифта: створки плавно разъезжаются, когда собраны все ключи."""
        scr = self.screen
        ex, ey = self.s.exit_cell
        x, y = ex * TILE - camx, ey * TILE - camy
        if x < -TILE or y < -TILE or x > SW or y > SH:
            return
        op = self.s.exit_open
        pygame.draw.rect(scr, (44, 50, 56), (x + 3, y + 3, TILE - 6, TILE - 6))
        pygame.draw.rect(scr, (96, 104, 112), (x + 3, y + 3, TILE - 6, TILE - 6), 2)
        for i in range(-TILE, TILE, 12):
            pygame.draw.line(scr, (86, 76, 28), (x + 5 + i, y + TILE - 6), (x + 17 + i, y + 6), 3)
        ix, iy, iw, ih = x + 14, y + 12, TILE - 28, TILE - 24
        pygame.draw.rect(scr, (20, 22, 24), (ix, iy, iw, ih))
        if op > 0:                                                   # свет из кабины лифта
            g = int(120 + 120 * op)
            pygame.draw.rect(scr, (g // 3, g, g // 2), (ix, iy, iw, ih))
        half = int(iw / 2 * (1 - op))
        pygame.draw.rect(scr, (70, 78, 86), (ix, iy, half, ih))
        pygame.draw.rect(scr, (70, 78, 86), (ix + iw - half, iy, half, ih))
        pygame.draw.line(scr, (30, 34, 38), (ix + half, iy), (ix + half, iy + ih), 1)
        lamp = (60, 255, 90) if op > 0.5 else (255, 40, 30)
        pygame.draw.circle(scr, lamp, (x + TILE // 2, y + 9), 4)
        if op < 0.5:
            scr.blit(self.exit_label, self.exit_label.get_rect(center=(x + TILE // 2, y + TILE // 2)))

    def draw_notes(self, camx, camy):
        """Записки с сюжетом: листки, лежащие на полу."""
        scr, t = self.screen, self.clock.t
        for it in self.s.notes:
            if not it["alive"]:
                continue
            sx, sy = int(it["x"] - camx), int(it["y"] - camy + math.sin(t * 2.4 + it["ph"]) * 2)
            if -30 < sx < SW + 30 and -30 < sy < SH + 30:
                pygame.draw.rect(scr, (8, 8, 10), (sx - 7, sy - 8, 16, 20))
                pygame.draw.rect(scr, (206, 198, 170), (sx - 8, sy - 10, 16, 20))
                for i in range(4):
                    pygame.draw.line(scr, (96, 84, 70), (sx - 5, sy - 6 + i * 4), (sx + 5, sy - 6 + i * 4), 1)

    def draw_props(self, camx, camy):
        scr = self.screen
        for it in self.s.botts:
            if not it["alive"]:
                continue
            sx, sy = int(it["x"] - camx), int(it["y"] - camy)
            if -20 < sx < SW + 20 and -20 < sy < SH + 20:
                pygame.draw.rect(scr, (10, 22, 14), (sx - 5, sy - 7, 10, 16), border_radius=3)
                pygame.draw.rect(scr, (60, 150, 86), (sx - 4, sy - 6, 8, 14), border_radius=3)
                pygame.draw.rect(scr, (60, 150, 86), (sx - 2, sy - 12, 4, 6))
                pygame.draw.line(scr, (200, 255, 215), (sx - 2, sy - 4), (sx - 2, sy + 4), 1)
        for L in self.s.lockers:
            sx, sy = int(L["x"] - camx), int(L["y"] - camy)
            if sx < -30 or sx > SW + 30 or sy < -30 or sy > SH + 30:
                continue
            opened = L is self.s.hid_L
            pygame.draw.rect(scr, (14, 16, 18), (sx - 16, sy - 18, 32, 38))
            pygame.draw.rect(scr, (24, 28, 30) if opened else (46, 56, 62), (sx - 15, sy - 17, 30, 34))
            pygame.draw.rect(scr, (86, 98, 106), (sx - 15, sy - 17, 30, 34), 1)
            for i in range(4):
                pygame.draw.line(scr, (18, 22, 24), (sx - 9, sy - 12 + i * 4), (sx + 9, sy - 12 + i * 4), 2)
            pygame.draw.circle(scr, (170, 160, 110), (sx + 9, sy + 8), 2)
        for L in self.s.lamps:
            sx, sy = int(L["x"] - camx), int(L["y"] - camy)
            if sx < -20 or sx > SW + 20 or sy < -20 or sy > SH + 20:
                continue
            on = L.get("idx", 2) >= 0
            pygame.draw.circle(scr, (40, 40, 44), (sx, sy), 8)
            pygame.draw.circle(scr, (250, 230, 170) if on else (70, 64, 58), (sx, sy), 5)

    def draw_thrown(self, camx, camy):
        for b in self.s.thrown:
            k = clamp(b["t"] / b["life"], 0, 1)
            x = b["x0"] + (b["tx"] - b["x0"]) * k - camx
            y = b["y0"] + (b["ty"] - b["y0"]) * k - camy
            h = math.sin(math.pi * k) * 30
            pygame.draw.ellipse(self.screen, (8, 8, 10), (int(x - 4), int(y - 2), 8, 4))
            pygame.draw.circle(self.screen, (120, 200, 140), (int(x), int(y - h)), 4)
            pygame.draw.circle(self.screen, (220, 255, 230), (int(x - 1), int(y - h - 1)), 1)

    def draw_outpost(self, camx, camy):
        """Аванпост: консоль дальней связи, шприц с антидотом, ампула сыворотки."""
        s, scr, t = self.s, self.screen, self.clock.t
        for n in s.npcs:                                   # аванпост: солдаты на постах и Лена у рации
            x, y = n["x"] - camx, n["y"] - camy + math.sin(t * 1.4 + n["x"]) * 1.2
            if -50 < x < SW + 50 and -50 < y < SH + 50:
                if "spr" not in n:                                       # повёрнутую текстуру считаем один раз
                    n["spr"] = pygame.transform.rotozoom(self.tex.persons[n["kind"]], -math.degrees(n["ang"]), 0.46)
                scr.blit(n["spr"], n["spr"].get_rect(center=(int(x), int(y))))
        if s.console_cell is not None:
            x, y = (s.console_cell[0] + 0.5) * TILE - camx, (s.console_cell[1] + 0.5) * TILE - camy
            if -60 < x < SW + 60 and -60 < y < SH + 60:
                x, y = int(x), int(y)
                pygame.draw.rect(scr, (14, 16, 18), (x - 24, y - 18, 48, 36))
                pygame.draw.rect(scr, (60, 68, 76), (x - 22, y - 16, 44, 32))
                pygame.draw.rect(scr, (16, 60, 52), (x - 16, y - 12, 32, 18))
                for i in range(3):
                    pygame.draw.line(scr, (80, 230, 170), (x - 13, y - 9 + i * 5), (x - 13 + 8 + int(9 * abs(math.sin(t * 3 + i))), y - 9 + i * 5), 2)
                pygame.draw.line(scr, (120, 126, 134), (x + 16, y - 16), (x + 22, y - 32), 2)
                lamp = (255, 60, 50) if s.evac_t is not None and int(t * 4) % 2 == 0 else (90, 30, 28)
                pygame.draw.circle(scr, lamp, (x + 22, y - 33), 3)
        for it in s.antidote:
            if it["alive"]:
                x, y = int(it["x"] - camx), int(it["y"] - camy + math.sin(t * 3 + it["ph"]) * 2)
                if -40 < x < SW + 40 and -40 < y < SH + 40:
                    pygame.draw.line(scr, (210, 220, 224), (x - 12, y + 6), (x + 10, y - 6), 7)
                    pygame.draw.line(scr, (90, 220, 230), (x - 8, y + 4), (x + 4, y - 3), 4)
                    pygame.draw.line(scr, (200, 204, 210), (x + 10, y - 6), (x + 18, y - 10), 2)
                    pygame.draw.circle(scr, (240, 250, 255), (x - 14, y + 8), 4)
        for it in s.serum:
            if it["alive"]:
                x, y = int(it["x"] - camx), int(it["y"] - camy + math.sin(t * 2.6 + it["ph"]) * 2)
                if -40 < x < SW + 40 and -40 < y < SH + 40:
                    pygame.draw.rect(scr, (10, 40, 18), (x - 7, y - 9, 14, 20), border_radius=5)
                    pygame.draw.rect(scr, (60, 220, 90), (x - 6, y - 8, 12, 18), border_radius=5)
                    pygame.draw.rect(scr, (40, 44, 40), (x - 3, y - 14, 6, 6))
                    pygame.draw.circle(scr, (20, 70, 30), (x, y + 1), 3)

    def draw_secret(self, camx, camy):
        """Секретный этаж: динамит на полу и завал в тупике (туда нужно донести динамит)."""
        s, scr, t = self.s, self.screen, self.clock.t
        for it in s.dynamite:
            if it["alive"]:
                sx, sy = it["x"] - camx, it["y"] - camy + math.sin(t * 3 + it["ph"]) * 2
                if -40 < sx < SW + 40 and -40 < sy < SH + 40:
                    draw_dynamite(scr, sx, sy, 1.0, t)
        if s.blast_cell is not None:
            bx, by = (s.blast_cell[0] + 0.5) * TILE - camx, (s.blast_cell[1] + 0.5) * TILE - camy
            if -80 < bx < SW + 80 and -80 < by < SH + 80:
                draw_rubble(scr, bx, by, 0.62)
                if s.has_dynamite:                                   # пульсирующий оранжевый маркер
                    pygame.draw.circle(scr, (255, 150, 40), (int(bx), int(by)), int(22 + 5 * math.sin(t * 6)), 2)

    def draw_blast_arrow(self, camx, camy):
        """Когда динамит у тебя, вокруг игрока — оранжевая стрелка к завалу."""
        p, s = self.s.player, self.s
        if not s.has_dynamite or s.blast_cell is None or s.hidden:
            return
        bx, by = (s.blast_cell[0] + 0.5) * TILE, (s.blast_cell[1] + 0.5) * TILE
        a = math.atan2(by - p.y, bx - p.x)
        r = 82 + 4 * math.sin(self.clock.t * 6)
        cx, cy = p.x - camx + math.cos(a) * r, p.y - camy + math.sin(a) * r
        pts = [(cx + math.cos(a) * 10, cy + math.sin(a) * 10), (cx + math.cos(a + 2.5) * 8, cy + math.sin(a + 2.5) * 8),
               (cx + math.cos(a - 2.5) * 8, cy + math.sin(a - 2.5) * 8)]
        pygame.draw.polygon(self.screen, (255, 150, 40), pts)
        pygame.draw.polygon(self.screen, (60, 24, 4), pts, 1)

    def draw_exit_arrow(self, camx, camy):
        """Когда все 3 ключа собраны, вокруг игрока появляется стрелка к выходу."""
        p = self.s.player
        if p.keys < self.s.keys_needed or self.s.hidden:
            return
        ex, ey = (self.s.exit_cell[0] + 0.5) * TILE, (self.s.exit_cell[1] + 0.5) * TILE
        a = math.atan2(ey - p.y, ex - p.x)
        r = 62 + 4 * math.sin(self.clock.t * 6)
        cx, cy = p.x - camx + math.cos(a) * r, p.y - camy + math.sin(a) * r
        pts = [(cx + math.cos(a) * 10, cy + math.sin(a) * 10),
               (cx + math.cos(a + 2.5) * 8, cy + math.sin(a + 2.5) * 8),
               (cx + math.cos(a - 2.5) * 8, cy + math.sin(a - 2.5) * 8)]
        pygame.draw.polygon(self.screen, (70, 230, 110), pts)
        pygame.draw.polygon(self.screen, (10, 40, 16), pts, 1)

    def draw_dust(self, camx, camy):
        """Пылинки в воздухе (видны только там, где есть свет)."""
        scr = self.screen
        for q in self.atmo.dust:
            sx, sy = q[0] - camx, q[1] - camy
            if 0 <= sx < SW and 0 <= sy < SH:
                v = 120 + int(60 * math.sin(q[4] * 2))
                scr.set_at((int(sx), int(sy)), (v, v, v - 10))
                if int(q[4] * 3) % 4 == 0:
                    scr.set_at((int(sx) + 1, int(sy)), (v - 40, v - 40, v - 50))

    def draw_glows(self, camx, camy):
        """Свечение предметов, двери, глаз монстра и ламп поверх тьмы; кольцо шума."""
        p, m, scr = self.s.player, self.s.monster, self.screen
        tt = self.clock.t
        for e in self.atmo.eyes:                           # красные глаза во тьме моргают и следят
            if not e["alive"]:
                continue
            ddx, ddy = e["x"] - p.x, e["y"] - p.y
            if ddx * ddx + ddy * ddy > 700 * 700 or int(tt * 1.3 + e["ph"]) % 7 == 0:
                continue
            if line_clear(self.s.grid, p.x, p.y, e["x"], e["y"]):
                for sd in (-1, 1):
                    gl = self.tex.glow_red
                    scr.blit(gl, gl.get_rect(center=(int(e["x"] - camx + sd * 8), int(e["y"] - camy))))
        for it, glow, lim in [(i, self.tex.glow_key, 520) for i in self.s.keys if i["alive"]] + \
                             [(i, self.tex.glow_bat, 330) for i in self.s.bats if i["alive"]] + \
                             [(i, self.tex.glow_bat, 240) for i in self.s.botts if i["alive"]] + \
                             [(i, self.tex.glow_note, 300) for i in self.s.notes if i["alive"]] + \
                             [(i, self.tex.glow_exit_r, 340) for i in self.s.dynamite if i["alive"]] + \
                             [(i, self.tex.glow_note, 320) for i in self.s.antidote if i["alive"]] + \
                             [(i, self.tex.glow_exit_g, 300) for i in self.s.serum if i["alive"]]:
            d = math.hypot(it["x"] - p.x, it["y"] - p.y)
            if d < lim and line_clear(self.s.grid, p.x, p.y, it["x"], it["y"]):
                k = 0.6 + 0.4 * math.sin(self.clock.t * 4 + it["ph"])
                g = glow.copy()
                g.set_alpha(int(clamp(int(255 * k), 0, 255)))
                scr.blit(g, g.get_rect(center=(it["x"] - camx, it["y"] - camy)))
        ex, ey = (self.s.exit_cell[0] + 0.5) * TILE, (self.s.exit_cell[1] + 0.5) * TILE
        if math.hypot(ex - p.x, ey - p.y) < 420 and line_clear(self.s.grid, p.x, p.y, ex, ey):
            gl = self.tex.glow_exit_g if p.keys >= self.s.keys_needed else self.tex.glow_exit_r
            scr.blit(gl, gl.get_rect(center=(ex - camx, ey - camy)))
        dm = math.hypot(m.x - p.x, m.y - p.y)
        if m.active and dm < 480 and line_clear(self.s.grid, p.x, p.y, m.x, m.y):
            cf, sf = math.cos(m.facing), math.sin(m.facing)
            for side in (-1, 1):
                ex_ = m.x - camx + cf * 13 - sf * 4 * side
                ey_ = m.y - camy + sf * 13 + cf * 4 * side
                scr.blit(self.tex.glow_red, self.tex.glow_red.get_rect(center=(ex_, ey_)))
        # кольцо шума
        if p.noise > 0:
            col = (74, 30, 30) if p.sprinting else (44, 30, 30)
            pygame.draw.circle(scr, col, (int(p.x - camx), int(p.y - camy)), int(p.noise), 1)

        for L in self.s.lamps:                    # тёплое свечение ламп поверх тьмы
            if L.get("idx", -1) < 0:
                continue
            sx, sy = L["x"] - camx, L["y"] - camy
            if -80 < sx < SW + 80 and -80 < sy < SH + 80 and math.hypot(L["x"] - p.x, L["y"] - p.y) < 780 \
                    and line_clear(self.s.grid, p.x, p.y, L["x"], L["y"]):
                gl = self.tex.glow_lamp
                gl.set_alpha(int(clamp(255 if L["idx"] == 2 else 140, 0, 255)))
                scr.blit(gl, gl.get_rect(center=(int(sx), int(sy))))


class PostFX:
    """Постобработка (ответственность: красная пульсация, виньетка, линии, зерно)."""
    def __init__(self, atmo, cfg, clock, s, screen, tex):
        self.atmo = atmo
        self.cfg = cfg
        self.clock = clock
        self.s = s
        self.screen = screen
        self.tex = tex

    def apply(self):
        """Красная пульсация (монстр рядом / сирена), виньетка, линии развёртки, зерно плёнки."""
        scr = self.screen
        a = 0
        if self.atmo.danger > 0.05:
            a = int(210 * self.atmo.danger ** 1.4 * (0.35 + 0.65 * self.atmo.pulse))
        if self.s.alarm_t > 0:
            a = max(a, int(95 * (0.5 + 0.5 * math.sin(self.clock.t * 8))))
        if a > 3:
            self.tex.red_vig.set_alpha(int(clamp(min(a, 255), 0, 255)))
            scr.blit(self.tex.red_vig, (0, 0))
        scr.blit(self.tex.overlay, (0, 0))                      # виньетка + линии развёртки
        if self.cfg.quality:
            scr.blit(random.choice(self.tex.grain), (0, 0))      # зерно киноплёнки
        if self.atmo.glitch_t > 0 and self.cfg.quality:           # «сбой», когда монстр вдруг вышел из тьмы
            screen_glitch(scr, min(1.0, self.atmo.glitch_t * 2.2) * (0.45 if self.cfg.gentle else 1.0), not self.cfg.gentle)


class Hud:
    """HUD (ответственность: полосы заряда/стамины, ключи, время, подсказки, сообщения)."""
    def __init__(self, cfg, clock, minimap, note, s, screen, text):
        self.cfg = cfg
        self.clock = clock
        self.minimap = minimap
        self.note = note
        self.s = s
        self.screen = screen
        self.text = text

    def draw(self):
        p, scr = self.s.player, self.screen
        # заряд фонарика
        frac = p.battery / 100.0
        col = (110, 220, 110) if frac > 0.5 else (230, 200, 70) if frac > 0.2 else (230, 60, 50)
        if frac <= 0.2 and int(self.clock.t * 4) % 2 == 0:
            col = (140, 30, 26)
        self.text.draw_text(self.text.f_small, "ФОНАРИК %d%%" % int(p.battery), (190, 190, 180), (16, 14), False)
        pygame.draw.rect(scr, (10, 10, 12), (14, 36, 184, 16))
        pygame.draw.rect(scr, col, (16, 38, int(180 * frac), 12))
        pygame.draw.rect(scr, (110, 110, 110), (14, 36, 184, 16), 1)
        # выносливость
        sc = (120, 150, 200) if not p.exhausted else (160, 80, 80)
        pygame.draw.rect(scr, (10, 10, 12), (14, 58, 184, 8))
        pygame.draw.rect(scr, sc, (16, 59, int(180 * p.stamina / 100), 6))
        pygame.draw.rect(scr, (90, 90, 90), (14, 58, 184, 8), 1)
        # ключи
        self.text.draw_text(self.text.f_small, "КЛЮЧИ", (190, 190, 180), (16, 76), False)
        for i in range(self.s.keys_needed):
            c = (240, 200, 60) if i < p.keys else (50, 50, 50)
            x = 90 + i * 30
            pygame.draw.circle(scr, c, (x, 86), 6, 3)
            pygame.draw.line(scr, c, (x + 5, 86), (x + 14, 86), 3)
        self.text.draw_text(self.text.f_small, "БУТЫЛКИ %d  [Q]" % self.s.bottles, (190, 190, 180), (16, 104), False)
        self.text.draw_text(self.text.f_small, "ЗАПИСКИ %d/%d  [TAB]" % (len(self.s.notes_read), StoryBook.TOTAL_NOTES),
                            (190, 190, 180), (16, 122), False)
        if self.s.has_dynamite:
            self.text.draw_text(self.text.f_small, "ДИНАМИТ: ЕСТЬ", (255, 170, 80), (16, 140), False)
        # этаж и время
        self.text.draw_text(self.text.f_small, FLOORS[self.s.floor]["name"], (170, 150, 120), (SW // 2, 34))
        tt = int(self.s.play_time)
        self.text.draw_text(self.text.f_small, "%02d:%02d" % (tt // 60, tt % 60), (150, 150, 140), (SW // 2, 14))
        if self.s.evac_t is not None:                      # обратный отсчёт эвакуации
            tl = max(0, int(self.s.evac_t))
            ec = (255, 70, 60) if int(self.clock.t * 3) % 2 == 0 else (200, 40, 40)
            self.text.draw_text(self.text.f_mid, "ЭВАКУАЦИЯ: %02d:%02d" % (tl // 60, tl % 60), ec, (SW // 2, 80))
        # миникарта (туман войны)
        if self.cfg.show_map:
            self.minimap.draw(SW - GW * MM - 12, 12)
        hint = None
        if self.s.hidden:
            hint = "E — выйти из шкафчика"
        else:
            for L in self.s.lockers:
                if math.hypot(L["x"] - p.x, L["y"] - p.y) < 46:
                    hint = "E — спрятаться"
        if hint:
            self.text.draw_text(self.text.f_small, hint, (200, 200, 190), (SW // 2, SH - 74))
        if self.s.alarm_t > 0:
            self.text.draw_text(self.text.f_small, "СИРЕНА!", (240, 60, 50) if int(self.clock.t * 4) % 2 == 0 else (120, 30, 26),
                           (SW // 2, 56))
        # сообщение
        if self.note.msg_t > 0:
            a = clamp(self.note.msg_t / 0.6, 0, 1)
            c = int(210 * a)
            self.text.draw_text(self.text.f_small, self.note.msg, (c, c, int(c * 0.9)), (SW // 2, SH - 40))


class ScreenRenderer:
    """Экраны (ответственность: меню, интро, пауза, поимка, поражение, победа)."""

    def __init__(self, ach, audio, cfg, clock, lighting, s, scores, screen, tex, text):
        self.ach = ach
        self.audio = audio
        self.cfg = cfg
        self.clock = clock
        self.lighting = lighting
        self.s = s
        self.scores = scores
        self.screen = screen
        self.tex = tex
        self.text = text
        # фон меню
        self.menu_bg = pygame.Surface((SW, SH))
        for y in range(0, SH, TILE):
            for x in range(0, SW, TILE):
                self.menu_bg.blit(random.choice(self.tex.wall_tiles), (x, y))
        for _ in range(7):
            x = random.randint(40, SW - 40)
            y0 = random.randint(0, SH // 2)
            for yy in range(y0, y0 + random.randint(120, 400), 3):
                pygame.draw.circle(self.menu_bg, (random.randint(70, 110), 3, 5), (x + random.randint(-1, 1), yy),
                                   random.randint(2, 4))
        self.snapshot = None
        self.retry = False
        self.win_t = 0.0
        self.arch_sel = 0
        self.floor_i = 0
        self.floor_t = 0.0
        self.note_t = 0.0
        self.note_title = self.note_text = ""
        self.fade_t = 0.0
        self.fade_dur = 1.0
        self.fade_surf = pygame.Surface((SW, SH))
        self.fade_surf.fill((0, 0, 0))
        self.lose_t = 0.0
        self.drips = []


    def draw_menu(self):
        scr = self.screen
        scr.blit(self.menu_bg, (0, 0))
        ang = -math.pi / 2 + math.sin(self.clock.t * 0.55) * 0.7
        hx = (SW / 2 + math.sin(self.clock.t * 0.3) * 320) / LS
        hy = (SH * 0.9) / LS
        lvl = 12 if random.random() > 0.03 else 4
        self.lighting.render_darkness(hx, hy, ang, lvl, None, 244)
        self.glitch_title("БУНКЕР-13", self.text.f_title, 190, (200, 20, 20))
        self.text.draw_text(self.text.f_mid, "ПОБЕГ ИЗ ЗАБРОШЕННОЙ ЛАБОРАТОРИИ", (150, 150, 140), (SW // 2, 262))
        lines = ["Найди 3 ключа и добеги до выхода.",
                 "Не попадись тому, кто бродит во тьме.",
                 "",
                 "WASD / СТРЕЛКИ — идти      SHIFT — бежать (ШУМНО)",
                 "МЫШЬ — луч фонаря         F / ЛКМ — вкл/выкл свет",
                 "M — карта                 P / ESC — пауза",
                 "E — шкафчик (прятаться)   ←/→ — сложность",
                 "Q / ПКМ — бутылка   TAB — архив записок   F2 — качество"]
        for i, s in enumerate(lines):
            self.text.draw_text(self.text.f_small, s, (170, 170, 160), (SW // 2, 340 + i * 26))
        if int(self.clock.t * 1.6) % 2 == 0:
            self.text.draw_text(self.text.f_mid, "НАЖМИТЕ  ENTER", (220, 220, 210), (SW // 2, 560))
        self.text.draw_text(self.text.f_mid, "СЛОЖНОСТЬ:  <  %s  >" % DIFFS[self.cfg.diff]["name"], (200, 170, 120), (SW // 2, 610))
        b = self.scores.best[self.cfg.diff]
        if b is not None:
            self.text.draw_text(self.text.f_small, "РЕКОРД: %02d:%02d" % (int(b) // 60, int(b) % 60), (150, 150, 120), (SW // 2, 645))
        self.text.draw_text(self.text.f_small, "ESC — выход", (110, 110, 100), (SW // 2, 676))
        self.text.draw_text(self.text.f_small, "F2 КАЧЕСТВО: %s    F3 ЩАДЯЩИЙ: %s    N ЗВУК: %s    F11 ЭКРАН" % (
            "ВЫСОКОЕ" if self.cfg.quality else "НИЗКОЕ", "ВКЛ" if self.cfg.gentle else "ВЫКЛ",
            "ВЫКЛ" if self.audio.muted else "ВКЛ"), (84, 84, 78), (SW // 2, 704))
        scr.blit(self.tex.overlay, (0, 0))
        scr.blit(random.choice(self.tex.grain), (0, 0))

    def glitch_title(self, text, font, cy, color):
        t = self.clock.t
        jx = random.randint(-4, 4) if random.random() < 0.06 else 0
        for off, c in ((-3, (0, 120, 140)), (3, (160, 0, 0))):
            img = font.render(text, True, c)
            self.screen.blit(img, img.get_rect(center=(SW // 2 + off + jx, cy)))
        k = 0.8 + 0.2 * math.sin(t * 9) if random.random() > 0.04 else 0.35
        img = font.render(text, True, (int(color[0] * k), int(color[1] * k), int(color[2] * k)))
        self.screen.blit(img, img.get_rect(center=(SW // 2 + jx, cy)))

    def draw_pause(self):
        scr = self.screen
        scr.blit(self.snapshot, (0, 0))
        veil = pygame.Surface((SW, SH), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 170))
        scr.blit(veil, (0, 0))
        self.text.draw_text(self.text.f_big, "ПАУЗА", (220, 220, 210), (SW // 2, SH // 2 - 30))
        self.text.draw_text(self.text.f_small, "P / ESC — продолжить      Q — в меню", (150, 150, 140), (SW // 2, SH // 2 + 30))
        self.text.draw_text(self.text.f_small, "ЧИТЫ:  F9 — ключи + телепорт к выходу   F10 — мгновенная победа", (110, 100, 80), (SW // 2, SH // 2 + 70))

    def draw_lose(self, dt):
        scr = self.screen
        self.lose_t += dt
        scr.fill((10, 0, 2))
        for d in self.drips:        # кровь стекает с верхнего края экрана
            d[1] = min(d[2] + 80, d[1] + (50 + d[3] * 6) * dt)
            pygame.draw.line(scr, (96, 4, 8), (d[0], 0), (d[0], d[1]), d[3])
            pygame.draw.circle(scr, (116, 6, 10), (d[0], int(d[1])), d[3] // 2 + 3)
        self.glitch_title("ВЫ ПОГИБЛИ", self.text.f_title, 260, (190, 10, 10))
        self.text.draw_text(self.text.f_mid, "Чудовище разорвало тебя на клочки. Ты стал ещё одной записью в журнале...", (160, 120, 120), (SW // 2, 350))
        self.text.draw_text(self.text.f_small, "%s     Ключей: %d / %d     Время: %d сек" % (FLOORS[self.s.floor]["name"], self.s.player.keys, self.s.keys_needed, int(self.s.play_time)),
                       (160, 150, 150), (SW // 2, 400))
        self.text.draw_text(self.text.f_small, "Шкафчиков: %d    Бутылок брошено: %d" % (self.s.stats["lockers"], self.s.stats["bottles"]),
                       (140, 130, 130), (SW // 2, 440))
        if int(self.clock.t * 1.6) % 2 == 0:
            self.text.draw_text(self.text.f_mid, ("ENTER — повторить бой" if self.retry else "ENTER — ещё раз"), (220, 200, 200), (SW // 2, 500))
        self.text.draw_text(self.text.f_small, "ESC — главное меню", (120, 100, 100), (SW // 2, 550))
        scr.blit(self.tex.overlay, (0, 0))
        scr.blit(random.choice(self.tex.grain), (0, 0))

    def begin_win(self):
        self.win_t = 0.0

    def draw_win(self):
        """Победа: заголовок и эпилог зависят от концовки (normal / kill / spare), текст печатается по буквам."""
        self.win_t += self.clock.dt
        scr = self.screen
        title, col, lines = StoryBook.ENDINGS[self.s.ending]
        scr.fill({"kill": (8, 8, 12), "serum": (18, 4, 4), "evac": (4, 8, 20), "cure": (8, 18, 10), "blast": (20, 11, 4)}.get(self.s.ending, (4, 10, 8)))
        for i in range(9):          # лучи света из открытой двери
            a = -math.pi / 2 + (i - 4) * 0.18 + math.sin(self.clock.t * 0.5 + i) * 0.03
            c = 14 + (i % 3) * 4
            pygame.draw.polygon(scr, (c + (10 if self.s.ending == "spare" else 0), c + 22, c + 12),
                                [(SW // 2, SH + 40),
                                 (SW // 2 + math.cos(a - 0.07) * 1300, SH + 40 + math.sin(a - 0.07) * 1300),
                                 (SW // 2 + math.cos(a + 0.07) * 1300, SH + 40 + math.sin(a + 0.07) * 1300)])
        self.glitch_title(title, self.text.f_title, 120, col)
        chars = max(0.0, self.win_t - 0.8) * 32
        y = 190
        for line in lines:
            for row in self.text.wrap(self.text.f_mid, line, 900):
                n = int(clamp(chars, 0, len(row)))
                if n > 0:
                    self.text.draw_text(self.text.f_mid, row[:n], (176, 200, 184), (SW // 2, y))
                chars -= len(row)
                y += 30
            chars -= 10
            y += 8
        t = int(self.s.finish_time)
        self.text.draw_text(self.text.f_small, "Время побега: %02d:%02d     Записок прочитано: %d / %d" % (
            t // 60, t % 60, len(self.s.notes_read), StoryBook.TOTAL_NOTES), (170, 200, 180), (SW // 2, 540))
        self.text.draw_text(self.text.f_small, "Шкафчиков: %d    Бутылок брошено: %d" % (self.s.stats["lockers"], self.s.stats["bottles"]),
                            (150, 180, 160), (SW // 2, 566))
        self.text.draw_text(self.text.f_small, "Достижения (за эту сессию): %d / %d" % (len(self.ach.unlocked), len(AchievementTracker.LIST)),
                            (214, 176, 90), (SW // 2, 616), True, False)
        if self.s.cheated:
            self.text.draw_text(self.text.f_small, "(пройдено с читом — рекорд не засчитан)", (170, 150, 110), (SW // 2, 592))
        elif self.scores.new_record:
            self.text.draw_text(self.text.f_small, "НОВЫЙ РЕКОРД! (%s)" % DIFFS[self.cfg.diff]["name"], (240, 220, 120), (SW // 2, 592))
        elif self.s.ending == "normal" and not self.s.all_notes_read:
            self.text.draw_text(self.text.f_small, "Прочти все записки (%d) — и в финале появится выбор" % StoryBook.TOTAL_NOTES, (200, 170, 110), (SW // 2, 592))
        if int(self.clock.t * 1.6) % 2 == 0:
            self.text.draw_text(self.text.f_mid, "ENTER — сыграть снова", (210, 235, 215), (SW // 2, 634))
        self.text.draw_text(self.text.f_small, "ESC — главное меню", (100, 130, 110), (SW // 2, 678))
        self.screen.blit(self.tex.overlay, (0, 0))
        self.screen.blit(random.choice(self.tex.grain), (0, 0))

    def begin_serum(self):
        self.capture()

    def draw_serum(self):
        """Ампула сыворотки: выпить (новая концовка) или оставить."""
        scr, tx = self.screen, self.text
        scr.blit(self.snapshot, (0, 0))
        self.fade_surf.set_alpha(195)
        scr.blit(self.fade_surf, (0, 0))
        tx.draw_text(tx.f_title, "АМПУЛА", (110, 230, 140), (SW // 2, 140))
        for i, ln in enumerate(("Зелёная сыворотка «ГЛУБИНА». Записка сержанта: «Не пей. Я выпил — и теперь слышу всех».",
                                "Она делает сильнее. И превращает в то, что бродит по этажам.")):
            tx.draw_text(tx.f_small, ln, (200, 210, 196), (SW // 2, 230 + i * 30))
        blink = 0.75 + 0.25 * math.sin(self.clock.t * 5)
        tx.draw_text(tx.f_big, "[1]  ВЫПИТЬ — стать сильнее", (int(230 * blink), int(100 * blink), int(100 * blink)), (SW // 2, 360))
        tx.draw_text(tx.f_big, "[2]  ОСТАВИТЬ", (int(170 * blink), int(240 * blink), int(180 * blink)), (SW // 2, 430))
        scr.blit(self.tex.overlay, (0, 0))

    def begin_archive(self):
        self.capture()
        self.arch_sel = 0

    def draw_archive(self, items):
        """Архив: слева список найденных записок, справа текст выбранной."""
        scr, tx = self.screen, self.text
        scr.blit(self.snapshot, (0, 0))
        self.fade_surf.set_alpha(225)
        scr.blit(self.fade_surf, (0, 0))
        tx.draw_text(tx.f_big, "АРХИВ ЗАПИСОК   %d / %d" % (len(items), StoryBook.TOTAL_NOTES), (214, 192, 150), (SW // 2, 52))
        sel = int(clamp(self.arch_sel, 0, max(0, len(items) - 1)))
        if not items:
            tx.draw_text(tx.f_mid, "Пока нет ни одной записки. Ищи их в лабиринте.", (150, 150, 140), (SW // 2, SH // 2))
        for i, (fl, idx) in enumerate(items):
            title = StoryBook.NOTES[fl][idx][0]
            on = i == sel
            tx.draw_text(tx.f_small, ("> " if on else "  ") + title, (255, 230, 150) if on else (150, 150, 140),
                         (50, 100 + i * 30), False, on)
        if items:
            fl, idx = items[sel]
            title, body = StoryBook.NOTES[fl][idx]
            r = pygame.Rect(500, 100, 490, 470)
            pygame.draw.rect(scr, (200, 190, 158), r)
            pygame.draw.rect(scr, (120, 104, 78), r, 3)
            tx.draw_text(tx.f_small, title, (110, 22, 22), (r.left + 24, r.top + 22), False, False)
            y = r.top + 66
            for ln in tx.wrap(tx.f_small, body, r.w - 48):
                tx.draw_text(tx.f_small, ln, (52, 40, 30), (r.left + 24, y), False, False)
                y += 28
        tx.draw_text(tx.f_small, "Вверх/вниз — выбрать     ENTER — читать     TAB / ESC — закрыть", (130, 126, 114), (SW // 2, SH - 30))
        scr.blit(self.tex.overlay, (0, 0))

    def capture(self):
        """Запоминает текущий кадр (для паузы и сцены поимки)."""
        self.snapshot = self.screen.copy()

    def begin_lose(self):
        """Кровь стекает с верхнего края экрана поражения."""
        self.drips = [[random.randint(0, SW), random.uniform(0, 60), random.uniform(60, 220), random.randint(3, 9)]
                      for _ in range(60)]
        self.lose_t = 0.0

    def start_fade(self, dur=0.5):
        self.fade_dur, self.fade_t = dur, dur

    def draw_fade(self, dt):
        """Плавное проявление из чёрного после смены экрана."""
        if self.fade_t > 0:
            self.fade_t -= dt
            self.fade_surf.set_alpha(int(clamp(int(255 * clamp(self.fade_t / self.fade_dur, 0, 1)), 0, 255)))
            self.screen.blit(self.fade_surf, (0, 0))

    def begin_floor(self, floor):
        self.floor_i = floor
        self.floor_t = 0.0

    def draw_floor_card(self, dt):
        """Карточка этажа: лифт, название, строка сюжета. Возвращает True, когда пора начинать этаж."""
        self.floor_t += dt
        t = self.floor_t
        scr = self.screen
        plan = FLOORS[self.floor_i]
        scr.fill((3, 3, 5))
        for i in range(9):                                   # полосы света в шахте лифта ползут вверх
            y = (i * 100 - t * 240) % (SH + 100) - 50
            pygame.draw.rect(scr, (11, 13, 16), (0, int(y), SW, 3))
        a = clamp(t / 0.8, 0.0, 1.0)
        c = int(220 * a)
        self.glitch_title(plan["name"], self.text.f_title, 240, (c, int(c * 0.15), int(c * 0.15)))
        g = int(150 * a)
        self.text.draw_text(self.text.f_mid, plan["title"], (g, g, g), (SW // 2, 320))
        chars = (t - 1.0) * 30
        y = 395
        for line in StoryBook.FLOOR_LINES[self.floor_i]:
            for row in self.text.wrap(self.text.f_small, line, 860):
                n = int(clamp(chars, 0, len(row)))
                if n > 0:
                    self.text.draw_text(self.text.f_small, row[:n], (190, 190, 180), (SW // 2, y))
                chars -= len(row)
                y += 26
            chars -= 6
            y += 8
        if t > 5.0:
            self.text.draw_text(self.text.f_small, "Ключей для лифта: %d" % plan["keys"], (200, 170, 90), (SW // 2, 590))
        self.text.draw_text(self.text.f_small, "ENTER — пропустить", (90, 90, 84), (SW // 2, SH - 40))
        scr.blit(self.tex.overlay, (0, 0))
        scr.blit(random.choice(self.tex.grain), (0, 0))
        return t > 10.0

    def begin_note(self, floor, idx):
        self.capture()
        self.note_t = 0.0
        self.note_title, self.note_text = StoryBook.NOTES[floor][idx]

    def draw_note(self, dt):
        """Читаем записку: бумага поверх затемнённого кадра, текст печатается по буквам."""
        self.note_t += dt
        scr = self.screen
        scr.blit(self.snapshot, (0, 0))
        self.fade_surf.set_alpha(200)
        scr.blit(self.fade_surf, (0, 0))
        r = pygame.Rect(SW // 2 - 300, 100, 600, 470)
        pygame.draw.rect(scr, (6, 6, 8), r.move(8, 10))
        pygame.draw.rect(scr, (200, 190, 158), r)
        pygame.draw.rect(scr, (120, 104, 78), r, 3)
        self.text.draw_text(self.text.f_mid, self.note_title, (110, 22, 22), (SW // 2, r.top + 44), True, False)
        pygame.draw.line(scr, (110, 90, 70), (r.left + 40, r.top + 74), (r.right - 40, r.top + 74), 2)
        chars = self.note_t * 34
        y = r.top + 110
        for line in self.text.wrap(self.text.f_small, self.note_text, r.w - 90):
            n = int(clamp(chars, 0, len(line)))
            if n > 0:
                self.text.draw_text(self.text.f_small, line[:n], (52, 40, 30), (r.left + 45, y), False, False)
            chars -= len(line) + 3
            y += 30
        self.text.draw_text(self.text.f_small, "ENTER — закрыть", (96, 78, 58), (SW // 2, r.bottom - 28), True, False)
        scr.blit(self.tex.overlay, (0, 0))
        scr.blit(random.choice(self.tex.grain), (0, 0))


class FinalCutscene:
    """Финальная кат-сцена (ответственность: таймлайн, актёры, обломки, пыль — без рисования)."""
    CS_X, CS_Y = 20, 4          # смещение камеры (комната 19x13 тайлов чуть шире экрана)
    CS_END = 11.0               # конец кат-сцены (дальше начинается бой)
    CS_SUBS = [
        (0.8, 2.9, "Арсенал. На столе — конверт и пистолет."),
        (3.4, 4.5, "Письмо Вейры: «Цельтесь в потолок, Марк.»"),
        (4.7, 5.5, "Что-то бежит за тобой..."),
        (5.5, 6.3, "Его не остановить... ПОТОЛОК!"),
        (6.4, 7.2, "СТЕНА РУХНУЛА!"),
        (7.3, 8.3, "Томас... прости."),
        (8.5, 9.4, "Плита... шевелится?!"),
        (9.5, 10.4, "ОН ВЫБРАЛСЯ!"),
        (10.4, 11.0, "К БОЮ!"),
    ]

    def __init__(self, atmo, audio, cfg, note, s):
        self.atmo = atmo
        self.audio = audio
        self.cfg = cfg
        self.note = note
        self.s = s
        self.grid = None
        self.cs_t = 0.0
        self.cs_ev = set()
        self.cs_debris, self.cs_rubble, self.cs_puffs, self.cs_cracks = [], [], [], []
        self.cs_shake, self.cs_flash, self.cs_prog = 0.0, 0.0, 0.0
        self.cs_buried = False


    def start(self):
        """Готовит состояние финала: комната, трещины, актёры (всё, что не касается рисования)."""
        g = [[1] * GW for _ in range(GH)]
        for y in range(1, 12):
            for x in range(1, 18):
                g[y][x] = 0
        for x in range(1, 18):                 # разделительная стена с проёмом
            g[7][x] = 1
        g[7][8] = g[7][9] = 0
        g[12][8] = g[12][9] = 0                # дверь, через которую вошёл игрок
        self.grid = g
        # трещины в потолке: ломаные от точки попадания пули
        self.cs_cracks = []
        ix, iy = 504.0, 150.0
        for _ in range(11):
            a = random.uniform(0, 6.283)
            x, y = ix, iy
            pts = [(x, y)]
            for _ in range(random.randint(14, 24)):
                a += random.uniform(-0.5, 0.5)
                l = random.uniform(18, 34)
                x += math.cos(a) * l
                y += math.sin(a) * l
                pts.append((x, y))
            self.cs_cracks.append((pts, 0.0))
            for _ in range(random.randint(1, 3)):
                k = random.randint(3, len(pts) - 2)
                bx, by = pts[k]
                ba = a + random.choice((-1, 1)) * random.uniform(0.5, 1.2)
                bp = [(bx, by)]
                for _ in range(random.randint(4, 9)):
                    ba += random.uniform(-0.5, 0.5)
                    l = random.uniform(12, 24)
                    bx += math.cos(ba) * l
                    by += math.sin(ba) * l
                    bp.append((bx, by))
                self.cs_cracks.append((bp, k * 26.0))

        p, m = self.s.player, self.s.monster
        p.x, p.y, p.angle = 504.0, 700.0, -math.pi / 2
        p.light_on, p.battery, p.noise = True, 100.0, 0.0
        m.x, m.y, m.facing, m.state, m.anim = 504.0, 760.0, -math.pi / 2, "chase", 0.0
        self.s.has_gun = False
        self.s.hidden = False
        self.cs_t = 0.0
        self.cs_ev = set()
        self.cs_debris, self.cs_rubble, self.cs_puffs = [], [], []
        self.cs_shake, self.cs_flash, self.cs_prog = 0.0, 0.0, 0.0
        self.cs_buried = False
        self.atmo.shake = (0, 0)
        self.atmo.danger, self.atmo.pulse, self.atmo.heart_t, self.s.alarm_t = 0.0, 0.0, 0.0, 0.0
        self.note.msg_t = 0.0

    def cs_angle(self, t):
        """Куда смотрит игрок: вверх -> разворот к монстру -> рывок стволом вверх -> опускает оружие."""
        up, down = -math.pi / 2, math.pi / 2
        if t < 4.6:
            return up
        if t < 5.1:
            return up + math.pi * (t - 4.6) / 0.5
        if t < 5.45:
            return down
        if t < 5.6:
            return down - math.pi * (t - 5.45) / 0.15
        if t < 7.2:
            return up
        return up + math.pi * clamp((t - 7.2) / 1.0, 0, 1)

    def cs_puff(self, x, y, k=1.0):
        if len(self.cs_puffs) > 130:
            return
        life = random.uniform(1.6, 3.6) * k
        self.cs_puffs.append({"x": x, "y": y, "vx": random.uniform(-26, 26), "vy": random.uniform(-26, 26),
                              "i": random.randint(0, 2), "life": life, "max": life})

    def cs_spawn(self, n, cx, cy, sx, sy, big=False):
        for _ in range(n):
            self.cs_debris.append({"x": cx + random.uniform(-sx, sx), "y": cy + random.uniform(-sy, sy),
                                   "z": random.uniform(260, 520), "vz": 0.0,
                                   "s": random.randint(14, 30) if big else random.randint(7, 20),
                                   "rot": random.uniform(0, 6.28), "delay": random.uniform(0, 0.4)})

    def cs_add_rubble(self, x, y, s):
        if len(self.cs_rubble) > 260:
            return
        n = random.randint(5, 7)
        a0 = random.uniform(0, 6.28)
        pts = [(x + math.cos(a0 + i * 6.283 / n) * s * random.uniform(0.6, 1.1),
                y + math.sin(a0 + i * 6.283 / n) * s * random.uniform(0.6, 1.1)) for i in range(n)]
        gv = random.randint(60, 118)
        self.cs_rubble.append((pts, (gv, gv - 4, gv - 8), (min(255, gv + 50),) * 3))

    def update(self, dt):
        if 5.4 < self.cs_t < 6.1:      # замедление времени вокруг выстрела
            dt *= 0.45
        self.cs_t += dt
        t = self.cs_t
        p, m, ev = self.s.player, self.s.monster, self.cs_ev
        p.angle = self.cs_angle(t)
        p.x = 504.0
        p.y = max(235.0, 700.0 - 155.0 * t)
        if t > 9.5:                                  # отшатывается назад, когда плита лопается
            p.y -= 18 * min(1.0, (t - 9.5) / 0.3)

        if t >= 3.3 and "gun" not in ev:
            ev.add("gun")
            self.s.has_gun = True
            self.audio.play("pickup")
        if t >= 4.6 and "growl" not in ev:
            ev.add("growl")
            self.audio.play("growl")
        if t >= 4.6 and not self.cs_buried and "burst" not in ev:         # монстр несётся по прямой, потом его придавливает
            m.y -= (215.0 if t < 6.1 else 26.0) * dt
            m.x = 504.0 + math.sin(t * 3.0) * 4
            m.facing = -math.pi / 2
            m.anim += dt

        if t >= 5.7 and "shot" not in ev:           # ВЫСТРЕЛ В ПОТОЛОК
            ev.add("shot")
            self.audio.play("shot")
            self.cs_flash = 1.0
            self.cs_shake = max(self.cs_shake, 14)
            for _ in range(14):
                self.cs_puff(504 + random.uniform(-50, 50), 150 + random.uniform(-40, 40), 0.5)
            self.cs_spawn(8, 504, 170, 90, 40)
        if t >= 5.9 and "rumble" not in ev:
            ev.add("rumble")
            self.audio.play("rumble")
        if 5.9 <= t < 6.95:
            self.cs_shake = max(self.cs_shake, 3 + (t - 5.9) * 6)
        if 5.95 <= t < 6.95:                         # сыплются обломки
            if random.random() < 0.8:
                self.cs_spawn(random.randint(1, 3), 504, 410, 150, 70, True)
            if random.random() < 0.3:
                self.cs_spawn(1, 504, 200, 150, 60)

        self.cs_prog = clamp((t - 6.0) / 0.95, 0, 1) ** 2   # плита стены падает с потолка
        if t >= 6.95 and "land" not in ev:
            ev.add("land")
            self.cs_buried = True
            self.audio.play("crash")
            self.cs_shake = 32
            self.cs_flash = 0.55
            self.grid[7][8] = self.grid[7][9] = 1
            for _ in range(70):
                self.cs_puff(random.uniform(340, 670), random.uniform(380, 570), 1.0)
            for _ in range(46):
                self.cs_add_rubble(random.uniform(320, 690), random.uniform(360, 590), random.randint(5, 16))

        if t >= 8.4 and "heave" not in ev:           # плита начинает вздыматься
            ev.add("heave")
            self.audio.play("rumble")
        if 8.4 <= t < 9.5:
            self.cs_shake = max(self.cs_shake, 4 + (t - 8.4) * 9)
            if random.random() < 0.5:
                self.cs_puff(random.uniform(380, 630), random.uniform(380, 500), 0.7)
        if t >= 9.5 and "burst" not in ev:           # МОНСТР ПРОБИВАЕТ ПЛИТУ И ВЫБИРАЕТСЯ
            ev.add("burst")
            self.cs_buried = False
            self.grid[7][8] = self.grid[7][9] = 0
            m.x, m.y = 504.0, 440.0
            self.audio.play("crash")
            self.audio.play("roar")
            self.cs_shake = 36
            self.cs_flash = 0.7
            for _ in range(60):
                self.cs_puff(random.uniform(340, 670), random.uniform(380, 540), 1.0)
            for _ in range(40):
                self.cs_add_rubble(random.uniform(320, 690), random.uniform(360, 590), random.randint(6, 18))
            self.cs_spawn(14, 504, 430, 140, 60, True)
        if "burst" in ev:                            # выбрался и идёт на игрока
            m.facing = -math.pi / 2
            m.anim += dt
            m.y -= (0.0 if t < 10.0 else 110.0) * dt
            m.x = 504.0 + math.sin(t * 3.0) * 4

        # обломки: падение, приземление
        keep = []
        for d in self.cs_debris:
            if d["delay"] > 0:
                d["delay"] -= dt
                keep.append(d)
                continue
            d["vz"] += 900 * dt
            d["z"] -= d["vz"] * dt
            if d["z"] <= 0:
                self.cs_add_rubble(d["x"], d["y"], d["s"] * 0.8)
                self.cs_puff(d["x"], d["y"], 0.6)
                self.cs_shake = max(self.cs_shake, 2 + d["s"] * 0.15)
            else:
                keep.append(d)
        self.cs_debris = keep
        keep = []
        for q in self.cs_puffs:
            q["x"] += q["vx"] * dt
            q["y"] += q["vy"] * dt
            q["vx"] *= max(0.0, 1 - dt * 0.6)
            q["vy"] *= max(0.0, 1 - dt * 0.6)
            q["life"] -= dt
            if q["life"] > 0:
                keep.append(q)
        self.cs_puffs = keep

        self.cs_flash = max(0.0, self.cs_flash - dt * 5)
        self.cs_shake *= max(0.0, 1 - 3.0 * dt)
        a = self.cs_shake * (0.35 if self.cfg.gentle else 1.0)
        self.atmo.shake = (random.uniform(-a, a), random.uniform(-a, a)) if a > 0.3 else (0, 0)

        self.atmo.pulse = max(0.0, self.atmo.pulse - dt * 3)
        if 4.6 <= t < 7.0:
            self.atmo.danger = min(0.9, (t - 4.6) / 1.0)
            self.atmo.heart_t -= dt
            if self.atmo.heart_t <= 0:
                self.audio.play("heart")
                self.atmo.pulse = 1.0
                self.atmo.heart_t = 0.45
        else:
            self.atmo.danger = max(0.0, self.atmo.danger - dt * 0.5)

        if t >= self.CS_END:
            self.s.emit("cutscene_done")


class CutsceneRenderer:
    """Рисование финала (ответственность: комната, плита, трещины, пыль, субтитры, полосы, затемнения)."""
    def __init__(self, atmo, cfg, cut, fx, lighting, monster_view, painter, s, screen, sprites, tex, text):
        self.monster_view = monster_view
        self.atmo = atmo
        self.cfg = cfg
        self.cut = cut
        self.fx = fx
        self.lighting = lighting
        self.painter = painter
        self.s = s
        self.screen = screen
        self.sprites = sprites
        self.tex = tex
        self.text = text
        self.world = None
        self.slab = None
        self.shadow = None
        self.layer = pygame.Surface((SW, SH), pygame.SRCALPHA)
        self.fade = pygame.Surface((SW, SH))


    def prepare(self):
        """Строит визуальные ресурсы финала: комнату из текстур и плиту падающей стены."""
        self.world = self.painter.render(self.cut.grid, 19, 13, 9)
        # плита стены: кладка из тех же процедурных тайлов + трещины
        bricks = pygame.Surface((336, 224))
        for ty in range(4):
            for tx in range(6):
                bricks.blit(random.choice(self.tex.wall_tiles), (tx * TILE, ty * TILE))
        slab = pygame.Surface((336, 200))
        slab.blit(bricks, (0, 0))
        slab.fill((150, 148, 146), special_flags=pygame.BLEND_RGB_MULT)
        for _ in range(10):
            x, y, a = random.uniform(10, 326), random.uniform(10, 190), random.uniform(0, 6.28)
            for _ in range(random.randint(5, 10)):
                a += random.uniform(-0.7, 0.7)
                l = random.uniform(8, 18)
                nx, ny = x + math.cos(a) * l, y + math.sin(a) * l
                pygame.draw.line(slab, (10, 10, 12), (x, y), (nx, ny), 2)
                x, y = nx, ny
        pygame.draw.rect(slab, (16, 16, 18), (0, 0, 336, 200), 4)
        pygame.draw.rect(slab, (120, 124, 130), (4, 4, 328, 192), 1)
        self.slab = slab
        self.shadow = pygame.Surface((336, 200))
        self.shadow.fill((0, 0, 0))

    def draw_slab(self, camx, camy):
        scr = self.screen
        prog = self.cut.cs_prog
        cx, cy = 504 - camx, 472 - camy
        self.shadow.set_alpha(int(clamp(int(170 * prog), 0, 255)))
        scr.blit(self.shadow, (cx - 168, cy - 100))
        if self.cut.cs_buried:
            img = self.slab
            img.set_alpha(255)
        else:
            s = 1.0 + 0.45 * (1 - prog)           # «ближе к камере» = крупнее, пока падает
            img = pygame.transform.smoothscale(self.slab, (int(336 * s), int(200 * s)))
            img.set_alpha(int(clamp(int(70 + 185 * prog), 0, 255)))
        jit = 0.0
        if 8.4 <= self.cut.cs_t < 9.5:                 # плита вздымается и дрожит
            jit = 1.0 + (self.cut.cs_t - 8.4) * 6
        scr.blit(img, img.get_rect(center=(int(cx + random.uniform(-jit, jit)), int(cy + random.uniform(-jit, jit)))))

    def draw_cs_cracks(self, camx, camy):
        t = self.cut.cs_t
        layer = self.layer
        layer.fill((0, 0, 0, 0))
        grow = (t - 5.7) * 900.0
        for pts, off in self.cut.cs_cracks:
            rem = grow - off
            if rem <= 0:
                continue
            for i in range(1, len(pts)):
                ax, ay = pts[i - 1][0] - camx, pts[i - 1][1] - camy
                bx, by = pts[i][0] - camx, pts[i][1] - camy
                seg = math.hypot(bx - ax, by - ay)
                if rem < seg:
                    f = rem / seg
                    bx, by = ax + (bx - ax) * f, ay + (by - ay) * f
                pygame.draw.line(layer, (0, 0, 0, 200), (ax + 1, ay + 1), (bx + 1, by + 1), 3)
                pygame.draw.line(layer, (210, 200, 180, 170), (ax, ay), (bx, by), 1)
                rem -= seg
                if rem <= 0:
                    break
        fade = 1.0 if t < 7.5 else max(0.0, 1 - (t - 7.5) / 1.8)
        layer.set_alpha(int(clamp(int(255 * fade), 0, 255)))
        self.screen.blit(layer, (0, 0))

    def draw(self):
        scr, p, m, t = self.screen, self.s.player, self.s.monster, self.cut.cs_t
        camx = self.cut.CS_X + int(self.atmo.shake[0])
        camy = self.cut.CS_Y + int(self.atmo.shake[1])
        scr.fill((0, 0, 0))
        scr.blit(self.world, (-camx, -camy))
        fcx, fcy = int(clamp(camx, 0, WW - SW)), int(clamp(camy, 0, WH - SH))
        scr.blit(self.tex.fog_world, (0, 0), pygame.Rect(fcx, fcy, SW, SH), pygame.BLEND_RGB_ADD)

        # стол, лампа и пистолет
        tx, ty = 504 - camx, 130 - camy
        pygame.draw.rect(scr, (30, 22, 16), (tx - 64, ty - 22, 128, 50))
        pygame.draw.rect(scr, (86, 64, 44), (tx - 62, ty - 24, 124, 46))
        pygame.draw.rect(scr, (120, 92, 62), (tx - 62, ty - 24, 124, 46), 2)
        pygame.draw.circle(scr, (40, 40, 44), (tx + 46, ty - 4), 9)
        pygame.draw.circle(scr, (240, 220, 160), (tx + 46, ty - 4), 5)
        if not self.s.has_gun:
            pygame.draw.rect(scr, (24, 24, 28), (tx - 16, ty - 10, 30, 9))
            pygame.draw.rect(scr, (24, 24, 28), (tx - 14, ty - 3, 9, 16))
            pygame.draw.line(scr, (110, 110, 118), (tx - 15, ty - 9), (tx + 13, ty - 9), 1)

        burst = "burst" in self.cut.cs_ev
        if t >= 4.6 and (not self.cut.cs_buried or burst):
            self.monster_view.draw(m, camx, camy)
        if t >= 6.0 and not burst:
            self.draw_slab(camx, camy)
        if self.cut.cs_buried and not burst:                     # рука монстра торчит из-под плиты и затихает
            k = max(0.0, 1 - (t - 6.95) / 1.3)
            sw = math.sin(t * 5) * k
            ax, ay = 523 - camx, 372 - camy
            hx, hy = ax + 6 * sw, ay - 26 - 5 * k + 4 * sw
            pygame.draw.line(scr, (92, 82, 76), (ax + 4, ay + 30), (hx, hy), 6)
            pygame.draw.circle(scr, (110, 100, 92), (int(hx), int(hy)), 6)
            for c in (-1, 0, 1):
                pygame.draw.line(scr, (210, 200, 180), (hx, hy), (hx + c * 6 + 2 * sw, hy - 10 - 3 * k), 2)
        for pts, col, hi in self.cut.cs_rubble:
            sp = [(x - camx, y - camy) for x, y in pts]
            pygame.draw.polygon(scr, col, sp)
            pygame.draw.lines(scr, hi, False, sp[:3], 1)
        for d in self.cut.cs_debris:                # падающие обломки: тень на полу + кусок «ближе к камере»
            if d["delay"] > 0:
                continue
            sx, sy = d["x"] - camx, d["y"] - camy
            k = 1 - d["z"] / 520.0
            r = max(2, int(d["s"] * (0.5 + 0.6 * k)))
            pygame.draw.ellipse(scr, (10, 10, 12), pygame.Rect(int(sx - r), int(sy - r * 0.6), r * 2, max(2, int(r * 1.2))))
            hs = d["s"] * (1.0 + (1 - k) * 0.9)
            cy = sy - d["z"] * 0.45
            a0 = d["rot"] + t * 3
            pts = [(sx + math.cos(a0 + i * 1.2566) * hs * f, cy + math.sin(a0 + i * 1.2566) * hs * f)
                   for i, f in enumerate((1.0, 0.7, 0.95, 0.6, 0.85))]
            pygame.draw.polygon(scr, (128, 122, 114), pts)
        psx, psy = int(p.x - camx), int(p.y - camy)
        self.sprites.draw_player(psx, psy)
        if 5.7 <= t < 5.84:                     # вспышка выстрела
            ca, sa = math.cos(p.angle), math.sin(p.angle)
            tipx, tipy = psx + sa * 4 + ca * 25, psy - ca * 4 + sa * 25
            pts = [(tipx + math.cos(i * 0.6283) * (22 if i % 2 == 0 else 8),
                    tipy + math.sin(i * 0.6283) * (22 if i % 2 == 0 else 8)) for i in range(10)]
            pygame.draw.polygon(scr, (255, 240, 170), pts)
            pygame.draw.circle(scr, (255, 255, 255), (int(tipx), int(tipy)), 6)

        # свет: фонарик + лампы комнаты (дёргаются во время обвала)
        lvl = 13
        if t >= 5.7:
            lvl = random.choice((13, 13, 12, 9, 6)) if t < 8.6 else 12
        extras = [((504 - camx) / LS, (140 - camy) / LS, self.lighting.rmasks[3 if math.sin(t * 17) > -0.8 else 2])]
        if t < 5.9:
            di = 4
        elif t < 6.95:
            di = random.choice((4, 3, 2))
        else:
            di = random.choice((1, 1, 0, -1))
        if di >= 0:
            extras.append(((504 - camx) / LS, (390 - camy) / LS, self.lighting.rmasks[di]))
        if 5.7 <= t < 5.85:
            extras.append((psx / LS, psy / LS, self.lighting.rmasks[6]))
        self.lighting.render_darkness(psx / LS, psy / LS, p.angle, lvl, None, 212, extras)

        # свечение пистолета, красные глаза
        if not self.s.has_gun:
            g = self.tex.glow_key
            g.set_alpha(int(clamp(int(150 + 100 * math.sin(t * 5)), 0, 255)))
            scr.blit(g, g.get_rect(center=(int(tx), int(ty))))
        if t >= 4.6 and (not self.cut.cs_buried or burst) and m.y < 740 and line_clear(self.cut.grid, p.x, p.y, m.x, m.y):
            for side in (-1, 1):
                ex_ = m.x - camx - 4 * side
                ey_ = m.y - camy - 13
                scr.blit(self.tex.glow_red, self.tex.glow_red.get_rect(center=(int(ex_), int(ey_))))
        if self.cut.cs_buried and not burst:        # красный свет из-под плиты: затихает, потом разгорается
            k = max(0.0, 1 - (t - 6.95) / 1.6) if t < 8.4 else min(1.0, (t - 8.4) / 1.0)
            g = self.tex.glow_red
            g.set_alpha(int(clamp(int(255 * k * (0.6 + 0.4 * math.sin(t * 14))), 0, 255)))
            scr.blit(g, g.get_rect(center=(int(500 - camx), int(392 - camy))))
            g.set_alpha(255)

        if 5.7 <= t < 9.6:
            self.draw_cs_cracks(camx, camy)
        for q in self.cut.cs_puffs:                 # облака пыли поверх тьмы
            sp = self.tex.dust_sprites[q["i"]]
            sp.set_alpha(int(clamp(int(255 * clamp(q["life"] / q["max"], 0, 1)), 0, 255)))
            scr.blit(sp, sp.get_rect(center=(int(q["x"] - camx), int(q["y"] - camy))))
        for sp in self.tex.dust_sprites:
            sp.set_alpha(255)

        self.fx.apply()
        bar = int(56 * clamp(min(t / 1.2, (self.cut.CS_END - t) / 1.0), 0, 1))     # кинематографичные чёрные полосы
        if bar > 0:
            pygame.draw.rect(scr, (0, 0, 0), (0, 0, SW, bar))
            pygame.draw.rect(scr, (0, 0, 0), (0, SH - bar, SW, bar))
        for a, b, s in self.cut.CS_SUBS:
            if a <= t < b:
                k = min(1.0, (t - a) / 0.25, (b - t) / 0.25)
                c = int(235 * k)
                self.text.draw_text(self.text.f_mid, s, (c, c, int(c * 0.92)), (SW // 2, SH - 28))
        if t > 1.5:
            self.text.draw_text(self.text.f_small, "ENTER — пропустить", (90, 90, 84), (SW - 110, 18))
        fs = self.fade
        if self.cut.cs_flash > 0:
            fs.fill((255, 250, 230))
            fs.set_alpha(int(clamp(int(200 * min(1.0, self.cut.cs_flash) * (0.3 if self.cfg.gentle else 1.0)), 0, 255)))
            scr.blit(fs, (0, 0))
        if t < 1.2:
            fs.fill((0, 0, 0))
            fs.set_alpha(int(clamp(int(255 * (1 - t / 1.2)), 0, 255)))
            scr.blit(fs, (0, 0))
        elif t > self.cut.CS_END - 0.4:             # короткое затемнение перед боем
            fs.fill((0, 0, 0))
            fs.set_alpha(int(clamp(int(255 * clamp((t - (self.cut.CS_END - 0.4)) / 0.4, 0, 1)), 0, 255)))
            scr.blit(fs, (0, 0))


class PlayView:
    """Кадр игры (ответственность: порядок слоёв — мир, туман, спрайты, свет, свечения, HUD)."""
    def __init__(self, atmo, camera, cfg, clock, fx, hud, lighting, monster_view, painter, s, screen, sprites, tex, torch):
        self.monster_view = monster_view
        self.atmo = atmo
        self.camera = camera
        self.cfg = cfg
        self.clock = clock
        self.fx = fx
        self.hud = hud
        self.lighting = lighting
        self.painter = painter
        self.s = s
        self.screen = screen
        self.sprites = sprites
        self.tex = tex
        self.torch = torch
        self.world = None
        self.slit = pygame.Surface((SW * 2, SH * 2), pygame.SRCALPHA)     # щель шкафчика
        self.slit.fill((0, 0, 0, 255))
        pygame.draw.rect(self.slit, (0, 0, 0, 0), (SW - 230, SH - 14, 460, 28))


    def prepare(self):
        """Новый уровень: собирает его картинку из текстур."""
        self.world = self.painter.render(self.s.grid, GW, GH, 24)
        if self.s.rooms:                                    # аванпост: комнаты с обстановкой и подписями
            paint_outpost(self.world, self.s.rooms, self.hud.text.f_small)
        tint = self.s.plan.get("tint")                     # каждый этаж чуть иного цвета: реактор — тёплый, аванпост — холодный
        if tint:
            self.world.fill(tint, special_flags=pygame.BLEND_RGB_MULT)

    def draw(self):
        p, m, scr = self.s.player, self.s.monster, self.screen
        camx, camy = self.camera.view()

        # 1) мир с процедурными текстурами
        scr.blit(self.world, (-camx, -camy))
        # 2) туман (складывается с картинкой — виден только там, где есть свет)
        scr.blit(self.tex.fog_world, (0, 0), pygame.Rect(camx, camy, SW, SH), pygame.BLEND_RGB_ADD)
        fx = int(SW / 2 + (SW / 2 - 2) * math.sin(self.clock.t * 0.07))
        fy = int(SH / 2 + (SH / 2 - 2) * math.sin(self.clock.t * 0.05 + 1.0))
        if self.cfg.quality:
            scr.blit(self.tex.fog_drift, (0, 0), pygame.Rect(fx, fy, SW, SH), pygame.BLEND_RGB_ADD)

        # 3) объекты
        self.sprites.draw_exit(camx, camy)
        self.sprites.draw_pickups(camx, camy)
        self.sprites.draw_notes(camx, camy)
        self.sprites.draw_secret(camx, camy)
        self.sprites.draw_outpost(camx, camy)
        self.sprites.draw_props(camx, camy)
        self.sprites.draw_thrown(camx, camy)
        self.sprites.draw_dust(camx, camy)
        if m.active:
            self.monster_view.draw(m, camx, camy)
        if not self.s.hidden:
            self.sprites.draw_player(int(p.x - camx), int(p.y - camy))

        # 4) свет и тени
        level, rng = self.torch.state()
        ox, oy = p.x, p.y
        poly = self.lighting.visibility_polygon(ox, oy, 760, camx, camy)    # дальность лучей > света: видны далёкие лампы
        alpha = 238 + random.randint(0, 5) + (8 if self.atmo.flick_t > 0 else 0)
        extras = self.lighting.lamp_lights(camx, camy)
        self.lighting.render_darkness((ox - camx) / LS, (oy - camy) / LS, p.angle, level, poly, min(alpha, 252), extras)

        self.sprites.draw_glows(camx, camy)
        if self.s.hidden:                         # в шкафчике видно только через щель
            scr.blit(self.slit, (int(p.x - camx) - SW, int(p.y - camy) + 8 - SH))
        self.sprites.draw_exit_arrow(camx, camy)
        self.sprites.draw_blast_arrow(camx, camy)
        self.fx.apply()
        self.hud.draw()


# ------------------------------------------------------------------ МОНСТР И СКРИМЕР
class MonsterRenderer:
    """Монстр (ответственность: вид сверху — позвоночник, 4 руки, щупальца, голова с раскрытой пастью)."""

    def __init__(self, clock, s, screen, tex):
        self.clock = clock
        self.s = s
        self.screen = screen
        self.tex = tex

    def draw(self, m, camx, camy):
        sx, sy = m.x - camx, m.y - camy
        if sx < -90 or sy < -90 or sx > SW + 90 or sy > SH + 90:
            return
        p = self.s.player
        scream = m.state == "chase" and math.hypot(p.x - m.x, p.y - m.y) < 170
        self.paint(self.screen, m, sx, sy, scream)

    def paint(self, scr, m, sx, sy, scream=False):
        """Монстр на поверхности scr: текстурное тело/череп (запечены в Textures) + анимированные руки, щупальца, пасть."""
        t = self.clock.t
        chase = m.state == "chase"
        if chase:                                            # дёргается, как будто кости не слушаются
            sx += random.uniform(-1.6, 1.6)
            sy += random.uniform(-1.6, 1.6)
        f = m.facing
        cf, sf = math.cos(f), math.sin(f)
        px, py = -sf, cf
        rate = 12 if chase else 3.2
        ph = m.anim * rate
        breath = 1.0 + 0.06 * math.sin(t * 2.2)
        skin, dark, bone = (150, 140, 128), (58, 44, 44), (226, 218, 196)

        pygame.draw.circle(scr, (6, 4, 4), (sx + 3, sy + 4), 19)
        if chase and random.random() < 0.4:                  # красный «призрак» позади — глитч
            pygame.draw.circle(scr, (96, 14, 14), (sx - cf * 11 + random.uniform(-4, 4), sy - sf * 11), 14)
        # щупальца, волочащиеся за спиной (тёмный контур + влажный блик)
        for k in range(4):
            a0 = math.pi + (k - 1.5) * 0.45
            pts = [(sx - cf * 8, sy - sf * 8)]
            for i in range(1, 7):
                w = math.sin(ph * 0.7 + i * 0.9 + k * 1.7) * (2.5 + i * 0.7)
                d = i * 6.5
                ax, ay = math.cos(f + a0), math.sin(f + a0)
                pts.append((sx - cf * 8 + ax * d - ay * w * 0.4, sy - sf * 8 + ay * d + ax * w * 0.4))
            pygame.draw.lines(scr, (22, 14, 16), False, pts, 5)
            pygame.draw.lines(scr, (62, 44, 46), False, pts, 3)
            pygame.draw.lines(scr, (120, 96, 98), False, [(x - 0.6, y - 0.6) for x, y in pts], 1)
            pygame.draw.circle(scr, (140, 28, 28), (int(pts[-1][0]), int(pts[-1][1])), 2)
        # позвоночник: цепочка позвонков, изгибающаяся волной
        for i in range(4, 0, -1):
            w = math.sin(ph * 0.5 + i * 0.8) * 3
            bx = sx - cf * (7 + i * 7) + px * w
            by = sy - sf * (7 + i * 7) + py * w
            pygame.draw.circle(scr, (24, 16, 16), (bx, by), 10 - i)
            pygame.draw.circle(scr, dark, (bx, by), 9 - i)
            pygame.draw.circle(scr, bone, (bx - cf * 2, by - sf * 2), 2)
        # задние тонкие ручки подёргиваются
        for side in (-1, 1):
            tw = math.sin(ph * 1.9 + side) * 5
            a = (sx - cf * 4 + px * 9 * side, sy - sf * 4 + py * 9 * side)
            b = (a[0] - cf * 10 + px * (7 + tw) * side, a[1] - sf * 10 + py * (7 + tw) * side)
            pygame.draw.line(scr, (24, 16, 16), a, b, 5)
            pygame.draw.line(scr, dark, a, b, 3)
            pygame.draw.circle(scr, bone, (int(b[0]), int(b[1])), 2)
        # длинные передние руки: контур + кожа + блик + вена; сустав-кость; когти
        reach = 1.35 if chase else 1.0
        for side in (-1, 1):
            sw = math.sin(ph + (0 if side > 0 else math.pi))
            sh = (sx + px * 11 * side * breath, sy + py * 11 * side * breath)
            el = (sh[0] + cf * 16 * reach + px * side * (8 + 3 * sw), sh[1] + sf * 16 * reach + py * side * (8 + 3 * sw))
            hd = (el[0] + cf * (22 + 9 * sw) * reach - px * side * 5, el[1] + sf * (22 + 9 * sw) * reach - py * side * 5)
            for (a, b, w1, w2) in ((sh, el, 9, 6), (el, hd, 7, 5)):
                pygame.draw.line(scr, (30, 20, 20), a, b, w1)
                pygame.draw.line(scr, (124, 108, 100), a, b, w2)
                pygame.draw.line(scr, (176, 160, 146), (a[0] - px * side * 1.2, a[1] - py * side * 1.2),
                                 (b[0] - px * side * 1.2, b[1] - py * side * 1.2), 1)
                pygame.draw.line(scr, (112, 26, 34), (a[0] + px * side * 1.0, a[1] + py * side * 1.0),
                                 (b[0] + px * side * 1.0, b[1] + py * side * 1.0), 1)
            pygame.draw.circle(scr, (30, 20, 20), (int(el[0]), int(el[1])), 5)
            pygame.draw.circle(scr, bone, (int(el[0]), int(el[1])), 3)
            for k in (-1.5, -0.5, 0.5, 1.5):
                a = f + k * 0.28
                tip = (hd[0] + math.cos(a) * 12, hd[1] + math.sin(a) * 12)
                pygame.draw.line(scr, (38, 28, 26), hd, tip, 4)
                pygame.draw.line(scr, bone, hd, tip, 2)
        # текстурное тело и череп (рёбра, мышцы, швы — всё внутри запечённой картинки)
        body = pygame.transform.rotozoom(self.tex.monster_base, -math.degrees(f), 0.62 * breath)
        scr.blit(body, body.get_rect(center=(int(sx), int(sy))))
        for k in range(-2, 3):                                # костяные шипы вдоль спины
            pygame.draw.line(scr, (30, 22, 20), (sx - cf * 13 + px * k * 4, sy - sf * 13 + py * k * 4),
                             (sx - cf * 21 + px * k * 5, sy - sf * 21 + py * k * 5), 4)
            pygame.draw.line(scr, bone, (sx - cf * 13 + px * k * 4, sy - sf * 13 + py * k * 4),
                             (sx - cf * 20 + px * k * 5, sy - sf * 20 + py * k * 5), 2)
        # пасть раскрыта (V-образный разлом): дёсны, длинные игольчатые зубы
        hx, hy = sx + cf * 14, sy + sf * 14
        open_ = 0.30 + 0.12 * math.sin(ph * 0.8) + (0.55 if scream else 0.0)
        for side in (-1, 1):
            a = f + side * open_
            base_pt = (hx + cf * 4, hy + sf * 4)
            tip = (base_pt[0] + math.cos(a) * 20, base_pt[1] + math.sin(a) * 20)
            pygame.draw.line(scr, (50, 6, 10), base_pt, tip, 8)
            pygame.draw.line(scr, (118, 24, 28), base_pt, tip, 5)
            for k in range(1, 7):
                u = k / 7.0
                bx = base_pt[0] + (tip[0] - base_pt[0]) * u
                by = base_pt[1] + (tip[1] - base_pt[1]) * u
                ln = 3.2 + (k % 2) * 2.2
                pygame.draw.line(scr, bone, (bx, by), (bx - math.sin(a) * side * ln, by + math.cos(a) * side * ln), 1)
        if scream:                                            # слюна тянется из пасти
            for k in (-1, 0, 1):
                pygame.draw.line(scr, (196, 186, 176), (hx + cf * 16 + px * k * 5, hy + sf * 16 + py * k * 5),
                                 (hx + cf * 24 + px * k * 7, hy + sf * 24 + py * k * 7), 1)
        # глаза: горящие зрачки в тёмных глазницах (зрачки пульсируют)
        pr = 2 + (1 if int(t * 6) % 2 == 0 else 0) + (1 if chase else 0)
        for side in (-1, 1):
            ex_, ey_ = hx + cf * 4 + px * 4.5 * side, hy + sf * 4 + py * 4.5 * side
            pygame.draw.circle(scr, (250, 40, 28), (ex_, ey_), pr)
            pygame.draw.circle(scr, (255, 220, 190), (ex_ - 0.5, ey_ - 0.5), 1)


class JumpscareRenderer:
    """
    Скример: ЧУДОВИЩЕ СЪЕДАЕТ ПЕРСОНАЖА (ответственность: сцена поимки).
    Замирание -> из темноты вылетают жвалы -> героя затягивает в пасть -> ХРУСТ -> монстр жуёт, кровь -> чернота.
    """

    DREAD = 0.90            # секунды затишья перед броском (сердце, подсознательные кадры)
    GRAB = 0.85             # через сколько секунд после броска когти хватают героя и РВУТ его
    TOTAL = 4.2

    def __init__(self, clock, s, screen, sprites, tex, text):
        self.clock = clock
        self.s = s
        self.screen = screen
        self.sprites = sprites
        self.tex = tex
        self.text = text
        self.snapshot = None
        self.bg = None
        self.t = 0.0
        self.ang = 0.0
        self.screamed = False
        self.chomped = False
        self.maw_tex = make_maw_texture()
        self.tmp_p = pygame.Surface((270, 270), pygame.SRCALPHA)
        rnd = random.Random(9)
        self.teeth = [(rnd.uniform(0.7, 1.4), rnd.uniform(0.8, 1.25)) for _ in range(12)]
        self.drops = [(rnd.uniform(0, 6.283), rnd.uniform(120, 560), rnd.uniform(4, 15)) for _ in range(80)]   # брызги крови
        self.sched = []
        self.i = 0
        self.gore = None

    def begin(self, ang=None):
        """Запоминает кадр. ang — направление броска монстра (по умолчанию — от монстра к игроку)."""
        self.snapshot = self.screen.copy()
        small = pygame.transform.smoothscale(self.snapshot, (SW // 18, SH // 18))
        self.bg = pygame.transform.scale(small, (SW, SH))
        self.bg.fill((255, 70, 70), special_flags=pygame.BLEND_RGB_MULT)
        if ang is None:
            m, p = self.s.monster, self.s.player
            ang = math.atan2(p.y - m.y, p.x - m.x)
        self.ang = ang
        self.t = 0.0
        self.i = 0
        self.sched = [(0.30, "thump"), (0.55, "thump"), (0.74, "thump"), (self.DREAD, "scream"),
                      (self.DREAD + self.GRAB, "rip"), (self.DREAD + self.GRAB + 1.5, "flatline"), (self.TOTAL, "done")]
        self.gore = None

    def advance(self, dt):
        """Расписание: 'thump' (сердце) x3, 'scream' (бросок), 'rip' (герой разорван), 'flatline' (остановка сердца), 'done'."""
        self.t += dt
        if self.i < len(self.sched) and self.t >= self.sched[self.i][0]:
            ev = self.sched[self.i][1]
            self.i += 1
            return ev
        return None

    def draw_maw(self, hx, hy, sc, open_k, u):
        """
        Пасть сверху: череп, две огромные жвалы-половины с зубами (шарнир в точке hx,hy), глотка и язык.
        open_k: 1 — раскрыта, 0 — сомкнута.
        """
        scr, a0 = self.screen, self.ang
        f = (math.cos(a0), math.sin(a0))
        oa = 0.05 + open_k * 0.62
        L = 320 * sc
        tips = [(hx + math.cos(a0 + sd * oa) * L, hy + math.sin(a0 + sd * oa) * L) for sd in (-1, 1)]
        pygame.draw.polygon(scr, (40, 2, 8), [(hx, hy), tips[0], tips[1]])                      # глотка
        mid = [(hx + (t[0] - hx) * 0.55, hy + (t[1] - hy) * 0.55) for t in tips]
        pygame.draw.polygon(scr, (104, 12, 20), [(hx, hy), mid[0], mid[1]])
        return f, oa, L, tips

    def draw_jaws(self, hx, hy, sc, oa, L, tips, u, open_k):
        scr, a0 = self.screen, self.ang
        f = (math.cos(a0), math.sin(a0))
        # язык
        pts = [(hx + f[0] * L * k + (-f[1]) * math.sin(u * 14 + k * 6) * 16 * sc * open_k,
                hy + f[1] * L * k + f[0] * math.sin(u * 14 + k * 6) * 16 * sc * open_k) for k in (0.05, 0.2, 0.4, 0.6, 0.78)]
        pygame.draw.lines(scr, (150, 70, 82), False, pts, max(4, int(24 * sc * (0.3 + open_k))))
        for sd, tip in zip((-1, 1), tips):
            a = a0 + sd * oa
            d = (math.cos(a), math.sin(a))
            n = (sd * math.sin(a), -sd * math.cos(a))                    # внутренняя нормаль (к оси пасти)
            w0, w1 = 66 * sc, 15 * sc
            inner0 = (hx + n[0] * w0 * 0.30, hy + n[1] * w0 * 0.30)
            pygame.draw.polygon(scr, (34, 22, 20), [(hx - n[0] * w0, hy - n[1] * w0), (tip[0] - n[0] * w1, tip[1] - n[1] * w1), tip, inner0])
            pygame.draw.polygon(scr, (152, 140, 126), [(hx - n[0] * w0 * 0.82, hy - n[1] * w0 * 0.82),
                                                       (tip[0] - n[0] * w1 * 0.7, tip[1] - n[1] * w1 * 0.7),
                                                       (tip[0] - n[0] * 2, tip[1] - n[1] * 2), (inner0[0] - n[0] * 4, inner0[1] - n[1] * 4)])
            pygame.draw.line(scr, (96, 12, 18), inner0, tip, max(3, int(12 * sc)))          # десна
            for k, (hl, wd) in enumerate(self.teeth):                                      # клыки
                kk = 0.10 + 0.86 * (k + 0.5) / len(self.teeth)
                bx, by = inner0[0] + (tip[0] - inner0[0]) * kk, inner0[1] + (tip[1] - inner0[1]) * kk
                tw, tl = 9 * sc * wd, (44 + 34 * hl) * sc
                pygame.draw.polygon(scr, (238, 230, 202), [(bx - d[0] * tw, by - d[1] * tw), (bx + d[0] * tw, by + d[1] * tw),
                                                           (bx + n[0] * tl + d[0] * 3 * sc, by + n[1] * tl + d[1] * 3 * sc)])
        if open_k > 0.3:                                                                    # нити слюны между челюстями
            for k in (0.35, 0.55, 0.75):
                x0, y0 = hx + (tips[0][0] - hx) * k, hy + (tips[0][1] - hy) * k
                x1, y1 = hx + (tips[1][0] - hx) * k, hy + (tips[1][1] - hy) * k
                pygame.draw.line(scr, (206, 196, 186), (x0, y0), (x1, y1 + math.sin(u * 9 + k * 5) * 6), 1)
        # череп сверху челюстей (закрывает их основания) + светящиеся глаза
        sx, sy = hx - f[0] * 120 * sc, hy - f[1] * 120 * sc
        skull = pygame.transform.rotozoom(self.maw_tex, -math.degrees(a0), sc)
        scr.blit(skull, skull.get_rect(center=(int(sx), int(sy))))
        p = (-f[1], f[0])
        for sd in (-1, 1):
            ex, ey = sx + f[0] * 68 * sc + p[0] * sd * 52 * sc, sy + f[1] * 68 * sc + p[1] * sd * 52 * sc
            pygame.draw.circle(scr, (20, 0, 0), (ex, ey), 17 * sc)
            pygame.draw.circle(scr, (255, 40, 28), (ex, ey), 11 * sc)
            pygame.draw.circle(scr, (255, 230, 200), (ex - 3 * sc, ey - 3 * sc), 3 * sc)

    def draw(self):
        if self.t < self.DREAD:
            self.draw_dread()
        else:
            self.draw_scream(self.t - self.DREAD)

    def draw_peek(self):
        """Подсознательный кадр на 2-3 фрейма: два горящих глаза и оскал в абсолютной тьме."""
        scr = self.screen
        scr.fill((0, 0, 0))
        cx, cy = SW // 2, SH // 2
        for sd in (-1, 1):
            pygame.draw.circle(scr, (90, 0, 0), (cx + sd * 120, cy - 30), 46)
            pygame.draw.circle(scr, (255, 30, 20), (cx + sd * 120, cy - 30), 30)
            pygame.draw.circle(scr, (255, 220, 200), (cx + sd * 120, cy - 36), 8)
        for i in range(-7, 8):
            x = cx + i * 30
            y = cy + 110 + int(18 * abs(i) ** 0.7)
            pygame.draw.polygon(scr, (230, 222, 196), [(x - 12, y), (x + 12, y), (x, y + 60 + (i % 3) * 14)])

    def draw_dread(self):
        """Затишье: кадр наезжает, темнеет, сердце бьётся всё чаще; на 2-3 кадра мелькает оскал; нарастающие сбои."""
        scr, k = self.screen, self.t / self.DREAD
        if 0.43 <= self.t < 0.47 or 0.80 <= self.t < 0.83:
            self.draw_peek()
            screen_glitch(scr, 1.0)
            return
        sc = 1.0 + 0.18 * k * k
        img = pygame.transform.smoothscale(self.snapshot, (int(SW * sc), int(SH * sc)))
        amp = 1 + 7 * k
        scr.fill((0, 0, 0))
        scr.blit(img, (int((SW - img.get_width()) / 2 + random.uniform(-amp, amp)),
                       int((SH - img.get_height()) / 2 + random.uniform(-amp, amp))))
        veil = pygame.Surface((SW, SH))
        veil.fill((0, 0, 0))
        veil.set_alpha(int(clamp(110 * k, 0, 255)))
        scr.blit(veil, (0, 0))
        self.tex.red_vig.set_alpha(int(clamp(60 + 190 * k, 0, 255)))
        scr.blit(self.tex.red_vig, (0, 0))
        scr.blit(self.tex.overlay, (0, 0))
        scr.blit(random.choice(self.tex.grain), (0, 0))
        screen_glitch(scr, 0.08 + 0.5 * k * k, False)

    # --- куски героя: рисуются примитивами в масштабе ×3 от игрового спрайта (куртка, шапка, рюкзак, ботинки)
    def draw_piece(self, kind, x, y, ang, k=1.0):
        scr = self.screen
        c, sn = math.cos(ang), math.sin(ang)

        def pt(dx, dy):
            return (x + (dx * c - dy * sn) * k, y + (dx * sn + dy * c) * k)

        if kind == "torso":
            body = [(-30, -42), (30, -42), (36, 0), (30, 42), (-30, 42), (-36, 0)]
            pygame.draw.polygon(scr, (18, 26, 34), [pt(dx, dy) for dx, dy in body])
            pygame.draw.polygon(scr, (46, 68, 84), [pt(dx * 0.88, dy * 0.88) for dx, dy in body])
            pygame.draw.line(scr, (24, 36, 46), pt(0, -38), pt(0, 38), 2)
            pygame.draw.line(scr, (210, 200, 110), pt(-22, -30), pt(22, -30), 3)         # световозвращающая полоса
            for i in range(6):                                                           # рваный низ и торчащие рёбра
                pygame.draw.polygon(scr, (150, 14, 20), [pt(-30 + i * 12, 40), pt(-22 + i * 12, 40), pt(-26 + i * 12, 52 + (i % 2) * 9)])
            for i in range(3):
                pygame.draw.line(scr, (232, 224, 198), pt(-16 + i * 16, 44), pt(-14 + i * 16, 60), 3)
        elif kind == "head":
            pygame.draw.circle(scr, (110, 8, 14), pt(-26, 0), int(20 * k))                # кровавая шея
            pygame.draw.circle(scr, (30, 18, 16), pt(0, 0), int(31 * k))
            pygame.draw.circle(scr, (138, 44, 40), pt(0, 0), int(28 * k))                 # вязаная шапка
            for a in range(0, 360, 30):
                pygame.draw.line(scr, (96, 28, 28), pt(math.cos(math.radians(a)) * 8, math.sin(math.radians(a)) * 8),
                                 pt(math.cos(math.radians(a)) * 26, math.sin(math.radians(a)) * 26), 1)
            pygame.draw.circle(scr, (186, 150, 130), pt(0, 0), int(9 * k))
        elif kind == "pack":
            pygame.draw.polygon(scr, (44, 30, 18), [pt(-25, -39), pt(25, -39), pt(25, 39), pt(-25, 39)])
            pygame.draw.polygon(scr, (92, 66, 42), [pt(-22, -36), pt(22, -36), pt(22, 36), pt(-22, 36)])
            pygame.draw.line(scr, (60, 42, 26), pt(-22, -14), pt(22, -14), 2)
            pygame.draw.polygon(scr, (150, 14, 20), [pt(-22, 36), pt(0, 36), pt(-8, 50), pt(-18, 44)])
        elif kind == "arm":
            pygame.draw.line(scr, (18, 26, 34), pt(0, 0), pt(66, 0), int(26 * k))
            pygame.draw.line(scr, (46, 68, 84), pt(0, 0), pt(66, 0), int(20 * k))
            pygame.draw.circle(scr, (26, 26, 30), pt(70, 0), int(13 * k))                  # перчатка
            pygame.draw.circle(scr, (150, 14, 20), pt(-2, 0), int(13 * k))                 # оторванное плечо
            pygame.draw.circle(scr, (232, 224, 198), pt(-3, 0), int(5 * k))
        elif kind == "leg":
            pygame.draw.line(scr, (14, 18, 26), pt(0, 0), pt(62, 0), int(28 * k))
            pygame.draw.line(scr, (40, 48, 66), pt(0, 0), pt(62, 0), int(22 * k))
            pygame.draw.circle(scr, (16, 18, 22), pt(66, 0), int(15 * k))                  # ботинок
            pygame.draw.circle(scr, (46, 50, 58), pt(70, 0), int(9 * k))
            pygame.draw.circle(scr, (150, 14, 20), pt(-2, 0), int(14 * k))

    def spawn_gore(self, P):
        """Герой разорван: куски тела разлетаются, вокруг — мясо, кости и брызги."""
        rnd = random.Random(21)
        ca, sa = math.cos(self.ang), math.sin(self.ang)
        specs = (("torso", (0, 0), 140), ("head", (30, 0), 430), ("pack", (-34, 0), 360), ("arm", (0, -40), 520),
                 ("arm", (0, 40), 520), ("leg", (-24, -18), 470), ("leg", (-24, 18), 470))
        pieces = []
        for kind, (ox, oy), speed in specs:
            wx, wy = ox * ca - oy * sa, ox * sa + oy * ca
            d = math.atan2(wy, wx) if (ox or oy) else rnd.uniform(0, 6.283)
            d += rnd.uniform(-0.35, 0.35)
            v = speed * rnd.uniform(0.85, 1.15)
            pieces.append({"kind": kind, "x": P[0] + wx, "y": P[1] + wy, "vx": math.cos(d) * v, "vy": math.sin(d) * v,
                           "a": rnd.uniform(0, 6.283), "spin": rnd.uniform(-8, 8)})
        chunks = []
        for _ in range(60):
            d, v = rnd.uniform(0, 6.283), rnd.uniform(160, 760)
            bone = rnd.random() < 0.2
            col = (232, 224, 198) if bone else rnd.choice(((170, 30, 40), (120, 16, 24), (214, 104, 108), (90, 8, 14)))
            chunks.append({"x": P[0], "y": P[1], "vx": math.cos(d) * v, "vy": math.sin(d) * v, "r": rnd.uniform(5, 17),
                           "a": rnd.uniform(0, 6.283), "spin": rnd.uniform(-10, 10), "col": col, "bone": bone})
        self.gore = {"pieces": pieces, "chunks": chunks, "P": P}

    @staticmethod
    def drag_pos(x, y, vx, vy, tau, c=3.2):
        """Положение при линейном торможении (аналитически — не зависит от частоты кадров)."""
        k = (1.0 - math.exp(-c * tau)) / c
        return x + vx * k, y + vy * k

    def draw_claws(self, P, f, pull):
        """Огромные когтистые лапы монстра хватают героя за плечи с двух сторон и тянут в стороны."""
        scr = self.screen
        p = (-f[1], f[0])
        for sd in (-1, 1):
            far = 120 + 190 * (1 - pull) * 0 + 40 * pull * sd * sd
            q = (P[0] + p[0] * sd * (70 + 110 * pull), P[1] + p[1] * sd * (70 + 110 * pull))
            o = (q[0] + p[0] * sd * 900, q[1] + p[1] * sd * 900)
            pygame.draw.line(scr, (30, 20, 20), o, q, 46)
            pygame.draw.line(scr, (126, 110, 100), o, q, 36)
            pygame.draw.line(scr, (112, 26, 34), (o[0] + f[0] * 8, o[1] + f[1] * 8), (q[0] + f[0] * 8, q[1] + f[1] * 8), 3)
            pygame.draw.circle(scr, (30, 20, 20), (int(q[0]), int(q[1])), 40)
            pygame.draw.circle(scr, (140, 124, 112), (int(q[0]), int(q[1])), 34)
            for i in range(-2, 2):                                                      # четыре когтя впиваются в героя
                base = (q[0] + f[0] * (i + 0.5) * 17, q[1] + f[1] * (i + 0.5) * 17)
                tip = (base[0] - p[0] * sd * (46 + 22 * pull), base[1] - p[1] * sd * (46 + 22 * pull))
                pygame.draw.line(scr, (24, 16, 16), base, tip, 11)
                pygame.draw.line(scr, (232, 224, 198), base, tip, 7)
                pygame.draw.circle(scr, (140, 8, 14), (int(tip[0]), int(tip[1])), 5)

    def draw_gore(self, tc, hinge):
        """Разлетающиеся куски героя с кровавыми следами, мясо, кости и растущая лужа."""
        scr = self.screen
        g = self.gore
        P = g["P"]
        pool = clamp(tc / 1.2, 0.0, 1.0)
        pygame.draw.circle(scr, (84, 4, 8), (int(P[0]), int(P[1])), int(30 + 150 * pool))
        for (a, dist, r) in self.drops[:int(10 + 60 * pool)]:
            pygame.draw.circle(scr, (110, 6, 12), (int(P[0] + math.cos(a) * dist * 0.55 * pool), int(P[1] + math.sin(a) * dist * 0.4 * pool)), int(r))
        for ch in g["chunks"]:
            x, y = self.drag_pos(ch["x"], ch["y"], ch["vx"], ch["vy"], tc)
            a = ch["a"] + ch["spin"] * min(tc, 0.6)
            r = ch["r"]
            pts = [(x + math.cos(a + i * 1.3) * r * (0.6 + 0.4 * ((i * 5) % 3) / 2.0), y + math.sin(a + i * 1.3) * r * (0.6 + 0.4 * ((i * 5) % 3) / 2.0))
                   for i in range(5)]
            pygame.draw.polygon(scr, (60, 4, 8) if not ch["bone"] else (130, 120, 100), pts)
            pygame.draw.polygon(scr, ch["col"], [(x + (px_ - x) * 0.75, y + (py_ - y) * 0.75) for px_, py_ in pts])
        for pc in g["pieces"]:
            x, y = self.drag_pos(pc["x"], pc["y"], pc["vx"], pc["vy"], tc)
            if pc["kind"] == "torso" and tc > 0.25:                                    # монстр подтягивает торс к пасти
                m = clamp((tc - 0.25) / 0.7, 0.0, 1.0)
                x, y = x + (hinge[0] - x) * m, y + (hinge[1] - y) * m
                if m >= 1.0:
                    continue
            if tc < 1.4:                                                               # кровавый шлейф за каждым куском
                prev = (x, y)
                for j in range(1, 9):
                    px_, py_ = self.drag_pos(pc["x"], pc["y"], pc["vx"], pc["vy"], max(0.0, tc - j * 0.025))
                    pygame.draw.line(scr, (130, 6, 12), prev, (px_, py_), max(2, 16 - j * 2))
                    prev = (px_, py_)
            self.draw_piece(pc["kind"], x, y, pc["a"] + pc["spin"] * min(tc, 0.9))

    def draw_scream(self, u):
        scr = self.screen
        tc = u - self.GRAB                                        # время после разрыва (<0 — ещё хватает и растягивает)
        left = self.TOTAL - self.t
        fl = pygame.Surface((SW, SH))
        f = (math.cos(self.ang), math.sin(self.ang))
        P = (SW / 2, SH / 2)
        sc = 1.25
        lunge = clamp(u / 0.30, 0.0, 1.0)
        e = 1 - (1 - lunge) ** 3
        final = (P[0] - f[0] * 175 * sc, P[1] - f[1] * 175 * sc)
        start = (final[0] - f[0] * 1100, final[1] - f[1] * 1100)
        creep = max(0.0, u - 0.30) * 14
        hx, hy = start[0] + (final[0] - start[0]) * e + f[0] * creep, start[1] + (final[1] - start[1]) * e + f[1] * creep
        if tc < 0:
            open_k = min(1.0, 0.2 + u * 6)
        elif tc < 0.55:
            open_k = 1.0                                          # рёв над растерзанным телом
        elif tc < 1.4:
            open_k = 0.25 + 0.55 * abs(math.sin(tc * 9))          # жрёт куски
        else:
            open_k = 0.03 + 0.07 * abs(math.sin(tc * 17))
        amp = 6 + (50 * math.exp(-tc * 3.0) if tc >= 0 else 14 * min(1.0, max(0.0, u - 0.3) / 0.55))
        ox, oy = random.uniform(-amp, amp), random.uniform(-amp, amp)
        scr.blit(self.bg, (random.randint(-10, 10), random.randint(-10, 10)))
        f2, oa, L, tips = self.draw_maw(hx + ox, hy + oy, sc, open_k, u)
        if tc < 0:                                                # хватает: герой растягивается между когтями
            pull = clamp((u - 0.25) / (self.GRAB - 0.25), 0.0, 1.0)
            pl = self.s.player
            pl.angle, pl.moving, pl.sprinting, pl.light_on = self.ang + math.pi + math.sin(u * 38) * 0.9, True, True, True
            self.tmp_p.fill((0, 0, 0, 0))
            self.sprites.draw_player(135, 135, self.tmp_p, zoom=3.0)
            big = pygame.transform.rotozoom(self.tmp_p, math.sin(u * 30) * 25 * (1 - pull), 1.0)
            w2, h2 = big.get_size()
            st = pygame.transform.smoothscale(big, (max(2, int(w2 * (1 + 0.55 * pull))), max(2, int(h2 * (1 - 0.25 * pull)))))
            jx, jy = random.uniform(-5, 5) * (1 + 2 * pull), random.uniform(-5, 5) * (1 + 2 * pull)
            scr.blit(st, st.get_rect(center=(int(P[0] + ox + jx), int(P[1] + oy + jy))))
            self.draw_claws((P[0] + ox, P[1] + oy), f, pull)
        else:
            if self.gore is None:
                self.spawn_gore(P)
            self.draw_gore(tc, (hx + ox + f[0] * 120, hy + oy + f[1] * 120))
        self.draw_jaws(hx + ox, hy + oy, sc, oa, L, tips, u, open_k)
        if tc >= 0:                                               # кровь на «объективе» и потёки с клыков
            k = clamp(tc / 0.9, 0.0, 1.0)
            for (a, dist, r) in self.drops[:int(80 * k)]:
                pygame.draw.circle(scr, (118, 4, 10), (int(SW // 2 + math.cos(a) * dist * 1.1), int(SH // 2 + math.sin(a) * dist * 0.8)), int(r))
            for tip in tips:
                for j in range(5):
                    x = tip[0] + (hx - tip[0]) * j / 6.0
                    y0 = tip[1] + (hy - tip[1]) * j / 6.0
                    pygame.draw.line(scr, (118, 6, 10), (int(x + ox), int(y0 + oy)), (int(x + ox), int(y0 + oy + 20 + 70 * k + j * 6)), 4)
        scr.blit(random.choice(self.tex.grain), (0, 0))
        if u < 0.08:                                              # белая вспышка при броске
            fl.fill((255, 255, 255))
            fl.set_alpha(int(clamp(255 * (1 - u / 0.08), 0, 255)))
            scr.blit(fl, (0, 0))
        elif 0 <= tc < 0.14:                                      # красная вспышка в момент разрыва
            fl.fill((255, 20, 10))
            fl.set_alpha(int(clamp(230 * (1 - tc / 0.14), 0, 255)))
            scr.blit(fl, (0, 0))
        if tc > 1.1:                                              # титр
            k = clamp((tc - 1.1) / 0.5, 0.0, 1.0)
            self.text.draw_text(self.text.f_big, "ТЕБЯ РАЗОРВАЛИ НА КЛОЧКИ", (int(210 * k), int(10 * k), int(10 * k)),
                                (SW // 2, SH // 2 - 20), True, False)
        screen_glitch(scr, 1.0 if u < 0.35 else (0.9 if 0 <= tc < 0.3 else 0.25))
        if left < 0.8:                                            # уход в чёрный
            fl.fill((0, 0, 0))
            fl.set_alpha(int(clamp(255 * (1 - left / 0.8), 0, 255)))
            scr.blit(fl, (0, 0))


# ------------------------------------------------------------------ ФИНАЛЬНЫЙ БОЙ
class BossFight:
    """
    Финальный бой (ответственность: ПРАВИЛА — патроны, перезарядка, тайминг выстрела, атаки и парирование).
    Ничего не рисует; о победе и поражении сообщает событиями boss_won / boss_lost.
      ПКМ — выстрел: попасть надо, когда сужающееся кольцо совпадёт с кругом-целью (идеально = 2 урона, хорошо = 1).
      Q   — перезарядка (беззащитен 1.3 с).
      ПРОБЕЛ — парирование: нажать в зелёное окно перед ударом монстра. Успех оглушает его (выстрелы идеальны).
    """

    MAG, RESERVE, BOSS_HP, PLAYER_HP = 6, 14, 14, 3
    RELOAD_T, RING_PERIOD, SHOT_CD = 1.3, 1.15, 0.38
    TARGET, PERFECT, GOOD = 0.22, 0.055, 0.14       # радиус цели кольца и допуски по радиусу (0..1)
    facing = 0.0                                     # босс — «актёр» для MonsterRenderer.paint
    state = "chase"

    def __init__(self, audio, s):
        self.audio = audio
        self.s = s
        self.begin()

    def begin(self):
        self.t = 0.0
        self.anim = 0.0
        self.phase = "intro"          # intro -> fight -> dying -> done | lost
        self.hp = self.BOSS_HP
        self.php = self.PLAYER_HP
        self.mag = self.MAG
        self.reserve = self.RESERVE
        self.reload_t = 0.0
        self.ring = 0.0
        self.shot_cd = 0.0
        self.gap = 760.0
        self.gap_push = 0.0
        self.attack = None
        self.next_attack = 2.2
        self.stagger_t = 0.0
        self.parry_cd = 0.0
        self.popups = []
        self.tracers = []
        self.shake = 0.0
        self.flash = 0.0
        self.muzzle = 0.0
        self.hit_t = 0.0
        self.dead_t = 0.0

    # ---- вычисляемые величины для отрисовки
    @property
    def ring_radius(self):
        return 1.0 - self.ring

    @property
    def reload_frac(self):
        return 0.0 if self.reload_t <= 0 else 1.0 - self.reload_t / self.RELOAD_T

    @property
    def in_window(self):
        a = self.attack
        return a is not None and a["t"] >= a["win0"]

    def say(self, text, color, where="boss"):
        self.popups.append({"text": text, "color": color, "where": where, "t": 0.0})

    # ---- действия игрока
    def shoot(self):
        if self.phase != "fight":
            return
        if self.reload_t > 0:
            self.say("ПЕРЕЗАРЯДКА...", (180, 180, 170), "player")
            return
        if self.mag <= 0:
            self.audio.play("click")
            self.say("ПУСТО! Q — перезарядка", (255, 150, 90), "player")
            return
        if self.shot_cd > 0:
            return
        self.mag -= 1
        self.shot_cd = self.SHOT_CD
        self.muzzle = 0.12
        self.audio.play("shot", vol=0.65)
        err = abs(self.ring_radius - self.TARGET)
        if self.stagger_t > 0 or err <= self.PERFECT:
            q = "perfect"
        elif err <= self.GOOD:
            q = "good"
        else:
            q = "miss"
        self.tracers.append({"t": 0.0, "q": q})
        self.s.emit("shot", q)
        dmg = {"perfect": 2, "good": 1, "miss": 0}[q]
        if dmg == 0:
            self.say("МИМО", (160, 160, 160))
            return
        self.hp = max(0, self.hp - dmg)
        self.hit_t = 1.0
        self.gap_push += 26 * dmg
        self.audio.play("hit", vol=0.7)
        self.say("ИДЕАЛЬНО! x2" if q == "perfect" else "ХОРОШО", (255, 220, 90) if q == "perfect" else (150, 230, 150))
        if self.hp <= 0:
            self.kill()

    def reload(self):
        if self.phase != "fight" or self.reload_t > 0:
            return
        if self.mag >= self.MAG:
            self.say("Магазин полон", (170, 170, 160), "player")
            return
        if self.reserve <= 0:
            self.say("Нет патронов! Парируй — отобьёшь патрон", (255, 150, 90), "player")
            return
        self.reload_t = self.RELOAD_T
        self.audio.play("reload")
        self.say("ПЕРЕЗАРЯДКА", (200, 200, 190), "player")

    def parry(self):
        if self.phase != "fight" or self.parry_cd > 0:
            return
        a = self.attack
        if a is None or self.stagger_t > 0:             # рано / впустую: нельзя «спамить» пробел
            self.parry_cd = 0.5
            self.say("РАНО", (170, 170, 160), "player")
            return
        if a["t"] >= a["win0"]:                         # попали в окно
            self.attack = None
            self.stagger_t = 1.5
            self.reserve += 1
            self.gap_push += 90
            self.shake = 16
            self.next_attack = 2.0
            self.audio.play("parry")
            self.s.emit("parry_ok")
            self.say("ПАРИРОВАНО!", (120, 220, 255), "player")
        else:                                           # раньше окна
            self.parry_cd = 0.7
            self.say("СЛИШКОМ РАНО", (255, 150, 90), "player")

    def kill(self, force=False):
        """Конец боя. Если прочитаны ВСЕ записки, Томас узнаёт Марка и замирает — игрок выбирает судьбу."""
        self.hp = 0
        self.attack = None
        if self.s.all_notes_read and not force:
            self.phase = "recognition"
            self.s.emit("boss_choice")
            self.audio.play("ding", vol=0.5)
            return
        self.phase = "dying"
        self.audio.play("growl")

    def resolve(self, spare):
        """Выбор в момент узнавания: пощадить или добить."""
        if self.phase != "recognition":
            return
        if spare == "cure":                                  # антидот: Томас снова человек
            if not self.s.has_antidote:
                return
            self.s.ending = "cure"
        else:
            self.s.ending = "spare" if spare else "kill"
        self.phase = "dying"
        if spare:
            self.audio.play("ding", vol=0.7)
        else:
            self.audio.play("shot", vol=0.7)
            self.muzzle = 0.12
            self.tracers.append({"t": 0.0, "q": "perfect"})

    # ---- такт
    def take_hit(self):
        self.php -= 1
        self.attack = None
        self.flash = 1.0
        self.shake = 30
        self.gap_push -= 80
        self.next_attack = random.uniform(1.5, 2.6)
        self.audio.play("hit")
        self.say("-1 ЖИЗНЬ", (255, 90, 80), "player")
        if self.php <= 0:
            self.phase = "lost"
            self.s.emit("boss_lost")

    def update(self, dt):
        self.t += dt
        self.anim += dt * (0.35 if self.stagger_t > 0 else 1.0)
        self.shake *= max(0.0, 1 - 4 * dt)
        self.flash = max(0.0, self.flash - dt * 2.5)
        self.muzzle = max(0.0, self.muzzle - dt)
        self.hit_t = max(0.0, self.hit_t - dt * 4)
        self.parry_cd = max(0.0, self.parry_cd - dt)
        self.shot_cd = max(0.0, self.shot_cd - dt)
        for pp in self.popups:
            pp["t"] += dt
        self.popups = [pp for pp in self.popups if pp["t"] < 1.1]
        for tr in self.tracers:
            tr["t"] += dt
        self.tracers = [tr for tr in self.tracers if tr["t"] < 0.16]

        if self.phase == "intro":                       # монстр вылетает из темноты и догоняет
            k = clamp(self.t / 1.7, 0.0, 1.0)
            self.gap = 760 - 430 * (1 - (1 - k) ** 2)
            if self.t >= 1.7:
                self.phase = "fight"
                self.say("БОЙ!", (255, 220, 120), "player")
            return
        if self.phase == "dying":
            self.dead_t += dt
            self.shake = max(self.shake, 8)
            if self.dead_t >= 2.8:
                self.phase = "done"
                self.s.emit("boss_won")
            return
        if self.phase == "recognition":                 # время замерло, ждём выбор игрока
            self.anim += 0.0
            return
        if self.phase != "fight":
            return

        self.ring = (self.ring + dt / self.RING_PERIOD) % 1.0
        if self.reload_t > 0:
            self.reload_t -= dt
            if self.reload_t <= 0:
                n = min(self.MAG - self.mag, self.reserve)
                self.mag += n
                self.reserve -= n
        self.gap_push *= max(0.0, 1 - 2.2 * dt)
        self.gap = clamp(330.0 + self.gap_push + 12 * math.sin(self.anim * 3), 190.0, 560.0)

        if self.stagger_t > 0:
            self.stagger_t -= dt
        elif self.attack is None:
            self.next_attack -= dt
            if self.next_attack <= 0:
                lunge = self.hp <= 8 and random.random() < 0.5
                tele = 1.15 if lunge else 0.85
                win = 0.36 if lunge else 0.30
                self.attack = {"kind": "lunge" if lunge else "swipe", "t": 0.0, "tele": tele, "win0": tele - win}
                self.audio.play("swipe", vol=0.75)
                self.audio.play("growl", vol=0.4)
        else:
            a = self.attack
            a["t"] += dt
            if a["t"] >= a["tele"]:                     # не парировал — удар достигает цели
                self.take_hit()
                if self.phase == "fight":
                    self.next_attack = random.uniform(1.5, 2.7) * (0.7 + 0.3 * self.hp / self.BOSS_HP)


class BossRenderer:
    """Рисование боя (ответственность: коридор, монстр-гигант, кольцо тайминга, телеграф атак, HUD боя)."""

    GY = 364                # высота «дорожки» боя
    PX = 800                # положение игрока по x
    SCALE_M = 2.8           # во сколько раз монстр больше своего спрайта
    SCALE_P = 2.2

    def __init__(self, boss, clock, fx, lighting, monster_view, s, screen, sprites, tex, text):
        self.boss = boss
        self.clock = clock
        self.fx = fx
        self.lighting = lighting
        self.monster_view = monster_view
        self.s = s
        self.screen = screen
        self.sprites = sprites
        self.tex = tex
        self.text = text
        self.strip = None
        self.tmp_m = pygame.Surface((220, 220), pygame.SRCALPHA)
        self.tmp_p = pygame.Surface((90, 90), pygame.SRCALPHA)
        self.fade = pygame.Surface((SW, SH))

    def prepare(self):
        """Длинная лента коридора из тех же процедурных тайлов (потом просто прокручивается)."""
        if self.strip is not None:
            return
        cols = 40
        strip = pygame.Surface((cols * TILE, 13 * TILE))
        ao, h = self.tex.ao, self.tex.ao["h"]
        for c in range(cols):
            for r in range(13):
                tile = random.choice(self.tex.floor_tiles if 3 <= r <= 9 else self.tex.wall_tiles)
                strip.blit(tile, (c * TILE, r * TILE))
            strip.blit(ao["top"], (c * TILE, 3 * TILE))
            strip.blit(ao["bottom"], (c * TILE, 10 * TILE - h))
            pygame.draw.rect(strip, (104, 110, 120), (c * TILE, 3 * TILE - 3, TILE, 2))
            pygame.draw.rect(strip, (104, 110, 120), (c * TILE, 10 * TILE + 1, TILE, 2))
        self.strip = strip

    # ---- части кадра
    def draw_monster(self, mx, my):
        b = self.boss
        scream = b.attack is not None or b.stagger_t > 0 or b.phase == "dying"
        self.tmp_m.fill((0, 0, 0, 0))
        self.monster_view.paint(self.tmp_m, b, 110, 110, scream)
        sc = self.SCALE_M * (1.0 + 0.04 * math.sin(b.anim * 6))
        big = pygame.transform.smoothscale(self.tmp_m, (int(220 * sc), int(220 * sc)))
        if b.phase == "dying":
            big.set_alpha(int(clamp(int(255 * max(0.0, 1 - b.dead_t / 2.6)), 0, 255)))
        jx = jy = 0.0
        if b.stagger_t > 0 or b.hit_t > 0 or b.phase == "dying":
            jx, jy = random.uniform(-7, 7), random.uniform(-7, 7)
        lunge = 0.0
        if b.attack is not None:
            k = clamp(b.attack["t"] / b.attack["tele"], 0, 1)
            lunge = (70 if b.attack["kind"] == "lunge" else 36) * k * k
        self.screen.blit(big, big.get_rect(center=(int(mx + jx + lunge), int(my + jy))))

    def draw_player(self, px, py):
        p = self.s.player
        p.angle, p.moving, p.sprinting, p.light_on = math.pi, True, True, True
        p.battery = max(p.battery, 50.0)
        self.s.hidden = False
        self.tmp_p.fill((0, 0, 0, 0))
        self.sprites.draw_player(45, 45, self.tmp_p)
        big = pygame.transform.smoothscale(self.tmp_p, (int(90 * self.SCALE_P), int(90 * self.SCALE_P)))
        self.screen.blit(big, big.get_rect(center=(int(px), int(py))))

    def draw_ring(self, tx, ty):
        """Кольцо тайминга: стреляй, когда сужающийся круг совпадёт с кругом-целью."""
        b, scr = self.boss, self.screen
        active = b.phase == "fight" and b.reload_t <= 0 and b.mag > 0
        r_t = int(26 + 150 * b.TARGET)
        r = int(26 + 150 * b.ring_radius)
        err = abs(b.ring_radius - b.TARGET)
        if not active:
            col = (90, 90, 90)
        elif b.stagger_t > 0 or err <= b.PERFECT:
            col = (255, 230, 90)
        elif err <= b.GOOD:
            col = (120, 230, 120)
        else:
            col = (230, 230, 230)
        pygame.draw.circle(scr, (255, 70, 60) if active else (70, 40, 40), (int(tx), int(ty)), r_t, 2)
        pygame.draw.circle(scr, col, (int(tx), int(ty)), max(4, r), 4 if col != (230, 230, 230) else 2)
        pygame.draw.circle(scr, (255, 60, 40), (int(tx), int(ty)), 5)
        for a in range(0, 360, 90):                         # «прицельные риски»
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            pygame.draw.line(scr, col, (tx + ca * (r_t + 6), ty + sa * (r_t + 6)), (tx + ca * (r_t + 18), ty + sa * (r_t + 18)), 2)

    def draw_telegraph(self, mx, my, px, py):
        b, scr = self.boss, self.screen
        a = b.attack
        if a is None:
            return
        k = clamp(a["t"] / a["tele"], 0.0, 1.0)
        win = b.in_window
        self.tex.red_vig.set_alpha(int(clamp(int(60 + 150 * k), 0, 255)))
        scr.blit(self.tex.red_vig, (0, 0))
        col = (90, 255, 130) if win else (255, 70, 60)
        r = int(40 + 130 * (1 - k))
        pygame.draw.circle(scr, col, (int(px), int(py)), r, 4)             # сужающееся кольцо парирования
        pygame.draw.circle(scr, col, (int(px), int(py)), 40, 2)
        w = int(4 + 14 * k)                                               # красный росчерк когтей по направлению к игроку
        pygame.draw.line(scr, (255, 60, 40), (mx + 70, my - 30), (px - 50, py - 10 + 20 * math.sin(self.clock.t * 30)), w)
        pygame.draw.line(scr, (255, 60, 40), (mx + 70, my + 30), (px - 50, py + 10 - 20 * math.sin(self.clock.t * 30)), w)
        if a["t"] > 0.18:
            label = "ПАРИРУЙ! [ПРОБЕЛ]" if win else "ПРИГОТОВЬСЯ..."
            self.text.draw_text(self.text.f_big, label, (110, 255, 140) if win else (255, 200, 120), (SW // 2, 112))

    def draw_effects(self, tipx, tipy, tx, ty, px, py, mx, my):
        b, scr = self.boss, self.screen
        for tr in b.tracers:
            col = {"perfect": (255, 230, 90), "good": (190, 240, 150), "miss": (150, 150, 150)}[tr["q"]]
            endx, endy = (tx, ty) if tr["q"] != "miss" else (tx - 160, ty + random.uniform(-80, 80))
            pygame.draw.line(scr, col, (tipx, tipy), (endx, endy), 3)
            if tr["q"] != "miss":                                           # брызги крови/искры
                for _ in range(4):
                    pygame.draw.circle(scr, (200, 20, 20) if tr["q"] == "good" else (255, 240, 140),
                                       (int(endx + random.uniform(-26, 26)), int(endy + random.uniform(-26, 26))), 3)
        if b.muzzle > 0:                                                    # вспышка выстрела
            pts = [(tipx + math.cos(i * 0.6283) * (26 if i % 2 == 0 else 9), tipy + math.sin(i * 0.6283) * (26 if i % 2 == 0 else 9))
                   for i in range(10)]
            pygame.draw.polygon(scr, (255, 240, 170), pts)
            pygame.draw.circle(scr, (255, 255, 255), (int(tipx), int(tipy)), 8)
        for pp in b.popups:                                                 # всплывающие надписи
            k = pp["t"] / 1.1
            x, y = (px, py - 130) if pp["where"] == "player" else (mx + 40, my - 190)
            col = tuple(int(c * (1 - k * 0.7)) for c in pp["color"])
            self.text.draw_text(self.text.f_big if pp["where"] == "boss" else self.text.f_mid, pp["text"], col,
                                (int(x), int(y - 60 * k)))

    def draw_hud(self):
        b, scr = self.boss, self.screen
        # жизни игрока
        for i in range(b.PLAYER_HP):
            col = (220, 40, 50) if i < b.php else (50, 30, 32)
            x, y = 36 + i * 38, 40
            pygame.draw.circle(scr, col, (x - 7, y - 5), 8)
            pygame.draw.circle(scr, col, (x + 7, y - 5), 8)
            pygame.draw.polygon(scr, col, [(x - 15, y - 1), (x + 15, y - 1), (x, y + 16)])
        # полоса здоровья босса
        w = 420
        pygame.draw.rect(scr, (10, 6, 6), (SW // 2 - w // 2 - 3, 22, w + 6, 22))
        pygame.draw.rect(scr, (170, 24, 28), (SW // 2 - w // 2, 25, int(w * b.hp / b.BOSS_HP), 16))
        pygame.draw.rect(scr, (140, 130, 120), (SW // 2 - w // 2 - 3, 22, w + 6, 22), 2)
        self.text.draw_text(self.text.f_small, "ТОМАС  (ОБРАЗЕЦ №13)", (210, 200, 190), (SW // 2, 58))
        # патроны: магазин + запас
        for i in range(b.MAG):
            col = (230, 200, 90) if i < b.mag else (50, 46, 40)
            pygame.draw.rect(scr, col, (28 + i * 16, SH - 78, 10, 28))
            pygame.draw.rect(scr, (20, 18, 14), (28 + i * 16, SH - 78, 10, 28), 1)
        self.text.draw_text(self.text.f_mid, "x %d" % b.reserve, (200, 190, 160), (150, SH - 64), False)
        if b.reload_t > 0:
            pygame.draw.rect(scr, (20, 20, 20), (28, SH - 100, 150, 10))
            pygame.draw.rect(scr, (230, 200, 90), (28, SH - 100, int(150 * b.reload_frac), 10))
        elif b.mag == 0 and b.phase == "fight" and int(self.clock.t * 4) % 2 == 0:
            self.text.draw_text(self.text.f_small, "ПУСТО — Q", (255, 120, 90), (28, SH - 100), False)
        self.text.draw_text(self.text.f_small, "ПКМ — выстрел в такт     Q — перезарядка     ПРОБЕЛ — парировать",
                            (120, 118, 110), (SW // 2, SH - 20))

    def draw_choice(self):
        """Развилка: пощадить Томаса или добить."""
        scr, tx, C = self.screen, self.text, StoryBook.CHOICE
        self.fade.fill((0, 0, 0))
        self.fade.set_alpha(150)
        scr.blit(self.fade, (0, 0))
        tx.draw_text(tx.f_title, C["title"], (230, 200, 150), (SW // 2, 170))
        for i, ln in enumerate(C["lines"]):
            tx.draw_text(tx.f_mid, ln, (210, 200, 190), (SW // 2, 260 + i * 38))
        blink = 0.75 + 0.25 * math.sin(self.clock.t * 5)
        tx.draw_text(tx.f_big, C["spare"], (int(150 * blink), int(240 * blink), int(160 * blink)), (SW // 2, 400))
        tx.draw_text(tx.f_big, C["kill"], (int(240 * blink), int(120 * blink), int(110 * blink)), (SW // 2, 470))
        if self.s.has_antidote:
            tx.draw_text(tx.f_big, "[3]  ВВЕСТИ АНТИДОТ — вернуть Томаса", (int(120 * blink), int(235 * blink), int(235 * blink)), (SW // 2, 540))

    def draw(self):
        b, scr = self.boss, self.screen
        amp = b.shake
        shx, shy = random.uniform(-amp, amp) * 0.6, random.uniform(-amp, amp) * 0.6
        scr.fill((0, 0, 0))
        W = self.strip.get_width()
        off = int(self.clock.t * 320) % W
        scr.blit(self.strip, (int(-off + shx), int(-4 + shy)))
        scr.blit(self.strip, (int(W - off + shx), int(-4 + shy)))
        px, py = self.PX + shx, self.GY + shy
        mx, my = px - b.gap + shx, self.GY + 8 * math.sin(b.anim * 2.4) + shy
        pygame.draw.ellipse(scr, (6, 4, 4), pygame.Rect(int(mx - 150), int(my + 110), 300, 60))      # тень монстра
        self.draw_monster(mx, my)
        self.draw_player(px, py)
        tipx, tipy = px - 25 * self.SCALE_P - 6, py - 10
        tx, ty = mx - 10, my                                 # слабое место — рана на груди
        extras = [(mx / LS, my / LS, self.lighting.rmasks[5])]
        if b.muzzle > 0:
            extras.append((tipx / LS, tipy / LS, self.lighting.rmasks[6]))
        self.lighting.render_darkness(px / LS, py / LS, math.pi, 14, None, 198, extras)
        self.draw_telegraph(mx, my, px, py)
        if b.phase in ("fight", "intro"):
            self.draw_ring(tx, ty)
        self.draw_effects(tipx, tipy, tx, ty, px, py, mx, my)
        if b.flash > 0:
            self.tex.red_vig.set_alpha(int(clamp(int(255 * min(1.0, b.flash)), 0, 255)))
            scr.blit(self.tex.red_vig, (0, 0))
        self.fx.apply()
        self.draw_hud()
        if b.phase == "recognition":
            self.draw_choice()
        if b.phase == "intro":
            self.text.draw_text(self.text.f_big, "ОН ВЫБРАЛСЯ!", (230, 60, 50), (SW // 2, 130))
        if b.phase == "dying" and b.dead_t > 2.0:                                   # финальная вспышка
            self.fade.fill((255, 250, 235))
            self.fade.set_alpha(int(clamp(int(255 * clamp((b.dead_t - 2.0) / 0.8, 0.0, 1.0)), 0, 255)))
            scr.blit(self.fade, (0, 0))


# ------------------------------------------------------------------ САУНДТРЕК
class MusicDirector:
    """
    Режиссёр музыки (ответственность: решает, какие музыкальные слои звучат, и плавно микширует их).
    Меню — тема со шкатулкой; на каждом этаже свой фон; напряжение растёт с опасностью; в погоне вступает
    ритм-секция; в финале и бою — свои дорожки; победа и поражение — короткие темы.
    """

    ONESHOT = ("mus_win", "mus_lose", "mus_win_dark", "mus_win_warm", "mus_win_blast")     # играют один раз
    FLOOR_TRACK = {0: "mus_floor0", 1: "mus_floor1", 2: "mus_floor2", 3: "mus_floor3", 4: "mus_floor4", 5: "mus_outpost", 6: "mus_floor5"}
    AMBIENCE = {0: "amb_lab", 1: "amb_lab", 2: "amb_lab", 3: "amb_shaft", 4: "amb_reactor", 5: "amb_outpost", 6: "amb_warehouse"}
    WIN_TRACK = {"normal": "mus_win", "kill": "mus_win_dark", "serum": "mus_win_dark", "spare": "mus_win_warm", "cure": "mus_win_warm",
                 "evac": "mus_win_warm", "blast": "mus_win_blast"}
    FADE = 0.7                             # скорость плавного изменения громкости (1/сек)

    def __init__(self, atmo, audio, boss, s):
        self.atmo = atmo
        self.audio = audio
        self.boss = boss
        self.s = s
        self.cur = {}                      # текущие громкости слоёв

    def targets(self, state):
        """Целевые громкости слоёв для текущего состояния игры."""
        s, a = self.s, self.atmo
        t = {}
        if state == "menu":
            t["mus_menu"] = 0.6
        elif state == "prologue":
            t["mus_finale"] = 0.5
            t["mus_tension"] = 0.18
        elif state == "struggle":
            t["mus_chase"] = 0.8
            t["mus_tension"] = 0.6
        elif state == "pounce":
            t["mus_chase"] = 0.9
            t["mus_tension"] = 0.8
        elif state == "cinematic" and s.cin_name == "outpost":      # прибытие на аванпост: напряжённая тема поста
            t["mus_outpost"] = 0.65
            t["amb_outpost"] = 0.25
            t["mus_tension"] = 0.2
        elif state == "cinematic":
            t["mus_finale"] = 0.55
            t["mus_tension"] = 0.45
        elif state == "floor":
            t["mus_menu"] = 0.25
        elif state in ("play", "pause", "reading"):
            k = {"play": 1.0, "pause": 0.35, "reading": 0.5}[state]
            evac = s.evac_t is not None
            t[self.FLOOR_TRACK.get(s.floor, "mus_floor2")] = 0.55 * k * (0.35 if evac else 1.0)
            t[self.AMBIENCE.get(s.floor, "amb_lab")] = 0.30 * k
            if evac:
                t["mus_evac"] = 0.8 * k
            t["mus_tension"] = (clamp((a.danger - 0.15) / 0.6, 0.0, 1.0) * 0.55 + (0.25 if s.alarm_t > 0 else 0.0)) * k
            if s.monster is not None and s.monster.state == "chase":
                t["mus_chase"] = 0.7 * k
        elif state == "cutscene":
            t["mus_finale"] = 0.6
            t["mus_tension"] = clamp(a.danger / 0.9, 0.0, 1.0) * 0.5
        elif state == "boss":
            t["boss_music"] = 0.55
            t["mus_tension"] = 0.2 + (0.25 if self.boss.attack is not None else 0.0)
        elif state == "win":
            t[self.WIN_TRACK.get(s.ending, "mus_win")] = 0.7
        elif state == "lose":
            t["mus_lose"] = 0.7
        return t                           # в состоянии caught — тишина (слои быстро затухают)

    def update(self, dt, state):
        tgt = self.targets(state)
        rate = 4.0 if state == "caught" else self.FADE
        for name in set(tgt) | set(self.cur):
            goal = tgt.get(name, 0.0)
            v = self.cur.get(name, 0.0)
            v = min(goal, v + rate * dt) if goal > v else max(goal, v - rate * dt)
            if goal <= 0.0 and v <= 0.001:
                self.cur.pop(name, None)
                self.audio.music_stop(name)
                continue
            self.cur[name] = v
            self.audio.music(name, v, 0 if name in self.ONESHOT else -1)


# ------------------------------------------------------------------ РАЦИЯ
class RadioSystem:
    """Рация (ответственность: выбирает сюжетные реплики по событиям игры и ведёт очередь; не рисует)."""

    HOLD_MIN = 3.2

    def __init__(self, audio, s):
        self.audio = audio
        self.s = s
        self.queue = []
        self.cur = None
        self.t = 0.0
        self.hold = 3.0

    def clear(self):
        self.queue, self.cur, self.t = [], None, 0.0

    def say_key(self, key):
        """Ставит в очередь сцену key — один раз за прохождение."""
        if key in self.s.radio_seen or key not in StoryBook.RADIO:
            return
        self.s.radio_seen.add(key)
        self.queue.extend(StoryBook.RADIO[key])

    def on_event(self, ev, data=None):
        s = self.s
        if ev == "floor_start":
            self.say_key("floor_start_%d" % data)
        elif ev == "key" and data == 1:
            self.say_key("first_key")
        elif ev == "third_key":
            self.say_key("all_keys")
        elif ev == "monster_alert":
            self.say_key("monster_first")
        elif ev == "note":
            self.say_key("note_first")
            self.say_key("note_%d_%d" % data)             # реакция Лены на конкретную записку
            if len(s.notes_read) >= StoryBook.TOTAL_NOTES // 2:
                self.say_key("notes_half")
            if s.all_notes_read:
                self.say_key("all_notes")
        elif ev == "evac_start":
            self.say_key("evac_start")
        elif ev == "evac_half":
            self.say_key("evac_half")
        elif ev == "antidote":
            self.say_key("antidote_found")
        elif ev == "serum_offer":
            self.say_key("serum_seen")
        elif ev == "console_seen":
            self.say_key("console_hint")
        elif ev == "dynamite":
            self.say_key("dynamite_found")
        elif ev == "blast_seen":
            self.say_key("blast_hint")
        elif ev == "hide":
            self.say_key("first_hide")
        elif ev == "throw":
            self.say_key("first_throw")
        elif ev == "low_battery":
            self.say_key("low_battery")
        elif ev == "boss_start":
            self.say_key("boss_start")
        elif ev == "boss_choice":
            self.say_key("choice")
        elif ev == "whisper" and self.cur is None and not self.queue:
            self.queue.append(("???", random.choice(StoryBook.WHISPERS)))

    def update(self, dt):
        if self.cur is not None:
            self.t += dt
            if self.t >= self.hold:
                self.cur = None
        if self.cur is None and self.queue:
            self.cur = self.queue.pop(0)
            self.t = 0.0
            self.hold = max(self.HOLD_MIN, len(self.cur[1]) * 0.05 + 1.5)
            self.audio.play("radio", vol=0.5)


class RadioRenderer:
    """Рация на экране (ответственность: плашка с именем говорящего и печатающимся текстом, помехи)."""

    def __init__(self, clock, radio, screen, text):
        self.clock = clock
        self.radio = radio
        self.screen = screen
        self.text = text

    def draw(self):
        r = self.radio
        if r.cur is None:
            return
        speaker, line = r.cur
        scr, tx = self.screen, self.text
        box = pygame.Rect(SW // 2 - 250, SH - 206, 500, 96)
        ghost = speaker == "???"
        pygame.draw.rect(scr, (4, 6, 6), box.move(3, 3))
        pygame.draw.rect(scr, (30, 12, 14) if ghost else (12, 22, 20), box)
        pygame.draw.rect(scr, (130, 40, 44) if ghost else (60, 130, 104), box, 2)
        col = (235, 120, 110) if ghost else (140, 232, 190)
        tx.draw_text(tx.f_small, "%s  [РАЦИЯ]" % speaker, col, (box.left + 12, box.top + 8), False, False)
        n = int(r.t * 42)
        y = box.top + 32
        for ln in tx.wrap(tx.f_small, line, box.w - 24):
            part = ln[:max(0, n)]
            n -= len(ln)
            if part:
                tx.draw_text(tx.f_small, part, (222, 232, 224), (box.left + 12, y), False, False)
            y += 21
        if r.t < 0.3 or random.random() < 0.04:                    # помехи эфира
            for _ in range(6):
                yy = box.top + random.randint(2, box.h - 2)
                pygame.draw.line(scr, (120, 150, 140), (box.left + 2, yy), (box.right - 2, yy), 1)


# ------------------------------------------------------------------ ДОСТИЖЕНИЯ
class AchievementTracker:
    """Достижения (ответственность: следит за событиями игры, открывает награды, ведёт очередь уведомлений)."""

    LIST = {
        "ghost": ("ТИХАЯ ТЕНЬ", "Пройди этаж, ни разу не попавшись монстру на глаза"),
        "reader": ("НАЧИТАННЫЙ", "Прочти все 24 записки"),
        "parry": ("МАСТЕР ПАРИРОВАНИЯ", "Отбей 5 ударов босса за один бой"),
        "sniper": ("МЕТКИЙ ГЛАЗ", "Сделай 3 идеальных выстрела подряд"),
        "mercy": ("МИЛОСЕРДИЕ", "Пощади Томаса в финале"),
        "slip": ("УСКОЛЬЗНУЛ", "Вырвись из хватки монстра за 3 секунды"),
        "blaster": ("ПОДРЫВНИК", "Выберись на поверхность, взорвав завал на этаже -10"),
        "evac": ("ЭВАКУИРОВАН", "Вызови вертолёт с аванпоста и дождись его"),
        "serum": ("НОВАЯ ПЛОТЬ", "Выпей сыворотку на аванпосте"),
        "cure": ("ВСЕ ЖИВЫ", "Верни Томасу человеческий облик антидотом"),
    }

    def __init__(self, audio, s):
        self.audio = audio
        self.s = s
        self.unlocked = set()          # открытые за эту сессию программы
        self.toasts = []
        self.spotted = False           # был ли замечен на текущем этаже
        self.parries = 0
        self.streak = 0

    def new_floor(self):
        self.spotted = False

    def new_fight(self):
        self.parries = 0
        self.streak = 0

    def unlock(self, key):
        if key in self.unlocked:
            return
        self.unlocked.add(key)
        self.toasts.append({"key": key, "t": 0.0})
        self.audio.play("ding", vol=0.6)

    def on_event(self, ev, data=None):
        if ev == "monster_alert":
            self.spotted = True
        elif ev == "floor_cleared":
            if not self.spotted and not self.s.cheated:
                self.unlock("ghost")
        elif ev == "note" and self.s.all_notes_read:
            self.unlock("reader")
        elif ev == "parry_ok":
            self.parries += 1
            if self.parries >= 5:
                self.unlock("parry")
        elif ev == "shot":
            self.streak = self.streak + 1 if data == "perfect" else 0
            if self.streak >= 3:
                self.unlock("sniper")
        elif ev == "struggle_won":
            self.unlock("slip")
        elif ev == "blast_done":
            self.unlock("blaster")
        elif ev == "evac_done":
            self.unlock("evac")
        elif ev == "serum_done":
            self.unlock("serum")
        elif ev == "boss_won" and self.s.ending == "cure":
            self.unlock("cure")
        elif ev == "boss_won" and self.s.ending == "spare":
            self.unlock("mercy")

    def update(self, dt):
        for t in self.toasts:
            t["t"] += dt
        self.toasts = [t for t in self.toasts if t["t"] < 4.6]


class AchievementRenderer:
    """Плашки достижений (ответственность: выезжающая справа табличка с названием и описанием)."""

    def __init__(self, ach, screen, text):
        self.ach = ach
        self.screen = screen
        self.text = text

    def draw(self):
        tx = self.text
        for i, t in enumerate(self.ach.toasts[:2]):
            name, desc = AchievementTracker.LIST[t["key"]]
            k = min(1.0, t["t"] / 0.4, (4.6 - t["t"]) / 0.4)          # выезд и уезд
            box = pygame.Rect(SW - 8 - int(380 * k), 138 + i * 92, 372, 84)
            pygame.draw.rect(self.screen, (6, 6, 4), box.move(3, 3))
            pygame.draw.rect(self.screen, (28, 24, 12), box)
            pygame.draw.rect(self.screen, (214, 176, 70), box, 2)
            tx.draw_text(tx.f_small, "ДОСТИЖЕНИЕ: " + name, (255, 220, 110), (box.left + 12, box.top + 8), False, False)
            for j, ln in enumerate(tx.wrap(tx.f_small, desc, box.w - 24)[:3]):
                tx.draw_text(tx.f_small, ln, (214, 206, 186), (box.left + 12, box.top + 32 + j * 20), False, False)


# ------------------------------------------------------------------ СХВАТКА
class StruggleFight:
    """
    Схватка (ответственность: правила QTE). Монстр поймал героя: за 3 секунды нужно 10 раз нажать ПРОБЕЛ.
    Успех — герой вырывается (событие struggle_won), провал — скример (struggle_lost).
    """

    NEED, TIME, FREE_T = 10, 3.0, 0.7

    def __init__(self, audio, s):
        self.audio = audio
        self.s = s
        self.begin()

    def begin(self):
        self.t = 0.0
        self.count = 0
        self.phase = "fight"          # fight -> freed -> done | lost
        self.free_t = 0.0
        self.kick = 0.0

    @property
    def progress(self):
        return self.count / float(self.NEED)

    def press(self):
        if self.phase != "fight":
            return
        self.count += 1
        self.kick = 1.0
        self.audio.play("hit", vol=min(1.0, 0.35 + 0.06 * self.count))
        if self.count >= self.NEED:
            self.phase = "freed"
            self.audio.play("parry")
            self.audio.play("roar", vol=0.45)

    def update(self, dt):
        self.kick = max(0.0, self.kick - dt * 6)
        if self.phase == "fight":
            self.t += dt
            if self.t >= self.TIME:
                self.phase = "lost"
                self.s.emit("struggle_lost")
        elif self.phase == "freed":
            self.free_t += dt
            if self.free_t >= self.FREE_T:
                self.phase = "done"
                self.s.emit("struggle_won")


class StruggleRenderer:
    """Рисование схватки (ответственность: пасть и когти монстра, герой в хватке, шкала нажатий, обратный отсчёт)."""

    def __init__(self, cfg, clock, scare, s, screen, sprites, struggle, tex, text):
        self.cfg = cfg
        self.clock = clock
        self.scare = scare
        self.s = s
        self.screen = screen
        self.sprites = sprites
        self.struggle = struggle
        self.tex = tex
        self.text = text
        self.tmp_p = pygame.Surface((270, 270), pygame.SRCALPHA)
        self.bg = None
        self.ang = 0.0

    def begin(self):
        m, p = self.s.monster, self.s.player
        self.ang = math.atan2(p.y - m.y, p.x - m.x)
        small = pygame.transform.smoothscale(self.screen.copy(), (SW // 18, SH // 18))
        self.bg = pygame.transform.scale(small, (SW, SH))
        self.bg.fill((255, 90, 90), special_flags=pygame.BLEND_RGB_MULT)

    def draw(self):
        st, scr, sc_ = self.struggle, self.screen, self.scare
        sc_.ang = self.ang                                   # жвалы/когти рисует JumpscareRenderer — общая «модель» монстра
        f = (math.cos(self.ang), math.sin(self.ang))
        P = (SW / 2, SH / 2)
        sc = 1.25
        prog = st.progress
        urgency = (st.t / st.TIME) * (1.0 - prog)
        freed = st.phase in ("freed", "done")
        fr = clamp(st.free_t / st.FREE_T, 0.0, 1.0) if freed else 0.0
        calm = 0.4 if self.cfg.gentle else 1.0
        amp = (6 + 16 * st.kick + 10 * urgency) * calm
        ox, oy = random.uniform(-amp, amp), random.uniform(-amp, amp)
        dist = 175 * sc * (1.05 - 0.25 * urgency) + 900 * fr * fr           # время идёт — пасть ближе; вырвался — монстр отброшен
        hx, hy = P[0] - f[0] * dist + ox, P[1] - f[1] * dist + oy
        open_k = 1.0 - 0.88 * fr
        scr.blit(self.bg, (random.randint(-8, 8), random.randint(-8, 8)))
        f2, oa, L, tips = sc_.draw_maw(hx, hy, sc, open_k, st.t)
        pl = self.s.player                                    # герой бьётся в когтях
        pl.angle, pl.moving, pl.sprinting, pl.light_on = self.ang + math.pi + math.sin(st.t * 38) * (0.9 - 0.6 * prog), True, True, True
        self.tmp_p.fill((0, 0, 0, 0))
        self.sprites.draw_player(135, 135, self.tmp_p, zoom=3.0)
        pull = (0.25 + 0.6 * (1.0 - prog)) * (1.0 - fr)
        big = pygame.transform.rotozoom(self.tmp_p, math.sin(st.t * 30) * 20, 1.0)
        w2, h2 = big.get_size()
        held = pygame.transform.smoothscale(big, (max(2, int(w2 * (1 + 0.5 * pull))), max(2, int(h2 * (1 - 0.2 * pull)))))
        hp = (P[0] + ox + random.uniform(-5, 5) * (0.5 + pull) + f[0] * 120 * fr, P[1] + oy + random.uniform(-5, 5) * (0.5 + pull) + f[1] * 120 * fr)
        scr.blit(held, held.get_rect(center=(int(hp[0]), int(hp[1]))))
        if not freed:
            sc_.draw_claws((P[0] + ox, P[1] + oy), f, pull)
        sc_.draw_jaws(hx, hy, sc, oa, L, tips, st.t, open_k)
        self.tex.red_vig.set_alpha(int(clamp(90 + 140 * urgency, 0, 255)))
        scr.blit(self.tex.red_vig, (0, 0))
        scr.blit(random.choice(self.tex.grain), (0, 0))
        if not self.cfg.gentle:
            screen_glitch(scr, 0.10 + 0.30 * urgency + 0.15 * st.kick, False)
        self.draw_hud(st, freed, fr)

    def draw_hud(self, st, freed, fr):
        scr, tx = self.screen, self.text
        bx, by = SW // 2 - 250, SH - 120
        left = clamp(1.0 - st.t / st.TIME, 0.0, 1.0)
        pygame.draw.rect(scr, (8, 6, 6), (bx - 6, 34, 512, 24))
        pygame.draw.rect(scr, (int(60 + 190 * (1 - left)), int(220 * left + 20), 40), (bx, 40, int(500 * left), 14))
        pygame.draw.rect(scr, (8, 6, 6), (bx - 6, by - 6, 512, 44))
        for i in range(st.NEED):                              # десять ячеек — десять нажатий
            pygame.draw.rect(scr, (240, 200, 60) if i < st.count else (50, 44, 40), (bx + i * 50, by, 44, 32))
        pygame.draw.rect(scr, (150, 140, 120), (bx - 6, by - 6, 512, 44), 2)
        tx.draw_text(tx.f_mid, "%d / %d" % (st.count, st.NEED), (230, 220, 190), (SW // 2, by - 30))
        if freed:
            tx.draw_text(tx.f_title, "ВЫРВАЛСЯ!", (110, 255, 140), (SW // 2, 150), True, False)
            if fr < 0.3:                                      # вспышка освобождения
                fl = pygame.Surface((SW, SH))
                fl.fill((255, 255, 255))
                fl.set_alpha(int(clamp(200 * (1 - fr / 0.3), 0, 255)))
                scr.blit(fl, (0, 0))
        else:
            pulse = 0.75 + 0.25 * math.sin(self.clock.t * 14)
            tx.draw_text(tx.f_title, "ЖМИ ПРОБЕЛ!", (int(255 * pulse), int(90 * pulse + 40 * left), 40), (SW // 2, 130), True, False)
            tx.draw_text(tx.f_small, "осталось %.1f с" % (st.TIME - st.t), (220, 200, 180), (SW // 2, 76))


# ------------------------------------------------------------------ ВСТУПЛЕНИЕ
class PrologueSystem:
    """Вступительная кат-сцена (ответственность: таймлайн шести сцен, звуки по времени, сигнал о завершении)."""

    CUES = [(0, 0.2, "hum", 2, 0.5), (1, 0.4, "sub", 0, 0.6), (1, 2.5, "click", 0, 0.7),
            (2, 1.2, "clunk", 0, 0.9), (2, 1.5, "heart", 0, 0.7), (2, 3.0, "heart", 0, 0.8),
            (3, 0.9, "rumble", 0, 1.0), (3, 2.3, "crash", 0, 1.0), (3, 2.4, "alarm", 1, 0.45), (3, 4.2, "roar", 0, 0.55),
            (4, 0.5, "door", 0, 0.9), (4, 2.3, "door", 0, 0.9), (5, 1.0, "radio", 0, 0.7), (5, 2.2, "whisper", 0, 0.5)]

    def __init__(self, audio, s):
        self.audio = audio
        self.s = s
        self.starts = []
        acc = 0.0
        for dur, _ in StoryBook.PROLOGUE:
            self.starts.append(acc)
            acc += dur
        self.total = acc
        self.cues = sorted((self.starts[i] + off, name, loops, vol) for i, off, name, loops, vol in self.CUES)
        self.begin()

    def begin(self):
        self.t = 0.0
        self.ci = 0
        self.done = False

    def scene(self):
        """(номер сцены, секунды внутри неё, длительность)."""
        idx = 0
        for i, st in enumerate(self.starts):
            if self.t >= st:
                idx = i
        dur = StoryBook.PROLOGUE[idx][0]
        return idx, clamp(self.t - self.starts[idx], 0.0, dur), dur

    def skip(self):
        if self.t > 0.8:
            self.t = self.total + 0.1

    def update(self, dt):
        if self.done:
            return
        self.t += dt
        while self.ci < len(self.cues) and self.t >= self.cues[self.ci][0]:
            _, name, loops, vol = self.cues[self.ci]
            self.audio.play(name, loops, vol)
            self.ci += 1
        if self.t >= self.total + 0.1:
            self.done = True
            self.audio.stop("hum")
            self.audio.stop("alarm")
            self.s.emit("prologue_done")


class PrologueRenderer:
    """Рисование вступления (ответственность: шесть анимированных сцен сверху, титры рассказчика, полосы, затемнения)."""

    def __init__(self, clock, prologue, screen, tex, text):
        self.clock = clock
        self.prologue = prologue
        self.screen = screen
        self.tex = tex
        self.text = text
        self.room = None
        self.tmp = pygame.Surface((320, 320), pygame.SRCALPHA)
        self.veil = pygame.Surface((SW, SH))
        self.plate = pygame.Surface((SW, 150))
        self.plate.fill((0, 0, 0))
        self.plate.set_alpha(150)

    def prepare(self):
        """Лабораторный пол из тех же процедурных тайлов (строится один раз)."""
        if self.room is not None:
            return
        self.room = make_tiled_room(self.tex)

    # ---- общие кирпичики
    def dim(self, alpha):
        self.veil.fill((0, 0, 0))
        self.veil.set_alpha(int(clamp(alpha, 0, 255)))
        self.screen.blit(self.veil, (0, 0))

    def lamp(self, x, y, k=1.0):
        g = self.tex.glow_lamp
        g.set_alpha(int(clamp(255 * k, 0, 255)))
        self.screen.blit(g, g.get_rect(center=(int(x), int(y))))
        g.set_alpha(255)

    def figure(self, x, y, coat, size=1.0):
        """Человек сверху: подбирается текстура по цвету одежды (халат — учёный, чёрный костюм — Кесслер, тёмно-серая форма — охрана)."""
        kind = min(PERSONS, key=lambda k_: sum(abs(a - b) for a, b in zip(PERSONS[k_]["coat"], coat)))
        spr = pygame.transform.rotozoom(self.tex.persons[kind], -math.degrees(math.atan2(SH / 2 - y, SW / 2 - x)), 0.5 * size)
        self.screen.blit(spr, spr.get_rect(center=(int(x), int(y))))

    def tank(self, cx, cy, u, cracks=0.0, broken=False, grow=1.0):
        """Стеклянный резервуар с образцом №13 (светящееся зелёное существо)."""
        scr = self.screen
        if not broken:
            pygame.draw.circle(scr, (30, 36, 38), (cx, cy), 162)
            pygame.draw.circle(scr, (84, 96, 98), (cx, cy), 154)
            pygame.draw.circle(scr, (14, 54, 42), (cx, cy), 142)
        spr = pygame.transform.rotozoom(self.tex.monster_hi, -90 + math.sin(u * 1.2) * 10, 0.75 * grow)
        if not broken:
            spr.fill((70, 200, 150, 255), special_flags=pygame.BLEND_RGBA_MULT)
            spr.set_alpha(175)
        scr.blit(spr, spr.get_rect(center=(int(cx), int(cy + math.sin(u * 1.5) * 8))))
        if not broken:
            for i in range(14):                                                 # пузыри
                bx = cx + math.sin(i * 3.1 + u * 0.7) * 90
                by = cy + 130 - ((u * 40 + i * 37) % 260)
                pygame.draw.circle(scr, (120, 220, 180), (int(bx), int(by)), 3 + i % 4)
            pygame.draw.arc(scr, (200, 230, 226), pygame.Rect(cx - 120, cy - 120, 240, 240), 2.4, 3.6, 3)
            for sd in (-1, 1):                                                  # трубки
                pygame.draw.line(scr, (70, 76, 78), (cx + sd * 60, 0), (cx + sd * 60, cy - 150), 10)
            for k in range(9):                                                  # трещины в стекле
                if cracks <= 0:
                    break
                a = k * 0.7
                pts = [(cx + math.cos(a + math.sin(k * 3 + i) * 0.25) * (20 + i * 26 * cracks),
                        cy + math.sin(a + math.sin(k * 3 + i) * 0.25) * (20 + i * 26 * cracks)) for i in range(6)]
                pygame.draw.lines(scr, (225, 240, 236), False, pts, 2)

    # ---- шесть сцен
    def scene0(self, u, d):                                   # лаборатория: резервуар с образцом №13
        scr = self.screen
        self.dim(120)
        cx, cy = SW // 2, SH // 2 - 10
        self.tank(cx, cy, u)
        for sd in (-1, 1):
            self.figure(cx + sd * 260, cy + 40 + math.sin(u * 0.9 + sd) * 4, (214, 214, 220))
            pygame.draw.line(scr, (210, 210, 200), (cx + sd * 240, cy + 40), (cx + sd * 176, cy + 20), 3)
        for lx in (cx - 340, cx + 340):
            self.lamp(lx, 120, 0.6 + 0.4 * math.sin(u * 9 + lx))

    def scene1(self, u, d):                                   # кабинет: Кесслер отдаёт приказ
        scr = self.screen
        self.dim(135)
        cx, cy = SW // 2, SH // 2
        pygame.draw.rect(scr, (30, 22, 14), (cx - 200, cy - 20, 400, 130))
        pygame.draw.rect(scr, (96, 68, 44), (cx - 196, cy - 24, 392, 124))
        pygame.draw.rect(scr, (146, 112, 74), (cx - 196, cy - 24, 392, 124), 3)
        for i in range(3):                                                      # бумаги и красная печать
            pygame.draw.rect(scr, (214, 208, 190), (cx - 120 + i * 90, cy - 4 + (i % 2) * 6, 70, 46))
        pygame.draw.circle(scr, (170, 24, 28), (cx + 90, cy + 40), 16)
        self.figure(cx, cy - 74, (28, 28, 34), 1.5)                              # Кесслер: тёмный костюм, красный галстук
        pygame.draw.line(scr, (190, 30, 34), (cx, cy - 74), (cx, cy - 54), 4)
        self.figure(cx - 280, cy + 20 + math.sin(u * 5) * 6, (232, 232, 236), 1.2)   # Вейра качает головой
        self.figure(cx + 280, cy + 20, (60, 60, 70), 1.1)                           # охрана
        k = 0.5 + 0.5 * math.sin(u * 6)
        g = self.tex.glow_exit_r
        g.set_alpha(int(clamp(60 + 190 * k, 0, 255)))
        scr.blit(g, g.get_rect(center=(SW - 90, 110)))                         # красная сигнальная лампа
        g.set_alpha(255)
        self.lamp(cx, 90, 0.8)

    def scene2(self, u, d):                                   # медпункт: Марку делают «витамины»
        scr = self.screen
        self.dim(110)
        cx, cy = SW // 2, SH // 2 + 20
        pygame.draw.rect(scr, (24, 26, 30), (cx - 230, cy - 90, 460, 190))
        pygame.draw.rect(scr, (214, 218, 222), (cx - 226, cy - 94, 452, 182))
        pygame.draw.rect(scr, (140, 146, 152), (cx - 226, cy - 94, 452, 182), 3)
        mark = pygame.transform.rotozoom(self.tex.player_hi, 90, 0.95)
        scr.blit(mark, mark.get_rect(center=(cx - 10, cy)))
        k = clamp((u - 0.8) / 2.4, 0.0, 1.0)                                        # шприц подъезжает к плечу
        sx, sy = cx + 250 - 230 * k, cy - 190 + 125 * k
        pygame.draw.line(scr, (230, 232, 236), (sx + 70, sy - 40), (sx, sy), 14)
        pygame.draw.line(scr, (80, 220, 150), (sx + 60 - 40 * k, sy - 34 + 24 * k), (sx + 6, sy - 3), 8)
        pygame.draw.line(scr, (190, 194, 198), (sx, sy), (sx - 26, sy + 16), 3)
        pygame.draw.circle(scr, (60, 120, 190), (int(sx + 80), int(sy - 46)), 15)       # перчатка Вейры
        mon = [(SW - 220 + i * 6, 110 - int(26 * math.sin(i * 0.9 + u * 6)) if i % 5 == 2 else 110) for i in range(30)]   # кардиомонитор
        pygame.draw.lines(scr, (80, 255, 130), False, mon, 2)
        self.lamp(cx, 70, 1.0)
        self.lamp(cx, cy, 0.5)

    def scene3(self, u, d):                                   # прорыв: стекло трескается и лопается
        scr = self.screen
        cx, cy = SW // 2, SH // 2 - 10
        self.dim(120)
        brk = u > 2.3
        t2 = max(0.0, u - 2.3)
        if brk:
            pygame.draw.circle(scr, (22, 86, 60), (cx, cy), int(150 + t2 * 190))        # зелёная жижа растекается
        self.tank(cx, cy, u, cracks=clamp((u - 0.8) / 1.4, 0.0, 1.0), broken=brk, grow=1.0 + t2 * 0.9)
        if brk:
            for i in range(16):                                                     # осколки стекла
                a = i * 0.39 + 0.2
                x, y = cx + math.cos(a) * (150 + t2 * 380), cy + math.sin(a) * (150 + t2 * 380)
                pygame.draw.polygon(scr, (160, 210, 206), [(x, y), (x + 22, y + 8), (x + 6, y + 26)])
        for sd in (-1, 1):                                                          # учёные разбегаются
            fx = cx + sd * (260 + max(0.0, u - 2.0) * 340)
            self.figure(fx, cy + 40 + sd * max(0.0, u - 2.0) * 40, (214, 214, 220))
        if brk:
            k = 0.5 + 0.5 * math.sin(self.clock.t * 14)
            self.veil.fill((200, 10, 10))
            self.veil.set_alpha(int(clamp(40 + 60 * k, 0, 255)))
            scr.blit(self.veil, (0, 0))
            if t2 < 0.25:                                                           # вспышка при разрыве стекла
                self.veil.fill((255, 255, 255))
                self.veil.set_alpha(int(clamp(220 * (1 - t2 / 0.25), 0, 255)))
                scr.blit(self.veil, (0, 0))
                screen_glitch(scr, 1.0, False)

    def scene4(self, u, d):                                   # печать: створки захлопываются
        scr = self.screen
        self.dim(120)
        k = clamp(u / 3.0, 0.0, 1.0)
        # Кесслер убегает к лифту
        self.figure(SW - 130, SH - 150 - u * 85, (24, 24, 30), 1.3)
        pygame.draw.rect(scr, (60, 64, 70), (SW - 190, 70, 120, 64))
        pygame.draw.polygon(scr, (90, 220, 120), [(SW - 130, 80), (SW - 150, 110), (SW - 110, 110)])
        w = int(SW / 2 * k)
        for sd, x0 in ((-1, 0), (1, SW - w)):
            pygame.draw.rect(scr, (52, 56, 62), (x0, 0, w, SH))
            for i in range(-SH, w + SH, 46):                                       # предупреждающие полосы
                pygame.draw.line(scr, (150, 126, 30), (x0 + i, SH), (x0 + i + SH // 2, SH // 2 - SH // 2), 10)
            pygame.draw.rect(scr, (110, 116, 124), (x0, 0, w, SH), 4)
        if k > 0.85 and int(self.clock.t * 4) % 2 == 0:
            self.text.draw_text(self.text.f_title, "ПЕЧАТЬ", (220, 20, 20), (SW // 2, SH // 2 - 30), True, False)
        a = 0.5 + 0.5 * math.sin(self.clock.t * 10)
        g = self.tex.glow_exit_r
        g.set_alpha(int(clamp(80 + 170 * a, 0, 255)))
        scr.blit(g, g.get_rect(center=(80, 90)))
        g.set_alpha(255)

    def scene5(self, u, d):                                   # пробуждение: Марк открывает глаза
        scr = self.screen
        self.dim(170)
        cx, cy = SW // 2, SH // 2
        self.lamp(cx, cy + 60, 1.0)
        self.lamp(cx, cy + 60, 0.7)
        e = clamp((u - 0.6) / 1.8, 0.0, 1.0)
        open_k = e * e * (3 - 2 * e)
        if 3.1 < u < 3.35:                                                           # моргание
            open_k = 0.1
        lid = int(SH / 2 * (1.0 - open_k))
        pygame.draw.rect(scr, (0, 0, 0), (0, 0, SW, lid))
        pygame.draw.rect(scr, (0, 0, 0), (0, SH - lid, SW, lid))
        for _ in range(3 if open_k > 0.3 else 0):                                    # помехи рации
            y = random.randint(SH - 150, SH - 60)
            pygame.draw.line(scr, (150, 170, 160), (random.randint(0, SW // 2), y), (random.randint(SW // 2, SW), y), 1)

    def subtitles(self, idx, u):
        scr, tx = self.screen, self.text
        scr.blit(self.plate, (0, SH - 56 - 150))
        chars = max(0.0, u - 0.5) * 30
        y = SH - 56 - 120
        for line in StoryBook.PROLOGUE[idx][1]:
            for row in tx.wrap(tx.f_mid, line, 920):
                n = int(clamp(chars, 0, len(row)))
                if n > 0:
                    tx.draw_text(tx.f_mid, row[:n], (214, 210, 196), (SW // 2, y))
                chars -= len(row)
                y += 34
            chars -= 6
            y += 10

    def draw(self):
        pr, scr = self.prologue, self.screen
        idx, u, d = pr.scene()
        scr.blit(self.room, (0, 0))
        getattr(self, "scene%d" % idx)(u, d)
        scr.blit(self.tex.overlay, (0, 0))
        scr.blit(random.choice(self.tex.grain), (0, 0))
        pygame.draw.rect(scr, (0, 0, 0), (0, 0, SW, 56))                           # кинематографичные полосы
        pygame.draw.rect(scr, (0, 0, 0), (0, SH - 56, SW, 56))
        self.subtitles(idx, u)
        if pr.t > 0.8:
            self.text.draw_text(self.text.f_small, "ENTER — пропустить", (100, 100, 94), (SW - 110, 24))
        last = idx == len(StoryBook.PROLOGUE) - 1
        a = max(clamp(1.0 - u / 0.45, 0.0, 1.0), clamp((u - (d - (0.9 if last else 0.4))) / (0.9 if last else 0.4), 0.0, 1.0))
        if a > 0:
            self.veil.fill((0, 0, 0))
            self.veil.set_alpha(int(clamp(255 * a, 0, 255)))
            scr.blit(self.veil, (0, 0))


# ------------------------------------------------------------------ КИНО: ПАДЕНИЕ ЛИФТА И ПОДРЫВ
class CinematicSystem:
    """Короткие кат-сцены без управления (ответственность: таймлайн, звуки по времени, сигнал о завершении)."""

    SCENES = {
        "outpost": {"total": 16.0, "done": "outpost_done",
                    "cues": [(2.2, "rumble", 0, 0.7), (3.0, "ding", 0, 0.9), (3.45, "click", 0, 0.9), (3.6, "click", 0, 0.8),
                             (4.7, "door", 0, 0.9), (8.9, "click", 0, 0.7), (9.1, "click", 0, 0.6)]
                    + [(7.2 + 0.25 * i, "step_metal" if i % 2 else "step_metal2", 0, 0.45) for i in range(6)]
                    + [(12.0 + 0.45 * i, "step_metal" if i % 2 else "step_metal2", 0, 0.35) for i in range(7)]},
        "evac": {"total": 8.0, "done": "evac_done",
                 "cues": [(0.2, "rotor", 6, 0.55), (2.8, "static", 0, 0.5), (3.4, "door", 0, 0.7), (5.4, "ding", 0, 0.6)]},
        "serum_end": {"total": 7.6, "done": "serum_done",
                      "cues": [(0.2, "gulp", 0, 1.0), (1.0, "heart", 0, 0.9), (1.6, "transform", 0, 1.0), (3.6, "roar", 0, 0.9),
                               (5.2, "whisper", 0, 0.6)]},
        "fall": {"total": 8.3, "done": "fall_done",
                 "cues": [(0.1, "alarm", 1, 0.5), (0.9, "bang", 0, 0.9), (1.25, "crunch", 0, 0.8), (1.5, "rumble", 0, 1.0),
                          (4.0, "rumble", 0, 1.0), (6.3, "crash", 0, 1.0), (6.35, "sub", 0, 1.0)]},
        "blast": {"total": 8.2, "done": "blast_done",
                  "cues": [(0.4, "clunk", 0, 0.9), (1.0, "static", 0, 0.6), (1.4, "static", 0, 0.6), (1.8, "static", 0, 0.6),
                           (2.2, "static", 0, 0.6), (2.6, "static", 0, 0.7), (3.0, "static", 0, 0.8), (3.4, "static", 0, 0.8),
                           (4.2, "crash", 0, 1.0), (4.2, "sub", 0, 1.0), (4.25, "shriek", 0, 0.35), (4.5, "rumble", 0, 1.0),
                           (6.4, "ding", 0, 0.6)]},
    }

    def __init__(self, audio, s):
        self.audio = audio
        self.s = s
        self.name = "fall"
        self.cues = []
        self.t = 0.0
        self.ci = 0
        self.done = False

    @property
    def total(self):
        return self.SCENES[self.name]["total"]

    def begin(self, name):
        self.name = name
        self.t = 0.0
        self.ci = 0
        self.done = False
        self.cues = sorted(self.SCENES[name]["cues"])

    def skip(self):
        if self.t > 1.0:
            self.t = self.total

    def update(self, dt):
        if self.done:
            return
        self.t += dt
        while self.ci < len(self.cues) and self.t >= self.cues[self.ci][0]:
            _, name, loops, vol = self.cues[self.ci]
            self.audio.play(name, loops, vol)
            self.ci += 1
        if self.t >= self.total:
            self.done = True
            self.audio.stop("alarm")
            self.audio.stop("rotor")
            self.s.emit(self.SCENES[self.name]["done"])


class CinematicRenderer:
    """Рисование кино (ответственность: кабина падающего лифта; подрыв завала с ослепительным светом поверхности)."""

    SUBS = {
        "outpost": [(0.5, 2.7, "Аванпост «Сентинел». Три недели без связи с поверхностью."), (3.1, 4.4, "— Слышишь?.. Лифт!"),
                    (4.4, 5.9, "— Он же мёртвый... Оружие на изготовку!"), (6.0, 7.5, "— Руки! Не двигаться!"),
                    (7.6, 9.0, "— НЕ СТРЕЛЯЙТЕ! Это Марк!"), (9.0, 10.5, "— ...Свои. Опустить оружие."),
                    (10.6, 12.3, "— Марк... Ты жив. Слава богу."), (12.5, 15.0, "— Идём. Тебе нужно отдохнуть... и многое рассказать.")],
        "evac": [(0.3, 2.5, "Рокот винтов... Они услышали вызов!"), (3.0, 5.2, "Держись! Солдаты уже здесь!"), (5.6, 7.8, "Эвакуация...")],
        "serum_end": [(0.3, 1.6, "Ты выпил ампулу до дна."), (1.8, 4.2, "Боль... нет. Ясность."),
                      (4.4, 7.2, "Тьма больше не пугает. Тьма — это дом.")],
        "fall": [(0.3, 2.3, "Лифт дрожит. Что-то не так..."), (1.25, 3.6, "ТРОС ОБОРВАЛСЯ!"), (3.8, 6.2, "Всё быстрее... всё ниже..."),
                 (6.9, 8.2, "ЭТАЖ -10")],
        "blast": [(0.3, 2.2, "Динамит. Фитиль... Надеюсь, хватит."), (2.4, 4.1, "Прячься!"),
                  (4.3, 6.2, "ВЗРЫВ! Свет... это поверхность?")],
    }

    def __init__(self, cin, clock, screen, tex, text):
        self.cin = cin
        self.clock = clock
        self.screen = screen
        self.tex = tex
        self.text = text
        self.room = None
        self.cabin = None
        self.veil = pygame.Surface((SW, SH))
        self.beam = pygame.Surface((SW, SH), pygame.SRCALPHA)
        pygame.draw.polygon(self.beam, (255, 250, 220, 110), [(SW // 2 - 90, 0), (SW // 2 + 90, 0), (SW // 2 + 420, SH), (SW // 2 - 420, SH)])

    def prepare(self):
        if self.room is None:
            self.room = make_tiled_room(self.tex)
            cab = pygame.Surface((380, 360))
            for ty in range(0, 360, TILE):
                for tx_ in range(0, 380, TILE):
                    cab.blit(self.tex.wall_tiles[(tx_ // TILE + ty // TILE) % len(self.tex.wall_tiles)], (tx_, ty))
            cab.fill((150, 150, 156), special_flags=pygame.BLEND_RGB_MULT)
            pygame.draw.rect(cab, (20, 22, 26), (0, 0, 380, 360), 8)
            pygame.draw.line(cab, (14, 16, 18), (190, 70), (190, 360), 5)
            for i in range(-360, 380, 40):
                pygame.draw.line(cab, (150, 126, 30), (i, 360), (i + 36, 322), 8)
            self.cabin = cab

    def flash(self, rgb, a):
        self.veil.fill(rgb)
        self.veil.set_alpha(int(clamp(a, 0, 255)))
        self.screen.blit(self.veil, (0, 0))

    def draw_fall(self, u):
        scr, tx, t = self.screen, self.text, self.clock.t
        fall = clamp((u - 1.25) / 5.0, 0.0, 1.0)                 # 0..1: прогресс падения (трос рвётся на 1.25 с)
        speed = 120 + 1500 * fall
        scr.fill((6, 6, 8))
        off = (t * speed) % 120                                   # балки шахты проносятся вверх
        for i in range(-1, 8):
            y = int(i * 120 + off)
            pygame.draw.rect(scr, (30, 32, 36), (0, y, 250, 14))
            pygame.draw.rect(scr, (30, 32, 36), (SW - 250, y, 250, 14))
            pygame.draw.line(scr, (52, 56, 60), (250, y + 7), (250, y + 127), 3)
            pygame.draw.line(scr, (52, 56, 60), (SW - 250, y + 7), (SW - 250, y + 127), 3)
        for _ in range(int(6 + 40 * fall)):                       # полосы скорости
            x, y = random.randint(0, SW), random.randint(0, SH)
            pygame.draw.line(scr, (74, 78, 84), (x, y), (x, y + 40 + int(140 * fall)), 1)
        amp = 2 + 12 * fall if u >= 1.0 else 1.5 * math.sin(u * 40)
        sh = (random.uniform(-amp, amp), random.uniform(-amp, amp))
        cx, cy = SW // 2 + sh[0], 150 + sh[1]
        cable_top = int(cy)
        if u < 1.25:                                              # трос цел и натянут
            pygame.draw.line(scr, (96, 96, 102), (SW // 2, 0), (int(cx), cable_top), 8)
        else:                                                     # оборван: лохмотья сверху, обрубок на крыше
            pygame.draw.line(scr, (96, 96, 102), (SW // 2, 0), (SW // 2 + int(math.sin(t * 9) * 8), 120), 8)
            pygame.draw.line(scr, (96, 96, 102), (int(cx), cable_top), (int(cx) + 12, cable_top - 30), 8)
            if u < 2.3:
                for _ in range(12):
                    pygame.draw.circle(scr, (255, 220, 90), (int(cx) + random.randint(-26, 26), cable_top - random.randint(0, 40)), random.randint(1, 4))
        scr.blit(self.cabin, (int(cx - 190), cable_top))
        pygame.draw.rect(scr, (10, 10, 12), (int(cx - 62), cable_top + 14, 124, 52))               # табло этажа
        n = 3 + int(fall * 7.99)
        blink = u < 1.25 and int(t * 4) % 2 == 0
        tx.draw_text(tx.f_big, "-%d" % n, (255, 50, 40) if not blink else (120, 20, 20), (int(cx), cable_top + 40), True, False)
        pl = pygame.transform.rotozoom(self.tex.player_hi, -90 + math.sin(t * 18) * 8 * fall, 0.85)
        scr.blit(pl, pl.get_rect(center=(int(cx), cable_top + 220)))
        if u > 1.0:                                                # мигающий свет, к концу — полная темнота
            self.flash((0, 0, 0), random.choice((0, 0, 40, 90, 160)) if u < 6.0 else 235)
        if u >= 6.3:                                               # УДАР
            t2 = u - 6.3
            if t2 < 0.4:
                self.flash((255, 255, 255), 255 * (1 - t2 / 0.4))
            else:
                scr.fill((0, 0, 0))
                if u > 6.8:
                    tx.draw_text(tx.f_title, "ЭТАЖ -10", (200, 40, 30), (SW // 2, SH // 2), True, False)

    def draw_blast(self, u):
        scr, tx, t = self.screen, self.text, self.clock.t
        C = (SW // 2, SH // 2 - 30)
        t2 = u - 4.2                                               # время после взрыва (<0 — ещё не взорвалось)
        amp = 30 * math.exp(-t2 * 2.0) if t2 >= 0 else 0.0
        ox, oy = random.uniform(-amp, amp), random.uniform(-amp, amp)
        scr.blit(self.room, (int(ox) - 10, int(oy) - 10))
        self.flash((0, 0, 0), 130 if t2 < 0 else 40)
        if t2 < 0:
            draw_rubble(scr, C[0], C[1], 2.4)
            if u > 0.5:                                            # динамит заложен, фитиль уходит вдаль
                draw_dynamite(scr, C[0] + 14, C[1] + 70, 2.0, t, u > 1.0)
            end = (200, SH - 160)
            if u > 0.9:
                fz = clamp((u - 1.0) / 3.2, 0.0, 1.0)
                pygame.draw.line(scr, (60, 52, 38), (C[0] + 28, C[1] + 56), end, 3)                        # фитиль
                sp = (C[0] + 28 + (end[0] - C[0] - 28) * (1 - fz), C[1] + 56 + (end[1] - C[1] - 56) * (1 - fz))
                pygame.draw.circle(scr, (255, 200, 60), (int(sp[0]), int(sp[1])), 6)                       # искра бежит к динамиту
                pygame.draw.circle(scr, (255, 245, 200), (int(sp[0]), int(sp[1])), 3)
            k = clamp((u - 1.0) / 1.6, 0.0, 1.0)                                                           # герой убегает и прячется
            px, py = C[0] - 70 + (150 - C[0] + 70) * k, C[1] + 110 + (SH - 150 - C[1] - 110) * k
            hero = pygame.transform.rotozoom(self.tex.player_hi, 150 if k < 1 else 200, 0.75)
            scr.blit(hero, hero.get_rect(center=(int(px), int(py))))
        else:
            beam_k = clamp(t2 / 1.2, 0.0, 1.0)
            self.beam.set_alpha(int(clamp(255 * beam_k, 0, 255)))
            scr.blit(self.beam, (0, 0))                                                                    # свет поверхности
            for i in range(3):                                                                             # ударные волны
                r = int(60 + t2 * (700 - i * 140))
                pygame.draw.circle(scr, (255, 220, 160), (C[0], C[1]), r, 6)
            for i in range(26):                                                                            # обломки
                a = i * 0.2415
                k2 = (1 - math.exp(-3.0 * t2)) / 3.0
                x, y = C[0] + math.cos(a) * (360 + (i % 5) * 70) * k2, C[1] + math.sin(a) * (300 + (i % 4) * 60) * k2
                g = 70 + (i % 6) * 14
                pygame.draw.polygon(scr, (g, g - 4, g - 8), [(x, y), (x + 22, y + 8), (x + 8, y + 26)])
            for i in range(18):                                                                            # пыль поднимается
                x = C[0] + math.sin(i * 2.1) * 260
                y = C[1] + 160 - (t2 * 90 + i * 31) % 420
                pygame.draw.circle(scr, (176, 170, 156), (int(x), int(y)), 14 + i % 16)
            k = clamp(t2 / 0.35, 0.0, 1.0)
            if k < 1.0:
                self.flash((255, 255, 255), 255 * (1 - k))
            if u > 6.2:                                            # уход в слепящий свет
                self.flash((255, 252, 235), 255 * clamp((u - 6.2) / 2.0, 0.0, 1.0))

    def draw_evac(self, u):
        """Вертолёт над люком: прожектор, тени вращающихся лопастей, вихрь пыли; солдаты бегут к герою."""
        scr, t = self.screen, self.clock.t
        C = (SW // 2, SH // 2)
        scr.blit(self.room, (-10, -10))
        k = clamp(u / 3.0, 0.0, 1.0)
        self.flash((0, 0, 0), 150 - 95 * k)
        for i in range(34):                                                # ветер от винта: пыль летит по кругу
            a = i * 0.185 + t * (2.0 + 6.0 * k)
            r = 120 + (i * 37) % 360
            pygame.draw.circle(scr, (176, 170, 156), (int(C[0] + math.cos(a) * r), int(C[1] + math.sin(a) * r * 0.7)), 2 + i % 4)
        spot = int(70 + 220 * k)
        pygame.draw.circle(scr, (250, 246, 220), C, spot)
        pygame.draw.circle(scr, (255, 255, 240), C, int(spot * 0.6))
        for j in range(4):                                                  # тень лопастей
            a = t * 22 + j * math.pi / 2
            pygame.draw.line(scr, (34, 34, 38), C, (int(C[0] + math.cos(a) * 430 * k), int(C[1] + math.sin(a) * 430 * k)), int(10 + 14 * k))
        hero = pygame.transform.rotozoom(self.tex.player_hi, 20 * math.sin(t * 6), 0.8)
        scr.blit(hero, hero.get_rect(center=(C[0] + int(math.sin(t * 9) * 3), C[1] + 10)))
        if u > 3.2:                                                         # солдаты сбегаются со всех сторон
            m = clamp((u - 3.2) / 2.2, 0.0, 1.0)
            for i, (sx, sy) in enumerate(((60, 120), (SW - 60, 160), (80, SH - 130), (SW - 90, SH - 110))):
                x, y = sx + (C[0] - sx) * 0.82 * m, sy + (C[1] - sy) * 0.82 * m
                pygame.draw.ellipse(scr, (6, 6, 8), pygame.Rect(int(x - 18), int(y - 8), 40, 26))
                pygame.draw.ellipse(scr, (54, 74, 54), pygame.Rect(int(x - 20), int(y - 12), 40, 26))
                pygame.draw.circle(scr, (196, 168, 140), (int(x), int(y)), 8)
                pygame.draw.circle(scr, (40, 54, 40), (int(x), int(y - 2)), 8)
        if u > 6.2:
            self.flash((255, 252, 235), 255 * clamp((u - 6.2) / 1.6, 0.0, 1.0))

    def draw_serum_end(self, u):
        """Превращение: вены ползут от краёв к центру, герой сменяется монстром, загораются красные глаза."""
        scr, t = self.screen, self.clock.t
        C = (SW // 2, SH // 2)
        scr.blit(self.room, (-10, -10))
        self.flash((0, 0, 0), 150)
        g = clamp(u / 5.0, 0.0, 1.0)
        k = clamp((u - 1.6) / 2.4, 0.0, 1.0)                                # 0 — человек, 1 — монстр
        hero = pygame.transform.rotozoom(self.tex.player_hi, math.sin(t * 22) * 12 * (1 - k), 1.2)
        hero.set_alpha(int(clamp(255 * (1 - k), 0, 255)))
        scr.blit(hero, hero.get_rect(center=C))
        mon = pygame.transform.rotozoom(self.tex.monster_hi, 0, 0.7 + 0.55 * k)
        mon.set_alpha(int(clamp(255 * k, 0, 255)))
        scr.blit(mon, mon.get_rect(center=C))
        for i in range(26):                                                  # вены
            a = i * 0.2417
            x0, y0 = C[0] + math.cos(a) * 760, C[1] + math.sin(a) * 560
            pts = [(x0 + (C[0] - x0) * (j / 7.0) * g + math.sin(i * 3 + j * 1.7 + t * 3) * 18 * (1 - j / 7.0),
                    y0 + (C[1] - y0) * (j / 7.0) * g + math.cos(i * 2 + j * 1.3 + t * 3) * 18 * (1 - j / 7.0)) for j in range(8)]
            pygame.draw.lines(scr, (130, 14, 24), False, pts, 3)
            pygame.draw.lines(scr, (210, 60, 70), False, pts, 1)
        if k > 0.55:                                                         # красные глаза
            for sd in (-1, 1):
                pygame.draw.circle(scr, (60, 0, 0), (C[0] + sd * 48, C[1] - 40), 26)
                pygame.draw.circle(scr, (255, 40, 30), (C[0] + sd * 48, C[1] - 40), 15)
        beat = 0.5 + 0.5 * math.sin(t * 9)                                   # пульс: красная виньетка
        self.tex.red_vig.set_alpha(int(clamp((60 + 160 * g) * beat, 0, 255)))
        scr.blit(self.tex.red_vig, (0, 0))
        if u > 6.6:
            self.flash((0, 0, 0), 255 * clamp((u - 6.6) / 1.0, 0.0, 1.0))

    def draw_outpost(self, u):
        """Вид сбоку: двое солдат у лифта слышат его приезд, вскидывают автоматы; дверь открывается — внутри Марк;
        вбегает Лена, оружие опускают, и Марк уходит вместе с ней."""
        scr, tx, t = self.screen, self.text, self.clock.t
        gy = 560
        scr.fill((26, 30, 34))                                                     # бетонная стена бункера
        for x in range(0, SW, 128):
            pygame.draw.line(scr, (18, 22, 26), (x, 0), (x, gy), 3)
        pygame.draw.rect(scr, (34, 40, 44), (0, 86, SW, 12))
        pygame.draw.rect(scr, (58, 64, 68), (0, 120, SW, 14))                      # трубы
        pygame.draw.rect(scr, (44, 50, 54), (0, 144, SW, 8))
        for x in range(60, SW, 210):
            pygame.draw.rect(scr, (30, 34, 38), (x, 112, 12, 36))
        pygame.draw.rect(scr, (34, 38, 42), (0, gy - 70, SW, 70))                  # цоколь с предупреждающими полосами
        for x in range(-40, SW, 60):
            pygame.draw.line(scr, (150, 126, 30), (x, gy), (x + 40, gy - 24), 8)
        tx.draw_text(tx.f_big, "СЕНТИНЕЛ", (44, 52, 56), (330, 300))
        pygame.draw.rect(scr, (40, 42, 44), (0, gy, SW, SH - gy))                  # пол
        for x in range(0, SW + 60, 90):
            pygame.draw.line(scr, (26, 28, 30), (x, gy), (x - 50, SH), 2)
        pygame.draw.line(scr, (70, 72, 76), (0, gy), (SW, gy), 3)
        for lx in (260, 640):                                                      # лампы: свет падает на пол
            pygame.draw.rect(scr, (80, 76, 60), (lx - 40, 70, 80, 10))
            self.screen.blit(self.tex.glow_lamp, self.tex.glow_lamp.get_rect(center=(lx, 90)))
        cx = 800                                                                    # лифт
        op = clamp((u - 4.7) / 1.4, 0.0, 1.0)
        op = op * op * (3 - 2 * op)
        pygame.draw.rect(scr, (12, 14, 16), (cx - 136, 186, 272, gy - 186))
        pygame.draw.rect(scr, (20, 22, 26), (cx - 124, 198, 248, gy - 198))
        pygame.draw.rect(scr, (10, 10, 12), (cx - 66, 148, 132, 36))                # табло этажа
        lvl = "-8" if u < 3.0 else "-6"
        lit = u >= 3.0 and int(t * 5) % 2 == 0 or u < 3.0 and u > 2.2 and int(t * 6) % 2 == 0
        tx.draw_text(tx.f_mid, lvl, (255, 70, 50) if lit or u >= 3.0 else (150, 40, 30), (cx - 14, 166))
        pygame.draw.polygon(scr, (255, 70, 50) if u >= 3.0 else (110, 30, 24), [(cx + 28, 176), (cx + 44, 176), (cx + 36, 160)])
        inner = (cx - 110, 210, 220, gy - 210)
        pygame.draw.rect(scr, (176, 164, 124), inner)                               # свет кабины
        pygame.draw.rect(scr, (120, 110, 84), (cx - 110, 210, 220, 30))
        if op > 0:                                                                  # световое пятно на полу
            pygame.draw.ellipse(scr, (74, 70, 48), pygame.Rect(int(cx - 110 - 330 * op), gy - 8, int(330 * op + 110), 30))
        hx_ = cx if u < 9.8 else cx - 100 * clamp((u - 9.8) / 1.4, 0.0, 1.0)         # Марк: в кабине, затем выходит
        if 4.6 <= u < 12.0:                                                          # дальше Марк идёт следом за Леной (рисуется ниже)
            side_person_rig(scr, self.tex.rigs["mark"], hx_, gy, -1, 1.0, walk=t * 8 if u > 9.8 and u < 11.2 else 0.0,
                            hands_up=0.45 if 5.8 <= u < 9.4 else 0.0)
        pw = int(110 * (1 - op))
        for x0 in (cx - 110, cx + 110 - pw):                                        # створки дверей
            pygame.draw.rect(scr, (108, 114, 120), (x0, 210, pw, gy - 210))
            pygame.draw.rect(scr, (70, 76, 82), (x0, 210, pw, gy - 210), 3)
            pygame.draw.line(scr, (140, 146, 152), (x0 + pw // 2, 222), (x0 + pw // 2, gy - 12), 2)
        if u >= 5.4 and u < 8.9:                                                    # красные точки прицелов на груди Марка
            for dy in (-70, -58):
                pygame.draw.circle(scr, (255, 40, 40), (int(hx_ - 4 + random.uniform(-2, 2)), int(gy + dy + random.uniform(-2, 2))), 3)
        aim = clamp((u - 3.3) / 0.6, 0.0, 1.0) * (1.0 - clamp((u - 8.8) / 0.9, 0.0, 1.0))   # автоматы: вскинуты -> опущены
        jolt = 1.0 if 3.0 <= u < 3.7 else 0.0
        for sx, sw_ in ((400, 0.0), (510, 1.7)):
            side_person_rig(scr, self.tex.rigs["soldier"], sx, gy, 1, 1.0, rifle=True, aim=aim,
                            lean=0.35 * jolt + 0.25 * aim + 0.1 * math.sin(t * 1.3 + sw_))
        run = clamp((u - 7.0) / 1.6, 0.0, 1.0)                                       # Лена вбегает слева
        if u >= 7.0:
            lx = -90 + 680 * run
            face, walk = 1, t * 20
            if u >= 8.6:
                lx = 590 + 50 * clamp((u - 9.8) / 1.2, 0.0, 1.0)
                walk = 0.0 if u < 9.8 or u > 11.0 else t * 8
            if u >= 12.0:                                                            # уходят вместе влево
                k = clamp((u - 12.0) / 3.2, 0.0, 1.0)
                lx, face, walk = 640 - 740 * k, -1, t * 8
            side_person_rig(scr, self.tex.rigs["lena"], lx, gy + 8, face, 1.0, walk=walk, hands_up=0.8 if 8.6 <= u < 9.8 else 0.0)
        if u >= 12.0:                                                                # Марк идёт следом
            k = clamp((u - 12.0) / 3.2, 0.0, 1.0)
            side_person_rig(scr, self.tex.rigs["mark"], 700 - 740 * k + 24, gy, -1, 1.0, walk=t * 8 + 1.2)
        for bx in (40, 118):                                                         # мешки с песком на переднем плане
            pygame.draw.ellipse(scr, (70, 62, 44), pygame.Rect(bx - 40, gy - 24, 100, 30))
            pygame.draw.ellipse(scr, (96, 86, 62), pygame.Rect(bx - 36, gy - 26, 92, 24))
        if 3.0 <= u < 3.15:                                                          # вспышка при «динь»
            self.flash((255, 255, 255), 160)
        if u > 15.0:
            self.flash((0, 0, 0), 255 * clamp((u - 15.0) / 1.0, 0.0, 1.0))

    def draw(self):
        c, scr = self.cin, self.screen
        u = c.t
        getattr(self, "draw_" + c.name)(u)
        if c.name == "fall" and 1.0 < u < 6.3:
            screen_glitch(scr, 0.25, False)
        scr.blit(self.tex.overlay, (0, 0))
        scr.blit(random.choice(self.tex.grain), (0, 0))
        pygame.draw.rect(scr, (0, 0, 0), (0, 0, SW, 56))
        pygame.draw.rect(scr, (0, 0, 0), (0, SH - 56, SW, 56))
        for a, b, line in self.SUBS[c.name]:
            if a <= u < b:
                k = min(1.0, (u - a) / 0.25, (b - u) / 0.25)
                v = int(235 * k)
                self.text.draw_text(self.text.f_mid, line, (v, v, int(v * 0.92)), (SW // 2, SH - 28))
        if u > 1.0:
            self.text.draw_text(self.text.f_small, "ENTER — пропустить", (90, 90, 84), (SW - 110, 24))
        fade = clamp((0.5 - u) / 0.5, 0.0, 1.0)
        if fade > 0:
            self.flash((0, 0, 0), 255 * fade)


# ------------------------------------------------------------------ БРОСОК (КАК ФОКСИ)
class PounceSystem:
    """Бросок на камеру (ответственность: таймлайн «прыжка» в момент поимки; затем начинается схватка)."""

    TOTAL = 0.85

    def __init__(self, audio, s):
        self.audio = audio
        self.s = s
        self.t = 0.0
        self.done = False

    def begin(self):
        self.t = 0.0
        self.done = False
        self.audio.play("whoosh", vol=0.9)
        self.audio.play("pounce", vol=1.0)

    @property
    def k(self):
        return clamp(self.t / self.TOTAL, 0.0, 1.0)

    def update(self, dt):
        if self.done:
            return
        self.t += dt
        if self.t >= self.TOTAL:
            self.done = True
            self.audio.play("static", vol=0.6)
            self.s.emit("pounce_done")


class PounceRenderer:
    """
    Рисование броска (ответственность: монстр срывается с места и ЛЕТИТ НА КАМЕРУ — ускоряясь, с судорожной тряской,
    щёлкающей пастью, чёрными кадрами и статикой, как прыжок Фокси в FNaF 2).
    """

    def __init__(self, cfg, clock, pounce, scare, s, screen, sprites, tex):
        self.cfg = cfg
        self.clock = clock
        self.pounce = pounce
        self.scare = scare
        self.s = s
        self.screen = screen
        self.sprites = sprites
        self.tex = tex
        self.tmp_p = pygame.Surface((270, 270), pygame.SRCALPHA)
        self.snap = None
        self.dark = pygame.Surface((SW, SH))
        self.dark.fill((0, 0, 0))
        self.flash = pygame.Surface((SW, SH))
        self.ang = 0.0

    def begin(self):
        m, p = self.s.monster, self.s.player
        self.ang = math.atan2(p.y - m.y, p.x - m.x)           # бросок идёт оттуда, откуда монстр подкрался
        self.snap = self.screen.copy()

    def draw(self):
        pn, scr, sc_ = self.pounce, self.screen, self.scare
        k = pn.k
        e = k ** 2.4                                           # ускорение: сначала крадётся, потом РЫВОК
        calm = 0.4 if self.cfg.gentle else 1.0
        f = (math.cos(self.ang), math.sin(self.ang))
        p = (-f[1], f[0])
        P = (SW / 2, SH / 2)
        amp = (4 + 70 * e) * calm                              # судорожная тряска нарастает вместе с броском
        ox, oy = random.uniform(-amp, amp), random.uniform(-amp, amp)
        scr.blit(self.snap, (int(ox * 0.4), int(oy * 0.4)))     # фон — последний кадр игры
        self.dark.set_alpha(int(clamp(40 + 130 * e, 0, 255)))
        scr.blit(self.dark, (0, 0))
        pl = self.s.player                                      # герой застыл в панике
        pl.angle, pl.moving, pl.sprinting, pl.light_on = self.ang + math.pi + math.sin(pn.t * 40) * 0.4, True, True, True
        self.tmp_p.fill((0, 0, 0, 0))
        self.sprites.draw_player(135, 135, self.tmp_p, zoom=3.0)
        big = pygame.transform.rotozoom(self.tmp_p, 0.0, 0.8)
        scr.blit(big, big.get_rect(center=(int(P[0] + ox), int(P[1] + oy))))
        sc = 0.45 + 2.2 * e                                     # монстр растёт, пока летит в экран
        dist = 1250 * (1 - e) + 175 * 1.25
        sway = math.sin(k * 11) * 200 * (1 - e)                 # виляет по дуге, как зверь, который ловит момент
        hx, hy = P[0] - f[0] * dist + p[0] * sway + ox, P[1] - f[1] * dist + p[1] * sway + oy
        open_k = (0.2 + k) if k <= 0.3 else 0.2 + 0.8 * abs(math.sin(pn.t * 36))      # пасть ЩЁЛКАЕТ
        sc_.ang = self.ang
        f2, oa, L, tips = sc_.draw_maw(hx, hy, sc, open_k, pn.t)
        sc_.draw_jaws(hx, hy, sc, oa, L, tips, pn.t, open_k)
        scr.blit(random.choice(self.tex.grain), (0, 0))
        if not self.cfg.gentle:
            screen_glitch(scr, 0.25 + 0.75 * e, False)
        if random.random() < 0.07 * (1 + 2 * e) * calm:         # чёрные кадры «короткого замыкания»
            self.flash.fill((0, 0, 0))
            self.flash.set_alpha(255)
            scr.blit(self.flash, (0, 0))
        if k > 0.88:                                            # вспышка в момент, когда пасть закрывает экран
            self.flash.fill((255, 255, 255) if not self.cfg.gentle else (200, 200, 200))
            self.flash.set_alpha(int(clamp(255 * (k - 0.88) / 0.12, 0, 255)))
            scr.blit(self.flash, (0, 0))


# ------------------------------------------------------------------ ЭВАКУАЦИЯ
class EvacSystem:
    """Эвакуация (ответственность: обратный отсчёт после вызова с аванпоста и прибытие вертолёта). На аванпосте монстра нет."""

    def __init__(self, audio, note, s):
        self.audio = audio
        self.note = note
        self.s = s
        self.half_said = False

    def start(self):
        self.half_said = False
        self.audio.play("console_on")
        self.audio.play("alarm", 8, 0.3)
        self.note.say("ВЫЗОВ ПОСЛАН! Вертолёт будет через минуту", 5.0)

    def update(self, dt):
        s = self.s
        if s.evac_t is None:
            return
        s.evac_t -= dt
        if s.evac_t <= 30 and not self.half_said:
            self.half_said = True
            s.emit("evac_half")
        if s.evac_t <= 0:
            s.evac_t = None
            s.evac_done = True
            self.audio.stop("alarm")
            s.emit("evac_arrive")


# ------------------------------------------------------------------ ВВОД
class InputRouter:
    """Переводит события и опрос клавиатуры pygame в команды. Никакой игровой логики."""

    def __init__(self, clock):
        self.clock = clock
        self.mouse_t = -99.0

    def axes(self):
        """Опрос движения: (ix, iy, бег)."""
        k = pygame.key.get_pressed()
        ix = (k[pygame.K_d] or k[pygame.K_RIGHT]) - (k[pygame.K_a] or k[pygame.K_LEFT])
        iy = (k[pygame.K_s] or k[pygame.K_DOWN]) - (k[pygame.K_w] or k[pygame.K_UP])
        return ix, iy, bool(k[pygame.K_LSHIFT] or k[pygame.K_RSHIFT])

    @staticmethod
    def mouse_pos():
        return pygame.mouse.get_pos()

    def mouse_recent(self):
        """Двигали ли мышь недавно (тогда фонарь следует за курсором)."""
        return self.clock.t - self.mouse_t < 2.5

    def translate(self, e, state):
        """Событие -> список команд вида (имя, аргумент...) с учётом состояния игры."""
        if e.type == pygame.QUIT:
            return [("quit",)]
        if e.type == pygame.MOUSEMOTION:
            self.mouse_t = self.clock.t
            return []
        if e.type == pygame.MOUSEBUTTONDOWN:
            if state == "play":
                if e.button == 1:
                    return [("toggle_light",)]
                if e.button == 3:
                    return [("throw",)]
            if state == "boss" and e.button == 3:
                return [("boss_shoot",)]
            return []
        if e.type != pygame.KEYDOWN:
            return []
        k = e.key
        enter = k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER)
        if k == pygame.K_F2:
            return [("quality",)]
        if k == pygame.K_F3:
            return [("gentle",)]
        if k == pygame.K_n:
            return [("mute",)]
        if k == pygame.K_F11:
            return [("fullscreen",)]
        if state == "menu":
            if enter:
                return [("start_prologue",)]
            if k == pygame.K_ESCAPE:
                return [("quit",)]
            if k in (pygame.K_LEFT, pygame.K_a):
                return [("diff", -1)]
            if k in (pygame.K_RIGHT, pygame.K_d):
                return [("diff", 1)]
            if k in (pygame.K_1, pygame.K_2, pygame.K_3):
                return [("diff_set", k - pygame.K_1)]
        elif state == "archive":
            if k in (pygame.K_UP, pygame.K_w):
                return [("archive_nav", -1)]
            if k in (pygame.K_DOWN, pygame.K_s):
                return [("archive_nav", 1)]
            if enter:
                return [("archive_read",)]
            if k in (pygame.K_ESCAPE, pygame.K_TAB):
                return [("archive_close",)]
        elif state == "boss":
            if k == pygame.K_1:
                return [("boss_choose", True)]
            if k == pygame.K_2:
                return [("boss_choose", False)]
            if k == pygame.K_3:
                return [("boss_choose", "cure")]
            if k == pygame.K_q:
                return [("boss_reload",)]
            if k == pygame.K_SPACE:
                return [("boss_parry",)]
            if k == pygame.K_F10:
                return [("cheat_boss",)]
        elif state == "floor":
            if enter or k == pygame.K_ESCAPE:
                return [("skip_floor",)]
        elif state == "reading":
            if enter or k == pygame.K_ESCAPE:
                return [("close_note",)]
        elif state == "prologue":
            if enter or k == pygame.K_ESCAPE:
                return [("skip_prologue",)]
        elif state == "serum":
            if k == pygame.K_1:
                return [("serum_choose", 0)]
            if k in (pygame.K_2, pygame.K_ESCAPE):
                return [("serum_choose", 1)]
        elif state == "cinematic":
            if enter or k == pygame.K_ESCAPE:
                return [("skip_cinematic",)]
        elif state == "struggle":                       # вырваться из хватки: только ПРОБЕЛ
            if k == pygame.K_SPACE:
                return [("struggle_press",)]
        elif state == "play":
            table = {pygame.K_ESCAPE: "pause", pygame.K_p: "pause", pygame.K_f: "toggle_light",
                     pygame.K_m: "toggle_map", pygame.K_e: "hide", pygame.K_q: "throw",
                     pygame.K_F9: "cheat_boost", pygame.K_F10: "cheat_win",
                     pygame.K_F8: "cheat_floor", pygame.K_TAB: "archive"}
            if k in table:
                return [(table[k],)]
        elif state == "pause":
            if k in (pygame.K_ESCAPE, pygame.K_p):
                return [("resume",)]
            if k == pygame.K_q:
                return [("to_menu",)]
        elif state == "cutscene":
            if enter or k == pygame.K_ESCAPE:
                return [("skip_cutscene",)]
        elif state == "caught":
            if enter:
                return [("skip_scare",)]
        elif state in ("lose", "win"):
            if enter:
                return [("restart",)]
            if k == pygame.K_ESCAPE:
                return [("to_menu",)]
        return []


# ------------------------------------------------------------------ ПРИЛОЖЕНИЕ
class Game:
    """
    Приложение: окно, главный цикл и конечный автомат состояний
    (menu -> prologue -> floor -> play <-> pause -> pounce -> struggle -> caught -> lose | cinematic | cutscene -> boss -> win).
    Сам ничего не считает и не рисует: связывает компоненты и передаёт им управление.
    """

    after_cin = None         # (этаж, вещи), куда перейти после кат-сцены падения
    from_archive = False     # записка открыта из архива (после закрытия вернёмся в архив)
    lose_boss = False        # поражение произошло в финальном бою (тогда ENTER повторяет бой)

    HINT = "WASD — идти · SHIFT — бежать (шумно!) · МЫШЬ — свет · F — фонарик · E — шкафчик · M — карта"

    def __init__(self):
        pygame.display.set_caption("БУНКЕР-13")
        self.screen = pygame.display.set_mode((SW, SH))
        self.clock = FrameClock()
        self.cfg = Settings()
        self.note = Notifier()
        self.scores = ScoreBoard()
        self.s = Session()
        self.show_loading("ЗАГРУЗКА...")
        self.tex = Textures(progress=self.show_loading)
        self.audio = Audio(progress=self.show_loading)
        self.audio.play("drone", -1)
        self.input = InputRouter(self.clock)
        self.ach = AchievementTracker(audio=self.audio, s=self.s)
        self.atmo = Atmosphere(audio=self.audio, cfg=self.cfg, s=self.s)
        self.monster_view = MonsterRenderer(clock=self.clock, s=self.s, screen=self.screen, tex=self.tex)
        self.camera = Camera(atmo=self.atmo, s=self.s)
        self.pc = PlayerController(camera=self.camera, s=self.s)
        self.torch = Flashlight(atmo=self.atmo, audio=self.audio, note=self.note, s=self.s)
        self.threat = ThreatSystem(s=self.s)
        self.pickups = PickupSystem(audio=self.audio, note=self.note, s=self.s)
        self.stealth = StealthSystem(audio=self.audio, note=self.note, s=self.s)
        self.cheats = Cheats(note=self.note, s=self.s)
        self.minimap = Minimap(clock=self.clock, s=self.s, screen=self.screen)
        self.text = TextRenderer(screen=self.screen)
        self.painter = WorldPainter(tex=self.tex)
        self.lighting = LightingRenderer(cfg=self.cfg, clock=self.clock, s=self.s, screen=self.screen)
        self.sprites = SpriteRenderer(atmo=self.atmo, clock=self.clock, s=self.s, screen=self.screen, tex=self.tex, text=self.text)
        self.scare = JumpscareRenderer(clock=self.clock, s=self.s, screen=self.screen, sprites=self.sprites, tex=self.tex, text=self.text)
        self.struggle = StruggleFight(audio=self.audio, s=self.s)
        self.struggle_view = StruggleRenderer(cfg=self.cfg, clock=self.clock, scare=self.scare, s=self.s, screen=self.screen,
                                              sprites=self.sprites, struggle=self.struggle, tex=self.tex, text=self.text)
        self.prologue = PrologueSystem(audio=self.audio, s=self.s)
        self.prologue_view = PrologueRenderer(clock=self.clock, prologue=self.prologue, screen=self.screen, tex=self.tex, text=self.text)
        self.pounce = PounceSystem(audio=self.audio, s=self.s)
        self.pounce_view = PounceRenderer(cfg=self.cfg, clock=self.clock, pounce=self.pounce, scare=self.scare, s=self.s,
                                          screen=self.screen, sprites=self.sprites, tex=self.tex)
        self.cin = CinematicSystem(audio=self.audio, s=self.s)
        self.cin_view = CinematicRenderer(cin=self.cin, clock=self.clock, screen=self.screen, tex=self.tex, text=self.text)
        self.evac = EvacSystem(audio=self.audio, note=self.note, s=self.s)
        self.fx = PostFX(atmo=self.atmo, cfg=self.cfg, clock=self.clock, s=self.s, screen=self.screen, tex=self.tex)
        self.hud = Hud(cfg=self.cfg, clock=self.clock, minimap=self.minimap, note=self.note, s=self.s, screen=self.screen, text=self.text)
        self.screens = ScreenRenderer(ach=self.ach, audio=self.audio, cfg=self.cfg, clock=self.clock, lighting=self.lighting, s=self.s, scores=self.scores, screen=self.screen, tex=self.tex, text=self.text)
        self.cut = FinalCutscene(atmo=self.atmo, audio=self.audio, cfg=self.cfg, note=self.note, s=self.s)
        self.cutview = CutsceneRenderer(atmo=self.atmo, cfg=self.cfg, cut=self.cut, fx=self.fx, lighting=self.lighting, monster_view=self.monster_view, painter=self.painter, s=self.s, screen=self.screen, sprites=self.sprites, tex=self.tex, text=self.text)
        self.boss = BossFight(audio=self.audio, s=self.s)
        self.music = MusicDirector(atmo=self.atmo, audio=self.audio, boss=self.boss, s=self.s)
        self.radio = RadioSystem(audio=self.audio, s=self.s)
        self.achview = AchievementRenderer(ach=self.ach, screen=self.screen, text=self.text)
        self.radioview = RadioRenderer(clock=self.clock, radio=self.radio, screen=self.screen, text=self.text)
        self.playview = PlayView(atmo=self.atmo, camera=self.camera, cfg=self.cfg, clock=self.clock, fx=self.fx, hud=self.hud, lighting=self.lighting, monster_view=self.monster_view, painter=self.painter, s=self.s, screen=self.screen, sprites=self.sprites, tex=self.tex, torch=self.torch)
        self.bossview = BossRenderer(boss=self.boss, clock=self.clock, fx=self.fx, lighting=self.lighting, monster_view=self.monster_view, s=self.s, screen=self.screen, sprites=self.sprites, tex=self.tex, text=self.text)
        self.state = "menu"
        pygame.mouse.set_visible(True)

    # ---------------------------------------------------------- вспомогательное
    def show_loading(self, text):
        self.screen.fill((4, 4, 6))
        f = pygame.font.SysFont("dejavusansmono,couriernew,consolas,monospace", 30, bold=True)
        img = f.render(text, True, (140, 40, 40))
        self.screen.blit(img, img.get_rect(center=(SW // 2, SH // 2)))
        pygame.display.flip()
        pygame.event.pump()

    # ---------------------------------------------------------- переходы между состояниями
    def start_game(self):
        """Новая игра: показывает карточку первого этажа, затем начинает его."""
        self.audio.restore()
        self.begin_floor_card(0, None)

    def begin_floor_card(self, floor, carry):
        self.audio.stop("alarm")
        self.pending_floor, self.pending_carry = floor, carry
        self.audio.play("ding", vol=0.7)
        self.audio.play("hum", 2)                          # гул шахты лифта, пока идёт карточка этажа
        self.screens.begin_floor(floor)
        self.screens.start_fade(0.6)
        self.state = "floor"
        pygame.mouse.set_visible(False)

    def start_floor(self):
        """Строит этаж self.pending_floor и пускает игрока в него."""
        floor = self.pending_floor
        self.audio.stop("hum")
        self.s.start(self.cfg.dc, floor, self.pending_carry)
        self.atmo.reset()
        self.minimap.reset()
        self.note.clear()
        self.radio.clear()
        self.radio.on_event("floor_start", floor)
        self.ach.new_floor()
        self.note.say(self.HINT if floor == 0 else "Ключей на этаже: %d. Лифт — в тупике, подальше от старта." % FLOORS[floor]["keys"], 9.0)
        self.playview.prepare()
        self.screens.start_fade(0.7)
        self.state = "play"
        pygame.mouse.set_visible(False)

    def begin_cinematic(self, name):
        """Кат-сцена без управления: 'fall' (лифт падает на -10) или 'blast' (подрыв завала)."""
        self.audio.stop("alarm")
        self.s.cin_name = name
        self.cin.begin(name)
        self.cin_view.prepare()
        self.screens.start_fade(0.4)
        self.state = "cinematic"
        pygame.mouse.set_visible(False)

    def begin_pounce(self):
        """Монстр прыгает на камеру (как Фокси в FNaF 2) — мгновение спустя он уже на герое."""
        self.audio.stop("alarm")
        self.pounce.begin()
        self.pounce_view.begin()
        self.s.hidden = False
        self.state = "pounce"
        pygame.mouse.set_visible(False)

    def begin_struggle(self):
        """Монстр схватил героя: 3 секунды, 10 нажатий ПРОБЕЛА."""
        self.audio.stop("alarm")
        self.audio.play("growl")
        self.struggle.begin()
        self.struggle_view.begin()
        self.s.hidden = False
        self.state = "struggle"
        pygame.mouse.set_visible(False)

    def end_struggle(self):
        """Вырвался: игрок отброшен подальше, монстр оглушён на 3 секунды, герой неуязвим на время рывка."""
        s = self.s
        p, m = s.player, s.monster
        far = [c for c in s.floors if 360 < math.hypot((c[0] + 0.5) * TILE - m.x, (c[1] + 0.5) * TILE - m.y) < 800]
        far.sort(key=lambda c: math.hypot((c[0] + 0.5) * TILE - p.x, (c[1] + 0.5) * TILE - p.y))
        if far:
            c = random.choice(far[:6])
            p.x, p.y = (c[0] + 0.5) * TILE, (c[1] + 0.5) * TILE
        m.stun = 3.0
        m.state, m.timer = "search", 3.0
        s.grace = 3.5
        s.pending_catch = False
        s.hidden = False
        self.note.say("ВЫРВАЛСЯ! Монстр оглушён — беги!", 3.5)
        self.screens.start_fade(0.5)
        self.state = "play"
        pygame.mouse.set_visible(False)

    def begin_caught(self):
        self.scare.begin(0.0 if self.lose_boss else None)      # в бою монстр атакует слева
        self.state = "caught"
        self.s.hidden = False
        self.audio.stop("alarm")
        self.audio.silence()
        self.audio.play("dread")

    def begin_boss(self):
        """Старт финального боя (после кат-сцены и при повторе после поражения)."""
        self.audio.stop("alarm")
        self.audio.restore()
        self.boss.begin()
        self.bossview.prepare()
        self.atmo.danger, self.atmo.pulse, self.atmo.shake = 0.55, 0.0, (0, 0)
        self.s.has_gun = True
        self.s.ending = "normal"
        self.lose_boss = False
        self.radio.clear()
        self.radio.on_event("boss_start")
        self.ach.new_fight()
        self.screens.start_fade(0.5)
        self.state = "boss"
        pygame.mouse.set_visible(False)

    def begin_note(self, data):
        floor, idx = data
        self.from_archive = False
        self.screens.begin_note(floor, idx)
        self.state = "reading"

    def archive_items(self):
        return sorted(self.s.notes_read)

    def begin_finale(self):
        self.audio.stop("alarm")
        self.screens.start_fade(0.8)
        self.cut.start()
        self.cutview.prepare()
        self.state = "cutscene"
        pygame.mouse.set_visible(False)

    def finish_finale(self):
        self.state = "win"
        self.screens.begin_win()
        self.screens.start_fade(1.0)
        self.audio.play("win")
        pygame.mouse.set_visible(True)
        self.atmo.danger = 0.0
        self.atmo.shake = (0, 0)
        self.scores.submit(self.s.finish_time, self.cfg.diff, self.s.cheated)

    def dispatch_events(self):
        """События модели (Session.emit) -> реакции приложения."""
        for ev, data in self.s.drain():
            self.radio.on_event(ev, data)
            self.ach.on_event(ev, data)
            if ev == "note":
                self.begin_note(data)
            elif ev == "floor_cleared":              # data — номер следующего этажа
                self.audio.play("win")
                if self.s.floor == 0 and data == 3:  # с -3 лифт не поднимается: трос рвётся, кабина падает на -10
                    self.after_cin = (3, self.s.carry())
                    self.begin_cinematic("fall")
                elif data == 5:                      # прибытие на аванпост: сцена у лифта, потом карточка этажа
                    self.after_cin = (5, self.s.carry())
                    self.begin_cinematic("outpost")
                else:
                    self.begin_floor_card(data, self.s.carry())
            elif ev in ("fall_done", "outpost_done"):
                self.begin_floor_card(*self.after_cin)
            elif ev == "evac_start":                 # консоль аванпоста: вызов эвакуации, отсчёт 60 секунд
                self.evac.start()
            elif ev == "evac_arrive":
                self.begin_cinematic("evac")
            elif ev == "evac_done":                  # концовка: эвакуация вертолётом
                self.s.ending = "evac"
                self.s.finish_time = self.s.play_time
                self.finish_finale()
            elif ev == "serum_offer":                # ампула сыворотки: выбор
                self.screens.begin_serum()
                self.state = "serum"
            elif ev == "serum_done":                 # концовка: герой стал чудовищем
                self.s.ending = "serum"
                self.s.finish_time = self.s.play_time
                self.finish_finale()
            elif ev == "secret_blast":               # динамит у завала: подрыв
                self.begin_cinematic("blast")
            elif ev == "blast_done":                 # новая концовка: выход через шахту
                self.s.ending = "blast"
                self.s.finish_time = self.s.play_time
                self.finish_finale()
            elif ev == "monster_alert":
                self.audio.play("growl")
            elif ev == "monster_seen":
                self.audio.play("sting")
                self.audio.play("static", vol=0.5)
            elif ev == "watcher":
                self.audio.play("breath", vol=0.7)
                self.audio.play("static", vol=0.4)
            elif ev == "caught":                     # поймал: бросок на камеру, затем схватка (10 раз ПРОБЕЛ за 3 секунды)
                self.lose_boss = False
                self.begin_pounce()
            elif ev == "pounce_done":
                self.begin_struggle()
            elif ev == "struggle_won":
                self.end_struggle()
            elif ev == "struggle_lost":              # не вырвался — скример
                self.begin_caught()
            elif ev == "prologue_done":
                self.start_game()
            elif ev == "third_key":
                self.stealth.trigger_alarm()
            elif ev == "exit_reached":
                self.begin_finale()
            elif ev == "cutscene_done":
                self.begin_boss()
            elif ev == "boss_won":
                self.finish_finale()
            elif ev == "boss_lost":
                self.lose_boss = True
                self.begin_caught()

    # ---------------------------------------------------------- команды ввода
    def toast(self, text):
        if self.state == "play":
            self.note.say(text, 2.0)

    def execute(self, cmd):
        name = cmd[0]
        if name == "quit":
            pygame.quit()
            sys.exit()
        elif name == "start_prologue":
            self.audio.restore()
            self.prologue.begin()
            self.prologue_view.prepare()
            self.state = "prologue"
            pygame.mouse.set_visible(False)
        elif name == "skip_prologue":
            self.prologue.skip()
        elif name == "skip_cinematic":
            self.cin.skip()
        elif name == "struggle_press":
            self.struggle.press()
        elif name == "start_game":
            self.start_game()
        elif name == "skip_scare":                 # повторные смерти: пропуск сцены (не раньше разрыва)
            if self.scare.t > self.scare.DREAD + self.scare.GRAB + 0.5:
                self.scare.t = self.scare.TOTAL - 0.01
                self.scare.i = len(self.scare.sched) - 1       # пропускаем всё, кроме финала (звук сердца не включится)
        elif name == "skip_floor":
            self.start_floor()
        elif name == "close_note":
            self.state = "archive" if self.from_archive else "play"
            self.from_archive = False
        elif name == "archive":
            self.screens.begin_archive()
            self.state = "archive"
        elif name == "archive_nav":
            n = len(self.archive_items())
            self.screens.arch_sel = int(clamp(self.screens.arch_sel + cmd[1], 0, max(0, n - 1)))
        elif name == "archive_read":
            items = self.archive_items()
            if items:
                fl, idx = items[int(clamp(self.screens.arch_sel, 0, len(items) - 1))]
                self.screens.begin_note(fl, idx)
                self.from_archive = True
                self.state = "reading"
        elif name == "archive_close":
            self.state = "play"
        elif name == "serum_choose":
            if cmd[1] == 0:                          # выпил
                self.begin_cinematic("serum_end")
            else:                                    # оставил
                for it in self.s.serum:
                    it["alive"] = False
                self.state = "play"
        elif name == "boss_choose":
            self.boss.resolve(cmd[1])
        elif name == "cheat_floor":
            self.cheats.floor()
        elif name == "diff":
            self.cfg.cycle_diff(cmd[1])
            self.audio.play("click", vol=0.5)
        elif name == "diff_set":
            self.cfg.set_diff(cmd[1])
            self.audio.play("click", vol=0.5)
        elif name == "pause":
            self.screens.capture()
            self.state = "pause"
            pygame.mouse.set_visible(True)
        elif name == "resume":
            self.state = "play"
            pygame.mouse.set_visible(False)
        elif name == "to_menu":
            self.audio.restore()
            self.state = "menu"
            pygame.mouse.set_visible(True)
        elif name == "toggle_light":
            self.torch.toggle()
        elif name == "toggle_map":
            self.cfg.show_map = not self.cfg.show_map
        elif name == "hide":
            self.stealth.try_hide()
        elif name == "throw":
            self.stealth.throw_bottle()
        elif name == "cheat_boost":
            self.cheats.boost()
        elif name == "cheat_win":
            self.cheats.win()
        elif name == "skip_cutscene":
            if self.cut.cs_t > 1.0:
                self.begin_boss()
        elif name == "boss_shoot":
            self.boss.shoot()
        elif name == "boss_reload":
            self.boss.reload()
        elif name == "boss_parry":
            self.boss.parry()
        elif name == "cheat_boss":
            self.boss.kill(True)
        elif name == "restart":
            if self.state == "lose" and self.lose_boss:
                self.begin_boss()
            else:
                self.start_game()
        elif name == "quality":
            self.cfg.quality = 1 - self.cfg.quality
            self.toast("Качество: " + ("высокое" if self.cfg.quality else "низкое"))
        elif name == "gentle":
            self.cfg.gentle = not self.cfg.gentle
            self.toast("Щадящий режим: " + ("вкл (меньше тряски и вспышек)" if self.cfg.gentle else "выкл"))
        elif name == "mute":
            self.audio.set_muted(not self.audio.muted)
            self.toast("Звук выключен" if self.audio.muted else "Звук включён")
        elif name == "fullscreen":
            pygame.display.toggle_fullscreen()
        self.dispatch_events()

    # ---------------------------------------------------------- покадровая работа
    def update_play(self, dt):
        s = self.s
        s.play_time += dt
        ix, iy, sprint = self.input.axes()
        self.pc.update(dt, ix, iy, sprint, self.input.mouse_pos(), self.input.mouse_recent())
        self.torch.update(dt)
        self.threat.update(dt)
        self.dispatch_events()
        if self.state != "play":                 # монстр поймал игрока
            return
        self.atmo.update(dt)
        self.pickups.update(dt)
        self.evac.update(dt)
        self.stealth.update(dt)
        self.minimap.update()
        self.note.tick(dt)
        self.dispatch_events()

    def step(self, dt):
        st = self.state
        if st == "menu":
            self.screens.draw_menu()
        elif st == "play":
            self.update_play(dt)
            if self.state == "play":
                self.playview.draw()
        elif st == "prologue":
            self.prologue.update(dt)
            self.dispatch_events()
            if self.state == "prologue":
                self.prologue_view.draw()
        elif st == "pounce":
            self.pounce.update(dt)
            self.dispatch_events()
            if self.state == "pounce":
                self.pounce_view.draw()
        elif st == "serum":
            self.screens.draw_serum()
        elif st == "cinematic":
            self.cin.update(dt)
            self.dispatch_events()
            if self.state == "cinematic":
                self.cin_view.draw()
        elif st == "struggle":
            self.struggle.update(dt)
            self.dispatch_events()
            if self.state == "struggle":
                self.struggle_view.draw()
        elif st == "cutscene":
            self.cut.update(dt)
            self.dispatch_events()
            if self.state == "cutscene":
                self.cutview.draw()
        elif st == "pause":
            self.screens.draw_pause()
        elif st == "floor":
            if self.screens.draw_floor_card(dt):
                self.start_floor()
        elif st == "reading":
            self.screens.draw_note(dt)
        elif st == "archive":
            self.screens.draw_archive(self.archive_items())
        elif st == "boss":
            self.boss.update(dt)
            self.dispatch_events()
            if self.state == "boss":
                self.bossview.draw()
        elif st == "caught":
            res = self.scare.advance(dt)
            if res == "scream":                      # бросок: крик несколькими слоями
                self.audio.play("scare")
                self.audio.play("shriek")
            elif res == "rip":                       # героя рвут: треск плоти, хруст костей, глухой удар
                self.audio.play("rip")
                self.audio.play("crunch")
                self.audio.play("sub")
                self.audio.play("squelch", vol=0.7)
            elif res == "flatline":                  # сердце остановилось
                self.audio.play("flatline", vol=0.55)
            elif res == "thump":                     # сердце колотится всё быстрее
                self.audio.play("heart", vol=min(1.0, 0.45 + self.scare.t * 0.7))
            if res == "done":
                self.state = "lose"
                self.screens.retry = self.lose_boss
                self.screens.begin_lose()
                self.screens.start_fade(0.8)
                pygame.mouse.set_visible(True)
            else:
                self.scare.draw()
        elif st == "lose":
            self.screens.draw_lose(dt)
        elif st == "win":
            self.screens.draw_win()
        if self.state in ("play", "boss", "cutscene"):
            self.radio.update(dt)
        if self.state in ("play", "pause", "boss", "cutscene"):
            self.radioview.draw()
        self.ach.update(dt)
        if self.state in ("play", "boss", "cutscene", "pause", "win", "floor"):
            self.achview.draw()
        self.music.update(dt, self.state)
        self.screens.draw_fade(dt)

    def run(self):
        while True:
            dt = self.clock.tick()
            if self.state in ("play", "cutscene") and self.cfg.watch_frame(self.clock.raw):
                self.note.say("Низкий FPS: качество снижено (F2 — вернуть)", 4.0)
            for e in pygame.event.get():
                for cmd in self.input.translate(e, self.state):
                    self.execute(cmd)
            self.step(dt)
            pygame.display.flip()


def main():
    try:
        pygame.mixer.pre_init(22050, -16, 1, 512)
    except pygame.error:
        pass
    pygame.init()
    Game().run()


if __name__ == "__main__":
    main()