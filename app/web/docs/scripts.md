# Scripts

*Read how the game does things, and write scripts of your own: a door that wants a key, a note that moves a quest on.*

## The page

**On the left**, every script: your mod's first (a green dot is your own, an amber one a game script you changed), then the game's. The search looks at names; tick **Search inside the scripts too** to find any word in their text.

**In the middle**, the script. Everything you type is checked as you go by the same compiler that saves it, and a mistake shows at its line in red, with what's wrong underneath: click that to go there.

**On the right**, help. Put the cursor on a word to see what it is: a command with its parameters and notes, a block, a variable, or the thing an editor ID names. **Where it's used** lists every script that has that word, the game's own too, so you can see how the game uses a command. Below that, every command and block, to search.

## Saving

**Save** (or Ctrl+S in the editor) compiles the script and keeps it in your mod, as one step you can Undo. If the script has a mistake, nothing is saved: the editor keeps your text, the old version stays in your mod, and the line with the mistake is selected. Unsaved text also stays in this browser if the window closes.

Saving only keeps it in your mod's changes, like any other edit. It reaches the game when you **Save** the mod and **Put in game**.

- **A game script**, changed, stays in your mod as your version of it. **Put back as the game has it** takes your version away. Changing one changes it everywhere that script runs.
- **Make a copy** starts a script of your own from any script. The name in its first line is changed for you.
- **What it runs on**: *On a thing* (a door, an item, a character), *On a quest*, or *An effect*. Some commands need the thing spelled out in a quest script (`player.AddItem`, not `AddItem`).
- A script's name is its first line, `scn MyScript`. Changing that line renames it. A name another thing in the game has already is refused.
- Variables keep their numbers when you change a script (a new variable gets a new number; one you take out leaves a gap), so saved games and other scripts that use them stay right.

## Starting from a template

**＋ New script** offers a blank script or a starter in plain words. Say what it needs and it writes the script, then it's an ordinary script to change as you like:

- **A door that needs a key**: only opens for the player if they carry the key. Otherwise it shows your message.
- **An item that does something when worn or held**: runs when the player equips it, and when they take it off.
- **A trigger that shows a message**: shows your message the first time the player walks in. This needs a *trigger box* in the world, which FOLab can't draw yet, so it only works on an activator you already have as a trigger.
- **Picking something up moves a quest on**: when the player takes the item, the quest goes to that stage.

A starter with a message makes the message as well: a record of your own, under **Messages** on the Browse page, named after the script.

## Putting a script on something

A script does nothing until something runs it. Three ways, all the same underneath:

- **What runs it**, the tab on the right of this page: what has the script, and a search to put it on something else. ✕ takes it off.
- **The Script row** on a record on the Browse and Create pages, and under **Selected** in the World page: pick a script, take it off, or ＋ New to write one that goes straight on it.
- An effect script is picked in the base effect's record.

A script goes on the kind of thing, not on one placed in the world, so every door of that kind gets it. To have one door behave differently, make a copy of the door on Create or Browse and place that. Only things that can have a script show the row. A quest takes a quest script; everything else takes one for things.

## What it doesn't do yet

- **xNVSE's commands aren't known**: the compiler knows the commands in the game's own program, so a script using xNVSE's gets "Unknown". Keep such scripts in the GECK for now.
- **Your own placed things have no editor ID**, so a script can't name one (`MyDoorRef.Activate`). Scripts can name the game's persistent references, and any record of yours by its editor ID.
- **Scripts inside a quest's stages or dialogue** aren't edited here.
- **Nothing is proven until the game runs it.** The compiler gives the same bytes as the game's own scripts have (all but a handful that were out of date when the game shipped), but whether your script does what you meant, only the game can say.
