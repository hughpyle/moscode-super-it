"""Helpers: write a deck, run it in ngspice (subprocess), collect results."""
import os, re, subprocess, sys
import numpy as np
from circuit import deck, PARAMS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)


def run(name, show=False, **kw):
    """Generate deck `name`, run it, return (stdout lines, {scalar: value})."""
    path = os.path.join(OUT, name + ".cir")
    with open(path, "w") as f:
        f.write(deck(title=name, lib="../../kicad/superit.lib", **kw))
    r = subprocess.run([sys.executable, os.path.join(HERE, "ngrun.py"), path],
                       capture_output=True, text=True, timeout=1800)
    lines = (r.stdout + r.stderr).splitlines()
    if show:
        print("\n".join(lines))
    vals = {}
    for ln in lines:
        m = re.match(r"^\s*([\w.@\[\]()#+-]+)\s*=\s*([-+0-9.eE]+)\s*(?:targ|at|from|$)", ln)
        if m:
            try:
                vals[m.group(1).lower()] = float(m.group(2))
            except ValueError:
                pass
    errs = [l for l in lines if re.search(r"(?i)\berror\b|singular|timestep too small|not converge", l)]
    if errs:
        print(f"[{name}] ngspice complaints:\n  " + "\n  ".join(errs[:8]))
    return lines, vals


def table(name):
    """Load a file written by ngspice `wrdata` as a 2-D array."""
    return np.loadtxt(os.path.join(OUT, name))
