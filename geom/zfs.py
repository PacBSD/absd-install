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

class nvpair(Structure):
    _fields_ = [('nvp_size',       c_int32),
                ('nvp_name_sz',    c_int16),
                ('_nvp_reserve',   c_int16),
                ('nvp_value_elem', c_int32),
                ('nvp_type',       c_int), # data_type_t enum
               ]
nvpair_p = POINTER(nvpair)

class nvlist(Structure):
    _fields_ = [('nvl_version', c_int32),
                ('nvl_nvflag',  c_uint32),
                ('nvl_priv',    c_uint64), # they "call" that a pointer...
                ('nvl_flag',    c_uint32),
                ('nvl_pad',     c_int32),
               ]
nvlist_p = POINTER(nvlist)

boolean_t = c_int

ZFS_TYPE_FILESYSTEM = 0x1
ZFS_TYPE_SNAPSHOT   = 0x2
ZFS_TYPE_VOLUME     = 0x4
ZFS_TYPE_POOL       = 0x8

ZFS_TYPE_DATASET = ZFS_TYPE_FILESYSTEM | ZFS_TYPE_VOLUME | ZFS_TYPE_SNAPSHOT

def make_enum(lst):
    G = globals()
    for i in range(len(lst)):
        G[lst[i]] = i

make_enum(["ZFS_PROP_TYPE",
           "ZFS_PROP_CREATION",
           "ZFS_PROP_USED",
           "ZFS_PROP_AVAILABLE",
           "ZFS_PROP_REFERENCED",
           "ZFS_PROP_COMPRESSRATIO",
           "ZFS_PROP_MOUNTED",
           "ZFS_PROP_ORIGIN",
           "ZFS_PROP_QUOTA",
           "ZFS_PROP_RESERVATION",
           "ZFS_PROP_VOLSIZE",
           "ZFS_PROP_VOLBLOCKSIZE",
           "ZFS_PROP_RECORDSIZE",
           "ZFS_PROP_MOUNTPOINT",
           "ZFS_PROP_SHARENFS",
           "ZFS_PROP_CHECKSUM",
           "ZFS_PROP_COMPRESSION",
           "ZFS_PROP_ATIME",
           "ZFS_PROP_DEVICES",
           "ZFS_PROP_EXEC",
           "ZFS_PROP_SETUID",
           "ZFS_PROP_READONLY",
           "ZFS_PROP_ZONED",
           "ZFS_PROP_SNAPDIR",
           "ZFS_PROP_ACLMODE",
           "ZFS_PROP_ACLINHERIT",
           "ZFS_PROP_CREATETXG",    #/* not exposed to the user */
           "ZFS_PROP_NAME",         #/* not exposed to the user */
           "ZFS_PROP_CANMOUNT",
           "ZFS_PROP_ISCSIOPTIONS", #/* not exposed to the user */
           "ZFS_PROP_XATTR",
           "ZFS_PROP_NUMCLONES",    #/* not exposed to the user */
           "ZFS_PROP_COPIES",
           "ZFS_PROP_VERSION",
           "ZFS_PROP_UTF8ONLY",
           "ZFS_PROP_NORMALIZE",
           "ZFS_PROP_CASE",
           "ZFS_PROP_VSCAN",
           "ZFS_PROP_NBMAND",
           "ZFS_PROP_SHARESMB",
           "ZFS_PROP_REFQUOTA",
           "ZFS_PROP_REFRESERVATION",
           "ZFS_PROP_GUID",
           "ZFS_PROP_PRIMARYCACHE",
           "ZFS_PROP_SECONDARYCACHE",
           "ZFS_PROP_USEDSNAP",
           "ZFS_PROP_USEDDS",
           "ZFS_PROP_USEDCHILD",
           "ZFS_PROP_USEDREFRESERV",
           "ZFS_PROP_USERACCOUNTING",#/* not exposed to the user */
           "ZFS_PROP_STMF_SHAREINFO",#/* not exposed to the user */
           "ZFS_PROP_DEFER_DESTROY",
           "ZFS_PROP_USERREFS",
           "ZFS_PROP_LOGBIAS",
           "ZFS_PROP_UNIQUE",       #/* not exposed to the user */
           "ZFS_PROP_OBJSETID",     #/* not exposed to the user */
           "ZFS_PROP_DEDUP",
           "ZFS_PROP_MLSLABEL",
           "ZFS_PROP_SYNC",
           "ZFS_PROP_REFRATIO",
           "ZFS_PROP_WRITTEN",
           "ZFS_PROP_CLONES",
           "ZFS_PROP_LOGICALUSED",
           "ZFS_PROP_LOGICALREFERENCED",
           "ZFS_PROP_INCONSISTENT", #/* not exposed to the user */
           "ZFS_NUM_PROPS"])

make_enum(["ZFS_PROP_USERUSED",
           "ZFS_PROP_USERQUOTA",
           "ZFS_PROP_GROUPUSED",
           "ZFS_PROP_GROUPQUOTA",
           "ZFS_NUM_USERQUOTA_PROPS"])

make_enum(["ZPOOL_PROP_NAME",
           "ZPOOL_PROP_SIZE",
           "ZPOOL_PROP_CAPACITY",
           "ZPOOL_PROP_ALTROOT",
           "ZPOOL_PROP_HEALTH",
           "ZPOOL_PROP_GUID",
           "ZPOOL_PROP_VERSION",
           "ZPOOL_PROP_BOOTFS",
           "ZPOOL_PROP_DELEGATION",
           "ZPOOL_PROP_AUTOREPLACE",
           "ZPOOL_PROP_CACHEFILE",
           "ZPOOL_PROP_FAILUREMODE",
           "ZPOOL_PROP_LISTSNAPS",
           "ZPOOL_PROP_AUTOEXPAND",
           "ZPOOL_PROP_DEDUPDITTO",
           "ZPOOL_PROP_DEDUPRATIO",
           "ZPOOL_PROP_FREE",
           "ZPOOL_PROP_ALLOCATED",
           "ZPOOL_PROP_READONLY",
           "ZPOOL_PROP_COMMENT",
           "ZPOOL_PROP_EXPANDSZ",
           "ZPOOL_PROP_FREEING",
           "ZPOOL_NUM_PROPS"])

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
                          zfs.zfs_type_to_name(zfs.zfs_get_type(fs)).decode('utf-8')))
        res = zfs.zfs_iter_children(fs, zfs_iter_f(fs_iter), None)
        return 0
    res = zfs.zfs_iter_root(handle, zfs_iter_f(fs_iter), None)

    zfs.libzfs_fini(handle)

if __name__ == '__main__':
    main()
