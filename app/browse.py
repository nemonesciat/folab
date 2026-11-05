"""The Browse page's data: record types, lists of records, one record decoded for editing, the names of the forms it
links to, finding forms by editor ID, and where a form is used. The mod's own changes are laid over the game's."""
import threading
import time

import recordio
import schema
import tes4


class Browse:
    def __init__(self, gd, get_project):
        self.gd = gd
        self.pr = get_project              # (the open mod changes; ask each time)
        self.by_type = {}                  # type -> [fid]
        for fid, (i, rec) in gd.forms.items():
            self.by_type.setdefault(rec.tag, []).append(fid)
        self._names = {}                   # fid -> (edid, name), filled as asked and by the index below
        self.edids = None                  # lower editor ID -> fid, built in the background
        self.used = None                   # fid -> [(kind, key)], built in the background
        self.stopped = False
        threading.Thread(target=self._index, daemon=True).start()

    def close(self):
        """Stop the background index (the game was loaded again, for another mod)."""
        self.stopped = True

    # ---- names ----

    def names(self, fid):
        n = self._names.get(fid)
        if n is None:
            i, rec = self.gd.source(fid)
            f = self.gd.plugins[i].fields(rec)
            n = self._names[fid] = (tes4.zstr(f.get('EDID', b'')), tes4.zstr(f.get('FULL', b'')))
        return n

    def label(self, key):
        """'EditorID — Name (TYPE)' for a form key, the mod's own included."""
        pr = self.pr()
        rec = pr.records.get(key) if pr else None
        if rec:
            e, n, t = recordio.field(rec, 'EDID'), recordio.field(rec, 'FULL'), rec['type']
        else:
            try:
                fid = self.gd.from_key(key)
            except (ValueError, KeyError):
                return key
            if fid not in self.gd.forms:
                return key + ' (not loaded)'
            (e, n), t = self.names(fid), self.gd.forms[fid][1].tag
        return '%s%s (%s)' % (e or key, ' — ' + n if n and n != e else '', t)

    def _index(self):
        # (a few hundred records at a time with a pause between, so the editor keeps answering while this runs)
        t0 = time.time()
        gd, edids, used = self.gd, {}, {}
        for n, fid in enumerate(gd.forms):
            if n % 150 == 0:
                if self.stopped:
                    return
                time.sleep(0.02)                 # (give way: drawing a place comes first)
            try:
                e, _n = self.names(fid)
            except Exception:
                continue
            if e:
                edids.setdefault(e.lower(), fid)
        self.edids = edids
        # where each form is used: placed in a place, or named by a record a layout reads
        for n, (cell, refs) in enumerate(gd.cell_refs.items()):
            if n % 8 == 0:
                if self.stopped:
                    return
                time.sleep(0.02)                 # (give way: drawing a place comes first)
            ck = gd.key(cell)
            for r in gd.refs(cell):
                if r['base']:
                    used.setdefault(r['base'], []).append(('placed', ck))
        for n, (fid, (i, rec)) in enumerate(gd.forms.items()):
            if n % 150 == 0:
                if self.stopped:
                    return
                time.sleep(0.02)                 # (give way: drawing a place comes first)
            if rec.tag not in schema.TYPES or rec.tag == 'CELL':
                continue
            try:
                subs = list(tes4.iter_subrecords(gd.plugins[i].data(rec)))
            except Exception:
                continue
            for n, off in schema.record_form_offsets(rec.tag, subs):
                v = int.from_bytes(subs[n][1][off:off + 4], 'little')
                if v:
                    used.setdefault(gd.to_global(i, v), []).append(('record', gd.key(fid)))
        self.used = used
        print('Browse index ready (%d editor IDs, %.0fs)' % (len(edids), time.time() - t0), flush=True)

    # ---- lists ----

    def types(self):
        pr = self.pr()
        own = {}
        for k, r in (pr.records if pr else {}).items():
            if k.startswith('+'):
                own[r['type']] = own.get(r['type'], 0) + 1
        return [{'type': t, 'label': lab, 'count': len(self.by_type.get(t, ())) + own.get(t, 0),
                 'editable': t not in ('WRLD', 'QUST')} for t, (lab, _l) in schema.TYPES.items()]

    def records(self, rtype, q='', limit=1500):
        words, out, pr = q.lower().split(), [], self.pr()
        mine = pr.records if pr else {}
        for k, r in mine.items():
            if k.startswith('+') and r['type'] == rtype:
                e, n = recordio.field(r, 'EDID'), recordio.field(r, 'FULL')
                if all(w in (e + ' ' + n).lower() for w in words):
                    out.append({'key': k, 'edid': e, 'name': n, 'state': 'new'})
        rows = []
        for fid in self.by_type.get(rtype, ()):
            e, n = self.names(fid)
            if all(w in (e + ' ' + n).lower() for w in words):
                k = self.gd.key(fid)
                rows.append({'key': k, 'edid': e, 'name': n, 'state': 'changed' if k in mine else ''})
        rows.sort(key=lambda r: (not r['state'], r['edid'].lower()))
        return out + rows[:limit]

    # ---- one record ----

    def record(self, key):
        pr = self.pr()
        mine = pr.records.get(key) if pr else None
        if mine:
            rec, state = mine, 'new' if key.startswith('+') else 'changed'
        else:
            rec, state = recordio.load(self.gd, self.gd.from_key(key)), ''
        links = {k: self.label(k) for k in recordio.links(rec)}
        frm = rec['src'] if not key.startswith('+') else 'your mod'
        raw_from_dlc = any(s['kind'] == 'raw' for s in rec['subs']) and rec['src'].lower() != self.gd.names[0]
        return {'key': key, 'record': rec, 'state': state, 'from': frm, 'links': links,
                'editable': rec['type'] in schema.TYPES and rec['type'] not in ('WRLD', 'QUST'),
                'raw_note': raw_from_dlc, 'model': recordio.field(rec, 'MODL')}

    def resolve(self, q, limit=30):
        """Forms whose editor ID starts with (or contains) q, for picking a link."""
        if self.edids is None:
            return {'busy': True, 'hits': []}
        q = q.lower().strip()
        hits = [fid for e, fid in self.edids.items() if e.startswith(q)][:limit]
        if len(hits) < limit:
            hits += [fid for e, fid in self.edids.items() if q in e and not e.startswith(q)][:limit - len(hits)]
        return {'busy': False, 'hits': [{'key': self.gd.key(f), 'label': self.label(self.gd.key(f))} for f in hits]}

    def where_used(self, key, limit=200):
        if self.used is None:
            return {'busy': True}
        fid = self.gd.from_key(key)
        rows, seen = [], set()
        for kind, k in self.used.get(fid, []):
            if (kind, k) in seen:
                continue
            seen.add((kind, k))
            rows.append({'kind': kind, 'key': k, 'label': self.label(k)})
            if len(rows) >= limit:
                break
        return {'busy': False, 'rows': rows, 'total': len(set(self.used.get(fid, [])))}
