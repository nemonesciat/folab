"""Distant land: the game's own terrain chunks rebuilt byte for byte; the settings file sized as the game's are; a chunk of a
new world's land, its textures running the way the game's do; in and out of a fake Data folder. No real game."""
import math
import os
import struct
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import gamedata
import lodgen
import maptiles
import nif
import project
import roadgen

BS = chr(92)


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % detail if detail else ''))


G = gamedata.GameData()


def chunks(world):
    pre = BS.join(['meshes', 'landscape', 'lod', world.lower(), ''])
    return sorted({n for a in G.archives() for n in a.files if n.startswith(pre) and BS + 'blocks' + BS not in n and n.endswith('.nif')})


for wn in ('FreesideNorthWorld', 'NVDLC01VillaDean'):
    names = chunks(wn)
    same = 0
    for n in names:
        d = G.read_file(n)
        parts = n.rsplit(BS, 1)[-1].split('.')
        L, x, y = int(parts[1][5:]), int(parts[2][1:]), int(parts[3][1:])
        v, u, t, c = lodgen.read_terrain_nif(d)
        i = d.find(b'Data' + bytes([92]) + b'Textures')
        path = d[i:i + struct.unpack_from('<I', d, i - 4)[0]].decode()
        same += lodgen.terrain_nif(path.split(BS)[4], L, x, y, v, u, t, c) == d
    check('%s: all %d terrain chunks rebuilt byte for byte' % (wn, len(names)), same == len(names) and names, '%d of %d' % (same, len(names)))

# settings: the same sums as the game's
for wn in ('WastelandNV', 'WastelandNVmini', 'GamorrahWorld', 'FreesideNorthWorld', 'NVDLC02ZionCanyon'):
    have = G.read_file(BS.join(['lodsettings', wn.lower() + '.dlodsettings']))
    a = struct.unpack('<3I4hI', have[:24])
    # (from its box, as stored)
    mine = struct.unpack('<3I4hI', lodgen.settings_bytes(a[3:7]))
    check('%s: settings as the game has them, from its box' % wn, mine == a, '%r %r' % (mine, a))

# a chunk's chunks, counted from the south-west corner
got = lodgen.chunks_for((-9, -7, 5, 11), 8)
pre = BS.join(['meshes', 'landscape', 'lod', 'freesidenorthworld', ''])
game = {n[len(pre):] for n in chunks('FreesideNorthWorld')}
ours = {'freesidenorthworld.level%d.x%d.y%d.nif' % c for c in got}
check('the chunks of a world are those the game has for it', ours == game, str(sorted(ours ^ game)[:4]))

# textures: DXT1 written and read back
px = [(x, y, 128) for y in range(0, 256, 8) for x in range(0, 256, 8)]
px = [(r, g, b) for r, g, b in px]
d = lodgen.dds_dxt1(px, 32)
w, h, back = lodgen.decode_dxt1(d)
game_tex = G.read_file(BS.join(['textures', 'landscape', 'lod', 'freesidenorthworld', 'diffuse', 'freesidenorthworld.n.level4.x3.y1.dds']))
check('the DDS header is as the game\'s (flags, mip count, format)', d[:4] == b'DDS ' and struct.unpack_from('<2I', d, 4)[1] == struct.unpack_from('<2I', game_tex, 4)[1] and d[84:88] == b'DXT1' and struct.unpack_from('<I', d, 28)[0] == 6, '%x %x' % (struct.unpack_from('<I', d, 8)[0], struct.unpack_from('<I', game_tex, 8)[0]))
check('… a picture size the game\'s are: 256 with mips is its length', len(lodgen.dds_dxt1([(1, 2, 3)] * (256 * 256), 256)) == len(game_tex), '%d %d' % (len(lodgen.dds_dxt1([(1, 2, 3)] * (256 * 256), 256)), len(game_tex)))
err = max(abs(a[k] - b[k]) for a, b in zip(px, back) for k in range(3))
check('… and comes back near what went in', err < 48, str(err))

# a chunk from land: its height and normals run as the game's own do
W = next(x for x in G.worlds() if G.edid(x) == 'FreesideNorthWorld')
pr = project.Project.create('Far Land')
S = lodgen.Sampler(G, pr, W, maptiles.Painter(G))
cx, cy = -1, 1
v, u, t = lodgen.chunk_mesh(S, 4, cx, cy)
check('a chunk\'s mesh: 65 x 65 and a skirt', len(v) == 65 * 65 + 256 and sum(1 for p in v if p[2] == lodgen.SKIRT_Z) == 256)
data = lodgen.terrain_nif('FreesideNorthWorld', 4, cx, cy, v, u, t)
v2, u2, t2, _c = lodgen.read_terrain_nif(data)
check('it reads back whole', len(v2) == len(v) and len(t2) == len(t) and abs(v2[100][2] - v[100][2]) < 0.01)
parts = nif.mesh_from_nif(data)
check('FOLab\'s own mesh reader takes it too', parts and len(parts[0]['i']) // 3 == len(t), str(len(parts)))
gv, _gu, _gt, _gc = lodgen.read_terrain_nif(G.read_file(pre + 'freesidenorthworld.level4.x-1.y1.nif'))
err = [abs(p[2] - S.height(cx * 4096 + p[0], cy * 4096 + p[1])) for p in gv if p[2] != lodgen.SKIRT_Z]
check('the game\'s chunk stands on the land we sample', sum(err) / len(err) < 64, str(round(sum(err) / len(err), 1)))
d, n = lodgen.chunk_textures(S, 4, cx, cy)
gd_tex = G.read_file(BS.join(['textures', 'landscape', 'lod', 'freesidenorthworld', 'normals', 'freesidenorthworld.n.level4.x-1.y1.dds']))
_w, _h, gn = lodgen.decode_dxt1(gd_tex)
_w, _h, mn = lodgen.decode_dxt1(n)


def corr(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    na, nb = math.sqrt(sum((p - ma) ** 2 for p in a)), math.sqrt(sum((q - mb) ** 2 for q in b))
    return sum((p - ma) * (q - mb) for p, q in zip(a, b)) / (na * nb or 1)


idx = list(range(0, 256 * 256, 37))
check('our normals follow the game\'s: red', corr([gn[i][0] for i in idx], [mn[i][0] for i in idx]) > 0.6, str(round(corr([gn[i][0] for i in idx], [mn[i][0] for i in idx]), 2)))
check('… green', corr([gn[i][1] for i in idx], [mn[i][1] for i in idx]) > 0.6, str(round(corr([gn[i][1] for i in idx], [mn[i][1] for i in idx]), 2)))
_w, _h, gd_c = lodgen.decode_dxt1(G.read_file(BS.join(['textures', 'landscape', 'lod', 'freesidenorthworld', 'diffuse', 'freesidenorthworld.n.level4.x-1.y1.dds'])))
_w, _h, md_c = lodgen.decode_dxt1(d)
bri = lambda p: p[0] + p[1] + p[2]
print('# diffuse: game %r, ours %r, correlation %.2f' % (gd_c[30000], md_c[30000], corr([bri(gd_c[i]) for i in idx], [bri(md_c[i]) for i in idx])))
check('our colours follow the game\'s', corr([bri(gd_c[i]) for i in idx], [bri(md_c[i]) for i in idx]) > 0.2, str(round(corr([bri(gd_c[i]) for i in idx], [bri(md_c[i]) for i in idx]), 2)))

# a whole small world in a folder
class Small:
    """A world of the game's with a fake box, so this stays quick."""
out = os.path.join(project.HOME, 'lod')
orig = lodgen.world_box
lodgen.world_box = lambda gd, world: (0, 0, 3, 3)
real_find = G.find_file
G.find_file = lambda rel: None if 'dlodsettings' in rel else real_find(rel)      # (as a new world has none)
rep = lodgen.generate(G, pr, W, out)
G.find_file = real_find
lodgen.world_box = orig
check('a new world: one chunk, three files and its settings', rep['chunks'] == 1 and rep['files'] == 4 and rep['settings_written'], str(rep))
stem = BS.join(['meshes', 'landscape', 'lod', 'FreesideNorthWorld', 'FreesideNorthWorld.level4.x0.y0.nif']).replace(BS, os.sep)
check('… laid out as Data is', os.path.isfile(os.path.join(out, stem)) and os.path.isfile(os.path.join(out, 'lodsettings', 'FreesideNorthWorld.dlodsettings')))

# only what changed, on a world of the game's
rep2 = lodgen.generate(G, pr, W, os.path.join(project.HOME, 'lod2'))
check('a game world with no land changed: nothing to make', rep2['chunks'] == 0 and rep2.get('note'))
c0 = G.grid(W)[(-1, 1)]
pr.land[G.key(c0)] = {'h': [1000.0] * 1089, 'c': None, 'q': lodgen.land.decode(G, G.land[c0], {})['q']}
got2 = lodgen.chunks_for((-9, -7, 5, 11), 8, {(-1, 1)})
check('a changed cell: the chunks over it, one at each level', sorted(got2) == [(4, -1, 1), (8, -1, 1)], str(got2))
del pr.land[G.key(c0)]
rp = lodgen.report_for(G, pr, W)
check('the report says what\'s there', rp['game_terrain'] >= 26 and rp['game_objects'] >= 1 and rp['settings'] and rp['all_chunks'] == 26, str(rp))

# in and out of a fake Data
fake = os.path.join(project.HOME, 'fake data')
os.makedirs(os.path.join(fake, 'lodsettings'))
was = os.path.join(fake, 'lodsettings', 'FreesideNorthWorld.dlodsettings')
with open(was, 'wb') as f:
    f.write(b'theirs')
n = lodgen.install(pr, fake, out)
check('into a fake Data: all its files', n == 4 and os.path.isfile(os.path.join(fake, stem)))
with open(was, 'rb') as f:
    check('… over what was there', f.read() != b'theirs')
n = lodgen.uninstall(pr, fake)
with open(was, 'rb') as f:
    check('taken out: what it replaced is back', f.read() == b'theirs')
check('… and what it added is gone', not os.path.exists(os.path.join(fake, stem)))
