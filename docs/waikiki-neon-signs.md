# Waikiki: neon and better signs (proposal, 21 Nov 2026)

The user's asks (21 Nov, ~09:25): "would like to see more neon lights, maybe some on the hotel signs, would be cool to see
them from a distance glowing thru as storms roll in?" and "is it possible to get better, more stylized signage in
general? text and theme is very simplistic."

Nothing here is in Waikiki yet. The pictures are flat sketches made by FOLab's own painter (`app/signpaint.py`), each
shown three ways: by day, at night, and at night through storm haze. They're not screenshots from the game.

## What the game does (read from its files)

- **The Strip's neon** (the Tops, Gomorrah, the Lucky 38, the Prospector's sign in Goodsprings) is tube-shaped meshes
  with an unlit shader. They glow 4 to 25 times over, coloured by the material's emissive colour, and most are animated
  (chasing, flicker, on and off).
- **Signs that light only their letters** (the Prospector's, the Ultra-Luxe's, the Lucky 38's entrance) use a second
  picture beside the colour one: a glow map, `_g.dds`, black where nothing lights.
- FOLab already makes glowing shapes this way (`nifmake` glow, `waikikiset.lit`). Until now the glow map was the game's
  plain white, so a whole part lit evenly. `signpaint` makes real glow maps, so only the tubes and letters light.
- **No distant model of the game's glows.** Not one `_lod` file carries a glow or an emissive colour, not even the
  Strip's. So "seen from far off" can't be copied from the game: it has to be tried.

## The styles

| Style | For | Picture |
|---|---|---|
| Neon tubes on enamel, tube border, starburst | the Moana, the Kilauea's blade, motels, bars | `sign-hotel-moana.png`, `sign-hotel-kilauea.png`, `sign-sample-cocktails.png` |
| Deco: tall letters, thick uprights and thin crossbars, outline, shadow | the Royal Hawaiian, older shops | `sign-hotel-royal.png` |
| Brush: the sign painter's slanted pen, outline, shadow | surf shops, stalls, painted boards | `sign-sample-surf-shop.png` |
| Chisel: letters carved into koa, painted in | tiki bars, the beach bar | `sign-hotel-tiki.png` |

For comparison, today's: `sign-now-kil_signs.png` (the Kilauea's board) and `sign-now-rh_sign.png` (the Royal Hawaiian's
painted name). Each sign is weathered: chipped enamel, flaking paint, grime, rust.

Still plain: the letters all come from one simple block alphabet, drawn in each style. The real step up, if the user
wants it, is FOLab's own curved alphabets (a script for the neon names, a proper deco face). That is about a day's work.

## Costs (Waikiki is held back by how many pieces it draws)

- A sign picture with a glow map adds no draws: it's the same shape, with a third picture.
- Neon as tube shapes standing off the board (the game's way: you see the glass from the side) adds one draw per colour
  per model. Painted in the picture with a glow map, a tube costs nothing, but looks flat up close. Proposal: hotel names
  as real tubes (about ten in the city), everything else in the picture.
- Lights: none extra. A glow lights itself. Each hotel and motel sign already has one of the game's neon lights for the
  light it spills (`LIGHTS`).
- Animation (flicker, chase) costs a controller per sign. Leave it out at first; a sign or two buzzing on and off later.

## From far off, through a storm

- Inside the loaded cells (about two cells round you, some 8,000 units) the full sign is drawn. The storm session's fog
  ends nearer than that (its test weathers, not in Waikiki yet: storm 6,500 by day and 4,500 at night, hurricane peak
  3,200 and 2,400). So in a storm the far blocks don't come into it: what fog lets you see is the full sign. The game
  fogs glow too, so a lit sign reads to about half the far distance: in a storm about 3,000 by day and 2,200 at night,
  at the peak 1,500 and 1,100. Past that it's a faint smudge. To read from further: bigger, brighter glow (a self-lit
  card, a light beside it), or the storm session holds the fog's far end back a little (it offered).
- On a clear night, beyond the loaded cells the game draws the distant blocks (`lodobj`). Nothing the game ships glows there. **One test in the game
  is needed**: a far block with the hotel names' parts given an emissive colour, seen at night from the beach, in
  nv-rs (which the user plays) and in the original game. If it doesn't glow, a bright far texture still reads lighter
  than the dark city at dusk, but not at night.

## Proposed order

1. Hotel names in neon (Moana, Kilauea, Royal Hawaiian), with glow maps: on a copy, pictures, then the user's go.
2. The far-off glow test (one sign, one install, one look in the game).
3. Every sign picture in the city redone in these styles: motels, shops, kiosks, bars.
4. Own alphabets, if wanted.

## Built (21 Nov 2026, after the user's "these are right")

- **FOLab's own alphabet** (`app/signfont.py`): curved capitals, figures and marks (the ʻokina too), each its own width.
  `signpaint` draws it as neon tubes, deco (thick uprights, thin crossbars, high waist), brush (the slanted pen) and
  chisel (carved and painted). Shaped boards (rounded, arch, shield, arrow, oval), ribbon banners, the shark-tooth
  border, two-tone letters.
- **Pictures** (`app/signart.py`): palms, cocktail umbrellas, a macaw, hibiscus, surfboards, breaking waves, a setting
  sun, tiki faces, a cocktail glass, a bus. Each can be painted or drawn in neon.
- **The city's sign sheets redrawn** (`app/signsheets.py`, put in place of the sets' own by `modelsets._all_sets`): the
  street stalls, the motels (the beach bar's TIKI ROOM among them), the kiosk, the hotel towers' names, the coast's and
  the resort's boards, the Kilauea's blade and CASINO, the tank, and the four historic names. Each keeps its old size
  and layout, so the models are unchanged. Pictures: `signs-*.png` (in the sheets with a second view, the bottom one is
  night).
- **Neon:** `modelsets.neon(name, mult)` is a look whose glow picture (`_g`, signpaint's) lights only the tubes and lit
  letters. The Kilauea's blade (KILAUEA in amber tubes, a tube border, two starbursts) and CASINO (lit), and the Royal
  Hawaiian's and the Moana's names (neon run down their painted deco letters, as channel letters are lit: style
  `deco_tube`). A model the mod already has gets its glow by `nifglow.light_up` (two blocks change: the texture set's
  glow slot, the material's emissive), so nothing else in it changes.
- Into Waikiki: files only (11 sheets, 3 glow pictures, 6 hotel models patched), no records, no navmesh. The distant
  blocks still show the old pictures until lodobj is run again (and the far view doesn't glow: the game test).
