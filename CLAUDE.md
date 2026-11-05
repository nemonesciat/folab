# FOLab

A New Vegas editor in the spirit of Morrowind Workshop (`C:\Users\AMD RYZEN\Desktop\Morrowind Workshop`), which is
the model for style, UI and approach. Python, standard library first, code in `app/`.

## Ground rules

- **Game files are read-only.** Nothing ever writes into the game's `Data` folder; plugins we make are written
  elsewhere and copied in by the user's choice.
- **fnv_decomp is reference only.** `C:\Users\AMD RYZEN\Documents\GitHub\fnv_decomp` (no licence granted). Read it to
  learn how the game works; never copy its code, comments or names into this project. Write our own from understanding.
- **Engine apart from game.** Keep anything that depends on how the game is run (original game vs a possible OpenMW
  or source-port New Vegas: launching, config, scripts, navmesh) behind one small interface.
- Morrowind Workshop stays untouched; copy ideas or code from it, never edit it from here.

## Finding the game

`FOLAB_NV_DATA` overrides the Data folder; otherwise Steam's library folders are searched for app 22380.
Never read from `steamapps\downloading`: open files there make Steam's install fail with "disk write error".
