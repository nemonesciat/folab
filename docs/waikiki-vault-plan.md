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

## What's only proposed (waikiki-lore-additions.md, not decided)

- Internal name "A Modest Proposal".
- Servants and staff who outnumbered the rich and were eaten first; ration "lotteries".
- Food systems built to fail; a "protein reclamation" plant; cold storage far too large; a medical wing built like a
  butcher's.
- A back door at the top of the settlers' cliff trail.

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
| The feast hall | mess | a banquet table, wine, candles: where they eat | yes (they eat people; how it's shown is open) |
| The Pip-Boy workshop | workroom | a workbench, spare parts, electronics | yes |
| The cell charging room | workroom | computer racks, drained cells, a locked box of micro fusion cells | yes |
| The armoury | store | gun cabinet, reloading bench, locked ammo | yes (they pay in guns) |
| The clinic | clinic | operating table, surgical carts, a locked first aid kit, medical cabinet | yes (they pay in medicine) |
| The families' council | the game's overseer's office | a council table; locked on a key left elsewhere in the vault | who rules is open |
| The reactor | reactor | the deepest room, at the end of the power wing | yes |
| The cold store | store | empty fridges, chains | proposed only |
| The reclamation plant | workroom | a grinder bench, a big pot, blood | proposed only |
| The holding rooms | store | bedrolls, a bucket | not written down anywhere: where the bought are kept |

The proposed rooms are left out unless `proposed=True`. The vault is kept up (`kept`): no room is left wrecked, and none
of the ordinary vaults' stories (lived on, taken over, gone quiet) is used.

Locks are the generator's: a few rooms whose doors alone close them off (never one that would cut off anything else),
harder further down, and things to search; the council room needs a key that lies on top of something to search in
another room (an Overseer's Key, a key record of the mod's own).

Measured, size 4, three layouts: 19 to 22 rooms, 5 to 7 levels, the reactor the deepest room every time, every square
reached from the door landing, no way out, no gap to fall through (with and without the furnishing), 4 or 5 rooms and
3 to 9 things to search locked.

Pictures, every level from above (rooms named, doors, locks, the key, things to search, stairs down):
- `waikiki-vault-inside-decided-1.svg`, `waikiki-vault-inside-decided-2.svg`: decided rooms only
- `waikiki-vault-inside-with-proposed-1.svg`: with the proposed rooms

Not yet seen in 3D or in the game. To put it in a copy of a mod: `kaauvault.ops(game, kits, size, seed, at, ...)` gives
the changes (a place of the mod's own to add them to, then the navmesh, then the way out linked to the outside's gear
door). Nothing calls it from the editor yet.

## Open questions (for the user; nothing below is built in)

1. **The Vault's number,** checked against the canon list.
2. **Who rules:** an overseer, a council of the founding families, one family? (The council room is the overseer's
   office for now.)
3. **Where the bought people are kept** between the door and the table, and how much of that a player sees.
4. **How plainly the eating is shown:** the feast hall only, or the kitchens and cold rooms too (the proposed rooms).
5. **Who is inside and where:** the families, their young, guards, workers? The generator places nobody: Populate
   would need people of the mod's own (Vault jumpsuits, Pip-Boys), and the madness (kuru) may want a look of its own.
6. **The way in:** only the gear door, or the settlers' cliff trail as a back door (proposed), and where it comes in.
7. **Is it lit and clean,** as full power and comfort say, or is the rot showing in places?
8. **The young companion's family:** does one of the suites belong to them?
9. **Servants:** were there servants and staff (proposed), and are any left?
