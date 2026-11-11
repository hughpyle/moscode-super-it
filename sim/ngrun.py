#!/usr/bin/env python3
"""Run a SPICE deck through the ngspice library that ships inside KiCad.

usage: ngrun.py deck.cir   (the deck's .control block does the work)
"""
import ctypes, os, sys

LIB = "/Applications/KiCad/KiCad.app/Contents/PlugIns/sim/libngspice.dylib"
_keep = []


def run(deck, quiet=False):
    out = []
    ng = ctypes.CDLL(LIB)
    PF = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
    EF = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool,
                          ctypes.c_int, ctypes.c_void_p)
    BF = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)

    def on_print(s, i, p):
        line = s.decode(errors="replace")
        for pre in ("stdout ", "stderr "):
            if line.startswith(pre):
                line = line[len(pre):]
        out.append(line)
        if not quiet:
            print(line)
        return 0

    cbs = (PF(on_print), PF(lambda s, i, p: 0), EF(lambda *a: 0), BF(lambda *a: 0))
    _keep.append(cbs)
    ng.ngSpice_Init(cbs[0], cbs[1], cbs[2], None, None, cbs[3], None)
    ng.ngSpice_Command(f"source {deck}".encode())
    return out


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[1])) or ".")
    run(os.path.basename(sys.argv[1]))
