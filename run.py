from skalpit import Skalpit

import time

def get_opts(argv):
    opts = {}
    while argv:
        if argv[0][0] == '-':
            opts[argv[0][1:]] = argv[1]
        argv = argv[1:]
    return opts

def str_to_class(str):
    from sys import modules as m
    return getattr(m[__name__], str)

if __name__ == '__main__':

    from sys import argv
    myargs = get_opts(argv)

    engine = str_to_class(myargs['type'])(myargs)
