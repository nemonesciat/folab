"""The player's face from a New Vegas save (.fos), as the values a character record holds, so a mod can give the player
that face from the start. Read-only.

A save: 'FO3SAVEGAME', a header (its fields each followed by '|'), the screenshot, the plugin list, a table of where
its parts are, the global data, then one change record for every form the game changed: its ref (3 bytes), what changed
(flags), its type, a version and its length. Refs name forms by their place in the save's form ID list (or, with the
top bits 01, a form of the first file straight). Values inside a change record are each followed by '|'.

The player's base form (0x000007) records its face when flag 0x800 is set: a byte (whether it is the second face set),
the FaceGen numbers (50 shape, 30 asymmetry, 50 skin; the fourth set is empty), hair, eyes, hair length, hair colour (as
HCLR's four bytes), then its head parts (beard, eyebrows…; a count whose low two bits say how many bytes it takes).
Race (0x2000000) and sex (0x1000000) are only there when changed from the record. What comes before the face (spells,
attributes, name…) is skipped by finding the face's own shape: it must end exactly where the record ends."""
import struct

MAGIC = b'FO3SAVEGAME'
FACE, RACE, SEX = 0x800, 0x2000000, 0x1000000
PLAYER_BASE = 0x000007
COUNTS = (50, 30, 50)                   # FGGS, FGGA, FGTS (the empty fourth set has none)


class SaveError(ValueError):
    pass


def _vsval(d, p):
    """(value, bytes used): a count whose low two bits say its size."""
    size = (d[p] & 3) + 1
    return int.from_bytes(d[p:p + size], 'little') >> 2, size


class Save:
    def __init__(self, path):
        with open(path, 'rb') as f:
            self.d = d = f.read()
        if not d.startswith(MAGIC):
            raise SaveError('Not a New Vegas save')
        p = len(MAGIC) + 4 + struct.unpack_from('<I', d, len(MAGIC))[0]
        w, h = self._screenshot_size()
        p += w * h * 3
        self.form_version = d[p]
        size = struct.unpack_from('<I', d, p + 1)[0]
        q, end = p + 5, p + 5 + size
        count = d[q]
        q += 2
        self.plugins = []
        for _ in range(count):
            n = struct.unpack_from('<H', d, q)[0]
            self.plugins.append(d[q + 3:q + 3 + n].decode('cp1252'))
            q += 3 + n + 1
        if q != end:
            raise SaveError('The plugin list doesn\'t read as expected')
        ids_at, _t3, gd1_at, gd2_at, gd3_at, gd1_n, gd2_n, changes_n, gd3_n = struct.unpack_from('<9I', d, end)
        n = struct.unpack_from('<I', d, ids_at)[0]
        self.ids = struct.unpack_from('<%dI' % n, d, ids_at + 4)
        # the change records follow the first two tables of global data
        q = gd1_at
        for _ in range(gd1_n):
            q += 8 + struct.unpack_from('<I', d, q + 4)[0]
        self.changes = []
        for _ in range(changes_n):
            t = d[q + 7]
            size = (1, 2, 4)[t >> 6]
            ln = int.from_bytes(d[q + 9:q + 9 + size], 'little')
            body = q + 9 + size
            self.changes.append((self.ref(d[q:q + 3]), struct.unpack_from('<I', d, q + 3)[0], t & 63, body, ln))
            q = body + ln
        if q != gd3_at:
            raise SaveError('The change records don\'t end where the save says')

    def _screenshot_size(self):
        parts = self.d[len(MAGIC) + 4:].split(b'|', 3)
        return struct.unpack('<I', parts[2][:4])[0], struct.unpack('<I', parts[3][:4])[0]

    def ref(self, b):
        v = int.from_bytes(b, 'big')
        kind, v = v >> 22, v & 0x3FFFFF
        if kind == 0:
            return self.ids[v - 1] if v else 0
        return v if kind == 1 else 0xFF000000 | v

    def key(self, fid):
        """A form ID as FOLab's lasting key ('FalloutNV.esm:00ABCD'), by the save's own plugin list."""
        return '%s:%06X' % (self.plugins[fid >> 24], fid & 0xFFFFFF)

    def player_face(self):
        """{'fggs', 'fgga', 'fgts': floats, 'hair', 'eyes': keys, 'hair_length', 'hair_colour': [r, g, b], 'parts': keys,
        'race_changed', 'sex_changed'} or None when the save keeps the record's face."""
        ch = next((c for c in self.changes if c[0] == PLAYER_BASE), None)
        if not ch or not ch[1] & FACE:
            return None
        if ch[1] & (RACE | SEX):
            raise SaveError('This save changes the player\'s race or sex too: FOLab doesn\'t read those yet')
        _ref, flags, _t, body, ln = ch
        d, end = self.d, body + ln
        # (the face is the last thing in the record: find where it starts by its shape, ending exactly at the end)
        for start in range(body, end):
            got = self._face_at(start, end)
            if got:
                return got
        raise SaveError('The player\'s face doesn\'t read as expected in this save')

    def _face_at(self, p, end):
        d = self.d
        if d[p] not in (0, 1) or d[p + 1] != 0x7C:
            return None
        p += 2
        floats = []
        for _ in range(sum(COUNTS)):
            if p + 5 > end or d[p + 4] != 0x7C:
                return None
            floats.append(struct.unpack_from('<f', d, p)[0])
            p += 5
        try:
            hair, eyes = self.ref(d[p:p + 3]), self.ref(d[p + 4:p + 7])
            if d[p + 3] != 0x7C or d[p + 7] != 0x7C:
                return None
            p += 8
            length = struct.unpack_from('<f', d, p)[0]
            colour = d[p + 5:p + 8]
            p += 10
            n, size = _vsval(d, p)
            p += size + 1
            parts = []
            for _ in range(n):
                parts.append(self.ref(d[p:p + 3]))
                p += 4
        except (IndexError, struct.error):
            return None
        if p != end:
            return None
        a, b = COUNTS[0], COUNTS[0] + COUNTS[1]
        return {'fggs': floats[:a], 'fgga': floats[a:b], 'fgts': floats[b:], 'hair': self.key(hair) if hair else '',
                'eyes': self.key(eyes) if eyes else '', 'hair_length': length, 'hair_colour': list(colour),
                'parts': [self.key(x) for x in parts]}


def apply_face(rec, face):
    """A character record (recordio's form) with the face put in: the FaceGen numbers, hair, eyes, hair length and
    colour, head parts (all replaced, as the save has them). The order of its subrecords is kept."""
    import api_characters as ac
    pack = lambda fl: struct.pack('<%df' % len(fl), *fl).hex()
    rec['subs'] = [s for s in rec['subs'] if s['tag'] not in ('PNAM', 'HNAM', 'ENAM', 'LNAM', 'HCLR', 'FGGS', 'FGGA', 'FGTS')]
    for k in face['parts']:
        ac.insert(rec, {'tag': 'PNAM', 'label': 'Head part', 'kind': 'F', 'value': k})
    if face['hair']:
        ac.insert(rec, {'tag': 'HNAM', 'label': 'Hair', 'kind': 'F', 'value': face['hair']})
    ac.insert(rec, {'tag': 'LNAM', 'label': 'Hair length', 'kind': 'struct', 'fields': [{'name': 'Length', 'code': 'f', 'value': face['hair_length']}]})
    if face['eyes']:
        ac.insert(rec, {'tag': 'ENAM', 'label': 'Eyes', 'kind': 'F', 'value': face['eyes']})
    r, g, b = face['hair_colour']
    ac.insert(rec, {'tag': 'HCLR', 'label': 'Hair colour', 'kind': 'struct', 'fields': [
        {'name': 'Red', 'code': 'B', 'value': r}, {'name': 'Green', 'code': 'B', 'value': g}, {'name': 'Blue', 'code': 'B', 'value': b}, {'pad': '00'}]})
    for tag, fl in (('FGGS', face['fggs']), ('FGGA', face['fgga']), ('FGTS', face['fgts'])):
        ac.insert(rec, {'tag': tag, 'label': tag, 'kind': 'raw', 'value': pack(fl)})
    return rec


if __name__ == '__main__':
    import json
    import sys
    s = Save(sys.argv[1])
    print(json.dumps(s.player_face(), indent=1))
