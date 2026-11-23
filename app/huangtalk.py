"""The Huáng's own goodbyes, hellos and idle chatter (the user, 22 Nov 2026: they said the game's stock "bye" and "see ya").

The game picks a line of a topic from the quests that have one, the highest priority first, the first whose conditions
pass. Its stock GOODBYE, HELLO and IdleChatter lines (the generic quests', priority 5 to 8, by voice type) were all the
Huáng had there: their own lines were only greetings. So each Huáng gets lines of their own in those three topics, in the
quest their greetings are in (FOLabWaikikiPeople, priority 40, so theirs come first), one person each (GetIsID, as their
greetings: a line's voice is written for its speaker's voice type), by role (`SAID`): Mandarin in pinyin with the meaning
after it in brackets on screen, spoken in Mandarin by huangland.voice; Zhao Lei at the gate in short broken English
(`ZHAO`). Nothing is said of the Huáng that the story hasn't: these are what anyone says.

    ops(gd, pr)                 (ops, plan, report): one Undo; plan as huangland.voice takes it, after the ops are applied
    leaks(gd, pr)               {topic: [Huáng with no line of their own there]}: what still falls through to the game's

huangland (the Huáng's land, speech and paths) is the people session's: its helpers are used as they are."""
import json

import huangland as HL
import recordio

TOPICS = ('GOODBYE', 'HELLO', 'IdleChatter')
# role -> topic -> [(English shown, pinyin spoken)]; one is picked per person
SAID = {
    'guard': {'GOODBYE': [("Go.", "Zǒu."), ("Keep to the road.", "Yánzhe lù zǒu.")],
              'HELLO': [("Barbarian.", "Mánzi."), ("Stop there.", "Zhàn zhù.")],
              'IdleChatter': [("Quiet today.", "Jīntiān hěn ānjìng."), ("Watch the road.", "Kàn zhe lù.")]},
    'patrol': {'GOODBYE': [("Go.", "Zǒu.")],
               'HELLO': [("Barbarian.", "Mánzi.")],
               'IdleChatter': [("Keep walking.", "Jìxù zǒu.")]},
    'nongmin': {'GOODBYE': [("Goodbye.", "Zàijiàn."), ("Take care.", "Màn zǒu.")],
                'HELLO': [("Hello.", "Nǐ hǎo."), ("Mm.", "Èn.")],
                'IdleChatter': [("Have you eaten?", "Chī le ma?"), ("The maize is growing well.", "Yùmǐ zhǎng de hǎo."),
                                ("It will rain soon.", "Kuài xià yǔ le."), ("So tired today.", "Jīntiān hǎo lèi.")]},
    'elder': {'GOODBYE': [("Go now.", "Qù ba.")],
              'HELLO': [("Outsider.", "Wàirén.")],
              'IdleChatter': [("Mm. Good.", "Èn. Hǎo.")]},
}
ZHAO = {'GOODBYE': "You go now. Stay on road.", 'HELLO': "You. Outsider.", 'IdleChatter': "Quiet. Good."}


def _topic(gd, name):
    return gd.key(next(f for f, (_i, r) in gd.forms.items() if r.tag == 'DIAL' and (f >> 24) == 0 and gd.edid(f) == name))


def _people(pr):
    fac = HL.faction_key(pr)
    return {k: HL._edid(pr, k) for k, r in pr.records.items() if r.get('type') == 'NPC_' and HL.is_huang(pr, k, fac)}


def leaks(gd, pr, topics=TOPICS):
    says = HL._says(gd, pr)
    out = {}
    for name in topics:
        t = _topic(gd, name)
        out[name] = sorted(e for k, e in _people(pr).items() if not any(pr.records[lk].get('topic') == t for lk in says.get(k, [])))
    return out


def _said(role, name):
    """(English, pinyin) choices for a role in a topic: the talk's, or the barks' (fighters: the Shouwei; the rest: civil)."""
    if name in TOPICS:
        return SAID[role][name]
    group = 'fighter' if role in ('guard', 'patrol') else 'civil'
    b = BARKS[name]
    return b.get(group) or b['all']


def ops(gd, pr, topics=TOPICS, zhao=None):
    import activity
    import questrec as qr
    zhao = ZHAO if zhao is None else zhao
    says = HL._says(gd, pr)
    greet = HL.greeting_key(gd)
    people = _people(pr)
    # (the shape of a line: a Huáng greeting, its quest, its one condition GetIsID)
    template = next((k for p, ks in says.items() if p in people for k in ks if pr.records[k].get('topic') == greet), None)
    if template is None:
        raise ValueError('no Huáng greeting to copy the shape of: run huangland.lines first')
    tkeys = {name: _topic(gd, name) for name in topics}
    out, plan, rep = [], [], {name: 0 for name in topics}
    rep['zhao'] = 0
    for who, e in sorted(people.items()):
        role = HL.role_of(e)
        mine = says.get(who, [])
        for name, t in tkeys.items():
            if any(pr.records[lk].get('topic') == t for lk in mine):
                continue                                    # (they have one there already)
            rec = json.loads(json.dumps(pr.records[template]))
            plain = qr.info_plain(rec)
            for c in plain['conditions']:
                if c.get('fn') == 72:
                    c['p1'] = who
            plain['responses'] = plain['responses'][:1]
            if role == 'zhao':
                text, zh = zhao.get(name, zhao.get('*', 'Hm.')), None
                rep['zhao'] += 1
            else:
                takes = _said(role, name)
                en, zh = takes[int(who.lstrip('+').split(':')[-1], 16) % len(takes)]
                text = HL.shown(en, zh)
            plain['responses'][0]['text'] = text
            plain['topic'] = t
            new = qr.info_record(plain)
            new.update({k: v for k, v in rec.items() if k not in ('subs',)})
            new['topic'] = t
            new.pop('seq', None)
            k = activity._new_key(pr)
            out.append({'op': 'record', 'key': k, 'record': new})
            plan.append((k, plain['responses'][0]['number'], zh))
            rep[name] += 1
    rep['people'] = len(people)
    return out, plan, rep


# The combat and reaction barks (the Workshop, 23 Nov 2026: "do the combat and reaction barks too"): what the game says
# for a person in a fight, on the alert, or at what the player does. topic -> {'fighter' or 'civil' or 'all': choices}
BARKS = {
    'Attack': {'fighter': [("Kill!", "Shā!"), ("Die!", "Qù sǐ!")], 'civil': [("Get away!", "Gǔn kāi!")]},
    'PowerAttack': {'all': [("Take this!", "Kàn zhāo!")]},
    'Hit': {'all': [("Ah!", "Ā!"), ("Ow!", "Āiyā!")]},
    'Death': {'all': [("Ah...", "Ā...")]},
    'Flee': {'fighter': [("Fall back!", "Chè!")], 'civil': [("Help!", "Jiùmìng!"), ("Run!", "Kuài pǎo!")]},
    'NormalToCombat': {'fighter': [("Enemy!", "Dírén!")], 'civil': [("Help!", "Jiùmìng a!")]},
    'AlertToCombat': {'fighter': [("There! Enemy!", "Nàlǐ! Dírén!")], 'civil': [("Help!", "Jiùmìng a!")]},
    'LostToCombat': {'all': [("There!", "Zài nàlǐ!")]},
    'NormalToAlert': {'all': [("Who's there?", "Shéi?"), ("What was that?", "Shénme shēngyīn?")]},
    'AlertIdle': {'all': [("Where did it go?", "Zài nǎlǐ?")]},
    'LostIdle': {'all': [("Where are you?", "Nǐ zài nǎlǐ?")]},
    'CombatToLost': {'all': [("Where did they go?", "Rén ne?")]},
    'AlertToNormal': {'all': [("Nothing.", "Méi shénme.")]},
    'CombatToNormal': {'all': [("It's over.", "Jiéshù le.")]},
    'LostToNormal': {'all': [("Gone.", "Zǒu le.")]},
    'ObserveCombat': {'fighter': [("Fighting! Go!", "Dǎ qǐlái le! Shàng!")], 'civil': [("Fighting!", "Dǎ qǐlái le!")]},
    'Murder': {'all': [("Murderer!", "Shārén la!")]},
    'MurderNoCrime': {'all': [("Murderer!", "Shārén la!")]},
    'Assault': {'all': [("You struck me!", "Nǐ dǎ wǒ!")]},
    'AssaultNoCrime': {'all': [("You struck me!", "Nǐ dǎ wǒ!")]},
    'Steal': {'all': [("Thief!", "Xiǎotōu!")]},
    'StealNoCrime': {'all': [("Thief!", "Xiǎotōu!")]},
    'Pickpocket': {'all': [("Hands off!", "Bié dòng shǒu!")]},
    'PickpocketNoCrime': {'all': [("Hands off!", "Bié dòng shǒu!")]},
    'TrespassNoCrime': {'all': [("Get out!", "Chūqù!")]},
    'Yield': {'all': [("Stop! Enough!", "Tíng! Gòu le!")]},
    'AcceptYield': {'all': [("Fine. Go.", "Hǎo ba. Zǒu.")]},
    'AvoidThreat': {'all': [("Careful!", "Xiǎoxīn!")]},
    'FireExplosive': {'all': [("Look out!", "Xiǎoxīn zhàdàn!")]},
    'Corpse': {'all': [("Someone's dead.", "Sǐ rén le.")]},
    'PLAYERFIREWEAPON': {'all': [("Put that gun away!", "Bǎ qiāng shōu qǐlái!")]},
    'PLAYERSWINGMELEEWEAPON': {'all': [("Careful with that!", "Xiǎoxīn diǎn!")]},
    'PLAYERTHROWGRENADE': {'all': [("Are you mad?", "Nǐ fēng le ma?")]},
    'PLAYERSTANDONFURNITURE': {'all': [("Get down!", "Xiàlái!")]},
    'PLAYERDESTROYOBJECT': {'all': [("Stop that!", "Bié nòng le!")]},
    'PLAYERKNOCKOVEROBJECTS': {'all': [("Careful!", "Xiǎoxīn!")]},
}
ZHAO_BARKS = {'Attack': "Die!", 'PowerAttack': "Take!", 'Hit': "Ugh!", 'Death': "Ah...", 'Flee': "Back!", 'NormalToCombat': "Enemy!",
              'AlertToCombat': "Enemy!", 'LostToCombat': "There!", 'NormalToAlert': "Who there?", 'Murder': "Murderer!", 'MurderNoCrime': "Murderer!",
              'Steal': "Thief!", 'StealNoCrime': "Thief!", 'Pickpocket': "Hands off!", 'PickpocketNoCrime': "Hands off!", 'TrespassNoCrime': "Out!",
              'Yield': "Stop! Enough!", 'AcceptYield': "Good. Go.", 'PLAYERFIREWEAPON': "Gun away!", '*': "Hm."}
