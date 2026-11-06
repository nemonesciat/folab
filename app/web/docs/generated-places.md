# Generated places

The **Kit** tab builds whole places from the game's own building pieces. Open a place of your own first (**+ New** under Places), then open the tab.

## Generate

Pick a kit and a size in squares, then press **Generate**. FOLab:

1. **Plans first.** It decides on rooms of different sizes, each with a purpose, joined by corridors. There's a main route from the first room to a far end, with side rooms off it, and stairs where the kit has stairs that really work.
2. **Fills the plan with pieces.** Every side has to agree with what's beside it. Each room keeps to a few pieces of its own, so one room looks different from the next. Joins the game itself built are preferred.
3. **Adds doors, lights and furnishings.** These are copied from real rooms in the game, in the same spots on the same pieces. Each room takes after one real place that suits its purpose.
4. **Walks it.** Using the pieces' real collision shapes, it walks from the first room to every square. A layout with a part you can't reach, or a way out, is thrown away. Anything that stands in the way is taken out.

**Try another** replaces the last result with a new one. Everything is one undo step.

Kits with no pieces that close a room (caves, for example) are filled the old way, and still walked.

## A vault in one click

The dial sets the size. You get an entrance, an atrium, living quarters along their own corridors, an overseer's office up a flight of stairs, and a reactor at the far end. Higher settings add a mess hall, a clinic, stores and workrooms. Tick **Ruined, with rubble** to use the ruined kit.

The game's own one-piece overseer's office and gear-door room aren't used, because they don't sit on the square grid. These rooms are built from ordinary pieces instead. The tall "galley" atrium pieces aren't used either, as the kit has no corners for them, so the atrium is a large room with rows of columns.

## Grow this place

**Grow it** adds a new wing to the place you're in and keeps what's built. One wall piece is swapped for the same piece with a doorway, and a corridor and rooms go on beyond it. You can press it again and again. It also works on places from the game, as long as most of the place comes from one kit.

## The way out

A generated place has an exit door in its first room, which leads nowhere yet. Select it and link it as you would any other door. Then make the navmesh again, so characters can use it. The tab makes a navmesh by itself after each generate, but a door's link changes it.

## Check in the game

FOLab can only prove so much from the files. Try these in game:

- Doors open, and aren't set back from their frames.
- Lights look right. They're copied from the game, but in new company.
- Furnishings don't float or sink.
- Characters can follow you up stairs and through doors.
