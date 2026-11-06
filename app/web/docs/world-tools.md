# World tools: navmesh, regions, markers, zones, roads

*What's marked and painted on the map outside: where characters walk, the weather and sounds, the places on the Pip-Boy, how tough things are, roads, patrols and distant land.*

Open a worldspace from **Outside**, then press **🧭 World tools**. The map opens with a panel of tabs. Each drag or click is one Undo.

Nothing here has been tried in the running game yet. The files are checked against the game's own, but the section at the end lists what to try and look for.

## Navmesh

Characters find their way on the navmesh. Outside, each cell's mesh joins its neighbours.

- Drag on the map to mark cells (**Ctrl** takes away), then **Make for marked**. It takes about 6 seconds a cell, in the background.
- **Mark what's out of date** marks what needs doing again. The colours on the map:

| Colour | Means |
|---|---|
| Green | Made here, up to date. |
| Amber | Made here, but something moved or the ground changed. Make it again. |
| Red | The ground changed under the game's mesh, which no longer fits. |
| Blue | The game's mesh, its links changed to meet yours. It goes in your mod too. |

- After **Shape the land**, and after a road that settles the ground, FOLab offers to make new meshes for those cells.
- **Remove from marked** puts the game's mesh back and puts the neighbours right.
- A new mesh is usually bigger than the game's own (a few hundred to about a thousand triangles a cell, against about 160 in the game's). That's fine for the land you've changed; don't redo the whole Mojave.
- A cell or place with several game meshes keeps the first form for the new mesh. The others are retired: one triangle each, deep under the ground, because the game has no way of deleting a mesh.

Inside, it's still in the **Kit** tab.

### By hand, in 3D

**✎ Edit by hand in 3D** (or the same button in the Kit tab, inside) shows the mesh over the world.

| Do this | To |
|---|---|
| Click a corner or triangle | Pick it. **Shift** adds. |
| Drag a corner | Move it. **Alt** moves it up and down. A corner on an edge joined to the next mesh only moves up and down. |
| **Edges**, then click | Pick edges, for **Join** and **Cut**. |
| **Join** | Close edges of one mesh weld together. Edges further apart, or at different heights, get a ledge link. |
| **Add** | Click three corners or spots. |
| **Delete**, or the Delete key | Takes the picked triangles away. Doors on them move to the nearest triangle left. |
| **★ Preferred**, **≈ Water**, **▣ Cover** | Mark the picked triangles. Click again to clear. |

FOLab checks the mesh after each change and refuses anything that would break it, saying why. Generating a cell again replaces what you did by hand there.

## Regions

A region gives its cells weather, background sounds and a list of objects.

- **＋ New region** or pick one, then drag on the map (**Ctrl** takes away). A cell can be in several regions.
- **Weather**: at most 8, each with a chance. **Sounds**: each with a chance. **Objects**: at most 13; **Learn from the land here** fills the list from what the game placed nearby.
- The **Scatter** brush in **Ground** then offers **This region's objects** in cells of that region.

Regions don't scatter things by themselves in game: objects only appear where you scatter them.

## Map markers

Fill in a name and type, then click the map. The marker goes in the world's always-loaded cell, as the game's do. **Known from the start** shows it on the Pip-Boy straight away; otherwise it appears when found. A world of your own has no Pip-Boy map picture: markers show on a blank map.

## Encounter zones

**＋ New zone**, set the **lowest level**, whether what's killed stays dead, and an owner, then drag on the map. **The game's zones have only a lowest level**: there's no highest level in its files, so a level range can't be set.

## A cell's details

The **Cell** tab: click a cell for its music, lighting template, water, owner, zone, echo and image space. Inside, the same fields are under **This place** in the Kit tab, with the place's name, its own light colours and fog.

## Roads and spots

- **🛣 Road**: click the start and the end. The game's own road pieces go between them, on the gentlest dry way over the ground, up to about 15 cells at a time. **Settle the ground** beds it in. Curves are straight pieces that overlap a little, so sharp bends show.
- **🚶 Patrol**: pick who walks it, click the points. They join in a ring. The walker is a copy of that character or creature with a patrol of its own, so the original isn't changed.
- **⚔ Encounter spot**: pick who, how many and a zone, then click. Those marked *varies* take their looks from a leveled list. The game's own cells hold no leveled lists directly, so this is what it does too.

## Far land

Distant land is what shows beyond the loaded cells.

| | |
|---|---|
| **Distant ground and its colours** | **FOLab makes these.** For a new world, every chunk. For a game world, only the chunks over land you changed. |
| **Distant buildings and trees** | **FOLab doesn't make these. Use xLODGen** (a free tool) if you want them. |

**Make distant land** writes to a folder of its own beside your plugin. **Put in game** copies it into Data, keeping anything it replaces; **Take out** removes exactly that. Make it again after changing the land.

## In the game: what to try

Nothing above has been proven in the running game, so try these:

1. **Outdoor navmesh**: make two neighbouring cells in the Mojave, put in game, `coc` there, and make an NPC walk across the border (`tcai`, or lead a follower). Watch the game starts without a NAVI error.
2. **Retired meshes**: make a cell that had several meshes and check nothing paths to a spot under the ground.
3. **By hand**: delete some triangles and mark some preferred, and see whether characters walk round the hole and follow the path.
4. **Regions**: paint a region with one weather and check it sets in. **Markers**: check one shows on the Pip-Boy and can be fast travelled to.
5. **Zones**: check a level floor changes what spawns. **Patrols**: check the walker walks the ring.
6. **Far land**: look from a height across a new world, and check the chunks line up with the ground as you walk.
