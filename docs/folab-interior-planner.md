# An interior planner for FOLab: what's there, what Morrowind Workshop has, what's missing

21 Nov 2026. Morrowind Workshop's planner read (never edited): `app/web/planner.js` (1,555 lines), `app/plans.py`,
`app/planfrom.py`, `app/extend.py`, `app/rollinside.py`, `app/layoutsurvey.py`, `app/placecheck.py`.

## What FOLab's Kit tab has

- **One click:** a whole place planned and built from a kit (vaults, service tunnels, office blocks, research
  facilities; `kitplan.vault`, `one_click`), every square walked over the pieces' real collision before you see it,
  furnished from the game's own rooms, vaults with a story, locks and a key.
- **One room at a time:** pick a room of the last place made and change what it's for, which real room it copies,
  or re-roll its pieces without touching the rest (`change_room`, `room_themes`, `web/kitroom.js`).
- **Draw a floor plan:** a small canvas: drag a rectangle for a room, drag from room to room to link them (a door if
  they touch, a corridor if not, stairs if their levels differ), a level and a purpose for each room, Build
  (`plan_from_drawing`, `drawn`).
- **Grow this place:** a new wing through a wall of what's built (`grow`).
- **Caves:** only `filled` (an area filled with the cave kit's tunnels, kept if it walks).

## What Morrowind Workshop's planner has that FOLab's doesn't

| | Morrowind Workshop | FOLab |
|---|---|---|
| Rooms | rectangles with tiles cut out, moved by dragging, resized by corners and side tabs, rotated, duplicated, mirrored | rectangles drawn once; only taken away |
| Floors | five, named, tabs, a floor duplicated | a level number per room |
| Doorways | click the wall between two rooms; click an outside wall for the way out | a line between rooms; the way out is wherever the generator puts it |
| Stairs | worked out from the style's pieces, drawn on both floors, pinned by dragging, turned with R | laid by the generator |
| Seeing it | plan view with names, a 3D doll's-house view of all floors | the drawing canvas; a generated plan is seen only in 3D |
| Hand and generator together | a built place remembers its plan; open it, change it, build again; shuffle; extend through a wall with a ghost first | a generated plan can't be opened for drawing (until now: see below) |
| Plans kept | saved by name, loaded again (`plans.py`) | none |
| From the game | any of the game's places read back into a plan (`planfrom.py`) | none |
| Checks while drawing | unreachable rooms flagged, the way out blocked, overlaps | only on Build |
| Sizes | room sizes from the game's own rooms by kind (`layoutsurvey.py`) | the generator's sizes, not offered while drawing |
| Rolling | roll the interior until it has what was asked for, keep one (`rollinside.py`) | re-roll one room |
| Undo in the planner | its own undo and redo | none |

## What's missing, most useful first

1. **Hand and generator on one plan.** Open the last generated place as a drawing, change it, build again. *Started
   21 Nov 2026* (below).
2. **See the generated plan** in the Kit tab, every level from above. *Started* (`planpic.py`).
3. **Move and resize rooms,** undo and redo in the drawing. *Done 22 Nov 2026* (below).
4. **Doorways and the way out by hand:** click a wall to put a doorway, an outside wall for the way out.
5. **Names for rooms** in the drawing. *Done 21 Nov 2026.*
6. **Plans kept by name,** like prefabs. *Done 22 Nov 2026.*
7. **Checks while drawing:** a room nothing reaches, a link that can't be made, a room too small for the kit. *Done 22 Nov 2026.*
8. **A plan from one of the game's places** (Vault 22, say), to study and build from.
9. **Caves:** the cave kit's caverns are 2 x 2 pieces (CaveEpic corners, walls, middles, placed 300 times by the
   game) on a grid twice the tunnels'; FOLab plans only on one grid. See `waikiki-caves.md`.
10. **Stairs by hand,** pinned where you want them.
11. **A doll's-house 3D view** of the plan before it's built.

## Started: the last place as a drawing, and its picture

- `kitplan.drawing_of(plan)`: a generated plan as the drawing canvas's rooms (the box round each room on the level
  it's mostly on, its purpose and its own name) and links (rooms joined through a door, or through corridors and
  stairs between them). Rooms built whole (the overseer's office, a two-storey atrium) come over as plain rooms.
- `/api/kit/drawing` gives it for the last place made; the Kit tab's **Draw from the last place** puts it on the canvas.
- `/api/kit/picture` gives the last place's plan as a picture (`planpic.svg`); the Kit tab shows it under the rooms.
- `plan_from_drawing` keeps a drawn room's name.

## Added 22 Nov 2026

- **Dragging moves or resizes a room** (the "Dragging" buttons over the canvas: draws and links / moves a room / resizes a
  room); a dashed outline shows where it would go, red where it would overlap or be under 2 squares. **↶ ↷** and
  Ctrl+Z / Ctrl+Y on the canvas undo and redo any change to the drawing (80 steps).
- **Checked while you draw** (`kitdrawings.check`, `/api/kit/drawcheck`): after each change the drawing is planned as Build
  would, without its pieces (a hundredth of a second once the kit is read), and the tab says "every room reached", or
  what's wrong (overlap, too narrow, nothing joins a room), and what Build would do differently (a link it can't make
  left out, a room joined to its nearest instead). What Build then can't fill or walk is still said by Build.
- **Plans kept by name** (`kitdrawings.save/load/remove/names`, `/api/kit/plans`, `/api/kit/plan/save|load|delete`):
  JSON in `plans/` under FOLab's home, like prefabs, with the kit it was drawn for.

Still to do, most useful first: two-storey rooms in a drawing (so a vault's atrium comes over: the last place as a drawing
rebuilt 2 of 4 vaults), doorways and the way out by hand, a plan from one of the game's places, stairs by hand, a 3D view
of the plan, caves (two grids).
