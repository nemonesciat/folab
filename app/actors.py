"""What a character or creature looks like, as meshes to draw: for a character, its race's body, hands and head, its
hair and eyes, and the apparel it carries (which takes the place of the body parts it covers); for a creature, the
body meshes listed beside its skeleton. Every part is already placed for the others (skinned meshes in their bind
pose, feet at 0), so they're drawn together at the actor's position.

Templates are followed the way the game does for what they give: traits (race, sex, hair, eyes) and inventory for a
character, the model for a creature; a levelled list stands for its first entry."""
import struct

import tes4

FEMALE = 0x1
# template flags (ACBS): which parts come from the template
USE_TRAITS = 0x1
USE_MODEL = 0x40            # (creatures: model and animation)
USE_INVENTORY = 0x100
# body slots (ARMO BMDT)
HEAD, HAIR, BODY, LHAND, RHAND = 0x1, 0x2, 0x4, 0x8, 0x10
HAT = 0x400


def _subs(gd, fid):
    i, rec = gd.source(fid)
    return i, rec.tag, list(tes4.iter_subrecords(gd.plugins[i].data(rec)))


def _fid(gd, i, data, off=0):
    v = struct.unpack_from('<I', data, off)[0]
    return gd.to_global(i, v) if v else None


def _first_in_list(gd, fid, want, depth=0):
    """A levelled list's first entry of the wanted types (lists inside lists followed)."""
    if fid not in gd.forms or depth > 6:
        return None
    i, tag, subs = _subs(gd, fid)
    if tag in want:
        return fid
    if not tag.startswith('LVL'):
        return None
    for t, d in subs:
        if t == 'LVLO' and len(d) >= 8:
            got = _first_in_list(gd, _fid(gd, i, d, 4), want, depth + 1)
            if got:
                return got
    return None


def _template(gd, fid, flag, depth=0):
    """The record a character or creature takes `flag`'s parts from (itself when it doesn't use a template for them)."""
    if depth > 8 or fid not in gd.forms:
        return fid
    i, tag, subs = _subs(gd, fid)
    f = dict(subs)
    flags = struct.unpack_from('<H', f['ACBS'], 22)[0] if len(f.get('ACBS', b'')) >= 24 else 0
    if not (flags & flag) or 'TPLT' not in f:
        return fid
    t = _first_in_list(gd, _fid(gd, i, f['TPLT']), (tag,))
    return _template(gd, t, flag, depth + 1) if t else fid


def _race_parts(gd, race, female):
    """{('head'|'body', index): (model, texture)} for a race and sex."""
    out = {}
    i, _tag, subs = _subs(gd, race)
    part, sex, idx = None, None, None
    for t, d in subs:
        if t == 'NAM0':
            part = 'head'
        elif t == 'NAM1':
            part = 'body'
        elif t in ('MNAM', 'FNAM') and part and not d:
            sex = t == 'FNAM'
        elif t == 'HNAM':
            part = None                         # (the hair and eye lists that follow are something else)
        elif t == 'INDX' and part:
            idx = struct.unpack('<I', d)[0]
        elif t in ('MODL', 'ICON') and part and sex == female and idx is not None:
            m, tex = out.get((part, idx), ('', ''))
            out[(part, idx)] = (tes4.zstr(d), tex) if t == 'MODL' else (m, tes4.zstr(d))
    return out


def _inventory(gd, fid):
    i, _tag, subs = _subs(gd, fid)
    return [_fid(gd, i, d) for t, d in subs if t == 'CNTO' and len(d) >= 4]


def _wear(gd, items, female):
    """[(model, slots)] of the apparel worn: each piece in the order carried, unless a slot it covers is taken."""
    worn, taken = [], 0
    for it in items:
        a = _first_in_list(gd, it, ('ARMO',)) if it in gd.forms else None
        if not a:
            continue
        _i, _t, subs = _subs(gd, a)
        f = dict(subs)
        slots = struct.unpack_from('<I', f['BMDT'])[0] if len(f.get('BMDT', b'')) >= 4 else 0
        model = tes4.zstr(f.get('MOD3' if female else 'MODL', b'')) or tes4.zstr(f.get('MODL', b''))
        if not slots or slots & taken or not model:
            continue
        worn.append((model, slots))
        taken |= slots
    return worn, taken


def parts(gd, fid):
    """{'parts': [{'model', 'tex'}], 'scale'} for a character (NPC_) or creature (CREA) base form."""
    i, tag, subs = _subs(gd, fid)
    f = dict(subs)
    out = []
    if tag == 'CREA':
        src = _template(gd, fid, USE_MODEL)
        si, _t, ssubs = _subs(gd, src)
        sf = dict(ssubs)
        folder = tes4.zstr(sf.get('MODL', b'')).replace('/', '\\').rsplit('\\', 1)[0]
        for name in sf.get('NIFZ', b'').split(b'\0'):
            if name:
                out.append({'model': 'meshes\\%s\\%s' % (folder, name.decode('cp1252')), 'tex': ''})
        scale = struct.unpack('<f', f['BNAM'])[0] if len(f.get('BNAM', b'')) == 4 else 1.0
        return {'parts': out, 'scale': scale}
    traits = _template(gd, fid, USE_TRAITS)
    ti, _t, tsubs = _subs(gd, traits)
    tf = dict(tsubs)
    female = bool(len(tf.get('ACBS', b'')) >= 4 and struct.unpack_from('<I', tf['ACBS'])[0] & FEMALE)
    worn, taken = _wear(gd, _inventory(gd, _template(gd, fid, USE_INVENTORY)), female)
    race = _fid(gd, ti, tf['RNAM']) if 'RNAM' in tf else None
    rp = _race_parts(gd, race, female) if race in gd.forms else {}
    # the race's body parts that nothing worn covers: body, left hand, right hand
    for idx, slot in ((0, BODY), (1, LHAND), (2, RHAND)):
        m, tex = rp.get(('body', idx), ('', ''))
        if m and not taken & slot:
            out.append({'model': 'meshes\\' + m, 'tex': tex and 'textures\\' + tex})
    if not taken & HEAD:
        for idx in (0, 2, 6, 7):                # head, mouth, eyes (teeth and tongue are inside)
            m, tex = rp.get(('head', idx), ('', ''))
            if m:
                out.append({'model': 'meshes\\' + m, 'tex': tex and 'textures\\' + tex if idx == 0 else ''})
        hair = _fid(gd, ti, tf['HNAM']) if 'HNAM' in tf else None
        if hair in gd.forms and not taken & (HAIR | HAT):
            hm = tes4.zstr(gd.fields(hair).get('MODL', b''))
            if hm:
                out.append({'model': 'meshes\\' + hm, 'tex': ''})
    for m, _slots in worn:
        out.append({'model': 'meshes\\' + m, 'tex': ''})
    scale = struct.unpack('<f', f['NAM6'])[0] if len(f.get('NAM6', b'')) == 4 else 1.0
    return {'parts': out, 'scale': scale or 1.0}
