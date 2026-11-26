"""People worth talking to (the user, 26 Nov 2026: "a lot of the random surfers i find in camps and such have no dialogue
lines, nothing to say, no reason to exist basically ... they can drop tidbits about game lore, or point out a hidden cache
somewhere. maybe just some humor about other npcs ... maybe they give bonuses according to your skills ... for now we just
need the non hostile world to feel like it has a reason to exist").

Who (`POOLS`, by editor ID; a pool is one set of lines said by any of its records, GetIsID OR'd, voiced into every voice
folder they may speak in): the island's surfers, market-goers, stallholders, pier fishers and locals; the Kahuna's court
living in the Moana and Kahuna Palms (guests, retainers, servants, court guards, the watchman); the Kilauea's crowd
(gamblers, dealers, showgirls, bartenders, fight fans, fighters, bouncers); the Huáng's Nongmin (Mandarin, the meaning on
screen in brackets, as huangtalk). Before this, 155 surfers and about 120 more had no greeting at all. Pirates of the Fiends'
factions are hostile and stay out; the pirate traders, the Pearl's people and the named have lines of their own.

What each says (quest `QUEST`, priority `PRIORITY`: over the rumours' 45, so a teller's hints come before the rumours):
- a greeting (only for those with none: `silent`), drawn at random, unless a storm, the night or the Dread Name come first;
- "What's new?": your traits (Dread Name: nervous; Captain's Kin: court gossip; Raised on the Boats: deck talk), how the
  side sees you (both axes: fame and infamy, GetReputationThreshold; favour and suspicion, Your Name on the Water's score),
  the storm, the hour; then gossip about the island's named people and decided lore, at random, each once a day
  (say_once_a_day); then a fallback;
- "Tell me about this place.": by where they stand (the nearest named map marker within its reach, or the place they're
  in), only what's decided (docs/waikiki-lore.md, waikiki-decisions.md, the rumours, the people's backgrounds);
- "Heard anything?" (the rumours' own topic, shared): a favour for a skill once a pool every `COOLDOWN` days (Survival:
  fish; Medicine: a cut seen to, food; Barter: +`BARTER_UP` Barter for a day; Repair: scrap), then the caches (`CACHES`):
  real finds the mod has placed (start-scene bags, lookouts and roof camps, finds by sunken wrecks), each told once
  (hint<n>), its nearest map marker shown on your map; the harder ones need Speech `HINT_SPEECH`. Then the rumours (for
  their tellers) or a fallback.

Companions and romance are the user's later ask (docs/waikiki-decisions.md), not built here.

    plan(gd, pr)       {'rows', 'skipped', 'pools', 'caches', 'markers'}
    apply(pr, gd, P)   one Undo (VOICE; ZH: the Mandarin lines)
    routes()           every pool answers every topic at every point the conditions can be in; hints once each; favours
                       wait their days; the Barter rise goes again a day later (the lines' own conditions and end scripts)
"""
import itertools
import json
import math
import re

import recordio

LABEL = 'People worth talking to'
QUEST, SCRIPT = 'FOLabPeopleTalk', 'FOLabPeopleTalkScript'
VOICE = [QUEST]
ZH = {}
PRIORITY = 46
COOLDOWN, BARTER_UP, HINT_SPEECH, SKILL_AT, BARTER_AT = 2, 5, 50, 40, 50
NEAR = 7000.0                           # (a place's lines within this of its map marker)
TOPICS = {'new': ('FOLabTalkNew', "What's new?"), 'place': ('FOLabTalkPlace', 'Tell me about this place.')}
HEARD = 'FOLabRumoursAsk'               # (the rumours' "Heard anything?": shared, not a second one)
RUMOURS = 'FOLabRumours'
TELLERS = ('FOLabWaikikiLocal', 'FOLabWaikikiLocal2', 'FOLabMarketGoer', 'FOLabMarketSeller', 'FOLabPierFisher')
NOW, REPS = 'FOLabNameOnWater', {'court': 'FOLabRepCourt', 'pirates': 'FOLabRepPirates', 'huang': 'FOLabRepHuang'}
TRAITS = {'dread': 'FOLabTraitDreadName', 'kin': 'FOLabTraitCaptainsKin', 'boats': 'FOLabTraitRaisedOnTheBoats'}
STORM = 'FOLabStormShelter'
FISH, MEAL, SCRAP = 'FOLabRawReefFish', 'FOLabGrilledReefFish', 'SpareParts'
AV = {'Survival': 'AVThrowing',      # (the game's Survival is the old Throwing value, 44)
       'Medicine': 'AVMedicine', 'Barter': 'AVBarter', 'Repair': 'AVRepair', 'Speech': 'AVSpeech'}
AVI = {'Barter': 32, 'Lockpick': 36, 'Medicine': 37, 'Repair': 39, 'Speech': 43, 'Survival': 44}

# pool -> (editor ID stems, names kept (None: all), language)
POOLS = {
    'island': (('FOLabSurferVSpawn', 'FOLabBeachSurfer', 'FOLabMarketGoer', 'FOLabWaikikiLocal', 'FOLabMarketSeller', 'FOLabPierFisher'),
               None, 'en'),
    'court': (('FOLabCourtGuest', 'FOLabCourtServant', 'FOLabCourtRetainer', 'FOLabCourtGuard', 'FOLabKPCourt', 'FOLabKPWatchman'),
              None, 'en'),
    'casino': (('FOLabKilaueaGambler', 'FOLabKilaueaDealer', 'FOLabKilaueaCrowd', 'FOLabKilaueaShowgirl', 'FOLabKilaueaDancer',
                'FOLabKilaueaBartender', 'FOLabKilaueaFighter', 'FOLabKilaueaBouncer', 'FOLabKilaueaSleeper'), None, 'en'),
    'huang': (('FOLabHuangFolk', 'FOLabHuangFarmer', 'FOLabNongmin'), ('Nongmin', "Gao's Tenant"), 'zh'),
}
COURT_CELLS = {'moana': ('FOLabMoanaFloor',), 'kp': ('FOLabKahunaPalmsFloor',)}

# real finds told of: (pool, kind, near this (x, y), within, Speech needed, words). The find is the mod's container
# nearest the spot within `within`; its nearest map marker is the one shown.
CACHES = [
    ('island', 'bag', (92812, -39453), 400, 0, "Somebody left a bag up on the crater rim above Hanauma Bay. Long climb. Might be worth it."),
    ('island', 'bag', (79848, -39860), 400, 0, "There's a bag lying on the beach down from the Pink Pearl. Nobody's come back for it."),
    ('island', 'bag', (94490, -42675), 400, 0, "Past Hanauma Bay, up the hill, there's a cold camp. Whoever slept there left their bag."),
    ('island', 'high', (-79793, -30574), 400, 0, "Somebody's camp up on a roof by the Kapiolani ferris wheel. Boxes and a bag. Mind the ramps."),
    ('island', 'high', (-13488, -31808), 400, 0, "Up on a roof by Makai Tower, a camp with ammo boxes. Pirate lookouts, maybe. Gone now."),
    ('island', 'high', (-76484, -13730), 400, 0, "Over the Ala Wai boat harbor there's a roof camp. Footlockers, ammo. Some of it's locked."),
    ('island', 'wreck', (-88777, -54784), 600, HINT_SPEECH, "Off the Natatorium, deep down, there's a sunk boat. Boxes still in it. Hold your breath."),
    ('island', 'high', (-59586, -48286), 600, HINT_SPEECH, "Up on Diamond Head's rim there's a locker somebody hid. Old guns, they say. I never made the climb."),
    ('court', 'high', (-91909, -21766), 400, 0, "The guards keep a box on the roof by the Royal Hawaiian. They think nobody knows. Everybody knows."),
    ('court', 'high', (-96812, -23544), 400, 0, "Up at the Royal Hawaiian lookout there's a crate of food. The watch forgets it's there."),
    ('court', 'high', (-59586, -48286), 600, HINT_SPEECH, "A retainer told me there's a locker hidden on Diamond Head's rim. Old guns. Don't say I said."),
    ('casino', 'high', (-106001, -18065), 500, HINT_SPEECH, "Up on the Kilauea's top deck there's a gun cabinet, locked tight. Some high roller's, they say."),
    ('casino', 'high', (-76484, -13730), 400, 0, "A dealer told me there's a roof camp over the Ala Wai boat harbor. Lockers, ammo. She never went."),
    ('casino', 'high', (-96812, -23544), 400, 0, "The Royal Hawaiian lookout keeps a food crate. The watch forgets it. You didn't hear it from me."),
    ('huang', 'high', (131490, 40274), 400, 0, ("Past the Makapuu gate, up the hill, someone left a crate.",
                                              "Guò le Mǎkǎpǔ de mén, shàng shān, yǒu rén liú le yí ge xiāngzi.")),
    ('huang', 'high', (48413, 92810), 400, 0, ("By the Border Post there's a soldier's box. Nobody came back for it.",
                                             "Biānjiè gǎng pángbiān yǒu yí ge bīng de xiāngzi. Méi rén huílai ná.")),
    ('huang', 'high', (124008, 20954), 400, 0, ("On top of the settlers' watchtower there's a box. Climb, if you dare.",
                                              "Liàowàng tǎ shàngmiàn yǒu yí ge xiāngzi. Gǎn pá jiù pá.")),
    ('huang', 'wreck', (106888, 70379), 600, HINT_SPEECH, ("A boat sank off Moana Kai. Under the water there are boxes still.",
                                                         "Mó ā nà kǎi wàimiàn chén le yì tiáo chuán. Shuǐ xià hái yǒu xiāngzi.")),
]

# places: (pool, marker name or cell words, words); tried in this order, the first within NEAR (or in the cell) wins
PLACES = [
    ('island', "Kuliouou Squatters' Camp", "Kuliouou. Don't trust anyone here with a rope. People get sold out of this camp."),
    ('island', 'Pink Pearl Hotel', "The Pink Pearl's the boats' hotel. When a big storm comes, the crews run in and hole up there."),
    ('island', 'Koko Marina', "Koko Marina. The boats haul out here. When a storm comes in, every crew on the coast runs for it."),
    ('island', 'Hanauma Bay', "Hanauma Bay. Old Walt walks the tide line every morning. Says the sea brings in all sorts. People too."),
    ('island', 'Kahala Reef', "The Kahala. Pirates trade outside the walls. Nobody fights on the trade ground. That's the rule."),
    ('island', "Makapu'u Gate", "Makapuu. The Huang's gate. They trade there, polite if you're polite. Don't touch anything."),
    ('island', 'Loa Gate', "Loa Gate's up in the hills. Scoundrels from every side. More men up there than anybody says."),
    ('island', 'Diamond Head', "Diamond Head. Best view on the island from the rim, if you make the climb."),
    ('island', 'The Royal Hawaiian', "Waikiki. The Kahuna's city. No raids here. The court keeps a bargain with the boats, and nobody asks what it costs."),
    ('island', 'Kahuna Palms', "The round hotel at the end of the strip. Kahuna Palms. The dead that walk took it. Ask the court's watchman about it."),
    ('court', 'moana', "The Moana. The court lives here, guests and retainers and all of us. The Kahuna keeps the Royal Hawaiian."),
    ('court', 'kp', "Kahuna Palms. The court took the tower back from the dead. You can still smell them on the stairs."),
    ('casino', None, "The Kilauea. Tallest thing in Waikiki, a volcano on its crown. Kala's what we play for. The Kilauea's own token, once."),
    ('huang', 'Kailua', ("The palace is across the bay, on Mokapu.", "Gōngdiàn zài hǎiwān duìmiàn, zài Mókǎpǔ.")),
    ('huang', "Kane'ohe", ("Good land here. The dukes' plantations.", "Zhèlǐ shì hǎo dì. Shì gōngjué de zhuāngyuán.")),
    ('huang', 'Blue Lagoon', ("Huang land, all of it, from the mountain to the sea.", "Zhèlǐ dōu shì Huáng rén de dì, cóng shān dào hǎi.")),
]
PLACE_ELSE = {
    'island': "Squatters' ground. Nobody owns it, so everybody does. Keep your gear close.",
    'court': "The Kahuna's house. Behave as a guest does.",
    'casino': "The Kilauea. Mind your tokens.",
    'huang': ("Our fields. Our village. Be polite.", "Wǒmen de tián. Wǒmen de cūnzi. Qǐng yǒu lǐmào."),
}

# what's new / greetings: [(conditions, words)]. Conditions: ('storm',), ('night',), ('morning',), ('perk', t),
# ('nw', side, op, v), ('fame', side), ('infamy', side), ('cell', which). 'G' greetings, 'N' news specials,
# 'R' news at random (each once a day), 'E' the news fallback; 'F' favours (skill, gift)
LINES = {
    'island': {
        'G': [([('perk', 'dread')], "Easy. I don't want trouble. Whatever you need, it's yours."),
              ([('storm',)], "Storm's coming in hard. Find a roof."),
              ([('night',)], "Late to be walking round. Pirates like the dark."),
              ([], "Howzit. You look like you just washed in."),
              ([], "Aloha. Don't mind me, I'm watching the swell."),
              ([], "Eh, malihini. You need something?"),
              ([], "Nice day for it. You stopping, or passing through?")],
        'N': [([('perk', 'dread')], "Nothing! Nothing's new. I mind my business, I swear it."),
              ([('perk', 'kin')], "Captain's kin, yeah? Then you've heard the talk. The Missouri's captain tells the Kahuna what suits the captain. Not that I said it."),
              ([('perk', 'boats')], "Eh, deck brother. You've got the walk of the boats. Mind the Flotilla's crews, though. They don't ask before they take."),
              ([('storm',)], "Big blow coming in. The boats are running for Koko Marina already."),
              ([('infamy', 'court')], "You're the one from the stories. The bad ones. Stay over there."),
              ([('fame', 'court')], "You're the one who's been helping round here, yeah? Mahalo."),
              ([('nw', 'court', '<=', -25)], "Word is the court's watching you. I'd keep my head down, if I were you."),
              ([('nw', 'court', '>=', 25)], "People say you're well thought of at the court. Lucky you."),
              ([('nw', 'pirates', '>=', 25)], "Pirates on the road say your name like a curse. Good. Keep it that way."),
              ([('morning',)], "Waves were glassy at dawn. You missed it.")],
        'R': ["Fight night soon. All Waikiki turns out when the Kahuna's fighters go at it.",
              "Doc Albright sewed up three losers after the last fight night. She says she loves a quiet one. Never gets one.",
              "Tom Kowalski and Linda Moreno are at it again. He says she steals his customers. She sells what his guns go through.",
              "Ray Delgado's prices follow the boats. Boats late, prices up. He says it's not his fault. It never is.",
              "Old Walt Pruitt at Hanauma says the sea brought him a boot once, with the foot still in it.",
              "Zhao Lei, the Huang's gate guard at Makapuu, doesn't say much. He doesn't need to.",
              "The toll post takes its cut of the coast road. Then the pirates take the rest. Everyone blames someone else.",
              "The Pink Pearl's full of boat crews between tides. Pirate hotel, pirate prices."],
        'E': "Same as always. Sun, surf, and somebody else's trouble.",
        'F': {'Survival': ("You read the reef like a fisher. The run's on. Take a couple, I've got plenty.", 'fish'),
              'Medicine': ("You know doctoring? Look at this cut for me. That's better. Mahalo. Here, eat something.", 'meal'),
              'Barter': ("You've got a trader's eye. Tell the stallholders I said to give you a fair price today.", 'barter'),
              'Repair': ("You're handy, yeah? My board rack's busted. There. Take this scrap, I don't need it.", 'scrap')},
        'H': "Nothing worth telling. Ask me another day.",
    },
    'court': {
        'G': [([('perk', 'dread')], "Oh. You. Please, go on through."),
              ([('night',)], "The house is asleep. Mostly. Keep your voice down."),
              ([], "Aloha. You're a long way from the stairs."),
              ([], "Mind the floors. They've just been polished."),
              ([], "Another guest of the court? Welcome."),
              ([], "Keep your voice down. The court hears everything.")],
        'N': [([('perk', 'dread')], "Nothing new. Nothing at all. I've work to do."),
              ([('perk', 'kin')], "A captain's kin. Then you'll have heard what the house whispers. The Missouri's captain tells the Kahuna only what suits him."),
              ([('perk', 'boats')], "You talk like a deckhand. Mind it up here. The court doesn't love the boats, whatever it pays them."),
              ([('storm',)], "The storm's kept everyone indoors. The Kahuna wants a feast to pass the time."),
              ([('infamy', 'court')], "The guards have your description. I'd be quick, if I were you."),
              ([('fame', 'court')], "The court speaks well of you. Doors open for people like that."),
              ([('nw', 'court', '<=', -25)], "Someone's been asking the stewards about you. I didn't tell them anything."),
              ([('nw', 'court', '>=', 25)], "The retainers say the Kahuna's heard your name. Kindly, for now.")],
        'R': ["There's a feast every time the Kahuna's in good spirits. That's most nights.",
              "Fight night. The Kahuna's fighters, koa clubs, the whole house watching. Doctor Albright sews up whoever loses.",
              "The Kahuna's Guard at the Royal Hawaiian would stand in the sea if he told them to.",
              "The guest rooms are full. Everyone wants to be near the court.",
              "Tom Kowalski the gunsmith carves the court's clubs. He says guns run out of bullets, a club never does."],
        'E': "Nothing a guest needs to worry about.",
        'F': {'Medicine': ("You've a steady hand. Would you look at my burn? Kitchen work. Thank you. Take something from the feast.", 'meal'),
              'Repair': ("The dumbwaiter's jammed again. You can fix it? Bless you. Here, the steward's scrap, he'll never miss it.", 'scrap')},
        'H': "Nothing I'd repeat in this house.",
    },
    'casino': {
        'G': [([('perk', 'dread')], "Hey, no trouble. The table's yours if you want it."),
              ([('storm',)], "Storm outside, so the tables are full. Best night of the season."),
              ([], "Feeling lucky? Everybody here is, till they aren't."),
              ([], "Tokens on the table, or keep walking."),
              ([], "Kala's kala. Spend it."),
              ([], "Fight's later. Get a good spot.")],
        'N': [([('perk', 'dread')], "Nothing's new. I'm just here to play. Honest."),
              ([('perk', 'kin')], "Captain's kin, eh? Then you know kala's only good because the court says it is. Every token here is the court's promise."),
              ([('perk', 'boats')], "Boat crews come in flush with cells and leave without them. Pull up a chair, deck brother."),
              ([('storm',)], "Big storm. Nobody's leaving, so everybody's betting."),
              ([('infamy', 'court')], "The bouncers know your face. Not in a good way."),
              ([('fame', 'court')], "Word at the tables is you're a friend of the court. The dealers will be nice to you. Nicer."),
              ([('night',)], "Night's when the money moves. Watch the high tables.")],
        'R': ["Kala started here, you know. The Kilauea's machine tokens. Now the whole court spends them.",
              "Fight night at the Kahuna's, then everyone comes here to lose their winnings.",
              "The showgirls get tipped better than the dealers. The dealers know it.",
              "The Huang pay in tongbao. Deal with them and you'll want the money changer at Makapuu.",
              "Pirate crews count in cells, not kala. Four kala a cell at their traders."],
        'E': "Only gossip I've got is who lost what. You don't want it.",
        'F': {'Barter': ("You count like a dealer. Here's a tip: everyone haggles today, so you haggle harder.", 'barter'),
              'Medicine': ("You know cuts? Patch me up before the next bout. Thanks. Take this, I can't eat before a fight.", 'meal')},
        'H': "Nothing worth a token. Ask me another night.",
    },
    'huang': {
        'G': [([('perk', 'dread')], ("Please, take what you need. Don't hurt anyone.", "Qǐng, nǐ yào shénme jiù ná. Bié shāng rén.")),
              ([('storm',)], ("A big storm. Get inside.", "Dà fēngbào. Kuài jìn wū.")),
              ([], ("Outsider. Have you eaten?", "Wàirén. Chī le ma?")),
              ([], ("Walk carefully. This is An land.", "Xiǎoxīn zǒu. Zhè shì Ān jiā de dì.")),
              ([], ("The fields need rain.", "Tiándì xūyào yǔ.")),
              ([], ("Mm. You again.", "Èn. Yòu shì nǐ."))],
        'N': [([('perk', 'dread')], ("Nothing. Nothing is new. Please go.", "Méi shénme. Méi shénme xīn de. Qǐng zǒu ba.")),
              ([('perk', 'kin')], ("A captain's kin? The court and the pirates are friends, they say.", "Chuánzhǎng de qīnqi? Tīngshuō cháotíng hé hǎidào shì péngyou.")),
              ([('perk', 'boats')], ("You talk like the boat people. The landlords like them. We don't.", "Nǐ shuōhuà xiàng chuán shàng de rén. Dìzhǔ xǐhuan tāmen. Wǒmen bù xǐhuan.")),
              ([('storm',)], ("The storm will flatten the maize.", "Fēngbào huì bǎ yùmǐ guā dǎo.")),
              ([('infamy', 'huang')], ("People here know what you did. Go away.", "Zhèlǐ de rén zhīdào nǐ zuò le shénme. Zǒu kāi.")),
              ([('fame', 'huang')], ("You are welcome here. People say so.", "Zhèlǐ huānyíng nǐ. Dàjiā dōu zhème shuō.")),
              ([('nw', 'huang', '<=', -25)], ("You have lost face here. People watch you.", "Nǐ zài zhèlǐ diū le miànzi. Rénmen dōu kàn zhe nǐ.")),
              ([('nw', 'huang', '>=', 25)], ("The elders speak well of you. That is rare.", "Zhǎnglǎo shuō nǐ hǎo. Zhè hěn shǎo jiàn."))],
        'R': [("The landlords deal with the pirates. Their plantations grow rich on it.", "Dìzhǔ gēn hǎidào zuò mǎimai. Tāmen de zhuāngyuán yīncǐ fā cái."),
              ("The Ship-King lives in the palace on Mokapu.", "Chuánwáng zhù zài Mókǎpǔ de gōngdiàn lǐ."),
              ("The founder came on a ship. We remember him at the freighter.", "Zǔxiān shì zuò chuán lái de. Wǒmen zài huòchuán shàng jìniàn tā."),
              ("Tongbao, not kala. Kala is the court's money.", "Yào tóngbǎo, bú yào kǎlā. Kǎlā shì cháotíng de qián."),
              ("Listen to our radio. Songs from home.", "Tīng wǒmen de diàntái ba. Jiāxiāng de gē.")],
        'E': ("Nothing new. The maize grows.", "Méi shénme xīn de. Yùmǐ zài zhǎng."),
        'F': {'Repair': (("Our water pump is broken. You can fix it? Good. Take this.", "Wǒmen de shuǐbèng huài le. Nǐ néng xiū ma? Hǎo. Ná zhe."), 'scrap'),
              'Medicine': (("My son cut his hand. Can you look? Thank you. Eat this.", "Wǒ érzi gē shāng le shǒu. Nǐ néng kàn kan ma? Xièxie. Chī ba."), 'meal')},
        'H': ("Nothing I can tell an outsider.", "Méi shénme kěyǐ gàosu wàirén de."),
    },
}
GIFT = {'fish': 'player.AddItem %s 2' % FISH, 'meal': 'player.AddItem %s 1' % MEAL, 'scrap': 'player.AddItem %s 3' % SCRAP}
FAVOUR_AT = {'Survival': SKILL_AT, 'Medicine': SKILL_AT, 'Repair': SKILL_AT, 'Barter': BARTER_AT}


def said(words):
    """What goes on screen: English, or the Huáng's pinyin with the meaning."""
    if isinstance(words, tuple):
        import huangland
        return huangland.shown(words[0], words[1])
    return words


def _zh():
    for p in LINES.values():
        for w in _all_words(p):
            if isinstance(w, tuple):
                ZH[said(w)] = w[1]
    for c in CACHES + PLACES:
        if isinstance(c[-1], tuple):
            ZH[said(c[-1])] = c[-1][1]
    for w in PLACE_ELSE.values():
        if isinstance(w, tuple):
            ZH[said(w)] = w[1]


def _all_words(p):
    out = [w for _c, w in p['G']] + [w for _c, w in p['N']] + list(p['R']) + [p['E'], p['H']]
    out += [w for w, _g in p['F'].values()]
    return out


# ---------- the lines, as data (one list the step, the test and routes all use) ----------

def lines_spec():
    """[(pool, topic, words, conditions, end, flags, speakers)]: topic 'G', 'new', 'place', 'heard'; speakers 'silent' (only
    those with no greeting of their own) or 'all'; flags of the INFO; end a result script (with {hint}/{marker} filled by
    apply). In the order the game tries them."""
    L = []
    q = QUEST
    for pool, p in LINES.items():
        gr = p['G']
        sp = [x for x in gr if x[0]]
        rn = [x for x in gr if not x[0]]
        for c, w in sp:
            L.append((pool, 'G', w, c, '', {}, 'silent'))
        for n, (c, w) in enumerate(rn):
            L.append((pool, 'G', w, c, '', {'random': True, 'random_end': n == len(rn) - 1}, 'silent'))
        for c, w in p['N']:
            L.append((pool, 'new', w, c, '', {'say_once_a_day': True}, 'all'))
        for n, w in enumerate(p['R']):
            L.append((pool, 'new', w, [], '', {'random': True, 'random_end': n == len(p['R']) - 1, 'say_once_a_day': True}, 'all'))
        L.append((pool, 'new', p['E'], [], '', {}, 'all'))
        for where, w in [(x[1], x[2]) for x in PLACES if x[0] == pool]:
            c = [('cell', where)] if where in COURT_CELLS else [('near', where)] if where else []
            L.append((pool, 'place', w, c, '', {}, 'all'))
        L.append((pool, 'place', PLACE_ELSE[pool], [], '', {}, 'all'))
        for skill, (w, gift) in p['F'].items():
            end = 'set %s.ready_%s to 0\nset %s.next_%s to GameDaysPassed + %d\n' % (q, pool, q, pool, COOLDOWN)
            if gift == 'barter':
                end += ('if %s.barter_on == 0\n\tplayer.ModAV Barter %d\n\tset %s.barter_on to 1\nendif\n'
                        'set %s.barter_until to GameDaysPassed + 1' % (q, BARTER_UP, q, q))
            else:
                end += GIFT[gift]
            L.append((pool, 'heard', w, [('ready', pool), ('skill', skill, FAVOUR_AT[skill])], end, {}, 'all'))
        hints = [(n, c) for n, c in enumerate(CACHES) if c[0] == pool]
        for i, (n, c) in enumerate(hints):
            conds = [('hint', n)] + ([('skill', 'Speech', c[4])] if c[4] else [])
            L.append((pool, 'heard', c[5], conds, 'set %s.hint%d to 1\nShowMap {marker%d}' % (q, n, n),
                      {'random': True, 'random_end': i == len(hints) - 1}, 'all'))
        L.append((pool, 'heard', p['H'], [], '', {}, 'nontellers' if pool == 'island' else 'all'))
    return L


def quest_script():
    v = ['scn %s' % SCRIPT] + ['short hint%d' % n for n in range(len(CACHES))]
    v += ['short ready_%s' % p for p in LINES] + ['float next_%s' % p for p in LINES] + ['short barter_on', 'float barter_until', '']
    b = ['Begin GameMode']
    for p in LINES:
        b += ['\tif ready_%s == 0' % p, '\t\tif GameDaysPassed >= next_%s' % p, '\t\t\tset ready_%s to 1' % p, '\t\tendif', '\tendif']
    b += ['\tif barter_on == 1', '\t\tif GameDaysPassed >= barter_until', '\t\t\tplayer.ModAV Barter -%d' % BARTER_UP,
          '\t\t\tset barter_on to 0', '\t\tendif', '\tendif', 'End', '']
    return '\n'.join(v + b)


# ---------- where ----------

def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _edid(pr, k):
    return recordio.field(pr.records.get(k) or {'subs': []}, 'EDID') or ''


def _speakers(gd, pr):
    """{pool: {'all': [keys], 'silent': [keys]}}: the mod's NPC_ of each pool; silent ones have no greeting."""
    import peopletalk
    greet = peopletalk._topic(gd, 'GREETING')
    has = set()
    for r in pr.records.values():
        if r.get('type') == 'INFO' and r.get('topic') == greet:
            for s in r['subs']:
                if s['tag'] == 'CTDA':
                    v = {f.get('name'): f.get('value') for f in s.get('fields', [])}
                    if v.get('Function') == 72 and isinstance(v.get('Parameter 1'), str):
                        has.add(v['Parameter 1'])
    out = {}
    for pool, (stems, names, _lang) in POOLS.items():
        keys = sorted(k for k, r in pr.records.items() if r.get('type') == 'NPC_' and k.startswith('+') and _edid(pr, k).startswith(stems)
                      and (names is None or recordio.field(r, 'FULL') in names))
        out[pool] = {'all': keys, 'silent': [k for k in keys if k not in has]}
    tellers = {k for k in out['island']['all'] if _edid(pr, k) in TELLERS}
    out['island']['nontellers'] = [k for k in out['island']['all'] if k not in tellers]
    return out


def _markers(pr):
    out = {}
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            m = r.get('marker')
            name = m.get('name') if isinstance(m, dict) else m
            if name and not r.get('removed') and r.get('p'):
                out.setdefault(str(name), (ck, rk, r.get('edid'), r['p']))
    return out


def marker_edid(name):
    return 'FOLabMarker%sREF' % re.sub(r'[^A-Za-z0-9]', '', name)


def plan(gd, pr):
    rows, skipped = [], []
    S = _speakers(gd, pr)
    for pool, s in S.items():
        rows.append({'pool': pool, 'people': len(s['all']), 'silent': len(s['silent'])})
        if not s['all']:
            skipped.append('no %s people in the mod' % pool)
    for e, t in [(QUEST, 'QUST')]:
        if _mod_key(pr, e, t):
            skipped.append('the mod has %s already' % e)
    for e, t in [(RUMOURS, 'QUST'), (HEARD, 'DIAL'), (NOW, 'QUST'), (STORM, 'GLOB'), (FISH, None), (MEAL, None)] + \
            [(v, 'REPU') for v in REPS.values()] + [(v, 'PERK') for v in TRAITS.values()]:
        if not _mod_key(pr, e, t):
            skipped.append('no %s in the mod' % e)
    M = _markers(pr)
    want = {x[1] for x in PLACES if x[1] and x[1] not in COURT_CELLS}
    for w in sorted(want):
        if w not in M:
            skipped.append('no map marker %s' % w)
    # the caches: the mod's containers outside nearest each spot
    finds = []
    for ck, c in pr.cells.items():
        if ck.startswith('+'):
            continue
        for rk, r in (c.get('refs') or {}).items():
            b = r.get('base')
            if r.get('removed') or not b or not r.get('p'):
                continue
            t = (pr.records.get(b) or {}).get('type') if b.startswith('+') else _tag(gd, b)
            if t == 'CONT' and not _edid_any(gd, pr, b).endswith('Chest'):
                finds.append((ck, rk, r['p']))
    caches = []
    for n, (pool, kind, (x, y), within, speech, words) in enumerate(CACHES):
        got = min(finds, key=lambda f: math.hypot(f[2][0] - x, f[2][1] - y)) if finds else None
        if not got or math.hypot(got[2][0] - x, got[2][1] - y) > within:
            skipped.append('cache %d (%s): no find within %d of %s' % (n, pool, within, (x, y)))
            continue
        name, (mck, mrk, medid, mp) = min(M.items(), key=lambda kv: math.hypot(kv[1][3][0] - x, kv[1][3][1] - y))
        caches.append({'n': n, 'pool': pool, 'kind': kind, 'find': got[1], 'cell': got[0], 'p': [round(v) for v in got[2][:3]],
                       'marker': name, 'marker_ref': mrk, 'marker_cell': mck, 'marker_edid': medid or marker_edid(name),
                       'named': bool(medid), 'from_marker': round(math.hypot(mp[0] - x, mp[1] - y))})
        rows.append({'cache': n, 'pool': pool, 'kind': kind, 'p': caches[-1]['p'], 'marker': name, 'from marker': caches[-1]['from_marker']})
    marks = {}
    for w in want:
        if w in M:
            ck, rk, e, p = M[w]
            marks[w] = {'cell': ck, 'ref': rk, 'edid': e or marker_edid(w), 'named': bool(e)}
    for c in caches:
        marks.setdefault(c['marker'], {'cell': c['marker_cell'], 'ref': c['marker_ref'], 'edid': c['marker_edid'], 'named': c['named']})
    cells = {}
    for k, r in pr.records.items():
        if r.get('type') == 'CELL' and k.startswith('+'):
            e = recordio.field(r, 'EDID') or ''
            for which, words in COURT_CELLS.items():
                if e.startswith(words):
                    cells.setdefault(which, []).append(k)
    for which in COURT_CELLS:
        if which not in cells:
            skipped.append('no %s places' % which)
    return {'rows': rows, 'skipped': skipped, 'pools': S, 'caches': caches, 'markers': marks, 'cells': cells}


def _tag(gd, b):
    try:
        return gd.forms[gd.from_key(b)][1].tag
    except Exception:
        return '?'


def _edid_any(gd, pr, b):
    if b.startswith('+'):
        return _edid(pr, b)
    try:
        return gd.edid(gd.from_key(b)) or ''
    except Exception:
        return ''


# ---------- the step ----------

def _cond(fn, op, value, p1=0, p2=0, run=0, orr=False):
    op = '=' if op == '==' else op
    return {'or': orr, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def apply(pr, gd, P=None):
    import api_quests as aq
    import api_scripts
    import questrec as qr
    import scriptc
    import tes4
    from activity import _new_key
    P = P or plan(gd, pr)
    if P['skipped']:
        raise ValueError('; '.join(P['skipped']))
    _zh()
    S, caches, marks = P['pools'], {c['n']: c for c in P['caches']}, P['markers']
    out, rep = [], {'made': [], 'pools': {p: {'people': len(s['all']), 'silent': len(s['silent'])} for p, s in S.items()}}
    # the map markers named (persistent) as the rumours name theirs
    for name, m in sorted(marks.items()):
        if not m['named']:
            out.append({'op': 'ref_set', 'cell': m['cell'], 'ref': m['ref'], 'set': {'edid': m['edid'], 'persistent': True}})
            m['named'] = True
    # the quest and its script, the two topics; the rumours' topic gains this quest
    sc = api_scripts.scripts()
    qkey, skey = _new_key(pr), _new_key(pr)
    quest = qr.quest_record({'edid': QUEST, 'script': skey, 'name': '', 'flags': {'start_enabled': True}, 'priority': PRIORITY,
                             'delay': 5.0, 'stages': [], 'objectives': []})
    c = sc.compile(quest_script(), skey, 'quest', {qkey: quest})
    if not hasattr(c, 'subrecords'):
        raise ValueError('%s: %s' % (SCRIPT, c))
    srec = sc._record_of(c, SCRIPT)
    out += [{'op': 'record', 'key': skey, 'record': srec}, {'op': 'record', 'key': qkey, 'record': quest}]
    rep['made'] += [QUEST, SCRIPT]
    V = {}
    last = None
    for s in srec['subs']:
        if s['tag'] == 'SLSD':
            last = next(f['value'] for f in s['fields'] if f.get('name') == 'Index')
        elif s['tag'] == 'SCVR' and last is not None:
            V[s['value'].lower()] = last
    tkeys = {}
    for t, (edid, prompt) in TOPICS.items():
        tkeys[t] = _new_key(pr)
        out.append({'op': 'record', 'key': tkeys[t], 'record': qr.topic_record({'edid': edid, 'name': prompt, 'priority': 50.0, 'kind': 0,
                                                                                 'flags': {'top_level': True},
                                                                                 'quests': [{'quest': qkey, 'links': []}]})})
        rep['made'].append(edid)
    hk = _mod_key(pr, HEARD, 'DIAL')
    heard = qr.topic_plain(json.loads(json.dumps(pr.records[hk])))
    if not any(x['quest'] == qkey for x in heard['quests']):
        heard['quests'].append({'quest': qkey, 'links': []})
    hrec = qr.topic_record(heard)
    hrec['src'] = pr.records[hk].get('src', '')
    out.append({'op': 'record', 'key': hk, 'record': hrec})
    tkeys['heard'] = hk
    # the conditions
    now = _mod_key(pr, NOW, 'QUST')
    nv = {}
    if now:
        ns = recordio.field(pr.records[now], 'SCRI')
        last = None
        for s in pr.records[ns]['subs']:
            if s['tag'] == 'SLSD':
                last = next(f['value'] for f in s['fields'] if f.get('name') == 'Index')
            elif s['tag'] == 'SCVR' and last is not None:
                nv[s['value'].lower()] = last
    storm = _mod_key(pr, STORM, 'GLOB')
    avk = lambda e: gd.key(next(f for f, (i, r) in gd.forms.items() if r.tag == 'AVIF' and gd.edid(f) == e))
    marker_key = {name: m['ref'] for name, m in marks.items()}

    def conds(cs):
        o = []
        for c in cs:
            k = c[0]
            if k == 'storm':
                o.append(_cond(74, '==', 1, storm))
            elif k == 'night':                      # (21:00 to 05:00: two conditions OR'd)
                o += [_cond(18, '>=', 21, orr=True), _cond(18, '<', 5)]
            elif k == 'morning':
                o += [_cond(18, '>=', 5), _cond(18, '<', 11)]
            elif k == 'perk':
                o.append(_cond(449, '==', 1, _mod_key(pr, TRAITS[c[1]], 'PERK'), 0, 1))
            elif k == 'nw':
                o.append(_cond(79, c[2], c[3], now, nv[c[1]]))
            elif k == 'fame':
                o.append(_cond(575, '>=', 2, _mod_key(pr, REPS[c[1]], 'REPU'), 1))
            elif k == 'infamy':
                o.append(_cond(575, '>=', 2, _mod_key(pr, REPS[c[1]], 'REPU'), 0))
            elif k == 'near':
                o.append(_cond(1, '<', NEAR, marker_key[c[1]]))
            elif k == 'cell':
                cl = P['cells'][c[1]]
                o += [_cond(67, '==', 1, ck, orr=n < len(cl) - 1) for n, ck in enumerate(cl)]
            elif k == 'ready':
                o.append(_cond(79, '==', 1, qkey, V['ready_' + c[1]]))
            elif k == 'hint':
                o.append(_cond(79, '==', 0, qkey, V['hint%d' % c[1]]))
            elif k == 'skill':
                o.append(_cond(14, '>=', c[2], AVI[c[1]], 0, 1))
        return o
    lines, skipped = [], []
    for pool, topic, words, cs, end, flags, who in lines_spec():
        if any(c[0] == 'hint' and c[1] not in caches for c in cs):
            skipped.append('hint %d' % next(c[1] for c in cs if c[0] == 'hint'))
            continue
        keys = S[pool][who]
        if not keys:
            continue
        speakers = [_cond(72, '==', 1, k, orr=n < len(keys) - 1) for n, k in enumerate(keys)]
        tp = qr.GREETING if topic == 'G' else tkeys[topic]
        l = aq.new_line_plain(gd, pr, tp, qkey, None, said(words), conditions=speakers + conds(cs))
        l['flags'].update(flags)
        skill = next((c[1] for c in cs if c[0] == 'skill'), None)
        if skill:
            l['skill'] = avk(AV[skill])
        if end:
            for n in [int(x) for x in re.findall(r'\{marker(\d+)\}', end)]:
                end = end.replace('{marker%d}' % n, marks[caches[n]['marker']]['edid'])
            l['end'] = {'source': end, 'parts': None}
        l.setdefault('begin', None)
        l.setdefault('end', None)
        lines.append(l)
    # compile against the mod with this step's records and the named markers laid over
    forms = aq.ModForms(gd, pr)
    for x in out:
        if x['op'] == 'record':
            e = recordio.field(x['record'], 'EDID')
            if e:
                forms.own[e.lower()] = (x['key'], x['record'])
    names = {m['edid'] for m in marks.values()}
    for m in marks.values():
        forms.own[m['edid'].lower()] = (m['ref'], {'type': 'REFR', 'flags': tes4.PERSISTENT,
                                                   'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': m['edid']}]})
    forms.is_map_marker = lambda f: f.rec is not None and recordio.field(f.rec, 'EDID') in names
    plain = forms.find_edid

    def find_edid(name, plain=plain):            # (a marker the source plugin placed has the plugin's key, not the mod's '+')
        hit = forms.own.get(name.lower())
        if hit and not hit[0].startswith('+'):
            return scriptc.Form(forms, gd.from_key(hit[0]), 'REFR', True, None, hit[1])
        return plain(name)
    forms.find_edid = find_edid
    _script_vars = forms.script_vars

    def script_vars(form, _sv=_script_vars):     # (this step's own quest script isn't in the mod yet)
        if form.rec is quest or (form.rec and recordio.field(form.rec, 'EDID') == QUEST):
            return {k: (v, False) for k, v in V.items()}
        return _sv(form)
    forms.script_vars = script_vars
    compiled = []
    for l in lines:
        errors = aq.compile_line(l, forms)
        if errors:
            raise ValueError('%s: %s (%s)' % (errors[0]['where'], errors[0]['message'], l['responses'][0]['text'][:40]))
        compiled.append(qr.info_record(l))
    pr.apply(LABEL, out + [{'op': 'record_new', 'record': r} for r in compiled])
    rep.update({'lines': len(compiled), 'caches': len(caches), 'markers': sorted(m['edid'] for m in marks.values()),
                'mandarin': sum(1 for l in lines if l['responses'][0]['text'] in ZH), 'skipped': skipped})
    rep['made'] += ['%d lines' % len(compiled)]
    import os
    global VOICE_ONLY
    if REUSE_FROM and os.path.isdir(REUSE_FROM) and os.path.normcase(os.path.abspath(REUSE_FROM)) != os.path.normcase(os.path.abspath(
            os.path.dirname(os.path.dirname(library_dir(pr))))):
        got = reuse(gd, pr, REUSE_FROM)
        rep['reused'] = {k: v for k, v in got.items() if k != 'missing'}
        VOICE_ONLY = got['missing'] or ['+NOTHING']       # (the runner voices only what had no rehearsal take)
        rep['voice_still'] = len(got['missing'])
    # the Huáng's lines in Mandarin, into every folder their speakers use (voicelines' Mandarin pass speaks only the
    # editor's own folder: 200 files were missing at the first rehearsal); the runner then leaves them alone
    zh_lines, made = zh_fill(gd, pr)
    rep['mandarin_files'] = made
    if VOICE_ONLY is None:
        VOICE_ONLY = sorted(k for k, r in pr.records.items() if r.get('type') == 'INFO' and _quest_of(pr, k) == QUEST and k not in zh_lines) or ['+NOTHING']
    else:
        VOICE_ONLY = [k for k in VOICE_ONLY if k not in zh_lines] or ['+NOTHING']
    return rep


def _quest_of(pr, k):
    q = recordio.field(pr.records[k], 'QSTI')
    return _edid(pr, q) if q else ''


def zh_fill(gd, pr):
    """Speaks each Mandarin response of QUEST into every voice folder its speakers may use that lacks it, each folder in a
    Mandarin voice of its own (huangland.zh_voice), and keeps the editor's folder's entry in voices.json. ({line keys}, files)."""
    import os
    import zlib
    import api_voices as av
    import huangland
    import library
    import peopletalk
    import voicegen
    import voicelines
    _zh()
    voices = av.load(pr)
    root = library.assets_dir(pr)
    zh_keys, made = set(), 0
    for p in voicelines.plan_for(gd, pr, VOICE):
        info = av.line_info(gd, pr, p['line'], voices)
        r = next((x for x in info.get('responses', ()) if x['number'] == p['number']), None)
        if not r or r['text'] not in ZH:
            continue
        zh_keys.add(p['line'])
        parts = r['path'].split(os.sep)
        for vt, female in sorted(peopletalk.folders(gd, pr, tuple(p['keys'])).items()):
            base = os.path.join(root, *(parts[:3] + [vt] + parts[4:]))
            if os.path.isfile(base + '.ogg') and os.path.isfile(base + '.lip'):
                continue
            os.makedirs(os.path.dirname(base), exist_ok=True)
            v = huangland.zh_voice('+%06X' % (zlib.crc32(vt.encode()) & 0xFFFFFF), female, 'nongmin')
            voicegen.write_line(base, ZH[r['text']], v, huangland.ZH_PACE, lang='zh')
            made += 1
            if vt == parts[3]:
                voices['lines'].setdefault(p['line'], {})[str(p['number'])] = {'text': r['text'], 'voice': v, 'speed': huangland.ZH_PACE, 'pitch': 0.0,
                                                                                'path': r['path'], 'lang': 'zh', 'say': ZH[r['text']]}
    av.save(pr, voices)
    library.publish(pr)
    return zh_keys, made


# ---------- voices made once: the rehearsal's takes laid on the live mod's lines ----------
REUSE_FROM = r'D:\FOLab-held\home13'     # (the rehearsal's FOLab home: its voices, by line text, onto these lines)
VOICE_ONLY = None


def library_dir(pr):
    import library
    return library.assets_dir(pr)


def reuse(gd, pr, home, quests=None, only=None):
    """Copies the rehearsal's voice files and voices.json entries onto this mod's lines of `quests` (default QUEST; `only`:
    these line keys), matched by the words of each response, renamed to this mod's INFO IDs in every voice folder. Where
    the rehearsal has several lines with the same words (a pool's line copied to other speakers: firstbearings' refugees),
    every one's files are taken, so each folder finds its own take; the voices.json entry is the one whose folder is the
    line's own. Files already there are left. {'files', 'entries', 'lines', 'missing': [line keys with a response not taken]}."""
    import os
    import shutil
    import api_voices as av
    import library
    import peopletalk
    import voicelines
    name = os.path.basename(library.assets_dir(pr))
    src_root = os.path.join(home, 'projects', name)
    with open(os.path.join(home, 'projects', pr.name + ' voices', 'voices.json'), encoding='utf-8') as f:
        old = json.load(f)
    by_text = {}
    for lk, rs in old.get('lines', {}).items():
        for num, e in rs.items():
            if e.get('path') and e.get('text'):
                by_text.setdefault((e['text'], num), []).append((lk, e))
    files = {}
    for root, _dirs, names in os.walk(os.path.join(src_root, 'sound', 'voice')):
        for n in names:
            files.setdefault(n.lower(), []).append(root)
    voices = av.load(pr)
    dst_root = library.assets_dir(pr)
    plan = [p for p in voicelines.plan_for(gd, pr, quests or VOICE) if only is None or p['line'] in only]
    nfiles = nentries = 0
    lines_done = set()
    for p in plan:
        lk, num = p['line'], str(p['number'])
        info = av.line_info(gd, pr, lk, voices)
        r = next((x for x in info.get('responses', ()) if str(x['number']) == num), None)
        hits = by_text.get((r['text'], num), []) if r else []
        own = None
        for olk, e in hits:
            old_id, new_id = '_%08x_%s' % (int(olk[1:], 16) & 0xFFFFFF, num), '_%08x_%s' % (int(lk[1:], 16) & 0xFFFFFF, num)
            stem = os.path.basename(e['path']).lower()           # (the rehearsal's own name: its INFO ID in it)
            if old_id not in stem or stem.split('_')[:2] != os.path.basename(r['path']).lower().split('_')[:2]:
                continue                                         # (another quest's or topic's line with the same words)
            for ext in ('.ogg', '.lip'):
                for folder in files.get(stem + ext, ()):
                    rel = os.path.relpath(folder, src_root)
                    dst = os.path.join(dst_root, rel, stem.replace(old_id, new_id) + ext)
                    if os.path.isfile(dst):
                        continue
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copyfile(os.path.join(folder, stem + ext), dst)
                    nfiles += 1
            if own is None or os.path.dirname(e['path']).lower() == os.path.dirname(r['path']).lower():
                own = e
        if own:
            voices['lines'].setdefault(lk, {})[num] = dict(own, path=r['path'])
            nentries += 1
            lines_done.add(lk)
    av.save(pr, voices)
    library.publish(pr)
    missing = sorted({lk for lk, _p in peopletalk.unvoiced(gd, pr, plan)})
    return {'files': nfiles, 'entries': nentries, 'lines': len(lines_done), 'missing': missing}


# ---------- the run-through: the lines' own conditions and end scripts, every way they can be met ----------

class Game:
    """The player and the island as the lines' conditions see them; end scripts run as the game would."""

    def __init__(self, **kw):
        self.day, self.hour, self.storm = 0.0, 12, 0
        self.perks, self.skills = set(), {s: 0 for s in AVI}
        self.fame, self.infamy, self.nw = {}, {}, {}
        self.near, self.cell = None, None
        self.q = {'barter_on': 0, 'barter_until': 0.0}
        for p in LINES:
            self.q['ready_' + p], self.q['next_' + p] = 1, 0.0
        for n in range(len(CACHES)):
            self.q['hint%d' % n] = 0
        self.items, self.shown, self.said_today = {}, [], set()
        self.__dict__.update(kw)

    def holds(self, c):
        k = c[0]
        ops = {'==': lambda a, b: a == b, '>=': lambda a, b: a >= b, '<=': lambda a, b: a <= b, '<': lambda a, b: a < b}
        return {'storm': lambda: self.storm == 1, 'night': lambda: self.hour >= 21 or self.hour < 5, 'morning': lambda: 5 <= self.hour < 11,
                'perk': lambda: c[1] in self.perks, 'nw': lambda: ops[c[2]](self.nw.get(c[1], 0), c[3]),
                'fame': lambda: self.fame.get(c[1], 0) >= 2, 'infamy': lambda: self.infamy.get(c[1], 0) >= 2,
                'near': lambda: self.near == c[1], 'cell': lambda: self.cell == c[1], 'ready': lambda: self.q['ready_' + c[1]] == 1,
                'hint': lambda: self.q['hint%d' % c[1]] == 0, 'skill': lambda: self.skills[c[1]] >= c[2]}[k]()

    def tick(self, days):
        """Time passes and the quest script runs."""
        self.day += days
        self.said_today = set()
        for p in LINES:
            if self.q['ready_' + p] == 0 and self.day >= self.q['next_' + p]:
                self.q['ready_' + p] = 1
        if self.q['barter_on'] == 1 and self.day >= self.q['barter_until']:
            self.skills['Barter'] -= BARTER_UP
            self.q['barter_on'] = 0

    def run(self, src):
        lines = src.split('\n')
        i = 0
        while i < len(lines):
            s = lines[i].strip()
            m = re.match(r'set %s\.(\w+) to (.+)' % QUEST, s)
            if m:
                self.q[m.group(1)] = eval(m.group(2).replace('GameDaysPassed', repr(self.day)), {}, dict(self.q))
            elif s.startswith('if %s.barter_on == 0' % QUEST):
                if self.q['barter_on'] != 0:
                    while lines[i].strip() != 'endif':
                        i += 1
            elif s.startswith('player.ModAV Barter'):
                self.skills['Barter'] += int(s.split()[-1])
            elif s.startswith('player.AddItem'):
                _p, it, n = s.split()
                self.items[it] = self.items.get(it, 0) + int(n)
            elif s.startswith('ShowMap'):
                self.shown.append(s.split()[1])
            i += 1

    def answer(self, pool, topic, who='all', teller=False):
        """The line the game would pick (a random group: the first not said today), and its end script run."""
        cand = [l for l in lines_spec() if l[0] == pool and l[1] == topic and (l[6] == 'all' or l[6] == who or
                                                                                 (l[6] == 'nontellers' and not teller))]
        for _p, _t, w, cs, end, flags, _w in cand:
            if flags.get('say_once_a_day') and w in self.said_today:
                continue
            if all(self.holds(c) for c in cs):
                if flags.get('say_once_a_day'):
                    self.said_today.add(w)
                if end:
                    self.run(end)
                return w
        return None


def routes():
    """{route: (what happened, ok)}."""
    R = {}
    states = list(itertools.product([0, 1], [3, 8, 14, 23], [(), ('dread',), ('kin',), ('boats',)], [-50, 0, 50], [0, 2]))
    for pool in LINES:
        bad = []
        for storm, hour, perks, nw, rep in states:
            g = Game(storm=storm, hour=hour, perks=set(perks), nw={s: nw for s in REPS}, fame={s: rep for s in REPS}, infamy={s: 2 - rep for s in REPS})
            for topic in ('G', 'new', 'place', 'heard'):
                if g.answer(pool, topic, 'silent' if topic == 'G' else 'all') is None:
                    bad.append((pool, topic, storm, hour, perks, nw, rep))
        R['%s: every topic answered in every state' % pool] = (len(bad) or len(states), not bad)
        # the traits come first, each as asked
        for t in TRAITS:
            g = Game(perks={t})
            w = g.answer(pool, 'new')
            want = next(w2 for c, w2 in LINES[pool]['N'] if c == [('perk', t)]) if any(c == [('perk', t)] for c, _w in LINES[pool]['N']) else None
            R['%s: %s heard first' % (pool, t)] = (said(w) if w else w, want is None or w == want)
        # every hint told once, then the fallback; each shows its marker
        hints = [n for n, c in enumerate(CACHES) if c[0] == pool]
        g = Game(skills={s: 100 if s == 'Speech' else 0 for s in AVI})
        told = [g.answer(pool, 'heard', teller=False) for _ in range(len(hints) + 2)]
        R['%s: each cache told once, then nothing to tell' % pool] = (
            '%d told, %d markers' % (len(set(told[:len(hints)])), len(g.shown)),
            len(set(told[:len(hints)])) == len(hints) and told[-1] == LINES[pool]['H'] and len(g.shown) == len(hints))
        g = Game()
        weak = [g.answer(pool, 'heard') for _ in range(len(hints) + 1)]
        R['%s: the hard caches wait for Speech %d' % (pool, HINT_SPEECH)] = (
            len(set(weak)) - 1, sum(1 for n in hints if CACHES[n][4] == 0) == len(set(weak)) - 1)
        # favours: once, then wait COOLDOWN days
        for skill, (w, gift) in LINES[pool]['F'].items():
            g = Game(skills={s: (100 if s == skill else 0) for s in AVI})
            first, again = g.answer(pool, 'heard'), g.answer(pool, 'heard')
            g.tick(COOLDOWN - 0.5)
            soon = g.answer(pool, 'heard')
            g.tick(0.5)
            later = g.answer(pool, 'heard')
            ok = first == w and again != w and soon != w and later == w
            if gift == 'barter':
                g2 = Game(skills={s: (60 if s == 'Barter' else 0) for s in AVI})
                g2.answer(pool, 'heard')
                up = g2.skills['Barter']
                g2.tick(1)
                ok = ok and up == 60 + BARTER_UP and g2.skills['Barter'] == 60 and g2.q['barter_on'] == 0
            elif gift:
                ok = ok and g.items.get({'fish': FISH, 'meal': MEAL, 'scrap': SCRAP}[gift], 0) > 0
            R['%s: %s favour once, then after %d days' % (pool, skill, COOLDOWN)] = (gift, ok)
        # gossip: each once a day, then the fallback
        g = Game()
        got = [g.answer(pool, 'new') for _ in range(len(LINES[pool]['R']) + 1)]
        R['%s: gossip each once a day, then the fallback' % pool] = (
            len(set(got[:-1])), len(set(got[:-1])) == len(LINES[pool]['R']) and got[-1] == LINES[pool]['E'])
    # the island's places by where they stand
    for _pool, where, w in [x for x in PLACES if x[0] == 'island']:
        g = Game(near=where)
        R['island: about %s' % where] = (w[:30], g.answer('island', 'place') == w)
    for which in COURT_CELLS:
        g = Game(cell=which)
        R['court: in the %s' % which] = (which, g.answer('court', 'place') == next(x[2] for x in PLACES if x[0] == 'court' and x[1] == which))
    return R
