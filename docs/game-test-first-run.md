# The game test's first real run

Nothing in the game test has ever run in the real game. It has only run against `tests/fake_game.py`, which does what the checker *should* make the game do. This page says what a first real run will do to your machine, what you are approving, what isn't known yet, and what to look at first if each thing fails.

**Start small.** Pick a little place of your own with a door and a few rooms. Expect the first few runs to stop early, because the checker's text has never been through the game's compiler. A run that stops early is safe and tells you where it stopped. Most failures should be one-line fixes in `app/gametestcheck.py`.

## What it does to your machine

From **Start the game** on **Tools > Test in game**, in this order:

1. **Refuses if it can't go.** Nothing has changed at this point. It refuses if the game is running, xNVSE or JIP LN is missing, a master isn't in Data, the place has no editor ID, or an earlier run hasn't been put back yet.
2. **Fingerprints your things.** That means every file in your saves folder (hashed), `Fallout.ini`, `FalloutPrefs.ini` and `plugins.txt` (hashed), and the size and date of each plugin in Data.
3. **Writes a journal**, `gametest\journal.json` in FOLab's folder. Every change below is listed there *before* it's made, with a copy of whatever it replaces.
4. **Puts these in your Data folder, for the run only:**
   - `FOLabGT <your mod>.esp`, a test copy, so a version you've installed under the mod's own name isn't touched.
   - `FOLab Game Test.esp`, the checker's plugin. It holds only global variables.
   - `NVSE\plugins\scripts\gr_folabgt.txt`, `gl_folabgt.txt` and `gn_folabgt.txt`.
   - `NVSE\user_defined_functions\folabgt_tick.txt`.
   - The folder `FOLabGameTest\`, holding the plan, the result file and the console log.
   - Your mod's own meshes and textures, if it has any. Anything they replace is kept and put back.
5. **Sets aside** `gr_folab_load.txt` (Play here's autoload), because it would load a save.
6. **Rewrites `plugins.txt`.** It lists only your mod's masters, the test copy and the checker. No dates on your files change.
7. **Edits both INIs** (`Documents\My Games\FalloutNV`):

   | Setting | For the run | Why |
   |---|---|---|
   | `sLocalSavePath` | `FOLabGameTest\` | Your saves are kept apart |
   | `bSaveOnTravel`, `bSaveOnWait`, `bSaveOnRest`, `bSaveOnInteriorExteriorSwitch` | 0 | No autosaves |
   | `bFull Screen`, `iSize W`, `iSize H` | 0, 1024, 768 | A small window |
   | `bAlwaysActive` | 1 | It keeps running behind other windows |
   | `bBackground Mouse`, `bBackground Keyboard` | 1 | It doesn't hold your mouse or keyboard |
   | `SIntroSequence`, `sMainMenuMovieIntro` | empty | Straight to the main menu |
   | `fDefaultMasterVolume` | 0 | Silent |

8. **Starts the game** through `nvse_loader.exe`. It never starts `FalloutNV.exe` directly, and never sends keys or takes the focus on purpose. Steam must be running.
9. **Watches it.** It closes the game, and only the process it started, on any of these:
   - The time cap: twice the estimate plus 7 minutes, never more than an hour.
   - No first line in the result file within 4 minutes.
   - The file not growing for 2 minutes.
   - One of your saves changing.
   - The cursor being held inside a window.
10. **Puts everything back,** whatever happened: files byte for byte, with dates and read-only marks. It then fingerprints again, and **any difference is the first line of the report.** Your saves are never written to, even to undo something.

If FOLab itself dies during a run, the journal is still there. The next time FOLab starts it puts everything back, unless the game is still running, in which case it waits for the game to close. It also makes a report from whatever the run had written.

### What it can't keep apart

- **xNVSE plugins (DLLs) still load.** Only plugins can be switched off. The checklist before a run names the DLLs.
- **Other mods' text scripts** in `NVSE\plugins\scripts` still run. FOLab leaves other mods' files alone. Their `gl_`/`gr_` scripts may fail to compile with their plugins off, and JIP then prints a line saying a script file couldn't be compiled.
- **Loose files and archives in Data** stay in play. A texture or mesh replacer still applies.
- **The game's logs** beside the exe (`jip_ln_nvse.log`, `nvse.log` and others) are rewritten by any start. FOLab copies them into the run's folder. `script_data_cache.bin` beside the exe may also be rewritten; FOLab neither checks nor restores it.
- **A mod manager.** FOLab reads and writes the usual `%LOCALAPPDATA%\FalloutNV\plugins.txt` and starts the game itself. A virtual folder from Mod Organizer won't be in play.

## What you're approving

- Typing the words on the page starts the real game, once, for that one place. Nothing else starts it.
- The temporary changes listed above, to your Data folder, `plugins.txt` and both INIs.
- A game window opening. It may come to the front (see below).
- About as long as the page estimates, or less if it stops early.

Leave the game alone while it runs. Clicking into it can make it take the mouse, and FOLab then closes it.

## What's known, and how

**Proven with the fake game and by the tests (`tests/test_gametest.py`):** the plan, the plan's chunks, the format and every field of the result file, the whole report, all of the isolation, restoring from any state, and each way of stopping. The checker's text has also passed the checks that need no game: `if`/`endif` balance, every variable declared, and the field counts of everything it writes.

**Read from your own files, not run** (`py -3 app/gametestcheck.py` rechecks the tables):

- Every xNVSE and JIP command used exists, with the number of parameters the checker gives it. Every game command is in `scriptfuncs.json`.
- From JIP's machine code: the runner's prefixes are `gr`, `xm`, `gl`, `gn`, `ln`, `gs` and `gx`. Only `gr` compiles and runs at once.
- `WriteStringToFile` goes by the game's folder. Non-zero mode adds a line break and then the text. It makes missing folders for a new file.
- `ReadStringFromFile` sees only a file's first 16 KB (hence the plan in chunks), with first-line and count arguments.
- `FileExists` adds `data\` itself.
- `GetRayCastPos` takes three globals and needs a calling ref.
- xNVSE's DLL contains `data/nvse/user_defined_functions/`, which is presumably where `CompileScript` looks.

## What only a real run can prove

Each entry says what's assumed and what you'd see if it's wrong. "Lines" means the result file, kept in the run's folder as `lines.txt`. Beside it are `console.txt` and `game jip_ln_nvse.log`. The report's advice points at these sections.

<a id="gr-rules"></a>
### `gr_` compile rules: no lines at all

- **Assumed:** JIP compiles a whole text with `ref rT`, `let` and `if`, no `scn` or `begin`, and `con_SCOF` with a path. Today's only evidence is Play here's single-line `LoadGame`.
- **If wrong:** the report says *never started*. Nothing is in lines.
- **Look first:** `game jip_ln_nvse.log`, whose message for this is "One or more script files could not be compiled". Then check that the game reached its main menu at all (is `SIntroSequence` empty enough, or does a menu wait for a key?).
- **Try:** cut `gr_folabgt.txt` down to one line and build up from there.

<a id="tick"></a>
### The tick: `boot|gr` and nothing more

- **Assumed:**
  - `CompileScript "folabgt_tick.txt"` finds the file in `user_defined_functions` (perhaps it wants no `.txt`).
  - It compiles `begin Function { }` with `let`, `$` strings and `aP[0]` as written.
  - `SetGameMainLoopCallback rT 1 2 3` means add it, every 2 frames, in game and menus. These arguments are from memory; only their types were read from the DLL.
- **If wrong:** `abort|tick did not compile`, or `boot|gr` alone.
- **Look first:** `console.txt`, which holds compile errors if SCOF took effect.

<a id="coc"></a>
### `coc` from the main menu, without a save: `go|1` and no `at`

- **Assumed:**
  - `con_CenterOnCell "Edid"` from the main menu starts the game in that place with no save.
  - `MenuMode 1013` means the main menu.
  - The tick survives the move, or `gl_`/`gn_` restart it. **Whether a move from the menu resets the globals or stops the callback isn't known.** That's why `went.txt` exists: without it, a reset would send the game back to the place forever.
- **If wrong:** the report's advice is *no move*. A line `abort|the first move never happened` means the game stayed at the menu. If the file stops after `go|1` with the game in the place, the tick died: look at which `boot|` lines came (`gl` or `gn` means a load fired, and which one).
- **Way out if it never works:** start from a small save made for the purpose, kept in the test saves folder. That means a `LoadGame` in `gr_` and an extra approval from you, because it makes a save.

<a id="plan"></a>
### Reading the plan: an `at` line and no `cal` or `stand`

- **Assumed:**
  - `sv_Construct` with `%.0f` builds the chunk's path.
  - `ReadStringFromFile $sPath n 1` gives line n and no line break.
  - `sv_Split $sL "|"` gives an array from 0.
  - `ToNumber` reads it.
  - `SetPosEx` moves the player in the same tick's cell.
- **If wrong:** `abort|plan line not understood`, or silence.

### `WriteStringToFile` with `%i` and `%n`: lines look wrong

- **Assumed:** `%.1f` works with globals and locals, `%i` gives a form's 8 hex digits, and `%n` gives its name. A name with nothing in it just leaves that field empty.
- **If wrong:** `unreadable_lines` in the report. Compare lines with `RESULTS` in `gametestcheck.py`. Forms are compared by their last 6 digits, so a form printed some other way shows as *wrong_place*: check that first.

### God mode: `player_died`, or the player hurt by falls

- **Assumed:** `con_ToggleGodMode` runs once and works from a UDF. A run dying from falls is exactly what happened on the Workshop's run 2.

### What rays mean: `rays_not_trusted`

- **Assumed:**
  - `player.GetRayCastPos gX gY gZ` with defaults casts from the player, the way the player faces, and fills the globals with the hit.
  - `SetAngle X 89` looks down, and `SetAngle Z 0` faces north.
  - A miss leaves the globals alone (the checker sets -99999 first).
  - The optional float, integer, string and float parameters are left at their defaults; what they mean is unread.
- **What protects you:** the first step (`cal`) tests this at one point. Down must land near the floor and north must go north, or **no ray's answer counts** and the report says so. Stands, falls, doors and positions don't use rays.
- **If wrong:** read the `cal` line. If only the pitch's sign is backwards, change `89` in `gametestcheck.py`. If rays start at the camera, the 64-unit tolerance in `_calibrate` may need widening.
- **Also unknown:** whether a ray stops on the player's own body, and whether it hits clutter. A thing that stops the ray itself is counted as *thing_own_ray* and left unjudged.

### Standing, doors and NPCs: findings that look like false alarms

- **Falls:** `SetPosEx` puts the player's feet at the point, and collision and gravity act within the 12 ticks allowed. If points read as falling though the floor is fine, the wait is too short; see `SETTLE`. The limits are constants at the top of `gametest.py`, chosen from Morrowind experience and untested on this game.
- **Doors:** `GetFormFromMod "FOLabGT Mine.esp" "000801"` finds a ref by its 6-digit number. `Activate player 1` takes the player through a load door from a script without opening a menu. 40 ticks in-game is long enough to land. A door to outside lands in a cell whose number isn't compared (only its position is).
- **NPCs:** `PlaceAtMe` with a form from `GetFormFromMod`, `AddScriptPackage DefaultFollowPlayerFar`, and a plain refugee NPC (`1ERefugeeAAM`). If nobody moves in places that are clearly fine, suspect the package before the navmesh.
- **Message boxes:** a mod's script that pops up a box leaves the game in a menu forever. That ends as *went silent*.

<a id="partway"></a>
### Stopped partway

The report says how many of each check were reached and claims nothing about the rest. `last_line` in `report.json` is the last thing written. The next plan line in `gametest\runs\<run>\plan.json` is what it was doing.

### The window and the mouse: `mouse taken`

- **Assumed:** with these INI settings the game leaves the cursor free and doesn't pause in the background, and `SW_SHOWNOACTIVATE` passed to the loader doesn't stop the window coming to the front (it probably won't help).
- **What FOLab watches:** the cursor being clipped to part of the screen. If the game clips it just from starting, every run stops at once. Take `input_grabbed` out of `_thread_run` only if you accept the game holding your mouse while it runs.

### Things nothing watches

Rendering isn't checked, so the report says nothing about looks. A wrong `sLocalSavePath` format would put autosaves somewhere odd; with autosaves off it shouldn't matter, and the live watch covers your real folder. Look at `Documents\My Games\FalloutNV` after the first run: only `RendererInfo.txt` and the like should have changed.

## After the first real run

Change this page: move what you've learned into the "known" section, and fix the checker. Then, as the Workshop did, put a table of what a real run found at the end of this page.
