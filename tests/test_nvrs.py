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
    os.makedirs(os.path.dirname(path), exist_ok=True)
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

# A file put in its place since (not FOLab's link any more) is yours: left alone
os.remove(os.path.join(m, 'textures', 'folab', 'hut.dds'))
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
# ---------- folders of mods (OpenMW's launcher's list) ----------
nvrs.take_out(rs)
for f in ('SomeoneElse.esm', os.path.join('textures', 'folab', 'hut.dds')):
    os.remove(os.path.join(m, f))
import shutil  # noqa: E402
shutil.rmtree(os.path.join(m, 'textures'))
lib = os.path.join(home, 'mods library')
a, b = os.path.join(lib, 'A'), os.path.join(lib, 'B')
plugin(os.path.join(a, 'Alpha.esm'), ['FalloutNV.esm', 'HonestHearts.esm'])
plugin(os.path.join(a, 'Spare.esp'), ['FalloutNV.esm'])
write(os.path.join(a, 'Alpha - Main.bsa'), 'bsa')
write(os.path.join(a, 'meshes', 'x.nif'), 'A')
write(os.path.join(a, 'readme.txt'), 'readme')
write(os.path.join(a, 'meta.ini'), '[General]')
write(os.path.join(a, 'fomod', 'ModuleConfig.xml'), 'x')
write(os.path.join(a, 'textures', 'y.dds.mohidden'), 'hidden')
plugin(os.path.join(b, 'Beta.esp'), ['FalloutNV.esm', 'Alpha.esm', 'Nowhere.esm'])
write(os.path.join(b, 'meshes', 'x.nif'), 'B')
write(os.path.join(b, 'nvse', 'plugins', 'thing.dll'), 'dll')
setup = {'folders': [{'path': a}, {'path': b}, {'path': os.path.join(lib, 'gone')}],
         'plugins': [{'name': 'Beta.esp'}, {'name': 'Spare.esp', 'on': False}]}
rows = nvrs.plugin_rows(setup)
check([(r['name'], r['on']) for r in rows] == [('Beta.esp', True), ('Spare.esp', False), ('Alpha.esm', True)],
      "plugins in the setup's order, new ones after: %s" % rows)
check(rows[0]['needs'] == ['Alpha.esm', 'Nowhere.esm'] and rows[2]['needs'] == [],
      'what a plugin needs that nothing above it gives')
mine_txt = os.path.join(m, 'plugins.txt')
write(mine_txt, 'yours')
needs_alpha = os.path.join(build, 'OnAlpha.esp')
plugin(needs_alpha, ['FalloutNV.esm', 'Alpha.esm'])
out = nvrs.put_in(rs, [needs_alpha], setup)
with open(os.path.join(m, 'meshes', 'x.nif')) as f:
    check(f.read() == 'B' and os.path.samefile(os.path.join(m, 'meshes', 'x.nif'), os.path.join(b, 'meshes', 'x.nif')),
          'a later folder wins, and goes in as a link')
check(os.path.isfile(os.path.join(m, 'Alpha - Main.bsa')) and os.path.isfile(os.path.join(m, 'Alpha.esm')) and
      not os.path.exists(os.path.join(m, 'Spare.esp')), "archives and plugins that are on go in; one ticked off doesn't")
check(not any(os.path.exists(os.path.join(m, x)) for x in ('readme.txt', 'meta.ini', 'fomod', os.path.join('textures', 'y.dds'))),
      "a folder's readme, MO2's meta.ini, fomod and hidden files stay out")
with open(mine_txt) as f:
    lines = f.read().split()
check(lines == ['HonestHearts.esm', 'Alpha.esm', 'Beta.esp', 'OnAlpha.esp'],
      'plugins.txt: the DLC they need, masters first, the mod last: %s' % lines)
check(any(open(x).read() == 'yours' for x in out['backups']), 'a plugins.txt of yours went to backups')
check(out['nvse'] == 1 and out['copied'] == 0 and out['linked'] == 5, 'xNVSE plugins counted; the folders linked, none copied: %s' % out)
setup['folders'][1]['on'] = False
setup['plugins'] = [{'name': 'Alpha.esm'}]
nvrs.put_in(rs, [], setup)
with open(os.path.join(m, 'meshes', 'x.nif')) as f:
    check(f.read() == 'A' and not os.path.exists(os.path.join(m, 'Beta.esp')) and not os.path.exists(os.path.join(m, 'nvse')),
          "a folder switched off: its files out, the one under it shows through")
nvrs.put_in(rs, [], {'folders': []})
check(sorted(os.listdir(m)) == ['READ ME.txt', nvrs.MANIFEST], 'no folders: everything FOLab put there is out again (%s)'
      % sorted(os.listdir(m)))
check(os.path.isfile(os.path.join(a, 'meshes', 'x.nif')), 'the folders themselves are untouched')

# from an MO2 profile
import loadout  # noqa: E402
mo = os.path.join(home, 'MO2')
write(os.path.join(mo, 'ModOrganizer.ini'), '[General]\ngameName=New Vegas\ngamePath=%s\n' % os.path.join(home, 'game').replace(os.sep, '/'))
for name, folder in (('A', a), ('B', b)):
    os.makedirs(os.path.join(mo, 'mods'), exist_ok=True)
    os.rename(folder, os.path.join(mo, 'mods', name))
os.makedirs(os.path.join(mo, 'overwrite'), exist_ok=True)
plugin(os.path.join(home, 'game', 'Data', 'FalloutNV.esm'), [])
plugin(os.path.join(home, 'game', 'Data', 'Loose.esp'), ['FalloutNV.esm'])
write(os.path.join(mo, 'profiles', 'P', 'modlist.txt'), '+B\n-Off\n+A\n*DLC: HonestHearts\n')
write(os.path.join(mo, 'profiles', 'P', 'plugins.txt'), '*Alpha.esm\n*Beta.esp\n*Loose.esp\n')
write(os.path.join(mo, 'profiles', 'P', 'loadorder.txt'), 'FalloutNV.esm\nAlpha.esm\nBeta.esp\nLoose.esp\n')
got, data_only = nvrs.from_mo2(loadout.Loadout(loadout.Instance(mo), 'P'))
check([os.path.basename(f['path']) for f in got['folders']] == ['A', 'B', 'overwrite'] and
      [p['name'] for p in got['plugins']] == ['Alpha.esm', 'Beta.esp'] and data_only == ['Loose.esp'],
      'an MO2 profile: its mods lowest first, overwrite last, its plugins; one only in Data listed apart: %s %s' % (got, data_only))

check(install.BACKUPS.startswith(home), 'backups in FOLab\'s scratch home')
