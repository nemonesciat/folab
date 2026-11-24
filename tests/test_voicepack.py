"""The voice pack (voicepack.py): a zip of its own with the voice maker's packages. Found in Downloads, checked (its mark,
this Python, nothing outside its folder), unpacked into FOLab's folder and put on sys.path without a restart; another
Python's pack refused; what the Voice part says in each case. Runs in a fresh FOLAB_HOME with a pretend Downloads."""
import json
import os
import sys
import tempfile
import time
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import voicepack as V  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


home = os.environ.get('FOLAB_HOME') or tempfile.mkdtemp()
os.environ['FOLAB_HOME'] = home
down = tempfile.mkdtemp()

# a pretend package in a pack made the way the build makes it
src = tempfile.mkdtemp()
os.makedirs(os.path.join(src, 'folabpackprobe'))
open(os.path.join(src, 'folabpackprobe', '__init__.py'), 'w').write('HERE = True\n')
os.makedirs(os.path.join(src, '__pycache__'))
open(os.path.join(src, '__pycache__', 'x.pyc'), 'wb').write(b'junk')
zp = V.make(src, os.path.join(down, 'FOLab-voice-pack-0.6.0-test21.zip'), '0.6.0-test21')
names = zipfile.ZipFile(zp).namelist()
check('the pack is one folder with its mark, no compiled leftovers', all(n.startswith('voice pack/') for n in names)
      and 'voice pack/voicepack.json' in names and not any('__pycache__' in n for n in names), names)

real_importable = V.importable
V.importable = lambda: False            # (this Python has numpy: pretend it's FOLab.exe's, which hasn't)
st = V.state(down)
check('missing, but in Downloads: Install is offered', not st['ready'] and st['zip'] == zp and 'Install' in st['why'], st)
empty = tempfile.mkdtemp()
st = V.state(empty)
check('missing and not downloaded: where to get it', not st['ready'] and st['zip'] is None and 'Nexus' in st['why'] and st['page'])

old = os.path.join(down, 'FOLab-voice-pack-0.6.0-test20.zip')
V.make(src, old, '0.6.0-test20')
t = time.time()
os.utime(old, (t - 3600, t - 3600))
check('the newest zip in Downloads is the one', V.found_zip(down) == zp, V.found_zip(down))

got = V.install(downloads=down)
check('installed into FOLab\'s folder', os.path.isfile(os.path.join(home, 'voice pack', 'folabpackprobe', '__init__.py'))
      and got['made_for'] == '0.6.0-test21')
import importlib  # noqa: E402
check('its packages import without a restart', importlib.import_module('folabpackprobe').HERE is True)
check('load() at the next start finds it', V.load() and os.path.abspath(V.folder()) in sys.path)

again = V.install(zp)
check('installed again over itself: the old set aside, then tidied', os.path.isdir(V.folder()) and
      (V.tidy() or not os.path.exists(V.folder() + ' (old)')), again.get('made_for'))

# another Python's pack
other = os.path.join(down, 'other.zip')
with zipfile.ZipFile(other, 'w') as z:
    z.writestr('voice pack/voicepack.json', json.dumps({'python': '3.9', 'made_for': 'x'}))
try:
    V.install(other)
    check('another Python\'s pack is refused', False)
except ValueError as e:
    check('another Python\'s pack is refused', 'another FOLab' in str(e), e)

# anything reaching outside its folder
evil = os.path.join(down, 'evil.zip')
with zipfile.ZipFile(evil, 'w') as z:
    z.writestr('voice pack/voicepack.json', json.dumps({'python': V.python_tag()}))
    z.writestr('voice pack/../../outside.txt', 'x')
try:
    V.install(evil)
    check('a zip reaching outside its folder is refused', False)
except ValueError as e:
    check('a zip reaching outside its folder is refused', not os.path.exists(os.path.join(home, '..', 'outside.txt')), e)

notpack = os.path.join(down, 'notpack.zip')
with zipfile.ZipFile(notpack, 'w') as z:
    z.writestr('something/else.txt', 'x')
try:
    V.install(notpack)
    check('a zip that isn\'t a voice pack is refused', False)
except ValueError as e:
    check('a zip that isn\'t a voice pack is refused', 'isn\'t a FOLab voice pack' in str(e), e)

# a pack for another Python already unzipped into FOLab's folder
json.dump({'python': '3.9'}, open(os.path.join(V.folder(), 'voicepack.json'), 'w'))
st = V.state(empty)
check('an unzipped pack for another FOLab says so', not st['ready'] and 'another FOLab' in st['why'], st['why'])
V.importable = real_importable
