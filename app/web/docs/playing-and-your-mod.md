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

## Your own new game

Making a game, not a mod for the Mojave? **New Game** can start in your world instead of at Doc Mitchell's house.

1. Open the place where the player should wake up, right-click a spot on the floor and choose **This place › Start a new game here**. You'll face the way the view looks. Inside or outside, the game's places or your own.
2. On the **My mod** page, the card **Your own new game** has the rest:
   - **Screens before you play**: name, face and sex, S.P.E.C.I.A.L., tag skills and traits, one after another, the way the game's own Character revision does them. Untick one and the player starts as their record has it.
   - **An opening message**: your own words in a box, once you've arrived and before the screens.
   - **The hour you wake up**, and whether you **start with the Pip-Boy**. The game only lets it be put on while something is open, so it goes on during the last screen (or the message): with no screens and no message you start without it, and the card says so.
   - **What you start with**: gear, S.P.E.C.I.A.L., skills and looks are the player's own record. **Edit the player** opens it on the Characters page; give them what they should carry.
   - **The Mojave's own start, switched off**: Doc Mitchell's opening always (and with it the main quest, which it starts). Also, if you like, the pre-order packs and Courier's Stash (Mojave gear in your pack), and the DLCs' invitations. Switching those off makes the packs or DLCs masters of your mod, so players need them.
3. **▶ Try it** on the card saves, puts your mod in the game and starts it: choose **New** at the menu. The screen stays white until you've arrived.

FOLab makes it from ordinary parts of your mod: a marker where you wake up, a quest that starts with the game, and its script. You'll see them on the Scripts and Quests pages, and FOLab writes them again whenever you change the card. It's one Undo step each time. Untick **A new game starts in my mod** and it all goes.

A save that has met Doc Mitchell (in his house or past it) is left as it is, so your old saves and **Play here** still work with the mod in.

## Game settings

The **Game** page edits New Vegas's own settings (Fallout.ini and FalloutPrefs.ini): fullscreen, window or **borderless** (FOLab makes it when it starts the game), the monitor and resolution, v-sync, field of view, texture filtering, keep running in the background, skip the intro… and every other setting, searchable. FOLab changes only the lines you change, keeps a copy of both files first, and won't save while the game runs.

## If something goes wrong

**Help → Report a problem** copies FOLab's version, the game's files, your mod's state and the last errors, ready to paste into a message.
