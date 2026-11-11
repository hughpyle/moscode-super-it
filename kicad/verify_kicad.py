#!/usr/bin/env python3
"""Check the generated KiCad project against ../sim/circuit.py.

    python verify_kicad.py            (after gen_kicad.py)

1. ERC through kicad-cli.
2. Export the SPICE netlist KiCad's simulator would use, expand it and the
   reference deck (circuit.deck()) in ngspice, and compare them element by
   element: same parts, same connections, same values and models.
3. Solve the DC operating point and the 1 kHz gain of both and compare.

The KiCad netlist uses ngspice's "potentiometer" code model for R13 / R14, so
the code models are loaded first, as KiCad's simulator does.
"""
import ctypes
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sim"))
NGLIB = "/Applications/KiCad/KiCad.app/Contents/PlugIns/sim/libngspice.dylib"
CMDIR = "/Applications/KiCad/KiCad.app/Contents/PlugIns/sim/ngspice/"
SYMMETRIC = "rcl"
NNODES = dict(r=2, c=2, l=2, d=2, v=2, i=2, b=2, j=3, m=3, q=3, g=4, e=4)


# ------------------------------------------------------------------ ngspice
def ngspice_child(deck, commands):
    out = []
    ng = ctypes.CDLL(NGLIB)
    PF = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
    EF = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool,
                          ctypes.c_int, ctypes.c_void_p)
    BF = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)

    def pr(s, i, p):
        line = s.decode(errors="replace")
        for pre in ("stdout ", "stderr "):
            if line.startswith(pre):
                line = line[len(pre):]
        print(line)
        return 0

    cbs = (PF(pr), PF(lambda s, i, p: 0), EF(lambda *a: 0), BF(lambda *a: 0))
    ng.ngSpice_Init(cbs[0], cbs[1], cbs[2], None, None, cbs[3], None)
    for cm in ("analog", "xtradev"):
        ng.ngSpice_Command(("codemodel %s%s.cm" % (CMDIR, cm)).encode())
    ng.ngSpice_Command(("source " + deck).encode())
    for c in commands:
        ng.ngSpice_Command(("echo @@@ " + c).encode())
        ng.ngSpice_Command(c.encode())
    return out


def ngspice(deck, commands):
    """Run commands on a deck in a fresh ngspice; return [(command, [lines])]."""
    r = subprocess.run([sys.executable, __file__, "--ng", deck] + list(commands),
                       capture_output=True, text=True, timeout=900)
    res = [("", [])]
    for line in (r.stdout + r.stderr).splitlines():
        if line.startswith("@@@ "):
            res.append((line[4:], []))
        else:
            res[-1][1].append(line)
    bad = [l for l in res[0][1] if re.search(r"(?i)\berror\b|unknown|unable|singular", l)]
    if bad:
        raise SystemExit("ngspice could not load %s:\n  %s" % (deck, "\n  ".join(bad[:10])))
    return res


def num(s):
    m = re.match(r"^([-+]?[0-9.]+(?:e[-+]?\d+)?)(meg|mil|[tgkmunpf])?[a-z]*$", s.lower())
    if not m:
        return None
    mult = dict(t=1e12, g=1e9, meg=1e6, k=1e3, m=1e-3, u=1e-6, n=1e-9, p=1e-12, f=1e-15,
                mil=25.4e-6).get(m.group(2), 1.0)
    return float(m.group(1)) * mult


# ------------------------------------------------------------------ element lists
def elements(listing):
    """[(name, [nodes], rest)] from `listing expand`, plus pot models."""
    els, models = [], {}
    for line in listing:
        m = re.match(r"^\s*\d+ : (\S+)\s+(.*)$", line)
        if not m:
            continue
        name, rest = m.group(1).lower(), m.group(2).strip()
        if name == ".model":
            mm = re.match(r"(\S+)\s+potentiometer\(\s*r=(\S+)\s+position=(\S+)\s*\)", rest)
            if mm:
                models[mm.group(1)] = (num(mm.group(2)), float(mm.group(3)))
            continue
        if name.startswith(".") or name.startswith("*") or (name, rest) == ("kicad", "schematic"):
            continue                            # directives, comments, KiCad's title line
        toks = rest.split()
        if name[0] == "a":                      # potentiometer -> two resistors
            r0, wiper, r1, model = toks[:4]
            els.append((name, [r0, wiper, r1], model))
            continue
        n = NNODES[name[0]]
        els.append((name, toks[:n], " ".join(toks[n:])))
    out = []
    for name, nodes, rest in els:
        if name[0] == "a":
            r, pos = models[rest]
            out.append(("r." + name + ".lower", [nodes[1], nodes[0]], repr(r * pos)))
            out.append(("r." + name + ".upper", [nodes[2], nodes[1]], repr(r * (1 - pos))))
        else:
            out.append((name, nodes, rest))
    return out


def split_name(name):
    """'c.xchl.xc1.cx' -> ['xchl', 'xc1', 'cx'];  'rr24' -> ['rr24']"""
    parts = name.split(".")
    return parts[1:] if len(parts) > 1 and len(parts[0]) == 1 else parts


def key_reference(name):
    """Canonical (channel, REF, sub...) for an element of circuit.deck()."""
    p = split_name(name)
    fixture = {"vinl": "VIN1", "vinr": "VIN2", "rsrcl": "RSRC1", "rsrcr": "RSRC2",
               "rloadl": "RLOAD1", "rloadr": "RLOAD2", "cloadl": "CLOAD1", "cloadr": "CLOAD2"}
    if p[0] in fixture:
        return ("T", fixture[p[0]]) + tuple(p[1:])
    ch = "T"
    if p[0] in ("xchl", "xchr"):
        ch = p[0][-1].upper()
        p = p[1:]
    return (ch, p[0][1:].upper()) + tuple(p[1:])


def key_kicad(name, chan_refs):
    """Canonical key for an element of the KiCad netlist."""
    p = split_name(name)
    head = p[0].upper()
    sub = tuple(p[1:])
    # KiCad puts the SPICE device letter in front of a reference that lacks it
    ref = head[1:] if head[0] in "JMXA" else head
    base, n = re.match(r"^([A-Z]+?)(\d+)$", ref).groups()
    n = int(n)
    if base == "V" and n in (1, 101, 2):        # dual triodes, heater inside
        heater = {1: "RH2", 101: "RH1", 2: "RH3"}[n]
        if sub == ("rh",):
            return ("T", heater)
        half = sub[0]
        if n == 2:
            return ({"xa": "L", "xb": "R"}[half], "V2") + sub[1:]
        return ("L" if n == 1 else "R", "V1" + {"xa": "A", "xb": "B"}[half]) + sub[1:]
    if ref == "IC2":
        return ("T", "IC2" + sub[0][-1].upper()) + sub[1:]
    if ref == "CR1":
        return ("T", "CR1" + sub[0][-1].upper()) + sub[1:]
    if base in ("R",) and n in (13, 14, 113, 114) and sub:
        ch = "L" if n < 100 else "R"
        return (ch, "R%d%s" % (n % 100, {"upper": "A", "lower": "B"}[sub[0]]))
    if ref in ("VHT1", "VHTR1"):
        return ("T", ref[:-1])
    if base == "RSW":
        return ("L" if n == 1 else "R", "RSW")
    if ref in chan_refs:
        return ("L", ref) + sub
    if n > 100 and "%s%d" % (base, n - 100) in chan_refs:
        return ("R", "%s%d" % (base, n - 100)) + sub
    return ("T", ref) + sub


def same_value(a, b):
    a, b = a.strip().lower(), b.strip().lower()
    if re.sub(r"\s+", "", a) == re.sub(r"\s+", "", b):
        return True
    ta, tb = a.split(), b.split()
    if len(ta) != len(tb):
        return False
    for x, y in zip(ta, tb):
        if x == y or x.split(":")[-1] == y.split(":")[-1]:
            continue
        nx, ny = num(x), num(y)
        if nx is None or ny is None:
            return False
        if abs(nx - ny) > max(1.5e-3 if max(abs(nx), abs(ny)) < 2e-3 else 0, 1e-9 * abs(nx)):
            return False
    return True


def compare(ref_els, kc_els, chan_refs):
    ref = {key_reference(n): (n, nodes, rest) for n, nodes, rest in ref_els}
    kc = {key_kicad(n, chan_refs): (n, nodes, rest) for n, nodes, rest in kc_els}
    problems = []
    for k in sorted(set(ref) - set(kc)):
        problems.append("missing from KiCad netlist: %s (%s)" % (ref[k][0], k))
    for k in sorted(set(kc) - set(ref)):
        problems.append("extra in KiCad netlist: %s (%s)" % (kc[k][0], k))
    fwd, back = {"0": "0"}, {"0": "0"}

    def bind(a, b):
        if fwd.get(a, b) != b or back.get(b, a) != a:
            return False
        fwd[a], back[b] = b, a
        return True

    def fits(na, nb):
        return all(fwd.get(a, b) == b and back.get(b, a) == a for a, b in zip(na, nb)) and \
            len({(a, b) for a, b in zip(na, nb)}) == len(set(na)) == len(set(nb))

    # A part with one end left open (the S1A load resistors with the switch
    # open) may be drawn at either side of the switch: only its value matters.
    def uses(els):
        cnt = {}
        for _, nodes, _ in els:
            for x in set(nodes):
                cnt[x] = cnt.get(x, 0) + 1
        return cnt
    ru, ku = uses(ref_els), uses(kc_els)
    open_ended = {k for k in set(ref) & set(kc)
                  if any(ru[x] == 1 for x in ref[k][1]) and any(ku[x] == 1 for x in kc[k][1])}
    pending = [k for k in sorted(ref) if k in kc and k not in open_ended]
    progress = True
    while pending and progress:
        progress, later = False, []
        for k in pending:
            (rn, rnodes, _), (kn, knodes, _) = ref[k], kc[k]
            if rn[0] in SYMMETRIC:
                options = [o for o in (knodes, knodes[::-1]) if fits(rnodes, o)]
                options = [list(x) for x in {tuple(o) for o in options}]
                if len(options) == 0:
                    problems.append("connection differs: %s %s  vs  %s %s" % (rn, rnodes, kn, knodes))
                    progress = True
                    continue
                if len(options) > 1:
                    later.append(k)
                    continue
                knodes = options[0]
            if not all(bind(a, b) for a, b in zip(rnodes, knodes)):
                problems.append("connection differs: %s %s  vs  %s %s" % (rn, rnodes, kn, knodes))
            progress = True
        pending = later
    for k in pending:                           # isolated two-terminal parts: either way round
        for a, b in zip(ref[k][1], kc[k][1]):
            bind(a, b)

    def mapped(expr):
        return re.sub(r"v\(([^)]*)\)", lambda m: "v(" + ",".join(
            fwd.get(x.strip(), "?" + x.strip()) for x in m.group(1).split(",")) + ")", expr)

    for k in sorted(set(ref) & set(kc)):
        rv, kv = mapped(ref[k][2]), kc[k][2]
        if not same_value(re.sub(r"\s+", " ", rv), re.sub(r"\s+", " ", kv)):
            problems.append("value differs: %s '%s'  vs  %s '%s'" % (ref[k][0], ref[k][2], kc[k][0], kc[k][2]))
    return problems, fwd, len(set(ref) & set(kc)), sorted(ref[k][0] for k in open_ended)


def vectors(lines, cplx=False):
    out = {}
    for line in lines:
        m = re.match(r"^(\S+) = ([-+0-9.e]+)(?:,([-+0-9.e]+))?\s*$", line.strip())
        if m:
            v = float(m.group(2))
            if cplx and m.group(3) is not None:
                v = complex(v, float(m.group(3)))
            out[m.group(1).lower()] = v
    return out


def main():
    import math
    import circuit
    tmp = tempfile.mkdtemp(prefix="superit_verify_")
    sch = os.path.join(HERE, "superit.kicad_sch")
    ok = True

    # ---- 1. ERC
    rpt = os.path.join(tmp, "erc.json")
    subprocess.run(["kicad-cli", "sch", "erc", "--severity-all", "--format", "json", "-o", rpt, sch],
                   capture_output=True, text=True)
    erc = json.load(open(rpt))
    viol = [(v["severity"], v["type"], v["description"], s.get("path", ""),
             "; ".join(i.get("description", "") for i in v.get("items", [])))
            for s in erc.get("sheets", []) for v in s.get("violations", [])]
    print("ERC: %d violation(s)" % len(viol))
    for v in viol:
        print("   %s %s: %s [%s] %s" % v)
    ok &= not [v for v in viol if v[0] == "error"]

    # ---- 2. netlists
    kc_deck = os.path.join(tmp, "kicad_export.cir")
    r = subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "spice", "-o", kc_deck, sch],
                       capture_output=True, text=True)
    if not os.path.exists(kc_deck):
        raise SystemExit("netlist export failed:\n" + r.stdout + r.stderr)
    ref_deck = os.path.join(tmp, "reference.cir")
    with open(ref_deck, "w") as f:
        f.write(circuit.deck(lib=os.path.join(HERE, "superit.lib"),
                             source_l="DC 0 SIN( 0 0.5m 1k 0 0 0 ) AC 1",
                             source_r="DC 0 SIN( 0 0 1k 0 0 0 ) AC 0"))
    cmds = ["listing expand", "op", "print all", "ac lin 1 1k 1k", "print all"]
    ref = ngspice(ref_deck, cmds)
    kc = ngspice(kc_deck, cmds)
    chan_refs = {re.sub(r"^(R1[34])[AB]$", r"\1", r) for r, *_ in circuit.CHANNEL}
    problems, fwd, n, loose = compare(elements(dict(ref)["listing expand"]),
                               elements(dict(kc)["listing expand"]), chan_refs)
    print("Netlist: %d expanded elements compared, %d difference(s)" % (n, len(problems)))
    for p in problems:
        print("   " + p)
    if loose:
        print("   (open-ended parts, value only: %s)" % " ".join(loose))
    ok &= not problems

    # ---- 3. operating point and gain
    def after(res, analysis):
        return res[[c for c, _ in res].index(analysis) + 1][1]

    rop, kop = vectors(after(ref, "op")), vectors(after(kc, "op"))
    worst, where, cnt = 0.0, "", 0
    for a, b in fwd.items():
        if a in rop and b in kop:
            cnt += 1
            d = abs(rop[a] - kop[b])
            if d > worst:
                worst, where = d, "%s / %s" % (a, b)
    print("Operating point: %d node voltages compared, largest difference %.3g V (%s)" % (cnt, worst, where))
    ok &= cnt > 50 and worst < 5e-3          # solver tolerance on ~250 V nodes
    show = [("bp1", "B+ stage 1"), ("bp2", "B+ stage 2"), ("rail", "pre-regulator rail"),
            ("neg", "op-amp negative rail"), ("vh", "heater rail"),
            ("xchl.p1", "stage-1 plate"), ("xchl.k1", "Q7 drain / V1 cathodes"),
            ("xchl.p2", "stage-2 plate"), ("xchl.s5", "Q5 source")]
    for node, what in show:
        if node in rop and fwd.get(node) in kop:
            print("   %-24s reference %9.3f V   KiCad %9.3f V   (%s)" % (what, rop[node], kop[fwd[node]], fwd[node]))
    rac, kac = vectors(after(ref, "ac lin 1 1k 1k"), True), vectors(after(kc, "ac lin 1 1k 1k"), True)
    for a, what in (("outl", "gain L, 1 kHz"), ("outr", "crosstalk into R, 1 kHz")):
        ga = 20 * math.log10(abs(rac[a]) + 1e-30)
        gb = 20 * math.log10(abs(kac[fwd[a]]) + 1e-30)
        print("   %-24s reference %9.3f dB  KiCad %9.3f dB" % (what, ga, gb))
        ok &= abs(ga - gb) < (0.01 if ga > -100 else 1.0)
    print("RESULT:", "PASS" if ok else "FAIL")
    print("(files kept in %s)" % tmp)
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--ng":
        ngspice_child(sys.argv[2], sys.argv[3:])
    else:
        sys.exit(main())
