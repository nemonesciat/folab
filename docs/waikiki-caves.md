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
- **Settled 22 Nov 2026: those "holes" weren't.** Every one was the same spot inside the same piece (168 in, 104
  across in the plain dead end, for one): the cave floor runs on under rock too low to stand under (an overhang 113 over
  the floor), so walking stops there, and the rock was 3 units too high to count as a wall. The check now counts floor
  running on (within a step) as no hole, and needs something to land on under every column of a gap. Both samples: 0.
- **Can't yet:** rooms. FOLab plans rooms on one grid, from one-square pieces; on the tunnels' grid the kit closes only
  a 2 x 2 chamber with no way in. The real chambers are the CaveEpic pieces on a grid twice as coarse.

## What a cave planner needs (in order)

1. ~~Settle the hole check on cave rock~~ (done 22 Nov 2026: they weren't holes).
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

## The first cave: in the Ko'olau ridges (22 Nov 2026)

The user: "the first cave goes in the Ko'olau ridges". Made on a copy of Waikiki, not in it (`app/kocave.py`,
`app/rockdoor.py`, `tests/test_kocave.py`; rehearsed by `D:\FOLab-vault2\vault_cave_into_waikiki.py`).

- **Inside:** tunnels of the cave kit filling an area of 10 x 8 squares (about 73 by 58 m), kept only if walking from the
  way in reaches nearly all of it and nowhere else, and no hole. Its way out is the kit's cave mouth
  (`CaveHallAntagonizerEntrance`) where it opens on nothing, with the cave door the game hangs in that piece (CaveDoor01,
  FalloutNV's own: Honest Hearts hangs an invisible one there). Lights and things from the game's own caves, piece by piece
  (fungus, cave lights, rocks, some loot); bones and gore left out until the user says what happened there.
- **Outside:** the mouth is on the Wai'alae Nui ridge (the Radar Dome's ridge: "empty jungle", wild), on a steep slope a
  short climb above where its trail starts: the game's mine door frame and cave door set into a bank cut in the slope,
  Zion's canyon rocks round it, plants cleared off the pad, a path up from the trail's signpost. Which ridge was FOLab's
  pick: easy to move.
- **Not decided (the user's):** what the cave is (a lava tube? a hideout? whose?), its name (it's "Cave" for now), what
  lives in it, whether it has a map marker (none yet).
- Caverns (the 1,024 CaveEpic chambers) are still not planned: this cave is tunnels only.
