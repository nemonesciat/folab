# Tools: looking after your mod

*The **Tools** page: what's wrong with a plugin, the game's load order, every change you've made, getting a mod ready to share, and merging plugins.*

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
