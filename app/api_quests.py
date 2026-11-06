"""The Quests page's routes: quests, stages and objectives in plain fields, result scripts compiled as they're saved, a
character's conversation to read and follow, the board, and the check.

server.py hands over anything under /api/quest and /api/dlg:

    get(path, q, gd, pr, br)                the answer, or None for 'no such route'
    post(path, body, gd, pr, br, edit)      edit(label, ops) makes the change (one Undo step)

Records stay what they are everywhere else (recordio.py), kept in the mod under their keys; a line also says which topic
it's in ('topic'), and where among the topic's lines it stands ('seq', when it's been moved)."""
import json
import re
import struct

import questrec as qr
import recordio
import schema
import scriptc
import tes4

OWN_FID = 0xFD000000                    # (the mod's own forms, as the compiler sees them)
LONG_LINE = 200                         # the game's own lines rarely pass this; longer ones are hard to read as subtitles
COMMON_FUNCTIONS = ['GetIsID', 'GetStage', 'GetStageDone', 'GetQuestVariable', 'GetGlobalValue', 'GetItemCount', 'GetIsSex', 'GetPCIsSex',
                    'GetIsRace', 'GetPCIsRace', 'GetInFaction', 'GetFactionRank', 'GetActorValue', 'GetDead', 'GetDisposition', 'GetIsClass',
                    'GetIsVoiceType', 'GetRandomPercent', 'GetLevel', 'GetInCell', 'HasPerk', 'GetIsReference', 'GetDistance', 'GetCurrentTime', 'IsInCombat']
RUN_ON = ['the speaker', 'the player', 'a chosen thing', 'their combat target', 'their linked ref']


# ---------- the compiler's view of the mod ----------
class ModForms:
    """GameForms with the mod's own records laid over: forms found by editor ID, the mod's first. Each own form gets a stand-in
    form ID (OWN_FID | object ID), which key_of turns back into its key."""

    def __init__(self, gd, pr):
        self.gd, self.pr = gd, pr
        self.game = scriptc.GameForms(gd)
        self.own = {}
        for key, rec in (pr.records if pr else {}).items():
            e = recordio.field(rec, 'EDID')
            if e and key.startswith('+'):
                self.own[e.lower()] = (key, rec)

    def key_of(self, fid):
        return '+%06X' % (fid & 0xFFFFFF) if fid >> 24 == OWN_FID >> 24 else self.gd.key(fid)

    def find_edid(self, name):
        hit = self.own.get(name.lower())
        if hit:
            persistent = bool(hit[1].get('flags', 0) & tes4.PERSISTENT)
            return scriptc.Form(self, OWN_FID | int(hit[0][1:], 16), hit[1]['type'], persistent, None, hit[1])
        return self.game.find_edid(name)

    def find(self, name):
        return self.find_edid(name) or self.game.find(name)

    def script_vars(self, form):
        scri = recordio.field(form.rec, 'SCRI')
        if not scri:
            return None
        if not scri.startswith('+'):
            return self.game.vars_of(self.gd.from_key(scri))
        got, last = {}, None
        for s in (self.pr.records.get(scri) or {'subs': ()})['subs']:
            if s['tag'] == 'SLSD':
                last = s['fields']
            elif s['tag'] == 'SCVR' and last:
                num = next(f['value'] for f in last if f.get('name') == 'Index')
                flag = next(f['value'] for f in last if f.get('name') == 'Flags')
                got[s['value'].lower()] = (num, bool(flag))
                last = None
        return got

    def message_text(self, form):
        return recordio.field(form.rec, 'DESC').encode('cp1252', 'replace')

    def is_interior(self, form):
        return form.tag == 'CELL'

    def is_map_marker(self, form):
        return False


def compile_parts(source, forms, old=None):
    """A result script's subrecords, decoded as a mod keeps them, form links as keys. old: its parts before, so variables keep
    their numbers. Raises scriptc.CompileError."""
    if not source.strip():
        return qr.empty_parts()
    old_vars, last = [], None
    for s in old or ():
        if s['tag'] == 'SLSD':
            last = s
        elif s['tag'] == 'SCVR' and last:
            old_vars.append((qr._f(last, 'Index'), s['value'], bool(qr._f(last, 'Flags'))))
            last = None
    c = scriptc.compile_script(source, forms, scriptc.SCRIPT_OBJECT, old_vars=old_vars, partial=True, strict=True)
    parts = []
    for tag, data in c.subrecords():
        s = schema.decode_sub('INFO', tag, data)
        if tag == 'SCRO':
            s['value'] = forms.key_of(struct.unpack('<I', data)[0])
        parts.append(s)
    return parts


def _norm(text):
    return (text or '').replace('\r\n', '\n').replace('\r', '\n')


def compile_one(script, forms, where, errors):
    """A plain result script with its parts brought up to date with its source. A source nobody changed keeps its bytes."""
    if script is None:
        return None
    if _norm(script.get('source')) == _norm(qr.script_plain(script.get('parts') or []).get('source')) and script.get('parts'):
        return script
    try:
        return {'source': script.get('source', ''), 'parts': compile_parts(script.get('source', ''), forms, script.get('parts'))}
    except scriptc.CompileError as e:
        errors.append({'where': where, 'line': e.line, 'message': e.message})
        return script


def compile_quest(q, forms):
    errors = []
    for st in q.get('stages', ()):
        for n, e in enumerate(st.get('entries', ())):
            if e.get('script'):
                e['script'] = compile_one(e['script'], forms, 'Stage %s%s' % (st['index'], ' entry %d' % (n + 1) if n else ''), errors)
            elif not e.get('no_flags'):
                e['script'] = qr.empty_script()
    return errors


def compile_line(l, forms):
    errors = []
    l['begin'] = compile_one(l.get('begin') or qr.empty_script(), forms, 'Before the line', errors)
    l['end'] = compile_one(l.get('end') or qr.empty_script(), forms, 'After the line', errors)
    return errors


# ---------- reading ----------
def record(gd, pr, key):
    mine = pr.records.get(key) if pr else None
    if mine:
        return mine
    return recordio.load(gd, gd.from_key(key))


def state_of(gd, pr, key):
    if key.startswith('+'):
        return 'new'
    return 'changed' if pr and key in pr.records else ''


def short(gd, pr, key):
    """A form's name for a person: its name if it has one, else its editor ID."""
    if not key:
        return ''
    if key == 'FalloutNV.esm:000014' or key == 'FalloutNV.esm:000007':
        return 'Player'
    rec = pr.records.get(key) if pr else None
    if rec:
        return recordio.field(rec, 'FULL') or recordio.field(rec, 'EDID') or key
    try:
        fid = gd.from_key(key)
        if fid not in gd.forms:
            return key
        f = gd.fields(fid)
        return tes4.zstr(f.get('FULL', b'')) or tes4.zstr(f.get('EDID', b'')) or key
    except (ValueError, KeyError):
        return key


def edid_of(gd, pr, key):
    rec = pr.records.get(key) if pr else None
    if rec:
        return recordio.field(rec, 'EDID')
    try:
        return gd.edid(gd.from_key(key))
    except (ValueError, KeyError):
        return ''


def _fn_entry(fn):
    return scriptc.tables().by_code.get(0x1000 + int(fn))


def quest_variable_name(gd, pr, quest, n):
    try:
        rec = record(gd, pr, quest)
        scri = recordio.field(rec, 'SCRI')
        if scri.startswith('+'):
            for name, (num, _i) in (ModForms(gd, pr).script_vars(scriptc.Form(None, 0, 'QUST', False, None, rec)) or {}).items():
                if num == n:
                    return name
        elif scri:
            for name, (num, _i) in scriptc.GameForms(gd).vars_of(gd.from_key(scri)).items():
                if num == n:
                    return name
    except Exception:
        pass
    return 'variable %d' % n


def _num(v):
    v = round(float(v), 4)
    return str(int(v)) if v == int(v) else str(v)


def condition_words(gd, pr, c):
    """One condition in plain words: 'Speaker is Sunny Smiles', 'Quest X has reached stage 20'."""
    e = _fn_entry(c['fn'])
    name = e['name'] if e else 'Function %s' % c['fn']
    who = {0: 'The speaker', 1: 'The player', 2: short(gd, pr, c.get('ref')) or 'The thing', 3: 'Their combat target', 4: 'Their linked ref'}.get(c.get('run', 0), 'The speaker')
    if c.get('use_target') and not c.get('run'):
        who = 'The player'
    p1, p2 = c.get('p1'), c.get('p2')
    val = short(gd, pr, c['global']) if c.get('global') else _num(c.get('value', 0))
    op = c['op']
    opw = {'=': 'is', '!=': 'is not', '>': 'is over', '>=': 'is at least', '<': 'is under', '<=': 'is at most'}.get(op, str(op))
    yes = not c.get('global') and ((op == '=' and float(c.get('value', 0)) == 1) or (op == '!=' and float(c.get('value', 0)) == 0) or (op == '>' and float(c.get('value', 0)) == 0) or (op == '>=' and float(c.get('value', 0)) == 1))
    no = not c.get('global') and ((op == '=' and float(c.get('value', 0)) == 0) or (op == '!=' and float(c.get('value', 0)) == 1) or (op == '<' and float(c.get('value', 0)) == 1))
    truth = 'yes' if yes else 'no' if no else None

    def boolean(pos, neg):
        return pos if truth == 'yes' else neg if truth == 'no' else '%s: %s %s' % (pos, opw, val)
    label = (short(gd, pr, p1) or '(nothing picked)') if isinstance(p1, str) else p1
    tab = scriptc.tables().lists
    params = (e or {}).get('params', [])
    if name == 'GetIsID':
        return boolean('%s is %s' % (who, label), '%s isn\'t %s' % (who, label))
    if name == 'GetStage':
        return '%s: stage %s %s' % (label, opw, val)
    if name == 'GetStageDone':
        return boolean('%s: stage %s has been reached' % (label, p2), '%s: stage %s hasn\'t been reached' % (label, p2))
    if name == 'GetObjectiveDisplayed':
        return boolean('%s: objective %s is showing' % (label, p2), '%s: objective %s isn\'t showing' % (label, p2))
    if name == 'GetObjectiveCompleted':
        return boolean('%s: objective %s is done' % (label, p2), '%s: objective %s isn\'t done' % (label, p2))
    if name == 'GetQuestCompleted':
        return boolean('%s is complete' % label, '%s isn\'t complete' % label)
    if name == 'GetQuestRunning':
        return boolean('%s is running' % label, '%s isn\'t running' % label)
    if name == 'GetQuestVariable':
        return '%s: %s %s %s' % (label, quest_variable_name(gd, pr, p1, p2), opw, val)
    if name == 'GetGlobalValue':
        return 'Global %s %s %s' % (label, opw, val)
    if name == 'GetItemCount':
        return boolean('%s carries %s' % (who, label), '%s carries no %s' % (who, label)) if truth or val == '0' else '%s carries %s %s of %s' % (who, opw, val, label)
    if name in ('GetIsSex', 'GetPCIsSex'):
        sex = 'female' if p1 == 1 else 'male'
        whom = 'The player' if name == 'GetPCIsSex' else who
        return boolean('%s is %s' % (whom, sex), '%s isn\'t %s' % (whom, sex))
    if name in ('GetIsRace', 'GetPCIsRace', 'GetIsClass', 'GetIsVoiceType', 'GetIsReference', 'GetIsCreature'):
        whom = 'The player' if name.startswith('GetPC') else who
        return boolean('%s is %s' % (whom, label), '%s isn\'t %s' % (whom, label))
    if name == 'GetInFaction':
        return boolean('%s is in %s' % (who, label), '%s isn\'t in %s' % (who, label))
    if name == 'GetFactionRank':
        return '%s: rank in %s %s %s' % (who, label, opw, val)
    if name == 'GetDead':
        return boolean('%s is dead' % who, '%s is alive' % who)
    if name == 'HasPerk':
        return boolean('%s has %s' % (who, label), '%s doesn\'t have %s' % (who, label))
    if name == 'GetRandomPercent':
        return 'Chance: a roll of 0-99 %s %s' % (opw, val)
    if name in ('GetActorValue', 'GetBaseActorValue', 'GetPermanentActorValue'):
        av = next((k for k, v in tab[5].items() if v == p1), 'value %s' % p1)
        return '%s: %s %s %s' % (who, av, opw, val)
    if name == 'GetDisposition':
        return '%s: disposition towards %s %s %s' % (who, label, opw, val)
    if name == 'GetLevel':
        return '%s: level %s %s' % (who, opw, val)
    if name == 'GetInCell':
        return boolean('%s is in %s' % (who, label), '%s isn\'t in %s' % (who, label))
    args = []
    for p, v in zip(params, (p1, p2)):
        args.append(short(gd, pr, v) if isinstance(v, str) else (next((k for k, x in tab[p[0]].items() if x == v), str(v)) if p[0] in tab else str(v)))
    return '%s: %s%s %s %s' % (who, name[3:] if name.startswith('Get') else name, ' (%s)' % ', '.join(args) if args else '', opw, val)


def conditions_words(gd, pr, conds):
    """[{'text', 'or': joins to the next with or}]"""
    return [{'text': condition_words(gd, pr, c), 'or': bool(c.get('or'))} for c in conds]


def script_summary(gd, pr, source):
    """What a script does to quests, in words a person reads: stages set, quests started."""
    fx = qr.script_effects(source)
    out = []
    for q, n in fx['sets']:
        out.append({'kind': 'stage', 'quest': q, 'stage': n, 'text': 'sets %s to stage %d' % (q, n)})
    for q, n, what, on in fx['objectives']:
        out.append({'kind': 'objective', 'quest': q, 'index': n, 'what': what, 'on': on,
                    'text': '%s objective %d of %s' % ({'displayed': 'shows' if on else 'hides', 'completed': 'completes' if on else 'un-completes'}[what], n, q)})
    for verb, q in fx['quests']:
        out.append({'kind': 'quest', 'verb': verb, 'quest': q, 'text': '%s %s' % (verb.replace('quest', '').strip(), q)})
    return out


def quest_view(gd, pr, key):
    rec = record(gd, pr, key)
    q = qr.quest_plain(json.loads(json.dumps(rec)))
    links = {}
    for k in recordio.links(rec):
        links[k] = short(gd, pr, k)
    for c in _all_conditions(q):
        c['words'] = condition_words(gd, pr, c)
    return {'key': key, 'quest': q, 'state': state_of(gd, pr, key), 'links': links, 'from': rec.get('src') or 'your mod', 'copied_from': rec.get('copied_from', '')}


def _all_conditions(q):
    out = list(q['conditions'])
    for st in q['stages']:
        for e in st['entries']:
            out += e['conditions']
    for o in q['objectives']:
        for t in o['targets']:
            out += t['conditions']
    return out


def _clean_conditions(obj):
    """words are for showing: they don't go in the record"""
    if isinstance(obj, dict):
        obj.pop('words', None)
        for v in obj.values():
            _clean_conditions(v)
    elif isinstance(obj, list):
        for v in obj:
            _clean_conditions(v)


def unique_edid(gd, pr, br, base):
    base = re.sub(r'[^A-Za-z0-9_]', '', base) or 'Thing'
    taken = set(getattr(br, 'edids', None) or {}) | {recordio.field(r, 'EDID').lower() for r in pr.records.values()}
    n, edid = 1, base
    game = scriptc.GameForms(gd)
    while edid.lower() in taken or game.find_edid(edid):
        n += 1
        edid = '%s%d' % (base, n)
    return edid


def list_quests(gd, pr, br, q=''):
    rows = br.records('QUST', q)
    for r in rows:
        r['mine'] = bool(r.get('state'))
    return rows


# ---------- changes to quests ----------
def new_quest(gd, pr, br, edit, body):
    name = body.get('name') or 'New Quest'
    edid = unique_edid(gd, pr, br, body.get('edid') or name)
    plain = {'edid': edid, 'name': name, 'flags': {'start_enabled': bool(body.get('start_enabled', True))}, 'priority': 50, 'delay': 5.0,
             'conditions': [], 'stages': [], 'objectives': []}
    return edit('New quest ' + name, [{'op': 'record_new', 'record': qr.quest_record(plain)}])


def copy_quest(gd, pr, br, edit, key):
    rec = json.loads(json.dumps(record(gd, pr, key)))
    base = recordio.field(rec, 'EDID') or 'Quest'
    recordio.set_field(rec, 'EDID', unique_edid(gd, pr, br, base + 'Copy'), label='Editor ID')
    rec['copied_from'] = rec.get('copied_from') or key
    return edit('Copy quest ' + base, [{'op': 'record_new', 'record': rec}])


def save_quest(gd, pr, edit, key, plain):
    _clean_conditions(plain)
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', plain.get('edid') or ''):
        raise ValueError('A quest\'s editor ID needs letters and numbers only, no spaces.')
    seen = set()
    for st in plain.get('stages', ()):
        st['index'] = int(st['index'])
        if st['index'] in seen:
            raise ValueError('There are two stages numbered %d.' % st['index'])
        seen.add(st['index'])
    plain['stages'] = sorted(plain.get('stages', ()), key=lambda s: s['index'])
    if plain.get('delay') is None and key.startswith('+'):
        plain['delay'] = 5.0
    forms = ModForms(gd, pr)
    errors = compile_quest(plain, forms)
    if errors:
        return {'errors': errors}
    old = pr.records.get(key)
    rec = qr.quest_record(plain)
    if old and old.get('copied_from'):
        rec['copied_from'] = old['copied_from']
    return edit('Edit quest ' + plain['edid'], [{'op': 'record', 'key': key, 'record': rec}])


# ---------- dialogue ----------
def lines_of_topic(gd, pr, topic):
    """Keys of a topic's lines in the game's order: the game's first (the mod's override in place), then the mod's own by their seq."""
    idx = qr.line_index(gd)
    out = []
    if not topic.startswith('+'):
        out = [gd.key(f) for f in idx.lines.get(gd.from_key(topic), ())]
        fid = gd.from_key(topic)
        if fid in idx.first_topic:      # (a topic can borrow another's lines: its INFC links)
            for q in qr.topic_plain(pr.records.get(topic) if pr and topic in pr.records else qr.game_topic_record(gd, fid))['quests']:
                out += [l['info'] for l in q['links'] if l['info'] and l['info'] not in out and gd.from_key(l['info']) in gd.forms]
    mine = [k for k, r in pr.records.items() if r['type'] == 'INFO' and r.get('topic') == topic and k not in out] if pr else []
    mine.sort(key=lambda k: qr.line_seq(k, pr.records[k]))
    return out + mine


def line_view(gd, pr, key):
    rec = record(gd, pr, key)
    l = qr.info_plain(json.loads(json.dumps(rec)))
    if not l['topic']:
        l['topic'] = qr.line_topic(gd, pr, key, rec) or ''
    for c in l['conditions']:
        c['words'] = condition_words(gd, pr, c)
    who = [c.get('p1') for c in l['conditions'] if _fn_entry(c['fn']) and _fn_entry(c['fn'])['name'] == 'GetIsID' and c['op'] == '=' and c.get('value') == 1 and isinstance(c.get('p1'), str)]
    if l['speaker']:
        who = [l['speaker']]
    src_end = (l.get('end') or {}).get('source', '')
    src_begin = (l.get('begin') or {}).get('source', '')
    does = script_summary(gd, pr, src_end) + script_summary(gd, pr, src_begin)
    return {'key': key, 'state': state_of(gd, pr, key), 'line': l, 'text': ' '.join(r['text'] for r in l['responses']),
            'who': [{'key': k, 'name': short(gd, pr, k)} for k in who], 'when': [c['words'] for c in l['conditions']],
            'ors': [bool(c.get('or')) for c in l['conditions']], 'goodbye': bool(l['flags'].get('goodbye')),
            'choices': [{'key': k, 'prompt': _prompt(gd, pr, k)} for k in l['choices']],
            'adds': [{'key': k, 'prompt': _prompt(gd, pr, k)} for k in l['add']], 'does': does, 'quest_name': short(gd, pr, l['quest'])}


def _prompt(gd, pr, topic):
    try:
        rec = record(gd, pr, topic)
    except Exception:
        return topic
    return recordio.field(rec, 'FULL') or recordio.field(rec, 'EDID') or topic


def topic_view(gd, pr, key):
    rec = pr.records.get(key) if pr else None
    if rec is None and not key.startswith('+'):
        fid = gd.from_key(key)
        rec = qr.game_topic_record(gd, fid) if fid in qr.line_index(gd).first_topic else recordio.load(gd, fid)
    t = qr.topic_plain(json.loads(json.dumps(rec)))
    return {'key': key, 'edid': t['edid'], 'name': t['name'], 'priority': t['priority'], 'kind': t['kind'], 'flags': t['flags'],
            'state': state_of(gd, pr, key), 'quests': [q['quest'] for q in t['quests'] if q['quest']]}


def convo(gd, pr, who=None, quest=None):
    """A character's or a quest's conversation: greeting lines first, then every topic reachable, each with its lines."""
    idx = qr.line_index(gd)
    keys = []
    if who:
        if not who.startswith('+'):
            fid = gd.from_key(who)
            keys += [gd.key(f) for f in idx.by_who.get(fid, ())]
    if quest and not quest.startswith('+'):
        keys += [gd.key(f) for f in idx.by_quest.get(gd.from_key(quest), ())]
    for k, r in (pr.records if pr else {}).items():
        if r['type'] != 'INFO' or k in keys:
            continue
        if who and (recordio.field(r, 'ANAM') == who or any(_says(s, who) for s in r['subs'] if s['tag'] == 'CTDA')):
            keys.append(k)
        elif quest and recordio.field(r, 'QSTI') == quest:
            keys.append(k)
    keys = list(dict.fromkeys(keys))
    by_topic = {}
    for k in keys:
        rec = record(gd, pr, k)
        t = qr.line_topic(gd, pr, k, rec)
        if t:
            by_topic.setdefault(t, set()).add(k)
    topics = {}
    for t, have in by_topic.items():
        tv = topic_view(gd, pr, t)
        order = [k for k in lines_of_topic(gd, pr, t) if k in have]
        order += [k for k in have if k not in order]
        tv['lines'] = [line_view(gd, pr, k) for k in order]
        topics[t] = tv
    # (choices that lead to topics with no line for this person show as ways out with no answer yet)
    missing = set()
    for t in topics.values():
        for l in t['lines']:
            for c in l['choices']:
                if c['key'] not in topics:
                    missing.add(c['key'])
    for k in missing:
        tv = topic_view(gd, pr, k)
        # (not written for them by name: a short list is still what they'd say; a long one is everybody's)
        others = lines_of_topic(gd, pr, k)
        tv['lines'] = [line_view(gd, pr, x) for x in others] if len(others) <= 12 else []
        topics[k] = tv
    entry = [k for k, t in topics.items() if k == qr.GREETING or (t['edid'] or '').upper() == 'GREETING']
    return {'who': {'key': who, 'name': short(gd, pr, who)} if who else None, 'quest': {'key': quest, 'name': short(gd, pr, quest)} if quest else None,
            'greeting': entry[0] if entry else None, 'topics': list(topics.values())}


def _says(sub, who):
    f = {x.get('name'): x.get('value') for x in sub['fields']}
    return f.get('Function') == 72 and f.get('Parameter 1') == who and not f.get('Type', 0) & 0xE0


def _reserve(pr, n):
    """The keys the next n record_new ops will get (they're made in order)."""
    return ['+%06X' % (pr.next_id + k) for k in range(n)]


def is_condition(who, fn=72):
    return {'or': False, 'use_target': False, 'op': '=', 'fn': fn, 'p1': who, 'p2': 0, 'run': 0, 'ref': '', 'value': 1.0}


def new_line_plain(gd, pr, topic, quest, who, text, goodbye=False, conditions=None):
    l = {'kind': 0, 'next_speaker': 0, 'flags': {'goodbye': bool(goodbye)}, 'quest': quest, 'topic': topic,
         'responses': split_responses(text), 'conditions': [is_condition(who)] if who else [], 'choices': []}
    if conditions:
        l['conditions'] += conditions
    return l


def split_responses(text):
    """Words into the game's responses: each stays short enough to read as a subtitle, cut where a sentence ends."""
    text = (text or '').strip()
    out, now = [], ''
    for part in re.split(r'(?<=[.!?])\s+', text):
        if now and len(now) + 1 + len(part) > 150:
            out.append(now)
            now = part
        else:
            now = (now + ' ' + part).strip()
    out.append(now)
    return [{'emotion': 0, 'strength': 50, 'number': n + 1, 'sound': '', 'anim': 0, 'text': t} for n, t in enumerate(out)]


def start_conversation(gd, pr, br, edit, body):
    """Greeting for a character: a line in the game's GREETING topic under a quest (a new one when none is given)."""
    who = body['who']
    ops, quest = [], body.get('quest')
    name = short(gd, pr, who)
    if not quest:
        edid = unique_edid(gd, pr, br, re.sub(r'[^A-Za-z0-9]', '', name) + 'Talk')
        quest = _reserve(pr, 1)[0]
        ops.append({'op': 'record_new', 'record': qr.quest_record({'edid': edid, 'flags': {'start_enabled': True}, 'priority': 50, 'delay': 5.0, 'stages': [], 'objectives': []})})
    plain = new_line_plain(gd, pr, qr.GREETING, quest, who, body.get('text') or 'Hello there.', conditions=None)
    ops.append({'op': 'record_new', 'record': _compiled_line(gd, pr, plain)})
    out = edit('Greeting for ' + name, ops)
    out['quest'] = quest
    return out


def _compiled_line(gd, pr, plain):
    plain.setdefault('begin', None)
    plain.setdefault('end', None)
    errors = compile_line(plain, ModForms(gd, pr))
    if errors:
        raise ValueError('%s, line %s: %s' % (errors[0]['where'], errors[0]['line'], errors[0]['message']))
    return qr.info_record(plain)


def add_choice(gd, pr, br, edit, body):
    """A choice under a line: a new topic (the words on the button are its name), with the first answer in it, or an existing topic."""
    line_key, l = body['line'], None
    rec = json.loads(json.dumps(record(gd, pr, line_key)))
    l = qr.info_plain(rec)
    l['topic'] = l['topic'] or qr.line_topic(gd, pr, line_key, rec)
    who = body.get('who') or next((c['p1'] for c in l['conditions'] if c['fn'] == 72 and c['op'] == '='), None)
    quest = body.get('quest') or l['quest']
    ops = []
    topic = body.get('topic')
    if not topic:
        prompt = (body.get('prompt') or '').strip()
        if not prompt:
            raise ValueError('A choice needs the words the player picks.')
        base = re.sub(r'[^A-Za-z0-9]', '', edid_of(gd, pr, quest) + ' ' + prompt.title())[:48]
        edid = unique_edid(gd, pr, br, base + 'Topic')
        keys = _reserve(pr, 2)
        topic = keys[0]
        ops.append({'op': 'record_new', 'record': qr.topic_record({'edid': edid, 'name': prompt, 'priority': 50.0, 'kind': 0,
                                                                   'quests': [{'quest': quest, 'links': []}]})})
        ops.append({'op': 'record_new', 'record': _compiled_line(gd, pr, new_line_plain(gd, pr, topic, quest, who, body.get('text') or '...', bool(body.get('goodbye'))))})
    if topic not in l['choices']:
        l['choices'].append(topic)
    new_rec = qr.info_record(l)
    for k in ('seq', 'copied_from'):
        if k in rec:
            new_rec[k] = rec[k]
    ops.append({'op': 'record', 'key': line_key, 'record': new_rec})
    out = edit('Add choice', ops)
    out['topic'] = topic
    return out


def save_line(gd, pr, edit, key, plain):
    _clean_conditions(plain)
    old = pr.records.get(key) or {}
    plain['topic'] = plain.get('topic') or old.get('topic') or qr.line_topic(gd, pr, key, record(gd, pr, key))
    if not plain.get('quest'):
        raise ValueError('A line must belong to a quest.')
    for n, r in enumerate(plain.get('responses', ())):
        r['number'] = n + 1
    errors = compile_line(plain, ModForms(gd, pr))
    if errors:
        return {'errors': errors}
    rec = qr.info_record(plain)
    for k in ('seq', 'copied_from'):
        if k in old:
            rec[k] = old[k]
    return edit('Edit line', [{'op': 'record', 'key': key, 'record': rec}])


def new_line(gd, pr, edit, body):
    """Another line in a topic: another thing the person might say here."""
    plain = new_line_plain(gd, pr, body['topic'], body['quest'], body.get('who'), body.get('text') or '...', bool(body.get('goodbye')))
    return edit('New line', [{'op': 'record_new', 'record': _compiled_line(gd, pr, plain)}])


def delete_line(gd, pr, edit, key):
    rec = pr.records.get(key)
    if not rec:
        raise ValueError('This line is the game\'s own and your mod doesn\'t change it.')
    ops = [{'op': 'record_revert', 'key': key}]
    t = rec.get('topic')
    if key.startswith('+') and t and t.startswith('+') and not [k for k in lines_of_topic(gd, pr, t) if k != key]:
        ops.append({'op': 'record_revert', 'key': t})           # (a topic of the mod's with no lines left)
        for k, r in pr.records.items():
            if r['type'] == 'INFO' and k != key and any(s['tag'] in ('TCLT', 'NAME') and s['value'] == t for s in r['subs']):
                r2 = json.loads(json.dumps(r))
                r2['subs'] = [s for s in r2['subs'] if not (s['tag'] in ('TCLT', 'NAME') and s['value'] == t)]
                ops.append({'op': 'record', 'key': k, 'record': r2})
    return edit('Delete line', ops)


def move_line(gd, pr, edit, key, way):
    """Up or down among the topic's lines of the mod's (the first that fits is the one said)."""
    rec = pr.records.get(key)
    if not rec or not key.startswith('+'):
        raise ValueError('Only your own lines can be moved.')
    mine = [k for k in lines_of_topic(gd, pr, rec['topic']) if k.startswith('+')]
    at = mine.index(key)
    to = at + (-1 if way < 0 else 1)
    if not 0 <= to < len(mine):
        return edit('Move line', [])
    ops = []
    for k, n in ((mine[at], qr.line_seq(mine[to], pr.records[mine[to]])), (mine[to], qr.line_seq(mine[at], pr.records[mine[at]]))):
        r = json.loads(json.dumps(pr.records[k]))
        r['seq'] = n
        ops.append({'op': 'record', 'key': k, 'record': r})
    return edit('Move line', ops)


def save_topic(gd, pr, edit, key, body):
    rec = json.loads(json.dumps(pr.records.get(key) or qr.game_topic_record(gd, gd.from_key(key))))
    t = qr.topic_plain(rec)
    if 'name' in body:
        t['name'] = body['name']
    if body.get('priority') is not None:
        t['priority'] = float(body['priority'])
    if 'top_level' in body:
        t['flags']['top_level'] = bool(body['top_level'])
    return edit('Edit topic', [{'op': 'record', 'key': key, 'record': qr.topic_record(t)}])


def characters(gd, pr, br, q=''):
    idx = qr.line_index(gd)
    mine = {}
    for k, r in (pr.records if pr else {}).items():
        if r['type'] == 'INFO':
            for s in r['subs']:
                if s['tag'] == 'CTDA':
                    v = {x.get('name'): x.get('value') for x in s['fields']}
                    if v.get('Function') == 72 and isinstance(v.get('Parameter 1'), str):
                        mine[v['Parameter 1']] = mine.get(v['Parameter 1'], 0) + 1
    out = []
    for t in ('NPC_', 'CREA', 'TACT'):
        for r in br.records(t, q, limit=400):
            k = r['key']
            n = len(idx.by_who.get(gd.from_key(k), ())) if not k.startswith('+') else 0
            out.append(dict(r, type=t, lines=n, mine=mine.get(k, 0)))
    out.sort(key=lambda r: (not r.get('state') and not r['mine'], -(r['mine'] + r['lines']) if q else 0, (r['name'] or r['edid']).lower()))
    return out[:600]


# ---------- what moves a quest ----------
def _source_of(part):
    return (part or {}).get('source', '') if part else ''


def game_script_refs(gd):
    """Every script of the game, by what it says to which quest: {quest ID lower: {'sets': {stage: [where]}, 'objectives': ..., 'starts': [where]}}. Read once."""
    got = getattr(gd, '_quest_refs', None)
    if got is not None:
        return got
    got = gd._quest_refs = {}

    def note(where, text):
        if not text or 'stage' not in text.lower() and 'objective' not in text.lower() and 'quest' not in text.lower():
            return
        fx = qr.script_effects(text)
        for q, n in fx['sets']:
            got.setdefault(q.lower(), {'sets': {}, 'objectives': {}, 'starts': []})['sets'].setdefault(n, []).append(where)
        for q, n, what, on in fx['objectives']:
            if on:
                got.setdefault(q.lower(), {'sets': {}, 'objectives': {}, 'starts': []})['objectives'].setdefault((n, what), []).append(where)
        for verb, q in fx['quests']:
            if verb == 'startquest':
                got.setdefault(q.lower(), {'sets': {}, 'objectives': {}, 'starts': []})['starts'].append(where)
    for i, p in enumerate(gd.plugins):
        for rec, _path in p.walk():
            if rec.tag in ('SCPT', 'QUST', 'INFO'):
                try:
                    data = p.data(rec)
                except Exception:
                    continue
                if b'SCTX' not in data:
                    continue
                for t, d in tes4.iter_subrecords(data):
                    if t == 'SCTX':
                        note((rec.tag, gd.key(gd.to_global(i, rec.formid))), d.decode('cp1252', 'replace'))
    return got


def quest_refs(gd, pr, key, plain):
    """What sets each stage, shows and completes each objective, and starts a quest: every script of the mod and, for a game quest,
    of the game. {'sets': {stage: [move]}, 'objectives': {(index, what): [move]}, 'starts': [move]}"""
    edid = (plain.get('edid') or '').lower()
    out = {'sets': {}, 'objectives': {}, 'starts': []}

    def add(move, text):
        fx = qr.script_effects(text)
        for q, n in fx['sets']:
            if q.lower() == edid:
                out['sets'].setdefault(n, []).append(move)
        for q, n, what, on in fx['objectives']:
            if q.lower() == edid and on:
                out['objectives'].setdefault((n, what), []).append(move)
        for verb, q in fx['quests']:
            if q.lower() == edid and verb == 'startquest':
                out['starts'].append(move)
    for k, r in pr.records.items() if pr else ():
        if r['type'] == 'INFO':
            p = qr.info_plain(r)
            for sc in (p.get('begin'), p.get('end')):
                if sc:
                    add({'kind': 'line', 'key': k, 'conditions': p['conditions'], 'text': ' '.join(x['text'] for x in p['responses']), 'topic': p['topic'] or qr.line_topic(gd, pr, k, r)}, sc['source'])
        elif r['type'] == 'QUST':
            p = qr.quest_plain(r)
            for st in p['stages']:
                for e in st['entries']:
                    if e.get('script'):
                        add({'kind': 'stage', 'key': k, 'stage': st['index'], 'text': 'Stage %s of %s' % (st['index'], p['edid']), 'same': k == key}, e['script']['source'])
        elif r['type'] == 'SCPT':
            for s in r['subs']:
                if s['tag'] == 'SCTX':
                    add({'kind': 'script', 'key': k, 'text': 'Script ' + recordio.field(r, 'EDID')}, bytes.fromhex(s['value']).decode('cp1252', 'replace'))
    if not key.startswith('+'):             # (only a game quest can be moved by the game's own scripts)
        refs = game_script_refs(gd).get(edid, {})
        for n, wheres in refs.get('sets', {}).items():
            for tag, k in wheres:
                if pr is None or k not in pr.records:
                    out['sets'].setdefault(n, []).append(_game_move(gd, pr, tag, k, key, n))
        for nw, wheres in refs.get('objectives', {}).items():
            for tag, k in wheres:
                if pr is None or k not in pr.records:
                    out['objectives'].setdefault(nw, []).append({'kind': tag, 'key': k, 'text': short(gd, pr, k)})
        for tag, k in refs.get('starts', ()):
            out['starts'].append({'kind': tag, 'key': k, 'text': short(gd, pr, k)})
    return out


def _game_move(gd, pr, tag, k, quest_key, n):
    if tag == 'INFO':
        r = recordio.load(gd, gd.from_key(k))
        p = qr.info_plain(r)
        t = qr.line_index(gd).topic_of.get(gd.from_key(k))
        return {'kind': 'line', 'key': k, 'conditions': p['conditions'], 'text': ' '.join(x['text'] for x in p['responses']), 'topic': gd.key(t) if t else ''}
    if tag == 'QUST':
        return {'kind': 'stage', 'key': k, 'text': short(gd, pr, k), 'same': k == quest_key}
    return {'kind': 'script', 'key': k, 'text': short(gd, pr, k)}


def _needs(gd, pr, conds, key):
    """A line's or a stage's conditions on this quest's stage: [{'op','value'}] from GetStage, 'done' from GetStageDone."""
    out = []
    for c in conds:
        e = _fn_entry(c['fn'])
        if not e or c.get('p1') != key:
            continue
        if e['name'] == 'GetStage':
            out.append({'op': c['op'], 'value': float(c.get('value', 0))})
        elif e['name'] == 'GetStageDone':
            yes = (c['op'] == '=' and float(c.get('value', 0)) == 1) or (c['op'] == '!=' and float(c.get('value', 0)) == 0)
            out.append({'op': '>=' if yes else '<', 'value': float(c.get('p2', 0)), 'done': c.get('p2')})
    return out


def _fits(stage, needs):
    tests = {'=': lambda v: stage == v, '!=': lambda v: stage != v, '>': lambda v: stage > v, '>=': lambda v: stage >= v, '<': lambda v: stage < v, '<=': lambda v: stage <= v}
    return all(tests[n['op']](n['value']) for n in needs if n['op'] in tests)


def board(gd, pr, key):
    """A quest as a flow: the stages in order, and each move (a line said, another stage's script, a script) from where it can
    happen to the stage it sets. Stages nothing sets and stages nothing leads out of are flagged."""
    rec = record(gd, pr, key)
    q = qr.quest_plain(json.loads(json.dumps(rec)))
    refs = quest_refs(gd, pr, key, q)
    stages = [s['index'] for s in q['stages']]
    moves = []
    for to, ms in sorted(refs['sets'].items()):
        for m in ms:
            needs = _needs(gd, pr, m.get('conditions', ()), key)
            if m['kind'] == 'stage' and m.get('same'):
                frm = m.get('stage')
            elif needs:
                frm = next((s for s in stages if _fits(s, needs)), None)
                if frm is None and _fits(0, needs):
                    frm = 'start'
            else:
                frm = 'any'
            mv = {'kind': m['kind'], 'key': m['key'], 'to': to, 'from': frm, 'text': (m.get('text') or '')[:140],
                  'who': [], 'topic': _prompt(gd, pr, m['topic']) if m.get('topic') else ''}
            if m['kind'] == 'line':
                mv['who'] = [short(gd, pr, c['p1']) for c in m['conditions'] if c['fn'] == 72 and c['op'] == '=' and isinstance(c.get('p1'), str)]
            moves.append(mv)
    out = {'key': key, 'edid': q['edid'], 'name': q['name'], 'start_enabled': bool(q['flags'].get('start_enabled')), 'state': state_of(gd, pr, key),
           'started_by': [m.get('text', '') for m in refs['starts']][:8], 'stages': [], 'moves': moves}
    leaves = {m['from'] for m in moves}
    next_quests = []
    for s in q['stages']:
        n = s['index']
        log = next((e['log'] for e in s['entries'] if e.get('log')), '')
        complete = any(e['flags'].get('complete') for e in s['entries'])
        fail = any(e['flags'].get('fail') for e in s['entries'])
        for e in s['entries']:
            if e.get('next'):
                next_quests.append({'stage': n, 'key': e['next'], 'name': short(gd, pr, e['next'])})
            for sc in [e.get('script')]:
                if sc:
                    for v, qid in qr.script_effects(sc['source'])['quests']:
                        if v == 'completequest' and qid.lower() == (q['edid'] or '').lower():
                            complete = True
        out['stages'].append({'index': n, 'log': log, 'complete': complete, 'fail': fail, 'set': n in refs['sets'], 'leads': n in leaves,
                              'unset': n not in refs['sets'], 'dead': n not in leaves and not complete and not fail and n != (stages[-1] if stages else None)})
    out['next_quests'] = next_quests
    out['missing'] = sorted(set(refs['sets']) - set(stages))
    return out


# ---------- check this quest ----------
BUILTIN_TOPIC_MAX = 0x800


def check_quest(gd, pr, key):
    """Plain-word list of what's wrong or likely wrong with a quest: [{'level': 'problem'|'note', 'kind', 'text', 'go': {...}}]."""
    rec = record(gd, pr, key)
    q = qr.quest_plain(json.loads(json.dumps(rec)))
    refs = quest_refs(gd, pr, key, q)
    out = []

    def say(level, kind, text, **go):
        out.append({'level': level, 'kind': kind, 'text': text, 'go': go})
    forms = ModForms(gd, pr)
    # a quest that never runs says nothing
    if not q['flags'].get('start_enabled') and not refs['starts']:
        say('problem', 'start', 'Nothing starts this quest: it isn\'t set to start with the game, and no script of your mod says StartQuest %s. Its lines will never be said.' % q['edid'], quest=key)
    stages = [s['index'] for s in q['stages']]
    for s in q['stages']:
        n = s['index']
        if n not in refs['sets']:
            say('problem' if n != (stages[0] if stages else None) or not q['flags'].get('start_enabled') else 'note', 'stage', 'Stage %d: nothing sets it. No line or script says SetStage %s %d.' % (n, q['edid'], n), quest=key, stage=n)
        for ei, e in enumerate(s['entries']):
            sc = e.get('script')
            if sc and sc['source'].strip():
                _check_script(forms, sc, say, 'Stage %d\'s script' % n, dict(quest=key, stage=n))
    for n in sorted(set(refs['sets']) - set(stages)):
        say('problem', 'stage', 'Something sets stage %d, but this quest has no such stage.' % n, quest=key)
    if q['stages'] and not any(e['flags'].get('complete') for s in q['stages'] for e in s['entries']) \
            and not any(v == 'completequest' and q2.lower() == q['edid'].lower() for s in q['stages'] for e in s['entries'] if e.get('script') for v, q2 in qr.script_effects(e['script']['source'])['quests']):
        say('note', 'stage', 'No stage completes this quest. (Tick "Completes the quest" on the last one.)', quest=key)
    # objectives
    for o in q['objectives']:
        n = o['index']
        if (n, 'displayed') not in refs['objectives']:
            say('problem', 'objective', 'Objective %d ("%s"): nothing shows it. Say SetObjectiveDisplayed %s %d 1 in a stage or line.' % (n, o['text'][:40], q['edid'], n), quest=key, objective=n)
        if (n, 'completed') not in refs['objectives']:
            say('problem', 'objective', 'Objective %d ("%s"): nothing completes it. Say SetObjectiveCompleted %s %d 1 in a stage or line.' % (n, o['text'][:40], q['edid'], n), quest=key, objective=n)
        for t in o['targets']:
            if not t.get('target'):
                say('problem', 'objective', 'Objective %d has a map target that points at nothing.' % n, quest=key, objective=n)
    # the quest's lines and topics
    lines = _lines_of_quest(gd, pr, key)
    reached = _topics_reached(gd, pr)
    seen_topics = {}
    for k, r, p in lines:
        t = p['topic'] or qr.line_topic(gd, pr, k, r)
        seen_topics.setdefault(t, []).append((k, p))
    for t, ls in seen_topics.items():
        tv = topic_view(gd, pr, t) if t else {'edid': '?', 'name': '?', 'flags': {}, 'kind': 0}
        builtin = t and not t.startswith('+') and gd.from_key(t) & 0xFFFFFF < BUILTIN_TOPIC_MAX
        label = tv['name'] or tv['edid'] or t
        if t and not builtin and not tv['flags'].get('top_level') and tv['kind'] == 0 and t not in reached:
            say('problem', 'topic', 'Topic "%s": nobody can reach it. No line offers it as a choice, adds it, and it isn\'t a top-level topic.' % label, topic=t, line=ls[0][0])
        for k, p in ls:
            text = ' '.join(x['text'] for x in p['responses'])
            if not p['responses'] or not text.strip():
                say('problem', 'line', 'A line in "%s" has no words.' % label, line=k, topic=t)
            for x in p['responses']:
                if len(x['text']) > LONG_LINE:
                    say('note', 'line', 'A line in "%s" is %d letters long: split it, so the subtitle fits and reads in time ("%s...").' % (label, len(x['text']), x['text'][:40]), line=k, topic=t)
            if not p['conditions'] and not p['speaker']:
                say('note', 'line', 'A line in "%s" has no conditions: anyone in the game could say it ("%s...").' % (label, text[:40]), line=k, topic=t)
            for c in p['choices']:
                if not lines_of_topic(gd, pr, c):
                    say('problem', 'line', 'A line in "%s" offers the choice "%s", which has nothing to answer with.' % (label, _prompt(gd, pr, c)), line=k, topic=c)
            for name, sc in (('before', p.get('begin')), ('after', p.get('end'))):
                if sc and sc['source'].strip():
                    _check_script(forms, sc, say, 'The script %s a line in "%s"' % (name, label), dict(line=k, topic=t))
            for c in p['conditions']:
                if c['fn'] == 72 and c['op'] == '=' and isinstance(c.get('p1'), str) and c['p1']:
                    _check_voice(gd, pr, c['p1'], say, k)
    has_greeting = any(t == qr.GREETING for t in seen_topics)
    if lines and not has_greeting and not any(t and topic_view(gd, pr, t)['flags'].get('top_level') for t in seen_topics if t):
        say('note', 'topic', 'None of this quest\'s lines is a greeting or a top-level topic. Conversations have to start from one, or from a script.', quest=key)
    return {'key': key, 'edid': q['edid'], 'name': q['name'], 'problems': sum(1 for x in out if x['level'] == 'problem'), 'notes': sum(1 for x in out if x['level'] == 'note'), 'items': out}


def _check_voice(gd, pr, who, say, line):
    """A character with no voice type: dialogue depends on it even when silent (the game builds each line's voice path from it)."""
    try:
        rec = record(gd, pr, who)
    except Exception:
        say('problem', 'line', 'A line is for a form that can\'t be found: %s.' % who, line=line)
        return
    if rec.get('type') == 'NPC_' and not recordio.field(rec, 'VTCK') and not recordio.field(rec, 'TPLT'):
        say('problem', 'line', '%s has no voice type, so the game has nowhere to look for their lines. Set Voice on their record (Create page, Characters).' % short(gd, pr, who), line=line)


def _check_script(forms, sc, say, what, go):
    try:
        scriptc.compile_script(sc['source'], forms, scriptc.SCRIPT_OBJECT, partial=True, strict=True)
    except scriptc.CompileError as e:
        say('problem', 'script', '%s doesn\'t compile%s: %s' % (what, ' (line %d)' % e.line if e.line else '', e.message), **go)
    except Exception as e:
        say('problem', 'script', '%s couldn\'t be compiled: %s' % (what, e), **go)


def _lines_of_quest(gd, pr, key):
    out, seen = [], set()
    for k, r in (pr.records if pr else {}).items():
        if r['type'] == 'INFO' and recordio.field(r, 'QSTI') == key:
            out.append((k, r, qr.info_plain(json.loads(json.dumps(r)))))
            seen.add(k)
    if not key.startswith('+'):
        for f in qr.line_index(gd).by_quest.get(gd.from_key(key), ()):
            k = gd.key(f)
            if k not in seen:
                r = recordio.load(gd, f)
                out.append((k, r, qr.info_plain(r)))
    return out


def _topics_reached(gd, pr):
    """Topics any line offers or adds, from the mod's lines and the game's; scripts count when they name one."""
    got = getattr(gd, '_topics_offered', None)
    if got is None:
        got = set()
        for i, p in enumerate(gd.plugins):
            for rec, _path in p.walk():
                if rec.tag == 'INFO':
                    for t, d in tes4.iter_subrecords(p.data(rec)):
                        if t in ('TCLT', 'NAME', 'TCLF', 'TCFU'):
                            got.add(gd.key(gd.to_global(i, int.from_bytes(d, 'little'))))
                elif rec.tag == 'PACK':
                    for t, d in tes4.iter_subrecords(p.data(rec)):
                        if t == 'TNAM' and len(d) == 4:
                            got.add(gd.key(gd.to_global(i, int.from_bytes(d, 'little'))))
        gd._topics_offered = got
    out = set(got)
    edids = {}
    for k, r in (pr.records if pr else {}).items():
        if r['type'] == 'DIAL':
            edids[recordio.field(r, 'EDID').lower()] = k
    for k, r in (pr.records if pr else {}).items():
        if r['type'] == 'INFO':
            for s in r['subs']:
                if s['tag'] in ('TCLT', 'NAME', 'TCLF', 'TCFU'):
                    out.add(s['value'])
        if r['type'] in ('INFO', 'QUST', 'SCPT'):
            for s in r['subs']:
                if s['tag'] == 'SCTX':
                    for w in qr.script_effects(bytes.fromhex(s['value']).decode('cp1252', 'replace'))['topics']:
                        if w.lower() in edids:
                            out.add(edids[w.lower()])
        if r['type'] == 'PACK':
            for s in r['subs']:
                if s['tag'] == 'TNAM' and s['kind'] == 'F':
                    out.add(s['value'])
    return out


def mod_quests(gd, pr):
    return [{'key': k, 'edid': recordio.field(r, 'EDID'), 'name': recordio.field(r, 'FULL'), 'state': state_of(gd, pr, k)}
            for k, r in sorted(pr.records.items()) if r['type'] == 'QUST'] if pr else []


def pick(gd, pr, br, q, types, limit=40):
    """Forms whose editor ID has q in it, of these record types (any, with none): for picking a link."""
    q = q.lower().strip()
    types = set(types)
    own = [(recordio.field(r, 'EDID'), k, r['type']) for k, r in (pr.records if pr else {}).items() if k.startswith('+') and q in recordio.field(r, 'EDID').lower() and (not types or r['type'] in types)]
    out = [{'key': k, 'label': '%s (%s)' % (e, t)} for e, k, t in own][:limit]
    if br.edids is None:
        return {'busy': True, 'hits': out}
    first, then = [], []
    for e, fid in br.edids.items():
        if q in e and fid in gd.forms and (not types or gd.forms[fid][1].tag in types):
            (first if e.startswith(q) else then).append(fid)
    for fid in (first + then)[:limit - len(out)]:
        out.append({'key': gd.key(fid), 'label': br.label(gd.key(fid))})
    return {'busy': False, 'hits': out}


def functions(gd):
    """The condition functions, the common first, each with what its parameters are."""
    t = scriptc.tables()
    out = []
    common = {n.lower(): i for i, n in enumerate(COMMON_FUNCTIONS)}
    for code, e in t.by_code.items():
        if not 0x1000 <= code < 0x2000 or e['name'].startswith('Unused'):
            continue
        params = []
        for p in e['params']:
            kind = 'form' if p[0] in scriptc.PARAM_FORMS else 'list' if p[0] in (5, 18) else 'int'
            item = {'kind': kind, 'label': p[2].replace('(optional)', '').strip(), 'pk': p[0]}
            if kind == 'list':
                item['options'] = [[v, k] for k, v in sorted(t.lists[p[0]].items(), key=lambda kv: kv[1])]
            forms_of = scriptc.PARAM_FORMS.get(p[0])
            if forms_of and forms_of[1]:
                item['types'] = sorted(forms_of[1])
            params.append(item)
        out.append({'fn': code - 0x1000, 'name': e['name'], 'ref': bool(e['ref']), 'params': params, 'rank': common.get(e['name'].lower(), 999)})
    out.sort(key=lambda f: (f['rank'], f['name'].lower()))
    return out


# ---------- routes ----------
def get(path, q, gd, pr, br):
    if path == '/api/quest/list':
        return list_quests(gd, pr, br, q.get('q', ''))
    if path == '/api/quest/open':
        return quest_view(gd, pr, q['key'])
    if path == '/api/quest/functions':
        return functions(gd)
    if path == '/api/quest/pick':
        return pick(gd, pr, br, q.get('q', ''), q.get('types', '').split())
    if path == '/api/quest/board':
        return board(gd, pr, q['key'])
    if path == '/api/quest/mine':
        return mod_quests(gd, pr)
    if path == '/api/quest/check':
        return check_quest(gd, pr, q['key'])
    if path == '/api/dlg/characters':
        return characters(gd, pr, br, q.get('q', ''))
    if path == '/api/dlg/convo':
        return convo(gd, pr, q.get('who') or None, q.get('quest') or None)
    if path == '/api/dlg/line':
        return line_view(gd, pr, q['key'])
    return None


def post(path, body, gd, pr, br, edit):
    if path == '/api/quest/new':
        return new_quest(gd, pr, br, edit, body)
    if path == '/api/quest/copy':
        return copy_quest(gd, pr, br, edit, body['key'])
    if path == '/api/quest/save':
        return save_quest(gd, pr, edit, body['key'], body['quest'])
    if path == '/api/quest/revert':
        return edit('Put back quest', [{'op': 'record_revert', 'key': body['key']}])
    if path == '/api/quest/words':
        return [condition_words(gd, pr, c) for c in body['conditions']]
    if path == '/api/dlg/start':
        return start_conversation(gd, pr, br, edit, body)
    if path == '/api/dlg/choice':
        return add_choice(gd, pr, br, edit, body)
    if path == '/api/dlg/line/save':
        return save_line(gd, pr, edit, body['key'], body['line'])
    if path == '/api/dlg/line/new':
        return new_line(gd, pr, edit, body)
    if path == '/api/dlg/line/delete':
        return delete_line(gd, pr, edit, body['key'])
    if path == '/api/dlg/line/move':
        return move_line(gd, pr, edit, body['key'], int(body['way']))
    if path == '/api/dlg/topic/save':
        return save_topic(gd, pr, edit, body['key'], body)
    return None
