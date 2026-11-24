# FOLab 0.6.0 test 20

A test build of FOLab, an editor for Fallout: New Vegas. Unzip it anywhere and run `FOLab.exe`. Nothing is put into
your game until you choose to.

**Download:** `FOLab-0.6.0-test20-portable.zip`
SHA-256: `8a4cac7ad586b88895609c7f30ad72ccc53c8c7964cbb9366990372eec386ea4`

Since test 19 FOLab works more like any program: you open a mod, change it, and nothing is written until you save.
Big mods save and build much faster, and you can now set a worldspace's water level.

## What's new

### Open, Save, Save As
- **Changes stay unsaved until you press Save** (Ctrl+S). The top shows `Your mod *` and **● Not saved (3 changes)**,
  then **✓ Saved 14:32**.
- **File ▸ Open…** (Ctrl+O), **Save As…** (a copy under a new name; its models and pictures are shared with the
  original), **Throw away unsaved changes…**. Opening another mod asks Save, Don't save or Cancel.
- **Nothing is lost if FOLab closes first:** unsaved changes wait beside the mod, and FOLab offers them back next time.
- **Put in game**, **Open in game** and **Play here** ask to save first.

### Editing you can see happen
- Every action says at once what it is doing and when it is done ("⏳ Removing…", "✓ Removed · Ctrl+Z puts it back").
- Clicking the 3D view takes the keyboard back from any text box, so Delete and the arrow keys work; a key typed into a
  box by mistake says so.
- **Arrow keys nudge** what's selected by 1 unit (Shift: 16), Page Up/Down lift and lower it, Ctrl+←/→ turn it.
- Move step, turn step, lining up with pieces and dropping onto what's below are **off** until you turn them on, so
  nothing jumps by itself.
- **How to edit your map**, first in Help: the everyday steps in one page.

### Worlds
- **A worldspace's water level** (the GECK's Default Water Height): Ground panel ▸ **Water · the whole world**. Cells
  that take their water from the world follow it, cells with a level of their own keep theirs, and the far water moves
  with it. One Undo.
- A worldspace's water, far water, climate, image space and music are editable in Browse.

### Faster with big mods
- Saving writes only what changed, and building the plugin reuses what hasn't: on a very large mod an edit went from
  12 s to 0.3 s and a build from 71 s to a few seconds.
- **Put in game** goes to every place you tick (the game itself, MO2, or each copy of nv-rs) and says where your mod is
  current.

### Doors, buildings and checks
- **Doors made to fit their doorways**, pair doors that meet in the middle, and doors placed where you can reach them.
- **Arrivals clear of what stands there:** Health finds doors that put you inside a wall or off the navmesh, and stops
  an install until they're fixed.
- **Floating buildings:** Health finds daylight under a building's walls, and a fix raises the ground to it.
- Doors your mod adds keep their navmesh links.
- **A character's face from your save:** read the player's face from a save game and put it into a character.
- **Birds** made from the game's raven: perch, look round and fly off when you come near.

## Known
- A test build: try it on a copy of a mod you care about.
- Voice models aren't included: you download them yourself.
- Only Windows.
