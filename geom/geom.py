from ctypes import *
import atexit

from . import util

class GeomException(Exception):
    pass

off_t = c_long

def LIST_ENTRY(ty):
    class ListEntry(Structure):
        _fields_ = [("le_next", POINTER(ty)),
                    ("le_prev", POINTER(POINTER(ty))),
                   ]
    return ListEntry

def pointer_list(start, attrname):
    cur = getattr(start, attrname)
    while bool(cur):
        yield(cur[0])
        cur = getattr(cur[0], attrname).le_next


class GIdent(Structure):
    @property
    def what(self):
        return self.lg_what.value

class GMesh(Structure):
    @property
    def class_():
        return self.lg_class[0]

class GConfig(Structure):
    @property
    def next(self):
        if bool(self.lg_config.le_next):
            return self.lg_config.le_next[0]
        return None

    @property
    def name(self):
        return self.lg_name.decode('utf-8')

    @property
    def value(self):
        if self.lg_val is not None:
            return self.lg_val.decode('utf-8')
        else:
            return None

    @property
    def val(self):
        return self.value

class GClass(Structure):
    @property
    def name(self):
        return self.lg_name.decode('utf-8')

    def next(self):
        if bool(self.lg_class.le_next):
            return self.lg_class.le_next[0]
        return None

    def geoms(self):
        return pointer_list(self, 'lg_geom')

    def configs(self):
        return pointer_list(self, 'lg_config')

class GGeom(Structure):
    @property
    def class_(self):
        return self.lg_class[0]

    @property
    def name(self):
        return self.lg_name.decode('utf-8')

    @property
    def rank(self):
        return self.lg_rank.value

    def next(self):
        if bool(self.lg_geom.le_next):
            return self.lg_geom.le_next[0]
        return None

    def consumers(self):
        return pointer_list(self, 'lg_consumer')
    def providers(self):
        return pointer_list(self, 'lg_provider')
    def configs(self):
        return pointer_list(self, 'lg_config')


class GConsumer(Structure):
    @property
    def geom(self):
        return self.lg_geom[0]

    def next(self):
        if bool(self.lg_consumer.le_next):
            return self.lg_consumer.le_next[0]
        return None

    def providers(self):
        return pointer_list(self, 'lg_provider')

    def consumers(self):
        """consumers of this consumer..."""
        # I hope I got this right, the C header simply defines:
        # LIST_ENTRY(gconsumer) lg_consumer;
        # LIST_ENTRY(gconsumer) lg_consumers;
        # Which I personally want to slap someone for...
        cur = self.lg_consumers
        while bool(cur):
            yield(cur[0])
            cur = cur[0].lg_consumer.le_next

    @property
    def mode(self):
        return self.lg_mode.decode('utf-8')

    def configs(self):
        return pointer_list(self, 'lg_config')

class GProvider(Structure):
    @property
    def name(self):
        return self.lg_name.decode('utf-8')

    @property
    def geom(self):
        return self.lg_geom[0]

    def next(self):
        if bool(self.lg_provider.le_next):
            return self.lg_provider.le_next[0]
        return None

    def consumers(self):
        return pointer_list(self, 'lg_consumer')

    @property
    def mode(self):
        return self.lg_mode.decode('utf-8')

    @property
    def mediasize(self):
        return self.lg_mediasize

    @property
    def sectorsize(self):
        return self.lg_sectorsize

    @property
    def stripesize(self):
        return self.lg_stripesize

    def configs(self):
        return pointer_list(self, 'lg_config')


GIdent._fields_    = [("lg_id",     c_void_p),
                      ("lg_ptr",    c_void_p),
                      ("lg_what",   c_int)
                     ]

GMesh._fields_     = [("lg_class",  POINTER(GClass)),
                      ("lg_ident",  POINTER(GIdent))
                     ]

GConfig._fields_   = [("lg_config", LIST_ENTRY(GConfig)),
                      ("lg_name",   c_char_p),
                      ("lg_val",    c_char_p)
                     ]

GClass._fields_    = [("lg_id",     c_void_p),
                      ("lg_name",   c_char_p),
                      ("lg_class",  LIST_ENTRY(GClass)),
                      ("lg_geom",   POINTER(GGeom)),
                      ("lg_config", POINTER(GConfig))
                     ]

GGeom._fields_     = [("lg_id",        c_void_p),
                      ("lg_class",     POINTER(GClass)),
                      ("lg_name",      c_char_p),
                      ("lg_rank",      c_uint),
                      ("lg_geom",      LIST_ENTRY(GGeom)),
                      ("lg_consumer",  POINTER(GConsumer)),
                      ("lg_provider",  POINTER(GProvider)),
                      ("lg_config",    POINTER(GConfig))
                     ]

GConsumer._fields_ = [("lg_id",           c_void_p),
                      ("lg_geom",         POINTER(GGeom)),
                      ("lg_consumer",     LIST_ENTRY(GConsumer)),
                      ("lg_provider",     POINTER(GProvider)),
                      ("lg_consumers",    LIST_ENTRY(GConsumer)),
                      ("lg_mode",         c_char_p),
                      ("lg_config",       POINTER(GConfig))
                     ]

GProvider._fields_ = [("lg_id",           c_void_p),
                      ("lg_name",         c_char_p),
                      ("lg_geom",         POINTER(GGeom)),
                      ("lg_provider",     LIST_ENTRY(GProvider)),
                      ("lg_consumer",     POINTER(GConsumer)),
                      ("lg_mode",         c_char_p),
                      ("lg_mediasize",    off_t),
                      ("lg_sectorsize",   c_uint),
                      ("lg_stripeoffset", off_t),
                      ("lg_stripesize",   off_t),
                      ("lg_config",       POINTER(GConfig))
                     ]

GReqPtr = POINTER(c_void_p)

geom_functions = [
    ("gctl_get_handle", GReqPtr,    None),
    ("gctl_issue",      c_char_p,   [GReqPtr]),
    ("gctl_ro_param",   None,       [GReqPtr, c_char_p, c_int, c_void_p]),
    ("gctl_rw_param",   None,       [GReqPtr, c_char_p, c_int, c_void_p]),
    ("gctl_free",       None,       [GReqPtr]),

    ("geom_gettree",    c_int,      [POINTER(GMesh)]),
    ("geom_deletetree", None,       [POINTER(GMesh)]),
    ("geom_lookupid",   POINTER(GIdent),
                                    [POINTER(GMesh), c_void_p]),

    ("g_open",          c_int,      [c_char_p, c_int]),
    ("g_close",         None,       [c_int]),
    ("g_mediasize",     off_t,      [c_int]),
]

lib = CDLL('libgeom.so.5', mode=RTLD_GLOBAL)
if lib is None:
    raise Exception('failed to open libgeom.so.5')
util.load_functions(lib, geom_functions)

class Mesh(object):
    def __init__(self):
        self.mesh = GMesh()
        err = lib.geom_gettree(byref(self.mesh))
        if err != 0:
            self.mesh = None
            raise GeomException('geom_gettree failed with error %i' % err)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.mesh is not None:
            lib.geom_deletetree(byref(self.mesh))

    def classes(self):
        return pointer_list(self.mesh, 'lg_class')

    def find_class(self, name):
        for cl in self.classes():
            if cl.lg_name == name:
                return cl
        return None

def partition_type_for(scheme, ty):
    ty     = ty.lower()
    scheme = scheme.lower()
    if scheme == 'gpt':
        if ty == 'freebsd' or len(ty) == 0:
            return 'freebsd-ufs'
        elif ty == 'swap':
            return 'freebsd-swap'
    elif scheme == 'mbr':
        if (ty.startswith('freebsd-') or
            len(ty) == 0              or
            ty == 'swap'
           ):
            return 'freebsd'
    return ty

def gctl_param(req, param, ty, value):
    key = create_string_buffer(param.encode('utf-8'))
    if ty == int:
        v = c_long(value)
        lib.gctl_ro_param(req, key, sizeof(c_long), byref(v))
        return v
    elif ty == str:
        v = create_string_buffer(value.encode('utf-8'))
        lib.gctl_ro_param(req, key, sizeof(v), cast(v, c_void_p))
        return v
    else:
        raise ValueError

Uncommitted = []

def geom_part_do(provider, verb, data):
    req = lib.gctl_get_handle()
    keeparound = [gctl_param(req, 'class', str, 'PART'),
                  gctl_param(req, 'verb',  str, verb),
                  gctl_param(req, 'arg0',  str, provider),
                  gctl_param(req, 'flags', str, 'x') # don't commit immediately
                 ]
    for k,t,v in data:
        keeparound.append(gctl_param(req, k, t, v))
    err = lib.gctl_issue(req)
    lib.gctl_free(req)
    if err is None and provider not in Uncommitted:
        Uncommitted.append(provider)
    return err

def geom_part_commit(provider):
    if provider not in Uncommitted:
        return None
    req = lib.gctl_get_handle()
    keeparound = [gctl_param(req, 'class', str, 'PART'),
                  gctl_param(req, 'verb',  str, 'commit'),
                  gctl_param(req, 'arg0',  str, provider)
                 ]
    err = lib.gctl_issue(req)
    lib.gctl_free(req)
    if err is None:
        Uncommitted.remove(provider)
    return err

def geom_part_undo(provider):
    if provider not in Uncommitted:
        return None
    req = lib.gctl_get_handle()
    keeparound = [gctl_param(req, 'class', str, 'PART'),
                  gctl_param(req, 'verb',  str, 'undo'),
                  gctl_param(req, 'arg0',  str, provider)
                 ]
    err = lib.gctl_issue(req)
    lib.gctl_free(req)
    if err is None:
        Uncommitted.remove(provider)
    return err

def geom_commit_all():
    while len(Uncommitted):
        geom_part_commit(Uncommitted[0])

def geom_undo_all():
    while len(Uncommitted):
        geom_part_undo(Uncommitted[0])

atexit.register(geom_undo_all)

__all__ = [
    'GIdent',
    'GMesh',
    'GConfig',
    'GClass',
    'GConsumer',
    'GProvider',
    'GReqPtr',
    'lib',
    'GeomException',
    'Mesh',
    'partition_type_for',
    'geom_part_do',
    'geom_part_commit',
    'geom_part_undo',
    'gctl_param',
]
