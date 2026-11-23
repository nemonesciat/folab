"""bars_into_waikiki.py [real] [--home H] [--app A]: the DoorBarricades still standing in front of doors something leads to
taken away (after door_pick_into_waikiki.py: 17 in the city, 60 to 300 out, some to the side). A bar counts when it stands
in front of the door (along its face from -40 to REACH, within ACROSS to the side), in the same world or place, and nothing
names it. doorpick before and after over the doors they stood at. One Undo; backup; refuses while the game runs (not on a
FOLabScratch home). Dry run without `real`."""
import math, os, shutil, struct, subprocess, sys, time

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


HOME = opt('--home', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
HERE = os.path.dirname(os.path.abspath(__file__))
REACH, ACROSS = 320.0, 200.0
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
import gamedata, project, server, doorswap, recordio  # noqa: E402
import doorpick  # noqa: E402
src = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
was = project.modified(src)
say('mod', src, time.strftime('%d %b %H:%M', time.localtime(was)))
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr); server.PR = pr
gd = server.GD
name = doorswap.Names(gd, pr)


def all_refs():
    return {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items()
            if not r.get('removed') and r.get('p') and r['p'][2] > -20000}


def model_of(b):
    try:
        if b.startswith('+'):
            rr = pr.records.get(b)
            mm = recordio.field(rr, 'MODL') if rr else None
            return ('meshes' + chr(92) + mm) if mm else None
        t, e, f, mm = gd.describe(gd.from_key(b))
        return gd.model_path(t, mm) if mm else None
    except Exception:
        return None


def obnd(b):
    try:
        if b.startswith('+'):
            s = next(x for x in pr.records[b]['subs'] if x['tag'] == 'OBND')
            return [int(f['value']) for f in s['fields'] if 'name' in f]
        return list(struct.unpack('<6h', gd.fields(gd.from_key(b))['OBND'][:12]))
    except Exception:
        return None


_g = {}


def group_of(c):
    if c not in _g:
        try:
            w = gd.ext_cells.get(gd.from_key(c))
        except Exception:
            w = None
        _g[c] = ('world', w) if w is not None else ('place', c)
    return _g[c]


refs = all_refs()
leads = {}
for rk, (ck, r) in refs.items():
    t = r.get('tel') or {}
    if t.get('door') and t.get('p'):
        leads.setdefault(t['door'], []).append(t['p'])
named = set(leads)
bars = [(rk, ck, r) for rk, (ck, r) in refs.items() if name(r.get('base') or '')[0] == 'DoorBarricade'
        and not r.get('tel') and not r.get('persistent') and rk not in named]
grid = {}
for b in bars:
    grid.setdefault((group_of(b[1]), int(b[2]['p'][0] // 512), int(b[2]['p'][1] // 512)), []).append(b)
gone, at = {}, {}
for d, arr in leads.items():
    if d not in refs or name(refs[d][1].get('base') or '')[1] != 'DOOR':
        continue
    ck, r = refs[d]
    a = arr[0]
    vx, vy = a[0] - r['p'][0], a[1] - r['p'][1]
    ln = math.hypot(vx, vy)
    if ln < 1:
        continue
    ox, oy = vx / ln, vy / ln
    g = group_of(ck)
    for gx in (-1, 0, 1):
        for gy in (-1, 0, 1):
            for brk, bck, br in grid.get((g, int(r['p'][0] // 512) + gx, int(r['p'][1] // 512) + gy), ()):
                dx, dy = br['p'][0] - r['p'][0], br['p'][1] - r['p'][1]
                along, across = dx * ox + dy * oy, abs(-dx * oy + dy * ox)
                if -40 <= along <= REACH and across <= ACROSS:
                    gone[brk] = bck
                    at.setdefault(d, (ox, oy))
say('DoorBarricades in front of doors something leads to:', len(gone), '| at doors', len(at))


def picks(refs_now, label):
    P = doorpick.Picker(gd, pr, refs_now, model_of, group_of)
    full = sp = pk = 0
    for d, out in at.items():
        res = P.door(d, out, obnd(refs_now[d][1]['base']))
        full += res['picked'] == res['spots']
        sp += res['spots']
        pk += res['picked']
    say('%s: %d of %d doors picked at every spot, spots %d of %d' % (label, full, len(at), pk, sp))
    return full


before = picks(refs, 'before')
if not gone:
    sys.exit('nothing to do: run already?')
if not REAL:
    say('dry run: nothing saved')
    sys.exit(0)
if project.modified(src) != was:
    sys.exit('Waikiki changed while this ran: stopping')
back = os.path.join(HOME, 'backups', 'Waikiki before bars %s' % time.strftime('%m%d-%H%M'))
os.makedirs(back)
for f in (src, os.path.splitext(src)[0] + '.changes'):
    if os.path.isfile(f):
        shutil.copy2(f, back)
say('backup', back)
pr.apply('DoorBarricades out of the way of doors one goes through', [{'op': 'remove', 'cell': c, 'ref': k} for k, c in gone.items()])
say('applied and saved')
after = picks(all_refs(), 'after, from the saved mod')
say('CHECKS: ' + ('all good' if after >= before else 'PROBLEMS: fewer doors picked than before'))
