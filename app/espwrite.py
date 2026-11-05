"""Writes a project as a New Vegas plugin (.esp).

What goes in: the cells the project touches (each a copy of the game's own CELL record, as every plugin that
edits a cell must carry), every ref it moved or turned (a copy of the game's record with new DATA/XSCL), every ref
it removed (kept, but disabled and sunk out of sight: deleting a game ref crashes saves that knew it), and every new
ref. Form IDs in copied records are re-pointed from the source file's own master list to this plugin's."""
import struct

import gamedata
import tes4

FORM_VERSION = 15                       # New Vegas records
HEDR_VERSION = 1.34
INITIALLY_DISABLED = 0x00000800
SUNK_Z = -30000.0

# Subrecords holding form IDs, and where: a list of byte offsets, or 'all' for a plain list of form IDs
FORMID_FIELDS = {
    'REFR': {'NAME': [0], 'XEZN': [0], 'XTEL': [0], 'WMI1': [0], 'XTRG': [0], 'INAM': [0], 'XRDO': [12],
             'XOWN': [0], 'XLOC': [4], 'XAMT': [0], 'XPWR': [0], 'XLTW': [0], 'XDCR': [0], 'XLKR': [0], 'XAPR': [0],
             'XESP': [0], 'XEMI': [0], 'XMBR': [0], 'XNDP': [0], 'XPOD': 'all', 'XLRM': 'all', 'XORD': 'all'},
    'CELL': {'XCLR': 'all', 'XCIM': [0], 'XEZN': [0], 'XCCM': [0], 'XCWT': [0], 'XOWN': [0], 'XCAS': [0],
             'XCMO': [0], 'LTMP': [0]},
}
FORMID_FIELDS['ACHR'] = FORMID_FIELDS['ACRE'] = FORMID_FIELDS['REFR']


def sub(tag, data):
    if len(data) > 0xFFFF:
        return struct.pack('<4sHI', b'XXXX', 4, len(data)) + struct.pack('<4sH', tag.encode(), 0) + data
    return struct.pack('<4sH', tag.encode(), len(data)) + data


def record(tag, flags, formid, data):
    return struct.pack('<4sIIIIHH', tag.encode(), len(data), flags, formid, 0, FORM_VERSION, 0) + data


def group(label, gtype, contents):
    if isinstance(label, str):
        label = struct.unpack('<I', label.encode())[0]
    return struct.pack('<4sIIiHHHH', b'GRUP', 24 + len(contents), label, gtype, 0, 0, 0, 0) + contents


class Writer:
    def __init__(self, gd, project):
        self.gd, self.pr = gd, project
        self.masters = []

    # --- form IDs ---

    def local(self, fid):
        """A load-order form ID as this plugin writes it."""
        name = self.gd.names[fid >> 24]
        return (self.mindex[name] << 24) | (fid & 0xFFFFFF)

    def own(self, objid):
        return (len(self.masters) << 24) | objid

    def remap_fields(self, plugin_i, tag, subs):
        """Form IDs inside a copied record, from plugin plugin_i's numbering to ours."""
        fields = FORMID_FIELDS.get(tag, {})
        out = []
        for st, sd in subs:
            where = fields.get(st)
            if where and sd:
                b = bytearray(sd)
                offs = range(0, len(b) - 3, 4) if where == 'all' else [o for o in where if o + 4 <= len(b)]
                for o in offs:
                    v = struct.unpack_from('<I', b, o)[0]
                    if v:
                        struct.pack_into('<I', b, o, self.local(self.gd.to_global(plugin_i, v)))
                sd = bytes(b)
            out.append((st, sd))
        return out

    # --- what the plugin needs ---

    def plan(self):
        """Which game files this plugin must name as masters: every file whose forms it uses, in load order."""
        gd, used = self.gd, {0}
        for ckey, c in self.pr.cells.items():
            cell = gd.from_key(ckey)
            used.add(gd.source(cell)[0])
            for rkey, r in c['refs'].items():
                if not rkey.startswith('+'):
                    used.add(gd.from_key(rkey) >> 24)
                    used.add(gd.cell_refs[cell][gd.from_key(rkey)][0])
                if r.get('base'):
                    used.add(gd.from_key(r['base']) >> 24)
        for i in list(used):                    # a copied record may name its own file's masters
            for m in gd.plugins[i].header['masters']:
                if m.lower() in gd.names:
                    used.add(gd.names.index(m.lower()))
        order = sorted(used)
        self.masters = [gd.plugins[i].path.replace('\\', '/').rsplit('/', 1)[-1] for i in order]
        self.mindex = {gd.names[i]: k for k, i in enumerate(order)}

    # --- records ---

    def cell_record(self, cell):
        i, rec = self.gd.source(cell)
        subs = self.remap_fields(i, 'CELL', list(tes4.iter_subrecords(self.gd.plugins[i].data(rec))))
        return record('CELL', rec.flags & ~tes4.COMPRESSED, self.local(cell), b''.join(sub(t, d) for t, d in subs))

    def ref_record(self, cell, rkey, r):
        """(persistent?, record bytes) for one changed or new ref."""
        gd = self.gd
        if rkey.startswith('+'):
            subs = [('NAME', struct.pack('<I', self.local(gd.from_key(r['base']))))]
            if r.get('s', 1.0) != 1.0:
                subs.append(('XSCL', struct.pack('<f', r['s'])))
            subs.append(('DATA', struct.pack('<6f', *r['p'])))
            flags = tes4.PERSISTENT if r.get('persistent') else 0
            return bool(r.get('persistent')), record('REFR', flags, self.own(int(rkey[1:], 16)),
                                                     b''.join(sub(t, d) for t, d in subs))
        fid = gd.from_key(rkey)
        i, rec = gd.cell_refs[cell][fid]
        subs = self.remap_fields(i, rec.tag, list(tes4.iter_subrecords(gd.plugins[i].data(rec))))
        flags = rec.flags & ~tes4.COMPRESSED
        p, s = r.get('p'), r.get('s')
        if r.get('removed'):
            flags |= INITIALLY_DISABLED
            old = next((d for t, d in subs if t == 'DATA'), None)
            if old:
                v = list(struct.unpack_from('<6f', old))
                p = v[:2] + [SUNK_Z] + v[3:]
        out = []
        for t, d in subs:
            if t == 'XSCL' and s is not None:
                continue
            if t == 'NAME' and r.get('base'):
                d = struct.pack('<I', self.local(gd.from_key(r['base'])))
            if t == 'DATA' and p is not None:
                if s is not None and s != 1.0:
                    out.append(('XSCL', struct.pack('<f', s)))
                d = struct.pack('<6f', *p)
            out.append((t, d))
        return bool(rec.flags & tes4.PERSISTENT), record(rec.tag, flags, self.local(fid),
                                                         b''.join(sub(t, d) for t, d in out))

    def build(self):
        self.plan()
        gd = self.gd
        blocks = {}                             # block -> subblock -> [cell bytes + children group]
        nrec = ngrp = 0
        for ckey in sorted(self.pr.cells):
            c = self.pr.cells[ckey]
            if not c['refs']:
                continue
            cell = gd.from_key(ckey)
            lid = self.local(cell)
            pers, temp = [], []
            for rkey in sorted(c['refs']):
                is_p, data = self.ref_record(cell, rkey, c['refs'][rkey])
                (pers if is_p else temp).append(data)
                nrec += 1
            kids = b''
            if pers:
                kids += group(lid, tes4.G_CELL_PERSISTENT, b''.join(pers))
                ngrp += 1
            if temp:
                kids += group(lid, tes4.G_CELL_TEMPORARY, b''.join(temp))
                ngrp += 1
            obj = cell & 0xFFFFFF
            blocks.setdefault(obj % 10, {}).setdefault((obj // 10) % 10, []).append(
                self.cell_record(cell) + group(lid, tes4.G_CELL_CHILDREN, kids))
            nrec += 1
            ngrp += 1
        body = b''
        if blocks:
            top = b''
            for b in sorted(blocks):
                inner = b''.join(group(sb, tes4.G_INT_SUBBLOCK, b''.join(blocks[b][sb])) for sb in sorted(blocks[b]))
                top += group(b, tes4.G_INT_BLOCK, inner)
                ngrp += 1 + len(blocks[b])
            body = group('CELL', tes4.G_TOP, top)
            ngrp += 1
        hdr = [sub('HEDR', struct.pack('<fiI', HEDR_VERSION, nrec + ngrp, self.own(self.pr.next_id))),
               sub('CNAM', (self.pr.author or 'FOLab').encode('cp1252', 'replace')[:511] + b'\0')]
        if self.pr.description:
            hdr.append(sub('SNAM', self.pr.description.encode('cp1252', 'replace')[:511] + b'\0'))
        for m in self.masters:
            hdr += [sub('MAST', m.encode('cp1252') + b'\0'), sub('DATA', b'\0' * 8)]
        return record('TES4', 0, 0, b''.join(hdr)) + body


def write(gd, project, path):
    data = Writer(gd, project).build()
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    import os
    os.replace(tmp, path)
    return len(data)
