"""What a placed object carries besides where it stands: owner, lock, where a door leads, what enables it.
For the object window and the right-click menu. Read-only."""
import struct

import tes4

LOCK_LEVELS = {0: 'Very easy', 25: 'Easy', 50: 'Average', 75: 'Hard', 100: 'Very hard', 255: 'Needs a key'}


def _name(gd, fid):
    """'EditorID (Name)' for a form, or its key when it isn't loaded."""
    if fid not in gd.forms:
        return '%08X' % fid
    f = gd.fields(fid)
    e, n = tes4.zstr(f.get('EDID', b'')), tes4.zstr(f.get('FULL', b''))
    return '%s (%s)' % (e, n) if n and n != e else e or '%08X' % fid


def door_target(gd, fid):
    """Where a door ref leads: {'door', 'cell', 'cell_edid', 'interior', 'p': [x, y, z, rx, ry, rz]} or None."""
    if fid not in gd.ref_cell:
        return None
    i, rec = gd.cell_refs[gd.ref_cell[fid]][fid]
    f = gd.plugins[i].fields(rec)
    if 'XTEL' not in f or len(f['XTEL']) < 28:
        return None
    dest = gd.to_global(i, struct.unpack_from('<I', f['XTEL'])[0])
    p = list(struct.unpack_from('<6f', f['XTEL'], 4))
    cell = gd.ref_cell.get(dest)
    out = {'door': gd.key(dest) if dest in gd.forms or cell else '%08X' % dest, 'p': p,
           'cell': gd.key(cell) if cell else None, 'interior': cell in gd.interiors if cell else False}
    if cell:
        cf = gd.fields(cell)
        out['cell_edid'] = tes4.zstr(cf.get('EDID', b''))
        out['cell_name'] = tes4.zstr(cf.get('FULL', b''))
        # outside: the worldspace it leads into (the door itself is usually in the world's persistent cell)
        world = gd.ext_cells.get(cell) or next((w for w, c in gd.world_persistent.items() if c == cell), None)
        if world is not None:
            wf = gd.fields(world)
            out['world'] = gd.key(world)
            out['world_name'] = tes4.zstr(wf.get('FULL', b'')) or tes4.zstr(wf.get('EDID', b''))
    return out


def ref_info(gd, fid):
    """The placed object's own fields, readable."""
    if fid not in gd.ref_cell:
        return {}
    i, rec = gd.cell_refs[gd.ref_cell[fid]][fid]
    f = gd.plugins[i].fields(rec)
    g = lambda off, sd: gd.to_global(i, struct.unpack_from('<I', sd, off)[0])
    out = {'persistent': bool(rec.flags & tes4.PERSISTENT), 'disabled': bool(rec.flags & 0x800),
           'from': gd.names[i]}
    if 'EDID' in f:
        out['edid'] = tes4.zstr(f['EDID'])
    if 'XOWN' in f:
        out['owner'] = _name(gd, g(0, f['XOWN']))
        if 'XRNK' in f:
            out['owner_rank'] = struct.unpack_from('<i', f['XRNK'])[0]
    if 'XLOC' in f and len(f['XLOC']) >= 8:
        level = f['XLOC'][0]
        out['lock'] = LOCK_LEVELS.get(level, str(level))
        key = struct.unpack_from('<I', f['XLOC'], 4)[0]
        if key:
            out['lock_key'] = _name(gd, gd.to_global(i, key))
    if 'XESP' in f:
        out['enable_parent'] = _name(gd, g(0, f['XESP']))
        out['enable_opposite'] = bool(len(f['XESP']) > 4 and f['XESP'][4] & 1)
    if 'XTEL' in f:
        out['door'] = door_target(gd, fid)
    if 'XCNT' in f:
        out['count'] = struct.unpack_from('<i', f['XCNT'])[0]
    if 'XLKR' in f:
        out['linked'] = _name(gd, g(0, f['XLKR']))
    return out
