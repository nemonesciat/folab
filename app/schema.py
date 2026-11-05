"""Field layouts of New Vegas records, for reading and editing them.

Each subrecord a record type has is described once: a zero-terminated string ('z'), a form link ('F'), a list of
form links ('F*'), or a struct of named fields. Struct field codes are Python struct letters (b B h H i I f) plus
'F' for a form link and 'Nx' for N bytes the game doesn't use (kept as they were, never shown). Subrecords not
described are kept as raw bytes and shown read-only.

Written from the known file format; checkall() proves it against the game: a layout only counts for a type when
every subrecord with that tag, in every record of that type in the official files, is exactly its size and encodes
back byte for byte."""
import struct

# ---- shared parts ----
OBND = ('Bounds', [('h', 'X1'), ('h', 'Y1'), ('h', 'Z1'), ('h', 'X2'), ('h', 'Y2'), ('h', 'Z2')])
CTDA = [('Condition', [('B', 'Type'), ('3x', ''), ('I', 'Value'), ('H', 'Function'), ('2x', ''), ('I', 'Parameter 1'),
                       ('I', 'Parameter 2'), ('I', 'Run on'), ('F', 'Reference')]),
        ('Condition', [('B', 'Type'), ('3x', ''), ('I', 'Value'), ('H', 'Function'), ('2x', ''), ('I', 'Parameter 1'), ('I', 'Parameter 2')])]
COMMON = {
    'EDID': ('Editor ID', 'z'), 'FULL': ('Name', 'z'), 'MODL': ('Model', 'z'), 'MODB': ('Model bound', [('f', 'Radius')]),
    'ICON': ('Icon', 'z'), 'MICO': ('Small icon', 'z'), 'SCRI': ('Script', 'F'), 'OBND': OBND, 'DESC': ('Description', 'z'),
    'YNAM': ('Pick-up sound', 'F'), 'ZNAM': ('Drop sound', 'F'), 'EITM': ('Object effect', 'F'), 'ETYP': ('Equip type', [('i', 'Type')]),
    'REPL': ('Repair list', 'F'), 'BIPL': ('Biped model list', 'F'), 'CTDA': CTDA, 'EAMT': ('Effect charge', [('H', 'Amount')]),
    'EFID': ('Effect', 'F'), 'EFIT': ('Effect data', [('I', 'Magnitude'), ('I', 'Area'), ('I', 'Duration'), ('I', 'Range'), ('i', 'Actor value')]),
    'CNTO': ('Item', [('F', 'Item'), ('i', 'Count')]), 'SNAM': ('Sound', 'F'),
}

TYPES = {
    'WEAP': ('Weapons', {
        'NAM0': ('Ammo', 'F'), 'INAM': ('Impact data set', 'F'), 'WNAM': ('1st-person model', 'F'),
        'DATA': ('Data', [('i', 'Value'), ('i', 'Health'), ('f', 'Weight'), ('h', 'Damage'), ('B', 'Clip size')]),
        'CRDT': ('Critical', [('H', 'Critical damage'), ('2x', ''), ('f', 'Critical chance ×'), ('B', 'Flags'), ('3x', ''), ('F', 'Critical effect')]),
        'VATS': [('V.A.T.S.', [('F', 'Effect'), ('f', 'Skill'), ('f', 'Damage ×'), ('f', 'AP'), ('B', 'Silent'), ('B', 'Mod required'), ('2x', '')]),
                 ('V.A.T.S.', [('F', 'Effect'), ('f', 'Skill'), ('f', 'Damage ×'), ('f', 'AP')])],
        'VNAM': ('Sound level', [('I', 'Level')]),
        'WMI1': ('Mod slot 1', 'F'), 'WMI2': ('Mod slot 2', 'F'), 'WMI3': ('Mod slot 3', 'F'),
    }),
    'ARMO': ('Apparel', {
        'MOD2': ('Ground model', 'z'), 'MOD3': ('Worn model (female)', 'z'), 'MOD4': ('Ground model (female)', 'z'),
        'BMDT': ('Body slots', [('I', 'Biped flags'), ('B', 'Flags'), ('3x', '')]),
        'DATA': ('Data', [('i', 'Value'), ('i', 'Health'), ('f', 'Weight')]),
        'DNAM': [('Protection', [('h', 'DR'), ('H', 'Flags'), ('f', 'DT'), ('4x', '')]), ('Protection', [('h', 'DR'), ('H', 'Flags')])],
        'SNAM': ('Sound', [('F', 'Sound'), ('B', 'Chance'), ('3x', ''), ('I', 'Type')]),
        'BNAM': ('Overrides sounds', [('I', 'Flag')]), 'TNAM': ('Animation type', [('I', 'Type')]),
    }),
    'AMMO': ('Ammo', {
        'DATA': ('Data', [('f', 'Speed'), ('B', 'Flags'), ('3x', ''), ('i', 'Value'), ('B', 'Clip rounds')]),
        'DAT2': [('Projectile', [('I', 'Projectiles per shot'), ('F', 'Projectile'), ('f', 'Weight'), ('F', 'Consumed ammo'), ('f', 'Consumed %')]),
                 ('Projectile', [('I', 'Projectiles per shot'), ('F', 'Projectile'), ('f', 'Weight')])],
        'ONAM': ('Short name', 'z'), 'QNAM': ('Abbreviation', 'z'), 'RCIL': ('Ammo effect', 'F'),
    }),
    'ALCH': ('Aid', {
        'DATA': ('Data', [('f', 'Weight')]),
        'ENIT': ('Effect data', [('i', 'Value'), ('B', 'Flags'), ('3x', ''), ('F', 'Withdrawal effect'), ('f', 'Addiction chance'), ('F', 'Consume sound')]),
    }),
    'MISC': ('Misc items', {'DATA': ('Data', [('i', 'Value'), ('f', 'Weight')]), 'RNAM': ('Radio sound', 'F')}),
    'KEYM': ('Keys', {'DATA': ('Data', [('i', 'Value'), ('f', 'Weight')]), 'RNAM': ('Radio sound', 'F')}),
    'BOOK': ('Books', {'DATA': ('Data', [('B', 'Flags'), ('b', 'Skill'), ('i', 'Value'), ('f', 'Weight')])}),
    'NOTE': ('Notes', {'DATA': ('Data', [('B', 'Type')]), 'ONAM': ('Quest', 'F')}),
    'CONT': ('Containers', {
        'DATA': ('Data', [('B', 'Flags'), ('f', 'Weight')]), 'QNAM': ('Close sound', 'F'), 'RNAM': ('Random looping sound', 'F'),
    }),
    'NPC_': ('Characters', {
        'ACBS': ('Base stats', [('I', 'Flags'), ('H', 'Fatigue'), ('H', 'Barter gold'), ('h', 'Level'), ('H', 'Calc min level'),
                                ('H', 'Calc max level'), ('H', 'Speed ×'), ('f', 'Karma'), ('h', 'Disposition'), ('H', 'Template flags')]),
        'SNAM': ('Faction', [('F', 'Faction'), ('b', 'Rank'), ('3x', '')]),
        'INAM': ('Death item', 'F'), 'VTCK': ('Voice', 'F'), 'TPLT': ('Template', 'F'), 'RNAM': ('Race', 'F'),
        'SPLO': ('Spell / ability', 'F'), 'PKID': ('AI package', 'F'), 'CNAM': ('Class', 'F'), 'HNAM': ('Hair', 'F'),
        'ENAM': ('Eyes', 'F'), 'ZNAM': ('Combat style', 'F'), 'PNAM': ('Head part', 'F'), 'LNAM': ('Hair length', [('f', 'Length')]),
        'HCLR': ('Hair colour', [('B', 'Red'), ('B', 'Green'), ('B', 'Blue'), ('x', '')]),
        'NAM4': ('Impact material', [('I', 'Type')]), 'NAM6': ('Height', [('f', 'Height')]), 'NAM7': ('Weight', [('f', 'Weight')]),
        'AIDT': ('AI', [('B', 'Aggression'), ('B', 'Confidence'), ('B', 'Energy'), ('B', 'Responsibility'), ('B', 'Mood'), ('3x', ''),
                        ('I', 'Services'), ('b', 'Teaches'), ('B', 'Max training'), ('b', 'Assistance'), ('B', 'Aggro radius on'), ('i', 'Aggro radius')]),
        'DATA': ('Stats', [('i', 'Health'), ('B', 'Strength'), ('B', 'Perception'), ('B', 'Endurance'), ('B', 'Charisma'),
                           ('B', 'Intelligence'), ('B', 'Agility'), ('B', 'Luck')]),
        'DNAM': ('Skills', [('B', n) for n in ('Barter', 'Big Guns', 'Energy Weapons', 'Explosives', 'Lockpick', 'Medicine', 'Melee Weapons',
                                               'Repair', 'Science', 'Guns', 'Sneak', 'Speech', 'Survival', 'Unarmed')] +
                           [('B', n + ' offset') for n in ('Barter', 'Big Guns', 'Energy Weapons', 'Explosives', 'Lockpick', 'Medicine', 'Melee Weapons',
                                                           'Repair', 'Science', 'Guns', 'Sneak', 'Speech', 'Survival', 'Unarmed')]),
    }),
    'CREA': ('Creatures', {
        'ACBS': ('Base stats', [('I', 'Flags'), ('H', 'Fatigue'), ('H', 'Barter gold'), ('h', 'Level'), ('H', 'Calc min level'),
                                ('H', 'Calc max level'), ('H', 'Speed ×'), ('f', 'Karma'), ('h', 'Disposition'), ('H', 'Template flags')]),
        'SNAM': ('Faction', [('F', 'Faction'), ('b', 'Rank'), ('3x', '')]),
        'INAM': ('Death item', 'F'), 'VTCK': ('Voice', 'F'), 'TPLT': ('Template', 'F'), 'SPLO': ('Spell / ability', 'F'),
        'PKID': ('AI package', 'F'), 'ZNAM': ('Combat style', 'F'), 'CSCR': ('Inherits sounds from', 'F'),
        'AIDT': ('AI', [('B', 'Aggression'), ('B', 'Confidence'), ('B', 'Energy'), ('B', 'Responsibility'), ('B', 'Mood'), ('3x', ''),
                        ('I', 'Services'), ('b', 'Teaches'), ('B', 'Max training'), ('b', 'Assistance'), ('B', 'Aggro radius on'), ('i', 'Aggro radius')]),
        'DATA': ('Stats', [('B', 'Type'), ('B', 'Combat skill'), ('B', 'Magic skill'), ('B', 'Stealth skill'), ('h', 'Health'), ('2x', ''),
                           ('h', 'Damage'), ('B', 'Strength'), ('B', 'Perception'), ('B', 'Endurance'), ('B', 'Charisma'),
                           ('B', 'Intelligence'), ('B', 'Agility'), ('B', 'Luck')]),
        'RNAM': ('Attack reach', [('B', 'Reach')]), 'TNAM': ('Turning speed', [('f', 'Speed')]), 'BNAM': ('Base scale', [('f', 'Scale')]),
        'WNAM': ('Foot weight', [('f', 'Weight')]), 'NAM4': ('Impact material', [('I', 'Type')]), 'NAM5': ('Sound level', [('I', 'Level')]),
        'EAMT': ('Attack animation', [('H', 'Type')]), 'NIFZ': ('Model list', 'z'),
    }),
    'FACT': ('Factions', {
        'XNAM': ('Relation', [('F', 'Faction'), ('i', 'Modifier'), ('I', 'Group combat reaction')]),
        'RNAM': ('Rank', [('i', 'Number')]), 'MNAM': ('Male title', 'z'), 'FNAM': ('Female title', 'z'), 'INAM': ('Insignia', 'z'),
        'WMI1': ('Reputation', 'F'),
    }),
    'PERK': ('Perks', {
        'DATA': [('Data', [('B', 'Trait'), ('B', 'Level'), ('B', 'Ranks'), ('B', 'Playable'), ('B', 'Hidden')]),
                 ('Data', [('B', 'Trait'), ('B', 'Level'), ('B', 'Ranks'), ('B', 'Playable')])],
    }),
    'LVLI': ('Item lists', {
        'LVLD': ('Chance none', [('B', 'Percent')]), 'LVLF': ('Flags', [('B', 'Flags')]), 'LVLG': ('Use global', 'F'),
        'LVLO': ('Entry', [('h', 'Level'), ('2x', ''), ('F', 'Item'), ('h', 'Count'), ('2x', '')]),
    }),
    'LVLN': ('Character lists', {
        'LVLD': ('Chance none', [('B', 'Percent')]), 'LVLF': ('Flags', [('B', 'Flags')]),
        'LVLO': ('Entry', [('h', 'Level'), ('2x', ''), ('F', 'Character'), ('h', 'Count'), ('2x', '')]),
    }),
    'LVLC': ('Creature lists', {
        'LVLD': ('Chance none', [('B', 'Percent')]), 'LVLF': ('Flags', [('B', 'Flags')]),
        'LVLO': ('Entry', [('h', 'Level'), ('2x', ''), ('F', 'Creature'), ('h', 'Count'), ('2x', '')]),
    }),
    'STAT': ('Statics', {'BRUS': ('Passthrough sound', [('b', 'Sound')]), 'RNAM': ('Looping sound', 'F')}),
    'MSTT': ('Movable statics', {'DATA': ('Data', [('B', 'Unknown')])}),
    'FURN': ('Furniture', {'MNAM': ('Marker flags', [('I', 'Flags')])}),
    'DOOR': ('Doors', {'ANAM': ('Close sound', 'F'), 'BNAM': ('Loop sound', 'F'), 'FNAM': ('Flags', [('B', 'Flags')])}),
    'LIGH': ('Lights', {
        'DATA': ('Light', [('i', 'Time'), ('I', 'Radius'), ('B', 'Red'), ('B', 'Green'), ('B', 'Blue'), ('x', ''), ('I', 'Flags'),
                           ('f', 'Falloff exponent'), ('f', 'FOV'), ('I', 'Value'), ('f', 'Weight')]),
        'FNAM': ('Fade', [('f', 'Value')]),
    }),
    'ACTI': ('Activators', {'VNAM': ('Activation sound', 'F'), 'INAM': ('Radio template', 'F'), 'RNAM': ('Radio station', 'F'),
                            'WNAM': ('Water type', 'F'), 'XATO': ('Activation prompt', 'z')}),
    'TERM': ('Terminals', {'PNAM': ('Password note', 'F'), 'DNAM': [('Data', [('B', 'Difficulty'), ('B', 'Flags'), ('B', 'Server type'), ('x', '')]),
                                    ('Data', [('B', 'Difficulty'), ('B', 'Flags'), ('B', 'Server type')])],
                           'ITXT': ('Menu item text', 'z'), 'RNAM': ('Result text', 'z'), 'ANAM': ('Menu item flags', [('B', 'Flags')]),
                           'INAM': ('Display note', 'F'), 'TNAM': ('Sub-menu', 'F')}),
    'CELL': ('Places', {'DATA': ('Flags', [('B', 'Flags')]), 'XCLW': ('Water height', [('f', 'Height')]), 'LTMP': ('Lighting template', 'F'),
                        'XCLR': ('Regions', 'F*'), 'XCIM': ('Image space', 'F'), 'XEZN': ('Encounter zone', 'F'), 'XCCM': ('Climate', 'F'),
                        'XCWT': ('Water', 'F'), 'XOWN': ('Owner', 'F'), 'XRNK': ('Owner rank', [('i', 'Rank')]), 'XCAS': ('Acoustic space', 'F'),
                        'XCMO': ('Music', 'F'), 'XNAM': ('Water noise texture', 'z')}),
    'QUST': ('Quests', {'DATA': [('Data', [('B', 'Flags'), ('B', 'Priority'), ('2x', ''), ('f', 'Delay')]),
                                 ('Data', [('B', 'Flags'), ('B', 'Priority')])]}),
    'WRLD': ('Worldspaces', {}),
    'SPEL': ('Spells and abilities', {'SPIT': ('Data', [('I', 'Type'), ('I', 'Cost'), ('I', 'Level'), ('B', 'Flags'), ('3x', '')])}),
}


# subrecords that mean something else once a record's later parts begin (PERK's DATA inside its effects)
AFTER = {'PERK': ('PRKE', {'DATA'})}


def _alts(rtype, tag):
    d = TYPES.get(rtype, (None, {}))[1].get(tag) or COMMON.get(tag)
    return [] if d is None else d if isinstance(d, list) else [d]


def layout(rtype, tag, data=None):
    """(label, kind) for a subrecord; with data, the alternative whose size fits it (None when none does)."""
    alts = _alts(rtype, tag)
    if data is None:
        return alts[0] if alts else None
    return next((d for d in alts if _fits(d, data)), None)


def _fmt(fields):
    """struct format and the fields kept (None for padding) for a struct layout"""
    fmt, keep = '<', []
    for code, name in fields:
        if code.endswith('x'):
            fmt += (code[:-1] or '1') + 's'
            keep.append(None)
        else:
            fmt += 'I' if code == 'F' else code
            keep.append((code, name))
    return fmt, keep


def _fits(d, data):
    kind = d[1]
    if kind == 'z':
        return not data or data.endswith(b'\0')
    if kind == 'F':
        return len(data) == 4
    if kind == 'F*':
        return len(data) % 4 == 0
    return struct.calcsize(_fmt(kind)[0]) == len(data)


def decode_sub(rtype, tag, data, late=False):
    """{'tag', 'label', 'kind': 'z'|'F'|'F*'|'struct'|'raw', 'value' or 'fields'}: raw when no layout fits, or when
    the subrecord is in a later part of the record the layouts don't describe (late)."""
    d = None if late and tag in AFTER.get(rtype, ('', ()))[1] else layout(rtype, tag, data)
    if d:
        label, kind = d
        if kind == 'z':
            return {'tag': tag, 'label': label, 'kind': 'z', 'value': data[:-1].decode('cp1252', 'replace')}
        if kind == 'F':
            return {'tag': tag, 'label': label, 'kind': 'F', 'value': struct.unpack('<I', data)[0]}
        if kind == 'F*':
            return {'tag': tag, 'label': label, 'kind': 'F*', 'value': list(struct.unpack('<%dI' % (len(data) // 4), data))}
        fmt, keep = _fmt(kind)
        fields = []
        for k, v in zip(keep, struct.unpack(fmt, data)):
            fields.append({'pad': v.hex()} if k is None else {'name': k[1], 'code': k[0], 'value': v})
        return {'tag': tag, 'label': label, 'kind': 'struct', 'fields': fields}
    first = layout(rtype, tag)
    return {'tag': tag, 'label': first[0] if first else tag, 'kind': 'raw', 'value': data.hex()}


def decode_record(rtype, subs):
    """Every subrecord of a record, decoded in order."""
    late, out = False, []
    after = AFTER.get(rtype, (None, ()))[0]
    for tag, data in subs:
        if tag == after:
            late = True
        out.append(decode_sub(rtype, tag, data, late))
    return out


def _struct_for(rtype, tag, fields):
    """the struct alternative a decoded subrecord came from (its fields, padding included, line up)"""
    for d in _alts(rtype, tag):
        if isinstance(d[1], list) and len(d[1]) == len(fields):
            return d[1]
    raise ValueError('no layout for %s %s with %d fields' % (rtype, tag, len(fields)))


def encode_sub(rtype, s):
    kind = s['kind']
    if kind == 'raw':
        return bytes.fromhex(s['value'])
    if kind == 'z':
        return s['value'].encode('cp1252', 'replace') + b'\0'
    if kind == 'F':
        return struct.pack('<I', int(s['value']))
    if kind == 'F*':
        return struct.pack('<%dI' % len(s['value']), *[int(v) for v in s['value']])
    fmt, keep = _fmt(_struct_for(rtype, s['tag'], s['fields']))
    vals = []
    for f, k in zip(s['fields'], keep):
        vals.append(bytes.fromhex(f['pad']) if k is None else float(f['value']) if k[0] == 'f' else int(f['value']))
    return struct.pack(fmt, *vals)


def form_offsets(rtype, tag, data, late=False):
    """Byte offsets of the form links inside one subrecord, by its layout (empty when it has none or none fits)."""
    d = None if late and tag in AFTER.get(rtype, ('', ()))[1] else layout(rtype, tag, data)
    if not d or d[1] == 'z':
        return []
    if d[1] == 'F':
        return [0]
    if d[1] == 'F*':
        return list(range(0, len(data) - 3, 4))
    out, off = [], 0
    for code, _name in d[1]:
        if code == 'F':
            out.append(off)
        off += struct.calcsize('<' + ((code[:-1] or '1') + 's' if code.endswith('x') else 'I' if code == 'F' else code))
    return out


def record_form_offsets(rtype, subs):
    """[(subrecord index, offset)] of every form link a layout knows of, in a record's subrecords."""
    late, out = False, []
    after = AFTER.get(rtype, (None, ()))[0]
    for n, (tag, data) in enumerate(subs):
        if tag == after:
            late = True
        out += [(n, o) for o in form_offsets(rtype, tag, data, late)]
    return out


def checkall(gd, types=None):
    """For every type and tag: how many subrecords decode and encode back exactly, and how many don't (a subrecord
    no layout fits counts as not, unless it is in a part the layouts leave raw on purpose)."""
    import collections
    import tes4
    want = set(types or TYPES)
    stats = {t: collections.defaultdict(lambda: [0, 0]) for t in want}
    records = collections.Counter()
    for p in gd.plugins:
        for rec, _path in p.walk():
            if rec.tag not in want:
                continue
            records[rec.tag] += 1
            subs = list(tes4.iter_subrecords(p.data(rec)))
            late = False
            after = AFTER.get(rec.tag, (None, ()))[0]
            for (tag, data), s in zip(subs, decode_record(rec.tag, subs)):
                if tag == after:
                    late = True
                left_raw = late and tag in AFTER.get(rec.tag, ('', ()))[1]
                ok = (s['kind'] != 'raw' or left_raw) and encode_sub(rec.tag, s) == data
                stats[rec.tag][tag][0 if ok else 1] += 1
    return records, stats
