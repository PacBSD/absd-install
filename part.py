import math
from geom import geom

def find_cfg(gobj, name):
    for c in gobj.configs():
        if c.name == name:
            return c.value
    return None

class Partition(object):
    def __init__(self, own, name, by, secs, pty, rty, start, end, idx):
        self.owner      = owner
        self.name       = name
        self.bytes_     = by
        self.sectorsize = secs
        self.partype    = pty
        self.rawtype    = rty
        self.start      = start
        self.end        = end
        self.index      = idx

    @staticmethod
    def from_provider(owner, p):
        return Partition(owner,
                         p.name,
                         p.mediasize,
                         p.sectorsize,
                         find_cfg(p, 'type'),
                         find_cfg(p, 'rawtype'),
                         int(find_cfg(p, 'start')),
                         int(find_cfg(p, 'end')),
                         int(find_cfg(p, 'index')))

class PartitionTable(object):
    def __init__(self, name, scheme, first, last, size, sectorsize):
        self.name       = name
        self.scheme     = scheme
        self.first      = first
        self.last       = last
        self.size       = size
        self.sectorsize = sectorsize
        self.partitions = []

    def add(self, part):
        """sorted insert"""
        for i in range(0, len(self.partitions)):
            if part.start < self.partitions[i].start:
                self.partitions.insert(i, part)
                return
        self.partitions.append(part)

    @staticmethod
    def from_geom(g):
        scheme = None
        first  = 0
        last   = 0
        size   = 0
        sector = 0
        for c in g.configs():
            if c.name == 'scheme':
                scheme = c.val
            elif c.name == 'first':
                first  = int(c.val)
            elif c.name == 'last':
                last   = int(c.val)
        if bool(g.lg_consumer):
            c = g.lg_consumer[0]
            if bool(c.lg_provider):
                size   = c.lg_provider[0].mediasize
                sector = c.lg_provider[0].sectorsize
        table = PartitionTable(g.name, scheme, first, last, size, sector)
        for p in g.providers():
            table.add(Partition.from_provider(table, p))
        return table

def load():
    tables = []
    with geom.Mesh() as mesh:
        gpart = mesh.find_class(b'PART')
        if gpart is None:
            return None
        for g in gpart.geoms():
            tables.append(PartitionTable.from_geom(g))
    return tables

def info():
    with geom.Mesh() as mesh:
        gpart = mesh.find_class(b'PART')
        if gpart is None:
            return None
        for g in gpart.geoms():
            print(g.name)
            for c in g.configs():
                print('  %s: %s' % (c.name, c.val))
            for p in g.providers():
                print('   -> %s' % p.name)
                for c in p.configs():
                    print('           %s: %s' % (c.name, c.val))

def bytes2str(b, d=1):
    suffix = 'b'
    # gpart uses SI units so... not 1024
    for s in ['k', 'M', 'G', 'T' ]:
        if b < 1000:
            break
        b /= 1000
        suffix = s
    return ('%%.%uf%%s' % d) % (b, suffix)

str2byte_sufs = {
    'k': 1000,
    'M': 1000*1000,
    'G': 1000*1000*1000,
    'T': 1000*1000*1000*1000,
}
def str2bytes(b, d=1):
    """This does not floor the result and allows floating point values."""
    b = str(b)
    num = ''
    mul = 1
    for i in range(len(b)):
        c = b[i]
        if c == '.' or c in string.digits:
            num += c
            continue
        if c == ',':
            continue
        mul = str2byte_sufs.get(c, 1)
        break
    return num * mul

def delete_partition(p):
    try:
        index = p.owner.partitions.index(p)
    except ValueError:
        return 'failed to find partition index'
    return geom_part_do(p.owner.name, 'delete', [('index', int, index)])

def create_partition(table, label, start, size, type_):
    data = []
    if len(label) > 0:
        data.append('label', str, str(label))

    ty = geom.partition_type_for(table.scheme, str(type_))
    if ty is None:
        return 'invalid type: %s' % type_
    data.append('type', str, ty)

    start = max(str2bytes(start) // table.sectorsize, table.first)
    size  = str2bytes(size)  // table.sectorsize

    if start + size > table.last:
        size = table.last - start

    data.append('start', str, str(start))
    data.append('size',  str, str(size))

    return geom_part_do(table.name, 'add', data)


__all__ = ['find_cfg',
           'Partition',
           'PartitionTable',
           'load',
           'info',
           'bytes2str',
           'str2bytes',
          ]
