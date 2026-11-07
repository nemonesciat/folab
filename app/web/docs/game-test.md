# Test in game

*The **Tools** page, **Test in game**: the game walks a place by itself and writes down what goes wrong, and FOLab turns that into a report. So you don't have to walk it yourself.*

**This is still new.** It has run all the way through in the real game, but only on one small place, so a run on yours may stop early; your files were put back every time that happened. Keep the game window in front while it runs, and leave the controller alone. What's under things isn't judged reliably yet. `docs/game-test-first-run.md` lists what real runs found, what's still unknown, and what to look at when something fails.

## What it checks

Pick a place of your mod and press **See what it would check**. The game isn't involved yet. The counts come from what FOLab already has:

| What | How |
|---|---|
| **Floor** | One point for every 256-unit square of the navmesh, per level. The game stands on each, then looks for falling through, being pushed off, or having something close all round. |
| **Doors** | What the game says of each, then through it: does it land where it should, and do you stay up? |
| **Things** | Your loose items, containers and furniture: did they move, and what's under them? |
| **Characters** | The ones you placed: are they still there, alive, and not through the floor? |
| **Walks** | Someone told to follow you across the place: does the navmesh bring them? |

Some things show before any run, such as a navmesh in pieces that don't join, or a place with no editor ID.

## Running it

The page lists what must be ready first: xNVSE, JIP LN NVSE, the game closed. To start, type the words it asks for. The game then opens in a small window, runs by itself and quits. Leave it alone while it runs.

While it runs:

- **Only your mod's masters, your mod and the checker are on.** Your load order comes back afterwards.
- **Your saves are kept apart** and autosaves are off. If one of your saves changes anyway, FOLab closes the game at once and says so.
- **Everything goes back when it ends,** byte for byte, and FOLab then checks that. If FOLab or the game crashes, it's put back the next time FOLab starts.
- **FOLab closes the game** if it runs past its time, stops writing, or holds your mouse. It only ever closes the game it started.

xNVSE plugins, other mods' text scripts and loose files in Data still apply: only plugins can be switched off.

## The report

Worst first. **Go there** opens the place at the spot.

| Says | Means |
|---|---|
| *It ran to the end and nothing serious turned up* | Every check got an answer, with no errors. |
| *It ran to the end and found problems* | See the list. |
| *The run stopped before the end* | Only part of an answer: it counts what was reached and claims nothing about the rest. |
| *The game never started checking* | Nothing was measured. The red line says what to look at first. |

Some of the findings you'll see most:

| Finding | What it is |
|---|---|
| `your_file_changed` | Something of yours isn't as it was. Always at the top. |
| `fell_through`, `door_fell`, `actor_fell` | Collision isn't where it looks. |
| `boxed_in`, `pushed_off` | Something solid is on the spot. |
| `door_did_not_lead`, `door_wrong_place`, `door_leads_nowhere` | The door isn't what the mod says. |
| `no_path` | Someone couldn't walk across: look at the navmesh. |
| `thing_floating`, `thing_buried`, `thing_moved` | Things not resting where they should. Things on furniture with no collision show here too. |
| `rays_not_trusted` | The first ray test failed, so rays weren't used for this report. Falls and doors don't need them. |

**Read a result file…** makes a report from pasted text, for a place you pick. The game isn't involved. Earlier runs stay listed, each with its files in `gametest\runs` in FOLab's folder.
