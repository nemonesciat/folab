"""Lookouts with a reason to climb (the user, 21 Nov 2026: "yes, all those please" to towers, the Kilauea's crown and
Diamond Head's rim each with a stash, a sniper nest or a map marker at the top). Only what is already there and walked:
FOLab's guard towers and bamboo towers (walked to the deck by walkcheck, `guardtower.WALK`), the court's city lookouts
(citypieces' ramp towers with a hut on top), the lifeguard towers, the observation deck under the Kilauea's crown (its
small world, up the lift) and the ground of Diamond Head's rim beside its tower.

A find goes on the top's floor (lootplace's `Seat` with the top's height as its level: a surface within `ON_TOP` of it
and nothing else), its back to the rail and its front to the middle; a band up from where it stands (lootplace's bands),
so a climb pays. A sniper nest (`NEST`) is a bedroll and a gun find, on the towers that look over the most (`NESTS`) and on
the rim. A tower with no map marker within `MARKER_NEAR` gets one at its foot, named for the nearest place (`marker_name`).

    ops(gd, pr, world, seed)    (ops, report), nothing applied"""
import math
import random
import re

import guardtower
import lootplace
import roadgen
import settleup
import townbuild

TOWERS = {'FOLabGuardTower': guardtower.DECK, 'FOLabBambooGuardTower': guardtower.DECK}
CITY = re.compile(r'^FOLabCityLookout(\d+)x0$')
CITY_EVERY = 3                  # (one court lookout in this many gets a stash: they stand all over Waikiki)
LIFEGUARD = 'FOLabWaikikiLifeguardTower'
TOWER_KINDS = ['military', 'ammo', 'medicine', 'food']
CITY_KINDS = ['ammo', 'food', 'bag', 'medicine']
NESTS = 3                       # (towers that also get a sniper nest: those standing highest over the sea)
NEST = ('NVBedrollL', 'guns')
ON_TOP = 30.0
DECK_HALF = guardtower.HALF - 40.0
MARKER_NEAR = 2500.0
KILAUEA_WORLD = 'FOLabKilaueaWorld'
KILAUEA_DECK = 5512.0           # (hotelinside.KIL_FLOOR + KIL_DECK: the deck over the piece's foot)
RIM = 'Diamond Head'
RIM_REACH = 2600.0
RIM_FROM = 700.0                # (the rim's nest this far at least from the tower and the radio mast)
RIM_SANDBAG = 'SandbagStraight'


def _key(gd, edid, tags):
    best = None
    for f, (_i, r) in gd.forms.items():
        if r.tag in tags and gd.edid(f) == edid and (best is None or f >> 24 < best >> 24):
            best = f
    return gd.key(best) if best is not None else None


class Tops:
    def __init__(self, gd, pr, world, seed):
        self.gd, self.pr, self.world = gd, pr, world
        self.P = lootplace.Plan(gd, pr, world, seed)
        self.rng = self.P.rng
        self.solids = lootplace.Solids(gd, pr)
        self.S = lootplace.Seat(gd, pr, world, self.solids)
        self.start = tuple((pr.newgame or {}).get('p', [0, 0])[:2])
        self.reach = lootplace.farthest(gd, world, self.start)
        self.O = lootplace.Outside(self.P, None, self.S, self.start, reach=self.reach)
        self.report = {'tops': [], 'markers': []}
        self.extra = []                     # (ops of things that aren't finds: bedrolls, sandbags, markers)

    def band(self, x, y, up=1):
        return self.O.band(x, y, up)

    def on_top(self, S, ck, edid, cx, cy, level, half, turn=0.0, kind_band=None, spot='top', base_key=None, centre=None):
        """One thing on a top: tried on a grid over (cx, cy) ± half in the top's frame, facing its middle."""
        key = base_key or self.P.key_of(edid)
        fb = townbuild.obnd(self.gd, key)
        if not fb:
            return None
        front = self.P.front(edid) if base_key is None else (0.0, -1.0)
        r = max(fb[3] - fb[0], fb[4] - fb[1]) / 2
        mx, my = centre or (cx, cy)
        tries = [(a, b) for a in range(-int(half), int(half) + 1, 40) for b in range(-int(half), int(half) + 1, 40)]
        tries.sort(key=lambda t: -max(abs(t[0]), abs(t[1])) + self.rng.uniform(0, 30))     # (the rail's side first)
        S.load(cx, cy)
        for a, b in tries:
            ox, oy = lootplace._turn(a, b, turn)
            x, y = cx + ox, cy + oy
            dx, dy = mx - x, my - y
            if math.hypot(dx, dy) < 1:
                dx, dy = 0.0, -1.0
            rz = lootplace._face(dx, dy, front)
            if not S.free(x, y, r):
                continue
            p = S.at(x, y, rz, fb, level, outside=False)
            if p is None or abs(p[2] + fb[2] - level) > ON_TOP:
                continue
            S.take(x, y, r)
            return p, key
        return None


def marker_name(marks, x, y):
    name, d = min(((n, math.hypot(p[0] - x, p[1] - y)) for n, p in marks.items()), key=lambda t: t[1])
    for cut in (' Squatters\' Camp', ' Refugee Camp', ' Raider Camp', ' Camp'):
        if name.endswith(cut):
            name = name[:-len(cut)]
    if name.startswith('The '):
        name = name[4:]
    return name + ' Lookout'


def ops(gd, pr, world, seed=17):
    T = Tops(gd, pr, world, seed)
    P, S = T.P, T.S
    G = roadgen.Ground(gd, pr, world)
    marks = lootplace._markers(gd, pr, world)
    grid = gd.grid(world)
    towers, city, guards = [], [], []
    for xy, c in grid.items():
        ck = gd.key(c)
        for rk, r in (pr.cells.get(ck) or {}).get('refs', {}).items():
            if not r.get('p') or not r.get('base') or r.get('removed'):
                continue
            e = settleup._edid(gd, pr, r['base']) or ''
            if e in TOWERS:
                towers.append((ck, rk, r, e))
            elif CITY.match(e):
                city.append((ck, rk, r, e))
            elif e == LIFEGUARD:
                guards.append((ck, rk, r, e))

    # towers: a stash on the deck; the highest few over the sea a sniper nest too
    towers.sort(key=lambda t: -t[2]['p'][2])
    nests = {t[1] for t in towers[:NESTS]}
    for i, (ck, rk, r, e) in enumerate(towers):
        x, y, z, _rx, _ry, rz = r['p']
        s = r.get('s', 1.0) or 1.0
        level = z + TOWERS[e] * s
        band = T.band(x, y)
        kind = TOWER_KINDS[i % len(TOWER_KINDS)]
        edid, lock = P.choose(kind, band)
        got = T.on_top(S, ck, edid, x, y, level, DECK_HALF * s, rz, spot='tower')
        row = {'at': [round(x), round(y), round(level)], 'what': e, 'band': band, 'finds': 0}
        if got:
            P.add(ck, edid, got[0], lock=lock, spot='tower', band=band)
            row['finds'] += 1
        if rk in nests:
            bed = T.on_top(S, ck, NEST[0], x, y, level, DECK_HALF * s, rz, spot='nest', base_key=_key(gd, NEST[0], ('STAT', 'FURN')))
            if bed:
                T.extra.append({'op': 'add', 'cell': ck, 'base': bed[1], 'p': bed[0], 's': 1.0})
            gedid, glock = P.choose(NEST[1], band)
            gun = T.on_top(S, ck, gedid, x, y, level, DECK_HALF * s, rz, spot='nest')
            if gun:
                P.add(ck, gedid, gun[0], lock=glock, spot='nest', band=band)
                row['finds'] += 1
            row['nest'] = bool(bed)
        T.report['tops'].append(row)
        if not any(math.hypot(p[0] - x, p[1] - y) < MARKER_NEAR for p in marks.values()):
            name = marker_name(marks, x, y)
            spot = None
            for ang in range(0, 360, 30):           # (at its foot, on dry land)
                mx, my = x + 500 * math.cos(math.radians(ang)), y + 500 * math.sin(math.radians(ang))
                g, wl = G.at(mx, my), G.water(mx, my)
                if g is not None and g > 8 and (wl is None or g > wl + 8):
                    spot = (mx, my, g)
                    break
            if spot is None:
                continue
            import worldrec
            T.extra.append(worldrec.marker_op(gd, world, [round(spot[0], 1), round(spot[1], 1), round(spot[2] + 40, 1)], name, 8, 2))
            T.report['markers'].append(name)
            marks[name] = (x, y, z)

    # the court's lookouts: one in CITY_EVERY a find in the hut
    T.rng.shuffle(city)
    for i, (ck, rk, r, e) in enumerate(city[::CITY_EVERY]):
        x, y, z, _rx, _ry, rz = r['p']
        s = r.get('s', 1.0) or 1.0
        level = z + int(CITY.match(e).group(1)) * s
        band = T.band(x, y)
        edid, lock = P.choose(CITY_KINDS[i % len(CITY_KINDS)], band)
        got = T.on_top(S, ck, edid, x, y, level, 900 * s, rz, spot='city')
        if got:
            P.add(ck, edid, got[0], lock=lock, spot='city', band=band)
        T.report['tops'].append({'at': [round(x), round(y), round(level)], 'what': e, 'band': band, 'finds': int(bool(got))})

    # lifeguard towers: a first aid kit on the chair's platform
    for ck, rk, r, e in guards:
        x, y, z, _rx, _ry, rz = r['p']
        S.load(x, y)
        g = G.at(x, y) or z
        tops = sorted(zz for zz, _r in T.solids.tops(x, y) if g + 90 < zz < g + 600)
        if not tops:
            T.report['tops'].append({'at': [round(x), round(y)], 'what': e, 'finds': 0, 'why': 'no platform'})
            continue
        level = tops[0]
        edid = 'LootFirstAidKitNV' if 'LootFirstAidKitNV' in P.forms else P.choose('medicine', 0)[0]
        if edid not in P.forms:
            P.forms[edid] = gd.from_key(_key(gd, edid, ('CONT',)))
        got = T.on_top(S, ck, edid, x, y, level, 160, rz, spot='lifeguard')
        if got:
            P.add(ck, edid, got[0], spot='lifeguard', band=0)
        T.report['tops'].append({'at': [round(x), round(y), round(level)], 'what': e, 'finds': int(bool(got))})

    # Diamond Head's rim: a sniper nest on its highest open ground, away from the tower and the mast
    if RIM in marks:
        mx, my, _mz = marks[RIM]
        keep_off = [(t[2]['p'][0], t[2]['p'][1]) for t in towers if math.hypot(t[2]['p'][0] - mx, t[2]['p'][1] - my) < RIM_REACH * 1.5]
        keep_off.append((mx, my))
        best = []
        for a in range(-int(RIM_REACH), int(RIM_REACH) + 1, 128):
            for b in range(-int(RIM_REACH), int(RIM_REACH) + 1, 128):
                x, y = mx + a, my + b
                g = G.at(x, y)
                if g is not None and math.hypot(a, b) <= RIM_REACH and all(math.hypot(x - u, y - v) > RIM_FROM for u, v in keep_off):
                    best.append((g, x, y))
        best.sort(reverse=True)
        ck = None
        for g, x, y in best[:60]:
            c = grid.get((int(x // 4096), int(y // 4096)))
            if c is None:
                continue
            ck = gd.key(c)
            sea = (0.0, -1.0)                      # (Diamond Head looks out over the sea to its south)
            sb = _key(gd, RIM_SANDBAG, ('STAT',))
            fb = townbuild.obnd(gd, sb)
            put, bags = [], []
            S.load(x, y)
            for off in (-1, 0, 1):
                # (sandbags in a shallow arc on the seaward side, each turned along it)
                ang = off * 0.55
                bx, by = x + math.sin(ang) * 170, y - math.cos(ang) * 170
                rz = -ang
                q = S.at(bx, by, rz, fb, (G.at(bx, by) or g))
                if q is None:
                    break
                bags.append({'op': 'add', 'cell': ck, 'base': sb, 'p': q, 's': 1.0})
            if len(bags) < 3:
                continue
            band = 2
            bed = _key(gd, NEST[0], ('STAT', 'FURN'))
            bb = townbuild.obnd(gd, bed)
            qb = S.at(x, y + 40, 0.0, bb, g)
            gedid, glock = P.choose(NEST[1], band)
            gb = P.box(gedid)
            gx, gy = x + 130, y + 120
            qg = S.at(gx, gy, lootplace._face(x - gx, y - gy - 170, P.front(gedid)), gb, G.at(gx, gy) or g)
            aedid, alock = P.choose('ammo', band)
            ab = P.box(aedid)
            ax, ay = x - 130, y + 120
            qa = S.at(ax, ay, lootplace._face(x - ax, y - ay - 170, P.front(aedid)), ab, G.at(ax, ay) or g)
            if not (qb and qg and qa):
                continue
            T.extra += bags + [{'op': 'add', 'cell': ck, 'base': bed, 'p': qb, 's': 1.0}]
            P.add(ck, gedid, qg, lock=glock, spot='rim', band=band)
            P.add(ck, aedid, qa, lock=alock, spot='rim', band=band)
            T.report['tops'].append({'at': [round(x), round(y), round(g)], 'what': 'Diamond Head rim nest', 'band': band, 'finds': 2, 'nest': True})
            break

    # the Kilauea's crown: its observation deck, in its own small world
    kw = next((w for w in gd.worlds() if gd.edid(w) == KILAUEA_WORLD), None)
    if kw is not None:
        KS = lootplace.Seat(gd, pr, kw, lootplace.Solids(gd, pr), ground=False)
        piece = None
        for xy, c in gd.grid(kw).items():
            for rk, r in (pr.cells.get(gd.key(c)) or {}).get('refs', {}).items():
                e = settleup._edid(gd, pr, r.get('base')) if r.get('base') else ''
                if r.get('p') and not r.get('removed') and re.search(r'kilauea', e or '', re.I) and re.search(r'open', e or '', re.I):
                    piece = (gd.key(c), r)
        if piece:
            ck, r = piece
            x, y, z, _rx, _ry, rz = r['p']
            s = r.get('s', 1.0) or 1.0
            level = z + KILAUEA_DECK * s
            row = {'at': [round(x), round(y), round(level)], 'what': 'Kilauea observation deck', 'band': 2, 'finds': 0}
            for kind, lock_up in (('safe', 0), ('military', 0)):
                if kind == 'safe':
                    edid, lock = 'GenericSafe01', 75
                else:
                    edid, lock = P.choose(kind, 2)
                # (on the deck's ring between the glass and the lift, tried round it)
                for ang in [T.rng.uniform(0, math.tau) for _k in range(24)]:
                    rr = T.rng.uniform(1300, 1900) * s
                    got = T.on_top(KS, ck, edid, x + math.cos(ang) * rr, y + math.sin(ang) * rr, level, 120, 0.0, spot='kilauea', centre=(x, y))
                    if got:
                        P.add(ck, edid, got[0], lock=lock, spot='kilauea', band=2)
                        row['finds'] += 1
                        break
            T.report['tops'].append(row)
        else:
            T.report['kilauea'] = 'its open piece not found in %s' % KILAUEA_WORLD
    T.report['finds'] = P.report['finds']
    T.report['locked'] = P.report['locked']
    return T.extra + P.ops, T.report
