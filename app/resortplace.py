"""resortset's hotels and landmarks stood over a world made from a map, as one Undo, by `coastplace.Coast`'s means
(sites tried with every turn, the hotels' keep-clear, ground levelled, what stood on moved ground re-seated).

Site rules: where the map has the real thing it stands there or as near as it can; else the shape of the city says.

  lani_moku       an OSM hotel named Hilton or Hawaiian Village, else the strip behind the beach (modelsets.SHORE),
                  facing the sea; APART_NEAR from every hotel (then less, never under FRONT_APART). Always on the beach
                  front from Waikiki to Kahala (FRONT, a lat/lon box) when the map reaches it: towers belong on that shore.
  coral_crescent  an OSM hotel named Outrigger or Sheraton, else the strip behind the beach where there is sand in
                  front of it (its arc holds a beach); facing the sea; on FRONT as Lani Moku.
  tradewinds      inland (LODGE_SEA from the sea) with its courtyard to a road (asphalt LODGE_ROAD from its middle,
                  just past its open side); a motor lodge is on the road, not the beach.
  sky_wheel       tourism=theme_park or an attraction that is a ride or a wheel; else where the people after the war
                  would keep one, on open public ground: by the zoo (tourism=zoo) at the park's edge, else in a park named
                  Kapiolani or Ala Moana, else the biggest park, else by the groin's pavilion (maps\\coast.json); each
                  tried near, then wider, then anywhere on land with the rules eased: it never goes unstood.
  water_tower     man_made=water_tower, else the highest ground within TOWER_ROAD of a road and TOWER_SEA of the sea
                  (where the city is, high enough to give it pressure).
  band_shell      a theatre or bandstand named Shell, else the biggest park; its stage to the park's middle.
  giant_tiki      an attraction named tiki or kahuna, else beside the main road behind the strip, facing it.
  cd_siren        every emergency=siren, else the busiest street corners (OSM highway nodes three or more streets
                  meet at), SIREN_APART from each other, at most SIREN_MOST; each beside its corner, facing it.

maps\\hotels.json gains the hotels, maps\\resort.json lists the rest. NOT twice: it adds. Until `modelsets.Obstacles`
and `modelsets.footprints` know resortset's pieces, later steps don't keep off them (see the notes)."""
import math
import xml.etree.ElementTree as ET

import coastplace
import modelsets
import resortset

HOTEL_NAMES = {'lani_moku': ('hilton', 'hawaiian village'), 'coral_crescent': ('outrigger', 'sheraton')}
LODGE_SEA = (1800.0, 9000.0)
LODGE_ROAD = (1950.0, 2900.0)   # from its middle: the courtyard's open side is 1,870 out
TOWER_ROAD = 900.0
TOWER_SEA = (2500.0, 14000.0)
SIREN_APART = 7000.0
SIREN_MOST = 10
TIKI_ROAD = (450.0, 950.0)
FRONT = ((21.250, -157.848), (21.292, -157.760))    # Waikiki's and Kahala's beach front: (south-west, north-east) lat/lon
FRONT_APART = 2600.0        # the least a tower on the front keeps from another hotel when the front is full
WHEEL_PARKS = ('kapiolani', 'kapiʻolani', 'ala moana')
FAIR_NEAR = 4000.0          # how far from the groin's pavilion the wheel may stand


def osm_marks(path):
    """coastplace's marks, and: 'fair', 'water_tower', 'shell', 'tiki', 'siren' [(lat, lon, name)], 'park' [(lat, lon,
    name, points)], 'corner' [(lat, lon, streets)] where three or more named streets meet."""
    out = coastplace.osm_marks(path)
    for k in ('fair', 'zoo', 'water_tower', 'shell', 'tiki', 'siren', 'park', 'corner'):
        out[k] = []
    nodes, uses = {}, {}
    big = ('primary', 'secondary', 'tertiary', 'residential', 'unclassified')
    for _ev, el in ET.iterparse(path):
        if el.tag == 'node':
            nodes[el.get('id')] = (float(el.get('lat')), float(el.get('lon')))
        if el.tag not in ('node', 'way'):
            continue
        tags = {t.get('k'): t.get('v') for t in el.findall('tag')}
        if el.tag == 'way' and tags.get('highway') in big:
            for n in el.findall('nd'):
                uses[n.get('ref')] = uses.get(n.get('ref'), 0) + 1
        if tags:
            name = tags.get('name', '')
            low = name.lower()
            refs = [n.get('ref') for n in el.findall('nd')] if el.tag == 'way' else [el.get('id')]
            pts = [nodes[r] for r in refs if r in nodes]
            if pts:
                mid = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), name)
                if tags.get('tourism') == 'theme_park' or tags.get('attraction') in ('amusement_ride', 'big_wheel', 'ferris_wheel'):
                    out['fair'].append(mid)
                if tags.get('tourism') == 'zoo':
                    out['zoo'].append(mid)
                if tags.get('man_made') == 'water_tower':
                    out['water_tower'].append(mid)
                if (tags.get('amenity') == 'theatre' or tags.get('leisure') == 'bandstand') and 'shell' in low:
                    out['shell'].append(mid)
                if tags.get('tourism') == 'attraction' and ('tiki' in low or 'kahuna' in low):
                    out['tiki'].append(mid)
                if tags.get('emergency') == 'siren':
                    out['siren'].append(mid)
                if tags.get('leisure') == 'park' and el.tag == 'way' and len(pts) > 3:
                    out['park'].append(mid + (pts,))
        if el.tag == 'way':
            el.clear()
    out['corner'] = [nodes[r] + (n,) for r, n in uses.items() if n >= 3 and r in nodes]
    return out


class Resort(coastplace.Coast):
    def __init__(self, gd, pr, world, cover, roads, xy, marks, seed=1, progress=None):
        coastplace.Coast.__init__(self, gd, pr, world, cover, roads, xy, {k: v for k, v in marks.items() if k != 'park'}, seed, progress)
        A, D, gx0, gy0 = cover.A, cover.D, cover.gx0, cover.gy0
        self.cover = cover
        self.xy = xy
        (fx0, fy0), (fx1, fy1) = xy(FRONT[0]), xy(FRONT[1])
        self.front = (min(fx0, fx1), min(fy0, fy1), max(fx0, fx1), max(fy0, fy1))
        self.front_land = [(x, y) for x, y in self.land if self.on_front(x, y)]
        self.roadpts = {}
        for y in range(0, D, 3):
            for x in range(0, A, 3):
                if cover.kind[y * A + x] == self.road_code:
                    rx, ry = (gx0 + x) * 128.0, (gy0 + y) * 128.0
                    self.roadpts.setdefault((int(rx // 768), int(ry // 768)), []).append((rx, ry))
        self.parks = [(xy((la, lo)), n, [xy(p) for p in pts]) for la, lo, n, pts in marks.get('park', [])]
        self.corners = [(xy((la, lo)), n) for la, lo, n in marks.get('corner', [])]
        self._facing = None
        import api_maps
        self.coast_things = api_maps._kept(pr, 'coast.json').get(gd.edid(world)) or []

    # ----- what's round a spot -----

    def on_front(self, x, y):
        fx0, fy0, fx1, fy1 = self.front
        return fx0 <= x <= fx1 and fy0 <= y <= fy1

    def kind_at(self, x, y):
        c = self.cover
        i, j = int(round(x / 128.0)) - c.gx0, int(round(y / 128.0)) - c.gy0
        if 0 <= i < c.A and 0 <= j < c.D:
            return c.kind[j * c.A + i]
        return None

    def to_road(self, x, y, reach=6):
        best = None
        cx, cy = int(x // 768), int(y // 768)
        for i in range(cx - reach, cx + reach + 1):
            for j in range(cy - reach, cy + reach + 1):
                for rx, ry in self.roadpts.get((i, j), ()):
                    d = (rx - x) ** 2 + (ry - y) ** 2
                    if best is None or d < best[0]:
                        best = (d, rx, ry)
        if best is None:
            return None, (0.0, -1.0)
        d = math.sqrt(best[0]) or 1.0
        return d, ((best[1] - x) / d, (best[2] - y) / d)

    def to_sea(self, x, y):
        """As Coast's, unless a rule has asked for its pieces to face something else (`facing`): then that thing's
        distance and way, so Coast.site's 'shore' and 'face' mean it instead."""
        if self._facing:
            return self._facing(x, y)
        return coastplace.Coast.to_sea(self, x, y)

    def site(self, name, spots, **how):
        """Coast.site over only the spots where the piece's footprint keeps clear of everything stood in this run
        (Batch._score only charges for it, and a near target can outweigh that)."""
        _key, box = self.piece(name)
        r = math.hypot(box[2] - box[0], box[3] - box[1]) / 2
        made = [(kx, ky, math.hypot(kb[2] - kb[0], kb[3] - kb[1]) / 2) for kx, ky, _krz, kb in self.batch.made]
        free = [(x, y) for x, y in spots if all(math.hypot(x - kx, y - ky) >= r + kr for kx, ky, kr in made)]
        return coastplace.Coast.site(self, name, free, **how) if free else None

    def facing(self, fn, name, spots, **how):
        self._facing = fn
        try:
            return self.site(name, spots, **how)
        finally:
            self._facing = None

    def _from_mark(self, kinds):
        for k in kinds:
            got = self.marks.get(k) or []
            if got:
                return got[0][0], got[0][1]
        return None, None

    def _stood(self, name, best, by):
        if best is None:
            return None
        _c, x, y, rz, z = best
        if not self.stand(name, x, y, rz, z):
            return None
        return {'piece': name, 'x': round(x), 'y': round(y), 'turn': round(rz % math.tau, 3), 'by': by}

    # ----- the rules -----

    def hotels_step(self):
        out = []
        spots = [(x, y) for n, (x, y) in enumerate(self.land) if n % 2 == 0]
        for name in resortset.HOTELS:
            self.progress('Standing the hotels', len(out), len(resortset.HOTELS))
            best, by = None, None
            target = self.named('hotel', HOTEL_NAMES.get(name, ()))
            if name == 'tradewinds_lodge':
                face = lambda x, y: self.to_road(x, y)
                best = (self.facing(face, name, spots, shore=LODGE_ROAD, apart=modelsets.APART_NEAR, step_over=220.0,
                                    prefer=lambda x, y, z: 0.0 if LODGE_SEA[0] <= (coastplace.Coast.to_sea(self, x, y)[0] or 0) <= LODGE_SEA[1] else 1e6))
                by = 'a road inland'
            else:
                if target:
                    best = (self.site(name, self.rings(*target, coastplace.HOTEL_NEAR), near=target, shore=(300.0, 4000.0), apart=modelsets.APART_NEAR)
                            or self.site(name, self.rings(*target, coastplace.HOTEL_FAR, 384), near=target, shore=(300.0, 5000.0), apart=modelsets.APART_NEAR))
                    what = self.named_name('hotel', HOTEL_NAMES[name])
                    by = ('near the map\'s ' + what) if best else ('the shore (no room near the map\'s %s)' % what)
                if best is not None and self.front_land and not self.on_front(best[1], best[2]):
                    best, by = None, 'the beach front (no room on it near the map\'s %s)' % self.named_name('hotel', HOTEL_NAMES[name])
                if best is None:
                    prefer = None
                    if name == 'coral_crescent':          # sand in front of it: a beach for the arc to hold
                        def prefer(x, y, z):
                            d, (ux, uy) = coastplace.Coast.to_sea(self, x, y)
                            if d is None:
                                return 50.0
                            sand = sum(1 for t in (0.3, 0.6, 0.9) if self.kind_at(x + ux * d * t, y + uy * d * t) == self.sand_code)
                            return 30.0 * (3 - sand)
                    if self.front_land:             # (the map reaches Waikiki's front: only there, easing the rules till one fits)
                        fs = self.front_land
                        best = (self.site(name, fs, shore=modelsets.SHORE, apart=modelsets.APART_NEAR, prefer=prefer)
                                or self.site(name, fs, shore=modelsets.SHORE_WIDE, apart=modelsets.APART_NEAR * 0.75, prefer=prefer, step_over=450.0)
                                or self.site(name, fs, shore=(200.0, 6000.0), apart=FRONT_APART, prefer=prefer, step_over=600.0))
                        by = by or 'the beach front'
                    else:
                        best = (self.site(name, spots, shore=modelsets.SHORE, apart=modelsets.APART_NEAR, prefer=prefer)
                                or self.site(name, spots, shore=modelsets.SHORE_WIDE, apart=modelsets.APART_NEAR, prefer=prefer, step_over=450.0)
                                or self.site(name, self.land, shore=(300.0, 12000.0), apart=modelsets.APART_NEAR * 0.8, prefer=prefer, step_over=600.0))
                        by = by or 'the shore'
            got = self._stood(name, best, by)
            if got:
                self.hotels.append((name, got['x'], got['y'], got['turn']))
                got['label'] = modelsets.PIECES[name]['label']
                out.append(got)
                self.stood.pop()                    # (a hotel is kept in hotels.json)
        return out

    def wheel_targets(self):
        """Where a wheel would be, best first: [((x, y), why)]."""
        out = [(p, 'the map\'s fairground') for p, _n in self.marks.get('fair', [])]
        out += [(p, 'by the zoo (%s)' % (n or 'the zoo')) for p, n in self.marks.get('zoo', [])]
        out += [(p, 'in %s' % n) for p, n, _pts in self.parks if any(w in (n or '').lower() for w in WHEEL_PARKS)]
        if self.parks:
            def area(pts):
                return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))) / 2
            big = max(self.parks, key=lambda p: area(p[2]))
            out.append((big[0], 'in the biggest park (%s)' % (big[1] or 'unnamed')))
        out += [((t['x'], t['y']), 'by the groin\'s pavilion') for t in self.coast_things if t.get('piece') == 'groin_pavilion']
        return out

    def wheel_step(self):
        every = [(x, y) for n, (x, y) in enumerate(self.land) if n % 2 == 0]
        for target, by in self.wheel_targets():
            best = (self.site('sky_wheel', self.rings(*target, FAIR_NEAR, 320), near=target, face=None, step_over=200.0, apart=2500.0)
                    or self.site('sky_wheel', self.rings(*target, 2 * FAIR_NEAR, 384), near=target, face=None, step_over=320.0, apart=1800.0))
            if best is not None:
                return self._stood('sky_wheel', best, by)
        # (nowhere it belongs has room: the shore, then any land, with the rules eased; it is never left out)
        best = (self.site('sky_wheel', every, shore=(200.0, 5000.0), step_over=300.0, apart=2500.0)
                or self.site('sky_wheel', self.land, face=None, step_over=600.0))
        return self._stood('sky_wheel', best, 'the shore (no room anywhere it belongs)' if best and (coastplace.Coast.to_sea(self, best[1], best[2])[0] or 1e9) < 5000
                           else 'open ground (no room anywhere it belongs)')

    def tower_step(self):
        target, _n = self._from_mark(('water_tower',))
        if target:
            best = self.site('water_tower', self.rings(*target, 1500, 192), near=target, face=None, step_over=260.0)
            return self._stood('water_tower', best, 'the map\'s water tower')
        spots = []
        for n, (x, y) in enumerate(self.land):
            if n % 3:
                continue
            d, _u = coastplace.Coast.to_sea(self, x, y)
            if d is None or not TOWER_SEA[0] <= d <= TOWER_SEA[1]:
                continue
            r, _v = self.to_road(x, y, reach=2)
            if r is not None and r <= TOWER_ROAD:
                spots.append((x, y))
        spots.sort(key=lambda p: -(self.batch.height(*p) or 0.0))
        best = self.site('water_tower', spots[:400], face=None, step_over=260.0, prefer=lambda x, y, z: -z / 40.0)
        return self._stood('water_tower', best, 'high ground in the city')

    def shell_step(self):
        target, _n = self._from_mark(('shell',))
        by = 'the map\'s band shell'
        park = None
        if target is None and self.parks:
            def area(pts):
                return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1]))) / 2
            park = max(self.parks, key=lambda p: area(p[2]))
            target, by = park[0], 'the biggest park (%s)' % (park[1] or 'unnamed')
        if target is None:
            return None
        mid = target
        face = lambda x, y: (math.hypot(mid[0] - x, mid[1] - y) or 1.0, ((mid[0] - x) / (math.hypot(mid[0] - x, mid[1] - y) or 1.0),
                                                                         (mid[1] - y) / (math.hypot(mid[0] - x, mid[1] - y) or 1.0)))
        best = (self.facing(face, 'band_shell', self.rings(*target, 3000, 256)[1:], near=target, step_over=180.0)
                or self.facing(face, 'band_shell', self.rings(*target, 7000, 384)[1:], near=target, step_over=300.0))
        return self._stood('band_shell', best, by)

    def tiki_step(self):
        target, _n = self._from_mark(('tiki',))
        if target:
            best = self.facing(lambda x, y: self.to_road(x, y), 'giant_tiki', self.rings(*target, 1200, 128), near=target, step_over=120.0)
            return self._stood('giant_tiki', best, 'the map\'s tiki')
        spots = []
        for n, (x, y) in enumerate(self.land):
            if n % 2:
                continue
            d, _u = coastplace.Coast.to_sea(self, x, y)
            if d is None or not 800 <= d <= 3500:
                continue
            spots.append((x, y))
        hotels = [(hx, hy) for _p, hx, hy, _r in self.hotels]
        prefer = lambda x, y, z: (min((math.hypot(x - hx, y - hy) for hx, hy in hotels), default=0.0) / 400.0)
        best = self.facing(lambda x, y: self.to_road(x, y), 'giant_tiki', spots, shore=TIKI_ROAD, step_over=120.0, prefer=prefer)
        return self._stood('giant_tiki', best, 'the main road behind the strip')

    def sirens_step(self):
        corners = [p for p, _n in self.marks.get('siren', [])]
        by = 'the map\'s sirens'
        if not corners:
            corners = [p for p, n in sorted(self.corners, key=lambda c: -c[1])]
            by = 'street corners'
        out, done = [], []
        for cx, cy in corners:
            if len(out) >= SIREN_MOST:
                break
            if any(math.hypot(cx - x, cy - y) < SIREN_APART for x, y in done):
                continue
            face = lambda x, y, cx=cx, cy=cy: (math.hypot(cx - x, cy - y) or 1.0, ((cx - x) / (math.hypot(cx - x, cy - y) or 1.0), (cy - y) / (math.hypot(cx - x, cy - y) or 1.0)))
            spots = [(x, y) for x, y in self.rings(cx, cy, 640, 160)[1:] if self.kind_at(x, y) not in (self.road_code, self.sea_code)]
            best = self.facing(face, 'cd_siren', spots, turns=8, step_over=80.0, prefer=lambda x, y, z, cx=cx, cy=cy: math.hypot(x - cx, y - cy) / 60.0)
            got = self._stood('cd_siren', best, by)
            if got:
                out.append(got)
                done.append((cx, cy))
        return out


def plan(gd, pr, world, cover, roads, xy, marks, seed=1, progress=None, only=None):
    """(ops, report, hotels for maps\\hotels.json (all of them), things for maps\\resort.json), as coastplace.plan.
    only: names of steps (hotels, wheel, tower, shell, tiki, sirens)."""
    import api_maps
    c = Resort(gd, pr, world, cover, roads, xy, marks, seed, progress)
    rep = {}
    # (the landmarks the map has a real place for first: a hotel can go anywhere along the shore, the shell only where it is)
    steps = [('wheel', c.wheel_step), ('shell', c.shell_step), ('hotels', c.hotels_step), ('tower', c.tower_step), ('tiki', c.tiki_step),
             ('sirens', c.sirens_step)]
    for n, (name, fn) in enumerate(steps):
        if only and name not in only:
            continue
        c.progress('Standing the city\'s landmarks: ' + name, n, len(steps))
        rep[name] = fn()
    seats = modelsets.reseat(gd, pr, c.grid, c.batch)
    gone = {(o['cell'], o['ref']) for o in c.batch.ops if o['op'] == 'remove'}
    for ck, cl in pr.cells.items():
        for rk, r in cl['refs'].items():
            if (ck, rk) in gone and r.get('tel'):
                raise ValueError('This would have taken out a door that leads somewhere (%s): nothing was changed.' % rk)
    used = {o['base'] for o in c.adds}
    c.first = [o for name, made in c.made.items() if c.keys[name] in used for o in made]
    ops = c.first + c.batch.done() + c.adds + seats + c.lights
    rep.update(reseated=len(seats), cleared=len(gone), levelled=len(c.batch.forms), lights=len(c.lights), records=len(c.first),
               refused=sorted({'%s: %s' % r for r in c.refused}))
    kept = api_maps._kept(pr, 'hotels.json').get(gd.edid(world)) or []
    hotels = kept + (rep.get('hotels') or [])
    things = (api_maps._kept(pr, 'resort.json').get(gd.edid(world)) or []) + c.stood
    return ops, rep, hotels, things
