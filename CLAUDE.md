# FOLab

A New Vegas editor in the spirit of Morrowind Workshop (`C:\Users\AMD RYZEN\Desktop\Morrowind Workshop`), which is
the model for style, UI and approach. Python, standard library first, code in `app/`.

## Ground rules

- **Game files are read-only.** Nothing ever writes into the game's `Data` folder; plugins we make are written
  elsewhere and copied in by the user's choice.
- **fnv_decomp is reference only.** `C:\Users\AMD RYZEN\Documents\GitHub\fnv_decomp` (no licence granted). Read it to
  learn how the game works; never copy its code, comments or names into this project. Write our own from understanding.
- **Engine apart from game.** Keep anything that depends on how the game is run (original game vs a possible OpenMW
  or source-port New Vegas: launching, config, scripts, navmesh) behind one small interface.
- Morrowind Workshop stays untouched; copy ideas or code from it, never edit it from here.

## Layout

- Readers: `tes4.py` (plugins), `bsa.py` (archives), `nif.py` (meshes), `gamedata.py` (the game as one thing).
- Mod: `project.py` (changes as JSON in `projects/`, undo/redo), `espwrite.py` (writes `build/<mod>.esp` by laying
  the changes over a `plugintree.py` tree: empty for a new mod, the plugin itself for an opened one, so untouched
  records keep their exact bytes), `adopt.py` (open a plugin as your mod: a copy in `projects/<name> source/`,
  loaded on top of the game, any mods it needs under it; it gains masters when edits need them: `masterlist.py` re-points every link), `install.py` (copies into
  Data + plugins.txt, backups in `backups/`).
- Editor: `server.py` (port 8771) + `web/index.html`, `web/app.js` (panels, edits), `web/world.js` (3D view).
- Building: places of the mod's own are '+ID' keys in both `records` (their CELL) and `cells`; door links are a
  ref change `tel` (XTEL, made persistent; arrival points picked in world.js `arrivalFor`). Snap pieces: kit
  pieces (same mesh folder, same turn) join on 128-unit steps, else box edges (`snapOffset`). Prefabs are JSON in
  `prefabs/` (bases by key, places from the group's middle and lowest point).
- Play: `playtest.py` starts FalloutNV.exe; Play here writes `FOLab Test.esp` (marker + start-enabled quest + one
  hand-compiled script, bytes checked against the game's own scripts; a new quest ID each time). Never call
  `/api/play` in tests: it starts the user's real game.
- xNVSE: FOLab fetches nothing from the internet (Nexus's rule on tools that download): My mod links to xNVSE's page and `nvse.py` installs from the user's Downloads folder (an archive counts if nvse_1_4.dll is inside), unpacking into `downloads/`; its .dll/.exe go
  beside FalloutNV.exe (its config in Data\NVSE), records what it put in for Take out. The game starts through
  nvse_loader.exe when present (setting `launch_via`), else steam://rungameid/22380; never FalloutNV.exe directly
  (Steam's load error 5:0000065434).
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
  added to that plugin, then the plugin opened as the mod (undo starts afresh) so the world is game data to edit.
- Auto-paint (`autopaint.py`): textures by slope band learnt from the game's land nearby; land shaping uses it.
- Real maps (help doc `real-maps`; FOLab fetches none of these files): `elevation.py` reads GeoTIFF/.hgt/PNG into a `Raster` (pixel centres; NaN for no data); `mapscale.py` is the scale (`Plan`: compress, exag, base at z 0, limits measured from the game; `heights` makes one `Grid` of land points for the whole world, whole 8-unit steps, slopes VHGT can hold, so cells meet by construction); `mapworld.py` paints by slope and hands `worldgen.add_world` a callback per cell (compressed LAND in the plugin, never `project.land`: a world of thousands of cells would not fit in JSON). `api_maps.py` (every `/api/maps/`, outside the server's lock, a job at a time; files copied to `maps/` under FOLab's home), `web/mapland.js` (the panel over the flat map, through `lsDraw`/`lsMouse`, and the World tools tab Real map). The way back: the mod kept in `projects/<mod> before map/`, `/api/undo` uses it when nothing else is left to undo and the mod has no changes. `projects/<mod> maps/` holds `made.json` (where each world came from: `osmplace.Georef` needs it) and `layers.json` (marker layer): in a folder, as every .json directly in `projects/` is listed as a mod. `osm.py` reads .osm XML; `osmplace.py` lays it as ops, one Undo (`roadgen.lay_line`, `landshape.shape_all` per shape, pads through `put_point`). `landcover.py`: a class file over the heights, textures through `Painter.cover` as the world is made, scatter as ops after.
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
- Navmesh: `navbuild.py` keeps a place's mesh in `project.navmesh` (op `navmesh`; `others` for a place's further meshes), `espwrite` writes NAVM + NAVI + each door's XNDP, Kit tab makes it. Outside, `navbuild.Area`/`generate_area` joins cells to whatever is round them; neighbours are whole copies (`copy`, same triangles, links changed). Meshes that had to go become stubs (`navmesh.stub_mesh`). `navedit.py`: by hand, `web/navtool.js`. `navmesh.py` reads/writes NAVM and NAVI byte for byte and holds the rules (its docstring: what a
  plugin must do), `navgen.py` generates a cell's mesh, `hkshape.py` reads collision shapes. Run `py -3 app/navmesh.py`
  to recheck every game record. Collision triangle soups wind either way (they came from strips): don't trust facing.
- Kits (`kitindex.py`): building pieces per mesh folder on each kit's grid; each side's section (cut just inside it from the
  mesh) says if it's a way through and what it meets; `kit.seen` is every join the game built. `Tileset` + `build_area` fill any
  squares with every side agreeing (one-square, one-level pieces; `kitplan.py` adds plans, stairs and big pieces); `can_walk_out` checks a
  layout from the real meshes. Editor: `web/kits.js` (Joins under Selected, the Kit tab), `/api/kits`, `/api/kit/piece`, `/api/kit/layout`.
- Tools page (`web/tools.js`, one hook `/api/tools/` to `modtools.py`): `health.py`/`health.js` (reads the plugin itself, so any plugin; fixes are ops), `loadorder.py` (plugins.txt + file dates, backup first; test only with a fake Data and `LOCALAPPDATA`), `changes.py`/`mychanges.js`, `release.py` (zip into `releases/`, own files from Data or `projects/<name> files/`), `merge.py`/`mergepage.js` (grafts a plugin; the result becomes the mod, like a new world). `formlinks.py` is every form link's byte position, raw parts included; `py -3 app/formlinks.py` rechecks it against every game record. Op `drop`: an opened plugin's record left out on save (`project.drop`).
- Generated places: `kitplan.py` plans first. A side reads as a word (F full, A along a wall, P passage, . closed), a square's four words say what it is in any kit; `Plan` holds rooms, corridors, flights on levels; `fill` solves pieces (per-room palette, `kit.seen`, bigger pieces merged in afterwards); `walk_check` walks real collision eroded as the navmesh is, from the first room to every square. `PlanTiles(kit, game)` leaves out pieces whose collision closes a drawn doorway, and stairs that don't walk. `generate`, `layout`, `vault`, `grow` are what the Kit tab calls (`/api/kit/layout`, `/vault`, `/grow`). `kitdress.py` surveys doors, lights and things per piece in the piece's frame (kept beside the kit index as dressing.json: delete it when its format changes); each room takes after one real cell chosen by purpose (`PURPOSE_TAGS`), `clear_ways` takes out what blocks the walk. Kits with no room pieces fall back to `filled`. Not used: gear-door room (an alcove that needs its own sunken pieces round it), `Rm2x` tall rooms, stairs inside rooms (`OffRmMidStairsDown`), metro and pipe kits (nothing closes a tunnel's end).
- Richer places (all in `kitplan.py`, measured by `tools/interior_bench.py`): `Galley` and `Pit` are tall rooms read from sections (`upper_slot` reads a side at a height; other kits' `Pit`s don't read complete yet), placed whole (`plan.placed`, its squares in `plan.air` if nothing stands there), with rooms standing open against the balconies (`plan.opens`) on both floors: under a railing the piece is open, so a room there is what seals it. `Planner.find_way`/`lay_way`/`join` route corridors between any two owners, stairs included; `add_loops` uses them, kept only if `fill` still solves. `stair_moves` kinds (`straight`, `long`, `back`, `turn`), each proven per kit in `ts.stair_kinds` by `_stairs_walk`. `SetPiece` is a room in one piece, joined exactly as a `kit.seen` join (off the grid by whatever that was), other exits plugged. `Walk.open_edges` finds floor ending on the void with no wall (walking alone never saw these); `walk_check` returns them as `edges` and `generate` rejects them. `_read_niche`: a kit's narrowest real corridor sets what counts as a way through (`utility`), and `_trust_game` takes the game's joins between its off-centre passages. `ONE_CLICK` is the other one-click places. `change_room`/`reroll_room`/`room_themes` (`/api/kit/room`, `/api/kit/themes`) work on `store['last']`; `drawn`/`plan_from_drawing` build a hand-drawn plan (`/api/kit/drawn`). `web/kitroom.js` is their UI, wrapping `kitTab` and `kitPut`.
- Furnishing (`kitdress.py`): `tags_of` matches whole words of an editor ID; `theme_scores` judges a real place as a whole room; `_not_a_showroom` caps one big thing per room; `keep_fronts` clears doorways (`dressing2.json`; tags are worked out afresh on load).
- MO2 loadouts (`loadout.py`, `web/loadouts.js`, Tools tab, `/api/tools/loadout`): an instance's ModOrganizer.ini, a profile's modlist.txt (highest priority first; `*` unmanaged), plugins.txt and loadorder.txt (a new profile has none: order goes by the files' dates, as the game's). A `Loadout` is the virtual folder worked out from the files (real Data, mods on, overwrite); `server.use_loadout` makes it what `load_game` loads and `GD.view` what files come through. Anything opening a plugin goes through `loadout.plugin_path`, a loose file through `GD.loose_path`, not `data_dir`. `loadout.py` only reads; while one is current `refuse_writes` stops everything that writes to the real game. `mod_needs` refuses a mod whose links name plugins not loaded. A patch is an ordinary new mod made in a loadout: records load from the winner (`recordio.load`, `src`), which `espwrite` makes a master. `mo2write.py` is the one place MO2 changes: Put in MO2 (`put_in_mo2`) makes a mod folder marked `madeByFOLab=true` in meta.ini, adds it to modlist.txt, plugins.txt and loadorder.txt with backups, refuses while MO2 runs (it rewrites the lists when it closes) and never touches a folder it didn't make. Test only on a separate profile. Started from MO2 (`loadout.under_mo2`: usvfs is hooked in; `running_setup` finds the profile by the plugins.txt MO2 shows it): MO2 is locked and running, so Put in MO2 writes only the folder (`switch_on`), and `playtest.launch` may start the game, whose child process gets the virtual folder. `add_to_run_list` adds FOLab beside MO2's Run button.
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
- New Vegas rules kept in the writer: game refs are never deleted (disabled + sunk to z -30000); form IDs in
  copied records are re-pointed to this plugin's master list.
- Scripts: `scriptc.py` compiles New Vegas script source to the game's bytes (`compile_script`, `compile_result` for
  INFO/QUST result scripts; forms come through `GameForms` or anything with its `find`/`find_edid`). Function table:
  `scriptfuncs.json`, made from the user's FalloutNV.exe by `tools/gen_scriptfuncs.py`. `tools/script_oracle.py` compares
  every script of the game with its shipped bytes; all match but the 19 out of step listed in `tests/test_scriptc.py`.
- Scripts page (`web/scripts.js` + `scriptshelp.js`, `scriptattach.js`; `api_scripts.py`): a script is an SCPT record in `project.records`, only ever
  written with bytes the compiler gave for its source; `ModForms` lays the mod's forms over `GameForms`, `set_script` puts SCRI in the game's place. A compile
  problem comes back as `problem`, not `error` (`post()` throws on that). Starters in `scripttemplates.py`, notes on commands in `scriptdocs.py`.
- Records: `schema.py` layouts (checked against every record of each type: run `checkall`; a layout only counts
  if every subrecord fits and encodes back byte for byte), `recordio.py` (a mod's records with links as keys),
  `browse.py` (Browse page data; its index builds in the background, ~20 s). Subrecords no layout reads stay raw in a kept record, in its source file's numbering; the writer re-points their links with `formlinks.py`, which also reads the types not in `schema.TYPES`.
  Everything else raw is hash/geometry blobs (MODT, FGGS, NIFT, KFFZ, DMDT) or compiled script text.

## Finding the game

`FOLAB_NV_DATA` overrides the Data folder; otherwise Steam's library folders are searched for app 22380.
Never read from `steamapps\downloading`: open files there make Steam's install fail with "disk write error".
