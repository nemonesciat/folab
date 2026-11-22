# The Vault in Kaʻau Crater: the inside

A plan for the Vault's interior, and a first generated layout. Made 21 Nov 2026 on copies only: nothing is in
Waikiki.json or any game folder. The outside (the crater, the ledge path, the door landing) is built already
(`app/vaultgate.py`, `waikiki-vault-built.png`); its gear door stays locked until an inside is linked to it.

## What's decided (the user's words, docs/waikiki-story-plan.md and waikiki-lore.md)

- The island's one vault, high in Kaʻau Crater, sealed and still running.
- **Its own reactor:** full power, comfort and security, the one place on the island that has them. The reactor is the
  deepest room (asked for 21 Nov 2026).
- **Its workshops keep the Pip-Boys working:** made for its people, kept going 200 years; nowhere below can make or mend one.
- **It recharges power cells** and pays the pirates in them, and in **medicine and guns**.
- **The founding families are an aristocracy;** the pirate captains are its own, sent out or let go.
- **Its young grow up in comfort** and are told what their people eat only when they come of age.
- **Its people eat the people it buys.** The least useful go up the mountain and disappear, and so do the ones it wants
  most for itself. Some of them are going mad (kuru or something like it).
- The door is high in the crater's north wall, reached by the ledge path in full view.

**The user's answers, 22 Nov 2026 (~09:00, docs/waikiki-decisions.md):**
- **Ruled by a council of the founding families.** The council chamber (the game's overseer's office, set whole), locked on
  the Council Key, which lies on something to search in another room.
- **The eating shown plainly:** the kitchens (range, butchery, scullery) and the cold store (fridges, a freezer, chains) are
  built; meat on the cutting boards and the feast hall's plates.
- **Lit and clean:** nothing wrecked, no rubble, nothing whose name says it's dirty, broken or bloody from the game's rooms
  (kitdress `DIRTY_WORDS`), no failing or red lights, and lit as the best lit of the game's rooms. The blood is only in what
  the kitchens and cold store are for.
- **The way in is the gear door and a back door off the settlers' cliff trail.** A back door room of its own inside; outside,
  a mine door in the windward face under the crest (rockdoor.py), north of where Ka'au's climb meets the Crest Trail, a path
  down to it. The cliff trail itself (down to Waimānalo) isn't built yet: the door is where it would come up. Unlocked.
- **Servants remain:** servants' quarters (bunks, footlockers), one, and one more for every four of the size.

## What's only proposed (waikiki-lore-additions.md, not decided)

- Internal name "A Modest Proposal".
- Servants and staff who outnumbered the rich and were eaten first (that servants remain is decided); ration "lotteries".
- Food systems built to fail; a "protein reclamation" plant; cold storage far too large (the cold store is decided); a
  medical wing built like a butcher's.

## The layout

`app/kaauvault.py` lays it with the vault kit through kitplan (rooms, corridors, stairs, every square walked over the
pieces' real collision) and dresses it through kitdress and kitlife (furnishing taken from the game's own vault rooms,
then this place's own scenes and things to search). Each room keeps its own name.

| Room | Furnished as | Why it's there | Decided? |
|---|---|---|---|
| The door landing | entrance | the gear door from the ledge comes in here | yes (the door) |
| The atrium | two storeys, balconies | the vault's heart | the kit's, not the story's |
| Founders' suites (3 + 1 for every 2 of the size) | quarters | the families' comfort: queen beds, paintings, candlesticks, rugs | yes (comfort, the families) |
| The schoolroom | classroom | the young, raised in comfort and kept from the truth | yes |
| The feast hall | mess | a banquet table, wine, candles, meat on the plates: where they eat | yes |
| The kitchens | mess | a clean range and pot, a butchery table with meat on the board, a hanging chain, a scullery | yes (22 Nov) |
| The cold store (1, and 1 more for every 5 of the size) | store | fridges, a freezer with meat, chains | yes (22 Nov) |
| Servants' quarters (1, and 1 more for every 4) | quarters | bunks, footlockers | yes (22 Nov) |
| The back door | entrance | a second way out: the back door off the cliff trail | yes (22 Nov) |
| The Pip-Boy workshop | workroom | a workbench, spare parts, electronics | yes |
| The cell charging room | workroom | computer racks, drained cells, a locked box of micro fusion cells | yes |
| The armoury | store | gun cabinet, reloading bench, locked ammo | yes (they pay in guns) |
| The clinic | clinic | operating table, surgical carts, a locked first aid kit, medical cabinet | yes (they pay in medicine) |
| The council chamber | the game's overseer's office | a council table; locked on the Council Key, left elsewhere in the vault | yes (22 Nov) |
| The reactor | reactor | the deepest room, at the end of the power wing | yes |
| The reclamation plant | workroom | a grinder bench, a big pot, blood | proposed only |
| The holding rooms | store | bedrolls, a bucket | not written down anywhere: where the bought are kept |

The proposed rooms are left out unless `proposed=True`. The vault is kept up (`kept`): no room is left wrecked, and none
of the ordinary vaults' stories (lived on, taken over, gone quiet) is used.

Locks are the generator's: a few rooms whose doors alone close them off (never one that would cut off anything else),
harder further down, and things to search; the council room needs a key that lies on top of something to search in
another room (the Council Key, a key record of the mod's own).

Measured, size 4, three layouts: 19 to 22 rooms, 5 to 7 levels, the reactor the deepest room every time, every square
reached from the door landing, no way out, no gap to fall through (with and without the furnishing), 4 or 5 rooms and
3 to 9 things to search locked.

Pictures, every level from above (rooms named, doors, locks, the key, things to search, stairs down):
- `waikiki-vault-inside-decided-1.svg`, `waikiki-vault-inside-decided-2.svg`: decided rooms only
- `waikiki-vault-inside-with-proposed-1.svg`: with the proposed rooms

The first version (decided rooms of 21 Nov) went into Waikiki on 22 Nov 2026 at 05:25 (nv-rs-pad): 19 rooms, walked clean.

## As decided, rehearsed on a copy (22 Nov 2026)

`D:\FOLab-vault2\vault_cave_into_waikiki.py rehearse` on a fresh copy of Waikiki (one Undo, "The Vault as decided, and
the first Ko'olau cave"): the Vault's place emptied and laid again (same place, same key record renamed the Council Key),
the gear door linked again (its lock as before), the back door outside and its path, the first Ko'olau cave
(waikiki-caves.md), their navmeshes, the outside cells' navmeshes made again. Measured, size 4: 24 rooms on 8 levels,
500 pieces and about a thousand things, the reactor the deepest room, every square walked with everything in (nothing
missing, no way out, no gap), nothing dirty, broken or failing; navmesh ~1,500 triangles, both doors on it. Read back from
the built plugin; health 0 errors and the same warnings as an untouched copy. Not in Waikiki: it goes in at an install
the user asks for (nv-rs-pad and nv-rs-next), `real` mode, with a backup first.

The back door outside (`app/rockdoor.py`): 1,600 below where Ka'au's climb meets the Crest Trail, on a 52° stretch of the
windward face, facing north-west down it: the game's mine door frame and cave door on a pad cut into the slope, a bank
behind, canyon rocks (one left out to keep the path clear), the path down from the crest signpost round the side and
onto the pad along the slope. Pictures: `waikiki-vault-decided.png` (every level), `waikiki-vault-back-door.png` (the
ground round the door, the path).

**Vault 50** (the user's pick, 22 Nov 2026). The place is named Vault 50 (`kaauvault.NAME`). The number shows where the
game shows one: the gear door. Vault 22's gear door, which stands at the crater, takes its number from a sheet of the game's
vault numbers, and the plate it shows was **92**. `app/vaultnumber.py` paints 50 on that plate (the game's own stencil
figures from the sheet's hatch strips, in the old figures' rust) and the install swaps the crater's door to a copy of it on
that picture (its link and lock kept). Picture: `waikiki-vault50-plate.png`. Nothing else in the Vault carries a number yet:
nobody is placed (so no jumpsuits; when people are, their suits' numbers come with them), and the rehearsal lists anything
the furnishing brings that's named for another vault. Someday there may be a "Vault 9" at ground zero by Pearl Harbor
(the user): nothing built for it.

Not yet seen in 3D or in the game. `kaauvault.ops(game, kits, size, seed, at, ...)` gives the changes for any copy.

## Open questions (for the user; nothing below is built in)

Answered 22 Nov 2026: **its number is 50: Vault 50** (the place's name; the crater's gear door now shows 50, below), who rules (a council of the founding families), how plainly the eating is shown (kitchens and
cold rooms too), lit and clean (yes), the way in (the gear door and a back door off the cliff trail), servants (they
remain). Still open:

2. **Who exactly lives there, and where:** the families, their young, the servants, guards? The generator places nobody.
   How many founding families (the council table seats two for now; one suite each?), how many servants.
   Decided 22 Nov: its people are predominantly Caucasian, with faces and names to fit, and the founding families' names
   suggest elite, rich backgrounds (WASP, Jewish, Italian and other affluent families); the council is of these families.
   The story session drafts the names for the user's approval: use those, never names made up here.
3. **The young companion's family:** does one of the suites belong to them?
4. **Where the bought people are kept** between the door and the table (the holding rooms, proposed), and the
   "protein reclamation" plant (proposed): in or out?
5. **The gear door's lock:** it is still locked on a key nobody has; is the front door meant to be shut to the player?
6. **The back door:** unlocked for now; should it be hidden (no map marker, none now) or locked, and does the cliff trail
   down to Waimānalo come with the settlers' build?
