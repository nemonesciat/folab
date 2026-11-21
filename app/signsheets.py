"""Waikiki's sign pictures redrawn with signpaint's lettering and signart's pictures (the user's look, 21 Nov 2026: "signs
should be made better stylistically", "little umbrellas, palm trees, parrots").

Each sheet keeps the size and the panel layout of the picture it replaces (the models show a panel through a look's
'region'), so no model changes: only the pictures. Every panel is painted on its own small picture and pasted in, and a
shaped board (an arrow, a shield, an arch) stands on a painted backing plate, as a cut-out sign on a flat board would:
the sheets stay solid. Imported last by modelsets._all_sets, so these painters replace the sets' own."""
import modelsets
import signart as sa
import signpaint as sp
import texpaint as tp
import texwear as tw

CREAM, RED, TEAL_INK = (240, 228, 200), (190, 52, 44), (28, 96, 106)
SAND, SEA, CORAL = (238, 224, 186), (44, 132, 140), (236, 120, 100)
DARK = (26, 32, 40)


def panel(w, h, board='enamel', ground=CREAM, shape='rect', back=(70, 74, 78), seed=2000):
    """(colour, glow) of one panel: a board of `shape` filling it (inset on a backing plate if not a rectangle)."""
    if shape == 'rect':
        return sp.blank(w, h, board, ground, seed)
    c, g = sp.blank(w, h, board, ground, seed, box=(3, 3, w - 3, h - 3), shape=shape)
    plate = tw.Field(w, h, seed + 5, cells=4, octaves=3)
    for p in range(w * h):
        a = c.a[p]
        if a < 1:
            col = tw.mul(back, 0.86 + 0.2 * plate.v[p])
            c.rgb[p] = tw.mix(col, c.rgb[p], a)
            if a < 0.5:
                c.ht[p], c.gloss[p] = 0.46, 20
    c.a = None
    return c, g


def paste(sheet, glow, c, g, x0, y0):
    for y in range(c.h):
        so, do = y * c.w, (y0 + y) * sheet.w + x0
        sheet.rgb[do:do + c.w] = c.rgb[so:so + c.w]
        sheet.ht[do:do + c.w] = c.ht[so:so + c.w]
        sheet.gloss[do:do + c.w] = c.gloss[so:so + c.w]
        if glow is not None and g is not None:
            glow.rgb[do:do + c.w] = g.rgb[so:so + c.w]


def sheet(w, h, panels):
    """A sheet of panels: [(x0, y0, w, h, painter(w, h) -> (c, g))]. Returns the colour Picture; the glow is kept as
    .glow (None if nothing lights)."""
    out = tw.Picture(w, h, gloss=24)
    glow = tw.Picture(w, h, gloss=0)
    glow.rgb = [(0, 0, 0)] * (w * h)
    for x0, y0, pw, ph, fn in panels:
        c, g = fn(pw, ph)
        paste(out, glow, c, g, x0, y0)
    out.glow = glow if sp.lit_any(glow) else None
    return out


def _grid(w, h, cols, rows, fns):
    pw, ph = w // cols, h // rows
    return sheet(w, h, [((k % cols) * pw, (k // cols) * ph, pw, ph, fn) for k, fn in enumerate(fns)])


def _bands(w, h, fns):
    return _grid(w, h, 1, len(fns), fns)


def _two(big, small, style, ink, small_ink=None, outline=None, ink2=None, split=0.62, small_style='deco', seed=0):
    """Draws a big line over smaller ones into (c, g) within box."""
    def draw(c, g, box):
        x0, y0, x1, y1 = box
        cut = y0 + (y1 - y0) * (split if small else 1.0)
        sp.words_on(c, g, big, style, (x0, y0, x1, cut), ink, outline=outline, seed=seed, ink2=ink2)
        if small:
            n = len(small)
            hh = (y1 - cut) / n
            for k, t in enumerate(small):
                sp.words_on(c, g, t, small_style, (x0 + (x1 - x0) * 0.1, cut + k * hh, x1 - (x1 - x0) * 0.1, cut + (k + 1) * hh), small_ink or ink, seed=seed + 1 + k)
    return draw


# ---------- the street's signs (waikiki/signs: 4 x 2 panels a quarter wide, half high) ----------

def _stall(words, small, ground, ink, art, style='brush', shape='rect', outline=None, seed=0):
    def fn(w, h):
        c, g = panel(w, h, 'enamel', ground, shape, seed=seed)
        art(c, w, h)
        _two(words, small, style, ink, outline=outline, seed=seed + 2)(c, g, (w * 0.1, h * 0.1, w * 0.9, h * (0.62 if small else 0.62)))
        sp.weather(c, 0.45, seed + 3)
        return c, g
    return fn


def waikiki_signs():
    W, H = 1024, 512
    fns = [
        _stall('BUS', ('STOP',), (246, 204, 70), DARK, lambda c, w, h: sa.bus(c, w * 0.5, h * 0.9, w * 0.6), 'deco', seed=2010),
        _stall('SURF SHOP', ('BOARDS  WAX',), SAND, TEAL_INK, lambda c, w, h: (sa.waves(c, w * 0.06, w * 0.94, h * 0.92, h * 0.2, curls=3),
                                                                            sa.surfboard(c, w * 0.85, h * 0.6, h * 0.5, turn=-80, colour=sa.RED)), outline=CREAM, seed=2020),
        _stall('FRESH POI', (), (210, 196, 220), (90, 40, 110), lambda c, w, h: sa.hibiscus(c, w * 0.5, h * 0.78, h * 0.15, colour=(170, 90, 180)), seed=2030),
        _stall('LEIS', ('50 CENTS',), (250, 236, 216), RED, lambda c, w, h: [sa.hibiscus(c, w * (0.18 + 0.16 * k), h * (0.86 - 0.05 * (k % 2)), h * 0.08, colour=(sa.PINK, sa.YELLOW, sa.RED, sa.ORANGE, sa.PINK)[k], turn=k * 30) for k in range(5)], seed=2040),
        _stall('SHAVE ICE', ('ALL FLAVORS',), (150, 214, 220), (200, 50, 90), lambda c, w, h: sa.umbrella(c, w * 0.82, h * 0.7, h * 0.24, tilt=20), outline=CREAM, seed=2050),
        _stall('FRUIT', ('PINEAPPLE',), (250, 220, 120), (60, 110, 50), lambda c, w, h: sa.palm(c, w * 0.85, h * 0.98, h * 0.5, lean=-10), seed=2060),
        _stall('FRESH FISH', (), (200, 226, 230), (24, 72, 120), lambda c, w, h: sa.waves(c, w * 0.08, w * 0.92, h * 0.94, h * 0.22, curls=3, colour=(60, 120, 170)), seed=2070),
        _stall('LIFEGUARD', ('ON DUTY',), (220, 60, 50), (250, 246, 236), lambda c, w, h: sa.shape(c, [(w * 0.42, h * 0.7), (w * 0.58, h * 0.7), (w * 0.58, h * 0.76), (w * 0.64, h * 0.76), (w * 0.64, h * 0.82), (w * 0.58, h * 0.82), (w * 0.58, h * 0.88), (w * 0.42, h * 0.88), (w * 0.42, h * 0.82), (w * 0.36, h * 0.82), (w * 0.36, h * 0.76), (w * 0.42, h * 0.76)], (250, 246, 236), line=0), 'deco', seed=2080),
    ]
    return _grid(W, H, 4, 2, fns)


# ---------- the motels' boards (waikiki/motels: 2 x 2) ----------

def _motel_board(name, small, ground, ink, art, seed, style='brush', ribbon=True):
    def fn(w, h):
        c, g = panel(w, h, 'enamel', ground, 'rect', seed=seed)
        art(c, w, h)
        if ribbon:
            sa.ribbon(c, (w * 0.25, h * 0.07, w * 0.75, h * 0.38))
            sp.words_on(c, g, name, style, (w * 0.26, h * 0.08, w * 0.74, h * 0.37), ink, seed=seed + 1)
        else:
            sp.words_on(c, g, name, style, (w * 0.08, h * 0.08, w * 0.92, h * 0.44), ink, outline=CREAM, seed=seed + 1)
        for k, t in enumerate(small):
            sa.shape(c, sp.rounded(w * 0.24, h * (0.52 + 0.2 * k), w * 0.76, h * (0.68 + 0.2 * k), 8), DARK, line=3)
            sp.words_on(c, g, t, 'deco', (w * 0.27, h * (0.535 + 0.2 * k), w * 0.73, h * (0.665 + 0.2 * k)), CREAM, seed=seed + 2 + k)
        sp.weather(c, 0.45, seed + 5)
        return c, g
    return fn


def motels():
    W, H = 512, 512
    fns = [
        _motel_board('MAHALO', ('MOTOR INN', 'VACANCY'), (40, 120, 130), RED, lambda c, w, h: (sa.palm(c, w * 0.1, h * 0.98, h * 0.7, lean=8), sa.palm(c, w * 0.92, h * 0.98, h * 0.62, lean=-10)), 2100),
        _motel_board('SEA BREEZE', ('MOTEL', 'POOL  TV'), (150, 210, 200), TEAL_INK, lambda c, w, h: (sa.sunset(c, w * 0.5, h * 0.5, h * 0.3), sa.waves(c, 0, w, h, h * 0.16, curls=4)), 2110, ribbon=False),
        _motel_board('KONA KAI', ('COURTS',), (238, 128, 108), (250, 240, 220), lambda c, w, h: (sa.palm(c, w * 0.12, h * 0.98, h * 0.66, lean=12), sa.parrot(c, w * 0.86, h * 0.9, h * 0.36, facing=-1)), 2120, ribbon=False),
        _motel_board('TIKI ROOM', ('COCKTAILS',), (110, 70, 44), (176, 46, 32), lambda c, w, h: (sa.tiki_face(c, w * 0.12, h * 0.7, h * 0.4), sa.tiki_face(c, w * 0.88, h * 0.7, h * 0.4),
                                                                                           sa.umbrella(c, w * 0.5, h * 0.9, h * 0.14, tilt=0)), 2130),
    ]
    return _grid(W, H, 2, 2, fns)


# ---------- the kiosk (kiosk_signs: a band over two halves) ----------

def kiosk():
    W, H = 512, 256

    def top(w, h):
        c, g = panel(w, h, 'enamel', SAND, 'rect', seed=2200)
        sa.waves(c, w * 0.02, w * 0.3, h * 0.96, h * 0.4, curls=2)
        sa.surfboard(c, w * 0.92, h * 0.94, h * 0.9, turn=-76, colour=sa.TEAL)
        sp.words_on(c, g, 'SURF & SNACKS', 'brush', (w * 0.26, h * 0.12, w * 0.86, h * 0.88), TEAL_INK, outline=CREAM, seed=2201)
        sp.weather(c, 0.4, 2202)
        return c, g

    def menu(w, h):
        c, g = panel(w, h, 'enamel', (248, 244, 232), 'rect', seed=2210)
        for k, (t, ink) in enumerate((('SHAVE ICE', RED), ('COLD DRINKS', TEAL_INK), ('BOARD RENTAL', TEAL_INK))):
            sp.words_on(c, g, t, 'deco', (w * 0.08, h * (0.08 + 0.29 * k), w * 0.92, h * (0.33 + 0.29 * k)), ink, seed=2211 + k)
        sp.weather(c, 0.35, 2215)
        return c, g

    def aloha(w, h):
        c, g = panel(w, h, 'enamel', (246, 204, 70), 'rect', seed=2220)
        sa.hibiscus(c, w * 0.12, h * 0.5, h * 0.22, colour=RED, turn=10)
        sa.hibiscus(c, w * 0.88, h * 0.5, h * 0.22, colour=sa.PINK, turn=40)
        sp.words_on(c, g, 'ALOHA', 'brush', (w * 0.24, h * 0.14, w * 0.76, h * 0.86), RED, outline=CREAM, seed=2221, ink2=(140, 30, 30))
        sp.weather(c, 0.35, 2222)
        return c, g
    return sheet(W, H, [(0, 0, 512, 128, top), (0, 128, 256, 128, menu), (256, 128, 256, 128, aloha)])


# ---------- hotel towers' names (hotel/signs: four bands) ----------

def _name_band(words, ground, ink, art, style='deco', board='enamel', outline=None, seed=0, ink2=None):
    def fn(w, h):
        c, g = panel(w, h, board, ground, 'rect', seed=seed)
        lo, hi = art(c, w, h) or (0.1, 0.9)
        sp.words_on(c, g, words, style, (w * lo, h * 0.12, w * hi, h * 0.88), ink, outline=outline, seed=seed + 1, ink2=ink2)
        sp.weather(c, 0.45, seed + 2)
        return c, g
    return fn


def hotel_signs():
    fns = [
        _name_band('MAKAI TOWER', (232, 232, 222), TEAL_INK, lambda c, w, h: (sa.waves(c, w * 0.02, w * 0.14, h * 0.96, h * 0.6, curls=1), sa.waves(c, w * 0.86, w * 0.98, h * 0.96, h * 0.6, curls=1), (0.16, 0.84))[-1], seed=2300),
        _name_band('BLUE LAGOON', (60, 150, 170), (250, 246, 236), lambda c, w, h: (sa.palm(c, w * 0.06, h * 1.0, h * 0.95, lean=8), sa.palm(c, w * 0.94, h * 1.0, h * 0.9, lean=-8), (0.14, 0.86))[-1], style='brush', outline=TEAL_INK, seed=2310),
        _name_band('PINK PEARL HOTEL', (246, 226, 214), (196, 70, 96), lambda c, w, h: (sa.hibiscus(c, w * 0.06, h * 0.5, h * 0.34, colour=sa.PINK), sa.hibiscus(c, w * 0.94, h * 0.5, h * 0.34, colour=sa.PINK, turn=36), (0.13, 0.87))[-1], seed=2320),
        _name_band('KAHUNA PALMS', (246, 204, 70), RED, lambda c, w, h: (sa.palm(c, w * 0.06, h * 1.0, h * 0.95, lean=10), sa.parrot(c, w * 0.93, h * 0.92, h * 0.8, facing=-1), (0.13, 0.86))[-1], style='brush', outline=CREAM, ink2=(140, 30, 30), seed=2330),
    ]
    return _bands(512, 512, fns)


# ---------- the coast's (coast/signs) and the resort's (resort/signs): eight bands ----------

def coast_signs():
    import coastset
    old = coastset._signs                      # (its fish band, the fifth, is kept as it was drawn)
    fish_src = old()
    lines = coastset.SIGN_LINES
    looks = [(SAND, TEAL_INK, 'brush', lambda c, w, h: sa.waves(c, w * 0.02, w * 0.16, h * 0.96, h * 0.7, curls=1)),
             ((60, 150, 160), CREAM, 'deco', lambda c, w, h: sa.palm(c, w * 0.05, h * 1.0, h * 0.95, lean=8)),
             ((250, 246, 236), RED, 'brush', lambda c, w, h: sa.hibiscus(c, w * 0.06, h * 0.5, h * 0.34, colour=RED)),
             ((246, 204, 70), TEAL_INK, 'deco', lambda c, w, h: sa.waves(c, w * 0.02, w * 0.16, h * 0.96, h * 0.7, curls=1, colour=(40, 100, 160))),
             None,
             ((240, 240, 232), TEAL_INK, 'deco', lambda c, w, h: sa.sunset(c, w * 0.08, h * 0.9, h * 0.5)),
             (SAND, RED, 'brush', lambda c, w, h: sa.umbrella(c, w * 0.07, h * 0.18, h * 0.6, tilt=-15)),
             ((250, 250, 244), RED, 'deco', lambda c, w, h: None)]
    fns = []
    for n, t in enumerate(lines):
        if looks[n] is None:
            fns.append(lambda w, h, n=n: (_crop(fish_src, 0, n * h, w, h), None))
            continue
        ground, ink, style, art = looks[n]
        fns.append(_name_band(t, ground, ink, lambda c, w, h, art=art: (art(c, w, h), (0.17, 0.92))[-1], style=style, outline=CREAM if style == 'brush' else None, seed=2400 + 10 * n))
    return _bands(1024, 1024, fns)


def _crop(src, x0, y0, w, h):
    c = tw.Picture(w, h, gloss=24)
    for y in range(h):
        so = (y0 + y) * src.w + x0
        c.rgb[y * w:(y + 1) * w] = src.rgb[so:so + w]
        c.ht[y * w:(y + 1) * w] = src.ht[so:so + w]
    return c


def resort_signs():
    import resortset
    lines = resortset.SIGN_LINES
    looks = [((40, 120, 130), CREAM, 'brush', 'palm'), ((238, 128, 108), CREAM, 'deco', 'hibiscus'), ((60, 150, 170), CREAM, 'brush', 'waves'),
             (SAND, RED, 'deco', 'sunset'), (DARK, (250, 80, 70), 'tube', None), ((246, 204, 70), RED, 'deco', 'umbrella'),
             ((248, 244, 232), TEAL_INK, 'deco', None), ((238, 128, 108), (250, 240, 220), 'brush', 'tiki')]
    art_of = {'palm': lambda c, w, h: sa.palm(c, w * 0.06, h * 1.0, h * 0.95, lean=8),
              'hibiscus': lambda c, w, h: sa.hibiscus(c, w * 0.07, h * 0.5, h * 0.34),
              'waves': lambda c, w, h: sa.waves(c, w * 0.01, w * 0.16, h * 0.96, h * 0.7, curls=1),
              'sunset': lambda c, w, h: sa.sunset(c, w * 0.08, h * 0.92, h * 0.5),
              'umbrella': lambda c, w, h: sa.umbrella(c, w * 0.07, h * 0.16, h * 0.62, tilt=-15),
              'tiki': lambda c, w, h: sa.tiki_face(c, w * 0.07, h * 0.5, h * 0.8)}
    fns = []
    for n, t in enumerate(lines):
        ground, ink, style, art = looks[n]
        a = art_of.get(art)
        fns.append(_name_band(t, ground, ink, (lambda c, w, h, a=a: (a(c, w, h), (0.16, 0.92))[-1]) if a else (lambda c, w, h: (0.08, 0.92)),
                              style=style, outline=DARK if style == 'brush' else None, seed=2500 + 10 * n))
    return _bands(1024, 1024, fns)


# ---------- painted names on walls (the historic hotels', the tank) ----------

def wall_letters(words, wall, ink, w=1024, h=128, seed=2600, style='deco', outline=None, neon=None):
    """A name painted straight onto a wall: the wall's own render behind, no board, letters faded and flaking. neon: a
    tube's colour run down the middle of each letter (deco only), lit in the picture's .glow."""
    c, g = sp.blank(w, h, 'stucco', wall, seed)
    _plain(c, wall, seed)                       # (painted over the board: no rim, the wall runs on)
    box = (w * 0.03, h * 0.12, w * 0.97, h * 0.88)
    sp.words_on(c, g, words, style, box, ink, outline=outline, seed=seed + 1, wear=0.7)
    sp.weather(c, 0.6, seed + 2)
    if neon:
        sp.words_on(c, g, words, 'deco_tube', box, neon)
    c.glow = g if sp.lit_any(g) else None
    return c


def _plain(c, wall, seed):
    f = tw.Field(c.w, c.h, seed + 9, cells=8, octaves=4)
    for p in range(c.w * c.h):
        c.rgb[p], c.ht[p], c.gloss[p] = tw.mul(wall, 0.9 + 0.16 * f.v[p]), 0.5 + 0.05 * f.v[p], 16


def kil_signs():
    def blade(w, h):
        c, g = panel(w, h, 'enamel', (110, 32, 26), 'rect', seed=2700)
        sp.tube_path(c, g, sp.rounded(10, 10, w - 10, h - 10, h * 0.3), 6, (255, 190, 70), round_=0)
        sp.star(c, g, w * 0.065, h * 0.5, h * 0.19, (255, 200, 90))
        sp.star(c, g, w * 0.935, h * 0.5, h * 0.19, (255, 200, 90))
        sp.words_on(c, g, 'KILAUEA', 'tube', (w * 0.15, h * 0.12, w * 0.85, h * 0.88), (255, 130, 40))
        return c, g

    def casino(w, h):
        c, g = panel(w, h, 'enamel', (240, 226, 196), 'rect', seed=2710)
        sp.words_on(c, g, 'CASINO', 'deco', (w * 0.14, h * 0.14, w * 0.86, h * 0.86), (170, 36, 30), outline=(60, 20, 16), seed=2711, glow=True)
        for x in (w * 0.07, w * 0.93):
            sa.shape(c, sa._ellipse(x, h * 0.5, h * 0.16, h * 0.16), (170, 36, 30), line=4)
            sa.shape(c, sa._ellipse(x, h * 0.5, h * 0.07, h * 0.07), (240, 226, 196))
        sp.weather(c, 0.4, 2712)
        return c, g
    return sheet(1024, 512, [(0, 0, 1024, 256, blade), (0, 256, 1024, 256, casino)])


def _hist(key, words, wall, ink, neon=None):
    return lambda: wall_letters(words, wall, ink, seed=2800 + sum(map(ord, key)) % 97, neon=neon)


def install():
    """Puts these painters in place of the sets' own (the sets must be imported first)."""
    import historicset as hs
    modelsets.TEXTURES.update({
        'waikiki/signs': waikiki_signs,
        'waikiki/motels': motels,
        'kiosk_signs': kiosk,
        'hotel/signs': hotel_signs,
        'coast/signs': coast_signs,
        'resort/signs': resort_signs,
        'resort/kil_signs': kil_signs,
        'resort/tank': lambda: wall_letters('WAIKIKI       WAIKIKI', (190, 192, 184), (40, 78, 110), w=1024, h=256, seed=2900, style='brush'),
        'hist/rh_sign': _hist('rh', 'ROYAL HAWAIIAN', hs.PINK, (120, 40, 44), neon=(255, 96, 150)),
        'hist/mo_sign': _hist('mo', 'MOANA HOTEL', hs.MOANA_WHITE, (60, 80, 64), neon=(80, 235, 210)),
        'hist/nat_sign': _hist('nat', 'WAIKIKI WAR MEMORIAL', hs.STONE, (90, 84, 70)),
        'hist/bat_sign': _hist('bat', 'BATTERY RANDOLPH 1911', hs.BATTERY, (40, 40, 36)),
    })
