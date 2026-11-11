"""The mod's own new game: where New Game puts you, and what happens before you play.

A new game of New Vegas runs the Mojave's opening, Doc Mitchell's house (quest VCG01, start game enabled), which asks for
your name, face, S.P.E.C.I.A.L., tag skills and traits and then starts the main quest. A game of your own needs none
of that. Switched on, FOLab makes these ordinary parts of the mod and writes them again whenever the settings change:

  - a marker where you wake up: an XMarkerHeading, persistent, with an editor ID scripts can name (<P>NewGameStart);
  - a quest, start game enabled, and its script (<P>NewGame, <P>NewGameScript), compiled by scriptc like any other.
    The script moves you to the marker, sets the hour, and opens the screens you chose one after another, the way the
    game's own Character revision (VCG04ActivatorScript) does: GetPlayerName, ShowRaceMenu, SetSPECIALPoints 40,
    SetTagSkills 3, ShowTraitMenu. A menu stops GameMode, so the next one opens the moment the last one closes;
  - the Mojave's opening switched off: VCG01's Start game enabled flag cleared in an override, and, since the game
    sets it going at a new game all the same, its stages while the player is in bed emptied (_hush) and the quest
    stopped by the script whenever it runs. No Doc Mitchell, no main quest (VCG01 starts VMQ01 at its end);
  - what that opening did for every new game, done by the script: the white the film leaves cleared, and the Pip-Boy.
    The one the player's record carries counts as worn and shows nowhere, so it's taken away and a new one given and
    put on, in Doc Mitchell's order, WHILE THE LAST SCREEN IS OPEN: put on by script in play, a Pip-Boy goes through
    the game's queue and crashes it. Then the Pip-Boy's reset once more in play, once it's worn. This is what worked
    in the real game (11 Nov 2026, after eleven tries; each step's comment in source() says what failed without it);
  - by choice (both off unless ticked), other start quests switched off the same way: the pre-order packs and Courier's
    Stash, which put Mojave gear in your pack, and the DLCs' invitations, their radio signals. Each override is the
    whole quest, so the packs or DLCs become masters of the mod.

A save that has met Doc Mitchell (VCG01 running, or its stage 200 done) is not a new game of this mod: there the script
stops itself and moves nothing, so the mod can still be tried on an old save with Play here. (A save in the middle of his
house counted as new at first and was moved, 9 Nov 2026.)

What you start with (gear, S.P.E.C.I.A.L., skills, looks) is the player's own record, Player (NPC_ 7) on the Characters
page: the game hands you its inventory at a new game. A screen left out means you start as that record has it.

settings (project.newgame): {'on', 'cell', 'p': [x, y, z, facing], 'steps': [names from STEPS], 'hour', 'pipboy',
'quiet': [names from QUIET], 'made': {'marker': [cell, ref key], 'script': key, 'quest': key, 'quiet': [game quest keys]}}"""
import re

import recordio
import tes4

STEPS = [('name', 'Name', 'GetPlayerName'),
         ('face', 'Face and sex', 'ShowRaceMenu'),
         ('special', 'S.P.E.C.I.A.L.', 'SetSPECIALPoints 40'),
         ('tags', 'Tag skills', 'SetTagSkills 3'),
         ('traits', 'Traits', 'ShowTraitMenu')]
OPENING = 'VCG01'
HUSH_BELOW = 55     # (the opening's stages while the player is in bed, up to being let walk)
WORN_WAIT = 120   # (seconds to wait for the Pip-Boy to be on before giving up on its reset)
SETTLE = 1    # (seconds of play before the player is moved: the new game sets them up first)
QUIET = {'dlc': ('The DLCs\' invitations', 'radio signals and notes that start Dead Money, Honest Hearts, Old World Blues and Lonesome Road',
                 ['NVDLC01MQ00', 'NVDLC02MQ00', 'NVDLC03MQ00', 'NVDLC04MQ00']),
         'stash': ('Pre-order packs and the Courier\'s Stash', 'Mojave gear put in your pack at the start. Switching them off makes the packs masters of your mod, so players need them',
                   ['VPreorderClassic', 'VPreorderMercenary', 'VPreorderCaravan', 'VPreorderTribal', 'PreordVault13CanteenQuest'])}
START_ENABLED = 0x01
PLAYER = 0x7
DEFAULT = {'on': False, 'cell': None, 'p': None, 'steps': [s[0] for s in STEPS], 'hour': 8, 'pipboy': True, 'quiet': [], 'message': '',
           'made': {}}
MESSAGE_MAX = 1500      # (letters in the opening message: the game's own longest boxes are about this)
PERSISTENT = 0x400


def settings(pr):
    s = dict(DEFAULT)
    s.update(pr.newgame or {})
    s['made'] = dict(s.get('made') or {})
    return s


def prefix(pr):
    """The start of every editor ID the new game makes: the plugin's name in letters and numbers."""
    stem = re.sub(r'\.es[mp]$', '', pr.plugin, flags=re.I)
    words = re.findall(r'[A-Za-z0-9]+', stem)
    p = ''.join(w[:1].upper() + w[1:] for w in words)[:24]
    return p if p[:1].isalpha() else 'Mod' + p


def names(pr):
    p = prefix(pr)
    return {'marker': p + 'NewGameStart', 'quest': p + 'NewGame', 'script': p + 'NewGameScript', 'message': p + 'NewGameMessage'}


def menus(pr, s):
    """What the script opens once you've arrived, in order: the opening message if there is one, then the screens."""
    words = (s.get('message') or '').strip()
    return (['ShowMessage %s' % names(pr)['message']] if words else []) + [cmd for key, _label, cmd in STEPS if key in s['steps']]


def _message_record(edid, words):
    """A message box with OK, laid out as the game's own (PrimmSlimRepairFail and the like)."""
    return {'type': 'MESG', 'flags': 0, 'src': '', 'subs': [
        {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid},
        {'tag': 'DESC', 'label': 'Description', 'kind': 'z', 'value': words},
        {'tag': 'INAM', 'label': 'Icon', 'kind': 'F', 'value': ''},
        {'tag': 'DNAM', 'label': 'Flags', 'kind': 'struct', 'fields': [{'name': 'Flags', 'code': 'I', 'value': 1}]}]}


def quest_keys(gd, edids):
    """The loaded game's quests by editor ID (those not loaded are left out)."""
    want = {e.lower() for e in edids}
    out = []
    for fid, (_i, r) in sorted(gd.forms.items()):
        if r.tag == 'QUST' and tes4.zstr(gd.fields(fid).get('EDID', b'')).lower() in want:
            out.append(gd.key(fid))
    return out


def source(pr, s):
    """The start script's text."""
    n = names(pr)
    steps = menus(pr, s)
    lines = ['scn %s' % n['script'], '',
             '; Made by FOLab (My mod > Your own new game): it writes this again whenever the new game changes.',
             'short step', 'short worn', 'float pause', 'float waited', '',
             'begin GameMode', '',
             '\tif step == 0',
             '\t\tif GetQuestRunning %s == 1\t; (a game that has met Doc Mitchell: not a new game of this mod)' % OPENING,
             '\t\t\tStopQuest %s' % n['quest'],
             '\t\t\treturn',
             '\t\tendif',
             '\t\tif GetStageDone %s 200 == 1' % OPENING,
             '\t\t\tStopQuest %s' % n['quest'],
             '\t\t\treturn',
             '\t\tendif',
             # (the player's record carries the Pip-Boy from the first moment and it stays on: one put on by script
             # crashes the game, see _hush. Taking it off is safe)
             *([] if s['pipboy'] else ['\t\tplayer.RemoveItem PipBoy 1 1', '\t\tplayer.RemoveItem PipBoyGlove 1 1']),
             '\t\tset step to 1',
             # (a new game sets the player up in its own first moments: moving them half a second in crashed the
             # game in the real thing, 9 Nov 2026, while the new place loaded)
             '\t\tset pause to %s' % SETTLE,
             '\tendif',
             # (its start flag is off, but the game sets the opening going at a new game all the same: his scene came
             # along to the new place, the player in its bed pose and asked their name twice, 11 Nov 2026. Its early
             # stages are empty in the mod's copy (_hush); here it is stopped whenever it starts, and anything a stage
             # did put right: Victor away, the house's door broken, the fades, the controls, the bed camera)
             '\tif GetQuestRunning %s == 1' % OPENING,
             '\t\tStopQuest %s' % OPENING,
             '\t\tplayer.RemoveScriptPackage',
             '\t\tRemoveImageSpaceModifier VCG01FadeInFromBlackISFX',
             '\t\tRemoveImageSpaceModifier VCG01PlayerStrainISFX',
             '\t\tEnablePlayerControls',
             '\t\tVictorREF.Enable',
             '\t\tGSDocMitchellHouseIntDoorREF.SetDestroyed 0',
             '\tendif',
             '\tif pause > 0',
             '\t\tset pause to pause - GetSecondsPassed',
             '\t\treturn',
             '\tendif', '',
             '\tif step == 1',
             '\t\tif IsPlayerMovingIntoNewSpace == 1',
             '\t\t\treturn',
             '\t\tendif',
             '\t\tset step to 2',
             '\t\tset GameHour to %d' % int(s['hour']),
             '\t\tplayer.MoveTo %s' % n['marker'],
             '\t\tset pause to 1.5',
             '\telseif step == 2\t; (once the new place has loaded)',
             '\t\tif IsPlayerMovingIntoNewSpace == 1',
             '\t\t\treturn',
             '\t\tendif',
             '\t\tset step to 3',
             # (a new game begins all white, from the film before it, and the opening's first stage is what clears
             # that: with the stage empty the whole world stayed white, 11 Nov 2026. Cleared only here, once you've
             # arrived, so the moment in Doc Mitchell's house stays behind it)
             '\t\tRemoveImageSpaceModifier WhiteISFX',
             '\t\tset pause to 1']
    for k, cmd in enumerate(steps):
        lines += ['\telseif step == %d' % (k + 3), '\t\tset step to %d' % (k + 4), '\t\t' + cmd]
    if s['pipboy'] and steps:
        # (the reset once more, in play, when the Pip-Boy is really on: put on in a menu it goes through the game's
        # queue, so the reset there ran before it was worn and the arm stayed bare, 11 Nov 2026. Only once it's worn:
        # the crash was the Pip-Boy still in that queue)
        k = len(steps) + 3
        lines += ['\telseif step == %d' % k,
                  '\t\tset waited to waited + GetSecondsPassed',
                  '\t\tif player.GetEquipped PipBoy == 1',
                  '\t\t\tset step to %d' % (k + 1),
                  '\t\t\tset pause to 1',
                  '\t\telseif waited > %d' % WORN_WAIT,
                  '\t\t\tset step to %d' % (k + 2),
                  '\t\tendif',
                  '\telseif step == %d' % (k + 1),
                  '\t\tset step to %d' % (k + 2),
                  '\t\tResetPipboyManager']
    lines += ['\telse', '\t\tStopQuest %s' % n['quest'], '\tendif', '', 'end', '']
    if s['pipboy'] and steps:
        # (the player's record carries the Pip-Boy but nothing wears it: the arm came up bare, 11 Nov 2026. Put on by
        # script in play, it crashes the game, see _hush; the game's own handover is in Doc Mitchell's conversation,
        # a menu, so here it is put on while a screen is open, in his order, his reset last. The last screen, as his
        # handover comes after all his: put on during the first, it said so and the arm was still bare, the screens
        # after it making the player's body again)
        lines += ['begin MenuMode', '',
                  '\tif step > %d && worn == 0' % (len(steps) + 2),
                  '\t\tset worn to 1',
                  # (the one the record came with counts as worn and shows nowhere, so putting it on did nothing:
                  # taken away and a new one given, as the opening takes it and Doc Mitchell gives one)
                  '\t\tplayer.RemoveItem PipBoy 1 1',
                  '\t\tplayer.RemoveItem PipBoyGlove 1 1',
                  '\t\tplayer.AddItem PipBoy 1 1',
                  '\t\tplayer.AddItem PipBoyGlove 1 1',
                  '\t\tplayer.EquipItem PipBoy',
                  '\t\tplayer.EquipItem PipBoyGlove',
                  '\t\tResetPipboyManager',
                  '\tendif', '', 'end', '']
    return '\r\n'.join(lines)


def _quest_record(edid, script_key):
    return {'type': 'QUST', 'flags': 0, 'src': '', 'subs': [
        {'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid},
        {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': script_key},
        {'tag': 'DATA', 'label': 'Data', 'kind': 'struct', 'fields': [
            {'name': 'Flags', 'code': 'B', 'value': START_ENABLED}, {'name': 'Priority', 'code': 'B', 'value': 60},
            {'pad': '0000'}, {'name': 'Delay', 'code': 'f', 'value': 0.1}]}]}


def _start_flag(rec, on):
    """A copy of a quest record with Start game enabled set or cleared."""
    rec = {k: v for k, v in rec.items()}
    rec['subs'] = [dict(x) for x in rec['subs']]
    for sub in rec['subs']:
        if sub['tag'] == 'DATA':
            sub['fields'] = [dict(f) for f in sub['fields']]
            for f in sub['fields']:
                if f.get('name') == 'Flags':
                    f['value'] = (f['value'] | START_ENABLED) if on else (f['value'] & ~START_ENABLED)
    return rec


def _hush(rec, below=HUSH_BELOW):
    """A copy of the opening's quest whose early stages do nothing: each result script below this stage becomes a comment,
    stored the way the game stores its own comment-only stages (a header saying no code, the text, nothing else).
    The game sets the opening going at a new game whatever its start flag says, and its first stage takes the Pip-Boy
    off and lays the player in bed before any script of the mod's can stop it; a Pip-Boy put back on by script crashes
    the game (it goes through the queue of things to put on, and the Pip-Boy's manager runs that queue again before the
    entry is off it: crash dumps, 11 Nov 2026). With nothing in those stages the player keeps the Pip-Boy and their feet."""
    rec = {k: v for k, v in rec.items()}
    out, stage = [], None
    for sub in rec['subs']:
        tag = sub['tag']
        if tag == 'INDX':
            stage = sub['fields'][0]['value']
        elif tag in ('QOBJ', 'NNAM', 'QSTA') and stage is not None:
            stage = None                                    # (the objectives, after the stages)
        if stage is not None and stage < below:
            if tag in ('SCDA', 'SCRO', 'SLSD', 'SCVR', 'SCRV'):
                continue
            if tag == 'SCHR':
                sub = dict(sub, fields=[dict(f, value=0) if f.get('name') in ('Reference count', 'Compiled size', 'Variable count') else dict(f)
                                        for f in sub['fields']])
            elif tag == 'SCTX':
                sub = dict(sub, value=b'; switched off by FOLab: this mod has a new game of its own'.hex())
        out.append(sub)
    rec['subs'] = out
    return rec


def _marker_base(gd):
    return gd.key(next(fid for fid, (_i, r) in gd.forms.items()
                       if r.tag == 'STAT' and tes4.zstr(gd.fields(fid).get('EDID', b'')) == 'XMarkerHeading'))


class Problem(Exception):
    pass


def plan(gd, pr, compile_script, new):
    """The ops that make the mod's new game as new says (or take it all out when it's off): (label, ops, settings).
    compile_script(text, key, extra) -> a compiled script record (api_scripts' Scripts), raising Problem on a fault."""
    old = settings(pr)
    s = dict(old)
    s.update({k: v for k, v in (new or {}).items() if k in DEFAULT and k != 'made'})
    s['steps'] = [k for k, _l, _c in STEPS if k in (s.get('steps') or [])]
    s['quiet'] = [k for k in QUIET if k in (s.get('quiet') or [])]
    s['hour'] = max(0, min(23, int(s.get('hour') or 0)))
    s['message'] = str(s.get('message') or '').strip()[:MESSAGE_MAX]
    made = dict(old['made'])
    n = names(pr)
    ops = []
    # what was made before goes first (a marker is laid again where it's wanted: its key changes, so the script is made again too)
    if made.get('marker'):
        mk = made.pop('marker')[1]
        home = next((ck for ck, c in pr.cells.items() if mk in c.get('refs', {})), None)   # (outside, the square it went in)
        if home:
            ops.append({'op': 'remove', 'cell': home, 'ref': mk})
    want_quiet = set()
    if s['on']:
        want_quiet = set(quest_keys(gd, [OPENING] + [e for k in s['quiet'] for e in QUIET[k][2]]))
    opening = set(quest_keys(gd, [OPENING]))
    for key in made.get('quiet', []):
        if key not in want_quiet and key in pr.records:
            ops.append({'op': 'record_revert', 'key': key} if key in opening or _only_flag(gd, pr, key)
                       else {'op': 'record', 'key': key, 'record': _start_flag(pr.records[key], True)})
    if not s['on']:
        for k in ('script', 'quest', 'message'):
            if made.get(k):
                ops.append({'op': 'record_revert', 'key': made.pop(k)})
        made['quiet'] = []
        s['made'] = made
        ops.append({'op': 'newgame', 'settings': s})
        return 'Your own new game' + (' off' if old['on'] else ''), ops, s
    if not s.get('cell') or not s.get('p'):
        raise Problem('Pick where the new game starts first: right-click a spot in a place and choose Start a new game here.')
    # the marker: the next key the mod gives (the remove above makes none)
    marker_key = '+%06X' % pr.next_id
    ops.append({'op': 'add', 'cell': s['cell'], 'base': _marker_base(gd),
                'p': [float(s['p'][0]), float(s['p'][1]), float(s['p'][2]), 0.0, 0.0, float(s['p'][3])],
                'extra': {'persistent': True, 'edid': n['marker']}})
    nid = pr.next_id + 1
    extra = {marker_key: {'type': 'REFR', 'flags': PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': n['marker']}]}}
    # the opening message, a record of the mod's own while there are words for it (before the script, which names it)
    if s['message']:
        message = _message_record(n['message'], s['message'])
        message_key = made.get('message') or '+%06X' % nid
        if not made.get('message'):
            nid += 1
        ops.append({'op': 'record', 'key': message_key, 'record': message} if made.get('message') else {'op': 'record_new', 'record': message})
        made['message'] = message_key
        extra[message_key] = message
    elif made.get('message'):
        ops.append({'op': 'record_revert', 'key': made.pop('message')})
    script_key = made.get('script') or '+%06X' % nid
    if not made.get('script'):
        nid += 1
    quest_key = made.get('quest') or '+%06X' % nid
    extra[quest_key] = _quest_record(n['quest'], script_key)
    text = source(pr, s)
    script = compile_script(text, made.get('script'), extra)
    ops.append({'op': 'record', 'key': script_key, 'record': script} if made.get('script') else {'op': 'record_new', 'record': script})
    quest = _quest_record(n['quest'], script_key)
    ops.append({'op': 'record', 'key': quest_key, 'record': quest} if made.get('quest') else {'op': 'record_new', 'record': quest})
    for key in sorted(want_quiet):
        mine = key in pr.records and not (key in old['made'].get('quiet', []) and _only_flag(gd, pr, key))   # (a copy the mod changed itself)
        base = pr.records[key] if mine and key not in opening else _game_copy(gd, gd.from_key(key))
        ops.append({'op': 'record', 'key': key, 'record': _hush(_start_flag(base, False)) if key in opening else _start_flag(base, False)})
    made.update({'script': script_key, 'quest': quest_key, 'quiet': sorted(want_quiet), 'marker': [s['cell'], marker_key]})
    s['made'] = made
    ops.append({'op': 'newgame', 'settings': s})
    return 'Your own new game', ops, s


def _game_copy(gd, fid):
    """The quest as switching it off starts from: the whole of it, as the file that last has it says. (A bare one, only EDID
    and DATA, kept a pre-order pack from becoming a master, but its script went with it while the pack's other scripts read
    the quest's variables: New Game crashed in the real game, 9 Nov 2026.)"""
    return recordio.load(gd, fid)


def _only_flag(gd, pr, key):
    """Is the mod's copy of this game quest the game's own but for Start game enabled? (then putting it back is taking it out)"""
    try:
        game = _game_copy(gd, gd.from_key(key))
    except (KeyError, ValueError):
        return True
    return _start_flag(pr.records[key], True)['subs'] == _start_flag(game, True)['subs']


def view(gd, pr):
    """What the page shows."""
    s = settings(pr)
    place = world = None
    if s.get('cell'):
        c = s['cell']
        rec = pr.records.get(c) if c.startswith('+') else None
        if rec:
            place = recordio.field(rec, 'FULL') or recordio.field(rec, 'EDID')
        else:
            try:
                f = gd.fields(gd.from_key(c))
                place = tes4.zstr(f.get('FULL', b'')) or tes4.zstr(f.get('EDID', b''))
                if gd.from_key(c) in gd.ext_cells:
                    w = gd.ext_cells[gd.from_key(c)]
                    world = gd.key(w)
                    place = place or tes4.zstr(gd.fields(w).get('FULL', b'')) or tes4.zstr(gd.fields(w).get('EDID', b''))
            except (KeyError, ValueError):
                place = c
    quiet = [{'id': k, 'label': v[0], 'note': v[1], 'found': len(quest_keys(gd, v[2]))} for k, v in QUIET.items()]
    return {'settings': s, 'place': place, 'world': world, 'steps': [{'id': k, 'label': l} for k, l, _c in STEPS], 'quiet': quiet,
            'message_max': MESSAGE_MAX, 'pipboy_gap': bool(s['pipboy'] and not menus(pr, s)),   # (nothing open to put it on in)
            'names': names(pr), 'player': gd.key(PLAYER), 'player_changed': gd.key(PLAYER) in pr.records}
