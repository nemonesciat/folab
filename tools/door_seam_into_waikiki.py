"""door_seam_into_waikiki.py [real] [--home H] [--app A]: the pairs of leaves of FOLab's hotel doors (the Royal Hawaiian's,
the Kilauea's) meet with no gap (the Workshop, 23 Nov 2026: close the seam in doorset). doorset made each leaf a unit
narrower than its half, so a pair showed a 1-unit seam down the middle where the crosshair found nothing (hoteldoors.py:
50 of 50 off the seam, not on it). Now `_leaf_spans`: half a unit clear of the frame, the pair touching.

The door pieces' files are made again with --app (the main checkout's, which built the installed doors) and --doorset (doorswap.refit_ops: only files that differ are written,
records' bounds refit where they changed). doorpick before and after over a strip 12 wide down the middle of every pair
door something leads to (5 x 5 spots from 60 out, at eye height and 1.2 m). No ref moves, no navmesh changes. One Undo
if a record changes; no backup (the install makes the one); refuses while the game runs (not on a FOLabScratch home).
Dry run without `real`: the check before and the files it would write."""
import math, os, subprocess, sys, time

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


HOME = opt('--home', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')     # (the main checkout: what built the installed doors)
DOORSET = opt('--doorset', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\.claude\worktrees\zealous-rosalind-5e1645\app\doorset.py')
HERE = os.path.dirname(os.path.abspath(__file__))
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
import importlib.util  # noqa: E402
import modelsets  # noqa: E402,F401
# (the seam branch's doorset in place of the app's: with the main checkout's app it changes only the two pair doors)
_spec = importlib.util.spec_from_file_location('doorset', DOORSET)
doorset = importlib.util.module_from_spec(_spec)
sys.modules['doorset'] = doorset
_spec.loader.exec_module(doorset)
import gamedata, project, server, doorswap, recordio  # noqa: E402
import doorpick  # noqa: E402
if not hasattr(doorset, '_leaf_spans'):
    sys.exit(DOORSET + ' has no _leaf_spans: the branch with the seam closed is wanted')
src = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
was = project.modified(src)
say('mod', src, time.strftime('%d %b %H:%M', time.localtime(was)))
server.not_while_playing = lambda: None
server.GD = gamedata.GameData(); server.BR = None
pr = project.Project.open('Waikiki'); server.load_game(pr); server.PR = pr
gd = server.GD
name = doorswap.Names(gd, pr)
PAIRS = {'FOLabDoorRoyalHawaiian': (3.0, 314.0), 'FOLabDoorKilauea': (3.0, 250.0)}     # (the leaves' height in the piece's frame)


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


_g = {}


def group_of(c):
    if c not in _g:
        try:
            w = gd.ext_cells.get(gd.from_key(c))
        except Exception:
            w = None
        _g[c] = ('world', w) if w is not None else ('place', c)
    return _g[c]


def check(label):
    refs = {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}
    P = doorpick.Picker(gd, pr, refs, model_of, group_of)
    doors = full = spots = picked = 0
    for rk, (ck, r) in sorted(refs.items()):
        e = name(r.get('base') or '')[0]
        if e not in PAIRS:
            continue
        lead = [x['tel']['p'] for k, (c, x) in refs.items() if (x.get('tel') or {}).get('door') == rk and x['tel'].get('p')]
        if not lead:
            continue
        a = lead[0]
        vx, vy = a[0] - r['p'][0], a[1] - r['p'][1]
        ln = math.hypot(vx, vy) or 1.0
        z0, z1 = PAIRS[e]
        res = P.door(rk, (vx / ln, vy / ln), [-6, -6, z0, 6, -1, z1])
        doors += 1
        full += res['picked'] == res['spots']
        spots += res['spots']
        picked += res['picked']
    say('%s: pair doors picked at every spot down the seam %d of %d; spots %d of %d' % (label, full, doors, picked, spots))
    return full, doors, picked, spots


before = check('before')
refit, files = doorswap.refit_ops(gd, pr, write=False)
say('files that differ', files, '| records refit', [o['key'] for o in refit])
if not REAL:
    say('dry run: nothing written')
    sys.exit(0)
if project.modified(src) != was:
    sys.exit('Waikiki changed while this ran: stopping')
refit, files = doorswap.refit_ops(gd, pr, write=True)
if refit:
    pr.apply("FOLab's hotel doors: the pair of leaves meeting with no seam", refit)
say('written', len(files), 'files; records refit', len(refit))
after = check('after, from the written files')
bad = []
if any(not f.lower().endswith(('door_royal_hawaiian.nif', 'door_kilauea.nif')) for f in files):
    bad.append('files other than the two pair doors changed: %s (another app than the one that built them?)' % files)
if after[0] < after[1]:
    bad.append('%d of %d pair doors still miss on the seam' % (after[1] - after[0], after[1]))
say('CHECKS: ' + ('all good' if not bad else 'PROBLEMS: ' + '; '.join(bad)))
