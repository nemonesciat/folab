"""A record's contents in words, and the difference between two copies of it. Links are spelled by their file
('FalloutNV.esm:00ABCD'), so copies numbered differently by their plugins compare as the same thing."""
import difflib
import os
import struct

import formlinks
import schema
import tes4


def own_name(pf):
    return os.path.basename(pf.path)


def link_text(pf, v):
    m = pf.header['masters']
    return '%s:%06X' % (m[v >> 24] if v >> 24 < len(m) else own_name(pf), v & 0xFFFFFF)


def normal(pf, rec):
    """A record's subrecords with every link's number made the same whichever plugin wrote it, for comparing."""
    subs = list(tes4.iter_subrecords(pf.data(rec)))
    return spelled(pf, rec.tag, subs)


def spelled(pf, tag, subs):
    masters = [m.lower() for m in pf.header['masters']]
    me = own_name(pf).lower()
    own = len(masters)
    table = _names

    def spell(v):
        name = masters[v >> 24] if v >> 24 < own else me
        return (table.setdefault(name, len(table) + 1) << 24) | (v & 0xFFFFFF)
    return formlinks.repoint(tag, subs, own, spell)[0]


_names = {}


def lines(tag, subs, text_link):
    """[(label, text)] for a record's subrecords. text_link(v): how a form link reads."""
    out = []
    for s in schema.decode_record(tag, subs):
        label = s.get('label') or s['tag']
        k = s['kind']
        if k == 'z':
            out.append((label, s['value']))
        elif k == 'F':
            out.append((label, text_link(s['value']) if s['value'] else 'nothing'))
        elif k == 'F*':
            out.append((label, ', '.join(text_link(v) if v else 'nothing' for v in s['value'])))
        elif k == 'struct':
            parts = []
            for f in s['fields']:
                if 'name' not in f:
                    continue
                v = f['value']
                if f.get('code') == 'F':
                    v = text_link(v) if v else 'nothing'
                elif isinstance(v, float):
                    v = '%g' % round(v, 4)
                parts.append('%s %s' % (f['name'], v))
            out.append((label, ', '.join(parts) or ' '))
        else:
            out.append((label, _raw(tag, s, text_link)))
    return out


def _raw(tag, s, text_link):
    """What a part no layout reads can say for itself."""
    d = bytes.fromhex(s['value'])
    t = s['tag']
    if t in ('DATA', 'XSCL') and tag in formlinks.PLACED_TAGS and len(d) in (4, 24):
        v = struct.unpack('<%df' % (len(d) // 4), d)
        return ' '.join('%g' % round(x, 3) for x in v)
    if t in formlinks.PLACED and len(d) >= 4:
        where = formlinks.PLACED[t]
        o = 0 if where == 'all' else where[0]
        if o + 4 <= len(d):
            return text_link(struct.unpack_from('<I', d, o)[0])
    if d.endswith(b'\0') and len(d) < 200 and all(32 <= c < 127 for c in d[:-1]):
        return d[:-1].decode('ascii')
    return '(%d bytes, %s)' % (len(d), d[:12].hex() + ('…' if len(d) > 12 else ''))


def diff(old, new):
    """[{'label', 'old', 'new'}] where two lists of (label, text) differ: old None when added, new None when gone."""
    a = ['%s: %s' % x for x in old]
    b = ['%s: %s' % x for x in new]
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == 'equal':
            continue
        n = max(i2 - i1, j2 - j1)
        for k in range(n):
            o = old[i1 + k] if i1 + k < i2 else None
            w = new[j1 + k] if j1 + k < j2 else None
            out.append({'label': (o or w)[0], 'old': o[1] if o else None, 'new': w[1] if w else None})
    return out
