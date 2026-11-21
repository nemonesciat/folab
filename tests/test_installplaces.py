"""Every place the game could load the mod from (copies.everywhere, server.install_places / install_everywhere): the place
Put in game puts it, every nv-rs on the PC, other copies; each current, old, switched off or missing; Bring everything
up to date puts the save in the place and in each nv-rs that should have it, never in one it shouldn't; a scratch FOLab
refuses nv-rs too. Fake folders throughout; the real putting-in (install.install, nvrs.put_in) is replaced by a note.
After 18-20 Nov 2026: "is it really in?" asked again and again across the game, MO2 and four nv-rs copies."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import copies  # noqa: E402
import install  # noqa: E402
import nvrs  # noqa: E402
import project  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


root = os.path.join(project.HOME, 'places')
NEW, OLD = b'TES4 tonight' * 100, b'TES4 last night' * 90


def put(folder, data, name='Mod.esp'):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name), 'wb') as f:
        f.write(data)
    return os.path.join(folder, name)


def a_nvrs(name):
    d = os.path.join(root, 'Games', name)
    os.makedirs(os.path.join(d, 'app'), exist_ok=True)
    for f in ('Play.exe', os.path.join('app', 'FalloutNV.exe')):
        open(os.path.join(d, f), 'wb').close()
    return d


built = put(os.path.join(root, 'build'), NEW)
data = os.path.join(root, 'Data')
os.makedirs(data, exist_ok=True)
rs1, rs2, rs3 = a_nvrs('nv-rs'), a_nvrs('nv-rs-pad'), a_nvrs('nv-rs-old')
put(os.path.join(rs2, 'mods'), NEW)
put(os.path.join(rs3, 'mods'), OLD)

main = {'installed': True, 'current': True, 'active': True}
rows = copies.everywhere(built, main, "the game's Data folder", os.path.join(data, 'Mod.esp'), None, None, [rs1, rs2, rs3], False)
by = {r.get('folder', r['kind']): r for r in rows}
check('the main place first, current', rows[0]['kind'] == 'main' and rows[0]['state'] == 'current')
check('an nv-rs with this save: current', by[rs2]['state'] == 'current' and by[rs2]['target'])
check('an nv-rs with an older one: old, and to be brought up to date', by[rs3]['state'] == 'old' and by[rs3]['target'])
check('an nv-rs without it, nv-rs not what plays: missing, left alone', by[rs1]['state'] == 'missing' and not by[rs1]['target'])
rows = copies.everywhere(built, main, 'x', 'y', None, None, [rs1], True)
check('with nv-rs chosen, every nv-rs is a place to put it', rows[1]['target'])
for m, want in (({'installed': False}, 'missing'), ({'installed': True, 'current': False}, 'old'),
                ({'installed': True, 'current': True, 'active': False}, 'off')):
    check('main place: %s' % want, copies.everywhere(built, m, 'x', 'y')[0]['state'] == want)

# ---- in a loadout: other copies that would load instead are listed, never a place to put it
import types  # noqa: E402
mods = os.path.join(root, 'mo2mods')
mine = os.path.join(mods, 'Mod')
put(mine, NEW)
put(data, OLD)
lo = types.SimpleNamespace(data_dir=data, instance=types.SimpleNamespace(mods_dir=mods, overwrite_dir=os.path.join(root, 'over')),
                           modlist=[{'name': 'Mod', 'on': True, 'unmanaged': False}])
rows = copies.everywhere(built, main, 'MO2', os.path.join(mine, 'Mod.esp'), lo, mine, [], False)
other = [r for r in rows if r['kind'] == 'other']
check("the game's Data's old copy: listed as old, movable, not a place to put it",
      len(other) == 1 and other[0]['state'] == 'old' and other[0]['movable'] and not other[0]['target'], other)
os.remove(os.path.join(data, 'Mod.esp'))

# ---- Bring everything up to date, through the server with the putting-in replaced
import server  # noqa: E402
import loadout  # noqa: E402
did = []
server.PR = types.SimpleNamespace(plugin='Mod.esp', name='Mod', path=built)
server.GD = types.SimpleNamespace(data_dir=data)
project.BUILD_DIR = os.path.dirname(built)
server.save = lambda: {'path': built}
server.state = lambda: {'ok': True}
server.not_while_playing = lambda: None
server._engine = lambda: 'original'
server._nvrs_setup = lambda: None
server.load_settings = lambda: {}
loadout.current = lambda: None
loadout.under_mo2 = lambda: False
nvrs.all_found = lambda chosen=None: [rs1, rs2, rs3]
install.install = lambda d, b: did.append(('game', d))
nvrs.put_in = lambda folder, plugins, setup=None: did.append(('nv-rs', folder))
install.status = lambda d, p: {'installed': False, 'current': False, 'active': False}
out = server.install_everywhere()
check('put in the game, and the nv-rs with an older copy; not the up-to-date one, not one without it',
      did == [('game', data), ('nv-rs', rs3)], did)
check('says what it did', not out['failed'] and len(out['done']) == 2 and out['state'] == {'ok': True}, out)

did.clear()
loadout.under_mo2 = lambda: True
out = server.install_everywhere()
check('started from MO2: nv-rs left, and said why', did == [('game', data)] and any('MO2' in f['why'] for f in out['failed']), out)
loadout.under_mo2 = lambda: False

did.clear()
install.install = lambda d, b: (_ for _ in ()).throw(ValueError('Data is read-only'))
out = server.install_everywhere()
check('one place failing is said; the others still done', ('nv-rs', rs3) in did and out['failed'][0]['why'] == 'Data is read-only', out)

# ---- a scratch FOLab: nothing into nv-rs either
import importlib  # noqa: E402
importlib.reload(nvrs)
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
try:
    nvrs.put_in(rs1, [built])
    check('a scratch FOLab may not put into nv-rs', False)
except ValueError as e:
    check('a scratch FOLab may not put into nv-rs', 'scratch' in str(e))
check('and nothing landed there', not os.path.exists(os.path.join(rs1, 'mods', 'Mod.esp')))
try:
    server.install_everywhere()
    check('a scratch FOLab: Bring everything up to date refused', False)
except ValueError:
    check('a scratch FOLab: Bring everything up to date refused', True)
