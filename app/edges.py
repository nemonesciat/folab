"""The edges (docs/waikiki-story-plan.md, "The edges", build list 8), the parts FOLab can make now:

- **Radiation that climbs.** The game's radiation markers (`RadiationMarker` with its reach and rads a second,
  worldrec's 'radiation' extra, as the game's 216 have them), in steps that rise as you go on: across the north from
  just past the settlers' Border Post to the map's top edge (`NORTH_FROM`, `NORTH_STEPS`), where the Kaneohe fallout
  came over; and west behind the wall, deeper into downtown the worse (`WEST_STEPS`), no marker reaching back over the
  wall (each stands `WEST_CLEAR` past it, its reach short of it). None reaches the Crest Trail's line.
- **Signs and bones** on the coast road north of the Border Post: radiation signs and keep-out boards, the dead who
  went on, wrecked carts and cars.

Not here: the game's invisible stop (a border region: FOLab can't make one yet) and the distant ground and ruins
past the land's edges. `ops` returns (ops, report, cells)."""
import json
import math
import os

import borderwall
import ridgeplaces
import shipinside
import townbuild

RAD = 'RadiationMarker'
NORTH_FROM = 94400.0                   # (just past the Border Post at y 93,442; the map ends at 98,304)
NORTH_STEPS = [(1200.0, 1700.0, 1.0), (2600.0, 1700.0, 4.0), (3800.0, 1700.0, 12.0)]   # (past NORTH_FROM, reach, rads/s)
NORTH_X = (-64000.0, 112000.0, 3000.0)
WEST_STEPS = [(3500.0, 1.0), (7000.0, 5.0), (1e9, 12.0)]   # (behind the wall up to this far: rads/s)
WEST_CLEAR = 1700.0
WEST_REACH = 1400.0
GRID = 3000.0
TRAIL_CLEAR = 300.0
SIGNS = ['NVRadiationAreaSign', 'SignRadiation01', 'NVSignRad', 'SCOLWoodSignKeepOut', 'SCOLWoodSignKeepOut02']
DEAD = ['SkeletonWholeBodyRags', 'SkeletonWholeBodyClothes', 'NVDLC03SkeletonStatic', 'SkeletonTorsoNaked']
WRECKS = ['NVWoodCart', 'Car01HulkBodyStatic', 'Car03HulkBodyStatic']
BORDER = (49988.0, 93442.0)
NAMES = {RAD} | set(SIGNS) | set(DEAD) | set(WRECKS)


def _wall_x(y):
    """The wall's x at y along its line from the sea round downtown to the map's west edge, or None past its ends."""
    pts = borderwall.line_world()[:5]
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        if min(ay, by) <= y <= max(ay, by) and by != ay:
            return ax + (bx - ax) * (y - ay) / (by - ay)
    return None


def ops(gd, pr, world, side, roads, trail_lines=None, cat=None):
    import server
    cat = cat if cat is not None else townbuild.load(gd, server.kits_folder())
    B = ridgeplaces.Builder(gd, pr, world, side, cat)
    found = shipinside._forms(gd, NAMES)
    B.key_of.update({e: gd.key(f) for e, f in found.items()})
    rep = {'missing': sorted(NAMES - set(found))}
    trail = []
    for line in (trail_lines or {}).values():
        trail += [tuple(p) for p in line]
    buckets = {}
    for x, y in trail:
        buckets.setdefault((int(x // 2048), int(y // 2048)), []).append((x, y))

    def trail_near(x, y, r):
        for i in range(int((x - r) // 2048), int((x + r) // 2048) + 1):
            for j in range(int((y - r) // 2048), int((y + r) // 2048) + 1):
                for a, b in buckets.get((i, j), ()):
                    if math.hypot(a - x, b - y) < r:
                        return True
        return False

    def marker(x, y, reach, rads):
        if trail_near(x, y, reach + TRAIL_CLEAR):
            return 0
        ck = B.w.cell_at(x, y)
        if ck is None:
            return 0
        z = (B.ground.at(x, y) or 0.0) + 40.0
        B.ops.append({'op': 'add', 'cell': ck, 'base': B.key_of[RAD], 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, 0.0], 's': 1,
                      'extra': {'radiation': {'radius': reach, 'rads': rads}}})
        B.cells.add(ck)
        return 1
    n_north = 0
    x0, x1, dx = NORTH_X
    x = x0
    while x <= x1:
        for off, reach, rads in NORTH_STEPS:
            n_north += marker(x, NORTH_FROM + off, reach, rads)
        x += dx
    n_west = 0
    y = -13000.0
    while y < 42000.0:
        wx = _wall_x(y)
        if wx is not None:
            d = WEST_CLEAR
            while True:
                x = wx - d
                if x < -151000.0:
                    break
                rads = next(r for lim, r in WEST_STEPS if d <= lim)
                n_west += marker(x, y, min(WEST_REACH, d - 300.0), rads)
                d += GRID
        y += GRID
    rep['radiation'] = {'north': n_north, 'west': n_west}
    # the road north from the Border Post: signs, the dead, wrecks
    pts = []
    for name, kind, line in roads:
        if 'Kalaniana' in name:
            pts += [p for p in line if p[1] > BORDER[1] + 300.0 and p[0] < BORDER[0] + 3000.0]
    pts.sort(key=lambda p: p[1])
    dense = pts[:1]
    for a_, b_ in zip(pts, pts[1:]):             # (the road's points every 300, whatever the street map gives)
        L = math.dist(a_, b_)
        for t in range(1, int(L // 300) + 1):
            dense.append((a_[0] + (b_[0] - a_[0]) * t * 300 / L, a_[1] + (b_[1] - a_[1]) * t * 300 / L))
        dense.append(b_)
    pts = dense
    pl = ridgeplaces.Place(B, 'north road', BORDER[0], BORDER[1], 0.0)
    signs = dead = wrecks = 0
    last = None
    for k, (px, py) in enumerate(pts):
        if last and math.dist(last, (px, py)) < 700.0:
            continue
        nxt = pts[min(len(pts) - 1, k + 1)]
        L = math.dist((px, py), nxt) or 1.0
        ux, uy = (nxt[0] - px) / L, (nxt[1] - py) / L
        sd = 1 if (len(pts) - k) % 2 else -1
        sx, sy = px - uy * sd * 420.0, py + ux * sd * 420.0
        yaw = math.atan2(-ux, -uy)                       # (facing back down the road, to whoever comes up it)
        for off in ((420.0, 560.0, 700.0, -420.0, -560.0, -700.0) if k % 3 == 0 else ()):
            sx, sy = px - uy * sd * off, py + ux * sd * off
            kinds = [e for e in SIGNS if B.box(e)]
            if kinds and pl.put(kinds[k % len(kinds)], sx, sy, yaw, r=60.0):
                signs += 1
                break
        for j in range(1 + k % 2):
            a = k * 1.9 + j * 2.3
            dead += pl.put(DEAD[(k + j) % len(DEAD)], px + math.cos(a) * 520.0, py + math.sin(a) * 520.0, a, r=60.0)
        if k % 2 == 0:
            for off in (700.0, 900.0, 1100.0, -700.0, -900.0, -1100.0):
                if pl.put(WRECKS[wrecks % len(WRECKS)], px + uy * sd * off, py - ux * sd * off, yaw + 0.6, r=180.0):
                    wrecks += 1
                    break
        last = (px, py)
    rep['north_road'] = {'signs': signs, 'dead': dead, 'wrecks': wrecks}
    return B.ops, rep, sorted(B.cells)
