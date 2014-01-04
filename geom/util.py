def load_functions(lib, lst):
    def register(fn):
        func = getattr(lib, fn[0], None)
        if func is None:
            raise Exception('failed to find function %s' % fn[0])

        func.restype  = fn[1]
        func.argtypes = fn[2]

    for i in lst:
        register(i)
