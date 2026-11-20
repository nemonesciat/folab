"""The Castaway's opening talk (docs/waikiki-story-plan.md, "The opening, step by step", decided 19 Nov 2026).

You lie on the sand at Hanauma; the beachcomber picking over the wreck shakes you awake and talks you through what
New Vegas does at Doc Mitchell's: each of the game's character screens opens from a line of the talk, in his order,
and the talk goes on when the screen closes. The Pip-Boy, taken off the drowned man by the rocks, is handed over and
put on while the conversation is open (the one way the game takes it safely: one put on by script in play crashed it,
newgame.py's notes), and its manager reset once it's worn.

Made here, as ordinary parts of the mod:
  - the beachcomber (`COMBER`, a copy of the game's prospector), stood at the comber's marker, told to stay there;
  - the quest `QUEST` (start game enabled) and its script: waits for a fresh game (`GameDaysPassed` under 1: an old save
    never gets it) and for the new game's own start to have run, holds you lying (controls off), then runs the talk:
    each line's result sets `want`, the script opens that screen in play and starts the next topic when it closes;
  - one topic a step (`STEPS`), each a single silent line, the four answers to "Where'd they take you from?" as
    choices (`FROM`), the answer kept in the quest's `origin`.
The mod's new game then opens no screens of its own and gives no Pip-Boy (`newgame` settings: steps [], pipboy off):
this does both.

`build(server)` applies it (several Undo steps) to server.PR and returns a report; `update(server)` makes the script
again from `script_source` and stands the beachcomber at your side (`BESIDE` from where you wake, facing you)."""
import json

QUEST = 'FOLabCastawayOpening'
SCRIPT = 'FOLabCastawayOpeningScript'
COMBER = 'FOLabBeachcomber'
COMBER_REF = 'FOLabBeachcomberREF'
COMBER_NAME = 'Beachcomber'
TEMPLATE = 'NVProspectorMale'
STAY = 'DefaultStayAtEditorLocation'
COMBER_SPOT = ('Waikiki.esp:000CB6', '+0A1904')        # (castaway.py's FOLabHanaumaComber marker)

# (topic editor ID, the words, what the line's result asks the script for: a screen's number, or 0 for none)
STEPS = [
    ('FOLabCastaway1Wake', "Still breathing. Don't try to get up yet. Here. See what the sea left of you.", 1),       # face
    ('FOLabCastaway2Name', "Got a name?", 2),                                                                          # name
    ('FOLabCastaway3Look', "Grip my hand. Now follow my finger. Can you sit up? You'll live. Let's see what's left.", 3),  # SPECIAL
    ('FOLabCastaway4From', "Where'd they take you from?", 0),                                                          # (answered by a choice)
    ('FOLabCastaway5Skills', "What were you, before? What could you do?", 5),                                          # tag skills
    ('FOLabCastaway6Traits', "Anything else wrong with you I should know about?", 6),                                 # traits
    ('FOLabCastaway7PipBoy', "This was on the one by the rocks. He won't need it.", 7),                               # the Pip-Boy
    ('FOLabCastaway8Road', "Road's up there, over the rim. Don't go north.", 8),                                      # you stand
]
FROM = [('FOLabCastawayFromIsland', 'Another island.', "Another island. They come over the sea for people, same as anywhere."),
        ('FOLabCastawayFromShip', 'A ship from the mainland.', "The mainland. Long way to come to end up in a hold."),
        ('FOLabCastawayFromOahu', 'Somewhere here, on the island.', "Here, then. Sold by your own, most like. Don't go home asking why."),
        ('FOLabCastawayFromNone', "I don't remember.", "Don't remember. Might be a mercy.")]
RETRY, TRIES, GIVE_UP = 6, 4, 240     # (seconds of play a line has to answer; asks a step gets; seconds in all)
SCREENS = {1: 'ShowRaceMenu', 2: 'GetPlayerName', 3: 'SetSPECIALPoints 40', 5: 'SetTagSkills 3', 6: 'ShowTraitMenu'}


def script_source(newgame_quest):
    """The opening as a scene that can't be left half done (what an opening like Doc Mitchell's must do: get a new
    character ready to play, whatever happens):
      - held: from the first frame no walking, fighting or Pip-Boy; the beachcomber made essential and unaggressive, kept out
        of fights; nothing hostile near (removed from the bay, castawaytalk.clear_ops);
      - one step at a time: `step` is the step now (1-8). Its line is asked for (StartConversation) once; the line's
        result script answers in `want`. A screen asked for opens in play and the next step's line comes once it shuts;
      - knocked off course, picked up again: a step whose line hasn't answered within `RETRY` seconds of play (the talk
        cut short, never started) has its line asked for again;
      - never stuck: after `TRIES` tries at one step, or `GIVE_UP` seconds in all, the script does the rest itself (the
        screens left, then the Pip-Boy put on during the last of them as newgame does), so the character is always
        finished; controls given back last, every way;
      - once: never on an old save (a new game starts at day 5), and `step` 9 is done for good."""
    topics = [t for t, _w, _s in STEPS]
    L = ['scn ' + SCRIPT, '',
         '; Made by FOLab (castawaytalk.py): the Castaway\'s opening on the beach at Hanauma. See its notes.',
         'short step', 'short want', 'short origin', 'short asked', 'short tries', 'short alone', 'short worn', 'short shut',
         'float pause', 'float waited', 'float since', 'float total', 'short talked', '',
         'begin GameMode', '',
         '\tif step == 9',
         '\t\treturn',
         '\tendif',
         '\tif step == 0',
         # (a new game of New Vegas starts at day 5, GameDaysPassed's own value: "> 1" stopped the talk in every new game,
         # 19 Nov 2026. More than a day of play after that is an old save)
         '\t\tif GameDaysPassed > 6',
         '\t\t\tset step to 9',
         '\t\t\tStopQuest %s' % QUEST,
         '\t\t\treturn',
         '\t\tendif',
         '\t\tif GetQuestRunning %s == 1\t; (the new game still moving you here)' % newgame_quest,
         '\t\t\treturn',
         '\t\tendif',
         '\t\tif player.GetDistance %s > 3000' % COMBER_REF,
         '\t\t\treturn',
         '\t\tendif',
         '\t\tDisablePlayerControls 1 1 1 0 0 1 0',
         '\t\t%s.SetActorValue Aggression 0' % COMBER_REF,
         '\t\tset step to 1',
         '\t\tset pause to 0.3',
         '\tendif',
         '\tset total to total + GetSecondsPassed',
         '\tif pause > 0',
         '\t\tset pause to pause - GetSecondsPassed',
         '\t\treturn',
         '\tendif',
         # (never stuck: too long in all, or too many tries at one step, and the rest is done without the talk)
         '\tif alone == 0 && (total > %d || tries > %d)' % (GIVE_UP, TRIES),
         '\t\tset alone to 1',
         '\tendif',
         '']
    # ---- a step's talk shown and over (the dialogue was open since its line was asked for, and is shut now): what
    # the step does next. Not from the lines' own result scripts: those never took effect in the game, 19 Nov 2026
    # (the first line said, the talk shut, the same line again and again) ----
    L += ['\tif alone == 0 && asked == 1 && talked == 1',
          '\t\tset talked to 0',
          '\t\tset asked to 0',
          '\t\tset tries to 0']
    for k, cmd in SCREENS.items():
        L += ['\t\tif step == %d' % k, '\t\t\tset step to %d' % (k + 1),
              '\t\t\tset pause to 0.5\t; (counted in play only: the next line half a second after the screen shuts)',
              '\t\t\t' + cmd, '\t\t\treturn', '\t\tendif']
    L += ['\t\tif step == 4\t; (where you\'re from, answered)', '\t\t\tset step to 5', '\t\t\tset pause to 0.5', '\t\t\treturn', '\t\tendif',
          '\t\tif step == 8', '\t\t\tset step to 99', '\t\tendif',
          '\t\t; (step 7: the Pip-Boy was put on while its line was open; if it wasn\'t, its line is asked for again)',
          '\tendif',
          '\tif step == 7 && worn == 1\t; (the Pip-Boy put on in a menu: reset in play once it is really worn)',
          '\t\tset waited to waited + GetSecondsPassed',
          '\t\tif player.GetEquipped PipBoy == 1 || waited > 30',
          '\t\t\tResetPipboyManager',
          '\t\t\tset worn to 2',
          '\t\t\tset want to 0',
          '\t\t\tset step to 8',
          '\t\t\tset asked to 0',
          '\t\t\tset tries to 0',
          '\t\t\tset pause to 1',
          '\t\tendif',
          '\t\treturn',
          '\tendif',
          '']
    # ---- on our own: the screens left, the Pip-Boy, done ----
    L += ['\tif alone == 1 && step < 9']
    for k, cmd in SCREENS.items():
        L += ['\t\tif step == %d' % k, '\t\t\tset step to %d' % (k + 1), '\t\t\tset pause to 0.5', '\t\t\t' + cmd, '\t\t\treturn', '\t\tendif']
    L += ['\t\tif step == 4', '\t\t\tset step to 5', '\t\t\treturn', '\t\tendif',
          '\t\tif step == 7 && worn == 0\t; (no screen left to put it on in: one opened for it, the traits shown again)',
          '\t\t\tset shut to 1',
          '\t\t\tShowTraitMenu',
          '\t\t\treturn',
          '\t\tendif',
          '\t\tif step == 8', '\t\t\tset step to 99', '\t\tendif',
          '\tendif',
          '']
    # ---- done, every way ----
    L += ['\tif step == 99',
          '\t\tEnablePlayerControls',
          '\t\tif player.GetEquipped PipBoy == 0 && worn < 2\t; (whatever happened, you leave with it on)',
          '\t\t\tplayer.AddItem PipBoy 1 1',
          '\t\t\tplayer.EquipItem PipBoy',
          '\t\tendif',
          '\t\tset step to 9',
          '\t\tStopQuest %s' % QUEST,
          '\t\treturn',
          '\tendif',
          '']
    # ---- the step's line asked for, and asked again if it doesn't answer ----
    L += ['\tif alone == 0 && step >= 1 && step <= 8',
          '\t\tif asked == 0',
          '\t\t\tset asked to 1',
          '\t\t\tset since to 0',
          '\t\t\tset tries to tries + 1']
    for k, topic in enumerate(topics, start=1):
        L += ['\t\t\tif step == %d' % k, '\t\t\t\t%s.StartConversation PlayerREF %s' % (COMBER_REF, topic), '\t\t\tendif']
    L += ['\t\telse',
          '\t\t\tset since to since + GetSecondsPassed',
          '\t\t\tif since > %d\t; (no answer in play this long: the talk cut short or never started)' % RETRY,
          '\t\t\t\tset asked to 0',
          '\t\t\tendif',
          '\t\tendif',
          '\tendif',
          '', 'end', '',
          'begin MenuMode', '',
          # (the Pip-Boy: given and put on while a menu is open, the one way the game takes it: in the talk when its line
          # is on screen, or, done alone, while the traits screen shown for it is open)
          '\tif MenuMode 1009\t; (the dialogue: the step\'s line is being shown)',
          '\t\tif asked == 1',
          '\t\t\tset talked to 1',
          '\t\tendif',
          '\tendif',
          '\tif worn == 0 && ((step == 7 && asked == 1 && MenuMode 1009) || shut == 1)',
          '\t\tset worn to 1',
          '\t\tplayer.RemoveItem PipBoy 1 1',
          '\t\tplayer.RemoveItem PipBoyGlove 1 1',
          '\t\tplayer.AddItem PipBoy 1 1',
          '\t\tplayer.AddItem PipBoyGlove 1 1',
          '\t\tplayer.EquipItem PipBoy',
          '\t\tplayer.EquipItem PipBoyGlove',
          '\t\tResetPipboyManager',
          '\t\tset want to 0',
          '\t\tset step to 7',
          '\tendif', '', 'end', '']
    return '\r\n'.join(L)


def build(server, apply=True):
    import api_characters as ac
    import api_quests as aq
    import api_scripts
    import newgame
    import questrec as qr
    import recordio
    gd, pr = server.GD, server.PR
    rep = {}
    edit = (lambda label, ops: server.edit(label, ops)) if apply else (lambda label, ops: {'ops': ops})
    if not apply:
        raise ValueError('build(apply=False) is not supported: records are made in steps that name each other')
    # 1. the beachcomber, the quest (no script yet), the topics
    tmpl = gd.key(ac._find(gd, 'NPC_', TEMPLATE))
    npc = json.loads(json.dumps(ac.get_record(gd, pr, tmpl)))
    recordio.set_field(npc, 'EDID', COMBER, label='Editor ID')
    full = ac.one(npc, 'FULL')
    if full:
        full['value'] = COMBER_NAME
    else:
        ac.insert(npc, {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': COMBER_NAME})
    npc['subs'] = [s for s in npc['subs'] if s['tag'] not in ('SCRI', 'PKID')]
    ac.insert(npc, {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': gd.key(ac._find(gd, 'PACK', STAY))})
    ac.set_num(npc, 'ACBS', 'Flags', ac.num(npc, 'ACBS', 'Flags') & ~0x2)
    npc['src'] = npc.get('src') or ''
    npc['copied_from'] = tmpl
    keys = aq._reserve(pr, 3 + len(STEPS) + len(FROM))
    npc_key, script_key, quest_key = keys[0], keys[1], keys[2]
    topic_keys = keys[3:3 + len(STEPS)]
    from_keys = keys[3 + len(STEPS):]
    ops = [{'op': 'record_new', 'record': npc}]
    # (the script's place is taken first so the quest can name it; filled in step 2)
    ops.append({'op': 'record_new', 'record': {'type': 'SCPT', 'flags': 0, 'src': '', 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': SCRIPT}]}})
    quest = newgame._quest_record(QUEST, script_key)
    ops.append({'op': 'record_new', 'record': quest})
    for (edid, _w, _s) in STEPS:
        ops.append({'op': 'record_new', 'record': qr.topic_record({'edid': edid, 'name': '', 'priority': 50.0, 'kind': 0, 'quests': [{'quest': quest_key, 'links': []}]})})
    for (edid, prompt, _w) in FROM:
        ops.append({'op': 'record_new', 'record': qr.topic_record({'edid': edid, 'name': prompt, 'priority': 50.0, 'kind': 0, 'quests': [{'quest': quest_key, 'links': []}]})})
    cell, marker = COMBER_SPOT
    mp = pr.cells[cell]['refs'][marker]['p']
    ops.append({'op': 'add', 'cell': cell, 'base': npc_key, 'p': [mp[0], mp[1], mp[2], 0.0, 0.0, mp[5]], 'extra': {'persistent': True, 'edid': COMBER_REF}})
    edit('The beachcomber and the opening\'s topics', ops)
    assert pr.records[npc_key]['type'] == 'NPC_' and pr.records[quest_key]['type'] == 'QUST', 'keys not as reserved'
    # 2. the script, compiled now the quest, topics and the beachcomber's ref exist
    made = newgame.settings(pr)['made']
    ng_quest = recordio.field(pr.records[made['quest']], 'EDID') if made.get('quest') else None
    if not ng_quest:
        raise ValueError('the mod has no new game of its own to follow')
    sc = api_scripts.scripts()
    # (the beachcomber's ref by its editor ID, as newgame names its marker: placed refs aren't records the compiler finds)
    ref_key = next(rk for rk, r in pr.cells[cell]['refs'].items() if r.get('edid') == COMBER_REF)
    extra = {quest_key: pr.records[quest_key],
             ref_key: {'type': 'REFR', 'flags': newgame.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': COMBER_REF}]}}
    c = sc.compile(script_source(ng_quest), script_key, 'quest', extra)
    edit('The opening\'s script', [{'op': 'record', 'key': script_key, 'record': sc._record_of(c, c.name)}])
    rep['script_vars'] = [v for v in getattr(c, 'variables', [])] if hasattr(c, 'variables') else None
    # 3. the lines
    lines = []
    for k, ((edid, words, want), tkey) in enumerate(zip(STEPS, topic_keys)):
        l = aq.new_line_plain(gd, pr, tkey, quest_key, npc_key, words, goodbye=(edid != 'FOLabCastaway4From'))
        if want == 7:
            l['begin'] = {'source': 'set %s.want to 70' % QUEST}
        elif want:
            l['end'] = {'source': 'set %s.want to %d' % (QUEST, want)}
        if edid == 'FOLabCastaway4From':
            l['choices'] = list(from_keys)
        lines.append(l)
    for k, ((edid, prompt, reply), fkey) in enumerate(zip(FROM, from_keys), start=1):
        l = aq.new_line_plain(gd, pr, fkey, quest_key, npc_key, reply, goodbye=True)
        l['end'] = {'source': 'set %s.origin to %d\r\nset %s.want to 4' % (QUEST, k, QUEST)}
        lines.append(l)
    edit('The opening\'s lines', [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines])
    rep['lines'] = len(lines)
    # 4. the new game opens no screens and gives no Pip-Boy of its own now: the talk does both
    server.new_game({'steps': [], 'pipboy': False})
    rep.update({'npc': npc_key, 'quest': quest_key, 'script': script_key, 'topics': topic_keys + from_keys})
    return rep


BESIDE = 90.0               # (the beachcomber this far from where you wake, crouched at your side)
WAKE_SPOT = ('Waikiki.esp:000CB6', '+0A1902')    # (castaway.py's FOLabHanaumaWake marker)


def update(server):
    """The script made again from script_source, the beachcomber stood at your side facing you, the new game's own
    message taken out (nothing before the scene). One Undo step each. Returns a report."""
    import math
    import api_scripts
    import newgame
    import recordio
    gd, pr = server.GD, server.PR
    quest_key = next(k for k, r in pr.records.items() if r.get('type') == 'QUST' and recordio.field(r, 'EDID') == QUEST)
    script_key = recordio.field(pr.records[quest_key], 'SCRI')
    cell, wake = WAKE_SPOT
    wp = pr.cells[cell]['refs'][wake]['p']
    ref_cell, ref_key = next((ck, rk) for ck, c in pr.cells.items() for rk, r in c.get('refs', {}).items() if r.get('edid') == COMBER_REF)
    r = pr.cells[ref_cell]['refs'][ref_key]
    # (at your side, a step off the way you face, turned to look at you)
    face = wp[5]
    sx, sy = wp[0] + math.sin(face + 1.2) * BESIDE, wp[1] + math.cos(face + 1.2) * BESIDE
    look = math.atan2(wp[0] - sx, wp[1] - sy) % math.tau
    server.edit("The beachcomber at your side", [{'op': 'move', 'cell': ref_cell, 'ref': ref_key, 'p': [round(sx, 1), round(sy, 1), wp[2], 0.0, 0.0, round(look, 4)]}])
    made = newgame.settings(pr)['made']
    ng_quest = recordio.field(pr.records[made['quest']], 'EDID')
    sc = api_scripts.scripts()
    extra = {quest_key: pr.records[quest_key],
             ref_key: {'type': 'REFR', 'flags': newgame.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': COMBER_REF}]}}
    c = sc.compile(script_source(ng_quest), script_key, 'quest', extra)
    server.edit("The opening's script", [{'op': 'record', 'key': script_key, 'record': sc._record_of(c, c.name)}])
    server.new_game({'message': ''})
    return {'beside': [round(sx), round(sy)], 'script': script_key}


CLEAR = 10000.0             # (nothing hostile within this of where you wake: the bay and the way up out of it)
HOSTILE_WORDS = ('Ghoul', 'Gecko', 'Fiend', 'Raider', 'Cazador', 'Deathclaw', 'Mantis', 'Radscorpion', 'Scorpion', 'Coyote',
                 'Dog', 'Bloatfly', 'Rat', 'Roach', 'Lakelurk', 'Nightstalker', 'Mutant', 'Spore', 'Ant', 'Viper', 'Jackal')


def clear_ops(gd, pr, start=(96780.0, -36200.0)):
    """The hostile creatures and actors placed within CLEAR of the start, taken out (a ghoul there pulled the
    beachcomber into a fight after his first line, 19 Nov 2026). Returns (ops, names)."""
    import math
    ops, names = [], []
    for ck, c in pr.cells.items():
        for rk, r in c.get('refs', {}).items():
            p, b = r.get('p'), r.get('base')
            if not p or not b or r.get('removed') or b.startswith('+') or math.hypot(p[0] - start[0], p[1] - start[1]) > CLEAR:
                continue
            try:
                f = gd.from_key(b)
                tag, e = gd.forms[f][1].tag, gd.edid(f) or ''
            except (KeyError, ValueError):
                continue
            if tag in ('CREA', 'NPC_', 'LVLC', 'LVLN') and any(w in e for w in HOSTILE_WORDS):
                ops.append({'op': 'remove', 'cell': ck, 'ref': rk})
                names.append(e)
    return ops, names


def essential_op(gd, pr):
    """The beachcomber essential (can't be killed), unaggressive."""
    import api_characters as ac
    import recordio
    key = next(k for k, r in pr.records.items() if r.get('type') == 'NPC_' and recordio.field(r, 'EDID') == COMBER)
    rec = json.loads(json.dumps(pr.records[key]))
    ac.set_num(rec, 'ACBS', 'Flags', ac.num(rec, 'ACBS', 'Flags') | 0x2)
    return {'op': 'record', 'key': key, 'record': rec}
