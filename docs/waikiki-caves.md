# Caves in New Vegas, and what FOLab can plan with them

21 Nov 2026, read from the game's files with kitindex (`dungeons\caves` and the rest); nothing put in Waikiki.

## Yes: New Vegas has a cave kit, and its mines use it

- **`dungeons\caves`:** 190 pieces on a 512-unit grid, placed 3,090 times in the game's caves and mines (6,451 joins
  between its pieces in the game's own places, which FOLab keeps as `kit.seen`). The game's mines are this kit with
  mine clutter (supports, carts) on top; there is no mine kit of its own apart from one piece of Lonesome Road's.
- **Tunnels (512 a square):** straight, corner, T, cross, dead end (CaveHall2Way, 3Way, 1way, DeadEnd...), twists,
  doorways out to the sky (CaveHallSmallDoorSky), the way out (CaveExit01). Complete: FOLab's planner reads every one.
- **Caverns (1,024 a square):** the CaveEpic pieces, each 2 x 2 squares of the tunnels' grid: corners (placed 149
  times), walls (49), middles and inside corners (129). These are what make the game's big chambers.
- **Cave to vault:** `CaveHallVaultTrans01`, `CaveToVaultBroken01`: the game joins caves straight onto vault pieces.
  A back way into Kaʻau's Vault through rock (the settlers' cliff trail, proposed) could end in one of these.
- **Rocks and features:** RockCave01-11 boulders and slabs, sulfur variants (NVSulfur...), a crystal rock.
- **Others:** Lonesome Road's sea cave (`dlc04\dungeons\seacave`, 20 pieces, 1,024 a square; FOLab reads all its
  sides as closed, so it can't join them yet), Old World Blues' cave (4 pieces), metro tunnels (Fallout 3's).

## What FOLab can do with caves now

- **Fill an area with tunnels** (`kitplan.filled`, the Kit tab's Generate with the cave kit picked): the area tiled
  with tunnel pieces whose sides all agree, kept only if walking from one end reaches most of it and gets nowhere
  else. Samples: an 8 x 8 area gave 52 pieces, every one reached; 12 x 6 gave 48, 3 squares not reached (left out).
  Pictures: `waikiki-cave-sample-8x8.svg`, `waikiki-cave-sample-12x6.svg`.
- **Not proven:** FOLab's hole check (a floor edge with no wall and nothing under it) finds 33 to 37 such edges in
  each sample. Either the samples really open onto the void where the filled area ends, or the check misreads rough
  rock walls that lean back; not looked into yet. Don't build a cave for Waikiki on these until that's settled.
- **Can't yet:** rooms. FOLab plans rooms on one grid, from one-square pieces; on the tunnels' grid the kit closes only
  a 2 x 2 chamber with no way in. The real chambers are the CaveEpic pieces on a grid twice as coarse.

## What a cave planner needs (in order)

1. Settle the hole check on cave rock (are those 33 edges real?).
2. Caverns as rooms on their own grid: read the CaveEpic pieces as one-square pieces of a 1,024 tileset (the same
   words: corner `..FF`, wall `.FFF`, middle `FFFF`), so a cavern of any size closes.
3. Joining the two grids: where a tunnel meets a cavern wall, as the game joins them (`kit.seen` has every such join),
   the way SetPiece joins the overseer's office.
4. A cave program: a way in, tunnels that wind (the planner's corridors with more bends), caverns along them, dead
   ends worth walking to, levels by the kit's ramps. Then the cave's own dressing (camps, bones, loot).

## A lava tube for Waikiki

A lava tube is one long tunnel, sometimes widening into a chamber, with skylights where the roof fell in. With the
cave kit: a long run of tunnel pieces (straight and gently turning), a cavern or two where it widens, and
CaveHallSmallDoorSky pieces where light comes down. Most of that is what the planner already does with corridors;
the caverns need step 2 above. Where on the island, and what's in it, isn't decided: a question for the user.
