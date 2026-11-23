"""settler_far_redraw.py [real] [--home H] [--app A]: the settlers' and the Huáng halls' far models (_lod.nif) written afresh,
light enough for the distant blocks.

From a ridge the user saw no Huáng town (23 Nov 2026). The distant block over it (x19, y16) was full: a block is one shape
of at most 65,000 corners, and settlerset's far roofs were the full curved sweep (9 rows by 15), so a wall length's far
model was 1,816 corners, a big gate's 5,736; lodobj then left out 28 of the 61 walls, the 6 screens, the freighter and two
gates. settlerset's far roofs are now a few rows (`ROWS_FAR`, `ALONG_FAR`: a wall 216, a hall 568, a gate 936; the full
models unchanged), and lodobj puts what's built before what grows. This writes the far files of every settler piece and
both Huáng halls the mod has a record of into its own files again. Files only: no Undo, nothing in Waikiki.json. Then the
distant blocks are made again (lodobj), and the build and install.

The app must have the far roofs (its settlerset has ROWS_FAR); huangset comes from this file's checkout. Without `real`:
into a copy of those folders in D:\\FOLabScratch\\settlerfar."""
import importlib.util
import os
import shutil
import subprocess
import sys

ARGS = sys.argv[1:]
REAL = 'real' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


REAL_HOME = r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab'
SCRATCH = r'D:\FOLabScratch\settlerfar'
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
    shutil.rmtree(SCRATCH, ignore_errors=True)
    os.makedirs(os.path.join(SCRATCH, 'projects'))
    src = os.path.join(REAL_HOME, 'projects')
    for n in os.listdir(src):
        if n.startswith('Waikiki.') and os.path.isfile(os.path.join(src, n)):
            shutil.copy2(os.path.join(src, n), os.path.join(SCRATCH, 'projects', n))
    for d in ('settler', 'huang'):
        shutil.copytree(os.path.join(src, 'Waikiki assets', 'meshes', 'folab', d), os.path.join(SCRATCH, 'projects', 'Waikiki assets', 'meshes', 'folab', d))
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
if '--settlerset' in ARGS:       # (a patched settlerset to rehearse with, before it is in the app)
    _sp = importlib.util.spec_from_file_location('settlerset', opt('--settlerset', ''))
    sys.modules['settlerset'] = importlib.util.module_from_spec(_sp)
    _sp.loader.exec_module(sys.modules['settlerset'])
import library, modelmake, modelsets, project, recordio, settlerset  # noqa: E402
if not hasattr(settlerset, 'ROWS_FAR'):
    sys.exit('this app\'s settlerset has the full far roofs still (no ROWS_FAR): nothing done')
modelsets._all_sets()
for k in [k for k, v in modelsets.PIECES.items() if v.get('set') in ('doors', 'huang')]:
    modelsets.PIECES.pop(k, None)
for m in ('doorset', 'huangset'):
    spec = importlib.util.spec_from_file_location(m, os.path.join(MINE, m + '.py'))
    sys.modules[m] = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sys.modules[m])
pr = project.Project.open('Waikiki')
have = {recordio.field(r, 'EDID') for k, r in pr.records.items() if k.startswith('+') and r.get('type') == 'STAT'}
root = library.assets_dir(pr)
written, same, sizes = [], 0, {}
for piece, what in sorted(modelsets.PIECES.items()):
    if what['set'] not in ('settler', 'huang') or what['edid'] not in have:
        continue
    desc = what['describe']()
    far = modelsets.far_of(desc)
    if far is None:
        continue
    made = modelmake.make(far)
    rel = 'meshes\\folab\\%s\\%s_lod.nif' % (what['set'], what['file'])
    sizes[piece] = sum(len(s['p']) // 3 for s in made['shapes'])
    full = os.path.join(root, rel)
    if os.path.isfile(full) and open(full, 'rb').read() == made['nif']:
        same += 1
        continue
    library._put(root, rel, made['nif'])
    written.append(rel)
print('far models written again:', len(written), '; already right:', same)
print('corners each:', sizes)
print('CHECKS: all good' if (written or same) and max(sizes.values() or [0]) < 2000 else 'CHECKS FAILED')
