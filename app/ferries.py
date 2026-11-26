"""Ferries round the island, each side's own, for a fare (the user, 25 Nov 2026: "travel ferries that offer quick travel ...
for a small fee. some faction dependent, huang ones aren't immediately accessible. pirates might have their own").

Built on boatferry.py's boats (the game's Boat03a as an activator by the shore, a menu, the quick fade, put ashore, hours
passed: only the game's own commands, so the same in nv-rs). Three lines (`LINES`), each its side's boats and money:

| Line | Stops | Fare | Who may sail |
|---|---|---|---|
| The court's | Waikiki, Hanauma Bay, Kāhala | 10 kala an hour of sailing | anyone the court isn't watching closely (its band 1 or more) |
| The pirates' | Kāhala, the Flotilla, Hawaiʻi Kai | 3 cells an hour | anyone the pirates deal with (a trader's "Let's deal." passed) or who has their respect (band 2) |
| The Huáng's | Waimānalo, Kailua, Kāneʻohe | 1 tongbao an hour | a guest of the Huáng (Through Makapuʻu Gate done) or one with face among them (band 3) |

Kāhala, where the two sides meet and trade, has one boat offering both its lines. The Huáng's line joins nothing else: you
reach it through their land. The fare: the pirates charge a soft touch (their band 0-1) double; Barter 50 talks any fare down
by a quarter; Shipwright (Repair 75) sails free. Can't pay, or not allowed: a message says why, and you stay ashore.

    plan(gd, pr)       {'rows': stops found, 'skipped'}
    apply(pr, gd, P)   one Undo
"""
import math

import recordio

LABEL = 'Ferries round the island'
# stop key: (button name, map marker, lines)
STOPS = {
    'waikiki': ('Waikiki', 'Ala Wai Boat Harbor', ('court',)),
    'hanauma': ('Hanauma Bay', 'Hanauma Bay', ('court',)),
    'kahala': ('Kahala', 'Kahala Reef', ('court', 'pirates')),
    'flotilla': ('The Flotilla', 'The Flotilla', ('pirates',)),
    'hawaiikai': ("Hawai'i Kai", 'Koko Marina', ('pirates',)),
    'waimanalo': ('Waimanalo', 'Blue Lagoon', ('huang',)),
    'kailua': ('Kailua', 'Kailua', ('huang',)),
    'kaneohe': ("Kane'ohe", "Kane'ohe", ('huang',)),
}
# line: (money item, fare an hour, its word for the money)
LINES = {'court': ('Caps001', 10, 'Kala'), 'pirates': ('AmmoSmallEnergyCell', 3, 'Cells'), 'huang': ('FOLabTongbao', 1, 'Tongbao')}
BARTER_LESS, SHIPWRIGHT = 50, 'FOLabPerkShipwright'
GUEST_QUEST = 'FOLabMakapuuGate'
EDIDS = {'boat': 'FOLabFerryBoatLine', 'boat_script': 'FOLabFerryLineBoatScript', 'quest': 'FOLabFerryLines',
         'quest_script': 'FOLabFerryLinesScript', 'not_now': 'FOLabFerryLinesNotNow'}
WORDS = {
    'court_no': "The court's boatmen won't carry someone the court is watching.",
    'pirates_no': "The pirates' boats don't carry strays. Deal with them first.",
    'huang_no': "The Huang boatmen look past you. They carry only those the Huang know.",
    'court_broke': "You can't pay the fare in kala.", 'pirates_broke': "You can't pay the fare in cells.",
    'huang_broke': "You can't pay the fare in tongbao.",
    'question': 'Where do you want to sail?', 'stay': 'Stay ashore',
    'not_now': "You can't sail while enemies are close.",
}
SEA_MOST = 100.0                                    # (water this high or lower is the sea)
REACH_MORE = (6000, 9000, 12000, 20000, 28000)     # (a town's marker inland: its bay further out)


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and r.get('subs') and recordio.field(r, 'EDID') == edid), None)


def _land(n):
    return 'FOLabFerryStop%d' % n


def _menu(n):
    return 'FOLabFerryLinesMenu%d' % n


def plan(gd, pr):
    """Each stop's boat water and arrival ground (boatferry.spots, stop by stop, looking further out where the marker is
    inland); a stop with no shore is left out, saying so."""
    import boatferry as B
    rep = {'rows': [], 'skipped': []}
    if _mod_key(pr, EDIDS['quest'], 'QUST'):
        rep['skipped'].append(('all', 'the mod already has its ferries (Undo first)'))
        return rep
    if _mod_key(pr, B.EDIDS['quest'], 'QUST'):
        rep['skipped'].append(('all', "the mod has boatferry.py's boats: these replace them, take those out first"))
        return rep
    keep_stops, keep_reach, keep_water = B.STOPS, B.REACH, B._water
    world = None

    def sea_only(gd_, pr_, world_, ck):
        level = keep_water(gd_, pr_, world_, ck)
        return level if level < SEA_MOST else -1.0e9           # (a pond or reservoir up a valley is no ferry stop)
    B._water = sea_only
    try:
        for key, (name, mark, lines) in STOPS.items():
            got = None
            for reach in REACH_MORE:
                B.STOPS, B.REACH = [(key, name, mark)], reach
                try:
                    got = B.spots(gd, pr)
                    break
                except ValueError as e:
                    err = str(e)
            if got:
                world = got['world']
                rep['rows'].append({'what': 'stop', 'key': key, 'name': name, 'lines': list(lines), 'boat': got['boat'][0],
                                    'land': got['land'][0], 'from_marker': got['from_marker'][0]})
            else:
                rep['skipped'].append((key, err))
    finally:
        B.STOPS, B.REACH, B._water = keep_stops, keep_reach, keep_water
    rep['world'] = world
    return rep


def _menus(stops):
    """For each stop (1-based): [(button, destination stop number, line)] its boat offers, in stop order."""
    out = {}
    for i, a in enumerate(stops, 1):
        dests = []
        for j, b in enumerate(stops, 1):
            if j == i:
                continue
            common = [l for l in a['lines'] if l in b['lines']]
            if common:
                dests.append((len(dests), j, common[0]))
        out[i] = dests
    return out


def _hours(a, b):
    import boatferry as B
    (x0, y0), (x1, y1) = a['land'][1][:2], b['land'][1][:2]
    return max(1, int(round(math.hypot(x1 - x0, y1 - y0) / B.UNITS_AN_HOUR)))


def quest_source(stops, menus, rules):
    """step 0 asks, 1 waits for a button and settles the fare, 2 fades (moved at MOVE_AT), 3 arrived."""
    import boatferry as B
    q = EDIDS['quest']
    L = ['scn ' + EDIDS['quest_script'], '', "; Made by FOLab (ferries.py): the island's ferries, each side's own, for a fare.",
         'short here', 'short dest', 'short step', 'short button', 'short line', 'short fare', 'short hours', 'float timer', '',
         'begin GameMode', '', '\tif step == 0', '\t\tif player.IsInCombat', '\t\t\tShowMessage %s' % EDIDS['not_now'],
         '\t\t\tset here to 0', '\t\t\tStopQuest %s' % q, '\t\t\treturn', '\t\tendif']
    for n in range(1, len(stops) + 1):
        L += ['\t\t%sif here == %d' % ('' if n == 1 else 'else', n), '\t\t\tShowMessage %s' % _menu(n)]
    L += ['\t\telse', '\t\t\tStopQuest %s' % q, '\t\t\treturn', '\t\tendif', '\t\tset dest to 0', '\t\tset step to 1', '\t\treturn', '\tendif', '',
          '\tif step == 1', '\t\tset button to GetButtonPressed', '\t\tif button < 0', '\t\t\treturn', '\t\tendif', '\t\tset line to 0']
    lines = list(LINES)
    first = True
    for i, dests in menus.items():
        for b, j, line in dests:
            L += ['\t\t%sif here == %d && button == %d' % ('' if first else 'else', i, b), '\t\t\tset dest to %d' % j,
                  '\t\t\tset line to %d' % (lines.index(line) + 1),
                  '\t\t\tset fare to %d' % (LINES[line][1] * _hours(stops[i - 1], stops[j - 1])),
                  '\t\t\tset hours to %d' % _hours(stops[i - 1], stops[j - 1])]
            first = False
    L += ['\t\tendif', '\t\tif dest == 0', '\t\t\tset here to 0', '\t\t\tset step to 0', '\t\t\tStopQuest %s' % q, '\t\t\treturn', '\t\tendif']
    # who may sail each line
    for n, line in enumerate(lines, 1):
        L += ['\t\tif line == %d && (%s)' % (n, rules[line]['refuse']), '\t\t\tShowMessage FOLabFerry%sNo' % line.capitalize(),
              '\t\t\tset here to 0', '\t\t\tset step to 0', '\t\t\tStopQuest %s' % q, '\t\t\treturn', '\t\tendif']
    # the fare: double for the pirates' soft touch, a quarter off at Barter 50, nothing with Shipwright
    L += ['\t\tif line == %d && %s' % (lines.index('pirates') + 1, rules['pirates']['soft']), '\t\t\tset fare to fare * 2', '\t\tendif',
          '\t\tif player.GetActorValue Barter >= %d' % BARTER_LESS, '\t\t\tset fare to fare * 3 / 4', '\t\t\tif fare < 1', '\t\t\t\tset fare to 1',
          '\t\t\tendif', '\t\tendif']
    if rules['shipwright']:
        L += ['\t\tif player.HasPerk %s' % SHIPWRIGHT, '\t\t\tset fare to 0', '\t\tendif']
    for n, line in enumerate(lines, 1):
        money = LINES[line][0]
        L += ['\t\tif line == %d' % n, '\t\t\tif player.GetItemCount %s < fare' % money, '\t\t\t\tShowMessage FOLabFerry%sBroke' % line.capitalize(),
              '\t\t\t\tset here to 0', '\t\t\t\tset step to 0', '\t\t\t\tStopQuest %s' % q, '\t\t\t\treturn', '\t\t\tendif',
              '\t\t\tif fare > 0', '\t\t\t\tplayer.RemoveItem %s fare' % money, '\t\t\tendif', '\t\tendif']
    L += ['\t\tApplyImageSpaceModifier %s' % B.FADE, '\t\tDisablePlayerControls', '\t\tset timer to 0', '\t\tset step to 2', '\t\treturn', '\tendif', '',
          '\tset timer to timer + GetSecondsPassed', '\tif step == 2 && timer > %.1f' % B.MOVE_AT]
    for n in range(1, len(stops) + 1):
        L += ['\t\t%sif dest == %d' % ('' if n == 1 else 'else', n), '\t\t\tplayer.MoveTo %s' % _land(n)]
    L += ['\t\tendif', '\t\tset GameHour to GameHour + hours', '\t\tset timer to 0', '\t\tset step to 3',
          '\telseif step == 3 && timer > %.1f' % B.BACK_AT, '\t\tEnablePlayerControls', '\t\tset here to 0', '\t\tset dest to 0',
          '\t\tset step to 0', '\t\tStopQuest %s' % q, '\tendif', '', 'end', '']
    return '\r\n'.join(L)


def boat_source(n_stops):
    import boatferry as B
    near = B.NEAR
    L = ['scn ' + EDIDS['boat_script'], '', "; Made by FOLab (ferries.py): a ferry; it finds which stop it's at and starts the trip.",
         '', 'begin OnActivate', '', '\tif IsActionRef player == 0', '\t\treturn', '\tendif',
         '\tif GetQuestRunning %s' % EDIDS['quest'], '\t\treturn', '\tendif', '\tset %s.here to 0' % EDIDS['quest']]
    for n in range(1, n_stops + 1):
        L += ['\t%sif GetDistance %s < %d' % ('' if n == 1 else 'else', _land(n), near), '\t\tset %s.here to %d' % (EDIDS['quest'], n)]
    L += ['\tendif', '\tif %s.here' % EDIDS['quest'], '\t\tStartQuest %s' % EDIDS['quest'], '\tendif', '', 'end', '']
    return '\r\n'.join(L)


def ops(gd, pr, P=None):
    import api_scripts
    import boatferry as B
    import money
    import newgame
    import questrec as qr
    from activity import _new_key
    P = P or plan(gd, pr)
    if any(w == 'all' for w, _x in P['skipped']):
        raise ValueError(P['skipped'][0][1])
    stops = [r for r in P['rows'] if r['what'] == 'stop']
    if len(stops) < 2:
        raise ValueError('fewer than two stops found: %s' % P['skipped'])
    menus = _menus(stops)
    out, extra, rep = [], {}, {'made': [], 'skipped': list(P['skipped'])}

    def record(edid, rec, key=None):
        k = key or _new_key(pr)
        extra[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(edid)
        return k
    # who may sail: conditions the script tests
    nq, nv = money._var_index(pr, 'FOLabNameOnWater')
    dq, dv = money._var_index(pr, 'FOLabPirateDeals')
    band = lambda side, op, n: ('FOLabNameOnWater.band%s %s %d' % (side, op, n)) if nq and ('band' + side) in nv else None
    court_refuse = band('court', '<', 1) or '0'
    pirate_ok = ' || '.join(x for x in ([band('pirates', '>=', 2)] + ['FOLabPirateDeals.%s == 1' % v for v in ('dealkahala', 'dealmarina') if dq and v in dv]) if x) or '1'
    guest = _mod_key(pr, GUEST_QUEST, 'QUST')
    huang_ok = ' || '.join(x for x in [band('huang', '>=', 3), 'GetQuestCompleted %s' % GUEST_QUEST if guest else None] if x) or '0'
    rules = {'court': {'refuse': court_refuse}, 'pirates': {'refuse': '(%s) == 0' % pirate_ok, 'soft': band('pirates', '<=', 1) or '0'},
             'huang': {'refuse': '(%s) == 0' % huang_ok}, 'shipwright': bool(_mod_key(pr, SHIPWRIGHT, 'PERK'))}
    # the messages
    for line in LINES:
        record('FOLabFerry%sNo' % line.capitalize(), B._message('FOLabFerry%sNo' % line.capitalize(), WORDS[line + '_no']))
        record('FOLabFerry%sBroke' % line.capitalize(), B._message('FOLabFerry%sBroke' % line.capitalize(), WORDS[line + '_broke']))
    record(EDIDS['not_now'], B._message(EDIDS['not_now'], WORDS['not_now']))
    for i, dests in menus.items():
        buttons = ['%s (%d %s)' % (stops[j - 1]['name'], LINES[line][1] * _hours(stops[i - 1], stops[j - 1]), LINES[line][2])
                   for _b, j, line in dests] + [WORDS['stay']]
        record(_menu(i), B._message(_menu(i), WORDS['question'], buttons))
    # the arrival markers (named, persistent) and their stand-ins for the compiler
    marker = gd.key(B._game_form(gd, 'XMarkerHeading', 'STAT'))
    lands = {}
    for n, s in enumerate(stops, 1):
        k = _new_key(pr)
        lands[n] = k
        cell, p = s['land']
        out.append({'op': 'place', 'cell': cell, 'key': k, 'ref': {'base': marker, 'p': p, 's': 1.0, 'persistent': True, 'edid': _land(n)}})
        extra[k] = {'type': 'REFR', 'flags': newgame.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': _land(n)}]}
    # the quest and the boat
    qk, qsk, bk, bsk = _new_key(pr), _new_key(pr), _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': EDIDS['quest'], 'script': qsk, 'name': '', 'flags': {}, 'priority': 0, 'delay': 0.1, 'stages': [], 'objectives': []})
    extra[qk] = quest
    sc = api_scripts.scripts()
    c = sc.compile(quest_source(stops, menus, rules), qsk, 'quest', extra)
    if not hasattr(c, 'subrecords'):
        raise ValueError('the ferries\' trip script: %s' % (c,))
    record(EDIDS['quest_script'], sc._record_of(c, EDIDS['quest_script']), qsk)
    record(EDIDS['quest'], quest, qk)
    c = sc.compile(boat_source(len(stops)), bsk, 'object', extra)
    if not hasattr(c, 'subrecords'):
        raise ValueError('the ferry boat script: %s' % (c,))
    record(EDIDS['boat_script'], sc._record_of(c, EDIDS['boat_script']), bsk)
    boat = B.boat_record(gd, bsk)
    recordio.set_field(boat, 'EDID', EDIDS['boat'], label='Editor ID')
    recordio.set_field(boat, 'FULL', 'Ferry')
    record(EDIDS['boat'], boat, bk)
    for s in stops:
        cell, p = s['boat']
        out.append({'op': 'place', 'cell': cell, 'key': _new_key(pr), 'ref': {'base': bk, 'p': p, 's': 1.0}})
    rep['stops'] = [(s['key'], s['lines'], s['from_marker']) for s in stops]
    rep['routes'] = {'%s-%s' % (stops[i - 1]['key'], stops[j - 1]['key']): '%s %d h, %d %s' % (line, _hours(stops[i - 1], stops[j - 1]),
                     LINES[line][1] * _hours(stops[i - 1], stops[j - 1]), LINES[line][2]) for i, d in menus.items() for _b, j, line in d}
    rep['who'] = {k: v.get('refuse') for k, v in rules.items() if isinstance(v, dict)}
    rep['keys'] = {'quest': qk}
    return out, rep


def apply(pr, gd, P=None):
    o, rep = ops(gd, pr, P)
    pr.apply(LABEL, o)
    return rep

