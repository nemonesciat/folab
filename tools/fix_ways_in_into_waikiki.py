"""fix_ways_in_into_waikiki.py [real] [--home H] [--app A] [--before DIR]: run before cut_doorways_into_waikiki.py on the
Waikiki the 10:06 ways-in run changed. That run told a door's outside by the nearest big static and 4 of its 16 links arrive
facing into their building. Each city door the run linked (told by --before, its backup) is checked against its building's
catalogue box (doorout); one facing in gets its arrival on the true outside if that is on the city's navmesh, else the
doorway goes back as it was (its static again, no link, locked as before), so the next step gives the place a doorway of
its own. One Undo; backup; refuses while the game runs (not on a FOLabScratch home)."""
import json, math, os, shutil, struct, subprocess, sys, time

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


HOME = opt('--home', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
BEFORE = opt('--before', os.path.join(HOME, 'backups', 'Waikiki before ways in 1122-1006'))
STEP = 110.0
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
sys.stdout.reconfigure(encoding='utf-8')
t0 = time.time()
say = lambda *a: print('%5.0fs' % (time.time() - t0), *a, flush=True)
if REAL and 'FOLabScratch' not in HOME:
    running = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    busy = [n for n in ('falloutnv.exe', 'nv-rs.exe', 'nvrs.exe', 'folab.exe', 'modorganizer.exe', 'nvse_loader.exe', 'play.exe', 'geck.exe')
            if n in running]
    if busy:
        sys.exit('not while these run: ' + ', '.join(busy))

import gamedata, project, server, doorswap, doorset, townbuild, restyleset, modelsets  # noqa: E402
sys.path.insert(0, HERE)
import doorout  # noqa: E402
src = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
was = project.modified(src)
say('mod', src, time.strftime('%d %b %H:%M', time.localtime(was)))
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr); server.PR = pr
gd = server.GD
modelsets._all_sets()
name = doorswap.Names(gd, pr)
worlds = {gd.edid(w): w for w in gd.worlds()}
cgrid = gd.grid(worlds[doorset.CITY])
city = {gd.key(c) for c in cgrid.values()}
refs = {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}
before = project.Project(os.path.join(BEFORE, 'Waikiki.json'))
old = {rk: r for c in before.cells.values() for rk, r in (c.get('refs') or {}).items()}
cat = townbuild.load(gd, server.kits_folder())
boxes = {b['key']: b['box'] for b in cat}
byedid = {b['edid']: b for b in cat}
for g, piece in restyleset.REPLACES.items():
    k = modelsets.record_of(pr, piece)
    if k and g in byedid:
        boxes[k] = byedid[g]['box']
BLD = doorout.Buildings(refs, None, name, city, boxes=boxes)


def obnd(base):
    try:
        if base.startswith('+'):
            s = next(x for x in pr.records[base]['subs'] if x['tag'] == 'OBND')
            return [int(f['value']) for f in s['fields'] if 'name' in f]
        return list(struct.unpack('<6h', gd.fields(gd.from_key(base))['OBND'][:12]))
    except Exception:
        return [-60, -10, 0, 60, 10, 200]


def city_cell(x, y):
    c = cgrid.get((int(x // 4096), int(y // 4096)))
    return gd.key(c) if c is not None else None


def on_navmesh(ck, x, y, z):
    m = pr.navmesh.get(ck)
    if not m:
        return False
    vs = m['verts']
    for t in m['tris']:
        a, b, c = (vs[i] for i in t[:3])
        if abs((a[2] + b[2] + c[2]) / 3.0 - z) > 120:
            continue
        def s(p, q, r_): return (p[0] - r_[0]) * (q[1] - r_[1]) - (q[0] - r_[0]) * (p[1] - r_[1])
        d = (s((x, y), a, b), s((x, y), b, c), s((x, y), c, a))
        if not (min(d) < 0 < max(d)):
            return True
    return False


ops, report = [], []
for rk, (ck, r) in refs.items():
    if ck not in city or not r.get('tel') or (old.get(rk) or {}).get('tel') == r['tel']:
        continue                                        # (only the city doors the 10:06 run linked)
    place_door = r['tel']['door']
    pck, pr_ = refs[place_door]
    out_p = (pr_.get('tel') or {}).get('p')
    b = obnd(r['base'])
    s = float(r.get('s') or 1.0)
    rz = r['p'][5]
    c, sn = math.cos(rz), math.sin(rz)
    lx, ly = (1.0, 0.0) if (b[3] - b[0]) < (b[4] - b[1]) else (0.0, 1.0)
    nx, ny = lx * c + ly * sn, -lx * sn + ly * c
    sg = BLD.outward(r['p'], (nx, ny))
    if sg is None or not out_p:
        continue
    now = 1 if (out_p[0] - r['p'][0]) * nx + (out_p[1] - r['p'][1]) * ny >= 0 else -1
    if now == sg:
        continue                                        # (faces out already)
    foot = r['p'][2] + b[2] * s
    new = None
    for step in (STEP, 150.0, 200.0, 260.0):
        x, y = r['p'][0] + sg * nx * step, r['p'][1] + sg * ny * step
        if on_navmesh(city_cell(x, y), x, y, foot):
            new = [round(x, 2), round(y, 2), round(foot + 8.0, 2), 0.0, 0.0, round(math.atan2(sg * nx, sg * ny) % math.tau, 4)]
            break
    if new:
        ops.append({'op': 'tel', 'cell': pck, 'ref': place_door, 'tel': dict(pr_['tel'], p=new)})
        report.append({'door': rk, 'is': name(r['base'])[0], 'place_door': place_door, 'did': 'arrival moved outside'})
    else:
        o = old.get(rk) or {}
        ops.append({'op': 'tel', 'cell': ck, 'ref': rk, 'tel': None})
        if o.get('base') and o['base'] != r['base']:
            ops.append({'op': 'swap', 'cell': ck, 'ref': rk, 'base': o['base']})
        if (o.get('props') or {}).get('lock'):
            ops.append({'op': 'props', 'cell': ck, 'ref': rk, 'props': {'lock': o['props']['lock']}})
        ops.append({'op': 'tel', 'cell': pck, 'ref': place_door, 'tel': dict(pr_['tel'], door=(old.get(place_door) or {}).get('tel', {}).get('door', pr_['tel']['door']),
                                                                       p=(old.get(place_door) or {}).get('tel', {}).get('p', pr_['tel']['p']))})
        report.append({'door': rk, 'is': name(r['base'])[0], 'place_door': place_door, 'did': 'doorway put back: no navmesh on its outside'})
say('links facing into their building', len(report), json.dumps(report))
if not ops:
    sys.exit('nothing to fix: run already?')
if len(report) > 8:
    sys.exit('more to fix than the check found (4): stopping')
if not REAL:
    say('dry run: nothing saved')
    sys.exit(0)
if project.modified(src) != was:
    sys.exit('Waikiki changed while this ran: stopping')
back = os.path.join(HOME, 'backups', 'Waikiki before ways in fixed %s' % time.strftime('%m%d-%H%M'))
os.makedirs(back)
for f in (src, os.path.splitext(src)[0] + '.changes'):
    if os.path.isfile(f):
        shutil.copy2(f, back)
say('backup', back)
pr.apply('Ways in from the city: arrivals facing out', ops)
say('applied and saved')
refs = {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}
bad = [x['door'] for x in report if x['did'].startswith('arrival') and not (refs[x['place_door']][1].get('tel') or {}).get('p')]
same = doorswap.same_arrivals(pr)
say('CHECKS: ' + ('all good' if not bad and not same else 'PROBLEMS: %s %s' % (bad, same)))
