# Land from real maps

*A new worldspace from a real place's heights, and its roads, rivers, lakes and building plots from OpenStreetMap.*

You bring the files. FOLab downloads nothing and never goes online for them.

## What you need

**A height file** (one is enough):

| Kind | Where to get it | Notes |
|---|---|---|
| **SRTM `.hgt`** | NASA Earthdata (earthdata.nasa.gov, free account), the USGS EarthExplorer (earthexplorer.usgs.gov), or viewfinderpanoramas.org | Most of the world at about 30 m or 90 m a point. A `.hgt.zip` is fine. Keep the name (like `N36W116.hgt`): that's how FOLab knows where it is. |
| **GeoTIFF `.tif`** | USGS National Map (apps.nationalmap.gov/downloader) for the USA; OpenTopography (opentopography.org); Copernicus DEM (dataspace.copernicus.eu); your country's mapping agency | Uncompressed, LZW or Deflate; 16-bit or 32-bit float; strips or tiles. |
| **16-bit PNG** | Terrain tools (World Machine, Gaea, GIMP, Krita), or FOLab's own height map export | No place of its own: you say how big a pixel is and what black and white stand for. |

**OpenStreetMap, if you want roads and water** (a `.osm` file, or `.osm.bz2` / `.osm.gz`; not `.pbf`):

- Small areas: the **Export** tab on openstreetmap.org.
- Bigger ones: the **Overpass** API through overpass-turbo.eu (Export > raw OSM data), or BBBike's extract service (extract.bbbike.org, choose OSM XML).
- A `.pbf` extract (Geofabrik) has to be turned into XML first, for instance with `osmium cat in.osm.pbf -o out.osm`.

OpenStreetMap's data is © OpenStreetMap contributors under the ODbL. If you release a mod made from it, say so in your credits. Height data has its own terms, usually just a credit: check where you got it.

## Making the world

In **Outside**, press **＋ New worldspace…**, then **🗺 From a real map…**. The flat map opens.

1. **Pick the file.** FOLab copies it into its own `maps` folder and shows it shaded on the map, north at the top. Grey ground is what you've left out; blue is under the base level.
2. **Set the scale** (below).
3. **Choose the part you want.** Drag on the map for a rectangle; drag inside it to move it. It snaps to whole cells. Right-drag pans, the wheel zooms.
4. **Read the numbers.** Before anything is made you see the cells, the plugin's size, how long it'll take, and how high the heights run.
5. **Make it.** Your mod is saved and reopened with the new world in it. The map shows it, and every tool outside works on it as on any other land.

**Undo** takes the whole world away again, back to your mod as it was, as long as you haven't changed anything in it since. Once you have, **World tools > Real map > Go back to before this world** still can, but what you've done since goes with it. (Only the latest world can be taken back like this.)

## Scale: the main decision

A cell is 4,096 units, about **58 m**, so **1 km is about 17 cells**. The Mojave in the game has about 16,000 cells, which at real size would be a square 7.5 km across. A real county won't fit.

- **Size** is how much real ground goes in the same space. At **1 : 10**, 10 m of the real place become 1 m in the game: a cell holds 585 m, and 1 km is 1.7 cells. The whole file comes out about 48 cells across unless you change it.
- **Height ×**: at 1, slopes are as steep as the real ones, whatever the size. So land compressed 1 : 30 with height × 1 is a true model, but its hills have shrunk by 30 too, and it feels flat. Fallout's own land is much steeper than the places it stands for. The default goes up with compression: 1.5 at 1 : 3 to 1 : 5, 2 up to 1 : 20, 3 past that.
- **Base level** is the real height that comes out at z 0. The world's water stands there, so for a place on the coast it's sea level (0), and FOLab picks that if the file reaches the sea; inland, it picks just under the lowest ground, so there's no sea. Set it higher to flood the valleys.

Rule of thumb: a town is 1 : 1 to 1 : 3; a valley 1 : 5 to 1 : 15; a whole SRTM square (100 km) 1 : 30 to 1 : 60.

**Limits.** More than 4,096 cells (the size of a whole DLC world) gets a warning. FOLab stops at 16,384, or 256 across: the size of the game's own largest world. Each cell takes about 5.6 KB of plugin. Far out-of-range heights also get a warning: the game's own land stays between about -8,000 and 32,000 units.

## How the land is made

- **Heights** are in whole 8-unit steps, on one grid shared by the whole world, so cells meet exactly. Slopes the game's land can't store (a rise of more than 1,016 units in 128 across, nearly a wall) come down from the top; the numbers tell you how many points that was.
- **Pictures smaller than the land:** where the file has several points to a land point, they're averaged. Where it has fewer, the land is drawn straight between them, so a coarse file looks faceted at real size.
- **Holes in the file:** small ones are filled from the ground round them. Big ones (some files mark the sea this way) become sea bed.
- **Paint:** each slope gets the mix of ground textures the game itself shows at that steepness, learnt from the world you choose under *Weather, paint like*. That world also gives the climate, water and music.
- **Water:** one level for the world at z 0; a cell has water only if some of its ground is under it.

## OpenStreetMap on the world

With the new world open, press **🧭 World tools > Real map**, pick the `.osm` file and press **Read it**. The map shows what's in it, in place. Choose what you want and press **Lay it**: one Undo.

- **Roads** are the game's own road pieces following the real line, the ground settled under them. Motorways down to tertiary roads are on by default; lesser roads and tracks are a tick away. A road piece stays 9 m wide at any scale. Tunnels are left out; bridges are left out too and listed for you, since FOLab doesn't build them.
- **Rivers and lakes** go through the same shaping as **Shape land**: a channel that runs downhill, a basin under its lowest shore. Streams are a tick away. Remember **one water level a cell**: a river steps down cell by cell, and at heavy compression anything else in that cell low enough is under water too. Coastlines aren't used: that's what the base level is for.
- **Buildings** become flat pads at the ground's middle height under them, and a **marker layer**: the outlines, kept in `projects/<mod> map layers.json` and shown on the map under **Real map**, for you to build to later. No building is put up. Places too small to see at this scale (less than a land point across) go in the layer without a pad.

FOLab needs to know where the height file is on Earth to line this up. SRTM names and most GeoTIFFs say so; GeoTIFFs in degrees, UTM (WGS84, NAD83, ETRS89) or web mercator work. A plain PNG doesn't, so the OSM file's own bounds are taken as the whole picture.

## Ground types

**World tools > Real map > Ground types** paints from a land-cover file, such as ESA WorldCover or the USGS NLCD: a GeoTIFF of class numbers in the same place as your heights. Each class has a row saying which of the game's textures it gets, and which set of plants and rocks may be scattered there. The defaults are guesses you can change, and FOLab remembers your table for each mod.

## What's left to you

Navmesh, distant land, regions and map markers are in **World tools**: FOLab offers them after the land changes. New worlds have no distant land until you make it (**World tools > Distant land**). Reach the world in game with a door, or the console: `cow <editor ID> 0 0`.
