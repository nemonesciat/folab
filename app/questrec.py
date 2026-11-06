"""Quests and dialogue as plain data, over the records a mod keeps (recordio.py).

    quest_plain(rec) / quest_record(plain)      QUST: stages with log entries, objectives with targets
    topic_plain(rec) / topic_record(plain)      DIAL: its quests, prompt, priority
    info_plain(rec)  / info_record(plain)       INFO: one line (its responses, conditions, choices, scripts)

Each pair is exact: a game record read and built again gives back the same subrecords, padding and all (tests go through
every record of the game). Result scripts carry their source in 'source' and their compiled parts in 'parts'; a changed
source is compiled when saved (api_quests.py), not here.

What the game's records need, found out from the files and how the game reads them:
- A topic's lines sit in a children group (type 7, labelled with the DIAL's ID) straight after the DIAL. The game reads
  an INFO against the DIAL it read last, so they can't be anywhere else.
- A line with no previous-line link (PNAM) goes after the ones before it: order in the group is order of choosing.
- A DIAL must list the quest of each of its lines (QSTI). A plugin that adds lines to a game topic copies the DIAL with
  all the quests its own file gives it, plus its own (all four story DLCs do this with GREETING).
- A silent line: TRDT (sound 0), NAM1 with the words, empty NAM2 and NAM3. No voice file is needed: when there's no
  .lip beside the voice path the game gives the line a time from its length and still shows the words."""
import re

import plugintree
import recordio
import schema
import tes4

# ---- flags, in plain words ----
QUEST_FLAGS = [(1, 'start_enabled'), (4, 'repeat_topics'), (8, 'repeat_stages')]
STAGE_FLAGS = [(1, 'complete'), (2, 'fail')]
TOPIC_FLAGS = [(1, 'rumors'), (2, 'top_level')]
INFO_FLAGS = [(1, 'goodbye'), (2, 'random'), (4, 'say_once'), (8, 'run_immediately'), (0x10, 'refusal'), (0x20, 'random_end'),
              (0x40, 'rumors'), (0x80, 'speech_challenge'), (0x100, 'say_once_a_day'), (0x200, 'always_darken')]
OPS = ['=', '!=', '>', '>=', '<', '<=']
GREETING = 'FalloutNV.esm:0000C8'


def _flags(v, names):
    return {n: bool(v & bit) for bit, n in names}


def _unflags(d, names):
    v = 0
    for bit, n in names:
        if d.get(n):
            v |= bit
    return v


def _extra(v, names):
    """the bits of a flags value no name covers (kept as they were)"""
    for bit, _n in names:
        v &= ~bit
    return v


def _f(sub, name):
    return next(x['value'] for x in sub['fields'] if x.get('name') == name)


def _pads(sub):
    return [x['pad'] for x in sub['fields'] if 'pad' in x]


def _z(tag, value, label=None):
    return {'tag': tag, 'label': label or tag, 'kind': 'z', 'value': value}


def _F(tag, value, label=None):
    return {'tag': tag, 'label': label or tag, 'kind': 'F', 'value': value}


def _fields(tag, label, fields, values, pads=()):
    out, vals, ps = [], iter(values), iter(pads)
    for code, name in fields:
        if code.endswith('x'):
            out.append({'pad': next(ps, '00' * int(code[:-1] or 1))})
        else:
            out.append({'name': name, 'code': code, 'value': next(vals)})
    return {'tag': tag, 'label': label, 'kind': 'struct', 'fields': out}


def _struct(rtype, tag, values, pads=()):
    """A decoded struct subrecord from values in layout order (padding from pads, else zero)."""
    label, fields = schema.layout(rtype, tag)
    return _fields(tag, label, fields, values, pads)


# ---- conditions ----
def condition_plain(sub):
    v = {f['name']: f['value'] for f in sub['fields'] if 'name' in f}
    kind = v['Type']
    out = {'or': bool(kind & 1), 'use_target': bool(kind & 2), 'op': OPS[kind >> 5] if kind >> 5 < 6 else kind >> 5,
           'fn': v['Function'], 'p1': v.get('Parameter 1', 0), 'p2': v.get('Parameter 2', 0), 'run': v.get('Run on', 0),
           'ref': v.get('Reference', '')}
    if kind & 4:
        out['global'] = v['Value'] or None
        out['value'] = 0.0
    else:
        out['value'] = v['Value']
    if kind & 0x18:
        out['xbits'] = kind & 0x18
    pads = _pads(sub)
    if pads != ['000000', '0000']:
        out['pads'] = pads
    if len(sub['fields']) != 9:
        out['size'] = len(sub['fields'])
    return out


def condition_sub(c):
    op = OPS.index(c['op']) if c['op'] in OPS else int(c['op'])
    is_global = 'global' in c
    kind = (op << 5) | (1 if c.get('or') else 0) | (2 if c.get('use_target') else 0) | (4 if is_global else 0) | c.get('xbits', 0)
    ps = schema.condition_params().get(int(c['fn']), [])
    code = lambda n: 'F' if n < len(ps) and ps[n][0] else 'I'

    def param(n, v):                     # (a form link when the function wants one: 0 and '' both mean none)
        return (v or '') if code(n) == 'F' else int(v or 0)
    value = (c.get('global') or '') if is_global else float(c.get('value', 0) or 0)
    fields = [('B', 'Type'), ('3x', ''), ('F' if is_global else 'f', 'Value'), ('H', 'Function'), ('2x', ''),
              (code(0), 'Parameter 1'), (code(1), 'Parameter 2'), ('I', 'Run on'), ('F', 'Reference')]
    values = [kind, value, int(c['fn']), param(0, c.get('p1')), param(1, c.get('p2')), int(c.get('run', 0) or 0), c.get('ref') or '']
    return _fields('CTDA', 'Condition', fields[:c.get('size', 9)], values, c.get('pads') or ())


# ---- result scripts ----
SCRIPT_TAGS = {'SCHR', 'SCDA', 'SCTX', 'SLSD', 'SCVR', 'SCRV', 'SCRO'}


def script_plain(parts):
    """A result script from its subrecords: SCHR, SCDA, SCTX, variables, references."""
    s = next((p for p in parts if p['tag'] == 'SCTX'), None)
    return {'source': bytes.fromhex(s['value']).decode('cp1252', 'replace') if s else '', 'parts': parts}


def empty_parts():
    """What a line or a stage holds when it has no script (SCHR all nought but its flags, as the game's have it)."""
    return [_struct('INFO', 'SCHR', [0, 0, 0, 0, 1])]


def empty_script():
    return {'source': '', 'parts': empty_parts()}


# ---- quests ----
def quest_plain(rec):
    subs = rec['subs']
    q = {'type': 'QUST', 'edid': None, 'script': '', 'name': None, 'icon': None, 'flags': {}, 'xflags': 0, 'priority': 0, 'delay': None,
         'conditions': [], 'stages': [], 'objectives': [], 'rec_flags': rec.get('flags', 0), 'src': rec.get('src', '')}
    stage = entry = obj = target = None
    i, n = 0, len(subs)
    while i < n:
        s = subs[i]
        t = s['tag']
        if t == 'EDID':
            q['edid'] = s['value']
        elif t == 'SCRI':
            q['script'] = s['value']
        elif t == 'FULL':
            q['name'] = s['value']
        elif t == 'ICON':
            q['icon'] = s['value']
        elif t == 'DATA':
            q['flags'] = _flags(_f(s, 'Flags'), QUEST_FLAGS)
            q['xflags'] = _extra(_f(s, 'Flags'), QUEST_FLAGS)
            q['priority'] = _f(s, 'Priority')
            if len(s['fields']) > 2:
                q['delay'] = _f(s, 'Delay')
                if _pads(s) != ['0000']:
                    q['dpad'] = _pads(s)
        elif t == 'INDX':
            stage, entry, obj, target = {'index': _f(s, 'Index'), 'entries': []}, None, None, None
            q['stages'].append(stage)
        elif t == 'QSDT':
            entry = {'flags': _flags(_f(s, 'Flags'), STAGE_FLAGS), 'xflags': _extra(_f(s, 'Flags'), STAGE_FLAGS), 'conditions': [], 'log': None, 'next': ''}
            stage['entries'].append(entry)
        elif t == 'CNAM':
            entry['log'] = s['value']
        elif t == 'NAM0':
            entry['next'] = s['value']
        elif t == 'QOBJ':
            obj, target, stage, entry = {'index': _f(s, 'Index'), 'text': '', 'targets': []}, None, None, None
            q['objectives'].append(obj)
        elif t == 'NNAM':
            obj['text'] = s['value']
        elif t == 'QSTA':
            target = {'target': _f(s, 'Target'), 'flags': _f(s, 'Flags'), 'conditions': []}
            if _pads(s) != ['000000']:
                target['pad'] = _pads(s)
            obj['targets'].append(target)
        elif t == 'CTDA':
            (target or entry or q)['conditions'].append(condition_plain(s))
        elif t in SCRIPT_TAGS:
            parts = []
            while i < n and subs[i]['tag'] in SCRIPT_TAGS:
                parts.append(subs[i])
                i += 1
            if entry is None:                   # (a stage with a script and no flags byte: one of the game's)
                entry = {'flags': {}, 'xflags': 0, 'conditions': [], 'log': None, 'next': '', 'no_flags': True}
                stage['entries'].append(entry)
            entry['script'] = script_plain(parts)
            continue
        else:
            raise ValueError('quest %s: subrecord %s has no place' % (q['edid'], t))
        i += 1
    return q


def quest_record(q):
    subs = [_z('EDID', q['edid'], 'Editor ID')] if q.get('edid') is not None else []
    if q.get('script'):
        subs.append(_F('SCRI', q['script'], 'Script'))
    if q.get('name') is not None:
        subs.append(_z('FULL', q['name'], 'Name'))
    if q.get('icon') is not None:
        subs.append(_z('ICON', q['icon'], 'Icon'))
    fl = _unflags(q.get('flags') or {}, QUEST_FLAGS) | int(q.get('xflags') or 0)
    if q.get('delay') is None:
        subs.append(_fields('DATA', 'Data', [('B', 'Flags'), ('B', 'Priority')], [fl, int(q.get('priority', 0))]))
    else:
        subs.append(_fields('DATA', 'Data', [('B', 'Flags'), ('B', 'Priority'), ('2x', ''), ('f', 'Delay')],
                            [fl, int(q.get('priority', 0)), float(q['delay'])], q.get('dpad') or ()))
    subs += [condition_sub(c) for c in q.get('conditions', ())]
    for st in q.get('stages', ()):
        subs.append(_struct('QUST', 'INDX', [int(st['index'])]))
        for e in st.get('entries', ()):
            if not e.get('no_flags'):
                subs.append(_struct('QUST', 'QSDT', [_unflags(e.get('flags') or {}, STAGE_FLAGS) | int(e.get('xflags') or 0)]))
            subs += [condition_sub(c) for c in e.get('conditions', ())]
            if e.get('log') is not None:
                subs.append(_z('CNAM', e['log'], 'Log entry'))
            if e.get('script'):
                subs += e['script']['parts']
            if e.get('next'):
                subs.append(_F('NAM0', e['next'], 'Next quest'))
    for o in q.get('objectives', ()):
        subs.append(_struct('QUST', 'QOBJ', [int(o['index'])]))
        subs.append(_z('NNAM', o.get('text', ''), 'Objective text'))
        for t in o.get('targets', ()):
            subs.append(_struct('QUST', 'QSTA', [t.get('target') or '', int(t.get('flags', 0))], t.get('pad') or ()))
            subs += [condition_sub(c) for c in t.get('conditions', ())]
    return {'type': 'QUST', 'flags': int(q.get('rec_flags', 0)), 'src': q.get('src', ''), 'subs': subs}


# ---- topics ----
def topic_plain(rec):
    t = {'type': 'DIAL', 'edid': None, 'quests': [], 'name': None, 'priority': None, 'dumb': None, 'kind': 0, 'flags': {}, 'xflags': 0,
         'one_byte': False, 'rec_flags': rec.get('flags', 0), 'src': rec.get('src', '')}
    last = None
    for s in rec['subs']:
        tg = s['tag']
        if tg == 'EDID':
            t['edid'] = s['value']
        elif tg == 'QSTI':
            last = {'quest': s['value'], 'links': []}
            t['quests'].append(last)
        elif tg == 'INFC':
            if last is None:                    # (some game topics hold these before any quest)
                last = {'quest': None, 'links': []}
                t['quests'].append(last)
            last['links'].append({'info': s['value']})
        elif tg == 'INFX':
            last['links'][-1]['index'] = _f(s, 'Index')
        elif tg == 'FULL':
            t['name'] = s['value']
            t['name_at'] = len(t['quests'])     # (where it stood among the quests)
        elif tg == 'PNAM':
            t['priority'] = _f(s, 'Priority')
        elif tg == 'TDUM':
            t['dumb'] = s['value']
        elif tg == 'DATA':
            t['kind'] = _f(s, 'Type')
            if len(s['fields']) > 1:
                t['flags'] = _flags(_f(s, 'Flags'), TOPIC_FLAGS)
                t['xflags'] = _extra(_f(s, 'Flags'), TOPIC_FLAGS)
            else:
                t['one_byte'] = True
        else:
            raise ValueError('topic %s: subrecord %s has no place' % (t['edid'], tg))
    return t


def topic_record(t):
    subs = [_z('EDID', t['edid'], 'Editor ID')] if t.get('edid') is not None else []
    name = _z('FULL', t['name'], 'Name') if t.get('name') is not None else None
    at = t.get('name_at')
    for n, q in enumerate(t.get('quests', ())):
        if at == n and name:
            subs.append(name)
            name = None
        if q['quest'] is not None:
            subs.append(_F('QSTI', q['quest'], 'Quest'))
        for l in q.get('links', ()):
            subs.append(_F('INFC', l['info'], 'Response link'))
            if 'index' in l:
                subs.append(_struct('DIAL', 'INFX', [l['index']]))
    if name:
        subs.append(name)
    if t.get('priority') is not None:
        subs.append(_struct('DIAL', 'PNAM', [float(t['priority'])]))
    if t.get('dumb') is not None:
        subs.append(_z('TDUM', t['dumb'], 'Dumb response'))
    flags = _unflags(t.get('flags') or {}, TOPIC_FLAGS) | int(t.get('xflags') or 0)
    if t.get('one_byte'):
        subs.append(_fields('DATA', 'Data', [('B', 'Type')], [int(t.get('kind', 0))]))
    else:
        subs.append(_fields('DATA', 'Data', [('B', 'Type'), ('B', 'Flags')], [int(t.get('kind', 0)), flags]))
    return {'type': 'DIAL', 'flags': int(t.get('rec_flags', 0)), 'src': t.get('src', ''), 'subs': subs}


# ---- lines ----
def info_plain(rec):
    l = {'type': 'INFO', 'kind': 0, 'next_speaker': 0, 'flags': {}, 'xflags': 0, 'quest': '', 'prev': None, 'add': [], 'responses': [],
         'conditions': [], 'choices': [], 'links_from': [], 'follow_up': [], 'begin': None, 'end': None, 'prompt': None, 'speaker': '',
         'skill': '', 'challenge': None, 'rec_flags': rec.get('flags', 0), 'topic': rec.get('topic', ''), 'src': rec.get('src', ''), 'has_next': False}
    subs = rec['subs']
    i, n, last, order = 0, len(subs), None, []
    while i < n:
        s = subs[i]
        t = s['tag']
        if t == 'DATA':
            l['kind'], l['next_speaker'] = _f(s, 'Type'), _f(s, 'Next speaker')
            l['flags'] = _flags(_f(s, 'Flags'), INFO_FLAGS)
            l['xflags'] = _extra(_f(s, 'Flags'), INFO_FLAGS)
        elif t == 'QSTI':
            l['quest'] = s['value']
        elif t == 'PNAM':
            l['prev'] = s['value']
        elif t == 'NAME':
            l['add'].append(s['value'])
        elif t == 'TRDT':
            last = {'emotion': _f(s, 'Emotion'), 'strength': _f(s, 'Emotion strength'), 'number': _f(s, 'Response number'),
                    'sound': _f(s, 'Sound'), 'anim': _f(s, 'Use emotion animation'), 'text': '', 'notes': '', 'edits': '', 'speaker_idle': '', 'listener_idle': ''}
            if _pads(s) != ['00000000', '000000', '000000']:
                last['pads'] = _pads(s)
            l['responses'].append(last)
        elif t == 'NAM1':
            last['text'] = s['value']
        elif t == 'NAM2':
            last['notes'] = s['value']
        elif t == 'NAM3':
            last['edits'] = s['value']
        elif t == 'SNAM':
            last['speaker_idle'] = s['value']
        elif t == 'LNAM':
            last['listener_idle'] = s['value']
        elif t == 'CTDA':
            l['conditions'].append(condition_plain(s))
        elif t == 'TCLT':
            l['choices'].append(s['value'])
        elif t == 'TCLF':
            l['links_from'].append(s['value'])
        elif t == 'TCFU':
            l['follow_up'].append(s['value'])
        elif t == 'NEXT':
            l['has_next'] = True
        elif t in SCRIPT_TAGS:
            parts = []
            while i < n and subs[i]['tag'] in SCRIPT_TAGS:
                parts.append(subs[i])
                i += 1
            l['end' if l['has_next'] else 'begin'] = script_plain(parts)
            continue
        elif t == 'RNAM':
            l['prompt'] = s['value']
        elif t == 'ANAM':
            l['speaker'] = s['value']
        elif t == 'KNAM':
            l['skill'] = s['value']
        elif t == 'DNAM':
            l['challenge'] = _f(s, 'Difficulty')
        else:
            raise ValueError('line: subrecord %s has no place' % t)
        order.append(t)
        i += 1
    return l


def info_record(l):
    subs = [_struct('INFO', 'DATA', [int(l.get('kind', 0)), int(l.get('next_speaker', 0)), _unflags(l.get('flags') or {}, INFO_FLAGS) | int(l.get('xflags') or 0)])]
    if l.get('quest'):
        subs.append(_F('QSTI', l['quest'], 'Quest'))
    if l.get('prev') is not None:
        subs.append(_F('PNAM', l['prev'], 'Previous response'))
    subs += [_F('NAME', k, 'Add topic') for k in l.get('add', ())]
    for n, r in enumerate(l.get('responses', ())):
        subs.append(_struct('INFO', 'TRDT', [int(r.get('emotion', 0)), int(r.get('strength', 50)), int(r.get('number', n + 1)), r.get('sound') or '', int(r.get('anim', 0))],
                            r.get('pads') or ()))
        subs += [_z('NAM1', r.get('text', ''), 'Response text'), _z('NAM2', r.get('notes', ''), 'Script notes'), _z('NAM3', r.get('edits', ''), 'Edits')]
        if r.get('speaker_idle'):
            subs.append(_F('SNAM', r['speaker_idle'], 'Speaker idle'))
        if r.get('listener_idle'):
            subs.append(_F('LNAM', r['listener_idle'], 'Listener idle'))
    subs += [condition_sub(c) for c in l.get('conditions', ())]
    subs += [_F('TCLT', k, 'Choice') for k in l.get('choices', ())]
    subs += [_F('TCLF', k, 'Link from') for k in l.get('links_from', ())]
    subs += [_F('TCFU', k, 'Linked from topic') for k in l.get('follow_up', ())]
    subs += (l.get('begin') or empty_script())['parts']
    subs.append({'tag': 'NEXT', 'label': 'Marker', 'kind': 'struct', 'fields': []})
    subs += (l.get('end') or empty_script())['parts']
    if l.get('prompt') is not None:
        subs.append(_z('RNAM', l['prompt'], 'Prompt'))
    if l.get('speaker'):
        subs.append(_F('ANAM', l['speaker'], 'Speaker'))
    if l.get('skill'):
        subs.append(_F('KNAM', l['skill'], 'Speech skill'))
    if l.get('challenge') is not None:
        subs.append(_struct('INFO', 'DNAM', [int(l['challenge'])]))
    out = {'type': 'INFO', 'flags': int(l.get('rec_flags', 0)), 'src': l.get('src', ''), 'subs': subs}
    if l.get('topic'):
        out['topic'] = l['topic']
    return out


# ---- what a script does to quests (read from its source: it's what the line or stage says it does) ----
_SET = re.compile(r'(?:^|[\s.;])setstage\s+("?)(\w+)\1\s*,?\s+(\d+)', re.I | re.M)
_OBJ = re.compile(r'(?:^|[\s.;])setobjective(displayed|completed)\s+("?)(\w+)\2\s*,?\s+(-?\d+)\s*,?\s+(\d+)', re.I | re.M)
_QUEST = re.compile(r'(?:^|[\s.;])(startquest|stopquest|completequest|failquest|resetquest)\s+("?)(\w+)\2', re.I | re.M)
_TOPIC = re.compile(r'(?:^|[\s.;])(addtopic|sayto|say|startconversation)\b[^;\n]*', re.I | re.M)


def strip_comments(source):
    return '\n'.join(line.split(';', 1)[0] for line in (source or '').replace('\r\n', '\n').split('\n'))


def script_effects(source):
    """{'sets': [(quest ID, stage)], 'objectives': [(quest ID, index, 'displayed'|'completed', on)], 'quests': [(verb, quest ID)],
    'topics': [words naming topics]} of a script's text."""
    src = strip_comments(source)
    return {'sets': [(m.group(2), int(m.group(3))) for m in _SET.finditer(src)],
            'objectives': [(m.group(3), int(m.group(4)), m.group(1).lower(), int(m.group(5))) for m in _OBJ.finditer(src)],
            'quests': [(m.group(1).lower(), m.group(3)) for m in _QUEST.finditer(src)],
            'topics': [w for m in _TOPIC.finditer(src) for w in re.findall(r'\w+', m.group(0))[1:]]}


# ---- which lines the game's topics hold (read once for each load of the game) ----
class LineIndex:
    """topic_of {INFO: DIAL}, lines {DIAL: [INFO] in the order the game reads them}, first_topic {DIAL: (file, Record) of the file
    that first has it}, by_quest {QUST: [INFO]}, by_who {actor: [INFO] whose conditions or speaker name it}."""

    def __init__(self, gd):
        self.topic_of, self.lines, self.first_topic, self.by_quest, self.by_who = {}, {}, {}, {}, {}
        getisid = 72
        g = gd.to_global
        for i, p in enumerate(gd.plugins):
            for rec, path in p.walk():
                if rec.tag == 'DIAL':
                    self.first_topic.setdefault(g(i, rec.formid), (i, rec))
                elif rec.tag == 'INFO':
                    fid = g(i, rec.formid)
                    topic = g(i, path[-1][1]) if path and path[-1][0] == tes4.G_TOPIC_CHILDREN else None
                    if fid not in self.topic_of:
                        self.lines.setdefault(topic, []).append(fid)
                    self.topic_of[fid] = topic
                    for t, d in tes4.iter_subrecords(p.data(rec)):
                        if t == 'QSTI':
                            self.by_quest.setdefault(g(i, int.from_bytes(d, 'little')), []).append(fid)
                        elif t == 'ANAM':
                            self.by_who.setdefault(g(i, int.from_bytes(d, 'little')), []).append(fid)
                        elif t == 'CTDA' and len(d) >= 16 and int.from_bytes(d[8:10], 'little') == getisid and not d[0] & 0xE0:
                            self.by_who.setdefault(g(i, int.from_bytes(d[12:16], 'little')), []).append(fid)


def line_index(gd):
    got = getattr(gd, '_line_index', None)
    if got is None:
        got = gd._line_index = LineIndex(gd)
    return got


def game_topic_record(gd, fid):
    """A game topic as the file that first has it gives it (a plugin adding lines copies this, plus its own quests)."""
    i, rec = line_index(gd).first_topic[fid]
    subs = list(tes4.iter_subrecords(gd.plugins[i].data(rec)))
    return {'type': 'DIAL', 'flags': rec.flags & ~tes4.COMPRESSED, 'src': gd.names[i],
            'subs': [recordio._keys(gd, i, 'DIAL', s) for s in schema.decode_record('DIAL', subs)]}


def line_topic(gd, pr, key, rec):
    """The topic a line of the mod's belongs to."""
    if rec.get('topic'):
        return rec['topic']
    src = rec.get('copied_from') or key                 # (a line saved from Browse, which knows nothing of topics)
    if src.startswith('+'):
        return (pr.records.get(src) or {}).get('topic')
    t = line_index(gd).topic_of.get(gd.from_key(src))
    return gd.key(t) if t is not None else None


def line_seq(key, rec):
    """Where a line stands among its topic's: order in the group is order of choosing."""
    if 'seq' in rec:
        return float(rec['seq'])
    return float(int(key.rsplit(':', 1)[-1].lstrip('+'), 16))


def plan_masters(gd, pr, used):
    """The files a mod's lines need beyond their own links: each line's topic."""
    for key, rec in pr.records.items():
        if rec['type'] == 'INFO':
            t = line_topic(gd, pr, key, rec)
            if t and not t.startswith('+'):
                used.add(gd.from_key(t) >> 24)
                used.add(line_index(gd).first_topic[gd.from_key(t)][0])


def write_lines(w, tree, found, order, join):
    """The mod's lines, each in its topic's children group; a game topic it only adds lines to comes along as a copy; every
    topic lists the quests of its lines."""
    gd, pr = w.gd, w.pr
    topics = {}
    for key, rec in pr.records.items():
        if rec['type'] == 'INFO':
            t = line_topic(gd, pr, key, rec)
            if t and (not t.startswith('+') or t in pr.records):
                topics.setdefault(t, []).append(key)
    for tkey in sorted(topics):
        tfid = w.link(tkey)
        have = found.get(tfid)
        if have is None:
            base = game_topic_record(gd, gd.from_key(tkey))
            node = plugintree.Rec.new('DIAL', base['flags'], tfid, join(recordio.to_bytes(base, w.link)), w.form_version)
            top = tree.top('DIAL', order)
            top.kids.append(node)
            have = found[tfid] = (node, top)
        node, parent = have
        subs = list(tes4.iter_subrecords(node.data()))
        listed = {d for t, d in subs if t == 'QSTI'}
        wanted = []
        for k in topics[tkey]:
            q = next((s['value'] for s in pr.records[k]['subs'] if s['tag'] == 'QSTI'), '')
            d = w.link(q).to_bytes(4, 'little') if q else b''
            if d and d not in listed and d not in wanted:
                wanted.append(d)
        if wanted:
            at = max([n + 1 for n, (t, _d) in enumerate(subs) if t in ('QSTI', 'INFC', 'INFX', 'EDID')] or [0])
            subs[at:at] = [('QSTI', d) for d in wanted]
            node.set_data(join(subs), node.flags & ~tes4.COMPRESSED)
        at = parent.kids.index(node)
        nxt = parent.kids[at + 1] if at + 1 < len(parent.kids) else None
        if isinstance(nxt, plugintree.Group) and nxt.gtype == tes4.G_TOPIC_CHILDREN:
            group = nxt
        else:
            group = plugintree.Group(tfid, tes4.G_TOPIC_CHILDREN)
            parent.kids.insert(at + 1, group)
        for k in sorted(topics[tkey], key=lambda k: line_seq(k, pr.records[k])):
            rec = pr.records[k]
            fid = w.link(k)
            data = join(recordio.to_bytes(rec, w.link))
            if fid in found:
                found[fid][0].set_data(data, rec['flags'])
            else:
                n = plugintree.Rec.new('INFO', rec['flags'], fid, data, w.form_version)
                group.kids.append(n)
                found[fid] = (n, group)
