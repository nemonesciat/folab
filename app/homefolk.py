"""People living in the city's houses (the user, 27 Nov 2026, via the Workshop: "How many interiors now have people living in
them? ... Might be good to give a few of them names, stories, lines, and a couple minor quests. Just to add activity to the
world, that doesn't necessarily involve big stories or factions"; then "Add a couple minor ones too in Huang lands so you can
improve your standing with their people and increase their level of trust for you"; "Maybe one starting at the gate too?").

On 27 Nov 51 of Waikiki's 2,092 places had anyone in them, nearly all hotels, the Vault, the Missouri and the Flotilla; the
houses and shops behind the city's doors stood empty. This step gives thirteen of them residents (`HOMES`): unlocked, empty,
navmeshed, no quest's, a bed inside and islanders living round the door (the Workshop's survey: the Holdouts and the Palolo
camp have no such house near), plus two of the Huáng's four empty family homes.

- **People** (`PEOPLE`, 23): a name, a few lines of who they are (`W`, `M` for Mandarin, shown as pinyin with the meaning in
  brackets), a greeting and two top-level topics in the quest `LIFE` ("Tell me about yourself.", "What do you do all day?").
  Faces: a free one where any is left, else one worn only by people at least `FACE_APART` away, of another surname, in no
  quest of theirs (the user: "let faces repeat if there's enough distance").
- **Days** (`_days`): asleep in their own bed `SLEEP` (the game's sleep package copied), out at work by their door by day
  (`WORK`: a marker of the step's own on the navmesh outside, a sandbox round it), at home otherwise (a sandbox round their
  bed, eating and sitting as sandboxes do). Han Jiaqi keeps his watch at the gate. Nothing is sent across the island.
- **Quests** (`Q`), none tied to the factions or the big story, each with several ways through and modest rewards:
  Word from Hahaione (a letter, Kaimuki to Hahaione), Rain in the Rafters (Koko Marina), Shig's Tackle Box (Kahala), The
  Cabrals' Radio (by the Moana; once mended it plays the island's station: a copy of the game's VintageRadio activator on
  that station, swapped in for a dead one), and in the Huáng's land Pay for Auntie (from Han Jiaqi at Makapuʻu Gate, not one
  of the gate's existing people; it leads to the household, never needed for it), The Dry Well, The Tablet on the Road.
- **Trust with the Huáng:** each honest ending of their three is +1 fame (FOLabRepHuang) and +`FACE` face (repstanding's
  hidden score, which already opens Shangren's trade contract at band 2), and counts in `LIFE`'s `trust`. Their greetings
  warm after the first; with all three, Pan Xiufang's word gives the elder's "Show me what the ship carries" a second way at
  Speech `HOLD_TRUSTED` (a line of this step's beside huangstanding's, its own untouched).
- The world at rest: nothing starts until you ask.

    plan(gd, pr)       {'rows', 'skipped', 'spots'}
    apply(pr, gd, P)   one Undo (VOICE: the step's quests' lines; ZH: the Mandarin)
"""
import json
import math
import re

import recordio
import upvalleys as UV

LABEL = 'People living in the houses, and small quests'
LIFE = 'FOLabHomeLife'
Q = {
    'letter': ('FOLabHFLetter', 'Word from Hahaione'),
    'roof': ('FOLabHFRoof', 'Rain in the Rafters'),
    'tackle': ('FOLabHFTackle', "Shig's Tackle Box"),
    'radio': ('FOLabHFRadio', "The Cabrals' Radio"),
    'pay': ('FOLabHFPay', 'Pay for Auntie'),
    'well': ('FOLabHFWell', 'The Dry Well'),
    'tablet': ('FOLabHFTablet', 'The Tablet on the Road'),
}
QUESTS = {k: v[0] for k, v in Q.items()}
VOICE = [LIFE] + list(QUESTS.values())
VOICE_ONLY = None
ZH = {}
HUANG_Q = ('pay', 'well', 'tablet')
PRIORITY_LIFE, PRIORITY_Q = 57, 60          # (over huangstanding's 55: the elder's second way is LIFE's)
KALA, TONGBAO = 'Caps001', 'FOLabTongbao'
FACE = 5
HOLD_TRUSTED = 70
FACE_APART = 45000.0
SLEEP = (22, 8)
WORK = (8, 8)
NO_SLEEP = 0x2
TALK_G = 'FOLabTraitTalk'

# place: editor ID of the CELL (the Workshop's survey, 27 Nov 2026)
HOMES = {'cabral': 'FOLabWaikikiHouse876', 'callaghan': 'FOLabWaikikiHouse903', 'oyama': 'FOLabWaikikiHouse33',
         'fonoti': 'FOLabWaikikiHouse875', 'pakele': 'FOLabWaikikiHouse256', 'palama': 'FOLabWaikikiHouse259',
         'ramos': 'FOLabWaikikiHouse224', 'matsuda': 'FOLabWaikikiHouse232', 'furtado': 'FOLabWaikikiHouse291',
         'ahsing': 'FOLabWaikikiHouse242', 'sione': 'FOLabWaikikiHouse453', 'sun': 'FOLabHuangHome01', 'gao': 'FOLabHuangHome02'}
LOCALS = ('Caucasian', 'Asian', 'Hispanic', 'AfricanAmerican')
# key: (editor ID, name, sex, races, home or 'gate', kind, wears)
PEOPLE = {
    'manuel': ('FOLabHFManuelCabral', 'Manuel Cabral', 'M', ('Hispanic', 'Caucasian'), 'cabral', 'local', 'FOLabHawaiianShirtKhakiCream|FOLabBoater'),
    'rosa': ('FOLabHFRosaCabral', 'Rosa Cabral', 'F', ('Hispanic', 'Caucasian'), 'cabral', 'local', 'FOLabHawaiianShirtRed'),
    'nora': ('FOLabHFNoraCallaghan', 'Nora Callaghan', 'F', ('Caucasian',), 'callaghan', 'local', 'FOLabHawaiianShirtCream'),
    'ray': ('FOLabHFHideoOyama', 'Hideo Oyama', 'M', ('Asian',), 'oyama', 'local', 'FOLabOldBoardShortsNavy|FOLabLauhala'),
    'grace': ('FOLabHFGraceOyama', 'Grace Oyama', 'F', ('Asian',), 'oyama', 'local', 'FOLabHawaiianShirtBlue|FOLabLauhala'),
    'tetsuo': ('FOLabHFTetsuoOyama', 'Tetsuo Oyama', 'M', ('AsianOld', 'Asian'), 'oyama', 'local', 'FOLabOldHawaiianShirtBlack'),
    'lupe': ('FOLabHFLupeFonoti', 'Lupe Fonoti', 'F', ('Hispanic', 'AfricanAmerican', 'Asian'), 'fonoti', 'local', 'FOLabHawaiianShirtRed'),
    'hiram': ('FOLabHFHiramPakele', 'Hiram Pakele', 'M', ('Hispanic', 'Asian', 'AfricanAmerican'), 'pakele', 'local', 'FOLabHawaiianShirtDenimBlue'),
    'sonny': ('FOLabHFSonnyPalama', 'Sonny Palama', 'M', ('Hispanic', 'Asian', 'AfricanAmerican'), 'palama', 'local', 'FOLabBoardShortsRed'),
    'lani': ('FOLabHFIpoPalama', 'Ipo Palama', 'F', ('Hispanic', 'Asian', 'AfricanAmerican'), 'palama', 'local', 'FOLabHawaiianShirtBlue'),
    'pilar': ('FOLabHFPilarRamos', 'Pilar Ramos', 'F', ('Hispanic',), 'ramos', 'local', 'FOLabHawaiianShirtCream'),
    'joaquin': ('FOLabHFJoaquinRamos', 'Joaquin Ramos', 'M', ('Hispanic',), 'ramos', 'local', 'FOLabHawaiianShirtKhakiRed'),
    'shig': ('FOLabHFShigMatsuda', 'Shig Matsuda', 'M', ('AsianOld', 'Asian'), 'matsuda', 'local', 'FOLabOldHawaiianShirtMaroon|FOLabLauhala'),
    'gus': ('FOLabHFGusFurtado', 'Gus Furtado', 'M', ('Caucasian', 'Hispanic'), 'furtado', 'local', 'FOLabOldHawaiianShirtNavy'),
    'mahina': ('FOLabHFMahinaFurtado', 'Mahina Furtado', 'F', ('Hispanic', 'Asian', 'AfricanAmerican'), 'furtado', 'local', 'FOLabHawaiianShirtBlue'),
    'tommy': ('FOLabHFTommyAhSing', 'Tommy Ah Sing', 'M', ('Asian',), 'ahsing', 'local', 'FOLabOldBoardShortsBlack'),
    'marisol': ('FOLabHFMarisolSione', 'Marisol Sione', 'F', ('Hispanic',), 'sione', 'local', 'FOLabHawaiianShirtRed|FOLabLauhala'),
    'tavita': ('FOLabHFTavitaSione', 'Tavita Sione', 'M', ('AfricanAmerican', 'Hispanic', 'Asian'), 'sione', 'local', 'FOLabBoardShortsBlue'),
    'yuying': ('FOLabHFSunYuying', 'Sun Yuying', 'F', ('Asian', 'AsianOld'), 'sun', 'huang', 'FOLabChangshan|FOLabSilkGown'),
    'dehai': ('FOLabHFKongDehai', 'Kong Dehai', 'M', ('Asian', 'AsianOld'), 'sun', 'huang', 'FOLabChangshan'),
    'xiufang': ('FOLabHFPanXiufang', 'Pan Xiufang', 'F', ('AsianOld', 'Asian'), 'gao', 'huang', 'FOLabSilkGown|FOLabChangshan'),
    'wei': ('FOLabHFPanWei', 'Pan Wei', 'M', ('Asian',), 'gao', 'huang', 'FOLabChangshan'),
    'jiaqi': ('FOLabHFHanJiaqi', 'Han Jiaqi', 'M', ('Asian',), 'gate', 'shouwei', 'FOLabHuangLamellar'),
}
HUANG_FOLK = ('yuying', 'dehai', 'xiufang', 'wei', 'jiaqi')
GATE_GUARD = 'FOLabMakapuuGuard'            # (Through Makapuʻu Gate's guard: Han stands near him, not him)
ELDER, HOLD_KEY, STANDING_Q = 'FOLabHuangElder01', 'FOLabFreighterHoldKey', 'FOLabHuangStanding'

# items: key: (editor ID, name, like (MISC to copy), value)
ITEMS = {'letter': ('FOLabHFPilarsLetter', "Pilar's Letter", 'VRRCMisfitsDrugs', 0),
         'reply': ('FOLabHFMarisolsReply', "Marisol's Reply", 'VRRCMisfitsDrugs', 0),
         'box': ('FOLabHFTackleBox', "Shig's Tackle Box", 'LunchBox', 45),
         'tablet': ('FOLabHFSpiritTablet', 'Spirit Tablet', 'VRRCMisfitsDrugs', 0),
         'newtablet': ('FOLabHFNewTablet', 'New Spirit Tablet', 'VRRCMisfitsDrugs', 0)}
LOCKER_LIKE = ('Footlocker01Empty', 'Footlocker01HouseholdNV')
BASKET_LIKE = ('CampSearchlightNVDuffleBag', 'NVDLC02DuffleBagzGen01', 'Footlocker01Empty')
RADIO_LIKE = 'VintageRadioNVStartONCountry'
STATION = 'Radio Atoll'                 # (the island's station; Haixin Dongtai is the Huáng's)
LOCKER_LOCK = 25
SHORE_Z = (5.0, 160.0)

# ---------- what they say ----------
W = {
    # topics of LIFE
    't_you': "Tell me about yourself.",
    't_work': "What do you do all day?",
    # residents
    'manuel_hi': "Mind the nets. Took me all morning to lay them out.",
    'manuel_you': "Manuel Cabral. I shined shoes at the Moana when its guests paid in dollars. Now the court pays me in fish to mend its boats' nets.",
    'manuel_work': "Nets. Every morning, down on the sand by the Moana. A hole doesn't care who's Kahuna.",
    'rosa_hi': "Shave ice is at the market, not in my kitchen.",
    'rosa_you': "Rosa Cabral. Forty years married to a man who talks to his radio more than to me. It's been dead two years, the radio. He still talks to it.",
    'rosa_work': "Shave ice, by the market stalls. Coconut syrup if the boats brought coconuts. Plain if they didn't.",
    'nora_hi': "If you've come to learn your letters, lessons are in the mornings.",
    'nora_you': "Nora Callaghan. My mother ran the switchboard at the Royal Hawaiian. I was nine when the lines went dead. I've been teaching ever since.",
    'nora_work': "I teach the court's children to read and count, out on the lawn by the lookout. They pay me in rice. It's a fair rate for an alphabet.",
    'ray_hi': "Tide's turning. Be quick.",
    'ray_you': "Hideo Oyama. I fish, Grace weaves, her father tells stories. That's the whole house.",
    'ray_work': "Dawn on the Kapahulu wall with a line and a bucket. Whatever I catch is dinner. Whatever's left goes for kala.",
    'grace_hi': "Careful, that's drying.",
    'grace_you': "Grace Oyama. Born in this house. Married in it too, if you count the porch.",
    'grace_work': "Lauhala hats. The court's people like them wide in the brim. I sit out front where the light's good.",
    'tetsuo_hi': "Sit, sit. Nobody listens to an old bellman any more.",
    'tetsuo_you': "Tetsuo Oyama. Thirty-one years a bellman at the Royal Hawaiian. Film stars, admirals. Now there's a king in it. The tips were better before.",
    'tetsuo_work': "Work? I'm retired. I walk to the beach and back and tell the young people they're doing it wrong.",
    'lupe_hi': "Plate lunch is two kala. Rice, fish, whatever the boats bring.",
    'lupe_you': "Lupe Fonoti. My people came from Samoa three generations back, and my grandmother's recipes came with them. The war didn't take those.",
    'lupe_work': "I cook. People come to the front room, they eat, they pay. Some days they pay in stories. Those I don't take.",
    'hiram_hi': "Don't lean on that. I haven't glued it yet.",
    'hiram_you': "Hiram Pakele. Carpenter. My father built half the lanais in Kaimuki, and I've patched the other half.",
    'hiram_work': "I work on the street out front. The court's men come by and take my best planks for their walls. So I don't leave my best planks out front any more.",
    'sonny_hi': "Water's a kala a bucket. Unless you're family.",
    'sonny_you': "Sonny Palama. Me and Ipo are saving for a boat. A real one, with a sail. Two more years of buckets.",
    'sonny_work': "I haul water up from the spring to the houses round here. Up, down, up, down. Good for the legs.",
    'lani_hi': "Sonny's at the spring. You want water, find him.",
    'lani_you': "Ipo Palama. Sonny thinks the boat was his idea. It was mine.",
    'lani_work': "I salt fish for the storm months, out back where the wind is. And I count the kala jar. Every night.",
    'pilar_hi': "Are you going east? Toward Hahaione?",
    'pilar_you': "Pilar Ramos. A widow. And my daughter's mother, though she forgets.",
    'pilar_work': "I keep the house, and I keep my brother from saying the wrong thing to the court's collectors.",
    'joaquin_hi': "If the collectors sent you, the tribute's paid. Tell them that.",
    'joaquin_you': "Joaquin Ramos. Pilar's brother. I pay this house's tribute and I complain about it, which is my right.",
    'joaquin_work': "I sort salvage on the street out front. Anything metal goes to the court. Anything useful, I keep quiet about.",
    'shig_hi': "My knees, my knees. Ah. A young person.",
    'shig_you': "Shig Matsuda. I fished the Kahala reef for sixty years. Now the reef comes to me in other men's buckets.",
    'shig_work': "I sit by my door and tell the boys where the fish are. They don't listen. Then they come back empty.",
    'gus_hi': "Don't mind the tar on my hands. It doesn't come off.",
    'gus_you': "Gus Furtado. I caulk hulls at the boatyard. Pirates' hulls, mostly. The water doesn't ask whose boat it is.",
    'gus_work': "The boatyard. Pitch and oakum, all day. My house leaks worse than any boat I've ever touched.",
    'mahina_hi': "Mind the bucket. The roof's been dripping on that spot since the last storm.",
    'mahina_you': "Mahina Furtado. Gus fixes every boat in the marina and not one hole in his own roof.",
    'mahina_work': "I mend sails for the boatyard, by the door where there's light. When it rains I mend them in the kitchen, in the one dry corner.",
    'tommy_hi': "Got work? I'll take it. Got none? Then mind the nets.",
    'tommy_you': "Tommy Ah Sing. I mend nets and I do odd jobs. Anything for kala, nothing for free.",
    'tommy_work': "Nets by day, odd jobs whenever someone pays. Roofs, fences, whatever needs a pair of hands.",
    'marisol_hi': "If you're selling, we're not buying. If you're buying, we've got taro.",
    'marisol_you': "Marisol Sione. I grew up in Kaimuki. I married Tavita and his taro, and I came east where the water's good.",
    'marisol_work': "The taro patch, every day. It doesn't weed itself, and Tavita can't be in two places.",
    'tavita_hi': "Talofa. Mind your feet, the patch is muddy.",
    'tavita_you': "Tavita Sione. My family's grown taro here since before the bombs. Marisol's the first in-law who could keep up.",
    'tavita_work': "Taro. Up to my knees in water, all day. You get used to it. Then you get to like it.",
    'wei_hi': "You come for mule? Mule is not for sale.",
    'wei_hi2': "Friend! Mule likes you now. Almost.",
    'wei_you': "Pan Wei. I drive cart. Maize to the hall, fields to house. Aunt Xiufang say I talk too much English. She is right.",
    'wei_work': "Cart, every day. Mule is stubborn. I am more stubborn.",
    'jiaqi_hi': "Stop. ...Ah, you walk the road. Is fine. Walk.",
    'jiaqi_hi2': "Friend of my aunt. Road is open for you, always.",
    'jiaqi_you': "Han Jiaqi. Shouwei. I watch this road, day and night, until relief comes. Relief does not come.",
    'jiaqi_work': "I watch. That is the work. Watching.",
    # ----- Word from Hahaione -----
    'l_ask': "What's in Hahaione?",
    'l_ask_r': "My daughter, Marisol. She married a taro grower out past Koko Head and hasn't written in a year. Take this letter to her. Bring me back her answer, even if it's no.",
    'l_back': "Did she read it? What did she say?",
    'l_reply': "Here's her reply.",
    'l_reply_r': "Her hand. \"Mama, the taro's good this year. Come at the new moon, Tavita will fetch you.\" ...She wants me to come. Take this. It isn't much.",
    'l_says': "She's well. She says she misses you.",
    'l_says_yes': "[SUCCEEDED] She said that? My Marisol? ...Then I can wait for her to say it herself. Thank you.",
    'l_says_no': "[FAILED] You're kind. But she'd never say she misses me. She'd say she's busy. ...Thank you for carrying it, anyway.",
    'l_done': "Hahaione's a long way, but not so long as a year.",
    'l_letter': "Your mother sent this.",
    'l_letter_r': "From Mama. ...She'll want me to say sorry. I'm not the one who should say sorry.",
    'l_coax': "She only wants to hear from you. That's all the letter asks.",
    'l_coax_yes': "[SUCCEEDED] ...That's all? Fine. Give me a moment. ...Here. Tell her the taro's good.",
    'l_coax_no': "[FAILED] You don't know her. I'll write when I'm ready.",
    'l_paper': "Paper's dear out here. Take five kala for it, and write her something.",
    'l_paper_r': "...You'd pay for my letter? You're as stubborn as she is. Fine. Here.",
    # ----- Rain in the Rafters -----
    'r_ask': "Is that roof leaking?",
    'r_ask_r': "Like a basket. Gus says he'll fix it after the next hull. There's always a next hull. Four sheets of scrap metal would patch it, if you've got hands.",
    'r_back': "The roof? Still dripping.",
    'r_metal': "Here's the scrap metal. I'll put it up.",
    'r_metal_r': "Gus! Come and look, someone's fixed the roof! ...Here. And take some fish, I grilled too much.",
    'r_repair': "I'll patch it with what's lying around.",
    'r_repair_yes': "[SUCCEEDED] Off-cuts and tar, and it holds? Gus will never hear the end of this. Thank you.",
    'r_repair_no': "[FAILED] That sheet's rusted through. You'll want proper metal.",
    'r_paid': "I paid Tommy Ah Sing to fix it.",
    'r_paid_r': "So that's who was banging up there all afternoon. You didn't have to. ...Take some fish, at least.",
    'r_done': "Not a drop last night. I slept right through.",
    'r_tommy': "The Furtados' roof needs patching. Will you do it?",
    'r_tommy_r': "For twenty-five kala, I'll have it done by sundown.",
    'r_tommy_pay': "Here's twenty-five.",
    'r_tommy_paid': "Done by sundown. Tommy Ah Sing keeps his word.",
    # ----- Shig's Tackle Box -----
    's_ask': "Can I help you with something?",
    's_ask_r': "My tackle box. It's in my locker down by the canoe landing. My knees won't take the path any more. Bring it up and I'll make it worth your while.",
    's_back': "My box? You found the locker?",
    's_key': "Have you got a key to the locker?",
    's_key_r': "The key? ...Here. Don't lose it, it's the only one.",
    's_box': "Here's your tackle box.",
    's_box_r': "My box! Sixty years of hooks. ...Take this, and thank you. You've saved an old man's pride, and his knees.",
    's_gone': "Your locker was empty. Somebody took the box.",
    's_gone_yes': "[SUCCEEDED] Empty. ...Well. The reef takes everything in the end. Thank you for looking.",
    's_gone_no': "[FAILED] Empty? You've got sand on your boots and my box under your arm. Get out of my door.",
    's_done': "The boys use my hooks now. They still don't listen.",
    # ----- The Cabrals' Radio -----
    'c_ask': "Is that radio working?",
    'c_ask_r': "Dead two years. My father's. If you know anything about wires, I'd be grateful. Rosa says I talk to it. I don't. I talk near it.",
    'c_back': "Any luck with the radio?",
    'c_fix': "I'll fix it. I've got a part.",
    'c_fix_yes': "[SUCCEEDED] ...Is that... turn it up! Turn it up! Rosa! The radio!",
    'c_fix_no': "[FAILED] You've got the part. Your hands don't know where it goes.",
    'c_tubes': "The tubes only need seating again. No parts needed.",
    'c_tubes_yes': "[SUCCEEDED] That's all it was? Two years! ...Listen to that. Here, take this.",
    'c_tubes_no': "[FAILED] Now there's a tube on the floor. Careful.",
    'c_parts': "Here, two pieces of scrap electronics. Can you do it yourself?",
    'c_parts_r': "With these? My father showed me once. Give me the evening. ...There. There it is. Thank you.",
    'c_done': "Listen. That's the island talking.",
    'rosa_radio': "He sings with it now. Badly. I'm not complaining.",
    # ----- Pay for Auntie (Han Jiaqi, broken English; Sun Yuying, Mandarin) -----
    'p_ask': "You look like you need something.",
    'p_ask_r': "Ha. Yes. My pay. Ten tongbao. My aunt, Sun Yuying, in the houses by the wall, she needs it. I cannot leave the road. You carry? She will feed you.",
    'p_yes': "I'll carry it.",
    'p_yes_r': "Good. Ten. I count, she count. Go.",
    'p_back': "My aunt got it?",
    'p_done': "Aunt says you are honest. Is good. ...She has more trouble than tongbao. Go see her house.",
    'p_cold': "Aunt says five come. I gave ten. ...Walk, then.",
    'y_pay': "Han Jiaqi sent his pay.",
    'y_lie': "Five is all he gave me.",
    # ----- The Dry Well -----
    'k_ask': "Your pump looks broken.",
    'k_metal': "I'll free it, with two pieces of scrap metal.",
    'k_repair': "I can free it without any parts.",
    'k_mule': "Pan Wei will lend his mule for the old wheel.",
    'k_wmule': "Kong Dehai's pump has seized. Could your mule turn the old wheel?",
    'k_wmule_yes': "[SUCCEEDED] Mule hates the wheel. ...For Kong, okay. One week. Then he fix pump himself.",
    'k_wmule_no': "[FAILED] Mule is busy. I am busy. No.",
    # ----- The Tablet on the Road -----
    'x_ask': "You look troubled.",
    'x_tablet': "Here's the tablet.",
    'x_new': "Pan Wei carved a new one.",
    'x_rest': "The dogs carried it off. Let it rest.",
    'x_wcarve': "Could you carve your aunt a new tablet?",
    'x_wcarve_r': "New one? I can carve. But wood is dear. Ten tongbao, and I make it tonight.",
    'x_wpay': "Here's ten tongbao.",
    'x_wpay_r': "Good. ...Here. Not so fine as Uncle's. But careful.",
    # ----- the elder's second way -----
    'e_hold': "Show me what the ship carries.",
}
# Mandarin: key: (English, toned pinyin)
M = {
    'yuying_hi': ("You're a stranger. Have you eaten?", "Nǐ shì wàirén. Nǐ chī le ma?"),
    'yuying_hi2': ("You came back. Sit, there is rice.", "Nǐ huílái le. Zuò ba, yǒu fàn."),
    'yuying_you': ("I am Sun Yuying. My family farms the maize by the wall. My nephew stands at the gate.",
                   "Wǒ jiào Sūn Yùyīng. Wǒ jiā zài qiáng biān zhòng yùmǐ. Wǒ zhízi zhàn zài chéngmén."),
    'yuying_work': ("The maize, from dawn. Then cooking. Then the maize again.", "Zǎoshang zhòng yùmǐ. Ránhòu zuò fàn. Ránhòu yòu shì yùmǐ."),
    'dehai_hi': ("Hm. A barbarian.", "Āi. Yí gè mányí."),
    'dehai_hi2': ("Ah. The one who helps. Come.", "À. Bāngmáng de rén. Lái."),
    'dehai_you': ("Kong Dehai. I farm. That is all you need to know.", "Kǒng Déhǎi. Wǒ zhòng dì. Nǐ zhīdào zhèxiē jiù gòu le."),
    'dehai_work': ("The fields. The pump. The fields.", "Tiándì. Shuǐbèng. Tiándì."),
    'xiufang_hi': ("The altar is not for strangers. Speak quietly.", "Shéntái bú shì gěi wàirén de. Xiǎo shēng diǎn."),
    'xiufang_hi2': ("Welcome. This house remembers you.", "Huānyíng. Zhè jiā jìde nǐ."),
    'xiufang_you': ("Pan Xiufang. My husband has been gone four winters. I keep his place at the altar.",
                    "Pān Xiùfāng. Wǒ zhàngfu zǒu le sì gè dōngtiān. Wǒ shǒu zhe tā de shéntái."),
    'xiufang_work': ("I keep the house. I keep the altar. My nephew keeps the mule.", "Wǒ guǎn jiā. Wǒ shǒu shéntái. Wǒ zhízi guǎn luózi."),
    # Pay for Auntie
    'y_whole': ("All ten. He is a good boy. And you are an honest one. Eat with us, any time. My husband's pump has seized, if your hands are good.",
                "Shí gè dōu zài. Tā shì hǎo háizi. Nǐ yě shì lǎoshi rén. Suíshí lái chī fàn. Wǒ zhàngfu de shuǐbèng huài le, rúguǒ nǐ huì xiū."),
    'y_count': ("Five? He said ten. He always says ten.", "Wǔ gè? Tā shuō shí gè. Tā zǒng shì shuō shí gè."),
    'y_lie_yes': ("Then he is spending it on dice again. I will speak to him.", "Nà tā yòu ná qù dǔ le. Wǒ huì gēn tā shuō."),
    'y_lie_no': ("You have a liar's face. Go.", "Nǐ yǒu yì zhāng piànzi de liǎn. Zǒu ba."),
    # The Dry Well
    'k_ask_r': ("Seized. The maize rows are drying. I do not ask a barbarian for help. But if your hands are good, I do not stop you.",
                "Kǎ sǐ le. Yùmǐ dì zài gān. Wǒ bú qiú mányí bāngmáng. Dàn nǐ rúguǒ huì xiū, wǒ bù lán nǐ."),
    'k_back': ("The pump still does not turn.", "Shuǐbèng hái bú zhuàn."),
    'k_fixed': ("It turns. It turns! Hm. Thank you. Take this.", "Zhuàn le. Zhuàn le! Āi. Xièxie. Ná zhe."),
    'k_fail': ("You have made it worse. Leave it.", "Nǐ nòng de gèng huài le. Fàng zhe ba."),
    'k_mule_r': ("The mule. It is slow, but the water comes. Thank you.", "Luózi. Màn, dàn shuǐ lái le. Xièxie."),
    'k_done': ("The maize drinks again.", "Yùmǐ yòu hē shuǐ le."),
    # The Tablet on the Road
    'x_ask_r': ("My husband's spirit tablet. It fell from Pan Wei's cart on the field road. Without it he has no place at the altar. Find it, please.",
                "Wǒ zhàngfu de shénwèi. Cóng Pān Wěi de chē shàng diào zài tián lù shàng le. Méiyǒu tā, tā zài shéntái shàng méiyǒu wèizi. Qǐng nǐ zhǎo yi zhǎo."),
    'x_back': ("Did you find him?", "Nǐ zhǎodào tā le ma?"),
    'x_tablet_r': ("He is home. You have done this house a kindness it will not forget.", "Tā huí jiā le. Nǐ duì zhè jiā de ēnqíng, wǒmen bú huì wàng."),
    'x_new_r': ("Not his. But made with care. It will do, until the old one comes home.", "Bú shì tā de. Dàn zuò de hěn yòngxīn. Xiān yòng zhe, děng jiù de huílái."),
    'x_rest_yes': ("Then the fields keep him. So be it.", "Nà tiándì liú zhe tā ba. Jiù zhèyàng ba."),
    'x_rest_no': ("You did not look. Go and look.", "Nǐ méi zhǎo. Qù zhǎo."),
    'x_done': ("He is at the altar. Thank you.", "Tā zài shéntái shàng. Xièxie nǐ."),
    'e_hold_yes': ("Pan Xiufang says you brought her husband home. A guest she vouches for may look. Here is the key. A guest looks. A guest does not take.",
                   "Pān Xiùfāng shuō nǐ bǎ tā zhàngfu dài huí jiā le. Tā bǎozhèng de kèrén kěyǐ kàn. Zhè shì yàoshi. Kèrén zhǐ kàn, bù ná."),
}
TAGS = {'y_lie_yes': '[SUCCEEDED] ', 'y_lie_no': '[FAILED] ', 'k_fail': '[FAILED] ', 'x_rest_yes': '[SUCCEEDED] ', 'x_rest_no': '[FAILED] '}


def shown(k):
    import huangland
    english, pinyin = M[k]
    return TAGS.get(k, '') + huangland.shown(english, pinyin)


def words(k):
    return shown(k) if k in M else W[k]


def zh_parts(k):
    """As upvalleys': sentence by sentence, shown words with the pinyin said, within a subtitle's 150."""
    import huangland
    english, pinyin = M[k]
    cut = lambda t: [x for x in re.split(r'(?<=[.!?])\s+', t.strip()) if x]
    en, zh = cut(english), cut(pinyin)
    tag = TAGS.get(k, '')
    if len(en) != len(zh):
        return [(tag + huangland.shown(english, pinyin), pinyin)]
    out, now = [], None
    for e, z in zip(en, zh):
        if now and len(huangland.shown(now[0] + ' ' + e, now[1] + ' ' + z)) > 140:
            out.append(now)
            now = None
        now = (now[0] + ' ' + e, now[1] + ' ' + z) if now else (e, z)
    out.append(now)
    return [((tag if n == 0 else '') + huangland.shown(e, z), z) for n, (e, z) in enumerate(out)]


def zh_responses(k):
    return [{'emotion': 0, 'strength': 50, 'number': n + 1, 'sound': '', 'anim': 0, 'text': t} for n, (t, _z) in enumerate(zh_parts(k))]


def _zh():
    for k in M:
        for t, z in zh_parts(k):
            ZH[t] = z


try:
    _zh()
except Exception:                       # noqa: BLE001  (g2pzh unavailable at import: filled when the step runs)
    pass

# ---------- the quests ----------
# rewards: [(item, n)] ('karma', n) for RewardKarma
REWARD = {
    'letter': {1: [(KALA, 40), ('FOLabItemCoconut', 2), ('karma', 10)], 2: [(KALA, 40)], 3: [(KALA, 15)]},
    'roof': {1: [(KALA, 30), ('FOLabGrilledReefFish', 3)], 2: [(KALA, 30), ('FOLabGrilledReefFish', 2)], 3: [('FOLabGrilledReefFish', 2)]},
    'tackle': {1: [(KALA, 35), ('karma', 10)], 2: [], 3: [('karma', -10)]},
    'radio': {1: [(KALA, 25)], 2: [(KALA, 25)], 3: [(KALA, 15)]},
    'pay': {1: [('FOLabGrilledReefFish', 1)], 2: [], 3: []},
    'well': {1: [(TONGBAO, 10)], 2: [(TONGBAO, 5)]},
    'tablet': {1: [(TONGBAO, 10), ('karma', 10)], 2: [(TONGBAO, 5)], 3: []},
}
# Huáng standing by ending: (fame steps, face, counts as trust)
TRUST = {'pay': {1: (1, FACE, True), 2: (0, 0, False), 3: (0, -FACE, False)},
         'well': {1: (1, FACE, True), 2: (1, 3, True)},
         'tablet': {1: (1, FACE, True), 2: (1, 3, True), 3: (0, 0, False)}}
# stage logs; objectives (index, text, target key)
LOGS = {
    'letter': {10: "Pilar Ramos in Kaimuki hasn't heard from her daughter Marisol in a year. She gave me a letter to take to Marisol in Hahaione, and wants her answer.",
               20: "Marisol Sione wrote her mother a reply.",
               101: "I brought Pilar her daughter's reply. Marisol wants her to come at the new moon.",
               102: "I told Pilar her daughter misses her. She believed me.",
               103: "I told Pilar her daughter misses her. She didn't believe me, but she thanked me for carrying the letter."},
    'roof': {10: "The Furtados' roof in Koko Marina leaks. Four sheets of scrap metal would patch it.",
             101: "I patched the Furtados' roof with scrap metal.", 102: "I patched the Furtados' roof with what was lying around.",
             103: "I paid Tommy Ah Sing to patch the Furtados' roof."},
    'tackle': {10: "Shig Matsuda of Kahala can't get down to his locker by the canoe landing any more. He wants his tackle box brought up.",
               20: "I have Shig's tackle box.",
               101: "I brought Shig Matsuda his tackle box.", 102: "I kept Shig's tackle box and told him his locker was empty.",
               103: "Shig Matsuda caught me keeping his tackle box."},
    'radio': {10: "Manuel Cabral's radio, by the Moana, has been dead for two years.",
              101: "I mended the Cabrals' radio with a part.", 102: "I mended the Cabrals' radio by seating its tubes again.",
              103: "I gave Manuel Cabral the parts and he mended his radio himself."},
    'pay': {10: "Han Jiaqi, a Shouwei at Makapuu Gate, gave me his pay, ten tongbao, to carry to his aunt Sun Yuying in Waimanalo.",
            101: "I gave Sun Yuying all of her nephew's pay. She thinks me honest.", 102: "I gave Sun Yuying half her nephew's pay, and told her that was all.",
            103: "Sun Yuying caught me keeping half her nephew's pay."},
    'well': {10: "Kong Dehai's pump in Waimanalo has seized and his maize is drying.",
             101: "I freed Kong Dehai's pump.", 102: "Pan Wei lent his mule to turn Kong Dehai's old wheel."},
    'tablet': {10: "Pan Xiufang's late husband's spirit tablet fell from Pan Wei's cart on the field road. She wants it found.",
               20: "I found the spirit tablet by the field road.",
               101: "I brought Pan Xiufang her husband's tablet.", 102: "Pan Wei carved his aunt a new tablet.",
               103: "I told Pan Xiufang the dogs took the tablet. She let it rest."},
}
OBJ = {
    'letter': [(10, "Take Pilar's letter to Marisol Sione in Hahaione", 'marisol'), (20, "Take Marisol's answer to Pilar", 'pilar')],
    'roof': [(10, "Patch the Furtados' roof", 'mahina')],
    'tackle': [(10, "Fetch Shig's tackle box from his locker by the canoe landing", 'locker'), (20, "Bring Shig his tackle box", 'shig')],
    'radio': [(10, "Mend Manuel Cabral's radio", 'manuel')],
    'pay': [(10, "Take Han Jiaqi's pay to Sun Yuying", 'yuying')],
    'well': [(10, "Get Kong Dehai's pump turning", 'dehai')],
    'tablet': [(10, "Find the spirit tablet on the field road", 'basket'), (20, "Bring Pan Xiufang the tablet", 'xiufang')],
}
WATCH = {'letter': 'reply', 'tackle': 'box', 'tablet': 'tablet'}       # (stage 20 when the player has it)
VARS = {'letter': ('coaxed',), 'roof': ('tommy',), 'tackle': ('haskey',), 'radio': (), 'pay': (), 'well': ('mule',), 'tablet': ('carved',)}
CHECKS = {'l_says': 50, 'l_coax': 40, 'r_repair': 45, 's_gone': 30, 'c_fix': 30, 'c_tubes': 55, 'y_lie': 45, 'k_metal': 30,
          'k_repair': 50, 'k_wmule': 40, 'x_rest': 50}


def lines_spec():
    """[(who, quest or 'life', topic, words key, conds, end script, skill, choices, goodbye)]; conds as upvalleys' plus
    ('life', var, op, v)."""
    L = []

    def line(who, quest, topic, w, conds=(), end='', skill=None, choices=(), bye=False):
        L.append((who, quest, topic, w, list(conds), end, skill, list(choices), bye))
    qv = lambda w, var, op, v: ('q', w, var, op, v)
    S = lambda w: (lambda var, v=1: 'set %s.%s to %s' % (QUESTS[w], var, v))
    give = lambda it, n: 'player.AddItem %s %d' % (it, n)
    take = lambda it, n: 'player.RemoveItem %s %d' % (it, n)
    fin = lambda w, n: S(w)('endv', n)
    talk = lambda n: ('glob', TALK_G, '>=', n)
    sk = lambda s, n: ('skill', s, '>=', n)
    # ----- everyone's own lines (LIFE) -----
    for who in PEOPLE:
        if who in HUANG_FOLK:
            line(who, 'life', 'G', who + '_hi2', [('life', 'trust', '>=', 1)])
        line(who, 'life', 'G', who + '_hi', [], '', None, ['t_you', 't_work'])
        line(who, 'life', 't_you', who + '_you')
        line(who, 'life', 't_work', who + '_work')
    line('rosa', 'life', 'G', 'rosa_radio', [qv('radio', 'endv', '>=', 1)], '', None, ['t_you', 't_work'])
    # ----- Word from Hahaione -----
    A = 'letter'
    open_ = [qv(A, 'endv', '==', 0)]
    line('pilar', A, 'G', 'l_done', [qv(A, 'endv', '>=', 1)], '', None, [], True)
    line('pilar', A, 'G', 'l_back', open_ + [qv(A, 'asked', '==', 1)], '', None, ['l_reply', 'l_says'])
    line('pilar', A, 'G', 'pilar_hi', [qv(A, 'asked', '==', 0)], '', None, ['l_ask', 't_you', 't_work'])
    line('pilar', A, 'l_ask', 'l_ask_r', [qv(A, 'asked', '==', 0)], S(A)('asked') + '\n' + give('letter', 1))
    line('pilar', A, 'l_reply', 'l_reply_r', open_ + [('items', 'reply', '>=', 1)], take('reply', 1) + '\n' + fin(A, 1))
    line('pilar', A, 'l_says', 'l_says_yes', open_ + [qv(A, 'asked', '==', 1), talk(CHECKS['l_says'])], take('letter', 1) + '\n' + fin(A, 2), 'Speech')
    line('pilar', A, 'l_says', 'l_says_no', open_ + [qv(A, 'asked', '==', 1)], take('letter', 1) + '\n' + fin(A, 3), 'Speech')
    gotr = [('items', 'letter', '>=', 1), qv(A, 'got', '==', 0)]
    line('marisol', A, 'l_letter', 'l_letter_r', gotr, '', None, ['l_coax', 'l_paper'])
    line('marisol', A, 'l_coax', 'l_coax_yes', gotr + [qv(A, 'coaxed', '==', 0), talk(CHECKS['l_coax'])], take('letter', 1) + '\n' + give('reply', 1), 'Speech')
    line('marisol', A, 'l_coax', 'l_coax_no', gotr + [qv(A, 'coaxed', '==', 0)], S(A)('coaxed'), 'Speech', ['l_paper'])
    line('marisol', A, 'l_paper', 'l_paper_r', gotr + [('items', KALA, '>=', 5)], take(KALA, 5) + '\n' + take('letter', 1) + '\n' + give('reply', 1))
    # ----- Rain in the Rafters -----
    R = 'roof'
    open_ = [qv(R, 'endv', '==', 0)]
    line('mahina', R, 'G', 'r_done', [qv(R, 'endv', '>=', 1)], '', None, ['t_you', 't_work'])
    line('mahina', R, 'G', 'r_back', open_ + [qv(R, 'asked', '==', 1)], '', None, ['r_metal', 'r_repair', 'r_paid'])
    line('mahina', R, 'r_ask', 'r_ask_r', [qv(R, 'asked', '==', 0)], S(R)('asked'), None, ['r_metal', 'r_repair'])
    line('mahina', R, 'G', 'mahina_hi', [qv(R, 'asked', '==', 0)], '', None, ['r_ask', 't_you', 't_work'])
    line('mahina', R, 'r_metal', 'r_metal_r', open_ + [('items', 'SpareParts', '>=', 4)], take('SpareParts', 4) + '\n' + fin(R, 1))
    line('mahina', R, 'r_repair', 'r_repair_yes', open_ + [sk('Repair', CHECKS['r_repair'])], fin(R, 2), 'Repair')
    line('mahina', R, 'r_repair', 'r_repair_no', open_, '', 'Repair')
    line('mahina', R, 'r_paid', 'r_paid_r', open_ + [qv(R, 'tommy', '==', 1)], fin(R, 3))
    line('tommy', R, 'r_tommy', 'r_tommy_r', open_ + [qv(R, 'asked', '==', 1), qv(R, 'tommy', '==', 0)], '', None, ['r_tommy_pay'])
    line('tommy', R, 'r_tommy_pay', 'r_tommy_paid', open_ + [qv(R, 'tommy', '==', 0), ('items', KALA, '>=', 25)], take(KALA, 25) + '\n' + S(R)('tommy'))
    # ----- Shig's Tackle Box -----
    T = 'tackle'
    open_ = [qv(T, 'endv', '==', 0)]
    line('shig', T, 'G', 's_done', [qv(T, 'endv', '==', 1)], '', None, ['t_you', 't_work'])
    line('shig', T, 'G', 's_back', open_ + [qv(T, 'asked', '==', 1)], '', None, ['s_box', 's_gone', 's_key'])
    line('shig', T, 'G', 'shig_hi', [qv(T, 'asked', '==', 0)], '', None, ['s_ask', 't_you', 't_work'])
    line('shig', T, 's_ask', 's_ask_r', [qv(T, 'asked', '==', 0)], S(T)('asked'), None, ['s_key'])
    line('shig', T, 's_key', 's_key_r', open_ + [qv(T, 'asked', '==', 1), qv(T, 'haskey', '==', 0)], S(T)('haskey') + '\n' + give('key', 1))
    line('shig', T, 's_box', 's_box_r', open_ + [('items', 'box', '>=', 1)], take('box', 1) + '\n' + fin(T, 1))
    line('shig', T, 's_gone', 's_gone_yes', open_ + [('items', 'box', '>=', 1), talk(CHECKS['s_gone'])], fin(T, 2), 'Speech')
    line('shig', T, 's_gone', 's_gone_no', open_ + [('items', 'box', '>=', 1)], fin(T, 3), 'Speech', [], True)
    # ----- The Cabrals' Radio -----
    C = 'radio'
    open_ = [qv(C, 'endv', '==', 0)]
    line('manuel', C, 'G', 'c_done', [qv(C, 'endv', '>=', 1)], '', None, ['t_you', 't_work'])
    line('manuel', C, 'G', 'c_back', open_ + [qv(C, 'asked', '==', 1)], '', None, ['c_fix', 'c_tubes', 'c_parts'])
    line('manuel', C, 'G', 'manuel_hi', [qv(C, 'asked', '==', 0)], '', None, ['c_ask', 't_you', 't_work'])
    line('manuel', C, 'c_ask', 'c_ask_r', [qv(C, 'asked', '==', 0)], S(C)('asked'), None, ['c_fix', 'c_tubes', 'c_parts'])
    part = [('items', 'ScrapElectronics', '>=', 1)]
    line('manuel', C, 'c_fix', 'c_fix_yes', open_ + part + [sk('Repair', CHECKS['c_fix'])], take('ScrapElectronics', 1) + '\n' + fin(C, 1), 'Repair')
    line('manuel', C, 'c_fix', 'c_fix_no', open_ + part, '', 'Repair')
    line('manuel', C, 'c_tubes', 'c_tubes_yes', open_ + [sk('Science', CHECKS['c_tubes'])], fin(C, 2), 'Science')
    line('manuel', C, 'c_tubes', 'c_tubes_no', open_, '', 'Science')
    line('manuel', C, 'c_parts', 'c_parts_r', open_ + [('items', 'ScrapElectronics', '>=', 2)], take('ScrapElectronics', 2) + '\n' + fin(C, 3))
    # ----- Pay for Auntie -----
    P = 'pay'
    open_ = [qv(P, 'endv', '==', 0)]
    line('jiaqi', P, 'G', 'p_done', [qv(P, 'endv', '==', 1)], '', None, ['t_you', 't_work'])
    line('jiaqi', P, 'G', 'p_cold', [qv(P, 'endv', '>=', 2)], '', None, [], True)
    line('jiaqi', P, 'G', 'p_back', open_ + [qv(P, 'asked', '==', 1)], '', None, ['t_you', 't_work'])
    line('jiaqi', P, 'G', 'jiaqi_hi', [qv(P, 'asked', '==', 0)], '', None, ['p_ask', 't_you', 't_work'])
    line('jiaqi', P, 'p_ask', 'p_ask_r', [qv(P, 'asked', '==', 0)], '', None, ['p_yes'])
    line('jiaqi', P, 'p_yes', 'p_yes_r', [qv(P, 'asked', '==', 0)], S(P)('asked') + '\n' + give(TONGBAO, 10))
    line('yuying', P, 'y_pay', 'y_whole', open_ + [qv(P, 'asked', '==', 1), ('items', TONGBAO, '>=', 10)], take(TONGBAO, 10) + '\n' + fin(P, 1))
    line('yuying', P, 'y_pay', 'y_count', open_ + [qv(P, 'asked', '==', 1), ('items', TONGBAO, '>=', 5)], '', None, ['y_lie'])
    line('yuying', P, 'y_lie', 'y_lie_yes', open_ + [('items', TONGBAO, '>=', 5), talk(CHECKS['y_lie'])], take(TONGBAO, 5) + '\n' + fin(P, 2), 'Speech')
    line('yuying', P, 'y_lie', 'y_lie_no', open_ + [('items', TONGBAO, '>=', 5)], take(TONGBAO, 5) + '\n' + fin(P, 3), 'Speech', [], True)
    # ----- The Dry Well -----
    D = 'well'
    open_ = [qv(D, 'endv', '==', 0)]
    line('dehai', D, 'G', 'k_done', [qv(D, 'endv', '>=', 1)], '', None, ['t_you', 't_work'])
    line('dehai', D, 'G', 'k_back', open_ + [qv(D, 'asked', '==', 1)], '', None, ['k_metal', 'k_repair', 'k_mule'])
    line('dehai', D, 'k_ask', 'k_ask_r', [qv(D, 'asked', '==', 0)], S(D)('asked'), None, ['k_metal', 'k_repair'])
    line('dehai', D, 'k_metal', 'k_fixed', open_ + [('items', 'SpareParts', '>=', 2), sk('Repair', CHECKS['k_metal'])],
         take('SpareParts', 2) + '\n' + fin(D, 1), 'Repair')
    line('dehai', D, 'k_metal', 'k_fail', open_ + [('items', 'SpareParts', '>=', 2)], '', 'Repair')
    line('dehai', D, 'k_repair', 'k_fixed', open_ + [sk('Repair', CHECKS['k_repair'])], fin(D, 1), 'Repair')
    line('dehai', D, 'k_repair', 'k_fail', open_, '', 'Repair')
    line('dehai', D, 'k_mule', 'k_mule_r', open_ + [qv(D, 'mule', '==', 1)], fin(D, 2))
    line('wei', D, 'k_wmule', 'k_wmule_yes', open_ + [qv(D, 'asked', '==', 1), qv(D, 'mule', '==', 0), talk(CHECKS['k_wmule'])], S(D)('mule'), 'Speech')
    line('wei', D, 'k_wmule', 'k_wmule_no', open_ + [qv(D, 'asked', '==', 1), qv(D, 'mule', '==', 0)], '', 'Speech')
    # ----- The Tablet on the Road -----
    X = 'tablet'
    open_ = [qv(X, 'endv', '==', 0)]
    line('xiufang', X, 'G', 'x_done', [qv(X, 'endv', '>=', 1), qv(X, 'endv', '<=', 2)], '', None, ['t_you', 't_work'])
    line('xiufang', X, 'G', 'x_back', open_ + [qv(X, 'asked', '==', 1)], '', None, ['x_tablet', 'x_new', 'x_rest'])
    line('xiufang', X, 'x_ask', 'x_ask_r', [qv(X, 'asked', '==', 0)], S(X)('asked'), None, ['x_tablet', 'x_rest'])
    line('xiufang', X, 'x_tablet', 'x_tablet_r', open_ + [('items', 'tablet', '>=', 1)], take('tablet', 1) + '\n' + fin(X, 1))
    line('xiufang', X, 'x_new', 'x_new_r', open_ + [('items', 'newtablet', '>=', 1)], take('newtablet', 1) + '\n' + fin(X, 2))
    line('xiufang', X, 'x_rest', 'x_rest_yes', open_ + [qv(X, 'asked', '==', 1), talk(CHECKS['x_rest'])], fin(X, 3), 'Speech')
    line('xiufang', X, 'x_rest', 'x_rest_no', open_ + [qv(X, 'asked', '==', 1)], '', 'Speech')
    line('wei', X, 'x_wcarve', 'x_wcarve_r', open_ + [qv(X, 'asked', '==', 1), qv(X, 'carved', '==', 0)], '', None, ['x_wpay'])
    line('wei', X, 'x_wpay', 'x_wpay_r', open_ + [qv(X, 'carved', '==', 0), ('items', TONGBAO, '>=', 10)],
         take(TONGBAO, 10) + '\n' + give('newtablet', 1) + '\n' + S(X)('carved'))
    # topic lines with no answer hold the topic's place for those not asked (nothing: the topic doesn't show)
    return L


# the topics: key -> (quest, prompt words key, top level)
TOPICS = {'t_you': ('life', True), 't_work': ('life', True),
          'l_ask': ('letter', False), 'l_reply': ('letter', False), 'l_says': ('letter', False), 'l_letter': ('letter', True),
          'l_coax': ('letter', False), 'l_paper': ('letter', False),
          'r_ask': ('roof', False), 'r_metal': ('roof', False), 'r_repair': ('roof', False), 'r_paid': ('roof', False),
          'r_tommy': ('roof', True), 'r_tommy_pay': ('roof', False),
          's_ask': ('tackle', False), 's_key': ('tackle', False), 's_box': ('tackle', False), 's_gone': ('tackle', False),
          'c_ask': ('radio', False), 'c_fix': ('radio', False), 'c_tubes': ('radio', False), 'c_parts': ('radio', False),
          'p_ask': ('pay', False), 'p_yes': ('pay', False), 'y_pay': ('pay', True), 'y_lie': ('pay', False),
          'k_ask': ('well', True), 'k_metal': ('well', False), 'k_repair': ('well', False), 'k_mule': ('well', False),
          'k_wmule': ('well', True),
          'x_ask': ('tablet', True), 'x_tablet': ('tablet', False), 'x_new': ('tablet', False), 'x_rest': ('tablet', False),
          'x_wcarve': ('tablet', True), 'x_wpay': ('tablet', False)}
SKILL_TOPIC = {'l_says': 'Speech', 'l_coax': 'Speech', 'r_repair': 'Repair', 's_gone': 'Speech', 'c_fix': 'Repair', 'c_tubes': 'Science',
               'y_lie': 'Speech', 'k_metal': 'Repair', 'k_repair': 'Repair', 'k_wmule': 'Speech', 'x_rest': 'Speech'}


def topic_name(t):
    n = W[t]
    if t in SKILL_TOPIC:
        n = '[%s %d] %s' % (SKILL_TOPIC[t], CHECKS[t], n)
    return n


def topic_edid(t):
    return 'FOLabHF' + ''.join(p.capitalize() for p in t.split('_'))


def quest_script(w, items):
    q = QUESTS[w]
    vs = ['asked', 'got', 'endv', 'done', 's10', 's20'] + list(VARS[w])
    L = ['scn %sScript' % q] + ['short %s' % v for v in vs] + ['', 'Begin GameMode']
    L += UV._ifonce('asked == 1', 's10', ['SetStage %s 10' % q])
    if w in WATCH:
        L += ['\tif got == 0', '\t\tif player.GetItemCount %s >= 1' % items[WATCH[w]], '\t\t\tset got to 1', '\t\tendif', '\tendif']
        L += UV._ifonce('got == 1 && endv == 0', 's20', ['SetStage %s 20' % q])
    ends = sorted(REWARD[w])
    L += ['\tif done == 0 && endv > 0', '\t\tset done to 1']
    for n, e in enumerate(ends):
        L += ['\t\t%s endv == %d' % ('if' if n == 0 else 'elseif', e), '\t\t\tSetStage %s %d' % (q, 100 + e)]
    L += ['\t\tendif', '\tendif']
    return '\n'.join(L + ['End', ''])


def life_script(radio):
    L = ['scn %sScript' % LIFE, 'short trust', 'short radioon', '', 'Begin GameMode']
    if radio:
        dead, live = radio
        L += ['\tif radioon == 0', '\t\tif %s.endv > 0' % QUESTS['radio'], '\t\t\tset radioon to 1', '\t\t\t%s.Disable' % dead,
              '\t\t\t%s.Enable' % live, '\t\tendif', '\tendif']
    return '\n'.join(L + ['End', ''])


def _end_script(w, e, have, items):
    out = []
    for it, n in REWARD[w].get(e, ()):
        if it == 'karma':
            out.append('RewardKarma %d' % n)
        else:
            out.append('player.AddItem %s %d' % (items.get(it, it), n))
    if w in TRUST and e in TRUST[w]:
        fame, face, counts = TRUST[w][e]
        if fame and have.get('rep'):
            out.append('AddReputation FOLabRepHuang 1 %d' % fame)
        if face and have.get('names'):
            import repstanding
            out.append(repstanding.bump('huang', face))
        if counts:
            out.append('set %s.trust to %s.trust + 1' % (LIFE, LIFE))
    return '\n'.join(out)


def quests_plain(keys, skeys, targets, have, items):
    out = {}
    for w in QUESTS:
        q = QUESTS[w]
        objs = OBJ[w]
        stages = []
        for n, log in sorted(LOGS[w].items()):
            src = ''
            if n == 10:
                src += 'SetObjectiveDisplayed %s 10 1\n' % q
            elif n == 20:
                src += 'SetObjectiveCompleted %s 10 1\nSetObjectiveDisplayed %s 20 1\n' % (q, q)
            else:
                s = _end_script(w, n - 100, have, items)
                src += (s + '\n') if s else ''
                src += ''.join('SetObjectiveCompleted %s %d 1\n' % (q, o[0]) for o in objs) + 'CompleteQuest %s\n' % q
            stages.append(UV._stage(n, log, src))
        tgt = lambda who: [{'target': targets[who], 'flags': 0, 'conditions': []}] if targets.get(who) else []
        out[w] = {'edid': q, 'name': Q[w][1], 'script': skeys[w], 'flags': {'start_enabled': True}, 'priority': PRIORITY_Q, 'delay': 1.0,
                  'stages': stages, 'objectives': [{'index': n, 'text': t, 'targets': tgt(who)} for n, t, who in objs], 'conditions': []}
    return out


# ---------- where ----------

def _place_key(pr, edid):
    return next((k for k, r in pr.records.items() if k.startswith('+') and r.get('type') == 'CELL' and recordio.field(r, 'EDID') == edid), None)


def _base_edid(gd, pr, b):
    if not b:
        return ''
    if b in pr.records:
        return recordio.field(pr.records[b], 'EDID') or ''
    try:
        return gd.edid(gd.from_key(b)) or ''
    except Exception:                   # noqa: BLE001
        return ''


def _base_tag(gd, pr, b):
    if b in pr.records:
        return pr.records[b].get('type')
    try:
        return gd.forms[gd.from_key(b)][1].tag
    except Exception:                   # noqa: BLE001
        return None


def _way_in(pr, place):
    """(inside door ref, outside door ref, outside cell, outside position) of a place's way in from outside."""
    cellof = {}
    for ck, ent in pr.cells.items():
        for rk, r in (ent.get('refs') or {}).items():
            if isinstance(r, dict):
                cellof[rk] = ck
    for rk, r in ((pr.cells.get(place) or {}).get('refs') or {}).items():
        if not isinstance(r, dict) or r.get('removed'):
            continue
        d = (r.get('tel') or {}).get('door')
        if d and d in cellof and not cellof[d].startswith('+'):
            o = pr.cells[cellof[d]]['refs'][d]
            if o.get('p'):
                return rk, d, cellof[d], o['p']
    return None


def _beds(gd, pr, place):
    out = []
    for rk, r in ((pr.cells.get(place) or {}).get('refs') or {}).items():
        if not isinstance(r, dict) or r.get('removed') or not r.get('p'):
            continue
        e = _base_edid(gd, pr, r.get('base'))
        if _base_tag(gd, pr, r.get('base')) == 'FURN' and re.search(r'bed|mattress|cot|bunk', e, re.I):
            out.append((rk, r['p']))
    return sorted(out, key=lambda x: x[0])


def _tables(gd, pr, place):
    out = []
    for rk, r in ((pr.cells.get(place) or {}).get('refs') or {}).items():
        if not isinstance(r, dict) or r.get('removed') or not r.get('p'):
            continue
        e = _base_edid(gd, pr, r.get('base'))
        if re.search(r'table|desk|counter|dresser|endtable', e, re.I) and not re.search(r'chair|lamp', e, re.I):
            out.append((rk, r))
    return out


def _top_of(gd, pr, ref):
    """The height of a ref's top: its base's OBND z max, scaled."""
    b = ref.get('base')
    rec = pr.records.get(b) if b in pr.records else recordio.load(gd, gd.from_key(b))
    ob = next((s for s in rec['subs'] if s['tag'] == 'OBND'), None)
    if not ob:
        return None
    vals = {f['name']: f['value'] for f in ob.get('fields', [])} if ob.get('fields') else {}
    zt = next((v for k, v in vals.items() if k.lower() in ('z2', 'max z', 'zmax', 'z max')), None)
    if zt is None and isinstance(ob.get('value'), (list, tuple)) and len(ob['value']) == 6:
        zt = ob['value'][5]
    return None if zt is None else ref['p'][2] + zt * float(ref.get('s') or 1.0)


def _spot_in(gd, pr, cell, near, taken, reach=(60.0, 500.0)):
    """A walked spot in a place near `near`, clear of doors, others standing, seats and `taken` (each person their own)."""
    import robots
    tris = robots._tris(gd, pr, cell)
    doors, actors, seats = robots._things(gd, pr, cell)
    for lo, hi, door in ((reach[0], reach[1], robots.DOOR_CLEAR), (30.0, reach[1] * 2, 180.0), (0.0, 1e9, 120.0)):
        ok = [p for p in tris if lo < math.hypot(p[0] - near[0], p[1] - near[1]) < hi
              and min((robots._d(p, a) for a in actors), default=1e9) > robots.APART
              and min((robots._d(p, d) for d in doors), default=1e9) > door
              and min((robots._d(p, s) for s in seats), default=1e9) > 60.0
              and min((math.dist(p[:2], t[:2]) for t in taken), default=1e9) > 110.0]
        if ok:
            p = min(ok, key=lambda p: (abs(math.hypot(p[0] - near[0], p[1] - near[1]) - 200), p))
            return (round(p[0], 1), round(p[1], 1), round(p[2], 1))
    return None


def _shelf(gd, pr, cell):
    """Something in the place with a top 55-115 over its foot and room on it (a table, dresser, counter, shelf): (ref, top)."""
    out = []
    for rk, r in sorted(((pr.cells.get(cell) or {}).get('refs') or {}).items()):
        if not isinstance(r, dict) or r.get('removed') or not r.get('p') or not r.get('base'):
            continue
        if _base_tag(gd, pr, r['base']) not in ('STAT', 'FURN', 'CONT', 'MSTT'):
            continue
        e = _base_edid(gd, pr, r['base'])
        if not re.search(r'table|desk|counter|dresser|shelf|shelves|cabinet|nightstand|drawers|sideboard|bureau', e, re.I) or \
                re.search(r'bed|chair|stool|bench|couch|sofa|settee|seat|door|lamp|light|broken|wrecked|pot\b', e, re.I):
            continue
        try:
            rec = pr.records.get(r['base']) if r['base'] in pr.records else recordio.load(gd, gd.from_key(r['base']))
        except Exception:               # noqa: BLE001
            continue
        ob = next((s for s in rec['subs'] if s['tag'] == 'OBND' and s.get('fields')), None)
        if not ob:
            continue
        v = {f['name']: f['value'] for f in ob['fields']}
        sc = float(r.get('s') or 1.0)
        top = v['Z2'] * sc
        centred = abs(v['X1'] + v['X2']) * sc < 16 and abs(v['Y1'] + v['Y2']) * sc < 16      # (the radio stands on its origin)
        if centred and 55 <= top - v['Z1'] * sc <= 115 and (v['X2'] - v['X1']) * sc >= 30 and (v['Y2'] - v['Y1']) * sc >= 30 and abs(v['Z1'] * sc) < 20:
            out.append((rk, r, r['p'][2] + top, e))
    return out


def _shore(ctx, cl, x, y):
    for r in (600, 900, 1300, 1800, 2400, 3200, 4200):
        for s in ctx.around(x, y, 24, radii=(r,), turns=24):
            if SHORE_Z[0] < s[2] < SHORE_Z[1] and cl.ok(s[0], s[1], people=True):
                cl.take(s[0], s[1])
                return (round(s[0], 1), round(s[1], 1), round(s[2], 1))
    return None


def plan(gd, pr):
    import activity
    rows, skipped, S = [], [], {}
    for q in list(QUESTS.values()) + [LIFE]:
        if UV._mod_key(pr, q, 'QUST'):
            skipped.append('the mod has %s already' % q)
    for e in (TONGBAO, TALK_G, 'FOLabHuangFaction', 'FOLabRepHuang', 'FOLabNameOnWater'):
        if not UV._mod_key(pr, e):
            skipped.append('no %s in the mod' % e)
    names = {(recordio.field(r, 'FULL') or '').lower() for k, r in pr.records.items() if r.get('type') == 'NPC_' and r.get('subs')}
    for k, p in PEOPLE.items():
        if p[1].lower() in names:
            skipped.append('someone in the mod is already called %s' % p[1])
    if skipped:
        return {'rows': rows, 'skipped': skipped, 'spots': S}
    ctx = activity.Ctx(gd, pr)
    cl = UV._Clear(gd, pr, ctx)
    S['world'] = gd.key(ctx.world)
    homes = {}
    for h, edid in HOMES.items():
        ck = _place_key(pr, edid)
        if not ck:
            skipped.append('no place %s' % edid)
            continue
        way = _way_in(pr, ck)
        if not way:
            skipped.append('no way in to %s' % edid)
            continue
        refs = (pr.cells.get(ck) or {}).get('refs') or {}
        if any(isinstance(r, dict) and not r.get('removed') and _base_tag(gd, pr, r.get('base')) in ('NPC_', 'CREA', 'LVLN', 'LVLC') for r in refs.values()):
            skipped.append('someone lives in %s already' % edid)
            continue
        if not pr.navmesh.get(ck):
            skipped.append('%s has no navmesh' % edid)
            continue
        beds = _beds(gd, pr, ck)
        if not beds:
            skipped.append('no bed in %s' % edid)
            continue
        homes[h] = {'cell': ck, 'edid': edid, 'door': way[1], 'door_p': way[3][:3], 'beds': beds}
    S['homes'] = homes
    # each person: a spot inside by a bed, their bed, a work marker outside
    who_at = {}
    for k, p in PEOPLE.items():
        h = p[4]
        if h == 'gate':
            continue
        if h not in homes:
            continue
        H = homes[h]
        mates = [x for x in PEOPLE if PEOPLE[x][4] == h]
        bed = H['beds'][mates.index(k) % len(H['beds'])]
        taken = [v['p'] for v in who_at.values() if v.get('cell') == H['cell']]
        spot = _spot_in(gd, pr, H['cell'], bed[1][:3], taken)
        if not spot:
            skipped.append('no room for %s in %s' % (p[1], H['edid']))
            continue
        dx, dy = H['door_p'][:2]
        work = UV._outside_spot(ctx, cl, dx, dy, (500, 700, 900, 1200, 1600, 2000, 2600, 3200, 4000), people=True)
        if not work:
            skipped.append('no work spot outside for %s' % p[1])
            continue
        who_at[k] = {'cell': H['cell'], 'p': spot, 'bed': bed[0], 'work': {'world': work}, 'door_xy': [dx, dy]}
    # Han Jiaqi at the gate, near (not as) its guard
    gk = UV._mod_key(pr, GATE_GUARD, 'NPC_')
    gref = UV._ref_by_base(pr, gk) if gk else (None, None, None)
    if gref[2] is None:
        skipped.append('no %s placed (the gate)' % GATE_GUARD)
    else:
        gp = gref[2]['p']
        s = UV._outside_spot(ctx, cl, gp[0], gp[1], (300, 450, 600, 800, 1000), people=True)
        (who_at.__setitem__('jiaqi', {'world': s, 'door_xy': [gp[0], gp[1]]}) if s else skipped.append('no room for Han Jiaqi at the gate'))
    S['who'] = who_at
    # the tackle locker on the shore below Kahala, the tablet's basket on the field road, the radio on a table
    if 'matsuda' in homes:
        dx, dy = homes['matsuda']['door_p'][:2]
        s = _shore(ctx, cl, dx, dy)
        (S.__setitem__('locker', {'world': s, 'near': cl.dist(s[0], s[1])}) if s else skipped.append('no shore for the tackle locker'))
    if 'gao' in homes:
        dx, dy = homes['gao']['door_p'][:2]
        s = UV._outside_spot(ctx, cl, dx, dy, (900, 1200, 1500, 1800, 2200))
        (S.__setitem__('basket', {'world': s, 'near': cl.dist(s[0], s[1])}) if s else skipped.append('no spot for the tablet on the field road'))
    if 'cabral' in homes:
        tabs = _shelf(gd, pr, homes['cabral']['cell'])
        if tabs:
            rk, r, z, e = tabs[0]
            S['radio'] = {'cell': homes['cabral']['cell'], 'p': (r['p'][0], r['p'][1], round(z, 1)), 'turn': r['p'][5] if len(r['p']) > 5 else 0.0,
                          'on': e}
        else:
            taken = [v['p'] for v in who_at.values() if v.get('cell') == homes['cabral']['cell']]
            s = _spot_in(gd, pr, homes['cabral']['cell'], homes['cabral']['beds'][0][1][:3], taken)
            (S.__setitem__('radio', {'cell': homes['cabral']['cell'], 'p': s, 'turn': 0.0, 'on': 'floor'}) if s else skipped.append('no spot for the radio'))
    import radio as RD
    st = sorted((s for s in RD.stations(gd, pr) if s.get('on_pipboy')), key=lambda s: s.get('name') != STATION)
    if not st:
        skipped.append('no island radio station in the mod')
    else:
        S['station'] = st[0]['key']
        S['station_name'] = st[0]['name']
        S['stations'] = [s['name'] for s in RD.stations(gd, pr)]
    if UV._game_key(gd, (RADIO_LIKE,), 'ACTI')[0] is None:
        skipped.append('no %s in the game' % RADIO_LIKE)
    for k, v in sorted(who_at.items()):
        rows.append({k: PEOPLE[k][1], 'in': HOMES.get(PEOPLE[k][4], 'outside'), 'at': [round(x) for x in (v.get('p') or v['world'])[:3]],
                     'work': [round(x) for x in v['work']['world'][:3]] if v.get('work') else None})
    for k in ('locker', 'basket', 'radio'):
        if k in S:
            rows.append({k: [round(x) for x in (S[k].get('world') or S[k]['p'])[:3]], 'near': S[k].get('near'), 'on': S[k].get('on')})
    rows.append({'station': S.get('station_name')})
    return {'rows': rows, 'skipped': skipped, 'spots': S}


# ---------- faces ----------

class Faces:
    """Free faces first; else one worn by the mod's people only FACE_APART or more away, of another surname."""

    def __init__(self, gd, pr):
        import activity
        import anquest
        self.gd, self.pr = gd, pr
        self.ctx = activity.Ctx(gd, pr)
        self.hctx = anquest._faces(gd, pr)
        self.used = set()
        self.taken = set()               # (faces this step gave: never one twice, near or far)
        self._wearers = None

    def digest(self, key, depth=0):
        """The FaceGen numbers a record's look comes from (its traits template followed to the end), as the faces gate reads them."""
        import hashlib
        gd, pr = self.gd, self.pr
        rec = pr.records.get(key) if key in pr.records else None
        if rec is None:
            try:
                rec = recordio.load(gd, gd.from_key(key))
            except Exception:           # noqa: BLE001
                return None
        if not rec or not rec.get('subs') or depth > 5:
            return None
        t = recordio.field(rec, 'TPLT')
        acbs = next((s for s in rec['subs'] if s['tag'] == 'ACBS'), None)
        tf = next((f['value'] for f in (acbs or {}).get('fields', ()) if f.get('name') == 'Template flags'), 0) if acbs else 0
        if t and tf & 0x01:
            return self.digest(t, depth + 1)
        parts = [json.dumps(s.get('value') if 'value' in s else s.get('fields'), sort_keys=True, default=str)
                 for s in rec['subs'] if s['tag'] in ('FGGS', 'FGGA', 'FGTS')]
        if not parts or not any(p.strip('"0') for p in parts):
            return None
        return hashlib.md5('|'.join(parts).encode()).hexdigest()[:16]

    def _index(self):
        gd, pr = self.gd, self.pr
        cellof = {}
        for ck, ent in pr.cells.items():
            for rk, r in (ent.get('refs') or {}).items():
                if isinstance(r, dict):
                    cellof[rk] = ck
        door_xy = {}
        for ck, ent in pr.cells.items():
            if ck.startswith('+'):
                continue
            for rk, r in (ent.get('refs') or {}).items():
                if isinstance(r, dict) and r.get('tel') and r.get('p'):
                    tc = cellof.get((r['tel'] or {}).get('door'))
                    if tc and tc.startswith('+'):
                        door_xy.setdefault(tc, r['p'][:2])
        where = {}
        for ck, ent in pr.cells.items():
            for rk, r in (ent.get('refs') or {}).items():
                if isinstance(r, dict) and not r.get('removed') and r.get('p') and str(r.get('base', '')).startswith('+'):
                    xy = r['p'][:2] if not ck.startswith('+') else door_xy.get(ck)
                    where.setdefault(r['base'], []).append(xy)
        w = {}
        for k, r in pr.records.items():
            if r.get('type') != 'NPC_' or not r.get('subs') or k not in where:
                continue
            d = self.digest(k)
            if not d:
                continue
            nm = recordio.field(r, 'FULL') or ''
            w.setdefault(d, []).append((nm.split()[-1].lower() if nm.split() else '', where.get(k, [])))
        self._wearers = w

    def far_ok(self, face_key, at, surname):
        """No one of the mod wears this face within FACE_APART (a place with no way out found counts as near), nor one of the
        same surname anywhere."""
        if self._wearers is None:
            self._index()
        d = self.digest(face_key)
        if not d or d in self.taken:
            return False
        for sn, spots in self._wearers.get(d, ()):
            if sn == surname:
                return False
            for xy in spots:
                if xy is None or math.hypot(xy[0] - at[0], xy[1] - at[1]) < FACE_APART:
                    return False
        return True

    def pick(self, races, sex, huang, at, surname):
        gd = self.gd
        tried = []
        try:
            f = self.hctx.free_face(races, sex) if huang else self.ctx.free_face(races, sex)
            if f is not None:
                tried.append(f)
        except Exception:               # noqa: BLE001
            pass
        tried += [x for x in UV._spare_faces(gd, self.pr, races, sex)][:400]
        f = next((x for x in tried if gd.key(x) not in self.used and self.far_ok(gd.key(x), at, surname)), None)
        if f is None:
            # (a face worn far off: every game person of the race and sex)
            import factionfolk as ff
            rid = {gd.key(x): gd.edid(x) for x, (_i, r) in gd.forms.items() if r.tag == 'RACE'}
            for x, (_i, r) in sorted(gd.forms.items()):
                if r.tag != 'NPC_' or gd.key(x) in self.used:
                    continue
                e = (gd.edid(x) or '').lower()
                if e.endswith(('dead', 'template')) or 'child' in e:
                    continue
                rec = recordio.load(gd, x)
                if recordio.field(rec, 'TPLT') or rid.get(recordio.field(rec, 'RNAM')) not in races:
                    continue
                if ('F' if ff._num(rec, 'ACBS', 'Flags') & 0x1 else 'M') != sex:
                    continue
                if self.far_ok(gd.key(x), at, surname):
                    f = x
                    break
        if f is None:
            raise ValueError('no face for a %s of %s, near or far' % (sex, races))
        self.used.add(gd.key(f))
        self.taken.add(self.digest(gd.key(f)))
        return f


# ---------- the step ----------

def apply(pr, gd, P=None):
    import api_quests as aq
    import api_scripts
    import factionfolk as ff
    import pearllife as PL
    import pinkpearl as PP
    import questrec as qr
    import struct
    import surffish
    import api_characters as ac
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
            x, y, z = spot['world'][:3]
            return gd.key(grid[(int(math.floor(x / 4096.0)), int(math.floor(y / 4096.0)))]), (x, y, z)
        return spot['cell'], spot['p'][:3]

    def place(base, spot, edid, props=None, turn=0.0, extra=None, persistent=True):
        k = _new_key(pr)
        cell, (x, y, z) = cell_of(spot)
        ref = {'base': base, 'p': [round(x, 1), round(y, 1), round(z, 1), 0.0, 0.0, turn], 's': 1.0, 'persistent': persistent}
        if edid:
            ref['edid'] = edid
        if props:
            ref['props'] = props
        if extra:
            ref.update(extra)
        out.append({'op': 'place', 'cell': cell, 'key': k, 'ref': ref})
        if edid:
            rep['made'].append(edid)
        return k

    def item_key(e):
        return UV._mod_key(pr, e) or UV._game_item(gd, e)
    # ----- items -----
    keys_of = {}
    for k, (e, n, like, value) in ITEMS.items():
        rec = surffish._copy(gd, 'MISC', UV._game_key(gd, (like, 'VRRCMisfitsDrugs'), 'MISC')[1], e, n)
        rec['subs'] = [s for s in rec['subs'] if s['tag'] != 'SCRI']
        for s in rec['subs']:
            if s['tag'] == 'DATA' and s.get('fields'):
                for f in s['fields']:
                    if f.get('name') == 'Value':
                        f['value'] = value
        keys_of[k] = record(rec)
    keys_of['key'] = record(PP._key(gd, 'FOLabHFShigsLockerKey', "Shig's Locker Key"))
    items = {k: ITEMS[k][0] for k in ITEMS}
    items['key'] = 'FOLabHFShigsLockerKey'

    def chest(edid, name, like, contents):
        base = UV._game_key(gd, like, 'CONT')[0]
        rec = recordio.load(gd, gd.from_key(base))
        rec['src'] = ''
        rec.pop('copied_from', None)
        recordio.set_field(rec, 'EDID', edid, label='Editor ID')
        if any(s['tag'] == 'FULL' for s in rec['subs']):
            recordio.set_field(rec, 'FULL', name)
        else:
            ac.insert(rec, {'tag': 'FULL', 'label': 'Name', 'kind': 'z', 'value': name})
        rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('CNTO', 'COED', 'SCRI')]
        for it, cnt in contents:
            s = ff._sub('CONT', 'CNTO', struct.pack('<Ii', 0, cnt))
            ff._set_link(s, keys_of[it])
            ac.insert(rec, s)
        return record(rec)
    # ----- packages: sleep in one's bed, work by the door, home otherwise -----
    packs = {}

    def pack(kind, target, hour, hours, radius, flags, tag):
        sig = (kind, target, hour, hours, radius, flags)
        if sig not in packs:
            src = 'DefaultSleepAlways256' if kind == 'sleep' else 'DefaultSandboxEditorLocation256'
            edid = 'FOLabHF%s%s%s' % (kind.capitalize(), tag, '' if hour < 0 else '%02dx%d' % (hour, hours))
            packs[sig] = record(PL._pack(gd, src, edid, hour, hours, target, radius, flags))
        return packs[sig]
    # markers to work round (XMarker, persistent)
    who = S['who']
    work_ref = {}
    for k, v in who.items():
        if v.get('work'):
            work_ref[k] = place('FalloutNV.esm:00003B', v['work'], 'FOLabHFWork%sREF' % PEOPLE[k][0][7:])
    # ----- people -----
    faces = Faces(gd, pr)
    fac_huang = UV._mod_key(pr, 'FOLabHuangFaction', 'FACT')
    wear = lambda names: [(it, 1) for it in (PP._item_key(gd, pr, n) for n in names.split('|')) if it]
    people, refs = {}, {}
    for k, (e, n, sex, races, home, kind, clothes) in PEOPLE.items():
        if k not in who:
            continue
        v = who[k]
        huang = kind in ('huang', 'shouwei')
        f = faces.pick(races, sex, huang, v['door_xy'], n.split()[-1].lower() if not huang else n.split()[0].lower())
        g = dict(ff.GROUPS['shouwei' if kind == 'shouwei' and 'shouwei' in ff.GROUPS else ('huang_folk' if huang else 'court_fighter')])
        g['package'] = 'DefaultSandboxEditorLocation256'
        rec = ff.person(gd, pr, f, e, n, g, wear(clothes), [], fac_huang if huang else '')
        if not huang:
            rec['subs'] = [x for x in rec['subs'] if not (x['tag'] == 'SNAM' and not next((y.get('value') for y in x.get('fields', ()) if y.get('name') == 'Faction'), None))]
        ff._set_num(rec, 'AIDT', 'Aggression', 0 if kind != 'shouwei' else 1)
        ff._set_num(rec, 'AIDT', 'Confidence', 1 if kind != 'shouwei' else 3)
        people[k] = rec
    # refs first (packages name them), then the days
    for k in people:
        v = who[k]
        spot = {'world': v['world']} if 'world' in v else {'cell': v['cell'], 'p': v['p']}
        pk = _new_key(pr)
        people[k] = record(people[k], pk)
        refs[k] = place(pk, spot, PEOPLE[k][0] + 'REF')
    for k, pk in people.items():
        rec = next(o['record'] for o in out if o['op'] == 'record' and o['key'] == pk)
        v = who[k]
        if PEOPLE[k][5] == 'shouwei':
            day = [pack('sandbox', refs[k], -1, 0, 200, NO_SLEEP, 'Watch%s' % PEOPLE[k][0][7:])]
        else:
            t = PEOPLE[k][0][7:]
            day = [pack('sleep', v['bed'], SLEEP[0], SLEEP[1], 96, 0, 'Bed' + t),
                   pack('sandbox', work_ref[k], WORK[0], WORK[1], 512, NO_SLEEP, 'Work' + t),
                   pack('sandbox', v['bed'], -1, 0, 640, NO_SLEEP, 'Home' + t)]
        PL._set_pkids(rec, day)
    # ----- things: the locker, the basket, the radio -----
    locker = chest('FOLabHFShigsLocker', "Shig's Locker", LOCKER_LIKE, [('box', 1)])
    refs['locker'] = place(locker, S['locker'], 'FOLabHFShigsLockerREF', {'lock': {'level': LOCKER_LOCK, 'key': keys_of['key'], 'leveled': False}})
    basket = chest('FOLabHFSpilledBasket', 'Spilled Basket', BASKET_LIKE, [('tablet', 1)])
    refs['basket'] = place(basket, S['basket'], 'FOLabHFSpilledBasketREF')
    rk, like = UV._game_key(gd, (RADIO_LIKE,), 'ACTI')
    live = recordio.load(gd, gd.from_key(rk))
    live['src'] = ''
    live.pop('copied_from', None)
    recordio.set_field(live, 'EDID', 'FOLabHFCabralRadio', label='Editor ID')
    for s in live['subs']:
        if s['tag'] == 'RNAM':
            s['value'] = S['station']
    dead = json.loads(json.dumps(live))
    recordio.set_field(dead, 'EDID', 'FOLabHFCabralRadioDead', label='Editor ID')
    dead['subs'] = [s for s in dead['subs'] if s['tag'] not in ('SCRI', 'RNAM', 'VNAM', 'INAM')]
    recordio.set_field(dead, 'FULL', 'Dead Radio')
    lk, dk = record(live), record(dead)
    rs = S['radio']
    refs['radio_dead'] = place(dk, {'cell': rs['cell'], 'p': rs['p']}, 'FOLabHFCabralRadioDeadREF', turn=rs['turn'])
    refs['radio'] = place(lk, {'cell': rs['cell'], 'p': rs['p']}, 'FOLabHFCabralRadioREF', {'enabled': False}, turn=rs['turn'])
    # ----- quests, scripts, topics -----
    sc = api_scripts.scripts()
    W2 = dict(QUESTS, life=LIFE)
    keys = {w: _new_key(pr) for w in W2}
    skeys = {w: _new_key(pr) for w in W2}
    targets = {k: refs[k] for k in refs}
    have = {'names': bool(UV._mod_key(pr, 'FOLabNameOnWater', 'QUST')), 'rep': bool(UV._mod_key(pr, 'FOLabRepHuang', 'REPU'))}
    plains = quests_plain({w: keys[w] for w in QUESTS}, {w: skeys[w] for w in QUESTS}, targets, have, items)
    plains['life'] = {'edid': LIFE, 'name': '', 'script': skeys['life'], 'flags': {'start_enabled': True}, 'priority': PRIORITY_LIFE,
                      'delay': 2.0, 'stages': [], 'objectives': [], 'conditions': []}
    stubs = {w: qr.quest_record(dict(plains[w], stages=[], objectives=[])) for w in W2}
    stub = lambda edid, typ='REFR': {'type': typ, 'flags': 0x400, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': edid}]}
    ext = {}
    for o in out:
        if o['op'] == 'place' and o['ref'].get('edid'):
            is_actor = o['ref']['base'] in people.values()
            ext[o['key']] = stub(o['ref']['edid'], 'ACHR' if is_actor else 'REFR')
    known = dict(ext)
    known.update({keys[w]: stubs[w] for w in W2})
    known.update({x['key']: x['record'] for x in out if x['op'] == 'record'})
    tkeys = {}
    for t, (w, top) in TOPICS.items():
        k = _new_key(pr)
        rec = qr.topic_record({'edid': topic_edid(t), 'name': topic_name(t), 'priority': 50.0, 'kind': 0,
                               'flags': {'top_level': top}, 'quests': [{'quest': keys[w], 'links': []}]})
        tkeys[t] = k
        known[k] = rec
        out.append({'op': 'record', 'key': k, 'record': rec})
    srcs = {w: quest_script(w, items) for w in QUESTS}
    srcs['life'] = life_script(('FOLabHFCabralRadioDeadREF', 'FOLabHFCabralRadioREF'))
    srecs = {}
    order = list(QUESTS) + ['life']
    for w in order:
        src = srcs[w]
        c = sc.compile(src, skeys[w], 'quest', known)
        if not hasattr(c, 'subrecords'):
            raise ValueError('%s: %s' % (src.split('\n')[0], c))
        srecs[w] = sc._record_of(c, src.split('\n')[0][4:])
        known[skeys[w]] = srecs[w]
    out += [{'op': 'record', 'key': skeys[w], 'record': srecs[w]} for w in order]
    out += [{'op': 'record', 'key': keys[w], 'record': stubs[w]} for w in order]
    rep['made'] += list(W2.values())
    V = {w: PP._vars(srecs[w]) for w in order}

    def conds(cs):
        o = []
        for c in cs:
            k = c[0]
            if k == 'q':
                o.append(UV._cond(79, c[3], c[4], keys[c[1]], V[c[1]][c[2]]))
            elif k == 'life':
                o.append(UV._cond(79, c[2], c[3], keys['life'], V['life'][c[1]]))
            elif k == 'glob':
                o.append(UV._cond(74, c[2], c[3], UV._mod_key(pr, c[1], 'GLOB')))
            elif k == 'skill':
                o.append(UV._cond(14, c[2], c[3], UV.AVI[c[1]], 0, 1))
            elif k == 'items':
                o.append(UV._cond(47, c[2], c[3], keys_of.get(c[1]) or item_key(c[1]), 0, 1))
        return o
    lines = []
    import skillcheck
    for whom, quest, topic, w, cs, end, skill, choices, bye in lines_spec():
        if whom not in people:
            continue
        tp = qr.GREETING if topic == 'G' else tkeys[topic]
        for nm, e in items.items():
            end = re.sub(r'(?<=AddItem )%s\b|(?<=RemoveItem )%s\b' % (nm, nm), e, end)
        l = aq.new_line_plain(gd, pr, tp, keys['life' if quest == 'life' else quest], people[whom], words(w), goodbye=bye, conditions=conds(cs))
        if w in M:
            l['responses'] = zh_responses(w)
        if skill:
            l['skill'] = skillcheck.skill_key(gd, skill)
        l['end'] = {'source': end, 'parts': None} if end else None
        l['choices'] = [tkeys[t] for t in choices]
        l.setdefault('begin', None)
        lines.append(l)
    # the elder's second way: a line of LIFE in huangstanding's "Show me what the ship carries"
    sq = UV._mod_key(pr, STANDING_Q, 'QUST')
    elder = UV._mod_key(pr, ELDER, 'NPC_')
    hold_topic = next((k for k, r in pr.records.items() if r.get('type') == 'DIAL' and recordio.field(r, 'EDID') == 'FOLabHuangStandingHold'), None)
    if sq and elder and hold_topic and UV._mod_key(pr, HOLD_KEY, 'KEYM'):
        sv = PP._vars(pr.records[recordio.field(pr.records[sq], 'SCRI')])
        tp = qr.topic_plain(json.loads(json.dumps(pr.records[hold_topic])))
        if not any(x.get('quest') == keys['life'] for x in tp['quests']):
            tp['quests'].append({'quest': keys['life'], 'links': []})
        out.append({'op': 'record', 'key': hold_topic, 'record': dict(pr.records[hold_topic], subs=qr.topic_record(tp)['subs'])})
        import repstanding
        l = aq.new_line_plain(gd, pr, hold_topic, keys['life'], elder, words('e_hold_yes'),
                              conditions=[UV._cond(79, '==', 0, sq, sv['askedhold']), UV._cond(79, '>=', 3, keys['life'], V['life']['trust']),
                                          UV._cond(14, '>=', HOLD_TRUSTED, UV.AVI['Speech'], 0, 1)])
        l['responses'] = zh_responses('e_hold_yes')
        l['skill'] = skillcheck.skill_key(gd, 'Speech')
        l['end'] = {'source': 'player.AddItem %s 1\nset %s.askedhold to 1\n%s' % (HOLD_KEY, STANDING_Q, repstanding.bump('huang', FACE)), 'parts': None}
        l['choices'] = []
        l.setdefault('begin', None)
        lines.append(l)
        rep['elder'] = 'second way at Speech %d with all three Huang favours' % HOLD_TRUSTED
    else:
        rep['elder'] = 'not added (huangstanding\'s hold line not in the mod)'
    forms = PP._forms(gd, pr, ext, {x['key']: x['record'] for x in out if x['op'] == 'record'})
    compiled_q = {}
    for w in W2:
        full = json.loads(json.dumps(plains[w]))
        errors = aq.compile_quest(full, forms)
        if errors:
            raise ValueError('%s: %s' % (W2[w], errors))
        compiled_q[w] = full
    compiled = []
    for l in lines:
        errors = aq.compile_line(l, forms)
        if errors:
            raise ValueError('%s: %s (%s)' % (errors[0]['where'], errors[0]['message'], l['responses'][0]['text'][:40]))
        compiled.append(qr.info_record(l))
    before_info = {k for k, r in pr.records.items() if r.get('type') == 'INFO'}
    pr.apply(LABEL, out)
    pr.apply(LABEL, [{'op': 'record', 'key': keys[w], 'record': qr.quest_record(compiled_q[w])} for w in W2] +
             [{'op': 'record_new', 'record': r} for r in compiled], merge=True)
    global VOICE_ONLY
    VOICE_ONLY = sorted(k for k, r in pr.records.items() if r.get('type') == 'INFO' and k not in before_info) or ['+NOTHING']
    rep.update({'lines': len(compiled), 'people': {k: PEOPLE[k][1] for k in people}, 'faces': sorted(faces.used),
                'homes': {h: v['edid'] for h, v in S['homes'].items()}})
    return rep
