from . import platform
from ctypes import *

def load_functions(lib, lst):
    def register(fn):
        func = getattr(lib, fn[0], None)
        if func is None:
            raise Exception('failed to find function %s' % fn[0])

        func.restype  = fn[1]
        func.argtypes = fn[2]

    for i in lst:
        register(i)

class Struct_statfs(Structure):
    _fields_ = [('f_version',     c_uint32),
                ('f_type',        c_uint32),
                ('f_flags',       c_uint64),
                ('f_bsize',       c_uint64),
                ('f_iosize',      c_uint64),
                ('f_blocks',      c_uint64),
                ('f_bfree',       c_uint64),
                ('f_bavail',      c_int64),
                ('f_files',       c_uint64),
                ('f_ffree',       c_int64),
                ('f_syncwrites',  c_uint64),
                ('f_asyncwrites', c_uint64),
                ('f_syncreads',   c_uint64),
                ('f_asyncreads',  c_uint64),
                ('f_spare',       c_uint64 * 10),
                ('f_namemax',     c_uint32),
                ('f_owner',       platform.uid_t),
                ('f_fsid',        platform.fsid_t),
                ('f_charspare',   c_char * 80),
                ('f_fstypename',  c_char * platform.MFSNAMELEN),
                ('f_mntfromname', c_char * platform.MNAMELEN),
                ('f_mnttoname',   c_char * platform.MNAMELEN)]

util_functions = [
    ("getfsstat", c_int,    [POINTER(Struct_statfs), c_long, c_int]),
]

libc = CDLL(platform.LIBC, mode=RTLD_GLOBAL)
if libc is None:
    raise Exception('failed to open libgeom.so.5')
load_functions(libc, util_functions)

def genmounts():
    count      = max(1024, libc.getfsstat(None, 0, platform.MNT_WAIT))
    array_type = Struct_statfs * count
    data       = array_type()
    got        = libc.getfsstat(data, sizeof(array_type), 0)

    for idx in range(0, got):
        fromname = data[idx].f_mntfromname.decode('utf-8')
        toname   = data[idx].f_mnttoname.decode('utf-8')
        yield (fromname, toname)
