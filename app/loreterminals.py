"""Terminals with the island's history in them (docs/waikiki-weak-spots-1126.md, weak spots 1-6; the user, 26 Nov 2026:
"Tidbits of history and lore in the terminals").

Three or four terminals an area where the player walks first, each in a place that would have had one: offices, a ranger
post, a library, a clinic, checkpoints, a lighthouse, ruined homes. They hold only what is decided: the wall's land and
Ground Zero beyond it, the court and the Kahuna, the Missouri beached on the reef, Vault 50 sold to the rich, the Huang's
ship, catchers and tribute day, the storms, pre-war Honolulu. Personal logs make them human; some are funny. Pre-war
entries are dated 2077; entries typed long after say so. Names and small histories are this step's own, written into
docs/waikiki-decisions.md as "built 26 Nov, user may change" (`INVENTED`).

- **Where** (`SITES`): a place by its name (`place`: the FULL as a pattern, the nearest whose outside door is closest to a
  point), or a map marker's ground (`outside`: open navmesh round it, factionfolk's search, as secretcaches stands its
  terminals). Inside: on the place's own navmesh, by a desk or table if one stands there, clear of doors and arrivals,
  anyone standing and seats (robots' rules). Each place takes one terminal; a place with a terminal already is passed by.
- **Payoffs** (`cache`): six terminals open a locked container of their own beside them (lock "needs a key", no key: only
  the terminal's item opens it, `<ref>.Unlock` as terminals.py does, proven in nv-rs). Others point at what is already out
  there (the Heights' estate terminal, wrecks off the lighthouse, the radar dome).
- **Locks** by how far from the start and how much a place holds: open near the start, Science 25-75 further in.
- One Undo, by result scripts only. Nothing voiced (terminals have no voices).

    plan(gd, pr)       {'rows', 'skipped'}
    ops(gd, pr, P)     (ops, report)
"""
import math
import re

import recordio

LABEL = 'Terminals with the island\'s history'
NEAR_DESK = (80.0, 600.0)
CACHE_NEAR = (180.0, 700.0)
OUT_RADII = (300, 450, 600, 800, 1000, 1200)
CACHE_OUT = (250, 350, 450, 600, 800)
ROADS = re.compile(r'Road|Highway|Freeway|Overpass|Bridge|Sidewalk', re.I)   # (never on a road piece: kept 200 from their middles)
FOOT = 'FOLabFootlocker01MilitaryNVIsland|Footlocker01Military'
BOX = 'FOLabAmmoBox01NVIsland|AmmoBox01|' + FOOT
SAFE = 'SafeWall01|Safe01|' + FOOT
HEAD = 'ROBCO INDUSTRIES UNIFIED OPERATING SYSTEM\n  COPYRIGHT 2075-2077 ROBCO INDUSTRIES'

# key: {area, where, text, cache}
#   where ('place', FULL pattern, (x, y) the door nearest it)  or  ('outside', map marker name)
#   cache (editor ID, name, container to copy, [(item, n)])
SITES = {}


def _site(key, area, where, text, cache=None):
    SITES[key] = {'area': area, 'where': where, 'text': text.strip('\n') + '\n', 'cache': cache}


# ---------- 1. the coast road, Koko Marina west to the Kahala ----------
_site('niu_ranger', 1, ('place', r'^Ranger Post$', (34327, -11739)), """
Terminal: FOLabLoreNiuRanger
Name: Ranger Post Terminal
Model: desk
Lock: none
Welcome:
  DEPARTMENT OF LAND AND NATURAL RESOURCES
  NIU VALLEY RANGER POST
== Duty log, 10-21-2077
Says:
  Hikers on the ridge trail again without water. Third time this week.
  Signs say the ridge is closed. Signs have said that since 2071.
  Wild pig damage on the Niu side. Requested traps. Requested again.
== Duty log, 10-23-2077
Says:
  0350. Light over town. Sirens on the radio, then nothing on the radio.
  Wind is from the northeast. Whatever is coming off town is going out to sea.
  Opened the post to anyone from the valley. Fourteen so far.
  Keeping the rifle locker shut until I know who's who.
== (an entry typed long after; the date reads 00-00-0000)
Says:
  Found this box still running on a cell. Somebody has kept it dry for a long time.
  Whoever you were, ranger: the locker's still shut. We never got the code out of it.
  The court's men came through for the tally Tuesday. The boat men came Friday.
  Niu pays both. Niu always pays both.
== Open the rifle locker
Unlocks: {cache}
Says: Rifle locker released.
""", ('FOLabLoreNiuLocker', 'Ranger Rifle Locker', FOOT, [('Ammo308', 24), ('Stimpak', 2), ('SpareParts', 3)]))

_site('ainahaina_home', 1, ('outside_place', r'^House$', "Aina Haina Refugee Camp"), """
Terminal: FOLabLoreAinaHainaHome
Name: Family Terminal
Model: desk
Lock: none
Welcome:
  THE KEALOHA HOUSEHOLD
  PLEASE WIPE YOUR FEET (THIS MEANS YOU, KIMO)
== Shopping list, 10-22-2077
Says:
  Rice (if any). Spam (if any). Batteries, D.
  Water: store says the truck comes Tuesday.
  Kimo's school shoes. No. Next month.
== Message from Dad, 10-23-2077, 4:05 AM
Says:
  Sirens at quarter to four. The sky over town went white, then orange.
  Don't go to the windows.
  We've taken the car up the valley to Auntie Lei's.
  If you read this, follow the stream up. Don't wait for us here.
== (typed long after)
Says:
  Nobody named Kealoha lives here now. We just kept the screen.
  The catchers came through before tribute day, two of them, asking who had no family.
  We said everybody here has family. They counted us anyway.
""")

_site('kahala_vaulttec', 1, ('place', r'^Kahala Business Plaza', (-34197, -27676)), """
Terminal: FOLabLoreVaultTecKahala
Name: Vault-Tec Sales Office
Model: desk
Lock: easy
Welcome:
  VAULT-TEC CORPORATION
  PREMIER RESIDENCES DIVISION - KAHALA OFFICE
  "A Better Tomorrow, Underground, In Paradise"
== Sales memo: the Ka'au site
Says:
  Vault 50 is not a public shelter and is never to be called one.
  Clients are buying a residence in a sealed community in Ka'au Crater,
  above Palolo Valley, with household staff and security included.
  Do not discuss the reactor. Do not discuss the "behavioural programme".
  If asked, say: "Every residence comes with peace of mind."
== Client file: Platinum residences, closing list
Says:
  ASHFORD .......... PAID IN FULL. Party of 6, staff of 4.
  VANDERMEER ....... PAID IN FULL. Party of 5, staff of 3.
  WHITCOMBE ........ PAID IN FULL. Party of 4, staff of 5.
  (11 further clients PAID, residence assignment PENDING)
  Note: pending clients are to be told the site is "nearly ready".
== Note from the branch manager
Says:
  Gary. The Heights people keep calling. The residences are SOLD.
  We are not "adding a floor". Stop saying we'll look into it.
  Also the office safe is for contracts, not your lunch.
== Release the office safe
Unlocks: {cache}
Says: Office safe released.
""", ('FOLabLoreVaultTecSafe', 'Vault-Tec Office Safe', SAFE, [('Caps001', 80), ('Stimpak', 2), ('RadAway', 1), ('Mentats', 1)]))

_site('makai_lifeguard', 1, ('outside', 'Makai Tower'), """
Terminal: FOLabLoreLifeguard
Name: Lifeguard Station Terminal
Model: desk
Lock: none
Welcome:
  CITY AND COUNTY OF HONOLULU
  OCEAN SAFETY - KAHALA STATION
== Incident log, 10-19-2077
Says:
  Visitor stung, Portuguese man o' war. Vinegar. Visitor fine.
  Visitor asked if the sharks are "the friendly kind". Advised there is no such kind.
  Surf 3-5 ft. Trades 15-20.
== Incident log, 10-23-2077
Says:
  No swimmers today.
  0430: a warship coming along the coast from the east, low in the water at the bow.
  Big. Battleship big. She went past toward Diamond Head, slow, listing.
  Radio says she's making for the reef. Nobody's telling us anything else.
== Hurricane season reminder
Says:
  When the flags go up, everyone off the beach. Everyone. Including you, Duke.
  Close the shutters. Bring the boards in. The sea comes up further than you think.
""")

# ---------- 2. Manoa, Palolo, Kaimuki ----------
_site('hamilton', 2, ('place', r'^Hamilton Library$', (-76714, 13544)), """
Terminal: FOLabLoreHamilton
Name: Library Catalogue
Model: desk
Lock: none
Welcome:
  UNIVERSITY OF HAWAII AT MANOA
  HAMILTON LIBRARY - PUBLIC CATALOGUE
== Search: "sugar"
Says:
  14 results. Top result:
  "Chinese laborers came to Hawaii from the 1850s to work the sugar
  plantations. Many stayed, and their families became part of the islands."
  Status: ON SHELF. Third floor.
== Search: "Kalakaua"
Says:
  9 results. Top result:
  "King Kalakaua, the Merrie Monarch, revived the hula and the old chants
  and built Iolani Palace. Waikiki's avenue bears his name."
  Status: ON SHELF.
== Overdue notices
Says:
  Patron 0041177: "Fallout Shelters for the Home Handyman", 212 days overdue.
  Patron 0041177: "So You've Been Drafted", 198 days overdue.
  Patron 0041177 has been referred to collections.
== Reading room notice, 10-20-2077
Says:
  The basement is a designated shelter for staff and students only.
  Faculty with Vault-Tec "residences" are reminded they may not reserve study carrels.
""")

_site('manoa_ranger', 2, ('place', r'^Ranger Post$', (-63179, 31700)), """
Terminal: FOLabLoreManoaRanger
Name: Ranger Post Terminal
Model: desk
Lock: easy
Welcome:
  DEPARTMENT OF LAND AND NATURAL RESOURCES
  UPPER MANOA RANGER POST
== Stream report
Says:
  Manoa Stream: running high. Wettest valley on the island again.
  Reminder: do not drink from the stream. Leptospirosis. Boil it or don't.
  The city pumps the water up from underground. If the pumps stop, the valleys have the water.
== (typed long after)
Says:
  We farm the floor now: taro, sweet potato, bananas. Good years.
  The court calls Manoa its breadbasket. It says it like a compliment.
  Collectors count the baskets and then they count the people.
  This year the quota went up again. Nobody says why. Everyone knows it's the mountain.
== (typed long after)
Says:
  Saw a line of them go up past the head of the valley last night, roped,
  toward Palolo and the crater road. Guards with lights. Didn't look long.
""")

_site('palolo_home', 2, ('outside_place', r'^House$', "Palolo Refugee Camp"), """
Terminal: FOLabLorePaloloHome
Name: Home Terminal
Model: desk
Lock: average
Welcome:
  WELCOME HOME
  (A NOTE TAPED ON THE SCREEN: "DON'T")
== (typed long after) The road
Says:
  The road up the valley goes to the crater. Everyone in Palolo knows it.
  They bring them past at night, from the coast. The waystation feeds the guards.
  We sell the guards fish. That's all. We sell them fish.
== (typed long after) What we keep
Says:
  Mother says if the boat men ever come for us we'll need something to pay with.
  It's under the floor by the stove. Medicine mostly. The good kind, the kind from up there.
  Don't ask where it came from. I didn't.
== Unlatch the floor box
Unlocks: {cache}
Says: You hear a latch go under the floor by the stove.
""", ('FOLabLorePaloloStash', 'Floor Box', FOOT, [('Stimpak', 3), ('RadAway', 2), ('Caps001', 40), ('AmmoSmallEnergyCell', 20)]))

_site('kaimuki_collector', 2, ('outside_place', r'^Works$', "Kaimuki Squatters' Camp"), """
Terminal: FOLabLoreKaimukiCollector
Name: Collector's Ledger
Model: desk
Lock: average
Welcome:
  BY THE KAHUNA'S LEAVE
  TRIBUTE ROLL - KAIMUKI AND THE VALLEY MOUTHS
== This season's roll
Says:
  Kaimuki ....... food: paid. hands: 2 owed, 2 given.
  Manoa ......... food: paid. hands: 3 owed, 3 given.
  Palolo ........ food: short. hands: 2 owed, 1 given, 1 "ran".
  The Tanks ..... food: paid late. hands: 1 owed. Arguing.
  The Holdouts .. nothing. As ever. Noted for the Captain.
== Note to the next collector
Says:
  Count the people BEFORE they know it's tribute day.
  Afterwards there are always fewer of them and a lot more cousins "visiting from Kalihi".
  Catchers are paid on delivery, not on promises. Don't advance them a thing.
== Complaint, filed and ignored
Says:
  To the court: a farmer in Manoa says the Kahuna's peace is "bought with his nephew".
  Recommend: no action. He paid his basket.
""")

# ---------- 3. Diamond Head, Kapiolani Park, the Aquarium, Coral Crescent ----------
_site('building303', 3, ('place', r'^Building 303$', (-60009, -45090)), """
Terminal: FOLabLoreCivilDefense
Name: Civil Defense Duty Terminal
Model: desk
Lock: average
Welcome:
  STATE OF HAWAII - CIVIL DEFENSE
  DIAMOND HEAD - DUTY OFFICER
== Duty log, 10-23-2077
Says:
  0322. Flash traffic relayed from CINCPACFLT, Pearl Harbor. Attack warning.
  0347. Detonations, downtown and Pearl. Lost Pearl on every circuit.
  0410. Wind northeast at 15. Plume bearing out to sea, southwest.
  0455. USS Missouri, inbound from the east, reports holed at the bow and flooding.
        Intends to put her on the flat reef off the Natatorium so she can't sink.
  0530. Missouri aground, upright. Crew aboard. Guns intact, she says.
== Shelter roster
Says:
  Capacity: staff and their families only. Do not open the outer door to the public.
  (Underneath, typed later:) We opened it anyway. Of course we did.
== Release the supply locker
Unlocks: {cache}
Says: Civil defense supply locker released.
""", ('FOLabLoreCivilLocker', 'Civil Defense Supply Locker', FOOT, [('RadAway', 3), ('RadX', 3), ('Stimpak', 2), ('WaterPurified', 3)]))

_site('waikiki_shell', 3, ('place', r'^Waikiki Shell$', (-78306, -38847)), """
Terminal: FOLabLoreWaikikiShell
Name: Box Office Terminal
Model: desk
Lock: none
Welcome:
  THE WAIKIKI SHELL
  KAPIOLANI PARK - BOX OFFICE
== October bookings, 2077
Says:
  10-24: Royal Hawaiian luau revue, "The Big Kahuna Live". SOLD OUT.
  10-25: Navy Band, Pacific Fleet. Free to servicemen.
  10-26: Civil defense drill (shelter is the bathhouse at the Natatorium, NOT the stage).
== Ticket queries
Says:
  Q: Is the Big Kahuna a real king?
  A: No, ma'am. He's a performer. He's very good.
  Q: Will the show go ahead if there's a war?
  A: The show goes ahead in all weather.
== (typed long after)
Says:
  The show went ahead. Two hundred years and it never stopped.
  The court holds its feasts where the stage was. Same torches. Same conch.
""")

_site('coral_home', 3, ('outside_place', r'^House$', "Coral Crescent"), """
Terminal: FOLabLoreCoralHome
Name: Home Terminal
Model: desk
Lock: easy
Welcome:
  PERSONAL TERMINAL
  (PASSWORD HINT: "WHAT WE CALL THE SHIP")
== (typed long after) The ship
Says:
  You can see the Missouri from the roof. Everyone in Waikiki can. That's the point of her.
  The court says her big guns keep the pirates honest.
  My grandfather served aboard as a boy. He never once said he heard them fire.
== (typed long after) Tribute day
Says:
  They walk them out along the pier to the ship in the morning.
  The boats come in the afternoon. By night the ship's quiet again.
  The Kahuna feasts on tribute day. I used to think that was a coincidence.
== (typed long after) Note to my daughter
Says:
  Don't get into debt with anyone in the court. Debtors go first.
  And if you ever go up the hill past the Holdouts, don't come back with a story.
""")

_site('lighthouse', 3, ('outside', 'Lighthouse'), """
Terminal: FOLabLoreLighthouse
Name: Light Station Terminal
Model: desk
Lock: none
Welcome:
  U.S. COAST GUARD
  DIAMOND HEAD LIGHT
== Light log
Says:
  Light: automatic. Keeper: none since 1924. Visitors: please stop leaving leis on the door.
== Storm log
Says:
  Hurricane season, June to November. The swell comes round Diamond Head first.
  Wind takes the rain sideways here. You will not stay dry. Do not try.
  Small craft run for Hawaii Kai and the old fishpond harbour. Big ships ride it out.
== Wrecks charted off the head
Says:
  Hulls on the bottom between here and Koko Head, more every storm season.
  Koko Head's reef takes a boat a year. Divers: the water round them isn't empty either.
""")

# ---------- 4. the eastern ridges ----------
_site('crows_nest', 4, ('place', r'^Shack$', (90540, 16929)), """
Terminal: FOLabLoreCrowsNest
Name: Lookout Tally
Model: desk
Lock: average
Welcome:
  PROPERTY OF THE CROW'S NEST
  TOUCH IT AND SWIM HOME
== Boats in the bay
Says:
  Day: 3 at the marina, 1 out past the reef, the big ones lashed off Maunalua as ever.
  Night: lanterns on the Flotilla. A light on the Missouri. Nothing from the court's beach.
== Cells
Says:
  Cells in: 40, came down from the mountain with the last run. Two a head.
  Cells out: 12 to the marina, 8 for the light, 6 owed to Pua for the cards. Pua cheats.
  Rest in the box. The box is locked. The code is not "1234" any more, Pua.
== Release the cell box
Unlocks: {cache}
Says: Cell box released.
""", ('FOLabLoreCellBox', 'Cell Box', BOX, [('AmmoSmallEnergyCell', 30), ('AmmoMicroFusionCell', 10), ('Caps001', 20)]))

_site('hahaione_home', 4, ('outside_place', r'^House$', "Hahaione Refugee Camp"), """
Terminal: FOLabLoreHahaioneHome
Name: Family Terminal
Model: desk
Lock: none
Welcome:
  THE NAKAMURA FAMILY
  "HOME SWEET HAWAII KAI"
== Message from Ken, 10-22-2077
Says:
  Ship's in Pearl Thursday, then two days' leave. Tell the kids.
  The Fleet's jumpy. Everybody's jumpy. Don't watch the news, it just makes you jumpy.
  Love you. Save me some of your mother's mochi.
== Message to Ken, 10-23-2077, unsent
Says:
  Ken the radio says Pearl. The radio says Pearl and then it stopped.
  We're going up the ridge with the Okadas. I'll leave this on.
  If you get this come up the ridge. Come up the ridge, Ken.
""")

_site('kamiloiki_home', 4, ('outside_place', r'^House$', "Kamiloiki Valley Refugee Camp"), """
Terminal: FOLabLoreKamiloikiHome
Name: Old Terminal
Model: desk
Lock: easy
Welcome:
  (THE SCREEN FLICKERS. SOMEONE HAS BEEN USING THIS AS A DIARY.)
== (typed long after) Running
Says:
  Our valley owed two at tribute and they picked me. So I ran.
  Up the ridge and along the top. The crest trail is a knife and the cloud never lifts.
  Catchers behind me two days, then not.
== (typed long after) The other side
Says:
  Don't go down to the windward side. The Huang catch runaways and hand them to the pirates
  at Makapuu, every one. Everybody says they're cruel. They're not cruel. They're careful.
  I came back down here instead. Nobody's counted this valley in years.
""")

# ---------- 5. the north-west: the checkpoints, the Heights, upper Kalihi ----------
_site('h3_checkpoint', 5, ('outside', 'H-3 Checkpoint'), """
Terminal: FOLabLoreH3
Name: Checkpoint Terminal
Model: desk
Lock: average
Welcome:
  U.S. ARMY - HAWAII MARTIAL LAW COMMAND
  CHECKPOINT H-3 (TETSUO HARANO TUNNELS)
== Standing orders
Says:
  No civilian traffic toward Marine Corps Base Hawaii, Kaneohe Bay. None.
  Curfew 2000 to 0600. Ration cards to be shown on request.
  Persons of Chinese descent: refer to the duty officer. Do not detain on sight.
  (We were told to write that last part down after the thing with the Lees.)
== Traffic log, 10-23-2077
Says:
  0350. Flash. Tunnel lights out, generators up.
  0412. Kaneohe asks if we can see town. We can see where town was.
  0600. Cars from the city at the barrier. Orders: hold. Nobody through.
== Release the ammunition crate
Unlocks: {cache}
Says: Ammunition crate released.
""", ('FOLabLoreH3Crate', 'Checkpoint Ammunition Crate', BOX, [('Ammo556mm', 40), ('Ammo10mm', 30), ('WeapGrenadeFrag', 2)]))

_site('likelike_checkpoint', 5, ('outside', 'Likelike Checkpoint'), """
Terminal: FOLabLoreLikelike
Name: Checkpoint Terminal
Model: desk
Lock: easy
Welcome:
  U.S. ARMY - HAWAII MARTIAL LAW COMMAND
  CHECKPOINT LIKELIKE
== Morale notice
Says:
  It is pronounced "lee-keh-lee-keh". Not "like-like".
  The next man who says "like-like" on the radio pulls the tunnel shift alone.
== Incident report, 10-14-2077
Says:
  Civilian attempted to pass with 40 lbs of rice "for his mother".
  Mother confirmed by radio. Mother also wanted rice. Rice confiscated.
  Recommend: someone looks into the rice situation.
""")

_site('pali_checkpoint', 5, ('outside', 'Pali Checkpoint'), """
Terminal: FOLabLorePali
Name: Checkpoint Terminal
Model: desk
Lock: average
Welcome:
  U.S. ARMY - HAWAII MARTIAL LAW COMMAND
  CHECKPOINT PALI
== Post history (for new arrivals)
Says:
  Nuuanu Pali. In 1795 Kamehameha's army drove the defenders of Oahu up this valley
  and over these cliffs. Show some respect.
  It is also the windiest post on the island. Secure your cover. Secure your paperwork.
  Secure yourself.
== Lost property
Says:
  Hats: 61. Clipboards: 14. One (1) sergeant, recovered.
== (typed long after)
Says:
  Up past the Heights the old rich still talk about the crater as if it owes them.
  One of their estates has a terminal with the service road on it. They guard it like a will.
""")

_site('hsuyun', 5, ('place', r'^Hsu Yun Temple', (-121722, 51972)), """
Terminal: FOLabLoreHsuYun
Name: Temple Office Terminal
Model: desk
Lock: none
Welcome:
  HSU YUN TEMPLE
  CHINESE BUDDHIST ASSOCIATION OF HAWAII - OFFICE
== Notice to members, 06-12-2077
Says:
  Our families came to these islands in 1852 to work the sugar. We are Americans.
  If you are questioned by federal agents, be polite, give your name, and call the office.
  Do not argue with them on the temple steps. Mrs. Wong, this means you.
== Lunar New Year, parking
Says:
  Members park on the street. The lot is for the lion dance.
  The lion dance is not to be held in the lot if it is raining. It is always raining.
== Notice, 10-22-2077
Says:
  The evening service will be held as usual.
  Bring water and a blanket. Leave the car facing up the hill.
""")
# ---------- 6. Kailua and Kaneohe ----------
_site('kailua_post', 6, ('place', r'^Kailua Post Office$', (34287, 153485)), """
Terminal: FOLabLoreKailuaPost
Name: Post Office Terminal
Model: desk
Lock: none
Welcome:
  UNITED STATES POSTAL SERVICE
  KAILUA - UNDELIVERED MAIL QUEUE
== Undelivered: to Mrs. L. Kahananui
Says:
  "Dear Mom. San Diego's fine. Food's rationed here too. They say it'll be over by
  Christmas. Don't send any more cookies, they took the last box at customs for 'inspection'."
== Undelivered: to Occupant
Says:
  "CONGRATULATIONS! You may already have been selected for a VAULT-TEC PREMIER RESIDENCE.
  Call our Kahala office today." (Return to sender: occupant was not selected.)
== Undelivered: to Kailua Beach Park, Lost and Found
Says:
  "One (1) surfboard, yellow, found on the sand, 10-22. Owner please collect."
""")

_site('kaneohe_pharmacy', 6, ('place', r'^Windward Mall$', (-52823, 196536)), """
Terminal: FOLabLoreKaneohePharmacy
Name: Pharmacy Terminal
Model: desk
Lock: average
Welcome:
  WINDWARD MALL PHARMACY
  KANEOHE - DISPENSING SYSTEM
== Advisory: stream water
Says:
  Cases of leptospirosis up again after the rains. It comes from rat-fouled water.
  Fever, headache, aching calves. Boil all stream water. Antibiotics work if given early.
== Advisory, 10-23-2077
Says:
  Mass casualty plan in effect. Burns to the front, radiation to the back.
  Supplies will not be resupplied. Use them accordingly.
== Release the drug cabinet
Unlocks: {cache}
Says: Drug cabinet released.
""", ('FOLabLoreClinicCabinet', 'Drug Cabinet', FOOT, [('Stimpak', 3), ('Morphine', 1), ('NVAntivenom', 1), ('RadAway', 1)]))

_site('waimanalo_offices', 6, ('outside_place', r'^Offices$', "Waimanalo Beach Squatters' Camp"), """
Terminal: FOLabLoreWaimanaloOffice
Name: Office Terminal
Model: desk
Lock: easy
Welcome:
  WAIMANALO - DISTRICT OFFICE
== Report, 10-24-2077
Says:
  A freighter has run herself up the sand in Waimanalo Bay. No lights, foreign flag.
  Three hundred aboard, maybe more, Chinese. Families. Nobody speaks English but the captain,
  and not much of it.
  Police chief says they're the enemy who just burned Honolulu. Pastor says they're hungry.
== Report, 11-02-2077
Says:
  The ship people have dug in round the hull and they're armed better than we are.
  They've taken the farms nearest the beach. They've stopped coming to talk.
  This is the last report this office will send. There's nobody left to send it to.
""")


# ---------- planning ----------
def _ed(gd, pr, b):
    from secretcaches import _ed as e
    return e(gd, pr, b)


def _places_with_doors(gd, pr):
    from officeterminals import _ways_in
    ways = _ways_in(pr)
    out = []
    for ck, rec in pr.records.items():
        if rec.get('type') != 'CELL' or not ck.startswith('+') or ck not in ways:
            continue
        out.append((ck, recordio.field(rec, 'FULL') or '', ways[ck]))
    return out


def _has_terminal(gd, pr, ck):
    import robots
    return any(not r.get('removed') and robots._tag(gd, pr, r.get('base', '')) == 'TERM'
               for r in (pr.cells.get(ck) or {}).get('refs', {}).values())


def _inside(gd, pr, ck):
    """(terminal spot, cache spot or None, near) inside a place, or (None, None, why)."""
    import robots
    tris = robots._tris(gd, pr, ck)
    if not tris:
        return None, None, 'no navmesh'
    doors, actors, seats = robots._things(gd, pr, ck)
    d = robots._d

    def clear(p):
        return (min((d(p, x) for x in doors), default=1e9) >= robots.DOOR_CLEAR and
                min((d(p, a) for a in actors), default=1e9) >= robots.APART and
                min((d(p, s) for s in seats), default=1e9) >= robots.SEAT_CLEAR)
    free = [p for p in tris if clear(p)]
    if not free:
        return None, None, 'no clear navmesh'
    desks = [r['p'] for r in pr.cells[ck]['refs'].values() if not r.get('removed') and r.get('p')
             and re.search(r'desk|table|counter', _ed(gd, pr, r.get('base', '')), re.I)]
    best, face = None, None
    if desks:
        near = [(min(math.dist(p[:2], k[:2]) for k in desks), p) for p in free]
        near = [t for t in near if NEAR_DESK[0] <= t[0] <= NEAR_DESK[1]]
        if near:
            best = min(near)[1]
            face = min(desks, key=lambda k: math.dist(best[:2], k[:2]))
    if best is None:
        door = lambda p: min((d(p, x) for x in doors), default=1e9)
        best = max(free, key=lambda p: (round(door(p) / 300), -p[0], -p[1]))     # (in from the way in, not the furthest corner)
        face = min(doors, key=lambda x: d(best, x)) if doors else None
    rz = math.atan2(face[0] - best[0], face[1] - best[1]) if face else 0.0
    t = (round(best[0], 1), round(best[1], 1), round(best[2] + 4, 1), round(rz, 4))
    near = {'door': round(min((d(best, x) for x in doors), default=1e9)), 'by a desk': face is not None and bool(desks)}
    cands = [p for p in free if CACHE_NEAR[0] <= math.dist(p[:2], best[:2]) <= CACHE_NEAR[1] and abs(p[2] - best[2]) < 120]
    c = None
    if cands:
        cb = min(cands, key=lambda p: (abs(math.dist(p[:2], best[:2]) - 260), p))
        c = (round(cb[0], 1), round(cb[1], 1), round(cb[2], 1), round(math.atan2(best[0] - cb[0], best[1] - cb[1]), 4))
    return t, c, near


ROAD_CLEAR = 450.0      # (from a road piece's middle: off the slab, a game road piece being 512 to 1,024 long)


def _out(gd, pr, sp, x0, y0, radii, doors, posts, roads, avoid):
    import factionfolk as ff
    from secretcaches import _clear
    for s in ff._near(sp, x0, y0, 12, radii=radii, turns=16):
        if (_clear(gd, pr, sp, s[0], s[1], doors, posts) and all(math.hypot(s[0] - a[0], s[1] - a[1]) >= 200 for a in avoid)
                and all(math.hypot(s[0] - q[0], s[1] - q[1]) >= ROAD_CLEAR for q in roads)):
            return (round(s[0], 1), round(s[1], 1), round(s[2], 1), round(s[3] + math.pi, 4)), {
                'door': round(min((math.hypot(s[0] - d[0], s[1] - d[1]) for d in doors), default=1e9))}
    return None, None


def plan(gd, pr):
    import factionfolk as ff
    import robots
    from secretcaches import _spots_for, _outside, _outside_refs, TRAIL_POST
    mk = ff._markers(pr)
    places = _places_with_doors(gd, pr)
    posts = None
    used = set()
    rows, skipped = [], []
    for key, S in SITES.items():
        kind = S['where'][0]
        if kind in ('place', 'outside_place'):
            pat = re.compile(S['where'][1])
            if kind == 'place':
                at = S['where'][2]
            else:
                if S['where'][2] not in mk:
                    skipped.append((key, 'no map marker ' + S['where'][2]))
                    continue
                at = mk[S['where'][2]][1][:2]
            cands = sorted((math.dist(w, at), ck, full, tuple(w)) for ck, full, w in places if pat.search(full) and ck not in used)
            got = None
            for dist, ck, full, w in cands[:8]:
                if dist > 7000:
                    break
                if _has_terminal(gd, pr, ck):
                    continue
                t, c, near = _inside(gd, pr, ck)
                if t and (c or not S['cache']):
                    got = (ck, full, dist, t, c, near, w)
                    break
            if not got:
                skipped.append((key, 'no place fits (%d named so near)' % len([c for c in cands if c[0] <= 7000])))
                continue
            ck, full, dist, t, c, near, w = got
            used.add(ck)
            near['marker'] = round(dist)
            rows.append({'key': key, 'area': S['area'], 'cell': ck, 'full': full, 'p': t, 'cache_p': c, 'near': near, 'at': w})
        else:
            name = S['where'][1]
            if name not in mk:
                skipped.append((key, 'no map marker ' + name))
                continue
            ack, ap = mk[name]
            if posts is None:
                posts = [r['p'] for _c, _k, r in _outside_refs(gd, pr, lambda r: _ed(gd, pr, r.get('base', '')) == TRAIL_POST)]
            world = gd.key(gd.ext_cells[gd.from_key(ack)])
            sp = _spots_for(gd, pr, world)
            doors = robots._outside_doors(gd, pr, sp.grid, {'a': (ap[0], ap[1])})
            roads = [r['p'] for _c, _k, r in _outside_refs(gd, pr, lambda r: math.hypot(r['p'][0] - ap[0], r['p'][1] - ap[1]) < 3000
                                                           and ROADS.search(_ed(gd, pr, r.get('base', ''))))]
            tp, tn = _out(gd, pr, sp, ap[0], ap[1], OUT_RADII, doors, posts, roads, ())
            if not tp:
                skipped.append((key, 'no clear ground by ' + name))
                continue
            cp = None
            if S['cache']:
                cp, _cn = _out(gd, pr, sp, tp[0], tp[1], CACHE_OUT, doors, posts, roads, [tp])
                if not cp:
                    skipped.append((key, 'no ground for the cache by ' + name))
                    continue
            tn['marker'] = round(math.hypot(tp[0] - ap[0], tp[1] - ap[1]))
            tn['road piece'] = round(min((math.hypot(tp[0] - q[0], tp[1] - q[1]) for q in roads), default=1e9))
            rows.append({'key': key, 'area': S['area'], 'world': world, 'full': name, 'p': tp, 'cache_p': cp, 'near': tn, 'at': tp[:2]})
    return {'rows': rows, 'skipped': skipped}


def lock_of(text):
    m = re.search(r'^Lock:\s*(.+)$', text, re.M)
    return (m.group(1).strip().lower() if m else 'none')


# ---------- ops ----------
def ops(gd, pr, P=None):
    import terminals
    from activity import _new_key
    from secretcaches import _cache_record, SAFE_LOCK
    P = P or plan(gd, pr)
    have = {recordio.field(r, 'EDID') for r in pr.records.values()}
    if any(SITES[k]['text'].split('\n')[0].split(': ')[1] in have for k in SITES):
        raise ValueError('the mod has lore terminals already (Undo first)')
    grid = lambda w: gd.grid(gd.from_key(w))

    def cell_of(row, p):
        return row.get('cell') or gd.key(grid(row['world'])[(int(p[0] // 4096), int(p[1] // 4096))])
    out, rep = [], {'terminals': [], 'skipped': list(P['skipped'])}
    forms = terminals.mod_forms(gd, pr)
    places = []
    for row in P['rows']:
        S = SITES[row['key']]
        cache_ref = ''
        cache_rep = None
        if S['cache']:
            edid, name, src, items = S['cache']
            rec, got = _cache_record(gd, pr, edid, name, src, items)
            k = _new_key(pr)
            out.append({'op': 'record', 'key': k, 'record': rec})
            forms.own[edid.lower()] = (k, rec)
            cache_ref = edid + 'REF'
            rk = _new_key(pr)
            x, y, z, rz = row['cache_p']
            out.append({'op': 'place', 'cell': cell_of(row, row['cache_p']), 'key': rk,
                        'ref': {'base': k, 'p': [x, y, z, 0.0, 0.0, rz], 's': 1.0, 'persistent': True, 'edid': cache_ref,
                                'props': {'lock': dict(SAFE_LOCK)}}})
            forms.own[cache_ref.lower()] = (rk, {'type': 'REFR', 'flags': 0x400, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': cache_ref}]})
            cache_rep = {'name': name, 'items': got, 'from terminal': round(math.dist(row['cache_p'][:2], row['p'][:2]))}
        spec = terminals.plan(S['text'].replace('{cache}', cache_ref).replace('{HEAD}', HEAD))
        t_ops, t_keys = terminals.ops(gd, pr, spec, forms)
        for o in t_ops:
            k = _new_key(pr)
            assert k == t_keys[recordio.field(o['record'], 'EDID')], (k, o['record'])
            out.append({'op': 'record', 'key': k, 'record': o['record']})
        for e, k in t_keys.items():
            forms.own[e.lower()] = (k, {'type': 'TERM', 'flags': 0, 'subs': [{'tag': 'EDID', 'label': 'Editor ID', 'kind': 'z', 'value': e}]})
        x, y, z, rz = row['p']
        places.append({'op': 'place', 'cell': cell_of(row, row['p']), 'key': None,
                       'ref': {'base': t_keys[spec['edid']], 'p': [x, y, z - 4, 0.0, 0.0, rz], 's': 1.0}})
        rep['terminals'].append({'key': row['key'], 'area': row['area'], 'edid': spec['edid'], 'name': spec['name'], 'where': row['full'],
                                 'science': terminals.science_needed(spec), 'entries': len(spec['items']), 'p': row['p'], 'at': row.get('at'),
                                 'near': row['near'], 'cache': cache_rep})
    for pl in places:
        pl['key'] = _new_key(pr)
    return out + places, rep


INVENTED = [
    "Vault 50 was sold from a Vault-Tec sales office in the Kahala Business Plaza as 'premier residences'; the Ashford, "
    "Vandermeer and Whitcombe families bought among the first, eleven more paid and were told the site was 'nearly ready' "
    "(the Heights' people) (loreterminals, kahala_vaulttec)",
    "On 23 Oct 2077 the Diamond Head civil defense log records the attack warning relayed from CINCPACFLT at 0322, the "
    "detonations at 0347, the plume blowing out to sea, and the Missouri, inbound from the east and holed at the bow, put on "
    "the reef off the Natatorium at 0530, upright (building303)",
    "The Kealoha family of Aina Haina (a ruined home), the Nakamura family of Hahaione (Ken, a sailor bound for Pearl), a "
    "Niu Valley ranger, a Kamiloiki runaway who came back down: personal logs, no one alive to meet",
    "The court's collectors keep a tribute roll for Kaimuki and the valley mouths (food and 'hands' owed and given, the "
    "Holdouts paying nothing, noted for the Captain); catchers are paid on delivery (kaimuki_collector)",
    "Crow's Nest pirates are paid in cells from the mountain, 'two a head'; Pua cheats at cards (crows_nest)",
    "Waimanalo's district office saw the freighter run up the sand the day after the bombs, about 300 Chinese families "
    "aboard, the captain the only one with any English; within ten days they had dug in round the hull and taken the "
    "nearest farms (waimanalo_offices)",
    "The Waikiki Shell had 'The Big Kahuna Live', the Royal Hawaiian's luau revue, booked for 24 Oct 2077; the court "
    "feasts where its stage was (waikiki_shell)",
    "Pre-war martial-law checkpoints at the H-3, Likelike and Pali tunnels held the roads from the city on the morning of "
    "the bombs (h3_checkpoint, likelike_checkpoint, pali_checkpoint)",
]
