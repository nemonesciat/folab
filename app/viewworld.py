"""Rooms with a view: a small world set under a city's world, as New Vegas sets the Lucky 38's cocktail lounge and
penthouse (Lucky38World, high over the Strip), the Strip itself and Freeside under the Mojave. The engine draws nothing
outside an interior cell, so a lobby or a penthouse with windows is built outdoors instead, in a world of its own: the
building's own copy stands at its real place with the room inside it, the land round it copied from the city, the
things near enough to be seen through the windows copied in full (`stage_ops`), and past those the city's far ground and
far buildings drawn for this world (`far_view`: lodgen and lodobj with `like` the city). You come in by a load door.

The game's sixteen such worlds all set PNAM to 4 (the parent's map only: each has its own copy of the land and its own
far view) and the Lucky 38's DATA to 0x13 (small world, no fast travel, no far water). Ours keep the far water (the
sea round Waikiki), so DATA 0x03.

`add_world` puts the world straight into the mod's own source plugin (a mod opened from a plugin, as a real-map world
is): every change the mod keeps stays as it is, only new records are added, numbered from the mod's next free ID.
server.new_world can't be used on a big mod: it bakes every change into the plugin, and keys the mod's navmeshes and
new-game settings name would no longer point anywhere."""
import math
import os
import struct

import espwrite
import formlinks
import land
import plugintree
import worldgen

FLAGS = 0x03            # (small world, can't fast travel; far water kept: the sea)
REACH_LAND = 3          # (cells each way of the room's cell with the city's ground copied)
REACH_THINGS = 3        # (cells each way with the city's things copied in full: the game loads 2 each way round you)
KEEP = ('STAT', 'SCOL', 'MSTT', 'TREE', 'LIGH', 'FURN', 'DOOR')     # (no activators: their scripts would run twice)
DISABLED = 0x800


class SourceWriter:
    """What worldgen.add_world needs of a writer, numbering as the mod's own source plugin does (its own masters)."""

    def __init__(self, gd, me):
        self.gd, self.me = gd, me
        self.masters = [m.lower() for m in gd.plugins[me].header['masters']]

    def own(self, objid):
        return (len(self.masters) << 24) | (objid & 0xFFFFFF)

    def local(self, fid):
        """A load-order form ID as the source plugin writes it."""
        pi = fid >> 24
        if pi == self.me:
            return self.own(fid)
        name = self.gd.names[pi]
        if name not in self.masters:
            raise ValueError('The mod\'s plugin doesn\'t have %s as a master.' % name)
        return (self.masters.index(name) << 24) | (fid & 0xFFFFFF)

    def link(self, key):
        return self.local(self.gd.from_key(key)) if key else 0

    def remap_fields(self, i, tag, subs):
        """Form IDs in a record copied from plugin i, from its numbering to the source plugin's (as espwrite's)."""
        if i == self.me:
            return subs
        own = len(self.gd.plugins[i].header['masters'])
        return formlinks.repoint(tag, subs, own, lambda v: self.local(self.gd.to_global(i, v)))[0]

    _group = staticmethod(espwrite.Writer._group)


def source_index(gd, pr):
    src = os.path.normcase(os.path.abspath(pr.source_path()))
    return next(i for i, p in enumerate(gd.plugins) if os.path.normcase(os.path.abspath(p.path)) == src)


def land_options(gd, pr, parent, cx, cy, reach=REACH_LAND):
    """worldgen.add_world's options for the city's ground round cell (cx, cy): the mod's own land where it has some, else
    the plugin's, wet where the city's cell is."""
    grid = gd.grid(parent)
    cache = {}
    dn = gd.fields(parent).get('DNAM') or b''
    low = struct.unpack_from('<f', dn)[0] if len(dn) >= 4 else 0.0
    sea = struct.unpack_from('<f', dn, 4)[0] if len(dn) >= 8 else 0.0

    def land_for(x, y):
        c = grid.get((x, y))
        L = pr.land.get(gd.key(c)) if c is not None else None
        if L is None:
            e = gd.land_at(parent, x, y)
            L = land.decode(gd, e, cache) if e else None
        if L is None or not L.get('h'):
            L = {'h': [low] * 1089, 'c': None, 'q': [{'bkey': None, 'base': None, 'layers': []} for _ in range(4)]}
        return L, None

    def wet(x, y):
        c = grid.get((x, y))
        if c is None:
            return True
        if gd.key(c) in pr.water:
            h = pr.water[gd.key(c)]             # (None: the world's level; else the level the mod gave it)
        else:
            f = gd.fields(c)
            if not (f.get('DATA') or b'\0')[0] & 0x02:
                return False
            x_ = f.get('XCLW')
            h = struct.unpack_from('<f', x_)[0] if x_ and len(x_) >= 4 else None
        # (True for the world's level, FLT_MAX or the level itself; else the cell's own level, a dry cell's too: it has
        # the flag all the same, its level far under the ground, espwrite.dry)
        return True if h is None or h > 1e30 or abs(h - sea) < 1.0 else h
    n = 2 * reach + 1
    return {'rect': (cx - reach, cy - reach, n, n), 'land_for': land_for, 'wet': wet, 'height': low, 'ltex': None,
            'parent': parent, 'flags': FLAGS}


def add_world(gd, pr, parent, edid, name, cx, cy, reach=REACH_LAND):
    """Add the small world to the mod's source plugin (the mod must be one opened from a plugin). Returns its form ID as
    the plugin numbers it; the mod's next free ID moves past what was used. The game must be loaded again after."""
    if not pr.source:
        raise ValueError('Only a mod opened from a plugin can have a world added this way.')
    me = source_index(gd, pr)
    path = pr.source_path()
    tree = plugintree.Plugin.read(path)
    w = SourceWriter(gd, me)
    opts = dict(land_options(gd, pr, parent, cx, cy, reach), edid=edid, name=name, template=parent)
    wid, nid = worldgen.add_world(gd, tree, w, pr.next_id, opts)
    worldgen.fix_header(tree, w.own(nid))
    data = tree.bytes()
    for p in gd.plugins:
        if p is gd.plugins[me]:
            p.close()
    with open(path + '.tmp', 'wb') as f:
        f.write(data)
    os.replace(path + '.tmp', path)
    pr.next_id = nid
    return wid


# ---------- the city round it ----------

def _kind(gd, pr, base):
    if isinstance(base, str):
        r = pr.records.get(base)
        return r.get('type') if r else None
    e = gd.forms.get(base)
    return e[1].tag if e else None


def city_things(gd, pr, parent, cells):
    """The city's things standing in these grid cells, as the mod has them: (base key, p [x y z rx ry rz], scale, kind),
    the ones worth seeing only (no actors, no markers, nothing initially off)."""
    grid = gd.grid(parent)
    want = {grid[k] for k in cells if k in grid}
    changed = {}
    for ck, c in pr.cells.items():
        for rk, r in c['refs'].items():
            if not rk.startswith('+'):
                changed[rk] = r
    out = []
    pc = gd.world_persistent.get(parent)
    srcs = [(c, None) for c in want] + ([(pc, set(cells))] if pc is not None else [])
    for cell, only in srcs:
        for r in gd.refs(cell):
            if r['type'] != 'REFR' or r['base'] is None or not r['pos']:
                continue
            if only is not None and (int(r['pos'][0] // 4096), int(r['pos'][1] // 4096)) not in only:
                continue
            entry = gd.cell_refs[cell].get(r['ref']) if cell in gd.cell_refs else None
            if entry is not None and entry[1].flags & DISABLED:
                continue
            ch = changed.get(gd.key(r['ref']))
            if ch is not None and ch.get('removed'):
                continue
            kind = _kind(gd, pr, r['base'])
            if kind not in KEEP:
                continue
            edid = (gd.edid(r['base']) or '').lower()
            if 'marker' in edid:
                continue
            p = (ch.get('p') if ch else None) or (list(r['pos']) + list(r['rot']))
            out.append((gd.key(r['base']), list(p), float((ch or {}).get('s') or r['scale'] or 1.0), kind, gd.key(r['ref'])))
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        try:
            cell = gd.from_key(ck)
        except (ValueError, KeyError):
            continue
        if cell not in want:
            continue
        for rk, r in c['refs'].items():
            if not rk.startswith('+') or r.get('removed') or not r.get('base') or not r.get('p'):
                continue
            b = r['base']
            kind = _kind(gd, pr, b if b[:1] in ('+', '$') else gd.from_key(b))
            if kind not in KEEP:
                continue
            out.append((b, list(r['p']), float(r.get('s') or 1.0), kind, rk))
    return out


def stage_ops(gd, pr, parent, child, cx, cy, reach=REACH_THINGS, skip=None):
    """Ops copying the city's things round cell (cx, cy) into the small world, where they stand: doors locked and leading
    nowhere, activators as they look (their scripts left off: they'd run twice). skip(base key, p) -> True leaves one out
    (the building the room is in, which the world gets in its own form)."""
    cells = [(x, y) for x in range(cx - reach, cx + reach + 1) for y in range(cy - reach, cy + reach + 1)]
    grid = gd.grid(child)
    ops = []
    for base, p, s, kind, src in city_things(gd, pr, parent, cells):
        if skip and skip(base, p):
            continue
        cell = grid.get((int(p[0] // 4096), int(p[1] // 4096)))
        if cell is None:
            continue
        o = {'op': 'add', 'cell': gd.key(cell), 'base': base, 'p': [round(v, 4) for v in p], 's': round(s, 3)}
        if kind == 'DOOR':
            o['extra'] = {'props': {'lock': {'level': 255, 'key': '', 'leveled': False}}}
        ops.append(o)
    return ops


def far_view(gd, pr, child, parent, out):
    """The city's far ground and far buildings, drawn for the small world (into out, laid out as Data is)."""
    import lodgen
    import lodobj
    a = lodgen.generate(gd, pr, child, out, beyond=True, like=parent)
    b = lodobj.generate(gd, pr, child, out, like=parent)
    return {'ground': a, 'buildings': b}


def turn(lx, ly, rz):
    """A point in a building's own frame (rz its turn, as the game turns things: clockwise) to the world's axes."""
    c, s = math.cos(rz), math.sin(rz)
    return lx * c + ly * s, -lx * s + ly * c
