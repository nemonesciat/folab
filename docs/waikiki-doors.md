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
The north door also fell short of its frame (the user's picture from nv-rs): `lift_frame`'s opening is LIFT_H + 16 over the
floor, the game's lift door 174 tall. The lobby lift door is 190 now; `doorswap.refit_ops` writes the mod's door pieces'
files again and sets their records' OBND. The Kilauea's two lifts take the same piece: towerset stands
lift_frame (k 1/0.8, back 60) on its core at both the casino floor and the deck, so their openings are 216 x 190 in the world
too, and the 190 door fills them (`docs/waikiki-kilauea-lifts.jpg`). The Kilauea stands turned 180: its lifts face world +y.

## The Kilauea's way in (22 Nov 2026)
The user, nv-rs-next ~07:40: going into the Kilauea "just takes you outside but its a different space". The swap set the
arrival of every link to a Kilauea door to the outside point, and the lobby's door stands at the same spot as the city's
in the hotel's small world, so the way in arrived outside the glass in that world. Now an arrival is on its door's own side,
told by the door's world (`doorset.CITY`): outside `KILAUEA_ARRIVE`, inside `KILAUEA_INSIDE` (r 2500, as hotelinside's
arrive_in). `arrival_ops` sets the links again, `same_arrivals` lists linked pairs whose two links arrive at one spot (only
this pair, of every link in Waikiki). The lobby has no navmesh near the door; it hadn't before the swap either.

## The hotels' small worlds' door copies (22 Nov 2026)
viewworld.stage_ops copies the city round a hotel into its small world, doors locked and leading nowhere. By 21 Nov 21:26
(before the swap) 305 of those copies led into places and 74 places' ways out led into a small world, so leaving them put
you outside a hotel's glass. Neither the swap nor doorclear did it (they change no lock or link of a copy).
`doorswap.view_copies_ops`: copies of a city door still standing at their spot (same base within 2) locked, links taken off,
ways out pointed at the city's door: 265 copies, 61 ways out on Waikiki of 07:22. Left: the hotels' own doors and lifts, and
30 copies whose city door no longer stands there (13 places' ways out still lead to one of those).

## Ways in for the places only the hotels' small worlds reached (22 Nov 2026)
After the view-door step, 49 places had no way in and 4 still left into a hotel's small world. Two steps, run in order
(`tools/ways_in_into_waikiki.py`, `tools/cut_doorways_into_waikiki.py`, helper `tools/doorout.py`; the user: "do the ready
to make things", then "New doorways nearby"). Rehearsed together on a copy of Waikiki of 08:26 (D:\FOLabScratch\waysin2):
- ways in: the game's door statics near the old spot (191 have a real door of the same bounds) swapped for the door, only
  where its outside arrival is on the city's navmesh: 17 places.
- new doorways: a doorway the building really has (townbuild's catalogue, empty or shut with a static: 3), else a door hung
  flat on a wall of a building of the place's kind (house, shop, works; offices in office buildings, which the catalogue
  files as apartments), where the mesh shows one flat wall behind the door's width and height no deeper than 60 in from the
  box and the ground in front is on the navmesh: 31. One new door a wall. Touched cells' navmeshes made again (17 cells).
- Clutter named as such (crates, barrels, clotheslines...) in front of a new door taken away (19 things). A game model's
  bounds can be far smaller than it is: the first try took Quonset huts.
- Outside: which side is outside is told by the building's catalogue box, never by the navmesh (it covers the floors inside
  hollow buildings: 14 of 22 arrivals first pointed in). All 51 checked facing out.
- Health's places nothing leads to: 110 -> 63. Left: Offices003 and Offices004 (no fitting building within 9,000 with a
  doorway or a wall to take one). Picture: `docs/waikiki-new-doorways.jpg`.
- In Waikiki, nv-rs-pad and nv-rs-next since 22 Nov 2026 11:02 (the story session): ways_in 10:06 (16 linked, 4 arrivals
  facing in), fix_ways_in 10:57 (those 4 moved outside), cut_doorways 11:01 (35 places, 18 cells' navmeshes). Health's
  places nothing leads to 63, 0 errors. Not yet seen in game.

## Doors one can reach (22 Nov 2026, after the user: a door hung on a plastered wall caught the crosshair only at its rim)
`tools/doorray.py`: from 80 in front of a door at eye height, 25 rays at a grid over its face (from the middle of its bounds:
NVCraftsmanHomeDoor is made round its hinge edge) against the collision of everything near in the city (not the hotels'
small worlds: their copies stand at the same spots); a door counts when every ray meets it first. Of the 51 doors the ways-in
and doorway steps linked: 23 before. In the way: what had shut the doorway (DoorBarricade, a broken door), rubble, fruit
crates, and the building's own collision over the doorway (row houses, shacks, the Wrangler, the corner shops: the game's
shut doorways are closed in collision too). `tools/door_reach_into_waikiki.py`: loose things in front taken away (11),
then the door stood out from the wall 2 at a time until every ray meets it (19 doors, most 2-18; one, House863's on a
RowHouse02NV back wall, 54: that house's collision is a face ~50 in front of its drawn wall, so the door stands clear of the
wall there). 51 of 51 after, checked again from the saved mod; 21 cells' navmeshes made again. Not yet seen in game.
