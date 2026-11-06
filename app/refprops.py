"""A placed thing's own settings beside where it stands: who owns it, its lock, what enables it, whether it starts
switched off. Read from the game's record, changed by the op 'props' in a project and written by espwrite through
apply(). Kept whole in the ref's change: r['props'] = {'owner': key or '', 'rank': n, 'lock': {'level', 'key', 'leveled'}
or None, 'parent': {'ref': key, 'opposite': bool, 'popin': bool} or None, 'disabled': bool}; what isn't there stays as
the game has it.

The bytes are as in the game's own records (checked in tests/test_library.py against every game ref holding them):
    XOWN  the owner (a character or faction)                 XRNK  the faction rank that may use it
    XLOC  level (0-100; 255: needs a key), 3 spare bytes, key, flags (4: goes with the player's level), 3 spare, 8 spare
    XESP  the ref that enables it, flags (1: the opposite of it, 2: pops in)"""
import struct

import tes4

LOCK_LEVELS = [(0, 'Very easy'), (25, 'Easy'), (50, 'Average'), (75, 'Hard'), (100, 'Very hard'), (255, 'Needs a key')]
CAN_LOCK = {'DOOR', 'CONT', 'TERM'}
CAN_OWN = {'STAT', 'MSTT', 'FURN', 'CONT', 'DOOR', 'LIGH', 'MISC', 'ACTI', 'TACT', 'TERM', 'BOOK', 'NOTE', 'WEAP', 'ARMO',
           'ALCH', 'AMMO', 'KEYM', 'IMOD', 'CHIP', 'CMNY', 'CCRD'}


def encode_lock(lock, link):
    """A lock's XLOC, in the game's 20 bytes."""
    return (struct.pack('<B3xIB3x', max(0, min(255, int(lock.get('level', 0)))), link(lock['key']) if lock.get('key') else 0, 4 if lock.get('leveled') else 0)
            + b'\0' * 8)


def encode_parent(parent, link):
    return struct.pack('<IB3x', link(parent['ref']), (1 if parent.get('opposite') else 0) | (2 if parent.get('popin') else 0))


def apply(subs, props, flags, link):
    """A ref's subrecords and flags with its settings laid over. New ones go where the game's records have them: before
    the size and the position, the rank straight after the owner."""
    out = list(subs)

    def put(tag, data):
        for k, (t, _d) in enumerate(out):
            if t == tag:
                if data is None:
                    del out[k]
                else:
                    out[k] = (t, data)
                return
        if data is not None:
            at = next((k for k, (t, _d) in enumerate(out) if t in ('XSCL', 'DATA')), len(out))
            out.insert(at, (tag, data))

    if 'owner' in props:
        put('XOWN', struct.pack('<I', link(props['owner'])) if props['owner'] else None)
        if not props['owner']:
            put('XRNK', None)
    if 'rank' in props:
        rank = props['rank']
        put('XRNK', None)
        if rank is not None and rank != '' and any(t == 'XOWN' for t, _d in out):
            k = next(k for k, (t, _d) in enumerate(out) if t == 'XOWN')
            out.insert(k + 1, ('XRNK', struct.pack('<i', int(rank))))
    if 'lock' in props:
        put('XLOC', encode_lock(props['lock'], link) if props['lock'] else None)
    if 'parent' in props:
        put('XESP', encode_parent(props['parent'], link) if props['parent'] else None)
    if 'disabled' in props:
        flags = flags | 0x800 if props['disabled'] else flags & ~0x800
    return out, flags


def links(props):
    """Every form key the settings name (for the plugin's masters)."""
    out = []
    if props.get('owner'):
        out.append(props['owner'])
    if props.get('lock') and props['lock'].get('key'):
        out.append(props['lock']['key'])
    if props.get('parent'):
        out.append(props['parent']['ref'])
    return out


def of_game(gd, fid):
    """A game ref's settings, in the form the op takes."""
    if fid not in gd.ref_cell:
        return {}
    i, rec = gd.cell_refs[gd.ref_cell[fid]][fid]
    f = gd.plugins[i].fields(rec)
    k = lambda v: gd.key(gd.to_global(i, v)) if v else ''
    out = {'disabled': bool(rec.flags & 0x800)}
    if 'XOWN' in f:
        out['owner'] = k(struct.unpack_from('<I', f['XOWN'])[0])
    if 'XRNK' in f:
        out['rank'] = struct.unpack_from('<i', f['XRNK'])[0]
    if 'XLOC' in f and len(f['XLOC']) >= 8:
        x = f['XLOC']
        out['lock'] = {'level': x[0], 'key': k(struct.unpack_from('<I', x, 4)[0]), 'leveled': len(x) > 8 and bool(x[8] & 4)}
    if 'XESP' in f and len(f['XESP']) >= 4:
        v = f['XESP']
        out['parent'] = {'ref': k(struct.unpack_from('<I', v)[0]), 'opposite': len(v) > 4 and bool(v[4] & 1), 'popin': len(v) > 4 and bool(v[4] & 2)}
    return out


def merged(gd, pr, ckey, rkey):
    """The settings of a placed thing as the mod leaves them."""
    out = of_game(gd, gd.from_key(rkey)) if not rkey.startswith('+') else {}
    ch = (pr.cells.get(ckey) or {'refs': {}})['refs'].get(rkey) if pr else None
    if ch and ch.get('props'):
        out.update(ch['props'])
    return out


def describe(gd, pr, key):
    """A form or ref key's name for people."""
    if not key:
        return ''
    if key.startswith('+'):
        rec = pr.records.get(key) if pr else None
        if rec:
            return next((s['value'] for s in rec['subs'] if s['tag'] == 'EDID'), key)
        for c in (pr.cells.values() if pr else ()):
            r = c['refs'].get(key)
            if r:
                return 'your %s' % describe(gd, pr, r.get('base', ''))
        return key
    try:
        fid = gd.from_key(key)
    except (ValueError, IndexError):
        return key
    if fid in gd.forms and fid not in gd.ref_cell:
        e, n = gd.edid(fid), tes4.zstr(gd.fields(fid).get('FULL', b''))
        return '%s (%s)' % (e, n) if n and n != e else e or key
    if fid in gd.ref_cell:
        i, rec = gd.cell_refs[gd.ref_cell[fid]][fid]
        f = gd.plugins[i].fields(rec)
        if 'EDID' in f:
            return tes4.zstr(f['EDID'])
        if 'NAME' in f:
            base = gd.to_global(i, struct.unpack_from('<I', f['NAME'])[0])
            return 'a %s' % gd.edid(base) if base in gd.forms else key
    return key


def get(ctx, path, q):
    gd, pr = ctx['gd'](), ctx['pr']()
    if path == 'props':
        p = merged(gd, pr, q['cell'], q['ref'])
        return {'props': p, 'levels': LOCK_LEVELS, 'owner_name': describe(gd, pr, p.get('owner', '')),
                'owner_is_faction': _is_faction(gd, pr, p.get('owner', '')),
                'key_name': describe(gd, pr, (p.get('lock') or {}).get('key', '')), 'parent_name': describe(gd, pr, (p.get('parent') or {}).get('ref', ''))}
    if path == 'groups':
        return {'groups': groups_read(pr)}
    raise KeyError(path)


def _is_faction(gd, pr, key):
    if not key:
        return False
    if key.startswith('+'):
        return (pr.records.get(key) or {}).get('type') == 'FACT'
    fid = gd.from_key(key)
    return fid in gd.forms and gd.forms[fid][1].tag == 'FACT'


def ops_for(pr, gd, cell, ref, props):
    """The edit that keeps a placed thing's settings: the ref that enables it must stay loaded, so it's made persistent."""
    ops = [{'op': 'props', 'cell': cell, 'ref': ref, 'props': props}]
    parent = props.get('parent')
    if parent and parent.get('ref'):
        pc = None
        if parent['ref'].startswith('+'):
            pc = next((ck for ck, c in pr.cells.items() if parent['ref'] in c['refs']), None)
        else:
            c = gd.ref_cell.get(gd.from_key(parent['ref']))
            pc = gd.key(c) if c is not None else None
        if pc:
            ops.append({'op': 'persist', 'cell': pc, 'ref': parent['ref']})
    return ops


# ---------- groups: things that select together, kept with the mod ----------

def _groups_file(pr):
    import os
    import project
    return os.path.join(project.PROJECTS_DIR, pr.name + ' groups.json')


def groups_read(pr):
    import json
    if not pr:
        return []
    try:
        with open(_groups_file(pr), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def groups_save(pr, groups):
    import json
    with open(_groups_file(pr), 'w', encoding='utf-8') as f:
        json.dump(groups, f, indent=1)
    return groups


def post(ctx, path, body):
    gd, pr = ctx['gd'](), ctx['pr']()
    if path == 'props':
        out = ctx['edit']('Settings of ' + describe(gd, pr, body['ref']), ops_for(pr, gd, body['cell'], body['ref'], body['props']))
        return out
    if path == 'groups':
        return {'groups': groups_save(pr, body['groups'])}
    raise KeyError(path)
