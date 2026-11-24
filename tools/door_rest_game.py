"""door_rest_game.py [--home H] [--app A]: READ ONLY, after door_rest_survey.py. For each partly picked door of the game's
own base whose leaf another game piece covers: is it stood against that piece as the game stands it, and does the game's own
instance pick any better (the same rule, nv-rs's)? Linked or not: the game's door is found by its piece within REACH, the
side one stands on carried over in the piece's frame. Also: the doors a DoorBarricade covers, picked with that bar gone,
and whether the door's arrival stands clear of the bar. Adds 'game2' and 'bar' to door_rest_survey.json's rows."""
import collections, json, math, os, struct, sys, time

ARGS = sys.argv[1:]


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


HOME = opt('--home', r'D:\FOLabScratch\v50full')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
HERE = os.path.dirname(os.path.abspath(__file__))
REP = os.path.join(HERE, 'door_rest_survey.json')
REACH = 600.0
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8')
t0 = time.time()
say = lambda *a: print('%5.0fs' % (time.time() - t0), *a, flush=True)

import gamedata, project, server, doorswap, recordio, arrivalcheck  # noqa: E402
import doorpick  # noqa: E402

project.Project.save = lambda *a, **k: sys.exit('tried to save')
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr); server.PR = pr
pr.apply = lambda *a, **k: sys.exit('tried to apply')
gd = server.GD
name = doorswap.Names(gd, pr)
rep = json.load(open(REP, encoding='utf-8'))
rows = [r for r in rep['rows'] if r.get('picked')]
refs = {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}
_g = {}


def group_of(ck):
    if ck not in _g:
        try:
            w = gd.ext_cells.get(gd.from_key(ck))
        except Exception:
            w = None
        _g[ck] = ('world', w) if w is not None else ('place', ck)
    return _g[ck]


def model_of(base):
    try:
        if base.startswith('+'):
            rec = pr.records.get(base)
            m = recordio.field(rec, 'MODL') if rec else None
            return ('meshes' + chr(92) + m) if m else None
        t, e, f, m = gd.describe(gd.from_key(base))
        return gd.model_path(t, m) if m else None
    except Exception:
        return None


def obnd(base):
    try:
        if base.startswith('+'):
            s = next(x for x in pr.records[base]['subs'] if x['tag'] == 'OBND')
            return [int(f['value']) for f in s['fields'] if 'name' in f]
        return list(struct.unpack('<6h', gd.fields(gd.from_key(base))['OBND'][:12]))
    except Exception:
        return None


def to_local(piece_p, x, y):
    """(x, y) in a piece's frame (its z turn only; the convention of navgen._turn)."""
    dx, dy = x - piece_p[0], y - piece_p[1]
    c, s = math.cos(piece_p[5]), math.sin(piece_p[5])
    return dx * c - dy * s, dx * s + dy * c


def to_world_dir(piece_p, lx, ly):
    c, s = math.cos(piece_p[5]), math.sin(piece_p[5])
    return lx * c + ly * s, -lx * s + ly * c


def dir_local(piece_p, vx, vy):
    c, s = math.cos(piece_p[5]), math.sin(piece_p[5])
    return vx * c - vy * s, vx * s + vy * c


leads = {}
for rk, (ck, r) in refs.items():
    t = r.get('tel') or {}
    if t.get('door') and t.get('p'):
        leads.setdefault(t['door'], []).append((ck, rk, t['p']))
P = doorpick.Picker(gd, pr, refs, model_of, group_of)

# --- the mod's door against its main blocker: pose in the blocker's frame, and the side one stands on ---
want = collections.defaultdict(list)
for row in rows:
    if row['base'].startswith('+') or not row.get('by_base'):
        continue
    main = max(row['by_base'], key=row['by_base'].get)
    if main.startswith('(') or main.startswith('+'):
        continue
    ck, r = refs[row['door']]
    best = None
    for ork, orr in P.near(group_of(ck), r['p'][0], r['p'][1]):
        if orr.get('base') == main:
            d = math.hypot(orr['p'][0] - r['p'][0], orr['p'][1] - r['p'][1])
            if best is None or d < best[0]:
                best = (d, ork, orr)
    if not best:
        continue
    orr = best[2]
    a = leads[row['door']][0][2]
    vx, vy = a[0] - r['p'][0], a[1] - r['p'][1]
    ln = math.hypot(vx, vy) or 1.0
    lx, ly = to_local(orr['p'], r['p'][0], r['p'][1])
    row['_pose'] = {'piece': best[1], 'at': (lx, ly, r['p'][2] - orr['p'][2]),
                    'turn': (r['p'][5] - orr['p'][5]) % (2 * math.pi), 'out': dir_local(orr['p'], vx / ln, vy / ln)}
    want[(gd.from_key(row['base']), gd.from_key(main))].append(row)
say('pairs to find in the game', len(want), 'doors', sum(len(v) for v in want.values()))

door_bases = {k[0] for k in want}
piece_bases = {k[1] for k in want}
doors_in, pieces_in = collections.defaultdict(list), collections.defaultdict(list)
for cell in list(gd.cell_refs):
    try:
        got = gd.refs(cell)
    except Exception:
        continue
    for g in got:
        if g['pos'] and g['base'] in door_bases:
            doors_in[cell].append(g)
        if g['pos'] and g['base'] in piece_bases:
            pieces_in[cell].append(g)
say('game cells with those doors', len(doors_in))


def game_refs_round(cell):
    cells = [cell]
    if cell in gd.ext_cells:
        xy = gd.cell_grid(cell)
        grid = gd.grid(gd.ext_cells[cell])
        cells = [grid[(xy[0] + dx, xy[1] + dy)] for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (xy[0] + dx, xy[1] + dy) in grid]
    out = {}
    for c in cells:
        for g in gd.refs(c):
            if g['pos'] and g['base']:
                out[gd.key(g['ref'])] = (gd.key(c), {'base': gd.key(g['base']), 'p': list(g['pos']) + list(g['rot']), 's': g['scale']})
    return out


def neighbours(cell):
    if cell not in gd.ext_cells:
        return [cell]
    xy = gd.cell_grid(cell)
    grid = gd.grid(gd.ext_cells[cell])
    return [grid[(xy[0] + dx, xy[1] + dy)] for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (xy[0] + dx, xy[1] + dy) in grid]


found = {}
for (dbase, pbase), mine in want.items():
    inst = []
    for cell, gs in doors_in.items():
        for g in gs:
            if g['base'] != dbase:
                continue
            for c2 in neighbours(cell):
                for pg in pieces_in.get(c2, ()):
                    if pg['base'] == pbase and math.hypot(pg['pos'][0] - g['pos'][0], pg['pos'][1] - g['pos'][1]) < REACH:
                        pp = list(pg['pos']) + list(pg['rot'])
                        lx, ly = to_local(pp, g['pos'][0], g['pos'][1])
                        inst.append((cell, g, pp, (lx, ly, g['pos'][2] - pg['pos'][2]), (g['rot'][2] - pg['rot'][2]) % (2 * math.pi)))
    found[(dbase, pbase)] = inst
say('game instances found for', sum(1 for v in found.values() if v), 'of', len(found), 'pairs')

cache = {}
for (dbase, pbase), mine in want.items():
    inst = found[(dbase, pbase)]
    for row in mine:
        pose = row['_pose']
        if not inst:
            row['game2'] = None
            continue
        # the game's instance nearest the mod's pose in the piece's frame
        def dist(it):
            dt = min(abs(it[4] - pose['turn']), 2 * math.pi - abs(it[4] - pose['turn']))
            return math.dist(it[3], pose['at']) + dt * 100
        it = min(inst, key=dist)
        cell, g, pp, at, turn = it
        key = (gd.key(g['ref']), round(pose['out'][0], 2), round(pose['out'][1], 2))
        if key not in cache:
            grefs = game_refs_round(cell)
            GP = doorpick.Picker(gd, pr, grefs, model_of, lambda ck: 'g')
            ox, oy = to_world_dir(pp, *pose['out'])
            res = GP.door(gd.key(g['ref']), (ox, oy), obnd(row['base']))
            cache[key] = {'game_door': gd.key(g['ref']), 'cell': gd.edid(cell) or gd.key(cell), 'picked': res['picked'],
                          'spots': res['spots'], 'by': {(name(b)[0] or b): n for b, n in res['by'].items()}}
        row['game2'] = dict(cache[key], pose_off=round(dist(it), 1), instances=len(inst), game_s=round(g['scale'], 4),
                            game_dz=round(at[2] - pose['at'][2], 1))
        mr = refs[row['door']][1]
        if abs(g['scale'] - float(mr.get('s') or 1.0)) > 0.005 and dist(it) < 20:
            was_s = mr.get('s')
            mr['s'] = round(g['scale'], 4)
            ck_ = refs[row['door']][0]
            a_ = leads[row['door']][0][2]
            vx_, vy_ = a_[0] - mr['p'][0], a_[1] - mr['p'][1]
            ln_ = math.hypot(vx_, vy_)
            res_ = P.door(row['door'], (vx_ / ln_, vy_ / ln_), obnd(row['base']))
            mr['s'] = was_s
            row['at_game_s'] = {'s': round(g['scale'], 4), 'picked': res_['picked'],
                                'by': {(name(b)[0] or b): n for b, n in res_['by'].items()}}
say('game doors picked', len(cache))

# --- doors a DoorBarricade covers: picked with the bar gone; arrival clear of the bar ---
W = arrivalcheck.World(gd, pr)
for row in rows:
    bars = [b for b in row.get('by_base', {}) if (name(b)[0] or '') == 'DoorBarricade']
    if not bars:
        continue
    ck, r = refs[row['door']]
    gone = []
    for ork, orr in list(P.near(group_of(ck), r['p'][0], r['p'][1])):
        if orr.get('base') in bars and math.hypot(orr['p'][0] - r['p'][0], orr['p'][1] - r['p'][1]) < 200:
            gone.append(ork)
    saved = {}
    for g_ in gone:
        key = (group_of(refs[g_][0]), int(refs[g_][1]['p'][0] // 1024), int(refs[g_][1]['p'][1] // 1024))
        P.grid[key].remove(g_)
        saved[g_] = key
    a = leads[row['door']][0][2]
    vx, vy = a[0] - r['p'][0], a[1] - r['p'][1]
    ln = math.hypot(vx, vy)
    res = P.door(row['door'], (vx / ln, vy / ln), obnd(row['base']))
    for g_, key in saved.items():
        P.grid[key].append(g_)
    # where you come out of this door: the arrival of the link that names it
    arr = []
    for ack, ark, ap in leads[row['door']]:
        blocked, inside = W.judge(group_of(ck), ap[0], ap[1], ap[2], W.outside(group_of(ck)))
        arr.append({'from': ark, 'blocked by': (name(refs[blocked][1]['base'])[0] if blocked else None),
                    'd_door': round(math.hypot(ap[0] - r['p'][0], ap[1] - r['p'][1]))})
    row['bar'] = {'bars': gone, 'picked_without': res['picked'], 'by_without': {(name(b)[0] or b): n for b, n in res['by'].items()},
                  'arrivals': arr, 'bar_d': [round(math.hypot(refs[g_][1]['p'][0] - r['p'][0], refs[g_][1]['p'][1] - r['p'][1])) for g_ in gone]}
say('barred doors', sum(1 for r in rows if r.get('bar')))
for r in rows:
    r.pop('_pose', None)
json.dump(rep, open(REP, 'w', encoding='utf-8'), indent=1)
say('written', REP)
