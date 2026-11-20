# FOLab

A New Vegas editor in the spirit of Morrowind Workshop (`C:\Users\AMD RYZEN\Desktop\Morrowind Workshop`), which is
the model for style, UI and approach. Python, standard library first, code in `app/`.

## Ground rules

- **Game files are read-only.** Nothing ever writes into the game's `Data` folder; plugins we make are written
  elsewhere and copied in by the user's choice.
- **fnv_decomp: names and layouts, never code.** `C:\Users\AMD RYZEN\Documents\GitHub\fnv_decomp` (no licence in its
  repository; its authors told nv-rs anyone may use it, see nv-rs ADR-0009). Read it to learn how the game works; its
  names, types and record/structure layouts may be used (not its placeholder names made from addresses). Never copy its
  code or comments: write our own from understanding. Settle doubts in the game's own files or exe.
- **Engine apart from game.** Keep anything that depends on how the game is run (original game vs a possible OpenMW
  or source-port New Vegas: launching, config, scripts, navmesh) behind one small interface.
- Morrowind Workshop stays untouched; copy ideas or code from it, never edit it from here.

## Layout

- Readers: `tes4.py` (plugins), `bsa.py` (archives), `nif.py` (meshes), `gamedata.py` (the game as one thing).
- Mod: `project.py` (changes as JSON in `projects/`, undo/redo), `espwrite.py` (writes `build/<mod>.esp` by laying
  the changes over a `plugintree.py` tree: empty for a new mod, the plugin itself for an opened one, so untouched
  records keep their exact bytes), `adopt.py` (open a plugin as your mod: a copy in `projects/<name> source/`,
  loaded on top of the game, any mods it needs under it; it gains masters when edits need them: `masterlist.py` re-points every link), `install.py` (copies into
  Data + plugins.txt, backups in `backups/`); `copies.py` lists every other copy of the plugin the game could load
  instead (real Data, overwrite, other switched-on MO2 mods, nv-rs's mods): never report a mod as in while one differs
  (18 Nov 2026: yesterday's Waikiki.esp in Data played instead of MO2's).
- Editor: `server.py` (port 8771) + `web/index.html`, `web/app.js` (panels, edits), `web/world.js` (3D view).
- Building: places of the mod's own are '+ID' keys in both `records` (their CELL) and `cells`; door links are a
  ref change `tel` (XTEL, made persistent; arrival points picked in world.js `arrivalFor`). Snap pieces: kit
  pieces (same mesh folder, same turn) join on 128-unit steps, else box edges (`snapOffset`). Prefabs are JSON in
  `prefabs/` (bases by key, places from the group's middle and lowest point).
- Play: `playtest.py` starts FalloutNV.exe; Play here writes `FOLab Test.esp` (marker + start-enabled quest + one
  hand-compiled script, bytes checked against the game's own scripts; a new quest ID each time). Never call
  `/api/play` in tests: it starts the user's real game.
- 2 GB: `playtest.memory_room` reads the large-address flag of FalloutNV.exe (`state.memory`); unpatched, My mod shows a card linking the
  4GB Patcher's page and `roomToPlay()` (app.js) asks once a session before Play, Try it, Give. A map-made city ran a tester's game out of
  memory (15 Nov 2026): a crash in the scrap heap with virtual size near 2 GB in the dump's stream 22 is this.
- xNVSE: FOLab fetches nothing from the internet (Nexus's rule on tools that download): My mod links to xNVSE's page and `nvse.py` installs from the user's Downloads folder (an archive counts if nvse_1_4.dll is inside), unpacking into `downloads/`; its .dll/.exe go
  beside FalloutNV.exe (its config in Data\NVSE), records what it put in for Take out. The game starts through
  nvse_loader.exe when present (setting `launch_via`), else steam://rungameid/22380; never FalloutNV.exe directly
  (Steam's load error 5:0000065434).
- nv-rs (`nvrs.py`, setting `engine`: 'original' | 'nv-rs', `nvrs_dir`): the Rust port of the game, a folder of its
  own (C:\Games\nv-rs). With it chosen, Play / Play here / Give put the built plugins and their assets in its `mods`
  folder (listed in mods\folab.json, only those taken out again) and start `Play.exe --mods`; no xNVSE or JIP there
  (no save loaded at the menu). Its game is app\FalloutNV.exe, so `game_running()` sees it too.
  Folders of mods (`nvrs_setup`, `web/nvrsfolders.js`, `/api/nvrs/setup`, `/profiles`, `/play`), as OpenMW's launcher's data
  folders: each holds what goes in Data, lowest first (a later one's file wins), plugins ticked and ordered; `put_in` links the
  folders' files into mods (copies only off nv-rs's drive), FOLab's mod on top, and writes mods\plugins.txt (the DLC they need,
  then them); `from_mo2` fills it from a profile (`Loadout.layers`, overwrite last). Not yet tried in nv-rs itself.
- Own new game (`newgame.py`, `web/newgame.js`, `/api/newgame`; settings in `project.newgame`, op `newgame`, in Undo): a
  persistent named XMarkerHeading (a mod ref's `edid` is written as its EDID), a start game enabled quest and its script
  compiled by scriptc (MoveTo, hour, the screens as VCG04ActivatorScript opens them), VCG01's start flag cleared in an
  override; it leaves saves where VCG01 runs or is past stage 200 alone, and moves you only after `SETTLE` seconds and no
  cell load. Switching off the packs' or DLCs' start quests (opt-in) copies them whole, so they become masters (a bare
  pack quest lost its script and New Game crashed, 9 Nov 2026).
  Starting gear is the player's record (NPC_ 7). Worked in the real game 11 Nov 2026 (interior start, all screens,
  Pip-Boy), after what real runs taught: the game starts VCG01 whatever its flag says, so its bed stages are emptied
  (`_hush`) and the script stops it; the script clears `WhiteISFX`; a Pip-Boy put on by script in GameMode crashes the
  game (its manager re-runs the equip queue: stack overflow), so a fresh one is given and put on in a MenuMode block
  during the last screen, then `ResetPipboyManager` in play once worn. Don't reorder these without a real run.
  Since then, not yet run in the real game: an opening message (a MESG of the mod's own, `menus()`: it and the screens
  are what the Pip-Boy can go on in; none of them, `pipboy_gap`), the white kept until arrival, Try it on the card
  (Open in game), and tests for outdoor and own-place starts (`tests/test_newgame_places.py`). A crash
  leaves `%LOCALAPPDATA%\CrashDumps\FalloutNV.exe.*.dmp`: the faulting thread's stack against fnv_decomp's `@fnv`
  addresses names the loop.
- Create page (`web/create.js`): items in plain fields over the same records Browse edits; "Give it to me in game"
  (`/api/give`) reuses FOLab Test.esp: its quest runs player.AddItem once (bytes as the game's Hull20GaAddScript).
- Outside: `gamedata.py` indexes exterior cells (`ext_cells`, `grid(world)`), LAND (`land`, `land_at`, parent
  worlds' land), and the world's persistent refs by square (`persistent_in`, added to `refs(cell)`). `land.py`
  decodes LAND; `web/outside.js` streams 7x7 squares of ground (5x5 of things) round the camera via
  `/api/outside?xy=` batches. Editing outside: `edit()` files each change under its grid cell (`outside_cell`:
  a new thing by the square it stands in); the writer puts a copy of the WRLD (no OFST) with its children group,
  grid cells in block (y//32, x//32) / sub-block (y//8, x//8) groups, and persistent refs in the world's
  persistent cell (also Play here's marker).
- Ground: `project.land` {outside CELL key: land.py form, textures by LTEX key}, op `land`/`land_revert`, undo
  snapshots it shallowly (a change replaces a cell's whole entry). The writer encodes a LAND override (heights in
  whole 8-unit steps, normals from neighbours, VCLR, BTXT/ATXT/VTXT, at most 6 layers a quarter) into the cell's
  temporary group. `web/ground.js` is the brush (W.tool hook in world.js; W.lands for ground hits).
- Flat map: `web/map2d.js` (Map / 3D, M key; W.paused rests the 3D view). Outside, ground tiles from
  `maptiles.py` (16 x 16 cells, 16 px a cell; texture colours from `dds.py`), the game's own kept on disk in
  cache/maps/<game files' hash> and drawn ahead in the background; tiles with the mod's land drawn fresh.
  `/api/goto` (Ctrl+K): places, every world's map markers, 'x, y' cells, 'x y z' spots.
- Water: `project.water` {outside CELL key: height or None (the world's level, XCLW = FLT_MAX)}; the writer sets
  XCLW and the has-water flag on the cell's record. Lakes and rivers in `landshape.py` give each cell one level.
- New worldspace (`/api/world/new`, `worldgen.py`): the mod is saved with every game file as a master, the world
  added to that plugin, then the plugin opened as the mod (undo starts afresh) so the world is game data to edit. Its `trim_masters`
  lets the writer leave out masters neither the plugin nor the mod's changes use (`masterlist.used_by_file`, `grow(dropped=True)`).
- Auto-paint (`autopaint.py`): textures by slope band learnt from the game's land nearby; land shaping uses it.
- Real maps (help doc `real-maps`; FOLab fetches none of these files): `elevation.py` reads GeoTIFF/.hgt/PNG into a `Raster` (pixel centres; NaN for no data); `mapscale.py` is the scale (`Plan`: compress, exag, base at z 0, limits measured from the game; `heights` makes one `Grid` of land points for the whole world, whole 8-unit steps, slopes VHGT can hold, so cells meet by construction); `mapworld.py` paints by slope and hands `worldgen.add_world` a callback per cell (compressed LAND in the plugin, never `project.land`: a world of thousands of cells would not fit in JSON). `api_maps.py` (every `/api/maps/`, outside the server's lock, a job at a time; files copied to `maps/` under FOLab's home), `web/mapland.js` (the panel over the flat map, through `lsDraw`/`lsMouse`, and the World tools tab Real map). The way back: the mod kept in `projects/<mod> before map/`, `/api/undo` uses it when nothing else is left to undo and the mod has no changes. `projects/<mod> maps/` holds `made.json` (where each world came from: `osmplace.Georef` needs it) and `layers.json` (marker layer): in a folder, as every .json directly in `projects/` is listed as a mod. `osm.py` reads .osm XML; `osmplace.py` lays it as ops, one Undo (`roadgen.lay_line`, `landshape.shape_all` per shape, pads through `put_point`). `landcover.py`: a class file over the heights, textures through `Painter.cover` as the world is made, scatter as ops after. `townbuild.py` (`/api/maps/buildings`, Real map's Put up buildings) stands the game's stand-alone outdoor buildings on the layer's pads: a catalogue measured once (`buildings.json` in `server.kits_folder()`, `FORMAT`: footprint, doors in its frame, ground at middle/corners, family by editor ID words; upright mobile homes too, `DWELLING`), each plot's smallest rectangle, rows along the side nearest a road piece (side-on when nothing fits that way: trailer lots), `VARIETY` against repeats; the report's `cell_xy` is where Real map offers fresh outdoor navmeshes (`wnOffer`); generic (`GENERIC_USES`+ placements) fill ordinary plots, landmarks only on `is_poi` plots (named, civic, `POI_AREA`), once a world, alone on the plot; `KIND_WORD` picks by OSM kind within a family. Ways in: the catalogue keeps each building's `insides` (the game's interiors behind it, its way out, both arrivals); `Insides` picks some (`INSIDE_SHARE`, always on POI), `inside_ops` copies one as a '+' place (no actors, KEYM/NOTE/TERM/TACT, scripted non-doors, XESP or initially-off refs; no owner; other load doors locked), doors linked with `tel`; the rest locked 255; each place takes the game's own navmesh (`copied_navmesh`: one mesh, no outside links, doors re-pointed to the copy's named doors), else `navbuild.generate`. `project.apply` names: a record_new/add with 'name' is '$name' later in the same ops (`PR.names`); `apply(merge=True)` adds the navmeshes to the same Undo.
- A real city (on top of Real maps; tried on Waikiki, no buttons on the Real map panel yet: `/api/maps/make` options `coast`, `paint`, `relief`, `bumps`, `road_gap`, kept in the world's sidecar, and routes `/api/maps/landmarks`, `/api/maps/dress`): `coast.py` shapes the sea from OSM's coastline (`shape_sea`, land on its left), `roughen` adds small relief (not on `calm` points), `level_bumps` takes roofs a height file measured off flat ground (an opening `BUMP_REACH` wide, only where what is under is flat and only within `BUMP_NEAR` of a building on the map: without that it took the rim off Diamond Head). `osmcover.MapCover` says what each land point is (textures, `built`, `calm`); `osmplace.sparse` thins side streets at squeezed scales (`road_gap`); `townbuild` `stretch` lets buildings outgrow squeezed plots and `solid()` keeps facades and frames out of the catalogue. `landmarks.py`: `SETS` are the game's great buildings lifted piece by piece from where the game stands them (`lift`), `Batch.stand` levels, clears and nudges off roads and water, `Batch.harbour` builds OSM piers of dock pieces at the game's height over water with boats; run before buildings (townbuild then keeps off them). `osmdress.py`: things on the ground by kind, along and on the roads (`STREET`, `ON_ROAD`), what grows by kind (`PLANTS`, a pass of its own after `GROUND`: Zion's trees, Vault 22's ferns and grass scaled far up, banana plants, water plants in the shallows, pickables; `CLUMPS` come several together; cells in shuffled order under `PLANT_LIMIT`; spore plants and carriers in woods are `worldlife.IN_THE_WILD`), round each building by family and editor-ID word (`LIFE`, `LIFE_WORD`; the front is the side its first door is on), `scenes` (camps, raiders, roadblocks), `rough_roads` (rubble where a road is still steep). `landsoft.soften` eases what the mod shaped: roads first (`ROAD_STEP`), then the ground beside (`MAX_STEP`, or as steep as the land was before), ground under buildings and landmarks held (`keep`), everything on moved ground re-seated; all of dress is one Undo. `lodobj.py` writes distant buildings (block nifs counted from the world's south-west cell, one texture sheet) into the mod's assets, as `lodgen` does distant ground. Thing facings in `LIFE` are a guess (front = -y), not yet checked in game. Landmarks must be whole from every side: the Strip's casinos are street fronts round a hollow (The Tops' hotel blocks stand on stilts without its casino), so `tops` is the game's all-round `TheTopsWL` and `grandhotel` is put together from closed buildings; `closed_sides` measures it and `tests/test_landmarks.py` looks from sixteen sides. `osmdress.footings` lays what the game has round its own buildings (measured over the 557 it stands in the open: sidewalk slabs first, then rubble banked on walls): `SLABS` along each wall by each piece's own OBND, `BANKED`, `CORNER`. The Lucky 38 is closed by standing its casino four times about the tower (`round`) and the all-round `Lucky38WL` inside the shaft (`inside`). `osmplace.apart` lifts road pieces that lie over each other at one height `LIFT` apart (they flickered). `osmdress.lots` fills the plots nothing was built on by their size (`LOT_KINDS`, `LOT_BY_SIZE`: heaps, wrecks, walled yards, ruins, playgrounds, billboards). `worldlife.py` (`/api/maps/life`, after the mod's own new game says where the start is): `Life.air` a region over every cell (weathers by chance, a game region's sounds) with XCWT water and XCMO music on the cells, `zones` three ECZN by cells from the start (`TIERS`), `marker`, `people` at `osmdress.scenes`' spots (kept in `projects/<mod> maps/scenes.json`, landmarks in `landmarks.json`), `wildlife` by ground kind and tier, `settlement`; nothing hostile within `SAFE` of the start or the settlement. Nobody walks until the cells have navmeshes (`navbuild.generate_area`, about 4.5 s a cell). In the editor's own 3D view, `web/farthings.js` draws what stands past the loaded cells with the game's far models (`_lod.nif`), one instanced draw per model and map tile, from `/api/farthings` (`lodobj.Far`: the game's refs read once a tile, the mod's changes laid over each time); a far copy hides while its cell's things are shown in full. It isn't told when things change (`farThingsChanged` is there to call): a tile is fresh when next loaded.
- Another game's things (`othergame.py`, `tests/test_othergame.py`; no button yet): New Vegas has no big ship, so `SETS['carrier']` is Fallout 3's Rivet City read as that game stands it (`open_game`: a second `GameData` on its Data folder, found in a Steam library, never `downloading`; `lift`: pieces round the set's middle, laid along its length, heights from that game's water). `stand` copies each model, its `_lod.nif`, their textures and the textures' companions into `projects/<mod> assets/` (only what New Vegas hasn't under the same path), makes a STAT of the mod's own per model (`FOLab` + its editor ID) and places the set; `where` finds deep water clear of land. The copied files are the other game's: for the user's own play, not for a mod handed round (Nexus). `projects/<mod> maps/borrowed.json` lists them, `remove_borrowed` takes them out. `project.apply` resolves `$name` in a placed thing's `base` too.
- More on a real city: things that lie on the ground (`osmdress.LIES`: rubble, rocks, litter, tyres) are laid along its slope (`lie`), everything else stands upright. A plot the map calls a hotel (`townbuild.grand_kind`: its kind or its name) gets one of the game's big hotel or casino floors behind its door whatever building stands there (`GRAND`, `grand_inside`; arrival outside worked out from the door, `_arrive_out`; at most `GRAND_MOST` a go). Piers (`landmarks.harbour`): planking `DECK` over the water, not the 104 Lake Mead has, and `LANDING` pieces up the beach so a pier ends in the sand. `PLANTS` is 74 kinds; plants are never sown off the map's own area.
- Ways in, at scale (`townbuild`): `MAX_INSIDES` 240 a go, `INSIDE_SHARE` 0.6. `GRAND` is by kind (hotel, market, works, office, school, police, clinic; `grand_kind` from the plot's kind or name, `GRAND_MOST` of each). A building with a door but no place of its own borrows from its family's pool (`pools_of`, `POOL_THINGS`); one with no load door gets a way in where it has a door that leads nowhere or a `...DoorStatic` whose real door the game has (`entry_of`; counted `opened`). Borrowed places have no `arrive_out`: `_arrive_out` puts you a step outside the wall. Doorways with only boards over them get the game's `BlackPlane01` stood just inside (`boarded_ways`, `_facing`; counted `backed`). `PLANTS` also covers rock, farm and wet ground.
- Where the game grows grass (read from its code after two repaints put grass on roads and the beach, 15 Nov 2026): each LAND quadrant has 16 samples, at vertices 2, 6, 10, 14 each way of its 17 x 17, each looking only at the 3 x 3 vertices round it. A layer with grass counts at a point where its opacity is over the threshold T (an INI value, 0.3 in this engine's earlier games; the layer is skipped unless over 0.1 somewhere in the 3 x 3); a BASE with grass counts wherever 1 minus the sum of all six layers' opacities is over T, so it grows through any faded layer, a road's included. Each sample's nine weights are spread over a 512-unit patch, so blades reach a vertex or two past a grassy point. Every texture adds its own; none wins. So: a grass-bearing ground only well inside ground that should have it (3 vertices), at full strength or not at all, never as a base beside hard ground, and a twin texture with no grass for the fringe. The editor draws no grass blades: paint alone can't be judged there.
- After the user's look at the full build (16 Nov 2026): motel blocks and row houses (`townbuild.STRIP`) open only into the game's motel rooms (`ROOMS`), never a borrowed shop; boards (`board` rows) are left out of any doorway where a door or door prop stands (`unboarded`). `osmdress.seat_lying`, last of the dress job (and `seat.py` on a build): every lying thing (`LIES`, not `NOT_LIES` doorway boards) has its tilt fitted to the ground under nine spots of its footprint and is let down so none of its underside hangs; rubble that still would is taken out (`GONE_IF_HANGING`); one well over the ground (`SEAT_ON`) stands on something and is left. A FOLab server started for a scratch home sets `FOLAB_NO_GAME_WRITES` (`loadout.refuse_writes`): one without it put an experiment into the real game's Data on 15 Nov 2026.
- The Kilauea (`towerset.py`, `tests/test_towerset.py`): FOLab's own great tower (a volcano for a crown) in place of the Lucky 38,
  which read as Vegas on the beach. A landmark set of one of FOLab's own pieces: `landmarks.SETS['kilauea']` has `own` (a
  modelsets piece), `Batch._own` puts its files and a STAT op (first in `done`), stands it with its lights; `standing` keeps
  later steps off it by the mod's record. Its own worn pictures: `mosaic`, `shaft`, `gold`, `amber`. Hotel fronts are
  `texwear.FRONT_BAYS` 8 x 8 a picture (a 2 x 2 one read as a pattern in game). Far water: a world's NAM4 is its sea level,
  NAM2/NAM3 the water `worldlife.air` gives its cells (`world_water_op`); a FOLab world kept the Mojave's -2300 under its sea.
- Waikiki's historic buildings (`historicset.py`, `tests/test_historicset.py`): FOLab's own Royal Hawaiian, Moana, Natatorium
  and Battery Randolph, `landmarks.SETS` with `own`, where the game's grand hotel, Tops, swimming baths and gun battery stood in.
  Front (-y) is the SEA side for all four. Own pictures: `period_sheet` (arched / sash / bunker bays), `arch_board` and
  `balustrade` (see-through), `fluted`; trees of the set's own merged in by `combine`. The Natatorium's walls go `NAT_DEEP`
  down: it stands on the shore line, pool out to sea. Downtown (ʻIolani Palace, Aliʻiolani Hale) is off the Waikiki map: later.
- Waikiki's people (`peopledress.py`, `garmentprint.py`, `tests/test_peopledress.py`; `docs/waikiki-people-dress.md`): the game's
  spawns the mod placed outside swapped (`swap`) for NPC_ of the mod's own, one Undo a kind (`KINDS`: prospectors dress as
  surfers; Fiends, raiders, Vipers, Jackals and wastelanders are pirates, all in the Fiends' factions). Each copy keeps the
  game's template but its name, base data and inventory are its own (template flags 0x80, 0x100; pirates 0x04), the
  template's clothing lists swapped for the kind's. Shirts and dresses: FOLab's hibiscus prints over the cloth of the
  game's Pre-War Spring outfit (the check lines and the painted neckerchief taken out, folds kept), on its meshes
  retextured (`nifwrite`), not by MODS (FOLab can't write links to its own records inside those raw entries). Places of
  the mod's own (the hotels' floors) are left. garmentprint needs numpy/PIL/scipy (not in FOLab.exe's Python): a build step
  run from the developer's Python. Not yet seen in game.
- Rooms with a view (`viewworld.py`, `hotelinside.py`, `tests/test_viewworld.py`): the engine draws nothing outside an interior,
  so the game builds the Lucky 38's lounge and penthouse in a world of their own (Lucky38World, set under the Mojave: PNAM 4,
  its own copy of the land and far view; read from the game's files 16 Nov 2026). `viewworld.add_world` adds such a world
  straight to the mod's source plugin (`SourceWriter` numbers as that plugin does; nothing else in it changes, ids from the mod's
  `next_id`): never `server.new_world` on a big mod, it bakes every change and orphans navmesh and newgame keys. `stage_ops`
  copies the city's things round it (no actors, activators or initially-off refs; doors locked), `far_view` draws the city's
  far ground and buildings for it (`lodgen`/`lodobj` `like=`). `worldgen.add_world` takes `parent`, `use`, `flags`, and a `wet`
  that may give a level. `hotelinside.VIEWS`: each hotel's open piece (`royal_hawaiian_open`, `moana_open`, `kilauea_open`:
  the outside as before, the lobby and a lookout or deck inside, glazed so you see out and can't walk out), its things and
  doors in its frame (scaled with the ref: the Kilauea stands at 0.8); `view_ops` furnishes the world and links the way in
  with a door on the city's copy. `hotelfloors.py` (its docstring; `tests/test_hotelfloors.py`) the floors between, as
  places of the mod's own, lift from the lobby to the first, the top floor's lift (on the penthouse key) to the lookout.
  Not tried in the game. After the city changes round a hotel, `viewworld.restage` brings its world in line: the city's land on
  each of its cells, each copy moved to where its original stands now (same base within `MATCH`), what the city gained copied in;
  the hotel's own rooms and the closed hotel (`skip`) left.
- The USS Missouri (`battleship.py`, `shipinside.py`, `shipplace.py`, `tests/test_battleship.py`): FOLab's own battleship in place of
  Fallout 3's carrier (no borrowed files: a mod with her can be handed round). Model maker shape `hull` (stations of sections, one
  prism of collision per section: each corner on three faces, as Havok wants; solids thinner than ~10 don't close in `nifmake.check`,
  so rails' collision is a 30-wide wall with no look). Her frame: middle at the origin, waterline z 0, bow -y (port +x); `deck_z`,
  `half_beam`, `SPOTS` (gangway gap, the quarterdeck and bridge doors); `COOL` keeps her grade grey. `shipinside.PLACES` are four
  places, each one model (`Room`: walls with framed doorways, decks, overheads, built-in fittings) plus the game's things by editor
  ID (Rivet City's lights, naval chairs, bunks, lockers); doors are RCSmDoor01 (leaf across y, face to x). `board` makes the places
  (records copied from NellisHangar2's), links all eight doors both ways, the gangway, a pier to the shore, the marker; the old base's
  lockers go to the port berthing (empty). `shipplace.swap` takes out the carrier, its way aboard and its hangar base, stands her
  where it lay (port side to shore). navmeshes: `navbuild.place_refs` now gives a mod's own STAT its `model` and navgen reads its
  collision from the mod's files (`_solid_of_file`); before, the mod's own models were nothing to a navmesh. Not tried in the game.
- The Missouri aground (`shipway.py`, `natcompound.py`; the lore in `docs/waikiki-lore-additions.md`, she keeps her name): she lies
  off the Natatorium along the shore, bow to its -x (north on Waikiki), starboard to the shore, on the bottom at the height that
  puts her deck `RISE` over the sea wall's top; the floor under her just under her hull, round her up to `REEF` over her keel.
  `beach` moves everything on her (in every world holding a copy: a mod's own thing stays in the cell it was added to, so each is
  removed and added again, doors re-linked both ways). The way aboard: steps up through the arch and the walk over the bleachers
  (`historicset.NAT_*`), the pool's side wall, the sea wall, a dock-plank pier `PIER_LONG`, the scaffold stair tower (`tower`, a
  modelsets piece) to her rails' gap; the bathhouse is a copy of PrimmSheriffStation (placeholder). Her damage is in
  `battleship.missouri` and `damage` (blast from ahead and to port, her sea side): see-through sheets laid on her (`_side_decal`:
  a turn about y of +lean leans a port sheet out with her flare; -lean, as the hull number first had it, hid its top half in
  her). `natcompound` is the wall (junk walls, sandbags, rubble; gaps where roads cross), the park cleared but for `KEEP` trees,
  a screen of trees toward the city. Not tried in the game.
- Pip-Boy world map (`worldmap.py`, `tests/test_worldmap.py`; no button yet, `pipmap.py` in the scratch folder runs it): a world FOLab made had no ICON (worldgen drops the template's), so the Pip-Boy map was blank and nothing could be fast travelled to. `picture` draws a 1024 square in the game's manner (grey: shaded heights, dark sea with a pale shore, roads, pavement and buildings from what the mod placed, a cell grid, the frame's ticks and corner brackets); `ops` writes it under `textures\interface\worldmap\` in the mod's own files and a `record` op on the WRLD sets ICON, MNAM (size, size, then north-west and south-east cells of the square) and clears DATA's no-fast-travel flag. Markers are left as they are (flags 2: they show once found). Run it after anything that moves ground or stands things.
- Roads in the ground (`roadbed.py`, last in `/api/maps/dress`, after `landsoft`): the game's road piece is a slab, top at its origin, sides 25 under; the Mojave stands its origin about 14 over the land (5 in 100 with a point more than 32 over). `bed` lays every piece again on the ground as it is (slope along, a lean only where the ground leans), brings the land to the pieces' planes (the mean where pieces share ground, `ROUNDS` times so they agree), re-seats what stands there; `gaps` measures. Without it 37 in 100 showed their sides on Waikiki, with it 3. `roadgen.UNDER` is 12 for the same reason. Pavement (`osmdress.footings`' slabs) is bedded there too, harder: a slab's mesh is a bare sheet 16 over its origin with no sides (the game hides the edge with kerb pieces), so the sheet goes `SLAB_OVER` above land made flat and level under it (held ground by a building's wall too), and a slab whose ground still isn't flat within `SLAB_ROUGH`, or is in the sea, is taken out; `slab_gaps` measures. `footings` cuts each wall's strip into slab-size squares (scaled to the wall's length, `SLAB_FIT`), drops squares off dry open ground or lying in a slab already down (`laid`: two sheets at one height flicker). Doorways: `townbuild`'s catalogue keeps `shut` beside `doors` (what the game closes a doorway with when nobody goes through: a `...DoorStatic`, `DoorBarricade`, a door that leads nowhere), stood with the building; a building with neither (mobile homes, wrecks) has its door in its own mesh or none. Boards over doorways (`WoodPlanksGroup*`) count as `shut` too. A landmark set with a catalogue building among its `extra` pieces stands it with its doors and `shut` once `landmarks.know(cat)` was called (the landmarks route does): the grand hotel's wings were see-through at the door without. To look at a scratch home in the editor: launch config `folab-look` (port 8773).
- A big mod's edits: `Project.save` writes land and navmesh entries from the text kept for each (an entry is only ever replaced whole, never edited in place: keep it so), everything else afresh; `save(afresh=True)` (Save) trusts nothing kept. `_snap` copies cells and records through pickle. An edit on Waikiki (39 MB) went from 4.6 s to 0.2 s.
- Grid and pivot (after Morrowind Workshop's, a tester's asks 16 Nov 2026): `web/gridview.js` is the View tab's Grid, a plane
  put down and left there (at the selection, turned to it, right-click Put the grid here, or Fit the grid to the ground
  here: tilted to the slope, for cities on hills; Tilt and Facing in degrees), lines at the toolbar's Grid step, every
  fourth bright. `web/pivot.js`: the toolbar's Pivot (Median point, Individual origins, Active element), through
  `W.pivotAt`/`W.pivotEach` in world.js, and the View tab's Mouse (Blender's: middle-drag circles, Shift slides, Ctrl in
  and out; `W.blenderMouse`). `web/grab.js`, with Blender's controls: G and R pick what's selected up to move or turn
  with the mouse (X/Y/Z an axis, Shift+X/Y/Z the other two, a typed number exactly, click or Enter sets, Esc or right
  button puts back), a drag like the handles' own (`gizmoStart`, `gizmoFollow`, `commitSelected`); while one is on,
  `W.grabbing` keeps world.js's own Esc and right-button cancel off it. `web/placefold.js`: Place panel's Prefabs,
  Recently used and Suggested fold away (remembered), Suggested and Recently used by themselves while a search is typed.
  FOLab.exe waits as long as the server runs (it gave up after 180 s: through MO2 a big load order took longer).
- Rooms not the same twice (`roomvary.py`, `tests/test_roomvary.py`): the game lends only 116 places to a city's buildings
  (5 shops), so one place stood behind up to nine doors of Waikiki. `twins` finds copies of one place by what they're built
  of; every copy after the first gets things swapped like for like (`Swaps`: same nouns, bounds within `FIT`, same game file,
  no script, not a quest's/vault's/faction's, `NOT_IN`), loose things thinned, and a light of its own (`MOODS`, LNAM's colour
  bits cleared); doors and anything named, locked or linked kept; navmeshes stay current. Runs at the end of
  `/api/maps/buildings`; a copy no longer like the first is left alone. townbuild stands a door the catalogue has twice
  in one doorway once (`TWIN`: Waikiki had 80 doubled: office doors, shop-front door statics, planks).
- Walk before navmesh (`walkcheck.py`, `tests/test_walkcheck.py`; `py -3 app/walkcheck.py [name ...]`): a set's real
  collision walked as navgen sees it (Field, Graph, erosion), from flat ground round it or given starts (a ship's
  gangway, an open hotel's `arrive_in`). Faults: `invisible` (walked on, nothing drawn within `SEEN`: the guard tower
  without its parts), `short` (reached only if actors were thin: a way narrower than an actor), unreached `goals`.
  Other areas out of reach (roofs, closed insides, the guard tower's top deck, which the game's own navmeshes don't
  reach either) are listed only. Run it on anything people walk on before a navmesh run: a remake of Waikiki's took
  2.5 hours. Found 17 Nov 2026: the Missouri's bridge wings join the 03 level only through a gap ~32 wide.
- Ground upwards (`groundfit.py`, `roadbed.onto_roads`, `tests/test_groundfit.py`; after the user's look, 18 Nov 2026: buildings on
  grass plinths, cars in road slabs, tents off hills): the order is land, then roads bedded flush (`roadbed.bed`, buildings
  holding only their footprint), then buildings set to the street those roads make (`groundfit.fit`: `L` read past the walls,
  the building `SINK` under it, its yard cut or filled and eased back over `EASE`, never touching a road's ground within
  `ROAD_REACH`; close neighbours share a level, `TERRACE_MOST` the most one is lifted for it), then lying things seated
  (`osmdress.seat_lying`), then things in road pieces lifted onto them (`onto_roads`, `INTO_ROAD`), then standing junk let
  down off slopes (`settle_pieces`). Each step run twice changes nothing. padfill's banks are what this replaces. Last, `close_gaps` (after fit): a building still
  with daylight under a wall (`GAP`: by a road's ground, or one fit left) let down as far as its doors (`DOOR_BURY`) and its uphill
  side (`UPHILL_BURY`) allow, the land under its open walls filled up to its foot (only raised, never a road's); Waikiki 232 to 10. Not done:
  the hotel view worlds' copies of the city keep the old heights.
- Bare ground filled (`understory.py`, `tests/test_understory.py`; after the user's look, 18 Nov 2026: valley floors and road verges bare
  between the dressing's clumps): by the texture the game draws on top at each land point (`CLASSES`: none on pavement, asphalt,
  gravel, water; rock and sand thinner, `REACH_OF`), a clump (`MIXES`) wherever no plant stands within `reach` and the ground isn't
  steeper than `STEEP`, off roads, buildings and landmarks; each clump counts at once. Waikiki took it at reach 256 (79,104 plants).
  By hand: the Ground panel's Fill bare brush (`web/ground.js` `fillCommit`, How close = reach) posts a stroke's circles to
  `/api/ground/fill` (`server.ground_fill`: `fill(area=...)`, only the cells round it, ops back, nothing changed), then sends them
  to `/api/edit` labelled `understory.BRUSH_LABEL`; the game's plants and the landmarks are read once and kept (`_GAME`, `_MARKS`).
  A stroke is 0.3 s; the edit after it is Waikiki's 4.7 s save (194 MB of JSON), as for any edit there.
  A grown world's `api_maps.map_cover` plans on the grown box (it covered only the first one: the new land's plants were dropped).
- Plants that run and stand (20 Nov 2026, after a day of floating, buried, thinned and 12 fps plants on Waikiki). Count draws
  before handing a build over (each model shape a draw, the 5 x 5 loaded cells): the game's busiest places draw ~2,000 (Freeside's
  gate 2,196); Waikiki's start drew 12,693, 4,000 after. Low cover is the game's own grass (`plantgrass.py`): FOLab's grasses,
  ferns, low shrubs, taro, heliconia, ti as GRAS (`KINDS`), on grass-bearing twins of the wild grounds (`WILD`, `twins`), laid
  patch by patch (`paint`: `CLEAR_PTS` from roads, sea, beach; only `BUILT_PTS` from buildings). Grass models are
  `nifmake.build_grass`, byte for byte the game's blocks (one byte short crashed nv-rs reading a 1.9 GB length) with the sway in
  each corner colour's alpha, 0 at the ground (`plantgrass.SWAY`; 1 everywhere swung whole plants). Placed plants
  (`plantsplit.py`): clumps were several plants as one model and can't follow ground (51,305 taken apart); `rework` keeps each
  cell to `BUDGET_CITY` draws (jungle-shaping plants first, low green spaced) and `seat`s each by its own lowest points (`judge`:
  neither hanging past `HANG` nor buried past `BURY_SHARE` of its height; leaning with banks, `LEAN_MOST`/`LEAN_LOW`; else a
  grass, `seat_some`). One shape a plant (`plantsheet.py`: leaves, flowers, stem on one picture sheet; `dds.encode` `strips`,
  each strip its own coverage; a stem's strip plain). Stems vanished a few metres off: `_keep_cover` left them at exactly the cut
  and the game draws only over it (now `>`). Cut-outs drawn once across a card get a clear border (`rim`, else a bar along the
  card's top). Far off: FOLab's trees have far versions (`plantfar.py`, ~50 triangles, in lodobj's blocks) and the far ground is
  painted with what grows (`farfoliage.Cover`, lodgen's `foliage`). A cell's own water over a lower bank: raise the pocket.
- A ruined freeway (`ruinedfreeway.py`, `tests/test_ruinedfreeway.py`): the map squeezed H-1's bridges flat, so the old freeway
  stands over its ground road, broken: the game's `OverpassSectionLo01` chained along the freeway's line (`join` makes runs of the
  street map's pieces; one height a chain, `UNDER` the land, never `DEEP`), a span fallen now and then with its rubble below, ends
  broken or on a ramp; none where the line bends (`BEND`), a pillar lands in a building, a building reaches the deck, or the other
  carriageway has one (`APART`) or its outline overlaps one standing (`_overlap`; `clear` takes the later of two out, and
  whatever stands in a pillar's foot). Waikiki: 15 sections after the user's look (crossings at interchanges, both carriageways decked).
- Loot (`lootplace.py`, `tests/test_lootplace.py`; the plan `docs/waikiki-loot-plan.md`): the game's own containers (levelled
  contents) placed where they make sense, harder spots paying more: `band` by thirds of the way from the new game's start to the
  world's farthest cell (not worldlife's zones: from Hanauma Bay those put all Waikiki past the last), one up for `PLACES` (held or
  high, by map marker name), behind the wall, the north. Outside a find stands against an anchor (`ANCHOR` words: tents, crates,
  wrecks, roof camps' crates, cairns), its back to it, its front by its model (`front_of`: the side with handles, latches or a dial;
  a footlocker's is -x, a gun cabinet's -y, a safe's +x: the game's containers face every way), seated by `Seat` on the land and
  every placed thing's collision (`Solids`, settleup's), never on a road piece, in water, a doorway, another thing's footprint
  (walls seen from above are lines), and checked corner by corner as it stands (`SEATED`). Inside: empty containers become the full
  one of the same model (`FILL`), safes, gun cabinets and some kits and boxes locked by band (the lent places lost the game's
  locks), finds against walls where the navmesh ends. Keys: KEYM of the mod's own on the lid of another find of the spot.
  `new_ways` adds ramp towers and roof camps through `rooftops.plan(only=, extras=False, limit=)`. Never let `modelsets.put`
  write over a ramp's file already in the mod (its towers were walked on the old design): the run script adds missing files only.
- Sky (`web/sky.js`, View > Sky): a shader dome round the camera, haze at the horizon; View > Distant buildings is `FT.on`.
- Packaging (`packaging/`): `build.py` makes out/FOLab (FOLab.exe + its own Python + app) and a portable zip;
  FOLab.exe (`launcher.cs`, after MWWS's) runs `python\pythonw app\server.py --no-browser`, finds it by
  `folab_running.json`, opens an Edge app window titled "FOLab", quits it with POST /api/quit (X-FOLab-Quit).
  `brand.py` draws the logo/icon (wrench F, gear O, LAB) into app/web/vendor. Themes: `web/theme.js` (CSS variables; `TH_FONTS` is a choice of its own, any font with any theme).
- Home: `web/home.js`, the logo's page (`page('home')`, last script so it wraps `page`, `setState`, `loadPlaces`, `openPlace`); FOLab opens there unless unticked. Right-click the logo: About.
- Right-click on lists: `web/listmenu.js` (rows of Places, Objects, Outside, Place, and any other `.row`); Edge's menu stays only in typing boxes and on selected text. Placing: `W.place` {yaw, scale, raise} in `world.js`.
- Characters page (`web/characters.js`, routes `/api/char/` in `api_characters.py`): NPC_, CREA, PACK, FACT in plain fields over the same records as Browse; the
  inventory is `create.js`'s editor. A character's look comes from the mod's records (`look`; `actors.py` is for the game's). Packages start as copies of the game's
  `Default*`. Faces copy FaceGen numbers only; the game's painted face files (`textures\characters\facemods`) can't be made yet: `warnings` says so. Levelled means
  what the game does: an actor whose TPLT is the list, never a list placed. `populate.py` plans from a survey of who the game places where; a ref's `xlcm` is XLCM.
- Game settings: `gameini.py` edits Documents\My Games\FalloutNV\Fallout.ini + FalloutPrefs.ini line by line (backup
  first, read-only kept, never while the game runs; `FOLAB_NV_INI` points it elsewhere, which tests always do).
  Borderless is FOLab's own: windowed at the screen's size, frame taken off after FOLab starts the game.
- Navmesh: `navbuild.py` keeps a place's mesh in `project.navmesh` (op `navmesh`; `others` for a place's further meshes), `espwrite` writes NAVM + NAVI + each door's XNDP, Kit tab makes it. Outside, `navbuild.Area`/`generate_area` joins cells to whatever is round them; neighbours are whole copies (`copy`, same triangles, links changed). Meshes that had to go become stubs (`navmesh.stub_mesh`). `Area.mend` takes off links that don't point back before the check (3 of 35 batches of 40 Waikiki cells had one, never the same batch twice from one start: the cause is not found; `tests/test_navmend.py`). `navedit.py`: by hand, `web/navtool.js`. `navmesh.py` reads/writes NAVM and NAVI byte for byte and holds the rules (its docstring: what a
  plugin must do), `navgen.py` generates a cell's mesh, `hkshape.py` reads collision shapes. Run `py -3 app/navmesh.py`
  to recheck every game record. Collision triangle soups wind either way (they came from strips): don't trust facing.
- Navmesh cover: `navgen.mark_cover` marks each new mesh's open edges that have a wall beyond them (edge 0-1 in bits 0-5 of a triangle's cover flags, edge 1-2 in bits 6-11; `navmesh.COVER_BITS`; NVCA lists them), as the Mojave's do (2 triangles in 100). Not optional on a big mesh: someone looking for somewhere to hide searches outward for a cover triangle and nothing else ends the search, so a 188,000-triangle city with none crashed the game when its camp was walked into (15 Nov 2026: a write to null+0x34 at 006A7F22, the pathfinder's node pool run out). The value's meaning (taken as height in sixteenths) is a guess: the game only asks if it is over 0. Generated outdoor meshes are also 2.6 times the Mojave's triangles a cell, not yet thinned.
- Kits (`kitindex.py`): building pieces per mesh folder on each kit's grid; each side's section (cut just inside it from the
  mesh) says if it's a way through and what it meets; `kit.seen` is every join the game built. `Tileset` + `build_area` fill any
  squares with every side agreeing (one-square, one-level pieces; `kitplan.py` adds plans, stairs and big pieces); `can_walk_out` checks a
  layout from the real meshes. Editor: `web/kits.js` (Joins under Selected, the Kit tab), `/api/kits`, `/api/kit/piece`, `/api/kit/layout`.
- Tools page (`web/tools.js`, one hook `/api/tools/` to `modtools.py`): `health.py`/`health.js` (reads the plugin itself, so any plugin; fixes are ops;
  models: each one there read through its block table, `mesh_broken` and `mesh_collision` (`Scan.BAD_BLOCKS`), and a missing one offered the file
  of that name under the most like path, `near_model`, fix `repath` for every record naming it, never male for female), `loadorder.py` (plugins.txt + file dates, backup first; test only with a fake Data and `LOCALAPPDATA`), `changes.py`/`mychanges.js`, `release.py` (zip into `releases/`, own files from Data or `projects/<name> files/`), `merge.py`/`mergepage.js` (grafts a plugin; the result becomes the mod, like a new world). `formlinks.py` is every form link's byte position, raw parts included; `py -3 app/formlinks.py` rechecks it against every game record. Op `drop`: an opened plugin's record left out on save (`project.drop`).
- Generated places: `kitplan.py` plans first. A side reads as a word (F full, A along a wall, P passage, . closed), a square's four words say what it is in any kit; `Plan` holds rooms, corridors, flights on levels; `fill` solves pieces (per-room palette, `kit.seen`, bigger pieces merged in afterwards); `walk_check` walks real collision eroded as the navmesh is, from the first room to every square. `PlanTiles(kit, game)` leaves out pieces whose collision closes a drawn doorway, and stairs that don't walk. `generate`, `layout`, `vault`, `grow` are what the Kit tab calls (`/api/kit/layout`, `/vault`, `/grow`). `kitdress.py` surveys doors, lights and things per piece in the piece's frame (kept beside the kit index as dressing.json: delete it when its format changes); each room takes after one real cell chosen by purpose (`PURPOSE_TAGS`), `clear_ways` takes out what blocks the walk. Kits with no room pieces fall back to `filled`. Not used: gear-door room (an alcove that needs its own sunken pieces round it), `Rm2x` tall rooms, stairs inside rooms (`OffRmMidStairsDown`), metro and pipe kits (nothing closes a tunnel's end).
- Richer places (all in `kitplan.py`, measured by `tools/interior_bench.py`): `Galley` and `Pit` are tall rooms read from sections (`upper_slot` reads a side at a height; other kits' `Pit`s don't read complete yet), placed whole (`plan.placed`, its squares in `plan.air` if nothing stands there), with rooms standing open against the balconies (`plan.opens`) on both floors: under a railing the piece is open, so a room there is what seals it. `Planner.find_way`/`lay_way`/`join` route corridors between any two owners, stairs included; `add_loops` uses them, kept only if `fill` still solves. `stair_moves` kinds (`straight`, `long`, `back`, `turn`), each proven per kit in `ts.stair_kinds` by `_stairs_walk`. `SetPiece` is a room in one piece, joined exactly as a `kit.seen` join (off the grid by whatever that was), other exits plugged. `Walk.open_edges` finds floor ending on the void with no wall (walking alone never saw these); `walk_check` returns them as `edges` and `generate` rejects them. `_read_niche`: a kit's narrowest real corridor sets what counts as a way through (`utility`), and `_trust_game` takes the game's joins between its off-centre passages. `ONE_CLICK` is the other one-click places. `change_room`/`reroll_room`/`room_themes` (`/api/kit/room`, `/api/kit/themes`) work on `store['last']`; `drawn`/`plan_from_drawing` build a hand-drawn plan (`/api/kit/drawn`). `web/kitroom.js` is their UI, wrapping `kitTab` and `kitPut`.
- Furnishing (`kitdress.py`): `tags_of` matches whole words of an editor ID. A room takes after one real room (`real_rooms`: pieces open to each other, `survey.room`), not a whole place: `room_scores`, `_furnish` (then rooms like it, then any open floor, until it says what it's for), `_fits` keeps other rooms' furnishings out. `theme_scores` (a whole place) is what `pick` and the page's list use. `wreck_some` leaves a few rooms wrecked on purpose. `_not_a_showroom` caps things per room (`ONE_TO_A_ROOM`, what a real room usually has), `keep_fronts` clears doorways, `clear_ways` takes out only what's on a lost square; `_drop` takes what stood on it too (`dressing3.json`; tags are worked out afresh on load).
- Vault stories (`kitlife.py`): a vault is a shelter people went on living in. `live` lays each vault's story (`STORIES`, `plan.story`) room by room over what `kitdress` stood there: `SCENES` of the game's things by editor ID on free squares, `FINDS` to search. Stays a maze on purpose: the user wants vaults twisty, with rooms worth exploring. Vaults go down (`Spec.down`, `VAULT_STAIRS`): each wing starts down a flight, the reactor's deepest.
  POI: `secure` (after `clear_ways`) locks rooms `lockable` finds (every doorway has a door, `Item.link`, nothing beyond them) and some `plan.finds`, harder deeper; the office needs a key laid on a find elsewhere, the key a KEYM of the mod's own (`key_record`, first in the ops, named `$made`, which `project.apply` also resolves in a lock). `people` names the game places Populate learns from per story (`populate.plan` `like`/`skip`, `apply` `away`); `kits.js` `kitPeople` runs it after `navMake`.
  Scenes not `IN_THE_OPEN` go only on wall squares; `HUNG_AT` things hang at the game's height. `is_window` (a closed side with a sill, or a piece named for a window): `PlanTiles.window`, never on an 'x' side.
  Holes: `open_edges` counts a gap of `GAP_FALLS` or more between a floor's edge and the wall, with nothing within `DROP_SAFE` under it, as a hole (a corner piece whose floor stops short, a dead end narrower than what it closes); `walk_check` and SetPiece's final check look `EDGE_REACH` past the eroded walk, since a player squeezes past furniture.
- Compact plans: `Planner.attach_best` weighs every way of joining a room (`_weigh_room`, `COMPACT_*`) and tries the best in `fill` as it goes. `side_purposes` gives the rooms round a tall room what they're for (`o['dress']`). `tools/vault_measure.py` measures vaults as seen: outline, gaps, rooms that read as what they're for, repeats.
- MO2 loadouts (`loadout.py`, `web/loadouts.js`, Tools tab, `/api/tools/loadout`): an instance's ModOrganizer.ini, a profile's modlist.txt (highest priority first; `*` unmanaged), plugins.txt and loadorder.txt (a new profile has none: order goes by the files' dates, as the game's). A `Loadout` is the virtual folder worked out from the files (real Data, mods on, overwrite); `server.use_loadout` makes it what `load_game` loads and `GD.view` what files come through. Anything opening a plugin goes through `loadout.plugin_path`, a loose file through `GD.loose_path`, not `data_dir`. `loadout.py` only reads; while one is current `refuse_writes` stops everything that writes to the real game. `mod_needs` refuses a mod whose links name plugins not loaded. A patch is an ordinary new mod made in a loadout: records load from the winner (`recordio.load`, `src`), which `espwrite` makes a master. `mo2write.py` is the one place MO2 changes: Put in MO2 (`put_in_mo2`) makes a mod folder marked `madeByFOLab=true` in meta.ini, adds it to modlist.txt, plugins.txt and loadorder.txt with backups, refuses while MO2 runs (it rewrites the lists when it closes) and never touches a folder it didn't make. Test only on a separate profile. Started from MO2 (`loadout.under_mo2`: usvfs is hooked in; `running_setup` finds the profile by the plugins.txt MO2 shows it): MO2 is locked and running, so Put in MO2 writes only the folder (`switch_on`), and `playtest.launch` may start the game, whose child process gets the virtual folder. `add_to_run_list` adds FOLab beside MO2's Run button. Play here in a loadout (FOLab opened on its own): `server._put_in_setup`/`_put_test_in_setup` put the mod and a `FOLab Test` mod in the profile (`install_mod`'s `may_be_open`: MO2 may be open if the lists need no change), `playtest.launch_through_mo2` runs `ModOrganizer.exe -p profile run -e <title>`; tests replace `playtest._start`. `playtest.floor_near` puts you on a mod's own place's floor, wherever the view was. Started from MO2, Play here, Open in game and Give it to me go in for one run (`server._run_inside`, `mo2write.place_inside`): files written through the virtual Data (new ones land in overwrite, checked; the mod's own FOLab folder written in place; anything real Data or another mod has is never written through), `FOLab Play Here.esp` (not FOLab Test.esp, which real Data may hold), lines added to the profile's plugins.txt and taken out `RELEASE_AFTER` the game starts; files out at Open in game, quit and next start (`clean_inside`, noted in `mo2_inside.json` in FOLab's home; a file changed since stays). Tests swap `mo2write.VIRTUAL`.
- Mod conflicts (`conflicts.py`, `web/conflicts.js`, under `/api/tools/conflicts/`): a plugin against the active load order, read only. Headers first (`Index`: formid, type, offset, flags, parent, kept sorted in `cache/conflicts`, named by file size and date), then only copies of what it touches. A change is what differs from its base, the last copy among the files it's built on; it's lost if the winner doesn't say the same in that field (`lost_fields`: struct fields by `schema.py`, repeated subrecords as a bag, links through `recdiff.spelled`). NAVI is never a clash (the game merges it). Moves go through `loadorder.save`, only at a click; test with a fake Data and `LOCALAPPDATA`. The script's globals are `MCF`/`mcf*`, since comforts.js has `CF`/`cf*`.
- Quests and dialogue: `questrec.py` (QUST/DIAL/INFO as plain data and back, byte exact over every game record; `write_lines` puts each INFO in its DIAL's type-7 group, copying a game topic from the file that first has it with our quests added), `api_quests.py` (routes under /api/quest, /api/dlg; scripts compiled on save through `ModForms`; board, check), `web/quests.js`, `dialogue.js`, `questboard.js`. An INFO record keeps its topic in `rec['topic']` and its place in `rec['seq']`. Silent lines need no voice files (TRDT sound 0, words in NAM1). Conditions: `schema.condition_fields` reads CTDA parameters by function, so their links are keys and re-point; only conditions in records saved before this keep raw numbers.
- Library (`library.py`, `web/library.js`, hooks `/api/library/*`): `Index` over every mesh, texture and sound; thumbnails in
  cache/thumbs (`meshthumb.py` software-draws meshes, `dds.decode`). A mod's own files live in `projects/<mod> assets/`, seen through
  `GameData.overlay` first; Save copies them to `build/<plugin> assets/`, `install.py` puts them in Data with the plugin and lists them in
  `<plugin>.files.json` for taking out. `nifwrite.py` changes texture paths and nothing else (`py -3 app/nifwrite.py` re-proves every game mesh).
- Styles: `stylesurvey.py` reads every place once per game files (cache/style) for suggestions, palettes, sets; `web/stylepal.js`.
- Placed things: `refprops.py` is owner, lock, enable parent (op `props`, kept whole in the ref's change), `web/comforts.js` holds line up, Settle,
  groups (`projects/<mod> groups.json`) and the second window (BroadcastChannel, `?win=2`). Library, palette and comforts add to the page from their
  own files (nav button, Place section, menu entries, wrapping `drawSelected`, `select`, `post`): index.html only has their script tags.
- World tools (`web/worldtools.js` panel + map hooks, `web/worldtabs.js` tabs, `worldapi.py` every `/api/w/`): `worldrec.py` regions, zones, markers, patrols, encounter spots (its docstring: the layouts); what changes on a CELL is `project.cellinfo` {cell: {tag: key}} (op `cellinfo`), extras on a ref are in its change (`marker`, `zone`, `link`, `patrol_wait`; op `place` for refs naming each other). `roadgen.py` roads, `lodgen.py` distant ground only (written to `build/<mod> distant land/`, copied in by choice; its chunks rebuilt byte for byte in `tests/test_lodgen.py`; distant objects and trees: xLODGen).
- Game test (`gametest.py` plan, report, run; `gametestguard.py` isolation, all by paths; `gametestcheck.py` the checker's text; `web/gametest.js`, Tools tab): the game walks a place and writes `Data\FOLabGameTest\lines.txt`, raw numbers only; `make_report` judges. Run in the real game on one small place (7 Nov 2026): `docs/game-test-first-run.md` lists what real runs found and what's unproven, and any real run needs the user's go. The one real start is `launch_real` (needs the words from the page, refuses with `FOLAB_NV_INI` set); tests give `run_test` a fake launcher (`tests/fake_game.py`). A change to the checker's lines goes in `gametestcheck.RESULTS` too. `py -3 app/gametestcheck.py` rechecks its commands against the user's DLLs.
- Tests: `py -3 tests/run.py` (each test_*.py in a fresh FOLAB_HOME, against the game's files; never the real game).
  Run it before committing changes to the readers, writer, project or schema.
- Test server: launch config `folab-test` (port 8772, `FOLAB_HOME=%TEMP%\folab-test`) so tests never touch the
  user's own mods. Never test `install` against the real game: use a fake Data folder and `LOCALAPPDATA`.
- Outside cells as the game files them (`espwrite.as_the_game_files`, `tests/test_world_as_game.py`; measured over every
  world of the game): all LAND compressed (`plugintree.Rec.packed`), a world's persistent cell with a persistent group in
  its children, every grid cell with the has-water flag and XCLW (none to see: `espwrite.dry`, far under the lowest land),
  no empty children group. Earlier FOLab worlds (`trim_masters`) are brought into line on their next save. Done after a
  tester's report that FOLab worlds crash the GECK on loading cells (test 10). Tried in the GECK 11 Nov 2026: worlds written
  the old way (flat and real-map) and the new way all load and draw, so the crash is not reproduced and its cause unknown.
  A second tester's world (Sins of the Past, 16 Nov 2026: fine in FOLab and the game, the GECK crashed loading its cells)
  had every LAND uncompressed and 15 of its own REFRs held as nothing but a deleted mark (the GECK Extender's log: "Bad
  form ... could not be removed", then the crash). Every save now stores all LAND compressed, any plugin's, and leaves the
  plugin's own empty deleted refs out (`Writer._empty_deleted`); a master's ref deleted that way stays (Dead Money has 51).
  With test 17 he reported the GECK loading it, its exterior cells included (not seen by us in the GECK).
  Driving the GECK by computer use takes over the user's screen for minutes: ask first, or have them do it.
- New Vegas rules kept in the writer: game refs are never deleted (disabled + sunk to z -30000); form IDs in
  copied records are re-pointed to this plugin's master list.
- Scripts: `scriptc.py` compiles New Vegas script source to the game's bytes (`compile_script`, `compile_result` for
  INFO/QUST result scripts; forms come through `GameForms` or anything with its `find`/`find_edid`). Function table:
  `scriptfuncs.json`, made from the user's FalloutNV.exe by `tools/gen_scriptfuncs.py`. `tools/script_oracle.py` compares
  every script of the game with its shipped bytes; all match but the 19 out of step listed in `tests/test_scriptc.py`.
- Extender commands: `app/extfuncs.json` (xNVSE's and its plugins' commands: name, opcode, parameters, `expr` for those only xNVSE's
  expression compiler can write), made by `tools/gen_extfuncs.py` from the user's nvse_1_4.dll (opcodes by the order its start-up code adds
  them, checked against `ANCHORS` from real mods' compiled scripts), the plugin DLLs and nvse.log (plugin opcodes). `scriptc` compiles the
  plain ones as the game's; `scriptx.py` (a mixin of its compiler; its docstring is the byte format) compiles xNVSE's own expressions:
  let and bare assignment, if eval, while/foreach/loop, call, string_var/array_var, begin Function. Not: a function inside a line
  (lambda), other extenders' commands. `tools/script_oracle.py --plugin X.esp` compares a mod's scripts with its own bytes (JSawyer
  Ultimate: 48 of 53; of the rest 3 are lambdas, 1 an older xNVSE's function header, 1 a plugin not installed). Shell heredocs eat
  backslashes: patch these files with Edit or a script written by Write.
- Scripts page (`web/scripts.js` + `scriptshelp.js`, `scriptattach.js`; `api_scripts.py`): a script is an SCPT record in `project.records`, only ever
  written with bytes the compiler gave for its source; `ModForms` lays the mod's forms over `GameForms`, `set_script` puts SCRI in the game's place. A compile
  problem comes back as `problem`, not `error` (`post()` throws on that). Starters in `scripttemplates.py`, notes on commands in `scriptdocs.py`.
- GECK parity (help doc `geck`): the GECK's menus and windows were read out of Geck.exe and matched against FOLab. `schema._MORE` is the
  27 kinds its World, Gameplay and Character menus edit (game settings by `setting_kind`: the name's first letter says what DATA holds;
  a tag a type lists as None is left raw whatever COMMON says). Still raw there: WTHR INAM, IMAD curves, WATR DNAM, EFSH/CSNO/LSCT DATA,
  SCOL placements, BPTD BPND, RGDL. Not started: face textures, distant objects, local maps, text export, cover edges, rooms and portals.
- Records: `schema.py` layouts (checked against every record of each type: run `checkall`; a layout only counts
  if every subrecord fits and encodes back byte for byte), `recordio.py` (a mod's records with links as keys),
  `browse.py` (Browse page data; its index builds in the background, ~20 s). Subrecords no layout reads stay raw in a kept record, in its source file's numbering; the writer re-points their links with `formlinks.py`, which also reads the types not in `schema.TYPES`.
  Everything else raw is hash/geometry blobs (MODT, FGGS, NIFT, KFFZ, DMDT) or compiled script text.

## Finding the game

`gamedata.find_data_dir`: `FOLAB_NV_DATA` overrides the Data folder; else the folder the user chose (`game_data` in
folab_settings.json), else Steam wherever the registry says it is and every library it lists, else where the game's
launcher or GOG wrote it was installed. Nowhere: `server.NO_GAME`, and only `web/findgame.html` answers (it asks for
the folder, `/api/game/folder`) until the game loads. It used to crash on any PC with Steam off C: (a tester, test 10).
Test with `gamedata._registry` and `_STEAM_USUAL` replaced (`tests/test_findgame.py`).
Never read from `steamapps\downloading`: open files there make Steam's install fail with "disk write error".
