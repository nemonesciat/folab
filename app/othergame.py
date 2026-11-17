"""Things out of another game of the same engine that the user owns, stood in their mod: Fallout 3's aircraft carrier.

New Vegas has no big ship of its own (its largest boat is 22 metres), but Fallout 3's Rivet City is made the same way a
New Vegas building is: statics, in the same mesh format. So a set is read from the other game as that game stands it
(its own plugin says where each piece goes, as landmarks.lift reads New Vegas's), the models and textures those pieces
need are copied from that game's archives into the mod's own files (`projects/<mod> assets/`: only what New Vegas hasn't
got under the same path), a static of the mod's own is made for each model, and the set is stood in the sea at the
height it floats at in its own game.

The copied files are the other game's: this is for the user's own play. A mod holding them isn't one to hand round
(Nexus doesn't take one game's files in another's mod), so `borrowed` lists every file that came this way and
`remove_borrowed` takes them out again. Nothing is read from a game still being installed (Steam's downloading folder).

Not copied here: sounds, scripts, the way in (Rivet City's swing bridge is an activator with a script, its doors lead to
Fallout 3's interiors). The way aboard and somewhere to go into are made of New Vegas's own things, after the ship is
stood: aboard.py."""
import json
import math
import os
import re

import bsa
import gamedata
import library
import nif
import nifwrite
import roadgen

# a set: the other game's plugin and worldspace, which models are its pieces, which are left out
SETS = {
    'carrier': {'label': 'Aircraft carrier', 'game': 'Fallout 3', 'plugin': 'Fallout3.esm', 'world': 'Wasteland',
                'match': r'dungeons\\rivetcity\\exterior\\', 'not': r'bridgebay|exbridge|extbldcor', 'folders': ('Fallout 3 goty', 'Fallout 3')},
}
BESIDE = ('_n', '_g', '_e', '_m', '_s', '_p')    # (a texture's companions: its normal map, glow, and the rest)
NOTE = 'borrowed.json'
OFF_SHORE = 900.0          # (the nearest land is at least this far from the set's outline)
DEEP = -120.0              # (and the sea bed under all of it at least this far under the water)
_other = {}


def find(name):
    """The other game's Data folder for a set, or None: in a Steam library, installed (not while it is still coming down)."""
    spec = SETS[name]
    for lib in gamedata._steam_libraries():
        for folder in spec['folders']:
            d = os.path.join(lib, 'steamapps', 'common', folder, 'Data')
            if os.path.isfile(os.path.join(d, spec['plugin'])):
                return d
    return None


def open_game(name, data_dir=None):
    """The other game, read as New Vegas is: a GameData of its plugin, its archives behind it."""
    d = data_dir or find(name)
    if not d:
        raise FileNotFoundError('%s is not installed in any Steam library on this computer.' % SETS[name]['game'])
    if 'downloading' in os.path.normpath(d).lower().split(os.sep):
        raise FileNotFoundError('%s is still being installed.' % SETS[name]['game'])
    key = (name, os.path.normcase(d))
    if key not in _other:
        _other[key] = gamedata.GameData(d, [SETS[name]['plugin']])
    return _other[key]


def lift(other, name):
    """The set as the other game stands it: {'label', 'pieces': [(editor ID, model, east, north, up from the water, rx, ry,
    rz, scale)], 'box': (x0, y0, x1, y1), 'draught'} round its own middle, or None."""
    spec = SETS[name]
    pat, skip = re.compile(spec['match']), re.compile(spec['not'])
    world = next((w for w in other.worlds() if other.edid(w) == spec['world']), None)
    if world is None:
        return None
    models = {}
    for fid, e in other.forms.items():
        if e[1].tag in ('STAT', 'MSTT', 'ACTI', 'DOOR'):
            _t, edid, _n, model = other.describe(fid)
            m = (model or '').replace('/', '\\').lower()
            if pat.search(m) and not skip.search(m) and not skip.search(edid.lower()):
                models[fid] = (edid, m)
    rows = []
    for cell, w in other.ext_cells.items():
        if w != world:
            continue
        for r in other.refs(cell):
            if r['base'] in models and r['pos']:
                rows.append((models[r['base']], r['pos'], r['rot'] or (0.0, 0.0, 0.0), r['scale'] or 1.0))
    if not rows:
        return None
    ground = roadgen.Ground(other, None, world)
    big = max(rows, key=lambda r: _reach(other, r[0][1]))
    water = ground.water(big[1][0], big[1][1])
    if water is None:
        water = min(r[1][2] for r in rows)
    x0 = y0 = 1e18
    x1 = y1 = low = -1e18
    low = 1e18
    outline = []
    for (edid, model), pos, rot, sc in rows:
        b = _bounds(other, model)
        for cx, cy in ((b[0], b[1]), (b[3], b[1]), (b[3], b[4]), (b[0], b[4])):
            tx, ty = _turn(cx * sc, cy * sc, rot[2])
            outline.append((pos[0] + tx, pos[1] + ty))
        low = min(low, pos[2] + b[2] * sc - water)
    x0, y0 = min(p[0] for p in outline), min(p[1] for p in outline)
    x1, y1 = max(p[0] for p in outline), max(p[1] for p in outline)
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    # (laid along its own length: turned so its longest reach runs east-west, a turn of 0 then means that)
    lie = _long_way([(p[0] - mx, p[1] - my) for p in outline])
    pieces, pts = [], []
    for (edid, model), pos, rot, sc in rows:
        dx, dy = _turn(pos[0] - mx, pos[1] - my, lie)
        pieces.append((edid, model, dx, dy, pos[2] - water, rot[0], rot[1], rot[2] + lie, sc))
    for px, py in outline:
        pts.append(_turn(px - mx, py - my, lie))
    return {'label': spec['label'], 'pieces': pieces, 'draught': round(-low, 1),
            'box': (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))}


def _turn(lx, ly, rz):
    c, s = math.cos(rz), math.sin(rz)
    return lx * c + ly * s, -lx * s + ly * c


def _long_way(pts):
    """The turn that lays a cloud of points with its longest reach along x."""
    best, at = None, 0.0
    for k in range(180):
        a = math.pi * k / 180
        xs = [_turn(x, y, a)[0] for x, y in pts]
        ys = [_turn(x, y, a)[1] for x, y in pts]
        v = (max(ys) - min(ys)) - 1e-6 * (max(xs) - min(xs))
        if best is None or v < best:
            best, at = v, a
    return at


_boxes = {}


def _bounds(other, model):
    key = (id(other), model)
    if key not in _boxes:
        lo, hi = [1e18] * 3, [-1e18] * 3
        try:
            for sh in nif.mesh_from_nif(other.read_file('meshes\\' + model)):
                p = sh['p']
                for k in range(0, len(p), 3):
                    for a in range(3):
                        lo[a] = min(lo[a], p[k + a])
                        hi[a] = max(hi[a], p[k + a])
        except Exception:
            pass
        _boxes[key] = [-64.0, -64.0, 0.0, 64.0, 64.0, 64.0] if hi[0] < lo[0] else lo + hi
    return _boxes[key]


def _reach(other, model):
    b = _bounds(other, model)
    return max(b[3] - b[0], b[4] - b[1])


# ---------- the files ----------

def files_for(other, models):
    """Every file the models need from the other game: {path under Data: where it is to be read (the same path)}: each
    mesh, its far model if it has one, their textures and the textures' companions."""
    out = []
    seen = set()

    def want(rel):
        rel = bsa.norm(rel)
        if rel in seen:
            return None
        seen.add(rel)
        try:
            data = other.read_file(rel)
        except (FileNotFoundError, OSError):
            return None
        out.append(rel)
        return data

    for model in models:
        for rel in ('meshes\\' + model, 'meshes\\' + model[:-4] + '_lod.nif'):
            data = want(rel)
            if data is None:
                continue
            try:
                texs = [t['path'] for t in nifwrite.textures_in(data)]
            except Exception:
                texs = []
            for t in texs:
                t = bsa.norm(t)
                if not t.startswith('textures\\'):
                    t = 'textures\\' + t.split('textures\\')[-1] if 'textures\\' in t else 'textures\\' + t
                want(t)
                stem = t[:-4]
                for suffix in BESIDE:
                    want(stem + suffix + '.dds')
    return out


def _note(pr, value=None):
    """Which of the mod's own files came from another game: kept beside its maps' notes, in a folder (every .json
    directly in projects/ is a mod)."""
    import project
    folder = os.path.join(project.PROJECTS_DIR, pr.name + ' maps')
    path = os.path.join(folder, NOTE)
    if value is None:
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    os.makedirs(folder, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(value, f, indent=1)
    return value


def borrowed(pr):
    """{game: [files of the mod's own that are that game's]}."""
    return _note(pr)


def copy_files(gd, pr, other, rels, game):
    """Copies what New Vegas (and the mod) hasn't got under the same path into the mod's own files. Returns how many."""
    root = library.assets_dir(pr)
    note = _note(pr)
    mine = set(note.get(game, []))
    n = 0
    for rel in rels:
        dest = os.path.join(root, rel)
        if os.path.isfile(dest):
            continue
        try:
            gd.read_file(rel)
            continue                            # (the game has its own under that name: that one is used)
        except (FileNotFoundError, OSError):
            pass
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(other.read_file(rel))
        mine.add(rel)
        n += 1
    note[game] = sorted(mine)
    _note(pr, note)
    return n


def remove_borrowed(pr, game=None):
    """Takes the other game's files out of the mod's own again (before handing the mod to anyone). Returns how many."""
    root = library.assets_dir(pr)
    note = _note(pr)
    n = 0
    for g in [game] if game else list(note):
        for rel in note.pop(g, []):
            p = os.path.join(root, rel)
            if os.path.isfile(p):
                os.remove(p)
                n += 1
    _note(pr, note)
    return n


# ---------- the records and the standing ----------

def _static(edid, model, box):
    clamp = lambda v: int(max(-32000, min(32000, round(v))))
    return {'type': 'STAT', 'flags': 0, 'src': '', 'subs': [
        {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid},
        {'tag': 'OBND', 'label': 'Bounds', 'kind': 'struct', 'fields': [{'name': n, 'code': 'h', 'value': clamp(v)} for n, v in zip(('X1', 'Y1', 'Z1', 'X2', 'Y2', 'Z2'), box)]},
        {'tag': 'MODL', 'label': 'Model', 'kind': 'z', 'value': model}]}


def _mine(pr, edid):
    """The mod's own record of that editor ID, or None."""
    import recordio
    for key, rec in pr.records.items():
        if key.startswith('+') and rec.get('type') == 'STAT' and recordio.field(rec, 'EDID') == edid:
            return key
    return None


def where(gd, pr, world, got, near, turns=8):
    """A place in the sea for a set, as near `near` (x, y) as its whole outline lies over deep water clear of land:
    (x, y, turn) or None."""
    ground = roadgen.Ground(gd, pr, world)
    grid = gd.grid(world)
    x0, y0, x1, y1 = got['box']

    def fits(x, y, a):
        for i in range(13):
            for j in range(5):
                lx, ly = x0 - OFF_SHORE + (x1 - x0 + 2 * OFF_SHORE) * i / 12.0, y0 - OFF_SHORE + (y1 - y0 + 2 * OFF_SHORE) * j / 4.0
                tx, ty = _turn(lx, ly, a)
                px, py = x + tx, y + ty
                inside = x0 <= lx <= x1 and y0 <= ly <= y1
                if (int(px // 4096), int(py // 4096)) not in grid:
                    if inside:
                        return False
                    continue
                z = ground.at(px, py)
                if z is None or z > (DEEP if inside else -8.0):
                    return False
        return True

    step = 1024.0
    for ring in range(0, 60):
        spots = [(near[0], near[1])] if ring == 0 else [(near[0] + math.sin(t) * ring * step, near[1] + math.cos(t) * ring * step) for t in (k * math.tau / (8 * ring) for k in range(8 * ring))]
        for sx, sy in spots:
            for k in range(turns):
                a = math.pi * k / turns
                if fits(sx, sy, a):
                    return sx, sy, a
    return None


def stand(gd, pr, world, name, x, y, turn, other=None, prefix='FOLab'):
    """(ops, report): the set's files copied in, a static for each of its models, and the set stood at x, y turned by
    `turn`, floating as it does in its own game."""
    other = other or open_game(name)
    got = lift(other, name)
    if not got:
        raise ValueError('%s has no %s to take.' % (SETS[name]['game'], SETS[name]['label'].lower()))
    models = sorted({m for _e, m, *_r in got['pieces']})
    rels = files_for(other, models)
    copied = copy_files(gd, pr, other, rels, SETS[name]['game'])
    ground = roadgen.Ground(gd, pr, world)
    water = ground.water(x, y) or 0.0
    grid = gd.grid(world)
    ops, keys = [], {}
    for edid, model, *_r in got['pieces']:
        if edid in keys:
            continue
        mine = _mine(pr, prefix + edid)
        if mine:
            keys[edid] = mine
        else:
            ops.append({'op': 'record_new', 'record': _static(prefix + edid, model.replace('meshes\\', ''), _bounds(other, model)), 'name': 'og_' + edid})
            keys[edid] = '$og_' + edid
    stood = 0
    for edid, _model, dx, dy, dz, rx, ry, rz, sc in got['pieces']:
        tx, ty = _turn(dx, dy, turn)
        px, py = x + tx, y + ty
        cell = grid.get((int(px // 4096), int(py // 4096))) or grid.get((int(x // 4096), int(y // 4096)))
        if cell is None:
            continue
        ops.append({'op': 'add', 'cell': gd.key(cell), 'base': keys[edid],
                    'p': [round(px, 1), round(py, 1), round(water + dz, 1), round(rx, 4), round(ry, 4), round((rz + turn) % math.tau, 4)], 's': round(sc, 3)})
        stood += 1
    return ops, {'set': name, 'label': got['label'], 'x': round(x), 'y': round(y), 'turn': round(turn, 3), 'pieces': stood, 'kinds': len(keys),
                 'files': len(rels), 'copied': copied, 'long': round(got['box'][2] - got['box'][0]), 'wide': round(got['box'][3] - got['box'][1]), 'draught': got['draught']}
