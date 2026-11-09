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
- **Base level** is the real height that comes out at z 0. The world's water stands there, so for a place on the coast it's sea level (0), and FOLab picks that if the file reaches the sea; inland, it picks just under the lowest ground of the part you've chosen, so there's no sea. (A town cut from a big tile stands on its own ground, not the tile's lowest corner.) Set it higher to flood the valleys.

Rule of thumb: a town is 1 : 1 to 1 : 3; a valley 1 : 5 to 1 : 15; a whole SRTM square (100 km) 1 : 30 to 1 : 60.

**Limits.** More than 4,096 cells (the size of a whole DLC world) gets a warning. FOLab stops at 16,384, or 256 across: the size of the game's own largest world. Each cell takes about 5.6 KB of plugin. Far out-of-range heights also get a warning: the game's own land stays between about -8,000 and 32,000 units.

## How the land is made

- **Heights** are in whole 8-unit steps, on one grid shared by the whole world, so cells meet exactly. Slopes the game's land can't store (a rise of more than 1,016 units in 128 across, nearly a wall) come down from the top; a message says how many points that was when the world is made.
- **Pictures smaller than the land:** where the file has several points to a land point, they're averaged. Where it has fewer, the land is drawn straight between them, so a coarse file looks faceted at real size.
- **Holes in the file:** small ones are filled from the ground round them. Big ones (some files mark the sea this way) become sea bed.
- **Paint:** each slope gets the mix of ground textures the game itself shows at that steepness, learnt from the world you choose under *Weather, paint like*. That world also gives the climate, water and music.
- **Water:** one level for the world at z 0; a cell has water only if some of its ground is under it.

## OpenStreetMap on the world

With the new world open, press **🧭 World tools > Real map**, pick the `.osm` file and press **Read it**. The map shows what's in it, in place. Choose what you want and press **Lay it**: one Undo.

- **Roads** are the game's own road pieces following the real line, the ground settled under them. Motorways down to tertiary roads are on by default; lesser roads and tracks are a tick away. A road piece stays 9 m wide at any scale. Tunnels are left out; bridges are left out too and listed for you, since FOLab doesn't build them.
- **Rivers and lakes** go through the same shaping as **Shape land**: a channel that runs downhill, a basin under its lowest shore. Streams are a tick away. Remember **one water level a cell**: a river steps down cell by cell, and at heavy compression anything else in that cell low enough is under water too. Coastlines aren't used: that's what the base level is for.
- **Buildings** become flat pads at the ground's middle height under them, and a **marker layer**: the outlines, kept in `projects/<mod> maps/layers.json` and shown on the map under **Real map**. Places too small to see at this scale (less than a land point across) go in the layer without a pad.

## Putting up buildings

Once the pads are laid, **World tools > Real map > 🏚 Put up buildings** stands the game's own buildings on them. It's one Undo, and pressing it again only fills plots that have nothing yet.

- **Which buildings:** every building the game stands on its own outdoors: Novac's and Goodsprings' houses, shacks, ranch houses, corner stores, gas stations, offices and apartment blocks, barracks, transmission buildings, the police station and the like, and the mobile homes the game sets upright (closed up, no way in). City-block kit pieces, walls, signs and rubble aren't used. FOLab measures them the first time (about a minute) and keeps what it found.
- **Which one where:** each plot gets the nearest fit for its size and its kind. OpenStreetMap's `building=house` gets a house, `retail` a shop, `industrial` works, `church` or `school` a hall. Plain `building=yes` goes by size. A wide plot takes a row of buildings and a deep one a second row facing the back. A town doesn't get one house over and over: a building gets less likely each time it's used.
- **Generic and landmarks:** most of a town is the game's generic buildings: the ones it uses three times or more, ruined and ordinary as the Mojave's are. Its one-offs (the Prospector Saloon, Nipton's town hall, the Goodsprings schoolhouse, the church) are landmarks. They only go on plots that stand out: a building named in the file, a church, school, police station or other public building, or a very big plot. Each landmark appears once in a world and keeps its plot to itself. Where the game has a building of that very kind, it's chosen: a church gets the church.
- **Facing:** fronts face the nearest road you've laid, where the game had the doors. Lay the roads first: with none, a long side faces out. A plot too narrow on its street side for anything (a trailer lot) is tried side-on, the way a mobile home stands on a real one.
- **On the ground:** each sits on its pad as deep as the game sets it. Nothing goes on a road piece or on another building, and the small things you'd scattered on a plot (plants, rocks) are taken off.
- **Doors** go where the game had them on that building.
- **Navmesh:** characters outside would walk through the new buildings, so FOLab offers to make the navmesh again in the cells they went up in. Say yes, or do it later from World tools.

### Ways in

**Ways in** says how many buildings open: none, a few, about a third (the default), most, or every one that can. A plot that stands out always opens when it can. A building that opens gets its own copy of a place the game itself has behind that same building. A Novac house gets one of Novac's house interiors, a ranch house a ranch's, the church the church's, so the inside always fits the outside. Each copy is a place of your mod's own:

- **Furnished as the game has it:** walls, furniture, clutter, lights and containers to search, with nothing owned and nothing locked.
- **Without the game's story:** its people and creatures, keys, notes, terminals, talking radios, anything switched on by a quest, and anything with a script of its own stay out. A door inside that led somewhere else in the game is locked.
- **Linked both ways:** you arrive just inside the way out, and back outside in front of the building's door.
- **Walkable:** each gets its navmesh, made in the same Undo.
- **Named for what it is:** your world's editor ID with House, Shop, Offices, Works or Hall and a number, shown as the plot's name if the map has one (a church called St Mary is "St Mary"), otherwise as House, Shop and so on. Rename them in Places like any place of your own.

The game has a place behind about 50 of the 86 buildings FOLab uses. The rest stay locked. FOLab makes at most 40 places in one go. A plot that already has its building isn't opened later: Undo and put the buildings up again to change how many open.

Real buildings are often smaller than the game's once the map is compressed. A plot too small for any of the game's buildings is left empty, and the message says how many. At 1 : 1 to 1 : 3 most houses get one. Past about 1 : 5, only the big plots do. Even at 1 : 1, sheds and garages (OpenStreetMap maps them too) are smaller than anything the game has: Goodsprings at real size fills 139 of its 222 outlines.

FOLab needs to know where the height file is on Earth to line this up. SRTM names and most GeoTIFFs say so; GeoTIFFs in degrees, UTM (WGS84, NAD83, ETRS89) or web mercator work. A plain PNG doesn't, so the OSM file's own bounds are taken as the whole picture.

## Ground types

Before you make the world, the panel's **Ground types** section takes a land-cover file: a GeoTIFF of class numbers lying over the same ground as your heights.

| Where to get one | Notes |
|---|---|
| **ESA WorldCover** (esa-worldcover.org) | The whole world, 10 m, in degrees: it lines up with SRTM. |
| **USGS NLCD** (mrlc.gov) | The USA, 30 m, in its own projection. Turn it into your height file's first: `gdalwarp -t_srs EPSG:4326 nlcd.tif out.tif`. |

FOLab recognises these two by their numbers; any other file just shows its numbers, for you to say what each gets. Each class has a row: a **ground texture** from the game's (blank leaves it to the slope), a **set of things** to scatter (plants, rocks, trees or junk: what the game itself placed in the world you take after), and how many a cell. The defaults are guesses, so look through them. FOLab remembers your choices for that kind of file on this computer.

Steep ground stays as the slope says, so grass doesn't climb cliffs. Textures go into the world as it's made; scatter comes straight after as its own Undo, at most 30,000 things (thinned evenly if it would be more). Nothing stands in water.

## What's left to you

Navmesh, distant land, regions and map markers are in **World tools**: FOLab offers them after the land changes. New worlds have no distant land until you make it (**World tools > Far land**). Reach the world in game with a door, or the console: `cow <editor ID> 0 0`.
