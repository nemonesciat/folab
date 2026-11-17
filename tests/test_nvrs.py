"""Playing a mod in nv-rs: the mod and its own files go in a made-up nv-rs folder's mods folder (never a real one, never
the game's), FOLab takes out only what it put there, and a file of yours it would replace goes to backups first.
Nothing starts: playtest._start is a stand-in."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import install  # noqa: E402
import nvrs  # noqa: E402
import playtest  # noqa: E402
import project  # noqa: E402

started = []
playtest._start = started.append
nvrs.DEFAULT_PLACES = []


def check(ok, what):
    print(('PASS ' if ok else 'FAIL ') + what)


def sub(tag, data):
    return tag.encode() + struct.pack('<H', len(data)) + data


def plugin(path, masters):
    body = sub('HEDR', struct.pack('<fiI', 1.34, 0, 0x800))
    for m in masters:
        body += sub('MAST', m.encode() + b'\0') + sub('DATA', bytes(8))
    with open(path, 'wb') as f:
        f.write(b'TES4' + struct.pack('<IIIIHH', len(body), 0, 0, 0, 15, 0) + body)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(text)


home = project.HOME
rs = os.path.join(home, 'nv-rs')
write(os.path.join(rs, 'Play.exe'), 'x')
write(os.path.join(rs, 'app', 'FalloutNV.exe'), 'x')
write(os.path.join(rs, 'BUILD.txt'), 'nv-rs Windows preview test\nmore')
write(os.path.join(rs, 'mods', 'READ ME.txt'), 'theirs')
check(nvrs.find() is None and nvrs.find(rs) == os.path.normpath(rs) and not nvrs.is_nvrs(home),
      'nv-rs found by its Play.exe and app\\FalloutNV.exe, only where it is')
check(nvrs.version(rs) == 'nv-rs Windows preview test', 'its version from BUILD.txt')

build = os.path.join(home, 'build')
os.makedirs(build, exist_ok=True)
mod = os.path.join(build, 'Isle.esp')
test = os.path.join(build, playtest.TEST_PLUGIN)
plugin(mod, ['FalloutNV.esm', 'DeadMoney.esm'])
plugin(test, ['FalloutNV.esm', 'Isle.esp'])
write(os.path.join(build, 'Isle assets', 'meshes', 'folab', 'hut.nif'), 'hut')
write(os.path.join(build, 'Isle assets', 'textures', 'folab', 'hut.dds'), 'dds')
# a file of yours where the mod's would go
write(os.path.join(rs, 'mods', 'textures', 'folab', 'hut.dds'), 'mine')

out = nvrs.put_in(rs, [mod, test])
m = os.path.join(rs, 'mods')
check(os.path.isfile(os.path.join(m, 'Isle.esp')) and os.path.isfile(os.path.join(m, playtest.TEST_PLUGIN)),
      'the mod and FOLab Test.esp in the mods folder')
check(os.path.getmtime(os.path.join(m, playtest.TEST_PLUGIN)) > os.path.getmtime(os.path.join(m, 'Isle.esp')),
      'FOLab Test.esp dated after the mod (nv-rs orders plugins by date)')
with open(os.path.join(m, 'meshes', 'folab', 'hut.nif')) as f:
    check(f.read() == 'hut', "the mod's own files beside it")
check(len(out['backups']) == 1 and open(out['backups'][0]).read() == 'mine',
      'a file of yours it replaced is in backups: %s' % out['backups'])
check(nvrs.status(rs, home)['mine'] == ['FOLab Test.esp', 'Isle.esp'], 'its status lists what FOLab put in')

# Again without Play here: FOLab Test.esp goes, the mod stays; a file it no longer has goes
os.remove(os.path.join(build, 'Isle assets', 'meshes', 'folab', 'hut.nif'))
nvrs.put_in(rs, [mod])
check(not os.path.exists(os.path.join(m, playtest.TEST_PLUGIN)) and os.path.isfile(os.path.join(m, 'Isle.esp')),
      'a later Open in game takes out the Play here plugin')
check(not os.path.exists(os.path.join(m, 'meshes')), 'a file the mod no longer has is taken out, and its empty folders')

# A file changed since FOLab put it there is yours: left alone
write(os.path.join(m, 'textures', 'folab', 'hut.dds'), 'changed by you')
left = nvrs.take_out(rs)
check(left['left'] == [os.path.join('textures', 'folab', 'hut.dds')] and
      open(os.path.join(m, 'textures', 'folab', 'hut.dds')).read() == 'changed by you',
      'take out leaves a file changed since: %s' % left)
check(not os.path.exists(os.path.join(m, 'Isle.esp')) and os.path.isfile(os.path.join(m, 'READ ME.txt')) and
      not os.path.exists(os.path.join(m, nvrs.MANIFEST)), "take out removes FOLab's, never nv-rs's own")

# A master nv-rs wouldn't have
other = os.path.join(build, 'Needs.esp')
plugin(other, ['FalloutNV.esm', 'SomeoneElse.esm'])
try:
    nvrs.put_in(rs, [other])
    check(False, 'a mod needing a master nv-rs lacks is refused')
except ValueError as e:
    check('SomeoneElse.esm' in str(e) and not os.path.exists(os.path.join(m, 'Needs.esp')),
          'refused before anything goes in: %s' % e)
write(os.path.join(m, 'SomeoneElse.esm'), 'x')
check(nvrs.missing_masters(rs, [other]) == [], "a master you've put in its mods folder counts")

check(nvrs.launch(rs) == 'nv-rs' and started[-1] == [os.path.join(rs, 'Play.exe'), '--mods'],
      'it starts Play with mods (here a stand-in)')
nvrs.import_saves(rs)
check(started[-1] == [os.path.join(rs, 'Play.exe'), '--mods', '--import-saves'], "copying saves in is nv-rs's own Import")
check(install.BACKUPS.startswith(home), 'backups in FOLab\'s scratch home')
