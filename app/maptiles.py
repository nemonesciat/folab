"""The flat map's pictures of the ground: one PNG per 16 x 16 cells, 16 pixels a cell (every other point of the
land), north up.

Each pixel is the ground as the game paints it there: the quarter's base texture's average colour, each painted layer
over it as strongly as it shows, times the ground's own colour (VCLR), shaded by the slope (light from the north-west,
as maps have it), and blue under water. Squares with no cell are left clear."""
import struct
import zlib

import dds
import land
import tes4

TILE = 16                  # cells a tile is across
PX = 16                    # pixels a cell is across
LIGHT = (-0.5, 0.5, 0.707)


def png(width, height, rows):
    """An RGBA PNG from rows of bytes (each width * 4 long)."""
    raw = b''.join(b'\0' + bytes(r) for r in rows)

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


class Painter:
    def __init__(self, gd):
        self.gd = gd
        self.tex = {}          # LTEX -> picture path (land.py's cache)
        self.colour = {}       # picture path -> (r, g, b)

    def colour_of(self, path):
        if path not in self.colour:
            c = None
            try:
                c = dds.average_colour(self.gd.read_file(path))
            except (FileNotFoundError, KeyError, struct.error):
                pass
            self.colour[path] = c or (128, 116, 96)
        return self.colour[path]

    def water(self, world, cell, mine=None):
        """The water's height in a cell, or None where it has none. mine: {CELL key: height or None} as a mod sets
        it (None: the world's own level)."""
        k = self.gd.key(cell)
        if mine is not None and k in mine:
            return self.world_water(world) if mine[k] is None else mine[k]
        f = self.gd.fields(cell)
        flags = f.get('DATA', b'\0')[0]
        if not flags & 2:
            return None
        if 'XCLW' in f and len(f['XCLW']) >= 4:
            v = struct.unpack_from('<f', f['XCLW'])[0]
            if abs(v) < 1e7:
                return v
        return self.world_water(world)

    def world_water(self, world):
        wd = self.gd.fields(world).get('DNAM')
        return struct.unpack_from('<f', wd, 4)[0] if wd and len(wd) >= 8 else None

    def tile(self, world, tx, ty, mine=None, water=None):
        """PNG bytes for tile (tx, ty): cells tx*16 .. +15 across, ty*16 .. +15 up. mine: {CELL key: land} as the
        mod has it, over the game's."""
        gd, size = self.gd, TILE * PX
        img = bytearray(size * size * 4)
        grid = gd.grid(world)
        for j in range(TILE):
            for i in range(TILE):
                cx, cy = tx * TILE + i, ty * TILE + j
                cell = grid.get((cx, cy))
                L = (mine or {}).get(gd.key(cell)) if cell is not None else None
                if L is None:
                    e = gd.land_at(world, cx, cy)
                    if not e:
                        continue
                    L = land.decode(gd, e, self.tex)
                if not L.get('h'):
                    continue
                wl = self.water(world, cell, water) if cell is not None else None
                self._cell(img, size, i, TILE - 1 - j, L, wl)
        return png(size, size, [img[r * size * 4:(r + 1) * size * 4] for r in range(size)])

    def _cell(self, img, size, i, jrow, L, water):
        h = L['h']
        vclr = bytes.fromhex(L['c']) if L.get('c') else None
        quarters = []
        for q in L['q']:
            quarters.append((self.colour_of(q['base']) if q.get('base') else (128, 116, 96),
                             [(self.colour_of(l['tex']), l['a']) for l in q['layers'] if l.get('tex')]))
        lx, ly, lz = LIGHT
        for pr in range(PX):
            gr = pr * 2
            for pc in range(PX):
                gc = pc * 2
                qx, qy = (1 if gc >= 16 else 0), (1 if gr >= 16 else 0)
                base, layers = quarters[qx + 2 * qy]
                k = (gr - 16 * qy) * 17 + (gc - 16 * qx)
                r, g, b = base
                for col, a in layers:
                    w = a[k]
                    if w:
                        r += (col[0] - r) * w; g += (col[1] - g) * w; b += (col[2] - b) * w
                n = gr * 33 + gc
                if vclr:
                    r, g, b = r * vclr[n * 3] / 255, g * vclr[n * 3 + 1] / 255, b * vclr[n * 3 + 2] / 255
                # the slope, from the points either side
                dx = (h[gr * 33 + min(32, gc + 1)] - h[gr * 33 + max(0, gc - 1)]) / 256
                dy = (h[min(32, gr + 1) * 33 + gc] - h[max(0, gr - 1) * 33 + gc]) / 256
                nl = (dx * dx + dy * dy + 1) ** 0.5
                shade = 0.55 + 0.75 * max(0.0, (-dx * lx - dy * ly + lz) / nl)
                r, g, b = r * shade, g * shade, b * shade
                if water is not None and h[n] < water:
                    deep = min(1.0, (water - h[n]) / 1500)
                    r, g, b = r * 0.35 * (1 - deep) + 40 * (0.6 + deep), g * 0.35 * (1 - deep) + 80 * (0.6 + deep), b * 0.4 * (1 - deep) + 130 * (0.6 + deep)
                o = ((jrow * PX + (PX - 1 - pr)) * size + i * PX + pc) * 4
                img[o:o + 4] = bytes((min(255, max(0, int(r))), min(255, max(0, int(g))), min(255, max(0, int(b))), 255))
