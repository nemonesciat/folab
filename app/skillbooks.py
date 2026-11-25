"""Island skill books (docs/waikiki-speech-science.md section J, system 14): a Speech book and a Science book of the island's
own, each hidden behind the kind of check it helps with.

- **The books** (`BOOKS`) are the game's skill books copied (Lying, Congressional Style for Speech, the Big Book of Science
  for Science: their model, picture and the game's own reading rule, a skill point gain), with names and words of their own.
  - **[proposal]** The titles and words are this step's own.
- **Where** (`WHERE`), both in places already behind checks:
  - the Science book in the Radar Dome's cargo pod (secretcaches.py), whose seal only the station's terminal releases;
  - the Speech book in the freighter's hold (the Huang's), behind the elder's Speech 85 key. Its toolbox is the game's,
    whose contents every toolbox shares, so the hold's gets a copy of its own with the book in. Taking it is stealing,
    as anything from the hold.

    plan(gd, pr)       (rows, skipped)
    ops(gd, pr, P)     (ops, report): one Undo
"""
import json
import struct

import recordio

LABEL = 'Island skill books'
BOOKS = {   # skill: (the game's book copied, editor ID, title, what it says)
    'speech': ('BookSkillSpeech', 'FOLabBookTalkStory', 'Talk Story: Island Hospitality for Hotel Staff',
               'A pre-war hotel training manual. Greet, listen, never say no outright. Most of it is about how to make a guest '
               'think the idea was theirs.'),
    'science': ('BookSkillScience', 'FOLabBookObservatory', 'Volcano Observatory Field Notes',
                'Survey sheets, wiring diagrams for the seismographs and a long chapter on keeping instruments running in salt '
                'air.'),
}
WHERE = {   # skill: ('container', its record's editor ID) or ('swap', the place's editor ID, the game container there)
    'science': ('container', 'FOLabVertibirdCargo'),
    'speech': ('swap', 'FOLabFreighterHold', 'ToolboxContainer'),
}
HOLD_BOX = 'FOLabFreighterHoldToolbox'


def _key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _game(gd, tag, edid):
    f = next((f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid), None)
    if f is None:
        raise ValueError('the game has no %s %s' % (tag, edid))
    return f


def plan(gd, pr):
    rows, skipped = [], []
    if any(_key(pr, b[1], 'BOOK') for b in BOOKS.values()):
        return rows, [('books', 'already in the mod (Undo first)')]
    for skill, w in WHERE.items():
        if w[0] == 'container':
            k = _key(pr, w[1], 'CONT')
            (rows.append({'skill': skill, 'how': 'container', 'container': k, 'where': w[1]}) if k else
             skipped.append((skill, '%s not in the mod' % w[1])))
            continue
        place = _key(pr, w[1], 'CELL')
        box = gd.key(_game(gd, 'CONT', w[2]))
        refs = [(rk, r) for rk, r in ((pr.cells.get(place) or {}).get('refs') or {}).items()
                if r.get('base') == box and not r.get('removed')] if place else []
        if not refs:
            skipped.append((skill, 'no %s in %s' % (w[2], w[1])))
            continue
        rows.append({'skill': skill, 'how': 'swap', 'cell': place, 'ref': refs[0][0], 'from': box, 'where': w[1]})
    return rows, skipped


def _item(gd, rec, book_key):
    import api_characters as ac
    import factionfolk as ff
    s = ff._sub('CONT', 'CNTO', struct.pack('<Ii', 0, 1))
    ff._set_link(s, book_key)
    ac.insert(rec, s)


def ops(gd, pr, P=None):
    from activity import _new_key
    from surffish import _copy
    rows, skipped = P or plan(gd, pr)
    if not rows:
        raise ValueError('nothing to do: %s' % (skipped,))
    out, rep = [], {'made': [], 'where': {}, 'skipped': skipped}
    for row in rows:
        src, edid, title, words = BOOKS[row['skill']]
        bk = _new_key(pr)
        book = _copy(gd, 'BOOK', src, edid, title)
        for s in book['subs']:
            if s['tag'] == 'DESC':
                s['value'] = words
        out.append({'op': 'record', 'key': bk, 'record': book})
        rep['made'].append(edid)
        if row['how'] == 'container':
            rec = json.loads(json.dumps(pr.records[row['container']]))
            _item(gd, rec, bk)
            out.append({'op': 'record', 'key': row['container'], 'record': rec})
        else:
            ck = _new_key(pr)
            box = recordio.load(gd, gd.from_key(row['from']))
            box['src'] = ''
            box['copied_from'] = row['from']
            recordio.set_field(box, 'EDID', HOLD_BOX, label='Editor ID')
            _item(gd, box, bk)
            out += [{'op': 'record', 'key': ck, 'record': box}, {'op': 'swap', 'cell': row['cell'], 'ref': row['ref'], 'base': ck}]
            rep['made'].append(HOLD_BOX)
        rep['where'][edid] = row['where']
    return out, rep
