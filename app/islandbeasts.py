"""Waikiki's lesser island animals (the user, 23 Nov 2026: "i like all those ideas for fillers"; docs/waikiki-pacing-plan.md):
three of the game's creatures repainted as animals Hawai'i really has, each moving as the game's does (creaturepaint.py,
the Vespid's way):

  mongoose       the giant rat     lowland scrub and town edges        (the small Indian mongoose, brought for the cane rats)
  coconut crab   the radscorpion   rocky shores and beaches            (the robber crab of the Pacific's islands)
  cane toad      the gecko         wet valleys and taro fields         (brought for the cane beetles)

Each is a copy of the game's full record (the levelled ones are templates of it: `GAME`), its own body file beside the
skeleton (NIFZ names bodies there) with its own pictures, its own name, scale, health and level, lower danger than the
Mojave's (`KINDS`). Pictures are painted by body part over the game's own light and shade (`paint_*`).

    pictures(gd, kind)          {name: PIL image}
    files(gd, kind, slug)       {path under Data: bytes}
    creature(gd, kind, slug)    the kind's CREA
"""
import json

# kind: game record, its body, {its picture: our name}, editor ID, shown name, scale, health, level, damage
KINDS = {
    'mongoose': dict(game='NVCrGiantRat', body='meshes\\creatures\\nvgiantrat\\nvgiantrat.nif',
                     pics={'textures\\creatures\\giantrat\\NV_GiantRat.dds': 'body',
                           'textures\\creatures\\giantrat\\NV_GiantRat_g.dds': 'body_g'},
                     edid='FOLabMongoose', name='Mongoose', scale=0.75, health=20, level=2, damage=10),
    'crab': dict(game='CrRadscorpion1Small', body='meshes\\creatures\\radscorpion\\radscorpion.nif',
                 pics={'textures\\creatures\\radscorpion\\Radscorpion.dds': 'body'},
                 edid='FOLabCoconutCrab', name='Coconut Crab', scale=0.4, health=45, level=5, damage=18),
    'toad': dict(game='NVCrGecko', body='meshes\\creatures\\nvgecko\\nvgecko.nif',
                 pics={'textures\\creatures\\gecko\\Gecko_D.dds': 'body',
                       'textures\\creatures\\gecko\\Gecko_Fire_D.dds': 'eye'},
                 edid='FOLabCaneToad', name='Cane Toad', scale=0.6, health=35, level=3, damage=12),
}
BODY = '%s\\folab%s_%s.nif'                     # (the game body's folder, mod, kind: beside the skeleton)
TEX = 'textures\\folab\\%s\\beasts\\%s_%s.dds'  # (mod, kind, picture)


def _np():
    import numpy as np
    return np


def grizzle(p, base, light, dark, seed):
    """Fur of fine light and dark flecks (a mongoose's agouti hairs) over `base`, by texel."""
    np = _np()
    rng = np.random.default_rng(seed)
    r = rng.random(p.shape)
    col = np.zeros(p.shape + (3,), np.float32) + np.array(base, np.float32)
    col[r > 0.72] = light
    col[r < 0.22] = dark
    return col


# ---------- mongoose (on the giant rat: head +y, tail to -y, stands on z 0) ----------

MG_FUR = (138, 112, 76)
MG_LIGHT = (186, 166, 126)
MG_DARK = (82, 62, 40)
MG_FEET = (64, 50, 36)
MG_NOSE = (120, 84, 70)
MG_EYE = (60, 36, 14)


def _rat_parts(pos):
    np = _np()
    x, y, z = pos[..., 0], pos[..., 1], pos[..., 2]
    out = np.full(pos.shape[:-1], 'body', dtype=object)
    out[y > 14] = 'head'
    out[(y < -42) & (np.abs(x) < 5) & (z < 20)] = 'tail'
    out[(z < 5) & (y > -42)] = 'feet'
    out[(y > 34) & (z < 26)] = 'nose'
    return out


def paint_mongoose(gd, pics):
    """{our picture name: PIL image} for the mongoose."""
    np = _np()
    import creaturepaint as cp
    from PIL import Image, ImageFilter
    k = KINDS['mongoose']
    body_pic, glow_pic = list(k['pics'])
    p = cp.Paint(gd, k['body'], body_pic)
    part = _rat_parts(p.pos)
    p.part[p.have] = part[p.have]
    fur = grizzle(p.lum, MG_FUR, MG_LIGHT, MG_DARK, 41)
    # (paler, greyer on the head and the underside; darker down the back's line)
    under = np.clip(-p.face[..., 2], 0, 1)[..., None]
    fur = fur * (1 - 0.25 * under) + np.array((200, 180, 140), np.float32) * 0.25 * under
    p.put(p.have, fur)
    head = p.have & (part == 'head')
    p.mix(head, (170, 150, 118), 0.3)
    tail = p.have & (part == 'tail')
    tip = np.clip((-60 - p.pos[..., 1]) / 20.0, 0, 1)
    p.mix(tail, MG_DARK, tip * 0.8)
    p.put(p.have & (part == 'feet'), MG_FEET)
    p.put(p.have & (part == 'nose'), MG_NOSE)
    g = p.game
    eye = p.have & (g[..., 2] > g[..., 0] + 40) & (g[..., 1] > g[..., 0] + 30)     # (the rat's cyan eye)
    p.part[eye] = 'eye'
    p.put(eye, MG_EYE)
    body = p.picture(keep=0.8)
    # the glow: the rat's cyan eye made a dull amber shine
    gsize = cp.size_of(gd, glow_pic)[0]
    gl = np.zeros(eye.shape + (3,), np.float32)
    gl[eye] = (60, 34, 8)
    glow = Image.fromarray(gl.astype(np.uint8), 'RGB').filter(ImageFilter.GaussianBlur(1.0)).resize((gsize, gsize), Image.LANCZOS)
    return {'body': (body, p.game), 'body_g': (glow, None)}


# ---------- coconut crab (on the radscorpion: claws to -y, the tail up from +y; crabshell.py takes the tail out and
# gives it a carapace) ----------

CR_SHELL = (76, 58, 118)        # (violet-blue back)
CR_RUST = (178, 78, 42)         # (orange-red legs and claws)
CR_JOINT = (196, 192, 204)      # (pale blue-white joints)
CR_UNDER = (206, 180, 146)
CR_TIP = (30, 22, 26)


def _scorp_parts(pos):
    np = _np()
    x, y, z = pos[..., 0], pos[..., 1], pos[..., 2]
    out = np.full(pos.shape[:-1], 'leg', dtype=object)
    shell = (np.abs(x) < 34) & (y > -60) & (y < 115) & (z > 12)
    out[shell] = 'shell'
    out[(y > 96) & (np.abs(x) < 16)] = 'tail'                   # (out of sight: crabshell leaves it out)
    out[(y < -60) & (np.abs(x) > 25)] = 'claw'
    out[(y < -44) & (np.abs(x) > 45)] = 'claw'
    return out


def paint_crab(gd, pics):
    np = _np()
    import creaturepaint as cp
    k = KINDS['crab']
    p = cp.Paint(gd, k['body'], list(k['pics'])[0])
    part = _scorp_parts(p.pos)
    p.part[p.have] = part[p.have]
    blot = cp.space_noise(p.pos, 16.0, 51)[..., None]
    shell = np.array(CR_SHELL, np.float32) * (1 - 0.55 * blot) + np.array(CR_RUST, np.float32) * 0.55 * blot
    rust = np.array(CR_RUST, np.float32) * (0.85 + 0.3 * cp.space_noise(p.pos, 6.0, 52)[..., None])
    col = np.where(np.isin(part, ['shell', 'tail'])[..., None], shell, rust)
    under = np.clip(-p.face[..., 2], 0, 1)[..., None]
    col = col * (1 - 0.7 * under) + np.array(CR_UNDER, np.float32) * 0.7 * under
    p.put(p.have, col)
    # pale joints: where the game's picture is darkest in a leg's seams, lighter bands
    joints = p.have & np.isin(part, ['leg', 'claw']) & (cp.space_noise(p.pos, 4.0, 53) > 0.78)
    p.mix(joints, CR_JOINT, 0.55)
    tips = p.have & (part == 'claw') & (p.pos[..., 1] < -128)
    p.put(tips, CR_TIP)
    tips = p.have & (part == 'leg') & (p.pos[..., 2] < 6)
    p.put(tips, CR_TIP)
    sting = p.have & (part == 'tail') & (p.pos[..., 2] > 120) & (p.pos[..., 1] > -40)
    p.put(sting, CR_TIP)
    return {'body': (p.picture(keep=0.75, sheen=0.1), p.game)}


# ---------- cane toad (on the gecko: upright, face +y, the tail to -y) ----------

TD_BACK = (112, 94, 58)
TD_DARK = (64, 50, 30)
TD_WART = (150, 120, 72)
TD_BELLY = (220, 204, 158)
TD_MOTTLE = (120, 104, 80)
TD_GLAND = (184, 150, 76)
TD_EYE = (196, 150, 54)


def paint_toad(gd, pics):
    np = _np()
    import creaturepaint as cp
    from PIL import Image
    k = KINDS['toad']
    body_pic, eye_pic = list(k['pics'])
    p = cp.Paint(gd, k['body'], body_pic)
    x, y, z = p.pos[..., 0], p.pos[..., 1], p.pos[..., 2]
    fy, fz = p.face[..., 1], p.face[..., 2]
    front = (fy > 0.3) & (z > 18) & (z < 68) & (y > -25)    # (chest and belly face forward on an upright gecko)
    p.part[p.have] = 'skin'
    blot = cp.space_noise(p.pos, 7.0, 61)[..., None]
    col = np.array(TD_BACK, np.float32) * (1 - 0.6 * blot) + np.array(TD_DARK, np.float32) * 0.6 * blot
    # warts: raised bumps, pale-topped, each ringed dark
    w = cp.space_noise(p.pos, 1.3, 62)
    col[w > 0.66] = np.array(TD_DARK, np.float32) * 0.8
    col[w > 0.76] = TD_WART
    p.put(p.have, col)
    belly = p.have & front
    mottle = cp.space_noise(p.pos, 3.0, 63)[..., None]
    p.put(belly, np.array(TD_BELLY, np.float32) * (1 - 0.45 * (mottle > 0.62)) + np.array(TD_MOTTLE, np.float32) * 0.45 * (mottle > 0.62))
    p.part[belly] = 'belly'
    # the bony ridges over the eyes and the head's frills dark
    ridge = p.have & (z > 84) & ~belly
    p.mix(ridge, TD_DARK, 0.5)
    # the parotoid glands: a swollen pale oval each side behind the eyes
    for side in (1, -1):
        c = np.array([side * 12.0, 14.0, 84.0])
        d = ((p.pos - c) / np.array([6.0, 8.0, 5.0])) ** 2
        gland = p.have & (d.sum(axis=-1) < 1.0) & ~belly
        p.put(gland, TD_GLAND)
        p.part[gland] = 'gland'
    out = {'body': (p.picture(keep=0.5, sheen=0.05), p.game)}
    # the eye: the gecko's fire-orange eye picture made gold with a level black pupil
    e = cp.game_picture(gd, eye_pic)
    lum = e[..., :3].mean(axis=2, keepdims=True) / 255.0
    eye = np.array(TD_EYE, np.float32) * (0.4 + 1.0 * lum)
    out['eye'] = (Image.fromarray(np.clip(eye, 0, 255).astype(np.uint8), 'RGB'), None)
    return out


PAINTERS = {'mongoose': paint_mongoose, 'crab': paint_crab, 'toad': paint_toad}


def pictures(gd, kind):
    """{our picture name: (PIL image, the game picture's RGBA when its alpha is kept, else None)}."""
    return PAINTERS[kind](gd, None)


def files(gd, kind, slug, made=None):
    """{path under Data: bytes}: the kind's body (the game's with its pictures changed) and its pictures."""
    import creaturepaint as cp
    import nifwrite
    k = KINDS[kind]
    made = made or pictures(gd, kind)
    data = gd.read_file(k['body'])
    old = {t['path'] for t in nifwrite.textures_in(data)}
    swap, out = {}, {}
    for game_p, ours in k['pics'].items():
        was = next(p for p in old if nifwrite.key(p) == nifwrite.key(game_p))
        new = TEX % (slug, kind, ours)
        swap[was] = new
        img, alpha = made[ours]
        out[new] = cp.dds_of(img, alpha_from=alpha if alpha is not None and (alpha[..., 3] < 250).any() else None)
    if kind == 'crab':
        import crabshell
        data = crabshell.body(gd)
        out.update(crabshell.files(gd, slug))
    out[BODY % (k['body'].rsplit('\\', 1)[0], slug, kind)] = nifwrite.retexture(data, swap)
    return out


def body_paths(kind, slug):
    """Every body file in the kind's model list (NIFZ): its body, and the crab's shell and cap."""
    if kind == 'crab':
        import crabshell
        return [body_path(kind, slug), crabshell.SHELL % slug, crabshell.CAP % slug]
    return [body_path(kind, slug)]


def body_path(kind, slug):
    k = KINDS[kind]
    return BODY % (k['body'].rsplit('\\', 1)[0], slug, kind)


def put_files(gd, pr, kinds=None):
    import library
    root = library.assets_dir(pr)
    done = []
    for kind in kinds or KINDS:
        for rel, data in files(gd, kind, library.slug(pr.name)).items():
            library._put(root, rel, data)
            done.append(rel)
    return sorted(done)


# ---------- records ----------

def _game(gd, tag, edid):
    got = [f for f, (_i, r) in gd.forms.items() if r.tag == tag and gd.edid(f) == edid]
    if not got:
        raise ValueError('the game has no %s %s' % (tag, edid))
    return min(got, key=lambda f: f >> 24)


def creature(gd, kind, slug):
    """The kind's CREA: the game's full record with its own body, name, scale, health, level and bite."""
    import recordio
    k = KINDS[kind]
    rec = json.loads(json.dumps(recordio.load(gd, _game(gd, 'CREA', k['game']))))
    rec['src'] = ''
    for s in rec['subs']:
        if s['tag'] == 'EDID':
            s['value'] = k['edid']
        elif s['tag'] == 'FULL':
            s['value'] = k['name']
        elif s['tag'] == 'NIFZ':
            s['value'] = '\0'.join(p.rsplit('\\', 1)[1] for p in body_paths(kind, slug)) + '\0'
        elif s['tag'] == 'BNAM':
            s['fields'][0]['value'] = k['scale']
        elif s['tag'] == 'DATA':
            for f in s['fields']:
                if f.get('name') == 'Health':
                    f['value'] = k['health']
                elif f.get('name') == 'Damage':
                    f['value'] = k['damage']
        elif s['tag'] == 'ACBS':
            for f in s['fields']:
                if f.get('name') == 'Level':
                    f['value'] = k['level']
    return rec
