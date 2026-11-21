# Storms for Waikiki: what's possible, and a plan to choose from

21 Nov 2026. Planning only: nothing built, nothing written to Waikiki or any game folder.

What you've agreed (`docs/waikiki-lore-additions.md`): **storms like Morrowind's ash storms, with sideways rain
driven by high wind.** Hurricanes and boats running for Hawaiʻi Kai come **later**. Everything else in that file's
Weather bullet (fog, lightning, sounds, gameplay) is only a proposal, so it shows up below as options for you to pick.

## Waikiki's weather today

Waikiki's air region picks a weather by chance from three of Honest Hearts' Zion weathers:

| Weather | Chance | What it looks like |
|---|---|---|
| Zion Valley (clear) | 70 | sunny, light cloud |
| Zion Valley **rain** | 20 | grey storm clouds, haze, distant thunder, lightning flashes |
| The Narrows | 10 | overcast |

**The rain weather never actually rains in Waikiki.** The game doesn't draw rain from the weather by itself.
Honest Hearts has a script that moves three rain models to wherever the player is while it's raining, and that
script only works above a set height (Zion's valley floor). Waikiki's ground sits near sea level, far below that
height, so you get the dark sky and the thunder with no rain falling. Have you seen that grey, thundery sky with
nothing falling? That's this.

## What the game can do

| Piece | Can New Vegas do it? | How |
|---|---|---|
| Rain falling | **Yes, but only the way Honest Hearts does it.** | Rain models (falling streaks, 3 draws each) kept on the player by a quest script while the storm is on. |
| Rain blowing sideways | **Probably. Needs a look in game.** | Each rain model has a "which way is down" setting for its drops. FOLab can tilt it in a copy of the model. The unknown: the streak pictures may stay upright on screen while they drift sideways. That would look odd, and only seeing it settles it. |
| Clouds racing | Yes | Cloud speeds in the weather record. |
| Grass whipping | Probably | The game passes the weather's wind strength to the grass every frame. Waikiki's low cover is the game's own grass, so it should sway harder. To be checked in the same look. |
| **Palms whipping** | **No, not cheaply** | The game only sways grass (and a kind of tree FOLab can't make). FOLab's palms are still models. Making them move would mean animated palms, which is a big job and costs more to draw. My suggestion: leave this out. |
| Short sight in storms only | Yes | Fog distances in the storm weather. Things are still drawn: the fog only hides them while the storm lasts. Your clear-day view stays as it is. |
| Grey-green fog, darker picture | Yes | The weather's fog colours, plus the game's own screen tints. Dead Money's and Honest Hearts' tints can be used as they are. |
| Lightning and thunder | Yes | Built into the weather record (how often, flash colour, a thunder sound). |
| Wind, rain on roofs | Yes | The game already has wind loops (the Hidden Valley sandstorm, Lonesome Road) and Honest Hearts' rain sounds, indoor ones included. |
| Surf | Already there | From Waikiki's region sounds. |

**In nv-rs:** nv-rs runs the game's own code translated, and its sky, weather, particle, region and script parts are
all translated in full. So everything above should look the same there as in the original game. None of it needs
xNVSE, which nv-rs doesn't have. Not yet proven in either game: the sideways rain and the harder-swaying grass.

**Cost to the frame rate:** small. A rain model is 3 draws against Waikiki's thousands. Fog and tints cost nothing
extra.

## How a storm comes and goes

1. **By chance (the region's list).** Swap Zion's rain in Waikiki's list for a Waikiki storm, at whatever chance
   you like. No script. The game decides when, so a storm can come at any hour and last a few hours.
2. **On a schedule (a quest script).** For example, a storm now and then, building from overcast, a few hours of
   storm, then clearing. It uses the game's own weather commands. FOLab's script compiler already writes them
   (tried today: a storm script compiled cleanly against the game's weathers). Gameplay later (people indoors,
   shops shut) can hang off the same script.

The rain has to be kept on the player by a quest script either way. Option 2 just gives that script more to do.

## Hurricanes (later, as agreed)

This can be done the same way: a season flag in the script, with two sets of boats, each set switched on and off
together. The small boats would vanish from the Flotilla and appear in the Hawaiʻi Kai marina. I've written nothing
more about it, as agreed.

## Gameplay (all proposed, none agreed)

Roughly cheapest first:
- Worse aim in storms: a small effect put on the player while the storm is on.
- People indoors, shops shut: conditions on the people's routines ("if it's raining, stay in"). Each group has to
  be done separately.
- A better chance to sneak.
- Boats kept in.

## First look in nv-rs (21 Nov 2026)

You looked at a test with Honest Hearts' rain leaned 40° and twice as heavy. **It looked like normal rain.** Leaning
the drops doesn't read as sideways: each drop is a small upright streak and lives only about half a second. The test
files came out of nv-rs-pad the same sitting, along with nv-rs's own built copies of them.

**What comes next: storms the way Morrowind makes its ash storms.** Morrowind's storm is clouds of soft puffs blown
sideways past you on the wind, with a thick tinted haze and a howling wind loop. New Vegas can do the same thing:
- A storm model of FOLab's own, made from the game's particle rain. Its puffs are thrown out sideways, fast, from
  upwind of you, rather than falling, and kept on you by the same script.
- The puffs use soft pictures the game already has (spray, mist, smoke wisps), tinted grey-green.
- Round puffs look the same from every side, so they read as blowing whichever way you face. That is where the
  leaned rain failed.
- The game's own storm-wall models (Hidden Valley's and Lonesome Road's sandstorms), re-pictured, are kept for later
  if the puffs alone aren't enough.

Cost: a few draws, like the rain. Second look: about 1½ hours to build, then 10 minutes for you.

**Second look (21 Nov):** "the right idea, the effect needs refinement: large white orbs; it needs to be like a
hurricane." The game's spray picture was too big, too white and too round. A third test (on D:\FOLab-weather3) uses
two pictures of FOLab's own instead, both grey and faint, with edges that fade to nothing:
- sheets of driven rain: many small streak cards, very fast, falling a little as they blow;
- torn grey scud sweeping low through them.

Its fog is closer and darker too (about 6,500 units by day).

**Third and fourth looks (21 Nov):** test 3's streaks flew straight at you whenever you faced the wind, which was
fixed from the west. Test 4 turns the wind with your view, so the rain always sweeps across the screen from left to
right, and slants its streaks to match the way the drops fall. The user: **"it looks a lot closer. good work."** Test 4
is what to build on: `D:\FOLab-weather4`, with its build scripts in `build scripts\`. Every test came out of nv-rs-pad
the same sitting.

What test 4 is:
- a weather of its own (Honest Hearts' Zion rain record with full wind, racing clouds, close dark grey-green fog,
  more lightning, two of Lonesome Road's storm winds and Honest Hearts' rain sound);
- two particle models made from Honest Hearts' rain, with FOLab's own pictures (`folabstormstreaks`,
  `folabstormhaze`): sheets of slanting streaks and low grey scud;
- a quest script that keeps both on the player outdoors and turns them with the player's heading.

Not done yet:
- the frame rate in a storm;
- how a storm comes and goes;
- the storm in the original game.

Watch for: nv-rs reads its mods folder only as it starts. A test copied in while it is starting is missed (it
happened once: check `userdata\logs\launcher.log` for "names made").

## Storms on a schedule (the user's choice, 21 Nov)

One quest script runs the cycle. Each step hands the sky over gradually (the game's SetWeather, with the override):
1. **Calm:** Waikiki's own weathers, by chance as now.
2. **Building:** an overcast sky (Honest Hearts' Narrows weather).
3. **Storm:** FOLab's storm weather, with the sheets of rain and scud kept on you outdoors.
4. **Clearing:** overcast again, then Waikiki's own weathers take over.

Proposed lengths for Waikiki: a storm every 3 to 6 game days at random, building 2 hours, storm 4 to 8 hours,
clearing 2 hours. Only while you are in Waikiki's world. To be settled after the look.

Test 5 (`D:\FOLab-weather5`) runs the same cycle fast so it can be seen in one sitting. In game hours it is calm 2,
building 1, storm 2, clearing 1, and a line on screen names each step. At the game's usual speed a game hour is about
2 minutes.

Later, from the same script: people indoors and shops shut while it storms, and the hurricane season.

**Test 5:** the storm step never came. Its first command was the gradual change to FOLab's storm weather, and the
likely reading is that the change failed and took the rest of that step with it (no rain either).

**Test 6:** the step's own work comes first and the sky change last. If the storm sky isn't current 10 game minutes
in, it is forced. The user: **"i see the storms roll in"**, with the rain, at **53 fps** in the storm on the road out of
Waikiki (screenshot, 21 Nov 07:5x). No on-screen messages showed in nv-rs, so whether the gradual change or the forced
one brought the sky is not known. For the real build, keep the force as the fallback. (`ShowWarning` shows nothing to
the player here: use a message of the mod's own if a line is ever wanted.)

A second screenshot, in the town among the buildings, read **39 fps**. That place's frame rate without the storm is
not known yet: look at the same spot in calm weather before deciding the storm's cost.

**Where (agreed 21 Nov):** storms cover the whole island's world, not the Mojave or the DLC worlds; the rain stops
indoors.
- **The hotels' view worlds [the user wants]:** the storm seen out through the lobby and lookout glass, with no rain
  falling inside. Done by standing the rain emitters outside the glass in those worlds instead of on the player
  (`hotelinside.VIEWS` knows each open piece's frame), the storm sky as everywhere else.
- **A peak [the user wants]:** the storm should reach its full hurricane violence at its height. Proposed: the storm
  step split into rising, peak and easing. At the peak:
  - a darker weather of its own (fog closer, lightning far more often);
  - a second, heavier set of rain sheets switched on;
  - the wind loud.

**Tests 7 and 8 (the peak):**
- Test 7 ran the peak on a game-time schedule. Its storm never came for the user (waiting and waiting). It was loaded,
  but why its timer failed is not found. Note that the console can't name a weather in play: `fw` needs the form
  number (0A000805 there).
- Test 8 starts the storm at load with ForceWeather and runs the cycle on real seconds: storm 60 s, peak 90 s,
  storm 45 s, calm 45 s. The user: **"the hurricanes look pretty good now."**
- The peak is its own weather: fog 20 to 3,200 by day, sky and light darker, lightning about every 18. Over the
  storm's rain it adds a third, flatter and faster layer (`folabstormfury`), plus Hidden Valley's sandstorm roar and
  another Lonesome Road wind.
- `D:\FOLab-weather8` holds test 8 and its build scripts.

For the real build, the schedule is in game time again (days between storms), so the timer that failed in test 7
has to be found and proven first. Plan: ForceWeather only, and a timer checked for waiting and sleeping. Prove it
on a copy with the console's `set timescale` turned up, before the user looks.

**Test 9 (the game-time schedule, fixed; `D:\FOLab-weather9`):**
- Test 7's compiled script was read back line by line. Every jump lands where it should, so the cause is not a bad
  compile.
- What test 8 did and test 7 didn't: let go first of any storm setting a save carried over from an earlier test
  (`ReleaseWeatherOverride`). That is the likely cause, unproven.
- Test 9 is test 6's way of changing the sky (the one whose storms rolled in for the user), with the peak and that
  release at the start.
- A wait or sleep that runs more than 6 hours past a step ends the storm.
- Checked offline: every jump of its compiled script (85 lines, 20 jumps), and its steps simulated over 40 minutes
  of play at the game's speed, a 3-hour wait and a 12-hour sleep included.

Not yet seen in the game. It was put in nv-rs-pad at 09:13 on 21 Nov and taken out the same sitting; the user will look later, after the other sessions' tests. Put it back from `D:\FOLab-weather9` (only nv-rs-pad; take it out after).

## The schedule the user chose (21 Nov 2026)

Their words, relayed: "i want the squalls to be more frequent, since they arent truly destructive what we have now is
fine for the 3-6 day cycle. something like the proposed idea is ok, just so that they don;t pass over too quickly
considering the weait in between". (Real Hawaiian hurricanes are rare: season June to November, the core crossing an
island in hours, with a day or two of squalls round it.)

Reading of it:
- the big storm, with its hurricane peak, stays on the 3 to 6 game day cycle;
- lighter squalls (rain and wind, no peak) come more often in between;
- the big storm lasts long enough not to feel over in a moment after days of waiting, with bands of squalls before and
  after its core.

**Proposed lengths (game time; at the game's usual speed an hour is about 2 real minutes):**

| | How often | How long |
|---|---|---|
| **Squall** | every 1 to 2 days at random, never inside a big storm | 1 to 3 hours: sky building 30 min, squall 1 to 2 hours, clearing 30 min |
| **Big storm** | 3 to 6 days after the last one ended | 31 hours in all (first written as 29: the parts add to 31) |
| ↳ squall bands before | | 6 hours: 2 squalls of about an hour, with a break |
| ↳ building | | 2 hours |
| ↳ storm | | 6 hours |
| ↳ **hurricane peak** | | 3 hours |
| ↳ storm | | 6 hours |
| ↳ squall bands after | | 6 hours, as before it |
| ↳ clearing | | 2 hours |

The core, from building to the last of the storm, is about 17 game hours: some 35 minutes of play, the peak about 6
of them. A squall is about 2 to 6 minutes.

**Sunny periods between [the user: "make sure that we have nice sunny periods between those storm periods so they
don't become excessive"]:**
- **The 3 to 6 days are counted from the end of one big storm to the start of the next,** so each big storm is
  followed by at least 3 days without one.
- **At least 12 sunny hours on each side of every squall.** No squall in the first day after a big storm, and none in
  the half day before its first squall band. In practice that's about one squall a day at most, often fewer.
- **Fair weather is sunny.** Between storms, Waikiki's region gets clear and lightly cloudy weathers only. The Honest
  Hearts rain and overcast now in its list go, since grey skies come from the schedule.
- **The bands round a big storm shrink to 6 hours each side** (12 made it too long against the gaps). That makes the
  big storm 31 game hours in all.

Stormy share of the time, worked out: a big storm 31 hours in every 4½ to 7½ days, about a fifth of the time,
plus squalls at about 1 hour in 20. **Roughly three quarters of the time is fair, mostly sunny.** One switch (the length of
the gap) moves that share up or down later.

**The squall:** a lighter weather of its own.
- Its sky: grey; fog to about 12,000 (the storm's is 6,500); wind strong, not full; thunder rare.
- Its rain: the storm's sheets at about half as many, and no scud.
- Its sound: one wind loop and the rain sound.
- It costs fewer draws than the storm.

What is left before storms go into Waikiki:
- ~~the real lengths~~, ~~the storm only while in Waikiki's world~~, ~~the mod's own records~~: built (below);
- the look in nv-rs (test 10);
- a look in the original game.

## The schedule built (21 Nov 2026, the user: "get the storm schedules dialed in")

`app/stormsched.py` (tests `tests/test_stormsched.py`). Everything the schedule needs for Waikiki is made by `ops` as one
Undo. It hasn't gone into Waikiki yet.

**The lengths, in game time:**
- **A squall:** every 0.9 to 1.8 days after the last one ends. It runs: sky building 30 min, rain 1 to 2 h, clearing 30 min.
  There is none in the first day after a big storm, and none that would end within half a day of one starting.
- **A big storm:** 3 to 6 days after the last one ended; the first one 1½ to 3 days after the schedule starts.
  31 hours, step by step:
  - a squall 1 h, overcast 2 h, a squall 1 h, overcast 2 h;
  - building 2 h (squall sky and rain);
  - storm 6 h;
  - the hurricane peak 3 h;
  - storm 6 h;
  - the same bands after;
  - clearing 2 h.

**How it holds through waiting and sleeping:** each step starts where the last one ended, and the steps are walked one a
frame. A wait or sleep through part of a storm wakes you in the step the storm would be in by then. Through all of it,
you wake to fair weather, and the next storm is counted from when that one would have ended. A step already over shows
nothing while the steps are walked: only the one you wake in does.

**Where:**
- **The island's world:** the sky, and rain on you outdoors.
- **A hotel's small world:** the storm's sky. Its rain stands outside the glass:
  - window rain emitters, turned so the rain runs along each wall, 450 units clear of it;
  - a ring of them at the ground floor and one at the lookout or deck (34 for the three hotels);
  - all switched on and off by one parent marker.
- **Indoors:** no rain.
- **Any other world outdoors** (the Mojave, the DLC worlds): the storm is let go. It comes back at once when you return
  to the island.

**The squall's weather** (`FOLabSquallWeather`): fog to 12,000, wind 190, thunder rare. The storm and peak are tests 8
and 9's. The squall's rain is the storm's sheets at half as many (`folabsquallsheets`).

**Fair weather:** `fair_ops` takes every weather that isn't flagged pleasant out of Waikiki's region. On a copy of
Waikiki it finds the region `FOLabWaikikiAir` and three weathers to take out.

**Proved offline:** the script's own text was run in a small interpreter of the lines it uses (`stormsched.run`). The run
covered 30 game days at the game's usual speed:
- big storms 3.9 to 5.5 days apart, each 31 h;
- squalls 1 to 2 days apart, each 2 to 3 h long with its building and clearing;
- about three quarters of the time fair;
- no sunny spell under 12 h beside a squall, no squall in a storm's quiet day.

Waits, sleeps and other worlds were run too:
- the Mojave in mid-storm lets go of the sky and takes your rain off;
- back on the island the storm is given at once;
- in a hotel world and indoors there is no rain on you;
- after a 12-hour sleep through the peak you wake in the clearing overcast;
- after a 48-hour sleep through a whole storm you wake to fair weather.

The compiled script (3,475 bytes) was read back and every jump lands where it should.

**Test 10** (`D:\FOLab-weather10`; build script in `build scripts\`): the real schedule, with the first big storm half an
hour after loading.
- It's a plugin of its own with Waikiki.esp as a master, for the window rain in the hotels' worlds. Its copies of those
  three worlds and their persistent cells are byte for byte what the installed Waikiki.esp has.
- The region's fair-only change isn't in it, so between storms you may still see the region's old grey skies.
- The look: load a Waikiki save outdoors. About a minute in, the first squall band comes. To see a whole storm sooner,
  `set timescale to 120` in the console (31 h is then about 15 minutes; the peak comes about 7 minutes in), then
  `set timescale to 30` before saving. Walk into a hotel lobby while it rains. After the storm, wait a day: a squall
  comes 1 to 2 days later.
- It goes into nv-rs-pad's mods only on the user's go, after the Waikiki install, and comes out the same sitting.

## My recommendation (first written)

**Step 1: one look in nv-rs (about 1½ hours for me, 10 minutes for you).** On a practice copy on D:, I'd make a
small separate test plugin with:
- a Waikiki storm weather: wind full, clouds racing, close grey-green fog, a dark tint, lightning and thunder, a
  wind loop;
- the rain kept on the player, using **tilted** copies of Honest Hearts' rain models;
- the storm switched on as soon as you load your Waikiki save.

You'd see three things at once:
1. whether the sideways rain looks right;
2. whether the grass whips;
3. whether the fog is too much.

It would go into nv-rs's mods only on your go, and come out again the same sitting. Waikiki itself isn't touched.

**Step 2, after you've seen it:** put the storm into Waikiki.
- By chance at first (simplest), or on a schedule if you'd rather storms came in a set pattern.
- If the tilted rain looks wrong, either straight rain, or FOLab's own sheets of slanted rain round the player
  (about a day's work).

Later, only if you want them: the gameplay pieces, one at a time, and the hurricane season.
