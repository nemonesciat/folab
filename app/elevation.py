"""Height files from the real world, read with the standard library only: GeoTIFF, SRTM .hgt and plain 16-bit PNG (a .zip,
.gz holding one counts). The person brings the file; FOLab fetches nothing.

A Raster is the heights as written, a float32 array row by row from the north (NaN where the file has no data), and
where each pixel is on Earth if the file says. Coordinates in here always mean pixel *centres*: value number (row, col) stands at
exactly (col, row). A GeoTIFF's corner origin is moved half a pixel in when its pixels are areas, not points.

GeoTIFF: uncompressed, LZW or Deflate; 8/16/32-bit integers, 32/64-bit floats; strips or tiles; both byte orders; BigTIFF;
predictors 2 and 3. Geo tags: ModelPixelScale + ModelTiepoint or ModelTransformation (no rotation), GeoKeys for whether it's in
degrees or a projection and in which units, GDAL_NODATA. The first band is the height."""
import array
import gzip
import io
import itertools
import math
import os
import re
import struct
import sys
import zipfile
import zlib

import heightmap

NAN = float('nan')
FOOT = 0.3048
US_FOOT = 1200.0 / 3937.0
WILD = 1e5                    # (nothing on Earth is this far from sea level in metres or feet: it's a no-data value)
MAX_PIXELS = 400_000_000      # (1.6 GB in memory: past this, ask for a smaller file)


class MapFileError(ValueError):
    """Why this file can't be read, in words for the person who brought it."""


class Raster:
    """w x h heights. geo: None or {'kind': 'deg'|'proj', 'x0', 'y0' (pixel (0, 0)'s centre), 'dx', 'dy' (one pixel east, one pixel
    south, both positive), 'epsg', 'unit' (metres in a projection unit)}. plain: a picture with no heights of its own, values 0-1."""

    def __init__(self, w, h, v, geo=None, name='', plain=False, notes=None, kind=''):
        self.w, self.h, self.v, self.geo, self.name, self.plain = w, h, v, geo, name, plain
        self.notes = notes or []
        self.kind = kind
        self.folab = None                  # (a FOLab height map's own text: game units, one pixel a land point)
        self._stats = None

    def at(self, col, row):
        return self.v[row * self.w + col]

    def stats(self):
        """(lowest, highest, how many have no data)."""
        if self._stats is None:
            good = [x for x in self.v if x == x]
            self._stats = (min(good), max(good), len(self.v) - len(good)) if good else (0.0, 0.0, len(self.v))
        return self._stats

    def metres_per_pixel(self, fallback=30.0):
        """(east-west, north-south) size of a pixel in metres, at the middle of the file."""
        g = self.geo
        if not g:
            return fallback, fallback
        if g['kind'] == 'proj':
            return g['dx'] * g['unit'], g['dy'] * g['unit']
        lat = math.radians(g['y0'] - g['dy'] * (self.h - 1) / 2)
        by_lat = 111132.92 - 559.82 * math.cos(2 * lat) + 1.175 * math.cos(4 * lat)
        by_lon = 111412.84 * math.cos(lat) - 93.5 * math.cos(3 * lat) + 0.118 * math.cos(5 * lat)
        return g['dx'] * by_lon, g['dy'] * by_lat

    def to_pixel(self, lat, lon):
        """(col, row) of a spot on Earth, or None when the file doesn't say where it is or its projection isn't one FOLab knows."""
        return pixel_of(self.geo, lat, lon) if self.geo else None


def pixel_of(g, lat, lon):
    """(col, row) of a spot on Earth in a file with this place; None when its projection isn't one FOLab knows."""
    if g['kind'] == 'deg':
        x, y = lon, lat
    else:
        xy = project(g.get('epsg'), lat, lon, g['unit'])
        if xy is None:
            return None
        x, y = xy
    return (x - g['x0']) / g['dx'], (g['y0'] - y) / g['dy']


# ---------- projections (only what height files commonly come in) ----------

def project(epsg, lat, lon, unit=1.0):
    """(x, y) in this projection, in its units; None for one FOLab doesn't know."""
    if not epsg:
        return None
    if epsg in (3857, 3785, 900913):
        r = 6378137.0
        return r * math.radians(lon) / unit, r * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) / unit
    zone, south = None, False
    if 32601 <= epsg <= 32660:
        zone = epsg - 32600
    elif 32701 <= epsg <= 32760:
        zone, south = epsg - 32700, True
    elif 26901 <= epsg <= 26923:           # (NAD83 / UTM north: GRS80, close enough to WGS84 here)
        zone = epsg - 26900
    elif 25828 <= epsg <= 25838:           # (ETRS89 / UTM)
        zone = epsg - 25800
    elif 6330 <= epsg <= 6348:             # (NAD83(2011) / UTM)
        zone = epsg - 6329
    if zone is None:
        return None
    x, y = _utm(lat, lon, zone, south)
    return x / unit, y / unit


def _utm(lat, lon, zone, south):
    a, f, k0 = 6378137.0, 1 / 298.257223563, 0.9996
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    phi, lam = math.radians(lat), math.radians(lon)
    lam0 = math.radians(zone * 6 - 183)
    n = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    t = math.tan(phi) ** 2
    c = ep2 * math.cos(phi) ** 2
    A = (lam - lam0) * math.cos(phi)
    m = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * phi
             - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * phi)
             + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * phi)
             - (35 * e2 ** 3 / 3072) * math.sin(6 * phi))
    x = k0 * n * (A + (1 - t + c) * A ** 3 / 6 + (5 - 18 * t + t * t + 72 * c - 58 * ep2) * A ** 5 / 120) + 500000.0
    y = k0 * (m + n * math.tan(phi) * (A * A / 2 + (5 - t + 9 * c + 4 * c * c) * A ** 4 / 24
                                       + (61 - 58 * t + t * t + 600 * c - 330 * ep2) * A ** 6 / 720))
    return x, y + (10000000.0 if south else 0.0)


# ---------- opening a file ----------

def read_file(path, progress=None):
    """A Raster from a file on disk, whichever kind it is."""
    name = os.path.basename(path)
    low = name.lower()
    if low.endswith('.zip'):
        with zipfile.ZipFile(path) as z:
            inner = [n for n in z.namelist() if n.lower().endswith(('.hgt', '.tif', '.tiff', '.png'))]
            if not inner:
                raise MapFileError('Nothing in %s is a height file (.tif, .hgt or .png).' % name)
            inner.sort(key=lambda n: -z.getinfo(n).file_size)
            data = z.read(inner[0])
        return read_bytes(os.path.basename(inner[0]), data, progress)
    if low.endswith('.gz'):
        with gzip.open(path, 'rb') as f:
            return read_bytes(name[:-3], f.read(), progress)
    if low.endswith(('.tif', '.tiff')):
        with open(path, 'rb') as f:
            return read_tiff(f, name, progress)
    with open(path, 'rb') as f:
        return read_bytes(name, f.read(), progress)


def read_bytes(name, data, progress=None):
    low = name.lower()
    if low.endswith(('.tif', '.tiff')) or data[:4] in (b'II*\0', b'MM\0*', b'II+\0', b'MM\0+'):
        return read_tiff(io.BytesIO(data), name, progress)
    if low.endswith('.hgt'):
        return read_hgt(data, name)
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return read_png(data, name)
    raise MapFileError('%s isn\'t a kind of file FOLab reads: GeoTIFF (.tif), SRTM (.hgt) or a 16-bit PNG.' % name)


# ---------- SRTM ----------

def read_hgt(data, name=''):
    """SRTM: a square of big-endian 16-bit heights in metres, north row first, -32768 for none. The name says where its
    south-west corner is (N36W116); the edges are shared with the squares next door, so it's 1201 or 3601 points a side."""
    n = int(round((len(data) / 2) ** 0.5))
    if n < 2 or n * n * 2 != len(data):
        raise MapFileError('%s isn\'t the size of an SRTM square: %d bytes.' % (name, len(data)))
    a = array.array('h')
    a.frombytes(data)
    if sys.byteorder == 'little':
        a.byteswap()
    v = array.array('f', a)
    if a.count(-32768):
        for i, x in enumerate(a):
            if x == -32768:
                v[i] = NAN
    m = re.search(r'([NS])(\d{2})([EW])(\d{3})', name.upper())
    geo, notes = None, []
    if m:
        lat, lon = int(m[2]) * (1 if m[1] == 'N' else -1), int(m[4]) * (1 if m[3] == 'E' else -1)
        d = 1.0 / (n - 1)
        geo = {'kind': 'deg', 'x0': float(lon), 'y0': lat + 1.0, 'dx': d, 'dy': d, 'epsg': 4326, 'unit': 1.0}
    else:
        notes.append('The file\'s name doesn\'t say where on Earth it is (like N36W116.hgt): give the size of a pixel by hand.')
    return Raster(n, n, v, geo, name, notes=notes, kind='SRTM')


# ---------- PNG ----------

def read_png(data, name=''):
    """A greyscale picture: no heights or place of its own, so the person says them. One of FOLab's own height maps knows
    its heights and that a pixel is a land point."""
    try:
        w, h, vals, text = heightmap.read_png(data)
    except ValueError as e:
        raise MapFileError(str(e))
    head_depth = data[24]
    r = Raster(w, h, array.array('f', vals), None, name, plain=True, kind='PNG')
    if head_depth < 16:
        r.notes.append('This picture has only 256 levels of grey, so the land will come out in terraces. A 16-bit picture is far better.')
    if text and 'low' in text and 'high' in text:
        r.folab = {'low': float(text['low']), 'high': float(text['high'])}
    return r


# ---------- GeoTIFF ----------

TAG_NAMES = {256: 'w', 257: 'h', 258: 'bits', 259: 'comp', 273: 'strips', 277: 'spp', 278: 'rows', 279: 'stripn', 284: 'planar',
             317: 'pred', 322: 'tw', 323: 'th', 324: 'tiles', 325: 'tilen', 339: 'fmt', 254: 'sub', 33550: 'scale', 33922: 'tie',
             34264: 'matrix', 34735: 'geokeys', 34736: 'geodouble', 42113: 'nodata'}
FIELD = {1: ('B', 1), 2: ('s', 1), 3: ('H', 2), 4: ('I', 4), 5: ('II', 8), 6: ('b', 1), 7: ('B', 1), 8: ('h', 2), 9: ('i', 4),
         10: ('ii', 8), 11: ('f', 4), 12: ('d', 8), 13: ('I', 4), 16: ('Q', 8), 17: ('q', 8), 18: ('Q', 8)}


def _read_ifd(f, order, big, pos):
    """{tag name: value (a tuple, or a string)} and where the next directory is."""
    f.seek(pos)
    count = struct.unpack(order + ('Q' if big else 'H'), f.read(8 if big else 2))[0]
    tags = {}
    size = 20 if big else 12
    block = f.read(count * size + (8 if big else 4))
    for i in range(count):
        e = block[i * size:(i + 1) * size]
        if big:
            tag, typ, n = struct.unpack(order + 'HHQ', e[:12])
            inline, off_fmt = e[12:20], 'Q'
        else:
            tag, typ, n = struct.unpack(order + 'HHI', e[:8])
            inline, off_fmt = e[8:12], 'I'
        if tag not in TAG_NAMES or typ not in FIELD:
            continue
        fmt, width = FIELD[typ]
        total = width * n
        if total <= len(inline):
            raw = inline[:total]
        else:
            at = f.tell()
            f.seek(struct.unpack(order + off_fmt, inline)[0])
            raw = f.read(total)
            f.seek(at)
        if typ == 2:
            tags[TAG_NAMES[tag]] = raw.split(b'\0')[0].decode('ascii', 'replace')
        elif typ in (5, 10):
            vals = struct.unpack(order + fmt[0] * (2 * n), raw)
            tags[TAG_NAMES[tag]] = tuple(vals[k] / (vals[k + 1] or 1) for k in range(0, 2 * n, 2))
        else:
            tags[TAG_NAMES[tag]] = struct.unpack(order + fmt * n, raw)
    next_at = struct.unpack(order + ('Q' if big else 'I'), block[count * size:])[0]
    return tags, next_at


def read_tiff(f, name='', progress=None):
    head = f.read(8)
    if head[:2] not in (b'II', b'MM'):
        raise MapFileError('%s isn\'t a TIFF file.' % name)
    order = '<' if head[:2] == b'II' else '>'
    magic = struct.unpack(order + 'H', head[2:4])[0]
    if magic == 42:
        big, pos = False, struct.unpack(order + 'I', head[4:8])[0]
    elif magic == 43:
        big = True
        pos = struct.unpack(order + 'Q', f.read(8))[0]
    else:
        raise MapFileError('%s isn\'t a TIFF file.' % name)
    tags, _next = _read_ifd(f, order, big, pos)
    one = lambda k, d=None: tags[k][0] if k in tags else d
    w, h = one('w'), one('h')
    if not w or not h:
        raise MapFileError('%s has no picture size.' % name)
    if w * h > MAX_PIXELS:
        raise MapFileError('%s has %d x %d points, more than FOLab can hold. Cut out the part you want first (QGIS: Raster > Extraction > Clip).' % (name, w, h))
    bits = one('bits', 8)
    spp = one('spp', 1)
    fmt = one('fmt', 1)
    comp = one('comp', 1)
    pred = one('pred', 1)
    if comp not in (1, 5, 8, 32946):
        raise MapFileError('%s is compressed in a way FOLab doesn\'t read (TIFF compression %d). Save it uncompressed, LZW or Deflate.' % (name, comp))
    code = {(1, 8): 'B', (2, 8): 'b', (1, 16): 'H', (2, 16): 'h', (1, 32): 'I', (2, 32): 'i', (3, 32): 'f', (3, 64): 'd'}.get((fmt, bits))
    if code is None:
        raise MapFileError('%s holds %d-bit %s numbers, which FOLab doesn\'t read. Save it as 16-bit integers or 32-bit floats.'
                           % (name, bits, {1: 'whole', 2: 'whole', 3: 'floating'}.get(fmt, 'other')))
    if pred not in (1, 2, 3):
        raise MapFileError('%s uses TIFF predictor %d, which FOLab doesn\'t read.' % (name, pred))
    if array.array(code).itemsize != bits // 8:
        code = {'I': 'L', 'i': 'l'}.get(code, code)
    planar = one('planar', 1)
    band_in_chunk = 1 if planar == 2 else spp
    tiled = 'tiles' in tags
    if tiled:
        tw, th = one('tw'), one('th')
        offs, sizes = tags['tiles'], tags.get('tilen')
        across = (w + tw - 1) // tw
        down = (h + th - 1) // th
    else:
        tw, th = w, one('rows', h)
        if th > h:
            th = h
        offs, sizes = tags.get('strips'), tags.get('stripn')
        across, down = 1, (h + th - 1) // th
    if not offs or not sizes:
        raise MapFileError('%s has no picture data.' % name)
    nodata = None
    if 'nodata' in tags:
        try:
            nodata = float(str(tags['nodata']).strip())
        except ValueError:
            nodata = None
    if nodata is not None and nodata == nodata and abs(nodata) < 1e38:
        nodata = struct.unpack('f', struct.pack('f', nodata))[0]      # (as the float32s it's compared with have it)
    v = array.array('f', bytes(4 * w * h))
    total = across * down
    swap = (order == '<') != (sys.byteorder == 'little')
    width = bits // 8
    for k in range(total):
        tx, ty = k % across, k // across
        cx, cy = tx * tw, ty * th
        ch = min(th, h - cy)
        rows_here = th if tiled else ch
        got = None
        if k < len(offs) and offs[k] and sizes[k]:
            f.seek(offs[k])
            raw = _inflate(f.read(sizes[k]), comp, name)
            got = _values(raw, tw, rows_here, band_in_chunk, width, code, swap, pred, order)
        cw = min(tw, w - cx)
        if got is None:
            for r in range(ch):
                a = (cy + r) * w + cx
                v[a:a + cw] = array.array('f', [NAN]) * cw
        else:
            for r in range(ch):
                a = (cy + r) * w + cx
                b = r * tw
                if b + cw > len(got):                       # (a short last chunk)
                    have = max(0, len(got) - b)
                    v[a:a + have] = got[b:b + have]
                    v[a + have:a + cw] = array.array('f', [NAN]) * (cw - have)
                else:
                    v[a:a + cw] = got[b:b + cw]
        if progress and k % 16 == 0:
            progress(k, total)
    _blank_nodata(v, nodata, code)
    notes = []
    if spp > 1:
        notes.append('This file has %d bands of numbers: FOLab took the first as the height.' % spp)
    geo, zscale = _geo(tags, w, h, notes, name)
    if zscale != 1.0:
        for i, x in enumerate(v):
            v[i] = x * zscale
    return Raster(w, h, v, geo, name, notes=notes, kind='GeoTIFF')


def _inflate(raw, comp, name):
    try:
        if comp == 1:
            return raw
        if comp == 5:
            return lzw_decode(raw)
        return zlib.decompress(raw)
    except (zlib.error, IndexError) as e:
        raise MapFileError('Part of %s is damaged and can\'t be unpacked (%s).' % (name, e))


def lzw_decode(data):
    """TIFF's LZW: codes high bit first, 9 to 12 bits, 256 clear, 257 end, the code size growing one code early."""
    out = []
    table = [bytes((i,)) for i in range(256)] + [b'', b'']
    width, acc, nacc = 9, 0, 0
    prev = None
    for byte in data:
        acc = (acc << 8) | byte
        nacc += 8
        while nacc >= width:
            nacc -= width
            code = (acc >> nacc) & ((1 << width) - 1)
            acc &= (1 << nacc) - 1
            if code == 256:
                del table[258:]
                width = 9
                prev = None
                continue
            if code == 257:
                return b''.join(out)
            if prev is None:
                entry = table[code]
                out.append(entry)
                prev = entry
                continue
            if code < len(table):
                entry = table[code]
                table.append(prev + entry[:1])
            else:
                entry = prev + prev[:1]
                table.append(entry)
            out.append(entry)
            prev = entry
            n = len(table) + 1
            if n >= 2048:
                width = 12
            elif n >= 1024:
                width = 11
            elif n >= 512:
                width = 10
    return b''.join(out)


def _values(raw, tw, th, spp, width, code, swap, pred, order):
    """A chunk's first band as float32s, tw to a row."""
    if pred == 3:
        raw = _unpredict_float(raw, tw, spp, width)
        swap = sys.byteorder == 'little'       # (the float predictor always leaves the bytes highest first)
    a = array.array(code)
    usable = len(raw) - len(raw) % width
    a.frombytes(raw[:usable])
    if swap:
        a.byteswap()
    if pred == 2:
        a = _unpredict_int(a, tw, spp, width, code)
    if spp > 1:
        a = a[::spp]
    return a if code == 'f' else array.array('f', a)


def _unpredict_int(a, tw, spp, width, code):
    """Horizontal differencing undone: each sample was stored as the difference from the one spp before it in its row."""
    mask = (1 << (width * 8)) - 1
    half = 1 << (width * 8 - 1)
    signed = code in 'bhil'
    add = lambda p, q: (p + q) & mask
    out = array.array(code, a)
    per = tw * spp
    for r in range(len(a) // per):
        for s in range(spp):
            run = itertools.accumulate((x & mask for x in a[r * per + s:(r + 1) * per:spp]), add)
            if signed:
                out[r * per + s:(r + 1) * per:spp] = array.array(code, ((x - (mask + 1) if x >= half else x) for x in run))
            else:
                out[r * per + s:(r + 1) * per:spp] = array.array(code, run)
    return out


def _unpredict_float(raw, tw, spp, width):
    """The floating-point predictor (TIFF Tech Note 3) undone: each row's bytes differenced with a stride of spp, over the
    number's bytes laid out highest byte plane first. Gives big-endian numbers."""
    per = tw * spp
    n = per * width
    out = bytearray(len(raw))
    for r in range(len(raw) // n):
        row = bytearray(raw[r * n:(r + 1) * n])
        for s in range(spp):
            row[s::spp] = bytes(itertools.accumulate(row[s::spp], lambda p, q: (p + q) & 255))
        for b in range(width):
            out[r * n + b:(r + 1) * n:width] = row[b * per:(b + 1) * per]
    return bytes(out)


def _blank_nodata(v, nodata, code):
    """What the file calls no data becomes NaN, and so does anything no height could be."""
    want = nodata if nodata is not None and nodata == nodata else None
    if code in 'fd' or want is not None or code == 'h':
        bad16 = -32768.0 if code == 'h' else None
        for i, x in enumerate(v):
            if x != x:
                continue
            if x == want or x == bad16 or x > WILD or x < -WILD:
                v[i] = NAN
    else:
        lo, hi = min(v), max(v)
        if lo < -WILD or hi > WILD:
            for i, x in enumerate(v):
                if x > WILD or x < -WILD:
                    v[i] = NAN


def _geo(tags, w, h, notes, name):
    """(geo for the Raster, what to multiply the file's heights by to get metres)."""
    keys = {}
    gk = tags.get('geokeys')
    doubles = tags.get('geodouble', ())
    if gk and len(gk) >= 4:
        for i in range(gk[3]):
            k, loc, cnt, val = gk[4 + i * 4:8 + i * 4]
            if loc == 0:
                keys[k] = val
            elif loc == 34736 and val < len(doubles):
                keys[k] = doubles[val]
    if 'matrix' in tags and len(tags['matrix']) >= 8:
        m = tags['matrix']
        if abs(m[1]) > 1e-9 or abs(m[4]) > 1e-9:
            notes.append('This file is turned on its map grid, which FOLab doesn\'t follow: it\'s treated as lying square.')
        dx, dy, ox, oy = m[0], -m[5], m[3], m[7]
    elif 'scale' in tags and 'tie' in tags and len(tags['tie']) >= 6:
        s, t = tags['scale'], tags['tie']
        dx, dy = s[0], s[1]
        ox, oy = t[3] - t[0] * s[0], t[4] + t[1] * s[1]
    else:
        notes.append('This TIFF doesn\'t say where on Earth it is: give the size of a pixel by hand.')
        return None, 1.0
    if dx <= 0 or dy == 0:
        notes.append('This TIFF\'s map position makes no sense, so it\'s treated as having none.')
        return None, 1.0
    if dy < 0:
        notes.append('This file is stored south-up; FOLab reads it as it lies, so check it the right way up in the preview.')
        dy = -dy
    # an area pixel's origin is its corner: everything in here means its centre
    if keys.get(1025, 1) != 2:
        ox += dx / 2
        oy -= dy / 2
    model = keys.get(1024)
    epsg = keys.get(3072) if model == 1 else keys.get(2048, 4326)
    unit = 1.0
    if model == 1 or (model is None and (abs(ox) > 360 or abs(oy) > 90)):
        kind = 'proj'
        u = keys.get(3076, 9001)
        unit = {9001: 1.0, 9002: FOOT, 9003: US_FOOT}.get(u, 1.0)
        if 3076 in keys and u not in (9001, 9002, 9003):
            notes.append('This file\'s map unit isn\'t one FOLab knows; it\'s taken as metres.')
    else:
        kind = 'deg'
        if epsg == 32767 or epsg is None:
            epsg = 4326
    z = keys.get(4099)
    zscale = {9002: FOOT, 9003: US_FOOT}.get(z, 1.0)
    if zscale != 1.0:
        notes.append('This file\'s heights are in feet: they\'ve been turned into metres.')
    return {'kind': kind, 'x0': ox, 'y0': oy, 'dx': dx, 'dy': dy, 'epsg': epsg, 'unit': unit}, zscale
