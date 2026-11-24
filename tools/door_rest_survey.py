"""door_rest_survey.py [--home H] [--app A] [--out F]: READ ONLY. The doors the door pick step (23 Nov 2026) left picked at
only some spots (nv-rs gives "Open" on part of the leaf). For each: what takes the pick at the other spots (the door's own
building or room, something loose, nothing), how much moving the door out 1..6 along its face helps, whether it would
then stand off what it stood on (floats), and how the game stands the same door with the same blocker in its own files
(picked by the same rule): when the game's own is no better, the door is as the game has it.

Writes nothing to any mod; the report goes to --out (default door_rest_survey.json beside this)."""
import collections, json, math, os, struct, sys, time

ARGS = sys.argv[1:]


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


HOME = opt('--home', r'D:\FOLabScratch\v50full')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = opt('--out', os.path.join(HERE, 'door_rest_survey.json'))
MOST = 6
SUPPORT_UP, SUPPORT_DOWN = 24.0, 200.0
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8')
t0 = time.time()
say = lambda *a: print('%5.0fs' % (time.time() - t0), *a, flush=True)

import gamedata, project, server, doorswap, recordio, land as _land, arrivalcheck  # noqa: E402
import doorpick  # noqa: E402

save = project.Project.save
project.Project.save = lambda *a, **k: sys.exit('survey tried to save')
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr); server.PR = pr
pr.apply = lambda *a, **k: sys.exit('survey tried to apply')
gd = server.GD
name = doorswap.Names(gd, pr)
say('mod', os.path.join(project.PROJECTS_DIR, 'Waikiki.json'))

rep = json.load(open(os.path.join(HERE, 'door_pick_report.json'), encoding='utf-8'))
LIST = [k for k, v in rep['after'].items() if v['picked'] < v['spots']]
say('doors the pick step left partly picked', len(LIST))

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


leads = {}
leads_all = set()
for rk, (ck, r) in refs.items():
    t = r.get('tel') or {}
    if t.get('door') and t.get('p'):
        leads.setdefault(t['door'], []).append((ck, rk, t['p']))
        leads_all.add(t['door'])
P = doorpick.Picker(gd, pr, refs, model_of, group_of)
W = arrivalcheck.World(gd, pr)

# --- ground: the mod's land over the game's ---
forms = {}


def land_z(world, x, y):
    def form(cx, cy):
        if (world, cx, cy) not in forms:
            cell = gd.grid(world).get((cx, cy))
            f_ = None
            if cell is not None:
                mine = pr.land.get(gd.key(cell))
                e_ = gd.land_at(world, cx, cy)
                if mine or e_:
                    f_ = dict(mine) if mine else _land.decode(gd, e_, {})
            forms[(world, cx, cy)] = f_
        return forms[(world, cx, cy)]
    gx, gy = x / 128.0, y / 128.0
    x0, y0 = int(math.floor(gx)), int(math.floor(gy))
    fx, fy = gx - x0, gy - y0
    v = []
    for a, b in ((x0, y0), (x0 + 1, y0), (x0, y0 + 1), (x0 + 1, y0 + 1)):
        cx, cy = a // 32, b // 32
        f_ = form(cx, cy)
        if not f_:
            return None
        v.append(float(f_['h'][(b - cy * 32) * 33 + (a - cx * 32)]))
    return (v[0] * (1 - fx) + v[1] * fx) * (1 - fy) + (v[2] * (1 - fx) + v[3] * fx) * fy


def support(group, x, y, top, skip):
    """The highest solid surface under (x, y) from `top` down SUPPORT_DOWN (land outside included), or None."""
    best = None
    for t, rk in W.around(group, x, y, 4, skip):
        d = arrivalcheck._hit((x, y, top), (0.0, 0.0, -1.0), t[0])
        if d is not None and d <= SUPPORT_DOWN:
            z = top - d
            best = z if best is None else max(best, z)
    if group[0] == 'world':
        z = land_z(group[1], x, y)
        if z is not None and top - SUPPORT_DOWN <= z <= top:
            best = z if best is None else max(best, z)
    return best


def leaf_frame(r, box, out, p):
    s = float(r.get('s') or 1.0)
    rz = p[5]
    c, sn = math.cos(rz), math.sin(rz)
    thin_x = (box[3] - box[0]) < (box[4] - box[1])
    width = ((box[4] - box[1]) if thin_x else (box[3] - box[0])) * s
    thick = ((box[3] - box[0]) if thin_x else (box[4] - box[1])) * s
    lx, ly = (1.0, 0.0) if thin_x else (0.0, 1.0)
    nx, ny = lx * c + ly * sn, -lx * sn + ly * c
    if nx * out[0] + ny * out[1] < 0:
        nx, ny = -nx, -ny
    mx, my = (box[0] + box[3]) / 2.0 * s, (box[1] + box[4]) / 2.0 * s
    q = (p[0] + mx * c + my * sn, p[1] - mx * sn + my * c)
    return q, (nx, ny), (-ny, nx), width, thick, p[2] + box[2] * s


def floor_gap(rk, r, box, out, p):
    """How far the door's foot stands over what is under its leaf (the worst of six spots: three across, front and
    back of the leaf), None where nothing is under within reach."""
    ck = refs[rk][0]
    q, n, t, width, thick, foot = leaf_frame(r, box, out, p)
    worst = None
    for u in (-0.4, 0.0, 0.4):
        for f in (thick / 2.0, -thick / 2.0):
            x = q[0] + t[0] * u * width + n[0] * f
            y = q[1] + t[1] * u * width + n[1] * f
            z = support(group_of(ck), x, y, foot + SUPPORT_UP, {rk})
            g = None if z is None else foot - z
            if g is None:
                return None
            worst = g if worst is None else max(worst, g)
    return worst


LOOSE = ('barricade', 'rubble', 'debris', 'broken', 'heap') + __import__('doorout').CLUTTER


def kind_of(b):
    if b == '(the door not hit)':
        return 'none'
    nm = (name(b)[0] or '').lower()
    if any(w in nm for w in LOOSE) or (nm.endswith('static') and 'door' in nm):
        return 'loose'
    return 'shell'


def why_kept(rk, p, base):
    """Each ref of `base` near the door, and what the pick step's rule kept it for."""
    out = []
    ck = refs[rk][0]
    for ork, orr in P.near(group_of(ck), p[0], p[1]):
        if orr.get('base') != base or ork == rk:
            continue
        reasons = [w for w, c in (('a door', name(base)[1] == 'DOOR'), ('linked', bool(orr.get('tel'))),
                                  ('persistent', bool(orr.get('persistent'))), ('a door leads to it', ork in leads_all),
                                  ('named', bool(orr.get('edid')))) if c]
        out.append({'ref': ork, 'd': round(math.hypot(orr['p'][0] - p[0], orr['p'][1] - p[1])), 'kept for': reasons})
    return sorted(out, key=lambda o: o['d'])[:3]


rows = []
for i, rk in enumerate(LIST):
    if rk not in refs or not leads.get(rk):
        rows.append({'door': rk, 'gone': True})
        continue
    ck, r = refs[rk]
    a = leads[rk][0][2]
    vx, vy = a[0] - r['p'][0], a[1] - r['p'][1]
    ln = math.hypot(vx, vy)
    box = obnd(r['base'])
    if ln < 1 or not box:
        rows.append({'door': rk, 'skipped': 'no bounds or arrival on the door'})
        continue
    out0 = (vx / ln, vy / ln)
    res0 = P.door(rk, out0, box)
    out = res0['normal']
    by_k = [res0['picked']]
    for k in range(1, MOST + 1):
        p = list(r['p'])
        p[0], p[1] = r['p'][0] + out[0] * k, r['p'][1] + out[1] * k
        by_k.append(P.door(rk, out, box, p)['picked'])
    best = max(range(len(by_k)), key=lambda k: (by_k[k], -k))
    pb = list(r['p'])
    pb[0], pb[1] = r['p'][0] + out[0] * best, r['p'][1] + out[1] * best
    g0 = floor_gap(rk, r, box, out, r['p'])
    gb = floor_gap(rk, r, box, out, pb) if best else g0
    kinds = collections.Counter()
    for b, n_ in res0['by'].items():
        kinds[kind_of(b)] += n_
    loose = {name(b)[0] or b: why_kept(rk, r['p'], b) for b in res0['by'] if kind_of(b) == 'loose'}
    rows.append({'door': rk, 'is': name(r['base'])[0], 'base': r['base'], 'cell': ck, 'where': group_of(ck)[0],
                 'spots': res0['spots'], 'picked': by_k, 'best_out': best,
                 'by': {name(b)[0] or b: n_ for b, n_ in res0['by'].items()},
                 'by_base': {b: n_ for b, n_ in res0['by'].items()}, 'kinds': dict(kinds), 'loose': loose,
                 'foot_gap_now': None if g0 is None else round(g0, 1), 'foot_gap_best': None if gb is None else round(gb, 1)})
    if (i + 1) % 50 == 0:
        say('doors', i + 1, 'of', len(LIST))

# --- the game's own: the same door base with the same main blocker, picked by the same rule in the game's own files ---
want = collections.defaultdict(set)
for row in rows:
    if row.get('by_base') and not row['base'].startswith('+'):
        main = max(row['by_base'], key=row['by_base'].get)
        if main != '(the door not hit)' and not main.startswith('+'):
            want[gd.from_key(row['base'])].add(gd.from_key(main))
say('game comparison: door bases', len(want), 'pairs', sum(len(v) for v in want.values()))
door_refs = collections.defaultdict(list)
xtel = {}
cell_of = {}
n_cells = 0
for cell in list(gd.cell_refs):
    try:
        got = gd.refs(cell)
    except Exception:
        continue
    n_cells += 1
    for g in got:
        cell_of[g['ref']] = cell
        if g['leads']:
            try:
                entry = gd.cell_refs.get(cell, {}).get(g['ref'])
                if entry is None:
                    continue
                _i, f = gd.ref_fields(entry)
                d, x, y, z = struct.unpack_from('<I3f', f['XTEL'])
                xtel[g['ref']] = (gd.to_global(_i, d), (x, y, z))
            except Exception:
                pass
        if g['base'] in want and g['pos']:
            door_refs[g['base']].append((cell, g))
say('game cells read', n_cells, 'door refs of those bases', sum(len(v) for v in door_refs.values()))


def game_refs_round(cell):
    """{key: (cell key, ref)} of a game cell and, outside, the eight round it, in the mod's ref form."""
    cells = [cell]
    if cell in gd.ext_cells:
        xy = gd.cell_grid(cell)
        grid = gd.grid(gd.ext_cells[cell])
        cells = [grid[(xy[0] + dx, xy[1] + dy)] for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (xy[0] + dx, xy[1] + dy) in grid]
    out = {}
    for c in cells:
        for g in gd.refs(c):
            if g['pos'] and g['base']:
                out[gd.key(g['ref'])] = (gd.key(c), {'base': gd.key(g['base']), 'p': list(g['pos']) + list(g['rot']),
                                                     's': g['scale']})
    return out


game = {}
for dbase, blockers in want.items():
    for cell, g in door_refs.get(dbase, []):
        if g['ref'] not in xtel:
            continue
        other = xtel[g['ref']][0]
        if other not in xtel:
            continue
        arrive = xtel[other][1]
        grefs = game_refs_round(cell)
        dk = gd.key(g['ref'])
        near_bases = {orr['base'] for ok, (oc, orr) in grefs.items()
                      if abs(orr['p'][0] - g['pos'][0]) < 600 and abs(orr['p'][1] - g['pos'][1]) < 600}
        for bl in blockers:
            pair = (gd.key(dbase), gd.key(bl))
            if pair in game or gd.key(bl) not in near_bases:
                continue
            GP = doorpick.Picker(gd, pr, grefs, model_of, lambda ck: 'g')
            vx, vy = arrive[0] - g['pos'][0], arrive[1] - g['pos'][1]
            ln = math.hypot(vx, vy)
            box = obnd(gd.key(dbase))
            if ln < 1 or not box:
                continue
            res = GP.door(dk, (vx / ln, vy / ln), box)
            game[pair] = {'game_door': dk, 'cell': gd.edid(cell) or gd.key(cell), 'picked': res['picked'], 'spots': res['spots'],
                          'by': {(gd.edid(gd.from_key(b)) if not b.startswith('(') else b): n_ for b, n_ in res['by'].items()}}
say('game pairs picked', len(game), 'of', sum(len(v) for v in want.values()))
for row in rows:
    if row.get('by_base') and not row['base'].startswith('+'):
        main = max(row['by_base'], key=row['by_base'].get)
        row['game'] = game.get((row['base'], main))

# --- summary ---
ok = [r_ for r_ in rows if r_.get('picked')]
full_now = [r_ for r_ in ok if r_['picked'][0] == r_['spots']]
by_class = collections.Counter()
for r_ in ok:
    if r_['picked'][0] == r_['spots']:
        by_class['picked everywhere now'] += 1
        continue
    main = max(r_['kinds'], key=r_['kinds'].get)
    g_ = r_.get('game')
    as_game = g_ is not None and g_['picked'] <= r_['picked'][0]
    better = r_['picked'][r_['best_out']] - r_['picked'][0]
    floats = r_['best_out'] and (r_['foot_gap_best'] is None or r_['foot_gap_best'] > max(r_['foot_gap_now'] or 0, 0) + 2)
    by_class[(main, 'as the game' if as_game else ('game better' if g_ else 'no game copy'),
              'moving helps' if better > 0 else 'moving no help', 'would float' if floats else '')] += 1
say('rows', len(rows), '| picked everywhere now', len(full_now))
for k, v in by_class.most_common():
    say('  ', v, k)
say('spots picked now', sum(r_['picked'][0] for r_ in ok), 'of', sum(r_['spots'] for r_ in ok),
    '| at each door\'s best within %d' % MOST, sum(r_['picked'][r_['best_out']] for r_ in ok))
json.dump({'rows': rows, 'game': {'%s %s' % k: v for k, v in game.items()}}, open(OUT, 'w', encoding='utf-8'), indent=1)
say('report', OUT)
