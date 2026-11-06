"""The Characters page's routes and what's behind them: the choices its forms offer, what a character looks like and
wears (the mod's own records and unsaved changes included), new characters from a template, faces, AI packages from the
game's own, factions, and the Populate tool (populate.py).

The records themselves go through the same /api/record routes as Browse and Create."""
import json
import struct

import actors
import populate
import recordio
import tes4

PLAYER = 'FalloutNV.esm:000014'         # (made by the game itself: no record says so)

# where each subrecord sits in the game's records (their usual order), for putting a new one in the right place
ORDER = {
    'NPC_': ['EDID', 'OBND', 'FULL', 'MODL', 'MODB', 'MODT', 'ACBS', 'SNAM', 'INAM', 'VTCK', 'TPLT', 'RNAM', 'SPLO', 'EITM', 'EAMT', 'DEST', 'DSTD', 'DMDL',
             'DSTF', 'SCRI', 'CNTO', 'COED', 'AIDT', 'PKID', 'CNAM', 'DATA', 'DNAM', 'PNAM', 'HNAM', 'LNAM', 'ENAM', 'HCLR', 'ZNAM', 'NAM4', 'FGGS', 'FGGA',
             'FGTS', 'NAM5', 'NAM6', 'NAM7'],
    'CREA': ['EDID', 'OBND', 'FULL', 'MODL', 'MODB', 'MODT', 'SPLO', 'EITM', 'EAMT', 'NIFZ', 'NIFT', 'ACBS', 'SNAM', 'INAM', 'VTCK', 'TPLT', 'DEST', 'DSTD',
             'DMDL', 'DSTF', 'SCRI', 'CNTO', 'COED', 'AIDT', 'PKID', 'KFFZ', 'DATA', 'RNAM', 'ZNAM', 'PNAM', 'TNAM', 'BNAM', 'WNAM', 'NAM4', 'NAM5', 'CSCR',
             'CSDT', 'CSDI', 'CSDC', 'CNAM', 'LNAM'],
    'PACK': ['EDID', 'PKDT', 'PLDT', 'PSDT', 'PTDT', 'IDLF', 'IDLC', 'IDLT', 'IDLA', 'CTDA', 'PKDD', 'PKE2', 'PKPT', 'PKED', 'CNAM', 'PKW3', 'PKAM', 'PKFD',
             'PLD2', 'PTD2', 'PUID', 'POBA', 'POEA', 'POCA'],
    'FACT': ['EDID', 'FULL', 'XNAM', 'DATA', 'CNAM', 'RNAM', 'MNAM', 'FNAM', 'INAM', 'WMI1'],
}
# what a face is, in a character's record
FACE_TAGS = ('PNAM', 'HNAM', 'LNAM', 'ENAM', 'HCLR', 'FGGS', 'FGGA', 'FGTS')

# who a new character can start as: the game's own plain characters and creatures, none quest-bound
TEMPLATES = {
    'NPC_': [('GSSettlerAAM', 'Townsperson', 'An ordinary settler'), ('WestsideCitizenAAMTemplate', 'Town dweller', 'Lives in a poor part of town'),
             ('NVProspectorMale', 'Prospector', 'A wanderer of the waste'), ('NVMerchantMale', 'Merchant', 'A travelling trader, sells things'),
             ('CrimsonCaravanTraderAAMTemplate', 'Caravan trader', ''), ('CrimsonCaravanGuardAAMTemplate', 'Guard', 'Armed, watches over a place'),
             ('VStreetCasinoGuard', 'Casino guard', ''), ('PowderGangerGunAAMTEMPLATE', 'Outlaw with a gun', 'Hostile: a Powder Ganger'),
             ('PowderGangerMeleeAAMTEMPLATE', 'Outlaw with a club', 'Hostile: a Powder Ganger')],
    'CREA': [('CrRadroach', 'Radroach', ''), ('NVCrRaven', 'Raven', ''), ('CrBarkScorpion', 'Bark scorpion', ''), ('NVCrGiantMantis', 'Giant mantis', ''),
             ('CrLakelurkCG', 'Lakelurk', ''), ('CrMisterHandy', 'Mister Handy', 'A robot'), ('CrSporePlant', 'Spore plant', '')],
}
# AI packages start as copies of the game's own, so their every flag is one the game uses
PACKAGES = [
    ('sandbox', 'DefaultSandboxEditorLocation512', 'Sandbox here', 'Stay round their spot: sit, eat, sleep, chat, use what\'s there', {'radius': 512}),
    ('wander', 'DefaultWanderEditorLocation512', 'Wander round here', 'Walk about near their spot', {'radius': 512}),
    ('patrol', 'DefaultPatrolCasual', 'Patrol', 'Walk a path of patrol markers. The character must be linked to the first marker: FOLab can\'t make that link yet', {}),
    ('sleep', 'DefaultSleepAlways256', 'Sleep at night', 'To bed near their spot from 10 at night for 8 hours. Goes above the other packages', {'radius': 512, 'where': 3, 'time': 22, 'hours': 8}),
    ('guard', 'DefaultGuardStayAtPosition01', 'Guard', 'Stand at their spot and see off anyone who comes near', {}),
    ('stand', 'DefaultStayAtEditorLocationWeaponsDrawn', 'Stand ready', 'Stay at their spot, weapon out', {}),
    ('follow', 'DefaultFollowPlayerClose', 'Follow the player', 'Stay close behind the player', {}),
]


class _Cache:
    """What's read once per loaded game."""
    gd = None
    opts = None
    templates = None


def _find(gd, tag, edid):
    edid = edid.lower()
    for f, (_i, r) in gd.forms.items():
        if r.tag == tag and gd.edid(f).lower() == edid:
            return f
    return None


def edid_map(gd, tags):
    """{(type, lower editor ID): form} for the kinds asked."""
    out = {}
    for f, (_i, r) in gd.forms.items():
        if r.tag in tags:
            out[(r.tag, gd.edid(f).lower())] = f
    return out


def insert(rec, sub):
    """Put a new subrecord in its place: after the last of its own kind or of what comes before it."""
    order = ORDER.get(rec['type'], [])
    at = order.index(sub['tag']) if sub['tag'] in order else len(order)
    n = 0
    for k, s in enumerate(rec['subs']):
        if s['tag'] in order and order.index(s['tag']) <= at:
            n = k + 1
    rec['subs'].insert(n, sub)
    return sub


def subs_of(rec, tag):
    return [s for s in rec['subs'] if s['tag'] == tag]


def one(rec, tag):
    return next((s for s in rec['subs'] if s['tag'] == tag), None)


def num(rec, tag, name, default=0):
    s = one(rec, tag)
    if not s or s['kind'] != 'struct':
        return default
    return next((f['value'] for f in s['fields'] if f.get('name') == name), default)


def set_num(rec, tag, name, value):
    for f in one(rec, tag)['fields']:
        if f.get('name') == name:
            f['value'] = value
            return


def get_record(gd, pr, key):
    """A form as the mod has it, in recordio's form."""
    rec = pr.records.get(key) if pr else None
    return rec or recordio.load(gd, gd.from_key(key))


def exists(gd, pr, key):
    if not key:
        return False
    if pr and key in pr.records:
        return True
    if key.startswith('+'):
        return False
    try:
        return gd.from_key(key) in gd.forms
    except (ValueError, KeyError):
        return False


def type_of(gd, pr, key):
    if pr and key in pr.records:
        return pr.records[key]['type']
    return gd.forms[gd.from_key(key)][1].tag


def unique_edid(br, pr, base):
    taken = set(br.edids or {}) | {recordio.field(r, 'EDID').lower() for r in pr.records.values()}
    edid, n = base, 1
    while edid.lower() in taken:
        n += 1
        edid = '%s%d' % (base, n)
    return edid


# ---------- the choices the forms offer ----------

def _rows(gd, tag):
    out = []
    for f, (_i, r) in gd.forms.items():
        if r.tag == tag:
            d = gd.fields(f)
            out.append({'key': gd.key(f), 'edid': gd.edid(f), 'name': tes4.zstr(d.get('FULL', b''))})
    out.sort(key=lambda x: (x['name'] or x['edid']).lower())
    return out


def _preset_label(edid):
    """'CGPresetCaucasianF06' as 'Caucasian woman 6'."""
    e = edid.replace('CGPreset', '')
    for sex, word in (('F', 'woman'), ('M', 'man')):
        i = e.rfind(sex)
        if i > 0 and e[i + 1:].isdigit():
            return '%s %s %d' % (e[:i], word, int(e[i + 1:]))
    return edid


def options(gd, pr):
    """Races (with the hair and eyes each takes), classes, voices, hair, eyes, combat styles, factions, face presets."""
    if _Cache.gd is not gd or _Cache.opts is None:
        _Cache.gd, _Cache.templates = gd, None
        races = []
        for row in _rows(gd, 'RACE'):
            rec = recordio.load(gd, gd.from_key(row['key']))
            data = one(rec, 'DATA')
            flags = next((f['value'] for f in data['fields'] if f.get('name') == 'Flags'), 0) if data and data['kind'] == 'struct' else 0
            hairs = [k for s in subs_of(rec, 'HNAM') if s['kind'] == 'F*' for k in s['value']]
            eyes = [k for s in subs_of(rec, 'ENAM') if s['kind'] == 'F*' for k in s['value']]
            races.append(dict(row, playable=bool(flags & 1), child=bool(flags & 4), hairs=hairs, eyes=eyes))
        presets = []
        for f, (i, r) in gd.forms.items():
            if r.tag == 'NPC_':
                d = gd.fields(f)
                if len(d.get('ACBS', b'')) >= 4 and struct.unpack_from('<I', d['ACBS'])[0] & 4 and 'RNAM' in d:
                    presets.append({'key': gd.key(f), 'label': _preset_label(gd.edid(f)), 'female': bool(struct.unpack_from('<I', d['ACBS'])[0] & 1),
                                    'race': gd.key(gd.to_global(i, struct.unpack('<I', d['RNAM'])[0]))})
        presets.sort(key=lambda p: p['label'])
        _Cache.opts = {'races': races, 'classes': _rows(gd, 'CLAS'), 'voices': _rows(gd, 'VTYP'), 'hairs': _rows(gd, 'HAIR'), 'eyes': _rows(gd, 'EYES'),
                       'combat': _rows(gd, 'CSTY'), 'factions': _rows(gd, 'FACT'), 'presets': presets, 'order': ORDER}
    out = dict(_Cache.opts)
    # (the mod's own of these kinds)
    for name, tag in (('classes', 'CLAS'), ('factions', 'FACT')):
        mine = [{'key': k, 'edid': recordio.field(r, 'EDID'), 'name': recordio.field(r, 'FULL'), 'mine': True}
                for k, r in (pr.records.items() if pr else ()) if k.startswith('+') and r['type'] == tag]
        out[name] = mine + out[name]
    return out


def templates(gd):
    if _Cache.gd is not gd or _Cache.templates is None:
        options(gd, None)
        want = edid_map(gd, ('NPC_', 'CREA'))
        out = {}
        for tag, rows in TEMPLATES.items():
            out[tag] = [{'key': gd.key(want[(tag, e.lower())]), 'label': l, 'note': n} for e, l, n in rows if (tag, e.lower()) in want]
        _Cache.templates = out
    return _Cache.templates


def new_character(gd, pr, br, edit, body):
    """A character or creature of the mod's own from a template: a copy of it, without what ties it to the game's quests."""
    rec = json.loads(json.dumps(get_record(gd, pr, body['from'])))
    name = (body.get('name') or '').strip() or 'New character'
    stem = ''.join(w.capitalize() for w in ''.join(c if c.isalnum() else ' ' for c in name).split()) or 'Character'
    recordio.set_field(rec, 'EDID', unique_edid(br, pr, 'FOLab' + stem), label='Editor ID')
    full = one(rec, 'FULL')
    if full:
        full['value'] = name
    else:
        insert(rec, {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name})
    rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'SCRI']
    set_num(rec, 'ACBS', 'Flags', num(rec, 'ACBS', 'Flags') & ~0x2)     # (not essential)
    if rec['type'] == 'NPC_':
        # (the template's own packages belong to its town and its quests: only the game's general ones stay)
        keep = [s for s in subs_of(rec, 'PKID') if s['value'] and recordio.field(get_record(gd, pr, s['value']), 'EDID').startswith('Default')]
        rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'PKID' or s in keep]
        if not keep:
            insert(rec, {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': gd.key(_find(gd, 'PACK', 'DefaultSandboxEditorLocation512'))})
    rec['src'] = rec.get('src') or ''
    rec['copied_from'] = body['from']
    return edit('New character ' + name, [{'op': 'record_new', 'record': rec}])


# ---------- what a character looks like and wears ----------

def _first_of(gd, pr, key, want, depth=0):
    """A form, or a levelled list's first entry of the wanted types (lists inside lists followed)."""
    if depth > 6 or not exists(gd, pr, key):
        return None
    t = type_of(gd, pr, key)
    if t in want:
        return key
    if not t.startswith('LVL'):
        return None
    for s in subs_of(get_record(gd, pr, key), 'LVLO'):
        k = next((f['value'] for f in s['fields'] if f.get('code') == 'F'), '') if s['kind'] == 'struct' else ''
        got = _first_of(gd, pr, k, want, depth + 1)
        if got:
            return got
    return None


def source_of(gd, pr, rec, flag, depth=0):
    """The record a character takes `flag`'s parts from: its template (followed), else itself."""
    tp = one(rec, 'TPLT')
    if depth > 8 or not tp or not tp['value'] or not num(rec, 'ACBS', 'Template flags') & flag:
        return rec
    k = _first_of(gd, pr, tp['value'], (rec['type'],))
    return source_of(gd, pr, get_record(gd, pr, k), flag, depth + 1) if k else rec


def wearing(gd, pr, rec):
    """([{key, name, slots, model}] worn, slots taken): each piece of apparel in the order carried, unless a slot it covers is taken."""
    female = num(source_of(gd, pr, rec, actors.USE_TRAITS), 'ACBS', 'Flags') & actors.FEMALE
    src = source_of(gd, pr, rec, actors.USE_INVENTORY)
    worn, taken = [], 0
    for s in subs_of(src, 'CNTO'):
        k = next((f['value'] for f in s['fields'] if f.get('code') == 'F'), '') if s['kind'] == 'struct' else ''
        a = _first_of(gd, pr, k, ('ARMO',))
        if not a:
            continue
        ar = get_record(gd, pr, a)
        slots = num(ar, 'BMDT', 'Biped flags')
        model = recordio.field(ar, 'MOD3') if female else ''
        model = model or recordio.field(ar, 'MODL')
        if not slots or slots & taken or not model:
            continue
        worn.append({'key': a, 'name': recordio.field(ar, 'FULL') or recordio.field(ar, 'EDID'), 'slots': slots, 'model': model})
        taken |= slots
    return worn, taken


def look(gd, pr, key, draft=None):
    """{'parts': [{'model', 'tex'}], 'scale', 'wearing'} as the mod has it (or, given a draft, with its unsaved changes)."""
    rec = draft or get_record(gd, pr, key)
    if rec['type'] == 'CREA':
        src = source_of(gd, pr, rec, actors.USE_MODEL)
        folder = recordio.field(src, 'MODL').replace('/', '\\').rsplit('\\', 1)[0]
        names = recordio.field(src, 'NIFZ').split('\0')
        return {'parts': [{'model': 'meshes\\%s\\%s' % (folder, n), 'tex': ''} for n in names if n],
                'scale': num(rec, 'BNAM', 'Scale', 1.0) or 1.0, 'wearing': []}
    traits = source_of(gd, pr, rec, actors.USE_TRAITS)
    female = bool(num(traits, 'ACBS', 'Flags') & actors.FEMALE)
    worn, taken = wearing(gd, pr, rec)
    race = recordio.field(traits, 'RNAM')
    rp = actors._race_parts(gd, gd.from_key(race), female) if race and not race.startswith('+') and exists(gd, pr, race) else {}
    out = []
    for idx, slot in ((0, actors.BODY), (1, actors.LHAND), (2, actors.RHAND)):
        m, tex = rp.get(('body', idx), ('', ''))
        if m and not taken & slot:
            out.append({'model': 'meshes\\' + m, 'tex': tex and 'textures\\' + tex})
    if not taken & actors.HEAD:
        for idx in (0, 2, 6, 7):
            m, tex = rp.get(('head', idx), ('', ''))
            if m:
                out.append({'model': 'meshes\\' + m, 'tex': tex and 'textures\\' + tex if idx == 0 else ''})
        hair = recordio.field(traits, 'HNAM')
        if hair and exists(gd, pr, hair) and not taken & (actors.HAIR | actors.HAT):
            hm = recordio.field(get_record(gd, pr, hair), 'MODL')
            if hm:
                out.append({'model': 'meshes\\' + hm, 'tex': ''})
    out += [{'model': 'meshes\\' + w['model'], 'tex': ''} for w in worn]
    return {'parts': out, 'scale': num(rec, 'NAM6', 'Height', 1.0) or 1.0, 'wearing': [{'key': w['key'], 'name': w['name']} for w in worn]}


# ---------- faces ----------

def _face_file(gd, key):
    """The painted face texture the game keeps for a character, if any: textures\\characters\\facemods\\<file>\\<ID>_0.dds."""
    fid = gd.from_key(key)
    return 'textures\\characters\\facemods\\%s\\%08x_0.dds' % (gd.names[fid >> 24], fid & 0xFFFFFF)


def has_face_file(gd, key):
    return not key.startswith('+') and bool(gd.find_file(_face_file(gd, key)))


def copy_face(gd, pr, body):
    """A draft record with another character's face: its FaceGen numbers exactly, its hair, eyes and head parts. Only the
    draft changes: it's kept when the page saves. Face numbers name no forms, so they copy as they are."""
    rec = json.loads(json.dumps(body['record']))
    src = get_record(gd, pr, body['from'])
    src = source_of(gd, pr, src, actors.USE_TRAITS)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in FACE_TAGS]
    for s in src['subs']:
        if s['tag'] in FACE_TAGS:
            insert(rec, json.loads(json.dumps(s)))
    rec['face_race'] = recordio.field(src, 'RNAM')
    rec['face_female'] = bool(num(src, 'ACBS', 'Flags') & actors.FEMALE)
    rec['face_from'] = body['from']
    return {'record': rec, 'links': {k: label(gd, pr, k) for k in recordio.links(rec)}, 'warnings': warnings(gd, pr, body.get('key', ''), rec)}


def warnings(gd, pr, key, rec):
    """What will look wrong in game, in plain words."""
    out = []
    if rec['type'] != 'NPC_':
        return out
    tflags = num(rec, 'ACBS', 'Template flags')
    uses_traits = bool(tflags & actors.USE_TRAITS and one(rec, 'TPLT') and one(rec, 'TPLT')['value'])
    race, female = recordio.field(rec, 'RNAM'), bool(num(rec, 'ACBS', 'Flags') & actors.FEMALE)
    game = None
    if key and not key.startswith('+'):
        try:
            game = recordio.load(gd, gd.from_key(key))
        except (KeyError, ValueError):
            game = None
    if uses_traits:
        out.append('Race, sex and face come from the template, so what\'s set for them here doesn\'t show. Untick Traits under Template to set them here.')
        return out
    face_race = rec.get('face_race')
    if face_race is None and game:
        face_race = recordio.field(game, 'RNAM')
    elif face_race is None and rec.get('copied_from'):
        try:
            origin = source_of(gd, pr, get_record(gd, pr, rec['copied_from']), actors.USE_TRAITS)
            face_race = recordio.field(origin, 'RNAM')
        except (KeyError, ValueError):
            pass
    if face_race and race and face_race != race:
        out.append('Race changed: this face was made for %s, and is now on %s. Face numbers mean different things on different heads, so it will look wrong, '
                   'and the skin may not match the body. Pick a preset of this race, or copy a face from someone of this race.'
                   % (label_name(gd, pr, face_race), label_name(gd, pr, race)))
    if 'face_female' in rec and rec['face_female'] != female:
        out.append('This face came from a %s, and this character is a %s: the head mesh differs, so it will look wrong.'
                   % ('woman' if rec['face_female'] else 'man', 'woman' if female else 'man'))
    if key.startswith('+'):
        out.append('New character: the game keeps a painted face file for each of its own characters (named after the record\'s ID), and yours has none. '
                   'FOLab can\'t make that file yet, so the face may come out dark or not match the neck in game. A hat or helmet hides it; '
                   'the Face export in the GECK can make the file.')
    elif game:
        changed = any(json.dumps([s['value'] for s in subs_of(rec, t)]) != json.dumps([s['value'] for s in subs_of(game, t)]) for t in ('FGGS', 'FGGA', 'FGTS'))
        if changed or race != recordio.field(game, 'RNAM') or female != bool(num(game, 'ACBS', 'Flags') & actors.FEMALE):
            out.append('The game\'s painted face file for this character was made for its old face. Changing the face or race leaves that file in place, so the '
                       'skin colours and the new shape won\'t match in game.')
    return out


def label(gd, pr, key):
    if key == PLAYER:
        return 'Player'
    rec = pr.records.get(key) if pr else None
    if rec:
        e, n, t = recordio.field(rec, 'EDID'), recordio.field(rec, 'FULL'), rec['type']
    else:
        try:
            fid = gd.from_key(key)
        except (ValueError, KeyError):
            return key
        if fid not in gd.forms:
            return key
        f = gd.fields(fid)
        e, n, t = tes4.zstr(f.get('EDID', b'')), tes4.zstr(f.get('FULL', b'')), gd.forms[fid][1].tag
    return '%s%s (%s)' % (e or key, ' — ' + n if n and n != e else '', t)


def label_name(gd, pr, key):
    return label(gd, pr, key).split(' (')[0].split(' — ')[-1]


# ---------- one character, with what the page says about it ----------

def info(gd, pr, br, key):
    """The record as Browse has it, with what it wears, what will look wrong, where its traits come from."""
    d = br.record(key)
    rec = d['record']
    if PLAYER in d['links']:
        d['links'][PLAYER] = 'Player'
    if rec['type'] in ('NPC_', 'CREA'):
        d['look'] = look(gd, pr, key)
        d['warnings'] = warnings(gd, pr, key, rec)
        d['facefile'] = rec['type'] == 'NPC_' and has_face_file(gd, key)
        # (the template's name, and what's carried by it, when the inventory is the template's)
        src = source_of(gd, pr, rec, actors.USE_INVENTORY)
        if src is not rec:
            d['inherited'] = [{'name': label_name(gd, pr, k), 'count': next((f['value'] for f in s['fields'] if f.get('name') == 'Count'), 1)}
                              for s in subs_of(src, 'CNTO') for k in [next((f['value'] for f in s['fields'] if f.get('code') == 'F'), '')] if k]
    return d


# ---------- AI packages ----------

def set_place(rec, kind, target, radius, tag='PLDT'):
    """A package's location, as the kind says (a link for 0, 1 and 4; a plain number for the rest)."""
    is_form = kind in (0, 1, 4)
    fields = [{'name': 'Type', 'code': 'i', 'value': kind},
              {'name': 'Target', 'code': 'F', 'value': target or ''} if is_form else {'name': 'Value', 'code': 'I', 'value': int(target or 0)},
              {'name': 'Radius', 'code': 'i', 'value': int(radius)}]
    s = one(rec, tag)
    if s:
        s.update(kind='struct', fields=fields, label='Location')
        s.pop('value', None)
    else:
        insert(rec, {'tag': tag, 'label': 'Location', 'kind': 'struct', 'fields': fields})


def new_package(gd, pr, br, template, name=None, opts=None):
    """A package record from one of the game's own: (its record), not yet in the mod."""
    row = next(p for p in PACKAGES if p[0] == template)
    fid = _find(gd, 'PACK', row[1])
    if fid is None:
        raise ValueError('The game has no package called ' + row[1])
    rec = recordio.load(gd, fid)
    o = dict(row[4], **(opts or {}))
    stem = ''.join(w[0].upper() + w[1:] for w in ''.join(c if c.isalnum() else ' ' for c in (name or row[2])).split())
    recordio.set_field(rec, 'EDID', unique_edid(br, pr, 'FOLab' + (stem or 'Package')), label='Editor ID')
    if 'radius' in o or 'where' in o:
        cur = one(rec, 'PLDT')
        kind = o.get('where', num(rec, 'PLDT', 'Type', 3) if cur else 3)
        set_place(rec, kind, o.get('target', ''), o.get('radius', num(rec, 'PLDT', 'Radius', 0)))
    if 'time' in o:
        set_num(rec, 'PSDT', 'Time', o['time'])
        set_num(rec, 'PSDT', 'Duration', o['hours'])
    rec['src'] = rec.get('src') or ''
    return rec


def package_templates():
    return [{'id': p[0], 'label': p[2], 'note': p[3]} for p in PACKAGES]


# ---------- factions ----------

def new_faction(gd, pr, br, edit, body):
    name = (body.get('name') or '').strip() or 'New faction'
    stem = ''.join(w.capitalize() for w in ''.join(c if c.isalnum() else ' ' for c in name).split()) or 'Faction'
    rec = {'type': 'FACT', 'flags': 0, 'src': '', 'subs': [
        {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': unique_edid(br, pr, 'FOLab' + stem + 'Faction')},
        {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name},
        {'tag': 'DATA', 'label': 'Flags', 'kind': 'struct', 'fields': [{'name': 'Flags', 'code': 'B', 'value': 0}, {'name': 'Flags 2', 'code': 'B', 'value': 0}, {'pad': '0000'}]}]}
    return edit('New faction ' + name, [{'op': 'record_new', 'record': rec}])


def members(gd, br, key, limit=60):
    """Who belongs to a faction: the game's characters that name it (from the Browse index)."""
    u = br.where_used(key, limit=400) if not key.startswith('+') else {'rows': []}
    if u.get('busy'):
        return {'busy': True}
    rows = [r for r in u.get('rows', []) if r['label'].endswith(('(NPC_)', '(CREA)'))]
    return {'rows': rows[:limit], 'total': len(rows)}


# ---------- routes ----------

def get(path, q, gd, pr, br):
    if path == '/api/char/options':
        return options(gd, pr)
    if path == '/api/char/templates':
        return {'actors': templates(gd), 'packages': package_templates()}
    if path == '/api/char/info':
        return info(gd, pr, br, q['key'])
    if path == '/api/char/members':
        return members(gd, br, q['key'])
    if path == '/api/char/populate/place':
        if 'world' in q:              # (outside: the square the view is over)
            c = gd.grid(gd.from_key(q['world'])).get((int(q['x']), int(q['y'])))
            if c is None:
                return {'none': True}
            return populate.place_info(gd, pr, gd.key(c))
        return populate.place_info(gd, pr, q['cell'])
    raise FileNotFoundError(path)


def post(path, body, gd, pr, br, edit):
    if path == '/api/char/new':
        return new_character(gd, pr, br, edit, body)
    if path == '/api/char/look':
        return look(gd, pr, body['key'], body.get('record'))
    if path == '/api/char/face':
        return copy_face(gd, pr, body)
    if path == '/api/char/warnings':
        return {'warnings': warnings(gd, pr, body.get('key', ''), body['record'])}
    if path == '/api/char/package/new':
        rec = new_package(gd, pr, br, body['template'], body.get('name'))
        return edit('New package ' + recordio.field(rec, 'EDID'), [{'op': 'record_new', 'record': rec}])
    if path == '/api/char/faction/new':
        return new_faction(gd, pr, br, edit, body)
    if path == '/api/char/populate/plan':
        return populate.plan(gd, pr, br, body)
    if path == '/api/char/populate/apply':
        return populate.apply(gd, pr, br, edit, body)
    raise FileNotFoundError(path)
