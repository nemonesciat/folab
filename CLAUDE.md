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
- Mod: `project.py` (changes as JSON in `projects/`, undo/redo), `espwrite.py` (writes `build/<mod>.esp`),
  `install.py` (copies into Data + plugins.txt, backups in `backups/`).
- Editor: `server.py` (port 8771) + `web/index.html`, `web/app.js` (panels, edits), `web/world.js` (3D view).
- Test server: launch config `folab-test` (port 8772, `FOLAB_HOME=%TEMP%\folab-test`) so tests never touch the
  user's own mods. Never test `install` against the real game: use a fake Data folder and `LOCALAPPDATA`.
- New Vegas rules kept in the writer: game refs are never deleted (disabled + sunk to z -30000); form IDs in
  copied records are re-pointed to this plugin's master list.

## Finding the game

`FOLAB_NV_DATA` overrides the Data folder; otherwise Steam's library folders are searched for app 22380.
Never read from `steamapps\downloading`: open files there make Steam's install fail with "disk write error".
