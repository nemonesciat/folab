"""K1: the Missouri's guns, fixed (docs/waikiki-speech-science.md K1; the user, 25 Nov 2026: "let's go with all of those. you can
gain the captain's trust with high speech and respect in waikiki, maybe, or the captain's guard is its own faction too
perhaps ... the idea is his power is imagined now but it could become real ... no more what if. let's just go for it").
The design: k1-missouri-guns.md in the shared notes. After missouriterms (the Fire Control terminal and
FOLabCaptainsBluff), repstanding, piratedeal (the REPU), secretcaches (Alewa Fort), money (kala), shipcrew (the Flotilla's
Quartermaster and store).

- **The Captain's Guard:** FOLabCaptainsGuardFaction, its reputation FOLabRepGuard (fame and infamy), a fourth score
  `guard` in Your Name on the Water with its own line (repstanding's script compiled again with it: `standing_ops`).
  Aboard [names proposed]: Captain Kalani Hale (the Pilot House), Lieutenant Mahoe (the 2nd Deck), Gunner's Mate Ikaika
  (Turret Two), Chief Kekoa (the Engine Room), four Guardsmen (two at the gangway on deck, two on the 2nd Deck).
- **The Kalihi lord** [proposed] at Alewa Fort, with his Wall Watch terminal already there.
- **The quest FOLabMissouriGuns, "Sixteen Inches" [proposed]:**
  - 10 the truth known: the Fire Control terminal (FOLabCaptainsBluff.knows), Repair `KNOW_REPAIR` at Turret Two's breech,
    Ikaika (Speech `IKAIKA_SPEECH` or the Guard a friend), the Kalihi lord (Barter `LORD_BARTER`, `LORD_KALA` kala, or the
    court's favour);
  - 20 the Captain's trust: Speech `TRUST_SPEECH` with the court's standing, service to the Guard (the searchlight,
    Repair `LIGHT_REPAIR`; the 5-inch mount, Repair `MOUNT_REPAIR`) and the Guard a friend, or leverage (Speech
    `LEVER_SPEECH`, else a fight);
  - 30 what it would take: Repair `PARTS_REPAIR` at the breech and Science (the Turret Two Rangekeeper, locked hard);
  - 40 the parts: the breech block from the lord's scouts (`BLOCK_KALA`, Barter `BLOCK_BARTER` for half, or free for the
    secret; `BLOCK_DAYS` days), the seals at a workbench (Repair `SEAL_REPAIR`), three dry charges (the Flotilla's
    Quartermaster, Barter `CHARGE_BARTER` or `CHARGE_KALA`; or taken from the Flotilla's store);
  - 50 the raid: `RAIDERS` pirates over the side by night, once the block is fitted (at once if the charges were bought);
  - 60 Repair `FIRE_REPAIR` at the breech with everything: Turret Two can fire, `SALVOS` salvos;
  - 70 who you tell first: the Captain, the court (a Kahuna's guard), the Flotilla (Captain Io: the secret sold), the
    Kalihi lord (if promised), or nobody;
  - the salvos (Ikaika fires on your word): the Flotilla's anchorage, a warning over the Kahala, the court's yard, Ka'au
    Crater, or kept. Each with its standing, fame and globals (`GLOBALS`) for later steps.

    plan(gd, pr)       {'rows', 'skipped', 'spots'}
    apply(pr, gd, P)   one Undo (VOICE: the quest's lines)
"""
import json
import math

import recordio

LABEL = "The Missouri's guns: the Captain's Guard and Sixteen Inches"
QUEST, QNAME = 'FOLabMissouriGuns', 'Sixteen Inches'
VOICE = [QUEST]
BLUFF = 'FOLabCaptainsBluff'
FACTION = ('FOLabCaptainsGuardFaction', "The Captain's Guard")
REP = ('FOLabRepGuard', "The Captain's Guard", 'RepNVBrotherhood')
SIDE_LINES = ("The Guard keeps you off the gangway.", "The Guard doesn't trust you.", "The Guard hardly knows you.",
              "The Guard calls you a friend of the ship.", "The Captain calls you shipmate.")
GUARD_OBJ = 40
GLOBALS = ('FOLabFlotillaHit', 'FOLabCourtBroken', 'FOLabVaultShelled', 'FOLabKahalaWarned')
PLACES = {'pilot': 'FOLabMissouriPilotHouse', 'deck2': 'FOLabMissouri2ndDeck', 'turret': 'FOLabMissouriTurretTwo', 'engine': 'FOLabMissouriEngineRoom'}
KNOW_REPAIR, IKAIKA_SPEECH, LORD_BARTER, LORD_KALA = 50, 60, 50, 50
TRUST_SPEECH, LIGHT_REPAIR, MOUNT_REPAIR, LEVER_SPEECH = 70, 40, 75, 50
PARTS_REPAIR, SEAL_REPAIR, FIRE_REPAIR = 75, 60, 95
BLOCK_KALA, BLOCK_BARTER, BLOCK_DAYS = 300, 60, 2
CHARGE_KALA, CHARGE_BARTER, CHARGES = 600, 70, 3
SELL_BARTER, SELL_HIGH, SELL_LOW = 70, 1000, 500
RAIDERS, RAID_DAYS, SALVOS = 6, 2, 3
FANTAIL_Y = 6800.0                      # (her fantail, aft of the quarterdeck, in her own frame)
SLEEP, SLEEP_FOR, NOON, EVENING, DRILL, DRILL_FOR = 22, 8, 12, 18, 14, 2
JOIN_SPEECH = 60
GUARD_FRIEND = 15                       # (the Guard's score at which it counts you a friend of the ship: band 3)
KALA = 0x0F                             # (the game's caps, Kala on the island: money.py)
# The Order (the user, 25 Nov 2026: "a hereditary knight order that wears power armor passed down from the original crew";
# names "mostly descended from midwestern American stock ... with some variation to account for interbreeding with Waikiki
# locals"). key: (editor ID, name, post, sex). Posts: the ship's places (PLACES), 'deck' (the gangway watch), 'alewa'.
CREW = {
    'captain': ('FOLabMissouriCaptain', 'Captain August Lindqvist', 'pilot', 'M'),
    'lt': ('FOLabMissouriKnightKowalski', 'Lieutenant Walter Kowalski', 'deck2', 'M'),
    'k_henderson': ('FOLabMissouriKnightHenderson', 'Knight Dorothy Henderson', 'deck2', 'F'),
    'k_brandt': ('FOLabMissouriKnightBrandt', 'Knight Emil Brandt', 'deck2', 'M'),
    'g1': ('FOLabMissouriKnightSchultz', 'Knight Kai Schultz', 'deck', 'M'),
    'g2': ('FOLabMissouriKnightDawson', 'Knight Ruth Dawson', 'deck', 'F'),
    'g3': ('FOLabMissouriKnightNovak', 'Knight Leland Novak', 'deck', 'M'),
    'g4': ('FOLabMissouriKnightBergstrom', 'Knight Makana Bergstrom', 'deck', 'M'),
    'elmer': ('FOLabMissouriElmerHaugen', 'Elmer Haugen', 'engine', 'M'),
    'sq1': ('FOLabMissouriSquire01', 'Squire Billy Kowalski', 'deck2', 'M'),
    'sq2': ('FOLabMissouriSquire02', 'Squire Ellie Brandt', 'deck2', 'F'),
    'sq3': ('FOLabMissouriSquire03', 'Squire Noa Dawson', 'deck2', 'F'),
    'sq4': ('FOLabMissouriSquire04', 'Squire Hank Schultz', 'deck2', 'M'),
    'sq5': ('FOLabMissouriSquire05', 'Squire Ilima Novak', 'deck2', 'F'),
    'sq6': ('FOLabMissouriSquire06', 'Squire Gus Lindqvist', 'deck2', 'M'),
    'sq7': ('FOLabMissouriSquire07', 'Squire Pearl Henderson', 'deck2', 'F'),
    'sq8': ('FOLabMissouriSquire08', 'Squire Keahi Bergstrom', 'deck2', 'M'),
    'sq9': ('FOLabMissouriSquire09', 'Squire Roy Dawson', 'deck2', 'M'),
    'sq10': ('FOLabMissouriSquire10', 'Squire June Olson', 'deck2', 'F'),
    'gunner': ('FOLabMissouriGunnersMate', "Gunner's Mate Ikaika Olson", 'turret', 'M'),
    'chief': ('FOLabMissouriChief', 'Chief Kekoa Peterson', 'engine', 'M'),
    'c_swenson': ('FOLabMissouriSwenson', 'Marvin Swenson', 'engine', 'M'),
    'c_jorgensen': ('FOLabMissouriJorgensen', 'Leilani Jorgensen', 'engine', 'F'),
    'c_dietz': ('FOLabMissouriDietz', 'Gunner Earl Dietz', 'turret', 'M'),
    'c_mueller': ('FOLabMissouriMueller', 'Gunner Lani Mueller', 'turret', 'F'),
    'c_schmidt': ('FOLabMissouriSchmidt', 'Cook Bertha Schmidt', 'deck2', 'F'),
    'c_larson': ('FOLabMissouriLarson', 'Cook Ned Larson', 'deck2', 'M'),
    'c_hollister': ('FOLabMissouriHollister', 'Agnes Hollister', 'deck2', 'F'),
    'c_fischer': ('FOLabMissouriFischer', 'Bosun Ray Fischer', 'deck2', 'M'),
    'lord': ('FOLabKalihiLord', 'The Kalihi Lord', 'alewa', 'M'), 's1': ('FOLabKalihiScout1', 'Kalihi Scout', 'alewa', 'M'),
    's2': ('FOLabKalihiScout2', 'Kalihi Scout', 'alewa', 'F')}
KNIGHTS = {'lt': 'Kowalski', 'k_henderson': 'Henderson', 'k_brandt': 'Brandt', 'g1': 'Schultz', 'g2': 'Dawson', 'g3': 'Novak', 'g4': 'Bergstrom'}
HEIRLOOM = 'Haugen'                     # (the eighth suit, racked in the armoury: old Elmer Haugen's family's, no heir left aboard)
MIXED = {'g1', 'g4', 'sq3', 'sq5', 'sq8', 'gunner', 'chief', 'c_jorgensen', 'c_mueller'}   # (a Hawaiian name in the family: a Hispanic face)
SQUIRES = ['sq%d' % n for n in range(1, 11)]
NIGHT_WATCH = ('g3', 'g4')              # (the gangway's night watch: they sleep by day)
RANKS = {'captain': 'Captain', 'elmer': 'Knight, retired'}
for _k in KNIGHTS:
    RANKS[_k] = 'Knight'
for _k in SQUIRES:
    RANKS[_k] = 'Squire'
TARGETS = {'flotilla': ('the Flotilla', 0.0, 0.0), 'kahala': ('Kahala', 0.0, -2600.0), 'court': ('The Royal Hawaiian', 0.0, -900.0),
           'crater': ("Ka'au Crater", 0.0, 0.0)}
QM = 'FOLabFlotillaQuartermaster'
IO = 'FOLabFlotillaCaptain'
KAHUNA_GUARD = 'FOLabKahunaGuard01'

W = {
    # the breech, the rangekeeper (messages)
    'breech_dead': "The breech is seized and the recoil cylinders are bone dry. These guns haven't fired in two hundred years, and can't.",
    'breech_nothing': "Turret Two's breech. Whatever's wrong with it, you can't tell.",
    'breech_trust': "The Guard won't let you near the breech without the Captain's word.",
    'breech_parts': "You can see what it would take: a new breech block, recoil cylinder seals, and dry powder. The forward magazines are flooded.",
    'breech_fitted': "You fit what you've brought. Still missing: ",
    'breech_fire': "The breech block seats, the seals hold, the charges go in. Turret Two can fire. Three salvos, no more.",
    'breech_short': "The gun's whole now, but making her fire takes more skill than yours.",
    # the Captain
    'cap_hi': "This is the Captain's ship. State your business.",
    'cap_trust_ask': "Captain, let me look at your guns.",
    'cap_trust_yes': "[SUCCEEDED] The court speaks well of you. All right. Turret Two. Touch nothing you can't put back.",
    'cap_trust_no': "[FAILED] My guns are my business. Good day.",
    'cap_service': "Your Guard will tell you I've done the ship some good.",
    'cap_service_yes': "They have. Go on, then. Turret Two is yours to look at.",
    'cap_lever': "I know your guns are dead, Captain. I can make them real.",
    'cap_lever_yes': "[SUCCEEDED] ...Quietly, then. If you can do it, do it. If you talk, you'll swim home.",
    'cap_lever_no': "[FAILED] You know nothing. Guard! Take this one off my ship.",
    'cap_tell': "Captain, Turret Two can fire. It's yours.",
    'cap_tell_yes': "Then I don't need the Kahuna's leave for anything, do I. You're my gunner now.",
    'cap_after': "Three salvos. We spend them well.",
    # the Lieutenant, the Chief, Ikaika, the Guard
    'lt_hi': "The Captain's in the Pilot House. Don't waste his time.",
    'chief_hi': "Engine Room. Mind the cables.",
    'light': "Your searchlight's flickering. I can fix it.",
    'light_yes': "[SUCCEEDED] Steady as a star. The Guard owes you for that.",
    'light_no': "[FAILED] Now it's worse. Leave it to me.",
    'ik_hi': "Turret Two. What do you want?",
    'ik_truth': "These guns. Do they really fire?",
    'ik_truth_yes': "[SUCCEEDED] ...No. They haven't since she grounded. The Captain signs a report every week that says ready. I'm sick of it.",
    'ik_truth_no': "[FAILED] Ready as ever. Move along.",
    'ik_friend': "Between friends of the ship: do they fire?",
    'ik_friend_yes': "Between us? No. Not one shot in two hundred years. Don't tell him I told you.",
    'mount': "Your five-inch mount's traverse is binding. Let me work on it.",
    'mount_yes': "[SUCCEEDED] She turns! I'll tell the Chief. You've done the Guard a real turn.",
    'mount_no': "[FAILED] Worse than before. Leave it.",
    'ik_fire': "Ready to fire, gunner.",
    'ik_fire_hi': "Three salvos, on your word. Where?",
    'fire_flotilla': "The Flotilla's anchorage.",
    'fire_kahala': "A warning shot over the Kahala.",
    'fire_court': "The Royal Hawaiian's yard. The court.",
    'fire_crater': "Ka'au Crater.",
    'fire_hold': "Hold fire.",
    'fired': "On the way. ...Splash. You'll hear that one all over the island.",
    'empty': "That was the last charge. She's dumb again.",
    'g_hi': "The Captain's Guard. Keep your hands where I can see them.",
    # the Kalihi lord
    'lord_hi': "Alewa Fort. The Wall Watch sees everything that crosses the wall, stranger.",
    'lord_guns': "What does the Wall Watch know about the ship's guns?",
    'lord_guns_yes': "[SUCCEEDED] That the ship never asks for shells. A gun that's never fed doesn't fire. Keep that to yourself.",
    'lord_guns_no': "[FAILED] That they're big. Everyone knows that.",
    'lord_pay': "Here's 50 kala. What do you know about the guns?",
    'lord_pay_yes': "Generous. The ship never asks for shells. Work it out.",
    'lord_court': "The court sent me. Tell me about the ship's guns.",
    'lord_court_yes': "For the court, then: those guns are dead. Everyone at the wall knows it.",
    'lord_block': "I need a breech block from a wreck at Pearl Harbor.",
    'lord_block_hi': "My scouts go past the wall. It'll cost you. 300 kala.",
    'block_pay': "300 kala. Done.",
    'block_pay_yes': "Two days. It'll be in the crate by the gate.",
    'block_barter': "Half that. Your scouts go out anyway.",
    'block_barter_yes': "[SUCCEEDED] 150, then. Two days.",
    'block_barter_no': "[FAILED] 300, or nothing.",
    'block_secret': "Do it free, and the ship's secret stays yours to keep.",
    'block_secret_yes': "Now that's worth something. Two days. And I'll want a salvo kept for me, when the time comes.",
    'lord_ready': "Your breech block is in the crate by the gate.",
    # the Quartermaster, Captain Io, the court
    'qm_charges': "I need dry powder charges. Three.",
    'qm_charges_yes': "[SUCCEEDED] Three dry charges, for a friend. Don't ask me what they're for, and I won't either.",
    'qm_charges_no': "[FAILED] Powder? For what? No.",
    'qm_pay': "600 kala for three dry charges.",
    'qm_pay_yes': "600. Here. You didn't get them from me.",
    'io_sell': "The Missouri's guns can fire again. What's that worth to you?",
    'io_sell_yes': "[SUCCEEDED] A thousand kala, and you never saw me. We'll keep off the coast a while.",
    'io_sell_no': "[FAILED] Five hundred. Take it or swim.",
    'kg_tell': "Tell the Kahuna: the Missouri's guns can fire. I fixed them.",
    'kg_tell_yes': "...The Kahuna will hear it tonight. The court won't forget this.",
    'raid': "Pirates over the side! To the rail!",
    'join': "I want to serve the Order.",
    'join_yes': "[SUCCEEDED] You've done the ship good, and the court knows your name. Kneel. You're a Squire of the Order now.",
    'join_no': "[FAILED] The Order takes its own, and those who've earned it. You haven't. Not yet.",
    'suit': "Is there a suit for me?",
    'suit_yes': "The Haugen suit's been on its rack since Elmer's boy died. Elmer says it should walk again. It's yours, Knight.",
    'suit_no': "Eight suits, and never one more. One comes free when you've earned it.",
    'heir': "A Knight has fallen. His suit...",
    'heir_yes': "No son of his left to take it up. Take it from him, and wear it well. You're his heir now.",
}
GREET = {
    'lt': "Lieutenant Kowalski. My great-great-whatever-grandfather stood this same watch. The suit remembers him.",
    'k_henderson': "Henderson suit, three hundred years of Hendersons. Mind where you walk on my ship.",
    'k_brandt': "Knight Brandt. Squires drill on the fantail at two. Don't get in the way.",
    'g1': "Gangway watch. State your business with the ship.",
    'g2': "Gangway watch. Keep your hands where I can see them.",
    'g3': "Night watch. You're out late.",
    'g4': "Night watch. The ship sleeps. Mostly.",
    'elmer': "That's my family's suit on the rack in the armoury. My boy should be wearing it. Nobody's worn it since.",
    'sq1': "Squire Kowalski. One day it's my father's suit, and I hope that day's a long way off.",
    'sq2': "I've been a Squire six years. There are only eight suits.",
    'sq3': "Drill's at two on the fantail. The Knights don't go easy.",
    'sq4': "Squire Schultz. Wanna see me strip a rifle blindfolded?",
    'sq5': "My mother's people fished the Ala Wai. My father's crewed the ship. Here I am.",
    'sq6': "The Captain's my uncle. That doesn't get me a suit any sooner.",
    'sq7': "We train in combat armour. The Knights say it's like wearing paper.",
    'sq8': "Keahi Bergstrom. My brother's the Knight. I'm the spare.",
    'sq9': "Squire Dawson. Cousin to the Knight on the gangway. Everyone's somebody's cousin aboard.",
    'sq10': "Olson. My dad's the gunner's mate. I'd rather the suits than the guns.",
    'c_swenson': "Swenson. If it hums, I keep it humming.",
    'c_jorgensen': "The panels on deck give us the lights. The Vault's cells give us the nights.",
    'c_dietz': "Gunner Dietz. Drill every day for a gun that hasn't fired. You get used to it.",
    'c_mueller': "Lani Mueller. Somebody has to keep the mount greased.",
    'c_schmidt': "Mess is at noon and six. Eat what's put in front of you.",
    'c_larson': "Ned Larson. Fish again tonight. It's always fish.",
    'c_hollister': "I keep the log, as every Hollister has since she went aground. Every Knight's name is in it, and every suit's.",
    'c_fischer': "Bosun Fischer. Lines, decks and anyone who isn't pulling their weight.",
}


def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _cond(fn, op, value, p1=0, p2=0, run=0, orr=False):
    return {'or': orr, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def _places(pr):
    return {recordio.field(r, 'EDID'): k for k, r in pr.records.items() if r.get('type') == 'CELL' and k.startswith('+')}


def _ship(pr):
    key = _mod_key(pr, 'FOLabShipMissouri', 'STAT')
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if r.get('base') == key and not r.get('removed') and r.get('p'):
                return r
    return None


def deck_spot(ship, lx, ly, up=4.0):
    """A point on her deck, from her own frame (battleship's: middle at the origin, bow -y, port +x) to the world's."""
    import battleship
    x, y, z, _rx, _ry, rz = ship['p'][:6]
    s = ship.get('s', 1.0)
    c, sn = math.cos(rz), math.sin(rz)
    lx, ly = lx * s, ly * s
    return (x + lx * c + ly * sn, y - lx * sn + ly * c, z + battleship.deck_z(ly / s) * s + up)


def plan(gd, pr):
    """Spots: the crew in the ship's places, two Guardsmen and the raid on her deck, the lord at Alewa Fort, the targets."""
    import activity
    import battleship
    import robots
    rows, skipped, S = [], [], {}
    places = _places(pr)
    taken = {}
    for k, (_e, name, where, _sex) in CREW.items():
        if where in PLACES:
            ck = places.get(PLACES[where])
            if not ck:
                skipped.append('%s: %s not in the mod' % (k, PLACES[where]))
                continue
            got, why = robots.inside_spots(gd, pr, ck, ('butler',), taken.get(ck, ()))
            if not got:
                skipped.append('%s: %s' % (k, why))
                continue
            p = got[0][1]
            taken.setdefault(ck, []).append(p[:3])
            S[k] = {'cell': ck, 'p': p}
            rows.append({'what': k, 'place': PLACES[where], 'p': [round(v) for v in p[:3]], 'near': got[0][2]})
    for k, where in (('bench', 'engine'), ('locker', 'engine')):     # (the armoury's bench and locker)
        ck = places.get(PLACES[where])
        got, why = robots.inside_spots(gd, pr, ck, ('butler',), taken.get(ck, ())) if ck else ([], 'no place')
        if got:
            taken.setdefault(ck, []).append(got[0][1][:3])
            S[k] = {'cell': ck, 'p': got[0][1]}
            rows.append({'what': k, 'place': PLACES[where], 'p': [round(v) for v in got[0][1][:3]]})
        else:
            skipped.append('%s: %s' % (k, why))
    ck = places.get(PLACES['deck2'])                    # (the berths and the mess: the 2nd Deck's own bunks and tables)
    berths, benches, twins = [], [], []
    for rk, r in ((pr.cells.get(ck) or {}).get('refs') or {}).items() if ck else ():
        if r.get('removed') or not r.get('p'):
            continue
        e = (recordio.field(pr.records[r['base']], 'EDID') if r['base'] in pr.records else gd.edid(gd.from_key(r['base']))) or ''
        if e == 'NVbedtwin01':
            twins.append(rk)                            # (the officers' beds: the Captain's quarters, then Knights)
        elif e == 'BedFrame01Bunk':
            berths.append((-r['p'][1], rk))             # (aft first: the Knights' berths aft)
        elif e.startswith('NavalBench'):
            benches.append(rk)
    S['berths'] = sorted(twins) + [rk for _y, rk in sorted(berths)]
    S['mess'] = sorted(benches)[:1]
    rows.append({'what': 'barracks', 'berths': len(S['berths']), 'mess tables': len(benches)})
    ship = _ship(pr)
    if not ship:
        skipped.append('the Missouri is not in the mod')
    else:
        gy = battleship.SPOTS['gangway_y']
        hb = battleship.half_beam(gy) - 220.0
        for k, (lx, ly) in (('g1', (-hb, gy - 260.0)), ('g2', (-hb, gy + 260.0)), ('g3', (-hb, gy - 520.0)), ('g4', (-hb, gy + 520.0))):
            S[k] = {'world': deck_spot(ship, lx, ly)}
            rows.append({'what': k, 'p': [round(v) for v in S[k]['world']]})
        S['fantail'] = {'world': deck_spot(ship, 0.0, FANTAIL_Y)}          # (the training deck: the Squires drill there)
        rows.append({'what': 'fantail', 'p': [round(v) for v in S['fantail']['world']]})
        for n in range(RAIDERS):
            ly = -1600.0 + 520.0 * n
            S['raider%d' % n] = {'world': deck_spot(ship, battleship.half_beam(ly) - 260.0, ly)}
        rows.append({'what': 'raid', 'p': [round(v) for v in S['raider0']['world']]})
    ctx = activity.Ctx(gd, pr)
    mk = {n: p for n, (_c, p) in ctx.mk.items()}
    alewa = mk.get('Alewa Fort')
    if not alewa:
        skipped.append('no Alewa Fort marker')
    else:
        for k, radii in (('lord', (400, 600, 800)), ('s1', (700, 900, 1100)), ('s2', (700, 900, 1100, 1300)), ('crate', (500, 700, 900))):
            got = ctx.around(alewa[0], alewa[1], 1, radii=radii)
            for g in got:
                if all(math.hypot(g[0] - v['world'][0], g[1] - v['world'][1]) > 200 for v in S.values() if 'world' in v):
                    S[k] = {'world': tuple(g[:3])}
                    rows.append({'what': k, 'p': [round(v) for v in g[:3]]})
                    break
            else:
                skipped.append('%s: no spot at Alewa Fort' % k)
    for k, (name, dx, dy) in TARGETS.items():
        hit = next((p for n, p in mk.items() if n.lower().startswith(name.lower())), None)
        if hit:
            S['target_' + k] = {'world': (hit[0] + dx, hit[1] + dy, hit[2] + 600.0)}
            rows.append({'what': 'target ' + k, 'p': [round(v) for v in S['target_' + k]['world']], 'marker': name})
        else:
            skipped.append('target %s: no marker named %s' % (k, name))
    return {'rows': rows, 'skipped': skipped, 'spots': S, 'world': ctx.world}


WEAR = {'captain': ('FOLabOfficersCoat|OutfitMerc02', 'Weap10mmPistol'), 'elmer': ('OutfitPrewarCasualwear',),
        'gunner': ('OutfitJumpsuitHooverDamCivilian',), 'chief': ('OutfitJumpsuitHooverDamCivilian',),
        'c_swenson': ('OutfitJumpsuitHooverDamCivilian',), 'c_jorgensen': ('OutfitJumpsuitHooverDamCivilian',),
        'c_dietz': ('OutfitJumpsuitHooverDamCivilian',), 'c_mueller': ('OutfitJumpsuitHooverDamCivilian',),
        'c_schmidt': ('OutfitPrewarCasualwear',), 'c_larson': ('OutfitPrewarCasualwear',), 'c_hollister': ('OutfitPrewarCasualwear',),
        'c_fischer': ('OutfitJumpsuitHooverDamCivilian', 'Weap10mmPistol'),
        'lord': ('OutfitMerc04', 'WeapNVVarmintRifle'), 's1': ('ArmorLeather', 'Weap10mmPistol'), 's2': ('ArmorLeather', 'Weap10mmPistol')}
for _k in SQUIRES:
    WEAR[_k] = ('ArmorCombat', 'ArmorCombatHelmet', 'WeapNVServiceRifle')
for _k in KNIGHTS:
    WEAR[_k] = ('WeapNVServiceRifle',)         # (and their family's suit: made by ops)
RACES = ('Hispanic', 'Asian', 'AfricanAmerican', 'Caucasian')


def _item_key(gd, pr, names):
    for e in names.split('|'):
        k = _mod_key(pr, e)
        if k:
            return k
        f = next((f for f, (i, r) in gd.forms.items() if r.tag in ('ARMO', 'WEAP') and gd.edid(f) == e), None)
        if f is not None:
            return gd.key(f)
    return None


def women_faces(gd, pr):
    """{race: [game NPC_]} of women, as heldwatch.men_faces has men: the game's ordinary women called only by a role and
    the race presets, none with a template, none dead, none any person of the mod already wears."""
    import factionfolk as ff
    import heldwatch
    got = getattr(gd, '_order_women', None)
    if got is None:
        races = {f: gd.edid(f) for f, (_i, r) in gd.forms.items() if r.tag == 'RACE'}
        got = {}
        for f, (i, r) in sorted(gd.forms.items()):
            if r.tag != 'NPC_' or i != 0:
                continue
            e = (gd.edid(f) or '').lower()
            if e.endswith(('dead', 'template')):
                continue
            rec = recordio.load(gd, f)
            full = recordio.field(rec, 'FULL') or ''
            if recordio.field(rec, 'TPLT') or not (ff._num(rec, 'ACBS', 'Flags') & 1):
                continue
            if full not in heldwatch.ISLANDER_ROLES and not (full.startswith('race') and full[-3:-2] == 'F'):
                continue
            rn = recordio.field(rec, 'RNAM')
            race = races.get(gd.from_key(rn)) if rn else None
            if race in RACES:
                got.setdefault(race, []).append(f)
        gd._order_women = got
    used = set()
    for r in pr.records.values():
        if r.get('type') == 'NPC_':
            used.add(r.get('copied_from'))
            used.add(recordio.field(r, 'TPLT'))
    return {race: [f for f in v if gd.key(f) not in used] for race, v in got.items()}


def _face(gd, pr, ctx, k):
    """A face no one in the mod wears: the family's stock (Caucasian; Hispanic where a Hawaiian name married in), the sex."""
    import heldwatch
    _e, _n, _w, sex = CREW[k]
    pool = heldwatch.men_faces(gd, pr) if sex == 'M' else women_faces(gd, pr)
    want = ['Hispanic', 'Caucasian', 'AfricanAmerican'] if k in MIXED else ['Caucasian', 'Hispanic', 'AfricanAmerican']
    for race in want:
        for f in pool.get(race, ()):
            if gd.key(f) not in ctx._held_taken:
                ctx._held_taken.add(gd.key(f))
                return f
    return None


def _person(gd, pr, ctx, k, fac, extra=()):
    """One of the Order, the lord or a scout: a face no one else in the mod wears, their clothes and gun (a Knight's suit is
    `extra`), the faction; at their post (their packages are added by ops)."""
    import factionfolk as ff
    edid, name, _where, _sex = CREW[k]
    face = _face(gd, pr, ctx, k)
    if face is None:
        raise ValueError('no free face left for %s' % edid)
    g = dict(ff.GROUPS['court_fighter'])
    g['package'] = 'DefaultStayAtEditorLocation'
    items = [(it, 1) for it in (_item_key(gd, pr, n) for n in WEAR[k]) if it] + [(x, 1) for x in extra]
    rec = ff.person(gd, pr, face, edid, name, g, items, [], fac or '')
    ff._set_num(rec, 'AIDT', 'Aggression', 1)
    ff._set_num(rec, 'AIDT', 'Confidence', 3)
    return rec


def _suit(gd, family, helmet=False):
    """A family's heirloom: the game's T-45d under its family's name (the Missouri's own look is a retexture of its own)."""
    import surffish
    src = 'ArmorPowerT45dHelmet' if helmet else 'ArmorPowerT45d'
    return surffish._copy(gd, 'ARMO', src, 'FOLabOrderSuit%s%s' % (family, 'Helmet' if helmet else ''),
                          '%s Family T-45d%s' % (family, ' Helmet' if helmet else ''))


def _faction(gd, pr):
    import factionfolk as ff
    fac = ff._faction(gd, *FACTION)
    court = _mod_key(pr, 'FOLabKahunaCourtFaction', 'FACT')
    if court:                                   # (allied to the court, as the ship and the palace have been)
        fac['subs'].insert(2, {'tag': 'XNAM', 'label': 'Relation', 'kind': 'struct', 'fields': [
            {'name': 'Faction', 'code': 'F', 'value': court}, {'name': 'Modifier', 'code': 'i', 'value': 0},
            {'name': 'Group combat reaction', 'code': 'I', 'value': 2}]})
    return fac


def _misc(gd, edid, name, like):
    import surffish
    rec = surffish._copy(gd, 'MISC', like, edid, name)
    rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'SCRI']
    return rec


def _recipe(gd, seals_key):
    import surffish
    rcpe = surffish._copy(gd, 'RCPE', 'RecipeWeaponRepairKit', 'FOLabRecipeRecoilSeals', 'Recoil Cylinder Seals')
    head = [s for s in rcpe['subs'] if s['tag'] in ('EDID', 'FULL', 'DATA')]
    for s in head:
        if s['tag'] == 'DATA':
            for f in s['fields']:
                if f['name'] == 'Level':
                    f['value'] = SEAL_REPAIR
    rcil = next(s for s in rcpe['subs'] if s['tag'] == 'RCIL')
    qty = next(s for s in rcpe['subs'] if s['tag'] == 'RCQY')
    rcod = next(s for s in rcpe['subs'] if s['tag'] == 'RCOD')

    def n(c):
        q = json.loads(json.dumps(qty))
        q['fields'][0]['value'] = c
        return q
    body = []
    for e, c in (('DuctTape', 2), ('WonderGlue', 1), ('LeatherBelt', 2)):
        f = next(f for f, (i, r) in gd.forms.items() if r.tag == 'MISC' and gd.edid(f) == e)
        body += [dict(rcil, value=gd.key(f)), n(c)]
    rcpe['subs'] = head + body + [dict(rcod, value=seals_key), n(1)]
    return rcpe


def _global(edid):
    import stormafter
    rec = json.loads(json.dumps(stormafter.flag_record()))
    recordio.set_field(rec, 'EDID', edid, label='Editor ID')
    return rec


RANGEKEEPER = """Terminal: FOLabMissouriRangekeeper
Name: Turret Two Rangekeeper
Model: desk
Lock: hard
Welcome:
  USS MISSOURI (BB-63)
  TURRET TWO - RANGEKEEPER
== Firing solution
Script: set FOLabMissouriGuns.solution to 1
Says:
  Turret One: elevating gear lost. Turret Three: flooded below.
  Turret Two: mechanically whole. Training and elevation by hand, slow.
  Solution: Turret Two can lay on any target within range with what is here,
  given a sound breech, sealed recoil cylinders and dry charges.
"""
MESSAGES = {'dead': 'breech_dead', 'nothing': 'breech_nothing', 'trust': 'breech_trust', 'parts': 'breech_parts',
            'fitted': 'breech_fitted', 'fire': 'breech_fire', 'short': 'breech_short'}


GUNNERS_MATE = 'FOLabPerkGunnersMate'   # (the milestone perk, Repair 100: "one part fewer": the seals aren't needed)


def breech_script(msgs, gunners_mate=False):
    q = QUEST
    rep = lambda s: 'player.GetActorValue Repair >= %d' % s
    perk = ['\tif player.HasPerk %s == 1' % GUNNERS_MATE, '\t\tset lucky to 1', '\tendif'] if gunners_mate else []
    return '\n'.join([
        'scn FOLabTurretTwoBreechScript', 'short seals', 'short lucky', '', 'Begin OnActivate player',
        '\tset lucky to 0'] + perk + [
        '\tset seals to player.GetItemCount FOLabRecoilSeals', '\tif lucky == 1', '\t\tset seals to 1', '\tendif',
        '\tif %s.ready == 1' % q, '\t\tShowMessage %s' % msgs['fire'],
        '\telseif %s.trust == 0' % q,
        '\t\tif %s.knows == 1' % q, '\t\t\tShowMessage %s' % msgs['trust'],
        '\t\telseif %s' % rep(KNOW_REPAIR), '\t\t\tShowMessage %s' % msgs['dead'], '\t\t\tset %s.knows to 1' % q,
        '\t\telse', '\t\t\tShowMessage %s' % msgs['nothing'], '\t\tendif',
        '\telseif %s.parts == 0' % q,
        '\t\tif %s' % rep(PARTS_REPAIR), '\t\t\tShowMessage %s' % msgs['parts'], '\t\t\tset %s.parts to 1' % q,
        '\t\telse', '\t\t\tShowMessage %s' % msgs['nothing'], '\t\tendif',
        '\telse',
        '\t\tif %s.fitted == 0' % q, '\t\t\tif player.GetItemCount FOLabBreechBlock >= 1', '\t\t\t\tplayer.RemoveItem FOLabBreechBlock 1',
        '\t\t\t\tset %s.fitted to 1' % q, '\t\t\tendif', '\t\tendif',
        '\t\tif %s.fitted == 1' % q, '\t\t\tif %s.raid_done == 1' % q, '\t\t\t\tif seals >= 1',
        '\t\t\t\t\tif player.GetItemCount FOLabDryCharge >= %d' % CHARGES,
        '\t\t\t\t\t\tif %s' % rep(FIRE_REPAIR),
        '\t\t\t\t\t\t\tif lucky == 0', '\t\t\t\t\t\t\t\tplayer.RemoveItem FOLabRecoilSeals 1', '\t\t\t\t\t\t\tendif',
        '\t\t\t\t\t\t\tplayer.RemoveItem FOLabDryCharge %d' % CHARGES,
        '\t\t\t\t\t\t\tset %s.ready to 1' % q, '\t\t\t\t\t\t\tShowMessage %s' % msgs['fire'], '\t\t\t\t\t\t\treturn',
        '\t\t\t\t\t\telse', '\t\t\t\t\t\t\tShowMessage %s' % msgs['short'], '\t\t\t\t\t\t\treturn', '\t\t\t\t\t\tendif',
        '\t\t\t\t\tendif', '\t\t\t\tendif', '\t\t\tendif', '\t\tendif',
        '\t\tShowMessage %s' % msgs['fitted'],
        '\tendif', 'End', ''])


def quest_script():
    q = QUEST
    raid = ['FOLabMissouriRaider%dRef' % n for n in range(RAIDERS)]
    dead = ' && '.join('%s.GetDead == 1' % r for r in raid)
    L = ['scn FOLabMissouriGunsScript',
         'short knows', 'short trust', 'short light', 'short mount', 'short parts', 'short solution', 'short ordered', 'float block_day',
         'short block_done', 'short fitted', 'float raid_day', 'short raid_on', 'short raid_done', 'short bought', 'short ready',
         'short salvos', 'short told', 'short promised', 'short fire', 'short started', 'short night', 'short sold_out',
         'short squire', 'short suit', 'short heir', 'short late_deed', 'short give', '',
         'Begin GameMode',
         '\tif started == 0', '\t\tset started to 1', '\t\tset salvos to %d' % SALVOS, '\t\tFOLabKalihiCrateRef.Disable']
    L += ['\t\t%s.Disable' % r for r in raid] + ['\tendif']
    L += ['\tif knows == 0', '\t\tif %s.knows == 1' % BLUFF, '\t\t\tset knows to 1', '\t\tendif', '\tendif',
          '\tif knows == 1', '\t\tif GetStage %s < 10' % q, '\t\t\tSetStage %s 10' % q, '\t\tendif', '\tendif',
          '\tif trust == 1', '\t\tif GetStage %s < 20' % q, '\t\t\tSetStage %s 20' % q, '\t\tendif', '\tendif',
          '\tif parts == 1', '\t\tif solution == 1', '\t\t\tif GetStage %s < 30' % q, '\t\t\t\tSetStage %s 30' % q, '\t\t\tendif', '\t\tendif', '\tendif',
          '\tif ordered == 1', '\t\tif block_done == 0', '\t\t\tif GameDaysPassed >= block_day',
          '\t\t\t\tset block_done to 1', '\t\t\t\tFOLabKalihiCrateRef.Enable', '\t\t\t\tSetStage %s 42' % q, '\t\t\tendif', '\t\tendif', '\tendif',
          '\tif fitted == 1', '\t\tif raid_day == 0', '\t\t\tset raid_day to GameDaysPassed + %d' % RAID_DAYS, '\t\t\tif bought == 1',
          '\t\t\t\tset raid_day to GameDaysPassed', '\t\t\tendif', '\t\t\tSetStage %s 45' % q, '\t\tendif', '\tendif',
          '\tset night to 0', '\tif GameHour >= 21', '\t\tset night to 1', '\tendif', '\tif GameHour < 4', '\t\tset night to 1', '\tendif',
          '\tif fitted == 1', '\t\tif raid_on == 0', '\t\t\tif raid_done == 0', '\t\t\t\tif night == 1', '\t\t\t\t\tif GameDaysPassed >= raid_day']
    L += ['\t\t\t\t\t\t%s.Enable' % r for r in raid]
    L += ['\t\t\t\t\t\tset raid_on to 1', '\t\t\t\t\t\tSetStage %s 50' % q, '\t\t\t\t\tendif', '\t\t\t\tendif', '\t\t\tendif', '\t\tendif', '\tendif',
          '\tif raid_on == 1', '\t\tif %s' % dead, '\t\t\tset raid_on to 0', '\t\t\tset raid_done to 1', '\t\t\tSetStage %s 55' % q, '\t\tendif', '\tendif',
          '\tif ready == 1', '\t\tif GetStage %s < 60' % q, '\t\t\tSetStage %s 60' % q, '\t\tendif', '\tendif',
          # (a Squire's further deed: the guns made to fire or the raid beaten after joining; a Knight's death makes you heir)
          '\tif squire == 1', '\t\tif suit == 0', '\t\t\tif late_deed == 0', '\t\t\t\tif raid_done == 1', '\t\t\t\t\tif GetStageDone %s 92 == 1' % q,
          '\t\t\t\t\t\tset late_deed to 1', '\t\t\t\t\tendif', '\t\t\t\tendif', '\t\t\tendif', '\t\t\tif heir == 0'] + \
         ['\t\t\t\tif FOLabMissouriKnight%sRef.GetDead == 1' % f + '\n\t\t\t\t\tset heir to 1\n\t\t\t\tendif' for f in KNIGHTS.values()] + \
         ['\t\t\tendif', '\t\tendif', '\tendif',
          # (the Haugen suit from the armoury's locker, once the Captain gives it: stage 94 sets give)
          '\tif give == 1', '\t\tset give to 2', '\t\tFOLabOrderArmouryLockerRef.RemoveAllItems player', '\tendif',
          # (a salvo: three shells land by the target's marker; the stage for it says what it changes)
          '\tif fire > 0', '\t\tif salvos > 0']
    for code, (key, stage) in enumerate((('Flotilla', 80), ('Kahala', 82), ('Court', 84), ('Crater', 86)), 1):
        L += ['\t\t\tif fire == %d' % code] + ['\t\t\t\tFOLabMissouriTarget%sRef.PlaceAtMe NellisArtilleryExplosion 1' % key] * 3 + \
             ['\t\t\t\tSetStage %s %d' % (q, stage), '\t\t\tendif']
    L += ['\t\t\tset salvos to salvos - 1', '\t\t\tif told == 3', '\t\t\t\tif sold_out == 0', '\t\t\t\t\tset sold_out to 1', '\t\t\t\t\tSetStage %s 88' % q,
          '\t\t\t\tendif', '\t\t\tendif', '\t\t\tif salvos == 0', '\t\t\t\tSetStage %s 90' % q, '\t\t\tendif', '\t\tendif', '\t\tset fire to 0', '\tendif',
          'End', '']
    return '\n'.join(L)


PA_TRAINING = 'if player.HasPerk PowerArmorTraining == 0\nplayer.AddPerk PowerArmorTraining\nendif\n'


def quest_plain(gd, pr, key_script):
    import piratedeal
    import repstanding as RS
    reps = {k: piratedeal.REPS[k][0] for k in ('court', 'pirates')}
    have = {k: bool(_mod_key(pr, v, 'REPU')) for k, v in reps.items()}
    fame = lambda side, n: ('AddReputation %s 1 %d\n' % (reps[side], n)) if have.get(side) else ''
    infamy = lambda side, n: ('AddReputation %s 0 %d\n' % (reps[side], n)) if have.get(side) else ''
    gfame = lambda n: 'AddReputation %s 1 %d\n' % (REP[0], n)
    ginf = lambda n: 'AddReputation %s 0 %d\n' % (REP[0], n)
    obj = lambda n, on: 'SetObjectiveDisplayed %s %d %d\n' % (QUEST, n, on)
    done = lambda n: 'SetObjectiveCompleted %s %d 1\n' % (QUEST, n)
    b = lambda side, n: RS.bump(side, n) + '\n'

    def stage(n, log, src=''):
        return {'index': n, 'entries': [{'flags': {}, 'conditions': [], 'next': '', 'log': log, 'script': {'source': src, 'parts': None}}]}
    S = [
        stage(10, "The Missouri's big guns can't fire. The Captain's power rests on a bluff.", obj(10, 1) + done(10) + obj(20, 1)),
        stage(20, "The Captain trusts me near his guns. Turret Two is mine to look at.", done(20) + obj(30, 1)),
        stage(30, "Turret Two could fire, with a breech block, recoil cylinder seals and three dry powder charges.", done(30) + obj(40, 1)),
        stage(40, "The Kalihi lord's scouts will bring a breech block from a wreck at Pearl Harbor, past the wall.", ''),
        stage(42, "The breech block is in the crate by Alewa Fort's gate.", ''),
        stage(45, "The breech block is fitted. Word will get out.", ''),
        stage(50, "Pirates are boarding the Missouri.", obj(50, 1)),
        stage(55, "The boarding party is beaten off.", done(50) + b('guard', 10) + gfame(1)),
        stage(60, "Turret Two can fire. Three salvos, no more. Who hears of it first matters. The Order taught me to wear power armour for it.",
              done(40) + obj(60, 1) + done(60) + obj(70, 1) + PA_TRAINING),
        stage(70, "I told the Captain first. His power is real now, and he doesn't need the Kahuna's leave.",
              gfame(2) + b('guard', 20) + 'set FOLabCaptainBroke to 1\n'),
        stage(72, "I told the court first. The Kahuna's threat is no bluff now. The Guard counts me the court's spy.",
              fame('court', 2) + b('court', 20) + b('guard', -20)),
        stage(74, "I sold the secret to the Flotilla.", fame('pirates', 1)),
        stage(76, "I promised the Kalihi lord the ship's secret is his to keep.", ''),
        stage(80, "Turret Two fired on the Flotilla's anchorage.", b('pirates', 30) + infamy('pirates', 2) + fame('court', 1) + gfame(1) +
              'set FOLabFlotillaHit to 1\n'),
        stage(82, "Turret Two fired a warning over the Kahala.", b('pirates', 15) + 'set FOLabKahalaWarned to GameDaysPassed + 7\n'),
        stage(84, "Turret Two fired on the court. The Kahuna's yard is rubble, and the Captain holds Waikiki.",
              infamy('court', 3) + b('court', -50) + gfame(1) + 'SetEnemy FOLabKahunaCourtFaction PlayerFaction\nset FOLabCourtBroken to 1\n'),
        stage(86, "Turret Two fired on Ka'au Crater. Whoever is up there knows the ship can reach them.", 'set FOLabVaultShelled to 1\n'),
        stage(88, "The salvo gave away that I'd sold the secret.", ginf(1) + infamy('court', 1)),
        stage(90, "That was the last dry charge. Turret Two is dumb again.", done(70)),
        stage(92, "The Captain named me a Squire of the Order. A suit comes to a Squire who proves worthy, or when a Knight falls.",
              'player.AddToFaction FOLabCaptainsGuardFaction 0\nplayer.AddItem ArmorCombat 1\nplayer.AddItem ArmorCombatHelmet 1\n' + PA_TRAINING +
              gfame(1)),
        stage(94, "The Captain gave me the Haugen suit from the armoury. I'm a Knight of the Order.",
              'set %s.give to 1\n' % QUEST + gfame(2) + b('guard', 20)),
        stage(96, "A Knight has fallen. The Captain named me heir to his suit.", gfame(1)),
    ]
    objectives = [{'index': 10, 'text': "Find out whether the Missouri's guns can fire", 'targets': []},
                  {'index': 20, 'text': "Win the Captain's trust", 'targets': []},
                  {'index': 30, 'text': "Find out what Turret Two would need", 'targets': []},
                  {'index': 40, 'text': "Get a breech block, recoil cylinder seals and three dry charges", 'targets': []},
                  {'index': 50, 'text': "Beat off the boarding party", 'targets': []},
                  {'index': 60, 'text': "Make Turret Two fire", 'targets': []},
                  {'index': 70, 'text': "Choose who hears first, and where the salvos go", 'targets': []}]
    return {'edid': QUEST, 'name': QNAME, 'script': key_script, 'flags': {'start_enabled': True, 'repeat_stages': True}, 'priority': 55,
            'delay': 1.0, 'stages': S, 'objectives': objectives, 'conditions': []}


TRADER = 'FOLabPirateTraderKahala'       # (the Flotilla itself is hostile ground: its charges are sold by the pirates' Kahala trader)
SELLS_TO = 'FOLabPirateCaptainDeals'     # (a pirate captain who deals: the secret sold)
STORE_PLACE, STORE_ROOM = 'FOLabFlotillaBelowDecks', 'store'


def _store_spot(gd, pr):
    """(cell, (x, y, z, rz)) on the navmesh in the Flotilla's store room (shipcrew's rooms), clear of its other things."""
    import robots
    import shipcrew
    ck = _places(pr).get(STORE_PLACE)
    if not ck:
        return None
    i0, j0, w, h = shipcrew.ROOMS['below'][STORE_ROOM]
    x0, x1, y0, y1 = i0 * shipcrew.S, (i0 + w) * shipcrew.S, j0 * shipcrew.S, (j0 + h) * shipcrew.S
    tris = [p for p in robots._tris(gd, pr, ck) if x0 + 40 <= p[0] <= x1 - 40 and y0 + 40 <= p[1] <= y1 - 40]
    if not tris:
        return None
    things = [r['p'] for r in (pr.cells.get(ck) or {}).get('refs', {}).values() if r.get('p') and not r.get('removed')]
    best = max(tris, key=lambda p: min((math.hypot(p[0] - t[0], p[1] - t[1]) for t in things), default=1e9))
    return ck, (best[0], best[1], best[2], 0.0)


def standing_ops(gd, pr, rep_key):
    """repstanding's quest and script with a fourth side, the Captain's Guard: its script compiled again (its variables keep
    their numbers, the new ones after) and its quest's objectives with the Guard's five lines. Ops (records)."""
    import api_scripts
    import questrec as qr
    import repstanding as RS
    qk = _mod_key(pr, RS.QUEST, 'QUST')
    sk = _mod_key(pr, RS.SCRIPT, 'SCPT')
    if not qk or not sk:
        raise ValueError('the standing step (repstanding) first')
    sides, objs = dict(RS.SIDES), dict(RS.OBJ)
    try:
        RS.SIDES['guard'] = SIDE_LINES
        RS.OBJ['guard'] = GUARD_OBJ
        src = RS.script_source(RS.pirate_bases(pr)).replace(
            'short started', 'short started').replace('short band\n', 'short band\nshort guard\nshort bandguard\n')
        sc = api_scripts.scripts()
        c = sc.compile(src, sk, 'quest', {qk: pr.records[qk]})
        if not hasattr(c, 'subrecords'):
            raise ValueError('the standing script with the Guard: %s' % (c,))
        srec = sc._record_of(c, RS.SCRIPT)
    finally:
        RS.SIDES.clear()
        RS.SIDES.update(sides)
        RS.OBJ.clear()
        RS.OBJ.update(objs)
    plain = qr.quest_plain(json.loads(json.dumps(pr.records[qk])))
    if not any(o['index'] == GUARD_OBJ for o in plain['objectives']):
        plain['objectives'] += [{'index': GUARD_OBJ + b, 'text': t, 'targets': []} for b, t in enumerate(SIDE_LINES)]
    return [{'op': 'record', 'key': sk, 'record': srec}, {'op': 'record', 'key': qk, 'record': qr.quest_record(plain)}], srec


def ops(gd, pr, P=None):
    """(ops, report, built): one Undo's records and refs; the quest record and lines come after (apply)."""
    import activity
    import api_scripts
    import piratedeal
    import questrec as qr
    import tes4
    import terminals
    from activity import _new_key
    if _mod_key(pr, QUEST, 'QUST'):
        raise ValueError('the mod already has %s (Undo first)' % QUEST)
    if not _mod_key(pr, BLUFF, 'QUST'):
        raise ValueError("the Missouri's fire control (missouriterms) first")
    P = P or plan(gd, pr)
    S = P['spots']
    need = list(CREW) + ['raider%d' % n for n in range(RAIDERS)] + ['crate'] + ['target_' + t for t in TARGETS]
    missing = [k for k in need if k not in S]
    if missing:
        raise ValueError('no spot for: %s' % ', '.join(missing))
    world = P['world']
    grid = gd.grid(world if not isinstance(world, str) else gd.from_key(world))
    out, rep, named = [], {'made': [], 'skipped': P['skipped']}, {}

    def record(rec, k=None):
        k = k or _new_key(pr)
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(recordio.field(rec, 'EDID'))
        return k

    def place(base, spot, edid, props=None, persistent=True):
        k = _new_key(pr)
        if 'cell' in spot:
            ck, (x, y, z, rz) = spot['cell'], spot['p']
        else:
            x, y, z = spot['world']
            rz = spot.get('rz', 0.0)
            ck = gd.key(grid[(int(math.floor(x / 4096.0)), int(math.floor(y / 4096.0)))])
        ref = {'base': base, 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, rz], 's': 1.0, 'persistent': persistent, 'edid': edid}
        if props:
            ref['props'] = props
        named[k] = edid
        out.append({'op': 'place', 'cell': ck, 'key': k, 'ref': ref})
        return k
    # the Guard: faction, reputation
    fac = record(_faction(gd, pr))
    repu = record(piratedeal._rep_record(gd, REP[0], REP[1], REP[2]))
    for r in out:
        if r['op'] == 'record' and r['key'] == fac:
            r['record']['subs'].append({'tag': 'WMI1', 'label': 'Reputation', 'kind': 'F', 'value': repu})
    globs = {g: record(_global(g)) for g in GLOBALS + ('FOLabCaptainBroke',)}
    # the parts, the seals' recipe, the dry charges' hiding place
    block = record(_misc(gd, 'FOLabBreechBlock', "16-inch Breech Block", 'SpareParts'))
    seals = record(_misc(gd, 'FOLabRecoilSeals', 'Recoil Cylinder Seals', 'Conductor'))
    charge = record(_misc(gd, 'FOLabDryCharge', '16-inch Dry Powder Charge', 'HVFilterPart01'))
    record(_recipe(gd, seals))
    import anquest
    crate = record(anquest._chest(gd, pr, 'FOLabKalihiCrate', block))
    stash = record(anquest._chest(gd, pr, 'FOLabFlotillaChargeLocker', charge))
    for o in out:                                   # (three charges in the Flotilla's locker)
        if o['op'] == 'record' and o['key'] == stash:
            for s in o['record']['subs']:
                if s['tag'] == 'CNTO':
                    for f in s['fields']:
                        if f.get('name') == 'Count':
                            f['value'] = CHARGES
    # messages and the breech activator
    import newgame
    msgs = {k: record(newgame._message_record('FOLabMissouriMsg%s' % k.capitalize(), W[v])) for k, v in MESSAGES.items()}
    msg_edids = {k: 'FOLabMissouriMsg%s' % k.capitalize() for k in MESSAGES}
    import surffish
    act = surffish._copy(gd, 'ACTI', 'VControlPanel01R', 'FOLabTurretTwoBreech', 'Turret Two Breech')
    act_key = _new_key(pr)
    breech_skey = _new_key(pr)
    # people
    ctx = activity.Ctx.__new__(activity.Ctx)
    ctx.gd, ctx.pr = gd, pr
    ctx._held_taken = {v for r in pr.records.values() if r.get('type') == 'NPC_' for v in (r.get('copied_from'), recordio.field(r, 'TPLT')) if v}
    # the Order's eight suits, an heirloom each, named for its family; the Haugen suit racked in the armoury
    import sidequests
    import api_characters as ac
    suits = {}
    for fam in list(KNIGHTS.values()) + [HEIRLOOM]:
        suits[fam] = (record(_suit(gd, fam)), record(_suit(gd, fam, True)))
    locker = json.loads(json.dumps(anquest._chest(gd, pr, 'FOLabOrderArmouryLocker', suits[HEIRLOOM][0])))
    recordio.set_field(locker, 'FULL', 'Armoury Locker') if any(x['tag'] == 'FULL' for x in locker['subs']) else \
        ac.insert(locker, {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': 'Armoury Locker'})
    ac.insert(locker, sidequests._cnto(gd, suits[HEIRLOOM][1], 1))
    locker_key = record(locker)
    people = {}
    for k in CREW:
        people[k] = record(_person(gd, pr, ctx, k, fac if k not in ('lord', 's1', 's2') else '', suits[KNIGHTS[k]] if k in KNIGHTS else ()))
    refs = {}
    for k in CREW:
        refs[k] = place(people[k], S[k], CREW[k][0] + 'Ref')
    # the barracks: the Captain's bed, the armoury's bench and locker, the training deck's marker
    place(gd.key(piratedeal._game(gd, 'WorkBench', 'ACTI')), S['bench'], 'FOLabOrderWorkbenchRef', persistent=False)
    place(locker_key, S['locker'], 'FOLabOrderArmouryLockerRef', {'lock': {'level': 100, 'key': '', 'leveled': False}})
    fantail = place(gd.key(piratedeal._game(gd, 'XMarkerHeading', 'STAT')), S['fantail'], 'FOLabOrderFantailRef')
    # by the hour: a berth each (the Knights aft), the mess at noon and evening, the Squires' drill on the fantail
    import huanginside as HI
    pack = lambda edid, src, hour, hours, target, radius: record(HI._pack(gd, src, edid, hour, hours, target, radius))
    mess = (S.get('mess') or [None])[0]
    meals = [pack('FOLabOrderMessNoon', 'DefaultSandboxEditorLocation512', NOON, 1, mess, 600),
             pack('FOLabOrderMessEvening', 'DefaultSandboxEditorLocation512', EVENING, 1, mess, 600)] if mess else []
    drill = pack('FOLabOrderDrill', 'DefaultSandboxEditorLocation512', DRILL, DRILL_FOR, fantail, 600)
    berths = iter(S.get('berths') or ())
    rep['berths'] = {}
    for k in CREW:
        if k in ('lord', 's1', 's2'):
            continue
        bed = next(berths, None)          # (the Captain first: an officer's bed)
        mine = []
        if bed:
            mine.append(pack('FOLabOrderSleep%s' % CREW[k][0][12:], 'DefaultSleepAlways256', 8 if k in NIGHT_WATCH else SLEEP, SLEEP_FOR, bed, 128))
            rep['berths'][k] = bed
        if k in SQUIRES:
            mine.append(drill)
        mine += meals
        rec = next(o['record'] for o in out if o['op'] == 'record' and o['key'] == people[k])
        at = next(i for i, x in enumerate(rec['subs']) if x['tag'] == 'PKID')
        rec['subs'][at:at] = [{'tag': 'PKID', 'label': 'AI package', 'kind': 'F', 'value': pk} for pk in mine]
    raider = _mod_key(pr, 'FOLabPirateLvlFiend2GunVarNV', 'NPC_') or next((k for k, r in pr.records.items() if r.get('type') == 'NPC_'
                                                                           and (recordio.field(r, 'EDID') or '').startswith('FOLabPirate')), None)
    if not raider:
        raise ValueError('no pirate of the mod for the raid')
    for n in range(RAIDERS):
        place(raider, S['raider%d' % n], 'FOLabMissouriRaider%dRef' % n)
    xmh = gd.key(piratedeal._game(gd, 'XMarkerHeading', 'STAT'))
    for t in TARGETS:
        place(xmh, S['target_' + t], 'FOLabMissouriTarget%sRef' % t.capitalize())
    place(crate, S['crate'], 'FOLabKalihiCrateRef')
    st = _store_spot(gd, pr)
    if st:
        place(stash, {'cell': st[0], 'p': st[1]}, 'FOLabFlotillaChargeLockerRef', {'lock': {'level': 75, 'key': '', 'leveled': False}})
    else:
        rep['skipped'].append("the Flotilla's store: no spot (charges only from the trader)")
    # the breech in Turret Two, by the gunner's post
    tp = S['gunner']
    place(act_key, {'cell': tp['cell'], 'p': (tp['p'][0] + 180.0, tp['p'][1], tp['p'][2] - 4.0, tp['p'][3])}, 'FOLabTurretTwoBreechRef', persistent=False)
    actors = set(people.values()) | {raider}
    ext = {o['key']: {'type': 'ACHR' if o['ref']['base'] in actors else 'REFR', 'flags': tes4.PERSISTENT,
                      'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': o['ref']['edid']}]}
           for o in out if o['op'] == 'place'}
    B = type('B', (), {})()
    B.people, B.ext, B.fac, B.repu, B.block, B.seals, B.charge, B.msgs, B.act, B.act_key, B.breech_skey, B.msg_edids = \
        people, ext, fac, repu, block, seals, charge, msgs, act, act_key, breech_skey, msg_edids
    B.globs = globs
    B.key, B.skey = _new_key(pr), _new_key(pr)
    return out, rep, B


def apply(pr, gd, P=None):
    import api_quests as aq
    import api_scripts
    import questrec as qr
    import terminals
    from missouriterms import _WithScript
    o, rep, B = ops(gd, pr, P)
    plain = quest_plain(gd, pr, B.skey)
    stub = qr.quest_record(dict(plain, stages=[], objectives=[]))
    known = dict(B.ext, **{B.key: stub})
    known.update({x['key']: x['record'] for x in o if x['op'] == 'record'})
    sc = api_scripts.scripts()
    c = sc.compile(quest_script(), B.skey, 'quest', known)
    if not hasattr(c, 'subrecords'):
        raise ValueError('FOLabMissouriGunsScript: %s' % (c,))
    srec = sc._record_of(c, 'FOLabMissouriGunsScript')
    known[B.skey] = srec
    cb = sc.compile(breech_script(B.msg_edids, bool(_mod_key(pr, GUNNERS_MATE, 'PERK'))), B.breech_skey, 'object', known)
    if not hasattr(cb, 'subrecords'):
        raise ValueError('FOLabTurretTwoBreechScript: %s' % (cb,))
    for s in B.act['subs']:
        if s['tag'] == 'SCRI':
            s['value'] = B.breech_skey
    if not any(s['tag'] == 'SCRI' for s in B.act['subs']):
        import api_characters as ac
        ac.insert(B.act, {'tag': 'SCRI', 'label': 'Script', 'kind': 'F', 'value': B.breech_skey})
    o += [{'op': 'record', 'key': B.skey, 'record': srec}, {'op': 'record', 'key': B.key, 'record': stub},
          {'op': 'record', 'key': B.breech_skey, 'record': sc._record_of(cb, 'FOLabTurretTwoBreechScript')},
          {'op': 'record', 'key': B.act_key, 'record': B.act}]
    rep['made'] += ['FOLabMissouriGunsScript', QUEST, 'FOLabTurretTwoBreechScript', 'FOLabTurretTwoBreech']
    s_ops, s_rec = standing_ops(gd, pr, B.repu)
    o += s_ops
    # the rangekeeper in Turret Two (its item sets the quest's variable)
    spec = terminals.plan(RANGEKEEPER)
    forms = terminals.mod_forms(gd, pr, {B.key: stub, B.skey: srec})
    forms.pr = _WithScript(pr, B.skey, srec)
    forms.pr.records[B.key] = stub
    made = terminals.records(gd, forms, spec)
    from activity import _new_key
    tkeys = {}
    for r in made['notes'] + made['menus'] + [made['terminal']]:
        k = _new_key(pr)
        tkeys[recordio.field(r, 'EDID')] = k
    made = terminals.records(gd, forms, spec, tkeys)
    for r in made['notes'] + made['menus'] + [made['terminal']]:
        o.append({'op': 'record', 'key': tkeys[recordio.field(r, 'EDID')], 'record': r})
    tp = P['spots']['gunner']
    o.append({'op': 'place', 'cell': tp['cell'], 'key': _new_key(pr), 'ref': {'base': tkeys[spec['edid']],
              'p': [tp['p'][0] - 180.0, tp['p'][1], tp['p'][2] - 4.0, 0.0, 0.0, tp['p'][3]], 's': 1.0}})
    rep['made'].append(spec['edid'])
    T, lines = _lines(gd, pr, B, srec, s_rec)
    o += [{'op': 'record', 'key': k, 'record': r} for k, r in T]
    rep['made'] += [recordio.field(r, 'EDID') for _k, r in T]
    pr.apply(LABEL, o)
    full = json.loads(json.dumps(plain))
    errors = aq.compile_quest(full, aq.ModForms(gd, pr))
    if errors:
        raise ValueError('%s: %s' % (QUEST, errors))
    pr.apply(LABEL, [{'op': 'record', 'key': B.key, 'record': qr.quest_record(full)}] +
             [{'op': 'record_new', 'record': aq._compiled_line(gd, pr, l)} for l in lines], merge=True)
    rep.update({'lines': len(lines), 'people': len(B.people), 'named': sorted(v['subs'][0]['value'] for v in B.ext.values())})
    return rep


def _vars(srec):
    out, last = {}, None
    for sub in srec['subs']:
        if sub['tag'] == 'SLSD':
            last = next(f['value'] for f in sub['fields'] if f.get('name') == 'Index')
        elif sub['tag'] == 'SCVR' and last is not None:
            out[sub['value'].lower()] = last
    return out


def _lines(gd, pr, B, srec, stand):
    import api_quests as aq
    import questrec as qr
    import repstanding as RS
    from activity import _new_key
    G = qr.GREETING
    recs, lines, T = [], [], {}
    av = lambda e: gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'AVIF' and gd.edid(f) == e))
    SK = {'Speech': (43, av('AVSpeech')), 'Barter': (32, av('AVBarter')), 'Repair': (39, av('AVRepair'))}
    V, SV = _vars(srec), _vars(stand)
    sq = _mod_key(pr, RS.QUEST, 'QUST')
    qv = lambda var, op, v: _cond(79, op, v, B.key, V[var])
    sv = lambda var, op, v: _cond(79, op, v, sq, SV[var])
    stage = lambda op, v: _cond(58, op, v, B.key)
    sk = lambda s, op, v: _cond(14, op, v, SK[s][0], 0, 1)
    kala = lambda n: _cond(47, '>=', n, gd.key(gd.from_key(gd.key(next(f for f, (i, r) in gd.forms.items() if (f & 0xFFFFFF) == KALA and (f >> 24) == 0)))), 0, 1)
    caps = gd.key(next(f for f, (i, r) in gd.forms.items() if (f & 0xFFFFFF) == KALA and (f >> 24) == 0))
    kala = lambda n: _cond(47, '>=', n, caps, 0, 1)

    def topic(name, words):
        if name not in T:
            k = _new_key(pr)
            recs.append((k, qr.topic_record({'edid': 'FOLabMissouriTopic%s' % name, 'name': words, 'priority': 50.0, 'kind': 0,
                                             'quests': [{'quest': B.key, 'links': []}]})))
            T[name] = k
        return T[name]

    def line(tp, who, words, conds=(), end='', skill=None, choices=()):
        l = aq.new_line_plain(gd, pr, tp, B.key, who, words, conditions=list(conds))
        if skill:
            l['skill'] = SK[skill][1]
        if end:
            l['end'] = {'source': end, 'parts': None}
        l['choices'] = list(choices)
        lines.append(l)

    def check(tp, who, skill, need, passed, failed, on_pass='', conds=(), on_fail='', fail_choices=()):
        line(tp, who, passed, [sk(skill, '>=', need)] + list(conds), on_pass, skill)
        line(tp, who, failed, list(conds), on_fail, skill, fail_choices)
    P = B.people
    Q = QUEST
    setv = lambda var, v=1: 'set %s.%s to %s' % (Q, var, v)
    gup = lambda n: RS.bump('guard', n) + '\nAddReputation %s 1 1' % REP[0]
    # the Captain
    cap = P['captain']
    t_trust, t_serv, t_lever, t_tell = (topic('Trust', W['cap_trust_ask']), topic('Service', W['cap_service']),
                                        topic('Lever', W['cap_lever']), topic('Tell', W['cap_tell']))
    no_trust = [qv('trust', '=', 0)]
    line(G, cap, W['cap_after'], [qv('ready', '=', 1), qv('told', '!=', 0)])
    line(G, cap, W['cap_hi'], [], choices=[t_trust, t_serv, t_lever, t_tell, topic('Join', W['join']), topic('Suit', W['suit']), topic('Heir', W['heir'])])
    line(t_trust, cap, W['cap_trust_yes'], no_trust + [sk('Speech', '>=', TRUST_SPEECH), sv('bandcourt', '>=', 3)], setv('trust'), 'Speech')
    line(t_trust, cap, W['cap_trust_no'], no_trust, '', 'Speech')
    line(t_serv, cap, W['cap_service_yes'], no_trust + [sv('guard', '>=', GUARD_FRIEND)], setv('trust'))
    line(t_serv, cap, W['cap_trust_no'], no_trust)
    line(t_lever, cap, W['cap_lever_yes'], no_trust + [qv('knows', '=', 1), sk('Speech', '>=', LEVER_SPEECH)], setv('trust'), 'Speech')
    line(t_lever, cap, W['cap_lever_no'], no_trust + [qv('knows', '=', 1)], 'StartCombat player\n' + RS.bump('guard', -20), 'Speech')
    line(t_tell, cap, W['cap_tell_yes'], [qv('ready', '=', 1), qv('told', '=', 0)], setv('told', 1) + '\nSetStage %s 70' % Q)
    # the Lieutenant, the Chief, the gunner, the Guardsmen
    t_light = topic('Light', W['light'])
    line(G, P['chief'], W['chief_hi'], [qv('light', '=', 0)], choices=[t_light])
    line(G, P['chief'], W['chief_hi'])
    check(t_light, P['chief'], 'Repair', LIGHT_REPAIR, W['light_yes'], W['light_no'], setv('light') + '\n' + gup(10), [qv('light', '=', 0)])
    gun = P['gunner']
    t_truth, t_friend, t_mount, t_fire = (topic('Truth', W['ik_truth']), topic('Friend', W['ik_friend']), topic('Mount', W['mount']),
                                          topic('Fire', W['ik_fire']))
    targets = [topic('At%s' % n, W['fire_%s' % n.lower()]) for n in ('Flotilla', 'Kahala', 'Court', 'Crater')]
    t_hold = topic('Hold', W['fire_hold'])
    line(G, gun, W['ik_hi'], [], choices=[t_truth, t_friend, t_mount, t_fire])
    check(t_truth, gun, 'Speech', IKAIKA_SPEECH, W['ik_truth_yes'], W['ik_truth_no'], setv('knows'), [qv('knows', '=', 0)])
    line(t_friend, gun, W['ik_friend_yes'], [qv('knows', '=', 0), sv('guard', '>=', GUARD_FRIEND)], setv('knows'))
    check(t_mount, gun, 'Repair', MOUNT_REPAIR, W['mount_yes'], W['mount_no'], setv('mount') + '\n' + gup(10), [qv('mount', '=', 0)])
    line(t_fire, gun, W['ik_fire_hi'], [qv('ready', '=', 1), qv('salvos', '>', 0)], choices=targets + [t_hold])
    line(t_fire, gun, W['empty'], [qv('ready', '=', 1)])
    for code, tp in enumerate(targets, 1):
        line(tp, gun, W['fired'], [qv('salvos', '>', 0)], setv('fire', code))
    line(t_hold, gun, W['cap_after'])
    for k, words in GREET.items():                       # (everyone of the Order has a word of their own)
        line(G, P[k], words)
    # joining the Order: Speech, standing (the court's favour or the Guard's friendship), a deed
    t_join, t_suit, t_heir = topic('Join', W['join']), topic('Suit', W['suit']), topic('Heir', W['heir'])
    deed = [qv('light', '=', 1) | {'or': True}, qv('mount', '=', 1) | {'or': True}, qv('raid_done', '=', 1) | {'or': True}, qv('ready', '=', 1)]
    stand = [sv('bandcourt', '>=', 3) | {'or': True}, sv('guard', '>=', GUARD_FRIEND)]
    line(t_join, cap, W['join_yes'], [qv('squire', '=', 0), sk('Speech', '>=', JOIN_SPEECH)] + stand + deed,
         setv('squire') + '\nSetStage %s 92' % Q, 'Speech')
    line(t_join, cap, W['join_no'], [qv('squire', '=', 0)], '', 'Speech')
    line(t_suit, cap, W['suit_yes'], [qv('squire', '=', 1), qv('suit', '=', 0), qv('late_deed', '=', 1) | {'or': True}, qv('ready', '=', 1)],
         setv('suit') + '\nSetStage %s 94' % Q)
    line(t_suit, cap, W['suit_no'], [qv('squire', '=', 1), qv('suit', '=', 0)])
    line(t_heir, cap, W['heir_yes'], [qv('squire', '=', 1), qv('suit', '=', 0), qv('heir', '=', 1)], setv('suit') + '\nSetStage %s 96' % Q)
    # the Kalihi lord
    lord = P['lord']
    t_lg, t_lp, t_lc, t_lb = (topic('LordGuns', W['lord_guns']), topic('LordPay', W['lord_pay']), topic('LordCourt', W['lord_court']),
                              topic('LordBlock', W['lord_block']))
    t_bp, t_bb, t_bs = topic('BlockPay', W['block_pay']), topic('BlockBarter', W['block_barter']), topic('BlockSecret', W['block_secret'])
    order = lambda: setv('ordered') + '\nset %s.block_day to GameDaysPassed + %d\nSetStage %s 40' % (Q, BLOCK_DAYS, Q)
    line(G, lord, W['lord_ready'], [qv('block_done', '=', 1), stage('<', 45)])
    line(G, lord, W['lord_hi'], [], choices=[t_lg, t_lp, t_lc, t_lb])
    check(t_lg, lord, 'Barter', LORD_BARTER, W['lord_guns_yes'], W['lord_guns_no'], setv('knows'), [qv('knows', '=', 0)])
    line(t_lp, lord, W['lord_pay_yes'], [qv('knows', '=', 0), kala(LORD_KALA)], 'player.RemoveItem Caps001 %d\n%s' % (LORD_KALA, setv('knows')))
    line(t_lc, lord, W['lord_court_yes'], [qv('knows', '=', 0), sv('bandcourt', '>=', 3)], setv('knows'))
    line(t_lb, lord, W['lord_block_hi'], [stage('>=', 30), qv('ordered', '=', 0)], choices=[t_bp, t_bb, t_bs])
    line(t_bp, lord, W['block_pay_yes'], [qv('ordered', '=', 0), kala(BLOCK_KALA)], 'player.RemoveItem Caps001 %d\n%s' % (BLOCK_KALA, order()))
    line(t_bb, lord, W['block_barter_yes'], [qv('ordered', '=', 0), sk('Barter', '>=', BLOCK_BARTER), kala(BLOCK_KALA // 2)],
         'player.RemoveItem Caps001 %d\n%s' % (BLOCK_KALA // 2, order()), 'Barter')
    line(t_bb, lord, W['block_barter_no'], [qv('ordered', '=', 0)], '', 'Barter')
    line(t_bs, lord, W['block_secret_yes'], [qv('ordered', '=', 0)],
         order() + '\n' + setv('promised') + '\nif %s.told == 0\n%s\nendif\nSetStage %s 76' % (Q, setv('told', 4), Q))
    # the pirates' Kahala trader: the dry charges; a dealing captain: the secret sold; a Kahuna's guard: the court told
    trader = _mod_key(pr, TRADER, 'NPC_')
    if trader:
        t_qc, t_qp = topic('Charges', W['qm_charges']), topic('ChargesPay', W['qm_pay'])
        give = lambda: 'player.AddItem FOLabDryCharge %d\n%s' % (CHARGES, setv('bought'))
        line(G, trader, W['qm_charges'], [stage('>=', 30), qv('bought', '=', 0), qv('ready', '=', 0)], choices=[t_qc, t_qp])
        check(t_qc, trader, 'Barter', CHARGE_BARTER, W['qm_charges_yes'], W['qm_charges_no'], give(), [qv('bought', '=', 0)])
        line(t_qp, trader, W['qm_pay_yes'], [qv('bought', '=', 0), kala(CHARGE_KALA)], 'player.RemoveItem Caps001 %d\n%s' % (CHARGE_KALA, give()))
    buyer = _mod_key(pr, SELLS_TO, 'NPC_')
    if buyer:
        t_sell = topic('Sell', W['io_sell'])
        line(G, buyer, W['io_sell'], [qv('ready', '=', 1), qv('told', '=', 0)], choices=[t_sell])
        sold = lambda n: 'player.AddItem Caps001 %d\n%s\nSetStage %s 74' % (n, setv('told', 3), Q)
        line(t_sell, buyer, W['io_sell_yes'], [qv('told', '=', 0), sk('Barter', '>=', SELL_BARTER)], sold(SELL_HIGH), 'Barter')
        line(t_sell, buyer, W['io_sell_no'], [qv('told', '=', 0)], sold(SELL_LOW), 'Barter')
    kg = _mod_key(pr, KAHUNA_GUARD, 'NPC_')
    if kg:
        t_kg = topic('Court', W['kg_tell'])
        line(G, kg, W['kg_tell'], [qv('ready', '=', 1), qv('told', '=', 0)], choices=[t_kg])
        line(t_kg, kg, W['kg_tell_yes'], [qv('told', '=', 0)], setv('told', 2) + '\nSetStage %s 72' % Q)
    return recs, lines
