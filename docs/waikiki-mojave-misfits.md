# Waikiki: what still reads as the Mojave

Surveyed 20 Nov 2026 from the user's `Waikiki.json` (538,972 things placed: 281,850 outside in the city's cells, the rest
in places of the mod's own). Counts are things placed outside. "Copies" are the same thing in the Royal Hawaiian's,
Moana's and Kilauea's view worlds (the city copied round each hotel: `viewworld.restage` follows the city when it changes).
Where: the nearest OSM neighbourhood and the nearest named place on the map. Every model below was looked at (its pictures
and textures), not judged by its name alone.

## Buildings that read wrong: to restyle with FOLab's own

| Game building | In the city | Copies | Why it's wrong | Where |
|---|---|---|---|---|
| **NVProspectorSaloon** (Goodsprings) | 2 | 0 | "PROSPECTOR SALOON" painted on its false front | Mōʻiliʻili by University Ave (-78768, 593: the user's screenshot); Ala Moana by the Bank of Hawaii (-124777, -1879) |
| **NVGeneralStore** (Goodsprings) | 1 | 2 | "GENERAL STORE" in the same Wild West letters, false front | Makiki Kai (-127041, 8144) |
| **NVOldWestBldgGeneric01 / 02** (Goodsprings) | 20 + 2 | 5 + 3 | Wild West false-front shops with plank porches (no lettering) | 01: Mōʻiliʻili 3, Makiki 3, Kaimukī 2, Kapahulu 2, Waikīkī 2, Pawaa 2, Waiʻalae-Kāhala, Hawaiʻi Kai, Nuʻuanu, Portlock, Capital District, Kakaʻako; 02: Waikīkī by Lewers St, Liliha |
| NVGSSchoolHouse (Goodsprings) | 2 | 0 | Red Wild West schoolhouse with a belfry; less glaring | Kapahulu (-76205, -10651), Liliha by Good Shepherd Church |
| NVNiptonTownHall (Nipton) | 1 | 0 | Western town hall with a clock; no place name on it | Waimānalo Beach (87949, 68539) |

## Billboards naming Mojave places

| Game billboard | In the city | What it says | Where |
|---|---|---|---|
| **BillboardBoulderLNV** | 4 | "BOULDER CITY", "HOOVER DAM", "LAKE MEAD" | Pawaa, Wailupe, Lower Mānoa, Capital District |
| **BillboardSunsetSarsaparillaNV** (its picture is Helios One's) | 4 | "HELIOS ONE, the dawn of a golden age" | Hawaiʻi Kai, Lower Mānoa, Kakaʻako 2 |

The other billboards (Corvega "Driving Paradise", 3; blank, 6) name nowhere and can stay.

## Desert plants (outside, by the dressing: `osmdress.PLANTS` 'scrub' and 'rock', `understory`)

| Plant | Placed | Mostly in |
|---|---|---|
| CreosoteBushLg / Sm | 833 + 603 | Mānoa, Hawaiʻiloa Ridge, Waimānalo, Kamilonui, Kamiloiki, Hahaʻione, Black Point |
| NVSagebrush | 1,276 | Kamiloiki, Black Point, Maunalani Heights, Kalama Valley, Pacific Heights |
| YuccaA/B/CNV | 305 | Kamilonui, Kamiloiki, Kalama Valley, Black Point |
| BananaYuccaPickable | 194 | Waimānalo, Kamiloiki, Portlock |
| NVbarrelcactus02 | 161 | Kamilonui, Kalama Valley, Kamiloiki, Black Point |
| pricklypearcactus02 / 03 | 157 | Kamilonui, Kalama Valley |
| HoneyMesquitePickable | 173 | Waimānalo |

Prickly pear (pānini) and mesquite (kiawe) really grow on Oʻahu's dry slopes, so they fit. Creosote, sagebrush, yucca and
barrel cactus are Nevada. They're on the dry ridges and valleys of East Honolulu, where real scrub is kiawe, koa haole and
pili grass. These are plants, so changing them is the plant budget's business (memory: plants draw budget), not a model swap.

## Looked at and fine

- **Plain wooden houses** (the ones round the saloon in the screenshot): Goodsprings homes 63, Victor's shack 105, Novac
  houses 129, ranch houses 129, wood shacks. No signs or lettering, and plantation-camp houses looked much the same.
- **AtomicWranglerExt** (51): a plain three-storey brick block. Its cowboy neon sign is a separate model and isn't placed.
- **NoVacGasStationANV** (22): a plain service station, no name on it.
- **CLSoldiersTent01** (106, mostly Waimānalo and the valleys): plain canvas. The Legion's banners share its texture
  sheet but aren't on the tent.
- **NCR guard towers** (8 + parts), **Strip street lamps** (23, on Kalākaua: the seats' work), Strip planters (15),
  garden lanterns (10): no Vegas or NCR marks.
- Signs: no-parking 298, stop 107, radiation 11, Honest Hearts trail signs 32 (the Crest Trail): none name a place.

## Inside (for later, your call)

These are only seen inside the places townbuild lends to buildings, and most are on purpose (the grand hotel and casino
floors): casino rooms 2,465, Lucky 38 rooms 742, Ultra-Luxe 274, casino tables and slots 491, Goodsprings room pieces
3,037 (plain wooden rooms), Hoover Dam lights 266, and **Dinky the T-Rex souvenirs and dino toys, 224** (Novac's
souvenir: the one item inside that names a Mojave place).

## People (a task of its own)

Placed outside: **183 prospector spawns** (VSpawnProspectorAll), about 250 Fiends, raiders, Vipers and Jackals. To make
them surfers and pirates: the mod's own versions with other outfits, and outfits recoloured or new.

## The plantation town and the billboards (in the mod since 20 Nov 2026 13:45; into nv-rs with the next install)

`restyleset.plantation` is one kit: board-and-batten walls in a colour gone pale (mint, butter, barn red, white) with white
trim, hipped tin roofs with deep eaves, a lanai of posts with a tin roof and rails along the door side, sash windows, a
raised floor on a plinth, a blank sign board. Pictures: `docs/waikiki-plantation-town.png`. Each piece is in its game
building's frame with its doorways where the doors stand:

| Game building | FOLab's | In the mod (city + hotel copies) | Triangles (game's) |
|---|---|---|---|
| NVGeneralStore | `plantation_store` (mint, red tin, storeroom east) | 3 | 4,128 (4,381) |
| NVOldWestBldgGeneric01 | `plantation_shop` (butter, green tin) | 25 | 3,060 (4,060) |
| NVOldWestBldgGeneric02 | `plantation_dry_goods` (barn red, storeroom beside its lanai) | 5 | 4,280 (8,346) |
| NVGSSchoolHouse | `plantation_school` (white T, green tin, bell, chimney) | 2 | 4,894 (10,746) |
| NVNiptonTownHall | `plantation_hall` (two storeys, columned south lanai) | 1 | 9,808 (17,566) |

Billboards (`restyleset.GAME_SWAPS`): the 4 Boulder City boards and 4 Helios One boards are now the game's Corvega ad
and blank boards, turn about; the Boulder City ones lifted 214 so the new legs meet the ground.

Each walked (walkcheck) to its doors; tests 47/47. In the mod: 53 changes, one Undo; the city's 47 cells round them
navmeshed again (138 doors, 1 missed: a door the hotels' swap buried 3,000 under the ground, as meant); distant buildings
redrawn (175 blocks); health 0 errors. Backup: `backups/Waikiki before plantation town 1120-1335`.

## What to do, one kind at a time

1. **Prospector Saloon -> beach bar** (`restyleset.beach_bar`): made, tested and walked. See below.
2. Done (above). **General store and Wild West shops -> plantation-town shops**: one kit in the same way, each piece in its game
   building's frame with its doors where the catalogue has them: a tin roof, a shaded lanai on posts along the front,
   board-and-batten walls, a blank sign board. 3 + 25 in the city, 10 copies in the view worlds (restage brings those along).
3. Done (above). **Billboards -> the game's neutral ones**: the 8 Boulder City / Helios One boards swapped for the Corvega and blank
   boards already in the city. No new pictures, no new names.
4. Done (above). **Schoolhouse and Nipton town hall**: less glaring. A plantation schoolhouse and a civic hall would follow the
   shops' kit, if you want them.
5. **Desert plants**: swap creosote, sagebrush, yucca and barrel cactus in the dressing for dry-slope plants, within the
   plant budget.

## The beach bar (in the mod since 20 Nov 2026 13:00; into nv-rs with the next install)

`app/restyleset.py`, `app/restyle.py`, `tests/test_restyleset.py` (20 checks); pictures `docs/waikiki-beach-bar.png`
(drawn offline with its own textures). A thatched Polynesian bar on the saloon's footprint (2,310 x 1,430 with eaves and
planters; the saloon is 1,940 x 1,190). The hall's roof is in two tiers, a shallow skirt under a steep top, with crossed
poles at the ridge ends; it's about 800 to the ridge and 920 to the poles' tips (the saloon is 620). It draws 8,468
triangles against the saloon's 9,798.

Its own pictures: bamboo poles with nodes for the lower walls, lauhala weave above them, aged thatch with a ragged
see-through fringe at every eave, and a tapa-cloth band under the eaves and on the lanai's beams.

Round it: a lava rock footing, a west lanai deck under its own thatch with carved tiki posts and string lights, lit
torches, carved tikis either side of the bar's door, and two serving hatches with counters and stools under the Tiki Room
sign (waikikiset's board, so no new name). There are glass floats in a net on the north wall, surfboards by the lean-to,
and two lava rock planters of hibiscus.

The doors: the bar's door is on the hall's west wall, exactly where the saloon's was. The store's two doors are where the
saloon's scrap doors were. It's closed inside: the door leads where townbuild sent it.

Walked (walkcheck): from the ground to the bar door, the store door, the shut door's front and both counters, no faults.
The swap keeps each saloon's place, turn, doors, links and locks, adds its lights (a torch fire and a warm lamp at the
counters, kept apart), and lists the cells to navmesh again. Rehearsed on a copy of the mod (an earlier, plainer version
of the bar): 6 changes, 3 cells navmeshed again in 15 s, saved, health the same as before. The distant blocks (lodobj)
also need making again for those tiles: the saloon had a far model.
