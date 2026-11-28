"""A way out of every conversation (27 Nov 2026, the user's report: a refugee at the Koko Marina camp had only her three
topics and no way to leave; in nv-rs you leave by picking a line).

The game's goodbyes are lines of the GOODBYE topic in its generic quests (GenericAdult, Generic, GenericKids), each quest
held to a list of the game's own voice types (GetIsVoiceType ... OR), and its lines leave some of those out again. A
person on another voice type (the mod's people mostly have VoiceDoNotRecordM/F) has none of them. So each speaker standing
in the mod's cells who would get no goodbye line gets one of their own: in the quest the Huáng's small talk is in
(FOLabWaikikiPeople), conditioned on them alone (GetIsID, as huangtalk's: a line's voice is written for its speaker), so
nobody who has one gets two and nobody in the Mojave gets any. The Huáng say theirs in Mandarin (huangtalk's goodbyes);
everyone else a plain short one. Voiced in each speaker's own voice by voicelines.

    Judge(gd, pr).audit()       [{base, edid, refs, vt, goodbyes, unsure, ...}] for every speaker standing in the mod's cells
    ops(gd, pr)                 (ops, plan, report): one Undo; plan {'only': line keys, 'zh': {shown: pinyin}} to voice after

A condition is judged on what the speaker's record says (voice type, ID, sex, race, faction, creature, child); with OR set it
is or'ed with the next, and a quest's list and a line's are judged apart (an OR at the end of the quest's list ends there).
Anything else (a quest's variable, a list) counts unsure, and unsure is not a goodbye."""
import collections
import json

import api_quests as aq
import api_voices as av
import indoors
import ourpeople
import questrec as qr
import recordio

QUEST = 'FOLabWaikikiPeople'
KNOWN = {427: 'GetIsVoiceType', 72: 'GetIsID', 70: 'GetIsSex', 64: 'GetIsCreature', 69: 'GetIsRace', 71: 'GetInFaction', 365: 'IsChild'}
LABEL = 'A goodbye for everyone who had none'
# (plain English, picked by the person's key; no lore: what anyone says)
SAID = {
    'pirate': ("Get going.", "Move along.", "Off with you."),
    'child': ("Bye!", "See you!"),
    'court': ("Be on your way.", "Go on, then."),
    'anyone': ("Take care.", "See you around.", "Later.", "Be well.", "Go safely."),
}


def _cmp(a, op, b):
    return {'=': a == b, '!=': a != b, '>': a > b, '<': a < b, '>=': a >= b, '<=': a <= b}[op]


class Judge:
    def __init__(self, gd, pr):
        self.gd, self.pr = gd, pr
        self.bye = topic_key(gd)
        self.lines = []
        for k in aq.lines_of_topic(gd, pr, self.bye):
            l = qr.info_plain(json.loads(json.dumps(self.rec(k))))
            qrec = self.rec(l['quest']) if l['quest'] else None
            q = qr.quest_plain(json.loads(json.dumps(qrec))) if qrec else None
            self.lines.append((k, l, q))

    def rec(self, k):
        try:
            return aq.record(self.gd, self.pr, k)
        except Exception:
            return None

    def traits(self, base, d=0):
        r = self.rec(base)
        if not r or d > 5 or r['type'] not in ('NPC_', 'CREA'):
            return None
        tp = recordio.field(r, 'TPLT')
        if tp and av._acbs(r, 'Template flags') & 0x01:
            t = self.rec(tp)
            if t and t['type'] in ('NPC_', 'CREA'):
                return self.traits(tp, d + 1)
            if t and t['type'] == 'LVLN' and not tp.startswith('+'):
                es = ourpeople._entries(self.gd, self.gd.from_key(tp))
                if es:
                    return self.traits(self.gd.key(es[0]), d + 1)
        vt, fem = av.voice_type_of(self.gd, self.pr, base)
        vt_edid = (recordio.field(self.rec(vt), 'EDID') or '') if vt and self.rec(vt) else ''
        return {'vt': vt, 'vt_edid': vt_edid, 'female': fem, 'race': recordio.field(r, 'RNAM'), 'creature': r['type'] == 'CREA',
                'child': 'Child' in vt_edid}

    def factions(self, base, d=0):
        r = self.rec(base)
        out = set()
        if not r or d > 5:
            return out
        tp = recordio.field(r, 'TPLT')
        if tp and av._acbs(r, 'Template flags') & 0x04 and self.rec(tp) and self.rec(tp)['type'] == 'NPC_':
            return self.factions(tp, d + 1)
        for s in r['subs']:
            if s['tag'] == 'SNAM':
                f = next((x['value'] for x in s.get('fields', []) if isinstance(x.get('value'), str)), None)
                if f:
                    out.add(f)
        return out

    @staticmethod
    def one(c, who, t, fac):
        fn, v = c['fn'], c.get('value', 0)
        if c.get('run') or c.get('use_target') or 'global' in c or fn not in KNOWN:
            return None
        if fn == 427:
            x = c.get('p1') == t['vt']
        elif fn == 72:
            x = c.get('p1') == who
        elif fn == 70:
            x = int(c.get('p1') or 0) == (1 if t['female'] else 0)
        elif fn == 64:
            x = t['creature']
        elif fn == 69:
            x = c.get('p1') == t['race']
        elif fn == 365:
            x = t['child']
        else:
            x = c.get('p1') in fac
        return _cmp(1.0 if x else 0.0, c['op'], v)

    def passes(self, conds, who, t, fac):
        """True, False, or None (a condition not judged here)."""
        res, group = True, []
        for i, c in enumerate(conds):
            group.append(c)
            if c.get('or') and i < len(conds) - 1:
                continue
            vals = [self.one(g, who, t, fac) for g in group]
            group = []
            if any(v is True for v in vals):
                continue
            if all(v is False for v in vals):
                return False
            res = None
        return res

    def goodbyes(self, base):
        t = self.traits(base)
        if not t:
            return None
        fac = self.factions(base)
        got, unsure = [], []
        for k, l, q in self.lines:
            if q is None or not l['flags'].get('goodbye'):
                continue
            if not q['flags'].get('start_enabled') and not (l['quest'] or '').startswith('+'):
                unsure.append(k)                    # (a game quest that runs only when something starts it: Followers)
                continue
            pq, pl = self.passes(q['conditions'], base, t, fac), self.passes(l['conditions'], base, t, fac)
            p = False if False in (pq, pl) else (True if (pq, pl) == (True, True) else None)
            if p is True:
                got.append(k)
            elif p is None:
                unsure.append(k)
        return t, got, unsure

    def bases(self):
        """{NPC_ key: refs} standing in the mod's cells and its source plugin's (a levelled list's entries each)."""
        gd, pr = self.gd, self.pr
        src_i = ourpeople._src_index(gd, pr)
        cells = set(pr.cells)
        if src_i is not None:
            for f, (i, r) in gd.forms.items():
                if i == src_i and r.tag == 'CELL':
                    cells.add(gd.key(f))
        out = collections.Counter()
        for ck in cells:
            for _rk, base, _p, _s in indoors.placed(gd, pr, ck):
                for k in self._entries(base):
                    out[k] += 1
        return out

    def _entries(self, base, d=0):
        r = self.rec(base)
        if not r or d > 6:
            return []
        if r['type'] == 'NPC_':
            return [base]
        if r['type'] != 'LVLN':
            return []
        out = []
        for s in r['subs']:
            if s['tag'] == 'LVLO':
                k = next((x['value'] for x in s.get('fields', []) if isinstance(x.get('value'), str)), None)
                if k:
                    out += self._entries(k, d + 1)
        return out

    def says(self):
        out = set()
        for _k, r in self.pr.records.items():
            if r.get('type') == 'INFO':
                for c in qr.info_plain(json.loads(json.dumps(r)))['conditions']:
                    if c.get('fn') == 72 and isinstance(c.get('p1'), str):
                        out.add(c['p1'])
        return out

    def audit(self):
        says = self.says()
        rows = []
        for b, n in sorted(self.bases().items()):
            g = self.goodbyes(b)
            if not g:
                continue
            t, got, unsure = g
            rows.append({'base': b, 'edid': recordio.field(self.rec(b), 'EDID'), 'refs': n, 'vt': t['vt'], 'vt_edid': t['vt_edid'],
                         'female': t['female'], 'child': t['child'], 'talks': b in says, 'goodbyes': len(got), 'unsure': len(unsure),
                         'got': got[:3], 'unsure_ex': unsure[:3]})
        return rows


def topic_key(gd):
    return gd.key(next(f for f, (_i, r) in gd.forms.items() if r.tag == 'DIAL' and (f >> 24) == 0 and gd.edid(f) == 'GOODBYE'))


def _pick(choices, key):
    return choices[int(key.lstrip('+').split(':')[-1], 16) % len(choices)]


def kind_of(edid, child):
    if child:
        return 'child'
    if 'Pirate' in edid:
        return 'pirate'
    if edid.startswith(('FOLabCourt', 'FOLabKahuna')):
        return 'court'
    return 'anyone'


def words(pr, base, edid, child):
    """(shown, pinyin or None) for a speaker's goodbye."""
    import huangland as HL
    import huangtalk as HT
    if base.startswith('+') and HL.is_huang(pr, base):
        role = HL.role_of(edid)
        if role == 'zhao':
            return HT.ZHAO['GOODBYE'], None
        en, zh = _pick(HT.SAID[role]['GOODBYE'], base)
        return HL.shown(en, zh), zh
    return _pick(SAID[kind_of(edid, child)], base), None


def ops(gd, pr, rows=None):
    J = Judge(gd, pr)
    rows = J.audit() if rows is None else rows
    need = [r for r in rows if not r['goodbyes']]
    quest = next((k for k, r in pr.records.items() if r.get('type') == 'QUST' and recordio.field(r, 'EDID') == QUEST), None)
    if quest is None:
        raise ValueError('no %s quest in the mod' % QUEST)
    keys = aq._reserve(pr, len(need))
    out, zh, said = [], {}, collections.Counter()
    for k, r in zip(keys, need):
        text, pin = words(pr, r['base'], r['edid'] or '', r['child'])
        l = aq.new_line_plain(gd, pr, J.bye, quest, r['base'], text, goodbye=True)
        out.append({'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)})
        if pin:
            zh[l['responses'][0]['text']] = pin
        said['zh' if pin else kind_of(r['edid'] or '', r['child'])] += 1
    rep = {'speakers': len(rows), 'without': len(need), 'refs_without': sum(r['refs'] for r in need), 'lines': len(out),
           'by kind': dict(said), 'by voice type': dict(collections.Counter(r['vt_edid'] for r in need))}
    return out, {'only': keys, 'zh': zh, 'quest': QUEST}, rep
