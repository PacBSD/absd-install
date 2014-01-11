"""
Helper function and classes wrapping geom and zfs code.
"""

# pylint: disable=too-few-public-methods
#   The classes here are just informative structures

import string
from geom import geom, zfs
from ctypes import byref, POINTER, c_uint

import gettext
L = gettext.gettext

def find_cfg(gobj, name):
    """lookup a <config> entry by name"""
    for cfg in gobj.configs():
        if cfg.name == name:
            return cfg.value
    return None

class Partition(object):
    """Contains all the used information about a partition."""
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-arguments
    def __init__(self, own, name, by, secs, pty, rty, start, end, idx, lbl):
        self.owner      = own
        self.name       = name
        self.bytes_     = by
        self.sectorsize = secs
        self.partype    = pty
        self.rawtype    = rty
        self.start      = start
        self.end        = end
        self.index      = idx
        self.label      = lbl

    @staticmethod
    def from_provider(owner, provider):
        """Create a Partition from a geom provider object."""
        return Partition(owner,
                         provider.name,
                         provider.mediasize,
                         provider.sectorsize,
                         find_cfg(provider, 'type'),
                         find_cfg(provider, 'rawtype'),
                         int(find_cfg(provider, 'start')),
                         int(find_cfg(provider, 'end')),
                         int(find_cfg(provider, 'index')),
                         find_cfg(provider, 'label'))

class PartitionTable(object):
    """This usually wraps a disk containing a partition table.
    Keeps around a list of all partitions, and information about the disk's
    layout, such as size, sector-size, partitioning scheme..."""

    # pylint: disable=too-many-arguments
    def __init__(self, name, scheme, first, last, size, sectorsize):
        self.name       = name
        self.scheme     = scheme
        self.first      = first
        self.last       = last
        self.size       = size
        self.sectorsize = sectorsize
        self.partitions = []

    def add(self, part):
        """Insert a partition while keeping the list sorted by physical
        position."""
        for i in range(0, len(self.partitions)):
            if part.start < self.partitions[i].start:
                self.partitions.insert(i, part)
                return
        self.partitions.append(part)

    @staticmethod
    def from_geom(gobj):
        """Create a PartitionTable from a 'geom' object."""
        scheme = None
        first  = 0
        last   = 0
        size   = 0
        sector = 0
        for cfg in gobj.configs():
            if cfg.name == 'scheme':
                scheme = cfg.val
            elif cfg.name == 'first':
                first  = int(cfg.val)
            elif cfg.name == 'last':
                last   = int(cfg.val)
        if bool(gobj.lg_consumer):
            consumer = gobj.lg_consumer[0]
            if bool(consumer.lg_provider):
                size   = consumer.lg_provider[0].mediasize
                sector = consumer.lg_provider[0].sectorsize
        table = PartitionTable(gobj.name, scheme, first, last, size, sector)
        for provider in gobj.providers():
            table.add(Partition.from_provider(table, provider))
        return table

class ZPool(object):
    """Represents a zpool, currently only contains name and its children,
    flattened into a single array."""
    def __init__(self, name, children):
        self.name     = name
        self.children = children

    @staticmethod
    def from_handle(zhandle, pool):
        """Create a ZPool from a libzfs and zpool handle. Parses the pool's
        config to find its child-devices, and passes the list along to
        the ZPool ctor."""
        name = zfs.zfs.zpool_get_name(pool)
        if not bool(name):
            return None, L('failed to get zpool name')

        name = name.decode('utf-8')

        config = zfs.zfs.zpool_get_config(pool, None)
        if not bool(config):
            return None, (L('failed to get config for zpool %s') % name)

        nvroot = zfs.nvlist_p()
        res = zfs.zfs.nvlist_lookup_nvlist(config, b'vdev_tree', byref(nvroot))
        if res != 0:
            return None, (L('failed to get vdev tree for pool %s') % name)

        children = ZPool.__children(zhandle, pool, nvroot)

        return ZPool(name, children), None

    @staticmethod
    def __children(zhandle, pool, nvroot):
        """Recursively list a zpool's child vdevs given a handle to the
        libzfs, the zpool, and the current nvlist pointer from the zpool's
        config."""

        child    = POINTER(zfs.nvlist_p)()
        children = c_uint()
        zfs.zfs.nvlist_lookup_nvlist_array(nvroot, b'children',
                                           byref(child), byref(children))

        childlist = []
        for i in range(children.value):
            name = zfs.zfs.zpool_vdev_name(zhandle, pool, child[i], False)
            if not bool(name):
                continue
            childlist.append(name.decode('utf-8'))
            childlist.extend(ZPool.__children(zhandle, pool, child[i]))

        return childlist

def load():
    """Load the current disk geometry layout and provide a list of partition
    tables, zpools, and a list of unused devices to be shown in the partition
    editor."""

    tables = []
    used   = []
    unused = []
    errors = []

    zpools = []
    zhandle = zfs.zfs.libzfs_init()
    if bool(zhandle):
        def __pool_iter(pool, _):
            """C callback: called for each zpool"""
            # cannot raise exceptions past the C callback
            obj, err = ZPool.from_handle(zhandle, pool)
            if obj is not None:
                zpools.append(obj)
                used.extend(obj.children)
            else:
                errors.append(err)
            return 0

        zfs.zfs.zpool_iter(zhandle, zfs.zpool_iter_f(__pool_iter), None)
        zfs.zfs.libzfs_fini(zhandle)

    with geom.Mesh() as mesh:
        # first all the used ones
        cls = mesh.find_class(b'PART')
        if cls is not None:
            for gobj in cls.geoms():
                used.append(gobj.name)
                tables.append(PartitionTable.from_geom(gobj))

        # don't add RAID disks to the unused array
        # ELI attached devices have the same structural layout
        for cls in mesh.classes():
            load_class_used(cls, used)

        # now fill the unused-array
        for cls in mesh.classes():
            if cls.name == 'PART':
                continue
            load_class_unused(cls, used, unused)
    return tables, unused, zpools

def load_class_used(cls, used):
    """Load all the 'used' parts of a geom class which aren't handled
    explicitly, like disks and partitions part of a RAID or ELI."""
    if (cls.name != 'ELI' and not cls.name.startswith('RAID')):
        return
    for gobj in cls.geoms():
        for consumer in gobj.consumers():
            for provider in consumer.providers():
                used.append(provider.name)

def load_class_unused(cls, used, unused):
    """Load unused class members into the unused-array, hard masking things
    such as 'CDs' and partitions by inspecting the name. Partitions usually
    have their owner prefixed with a slash in front of them, so this will not
    add anything containing a slash."""
    for gobj in cls.geoms():
        for provider in gobj.providers():
            name = provider.name
            if name.startswith('cd'):
                # hard masking this one -_-
                continue
            if '/' in name:
                # this is a partition...
                continue
            if name in used:
                continue
            if next((x for x in unused if x.name == name), None) is not None:
                continue
            unused.append(provider)

def bytes2str(bytes_, precision=1):
    """convert an amount of bytes to a nice string with a unit suffix"""
    # gpart uses SI units so... not 1024
    suffix = 'X' # pylint Y U NO UNDERSTAND PYTHON'S SCOPING
    for suffix in [ 'b', 'k', 'M', 'G', 'T' ]:
        if bytes_ < 1024:
            break
        bytes_ /= 1024
    return ('%%.%uf%%s' % precision) % (bytes_, suffix)

def str2bytes(bytestr):
    """Convert a string with optional unit suffix to a number"""
    __str2byte_sufs = {
        'k': 1024,
        'M': 1024*1024,
        'G': 1024*1024*1024,
        'T': 1024*1024*1024*1024,
    }
    bytestr = str(bytestr)
    num = ''
    mul = 1
    for i in range(len(bytestr)):
        char = bytestr[i]
        if char == '.' or char in string.digits:
            num += char
            continue
        if char == ',':
            continue
        mul = __str2byte_sufs.get(char.tolower(), 1)
        break
    return int(num) * mul

def delete_partition(partition):
    """Delete the partition associated with a partition object."""
    owner = partition.owner
    index = partition.index
    res = geom.geom_part_do(owner.name, 'delete', [('index', int, index)])
    if res is not None:
        return res
    owner.partitions.remove(partition)
    return None

def create_partition(table, label, start, size, type_):
    """Create a partition inside the provided partition table."""
    data = []
    if len(label) > 0:
        data.append(('label', str, str(label)))

    if len(type_):
        known_type = geom.partition_type_for(table.scheme, type_)
        if known_type is None:
            return 'invalid type: %s' % type_
        data.append(('type', str, known_type))

    start = max(start // table.sectorsize, table.first)
    size  = (size // table.sectorsize) + 1

    if start + size > table.last:
        size = table.last - start + 1

    data.append(('start', str, str(start)))
    data.append(('size',  str, str(size)))

    return geom.geom_part_do(table.name, 'add', data)

def create_partition_table(provider, scheme):
    """Create a partitioning scheme on a geom provider."""
    data = [('scheme', str, scheme)]
    return geom.geom_part_do(provider.name, 'create', data)

def destroy_partition_table(table):
    """Destroy a partition table."""
    if len(table.partitions):
        return "Disk is not empty, remove partitions first!"
    return geom.geom_part_do(table.name, 'destroy', [])

__all__ = ['find_cfg',
           'Partition',
           'PartitionTable',
           'load',
           'bytes2str',
           'str2bytes',
           'create_partition',
           'delete_partition',
           'create_partition_table',
           'destroy_partition_table',
          ]
