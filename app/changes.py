"""My changes: every change the open mod makes, by place and by kind, each with where it is, what it was, and the step
that puts it back. An opened plugin's own contents are listed apart: they are what it already was, not edits here."""
import os
import struct

import recdiff
import recordio
import schema
import tes4

LIMIT = 1500            # (rows in one group; the count is always the full one)
MOVED = 0.05


def _base_word(gd, pr, key):
    if not key:
        return ''
    if key.startswith('+'):
        rec = pr.records.get(key)
        return (recordio.field(rec, 'EDID') or key) if rec else key + ' (gone)'
    try:
        fid = gd.from_key(key)
        return gd.edid(fid) or key
    except (ValueError, KeyError):
        return key


def _num(vals):
    return ', '.join('%g' % round(v, 1) for v in vals)


def _game_ref(gd, key):
    """(base key, position and turn, scale, leads where) as the game has a placed thing; None for one it hasn't."""
    try:
        fid = gd.from_key(key)
    except ValueError:
        return None
    cell = gd.ref_cell.get(fid)
    e = gd.cell_refs.get(cell, {}).get(fid) if cell is not None else None
    if not e:
        return None
    i, f = gd.ref_fields(e)
    base = gd.key(gd.to_global(i, struct.unpack_from('<I', f['NAME'])[0])) if len(f.get('NAME', b'')) == 4 else None
    p = list(struct.unpack_from('<6f', f['DATA'])) if len(f.get('DATA', b'')) >= 24 else None
    s = struct.unpack_from('<f', f['XSCL'])[0] if len(f.get('XSCL', b'')) == 4 else 1.0
    return {'base': base, 'p': p, 's': s}


def ref_row(gd, pr, ckey, rkey, r):
    """One placed thing's change in words."""
    old = None if rkey.startswith('+') else _game_ref(gd, rkey)
    base = r.get('base') or (old or {}).get('base')
    name = _base_word(gd, pr, base)
    if rkey.startswith('+'):
        rows = [{'label': 'Placed', 'old': None, 'new': _num(r['p'][:3])}]
        kinds, undo = ['new'], {'op': 'remove', 'cell': ckey, 'ref': rkey}
        if r.get('s', 1.0) != 1.0:
            rows.append({'label': 'Size', 'old': None, 'new': '%g' % r['s']})
    else:
        kinds, rows = [], []
        undo = {'op': 'revert', 'cell': ckey, 'ref': rkey}
        if r.get('removed'):
            kinds.append('removed')
            rows.append({'label': 'Removed', 'old': _num(old['p'][:3]) if old and old['p'] else '', 'new': 'disabled, sunk out of sight'})
        if 'p' in r and old and old['p']:
            if any(abs(a - b) > MOVED for a, b in zip(r['p'][:3], old['p'][:3])):
                kinds.append('moved')
                rows.append({'label': 'Where', 'old': _num(old['p'][:3]), 'new': _num(r['p'][:3])})
            if any(abs(a - b) > 0.001 for a, b in zip(r['p'][3:], old['p'][3:])):
                kinds.append('turned')
                rows.append({'label': 'Turned', 'old': _num(old['p'][3:]), 'new': _num(r['p'][3:])})
        if 's' in r and old and abs(r['s'] - old['s']) > 0.0001:
            kinds.append('resized')
            rows.append({'label': 'Size', 'old': '%g' % old['s'], 'new': '%g' % r['s']})
        if r.get('base') and old and r['base'] != old['base']:
            kinds.append('swapped')
            rows.append({'label': 'Is now', 'old': _base_word(gd, pr, old['base']), 'new': name})
    if r.get('tel'):
        kinds.append('door')
        rows.append({'label': 'Leads to', 'old': None, 'new': _base_word(gd, pr, r['tel']['door']) + ' (' + r['tel']['door'] + ')'})
    if not kinds:
        kinds = ['changed']
    go = {'cell': ckey, 'ref': rkey}
    return {'key': rkey, 'name': name, 'kinds': kinds, 'diff': rows, 'undo': undo, 'go': go}


def _place_title(S, ckey):
    gd, pr = S.GD, S.PR
    if ckey.startswith('+'):
        rec = pr.records.get(ckey)
        return (recordio.field(rec, 'FULL') or recordio.field(rec, 'EDID') or ckey) if rec else ckey, False, None
    cell = gd.from_key(ckey)
    if cell in gd.ext_cells:
        xy = gd.cell_grid(cell)
        w = gd.edid(gd.ext_cells[cell])
        return '%s, cell %d, %d' % (w, xy[0], xy[1]) if xy else w, True, gd.key(gd.ext_cells[cell])
    f = gd.fields(cell)
    return tes4.zstr(f.get('FULL', b'')) or tes4.zstr(f.get('EDID', b'')) or ckey, False, None


def _outside_go(gd, ckey, world, p=None):
    if p is None:
        xy = gd.cell_grid(gd.from_key(ckey))
        p = [xy[0] * 4096 + 2048, xy[1] * 4096 + 2048, 0] if xy else [0, 0, 0]
    return {'world': world, 'p': list(p[:3])}


def everything(S):
    """{'places': [{title, rows}], 'kinds': [...], 'counts'...} for the open mod."""
    gd, pr = S.GD, S.PR
    places = []
    for ckey in sorted(set(pr.cells) | set(pr.land) | set(pr.water) | set(pr.navmesh)):
        if ckey.startswith('+') and ckey not in pr.records:
            continue
        title, outside, world = _place_title(S, ckey)
        rows = []
        for rkey, r in sorted((pr.cells.get(ckey) or {'refs': {}})['refs'].items()):
            row = ref_row(gd, pr, ckey, rkey, r)
            if outside:
                p = r.get('p') or (_game_ref(gd, rkey) or {}).get('p') or None
                row['go'] = dict(_outside_go(gd, ckey, world, p), ref=rkey)
            rows.append(row)
        here = _outside_go(gd, ckey, world) if outside else {'cell': ckey}
        if ckey in pr.land:
            rows.append({'key': ckey, 'name': 'The ground', 'kinds': ['ground'], 'diff': [], 'undo': {'op': 'land_revert', 'cell': ckey}, 'go': here})
        if ckey in pr.water:
            h = pr.water[ckey]
            rows.append({'key': ckey, 'name': 'The water', 'kinds': ['water'], 'diff': [{'label': 'Level', 'old': None, 'new': 'the world\'s' if h is None else '%g' % h}],
                         'undo': {'op': 'water_revert', 'cell': ckey}, 'go': here})
        if ckey in pr.navmesh:
            rows.append({'key': ckey, 'name': 'The navmesh', 'kinds': ['navmesh'], 'diff': [{'label': 'Triangles', 'old': None, 'new': str(len(pr.navmesh[ckey]['tris']))}],
                         'undo': {'op': 'navmesh_revert', 'cell': ckey}, 'go': here})
        tally = {}
        for row in rows:
            for k in row['kinds']:
                tally[k] = tally.get(k, 0) + 1
        places.append({'key': ckey, 'title': title, 'own': ckey.startswith('+'), 'outside': outside, 'count': len(rows), 'tally': tally,
                       'rows': rows[:LIMIT], 'go': here})
    places.sort(key=lambda p: (not p['own'], p['outside'], p['title'].lower()))
    kinds = {}
    for key, rec in sorted(pr.records.items()):
        word = schema.TYPES[rec['type']][0] if rec['type'] in schema.TYPES else rec['type']
        new = key.startswith('+')
        row = {'key': key, 'name': recordio.field(rec, 'FULL') or recordio.field(rec, 'EDID') or key, 'edid': recordio.field(rec, 'EDID'),
               'kinds': ['new' if new else 'changed'], 'undo': {'op': 'record_revert', 'key': key}, 'go': {'record': key}, 'can_diff': not new}
        if rec['type'] == 'CELL':
            row['go'] = {'cell': key}
        kinds.setdefault(word, []).append(row)
    records = [{'title': w, 'count': len(r), 'rows': r[:LIMIT]} for w, r in sorted(kinds.items())]
    dropped = [{'key': k, 'name': _base_word(gd, pr, k), 'kinds': ['left out'], 'undo': {'op': 'drop_revert', 'key': k},
                'go': {'record': k}} for k in pr.drop]
    return {'plugin': pr.plugin, 'opened': bool(pr.source), 'places': places, 'records': records, 'dropped': dropped, 'total': pr.count()}


def _decoded_lines(rec, word):
    out = []
    for s in rec['subs']:
        label = s.get('label') or s['tag']
        k = s['kind']
        if k == 'z':
            out.append((label, s['value']))
        elif k == 'F':
            out.append((label, word(s['value']) if s['value'] else 'nothing'))
        elif k == 'F*':
            out.append((label, ', '.join(word(v) if v else 'nothing' for v in s['value'])))
        elif k == 'struct':
            parts = []
            for f in s['fields']:
                if 'name' in f:
                    v = f['value']
                    v = (word(v) if v else 'nothing') if f.get('code') == 'F' else '%g' % round(v, 4) if isinstance(v, float) else v
                    parts.append('%s %s' % (f['name'], v))
            out.append((label, ', '.join(parts) or ' '))
        else:
            out.append((label, '(%d bytes, %s)' % (len(s['value']) // 2, s['value'][:24] + ('…' if len(s['value']) > 24 else ''))))
    return out


def record_diff(S, key):
    """How a record of the mod differs from the game's."""
    gd, pr = S.GD, S.PR
    word = lambda k: _base_word(gd, pr, k)
    mine = pr.records.get(key)
    if key.startswith('+') or not mine:
        return {'key': key, 'changes': [{'label': a, 'old': None, 'new': b} for a, b in _decoded_lines(mine, word)] if mine else []}
    return {'key': key, 'changes': recdiff.diff(_decoded_lines(recordio.load(gd, gd.from_key(key)), word), _decoded_lines(mine, word))}


# ---------- what an opened plugin already holds ----------

def plugin_contents(S):
    """By kind: what the opened plugin itself adds and what it changes of the game's."""
    pr = S.PR
    if not pr.source:
        return {'kinds': []}
    pf = tes4.PluginFile(pr.source_path())
    try:
        own = len(pf.header['masters'])
        kinds = {}
        for rec, _g in pf.walk():
            k = kinds.setdefault(rec.tag, {'type': rec.tag, 'new': 0, 'changed': 0, 'rows': []})
            is_new = rec.formid >> 24 >= own
            k['new' if is_new else 'changed'] += 1
            if len(k['rows']) < 300 and rec.tag not in ('LAND', 'NAVM'):
                m = pf.header['masters']
                key = '%s:%06X' % (m[rec.formid >> 24] if not is_new else os.path.basename(pf.path), rec.formid & 0xFFFFFF)
                edid = next((tes4.zstr(d) for t, d in tes4.iter_subrecords(pf.data(rec)) if t == 'EDID'), '') if rec.tag not in ('REFR', 'ACHR', 'ACRE') else ''
                k['rows'].append({'key': key, 'edid': edid, 'new': is_new})
    finally:
        pf.close()
    out = []
    for t, k in sorted(kinds.items()):
        k['title'] = schema.TYPES[t][0] if t in schema.TYPES else t
        out.append(k)
    return {'kinds': out}


def plugin_diff(S, key):
    """One record of the opened plugin against the game's copy."""
    import health
    gd, pr = S.GD, S.PR
    scan = health.Scan(gd, pr.source_path(), pr)
    try:
        name, low = key.rsplit(':', 1)
        lows = [m.lower() for m in scan.masters]
        if name.lower() not in lows:
            return {'key': key, 'new': True, 'changes': []}
        v = (lows.index(name.lower()) << 24) | int(low, 16)
        rec = None
        for r, _g in scan.pf.walk():
            if r.formid == v:
                rec = r
                break
        if rec is None:
            return {'key': key, 'changes': []}
        e = scan._earlier([v]).get(v)
        word = lambda p: (lambda x: recdiff.link_text(p, x))
        now = recdiff.lines(rec.tag, scan.subs(rec), word(scan.pf))
        if not e:
            return {'key': key, 'changes': [{'label': a, 'old': None, 'new': b} for a, b in now]}
        pf, orig = e
        was = recdiff.lines(orig.tag, list(tes4.iter_subrecords(pf.data(orig))), word(pf))
        return {'key': key, 'changes': recdiff.diff(was, now)}
    finally:
        scan.close()
