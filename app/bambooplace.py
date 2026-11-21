"""bambooset's pieces stood in Waikiki where the user said (20 Nov 2026: "Settlers and ridges"): the ridge places
(ridgeplaces.py) and the settlers' land (settlers.py).

- **Shacks to huts.** At the ridge settlements in `HUTS` every shack townbuild stood (ridgeplaces.SHACKS) goes, with its
  doors and what shut its doorways, and a thatch hut stands where its middle was, its doorway the way the shack's door
  faced (the bigger hut if it fits there, else the small one, else the shack is left).
- **Towers.** FOLab's guard tower at the ridge places and the settlers' posts (`TOWERS`, by map marker) becomes the bamboo
  tower: the same ref, place and turn (a 'swap' of base: the two share frame, flights and collision).
- **What's added**, by recipe (`ADD`) round each place's map marker, each on its lowest ground (so nothing hangs), clear
  of everything big, the plants under it cleared (ridgeplaces.Place): cookhouses, storehouses, drying racks, screens and
  fences at the settlements, a lookout and a hut at Watcher's Hut, market stalls at Loa Gate and Makapu'u Gate (the
  settlers' trade gate), canoe sheds on the beach beside the settlers' freighter (open end to the sea), storehouses and
  racks at the edges of their maize.

`ops(gd, pr, world, side)` gives (ops, report, cells) for one Undo; the cells are the ones to navmesh again."""
import math

import bambooset  # noqa: F401  (registers the pieces)
import modelsets
import ridgeplaces
import townbuild

# which ridge places' shacks become huts
HUTS = ('beacon', 'tanks', 'holdouts')
# map markers whose FOLab guard tower becomes the bamboo tower (within TOWER_NEAR)
TOWERS = ("Crow's Nest", "Settlers' Watchtower", 'Border Post', "Makapu'u Gate", 'The Holdouts')
TOWER_NEAR = 2600.0
# by map marker: [(piece, how many, nearest, farthest from the marker)]
ADD = {
    'The Tanks': [('bamboo_cookhouse', 1, 300, 1400), ('bamboo_storehouse', 2, 500, 1800), ('bamboo_drying_rack', 2, 400, 1600),
                  ('bamboo_screen', 1, 300, 1400), ('bamboo_fence_lashed', 2, 600, 1800)],
    'The Holdouts': [('bamboo_cookhouse', 1, 300, 1300), ('bamboo_storehouse', 2, 400, 1600), ('bamboo_drying_rack', 2, 300, 1500),
                     ('bamboo_screen', 1, 300, 1300), ('bamboo_fence_lashed', 2, 400, 1600)],
    'Pacific Heights Beacon': [('bamboo_drying_rack', 1, 200, 900), ('bamboo_screen', 1, 200, 900)],
    "Watcher's Hut": [('bamboo_lookout', 1, 0, 1400), ('bamboo_hut_small', 1, 200, 1400), ('bamboo_drying_rack', 1, 200, 1400)],
    'Loa Gate': [('bamboo_market_stall', 3, 300, 1500), ('bamboo_drying_rack', 1, 300, 1500), ('bamboo_screen', 2, 300, 1500)],
    "Crow's Nest": [('bamboo_drying_rack', 2, 300, 1300), ('bamboo_screen', 1, 300, 1300)],
    "Settlers' Watchtower": [('bamboo_screen', 1, 200, 800)],
    "Makapu'u Gate": [('bamboo_market_stall', 4, 400, 2200), ('bamboo_storehouse', 1, 500, 2200)],
}
SHIP = 'FOLabSettlerFreighter'
SHEDS = 2                       # canoe sheds on the beach beside her
SHED_REACH = (900.0, 9000.0)    # how far from her middle (the sea is most of what's round her)
BEACH = (6.0, 300.0)            # the sand they stand on: over the water, under the dunes
# the most the ground may differ under a piece's footprint (its origin goes on the lowest of it): a hut's floor is a step
# over its platform's foot, so hardly any; things on posts take more
LEVEL = {'bamboo_hut': 16.0, 'bamboo_hut_small': 16.0, 'bamboo_lookout': 36.0, 'bamboo_cookhouse': 40.0, 'bamboo_market_stall': 40.0,
         'bamboo_storehouse': 60.0, 'bamboo_drying_rack': 50.0, 'bamboo_screen': 40.0, 'bamboo_fence_lashed': 50.0, 'bamboo_canoe_shed': 60.0}
PAD = ('bamboo_hut', 'bamboo_hut_small', 'bamboo_lookout', 'bamboo_market_stall', 'bamboo_storehouse', 'bamboo_cookhouse', 'bamboo_drying_rack')
PAD_MOST = 160.0                # (ground no steeper than this across a footprint gets a pad levelled for the piece)
PAD_EASE = 350.0
FARTHER = 1.8                  # (a second look this much farther out for what didn't find room)
FIELD_EDGE = 0.25               # (the rows this far out among them, from the fields' middle, are the edge rows)
FIELD_THINGS = [('bamboo_storehouse', 4), ('bamboo_drying_rack', 3), ('bamboo_cookhouse', 1)]
FIELD_OUT = 350.0               # how far outside a field's edge row they stand
DOORS_NEAR = 60.0               # a door or doorway shut this close to a shack's box is the shack's


def _face(fx, fy):
    """The turn that points a piece's front (-y) along (fx, fy) (townbuild.turn's sense)."""
    return math.atan2(-fx, -fy) % math.tau


class Placer:
    def __init__(self, gd, pr, world, side, cat=None, seed=11):
        import server
        self.gd, self.pr = gd, pr
        cat = cat if cat is not None else townbuild.load(gd, server.kits_folder())
        self.cat = {b['edid']: b for b in cat}
        self.B = B = ridgeplaces.Builder(gd, pr, world, side, cat, seed)
        self.put_ops, self.keys, self.boxes = [], {}, {}
        self.rep = {'huts': [], 'shacks_left': [], 'towers': [], 'added': {}, 'not_placed': {}}
        self.named = {}
        self.stood = []                 # ((x, y, radius) of every piece this run stood)

    # ----- the mod's own pieces as Builder things -----

    def piece(self, name):
        if name not in self.keys:
            ops, info = modelsets.put(self.pr, name)
            self.put_ops += ops
            self.keys[name] = info['key'] or '$model_' + name
            self.boxes[name] = info['box']
            self.B.key_of[name] = self.keys[name]
            self.B.boxes[name] = info['box']
        return self.keys[name]

    def edid(self, base):
        if base not in self.named:
            import natcompound
            self.named[base] = natcompound._named(self.gd, self.pr, base)
        return self.named[base]

    def refs(self):
        if not hasattr(self, '_refs'):
            self._refs = [(ck, rk, r) for ck, c in self.pr.cells.items() for rk, r in (c.get('refs') or {}).items()
                          if not r.get('removed') and r.get('p')]
        return self._refs

    def markers(self):
        return {r['marker']['name']: r['p'][:3] for _c, _r, r in self.refs() if r.get('marker')}

    # ----- huts for shacks -----

    def huts(self, at):
        B = self.B
        shacks = [(ck, rk, r) for ck, rk, r in self.refs() if self.edid(r.get('base')) in ridgeplaces.SHACKS
                  and any(math.hypot(r['p'][0] - x, r['p'][1] - y) < 2600 for x, y, _z in at)]
        for ck, rk, r in shacks:
            e = self.edid(r['base'])
            b = self.cat.get(e)
            if not b:
                self.rep['shacks_left'].append((e, 'not in the catalogue'))
                continue
            ox, oy, oz, _tx, _ty, rz = r['p']
            bx = b['box']
            mx, my = townbuild.turn((bx[0] + bx[3]) / 2, (bx[1] + bx[4]) / 2, rz)
            mx, my = ox + mx, oy + my
            reach = math.hypot(bx[3] - bx[0], bx[4] - bx[1]) / 2 + DOORS_NEAR
            mine = {d['base'] for d in b.get('doors', ())} | {d['base'] for d in b.get('shut', ())}
            parts = [(c2, r2, q) for c2, r2, q in self.refs() if q.get('base') in mine and math.hypot(q['p'][0] - mx, q['p'][1] - my) < reach]
            if any(q.get('tel') or q.get('link') for _c, _r, q in parts):
                self.rep['shacks_left'].append((e, 'a door of it leads somewhere'))
                continue
            door = b['doors'][0] if b.get('doors') else None
            if door:
                dx, dy = townbuild.turn(door['x'], door['y'], rz)
                yaw = _face(ox + dx - mx, oy + dy - my)
            else:
                yaw = rz
            pl = ridgeplaces.Place(B, 'hut', mx, my, 0.0)
            B.gone.add((ck, rk))
            for c2, r2, _q in parts:
                B.gone.add((c2, r2))
            before = len(B.ops)
            for name in ('bamboo_hut', 'bamboo_hut_small'):
                self.piece(name)
                if self._put(pl, name, mx, my, yaw):
                    break
            if len(B.ops) == before:
                B.gone.discard((ck, rk))
                for c2, r2, _q in parts:
                    B.gone.discard((c2, r2))
                self.rep['shacks_left'].append((e, 'no room for a hut'))
                continue
            done = B.ops[before:]
            B.ops[before:] = [{'op': 'remove', 'cell': ck, 'ref': rk}] + [{'op': 'remove', 'cell': c2, 'ref': r2} for c2, r2, _q in parts] + done
            B.cells.add(ck)
            self.rep['huts'].append((e, round(mx), round(my), len(parts)))

    def _put(self, pl, name, x, y, yaw):
        box = self.boxes[name]
        # (its origin on the lowest ground under it: posts and platforms go into the ground, none hangs)
        r = max(box[3] - box[0], box[4] - box[1]) / 2
        if any(math.hypot(x - a, y - b) < r + c for a, b, c in self.stood):
            return False                                    # (another hut this run stood is in the way)
        if pl.put(name, x, y, yaw, sink=-box[2]):
            self.stood.append((x, y, r))
            return True
        return False

    def _try(self, pl, name, x, y, yaw, why):
        """Stand a piece if the ground under its own turned footprint is level enough (LEVEL), dry, nothing big in the
        way and nothing this run stood too near; else count why not."""
        B = self.B
        box = self.boxes[name]
        pts = [townbuild.turn(lx, ly, yaw) for lx in (box[0], 0.0, box[3]) for ly in (box[1], 0.0, box[4])]
        hs = [B.ground.at(x + u, y + v) for u, v in pts]
        if any(h is None or h < 4.0 for h in hs):
            why['water or off the map'] = why.get('water or off the map', 0) + 1
            return False
        level = max(hs) - min(hs) <= LEVEL.get(name, 40.0)
        if not level and not (name in PAD and max(hs) - min(hs) <= PAD_MOST):
            why['not level'] = why.get('not level', 0) + 1
            return False
        r = max(box[3] - box[0], box[4] - box[1]) / 2
        if any(math.hypot(x - a, y - b) < r + c + ridgeplaces.APART for a, b, c in pl.taken + self.stood):
            why['crowded'] = why.get('crowded', 0) + 1
            return False
        fp = [(x + u, y + v) for u, v in [townbuild.turn(lx, ly, yaw) for lx, ly in ((box[0], box[1]), (box[3], box[1]), (box[3], box[4]), (box[0], box[4]))]]
        blocked, clear = B.blocking(fp)
        if blocked:
            why['something big in the way'] = why.get('something big in the way', 0) + 1
            return False
        if not level:
            # (a pad levelled for it, eased back over PAD_EASE: only where nothing this run stood is in reach of the easing)
            reach = math.hypot(r, r) + 40.0 + PAD_EASE
            if any(math.hypot(x - a, y - b) < reach + c for a, b, c in self.stood):
                why['a pad would move what was stood'] = why.get('a pad would move what was stood', 0) + 1
                return False
            if B.terrace(x, y, yaw, r + 40.0, r + 40.0, ease=PAD_EASE) is None:
                why['water or off the map'] = why.get('water or off the map', 0) + 1
                return False
            self.rep['pads'] = self.rep.get('pads', 0) + 1
        B.take_out(clear)
        if pl.put(name, x, y, yaw, sink=-box[2], check=False):
            self.stood.append((x, y, r))
            return True
        return False

    # ----- towers -----

    def towers(self, marks):
        tower = modelsets.record_of(self.pr, 'guard_tower')
        if not tower:
            return []
        key = self.piece('bamboo_tower')
        out = []
        for n in TOWERS:
            if n not in marks:
                continue
            x, y, _z = marks[n]
            for ck, rk, r in self.refs():
                if r.get('base') == tower and math.hypot(r['p'][0] - x, r['p'][1] - y) < TOWER_NEAR:
                    out.append({'op': 'swap', 'cell': ck, 'ref': rk, 'base': key})
                    self.B.cells.add(ck)
                    self.rep['towers'].append((n, [round(v) for v in r['p'][:3]]))
        return out

    # ----- what's added -----

    def add_round(self, label, x, y, recipe, face=None):
        B = self.B
        pl = ridgeplaces.Place(B, label, x, y, 0.0)
        for name, n, r0, r1 in recipe:
            self.piece(name)
            made, why = 0, {}
            for k in range(n * 240):
                if made >= n:
                    break
                far = FARTHER if k >= n * 120 else 1.0
                a = B.rnd.uniform(0, math.tau)
                d = B.rnd.uniform(r0, r1 * far)
                px, py = x + d * math.cos(a), y + d * math.sin(a)
                yaw = _face(*(face if face else (x - px, y - py)))
                if self._try(pl, name, px, py, yaw, why):
                    made += 1
            self.rep['added'][(label, name)] = made
            if made < n:
                self.rep['not_placed'][(label, name)] = [n - made, why]

    def sheds(self):
        B = self.B
        ship = next(((ck, rk, r) for ck, rk, r in self.refs() if self.edid(r.get('base')) == SHIP), None)
        if not ship:
            return
        sx, sy = ship[2]['p'][:2]
        name = 'bamboo_canoe_shed'
        self.piece(name)
        pl = ridgeplaces.Place(B, 'beach', sx, sy, 0.0)
        pl.taken.append((sx, sy, 2200.0))                     # (the freighter's own length)
        g = B.ground
        made, why = 0, {}
        for k in range(3000):
            if made >= SHEDS:
                break
            a = B.rnd.uniform(0, math.tau)
            d = B.rnd.uniform(*SHED_REACH)
            px, py = sx + d * math.cos(a), sy + d * math.sin(a)
            h = g.at(px, py)
            if h is None or not BEACH[0] < h < BEACH[1]:
                continue
            # (downhill: the sea; its length down the slope so the canoe goes straight out)
            low = min(((g.at(px + 400 * math.cos(b), py + 400 * math.sin(b)) or 1e9), b) for b in [j * math.pi / 8 for j in range(16)])
            yaw = _face(math.cos(low[1]), math.sin(low[1]))
            if self._try(pl, name, px, py, yaw, why):
                made += 1
        self.rep['added'][('beach', name)] = made
        if made < SHEDS:
            self.rep['not_placed'][('beach', name)] = [SHEDS - made, why]

    def fields(self):
        """Storehouses and racks a little outside the maize: each by a row picked at random, out from the fields' middle."""
        B = self.B
        rows = [r['p'][:2] for _c, _r, r in self.refs() if self.edid(r.get('base')) in ('SCOLmaizeRow1b', 'SCOLmaizeRow2b')]
        if not rows:
            return
        cx, cy = sum(p[0] for p in rows) / len(rows), sum(p[1] for p in rows) / len(rows)
        rows.sort(key=lambda p: -math.hypot(p[0] - cx, p[1] - cy))
        edge = rows[:max(1, int(len(rows) * FIELD_EDGE))]
        pl = ridgeplaces.Place(B, 'fields', cx, cy, 0.0)
        for name, n in FIELD_THINGS:
            self.piece(name)
            made, why = 0, {}
            for k in range(n * 200):
                if made >= n:
                    break
                px, py = B.rnd.choice(edge)
                ux, uy = px - cx, py - cy
                ln = math.hypot(ux, uy) or 1.0
                out = FIELD_OUT * (1 + k / (n * 100.0))
                px, py = px + ux / ln * out, py + uy / ln * out
                if any(math.hypot(px - a, py - b) < 250 for a, b in rows):
                    why['in the maize'] = why.get('in the maize', 0) + 1
                    continue                                  # (not in the maize: out past its edge)
                if self._try(pl, name, px, py, _face(cx - px, cy - py), why):
                    made += 1
            self.rep['added'][('fields', name)] = made
            if made < n:
                self.rep['not_placed'][('fields', name)] = [n - made, why]


def ops(gd, pr, world, side, cat=None, seed=11):
    P = Placer(gd, pr, world, side, cat, seed)
    marks = P.markers()
    names = {v[0]: k for k, v in ridgeplaces.SITES.items()}
    P.huts([marks[n] for n, k in names.items() if k in HUTS and n in marks])
    swaps = P.towers(marks)
    for n, recipe in ADD.items():
        if n in marks:
            P.add_round(n, marks[n][0], marks[n][1], recipe)
        else:
            P.rep['not_placed'][(n, 'no marker')] = 1
    P.sheds()
    P.fields()
    B = P.B
    lands = []
    for k, f in sorted(B.forms.items()):                  # (the pads' land, as ridgeplaces.ops writes its terraces')
        ck = gd.key(B.w.grid[k])
        lands.append({'op': 'land', 'cell': ck, 'land': f})
        B.cells.add(ck)
    moves = [{'op': 'move', 'cell': ck, 'ref': rk, 'p': p} for (ck, rk), p in sorted(B.moved.items()) if (ck, rk) not in B.gone]
    P.rep['land_cells'], P.rep['moved'] = len(lands), len(moves)
    rep = dict(P.rep, added={'%s: %s' % k: v for k, v in P.rep['added'].items()}, not_placed={'%s: %s' % k: v for k, v in P.rep['not_placed'].items()},
               missing=sorted(P.B.rep['missing']))
    return P.put_ops + lands + moves + swaps + B.ops, rep, sorted(B.cells)
