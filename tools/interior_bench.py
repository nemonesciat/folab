"""How good are generated places? Many seeds over several kits, read from the files only: nothing goes near the game.

    py -3 tools/interior_bench.py [--seeds 12] [--area 180] [--nav 4] [--kits vault,utility] [--json out.json]

For each kit: the share of seeds that made a place, the share of plans that passed the walk first go, levels used, tall rooms,
balconies, loops, shapes of rooms, different pieces used, and how much of each level the first navmesh covers."""
import argparse
import collections
import json
import os
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
import navgen              # noqa: E402

B = chr(92)
DEFAULT = ('dungeons\\vault', 'vault!', 'dungeons\\vaultruined', 'dungeons\\office', 'dungeons\\utility', 'dungeons\\metro', 'dungeons\\industrial',
           'dungeons\\facility', 'dungeons\\nv_casinolo')


def loops(plan):
    """Ways round: edges - owners + parts, in the graph of who joins whom (stairs count as owners)."""
    live = {o['n'] for o in plan.owners if o['purpose'] != 'outside' and o['purpose'] != 'built'}
    edges = set()
    for link in plan.links:
        a, b = tuple(link)
        x, y = plan.cells.get(a), plan.cells.get(b)
        if x != y and x in live and y in live:
            edges.add(frozenset((x, y)))
    seen, parts = set(), 0
    near = collections.defaultdict(set)
    for e in edges:
        x, y = tuple(e)
        near[x].add(y)
        near[y].add(x)
    for n in live:
        if n in seen:
            continue
        parts += 1
        todo = [n]
        while todo:
            q = todo.pop()
            if q not in seen:
                seen.add(q)
                todo += near[q]
    return len(edges) - len(live) + parts


def level_of(z, rise, floor=0):
    return int((z - floor + rise * 0.35) // rise)


def nav_cover(game, ts, plan, made, items, some_cell):
    """{level: share of its squares the first navmesh covers}, as the Kit tab makes it."""
    refs = P.as_refs(game, made) + D.item_refs(game, items)
    for n, it in enumerate(items):
        if it.what in ('door', 'exit'):
            refs.append({'ref': 200000 + n, 'type': 'REFR', 'base': game.from_key(it.key), 'pos': tuple(it.p[:3]), 'rot': tuple(it.p[3:6]), 'scale': 1.0, 'leads': False, 'bkey': it.key})
    mesh, _rep = navgen.generate(game, some_cell, refs=refs, floors=True)
    if not mesh:
        return {}
    area = collections.Counter()
    V = mesh['verts']
    for t in mesh['tris']:
        a, b, c = V[t[0]], V[t[1]], V[t[2]]
        s = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2
        area[level_of((a[2] + b[2] + c[2]) / 3, plan.rise, ts.floor)] += s
    squares = collections.Counter(c[2] for c in plan.squares())
    return {lv: area[lv] / (squares[lv] * ts.step * ts.step) for lv in sorted(squares)}


def one(game, kits, name, seed, area, sv, store, cache):
    """A generated place and what it took: (g or None, seconds)."""
    t0 = time.time()
    if name == 'vault!':
        ts = P.tiles_for(game, kits, 'dungeons' + B + 'vault', store, sv)
        if hasattr(P, 'vault_place'):
            return ts, P.vault_place(game, kits, 4, seed, store, cache, sv), time.time() - t0
        import random
        g = P.generate(game, ts, seed=seed, cache=cache, program=P.vault_program(4, random.Random(seed)), stairs=0.12, survey=sv, tries=4)
        return ts, g, time.time() - t0
    ts = P.tiles_for(game, kits, name, store, sv)
    if not ts.can['rooms']:
        return ts, None, 0.0
    return ts, P.generate(game, ts, area, seed, cache=cache, survey=sv), time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', type=int, default=12)
    ap.add_argument('--area', type=int, default=180)
    ap.add_argument('--nav', type=int, default=4, help='how many of each kit\'s places get a navmesh')
    ap.add_argument('--kits', default='')
    ap.add_argument('--json', default='')
    ap.add_argument('--index', default=os.path.join(os.environ['TEMP'], 'fri-home', 'kits'))
    a = ap.parse_args()
    game = gamedata.GameData()
    kits = K.load(game, a.index)
    names = [n if n == 'vault!' or B in n else 'dungeons' + B + n for n in a.kits.split(',')] if a.kits else list(DEFAULT)
    want = {'dungeons' + B + 'vault' if n == 'vault!' else n for n in names}
    sv = D.survey(game, kits, only=want)
    some_cell = next(iter(game.interiors))
    out = {}
    print('%-24s %5s %6s %6s %6s %5s %6s %6s %6s %6s %6s  %s' % ('kit', 'made', 'first', 'levels', 'multi', 'tall', 'loops', 'rooms', 'shaped', 'pieces', 'secs', 'navmesh cover by level'))
    for name in names:
        store, cache = {}, {}
        rows = []
        nav = collections.defaultdict(list)
        for seed in range(a.seeds):
            try:
                ts, g, secs = one(game, kits, name, seed * 37 + 1, a.area, sv, store, cache)
            except Exception as e:              # (a crash is a result too: it's counted as not made, and said)
                print('   %s seed %d: %r' % (name, seed, e))
                ts, g, secs = None, None, 0.0
            if not g:
                rows.append(None)
                continue
            plan = g['plan']
            rooms = plan.rooms()
            rows.append({'tries': g.get('tries', 1), 'levels': len({c[2] for c in plan.squares()}), 'loops': loops(plan), 'rooms': len(rooms),
                         'tall': sum(1 for o in rooms if o.get('tall')),
                         'shaped': sum(1 for o in rooms if len(o['cells']) != _box(o['cells'])), 'pieces': len({m.key for m in g['made']}), 'secs': secs,
                         'flights': len(plan.flights), 'kinds': sorted({f.get('kind', 'straight') for f in plan.flights}),
                         'missing': len(g['walk']['missing']), 'escaped': len(g['walk']['escaped'])})
            if seed < a.nav:
                for lv, s in nav_cover(game, ts, plan, g['made'], g['items'], some_cell).items():
                    nav[lv].append(s)
        good = [r for r in rows if r]

        def mean(k):
            return sum(r[k] for r in good) / max(1, len(good))
        first = sum(1 for r in good if r['tries'] == 1) / max(1, len(good))
        cover = ' '.join('L%d %.0f%%(min %.0f)' % (lv, 100 * sum(v) / len(v), 100 * min(v)) for lv, v in sorted(nav.items()))
        print('%-24s %4d%% %5d%% %6.1f %5d%% %5.1f %6.2f %6.1f %6.1f %6.1f %6.1f  %s' % (
            name.replace('dungeons' + B, ''), 100 * len(good) / len(rows), 100 * first, mean('levels'), 100 * sum(1 for r in good if r['levels'] > 1) / max(1, len(good)),
            mean('tall'), mean('loops'), mean('rooms'), mean('shaped'), mean('pieces'), mean('secs'), cover), flush=True)
        out[name] = {'rows': rows, 'nav': {str(k): v for k, v in nav.items()}}
    if a.json:
        with open(a.json, 'w') as f:
            json.dump(out, f)


def _box(cells):
    l0 = cells[0][2]
    pts = [c for c in cells if c[2] == l0]
    return (max(c[0] for c in pts) - min(c[0] for c in pts) + 1) * (max(c[1] for c in pts) - min(c[1] for c in pts) + 1) + len(cells) - len(pts)


if __name__ == '__main__':
    main()
