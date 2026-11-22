# Waikiki's doors: the survey and FOLab's own (21-22 Nov 2026)

The user (21 Nov): the game's doors fit many Waikiki buildings badly, none of the hotels has a matching door, many homes
don't; then "also missing elevator doors". Pictures, before and after from the same camera: `docs/waikiki-doors.jpg`.

## Survey (1,918 doors outside in FOLabWaikiki)
Each door was measured against the hole in its building's mesh: the building's triangles within 56 units of the door's plane
drawn flat, the empty region round the door's middle filled. 1,629 doors hang flat on a solid wall, the game's way (no
hole); 222 stand in a hole; 64 have no frame round them; 3 no wall at all. Every pairing and spot is one the game uses, so
flat-hung doors fit as in the Mojave; there the misfit is look (office doors on houses).

Worst, measured (count, fault):
| Building | Game door | Doors | What's wrong |
|---|---|---|---|
| The Royal Hawaiian | DoorStorefrontDbl01 216x174 | 1 (+3 in its small worlds) | in a 296x320 arched bay: 60% open round it |
| The Moana | DoorStorefrontDbl01 | 1 (+2) | 152-wide bay: door wider than the bay, 43% over the piers, 60% open |
| The Kilauea | DoorStorefrontDbl01 | 1 (+2) | on the ground behind a lava planter at bearing 255, no frame; the way out arrived inside the planter |
| NoVacHouse01 | OffDoorSmL01 128x176 | 71 | behind the house's 88x144 frame, showing round it |
| NoVacHouse02 | OffDoorHotelSmStatic 120x174 | 52 | over a 92x140 hole |
| NVGoodSprhome01/02 | NVGoodSpringsHomeExtDoor 91x143 | 61 | in a 104x148 hole: 18% open |
| Usonianhome01/02 | NVRanchHouseExtDoor / WastelandhomeextDoor | 66 | 6-11% open |
| NVBungalow2 | OffDoorHotelBlankSmL01 | 169 | an office-hotel door on a house; many 8-40 off their doorway in z (reseated buildings) |
| NVDLC03TransmBldgTallwreck | UtlDoorBg01 | 28 | no wall round it (not done yet) |
| hotel lifts | HotelElevatorDoor01/02 | 24 | a one-sided panel 2 units deep: not seen in game |

Not done yet: the wrecked transmission building's doors, ~10 doors standing with no building, the shacks and barracks
(the game's own pairings; they fit).

## FOLab's doors (`app/doorset.py`, `app/doorswap.py`, `tests/test_doorset.py`)
Royal Hawaiian: koa double doors glazed above, a fanlight behind the arch. Moana: a white glazed door and transom, the bay's
width. Kilauea: a gold storefront (pair and side lights) on the drum's glass at bearing 240 (between two planters, clear of
the front fin at 270), the arrival in front of it. Homes: painted cottage doors made to each doorway, lined. Bungalow: a
cottage door in a casing. Lifts: bronze doors drawn both sides with a frame and floor dial, the game's frame kept.

Rehearsed on a copy (D:\FOLabScratch\doors, Waikiki.json of 21 Nov 21:26): 429 doors, 24 lifts, 40 arrivals moved, 933 ops,
one Undo, 281 navmeshes kept current, the plugin builds (105 MB), health the same as the untouched copy (0 errors), a
second run refuses.

In Waikiki and nv-rs-pad since 22 Nov 2026 05:25 (the story session's install, after the hotels' new floors): checks all
good, 460 doors, 31 lifts (6 lobby, 25 on the new floors, caught by `doorset.LIFTS` as it was), none unlinked, no game
lift door left. Not yet seen in game.

## The Royal Hawaiian's second lift (22 Nov 2026)
The user, in the 05:25 build: the Royal Hawaiian lobby has no lift doors. Its lift bank (east end) has two frames; only the
north one (`lift`) ever had a door. `lift2` came into the lobby's model on 17 Nov, when the lobby was laid out again, and
`hotelinside.relay_ops` only moves doors already placed, so its frame stood empty (the other hotels' lifts were all there).
`doorswap.missing_lifts` adds a FOLab lift door, locked, wherever a lobby's lift frame (hotelinside.VIEWS) has none: one on
Waikiki of 22 Nov 06:20. Picture: `docs/waikiki-rh-lift2.jpg`. relay_ops matches doors by the game's base, so since the
swap it no longer finds the lifts: a relay of the lobbies would leave them where they are.
