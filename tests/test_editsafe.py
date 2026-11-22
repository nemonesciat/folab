"""Everyday editing you can trust (22 Nov 2026, the user: "I can't make edits to my map with FOLab, I'm unsure if MY
edits will save"):
- a running FOLab holds the mod it has open (project.hold): another process can still read it, but its writes (apply,
  save, sync) are refused with InUse and the mod's files don't change; a lock left by a FOLab that died counts for
  nothing; let go, others write again.
- Put in game with places chosen (server.play_in / put_in_chosen): the save goes into every chosen place and no other
  (the real nv-rs copies the user doesn't play, MO2), and the header's rows say which are chosen.
- a scratch FOLab (FOLAB_NO_GAME_WRITES) may put into a pretend nv-rs under FOLAB_FAKE_GAMES, never another.
Fake folders throughout; nothing touches a game."""
import json
import os
import subprocess
import sys
import time

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app')
sys.path.insert(0, APP)
import project  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


pr = project.Project.create('Trust')
pr.records['+000900'] = {'type': 'MISC', 'EDID': 'Mine'}
pr.sync()

# ---- another process (a FOLab) holds it
code = ('import sys, time; sys.path.insert(0, %r); import project; project.hold(%r); print("held", flush=True); '
        'time.sleep(30)' % (APP, pr.path))
child = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE, text=True, env=dict(os.environ))
check('the other process holds it', child.stdout.readline().strip() == 'held')
h = project.holder(pr.path)
check('holder names it, with a time', h and h.get('by') == 'FOLab' and h.get('since'), h)
before = (os.path.getsize(pr.path), os.path.exists(pr.journal_path) and os.path.getsize(pr.journal_path))
pr.records['+000901'] = {'type': 'MISC', 'EDID': 'Mine2'}
try:
    pr.sync()
    check('a write while FOLab holds it is refused', False)
except project.InUse as e:
    check('a write while FOLab holds it is refused, in words', 'Close FOLab first' in str(e) and 'Trust' in str(e), e)
for name, fn in (('save', lambda: pr.save()), ('apply', lambda: pr.apply('x', [{'op': 'record', 'key': '+000902', 'record': {'type': 'MISC', 'EDID': 'M3'}}]))):
    try:
        fn()
        check(name + ' refused too', False)
    except project.InUse:
        check(name + ' refused too', True)
after = (os.path.getsize(pr.path), os.path.exists(pr.journal_path) and os.path.getsize(pr.journal_path))
check("the mod's files untouched", before == after, (before, after))
check('reading it is fine', project.Project.open('Trust').records.get('+000900', {}).get('EDID') == 'Mine')
try:
    project.hold(pr.path)
    check('a second FOLab may not hold it too', False)
except project.InUse:
    check('a second FOLab may not hold it too', True)
child.kill(); child.wait()

# ---- that FOLab died without letting go: its lock is nothing
check('a dead FOLab holds nothing', project.holder(pr.path) is None)
pr.sync()
check('so writes go through again', '+000901' in project.Project.open('Trust').records)

# ---- held by this very process (FOLab's own server): its own writes go through; release lets go
project.hold(pr.path)
pr.records['+000903'] = {'type': 'MISC', 'EDID': 'M4'}
pr.sync()
check("the holder's own writes go through", '+000903' in project.Project.open('Trust').records)
project.release(pr.path)
check('released: no lock file left', not os.path.exists(project.lock_path(pr.path)))
with open(project.lock_path(pr.path), 'w') as f:
    json.dump({'pid': 'nonsense'}, f)
check('a broken lock file is no lock', project.holder(pr.path) is None)
os.remove(project.lock_path(pr.path))
check('the lock is never listed as a mod', all(p['name'] == 'Trust' for p in project.list_projects()))

# ---- Put in game into the places chosen, and only those
import types  # noqa: E402
import install  # noqa: E402
import loadout  # noqa: E402
import nvrs  # noqa: E402
import server  # noqa: E402

root = os.path.join(project.HOME, 'fakegames')


def a_nvrs(name):
    d = os.path.join(root, name)
    os.makedirs(os.path.join(d, 'app'), exist_ok=True)
    for f in ('Play.exe', os.path.join('app', 'FalloutNV.exe')):
        open(os.path.join(d, f), 'wb').close()
    return d


pad, nxt, old = a_nvrs('nv-rs-pad'), a_nvrs('nv-rs-next'), a_nvrs('nv-rs')
build = os.path.join(project.HOME, 'b')
os.makedirs(build, exist_ok=True)
built = os.path.join(build, 'Trust.esp')
with open(built, 'wb') as f:
    f.write(b'TES4 now' * 50)
os.makedirs(os.path.join(old, 'mods'), exist_ok=True)
with open(os.path.join(old, 'mods', 'Trust.esp'), 'wb') as f:
    f.write(b'TES4 then' * 40)
settings = {}
server.PR = types.SimpleNamespace(plugin='Trust.esp', name='Trust', path=pr.path)
server.GD = types.SimpleNamespace(data_dir=os.path.join(root, 'Data'))
project.BUILD_DIR = build
server.save = lambda: {'path': built}
server.state = lambda: {'ok': True}
server.not_while_playing = lambda: None
import playtest  # noqa: E402
playing = []
playtest.running_in = lambda f: f in playing
server._engine = lambda: 'nv-rs'
server._nvrs_setup = lambda: None
server.load_settings = lambda: dict(settings)
server.save_settings = lambda **kw: settings.update(kw)
loadout.current = lambda: None
loadout.under_mo2 = lambda: False
nvrs.all_found = lambda chosen=None: [old, pad, nxt]
did = []
install.install = lambda d, b: did.append(('game', d))
install.status = lambda d, p: {'installed': False}
real_put_in = nvrs.put_in
nvrs.put_in = lambda folder, plugins, setup=None: did.append(('nv-rs', folder))

check('nothing chosen: FOLab\'s usual place', server.play_in() == [] and [r['name'] for r in server.install_places() if r['chosen']] == ['the game'])
server.set_play_in([pad, nxt.upper()])
check('chosen: kept as the folders FOLab found', settings['play_in'] == [pad, nxt], settings)
rows = server.install_places()
check('rows: the chosen two and no other', sorted(r['name'] for r in rows if r['chosen']) == ['nv-rs-next', 'nv-rs-pad'], rows)
check('rows: each named short', {r['name'] for r in rows} >= {'the game', 'nv-rs', 'nv-rs-pad', 'nv-rs-next'})
out = server.put_in_chosen()
check('Put in game: into nv-rs-pad and nv-rs-next only', sorted(did) == sorted([('nv-rs', pad), ('nv-rs', nxt)]), did)
check('says where, by name', sorted(out['done']) == ['nv-rs-next', 'nv-rs-pad'] and not out['failed'], out)
check("the old nv-rs's copy doesn't count against it", server.stale_copies() == [] or all('nv-rs' not in c['where'] for c in server.stale_copies()), server.stale_copies())
did.clear(); playing.append(pad)
out = server.put_in_chosen()
check('a game running from nv-rs-pad: that one left and said why, nv-rs-next still done',
      did == [('nv-rs', nxt)] and out['done'] == ['nv-rs-next'] and out['failed'][0]['where'] == 'nv-rs-pad'
      and 'running' in out['failed'][0]['why'], out)
playing.clear()
try:
    server.set_play_in([os.path.join(root, 'not-a-game')])
    check('a folder that is not nv-rs is refused', False)
except ValueError:
    check('a folder that is not nv-rs is refused', True)

# ---- a scratch FOLab may put into a pretend nv-rs, never another
nvrs.put_in = real_put_in
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
os.environ['FOLAB_FAKE_GAMES'] = os.path.join(root, 'nv-rs-pad')
try:
    nvrs.put_in(nxt, [built])
    check('scratch: an nv-rs outside the pretend folder is refused', False)
except ValueError:
    check('scratch: an nv-rs outside the pretend folder is refused', not os.path.exists(os.path.join(nxt, 'mods', 'Trust.esp')))
os.environ['FOLAB_FAKE_GAMES'] = root
nvrs.put_in(pad, [built])
check('scratch: the pretend one gets it', open(os.path.join(pad, 'mods', 'Trust.esp'), 'rb').read() == open(built, 'rb').read())
