# Generated places

The **Kit** tab builds whole places from the game's own building pieces. Open a place of your own first (**+ New** under Places), then open the tab.

## Generate

Pick a kit and a size in squares, then press **Generate**. FOLab:

1. **Plans first.** It decides on rooms of different sizes and shapes, each with a purpose, joined by corridors. There's a main route from the first room to a far end, side rooms off it, and corridors that make more than one way round. The way in is a small room, a short straight corridor, and then the biggest thing in the place, straight ahead.
2. **Fills the plan with pieces.** Every side has to agree with what's beside it. Each room keeps to a few pieces of its own, so one room looks different from the next. Joins the game itself built are preferred.
3. **Adds doors, lights and furnishings.** These are copied from real rooms in the game, in the same spots on the same pieces. Each room takes after one real place that suits its purpose, judged as a whole room.
4. **Walks it.** Using the pieces' real collision shapes, it walks from the first room to every square. A layout with a part you can't reach, a way out, or an edge that opens on the void is thrown away. Anything that stands in the way is taken out.

**Try another** replaces the last result with a new one. Everything is one undo step.

Kits with no pieces that close a room (caves, for example) are filled the old way, and still walked.

## Tall rooms, stairs and ways round

**Tall rooms.** Where a kit has them (the vault kits' galley pieces), a main room can go up two storeys, with a balcony along each long side. It's built the way the game's own vaults build theirs: a room stands under each balcony, open to the hall, and another stands over it, which is how you get out onto the balcony. Stairs lead up from the room below to the room above. With only two rows of squares, a bridge joins the two balconies.

**Stairs.** A kit can use any of these, but only after FOLab has built each kind between two rooms and walked it:

- a straight flight, one storey;
- a long flight: a flight, a landing and another flight, two storeys in one line;
- a flight that doubles back: two flights with a turning landing, two storeys in little floor;
- a stairwell made in one piece, where the kit has one (office, facility, hotels, casinos).

**Ways round.** When two parts of a place are near on the plan but a long walk apart, a corridor may join them, by stairs if they're on different levels. A way round is only kept if the kit can still build the plan with it.

## A vault in one click

The dial sets the size. You get an entrance, a two-storey atrium with balconies, living quarters along their own corridors, the overseer's office and a reactor at the far end. Higher settings add a mess hall, a clinic, stores and workrooms. Tick **Ruined, with rubble** to use the ruined kit.

The overseer's office is the game's own room made in one piece. Its doorway isn't on the kit's grid, so it's joined exactly as the game joined it, and the way out of its lower part, which leads elsewhere in the game's cell, is closed with a dead end. If it doesn't fit, the office is built from ordinary pieces instead.

## Other places in one click

**Service tunnels** (the utility kit), an **Office block** and a **Research facility** are made the same way, with rooms that suit each. Metro tunnels and sewer pipes aren't offered. Their kits have a straight tunnel and a few curves, with nothing that closes the ends of a tunnel, so nothing built from them would be sealed.

## One room at a time

After anything is generated, its rooms are listed under **This place, one room at a time**. Pick one to:

- change what it's **for**, which chooses its furnishings again;
- choose which real place it **copies**, best fit first;
- **re-roll** it: new pieces and things for that room, with every other piece left alone.

A tall room or a room made in one piece can't be re-rolled, as it's built whole. This only works on the last place generated since FOLab started.

## Draw a floor plan

Under **Draw a floor plan**, drag on the grid to draw a room, and drag from one room to another to link them. Linked rooms that touch get a door. Otherwise they get a corridor, with stairs if they're on different levels. Click a room to choose what it's for and its level. The first room you draw is where you come in. **Build this plan** uses the kit picked at the top of the tab.

Your rooms are built where you drew them, and the whole thing is walked like any other place. If it can't be built, FOLab says why and nothing changes.

## Grow this place

**Grow it** adds a new wing to the place you're in and keeps what's built. One wall piece is swapped for the same piece with a doorway, and a corridor and rooms go on beyond it. You can press it again and again. It also works on places from the game, as long as most of the place comes from one kit.

## The way out

A generated place has an exit door in its first room, which leads nowhere yet. Select it and link it as you would any other door. Then make the navmesh again, so characters can use it. The tab makes a navmesh by itself after each generate, but a door's link changes it.

## Check in the game

FOLab can only prove so much from the files. Try these in game:

- Doors open, and aren't set back from their frames.
- Lights look right. They're copied from the game, but in new company.
- Furnishings don't float or sink.
- Characters can follow you up stairs and through doors, and along balconies.
- You can't get stuck under a balcony or on a landing.
- The overseer's office looks right joined to a corridor: only one such room was ever built by the game.
