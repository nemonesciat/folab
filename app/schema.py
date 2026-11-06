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
        ('Condition', [('B', 'Type'), ('3x', ''), ('I', 'Value'), ('H', 'Function'), ('2x', ''), ('I', 'Parameter 1'), ('I', 'Parameter 2'), ('I', 'Run on')]),
        ('Condition', [('B', 'Type'), ('3x', ''), ('I', 'Value'), ('H', 'Function'), ('2x', ''), ('I', 'Parameter 1'), ('I', 'Parameter 2')])]

def _size(fields):
    return sum(struct.calcsize('<' + ((c[:-1] or '1') + 's' if c.endswith('x') else 'I' if c == 'F' else c)) for c, _n in fields)


def _prefixes(label, fields, sizes):
    """The same layout cut short at each of several byte sizes (newer files grew some records at the end),
    longest first."""
    out = []
    for want in sorted(sizes, reverse=True):
        for k in range(len(fields) + 1):
            if _size(fields[:k]) == want:
                out.append((label, fields[:k]))
                break
        else:
            raise ValueError('%s: no cut of the layout is %d bytes' % (label, want))
    return out


def _rep(label, fields, counts):
    """A layout of n entries of the same shape, for each n in counts (largest first, so the fullest fits first)."""
    return [(label, [(c, '%s %d' % (nm, k + 1) if nm else nm) for k in range(n) for c, nm in fields]) for n in sorted(counts, reverse=True)]


MARK = ('Marker', [])

COMMON = {
    'EDID': ('Editor ID', 'z'), 'FULL': ('Name', 'z'), 'MODL': ('Model', 'z'), 'MODB': ('Model bound', [('f', 'Radius')]),
    'ICON': ('Icon', 'z'), 'MICO': ('Small icon', 'z'), 'SCRI': ('Script', 'F'), 'OBND': OBND, 'DESC': ('Description', 'z'),
    'YNAM': ('Pick-up sound', 'F'), 'ZNAM': ('Drop sound', 'F'), 'EITM': ('Object effect', 'F'), 'ETYP': ('Equip type', [('i', 'Type')]),
    'REPL': ('Repair list', 'F'), 'BIPL': ('Biped model list', 'F'), 'CTDA': CTDA, 'EAMT': ('Effect charge', [('H', 'Amount')]),
    'EFID': ('Effect', 'F'), 'EFIT': ('Effect data', [('I', 'Magnitude'), ('I', 'Area'), ('I', 'Duration'), ('I', 'Range'), ('i', 'Actor value')]),
    'CNTO': ('Item', [('F', 'Item'), ('i', 'Count')]), 'SNAM': ('Sound', 'F'),
    # scripts, as they sit inside quests, dialogue, packages, perks, terminals and script records
    'SCHR': ('Script header', [('4x', ''), ('I', 'Reference count'), ('I', 'Compiled size'), ('I', 'Variable count'), ('H', 'Type'), ('H', 'Flags')]),
    'SCRO': ('Script reference', 'F'), 'SCRV': ('Script variable', [('I', 'Index')]), 'SCVR': ('Script variable name', 'z'),
    'SLSD': ('Script variable data', [('I', 'Index'), ('12x', ''), ('B', 'Flags'), ('7x', '')]),
    # what a thing breaks into
    'DEST': ('Destruction', [('I', 'Health'), ('B', 'Stages'), ('B', 'Flags'), ('2x', '')]),
    'DSTD': ('Damage stage', [('B', 'Health %'), ('B', 'Index'), ('B', 'Damage stage'), ('B', 'Flags'), ('I', 'Self damage per second'),
                              ('F', 'Explosion'), ('F', 'Debris'), ('i', 'Debris count')]),
    'DSTF': MARK, 'DMDL': ('Damaged model', 'z'),
    'COED': ('Owner', [('F', 'Owner'), ('I', 'Rank or global'), ('f', 'Condition')]),
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


# ---- more layouts (kept apart from the first set above; same rules) ----
_WEAP_DNAM = [
    ('I', 'Animation type'), ('f', 'Animation multiplier'), ('f', 'Reach'), ('B', 'Flags'), ('B', 'Grip animation'),
    ('B', 'Ammo used per shot'), ('B', 'Reload animation'), ('f', 'Min spread'), ('f', 'Spread'), ('f', 'Drift'),
    ('f', 'Sight FOV'), ('f', 'Unknown 1'), ('F', 'Projectile'), ('B', 'V.A.T.S. to-hit chance'), ('B', 'Attack animation'),
    ('B', 'Projectiles per shot'), ('B', 'Embedded weapon actor value'), ('f', 'Min range'), ('f', 'Max range'),
    ('I', 'On hit'), ('I', 'More flags'), ('f', 'Attack animation multiplier'), ('f', 'Fire rate'), ('f', 'Override action points'),
    ('f', 'Rumble left motor'), ('f', 'Rumble right motor'), ('f', 'Rumble duration'), ('f', 'Override damage to weapon ×'),
    ('f', 'Attack shots per second'), ('f', 'Reload time'), ('f', 'Jam time'), ('f', 'Aim arc'), ('I', 'Skill'),
    ('I', 'Rumble pattern'), ('f', 'Rumble wavelength'), ('f', 'Limb damage ×'), ('I', 'Resist'), ('f', 'Sight usage'),
    ('f', 'Semi-auto delay min'), ('f', 'Semi-auto delay max'),
    ('I', 'Mod 1 effect'), ('I', 'Mod 2 effect'), ('I', 'Mod 3 effect'), ('f', 'Mod 1 value'), ('f', 'Mod 2 value'), ('f', 'Mod 3 value'),
    ('I', 'Power attack animation'), ('I', 'Strength needed'), ('B', 'Unknown 2'), ('B', 'Reload animation mod'), ('2x', ''),
    ('f', 'Regen rate'), ('f', 'Kill impulse'), ('f', 'Mod 1 value B'), ('f', 'Mod 2 value B'), ('f', 'Mod 3 value B'),
    ('f', 'Impulse distance'), ('I', 'Skill needed'), ('I', 'Unknown 3')]
_ARMO_DNAM = _prefixes('Protection', [('h', 'DR'), ('H', 'Flags'), ('f', 'DT'), ('4x', '')], [12, 4])
_MODEL_DETAIL = {'MODD': ('Face-gen model flags', [('B', 'Flags')]), 'MOSD': ('Face-gen model flags', [('B', 'Flags')])}
_DECAL = ('Decal', [('f', 'Min width'), ('f', 'Max width'), ('f', 'Min height'), ('f', 'Max height'), ('f', 'Depth'), ('f', 'Shininess'),
                    ('f', 'Parallax scale'), ('B', 'Parallax passes'), ('B', 'Flags'), ('2x', ''), ('B', 'Red'), ('B', 'Green'), ('B', 'Blue'), ('x', '')])
_IDLE_LIST = {'IDLF': ('Idle flags', [('B', 'Flags')]), 'IDLC': [('Idle count', [('B', 'Count')]), ('Idle count', [('B', 'Count'), ('3x', '')])],
              'IDLT': ('Idle timer', [('f', 'Seconds')]), 'IDLA': ('Idles', 'F*')}
_TYPE_ADD = {
    'WEAP': {
        'MODD': ('Face-gen model flags', [('B', 'Flags')]),
        'DNAM': _prefixes('Weapon data', _WEAP_DNAM, [204, 200, 196, 180, 172, 164, 136]),
        'XNAM': ('Sound (far shot)', 'F'), 'TNAM': ('Sound (no ammo)', 'F'), 'NAM6': ('Sound (idle / melee)', 'F'),
        'NAM7': ('Sound (looping shot)', 'F'), 'NAM8': ('Unequip sound', 'F'), 'NAM9': ('Equip sound', 'F'), 'UNAM': ('Idle sound', 'F'),
        'WMS1': ('Mod shot sound', 'F'), 'WMS2': ('Mod shot sound (2D)', 'F'), 'EFSD': ('Effect shader', 'F'),
        'WNM1': ('1st-person model with mod 1', 'F'), 'WNM2': ('1st-person model with mod 2', 'F'), 'WNM3': ('1st-person model with mod 3', 'F'),
        'WNM4': ('1st-person model with mods 1+2', 'F'), 'WNM5': ('1st-person model with mods 1+3', 'F'),
        'WNM6': ('1st-person model with mods 2+3', 'F'), 'WNM7': ('1st-person model with all mods', 'F'),
        'MWD1': ('Model with mod 1', 'z'), 'MWD2': ('Model with mod 2', 'z'), 'MWD3': ('Model with mod 3', 'z'),
        'MWD4': ('Model with mods 1+2', 'z'), 'MWD5': ('Model with mods 1+3', 'z'), 'MWD6': ('Model with mods 2+3', 'z'),
        'MWD7': ('Model with all mods', 'z'), 'MOD2': ('Shell casing model', 'z'), 'MOD3': ('1st-person model', 'z'),
        'MOD4': ('Model for mods', 'z'), 'NNAM': ('Embedded weapon node', 'z'), 'VANM': ('V.A.T.S. attack name', 'z'),
    },
    'ARMO': dict(_MODEL_DETAIL, ICO2=('Icon (female)', 'z'), MIC2=('Small icon (female)', 'z'), BMCT=('Ragdoll constraint template', 'z'),
                 DNAM=_ARMO_DNAM),
    'ARMA': ('Armor addons', dict(_MODEL_DETAIL, ICO2=('Icon (female)', 'z'), MOD2=('Ground model', 'z'), MOD3=('Worn model (female)', 'z'),
                                  BMDT=('Body slots', [('I', 'Biped flags'), ('B', 'Flags'), ('3x', '')]),
                                  DATA=('Data', [('i', 'Value'), ('i', 'Health'), ('f', 'Weight')]), DNAM=_ARMO_DNAM)),
    'NPC_': {'NAM5': ('Unknown', [('B', 'Unknown 1'), ('B', 'Unknown 2')])},
    'CREA': {
        'PNAM': ('Body part data', 'F'), 'CNAM': ('Impact data set', 'F'), 'LNAM': ('Melee weapon list', 'F'),
        'CSDT': ('Sound type', [('I', 'Type')]), 'CSDI': ('Sound', 'F'), 'CSDC': ('Sound chance', [('B', 'Chance')]),
    },
    'FACT': {'DATA': [('Flags', [('B', 'Flags'), ('B', 'Flags 2'), ('2x', '')]), ('Flags', [('B', 'Flags')])],
             'CNAM': ('Unknown', [('f', 'Value')])},
    'DIAL': ('Dialogue topics', {
        'QSTI': ('Quest', 'F'), 'PNAM': ('Priority', [('f', 'Priority')]), 'INFC': ('Response link', 'F'), 'INFX': ('Response link index', [('i', 'Index')]),
        'DATA': [('Data', [('B', 'Type'), ('B', 'Flags')]), ('Data', [('B', 'Type')])], 'TDUM': ('Dumb response', 'z')}),
    'INFO': ('Dialogue responses', {
        'DATA': ('Data', [('B', 'Type'), ('B', 'Next speaker'), ('H', 'Flags')]), 'QSTI': ('Quest', 'F'),
        'TRDT': ('Response', [('I', 'Emotion'), ('i', 'Emotion strength'), ('4x', ''), ('B', 'Response number'), ('3x', ''), ('F', 'Sound'),
                              ('B', 'Use emotion animation'), ('3x', '')]),
        'NAM1': ('Response text', 'z'), 'NAM2': ('Script notes', 'z'), 'NAM3': ('Edits', 'z'), 'TCLT': ('Choice', 'F'), 'NEXT': MARK,
        'ANAM': ('Speaker', 'F'), 'TCFU': ('Linked from topic', 'F'), 'NAME': ('Add topic', 'F'), 'KNAM': ('Speech skill', 'F'),
        'TCLF': ('Link from', 'F'), 'RNAM': ('Prompt', 'z'), 'PNAM': ('Previous response', 'F'), 'DNAM': ('Speech challenge', [('I', 'Difficulty')]),
        'LNAM': ('Listener idle', 'F'), 'SNAM': ('Speaker idle', 'F')}),
    'QUST': {'INDX': ('Stage', [('h', 'Index')]), 'QSDT': ('Stage flags', [('B', 'Flags')]), 'QOBJ': ('Objective', [('i', 'Index')]),
             'NNAM': ('Objective text', 'z'), 'NAM0': ('Next quest', 'F'), 'QSTA': ('Target', [('F', 'Target'), ('B', 'Flags'), ('3x', '')]), 'CNAM': ('Log entry', 'z')},
    'PERK': {'PRKE': ('Entry', [('B', 'Type'), ('B', 'Rank'), ('B', 'Priority')]), 'PRKC': ('Condition runs on', [('b', 'Who')]),
             'EPFT': ('Entry value type', [('B', 'Type')]), 'EPF3': ('Entry script flags', [('H', 'Flags')]), 'PRKF': MARK},
    'RACE': ('Races', {
        'DATA': ('Data', [(c, 'Skill %d %s' % (k + 1, w)) for k in range(7) for c, w in (('b', 'skill'), ('b', 'boost'))] +
                          [('2x', ''), ('f', 'Male height'), ('f', 'Female height'), ('f', 'Male weight'), ('f', 'Female weight'), ('I', 'Flags')]),
        'VTCK': ('Voices', [('F', 'Male voice'), ('F', 'Female voice')]), 'DNAM': ('Default hair', [('F', 'Male hair'), ('F', 'Female hair')]),
        'CNAM': ('Default hair colour', [('B', 'Male'), ('B', 'Female')]), 'PNAM': ('Face-gen main clamp', [('f', 'Value')]),
        'UNAM': ('Face-gen face clamp', [('f', 'Value')]), 'ATTR': ('Attributes', [('B', 'Male'), ('B', 'Female')]),
        'INDX': ('Head part index', [('I', 'Index')]), 'HNAM': ('Hairs', 'F*'), 'ENAM': ('Eyes', 'F*'), 'ONAM': ('Older race', 'F'), 'YNAM': ('Younger race', 'F'),
        'MODD': ('Face-gen model flags', [('B', 'Flags')]), 'NAM0': MARK, 'NAM1': MARK, 'NAM2': MARK, 'MNAM': MARK, 'FNAM': MARK, 'SNAM': ('Unknown', [('B', 'Unknown 1'), ('B', 'Unknown 2')])}),
    'CLAS': ('Classes', {
        'DATA': ('Data', [('i', 'Tag skill 1'), ('i', 'Tag skill 2'), ('i', 'Tag skill 3'), ('i', 'Tag skill 4'), ('I', 'Flags'), ('I', 'Services'),
                          ('b', 'Teaches'), ('B', 'Max training'), ('2x', '')]),
        'ATTR': ('S.P.E.C.I.A.L.', [('B', n) for n in ('Strength', 'Perception', 'Endurance', 'Charisma', 'Intelligence', 'Agility', 'Luck')])}),
    'ECZN': ('Encounter zones', {'DATA': ('Data', [('F', 'Owner'), ('b', 'Rank'), ('b', 'Min level'), ('B', 'Flags'), ('B', 'Unused')])}),
    'REGN': ('Regions', {
        'RCLR': ('Map colour', [('B', 'Red'), ('B', 'Green'), ('B', 'Blue'), ('x', '')]), 'WNAM': ('Worldspace', 'F'),
        'RPLI': ('Edge fall-off', [('I', 'Distance')]),
        'RDAT': ('Data header', [('I', 'Type'), ('B', 'Override'), ('B', 'Priority'), ('2x', '')]),
        'RDWT': _rep('Weather', [('F', 'Weather'), ('I', 'Chance'), ('F', 'Global')], range(1, 9)),
        'RDSD': _rep('Sound', [('F', 'Sound'), ('I', 'Flags'), ('I', 'Chance')], range(1, 70)),
        'RDMP': ('Map name', 'z'), 'RDID': ('Imposters', 'F*'),
        'RDOT': [MARK] + _rep('Object', [('F', 'Object'), ('H', 'Parent index'), ('2x', ''), ('f', 'Density'), ('B', 'Clustering'), ('B', 'Min slope'),
                                          ('B', 'Max slope'), ('B', 'Flags'), ('H', 'Radius from parent'), ('H', 'Radius'), ('f', 'Min height'),
                                          ('f', 'Max height'), ('f', 'Sink'), ('f', 'Sink variance'), ('f', 'Size variance'), ('H', 'Angle X'),
                                          ('H', 'Angle Y'), ('H', 'Angle Z'), ('2x', ''), ('4x', '')], range(1, 14)), 'RDSI': ('Incidental sound', 'F'), 'RDSB': ('Sound set', 'F')}),
    'PACK': ('AI packages', dict(_IDLE_LIST, **{
        'PKDT': _prefixes('Data', [('I', 'Flags'), ('B', 'Type'), ('B', 'Unused'), ('H', 'Fallout flags'), ('H', 'Type flags'), ('2x', '')], [12, 8]),
        'PSDT': ('Schedule', [('b', 'Month'), ('b', 'Day of week'), ('B', 'Date'), ('b', 'Time'), ('i', 'Duration')]),
        'INAM': ('Idle', 'F'), 'TNAM': ('Topic', 'F'), 'PKFD': ('Follow distance', [('f', 'Distance')]),
        'PKPT': [('Patrol flags', [('B', 'Flags'), ('B', 'Flags 2')]), ('Patrol flags', [('B', 'Flags')])],
        'POBA': MARK, 'POEA': MARK, 'POCA': MARK, 'PKAM': MARK, 'PKED': MARK, 'PUID': MARK, 'CNAM': ('Combat style', 'F')})),
    'IDLE': ('Idle animations', {
        'ANAM': ('Related idles', [('F', 'Parent'), ('F', 'Previous')]),
        'DATA': _prefixes('Data', [('B', 'Group'), ('B', 'Loop min'), ('B', 'Loop max'), ('B', 'Unknown'), ('h', 'Replay delay'), ('B', 'Flags'), ('B', 'Unused')], [8, 6])}),
    'IDLM': ('Idle markers', dict(_IDLE_LIST)),
    'MGEF': ('Magic effects', {
        'DATA': ('Data', [('I', 'Flags'), ('f', 'Base cost'), ('F', 'Associated item'), ('i', 'School'), ('i', 'Resist'), ('H', 'Counter effects'), ('2x', ''),
                          ('F', 'Light'), ('f', 'Projectile speed'), ('F', 'Effect shader'), ('F', 'Object display shader'), ('F', 'Effect sound'),
                          ('F', 'Bolt sound'), ('F', 'Hit sound'), ('F', 'Area sound'), ('f', 'Enchantment factor'), ('f', 'Barter factor'),
                          ('I', 'Archetype'), ('i', 'Actor value')])}),
    'ENCH': ('Enchantments', {'ENIT': ('Data', [('I', 'Type'), ('i', 'Charge'), ('i', 'Cost'), ('B', 'Flags'), ('3x', '')])}),
    'INGR': ('Ingredients', {'ENIT': ('Data', [('i', 'Value'), ('B', 'Flags'), ('3x', '')]), 'DATA': ('Data', [('f', 'Weight')])}),
    'PROJ': ('Projectiles', {
        'DATA': _prefixes('Data', [('H', 'Flags'), ('H', 'Type'), ('f', 'Gravity'), ('f', 'Speed'), ('f', 'Range'), ('F', 'Light'),
                                   ('F', 'Muzzle flash light'), ('f', 'Tracer chance'), ('f', 'Explosion proximity'), ('f', 'Explosion timer'),
                                   ('F', 'Explosion'), ('F', 'Sound'), ('f', 'Muzzle flash duration'), ('f', 'Fade duration'),
                                   ('f', 'Impact force'), ('F', 'Countdown sound'), ('F', 'Disable sound'), ('F', 'Default weapon source'),
                                   ('f', 'Rotation X'), ('f', 'Rotation Y'), ('f', 'Rotation Z'), ('f', 'Bounce ×')], [84, 68]),
        'NAM1': ('Model file', 'z'), 'VNAM': ('Sound level', [('I', 'Level')])}),
    'EXPL': ('Explosions', {
        'DATA': ('Data', [('f', 'Force'), ('f', 'Damage'), ('f', 'Radius'), ('F', 'Light'), ('F', 'Sound 1'), ('I', 'Flags'), ('f', 'Image space radius'),
                          ('F', 'Impact data set'), ('F', 'Sound 2'), ('f', 'Radiation level'), ('f', 'Radiation time'), ('f', 'Radiation radius'),
                          ('I', 'Sound level')]),
        'MNAM': ('Image space modifier', 'F')}),
    'IPCT': ('Impacts', {
        'DATA': ('Data', [('f', 'Effect duration'), ('I', 'Orientation'), ('f', 'Angle threshold'), ('f', 'Placement radius'), ('I', 'Sound level'), ('I', 'Flags')]),
        'DODT': _DECAL, 'DNAM': ('Texture set', 'F'), 'NAM1': ('Second sound', 'F')}),
    'IPDS': ('Impact data sets', {'DATA': ('Impacts', 'F*')}),
    'TXST': ('Texture sets', {'TX00': ('Colour map', 'z'), 'TX01': ('Normal map', 'z'), 'TX02': ('Mask', 'z'), 'TX03': ('Glow map', 'z'),
                              'TX04': ('Height map', 'z'), 'TX05': ('Environment map', 'z'), 'DNAM': ('Flags', [('H', 'Flags')]), 'DODT': _DECAL}),
    'RCPE': ('Recipes', {'DATA': ('Data', [('I', 'Skill'), ('I', 'Level'), ('F', 'Category'), ('F', 'Sub-category')]),
                         'RCIL': ('Ingredient', 'F'), 'RCQY': ('Quantity', [('i', 'Count')]), 'RCOD': ('Output', 'F')}),
    'CHAL': ('Challenges', {'DATA': ('Data', [('I', 'Type'), ('I', 'Threshold'), ('I', 'Flags'), ('I', 'Interval'), ('I', 'Parameter 1'), ('I', 'Parameter 2')]),
                            'XNAM': ('Parameter', 'F')}),
    'CMNY': ('Caravan money', {'DATA': ('Data', [('I', 'Absolute value')])}),
    'REPU': ('Reputations', {'DATA': ('Data', [('f', 'Value')])}),
    'GLOB': ('Globals', {'FNAM': ('Type', [('B', 'Type')]), 'FLTV': ('Value', [('f', 'Value')])}),
    'FLST': ('Form lists', {'LNAM': ('Entry', 'F')}),
    'TACT': ('Talking activators', {'VNAM': ('Voice type', 'F'), 'INAM': ('Radio template', 'F')}),
    'ADDN': ('Addon nodes', {'DATA': ('Node index', [('I', 'Index')]), 'DNAM': ('Data', [('H', 'Particle cap'), ('H', 'Flags')])}),
    'ANIO': ('Animated objects', {'DATA': ('Animation', 'F')}),
    'HDPT': ('Head parts', {'DATA': ('Flags', [('B', 'Flags')]), 'HNAM': ('Extra part', 'F')}),
    'LTEX': ('Landscape textures', {'TNAM': ('Texture set', 'F'), 'HNAM': ('Physics', [('B', 'Material'), ('B', 'Friction'), ('B', 'Restitution')]),
                                    'GNAM': ('Grass', 'F'), 'SNAM': ('Specular exponent', [('B', 'Exponent')])}),
    'EYES': ('Eyes', {'DATA': ('Flags', [('B', 'Flags')])}), 'HAIR': ('Hair', {'DATA': ('Flags', [('B', 'Flags')])}),
    'VTYP': ('Voice types', {'DNAM': ('Flags', [('B', 'Flags')])}),
    'CELL': {'XCLC': [('Grid', [('i', 'X'), ('i', 'Y'), ('B', 'Flags'), ('3x', '')]), ('Grid', [('i', 'X'), ('i', 'Y')])],
             'LNAM': ('Lighting inherits', [('I', 'Flags')]),
             'XCLL': ('Lighting', [('B', 'Ambient red'), ('B', 'Ambient green'), ('B', 'Ambient blue'), ('x', ''), ('B', 'Directional red'),
                                   ('B', 'Directional green'), ('B', 'Directional blue'), ('x', ''), ('B', 'Fog red'), ('B', 'Fog green'),
                                   ('B', 'Fog blue'), ('x', ''), ('f', 'Fog near'), ('f', 'Fog far'), ('i', 'Direction XY'), ('i', 'Direction Z'),
                                   ('f', 'Directional fade'), ('f', 'Clip distance'), ('f', 'Fog power')])},
    'CAMS': ('Camera shots', {
        'DATA': _prefixes('Data', [('I', 'Action'), ('I', 'Location'), ('I', 'Target'), ('I', 'Flags'), ('f', 'Player time ×'), ('f', 'Target time ×'),
                                   ('f', 'Global time ×'), ('f', 'Max time'), ('f', 'Min time'), ('f', 'Target % between actors')], [40, 36]),
        'MNAM': ('Image space modifier', 'F')}),
    'CPTH': ('Camera paths', {'ANAM': ('Related paths', [('F', 'Parent'), ('F', 'Previous')]), 'DATA': ('Zoom', [('B', 'Zoom')])}),
    'LSCR': ('Loading screens', {'WMI1': ('Loading screen type', 'F'),
                                 'LNAM': ('Location', [('F', 'Direct'), ('F', 'Worldspace'), ('h', 'Grid Y'), ('h', 'Grid X')])}),
    'GRAS': ('Grass', {'DATA': ('Data', [('B', 'Density'), ('B', 'Min slope'), ('B', 'Max slope'), ('B', 'Unknown'), ('H', 'Units from water'), ('2x', ''),
                                         ('I', 'Water rule'), ('f', 'Position range'), ('f', 'Height range'), ('f', 'Colour range'), ('f', 'Wave period'),
                                         ('B', 'Flags'), ('3x', '')])}),
    'CCRD': ('Cards', {'TX00': ('Face image', 'z'), 'TX01': ('Back image', 'z'), 'INTV': ('Number', [('I', 'Value')]), 'DATA': ('Value', [('I', 'Value')])}),
    'CDCK': ('Card decks', {'CARD': ('Card', 'F'), 'DATA': ('Count', [('I', 'Count')])}),
    'DOBJ': ('Default objects', {'DATA': ('Objects', 'F*')}),
    'IMOD': ('Weapon mods', {'DATA': ('Data', [('i', 'Value'), ('f', 'Weight')])}),
    'PWAT': ('Placeable water', {'DNAM': ('Data', [('I', 'Flags'), ('F', 'Water')])}),
    'AMEF': ('Ammo effects', {'DATA': ('Data', [('I', 'Type'), ('I', 'Operation'), ('f', 'Value')])}),
    'CLMT': ('Climates', {'WLST': _rep('Weather', [('F', 'Weather'), ('I', 'Chance'), ('F', 'Global')], [1, 2, 3, 4, 5, 6, 7, 8]),
                          'FNAM': ('Sun texture', 'z'), 'GNAM': ('Sun glare texture', 'z'),
                          'TNAM': ('Timing', [('B', 'Sunrise begin'), ('B', 'Sunrise end'), ('B', 'Sunset begin'), ('B', 'Sunset end'), ('B', 'Volatility'), ('B', 'Moons')])}),
    'ASPC': ('Acoustic spaces', {'WNAM': ('Unused', [('I', 'Value')]), 'RDAT': ('Region sound', 'F'), 'ANAM': ('Environment', [('I', 'Type')]), 'INAM': ('Is interior', [('I', 'Value')])}),
}
for _t, _d in _TYPE_ADD.items():
    if _t in TYPES:
        TYPES[_t][1].update(_d if isinstance(_d, dict) else _d[1])
    else:
        TYPES[_t] = _d


# subrecords that mean something else once a record's later parts begin (PERK's DATA inside its effects)
AFTER = {'PERK': ('PRKE', {'DATA'})}


def _alts(rtype, tag):
    d = TYPES.get(rtype, (None, {}))[1].get(tag) or COMMON.get(tag)
    return [] if d is None else d if isinstance(d, list) else [d]


_cond_params = None


def condition_params():
    """{condition function number: [(is it a form link, parameter's name)]}, from the game's own function table."""
    global _cond_params
    if _cond_params is None:
        import scriptc
        _cond_params = {e['code'] - 0x1000: [(p[0] in scriptc.PARAM_FORMS, p[2]) for p in e['params']]
                        for e in scriptc.tables().by_code.values() if 0x1000 <= e['code'] < 0x2000}
    return _cond_params


def condition_fields(data):
    """A condition's fields as its own bytes say: what its parameters are depends on the function (form links or plain
    numbers), and its value is a global's link when flag 4 is set, otherwise a float."""
    kind = data[0]
    fn = struct.unpack_from('<H', data, 8)[0]
    ps = condition_params().get(fn, [])
    code = lambda n: 'F' if n < len(ps) and ps[n][0] else 'I'
    fields = [('B', 'Type'), ('3x', ''), ('F' if kind & 4 else 'f', 'Value'), ('H', 'Function'), ('2x', ''),
              (code(0), 'Parameter 1'), (code(1), 'Parameter 2'), ('I', 'Run on'), ('F', 'Reference')]
    return fields[:{20: 7, 24: 8, 28: 9}[len(data)]]


def layout(rtype, tag, data=None):
    """(label, kind) for a subrecord; with data, the alternative whose size fits it (None when none does)."""
    if tag == 'CTDA' and data is not None and len(data) in (20, 24, 28):
        return 'Condition', condition_fields(data)
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
    if tag == 'CTDA':       # (a condition's own fields say what they are: see condition_fields)
        return [(f['code'], f['name']) if 'code' in f else ('%dx' % (len(f['pad']) // 2), '') for f in fields]
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
