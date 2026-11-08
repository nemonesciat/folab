# Tools: looking after your mod

*The **Tools** page: what's wrong with a plugin, the game's load order, where your mod clashes with it, every change you've made, getting a mod ready to share, and merging plugins.*

## Health check

What's wrong with your mod, in plain words, most serious first. **Go there** opens the record or the place. A **fix** appears only where one is safe; each is an undo step like any other, and **Fix everything safe** does them all as one.

| It finds | The fix |
|---|---|
| Links to things that don't exist | Clear the link, or take out a thing of yours whose base is gone |
| Missing meshes and textures | None: go there and pick another, or add the file |
| Changes identical to the game | Take them out |
| Things deleted outright | Disable and sink them (deleting a game's thing can crash saves) |
| Scripts with text but no compiled code | Compile it, when it's a script record and it compiles |
| Doors with no way back, doors to removed doors | None: FOLab can't know where you should arrive. Go there and link them |
| Places with characters and no navmesh; a navmesh out of date | Make one (places inside only) |
| Places with no lights, places nothing leads to, masters nothing uses | For you to judge |

The list at the top also takes a **look** at any plugin in the Data folder. That only reads it, so there are no fixes; **Open it as my mod** works on a copy.

## Load order

The plugins the game loads, top to bottom. When two change the same thing, the lower one wins. Tick to switch one on or off; drag it or use the arrows to move it. Nothing happens until **Save load order**.

- New Vegas goes by the files' **dates**, so moving a plugin gives its file a new date. Its contents aren't touched, and the game's own files keep theirs. Masters always load before plugins.
- Before saving, FOLab keeps a copy of `plugins.txt` and of every date. **Put back an earlier order** restores one.
- **Fix masters** moves each plugin after what it needs, and switches on what it needs.
- **Find conflicts** lists where two switched-on mods say different things about the same thing, who wins, and with **Compare**, how each copy differs from the one before.
- **Look** opens a health check of that plugin.

Close the game first: FOLab won't save the order while it runs.

## MO2 loadout

If you manage your mods with Mod Organizer 2, this is where FOLab meets them. It finds your New Vegas instances, reads a profile, and shows its mods, plugins and what replaces what. If yours is somewhere unusual, give FOLab its folder (the one with `ModOrganizer.ini` in it).

**Work in this loadout** makes that profile what the whole lab loads: its plugins in its order, and each mod's meshes, textures and archives, the same way MO2's virtual folder lays them out. You don't need to start FOLab through MO2. Browse, the 3D view, the Library, the Health check and Mod conflicts all see your mods, and a mod you make can use their things. FOLab remembers the loadout next time; **Back to the plain game** leaves it.

Plugins that are on but can't load are listed with the reason, usually a missing file or a master that's switched off.

**Make a patch:** name it under **Make a patch for this loadout** and press **New patch**, then edit what you like in Browse. What you edit starts from the winning mod's version of it, and your patch needs that mod as a master. The original mods aren't touched.

**Put in MO2** (where the button says Put in game otherwise) saves your patch and adds it to this profile as a mod folder of its own, switched on and loading last. MO2 has to be closed, because it rewrites these lists when it closes. A copy of the profile's lists goes to FOLab's `backups` first. **Take out of MO2** on the My mod page removes it again. FOLab only ever replaces or removes mod folders it made.

**Start FOLab from MO2:** on this page, **Add FOLab to MO2's list** (with MO2 closed) puts it beside MO2's Run button. Close FOLab, choose it there and press **Run**. It opens in the profile MO2 has on, with **Open in game** starting the game with your mods. MO2 is locked while FOLab runs, so **Put in MO2** only saves your patch's folder: close FOLab, press Refresh in MO2 and tick it in both panes.

**Play here** and **Open in game** work in a loadout: they put your mod (and, for Play here, a small mod called FOLab Test) in this profile and start the game through MO2. MO2 has to be closed the first time; once they're on, it can stay open.

**Started from MO2,** Play here, Open in game and Give it to me work too, without changing MO2's mod list. For that one run, your mod and a small plugin called FOLab Play Here go into MO2's virtual folder: your mod's own folder if it's in MO2 already, otherwise MO2's Overwrite. FOLab adds them to the profile's plugin list just long enough for the game to read it. They all come out again when you close FOLab, or use Open in game; if FOLab was cut off, the next time it starts. To keep your mod in MO2 for good, use **Put in MO2**.

While you're in a loadout, saving the load order, xNVSE and Test in game are refused, because they'd change the real game, not your MO2 setup. Change your mods and their order in MO2, then choose the loadout again to see the changes.

A mod that uses another mod's things only opens where that mod is on, and FOLab says which plugin it's missing.

## Mod conflicts

Where your mod clashes with the rest of your load order. For every record your mod has, it finds who else changes it and who wins, then says what you'd notice in the game and what to do. It only reads, until you press a Move button. Pick **A look at** in the list to check any plugin in Data.

The game doesn't merge records: the last plugin's copy is used whole. So:

- **Your change is overwritten**: a later plugin says something else about a field you changed. Compared field by field against the file your record was built on, so a later plugin that keeps your change, or differs only in fields you left alone, is listed as **harmless**, not as a clash.
- **You undo someone else's change**: your copy wins, and it doesn't say what an earlier plugin changed. **Take the copy out** is offered when your copy changes nothing at all.

Most serious first:

| It finds | What you'd see in the game |
|---|---|
| Masters missing, switched off or loading too late | The game won't start, or crashes loading |
| Records someone deleted (you change them, you bring them back, you delete what others change, or a link of yours points at one) | Crashes when the game reaches for them, or things missing |
| Your change overwritten | Their numbers, look or position, not yours |
| A navmesh in the same place | Characters stuck or walking through things; crashes |
| Door links, at either end | The wrong place, or a door that doesn't work |
| Ground that doesn't meet at a square's edge, ground both change | Cracks and cliffs; things floating or sunk |
| Topics more than one mod adds to | Some lines may never be spoken. The game's own add-ons do this to each other |
| Place settings overwritten | Their lighting, water and music, even if they only carried the place |
| Plugins built on yours | Nothing wrong: a patch, most likely |

**Side by side** shows every copy of a record in load order, the differing lines marked. **Load X after Y** moves a plugin: it gives files new dates, like the Load order page, keeps a copy of the old order first, and refuses if a plugin that needs yours would end up loading before it. **Put back an earlier order** on that page restores it. Moving settles every clash with that plugin one way, so read the **By plugin** table first; when neither way will do, a small patch loaded last can carry both changes.

The first run reads each plugin's record headers and keeps them in FOLab's `cache/conflicts`, so later runs only read what changed. If you use a mod manager that keeps plugins outside Data, those plugins can't be seen unless FOLab is started through it; the page says how many weren't checked.

Your unsaved edits count: the open mod is checked as it would be saved. If it isn't in Data yet, it's checked as if installed, loading last. The Health check shows the last result in one line, and **Get ready to share** has a step for it.

## My changes

Every change your mod makes: by place (moved, turned, resized, swapped, removed, new, door links, ground, water, navmesh) and by kind of record. **Go there**, **Put back** one or a whole group, and **Difference** to see what the game has. For an opened plugin, what it already held is listed apart.

## Get ready to share

1. **Check**: what the Health check found.
2. **Clean**: takes out what does nothing, makes deleted things safe.
3. **What players need**: its masters, in plain words. An opened plugin can drop the ones nothing uses.
4. **Its own files**: what your records (and your own meshes) name that the game doesn't have, found loose in Data or in `projects/<your mod> files`, which is laid out like Data. Put anything your records don't name there too, like music. Files that replace the game's own are marked.
5. **Describe it**: author, version, what's new, where to start, credits, permissions. This writes a readme, and text for a mod page.
6. **Make the zip**: saves your plugin and makes a zip in FOLab's `releases` folder, laid out as mod managers expect. **Nothing is uploaded.**

## Merge a plugin

Brings another plugin (one in Data, or another FOLab mod's saved plugin) into yours. **See what it would do** first: what's new, which masters your mod will gain, where the two disagree. Your copy stays unless you tick **Take theirs**.

Every link keeps pointing at the same thing. If the other plugin uses an object ID you already use, its thing gets a new one, so a save that knew it as part of that plugin won't recognise it.

Afterwards the merged plugin **is** your mod, as if you had opened it, so the Undo list starts afresh. A copy of how things were is kept first; **Put back** under Copies kept restores it.

## Masters

A plugin you opened now gains masters when your changes use something from another file: they go after the ones it has, and every link in the file is re-pointed. A plugin that needs another mod opens too, as long as that mod is in Data: it's loaded underneath.
