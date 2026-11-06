# The Library, styles and the 3D view's comforts

## The Library page

**Library** at the top shows every mesh, texture and sound the game can load, from its archives and its Data folder.

- **Kinds** on the left, with the folders of the one you're in. Click a folder tile to go in; the line above the grid takes you back up.
- **Search** looks anywhere in a file's name and folders: `vault door`, `pistol fire`. File names that match come first.
- Click anything to see it on the right: a mesh turns in 3D, a texture shows as a picture, a sound plays.
- The small pictures are made the first time they're needed and kept in FOLab's `cache\thumbs` folder, so the second look is instant.

For a mesh you also see its textures and the things drawn with it. Click a thing to place it; click a texture to go to it.

## Your own files

**＋ Bring in…**, or drop files on the page, takes files from anywhere on your computer:

| | |
|---|---|
| Meshes | `.nif` from New Vegas or Fallout 3's format (20.2.0.7). Other versions are refused, with a message |
| Pictures | `.dds` as it is; `.png`, `.tga` and `.bmp` become a plain 32-bit `.dds` with all its smaller copies (bigger than a compressed one: compress it yourself if size matters) |
| Sounds | `.wav`, `.ogg`, `.mp3`, kept and played here. Making a sound record from one isn't there yet |

Bring a mesh in **together with its pictures** and it's pointed at them by file name. If it names a picture that's neither brought in nor in the game, you're told: the game would draw it purple.

They're kept with your mod (`projects\<mod> assets`), under `meshes\folab\<mod>` and `textures\folab\<mod>`, so they can't land on a game file. **Save** copies them beside the plugin (`build\<mod> assets`), **Put in game** puts them in Data with the plugin, and **Take out of game** takes out exactly what it put in. Hand someone your mod: the plugin and that folder.

**Make a thing from it** turns a mesh into a record of your own in one click: a static, an item, a container or an activator. Its bounds come from the mesh. A picture can become a texture set record.

A mesh with no collision in it can be walked through in game. FOLab doesn't make collision: that has to be in the `.nif` you bring.

## Retexturing

Right-click a thing in 3D, **Looks › Retexture…** (or **🎨 Retexture…** under Selected, or in the Library). Pick one of its textures, then a picture to put in its place: your own show first, and typing searches the game's. FOLab makes a copy of the mesh with only those paths changed, a record of your own drawn with it, and swaps the one you clicked for it, all as one Undo. Other copies of that thing in the game stay as they are.

## Suggested for this place, and the Style palette

**Place** now lists what fits here: FOLab finds the game's places most like this one, by what they hold, and shows what they have that this one doesn't. ↻ looks again after you've changed things. Outside, it compares the cells round the camera with the rest of that kind of land.

**🎨 Style palette…** sorts the game's things by style: Casino, Vault, Office, Shacks and scrap, The Mojave, Zion… A thing is in a style when that style's places hold it much more often than places in general; **staple** marks those in nearly half of them or more. Rest the mouse on one to see what the game stands with it. Click, then click where it goes, or drag it into the view.

**Sets** are what the game puts together: a counter with its stools and ashtray, a table with its chairs. Each is one real arrangement from a game place, set down whole as one Undo.

The first time, FOLab reads every place in the game (some seconds, in the background) and keeps the result in `cache\style`.

## Comforts in the 3D view

**Line them up** (select several; on the right-click menu and under Selected): sides in line, bottoms or tops level, middles in line, space evenly.

**🪂 Settle** (Shift+End): what's selected falls and comes to rest on what's under it, lowest first so a stack lands on itself. Small things lean with a slope and tip off an edge when their middle is over nothing. This is a good guess from the meshes, not a physics simulation: nothing rolls or pushes anything else. **Drop down** (End) is still there for a plain drop.

**Groups** (Ctrl+G; Ctrl+Shift+G to ungroup): a click on one selects them all, Ctrl+click just that one. Kept with the mod.

**Owner, lock, what enables it** (under Selected, or the right-click menu):

- **Belongs to**: a character or faction; taking it counts as stealing. A faction can have a rank from which it's free to use.
- **Lock** (doors, containers, terminals): how hard, the key, and whether it gets harder with the player's level.
- **Enabled by**: press *Pick it in the view*, then click the thing. This one shows and hides with it, or the opposite. FOLab makes that other thing persistent, as the game needs.
- **Starts switched off**: until a script or its parent brings it.

**Hide every…** (right-click, View): hides all of a kind for now. The View tab has every kind, with locks.

**Scale them…** resizes a group round its middle. **Select it with everything on it** takes a table and what's on it. **Where it's used** opens its record.

**↗ Second window** opens this place in another window, looking where you look now. Both show the same mod and each sees what the other changes; Undo is shared too.
