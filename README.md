# FOLab

A Fallout: New Vegas editor that runs in your browser. Change the game's places, land and items in 3D and on a map,
try it in the game with one click, and save it as a plugin (.esp) the game loads like any other mod.

**This is a test version.** Thank you for trying it. Please report what goes wrong (Help → Report a problem copies
what's needed).

## What it does

- **Places**: every interior and the worldspaces outside, in 3D (fly with WASD) or on a flat map. Move, turn, size,
  add, remove and swap things; link doors; prefabs; snap building pieces together.
- **The land**: raise, lower, smooth, flatten, paint and tint the ground; scatter plants, rocks and trees the way the
  game does round there; set water; shape many cells at once from ridges, valleys, plateaus, lakes and rivers drawn on
  the map (painted by slope); height maps out to PNG and back; worldspaces of your own.
- **Items and records**: weapons, apparel, aid, ammo… in plain fields, inventories and levelled lists, models with a
  3D preview; every record of the game in Browse.
- **Building**: generate a vault or another interior from the game's own kit pieces, with planned rooms, corridors,
  stairs, doors, lights and furnishing; grow a place from any wall; navmeshes inside and out, made or edited by hand.
- **Characters and quests**: people, creatures, AI packages and factions in plain fields; fill a place with Populate;
  quests, conversations and a board of how a quest moves on.
- **Scripts**: read, write and compile the game's script language, with errors at their line and starters to build on.
- **The world**: regions, map markers, encounter zones, roads and distant ground.
- **Library and tools**: every mesh, texture and sound, with your own files and retexturing; a health check, load order,
  a list of your changes, merging plugins, and a zip ready to share.
- **Play**: Open in game, Play here (arrive where the view looks), Give it to me in game; the game's own settings
  (resolution, borderless, field of view…).

## Mod Organizer 2

FOLab can work inside an MO2 profile, so your mods are what you edit against. **Tools → MO2 loadout** finds your New Vegas
instances and shows each profile's mods and plugins.

- **Work in this loadout**: the whole lab uses that profile's plugins in its order, and each mod's files. MO2's files aren't changed.
- **New patch**: a mod of your own that loads last, built on whichever mod wins for each thing you edit. The mods it changes stay as they are.
- **Put in MO2**: adds your mod to the profile as a mod folder of its own, switched on. MO2 must be closed, and a copy of its lists is kept.
- **Start FOLab from MO2**: **Add FOLab to MO2's list**, then choose it beside MO2's Run button. FOLab opens in the profile that's on,
  and **Open in game** starts the game with your mods. MO2 is locked meanwhile, so Put in MO2 only saves the folder: close FOLab,
  press Refresh in MO2 and tick your mod in both panes.

While you're in a loadout, Play here, Give it to me, the load order page's saving, xNVSE and Test in game are switched off. This is
new and has only been tried on a small setup. Big mod lists may take a while to load.

## What you need

- **Fallout: New Vegas** from Steam (FOLab finds it in your Steam libraries on any drive, and asks you for the game's
  folder if it can't. A GOG copy is found too, but starting the game from FOLab is only tried with Steam's).
- With the **portable download** (FOLab.exe), nothing else: Python comes with it. From the source: **Python 3.10 or newer** for Windows, from [python.org](https://www.python.org/downloads/) (tick "Add to PATH" and
  the "py launcher"). Nothing else to install.
- For Play here and Give it to me in game: **xNVSE** (download it from its page and FOLab installs it from your Downloads folder) and
  **JIP LN NVSE** (from its Nexus page).

## Starting it

Double-click **FOLab.exe** (the portable download: unzip it somewhere you can save files, such as Documents or the
desktop). FOLab reads the game (about ten seconds) and opens in its own window, with an icon by the clock to open it
again, see its log, or quit. Closing its window closes FOLab. Your mods and settings are kept in that folder.

From the source: double-click **Start FOLab.bat**; FOLab opens in your browser at http://127.0.0.1:8771/ (keep the black
window open while you work). To make the portable download yourself: `py -3 packaging\build.py`.

The first time, a Getting started guide opens. Help (top right) has the rest.

## Your game is safe

FOLab never changes the game's own files. Your mod lives in FOLab's `projects` folder and is written to `build`. Only
**Put in game** (or Play) copies the plugin into the game's Data folder and switches it on, keeping copies of anything
it replaces in `backups`; **Take it out of the game** removes it. The Game page edits your settings files only when you
press Save, keeping a copy first.

## Reporting a problem

Help → **Report a problem** copies FOLab's version, the game's files, your mod's state and the last errors. Paste it
with a few words on what you did (and a screenshot if you can). The full log is `logs\folab.log`.

## For developers

Python standard library only, no build step. `app/` holds the server and readers (`server.py`, `tes4.py`, `nif.py`,
`espwrite.py`…) and `app/web/` the page. Tests: `py -3 tests/run.py` (they use the game's files and never touch your
game or mods). `CLAUDE.md` has the layout and the rules kept.
