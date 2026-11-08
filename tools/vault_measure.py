"""How good are generated vaults, as someone looking at one sees them? Read from the files only: nothing goes near the game.

    py -3 tools/vault_measure.py [--seeds 8] [--sizes 2,4,7] [--ruined] [--map] [--rooms] [--json out.json]

For each vault: squares that can be walked to, how much of the building's outline it fills from above, how far apart its rooms
stand, how much of it is corridor, corridors that go nowhere, the share of rooms that read as what they're for, and the most of
one big thing in a room. --map draws each level, --rooms lists each room and what's in it."""
import argparse
import collections
import json
import os
import statistics
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'app'))
os.environ.setdefault('FOLAB_HOME', os.path.join(tempfile.gettempdir(), 'folab-bench'))
import gamedata            # noqa: E402
import kitdress as D       # noqa: E402
import kitindex as K       # noqa: E402
import kitplan as P        # noqa: E402

B = chr(92)
# (the judge's own words and expectations, so a vault made by any version of the generator is judged alike)
JUDGE_WORDS = {'sleep': ('bed', 'bunk', 'mattress', 'cot', 'pillow', 'dresser', 'nightstand', 'wardrobe', 'bedroll', 'footlocker'),
               'desk': ('desk', 'terminal', 'computer', 'filing', 'file', 'typewriter', 'office', 'swivel', 'clipboard'),
               'eat': ('food', 'plate', 'kitchen', 'stove', 'fridge', 'refrigerator', 'oven', 'diner', 'cafeteria', 'dinerbooth', 'mug', 'tray', 'vending'),
               'machine': ('machine', 'machinery', 'reactor', 'generator', 'console', 'tank', 'turbine', 'pump', 'toolbox', 'workbench', 'mainframe', 'acunit', 'unit'),
               'store': ('crate', 'shelf', 'shelves', 'box', 'barrel', 'cabinet', 'chest', 'safe', 'rack', 'locker'),
               'care': ('medical', 'surgical', 'anesthesia', 'gurney', 'clinic', 'autodoc', 'firstaid', 'hospital'),
               'play': ('pool', 'chessboard', 'couch', 'jukebox', 'pinball', 'hamradio', 'radio', 'toy', 'teddy', 'piano', 'television'),
               'wash': ('toilet', 'stall', 'bathtub', 'shower', 'urinal', 'sink'),
               'learn': ('chalkboard', 'blackboard', 'school', 'classroom', 'lectern', 'globe')}
JUDGE = {'quarters': {'sleep'}, 'small room': {'sleep', 'store'}, 'office': {'desk'}, 'workroom': {'machine', 'desk'}, 'reactor': {'machine'}, 'far end': {'machine', 'store'},
         'long room': {'eat', 'store', 'care'}, 'atrium': {'eat'}, 'hall': {'eat', 'desk'}, 'entrance': {'store', 'machine'}, 'store': {'store'}, 'mess': {'eat'}, 'clinic': {'care'},
         'rec room': {'play'}, 'washroom': {'wash'}, 'classroom': {'learn', 'desk'}, 'under a balcony': {'store', 'eat'}, 'over a balcony': {'desk', 'sleep'}, 'over the hall': {'desk'}}
FITTINGS = ('skeleton', 'protectron', 'corpse', 'body', 'light', 'lights', 'lamp', 'fan', 'vent', 'conduit', 'klaxon', 'graf', 'graff', 'graffiti', 'stain', 'blood', 'decal', 'poster', 'drape', 'fog', 'mist', 'dust', 'glow',
            'litter', 'fx', 'arc', 'leak', 'intercom', 'speakers', 'pole', 'mat', 'wall', 'panel', 'cable', 'securiton', 'camera')


def judged(edid):
    """(is it a furnishing rather than a fitting, the purposes its name says)"""
    words = set(D.words_of(edid or ''))
    plain = (edid or '').lower()
    return not words & set(FITTINGS), {t for t, ws in JUDGE_WORDS.items() if any(w in words or (len(w) >= 6 and w in plain) for w in ws)}


def tops(plan):
    """What's seen from above: {(i, j)} of everything but the air."""
    return {(c[0], c[1]) for c, n in plan.cells.items() if c not in plan.air and plan.owners[n]['purpose'] != 'outside'}


def room_gaps(plan):
    """Squares between each room and the nearest other room seen from above, on any level; a room on a tall room's balcony counts as part of it."""
    rooms = [o for o in plan.rooms() if not o.get('part_of')]
    outlines = {}
    for o in rooms:
        cells = {(c[0], c[1]) for c in o['cells']}
        for m in o.get('sides', ()):
            cells |= {(c[0], c[1]) for c in plan.owners[m]['cells']}
        outlines[o['n']] = cells
    out = {}
    for o in rooms:
        best = None
        for p in rooms:
            if p is o:
                continue
            for a in outlines[o['n']]:
                for b in outlines[p['n']]:
                    g = max(abs(a[0] - b[0]), abs(a[1] - b[1])) - 1
                    if best is None or g < best:
                        best = g
        out[o['n']] = max(0, best or 0)
    return out


def clusters(plan):
    """Parts of the outline seen from above, with no square touching another part (corners count): (how many, largest gap between a part and the rest)."""
    seen, parts = set(), []
    cells = tops(plan)
    for c in cells:
        if c in seen:
            continue
        part, todo = set(), [c]
        while todo:
            q = todo.pop()
            if q in part:
                continue
            part.add(q)
            for a in (-1, 0, 1):
                for b in (-1, 0, 1):
                    n = (q[0] + a, q[1] + b)
                    if n in cells and n not in part:
                        todo.append(n)
        seen |= part
        parts.append(part)
    gap = 0
    if len(parts) > 1:
        for part in parts:
            rest = cells - part
            gap = max(gap, min(max(abs(a[0] - b[0]), abs(a[1] - b[1])) - 1 for a in part for b in rest))
    return len(parts), gap


def dead_ends(plan):
    """Corridor squares with one way on, that don't end at a door, stairs or anything else: corridors that go nowhere."""
    ways = collections.Counter()
    for link in plan.links:
        for c in link:
            ways[c] += 1
    for f in plan.flights:
        for q in f['ports']:
            ways[q[0]] += 0
    return [c for o in plan.owners if o['kind'] == P.HALL for c in o['cells'] if ways[c] < 2]


def longest_run(plan):
    return max((len(o['cells']) for o in plan.owners if o['kind'] == P.HALL), default=0)


def wayfinding(plan):
    """How easy it is to find your way: from the entrance's middle, walking the plan square by square. {'doors': owners passed through
    to reach a room (mean), 'doors_max', 'detour': walked over straight-line squares (mean), 'bends', 'junctions': corridor squares
    that turn, or give a choice of three or more, 'runs': separate corridors, 'flights'}."""
    near = collections.defaultdict(set)

    def join(a, b):
        near[a].add(b)
        near[b].add(a)
    for link in plan.links:
        a, b = tuple(link)
        join(a, b)
    for (c, d) in plan.opens:
        join(c, (c[0] + P.DX[d][0], c[1] + P.DX[d][1], c[2]))
    for o in plan.owners:
        cells = [c for c in o['cells'] if c not in plan.air] if o['kind'] != P.VOID else o['cells']
        have = set(cells)
        if o['kind'] == P.VOID:
            for a in cells:          # (a flight of stairs is one step, whichever way through)
                for b in cells:
                    if a != b:
                        join(a, b)
        else:
            for c in cells:
                for d in range(4):
                    n = (c[0] + P.DX[d][0], c[1] + P.DX[d][1], c[2])
                    if n in have:
                        join(c, n)
    first = plan.owners[0]['cells']
    mx, my = sum(c[0] for c in first) / len(first), sum(c[1] for c in first) / len(first)
    start = min(first, key=lambda c: abs(c[0] - mx) + abs(c[1] - my))
    dist, doors = {start: 0}, {start: 0}
    todo = collections.deque([start])
    while todo:
        q = todo.popleft()
        for n in near[q]:
            if n not in dist:
                dist[n] = dist[q] + 1
                doors[n] = doors[q] + (plan.cells.get(n) != plan.cells.get(q))
                todo.append(n)
    rooms = [o for o in plan.rooms() if o['n'] != 0]
    d_list, det = [], []
    for o in rooms:
        cells = [c for c in o['cells'] if c in dist]
        if not cells:
            continue
        c = min(cells, key=lambda q: dist[q])
        d_list.append(doors[c])
        det.append(dist[c] / max(1, abs(c[0] - start[0]) + abs(c[1] - start[1])))
    bends = junctions = 0
    for o in plan.owners:
        if o['kind'] == P.HALL:
            for c in o['cells']:
                ways = [d for d in range(4) if (c[0] + P.DX[d][0], c[1] + P.DX[d][1], c[2]) in near[c]]
                if len(ways) >= 3:
                    junctions += 1
                elif len(ways) == 2 and (ways[0] + 2) % 4 != ways[1]:
                    bends += 1
    return {'doors': statistics.mean(d_list) if d_list else 0, 'doors_max': max(d_list, default=0), 'detour': statistics.mean(det) if det else 0, 'bends': bends, 'junctions': junctions,
            'runs': sum(1 for o in plan.owners if o['kind'] == P.HALL), 'flights': len(plan.flights)}


def tall_owner(plan, o):
    return plan.owners[o['part_of']] if o.get('part_of') is not None else o


def room_reads(sv, plan, o, things):
    """(what it's meant to be for, furnishings for that, furnishings for something else, furnishings, things of any kind)."""
    wanted = JUDGE.get(o.get('dress') or o['purpose'], set())
    good = off = big = n = 0
    for it in things:
        info = sv.info.get(it.key, ('thing', (), ''))
        if it.what in ('light', 'door', 'exit') or info[0] == 'light':
            continue
        n += 1
        if it.what in D.BIG_KINDS:
            is_big, tags = judged(info[2])
            if is_big:
                big += 1
                good += bool(tags & wanted)
                off += bool(tags and not tags & wanted)
    return wanted, good, off, big, n


def measure(game, ts, sv, g):
    plan, items = g['plan'], g['items']
    per = collections.defaultdict(list)
    for it in items:
        if it.owner is not None:
            per[it.owner].append(it)
    # (what reads: a room with something big for what it's for and something more; or a room left wrecked on purpose)
    rooms = [o for o in plan.rooms() if not o.get('tall') or per[o['n']]]
    clear = wrecked = empty = mixed = 0
    most, most_what = 0, ''
    for o in rooms:
        _w, good, off, big, n = room_reads(sv, plan, o, per[o['n']])
        if o.get('wrecked'):
            wrecked += 1
        elif good >= 1 and off <= good:
            clear += 1
        elif off > good:
            mixed += 1
        if big == 0 and n < 3 and not o.get('wrecked'):
            empty += 1
        c = collections.Counter(it.key for it in per[o['n']] if it.what in D.BIG_KINDS and judged(sv.info.get(it.key, ('', (), ''))[2])[0])
        for k, v in c.items():
            if v > most:
                most, most_what = v, sv.info.get(k, ('', (), k))[2]
    gaps = room_gaps(plan)
    outline = tops(plan)
    xs, ys = [c[0] for c in outline], [c[1] for c in outline]
    squares = plan.squares()
    halls = sum(1 for c in squares if plan.owners[plan.cells[c]]['kind'] == P.HALL)
    parts, part_gap = clusters(plan)
    box = (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1)
    return {**wayfinding(plan), 'rooms': len(rooms), 'wanted': g.get('wanted'), 'squares': len(squares), 'reach': 1 - len(g['walk']['missing']) / max(1, len(squares)),
            'levels': len({c[2] for c in squares}), 'w': max(xs) - min(xs) + 1, 'h': max(ys) - min(ys) + 1, 'fill': len(outline) / box,
            'gap_max': max(gaps.values(), default=0), 'gap_mean': statistics.mean(gaps.values()) if gaps else 0, 'parts': parts, 'part_gap': part_gap,
            'hall_share': halls / max(1, len(squares)), 'longest': longest_run(plan), 'dead': len(dead_ends(plan)),
            'story': getattr(plan, 'story', ''), 'scenes': sum(1 for o in rooms if o.get('scenes')) / max(1, len(rooms)), 'finds': sum(1 for o in rooms if o.get('find')),
            'clear': clear / max(1, len(rooms) - wrecked), 'mixed': mixed, 'wrecked': wrecked, 'empty': empty, 'most': most, 'most_what': most_what}


def draw(plan):
    """Each level as rows of letters: a room is a letter of its own, - a corridor, = stairs, ~ the air of a tall room."""
    names = {}
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    for o in plan.rooms():
        names[o['n']] = letters[len(names) % len(letters)]
    allc = list(plan.cells)
    x0, x1 = min(c[0] for c in allc), max(c[0] for c in allc)
    y0, y1 = min(c[1] for c in allc), max(c[1] for c in allc)
    for l in sorted({c[2] for c in allc}):
        print('  level', l)
        for j in range(y1, y0 - 1, -1):
            row = ''
            for i in range(x0, x1 + 1):
                c = (i, j, l)
                n = plan.cells.get(c)
                if n is None:
                    row += '.'
                elif c in plan.air:
                    row += '~'
                else:
                    k = plan.owners[n]['kind']
                    row += '-' if k == P.HALL else '=' if k == P.VOID else names[n]
            print('   ', row)
    print('  rooms:', ' '.join('%s=%s' % (names[o['n']], o.get('dress') or o['purpose']) for o in plan.rooms()))


def list_rooms(sv, plan, items):
    per = collections.defaultdict(list)
    for it in items:
        per[it.owner].append(it)
    for o in plan.rooms():
        w, good, off, big, n = room_reads(sv, plan, o, per[o['n']])
        c = collections.Counter(sv.info.get(it.key, ('', (), it.key))[2] for it in per[o['n']] if it.what not in ('light', 'door', 'exit'))
        print('  %-16s %-14s %3d sq, theme %s; scenes %s find %s; for it %d, for else %d, big %d, all %d%s: %s' % (
            o['purpose'], o.get('dress') or '', sum(1 for q in o['cells'] if q not in plan.air), o.get('theme'), o.get('scenes'), o.get('find'), good, off, big, n, ' WRECKED' if o.get('wrecked') else '',
            ', '.join('%s %d' % r for r in c.most_common(10))))


COLUMNS = ('rooms', 'squares', 'reach', 'levels', 'fill', 'gap_max', 'hall_share', 'doors', 'doors_max', 'detour', 'bends', 'junctions', 'runs', 'flights', 'clear', 'wrecked', 'most', 'scenes', 'finds')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', type=int, default=8)
    ap.add_argument('--sizes', default='2,4,7')
    ap.add_argument('--ruined', action='store_true')
    ap.add_argument('--map', action='store_true')
    ap.add_argument('--rooms', action='store_true')
    ap.add_argument('--json', default='')
    ap.add_argument('--index', default=os.path.join(os.environ['TEMP'], 'fri-home', 'kits'))
    a = ap.parse_args()
    game = gamedata.GameData()
    kits = K.load(game, a.index)
    name = 'dungeons' + B + ('vaultruined' if a.ruined else 'vault')
    svs = D.survey(game, kits, only={name})
    store, cache = {}, {}
    ts = P.tiles_for(game, kits, name, store, svs)
    sv = svs[name]
    print(('%-12s' + ' %6s' * len(COLUMNS) + '  %s') % (('vault',) + COLUMNS + ('most of',)))
    out = []
    for size in (int(s) for s in a.sizes.split(',')):
        rows = []
        for k in range(a.seeds):
            seed = k * 37 + 1
            t0 = time.time()
            g = P.vault_place(game, kits, size, seed, store, cache, svs, a.ruined)
            if not g:
                print('size %d seed %d: none made' % (size, seed))
                rows.append(None)
                continue
            m = measure(game, ts, sv, g)
            m['size'], m['seed'], m['secs'] = size, seed, time.time() - t0
            rows.append(m)
            print(('%-12s' + ' %6.2f' * len(COLUMNS) + '  %s') % (('s%d seed %d' % (size, seed),) + tuple(float(m[c]) for c in COLUMNS) + (m['most_what'],)), flush=True)
            if a.map:
                draw(g['plan'])
            if a.rooms:
                list_rooms(sv, g['plan'], g['items'])
        good = [r for r in rows if r]
        if good:
            print(('%-12s' + ' %6.2f' * len(COLUMNS)) % (('s%d mean' % size,) + tuple(statistics.mean(float(r[c]) for r in good) for c in COLUMNS)), '  made %d/%d, %.0f s each' % (len(good), len(rows), statistics.mean(r['secs'] for r in good)), flush=True)
        out += good
    if a.json:
        with open(a.json, 'w') as f:
            json.dump(out, f)


if __name__ == '__main__':
    main()
