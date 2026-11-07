# Playing, and your mod

*Trying changes in the game, saving and sharing your mod, opening existing plugins, and the game's settings.*

## Trying it in game

| Button | What it does |
|---|---|
| **▶ Open in game** | Saves, puts your mod in the game and starts it (Continue or load a save). |
| **▶ Play here** | The same, then loads your newest save and moves you to where the view is looking (right-click a spot to pick it exactly). Works inside and outside. |
| **Give it to me in game** (Create) | Puts an item in your inventory once your save loads. |

Play here and Give need **xNVSE** and **JIP LN NVSE** (My mod page): download xNVSE from its page and FOLab installs it from your Downloads folder; JIP LN comes from its Nexus page. The game is started through xNVSE's loader, or through Steam if you prefer (My mod page).

Close New Vegas before saving into the game: it holds its plugins open while it runs.

## Your mod

- **Save** writes your plugin to FOLab's `build` folder. **Put in game** copies it into the game's Data folder and switches it on (in `plugins.txt`), keeping a copy of anything it replaces in `backups`. **Take it out of the game** removes it.
- **Save as a master** (My mod page) makes it an .esm other mods can build on.
- **Open a plugin as your mod** (My mod page): an existing .esp or .esm as your mod. Everything in it is kept exactly as it was; your changes are laid over it, and it gains any masters they need.
- The **Tools** page checks your mod, handles the game's load order, lists every change and makes a zip to share: see its guide.
- Your mod is a file in `projects`; FOLab keeps 200 Undo steps while it's open.

## Game settings

The **Game** page edits New Vegas's own settings (Fallout.ini and FalloutPrefs.ini): fullscreen, window or **borderless** (FOLab makes it when it starts the game), the monitor and resolution, v-sync, field of view, texture filtering, keep running in the background, skip the intro… and every other setting, searchable. FOLab changes only the lines you change, keeps a copy of both files first, and won't save while the game runs.

## If something goes wrong

**Help → Report a problem** copies FOLab's version, the game's files, your mod's state and the last errors, ready to paste into a message.
