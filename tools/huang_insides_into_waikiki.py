"""huang_insides_into_waikiki.py [real] [--home H] [--app A]: the Huáng's halls opened in Waikiki (huanginside.py).

One Undo, "The Huáng's halls opened": the six settlerset halls swapped for huangset's (a doorway where the door was
painted), a door on each, six places behind them (the elders' hall, four homes, the granary), furnished and lit, linked
both ways; each place's navmesh; then the three outside cells the halls stand in made again (their navmeshes link the
new doors), merged into the same Undo. Then every outside door is checked as the doors session's doorray does: rays from
80 out at eye height over its face, each must meet the door first.

Without `real` it rehearses on a copy (json, journal, source, assets) in D:\\FOLabScratch\\huang\\home. `real`: game,
FOLab, MO2, GECK and nv-rs closed; the mod backed up first. Run with the main checkout's app (it reads Waikiki.changes);
huangset/huanginside come from this file's checkout unless the app has them."""
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import time

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


REAL_HOME = r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab'
SCRATCH = r'D:\FOLabScratch\huang\home'
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
MINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
DOORRAY = opt('--doorray', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\.claude\worktrees\zealous-rosalind-5e1645\tools')
LABEL = 'The Huáng\'s halls opened'
HOME = opt('--home', REAL_HOME if REAL else SCRATCH)
t0 = time.time()
sys.stdout.reconfigure(encoding='utf-8')
say = lambda *a: print('%5.0fs' % (time.time() - t0), *a, flush=True)

if REAL:
    running = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    busy = [n for n in ('falloutnv.exe', 'folab.exe', 'play.exe', 'modorganizer.exe', 'geck.exe', 'nvse_loader.exe') if n in running]
    if busy:
        sys.exit('not while these run: ' + ', '.join(busy))
elif HOME == SCRATCH:
    src = os.path.join(REAL_HOME, 'projects')
    dst = os.path.join(SCRATCH, 'projects')
    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH)
    os.makedirs(dst)
    for n in os.listdir(src):
        if n.startswith('Waikiki.') and os.path.isfile(os.path.join(src, n)):
            shutil.copy2(os.path.join(src, n), os.path.join(dst, n))
    for d in ('Waikiki source', 'Waikiki assets'):
        subprocess.run(['robocopy', os.path.join(src, d), os.path.join(dst, d), '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/MT:16'], capture_output=True)
    say('copied Waikiki (json, journal, source, assets) into', SCRATCH)

os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path[:0] = [APP]
sys.path.append(MINE)
sys.path.append(DOORRAY)
# (navgen and navbuild from this checkout unless the app has the fix: a door of the mod's own gets its navmesh link)
import importlib.util  # noqa: E402
for _m in ('navgen', 'navbuild'):
    if "r.get('door')" not in open(os.path.join(APP, _m + '.py'), encoding='utf-8').read() and _m == 'navgen' or \
            "row['door'] = True" not in open(os.path.join(APP, _m + '.py'), encoding='utf-8').read() and _m == 'navbuild':
        _spec = importlib.util.spec_from_file_location(_m, os.path.join(MINE, _m + '.py'))
        sys.modules[_m] = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(sys.modules[_m])
        say('using this checkout\'s', _m)
import gamedata, project, server, navbuild, recordio  # noqa: E402
import huangset as HS, huanginside as HI  # noqa: E402
import doorray  # noqa: E402

mod = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
seen = os.path.getmtime(mod)
if REAL:
    back = os.path.join(HOME, 'backups', 'Waikiki before huang insides ' + time.strftime('%m%d-%H%M'))
    os.makedirs(back)
    for n in os.listdir(project.PROJECTS_DIR):
        if n.startswith('Waikiki.') and os.path.isfile(os.path.join(project.PROJECTS_DIR, n)):
            shutil.copy2(os.path.join(project.PROJECTS_DIR, n), os.path.join(back, n))
    say('backup', back)
server.not_while_playing = lambda: None
server.GD = gamedata.GameData()
server.BR = None
pr = project.Project.open('Waikiki')
server.load_game(pr)
server.PR = pr
gd = server.GD
say('loaded')

ops, rep = HI.ops(gd, pr)
say('ops', len(ops), 'places', [(p['edid'], p['role'], p['hall']) for p in rep['places']])
if os.path.getmtime(mod) != seen:
    sys.exit('Waikiki.json changed while loading: nothing written')
pr.apply(LABEL, ops)
names = dict(pr.names)
tags = [p['tag'] for p in rep['places']]
nav, nrep = HI.navmesh_ops(gd, pr, names, tags)
for t in tags:
    r = nrep.get(t)
    say('navmesh', t, r if isinstance(r, str) else {k: r[k] for k in r if k in ('triangles', 'doors', 'linked', 'missed', 'seconds') and not isinstance(r[k], (list, dict))} if isinstance(r, dict) else r)
pr.apply(LABEL, nav, merge=True)
cells = sorted({p['cell'] for p in rep['places']})
aops, arep = navbuild.generate_area(gd, pr, cells)
say('outside navmeshes', cells, {k: arep[k] for k in ('cells', 'triangles', 'doors', 'doors_missed', 'neighbours')})
pr.apply(LABEL, aops, merge=True)
pops, prep = HI.people_ops(gd, pr)
pr.apply(LABEL, pops, merge=True)
say('who lives there', prep['housed'], 'skipped', prep['skipped'])

# each outside door: can the player use it?
refs = {rk: (ck, r) for ck, c in pr.cells.items() for rk, r in (c.get('refs') or {}).items() if not r.get('removed')}


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


R = doorray.Rays(gd, pr, {k: v for k, v in refs.items() if not v[0].startswith('+')}, model_of)
door_key = names.get('huang_huang_door') or HI._mine(pr, 'FOLabHuangDoor', 'DOOR')
db = [int(f['value']) for f in next(s for s in pr.records[door_key]['subs'] if s['tag'] == 'OBND')['fields'] if 'name' in f]
rays = {}
for p in rep['places']:
    rk = names[p['tag'] + 'o']
    rz = p['door'][5]
    out = (-math.sin(rz), -math.cos(rz))
    rays[p['edid']] = R.door(rk, out, db)
    say('door', p['edid'], '%d of %d rays' % (rays[p['edid']]['hits'], rays[p['edid']]['rays']), rays[p['edid']]['blocked_by'] or '')
pr.save()
say('saved')
ok = (all(r['hits'] == r['rays'] for r in rays.values()) and all(isinstance(nrep.get(t), dict) and nrep[t].get('doors') == 1 for t in tags)
      and arep.get('doors', 0) >= len(tags) and not arep.get('doors_missed') and not prep['skipped'])
json.dump({'places': rep['places'], 'names': {t: names.get(t) for t in tags}, 'rays': rays,
           'navmesh': {t: (nrep[t] if isinstance(nrep.get(t), str) else 'made') for t in tags}, 'outside': arep.get('cells')},
          open(os.path.join(HOME, 'huang_insides_report.json'), 'w'), indent=1, default=str)
say('CHECKS: all good' if ok else 'CHECKS FAILED', '; one Undo: "%s"' % LABEL)
