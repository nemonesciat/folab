"""FOLab's local web server: the editor page and a small JSON API over the game's data and the open project.

    py -3 server.py [port] [--no-browser]        opens http://127.0.0.1:8771/ when ready

Game files are only read. Projects live in FOLab's projects folder; Save writes the plugin to FOLab's build folder,
and Install (the user's choice) copies it into the game."""
import json
import platform
import traceback
import os
import struct
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import espwrite
import gamedata
import gameini
import install
import kitindex
import navbuild
import nif
import nvse
import playtest
import project
import actors
import adopt
import api_scripts
import browse
import recordio
import base64
import hashlib
import autopaint
import heightmap
import plugintree
import shutil
import worldgen
import landshape
import land
import maptiles
import re
import refinfo
import scatter
import tes4
from version import VERSION

PORT = 8771
WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
SETTINGS = os.path.join(project.HOME, 'folab_settings.json')
TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css',
         '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.txt': 'text/plain',
         '.woff2': 'font/woff2', '.md': 'text/markdown; charset=utf-8', '.ttf': 'font/ttf'}
# What the Place panel offers, with the names it shows
PLACEABLE = {'STAT': 'Statics', 'MSTT': 'Movable statics', 'FURN': 'Furniture', 'CONT': 'Containers',
             'DOOR': 'Doors', 'LIGH': 'Lights', 'MISC': 'Items', 'ACTI': 'Activators', 'TACT': 'Talking activators',
             'TERM': 'Terminals', 'BOOK': 'Books', 'NOTE': 'Notes', 'WEAP': 'Weapons', 'ARMO': 'Apparel',
             'ALCH': 'Aid', 'AMMO': 'Ammo', 'KEYM': 'Keys', 'IDLM': 'Idle markers', 'PWAT': 'Placeable water',
             'ADDN': 'Addon nodes', 'IMOD': 'Weapon mods', 'CHIP': 'Chips', 'CMNY': 'Caravan money',
             'CCRD': 'Caravan cards', 'NPC_': 'Characters', 'CREA': 'Creatures'}
ACTORS = {'NPC_', 'CREA'}

GD = None
PR = None
BR = None
CATALOGUE = []                          # [key, type, edid, name, model] of every placeable game object
_meshes = {}
_land_tex = {}                          # LTEX -> its picture (land.py)
_tiles = {}                             # (world, tx, ty, the mod's land there) -> PNG
_painter = None
_markers = None                         # every worldspace's map markers, for Go to a place
_actors = {}                            # base key -> parts (actors.py)
_lock = threading.RLock()


def load_settings():
    try:
        with open(SETTINGS, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(**kw):
    s = load_settings()
    s.update(kw)
    with open(SETTINGS, 'w', encoding='utf-8') as f:
        json.dump(s, f, indent=1)


def is_marker(btype, edid, model):
    """Editor-only things the game never draws."""
    m = model.lower()
    return btype == 'STAT' and ('marker' in edid.lower() or m.startswith(('marker', 'editor')))


def build_catalogue():
    out = []
    for fid, (i, rec) in GD.forms.items():
        if rec.tag not in PLACEABLE:
            continue
        btype, edid, name, model = GD.describe(fid)
        if btype in ACTORS:
            out.append([GD.key(fid), btype, edid, name, ''])
            continue
        if not model or is_marker(btype, edid, model):
            continue
        out.append([GD.key(fid), btype, edid, name, GD.model_path(btype, model)])
    out.sort(key=lambda x: x[2].lower())
    return out


# --- places and things ---

def interiors():
    out = []
    changed = set(PR.cells) if PR else set()
    for c in GD.interiors:
        f = GD.fields(c)
        k = GD.key(c)
        out.append({'id': k, 'edid': tes4.zstr(f.get('EDID', b'')), 'name': tes4.zstr(f.get('FULL', b'')),
                    'refs': len(GD.cell_refs.get(c, ())), 'plugin': GD.names[c >> 24], 'mine': k in changed})
    for k, r in (PR.records.items() if PR else ()):
        if k.startswith('+') and r['type'] == 'CELL':
            out.append({'id': k, 'edid': recordio.field(r, 'EDID'), 'name': recordio.field(r, 'FULL'),
                        'refs': len((PR.cells.get(k) or {}).get('refs', {})), 'plugin': 'your mod', 'mine': True, 'own': True})
    out.sort(key=lambda x: x['edid'].lower())
    return out


def base_info(bkey):
    """(type, editor ID, name, model) of a base form as the mod leaves it: its own records and changes first."""
    rec = PR.records.get(bkey) if PR else None
    if rec:
        model = (recordio.field(rec, 'MOD2') if rec['type'] == 'ARMO' else '') or recordio.field(rec, 'MODL')
        return rec['type'], recordio.field(rec, 'EDID'), recordio.field(rec, 'FULL'), model
    return GD.describe(GD.from_key(bkey))


def light_of(bkey):
    """A light's radius, colour and flags, as the mod leaves it (None when it isn't a light)."""
    rec = PR.records.get(bkey) if PR else None
    if rec:
        d = next((s for s in rec['subs'] if s['tag'] == 'DATA' and s['kind'] == 'struct'), None)
        if not d:
            return None
        v = {f['name']: f['value'] for f in d['fields'] if 'name' in f}
    else:
        fid = GD.from_key(bkey)
        data = GD.fields(fid).get('DATA', b'')
        if len(data) < 32:
            return None
        t, radius, r, g, b, _x, flags, falloff, fov = struct.unpack_from('<iIBBBBIff', data)
        v = {'Radius': radius, 'Red': r, 'Green': g, 'Blue': b, 'Flags': flags, 'Falloff exponent': falloff}
    flags = v.get('Flags', 0)
    return {'radius': v.get('Radius', 0), 'color': [v.get('Red', 255), v.get('Green', 255), v.get('Blue', 255)],
            'off': bool(flags & 0x20), 'negative': bool(flags & 0x4), 'falloff': v.get('Falloff exponent', 1)}


def actor_parts(bkey):
    """The meshes a character or creature is drawn from (the game's form, or a record of the mod's own copied from
    one: drawn as the one it was copied from, by its editor ID's original)."""
    if bkey not in _actors:
        try:
            if bkey.startswith('+'):
                bkey_draw = (PR.records.get(bkey) or {}).get('copied_from', '') if PR else ''
                fid = GD.from_key(bkey_draw) if bkey_draw else None
            else:
                fid = GD.from_key(bkey)
            _actors[bkey] = actors.parts(GD, fid) if fid in GD.forms else {'parts': [], 'scale': 1.0}
        except Exception as e:
            _actors[bkey] = {'parts': [], 'scale': 1.0, 'error': str(e)}
    return _actors[bkey]


def thing(key, bkey, p, s, state):
    btype, edid, name, model = base_info(bkey)
    t = {'key': key, 'bkey': bkey, 'base': edid, 'type': btype, 'name': name,
         'model': GD.model_path(btype, model) if model else '', 'p': list(p), 's': s,
         'marker': is_marker(btype, edid, model), 'state': state}
    if btype in ACTORS:
        t['actor'] = True
    if btype == 'LIGH':
        t['light'] = light_of(bkey)
    if btype == 'TREE':
        t['model'], t['tree'] = '', tree_of(bkey, model)
    return t


_trees = {}


def tree_of(bkey, model):
    """A SpeedTree tree as FOLab draws it (gamedata.tree)."""
    if bkey not in _trees:
        _trees[bkey] = GD.tree(GD.from_key(bkey))
    return _trees[bkey]


def cell_things(ckey):
    """Every drawable thing in a cell as the mod leaves it: the game's refs with the project's changes laid over,
    and the project's own new ones."""
    c = None if ckey.startswith('+') else GD.from_key(ckey)
    mine = (PR.cells.get(ckey) or {}).get('refs', {}) if PR else {}
    out = []
    for r in GD.refs(c) if c is not None else ():
        if r['base'] not in GD.forms or not r['pos']:
            continue
        btype, _e, _n, model = GD.describe(r['base'])
        if not model and btype not in ACTORS and btype != 'LIGH':
            continue
        k = GD.key(r['ref'])
        ch = mine.get(k)
        p, s, state, base = list(r['pos']) + list(r['rot']), r['scale'], '', GD.key(r['base'])
        if ch:
            if ch.get('removed'):
                state = 'removed'
            else:
                p, s, state = ch.get('p', p), ch.get('s', s), 'moved'
                if ch.get('base'):
                    base = ch['base']
        t = thing(k, base, p, s, state)
        t['cell'] = ckey
        if r['leads'] or (ch or {}).get('tel'):
            t['door'] = True
        out.append(t)
    for k, ch in mine.items():
        if k.startswith('+'):
            t = thing(k, ch['base'], ch['p'], ch.get('s', 1.0), 'new')
            t['cell'] = ckey
            if ch.get('sc'):
                t['sc'] = True                   # (put down by the Scatter brush: it may take it back)
            if ch.get('gen'):
                t['gen'] = True                  # (from the Kit tab: generating again replaces it)
            if ch.get('tel'):
                t['door'] = True
            out.append(t)
    return out


PREFABS_DIR = os.path.join(project.HOME, 'prefabs')


def prefabs():
    out = []
    if os.path.isdir(PREFABS_DIR):
        for fn in sorted(os.listdir(PREFABS_DIR)):
            if fn.endswith('.json'):
                with open(os.path.join(PREFABS_DIR, fn), encoding='utf-8') as f:
                    d = json.load(f)
                out.append({'name': d['name'], 'count': len(d['items']), 'from': d.get('from', '')})
    return out


def prefab(name):
    """A prefab's things, each with what the view needs to draw it (bases of the mod's own are kept by key and only
    draw while that mod is open)."""
    with open(os.path.join(PREFABS_DIR, project.safe_name(name) + '.json'), encoding='utf-8') as f:
        d = json.load(f)
    items = []
    for it in d['items']:
        try:
            btype, edid, nm, model = base_info(it['base'])
        except Exception:
            continue
        items.append(dict(it, type=btype, edid=edid, model=GD.model_path(btype, model) if model else ''))
    return {'name': d['name'], 'items': items}


def prefab_save(body):
    """Things kept as a prefab: each one's base, place relative to the group's middle (and its lowest point), turn
    and size. Kept beside FOLab's projects, for any mod."""
    os.makedirs(PREFABS_DIR, exist_ok=True)
    name = project.safe_name(body['name'])
    with open(os.path.join(PREFABS_DIR, name + '.json'), 'w', encoding='utf-8') as f:
        json.dump({'name': name, 'from': body.get('from', ''), 'items': body['items']}, f, indent=1)
    return {'name': name, 'prefabs': prefabs()}


def worlds():
    """Worldspaces with ground to walk on, the big ones first."""
    out = []
    for w in GD.worlds():
        n = len(GD.grid(w))
        if not n:
            continue
        f = GD.fields(w)
        out.append({'id': GD.key(w), 'edid': tes4.zstr(f.get('EDID', b'')), 'name': tes4.zstr(f.get('FULL', b'')),
                    'cells': n, 'plugin': GD.names[w >> 24]})
    out.sort(key=lambda x: (-x['cells'], x['edid'].lower()))
    return out


def world(wkey):
    """A worldspace's map markers (the places on the Pip-Boy map), to jump to; else the middle of its cells."""
    w = GD.from_key(wkey)
    marks = []
    for rfid, entry in GD.cell_refs.get(GD.world_persistent.get(w), {}).items():
        i, f = GD.ref_fields(entry)
        if 'XMRK' in f and 'DATA' in f:
            p = list(struct.unpack_from('<6f', f['DATA']))
            marks.append({'name': tes4.zstr(f.get('FULL', b'')) or GD.edid(rfid) or GD.key(rfid), 'p': p})
    marks.sort(key=lambda m: m['name'].lower())
    g = GD.grid(w)
    xs, ys = [k[0] for k in g], [k[1] for k in g]
    mid = [(min(xs) + max(xs) + 1) / 2 * 4096, (min(ys) + max(ys) + 1) / 2 * 4096] if g else [0, 0]
    f = GD.fields(w)
    bounds = [min(xs), min(ys), max(xs), max(ys)] if g else [0, 0, 0, 0]
    return {'id': wkey, 'edid': tes4.zstr(f.get('EDID', b'')), 'name': tes4.zstr(f.get('FULL', b'')),
            'markers': marks, 'middle': mid, 'bounds': bounds}


def map_painter():
    global _painter
    if _painter is None or _painter.gd is not GD:
        _painter = maptiles.Painter(GD)
        _tiles.clear()
    return _painter


def map_tile(wkey, tx, ty):
    """The flat map's picture of 16 x 16 cells (maptiles.py), with the mod's ground in it. The game's own tiles are
    kept on disk (under cache/maps, for exactly these game files), and asking for one starts drawing the rest of
    that world's in the background, nearest first, so the map is quick from then on."""
    global _painter
    w = GD.from_key(wkey)
    if _painter is None or _painter.gd is not GD:
        _painter = maptiles.Painter(GD)
        _tiles.clear()
    mine = _mine_in_tile(w, tx, ty)
    water = _water_in_tile(w, tx, ty)
    if not mine and not water:
        path = _tile_path(wkey, tx, ty)
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                return f.read()
        data = _painter.tile(w, tx, ty)
        _tile_save(path, data)
        _tiles_ahead(wkey, tx, ty)
        return data
    sig = hashlib.md5(json.dumps([mine, water], sort_keys=True).encode()).hexdigest()
    k = (wkey, tx, ty, sig)
    if k not in _tiles:
        if len(_tiles) > 200:
            _tiles.clear()
        _tiles[k] = _painter.tile(w, tx, ty, mine, water)
    return _tiles[k]


_far = {}


def far_land(wkey, tx, ty):
    """The far ground of a map tile: heights every 8th point (4 a cell, 65 x 65 for the tile, rows from the south),
    the mod's ground in them; None where there's no land (drawn as a hole)."""
    w = GD.from_key(wkey)
    mine = _mine_in_tile(w, tx, ty)
    k = (wkey, tx, ty, hashlib.md5(json.dumps({c: L['h'] for c, L in mine.items()}).encode()).hexdigest() if mine else '')
    if k in _far:
        return _far[k]
    n = maptiles.TILE * 4 + 1
    out = [None] * (n * n)
    grid = GD.grid(w)
    for i in range(maptiles.TILE):
        for j in range(maptiles.TILE):
            cx, cy = tx * maptiles.TILE + i, ty * maptiles.TILE + j
            c = grid.get((cx, cy))
            L = mine.get(GD.key(c)) if c is not None else None
            if L:
                h = L['h']
            else:
                e = GD.land_at(w, cx, cy)
                if not e:
                    continue
                h = land.heights_of(dict(tes4.iter_subrecords(GD.plugins[e[0]].data(e[1])))['VHGT'])
            for r in range(5):
                for q in range(5):
                    out[(j * 4 + r) * n + i * 4 + q] = round(h[(r * 8) * 33 + q * 8])
    if len(_far) > 300:
        _far.clear()
    _far[k] = {'n': n, 'h': out}
    return _far[k]


def _heights(w, cx, cy, own_only=False):
    """A grid square's 33 x 33 heights as the mod leaves them (None: no ground; own_only: none either where the land
    is borrowed from a parent world, which can't be changed here)."""
    c = GD.grid(w).get((cx, cy))
    if c is not None and PR and GD.key(c) in PR.land:
        return PR.land[GD.key(c)]['h']
    if own_only and (c is None or c not in GD.land):
        return None
    e = GD.land_at(w, cx, cy)
    return land.heights_of(dict(tes4.iter_subrecords(GD.plugins[e[0]].data(e[1])))['VHGT']) if e else None


def heightmap_export(q):
    w = GD.from_key(q['world'])
    x, y, n, m = int(q['x']), int(q['y']), max(1, min(64, int(q['w']))), max(1, min(64, int(q['h'])))
    return heightmap.export(lambda cx, cy: _heights(w, cx, cy), q['world'], x, y, n, m)


def ground_ops(w, new, follow=True, quarters=None):
    """Edit ops putting new heights {(cx, cy): 33*33} into the ground (each cell's textures and colours kept) and,
    with follow, moving the things standing on it up and down with it."""
    ops = []
    for (cx, cy), hs in sorted(new.items()):
        c = GD.grid(w)[(cx, cy)]
        ck = GD.key(c)
        old = _heights(w, cx, cy)
        L = dict(PR.land[ck]) if ck in PR.land else land.decode(GD, GD.land[c], _land_tex)
        L['h'] = hs
        if quarters and (cx, cy) in quarters:
            L['q'] = quarters[(cx, cy)]
        ops.append({'op': 'land', 'cell': ck, 'land': L})
        if follow:
            for t in cell_things(ck):
                if t['state'] == 'removed':
                    continue
                lx, ly = t['p'][0] - cx * 4096, t['p'][1] - cy * 4096
                if not (0 <= lx <= 4096 and 0 <= ly <= 4096):
                    continue
                a, b = heightmap.ground(old, lx, ly), heightmap.ground(hs, lx, ly)
                if abs(t['p'][2] - a) < 200 and abs(b - a) > 0.5:
                    p = list(t['p'])
                    p[2] = round(p[2] + b - a, 2)
                    ops.append({'op': 'move', 'cell': ck, 'ref': t['key'], 'p': p})
    return ops


# ---------- land shaping (landshape.py) ----------

_settled = {}
_previews = {}
BUILT = ('STAT', 'SCOL', 'DOOR', 'FURN', 'ACTI', 'TERM', 'CONT')


def settled(w, cx, cy):
    """A town or a place with many buildings: a door, or 30 built pieces (rocks and plants aside)."""
    k = (w, cx, cy)
    if k not in _settled:
        c = GD.grid(w).get((cx, cy))
        n, doors = 0, 0
        for r in GD.refs(c) if c is not None else ():
            if r['base'] not in GD.forms:
                continue
            btype, edid, _n, model = GD.describe(r['base'])
            if btype == 'DOOR':
                doors += 1
            elif btype in BUILT and model and not scatter.kind(btype, edid, model) and 'landscape' not in model.lower():
                n += 1
        _settled[k] = doors > 0 or n >= 30
    return _settled[k]


def shape_cells(body):
    """The cells a plan changes: those its shapes reach and those marked by hand, less those unmarked by hand and
    (unless asked) settled ones; and the settled ones it left out."""
    w = GD.from_key(body['world'])
    reached = set()
    for sh in body['plan'].get('shapes', []):
        if sh.get('on', True) and sh.get('pts'):
            reached |= landshape.cells_reached(sh)
    reached |= {tuple(m) for m in body.get('marks', [])}
    reached -= {tuple(m) for m in body.get('unmarks', [])}
    grid = GD.grid(w)
    ok, skipped = [], []
    for k in sorted(reached):
        c = grid.get(k)
        if c is None or c not in GD.land:
            continue
        if not body.get('settled') and settled(w, *k) and list(k) not in body.get('marks', []):
            skipped.append(list(k))
        else:
            ok.append(list(k))
    return {'marked': ok, 'settled': skipped}


def shape_heights(body):
    w = GD.from_key(body['world'])
    plan, marked = body['plan'], [tuple(m) for m in body['marked']]
    start = (lambda cx, cy: _game_heights(w, cx, cy)) if plan.get('from_game', True) else (lambda cx, cy: _heights(w, cx, cy))
    boxes = []
    if plan.get('hold', True):
        near = {(cx + dx, cy + dy) for cx, cy in marked for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        grid = GD.grid(w)
        for k in near:
            c = grid.get(k)
            if c is None:
                continue
            for t in cell_things(GD.key(c)):
                if t['state'] == 'removed' or t['type'] not in BUILT or t['bkey'].startswith('+') or t.get('marker'):
                    continue
                btype, edid, _n, model = GD.describe(GD.from_key(t['bkey']))
                if scatter.kind(btype, edid, model) or 'landscape' in model.lower():
                    continue
                b = landshape.footprint(GD, {'base': GD.from_key(t['bkey']), 'pos': t['p'][:3], 'rot': t['p'][3:], 'scale': t['s']})
                if b and (b[2] - b[0]) * (b[3] - b[1]) > 64 * 64:
                    boxes.append(b)
    new, water = landshape.shape_all(plan, start, marked, boxes)
    quarters = paint_new(w, plan, new, start, marked) if plan.get('paint', True) else {}
    return new, water, w, quarters


_paint_models = {}


def paint_new(w, plan, new, start, marked):
    """The reshaped cells' textures, painted by their new slopes the way the land round them is (autopaint.py)."""
    if not new:
        return {}
    xs, ys = [k[0] for k in new], [k[1] for k in new]
    cx, cy = (min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2
    mk = (GD.key(w), cx // 4, cy // 4)
    if mk not in _paint_models:
        _paint_models[mk] = autopaint.learn(GD, w, cx, cy, tex_cache=_land_tex)
    model, pics = _paint_models[mk]
    fade, marked = max(128.0, float(plan.get('fade', 1024))), set(map(tuple, marked))
    out = {}
    for (x, y), hs in new.items():
        c = GD.grid(w)[(x, y)]
        ck = GD.key(c)
        L0 = PR.land[ck] if PR and ck in PR.land else land.decode(GD, GD.land[c], _land_tex)
        weight = lambda gr, gc, x=x, y=y: landshape._edge_weight(x * 4096 + gc * 128, y * 4096 + gr * 128, marked, fade)
        out[(x, y)] = autopaint.paint(GD, {'h': hs, 'q': L0['q']}, start(x, y), model, pics, weight)
    return out


def _game_heights(w, cx, cy):
    e = GD.land_at(w, cx, cy)
    return land.heights_of(dict(tes4.iter_subrecords(GD.plugins[e[0]].data(e[1])))['VHGT']) if e else None


def shape_preview(body):
    """The plan's land worked out and kept under a key, with the map tiles it touches: drawn by /api/shape/tile."""
    new, water, w, quarters = shape_heights(body)
    mine = dict(PR.land) if PR else {}
    wat = dict(PR.water) if PR else {}
    for (cx, cy), lv in water.items():
        wat[GD.key(GD.grid(w)[(cx, cy)])] = lv
    for (cx, cy), hs in new.items():
        c = GD.grid(w)[(cx, cy)]
        ck = GD.key(c)
        L = dict(mine[ck]) if ck in mine else land.decode(GD, GD.land[c], _land_tex)
        L['h'] = hs
        if (cx, cy) in quarters:
            L['q'] = quarters[(cx, cy)]
        mine[ck] = L
    key = hashlib.md5(json.dumps([body['world'], body['plan'], body['marked']], sort_keys=True).encode()).hexdigest()[:16]
    _previews.clear()
    _previews[key] = (w, mine, {}, wat)
    tiles = sorted({(cx // maptiles.TILE, cy // maptiles.TILE) for cx, cy in new})
    return {'key': key, 'tiles': tiles, 'cells': len(new)}


def shape_tile(key, tx, ty):
    w, mine, done, wat = _previews[key]
    if (tx, ty) not in done:
        global _painter
        if _painter is None or _painter.gd is not GD:
            _painter = maptiles.Painter(GD)
        grid = GD.grid(w)
        here = {}
        for i in range(maptiles.TILE):
            for j in range(maptiles.TILE):
                c = grid.get((tx * maptiles.TILE + i, ty * maptiles.TILE + j))
                if c is not None and GD.key(c) in mine:
                    here[GD.key(c)] = mine[GD.key(c)]
        done[(tx, ty)] = _painter.tile(w, tx, ty, here, wat)
    return done[(tx, ty)]


def shape_apply(body):
    new, water, w, quarters = shape_heights(body)
    if not new:
        raise ValueError('No marked cells with ground to shape.')
    ops = ground_ops(w, new, body.get('follow', True), quarters)
    ops += [{'op': 'water', 'cell': GD.key(GD.grid(w)[k]), 'h': round(v, 1)} for k, v in sorted(water.items())]
    out = edit('Shape the land (%d cells)' % len(new), ops)
    out['cells'] = len(new)
    return out


def heightmap_import(body):
    """A height map back into the ground: every cell it covers, and (follow) the things standing on the ground moved
    up and down with it, as one Undo."""
    w = GD.from_key(body['world'])
    png = base64.b64decode(body['data'])
    new = heightmap.apply(png, lambda cx, cy: _heights(w, cx, cy, own_only=True), body.get('x'), body.get('y'),
                          body.get('w'), body.get('h'), body.get('low'), body.get('high'))
    if not new:
        raise ValueError('The picture covers no ground FOLab can change here.')
    ops = ground_ops(w, new, body.get('follow', True))
    out = edit('Import a height map', ops)
    out['cells'] = len(new)
    return out


def _water_in_tile(w, tx, ty):
    out = {}
    if PR and PR.water:
        grid = GD.grid(w)
        for i in range(maptiles.TILE):
            for j in range(maptiles.TILE):
                c = grid.get((tx * maptiles.TILE + i, ty * maptiles.TILE + j))
                if c is not None and GD.key(c) in PR.water:
                    out[GD.key(c)] = PR.water[GD.key(c)]
    return out


def _mine_in_tile(w, tx, ty):
    mine = {}
    if PR and PR.land:
        grid = GD.grid(w)
        for i in range(maptiles.TILE):
            for j in range(maptiles.TILE):
                c = grid.get((tx * maptiles.TILE + i, ty * maptiles.TILE + j))
                if c is not None and GD.key(c) in PR.land:
                    mine[GD.key(c)] = PR.land[GD.key(c)]
    return mine


def _tile_dir():
    # (the game's files as they are now: a patch or another load order draws its own tiles)
    sig = hashlib.md5('|'.join('%s:%d:%d' % (p.path, os.path.getsize(p.path), os.path.getmtime(p.path))
                               for p in GD.plugins).encode()).hexdigest()[:12]
    return os.path.join(project.HOME, 'cache', 'maps', sig)


def _tile_path(wkey, tx, ty):
    return os.path.join(_tile_dir(), wkey.replace(':', '_'), '%d_%d.png' % (tx, ty))


def _tile_save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + '.tmp', 'wb') as f:
        f.write(data)
    os.replace(path + '.tmp', path)


_ahead = {}


def _tiles_ahead(wkey, tx, ty):
    """Draw the rest of a world's tiles in the background (once per world), nearest to (tx, ty) first."""
    if wkey in _ahead:
        return
    _ahead[wkey] = True
    gd, painter = GD, _painter

    def run():
        w = gd.from_key(wkey)
        tiles = sorted({(x // maptiles.TILE, y // maptiles.TILE) for x, y in gd.grid(w)},
                       key=lambda t: (t[0] - tx) ** 2 + (t[1] - ty) ** 2)
        for t in tiles:
            if GD is not gd:
                return                              # (the game was loaded again: another mod's land)
            path = _tile_path(wkey, *t)
            if os.path.isfile(path):
                continue
            try:
                _tile_save(path, painter.tile(w, *t))
            except Exception as e:
                print('map tile', t, e, flush=True)
            time.sleep(0.05)                        # (give way: the editor answers first)
    threading.Thread(target=run, daemon=True).start()


def goto(q, wkey=None):
    """Go to a place: places by name, map markers of every worldspace, a cell's coordinates ('-18, 0') or a spot
    in game units ('x y' or 'x y z', as the console gives it) in the worldspace open now."""
    global _markers
    q = q.strip()
    out = []
    nums = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', q)] if re.fullmatch(r'[\s,;()\-\d.]+', q or 'x') else []
    world = wkey or (GD.key(next((w for w in GD.worlds() if GD.edid(w) == 'WastelandNV'), GD.worlds()[0])) if GD.worlds() else None)
    if world and len(nums) == 2 and all(abs(v) < 1000 and v == int(v) for v in nums):
        x, y = int(nums[0]), int(nums[1])
        out.append({'kind': 'cell', 'world': world, 'name': 'Cell %d, %d' % (x, y), 'p': [x * 4096 + 2048, y * 4096 + 2048, 0]})
    elif world and len(nums) in (2, 3):
        out.append({'kind': 'spot', 'world': world, 'name': 'The spot %s' % ' '.join('%g' % v for v in nums),
                    'p': nums + ([0] if len(nums) == 2 else [])})
    if nums:
        return out
    words = q.lower().split()
    if not words:
        return out
    for c in interiors():
        if all(wd in (c['name'] + ' ' + c['edid']).lower() for wd in words):
            out.append({'kind': 'place', 'id': c['id'], 'name': c['name'] or c['edid'], 'edid': c['edid']})
        if len(out) >= 40:
            break
    if _markers is None:
        _markers = []
        for w in GD.worlds():
            if GD.grid(w):
                info = world_markers(w)
                _markers += [{'kind': 'marker', 'world': GD.key(w), 'world_name': info[1], 'name': m['name'], 'p': m['p']}
                             for m in info[0]]
    out += [m for m in _markers if all(wd in m['name'].lower() for wd in words)][:40]
    out.sort(key=lambda r: (not r['name'].lower().startswith(words[0]), r['kind'] != 'marker', r['name'].lower()))
    return out[:60]


def world_markers(w):
    wk = world(GD.key(w))
    return wk['markers'], wk['name'] or wk['edid']


def outside(wkey, x, y):
    """One grid square of a worldspace: its cell (if it has one), its ground, and the things in it."""
    w = GD.from_key(wkey)
    c = GD.grid(w).get((x, y))
    entry = GD.land_at(w, x, y)
    mine = PR.land.get(GD.key(c)) if PR and c is not None else None
    if _painter is None:
        map_painter()
    out = {'x': x, 'y': y, 'cell': GD.key(c) if c is not None else None,
           'land': mine or (land.decode(GD, entry, _land_tex) if entry else None), 'things': [],
           'water': _painter.water(w, c, PR.water if PR else None) if c is not None else None,
           'changed_water': bool(PR and c is not None and GD.key(c) in PR.water),
           'own_land': c is not None and c in GD.land, 'changed_land': bool(mine)}
    if c is not None:
        out['things'] = cell_things(GD.key(c))
    return out


def outside_cell(o, world):
    """Outside, the grid cell a change belongs to, whatever cell the view sent: a new thing's is the square it stands
    in; a game thing's is the cell holding it (one the world keeps loaded goes by the square it stood in); one of the
    mod's own stays where it was added."""
    grid = GD.grid(world)
    sq = lambda p: grid.get((int(p[0] // 4096), int(p[1] // 4096)))
    if o.get('op') == 'add' and o.get('p'):
        c = sq(o['p'])
        return GD.key(c) if c is not None else None
    r = o.get('ref')
    if not r:
        return None
    if r.startswith('+'):
        return next((ck for ck, c in (PR.cells.items() if PR else ()) if r in c['refs']), None)
    fid = GD.from_key(r)
    home = GD.ref_cell.get(fid)
    if home in GD.ext_cells:
        return GD.key(home)
    if home is not None and home == GD.world_persistent.get(world):
        f = GD.ref_fields(GD.cell_refs[home][fid])[1]
        c = sq(struct.unpack_from('<2f', f['DATA'])) if 'DATA' in f else None
        return GD.key(c) if c is not None else None
    return None


def land_textures():
    """Every ground texture (LTEX): its key, editor ID and picture, the ones the Mojave uses most first."""
    out = []
    for f, (i, r) in GD.forms.items():
        if r.tag != 'LTEX':
            continue
        tex = land.texture_of_fid(GD, f, _land_tex)
        if tex:
            out.append({'key': GD.key(f), 'edid': GD.edid(f), 'tex': tex})
    out.sort(key=lambda t: t['edid'].lower())
    return out


def place_name(ckey):
    """(editor ID, name) of a place, the mod's own included"""
    rec = PR.records.get(ckey) if PR else None
    if rec:
        return recordio.field(rec, 'EDID'), recordio.field(rec, 'FULL')
    f = GD.fields(GD.from_key(ckey))
    return tes4.zstr(f.get('EDID', b'')), tes4.zstr(f.get('FULL', b''))


def ref_cell_key(rkey):
    """Which place a ref is in, the mod's own refs and places included."""
    for ck, c in (PR.cells.items() if PR else ()):
        if rkey in c['refs'] and (rkey.startswith('+') or not c['refs'][rkey].get('removed')):
            if rkey.startswith('+'):
                return ck
    if rkey.startswith('+'):
        return None
    c = GD.ref_cell.get(GD.from_key(rkey))
    return GD.key(c) if c is not None else None


def new_place(body):
    """A place of the mod's own: a copy of a place's record (its lighting, music, sound), empty or with copies of
    everything in it; and, in an empty one, a marker where the console's coc arrives."""
    src = body['from']
    rec = json.loads(json.dumps(BR.record(src)['record']))
    rec['type'], rec['src'] = 'CELL', rec.get('src', '')
    # (an editor ID nothing else has: the console's coc finds places by it)
    taken = set(BR.edids or {}) | {GD.edid(c).lower() for c in GD.interiors} | \
        {recordio.field(r, 'EDID').lower() for r in PR.records.values()}
    edid, n = body['edid'], 1
    while edid.lower() in taken:
        n += 1
        edid = '%s%d' % (body['edid'], n)
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    recordio.set_field(rec, 'FULL', body['name'], label='Name')
    ops = [{'op': 'record_new', 'record': rec}]
    if body.get('copy'):
        for t in cell_things(src):
            if t['state'] != 'removed':
                ops.append({'op': 'add', 'cell': '$new', 'base': t['bkey'], 'p': t['p'], 's': t['s']})
    else:
        coc = next((GD.key(f) for f, (i, r) in GD.forms.items() if r.tag == 'STAT' and GD.edid(f) == 'COCMarkerHeading'), None)
        if coc:
            ops.append({'op': 'add', 'cell': '$new', 'base': coc, 'p': [0, 0, 0, 0, 0, 0], 's': 1})
    return edit('New place ' + body['name'], ops)


def link_doors(a, b):
    """Two doors leading to each other: a = {'cell', 'ref', 'arrive': [x, y, z, rx, ry, rz]} (where you arrive at a,
    coming through b), the same for b."""
    return edit('Link doors', [{'op': 'tel', 'cell': a['cell'], 'ref': a['ref'], 'tel': {'door': b['ref'], 'p': b['arrive']}},
                               {'op': 'tel', 'cell': b['cell'], 'ref': b['ref'], 'tel': {'door': a['ref'], 'p': a['arrive']}}])


def cell(ckey):
    return {'id': ckey, 'edid': place_name(ckey)[0], 'things': cell_things(ckey)}


def ref(ckey, rkey):
    """One placed thing for the object window: its base record and its own fields."""
    t = next((t for t in cell_things(ckey) if t['key'] == rkey), None)
    if not t:
        raise FileNotFoundError(rkey)
    frm = 'your mod' if t['bkey'].startswith('+') else GD.names[GD.source(GD.from_key(t['bkey']))[0]]
    out = {'thing': t, 'base': {'key': t['bkey'], 'type': t['type'], 'edid': t['base'], 'name': t['name'],
                                'model': t['model'], 'from': frm}}
    out['ref'] = refinfo.ref_info(GD, GD.from_key(rkey)) if not rkey.startswith('+') else {}
    d = door(rkey)
    if d:
        out['ref']['door'] = d
    return out


def door(rkey):
    """Where a door leads, as the mod leaves it: its own link first, else the game's."""
    for ck, c in (PR.cells.items() if PR else ()):
        tel = (c['refs'].get(rkey) or {}).get('tel')
        if tel:
            dest = ref_cell_key(tel['door'])
            e, n = place_name(dest) if dest else ('', '')
            out = {'door': tel['door'], 'p': tel['p'], 'cell': dest, 'cell_edid': e, 'cell_name': n,
                   'interior': True, 'mine': True}
            c = GD.from_key(dest) if dest and not dest.startswith('+') else None
            world = GD.ext_cells.get(c) or next((w for w, pc in GD.world_persistent.items() if pc == c), None)
            if world is not None:
                out.update(interior=False, world=GD.key(world), world_name=place_name(GD.key(world))[1])
            return out
    if rkey.startswith('+'):
        return None
    return refinfo.door_target(GD, GD.from_key(rkey))


def mesh(path):
    key = path.lower()
    with _lock:
        if key in _meshes:
            return _meshes[key]
    try:
        shapes = nif.mesh_from_nif(GD.read_file(path))
        for s in shapes:
            t = s['tex'].lower()
            if t and not t.startswith('textures\\'):
                s['tex'] = 'textures\\' + s['tex']
        out = json.dumps({'shapes': shapes}, separators=(',', ':')).encode()
    except Exception as e:
        out = json.dumps({'shapes': [], 'error': str(e)}).encode()
    with _lock:
        _meshes[key] = out
    return out


def search(q, kind='', limit=300):
    words = q.lower().split()
    out = []
    for k, r in (PR.records.items() if PR else ()):         # the mod's own new things first
        if k.startswith('+') and r['type'] in PLACEABLE and (not kind or r['type'] == kind) and recordio.field(r, 'MODL'):
            e, n = recordio.field(r, 'EDID'), recordio.field(r, 'FULL')
            if all(w in (e + ' ' + n).lower() for w in words):
                out.append({'key': k, 'type': r['type'], 'edid': e, 'name': n, 'model': GD.model_path(r['type'], recordio.field(r, 'MODL'))})
    for row in CATALOGUE:
        if kind and row[1] != kind:
            continue
        hay = (row[2] + ' ' + row[3] + ' ' + row[4]).lower()
        if all(w in hay for w in words):
            out.append({'key': row[0], 'type': row[1], 'edid': row[2], 'name': row[3], 'model': row[4]})
            if len(out) >= limit:
                break
    return out


# --- the project ---

# ---------- errors, About, problem reports ----------

LOG = os.path.join(project.HOME, 'logs', 'folab.log')
_errors = []                            # the last few errors, for a problem report
SERVER = None


def log_error(where, e):
    """An error answered to the page: kept for Report a problem, and written to logs/folab.log (the stack too)."""
    if isinstance(e, ValueError) and not isinstance(e, (UnicodeError, json.JSONDecodeError)):
        _errors.append('%s %s: %s' % (time.strftime('%H:%M:%S'), where, e))      # (a message for the user, not a fault)
    else:
        _errors.append('%s %s: %s: %s' % (time.strftime('%H:%M:%S'), where, type(e).__name__, e))
        try:
            os.makedirs(os.path.dirname(LOG), exist_ok=True)
            if os.path.isfile(LOG) and os.path.getsize(LOG) > 2_000_000:
                os.replace(LOG, LOG + '.old')
            with open(LOG, 'a', encoding='utf-8') as f:
                f.write('%s %s\n%s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), where, traceback.format_exc()))
        except OSError:
            pass
    del _errors[:-20]


def about():
    return {'version': VERSION, 'python': platform.python_version(), 'system': platform.platform(),
            'game': GD.data_dir if GD else None, 'plugins': [os.path.basename(p.path) for p in GD.plugins] if GD else [],
            'home': project.HOME}


def report():
    """Everything useful for looking into a problem, as text to paste."""
    a = about()
    lines = ['FOLab %s · Python %s · %s' % (a['version'], a['python'], a['system']),
             'Game: %s' % a['game'], 'Loaded: %s' % ', '.join(a['plugins'])]
    try:
        n = nvse.status(GD.data_dir)
        lines.append('xNVSE: %s' % (n.get('version') or ('installed' if n.get('installed') else 'not installed')))
        lines.append('NVSE plugins: %s' % ', '.join(nvse.plugins(GD.data_dir)['dlls']))
    except Exception as e:
        lines.append('xNVSE: (%s)' % e)
    if PR:
        st = PR.state()
        lines.append('Mod: %s (%s) · %d changes · opened from a plugin: %s · last change: %s' % (
            PR.name, PR.plugin, st['changes'], bool(PR.source), st['undo']))
        lines.append('Masters: %s' % ', '.join(masters()))
    lines.append('Game running: %s' % playtest.game_running())
    lines.append('')
    lines.append('Last errors:' if _errors else 'No errors this session.')
    lines += ['  ' + e for e in _errors]
    if os.path.isfile(LOG):
        with open(LOG, encoding='utf-8', errors='replace') as f:
            tail = f.read()[-3000:]
        lines += ['', 'From logs/folab.log (the end):', tail]
    return '\n'.join(l for l in lines if l is not None)


def state():
    s = {'game': GD.data_dir, 'interiors': len(GD.interiors), 'project': PR.state() if PR else None,
         'projects': project.list_projects(), 'kinds': PLACEABLE}
    s['nvse'] = nvse.status(GD.data_dir)
    s['launch_via'] = load_settings().get('launch_via', 'nvse')
    if PR:
        s['installed'] = install.status(GD.data_dir, PR.plugin)
        built = os.path.join(project.BUILD_DIR, PR.plugin)
        s['project']['built'] = os.path.isfile(built) and os.path.getmtime(built) >= os.path.getmtime(PR.path)
        s['project']['masters'] = masters()
    return s


def load_game(pr):
    """The game as FOLab shows it: the official files, and an opened mod's own plugin on top of them."""
    global GD, CATALOGUE, BR
    data_dir = GD.data_dir if GD else gamedata.find_data_dir()
    want = [os.path.join(data_dir, n) for n in gamedata.OFFICIAL if os.path.isfile(os.path.join(data_dir, n))]
    if pr and pr.source:
        want.append(pr.source_path())
    if GD and [p.path for p in GD.plugins] == want:
        return
    t = time.time()
    if BR:
        BR.close()
    GD = gamedata.GameData(data_dir, want)
    CATALOGUE = build_catalogue()
    BR = browse.Browse(GD, lambda: PR)
    _meshes.clear()
    _actors.clear()
    print('loaded %d plugins (%.1fs)' % (len(GD.plugins), time.time() - t), flush=True)


def new_world(body):
    """A new worldspace in the mod: the mod saved (naming every game file as a master, so the new land can use any of
    their things), the world added to that plugin (worldgen.py), and the plugin then opened as the mod, so the world
    is part of the game FOLab shows and every tool works on it. The mod's undo history starts afresh."""
    global PR
    if not PR:
        raise ValueError('Start a mod first.')
    not_while_playing()
    edid = re.sub(r'[^A-Za-z0-9_]', '', body.get('edid') or '')
    if not edid:
        raise ValueError('Give it an editor ID: letters and digits, no spaces.')
    if BR and BR.edids and edid.lower() in BR.edids:
        raise ValueError('The game already has something called %s.' % edid)
    tpl = GD.from_key(body['template']) if body.get('template') else next(w for w in GD.worlds() if GD.edid(w) == 'WastelandNV')
    size = max(1, min(64, int(body.get('size', 8))))
    ltex = body.get('ltex') or next((GD.key(f) for f, (i, r) in GD.forms.items() if r.tag == 'LTEX' and GD.edid(f) == 'DirtBarrenWastes01'), None)
    if not ltex:
        raise ValueError('Pick a ground texture.')
    path = PR.plugin_path()
    w = espwrite.Writer(GD, PR)
    w.force_all = not PR.source
    data = w.build()
    with open(path, 'wb') as f:
        f.write(data)
    tree = plugintree.Plugin.read(path)
    wid, nid = worldgen.add_world(GD, tree, w, PR.next_id, {'edid': edid, 'name': body.get('name') or '', 'template': tpl,
                                                            'size': size, 'height': float(body.get('height', 4000)), 'ltex': ltex})
    worldgen.fix_header(tree, w.own(nid))
    with open(path + '.tmp', 'wb') as f:
        f.write(tree.bytes())
    os.replace(path + '.tmp', path)
    # the mod is now that plugin, opened
    folder = PR.name + ' source'
    os.makedirs(os.path.join(project.PROJECTS_DIR, folder), exist_ok=True)
    shutil.copy2(path, os.path.join(project.PROJECTS_DIR, folder, PR.plugin))
    d = PR.to_dict()
    d.update(cells={}, records={}, land={}, water={}, next_id=nid, source=folder + '/' + PR.plugin)
    with open(PR.path, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=1)
    name = PR.name
    PR = None
    out = open_project(name)
    me = len(GD.plugins) - 1
    out['world'] = GD.key((me << 24) | (wid & 0xFFFFFF))
    return out


def open_project(name, create=False):
    global PR
    pr = project.Project.create(name) if create else project.Project.open(name)
    load_game(pr)
    PR = pr
    save_settings(project=PR.name)
    return state()


def masters():
    """The open mod's masters, as it would be saved now."""
    try:
        w = espwrite.Writer(GD, PR)
        w.plan()
        return w.masters
    except Exception as e:
        return ['(%s)' % e]


def edit(label, ops):
    if not PR:
        raise ValueError('no mod open')
    for o in ops:
        c = o.get('cell')
        if c and not c.startswith('+') and c != '$new' and GD.from_key(c) in GD.ext_cells:
            o['cell'] = outside_cell(o, GD.ext_cells[GD.from_key(c)]) or c
    made = PR.apply(label, ops)
    out = {'state': state(), 'made': made}
    cells = {o['cell'] for o in ops if 'cell' in o and o['cell'] != '$new'}
    keys = set(made) | {o.get('ref') for o in ops}
    if cells and len(cells) <= 9:
        out['things'] = [t for c in cells for t in cell_things(c) if t['key'] in keys]
    return out


# ---------- the building kits (kitindex.py): read once per game files, in the background ----------
_kits = {'for': None, 'kits': None, 'error': None, 'tilesets': {}, 'walls': {}}


def kits_state():
    """The index if it's ready; otherwise starts reading it and returns None."""
    if _kits['for'] is not GD:
        game = GD
        _kits.update({'for': game, 'kits': None, 'error': None, 'tilesets': {}, 'walls': {}})
        folder = os.path.join(os.path.dirname(_tile_dir()), '..', 'kits', os.path.basename(_tile_dir()))

        def run():
            try:
                got = kitindex.load(game, folder)
                if _kits['for'] is game:
                    _kits['kits'] = got
            except Exception as e:
                traceback.print_exc()
                _kits['error'] = str(e)
        threading.Thread(target=run, daemon=True).start()
    return _kits['kits']


def kits_list():
    kits = kits_state()
    if _kits['error']:
        return {'error': _kits['error']}
    if kits is None:
        return {'building': True}
    out = []
    for name, k in kits.items():
        ts = _kits['tilesets'].get(name)
        if ts is None:
            ts = _kits['tilesets'][name] = kitindex.Tileset(k)
        if len(ts.slot_sock) >= kitindex.MIN_TILES:
            out.append({'name': name, 'label': kitindex.label_of(name), 'step': k.step, 'tiles': len(ts.slot_sock)})
    return {'kits': sorted(out, key=lambda k: k['label'])}


def kit_piece(ckey, key):
    """What can join a placed piece. {'kit': None} if it isn't a building piece (or the index is still being read)."""
    kits = kits_state()
    if not kits:
        return {'kit': None}
    things = [t for t in cell_things(ckey) if t['state'] != 'removed']
    t = next((x for x in things if x['key'] == key), None)
    if not t:
        return {'kit': None}
    kit, piece = kitindex.find_piece(kits, t['bkey'])
    if not kit:
        return {'kit': None}
    turn = kitindex.quarter(t['p'][5])
    square = turn is not None and abs(t['p'][3]) < 0.01 and abs(t['p'][4]) < 0.01 and abs(t['s'] - 1) < 0.001
    out = {'kit': kit.name, 'label': kitindex.label_of(kit.name), 'step': kit.step, 'turned': not square, 'sides': []}
    if square:
        others = []
        for x in things:
            q = kit.pieces.get(x['bkey'])
            tq = kitindex.quarter(x['p'][5]) if q else None
            if x is not t and q and q.foot and tq is not None:
                others.append((q, x['p'][0], x['p'][1], x['p'][2], tq))
        out['sides'] = kitindex.piece_sides(kit, piece, t['p'][:3], turn, others)
    return out


def navmesh_make(ckey):
    """Make a place's navmesh: one undo step."""
    try:
        data, report = navbuild.generate(GD, PR, ckey)
    except navbuild.NavError as e:
        return {'note': str(e)}
    out = edit('Generate navmesh', [{'op': 'navmesh', 'cell': ckey, 'mesh': data}])
    out['report'] = report
    out['navmesh'] = navbuild.status(GD, PR, ckey)
    return out


def kit_layout(body):
    kits = kits_state()
    if not kits or body['kit'] not in kits:
        return {'note': 'The kits are still being read: a moment.'}
    w, h = max(2, min(40, int(body['w']))), max(2, min(40, int(body['h'])))
    return kitindex.layout(GD, kits, body['kit'], w, h, int(body['seed']), body['at'], _kits['tilesets'], _kits['walls'])


def record_copy(key):
    """A new record of the mod's own, a copy of this one, with an editor ID of its own."""
    rec = BR.record(key)['record']
    rec = json.loads(json.dumps(rec))
    base = recordio.field(rec, 'EDID') or 'Record'
    taken = set(BR.edids or {}) | {recordio.field(r, 'EDID').lower() for r in PR.records.values()}
    n, edid = 1, base + 'Copy'
    while edid.lower() in taken:
        n += 1
        edid = '%sCopy%d' % (base, n)
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    rec['src'] = rec.get('src') or ''
    rec['copied_from'] = (PR.records.get(key) or {}).get('copied_from') or key   # (drawn like the one it came from)
    return edit('Copy ' + base, [{'op': 'record_new', 'record': rec}])


def not_while_playing():
    if playtest.game_running():
        raise ValueError('New Vegas is running: close it first (it holds its plugins open while it runs).')


def play(body):
    """Save, put the mod in the game, and start it; with a place and a spot, Play here."""
    not_while_playing()
    saved = save()
    out = {'install': install.install(GD.data_dir, saved['path'])}
    if body.get('cell'):
        path = os.path.join(project.BUILD_DIR, playtest.TEST_PLUGIN)
        if body['cell'].startswith('+'):                # (a place of the mod's own: the test plugin builds on the mod)
            rec = PR.records[body['cell']]
            place = recordio.field(rec, 'FULL') or recordio.field(rec, 'EDID')
            out['test'] = playtest.write_test_plugin(GD, None, body['p'], path, place, mod=PR.plugin, own_place=(body['cell'], rec))
        else:
            cell = GD.from_key(body['cell'])
            f = GD.fields(cell)
            place = tes4.zstr(f.get('FULL', b'')) or tes4.zstr(f.get('EDID', b''))
            out['test'] = playtest.write_test_plugin(GD, cell, body['p'], path, place)
        out['test_install'] = install.install(GD.data_dir, path)      # (after the mod: newest, so it loads last)
        out['autoload'] = playtest.set_autoload(GD.data_dir, True)
    else:
        playtest.take_out_test(GD.data_dir)
        playtest.set_autoload(GD.data_dir, False)
    out['via'] = start_game()
    out['state'] = state()
    return out


def game_settings():
    """The game's settings page: the chosen settings with their values, every setting of both files, the screens."""
    files = gameini.read_all()
    final = {}
    for fn in gameini.FILES:
        for sec, k, v in files.get(fn, []):
            final[(sec.lower(), k.lower())] = v
    rows = []
    for sid, group, label, sec, key, kind, opts, note in gameini.SETTINGS:
        rows.append({'id': sid, 'group': group, 'label': label, 'section': sec, 'key': key, 'kind': kind,
                     'options': opts, 'note': note, 'value': final.get((sec.lower(), key.lower()))})
    every = {}
    for fn in gameini.FILES:
        for sec, k, v in files.get(fn, []):
            every.setdefault((sec, k), {'section': sec, 'key': k, 'files': {}})['files'][fn] = v
    return {'folder': gameini.folder(), 'files': [fn for fn in gameini.FILES if fn in files], 'settings': rows,
            'all': sorted(every.values(), key=lambda r: (r['section'].lower(), r['key'].lower())),
            'screens': gameini.screens(), 'borderless': load_settings().get('borderless'), 'intro': gameini.INTRO,
            'running': playtest.game_running()}


def game_settings_save(body):
    """body: {changes: [[section, key, value]], borderless: screen number or null (left out: as it is)}"""
    not_while_playing()
    changes = [tuple(c) for c in body.get('changes', [])]
    if 'borderless' in body:
        n = body['borderless']
        if n is not None:
            sc = gameini.screens()[int(n)]
            # windowed, the screen's size, at its top left (where Windows puts it, the screen's own corner)
            changes += [('Display', 'bFull Screen', '0'), ('Display', 'iSize W', str(sc['w'])),
                        ('Display', 'iSize H', str(sc['h'])), ('Display', 'iLocation X', str(sc['x'])),
                        ('Display', 'iLocation Y', str(sc['y']))]
        save_settings(borderless=n)
    backup = gameini.write(changes) if changes else None
    out = game_settings()
    out['backup'] = backup
    return out


def start_game():
    """Start the game the chosen way; borderless when that's on."""
    via = playtest.launch(GD.data_dir, load_settings().get('launch_via', 'nvse'))
    n = load_settings().get('borderless')
    if n is not None:
        sc = gameini.screens()
        if int(n) < len(sc):
            gameini.make_borderless(sc[int(n)])
    return via


def give(body):
    """Give it to me in game: save and put the mod in, then FOLab Test.esp, whose quest adds the item to your inventory
    once your newest save loads (JIP loads it at the menu), and start the game."""
    not_while_playing()
    key, count = body['key'], max(1, min(int(body.get('count', 1)), 100000))
    out = {}
    if PR:
        saved = save()
        out['install'] = install.install(GD.data_dir, saved['path'])
    elif key.startswith('+'):
        raise ValueError('Open the mod this item is in first.')
    rec = BR.record(key)['record']
    edid = recordio.field(rec, 'EDID') or key
    path = os.path.join(project.BUILD_DIR, playtest.TEST_PLUGIN)
    os.makedirs(project.BUILD_DIR, exist_ok=True)
    out['test'] = playtest.write_test_plugin(GD, None, None, path, give=[(key, count, edid)],
                                             mod=PR.plugin if PR else None)
    out['test_install'] = install.install(GD.data_dir, path)
    out['autoload'] = playtest.set_autoload(GD.data_dir, True)
    out['via'] = start_game()
    name = recordio.field(rec, 'FULL') or edid
    out['message'] = ('Starting New Vegas: %s%s will be in your inventory once %s loads.' %
                      ('%d × ' % count if count > 1 else '', name,
                       '"%s"' % out['autoload'] if out['autoload'] else 'a save'))
    out['state'] = state()
    return out


def save():
    path = PR.plugin_path()
    n = espwrite.write(GD, PR, path)
    return {'path': path, 'bytes': n, 'state': state()}


api_scripts.setup(lambda: GD, lambda: PR, lambda: BR, lambda: state())


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype='application/json', code=200, cache=False):
        if not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'max-age=86400' if cache else 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        try:
            if u.path in ('/', '/index.html'):
                # (the icon's address carries a hash of it: Edge keeps an app window's icon in a cache of its own,
                # so a changed icon only shows under a new address)
                with open(os.path.join(WEB, 'index.html'), encoding='utf-8') as f:
                    page = f.read()
                with open(os.path.join(WEB, 'vendor', 'folab-icon.png'), 'rb') as f:
                    tag = hashlib.md5(f.read()).hexdigest()[:10]
                page = page.replace('href="/web/vendor/folab-icon.png"', 'href="/web/vendor/folab-icon.png?v=%s"' % tag)
                return self.send(page.encode('utf-8'), 'text/html; charset=utf-8')
            if u.path.startswith('/web/'):
                p = os.path.normpath(os.path.join(WEB, u.path[5:]))
                if not p.startswith(WEB):
                    return self.send(b'no', 'text/plain', 403)
                return self.file(p)
            if u.path.startswith('/api/scripts'):
                return self.send(api_scripts.get(u.path, q))
            if u.path == '/api/about':
                return self.send(about())
            if u.path == '/api/report':
                return self.send(report().encode('utf-8'), 'text/plain; charset=utf-8')
            if u.path == '/api/doc':
                name = os.path.basename(q['name'])
                return self.file(os.path.join(WEB, 'docs', name + '.md'))
            if u.path == '/api/state':
                return self.send(state())
            if u.path == '/api/interiors':
                return self.send(interiors())
            if u.path == '/api/cell':
                with _lock:
                    return self.send(cell(q['id']))
            if u.path == '/api/navmesh/status':
                with _lock:
                    return self.send(navbuild.status(GD, PR, q['cell']) if PR else {'none': True})
            if u.path == '/api/navmesh':
                with _lock:
                    return self.send(navbuild.shape(GD, PR, q['cell']) if PR else {'source': None})
            if u.path == '/api/kits':
                with _lock:
                    return self.send(kits_list())
            if u.path == '/api/kit/piece':
                with _lock:
                    return self.send(kit_piece(q['cell'], q['key']))
            if u.path == '/api/ref':
                with _lock:
                    return self.send(ref(q['cell'], q['key']))
            if u.path == '/api/door':
                return self.send(door(q['key']))
            if u.path == '/api/gamesettings':
                return self.send(game_settings())
            if u.path == '/api/nvse/latest':
                return self.send(nvse.latest())
            if u.path == '/api/plugins':
                return self.send(adopt.candidates(GD.data_dir))
            if u.path == '/api/prefabs':
                return self.send(prefabs())
            if u.path == '/api/prefab':
                return self.send(prefab(q['name']))
            if u.path == '/api/types':
                return self.send(BR.types())
            if u.path == '/api/records':
                with _lock:
                    return self.send(BR.records(q['type'], q.get('q', '')))
            if u.path == '/api/record':
                with _lock:
                    return self.send(BR.record(q['key']))
            if u.path == '/api/resolve':
                return self.send(BR.resolve(q.get('q', '')))
            if u.path == '/api/used':
                return self.send(BR.where_used(q['key']))
            if u.path == '/api/search':
                return self.send(search(q.get('q', ''), q.get('kind', '')))
            if u.path == '/api/actor':
                with _lock:
                    return self.send(actor_parts(q['key']))
            if u.path == '/api/maptile':
                return self.send(map_tile(q['world'], int(q['tx']), int(q['ty'])), 'image/png')
            if u.path == '/api/farland':
                return self.send(far_land(q['world'], int(q['tx']), int(q['ty'])))
            if u.path == '/api/heightmap':
                data = heightmap_export(q)
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Content-Disposition', 'attachment; filename="%s %s,%s %sx%s.png"' % (
                    place_name(q['world'])[0] or 'world', q['x'], q['y'], q['w'], q['h']))
                self.end_headers()
                return self.wfile.write(data)
            if u.path == '/api/shape/tile':
                return self.send(shape_tile(q['key'], int(q['tx']), int(q['ty'])), 'image/png')
            if u.path == '/api/goto':
                return self.send(goto(q.get('q', ''), q.get('world') or None))
            if u.path == '/api/scatter':
                return self.send({'sets': scatter.SETS, 'found': scatter.learn(GD, GD.from_key(q['world']), int(q['x']), int(q['y']))})
            if u.path == '/api/landtex':
                return self.send(land_textures())
            if u.path == '/api/worlds':
                return self.send(worlds())
            if u.path == '/api/world':
                return self.send(world(q['id']))
            if u.path == '/api/outside':
                # (several squares at once, 'x,y;x,y': a browser has only a few connections, and meshes want them too)
                with _lock:
                    return self.send([outside(q['world'], *map(int, xy.split(','))) for xy in q['xy'].split(';')[:16]])
            if u.path == '/api/meshes':
                words = q.get('q', '').lower().replace('/', '\\').split()
                hits = [m for m in GD.mesh_list() if all(w in m for w in words)]
                return self.send({'total': len(hits), 'paths': hits[:int(q.get('limit', 300))]})
            if u.path == '/api/mesh':
                return self.send(mesh(q['path']), cache=True)
            if u.path == '/api/file':
                return self.send(GD.read_file(q['path']), 'application/octet-stream', cache=True)
            self.send(b'not found', 'text/plain', 404)
        except FileNotFoundError:
            self.send(b'not found', 'text/plain', 404)
        except Exception as e:
            log_error('GET ' + u.path, e)
            self.send({'error': str(e)}, code=500)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        try:
            n = int(self.headers.get('Content-Length') or 0)
            body = json.loads(self.rfile.read(n) or b'{}')
            if u.path == '/api/quit':
                # (FOLab.exe asks this when its window closes or Quit is picked: everything is saved as it's made)
                if self.headers.get('X-FOLab-Quit') != '1':
                    return self.send({'error': 'no'}, code=403)
                self.send({'ok': True})
                threading.Thread(target=SERVER.shutdown, daemon=True).start()
                return
            with _lock:
                if u.path.startswith('/api/scripts'):
                    return self.send(api_scripts.post(u.path, body))
                if u.path == '/api/nvse/download':
                    rel = nvse.latest()
                    return self.send({'version': nvse.download(rel), 'state': state()})
                if u.path == '/api/nvse/install':
                    not_while_playing()
                    return self.send({'install': nvse.install(GD.data_dir, body['version']), 'state': state()})
                if u.path == '/api/nvse/uninstall':
                    not_while_playing()
                    return self.send({'removed': nvse.uninstall(GD.data_dir), 'state': state()})
                if u.path == '/api/gamesettings':
                    return self.send(game_settings_save(body))
                if u.path == '/api/launch_via':
                    save_settings(launch_via='nvse' if body.get('via') == 'nvse' else 'steam')
                    return self.send(state())
                if u.path == '/api/give':
                    return self.send(give(body))
                if u.path == '/api/project/new':
                    return self.send(open_project(body['name'], create=True))
                if u.path == '/api/project/open':
                    return self.send(open_project(body['name']))
                if u.path == '/api/project/adopt':
                    name = adopt.adopt(GD, os.path.join(GD.data_dir, os.path.basename(body['file'])))
                    return self.send(open_project(name))
                if not PR:
                    return self.send({'error': 'Open or start a mod first.'}, code=400)
                if u.path == '/api/world/new':
                    return self.send(new_world(body))
                if u.path == '/api/shape/cells':
                    return self.send(shape_cells(body))
                if u.path == '/api/shape/preview':
                    return self.send(shape_preview(body))
                if u.path == '/api/shape/apply':
                    return self.send(shape_apply(body))
                if u.path == '/api/heightmap/import':
                    return self.send(heightmap_import(body))
                if u.path == '/api/edit':
                    return self.send(edit(body.get('label', 'Edit'), body['ops']))
                if u.path in ('/api/undo', '/api/redo'):
                    label = PR.undo() if u.path == '/api/undo' else PR.redo()
                    return self.send({'label': label, 'state': state()})
                if u.path == '/api/prefab/save':
                    return self.send(prefab_save(body))
                if u.path == '/api/place/new':
                    return self.send(new_place(body))
                if u.path == '/api/navmesh/make':
                    return self.send(navmesh_make(body['cell']))
                if u.path == '/api/navmesh/remove':
                    out = edit('Remove navmesh', [{'op': 'navmesh_revert', 'cell': body['cell']}])
                    out['navmesh'] = navbuild.status(GD, PR, body['cell'])
                    return self.send(out)
                if u.path == '/api/kit/layout':
                    return self.send(kit_layout(body))
                if u.path == '/api/doors/link':
                    return self.send(link_doors(body['a'], body['b']))
                if u.path == '/api/doors/unlink':
                    other = door(body['ref'])
                    ops = [{'op': 'tel', 'cell': body['cell'], 'ref': body['ref'], 'tel': None}]
                    if other and other.get('mine') and other.get('cell'):
                        ops.append({'op': 'tel', 'cell': other['cell'], 'ref': other['door'], 'tel': None})
                    return self.send(edit('Unlink door', ops))
                if u.path == '/api/record/save':
                    rec = body['record']
                    return self.send(edit('Edit ' + (recordio.field(rec, 'EDID') or body['key']), [{'op': 'record', 'key': body['key'], 'record': rec}]))
                if u.path == '/api/record/copy':
                    return self.send(record_copy(body['key']))
                if u.path == '/api/record/revert':
                    return self.send(edit('Put back ' + body['key'], [{'op': 'record_revert', 'key': body['key']}]))
                if u.path == '/api/project/esm':
                    PR.esm = bool(body.get('on'))
                    PR.save()
                    return self.send(state())
                if u.path == '/api/save':
                    return self.send(save())
                if u.path == '/api/play':
                    return self.send(play(body))
                if u.path == '/api/install':
                    not_while_playing()
                    saved = save()
                    return self.send({'install': install.install(GD.data_dir, saved['path']), 'state': state()})
                if u.path == '/api/uninstall':
                    not_while_playing()
                    playtest.take_out_test(GD.data_dir)
                    playtest.set_autoload(GD.data_dir, False)
                    return self.send({'install': install.uninstall(GD.data_dir, PR.plugin), 'state': state()})
            self.send(b'not found', 'text/plain', 404)
        except Exception as e:
            log_error('POST ' + u.path, e)
            self.send({'error': str(e)}, code=500)

    def file(self, p):
        if not os.path.isfile(p):
            return self.send(b'not found', 'text/plain', 404)
        with open(p, 'rb') as f:
            self.send(f.read(), TYPES.get(os.path.splitext(p)[1], 'application/octet-stream'))


def _running_here():
    """This folder's FOLab, if one is running (its folab_running.json, its process alive)."""
    try:
        with open(os.path.join(project.HOME, 'folab_running.json'), encoding='utf-8') as f:
            d = json.load(f)
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(d['pid']))
        if not h:
            return None
        ctypes.windll.kernel32.CloseHandle(h)
        return d
    except (OSError, ValueError, KeyError, AttributeError):
        return None


def main():
    global GD, CATALOGUE, PR, BR
    args = sys.argv[1:]
    port = next((int(a) for a in args if a.isdigit()), PORT)
    t = time.time()
    last = load_settings().get('project')
    if last:
        try:
            PR = project.Project.open(last)
        except (OSError, ValueError):
            PR = None
    load_game(PR)
    print('%s: %d interiors, %d placeable objects (%.1fs)' % (GD.data_dir, len(GD.interiors), len(CATALOGUE),
                                                               time.time() - t), flush=True)
    # (on Windows, address reuse lets a second FOLab bind the same port, and the browser then talks to whichever
    # answers, an old one included: refuse to start twice instead)
    ThreadingHTTPServer.allow_reuse_address = False
    asked = any(a.isdigit() for a in args)
    srv = None
    for p in ([port] if asked else range(port, port + 20)):
        try:
            srv = ThreadingHTTPServer(('127.0.0.1', p), Handler)
            port = p
            break
        except OSError:
            # (this folder's FOLab already running: say so; another program, or another folder's FOLab: the next port)
            mine = _running_here()
            if asked or (mine and mine.get('port') == p):
                print('FOLab is already running on port %d: close that one first (or open http://127.0.0.1:%d/).' % (p, p))
                sys.exit(1)
    if srv is None:
        print('No free port for FOLab between %d and %d.' % (port, port + 19))
        sys.exit(1)
    url = 'http://127.0.0.1:%d/' % port
    print('FOLab on ' + url, flush=True)
    # (for FOLab.exe: where this FOLab answers, so it can open its window and later ask it to quit)
    global SERVER
    SERVER = srv
    running = os.path.join(project.HOME, 'folab_running.json')
    with open(running, 'w', encoding='utf-8') as f:
        json.dump({'url': url, 'pid': os.getpid(), 'port': port}, f)
    import atexit
    atexit.register(lambda: os.path.exists(running) and os.remove(running))
    if '--no-browser' not in args and not os.environ.get('FOLAB_NO_BROWSER'):
        import webbrowser
        webbrowser.open(url)
    try:
        srv.serve_forever()
    finally:
        if os.path.exists(running):
            os.remove(running)


if __name__ == '__main__':
    main()
