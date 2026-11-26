r"""Two of the valley quests' people renamed (upvalleys; the story session's name gate, 26 Nov 2026): Fang Jun was already a
Huang farmer's name (FOLabHuangFolk11, in the An quests) and Leilani the woman at Kuliouou's fire (and the Missouri's
Leilani Jorgensen). Ours become Qiao Wenbo and Kalena Kamakau (her son is still Makana Kamakau). Editor IDs stay.

    ops(pr)        the record ops: the two NPC_'s names, the two quests' logs and objectives, Qiao Wenbo's lines
    RENAMED        what each name became
    voiced_again   the lines whose words changed: Qiao Wenbo's greeting (it says his name) and his long lines, which
                   were one response cut by split_responses into pinyin and English pieces (voiced in English: the
                   Mandarin voicing matches whole responses), now sentence pairs (upvalleys.zh_parts), all in Mandarin

Only the valley quests' own records are touched: the older Fang Jun and the two other Leilanis keep their names."""
import json
import re

import recordio

RENAMED = {'Fang Jun': 'Qiao Wenbo', 'Leilani Kamakau': 'Kalena Kamakau'}
SWAPS = [(re.compile(r'Fang Jun'), 'Qiao Wenbo'), (re.compile('Fāng Jùn'), 'Qiáo Wénbó'),
         (re.compile(r'\bLeilani\b'), 'Kalena')]
PEOPLE = ('FOLabUVFangJun', 'FOLabUVLeilaniKamakau')
QUESTS = ('FOLabUVTheCount', 'FOLabUVNavigatorsGlass')
SCRIPT_TAGS = ('SCTX', 'SCDA', 'SCHR')        # (a name in a script's text would need compiling again: refused)
LABEL = 'Valley quests: two names changed (Qiao Wenbo, Kalena Kamakau)'


def _swap(v, hits, tag):
    if isinstance(v, str):
        n = v
        for p, to in SWAPS:
            n = p.sub(to, n)
        if n != v:
            hits.append(tag)
        return n
    if isinstance(v, list):
        return [_swap(x, hits, tag) for x in v]
    if isinstance(v, dict):
        t = v.get('tag', tag) if isinstance(v.get('tag'), str) else tag
        return {k: _swap(x, hits, t) for k, x in v.items()}
    return v


def _by_edid(pr, edids):
    out = {}
    for k, r in pr.records.items():
        e = recordio.field(r, 'EDID') if isinstance(r, dict) else None
        if e in edids:
            out[e] = k
    return out


def _quest_of(r):
    for s in r.get('subs') or ():
        if s.get('tag') == 'QSTI':
            return s.get('value')
    return r.get('quest')


def _zh_pieces(rec):
    """Puts a Mandarin line's responses as upvalleys.zh_parts has them (in place); the tags changed."""
    import upvalleys as U
    nam1 = [x for x in rec.get('subs') or () if x.get('tag') == 'NAM1']
    said = ' '.join(x.get('value') or '' for x in nam1)
    k = next((k for k in U.M if U.shown(k) == said), None)
    if k is None:
        return []
    parts = U.zh_parts(k)
    if [x.get('value') for x in nam1] == [t for t, _z in parts]:
        return []
    if len(parts) != len(nam1):
        raise ValueError('%s: %d responses, %d Mandarin pieces' % (k, len(nam1), len(parts)))
    for x, (t, _z) in zip(nam1, parts):
        x['value'] = t
    return ['NAM1']


def ops(pr):
    people = _by_edid(pr, set(PEOPLE))
    quests = _by_edid(pr, set(QUESTS))
    if len(people) != 2 or len(quests) != 2:
        raise ValueError('the valley quests are not in this mod (found %s, %s)' % (sorted(people), sorted(quests)))
    qkeys = set(quests.values())
    keys = list(people.values()) + list(quests.values())
    keys += [k for k, r in pr.records.items() if isinstance(r, dict) and r.get('type') == 'INFO' and _quest_of(r) in qkeys]
    out, report, lines = [], {}, []
    for k in keys:
        r = pr.records[k]
        hits = []
        new = _swap(r, hits, None)
        if r.get('type') == 'INFO':
            hits += _zh_pieces(new)
        if not hits:
            continue
        bad = [t for t in hits if t in SCRIPT_TAGS]
        if bad:
            raise ValueError('%s has a name in its script (%s): not renamed' % (k, bad))
        out.append({'op': 'record', 'key': k, 'record': new})
        report[recordio.field(r, 'EDID') or k] = sorted(set(t or '?' for t in hits))
        if r.get('type') == 'INFO':
            lines.append(k)
    return out, report, lines


def check(pr):
    """Names left: (old names still in the valley quests' records, how many records name each new one)."""
    people = _by_edid(pr, set(PEOPLE))
    quests = _by_edid(pr, set(QUESTS))
    qkeys = set(quests.values())
    mine = set(people.values()) | qkeys | {k for k, r in pr.records.items() if isinstance(r, dict) and r.get('type') == 'INFO'
                                           and _quest_of(r) in qkeys}
    left = [k for k in mine if re.search(r'Fang Jun|\bLeilani\b', json.dumps(pr.records[k], ensure_ascii=False))]
    full = {}
    for k, r in pr.records.items():
        if isinstance(r, dict) and r.get('type') in ('NPC_', 'CREA'):
            n = recordio.field(r, 'FULL')
            if n:
                full.setdefault(n, []).append(recordio.field(r, 'EDID'))
    return left, {n: full.get(n, []) for n in RENAMED.values()}, {f: [n for n in full if n.split()[0] == f]
                                                                   for f in ('Qiao', 'Kalena')}
