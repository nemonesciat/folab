"""Waikiki's people dressed for the island, not the Mojave: the game's spawns a mod placed swapped for people of the mod's
own (NPC_), each a copy of the game's spawn with its own name and clothes. One Undo a kind (`KINDS`).

The user, 20 Nov 2026: "prospectors and raiders need to become surfers and pirates ... more hawaiian shirts and sunglasses";
then: wastelanders are pirates too, and no Jackals, Vipers, raiders or Fiends: the island's baddies are pirates. What a
surfer is (a gang?) is for later: for now prospectors only dress as surfers.

How, as the game itself does it (its Viper and Prospector spawns are built so):
  - a spawn of the mod's own is a copy of the game's: the same template (looks, voice, levels, weapons, AI from the game),
    but its name, its base data and its inventory its own (template flags 0x80 and 0x100 cleared); a kind with a faction
    (pirates) also lists its own factions (0x04 cleared): every pirate the Fiends' factions, so they don't fight each other.
  - its inventory is the game template's (the first that gives the spawn its inventory), each clothing list in it
    (`_clothing`: a list or item that is only apparel) swapped for the kind's own lists: body, head, eyes (`DRESS`).
  - the shirts: FOLab's prints (garmentprint) on the game's Pre-War Spring outfit, a copy of its three meshes (worn,
    worn by a woman, lying on the ground) with the printed picture in place of the game's (library.retexture_mesh,
    nifwrite: only the texture paths differ), an ARMO copied from OutfitPrewarSpring with those models. Pirates' are
    painted over the game's worn picture with its worn normal map.
  - hats and glasses are the game's own (the Rattan Cowboy Hat for straw, Sunglasses, bandanas, head wraps).
  - each placed one outside (never in a place of the mod's own: the hotels' floors are the user's to decide) gets a 'swap'
    to the new base: same spot, same facing. No navmesh changes.

Records of the mod's own name each other by key ('+' and the mod's next ID in order: `_Keys`), so a kind's records and
swaps are one list of ops. The pictures and meshes go among the mod's own files when the ops are planned (as any piece's
files do); planning the same kind again finds them there by name and writes them again.

`py -3 app/peopledress.py [kind]` with FOLAB_HOME set says what it would do to the open Waikiki (nothing saved)."""
import json
import struct

import library
import recordio

# what each kind is made from, its name in game, its clothes ('look'), and the game template whose factions it takes
KINDS = {
    'surfers': {'from': ['VSpawnProspectorAll'], 'name': 'Surfer', 'look': 'surfer', 'factions_of': None},
    'pirates': {'from': ['LvlFiend2GunVarNV', 'LvlFiend2RifleVarNV', 'LvlFiend2MeleeVarNV', 'LvlRaider1GunVar', 'LvlRaider1MeleeVar',
                         'VViperGangSpawnGunA', 'VViperGangSpawnGunB', 'VJackalGangSpawnMale', 'VJackalGangSpawnFemale', 'LvlWastelander'],
                'name': 'Pirate', 'look': 'pirate', 'factions_of': 'Fiend2GunAAFTEMPLATENV'},
}
# prints: (style word, ground, flower, leaf); a look's shirts are painted on the clean picture, or the worn one
PRINTS = {
    'surfer': (False, [('Blue', (30, 70, 140), (225, 60, 70), (40, 120, 80)),
                       ('Red', (200, 60, 50), (250, 240, 225), (40, 110, 70)),
                       ('Cream', (235, 225, 200), (220, 90, 60), (60, 120, 90))]),
    'pirate': (True, [('Navy', (24, 34, 70), (214, 110, 50), (50, 90, 70)),
                      ('Black', (30, 26, 26), (190, 50, 45), (60, 80, 50)),
                      ('Maroon', (100, 30, 34), (225, 205, 170), (70, 90, 60))]),
}
# a look's clothes: list -> (chance none %, [(editor ID or '@shirts', count weight)])
DRESS = {
    'surfer': {'body': (0, [('@shirts', 1)]),
               'head': (45, [('CowboyHat04', 1)]),                                      # (Rattan Cowboy Hat: woven straw)
               'eyes': (35, [('GlassesShades', 1)])},
    'pirate': {'body': (0, [('@shirts', 3), ('ArmorLeather', 1)]),
               'head': (25, [('OutfitWastelandHat05', 2), ('HeadWrap01', 1), ('HeadWrap02', 1), ('HeadWrap03', 1), ('HeadWrap04', 1)]),
               'eyes': (75, [('GlassesShades', 1)])},
}
SHIRT_NAME = {'surfer': 'Hawaiian Shirt', 'pirate': 'Old Hawaiian Shirt'}
SEED = {'surfer': 1, 'pirate': 21}
OUTFIT = 'OutfitPrewarSpring'
USE_FACTIONS, USE_BASE, USE_INVENTORY = 0x04, 0x80, 0x100
BODY = 0x4


class _Keys:
    """The keys records of the mod's own will get, in the order their record_new ops come."""

    def __init__(self, pr):
        self.next = pr.next_id
        self.ops = []

    def add(self, rec):
        key = '+%06X' % self.next
        self.next += 1
        self.ops.append({'op': 'record_new', 'record': rec})
        return key


def _edids(gd, tags):
    out = {}
    for f, (_i, r) in gd.forms.items():
        if r.tag in tags:
            out.setdefault(gd.edid(f).lower(), f)
    return out


def _sub(rtype, tag, data):
    import schema
    return schema.decode_sub(rtype, tag, data)


def _entries(gd, fid):
    """A levelled list's entries (form IDs)."""
    rec = recordio.load(gd, fid)
    return [gd.from_key(next(f['value'] for f in s['fields'] if f.get('code') == 'F'))
            for s in rec['subs'] if s['tag'] == 'LVLO']


def _apparel(gd, fid, depth=0):
    """Every ARMO a form is or a levelled item gives, or None if it gives anything that isn't apparel."""
    tag = gd.forms[fid][1].tag if fid in gd.forms else None
    if tag == 'ARMO':
        return [fid]
    if tag != 'LVLI' or depth > 6:
        return None
    out = []
    for e in _entries(gd, fid):
        got = _apparel(gd, e, depth + 1)
        if got is None:
            return None
        out += got
    return out


def _slots(gd, fid):
    rec = recordio.load(gd, fid)
    s = next((s for s in rec['subs'] if s['tag'] == 'BMDT'), None)
    return next((f['value'] for f in s['fields'] if f.get('name') == 'Biped flags'), 0) if s else 0


def _acbs(rec):
    return next(s for s in rec['subs'] if s['tag'] == 'ACBS')


def _num(rec, tag, name):
    s = next((s for s in rec['subs'] if s['tag'] == tag), None)
    return next((f['value'] for f in s['fields'] if f.get('name') == name), 0) if s else 0


def _set(rec, tag, name, value):
    for f in next(s for s in rec['subs'] if s['tag'] == tag)['fields']:
        if f.get('name') == name:
            f['value'] = value


def inventory_source(gd, fid, depth=0):
    """The NPC_ a spawn takes its inventory from (its template followed through lists, the first that gives one)."""
    if depth > 8 or fid not in gd.forms:
        return None
    tag = gd.forms[fid][1].tag
    if tag == 'LVLN':
        for e in _entries(gd, fid):
            got = inventory_source(gd, e, depth + 1)
            if got:
                return got
        return None
    rec = recordio.load(gd, fid)
    tp = recordio.field(rec, 'TPLT')
    if tp and _num(rec, 'ACBS', 'Template flags') & USE_INVENTORY:
        got = inventory_source(gd, gd.from_key(tp), depth + 1)
        if got:
            return got
    return fid


def _clothing(gd, rec):
    """[(index in subs, 'body' | 'head')] of the CNTO entries that are only apparel."""
    out = []
    for n, s in enumerate(rec['subs']):
        if s['tag'] != 'CNTO':
            continue
        item = next(f['value'] for f in s['fields'] if f.get('name') == 'Item')
        arm = _apparel(gd, gd.from_key(item)) if item and not item.startswith('+') else None
        if arm:
            out.append((n, 'body' if any(_slots(gd, a) & BODY for a in arm) else 'head'))
    return out


def _lvli(gd, edid, chance, items):
    """A levelled item list of the mod's own: [(key, weight)] each once per weight, all at level 1."""
    subs = [_sub('LVLI', 'EDID', edid.encode() + b'\0'), _sub('LVLI', 'OBND', b'\0' * 12),
            _sub('LVLI', 'LVLD', bytes([chance])), _sub('LVLI', 'LVLF', bytes([3]))]   # (from all levels, each of a count)
    for key, weight in items:
        for _w in range(weight):
            s = _sub('LVLI', 'LVLO', struct.pack('<hHIhH', 1, 0, 0, 1, 0))
            for f in s['fields']:
                if f.get('code') == 'F':
                    f['value'] = key
            subs.append(s)
    return {'type': 'LVLI', 'flags': 0, 'src': '', 'subs': subs}


def _shirt_files(gd, pr, look):
    """{style: {'m': mesh, 'f': mesh, 'go': mesh}} of the look's printed outfits, among the mod's own files."""
    import garmentprint            # (numpy, PIL, scipy: the developer's Python, not FOLab.exe's; a build step for now)
    worn, styles = PRINTS[look]
    root = library.assets_dir(pr)
    masks = {g: garmentprint.cloth_mask(gd, g) for g in ('m', 'f')}
    out = {}
    for n, (word, ground, flower, leaf) in enumerate(styles):
        got = {}
        for g in ('m', 'f'):
            mesh, clean, worn_tex, normal, worn_normal = garmentprint.GARMENTS[g]
            pic = 'textures\\folab\\%s\\people\\%s_%s_%s.dds' % (library.slug(pr.name), look, word.lower(), g)
            im = garmentprint.paint(gd, g, (ground, flower, leaf), worn=worn, seed=SEED[look] + n, mask=masks[g])
            library._put(root, pic, garmentprint.dds_of(im))
            changes = {garmentprint.TEXTURES + clean: pic}
            if worn:
                changes[garmentprint.TEXTURES + normal] = garmentprint.TEXTURES + worn_normal
            got[g] = (garmentprint.FOLDER + mesh, changes)
            if g == 'm':
                got['go'] = (garmentprint.FOLDER + 'GO.NIF', changes)
        out[word] = {}
        for part, (mesh, changes) in got.items():
            stem = '%s_%s_%s' % (look, word.lower(), part)
            rel = 'meshes\\folab\\%s\\%s.nif' % (library.slug(pr.name), stem)
            import nifwrite
            data = gd.read_file(mesh)
            new = nifwrite.retexture(data, changes)
            wrong = nifwrite.prove(data, changes)
            if wrong:
                raise ValueError('%s: %s' % (stem, '; '.join(wrong)))
            library._put(root, rel, new)                # (the same name each time: planning again writes it again)
            out[word][part] = rel
    return out


def _shirt_record(gd, outfit_fid, edid, name, files):
    rec = recordio.load(gd, outfit_fid)
    rec['src'] = ''
    rec['copied_from'] = gd.key(outfit_fid)
    for tag, part in (('MODL', 'm'), ('MOD3', 'f'), ('MOD2', 'go')):
        for s in rec['subs']:
            if s['tag'] == tag:
                s['value'] = files[part][7:]                # (models are named from meshes\)
    # (texture hashes and alternate textures belong to the game's models)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('MODT', 'MO2T', 'MO3T', 'MO4T', 'MODS', 'MO2S', 'MO3S', 'MO4S')]
    recordio.set_field(rec, 'EDID', edid)
    recordio.set_field(rec, 'FULL', name)
    return rec


def plan(gd, pr, kind):
    """(ops, report) for one kind: its records first, then a swap for every one of its spawns the mod placed outside."""
    k = KINDS[kind]
    look = k['look']
    npcs = _edids(gd, ('NPC_',))
    items = _edids(gd, ('ARMO',))
    taken = {recordio.field(r, 'EDID').lower() for r in pr.records.values()}
    word = k['name']

    def edid(s):
        e = 'FOLab' + s
        if e.lower() in taken:
            raise ValueError('The mod already has %s: this kind looks done (Undo it first to make it again).' % e)
        taken.add(e.lower())
        return e

    keys = _Keys(pr)
    rep = {'kind': kind, 'records': {}, 'swapped': {}, 'inside_left': {}, 'files': {}}
    files = _shirt_files(gd, pr, look)
    rep['files'] = files
    shirts = []
    for style, f in files.items():
        rec = _shirt_record(gd, items[OUTFIT.lower()], edid('%s%s' % (SHIRT_NAME[look].replace(' ', ''), style)), '%s (%s)' % (SHIRT_NAME[look], style.lower()), f)
        shirts.append(keys.add(rec))
    lists = {}
    for part, (chance, rows) in DRESS[look].items():
        got = []
        for e, weight in rows:
            if e == '@shirts':
                got += [(s, weight) for s in shirts]
            else:
                got.append((gd.key(items[e.lower()]), weight))
        lists[part] = keys.add(_lvli(gd, edid('%s%sList' % (word, part.capitalize())), chance, got))
    factions = []
    if k['factions_of']:
        src = recordio.load(gd, npcs[k['factions_of'].lower()])
        factions = [json.loads(json.dumps(s)) for s in src['subs'] if s['tag'] == 'SNAM']
    base_of = {}
    import api_characters
    for src_edid in k['from']:
        fid = npcs[src_edid.lower()]
        rec = recordio.load(gd, fid)
        rec['src'] = ''
        rec['copied_from'] = gd.key(fid)
        inv = recordio.load(gd, inventory_source(gd, fid))
        flags = _num(rec, 'ACBS', 'Template flags')
        if flags & USE_BASE:
            _set(rec, 'ACBS', 'Flags', _num(rec, 'ACBS', 'Flags') & ~1)       # (whether she's a woman comes with the looks)
        flags &= ~(USE_BASE | USE_INVENTORY)
        if factions:
            flags &= ~USE_FACTIONS
            rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'SNAM']
            for s in factions:
                api_characters.insert(rec, json.loads(json.dumps(s)))
        _set(rec, 'ACBS', 'Template flags', flags)
        if recordio.field(rec, 'FULL') == '' and not any(s['tag'] == 'FULL' for s in rec['subs']):
            api_characters.insert(rec, _sub('NPC_', 'FULL', word.encode() + b'\0'))
        recordio.set_field(rec, 'FULL', word)
        recordio.set_field(rec, 'EDID', edid('%s%s' % (word, src_edid)))
        rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'CNTO']
        swapped = dict(_clothing(gd, inv))
        put = set()
        for n, s in enumerate(inv['subs']):
            if s['tag'] != 'CNTO':
                continue
            if n in swapped:
                part = swapped[n]
                for p in (('body',) if part == 'body' else ('head', 'eyes')):
                    if p not in put:
                        c = json.loads(json.dumps(s))
                        for f in c['fields']:
                            if f.get('name') == 'Item':
                                f['value'] = lists[p]
                            elif f.get('name') == 'Count':
                                f['value'] = 1
                        api_characters.insert(rec, c)
                        put.add(p)
            else:
                api_characters.insert(rec, json.loads(json.dumps(s)))
        for p in ('body', 'head', 'eyes'):            # (a template that wore nothing on its head still gets the look's hat)
            if p not in put:
                c = api_characters.insert(rec, _sub('NPC_', 'CNTO', struct.pack('<Ii', 0, 1)))
                for f in c['fields']:
                    if f.get('name') == 'Item':
                        f['value'] = lists[p]
        base_of[gd.key(fid)] = keys.add(rec)
        rep['records'][src_edid] = {'key': base_of[gd.key(fid)], 'inventory_from': recordio.field(inv, 'EDID'),
                                    'clothing_lists_swapped': len(swapped)}
    swaps = []
    for ck, cell in pr.cells.items():
        for rk, r in (cell.get('refs') or {}).items():
            b = r.get('base')
            if b in base_of and not r.get('removed'):
                src_edid = gd.edid(gd.from_key(b))
                if ck.startswith('+'):
                    rep['inside_left'][src_edid] = rep['inside_left'].get(src_edid, 0) + 1
                    continue
                swaps.append({'op': 'swap', 'cell': ck, 'ref': rk, 'base': base_of[b]})
                rep['swapped'][src_edid] = rep['swapped'].get(src_edid, 0) + 1
    rep['keys_from'] = '+%06X' % pr.next_id
    return keys.ops + swaps, rep


# the Mojave's sides, by words in their factions' editor IDs: the user, 20 Nov 2026, "all mojave themed enemies need to be
# replaced or removed"; inside the places of the mod's own (the hotels' floors) they go
MOJAVE_SIDES = {'Fiends': ('fiend',), 'Powder Gangers': ('powderganger',), 'Raiders': ('raiderfaction',),
                'Jackals': ('jackalsgang',), 'Vipers': ('banditviper', 'vipergang'), 'Legion': ('caesarslegion', 'legionfaction'),
                'Great Khans': ('greatkhan',)}


def factions(gd, fid, depth=0, seen=None):
    """Editor IDs of every faction a spawn can be in: its own, or its template's where it takes them, every list entry."""
    seen = set() if seen is None else seen
    if depth > 8 or fid in seen or fid not in gd.forms:
        return set()
    seen.add(fid)
    if gd.forms[fid][1].tag in ('LVLN', 'LVLC'):
        out = set()
        for e in _entries(gd, fid):
            out |= factions(gd, e, depth + 1, seen)
        return out
    rec = recordio.load(gd, fid)
    tp = recordio.field(rec, 'TPLT')
    if tp and _num(rec, 'ACBS', 'Template flags') & 0x04:
        return factions(gd, gd.from_key(tp), depth + 1, seen)
    return {gd.edid(gd.from_key(f['value'])) or '' for s in rec['subs'] if s['tag'] == 'SNAM'
            for f in s['fields'] if f.get('code') == 'F' and f.get('value')}


def mojave_side(gd, base):
    """The Mojave side a placed actor's base belongs to, or None (a record of the mod's own is never one)."""
    if not base or base.startswith('+'):
        return None
    fid = gd.from_key(base)
    if fid not in gd.forms or gd.forms[fid][1].tag not in ('NPC_', 'LVLN'):
        return None
    words = ' '.join(factions(gd, fid)).lower()
    return next((side for side, ws in MOJAVE_SIDES.items() if any(w in words for w in ws)), None)


def _names(value, keys):
    """The keys among `keys` a ref's change names anywhere in it."""
    if isinstance(value, str):
        return {value} & keys
    if isinstance(value, dict):
        return set().union(*(_names(v, keys) for v in value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*(_names(v, keys) for v in value)) if value else set()
    return set()


def clear_inside(gd, pr):
    """(ops, report): every Mojave enemy the mod placed in a place of its own removed (a 'remove' each), one Undo. One that
    another ref names (an enable parent, a link) is left and reported, so nothing points at a ref that isn't there."""
    gone, rep = {}, {'removed': {}, 'kept_named': []}
    side_of = {}
    for ck, cell in pr.cells.items():
        if not ck.startswith('+'):
            continue
        for rk, r in (cell.get('refs') or {}).items():
            b = r.get('base')
            if r.get('removed') or not b:
                continue
            if b not in side_of:
                side_of[b] = mojave_side(gd, b)
            if side_of[b]:
                gone[rk] = (ck, side_of[b])
    keys = set(gone)
    for ck, cell in pr.cells.items():
        for rk, r in (cell.get('refs') or {}).items():
            if rk in keys or r.get('removed'):
                continue
            for k in _names(r, keys):
                rep['kept_named'].append(k)
                gone.pop(k, None)
    ops = []
    for rk, (ck, side) in sorted(gone.items()):
        ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
        name = recordio.field(pr.records[ck], 'FULL') if ck in pr.records else ck
        rep['removed'].setdefault(name or ck, {}).setdefault(side, 0)
        rep['removed'][name or ck][side] += 1
    return ops, rep


def apply_clear(server):
    """clear_inside as one Undo."""
    ops, rep = clear_inside(server.GD, server.PR)
    if ops:
        server.edit('Take the Mojave\'s gangs out of Waikiki\'s places', ops)
    return rep


def apply(server, kind):
    """Plan and put one kind in as one Undo; checks the records got the keys they were planned with."""
    pr = server.PR
    ops, rep = plan(server.GD, pr, kind)
    first = pr.next_id
    label = 'Dress Waikiki\'s %s' % kind
    out = server.edit(label, ops)
    made = [k for k in (out.get('made') or [])] if isinstance(out, dict) else []
    want = ['+%06X' % (first + n) for n in range(sum(1 for o in ops if o['op'] == 'record_new'))]
    if made[:len(want)] != want:
        raise RuntimeError('records got other keys than planned (%s vs %s): undo this step' % (made[:3], want[:3]))
    return rep


if __name__ == '__main__':
    import sys
    import gamedata
    import project
    import server
    server.not_while_playing = lambda: None
    server.GD = gamedata.GameData()
    server.BR = None
    p = project.Project.open('Waikiki')
    server.load_game(p)
    for kind in sys.argv[1:] or list(KINDS):
        o, r = plan(server.GD, p, kind)
        print(kind, len(o), 'ops')
        print(json.dumps(r, indent=1))
