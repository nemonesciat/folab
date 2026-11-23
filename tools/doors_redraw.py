"""doors_redraw.py [real] [--home H] [--app A]: FOLab's own doors' models, and the Kilauea's (closed and open), written
afresh into the mod's files.

doorset's doors carry one box of collision over the doorway, collision alone. Since modelmake gives every face left out a
look (the closed-model rule, 22 Nov 2026), that box took its part's look ('trim') and was drawn: a slab over the leaves,
so every FOLab door (homes, bungalows, hotels; not the lifts) showed as a plain painted panel. 9297809 gives the box no
look. The Kilauea's drum of glass is walled the same way (towerset._glass_wall: 24 boxes, gold): drawn, a gold slab
round its lobby glass in the city and in its view world; fixed the same way. A sweep of every set's 210 pieces found
no other (D:/FOLabScratch/huang/sweep.py). This writes each of these pieces the mod has a record of into
projects/<mod> assets/ again (modelsets.build, with this checkout's doorset and towerset), and says which files changed. No change to the mod's records: no Undo, nothing in Waikiki.json.
Then the usual build and install carries the new files.

Without `real`: into a copy of the assets in D:\\FOLabScratch\\doorsredraw (made from the real ones), to compare."""
import os
import shutil
import subprocess
import sys
import importlib.util

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


REAL_HOME = r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab'
SCRATCH = r'D:\FOLabScratch\doorsredraw'
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
MINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
HOME = opt('--home', REAL_HOME if REAL else SCRATCH)
sys.stdout.reconfigure(encoding='utf-8')
if REAL:
    running = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    busy = [n for n in ('falloutnv.exe', 'folab.exe', 'play.exe') if n in running]
    if busy:
        sys.exit('not while these run: ' + ', '.join(busy))
elif HOME == SCRATCH:
    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH)
    os.makedirs(os.path.join(SCRATCH, 'projects'))
    src = os.path.join(REAL_HOME, 'projects')
    for n in os.listdir(src):
        if n.startswith('Waikiki.') and os.path.isfile(os.path.join(src, n)):
            shutil.copy2(os.path.join(src, n), os.path.join(SCRATCH, 'projects', n))
    shutil.copytree(os.path.join(src, 'Waikiki assets', 'meshes', 'folab', 'doors'), os.path.join(SCRATCH, 'projects', 'Waikiki assets', 'meshes', 'folab', 'doors'))
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
import library, modelsets, project, recordio  # noqa: E402
modelsets._all_sets()
# (this checkout's doorset and towerset over the app's: their collision boxes have no look)
for k in [k for k, v in modelsets.PIECES.items() if v.get('set') == 'doors'] + ['kilauea', 'kilauea_open', 'kilauea_steps']:
    modelsets.PIECES.pop(k, None)
mods = {}
for m in ('doorset', 'towerset'):
    spec = importlib.util.spec_from_file_location(m, os.path.join(MINE, m + '.py'))
    mods[m] = sys.modules[m] = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mods[m])
doorset = mods['doorset']
REDRAW = dict(doorset.PIECES, **{k: modelsets.PIECES[k] for k in ('kilauea', 'kilauea_open')})
pr = project.Project.open('Waikiki')
have = {recordio.field(r, 'EDID') for k, r in pr.records.items() if k.startswith('+') and r.get('type') in ('DOOR', 'STAT')}
root = library.assets_dir(pr)
changed, same = [], 0
for piece, what in REDRAW.items():
    if what['edid'] not in have and what['edid'] + 'Static' not in have:
        continue
    made = modelsets.build(piece)
    for rel, data in made['files'].items():
        if not rel.lower().endswith('.nif'):
            continue                    # (the pictures didn't change)
        full = os.path.join(root, rel)
        if os.path.isfile(full) and open(full, 'rb').read() == data:
            same += 1
            continue
        library._put(root, rel, data)
        changed.append(rel)
print('door models written again:', len(changed), changed, '; already right:', same)
print('CHECKS: all good' if changed or same else 'CHECKS FAILED: no door of FOLab\'s in this mod')
