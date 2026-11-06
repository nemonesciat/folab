# The World page

*Opening places, moving about in 3D and on the flat map, selecting, placing and changing things.*

## Opening a place

- **Places** (left): every interior, your own first. **＋ New** makes a place of your own, empty or a copy of the one open.
- **Right-click a place**: open it, play there, copy it, rename or delete one of your own, put a game place back as it was, make its navmesh, copy its console line, or pin it to the top. Deleting or putting back asks first, and **Undo** takes it back. Other lists have right-click menus too: **Objects** gives the same menu as the 3D view.
- **Outside**: the worldspaces (the Mojave, the Strip, the DLC lands) and the places on each one's map. **＋ New worldspace** makes land of your own.
- **Go to a place** (Ctrl+K): a name, a cell's coordinates (*-18, 0*) or a spot in game units (*x y z*, as the console gives it).
- Select a door, right-click, **Go where it leads**. **Alt+←** goes back to where you were.

## The buttons over the view

The buttons float over the 3D view and the map in groups (Map/3D, the handles, snapping, editing, what shows, and the
ground tools outside). Drag a group by its **⋮⋮** grip to put it anywhere; it stays there. Right-click a group to put it
back in the row, arrange them all automatically, or lock them in place.

**The minimap** shows the place round you from above, with which way you look. Drag it by its title bar anywhere;
let go near a corner and it docks there. **◱** makes it bigger or smaller, **+ / −** zoom, **✕** hides it (the View tab
brings it back), and a click on it takes you there.

## Moving about

| Do | To |
|---|---|
| Right-drag | Look around |
| W A S D | Fly the way you look (Q / E down and up, Shift faster; tap twice and hold to sprint) |
| Wheel | Forward and back |
| Middle-drag | Slide |
| Alt+drag | Circle round the selection |
| F | Look at what's selected |
| M | The flat map (and back) |

**On the flat map**: drag to pan, the wheel to zoom, double-click to look at that spot in 3D.

## Selecting

- **Click** a thing; **Shift+click** adds or takes away; drag a box on empty space (on the map: **Shift+drag**).
- **Esc** deselects. **Right-click** for everything you can do with it. **Double-click**: its window (record and placement).
- **H** hides what's selected, **Shift+H** shows everything again. Hiding only changes what you see.
- The **View** tab (right): show or hide kinds of things, **🔒 lock** kinds against clicks (walls, say), only your mod's changes, the minimap, how far the outdoors loads.

## Moving, turning, sizing

Drag the arrows to move (**G**), the rings to turn (**R**), any handle of **Scale** (**3**) to size it evenly. **World axes / Own axes** switches the handles' directions. **Grid** and **Angle** set the steps; **Snap pieces** lines walls and floors up with the pieces round them. **End** sets a thing on what's below. The **Selected** tab has exact numbers.

## Placing

Search in **Place** (right), then click a result and click where it goes, or drag it into the view. **Recently used** and **Prefabs** (groups you saved with *Save as a prefab*) are above the search. **Ctrl+C / Ctrl+V** copy and paste, **Ctrl+D** duplicates.

While something's on the mouse, before you click it down:

| Do | To |
|---|---|
| Wheel | Turn it by the **Angle** setting (Shift+wheel: 1°) |
| R (Shift+R the other way) | A quarter turn |
| Ctrl+wheel, or [ and ] | Make it bigger or smaller |
| Alt+wheel, or Page Up / Page Down | Raise or lower it (Shift: 1 unit) |
| 0 | Put all that back |
| Esc or right-click | Stop placing |

It stays on the mouse so you can put down several. The turn carries on to the next thing you pick, as a run of pieces usually faces one way; size and height start afresh. A prefab turns and sizes as a whole. A note at the bottom of the view shows where it stands.

**Building from the game's kits.** Select a building piece from a vault, an office, a cave and so on: **Selected** lists its open sides, with green panels in the view. Pick a side to see what can join there, with the joins the game itself built first. Hover over one to see it in place, click to put it there, and carry on from the new piece. The **Kit** tab generates a whole layout in the place you've got open, one you can walk with every way out closed off. It has no stairs, lights or furnishings yet.

**Navmesh** (the **Kit** tab) is what lets characters find their way round a place in game. **Make navmesh** builds one for the place you've got open from what's in it now, and Save puts it in your plugin. If you move things afterwards it says it's out of date: make it again. **Show it in the view** draws it, the game's own too. Places inside only so far.

Right-click a thing: **Swap for…** replaces it, **Replace every one here…** replaces all of them.

## Doors

Right-click a door: **Link it to another door…** makes the two lead to each other (each arriving in front of the other). **Go where it leads** follows it.
