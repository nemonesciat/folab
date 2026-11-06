"""New Vegas navmeshes: the NAVM and NAVI records as plain structures, encoded back byte for byte, and the rules that
join meshes together. navgen.py builds new meshes from a cell's geometry. Everything below was checked against every
record in the game's files (FalloutNV.esm and the DLCs; run this file as a script to see the check again).

NAVM, one mesh, a child of its CELL in the cell's temporary group. All its form IDs are in its file's numbering.
    NVER        version, always 11
    DATA        the CELL, then counts: vertices, triangles, outside links, cover triangles, door links
    NVVX        vertices: x, y, z floats, in the world's coordinates
    NVTR        triangles, 16 bytes each: three corners, three edges, flags, cover flags. Corners run anticlockwise from
                above. Edge i runs from corner i to corner i + 1 and holds the triangle across it (NONE if there is
                none), or, when flag bit i is set, a number in NVEX.
    NVCA        the triangles with cover flags. Optional: 3,596 of the 6,129 meshes the game ends up with have none, and actors then just don't
                use cover there, so generated meshes leave it out.
    NVDP        door links, 8 bytes each: the door's REFR, the triangle by it, and two bytes of leftover junk
    NVGD        the search grid: side (from the triangle count, see grid_side), cell width and height, the box of the
                vertices, then for each cell, row by row from the south, a count and that many triangles. A game grid
                is the exact triangle/cell overlap of build_grid plus about 1.4% extra entries.
    NVEX        outside links, 10 bytes each: kind, target NAVM, triangle in it. Kind 0: across a cell edge (or to
                another mesh in the cell); the edge lies exactly on the border in 88,824 of FalloutNV.esm's 94,303. Kinds 1 and 2 (120
                each, always within one cell): a link up (1) or down (2) a ledge, between triangles that don't touch.
    Triangle flags: 1, 2, 4 edge links outside; 0x40 preferred path; 0x200 in water; 0x400 a door's triangle;
    0x800 'found', on every triangle in the game. Links are mutual: a triangle's neighbour has a link back along the same
    edge (always within a mesh; across meshes, in FalloutNV.esm, all but 71 of 94,447, and 96 more are stale, naming a
    triangle that no longer exists).

    Links across a cell edge need not join corner to corner: only 23% do (FalloutNV.esm). Each is one edge to one triangle.

NAVI, the master index: one record, form 014B92 of FalloutNV.esm, overridden by each DLC with just its own entries.
    NVER        version, 11
    NVMI        one per mesh, all of them before any NVCI: flags, the NAVM, the space (WRLD outside, the CELL inside),
                the grid square ((x << 16) | (y & 0xFFFF), 0 inside), the mean of the mesh's vertices, an outline if
                flag 0x20, then the share of its triangles that are preferred. The outline is the box and a rough copy
                of the mesh (vertices then triangles, some or no vertices of the mesh). Every mesh of a cell but one has
                an outline, and no mesh that is alone in its cell does, bar one: so a cell with one mesh needs none.
    NVCI        one per mesh: the NAVM, then counted lists: meshes joined through its edges, those joined through
                preferred triangles, and its doors (the same list as its NVDP). Rebuilt by links_for.
    info_for and links_for give back what the game stores: all 4,771 of FalloutNV.esm's position, value and doors, and
    the meshes it joins (in the same order in all but 5, which differ only in order), and the place and space of all.

What a plugin must do to add or change a navmesh and keep NAVI valid:
  - Add the NAVM under the CELL's temporary group (form ID its own for a new mesh, the old one to replace a mesh).
  - Override NAVI (form 014B92, FalloutNV.esm's) with NVER 11, then NVMI and NVCI for each mesh it adds or changes,
    and only those: the game merges entries mesh by mesh, as the DLCs rely on. (A mesh with no NVMI anywhere is unknown
    to the game: an NVCI naming one stops NAVI loading.) A new NVMI alone leaves the mesh's old lists until its NVCI.
  - Give each door with a link its XNDP (the NAVM and the triangle, 8 bytes): door_link. Door refs in NVDP and NVCI are
    REFRs in the same cell, or the world's persistent cell.
  - Links are triangle numbers, so if a mesh's triangles are renumbered, every mesh linking to it must be overridden too
    with new NVEX entries (link_edges does this, leaving the neighbour's triangles alone), and given new NVMI and NVCI
    if what it joins changed.
  - One mesh to a cell needs no outline. Replacing a cell's several meshes with one: the others can't be removed (the
    game has no deleted NAVM to copy from), so each is overridden as a stub_mesh: one triangle, deep under the ground, with
    an outline (the game itself has 148 one-triangle meshes). Tried in files, not yet in the game.
"""
import struct

import tes4

NONE = 0xFFFF           # 'no triangle here' in an edge
VERSION = 11            # NVER of every record in the game's files
NAVI_FORM = 0x014B92    # the one NAVI, FalloutNV.esm's: every DLC overrides this same form ID
GRID_HEAD = '<I8f'
GRID_HEAD_SIZE = struct.calcsize(GRID_HEAD)
# Triangle flags
F_EDGE0, F_EDGE1, F_EDGE2 = 1, 2, 4     # that edge (corner i to corner i + 1) links outside, through 'ext'
F_PREFERRED = 0x40
F_WATER = 0x200
F_DOOR = 0x400
F_FOUND = 0x800                         # set on every triangle in the game's files
# NVMI flags
INFO_EMPTY = 0x08
INFO_OUTLINE = 0x20


def _sub(tag, data):
    """A subrecord; one too long for its 16-bit size goes after an XXXX giving the real size."""
    tag = tag.encode('ascii')
    if len(data) > 0xFFFF:
        return b'XXXX' + struct.pack('<HI', 4, len(data)) + tag + b'\0\0' + data
    return tag + struct.pack('<H', len(data)) + data


def _floats(d):
    return struct.unpack('<%df' % (len(d) // 4), d)


def _triples(values):
    return [tuple(values[i:i + 3]) for i in range(0, len(values), 3)]


def _pack_triples(items):
    return struct.pack('<%df' % (3 * len(items)), *(v for it in items for v in it))


# --- NAVM ---

def read_navm(data):
    """A NAVM's subrecord bytes as a dict."""
    m = {'version': VERSION, 'cell': 0, 'verts': [], 'tris': [], 'cover': [], 'doors': [], 'grid': None, 'ext': [],
         'order': []}
    counts = None
    for tag, d in tes4.iter_subrecords(data):
        m['order'].append(tag)
        if tag == 'NVER':
            m['version'] = struct.unpack('<I', d)[0]
        elif tag == 'EDID':
            m['edid'] = d
        elif tag == 'DATA':
            m['cell'], *counts = struct.unpack('<6I', d)
            m['counts'] = counts
        elif tag == 'NVVX':
            m['verts'] = _triples(_floats(d))
        elif tag == 'NVTR':
            m['tris'] = list(struct.iter_unpack('<8H', d))
        elif tag == 'NVCA':
            m['cover'] = list(struct.unpack('<%dH' % (len(d) // 2), d))
        elif tag == 'NVDP':
            m['doors'] = list(struct.iter_unpack('<IHH', d))
        elif tag == 'NVGD':
            m['grid'] = read_grid(d)
        elif tag == 'NVEX':
            m['ext'] = list(struct.iter_unpack('<IIH', d))
        else:
            raise ValueError('NAVM: unknown subrecord ' + tag)
    return m


def read_grid(d):
    """The search grid: side cells by side cells over the mesh's box; each cell lists the triangles touching it."""
    head = struct.unpack_from(GRID_HEAD, d)
    pos, cells = GRID_HEAD_SIZE, []
    for _ in range(head[0] * head[0]):
        n = struct.unpack_from('<H', d, pos)[0]
        cells.append(list(struct.unpack_from('<%dH' % n, d, pos + 2)))
        pos += 2 + 2 * n
    if pos != len(d):
        raise ValueError('NVGD: %d bytes left over' % (len(d) - pos))
    return {'side': head[0], 'cw': head[1], 'ch': head[2], 'min': head[3:6], 'max': head[6:9], 'cells': cells}


def write_grid(g):
    out = [struct.pack(GRID_HEAD, g['side'], g['cw'], g['ch'], *g['min'], *g['max'])]
    for c in g['cells']:
        out.append(struct.pack('<H%dH' % len(c), len(c), *c))
    return b''.join(out)


def write_navm(m):
    """A mesh read from a record keeps its record's order and counts; a new one gets the order the game writes,
    with the optional lists left out when empty."""
    order = m.get('order') or ['NVER', 'DATA', 'NVVX', 'NVTR'] + ['NVCA'] * bool(m['cover']) + \
        ['NVDP'] * bool(m['doors']) + ['NVGD'] + ['NVEX'] * bool(m['ext'])
    parts = {
        'NVER': lambda: struct.pack('<I', m['version']),
        'EDID': lambda: m['edid'],
        'DATA': lambda: struct.pack('<6I', m['cell'], *m.get('counts', (len(m['verts']), len(m['tris']), len(m['ext']),
                                                                        len(m['cover']), len(m['doors'])))),
        'NVVX': lambda: _pack_triples(m['verts']),
        'NVTR': lambda: b''.join(struct.pack('<8H', *t) for t in m['tris']),
        'NVCA': lambda: struct.pack('<%dH' % len(m['cover']), *m['cover']),
        'NVDP': lambda: b''.join(struct.pack('<IHH', *e) for e in m['doors']),
        'NVGD': lambda: write_grid(m['grid']),
        'NVEX': lambda: b''.join(struct.pack('<IIH', *e) for e in m['ext']),
    }
    return b''.join(_sub(t, parts[t]()) for t in order)


# --- NAVI ---

def read_navi(data):
    n = {'version': VERSION, 'order': [], 'info': [], 'links': []}
    for tag, d in tes4.iter_subrecords(data):
        n['order'].append(tag)
        if tag == 'NVER':
            n['version'] = struct.unpack('<I', d)[0]
        elif tag == 'NVMI':
            n['info'].append(read_nvmi(d))
        elif tag == 'NVCI':
            n['links'].append(read_nvci(d))
        else:
            raise ValueError('NAVI: unknown subrecord ' + tag)
    return n


def read_nvmi(d):
    flags, navm, space, place = struct.unpack_from('<4I', d)
    pos = struct.unpack_from('<3f', d, 16)
    p = 28
    out = {'flags': flags, 'navm': navm, 'space': space, 'place': place, 'pos': pos, 'outline': None}
    if flags & 0x20:
        lo = struct.unpack_from('<3f', d, p)
        hi = struct.unpack_from('<3f', d, p + 12)
        nv, nt = struct.unpack_from('<2H', d, p + 24)
        p += 28
        verts = _triples(struct.unpack_from('<%df' % (3 * nv), d, p))
        p += 12 * nv
        tris = _triples(struct.unpack_from('<%dH' % (3 * nt), d, p))
        p += 6 * nt
        out['outline'] = {'min': lo, 'max': hi, 'verts': verts, 'tris': tris}
    out['value'] = struct.unpack_from('<f', d, p)[0]
    if p + 4 != len(d):
        raise ValueError('NVMI: %d bytes left over' % (len(d) - p - 4))
    return out


def write_nvmi(e):
    out = [struct.pack('<4I3f', e['flags'], e['navm'], e['space'], e['place'], *e['pos'])]
    o = e['outline']
    if o is not None:
        out.append(struct.pack('<6f2H', *o['min'], *o['max'], len(o['verts']), len(o['tris'])))
        out.append(_pack_triples(o['verts']))
        out.append(b''.join(struct.pack('<3H', *t) for t in o['tris']))
    out.append(struct.pack('<f', e['value']))
    return b''.join(out)


def read_nvci(d):
    navm = struct.unpack_from('<I', d)[0]
    p, lists = 4, []
    for _ in range(3):
        n = struct.unpack_from('<I', d, p)[0]
        lists.append(list(struct.unpack_from('<%dI' % n, d, p + 4)))
        p += 4 + 4 * n
    if p != len(d):
        raise ValueError('NVCI: %d bytes left over' % (len(d) - p))
    return {'navm': navm, 'adjacent': lists[0], 'preferred': lists[1], 'doors': lists[2]}


def write_nvci(e):
    out = [struct.pack('<I', e['navm'])]
    for k in ('adjacent', 'preferred', 'doors'):
        out.append(struct.pack('<I%dI' % len(e[k]), len(e[k]), *e[k]))
    return b''.join(out)


def write_navi(n):
    info, links = iter(n['info']), iter(n['links'])
    out = []
    for t in n['order']:
        out.append(_sub(t, struct.pack('<I', n['version']) if t == 'NVER' else
                        write_nvmi(next(info)) if t == 'NVMI' else write_nvci(next(links))))
    return b''.join(out)


def new_navi(info, links):
    """A plugin's NAVI: entries only for the meshes it adds or changes (the game merges it into the one it has)."""
    return {'version': VERSION, 'info': list(info), 'links': list(links),
            'order': ['NVER'] + ['NVMI'] * len(info) + ['NVCI'] * len(links)}


# --- the search grid ---

def grid_side(ntris):
    """How many cells a side the game's grids have, for a mesh this many triangles big (true of every mesh in the game)."""
    if ntris <= 16:
        return 1
    return 2 if ntris < 50 else min(12, ntris // 50 + 2)


def _overlaps(tri, x0, y0, x1, y1):
    """Does a triangle (three (x, y)s) touch a box, seen from above."""
    (ax, ay), (bx, by), (cx, cy) = tri
    for (px, py), (qx, qy) in (((ax, ay), (bx, by)), ((bx, by), (cx, cy)), ((cx, cy), (ax, ay))):
        nx, ny = qy - py, px - qx
        ds = (nx * (ax - px) + ny * (ay - py), nx * (bx - px) + ny * (by - py), nx * (cx - px) + ny * (cy - py))
        rs = [nx * (x - px) + ny * (y - py) for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
        if max(ds) < min(rs) or min(ds) > max(rs):
            return False
    return True


def build_grid(verts, tris):
    """The search grid of a mesh: row by row from the south, each cell listing the triangles touching it."""
    n = len(tris)
    s = grid_side(n)
    if not verts:
        return {'side': 1, 'cw': 0.0, 'ch': 0.0, 'min': (0.0,) * 3, 'max': (0.0,) * 3, 'cells': [[]]}
    lo = tuple(min(v[k] for v in verts) for k in range(3))
    hi = tuple(max(v[k] for v in verts) for k in range(3))
    cw, ch = (hi[0] - lo[0]) / s, (hi[1] - lo[1]) / s
    cells = [[] for _ in range(s * s)]
    for ti, t in enumerate(tris):
        tri = [verts[i][:2] for i in t[:3]]
        xs, ys = [p[0] for p in tri], [p[1] for p in tri]
        c0 = min(int((min(xs) - lo[0]) / cw), s - 1) if cw else 0
        c1 = min(int((max(xs) - lo[0]) / cw), s - 1) if cw else 0
        r0 = min(int((min(ys) - lo[1]) / ch), s - 1) if ch else 0
        r1 = min(int((max(ys) - lo[1]) / ch), s - 1) if ch else 0
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if s == 1 or _overlaps(tri, lo[0] + c * cw, lo[1] + r * ch, lo[0] + (c + 1) * cw, lo[1] + (r + 1) * ch):
                    cells[r * s + c].append(ti)
    return {'side': s, 'cw': cw, 'ch': ch, 'min': lo, 'max': hi, 'cells': cells}


# --- what NAVI says about a mesh ---

def info_for(m, navm, space, place=0):
    """The NVMI entry of a mesh of one piece (no outline). space: its WRLD, or its CELL when inside; place: its grid
    square (grid_place), 0 inside."""
    n = len(m['verts']) or 1
    pos = tuple(sum(v[k] for v in m['verts']) / n for k in range(3))
    tris = m['tris']
    preferred = sum(1 for t in tris if t[6] & F_PREFERRED)
    return {'flags': 0 if tris else INFO_EMPTY, 'navm': navm, 'space': space, 'place': place, 'pos': pos,
            'outline': None, 'value': preferred / len(tris) if tris else 0.0}


def links_for(m, navm):
    """The NVCI entry of a mesh: the meshes it joins through its edges (through a preferred triangle or not) and
    the doors on it, each named once, in the order the triangles first reach them."""
    adjacent, preferred = [], []
    for t in m['tris']:
        for i in range(3):
            if t[6] >> i & 1 and t[3 + i] < len(m['ext']):
                other = m['ext'][t[3 + i]][1]
                if t[6] & F_PREFERRED:
                    if other in adjacent:
                        adjacent.remove(other)
                    if other not in preferred:
                        preferred.append(other)
                elif other not in adjacent:
                    adjacent.append(other)
    return {'navm': navm, 'adjacent': adjacent, 'preferred': preferred, 'doors': [d[0] for d in m['doors']]}


def grid_place(x, y):
    return (x & 0xFFFF) << 16 | (y & 0xFFFF)


def outline_of(m):
    """An outline for NVMI: the mesh's box and a copy of it (the game's are rough copies, some exact, some empty)."""
    V = m['verts']
    return {'min': tuple(min(v[k] for v in V) for k in range(3)), 'max': tuple(max(v[k] for v in V) for k in range(3)),
            'verts': [tuple(v) for v in V], 'tris': [tuple(t[:3]) for t in m['tris']]}


STUB_Z = -30000.0


def stub_mesh(x, y):
    """What's left of a mesh that had to go: one triangle deep under the place, joined to nothing."""
    verts = [(x, y, STUB_Z), (x + 64.0, y, STUB_Z), (x, y + 64.0, STUB_Z)]
    tris = [(0, 1, 2, NONE, NONE, NONE, F_FOUND, 0)]
    return {'version': VERSION, 'verts': verts, 'tris': tris, 'cover': [], 'doors': [], 'ext': [], 'grid': build_grid(verts, tris)}


# --- joining meshes: doors ---

DOOR_REACH = 1024.0     # the game's door triangles are within 546 of their door 99% of the time, at most 1,279
CELL_SIZE = 4096.0
LINK_HEIGHT = 48.0      # two edges this far apart in height are not the same bit of ground
LINK_OVERLAP = 8.0      # edges that share less of the border than this are not linked
SPLIT_NEAR = 8.0        # no new corner this close to an old one


def door_link(navm, tri):
    """The XNDP of a door's REFR: which mesh and triangle it stands by."""
    return struct.pack('<IHH', navm, tri, 0)


def _tri_distance(p, a, b, c):
    """How far a point is from a triangle: along the ground to it, and up or down from it to the point."""
    d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if d:
        l1 = ((b[1] - c[1]) * (p[0] - c[0]) + (c[0] - b[0]) * (p[1] - c[1])) / d
        l2 = ((c[1] - a[1]) * (p[0] - c[0]) + (a[0] - c[0]) * (p[1] - c[1])) / d
        l3 = 1 - l1 - l2
        if l1 >= 0 and l2 >= 0 and l3 >= 0:
            return abs(l1 * a[2] + l2 * b[2] + l3 * c[2] - p[2])
    best = None
    for q, r in ((a, b), (b, c), (c, a)):
        dx, dy = r[0] - q[0], r[1] - q[1]
        ln = dx * dx + dy * dy
        f = max(0.0, min(1.0, ((p[0] - q[0]) * dx + (p[1] - q[1]) * dy) / ln)) if ln else 0.0
        e = ((q[0] + f * dx - p[0]) ** 2 + (q[1] + f * dy - p[1]) ** 2 + (q[2] + f * (r[2] - q[2]) - p[2]) ** 2) ** 0.5
        best = e if best is None or e < best else best
    return best


def link_doors(m, doors):
    """Tie doors to their nearest triangles: doors is [(door REFR, (x, y, z))]. Marks the triangles and lists the doors.
    Returns ({door: triangle} to give each its XNDP, [doors with no triangle within DOOR_REACH])."""
    found, missed = {}, []
    V = m['verts']
    for ref, pos in doors:
        best, bd = None, DOOR_REACH
        for ti, t in enumerate(m['tris']):
            d = _tri_distance(pos, V[t[0]], V[t[1]], V[t[2]])
            if d < bd:
                best, bd = ti, d
        if best is None:
            missed.append(ref)
            continue
        t = m['tris'][best]
        m['tris'][best] = t[:6] + (t[6] | F_DOOR,) + t[7:]
        m['doors'].append((ref, best, 0))
        found[ref] = best
    _touch(m)
    return found, missed


# --- joining meshes: across a cell's edge ---

def _touch(m):
    """A mesh has changed: forget the counts and order it was read with."""
    m.pop('counts', None)
    m.pop('order', None)


def renumber(m, fn):
    """A copy of a mesh with fn applied to each of its form IDs, from one file's numbering to another's."""
    out = dict(m, cell=fn(m['cell']), ext=[(k, fn(n), t) for k, n, t in m['ext']],
               doors=[(fn(r), t, p) for r, t, p in m['doors']])
    return out


def _forget_links(m, target):
    """Clear the links of m to mesh target, renumbering the rest."""
    keep, new = [], {}
    for i, e in enumerate(m['ext']):
        if e[1] != target:
            new[i] = len(keep)
            keep.append(e)
    if len(keep) == len(m['ext']):
        return
    for ti, t in enumerate(m['tris']):
        edges, fl = list(t[3:6]), t[6]
        for i in range(3):
            if fl >> i & 1:
                if edges[i] in new:
                    edges[i] = new[edges[i]]
                else:
                    edges[i] = NONE
                    fl &= ~(1 << i)
        m['tris'][ti] = t[:3] + tuple(edges) + (fl, t[7])
    m['ext'] = keep
    _touch(m)


def _on_line(m, axis, value):
    """The unlinked edges lying on a border: (triangle, edge, along from, along to, height from, height to)."""
    V = m['verts']
    other = 1 - axis
    out = []
    for ti, t in enumerate(m['tris']):
        for i in range(3):
            if t[6] >> i & 1 or t[3 + i] != NONE:
                continue
            a, b = V[t[i]], V[t[(i + 1) % 3]]
            if abs(a[axis] - value) < 0.5 and abs(b[axis] - value) < 0.5:
                out.append((ti, i, a[other], b[other], a[2], b[2]))
    return out


def _split(m, ti, i, pos):
    """Put a new corner at pos on border edge i of triangle ti, making two triangles. No change if it would disturb a
    link to another mesh, whose numbers we may not change. Returns True if done."""
    t = m['tris'][ti]
    if t[6] & (F_EDGE0 | F_EDGE1 | F_EDGE2):
        return False
    j, k = (i + 1) % 3, (i + 2) % 3
    a, b, c = t[i], t[j], t[k]
    n = len(m['verts'])
    new = len(m['tris'])
    m['verts'].append(tuple(pos))
    across_bc, across_ca = t[3 + j], t[3 + k]
    m['tris'][ti] = (a, n, c, NONE, new, across_ca, t[6], 0)
    m['tris'].append((n, b, c, NONE, across_bc, ti, t[6] & ~F_DOOR, 0))
    if across_bc != NONE:
        o = m['tris'][across_bc]
        m['tris'][across_bc] = o[:3] + tuple(new if x == ti else x for x in o[3:6]) + o[6:]
    _touch(m)
    return True


def _split_at(m, axis, value, points):
    """Split m's border edges at points (along, height) of the other mesh, so the two have the same corners."""
    other = 1 - axis
    done = 0
    for along, z in points:
        for ti, i, p, q, zp, zq in _on_line(m, axis, value):
            lo, hi = min(p, q), max(p, q)
            if lo + SPLIT_NEAR < along < hi - SPLIT_NEAR:
                f = (along - p) / (q - p)
                here = zp + f * (zq - zp)
                if abs(here - z) <= LINK_HEIGHT:
                    pos = [0.0, 0.0, here]
                    pos[axis], pos[other] = value, along
                    if _split(m, ti, i, pos):
                        done += 1
                    break
    return done


def _corners_on(m, axis, value):
    other = 1 - axis
    used = set()
    for ti, i, _p, _q, _zp, _zq in _on_line(m, axis, value):
        t = m['tris'][ti]
        used.update((t[i], t[(i + 1) % 3]))
    return [(m['verts'][v][other], m['verts'][v][2]) for v in used]


def _link(m, ti, i, target, tri):
    t = m['tris'][ti]
    edges = list(t[3:6])
    edges[i] = len(m['ext'])
    m['ext'].append((0, target, tri))
    m['tris'][ti] = t[:3] + tuple(edges) + (t[6] | 1 << i, t[7])
    _touch(m)


def link_edges(a, a_id, a_xy, b, b_id, b_xy, split_b=True):
    """Join the meshes of two neighbouring outside cells where their edges meet on the border, edge to edge, both ways.
    a is split at b's corners so edges can match; b too, unless split_b is False (a mesh of the game's, whose triangle
    numbers others rely on: its edges are only given links). Any links the two had to each other are replaced.
    Returns the number of edges joined. Update the grids (refresh) when all the linking is done."""
    if a_xy[0] != b_xy[0]:
        axis = 0
        value = max(a_xy[0], b_xy[0]) * CELL_SIZE
    else:
        axis = 1
        value = max(a_xy[1], b_xy[1]) * CELL_SIZE
    if abs(a_xy[0] - b_xy[0]) + abs(a_xy[1] - b_xy[1]) != 1:
        raise ValueError('not neighbours: %r %r' % (a_xy, b_xy))
    _forget_links(a, b_id)
    _forget_links(b, a_id)
    _split_at(a, axis, value, _corners_on(b, axis, value))
    if split_b:
        _split_at(b, axis, value, _corners_on(a, axis, value))
    pairs = []
    b_edges = _on_line(b, axis, value)
    for ea in _on_line(a, axis, value):
        la, ha = min(ea[2], ea[3]), max(ea[2], ea[3])
        for eb in b_edges:
            lb, hb = min(eb[2], eb[3]), max(eb[2], eb[3])
            over = min(ha, hb) - max(la, lb)
            if over < LINK_OVERLAP:
                continue
            mid = (max(la, lb) + min(ha, hb)) / 2
            za = ea[4] + (mid - ea[2]) / (ea[3] - ea[2]) * (ea[5] - ea[4]) if ea[3] != ea[2] else ea[4]
            zb = eb[4] + (mid - eb[2]) / (eb[3] - eb[2]) * (eb[5] - eb[4]) if eb[3] != eb[2] else eb[4]
            if abs(za - zb) <= LINK_HEIGHT:
                pairs.append((-over, abs(za - zb), ea[:2], eb[:2]))
    pairs.sort()
    used_a, used_b = set(), set()
    n = 0
    for _o, _d, ea, eb in pairs:
        if ea in used_a or eb in used_b:
            continue
        used_a.add(ea)
        used_b.add(eb)
        _link(a, ea[0], ea[1], b_id, eb[0])
        _link(b, eb[0], eb[1], a_id, ea[0])
        n += 1
    return n


def refresh(m, grid=True):
    """After changing a mesh: its grid again (leave it, grid False, if only links changed: the triangles are the same)."""
    if grid:
        m['grid'] = build_grid(m['verts'], m['tris'])
    _touch(m)
    return m


# --- every record in the game, read and written back ---

def check_files(data_dir=None, names=None):
    """Read and rewrite every NAVM and NAVI in the game's files: [(file, record count, [records that differ])]."""
    import os
    import gamedata
    data_dir = data_dir or gamedata.find_data_dir()
    out = []
    for name in names or gamedata.OFFICIAL:
        path = os.path.join(data_dir, name)
        if not os.path.isfile(path):
            continue
        p = tes4.PluginFile(path)
        count, bad = 0, []
        for r, _g in p.walk():
            if r.tag == 'NAVM':
                raw, back = p.data(r), None
                back = write_navm(read_navm(raw))
            elif r.tag == 'NAVI':
                raw = p.data(r)
                back = write_navi(read_navi(raw))
            else:
                continue
            count += 1
            if back != raw:
                bad.append(r.formid)
        p.close()
        out.append((name, count, bad))
    return out


if __name__ == '__main__':
    for fname, n, wrong in check_files():
        print('%-24s %5d records, %d differ %s' % (fname, n, len(wrong), ['%08X' % w for w in wrong[:5]]))


# --- validity ---

def validate(m, others=None, navm=None):
    """What is wrong with a mesh, as a list of strings; empty when it is sound. others: {navm id: mesh} to follow
    links across meshes, with navm this mesh's own id (links to meshes not given are left unchecked)."""
    out = []
    nv, nt = len(m['verts']), len(m['tris'])
    tris = m['tris']
    if 'counts' in m and m['counts'] != [nv, nt, len(m['ext']), len(m['cover']), len(m['doors'])]:
        out.append('DATA counts differ from the lists')
    for ti, t in enumerate(tris):
        if max(t[:3]) >= nv:
            out.append('triangle %d: a corner past the vertices' % ti)
            continue
        if len(set(t[:3])) < 3:
            out.append('triangle %d: two corners the same' % ti)
        for i in range(3):
            e = t[3 + i]
            if t[6] >> i & 1:
                if e >= len(m['ext']):
                    out.append('triangle %d edge %d: no such outside link %d' % (ti, i, e))
                    continue
                _kind, target, tri = m['ext'][e]
                o = (others or {}).get(target)
                if o is None:
                    continue
                if tri >= len(o['tris']):
                    out.append('triangle %d edge %d: mesh %s has no triangle %d' % (ti, i, target, tri))
                elif navm is not None:
                    ot = o['tris'][tri]
                    if not any(ot[6] >> j & 1 and ot[3 + j] < len(o['ext'])
                               and o['ext'][ot[3 + j]][1:] == (navm, ti) for j in range(3)):
                        out.append('triangle %d edge %d: mesh %s triangle %d does not link back' % (ti, i, target, tri))
            elif e != NONE:
                if e >= nt:
                    out.append('triangle %d edge %d: no triangle %d' % (ti, i, e))
                    continue
                pair = {t[i], t[(i + 1) % 3]}
                ot = tris[e]
                if not any(ot[3 + j] == ti and not ot[6] >> j & 1 and {ot[j], ot[(j + 1) % 3]} == pair for j in range(3)):
                    out.append('triangle %d edge %d: triangle %d does not link back along that edge' % (ti, i, e))
    for d in m['doors']:
        if d[1] >= nt:
            out.append('door %s on no triangle %d' % (d[0], d[1]))
        elif not tris[d[1]][6] & F_DOOR:
            out.append('door %s: triangle %d not marked as a door' % (d[0], d[1]))
    g = m['grid']
    if g is None:
        out.append('no grid')
        return out
    s = g['side']
    if len(g['cells']) != s * s:
        out.append('grid: %d cells for side %d' % (len(g['cells']), s))
        return out
    if s != grid_side(nt):
        out.append('grid: side %d for %d triangles' % (s, nt))
    in_cell = [set() for _ in range(nt)]
    for ci, c in enumerate(g['cells']):
        for ti in c:
            if ti >= nt:
                out.append('grid cell %d names triangle %d' % (ci, ti))
            else:
                in_cell[ti].add(ci)
    for ti, t in enumerate(tris):
        if max(t[:3]) >= nv:
            continue
        cx = sum(m['verts'][i][0] for i in t[:3]) / 3
        cy = sum(m['verts'][i][1] for i in t[:3]) / 3
        c = max(0, min(int((cx - g['min'][0]) / g['cw']), s - 1)) if g['cw'] else 0
        r = max(0, min(int((cy - g['min'][1]) / g['ch']), s - 1)) if g['ch'] else 0
        if r * s + c not in in_cell[ti]:
            out.append('triangle %d is not in the grid cell its middle lies in' % ti)
    return out
