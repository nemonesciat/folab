# FOLab from Waikiki: what making a whole mod taught us

Written 20 Nov 2026 from: CLAUDE.md, `docs/waikiki-reports.md`, `docs/waikiki-story-plan.md` ("Built so far"), the git
log since 15 Nov (40 commits), the scratch scripts the Waikiki sessions wrote (about 1,400 of them), and what is on disk
in FOLab.exe's home (`packaging\out\FOLab`).

**The hard truth.** Waikiki was made with FOLab's *modules*, not its *pages*. Of about 60 builders written for it, 9 can
be reached from the editor (the Real map panel's Make it, Grow, Put up buildings, Go back; the Ground panel's Fill bare
brush; World tools' navmesh; Play, Put in game, Put in MO2, the old-copies card). Everything else was a Claude session
loading `Waikiki.json` in Python, running a builder, making a backup by hand and saving. A person with only FOLab.exe
could make Waikiki's land and empty city, and nothing after.

Each item says **who it hurts**, **how often**, and **how big the fix is** (S: an afternoon; M: a day or two; L: several
days or more).

**What the scratch scripts did** (about 900 in the Waikiki sessions' scratch folders, the rest copied libraries):

- **Checks and measurements, ~250: the biggest group, run again and again.** Floating things (12+ scripts), walk
  checks (24; the Flotilla's walk alone in 7 versions), the wall's gaps (~21), navmesh rebuilds and their debugging
  (~18), far view (~21), water (~15), grass (13), draw counts, doubles, health (copied into several folders).
- **World-building steps, ~110:** each loads the mod, runs one builder's `ops`, applies it as one Undo, saves.
- **Developer patches to FOLab's code, ~120:** not jobs, left out here.
- **Pictures, ~45:** top-down plans and sheets of pieces for the user to look at before building.
- **Putting the build in, ~10:** every nv-rs, MO2, then a hash and far-view check of each copy.
- **The same steps in nearly every script:** refuse while the game, FOLab, MO2 or nv-rs runs (92); a dry run unless told
  `apply` (most); a copy of the mod as "Waikiki before <step>" (78); one Undo (132); a full save (144). 154 scripts
  switched off FOLab's own "game is running" guard to get past it. That is the Big jobs runner, written by hand ~100 times.
- **Work-rounds for things FOLab lacks:** let floating things down (floatfix, applyall), stitch torn cell edges
  (fix_seams), a plant cap per cell (thin), remake every out-of-date navmesh (navrun, renav), copy to every nv-rs by
  hand when the far view went stale (nvsync), check every copy after putting in (trialcheck), the Pip-Boy map (pipmap).

Added from this: **M13 torn cell edges** (a job: stitch neighbours' heights where they disagree; S) and **W10 a dry run**
(every big job should first say what it would change, then apply on a click; part of the runner).

---

## 1. Missing in FOLab's own pages (done by script, needs a button)

| # | What | Modules (all have an `ops`-style entry already) | Who / how often | Fix |
|---|------|------|------|-----|
| M1 | **Real city steps** with no button: coast, landmarks, dress (things on the ground, plants, lots, footings, roads bedded), life (weather, zones, wildlife, people), hotels (view worlds) | `api_maps` routes `/landmarks`, `/dress`, `/life`, `/hotels`, `/coast`, `/green`, `/plants` exist, the panel has no button for them | Anyone making a city from a map; every rebuild | S each: buttons on the Real map panel over routes that exist |
| M2 | **Fix-ups after building** that every big world needed: things floating or sunk (`settleup.settle`), ground upwards (`groundfit.fit`, `close_gaps`, `settle_pieces`), lying things seated (`osmdress.seat_lying`), road things lifted (`roadbed.onto_roads`), plants seated and budgeted (`plantsplit.split`/`rework`), bare ground filled (`understory`, whole world) | each `fn(gd, pr, world, ..., progress)` | Every big world, after every structural change; ran dozens of times on Waikiki | M: one "Big jobs" runner, these as its first jobs |
| M3 | **Swaps and dressings**: FOLab's guard tower for the game's (`guardtower.swap_ops`, `pad`), bamboo and thatch (`bambooplace.ops`), Mojave buildings restyled (`restyle.ops`), loot and finds (`lootplace.ops`), the ruined freeway (`ruinedfreeway.ops`), rooms not the same twice (`roomvary`) | as above | Anyone making a mod that isn't the Mojave | M: more jobs on the same runner |
| M4 | **Pip-Boy world map** (`worldmap.ops`): without it a FOLab world has a blank Pip-Boy map and no fast travel | `worldmap.ops` | Every new world, after every ground change | S: a job, and a health warning when a FOLab world has no ICON |
| M5 | **Distant view rebuild** (`lodobj` blocks, `lodgen` far ground with `farfoliage`, `plantfar` far trees) | routes partly exist | Every world, after every change outside; the user notices at once ("barren hills", "lollipops") | M: a job, plus "far view out of date" in health |
| M6 | **Walk-check a set** before navmeshing (`walkcheck.check_set`/`check_piece`) | `walkcheck` | Anyone placing stairs, decks, ships, towers | S: a button on a selected thing / set: walked, short, unreached, invisible |
| M7 | **Own models** (model maker: kiosk, settlers' halls, bamboo, hotels, ship, guard tower, hats, clubs) | `modelmake`, `modelsets.put`, `/api/models/make` | Anyone wanting things the game hasn't | L: a Models page (list of pieces, preview, Put in mod). Making a *new* shape still needs code |
| M8 | **Items of FOLab's own**: Hawaiian clubs and blades (`clubs`, `nifmake.build_held`), guns riding on a game gun (`guns`, `gunmake`), hats (`hats`) | as listed | Anyone dressing a setting | M: on the Create page, "Make a weapon / hat like ..." from the pieces that exist |
| M9 | **People restyled**: a kind of the game's people swapped for the mod's own, dress swapped, Mojave gangs out of places (`peopledress`) | needs numpy/PIL/scipy, which FOLab.exe's Python hasn't | Any non-Mojave setting | M + packaging: the swap and clear without the print-making (prints as a ready texture set) |
| M10 | **Set-piece builders of Waikiki itself** (`borderwall`, `ridgeplaces`, `seats`, `cresttrail`, `vaultgate`, `pirates`, `settlers`, `castaway`, `edges`, `flotilla`, `overpassposts`, `shipway`, `natcompound`, the Missouri) | each its own module | Only Waikiki | Not worth pages as they are. What's general in them is: *lay a wall along a line* (borderwall), *a trail along ridges* (cresttrail), *a level terrace in a hill* (ridgeplaces/guardtower.pad), *radiation edges* (edges): L, later, as general tools |
| M11 | **Another game's things** (`othergame`: Fallout 3's Rivet City) | `othergame` | Rare; files can't be handed round | Leave as is |
| M12 | **A border region** (the invisible edge) | none | Every new world | M: new feature (worldrec) |

## 2. Weak (worked, but hurt)

| # | What | Evidence | Who / how often | Fix |
|---|------|------|------|-----|
| W1 | **Backups fill the drive.** Every Put in game copies the old 107 MB `.esp` into `backups/` (two copies 6 s apart on 20 Nov 07:31); sessions' "Waikiki before X" folders are 250-385 MB each. 93 entries, 13 GB in FOLab.exe's home alone; 27 GB with the rest on 20 Nov, when C: was nearly full | `install._backup`, nothing ever deletes | Everyone; every install and big job | **S**: prune on each new backup (keep the last N of each kind, one a day for a week, a size cap), a Backups card (size, open, restore, delete) |
| W2 | **One huge mod file, saved whole on every edit.** `Waikiki.json` is 254 MB (39 MB on 16 Nov); an edit costs ~4.7 s to save, and two writers (FOLab and a script) overwrite each other silently | CLAUDE.md "A big mod's edits", understory note | Anyone with a big world; every edit | **L**: the mod split into parts saved only when changed (records, cells, land, navmesh, by world square). Touches project.py: every session uses it |
| W3 | **Two writers, one mod.** Sessions kept a hand-written note ("check the file's time first") so they didn't wipe each other's saves; FOLab itself saves over a newer file without a word | shared note `waikiki-mod-writes-story-session.md` | Anyone running FOLab while something else edits; the user and several sessions every day | **S**: a lock beside the mod (who has it, since when) and refusing to save over a file changed since it was loaded |
| W4 | **Navmesh runs take hours and can't stop or resume.** ~4.5 s a cell, Waikiki's whole city ~2.5 h; one link error in 3 of 35 batches; nothing saved until the end of a batch; and nobody walks until it's done | `navbuild.generate_area`, `Area.mend` | Every world; after every change to what's walked on | **M**: job saves as it goes, resumes, only remakes cells whose signature changed; walk-check offered first |
| W5 | **Long silent jobs.** Rebuilds of far view, plants, dressing ran minutes to an hour with no progress shown outside a terminal | scratch scripts' prints | Every big step | **S** with the Big jobs runner (progress bar, what it's on, time left) |
| W6 | **Installs to several game copies.** The game, MO2, and four nv-rs folders (`nv-rs`, `nv-rs-pad`, ...); "is it really in?" was asked again and again; a stale `Waikiki.esp` in Data played instead of MO2's (18 Nov) | `copies.py`, memory notes | The user, every build | **S**: copies.py already looks in Data, overwrite, other MO2 mods and every nv-rs on the PC (`nvrs.all_found`), and the pill says "In, but not ready". Missing: a card that lists *every* place, the current ones too (so "is it in nv-rs-pad?" is answered by looking), and one button to bring them all up to date |
| W7 | **Can't see in FOLab what the game shows.** No grass blades, no far trees as the game draws them, no draw count, no water as the game banding shows it, no lip sync | reports: lollipop trees, black bars on plants, 12 fps | The user, every look round | M each. **Draw count** first (S-M): the user's worst problem (12 fps) was invisible until counted by script |
| W8 | **Practice copies left behind.** Scratch homes for experiments (14.5 GB on 20 Nov), one of them once wrote into the real game (15 Nov) | memory notes | Sessions more than the user | S: a "Try it on a copy" that makes the copy on a chosen drive, marks it no-game-writes, deletes it on close |
| W9 | **Undo of big jobs costs memory and time**: each Undo step snapshots cells and records through pickle; a dress job is one step over the whole city | `_snap` | Big worlds | M, with W2 |

## 3. Lessons learned the hard way (to make defaults or checks)

| # | Lesson | What went wrong | Make it | Fix |
|---|------|------|------|-----|
| L1 | **Walk before navmesh** | The guard tower got no mesh up its stairs; the Missouri's wings joined by a 32-wide gap; each find cost a 2.5 h remake | Navmesh asks to walk-check new sets first, shows what wasn't reached | S (with M6) |
| L2 | **Game placement is the truth** | FOLab applied a root turn the game ignores: the wall was built 90° wrong, then "fixed" to look right in FOLab and wrong in the game | Done in `nif`/`hkshape`; keep `tests/test_nifroot.py` | Done |
| L3 | **Count draws before handing a build over** | Waikiki drew 12,693 at the start (the game's busiest place 2,196): 12 fps | A draw count at the camera / per cell in the editor, a health warning past ~4,000 | S-M |
| L4 | **Never write while the game runs; never write the real game from a scratch copy** | An experiment went into the real Data (15 Nov) | `FOLAB_NO_GAME_WRITES`, `game_running()` checks exist; make the scratch copy flag automatic (W8) | S |
| L5 | **Check every copy the game could load** | Yesterday's `Waikiki.esp` in Data played over MO2's (18 Nov) | copies.py; extend to every nv-rs (W6) | S |
| L6 | **Float checks by mesh and collision, not record bounds** | Billboards' OBND said 62 under; boxes counted as roofs; floating shacks reported many times | settleup's way as the one float check, a job and a health line | S |
| L7 | **Each step after ground upwards re-seats what's on it** | Buildings moved by groundfit left roof camps in the air | Big jobs run the seat step after any job that moves ground or buildings, by default | S (in the runner) |
| L8 | **Plants: one model per plant, seated by its own foot, budgeted per cell; low cover as the game's grass** | Clumps floated and leant; 12 fps; grass whole-plant sway; one byte short crashed nv-rs | Already in plantsplit/plantgrass; the budget as a check | S |
| L9 | **Every new world needs: Pip-Boy map, far view, water levels by cell, border** | Blank Pip-Boy map; barren far hills; water panels over beaches | A "world checklist" in health: no ICON, far view older than land, cell water over its own land | S |
| L10 | **Back up before every big job, named for it** | Sessions did it by hand each time ("Waikiki before X") | The runner does it, and prunes (W1) | S |
| L11 | **Keep the user's reports until they see them fixed** | Fixes "ready" were often not in the game | A Reports list per mod in FOLab (text, picture, open/closed by the user) | M, later |
| L12 | **A game building's doors and shut doorways come with it; lent rooms need variety** | see-through doorways; one room behind nine doors | Done (townbuild `shut`, roomvary) | Done |

---

## Ranked: what to build first

Ranked by (how much it hurts) x (how often) / (size), and whether it unblocks the rest.

1. **Backups that look after themselves (W1, L10).** S. Filled C: today. Prune on every new backup (keep the latest 5
   of each kind, one a day for 7 days, total under a cap, default 10 GB), never the newest; a Backups card in Tools with
   sizes, Open folder, Delete. Touches only install.py and a new module.
2. **Two writers, one mod (W3).** S. A lock and a "file changed since loaded" refusal in `Project.save`. Shared code:
   needs the other sessions' OK first.
3. **Big jobs page (M2-M5, W5, L7, L10).** M, built in steps. One runner: pick a job, it backs up, runs in the
   background with a progress bar, lands as one Undo, and offers the follow-ups (seat things, far view, Pip-Boy map).
   First jobs: things floating or sunk, ground upwards, plants seated, Pip-Boy map, guard towers, restyle, loot, far view.
4. **Install status card (W6, L5).** S (the finding is done, the showing isn't). Every place the game could load the mod from (Data, MO2, every nv-rs folder),
   each *current*, *old* or *missing*, one button to bring them all up to date.
5. **Draw count (W7, L3).** S-M. Draws round the camera in the 3D view, and the busiest cells in health.
6. **World checklist in health (L9, M4, L6).** S. Missing Pip-Boy map, far view older than the land, water over land,
   floating things.
7. **Real map panel buttons (M1).** S each. Landmarks, dress, life, hotels on routes that exist.
8. **Navmesh that resumes (W4, L1, M6).** M. Saves per batch, skips cells already current, walk-check first.
9. **Practice copies (W8, L4).** S.
10. **Models page and items (M7, M8, M9).** L. Later.
11. **The mod in parts (W2, W9).** L, risky, shared. Later, and planned with the other sessions.

Proposed now: **1 and 3**, then 4, 5, 6 if the user agrees. 2 after the other sessions agree.
