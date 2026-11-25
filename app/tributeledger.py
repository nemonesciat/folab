"""The court's tribute ledger (docs/waikiki-speech-science.md pick 8), on the decided storyline "The squeeze": the Vault
wants more people every year and Waikiki needs more food, so the Kahuna raises the quota.

- **Where:** a terminal in the Royal Hawaiian's "Court's Stores" (where the tribute is kept), locked average
  (Science 50). It's the old hotel's booking system turned tribute ledger.
- **What it holds** (decided only):
  - the quota raised again this year;
  - what each area owes: Mānoa (food, the breadbasket); the Tanks (Kaimukī's water); Alewa Fort and Kalihi; the Pacific
    Heights beacon; Kuliʻouʻou and Niu (they pay both sides);
  - the Holdouts paying nothing ("taxes due");
  - those "sent on" to the Natatorium's cages for the ship.

  Which valley stops paying is still undecided, so the ledger doesn't say.
- **Reading the quota page** sets FOLabTributeLedger.read to 1: a hook for the squeeze's quests to come.
- **Placement:** on the place's navmesh, clear of doors and arrivals, anyone standing (the court's robots included) and
  seats.

    plan(gd, pr)    (rows, skipped)
    ops(gd, pr, P)  (ops, report): one Undo
"""
import recordio

LABEL = "The court's tribute ledger"
PLACE = 'FOLabRoyalHawaiianFloor2'
QUEST, SCRIPT = 'FOLabTributeLedger', 'FOLabTributeLedgerScript'
TEXT = """Terminal: FOLabTributeLedgerTerminal
Name: Tribute Ledger
Model: desk
Lock: average
Welcome:
  THE ROYAL HAWAIIAN - GUEST SERVICES
  (BOOKINGS) TRIBUTE OF THE KAHUNA'S COURT
== The quota
Script: set FOLabTributeLedger.read to 1
Says:
  Quota raised again this year, by order of the Kahuna.
  Food: raised. Water: raised. People: raised.
  Collectors to keep the new figures on tribute day.
== What each area owes
Says:
  MANOA ........... food, the full measure. PAID.
  THE TANKS ....... water for Kaimuki. PAID.
  ALEWA FORT ...... held for the court. Owes its watch on the wall.
  PACIFIC HEIGHTS . the beacon kept lit. PAID.
  KULIOUOU ........ paid, short. (They pay the pirates too.)
  NIU ............. paid, short. (They pay the pirates too.)
  THE HOLDOUTS .... NOTHING PAID. TAXES DUE.
== Sent on
Says:
  Sent on to the ship, for the Natatorium cages, this quarter:
  from the valleys, as tribute. From the collectors' rounds.
  Count kept aboard the ship. Not entered here.
"""


def plan(gd, pr):
    import robots
    ck = next((k for k, r in pr.records.items() if r.get('type') == 'CELL' and recordio.field(r, 'EDID') == PLACE), None)
    if not ck:
        return [], [('ledger', PLACE + ' not in the mod')]
    got, why = robots.inside_spots(gd, pr, ck, ('butler',))
    if not got:
        return [], [('ledger', why or 'no spot')]
    return [{'what': 'ledger', 'cell': ck, 'place': recordio.field(pr.records[ck], 'FULL'), 'spot': got[0][1], 'near': got[0][2]}], []


def ops(gd, pr, P=None):
    import api_scripts
    import questrec as qr
    import terminals
    from activity import _new_key
    from missouriterms import _WithScript
    if any(recordio.field(r, 'EDID') == QUEST for r in pr.records.values()):
        raise ValueError('the mod already has %s (Undo first)' % QUEST)
    rows, skipped = P or plan(gd, pr)
    out, rep = [], {'terminals': [], 'skipped': skipped}
    if not rows:
        return out, rep
    quest_key, script_key = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': script_key, 'name': '', 'flags': {'start_enabled': True},
                             'priority': 50, 'delay': 5.0, 'stages': [], 'objectives': []})
    sc = api_scripts.scripts()
    c = sc.compile('scn %s\nshort read\n\nBegin GameMode\nEnd\n' % SCRIPT, script_key, 'quest', {quest_key: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the ledger\'s script: %s' % (c,))
    srec = sc._record_of(c, SCRIPT)
    out += [{'op': 'record', 'key': script_key, 'record': srec}, {'op': 'record', 'key': quest_key, 'record': quest}]
    forms = terminals.mod_forms(gd, pr, {quest_key: quest, script_key: srec})
    forms.pr = _WithScript(pr, script_key, srec)
    row = rows[0]
    spec = terminals.plan(TEXT)
    t_ops, t_keys = terminals.ops(gd, pr, spec, forms)
    for o in t_ops:
        k = _new_key(pr)
        assert k == t_keys[recordio.field(o['record'], 'EDID')]
        out.append({'op': 'record', 'key': k, 'record': o['record']})
    x, y, z, rz = row['spot']
    out.append({'op': 'place', 'cell': row['cell'], 'key': _new_key(pr),
                'ref': {'base': t_keys[spec['edid']], 'p': [x, y, z - 4, 0.0, 0.0, rz], 's': 1.0}})
    rep['terminals'].append({'place': row['place'], 'science': terminals.science_needed(spec), 'spot': row['spot'], 'near': row['near']})
    return out, rep
