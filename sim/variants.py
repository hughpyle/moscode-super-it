"""Circuit variants for the upgrade study."""
import re
from simlib import run
from circuit import PARAMS

GONE = "0.01p"     # capacitor removed
LINK = "1m"      # resistor replaced by a wire link


def _ids(params):
    lines, _ = run("bias", params=params, control="op\nprint @j.xchl.jq7[id] @j.xchl.jq6[id] v(xchl.p1) v(xchl.p2) v(xchl.k1) v(xchl.k2)")
    v = {}
    for ln in lines:
        m = re.match(r"\s*(\S+) = ([-+0-9.eE]+)", ln)
        if m: v[m.group(1)] = float(m.group(2))
    return v["@j.xchl.jq7[id]"], v["@j.xchl.jq6[id]"], v


def _num(x):
    mult = dict(k=1e3, m=1e-3, u=1e-6, n=1e-9, f=1e-15)
    m = re.match(r"([0-9.eE+-]+)(Meg|[kmunf])?$", x)
    return float(m.group(1))*(1e6 if m.group(2) == "Meg" else mult.get(m.group(2), 1))


def tune(params, trim1="r2", trim2="r11", target1=None, target2=1.0e-3):
    """Set the bias resistors.  Stage 2 has a trimmer (R11), always set for
    `target2`.  Stage 1: `trim1=None` leaves the fitted resistors alone;
    otherwise that resistor is re-selected for `target1` (default: the current
    the as-built stage 1 draws, so the variants compare like with like)."""
    p = dict(PARAMS); p.update(params)
    if trim1 and target1 is None:
        target1 = as_built_id1()
    for _ in range(14):
        i1, i2, v = _ids(p)
        ok = abs(i2/target2-1) < 2e-4
        # source voltage is nearly constant near the target, so scale R with I
        p[trim2] = f"{max(_num(p[trim2])*(i2/target2)**1.3, 1e-3):.5g}"
        if trim1:
            ok = ok and abs(i1/target1-1) < 2e-4
            p[trim1] = f"{max(_num(p[trim1])*(i1/target1)**1.3, 1e-3):.5g}"
        if ok:
            break
    p["_op"] = dict(id1=i1, id2=i2, p1=v["v(xchl.p1)"], p2=v["v(xchl.p2)"], k1=v["v(xchl.k1)"], k2=v["v(xchl.k2)"])
    return p


_AB = []
def as_built_id1():
    if not _AB:
        _AB.append(_ids(dict(PARAMS))[0])
    return _AB[0]


def clean(p):
    return {k: v for k, v in p.items() if not k.startswith("_")}


# name: (changes from the as-built parts list, stage-1 resistor to re-select or None)
SPECS = {
    "A as built (unit 1): U310s, R27 909R, R19 274R":   (dict(), None),
    "B high-gain build: R27 10R, R2 re-selected, C1 470u": (dict(r27="10", r2="1.9k", c1="470u"), "r2"),
    "C A with R19 = 1.5k (stage 2 degenerated)":        (dict(r19="1.5k", r11="400"), None),
    "D B with R19 = 1.5k":                              (dict(r27="10", r2="1.9k", c1="470u", r19="1.5k", r11="400"), "r2"),
    "E D with 2SK170 at Q7 (R27 22R, C1 1000u)":        (dict(jfet1="2SK170", r27="22", r2="330", c1="1000u", r19="1.5k", r11="400"), "r2"),
    "F A with C8 simply removed":                       (dict(c8=GONE), None),
}


def build():
    return {name: tune(d, t1) for name, (d, t1) in SPECS.items()}


if __name__ == "__main__":
    for name, p in build().items():
        o = p["_op"]
        print(f"{name}\n    R27={p['r27']} R2={p['r2']} R19={p['r19']} R11={p['r11']}  Id1={o['id1']*1e3:.3f}mA Id2={o['id2']*1e3:.3f}mA  plate1={o['p1']:.1f} plate2={o['p2']:.1f}  Vds(Q7)={o['k1']:.2f} Vds(Q6)~{o['k2']:.2f}")
