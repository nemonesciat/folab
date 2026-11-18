"""Reads a Windows event trace (.etl) as Windows' recorder writes it: buffers of events, each event behind one of the
kernel's compact headers or a provider's EVENT_HEADER. Only what the game measurement needs.

    for ev in events(path): ev.kind, ev.cpu, ev.time, ev.group, ev.type, ev.pid, ev.tid, ev.provider, ev.id, ev.payload
"""
import mmap
import struct

BUFFER_HEADER = 0x48
# header types (the byte at offset 2 of every event)
SYSTEM32, SYSTEM64, COMPACT32, COMPACT64 = 1, 2, 3, 4
FULL32, INSTANCE32, TIMED, ERROR, WNODE, MESSAGE = 10, 11, 12, 13, 14, 15
PERFINFO32, PERFINFO64, EVENT32, EVENT64, FULL64, INSTANCE64 = 16, 17, 18, 19, 20, 21


class Event:
    __slots__ = ('kind', 'cpu', 'time', 'group', 'type', 'pid', 'tid', 'provider', 'id', 'opcode', 'payload', 'version')


def _guid(b):
    a, b2, c = struct.unpack_from('<IHH', b, 0)
    return '%08x-%04x-%04x-%s-%s' % (a, b2, c, b[8:10].hex(), b[10:16].hex())


def buffers(path):
    """(buffer index, cpu, logger id, memoryview of its used bytes)"""
    with open(path, 'rb') as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        view = memoryview(mm)
        pos, n, size = 0, 0, len(mm)
        while pos + BUFFER_HEADER <= size:
            bsize, saved, cur = struct.unpack_from('<III', mm, pos)
            if bsize < BUFFER_HEADER or pos + bsize > size:
                break
            cpu, _align, logger = struct.unpack_from('<BBH', mm, pos + 0x28)
            used = saved if BUFFER_HEADER < saved <= bsize else (cur if BUFFER_HEADER < cur <= bsize else bsize)
            yield n, cpu, logger, view[pos:pos + used]
            pos += bsize
            n += 1
        try:
            view.release()
            mm.close()
        except BufferError:
            pass    # payloads still held by the caller keep the map open until they go


def events(path, want=None):
    """Every event. want(kind, group, type) -> bool may skip building payloads of events not wanted (kernel ones)."""
    for _n, cpu, _logger, buf in buffers(path):
        off, end = BUFFER_HEADER, len(buf)
        while off + 8 <= end:
            marker = buf[off:off + 4]
            if bytes(marker) == b'\xff\xff\xff\xff':
                break
            htype = marker[2]
            ev = None
            if htype in (SYSTEM32, SYSTEM64, COMPACT32, COMPACT64, PERFINFO32, PERFINFO64):
                version = marker[0] | (marker[1] << 8)
                size, etype, group = struct.unpack_from('<HBB', buf, off + 4)
                if size < 8:
                    break
                if htype in (SYSTEM32, SYSTEM64):
                    hl = 0x20
                    tid, pid, t = struct.unpack_from('<IIQ', buf, off + 8)
                elif htype in (COMPACT32, COMPACT64):
                    hl = 0x18
                    tid, pid, t = struct.unpack_from('<IIQ', buf, off + 8)
                else:
                    hl = 0x10
                    tid = pid = None
                    t, = struct.unpack_from('<Q', buf, off + 8)
                if want is None or want('k', group, etype):
                    ev = Event()
                    ev.kind, ev.cpu, ev.time, ev.group, ev.type = 'k', cpu, t, group, etype
                    ev.pid, ev.tid, ev.provider, ev.id, ev.opcode = pid, tid, None, None, None
                    ev.version = version
                    ev.payload = buf[off + hl:off + size]
            elif htype in (EVENT32, EVENT64):
                size, = struct.unpack_from('<H', buf, off)
                if size < 0x50:
                    break
                flags, prop, tid, pid, t = struct.unpack_from('<HHIIQ', buf, off + 4)
                eid, ver, _ch, _lvl, opcode, task = struct.unpack_from('<HBBBBH', buf, off + 0x28)
                prov = _guid(bytes(buf[off + 0x18:off + 0x28]))
                if want is None or want(prov, eid, opcode):
                    ev = Event()
                    ev.kind, ev.cpu, ev.time, ev.group, ev.type = 'e', cpu, t, task, opcode
                    ev.pid, ev.tid, ev.provider, ev.id, ev.opcode = pid, tid, prov, eid, opcode
                    ev.version = ver
                    ev.payload = buf[off + 0x50:off + size]
            elif htype in (FULL32, FULL64, INSTANCE32, INSTANCE64, WNODE, TIMED, ERROR, MESSAGE):
                size, = struct.unpack_from('<H', buf, off)
                if size < 8:
                    break
                etype = marker[0] if False else None
                if want is None or want('f', None, None):
                    ev = Event()
                    ev.kind, ev.cpu, ev.time, ev.group, ev.type = 'f', cpu, None, None, None
                    ev.pid = ev.tid = ev.provider = ev.id = ev.opcode = ev.version = None
                    ev.payload = buf[off:off + size]
            else:
                break   # an unknown header: the rest of this buffer can't be walked
            if ev is not None:
                yield ev
            off += (size + 7) & ~7


if __name__ == '__main__':
    import collections
    import sys
    import time
    t0 = time.time()
    kinds = collections.Counter()
    provs = collections.Counter()
    nbuf = 0
    for ev in events(sys.argv[1]):
        if ev.kind == 'k':
            kinds[(ev.group, ev.type)] += 1
        elif ev.kind == 'e':
            provs[(ev.provider, ev.id)] += 1
        else:
            kinds['full'] += 1
    print('%.0f s' % (time.time() - t0))
    for k, v in kinds.most_common(40):
        print('kernel', k, v)
    for k, v in provs.most_common(40):
        print('event', k, v)
