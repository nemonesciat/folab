# Waikiki: what the user has reported

Every problem the user reports in the game or in FOLab goes here the moment it is reported, in their words, with where
they saw it. An item is closed only when the user has seen it fixed in the game, not when a check says so. Read this
at the start of any Waikiki work, and before saying anything is ready.

## Open

- **Boater still on the side of the head** (21 Nov 2026 ~17:50, nv-rs-pad main-d9243748, third person by a stream:
  "boater still on side of head???"; screenshot `docs/waikiki-report-boater-side-2.webp`): after the 17:07 install with
  the "no Prn" fix the player's boater still hangs against the left of the head, brim vertical. Checked: the new
  boater.nif (16:56, 681d3e2e…) is the one in nv-rs, nv-rs-pad (mods and modgame\Data) and the build, so the fix
  itself doesn't work. Passed to the people session.

- **Distant trees too sparse** (21 Nov 2026, afternoon, 52 fps, looking NE at a green hill from a jungle rise; screenshot
  `docs/waikiki-report-far-foliage-sparse.webp`): "the distant foliage is a reallygood idea. its starting to look good. it
  should be a little denser though, maybe offer a few more sized to break monotony and big open stretches on distant
  landscapes". The far trees stand alone on bare slopes, all about one size. Passed to the story session (plantfar, lodobj).

- **The first quest's reward is lame** (21 Nov 2026, after 15:06): "captain;s lockbox loot is lame. it was like 4
  clipboards and some ammo", the reward "when u give box to beach comber". It was the game's duffle-bag lists
  (`castawayquest.REWARD`: LootDuffleBag100 once, LootDuffleBag25 three times), which are mostly junk. The user's choice: "Coat, pistol, stimpaks": the
  Officer's Coat, the QSZ-92 with 48 rounds of 9mm, five stimpaks (`REWARD`; `castawayquest.give_reward` compiles the
  script again, only the AddItem lines changed, so a save mid-quest goes on). A save past the reward keeps the old one.

- **Requests and feedback before going out** (21 Nov 2026, ~09:25), the user's words, each passed to a session:
  - "roads and rubble we made could use a little more detail. they're great so far, but look plain." (roads and rubble session)
  - "the trees in distance - the palm variety looks pretty good, the bulbous ones are still a little simplistic, and they
    need more variety - they all look like the same exact tree" (story session, `plantfar.py`)
  - "want to consider adding some custom armor types- would you suggest any? are there any that give hawaiian warrior
    vibe? pirate options? something for the Huang, neo-traditionalistic even?" and "maybe some unique chinese themed dress
    for the huang?" (people's dress session; suggestions first)
  - "at least a couple more types of chinese guns" (guns session)
  - "would like to see more neon lights, maybe some on the hotel signs, would be cool to see them from a distance glowing
    thru as storms roll in?" and "is it possible to get better, more stylized signage in general? text and theme is very
    simplistic." (own models session)

- **The QLZ-87 not seen when aiming** (21 Nov 2026, told to the guns session; seen earlier, game not yet said): "about the
  custom gun, i remember not seeing it when i zoomed down the barrel". The user, later: drawn in hand, then gone on aiming.
  Not yet known: nv-rs or the original game. Checked so far: the model's shape bounds are right (not culled by them);
  its sight line and ##SightingNode are the Light Machine Gun's exactly; no scope model (MOD3) on the record (nv-rs hides
  the first-person gun on aim only when there is one); the aim animations name none of its parts. Still different from the
  LMG's model: the shader's alpha-texture bit and the collision material. The check asked of the user: aim the game's own
  Light Machine Gun in the same game. The Huáng guns went in 21 Nov 15:06 (nv-rs, nv-rs-pad, MO2) with the QLZ-87's
  corrected model; not yet seen whether they show when aimed.
  Still gone on aim (the user, 21 Nov ~15:20, nv-rs-pad: the QLZ-87 and the QSZ-92, "could use enhanced texturing too").
  Cause found: every FOLab gun's parts had their unset pose written as +FLT_MAX (the game's is -FLT_MAX), a real pose
  10^38 away that the parts fly to once the controllers run; the QSZ-92 also kept the 9mm's scope overlay (MOD3). Fixed
  in gunmake/guns with tests; pictures 512 with machining, wear, stipple. Waiting for the game to close to go in.

- **Out of a house and into its walls** (21 Nov 2026, morning, in nv-rs-pad: "exiting a house placed me inside the
  building shell"; screenshot `docs/waikiki-report-inside-shell.webp`): coming out of a house's door left the player in a
  narrow dark gap between the building's walls and a row of stakes, not on the street. Suspect, not checked: the arrival
  point outside (`townbuild._arrive_out`, "a step outside the wall" for borrowed places, or a game arrival kept after
  groundfit moved or `restyle` swapped the building).
  Cause (story session, 21 Nov ~08:50): not the arrival. townbuild stood the game's `DoorBarricade` / boards for a doorway
  (`shut`) as well as the door itself, because the game stands its barricade 90-120 in front of the door and the catalogue
  counted only within 80 as the same doorway. 316 of 1,732 ways out had boards within 200. Fix rehearsed on a copy, not yet
  in the mod: `app/doorclear.py` takes out 542 pieces at 397 doors (316 -> 57 within 200; leftovers mostly the next
  doorway's), townbuild leaves them out from now on. Not checked: boards over a window beside a door.
  In the mod 21 Nov 08:57 (backup 'Waikiki before doors unbarred 1121-0856'); in nv-rs, nv-rs-pad and MO2 09:03 (MD5
  f5cbad00...; the plain game's Data too at 09:14, on the user's "Yes, update it"). Waiting for the user to see it.

- **Thin green lines across the view** (20 Nov 2026, ~21:00, in nv-rs-pad (main-d9243748) at night by the Natatorium and the Missouri: "why are these here again?", "see all these green lines?"; screenshots `docs/waikiki-report-green-lines-1.webp`, `-2.webp`): faint hairlines, long and nearly straight, drawn across the water and the air in front of the shore, as if a triangle or card had a corner pulled far away. Seen after tonight's installs (far trees remade, the city's grass thickened, guard towers, bamboo). Suspects, none checked: the new far tree models or rebuilt far blocks, a grass or plant model with a stray point, the bamboo or tower models' see-through edges. The user found it (screenshot `-3.webp`, marked in red): "its the top line of how this grass is drawn, it goes thru itself 3 ways, and the lines always appear at the top edge": a FOLab grass clump of three crossed cards, a thin line along each card's TOP edge. Likely the picture wrapping top-to-bottom: the stems kept opaque on the bottom rows (`modelsets.RIM_KEEP`, from the black-bars fix) are sampled at the top edge too (wrap mode, filtering and smaller mip levels). Fix to try: clamp the texture in v (the shader property's texture clamp mode) and/or keep the card's v inside half a pixel of each edge. Also in the first shot: grass blades growing up through a beach lounger (engine grass on sand under things); not yet confirmed with the user that this is what "these" meant.
- **A house with a wall missing inside** (20 Nov 2026, evening, in nv-rs-pad: "obviously interiors will need checking and work, but this house has a bare wall"; screenshot `docs/waikiki-report-bare-wall.webp`): inside a dark lent house, one whole wall opens onto blank white. The user wants interiors checked generally.
  Cause (proven 20 Nov 19:30 on the mod's data): `roomvary` (rooms not the same twice) took the game's whole house shell
  `UshomIntLight01` ("Light" means lightly worn in the game's house kit, read as a lamp) for a thing in the room and swapped
  it for `UshomIntLight02`, a shell of another shape: every copy after the first of the game's Usonian home, Goodsprings
  house and Nipton houses 3 and 4 stood with a side open. Not XESP / initially-off (the first guess): no copied place is
  missing a wall piece from what the game stands. Which house: the save's spot (nv-rs-pad autosave 19:19) is by
  FOLabWaikikiHouse330, a Nipton House 3 copy. Survey of all 1,787 places: 134 pieces in 105 places swapped that are part
  of the building (60 house shells in 53 houses, 4 army hut shells, wallpaper, rubble banks, signs). Code: `roomvary.MOST`
  (nothing over 600 across is ever swapped), `roomvary.mend` puts them back as the game has them; tests in
  `tests/test_roomvary.py`. In the mod 20 Nov 2026 ~20:05 (backup 'Waikiki before bare walls and Mojave things 1120-1954'), rehearsed first on a copy: 158 pieces in 126 places put back (also 24 Sunset Sarsaparilla posters the swaps had turned into the Strip's and McCarran's far walls: 'Imposter' read as 'poster'), health 0 errors, same warnings as before. Install: the story session's next.
  Found on the way: 61 places nothing leads to (left from buildings taken out); in the
  hotels' view worlds 18 copied city doors still lead into 12 places whose own door is locked and unlinked (you can't reach
  those doors from the hotels' rooms, but they're wrong); 60 shacks with no light of their own (the game's own are so);
  Mojave things on show inside (the user: "Mojave things out"; taken out in the same save, `townbuild.MOJAVE_SHOWN` / `mojave_out`, 370 in 179 places, Novac's dinosaur boxes made household boxes; copies made from now leave them out; `tests/test_mojaveout.py`): 59 Legion flags, 146 NCR posters, 35 Caesar bedrolls, 11 NCR decals, 10 Kings chalkboards,
  20 Novac dinosaur souvenir boxes and a few Primm, Lucky 38 and Gomorrah posters, in 186 places. Not checked: things floating or sunk.
- **Far trees look like lollipops** (20 Nov 2026, evening, in nv-rs-pad (main-d9243748) at Hanauma Bay, 45 fps: "right idea, but poor execution on distant foliage"; screenshot `docs/waikiki-report-far-trees.webp`): past the loaded cells FOLab's far trees are flat-shaded green blobs on bare poles, round tops sitting on the ridges like balls and a few hanging over the hills; they don't read as palms or forest beside the near trees. The far ground's green under them looks right. Passed to the story session. Fixed (~19:15): the far trees as lumps where each tree's leaves mass (broadleaf) or a fan of drooping fronds (palms), each in its own leaves' colour, every trunk 400 under its foot so a hilltop's coarser far ground can't leave it on air (`plantfar.py`); the blocks remade with the mod's own files seen (a bug of mine: without the overlay lodobj saw no FOLab far model; 175 blocks, 20,640 far things). Not yet in the game (it was running).
- **Desert plants on the dry ridges** (20 Nov 2026, the user via the build session: "yes, swap"; the list in waikiki-mojave-misfits.md): all 3,372 swapped: creosote and yucca to koa haole (FOLab's leafy shrubs) and kiawe (the game's mesquite), sagebrush to pili grass (FOLab's gold and dry tufts), the pickable banana yucca to pickable mesquite, barrel cactus to prickly pear; 609 on ground too steep for a FOLab plant became the game's mesquite in their own spot. None left. Reruns: `modelsets.DESERT` stand-ins on every dressing run, osmdress/understory lists changed. In MO2 and every nv-rs ~16:40. Not yet seen.
- **The Prospector Saloon in Waikiki, and other Mojave buildings** (20 Nov 2026, a screenshot in Mōʻiliʻili, the
  "PROSPECTOR SALOON" sign among plain wooden houses: "We should see about replacing more of the unique models in the
  Mojave, like the Prospector's Saloon ... This could be a tiki/luau themed beach bar about the same size. There are
  going to be other regionally flavored structures and statics in New Vegas that should get a restyle"). Surveyed:
  `docs/waikiki-mojave-misfits.md` (2 saloons, a general store, 22 Wild West shops, 8 billboards naming Boulder City and
  Helios One, the Nevada desert plants). The beach bar made (`restyleset.beach_bar`, picture `docs/waikiki-beach-bar.png`),
  walked and tested; in the mod 20 Nov 2026 13:00 (both saloons swapped, one Undo, 4 cells' navmesh remade,
  distant buildings redrawn, health 0 errors; backup 'Waikiki before beach bars 1120-1253'). Into nv-rs with the story
  session's next install (in every nv-rs ~13:15). Then the plantation town (general store, 22 Wild West shops, the
  schoolhouse and the Nipton hall, with their 10 hotel-world copies) and the 8 billboards naming Mojave places, in the
  mod 20 Nov 2026 13:45 (backup 'Waikiki before plantation town 1120-1335'); into nv-rs with the next install. Not yet
  seen by the user in the game.
- **People dressed for the Mojave** (20 Nov 2026: "prospectors and raiders need to become surfers and pirates ... more
  hawaiian shirts and sunglasses and boaters"; then "wastelanders are pirates ... we don't want jackal gang or wasters or
  raiders or whatever from the mojave, we need appropriate themed baddies"). Survey and plan `docs/waikiki-people-dress.md`;
  shirts and dresses in FOLab's own hibiscus prints on the game's Pre-War Spring outfit (the user's looks at the mock-up:
  the check pattern "looks like a hawaiian flannel", "a scarf or something over the shirt": both taken out). In the mod 20
  Nov 2026 13:55 (`peopledress.py`, two Undo steps; backup 'Waikiki before people dress 1120-1350'): 183 prospectors are
  Surfers, 382 Fiends, raiders, Vipers, Jackals and wastelanders are Pirates (one side, the Fiends' factions). In MO2 and
  every nv-rs 13:57. Not yet seen by the user in the game. The hotels' floors ("yes, all mojave themed enemies need to be
  replaced or removed please"; the user chose removed): 138 out (48 Fiends Royal Hawaiian, 39 Fiends + 1 raider Kilauea,
  51 Powder Gangers Moana), `peopledress.apply_clear`, one Undo, 16:44 (backup 'Waikiki before hotel gangs out
  1120-1640'), in MO2 and every nv-rs 16:46. Mojave animals left for now (the user's choice). Open: what a surfer is (a
  gang?). The boater and a lauhala sun hat made (`hats.py`, `docs/waikiki-hats.png`), the surfers' in place of the Rattan Cowboy Hat: in the mod 17:17 (one Undo; backup 'Waikiki before straw hats 1120-1714'), in MO2 and every nv-rs 17:18. Not yet seen in game. The user's look (21 Nov 2026): "havent seen any hats yet, the hawaiian shirts look good, but the shoes are also
  haweaiian printed like the shirts", "some variants with shorts", then of the first shorts tried "be sure those shorts look
  like beach shorts and not assless chaps. they almost seem risque". Found: the man's shoes' leather sits in his outfit's
  picture between the shirt fronts and was taken for a neckerchief, the woman's shoes where her sleeves were thought to be;
  now nothing below the ankle is printed (`garmentprint.FEET`). Shorts: Honest Hearts' Sorrows shorts were cut as high as
  briefs; now the Powder Gang's knee-length shorts on a bare-chested man (boots and belt plain, `docs/waikiki-board-shorts.png`),
  a woman in the same record in her printed dress, a third of surfers. Not yet in the mod. Hats: not yet looked into.
- **Hawaiian shirt with shorts, as well** (21 Nov 2026, via the beach kiosk session: "i like the swimming trunks you added,
  but i ALSO meant hawaiian shirt + short combos too, additionally, like the shirt/pants combos we have now. hawaiian
  shirt+shorts(like khaki or jean) would be cool to have too"). Wanted alongside the trunks and the shirt-and-trousers,
  not in their place. No game outfit is a collared shirt with shorts; mock-up of the shirt's top over the Powder Gang's
  knee-length shorts, khaki and denim: `docs/waikiki-shirt-shorts-mock.png`. The user's choices: the flap under the belt
  coloured in (it was the shirt outfit's own trousers: cut at the belt now), surfers an even mix (shirt and trousers,
  board shorts, shirt and shorts: "variety is good. some surfers having just shorts too"), and "maybe the shorts variant
  should be wearing sandals?": the game has none, so barefoot now (White Legs' feet), FOLab's own flip-flops later.
  Built (`outfitjoin.py`, `peopledress.combo_ops`, tests pass); into Waikiki through the story session (`dressup.py`, in
  17:07). Crashed when put on (21 Nov ~18:56, nv-rs-pad: "it was running great and then crashed when i equipped shorts and
  shirt"; "DrawIndexedPrimitive without an index buffer"): the joined model kept a shape with no triangles (the Powder
  Gang's belt and boots, all cut) and skin pieces with none. Fixed in outfitjoin (empty pieces and shapes left out,
  `empty_parts` checks); the six models again in `shortsfix.py`, waiting for the user's next build. Until then the six
  files in nv-rs-pad are a stopgap (the shirt-and-trousers model, 19:09).
- **The boater sits on the side of the head** (21 Nov 2026, in game, the player from behind: "boater also is on side of
  head"; the hat on its edge against the left of the head). Found: FOLab's worn hats (boater, lauhala, mahiole) named
  'Bip01 Head' as their parent ('Prn'), as the Pre-War Hat does; that bone is turned a quarter in the game's skeleton
  (its z is the head's left), so a hat made along the world's axes lies on its side. The game's cowboy hats name no bone
  and hang on HeadAnims, square to the world. Fixed in code (`nifmake.build_worn`: no Prn); the three hats' files
  go into Waikiki with the shirts and shorts (`dressup.py`). That was wrong: "boater still on side of head???" (21 Nov
  ~17:50, nv-rs-pad). The real cause, from the exe: every hat slot's rigid model hangs on Bip01 Head itself, whose own x is
  the body's up. Now the hats are skinned to that bone in the body's space, as the game's gambler fedora is (checked against
  its skin numbers; `docs/waikiki-hats-on-head.png`, its "before" the user's screenshot). The user: "get it in asap";
  `hatfix.py` through the story session. Not yet seen in game.
- **A glitched water tile up the shore** (20 Nov 2026, in nv-rs by the ruined freeway: "glitched water tile up shore"): a cell's own river level laid flat over a bank lower than it. 13 cells of 51 with their own water had such banks; the low pockets inside each cell raised 12 over the water (294 points, 50 things raised with them), one cell whose level was wrong written dry; none left inside a cell (pockets on a cell's edge, shared with its neighbour, left). In every nv-rs ~12:05. The user's look: "Better".
- **The city feels like the Mojave: "WHERE ARE THE PLANTS"** (20 Nov 2026, in nv-rs over the city, 21-27 fps: "this shit feels so unrealistic"; "i dont want a barren desert, but i dont want 10 fps. is this impossible?"). The grass grows on most wild ground (the census: about half the dry land by grassrule, more counting the mod's own twins it can't read; the rest roads and pavement) but thin. Made thick (`plantgrass.KINDS`: grasses 36-60, ferns 16-30, shrubs 12) and taro, heliconia and ti grown by the ground too; the far ground painted with what grows (`farfoliage.py`, through lodgen) next. Then the user's look at a lush stretch ("this has fewer trees and looks good too ... the answer isnt just more trees"): its ground is covered. Grass now right up to buildings (`plantgrass.BUILT_PTS`) and 384 from roads, not 512 (`CLEAR_PTS`). In every nv-rs ~12:05 with the thick grass. The user's look: "Better". Far ground green running.
- **Water banding at the start's bay** (20 Nov 2026, in nv-rs, looking over Hanauma's bay: "what causes this water banding?"): a straight-edged lighter band across the water. Ruled out: no cell there is dry (one in the whole map, (21, -7)), all the bay's cells the same water (XCWT FalloutNV 030009), the world's far water (NAM4) is 0 in the mod. Likely, not proven: the far ground under the sea (distant land, coarser) standing shallower than the near sea bed, so the water past the loaded cells is drawn as shallow water.
- **Round things floating beside the Missouri** (20 Nov 2026, in nv-rs: "floating objects that seem like they should be on ship"): three discs in the air level with her bridge. Ruled out: her model and far model drawn from the side (both right: the three domes sit on turret 2's roof), no placed thing high round her (the mod's or the plugin's), nv-rs's copy of her model the same file. Asked the user to point one out in the game.
- **The guard tower's floating, dangling parts** (20 Nov 2026, in nv-rs at the Flotilla: "your frequent reuse of this tower which has all this floating dangling shit on it"): NVGuardTower01 with panels hanging in the air round it; used by the Flotilla, the pirates' Kahala, the gun battery and the lookout. Being looked at.
- **The Flotilla's gangway, "sloppy"** (20 Nov 2026, in nv-rs): the rope-and-plank way from the dock up to the ship, its boards hanging at angles in the air beside the walk.
- **Can't get onto the road from the beach** (20 Nov 2026, in the game after the opening: "i asked for a path up to the road. you cant get on the road"). The user will fix it by hand: "ill fix it myself later". Nothing changed.
- **Black bars on top of FOLab's plants** (20 Nov 2026: "the plants here are still drawing these black lines on top of themselves", "its the fucking plants you made", "they carry the bars on top"). Solid pixels on the pictures' edges, wrapped to the other side of each card. The 19 plant pictures redrawn with a clear border (`dds.encode` `rim`, stems in `modelsets.RIM_KEEP` kept), in all four nv-rs copies. Not yet seen by the user.
- **"and no land was fixed"** (19 Nov 2026, same run): the land fix the story session was making isn't in the game.

- **The walls look bad in the game** (19 Nov 2026, in nv-rs with that day's build: "the walls look like literal shit in
  game?"; "they always look 90 degrees off in far view ... they dont even appear from far away"). My fault twice over:
  FOLab's model reader applied the root node's own turn, which the game leaves out, so FOLab drew McCarran's wallLong
  along y; I "fixed" the wall to look right in FOLab (10:58), which turned it wrong in the game. Reader fixed (`nif`,
  `hkshape`: the root's transform left out; 235 game models' bounds agree; 927 models have a turned root),
  `tests/test_nifroot.py`, the 115 pieces turned back, the code's turn undone. The far view hadn't been rebuilt since
  01:27, before the wall: rebuilt (the wall's pieces all have far models). Not yet seen in the game.
- **Gaps in the wall at every tower** (19 Nov 2026, asked three times: "every single one", "look at all these gaps",
  "it needs to look like something real"). I spaced the pieces by the towers' 660 foot; above the foot a tower is 348
  across and the wall 160 thick, so each end stood ~130 off the body; on the mountain, towers alone stood in a row with 288
  of air between. Two patch tries (scaled towers, filler pieces) measured boxes, not what's drawn, and changed nothing you
  could see. Fixed in the builder (`borderwall`: ends `INTO` the body, steps up steep ground, the wall stops at a cliff with
  a tower each side, the gate's towers at its ends) and the whole border wall laid again; the ridge square's sides laid
  evenly corner to corner (`ridgeplaces._wall_line`), its way in kept. Walking the line every 8 units: open only on three
  cliff faces (1,080, 1,080, 1,568). Not yet seen by the user.
- **Floating things** (19 Nov 2026: hovering billboard, boards over a trailer, "didn't check floating objects again").
  My checks read things' record bounds, which can be wrong (the billboard's says 62 under its origin, its mesh starts at
  it). Checked every thing in the world by its mesh against land and every thing's collision: 931 over land; 327 with
  nothing under them and nothing taller right beside them let down (boards 107, vines 77, rocks 32, mailboxes 31, trail
  signs 12, billboards 4, the two signs ...); doors, doorway boards and frames held by their walls left. Not yet seen.
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
  19 Nov 2026 12:34); (-19, -6) and (21, 13) hold a pond behind the beach too: the user, 19 Nov 2026: "get rid of the one at 21,13 and
  keep the other one" (21, 13 to the sea's level: saved 19 Nov 2026 13:33). Also: the
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

- **Distant hills look barren; trees and plants fade too soon** (20 Nov 2026: "is there no way to have a distant foliage trick or something, the distant hills look so barren and uninteresting"; via the other session: "trees and plants fade way too soon"). nv-rs's fade settings were already far out: the cut-off was the loaded cells' edge, and FOLab's plants had no far versions. Far versions of FOLab's trees, palms, tree ferns, bamboo, banana (`plantfar.py`, ~50 triangles each) in the distant blocks (175 blocks); the far ground painted with what grows (`farfoliage.py` through lodgen, 1,398 chunks). In every nv-rs ~13:15, files checked the same in each, far view clean. The user: "Looks good" (20 Nov 2026).
- **Plants floating, leaning, stems missing** (20 Nov 2026, in nv-rs-pad round the start: "whats with all these floating plants now", "why is it always the same plant", "the plant stems don't draw unless you're right up next to the plant, but the leaves do", "why are they all turned up at an angle", "more plants that fail to come down to the ground ... it feels like you didn't actually check any of this"; also a hovering mailbox, lamp post and power poles). Found: FOLab's jungle clumps (Undergrowth, Floor A/B, Thicket, Slope A/B, Log: 51,000 of 56,000 placed) are each one model of several plants, tilted to the slope as a whole, so on a crest or a bend in the ground the plants at its edges stand on air and every plant leans with the hill; the float check took a clump as one box (one corner on the ground = touching) so it never saw them. Stems: a thin stem down the middle of a see-through strip; in the far, smaller copies of the picture it fades out. Since 18 Nov at least, not new today. The beach path's two trail signs float 94 and 136 (mine, today). Measured over the whole city: 30,188 of 53,451 clumps have a plant more than 8 off the ground, 15,827 more than 50 ("you don't even lay them down intelligently"). Stems: the pictures' far copies keep the stem (checked), so that is not the cause; still unknown. Also "its always the same grass too" (20 Nov 2026): the slope clumps all use one grass tuft, one picture, five of every fifteen plants. Fixing (`plantsplit.py`): round the start (9 x 9 cells) clumps kept whole only on flat ground (124), the rest stood apart as single upright plants with six grasses (about 12,000), every FOLab plant there checked all round its lowest leaves (13,905, none over 6); stems solid at every size (`dds._keep_cover` over the cut, `texpaint.stick` halved plainly: nv-rs draws only alpha over 64, the stem's smaller copies were exactly 64). In every nv-rs 20 Nov 2026 ~09:00. Not yet seen by the user; the rest of the city waits for that. The user's look (20 Nov ~09:10): "overall its good", but "a bunch of them are buried into the dirt" (grass let down until nothing hung, on slopes its uphill side sank) and "back to barren dirt" (thinning and plants left out took ~9,000 away). Redoing it from the backup: each plant judged against how it sits on flat ground, neither hanging nor buried past a fifth of its height, leaning with banks (grass and ferns to 35 degrees), no thinning, a grass wherever the plant meant for a spot can't stand. Then frame rate ("frame rates are way too low now"): FOLab's grasses and small fern made the game's own grass (`plantgrass.py`, `nifmake.build_grass`), carried by the grass-bearing ground; round the start 51 hillside quarters given the grass twin of their rubble (none within 384 of a road, building, beach or water), 4,832 placed tufts and ferns taken out where grass grows now (6,324 kept where it doesn't); 19,075 things in the 81 cells. In every nv-rs ~09:40. The user's look: 12 fps on the rim road ("its awful right here"), 38-40 fps looking another way. Measured (the 5 x 5 cells loaded round a spot, each model's shapes a draw): the start 7,069 things, 12,693 draws, FOLab's plants 5,734 / 9,990 of them; the rim road 11,988 draws; Kalakaua 10,161 (FOLab plants 5,830). The game's own Mojave: Freeside's gate 1,691 things / 2,196 draws, Novac 1,109 / 1,403. Waikiki draws five times what the game ever does. Then (~10:00): FOLab's grasses on all wild ground round the start patch by patch (`plantgrass.paint`: 17,663 of 88,209 land points grow it, from 10,246), shrubs/ti/heliconia/hibiscus one draw each (`plantsheet.py`), placed plants held to `plantsplit.BUDGET` a cell (10,735 taken out, 3,448 kept). Draws round the start 12,693 -> 4,233, the rim road 11,988 -> 5,087 (FOLab plants ~1,530; the rest is the game's own things the dressing stood). In every nv-rs. Not yet seen; risk: bare ground where neither grass nor kept plants are. The game crashed with that build (~10:08, frame 6048: "heap exhausted allocating 1946157064 bytes", 0x74000008): FOLab's grass models' TallGrassShaderProperty was one byte short of the game's, so the picture path's first letter was read as its length. Fixed (`nifmake._GRASS_SHADER`), every grass model checked block for block against the game's; rebuilt into every nv-rs. The user then (~10:15): fps good, "the plants really seem thinned out"; low shrubs, ground ferns and small taro made game grass too, densities thicker, a quarter's spare layer reused: grass on 22,776 of 88,209 points round the start, draws 4,077. And "the whole plant is moving around": the grass shader sways a corner by its colour's alpha, the game's grass 0 at the ground, 0.1-0.3 up a blade, to 0.75 at a tip; FOLab's had 1 everywhere. Fixed (`nifmake.build_grass` sway, `plantgrass.SWAY`: grass 0.3 at the top, ferns 0.08, taro 0.05, shrubs 0.04), checked in every nv-rs. The user's look (~10:35): "the foliage is a little thin, but the grass looks better now, and it runs much better, too. the start works well now as well". Then the whole city the same way (~11:05-11:30, `plantsplit.rework`, `BUDGET_CITY`): grass on 1,108,004 of 4,116,420 land points, 51,305 clumps taken apart, 118,857 placed plants kept and every one checked on the ground (927 doubles on one spot out). Draws: the start 4,006, rim road 4,871, Kalakaua 5,901, inland 6,193, Waikiki beach 6,753. 542 clumps left in the hotels' view worlds. Health: the new warnings are navmesh signatures out of date (plants have no collision: the meshes stand) and one twin ground texture made twice. In every nv-rs. Not yet seen. The user, after the city build (20 Nov 2026 ~11:40): "Good".
- **The opening on the beach** (19-20 Nov 2026: "start is completely broken now"; the beachcomber said one line and looped, or left to fight a ghoul; no screens, no Pip-Boy). Hostiles near the start taken out, the talk moved on by dialogue closing (`MenuMode 1009`) instead of the lines' result scripts. Seen working 20 Nov 2026: "i was able to get through the opening fine".
- The Flotilla's containers clipping through the ship's side: the user looked in FOLab 19 Nov 2026, "that looks much
  better now".

- Floating shacks, sandbags and crates by the start and the Moana: the user looked in the game 19 Nov 2026, "It seems
  to be fine now". (Still open from the same work: the office building and Quonset hut over the ground, the shack, car
  hulks and rubble in cell `Waikiki.esp:00111E` 41-72 over it.)

- Barren ground east of Makai Tower and on the new land (18 Nov 2026): new land planted, bare ground filled (79,104).
- Freeway pillars on cars, buildings and on other sections (18 Nov 2026): "it look spretty good besides those two
  spots", then the two overlaps taken out.

- **nv-rs-pad crash logs, 21 Nov 2026** (the user asked the Workshop to check them; read by the story session ~19:30).
  Waikiki's data had 18 inventory or list entries holding a FORM LIST where an item belongs: AmmoList9mm,
  AmmoList556mm and AmmoList25mmGrenade, the gun's NAM0 copied into inventories. They were in the QLZ-87 test crate, the
  start footlocker, the Huang's 10 guards and 3 elders, and the Huang's ammo list.
  Fixed in code: `guns.ammo_item`, `factionfolk._ammo_of`, and a health check `not_an_item`, which finds all 18 in the
  installed plugin. The data fix is `fixammo_run.py`, queued for the next build the user asks for.
  Most of the day's stops go through ref clean-up in a cell, `00867f90` < `CellX::ProcessCellRefs`:
  - 08:08: inventory list read at 0x3a;
  - 09:14 and 17:45: a call through a bad pointer;
  - 08:37: a form lookup.
  The other two 00483714 stops (15:14, 17:27) are in marking a form deleted for the save. These fit a ref whose inventory
  holds a wrong-kind entry being cleaned up, but that is not proven. The 00483714 reads are of the game's own code
  address: a bad pointer chased. The game itself would read garbage there; nv-rs stops.
  Not Waikiki's: the frame-0 stops of the new nv-rs builds, "DrawIndexedPrimitive without an index buffer", and the
  heap free at frame 530 (a run on the Steam exe).

