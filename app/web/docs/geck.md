# FOLab and the GECK

*Using both on the same mod: what is safe, what to watch for, and what each can do that the other can't.*

The GECK is Bethesda's own editor for New Vegas. FOLab writes the same kind of file (.esp and .esm), so a mod can go back and forth. This page says plainly where that works and where it doesn't.

**How this page was made:** every command and window of the GECK was listed from the program itself (225 menu commands, 181 windows) and matched against FOLab. FOLab's files are checked against the game's own: record layouts against every record of each type, and outside cells against every outside cell the game has. **What is not done yet: opening FOLab's files in the GECK itself and trying each thing.** Until that is done, lines below marked *(not tried in the GECK)* are FOLab's best knowledge, not proof.

## Before you open a FOLab mod in the GECK

| Watch for | What happens | What to do |
|---|---|---|
| **A world made by FOLab** | A tester reported the GECK crashing when cells of a FOLab world load. Tried here in the GECK with a real-map world and a plain new world as test 14 wrote them: both opened and drew, no crash; so did a new world as this FOLab writes it. So the cause isn't known yet. | If it happens to you, please report it with the plugin (**Help › Report a problem**). Saving the mod once in this FOLab also rewrites its land and cells exactly the way the game's own are laid out, which can only help. |
| **More than one master** | The plain GECK refuses to load a plugin with more than one master. A FOLab mod that uses anything from a DLC has more than one. | In `Documents\My Games\FalloutNV\GECKCustom.ini`, under `[General]`, set `bAllowMultipleMasterLoads=1`. |
| **A master that is an .esp** (a patch made in an MO2 loadout over another mod) | The plain GECK drops .esp masters when it saves, and everything the mod took from them breaks. | Don't save such a mod in the plain GECK. GECK Extender (from Nexus) keeps .esp masters. |
| **Scripts that use xNVSE or JIP commands** | FOLab compiles these itself, xNVSE's own language included (`let`, arrays, strings, loops, user functions), to the same bytes; only a function written inside a line it can't. The GECK knows none of them unless it is started through xNVSE (`nvse_loader.exe -editor`): started plainly, it can't compile them and may save the script empty. | Start the GECK through xNVSE, or don't recompile those scripts there. |
| **Your own new game** | FOLab writes its marker, quest and script again whenever you change the card. Changes made to them in the GECK are lost the next time. | Change the card in FOLab, not those three things in the GECK. |

## After you save in the GECK

**FOLab does not see what the GECK changed.** A FOLab mod is a list of your changes kept in `projects`; **Save** writes the plugin from that list. If you then edit the plugin in the GECK and save, FOLab's list knows nothing of it, and FOLab's next Save writes the plugin without the GECK's changes.

To bring GECK work back: on **My mod**, **Open a plugin as your mod** and pick the file the GECK saved. Everything in it is kept exactly, and you go on from there. Take the GECK's file, not the one in FOLab's `build` folder.

The GECK also rewrites some things of its own accord when it saves (it finalises navmeshes its own way, rebuilds its tables for worlds, and sorts records). That is normal, and FOLab reads the result.

## What FOLab writes that the GECK should read as its own

- **Records**: each kind FOLab edits is written in the game's layout, checked by reading every such record of the game and writing it back byte for byte. Anything FOLab doesn't understand in an opened plugin is kept untouched.
- **Outside cells and land**: laid out as every one of the game's is (blocks, compressed land, water on every cell). A new world written this way was opened in the GECK and its cells loaded and drew.
- **Master files (.esm)**: list the placed things, navmeshes and land of other files they change, as the game's DLC files do. Without that list the game ignores those changes; FOLab's earlier versions left it out.
- **Things removed from the game's places** are switched off and sunk, never deleted: the safe way for both.
- **Scripts**: saved with their text and the compiled result, so the GECK shows the text and can compile it again. FOLab's compiler gives the game's own bytes for all but 19 of the game's scripts.
- **Navmeshes** *(not tried in the GECK)*: written with the game's rules for what a plugin must hold. The GECK may want to finalise them again.

## What the GECK does, and where FOLab stands

Where FOLab can't do it, use the GECK, then open the plugin as your mod again.

| GECK | In FOLab |
|---|---|
| **Weather** | Editable in Browse: fog, wind, clouds, thunder, and every sky colour by time of day. One block (the sky's fine settings by hour) is kept as it is and can't be changed. No preview: you see it in the game. |
| **ImageSpace, Lighting templates** | Editable in Browse, all fields. No preview. |
| **ImageSpace modifiers** (fades, blurs over time) | Listed and copyable; their curves can't be edited. |
| **Game settings** (Gameplay › Settings) | Editable in Browse. Only settings some game file already changes are listed; to change another, copy one and give it the setting's exact name. |
| **Sounds, Music types, Media sets, Media location controllers** | Editable in Browse, all fields. |
| **Combat styles, Water types, Actor values, Radiation, Dehydration, Hunger and Sleep stages** | Editable in Browse. A water type's look (its colours and waves) is kept as it is and can't be changed yet. |
| **Static collections, Effect shaders, Debris, Ragdolls, Body part data, Casinos, Load screen types** | Listed, and their names, models and textures can be changed; their main settings can't be edited yet. |
| **Trees, Casino chips, Recipe categories, Menu icons** | Editable in Browse. |
| **Faces**: Export NPC face textures (Ctrl+F4 on an NPC) | FOLab copies the face's numbers but can't paint the face files. New NPCs' faces may not match their bodies until the GECK exports them. FOLab warns on those NPCs. |
| **Distant objects and trees** (World LOD) | FOLab makes distant ground only. xLODGen does the rest. |
| **Local maps** (World › Create Local Maps), **Heightmap editing** of a whole world | Not in FOLab. FOLab shapes land in the 3D view and from real height maps. |
| **Havok sim** to settle things (Run Havok Sim) | **Settle** drops things onto what's under them, without physics. |
| **Text out and in** for translation (File › Export, Import) | Not in FOLab. |
| **Recording voice and lip files** | Not in FOLab. Silent lines need no files. |
| **Version control, BetaComment, render test reports** | Not in FOLab (Bethesda's own studio tools). |
| **Navmesh tests** (cover, dodge, flee, line of sight…) and **cover edges** | FOLab makes and edits navmeshes and checks them; **Test in game** walks them in the real game. No cover editing. |
| **Rooms and portals, occlusion planes, refraction, depth biasing** | Not in FOLab. |
| **Search and replace** across placed things | Right-click a thing: **Swap for…**, **Replace every one here…** and **Select all the … here**, within the place that's open. Nothing across places. |
| **Idle animations and camera paths as trees** | Records editable in Browse; no tree view or preview. |

## What FOLab does that the GECK doesn't

Generated places and vaults from kits, populated and furnished · land, roads and towns from real maps · your own New Game start · Play here, Give it to me, and Test in game · Mod Organizer 2 loadouts and patches · health check with fixes, conflicts against your load order, merging plugins · the Library with thumbnails of every mesh, texture and sound · 200 steps of Undo across everything, kept while the mod is open.

## If the GECK crashes on a FOLab file

Please report it (**Help › Report a problem**) with what you did just before, and the plugin if you can share it. Windows keeps a crash record in `%LOCALAPPDATA%\CrashDumps` that helps find the cause.
