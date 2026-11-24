"""voice_gaps_into_waikiki.py [real] [--count] [--home H] [--app A]: every line of Waikiki's own in every voice type folder its
speakers may look in (voicegaps.py). Counts the gaps (each response x folder without its .ogg and .lip), speaks what's
missing as peopletalk does, counts again. --count stops after the first count. No record changes (nothing for Undo): only
sound files and voices.json, which is backed up first in real mode.

Runs at Idle priority (Chatterbox's process inherits it). Without `real` it works on the scratch home the people-talk
rehearsal left (D:\\FOLabScratch\\peopletalk\\home) or --home. `real`: game, FOLab, MO2, GECK and nv-rs closed. The main
checkout's app; voicegaps and peopletalk from this file's checkout."""
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
COUNT = '--count' in ARGS


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


REAL_HOME = r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\packaging\out\FOLab'
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
MINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
HOME = opt('--home', REAL_HOME if REAL else r'D:\FOLabScratch\peopletalk\home')
t0 = time.time()
sys.stdout.reconfigure(encoding='utf-8')
say = lambda *a: print('%5.0fs' % (time.time() - t0), *a, flush=True)
if REAL and not COUNT:
    running = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    busy = [n for n in ('falloutnv.exe', 'folab.exe', 'play.exe', 'modorganizer.exe', 'geck.exe', 'nvse_loader.exe') if n in running]
    if busy:
        sys.exit('not while these run: ' + ', '.join(busy))
if not REAL and os.path.normcase(os.path.abspath(HOME)).startswith(os.path.normcase(REAL_HOME)):
    sys.exit('a rehearsal never works on the real home')
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
os.environ.setdefault('FOLAB_CHATTERBOX', r'D:\FOLab-voice\chatterbox')
sys.path.insert(0, APP)
import gamedata, project, server  # noqa: E402
for name in ('peopletalk', 'voicegaps'):
    spec = importlib.util.spec_from_file_location(name, os.path.join(MINE, name + '.py'))
    m = sys.modules[name] = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
VG = sys.modules['voicegaps']

mod = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
if REAL and not COUNT:
    if project.holder(mod) if hasattr(project, 'holder') else False:
        sys.exit('a FOLab holds Waikiki: close it first')
    vj = os.path.join(project.PROJECTS_DIR, 'Waikiki voices', 'voices.json')
    back = os.path.join(HOME, 'backups', 'voices.json before voice gaps ' + time.strftime('%m%d-%H%M'))
    os.makedirs(back)
    shutil.copy2(vj, os.path.join(back, 'voices.json'))
    say('backup', back)
server.not_while_playing = lambda: None
server.GD = gamedata.GameData()
server.BR = None
pr = project.Project.open('Waikiki')
server.load_game(pr)
gd = server.GD
say('loaded')
miss, rep = VG.gaps(gd, pr)
say('before', rep)
if COUNT or not miss:
    say('CHECKS: all good' if not miss else 'gaps to fill: %d' % len(miss))
    sys.exit(0)
v = VG.fill(gd, pr, miss, progress=lambda m: say(m))
say('voiced', v['voiced'], 'copied', v['copied'], 'problems', v['problems'][:5])
miss2, rep2 = VG.gaps(gd, pr)
say('after', rep2)
say('CHECKS: all good' if not miss2 and not v['problems'] else 'CHECKS FAILED')
