# FOLab 0.6.0 test 18

A test build of FOLab, an editor for Fallout: New Vegas. Unzip it anywhere and run `FOLab.exe`. Nothing is put into
your game until you choose to.

**Download:** `FOLab-0.6.0-test18-portable.zip`
SHA-256: `ee70077286b74f51994e71e546db919a22923eedb34abda0e3dd94014dd792ff`

Since test 16 FOLab has grown most in making whole places from real maps: a city that stands properly on its ground,
buildings and ships of FOLab's own, far views that look like the game's, and many fixes found by walking a large
map-made world in the game.

## What's new

### Editing in the 3D view
- **A grid you can tilt** to match a slope, so pieces line up on hillsides.
- **A pivot point** to turn and scale several things about.
- **Blender's mouse**, as a choice, for those used to it. (Blender's G and R keys aren't there yet.)
- **Select several** with a box anywhere, and Ctrl+click to add one or take it out.

### FOLab's own models
FOLab now makes models of its own, with their textures, collision and far models, instead of only using the game's:
- **Plants:** beach palms, banana plants, hibiscus, dune grass; a jungle of trees, bushes and ground plants; low cover
  for slopes.
- **Buildings and landmarks:** resort hotels, a tower of its own in the Lucky 38's place, historic buildings
  (a grand hotel, a beachfront hotel, a coastal battery, a natatorium), a band shell, a sky wheel, an aquarium, kiosks,
  street lamps, loungers, stalls and signs.
- **A battleship** with insides you can walk round: a second deck, an engine room, a gun turret and the pilot house,
  joined by doors, with a gangway and a pier to the shore.
- **More detail:** bevelled edges, baked shading, surface detail and shine, and far models that keep their
  textures, so FOLab's own buildings no longer show bare at a distance.
- **Hotels you can go into:** the grand hotel, the beachfront hotel and the tower open into lobbies that look out on
  the city, with floors above and a lookout at the top.
- **Textures are stored compressed**, as the game's own are. Uncompressed ones took 4 to 8 times the memory, and in a
  big world the game ran out and dropped them, far off first and then close up.

### Worlds from real maps
- **A city you can climb:** ramps up the outside of buildings to their roofs, camps on the roofs, walkways from roof
  to roof, lookout towers, and raider camps.
- **Buildings stand on the ground:** the land is raised to meet each building and banked round it, so no daylight
  shows under a wall and no foundation hangs over a slope.
- **No more buildings inside buildings.** The step that stands buildings checked each new one only against the first
  it had placed in that spot, so many stood through each other and flickered. It checks every one now.
- **The sea stays the sea:** a landmark by the shore is no longer stood on a square platform built out into the water.
- **Far water:** the distant land now carries the far sea, as the game's own distant land does over Lake Mead.
  Before, nothing past the loaded cells showed water, only the sea bed.
- **Distant land past the map's edge**, from the real coastline, so the horizon isn't a cliff.
- **Plants that suit where they grow:** trees the game grows out of cliff ledges are no longer sown on open ground,
  and vines only hang where they have something to hang from. Plants are thinned to what the game can draw in a
  busy place, so the frame rate holds.
- **Ways into buildings**, rooms behind motel doors, hotels that are hotels inside, piers at the water, rubble that
  lies on the ground, pavement that meets the ground, roads bedded into it, and a Pip-Boy map of the world.
- **Navmeshes mark cover** as the game's do. A big city without cover crashed the game when someone looked for a
  place to hide.

### Also new
- **Radio stations:** make a station from a name and a list of songs, heard everywhere or round one spot.
- **Health check finds broken models:** models that won't read, collision the game crashes on, and records pointing at
  a model that's somewhere else, with one click to point them at it. On one tester's mod it put right 384 of 477
  broken model paths.
- **Kit tab** carries on past a model it can't find, instead of stopping.
- **For the GECK:** land is always stored compressed, and empty deleted entries are left out, after a tester's report
  of the GECK crashing on a FOLab plugin.
- **FOLab.exe opens its window however long the game takes to load.**

## Known limits
- **Much of this hasn't been seen in the game yet:** the far water, the raised ground under buildings, the
  hotels' insides, the far models and the battleship's insides. The far water writes exactly what the game's own distant land holds over Lake Mead
  (the Mojave's water chunks rebuilt byte for byte), which is strong evidence but not the same as seeing it.
- **People only walk where there are navmeshes.** The roofs, walkways and the ship's decks outside have none, so
  only the player goes up there.
- **Big map-made worlds are heavy.** A large city can still run a 32-bit game out of memory; the 4GB patch is
  strongly recommended (FOLab's My mod page links to it).
- **Things borrowed from Fallout 3** (if you own it) are for your own play only, not for a mod you share.

## Checked
- The distant land's tests (29), including rebuilding every one of the Mojave's water chunks byte for byte.
- Tests for the buildings, landmarks, plants, models, battleship, navmesh writing and health check pass.
- The full test run: all 79 test files pass.
