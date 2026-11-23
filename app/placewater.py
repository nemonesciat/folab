"""Water in places (interior cells). A place's record says whether it has water (DATA flag 0x02) and how high it stands
(XCLW). The game draws none of it unless a water plane is placed, but an actor below that height is swimming: no running,
swim speeds, the air meter. A place copied from one of the game's for its light and sound (townbuild's ways in, the hotel
floors, the ship and flotilla insides, the Kit tab's new place) took that game place's water with it: 108 of Waikiki's
houses, works places and its cave were ~6,700 under water copied from the Tops' penthouse and the like, and the player
could only walk in them (22 Nov 2026).

make_dry: the copy's water put far under everything (the height the dry ones already carry), flag kept as the game's.
under_water: the mod's own places whose water stands over their floor (health's 'under_water')."""
import recordio

DRY = -2147483648.0          # (the level the game's dry places with the flag carry, and FOLab's dry copies)
HAS_WATER = 0x02
INTERIOR = 0x01
OVER = 40.0                  # (water this far over the lowest thing in a place: ankle-deep and up)


def flags_of(rec):
    for s in rec.get('subs', []):
        if s.get('tag') == 'DATA' and s.get('fields'):
            for f in s['fields']:
                if f.get('name') == 'Flags':
                    return int(f.get('value') or 0)
    return 0


def height_of(rec):
    """XCLW, or None when the record has none."""
    for s in rec.get('subs', []):
        if s.get('tag') == 'XCLW' and s.get('fields'):
            for f in s['fields']:
                if f.get('name') == 'Height':
                    return float(f['value'])
    return None


def make_dry(rec):
    """rec (a CELL record about to be the mod's own place) with its water far under everything. In place; returns rec.
    A place with no water flag is left as it is; one with the flag and no XCLW gets one."""
    if not (flags_of(rec) & INTERIOR) or not (flags_of(rec) & HAS_WATER):
        return rec
    for s in rec['subs']:
        if s.get('tag') == 'XCLW' and s.get('fields'):
            for f in s['fields']:
                if f.get('name') == 'Height':
                    f['value'] = DRY
            return rec
    at = next((i + 1 for i, s in enumerate(rec['subs']) if s.get('tag') in ('XCLL', 'LTMP', 'LNAM', 'DATA')), len(rec['subs']))
    rec['subs'].insert(at, {'tag': 'XCLW', 'kind': 'struct', 'label': 'Water height',
                            'fields': [{'name': 'Height', 'code': 'f', 'value': DRY}]})
    return rec


def under_water(pr):
    """[(place key, editor ID, water height, lowest thing's z)] of the mod's own places whose water stands OVER or more
    above the lowest thing standing in them."""
    out = []
    for k, rec in pr.records.items():
        if rec.get('type') != 'CELL' or not k.startswith('+'):
            continue
        fl = flags_of(rec)
        if not (fl & INTERIOR) or not (fl & HAS_WATER):
            continue
        h = height_of(rec)
        if h is None:
            continue
        zs = [r['p'][2] for r in ((pr.cells.get(k) or {}).get('refs') or {}).values() if r.get('p') and not r.get('removed')]
        if zs and h > min(zs) + OVER:
            out.append((k, recordio.field(rec, 'EDID') or k, h, min(zs)))
    return out


def dry_ops(pr, keys):
    """'record' ops putting these places' water far under them."""
    import copy
    return [{'op': 'record', 'key': k, 'record': make_dry(copy.deepcopy(pr.records[k]))} for k in keys]
