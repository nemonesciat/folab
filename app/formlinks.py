"""Every place a record holds a form link, down to the byte: the layouts in schema.py, and what they leave raw (placed
things, navmeshes, conditions, package targets, alternate textures...). The health check follows these to find dead
links; merging and growing a plugin's masters re-point them.

Worked out from the file format and checked against the game: `py -3 formlinks.py` follows every link of every
record of the official files and prints what doesn't lead anywhere, and every 4 bytes outside these places that look
like a link. A few fields hold a number or a link depending on something else ('maybe' below): those count as links
only when the value could be one."""
import json
import os
import struct

import schema
import tes4

BUILTIN_LIMIT = 0x800   # object IDs below this are the engine's own (the player, markers)
SCHEMA_TYPES = set(schema.TYPES)

PLACED = {'NAME': [0], 'XEZN': [0], 'XTEL': [0], 'WMI1': [0], 'XTRG': [0], 'INAM': [0], 'XRDO': [12], 'XOWN': [0],
          'XLOC': [4], 'XAMT': [0], 'XPWR': [0], 'XLTW': [0], 'XDCR': [0], 'XLKR': [0], 'XAPR': [0], 'XESP': [0], 'XEMI': [0],
          'XMBR': [0], 'XNDP': [0], 'XMRC': [0], 'CNAM': [0], 'SCRO': [0], 'XPOD': 'all', 'XLRM': 'all', 'XORD': 'all'}
WEATHER_IMAGESPACE = {bytes([i]).decode('latin-1') + 'IAD': [0] for i in range(0, 32)}
WEATHER_IMAGESPACE.update({chr(0x40 + i) + 'IAD': [0] for i in range(0, 32)})
# types the layouts don't cover (and a few fields of those they do), as (tag: offsets, or 'all' for a list of links)
TABLE = {
    'CELL': {'XCLR': 'all', 'XCIM': [0], 'XEZN': [0], 'XCCM': [0], 'XCWT': [0], 'XOWN': [0], 'XCAS': [0], 'XCMO': [0], 'LTMP': [0]},
    'WRLD': {'XEZN': [0], 'WNAM': [0], 'CNAM': [0], 'NAM2': [0], 'NAM3': [0], 'INAM': [0], 'ZNAM': [0], 'IMPS': [4, 8]},
    'ALOC': {'GNAM': [0], 'HNAM': [0], 'LNAM': [0], 'RNAM': [0], 'XNAM': [0], 'YNAM': [0], 'ZNAM': [0]},
    'ARMO': {'TNAM': [0]},
    'BPTD': {'BPND': [12, 16, 32, 36, 68, 72], 'RAGA': [0]},
    'CSNO': {'DATA': [44, 48]},
    'DEHY': {'DATA': [4]}, 'HUNG': {'DATA': [4]}, 'SLPD': {'DATA': [4]}, 'RADS': {'DATA': [4]},
    'IMAD': {'RDSD': [0]},
    'LAND': {'ATXT': [0], 'BTXT': [0], 'VTEX': 'all'},
    'MESG': {'INAM': [0], 'QNAM': [0], 'SCRO': [0]},
    'MSET': {'HNAM': [0], 'INAM': [0]},
    'PACK': {'PKDD': [4]},
    'RGDL': {'XNAM': [0], 'TNAM': [0]},
    'SCOL': {'ONAM': [0]},
    'SCPT': {'SCRO': [0]},
    'WATR': {'SNAM': [0], 'XNAM': [0], 'TNAM': [0]},
    'WTHR': dict(WEATHER_IMAGESPACE, SNAM=[0]),
    'TES4': {'ONAM': 'all'},
}
for _t in ('REFR', 'ACHR', 'ACRE', 'PGRE', 'PMIS', 'PBEA', 'PFLA', 'PCBE'):
    TABLE[_t] = PLACED
ALT_TEXTURES = {'MODS', 'MO2S', 'MO3S', 'MO4S', 'DMDS'}
# (which of a condition's parameters are links, by the function it calls; codes in the table start at 4096)
_cond_params = None


def _conditions():
    global _cond_params
    if _cond_params is None:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scriptfuncs.json'), encoding='utf-8') as f:
            t = json.load(f)
        _cond_params = {e['code'] - 4096: [bool(t['param_kinds'][p[0]][1]) for p in e['params']] for e in t['script']}
    return _cond_params


def _condition(d):
    """The links in a CTDA: a global, its parameters, its Run on reference."""
    out = []
    if len(d) >= 8 and d[0] & 4:            # (compared against a global: the value is its form)
        out.append(4)
    if len(d) >= 28:
        out.append(24)
    if len(d) >= 12:
        kinds = _conditions().get(struct.unpack_from('<H', d, 8)[0], ())
        for i, is_form in enumerate(kinds[:2]):
            if is_form and 16 + 4 * i <= len(d):
                out.append(12 + 4 * i)
    return out


def _alt_textures(d):
    """Alternate textures: a count, then each one's name (length first), its texture set, and a number."""
    out = []
    if len(d) < 4:
        return out
    n, p = struct.unpack_from('<I', d)[0], 4
    for _ in range(n):
        if p + 4 > len(d):
            return []
        size = struct.unpack_from('<I', d, p)[0]
        p += 4 + size
        if p + 8 > len(d):
            return []
        out.append(p)
        p += 8
    return out if p == len(d) else []


def _nvci(d):
    out = [0]
    p = 4
    for _ in range(3):
        if p + 4 > len(d):
            return out
        n = struct.unpack_from('<I', d, p)[0]
        out += [p + 4 + 4 * k for k in range(n)]
        p += 4 + 4 * n
    return out


def locate(tag, subs):
    """(links, maybes): lists of (subrecord index, byte offset). A 'maybe' is a link only if the value could be one."""
    sure = set(schema.record_form_offsets(tag, subs)) if tag in SCHEMA_TYPES else set()
    maybe = []
    table = TABLE.get(tag, {})
    late = False
    after = schema.AFTER.get(tag, (None, ()))[0]
    ptype = target = None
    for n, (st, d) in enumerate(subs):
        if st == after:
            late = True
        w = table.get(st)
        if w == 'all':
            sure.update((n, o) for o in range(0, len(d) - 3, 4))
        elif w:
            if tag in PLACED_TAGS and st == 'CNAM' and len(d) != 4:
                continue
            sure.update((n, o) for o in w if o + 4 <= len(d))
        if st == 'CTDA':
            sure.update((n, o) for o in _condition(d))
        elif st in ALT_TEXTURES:
            sure.update((n, o) for o in _alt_textures(d))
        elif st == 'COED' and len(d) >= 8:
            maybe.append((n, 4))            # (owned by a character: a global; by a faction: a rank)
        elif tag == 'NAVM':
            if st == 'DATA' and len(d) >= 4:
                sure.add((n, 0))
            elif st == 'NVDP':
                sure.update((n, o) for o in range(0, len(d) - 7, 8))
            elif st == 'NVEX':
                sure.update((n, o) for o in range(4, len(d) - 3, 10))
        elif tag == 'NAVI':
            if st == 'NVMI' and len(d) >= 12:
                sure.update([(n, 4), (n, 8)])
            elif st == 'NVCI':
                sure.update((n, o) for o in _nvci(d))
        elif tag == 'PACK' and st in ('PLDT', 'PLD2') and len(d) >= 8:
            if struct.unpack_from('<i', d)[0] in (0, 1, 4):      # (near a ref, in a cell, near an object of a kind)
                sure.add((n, 4))
        elif tag == 'PACK' and st in ('PTDT', 'PTD2') and len(d) >= 8:
            if struct.unpack_from('<i', d)[0] in (0, 1):         # (a ref, an object)
                sure.add((n, 4))
        elif tag == 'PERK':
            if st == 'EPFT' and d:
                ptype = d[0]
            elif st == 'EPFD' and ptype == 3 and len(d) == 4:    # (a levelled item)
                sure.add((n, 0))
            elif st == 'EPFD' and ptype == 5 and len(d) == 4:
                maybe.append((n, 0))
            elif st == 'DATA' and late and len(d) in (4, 8):     # (an effect: a spell, or a quest and stage)
                sure.add((n, 0))
        elif tag == 'REFR' and st == 'TNAM' and len(d) == 4:     # (a patrol's topic: a map marker's is 2 bytes)
            sure.add((n, 0))
        elif tag in PLACED_TAGS and st == 'TNAM' and len(d) == 4:
            sure.add((n, 0))
        elif tag == 'NOTE':
            if st == 'DATA' and d:
                ptype = d[0]
            elif st == 'TNAM' and ptype == 3 and len(d) == 4:    # (a voice note: its topic; else TNAM is the text)
                sure.add((n, 0))
    return sorted(sure), maybe


PLACED_TAGS = {'REFR', 'ACHR', 'ACRE', 'PGRE', 'PMIS', 'PBEA', 'PFLA', 'PCBE'}
LABEL_IS_FORM = {tes4.G_WORLD_CHILDREN, tes4.G_CELL_CHILDREN, tes4.G_TOPIC_CHILDREN, tes4.G_CELL_PERSISTENT,
                 tes4.G_CELL_TEMPORARY, tes4.G_CELL_VWD}


def could_be_link(v, own_index):
    return v and (v >> 24) <= own_index and (v & 0xFFFFFF) >= BUILTIN_LIMIT


def values(tag, subs, own_index):
    """(subrecord index, offset, value) of every non-empty link in a record."""
    sure, maybe = locate(tag, subs)
    out = []
    for n, o in sure:
        v = struct.unpack_from('<I', subs[n][1], o)[0]
        if v:
            out.append((n, o, v))
    for n, o in maybe:
        v = struct.unpack_from('<I', subs[n][1], o)[0]
        if could_be_link(v, own_index):
            out.append((n, o, v))
    return out


def repoint(tag, subs, own_index, fn):
    """A record's subrecords with every link put through fn; (the new list, whether anything changed)."""
    hits = values(tag, subs, own_index)
    if not hits:
        return subs, False
    changed = {}
    for n, o, v in hits:
        nv = fn(v)
        if nv != v:
            changed.setdefault(n, bytearray(subs[n][1]))
            struct.pack_into('<I', changed[n], o, nv)
    if not changed:
        return subs, False
    return [(t, bytes(changed[n]) if n in changed else d) for n, (t, d) in enumerate(subs)], True


def sweep(gd):
    """The check: for each kind of link, how many lead nowhere; for all other 4 bytes, how many look like links."""
    import collections
    dead = collections.Counter()
    good = collections.Counter()
    looks = collections.defaultdict(lambda: [0, 0])
    for i, p in enumerate(gd.plugins):
        own = len(p.header['masters'])
        for rec, _path in p.walk():
            subs = list(tes4.iter_subrecords(p.data(rec)))
            hits = values(rec.tag, subs, own)
            at = {(n, o) for n, o, _v in hits}
            for n, o, v in hits:
                if v & 0xFFFFFF < BUILTIN_LIMIT:
                    continue
                k = (rec.tag, subs[n][0], o if o < 80 else 80)
                (good if gd.to_global(i, v) in gd.forms else dead)[k] += 1
            for n, (st, d) in enumerate(subs):
                if st in ('SCDA', 'SCTX', 'OFST', 'VHGT', 'VNML', 'VCLR', 'VTXT', 'MODT', 'FGGS', 'FGGA', 'FGTS', 'NVVX', 'NVTR', 'NVGD', 'NVCA',
                          'RCLR', 'NIFT', 'DMDT', 'MO2T', 'MO3T', 'MO4T', 'NVEX', 'RDMP', 'RPLD', 'XPTL', 'XOCP', 'XPRM', 'DATA' if rec.tag in PLACED_TAGS else ''):
                    continue
                if len(d) >= 4 and (len(d) % 4 == 0 or len(d) < 16) and not d.endswith(b'\0\0\0\0\0'):
                    for o in range(0, min(len(d), 200) - 3, 4):
                        if (n, o) in at:
                            continue
                        v = struct.unpack_from('<I', d, o)[0]
                        if v and (v >> 24) <= own and v & 0xFFFFFF >= BUILTIN_LIMIT:
                            s = looks[(rec.tag, st, o)]
                            s[0] += 1
                            s[1] += gd.to_global(i, v) in gd.forms
    return dead, good, looks


if __name__ == '__main__':
    import gamedata
    gd = gamedata.GameData()
    dead, good, looks = sweep(gd)
    print('links that lead nowhere, by field (and how many lead somewhere):')
    for k, n in dead.most_common():
        print(' ', k, n, 'of', n + good[k])
    print('links followed:', sum(good.values()), 'dead:', sum(dead.values()))
    print('not known as links, but look like them:')
    for k, (n, hit) in sorted(looks.items()):
        if hit >= 2 and hit / n > 0.6:
            print(' ', k, hit, 'of', n)
