from ctypes import *
import atexit

#from . import util
import util

zhandle      = POINTER(c_void_p)

zfs_handle   = POINTER(c_void_p)

zpool_handle = POINTER(c_void_p)
zpool_iter   = POINTER(c_void_p)

zpool_iter_f = CFUNCTYPE(c_int, zpool_handle, c_void_p)
zfs_iter_f   = CFUNCTYPE(c_int, zfs_handle, c_void_p)

class nvpair_s(Structure):
    _fields_ = [('nvp_size',       c_int32),
                ('nvp_name_sz',    c_int16),
                ('_nvp_reserve',   c_int16),
                ('nvp_value_elem', c_int32),
                ('nvp_type',       c_int), # data_type_t enum
               ]
nvpair_p = POINTER(nvpair_s)

class nvlist_s(Structure):
    _fields_ = [('nvl_version', c_int32),
                ('nvl_nvflag',  c_uint32),
                ('nvl_priv',    c_uint64), # they "call" that a pointer...
                ('nvl_flag',    c_uint32),
                ('nvl_pad',     c_int32),
               ]
nvlist_p = POINTER(nvlist_s)

boolean_t = c_int

class ZFS_TYPE(object):
    FILESYSTEM = 0x1
    SNAPSHOT   = 0x2
    VOLUME     = 0x4
    DATASET    = FILESYSTEM | VOLUME | SNAPSHOT
    POOL       = 0x8

def make_enum(cls, lst):
    for i in range(len(lst)):
        setattr(cls, lst[i], i)

class ZFS_PROP(object):
    pass
make_enum(ZFS_PROP, ["TYPE",
                     "CREATION",
                     "USED",
                     "AVAILABLE",
                     "REFERENCED",
                     "COMPRESSRATIO",
                     "MOUNTED",
                     "ORIGIN",
                     "QUOTA",
                     "RESERVATION",
                     "VOLSIZE",
                     "VOLBLOCKSIZE",
                     "RECORDSIZE",
                     "MOUNTPOINT",
                     "SHARENFS",
                     "CHECKSUM",
                     "COMPRESSION",
                     "ATIME",
                     "DEVICES",
                     "EXEC",
                     "SETUID",
                     "READONLY",
                     "ZONED",
                     "SNAPDIR",
                     "ACLMODE",
                     "ACLINHERIT",
                     "CREATETXG",    #/* not exposed to the user */
                     "NAME",         #/* not exposed to the user */
                     "CANMOUNT",
                     "ISCSIOPTIONS", #/* not exposed to the user */
                     "XATTR",
                     "NUMCLONES",    #/* not exposed to the user */
                     "COPIES",
                     "VERSION",
                     "UTF8ONLY",
                     "NORMALIZE",
                     "CASE",
                     "VSCAN",
                     "NBMAND",
                     "SHARESMB",
                     "REFQUOTA",
                     "REFRESERVATION",
                     "GUID",
                     "PRIMARYCACHE",
                     "SECONDARYCACHE",
                     "USEDSNAP",
                     "USEDDS",
                     "USEDCHILD",
                     "USEDREFRESERV",
                     "USERACCOUNTING",#/* not exposed to the user */
                     "STMF_SHAREINFO",#/* not exposed to the user */
                     "DEFER_DESTROY",
                     "USERREFS",
                     "LOGBIAS",
                     "UNIQUE",       #/* not exposed to the user */
                     "OBJSETID",     #/* not exposed to the user */
                     "DEDUP",
                     "MLSLABEL",
                     "SYNC",
                     "REFRATIO",
                     "WRITTEN",
                     "CLONES",
                     "LOGICALUSED",
                     "LOGICALREFERENCED",
                     "INCONSISTENT", #/* not exposed to the user */
                     "PROP_COUNT"])

#make_enum(["ZFS_PROP_USERUSED",
#           "ZFS_PROP_USERQUOTA",
#           "ZFS_PROP_GROUPUSED",
#           "ZFS_PROP_GROUPQUOTA",
#           "ZFS_NUM_USERQUOTA_PROPS"])

class ZPOOL_PROP(object):
    pass
make_enum(ZPOOL_PROP, ["NAME",
                       "SIZE",
                       "CAPACITY",
                       "ALTROOT",
                       "HEALTH",
                       "GUID",
                       "VERSION",
                       "BOOTFS",
                       "DELEGATION",
                       "AUTOREPLACE",
                       "CACHEFILE",
                       "FAILUREMODE",
                       "LISTSNAPS",
                       "AUTOEXPAND",
                       "DEDUPDITTO",
                       "DEDUPRATIO",
                       "FREE",
                       "ALLOCATED",
                       "READONLY",
                       "COMMENT",
                       "EXPANDSZ",
                       "FREEING",
                       "PROP_COUNT"])

ZPROP_SRC_NONE = 0x1
ZPROP_SRC_DEFAULT = 0x2
ZPROP_SRC_TEMPORARY = 0x4
ZPROP_SRC_LOCAL = 0x8
ZPROP_SRC_INHERITED = 0x10
ZPROP_SRC_RECEIVED = 0x20

ZPROP_SRC_ALL  = 0x3f

zfs_functions = [
    ("libzfs_init",          zhandle,      []),
    ("libzfs_fini",          None,         [zhandle]),

    ("zpool_get_handle",     zhandle,      [zpool_handle]),
    ("zfs_get_handle",       zhandle,      [zfs_handle]),

    ("zpool_open",           zpool_handle, [zhandle, c_char_p]),
    ("zpool_close",          None,         [zpool_handle]),
    ("zpool_get_name",       c_char_p,     [zpool_handle]),
    ("zpool_free_handles",   None,         [zhandle]),

    ("zpool_iter",           c_int,        [zhandle, zpool_iter_f, c_void_p]),

    ("zpool_create",         c_int,
        [zhandle, c_char_p, nvlist_p, nvlist_p, nvlist_p]),
    ("zpool_destroy",        c_int,        [zpool_handle, c_char_p]),
    ("zpool_add",            c_int,        [zpool_handle, nvlist_p]),

    ("zfs_open",             zfs_handle,   [zhandle, c_char_p, c_int]),
    ("zfs_close",            None,         [zfs_handle]),
    ("zfs_get_name",         c_char_p,     [zfs_handle]),
    ("zfs_get_type",         c_int,        [zfs_handle]),
    ("zfs_get_pool_handle",  zpool_handle, [zfs_handle]),
    ("zfs_iter_root",        c_int,        [zhandle, zfs_iter_f, c_void_p]),
    ("zfs_iter_children",    c_int,        [zfs_handle, zfs_iter_f, c_void_p]),
    ("zfs_iter_filesystems", c_int,        [zfs_handle, zfs_iter_f, c_void_p]),
    ("zfs_iter_snapshots",   c_int,        [zfs_handle, zfs_iter_f, c_void_p]),
    ("zfs_type_to_name",     c_char_p,     [c_int]),

    ("zfs_prop_set",         c_int,        [zfs_handle, c_char_p, c_char_p]),
    ("zfs_prop_get_written", c_int,
        [zfs_handle, c_char_p, c_char_p, c_size_t]),
]

# libzfs needs these...
uutil = CDLL('libuutil.so.2', mode=RTLD_GLOBAL)
geom  = CDLL('libgeom.so.5',  mode=RTLD_GLOBAL)

zfs = CDLL('libzfs.so.2')
if zfs is None:
    raise Exception('failed to open libzfs.so.2')
util.load_functions(zfs, zfs_functions)

nvpair_functions = [
    ("nvlist_alloc",      c_int,     [POINTER(nvlist_p), c_uint, c_int]),
    ("nvlist_free",       None,      [nvlist_p]),
    ("nvlist_size",       c_int,     [nvlist_p, POINTER(c_size_t), c_int]),
    ("nvlist_remove_all", c_int,     [nvlist_p, c_char_p]),
    ("nvlist_exists",     boolean_t, [nvlist_p, c_char_p]),
]

for k,v in [('nvpair',        nvpair_p),
            ('boolean_value', boolean_t),
            ('byte',          c_byte),
            ('int8',          c_int8),
            ('int16',         c_int16),
            ('int32',         c_int32),
            ('int64',         c_int64),
            ('uint8',         c_uint8),
            ('uint16',        c_uint16),
            ('uint32',        c_uint32),
            ('uint64',        c_uint64),
            ('string',        c_char_p),
            ('nvlist',        nvlist_p)]:
    nvpair_functions.extend([
        ('nvlist_add_%s'%k,    c_int, [nvlist_p, c_char_p, v]),
        ('nvlist_lookup_%s'%k, c_int, [nvlist_p, c_char_p, POINTER(v)]),
        ])

nvpair = CDLL('libnvpair.so.2')
if nvpair is None:
    raise Exception('failed to open libnvpair.so.2')
util.load_functions(nvpair, nvpair_functions)


def main():
    ### testing this shit now...
    import sys
    def die(s):
        print(s)
        sys.exit(1)

    handle = zfs.libzfs_init()
    if not bool(handle):
        die("no handle")

    def pool_iter(pool, data):
        print('pool: %s' % zfs.zpool_get_name(pool).decode('utf-8'))
        return 0

    res = zfs.zpool_iter(handle, zpool_iter_f(pool_iter), None)

    def fs_iter(fs, data):
        print('%s: %s' % (zfs.zfs_get_name(fs).decode('utf-8'),
                          zfs.zfs_type_to_name(zfs.zfs_get_type(fs))))
        res = zfs.zfs_iter_children(fs, zfs_iter_f(fs_iter), None)
        return 0
    res = zfs.zfs_iter_root(handle, zfs_iter_f(fs_iter), None)

    zfs.libzfs_fini(handle)

if __name__ == '__main__':
    main()

__all__ = ['zhandle',
           'zfs_handle',
           'zpool_handle',
           'zpool_iter',
           'zpool_iter_f',
           'zfs_iter_f',
           'nvpair_p',
           'nvlist_p',
           'boolean_t',
           'ZFS_TYPE',
           'ZFS_PROP',
           'ZPOOL_PROP',
           'ZPROP_SRC_NONE',
           'ZPROP_SRC_DEFAULT',
           'ZPROP_SRC_TEMPORARY',
           'ZPROP_SRC_LOCAL',
           'ZPROP_SRC_INHERITED',
           'ZPROP_SRC_RECEIVED',
           'ZPROP_SRC_ALL',
           'zfs', 'nvpair'
           ]
