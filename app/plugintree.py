"""A plugin as a tree of groups and records, to change and write back. Records nobody touches keep their exact bytes
(compressed ones stay compressed), so a plugin read and written with no changes comes out identical."""
import struct

import tes4


def pack(data):
    """A compressed record's bytes: how long its contents are, then the contents through zlib."""
    import zlib
    return struct.pack('<I', len(data)) + zlib.compress(data, 6)


class Rec:
    __slots__ = ('tag', 'flags', 'formid', 'head', 'raw')

    def __init__(self, tag, flags, formid, head, raw):
        self.tag, self.flags, self.formid, self.head, self.raw = tag, flags, formid, head, raw

    @classmethod
    def new(cls, tag, flags, formid, data, version=15):
        head = struct.pack('<4sIIIIHH', tag.encode(), len(data), flags, formid, 0, version, 0)
        return cls(tag, flags, formid, head, data)

    @classmethod
    def packed(cls, tag, flags, formid, data, version=15):
        """A new record stored compressed (its size, then zlib), as the game's files keep all their land."""
        return cls.new(tag, flags | tes4.COMPRESSED, formid, pack(data), version)

    def set_packed(self, data, flags=None):
        """New contents, stored compressed."""
        self.flags = (self.flags if flags is None else flags) | tes4.COMPRESSED
        self.raw = pack(data)

    def data(self):
        """The subrecord bytes, inflated when stored compressed."""
        if self.flags & tes4.COMPRESSED:
            import zlib
            return zlib.decompressobj(-zlib.MAX_WBITS).decompress(self.raw[6:])
        return self.raw

    def set_data(self, data, flags=None):
        """New contents (stored uncompressed), keeping the header's version info."""
        self.flags = (self.flags if flags is None else flags) & ~tes4.COMPRESSED
        self.raw = data
        self.head = self.head[:4] + struct.pack('<III', len(data), self.flags, self.formid) + self.head[16:]

    def bytes(self):
        return self.head[:4] + struct.pack('<III', len(self.raw), self.flags, self.formid) + self.head[16:] + self.raw


class Group:
    __slots__ = ('label', 'gtype', 'tail', 'kids')

    def __init__(self, label, gtype, tail=b'\0' * 8, kids=None):
        self.label, self.gtype, self.tail, self.kids = label, gtype, tail, kids if kids is not None else []

    def bytes(self):
        body = b''.join(k.bytes() for k in self.kids)
        return struct.pack('<4sIIi', b'GRUP', 24 + len(body), self.label, self.gtype) + self.tail + body

    def count(self):
        """records and groups inside, this one included (the header's count)"""
        return 1 + sum(k.count() if isinstance(k, Group) else 1 for k in self.kids)


def type_label(tag):
    return struct.unpack('<I', tag.encode())[0]


class Plugin:
    """header record + top groups"""

    def __init__(self, header, tops):
        self.header, self.tops = header, tops

    @classmethod
    def read(cls, path):
        with open(path, 'rb') as f:
            mm = f.read()
        hsize = struct.unpack_from('<I', mm, 4)[0]
        header = Rec('TES4', struct.unpack_from('<I', mm, 8)[0], 0, mm[:24], mm[24:24 + hsize])

        def parse(pos, end):
            out = []
            while pos + 24 <= end:
                if mm[pos:pos + 4] == b'GRUP':
                    size, label, gtype = struct.unpack_from('<IIi', mm, pos + 4)
                    out.append(Group(label, gtype, mm[pos + 16:pos + 24], parse(pos + 24, pos + size)))
                    pos += size
                else:
                    tag, size, flags, formid = struct.unpack_from('<4sIII', mm, pos)
                    out.append(Rec(tag.decode('ascii', 'replace'), flags, formid, mm[pos:pos + 24], mm[pos + 24:pos + 24 + size]))
                    pos += 24 + size
            return out
        return cls(header, parse(24 + hsize, len(mm)))

    @classmethod
    def empty(cls, header_data, flags=0):
        return cls(Rec.new('TES4', flags, 0, header_data), [])

    def top(self, tag, order=None):
        """The top group of a record type, made (in the game's order) when there is none."""
        label = type_label(tag)
        for g in self.tops:
            if g.label == label and g.gtype == tes4.G_TOP:
                return g
        g = Group(label, tes4.G_TOP)
        if order and tag in order:
            rank = {t: n for n, t in enumerate(order)}
            at = next((n for n, x in enumerate(self.tops)
                       if rank.get(struct.pack('<I', x.label).decode('ascii', 'replace'), len(order)) > rank[tag]), len(self.tops))
            self.tops.insert(at, g)
        else:
            self.tops.append(g)
        return g

    def records(self):
        """(record, parent group, path of groups) for every record"""
        def walk(kids, path):
            for k in kids:
                if isinstance(k, Group):
                    yield from walk(k.kids, path + (k,))
                else:
                    yield k, path[-1] if path else None, path
        yield from walk(self.tops, ())

    def count(self):
        return sum(g.count() for g in self.tops)

    def bytes(self):
        return self.header.bytes() + b''.join(g.bytes() for g in self.tops)
