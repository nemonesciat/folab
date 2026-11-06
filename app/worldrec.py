"""Records of the world, as the World tools work on them: regions (REGN), encounter zones (ECZN), a cell's details, map
markers, patrols and encounter spots. Everything goes through the project as usual: records as recordio keeps them, what
changes on a cell in project.cellinfo, what's extra on a ref in the ref's own change.

Measured from the game's files:
  REGN   EDID, RCLR, WNAM, then the area as pairs of RPLI (edge fall-off, 1024 in the game's) and RPLD (corner x, y floats), then
         sections, each an RDAT (type, override, priority): 2 objects RDOT, 3 weather RDWT, 7 sounds RDSD. 5,332 cells name their
         regions in XCLR; both are written, the area kept to the outline of the cells painted.
  ECZN   EDID, DATA: owner, rank, lowest level, flags (1: never resets), a byte never used. The game's files hold no highest
         level, and neither does its loader: a zone sets a floor only.
  a map marker: a persistent REFR of MapMarker (form 10) in the world's persistent cell: XMRK, FNAM (1 shows on the map,
         2 can fast travel there), FULL, TNAM (type, 0), then DATA.
  a patrol: REFRs of XMarkerHeading (form 34) in a ring, each with XPRD (seconds waiting there), XPPA, INAM, SCHR, TNAM and XLKR
         to the next; the actor has XLKR to the first and a Patrol package (type 13) working 'near linked reference'.
  an encounter: no ref in the game's cells names a leveled list: all are ACHR of an NPC_ or ACRE of a CREA, the variety coming
         from a base that takes its looks from one (TPLT)."""
import struct

import recordio
import schema
import tes4

MAP_MARKER = 0x10
X_MARKER_HEADING = 0x34
RECORD_LIMITS = {'RDWT': 8, 'RDSD': 69, 'RDOT': 13}
MARKER_TYPES = ['None', 'City', 'Settlement', 'Encampment', 'Natural landmark', 'Cave', 'Factory', 'Monument', 'Military', 'Office',
                'Town ruins', 'Urban ruins', 'Sewer ruins', 'Metro', 'Vault']
CELL_LINKS = {'XCMO': 'MUSC', 'LTMP': 'LGTM', 'XCCM': 'CLMT', 'XCWT': 'WATR', 'XCAS': 'ASPC', 'XCIM': 'IMGS', 'XEZN': 'ECZN', 'XOWN': 'FACT'}
CELL_ORDER = ['EDID', 'FULL', 'DATA', 'XCLC', 'XCLL', 'IMPS', 'IMPF', 'LTMP', 'LNAM', 'XCLW', 'XNAM', 'XCLR', 'XCCM', 'XCWT', 'XOWN', 'XRNK',
              'XCIM', 'XCMO', 'XEZN', 'XCAS']
XCLL = '<4B4B4B2f2if2f'.replace('4B4B4B', '12B')


class WorldError(ValueError):
    """Why not, in words for the person asking."""


def _form(gd, pr, key):
    return key.startswith('+') and pr.records.get(key)


def ckey_of(gd, world, xy):
    c = gd.grid(world).get(tuple(xy))
    return gd.key(c) if c is not None else None


def _field(rec, tag):
    return next((s for s in rec['subs'] if s['tag'] == tag), None)


def _sub_fields(s):
    return {f['name']: f['value'] for f in s['fields'] if 'name' in f}


# --- what's on a cell, game's and mod's together ---

def cell_info(gd, pr, ckey):
    """{tag: key or text} of what can be changed on a place, as the mod leaves it."""
    out = {}
    if ckey.startswith('+'):
        rec = pr.records.get(ckey) or {'subs': []}
        for tag in CELL_LINKS:
            s = _field(rec, tag)
            if s and s['kind'] == 'F' and s['value']:
                out[tag] = s['value']
        out['FULL'] = recordio.field(rec, 'FULL')
        s = _field(rec, 'XCLL')
        if s and s['kind'] == 'raw':
            out['XCLL'] = _light_from(bytes.fromhex(s['value']))
        elif s and s['kind'] == 'struct':
            out['XCLL'] = _light_from(schema.encode_sub('CELL', s))
    else:
        cell = gd.from_key(ckey)
        i = gd.forms[cell][0]
        f = gd.fields(cell)
        for tag in CELL_LINKS:
            d = f.get(tag)
            if d and len(d) >= 4:
                v = struct.unpack_from('<I', d)[0]
                if v:
                    out[tag] = gd.key(gd.to_global(i, v))
        if 'FULL' in f:
            out['FULL'] = tes4.zstr(f['FULL'])
        if 'XCLL' in f:
            out['XCLL'] = _light_from(f['XCLL'])
    out.update((pr.cellinfo.get(ckey) or {}) if pr else {})
    return {k: v for k, v in out.items() if v not in (None, '') or k == 'XCLR'}


def regions_of(gd, pr, ckey):
    """The regions a cell belongs to, as keys."""
    info = (pr.cellinfo.get(ckey) or {}) if pr else {}
    if 'XCLR' in info:
        return list(info['XCLR'])
    if ckey.startswith('+'):
        return []
    cell = gd.from_key(ckey)
    i = gd.forms[cell][0]
    d = gd.fields(cell).get('XCLR', b'')
    return [gd.key(gd.to_global(i, v)) for v in struct.unpack('<%dI' % (len(d) // 4), d[:len(d) // 4 * 4])]


def _light_from(d):
    b = struct.unpack('<40B', d[:40]) if len(d) >= 40 else (0,) * 40
    near, far = struct.unpack_from('<2f', d, 12) if len(d) >= 20 else (0.0, 0.0)
    hexes = lambda k: '#%02x%02x%02x' % tuple(b[k:k + 3])
    return {'ambient': hexes(0), 'sun': hexes(4), 'fog': hexes(8), 'near': round(near, 1), 'far': round(far, 1)}


def _light_bytes(old, L):
    d = bytearray(old if len(old) >= 40 else struct.pack('<12B2f2i3f', *([0] * 12), 0.0, 0.0, 0, 0, 1.0, 0.0, 1.0))
    for off, k in ((0, 'ambient'), (4, 'sun'), (8, 'fog')):
        c = L[k].lstrip('#')
        d[off:off + 3] = bytes(int(c[j:j + 2], 16) for j in (0, 2, 4))
    struct.pack_into('<2f', d, 12, float(L['near']), float(L['far']))
    return bytes(d)


def apply_cell(subs, info, link):
    """A CELL's subrecords with the mod's details laid over. info: {tag: key, or None to take it away}; XCLR a list of keys;
    XCLL plain colours; FULL words. Each goes where the game's have it."""
    out = list(subs)

    def put(tag, data):
        nonlocal out
        out = [(t, d) for t, d in out if t != tag]
        if data is None:
            return
        rank = CELL_ORDER.index(tag)
        at = next((n for n, (t, _d) in enumerate(out) if t in CELL_ORDER and CELL_ORDER.index(t) > rank), len(out))
        out.insert(at, (tag, data))
    for tag, v in info.items():
        if tag == 'XCLR':
            put(tag, struct.pack('<%dI' % len(v), *[link(k) for k in v]) if v else None)
        elif tag == 'XCLL':
            put(tag, _light_bytes(next((d for t, d in out if t == 'XCLL'), b''), v) if v else None)
        elif tag == 'FULL':
            put(tag, v.encode('cp1252', 'replace') + b'\0' if v else None)
        elif tag in CELL_LINKS:
            put(tag, struct.pack('<I', link(v)) if v else None)
    return out


def cell_ops(gd, pr, ckey, changes):
    """The op setting details on a place: its entry is replaced whole, so Undo stays simple."""
    now = dict(pr.cellinfo.get(ckey) or {})
    now.update(changes)
    return {'op': 'cellinfo', 'cell': ckey, 'info': now}


def cell_details(gd, pr, ckey):
    info = cell_info(gd, pr, ckey)
    out = {'cell': ckey, 'info': info, 'outside': not ckey.startswith('+') and gd.from_key(ckey) in gd.ext_cells,
           'names': {}, 'regions': [], 'changed': sorted((pr.cellinfo.get(ckey) or {}).keys()) if pr else []}
    for tag, key in info.items():
        if tag in CELL_LINKS and key:
            out['names'][tag] = name_of(gd, pr, key)
    out['regions'] = [{'key': k, 'name': name_of(gd, pr, k)} for k in regions_of(gd, pr, ckey)]
    return out


def name_of(gd, pr, key):
    if key.startswith('+'):
        return recordio.field(pr.records.get(key) or {'subs': []}, 'EDID') or key
    f = gd.from_key(key)
    return (gd.edid(f) if f in gd.forms else '') or key


def choices(gd, pr, types):
    """Records to pick from: [{key, name}] of those types, the mod's first."""
    out = []
    for key, r in (pr.records.items() if pr else ()):
        if r['type'] in types and key.startswith('+'):
            out.append({'key': key, 'name': recordio.field(r, 'EDID') or key, 'type': r['type']})
    rows = []
    for f, (_i, r) in gd.forms.items():
        if r.tag in types:
            rows.append({'key': gd.key(f), 'name': gd.edid(f) or gd.key(f), 'type': r.tag})
    rows.sort(key=lambda x: x['name'].lower())
    return out + rows


# --- regions ---

def outline(cells):
    """The loops round a set of grid squares, as lists of corner (x, y) in game units: outside loops anticlockwise."""
    cells = set(tuple(c) for c in cells)
    next_of = {}
    for x, y in cells:
        for (ax, ay), (bx, by), d in (((x, y), (x + 1, y), (x, y - 1)), ((x + 1, y), (x + 1, y + 1), (x + 1, y)),
                                      ((x + 1, y + 1), (x, y + 1), (x, y + 1)), ((x, y + 1), (x, y), (x - 1, y))):
            if d not in cells:
                next_of.setdefault((ax, ay), []).append((bx, by))
    loops = []
    while next_of:
        start = next(iter(next_of))
        loop, p, came = [start], start, None
        while True:
            options = next_of[p]
            # (where two squares touch at a corner, turn the tightest way, so the loops don't cross)
            if len(options) > 1 and came is not None:
                options.sort(key=lambda q: (came[0] * (q[1] - p[1]) - came[1] * (q[0] - p[0])), reverse=True)
            q = options.pop(0)
            if not options:
                del next_of[p]
            came = (q[0] - p[0], q[1] - p[1])
            p = q
            if p == start:
                break
            loop.append(p)
        # straight runs need only their ends
        tight = []
        n = len(loop)
        for k in range(n):
            a, b, c = loop[k - 1], loop[k], loop[(k + 1) % n]
            if (b[0] - a[0]) * (c[1] - b[1]) != (b[1] - a[1]) * (c[0] - b[0]):
                tight.append(b)
        loops.append([(x * 4096.0, y * 4096.0) for x, y in tight])
    return loops


def _sub(rtype, tag, data):
    return schema.decode_sub(rtype, tag, data, False)


def _set_links(s, values):
    """A decoded struct's fields, by the order of their values."""
    keep = [f for f in s['fields'] if 'name' in f]
    for f, v in zip(keep, values):
        f['value'] = v
    return s


OBJECT_FIELDS = 'object,parent,density,cluster,slope_min,slope_max,flags,parent_radius,radius,height_min,height_max,sink,sink_var,size_var,ax,ay,az'.split(',')


def region_read(gd, pr, key):
    """A region as plain fields."""
    rec = pr.records.get(key) if pr else None
    if rec is None:
        rec = recordio.load(gd, gd.from_key(key))
    out = {'key': key, 'mine': key.startswith('+'), 'changed': bool(pr and key in pr.records), 'edid': recordio.field(rec, 'EDID'), 'color': '#c0c0c0', 'world': recordio.field(rec, 'WNAM'),
           'weathers': [], 'sounds': [], 'objects': [], 'priority': 50, 'map': ''}
    section = None
    for s in rec['subs']:
        if s['tag'] == 'RCLR':
            v = _sub_fields(s)
            out['color'] = '#%02x%02x%02x' % (v['Red'], v['Green'], v['Blue'])
        elif s['tag'] == 'RDAT' and s['kind'] == 'struct':
            v = _sub_fields(s)
            section = v['Type']
            if section == 3:
                out['priority'] = v['Priority']
        elif s['tag'] == 'RDMP':
            out['map'] = s['value']
        elif s['tag'] == 'RDWT' and s['kind'] == 'struct':
            vals = [f['value'] for f in s['fields'] if 'name' in f]
            for k in range(0, len(vals) - 2, 3):
                out['weathers'].append({'key': vals[k], 'chance': vals[k + 1], 'global': vals[k + 2], 'name': name_of(gd, pr, vals[k])})
        elif s['tag'] == 'RDSD' and s['kind'] == 'struct':
            vals = [f['value'] for f in s['fields'] if 'name' in f]
            for k in range(0, len(vals) - 2, 3):
                out['sounds'].append({'key': vals[k], 'flags': vals[k + 1], 'chance': vals[k + 2], 'name': name_of(gd, pr, vals[k])})
        elif s['tag'] == 'RDOT' and s['kind'] == 'struct':
            vals = [f['value'] for f in s['fields'] if 'name' in f]
            for k in range(0, len(vals), len(OBJECT_FIELDS)):
                o = dict(zip(OBJECT_FIELDS, vals[k:k + len(OBJECT_FIELDS)]))
                o['key'] = o.pop('object')
                o['name'] = name_of(gd, pr, o['key'])
                out['objects'].append(o)
    return out


def _chunks(rows, n):
    return [rows[k:k + n] for k in range(0, len(rows), n)] or []


def region_record(gd, pr, d, cells, base=None):
    """A REGN from plain fields. base: the record as it was (a game region or a copy), kept but for what's in d; sections FOLab
    doesn't show (map names, imposters, grass, land) go along. cells: the squares it covers now; None leaves its area alone."""
    rec = {'type': 'REGN', 'flags': (base or {}).get('flags', 0), 'src': (base or {}).get('src', ''), 'subs': []}
    color = d.get('color', '#c0c0c0').lstrip('#')
    head = [_sub('REGN', 'EDID', d['edid'].encode('cp1252', 'replace') + b'\0'),
            _sub('REGN', 'RCLR', bytes(int(color[j:j + 2], 16) for j in (0, 2, 4)) + b'\0'),
            _sub('REGN', 'WNAM', b'\0\0\0\0')]
    head[2]['value'] = d['world']
    rec['subs'] += head
    if cells is None:
        rec['subs'] += [s for s in (base or {'subs': []})['subs'] if s['tag'] in ('RPLI', 'RPLD')]
    else:
        for loop in outline(cells):
            rec['subs'].append(_sub('REGN', 'RPLI', struct.pack('<I', 1024)))
            rec['subs'].append(_sub('REGN', 'RPLD', b''.join(struct.pack('<2f', *p) for p in loop)))

    def section(kind, prio=None):
        return _sub('REGN', 'RDAT', struct.pack('<IBBH', kind, 0, 50 if prio is None else int(prio), 0))
    # the kept sections: anything after an RDAT of a type not edited here
    kept, on = [], False
    for s in (base or {'subs': []})['subs']:
        if s['tag'] == 'RDAT' and s['kind'] == 'struct':
            on = _sub_fields(s)['Type'] not in (2, 3, 7)
        if on:
            kept.append(s)
    objects = d.get('objects', [])
    if objects:
        rec['subs'].append(section(2))
        for chunk in _chunks(objects, RECORD_LIMITS['RDOT'])[:1]:
            s = _sub('REGN', 'RDOT', b'\0' * 52 * len(chunk))
            vals = []
            for o in chunk:
                vals += [o['key']] + [o.get(k, 0) for k in OBJECT_FIELDS[1:]]
            rec['subs'].append(_set_links(s, vals))
    weathers = d.get('weathers', [])
    if weathers:
        rec['subs'].append(section(3, d.get('priority')))
        s = _sub('REGN', 'RDWT', b'\0' * 12 * min(len(weathers), RECORD_LIMITS['RDWT']))
        vals = []
        for w in weathers[:RECORD_LIMITS['RDWT']]:
            vals += [w['key'], int(w.get('chance', 100)), w.get('global', '')]
        rec['subs'].append(_set_links(s, vals))
    sounds = d.get('sounds', [])
    if sounds:
        rec['subs'].append(section(7))
        s = _sub('REGN', 'RDSD', b'\0' * 12 * min(len(sounds), RECORD_LIMITS['RDSD']))
        vals = []
        for w in sounds[:RECORD_LIMITS['RDSD']]:
            vals += [w['key'], int(w.get('flags', 0)), int(w.get('chance', 50))]
        rec['subs'].append(_set_links(s, vals))
    rec['subs'] += kept
    return rec


def region_cells(gd, pr, world):
    """{key: [[x, y]]} of the regions cells in a world belong to, the mod's painting over the game's. Kept per world, for speed."""
    out = {}
    cached = getattr(gd, '_region_cells', {}).get(world)
    if cached is None:
        cached = {}
        for xy, c in gd.grid(world).items():
            d = gd.fields(c).get('XCLR')
            if d:
                i = gd.forms[c][0]
                cached[xy] = [gd.key(gd.to_global(i, v)) for v in struct.unpack('<%dI' % (len(d) // 4), d)]
        if not hasattr(gd, '_region_cells'):
            gd._region_cells = {}
        gd._region_cells[world] = cached
    back = {c: xy for xy, c in gd.grid(world).items()} if pr and pr.cellinfo else {}
    over = {}
    for ckey, info in (pr.cellinfo.items() if pr else ()):
        if 'XCLR' in info and not ckey.startswith('+') and gd.from_key(ckey) in back:
            over[back[gd.from_key(ckey)]] = info['XCLR']
    for xy, keys in list(cached.items()) + list(over.items()):
        if xy in over and keys is not over[xy]:
            continue
        for k in keys:
            out.setdefault(k, []).append(list(xy))
    return out


def regions_list(gd, pr, world):
    wkey = gd.key(world)
    cells = region_cells(gd, pr, world)
    out = []
    seen = set()
    for key, rec in (pr.records.items() if pr else ()):
        if rec['type'] == 'REGN' and recordio.field(rec, 'WNAM') == wkey:
            seen.add(key)
            out.append(key)
    for f, (i, r) in gd.forms.items():
        if r.tag == 'REGN':
            k = gd.key(f)
            if k in seen:
                continue
            w = gd.fields(f).get('WNAM')
            if w and gd.to_global(i, struct.unpack('<I', w)[0]) == world:
                out.append(k)
    rows = []
    for k in out:
        r = region_read(gd, pr, k)
        rows.append({'key': k, 'edid': r['edid'], 'color': r['color'], 'mine': r['mine'], 'changed': r['changed'], 'cells': cells.get(k, []),
                     'weathers': len(r['weathers']), 'sounds': len(r['sounds']), 'objects': len(r['objects'])})
    rows.sort(key=lambda r: (not r['mine'], r['edid'].lower()))
    return rows


def region_save(gd, pr, body):
    """New or changed region: (ops, its key)."""
    d = body['region']
    key = body.get('key')
    if not d.get('edid'):
        raise WorldError('A region needs a name.')
    base = None
    if key:
        base = pr.records.get(key) or recordio.load(gd, gd.from_key(key))
    world = gd.from_key(body['world'])
    d = dict(d, world=body['world'])
    cells = None
    if not key:
        key = '+%06X' % pr.next_id
        pr.next_id += 1
        cells = []
    return [{'op': 'record', 'key': key, 'record': region_record(gd, pr, d, cells, base)}], key


def region_paint(gd, pr, body):
    """Cells added to or taken from a region: the ops, one Undo. The region's own area follows when it's the mod's."""
    world = gd.from_key(body['world'])
    key = body['key']
    ops = []
    for xy, on in [(c, True) for c in body.get('add', [])] + [(c, False) for c in body.get('remove', [])]:
        ck = ckey_of(gd, world, xy)
        if not ck:
            continue
        have = regions_of(gd, pr, ck)
        if on and key not in have:
            have = have + [key]
        elif not on and key in have:
            have = [k for k in have if k != key]
        ops.append(cell_ops(gd, pr, ck, {'XCLR': have}))
    # its area in the record, as it will be
    if key in pr.records and key.startswith('+'):
        now = {tuple(c) for c in region_cells(gd, pr, world).get(key, [])}
        now |= {tuple(c) for c in body.get('add', []) if ckey_of(gd, world, c)}
        now -= {tuple(c) for c in body.get('remove', [])}
        d = region_read(gd, pr, key)
        ops.append({'op': 'record', 'key': key, 'record': region_record(gd, pr, d, sorted(now), pr.records[key])})
    return ops


def region_objects_from_game(gd, world, x, y):
    """Objects for a region's list, as the game placed them round this spot (via scatter.py)."""
    import scatter
    out = []
    for kind, rows in scatter.learn(gd, world, int(x), int(y)).items():
        for b in rows[:6]:
            out.append({'key': b['key'], 'name': b['edid'], 'parent': 0, 'density': round(min(30.0, 2.0 + b['n'] / 8.0), 1), 'cluster': 0, 'slope_min': 0, 'slope_max': 45,
                        'flags': 0, 'parent_radius': 0, 'radius': 0, 'height_min': 0.0, 'height_max': 0.0, 'sink': max(0.0, -b['dz']), 'sink_var': 0.0,
                        'size_var': round(b['smax'] - b['smin'], 2), 'ax': 0, 'ay': 0, 'az': 360, 'kind': kind})
    return out[:RECORD_LIMITS['RDOT']]


def scatter_set(gd, pr, world, x, y):
    """What a Scatter brush can use from regions here: the objects of those the cell belongs to, in scatter.learn's form."""
    ck = ckey_of(gd, world, (x, y))
    if not ck:
        return []
    out = []
    for rk in regions_of(gd, pr, ck):
        try:
            r = region_read(gd, pr, rk)
        except (KeyError, ValueError):
            continue
        for o in r['objects']:
            if o['key'].startswith('+'):
                continue
            f = gd.from_key(o['key'])
            if f not in gd.forms:
                continue
            btype, edid, _n, model = gd.describe(f)
            if not model:
                continue
            sv = o.get('size_var', 0) or 0
            out.append({'key': o['key'], 'edid': edid, 'model': gd.model_path(btype, model), 'type': btype, 'n': max(1, int(o.get('density', 1) * 4)),
                        'tree': gd.tree(f) if btype == 'TREE' else None, 'smin': round(1 - sv / 2, 2), 'smax': round(1 + sv / 2, 2),
                        'dz': -float(o.get('sink', 0) or 0), 'tilt': 0.0})
    return out


# --- encounter zones ---

def zone_read(gd, pr, key):
    rec = pr.records.get(key) if pr else None
    if rec is None:
        rec = recordio.load(gd, gd.from_key(key))
    v = _sub_fields(_field(rec, 'DATA'))
    return {'key': key, 'edid': recordio.field(rec, 'EDID'), 'owner': v['Owner'], 'rank': v['Rank'], 'level': v['Min level'], 'flags': v['Flags'], 'mine': key.startswith('+')}


def zone_record(d, base=None):
    s = _sub('ECZN', 'DATA', b'\0' * 8)
    for f in s['fields']:
        n = f.get('name')
        if n == 'Owner':
            f['value'] = d.get('owner') or ''
        elif n == 'Rank':
            f['value'] = int(d.get('rank', 0))
        elif n == 'Min level':
            f['value'] = max(0, min(127, int(d.get('level', 0))))
        elif n == 'Flags':
            f['value'] = int(d.get('flags', 0))
    return {'type': 'ECZN', 'flags': (base or {}).get('flags', 0), 'src': (base or {}).get('src', ''), 'subs': [_sub('ECZN', 'EDID', d['edid'].encode('cp1252', 'replace') + b'\0'), s]}


def zones_list(gd, pr, world=None):
    """Every zone, with which of a world's squares use it."""
    rows = {}
    for key, rec in (pr.records.items() if pr else ()):
        if rec['type'] == 'ECZN':
            rows[key] = zone_read(gd, pr, key)
    for f, (_i, r) in gd.forms.items():
        if r.tag == 'ECZN':
            k = gd.key(f)
            rows.setdefault(k, zone_read(gd, pr, k))
    if world is not None:
        cached = getattr(gd, '_zone_cells', {}).get(world)
        if cached is None:
            cached = {}
            for xy, c in gd.grid(world).items():
                d = gd.fields(c).get('XEZN')
                if d and len(d) >= 4:
                    v = struct.unpack_from('<I', d)[0]
                    if v:
                        cached[xy] = gd.key(gd.to_global(gd.forms[c][0], v))
            if not hasattr(gd, '_zone_cells'):
                gd._zone_cells = {}
            gd._zone_cells[world] = cached
        now = dict(cached)
        back = {c: xy for xy, c in gd.grid(world).items()}
        for ck, info in (pr.cellinfo.items() if pr else ()):
            if 'XEZN' in info and not ck.startswith('+') and gd.from_key(ck) in back:
                xy = back[gd.from_key(ck)]
                if info['XEZN']:
                    now[xy] = info['XEZN']
                else:
                    now.pop(xy, None)
        for r in rows.values():
            r['cells'] = []
        for xy, k in now.items():
            if k in rows:
                rows[k]['cells'].append(list(xy))
    return sorted(rows.values(), key=lambda r: (not r['mine'], r['edid'].lower()))


def zone_save(gd, pr, body):
    d = body['zone']
    if not d.get('edid'):
        raise WorldError('A zone needs a name.')
    key = body.get('key')
    base = (pr.records.get(key) or recordio.load(gd, gd.from_key(key))) if key else None
    if not key:
        key = '+%06X' % pr.next_id
        pr.next_id += 1
    return [{'op': 'record', 'key': key, 'record': zone_record(d, base)}], key


def zone_paint(gd, pr, body):
    world = gd.from_key(body['world'])
    ops = []
    for xy in body.get('add', []):
        ck = ckey_of(gd, world, xy)
        if ck:
            ops.append(cell_ops(gd, pr, ck, {'XEZN': body['key']}))
    for xy in body.get('remove', []):
        ck = ckey_of(gd, world, xy)
        if ck:
            ops.append(cell_ops(gd, pr, ck, {'XEZN': None}))
    return ops


# --- map markers ---

def marker_op(gd, world, p, name, mtype, flags=3):
    return {'op': 'add', 'cell': ckey_of(gd, world, (int(p[0] // 4096), int(p[1] // 4096))), 'base': gd.key(MAP_MARKER), 'p': [p[0], p[1], p[2], 0, 0, 0], 's': 1,
            'extra': {'persistent': True, 'marker': {'name': name, 'type': int(mtype), 'flags': int(flags)}}}


def markers_list(gd, pr, world):
    """The mod's markers and the game's it changed, for the map and the list."""
    out = []
    back = {c: xy for xy, c in gd.grid(world).items()}
    for ck, c in (pr.cells.items() if pr else ()):
        if ck.startswith('+') or gd.from_key(ck) not in back:
            continue
        for rk, r in c['refs'].items():
            if r.get('marker'):
                out.append({'cell': ck, 'ref': rk, 'p': r.get('p'), 'name': r['marker']['name'], 'type': r['marker']['type'], 'flags': r['marker']['flags']})
    return out


def ref_extra_subs(r, link):
    """What a new ref's extras write, in the order the game's have them. (first, after NAME; last, just before DATA or XSCL)"""
    first, last = [], []
    if r.get('zone'):
        first.append(('XEZN', struct.pack('<I', link(r['zone']))))
    if 'patrol_wait' in r:
        first += [('XPRD', struct.pack('<f', float(r['patrol_wait']))), ('XPPA', b''), ('INAM', b'\0\0\0\0'),
                  ('SCHR', b'\0' * 16 + b'\x01\0\0\0'), ('TNAM', b'\0\0\0\0')]
    m = r.get('marker')
    if m:
        first += [('XMRK', b''), ('FNAM', bytes([int(m['flags']) & 0xFF])), ('FULL', m['name'].encode('cp1252', 'replace') + b'\0'),
                  ('TNAM', struct.pack('<BB', int(m['type']) & 0xFF, 0))]
    if r.get('link'):
        last.append(('XLKR', struct.pack('<I', link(r['link']))))
    return first, last


def ref_extra_keys(r):
    return [k for k in (r.get('zone'), r.get('link')) if k]


# --- patrols and encounter spots ---

def _patrol_package(gd):
    """A Patrol package of the game's, working 'near linked reference', with no script of its own: the one to copy."""
    best = None
    for f, (i, r) in sorted(gd.forms.items()):
        if r.tag != 'PACK' or i != 0:
            continue
        fl = gd.fields(f)
        pk, pl = fl.get('PKDT'), fl.get('PLDT')
        if pk and pl and len(pk) >= 5 and pk[4] == 13 and struct.unpack_from('<I', pl)[0] == 6:
            n = len(list(tes4.iter_subrecords(gd.plugins[i].data(r))))
            if best is None or n < best[0]:
                best = (n, f)
    return best[1] if best else None


def patrol_ops(gd, pr, body):
    """A patrol on the world: heading markers round the points, joined in a ring, and an actor (a copy of the base, with a Patrol
    package of its own put first) standing at the first. Returns the ops; each marker is filed under its own square."""
    world = gd.from_key(body['world'])
    pts = body['points']
    if len(pts) < 2:
        raise WorldError('A patrol needs at least two points.')
    base = gd.from_key(body['base'])
    btype = gd.forms[base][1].tag
    if btype not in ('NPC_', 'CREA'):
        raise WorldError('Pick a character or a creature to walk it.')
    pack = _patrol_package(gd)
    if pack is None:
        raise WorldError('No Patrol package of the right kind in the game\'s files to copy.')
    edid = ''.join(c for c in body.get('name') or 'FOLabPatrol' if c.isalnum()) or 'FOLabPatrol'

    def new_key():
        k = '+%06X' % pr.next_id
        pr.next_id += 1
        return k
    ops = []
    pkey, akey = new_key(), new_key()
    prec = recordio.load(gd, pack)
    recordio.set_field(prec, 'EDID', edid + 'Package', label='Editor ID')
    ops.append({'op': 'record', 'key': pkey, 'record': prec})
    arec = recordio.load(gd, base)
    recordio.set_field(arec, 'EDID', edid + 'Walker', label='Editor ID')
    at = next((n for n, s in enumerate(arec['subs']) if s['tag'] == 'PKID'), None)
    pk = {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': pkey}
    if at is None:
        at = next((n for n, s in enumerate(arec['subs']) if s['tag'] in ('CNAM', 'HNAM', 'LNAM', 'ENAM', 'HCLR', 'ZNAM', 'NAM4', 'NAM5', 'CSCR', 'CSDT', 'NAM7', 'CNTO')), len(arec['subs']))
    arec['subs'].insert(at, pk)
    ops.append({'op': 'record', 'key': akey, 'record': arec})
    wait = float(body.get('wait', 5))
    # the markers' keys are made here so each can name the next
    keys = [new_key() for _ in pts]
    grid = gd.grid(world)
    for n, p in enumerate(pts):
        c = grid.get((int(p[0] // 4096), int(p[1] // 4096)))
        if c is None:
            raise WorldError('A point is off this world\'s land.')
        ops.append({'op': 'place', 'cell': gd.key(c), 'key': keys[n], 'ref': {'base': gd.key(X_MARKER_HEADING), 'p': [float(p[0]), float(p[1]), float(p[2]), 0.0, 0.0, 0.0], 's': 1.0,
                                                                                'persistent': True, 'patrol_wait': wait, 'link': keys[(n + 1) % len(keys)]}})
    p0 = pts[0]
    ops.append({'op': 'place', 'cell': gd.key(grid[(int(p0[0] // 4096), int(p0[1] // 4096))]), 'key': new_key(),
                'ref': {'base': akey, 'p': [float(p0[0]), float(p0[1]), float(p0[2]) + 16, 0.0, 0.0, 0.0], 's': 1.0, 'persistent': True, 'link': keys[0]}})
    return ops, {'actor': akey, 'package': pkey, 'markers': keys}


def encounter_choices(gd, pr):
    """Who can stand at a spot: those whose looks come from a leveled list first (different each time, level by level)."""
    leveled, plain = [], []
    for f, (i, r) in gd.forms.items():
        if r.tag in ('NPC_', 'CREA'):
            fl = gd.plugins[i].fields(r)
            row = {'key': gd.key(f), 'name': tes4.zstr(fl.get('EDID', b'')) or gd.key(f), 'type': r.tag}
            t = fl.get('TPLT')
            if t and len(t) >= 4 and gd.to_global(i, struct.unpack_from('<I', t)[0]) in gd.forms and gd.forms[gd.to_global(i, struct.unpack_from('<I', t)[0])][1].tag.startswith('LV'):
                row['leveled'] = True
                leveled.append(row)
            else:
                plain.append(row)
    leveled.sort(key=lambda r: r['name'].lower())
    plain.sort(key=lambda r: r['name'].lower())
    return leveled + plain


def encounter_ops(gd, pr, body):
    """Actors at a spot, spread a little round it, in a zone if given."""
    import math
    world = gd.from_key(body['world'])
    p = body['p']
    base = body['base']
    count = max(1, min(12, int(body.get('count', 3))))
    reach = float(body.get('spread', 192))
    ops = []
    for n in range(count):
        a = 2 * math.pi * n / count
        x, y = p[0] + (reach * math.cos(a) if count > 1 else 0), p[1] + (reach * math.sin(a) if count > 1 else 0)
        z = body.get('heights', [p[2]] * count)[n]
        ck = ckey_of(gd, world, (int(x // 4096), int(y // 4096)))
        if not ck:
            continue
        extra = {}
        if body.get('zone'):
            extra['zone'] = body['zone']
        ops.append({'op': 'add', 'cell': ck, 'base': base, 'p': [x, y, z, 0, 0, a], 's': 1, 'extra': extra})
    return ops
