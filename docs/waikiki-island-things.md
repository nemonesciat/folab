# Waikiki: island things in place of the Mojave's (night of 21 Nov 2026)

The user, overnight: "i liked what we did with new assets, updated designs ... i think we still need to add more custom
assets", "more items that add to the experience", "the world needs a lot more activity now that it is starting to look
good". For the user to pick from in the morning. **Nothing is in Waikiki or any game folder.** The pieces exist only as
code (`app/islandset.py`, `app/islandswap.py`); the swap was counted against Waikiki read-only.

## What shows most (counted, Waikiki's outdoor cells, 21 Nov 2026 22:00)

286,000 things stand outside in Waikiki's own world: 162,000 of FOLab's own, 124,000 of the game's. After the plants
(the plant sessions' area) and road pieces, sidewalk and car hulks (post-war, fine on an island), these read as Nevada:

| Game piece | In Waikiki | Why it reads as the Mojave |
|---|---|---|
| Lawn chair (Dead Money's) | 1,092 | aluminium-and-webbing lawn chair, everywhere |
| Crates (Brotherhood water crate stack, large crate) | 850 + 550 | stencilled for the Brotherhood and the Mojave |
| Canyon rocks (red sandstone, base game and Honest Hearts) | 1,278 | red desert sandstone on a volcanic island |
| Bitter Springs clotheslines | 459 | refugee-camp rags |
| Barbecue grill | 433 | a suburban kettle grill |
| Refugee tents (Bitter Springs) and Legion soldiers' tents | 134 + 106 | Legion canvas on Oʻahu |

Also Mojave, left for later or for others: honey mesquite, prickly pear, agave and their pickables (about 2,000:
plants), Italian cypress (384: plants), mailboxes (1,152: rural Nevada mailboxes, but they're containers with loot),
bedrolls (506: furniture you sleep on, need sleep markers in the model), wood shacks (about 500: the bamboo set's huts
could take some), tyre stacks and shopping carts (post-war, fine).

## Built: nine pieces (picture `waikiki-island-things.png`, `waikiki-island-rocks-finds.png`)

Each is made in the frame of the game piece it stands in for, so a swap is the ref's base and nothing else (Honest
Hearts' rocks get a lift: they stand on their origin where the base game's are sunk half).

| Piece | Stands in for | In Waikiki |
|---|---|---|
| Pineapple crates, stacked: slatted, stencilled KAHUKU PINES, fruit showing | the water crate stack | 850 |
| Shipping crate: HONOLULU, THIS SIDE UP, battens, rope | the large crate | 550 |
| Beach chair: folding wood, coral-and-cream striped sling | Dead Money's lawn chair | 1,092 |
| Clothesline: bamboo poles, two aloha shirts, a third, a pareo, a striped towel, board shorts | Bitter Springs' line | 459 |
| Huli-huli grill: an oil drum cut lengthwise on pipe legs, chicken on the grate, coals glowing | the kettle grill | 433 |
| Lava rocks, three: black basalt, pitted, rust-red weathering, lichen | the six canyon rocks | 1,278 |
| Tarp shelter: bamboo frame, faded blue tarp pegged one side and propped the other, mats, a crate, a lantern | refugee and Legion tents | 240 |

4,902 things in 1,299 cells, every one placed by the mod's own builders (none of them is in the plugin itself).

**Draws** (Waikiki is held back by how many pieces it draws): each piece's pictures are one sheet, so each draws once
(the grill and the shelter twice: their coals and lantern glow). The game's: crates, grill, Legion tent once; chair,
clothesline twice; refugee tent three times. The grill and the Legion tent's spots draw one more each, the chairs,
lines and refugee tents one fewer: over the city about 1,100 fewer draws in all (under one a cell: no change to how it runs).
Triangles are well under the game's (a crate 296 against 904, the shelter 1,274 against 2,912 and 4,816).

**Far:** only the shelter is big enough to see from the next cell; it has a far model (148 triangles, solid). The rest
are small, as the game's are, and have none.

**Navmeshes:** a crate, chair, grill or rock in the same place with the same footprint changes nothing worth a remake.
The shelter is open at the front where the Legion tent is closed, so its 240 cells could be made again if people should
walk in (`islandswap` lists them); left as they are, people walk round it as before.

## Built: five things to find and use

Loose things (one box of collision on the clutter layer, as the game's), each a record copied from the game's item it is
like, so it sells, weighs and (food) heals as that does. The Pip-Boy picture is the game item's for now.

| Find | Copied from | Value, weight |
|---|---|---|
| Ukulele | the Acoustic Guitar | 30 caps, 1 |
| Glass Fishing Float (green glass, a cord band) | the large whiskey bottle | 12, 1.5 |
| Tiki Mug | the coffee mug | 4, 1 |
| Coconut (heals as a mutfruit) | Mutfruit | 6, 1.5 |
| Pineapple (heals as a crunchy mutfruit) | Crunchy Mutfruit | 8, 1.5 |

Not yet placed anywhere: where they go is the user's pick. Ideas: floats and coconuts washed up along the tide line,
pineapples on the market stalls and in the fruit crates' spots, tiki mugs at bars and camps in place of some of the
game's empty bottles and coffee mugs (2,900 bottles and 1,400 mugs stand outside), the ukulele by camps and on porches,
and all of them in finds' levelled lists (lootplace).

## For the morning: what to pick

1. **The swap** (all of it, or by piece). One Undo, files and records only, about a minute; then a save and an install.
2. **The finds**: whether to add them, and where (above).
3. **More** if wanted, next in order of what shows: bedrolls as lauhala mats (506, needs the game's sleep markers),
   mailboxes as island mailboxes (1,152, keep their loot), wood shacks to the bamboo set's huts (about 500), a coconut
   palm drop (husks and fronds under palms), surfboards leaning on walls and fences, outrigger canoes pulled up on sand
   (waikikiset has an outrigger and a rack already), fishing nets drying on lines, shrine stones (a heiau's stacked
   rocks, offerings of ti leaves).

The stencils use texpaint's block letters (HONOLULU reads a little blocky); the signs' own alphabet (signfont) could
letter them instead.

## In Waikiki (22 Nov 2026 ~02:00, the user's "Yes, run it")

The swap, the finds and the remade loungers and beach bar went in as one Undo, "Island things in place of the Mojave's,
and finds" (backup: backups/Waikiki before island things 1122-0155), and into nv-rs-pad at ~02:15 (Waikiki.esp MD5
5826a98f..., no asset missing). Read back: 5,050 swapped, finds 350 coconuts, 400 pineapples, 400 tiki mugs, 139
ukuleles, 17 glass floats. Carried by the story session's 05:25 install into nv-rs-pad (MD5 a2590610...), the far
blocks rebuilt after it (44,440 far things, the shelters' far models among them). Not yet seen in game.

## Second batch, made, not in Waikiki (picture `waikiki-island-more.png`)

Lauhala sleeping mat (for the bedrolls: a furniture record still needs the game's sleep markers), island mailbox (for the
1,152 mailboxes: a container record keeping their loot), palm litter (dry fronds and husks under palms), surfboards in a
bamboo stand, a fishing net drying with glass floats, a fishermen's shrine (koʻa: stacked lava stones, a carved post, ti
and a coconut offering). Each one draw (the net two: its holes). For a later build.
