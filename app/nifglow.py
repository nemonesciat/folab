"""Lights up a sign in a New Vegas mesh already made: every shape showing one picture gets a glow picture in its texture
set's third slot and its material's emissive colour and multiplier (the game's way, and nifmake's: the glow picture says
where it lights, the multiplier how bright). Nothing else changes: other shapes, the collision and every other block keep
their bytes, and the header's sizes are put right for the blocks that grew (nifwrite's way).

For a model a mod already has, so that what was built into it stays as it was, glow added; a model built afresh gets its
glow from its looks (modelsets.neon)."""
import struct

import nif
import nifwrite


def light_up(data, tex, glow, mult=4.0, colour=(1.0, 1.0, 1.0)):
    """(the NIF with every shape showing `tex` lit by `glow`, how many shapes). tex compared as nifwrite.key does."""
    n = nif.Nif(data)
    for i in range(len(n.types)):
        n.block(i)
    want = nifwrite.key(tex)
    sets = set()
    edits = {}
    for i, k, t, how in nifwrite._spots(n):
        if t == 'BSShaderTextureSet' and k == 0 and nifwrite.key(nifwrite._read(n, how)) == want:
            sets.add(i)
    for i in sets:                                      # slot 2 (glow): its sized string replaced
        spots = [h for j, k, t, h in nifwrite._spots(n) if j == i]
        if len(spots) < 3:
            continue
        p = spots[2][1]
        old = struct.unpack_from('<I', data, p)[0]
        b = glow.encode('cp1252', 'replace')
        edits.setdefault(i, []).append((p, 4 + old, struct.pack('<I', len(b)) + b))
    lit = 0
    for i, t in enumerate(n.types):
        if t not in nif.GEOM_TYPES:
            continue
        props = n.blocks[i]['props'] if n.blocks[i] else []
        if not any(n.types[q] in ('BSShaderPPLightingProperty', 'Lighting30ShaderProperty') and (n.blocks[q] or {}).get('texset') in sets
                   for q in props if 0 <= q < len(n.types)):
            continue
        for q in props:
            if 0 <= q < len(n.types) and n.types[q] == 'NiMaterialProperty' and q not in edits:
                end = n.offsets[q] + n.sizes[q]
                # (the last nine numbers: specular, emissive, glossiness, alpha, emissive multiplier)
                spec_gloss = struct.unpack_from('<9f', data, end - 36)
                put = struct.pack('<9f', *(spec_gloss[:3] + tuple(colour) + spec_gloss[6:8] + (mult,)))
                edits[q] = [(end - 36, 36, put)]
        lit += 1
    if not edits:
        return bytes(data), 0
    return _apply(data, n, edits), lit


def _apply(data, n, edits):
    lay = nifwrite._layout(data)
    sizes_at, strings_end = lay[1], lay[3]
    sizes = list(n.sizes)
    pieces = []
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
    at = n.offsets[0] if n.offsets else strings_end
    last = n.offsets[-1] + n.sizes[-1]
    return bytes(head) + data[strings_end:at] + b''.join(pieces) + data[last:]
