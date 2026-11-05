"""Records as a mod keeps them: decoded by the schema, form links as lasting keys ('FalloutNV.esm:00ABCD'), the parts no
layout reads kept as raw bytes (with the file they came from, whose numbering those bytes still use).

    {'type': 'WEAP', 'flags': 0, 'src': 'FalloutNV.esm', 'subs': [decoded subrecord, ...]}"""
import struct

import schema
import tes4


def _keys(gd, i, rtype, s):
    """a decoded subrecord's form links, from plugin i's numbering to keys"""
    k = lambda v: gd.key(gd.to_global(i, v)) if v else ''
    if s['kind'] == 'F':
        s['value'] = k(s['value'])
    elif s['kind'] == 'F*':
        s['value'] = [k(v) for v in s['value']]
    elif s['kind'] == 'struct':
        for f in s['fields']:
            if f.get('code') == 'F':
                f['value'] = k(f['value'])
    return s


def load(gd, fid):
    """The game's record for a form, as a mod keeps it."""
    i, rec = gd.source(fid)
    subs = list(tes4.iter_subrecords(gd.plugins[i].data(rec)))
    return {'type': rec.tag, 'flags': rec.flags & ~tes4.COMPRESSED, 'src': gd.names[i],
            'subs': [_keys(gd, i, rec.tag, s) for s in schema.decode_record(rec.tag, subs)]}


def to_bytes(rec, link):
    """The record's subrecord bytes; link(key) gives a key's form ID in the plugin being written."""
    out = []
    for s in rec['subs']:
        s2 = dict(s)
        if s['kind'] == 'F':
            s2['value'] = link(s['value']) if s['value'] else 0
        elif s['kind'] == 'F*':
            s2['value'] = [link(v) if v else 0 for v in s['value']]
        elif s['kind'] == 'struct':
            s2['fields'] = [dict(f, value=link(f['value']) if f['value'] else 0) if f.get('code') == 'F' else f for f in s['fields']]
        out.append((s['tag'], schema.encode_sub(rec['type'], s2)))
    return out


def links(rec):
    """Every form key a record links to (for masters, and for 'where it's used')."""
    out = []
    for s in rec['subs']:
        if s['kind'] == 'F' and s['value']:
            out.append(s['value'])
        elif s['kind'] == 'F*':
            out += [v for v in s['value'] if v]
        elif s['kind'] == 'struct':
            out += [f['value'] for f in s['fields'] if f.get('code') == 'F' and f['value']]
    return out


def field(rec, tag):
    s = next((s for s in rec['subs'] if s['tag'] == tag), None)
    return s['value'] if s and s['kind'] in ('z', 'F') else ''


def set_field(rec, tag, value, kind='z', label=None):
    for s in rec['subs']:
        if s['tag'] == tag:
            s['value'] = value
            return
    # (a new EDID goes first, as the game's records have it)
    s = {'tag': tag, 'label': label or tag, 'kind': kind, 'value': value}
    if tag == 'EDID':
        rec['subs'].insert(0, s)
    else:
        rec['subs'].append(s)
