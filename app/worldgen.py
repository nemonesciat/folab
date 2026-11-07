"""A new worldspace: added to a plugin as the game files one.

    WRLD top group
        WRLD record (the template world's settings: climate, water, image space, music; its own name and bounds)
        world children group (label: the WRLD)
            persistent CELL (no grid square) + its children
            exterior block (label y//32, x//32) > sub-block (y//8, x//8) > CELL + children > temporary > LAND

Each grid cell copies the template world's persistent cell (its lighting template, acoustic space, water flag at the
world's level) with its own XCLC; each has flat land at the height asked, one ground texture, plain colour. The
world record keeps no parent, no map picture and no offset table (those describe the template's own file).

Land already worked out (mapworld.py) comes through opts: 'rect' (x0, y0, w, h) for any oblong of cells, 'land_for'(x, y) ->
(land.py form, beyond for its normals), 'wet'(x, y) -> whether the cell has water, at the world's level ('water'), 'progress'(n, of).
Those LAND records are stored compressed, as the game's own are."""
import struct
import zlib

import espwrite
import land
import plugintree
import tes4

WORLD_DROP = ('OFST', 'WNAM', 'PNAM', 'ICON', 'XEZN')


def add_world(gd, tree, writer, next_id, opts):
    """Add a world to a plugin tree. writer: an espwrite.Writer whose masters this plugin has (for links);
    opts: {edid, name, template (WRLD fid), size (cells across), height, ltex (key)}. Returns (world key as the
    plugin's own form ID, next free ID)."""
    order = gd.plugins[0].top_groups()
    own = writer.own
    tpl = opts['template']
    if opts.get('rect'):
        x0, y0, nx, ny = opts['rect']
    else:
        nx = ny = int(opts['size'])
        x0 = y0 = -nx // 2
    cells = [(x, y) for y in range(y0, y0 + ny) for x in range(x0, x0 + nx)]

    def new_id():
        nonlocal next_id
        next_id += 1
        return own(next_id - 1)

    # the world record
    i, rec = gd.source(tpl)
    subs = [(t, d) for t, d in writer.remap_fields(i, 'WRLD', list(tes4.iter_subrecords(gd.plugins[i].data(rec))))
            if t not in WORLD_DROP and t not in ('EDID', 'FULL')]
    wide = max(nx, ny)
    head = [('EDID', opts['edid'].encode('cp1252') + b'\0')]
    if opts.get('name'):
        head.append(('FULL', opts['name'].encode('cp1252', 'replace') + b'\0'))
    body = []
    for t, d in subs:
        if t == 'MNAM' and len(d) >= 16:
            d = struct.pack('<iihhhh', 2048 * nx // wide, 2048 * ny // wide, x0, y0 + ny - 1, x0 + nx - 1, y0)   # (map corners: north-west, south-east)
        elif t == 'NAM0':
            d = struct.pack('<2f', x0 * 4096, y0 * 4096)
        elif t == 'NAM9':
            d = struct.pack('<2f', (x0 + nx) * 4096, (y0 + ny) * 4096)
        elif t == 'DNAM' and len(d) >= 8:
            water = d[4:8] if opts.get('water') is None else struct.pack('<f', float(opts['water']))
            d = struct.pack('<f', float(opts['height'])) + water                  # (default land height; its water)
        body.append((t, d))
    wid = new_id()
    wrld = plugintree.Rec.new('WRLD', 0, wid, espwrite.join(head + body), espwrite.FORM_VERSION)
    top = tree.top('WRLD', order)
    top.kids.append(wrld)
    wkids = plugintree.Group(wid, tes4.G_WORLD_CHILDREN)
    top.kids.append(wkids)

    # its persistent cell: the template's, numbered for this plugin
    pc = gd.world_persistent.get(tpl)
    if pc is not None:
        i, prec = gd.source(pc)
        psubs = [(t, d) for t, d in writer.remap_fields(i, 'CELL', list(tes4.iter_subrecords(gd.plugins[i].data(prec))))
                 if t not in ('EDID', 'FULL', 'XCLR', 'XEZN')]
    else:
        psubs = [('DATA', b'\x02'), ('XCLC', struct.pack('<iiI', 0, 0, 0)), ('XCLW', struct.pack('<f', espwrite.WORLD_WATER))]
    pid = new_id()
    wkids.kids += [plugintree.Rec.new('CELL', tes4.PERSISTENT, pid, espwrite.join(psubs), espwrite.FORM_VERSION),
                   plugintree.Group(pid, tes4.G_CELL_CHILDREN)]

    # the grid: each cell like the persistent one with its square, flat land on it
    flat = {'h': [float(opts['height'])] * 1089, 'c': 'ff' * (33 * 33 * 3),
            'q': [{'bkey': opts['ltex'], 'base': None, 'layers': []} for _ in range(4)]}
    land_subs = land.encode(flat, [('DATA', struct.pack('<I', 0x1F))], writer.link)
    label = lambda a, b: struct.unpack('<I', struct.pack('<hh', a, b))[0]
    land_for, wet, progress = opts.get('land_for'), opts.get('wet'), opts.get('progress')
    for done, (x, y) in enumerate(cells):
        csubs = [(t, struct.pack('<iiI', x, y, 0) if t == 'XCLC' else d) for t, d in psubs]
        if wet:
            csubs = espwrite.set_water(csubs, None) if wet(x, y) else _dry(csubs)
        cid = new_id()
        block = writer._group(wkids, label(y // 32, x // 32), tes4.G_EXT_BLOCK)
        sub = writer._group(block, label(y // 8, x // 8), tes4.G_EXT_SUBBLOCK)
        kids = plugintree.Group(cid, tes4.G_CELL_CHILDREN)
        temp = plugintree.Group(cid, tes4.G_CELL_TEMPORARY)
        if land_for:
            form, beyond = land_for(x, y)
            raw = espwrite.join(land.encode(form, [('DATA', struct.pack('<I', 0x1F))], writer.link, beyond))
            temp.kids.append(plugintree.Rec.new('LAND', tes4.COMPRESSED, new_id(), struct.pack('<I', len(raw)) + zlib.compress(raw, 6), espwrite.FORM_VERSION))
            if progress:
                progress(done + 1, len(cells))
        else:
            temp.kids.append(plugintree.Rec.new('LAND', 0, new_id(), espwrite.join(land_subs), espwrite.FORM_VERSION))
        kids.kids.append(temp)
        sub.kids += [plugintree.Rec.new('CELL', 0, cid, espwrite.join(csubs), espwrite.FORM_VERSION), kids]
    return wid, next_id


def _dry(subs):
    """A CELL's subrecords with no water."""
    return [(t, bytes([d[0] & ~2]) + d[1:] if t == 'DATA' and d else d) for t, d in subs if t != 'XCLW']


def fix_header(tree, next_id_formid):
    """The plugin's header with its record count and next ID brought up to date."""
    subs = list(tes4.iter_subrecords(tree.header.raw))
    old = next((d for t, d in subs if t == 'HEDR'), None)
    v, _n, nxt = struct.unpack_from('<fiI', old)
    hedr = struct.pack('<fiI', v, tree.count(), max(nxt, next_id_formid)) + old[12:]
    tree.header.set_data(espwrite.join([(t, hedr if t == 'HEDR' else d) for t, d in subs]), tree.header.flags)
