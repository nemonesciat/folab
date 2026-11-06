# Outside: land, water and worldspaces

*Shaping and painting the ground by hand or over many cells at once, plants and rocks, water, height maps, and land of your own.*

A worldspace is a grid of cells, each 4,096 units (about 58 m) across, with a point of ground every 128 units. FOLab loads the cells round you as you fly (the **View** tab sets how many) and draws the distant hills to the horizon.

## The Ground brush (3D)

Press **⛰ Ground** in the toolbar, then drag on the ground.

| Tool | What it does |
|---|---|
| ▲ Raise / ▼ Lower | Ctrl does the opposite. |
| ≈ Smooth | Evens out bumps. |
| ▬ Flatten | Levels to the height where the stroke began. |
| 🖌 Paint | A ground texture. Shift+click the ground to take the one there. |
| 🎨 Tint | The ground's own colour. Ctrl paints back to plain. |
| 🌿 Scatter | Plants, rocks, trees and junk, learnt from what the game put round here. Remove (or Ctrl) takes back only what the brush put down. |

**[** and **]** change the size. Things standing on the ground move with it. Each stroke is one Undo.

## Water

The game keeps **one water level a cell**; everything in the cell lower than it is under water. The Ground panel's **Water** section sets the level of the cell you're over, takes it away, or puts it back as the game has it.

## Shaping many cells (the flat map)

Press **🗺⛰ Shape land**. Draw shapes on the map: **Ridge**, **Valley**, **Plateau**, **Flatten**, **Hill**, **Crater**, **Mesa**, **Lake**, **River**. Each marks the cells it reaches (towns and busy places are left out unless you say so; **✚ Mark** adds or takes away cells). The map shows the result half a second after any change; nothing changes until **Shape the land**, which is one Undo.

- Only marked cells change, and shapes fade out toward the edge, so the land meets the rest exactly.
- **Paint the new ground by its slopes** textures it the way the land round it is (roads kept).
- **Keep the ground under buildings and doors** holds it under them.
- Lakes and rivers go last. A river runs downhill all the way and steps down cell by cell, as the game's own do.

## Height maps

At the bottom of the Ground panel: **Save as PNG** saves an area as a 16-bit greyscale picture (a pixel a point); **Load a PNG** brings one back, from GIMP, Krita, World Machine or Gaea. A picture FOLab saved goes back where it came from.

## Land of your own

**Outside → ＋ New worldspace**: a square of flat land, 4 to 32 cells, with the weather and water of a world you pick. FOLab saves your mod and opens it again with the new land in it; from then on every tool here works on it. (Undo starts afresh at that point.) Reach it in game through a door, or the console: `cow <its editor ID> 0 0`.

## In the game

Changed ground shows in game once you restart it. Its **distant view** and the **navmesh** characters walk on don't follow by themselves: **🧭 World tools** makes both (see that guide). Distant buildings and trees still want **xLODGen** (a free tool).
