"""huang_talk_into_waikiki.py [real] [--home H] [--app A]: the Huáng's own goodbyes, hellos and idle chatter (huangtalk.py).

One Undo, "The Huáng's own goodbyes and hellos": a line of their own in GOODBYE, HELLO and IdleChatter for every Huáng
who had none there, each voiced as their greetings are (Mandarin by Kokoro's Chinese voices; Zhao Lei in English). Then
the checks: no Huáng left with no line of their own in those topics, every new line with its .ogg and .lip.

Without `real` it rehearses on a copy (json, journal, source, assets, voices) in D:\\FOLabScratch\\huangtalk\\home and
writes the plugin there. `real`: game, FOLab, MO2, GECK and nv-rs closed; backed up first. The main checkout's app (it
has huangland); huangtalk from this file's checkout."""
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
SCRATCH = r'D:\FOLabScratch\huangtalk\home' + ('_barks' if '--barks' in sys.argv[1:] else '')
APP = opt('--app', r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
MINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
HOME = opt('--home', REAL_HOME if REAL else SCRATCH)
BARKS = '--barks' in ARGS       # (the combat and reaction barks instead: a step of its own, after the talk step)
LABEL = 'The Huáng\'s own barks' if BARKS else 'The Huáng\'s own goodbyes and hellos'
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
    for d in ('Waikiki source', 'Waikiki assets', 'Waikiki voices'):
        subprocess.run(['robocopy', os.path.join(src, d), os.path.join(dst, d), '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/MT:16'], capture_output=True)
    say('copied Waikiki (json, journal, source, assets, voices) into', SCRATCH)
os.environ['FOLAB_HOME'] = HOME
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
sys.path.insert(0, APP)
import gamedata, project, server  # noqa: E402
import huangland as HL  # noqa: E402
spec = importlib.util.spec_from_file_location('huangtalk', os.path.join(MINE, 'huangtalk.py'))
HT = sys.modules['huangtalk'] = importlib.util.module_from_spec(spec)
spec.loader.exec_module(HT)

mod = os.path.join(project.PROJECTS_DIR, 'Waikiki.json')
seen = os.path.getmtime(mod)
if REAL:
    back = os.path.join(HOME, 'backups', 'Waikiki before huang %s ' % ('barks' if BARKS else 'talk') + time.strftime('%m%d-%H%M'))
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
TOPS = tuple(HT.BARKS) if BARKS else HT.TOPICS
before = {t: len(v) for t, v in HT.leaks(gd, pr, TOPS).items()}
say('Huáng with no line of their own, before', before)
ops, plan, rep = HT.ops(gd, pr, TOPS, HT.ZHAO_BARKS if BARKS else None)
say('new lines', rep)
if os.path.getmtime(mod) != seen:
    sys.exit('Waikiki.json changed while loading: nothing written')
pr.apply(LABEL, ops)
pr.save()
v = HL.voice(gd, pr, plan, progress=None)
say('voiced', v['voiced'], 'problems', v['problems'][:5])
after = HT.leaks(gd, pr, TOPS)
import api_voices as av, library  # noqa: E402
root = library.assets_dir(pr)
miss = []
for lk, num, _zh in plan:
    info = av.line_info(gd, pr, lk)
    r = next((x for x in info.get('responses', ()) if x['number'] == num), None)
    if r is None or not all(os.path.isfile(os.path.join(root, r['path'] + ext)) for ext in ('.ogg', '.lip')):
        miss.append((lk, num))
say('Huáng with no line of their own, after', {t: len(x) for t, x in after.items()}, '; lines without .ogg/.lip', len(miss), miss[:5])
if not REAL:
    import espwrite
    say('plugin written', pr.plugin_path(), espwrite.write(gd, pr, pr.plugin_path()), 'bytes')
ok = not any(after.values()) and not miss and not v['problems']
say('CHECKS: all good' if ok else 'CHECKS FAILED', '; one Undo: "%s"' % LABEL)
