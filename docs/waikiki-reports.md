# Waikiki: what the user has reported

Every problem the user reports in the game or in FOLab goes here the moment it is reported, in their words, with where
they saw it. An item is closed only when the user has seen it fixed in the game, not when a check says so. Read this
at the start of any Waikiki work, and before saying anything is ready.

## Open

- **The wall's pieces turned 90 degrees, all along it** (19 Nov 2026, in FOLab: "The wall looks correct from distance,
  but all pieces turned 90 degrees the wrong way up close", cells -31, 1 and -35, 9 and -33, 7). Cause: the McCarran
  wall's record says it runs along x, its mesh runs along y. Fixed 19 Nov 2026 10:58: all 113 pieces (wall and Alewa
  Fort) turned a quarter, the builders and test corrected. Waiting for the user to see it.
- **The Vault ledge's concrete blocks are sloppy** (19 Nov 2026, in FOLab, cell -4, 14: "this path by vault looks good.
  these concrete blocks are sloppy tho"). Short blocks with gaps, each on its own bit of slope, none following the climb.
  Fix ready: 42 blocks out, 46 sections of the game's road guardrail in, end to end at the path's height, tilted to its
  climb (vaultgate.py corrected too). Saved 19 Nov 2026 12:34 (backup `Waikiki before the look-round fixes 1119-1234`); waiting for the user to see it.
- **Trees clipping into buildings, "quite a few plants are grown into new buildings"** (19 Nov 2026, in FOLab, cell 19,
  18, the settlers' town: "we should double check for this generally"). Cause: the builders' room check knew only the
  game's things, not FOLab's own plants and models. Fix ready: a sweep of the whole city, 2,805 plants whose trunk is in
  a building or near enough a wall for its leaves to come through (tents, clotheslines, trucks, shacks, the settlers'
  walls and halls, the McCarran wall...); the builders now see FOLab's own things (ridgeplaces.Builder). To save when
  FOLab is closed.
- **A panel of water above the land on the east coast** (19 Nov 2026, in FOLab, cells 36, 8 and 36, 9: "there's a panel
  of water above the land here"). Cause: cells (35, 7) and (35, 8) carry a stream or pond level of 295 over the whole
  square, the beach under it. A sweep found 13 such cells by the sea; 11 hold no pond and go to the sea's level (saved
  19 Nov 2026 12:34); (-19, -6) and (21, 13) hold a pond behind the beach too: for the user to look at. Also: the
  water at Hawaii Kai drew unevenly ("the lake is a cool effect with flooded buildings, but the water draws unevenly",
  cells 18, -4 and 16, -3): stream levels of 16 on ground at 16 beside the sea, and two dry cells under sea level;
  those 5 cells to the sea's level, saved 12:34.
- **Terrain shearing** (19 Nov 2026, in FOLab, cell 31, 1: "terrain shearing here"). Cause: 25 cell edges where the
  two neighbours' heights disagreed (lines along x 30|31, -31|-30, y 18|19: an earlier ground pass). Stitched (both
  sides to their average, blended four points in), saved 12:34; a scan finds none left. Waiting for the user to see it.
- **The Flotilla: boats sunk, and not grand** (19 Nov 2026: "shouldn't the boats be floating in a flotilla? Also, I was
  expecting something a bit more... grand"; then "make the flotilla a freighter with cargo crates on it ... a little
  more different than the settler's barge"). Rebuilt 19 Nov 2026 12:53 (`app/flotilla.py`): a cargo ship of FOLab's own
  (the freighter's hull, her house amidships, blue-grey) settled on the shelf, her deck stacked with shipping
  containers (`app/cargoset.py`, FOLab's own: the game has none), a planking ring, four gangplanks, rafts with a shack
  and a guard tower, six hulks lashed alongside, boats floating at their waterlines (walkcheck: ring, gangplanks, deck
  fore and aft, both rafts reached). The moored boats were too low everywhere: 89 raised to float (Kahala jetty, Koko
  Marina, the Ala Wai), and landmarks.MOORED corrected. Waiting for the user to see it.
- **Missing section of wall at the end** (19 Nov 2026, in FOLab, cell -34, -4: "missing section of wall at the end";
  the breakwater stops about 4,500 short of its last tower, standing alone in the sea at -132,710, -13,107). The user:
  "maybe you can level the terrain a little under the water there, to keep the breakwater above the sea level". Fix
  ready: a mound raised under the line to just under the wall's foot, two long pieces at the breakwater's height, the
  tower stood on the mound (top 468, the wall's 160). Saved 19 Nov 2026 12:34 (backup `Waikiki before the look-round fixes 1119-1234`); waiting for the user to see it.

- **Floating shacks, sandbags and crates, worst by the start** (reported many times, last 19 Nov 2026: "floating shanty
  shacks by the origin", "floating in midair again, i hate floating items", "its especially always by the start").
  Seen: a corrugated lean-to in the air in front of the Moana; sandbags `+0457BE` at z 1205 in cell -29, -1 by a
  scaffold. Cause: the roof camps (rooftops.py) were stood on roofs, then ground upwards (groundfit fit, close_gaps)
  moved the buildings and left the camps. Earlier float checks missed them (a building's bounding box counted as its
  roof; the mod's own pieces were skipped). Fix in hand: `app/settleup.py`, by real collision, the whole map.
- **Roof camps, lean-tos and scaffolds in the air: fix applied 19 Nov 2026 01:07** (`settleup.py`: 68 let down, 5
  lifted, 94 taken out, 13 ramp towers to nowhere taken out; navmesh remade, in MO2 and nv-rs). Waiting for the user to
  see it in the game before closing the floating item above.
- **57 rubble piles, barrels, crates and mailboxes 40-117 over the ground** (found 19 Nov by `origincheck.py`; not yet
  seen by the user): let down 19 Nov 2026 01:45 (`groundlet.py`), no navmesh remake (the piles already blocked the same
  spots; 51 cells now read "navmesh out of date" in health for that reason only). Also found: NVOfficeBldg03 `+0056A3` 90 over and NVNellisQuonsetHut01 `+013BF4` 63 over: buildings, to
  look at by hand (lowering may bury doors). One hotel view world cell (`Waikiki.esp:047352`) has an out-of-date navmesh.
- **Ten gaps under walls beside roads** remain after close_gaps (232 to 10): not yet looked at by the user.

## Closed (seen fixed by the user)

- Floating shacks, sandbags and crates by the start and the Moana: the user looked in the game 19 Nov 2026, "It seems
  to be fine now". (Still open from the same work: the office building and Quonset hut over the ground, the shack, car
  hulks and rubble in cell `Waikiki.esp:00111E` 41-72 over it.)

- Barren ground east of Makai Tower and on the new land (18 Nov 2026): new land planted, bare ground filled (79,104).
- Freeway pillars on cars, buildings and on other sections (18 Nov 2026): "it look spretty good besides those two
  spots", then the two overlaps taken out.
