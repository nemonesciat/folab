"""The Pink Pearl's pirate activities (the user picked "All three", 26 Nov 2026; the drafts are the story session's). The Pink
Pearl is FOLabHotelPinkPearl just south of Koko Marina's boatyard; its lobby, two guest floors and top floor are places of
the mod's own (FOLabPinkPearlFloor1-4), joined by lifts. Its rooms have no doors, so what is locked is a thing in them: a
strongbox, a shackle, a boat's locker.

1. **The Boatyard's Cells** (`QUESTS['cells']`). A boatyard hand at Koko Marina lost his crew's toll crate of charged cells;
   he's sure a Kuliouou scavenger stashed it in the Pink Pearl. The crate is in a strongbox on Guest Floor 1 (Lockpick
   `BOX_LOCK`), opened too by forcing the jammed lift panel on Guest Floor 2 (Repair `PANEL_REPAIR`) or by the key the
   scavenger carries (on the top floor). With the crate:
   - give it back: `PAY` cells and pirate fame; Speech `HAGGLE` doubles it (Dread Name: always, he's afraid); Raised on the
     Boats: `BOAT_BONUS` more, for one of the boat-born;
   - lie that it's gone (Speech `LIE`; never believed from a Captain's Kin): you keep it (`CRATE` cells in it);
   - keep it to his face: you keep it, his crew of two turn on you, pirate infamy;
   - give it to the scavenger: Kuliouou good (`KULI_GOOD`), no pirate pay;
   - sell the scavenger out (once you've met him): `SELL_OUT` cells and pirate fame; the hand's crew take him away;
   - fight the scavenger (he goes for you; his key opens the box).
2. **The Boy in the Pearl** (`QUESTS['boy']`), after "The First Place on the Way": the son sold at Kuliouou is held on Guest
   Floor 2, shackled, until the boat sails (`SAIL_DAYS`), with one guard who sleeps at night:
   - buy him back: `PRICE` cells, Barter `BARTER` halves it; a Captain's Kin pays double (the boats hate the court's kin);
   - Speech `TALK` (FOLabTraitTalk: Soft Touch eases it); Raised on the Boats: Speech `BOATS_TALK`, "we grew up on the same
     decks";
   - Intimidate `THREAT` (FOLabTraitThreat: Dread Name always wins, Soft Touch never does);
   - sneak (Sneak `SNEAK`) past him while he sleeps and pick the shackle (Lockpick `SHACKLE_LOCK`): come near him awake to
     sleep, or not sneaking well enough, and he wakes and has words with you;
   - fight: his shackle key opens it;
   - leave him: the boat sails.
   Freed, the boy goes home by himself; his father gives a meal and tells you where the boats hide a cache near the camp.
   Kuliouou good; pirate infamy unless you paid.
3. **When the Boats Run In** (`QUESTS['storm']`): while the storm quest holds FOLabStormShelter (a big storm's building step
   to its end), a crew shelters in the Pink Pearl's lobby round a fire and a card table (under the persistent parent
   `CREW_PARENT`). Each storm, once:
   - trade storm salvage (Scrap Metal) for cells, `SALVAGE` each, `SALVAGE_MOST` at most; a Captain's Kin gets no trade;
   - cards: `STAKE` cells a hand, `HANDS` hands a storm, won by chance from Luck and Barter (Raised on the Boats: better);
   - Sneak `OVERHEAR` near the boss overhears their boat at the marina is unguarded: loot its locker (Lockpick `LOCKER`) or
     tell them (pirate fame);
   - fight them for a small court bounty (`BOUNTY` kala). The dead come back with the next storm's crew.

No face twice; every line voiced (VOICE). `routes()` plays every way through on the quests' own scripts and lines
(`play`): the conditions each line carries are the ones the route is judged by.

    plan(gd, pr)       {'rows', 'skipped', 'spots'}
    apply(pr, gd, P)   one Undo (VOICE: the three quests' lines)
"""
import json
import math
import re

import recordio

LABEL = "The Pink Pearl: the boatyard's cells, the boy in the Pearl, when the boats run in"
QUESTS = {'cells': 'FOLabPearlCells', 'boy': 'FOLabPearlBoy', 'storm': 'FOLabPearlStorm'}
NAMES = {'cells': "The Boatyard's Cells", 'boy': 'The Boy in the Pearl', 'storm': 'When the Boats Run In'}
VOICE = list(QUESTS.values())
FLOORS = {'lobby': 'FOLabPinkPearlFloor1', 'g1': 'FOLabPinkPearlFloor2', 'g2': 'FOLabPinkPearlFloor3', 'top': 'FOLabPinkPearlFloor4'}
MARINA, KULIOUOU = 'Koko Marina', "Kuliouou Squatters' Camp"
FIRST_PLACE, FIRST_DONE = 'FOLabFirstPlace', 100
FATHER, SON = 'FOLabKuliFatherREF', 'FOLabKuliSon'
SHELTER = 'FOLabStormShelter'
KULI = 'FOLabKuliGood'                 # (a count for later steps: what you've done for Kuliouou; no standing of its own yet)
TRAITS = {'dread': 'FOLabTraitDreadName', 'soft': 'FOLabTraitSoftTouch', 'boats': 'FOLabTraitRaisedOnTheBoats',
          'kin': 'FOLabTraitCaptainsKin'}
TALK_G, THREAT_G = 'FOLabTraitTalk', 'FOLabTraitThreat'
REP_PIRATES, NAME_Q = 'FOLabRepPirates', 'FOLabNameOnWater'
CELL, KALA, SCRAP, STIM = 'AmmoSmallEnergyCell', 'Caps001', 'SpareParts', 'Stimpak'    # (SpareParts is the game's Scrap Metal)
MEAL = 'FOLabGrilledReefFish'

# 1, the boatyard's cells
BOX_LOCK, PANEL_REPAIR = 25, 25
PAY, HAGGLE, LIE, CRATE, SELL_OUT, BOAT_BONUS, KULI_GOOD = 25, 35, 50, 40, 15, 10, 1
# 2, the boy
PRICE, BARTER, TALK, BOATS_TALK, THREAT, SNEAK, SHACKLE_LOCK, SAIL_DAYS = 60, 40, 45, 25, 55, 35, 50, 5
WAKE_NEAR, WATCHED = 900, 3000          # (asleep, he wakes if you come this near unsneaking: his bed must be nearer the boy than
                                        #  this; awake, he sees the shackle from anywhere on the floor. plan checks both)
SLEEP_AT, SLEEP_FOR = 23, 7
# 3, the storm crew
SALVAGE, SALVAGE_MOST, STAKE, HANDS, OVERHEAR, LOCKER, BOUNTY = 3, 10, 10, 3, 30, 25, 40
CARD_BASE, CARD_LUCK, CARD_BARTER, CARD_BOATS, CARD_MOST = 20, 5, 4, 10, 85
LOCKER_CELLS = 20
OVERHEAR_NEAR = 600

# who: key -> (editor ID, name, sex, wears, faction, package)
PEOPLE = {
    'hand': ('FOLabPearlBoatyardHand', 'Boatyard Hand', 'M', ('OutfitMerc02|ArmorLeather', 'Weap10mmPistol'), 'traders', 'DefaultSandboxEditorLocation256'),
    'crew1': ('FOLabPearlBoatyardCrew1', 'Boatyard Crewman', 'M', ('ArmorLeather', 'WeapNVVarmintRifle|Weap10mmPistol'), 'traders', 'DefaultSandboxEditorLocation256'),
    'crew2': ('FOLabPearlBoatyardCrew2', 'Boatyard Crewman', 'M', ('ArmorLeather', 'Weap10mmPistol'), 'traders', 'DefaultSandboxEditorLocation256'),
    'scav': ('FOLabPearlScavenger', 'Kuliouou Scavenger', 'M', ('OutfitWastelandWanderer|OutfitPrewarCasualwear', 'WeapNVMachete|Weap10mmPistol'), '', 'DefaultSandboxEditorLocation256'),
    'guard': ('FOLabPearlBoyGuard', 'Boat Guard', 'M', ('ArmorLeather', 'Weap10mmPistol'), 'traders', 'DefaultStayAtEditorLocation'),
    'boss': ('FOLabPearlStormBoss', 'Storm Crew Boss', 'M', ('OutfitMerc02|ArmorLeather', 'Weap10mmPistol'), 'traders', 'DefaultStayAtEditorLocation'),
    'dealer': ('FOLabPearlStormDealer', 'Card Dealer', 'F', ('OutfitPrewarCasualwear',), 'traders', 'DefaultStayAtEditorLocation'),
    'deck1': ('FOLabPearlStormDeckhand1', 'Deckhand', 'M', ('ArmorLeather', 'WeapNVMachete|Weap10mmPistol'), 'traders', 'DefaultSandboxEditorLocation256'),
    'deck2': ('FOLabPearlStormDeckhand2', 'Deckhand', 'F', ('ArmorLeather', 'Weap10mmPistol'), 'traders', 'DefaultSandboxEditorLocation256'),
}
REF = {k: v[0] + 'Ref' for k, v in PEOPLE.items()}
REF.update({'boy': 'FOLabPearlBoyRef', 'boy_home': 'FOLabPearlBoyHomeRef', 'box': 'FOLabPearlStrongboxRef', 'panel': 'FOLabPearlLiftPanelRef',
            'cache': 'FOLabPearlBoatCacheRef', 'parent': 'FOLabPearlStormCrewRef', 'locker': 'FOLabPearlStormLockerRef',
            'father': FATHER})
CREW_PARENT = REF['parent']
STORM_CREW = ('boss', 'dealer', 'deck1', 'deck2')
RACES = ('Hispanic', 'Asian', 'AfricanAmerican', 'Caucasian')

W = {
    # 1
    'hand_hi': "You. You look like you can climb stairs. Got a minute for a boat crew?",
    'hand_what': "What's the trouble?",
    'hand_story': "My crew's toll crate. Charged cells, a season's worth. Gone off the yard in the night. A Kuliouou scavenger took it, I'd "
                  "bet my boat. Squats in the Pink Pearl, the pink hotel south of the yard. Find it and you'll be paid.",
    'hand_wait': "The Pink Pearl. South of the yard. Bring my crate back.",
    'hand_crate': "That's my crate. You found it.",
    'return': "Here's your crate.",
    'return_yes': "Every cell still in it. Twenty-five for your trouble. The boats will hear you did right by us.",
    'return_boats': "Every cell still in it. One of the boat-born, eh? Thirty-five, then. The boats look after their own.",
    'haggle': "It was a hard climb. Worth more than twenty-five.",
    'haggle_yes': "All right, all right. Fifty. Just give it here.",
    'haggle_no': "Twenty-five's what it's worth to me. Take it or keep climbing.",
    'lie': "I looked. Somebody burnt it. It's gone.",
    'lie_yes': "Burnt. Course it was. Figures. Forget it, then.",
    'lie_no': "You're lying. I can see the crate's shape in your pack. Hand it over.",
    'lie_kin': "A captain's kin, telling a boatman tales? You'd say anything.",
    'keep': "I'm keeping it.",
    'keep_yes': "Then you've made enemies on the water. Boys!",
    'sell': "The one who took it is a Kuliouou scavenger on the Pearl's top floor.",
    'sell_yes': "Is he now. My boys will have words with him. Fifteen, for the name.",
    'scav_hi': "Nothing left on these floors. Go on, mind your business.",
    'scav_ask': "Did you take a crate from the boatyard?",
    'scav_ask_yes': "And if I did? The boats bleed Kuliouou for tolls every season. I took a little back.",
    'scav_found': "You found it. That's ours, by rights. The boats took it from Kuliouou cell by cell. Give it back to me.",
    'give': "Take it. Kuliouou needs it more than the boats.",
    'give_yes': "You're all right. Kuliouou won't forget it.",
    'refuse': "No. It's not yours either.",
    'refuse_yes': "Then you're no better than them.",
    'fight_scav': "Hand over your key, or I'll take it.",
    'fight_scav_yes': "You want it? Come and get it.",
    # 2
    'father_hi': "They're holding my boy at the Pink Pearl, by the marina, till the boat sails. I can't buy him back. I've nothing left.",
    'father_back': "My boy. You brought him home. Sit, eat. And listen: the boats keep a cache a little way off from the camp. I'll show you "
                   "where. Take it. They owe us that much.",
    'father_after': "He sleeps by the fire now. I won't sell him again.",
    'father_sailed': "The boat's gone. So is he.",
    'boy_thanks': "You came for me. Nobody comes for anyone.",
    'boy_home': "I'm home. I'll never go near the marina again.",
    'guard_hi': "Nobody sees the boy. He sails with the tide.",
    'guard_caught': "Hey. Thought you'd creep past me while I slept?",
    'buy': "I'll buy him back.",
    'buy_yes': "Sixty cells. Done. Take him, he cries all night anyway.",
    'buy_kin': "From a captain's kin? A hundred and twenty. The boats remember what your people did.",
    'buy_kin_yes': "A hundred and twenty. Done. Get him out of my sight.",
    'buy_no': "Sixty cells. Come back when you have them.",
    'barter': "Sixty for one scrawny boy? Thirty, and you're well paid.",
    'barter_yes': "Thirty. You'd have made a good boatman. Take him.",
    'barter_no': "Sixty. Not a cell less.",
    'talk': "The boat's captain won't miss one boy. You'll have less trouble without him.",
    'talk_yes': "Maybe you're right. He's more trouble than he's worth. Go on, take him.",
    'talk_no': "Nice words. The captain pays me to keep him, not to listen to you.",
    'boats': "We grew up on the same decks. Let him go, for the boats.",
    'boats_yes': "Boat-born, are you? All right. For the boats. Take him before I think better of it.",
    'boats_no': "The boats don't owe you anything.",
    'threat': "Let him go, or they'll find you floating in the marina.",
    'threat_yes': "All right! All right. He's yours. I was never here.",
    'threat_no': "You? Don't make me laugh.",
    'fight': "Then I'll take him.",
    'fight_yes': "Try it.",
    # 3
    'boss_hi': "Storm's got the whole marina in here. Trade, play, or keep walking.",
    'boss_kin': "A captain's kin in our lobby. We don't trade with your sort. Play cards if you must.",
    'salvage': "I've got storm salvage. Scrap metal.",
    'salvage_yes': "Three cells a piece, ten pieces at most. Let's see it.",
    'salvage_done': "One haul a storm. Come back next blow.",
    'cards': "Deal me in.",
    'cards_yes': "Ten cells on the table. Luck's a lady, the boats say.",
    'cards_no': "Three hands a storm, and ten cells a hand. House rules.",
    'dealer_hi': "Ten cells a hand. Sit down or move along.",
    'report': "Your boat at the marina's sitting unguarded.",
    'report_yes': "Is it now. You didn't have to tell us that. The boats won't forget.",
    'fight_crew': "This lobby belongs to the court. Get out.",
    'fight_crew_yes': "In this weather? Over our dead bodies.",
    'deck1': "Blowing a gale out there. Wouldn't put a dinghy out in this.",
    'deck2': "Fire's warm, cards are crooked. Best storm in years.",
}
MSG = {
    'panel_open': "You force the jammed lift panel. Behind it, a service way runs to the room where the strongbox sits; you work its "
                  "lock loose from the back.",
    'panel_jammed': "The lift's service panel is rusted shut. It would take some Repair skill to force it.",
    'panel_done': "The service panel hangs open.",
    'shackle_open': "The shackle's lock gives. The boy is free.",
    'shackle_key': "The guard's key turns the shackle. The boy is free.",
    'shackle_watched': "The guard is right there, watching you.",
    'shackle_locked': "The shackle is locked. It would take more Lockpick skill than you have.",
    'won': "You win the hand: twenty cells.",
    'lost': "You lose the hand.",
    'traded': "The boss counts your scrap and pays you in cells.",
    'overheard': "You overhear the boss: their boat at the marina is sitting unguarded, its locker full.",
    'bounty': "The court pays a bounty for the storm crew: forty kala.",
}


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _places(pr):
    return {recordio.field(r, 'EDID'): k for k, r in pr.records.items() if r.get('type') == 'CELL' and k.startswith('+')}


def _ed(gd, pr, base):
    if not base:
        return ''
    if base.startswith('+'):
        return recordio.field(pr.records[base], 'EDID') if base in pr.records else ''
    try:
        return gd.edid(gd.from_key(base)) or ''
    except Exception:
        return ''


def _refs(gd, pr, ck, words):
    """[(ref key, ref)] in a place whose base's editor ID has any of `words`."""
    out = []
    for rk, r in ((pr.cells.get(ck) or {}).get('refs') or {}).items():
        if not r.get('removed') and r.get('p') and any(w in _ed(gd, pr, r.get('base')) for w in words):
            out.append((rk, r))
    return sorted(out)


# ---------- where ----------

def plan(gd, pr):
    """Spots inside the Pearl (on its navmeshes, clear of doors, seats and each other) and outside by the marina and the camp."""
    import activity
    import robots
    from castawayquest import _ref_by_edid
    rows, skipped, S = [], [], {}
    places = _places(pr)
    missing = [v for v in FLOORS.values() if v not in places]
    if missing:
        return {'rows': [], 'skipped': ['the Pink Pearl\'s places are not in the mod: %s' % ', '.join(missing)], 'spots': {}}
    ck = {k: places[v] for k, v in FLOORS.items()}
    taken = {}

    def inside(what, floor, kind='butler'):
        got, why = robots.inside_spots(gd, pr, ck[floor], (kind,), taken.get(floor, ()))
        if not got:
            skipped.append('%s: %s' % (what, why))
            return None
        p = got[0][1]
        taken.setdefault(floor, []).append(p[:3])
        S[what] = {'cell': ck[floor], 'p': p}
        rows.append({'what': what, 'place': FLOORS[floor], 'p': [round(v) for v in p[:3]], 'clear': got[0][2]})
        return p
    # 1: the box deep in Guest Floor 1, the lift's panel by Guest Floor 2's lift, the scavenger on the top floor
    inside('box', 'g1', 'bank_guard')
    inside('panel', 'g2', 'doorman')
    inside('scav', 'top')
    # 2: the boy deep in Guest Floor 2, his guard between him and the lift; the guard's bed the nearest to his post
    inside('boy', 'g2', 'bank_guard')
    inside('guard', 'g2', 'doorman')
    if 'guard' in S:
        beds = _refs(gd, pr, ck['g2'], ('Bed',))
        gp = S['guard']['p']
        if beds:
            S['guard_bed'] = min(beds, key=lambda b: math.hypot(b[1]['p'][0] - gp[0], b[1]['p'][1] - gp[1]))[0]
            rows.append({'what': 'guard bed', 'ref': S['guard_bed']})
        else:
            skipped.append('guard bed: no bed on Guest Floor 2')
    if 'guard_bed' in S and 'boy' in S:         # (asleep he must lie near enough the boy to wake; awake he must see him)
        bed = pr.cells[ck['g2']]['refs'][S['guard_bed']]['p']
        bp, gp = S['boy']['p'], S['guard']['p']
        to_bed, to_post = math.hypot(bed[0] - bp[0], bed[1] - bp[1]), math.hypot(gp[0] - bp[0], gp[1] - bp[1])
        rows.append({'what': 'the boy from the guard', 'bed': round(to_bed), 'post': round(to_post)})
        if to_bed >= WAKE_NEAR - 100 or to_post >= WATCHED:
            skipped.append('the boy is %d from the guard bed and %d from his post: the sneak would not be needed' % (to_bed, to_post))
            del S['guard_bed']
    # 3: the storm crew round the lobby's lounge; the fire and the card table among them
    for k in STORM_CREW + ('fire', 'table'):
        inside(k, 'lobby')
    # outside: the boatyard hand and his crew by Koko Marina's marker, the boy at home and the cache by the camp, the locker by a boat
    ctx = activity.Ctx(gd, pr)
    mk = {n: p for n, (_c, p) in ctx.mk.items()}
    marina, camp = mk.get(MARINA), mk.get(KULIOUOU)
    if not marina:
        skipped.append('no %s marker' % MARINA)
    else:
        for k, radii in (('hand', (400, 550, 700)), ('crew1', (500, 650, 800)), ('crew2', (500, 650, 800, 950))):
            got = ctx.around(marina[0], marina[1], 1, radii=radii)
            if got:
                S[k] = {'world': tuple(got[0][:3])}
                rows.append({'what': k, 'p': [round(v) for v in got[0][:3]]})
            else:
                skipped.append('%s: no spot at %s' % (k, MARINA))
        boats = [p for e in ('Boat01a', 'Boat01b', 'Boat02a', 'Boat03a', 'Boat03b') for _c, p in ctx.refs.get(e, ())
                 if math.hypot(p[0] - marina[0], p[1] - marina[1]) < 4000]
        boats.sort(key=lambda p: math.hypot(p[0] - marina[0], p[1] - marina[1]))
        for b in boats + [marina]:
            got = ctx.around(b[0], b[1], 1, radii=(250, 350, 500, 700))
            if got:
                S['locker'] = {'world': tuple(got[0][:3]), 'rz': math.atan2(b[0] - got[0][0], b[1] - got[0][1])}
                rows.append({'what': 'locker', 'p': [round(v) for v in got[0][:3]], 'by a boat': b is not marina})
                break
        else:
            skipped.append('locker: no spot by the marina\'s boats')
    _fc, father = _ref_by_edid(pr, FATHER)
    fp = None
    if father:
        fr = pr.cells[_fc]['refs'][father]
        fp = fr['p']
    elif camp:
        fp = camp
    if not fp:
        skipped.append('no Kuliouou father or camp marker')
    else:
        got = ctx.around(fp[0], fp[1], 1, radii=(160, 220, 300))
        if got:
            S['boy_home'] = {'world': tuple(got[0][:3])}
            rows.append({'what': 'boy at home', 'p': [round(v) for v in got[0][:3]]})
        else:
            skipped.append('boy at home: no spot by his father')
        c = camp or fp
        got = ctx.around(c[0], c[1], 1, radii=(900, 1100, 1300, 1500))
        if got:
            S['cache'] = {'world': tuple(got[0][:3])}
            rows.append({'what': 'cache', 'p': [round(v) for v in got[0][:3]]})
        else:
            skipped.append('cache: no spot near the camp')
    return {'rows': rows, 'skipped': skipped, 'spots': S, 'world': ctx.world}


# ---------- people and things ----------

def _item_key(gd, pr, names):
    for e in names.split('|'):
        k = _mod_key(pr, e)
        if k:
            return k
        f = next((f for f, (i, r) in gd.forms.items() if r.tag in ('ARMO', 'WEAP', 'KEYM', 'ALCH', 'MISC') and gd.edid(f) == e), None)
        if f is not None:
            return gd.key(f)
    return None


def _faces(gd, pr):
    import heldwatch
    import missouriguns
    return {'M': heldwatch.men_faces(gd, pr), 'F': missouriguns.women_faces(gd, pr)}


def _person(gd, pr, k, face, fac, extra=()):
    import factionfolk as ff
    edid, name, _sex, wears, _f, package = PEOPLE[k]
    g = dict(ff.GROUPS['court_fighter'])
    g['package'] = package
    items = [(it, 1) for it in (_item_key(gd, pr, n) for n in wears) if it] + list(extra)
    rec = ff.person(gd, pr, face, edid, name, g, items, [], fac or '')
    ff._set_num(rec, 'AIDT', 'Aggression', 1)
    ff._set_num(rec, 'AIDT', 'Confidence', 3 if k != 'scav' else 2)
    return rec


def _pick_faces(gd, pr):
    """{person: game NPC_ face}: none any person of the mod wears, none twice here; races taken in turn."""
    pools = _faces(gd, pr)
    used, out = set(), {}
    for n, k in enumerate(PEOPLE):
        sex = PEOPLE[k][2]
        order = RACES[n % len(RACES):] + RACES[:n % len(RACES)]
        face = next((f for race in order for f in pools[sex].get(race, ()) if gd.key(f) not in used), None)
        if face is None:
            raise ValueError('no free face left for %s' % PEOPLE[k][0])
        used.add(gd.key(face))
        out[k] = face
    return out


def _global(edid, value=0.0):
    import stormafter
    rec = json.loads(json.dumps(stormafter.flag_record()))
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    return rec


def _misc(gd, edid, name, like):
    import surffish
    rec = surffish._copy(gd, 'MISC', like, edid, name)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'SCRI']
    return rec


def _key(gd, edid, name):
    import surffish
    like = next(gd.edid(f) for f, (i, r) in sorted(gd.forms.items()) if r.tag == 'KEYM' and i == 0)
    rec = surffish._copy(gd, 'KEYM', like, edid, name)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'SCRI']
    return rec


def _container(gd, pr, edid, name, items):
    import api_characters as ac
    import anquest
    import sidequests
    rec = anquest._chest(gd, pr, edid, items[0][0])
    for s in rec['subs']:
        if s['tag'] == 'CNTO':
            for f in s['fields']:
                if f.get('name') == 'Count':
                    f['value'] = items[0][1]
    for it, n in items[1:]:
        ac.insert(rec, sidequests._cnto(gd, it, n))
    if any(s['tag'] == 'FULL' for s in rec['subs']):
        recordio.set_field(rec, 'FULL', name)
    else:
        ac.insert(rec, {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name})
    return rec


def _set_script(rec, skey):
    import api_characters as ac
    if any(s['tag'] == 'SCRI' for s in rec['subs']):
        for s in rec['subs']:
            if s['tag'] == 'SCRI':
                s['value'] = skey
    else:
        ac.insert(rec, {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': skey})


# ---------- scripts ----------

def cells_script():
    q, r = QUESTS['cells'], REF
    return '\n'.join([
        'scn FOLabPearlCellsScript',
        'short met', 'short found', 'short scav_met', 'short resolved', 'short sold', 'short scav_gone', 'short done', 'short panel', '',
        'Begin GameMode',
        '\tif met == 1', '\t\tif GetStage %s < 10' % q, '\t\t\tSetStage %s 10' % q, '\t\tendif', '\tendif',
        '\tif found == 0', '\t\tif player.GetItemCount FOLabPearlCrate >= 1', '\t\t\tset found to 1',
        '\t\t\tif GetStage %s < 20' % q, '\t\t\t\tSetStage %s 20' % q, '\t\t\tendif', '\t\tendif', '\tendif',
        '\tif resolved > 0', '\t\tif done == 0', '\t\t\tset done to 1',
        '\t\t\tif resolved == 1', '\t\t\t\tSetStage %s 50' % q, '\t\t\telseif resolved == 2', '\t\t\t\tSetStage %s 52' % q,
        '\t\t\telseif resolved == 3', '\t\t\t\tSetStage %s 54' % q, '\t\t\telse', '\t\t\t\tSetStage %s 56' % q, '\t\t\tendif',
        '\t\tendif', '\tendif',
        # (sold out: the hand's crew take the scavenger away once you're off the top floor)
        '\tif sold == 1', '\t\tif scav_gone == 0', '\t\t\tif player.GetDistance %s > 3000' % r['scav'], '\t\t\t\tset scav_gone to 1',
        '\t\t\t\tif %s.GetDead == 0' % r['scav'], '\t\t\t\t\t%s.Disable' % r['scav'], '\t\t\t\tendif', '\t\t\tendif', '\t\tendif', '\tendif',
        'End', ''])


def panel_script():
    q, r = QUESTS['cells'], REF
    return '\n'.join([
        'scn FOLabPearlLiftPanelScript', '', 'Begin OnActivate player',
        '\tif %s.panel == 1' % q, '\t\tShowMessage FOLabPearlMsgPanelDone',
        '\telseif player.GetActorValue Repair >= %d' % PANEL_REPAIR, '\t\tset %s.panel to 1' % q, '\t\t%s.Unlock' % r['box'],
        '\t\tShowMessage FOLabPearlMsgPanelOpen',
        '\telse', '\t\tShowMessage FOLabPearlMsgPanelJammed', '\tendif', 'End', ''])


def boy_script():
    q, r = QUESTS['boy'], REF
    g, b = r['guard'], r['boy']
    stage = ['\t\t\tif freed == %d' % n + '\n\t\t\t\tSetStage %s %d\n\t\t\tendif' % (q, 18 + 2 * n) for n in range(1, 6)]
    return '\n'.join([
        'scn FOLabPearlBoyScript',
        'short started', 'float sail_day', 'short freed', 'short gone', 'short home', 'short rewarded', 'short sailed', 'short woke', 'short found', '',
        'Begin GameMode',
        '\tif started == 0', '\t\tif GetStage %s >= %d' % (FIRST_PLACE, FIRST_DONE), '\t\t\tset started to 1',
        '\t\t\tset sail_day to GameDaysPassed + %d' % SAIL_DAYS, '\t\t\t%s.Enable' % b, '\t\t\t%s.Enable' % g,
        '\t\t\tSetStage %s 10' % q, '\t\tendif', '\tendif',
        # (asleep: he wakes if you come near unsneaking, or sneaking with too little skill; then he has words with you)
        '\tif started == 1', '\t\tif freed == 0', '\t\t\tif woke == 0', '\t\t\t\tif %s.GetDead == 0' % g, '\t\t\t\t\tif %s.GetSleeping >= 3' % g,
        '\t\t\t\t\t\tif player.GetDistance %s < %d' % (g, WAKE_NEAR),
        '\t\t\t\t\t\t\tif player.IsSneaking == 0 || player.GetActorValue Sneak < %d' % SNEAK,
        '\t\t\t\t\t\t\t\tset woke to 1', '\t\t\t\t\t\t\t\t%s.StartConversation player FOLabPearlBoyCaught' % g,
        '\t\t\t\t\t\t\tendif', '\t\t\t\t\t\tendif', '\t\t\t\t\tendif', '\t\t\t\tendif', '\t\t\tendif',
        '\t\t\tif GameDaysPassed >= sail_day', '\t\t\t\tset sailed to 1', '\t\t\t\tset freed to -1', '\t\t\t\t%s.Disable' % b,
        '\t\t\t\t%s.Disable' % g, '\t\t\t\tSetStage %s 90' % q, '\t\t\tendif', '\t\tendif', '\tendif',
        # (freed: off home by himself; how he was freed says which stage)
        '\tif freed > 0', '\t\tif gone == 0', '\t\t\tset gone to 1'] + stage + [
        '\t\t\t%s.Disable' % b, '\t\t\t%s.Enable' % r['boy_home'], '\t\tendif', '\tendif',
        '\tif rewarded == 1', '\t\tif found == 0', '\t\t\tif player.GetDistance %s < 300' % r['cache'], '\t\t\t\tset found to 1',
        '\t\t\t\tSetStage %s 110' % q, '\t\t\tendif', '\t\tendif', '\tendif',
        'End', ''])


def shackle_script():
    """On the boy in the Pearl: talking to him is trying his shackle until he's free."""
    q, r = QUESTS['boy'], REF
    g = r['guard']
    return '\n'.join([
        'scn FOLabPearlShackleScript', 'short watched', '', 'Begin OnActivate player',
        '\tif %s.freed != 0' % q, '\t\tActivate', '\t\treturn', '\tendif',
        '\tset watched to 0', '\tif %s.GetDead == 0' % g, '\t\tif %s.GetSleeping < 3' % g,
        '\t\t\tif player.GetDistance %s < %d' % (g, WATCHED), '\t\t\t\tset watched to 1', '\t\t\tendif', '\t\tendif', '\tendif',
        '\tif player.GetItemCount FOLabPearlShackleKey >= 1', '\t\tset %s.freed to 5' % q, '\t\tShowMessage FOLabPearlMsgShackleKey',
        '\telseif watched == 1', '\t\tShowMessage FOLabPearlMsgShackleWatched',
        '\telseif player.GetActorValue Lockpick >= %d' % SHACKLE_LOCK, '\t\tset %s.freed to 4' % q, '\t\tShowMessage FOLabPearlMsgShackleOpen',
        '\telse', '\t\tShowMessage FOLabPearlMsgShackleLocked', '\tendif', 'End', ''])


def storm_script():
    q, r = QUESTS['storm'], REF
    crew = [r[k] for k in STORM_CREW]
    dead = ' && '.join('%s.GetDead == 1' % c for c in crew)
    L = ['scn FOLabPearlStormScript',
         'short on', 'short storms', 'short traded', 'short trade', 'short hands', 'short deal', 'short roll', 'short chance',
         'short overheard', 'short reported', 'short looted', 'short fought', 'short scrap', '',
         'Begin GameMode',
         # (a big storm: the crew in, everything once a storm again; the dead come back with the next crew)
         '\tif on == 0', '\t\tif %s == 1' % SHELTER, '\t\t\tset on to 1', '\t\t\tset storms to storms + 1',
         '\t\t\tset traded to 0', '\t\t\tset hands to 0', '\t\t\tset overheard to 0', '\t\t\tset reported to 0', '\t\t\tset looted to 0',
         '\t\t\tset fought to 0']
    L += ['\t\t\tif %s.GetDead == 1' % c + '\n\t\t\t\t%s.Resurrect 0\n\t\t\tendif' % c for c in crew]
    L += ['\t\t\t%s.Enable' % r['parent'], '\t\t\tif GetStage %s < 10' % q, '\t\t\t\tSetStage %s 10' % q, '\t\t\tendif', '\t\tendif', '\tendif',
          '\tif on == 1', '\t\tif %s == 0' % SHELTER, '\t\t\tif player.GetInCell %s == 0' % FLOORS['lobby'], '\t\t\t\tset on to 0',
          '\t\t\t\t%s.Disable' % r['parent'], '\t\t\t\t%s.Disable' % r['locker'], '\t\t\tendif', '\t\tendif', '\tendif',
          # (salvage: scrap metal for cells, ten pieces at most)
          '\tif trade == 1', '\t\tset trade to 0', '\t\tset traded to 1', '\t\tset scrap to player.GetItemCount %s' % SCRAP,
          '\t\tif scrap >= %d' % SALVAGE_MOST, '\t\t\tplayer.RemoveItem %s %d' % (SCRAP, SALVAGE_MOST),
          '\t\t\tplayer.AddItem %s %d' % (CELL, SALVAGE * SALVAGE_MOST),
          '\t\telseif scrap >= 5', '\t\t\tplayer.RemoveItem %s 5' % SCRAP, '\t\t\tplayer.AddItem %s %d' % (CELL, SALVAGE * 5),
          '\t\telseif scrap >= 1', '\t\t\tplayer.RemoveItem %s 1' % SCRAP, '\t\t\tplayer.AddItem %s %d' % (CELL, SALVAGE),
          '\t\tendif', '\t\tShowMessage FOLabPearlMsgTraded', '\tendif',
          # (cards: the stake is on the table already; the chance from Luck and Barter)
          '\tif deal == 1', '\t\tset deal to 0', '\t\tset hands to hands + 1',
          '\t\tset chance to %d + player.GetActorValue Luck * %d + player.GetActorValue Barter / %d' % (CARD_BASE, CARD_LUCK, CARD_BARTER),
          '\t\tif player.HasPerk %s == 1' % TRAITS['boats'], '\t\t\tset chance to chance + %d' % CARD_BOATS, '\t\tendif',
          '\t\tif chance > %d' % CARD_MOST, '\t\t\tset chance to %d' % CARD_MOST, '\t\tendif',
          '\t\tset roll to GetRandomPercent',
          '\t\tif roll < chance', '\t\t\tplayer.AddItem %s %d' % (CELL, 2 * STAKE), '\t\t\tShowMessage FOLabPearlMsgWon',
          '\t\telse', '\t\t\tShowMessage FOLabPearlMsgLost', '\t\tendif', '\tendif',
          # (overheard: sneaking near the boss)
          '\tif on == 1', '\t\tif overheard == 0', '\t\t\tif %s.GetDead == 0' % r['boss'], '\t\t\t\tif player.IsSneaking == 1',
          '\t\t\t\t\tif player.GetActorValue Sneak >= %d' % OVERHEAR, '\t\t\t\t\t\tif player.GetDistance %s < %d' % (r['boss'], OVERHEAR_NEAR),
          '\t\t\t\t\t\t\tset overheard to 1', '\t\t\t\t\t\t\t%s.RemoveAllItems' % r['locker'], '\t\t\t\t\t\t\t%s.AddItem %s %d' % (r['locker'], CELL, LOCKER_CELLS),
          '\t\t\t\t\t\t\t%s.AddItem %s 1' % (r['locker'], STIM), '\t\t\t\t\t\t\t%s.Lock %d' % (r['locker'], LOCKER), '\t\t\t\t\t\t\t%s.Enable' % r['locker'],
          '\t\t\t\t\t\t\tShowMessage FOLabPearlMsgOverheard', '\t\t\t\t\t\t\tSetStage %s 20' % q,
          '\t\t\t\t\t\tendif', '\t\t\t\t\tendif', '\t\t\t\tendif', '\t\t\tendif', '\t\tendif', '\tendif',
          '\tif overheard == 1', '\t\tif looted == 0', '\t\t\tif reported == 0', '\t\t\t\tif %s.GetItemCount %s == 0' % (r['locker'], CELL),
          '\t\t\t\t\tset looted to 1', '\t\t\t\t\tSetStage %s 30' % q, '\t\t\t\tendif', '\t\t\tendif', '\t\tendif', '\tendif',
          # (the fight: every one of the crew down, the court's bounty)
          '\tif on == 1', '\t\tif fought == 0', '\t\t\tif %s' % dead, '\t\t\t\tset fought to 1', '\t\t\t\tplayer.AddItem %s %d' % (KALA, BOUNTY),
          '\t\t\t\tShowMessage FOLabPearlMsgBounty', '\t\t\t\tSetStage %s 40' % q, '\t\t\tendif', '\t\tendif', '\tendif',
          'End', '']
    return '\n'.join(L)


def _stage(n, log, src=''):
    return {'index': n, 'entries': [{'flags': {}, 'conditions': [], 'next': '', 'log': log, 'script': {'source': src, 'parts': None}}]}


def quests_plain(keys, skeys, have, targets):
    """{which: quest plain}. have: which standings records the mod has; targets: {name: ref key} for objectives."""
    pf = (lambda n: 'AddReputation %s 1 %d\n' % (REP_PIRATES, n)) if have.get('rep') else (lambda n: '')
    pi = (lambda n: 'AddReputation %s 0 %d\n' % (REP_PIRATES, n)) if have.get('rep') else (lambda n: '')
    bump = (lambda n: 'set %s.pirates to %s.pirates %s %d\n' % (NAME_Q, NAME_Q, '+' if n >= 0 else '-', abs(n))) if have.get('names') else (lambda n: '')
    kuli = 'set %s to %s + %d\n' % (KULI, KULI, KULI_GOOD)

    def obj(q, n, on=1):
        return 'SetObjectiveDisplayed %s %d %d\n' % (QUESTS[q], n, on)

    def done(q, n):
        return 'SetObjectiveCompleted %s %d 1\n' % (QUESTS[q], n)
    keep = 'player.RemoveItem FOLabPearlCrate 1\nplayer.AddItem %s %d\n' % (CELL, CRATE)
    crew = ''.join('%s.StartCombat player\n' % REF[k] for k in ('hand', 'crew1', 'crew2'))
    C = [
        _stage(10, "A boatyard hand at Koko Marina lost his crew's toll crate of charged cells. He's sure a Kuliouou scavenger stashed it in the "
                   "Pink Pearl.", obj('cells', 10)),
        _stage(20, "I found the boatyard's crate in the Pink Pearl. What becomes of it is up to me.", done('cells', 10) + obj('cells', 20)),
        _stage(50, "I gave the crate back to the boatyard hand and was paid in cells.", done('cells', 20) + 'CompleteQuest %s\n' % QUESTS['cells']),
        _stage(52, "I told the boatyard hand the crate was burnt, and kept the cells.", keep + done('cells', 20) + 'CompleteQuest %s\n' % QUESTS['cells']),
        _stage(54, "I kept the crate to the boatyard hand's face. His crew won't forget it.",
               keep + crew + pi(1) + bump(-10) + done('cells', 20) + 'CompleteQuest %s\n' % QUESTS['cells']),
        _stage(56, "I gave the crate to the Kuliouou scavenger. Kuliouou needs it more than the boats.",
               kuli + done('cells', 20) + 'CompleteQuest %s\n' % QUESTS['cells']),
        _stage(60, "I told the boatyard hand who took his crate. His crew will have words with the scavenger.", ''),
    ]
    freed = lambda log, paid: _stage(0, log, done('boy', 10) + obj('boy', 20) + ('' if paid else pi(1) + bump(-10)) + kuli)
    B = [_stage(10, "The son Kuliouou sold is held in the Pink Pearl, by Koko Marina, until his boat sails. One guard keeps him.", obj('boy', 10))]
    for n, (log, paid) in enumerate((("I bought the boy back from his guard.", True), ("I talked the guard into letting the boy go.", False),
                                     ("I scared the guard into letting the boy go.", False),
                                     ("I crept past the sleeping guard and picked the boy's shackle.", False),
                                     ("I took the shackle key from the guard and freed the boy.", False)), 1):
        s = freed(log + " He's gone home to Kuliouou by himself.", paid)
        s['index'] = 18 + 2 * n
        B.append(s)
    B += [_stage(90, "The boat sailed with the boy aboard.", 'SetObjectiveDisplayed %s 10 0\nCompleteQuest %s\n' % (QUESTS['boy'], QUESTS['boy'])),
          _stage(100, "The boy's father fed me and showed me where the boats keep a cache near the camp.",
                 done('boy', 20) + 'player.AddItem %s 2\n' % MEAL + '%s.Enable\n' % REF['cache'] + obj('boy', 30)),
          _stage(110, "I found the boats' cache by Kuliouou's camp.", done('boy', 30) + 'CompleteQuest %s\n' % QUESTS['boy'])]
    S = [_stage(10, "When a big storm blows, the boats run for Koko Marina and their crews shelter in the Pink Pearl's lobby, round a fire and "
                    "a card table.", ''),
         _stage(20, "I overheard the storm crew: their boat at the marina is sitting unguarded, its locker full.", ''),
         _stage(30, "I emptied the storm crew's boat locker at the marina.", ''),
         _stage(32, "I told the storm crew their boat was sitting unguarded.", pf(1) + bump(5)),
         _stage(40, "I fought the storm crew in the Pink Pearl. The court paid a bounty for them.", pi(1) + bump(-5))]
    tgt = lambda n: [{'target': targets[n], 'flags': 0, 'conditions': []}] if targets.get(n) else []
    objectives = {
        'cells': [{'index': 10, 'text': "Find the boatyard's crate in the Pink Pearl", 'targets': []},
                  {'index': 20, 'text': "Decide what becomes of the crate", 'targets': tgt('hand')}],
        'boy': [{'index': 10, 'text': "Free the boy from the Pink Pearl before his boat sails", 'targets': tgt('boy')},
                {'index': 20, 'text': "Tell his father in Kuliouou", 'targets': tgt('father')},
                {'index': 30, 'text': "Find the boats' cache by Kuliouou's camp", 'targets': tgt('cache')}],
        'storm': []}
    stages = {'cells': C, 'boy': B, 'storm': S}
    return {w: {'edid': QUESTS[w], 'name': NAMES[w], 'script': skeys[w], 'flags': {'start_enabled': True, 'repeat_stages': w == 'storm'},
                'priority': 55, 'delay': 1.0, 'stages': stages[w], 'objectives': objectives[w], 'conditions': []} for w in QUESTS}


# ---------- lines ----------

def lines_spec():
    """[(who, topic, words key, conditions, end script, skill, choices)]: every line of the three quests, in the order the game
    tries them. A condition: ('q', which, var, op, v), ('stage', which, op, v), ('fq', quest edid, op, v),
    ('skill', name, op, v), ('glob', name, op, v), ('items', item, op, v), ('perk', trait, v). Topic 'G' is the greeting."""
    L = []

    def line(who, topic, words, conds=(), end='', skill=None, choices=()):
        L.append((who, topic, words, list(conds), end, skill, list(choices)))
    c, b, s = QUESTS['cells'], QUESTS['boy'], QUESTS['storm']
    qv = lambda w, var, op, v: ('q', w, var, op, v)
    has_crate = ('items', 'FOLabPearlCrate', '>=', 1)
    open_ = qv('cells', 'resolved', '==', 0)
    setc = lambda var, v=1: 'set %s.%s to %s' % (c, var, v)
    setb = lambda var, v=1: 'set %s.%s to %s' % (b, var, v)
    sets = lambda var, v=1: 'set %s.%s to %s' % (s, var, v)
    pay = lambda n: 'player.AddItem %s %d' % (CELL, n)
    fame = 'AddReputation %s 1 1' % REP_PIRATES
    # 1: the hand
    line('hand', 'G', 'hand_crate', [qv('cells', 'met', '==', 1), open_, has_crate], '', None, ['return', 'haggle', 'lie', 'keep', 'sell'])
    line('hand', 'G', 'hand_wait', [qv('cells', 'met', '==', 1), open_], '', None, ['sell'])
    line('hand', 'G', 'hand_hi', [qv('cells', 'met', '==', 0)], '', None, ['hand_what'])
    line('hand', 'hand_what', 'hand_story', [qv('cells', 'met', '==', 0)], setc('met'))
    line('hand', 'return', 'return_boats', [open_, has_crate, ('perk', 'boats', 1)],
         'player.RemoveItem FOLabPearlCrate 1\n%s\n%s\n%s' % (pay(PAY + BOAT_BONUS), fame, setc('resolved')))
    line('hand', 'return', 'return_yes', [open_, has_crate], 'player.RemoveItem FOLabPearlCrate 1\n%s\n%s\n%s' % (pay(PAY), fame, setc('resolved')))
    line('hand', 'haggle', 'haggle_yes', [open_, has_crate, ('perk', 'dread', 1)],
         'player.RemoveItem FOLabPearlCrate 1\n%s\n%s\n%s' % (pay(2 * PAY), fame, setc('resolved')), 'Speech')
    line('hand', 'haggle', 'haggle_yes', [open_, has_crate, ('glob', TALK_G, '>=', HAGGLE)],
         'player.RemoveItem FOLabPearlCrate 1\n%s\n%s\n%s' % (pay(2 * PAY), fame, setc('resolved')), 'Speech')
    line('hand', 'haggle', 'haggle_no', [open_, has_crate], '', 'Speech', ['return'])
    line('hand', 'lie', 'lie_kin', [open_, has_crate, ('perk', 'kin', 1)], '', 'Speech', ['return', 'keep'])
    line('hand', 'lie', 'lie_yes', [open_, has_crate, ('glob', TALK_G, '>=', LIE)], setc('resolved', 2), 'Speech')
    line('hand', 'lie', 'lie_no', [open_, has_crate], '', 'Speech', ['return', 'keep'])
    line('hand', 'keep', 'keep_yes', [open_, has_crate], setc('resolved', 3))
    line('hand', 'sell', 'sell_yes', [qv('cells', 'scav_met', '==', 1), qv('cells', 'sold', '==', 0)],
         '%s\n%s\n%s\nSetStage %s 60' % (pay(SELL_OUT), fame, setc('sold'), c))
    # 1: the scavenger
    line('scav', 'G', 'scav_found', [open_, has_crate], setc('scav_met'), None, ['give', 'refuse', 'fight_scav'])
    line('scav', 'G', 'scav_hi', [], setc('scav_met'), None, ['scav_ask', 'fight_scav'])
    line('scav', 'scav_ask', 'scav_ask_yes', [], setc('scav_met'))
    line('scav', 'give', 'give_yes', [open_, has_crate], 'player.RemoveItem FOLabPearlCrate 1\n%s' % setc('resolved', 4))
    line('scav', 'refuse', 'refuse_yes', [open_])
    line('scav', 'fight_scav', 'fight_scav_yes', [], '%s.StartCombat player' % REF['scav'])
    # 2: the father and the boy at home
    line('father', 'G', 'father_back', [qv('boy', 'freed', '>', 0), qv('boy', 'rewarded', '==', 0)], setb('rewarded') + '\nSetStage %s 100' % b)
    line('father', 'G', 'father_after', [qv('boy', 'rewarded', '==', 1)])
    line('father', 'G', 'father_sailed', [qv('boy', 'sailed', '==', 1)])
    line('father', 'G', 'father_hi', [qv('boy', 'started', '==', 1), qv('boy', 'freed', '==', 0)])
    line('boy_home', 'G', 'boy_home', [qv('boy', 'rewarded', '==', 1)])
    line('boy_home', 'G', 'boy_thanks', [])
    # 2: the guard (awake, or woken)
    free = qv('boy', 'freed', '==', 0)
    guard_topics = ['buy', 'barter', 'talk', 'boats', 'threat', 'fight']
    line('guard', 'G', 'guard_hi', [free], '', None, guard_topics)
    line('guard', 'caught', 'guard_caught', [free], '', None, guard_topics)
    line('guard', 'buy', 'buy_kin_yes', [free, ('perk', 'kin', 1), ('items', CELL, '>=', 2 * PRICE)],
         'player.RemoveItem %s %d\n%s' % (CELL, 2 * PRICE, setb('freed', 1)))
    line('guard', 'buy', 'buy_kin', [free, ('perk', 'kin', 1)], '', None, ['barter'])
    line('guard', 'buy', 'buy_yes', [free, ('items', CELL, '>=', PRICE)], 'player.RemoveItem %s %d\n%s' % (CELL, PRICE, setb('freed', 1)))
    line('guard', 'buy', 'buy_no', [free], '', None, ['barter'])
    line('guard', 'barter', 'barter_yes', [free, ('perk', 'kin', 0), ('skill', 'Barter', '>=', BARTER), ('items', CELL, '>=', PRICE // 2)],
         'player.RemoveItem %s %d\n%s' % (CELL, PRICE // 2, setb('freed', 1)), 'Barter')
    line('guard', 'barter', 'barter_yes', [free, ('perk', 'kin', 1), ('skill', 'Barter', '>=', BARTER), ('items', CELL, '>=', PRICE)],
         'player.RemoveItem %s %d\n%s' % (CELL, PRICE, setb('freed', 1)), 'Barter')
    line('guard', 'barter', 'barter_no', [free], '', 'Barter')
    line('guard', 'talk', 'talk_yes', [free, ('glob', TALK_G, '>=', TALK)], setb('freed', 2), 'Speech')
    line('guard', 'talk', 'talk_no', [free], '', 'Speech')
    line('guard', 'boats', 'boats_yes', [free, ('perk', 'boats', 1), ('glob', TALK_G, '>=', BOATS_TALK)], setb('freed', 2), 'Speech')
    line('guard', 'boats', 'boats_no', [free, ('perk', 'boats', 1)], '', 'Speech')
    line('guard', 'threat', 'threat_yes', [free, ('glob', THREAT_G, '>=', THREAT)], setb('freed', 3), 'Speech')
    line('guard', 'threat', 'threat_no', [free], '', 'Speech')
    line('guard', 'fight', 'fight_yes', [free], '%s.StartCombat player' % REF['guard'])
    # 3: the storm crew
    on = qv('storm', 'on', '==', 1)
    line('boss', 'G', 'boss_kin', [on, ('perk', 'kin', 1)], '', None, ['report', 'fight_crew'])
    line('boss', 'G', 'boss_hi', [on], '', None, ['salvage', 'report', 'fight_crew'])
    line('boss', 'salvage', 'salvage_yes', [qv('storm', 'traded', '==', 0), ('items', SCRAP, '>=', 1)], sets('trade'))
    line('boss', 'salvage', 'salvage_done', [])
    line('boss', 'report', 'report_yes', [qv('storm', 'overheard', '==', 1), qv('storm', 'reported', '==', 0), qv('storm', 'looted', '==', 0)],
         '%s\n%s.Disable\nSetStage %s 32' % (sets('reported'), REF['locker'], s))
    line('boss', 'fight_crew', 'fight_crew_yes', [on], '\n'.join('%s.StartCombat player' % REF[k] for k in STORM_CREW))
    line('dealer', 'G', 'dealer_hi', [on], '', None, ['cards'])
    line('dealer', 'cards', 'cards_yes', [on, qv('storm', 'hands', '<', HANDS), ('items', CELL, '>=', STAKE)],
         'player.RemoveItem %s %d\n%s' % (CELL, STAKE, sets('deal')), 'Barter')
    line('dealer', 'cards', 'cards_no', [], '', 'Barter')
    line('deck1', 'G', 'deck1', [on])
    line('deck2', 'G', 'deck2', [on])
    return L


TOPIC_WORDS = {'hand_what': 'hand_what', 'return': 'return', 'haggle': 'haggle', 'lie': 'lie', 'keep': 'keep', 'sell': 'sell',
               'scav_ask': 'scav_ask', 'give': 'give', 'refuse': 'refuse', 'fight_scav': 'fight_scav', 'caught': 'guard_caught',
               'buy': 'buy', 'barter': 'barter', 'talk': 'talk', 'boats': 'boats', 'threat': 'threat', 'fight': 'fight',
               'salvage': 'salvage', 'report': 'report', 'fight_crew': 'fight_crew', 'cards': 'cards'}
TOPIC_QUEST = {'hand_what': 'cells', 'return': 'cells', 'haggle': 'cells', 'lie': 'cells', 'keep': 'cells', 'sell': 'cells',
               'scav_ask': 'cells', 'give': 'cells', 'refuse': 'cells', 'fight_scav': 'cells', 'caught': 'boy', 'buy': 'boy',
               'barter': 'boy', 'talk': 'boy', 'boats': 'boy', 'threat': 'boy', 'fight': 'boy', 'salvage': 'storm', 'report': 'storm',
               'fight_crew': 'storm', 'cards': 'storm'}
WHO_QUEST = {'hand': 'cells', 'crew1': 'cells', 'crew2': 'cells', 'scav': 'cells', 'father': 'boy', 'boy': 'boy', 'boy_home': 'boy',
             'guard': 'boy', 'boss': 'storm', 'dealer': 'storm', 'deck1': 'storm', 'deck2': 'storm'}


def topic_edid(t):
    return 'FOLabPearlTopic' + ''.join(p.capitalize() for p in t.split('_')) if t != 'caught' else 'FOLabPearlBoyCaught'


# ---------- the step ----------

def _cond(fn, op, value, p1=0, p2=0, run=0, orr=False):
    op = '=' if op == '==' else op             # (the game's spelling)
    return {'or': orr, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def _vars(srec):
    out, last = {}, None
    for sub in srec['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            out[sub['value'].lower()] = last
    return out


def ops(gd, pr, P=None):
    """(ops, report, built): records and refs for one Undo; quests, scripts and lines come after (apply)."""
    import piratedeal
    import tes4
    from activity import _new_key
    for q in QUESTS.values():
        if _mod_key(pr, q, 'QUST'):
            raise ValueError('the mod already has %s (Undo first)' % q)
    if not _mod_key(pr, FIRST_PLACE, 'QUST'):
        raise ValueError('"The First Place on the Way" (kuliouquest) first')
    P = P or plan(gd, pr)
    S = P['spots']
    need = ['box', 'panel', 'scav', 'boy', 'guard', 'guard_bed', 'hand', 'crew1', 'crew2', 'locker', 'boy_home', 'cache', 'fire', 'table'] + list(STORM_CREW)
    missing = [k for k in need if k not in S]
    if missing:
        raise ValueError('no spot for: %s' % ', '.join(missing))
    son = _mod_key(pr, SON, 'NPC_')
    if not son:
        raise ValueError('no %s in the mod' % SON)
    world = P['world']
    grid = gd.grid(world if not isinstance(world, str) else gd.from_key(world))
    out, rep = [], {'made': [], 'skipped': list(P['skipped'])}

    def record(rec, k=None):
        k = k or _new_key(pr)
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(recordio.field(rec, 'EDID'))
        return k

    def rec_of(k):
        return next(o['record'] for o in out if o['op'] == 'record' and o['key'] == k)

    def place(base, spot, edid, props=None, persistent=True, scale=1.0):
        k = _new_key(pr)
        if 'cell' in spot:
            ck, (x, y, z, rz) = spot['cell'], spot['p']
        else:
            x, y, z = spot['world']
            rz = spot.get('rz', 0.0)
            ck = gd.key(grid[(int(math.floor(x / 4096.0)), int(math.floor(y / 4096.0)))])
        ref = {'base': base, 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, rz], 's': scale, 'persistent': persistent}
        if edid:
            ref['edid'] = edid
        if props:
            ref['props'] = props
        out.append({'op': 'place', 'cell': ck, 'key': k, 'ref': ref})
        return k
    game = lambda e, t: gd.key(piratedeal._game(gd, e, t))
    traders = _mod_key(pr, 'FOLabPirateTraders', 'FACT') or ''
    # things: the crate, keys, messages, the strongbox, the lift panel, the boy's own record (his shackle), the locker, the cache
    crate = record(_misc(gd, 'FOLabPearlCrate', "Boatyard Toll Crate", 'SpareParts'))
    box_key = record(_key(gd, 'FOLabPearlStrongboxKey', 'Pink Pearl Strongbox Key'))
    shackle_key = record(_key(gd, 'FOLabPearlShackleKey', 'Shackle Key'))
    import newgame
    msgs = {k: record(newgame._message_record('FOLabPearlMsg' + ''.join(p.capitalize() for p in k.split('_')), v)) for k, v in MSG.items()}
    box = record(_container(gd, pr, 'FOLabPearlStrongbox', 'Strongbox', [(crate, 1)]))
    import surffish
    panel = surffish._copy(gd, 'ACTI', 'VControlPanel01R', 'FOLabPearlLiftPanel', 'Jammed Lift Panel')
    panel_key, panel_skey = _new_key(pr), _new_key(pr)
    boy = json.loads(json.dumps(pr.records[son]))
    recordio.set_field(boy, 'EDID', 'FOLabPearlHeldSon', label='Editor ID')
    boy.pop('src', None)
    boy['src'] = ''
    boy_key, shackle_skey = _new_key(pr), _new_key(pr)
    locker = record(_container(gd, pr, 'FOLabPearlStormLocker', "Boat Locker", [(gd.key(piratedeal._game(gd, CELL, 'AMMO')), LOCKER_CELLS)]))
    cache = record(_container(gd, pr, 'FOLabPearlBoatCache', "Boats' Cache", [(gd.key(piratedeal._game(gd, CELL, 'AMMO')), 30),
                                                                           (gd.key(piratedeal._game(gd, STIM, 'ALCH')), 2)]))
    kuli = record(_global(KULI)) if not _mod_key(pr, KULI, 'GLOB') else None
    # people: a face each that no one in the mod wears
    faces = _pick_faces(gd, pr)
    people = {}
    for k in PEOPLE:
        extra = [(box_key, 1)] if k == 'scav' else [(shackle_key, 1)] if k == 'guard' else []
        people[k] = record(_person(gd, pr, k, faces[k], traders if PEOPLE[k][4] == 'traders' else '', extra))
    # the guard's night in the nearest bed (before his post)
    import huanginside as HI
    sleep = record(HI._pack(gd, 'DefaultSleepAlways256', 'FOLabPearlGuardSleep', SLEEP_AT, SLEEP_FOR, S['guard_bed'], 128))
    g = rec_of(people['guard'])
    at = next(i for i, x in enumerate(g['subs']) if x['tag'] == 'PKID')
    g['subs'].insert(at, {'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': sleep})
    # refs: the storm crew's parent first (persistent, off), the crew and their fire and cards under it
    xm = game('XMarker', 'STAT')
    parent = place(xm, {'cell': S['fire']['cell'], 'p': S['fire']['p']}, REF['parent'], {'enabled': False})
    under = {'parent': {'ref': parent, 'opposite': False}, 'enabled': True}
    refs = {}
    for k in PEOPLE:
        props = dict(under) if k in STORM_CREW else {'enabled': False} if k == 'guard' else None
        refs[k] = place(people[k], S[k], REF[k], props)
    place(game('Barrel02Fire256', 'LIGH'), S['fire'], 'FOLabPearlStormFireRef', dict(under))
    tp = S['table']['p']
    place(game('CardTable01', 'STAT'), S['table'], 'FOLabPearlStormTableRef', dict(under))
    place(game('PokerChip01', 'MSTT'), {'cell': S['table']['cell'], 'p': (tp[0] + 12, tp[1] - 8, tp[2] + 74, tp[3])}, None, dict(under), persistent=False)
    place(box, S['box'], REF['box'], {'lock': {'level': BOX_LOCK, 'key': box_key, 'leveled': False}})
    place(panel_key, S['panel'], REF['panel'], persistent=False)
    place(boy_key, S['boy'], REF['boy'], {'enabled': False})
    place(boy_key, S['boy_home'], REF['boy_home'], {'enabled': False})
    place(locker, S['locker'], REF['locker'], {'enabled': False, 'lock': {'level': LOCKER, 'key': '', 'leveled': False}})
    place(cache, S['cache'], REF['cache'], {'enabled': False})
    actors = set(people.values()) | {boy_key}
    ext = {o['key']: {'type': 'ACHR' if o['ref']['base'] in actors else 'REFR', 'flags': tes4.PERSISTENT,
                      'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': o['ref']['edid']}]}
           for o in out if o['op'] == 'place' and o['ref'].get('edid')}
    B = type('B', (), {})()
    B.people, B.ext, B.refs, B.msgs = people, ext, refs, msgs
    B.panel, B.panel_key, B.panel_skey, B.boy, B.boy_key, B.shackle_skey = panel, panel_key, panel_skey, boy, boy_key, shackle_skey
    B.keys = {w: _new_key(pr) for w in QUESTS}
    B.skeys = {w: _new_key(pr) for w in QUESTS}
    B.kuli = kuli
    return out, rep, B


def _parse_conds(gd, pr, B, V, conds, new=None):
    """CTDA conditions from lines_spec's."""
    import missouriguns
    av = lambda e: next(f for f, (i, r) in gd.forms.items() if r.tag == 'AVIF' and gd.edid(f) == e)
    AV = {'Speech': 43, 'Barter': 32, 'Repair': 39, 'Sneak': 42, 'Lockpick': 36}
    out = []
    for c in conds:
        kind = c[0]
        if kind == 'q':
            _k, w, var, op, v = c
            out.append(_cond(79, op, v, B.keys[w], V[w][var]))
        elif kind == 'stage':
            out.append(_cond(58, c[2], c[3], B.keys[c[1]]))
        elif kind == 'skill':
            out.append(_cond(14, c[2], c[3], AV[c[1]], 0, 1))
        elif kind == 'glob':
            out.append(_cond(74, c[2], c[3], (new or {}).get(c[1]) or _mod_key(pr, c[1], 'GLOB')))
        elif kind == 'items':
            it = (new or {}).get(c[1]) or _mod_key(pr, c[1]) or gd.key(next(f for f, (i, r) in gd.forms.items() if gd.edid(f) == c[1] and r.tag in ('AMMO', 'MISC', 'ALCH', 'KEYM')))
            out.append(_cond(47, c[2], c[3], it, 0, 1))
        elif kind == 'perk':
            out.append(_cond(449, '==', c[2], _mod_key(pr, TRAITS[c[1]], 'PERK'), 0, 1))
    del missouriguns, av
    return out


def _who_key(pr, B, who):
    if who in B.people:
        return B.people[who]
    if who in ('boy', 'boy_home'):
        return B.boy_key
    if who == 'father':
        return _mod_key(pr, 'FOLabKuliFather', 'NPC_')
    raise KeyError(who)


def _forms(gd, pr, ext, extra=None):
    """ModForms with this step's records and named refs laid over (keys as they will be once applied)."""
    import api_quests as aq
    extra = dict(extra or {})

    class Forms(aq.ModForms):
        def script_vars(self, form):
            scri = recordio.field(form.rec, 'SCRI')
            if scri in extra:
                got, last = {}, None
                for s in extra[scri]['subs']:
                    if s['tag'] == 'SLSD':
                        last = s['fields']
                    elif s['tag'] == 'SCVR' and last:
                        got[s['value'].lower()] = (next(x['value'] for x in last if x.get('name') == 'Index'),
                                                   bool(next(x['value'] for x in last if x.get('name') == 'Flags')))
                        last = None
                return got
            return aq.ModForms.script_vars(self, form)
    f = Forms(gd, pr)
    for k, rec in list(extra.items()) + list(ext.items()):
        e = recordio.field(rec, 'EDID')
        if e and k.startswith('+'):
            f.own[e.lower()] = (k, rec)
    return f


def apply(pr, gd, P=None):
    import api_quests as aq
    import api_scripts
    import questrec as qr
    from activity import _new_key
    o, rep, B = ops(gd, pr, P)
    targets = {'hand': B.refs.get('hand'), 'boy': next((k for k, v in B.ext.items() if v['subs'][0]['value'] == REF['boy']), None),
               'cache': next((k for k, v in B.ext.items() if v['subs'][0]['value'] == REF['cache']), None)}
    from castawayquest import _ref_by_edid
    targets['father'] = _ref_by_edid(pr, FATHER)[1]
    have = {'rep': bool(_mod_key(pr, REP_PIRATES, 'REPU')), 'names': bool(_mod_key(pr, NAME_Q, 'QUST'))}
    plains = quests_plain(B.keys, B.skeys, have, targets)
    stubs = {w: qr.quest_record(dict(plains[w], stages=[], objectives=[])) for w in QUESTS}
    known = dict(B.ext)
    known.update({B.keys[w]: stubs[w] for w in QUESTS})
    known.update({x['key']: x['record'] for x in o if x['op'] == 'record'})
    known[B.boy_key] = B.boy
    known[B.panel_key] = B.panel
    # the topics first: the guard's "caught" is started by the boy quest's script
    topics, trecs = {}, []
    for t in TOPIC_WORDS:
        k = _new_key(pr)
        rec = qr.topic_record({'edid': topic_edid(t), 'name': W[TOPIC_WORDS[t]], 'priority': 50.0, 'kind': 0,
                               'quests': [{'quest': B.keys[TOPIC_QUEST[t]], 'links': []}]})
        topics[t] = k
        trecs.append((k, rec))
        known[k] = rec
    sc = api_scripts.scripts()
    sources = {'cells': cells_script(), 'boy': boy_script(), 'storm': storm_script()}
    srecs = {}
    for w, src in sources.items():
        c = sc.compile(src, B.skeys[w], 'quest', known)
        if not hasattr(c, 'subrecords'):
            raise ValueError('%s: %s' % (src.split('\n')[0], c))
        srecs[w] = sc._record_of(c, src.split('\n')[0][4:])
        known[B.skeys[w]] = srecs[w]
    obj = {}
    for name, src, skey in (('FOLabPearlLiftPanelScript', panel_script(), B.panel_skey), ('FOLabPearlShackleScript', shackle_script(), B.shackle_skey)):
        c = sc.compile(src, skey, 'object', known)
        if not hasattr(c, 'subrecords'):
            raise ValueError('%s: %s' % (name, c))
        obj[skey] = sc._record_of(c, name)
    _set_script(B.panel, B.panel_skey)
    _set_script(B.boy, B.shackle_skey)
    o += [{'op': 'record', 'key': B.skeys[w], 'record': srecs[w]} for w in QUESTS]
    o += [{'op': 'record', 'key': B.keys[w], 'record': stubs[w]} for w in QUESTS]
    o += [{'op': 'record', 'key': k, 'record': r} for k, r in obj.items()]
    o += [{'op': 'record', 'key': B.panel_key, 'record': B.panel}, {'op': 'record', 'key': B.boy_key, 'record': B.boy}]
    o += [{'op': 'record', 'key': k, 'record': r} for k, r in trecs]
    rep['made'] += list(QUESTS.values()) + [s.split('\n')[0][4:] for s in sources.values()] + ['FOLabPearlLiftPanelScript', 'FOLabPearlShackleScript',
                                                                                              'FOLabPearlLiftPanel', 'FOLabPearlHeldSon']
    rep['made'] += [recordio.field(r, 'EDID') for _k, r in trecs]
    # the lines
    V = {w: _vars(srecs[w]) for w in QUESTS}
    G = qr.GREETING
    av_key = lambda e: gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'AVIF' and gd.edid(f) == e))
    SKILL = {'Speech': av_key('AVSpeech'), 'Barter': av_key('AVBarter')}
    new = {recordio.field(x['record'], 'EDID'): x['key'] for x in o if x['op'] == 'record'}
    lines = []
    for who, topic, words, conds, end, skill, choices in lines_spec():
        tp = G if topic == 'G' else topics[topic]
        quest = B.keys[TOPIC_QUEST[topic]] if topic != 'G' else B.keys[WHO_QUEST[who]]
        l = aq.new_line_plain(gd, pr, tp, quest, _who_key(pr, B, who), W[words], conditions=_parse_conds(gd, pr, B, V, conds, new))
        if skill:
            l['skill'] = SKILL[skill]
        if end:
            l['end'] = {'source': end, 'parts': None}
        l['choices'] = [topics[t] for t in choices]
        lines.append(l)
    forms = _forms(gd, pr, B.ext, {x['key']: x['record'] for x in o if x['op'] == 'record'})              # (ModForms knows records only: this step's stage and line scripts name its refs)
    for w in QUESTS:                            # (everything compiled before anything is applied: a failure leaves the mod as it was)
        full = json.loads(json.dumps(plains[w]))
        errors = aq.compile_quest(full, forms)
        if errors:
            raise ValueError('%s: %s' % (QUESTS[w], errors))
        plains[w] = full
    compiled = []
    for l in lines:
        l.setdefault('begin', None)
        l.setdefault('end', None)
        errors = aq.compile_line(l, forms)
        if errors:
            raise ValueError('%s, line %s: %s (%s)' % (errors[0]['where'], errors[0]['line'], errors[0]['message'], l['responses'][0]['text'][:40]))
        compiled.append(qr.info_record(l))
    pr.apply(LABEL, o)
    pr.apply(LABEL, [{'op': 'record', 'key': B.keys[w], 'record': qr.quest_record(plains[w])} for w in QUESTS] +
             [{'op': 'record_new', 'record': r} for r in compiled], merge=True)
    rep.update({'lines': len(lines), 'people': len(B.people), 'named': sorted(v['subs'][0]['value'] for v in B.ext.values()),
                'faces': {k: recordio.field(pr.records[v], 'TPLT') or pr.records[v].get('copied_from') for k, v in B.people.items()}})
    return rep


# ---------- the run-through: every way through, on the quests' own scripts and lines ----------

class _Return(Exception):
    pass


class Game:
    """What the quests' scripts and lines see. The player's skills, items and traits are set by the route."""

    def __init__(self, skills=None, items=None, perks=(), globs=None, first_place=FIRST_DONE):
        self.skills = dict({'Speech': 20, 'Barter': 20, 'Repair': 20, 'Sneak': 20, 'Lockpick': 20, 'Luck': 5}, **(skills or {}))
        self.items = dict(items or {})
        self.perks = set(perks)
        self.globs = dict({SHELTER: 0, KULI: 0}, **(globs or {}))
        self.globs.setdefault(TALK_G, self.skills['Speech'] + (15 if 'soft' in self.perks else 0))
        self.globs.setdefault(THREAT_G, 100 if 'dread' in self.perks else 0 if 'soft' in self.perks else self.skills['Speech'])
        self.stages = {QUESTS[w]: set() for w in QUESTS}
        self.stages[FIRST_PLACE] = {first_place} if first_place else set()
        self.on, self.off, self.dead, self.combat, self.talks = set(), set(), set(), [], []
        self.locked = {REF['box'].lower(): BOX_LOCK}
        self.near, self.sneaking, self.asleep, self.days, self.roll, self.in_lobby = None, False, False, 0.0, 0, False
        self.containers = {REF['box'].lower(): {'FOLabPearlCrate': 1}, REF['locker'].lower(): {}}
        self.messages, self.done, self.rep, self.names = [], set(), [], {'pirates': 0}
        self.activated = 0

    def call(self, name, args, ref):
        n, ref = name.lower(), (ref or '').lower()
        if n == 'return':
            raise _Return()
        if n in self.globs or name in self.globs:
            return self.globs.get(name, self.globs.get(n, 0))
        if n == 'gamedayspassed':
            return self.days
        if n == 'getrandompercent':
            return self.roll
        if n == 'getitemcount':
            if ref == 'player':
                return self.items.get(args[0], 0)
            return self.containers.get(ref, {}).get(args[0], 0)
        if n == 'additem':
            box = self.items if ref == 'player' else self.containers.setdefault(ref, {})
            box[args[0]] = box.get(args[0], 0) + int(float(args[1]))
            return 0
        if n == 'removeitem':
            assert self.items.get(args[0], 0) >= int(float(args[1])), 'removing %s %s the player hasn\'t' % (args[1], args[0])
            self.items[args[0]] -= int(float(args[1]))
            return 0
        if n == 'removeallitems':
            self.containers[ref] = {}
            return 0
        if n == 'getactorvalue':
            return self.skills.get(args[0], 0)
        if n == 'hasperk':
            return 1 if any(TRAITS[t] == args[0] for t in self.perks) else 0
        if n == 'issneaking':
            return 1 if self.sneaking else 0
        if n == 'getsleeping':
            return 3 if self.asleep and ref == REF['guard'].lower() else 0
        if n == 'getdistance':
            return 100.0 if self.near and self.near.lower() == args[0].lower() else 5000.0
        if n == 'getincell':
            return 1 if self.in_lobby and args[0] == FLOORS['lobby'] else 0
        if n == 'getdead':
            return 1 if ref in self.dead else 0
        if n == 'resurrect':
            self.dead.discard(ref)
            return 0
        if n == 'enable':
            self.on.add(ref)
            self.off.discard(ref)
            return 0
        if n == 'disable':
            self.off.add(ref)
            self.on.discard(ref)
            return 0
        if n == 'lock':
            self.locked[ref] = int(float(args[0]))
            return 0
        if n == 'unlock':
            self.locked.pop(ref, None)
            return 0
        if n == 'startcombat':
            self.combat.append(ref)
            return 0
        if n == 'startconversation':
            self.talks.append((ref, args[1]))
            return 0
        if n == 'getstage':
            return max(self.stages.get(args[0], {0}) or {0})
        if n == 'setstage':
            self.stages.setdefault(args[0], set()).add(int(float(args[1])))
            return 0
        if n in ('setobjectivedisplayed', 'setobjectivecompleted'):
            return 0
        if n == 'completequest':
            self.done.add(args[0])
            return 0
        if n == 'addreputation':
            self.rep.append((args[0], int(float(args[1])), int(float(args[2]))))
            return 0
        if n == 'showmessage':
            self.messages.append(args[0])
            return 0
        if n == 'activate':
            self.activated += 1
            return 0
        raise ValueError("the run-through doesn't know %s" % name)


def _sim_text(src, own):
    """A script's text for stormsched: a quest's own variables bare, other quests' as 'q__var', globals as they are."""
    def sub(m):
        q, v = m.group(1), m.group(2)
        if q == own:
            return v
        if q in QUESTS.values() or q == NAME_Q:
            return '%s__%s' % (q, v)
        return m.group(0)
    return re.sub(r'\b(FOLab\w+)\.(\w+)\b', sub, src)


class Play:
    """The three quests' scripts and lines run together on a Game."""

    def __init__(self, game):
        import stormsched
        for k, v in {'getdistance': 1, 'getitemcount': 1, 'additem': 2, 'removeitem': 2, 'setstage': 2, 'setobjectivedisplayed': 3,
                     'setobjectivecompleted': 3, 'startconversation': 2, 'completequest': 1, 'getactorvalue': 1, 'hasperk': 1, 'getstage': 1,
                     'addreputation': 3, 'startcombat': 1, 'getincell': 1, 'resurrect': 1, 'lock': 1, 'showmessage': 1}.items():
            stormsched._ARGS[k] = v
        self.S = stormsched
        self.g = game
        self.q = {w: stormsched.Script(_sim_text({'cells': cells_script(), 'boy': boy_script(), 'storm': storm_script()}[w], QUESTS[w]))
                  for w in QUESTS}
        self.stage_src = {}
        for w, plain in quests_plain({w: '' for w in QUESTS}, {w: '' for w in QUESTS}, {'rep': True, 'names': True}, {}).items():
            for s in plain['stages']:
                self.stage_src[(QUESTS[w], s['index'])] = s['entries'][0]['script']['source']
        self.ran = set()
        self.lines = lines_spec()

    def _run(self, src, own):
        s = self.S.Script('begin x\n' + _sim_text(src, QUESTS[own]) + '\nend')
        s.vars = self.q[own].vars
        for w in QUESTS:                       # (another quest's variable: read and written in its own place)
            for v, val in list(self.q[w].vars.items()):
                s.vars.setdefault('%s__%s' % (QUESTS[w].lower(), v), val)
        for v, val in self.g.names.items():
            s.vars.setdefault('%s__%s' % (NAME_Q.lower(), v), val)
        try:
            s.frame(self.g)
        except _Return:
            pass
        for w in QUESTS:
            for v in list(self.q[w].vars):
                k = '%s__%s' % (QUESTS[w].lower(), v)
                if k in s.vars and w != own:
                    self.q[w].vars[v] = s.vars.pop(k)
        for k in [k for k in s.vars if '__' in k]:
            if k.startswith(NAME_Q.lower()):
                self.g.names[k.split('__')[1]] = s.vars.pop(k)

    def frame(self, n=1):
        for _ in range(n):
            for w in QUESTS:
                try:
                    self.q[w].frame(self.g)
                except _Return:
                    pass
            for (q, i) in sorted((q, i) for q, st in self.g.stages.items() for i in st):
                if (q, i) not in self.ran and (q, i) in self.stage_src:
                    self.ran.add((q, i))
                    w = next(w for w, e in QUESTS.items() if e == q)
                    self._run(self.stage_src[(q, i)], w)

    def ok(self, conds):
        g = self.g
        cmp = lambda a, op, b: {'==': a == b, '!=': a != b, '>=': a >= b, '<=': a <= b, '>': a > b, '<': a < b}[op]
        for c in conds:
            if c[0] == 'q' and not cmp(self.q[c[1]].vars.get(c[2], 0), c[3], c[4]):
                return False
            if c[0] == 'skill' and not cmp(g.skills.get(c[1], 0), c[2], c[3]):
                return False
            if c[0] == 'glob' and not cmp(g.globs.get(c[1], 0), c[2], c[3]):
                return False
            if c[0] == 'items' and not cmp(g.items.get(c[1], 0), c[2], c[3]):
                return False
            if c[0] == 'perk' and (c[1] in g.perks) != bool(c[2]):
                return False
        return True

    def say(self, who, topic='G', after=None):
        """Talk to `who` about `topic`: the topic must be offered by the line before (the greeting, or `after`); the first line
        whose conditions pass is said and its end script run. Returns the words key said."""
        if topic != 'G':
            before = after or self.say_line(who, 'G')
            assert before and topic in before[6], '%s is not offered by %s' % (topic, before and before[2])
        line = self.say_line(who, topic)
        assert line, '%s has nothing to say on %s' % (who, topic)
        if line[4]:
            self._run(line[4], TOPIC_QUEST.get(topic, WHO_QUEST[who]) if topic != 'G' else WHO_QUEST[who])
        self.frame(2)
        return line

    def say_line(self, who, topic):
        return next((l for l in self.lines if l[0] == who and l[1] == topic and self.ok(l[3])), None)

    def activate(self, src, own):
        self._run(src.split('Begin OnActivate player', 1)[1].rsplit('End', 1)[0], own)
        self.frame(2)

    def take_from(self, box):
        """Open a container (unlocked) and take everything."""
        box = box.lower()
        assert box not in self.g.locked or self.g.skills['Lockpick'] >= self.g.locked[box] or \
            (box == REF['box'].lower() and self.g.items.get('FOLabPearlStrongboxKey')), 'the %s is locked' % box
        for it, n in self.g.containers.get(box, {}).items():
            self.g.items[it] = self.g.items.get(it, 0) + n
        self.g.containers[box] = {}
        self.frame(2)

    def kill(self, who, loot=()):
        self.g.dead.add(REF[who].lower())
        for it in loot:
            self.g.items[it] = self.g.items.get(it, 0) + 1
        self.frame(2)


def routes():
    """{name: (what it checks, ok)} for every way through the three quests."""
    out = {}

    def run(name, what, fn, **game):
        p = Play(Game(**game))
        p.frame(3)
        try:
            ok = fn(p)
        except (AssertionError, ValueError, KeyError, TypeError) as e:
            ok = False
            what += ' [%s: %s]' % (type(e).__name__, e)
        out[name] = (what, bool(ok))
    C, B, S = QUESTS['cells'], QUESTS['boy'], QUESTS['storm']
    st = lambda p, q: p.g.stages[q]

    # 1. the boatyard's cells: three ways to the crate, six ends
    def start(p, how='lockpick'):
        p.say('hand', 'hand_what')
        assert 10 in st(p, C)
        if how == 'lockpick':
            p.take_from(REF['box'])
        elif how == 'repair':
            p.activate(panel_script(), 'cells')
            assert REF['box'].lower() not in p.g.locked, 'the panel did not open the box'
            p.take_from(REF['box'])
        elif how == 'key':
            p.say('scav', 'fight_scav')
            p.kill('scav', ('FOLabPearlStrongboxKey',))
            p.take_from(REF['box'])
        assert 20 in st(p, C), 'the crate not found'

    def returned(p):
        start(p)
        p.say('hand', 'return')
        return 50 in st(p, C) and p.g.items.get(CELL) == PAY and C in p.g.done
    run('cells: lockpick, return', 'Lockpick 25 on the strongbox, the crate back: 25 cells, fame', returned, skills={'Lockpick': 25})

    def repair(p):
        start(p, 'repair')
        p.say('hand', 'return')
        return 50 in st(p, C)
    run('cells: repair the lift panel, return', 'Repair 25 on the jammed lift panel opens the box', repair, skills={'Repair': 25})

    def panel_fail(p):
        p.say('hand', 'hand_what')
        p.activate(panel_script(), 'cells')
        return REF['box'].lower() in p.g.locked and 'FOLabPearlMsgPanelJammed' in p.g.messages
    run('cells: the panel too hard', 'Repair 24: the panel stays jammed', panel_fail, skills={'Repair': 24})

    def key(p):
        start(p, 'key')
        p.say('hand', 'return')
        return 50 in st(p, C) and REF['scav'].lower() in p.g.combat
    run('cells: fight the scavenger for his key', 'the scavenger fought, his key opens the box', key)

    def haggle(p):
        start(p)
        p.say('hand', 'haggle')
        return p.g.items.get(CELL) == 2 * PAY and 50 in st(p, C)
    run('cells: Speech 35 doubles the pay', 'Speech 35: 50 cells', haggle, skills={'Lockpick': 25, 'Speech': 35})
    run('cells: Soft Touch eases the haggle', 'Speech 20 with Soft Touch (35 on the talk global): 50 cells', haggle, skills={'Lockpick': 25},
        perks=('soft',))
    run('cells: Dread Name doubles it', 'Dread Name, Speech 10: 50 cells', haggle, skills={'Lockpick': 25, 'Speech': 10}, perks=('dread',))

    def haggle_fail(p):
        start(p)
        p.say('hand', 'haggle')
        assert 50 not in st(p, C)
        line = p.say('hand', 'return', after=p.say_line('hand', 'haggle'))
        return line[2] == 'return_yes' and p.g.items.get(CELL) == PAY
    run('cells: haggle fails, then return', 'Speech 34: the haggle fails, the return still pays 25', haggle_fail, skills={'Lockpick': 25, 'Speech': 34})

    def boats(p):
        start(p)
        p.say('hand', 'return')
        return p.g.items.get(CELL) == PAY + BOAT_BONUS
    run('cells: Raised on the Boats', 'Raised on the Boats: 35 cells', boats, skills={'Lockpick': 25}, perks=('boats',))

    def lie(p):
        start(p)
        p.say('hand', 'lie')
        return 52 in st(p, C) and p.g.items.get(CELL) == CRATE and not p.g.items.get('FOLabPearlCrate') and not p.g.combat
    run('cells: Speech 50 lie, keep it', 'Speech 50: "burnt", 40 cells kept, no fight', lie, skills={'Lockpick': 25, 'Speech': 50})

    def lie_kin(p):
        start(p)
        line = p.say('hand', 'lie')
        return line[2] == 'lie_kin' and 52 not in st(p, C)
    run("cells: a Captain's Kin isn't believed", "Captain's Kin, Speech 60: the lie fails", lie_kin, skills={'Lockpick': 25, 'Speech': 60}, perks=('kin',))

    def keep(p):
        start(p)
        p.say('hand', 'keep')
        return 54 in st(p, C) and p.g.items.get(CELL) == CRATE and {REF['crew1'].lower(), REF['crew2'].lower()} <= set(p.g.combat) and \
            (REP_PIRATES, 0, 1) in p.g.rep
    run('cells: keep it openly', 'kept to his face: 40 cells, the crew fight, infamy', keep, skills={'Lockpick': 25})

    def give(p):
        start(p)
        p.say('scav')
        p.say('scav', 'give')
        return 56 in st(p, C) and p.q['cells'].vars.get('done') == 1 and not p.g.items.get(CELL)
    run('cells: give it to the scavenger', 'Kuliouou good, no pay', give, skills={'Lockpick': 25})

    def sell(p):
        start(p)
        p.say('scav')
        p.say('hand', 'sell')
        p.say('hand', 'return')
        p.g.near = None
        p.frame(2)
        return 60 in st(p, C) and 50 in st(p, C) and p.g.items.get(CELL) == SELL_OUT + PAY and REF['scav'].lower() in p.g.off
    run('cells: sell the scavenger out', 'the name for 15 cells and fame, then the crate back; the scavenger taken away', sell, skills={'Lockpick': 25})

    def refuse(p):
        start(p)
        p.say('scav', 'refuse')
        p.say('hand', 'return')
        return 50 in st(p, C)
    run('cells: refuse the scavenger', 'refused, then returned', refuse, skills={'Lockpick': 25})

    # 2. the boy in the Pearl
    def started(p):
        assert 10 in st(p, B), 'the quest did not start after The First Place on the Way'
        assert REF['boy'].lower() in p.g.on and REF['guard'].lower() in p.g.on

    def home(p, stage, paid):
        assert stage in st(p, B), 'freed stage %d not set (%s)' % (stage, sorted(st(p, B)))
        assert REF['boy'].lower() in p.g.off and REF['boy_home'].lower() in p.g.on
        p.say('father')
        p.g.near = REF['cache']
        p.frame(2)
        inf = (REP_PIRATES, 0, 1) in p.g.rep
        return 100 in st(p, B) and 110 in st(p, B) and B in p.g.done and p.g.items.get(MEAL) == 2 and REF['cache'].lower() in p.g.on and inf != paid

    def buy(p):
        started(p)
        p.say('guard', 'buy')
        return home(p, 20, True) and p.g.items.get(CELL) == 0
    run('boy: buy him back', '60 cells; no infamy', buy, items={CELL: PRICE})

    def buy_short(p):
        started(p)
        line = p.say('guard', 'buy')
        return line[2] == 'buy_no' and not p.q['boy'].vars.get('freed')
    run('boy: not enough cells', '59 cells: no sale', buy_short, items={CELL: PRICE - 1})

    def barter(p):
        started(p)
        p.say('guard', 'barter')
        return home(p, 20, True) and p.g.items.get(CELL) == PRICE // 2
    run('boy: Barter 40 halves it', 'Barter 40: 30 cells', barter, skills={'Barter': 40}, items={CELL: PRICE})

    def kin_buy(p):
        started(p)
        line = p.say('guard', 'buy')
        return line[2] == 'buy_kin_yes' and home(p, 20, True) and p.g.items.get(CELL) == 0
    run("boy: a Captain's Kin pays double", "Captain's Kin: 120 cells", kin_buy, items={CELL: 2 * PRICE}, perks=('kin',))

    def talk(p):
        started(p)
        p.say('guard', 'talk')
        return home(p, 22, False)
    run('boy: Speech 45', 'Speech 45: let go; infamy', talk, skills={'Speech': 45})
    run('boy: Soft Touch talks him round', 'Speech 30 with Soft Touch (45 on the talk global)', talk, skills={'Speech': 30}, perks=('soft',))

    def boats_talk(p):
        started(p)
        p.say('guard', 'boats')
        return home(p, 22, False)
    run('boy: Raised on the Boats', 'Raised on the Boats, Speech 25', boats_talk, skills={'Speech': 25}, perks=('boats',))

    def no_boats(p):
        started(p)
        return 'boats' in p.say_line('guard', 'G')[6] and p.say_line('guard', 'boats') is None
    run('boy: "same decks" only for the boat-born', 'no line in the topic without Raised on the Boats, so the game hides it', no_boats,
        skills={'Speech': 100})

    def threat(p):
        started(p)
        p.say('guard', 'threat')
        return home(p, 24, False)
    run('boy: Intimidate 55', 'Speech 55: scared off', threat, skills={'Speech': 55})
    run('boy: Dread Name always wins', 'Dread Name, Speech 5', threat, skills={'Speech': 5}, perks=('dread',))

    def soft_threat(p):
        started(p)
        line = p.say('guard', 'threat')
        return line[2] == 'threat_no' and not p.q['boy'].vars.get('freed')
    run('boy: Soft Touch never intimidates', 'Soft Touch, Speech 100: the threat fails', soft_threat, skills={'Speech': 100}, perks=('soft',))

    def sneak(p):
        started(p)
        p.g.asleep, p.g.sneaking, p.g.near = True, True, REF['guard']
        p.frame(3)
        assert not p.g.talks, 'he woke'
        p.g.near = REF['boy']
        p.activate(shackle_script(), 'boy')
        p.g.asleep, p.g.sneaking = False, False
        return home(p, 26, False)
    run('boy: sneak past him asleep, pick the shackle', 'Sneak 35 while he sleeps, Lockpick 50', sneak, skills={'Sneak': 35, 'Lockpick': 50})

    def woke(p):
        started(p)
        p.g.asleep, p.g.sneaking, p.g.near = True, True, REF['guard']
        p.frame(3)
        assert p.g.talks and p.g.talks[0][1] == 'FOLabPearlBoyCaught', 'he did not wake'
        p.g.asleep = False
        caught = p.say_line('guard', 'caught')
        p.say('guard', 'talk', after=caught)
        return home(p, 22, False)
    run('boy: Sneak 34 wakes him, then talk', 'he wakes and has words; Speech 45 then', woke, skills={'Sneak': 34, 'Speech': 45})

    def watched(p):
        started(p)
        p.g.near = REF['guard']
        p.activate(shackle_script(), 'boy')
        return 'FOLabPearlMsgShackleWatched' in p.g.messages and not p.q['boy'].vars.get('freed')
    run('boy: the shackle under his eye', 'awake and near: he watches, nothing happens', watched, skills={'Lockpick': 100})

    def fight(p):
        started(p)
        p.say('guard', 'fight')
        p.kill('guard', ('FOLabPearlShackleKey',))
        p.activate(shackle_script(), 'boy')
        return REF['guard'].lower() in p.g.combat and home(p, 28, False)
    run('boy: fight, the key', 'the guard fought, his key opens the shackle', fight)

    def leave(p):
        started(p)
        p.g.days = SAIL_DAYS + 0.1
        p.frame(3)
        return 90 in st(p, B) and B in p.g.done and REF['boy'].lower() in p.g.off and p.say_line('father', 'G')[2] == 'father_sailed'
    run('boy: leave him, the boat sails', 'after 5 days the boat sails', leave)

    def early(p):
        return 10 not in st(p, B) and REF['boy'].lower() not in p.g.on
    run('boy: not before The First Place on the Way', 'nothing before its stage 100', early, first_place=20)

    # 3. when the boats run in
    def storm(p):
        p.g.globs[SHELTER] = 1
        p.frame(2)
        assert REF['parent'].lower() in p.g.on and 10 in st(p, S), 'the crew did not come in'
        return True

    def salvage(p):
        storm(p)
        p.say('boss', 'salvage')
        p.frame(2)
        assert p.g.items.get(CELL) == SALVAGE * SALVAGE_MOST and p.g.items.get(SCRAP) == 2
        line = p.say('boss', 'salvage')
        return line[2] == 'salvage_done'
    run('storm: trade salvage', '12 scrap: 10 taken for 30 cells, once a storm', salvage, items={SCRAP: 12})

    def kin_trade(p):
        storm(p)
        return 'salvage' not in p.say_line('boss', 'G')[6]
    run("storm: a Captain's Kin gets no trade", 'no salvage topic', kin_trade, items={SCRAP: 5}, perks=('kin',))

    def cards(p, win):
        storm(p)
        p.g.roll = 0 if win else 99
        p.say('dealer', 'cards')
        return p.g.items.get(CELL) == (STAKE * 3 if win else STAKE) and ('FOLabPearlMsgWon' if win else 'FOLabPearlMsgLost') in p.g.messages
    run('storm: cards, a win', 'stake 10, win 20 back', lambda p: cards(p, True), items={CELL: 2 * STAKE})
    run('storm: cards, a loss', 'stake 10 lost', lambda p: cards(p, False), items={CELL: 2 * STAKE})

    def hands(p):
        storm(p)
        p.g.roll = 99
        for _ in range(HANDS):
            p.say('dealer', 'cards')
        return p.say('dealer', 'cards')[2] == 'cards_no' and p.g.items.get(CELL) == 100 - HANDS * STAKE
    run('storm: three hands a storm', 'the fourth refused', hands, items={CELL: 100})

    def overhear(p, then):
        storm(p)
        p.g.sneaking, p.g.near = True, REF['boss']
        p.frame(2)
        assert 20 in st(p, S) and REF['locker'].lower() in p.g.on, 'nothing overheard'
        p.g.sneaking = False
        if then == 'loot':
            p.take_from(REF['locker'])
            return 30 in st(p, S) and p.g.items.get(CELL) == LOCKER_CELLS
        p.say('boss', 'report')
        return 32 in st(p, S) and (REP_PIRATES, 1, 1) in p.g.rep and REF['locker'].lower() in p.g.off
    run('storm: overhear, loot the locker', 'Sneak 30 by the boss, Lockpick 25 on the locker', lambda p: overhear(p, 'loot'), skills={'Sneak': 30, 'Lockpick': 25})
    run('storm: overhear, report it', 'Sneak 30, then tell them: fame', lambda p: overhear(p, 'report'), skills={'Sneak': 30})

    def deaf(p):
        storm(p)
        p.g.sneaking, p.g.near = True, REF['boss']
        p.frame(2)
        return 20 not in st(p, S)
    run('storm: Sneak 29 hears nothing', 'nothing overheard', deaf, skills={'Sneak': 29})

    def fight_crew(p):
        storm(p)
        p.say('boss', 'fight_crew')
        for k in STORM_CREW:
            p.kill(k)
        ok = 40 in st(p, S) and p.g.items.get(KALA) == BOUNTY
        # the storm ends; the next storm's crew comes back, everything once a storm again
        p.g.globs[SHELTER] = 0
        p.frame(2)
        assert REF['parent'].lower() in p.g.off
        p.g.globs[SHELTER] = 1
        p.frame(2)
        return ok and not p.g.dead and p.q['storm'].vars['storms'] == 2 and p.q['storm'].vars['fought'] == 0
    run('storm: fight for the bounty, the next storm', '40 kala; the crew back with the next storm', fight_crew)

    def stays(p):
        storm(p)
        p.g.in_lobby = True
        p.g.globs[SHELTER] = 0
        p.frame(2)
        assert REF['parent'].lower() in p.g.on, 'gone while you stood there'
        p.g.in_lobby = False
        p.frame(2)
        return REF['parent'].lower() in p.g.off
    run('storm: the crew leaves when you do', 'not while you are in the lobby', stays)
    return out


if __name__ == '__main__':
    bad = 0
    for name, (what, ok) in routes().items():
        print(('PASS ' if ok else 'FAIL ') + name + ' (' + what + ')')
        bad += not ok
    print('%d ways through, %d failing' % (len(routes()), bad))
