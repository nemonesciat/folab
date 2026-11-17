"""The coast's hotels and one-off things (coastset's pieces) stood over a world made from a map, as one Undo.

Each has a site rule: where the map has the real thing (by kind or by name) it stands there or as near as the ground
and what is already standing allow; where it hasn't, the shape of the coast says where.

  hotels      Kahala Reef by an OSM hotel named Kahala, else the east end of the shore; Moana Kai by one named Ilikai,
              Hale Malia by one named Halekulani, else the best ground behind the beach (modelsets._best_site's rules:
              700 to 3,200 from the sea, level, facing it). APART_NEAR from every hotel, the four included.
  lighthouse  man_made=lighthouse, else the headland: the land point with the most sea round it. Faces the sea.
  groin       man_made=groyne named Kapahulu, else the longest groyne, else straight out from a sandy beach: a walk
              of concrete (GROIN_STEP lengths) from where the beach meets the water, out until it is OUT_MIN over
              water, and the pavilion at its end. Built at the water, nothing levelled.
  aquarium    tourism=aquarium, else a spot by the shore. Its front to the land (the street), its back to the sea.
  wreck       natural=reef (the surf breaks), else any water of the right depth: aground where the sea is WRECK_DEPTH
              deep under every part of it, its deck just over the water, listing a little.
  mast        natural=peak nearest the sea, else the highest ground near it: a headland.

Keep-clear is the hotels' (`modelsets.Obstacles`, own=True): no linked doors, landmarks, hotels, the carrier or
anything else big of the mod's own; what the mod has standing in a footprint on land is cleared, buildings the
footprint would cut through taken out whole. Things in the water refuse anything big at all. The ground under what
stands on land is levelled (`landmarks.Batch`), and what stood on ground that moved is moved with it.
maps\\hotels.json gains the hotels (so the Waikiki set dresses their grounds); maps\\coast.json lists the rest, which
`modelsets.footprints` then keeps later steps off. NOT twice: it adds."""
import math
import xml.etree.ElementTree as ET

import coastset
import modelsets
import waikikiset

HOTEL_NAMES = {'kahala_reef': ('kahala',), 'moana_kai': ('ilikai',), 'hale_malia': ('halekulani',)}
HOTEL_NEAR = 2400.0         # how far from the map's hotel of that name one may stand
HOTEL_FAR = 6000.0          # (and if nothing near has room, this far)
STEP = 256.0                # spots tried round a target this far apart
LIGHT_STEP = 450.0          # ground that may rise across a lighthouse's or a mast's yard (a terrace cut into a slope)
GROIN_OUT_MIN = 1500.0      # a groin reaches at least this far over the water
GROIN_LONGEST = 5000.0
GROIN_TOP = 45.0            # its walk over the water
WRECK_DEPTH = (120.0, 900.0)
WRECK_OVER = 40.0           # its deck over the water, in the middle
WRECK_LIST = 0.1            # (radians: a little over on one side)
WRECK_FROM = 2500.0         # how far from the map's reef it may lie
APART_IN_WATER = 2500.0     # between the groin, its pavilion and the wreck


def osm_marks(path):
    """What the coast's rules look for in an OSM file, as lat/lon: {'lighthouse', 'aquarium', 'peak', 'reef', 'hotel':
    [(lat, lon, name)], 'groyne': [([(lat, lon)], name)]}."""
    nodes, out = {}, {k: [] for k in ('lighthouse', 'aquarium', 'peak', 'reef', 'hotel', 'groyne')}
    for _ev, el in ET.iterparse(path):
        if el.tag == 'node':
            nodes[el.get('id')] = (float(el.get('lat')), float(el.get('lon')))
        if el.tag not in ('node', 'way'):
            continue
        tags = {t.get('k'): t.get('v') for t in el.findall('tag')}
        if tags:
            name = tags.get('name', '')
            pts = [nodes[n.get('ref')] for n in el.findall('nd') if n.get('ref') in nodes] if el.tag == 'way' else [nodes[el.get('id')]]
            if pts:
                mid = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), name)
                kind = (('lighthouse' if tags.get('man_made') == 'lighthouse' else None) or ('aquarium' if tags.get('tourism') == 'aquarium' else None)
                        or ('peak' if tags.get('natural') == 'peak' else None) or ('reef' if tags.get('natural') == 'reef' else None)
                        or ('hotel' if tags.get('tourism') == 'hotel' and name else None))
                if kind:
                    out[kind].append(mid)
                if tags.get('man_made') == 'groyne' and el.tag == 'way' and len(pts) > 1:
                    out['groyne'].append((pts, name))
        if el.tag == 'way':
            el.clear()
    return out


class Coast:
    def __init__(self, gd, pr, world, cover, roads, xy, marks, seed=1, progress=None):
        import landmarks
        import osmcover
        self.gd, self.pr, self.world, self.cover, self.lm = gd, pr, world, cover, landmarks
        self.grid = gd.grid(world)
        self.batch = landmarks.Batch(gd, pr, world, roads, seed)
        self.obs = modelsets.Obstacles(gd, pr, world, own=True)
        self.progress = progress or (lambda *a: None)
        self.marks = {k: [(xy((la, lo)), n) for la, lo, n in v] for k, v in marks.items() if k != 'groyne'}
        self.groynes = [([xy(p) for p in pts], n) for pts, n in marks.get('groyne', [])]
        A, D, gx0, gy0 = cover.A, cover.D, cover.gx0, cover.gy0
        self.sea_code, self.road_code, self.sand_code = osmcover.CODE['seabed'], osmcover.CODE['asphalt'], osmcover.CODE.get('sand')
        self.sea = [((gx0 + x) * 128.0, (gy0 + y) * 128.0) for y in range(0, D, 6) for x in range(0, A, 6) if cover.kind[y * A + x] == self.sea_code]
        self.coarse = {}                        # (768-unit squares) -> sea points in it
        for sx, sy in self.sea:
            self.coarse.setdefault((int(sx // 768), int(sy // 768)), []).append((sx, sy))
        self.land = [((gx0 + x) * 128.0, (gy0 + y) * 128.0) for y in range(8, D - 8, 4) for x in range(8, A - 8, 4)
                     if cover.kind[y * A + x] not in (self.sea_code, self.road_code)]
        self.first, self.adds, self.lights, self.refused, self.stood = [], [], [], [], []
        self.keys, self.boxes, self.made = {}, {}, {}
        self.hotels = []                         # (piece, x, y, turn) of every hotel, the four included
        import api_maps
        for h in api_maps._kept(pr, 'hotels.json').get(gd.edid(world)) or []:
            self.hotels.append((h.get('piece'), float(h['x']), float(h['y']), float(h.get('turn', 0.0))))
        self.lit = []

    # ----- the sea -----

    def to_sea(self, x, y):
        """How far the sea is from a spot, and which way (looking in the squares round it first)."""
        best = None
        cx, cy = int(x // 768), int(y // 768)
        for reach in (3, 8, 24, 80):
            for i in range(cx - reach, cx + reach + 1):
                for j in range(cy - reach, cy + reach + 1):
                    for sx, sy in self.coarse.get((i, j), ()):
                        d = (sx - x) ** 2 + (sy - y) ** 2
                        if best is None or d < best[0]:
                            best = (d, sx, sy)
            if best is not None and math.sqrt(best[0]) <= reach * 768:
                break
        if best is None:
            return None, (0.0, -1.0)
        d = math.sqrt(best[0]) or 1.0
        return d, ((best[1] - x) / d, (best[2] - y) / d)

    def sea_round(self, x, y, reach=3000.0):
        """How much sea there is within reach of a spot (in sea points): a headland has most."""
        n, r = 0, int(reach // 768) + 1
        cx, cy = int(x // 768), int(y // 768)
        for i in range(cx - r, cx + r + 1):
            for j in range(cy - r, cy + r + 1):
                n += sum(1 for sx, sy in self.coarse.get((i, j), ()) if (sx - x) ** 2 + (sy - y) ** 2 <= reach * reach)
        return n

    def water(self, x, y):
        return self.batch.ground.water(x, y)

    # ----- a piece -----

    def piece(self, name):
        if name not in self.keys:
            ops, info = modelsets.put(self.pr, name)
            self.made[name] = ops                # (put in only if it stands: see records)
            self.keys[name] = info['key'] or '$model_' + name
            b = info['box']
            self.boxes[name] = (b[0], b[1], b[3], b[4])
        return self.keys[name], self.boxes[name]

    def site(self, name, spots, turns=8, face='sea', step_over=modelsets.STEP_OVER, near=None, shore=None, apart=None, prefer=None):
        """The best of these spots for a piece standing on land: (cost, x, y, turn, ground height) or None."""
        _key, box = self.piece(name)
        lm, batch = self.lm, self.batch
        best = None
        for x, y in spots:
            if apart and any(math.hypot(x - hx, y - hy) < apart for _p, hx, hy, _r in self.hotels):
                continue
            d, (ux, uy) = self.to_sea(x, y)
            if shore and (d is None or not shore[0] <= d <= shore[1]):
                continue
            for k in range(turns):
                rz = k * math.tau / turns
                why = self.obs.in_the_way(x, y, rz, box)
                if why:
                    if (name, why) not in self.refused:
                        self.refused.append((name, why))
                    continue
                bad = batch._score(x, y, rz, box)
                if bad is None:
                    continue
                m = lm.MARGIN
                hs = [batch.height(x + tx, y + ty) for tx, ty in (lm._turn(box[0] - m + (box[2] - box[0] + 2 * m) * u / 4.0, box[1] - m + (box[3] - box[1] + 2 * m) * v / 4.0, rz)
                                                                 for u in range(5) for v in range(5))]
                if None in hs or min(hs) < 8 or max(hs) - min(hs) > step_over:
                    continue
                fx, fy = lm._turn(0.0, -1.0, rz)
                cost = bad + (max(hs) - min(hs)) / 60.0
                if face == 'sea':
                    cost += 25.0 * (1 - (fx * ux + fy * uy))
                elif face == 'land':
                    cost += 25.0 * (1 + (fx * ux + fy * uy))
                if near:
                    cost += math.hypot(x - near[0], y - near[1]) / 200.0
                z = sorted(hs)[len(hs) // 2]
                if prefer:
                    cost += prefer(x, y, z)
                if best is None or cost < best[0]:
                    best = (cost, x, y, rz, z)
        return best

    def stand(self, name, x, y, rz, z, level=True, ry=0.0):
        """A piece stood: what the mod has in its footprint cleared (on land), the ground under it levelled."""
        key, box = self.piece(name)
        batch = self.batch
        if level:
            z = max(24.0, round(z / 8) * 8.0)
            batch.clear(x, y, rz, box)
            for ck, rk, linked in self.obs.through(x, y, rz, box):          # a building it would stand half through goes whole
                if not linked and (ck, rk) not in batch.gone:
                    batch.gone.add((ck, rk))
                    batch.ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
            batch.level(x, y, rz, box, z)
        cell = self.grid.get((int(x // 4096), int(y // 4096)))
        if cell is None:
            return False
        ck = self.gd.key(cell)
        self.adds.append({'op': 'add', 'cell': ck, 'base': key, 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, round(ry, 4), round(rz % math.tau, 4)], 's': 1.0})
        batch.made.append((x, y, rz, box))
        for o in waikikiset.lights(self.gd, self.pr, name, x, y, z, rz, cell=ck):
            self.lights.append(o)
        self.stood.append({'piece': name, 'label': modelsets.PIECES[name]['label'], 'x': round(x), 'y': round(y), 'turn': round(rz % math.tau, 3), 'z': round(z, 1)})
        return True

    def rings(self, x, y, reach, step=STEP):
        out = [(x, y)]
        for k in range(1, int(reach // step) + 1):
            n = 6 * k
            out += [(x + math.sin(a) * k * step, y + math.cos(a) * k * step) for a in (j * math.tau / n for j in range(n))]
        return out

    def named_name(self, kind, words):
        for _xy, name in self.marks.get(kind, []):
            if any(w in (name or '').lower() for w in words):
                return name
        return None

    def named(self, kind, words):
        for (x, y), name in self.marks.get(kind, []):
            if any(w in (name or '').lower() for w in words):
                return x, y
        return None

    # ----- the rules -----

    def hotels_step(self):
        out = []
        xs = [x for x, _y in self.land] or [0.0]
        x_lo, x_hi = min(xs), max(xs)
        for name in coastset.HOTELS:
            self.progress('Standing the coast\'s hotels', len(out), len(coastset.HOTELS))
            target = self.named('hotel', HOTEL_NAMES.get(name, ()))
            best, by = None, 'the shore'
            if target:
                best = (self.site(name, self.rings(*target, HOTEL_NEAR), near=target, shore=(300.0, 4000.0), apart=modelsets.APART_NEAR)
                        or self.site(name, self.rings(*target, HOTEL_FAR, 384), near=target, shore=(300.0, 5000.0), apart=modelsets.APART_NEAR))
                what = self.named_name('hotel', HOTEL_NAMES[name])
                by = ('near the map\'s ' + what) if best else ('the shore (no room near the map\'s %s)' % what)
            if best is None:
                prefer = (lambda x, y, z: 60.0 * (x_hi - x) / max(1.0, x_hi - x_lo)) if name == 'kahala_reef' else None
                spots = [(x, y) for n, (x, y) in enumerate(self.land) if n % 2 == 0]
                best = (self.site(name, spots, shore=modelsets.SHORE, apart=modelsets.APART_NEAR, prefer=prefer)
                        or self.site(name, spots, shore=modelsets.SHORE_WIDE, apart=modelsets.APART_NEAR, prefer=prefer, step_over=450.0)
                        or self.site(name, self.land, shore=(300.0, 9000.0), apart=modelsets.APART_NEAR, prefer=prefer, step_over=600.0))
            if best is None:
                continue
            _c, x, y, rz, z = best
            if self.stand(name, x, y, rz, z):
                self.hotels.append((name, x, y, rz))
                out.append({'piece': name, 'label': modelsets.PIECES[name]['label'], 'x': round(x), 'y': round(y), 'turn': round(rz % math.tau, 3),
                            'by': by})
                self.stood.pop()                # (a hotel is kept in hotels.json, not coast.json)
        return out

    def headland(self):
        """The land point near the sea with the most sea round it."""
        best = None
        for n, (x, y) in enumerate(self.land):
            if n % 3:
                continue
            d, _u = self.to_sea(x, y)
            if d is None or d > 1500:
                continue
            g = self.batch.height(x, y) or 0.0
            s = self.sea_round(x, y) + g / 400.0
            if best is None or s > best[0]:
                best = (s, x, y)
        return best and (best[1], best[2])

    def lighthouse_step(self):
        target = (self.marks.get('lighthouse') or [(None, '')])[0][0] or self.headland()
        if not target:
            return None
        best = self.site('lighthouse', self.rings(*target, 1600, 128), turns=16, near=target, shore=(0.0, 2000.0), step_over=LIGHT_STEP)
        if best is None:
            return None
        _c, x, y, rz, z = best
        self.stand('lighthouse', x, y, rz, z)
        return {'x': round(x), 'y': round(y), 'by': 'the map\'s lighthouse' if self.marks.get('lighthouse') else 'the headland'}

    def aquarium_step(self):
        target = (self.marks.get('aquarium') or [(None, '')])[0][0]
        best, by = None, 'the shore'
        if target:
            best = (self.site('aquarium', self.rings(*target, 1800), face='land', near=target, shore=(150.0, 2200.0), step_over=250.0)
                    or self.site('aquarium', self.rings(*target, 5000, 320), face='land', near=target, shore=(150.0, 2200.0), step_over=250.0))
            by = 'near the map\'s aquarium' if best else 'the shore (no room near the map\'s aquarium)'
        if best is None:
            best = self.site('aquarium', [(x, y) for n, (x, y) in enumerate(self.land) if n % 2 == 0], face='land', shore=(150.0, 2200.0), step_over=250.0)
        if best is None:
            return None
        _c, x, y, rz, z = best
        self.stand('aquarium', x, y, rz, z)
        return {'x': round(x), 'y': round(y), 'by': by}

    def mast_step(self):
        peaks = sorted(((self.to_sea(x, y)[0] or 1e9, x, y) for (x, y), _n in self.marks.get('peak', [])))
        targets = [(x, y) for d, x, y in peaks if d < 6000] or []
        if not targets:
            high = None
            for n, (x, y) in enumerate(self.land):
                if n % 3:
                    continue
                d, _u = self.to_sea(x, y)
                g = self.batch.height(x, y)
                if d is not None and d < 5000 and g is not None and (high is None or g > high[0]):
                    high = (g, x, y)
            targets = [high[1:]] if high else []
        for target in targets:
            best = self.site('signal_mast', self.rings(*target, 3500, 192), face=None, near=target, step_over=LIGHT_STEP, prefer=lambda x, y, z: -z / 20.0)
            if best:
                _c, x, y, rz, z = best
                self.stand('signal_mast', x, y, rz, z)
                return {'x': round(x), 'y': round(y), 'z': round(z), 'by': 'the map\'s peak' if self.marks.get('peak') else 'the highest ground by the sea'}
        return None

    def _in_water_clear(self, x, y, rz, box):
        """Nothing big at all where a thing in the water would go, and none of the coast's other things in the water near."""
        if self.obs.in_the_way(x, y, rz, box) or self.obs.through(x, y, rz, box):
            return False
        return not any(math.hypot(s['x'] - x, s['y'] - y) < APART_IN_WATER for s in self.stood if s['piece'] in ('wreck', 'groin_pavilion'))

    def groin_step(self):
        lines = sorted(self.groynes, key=lambda g: (0 if 'kapahulu' in (g[1] or '').lower() else 1,
                                                    -sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(g[0], g[0][1:]))))
        tries = [(pts, 'the map\'s groyne' + (' (%s)' % n if n else '')) for pts, n in lines]
        # (and by the shape of the coast: straight out from the middle of the sandy shore)
        sands = []
        A, gx0, gy0 = self.cover.A, self.cover.gx0, self.cover.gy0
        for x, y in self.land:
            if self.sand_code is not None and self.cover.kind[(int(round(y / 128.0)) - gy0) * A + int(round(x / 128.0)) - gx0] == self.sand_code:
                d, (ux, uy) = self.to_sea(x, y)
                if d is not None and d < 400:
                    sands.append((x, y, ux, uy))
        if sands:
            mx, my = sum(s[0] for s in sands) / len(sands), sum(s[1] for s in sands) / len(sands)
            for x, y, ux, uy in sorted(sands, key=lambda s: math.hypot(s[0] - mx, s[1] - my))[:40:8]:
                tries.append(([(x - ux * 300, y - uy * 300), (x + ux * 2500, y + uy * 2500)], 'the shore'))
        for pts, by in tries:
            got = self._lay_groin(pts)
            if got:
                got['by'] = by
                return got
        return None

    def _lay_groin(self, pts):
        ground, water = self.batch.ground, self.water
        wet = lambda x, y: (lambda g, w: g is not None and w is not None and g <= w + 10)(ground.at(x, y), water(x, y))
        # which end is the shore's: the drier
        if sum(wet(*p) for p in pts[:1]) > sum(wet(*p) for p in pts[-1:]):
            pts = pts[::-1]
        # the line as it runs, then on straight past its end until it is far enough out
        steps = []
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            L = math.hypot(bx - ax, by - ay)
            for k in range(int(L // 64)):
                steps.append((ax + (bx - ax) * k * 64 / L, ay + (by - ay) * k * 64 / L, (bx - ax) / L, (by - ay) / L))
        if not steps:
            return None
        ux, uy = steps[-1][2], steps[-1][3]
        ex, ey = pts[-1]
        for k in range(int(GROIN_LONGEST // 64)):
            steps.append((ex + ux * k * 64, ey + uy * k * 64, ux, uy))
        start = next((n for n, s in enumerate(steps) if (lambda g, w: g is not None and w is not None and g <= w + 60)(ground.at(s[0], s[1]), water(s[0], s[1]))), None)
        if start is None:
            return None
        walk, over, n = [], 0.0, start
        step_n = int(coastset.GROIN_STEP // 64)
        while n + step_n < len(steps) and len(walk) * coastset.GROIN_STEP < GROIN_LONGEST:
            a, b = steps[n], steps[n + step_n]
            cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            vx, vy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(vx, vy) or 1.0
            gs = [ground.at(a[0], a[1]), ground.at(b[0], b[1]), ground.at(cx, cy)]
            ws = [water(a[0], a[1]), water(b[0], b[1]), water(cx, cy)]
            if None in gs or None in ws:
                return None
            top = max(max(ws) + GROIN_TOP, max(gs) + 25)
            walk.append((cx, cy, math.atan2(vx / L, vy / L), top + 2 * (len(walk) % 2)))
            if all(g <= w - 40 for g, w in zip(gs, ws)):
                over += coastset.GROIN_STEP
            if over >= GROIN_OUT_MIN and all(g <= w - 80 for g, w in zip(gs, ws)):
                break
            n += step_n
        if over < GROIN_OUT_MIN:
            return None
        _k, box = self.piece('groin_walk')
        for x, y, rz, _z in walk:
            if self.obs.in_the_way(x, y, rz, box) or self.obs.through(x, y, rz, box):
                return None
        lx, ly, lrz, _z = walk[-1]
        ux, uy = math.sin(lrz), math.cos(lrz)
        px, py = lx + ux * (coastset.GROIN_STEP / 2 + 520), ly + uy * (coastset.GROIN_STEP / 2 + 520)
        _k, pbox = self.piece('groin_pavilion')
        w = water(px, py)
        if w is None or not self._in_water_clear(px, py, lrz, pbox):
            return None
        for x, y, rz, z in walk:
            self.batch.clear(x, y, rz, box)
            self.stand('groin_walk', x, y, rz, z, level=False)
        self.batch.clear(px, py, lrz, pbox)
        self.stand('groin_pavilion', px, py, lrz, w + GROIN_TOP, level=False)
        return {'lengths': len(walk), 'over_water': round(over), 'x': round(px), 'y': round(py)}

    def wreck_step(self):
        _k, box = self.piece('wreck')
        reefs = [p for p, _n in self.marks.get('reef', [])]
        if not reefs:                           # (by the depth alone: sea points a little way out)
            reefs = [(x, y) for n, (x, y) in enumerate(self.sea) if n % 7 == 0 and (lambda g, w: g is not None and w is not None and WRECK_DEPTH[0] <= w - g <= WRECK_DEPTH[1])(self.batch.ground.at(x, y), self.water(x, y))][:60]
        best = None
        for rx, ry in reefs:
            for x, y in self.rings(rx, ry, WRECK_FROM, 320):
                for k in range(8):
                    rz = k * math.pi / 4
                    ok, depths = True, []
                    for u in (-1, 0, 1):
                        for v in (-1, -0.5, 0, 0.5, 1):
                            tx, ty = self.lm._turn(u * (box[2] + 200), v * (box[3] + 200) if v > 0 else -v * (box[1] - 200), rz)
                            g, w = self.batch.ground.at(x + tx, y + ty), self.water(x + tx, y + ty)
                            if g is None or w is None or not WRECK_DEPTH[0] <= w - g <= WRECK_DEPTH[1]:
                                ok = False
                                break
                            depths.append(w - g)
                        if not ok:
                            break
                    if not ok:
                        continue
                    cost = math.hypot(x - rx, y - ry) / 300.0 + abs(sum(depths) / len(depths) - 450) / 50.0
                    if best is not None and cost >= best[0]:
                        continue
                    if not self._in_water_clear(x, y, rz, box):
                        continue
                    best = (cost, x, y, rz)
            if best and best[0] < 4:
                break
        if best is None:
            return None
        _c, x, y, rz = best
        self.stand('wreck', x, y, rz, self.water(x, y) + WRECK_OVER - coastset.WRECK_HIGH, level=False, ry=WRECK_LIST)
        return {'x': round(x), 'y': round(y), 'by': 'the map\'s reef' if self.marks.get('reef') else 'the depth'}


def plan(gd, pr, world, cover, roads, xy, marks, seed=1, progress=None, only=None):
    """(ops, report, hotels for maps\\hotels.json (all of them), things for maps\\coast.json). xy: lat/lon to game units
    (osmplace.Georef(...).xy); marks: osm_marks' of the map. only: names of steps (hotels, lighthouse, groin, aquarium,
    wreck, mast) to do just those."""
    import api_maps
    c = Coast(gd, pr, world, cover, roads, xy, marks, seed, progress)
    rep = {}
    steps = [('hotels', c.hotels_step), ('lighthouse', c.lighthouse_step), ('aquarium', c.aquarium_step), ('mast', c.mast_step),
             ('groin', c.groin_step), ('wreck', c.wreck_step)]
    for n, (name, fn) in enumerate(steps):
        if only and name not in only:
            continue
        c.progress('Standing the coast: ' + name, n, len(steps))
        rep[name] = fn()
    seats = modelsets.reseat(gd, pr, c.grid, c.batch)
    gone = {(o['cell'], o['ref']) for o in c.batch.ops if o['op'] == 'remove'}
    for ck, cl in pr.cells.items():
        for rk, r in cl['refs'].items():
            if (ck, rk) in gone and r.get('tel'):
                raise ValueError('The coast would have taken out a door that leads somewhere (%s): nothing was changed.' % rk)
    used = {o['base'] for o in c.adds}
    c.first = [o for name, made in c.made.items() if c.keys[name] in used for o in made]
    ops = c.first + c.batch.done() + c.adds + seats + c.lights
    rep.update(reseated=len(seats), cleared=len(gone), levelled=len(c.batch.forms), lights=len(c.lights), records=len(c.first),
               refused=sorted({'%s: %s' % r for r in c.refused}))
    kept = api_maps._kept(pr, 'hotels.json').get(gd.edid(world)) or []
    hotels = kept + (rep.get('hotels') or [])
    things = (api_maps._kept(pr, 'coast.json').get(gd.edid(world)) or []) + c.stood
    return ops, rep, hotels, things
