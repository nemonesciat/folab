"""people_talk_into_waikiki.py [real] [--barks] [--dry] [--home H] [--app A]: Waikiki's people's own goodbyes, hellos and idle
chatter (peopletalk.py); with --barks their combat and reaction barks instead (a step of its own, after the talk step).

One Undo, "Waikiki's people's own goodbyes and hellos" (or "... barks"): lines of their own in those topics for every person
of the mod's who isn't Huáng, each spoken into every voice type folder the person may speak from (Chatterbox where the
mod uses it). Then the checks: nobody left with no line of their own in those topics, every response of every new line
with its .ogg and .lip in each folder. --dry stops before voicing (a scratch home only).

Runs at Idle priority (Chatterbox's process inherits it). Without `real` it rehearses on a copy (json, journal, source,
assets, voices) in D:\\FOLabScratch\\peopletalk\\home and writes the plugin there. `real`: game, FOLab, MO2, GECK and nv-rs
closed; backed up first. The main checkout's app; peopletalk from this file's checkout."""
import ctypes
import importlib.util
import os
import shutil
import subprocess
import sys
import time

ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x40)      # (Idle)
ARGS = sys.argv[1:]
REAL = 'real' in ARGS
BARKS = '--barks' in ARGS
DRY = '--dry' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


REAL_HOME = r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab'
SCRATCH = r'D:\FOLabScratch\peopletalk\home' + ('_barks' if BARKS else '')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
MINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
HOME = opt('--home', REAL_HOME if REAL else SCRATCH)
LABEL = "Waikiki's people's own barks" if BARKS else "Waikiki's people's own goodbyes and hellos"
t0 = time.time()
sys.stdout.reconfigure(encoding='utf-8')
say = lambda *a: print('%5.0fs' % (time.time() - t0), *a, flush=True)
if REAL:
    if DRY:
        sys.exit('--dry only on a scratch home')
    running = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    busy = [n for n in ('falloutnv.exe', 'folab.exe', 'play.exe', 'modorganizer.exe', 'geck.exe', 'nvse_loader.exe') if n in running]
    if busy:
        sys.exit('not while these run: ' + ', '.join(busy))
elif HOME == SCRATCH and '--keep' not in ARGS:
    src = os.path.join(REAL_HOME, 'projects')
    dst = os.path.join(SCRATCH, 'projects')
    if os.path.isdir(SCRATCH):
        shutil.rmtree(SCRATCH)
    os.makedirs(dst)
    for n in os.listdir(src):
        if n.startswith('Waikiki.') and os.path.isfile(os.path.join(src, n)):
            shutil.copy2(os.path.join(src, n), os.path.join(dst, n))
    for d in ('Waikiki source', 'Waikiki assets', 'Waikiki voices'):
        subprocess.run(['robocopy', os.path.join(src, d), os.path.join(dst, d), '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/MT:4'], capture_output=True)
    say('copied Waikiki (json, journal, source, assets, voices) into', SCRATCH)
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
os.environ.setdefault('FOLAB_CHATTERBOX', r'D:\FOLab-voice\chatterbox')
sys.path.insert(0, APP)
import gamedata, project, server  # noqa: E402
spec = importlib.util.spec_from_file_location('peopletalk', os.path.join(MINE, 'peopletalk.py'))
PT = sys.modules['peopletalk'] = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PT)

mod = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
seen = os.path.getmtime(mod)
if REAL:
    if project.holder(mod) if hasattr(project, 'holder') else False:
        sys.exit('a FOLab holds Waikiki: close it first')
    back = os.path.join(HOME, 'backups', 'Waikiki before people %s ' % ('barks' if BARKS else 'talk') + time.strftime('%m%d-%H%M'))
    os.makedirs(back)
    for n in os.listdir(project.PROJECTS_DIR):
        if n.startswith('Waikiki.') and os.path.isfile(os.path.join(project.PROJECTS_DIR, n)):
            shutil.copy2(os.path.join(project.PROJECTS_DIR, n), os.path.join(back, n))
    vj = os.path.join(project.PROJECTS_DIR, 'Waikiki voices', 'voices.json')
    if os.path.isfile(vj):
        shutil.copy2(vj, os.path.join(back, 'voices.json'))
    say('backup', back)
server.not_while_playing = lambda: None
server.GD = gamedata.GameData()
server.BR = None
pr = project.Project.open('Waikiki')
server.load_game(pr)
server.PR = pr
gd = server.GD
say('loaded')
TOPS = tuple(PT.BARKS) if BARKS else PT.TOPICS
before = PT.leaks(gd, pr, TOPS)
say('people with no line of their own, before', {t: len(v) for t, v in before.items()})
ops, plan, rep = PT.ops(gd, pr, TOPS)
say('new lines', rep)
if rep['not covered']:
    sys.exit('people no unit covers: %s' % rep['not covered'])
if os.path.getmtime(mod) != seen:
    sys.exit('Waikiki.json changed while loading: nothing written')
pr.apply(LABEL, ops)
pr.save()
after = PT.leaks(gd, pr, TOPS)
say('people with no line of their own, after', {t: len(x) for t, x in after.items()})
folds = {}
for p in plan:
    folds.setdefault(p['unit'], PT.folders(gd, pr, p['keys']))
say('folders a unit speaks from', {u: len(f) for u, f in folds.items()}, '; responses x folders', sum(len(folds[p['unit']]) for p in plan))
if DRY:
    sys.exit(0)
v = PT.voice(gd, pr, plan, progress=lambda m: say(m))
say('voiced', v['voiced'], 'copied', v['copied'], 'problems', v['problems'][:5])
miss = PT.unvoiced(gd, pr, plan)
say('responses x folders without .ogg/.lip', len(miss), miss[:5])
if not REAL:
    import espwrite
    say('plugin written', pr.plugin_path(), espwrite.write(gd, pr, pr.plugin_path()), 'bytes')
ok = not any(after.values()) and not miss and not v['problems']
say('CHECKS: all good' if ok else 'CHECKS FAILED', '; one Undo: "%s"' % LABEL)
