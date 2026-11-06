"""Changing a plugin's list of masters. The high byte of every form ID in a plugin is a place in that list (and one past
its end means the plugin itself), so a change to the list means re-pointing every link in the file: every record, every
group that names a form, the header's list of what it overrides. formlinks.py knows where they all are.

A record with nothing to re-point keeps its bytes (compressed ones stay compressed)."""
import struct

import formlinks
import plugintree
import tes4

# Types with no links in them, or none that aren't in formlinks (checked by its sweep of the game's files)
LINK_FREE = {'AVIF', 'CHIP', 'CSTY', 'DEBR', 'EFSH', 'GMST', 'IMGS', 'LGTM', 'LSCT', 'MICN', 'MUSC', 'RCCT', 'SOUN', 'TREE'}
RAW_CAUTION = 'FOLab doesn\'t know this kind of record, so links inside it wouldn\'t be followed'


def sub(tag, data):
    if len(data) > 0xFFFF:
        return struct.pack('<4sHI', b'XXXX', 4, len(data)) + struct.pack('<4sH', tag.encode(), 0) + data
    return struct.pack('<4sH', tag.encode(), len(data)) + data


def join(subs):
    return b''.join(sub(t, d) for t, d in subs)


def unknown_types(tree):
    """Record types in a plugin whose links FOLab can't vouch for."""
    return sorted({r.tag for r, _p, _x in tree.records() if not known_type(r.tag)})


def known_type(tag):
    return tag in formlinks.SCHEMA_TYPES or tag in formlinks.TABLE or tag in LINK_FREE or tag in ('NAVM', 'NAVI')


def remap(tree, own_index, fn):
    """Every form ID in a plugin's tree (records, groups, the header's list) through fn."""
    def walk(kids):
        for k in kids:
            if isinstance(k, plugintree.Group):
                if k.gtype in formlinks.LABEL_IS_FORM and k.label:
                    k.label = fn(k.label)
                walk(k.kids)
            else:
                subs = list(tes4.iter_subrecords(k.data()))
                new, changed = formlinks.repoint(k.tag, subs, own_index, fn)
                nid = fn(k.formid)
                if changed:
                    k.formid = nid
                    k.set_data(join(new), k.flags)
                else:
                    k.formid = nid
    walk(tree.tops)
    subs = list(tes4.iter_subrecords(tree.header.raw))
    new, changed = formlinks.repoint('TES4', subs, own_index, fn)
    if changed:
        tree.header.set_data(join(new), tree.header.flags)


def mapper(old_masters, own_name, new_masters, own_low=None, renamed=None):
    """fn(form ID as a plugin with old_masters writes it) -> the same form with new_masters. own_low: new object IDs for
    the plugin's own forms; renamed: {lower file name: (its forms now in the plugin itself) new object IDs or None}."""
    index = {m.lower(): i for i, m in enumerate(new_masters)}
    new_own = len(new_masters)
    old = [m.lower() for m in old_masters]
    me = own_name.lower()
    table = {}
    for i, name in enumerate(old + [me]):
        if name == me:
            table[i] = (new_own, own_low)
        elif renamed and name in renamed:
            table[i] = (new_own, renamed[name])
        elif name in index:
            table[i] = (index[name], None)
        else:
            raise ValueError('%s isn\'t in the new list of masters.' % name)

    def fn(v):
        e = table.get(v >> 24)
        if e is None:
            return v                # (points past the end of its masters: nothing to keep it right against)
        low = v & 0xFFFFFF
        if e[1]:
            low = e[1].get(low, low)
        return (e[0] << 24) | low
    return fn


def masters_of(tree):
    return [tes4.zstr(d) for t, d in tes4.iter_subrecords(tree.header.raw) if t == 'MAST']


def set_masters(tree, masters):
    """The header's list of masters (each followed by its DATA, as the game writes them), just where the old one was."""
    subs = list(tes4.iter_subrecords(tree.header.raw))
    out, at, skip = [], None, False
    for t, d in subs:
        if t == 'MAST':
            if at is None:
                at = len(out)
            skip = True
            continue
        if t == 'DATA' and skip:
            skip = False
            continue
        skip = False
        out.append((t, d))
    if at is None:
        at = next((n for n, (t, _d) in enumerate(out) if t not in ('HEDR', 'OFST', 'DELE', 'CNAM', 'SNAM')), len(out))
    mast = []
    for m in masters:
        mast += [('MAST', m.encode('cp1252', 'replace') + b'\0'), ('DATA', b'\0' * 8)]
    tree.header.set_data(join(out[:at] + mast + out[at:]), tree.header.flags)


def grow(tree, own_name, new_masters):
    """A plugin's masters replaced by new_masters, every link re-pointed. Returns False when they're the same."""
    old = masters_of(tree)
    if [m.lower() for m in old] == [m.lower() for m in new_masters]:
        return False
    remap(tree, len(old), mapper(old, own_name, new_masters))
    set_masters(tree, new_masters)
    return True


def used_masters(tree):
    """Which of a plugin's masters anything in it uses: [bool]; None when a kind of record in it can't be vouched for."""
    if unknown_types(tree):
        return None
    masters = masters_of(tree)
    own = len(masters)
    used = [False] * own

    def mark(v):
        if v >> 24 < own:
            used[v >> 24] = True
    def walk(kids):
        for k in kids:
            if isinstance(k, plugintree.Group):
                if k.gtype in formlinks.LABEL_IS_FORM and k.label:
                    mark(k.label)
                walk(k.kids)
            else:
                mark(k.formid)
                for _n, _o, v in formlinks.values(k.tag, list(tes4.iter_subrecords(k.data())), own):
                    mark(v)
    walk(tree.tops)
    return used
