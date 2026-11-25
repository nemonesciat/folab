"""Terminals of the mod's own, written from plain text (docs/waikiki-speech-science.md: pick 1; the user, 25 Nov 2026: "many
more doors locked behind terminals, and terminals that hold information").

A terminal (TERM) is laid out as the game's own (read over FalloutNV.esm's 344): EDID, OBND, FULL, MODL, DESC (the welcome
text at the top of the screen), SNAM (the hum), PNAM (a password note: carrying it skips the hacking), DNAM (difficulty
0 very easy .. 4 very hard, flags: 0x02 not locked, server type), then each menu item: ITXT (the words on the button),
RNAM (the text shown when picked), ANAM (flags), INAM (a note shown, and added to the Pip-Boy), TNAM (a sub-menu: another
TERM), SCHR/SCDA/SCTX/SCRO (its result script), CTDA (when it shows). nv-rs ports the game's terminal menu as it is
(computersmenu.rs: an item runs its result script, shows its result text, adds its note).

A lock a terminal releases is the item's own result script, `<ref>.Unlock`, as the game's terminals do. FOLab Skill
Proof.esp showed it in nv-rs-newest (25 Nov 2026: the bathroom door opened). A release by note watched by a quest script
(GetHasNote) did not unlock in that run (cause not found), so there is no such route.
Refs a script names must be persistent and have an editor ID (`extra: {'persistent': True, 'edid': ...}`).

The plain text a terminal is written in (`parse`):

    Terminal: FOLabProofTerminal          (its editor ID)
    Name: Barracks Lock Control
    Model: desk                           (desk, wall, or a model path)
    Lock: very easy                       (very easy, easy, average, hard, very hard; or none)
    Password: FOLabProofPassword          (a note's editor ID: the game's, or one made by a `Note:` here, above the items)
    Note: FOLabProofPassword | Password   (a note of the terminal's own, not shown by an item: its text indented under it)
      The password is SURF.
    Welcome:
      ROBCO INDUSTRIES UNIFIED OPERATING SYSTEM
      ...
    == Release lock: bathroom door        (a menu item, its words)
    Unlocks: FOLabProofDoorAREF           (its result script unlocks it; 'by script' may be written after)
    Says: Bathroom door released.         (the result text; several lines after 'Says:' on their own)
    == Read the log
    Note: FOLabProofLog | Barracks log    (a note of its own: editor ID | its title, the text indented under it)
      Day one. Nothing to report.
    == More                               (a sub-menu: its items follow, indented one '=' more)
    === Back                              (an item in the sub-menu)

`plan(text)` reads it into a spec; `records(gd, forms, spec)` makes the TERM, its notes and any sub-menus as records; `ops`
puts them in a mod as record_new ops."""
import re
import struct

import recordio
import scriptc

DIFFICULTY = {'very easy': 0, 'easy': 1, 'average': 2, 'hard': 3, 'very hard': 4}
SCIENCE_NEEDED = {0: 0, 1: 25, 2: 50, 3: 75, 4: 100}         # (the hacking screen's rule: the skill a difficulty asks)
NOT_LOCKED = 0x02
SERVER = 3                                                 # (the game's commonest server type for a plain terminal)
MODELS = {'desk': 'Terminals\\TerminalDesk01.NIF', 'wall': 'Terminals\\Terminal01.NIF'}
HUM = 'FalloutNV.esm:018EC0'                               # (the terminals' sound, 267 of the game's 344)
LIKE = 'CampSearchlightNCRStorage'                         # (a game desk terminal: its bounds are taken for a desk)
WAYS = ('script',)          # (the note route, a quest watching GetHasNote, didn't unlock in nv-rs: FOLab Skill Proof, 25 Nov)


class TermError(ValueError):
    pass


# ---------- the plain text ----------
def plan(text):
    """The plain text read into {'edid', 'name', 'model', 'lock', 'password', 'welcome', 'items': [...], 'notes': [...]}."""
    spec = {'edid': '', 'name': '', 'model': 'desk', 'lock': None, 'password': '', 'welcome': '', 'items': [], 'notes': []}
    stack = [(0, spec['items'])]
    item, field = None, None
    for n, raw in enumerate(text.replace('\r\n', '\n').split('\n'), 1):
        line = raw.rstrip()
        if not line.strip():
            if field is not None:
                field[0][field[1]] += '\n'
            continue
        m = re.match(r'\s*(==+)\s*(.+)$', line)
        if m:
            depth = len(m.group(1)) - 2
            while stack and stack[-1][0] > depth:
                stack.pop()
            if not stack or stack[-1][0] != depth:
                if not item or depth != stack[-1][0] + 1:
                    raise TermError('line %d: a sub-menu item needs an item above it to hang from' % n)
                item.setdefault('menu', [])
                stack.append((depth, item['menu']))
            item = {'text': m.group(2).strip(), 'says': '', 'unlocks': [], 'note': '', 'script': ''}
            stack[-1][1].append(item)
            field = None
            continue
        if raw[:1] in (' ', '\t') and field is not None:
            d, k = field
            d[k] += ('\n' if d[k] and not d[k].endswith('\n') else '') + line.strip()
            continue
        m = re.match(r'\s*([A-Za-z]+)\s*:\s*(.*)$', line)
        if not m:
            raise TermError('line %d: expected "Name: value" or "== item": %r' % (n, line))
        key, value = m.group(1).lower(), m.group(2).strip()
        field = None
        if item is None:
            if key == 'terminal':
                spec['edid'] = value
            elif key == 'name':
                spec['name'] = value
            elif key == 'model':
                spec['model'] = value
            elif key == 'lock':
                if value.lower() in ('none', 'no', 'open', ''):
                    spec['lock'] = None
                elif value.lower() in DIFFICULTY:
                    spec['lock'] = value.lower()
                else:
                    raise TermError('line %d: lock is one of %s, or none' % (n, ', '.join(DIFFICULTY)))
            elif key == 'password':
                spec['password'] = value
            elif key == 'welcome':
                spec['welcome'] = value
                field = (spec, 'welcome')
            elif key == 'note':
                spec['notes'].append(_note_head(value, n))
                field = (spec['notes'][-1], 'text')
            else:
                raise TermError('line %d: %s is not a terminal setting' % (n, m.group(1)))
        else:
            if key == 'says':
                item['says'] = value
                field = (item, 'says')
            elif key == 'unlocks':
                m2 = re.match(r'(\S+)(?:\s+by\s+(\w+))?$', value)
                if not m2 or (m2.group(2) or 'script').lower() not in WAYS:
                    raise TermError('line %d: "Unlocks: <ref editor ID>" (a lock is released by the item script)' % n)
                item['unlocks'].append((m2.group(1), 'script'))
            elif key == 'note':
                note = _note_head(value, n)
                spec['notes'].append(note)
                item['note'] = note['edid']
                field = (note, 'text')
            elif key == 'script':
                item['script'] = value
                field = (item, 'script')
            elif key == 'shows':
                item['note'] = value                 # (a note made elsewhere, or the game's)
            else:
                raise TermError('line %d: %s is not a menu item setting' % (n, m.group(1)))
    if not spec['edid']:
        raise TermError('the terminal needs "Terminal: <editor ID>"')
    if not spec['items']:
        raise TermError('the terminal needs at least one "== item"')
    for d in [spec] + spec['notes'] + list(_items(spec['items'])):
        for k in ('welcome', 'says', 'text', 'script'):
            if isinstance(d.get(k), str):
                d[k] = d[k].strip('\n')
    return spec


def _note_head(value, n):
    parts = [p.strip() for p in value.split('|')]
    if not parts[0]:
        raise TermError('line %d: "Note: <editor ID> | <title>"' % n)
    return {'edid': parts[0], 'name': parts[1] if len(parts) > 1 else '', 'text': ''}


def _items(items):
    for it in items:
        yield it
        yield from _items(it.get('menu') or ())


def unlocks(spec):
    """[ref editor ID] of every lock the terminal's items release."""
    return [ref for it in _items(spec['items']) for ref, _way in it['unlocks']]


# ---------- records ----------
def _z(tag, label, value):
    return {'tag': tag, 'label': label, 'kind': 'z', 'value': value}


def _crlf(text):
    return (text or '').replace('\r\n', '\n').replace('\n', '\r\n')


def note_record(edid, name, text):
    """A text note (DATA type 1), laid out as the game's terminal notes: no model, bounds of nought."""
    subs = [_z('EDID', 'Editor ID', edid),
            {'tag': 'OBND', 'label': 'Bounds', 'kind': 'struct', 'fields': [{'name': n, 'code': 'h', 'value': 0} for n in ('X1', 'Y1', 'Z1', 'X2', 'Y2', 'Z2')]}]
    if name:
        subs.append(_z('FULL', 'Name', name))
    subs.append({'tag': 'DATA', 'label': 'Data', 'kind': 'struct', 'fields': [{'name': 'Type', 'code': 'B', 'value': 1}]})
    subs.append({'tag': 'TNAM', 'label': 'TNAM', 'kind': 'raw', 'value': (_crlf(text).encode('cp1252', 'replace') + b'\0').hex()})
    return {'type': 'NOTE', 'flags': 0, 'src': '', 'subs': subs}


def _script_parts(source, forms):
    import api_quests
    import questrec
    if not (source or '').strip():
        return questrec.empty_parts()
    try:
        return api_quests.compile_parts(source, forms)
    except scriptc.CompileError as e:
        raise TermError('a menu item\'s script, line %s: %s' % (e.line, e.message))


def item_source(it):
    """A menu item's result script: its own lines, then `<ref>.Unlock` for each lock it releases by script."""
    lines = [l for l in (it.get('script') or '').split('\n') if l.strip()]
    lines += ['%s.Unlock' % ref for ref, _way in it['unlocks']]
    return '\n'.join(lines)


def records(gd, forms, spec, keys=None):
    """{'terminal': TERM, 'menus': [TERM of each sub-menu], 'notes': [NOTE]} for a spec. keys: {editor ID: key} of records
    made with it (sub-menus, notes), so links between them can be written; forms: what the scripts are compiled against
    (api_quests.ModForms, with stand-ins for refs a script names)."""
    keys = dict(keys or {})
    notes = [note_record(n['edid'], n['name'], n['text']) for n in spec['notes']]
    menus = []

    def link(edid):
        if not edid:
            return ''
        if edid in keys:
            return keys[edid]
        f = forms.find_edid(edid) if forms else None
        if f is None:
            raise TermError('%s: no such record (a note or sub-menu is named by its editor ID)' % edid)
        return forms.key_of(f.fid)

    def term(edid, name, welcome, lock, password, items, model):
        like = _like(gd)
        subs = [_z('EDID', 'Editor ID', edid)]
        subs.append(next(s for s in like['subs'] if s['tag'] == 'OBND'))
        subs.append(_z('FULL', 'Name', name or 'Terminal'))
        subs.append(_z('MODL', 'Model', MODELS.get(model, model)))
        subs.append(_z('DESC', 'Description', _crlf(welcome)))
        subs.append({'tag': 'SNAM', 'label': 'Sound', 'kind': 'F', 'value': HUM})
        if password:
            subs.append({'tag': 'PNAM', 'label': 'Password note', 'kind': 'F', 'value': link(password)})
        subs.append({'tag': 'DNAM', 'label': 'Data', 'kind': 'struct', 'fields': [
            {'name': 'Difficulty', 'code': 'B', 'value': DIFFICULTY.get(lock, 0)},
            {'name': 'Flags', 'code': 'B', 'value': 0 if lock else NOT_LOCKED},
            {'name': 'Server type', 'code': 'B', 'value': SERVER}, {'pad': '00'}]})
        for n, it in enumerate(items):
            subs.append(_z('ITXT', 'Menu item text', it['text']))
            subs.append(_z('RNAM', 'Result text', _crlf(it.get('says') or '')))
            subs.append({'tag': 'ANAM', 'label': 'Menu item flags', 'kind': 'struct', 'fields': [{'name': 'Flags', 'code': 'B', 'value': 0}]})
            note = it['note']
            if note:
                subs.append({'tag': 'INAM', 'label': 'Display note', 'kind': 'F', 'value': link(note)})
            if it.get('menu'):
                sub_edid = '%sMenu%d' % (edid, n + 1)
                menus.append(term(sub_edid, name, welcome, None, '', it['menu'], model))
                subs.append({'tag': 'TNAM', 'label': 'Sub-menu', 'kind': 'F', 'value': link(sub_edid)})
            subs += _script_parts(item_source(it), forms)
        return {'type': 'TERM', 'flags': 0, 'src': '', 'subs': subs}

    # (sub-menus and notes are named before they're made: their keys come first)
    for it_n, sub_edid in _menu_edids(spec):
        keys.setdefault(sub_edid, None)
    unknown = [e for e, k in keys.items() if k is None]
    if unknown:
        raise TermError('keys for %s were not given (reserve them first: `edids(spec)`)' % ', '.join(unknown))
    main = term(spec['edid'], spec['name'], spec['welcome'], spec['lock'], spec['password'], spec['items'], spec['model'])
    return {'terminal': main, 'menus': menus, 'notes': notes}


def _menu_edids(spec):
    out = []

    def walk(edid, items):
        for n, it in enumerate(items):
            if it.get('menu'):
                sub = '%sMenu%d' % (edid, n + 1)
                out.append((n, sub))
                walk(sub, it['menu'])
    walk(spec['edid'], spec['items'])
    return out


def edids(spec):
    """Editor IDs of every record a spec makes, in the order `ops` makes them: notes, sub-menus (deepest first), the terminal."""
    notes = [n['edid'] for n in spec['notes']]
    return notes + [e for _n, e in reversed(_menu_edids(spec))] + [spec['edid']]


_LIKE = {}


def _like(gd):
    got = _LIKE.get(id(gd))
    if got is None:
        f = next(f for f, (i, r) in gd.forms.items() if r.tag == 'TERM' and gd.edid(f) == LIKE)
        got = _LIKE[id(gd)] = recordio.load(gd, f)
    return got


def mod_forms(gd, pr, extra=None):
    """api_quests.ModForms with the mod's named refs (a ref's change with an 'edid') as persistent stand-ins, so a script
    can name them; extra: more {key: record} made with it."""
    import api_quests as aq
    import tes4
    forms = aq.ModForms(gd, pr)
    for c in (pr.cells.values() if pr else ()):
        for key, r in (c.get('refs') or {}).items():
            if r.get('edid') and not r.get('removed'):
                forms.own[r['edid'].lower()] = (key, {'type': 'REFR', 'flags': tes4.PERSISTENT,
                                                      'subs': [_z('EDID', 'Editor ID', r['edid'])]})
    for key, rec in (extra or {}).items():
        e = recordio.field(rec, 'EDID')
        if e:
            forms.own[e.lower()] = (key, rec)
    return forms


def ops(gd, pr, spec, forms=None):
    """(ops, {editor ID: key}) putting a terminal's records in the mod: record_new each, keys reserved first so they name
    each other. forms: api_quests.ModForms for its scripts (made here if not given)."""
    import api_quests as aq
    forms = forms or mod_forms(gd, pr)
    have = {e: forms.own[e.lower()][0] for e in edids(spec) if e.lower() in forms.own}   # (a note the mod has already)
    if spec['edid'] in have:
        raise TermError('the mod already has %s' % spec['edid'])
    order = [e for e in edids(spec) if e not in have]
    keys = dict(zip(order, aq._reserve(pr, len(order))))
    made = records(gd, forms, spec, dict(have, **keys))
    by_edid = {recordio.field(r, 'EDID'): r for r in made['notes'] + made['menus'] + [made['terminal']]}
    return [{'op': 'record_new', 'record': by_edid[e]} for e in order], dict(have, **keys)


def science_needed(spec):
    """The Science skill the hacking screen asks of this terminal (0 when it isn't locked)."""
    return SCIENCE_NEEDED[DIFFICULTY[spec['lock']]] if spec.get('lock') else 0
