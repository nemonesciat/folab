"""Waikiki's people's own goodbyes, hellos, idle chatter and barks (the user, 23 Nov 2026: "a lot of people with unique
voices all have the same goodbyes").

Everyone of the mod's own who isn't Huáng (huangtalk does theirs) fell back to the game's stock GOODBYE, HELLO, IdleChatter
and combat lines for their voice type: Albright said what every MaleAdult/FemaleAdult says. So each gets lines of their own
there, in FOLabWaikikiPeople (priority 40, over the generic quests' 5 to 8), flagged Random so the game picks one of several:

- a named person (`NAMED`, by editor ID): two lines a topic, from their background in docs/waikiki-people-dialogue.md
  (nothing new about the story: what each says anyway), on GetIsID as their greetings are;
- a crowd (`POOLS`: islanders, stallholders, fishers, pirates, captives): one record stands for many placed people, so a
  pool's lines are on GetIsID of each of its records, OR'd, five a topic for the big ones, so two pirates seldom say the
  same thing.

Voices. A line's sound is looked for in the folder of the speaker's voice type as the game works it out: a record that
takes its traits from a template (ACBS template flag 1) has the template's voice type, and a crowd's template is a
levelled list, so one pirate record speaks as any of up to a dozen voice types. `folders` lists them (walking the lists);
every line is spoken into each, in a voice of that sex: the person's own choice (voices.json) where it fits, else one of
their own for that folder (api_voices.own_default of the record and folder), so pirates of different voice types sound
different. The folder the editor knows (api_voices.line_info's) gets the person's choice, so the Voices page shows it done.

    units(gd, pr)                   [{'name', 'keys', 'role', 'lines': {topic: [text]}}]
    ops(gd, pr, topics)             (ops, plan, report): one Undo; plan for `voice` once applied
    voice(gd, pr, plan)             {'voiced', 'copied', 'problems'}
    leaks(gd, pr, topics)           {topic: [editor IDs of the mod's people with no line of their own there]}
    unvoiced(gd, pr, plan)          [(line, folder)] missing .ogg or .lip"""
import json
import os
import shutil

import recordio

TOPICS = ('GOODBYE', 'HELLO', 'IdleChatter')
QUEST = 'FOLabWaikikiPeople'
NOT_PEOPLE = ('Player',)

# editor ID -> (role, {topic: [lines]}); role is the barks' group
NAMED = {
    'FOLabWaikikiDoctor': ('civil', {
        'GOODBYE': ["Keep it clean. Wounds and hands both.", "Come back when you're bleeding. Not before."],
        'HELLO': ["Hurt? No? Then mind the door.", "Wash your hands if you're coming in."],
        'IdleChatter': ["Fight night again. I'll need more thread.", "Half my pills are older than I am."]}),
    'FOLabWaikikiGrocer': ('civil', {
        'GOODBYE': ["Come back hungry!", "Tell your friends. Ray's counter, Kalakaua."],
        'HELLO': ["Fresh today! Mostly.", "Hey! You eating or looking?"],
        'IdleChatter': ["Feast's coming. I'm counting, I'm counting.", "Boats are late again. Prices won't be."]}),
    'FOLabWaikikiGunsmith': ('civil', {
        'GOODBYE': ["Don't break it.", "Bring it back in one piece."],
        'HELLO': ["Clubs or guns. Decide.", "Hm. You again."],
        'IdleChatter': ["Koa doesn't rust. Remember that.", "Moreno's selling armour again. Fine armour. Hmph."]}),
    'FOLabWaikikiTrader': ('civil', {
        'GOODBYE': ["Come back when you're richer.", "Safe roads. Or good armour."],
        'HELLO': ["Looking for something sturdy to wear?", "Hello, hello. Take a look."],
        'IdleChatter': ["Silk from the Huang, koa from the court. Good week.", "Tom's sulking again. He'll get over it."]}),
    'FOLabKahunaGuard01': ('fighter', {
        'GOODBYE': ["Move along.", "Mind the court's rules."],
        'HELLO': ["Halt. State your business.", "The floors are closed. Keep to the lobby."],
        'IdleChatter': ["Nobody gets past. Nobody.", "He's laughing upstairs. A good day, then."]}),
    'FOLabKahunaGuard02': ('fighter', {
        'GOODBYE': ["See you at the feast. Maybe.", "Go on. I can smell the pig from here."],
        'HELLO': ["Hungry? Me too.", "You're not here for the buffet, are you?"],
        'IdleChatter': ["Whole pig tonight, I hope.", "Ray's fruit is the best part. Don't tell the Kahuna."]}),
    'FOLabKahunaGuard03': ('fighter', {
        'GOODBYE': ["Walk with respect.", "Mind the kapu."],
        'HELLO': ["Aloha. Step carefully here.", "Some places here are sacred. Ask first."],
        'IdleChatter': ["My grandmother would be glad to see this.", "The old ways came back. Slowly."]}),
    'FOLabKahunaGuard04': ('fighter', {
        'GOODBYE': ["Keep smiling, friend.", "Don't make me walk you out."],
        'HELLO': ["Well, well. Smile.", "Look who's here. Behave."],
        'IdleChatter': ["Everybody's friendly. For now.", "The Kahuna's smiling. Lucky us."]}),
    'FOLabKahunaGuard05': ('fighter', {
        'GOODBYE': ["Come to fight night!", "Later. Bet on the big one."],
        'HELLO': ["You fight? You look like you could.", "Hey! You hear about the last fight?"],
        'IdleChatter': ["Three fights, three wins. Then this spear.", "Fight night can't come fast enough."]}),
    'FOLabKahunaGuard06': ('fighter', {
        'GOODBYE': ["You are dismissed.", "Mind the court's titles."],
        'HELLO': ["Stand where I can see you.", "State your business with the court."],
        'IdleChatter': ["Order is kept. As it should be.", "The court is sitting. Quiet."]}),
    'FOLabCourtFighter05': ('fighter', {
        'GOODBYE': ["Stay out of trouble.", "Keep to the hotels."],
        'HELLO': ["Walking the hotels. You?", "Easy now."],
        'IdleChatter': ["No pirates today. Good.", "Quiet streets. That's the job."]}),
    'FOLabCourtFighter06': ('fighter', {
        'GOODBYE': ["Keep to the street.", "See you around."],
        'HELLO': ["Hey. Need directions?", "Keep it friendly."],
        'IdleChatter': ["Three streets over, that's home.", "Never been past the toll post. Never needed to."]}),
    'FOLabCourtFighter07': ('fighter', {
        'GOODBYE': ["Long shift. Go on.", "Watch yourself out there."],
        'HELLO': ["Still on shift. What?", "Yeah?"],
        'IdleChatter': ["Short pay. Still beats the coast.", "Out on the coast they sell people. Here they just overcharge you."]}),
    'FOLabCourtFighter08': ('fighter', {
        'GOODBYE': ["Eyes front.", "Off you go."],
        'HELLO': ["Hands where I can see them.", "Stop there. Okay. Go on."],
        'IdleChatter': ["Win a fight night and they'll find you.", "Lose one and the doctor finds you."]}),
    'FOLabPatrolCourt01': ('fighter', {
        'GOODBYE': ["Out of my way, then.", "Keep moving."],
        'HELLO': ["On my rounds. Walk with me or move.", "You. Asking questions?"],
        'IdleChatter': ["Questions about the Missouri. Don't.", "Rounds, rounds, rounds."]}),
    'FOLabPatrolCourt02': ('fighter', {
        'GOODBYE': ["Don't go past the edge.", "Out there you're on your own."],
        'HELLO': ["Edge of town. Turning back?", "Heading out? Careful."],
        'IdleChatter': ["Past here you're on your own.", "Don't stop at the camp down the road."]}),
    'FOLabCourtFighter01': ('fighter', {
        'GOODBYE': ["Road's yours.", "Move on."],
        'HELLO': ["Toll's owed on this road.", "Twelve years on this road. What do you want?"],
        'IdleChatter': ["Seen everything come up this road.", "The feasts don't pay for themselves."]}),
    'FOLabCourtFighter02': ('fighter', {
        'GOODBYE': ["Shoots, brah. Go.", "Laters."],
        'HELLO': ["Howzit. Pay and pass.", "Eh, brah."],
        'IdleChatter': ["Good view, at least.", "Waimanalo side was home. Before."]}),
    'FOLabCourtFighter03': ('fighter', {
        'GOODBYE': ["Keep it quiet out there.", "Go on."],
        'HELLO': ["Quiet road today.", "Seen anything out there?"],
        'IdleChatter': ["Court said let them pass. So we did.", "Quiet's good. Quiet's very good."]}),
    'FOLabCourtFighter04': ('fighter', {
        'GOODBYE': ["Waikiki's that way.", "Mind the road."],
        'HELLO': ["Toll first.", "Another one for Waikiki?"],
        'IdleChatter': ["We fished Maunalua Bay, once.", "Funny how things go."]}),
    'FOLabBeachcomber': ('civil', {
        'GOODBYE': ["Watch the tide.", "Mind the jellyfish."],
        'HELLO': ["Morning. Tide's out.", "Look what the sea brought back."],
        'IdleChatter': ["Planks, bottles, a boot...", "The sea's generous. Mostly with junk."]}),
    'FOLabKuliWoman': ('civil', {
        'GOODBYE': ["Come back. Eat something.", "Go careful."],
        'HELLO': ["Sit by the fire.", "You came back."],
        'IdleChatter': ["Somebody gotta feed them.", "Long time I been waiting."]}),
    'FOLabKuliFather': ('civil', {
        'GOODBYE': ["Just go.", "Don't come back."],
        'HELLO': ["Don't look at me like that.", "What do you want?"],
        'IdleChatter': ["Everybody sells something.", "He'll eat on that boat."]}),
    'FOLabKuliSon': ('civil', {
        'GOODBYE': ["Bye.", "See you. Maybe."],
        'HELLO': ["Hi.", "Are you a pirate too?"],
        'IdleChatter': ["Dad says it's only for a while.", "I'm gonna see Maui."]}),
    'FOLabKuliStranger': ('civil', {
        'GOODBYE': ["Please. Tell someone.", "Go. Before they see you."],
        'HELLO': ["Help me.", "Please."],
        'IdleChatter': ["Where are they taking me?", "I was only walking the road."]}),
    'FOLabKuliPirate': ('pirate', {
        'GOODBYE': ["Walk on.", "Business is done."],
        'HELLO': ["Business. Walk on.", "What."],
        'IdleChatter': ["Calloway sets the prices. I keep them.", "Tide's turning. Boat leaves soon."]}),
    'FOLabKuliCatcher': ('pirate', {
        'GOODBYE': ["Keep walking, friend.", "Go on, then."],
        'HELLO': ["This one's ours.", "Help you?"],
        'IdleChatter': ["Pirates pay best.", "Whoever pays for what we catch."]}),
    'FOLabKuliCatcher2': ('pirate', {
        'GOODBYE': ["Not you. Not today.", "Go on. Nothing to see."],
        'HELLO': ["Tribute day's coming.", "You lost?"],
        'IdleChatter': ["Pay, and the boats leave us be.", "Camp pays in people."]}),
    'FOLabPirateCaptain': ('pirate', {
        'GOODBYE': ["Pleasure doing business.", "Swim safe."],
        'HELLO': ["State your business or swim.", "Crew ground. Talk."],
        'IdleChatter': ["Waikiki pays us well.", "I buy, I sell. I don't ask."]}),
    'FOLabPirateCaptainVega': ('pirate', {
        'GOODBYE': ["Careful where you stand.", "Run along."],
        'HELLO': ["You've got the look of cargo.", "Well. Hello, cargo."],
        'IdleChatter': ["Calloway talks. I do everything else.", "Want to fight? Try."]}),
    'FOLabPirateCaptainAiona': ('pirate', {
        'GOODBYE': ["Off my shore.", "Go. Today you're not worth it."],
        'HELLO': ["My boats, my shore.", "You're on my beach."],
        'IdleChatter': ["My grandfather fished this bay.", "Everything here has a price."]}),
    'FOLabFlotillaCaptain': ('pirate', {
        'GOODBYE': ["Off my deck.", "Go, while I'm kind."],
        'HELLO': ["You're on my water.", "Speak fast."],
        'IdleChatter': ["The flotilla doesn't wait.", "Keep the lines tight."]}),
}

# pool -> (role, editor IDs or prefixes of its records, {topic: [lines]})
POOLS = {
    'islander': ('civil', ('FOLabSurferVSpawn', 'FOLabBeachSurfer', 'FOLabWaikikiLocal', 'FOLabMarketGoer'), {
        'GOODBYE': ["Shoots.", "Laters.", "A hui hou.", "Take it easy.", "Mind the reef."],
        'HELLO': ["Aloha.", "Howzit.", "Eh. New face.", "Keep your weapon down, yeah?", "Nice day for it."],
        'IdleChatter': ["Waves are good later.", "Feast coming, they say.", "Fight night was something.",
                        "Don't go past the toll post.", "Good fish this morning."]}),
    'seller': ('civil', ('FOLabMarketSeller',), {
        'GOODBYE': ["Come back soon.", "Mahalo.", "Tell your friends."],
        'HELLO': ["Fresh today!", "Take a look.", "Fair prices. Mostly."],
        'IdleChatter': ["Slow day.", "Boats are late.", "Who's buying?"]}),
    'fisher': ('civil', ('FOLabPierFisher',), {
        'GOODBYE': ["Mind the line.", "Tight lines.", "Shoots."],
        'HELLO': ["Quiet. You'll scare the fish.", "Fish aren't biting.", "Eh."],
        'IdleChatter': ["Nothing yet.", "Should've come at dawn.", "Big one got away."]}),
    'pirate': ('pirate', ('FOLabPirateLvl', 'FOLabPirateV', 'FOLabPirateDockhand', 'FOLabPirateRoadside', 'FOLabPirateRaider',
                          'FOLabFlotillaQuartermaster', 'FOLabFlotillaPenGuard'), {
        'GOODBYE': ["Get lost.", "Walk away.", "Go on. Swim.", "Don't come back.", "Lucky day for you."],
        'HELLO': ["What do you want?", "Crew ground.", "You lost?", "Look at this one.", "Keep your hands still."],
        'IdleChatter': ["Captain wants the boats ready.", "Cargo's late.", "Who's on watch?", "I could use a drink.",
                        "Tide's turning."]}),
    'captive': ('civil', ('FOLabFlotillaCaptive',), {
        'GOODBYE': ["Don't leave us.", "Please hurry.", "Come back. Please.", "Don't let them see you."],
        'HELLO': ["Help us.", "Please. Get us out.", "Who are you?", "Quiet. They'll hear."],
        'IdleChatter': ["How long have we been here?", "They feed us when they remember.", "I can hear the guard.",
                        "Where are they taking us?"]}),
    # (the Kahuna's court living in the Moana: ourpeople, the user's word 23 Nov 2026)
    'courtguard': ('fighter', ('FOLabCourtGuard',), {
        'GOODBYE': ["Keep the peace.", "Go on.", "Mind your manners here.", "The court is watching.", "Off with you."],
        'HELLO': ["You're in the Kahuna's house.", "Weapon down.", "State your business.", "Guests only up here.",
                  "Easy, stranger."],
        'IdleChatter': ["Quiet night.", "Change of watch soon.", "Keep the stairs clear.", "Nobody up without leave.",
                        "Kahuna's in good spirits."]}),
    'courtretainer': ('civil', ('FOLabCourtRetainer',), {
        'GOODBYE': ["The court thanks you.", "Go well.", "We'll speak again.", "Mind the protocol.", "A hui hou."],
        'HELLO': ["You have business with the court?", "Aloha. Be brief.", "The Kahuna is busy.", "Speak plainly.",
                  "Visitors are rare up here."],
        'IdleChatter': ["The Kahuna will want to hear of it.", "Too many petitions this week.", "The guest rooms are full.",
                        "Word from the toll post?", "Keep the old ways, and the house keeps you."]}),
    'courtservant': ('civil', ('FOLabCourtServant',), {
        'GOODBYE': ["Excuse me.", "Work to do.", "Mahalo.", "I'd best get on.", "Mind the floor, it's wet."],
        'HELLO': ["Can I help you?", "Pardon me.", "Aloha.", "Looking for someone?", "Guests are upstairs."],
        'IdleChatter': ["The linen won't wash itself.", "Feast tonight. More work.", "Kitchen's short again.",
                        "Rooms on six need airing.", "Don't let the steward see you sit."]}),
    'courtguest': ('civil', ('FOLabCourtGuest',), {
        'GOODBYE': ["Enjoy the house.", "Until later.", "A hui hou.", "Do look at the view.", "Off you go then."],
        'HELLO': ["Oh. Aloha.", "Another guest?", "Lovely, isn't it?", "You're not from the court.", "Howzit."],
        'IdleChatter': ["The Kahuna keeps a fine house.", "Best view on the island.", "Is there a feast tonight?",
                        "The sea's calm today.", "I hear the pirates are restless."]}),
    'child': ('civil', ('FOLabChild',), {          # (the refugee children made the mod's own: ourpeople, activity.kids)
        'GOODBYE': ["Bye!", "Shoots!", "See you, stranger!", "A hui hou!", "Gotta go!"],
        'HELLO': ["Who are you?", "Is that a Pip-Boy?", "You talk funny.", "Aloha!", "Got any candy?"],
        'IdleChatter': ["I found a shell this big!", "Race you to the pier!", "Mom says don't go near the boats.",
                        "I'm not scared of pirates.", "Tag, you're it!"]}),
}

# The barks: topic -> {'fighter' | 'pirate' | 'civil' | 'all': [lines]}, with the face the game shows (emotion, strength)
BARKS = {
    'Attack': ({'fighter': ["For the court!", "Die!"], 'pirate': ["Gut them!", "Over the side with you!"],
                'civil': ["Get away!", "Leave me alone!"]}, (1, 60)),
    'PowerAttack': ({'all': ["Take this!", "Hah!"]}, (1, 80)),
    'Hit': ({'all': ["Ah!", "Ugh!"]}, (7, 70)),
    'Death': ({'all': ["Ah...", "No..."]}, (7, 90)),
    'Flee': ({'fighter': ["Fall back!"], 'pirate': ["Back to the boats!"], 'civil': ["Help!", "Run!"]}, (3, 70)),
    'NormalToCombat': ({'fighter': ["Trouble!", "Weapons!"], 'pirate': ["Fresh meat!", "Get them!"], 'civil': ["Help!", "No!"]}, (1, 50)),
    'AlertToCombat': ({'fighter': ["There!"], 'pirate': ["Found you!"], 'civil': ["There! Help!"]}, (1, 50)),
    'LostToCombat': ({'all': ["There you are!"]}, (1, 50)),
    'NormalToAlert': ({'all': ["Who's there?", "What was that?"]}, (6, 40)),
    'AlertIdle': ({'all': ["Where'd they go?", "Show yourself."]}, (0, 50)),
    'LostIdle': ({'all': ["Come out.", "I know you're here."]}, (1, 30)),
    'CombatToLost': ({'all': ["Where'd they go?"]}, (1, 30)),
    'AlertToNormal': ({'all': ["Nothing.", "Must be the wind."]}, (0, 50)),
    'CombatToNormal': ({'all': ["It's over.", "That's done."]}, (0, 50)),
    'LostToNormal': ({'all': ["Gone.", "Long gone."]}, (0, 50)),
    'ObserveCombat': ({'fighter': ["Fighting! Move!"], 'pirate': ["A fight!"], 'civil': ["They're fighting!"]}, (6, 50)),
    'Murder': ({'all': ["Murderer!"]}, (3, 80)),
    'MurderNoCrime': ({'all': ["Murderer!"]}, (3, 80)),
    'Assault': ({'all': ["You hit me!"]}, (1, 70)),
    'AssaultNoCrime': ({'all': ["You hit me!"]}, (1, 70)),
    'Steal': ({'all': ["Thief!"]}, (1, 60)),
    'StealNoCrime': ({'all': ["Thief!"]}, (1, 60)),
    'Pickpocket': ({'all': ["Hands off!"]}, (1, 60)),
    'PickpocketNoCrime': ({'all': ["Hands off!"]}, (1, 60)),
    'TrespassNoCrime': ({'all': ["Get out of here!"]}, (1, 50)),
    'Yield': ({'all': ["Enough! Enough!"]}, (3, 70)),
    'AcceptYield': ({'all': ["Fine. Go."]}, (0, 50)),
    'AvoidThreat': ({'all': ["Careful!"]}, (3, 50)),
    'FireExplosive': ({'all': ["Look out!"]}, (3, 70)),
    'Corpse': ({'all': ["Someone's dead."]}, (4, 50)),
    'PLAYERFIREWEAPON': ({'all': ["Put that gun away!"]}, (1, 50)),
    'PLAYERSWINGMELEEWEAPON': ({'all': ["Careful with that!"]}, (1, 40)),
    'PLAYERTHROWGRENADE': ({'all': ["Are you mad?"]}, (3, 60)),
    'PLAYERSTANDONFURNITURE': ({'all': ["Get down from there!"]}, (2, 40)),
    'PLAYERDESTROYOBJECT': ({'all': ["Stop that!"]}, (1, 40)),
    'PLAYERKNOCKOVEROBJECTS': ({'all': ["Watch it!"]}, (2, 30)),
}


def _edid(pr, k):
    return recordio.field(pr.records.get(k) or {}, 'EDID') or ''


def _topic(gd, name):
    return gd.key(next(f for f, (_i, r) in gd.forms.items() if r.tag == 'DIAL' and (f >> 24) == 0 and gd.edid(f) == name))


def people(pr):
    """{key: editor ID} of the mod's own people this covers: every NPC_ of the mod not the Huáng's (huangtalk's) or the player."""
    import huangland as HL
    fac = HL.faction_key(pr)
    return {k: _edid(pr, k) for k, r in pr.records.items()
            if r.get('type') == 'NPC_' and k.startswith('+') and not HL.is_huang(pr, k, fac) and _edid(pr, k) not in NOT_PEOPLE}


def units(pr):
    """Who says what: a named person each, a pool of records each."""
    folk = people(pr)
    by_edid = {e: k for k, e in folk.items()}
    out = []
    for e, (role, lines) in NAMED.items():
        if e in by_edid:
            out.append({'name': e, 'keys': [by_edid[e]], 'role': role, 'lines': lines})
    for name, (role, prefixes, lines) in POOLS.items():
        keys = sorted(k for k, e in folk.items() if e not in NAMED and e.startswith(prefixes))
        if keys:
            out.append({'name': name, 'keys': keys, 'role': role, 'lines': lines})
    return out


def _bark_lines(role, topic):
    b = BARKS[topic][0]
    return b.get(role) or b.get('all') or b.get('civil')


def _lines(u, topic):
    """(lines, (emotion, strength)) a unit says in a topic."""
    if topic in u['lines']:
        return u['lines'][topic], (0, 50)
    return _bark_lines(u['role'], topic), BARKS[topic][1]


def leaks(gd, pr, topics=TOPICS):
    import huangland as HL
    says = HL._says(gd, pr)
    folk = people(pr)
    out = {}
    for name in topics:
        t = _topic(gd, name)
        out[name] = sorted(e for k, e in folk.items() if not any(pr.records[lk].get('topic') == t for lk in says.get(k, [])))
    return out


def _template(gd, pr):
    """A greeting of FOLabWaikikiPeople with one GetIsID: the shape every new line is copied from."""
    import questrec as qr
    greet = _topic(gd, 'GREETING')
    for k, r in sorted(pr.records.items()):
        if r.get('type') != 'INFO' or r.get('topic') != greet:
            continue
        plain = qr.info_plain(json.loads(json.dumps(r)))
        if _edid(pr, plain.get('quest')) == QUEST and [c.get('fn') for c in plain['conditions']] == [72]:
            return k
    raise ValueError('no greeting of %s with one GetIsID to copy the shape of' % QUEST)


def ops(gd, pr, topics=TOPICS):
    import activity
    import huangland as HL
    import questrec as qr
    says = HL._says(gd, pr)
    template = _template(gd, pr)
    tkeys = {name: _topic(gd, name) for name in topics}
    out, plan, rep = [], [], {name: 0 for name in topics}
    us = units(pr)
    fresh = set()                                           # (units given lines in this go)
    for u in us:
        for name, t in tkeys.items():
            if any(pr.records[lk].get('topic') == t for k in u['keys'] for lk in says.get(k, [])):
                continue                                    # (they have one there already)
            fresh.add(u['name'])
            lines, (emotion, strength) = _lines(u, name)
            for text in lines:
                rec = json.loads(json.dumps(pr.records[template]))
                plain = qr.info_plain(rec)
                c0 = plain['conditions'][0]
                plain['conditions'] = []
                for n, k in enumerate(u['keys']):
                    c = dict(c0, p1=k, **{'or': n < len(u['keys']) - 1})
                    plain['conditions'].append(c)
                plain['responses'] = plain['responses'][:1]
                r = plain['responses'][0]
                r.update({'text': text, 'emotion': emotion, 'strength': strength})
                plain['flags'] = dict(plain['flags'], random=len(lines) > 1, goodbye=False)
                plain['topic'] = t
                new = qr.info_record(plain)
                new.update({k: v for k, v in rec.items() if k not in ('subs',)})
                new['topic'] = t
                new.pop('seq', None)
                k = activity._new_key(pr)
                out.append({'op': 'record', 'key': k, 'record': new})
                plan.append({'line': k, 'number': r['number'], 'unit': u['name'], 'keys': u['keys']})
                rep[name] += 1
    # (a crowd's lines from before, its greetings, were spoken into one folder only: into all of them too; only for crowds
    # given lines now, so a later go for new people doesn't speak every crowd again)
    for u in us:
        if len(u['keys']) > 1 and u['name'] in fresh:
            for lk in sorted({lk for k in u['keys'] for lk in says.get(k, [])}):
                for r in qr.info_plain(json.loads(json.dumps(pr.records[lk])))['responses']:
                    plan.append({'line': lk, 'number': r['number'], 'unit': u['name'], 'keys': u['keys']})
                    rep['crowd lines spread'] = rep.get('crowd lines spread', 0) + 1
    rep['units'] = len(us)
    rep['people'] = sum(len(u['keys']) for u in us)
    rep['not covered'] = sorted(set(people(pr).values()) - {_edid(pr, k) for u in us for k in u['keys']})
    return out, plan, rep


# ---------- voices ----------

def _leaves(gd, pr, key, depth=0):
    """[(voice type key, female)] the game can give an actor of this record."""
    import api_voices as av
    rec = av._record(gd, pr, key)
    if not rec or depth > 6:
        return []
    if rec.get('type') == 'LVLN':
        out = []
        for s in rec['subs']:
            if s['tag'] == 'LVLO':
                ref = next((f['value'] for f in s.get('fields', ()) if isinstance(f.get('value'), str)), None)
                if ref:
                    out += _leaves(gd, pr, ref, depth + 1)
        return out
    if rec.get('type') != 'NPC_':
        return []
    female = bool(av._acbs(rec, 'Flags') & av.FEMALE)
    tplt = recordio.field(rec, 'TPLT')
    if tplt and av._acbs(rec, 'Template flags') & av.USE_TRAITS:
        got = _leaves(gd, pr, tplt, depth + 1)
        if got:
            return got
    vt = recordio.field(rec, 'VTCK')
    return [(vt, female)] if vt else []


def folders(gd, pr, keys):
    """{voice type folder name (lower case editor ID): female} every record of keys may speak as."""
    import api_voices as av
    out = {}
    for k in keys:
        for vt, female in _leaves(gd, pr, k):
            out.setdefault(av.edid(gd, pr, vt).lower(), female)
    return out


def voice(gd, pr, plan, progress=None):
    """Speaks each planned response into every folder its speakers may use (see the docstring)."""
    import api_voices as av
    import library
    import voicegen
    voices = av.load(pr)
    engine = av.engine_of(voices)
    root = library.assets_dir(pr)
    made = {}                          # (text, voice, speed, pitch, lively, mood) -> a base already written
    done = copied = 0
    problems = []
    fold = {}

    def speak(base, text, c, mood):
        nonlocal done, copied
        key = (text, c['voice'], float(c['speed']), float(c['pitch']), float(c['lively']), tuple(mood))
        if key in made:
            os.makedirs(os.path.dirname(base), exist_ok=True)
            for ext in ('.ogg', '.lip'):
                shutil.copyfile(made[key] + ext, base + ext)
            copied += 1
            return
        if engine == 'chatterbox':
            voicegen.write_line(base, text, c['voice'], float(c['speed']), float(c['pitch']), float(c['lively']),
                                engine='chatterbox', feeling=av.feeling_of(mood[0], mood[1]))
        else:
            times, up, tune = av.mood_of(mood[0], mood[1])
            voicegen.write_line(base, text, c['voice'], float(c['speed']) * times, float(c['pitch']) + up, float(c['lively']) * tune)
        made[key] = base
        done += 1

    for n, p in enumerate(plan):
        lk, num = p['line'], p['number']
        info = av.line_info(gd, pr, lk, voices)
        if info['problem']:
            problems.append((lk, info['problem']))
            continue
        r = next(x for x in info['responses'] if x['number'] == num)
        mood = [r['emotion'], r['strength']]
        c = info['choice']
        base = os.path.join(root, r['path'])
        speak(base, r['text'], c, mood)
        voices['lines'].setdefault(lk, {})[str(num)] = {'text': r['text'], 'voice': c['voice'], 'speed': c['speed'], 'pitch': c['pitch'],
                                                        'lively': c['lively'], 'path': r['path'], 'mood': mood, 'engine': engine}
        ks = tuple(p['keys'])
        if ks not in fold:
            fold[ks] = folders(gd, pr, ks)
        parts = r['path'].split(os.sep)
        female_c = voicegen.is_female(c['voice'])
        for vt, female in sorted(fold[ks].items()):
            if vt == parts[3]:
                continue
            other = os.path.join(root, *(parts[:3] + [vt] + parts[4:]))
            if female == female_c:
                use = c if len(ks) == 1 else dict(c, **av.own_default('%s %s' % (p['unit'], vt), female))
            else:
                use = dict(c, **av.own_default('%s %s' % (p['unit'], vt), female))
            speak(other, r['text'], use, mood)
        if progress and n % 20 == 0:
            progress('%d of %d lines: %d spoken, %d copied' % (n, len(plan), done, copied))
            av.save(pr, voices)
    av.save(pr, voices)
    library.publish(pr)
    return {'voiced': done, 'copied': copied, 'problems': problems}


def unvoiced(gd, pr, plan):
    """[(line, path)] of each planned response's folders missing its .ogg or .lip."""
    import api_voices as av
    import library
    root = library.assets_dir(pr)
    miss, fold = [], {}
    for p in plan:
        info = av.line_info(gd, pr, p['line'])
        r = next((x for x in info.get('responses', ()) if x['number'] == p['number']), None)
        if r is None:
            miss.append((p['line'], 'no response'))
            continue
        ks = tuple(p['keys'])
        if ks not in fold:
            fold[ks] = folders(gd, pr, ks)
        parts = r['path'].split(os.sep)
        for vt in set(fold[ks]) | {parts[3]}:
            path = os.path.join(root, *(parts[:3] + [vt] + parts[4:]))
            if not all(os.path.isfile(path + ext) for ext in ('.ogg', '.lip')):
                miss.append((p['line'], path))
    return miss
