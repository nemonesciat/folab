# How to edit your map

*The short version: click a thing, move it, look at the box at the top that says **Saved**, press **Put in game**. Everything below is the same, step by step.*

## Find your spot

- Press **World** at the top. Press **Ctrl+K** and type a place, a map marker, or two numbers (a cell, like `-30, 12`).
- Hold the **right mouse button** and move the mouse to look round. **W A S D** fly, **Q** and **E** go down and up, **Shift** goes faster.
- **M** switches between the 3D view and the flat map.

## Pick something

- **Click** it. A yellow box goes round it, and **Selected** on the right shows what it is and exactly where it stands.
- **Shift+click** adds more; drag a box round several to pick them all. **Esc** picks nothing.

## Move it

- **Drag an arrow** to slide it that way. Drag the up arrow to lift it.
- **Arrow keys** nudge it a little: ↑ away from you, ↓ nearer, ← and → to the sides. **Page Up** and **Page Down** lift and lower it. Each press is 1 unit; hold **Shift** for 16. Good for a small box that needs to sit just right.
- **Type the numbers**: in **Selected**, *Position* is where it stands (x, y and height). Type a number and press Enter.
- **End** (or **Drop down**) sets it down on whatever is under it.

## Turn it

- Press **R** (or **Turn** in the toolbar), then drag a ring.
- **Ctrl+←** and **Ctrl+→** turn it 1° a press (**Shift** for 15°).
- Or type degrees in *Turn °* in **Selected**.

## The switches in the toolbar

All of these are **off** to start with, so nothing jumps by itself. Turn one on only when you want it.

| Switch | What it does when on |
|---|---|
| **Move step** | Dragging moves in jumps of that many units (handy for lining up walls). The arrow keys use the same step. |
| **Turn step** | Turning moves in jumps of that many degrees. |
| **Line up with pieces** | While you drag, it jumps to line up with pieces right beside it: edge to edge, standing on top. For building from wall and floor pieces. A note says so whenever it happens. |
| **Drop onto what's below** | After you drag something along the ground, it drops onto whatever is under it. |

Something jumped and you don't know why? Look at these four first.

## Remove it, copy it, add something new

- **Delete** (or **Remove**) takes it out. **Ctrl+D** makes a copy beside it.
- To add something: **Place** on the right, search (say *crate*), click it, then click where it goes. The mouse wheel turns it before you put it down; **Esc** stops.

## Undo

Every change is one step: **Ctrl+Z** takes it back, **Ctrl+Y** puts it back. A run of arrow-key nudges counts as one step.

## Is it saved?

The box at the top beside your mod's name says:

- **✓ Saved 14:32**: everything you've done is in your mod's plugin.
- **● Not saved yet**: you've changed things since. Press **Save** (or **Ctrl+S**, or click that box).

Your edits are never thrown away: FOLab writes each one down the moment you make it, so they're there when you open FOLab again even if you didn't save. **Save** is what puts them into the plugin the game loads. If you close FOLab before saving, it asks first.

While FOLab is open, nothing else can change your mod (other tools, and Claude's scripts, are told to wait), so your edits and theirs can't overwrite each other.

## Put it in the game

- The next box says where your mod is: for example **✓ In nv-rs-pad and nv-rs-next**, or **● nv-rs-next has an older save**.
- Press **Put in game**. FOLab saves, puts your mod into every game ticked, and checks each one. The box turns green when they all have it.
- **Click that box** to choose which games get it (the game itself, MO2, or each copy of nv-rs on your PC).

Then start the game there and load a save. Close the game before pressing Put in game again: a running game holds the file.
