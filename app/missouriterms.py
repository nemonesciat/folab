"""The Missouri's fire control (docs/waikiki-speech-science.md pick 5; the decided storyline "The Captain's bluff": the
Missouri's big guns can't fire, and whoever finds out changes the balance).

- **Fire control:** a terminal in her Pilot House, locked hard (Science 75, the nearest of the game's levels to tier 5's 85).
  - Its gunnery log shows the main battery not ready and no firing since she went aground. It says nothing of why: that
    isn't decided.
  - Reading it sets FOLabCaptainsBluff.knows to 1 and says so in a message box. That's the storyline's hook: what
    knowing does is for the quests to come.
- **The Engine Room:** a terminal, locked average (Science 50), whose power log is the decided power table for her:
  solar panels and a wind turbine on deck, Vault cells, enough for the searchlight, the radio and the one working gun.
- Both stand on their place's own navmesh, clear of doors and arrivals, anyone standing and seats (robots' rules). Both
  are wired by result scripts, proven in nv-rs.

    plan(gd, pr)    (rows, skipped)
    ops(gd, pr, P)  (ops, report): one Undo
"""
import recordio

LABEL = "The Missouri's fire control"
QUEST, SCRIPT, MESSAGE = 'FOLabCaptainsBluff', 'FOLabCaptainsBluffScript', 'FOLabCaptainsBluffMessage'
PLACES = {'fire': 'FOLabMissouriPilotHouse', 'power': 'FOLabMissouriEngineRoom'}
KNOWN = "The Missouri's main battery hasn't fired since she went aground. Her big guns can't fire."
FIRE = """Terminal: FOLabMissouriFireControl
Name: Fire Control
Model: desk
Lock: hard
Welcome:
  USS MISSOURI (BB-63)
  MAIN BATTERY FIRE CONTROL
== Main battery status
Says:
  TURRET ONE ...... NOT READY
  TURRET TWO ...... NOT READY
  TURRET THREE .... NOT READY
  RANGEKEEPER ..... NO DATA
== Gunnery log
Script: set FOLabCaptainsBluff.knows to 1
Says:
  Last main battery fire: none recorded since the ship took the ground.
  Drill entries continue. No round loaded.
  Weekly report to the Captain: "Main battery ready." Signed and filed.
"""
POWER = """Terminal: FOLabMissouriPowerLog
Name: Ship's Power
Model: desk
Lock: average
Welcome:
  USS MISSOURI (BB-63)
  ENGINEERING - SHIP'S POWER
== Power log
Says:
  Boilers: cold.
  Deck solar panels: charging, daylight only.
  Wind turbine (fantail): charging.
  Vault cells: in use at night. Resupply by trade.
== Loads
Says:
  Searchlight: powered.
  Radio: powered.
  Secondary battery, one mount: powered.
  Main battery: not powered.
"""


def plan(gd, pr):
    import robots
    places = {recordio.field(r, 'EDID'): k for k, r in pr.records.items() if r.get('type') == 'CELL' and k.startswith('+')}
    rows, skipped = [], []
    for key, edid in PLACES.items():
        ck = places.get(edid)
        if not ck:
            skipped.append((key, edid + ' not in the mod'))
            continue
        got, why = robots.inside_spots(gd, pr, ck, ('butler',))
        if not got:
            skipped.append((key, why or 'no spot'))
            continue
        rows.append({'what': key, 'cell': ck, 'place': edid, 'spot': got[0][1], 'near': got[0][2]})
    return rows, skipped


def ops(gd, pr, P=None):
    import api_scripts
    import newgame
    import questrec as qr
    import terminals
    from activity import _new_key
    if any(recordio.field(r, 'EDID') == QUEST for r in pr.records.values()):
        raise ValueError('the mod already has %s (Undo first)' % QUEST)
    rows, skipped = P or plan(gd, pr)
    out, rep = [], {'terminals': [], 'skipped': skipped}
    quest_key, script_key, msg_key = _new_key(pr), _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': script_key, 'name': '', 'flags': {'start_enabled': True},
                             'priority': 50, 'delay': 1.0, 'stages': [], 'objectives': []})
    src = '\n'.join(['scn %s' % SCRIPT, 'short knows', 'short told', '', 'Begin GameMode',
                     '\tif knows && told == 0', '\t\tset told to 1', '\t\tShowMessage %s' % MESSAGE, '\tendif', 'End', ''])
    msg = newgame._message_record(MESSAGE, KNOWN)
    sc = api_scripts.scripts()
    c = sc.compile(src, script_key, 'quest', {quest_key: quest, msg_key: msg})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the bluff\'s script: %s' % (c,))
    srec = sc._record_of(c, SCRIPT)
    out += [{'op': 'record', 'key': msg_key, 'record': msg}, {'op': 'record', 'key': script_key, 'record': srec},
            {'op': 'record', 'key': quest_key, 'record': quest}]
    forms = terminals.mod_forms(gd, pr, {quest_key: quest, script_key: srec})
    forms.pr = _WithScript(pr, script_key, srec)
    for row in rows:
        spec = terminals.plan(FIRE if row['what'] == 'fire' else POWER)
        t_ops, t_keys = terminals.ops(gd, pr, spec, forms)
        for o in t_ops:
            k = _new_key(pr)
            assert k == t_keys[recordio.field(o['record'], 'EDID')]
            out.append({'op': 'record', 'key': k, 'record': o['record']})
        x, y, z, rz = row['spot']
        out.append({'op': 'place', 'cell': row['cell'], 'key': _new_key(pr),
                    'ref': {'base': t_keys[spec['edid']], 'p': [x, y, z - 4, 0.0, 0.0, rz], 's': 1.0}})
        rep['terminals'].append({'what': row['what'], 'place': row['place'], 'science': terminals.science_needed(spec),
                                 'spot': row['spot'], 'near': row['near']})
    return out, rep


class _WithScript:
    """The mod as the compiler sees it, with the bluff's script in already (a menu item's script sets its variable)."""

    def __init__(self, pr, key, rec):
        self._pr, self.records = pr, dict(pr.records)
        self.records[key] = rec

    def __getattr__(self, name):
        return getattr(self._pr, name)
