# The big ships: what is inside (the Flotilla's cargo ship, the settlers' freighter)

A plan (21 Nov 2026, from the user's "we also need to plan the vault, flotilla and barge interiors"; and, asked which
barge: "all big ships that can get an interior i mean. the flotilla container ship and the settler ship. arent they
big enough to go inside?"). The Vault's insides are planned elsewhere. Both ships are built on a copy on D: (last
sections); nothing here is in Waikiki until the step at the end is run.

What the story already says, and nothing more is assumed: the Flotilla is the pirates' boats lashed round a ship in
Maunalua Bay; the pirates carry people up to the Vault; their captains are the Vault's own and wear Pip-Boys.
Everything marked **[ask]** is a question for the user, not a decision.

## What stands there now

`flotilla.py`, in Waikiki at about 71680, -46208 (cell 17, -12), turned 0.6:

| Hull | What it is | Size (game units) | Now |
|---|---|---|---|
| Her heart: the cargo ship | FOLab's own (`settler_flotilla_ship`) | 7,700 long, 1,280 beam, deck 240 over the sea, a four-level house amidships | deck walked, containers, shacks, tents; the house and hull closed |
| Six hulks alongside | the game's `Boat01a`, `Boat01b`, `dlc04boatwrecked01` | 1,556 long, 668 beam, 930 keel to roof | floating outside the ring, not walked on |
| Two rafts of barges | the game's `Barge`, six to a raft | each 400 by 450, a flat pontoon 53 high | a shack on one, a guard tower on the other |
| Small boats | `Boat02*`, `Boat03*` | 612 and 250 long | moored round, scenery |

A ring of dock planking at the water joins everything; rope-bridge gangplanks climb from it to the ship's deck.

## Which hulls get insides

1. **The cargo ship: yes, all of her.** She is the only hull big enough to hold what the Flotilla is for. Four places
   (built, see below), a fifth later.
2. **Two of the six hulks: yes, one place each.** A `Boat01` is a river boat with a cabin deck: one small place each
   is believable (3 by 6 squares). Suggested: a crew boat (bunks, a stove, their own loot) and the old wreck
   `dlc04boatwrecked01` as a half-flooded hulk nobody lives in, with something worth going in for. The other four stay
   closed (boarded doors): six near-identical insides would be the "same room behind nine doors" problem again.
   *As built (22 Nov): the two intact boats to starboard got the cabins; the old wreck stays closed.*
3. **The barge rafts: no insides of their own.** The game's `Barge` is a solid pontoon 53 units high: there is nothing
   to be inside. What stands *on* a raft can have an inside: the shack on the bow raft is the game's `WoodShack02`,
   and gets one of the game's shack rooms through `townbuild` as any building does.
4. **Small boats: no.**

**"The barges" [answered]:** the user meant the big ships, not the game's pontoons: the Flotilla's container ship and
the settlers' freighter. Both are done below. The hulks stay as item 2: big enough for one small place each, not
built yet. The Missouri has her insides already.

## The cargo ship

Bow is -y in her frame; her house stands amidships with a block of containers before and abaft it.

| Place | Where in her | What is in it | In and out |
|---|---|---|---|
| **The House** | the deckhouse | one passage; off it the crew's mess (navy tables, lockers), the galley (stoves, water), the card room, the captain's cabin (the one real bed aboard, a desk, a safe, a gun cabinet) | a bulkhead door in the house's forward face, on deck; a door down at the passage's after end |
| **Below Decks** | under the house | one passage; forward berthing, the quartermaster's store, the brig (three cages), the still, after berthing | up through the store to the House; forward to the Hold; aft to the Pens |
| **The Hold** | forward, under the containers | what was taken: crates stacked down both sides with a lane between, a trunk and the pick of it at the forward end | a hatch in her deck in the lane before the house; a door aft to Below Decks |
| **The Pens** | aft | where people are kept until a boat takes them on: cages down both sides and across the after bulkhead, mattresses on the plates, a guard's table by the door | a hatch in her deck abaft the house; a door forward to Below Decks |
| *The Bridge* (later) | top of the house | the wheel and ports (the Missouri's helm and painted ports fit as they are), the radio, the lookout's view | an outside ladder from the deck, or a door from the House |

Not planned: an engine room. She is aground on the shelf and doesn't sail; a dead engine room is a fifth big room with
nothing to do in it. If the Flotilla's power matters (the story: "Vault cells first, wind and solar on the boats"), a
charging bench in the quartermaster's store says it in one corner.

**How the places join.** Below decks you walk the length of her without coming up: Hold, Below Decks, Pens, with the
House above the middle. Each door is a load door (four small places, not one big one: each place stays under the draw
budget and navmeshes in seconds). On deck there are three ways down, so there is always a second way out of a fight.

**Hull to hull:** over the top only, by the planking ring and gangplanks that are there now. No way below decks from
one hull to another: the hulks float a thousand units from her side with open water between, and an interior door can't
show that. One thing that would read well and costs little: a **cargo port** in her side at the waterline, a door from
the Hold straight out onto the ring's planking (a short plank across). **[ask]**

**Ladders.** The game's ladders are doors (`MetLadderLoad01`, `VHDExteriorLadder`): they move you, nobody climbs. The
hatches here are the game's flat `HatchDoor` set in the deck; inside, you arrive at a door in a bulkhead. A ladder
drawn under each hatch inside is dressing only.

## Who and what goes in them [ask before building]

Nobody lives in the four places yet. Before they are peopled:

- **Captives in the Pens:** people in the cages (the game can keep an NPC in a cage with a wander package), or empty
  cages and what they left? Can the player open them, and does anything follow if they do?
- **The captain:** one of the three Pirate Captains already placed (`factionfolk.py`) moves into the cabin, or a
  captain of the Flotilla's own?
- **Is the Flotilla hostile ground?** If pirates there shoot on sight, the insides are a dungeon (locked store, the
  key on the quartermaster, loot by depth as `lootplace` does). If you can walk aboard to trade, the mess and card
  room are where that happens and the Pens and store are what's locked.
- **The Castaway's own boat** sank on its way in to the Flotilla. Does anything aboard remember it (a manifest in the
  captain's safe is the obvious place)? Not written.

## How it is built

- **The kit:** New Vegas's Utility kit (grey steel rooms and passages on 256-unit squares), the same the Missouri's
  insides use. New Vegas has Rivet City's doors and a few of its corridor pieces, but no Rivet City room or floor
  piece, so a hall can't be made of that kit; the game has no boat interior of its own to borrow (its one "boat" place
  is a rental office on land).
- **The method:** `flotillainside.py` describes each place as rooms and a passage on the kit's squares with its doors
  and things (`shipinside.Layout`); `shipinside.build` picks the kit's pieces, hangs the game's doors where the game
  hangs them, lights it with the kit's own fittings, and walks the real collision to every square, with the
  furniture in, before anything is placed. A place that doesn't walk is refused.
- **What the kit asks:** rooms at least three squares each way (two-square rooms found no pieces), so rooms sit on one
  side of a passage: four squares across, 1,024 units, inside her 1,280 beam.
- **Dressing so far** is the game's own things by name: navy tables and bunks, lockers, stoves, crates, barrels,
  Gomorrah's dancer cages and Big MT's kennel cages for the pens, the Divide's still. FOLab's own pieces to make
  later, if wanted: hammocks, cargo netting over the stacks, a ladder under each hatch, portholes with painted sea (the
  Missouri's `ports` shows how).
- **Same rooms twice:** these four share a kit with the Missouri. They read differently by what is in them and by
  light (the Missouri is lit cool and even; these can go dim and warm with `roomvary`'s moods). Worth a look in game
  before more are made.

## Built on a copy, to prove it

The cargo ship's four places, on a copy of Waikiki in `D:\FOLab-flotilla\home` (21 Nov 2026; `app/flotillainside.py`,
`tests/test_flotillainside.py`). Not in Waikiki, not seen in any game.

| Place | Kit pieces | Things | Lights | Navmesh |
|---|---|---|---|---|
| The House | 60 | 25 | 20 | 194 triangles, 2 doors |
| Below Decks | 68 | 24 | 24 | 174 triangles, 3 doors |
| The Hold | 40 | 23 | 9 | 88 triangles, 2 doors |
| The Pens | 30 | 17 | 6 | 87 triangles, 2 doors |

- **Walked before placing:** each place's real collision, with its furniture in, from its first room to every square
  (`kitplan.walk_check`): all reached, first try, nothing blocking a doorway.
- **Her deck walked** (`walkcheck`, from the planking ring up the gangplanks): the house door and both hatches are
  reached, at 16-unit and at 32-unit columns. At 32 the walk lists three narrow areas elsewhere on her deck that were
  there before this (between containers); none is a way in.
- **Doors:** 12, every one leads to a door that leads back (`D:\FOLab-flotilla\check_doors.py`). On deck: the game's
  bulkhead door on the house's forward face, to starboard; the game's flat hatch in the lane before the house and
  another abaft it. You arrive a step clear of each.
- **Pictures** (FOLab's 3D view): `waikiki-flotilla-inside-1-mess.jpg`, `-2-brig.jpg`, `-3-berthing.jpg`,
  `-4-hold.jpg`, `-5-pens.jpg`, `-6-house-door.jpg`, `-7-deck-hatch.jpg`, beside this file.

What the pictures show and the game hasn't: the rooms are dim and read as "utility tunnel with furniture"; the cabin
most needs dressing of its own. What nobody has checked: the hatches as load doors in the game (the game uses this
hatch that way at Hoover Dam), the deck's own navmesh round the new door and hatches (companions may not follow down
until the deck's cell is navmeshed again: one cell), and how the four read after the Missouri's rooms.

The step for Waikiki, both ships together, is `D:\FOLab-flotilla\flotilla_into_waikiki.py real`: the game, FOLab and
MO2 closed; a backup first; eight places, 22 doors, two gangplanks and the places' navmeshes as one Undo ("Inside the
ships"); no install.

## Two of the hulks

The two `Boat01` hulks lashed to starboard outside the ring, fore and aft (`flotillainside.BOATS`), each with one
cabin of 3 by 4 squares. The other four hulks, the old wreck among them, stay closed.

| Place | What is in it | In and out | Built |
|---|---|---|---|
| **A Crew's Boat** (forward) | three bunks, a stove, water, a locker and footlocker, a table and chair | the game's flat hatch in the boat's after deck | 12 pieces, 9 things, 4 lights |
| **The Work Boat** (aft) | a workbench, toolbox, crates, barrels, a mattress on the deck | the same | 12 pieces, 8 things, 4 lights |

- **Getting aboard:** each boat's deck is 55 units over the planking, too high to step up, with 27 of open water
  between. A steel gangplank of FOLab's own (`flotilla_plank`, one small model) runs from the planking up to the
  after deck. Walked from the planking to the hatch at 16-unit and 32-unit columns (`walkcheck`): reached, no
  narrow place, nothing walked on that isn't drawn. Tilted the other way it isn't reached, so the test would catch it.
- The names ("A Crew's Boat", "The Work Boat") are placeholders, not lore.
- The way in is a hatch, not a door: the boat's cabin is a small wheelhouse, open behind, and a bulkhead door stood on
  it looked stuck on (seen in the 3D view, 22 Nov). A hatch in the after deck reads as going below.
- Pictures: `waikiki-flotilla-boat-1-gangplank.jpg`, `-2-cabin.jpg`.

## The settlers' freighter at Waimānalo

The same hull as the Flotilla's ship (`settlerset.freighter`), run bow-first up the beach: her house aft, five cargo
hatches forward, a ramp from her bow to the sand. Two places, with nothing said of the Huáng that the story hasn't
(the story gives her one thing: "a generator on their ship, run on alcohol from their sugar cane").

| Place | What is in it | In and out | Built |
|---|---|---|---|
| **The House** | one passage; a mess with its stoves, two berthings, the master's cabin (a bed, a desk, a bookcase) | the game's bulkhead door in the house's forward face, on deck; a door down to the Hold | 52 pieces, 18 things, 15 lights; navmesh 151 triangles |
| **The Hold** | the generator and its fuel tank at the after end, a control panel, barrels, crates of stores | the game's flat hatch in her deck between the third and fourth cargo hatches; a door up to the House | 40 pieces, 18 things, 9 lights; navmesh 85 triangles |

- Six doors, every one leading to one that leads back. Both places walked with their furniture in before placing.
- **Her deck:** walked from the head of her bow ramp to both ways in at 16-unit columns (a player). At 32 (what an
  outdoor navmesh sees) neither is reached: the side decks beside her cargo hatches are 230 wide, too narrow. That was
  so before this (her deck has no navmesh and the elders stand, they don't walk), and it means nobody but the player
  goes from her deck into her until her hatches are narrowed or her deck given a hand-made navmesh.
- Pictures: `waikiki-freighter-inside-1-mess.jpg`, `-2-hold.jpg`, `-3-house-door.jpg`.

**[ask] The Huáng's ship.** Left out, to be answered before anyone or anything of theirs goes in:
- Do the elders live in her house (they stand on her deck now), or is she kept as she was and nobody sleeps aboard?
- Is the generator still run, and is the hold where their radio is?
- Is she open to a stranger, or is the door locked and the hold more so?
- Should her rooms look like the courtyards (red posts, plaster: FOLab's own pieces) rather than grey steel? As built
  they are a plain ship's rooms and say nothing of two hundred years of the Huáng.

## Order, if this goes ahead

1. The user's answers to the questions above.
2. The eight places into Waikiki (one Undo, about nine minutes, most of it loading the mod; no outdoor navmesh is
   touched, so no long remake).
3. Their people and loot.
4. The Bridge; the shack on the raft; the deck cells' navmesh round the new doors and gangplanks.

## In Waikiki

In Waikiki since 22 Nov 2026 05:25 (the story session ran `D:/FOLab-flotilla/flotilla_into_waikiki.py real`; one Undo, "Inside the ships"; installed to nv-rs-pad). `check_doors.py` on the real mod: 22 doors, 0 not linked both ways, navmeshes on 8 of 8 places. Not yet seen in game.

## Aboard (the user's answers, 22 Nov 2026 ~09:00; `app/shipcrew.py`, `tests/test_shipcrew.py`)

Rehearsed on a copy (`D:/FOLab-flotilla/crew_into_waikiki.py rehearse`); not in Waikiki, not seen in game. One Undo,
"Aboard the ships". Pictures: `waikiki-flotilla-crew-1-pens.png`, `-2-store.png`, `-3-captain.png`,
`waikiki-freighter-crew-1-elders.png`.

The Flotilla, hostile ground:
- 17 of the mod's pirates by room (house 4, below decks 6, hold 3, pens 1, boats 2 and 1), stood on the navmeshes.
- The quartermaster's store is locked (needs its key): its door off the passage and the ladderway between it and the
  house, both ends. The key is on the Quartermaster, in the house's card room. So the house no longer leads below
  without the key: below decks is reached through the hold's or the pens' hatch.
- The pens' after end is three cells of the game's jail bars, a barred door each (lock 50), their key on the pens'
  guard. Five captives inside, dressed as the island's people, in the game's FiendFriendFaction so the pirates leave
  them be. Eight of the old show cages and kennels came out to make room.
- Captain Iolana "Io" Kanahele (the user's name) in the captain's cabin: the mod's woman pirate in the Officer's Coat
  with a Pip-Boy, level 16 at least.
- Loot by depth as lootplace does it: house and boats easy, below decks middling, hold, pens and store hard. Two empty
  containers filled, the captain's safe locked, 11 finds (five in the store: guns, ammunition, medicine; four in the
  hold with a safe).

The Huang's freighter, open to a stranger:
- The three Zhanglao are off her deck and in her house (two in the mess, one in the master's cabin).
- Her hold needs its key (Freighter Hold Key): the house's ladderway and the deck hatch, both sides. The key is on the
  elder in the master's cabin, to be taken from the body or picked from the pocket (the user, 22 Nov).
- Both her places are owned by the Huang, so taking things is stealing. (Mine to make "touch nothing" mean something;
  say if it should go.)

The user's answers since (22 Nov): captives stay wandering for now (they may end up in Waikiki later); the
Quartermaster and the pens' guard stay unnamed; the freighter stays the Huang's.
