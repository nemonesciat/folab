import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
"""The Library: search and previews on the game's files; a file of your own ends up beside the plugin and goes in and out
of a (fake) Data folder with it; a retextured mesh reads back with only its texture path changed."""
import json
import struct
import tempfile

import dds, espwrite, gamedata, install, library, meshthumb, nif, nifwrite, project, recordio, tes4


def check(what, ok):
    print(('PASS ' if ok else 'FAIL ') + what)


gd = gamedata.GameData()
pr = project.Project.create('Library Test')
gd.overlay = library.Overlay(lambda: pr)
idx = library.Index(gd)

# --- what the game has ---
check('thousands of meshes, textures and sounds', len(idx.paths['mesh']) > 10000 and len(idx.paths['texture']) > 10000 and len(idx.paths['sound']) > 10000)
check('only their own kind', all(p.endswith('.nif') for p in idx.paths['mesh'][:500]) and all(p.endswith(('.wav', '.ogg', '.mp3')) for p in idx.paths['sound']))
hits = idx.search('mesh', 'vault door')
check('search finds every word, anywhere in the path', hits and all('vault' in p and 'door' in p for p in hits))
chairs = idx.search('mesh', 'chair')
name_first = [('chair' in p.rsplit('\\', 1)[1]) for p in chairs]
check('file names that match come first', name_first == sorted(name_first, reverse=True))
subs, here = idx.folder('mesh', 'meshes\\furniture')
check('a folder lists its files and folders', here and all(p.startswith('meshes\\furniture\\') and p.count('\\') == 2 for p in here))
top, _ = idx.folder('mesh', '')
check('folders count what\'s under them', sum(f['n'] for f in top) == len(idx.paths['mesh']))

# --- pictures of them, kept ---
tex = next(p for p in idx.paths['texture'] if p.endswith('.dds') and 'clutter' in p)
png = library.thumb(gd, tex, 64)
w, h, px = meshthumb.read_png(png)
check('a texture\'s picture is a real picture', max(w, h) >= 64 and len(set(px[i] for i in range(0, len(px), 4))) > 4)
mesh = next(p for p in hits if gd.read_file(p) and nif.mesh_from_nif(gd.read_file(p)))
png = library.thumb(gd, mesh, 96)
w, h, px = meshthumb.read_png(png)
solid = sum(1 for i in range(3, len(px), 4) if px[i] > 128)
check('a mesh\'s picture shows something on nothing', (w, h) == (96, 96) and 300 < solid < 96 * 96)
kept = library.thumb_path(gd, mesh, 96)
check('kept in FOLab\'s cache folder', os.path.isfile(kept) and kept.startswith(os.path.join(project.HOME, 'cache', 'thumbs')))
stamp = os.path.getmtime(kept)
library.thumb(gd, mesh, 96)
check('and not drawn twice', os.path.getmtime(kept) == stamp)

# --- pictures brought in ---
w, h = 8, 8
rgba = bytes(v for y in range(h) for x in range(w) for v in (x * 30, y * 30, 200, 255))
pic = meshthumb.png_rgba(w, h, rgba)
check('a PNG reads back', meshthumb.read_png(pic) == (w, h, rgba))
made = dds.encode(w, h, rgba)
i = dds.info(made)
check('a DDS from it has every smaller copy', i['w'] == 8 and i['mips'] == 4)
check('and holds the picture', dds.decode(made, 8) == (w, h, rgba))
check('and the game\'s size of file', len(made) == 128 + (64 + 16 + 4 + 1) * 4)
tga = bytes([0, 0, 2]) + b'\0' * 9 + struct.pack('<HHBB', 2, 1, 32, 0x20) + bytes((1, 2, 3, 4, 5, 6, 7, 8))
check('a TGA reads', meshthumb.read_tga(tga) == (2, 1, bytes((3, 2, 1, 4, 7, 6, 5, 8))))
bmp = b'BM' + b'\0' * 8 + struct.pack('<IIiiHHI', 54, 40, 1, 1, 1, 24, 0) + b'\0' * 20 + bytes((9, 8, 7, 0))
check('a BMP reads', meshthumb.read_bmp(bmp) == (1, 1, bytes((7, 8, 9, 255))))

# --- a mesh of your own, with its picture, in a click ---
src = gd.read_file(mesh)
names = nifwrite.textures_in(src)
first = names[0]['path']
stem = os.path.splitext(first.replace('/', '\\').rsplit('\\', 1)[1])[0]
out = library.bring(gd, pr, [('C:\\somewhere\\My Crate.nif', src), (stem + '.png', pic), ('notes.txt', b'hello')])
check('brought in: the mesh and its picture', sorted(m['kind'] for m in out['made']) == ['mesh', 'texture'])
check('told what was left out', any('notes.txt' in w for w in out['warnings']))
own_mesh = next(m['path'] for m in out['made'] if m['kind'] == 'mesh')
own_tex = next(m['path'] for m in out['made'] if m['kind'] == 'texture')
me = library.slug(pr.name)
check('kept under the mod\'s own folders', own_mesh == 'meshes\\folab\\%s\\my_crate.nif' % me and own_tex.startswith('textures\\folab\\%s\\' % me))
check('kept in the mod\'s folder', os.path.isfile(os.path.join(project.PROJECTS_DIR, pr.name + ' assets', own_mesh)))
got = {t['path'] for t in nifwrite.textures_in(gd.read_file(own_mesh))}
check('the mesh is pointed at the picture that came with it', own_tex in got)
check('its other textures are left', all(p == own_tex or p != first for p in got))
check('the view sees it as a game file', gd.find_file(own_mesh) == 'your mod' and own_mesh[7:] in gd.mesh_list())
check('nothing written over: a second one gets its own name', library.bring(gd, pr, [('My Crate.nif', src)])['made'][0]['path'] == own_mesh[:-4] + '_2.nif')
bad = library.bring(gd, pr, [('junk.nif', b'not a mesh at all'), ('junk.dds', b'nope')])
check('what isn\'t a mesh or picture stays out', not bad['made'] and len(bad['warnings']) == 2)

# --- a record from it, in the plugin ---
rec = library.record_for_mesh(gd, own_mesh, 'STAT', 'FOLabMyCrate')
b = library.bounds_of(gd.read_file(own_mesh))
check('the record has the mesh\'s bounds', [f['value'] for f in next(s for s in rec['subs'] if s['tag'] == 'OBND')['fields']] == b)
misc = library.record_for_mesh(gd, own_mesh, 'MISC', 'FOLabMyItem', 'My item')
check('an item is modelled on a plain one', recordio.field(misc, 'FULL') == 'My item' and recordio.field(misc, 'MODL') == own_mesh[7:] and not any(s['tag'] in ('SCRI', 'MODT') for s in misc['subs']))
made = pr.apply('make', [{'op': 'record_new', 'record': rec}, {'op': 'record_new', 'record': misc}])
built = pr.plugin_path()
espwrite.write(gd, pr, built)
library.publish(pr)
beside = os.path.join(project.BUILD_DIR, 'Library Test assets', own_mesh)
check('an own asset ends up beside the plugin', os.path.isfile(beside) and os.path.dirname(built) == project.BUILD_DIR)
gd2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [built])
me2 = len(gd2.plugins) - 1
stat = next(f for f, (i, r) in gd2.forms.items() if i == me2 and r.tag == 'STAT')
check('the plugin\'s static names the mesh', gd2.describe(stat)[3] == own_mesh[7:] and struct.unpack('<6h', gd2.fields(stat)['OBND']) == tuple(b))
check('the plugin\'s item reads back', any(i == me2 and r.tag == 'MISC' and gd2.edid(f) == 'FOLabMyItem' for f, (i, r) in gd2.forms.items()))
for p in gd2.plugins:
    p.close()

# --- in and out of a fake game ---
fake = tempfile.mkdtemp(prefix='folab-data-')
os.environ['LOCALAPPDATA'] = tempfile.mkdtemp(prefix='folab-local-')
install.install(fake, built)
inside = os.path.join(fake, own_mesh)
check('it goes in the game with the plugin', os.path.isfile(inside) and os.path.isfile(os.path.join(fake, own_tex)) and os.path.isfile(os.path.join(fake, pr.plugin)))
check('status: in, and current', install.status(fake, pr.plugin)['current'])
library.bring(gd, pr, [('Later.png', pic)])
library.publish(pr)
check('status: a new file makes it out of date', not install.status(fake, pr.plugin)['current'])
library.remove_own(gd, pr, 'textures\\folab\\%s\\later.dds' % me)
library.publish(pr)
try:
    library.remove_own(gd, pr, own_mesh)
    check('a mesh a record uses can\'t be taken out', False)
except ValueError:
    check('a mesh a record uses can\'t be taken out', True)
try:
    library.remove_own(gd, pr, '..\\..\\outside.txt')
    check('only the mod\'s own files can be taken out', False)
except FileNotFoundError:
    check('only the mod\'s own files can be taken out', True)
elsewhere = os.path.join(fake, 'meshes', 'mine.nif')
with open(elsewhere, 'wb') as f:
    f.write(b'someone else\'s')
install.uninstall(fake, pr.plugin)
check('taken out with the plugin', not os.path.exists(inside) and not os.path.exists(os.path.join(fake, pr.plugin)))
check('and nothing else', os.path.isfile(elsewhere))
game_plugin = os.path.join(fake, 'Other.esp')

# --- retexturing: only the path changes ---
sample = [p for p in idx.paths['mesh'][::160]]
checked = changed = 0
wrong = {}
for p in sample:
    d = gd.read_file(p)
    w = nifwrite.prove(d)
    if nifwrite.textures_in(d):
        changed += 1
    checked += 1
    if w:
        wrong[p] = w
check('%d game meshes (%d with textures): only their texture paths change' % (checked, changed), checked > 100 and changed > 50 and not wrong)
if wrong:
    print(list(wrong.items())[:5])
d = gd.read_file(mesh)
old = nifwrite.textures_in(d)[0]['path']
new = nifwrite.retexture(d, {old: 'textures\\folab\\test\\new.dds'})
a, c = nif.mesh_from_nif(d), nif.mesh_from_nif(new)
check('the view draws the new picture', any(s['tex'] == 'textures\\folab\\test\\new.dds' for s in c) and not any(s['tex'].lower() == old.lower() for s in c))
check('and the same shape', [s['p'] for s in a] == [s['p'] for s in c] and [s['uv'] for s in a] == [s['uv'] for s in c] and [s['i'] for s in a] == [s['i'] for s in c])
check('nothing to change: the same bytes', nifwrite.retexture(d, {}) == bytes(d) and nifwrite.retexture(d, {'textures\\none.dds': 'x'}) == bytes(d))
check('longer and shorter paths both fit', not nifwrite.prove(d, {old: 'a.dds'}) and not nifwrite.prove(d, {old: 'textures\\' + 'long\\' * 60 + 'b.dds'}))
out_rel = library.retexture_mesh(gd, pr, mesh, {old: own_tex}, 'crate red')
check('a retextured copy is kept with the mod', out_rel == 'meshes\\folab\\%s\\crate_red.nif' % me and own_tex in {t['path'] for t in nifwrite.textures_in(gd.read_file(out_rel))})
check('and the game\'s mesh isn\'t touched', gd.read_file(mesh) == d and gd.find_file(mesh) != 'your mod')
# one that shares a string table entry: an NiSourceTexture
src_tex = next((p for p in idx.paths['mesh'] if b'NiSourceTexture' in gd.read_file(p)[:4096] and any(t['kind'] == 'NiSourceTexture' for t in nifwrite.textures_in(gd.read_file(p)))), None)
if src_tex:
    check('a texture named through the string table changes too', not nifwrite.prove(gd.read_file(src_tex)))
