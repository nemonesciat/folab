# Tonight: the battleship and the Natatorium

A brief for a Claude Code session, from a lore session with Nemo. Read `docs/waikiki-lore.md`, then
`docs/waikiki-lore-additions.md` (the sections "The battleship and the Natatorium" and "Waikiki" above all), then
this. `CLAUDE.md` still governs how the work is done; nothing here overrides it.

Marks used in the additions: **[decided]** Nemo settled it; **[agreed]** his working version; **[proposed]** suggested,
not confirmed. Build what is decided and agreed. Where a step rests on something proposed, say so when you start it,
so Nemo can stop you.

## Ask Nemo first

**Which of the steps below tonight, and in what order?** The order here is a suggestion.

## The ship stays the Missouri [decided]

No rename: she is still the USS Missouri (BB-63), "63" on her bows, the surrender plaque where it is. In the lore she was
brought back into service by a Navy stretched thin, and was coming home to Pearl Harbor from the east for resupply and
crew rotation when the bombs fell.

## The work, in suggested order

### 1. Stand her aground, upright, off the Natatorium (`shipplace.py`)
- **Where:** on the reef line off the War Memorial Natatorium, between Waikiki and Diamond Head (the Natatorium is in
  `historicset.py`). **Bow west**, toward Pearl Harbor. **Port side to the shore** (the pier and stair tower go there).
- **Grounded, not floating:** she sits on the reef, not at the sea's level as `stand` does now. She can ride a little
  low at the bow (flooded forward), but **her decks must stay level enough to walk and navmesh**: that was the reason
  for beaching her upright.
- Shallow reef water round her, with the sea floor brought up to meet her hull, so she reads as resting on it and not
  hovering. Check from shore and from the water.

### 2. Damage pass (model and textures)
The blast came from **ahead and to starboard** (downtown Honolulu lies west-northwest of her), so damage is heaviest
forward and on the starboard side. Topside is wrecked; the armoured hull and the three main turrets are whole.
- Foremast bent or toppled aft, radars gone.
- Bridge windows blown in, pilot house gutted (the armoured conning tower below it intact).
- Forward funnel caved in on its starboard side; after funnel standing.
- Mainmast down, lying across the deck.
- Starboard 5-inch mounts knocked askew; Phalanx domes gone; missile launchers crushed and burned out.
- Fantail crane toppled.
- Main turrets intact: one barrel drooping; Turret Two trained hard to starboard.
- Starboard scorch: paint blistered, teak burned, soot up the superstructure. **Flash shadows**: pale silhouettes on the
  scorched paint where railings and barrels blocked the flash. One in the shape of a person, at most.
- Bow holed below the waterline (seen from the water at low angle); the lower forward compartments flooded or sealed.
- Two hundred years: the rust and chalky paint already there, plus bird droppings, plants in soil pockets in the
  superstructure, barnacles and coral on the lower hull.
- The kālaimoku's people (can wait for a later pass): tin and tarp shacks on deck, a rebuilt signal mast with flags, a
  searchlight, a lookout nest on the foremast's stump.
Do what the model and texture tools can do well; list what needs a new mesh rather than faking it.

### 3. The way aboard, through the Natatorium (`aboard.py`, `historicset.py`)
Replace the straight shore-to-hull pier with this route. Every part is level walking; the only climb is the tower.
1. **The arch** on the street: the gate and checkpoint. The map marker goes here.
2. **The bathhouse** behind it: guardroom, armoury, cells (interiors can be placeholders tonight).
3. **The pool and its bleachers:** left open for now (later: the court of judgment).
4. **Along the top of the pool's side wall** to the seaward wall (the pool later becomes a boat basin).
5. **A timber pier on pilings** from the seaward wall across the reef shallows to her port side.
6. **A scaffold stair tower lashed to the hull**, landings and switchbacks, up to the main deck. Later: a hand-cranked
   cargo hoist beside it, counterweighted with anchor chain; cargo nets down the hull.
Then the navmesh for everything walked on, by the rules in `CLAUDE.md`.

### 4. If there's time: the compound
- A wall of rubble, sandbags and sheet metal round the Natatorium and its grounds.
- Kapiʻolani Park mostly cleared in front of it, a few great banyans kept as lookouts; ironwoods and banyans screening the
  compound from the city.

## Not tonight
The Flotilla and its cruise liner, the Huáng and their freighter, the vassal enclaves, weather, the radio stations, the
Vault. All are in the additions for later; don't start them unless Nemo asks.

## Before finishing
Show Nemo pictures from shore, from the pier, from the stair tower and from the deck, and list what is done, what is
placeholder, and what needs a new mesh.
