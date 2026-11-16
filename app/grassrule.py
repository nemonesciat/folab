"""Where the game will stand grass on a piece of land: its rule, as code, so that paint can be checked before anyone
has to play it.

The rule (read out of the game's grass-table build and placement by another session; T is an INI threshold whose
default is not known here, 0.3 in earlier games of the engine):

  a quarter of a cell has 16 samples, at the points x, y in {2, 6, 10, 14} of its 17 x 17. A sample looks only at
      the 3 x 3 points round it (so rows and columns 0, 4, 8, 12, 16 are never read);
  a LAYER whose texture carries grass is skipped for a sample unless its strength is over 0.1 at one of the nine;
      then each of the nine weighs the grass's density where the layer's strength there is over T, else nothing;
  a BASE whose texture carries grass weighs the density at each of the nine where one minus the sum of every layer's
      strength there is over T: a grassy base grows through anything thin or faded laid over it, a road included;
  per kind of grass, if the nine weights' mean is under T all nine are nothing;
  the nine weights are spread evenly over a patch 512 units square centred on the sample (so a grassy point puts
      blades up to two points beyond itself), and blades are scattered by that, each moved at random by up to the
      grass's own spacing;
  every texture in the quarter adds its grass by itself: nothing wins.

`predict` gives, for a quarter, how thick grass will stand at each of its 17 x 17 points (densities as parts of 1,
summed over kinds). Slope and water limits (the GRAS record's own) are left out: they only ever take grass away.
Two tries at green ground were wrong in the game before this was known (grass on the roads and the beach); a step
that lays grass-bearing ground is now held to this (greenground.py, tests/test_modelmake.py)."""

T = 0.3
SAMPLES = (2, 6, 10, 14)
Q = 17


def densities(gd, pr=None):
    """A function: LTEX key -> [density of each grass it carries, as parts of 1] ([] for one that grows nothing)."""
    import recordio
    seen = {}

    def of(key):
        if key not in seen:
            out = []
            try:
                rec = pr.records.get(key) if (pr is not None and key.startswith('+')) else recordio.load(gd, gd.from_key(key))
                for s in (rec or {}).get('subs', ()):
                    if s['tag'] == 'GNAM' and s.get('value'):
                        g = recordio.load(gd, gd.from_key(s['value']))
                        d = next((x for x in g['subs'] if x['tag'] == 'DATA'), None)
                        dens = next((f['value'] for f in (d or {}).get('fields', ()) if f.get('name') == 'Density'), 0)
                        out.append(dens / 100.0)
            except Exception:
                out = []
            seen[key] = out
        return seen[key]
    return of


def predict(quarter, dens, t=T, only=None):
    """How thick grass stands at each of a quarter's 289 points. quarter: {'bkey', 'layers': [{'key', 'a'}]} (land.py's
    form); dens: `densities`' function. only: count just these textures' grass (to see what one step added)."""
    out = [0.0] * (Q * Q)
    layers = [(l['key'], l['a']) for l in quarter['layers'] if l.get('key')]
    base = quarter.get('bkey')
    grassy = [(key, a) for key, a in layers if dens(key) and (only is None or key in only)]
    base_d = dens(base) if base and (only is None or base in only) else []
    if not grassy and not base_d:
        return out
    for sy in SAMPLES:
        for sx in SAMPLES:
            nine = [(sy + dy) * Q + sx + dx for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
            total = [0.0] * 9
            for key, a in grassy:
                op = [a[n] for n in nine]
                if max(op) <= 0.1:
                    continue
                for d in dens(key):
                    w = [d if o > t else 0.0 for o in op]
                    if sum(w) / 9.0 >= t:
                        total = [u + v for u, v in zip(total, w)]
            if base_d:
                clear = [1.0 - sum(a[n] for _k, a in layers) for n in nine]
                for d in base_d:
                    w = [d if c > t else 0.0 for c in clear]
                    if sum(w) / 9.0 >= t:
                        total = [u + v for u, v in zip(total, w)]
            if not any(total):
                continue
            # spread over the patch: the 3 x 3 stretched to the 5 x 5 points from two before the sample to two after
            for py in range(-2, 3):
                for px in range(-2, 3):
                    fx, fy = px / 2.0 + 1.0, py / 2.0 + 1.0          # where in the 3 x 3 (0 to 2)
                    ix, iy = min(1, int(fx)), min(1, int(fy))
                    tx, ty = fx - ix, fy - iy
                    v = (total[iy * 3 + ix] * (1 - tx) + total[iy * 3 + ix + 1] * tx) * (1 - ty) \
                        + (total[(iy + 1) * 3 + ix] * (1 - tx) + total[(iy + 1) * 3 + ix + 1] * tx) * ty
                    n = (sy + py) * Q + sx + px
                    if v > out[n]:
                        out[n] = v
    return out
