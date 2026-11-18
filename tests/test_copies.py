"""Other copies of the mod's plugin the game could load instead (copies.py): a fake MO2 instance and a fake Data folder.
After 18 Nov 2026, when Put in MO2 said it was in while yesterday's copy in the game's Data was what played."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import copies  # noqa: E402
import project  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


root = os.path.join(project.HOME, 'copies')


def put(folder, data, name='Waikiki.esp'):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name), 'wb') as f:
        f.write(data)
    return os.path.join(folder, name)


NEW, OLD = b'TES4 new ship spot' * 100, b'TES4 old ship spot' * 90
built = put(os.path.join(root, 'build'), NEW)
data = os.path.join(root, 'Data')
mods = os.path.join(root, 'mods')
over = os.path.join(root, 'overwrite')
mine = os.path.join(mods, 'Waikiki')
put(mine, NEW)
os.makedirs(data)
os.makedirs(over)
lo = types.SimpleNamespace(data_dir=data, instance=types.SimpleNamespace(mods_dir=mods, overwrite_dir=over),
                           modlist=[{'name': 'Waikiki', 'on': True, 'unmanaged': False},
                                    {'name': 'Older Waikiki', 'on': True, 'unmanaged': False},
                                    {'name': 'Switched off', 'on': False, 'unmanaged': False},
                                    {'name': 'Unmanaged: Waikiki', 'on': True, 'unmanaged': True}])

check('nothing else: no stale copies', copies.stale(built, lo, mine) == [])
check('its own mod folder is never counted', copies.others(built, lo, mine) == [])

old_data = put(data, OLD)
s = copies.stale(built, lo, mine)
check("an old copy in the game's Data is stale", [c['path'] for c in s] == [old_data], s)
check('and FOLab may move it', s and s[0]['movable'])

same = put(over, NEW)
check('a copy with the same bytes is listed but not stale',
      any(c['path'] == same and c['same'] for c in copies.others(built, lo, mine)) and len(copies.stale(built, lo, mine)) == 1)
os.remove(same)

put(os.path.join(mods, 'Older Waikiki'), OLD)
put(os.path.join(mods, 'Switched off'), OLD)
s = copies.stale(built, lo, mine)
check("another mod's switched-on copy is stale, not movable",
      any('Older Waikiki' in c['where'] and not c['movable'] for c in s), s)
check('a switched-off mod is not counted', not any('Switched off' in c['where'] for c in s))

nv = os.path.join(root, 'nv-rs mods')
put(nv, OLD)
check("nv-rs's copy counts only when asked", len(copies.stale(built, lo, mine, nv)) == len(s) + 1)

same_size = put(os.path.join(root, 'samesize'), b'X' * len(NEW))
check('same size, other bytes: stale', not copies._same(same_size, built))

moved = copies.move_out([old_data], 'Waikiki.esp')
check("move_out takes it out of Data", not os.path.exists(old_data))
check('into backups, with where it came from', os.path.isfile(moved[0]['to'])
      and open(os.path.join(os.path.dirname(moved[0]['to']), 'came from.txt'), encoding='utf-8').read().strip() == old_data)
try:
    copies.move_out([os.path.join(mine, 'Waikiki.esp').replace('Waikiki.esp', 'Other.esp')], 'Waikiki.esp')
    check('refuses a file of another name', False)
except ValueError:
    check('refuses a file of another name', True)
os.environ['FOLAB_NO_GAME_WRITES'] = '1'
try:
    copies.move_out([os.path.join(mods, 'Older Waikiki', 'Waikiki.esp')], 'Waikiki.esp')
    check('a scratch FOLab may not move anything', False)
except ValueError:
    check('a scratch FOLab may not move anything', True)
