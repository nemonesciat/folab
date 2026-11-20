"""The way off the Castaway's beach (docs/waikiki-story-plan.md, "The start"): "Road's up there, over the rim."

Hanauma's beach lies in a crater whose west wall rises ~3,600 in 3 km (about 45 degrees); the rim road comes down the
north side. So the path is the gentlest way from where you wake to the nearest stretch of that road: a cheapest-way
search over the land (cresttrail.Grid's, with a cost that keeps to gentle ground instead of high ground: `GRADE`, and
nothing steeper than `TOO_STEEP`), then cresttrail.Trail's tread (no step over its MAX_GRADE), mud, clearing and
re-seating, and a signpost at each end.

`ops(gd, pr, world, side, start, road_keys)` -> (ops, report, cells). start: where you wake (x, y); road_keys: the base
keys of road pieces (the path ends at the nearest one it can reach)."""
import math

import cresttrail
import ridgeplaces
import townbuild

BOX_PAD = 2500.0
GRADE = 40.0                 # (cost of steepness: a 1-in-2 step costs 11 times a flat one)
TOO_STEEP = 0.85             # (rise over run no step of the search may take)
ROAD_NEAR = 350.0            # (the path ends within this of a road piece's middle line)


class GentleGrid(cresttrail.Grid):
    def cost(self, a, b):
        ha, hb = self.H[a[0]][a[1]], self.H[b[0]][b[1]]
        if hb is None or ha is None or hb < 4.0:
            return None
        L = cresttrail.ST * math.hypot(a[0] - b[0], a[1] - b[1])
        gr = abs(hb - ha) / L
        if gr > TOO_STEEP:
            return None
        return L * (1 + GRADE * gr * gr)


def ops(gd, pr, world, side, start, road_refs, cat=None):
    """road_refs: [(x, y, z)] of the road pieces the path may end at."""
    import server
    cat = cat if cat is not None else townbuild.load(gd, server.kits_folder())
    T = cresttrail.Trail(gd, pr, world, side, cat)
    B = T.B
    xs = [start[0]] + [r[0] for r in road_refs]
    ys = [start[1]] + [r[1] for r in road_refs]
    box = (min(xs) - BOX_PAD, max(xs) + BOX_PAD, min(ys) - BOX_PAD, max(ys) + BOX_PAD)
    G = GentleGrid(B.ground, box)
    goal = set()
    for x, y, _z in road_refs:
        n = G.node(x, y)
        for dj in range(-2, 3):
            for di in range(-2, 3):
                m = (n[0] + dj, n[1] + di)
                if 0 <= m[0] < G.ny and 0 <= m[1] < G.nx:
                    goal.add(m)
    path = G.route(G.node(*start), goal)
    rep = {'found': bool(path)}
    if not path:
        return [], rep, []
    pts = cresttrail.smooth_line([G.xy(n) for n in path])
    T.line_buckets = {}
    for x, y in pts:
        T.line_buckets.setdefault((int(x // 512), int(y // 512)), []).append((x, y))
    held = T.tread(pts, skip=120.0)               # (not under you: where you wake stays as it is)
    T.paint(pts)
    moved, gone = T.reseat()
    # signposts: a little way up from the beach, and where the path meets the road
    pl = ridgeplaces.Place(B, 'beach path', 0.0, 0.0, 0.0)
    signs = 0
    for k in (min(12, len(pts) - 2), len(pts) - 4):
        if 0 <= k < len(pts) - 1:
            (x, y), (x2, y2) = pts[k], pts[k + 1]
            L = math.hypot(x2 - x, y2 - y) or 1.0
            signs += T.sign(pl, x, y, (x2 - x) / L, (y2 - y) / L)
    length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    prof = T.zs[0]
    grades = [abs(b - a) / max(1.0, math.dist(p, q)) for (p, a), (q, b) in zip(prof, prof[1:])]
    steep = {}
    walk = cresttrail.walk_check(B.ground, {'path': pts}, where=steep, zs=T.zs)
    rep.update({'length': round(length), 'from_z': round(prof[0][1]), 'to_z': round(prof[-1][1]),
                'steepest_line_deg': round(math.degrees(math.atan(max(grades))), 1), 'walk': walk, 'steep_at': steep,
                'land_points': len(T.changed), 'held': held, 'moved': moved, 'cleared': gone, 'signs': signs,
                'missing': sorted(B.rep['missing']), 'line': [(round(x), round(y)) for x, y in pts]})
    lands = []
    for k in sorted(B.forms):
        ck = gd.key(B.w.grid[k])
        lands.append({'op': 'land', 'cell': ck, 'land': B.forms[k]})
        B.cells.add(ck)
    moves = [{'op': 'move', 'cell': ck, 'ref': rk, 'p': p} for (ck, rk), p in sorted(B.moved.items()) if (ck, rk) not in B.gone]
    return lands + moves + B.ops, rep, sorted(B.cells)
