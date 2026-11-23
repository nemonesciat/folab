"""door_links_remake.py [real] [--home H] [--app A]: the outside navmeshes round FOLab's own doors made again, so each door
has its door triangle and people can path through it.

Until 5579156 the navmesh builder never counted a DOOR of the mod's own as a door: its link triangle was never made. On
22 Nov 2026 20:40, 363 of the 391 doors of the mod's own in Waikiki that lead somewhere had none, all outside (homes'
doors from doorset, the bungalows, the hotels' doors and lobby lifts, Vault 50's gear door), in 248 cells. This finds
them afresh (any mod-own door that leads somewhere and no mesh in its grid cell or the eight round it lists), makes
those cells' navmeshes again (navbuild.generate_area, NAV_BATCH at a time as api_maps does, each joined to what is round
it; a batch that fails goes a cell at a time), one Undo, and counts again: every such door must then be listed.

Without `real` it rehearses on a copy (json, journal, source, assets) in D:\\FOLabScratch\\doorlinks\\home. `real`: game,
FOLab, MO2, GECK and nv-rs closed; the mod backed up first. Run with the main checkout's app (it has the fix and reads
Waikiki.changes). About 4.5 s a cell: 248 cells near 20 minutes."""
import json
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
SCRATCH = r'D:\FOLabScratch\doorlinks\home'
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
HOME = opt('--home', REAL_HOME if REAL else SCRATCH)
LABEL = 'Navmeshes link FOLab\'s own doors'
NAV_BATCH = 40
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
sys.path.insert(0, APP)
import gamedata, project, server, navbuild, recordio  # noqa: E402
if "row['door'] = True" not in open(navbuild.__file__, encoding='utf-8').read():
    sys.exit('this app\'s navbuild doesn\'t count the mod\'s own doors yet (5579156): nothing done')

mod = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
seen = os.path.getmtime(mod)
if REAL:
    back = os.path.join(HOME, 'backups', 'Waikiki before door links ' + time.strftime('%m%d-%H%M'))
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

grid_of = {}
for w in gd.worlds():
    for xy, c in gd.grid(w).items():
        grid_of[gd.key(c)] = (w, xy)
by_world_xy = {v: k for k, v in grid_of.items()}


def unlinked():
    """[(door, the grid cell its foot is in)] of the mod's own doors that lead somewhere with no mesh listing them."""
    own = {k for k, r in pr.records.items() if k.startswith('+') and r.get('type') == 'DOOR'}
    cache, out = {}, []

    def listed(ck):
        if ck not in cache:
            nm = pr.navmesh.get(ck)
            metas = ([nm] + nm.get('others', [])) if nm else [navbuild.game_copy(gd, e) for e in navbuild.game_entries(gd, ck)]
            cache[ck] = {d[0] for m in metas for d in (m.get('doors') or [])}
        return cache[ck]
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if r.get('removed') or r.get('base') not in own or not r.get('tel') or not r.get('p'):
                continue
            if ck.startswith('+') or not navbuild.is_outside(gd, ck):
                if rk not in listed(ck):
                    out.append((rk, ck))
                continue
            w = gd.ext_cells[gd.from_key(ck)]           # (its world: a grid cell's or the world's persistent cell's)
            x, y = int(r['p'][0] // 4096), int(r['p'][1] // 4096)
            near = [by_world_xy.get((w, (x + dx, y + dy))) for dx in (0, -1, 1) for dy in (0, -1, 1)]
            near = [k for k in near if k]
            if near and not any(rk in listed(k) for k in near):
                out.append((rk, near[0]))
    return out


before = unlinked()
inside = sorted({ck for _d, ck in before if not navbuild.is_outside(gd, ck)})
todo = sorted({ck for _d, ck in before if navbuild.is_outside(gd, ck)})
say('doors without a door triangle', len(before), '; outside cells to make again', len(todo), '; places', len(inside))
if os.path.getmtime(mod) != seen:
    sys.exit('Waikiki.json changed while loading: nothing written')
first, made, missed = True, 0, []
for b in range(0, len(todo), NAV_BATCH):
    part = todo[b:b + NAV_BATCH]
    try:
        o, rep = navbuild.generate_area(gd, pr, part)
        pr.apply(LABEL, o, merge=not first)
        first = False
        made += rep['cells']
    except navbuild.NavError as e:
        say('batch', b, 'failed (%s): a cell at a time' % e)
        for k in part:
            try:
                o1, _r = navbuild.generate_area(gd, pr, [k])
                pr.apply(LABEL, o1, merge=not first)
                first = False
                made += 1
            except navbuild.NavError as e1:
                missed.append((k, str(e1)))
    say('cells', min(b + NAV_BATCH, len(todo)), 'of', len(todo))
for ck in inside:
    try:
        data, _r = navbuild.generate(gd, pr, ck)
        pr.apply(LABEL, [{'op': 'navmesh', 'cell': ck, 'mesh': data}], merge=not first)
        first = False
    except navbuild.NavError as e:
        missed.append((ck, str(e)))
after = unlinked()
pr.save()
say('saved')
json.dump({'before': before, 'after': after, 'cells': todo, 'places': inside, 'missed': missed},
          open(os.path.join(HOME, 'door_links_report.json'), 'w'), indent=1)
say('made', made, 'cells; missed', missed[:5], '; doors still without a door triangle', len(after), after[:5])
say('CHECKS: all good' if not after and not missed else 'CHECKS FAILED', '; one Undo: "%s"' % LABEL)
