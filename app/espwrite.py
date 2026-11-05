"""Writes a project as a New Vegas plugin (.esp or .esm).

A new mod starts from an empty plugin; a mod opened from a plugin (adopt.py) starts from that file, every group and
record of it kept as it was, and the changes are laid over it. What a mod's changes put in: the records it changes or
adds; the cells it touches (each with the game's CELL record, as every plugin that edits a cell must carry); every ref
it moved, turned, rescaled or swapped (a copy of the record with new DATA/XSCL/NAME); every game ref it removed (kept,
but disabled and sunk out of sight: deleting a game ref crashes saves that knew it); its new refs. Form IDs in records
copied from the game are re-pointed from their file's own master list to this plugin's."""
import os
import struct

import plugintree
import recordio
import tes4

FORM_VERSION = 15                       # New Vegas records
HEDR_VERSION = 1.34
INITIALLY_DISABLED = 0x00000800
SUNK_Z = -30000.0
ESM = 0x1

# Subrecords holding form IDs, and where: a list of byte offsets, or 'all' for a plain list of form IDs
FORMID_FIELDS = {
    'REFR': {'NAME': [0], 'XEZN': [0], 'XTEL': [0], 'WMI1': [0], 'XTRG': [0], 'INAM': [0], 'XRDO': [12],
             'XOWN': [0], 'XLOC': [4], 'XAMT': [0], 'XPWR': [0], 'XLTW': [0], 'XDCR': [0], 'XLKR': [0], 'XAPR': [0],
             'XESP': [0], 'XEMI': [0], 'XMBR': [0], 'XNDP': [0], 'XPOD': 'all', 'XLRM': 'all', 'XORD': 'all'},
    'CELL': {'XCLR': 'all', 'XCIM': [0], 'XEZN': [0], 'XCCM': [0], 'XCWT': [0], 'XOWN': [0], 'XCAS': [0],
             'XCMO': [0], 'LTMP': [0]},
}
FORMID_FIELDS['ACHR'] = FORMID_FIELDS['ACRE'] = FORMID_FIELDS['REFR']


class MasterError(ValueError):
    pass


def sub(tag, data):
    if len(data) > 0xFFFF:
        return struct.pack('<4sHI', b'XXXX', 4, len(data)) + struct.pack('<4sH', tag.encode(), 0) + data
    return struct.pack('<4sH', tag.encode(), len(data)) + data


def join(subs):
    return b''.join(sub(t, d) for t, d in subs)


class Writer:
    def __init__(self, gd, project):
        self.gd, self.pr = gd, project
        self.source = project.source_path()
        self.own_name = project.plugin.lower()
        self.masters = []

    # --- form IDs ---

    def local(self, fid):
        """A load-order form ID as this plugin writes it."""
        name = self.gd.names[fid >> 24]
        if name == self.own_name:
            return self.own(fid & 0xFFFFFF)
        if name not in self.mindex:
            raise MasterError('%s uses something from %s, which is not one of its masters (%s). FOLab can\'t add '
                              'masters to a plugin it opened yet.' % (self.pr.plugin, name, ', '.join(self.masters)))
        return (self.mindex[name] << 24) | (fid & 0xFFFFFF)

    def own(self, objid):
        return (len(self.masters) << 24) | objid

    def link(self, key):
        """A form key (a game form's, or '+ID' for one of the mod's own) as this plugin writes it."""
        return self.own(int(key[1:], 16)) if key.startswith('+') else self.local(self.gd.from_key(key))

    def remap_fields(self, plugin_i, tag, subs):
        """Form IDs inside a record copied from the game, from plugin plugin_i's numbering to ours."""
        if self.gd.names[plugin_i] == self.own_name:
            return subs                         # (the opened plugin's own records already number as we do)
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
        """The masters: an opened plugin keeps its own list as it was; a new mod names every game file whose forms it
        uses, in load order."""
        gd = self.gd
        if self.source:
            self.masters = list(tes4.PluginFile(self.source).header['masters'])
            self.mindex = {m.lower(): k for k, m in enumerate(self.masters)}
            return
        used = {0}
        for ckey, c in self.pr.cells.items():
            cell = gd.from_key(ckey)
            used.add(gd.source(cell)[0])
            for rkey, r in c['refs'].items():
                if not rkey.startswith('+'):
                    used.add(gd.from_key(rkey) >> 24)
                    used.add(gd.cell_refs[cell][gd.from_key(rkey)][0])
                if r.get('base') and not r['base'].startswith('+'):
                    used.add(gd.from_key(r['base']) >> 24)
        for key, rec in self.pr.records.items():
            if not key.startswith('+'):
                used.add(gd.from_key(key) >> 24)
            if rec.get('src', '').lower() in gd.names:
                used.add(gd.names.index(rec['src'].lower()))
            for k in recordio.links(rec):
                if not k.startswith('+'):
                    used.add(gd.from_key(k) >> 24)
        for i in list(used):                    # a copied record may name its own file's masters
            for m in gd.plugins[i].header['masters']:
                if m.lower() in gd.names:
                    used.add(gd.names.index(m.lower()))
        order = sorted(used)
        self.masters = [gd.plugins[i].path.replace('\\', '/').rsplit('/', 1)[-1] for i in order]
        self.mindex = {gd.names[i]: k for k, i in enumerate(order)}

    # --- records ---

    def game_cell(self, cell):
        """The game's CELL record for a place, numbered as we write."""
        i, rec = self.gd.source(cell)
        return self.remap_fields(i, 'CELL', list(tes4.iter_subrecords(self.gd.plugins[i].data(rec)))), rec.flags & ~tes4.COMPRESSED

    def new_ref(self, rkey, r):
        subs = [('NAME', struct.pack('<I', self.link(r['base'])))]
        if r.get('s', 1.0) != 1.0:
            subs.append(('XSCL', struct.pack('<f', r['s'])))
        subs.append(('DATA', struct.pack('<6f', *r['p'])))
        flags = tes4.PERSISTENT if r.get('persistent') else 0
        # (a character is placed as an ACHR, a creature as an ACRE, everything else as a REFR)
        btype = (self.pr.records.get(r['base']) or {}).get('type') if r['base'].startswith('+') else             self.gd.forms[self.gd.from_key(r['base'])][1].tag
        tag = {'NPC_': 'ACHR', 'CREA': 'ACRE'}.get(btype, 'REFR')
        return plugintree.Rec.new(tag, flags, self.own(int(rkey[1:], 16)), join(subs), FORM_VERSION)

    def changed_ref(self, subs, flags, r):
        """A ref's subrecords and flags with the mod's change laid over: moved, rescaled, swapped, removed."""
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
                d = struct.pack('<I', self.link(r['base']))
            if t == 'DATA' and p is not None:
                if s is not None and s != 1.0:
                    out.append(('XSCL', struct.pack('<f', s)))
                d = struct.pack('<6f', *p)
            out.append((t, d))
        return out, flags

    # --- the plugin ---

    def build(self):
        self.plan()
        gd = self.gd
        tree = plugintree.Plugin.read(self.source) if self.source else plugintree.Plugin.empty(b'')
        order = gd.plugins[0].top_groups()
        found = {r.formid: (r, parent) for r, parent, _path in tree.records()}

        # records the mod changes or adds (a place's record goes with the place, below)
        for key, rec in sorted(self.pr.records.items()):
            if rec['type'] == 'CELL':
                continue
            fid = self.link(key)
            data = join(recordio.to_bytes(rec, self.link))
            if fid in found:
                found[fid][0].set_data(data, rec['flags'])
            else:
                top = tree.top(rec['type'], order)
                node = plugintree.Rec.new(rec['type'], rec['flags'], fid, data, FORM_VERSION)
                top.kids.append(node)
                found[fid] = (node, top)

        # places: the cell's record, then its refs
        cells = {k for k, c in self.pr.cells.items() if c['refs']}
        cells |= {k for k, r in self.pr.records.items() if r['type'] == 'CELL' and not k.startswith('+')}
        for ckey in sorted(cells):
            cell = gd.from_key(ckey)
            lid = self.link(ckey)
            node, kids = self._cell_node(tree, found, cell, lid, order)
            mine = self.pr.records.get(ckey)
            if mine:
                node.set_data(join(recordio.to_bytes(mine, self.link)), mine['flags'])
            for rkey, r in sorted((self.pr.cells.get(ckey) or {'refs': {}})['refs'].items()):
                if rkey.startswith('+'):
                    group = self._ref_group(kids, lid, bool(r.get('persistent')))
                    ref = self.new_ref(rkey, r)
                    group.kids.append(ref)
                    found[ref.formid] = (ref, group)
                    continue
                fid = gd.from_key(rkey)
                rlid = self.local(fid)
                have = found.get(rlid)
                if have and r.get('removed') and rlid >> 24 == len(self.masters):
                    have[1].kids.remove(have[0])  # (the mod's own ref, removed: gone)
                    del found[rlid]
                    continue
                if have:
                    subs = list(tes4.iter_subrecords(have[0].data()))
                    subs, flags = self.changed_ref(subs, have[0].flags & ~tes4.COMPRESSED, r)
                    have[0].set_data(join(subs), flags)
                else:
                    i, rec = gd.cell_refs[cell][fid]
                    subs = self.remap_fields(i, rec.tag, list(tes4.iter_subrecords(gd.plugins[i].data(rec))))
                    subs, flags = self.changed_ref(subs, rec.flags & ~tes4.COMPRESSED, r)
                    group = self._ref_group(kids, lid, bool(rec.flags & tes4.PERSISTENT))
                    node2 = plugintree.Rec.new(rec.tag, flags, rlid, join(subs), FORM_VERSION)
                    group.kids.append(node2)
                    found[rlid] = (node2, group)

        # the header: an opened plugin's own, with its count and next ID brought up to date
        own_ids = [r.formid & 0xFFFFFF for r, _p, _path in tree.records() if r.formid >> 24 == len(self.masters)]
        next_id = self.own(max([self.pr.next_id] + [x + 1 for x in own_ids]))
        if self.source:
            subs = list(tes4.iter_subrecords(tree.header.raw))
            old = next((d for t, d in subs if t == 'HEDR'), None)
            v, _n, nxt = struct.unpack_from('<fiI', old)
            hedr = struct.pack('<fiI', v, tree.count(), max(nxt, next_id)) + old[12:]
            subs = [(t, hedr if t == 'HEDR' else d) for t, d in subs]
        else:
            subs = [('HEDR', struct.pack('<fiI', HEDR_VERSION, tree.count(), next_id)),
                    ('CNAM', (self.pr.author or 'FOLab').encode('cp1252', 'replace')[:511] + b'\0')]
            if self.pr.description:
                subs.append(('SNAM', self.pr.description.encode('cp1252', 'replace')[:511] + b'\0'))
            for m in self.masters:
                subs += [('MAST', m.encode('cp1252') + b'\0'), ('DATA', b'\0' * 8)]
        flags = (tree.header.flags & ~ESM) | (ESM if self.pr.esm else 0)
        new_head = join(subs)
        if new_head != tree.header.raw or flags != tree.header.flags:
            tree.header.set_data(new_head, flags)
        return tree.bytes()

    def _cell_node(self, tree, found, cell, lid, order):
        """The cell's record in the tree and its children group, both made (as the game files keep them) when the
        plugin doesn't have the cell yet."""
        have = found.get(lid)
        if have and have[0].tag == 'CELL' and have[1] is not None:
            node, parent = have
            at = parent.kids.index(node)
            nxt = parent.kids[at + 1] if at + 1 < len(parent.kids) else None
            if isinstance(nxt, plugintree.Group) and nxt.gtype == tes4.G_CELL_CHILDREN:
                return node, nxt
            kids = plugintree.Group(lid, tes4.G_CELL_CHILDREN)
            parent.kids.insert(at + 1, kids)
            return node, kids
        subs, flags = self.game_cell(cell)
        node = plugintree.Rec.new('CELL', flags, lid, join(subs), FORM_VERSION)
        top = tree.top('CELL', order)
        obj = lid & 0xFFFFFF
        block = self._group(top, obj % 10, tes4.G_INT_BLOCK)
        subblock = self._group(block, (obj // 10) % 10, tes4.G_INT_SUBBLOCK)
        kids = plugintree.Group(lid, tes4.G_CELL_CHILDREN)
        subblock.kids += [node, kids]
        found[lid] = (node, subblock)
        return node, kids

    @staticmethod
    def _group(parent, label, gtype):
        for g in parent.kids:
            if isinstance(g, plugintree.Group) and g.gtype == gtype and g.label == label:
                return g
        g = plugintree.Group(label, gtype)
        parent.kids.append(g)
        return g

    def _ref_group(self, kids, lid, persistent):
        gtype = tes4.G_CELL_PERSISTENT if persistent else tes4.G_CELL_TEMPORARY
        for g in kids.kids:
            if isinstance(g, plugintree.Group) and g.gtype == gtype:
                return g
        g = plugintree.Group(lid, gtype)
        # (persistent before temporary, as the game's files have them)
        kids.kids.insert(0 if persistent else len(kids.kids), g)
        return g


def write(gd, project, path):
    data = Writer(gd, project).build()
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, path)
    return len(data)
