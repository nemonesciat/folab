"""How much the game has to draw round a spot: the draw count (the View's badge, Health's busiest spots, /api/draws).

Waikiki ran at 12 fps round its start (20 Nov 2026) and nobody could see why until a script counted: every thing in the
5 x 5 cells the game keeps loaded round the player (the mod's things over the game's), each shape of its model one draw.
The start drew 12,693; the game's own busiest places draw about 2,000 (Freeside's gate 2,196, Novac 1,403). After FOLab's
plants were budgeted and its low cover made the game's grass, 4,000 to 6,700 ran well. The game's own grass (GRAS) and the
far view are drawn another way and aren't counted; neither are actors.

`Counter(gd, pr)` keeps what it learnt of each model (shapes) and each base (its kind). `around(world, x, y)` outside, or
`inside(cell_key)` for a place, give {things, draws, kinds: {kind: [things, draws]}, top: [(editor ID, things, draws)],
band, cells}. `busiest(world)` looks round every cell the mod changed and gives the heaviest spots.
"""
import os
import re

import library
import nif
import recordio

CELL = 4096.0
REACH = 2               # cells loaded each way round the player (uGridsToLoad 5)
GAME_BUSIEST = 2200     # the game's own busiest outdoor spot (Freeside's gate, 2,196)
HEAVY = 4000            # over this: heavier than anywhere in the game
TOO_MUCH = 7000         # over this: expect a low frame rate (Waikiki's start at 12,693 ran at 12 fps)

KINDS = [(r'^FOLab(Jungle|Beach|Mountain|Plant)|^FOLab.*(Palm|Fern|Taro|Heliconia|Hibiscus|Banana|Bamboo|Grass|Shrub|Ti)\b', "FOLab's plants"),
         (r'^FOLab', "FOLab's own models"),
         (r'rubble|litter|debris|trash|junk|rock|stone|plank|board', 'rubble, litter, rocks'),
         (r'tree|palm|bush|grass|fern|plant|shrub|vine|leaf|leaves|cactus|agave|yucca|sage|birch|cypress|banana|fung', "the game's plants"),
         (r'road|street|sidewalk|curb|kerb|slab|overpass|highway', 'roads and pavement'),
         (r'car|bus|truck|hulk|tire|wheel', 'wrecks'),
         (r'bldg|house|shack|wall|door|office|apartment|motel|store|fence|tower|building|hotel|casino|ruin', 'buildings, walls, doors')]


def band(draws):
    """('ok' | 'heavy' | 'too much', words)."""
    if draws <= HEAVY:
        return 'ok', 'about what the game itself draws' if draws <= GAME_BUSIEST * 1.2 else 'busier than the game, still fine'
    if draws <= TOO_MUCH:
        return 'heavy', 'heavier than anywhere in the game: frame rate may drop'
    return 'too much', 'far more than the game ever draws: expect a low frame rate'


class Counter:
    def __init__(self, gd, pr=None):
        self.gd, self.pr = gd, pr
        self.shapes, self.names, self.kinds = {}, {}, {}
        self.assets = library.assets_dir(pr) if pr else None

    def edid(self, b):
        if b not in self.names:
            try:
                if b.startswith('+'):
                    self.names[b] = recordio.field((self.pr.records if self.pr else {}).get(b) or {}, 'EDID') or b
                else:
                    self.names[b] = self.gd.edid(self.gd.from_key(b)) or b
            except Exception:
                self.names[b] = b
        return self.names[b]

    def kind(self, b):
        if b not in self.kinds:
            e = self.edid(b)
            self.kinds[b] = next((k for pat, k in KINDS if re.search(pat, e, re.I)), 'other')
        return self.kinds[b]

    def _model(self, b):
        if b.startswith('+'):
            return recordio.field((self.pr.records if self.pr else {}).get(b) or {}, 'MODL')
        d = self.gd.describe(self.gd.from_key(b))
        return d[3] if d else None

    def draws_of(self, b):
        """The shapes of a base's model: each one a draw (0 for one with no model, a marker, or one that can't be read)."""
        if b not in self.shapes:
            n = 0
            try:
                m = self._model(b)
                if m:
                    rel = 'meshes\\' + m.replace('/', '\\').lstrip('\\')
                    if rel.lower().startswith('meshes\\meshes\\'):
                        rel = rel[7:]
                    own = os.path.join(self.assets, rel) if self.assets else None
                    if own and os.path.isfile(own):
                        with open(own, 'rb') as f:
                            data = f.read()
                    else:
                        data = self.gd.read_file(rel)
                    n = len(nif.mesh_from_nif(data)) if data else 0
            except Exception:
                n = 0
            self.shapes[b] = n
        return self.shapes[b]

    def _things(self, c):
        """(base key) of every thing in a cell as the mod has it: the game's not removed or changed, then the mod's."""
        gd = self.gd
        ck = gd.key(c) if not isinstance(c, str) else c
        cell = gd.from_key(ck) if isinstance(c, str) else c
        mine = (self.pr.cells.get(ck, {}).get('refs', {}) if self.pr else {})
        for r in (gd.refs(cell) or ()):
            k = gd.key(r['ref'])
            if r.get('base') is None:
                continue
            ch = mine.get(k)
            if ch is not None:              # (a game thing the mod changed: gone, sunk out of the way, or swapped)
                if ch.get('removed') or (ch.get('p') and ch['p'][2] < -20000):
                    continue
                yield ch.get('base') or gd.key(r['base'])
                continue
            yield gd.key(r['base'])
        for k, r in mine.items():
            if k.startswith('+') and not r.get('removed') and r.get('base') and r.get('p') and r['p'][2] > -20000:
                yield r['base']

    def _sum(self, cells):
        things, draws, kinds, per = 0, 0, {}, {}
        for c in cells:
            for b in self._things(c):
                d = self.draws_of(b)
                things += 1
                draws += d
                k = kinds.setdefault(self.kind(b), [0, 0])
                k[0] += 1
                k[1] += d
                p = per.setdefault(b, [0, 0])
                p[0] += 1
                p[1] += d
        top = sorted(per.items(), key=lambda kv: -kv[1][1])[:12]
        b, words = band(draws)
        return {'things': things, 'draws': draws, 'kinds': kinds, 'band': b, 'words': words, 'cells': len(cells),
                'top': [(self.edid(k), n, d) for k, (n, d) in top], 'game_busiest': GAME_BUSIEST}

    def around(self, world, x, y):
        grid = self.gd.grid(world)
        cx, cy = int(x // CELL), int(y // CELL)
        cells = [grid[(cx + dx, cy + dy)] for dx in range(-REACH, REACH + 1) for dy in range(-REACH, REACH + 1)
                 if (cx + dx, cy + dy) in grid]
        out = self._sum(cells)
        out['at'] = (cx, cy)
        return out

    def inside(self, cell_key):
        return self._sum([cell_key])

    def busiest(self, world, most=8, progress=None):
        """The heaviest spots round the cells the mod changed in `world`: [{at: (x, y), draws, things, band}]."""
        gd = self.gd
        grid = gd.grid(world)
        xy_of = {gd.key(c): xy for xy, c in grid.items()}
        mine = [xy_of[k] for k in (self.pr.cells if self.pr else {}) if k in xy_of]
        per = {}

        def cell_draws(xy):
            if xy not in per:
                c = grid.get(xy)
                per[xy] = sum(self.draws_of(b) for b in self._things(c)) if c is not None else 0
            return per[xy]
        spots = {}
        for n, (x, y) in enumerate(mine):
            if progress and n % 50 == 0:
                progress('Counting draws round your cells', n, len(mine))
            spots[(x, y)] = sum(cell_draws((x + dx, y + dy)) for dx in range(-REACH, REACH + 1) for dy in range(-REACH, REACH + 1))
        best = sorted(spots.items(), key=lambda kv: -kv[1])
        out, taken = [], []
        for (x, y), d in best:                       # (spots a few cells apart, not one hot area five times)
            if any(abs(x - a) <= REACH and abs(y - b) <= REACH for a, b in taken):
                continue
            taken.append((x, y))
            out.append({'at': (x, y), 'draws': d, 'band': band(d)[0]})
            if len(out) >= most:
                break
        return out


_kept = {}


def counter(gd, pr):
    """One Counter per game and mod, kept: models' shapes don't change while FOLab runs (a mod's own model may: its file
    is read again when FOLab is started again)."""
    k = (id(gd), id(pr))
    if k not in _kept:
        _kept.clear()
        _kept[k] = Counter(gd, pr)
    return _kept[k]
