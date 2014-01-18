from ctypes import *

LIBC = 'libc.so.7'

uid_t  = c_uint32
fsid_t = c_int32 * 2

MFSNAMELEN     = 16
MNAMELEN       = 88
STATFS_VERSION = 0x20030518

MNT_WAIT       = 1
