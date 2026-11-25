"""Storm forecasting (docs/waikiki-speech-science.md section J, system 8): a barometer to read on the terminals that would
keep one, telling how near the island's next storm is, more exactly the better your Science.

- **The reading:** the quest FOLabBarometer (start enabled, every few seconds) works out a `band` from the storm quest's
  own clock (FOLabStormQuest: `mode`, `bigdue`, `squalldue`, `started`; stormsched.py) and your Science.
  - Science 40 and up (`FINE`): the storm on now, a squall passing, the big storm within hours, a squall within hours,
    within a day, in a day or two, in two to four days, or not for days; and after a big storm, that the sea will be
    putting things ashore (only when the mod has stormafter's wrack: its `wrack` variable).
  - Under 40 (`ROUGH`): only the needle, low, lower than it was, or in the middle.
- **On the terminals** (`TARGETS`, those the mod has): one menu item "Read the barometer" for each band, its result text
  the reading, shown only while its band holds (a condition, GetQuestVariable FOLabBarometer band). The terminal's
  record is the mod's own, so the items are added to it. No script runs from the terminal.
  - **[proposal]** Which terminals keep a barometer is this step's choice: the Radar Dome's and the Missouri's fire control.

Nothing is placed or spoken.

    plan(gd, pr)       (rows, skipped)
    ops(gd, pr, P)     (ops, report): one Undo
"""
import json

import recordio

LABEL = 'Storm forecasting on the barometers'
QUEST, SCRIPT, STORM = 'FOLabBarometer', 'FOLabBarometerScript', 'FOLabStormQuest'
TARGETS = ['FOLabRadarDomeTerminal', 'FOLabMissouriFireControl']      # (one a place: the ship's fire control, not its power log)
SCIENCE = 40
ITEM = 'Read the barometer'
GETQUESTVARIABLE = 79
FINE = {      # band: (when, in the script's own words; what the reading says)
    1: ("FOLabStormQuest.mode == 2", "The needle is down past STORMY and still shaking. The big storm is on the island now."),
    2: ("FOLabStormQuest.mode == 1", "The needle dipped hard and is climbing back. A squall, passing over."),
    3: ("bigleft < 0.5", "The needle is falling fast. The big storm will be here within hours."),
    8: ("squallleft < 0.25", "The needle is dropping in short jerks. A squall within hours."),
    4: ("bigleft < 1", "Falling, deep and steady. The big storm comes within a day."),
    5: ("bigleft < 2", "Falling slowly. A big storm in a day or two."),
    6: ("bigleft < 4", "A slow fall has begun. A big storm in two to four days."),
    7: (None, "High and steady. No storm for days yet.")}
AFTER = (9, "Rising again after the storm. Whatever the sea took will be washing up on the beaches.")
ROUGH = {
    11: ("FOLabStormQuest.mode > 0 || bigleft < 0.5", "The needle is low. The weather's turning bad, or already has."),
    12: ("bigleft < 1.5 || squallleft < 0.25", "The needle is lower than it was. Hard to say what that means."),
    13: (None, "The needle points somewhere in the middle. It might mean anything.")}


def _key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _vars(rec):
    return {s['value'].lower() for s in rec['subs'] if s['tag'] == 'SCVR'}


def plan(gd, pr):
    rows, skipped = [], []
    if _key(pr, QUEST, 'QUST'):
        return rows, [(QUEST, 'already in the mod (Undo first)')]
    storm = _key(pr, STORM, 'QUST')
    sk = _key(pr, 'FOLabStormScript', 'SCPT')
    if not storm or not sk:
        return rows, [(STORM, 'the storms are not in the mod')]
    have = _vars(pr.records[sk])
    need = {'mode', 'bigdue', 'squalldue', 'started'}
    if not need <= have:
        return rows, [(STORM, 'its script lacks %s' % ', '.join(sorted(need - have)))]
    for e in TARGETS:
        k = _key(pr, e, 'TERM')
        (rows.append({'terminal': k, 'edid': e, 'wrack': 'wrack' in have}) if k else skipped.append((e, 'not in the mod')))
    return rows, skipped


def source(wrack, storm_wise=False):
    """storm_wise: Storm-Wise (perks.py) reads it exactly too, at any Science."""
    L = ['scn %s' % SCRIPT, '', 'short band', 'float bigleft', 'float squallleft', '', 'Begin GameMode',
         '\tset bigleft to FOLabStormQuest.bigdue - GameDaysPassed', '\tset squallleft to FOLabStormQuest.squalldue - GameDaysPassed',
         '\tif FOLabStormQuest.started == 0', '\t\tset bigleft to 99', '\t\tset squallleft to 99', '\tendif',
         '\tif player.GetActorValue Science >= %d%s' % (SCIENCE, ' || player.HasPerk FOLabPerkStormWise' if storm_wise else '')]

    def chain(bands, depth):
        first = True
        for b, (when, _words) in bands.items():
            if when is None:
                L.append('\t' * depth + 'else')
            else:
                L.append('\t' * depth + ('if ' if first else 'elseif ') + when)
            L.append('\t' * (depth + 1) + 'set band to %d' % b)
            first = False
        L.append('\t' * depth + 'endif')
    chain(FINE, 2)
    if wrack:
        L += ['\t\tif FOLabStormQuest.wrack == 1 && FOLabStormQuest.mode == 0', '\t\t\tset band to %d' % AFTER[0], '\t\tendif']
    L.append('\telse')
    chain(ROUGH, 2)
    L += ['\tendif', 'End', '']
    return '\n'.join(L)


def _cond(fn, op, value, p1=0, p2=0, run=0):
    return {'or': False, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def ops(gd, pr, P=None):
    import api_scripts
    import questrec as qr
    import terminals
    from activity import _new_key
    rows, skipped = P or plan(gd, pr)
    if not rows:
        raise ValueError('nothing to do: %s' % (skipped,))
    wrack = rows[0]['wrack']
    quest_key, script_key = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': script_key, 'name': '', 'flags': {'start_enabled': True},
                             'priority': 10, 'delay': 5.0, 'stages': [], 'objectives': []})
    sc = api_scripts.scripts()
    c = sc.compile(source(wrack, storm_wise=bool(_key(pr, 'FOLabPerkStormWise', 'PERK'))), script_key, 'quest', {quest_key: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('the barometer script: %s' % (c,))
    srec = sc._record_of(c, SCRIPT)
    index, last = {}, None
    for sub in srec['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            index[sub['value'].lower()] = last
    out = [{'op': 'record', 'key': script_key, 'record': srec}, {'op': 'record', 'key': quest_key, 'record': quest}]
    bands = [(b, w) for b, (_c, w) in FINE.items()] + ([AFTER] if wrack else []) + [(b, w) for b, (_c, w) in ROUGH.items()]
    for row in rows:
        rec = json.loads(json.dumps(pr.records[row['terminal']]))
        for b, words in bands:
            rec['subs'] += [terminals._z('ITXT', 'Menu item text', ITEM), terminals._z('RNAM', 'Result text', terminals._crlf(words)),
                            {'tag': 'ANAM', 'label': 'Menu item flags', 'kind': 'struct', 'fields': [{'name': 'Flags', 'code': 'B', 'value': 0}]}]
            rec['subs'] += qr.empty_parts() + [qr.condition_sub(_cond(GETQUESTVARIABLE, '=', b, quest_key, index['band']))]
        out.append({'op': 'record', 'key': row['terminal'], 'record': rec})
    return out, {'made': [QUEST, SCRIPT] + [r['edid'] for r in rows], 'terminals': [r['edid'] for r in rows],
                 'bands': len(bands), 'after_storm': wrack, 'skipped': skipped,
                 'keys': {'quest': quest_key, 'script': script_key}}
