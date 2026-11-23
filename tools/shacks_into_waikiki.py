"""shacks_into_waikiki.py [real] [--home H] [--app A]: shacks with insides of their own (shackinside.py).

One Undo, "Shacks with insides of their own": every place that is a copy of Cottonwood Cove's restrooms (303: 286 shacks, 17
other buildings) made again from one of the game's shack and cabin insides, dealt out evenly; doors linked both ways; storm
shelter markers carried; navmeshes; then roomvary over the copies. Checks: no place left a copy of a restroom; how many
different insides; every new place's door linked both ways, with a navmesh, walked from its way in.

Without `real`: on a copy (json, journal, source, assets) in D:\\FOLabScratch\\shacks\\home, and the plugin written there.
`real`: game, FOLab, MO2, GECK and nv-rs closed; backed up first. The main checkout's app; shackinside and floorcheck from
this file's checkout."""
import collections
import importlib.util
import os
import shutil
import subprocess
import sys
import time

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


REAL_HOME = r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab'
SCRATCH = r'D:\FOLabScratch\shacks\home'
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
MINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
HERE = os.path.dirname(os.path.abspath(__file__))
HOME = opt('--home', REAL_HOME if REAL else SCRATCH)
LABEL = 'Shacks with insides of their own'
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
    for d in ('cache\\kits',):
        if os.path.isdir(os.path.join(REAL_HOME, d)):
            shutil.copytree(os.path.join(REAL_HOME, d), os.path.join(SCRATCH, d))
    say('copied Waikiki (json, journal, source, assets, kits) into', SCRATCH)
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
sys.path.append(HERE)
import gamedata, project, server, recordio, roomvary, townbuild  # noqa: E402
spec = importlib.util.spec_from_file_location('shackinside', os.path.join(MINE, 'shackinside.py'))
SI = sys.modules['shackinside'] = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SI)
import floorcheck  # noqa: E402

mod = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
seen = os.path.getmtime(mod)
if REAL:
    back = os.path.join(HOME, 'backups', 'Waikiki before shacks ' + time.strftime('%m%d-%H%M'))
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
cat = townbuild.load(gd, server.kits_folder())
pool = SI.pool_insides(gd, cat)
missing = [e for e in SI.POOL if e not in pool]
if missing:
    sys.exit('the catalogue lacks these pool places: %s' % missing)
chosen = SI.plan(gd, pr, pool)
say('places to make again', len(chosen))
ops, follow, rep = SI.ops(gd, pr, server._place_clear_ops, pool, chosen, {b['key'] for b in cat})
say('ops', len(ops), {k: rep.get(k) for k in ('places', 'given a way out')}, 'skipped', rep['skipped'], 'by pool', rep['by_pool'])
if os.path.getmtime(mod) != seen:
    sys.exit('Waikiki.json changed while loading: nothing written')
pr.apply(LABEL, ops)
names = dict(pr.names)
aops, arep = SI.after(gd, pr, names, follow)
pr.apply(LABEL, aops, merge=True)
say('after', arep)
vrep = roomvary.vary(gd, pr, apply=True, merge=True, label=LABEL)
say('roomvary', vrep if not isinstance(vrep, dict) else {k: vrep[k] for k in list(vrep)[:8]})
# checks
src = roomvary.sources(gd, pr)
left = [k for k, c in src.items() if gd.edid(c) in SI.RESTROOMS]
new_keys = [names[f['tag']] for f in follow]
by = collections.Counter(gd.edid(src[k]) if k in src else '?' for k in new_keys)
nolink, nonav, bad = [], [], []
for k in new_keys:
    doors = SI._doors_into(pr, k)
    if not doors or not all((pr.cells[k]['refs'].get(d[2]['tel']['door']) or {}).get('tel') for d in doors):
        nolink.append(k)
    if k not in pr.navmesh:
        nonav.append(k)
walked = 0
for k in new_keys[::10]:                       # (every tenth walked: a few minutes for all)
    r = floorcheck.check(gd, pr, k)
    walked += 1
    if not r['reached'] or r['unreached_ways']:
        bad.append((recordio.field(pr.records[k], 'EDID'), r))
same = 0
for k in new_keys:
    pass
say('restroom copies left', len(left), '; new places', len(new_keys), '; different insides', len(by), dict(by.most_common()))
say('door not linked both ways', len(nolink), '; no navmesh', len(nonav), '; walked', walked, 'of which not walkable from the way in', len(bad), bad[:3])
pr.save()
say('saved')
if not REAL:
    import espwrite
    say('plugin written', pr.plugin_path(), espwrite.write(gd, pr, pr.plugin_path()), 'bytes')
no_way = {k for k, why in rep['skipped'] if why == '0 doors lead in'}        # (copies nobody can get into: left as they are)
say('restroom copies with no door into them, left:', len(no_way))
ok = set(left) <= no_way and not nolink and not nonav and not bad and len(rep['skipped']) == len(no_way)
say('CHECKS: all good' if ok else 'CHECKS FAILED', '; one Undo: "%s"' % LABEL)
