"""door_pick_into_waikiki.py [real] [--home H] [--app A] [--doorset F]: every door one can open from the middle of its leaf.
The user, 22-23 Nov 2026 (in nv-rs): FOLab's doors answer only at their edge. nv-rs picks a door by its drawn triangles and
a building by its collision, the nearer wins (doorpick.py's docstring), and the game's buildings close their doorways in
collision at the wall's face, so a leaf set in the hole lost to the wall everywhere but its liners.

1. FOLab's hole doors made again with their leaves in front of the wall's face (doorset.LEAF_Y, from --doorset: the doors
   branch's doorset.py), their files and records' bounds written (doorswap.refit_ops).
2. doorpick over every door something leads to, outside and in places: 5 x 5 spots over the leaf from 60 out, at eye height
   and at 1.2 m.
3. What stands loose in front (barricades, rubble, clutter) taken away; a door still not picked at every spot moved out
   from its wall STEP at a time, at most MOST (6: further it would float), until it is (links kept; an
   arrival it came too close to put in front of it again). Touched cells' navmeshes made again.
4. doorpick again over the saved mod. One Undo; backup; refuses while the game runs (not on a FOLabScratch home).
Dry run without `real`: the check before, and what step 1 would write."""
import collections, importlib.util, json, math, os, shutil, struct, subprocess, sys, time

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


HOME = opt('--home', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
DOORSET = opt('--doorset', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\.claude\worktrees\zealous-rosalind-5e1645\app\doorset.py')
HERE = os.path.dirname(os.path.abspath(__file__))
STEP, MOST, ARRIVE_CLEAR = 1.0, 6.0, 70.0     # (no further: a door off its wall floats, the user won't have it)
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8')
t0 = time.time()
say = lambda *a: print('%5.0fs' % (time.time() - t0), *a, flush=True)
if REAL and 'FOLabScratch' not in HOME:
    running = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    busy = [n for n in ('falloutnv.exe', 'nv-rs.exe', 'nvrs.exe', 'folab.exe', 'modorganizer.exe', 'nvse_loader.exe', 'play.exe', 'geck.exe')
            if n in running]
    if busy:
        sys.exit('not while these run: ' + ', '.join(busy))
# the doors branch's doorset (leaves in front of the wall) in place of the app's
spec = importlib.util.spec_from_file_location('doorset', DOORSET)
_ds = importlib.util.module_from_spec(spec)
sys.modules['doorset'] = _ds
spec.loader.exec_module(_ds)
if not hasattr(_ds, 'LEAF_Y'):
    sys.exit(DOORSET + ' has no LEAF_Y: the doors branch\'s doorset.py is wanted')

import gamedata, project, server, doorswap, recordio, navbuild  # noqa: E402
import doorpick  # noqa: E402
src = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
was = project.modified(src)
say('mod', src, time.strftime('%d %b %H:%M', time.localtime(was)), '| doorset', DOORSET, 'LEAF_Y', _ds.LEAF_Y)
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr); server.PR = pr
gd = server.GD
name = doorswap.Names(gd, pr)


def all_refs():
    return {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}


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


_g = {}


def group_of(ck):
    if ck not in _g:
        try:
            w = gd.ext_cells.get(gd.from_key(ck))
        except Exception:
            w = None
        _g[ck] = ('world', w) if w is not None else ('place', ck)
    return _g[ck]



def on_navmesh(ck, x, y, z):
    m = pr.navmesh.get(ck)
    if not m:
        return False
    vs = m['verts']
    for t in m['tris']:
        a, b, c = (vs[i] for i in t[:3])
        if abs((a[2] + b[2] + c[2]) / 3.0 - z) > 120:
            continue
        def s_(p1, q1, r1): return (p1[0] - r1[0]) * (q1[1] - r1[1]) - (q1[0] - r1[0]) * (p1[1] - r1[1])
        d = (s_((x, y), a, b), s_((x, y), b, c), s_((x, y), c, a))
        if not (min(d) < 0 < max(d)):
            return True
    return False


def cell_at(ck, x, y):
    """The cell a spot is in: an outside cell's world grid, or the place itself."""
    g = group_of(ck)
    if g[0] != 'world':
        return ck
    c = gd.grid(g[1]).get((int(x // 4096), int(y // 4096)))
    return gd.key(c) if c is not None else ck


def check(refs, label):
    leads = {}
    for rk, (ck, r) in refs.items():
        t = r.get('tel') or {}
        if t.get('door') and t.get('p'):
            leads.setdefault(t['door'], []).append((ck, rk, t['p']))
    P = doorpick.Picker(gd, pr, refs, model_of, group_of)
    out = {}
    for rk in leads:
        if rk not in refs or name(refs[rk][1].get('base') or '')[1] != 'DOOR':
            continue
        ck, r = refs[rk]
        a = leads[rk][0][2]
        vx, vy = a[0] - r['p'][0], a[1] - r['p'][1]
        ln = math.hypot(vx, vy)
        box = obnd(r['base'])
        if ln < 1 or not box or not any(box):
            continue
        res = P.door(rk, (vx / ln, vy / ln), box)
        out[rk] = dict(res, out=res['normal'], box=box, leads=leads[rk])     # (moved along its own facing)
    full = sum(1 for v in out.values() if v['picked'] == v['spots'])
    say('%s: doors %d, picked at every spot %d, some %d, none %d, spots %d of %d' % (
        label, len(out), full, sum(1 for v in out.values() if 0 < v['picked'] < v['spots']),
        sum(1 for v in out.values() if v['picked'] == 0), sum(v['picked'] for v in out.values()), sum(v['spots'] for v in out.values())))
    return out, P


refs = all_refs()
before, _P = check(refs, 'before')
# whoever arrives on the navmesh before the step must still after it (49 arrivals were off it before: not this step's)
was_on = set()
for rk_, v_ in before.items():
    for ack, ark, a in v_['leads']:
        if on_navmesh(cell_at(refs[rk_][0], a[0], a[1]), a[0], a[1], a[2] - 8):
            was_on.add(ark)
refit, files = doorswap.refit_ops(gd, pr, write=REAL)
say('door models written again', files, '| records refit', [o['key'] for o in refit])
if not REAL:
    say('dry run: nothing saved')
    sys.exit(0)
if project.modified(src) != was:
    sys.exit('Waikiki changed while this ran: stopping')
back = os.path.join(HOME, 'backups', 'Waikiki before door pick %s' % time.strftime('%m%d-%H%M'))
os.makedirs(back)
for f in (src, os.path.splitext(src)[0] + '.changes'):
    if os.path.isfile(f):
        shutil.copy2(f, back)
say('backup', back)
label = 'Doors one opens from the middle of the leaf'
if refit:
    pr.apply(label, refit)
merged = bool(refit)
refs = all_refs()
mid, P = check(refs, 'with the doors made again')
ops, moved, gone, cleared = [], [], set(), []
leads_all = {r_.get('tel', {}).get('door') for _c, r_ in refs.values() if r_.get('tel')}
LOOSE = ('barricade', 'rubble', 'debris', 'broken', 'heap') + __import__('doorout').CLUTTER
for rk, v in mid.items():
    if v['picked'] == v['spots']:
        continue
    ck, r = refs[rk]
    out = v['out']
    k, res, p = 0.0, v, list(r['p'])
    for _round in range(200):
        if res['picked'] == res['spots']:
            break
        # what stands in front and is loose (a barricade, rubble, clutter, a door's static twin) is taken away first
        loose = [b for b in res['by'] if b != '(the door not hit)' and (any(w in (name(b)[0] or '').lower() for w in LOOSE)
                 or ((name(b)[0] or '').lower().endswith('static') and 'door' in (name(b)[0] or '').lower()))]
        took = False
        for ork, orr in list(P.near(group_of(ck), p[0], p[1])):
            if ork == rk or ork in gone or orr.get('base') not in loose:
                continue
            if name(orr['base'])[1] == 'DOOR' or orr.get('tel') or orr.get('persistent') or ork in leads_all:
                continue                                 # (never a door or anything something names: 'lamp' took a LamplightSouvDoor)
            dx, dy = orr['p'][0] - p[0], orr['p'][1] - p[1]
            along, across = dx * out[0] + dy * out[1], abs(-dx * out[1] + dy * out[0])
            reach = 320 if any(w in (name(orr['base'])[0] or '').lower() for w in ('rubble', 'heap')) else 160
            if -40 <= along <= reach and across <= reach:
                gone.add(ork)
                ops.append({'op': 'remove', 'cell': refs[ork][0], 'ref': ork})
                cleared.append(name(orr['base'])[0])
                lst = P.grid.get((group_of(refs[ork][0]), int(orr['p'][0] // 1024), int(orr['p'][1] // 1024)), [])
                if ork in lst:
                    lst.remove(ork)
                took = True
        if took:
            res = P.door(rk, out, v['box'], p)
            continue
        if k >= MOST:
            break
        k += STEP
        p = list(r['p'])
        p[0], p[1] = round(r['p'][0] + out[0] * k, 2), round(r['p'][1] + out[1] * k, 2)
        res = P.door(rk, out, v['box'], p)
    if res['picked'] < res['spots']:
        moved.append({'door': rk, 'is': name(r['base'])[0], 'cell': ck, 'out': None, 'picked': '%d/%d' % (res['picked'], res['spots']),
                      'by': {name(b)[0] or b: n for b, n in res['by'].items()}})
        continue
    if k == 0:
        moved.append({'door': rk, 'is': name(r['base'])[0], 'cell': ck, 'out': 0.0})
        continue
    ops.append({'op': 'move', 'cell': ck, 'ref': rk, 'p': p})
    for ack, ark, a in v['leads']:
        if (a[0] - p[0]) * out[0] + (a[1] - p[1]) * out[1] < ARRIVE_CLEAR:
            na = list(a)
            na[0], na[1] = round(p[0] + out[0] * (ARRIVE_CLEAR + 40), 2), round(p[1] + out[1] * (ARRIVE_CLEAR + 40), 2)
            if on_navmesh(cell_at(ck, na[0], na[1]), na[0], na[1], na[2] - 8) or not on_navmesh(cell_at(ck, a[0], a[1]), a[0], a[1], a[2] - 8):
                ops.append({'op': 'tel', 'cell': ack, 'ref': ark, 'tel': dict(refs[ark][1]['tel'], p=na)})      # (never off the navmesh if it was on)
    moved.append({'door': rk, 'is': name(r['base'])[0], 'cell': ck, 'out': k})
say('loose things taken away', len(cleared), collections.Counter(cleared).most_common(8))
say('moved out', sum(1 for m in moved if m['out']), '| most %.0f' % max([m['out'] or 0 for m in moved] or [0]),
    '| no good within %d: %d' % (MOST, sum(1 for m in moved if m['out'] is None)))
for m in moved:
    if m['out'] is None:
        say('   not fixed', m)
if ops:
    pr.apply(label, ops, merge=merged)
    merged = True
say('applied and saved')
cells = sorted({m['cell'] for m in moved if m['out'] is not None} | {refs[g][0] for g in gone if g in refs})
outside = [c for c in cells if group_of(c)[0] == 'world']
places = [c for c in cells if group_of(c)[0] == 'place']
if outside:
    t1 = time.time()
    nops, nrep = navbuild.generate_area(gd, pr, outside)
    pr.apply(label, nops, merge=merged)
    merged = True
    say('outside navmeshes made again: %d cells in %.0fs' % (len(outside), time.time() - t1), {k: nrep.get(k) for k in ('cells', 'doors', 'doors_missed', 'neighbours')})
pops = []
for c in places:
    try:
        data, words = navbuild.generate(gd, pr, c)
        pops.append({'op': 'navmesh', 'cell': c, 'mesh': data})
    except Exception as e:
        say('   place navmesh not made', c, e)
if pops:
    pr.apply(label, pops, merge=merged)
    say('places\' navmeshes made again', len(pops))
refs = all_refs()
after, _P = check(refs, 'after, from the saved mod')
bad = [rk for rk, v in after.items() if v['picked'] < v['spots']]
# every moved door: its link both ways and whoever arrives by it on the navmesh
off_mesh, one_way = [], []
for m in moved:
    if not m['out']:
        continue
    rk = m['door']
    ck, r = refs[rk]
    t = r.get('tel') or {}
    if t.get('door') in refs and (refs[t['door']][1].get('tel') or {}).get('door') != rk:
        one_way.append(rk)
    for ock, ork, orr in [(c_, k_, x_) for k_, (c_, x_) in refs.items() if (x_.get('tel') or {}).get('door') == rk]:
        a = orr['tel']['p']
        if not on_navmesh(cell_at(ck, a[0], a[1]), a[0], a[1], a[2] - 8) and ork in was_on:
            off_mesh.append((rk, ork))
say('moved doors: %d, largest move %.0f, arrivals off the navmesh %d, links one way %d' % (
    sum(1 for m in moved if m['out']), max([m['out'] or 0 for m in moved] or [0]), len(off_mesh), len(one_way)))
for rk, v in sorted(after.items(), key=lambda kv: kv[1]['picked'] - kv[1]['spots']):
    if v['picked'] < v['spots']:
        say('   still not picked everywhere:', rk, name(refs[rk][1]['base'])[0], refs[rk][0], '%d/%d' % (v['picked'], v['spots']),
            {name(b)[0] or b: n for b, n in v['by'].items()})
same = doorswap.same_arrivals(pr)
json.dump({'before': {k: {'picked': v['picked'], 'spots': v['spots']} for k, v in before.items()},
           'after': {k: {'picked': v['picked'], 'spots': v['spots'], 'by': {name(b)[0] or b: n for b, n in v['by'].items()}} for k, v in after.items()},
           'moved': moved}, open(os.path.join(HERE, 'door_pick_report.json'), 'w'), indent=1)
say('CHECKS: ' + ('all good' if not bad and not same and not off_mesh and not one_way else 'PROBLEMS: %d doors not picked everywhere %s %s' % (len(bad), bad[:20], same or '')))
