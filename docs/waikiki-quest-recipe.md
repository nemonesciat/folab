# How Waikiki's quests are made (the recipe, from the first one)

The first quest, "What the Sea Brought In" (`app/castawayquest.py`, `tests/test_castawayquest.py`), proved FOLab's quest
pipeline end to end. This is what it taught, for every quest after it. Status marks: **[proven]** seen working, **[built]**
made and checked in FOLab but not yet played, **[not yet]** still to do.

## The quest itself

1. **Agree it with the user first,** in plain words: what is asked, where it sends you, how it ends, what you get. Build
   only from `docs/waikiki-story-plan.md` or the user's own words. Where the plan is silent (money, the clue), ask, and
   offer a choice with your pick first.
2. **One builder module a quest** in `app/` (like `castawayquest.py`): `spots(gd, pr)` finds where things go in the mod,
   `ops(gd, pr, where)` returns every op without changing anything, `build(server)` applies them. The test feeds `ops` a
   small stand-in mod, so it never needs Waikiki.
3. **One Undo for the whole quest.** Every `record_new` and `add` takes the next key in order, so reserve them all first
   (`api_quests._reserve`), build the records that name each other, compile the script against them through `extra` (the
   compiler can't find what isn't made yet; placed refs never, so name each ref by its `edid` there), then one
   `server.edit`. `build` checks the keys came out as reserved. **[built]**
4. **Things the quest names are persistent refs with an editor ID** (`extra: {'persistent': True, 'edid': ...}`): objective
   targets (QSTA) and anything the script names. Make a marker of the quest's own where it needs a spot (`ARRIVE` at
   Kuliouou), rather than reusing a map marker another builder made. **[built]**

## How it moves: the quest script does every step

The lines' own result scripts never took effect in the game (the opening, 19 Nov 2026: the first line said, then the same
line again and again). Until that's understood, **no stage change hangs on a line's script.** The quest's own script:
- waits for what comes before (`FOLabCastawayOpening.step == 9`: another quest's variable can be read after it stopped);
- starts each talk itself (`Ref.StartConversation PlayerREF Topic`), when you're near, and asks again if it doesn't come
  within a few seconds of play; [proven by the opening]
- hears the talk was shown (`MenuMode 1009` sets a flag while the talk it asked for is up) and acts in GameMode, which
  only runs again once the dialogue has shut; [proven by the opening]
- watches the world for the rest: `player.GetItemCount` (found it), `player.GetDistance` to a persistent ref (got there);
- shows and completes objectives (`SetObjectiveDisplayed` / `SetObjectiveCompleted`), sets stages for their log entries,
  and ends with `CompleteQuest`. Stage records carry log entries only; the last stage has the complete flag. **[built]**
- Quest delay 0.5 s (DATA's delay) so it answers quickly.

A choice under a line (`choices` = a topic whose FULL is the button's words) works with this: the flag is set whichever
answer is picked. [proven by the opening's four answers]

Worth finding out later: why the result scripts didn't run (FOLab's compiled bytes, or the engine). Once they do, stages
can move from lines the usual way, and this script gets simpler.

## Lines

- **Silent:** TRDT with sound 0, the words in NAM1, empty NAM2/NAM3 (`api_quests.new_line_plain`, `split_responses` cuts
  them into subtitle-sized responses). The game times a line with no voice from its length. **[proven by the opening]**
- Said by one character: the condition GetIsID on its NPC_ (new_line_plain adds it).
- The topics aren't top-level, so they don't turn up in the character's own talk menu; only the script opens them.
- Plain ASCII in anything shown (Kuliouou, not Kuliʻouʻou): the game's fonts may not have the ʻokina. [not checked in game]

## Items, the find and the reward

- Items of the mod's own are copies of the game's (`recordio.load`, new EDID and FULL): the lockbox is the Lunchbox's model,
  the trunk is the game's empty trunk (VLootTrunkGen01) with one CNTO added.
- Where a find stands: `lootplace.Seat`'s solids (`tops`) give real collision. The Hanauma wreck lies all but under the
  water, so the trunk (53 tall) stands on her highest point with its top 27 over the sea.
- **The reward comes from the loot work's lists:** `player.AddItem` of the game's levelled lists that the loot work's kind
  uses for that band (here the duffle bag's LootDuffleBag100 x1 and LootDuffleBag25 x3, kind 'bag', easy band).
- **No caps** until the user decides what Waikiki uses for money (asked 20 Nov 2026; not yet answered).
- A message box (MESG, `newgame._message_record`) for what you see and can't carry; the same thing also comes up in talk,
  in case the box doesn't show in nv-rs. [not yet seen in either game]

## Checks before handing it over

- The test: stages and log entries, objectives aimed at the right persistent refs, the script's SCRO naming everything,
  silent lines with no scripts, the plugin passing health with 0 errors, one Undo taking it all away.
- A rehearsal on a copy of the mod on D: (a FOLAB_HOME of its own, FOLAB_NO_GAME_WRITES): build, save, write, health.
- Agree the save with the story session (it installs: nv-rs, nv-rs-pad, MO2 Default) and any other session writing the mod.
- Played start to finish by the user in nv-rs; the original game if it can be tried.

## Voices later (needs the user's choice; nothing made yet)

The plan: quests start silent, the game's own lines for small talk, maybe real voice actors for the main characters, never
a clone of the game's actors' voices for anything released. When voices come, each line's file goes at
`sound\voice\Waikiki.esp\<voice type>\<quest editor ID>_<topic editor ID>_<line form ID, 8 hex>_<response number>.ogg`
(the game's naming, as its own voice files are laid out; long editor IDs are cut short there, to check against the game's
files when voices are made; the voice type is the speaker's VTYP, the beachcomber's is the prospector's he was copied from), with a `.lip` of the same name
beside it for the lips to move. FOLab can't make `.lip` files yet. TRDT's sound stays 0 for a voiced line too: the game finds
the file by that path.

## People in a scene (from the second quest, `app/kuliouquest.py`)

- People of the quest's own are NPC_ copies of the game's (as the beachcomber: no script, the game's stay-put package),
  placed **off** (`extra.props.disabled`) and switched on by the script once the quest before has sent you there, so
  nobody stands about before their time.
- Someone led away walks on a **travel package**: a copy of the game's VHDYesManDamEndTravelPackage, aimed (PLDT kind 0)
  at a marker of the quest's own, given by `AddScriptPackage`, then switched off once you're well away or after a while.
  **[not yet seen in either game]**
- A scene whose people are dead is passed over, so the quest never sticks.
- Script variable names must not be command names (`ts` is one): use whole words.

## What the first quest still has to show (fill in after the user plays it)

- [ ] The ask comes after the opening's last line, in nv-rs and the original game.
- [ ] Objectives and their compass and map markers show in nv-rs.
- [ ] The trunk can be opened from the water; the message box shows when the lockbox is taken.
- [ ] The talk on coming back; the reward lands in the pack.
- [ ] Reaching Kuliouou completes it; the Pip-Boy lists it under completed.
