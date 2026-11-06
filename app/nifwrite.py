"""Changes the texture paths in a New Vegas mesh (NIF 20.2.0.7) and nothing else.

A NIF's header gives every block's size, so a block can grow or shrink without touching any other: the blocks holding
a path are rewritten, their sizes in the header put right, and every other byte stays as it was. With nothing to
change, the bytes that come out are the bytes that went in.

Where a path can be: a BSShaderTextureSet (a list of slots), the single file of a shader property, and an
NiSourceTexture (which names its file by the header's string table, so a changed one gets a new string there, kept apart
from any other block that happened to share the old one).

    py -3 app/nifwrite.py [n]     every game mesh (or every n-th): changes every path, reads it back with nif.py"""
import struct

import nif

SLOTS = ['Picture', 'Normal map', 'Glow', 'Height', 'Reflection', 'Reflection mask']
# after the object's own fields and the shader's, a clamp mode (the lighting ones) comes before the file name
_SHADER_FILE = {'BSShaderNoLightingProperty': True, 'TileShaderProperty': True, 'SkyShaderProperty': True,
                'TallGrassShaderProperty': False}


def _layout(data):
    """(position of the block sizes, position of the string table's count, position of the end of the string table,
    block count) of a NIF, from reading its header as nif.py does."""
    n = nif.Nif(data)
    r = nif.Reader(data, data.find(b'\n') + 1)
    r.u32(); r.u8(); r.u32()
    count = r.u32()
    r.u32()
    r.short(); r.short(); r.short()
    for _ in range(r.u16()):
        r.sized()
    r.p += 2 * count
    sizes_at = r.p
    r.p += 4 * count
    strings_at = r.p
    nstr = r.u32()
    r.u32()
    for _ in range(nstr):
        k = r.u32()
        r.p += k
    return n, sizes_at, strings_at, r.p


def _net_end(d, p):
    """Past an NiObjectNET's name, extra data and controller."""
    p += 4
    p += 4 + 4 * struct.unpack_from('<I', d, p)[0]
    return p + 4


def _spots(n):
    """Where every texture path is: (block, slot, type, how). how: ('sized', position in the file) or ('string', position
    of the index into the string table)."""
    d, out = n.data, []
    for i, t in enumerate(n.types):
        o = n.offsets[i]
        if t == 'BSShaderTextureSet':
            count = struct.unpack_from('<i', d, o)[0]
            p = o + 4
            for k in range(count):
                out.append((i, k, t, ('sized', p)))
                p += 4 + struct.unpack_from('<I', d, p)[0]
        elif t in _SHADER_FILE:
            p = _net_end(d, o) + 2 + 4 + 4 + 4 + 4       # flags, shader type, shader flags, flags 2, environment scale
            if _SHADER_FILE[t]:
                p += 4                                   # clamp mode
            out.append((i, 0, t, ('sized', p)))
        elif t == 'NiSourceTexture':
            p = _net_end(d, o)
            if d[p] == 1:                                # (external: the rest of the file is the mesh's, not a path)
                out.append((i, 0, t, ('string', p + 1)))
    return out


def _read(n, how):
    d = n.data
    if how[0] == 'sized':
        k = struct.unpack_from('<I', d, how[1])[0]
        return d[how[1] + 4:how[1] + 4 + k].decode('cp1252', 'replace')
    return n.string(struct.unpack_from('<i', d, how[1])[0])


def key(path):
    """A path as paths are compared: its case and slashes don't matter."""
    return path.replace('/', '\\').lower().strip()


def textures_in(data):
    """[{'block', 'slot', 'kind', 'path', 'label'}] of every non-empty texture path, in file order."""
    n = nif.Nif(data)
    out = []
    for i, k, t, how in _spots(n):
        p = _read(n, how)
        if p.strip():
            out.append({'block': i, 'slot': k, 'kind': t, 'path': p, 'label': SLOTS[k] if t == 'BSShaderTextureSet' and k < len(SLOTS) else 'Picture'})
    return out


def retexture(data, changes):
    """The NIF with its paths changed. changes: {old path: new path} (case and slashes of the old one don't matter).
    Only the blocks holding a changed path differ, and the header's sizes and strings with them."""
    wanted = {key(a): b for a, b in changes.items()}
    n, sizes_at, strings_at, strings_end = _layout(data)
    edits = {}                   # block -> [(position in file, length of what's there, bytes to put there)]
    new_strings = {}             # new path -> its index in the string table
    nstr = struct.unpack_from('<I', data, strings_at)[0]
    longest = struct.unpack_from('<I', data, strings_at + 4)[0]
    for i, _k, _t, how in _spots(n):
        p = _read(n, how)
        new = wanted.get(key(p))
        if new is None or new == p:
            continue
        b = new.encode('cp1252', 'replace')
        if how[0] == 'sized':
            old = struct.unpack_from('<I', data, how[1])[0]
            edits.setdefault(i, []).append((how[1], 4 + old, struct.pack('<I', len(b)) + b))
        else:
            if new not in new_strings:
                new_strings[new] = nstr + len(new_strings)
            edits.setdefault(i, []).append((how[1], 4, struct.pack('<i', new_strings[new])))
    if not edits:
        return bytes(data)
    sizes = list(n.sizes)
    pieces, at = [], n.offsets[0] if n.offsets else strings_end
    for i in range(len(n.types)):
        o, s = n.offsets[i], n.sizes[i]
        if i not in edits:
            pieces.append(data[o:o + s])
            continue
        block, p = [], o
        for pos, ln, put in sorted(edits[i]):
            block += [data[p:pos], put]
            p = pos + ln
        block.append(data[p:o + s])
        pieces.append(b''.join(block))
        sizes[i] = len(pieces[-1])
    head = bytearray(data[:strings_end])
    struct.pack_into('<%dI' % len(sizes), head, sizes_at, *sizes)
    extra = b''
    if new_strings:
        for s in new_strings:
            b = s.encode('cp1252', 'replace')
            extra += struct.pack('<I', len(b)) + b
            longest = max(longest, len(b))
        struct.pack_into('<II', head, strings_at, nstr + len(new_strings), longest)
    between = data[strings_end:at]                # (the groups list, between the strings and the first block)
    last = n.offsets[-1] + n.sizes[-1]
    return bytes(head) + extra + between + b''.join(pieces) + data[last:]


def prove(data, changes=None):
    """Reads a changed mesh back. Returns what's wrong (an empty list: the only difference is the texture paths)."""
    wrong = []
    if retexture(data, {}) != bytes(data):
        wrong.append('with nothing to change, the bytes changed')
    before = textures_in(data)
    changes = changes if changes is not None else {t['path']: 'textures\\folabtest\\%d.dds' % k for k, t in enumerate(before)}
    new = retexture(data, changes)
    a, b = nif.Nif(data), nif.Nif(new)
    if a.types != b.types:
        wrong.append('block types differ')
    wanted = {key(o): v for o, v in changes.items()}
    got = textures_in(new)
    want = [wanted.get(key(t['path']), t['path']) for t in before]
    if [t['path'] for t in got] != want:
        wrong.append('texture paths read back wrong')
    touched = {t['block'] for t in before if key(t['path']) in wanted}
    for i in range(len(a.types)):
        x, y = data[a.offsets[i]:a.offsets[i] + a.sizes[i]], new[b.offsets[i]:b.offsets[i] + b.sizes[i]]
        if i not in touched and x != y:
            wrong.append('block %d (%s) changed' % (i, a.types[i]))
    tail_a, tail_b = data[a.offsets[-1] + a.sizes[-1]:], new[b.offsets[-1] + b.sizes[-1]:] if a.offsets else (b'', b'')
    if tail_a != tail_b:
        wrong.append('the end of the file changed')
    # what the view draws is the same but for the texture name
    try:
        ma = nif.mesh_from_nif(data)
    except Exception:
        ma = None                       # (a mesh nif.py can't draw: the checks above still hold)
    if ma is not None:
        mb = nif.mesh_from_nif(new)
        # (as text: a few of the game's meshes hold not-a-number corners, which never equal themselves as numbers)
        same = lambda s: repr({k: v for k, v in s.items() if k != 'tex'})
        if [same(s) for s in ma] != [same(s) for s in mb]:
            wrong.append('the shapes changed')
        tex = {key(k): v for k, v in wanted.items()}
        if [tex.get(key(s['tex']), s['tex']).replace('/', '\\') for s in ma] != [s['tex'] for s in mb]:
            wrong.append('the shapes draw the wrong texture')
    return wrong


if __name__ == '__main__':
    import collections
    import sys
    import time
    import gamedata
    gd = gamedata.GameData()
    step = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    t0 = time.time()
    paths = gd.mesh_list()[::step]
    bad, kinds, n_paths, unread = {}, collections.Counter(), 0, []
    for k, m in enumerate(paths):
        rel = 'meshes\\' + m
        try:
            data = gd.read_file(rel)
            nif.Nif(data)
        except Exception as e:
            unread.append((m, str(e)))
            continue
        got = textures_in(data)
        n_paths += len(got)
        kinds.update(t['kind'] for t in got)
        w = prove(data)
        if w:
            bad[m] = w
        if k % 2000 == 0:
            print(k, 'of', len(paths), 'meshes', '%.0fs' % (time.time() - t0), flush=True)
    print('%d meshes, %d texture paths %s, %.0fs' % (len(paths), n_paths, dict(kinds), time.time() - t0))
    print('not readable by nif.py at all (left alone): %d' % len(unread), unread[:5])
    print('differences beyond the texture paths: %d' % len(bad))
    for m, w in list(bad.items())[:30]:
        print(' ', m, w)
