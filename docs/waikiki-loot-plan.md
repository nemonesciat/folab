# Waikiki: more to loot and find (plan, 20 Nov 2026, not built yet)

The user's ask: more locked chests, rewards, explosives, guns, groceries and medicine, placed so they make sense and pay
for exploring and effort. Nothing goes into the mod until the user has seen this plan.

## What Waikiki has now (counted 20 Nov 2026)

- **Inside:** the 1,787 places behind doors are copies of the game's own rooms, so they already hold the game's
  containers: 10,746 of them (toolboxes, fridges, first aid kits, footlockers, safes). Only 47 are locked, about 700
  are the game's "empty" versions (empty footlockers, crates, duffel bags, suitcases, registers), and 198 places hold
  nothing at all.
- **Outside:** almost nothing to find. 1,152 broken mailboxes and 391 dumpsters; 9 real finds in the whole city.
  The 366 scene spots (105 camps, 66 refuges, 63 raider camps, 59 crashes, 57 roadblocks, 16 beach spots) have crates
  and barrels to look at but nothing to open.
- **Roofs:** nothing in Waikiki leads up onto a roof today (no ladders or stairs outside). Only these are high and
  reachable: the two posts on the ruined freeway (scaffold towers), the hotels' lookouts, the ridge places, the
  Missouri, the Flotilla, the Vault's ledge path.

So the work is mostly **outside**, plus **locks and fills inside** where the rooms are already furnished.

## What goes in the boxes

Only the game's own containers from FalloutNV.esm, whose contents are the game's levelled lists (what you find grows
with your level, as in the game). The game already sorts many of them into grades, which is how harder spots pay more:

| Kind | Easy | Middling | Hard |
|---|---|---|---|
| Medicine | first aid kit | locked first aid kit, hospital footlocker | drug footlocker, locked kit |
| Food | food sack, cooler | food crate | food crates, fridge |
| Guns and ammo | ammo box | locked ammo box, military footlocker | locked gun cabinet, big locked ammo box |
| Explosives | (none) | explosives crate grade 1-2, grenade box | explosives crate grade 3-4, mine box |
| Valuables | duffel bag, suitcase | floor safe | wall or floor safe on a key |

## How hard each spot is

Three bands, from the game-start at Hanauma Bay outward (the same bands `worldlife` uses for who you meet: under 7
cells easy, 7 to 13 middling, past 13 hard). A spot moves up one band if it is:
- held by someone (the Kahala Hotel and Koko Marina pirates, the Flotilla, the Kahuna's court, the Missouri, Alewa
  Fort, the Vault's waystation);
- high or hard to reach (the freeway decks, ridge tops, the ends of the Crest Trail's side paths);
- behind the wall or in the radiation to the north.

What a band changes: how many finds a spot gets, how good a grade, and the lock (easy: none or very easy; middling:
easy to average; hard: average to very hard). Nothing hostile and nothing locked near the start (`SAFE`).

**Keys.** About 20 of the hardest safes need a key. The key is somewhere that fits, close by: in the boss's desk drawer
or footlocker in the same place, on a skeleton at a raider camp, in a locker in another room of the Missouri. Never
inside the safe it opens, never far away.

## Where things go, and how much

| Spot | What | About how many |
|---|---|---|
| Raider camps (63) | ammo box, military footlocker; hard ones a locked gun cabinet or explosives crate | 100 |
| Roadblocks (57) | ammo box, sometimes a grenade box | 60 |
| Prospector camps (105) | duffel bag or household footlocker, food sack | 120 |
| Refuges (66) | food crate, first aid kit (people hid here) | 90 |
| Crashes (59) | suitcase or duffel bag beside the wreck | 60 |
| Beach spots (16) | cooler or duffel bag | 16 |
| Car and truck wrecks | 1 in 25 wrecks: a bag or suitcase against the side or in the back of a truck | 170 |
| Ruined freeway | the court's toll post: a locked cash box and the collectors' footlocker; the pirates' post: their lock-up, ammo and explosives; a stash at each broken end you can climb to | 10 |
| Kahala Hotel (pirates) | their armoury: locked gun cabinets, explosives crates, a safe on a key | 12 |
| Koko Marina, the Flotilla | boat lockers, ammo, the Flotilla captain's safe (key on another boat) | 15 |
| Royal Hawaiian court | the tribute yard: locked strongbox, food crates | 8 |
| USS Missouri (4 rooms) | Turret Two: ammo, explosives; Second Deck: medicine; Engine Room: tools; Pilot House: safe, key in the berthing lockers | 12 |
| Alewa Fort, ridge places (10), Vault waystation | military footlockers at the fort; 1-2 finds at each ridge place, a cache at its lookout | 30 |
| Crest Trail side paths | a small stash behind the rock stack at the end of each side path | 15 |
| Behind the wall, the north | richest: military footlockers, hard explosives crates, radiation medicine, a few keyed safes in ruins | 25 |
| **Outside total** | | **about 740** |
| Inside, empty ones filled | half the ~700 empty containers turned into the full version of the same model, by what the place is (household in houses, military in security places, register money in shops) | 350 |
| Inside, places with nothing | one find each, against a wall on the floor, by what the place is | 198 |
| Clinics (12 places) | an extra locked medicine cabinet or drug footlocker each | 12 |
| Food places (Costco, Safeway, Times, Foodland, Zippy's, 13 places) | food crates in the back | 26 |
| Security places (7) | locked gun cabinet and ammo | 14 |
| Locks inside | safes, gun cabinets and some kits locked by band, about 300 | (locks) |

Houses keep what they have (they're full already). 740 new things outside over about 4,000 cells is one in five
cells: little against the draw count (Waikiki is draw-bound; each find is one draw).

## Placed so it makes sense

- **Never on open ground at random.** Every find stands against something: a tent, a wreck's side, a wall, a rock, a
  table or crate at the camp, a building's back wall.
- **Seated:** set on the land under its own footprint (tilted to the slope, lowest corner on the ground, as FOLab seats
  rubble), or on the floor of the room, never hanging or sunk.
- **Out of the way:** not in a doorway, not on a road, not on a path or gangway, not in front of a door's swing.
- Inside, filling empty containers and adding locks changes nothing about where things stand; new ones go only beside
  furniture already on that floor.

## How it gets built

1. `app/lootplace.py` (with tests) works out every find as FOLab ops; nothing written yet. Code only: **the game stays
   free to test while this is built (about 2 to 3 hours).**
2. A rehearsal on a copy of the mod (a scratch FOLab that can't touch the game): count by band and kind, look at a
   sample of spots, health check on the built plugin.
3. Agree the order with the other sessions writing Waikiki, back up to `backups/`, then one save, one Undo
   ("Loot and finds"). **The game closed for about 10 minutes** for that, then the usual install into every nv-rs copy
   and MO2.

## Hawaiian clubs (added 20 Nov 2026, handed over from the own-models session)

FOLab's own models (no borrowed files), each on the game's own weapon animations and stats:
- **Leiomano** (picked): a paddle-shaped club edged with saw-blade or rebar teeth; swings and cuts like the machete.
- **Newa** (picked): a short, thick hardwood club; hits like the police baton or lead pipe.
- **All three two-handed clubs** (the user: "all of them"): the **lāʻau pālau** (long war club, like the sledgehammer
  or baseball bat), the **hoe** (a koa canoe paddle with a weighted, sharpened blade), and the **pōhaku maul** (a
  lava-rock head lashed to a koa haft, hits like the super sledge). Five weapons in all.

How they'd come into play is the user's call, not decided here: who carries them and any story to them. Loot-wise
the plain proposal is only where they'd be found: in some of the new finds (camps, the ridge places, the pirates'
armoury), more often and in better condition in harder spots. Built after the loot, as their own step: models,
weapon records, then added to finds.

## Questions for the user

1. **Roofs:** only the high places you can already reach (above), or also add about 10 ladders or scaffold stairs onto
   flat roofs, each with a stash on top? Ways up need a walk check and their cells' navmesh made again (a few minutes each).
2. **Extra pay at the hardest spots:** only the game's own levelled boxes, or also one hand-picked prize at each of the
   ~20 keyed safes (a good gun, a stack of stimpaks, explosives)?
3. **Owned things:** should the court's, the pirates' and the settlers' stores count as theirs (taking them is stealing,
   once their people are in), or free to take for now?
4. **Who carries the clubs:** only found in loot for now, or does any group carry them (yours to say: none is
   assumed)?

## Rehearsed (20 Nov 2026, dry run on the mod as it is; nothing saved yet)

`app/lootplace.py` (tests `tests/test_lootplace.py`, 32 of 32), run by a script that saves once as one Undo,
"More to find: loot, locks, keys, ways up". What the last dry run made:

- **1,110 finds** (the game's own containers), 615 of them locked, **14 keys** each on the lid of another find of its spot:
  the Royal Hawaiian's, Koko Marina's, the Waystation's, Alewa Fort's, the Tanks', the Holdouts', Loa Gate's safes, the
  Missouri's pilot house safe (key on a find on the second deck), raider stashes and old safes behind the wall.
  The Kahala Reef's safe and the Heights found no room beside what stands there and have none.
- Outside: camps 108, refuges 118, raider camps 113, roadblocks 72, crashes 56, wrecks 102, roof camps 170, ruins behind
  the wall 49, the held and high places 50. Inside: 274 finds (233 places that had nothing, or clinics, food places and
  security places' extras; the Missouri's four rooms 21), 266 empty containers made full ones of the same model,
  741 locks on what was already there (gun cabinets 276, safes 164, footlockers and ammo boxes 167, first aid kits 134). The
  places FOLab lent from the game had lost the game's locks; this puts locks back on safes and gun cabinets everywhere.
- **Bands changed from the first draft:** the encounter zones put every bit of Waikiki in "hard" (the start is at Hanauma
  Bay, far east), so the loot's bands are thirds of the way from the start to the farthest cell: the east (Hawai'i Kai,
  Waimanalo) easy, the middle (Kahala, Kaimuki, Diamond Head) middling, Waikiki, Manoa, downtown hard; held or high places,
  behind the wall and the north a band up.
- **Roofs:** Waikiki already had about 170 ramp towers onto flat roofs (an earlier build); the roof camps on them get the
  finds. **10 new ramp towers** go onto the highest flat roofs that had none (the user asked for them), each with a camp; the
  one new ramp model walked end to end; their 14 cells' navmeshes made again (73 s). Ramp models already in the mod are never
  written over.
- **Seated:** every find was checked corner by corner on the real collision under it after placing: none hangs or is sunk by
  more than 8 units. Each faces the way its model's front is (handles, latches, a dial), its back to what it stands against.
- **Health:** nothing new wrong; 410 more cells read "navmesh out of date" only because a box now stands there (2,252 did
  already): small boxes don't change where people walk.

## Saved (20 Nov 2026, 14:48)

Written into Waikiki.json as one Undo, "More to find: loot, locks, keys, ways up" (backup `backups/Waikiki before the loot
1120-1448`): 1,104 finds (607 locked), 13 keys, 270 empty containers filled, about 700 locks inside, 10 ramp towers with
camps (one new model, `ramp2t_1216_0.nif`), 14 cells' navmeshes made again; the audit after found none hanging or sunk
past 8 units. Install into the nv-rs copies by the story session. Not yet seen in the game.
