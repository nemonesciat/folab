"""entcut: Vault22Entrance's model with the collision in front of Vault 50's gear door collapsed (each such triangle's three
corners made one, in place: the MOPP tree and every other triangle stay as they are). cut(data, rule) -> (bytes, n)."""
import math, struct, sys
sys.path.insert(0, r'C:\Users\AMD RYZEN\Claude Code Projects\FOLab\app')
import nif, hkshape

DISC = (-166.0, 41.5)        # (the gear door's disc middle in the entrance's frame, x and z)
R = 150.0                    # (the disc's radius: the doorway's own ring beyond it stays)
FRONT = (-220.0, -85.0)      # (y: from the ring's front to just in front of the door's face)
PLUG = range(340, 352)
EXTRA = False                # (also the ring round the old disc: no, the door stands on the hole, not on the ruined door)       # (the slab that closed the doorway, y -139 to -99: a box of 12 triangles, all of it)


def cut(data):
    n = nif.Nif(data)
    blk = next(i for i, t in enumerate(n.types) if t == 'hkPackedNiTriStripsData')
    off = n.offsets[blk]
    nt = struct.unpack_from('<I', data, off)[0]
    raw = struct.unpack_from('<%dH' % (4 * nt), data, off + 4)
    nv = struct.unpack_from('<I', data, off + 4 + 8 * nt)[0]
    vs = struct.unpack_from('<%df' % (3 * nv), data, off + 4 + 8 * nt + 4 + 1)
    # (the shape as collision_shapes gives it, in the model's units: the same triangles in the same order)
    s = hkshape.collision_shapes(data)[0]
    v = s['v']
    out = bytearray(data)
    gone = []
    for k in range(nt):
        a, b, c = s['i'][3 * k:3 * k + 3]
        cx = (v[3 * a] + v[3 * b] + v[3 * c]) / 3.0
        cy = (v[3 * a + 1] + v[3 * b + 1] + v[3 * c + 1]) / 3.0
        cz = (v[3 * a + 2] + v[3 * b + 2] + v[3 * c + 2]) / 3.0
        if k in PLUG or (EXTRA and math.hypot(cx - DISC[0], cz - DISC[1]) < R and FRONT[0] < cy < FRONT[1]):
            c0 = raw[4 * k]
            struct.pack_into('<3H', out, off + 4 + 8 * k, c0, c0, c0)
            gone.append(k)
    return bytes(out), gone
