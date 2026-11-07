"""OpenStreetMap's XML (.osm, or .osm.bz2 / .osm.gz), read with the standard library: what a world made from a map can use of it. Not .pbf. FOLab fetches nothing: the person brings
the file.

    roads      way with highway=...: 'major' (motorway to tertiary), 'minor' (residential, service...), 'track'. Tunnels, footpaths and anything planned are left out; bridges are kept apart.
    rivers     way with waterway=river/canal ('river'), stream/ditch/drain ('stream'), width= if it says.
    lakes      closed way or multipolygon with natural=water, landuse=reservoir/basin, water=lake...; not a river's own outline (water=river, waterway=riverbank: the river's line is used instead), and not the sea.
    buildings  closed way or multipolygon with building=...: its outline.
    places     node with place= and a name.

A point is (lat, lon) until osmplace.py puts it on the world. The ways share nodes where they join: a road's ends say so, so only a real dead end gets an end cap."""
import bz2
import gzip
import io
import xml.etree.ElementTree as ET

from elevation import MapFileError

ROAD_CLASS = {'motorway': 'major', 'trunk': 'major', 'primary': 'major', 'secondary': 'major', 'tertiary': 'major',
              'motorway_link': 'major', 'trunk_link': 'major', 'primary_link': 'major', 'secondary_link': 'major', 'tertiary_link': 'major',
              'residential': 'minor', 'unclassified': 'minor', 'living_street': 'minor', 'service': 'minor', 'road': 'minor',
              'track': 'track'}
RIVER_CLASS = {'river': 'river', 'canal': 'river', 'stream': 'stream', 'ditch': 'stream', 'drain': 'stream'}
RIVER_WATER = ('river', 'stream', 'canal', 'ditch', 'drain', 'stream_pool', 'wastewater', 'lock', 'moat', 'oxbow_river')
GONE = ('proposed', 'construction', 'abandoned', 'disused', 'razed')


class OsmData:
    def __init__(self):
        self.bounds = None             # (min lat, min lon, max lat, max lon)
        self.roads, self.bridges, self.rivers, self.lakes, self.buildings, self.places = [], [], [], [], [], []
        self.skipped = {}              # {what: how many} left out on purpose
        self.road_ends = {}            # {node id: how many roads end there}
        self.passing = {}              # {node id: how many roads have it at all}

    def counts(self):
        out = {'roads': {}, 'rivers': {}}
        for w in self.roads:
            out['roads'][w['class']] = out['roads'].get(w['class'], 0) + 1
        for w in self.rivers:
            out['rivers'][w['class']] = out['rivers'].get(w['class'], 0) + 1
        out.update(bridges=len(self.bridges), lakes=len(self.lakes), buildings=len(self.buildings), places=len(self.places), skipped=self.skipped)
        return out


def _skip(d, what):
    d.skipped[what] = d.skipped.get(what, 0) + 1


def _is_yes(v):
    return bool(v) and v not in ('no', 'false', '0')


def _open_stream(path_or_bytes, name=''):
    low = name.lower()
    if isinstance(path_or_bytes, (bytes, bytearray)):
        data = bytes(path_or_bytes)
        if data[:3] == b'BZh':
            data = bz2.decompress(data)
        elif data[:2] == b'\x1f\x8b':
            data = gzip.decompress(data)
        return io.BytesIO(data)
    low = low or str(path_or_bytes).lower()
    if low.endswith('.pbf'):
        raise MapFileError('FOLab reads OpenStreetMap\'s XML (.osm), not .pbf. Turn it into XML first (osmium cat in.osm.pbf -o out.osm), or export a smaller area from openstreetmap.org.')
    if low.endswith('.bz2'):
        return bz2.open(path_or_bytes, 'rb')
    if low.endswith('.gz'):
        return gzip.open(path_or_bytes, 'rb')
    return open(path_or_bytes, 'rb')


def read(source, name='', progress=None):
    """An OsmData from a path, or from the file's bytes. Takes the file a piece at a time, so a big one doesn't sit in memory as XML."""
    nodes, ways, relations = {}, {}, []
    d = OsmData()
    seen = 0
    root_ok = False
    try:
        f = _open_stream(source, name)
        try:
            for event, el in ET.iterparse(f, events=('start', 'end')):
                if event == 'start':
                    if el.tag == 'osm':
                        root_ok = True
                    elif not root_ok:
                        raise MapFileError('This isn\'t OpenStreetMap XML: it starts with <%s>.' % el.tag)
                    continue
                if el.tag == 'node':
                    try:
                        nodes[int(el.get('id'))] = (float(el.get('lat')), float(el.get('lon')))
                    except (TypeError, ValueError):
                        pass
                    if len(el):
                        tags = {t.get('k'): t.get('v') for t in el.iter('tag')}
                        if tags.get('place') and tags.get('name') and el.get('lat'):
                            d.places.append({'pt': (float(el.get('lat')), float(el.get('lon'))), 'name': tags['name'], 'kind': tags['place']})
                    el.clear()
                elif el.tag == 'way':
                    tags = {t.get('k'): t.get('v') for t in el.iter('tag')}
                    if tags:
                        ways[int(el.get('id'))] = ([int(n.get('ref')) for n in el.iter('nd')], tags)
                    else:                          # (no tags: only a relation's outline can want it)
                        ways[int(el.get('id'))] = ([int(n.get('ref')) for n in el.iter('nd')], None)
                    el.clear()
                elif el.tag == 'relation':
                    tags = {t.get('k'): t.get('v') for t in el.iter('tag')}
                    if tags.get('type') == 'multipolygon':
                        relations.append((tags, [(m.get('type'), int(m.get('ref')), m.get('role')) for m in el.iter('member')]))
                    el.clear()
                elif el.tag == 'bounds':
                    try:
                        d.bounds = (float(el.get('minlat')), float(el.get('minlon')), float(el.get('maxlat')), float(el.get('maxlon')))
                    except (TypeError, ValueError):
                        pass
                seen += 1
                if progress and seen % 50000 == 0:
                    progress(seen)
        finally:
            f.close()
    except ET.ParseError as e:
        raise MapFileError('This isn\'t a whole OpenStreetMap XML file: %s.' % e)
    except (OSError, EOFError) as e:
        if isinstance(e, FileNotFoundError):
            raise
        raise MapFileError('This file can\'t be unpacked: %s.' % e)
    if not root_ok:
        raise MapFileError('This isn\'t OpenStreetMap XML.')
    used_as_member = {r for _t, ms in relations for ty, r, _role in ms if ty == 'way'}
    for wid, (refs, tags) in ways.items():
        if tags:
            _way(d, nodes, wid, refs, tags, wid in used_as_member)
    for tags, members in relations:
        _relation(d, nodes, ways, tags, members)
    if not d.bounds and nodes:
        lats, lons = [n[0] for n in nodes.values()], [n[1] for n in nodes.values()]
        d.bounds = (min(lats), min(lons), max(lats), max(lons))
    return d


def _pts(nodes, refs):
    return [nodes[r] for r in refs if r in nodes]


def _lake_kind(tags):
    if tags.get('natural') == 'coastline':
        return None
    if tags.get('water') in RIVER_WATER or tags.get('waterway') == 'riverbank':
        return 'river area'
    if tags.get('natural') == 'water' or tags.get('landuse') in ('reservoir', 'basin') or tags.get('water') in ('lake', 'pond', 'reservoir', 'lagoon'):
        return 'lake'
    return None


def _way(d, nodes, wid, refs, tags, in_relation):
    closed = len(refs) > 3 and refs[0] == refs[-1]
    if tags.get('natural') == 'coastline':
        _skip(d, 'coastline (the base level is the sea)')
        return
    if 'highway' in tags:
        h = tags['highway']
        cls = ROAD_CLASS.get(h)
        if cls is None or any(k in tags for k in GONE):
            _skip(d, 'paths, footways and planned roads')
            return
        if _is_yes(tags.get('area')):
            _skip(d, 'paved areas')
            return
        if _is_yes(tags.get('tunnel')):
            _skip(d, 'road tunnels')
            return
        pts = _pts(nodes, refs)
        if len(pts) < 2:
            return
        for r in (refs[0], refs[-1]):
            d.road_ends[r] = d.road_ends.get(r, 0) + 1
        for r in set(refs):
            d.passing[r] = d.passing.get(r, 0) + 1
        w = {'id': wid, 'pts': pts, 'class': cls, 'kind': h, 'name': tags.get('name', ''), 'ends': (refs[0], refs[-1]), 'nodes': refs}
        (d.bridges if _is_yes(tags.get('bridge')) else d.roads).append(w)
        if _is_yes(tags.get('bridge')):
            w['class'] = 'bridge'
        return
    if 'waterway' in tags:
        cls = RIVER_CLASS.get(tags['waterway'])
        if tags['waterway'] == 'riverbank' and closed:
            _skip(d, 'river outlines (the river\'s line is used)')
            return
        if cls is None or _is_yes(tags.get('tunnel')) or any(k in tags for k in GONE):
            return
        pts = _pts(nodes, refs)
        if len(pts) >= 2:
            d.rivers.append({'id': wid, 'pts': pts, 'class': cls, 'kind': tags['waterway'], 'name': tags.get('name', ''), 'width_m': _metres(tags.get('width'))})
        return
    kind = _lake_kind(tags)
    if kind == 'river area':
        _skip(d, 'river outlines (the river\'s line is used)')
        return
    if kind == 'lake' and closed:
        pts = _pts(nodes, refs[:-1])
        if len(pts) >= 3:
            d.lakes.append({'id': wid, 'ring': pts, 'name': tags.get('name', '')})
        return
    if 'building' in tags and closed and tags['building'] != 'no':
        pts = _pts(nodes, refs[:-1])
        if len(pts) >= 3:
            d.buildings.append({'id': wid, 'ring': pts, 'kind': tags['building'], 'name': tags.get('name', '')})


def _metres(v):
    if not v:
        return None
    try:
        s = v.strip().lower()
        if s.endswith(('ft', "'")):
            return float(s.rstrip("ft' ")) * 0.3048
        return float(s.split()[0].rstrip('m'))
    except (ValueError, IndexError):
        return None


def _relation(d, nodes, ways, tags, members):
    """A multipolygon's outer rings, the ways joined end to end. Holes are left out."""
    kind = _lake_kind(tags)
    is_building = 'building' in tags and tags['building'] != 'no'
    if kind != 'lake' and not is_building:
        if kind == 'river area':
            _skip(d, 'river outlines (the river\'s line is used)')
        return
    parts = [list(ways[r][0]) for ty, r, role in members if ty == 'way' and role in ('outer', '') and r in ways and ways[r][0]]
    for ring in _join(parts):
        pts = _pts(nodes, ring[:-1])
        if len(pts) < 3:
            continue
        if kind == 'lake':
            d.lakes.append({'id': 0, 'ring': pts, 'name': tags.get('name', '')})
        else:
            d.buildings.append({'id': 0, 'ring': pts, 'kind': tags['building'], 'name': tags.get('name', '')})


def _join(parts):
    """Ways joined into closed rings of node ids (first equal to last)."""
    rings, parts = [], [p for p in parts if len(p) >= 2]
    while parts:
        cur = parts.pop()
        while cur[0] != cur[-1]:
            for i, p in enumerate(parts):
                if p[0] == cur[-1]:
                    cur += p[1:]
                elif p[-1] == cur[-1]:
                    cur += p[-2::-1]
                elif p[-1] == cur[0]:
                    cur = p[:-1] + cur
                elif p[0] == cur[0]:
                    cur = p[:0:-1] + cur
                else:
                    continue
                parts.pop(i)
                break
            else:
                break                      # (cut off at the edge of the extract: this ring never closes)
        if cur[0] == cur[-1] and len(cur) > 3:
            rings.append(cur)
    return rings
