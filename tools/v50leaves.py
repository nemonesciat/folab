"""v50leaves: Vault22Entrance's drawn model made clear of Vault 50's gear door (the Workshop, 23 Nov 2026: "a bunch of
leaves clipped into it"). The door stands at AT in the entrance's frame, turned TURN; as it opens its disc (radius
DISC_R, middle at door x 3.2, z 31.5) is pulled 120 back (door y 34 down to -150) and rolled 270 along door x. Every
triangle of the entrance's foliage (`LEAVES`: its ivy, moss and evergreen sprigs) with a corner or its middle within
MARGIN of that swept space is taken out; the rest of the ivy stays. The entrance's own ruined drill (`DRILL`) is taken out
whole: the intact door brings its own drill to the same spot, so two were drawn in one another.

A strip shape's triangles are taken out by cutting its strips round them (a run that starts on an odd triangle gets its
first corner twice, so every kept triangle keeps its facing); its corners are untouched. cut(data) -> (bytes, counts)."""
import math
import struct
import sys

sys.path.insert(0, r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
import nif, outfitjoin  # noqa: E402

# (where the game's own ruined disc sits, VGearDoorR22 at (-20.79, 25.4, -4.18) turned -5 degrees from Vault22Entrance
# in the Mojave, its face on the socket's outer edge: the intact model turned half round and moved (-144.5, -83, 15.5)
# in the ruined door's frame lands its disc there, within 3 every way. The user, 23 Nov 2026: "the gear door is supposed
# to sit on the outer edge of the gear socket, not deep within")
# (in the gear hole, its face flush with the doorway's face, as the game stands every intact gear door in the Mojave:
# VGearDoorR3/R11/R19/R108 at (64, 192, 0) from their VURmGearExit01 room, no turn. There the hole's ring (VGearDoor02's
# shape) is x -86..221, y 43..230, z -121..181, 230 the wall's face, and the disc fills that x and z with its face at
# 226. Vault22Entrance's ring (vgeardoorr02's shape) is the same ring turned half round: x -221..85, y -232..-45, top
# 195. So the room's frame turned half round, moved (0, -2, 14), is the entrance's at the hole: the door at
# (-64, -194, 14) turned 180, the disc x -221..86, face at y -228, z -107..195. The user, 23 Nov 2026: "the gear face sits
# flush with the doorway face")
AT = (-64.0, -194.0, 14.0)
TURN = math.pi
DISC_R, DISC_X, DISC_Z = 151.0, 3.2, 31.5
ROLL_X = 273.1                       # (VGearDoor01b's key at 20.7 s: rolled aside)
REST_Y, PULL_Y, THICK = 34.0, -150.0, 64.0
MARGIN = 10.0
LEAVES = ('v22vines.dds', 'v22moss.dds', 'treeevergreendetail01.dds')
DRILL = ('vgeardrillr01.dds', 'vgeardrill01ra.dds', 'vmeshr01.dds')


def door_local(p):
    """The entrance's frame to the door's."""
    c, s = math.cos(TURN), math.sin(TURN)
    dx, dy = p[0] - AT[0], p[1] - AT[1]
    return (dx * c - dy * s, dx * s + dy * c, p[2] - AT[2])


def door_to_entrance(x, y, z):
    """The door's frame to the entrance's."""
    c, s = math.cos(TURN), math.sin(TURN)
    return (AT[0] + x * c + y * s, AT[1] - x * s + y * c, AT[2] + z)


def swept(p, m=MARGIN):
    x, y, z = door_local(p)
    if PULL_Y - m <= y <= REST_Y + m and math.hypot(x - DISC_X, z - DISC_Z) <= DISC_R + m:
        return True                  # (where it stands and where it's pulled back to)
    if PULL_Y - m <= y <= PULL_Y + THICK + m:
        cx = min(max(x, DISC_X), ROLL_X)
        return math.hypot(x - cx, z - DISC_Z) <= DISC_R + m
    return False


def _mul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _shapes(n):
    """(strips block, its data block, texture, corners in the model's frame) for every drawn strip shape."""
    out = []
    I3 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

    def visit(i, R, t, s):
        b = n.block(i)
        if not b:
            return
        if i == 0:
            lR, lt, ls = I3, [0, 0, 0], 1.0
        else:
            lR, lt, ls = b['R'], b['t'], b['s']
        nR = _mul(R, lR)
        nt = [t[a] + s * sum(R[a][k] * lt[k] for k in range(3)) for a in range(3)]
        ns = s * ls
        if 'children' in b:
            for c in b['children']:
                visit(c, nR, nt, ns)
            return
        if n.types[i] != 'NiTriStrips':
            return
        d = n.block(b['data'])
        v = d['verts']
        pts = [[nt[a] + ns * sum(nR[a][k] * v[c + k] for k in range(3)) for a in range(3)] for c in range(0, len(v), 3)]
        tex = nif._looks(n, b['props'])[0] or ''
        out.append((i, b['data'], tex.lower().split(chr(92))[-1], pts))

    visit(0, I3, [0, 0, 0], 1.0)
    return out


def _strips(d, o, size):
    """(where the triangle count is, the strips) of an NiTriStripsData block."""
    p = outfitjoin._extra_at(d, o) + 4
    at = p
    nt, ns = struct.unpack_from('<HH', d, p)
    p += 4
    lengths = struct.unpack_from('<%dH' % ns, d, p)
    p += 2 * ns
    if not d[p]:
        raise ValueError('a strip shape with no points')
    p += 1
    strips = []
    for ln in lengths:
        strips.append(list(struct.unpack_from('<%dH' % ln, d, p)))
        p += 2 * ln
    if p != o + size:
        raise ValueError('strips read %d of %d bytes' % (p - o, size))
    return at, strips


def _recut(strips, drop):
    """The strips with each triangle drop(a, b, c) refuses left out; returns (strips, triangles kept, taken out)."""
    out, kept, gone = [], 0, 0
    for st in strips:
        run = None
        for k in range(len(st) - 2):
            a, b, c = st[k], st[k + 1], st[k + 2]
            if a == b or b == c or a == c:
                if run is not None:
                    run.append(c)
                continue
            if drop(a, b, c):
                gone += 1
                if run is not None and len(run) >= 3:
                    out.append(run)
                run = None
                continue
            kept += 1
            if run is None:
                run = ([a] if k % 2 else []) + [a, b, c]
            else:
                run.append(c)
        if run is not None and len(run) >= 3:
            out.append(run)
    return out, kept, gone


def cut(data):
    n = nif.Nif(data)
    blocks = [data[o:o + s] for o, s in zip(n.offsets, n.sizes)]
    counts = {}
    for shape, db, tex, pts in _shapes(n):
        if tex in LEAVES:
            def drop(a, b, c, pts=pts):
                mid = [(pts[a][k] + pts[b][k] + pts[c][k]) / 3.0 for k in range(3)]
                return any(swept(q) for q in (pts[a], pts[b], pts[c], mid))
        elif tex in DRILL and max(q[0] for q in pts) - min(q[0] for q in pts) < 120:
            drop = lambda a, b, c: True      # (the drill's parts, not the wide mesh grate on the same picture)
        else:
            continue
        o, size = n.offsets[db], n.sizes[db]
        at, strips = _strips(data, o, size)
        new, kept, gone = _recut(strips, drop)
        if not gone:
            continue
        hide = not new
        if hide:                     # (nothing left: one strip of one corner, and the shape hidden, not left out of the
            new, kept = [[0, 0, 0]], 1      #  model: a block nothing holds crashed nv-rs, outfitjoin.compact)
            so = n.offsets[shape]
            fl = outfitjoin._net(data, so, [], [])
            sb = bytearray(blocks[shape])
            struct.pack_into('<I', sb, fl - so, struct.unpack_from('<I', data, fl)[0] | nif.APP_CULLED)
            blocks[shape] = bytes(sb)
        body = struct.pack('<HH', kept, len(new)) + struct.pack('<%dH' % len(new), *map(len, new)) + b'\x01'
        body += b''.join(struct.pack('<%dH' % len(s), *s) for s in new)
        blocks[db] = data[o:at] + body
        c = counts.setdefault(tex, [0, 0])
        c[0] += gone
        c[1] += kept
    return outfitjoin._write(n, list(n.types), blocks, list(n.strings)), counts


def check(data):
    """Triangles of the model's foliage and drill still within the swept space (as nif.py reads it)."""
    n = nif.Nif(data)
    left = 0
    for shape, db, tex, pts in _shapes(n):
        if tex not in LEAVES + DRILL or n.block(shape)['flags'] & nif.APP_CULLED:
            continue
        if tex in DRILL and max(q[0] for q in pts) - min(q[0] for q in pts) >= 120:
            continue
        tris = n.block(db)['tris']
        for k in range(0, len(tris), 3):
            a, b, c = tris[k:k + 3]
            mid = [(pts[a][j] + pts[b][j] + pts[c][j]) / 3.0 for j in range(3)]
            if tex in DRILL or any(swept(q, 0.0) for q in (pts[a], pts[b], pts[c], mid)):
                left += 1
    return left
