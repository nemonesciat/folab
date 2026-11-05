"""The game's settings files: a change touches only its own lines, goes into both files, keeps read-only files
read-only and leaves a backup. Run against copies of the real files (tests/run.py points FOLAB_NV_INI at a scratch
folder); never the real ones."""
import os, shutil, stat, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gameini, project
def check(what, ok): print(('PASS ' if ok else 'FAIL ') + what)
real = os.path.join(os.path.expanduser('~'), 'Documents', 'My Games', 'FalloutNV')
ini = os.environ.get('FOLAB_NV_INI')
assert ini and os.path.normcase(os.path.abspath(ini)) != os.path.normcase(real), 'run through tests/run.py'
os.makedirs(ini, exist_ok=True)
for fn in gameini.FILES:
    shutil.copy2(os.path.join(real, fn), os.path.join(ini, fn))
os.chmod(os.path.join(ini, 'Fallout.ini'), stat.S_IREAD)                       # (as the user's is)
before = {fn: open(os.path.join(ini, fn), 'rb').read() for fn in gameini.FILES}
check('reads both files', set(gameini.read_all()) == set(gameini.FILES))
bk = gameini.write([('Display', 'fDefaultFOV', '90.0000'), ('display', 'ISIZE W', '1600'),
                    ('FOLab', 'sTestOnly', 'yes')])
after = {fn: open(os.path.join(ini, fn), 'rb').read() for fn in gameini.FILES}
check('the game ends up with the new FOV', gameini.value('Display', 'fDefaultFOV') == '90.0000')
check('names match whatever their case', gameini.value('Display', 'iSize W') == '1600')
for fn in gameini.FILES:
    a, b = before[fn].split(b'\r\n'), after[fn].split(b'\r\n')
    changed = [x for x, y in zip(a, b) if x != y]
    check('%s: only the changed lines differ (%d)' % (fn, len(changed)),
          all(l.lower().startswith((b'fdefaultfov', b'isize w')) for l in changed))
    check('%s: backup is the old file' % fn, open(os.path.join(bk, fn), 'rb').read() == before[fn])
check('a new setting goes into FalloutPrefs.ini only', b'sTestOnly=yes' in after['FalloutPrefs.ini'] and b'sTestOnly' not in after['Fallout.ini'])
check('Fallout.ini is still read-only', not os.access(os.path.join(ini, 'Fallout.ini'), os.W_OK))
check('backup is under FOLAB_HOME', os.path.abspath(bk).startswith(os.path.abspath(project.HOME)))
check('the real files were not touched', all(open(os.path.join(real, fn), 'rb').read() == before[fn] for fn in gameini.FILES))
sc = gameini.screens()
check('screens: one is the main one, first, with modes', bool(sc) and sc[0]['primary'] and sc[0]['modes'])
os.chmod(os.path.join(ini, 'Fallout.ini'), stat.S_IWRITE | stat.S_IREAD)
