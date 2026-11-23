"""moana_floors_into_waikiki.py [real] [--home H] [--app A]: the Moana's four floors made again (the user, 23 Nov 2026: "moana
interior very glitched, full of gaps and missing sections"; picture: corridor walls and ceiling panels missing, floor ending
on a drop).

The Moana's floors were built on 21 Nov by an earlier kitplan, which didn't yet turn down a plan whose floor steps off into
nothing. Walked as they stand (kitplan.Walk from each way in, over the real collision, eroded as the navmesh is): floor 1 has
8 holes, floor 3 19 (and 9 spots with no ceiling over the floor; half of it can't be reached), floor 4 4 (5 with no ceiling,
three quarters cut off); floor 2 none (the 8 edges every floor shows at its way in are the doorway behind the door, which a
walk can't see). The Royal Hawaiian's six and the Kilauea's four have none. Today's hotelfloors builds all of the Moana's on
the same kit with no open edges.

What it does, one Undo ("The Moana's floors made again"): finds the old floors (FOLabMoanaFloor<n>) and the two doors outside
that lead in (the lobby's lift, the deck's stair head), takes the old floors and their penthouse key out as Delete place
does, builds the new ones (hotelfloors.make, the Moana's own way), links the lobby lift and the deck to them both ways
arriving where you arrived before, makes their navmeshes, puts in who holds each floor (people_ops, as the old ones had).
Then every new floor is checked (holes: open edges past the way in's doorway; floor with no ceiling over it): any found
and nothing is saved.

Without `real` it rehearses on a copy (json, journal, source, assets, kits cache) in D:\\FOLabScratch\\moanafloors\\home.
`real`: game, FOLab, MO2, GECK and nv-rs closed; backed up first. The main checkout's app (it reads Waikiki.changes)."""
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
SCRATCH = r'D:\FOLabScratch\moanafloors\home'
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
HERE = os.path.dirname(os.path.abspath(__file__))
HOME = opt('--home', REAL_HOME if REAL else SCRATCH)
LABEL = 'The Moana\'s floors made again'
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
    if os.path.isdir(os.path.join(REAL_HOME, 'cache', 'kits')):
        shutil.copytree(os.path.join(REAL_HOME, 'cache', 'kits'), os.path.join(SCRATCH, 'cache', 'kits'))
    say('copied Waikiki (json, journal, source, assets, kits) into', SCRATCH)
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
sys.path.append(HERE)
import gamedata, project, recordio, server, navbuild, kitplan  # noqa: E402
import hotelfloors as HF  # noqa: E402
import floorcheck  # noqa: E402

mod = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
seen = os.path.getmtime(mod)
if REAL:
    back = os.path.join(HOME, 'backups', 'Waikiki before moana floors ' + time.strftime('%m%d-%H%M'))
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

hotel = 'moana'
tag = HF.HOTELS[hotel]['tag']
floors = sorted(((recordio.field(r, 'EDID'), k) for k, r in pr.records.items()
                 if k.startswith('+') and r.get('type') == 'CELL' and (recordio.field(r, 'EDID') or '').startswith('FOLab%sFloor' % tag)),
                key=lambda e: int(e[0][len('FOLab%sFloor' % tag):]))
if not floors:
    sys.exit('no old Moana floors found')
cells = [k for _e, k in floors]
say('old floors', [(e, k) for e, k in floors])
old = {e: floorcheck.check(gd, pr, k) for e, k in floors}
for e, r in old.items():
    say('before', e, r)
inside = {rk: ck for ck in cells for rk in (pr.cells.get(ck) or {}).get('refs', {})}
outside = [(ck, rk, r['tel']) for ck, c in pr.cells.items() if ck not in cells for rk, r in c['refs'].items()
           if (r.get('tel') or {}).get('door') in inside]
first, last = cells[0], cells[-1]
lobby = [o for o in outside if inside[o[2]['door']] == first]
lookout = [o for o in outside if inside[o[2]['door']] == last]
if len(lobby) != 1 or len(lookout) != 1 or len(outside) != 2:
    sys.exit('expected the lobby lift and the deck to lead in, found %s' % [(o[0], o[1], inside[o[2]['door']]) for o in outside])
back_to = {}
for ck in (first, last):
    for rk, r in pr.cells[ck]['refs'].items():
        t = r.get('tel')
        if t and t.get('door') in (lobby[0][1], lookout[0][1]):
            back_to[t['door']] = t['p']
if set(back_to) != {lobby[0][1], lookout[0][1]}:
    sys.exit('the old floors\' doors back out not found')
key = next((k for k, r in pr.records.items() if k.startswith('+') and recordio.field(r, 'EDID') == 'FOLab%sPenthouseKey' % tag), None)
named = set(cells) | ({key} if key else set())
users = sorted(recordio.field(r, 'EDID') or k for k, r in pr.records.items() if k not in named and any('"%s"' % n in json.dumps(r) for n in named))
if users:
    sys.exit('other records name an old floor or its key: %s' % users[:8])
others = [(ck, rk) for ck, c in pr.cells.items() if ck not in cells for rk, r in c['refs'].items()
          if key and ((r.get('props') or {}).get('lock') or {}).get('key') == key]
if others:
    sys.exit('locks elsewhere use the old key: %s' % others[:5])
remove_ops = []
for ck in cells:
    remove_ops += [o for o in server._place_clear_ops(ck) if not (o['op'] == 'tel' and o['ref'] in (lobby[0][1], lookout[0][1]))]
    remove_ops.append({'op': 'record_revert', 'key': ck})
if key:
    remove_ops.append({'op': 'record_revert', 'key': key})
if os.path.getmtime(mod) != seen:
    sys.exit('Waikiki.json changed while loading: nothing written')
pr.apply(LABEL, remove_ops)
say('old floors out:', len(remove_ops), 'ops')

m = HF.make(gd, pr, hotel, 1)
(lck, lrk, _t), (tck, trk, _t2) = lobby[0], lookout[0]
e, t = m['entry'], m['top']
ops = list(m['ops']) + [
    {'op': 'tel', 'cell': lck, 'ref': lrk, 'tel': {'door': '$' + e['door'], 'p': e['arrive']}},
    {'op': 'tel', 'cell': '$' + e['place'], 'ref': '$' + e['door'], 'tel': {'door': lrk, 'p': back_to[lrk]}},
    {'op': 'tel', 'cell': tck, 'ref': trk, 'tel': {'door': '$' + t['door'], 'p': t['arrive']}},
    {'op': 'tel', 'cell': '$' + t['place'], 'ref': '$' + t['door'], 'tel': {'door': trk, 'p': back_to[trk]}}]
pr.apply(LABEL, ops, merge=True)
names = dict(pr.names)
nav, nrep = HF.navmesh_ops(gd, pr, m, names)
bad = [k for k, v in nrep.items() if isinstance(v, str)]
if bad:
    sys.exit('no navmesh for %s: nothing saved' % bad)
pr.apply(LABEL, nav, merge=True)
pops, prep = HF.people_ops(gd, pr, m, names)
pr.apply(LABEL, pops, merge=True)
say('floors', [(r['place'], len(r['rooms'])) for r in m['report']], '; navmesh', {k: v.get('triangles') for k, v in nrep.items()}, '; people', prep if not isinstance(prep, dict) else {k: prep[k] for k in list(prep)[:6]})
new = {}
for p in m['places']:
    ck = names.get(p)
    new[recordio.field(pr.records[ck], 'EDID')] = floorcheck.check(gd, pr, ck)
for e2, r in new.items():
    say('after', e2, r)
fails = [e2 for e2, r in new.items() if r['holes'] or r['no_ceiling'] or r['unreached_ways']]
if fails:
    sys.exit('CHECKS FAILED on %s: nothing saved' % fails)
pr.save()
say('saved')
if not REAL:
    import espwrite
    say('plugin written', pr.plugin_path(), espwrite.write(gd, pr, pr.plugin_path()), 'bytes')
json.dump({'before': old, 'after': new}, open(os.path.join(HOME, 'moana_floors_report.json'), 'w'), indent=1, default=str)
say('CHECKS: all good ; one Undo: "%s"' % LABEL)
