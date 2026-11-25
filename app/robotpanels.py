"""Robots in a fight (docs/waikiki-speech-science.md section J, system 10): the ruins' hostile robots can be dealt with by
Science as well as by guns. The bank's two security Protectrons already go down from the bank's security terminal
(robots.py); this does the same for the crazed Mister Handys in the three ruined hotels.

Activating a hostile actor doesn't run its OnActivate in the game, so each robot has a **Maintenance Panel** near it (the
game's ControlPanel model; an activator of the mod's own, one a robot, its script naming its robot):
- **Under Science 50:** the wiring is past you (a message).
- **Science 50 and up:** a menu (message buttons).
  - "Shut it down" (KillActor): it drops for good and its parts are yours to loot. No experience for it.
  - "Reset it to service mode" (Science 75): it stops fighting and goes back to its rounds, harmless (StopCombat,
    Aggression 0, out of RobotFaction), and 25 experience (RewardXP). Nothing to loot.
  - "Leave it".
  So the trade-off is loot or experience, not a better way. Both are once only, and a dead robot leaves the panel dark.
- **The robots** get an editor ID and are made persistent (`ref_set`), so their panel's script can name them.
- **Where:** each panel stands on its place's navmesh `NEAR` from its robot's spot, clear of doors and arrivals, of anyone
  else standing and of seats (robots.py's rules), facing the robot.

    plan(gd, pr)       (rows, skipped)
    ops(gd, pr, P)     (ops, report): one Undo
"""
import math

import recordio

LABEL = 'Maintenance panels for the crazed robots'
CRAZED = 'FOLabRobotCrazedBellhop'
MODEL_FROM = 'ControlPanel'
SHUT, RESET = 50, 75
XP = 25
NEAR = (150.0, 700.0)
LEVEL = 100.0                   # (a floor this far under or over the robot counts as its own: a Mister Handy hovers)
WANT = 320.0                    # (the distance from the robot a panel is best at)
ROBOT_REF, PANEL, SCRIPT = 'FOLabCrazedBot%dREF', 'FOLabRobotPanel%d', 'FOLabRobotPanel%dScript'
MENU, LOW, NO_RESET, RESET_DONE, DARK = ('FOLabRobotPanelMenu', 'FOLabRobotPanelLowMsg', 'FOLabRobotPanelNoResetMsg',
                                         'FOLabRobotPanelResetMsg', 'FOLabRobotPanelDarkMsg')
WORDS = {
    MENU: ("A pre-war service panel, still live. Its readout calls the robot UNIT FAULT: GUEST HOSTILITY ROUTINE. "
           "You can see two ways in.", ['Shut it down', 'Reset it to service mode (Science 75)', 'Leave it']),
    LOW: ("A pre-war service panel, still live: a mess of service codes and wiring. You'd need to know more science to "
          "make sense of it. (Science 50)", []),
    NO_RESET: ("The service mode wants a code sequence you can't work out. (Science 75)", []),
    RESET_DONE: ("SERVICE MODE RESTORED. The robot goes back to its rounds.", []),
    DARK: ("The panel is dark. There's nothing more to do here.", []),
}


def _key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def robots_of(pr):
    """[(cell, ref key, (x, y, z, rz), edid it has)] of every crazed robot the mod placed."""
    base = _key(pr, CRAZED, 'CREA')
    out = []
    for ck, c in sorted(pr.cells.items()):
        for rk, r in sorted((c.get('refs') or {}).items()):
            if r.get('base') == base and not r.get('removed') and r.get('p'):
                p = r['p']
                out.append((ck, rk, (p[0], p[1], p[2], p[5] if len(p) > 5 else 0.0), r.get('edid')))
    return out


def _spot(gd, pr, ck, robot, taken):
    import robots as R
    tris = R._tris(gd, pr, ck)
    doors, actors, seats = R._things(gd, pr, ck)
    others = [a for a in actors if R._d(a, robot) > 1.0] + list(taken)
    best = None
    for p in tris:
        d = R._d(p, robot)
        if not NEAR[0] <= d <= NEAR[1] or abs(p[2] - robot[2]) > LEVEL:
            continue
        if (min((R._d(p, q) for q in doors), default=1e9) < R.DOOR_CLEAR or min((R._d(p, q) for q in others), default=1e9) < R.APART
                or min((R._d(p, q) for q in seats), default=1e9) < R.SEAT_CLEAR):
            continue
        score = abs(d - WANT)
        if best is None or score < best[0]:
            best = (score, p)
    if not best:
        return None
    p = best[1]
    rz = math.atan2(robot[0] - p[0], robot[1] - p[1])
    return (round(p[0], 1), round(p[1], 1), round(p[2], 1), round(rz, 4))


def plan(gd, pr):
    rows, skipped = [], []
    if _key(pr, PANEL % 1, 'ACTI'):
        return rows, [(PANEL % 1, 'already in the mod (Undo first)')]
    if not _key(pr, CRAZED, 'CREA'):
        return rows, [(CRAZED, 'not in the mod (robots first)')]
    taken = []
    for n, (ck, rk, p, edid) in enumerate(robots_of(pr), 1):
        s = _spot(gd, pr, ck, p, taken)
        name = recordio.field(pr.records.get(ck) or {'subs': []}, 'EDID') or ck
        if not s:
            skipped.append((name, 'no spot for a panel near its robot'))
            continue
        taken.append(s)
        rows.append({'n': n, 'cell': ck, 'place': name, 'robot': rk, 'robot_at': [round(v, 1) for v in p], 'edid': edid,
                     'panel': s, 'apart': round(math.dist(s[:3], p[:3]))})
    return rows, skipped


def source(n, robot):
    return '\n'.join([
        'scn %s' % (SCRIPT % n), '', 'short asking', 'short finished', 'short btn', '',
        'Begin OnActivate',
        '\tif IsActionRef player == 0', '\t\treturn', '\tendif',
        '\tif finished || %s.GetDead' % robot, '\t\tShowMessage %s' % DARK,
        '\telseif player.GetActorValue Science < %d' % SHUT, '\t\tShowMessage %s' % LOW,
        '\telse', '\t\tShowMessage %s' % MENU, '\t\tset asking to 1', '\tendif',
        'End', '',
        'Begin GameMode',
        '\tif asking', '\t\tset btn to GetButtonPressed',
        '\t\tif btn == 0', '\t\t\tset asking to 0', '\t\t\tset finished to 1', '\t\t\t%s.KillActor' % robot,
        '\t\telseif btn == 1', '\t\t\tset asking to 0',
        '\t\t\tif player.GetActorValue Science >= %d' % RESET,
        '\t\t\t\tset finished to 1', '\t\t\t\t%s.StopCombat' % robot, '\t\t\t\t%s.SetActorValue Aggression 0' % robot,
        '\t\t\t\t%s.RemoveFromFaction RobotFaction' % robot, '\t\t\t\tRewardXP %d' % XP, '\t\t\t\tShowMessage %s' % RESET_DONE,
        '\t\t\telse', '\t\t\t\tShowMessage %s' % NO_RESET, '\t\t\tendif',
        '\t\telseif btn == 2', '\t\t\tset asking to 0', '\t\tendif', '\tendif',
        'End', ''])


def ops(gd, pr, P=None):
    import api_characters as ac
    import api_scripts
    from activity import _new_key
    from generators import _message
    from surffish import _copy
    rows, skipped = P or plan(gd, pr)
    if not rows:
        raise ValueError('nothing to do: %s' % (skipped,))
    out, extra = [], {}
    for edid, (words, buttons) in WORDS.items():
        k = _new_key(pr)
        extra[k] = _message(edid, words, buttons)
        out.append({'op': 'record', 'key': k, 'record': extra[k]})
    made = list(WORDS)
    placed = []
    for row in rows:
        n = row['n']
        robot = row['edid'] or ROBOT_REF % n
        if not row['edid']:
            out.append({'op': 'ref_set', 'cell': row['cell'], 'ref': row['robot'], 'set': {'edid': robot, 'persistent': True}})
        panel_key, script_key = _new_key(pr), _new_key(pr)
        panel = _copy(gd, 'ACTI', MODEL_FROM, PANEL % n, 'Maintenance Panel')
        panel['subs'] = [s for s in panel['subs'] if s['tag'] != 'SCRI']
        ac.insert(panel, {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': script_key})
        stand_in = {'type': 'REFR', 'flags': 0x400, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': robot}]}
        sc = api_scripts.scripts()
        c = sc.compile(source(n, robot), script_key, 'object', dict(extra, **{panel_key: panel, row['robot']: stand_in}))
        if not hasattr(c, 'subrecords'):
            raise ValueError('a panel script: %s' % (c,))
        out += [{'op': 'record', 'key': script_key, 'record': sc._record_of(c, SCRIPT % n)},
                {'op': 'record', 'key': panel_key, 'record': panel},
                {'op': 'place', 'cell': row['cell'], 'key': _new_key(pr),
                 'ref': {'base': panel_key, 'p': [row['panel'][0], row['panel'][1], row['panel'][2], 0.0, 0.0, row['panel'][3]], 's': 1.0}}]
        made += [PANEL % n, SCRIPT % n]
        placed.append({'place': row['place'], 'robot': robot, 'apart': row['apart']})
    return out, {'made': made, 'panels': placed, 'skipped': skipped}

