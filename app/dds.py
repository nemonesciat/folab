"""A DDS texture's average colour, for drawing the ground on the flat map.

DDS: a 128-byte header (height at 12, width at 16, mipmap count at 28, the compression's four letters at 84), then
the picture at full size and each smaller copy after it. DXT1 keeps each 4 x 4 block of pixels as two colours (5-6-5
bits of red, green, blue) and a 2-bit choice per pixel among those two and two mixes of them; DXT3 and DXT5 put 8
bytes of transparency before the same colour block. The average is taken over a small copy (16 x 16), which the
texture keeps already shrunk."""
import struct


def _565(v):
    return ((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31


def _block(b, off):
    c0, c1, bits = struct.unpack_from('<HHI', b, off)
    a, z = _565(c0), _565(c1)
    if c0 > c1:
        pal = [a, z, tuple((2 * x + y) // 3 for x, y in zip(a, z)), tuple((x + 2 * y) // 3 for x, y in zip(a, z))]
    else:
        pal = [a, z, tuple((x + y) // 2 for x, y in zip(a, z)), (0, 0, 0)]
    return [pal[(bits >> (2 * i)) & 3] for i in range(16)]


def average_colour(data, want=16):
    """(r, g, b) 0-255, or None for a picture this can't read."""
    if len(data) < 128 or data[:4] != b'DDS ':
        return None
    h, w = struct.unpack_from('<II', data, 12)
    mips = max(1, struct.unpack_from('<I', data, 28)[0])
    four = data[84:88]
    step = {b'DXT1': 8, b'DXT3': 16, b'DXT5': 16}.get(four)
    if not step:
        return None
    off = 128
    for _ in range(mips - 1):
        if w <= want and h <= want:
            break
        off += max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * step
        w, h = max(1, w // 2), max(1, h // 2)
    n = max(1, (w + 3) // 4) * max(1, (h + 3) // 4)
    tot, k = [0, 0, 0], 0
    for i in range(n):
        o = off + i * step + (step - 8)
        if o + 8 > len(data):
            break
        for px in _block(data, o):
            tot[0] += px[0]; tot[1] += px[1]; tot[2] += px[2]
            k += 1
    return tuple(v // k for v in tot) if k else None
