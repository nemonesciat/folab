# The hotels inside: a plan

The three hotels of Waikiki each have a lobby and a lookout in a small world of their own (`viewworld.py`, `hotelinside.py`)
and floors between, built by `hotelfloors.py` from the game's own kits. Today all three are the same kind of place: rats
by the lobby, ghouls in the kitchens, a gang upstairs, the boss at the top. This plan gives each hotel a shape of its own,
fitting the story plan (`waikiki-story-plan.md`), and says how FOLab builds it.

Marks as the story plan's: **[decided]** the user has settled it, **[proposed]** for the user to say yes or no.

## What the story already settles

- **The Royal Hawaiian is the Kahuna's court. [decided]** He holds court there; its front on Kalākaua is guarded, the
  tribute is brought in at the east end of the block, the strip is lit (story plan, "the two seats").
- **The court is a tourist-trap kingdom. [decided]** Hotel pageantry, luau and tiki, not old Hawaiʻi; plain English
  names, no court titles.
- **Waikiki is weaker than it looks. [decided]** The guns don't fire, and more.
- Nothing in the plan says who holds **the Moana** or **the Kilauea** now. The rejected lore notes had the Moana as an
  inn where deals are made; that's not taken as settled here.

## Two kinds of place

**A fortress** is planned as one way in and one way on, nothing round it: every way to the heart goes through
checkpoints. A checkpoint is a small room on the main route with a barricade facing the way you come and a door each
side, the far one locked. Inside, rooms off the route are locked too, and the way up is behind the most important room.
One **servants' way** runs round a checkpoint, a corridor from a room before it to a room after it, behind a hard lock:
the sneaking route, for whoever can pick it or finds the key.

**A labyrinth** is the opposite: many ways round, dead ends, stairs up and down within the floor so you lose track of
which level you're on, rooms gone to wreck, corridors blocked so a near room is a long walk away.

Both are built the same way as every generated place: planned, filled with the kit's pieces, walked on their real
collision from the way in to every square (`kitplan.walk_check`), furnished after the game's own rooms, then given
what became of them.

## The Royal Hawaiian: the court [proposed]

A fortress. You come up from the lobby the way a petitioner would, and every floor is harder to get through than the
last. Built with the high-end hotel kit (Gomorrah's floors), as now.

| Floor | What it is | How it's built |
|---|---|---|
| **The court** (above the lobby) | The gate room (guards, a barricade), the waiting hall where petitioners and tribute bearers wait, then the **throne room**: the hotel's ballroom, the Kahuna's chair at the far end, straight ahead of the doors. Off the waiting hall the counting room (tribute weighed and written down) and the clerks' office. The way up is behind the throne, in the Kahuna's private room. | The main route is gate room, waiting hall, throne room, private room, in a line. No ways round but the servants' way. The throne room's doors are in line with its far wall. |
| **The stores** | The court's stores, the reason it rules (the history draft: real power was whoever ran the food): the granary and cold store, the armoury, the guards' barracks, the quartermaster's office. | A checkpoint at the stair head. The armoury locked on the quartermaster's key, which lies in his office. |
| **The court's floor** | Where the court lives: the guards' rooms, the courtiers' rooms, a lounge. | A checkpoint at the lift lobby. Rooms locked. |
| **The Kahuna's floor** | His suite, the hall of gifts (tribute of value, trophies), and the lift to the lookout. | Two checkpoints in a row before the suite. The lift up locked on the Kahuna's own key. |

**Who's there [proposed]:** the court's guards on every floor, servants and clerks in the court and the stores,
courtiers on the court's floor, and the Kahuna himself only if the story wants him met here. Not built tonight: the
floors are built empty of people.

## The Kilauea: the labyrinth [proposed]

The tower nobody holds. Its floors have fallen in and been patched across, stairwells cut and bridged, corridors
blocked with furniture, so the way up is a hunt. A place for scavengers and whatever lives in the dark.

- **Built with:** the game's high-end hotel kit (Gomorrah's floors), not the Lucky 38's the Kilauea uses now: FOLab can't
  read corridors in the Lucky 38's kit, so it gives no ways round and no stairs. Many ways round, stairs within a floor,
  about a third of the rooms wrecked.
- **Not yet possible:** a real hole through the floor you can drop through, or a plank bridge you cross over a gap.
  FOLab's generator only builds whole floors; collapsed floors would need pieces of FOLab's own, or the game's ruined
  kits' rubble, placed and walked.

## The Moana: open [proposed]

Two ideas, for the user to choose or set aside:
- **The court's guest house:** where envoys from the valleys, and the pirates when they come to trade, are kept under
  the court's eye. Neutral ground with rules; a place to overhear things.
- **A second labyrinth,** looted and empty, the way to the Kilauea's next door.

## Open questions for the user

1. Is the Royal Hawaiian's court above the lobby, or is the lobby itself the throne room, with the floors above as
   the court's private parts?
2. Is the Kahuna met in his hotel at all, or only at audiences in the lobby?
3. Who holds the Kilauea and the Moana, if anyone?
4. Do the court's guards attack on sight, or only past the first checkpoint? (A fortress you can walk into and be
   turned away from is a different place from one you fight through.)
5. Should the servants' way be a hard lock, or something you learn of from someone?

## Bigger than this: ideas from the user, 21 Nov 2026

The user's brainstorm, kept here so it isn't lost (none of it built yet):
- **The hotels are big buildings.** Not one or two floors of a few rooms. (Done in part tonight: six floors of 13 to 17
  rooms for the court, four of 17 to 20 for the labyrinth.)
- **Some should end up labyrinthine.** (The Kilauea, tonight.)
- **Interiors of FOLab's own:** a whole hotel kit made new, with surfaces for halls, lobbies, kitchens, pools, guest rooms
  and penthouses, after the ritzy interiors of New Vegas (the Tops, Gomorrah, the Ultra-Luxe, the Lucky 38) but each
  hotel with its own theme and look: the Royal Hawaiian pink and Moorish, the Moana white and colonial, the Kilauea a
  modern tower. Today's floors are the game's own kits, so the court's throne room is a plain big room.
- **Vault pieces that close up:** pieces to complete the vault kit, so a generated vault never shows a gap or a blank
  view out of a window. (Another session is working on vault generation.)
- **A window on the valley:** a room in the Vault whose window, opened, looks out over the valley, as the hotels'
  lobbies look out on Waikiki through a small world of their own (`viewworld.py`).
- **The bomb shelters and the battery** need interiors too.
- **Doors that fit:** many of the game's doors barely fit the buildings they serve; none of the hotels has a door that
  matches it, and many homes don't. Doors of FOLab's own, swapped in the way the roads and rubble were.

## Tonight: what was built

On scratch copies on `D:\FOLabScratch\hotel-court` only: nothing in `Waikiki.json` or any game folder, the scratch
FOLab started with game writes refused and stopped after looking.

**The Royal Hawaiian as the court** (`app/hotelcourt.py`): six floors, every one walked from its way in to every square
with everything stood in it, and given a navmesh.

| Floor | Rooms | Main route | Locks |
|---|---|---|---|
| The Court | 14 | gate room, guard post, waiting hall, throne room (the throne at the far end), the Kahuna's private room with the lift | gate, servants' way, 2 rooms |
| The Court's Stores | 13 | stair head, guard post, kitchens, quartermaster's office | 2 gates, servants' way, armoury, 2 rooms |
| The Court's Floor 1 to 3 | 17 each | lift lobby, guard post, lounge | gate(s), servants' way, 3 to 4 rooms |
| The Kahuna's Floor | 13 | lift lobby, two guard posts, hall of gifts, his suite with the lift to the lookout | 3 gates, servants' way, 3 rooms, the lift on a key |

Each floor is one level, but for one servants' stair on the Kahuna's floor. With the servants' way left out, every guard
post and the throne room is the only way to what lies past it (`hotelcourt.holds`, checked on every floor). The
servants' way sometimes comes out in the Kahuna's private room itself, behind its own lock.

**The Kilauea as the labyrinth** (`app/hotelmaze.py`): four floors of 17 to 20 rooms, 6 to 8 levels each, the lift 6 to
10 rooms in from the way in, about a third of the rooms wrecked, the top floor's lift on a key that lies on it.

**Pictures** (`docs/hotel-court/`): a plan drawing of every floor (`*-plan.png`: rooms green, corridors grey, stairs
orange, the servants' way purple, guard posts red, the throne room gold, the lift's room blue, the way in a green dot,
locked doors red dots, the key yellow; each level drawn beside the next), and three views from FOLab's 3D view: the
throne, a guard post's barricade, a labyrinth stair.

**Not done:** nobody stands in these floors yet; the Moana isn't built; FOLab's own hotel kit doesn't exist yet. Checked
from the files only (walked on the real collision shapes); nothing has been seen in the game.
