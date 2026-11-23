# Boats in Waikiki: a plan

The user, 21 Nov 2026: "having rideable boats would make this a next level mod". Two steps: boat travel first (works
everywhere, built), then a boat you steer yourself (a real project with real risks, below).

## What other New Vegas mods do

- **Cars, not boats.** The known drivable vehicles for New Vegas are cars and trucks: XRE CARS by Ermeso and the add-ons
  built on it (Uhmatt's DrivableCars and others), Standalone Drivable Cars, The Frontier's vehicles. All of them need
  the script extender (xNVSE), most also JIP LN. A boat would be built the same way.
- **How they move.** No mod gets the engine to drive anything. A script runs every frame: it reads the keys (an extender
  command: the plain game can't read keys), works out speed and turning, moves the vehicle with SetPos/SetAngle, and
  moves the player into the driver's seat with SetPos (or the player sits on furniture fixed to it). The camera is the
  game's own third-person camera pulled back.
- **Their known problems.** Moving the player by SetPos every frame bypasses the physics: jitter, the player sliding off
  or falling through, odd collisions. A thing moved by SetPos keeps its collision where it was until it's redrawn
  (Update3D) or its cell reloads: you can walk through a moved boat, or hit an invisible one. Crossing into cells that
  aren't loaded yet can stall or crash. Saving while moving can leave the vehicle and player apart. Followers don't come.
  An old forum warning sums it up: vehicle mods "crash the engine" because of how cells load and unload.
- **"New Vegas Driveables (WIP)".** The user mentioned it. I couldn't find a page by that name, and Nexus and DSOGaming
  refuse automated reading. With its link, it can be read in the browser.

## What nv-rs can run today

nv-rs-pad's own read-me: mods that need xNVSE, JIP or other plugins "don't work yet: their script commands are not
built in yet". Its "fixes" preset is the game's bug fixes, not JIP's script commands. So in nv-rs today a mod can use
**only the game's own script commands**. That settles the order:

- Boat travel uses only the game's own commands, so it works the same in the original game and in nv-rs.
- A boat you steer needs to read keys, which the plain game can't. It can't work in nv-rs until nv-rs adds the extender's
  commands, unless it is steered without keys (see below).

## (a) Boat travel: built, not yet in Waikiki

A boat lies by the shore at five stops. Walk up to one: "Sail Boat". A message asks where to; pick a stop (or Stay
ashore). The screen fades to black, you're put ashore beside the boat at the other stop, an hour or three has gone by,
and the screen fades back. Same as the game's own fades in its scripts (the move happens two seconds into the game's
quick fade). Nothing moves on the water, so none of the problems above can happen. Followers should come along (the game
warps them to you after a scripted move); not checked.

| Stop | Button | Where the boat lies |
|---|---|---|
| Waikiki | Waikiki | on the waterfront between the Ala Wai harbour and the Moana (5,000 units from the Ala Wai Boat Harbor marker: the harbour itself has no water deep enough) |
| The Flotilla | The Flotilla | in the water east of the raised sandbar, you land on the sandbar |
| Hawai'i Kai | Hawai'i Kai (Koko Marina) | Koko Marina, 2,000 units from its marker |
| Waimanalo | Waimanalo (Blue Lagoon) | by Blue Lagoon, near the settlers' ship. **The user to decide**: the settlers don't let outsiders through Makapu'u Gate, and a boat lands you inside their road. Drop this stop, or move it, if that's wrong |
| Hanauma Bay | Hanauma Bay | in the bay, by the start |

Rides take 1 to 3 game hours by distance. No fare yet: Waikiki's money isn't decided. Not while enemies are on you
("You can't sail while enemies are close.", as the game's fast travel refuses).

Made by `app/boatferry.py` (`tests/test_boatferry.py`, 14 pass). One Undo. Rehearsed on a copy of Waikiki in
`D:\FOLab-boats\home`: all five stops found, both scripts compile with FOLab's compiler, the plugin built (105 MB) and
read back with every record and boat in place, health with no errors (the five boat cells show "navmesh out of date":
the boats sit in water and the markers have no collision, so no navmesh redo is needed). Not seen in either game.

What could still go wrong in a game: a boat drawn a little high or low in the water (it uses the height the game's own
moored copies of this boat use), an arrival spot that's awkward (on a rock, facing a wall), the message box or fade
behaving differently in nv-rs. Each is a small fix.

## (b) A boat you steer

What it needs:
1. The boat: an activator of the game's boat model (or FOLab's own), with collision.
2. Getting in: the player sits at the helm (furniture moved with the boat), or stands on deck and is carried.
3. Steering: a script every frame reads forward, back, left, right, moves the boat with SetPos/SetAngle, keeps it on the
   water (the water's height in the cell), stops it at the shore (the ground's height ahead), and carries the player.
4. Getting out: at any shore, or only at piers (simpler and safer).
5. Saving: block saving while sailing, or put the player ashore on load.

Risks, worst first:
- **nv-rs can't run it today**: reading keys needs xNVSE. A version for nv-rs could only be "steered" without keys: e.g.
  a helm with buttons (ahead, left, right, stop) or the boat following where the player looks. Clunky.
- **Jitter and collision**: carrying the player by SetPos every frame is the source of every vehicle mod's problems. A
  boat is kinder than a car (flat water, no hills, slow), but the player still sits on a moving thing the physics doesn't
  know about.
- **Cells loading**: Waikiki is draw-bound already; sailing along the coast loads cells continuously. Loading stalls at
  speed, and a crash is possible on a busy shore.
- **Time**: days of work and many test runs in the game, not hours.

Recommendation: play the boat travel first. If the user wants to steer, build it for the original game with xNVSE as an
experiment on a separate test plugin, and keep boat travel as the way that works everywhere. Revisit nv-rs when its
read-me says extender commands work.

Sources: [XRE CARS](https://www.nexusmods.com/newvegas/mods/49042), [Uhmatt's DrivableCars](https://www.nexusmods.com/newvegas/mods/63890),
[SetPos and collisions (forum)](https://forums.nexusmods.com/topic/928384-setpos-and-mesh-collisions),
[drivable car (forum)](https://forums.nexusmods.com/topic/418990-drivable-car), nv-rs-pad's READ ME.txt and mods\READ ME.txt.
