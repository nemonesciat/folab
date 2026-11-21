# Waikiki armour and dress (21 Nov 2026)

The user asked for custom armour: "hawaiian warrior vibe? pirate options? something for the Huang, neo-traditionalistic
even?" and "maybe some unique chinese themed dress for the huang?". Of the ideas put to them: "love the armor ideas".
Then (21 Nov ~09:58): "Build and put them in".

**Built (21 Nov 2026, `app/armourset.py`, `tests/test_armourset.py`; picture `waikiki-armour-built.png`, painted by
the build's own code):**

| Piece | In game | Based on | Who wears it |
| --- | --- | --- | --- |
| Feather cloak | Ali'i Feather Cloak | Legion Praetorian | made; waits for the Kahuna's guard |
| Crested helmet | Mahiole | FOLab's own model, 0.18 clear of the game's head | made; waits for the Kahuna's guard |
| Fighter's armour | Koa Fighting Armor | Marked Men tribal (lauhala chest, coir, scrap shoulder plates with shark teeth) | made; waits for the fighters |
| Salvaged boarding armour | Salvaged Boarding Armor | Legion Centurion | **the pirates**: 2 entries in their body list |
| Captain's coat | Officer's Coat | Bounty Hunter Duster | made; waits for the captains |
| Huáng armour | Lamellar Armor | Legion Veteran | made; waits for the Huáng's guards |
| Everyday gown | Changshan | Veronica's robes | made; waits for the Huáng |
| Qipao-style dress | Silk Gown | Veronica's robes, red brocade | made; waits for the Huáng |
| Leaders' robe | Official's Robe | Brotherhood Elder's robe | made; waits for the Huáng's leaders |

Only the surfers, pirates and Waikiki's locals existed as people of the mod's own then, so only the pirates wore
something new. **Since (21 Nov ~13:00, `app/factionfolk.py`, picture `waikiki-people-placed.png`):** the Huáng, the
Kahuna's Guard, Court Fighters and Pirate Captains are made and placed, each in their piece; the Huáng carry the QSZ-92,
Type 79 and Type 81, the court the leiomano, pōhaku maul, newa and hoe paddle. Rehearsed on a copy; it goes into
Waikiki through the story session's write queue. The Silk Gown stands in for a
qipao: the cloth is right, but the cut is a long robe's.

Not tried in the game yet. The stats are each base's, minus its script and enchantment.

The rest of this page is the plan as it was put to the user.

Pictures:
- `waikiki-armour-mockups.png`: each armour's mock-up on the game's man and woman, front and back.
- `waikiki-armour-bases.png`: the game armour each one is based on, as the game has it.

The mock-ups are painted by a script in the scratch folder (`armourmock.py`, `armourdraw.py`, `qipao.py`). It labels
each pixel of a game picture two ways: where it lands on the body (cape, chest, arms, skirt, shins, feet, from the
mesh's triangles), and what it is made of (metal, red cloth, leather, cloth, from its colour). A recipe then paints a
pattern for each pairing, keeping the game's own folds and light. That is a first pass. A real build would want hand
masks wherever the guess is wrong: the officer's coat shows white specks of lining, and the boots are still the game's.

## What FOLab can make

- **A. Own pictures on a game garment** (like the Hawaiian shirts): works now.
- **B. Rigid headgear of FOLab's own** (like the boater and sun hat): works now. One model serves men and women.
- **C. New body shapes** (a cloak where the base has none, a fitted dress): not yet. Clothes that bend with the body
  need skin weights, which FOLab can't write.

Each armour is a copy of its base's record, with the models swapped for ours (as the shirts are), so damage threshold,
weight and value start as the base's. They're yours to set.

## Hawaiian warriors

**1. The aliʻi feather cloak, ʻahuʻula, and crested helmet, mahiole.** Who: the Kahuna's guard.
- Look: a red feather cloak with yellow crescents, over a woven lauhala chest guard, a tapa skirt, and coir arm and
  leg wraps.
- Made on: Legion Praetorian armour (A), for men and women. Its cape takes the feathers, its plates the lauhala, its
  skirt the tapa.
- Helmet (B): a close cap with a tall crest from front to back, in red and yellow feather, turned and swept like the
  boater.
- Caveat: the shape under it is still a Roman one (plated shoulders, the game's boots).

**2. The fighter's version.** Who: the court's ordinary fighters and the valleys' men.
- Look: woven lauhala and coconut fibre (coir) over scrap plates, with shark-tooth trim.
- Made on: the Marked Men's tribal armour from Lonesome Road (A), for men and women. The plates stay dull scrap; chest
  and arms take lauhala and coir.
- The shark teeth are not in the mock-up yet. They would be painted along the plates' edges, or made as a small
  rigid collar of our own (B).

## Pirates

**3. Salvaged diving gear and life-vest plates, tyre rubber and sailcloth.** Who: a crew's fighters and the press
gangs.
- Made on: Legion Centurion armour, which is already pieced together from other armour, for men and women (A).
  - The chest plates become orange life-vest panels.
  - The arm plates become dark dive-weight metal.
  - The straps become tyre rubber.
  - Cloth and the shoulder cape become sailcloth.
- Still to do: the mock-up's orange shows little, and the rest reads more grey than marine.

**4. The officer's coat.** Who: the captains (the Vault's exiles, in Pip-Boys).
- Look: a long navy coat over dark trousers and boots.
- Made on: the Bounty Hunter Duster (A), for men and women.
- Hat (B): a tricorn of our own, its brim turned up on three sides.
- Still to do: brass buttons and a sash, painted where the coat closes.

## The Huáng

**5. Lamellar armour** cut from their beached ship's hull, over padded jackets. Who: the guards at Makapuʻu gate and
the border post.
- Look: rows of laced iron scales on the chest and skirt, a red padded coat showing at the arms and shoulders.
- Made on: Legion Veteran armour (A), for men and women. Of all the mock-ups, this reads best.
- Helmet (B): a round iron bowl with a spike, a red plume and neck flaps.

**6. Everyday clothes: plain changshan.**
- Look: a plain long gown in dark indigo over black trousers.
- Made on: Veronica's robes (A), for men and women.
- The farmers' conical straw hat, dǒulì (B), is the easiest thing here: the sun hat's weave on a cone.

**7. Everyday dress: qipao-style.**
- Tried as brocade (peonies and cloud scrolls in red, jade or ink silk) on the Pre-War Spring dress, the same code as
  the Hawaiian shirts.
- The cloth reads Chinese, but the dress doesn't: a strapped 1950s sundress with a full skirt. A real qipao (high
  collar, fitted, side slits) is shape C, and no game dress has that shape.
- So, either:
  - the brocade on the changshan's woman's version, or on the robe below;
  - or wait until FOLab can make clothes of its own shape.

**8. The leaders' high-collared official's robe.** Who: those on the ship.
- Look: a long robe in midnight silk with faint gold clouds, gold trim on the collar and belt, black leather.
- Made on: the Brotherhood Elder's robe (A), for men and women. It already has the high collar and the long line.
- Hat (B): the official's black cap with two flat wings out the back.

## The hats and helmets (B), not drawn yet

These would be made the way the boater and sun hat were: shaped round the head, fitted against the game's head, one
model for men and women.
- Mahiole: crested.
- Tricorn: three-cornered.
- The Huáng's iron helmet: spike, plume and neck flaps.
- The official's winged cap.
- Dǒulì: conical straw.

## To decide

- Which ones first, and should any wait for better looks?
- The silk dress: put the brocade on a different garment, or wait for a fitted qipao of FOLab's own shape?
- The officer's coat: navy for all captains, or a colour each?
