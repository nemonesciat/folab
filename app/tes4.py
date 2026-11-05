"""Low-level reader for New Vegas plugins (.esm/.esp): the TES4 header, groups, records and subrecords.
Read-only: nothing here ever writes to game files.

Layout (Fallout 3 / New Vegas): every record and group has a 24-byte header. A record is
type, data size, flags, form ID, 8 bytes of version control info; a group is 'GRUP', its whole size
(header included), a label, the group type and 8 more bytes. Subrecords have a 6-byte header
(type, 16-bit size); an XXXX subrecord gives the 32-bit size of the one after it."""
import mmap
import struct
import zlib

ENC = 'cp1252'

COMPRESSED = 0x00040000
DELETED = 0x00000020
PERSISTENT = 0x00000400

# Group types (the 'label' means something different in each)
G_TOP = 0               # label: record type, e.g. b'CELL'
G_WORLD_CHILDREN = 1    # label: WRLD form ID
G_INT_BLOCK = 2         # label: block number
G_INT_SUBBLOCK = 3      # label: sub-block number
G_EXT_BLOCK = 4         # label: grid y, x (int16 each)
G_EXT_SUBBLOCK = 5
G_CELL_CHILDREN = 6     # label: CELL form ID
G_TOPIC_CHILDREN = 7    # label: DIAL form ID
G_CELL_PERSISTENT = 8   # label: CELL form ID
G_CELL_TEMPORARY = 9
G_CELL_VWD = 10


def zstr(b):
    i = b.find(b'\0')
    if i >= 0:
        b = b[:i]
    return b.decode(ENC, 'replace')


def iter_subrecords(data):
    """(tag, bytes) for each subrecord, following XXXX for oversized ones."""
    pos, n, big = 0, len(data), None
    unpack = struct.unpack_from
    while pos + 6 <= n:
        tag, size = unpack('<4sH', data, pos)
        pos += 6
        if big is not None:
            size, big = big, None
        if tag == b'XXXX':
            big = unpack('<I', data, pos)[0]
            pos += size
            continue
        yield tag.decode('ascii', 'replace'), data[pos:pos + size]
        pos += size


def subrecord_dict(data):
    """First occurrence of each subrecord, for records whose fields don't repeat."""
    out = {}
    for tag, sd in iter_subrecords(data):
        out.setdefault(tag, sd)
    return out


class Record:
    __slots__ = ('tag', 'offset', 'flags', 'formid', 'size')

    def __init__(self, tag, offset, flags, formid, size):
        self.tag, self.offset, self.flags, self.formid, self.size = tag, offset, flags, formid, size

    def __repr__(self):
        return '<%s %08X @%d>' % (self.tag, self.formid, self.offset)


class PluginFile:
    """Memory-mapped plugin. walk() yields records with the groups they sit in."""

    def __init__(self, path):
        self.path = path
        self._f = open(path, 'rb')
        self.mm = mmap.mmap(self._f.fileno(), 0, access=mmap.ACCESS_READ)
        self.header = {'author': '', 'description': '', 'masters': [], 'version': 0.0,
                       'records': 0, 'next_id': 0, 'flags': 0}
        if self.mm[0:4] != b'TES4':
            raise ValueError('not a New Vegas plugin (missing TES4 header)')
        size, flags = struct.unpack_from('<II', self.mm, 4)
        self.header['flags'] = flags
        for st, sd in iter_subrecords(self.mm[24:24 + size]):
            if st == 'HEDR' and len(sd) >= 12:
                v, n, nxt = struct.unpack_from('<fiI', sd, 0)
                self.header.update(version=round(v, 2), records=n, next_id=nxt)
            elif st == 'CNAM':
                self.header['author'] = zstr(sd)
            elif st == 'SNAM':
                self.header['description'] = zstr(sd)
            elif st == 'MAST':
                self.header['masters'].append(zstr(sd))
        self.first = 24 + size

    def close(self):
        self.mm.close()
        self._f.close()

    def walk(self, start=None, end=None, groups=()):
        """Yield (record, groups) for every record; groups is a tuple of (type, label, offset), outermost first.
        Groups are walked with an explicit stack so deep files don't recurse."""
        mm, unpack = self.mm, struct.unpack_from
        pos = self.first if start is None else start
        end = len(mm) if end is None else end
        stack = [(end, groups)]
        while stack:
            stop, path = stack[-1]
            if pos + 24 > stop:
                stack.pop()
                pos = max(pos, stop)
                continue
            tag = mm[pos:pos + 4]
            if tag == b'GRUP':
                gsize, label, gtype = unpack('<IIi', mm, pos + 4)
                if gsize < 24:
                    raise ValueError('bad group size at %d' % pos)
                stack.append((pos + gsize, path + ((gtype, label, pos),)))
                pos += 24
                continue
            size, flags, formid = unpack('<III', mm, pos + 4)
            yield Record(tag.decode('ascii', 'replace'), pos, flags, formid, size), path
            pos += 24 + size

    def top_groups(self):
        """The record type of each top group, in file order (the order the game's own files keep)."""
        out, pos, mm = [], self.first, self.mm
        while pos + 24 <= len(mm) and mm[pos:pos + 4] == b'GRUP':
            size, label = struct.unpack_from('<II', mm, pos + 4)
            out.append(struct.pack('<I', label).decode('ascii', 'replace'))
            pos += size
        return out

    def group_at(self, offset):
        """(type, label, start of contents, end) for the group header at offset."""
        gsize, label, gtype = struct.unpack_from('<IIi', self.mm, offset + 4)
        return gtype, label, offset + 24, offset + gsize

    def record_at(self, offset):
        tag, size, flags, formid = struct.unpack_from('<4sIII', self.mm, offset)
        return Record(tag.decode('ascii', 'replace'), offset, flags, formid, size)

    def data(self, rec):
        """The record's subrecord bytes, inflated when the record is compressed."""
        raw = self.mm[rec.offset + 24:rec.offset + 24 + rec.size]
        if rec.flags & COMPRESSED:
            want = struct.unpack_from('<I', raw, 0)[0]
            # read as raw deflate past the 2-byte zlib header: one of the game's own records (a LAND in FalloutNV.esm)
            # carries a wrong checksum, which the game ignores
            out = zlib.decompressobj(-zlib.MAX_WBITS).decompress(raw[6:])
            if len(out) != want:
                raise ValueError('%r inflated to %d bytes, expected %d' % (rec, len(out), want))
            return out
        return raw

    def fields(self, rec):
        return subrecord_dict(self.data(rec))

    def owner(self, formid):
        """Which file a form ID belongs to: one of the masters, or this plugin itself."""
        i = formid >> 24
        m = self.header['masters']
        return m[i] if i < len(m) else self.path.replace('\\', '/').rsplit('/', 1)[-1]


if __name__ == '__main__':
    import collections
    import sys
    import time
    p = PluginFile(sys.argv[1])
    print(p.header)
    t = time.time()
    counts = collections.Counter()
    for r, _g in p.walk():
        counts[r.tag] += 1
    print('%d records in %.1fs' % (sum(counts.values()), time.time() - t))
    for tag, n in counts.most_common(25):
        print('  %s %d' % (tag, n))
