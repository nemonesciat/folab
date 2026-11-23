"""huang_granary_edid.py [real] [--home H] [--app A]: the granary's room model (STAT) renamed FOLabHuangGranaryRoom, so it no
longer shares FOLabHuangGranary with the place it stands in (health's "Two things with one editor ID", 22 Nov 2026).
huangset names it so from now on. One Undo; only that record's editor ID changes (its model, bounds and the place's
ref to it stay). Without `real`: on a copy of Waikiki (json and journal) in D:\\FOLabScratch\\granaryedid."""
import copy
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
SCRATCH = r'D:\FOLabScratch\granaryedid'
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
HOME = opt('--home', REAL_HOME if REAL else SCRATCH)
OLD, NEW = 'FOLabHuangGranary', 'FOLabHuangGranaryRoom'
sys.stdout.reconfigure(encoding='utf-8')
if REAL:
    running = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    busy = [n for n in ('falloutnv.exe', 'folab.exe', 'play.exe', 'modorganizer.exe', 'geck.exe') if n in running]
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
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
import project, recordio  # noqa: E402
if REAL:
    back = os.path.join(HOME, 'backups', 'Waikiki before granary edid ' + time.strftime('%m%d-%H%M'))
    os.makedirs(back)
    for n in os.listdir(project.PROJECTS_DIR):
        if n.startswith('Waikiki.') and os.path.isfile(os.path.join(project.PROJECTS_DIR, n)):
            shutil.copy2(os.path.join(project.PROJECTS_DIR, n), os.path.join(back, n))
    print('backup', back)
pr = project.Project.open('Waikiki')
stat = [k for k, r in pr.records.items() if k.startswith('+') and r.get('type') == 'STAT' and recordio.field(r, 'EDID') == OLD]
cell = [k for k, r in pr.records.items() if k.startswith('+') and r.get('type') == 'CELL' and recordio.field(r, 'EDID') == OLD]
if len(stat) != 1 or len(cell) != 1:
    sys.exit('expected one STAT and one CELL named %s, found %d and %d: nothing done' % (OLD, len(stat), len(cell)))
if any(recordio.field(r, 'EDID') == NEW for r in pr.records.values()):
    sys.exit('%s is taken already: nothing done' % NEW)
rec = copy.deepcopy(pr.records[stat[0]])
recordio.set_field(rec, 'EDID', NEW, label='Editor ID')
pr.apply('The granary\'s room model renamed', [{'op': 'record', 'key': stat[0], 'record': rec}])
pr.save()
names = {}
for k, r in pr.records.items():
    e = (recordio.field(r, 'EDID') or '').lower()
    if e:
        names.setdefault(e, []).append(k)
left = [ks for ks in names.values() if len(ks) > 1]
print('renamed', stat[0], OLD, '->', NEW, '; records of the mod sharing an editor ID now:', left)
print('CHECKS: all good' if not left else 'CHECKS FAILED')
