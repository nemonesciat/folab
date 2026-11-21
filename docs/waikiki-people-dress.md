# Waikiki's people: from Mojave to Hawaiian (survey and proposal, 20 Nov 2026)

The user's ask: "prospectors and raiders need to become surfers and pirates ... more hawaiian shirts and sunglasses
and boaters". Nothing has been changed in the mod yet. This is what stands there now and what I propose.

## 1. Who the mod places, and where

Counted in `projects/Waikiki.json` (packaging/out/FOLab, 20 Nov 2026 12:34). "Area" is the side whose land they stand
on, read off `waikiki-territories.png`. Outside, they were all placed by `worldlife.people` at the scenes
`osmdress.scenes` made (camps, raider camps, roadblocks, refuges).

| Placed as (game base) | How many | Where (by area) | What the game dresses them in |
|---|---|---|---|
| `VSpawnProspectorAll` "Prospector" | 183 | pirates 50, pays both 36, Kahuna 36, settlers 34, Vault road 12, other 15 | cowboy hats, head wrap, slave scarf, metal helmet; leather/metal armour, merc outfits, brahmin-skin |
| `LvlWastelander` "Wastelander" | 94 | Kahuna 52, settlers 20, pirates 11, other 11 | caravaneer, field hand, settler, prospector, brahmin-skin, wanderer outfits, hats |
| Fiends (`LvlFiend2Gun/Rifle/MeleeVarNV`) | 190 outside | pirates 64, Kahuna 54, settlers 21, pays both 16, other 37 | Fiend helmets, raider spiked armour |
| `LvlRaider1GunVar`, `LvlRaider1MeleeVar` | 33 outside | Kahuna 33 | raider armour and helmets (Psycho-Tic, Painspike...) |
| Vipers (`VViperGangSpawnGunA/B`) | 33 | Kahuna 30, Heights 3 | metal armour, merc outfits, biker goggles, bandana, motorcycle helmet |
| Jackals (`VJackalGangSpawnMale/Female`) | 32 | Kahuna 30 | leather/metal armour, merc grunt, wasteland outfits |
| Inside: Fiends (mostly Vault 3's) and one raider | 87 | the Royal Hawaiian's Guest and Top floors (48), the Kilauea's three floors (39) | as the Fiends above |
| Inside: Powder Gangers (Vault 19's) | 51 | the Moana's Guest and Top floors | prison jumpsuits, dynamite |

Also placed: feral ghouls, spore plants, cazadores, geckos and other creatures (not people: left out here).

Things that don't fit the story, seen while counting (not part of this task; for the user to decide):
- **Hostile Fiends in the Royal Hawaiian**, the Kahuna's court (copied with the game's Vault 3 floors when the hotel's
  floors were made), Fiends in the Kilauea and Powder Gangers in the Moana.
- The raiders, Vipers and Jackals all stand in the Kahuna's land (they were the "easy" ones near the start).
- 34 prospectors and 41 Fiends and wastelanders stand in the settlers' land.

## 2. Decided and built (20 Nov 2026)

The user: wastelanders are pirates too; "we don't want jackal gang or wasters or raiders or whatever from the mojave, we
need appropriate themed baddies for the Hawaiian themed world". What a surfer is (perhaps a gang) is for later: for now
prospectors are only dressed as surfers.

- **Surfers** (`peopledress.KINDS['surfers']`): the 183 prospectors. Their own name "Surfer"; the game's prospectors'
  looks, levels, weapons, factions and behaviour. Hawaiian shirts (men) and dresses (women) in three bright prints, the
  Rattan Cowboy Hat (woven straw) more often than not, sunglasses about two in three.
- **Pirates** (`KINDS['pirates']`): every Fiend, raider, Viper, Jackal and wastelander placed outside (382). Their own name
  "Pirate"; each keeps its game spawn's looks, levels, weapons and behaviour, but all are in the Fiends' factions, so the
  old gangs don't fight one another. Old (worn) Hawaiian shirts in three dark prints, leather armour one in ten, a
  bandana or head wrap three in four, sunglasses one in four. No Mojave raider spikes or Fiend helmets.
- **Not touched yet:** the Fiends and Powder Gangers inside the Royal Hawaiian, the Kilauea and the Moana (places of the
  mod's own: left for the user to decide, question 4). None of the new pirates stand within worldlife's `SAFE` of the
  Castaway's start; the nearest two (wastelanders) about 9,000 units off.

### How (all the game's own meshes; nothing from other games)
1. **The shirt** (`app/garmentprint.py`). The game's *Pre-War Spring Outfit* (`Armor950StyleCasual02`) is a button-up
   shirt over trousers for a man, a dress for a woman, front and back laid flat on its texture. FOLab paints a hibiscus
   print over the cloth and keeps the game's folds, seams and buttons. The old check pattern is taken out of the shading
   (after the user's look: "it looks like a Hawaiian flannel"): the broad light from a median of the picture, only detail
   darker than it added back, the light taken against the light round it. The neckerchief the game painted in the shirt's
   V neck is printed over too ("a scarf over the shirt"). Trousers, belt, buttons and shoes as the game has them.
   Pirates' are painted over the game's worn ("Old") picture with its worn normal map. Mock-up:
   `docs/waikiki-shirt-mock.png`. (The user pointed at a Nexus mod, "Fear and Loathing in New Vegas Outfit", which
   retextures this same mesh with a flower print: looked at only; none of its files go into Waikiki.)
2. **Meshes: the game's with only the picture changed** (`nifwrite.retexture`, proven per mesh): three per print (worn,
   worn by a woman, lying on the ground), among the mod's own files with the pictures (DXT1, 1024 square, 0.7 MB each).
   An ARMO of the mod's own per print, copied from `OutfitPrewarSpring` (same slots and armour), named "Hawaiian Shirt
   (blue)" and so on, "Old Hawaiian Shirt (navy)" for pirates. (The game's own way, a texture set swapped in by `MODS`,
   would need FOLab to write links inside those raw entries to the mod's own records: not done.)
3. **Hats and glasses: the game's own.** `CowboyHat04` (Rattan Cowboy Hat), `GlassesShades`, `OutfitWastelandHat05`
   (bandana), `HeadWrap01..04`. In levelled lists of the mod's own (body, head, eyes for each kind).
4. **People of the mod's own** (`app/peopledress.py`), as the game builds its Viper and Prospector spawns: a copy of each
   game spawn, template the game's, its name, base data and inventory its own (template flags 0x80 and 0x100 cleared;
   pirates 0x04 too, with the Fiends' factions listed). The inventory is the game template's with each clothing list
   swapped for the kind's lists. The game's records are untouched: the Mojave's people stay as they were.
5. **The swap.** Each placed one outside gets a `swap` to the new base: same spot, same facing. One Undo a kind. No
   navmesh changes.
6. **Tests:** `tests/test_peopledress.py` (78 checks): the print only on the cloth, the check lines gone, records keyed
   as planned, the written plugin read back (names, templates, inventories, factions, outfits' models and pictures,
   lists only apparel), every spawn outside swapped, one inside left.

Not yet seen in the game: clearing "use base data" on the Lvl* spawns follows the game's own Viper and Prospector spawns,
but whether a woman's spawn still comes out a woman, and levels still follow the player, wants a look in game.

### The straw boater: what it would take
The game has no boater, and FOLab's model maker makes things that stand still, not things worn. A hat is a mesh bound
to the head bone (a skin with one bone), with a second model for when it lies on the ground and a Pip-Boy icon. To make
one FOLab would need to write a worn mesh: the game's *Pre-War Hat* (`Armor\HeadGear\1950StyleHat\M\SuitHat.NIF`) as
the frame, its skin data, bone list and partition kept, the shape replaced with a flat crown, a straight brim and a
band, every point weighted fully to the head; a straw texture from `texpaint`; the ground model; an ARMO of its own.
About a day of work, and it must be looked at in game (or nv-rs) before trusting it, because a worn mesh that's
wrong shows only there. Until then the Rattan Cowboy Hat is the straw hat.

## 3. Still open
1. What a surfer is (a gang?): later.
2. The boater: make it now (about a day), or the rattan straw hat for now?
3. The hostile Fiends and Powder Gangers inside the Royal Hawaiian, the Kilauea and the Moana.

## Every Mojave enemy left in Waikiki (survey 20 Nov 2026, after the surfers and pirates went in)

The user: "yes, all mojave themed enemies need to be replaced or removed please". Counted over every actor the mod
places (its source plugin places none), read only.

Outside: no Mojave gang is left (all 382 are pirates). Inside, only the three hotels' floors:

| Place | Who | How many |
| --- | --- | --- |
| Royal Hawaiian, Guest Floor and Top Floor (the Kahuna's court) | Fiends | 20 + 28 |
| Moana, Guest Floor and Top Floor | Powder Gangers (Vault 19's, some named Escaped Convict) | 24 + 27 |
| Kilauea, Guest Floors 1, 2 and Top Floor | Fiends, 1 raider | 9 + 10 + 20 |

Left alone as not Mojave: feral ghouls (the hotels' kitchens 53, outside 232), giant rats (function rooms 24), spore
plants and carriers (302), the Beachcomber (FOLab's own).

Mojave wildlife outside (worldlife.wildlife), for the user to decide: cazadores 64, geckos 90, giant mantises 31,
nightstalkers 24, radscorpions 6, lakelurks 5, and 72 from the game's mixed lists (deathclaws, Mister Gutsies,
protectrons, molerats, bloatflies, dogs).

## Straw hats (20 Nov 2026: "do both then please")

FOLab's own boater and lauhala sun hat (`app/hats.py`, picture `docs/waikiki-hats.png`) take the Rattan Cowboy Hat's
place in the surfers' head list (chance of none kept at 45%). Each ARMO is a copy of the Rattan Cowboy Hat (its slots,
value, weight), one worn model for men and women as the game's hats have. The Pip-Boy picture is the game's (the
fedora's, as the Rattan Cowboy Hat uses). Pirates keep their bandanas and head wraps.
