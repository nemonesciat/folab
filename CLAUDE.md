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
  loaded on top of the game; its masters are kept as they are and can't grow yet), `install.py` (copies into
  Data + plugins.txt, backups in `backups/`).
- Editor: `server.py` (port 8771) + `web/index.html`, `web/app.js` (panels, edits), `web/world.js` (3D view).
- Building: places of the mod's own are '+ID' keys in both `records` (their CELL) and `cells`; door links are a
  ref change `tel` (XTEL, made persistent; arrival points picked in world.js `arrivalFor`). Snap pieces: kit
  pieces (same mesh folder, same turn) join on 128-unit steps, else box edges (`snapOffset`). Prefabs are JSON in
  `prefabs/` (bases by key, places from the group's middle and lowest point).
- Play: `playtest.py` starts FalloutNV.exe; Play here writes `FOLab Test.esp` (marker + start-enabled quest + one
  hand-compiled script, bytes checked against the game's own scripts; a new quest ID each time). Never call
  `/api/play` in tests: it starts the user's real game.
- xNVSE: `nvse.py` downloads only from github.com/xNVSE/NVSE releases into `downloads/`, installs its .dll/.exe
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
- Packaging (`packaging/`): `build.py` makes out/FOLab (FOLab.exe + its own Python + app) and a portable zip;
  FOLab.exe (`launcher.cs`, after MWWS's) runs `python\pythonw app\server.py --no-browser`, finds it by
  `folab_running.json`, opens an Edge app window titled "FOLab", quits it with POST /api/quit (X-FOLab-Quit).
  `brand.py` draws the logo/icon (wrench F, gear O, LAB) into app/web/vendor. Themes: `web/theme.js` (CSS variables).
- Game settings: `gameini.py` edits Documents\My Games\FalloutNV\Fallout.ini + FalloutPrefs.ini line by line (backup
  first, read-only kept, never while the game runs; `FOLAB_NV_INI` points it elsewhere, which tests always do).
  Borderless is FOLab's own: windowed at the screen's size, frame taken off after FOLab starts the game.
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
- Records: `schema.py` layouts (checked against every record of each type: run `checkall`; a layout only counts
  if every subrecord fits and encodes back byte for byte), `recordio.py` (a mod's records with links as keys),
  `browse.py` (Browse page data; its index builds in the background, ~20 s). Known limit: subrecords no layout
  reads are kept raw in their source file's numbering, so links inside them are only right for FalloutNV.esm
  records (and a DLC that ends up at the same master index). Add layouts (e.g. WEAP DNAM) to close it.

## Finding the game

`FOLAB_NV_DATA` overrides the Data folder; otherwise Steam's library folders are searched for app 22380.
Never read from `steamapps\downloading`: open files there make Steam's install fail with "disk write error".
