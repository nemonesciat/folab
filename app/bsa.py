"""Reader for New Vegas / Fallout 3 BSA archives (version 104). Read-only.

Header (36 bytes): 'BSA\\0', version, offset of the folder records (36), archive flags, folder count, file count,
total length of folder names, total length of file names, file-type flags. Then one 16-byte record per folder
(name hash, file count, offset); then, per folder, its name (length byte, text, NUL) and a 16-byte record per file
(name hash, size, offset into the archive); then every file name, NUL-terminated, in the same order."""
import mmap
import struct
import zlib

ENC = 'cp1252'

HAS_DIR_NAMES = 0x1
HAS_FILE_NAMES = 0x2
COMPRESSED_DEFAULT = 0x4
EMBEDDED_NAMES = 0x100      # each file's data starts with its full path (length byte + text)
SIZE_TOGGLE = 0x40000000    # in a file's size: flips the archive's compression default for that file


def norm(path):
    return path.replace('/', '\\').lower().lstrip('\\')


class Archive:
    """Memory-mapped archive; files maps 'meshes\\foo\\bar.nif' to (offset, size, compressed)."""

    def __init__(self, path):
        self.path = path
        self._f = open(path, 'rb')
        self.mm = mmap.mmap(self._f.fileno(), 0, access=mmap.ACCESS_READ)
        mm, unpack = self.mm, struct.unpack_from
        magic, version, off, self.flags, nfolders, nfiles, _dlen, _flen, self.types = unpack('<4sIIIIIIII', mm, 0)
        if magic != b'BSA\0' or version != 104:
            raise ValueError('%s: not a version 104 BSA (%r, %d)' % (path, magic, version))
        if not (self.flags & HAS_DIR_NAMES and self.flags & HAS_FILE_NAMES):
            raise ValueError('%s: archive without names is not supported' % path)
        counts = [unpack('<QII', mm, off + 16 * i)[1] for i in range(nfolders)]
        pos = off + 16 * nfolders
        entries = []
        for n in counts:
            ln = mm[pos]
            folder = mm[pos + 1:pos + ln].decode(ENC, 'replace')     # ln includes the NUL
            pos += 1 + ln
            for _ in range(n):
                _h, size, foff = unpack('<QII', mm, pos)
                entries.append((folder, size, foff))
                pos += 16
        self.files = {}
        compressed_default = bool(self.flags & COMPRESSED_DEFAULT)
        for folder, size, foff in entries:
            j = mm.find(b'\0', pos)
            name = mm[pos:j].decode(ENC, 'replace')
            pos = j + 1
            comp = compressed_default != bool(size & SIZE_TOGGLE)
            self.files[norm(folder + '\\' + name)] = (foff, size & 0x3FFFFFFF, comp)
        if len(self.files) != nfiles:
            raise ValueError('%s: read %d files, header says %d' % (path, len(self.files), nfiles))

    def close(self):
        self.mm.close()
        self._f.close()

    def __contains__(self, path):
        return norm(path) in self.files

    def read(self, path):
        off, size, comp = self.files[norm(path)]
        mm = self.mm
        if self.flags & EMBEDDED_NAMES:
            skip = 1 + mm[off]
            off, size = off + skip, size - skip
        if comp:
            want = struct.unpack_from('<I', mm, off)[0]
            if want == 0:
                return b''
            # decompressobj, not decompress: a few of the game's own streams lack the closing checksum
            out = zlib.decompressobj().decompress(mm[off + 4:off + size])
            if len(out) != want:
                raise ValueError('%s inflated to %d bytes, expected %d' % (path, len(out), want))
            return out
        return mm[off:off + size]


if __name__ == '__main__':
    import sys
    a = Archive(sys.argv[1])
    print('%d files, flags %#x, types %#x' % (len(a.files), a.flags, a.types))
    for p in list(a.files)[:12]:
        d = a.read(p)
        print('  %-70s %8d  %r' % (p, len(d), d[:24]))
