"""A world FOLab writes is laid out as every one of the game's is (what the GECK expects of a file): all land stored
compressed, the world's persistent cell with a persistent group in its children, no outside cell without the has-water
flag and a level, no empty children group. And a world an earlier FOLab wrote the old way is brought into line the
next time its mod is saved, with nothing else in it changed."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import espwrite  # noqa: E402
import gamedata  # noqa: E402
import land  # noqa: E402
import plugintree  # noqa: E402
import project  # noqa: E402
import tes4  # noqa: E402
import worldgen  # noqa: E402


def check(what, ok, detail=''):
    print(('PASS ' if ok else 'FAIL ') + what + (' (%s)' % (detail,) if detail != '' else ''))


def survey(path):
    """What the file's worlds hold: {'land': [flags], 'grid': [(DATA byte, XCLW or None, children kinds or None)],
    'persistent': [children kinds or None]}"""
    out = {'land': [], 'grid': [], 'persistent': [], 'heights': []}
    tree = plugintree.Plugin.read(path)
    wtop = next(g for g in tree.tops if g.label == plugintree.type_label('WRLD'))

    def kinds(g):
        return [k.gtype if isinstance(k, plugintree.Group) else k.tag for k in g.kids]

    def walk(kids, grid):
        for n, k in enumerate(kids):
            if isinstance(k, plugintree.Group):
                if k.gtype in (tes4.G_EXT_BLOCK, tes4.G_EXT_SUBBLOCK, tes4.G_WORLD_CHILDREN):
                    walk(k.kids, k.gtype != tes4.G_WORLD_CHILDREN)
                continue
            if k.tag != 'CELL':
                continue
            nxt = kids[n + 1] if n + 1 < len(kids) else None
            ch = nxt if isinstance(nxt, plugintree.Group) and nxt.gtype == tes4.G_CELL_CHILDREN else None
            f = dict(tes4.iter_subrecords(k.data()))
            if grid:
                out['grid'].append((f['DATA'][0], struct.unpack('<f', f['XCLW'])[0] if 'XCLW' in f else None, kinds(ch) if ch else None))
            else:
                out['persistent'].append(kinds(ch) if ch else None)
            for g in (ch.kids if ch else []):
                for r in (g.kids if isinstance(g, plugintree.Group) else []):
                    if isinstance(r, plugintree.Rec) and r.tag == 'LAND':
                        out['land'].append(r.flags)
                        out['heights'].append((struct.unpack_from('<ii', f['XCLC']), land.heights_of(dict(tes4.iter_subrecords(r.data()))['VHGT'])))
    walk(wtop.kids, False)
    return out


def as_game(s):
    return (all(fl & tes4.COMPRESSED for fl in s['land']) and all(d & 2 and w is not None for d, w, _k in s['grid'])
            and all(k is None or k for _d, _w, k in s['grid']) and all(k and tes4.G_CELL_PERSISTENT in k for k in s['persistent']))


gd = gamedata.GameData()
mojave = next(w for w in gd.worlds() if gd.edid(w) == 'WastelandNV')
ltex = next(gd.key(f) for f, (i, r) in gd.forms.items() if r.tag == 'LTEX' and gd.edid(f) == 'DirtBarrenWastes01')

# ---------- the game's own, by the same survey (so the test's idea of "as the game" is the game's) ----------
hh = survey(os.path.join(gd.data_dir, 'HonestHearts.esm'))
check('the game: every land compressed, every cell with water, every persistent cell with its group', as_game(hh) and len(hh['land']) > 4000)

# ---------- a new world: flat, and one with dry and wet cells ----------
pr = project.Project.create('As Game')
path = pr.plugin_path()
wr = espwrite.Writer(gd, pr)
wr.force_all = True
with open(path, 'wb') as f:
    f.write(wr.build())
tree = plugintree.Plugin.read(path)
wid, nid = worldgen.add_world(gd, tree, wr, pr.next_id, {'edid': 'AsGameFlat', 'name': 'Flat', 'template': mojave, 'size': 4, 'height': 3000, 'ltex': ltex})
shape = lambda x, y: {'h': [float(200 + 8 * ((k % 33) % 5)) if x >= 0 else -64.0 for k in range(1089)], 'c': 'ff' * 3267,
                      'q': [{'bkey': ltex, 'base': None, 'layers': []} for _ in range(4)]}
wid2, nid = worldgen.add_world(gd, tree, wr, nid, {'edid': 'AsGameShaped', 'name': 'Shaped', 'template': mojave, 'ltex': ltex, 'rect': (-2, -2, 4, 4),
                                                   'height': -64.0, 'water': 0.0, 'land_for': lambda x, y: (shape(x, y), None),
                                                   'wet': lambda x, y: x < 0})
worldgen.fix_header(tree, wr.own(nid))
with open(path, 'wb') as f:
    f.write(tree.bytes())
s = survey(path)
check('new worlds: 32 cells, each with land', len(s['grid']) == 32 and len(s['land']) == 32)
check('all their land is stored compressed', all(fl & tes4.COMPRESSED for fl in s['land']))
check('every cell has the has-water flag and a level', all(d & 2 and w is not None for d, w, _k in s['grid']))
dry = sorted({w for _d, w, _k in s['grid'] if w < 1e30})
check('a cell with no water to see has its own level far under the lowest land', dry == [-64.0 - espwrite.DRY_BELOW], dry)
check('each world\'s persistent cell has a persistent group', s['persistent'] == [[tes4.G_CELL_PERSISTENT]] * 2, s['persistent'])
check('laid out as the game\'s are', as_game(s))
g2 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [path])
w2 = next(w for w in g2.worlds() if g2.edid(w) == 'AsGameFlat')
check('FOLab reads the compressed land back', set(land.decode(g2, g2.land_at(w2, 0, 0), {})['h']) == {3000.0})
for p in g2.plugins:
    p.close()

# ---------- a world as earlier FOLabs wrote it: brought into line on the next save ----------
old = plugintree.Plugin.read(path)
n_land = n_dry = n_empty = 0


def age(kids, grid):
    """Undo each of the three, as test 13 and before wrote them."""
    global n_land, n_dry, n_empty
    for n, k in enumerate(kids):
        if isinstance(k, plugintree.Group):
            if k.gtype in (tes4.G_EXT_BLOCK, tes4.G_EXT_SUBBLOCK, tes4.G_WORLD_CHILDREN):
                age(k.kids, k.gtype != tes4.G_WORLD_CHILDREN)
            elif k.gtype == tes4.G_CELL_CHILDREN:
                if not grid:
                    k.kids[:] = [g for g in k.kids if not (isinstance(g, plugintree.Group) and g.gtype == tes4.G_CELL_PERSISTENT and not g.kids)]
                    n_empty += 1
                for g in k.kids:
                    for r in g.kids:
                        if r.tag == 'LAND':
                            r.set_data(r.data(), r.flags)
                            n_land += 1
        elif k.tag == 'CELL' and grid:
            subs = list(tes4.iter_subrecords(k.data()))
            if any(t == 'XCLW' and struct.unpack('<f', d)[0] < -1000 for t, d in subs):
                k.set_data(espwrite.join([(t, bytes([d[0] & ~2]) + d[1:] if t == 'DATA' else d) for t, d in subs if t != 'XCLW']), k.flags)
                n_dry += 1


age(next(g for g in old.tops if g.label == plugintree.type_label('WRLD')).kids, False)
folder = os.path.join(project.PROJECTS_DIR, 'As Game source')
os.makedirs(folder, exist_ok=True)
src = os.path.join(folder, pr.plugin)
with open(src, 'wb') as f:
    f.write(old.bytes())
before = survey(src)
check('the old way: land not compressed, dry cells with no water at all, an empty children group',
      n_land == 32 and n_dry == 8 and n_empty == 2 and not as_game(before) and not any(fl & tes4.COMPRESSED for fl in before['land']))
import json  # noqa: E402
d = pr.to_dict()
d.update(source='As Game source/' + pr.plugin, next_id=nid, trim_masters=True)
with open(pr.path, 'w', encoding='utf-8') as f:
    json.dump(d, f)
pr2 = project.Project.open('As Game')
g3 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [pr2.source_path()])
out = pr2.plugin_path()
espwrite.write(g3, pr2, out)
for p in g3.plugins:
    p.close()
after = survey(out)
check('saved again: laid out as the game\'s are', as_game(after), (after['persistent'], set(after['land'])))
check('its dry cells have their far-down level again', sorted({w for _d, w, _k in after['grid'] if w < 1e30}) == dry)
check('and not a height of its land has changed', after['heights'] == before['heights'] and len(after['heights']) == 32)
again = out + '.again'
os.replace(out, src)
g4 = gamedata.GameData(plugins=list(gamedata.OFFICIAL) + [src])
espwrite.write(g4, pr2, again)
for p in g4.plugins:
    p.close()
with open(src, 'rb') as a, open(again, 'rb') as b:
    check('a world already right is written back byte for byte', a.read() == b.read())

# ---------- a master file lists what it changes of other files' placed things (ONAM), as the game's DLCs do ----------
pm = project.Project.create('As Master')
saloon = next(c for c in gd.interiors if gd.edid(c) == 'GSProspectorSaloonInterior')
moved = [r for r in gd.refs(saloon) if gd.cell_refs[saloon][r['ref']][1].tag == 'REFR'][:3]
pm.apply('move', [{'op': 'move', 'cell': gd.key(saloon), 'ref': gd.key(r['ref']), 'p': [r['pos'][0] + 8] + list(r['pos'][1:]) + list(r['rot'])} for r in moved])


def onam(p):
    t = plugintree.Plugin.read(p)
    d = next((d for tag, d in tes4.iter_subrecords(t.header.raw) if tag == 'ONAM'), None)
    return None if d is None else list(struct.unpack('<%dI' % (len(d) // 4), d))


espwrite.write(gd, pm, pm.plugin_path())
check('a plugin (.esp) lists nothing', onam(pm.plugin_path()) is None)
pm.esm = True
out_m = pm.plugin_path()
espwrite.write(gd, pm, out_m)
check('saved as a master: the three things it moved are listed', sorted(onam(out_m) or []) == sorted(r['ref'] for r in moved), onam(out_m))
gm = gamedata.GameData(plugins=['FalloutNV.esm', out_m])
check('and the file still reads, the things moved', all(abs(next(x for x in gm.refs(saloon) if x['ref'] == r['ref'])['pos'][0] - r['pos'][0] - 8) < 0.01 for r in moved))
for p in gm.plugins:
    p.close()
