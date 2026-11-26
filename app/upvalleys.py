"""Up the valleys (the user, 26 Nov 2026, via the Workshop: "we need things to do going up the valleys as well. Hints about
treasures to be found or buildings to be looted ... More quests that lure the player away from the shore, and get them to
climb the valleys and mountains").

Three quests that start by the shore and send you uphill, and four chains of clues up four valleys to a cache. Built on what
is decided (docs/waikiki-lore.md, waikiki-story-plan.md, waikiki-decisions.md): the Pacific Heights stop is "a signal beacon,
one of a chain of fires that warn Waikiki of pirate sails"; the St. Louis Heights stop is "a watcher's hut over Palolo; a man
who counts who is marched up the slave road and sells what he sees"; catchers take people before tribute day and the slave
road climbs Palolo to the crater; the Huang's ship's offices became hereditary houses (the navigator's keeps the stars and
calendar) and the Huang keep the cliff trail to the Vault's back door secret; the Kalihi lord's scouts go into the ruins.

What is invented (lean; each in docs/waikiki-decisions.md, "built 26 Nov, user may change"):
- **Hal Brennan**, the court's signalman at the Ala Wai Boat Harbor, and **Keoni Palakiko**, keeper of the Pacific Heights
  beacon, whom the pirates pay in cells to let it go dark on the nights their boats run in.
- **Leilani Kamakau** of the Palolo refugee camp, whose son **Makana** the catchers took before the last tribute day, and
  **Amos Tanabe**, the watcher (the stop's man, named).
- **Fang Jun**, an apprentice of the navigator's house at Waimanalo (Mandarin), who left the house's surveying glass and
  logbook at the old survey mark up the valley, running from the Vespids.
- Four leads: Dr. Helen Kaimana's arboretum cold store up Manoa; Grandpa Kenji's still up Palolo; a Kalihi scout's kit up
  Kalihi valley; the Olomana ranch cellar above Kailua.

1. **The Dark Beacon** (`QUESTS['beacon']`): Hal asks why the beacon is dark. Up Pacific Heights Road, Keoni.
   - Get the truth out of him (Speech `KB_WHY`), then light it: talk him round (Speech `KB_TALK`), frighten him (Dread Name or
     Intimidate `KB_THREAT`), or light it yourself (Survival `KB_SELF`): court fame, Hal pays.
   - Report him to Hal (once you know): the court takes him and puts its own man on the beacon: court fame, pirate infamy.
   - Take the pirates' cells (`KB_BRIBE`) and tell Hal it's beyond fixing (Speech `KB_LIE`; Captain's Kin is believed): it
     stays dark, pirate fame. Fail the lie and Hal sends men up: the court takes him as if reported, and remembers you.
   - Kill Keoni: Hal sends a man up; the beacon burns again; no pay.
2. **The Count** (`QUESTS['count']`): Leilani's son was taken before tribute day. Up St. Louis Heights, Amos counts who goes
   up the crater road. Buy it (`AM_PRICE` kala, Barter `AM_HAGGLE` for half), ask it as a kindness (Speech `AM_TALK`), frighten
   it out of him (Dread Name or Intimidate `AM_THREAT`), or open his footlocker (Lockpick, `AM_LOCK`) and take his tally.
   Back to Leilani: the truth (good karma), a kind lie (Speech `AM_LIE`), or the tally in her hands.
3. **The Navigator's Glass** (`QUESTS['glass']`): Fang Jun (Mandarin) left the house's glass and logbook at the old survey
   mark up Waimanalo's valley. Fetch them. Give both back (the Huang's face), the glass only and keep the book (less), or
   sell the glass to Linda Moreno. Reading the logbook with Science `GL_READ` shows the Vault's service door on your map.
4. **Leads up the valleys** (`LEADS`, one quest `QUESTS['leads']`): a lead's first step is an entry on a lore terminal
   already in the mod (loreterminals); its item script shows the next spot on your map. There a satchel holds a clue (and a
   key where the cache needs one); taking the clue shows the cache on your map and its words in a message box. The cache
   is locked (Lockpick, or the clue's key); taking its keepsake ends the lead.

The world at rest (docs/waikiki-weak-spots-1126.md): nothing starts until you ask; the beacon stays dark, Amos stays in his
hut, the satchels and caches wait. Every placement clear of doors, markers, roads and the other finds (`CLEAR`).

    plan(gd, pr)       {'rows', 'skipped', 'spots'}
    apply(pr, gd, P)   one Undo (VOICE: the quests' lines; ZH: Fang Jun's Mandarin)
"""
import json
import math
import re

import recordio

LABEL = 'Valley quests: the dark beacon, the count, the navigator\'s glass, and leads up four valleys'
QUESTS = {'beacon': 'FOLabUVDarkBeacon', 'count': 'FOLabUVTheCount', 'glass': 'FOLabUVNavigatorsGlass', 'leads': 'FOLabUVLeads'}
NAMES = {'beacon': 'The Dark Beacon', 'count': 'The Count', 'glass': "The Navigator's Glass", 'leads': 'Up the Valleys'}
VOICE = [QUESTS[k] for k in ('beacon', 'count', 'glass')]
VOICE_ONLY = None
ZH = {}

# the people: key: (editor ID, name, sex, races, kind)
PEOPLE = {
    'hal': ('FOLabUVSignalmanHal', 'Hal Brennan', 'M', ('Caucasian', 'AfricanAmerican', 'Hispanic'), 'court'),
    'keoni': ('FOLabUVBeaconKeoni', 'Keoni Palakiko', 'M', ('Hispanic', 'Asian', 'AfricanAmerican', 'Caucasian'), 'keeper'),
    'court_keeper': ('FOLabUVBeaconCourtman', 'Court Beacon Keeper', 'M', ('Caucasian', 'Hispanic', 'AfricanAmerican'), 'court'),
    'leilani': ('FOLabUVLeilaniKamakau', 'Leilani Kamakau', 'F', ('Hispanic', 'Asian', 'AfricanAmerican', 'Caucasian'), 'camp'),
    'amos': ('FOLabUVWatcherAmos', 'Amos Tanabe', 'M', ('Asian', 'AsianOld', 'Caucasian'), 'watcher'),
    'fang': ('FOLabUVFangJun', 'Fang Jun', 'M', ('Asian',), 'huang'),
}
REF = {k: v[0] + 'REF' for k, v in PEOPLE.items()}
REF.update({'fire': 'FOLabUVBeaconFireREF', 'locker': 'FOLabUVWatcherLockerREF', 'case': 'FOLabUVSurveyCaseREF'})
THEIRS = {'linda': 'FOLabWaikikiTrader'}
ITEMS = {'tally': ('FOLabUVWatchersTally', "Watcher's Tally"), 'glass': ('FOLabUVTheodolite', 'Survey Theodolite'),
         'book': ('FOLabUVLogbook', "Navigator's Logbook")}
MISC_LIKE = ('VRRCMisfitsDrugs', 'Briefcase', 'LunchBox')
CHEST_LIKE = ('Footlocker01Empty', 'Footlocker01HouseholdNV')
SATCHEL_LIKE = ('CampSearchlightNVDuffleBag', 'NVDLC02DuffleBagzGen01', 'Footlocker01Empty')
FIRES = ('FXFireSmall01',)               # (the game's animated fire, MSTT; stood scaled up on the beacon's campfire)
BEACON_PIT = ('CampfireCrafting03', 600.0)   # (the beacon's own campfire, this near its marker)
FIRE_SCALE = 3.0
KALA, TONGBAO, CELL = 'Caps001', 'FOLabTongbao', 'AmmoSmallEnergyCell'
NAME_Q = 'FOLabNameOnWater'
TALK_G, THREAT_G = 'FOLabTraitTalk', 'FOLabTraitThreat'
TRAITS = {'dread': 'FOLabTraitDreadName', 'kin': 'FOLabTraitCaptainsKin', 'soft': 'FOLabTraitSoftTouch',
          'tongues': 'FOLabTraitTwoTongues'}
REPS = {'court': 'FOLabRepCourt', 'pirates': 'FOLabRepPirates', 'huang': 'FOLabRepHuang'}
BACK_DOOR = 'FOLabVaultServiceDoorMarker'

# checks
KB_WHY, KB_TALK, KB_THREAT, KB_SELF, KB_LIE, KB_BRIBE = 45, 60, 60, 40, 50, 20
AM_PRICE, AM_HAGGLE, AM_TALK, AM_THREAT, AM_LOCK, AM_LIE = 40, 40, 60, 55, 50, 35
GL_READ = 50
# rewards
HAL_PAY = [(KALA, 60), ('Stimpak', 2)]
HAL_REPORT_PAY = [(KALA, 40)]
LEILANI_GIFT = [('WeapHuntingRifle', 1), ('Ammo308', 20)]
FANG_BOTH = [(TONGBAO, 15), ('Stimpak', 2)]
FANG_GLASS = [(TONGBAO, 8)]
LINDA_PAYS = 70

STANDING = {
    'kb_lit': [('court', 1, 1, 8)], 'kb_reported': [('court', 1, 1, 10), ('pirates', 0, 1, -10)],
    'kb_dark': [('pirates', 1, 1, 10), ('court', None, 0, -5)], 'kb_caught': [('court', None, 0, -10), ('pirates', 0, 1, -5)],
    'kb_dead': [('court', None, 0, -3)],
    'am_truth': [], 'am_lie': [], 'am_tally': [],
    'gl_both': [('huang', 1, 1, 10)], 'gl_glass': [('huang', None, 0, 5)], 'gl_sold': [('huang', 0, 1, -10), ('court', None, 0, 3)],
}

W = {
    # ----- The Dark Beacon: Hal Brennan, the court's signalman by the Ala Wai -----
    'h_hi': "Hal Brennan, the court's signalman. I watch the hills, so the city doesn't have to. Usually.",
    'h_back': "Well? Is it burning?",
    'h_work': "Anything wrong up in the hills?",
    'h_work_r': "The beacon on Pacific Heights has been dark three nights. It's one of the fires that warn the city when pirate sails come in. "
                "Keoni Palakiko keeps it. Go up Pacific Heights Road and find out why. If you get it burning, the court pays.",
    'h_lit': "The beacon's burning again.",
    'h_lit_r': "I saw it go up last night. Good. Here's the court's thanks.",
    'h_report': "The keeper lets it go dark for the pirates. They pay him in cells.",
    'h_report_r': "For cells. On the nights their boats come in. ...The court will see to Keoni. Our own man goes up tonight. Here, for your trouble.",
    'h_broken': "The beacon's beyond fixing. The pit's cracked through.",
    'h_broken_yes': "[SUCCEEDED] Cracked through. Damn it. I'll ask the court for stone and a mason. Months, that'll be.",
    'h_broken_kin': "If your family's word says so, it's so. Months, then.",
    'h_broken_no': "[FAILED] Cracked. I sat on that pit as a boy. Somebody up there's lying, and now I'm wondering about you too. The court sends men up tonight.",
    'h_dead': "Keoni's dead.",
    'h_dead_r': "Dead. ...Then nobody was lighting it. The court will put its own man up there. I won't ask how.",
    # Keoni Palakiko at the beacon
    'k_hi': "Long climb for nothing. Beacon's out. Wet wood.",
    'k_back': "You again.",
    'k_why': "Why is the beacon dark, really?",
    'k_why_yes': "[SUCCEEDED] ...Cells. The boat men pay me in cells to let it go dark the nights their boats run in. Forty a night. "
                 "The court pays me in fish heads. You do the sum.",
    'k_why_no': "[FAILED] Wet wood. Like I said.",
    'k_light': "Light it. Now.",
    'k_light_yes': "[SUCCEEDED] ...You're right. If the court finds out, I'm tribute. Fine. It burns tonight.",
    'k_light_no': "[FAILED] Light it yourself, if you're so keen.",
    'k_threat': "Light it, or I throw you off this ridge.",
    'k_threat_yes': "[SUCCEEDED] All right! All right. It's lit. Look. It's lit.",
    'k_threat_no': "[FAILED] Go on, then. They'd only send another keeper.",
    'k_self': "Then I'll light it myself.",
    'k_self_yes': "[SUCCEEDED] You built that in this wind? ...Huh. Your neck when the boat men ask, not mine.",
    'k_self_no': "[FAILED] Not in this wind, you won't. Takes years to learn the pit.",
    'k_deal': "What would the boat men pay me to keep quiet?",
    'k_deal_r': "Twenty cells, now. Tell the signalman it's broken beyond fixing, and there's more where those came from.",
    'k_gone': "Get off my ridge.",
    'ck_hi': "Court's beacon. Court's man. Move along.",
    # ----- The Count: Leilani Kamakau and Amos Tanabe -----
    'l_hi': "Have you come down the valley? Did you see a boy? Seventeen, tall, a burn on his left hand.",
    'l_back': "Did he tell you? The man on the hill?",
    'l_help': "Who are you looking for?",
    'l_help_r': "Makana. My son. The catchers took him the week before tribute day. People say there's a man up on St. Louis Heights "
                "who counts everyone they march up the crater road. He sells what he sees. Find out if my boy went up. Please.",
    'l_truth': "He went up the crater road. I'm sorry.",
    'l_truth_r': "...Up. Then he's gone. I knew. I knew, I only wanted somebody to say it. His father's rifle. Take it. I can't look at it.",
    'l_lie': "He's working the Manoa farms. He's alive.",
    'l_lie_yes': "[SUCCEEDED] Working. Alive. ...Then I'll wait for him. Take his father's rifle. He'll want a new one when he comes home.",
    'l_lie_no': "[FAILED] You're kind. You're a bad liar. ...He went up, didn't he.",
    'l_tally': "Here. His name's in this. Read it yourself.",
    'l_tally_r': "\"Makana Kamakau, roped, up the crater road.\" In his hand, every name. ...Thank you for not lying to me. Take the rifle.",
    'l_after': "I'll be here. Somebody has to remember them.",
    'a_hi': "You're standing in my light.",
    'a_back': "Come to buy, or come to stand there?",
    'a_who': "What do you watch up here?",
    'a_who_r': "The crater road. Who goes up roped, and when, and who walks them. Everyone wants to know something about that road. I sell it.",
    'a_makana': "A boy called Makana. Taken before tribute day.",
    'a_makana_r': "Names cost. Forty kala.",
    'a_pay': "Here's forty.",
    'a_haggle': "Twenty, and you won't have to eat fish heads this week.",
    'a_haggle_yes': "[SUCCEEDED] ...Twenty. Fine.",
    'a_haggle_no': "[FAILED] Forty. Names cost.",
    'a_talk': "His mother's waiting at the bottom of the hill. Tell me for her.",
    'a_talk_yes': "[SUCCEEDED] ...Mothers. Always the mothers. Fine. Free, this once. Don't tell anybody I do that.",
    'a_talk_no': "[FAILED] Everybody's got a mother. Forty kala.",
    'a_threat': "Tell me, or you won't count anything again.",
    'a_threat_yes': "[SUCCEEDED] Easy! Easy. I'll tell you.",
    'a_threat_no': "[FAILED] I've watched worse than you walk up that road. Forty kala.",
    'a_told': "Makana Kamakau. Tall, burn on his hand. Roped, three nights after the new moon, up the crater road with six others. "
              "Pirates walking them. Nobody comes back down that road.",
    # ----- The Navigator's Glass: Fang Jun (Mandarin), Linda Moreno -----
    'f_help': "What did you lose?",
    'f_glass': "Here's your glass.",
    'f_book': "And your logbook.",
    'lm_glass': "A pre-war surveying glass. Want it?",
    'lm_glass_r': "Brass, glass, and it still turns. The court's builders would kill for this. Seventy kala.",
}

# Fang Jun's lines in Mandarin: key: (English, toned pinyin) (shown as pinyin with the English in brackets: huangland.shown)
M = {
    'f_hi': ("You're a stranger. I'm Fang Jun, of the navigator's house. I've lost something. My master will have my hide.",
             "Nǐ shì wàirén. Wǒ jiào Fāng Jùn, dǎohángjiā de rén. Wǒ diū le dōngxi. Shīfu huì dǎ sǐ wǒ."),
    'f_back': ("Did you find it? The glass?", "Nǐ zhǎodào le ma? Nà gè jìng?"),
    'f_help_r': ("The house's surveying glass, and its logbook. I took them up the valley to the old survey mark, to take the stars. "
                 "The wasps came. I ran. I left them in the case by the mark. Please bring them back.",
                 "Wǒmen jiā de cèliáng jìng, hái yǒu rìzhì. Wǒ ná dào shāngǔ shàng miàn de jiù biāojì nàlǐ, kàn xīngxing. "
                 "Mǎfēng lái le. Wǒ pǎo le. Dōngxi liú zài biāojì páng de xiāngzi lǐ. Qǐng nǐ ná huílái."),
    'f_glass_r': ("The glass! It isn't broken. Thank you. ...And the logbook?", "Jìngzi! Méi huài. Xièxie nǐ. ...Rìzhì ne?"),
    'f_book_r': ("Both. The house owes you face for this. Take these, from the house.", "Dōu zài. Wǒmen jiā qiàn nǐ yí gè rénqíng. Ná zhe, shì wǒmen jiā gěi nǐ de."),
    'f_nobook': ("Only the glass. ...My master will ask about the book. Take this, it's all I have.",
                 "Zhǐyǒu jìngzi. ...Shīfu huì wèn rìzhì de. Ná zhe, wǒ zhǐ yǒu zhèxiē."),
    'f_sold': ("You sold it to the barbarians' court. The house will remember your face.", "Nǐ bǎ tā mài gěi le mányí de cháotíng. Wǒmen jiā huì jìzhù nǐ de liǎn."),
    'f_done': ("The house remembers you.", "Wǒmen jiā jìde nǐ."),
}
ZH_SAID = [k for k, v in M.items() if v]


def shown(k):
    import huangland
    english, pinyin = M[k]
    return huangland.shown(english, pinyin)


def words(k):
    return shown(k) if k in M else W[k]


def _zh():
    for k in ZH_SAID:
        ZH[shown(k)] = M[k][1]


try:
    _zh()
except Exception:                       # noqa: BLE001  (g2pzh unavailable at import: filled when the step runs)
    pass

# ---------- the leads ----------
# key: {terminal (loreterminals site), entry (title, words), clue (spot target, satchel words), cache (target, ...)}
LEADS = {
    'manoa': {
        'n': 1, 'terminal': 'hamilton', 'terminal_inside': 'manoa_ranger',
        'entry': ('Search: "arboretum"', """
  1 result. "Lyon Arboretum: seed collection moved 10-20-2077 to the cold store at the head
  of the valley, by order of Dr. H. Kaimana. Key and field notes kept at the upper Manoa
  ranger post." Status: OFF SITE."""),
        'clue': {'at': ('place', r'^Ranger Post$', (-63179, 31700)), 'name': "Dr. Kaimana's Field Notes", 'key': True,
                 'marker': ('FOLabUVManoaPostMarker', 'Upper Manoa Ranger Post', 4),
                 'words': "Dr. H. Kaimana, field notes, 10-21-2077: The seed collection is in the cold store at the head of the valley, "
                          "where the stream comes off the ridge. If this is what I think it is, somebody should come back for it. "
                          "Key's here. Don't lose it."},
        'cache': {'at': (-59400, 44000), 'name': 'Arboretum Cold Store', 'lock': 75,
                  'marker': ('FOLabUVArboretumMarker', 'Arboretum Cold Store', 4),
                  'items': [('Stimpak', 3), ('RadX', 2), ('Mentats', 1), ('Caps001', 40)], 'keepsake': ('FOLabUVSeedTin', 'Arboretum Seed Tin')},
    },
    'palolo': {
        'n': 2, 'terminal': 'palolo_home',
        'entry': ('(typed long after) Grandpa', """
  Grandpa Kenji kept a still up the valley, above the squatters, where the road bends
  and nobody looks. He left the recipe in a tin at the bend. He never told the boat
  men. He never told anybody. He only told this machine."""),
        'clue': {'at': (-42700, 11800), 'name': "Kenji's Recipe Card", 'key': True,
                 'marker': ('FOLabUVKenjiTinMarker', "Kenji's Tin", 4),
                 'words': "Kenji's recipe: sugarcane, taro peel, patience. The still is further up, past where the trees close in, under "
                          "the big rock. The cellar door sticks. Lift and pull."},
        'cache': {'at': (-35400, 24700), 'name': "Kenji's Still", 'lock': 75,
                  'marker': ('FOLabUVKenjiStillMarker', "Kenji's Still", 4),
                  'items': [('Moonshine', 3), ('WaterPurified', 3), ('Caps001', 60), ('Ammo10mm', 20)], 'keepsake': ('FOLabUVCopperCoil', "Kenji's Copper Coil")},
    },
    'kalihi': {
        'n': 3, 'terminal': 'hsuyun',
        'entry': ('A prayer slip left on the altar', """
  "For Ben, who scouts for the lord at Alewa. He hid his kit up Kalihi valley when the
  ruins made him sick, by the old water tank. He meant to go back for it. May he still."
  (Pinned under the slip: a scrap of map with a pencil cross.)"""),
        'clue': {'at': (-122600, 56500), 'name': "Ben's Map Scrap", 'key': False,
                 'marker': ('FOLabUVKalihiTankMarker', 'Old Water Tank', 4),
                 'words': "Ben's scrap: \"Kit's further up the valley, under the overhang where the trail turns to rock. Lord doesn't "
                          "know. What I saw past the wall stays with me.\""},
        'cache': {'at': (-119000, 67500), 'name': "Scout's Kit", 'lock': 50,
                  'marker': ('FOLabUVScoutKitMarker', "Scout's Overhang", 3),
                  'items': [('Ammo556mm', 40), ('RadAway', 2), ('RadX', 2), ('WeapGrenadeFrag', 2)], 'keepsake': ('FOLabUVScoutCompass', "Scout's Compass")},
    },
    'olomana': {
        'n': 4, 'terminal': 'kailua_post',
        'entry': ('Undelivered: to Olomana Ranch', """
  "Dear Mr. Silva. The ranch cellar key is under the water trough by the lower gate,
  as you asked. Your sister says take the good canned goods up before the roads close.
  The cellar's at the top paddock." (Postmarked 10-22-2077.)"""),
        'clue': {'at': (54000, 106000), 'name': 'Ranch Cellar Key Tag', 'key': True,
                 'marker': ('FOLabUVRanchGateMarker', 'Olomana Ranch, Lower Gate', 4),
                 'words': "A key on a tag: \"Silva - cellar, top paddock.\""},
        'cache': {'at': (48000, 112000), 'name': 'Ranch Cellar', 'lock': 75,
                  'marker': ('FOLabUVRanchCellarMarker', 'Olomana Ranch Cellar', 4),
                  'items': [('PorkNBeans', 3), ('InstaMash', 2), ('WaterPurified', 3), ('Caps001', 50)], 'keepsake': ('FOLabUVRanchBrand', 'Silva Ranch Brand')},
    },
}

# where the quests' people and things stand: key: (anchor map marker, radii)
SPOTS = {
    'hal': ('Ala Wai Boat Harbor', (300, 450, 600, 800, 1000)),
    'keoni': ('Pacific Heights Beacon', (150, 250, 350, 500)),
    'court_keeper': ('Pacific Heights Beacon', (200, 300, 400, 550)),
    'leilani': ('Palolo Refugee Camp', (200, 350, 500, 700)),
    'amos': ("Watcher's Hut", (100, 200, 300, 450)),
    'locker': ("Watcher's Hut", (150, 250, 350, 500)),
    'fang': ("Waimanalo Beach Squatters' Camp", (300, 450, 600, 800)),
}
CASE_AT = (52000, 64000)                # (the old survey mark up Waimanalo's valley: the line's top, ~1,400 high)
CLEAR = {'door': 1000.0, 'marker': 1200.0, 'road': 450.0, 'find': 900.0, 'apart': 1500.0}
NIGHT = (20, 5)
from skillcheck import SKILLS as _SKILLS
AVI = {k: v[0] for k, v in _SKILLS.items()}     # (Survival is 44, AVThrowing to the game)

TOPICS = {'h_work': 'beacon', 'h_lit': 'beacon', 'h_report': 'beacon', 'h_broken': 'beacon', 'h_dead': 'beacon',
          'k_why': 'beacon', 'k_light': 'beacon', 'k_threat': 'beacon', 'k_self': 'beacon', 'k_deal': 'beacon',
          'l_help': 'count', 'l_truth': 'count', 'l_lie': 'count', 'l_tally': 'count',
          'a_who': 'count', 'a_makana': 'count', 'a_pay': 'count', 'a_haggle': 'count', 'a_talk': 'count', 'a_threat': 'count',
          'f_help': 'glass', 'f_glass': 'glass', 'f_book': 'glass', 'lm_glass': 'glass'}
TOP = ('h_work', 'h_lit', 'h_report', 'h_broken', 'h_dead', 'l_help', 'l_truth', 'l_lie', 'l_tally', 'a_who', 'a_makana',
       'f_help', 'f_glass', 'lm_glass', 'k_why', 'k_light', 'k_self')


def topic_edid(t):
    return 'FOLabUV' + ''.join(p.capitalize() for p in t.split('_'))


VARS = {
    'beacon': ('asked', 'met', 'knows', 'lit', 'how', 'bribed', 'broken', 'reported', 'kdead', 'paid', 'caught', 'done'),
    'count': ('asked', 'told', 'how', 'answered', 'done'),
    'glass': ('asked', 'got', 'gotbook', 'readit', 'gave', 'gavebook', 'sold', 'done'),
    'leads': tuple('lead%d%s' % (n, v) for n in range(1, 5) for v in ('c', 'n', 'd')) + ('done',),
}


def lines_spec():
    """[(who, quest, topic, words, conds, end, skill, choices, goodbye)], conditions as crossquests' ('q', quest, var, op, v),
    ('perk', t, 1|0), ('glob', g, op, v), ('skill', s, op, v), ('items', item, op, v), ('dead', who)."""
    L = []

    def line(who, quest, topic, w, conds=(), end='', skill=None, choices=(), bye=False):
        L.append((who, quest, topic, w, list(conds), end, skill, list(choices), bye))
    Q = QUESTS
    qv = lambda w, var, op, v: ('q', w, var, op, v)
    S = lambda w: (lambda var, v=1: 'set %s.%s to %s' % (Q[w], var, v))
    sb, scn, sg = S('beacon'), S('count'), S('glass')
    give = lambda it, n: 'player.AddItem %s %d' % (it, n)
    take = lambda it, n: 'player.RemoveItem %s %d' % (it, n)
    gives = lambda lst: '\n'.join(give(i, n) for i, n in lst)
    # ----- The Dark Beacon -----
    B = 'beacon'
    open_b = [qv(B, 'lit', '==', 0), qv(B, 'reported', '==', 0), qv(B, 'broken', '==', 0), qv(B, 'kdead', '==', 0)]
    line('hal', B, 'G', 'h_back', [qv(B, 'asked', '==', 1), qv(B, 'done', '==', 0)], '', None, ['h_lit', 'h_report', 'h_broken', 'h_dead'])
    line('hal', B, 'G', 'h_hi', [], '', None, ['h_work'])
    line('hal', B, 'h_work', 'h_work_r', [qv(B, 'asked', '==', 0)], sb('asked'))
    line('hal', B, 'h_lit', 'h_lit_r', [qv(B, 'lit', '>=', 1), qv(B, 'lit', '<=', 3), qv(B, 'paid', '==', 0)], sb('paid') + '\n' + gives(HAL_PAY))
    line('hal', B, 'h_report', 'h_report_r', open_b + [qv(B, 'knows', '==', 1)], sb('reported') + '\n' + gives(HAL_REPORT_PAY))
    lie = open_b + [qv(B, 'bribed', '==', 1)]
    line('hal', B, 'h_broken', 'h_broken_kin', lie + [('perk', 'kin', 1)], sb('broken'))
    line('hal', B, 'h_broken', 'h_broken_yes', lie + [('glob', TALK_G, '>=', KB_LIE)], sb('broken'), 'Speech')
    line('hal', B, 'h_broken', 'h_broken_no', lie, sb('caught') + '\n' + sb('reported'), 'Speech')
    line('hal', B, 'h_dead', 'h_dead_r', [qv(B, 'kdead', '==', 1), qv(B, 'paid', '==', 0)], sb('paid', 2))
    # Keoni
    line('keoni', B, 'G', 'k_gone', [qv(B, 'broken', '==', 0), qv(B, 'lit', '>=', 1)], '', None, [], True)
    line('keoni', B, 'G', 'k_back', [qv(B, 'met', '==', 1)], '', None, ['k_why', 'k_light', 'k_threat', 'k_self', 'k_deal'])
    line('keoni', B, 'G', 'k_hi', [], sb('met'), None, ['k_why', 'k_light', 'k_threat', 'k_self'])
    line('keoni', B, 'k_why', 'k_why_yes', open_b + [qv(B, 'knows', '==', 0), ('glob', TALK_G, '>=', KB_WHY)], sb('knows'), 'Speech',
         ['k_light', 'k_threat', 'k_self', 'k_deal'])
    line('keoni', B, 'k_why', 'k_why_no', open_b + [qv(B, 'knows', '==', 0)], '', 'Speech', ['k_light', 'k_threat', 'k_self'])
    line('keoni', B, 'k_light', 'k_light_yes', open_b + [('glob', TALK_G, '>=', KB_TALK)], sb('lit', 1), 'Speech')
    line('keoni', B, 'k_light', 'k_light_no', open_b, '', 'Speech', ['k_threat', 'k_self'])
    line('keoni', B, 'k_threat', 'k_threat_yes', open_b + [('perk', 'dread', 1)], sb('lit', 2), 'Speech')
    line('keoni', B, 'k_threat', 'k_threat_yes', open_b + [('glob', THREAT_G, '>=', KB_THREAT)], sb('lit', 2), 'Speech')
    line('keoni', B, 'k_threat', 'k_threat_no', open_b, '', 'Speech', ['k_self'])
    line('keoni', B, 'k_self', 'k_self_yes', open_b + [('skill', 'Survival', '>=', KB_SELF)], sb('lit', 3), 'Survival')
    line('keoni', B, 'k_self', 'k_self_no', open_b, '', 'Survival')
    line('keoni', B, 'k_deal', 'k_deal_r', open_b + [qv(B, 'knows', '==', 1), qv(B, 'bribed', '==', 0), qv(B, 'asked', '==', 1)],
         sb('bribed') + '\n' + give(CELL, KB_BRIBE))
    line('court_keeper', B, 'G', 'ck_hi', [], '', None, [], True)
    # ----- The Count -----
    C = 'count'
    line('leilani', C, 'G', 'l_after', [qv(C, 'answered', '>=', 1)], '', None, [], True)
    line('leilani', C, 'G', 'l_back', [qv(C, 'asked', '==', 1)], '', None, ['l_truth', 'l_lie', 'l_tally'])
    line('leilani', C, 'G', 'l_hi', [], '', None, ['l_help'])
    line('leilani', C, 'l_help', 'l_help_r', [qv(C, 'asked', '==', 0)], scn('asked'))
    ans = [qv(C, 'told', '==', 1), qv(C, 'answered', '==', 0)]
    gift = '\n' + gives(LEILANI_GIFT)
    line('leilani', C, 'l_truth', 'l_truth_r', ans, scn('answered', 1) + gift + '\nRewardKarma 15')
    line('leilani', C, 'l_lie', 'l_lie_yes', ans + [('glob', TALK_G, '>=', AM_LIE)], scn('answered', 2) + gift, 'Speech')
    line('leilani', C, 'l_lie', 'l_lie_no', ans, scn('answered', 1) + gift, 'Speech')
    line('leilani', C, 'l_tally', 'l_tally_r', ans + [('items', 'tally', '>=', 1)], take('tally', 1) + '\n' + scn('answered', 3) + gift + '\nRewardKarma 15')
    no_tell = [qv(C, 'told', '==', 0)]
    line('amos', C, 'G', 'a_back', [qv(C, 'asked', '==', 1)], '', None, ['a_who', 'a_makana'])
    line('amos', C, 'G', 'a_hi', [], '', None, ['a_who', 'a_makana'])
    line('amos', C, 'a_who', 'a_who_r', [], '')
    line('amos', C, 'a_makana', 'a_told', [qv(C, 'told', '==', 1)], '')
    line('amos', C, 'a_makana', 'a_makana_r', no_tell + [qv(C, 'asked', '==', 1)], '', None, ['a_pay', 'a_haggle', 'a_talk', 'a_threat'])
    told = lambda how: scn('told') + '\n' + scn('how', how)
    line('amos', C, 'a_pay', 'a_told', no_tell + [('items', KALA, '>=', AM_PRICE)], take(KALA, AM_PRICE) + '\n' + told(1))
    line('amos', C, 'a_haggle', 'a_haggle_yes', no_tell + [('skill', 'Barter', '>=', AM_HAGGLE), ('items', KALA, '>=', AM_PRICE // 2)],
         take(KALA, AM_PRICE // 2) + '\n' + told(1), 'Barter', ['a_makana'])
    line('amos', C, 'a_haggle', 'a_haggle_no', no_tell, '', 'Barter', ['a_pay', 'a_talk', 'a_threat'])
    line('amos', C, 'a_talk', 'a_talk_yes', no_tell + [('perk', 'soft', 1)], told(2), 'Speech', ['a_makana'])
    line('amos', C, 'a_talk', 'a_talk_yes', no_tell + [('glob', TALK_G, '>=', AM_TALK)], told(2), 'Speech', ['a_makana'])
    line('amos', C, 'a_talk', 'a_talk_no', no_tell, '', 'Speech', ['a_pay', 'a_haggle', 'a_threat'])
    line('amos', C, 'a_threat', 'a_threat_yes', no_tell + [('perk', 'dread', 1)], told(3), 'Speech', ['a_makana'])
    line('amos', C, 'a_threat', 'a_threat_yes', no_tell + [('glob', THREAT_G, '>=', AM_THREAT)], told(3), 'Speech', ['a_makana'])
    line('amos', C, 'a_threat', 'a_threat_no', no_tell, '', 'Speech', ['a_pay', 'a_haggle', 'a_talk'])
    # ----- The Navigator's Glass -----
    G = 'glass'
    line('fang', G, 'G', 'f_sold', [qv(G, 'sold', '==', 1)], '', None, [], True)
    line('fang', G, 'G', 'f_done', [qv(G, 'gave', '==', 1)], '', None, ['f_book'])
    line('fang', G, 'G', 'f_back', [qv(G, 'asked', '==', 1)], '', None, ['f_glass'])
    line('fang', G, 'G', 'f_hi', [], '', None, ['f_help'])
    line('fang', G, 'f_help', 'f_help_r', [qv(G, 'asked', '==', 0)], sg('asked'))
    line('fang', G, 'f_glass', 'f_glass_r', [qv(G, 'gave', '==', 0), qv(G, 'sold', '==', 0), ('items', 'glass', '>=', 1)],
         take('glass', 1) + '\n' + sg('gave'), None, ['f_book'])
    line('fang', G, 'f_book', 'f_book_r', [qv(G, 'gave', '==', 1), qv(G, 'gavebook', '==', 0), ('items', 'book', '>=', 1)],
         take('book', 1) + '\n' + sg('gavebook') + '\n' + gives(FANG_BOTH))
    line('fang', G, 'f_book', 'f_nobook', [qv(G, 'gave', '==', 1), qv(G, 'gavebook', '==', 0)], sg('gavebook', 2) + '\n' + gives(FANG_GLASS))
    line('linda', G, 'lm_glass', 'lm_glass_r', [qv(G, 'gave', '==', 0), qv(G, 'sold', '==', 0), ('items', 'glass', '>=', 1)],
         take('glass', 1) + '\n' + give(KALA, LINDA_PAYS) + '\n' + sg('sold'))
    return L


# ---------- the quests' scripts ----------

def _ifonce(cond, var, body):
    return ['\tif %s' % cond, '\t\tif %s == 0' % var, '\t\t\tset %s to 1' % var] + ['\t\t\t' + b for b in body] + ['\t\tendif', '\tendif']


def beacon_script():
    q, r = QUESTS['beacon'], REF
    L = ['scn FOLabUVDarkBeaconScript'] + ['short %s' % v for v in VARS['beacon']] + ['short s10', 'short s20', 'short fireon', 'short swapped', '', 'Begin GameMode']
    L += _ifonce('asked == 1', 's10', ['SetStage %s 10' % q])
    L += _ifonce('knows == 1', 's20', ['SetStage %s 20' % q])
    L += ['\tif kdead == 0', '\t\tif %s.GetDead == 1' % r['keoni'], '\t\t\tset kdead to 1', '\t\tendif', '\tendif']
    # the court's man takes the beacon: reported, caught lying, or Keoni dead
    L += ['\tif swapped == 0', '\t\tif reported == 1 || kdead == 1', '\t\t\tset swapped to 1', '\t\t\t%s.Disable' % r['keoni'],
          '\t\t\t%s.Enable' % r['court_keeper'], '\t\t\tif lit == 0', '\t\t\t\tset lit to 4', '\t\t\tendif', '\t\tendif', '\tendif']
    L += _ifonce('lit > 0 && broken == 0', 'fireon', ['%s.Enable' % r['fire']])
    L += ['\tif done == 0',
          '\t\tif paid == 1', '\t\t\tset done to 1', '\t\t\tif lit == 1', '\t\t\t\tSetStage %s 100' % q, '\t\t\telseif lit == 2',
          '\t\t\t\tSetStage %s 102' % q, '\t\t\telse', '\t\t\t\tSetStage %s 104' % q, '\t\t\tendif',
          '\t\telseif caught == 1', '\t\t\tset done to 1', '\t\t\tSetStage %s 125' % q,
          '\t\telseif reported == 1', '\t\t\tset done to 1', '\t\t\tSetStage %s 110' % q,
          '\t\telseif broken == 1', '\t\t\tset done to 1', '\t\t\tSetStage %s 120' % q,
          '\t\telseif kdead == 1 && paid == 2', '\t\t\tset done to 1', '\t\t\tSetStage %s 130' % q,
          '\t\tendif', '\tendif']
    return '\n'.join(L + ['End', ''])


def count_script():
    q, r = QUESTS['count'], REF
    L = ['scn FOLabUVTheCountScript'] + ['short %s' % v for v in VARS['count']] + ['short s10', 'short s20', '', 'Begin GameMode']
    L += _ifonce('asked == 1', 's10', ['SetStage %s 10' % q])
    L += ['\tif told == 0', '\t\tif player.GetItemCount %s >= 1' % ITEMS['tally'][0], '\t\t\tset told to 1', '\t\t\tset how to 4', '\t\tendif', '\tendif']
    L += _ifonce('told == 1', 's20', ['SetStage %s 20' % q])
    L += ['\tif done == 0', '\t\tif answered > 0', '\t\t\tset done to 1', '\t\t\tif answered == 1', '\t\t\t\tSetStage %s 100' % q,
          '\t\t\telseif answered == 2', '\t\t\t\tSetStage %s 110' % q, '\t\t\telse', '\t\t\t\tSetStage %s 120' % q, '\t\t\tendif', '\t\tendif', '\tendif']
    return '\n'.join(L + ['End', ''])


def glass_script(read_msg, cant_msg):
    q = QUESTS['glass']
    L = ['scn FOLabUVNavigatorsGlassScript'] + ['short %s' % v for v in VARS['glass']] + ['short s10', 'short s20', '', 'Begin GameMode']
    L += _ifonce('asked == 1', 's10', ['SetStage %s 10' % q])
    L += ['\tif got == 0', '\t\tif player.GetItemCount %s >= 1' % ITEMS['glass'][0], '\t\t\tset got to 1', '\t\tendif', '\tendif']
    L += _ifonce('got == 1', 's20', ['SetStage %s 20' % q])
    # the logbook: read with Science, the cliff trail's pages show the Vault's service door
    L += ['\tif gotbook == 0', '\t\tif player.GetItemCount %s >= 1' % ITEMS['book'][0], '\t\t\tset gotbook to 1',
          '\t\t\tif player.GetActorValue Science >= %d' % GL_READ, '\t\t\t\tset readit to 1', '\t\t\t\tShowMessage %s' % read_msg,
          '\t\t\t\tShowMap %s' % BACK_DOOR, '\t\t\telse', '\t\t\t\tShowMessage %s' % cant_msg, '\t\t\tendif', '\t\tendif', '\tendif']
    L += ['\tif done == 0',
          '\t\tif gavebook == 1', '\t\t\tset done to 1', '\t\t\tSetStage %s 100' % q,
          '\t\telseif gavebook == 2', '\t\t\tset done to 1', '\t\t\tSetStage %s 110' % q,
          '\t\telseif sold == 1', '\t\t\tset done to 1', '\t\t\tSetStage %s 120' % q,
          '\t\tendif', '\tendif']
    return '\n'.join(L + ['End', ''])


def leads_script(clue_items, keepsakes, msgs, markers):
    """clue_items/keepsakes/msgs/markers: {n: editor ID}; markers {n: (clue marker, cache marker)}."""
    q = QUESTS['leads']
    L = ['scn FOLabUVLeadsScript'] + ['short %s' % v for v in VARS['leads']] + ['short step%d%d' % (n, k) for n in range(1, 5) for k in (1, 2, 3)] + ['', 'Begin GameMode']
    for n in range(1, 5):
        c, f, d = 'lead%dc' % n, 'lead%dn' % n, 'lead%dd' % n
        L += _ifonce('%s == 1' % c, 'step%d1' % n, ['SetObjectiveDisplayed %s %d 1' % (q, n * 10)])
        L += ['\tif %s == 0' % f, '\t\tif player.GetItemCount %s >= 1' % clue_items[n], '\t\t\tset %s to 1' % f, '\t\tendif', '\tendif']
        L += _ifonce('%s == 1' % f, 'step%d2' % n, ['ShowMessage %s' % msgs[n], 'ShowMap %s' % markers[n][1],
                                                    'SetObjectiveCompleted %s %d 1' % (q, n * 10), 'SetObjectiveDisplayed %s %d 1' % (q, n * 10 + 5)])
        L += ['\tif %s == 0' % d, '\t\tif player.GetItemCount %s >= 1' % keepsakes[n], '\t\t\tset %s to 1' % d, '\t\tendif', '\tendif']
        L += _ifonce('%s == 1' % d, 'step%d3' % n, ['SetObjectiveCompleted %s %d 1' % (q, n * 10), 'SetObjectiveCompleted %s %d 1' % (q, n * 10 + 5),
                                                    'SetStage %s %d' % (q, n * 10)])
    L += ['\tif done == 0', '\t\tif lead1d == 1 && lead2d == 1 && lead3d == 1 && lead4d == 1', '\t\t\tset done to 1', '\t\t\tSetStage %s 100' % q, '\t\tendif', '\tendif']
    return '\n'.join(L + ['End', ''])


# stage: (journal, ending in STANDING or None, completes)
STAGES = {
    'beacon': [(10, "Hal Brennan, the court's signalman at the Ala Wai, says the Pacific Heights beacon has been dark three nights. It "
                    "warns the city of pirate sails. Keoni Palakiko keeps it, up Pacific Heights Road.", None, False),
               (20, "Keoni lets the beacon go dark on the nights the pirates' boats run in. They pay him in cells.", None, False),
               (100, "I talked Keoni into lighting the beacon. Hal paid me for it.", 'kb_lit', True),
               (102, "I frightened Keoni into lighting the beacon. Hal paid me for it.", 'kb_lit', True),
               (104, "I lit the beacon on Pacific Heights myself. Hal paid me for it.", 'kb_lit', True),
               (110, "I told Hal the pirates pay Keoni to keep the beacon dark. The court put its own man on the beacon.", 'kb_reported', True),
               (120, "I took the pirates' cells and told Hal the beacon is beyond fixing. It stays dark.", 'kb_dark', True),
               (125, "Hal saw through my lie about the beacon. The court took Keoni, and doesn't trust me.", 'kb_caught', True),
               (130, "Keoni is dead. The court put its own man on the beacon.", 'kb_dead', True)],
    'count': [(10, "Leilani Kamakau's son Makana was taken by catchers before tribute day. A man on St. Louis Heights counts everyone "
                   "marched up the crater road. She wants to know if Makana went up.", None, False),
              (20, "Makana was roped and marched up the crater road with six others, three nights after the new moon.", None, False),
              (100, "I told Leilani the truth. She gave me her husband's rifle.", 'am_truth', True),
              (110, "I told Leilani her son is working the Manoa farms. She'll wait for him.", 'am_lie', True),
              (120, "I gave Leilani the watcher's tally. She read her son's name in it.", 'am_tally', True)],
    'glass': [(10, "Fang Jun of the Huang's navigator's house left the house's surveying glass and logbook at the old survey mark up "
                   "Waimanalo's valley, running from the wasps. He wants them back.", None, False),
              (20, "I have the navigator's house's surveying glass.", None, False),
              (100, "I gave Fang Jun the glass and the logbook. The house owes me face.", 'gl_both', True),
              (110, "I gave Fang Jun the glass, and kept the logbook.", 'gl_glass', True),
              (120, "I sold the navigator's house's glass to Linda Moreno for the court.", 'gl_sold', True)],
    'leads': [(10, "I found the arboretum's cold store at the head of Manoa valley.", None, False),
              (20, "I found Grandpa Kenji's still up Palolo valley.", None, False),
              (30, "I found the scout's kit up Kalihi valley.", None, False),
              (40, "I found the Olomana ranch cellar.", None, False),
              (100, "I followed every lead up the valleys.", None, True)],
}
OBJECTIVES = {
    'beacon': [(10, "Find out why the Pacific Heights beacon is dark", 'keoni'), (20, "Go back to Hal Brennan", 'hal')],
    'count': [(10, "Ask the watcher on St. Louis Heights about Makana", 'amos'), (20, "Go back to Leilani", 'leilani')],
    'glass': [(10, "Find the navigator's glass at the old survey mark", 'case'), (20, "Bring the glass to Fang Jun", 'fang')],
    'leads': [(n * 10 + k, t, '%s%d' % ('clue' if k == 0 else 'cache', n))
              for n, (t0, t1) in enumerate([("Find Dr. Kaimana's field notes at the upper Manoa ranger post", "Find the arboretum's cold store up Manoa"),
                                            ("Find Kenji's tin at the bend above the Palolo squatters", "Find Kenji's still up Palolo"),
                                            ("Find the scout's scrap by the old water tank up Kalihi", "Find the scout's kit up Kalihi valley"),
                                            ("Find the cellar key at Olomana ranch's lower gate", "Find the Olomana ranch cellar")], 1)
              for k, t in ((0, t0), (5, t1))],
}


def _standing_lines(ending, have):
    out = []
    for e in (ending or '').split('+'):
        for side, kind, step, score in STANDING.get(e, ()):
            if kind is not None and have.get('rep_' + side):
                out.append('AddReputation %s %d %d' % (REPS[side], kind, step))
            if score and have.get('names'):
                import repstanding
                out.append(repstanding.bump(side, score))
    return '\n'.join(out)


def _stage(n, log, src=''):
    return {'index': n, 'entries': [{'flags': {}, 'conditions': [], 'next': '', 'log': log, 'script': {'source': src, 'parts': None}}]}


def quests_plain(keys, skeys, targets, have):
    out = {}
    for w in QUESTS:
        q = QUESTS[w]
        objs = OBJECTIVES[w]
        stages = []
        for n, log, ending, completes in STAGES[w]:
            src = ''
            if w != 'leads':
                if n == 10:
                    src += 'SetObjectiveDisplayed %s 10 1\n' % q
                if n == 20 or (n >= 100 and w == 'count' and False):
                    src += 'SetObjectiveCompleted %s 10 1\nSetObjectiveDisplayed %s 20 1\n' % (q, q)
            if ending:
                s = _standing_lines(ending, have)
                src += (s + '\n') if s else ''
            if completes:
                src += ''.join('SetObjectiveCompleted %s %d 1\n' % (q, o[0]) for o in objs) + 'CompleteQuest %s\n' % q
            stages.append(_stage(n, log, src))
        tgt = lambda who: [{'target': targets[who], 'flags': 0, 'conditions': []}] if targets.get(who) else []
        out[w] = {'edid': q, 'name': NAMES[w], 'script': skeys[w], 'flags': {'start_enabled': True}, 'priority': 55, 'delay': 1.0,
                  'stages': stages, 'objectives': [{'index': n, 'text': t, 'targets': tgt(who)} for n, t, who in objs], 'conditions': []}
    return out


# ---------- where ----------

def _mod_key(pr, edid, tag=None):
    return next((k for k, r in pr.records.items() if (tag is None or r.get('type') == tag) and recordio.field(r, 'EDID') == edid), None)


def _ref_of(pr, edid):
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if r.get('edid') == edid and not r.get('removed'):
                return ck, rk, r
    return None, None, None


def _ref_by_base(pr, base_key):
    for ck, c in pr.cells.items():
        for rk, r in (c.get('refs') or {}).items():
            if r.get('base') == base_key and not r.get('removed') and r.get('p'):
                return ck, rk, r
    return None, None, None


def _bonus_finds():
    try:
        return [tuple(r['p'][:2]) for r in json.load(open(r'D:\FOLab-bonus\bonus_plan.json', encoding='utf-8'))['rows']]
    except (OSError, ValueError, KeyError):
        return []


class _Clear:
    """What a spot must keep clear of (CLEAR): doors and their arrivals, map markers, road pieces, the bonus finds, each other."""

    def __init__(self, gd, pr, ctx):
        import robots
        self.ctx = ctx
        self.doors, self.marks, self.roads = [], [], []
        for ck, c in pr.cells.items():
            if ck.startswith('+'):
                continue
            for r in (c.get('refs') or {}).values():
                if r.get('removed') or not r.get('p'):
                    continue
                if r.get('marker'):
                    self.marks.append(r['p'][:2])
                b = r.get('base', '')
                if r.get('tel') or (b and robots._tag(gd, pr, b) == 'DOOR'):
                    self.doors.append(r['p'][:2])
        self.roads = [p[:2] for e, v in ctx.refs.items() if re.match(r'(FOLabRoad|NVRoad|Road|WastelandRoad)', e) for _c, p in v]
        self.finds = _bonus_finds()
        self.mine = []

    def near(self, pts, x, y, d):
        return any(abs(p[0] - x) < d and abs(p[1] - y) < d and math.hypot(p[0] - x, p[1] - y) < d for p in pts)

    def ok(self, x, y, own_marker=None, people=False):
        marks = [m for m in self.marks if not (own_marker and math.hypot(m[0] - own_marker[0], m[1] - own_marker[1]) < 1)]
        if self.near(self.doors, x, y, CLEAR['door'] if not people else 400.0):
            return False
        if not people and self.near(marks, x, y, CLEAR['marker']):
            return False
        if self.near(self.roads, x, y, CLEAR['road'] if not people else 300.0):
            return False
        if self.near(self.finds, x, y, CLEAR['find']):
            return False
        return not self.near(self.mine, x, y, CLEAR['apart'] if not people else 250.0)

    def dist(self, x, y):
        f = lambda pts: round(min((math.hypot(p[0] - x, p[1] - y) for p in pts if abs(p[0] - x) < 20000 and abs(p[1] - y) < 20000), default=1e9))
        return {'door': f(self.doors), 'marker': f(self.marks), 'road': f(self.roads), 'find': f(self.finds)}

    def take(self, x, y):
        self.mine.append((x, y))


def _outside_spot(ctx, cl, x, y, radii, own_marker=None, people=False, rise_from=None):
    """A navmesh spot round (x, y) that keeps CLEAR; rise_from (z): only higher ground than that."""
    for r in radii:
        got = ctx.around(x, y, 12, radii=(r,), turns=16)
        for s in got:
            if rise_from is not None and s[2] < rise_from:
                continue
            if cl.ok(s[0], s[1], own_marker, people):
                cl.take(s[0], s[1])
                return (round(s[0], 1), round(s[1], 1), round(s[2], 1))
    return None


def _inside_spot(gd, pr, cell, near, reach=(150.0, 700.0)):
    import robots
    tris = robots._tris(gd, pr, cell)
    doors, actors, seats = robots._things(gd, pr, cell)
    ok = [p for p in tris if reach[0] < math.hypot(p[0] - near[0], p[1] - near[1]) < reach[1]
          and min((robots._d(p, a) for a in actors), default=1e9) > robots.APART
          and min((robots._d(p, d) for d in doors), default=1e9) > robots.DOOR_CLEAR
          and min((robots._d(p, s) for s in seats), default=1e9) > robots.SEAT_CLEAR]
    if not ok:
        return None
    p = min(ok, key=lambda p: (abs(math.hypot(p[0] - near[0], p[1] - near[1]) - 300), p))
    return (round(p[0], 1), round(p[1], 1), round(p[2], 1))


def plan(gd, pr):
    import activity
    import loreterminals as LT
    rows, skipped, S = [], [], {}
    for q in QUESTS.values():
        if _mod_key(pr, q, 'QUST'):
            skipped.append('the mod has %s already' % q)
    for e in [TALK_G, THREAT_G, NAME_Q, TONGBAO] + list(TRAITS.values()) + list(REPS.values()) + list(THEIRS.values()):
        if not _mod_key(pr, e):
            skipped.append('no %s in the mod' % e)
    if not _ref_of(pr, BACK_DOOR)[2]:
        skipped.append('no %s (secretcaches heights)' % BACK_DOOR)
    for k, L in LEADS.items():
        if not LT._term_key(pr, LT.terminals_edid(L['terminal'])):
            skipped.append('no lore terminal %s' % LT.terminals_edid(L['terminal']))
    if skipped:
        return {'rows': rows, 'skipped': skipped, 'spots': S}
    ctx = activity.Ctx(gd, pr)
    cl = _Clear(gd, pr, ctx)
    S['world'] = gd.key(ctx.world)
    mk = ctx.mk
    for k, (marker, radii) in SPOTS.items():
        if marker not in mk:
            skipped.append('no map marker %s' % marker)
            continue
        p = mk[marker][1]
        s = _outside_spot(ctx, cl, p[0], p[1], radii, own_marker=p[:2], people=True)
        if s:
            S[k] = {'world': s, 'near': cl.dist(s[0], s[1])}
        else:
            skipped.append('no room for %s at %s' % (k, marker))
    if 'Pacific Heights Beacon' in mk:
        bp = mk['Pacific Heights Beacon'][1]
        pits = sorted((math.hypot(p[0] - bp[0], p[1] - bp[1]), p) for p in ctx.of(BEACON_PIT[0]))
        if pits and pits[0][0] <= BEACON_PIT[1]:
            q = pits[0][1]
            S['fire'] = {'world': (round(q[0], 1), round(q[1], 1), round(q[2] + 8, 1)), 'near': {'campfire': 0, 'marker': round(pits[0][0])}}
        else:
            skipped.append('no campfire at the beacon')
    s = _outside_spot(ctx, cl, CASE_AT[0], CASE_AT[1], (0, 300, 600, 900, 1300, 1800), rise_from=900)
    (S.__setitem__('case', {'world': s, 'near': cl.dist(s[0], s[1])}) if s else skipped.append('no room for the survey case'))
    places = None
    for k, L in LEADS.items():
        n = L['n']
        at = L['clue']['at']
        if at[0] == 'place':
            from loreterminals import _places_with_doors
            places = places or _places_with_doors(gd, pr)
            pat = re.compile(at[1])
            cands = sorted((math.dist(w, at[2]), ck) for ck, full, w in places if pat.search(full))
            got = None
            if cands and cands[0][0] < 2000:
                ck = cands[0][1]
                term = LT.terminals_edid(L['terminal_inside']) if L.get('terminal_inside') else ''
                t = next((r['p'] for r in pr.cells[ck]['refs'].values() if not r.get('removed') and r.get('p') and term
                          and recordio.field(pr.records.get(r.get('base')) or {'subs': []}, 'EDID') == term), None)
                p = _inside_spot(gd, pr, ck, t or (0, 0, 0))
                if p:
                    got = {'cell': ck, 'p': p, 'outside': tuple(next(w for c2, f, w in places if c2 == ck))}
            if got:
                S['clue%d' % n] = got
            else:
                skipped.append('no room for lead %s\'s clue inside' % k)
        else:
            s = _outside_spot(ctx, cl, at[0], at[1], (0, 300, 600, 900, 1300, 1800, 2400))
            (S.__setitem__('clue%d' % n, {'world': s, 'near': cl.dist(s[0], s[1])}) if s else skipped.append('no room for lead %s\'s clue' % k))
        cz = (S.get('clue%d' % n) or {}).get('world', (0, 0, -1e9))[2] if 'world' in (S.get('clue%d' % n) or {}) else None
        c = L['cache']['at']
        s = _outside_spot(ctx, cl, c[0], c[1], (0, 300, 600, 900, 1300, 1800, 2400), rise_from=(cz + 200) if cz is not None else None)
        (S.__setitem__('cache%d' % n, {'world': s, 'near': cl.dist(s[0], s[1])}) if s else skipped.append('no room for lead %s\'s cache' % k))
    for k, v in S.items():
        if isinstance(v, dict) and ('world' in v or 'p' in v):
            rows.append({k: [round(x) for x in (v.get('world') or v['p'])[:3]], 'in': v.get('cell', 'outside'), 'near': v.get('near')})
    return {'rows': rows, 'skipped': skipped, 'spots': S}


# ---------- the step ----------

def _cond(fn, op, value, p1=0, p2=0, run=0, orr=False):
    op = '=' if op == '==' else op
    return {'or': orr, 'use_target': False, 'op': op, 'fn': fn, 'p1': p1, 'p2': p2, 'run': run, 'ref': '', 'value': float(value)}


def _game_key(gd, edids, tag):
    for e in edids:
        f = next((f for f, (i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == e), None)
        if f is not None:
            return gd.key(f), e
    return None, None


def _game_item(gd, e):
    f = next((f for f, (i, r) in gd.forms.items() if gd.edid(f) == e and r.tag in ('AMMO', 'ALCH', 'MISC', 'WEAP', 'ARMO', 'KEYM')), None)
    return gd.key(f) if f is not None else None


def _spare_faces(gd, pr, races, sex):
    import factionfolk as ff
    rid = {gd.key(f): gd.edid(f) for f, (_i, r) in gd.forms.items() if r.tag == 'RACE'}
    used = set()
    for r in pr.records.values():
        if r.get('type') == 'NPC_':
            used.add(r.get('copied_from'))
            used.add(recordio.field(r, 'TPLT'))
    by = {}
    for f, (_i, r) in sorted(gd.forms.items()):
        if r.tag != 'NPC_' or gd.key(f) in used:
            continue
        e = (gd.edid(f) or '').lower()
        if e.endswith(('dead', 'template')) or 'child' in e:
            continue
        rec = recordio.load(gd, f)
        if recordio.field(rec, 'TPLT'):
            continue
        race = rid.get(recordio.field(rec, 'RNAM'))
        if race not in races or ('F' if ff._num(rec, 'ACBS', 'Flags') & 0x1 else 'M') != sex:
            continue
        by.setdefault(race, []).append(f)
    return [f for race in races for f in by.get(race, ())]


def apply(pr, gd, P=None):
    import activity
    import anquest
    import api_quests as aq
    import api_scripts
    import api_characters as ac
    import factionfolk as ff
    import heldwatch
    import loreterminals as LT
    import newgame
    import pinkpearl as PP
    import questrec as qr
    import struct
    import surffish
    import terminals
    import tes4
    from activity import _new_key
    P = P or plan(gd, pr)
    if P['skipped']:
        raise ValueError('; '.join(P['skipped']))
    S = P['spots']
    out, rep = [], {'made': [], 'missing_items': []}
    world = gd.from_key(S['world'])
    grid = gd.grid(world)

    def record(rec, k=None):
        k = k or _new_key(pr)
        out.append({'op': 'record', 'key': k, 'record': rec})
        rep['made'].append(recordio.field(rec, 'EDID'))
        return k

    def cell_of(spot):
        if 'world' in spot:
            x, y, z = spot['world']
            return gd.key(grid[(int(math.floor(x / 4096.0)), int(math.floor(y / 4096.0)))]), (x, y, z)
        return spot['cell'], spot['p'][:3]

    def place(base, spot, edid, props=None, turn=0.0, extra=None, scale=1.0):
        k = _new_key(pr)
        cell, (x, y, z) = cell_of(spot)
        ref = {'base': base, 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, turn], 's': scale, 'persistent': True, 'edid': edid}
        if props:
            ref['props'] = props
        if extra:
            ref.update(extra)
        out.append({'op': 'place', 'cell': cell, 'key': k, 'ref': ref})
        rep['made'].append(edid)
        return k

    def item_key(e):
        return _mod_key(pr, e) or _game_item(gd, e)

    # ----- items: the quests' own, the leads' clues, keys and keepsakes -----
    misc_like = _game_key(gd, MISC_LIKE, 'MISC')[1]
    keys_of = {}

    def misc(e, n):
        rec = surffish._copy(gd, 'MISC', misc_like, e, n)
        rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'SCRI']
        keys_of[e] = record(rec)
        return keys_of[e]
    for k, (e, n) in ITEMS.items():
        misc(e, n)
    lead_keys = {}
    for k, L in LEADS.items():
        n = L['n']
        clue_e = 'FOLabUVClue%d' % n
        if L['clue']['key']:
            lead_keys[n] = record(PP._key(gd, clue_e, L['clue']['name']))
            keys_of[clue_e] = lead_keys[n]
        else:
            misc(clue_e, L['clue']['name'])
        misc(*L['cache']['keepsake'])
    # messages: each clue's words, the logbook read or not
    msgs = {}
    for k, L in LEADS.items():
        e = 'FOLabUVClue%dMsg' % L['n']
        msgs[L['n']] = e
        record(newgame._message_record(e, L['clue']['words']))
    record(newgame._message_record('FOLabUVLogbookRead', "The logbook is star sightings and angles, generation after generation. The last pages "
                                   "aren't stars: a line of bearings up the windward cliffs to the crater's rim, and a door in the rock marked "
                                   "with a cross. The house has kept the way up to the Vault."))
    record(newgame._message_record('FOLabUVLogbookCant', "The logbook is columns of numbers and star names in pinyin. You can't make head or tail of it."))
    # containers: a game chest copied with contents of its own
    def chest(edid, name, like, contents):
        base = _game_key(gd, like, 'CONT')[0]
        rec = recordio.load(gd, gd.from_key(base))
        rec['src'] = ''
        recordio.set_field(rec, 'EDID', edid, label='Editor ID')
        if any(s['tag'] == 'FULL' for s in rec['subs']):
            recordio.set_field(rec, 'FULL', name)
        else:
            ac.insert(rec, {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name})
        rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('CNTO', 'COED', 'SCRI')]
        for it, cnt in contents:
            kk = keys_of.get(it) or item_key(it)
            if not kk:
                rep['missing_items'].append(it)
                continue
            s = ff._sub('CONT', 'CNTO', struct.pack('<Ii', 0, cnt))
            ff._set_link(s, kk)
            ac.insert(rec, s)
        return record(rec)
    # ----- people -----
    fac = {'court': _mod_key(pr, 'FOLabKahunaCourtFaction', 'FACT'), 'huang': _mod_key(pr, 'FOLabHuangFaction', 'FACT')}
    ctx = activity.Ctx(gd, pr)
    hctx = anquest._faces(gd, pr)
    men, women = heldwatch.men_faces(gd, pr), None
    used = set()

    def face(sex, races, huang):
        nonlocal women
        f = hctx.free_face(races + ('AsianOld',), sex) if huang else ctx.free_face(races, sex)
        if f is None:
            if sex == 'M':
                pool = men
            else:
                import missouriguns
                women = women or missouriguns.women_faces(gd, pr)
                pool = women
            f = next((x for race in races for x in pool.get(race, ()) if gd.key(x) not in used), None)
        if f is None:
            f = next((x for x in _spare_faces(gd, pr, races, sex) if gd.key(x) not in used), None)
        if f is None:
            raise ValueError('no free face for a %s of %s' % (sex, races))
        used.add(gd.key(f))
        return f
    wear = lambda names: [(it, 1) for it in (PP._item_key(gd, pr, n) for n in names) if it]
    clothes = {'court': ('OutfitPrewarCasualwear|OutfitMerc02', 'FOLabWeapNewa|Weap10mmPistol'),
               'keeper': ('OutfitMerc05|OutfitMerc02', 'WeapHuntingRifle|Weap10mmPistol'),
               'camp': ('OutfitPrewarSpring|OutfitMerc03',), 'watcher': ('OutfitMerc05|OutfitMerc02', 'WeapNVVarmintRifle|WeapHuntingRifle'),
               'huang': ('FOLabChangshan',)}
    people = {}
    for k, (e, n, sex, races, kind) in PEOPLE.items():
        huang = kind == 'huang'
        g = dict(ff.GROUPS['huang_folk' if huang else 'court_fighter'])
        g['package'] = 'DefaultSandboxEditorLocation256' if kind in ('court', 'camp') else 'DefaultStayAtEditorLocation'
        rec = ff.person(gd, pr, face(sex, races, huang), e, n, g, wear(clothes[kind]), [], fac.get(kind) or '')
        if not fac.get(kind):
            rec['subs'] = [x for x in rec['subs'] if not (x['tag'] == 'SNAM' and not next((y.get('value') for y in x.get('fields', ()) if y.get('name') == 'Faction'), None))]
        ff._set_num(rec, 'AIDT', 'Aggression', 0 if kind in ('camp', 'huang', 'watcher') else 1)
        ff._set_num(rec, 'AIDT', 'Confidence', 1 if kind in ('camp', 'huang', 'watcher') else 2)
        people[k] = record(rec)
    refs = {}
    for k in ('hal', 'keoni', 'leilani', 'amos', 'fang'):
        refs[k] = place(people[k], S[k], REF[k])
    refs['court_keeper'] = place(people['court_keeper'], S['court_keeper'], REF['court_keeper'], {'enabled': False})
    fire_base = _game_key(gd, FIRES, 'MSTT')[0]
    if fire_base:
        refs['fire'] = place(fire_base, S['fire'], REF['fire'], {'enabled': False}, scale=FIRE_SCALE)
    else:
        rep['missing_items'].append('a fire for the beacon')
    locker = chest('FOLabUVWatcherLocker', "Watcher's Footlocker", CHEST_LIKE, [(ITEMS['tally'][0], 1)])
    refs['locker'] = place(locker, S['locker'], REF['locker'], {'lock': {'level': AM_LOCK, 'key': '', 'leveled': False}})
    case = chest('FOLabUVSurveyCase', 'Survey Case', SATCHEL_LIKE, [(ITEMS['glass'][0], 1), (ITEMS['book'][0], 1)])
    refs['case'] = place(case, S['case'], REF['case'])
    # the leads: markers (hidden till shown), the clue's satchel, the cache
    lead_refs, markers = {}, {}
    for k, L in LEADS.items():
        n = L['n']
        clue_spot = S['clue%d' % n]
        sat = chest('FOLabUVClue%dSatchel' % n, 'Satchel', SATCHEL_LIKE, [('FOLabUVClue%d' % n, 1)])
        lead_refs['clue%d' % n] = place(sat, clue_spot, 'FOLabUVClue%dSatchelREF' % n)
        cache = chest('FOLabUVCache%d' % n, L['cache']['name'], CHEST_LIKE, L['cache']['items'] + [(L['cache']['keepsake'][0], 1)])
        lock = {'level': L['cache']['lock'], 'key': lead_keys.get(n, ''), 'leveled': False}
        lead_refs['cache%d' % n] = place(cache, S['cache%d' % n], 'FOLabUVCache%dREF' % n, {'lock': lock})
        # markers: the clue's (outside: at the satchel, or the place's door) and the cache's
        cm_edid, cm_name, cm_type = L['clue']['marker']
        if 'world' in clue_spot:
            mspot = clue_spot
        else:
            ox, oy = clue_spot['outside']
            mspot = {'world': (ox, oy, ctx.around(ox, oy, 1, radii=(0, 200, 400))[0][2])}
        xm, ym, zm = cell_of(mspot)[1]
        markers[n] = (cm_edid, L['cache']['marker'][0])
        place('FalloutNV.esm:000010', mspot, cm_edid, extra={'marker': {'name': cm_name, 'type': cm_type, 'flags': 2}})
        ca_edid, ca_name, ca_type = L['cache']['marker']
        place('FalloutNV.esm:000010', S['cache%d' % n], ca_edid, extra={'marker': {'name': ca_name, 'type': ca_type, 'flags': 2}})
    # ----- quests, scripts, topics -----
    sc = api_scripts.scripts()
    keys = {w: _new_key(pr) for w in QUESTS}
    skeys = {w: _new_key(pr) for w in QUESTS}
    targets = {k: refs[k] for k in ('hal', 'keoni', 'leilani', 'amos', 'fang', 'case')}
    targets['linda'] = _ref_by_base(pr, _mod_key(pr, THEIRS['linda'], 'NPC_'))[1]
    for n in range(1, 5):
        targets['clue%d' % n], targets['cache%d' % n] = lead_refs['clue%d' % n], lead_refs['cache%d' % n]
    have = {'names': bool(_mod_key(pr, NAME_Q, 'QUST'))}
    have.update({'rep_' + s: bool(_mod_key(pr, e, 'REPU')) for s, e in REPS.items()})
    plains = quests_plain(keys, skeys, targets, have)
    stubs = {w: qr.quest_record(dict(plains[w], stages=[], objectives=[])) for w in QUESTS}
    stub = lambda edid, typ='REFR': {'type': typ, 'flags': tes4.PERSISTENT, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid}]}
    ext = {}
    for o in out:
        if o['op'] == 'place':
            e = o['ref']['edid']
            is_actor = any(o['ref']['base'] == people[k] for k in people)
            ext[o['key']] = stub(e, 'ACHR' if is_actor else 'REFR')
    bd = _ref_of(pr, BACK_DOOR)
    ext[bd[1]] = stub(BACK_DOOR)
    marker_edids = {o['ref']['edid'] for o in out if o['op'] == 'place' and o['ref'].get('marker')} | {BACK_DOOR}
    known = dict(ext)
    known.update({keys[w]: stubs[w] for w in QUESTS})
    known.update({x['key']: x['record'] for x in out if x['op'] == 'record'})
    tkeys = {}
    for t, w in TOPICS.items():
        k = _new_key(pr)
        rec = qr.topic_record({'edid': topic_edid(t), 'name': W[t] if t in W else t, 'priority': 50.0, 'kind': 0,
                               'flags': {'top_level': t in TOP}, 'quests': [{'quest': keys[w], 'links': []}]})
        tkeys[t] = k
        known[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
    srcs = {'beacon': beacon_script(), 'count': count_script(), 'glass': glass_script('FOLabUVLogbookRead', 'FOLabUVLogbookCant'),
            'leads': leads_script({n: 'FOLabUVClue%d' % n for n in range(1, 5)},
                                  {L['n']: L['cache']['keepsake'][0] for L in LEADS.values()}, msgs, markers)}
    srecs = {}
    was_mm = sc.forms.is_map_marker        # (the compiler takes only the game's markers for ShowMap: these are the mod's own)
    sc.forms.is_map_marker = lambda f, was=was_mm: (getattr(f, 'rec', None) is not None and recordio.field(f.rec, 'EDID') in marker_edids) or was(f)
    for w in QUESTS:
        src = srcs[w]
        try:
            c = sc.compile(src, skeys[w], 'quest', known)
        finally:
            if w == list(QUESTS)[-1]:
                sc.forms.is_map_marker = was_mm
        if not hasattr(c, 'subrecords'):
            raise ValueError('%s: %s' % (src.split('\n')[0], c))
        srecs[w] = sc._record_of(c, src.split('\n')[0][4:])
        known[skeys[w]] = srecs[w]
    out += [{'op': 'record', 'key': skeys[w], 'record': srecs[w]} for w in QUESTS]
    out += [{'op': 'record', 'key': keys[w], 'record': stubs[w]} for w in QUESTS]
    rep['made'] += list(QUESTS.values())
    V = {w: PP._vars(srecs[w]) for w in QUESTS}
    nq = _mod_key(pr, NAME_Q, 'QUST')
    nv = PP._vars(pr.records[recordio.field(pr.records[nq], 'SCRI')]) if nq else {}
    named_items = {k: keys_of[e] for k, (e, _n) in ITEMS.items()}

    def conds(cs):
        o = []
        for c in cs:
            k = c[0]
            if k == 'q':
                o.append(_cond(79, c[3], c[4], keys[c[1]], V[c[1]][c[2]]))
            elif k == 'band':
                var = 'band' + c[1]
                o.append(_cond(79, c[2], c[3], nq, nv[var]) if var in nv else _cond(14, '>=', 101, AVI['Speech'], 0, 1))
            elif k == 'perk':
                o.append(_cond(449, '==', c[2], _mod_key(pr, TRAITS[c[1]], 'PERK'), 0, 1))
            elif k == 'glob':
                o.append(_cond(74, c[2], c[3], _mod_key(pr, c[1], 'GLOB')))
            elif k == 'skill':
                o.append(_cond(14, c[2], c[3], AVI[c[1]], 0, 1))
            elif k == 'items':
                o.append(_cond(47, c[2], c[3], named_items.get(c[1]) or item_key(c[1]), 0, 1))
        return o
    who_key = dict(people)
    who_key.update({k: _mod_key(pr, e, 'NPC_') for k, e in THEIRS.items()})
    lines = []
    for who, quest, topic, w, cs, end, skill, choices, bye in lines_spec():
        tp = qr.GREETING if topic == 'G' else tkeys[topic]
        for nm, (e, _n) in ITEMS.items():
            end = re.sub(r'\b%s\b' % nm, e, end)
        l = aq.new_line_plain(gd, pr, tp, keys[quest], who_key[who], words(w), goodbye=bye, conditions=conds(cs))
        if skill:
            import skillcheck
            l['skill'] = skillcheck.skill_key(gd, skill)
        if end:
            l['end'] = {'source': end, 'parts': None}
        l['choices'] = [tkeys[t] for t in choices]
        l.setdefault('begin', None)
        l.setdefault('end', None)
        lines.append(l)
    forms = PP._forms(gd, pr, ext, {x['key']: x['record'] for x in out if x['op'] == 'record'})
    compiled_q = {}
    for w in QUESTS:
        full = json.loads(json.dumps(plains[w]))
        errors = aq.compile_quest(full, forms)
        if errors:
            raise ValueError('%s: %s' % (QUESTS[w], errors))
        compiled_q[w] = full
    compiled = []
    for l in lines:
        errors = aq.compile_line(l, forms)
        if errors:
            raise ValueError('%s: %s (%s)' % (errors[0]['where'], errors[0]['message'], l['responses'][0]['text'][:40]))
        compiled.append(qr.info_record(l))
    # ----- the lore terminals: each lead's first entry, its item script shows the clue's spot -----
    tforms = PP._forms(gd, pr, ext, {x['key']: x['record'] for x in out if x['op'] == 'record'})   # (the leads quest's variables known)
    for e, kr in terminals.mod_forms(gd, pr).own.items():          # (and the mod's named refs, the lore caches' among them)
        tforms.own.setdefault(e, kr)
    was = tforms.is_map_marker
    tforms.is_map_marker = lambda f, was=was: (f.rec is not None and recordio.field(f.rec, 'EDID') in marker_edids) or was(f)
    term_ops = []
    for k, L in LEADS.items():
        site = L['terminal']
        tk = LT._term_key(pr, LT.terminals_edid(site))
        have_rec = pr.records[tk]
        Sx = LT.SITES[site]
        cache_ref = (Sx['cache'][0] + 'REF') if Sx['cache'] else ''
        spec = terminals.plan(LT.text_of(site).replace('{cache}', cache_ref).replace('{HEAD}', LT.HEAD))
        before = terminals.records(gd, tforms, spec, {})['terminal']
        if json.dumps(before['subs'], sort_keys=True) != json.dumps(have_rec['subs'], sort_keys=True):
            raise ValueError('%s is not as loreterminals makes it (run loreword first?)' % LT.terminals_edid(site))
        title, said = L['entry']
        item = {'text': title, 'says': '\n'.join(x.strip() for x in said.strip('\n').split('\n')), 'unlocks': [], 'note': '',
                'script': 'set %s.lead%dc to 1\nShowMap %s' % (QUESTS['leads'], L['n'], L['clue']['marker'][0])}
        at = next((i for i, it in enumerate(spec['items']) if it['unlocks']), len(spec['items']))
        spec['items'].insert(at, item)
        new = terminals.records(gd, tforms, spec, {})['terminal']
        term_ops.append({'op': 'record', 'key': tk, 'record': dict(have_rec, subs=new['subs'])})
        rep['made'].append(LT.terminals_edid(site) + ' (entry)')
    before_info = {k for k, r in pr.records.items() if r.get('type') == 'INFO'}
    pr.apply(LABEL, out)
    pr.apply(LABEL, [{'op': 'record', 'key': keys[w], 'record': qr.quest_record(compiled_q[w])} for w in QUESTS] +
             [{'op': 'record_new', 'record': r} for r in compiled] + term_ops, merge=True)
    global VOICE_ONLY
    VOICE_ONLY = sorted(k for k, r in pr.records.items() if r.get('type') == 'INFO' and k not in before_info) or ['+NOTHING']
    rep.update({'lines': len(compiled), 'people': {k: recordio.field(pr.records[v], 'EDID') for k, v in people.items()},
                'faces': sorted(used), 'at': {k: (v.get('world') or v.get('p'))[:3] for k, v in S.items() if isinstance(v, dict) and ('world' in v or 'p' in v)}})
    return rep
