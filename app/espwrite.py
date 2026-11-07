"""Writes a project as a New Vegas plugin (.esp or .esm).

A new mod starts from an empty plugin; a mod opened from a plugin (adopt.py) starts from that file, every group and
record of it kept as it was, and the changes are laid over it. What a mod's changes put in: the records it changes or
adds; the cells it touches (each with the game's CELL record, as every plugin that edits a cell must carry); every ref
it moved, turned, rescaled or swapped (a copy of the record with new DATA/XSCL/NAME); every game ref it removed (kept,
but disabled and sunk out of sight: deleting a game ref crashes saves that knew it); its new refs. Form IDs in records
copied from the game are re-pointed from their file's own master list to this plugin's."""
import os
import struct

import formlinks
import gamedata
import land as landmod
import masterlist
import navbuild
import navmesh
import plugintree
import questrec
import recordio
import refprops
import tes4
import worldrec

FORM_VERSION = 15                       # New Vegas records
HEDR_VERSION = 1.34
INITIALLY_DISABLED = 0x00000800
SUNK_Z = -30000.0
ESM = 0x1

FORMID_FIELDS = formlinks.TABLE         # (where the form links are: formlinks.py has it all)


class MasterError(ValueError):
    pass


def sub(tag, data):
    if len(data) > 0xFFFF:
        return struct.pack('<4sHI', b'XXXX', 4, len(data)) + struct.pack('<4sH', tag.encode(), 0) + data
    return struct.pack('<4sH', tag.encode(), len(data)) + data


def join(subs):
    return b''.join(sub(t, d) for t, d in subs)


class Writer:
    form_version = FORM_VERSION

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
            raise MasterError('%s uses something from %s, which is not one of its masters (%s).' % (self.pr.plugin, name, ', '.join(self.masters)))
        return (self.mindex[name] << 24) | (fid & 0xFFFFFF)

    def own(self, objid):
        return (len(self.masters) << 24) | objid

    def link(self, key):
        """A form key (a game form's, or '+ID' for one of the mod's own) as this plugin writes it."""
        return self.own(int(key[1:], 16)) if key.startswith('+') else self.local(self.gd.from_key(key))

    def remap_fields(self, plugin_i, tag, subs):
        """Form IDs inside a record copied from the game, from plugin plugin_i's numbering to ours."""
        if self.gd.names[plugin_i] == self.own_name and self.masters == getattr(self, 'source_masters', None):
            return subs                         # (the opened plugin's own records already number as we do)
        own = len(self.gd.plugins[plugin_i].header['masters'])
        return formlinks.repoint(tag, subs, own, lambda v: self.local(self.gd.to_global(plugin_i, v)))[0]

    def record_subs(self, rec):
        """A kept record's subrecords as we write it. Decoded links go through link(); the parts no layout reads are
        still in the numbering of the file they came from, so their links are re-pointed from that file's."""
        subs = recordio.to_bytes(rec, self.link)
        src = (rec.get('src') or '').lower()
        raw = {n for n, s in enumerate(rec['subs']) if s['kind'] == 'raw'}
        if not raw or src not in self.gd.names:
            return subs
        if src == self.own_name and self.masters == getattr(self, 'source_masters', None):
            return subs                         # (the opened plugin numbers as we do)
        i = self.gd.names.index(src)
        own = len(self.gd.plugins[i].header['masters'])
        out = [bytearray(d) if n in raw else None for n, (_t, d) in enumerate(subs)]
        for n, o, v in formlinks.values(rec['type'], subs, own):
            if n in raw and v & 0xFFFFFF >= formlinks.BUILTIN_LIMIT:
                struct.pack_into('<I', out[n], o, self.local(self.gd.to_global(i, v)))
        return [(t, bytes(out[n]) if out[n] is not None else d) for n, (t, d) in enumerate(subs)]

    # --- what the plugin needs ---

    def plan(self):
        """The masters: an opened plugin keeps its own list as it was; a new mod names every game file whose forms it
        uses, in load order."""
        gd = self.gd
        kept = None
        if self.source:
            pf = tes4.PluginFile(self.source)
            kept = list(pf.header['masters'])
            pf.close()
        used = {0}
        if getattr(self, 'force_all', False):
            # (every game file: a new world may use any of them later. Not a loadout's mods: it'd need them all.)
            official = {n.lower() for n in gamedata.OFFICIAL}
            used |= {i for i, n in enumerate(gd.names) if n in official}
        for ckey, c in self.pr.cells.items():
            cell = None if ckey.startswith('+') else gd.from_key(ckey)
            if cell is not None:
                used.add(gd.source(cell)[0])
                if cell in gd.ext_cells:
                    used.add(gd.source(gd.ext_cells[cell])[0])
            for rkey, r in c['refs'].items():
                if r.get('tel') and not r['tel']['door'].startswith('+'):
                    used.add(gd.from_key(r['tel']['door']) >> 24)
                if not rkey.startswith('+'):
                    fid = gd.from_key(rkey)
                    used.add(fid >> 24)
                    used.add(gd.cell_refs[gd.ref_cell.get(fid, cell)][fid][0])
                    used.add(gd.source(gd.ref_cell.get(fid, cell))[0])
                if r.get('base') and not r['base'].startswith('+'):
                    used.add(gd.from_key(r['base']) >> 24)
                for k in list(refprops.links(r.get('props') or {})) + worldrec.ref_extra_keys(r):
                    if not k.startswith('+'):
                        used.add(gd.from_key(k) >> 24)
        for ckey in getattr(self.pr, 'water', {}):
            cell = gd.from_key(ckey)
            used.add(gd.source(cell)[0])
            used.add(gd.source(gd.ext_cells[cell])[0])
        for ckey, L in getattr(self.pr, 'land', {}).items():
            cell = gd.from_key(ckey)
            used.add(gd.source(cell)[0])
            used.add(gd.source(gd.ext_cells[cell])[0])
            if cell in gd.land:
                used.add(gd.land[cell][0])
            for q in L['q']:
                for k in [q.get('bkey')] + [l.get('key') for l in q['layers']]:
                    if k:
                        used.add(gd.from_key(k) >> 24)
        for ckey, info in getattr(self.pr, 'cellinfo', {}).items():
            if not ckey.startswith('+'):
                cell = gd.from_key(ckey)
                used.add(gd.source(cell)[0])
                if cell in gd.ext_cells:
                    used.add(gd.source(gd.ext_cells[cell])[0])
            for tag, v in info.items():
                for k in (v if tag == 'XCLR' else [v] if tag in worldrec.CELL_LINKS and v else []):
                    if not k.startswith('+'):
                        used.add(gd.from_key(k) >> 24)
        for ckey, nav in getattr(self.pr, 'navmesh', {}).items():
            if not ckey.startswith('+'):
                used.add(gd.source(gd.from_key(ckey))[0])
                if gd.from_key(ckey) in gd.ext_cells:
                    used.add(gd.source(gd.ext_cells[gd.from_key(ckey)])[0])
            for k in navbuild.keys_used(nav):
                if not k.startswith('+'):
                    fid = gd.from_key(k)
                    used.add(fid >> 24)
                    if fid in gd.ref_cell:                   # (a door's copy needs its place, and its world, numbered too)
                        used.add(gd.source(gd.ref_cell[fid])[0])
        for key, rec in self.pr.records.items():
            if not key.startswith('+'):
                used.add(gd.from_key(key) >> 24)
            if rec.get('src', '').lower() in gd.names:
                used.add(gd.names.index(rec['src'].lower()))
            for k in recordio.links(rec):
                if not k.startswith('+'):
                    used.add(gd.from_key(k) >> 24)
        questrec.plan_masters(gd, self.pr, used)
        for i in list(used):                    # a copied record may name its own file's masters
            for m in gd.plugins[i].header['masters']:
                if m.lower() in gd.names:
                    used.add(gd.names.index(m.lower()))
        order = sorted(used)
        file_name = lambda i: gd.plugins[i].path.replace('\\', '/').rsplit('/', 1)[-1]
        if kept is not None:
            # (what it had stays where it was; anything new it now uses goes after, every link re-pointed in build())
            low = {m.lower() for m in kept} | {self.own_name}
            self.source_masters = kept
            self.masters = kept + [file_name(i) for i in order if gd.names[i] not in low]
            self.mindex = {m.lower(): k for k, m in enumerate(self.masters)}
            return
        self.masters = [file_name(i) for i in order]
        self.mindex = {gd.names[i]: k for k, i in enumerate(order)}

    # --- records ---

    def game_cell(self, cell):
        """The game's CELL record for a place, numbered as we write."""
        i, rec = self.gd.source(cell)
        return self.remap_fields(i, 'CELL', list(tes4.iter_subrecords(self.gd.plugins[i].data(rec)))), rec.flags & ~tes4.COMPRESSED

    def tel(self, r):
        """A door's XTEL as the game writes it: the door it leads to, where you arrive (position, turn), flags."""
        t = r['tel']
        return struct.pack('<I6fI', self.link(t['door']), *[float(v) for v in t['p']], 0)

    def new_ref(self, rkey, r):
        subs = [('NAME', struct.pack('<I', self.link(r['base'])))]
        first, last = worldrec.ref_extra_subs(r, self.link)
        subs += first
        if r.get('xlcm') is not None:                   # (a levelled actor's difficulty: after NAME and XEZN, as the game has it)
            subs.append(('XLCM', struct.pack('<i', r['xlcm'])))
        if r.get('tel'):
            subs.append(('XTEL', self.tel(r)))
        subs += last
        if r.get('s', 1.0) != 1.0:
            subs.append(('XSCL', struct.pack('<f', r['s'])))
        subs.append(('DATA', struct.pack('<6f', *r['p'])))
        flags = tes4.PERSISTENT if r.get('persistent') else 0
        if r.get('props'):
            subs, flags = refprops.apply(subs, r['props'], flags, self.link)
        # (a character is placed as an ACHR, a creature as an ACRE, everything else as a REFR)
        btype = (self.pr.records.get(r['base']) or {}).get('type') if r['base'].startswith('+') else             self.gd.forms[self.gd.from_key(r['base'])][1].tag
        tag = {'NPC_': 'ACHR', 'CREA': 'ACRE'}.get(btype, 'REFR')
        return plugintree.Rec.new(tag, flags, self.own(int(rkey[1:], 16)), join(subs), FORM_VERSION)

    def changed_ref(self, subs, flags, r):
        """A ref's subrecords and flags with the mod's change laid over: moved, rescaled, swapped, removed."""
        p, s = r.get('p'), r.get('s')
        if r.get('removed'):
            flags = (flags | INITIALLY_DISABLED) & ~tes4.DELETED    # (a deleted one, in an opened plugin, comes back sunk)
            old = next((d for t, d in subs if t == 'DATA'), None)
            if old:
                v = list(struct.unpack_from('<6f', old))
                p = v[:2] + [SUNK_Z] + v[3:]
        out = []
        if r.get('props'):
            subs, flags = refprops.apply(subs, r['props'], flags, self.link)
        if r.get('persistent'):
            flags |= tes4.PERSISTENT
        if 'tel' in r:                                  # (a door the mod links: its XTEL replaced, or put in before DATA)
            subs = [(t, d) for t, d in subs if t != 'XTEL']
            at = next((n for n, (t, _d) in enumerate(subs) if t == 'DATA'), len(subs))
            subs = subs[:at] + [('XTEL', self.tel(r))] + subs[at:]
            flags |= tes4.PERSISTENT
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
        if self.source and self.masters != self.source_masters:
            masterlist.grow(tree, self.pr.plugin, self.masters)
        order = gd.plugins[0].top_groups()
        found = {r.formid: (r, parent) for r, parent, _path in tree.records()}

        # records the mod changes or adds (a place's record goes with the place, below)
        for key, rec in sorted(self.pr.records.items()):
            if rec['type'] in ('CELL', 'INFO'):     # (these go with their place and their topic)
                continue
            fid = self.link(key)
            data = join(self.record_subs(rec))
            if fid in found:
                found[fid][0].set_data(data, rec['flags'])
            else:
                top = tree.top(rec['type'], order)
                node = plugintree.Rec.new(rec['type'], rec['flags'], fid, data, FORM_VERSION)
                top.kids.append(node)
                found[fid] = (node, top)
        questrec.write_lines(self, tree, found, order, join)

        # places: the cell's record, then its refs
        cells = {k for k, c in self.pr.cells.items() if c['refs']}
        cells |= set(getattr(self.pr, 'cellinfo', {}))
        cells |= set(getattr(self.pr, 'land', {})) | set(getattr(self.pr, 'water', {}))
        cells |= {k for k, r in self.pr.records.items() if r['type'] == 'CELL'}
        # (a navmesh goes with its place, unless the place itself has been undone away)
        navs = {k: v for k, v in getattr(self.pr, 'navmesh', {}).items() if not k.startswith('+') or k in self.pr.records}
        cells |= set(navs)
        nav_info, nav_links = [], []
        nodes = {}

        def cell_kids(c):
            # (a cell's children group, the cell's record put in the first time; outside, the world's too)
            if c not in nodes:
                nodes[c] = self._cell_node(tree, found, c, self.local(c), order)
            return nodes[c][1]
        for ckey in sorted(cells):
            cell = None if ckey.startswith('+') else gd.from_key(ckey)
            lid = self.link(ckey)
            mine = self.pr.records.get(ckey)
            outside = cell in gd.ext_cells
            if not outside:
                node, kids = self._cell_node(tree, found, cell, lid, order, mine)
                nodes[cell] = (node, kids)
                if mine:
                    node.set_data(join(self.record_subs(mine)), mine['flags'])
            # outside, what stays loaded (persistent) lives in the world's persistent cell
            keep = gd.world_persistent.get(gd.ext_cells[cell]) if outside else None

            def home(fid, persistent):
                c = gd.ref_cell.get(fid, cell) if fid is not None else cell
                return keep if outside and persistent and keep is not None else c
            for rkey, r in sorted((self.pr.cells.get(ckey) or {'refs': {}})['refs'].items()):
                if rkey.startswith('+'):
                    hc = home(None, bool(r.get('persistent')))
                    kids = cell_kids(hc) if outside else nodes[cell][1]
                    group = self._ref_group(kids, self.local(hc) if outside else lid, bool(r.get('persistent')))
                    ref = self.new_ref(rkey, r)
                    group.kids.append(ref)
                    found[ref.formid] = (ref, group)
                    continue
                fid = gd.from_key(rkey)
                rlid = self.local(fid)
                have = found.get(rlid)
                hc = home(fid, False)
                kids = cell_kids(hc) if outside else nodes[cell][1]
                hlid = self.local(hc) if outside else lid
                if have and r.get('removed') and rlid >> 24 == len(self.masters):
                    have[1].kids.remove(have[0])  # (the mod's own ref, removed: gone)
                    del found[rlid]
                    continue
                if have:
                    subs = list(tes4.iter_subrecords(have[0].data()))
                    if r.get('removed') and not any(t == 'DATA' for t, _d in subs):
                        subs = self._restored_ref(fid, rlid) or subs    # (deleted with nothing left in it: from its master)
                    was = have[0].flags
                    subs, flags = self.changed_ref(subs, have[0].flags & ~tes4.COMPRESSED, r)
                    have[0].set_data(join(subs), flags)
                    if flags & tes4.PERSISTENT and not was & tes4.PERSISTENT and have[1] is not None:
                        # (a door linked now: teleport doors live in the cell's persistent group, as the game's do)
                        have[1].kids.remove(have[0])
                        if outside:
                            hc = home(fid, True)
                            kids, hlid = cell_kids(hc), self.local(hc)
                        group = self._ref_group(kids, hlid, True)
                        group.kids.append(have[0])
                        found[rlid] = (have[0], group)
                else:
                    i, rec = gd.cell_refs[gd.ref_cell.get(fid, cell)][fid]
                    subs = self.remap_fields(i, rec.tag, list(tes4.iter_subrecords(gd.plugins[i].data(rec))))
                    subs, flags = self.changed_ref(subs, rec.flags & ~tes4.COMPRESSED, r)
                    if outside and flags & tes4.PERSISTENT:
                        hc = home(fid, True)
                        kids, hlid = cell_kids(hc), self.local(hc)
                    group = self._ref_group(kids, hlid, bool(flags & tes4.PERSISTENT))
                    node2 = plugintree.Rec.new(rec.tag, flags, rlid, join(subs), FORM_VERSION)
                    group.kids.append(node2)
                    found[rlid] = (node2, group)
        # (after every place's refs, as a door may stand in another cell, or be new there)
        for ckey, nav in sorted(navs.items()):
            cell = None if ckey.startswith('+') else gd.from_key(ckey)
            lid = self.link(ckey)
            outside = cell in gd.ext_cells
            kids = cell_kids(cell) if outside else self._cell_node(tree, found, cell, lid, order, self.pr.records.get(ckey))[1]
            for mesh in [nav] + nav.get('others', []):
                self._write_navmesh(found, cell, kids, lid, mesh, nav_info, nav_links, cell_kids)
        if nav_info:
            self._write_navi(tree, found, order, nav_info, nav_links)

        # the ground: each changed cell's LAND, over the game's own, in the cell's temporary group
        for ckey, L in sorted(getattr(self.pr, 'land', {}).items()):
            cell = gd.from_key(ckey)
            if cell not in gd.land:
                continue                                    # (land borrowed from a parent world isn't the cell's own)
            i, rec = gd.land[cell]
            llid = self.local(gd.to_global(i, rec.formid))
            original = list(tes4.iter_subrecords(gd.plugins[i].data(rec)))
            subs = landmod.encode(L, original, self.link, self._beyond(cell))
            have = found.get(llid)
            if have:
                have[0].set_data(join(subs), rec.flags & ~tes4.COMPRESSED)
                continue
            kids = cell_kids(cell)
            group = self._ref_group(kids, self.local(cell), False)
            node = plugintree.Rec.new('LAND', rec.flags & ~tes4.COMPRESSED, llid, join(subs), FORM_VERSION)
            group.kids.insert(0, node)                      # (the land first, as the game's cells have it)
            found[llid] = (node, group)

        # water: the cell's record says how high its water stands (XCLW; the world's own level: the greatest float)
        for ckey, h in sorted(getattr(self.pr, 'water', {}).items()):
            cell = gd.from_key(ckey)
            cell_kids(cell)
            node = nodes[cell][0]
            subs = list(tes4.iter_subrecords(node.data()))
            subs = set_water(subs, h)
            node.set_data(join(subs), node.flags & ~tes4.COMPRESSED)

        # details on a place: its music, lighting, region, zone, as worldrec.py has them
        for ckey, info in sorted(getattr(self.pr, 'cellinfo', {}).items()):
            if ckey.startswith('+') and ckey not in self.pr.records:
                continue                                    # (the place itself has been undone away)
            cell = None if ckey.startswith('+') else gd.from_key(ckey)
            if cell in gd.ext_cells:
                cell_kids(cell)
                node = nodes[cell][0]
            else:
                node = self._cell_node(tree, found, cell, self.link(ckey), order, self.pr.records.get(ckey))[0]
            subs = worldrec.apply_cell(list(tes4.iter_subrecords(node.data())), info, self.link)
            node.set_data(join(subs), node.flags & ~tes4.COMPRESSED)

        self._drop(tree, found)

        # the header: an opened plugin's own, with its count and next ID brought up to date
        own_ids = [r.formid & 0xFFFFFF for r, _p, _path in tree.records() if r.formid >> 24 == len(self.masters)]
        next_id = self.own(max([self.pr.next_id] + [x + 1 for x in own_ids]))
        if self.source:
            subs = list(tes4.iter_subrecords(tree.header.raw))
            old = next((d for t, d in subs if t == 'HEDR'), None)
            v, _n, nxt = struct.unpack_from('<fiI', old)
            hedr = struct.pack('<fiI', v, tree.count(), max(nxt, next_id)) + old[12:]
            subs = [(t, hedr if t == 'HEDR' else d) for t, d in subs]
            # (only what you've changed on the Get ready to share page: an untouched plugin keeps its header)
            subs = _set_text(subs, 'CNAM', self.pr.author)
            subs = _set_text(subs, 'SNAM', self.pr.description)
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

    def _restored_ref(self, fid, rlid):
        """A placed thing's subrecords as its own file has them, numbered as we write."""
        i = fid >> 24
        p = self.gd.plugins[i]
        own = len(p.header['masters'])
        low = fid & 0xFFFFFF
        for rec, _g in p.walk():
            if rec.formid == (own << 24) | low:
                return self.remap_fields(i, rec.tag, list(tes4.iter_subrecords(p.data(rec))))
        return None

    def _drop(self, tree, found):
        """Records the mod has cleaned out of an opened plugin, and any groups that leaves empty."""
        gone = False
        for key in getattr(self.pr, 'drop', ()):
            have = found.get(self.link(key))
            if have and have[1] is not None and have[0] in have[1].kids:
                have[1].kids.remove(have[0])
                del found[self.link(key)]
                gone = True
        if gone:
            def prune(kids):
                keep = []
                for k in kids:
                    if isinstance(k, plugintree.Group):
                        k.kids = prune(k.kids)
                        if not k.kids:
                            continue
                    keep.append(k)
                return keep
            tree.tops = prune(tree.tops)

    def _write_navmesh(self, found, cell, kids, lid, nav, info, links, cell_kids):
        """A place's NAVM, first in its temporary group as the game has it, and its doors told which triangle they stand by
        (a mesh only copied to change its links keeps its triangles, so its doors are right as they are)."""
        fid = self.link(nav['form'])
        m = navbuild.to_record(nav, lid, self.link)
        data = navmesh.write_navm(m)
        have = found.get(fid)
        if have:
            have[0].set_data(data, 0)
        else:
            group = self._ref_group(kids, lid, False)
            node = plugintree.Rec.new('NAVM', 0, fid, data, FORM_VERSION)
            group.kids.insert(0, node)
            found[fid] = (node, group)
        world = self.gd.ext_cells.get(cell)
        e = navmesh.info_for(m, fid, self.local(world) if world is not None else lid,
                             navmesh.grid_place(*self.gd.cell_grid(cell)) if world is not None else 0)
        if nav.get('outline'):
            e['flags'] |= navmesh.INFO_OUTLINE
            e['outline'] = navbuild.outline_record(nav['outline'])
        info.append(e)
        links.append(navmesh.links_for(m, fid))
        if nav.get('copy'):
            return
        for door, tri in nav['doors']:
            self._door_xndp(found, door, cell, cell_kids, kids, lid, navmesh.door_link(fid, tri))
        for door in nav.get('no_door', []):
            self._door_xndp(found, door, cell, cell_kids, kids, lid, None)

    def _door_xndp(self, found, door, cell, cell_kids, kids, lid, xndp):
        """A door told which triangle it stands by (xndp), or (None) told it stands by none."""
        rid = self.link(door)
        have = found.get(rid)
        if have is None:                            # (a game door nothing else changed: an override of it)
            g = self.gd.from_key(door)
            home = self.gd.ref_cell.get(g, cell)
            i, rec = self.gd.cell_refs[home][g]
            subs = self.remap_fields(i, rec.tag, list(tes4.iter_subrecords(self.gd.plugins[i].data(rec))))
            flags = rec.flags & ~tes4.COMPRESSED
            if home != cell:
                kids, lid = cell_kids(home), self.local(home)
            group = self._ref_group(kids, lid, bool(flags & tes4.PERSISTENT))
            node = plugintree.Rec.new(rec.tag, flags, rid, join(subs), FORM_VERSION)
            group.kids.append(node)
            have = found[rid] = (node, group)
        subs = [(t, d) for t, d in tes4.iter_subrecords(have[0].data()) if t != 'XNDP']
        if xndp:
            at = navbuild.door_tag_at(subs)
            subs = subs[:at] + [('XNDP', xndp)] + subs[at:]
        have[0].set_data(join(subs), have[0].flags & ~tes4.COMPRESSED)

    def _write_navi(self, tree, found, order, info, links):
        """The master index: entries for this plugin's meshes only (the game merges them into its own), keeping any this
        plugin already has for meshes it didn't remake."""
        fid = self.local(navmesh.NAVI_FORM)
        have = found.get(fid)
        new = {e['navm'] for e in info}
        if have:
            old = navmesh.read_navi(have[0].data())
            info = [e for e in old['info'] if e['navm'] not in new] + info
            links = [e for e in old['links'] if e['navm'] not in new] + links
        data = navmesh.write_navi(navmesh.new_navi(info, links))
        if have:
            have[0].set_data(data, 0)
            return
        top = tree.top('NAVI', order)
        node = plugintree.Rec.new('NAVI', 0, fid, data, FORM_VERSION)
        top.kids.append(node)
        found[fid] = (node, top)

    def _cell_node(self, tree, found, cell, lid, order, mine=None):
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
        if cell is None:                                # (a place of the mod's own: its record is all there is)
            subs, flags = self.record_subs(mine), mine['flags']
        else:
            subs, flags = self.game_cell(cell)
        node = plugintree.Rec.new('CELL', flags, lid, join(subs), FORM_VERSION)
        world = self.gd.ext_cells.get(cell)
        if world is None and cell is not None:
            world = next((w for w, c in self.gd.world_persistent.items() if c == cell), None)
        if world is not None:
            return self._ext_cell_node(tree, found, cell, world, node, lid, order)
        top = tree.top('CELL', order)
        obj = lid & 0xFFFFFF
        block = self._group(top, obj % 10, tes4.G_INT_BLOCK)
        subblock = self._group(block, (obj // 10) % 10, tes4.G_INT_SUBBLOCK)
        kids = plugintree.Group(lid, tes4.G_CELL_CHILDREN)
        subblock.kids += [node, kids]
        found[lid] = (node, subblock)
        return node, kids

    def _beyond(self, cell):
        """Heights just past a cell's edges, from the cells next door (as the mod has them), for its normals."""
        gd = self.gd
        world, xy = gd.ext_cells[cell], gd.cell_grid(cell)
        cache = {}

        def heights(dx, dy):
            if (dx, dy) not in cache:
                c = gd.grid(world).get((xy[0] + dx, xy[1] + dy))
                mine = self.pr.land.get(gd.key(c)) if c is not None else None
                if mine:
                    cache[(dx, dy)] = mine['h']
                else:
                    e = gd.land_at(world, xy[0] + dx, xy[1] + dy)
                    cache[(dx, dy)] = landmod.heights_of(dict(tes4.iter_subrecords(gd.plugins[e[0]].data(e[1])))['VHGT']) if e else None
            return cache[(dx, dy)]

        def beyond(r, c):
            dx = -1 if c < 0 else 1 if c > 32 else 0
            dy = -1 if r < 0 else 1 if r > 32 else 0
            h = heights(dx, dy)
            # (cells share their edge points: one past our edge is one in from theirs)
            return h[(r - 32 * dy) * 33 + (c - 32 * dx)] if h else None
        return beyond

    def _world_children(self, tree, found, world, order):
        """The world's record (a copy of the game's, as every plugin with outside cells carries) and its children."""
        wlid = self.local(world)
        have = found.get(wlid)
        if have and have[1] is not None:
            node, parent = have
        else:
            i, rec = self.gd.source(world)
            subs = self.remap_fields(i, 'WRLD', list(tes4.iter_subrecords(self.gd.plugins[i].data(rec))))
            subs = [(t, d) for t, d in subs if t != 'OFST']   # (where its cells sit in the game's own file: not ours)
            node = plugintree.Rec.new('WRLD', rec.flags & ~tes4.COMPRESSED, wlid, join(subs), FORM_VERSION)
            parent = tree.top('WRLD', order)
            parent.kids.append(node)
            found[wlid] = (node, parent)
        at = parent.kids.index(node)
        nxt = parent.kids[at + 1] if at + 1 < len(parent.kids) else None
        if isinstance(nxt, plugintree.Group) and nxt.gtype == tes4.G_WORLD_CHILDREN:
            return nxt
        kids = plugintree.Group(wlid, tes4.G_WORLD_CHILDREN)
        parent.kids.insert(at + 1, kids)
        return kids

    def _ext_cell_node(self, tree, found, cell, world, node, lid, order):
        """An outside cell in its world: the persistent cell first in the world's group, a grid cell in its block
        (label: y // 32, x // 32) and sub-block (y // 8, x // 8), as the game files them."""
        wkids = self._world_children(tree, found, world, order)
        kids = plugintree.Group(lid, tes4.G_CELL_CHILDREN)
        xy = self.gd.cell_grid(cell) if cell in self.gd.ext_cells else None
        if xy is None:
            wkids.kids[0:0] = [node, kids]
            found[lid] = (node, wkids)
            return node, kids
        x, y = xy
        label = lambda a, b: struct.unpack('<I', struct.pack('<hh', a, b))[0]
        block = self._group(wkids, label(y // 32, x // 32), tes4.G_EXT_BLOCK)
        sub = self._group(block, label(y // 8, x // 8), tes4.G_EXT_SUBBLOCK)
        sub.kids += [node, kids]
        found[lid] = (node, sub)
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


WORLD_WATER = 3.4028234663852886e+38       # (XCLW at the greatest float: the cell takes its world's water level)
WATER_AFTER = ('EDID', 'FULL', 'DATA', 'XCLC', 'XCLL', 'IMPS', 'IMPF', 'LTMP', 'LNAM')


def set_water(subs, h):
    """A CELL's subrecords with its water at h (None: the world's level), the has-water flag on."""
    v = struct.pack('<f', WORLD_WATER if h is None else float(h))
    out, done = [], False
    for t, d in subs:
        if t == 'DATA' and d:
            d = bytes([d[0] | 2]) + d[1:]
        if t == 'XCLW':
            d, done = v, True
        out.append((t, d))
    if not done:
        at = max([n + 1 for n, (t, _d) in enumerate(out) if t in WATER_AFTER] or [len(out)])
        out.insert(at, ('XCLW', v))
    return out


def _set_text(subs, tag, text):
    """A header's author or description, if the project has one that differs from it."""
    have = next((d for t, d in subs if t == tag), None)
    if not text or tes4.zstr(have or b'') == text:
        return subs
    data = text.encode('cp1252', 'replace')[:511] + b'\0'
    if have is not None:
        return [(t, data if t == tag else d) for t, d in subs]
    at = 0
    for n, (t, _d) in enumerate(subs):
        if t in ('HEDR', 'OFST', 'DELE', 'CNAM'):
            at = n + 1
    return subs[:at] + [(tag, data)] + subs[at:]


def write(gd, project, path):
    data = Writer(gd, project).build()
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, path)
    return len(data)
