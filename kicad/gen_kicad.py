#!/usr/bin/env python3
"""Generate the KiCad project for the Moscode / NYAL "SuperIt" Rev D.

    python gen_kicad.py

Reads the parts tables in ../sim/circuit.py (CHANNEL, SHARED, PSU, PARAMS) and
writes, next to this script:

    superit.kicad_pro     project (ERC and simulator settings)
    superit.kicad_sch     root sheet: power supply, shared parts, test fixture,
                          and the two channel sheets
    channel.kicad_sch     one audio channel, used twice (L and R)
    superit_kicad.lib     wrappers so multi-unit packages (dual triode with
                          heater, dual op-amp, bridge) map onto the single-section
                          models in superit.lib

Values, tags (K/P/E) and notes come from circuit.py, so after editing that
file just run this again.  Only the layout lives here.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "sim"))

import circuit                      # noqa: E402
from kisch import Sheet, uid        # noqa: E402

PROJECT = "superit"
LIB = "superit.lib"
KLIB = "superit_kicad.lib"
P = circuit.PARAMS
TAGS = {"K": "known (drawing / owners' notes)", "P": "read from board photographs",
        "E": "estimate"}


def table(rows):
    """{ref: (kind, [nets], value, tag, note)} with PARAMS substituted."""
    return {r: (k, n.split(), v.format(**P), t, note) for r, k, n, v, t, note in rows}


CH, SH, PS = table(circuit.CHANNEL), table(circuit.SHARED), table(circuit.PSU)
placed = set()


def info(ref, *also):
    """Look a part up in the tables and remember that it has been drawn."""
    for tbl in (CH, SH, PS):
        if ref in tbl:
            placed.add(ref)
            placed.update(also)
            return tbl[ref]
    raise KeyError(ref)


def notes(ref, extra=None):
    kind, nets, value, tag, note = info(ref)
    f = {"Status": "%s - %s" % (tag, TAGS[tag])}
    if note:
        f["Note"] = note
    f.update(extra or {})
    return f


# ----------------------------------------------------------------- part helpers
def res(sh, ref, x, y, horiz=False, name=None, **kw):
    """Resistor.  Vertical: pin 1 on top.  Horizontal: pin 1 on the left."""
    value = info(ref)[2]
    if horiz:
        kw.setdefault("rp", (0, -1.2, None))
        kw.setdefault("vp", (0, 1.2, None))
    return sh.sym(name or ref, "Device:R", x, y, rot=90 if horiz else 0, value=value,
                  fields=notes(ref), **kw)


def cap(sh, ref, x, y, horiz=False, name=None, **kw):
    """Capacitor: film (kind C) or electrolytic with ESR (kind CE, + on top)."""
    kind, nets, value, tag, note = info(ref)
    if horiz:
        kw.setdefault("rp", (0, -1.6, None))
        kw.setdefault("vp", (0, 1.6, None))
    else:
        kw.setdefault("rp", (1.4, -0.5, "left"))
        kw.setdefault("vp", (1.4, 0.5, "left"))
    if kind == "CE":
        c, esr = value.split(",")
        f = notes(ref, {"Sim.Library": LIB, "Sim.Name": "ELCAP", "Sim.Device": "SUBCKT",
                        "Sim.Pins": "1=P 2=N", "Sim.Params": "C=%s ESR=%s" % (c, esr)})
        return sh.sym(name or ref, "Device:C_Polarized", x, y, rot=90 if horiz else 0,
                      value=c, fields=f, **kw)
    return sh.sym(name or ref, "Device:C", x, y, rot=90 if horiz else 0, value=value,
                  fields=notes(ref), **kw)


def ind(sh, ref, x, y, **kw):
    kw.setdefault("rp", (0, -1.3, None))
    kw.setdefault("vp", (0, 1.1, None))
    return sh.sym(ref, "Device:L", x, y, rot=90, value=info(ref)[2], fields=notes(ref), **kw)


def dio(sh, ref, x, y, k="up", **kw):
    """Diode, cathode pointing up / down / left / right."""
    model = info(ref)[2]
    rot = {"up": 270, "down": 90, "left": 0, "right": 180}[k]
    lib = "Device:D_Zener" if model.startswith("DZ") else "Device:D"
    f = notes(ref, {"Sim.Library": LIB, "Sim.Name": model, "Sim.Device": "D",
                    "Sim.Pins": "1=K 2=A"})
    if k in ("left", "right"):
        kw.setdefault("rp", (0, -1.5, None))
        kw.setdefault("vp", (0, 1.5, None))
    return sh.sym(ref, lib, x, y, rot=rot, value=model, fields=f, **kw)


def jfet(sh, ref, x, y, **kw):
    model = info(ref)[2]
    f = notes(ref, {"Sim.Library": LIB, "Sim.Name": model, "Sim.Device": "NJFET",
                    "Sim.Pins": "1=D 2=G 3=S"})
    kw.setdefault("rp", (2.0, -0.6, "left"))
    kw.setdefault("vp", (2.0, 0.6, "left"))
    return sh.sym(ref, "Device:Q_NJFET_DGS", x, y, value=model, fields=f, **kw)


def nmos(sh, ref, x, y, **kw):
    model = info(ref)[2]
    f = notes(ref, {"Sim.Library": LIB, "Sim.Name": model, "Sim.Device": "NMOS",
                    "Sim.Type": "VDMOS", "Sim.Pins": "D=D G=G S=S"})
    kw.setdefault("rp", (2.2, -0.6, "left"))
    kw.setdefault("vp", (2.2, 0.6, "left"))
    return sh.sym(ref, "Device:Q_NMOS", x, y, value=model, fields=f, **kw)


def npn(sh, ref, x, y, **kw):
    model = info(ref)[2]
    f = notes(ref, {"Sim.Library": LIB, "Sim.Name": model, "Sim.Device": "NPN",
                    "Sim.Type": "GUMMELPOON", "Sim.Pins": "C=C B=B E=E"})
    kw.setdefault("rp", (2.0, -0.6, "left"))
    kw.setdefault("vp", (2.0, 0.6, "left"))
    return sh.sym(ref, "Device:Q_NPN", x, y, value=model, fields=f, **kw)


def triode(sh, ref, tube, x, y, unit, **kw):
    """One unit of an ECC83.  Unit 2 = pins 1,2,3; unit 1 = pins 6,7,8; unit 3 = heater."""
    f = {"Status": "K - " + TAGS["K"],
         "Note": "dual triode + heater; model %s_DUAL wraps two %s sections" % (tube, tube),
         "Sim.Library": KLIB, "Sim.Name": tube + "_DUAL", "Sim.Device": "SUBCKT",
         "Sim.Pins": "1=A1 2=G1 3=K1 6=A2 7=G2 8=K2 4=H4 5=H5"}
    kw.setdefault("rp", (2.3, -0.6, "left"))
    kw.setdefault("vp", (2.3, 0.6, "left"))
    return sh.sym(ref, "Valve:ECC83", x, y, unit=unit, value=tube, fields=f, **kw)


def pot(sh, ref, x, y, pos, **kw):
    """Potentiometer from the two halves REFA (upper) / REFB (lower) in circuit.py.
    Drawn with pin 3 (hot end) on top; pos = 1 puts the wiper at the top."""
    upper, lower = info(ref + "A")[2], info(ref + "B")[2]
    note = info(ref + "A")[4]
    total = lower                       # tables carry the pot at one end: upper part ~ 0
    f = {"Status": "%s - %s" % (info(ref + "A")[3], TAGS[info(ref + "A")[3]]),
         "Note": note + " | circuit.py: %sA=%s, %sB=%s" % (ref, upper, ref, lower),
         "Sim.Device": "R", "Sim.Type": "POT", "Sim.Pins": "1=r0 2=wiper 3=r1",
         "Sim.Params": "r=%s pos=%s" % (total, pos)}
    kw.setdefault("rp", (-1.2, -0.5, "right"))
    kw.setdefault("vp", (-1.2, 0.5, "right"))
    return sh.sym(ref, "Device:R_Potentiometer", x, y, mirror="x", value=total, fields=f, **kw)


def vsrc(sh, ref, x, y, params, shown, sin=False, note=None, **kw):
    f = {"Sim.Device": "V", "Sim.Type": "SIN" if sin else "DC", "Sim.Pins": "1=+ 2=-",
         "Sim.Params": params}
    if note:
        f["Note"] = note
    kw.setdefault("rp", (2.2, -0.6, "left"))
    kw.setdefault("vp", (2.2, 0.6, "left"))
    return sh.sym(ref, "Simulation_SPICE:VSIN" if sin else "Simulation_SPICE:VDC", x, y,
                  value=shown, fields=f, **kw)


def flag(sh, pt):
    sh._pwr += 1
    return sh.sym("#FLG%02d" % sh._pwr, "power:PWR_FLAG", pt[0], pt[1], value="PWR_FLAG",
                  show_value=False)


def legend(rows, extra=()):
    """Text block: which parts carry which tag."""
    out = ["Where the values come from (hidden fields Status / Note on every part say more):"]
    for tag in "KPE":
        refs = []
        for r, row in rows.items():
            if row[3] != tag:
                continue
            r = re.sub(r"^(R1[34])[AB]$", r"\1", r)
            r = re.sub(r"^(CR1|IC2|V1)[A-D]$", r"\1", r)
            if r not in refs:
                refs.append(r)
        if refs:
            out.append("  %s  %s: %s" % (tag, TAGS[tag], " ".join(refs)))
    return "\n".join(out + list(extra))


# ============================================================ channel sheet
def build_channel(root_uuid, sheet_uuids):
    def right(ref):
        if ref in ("V2",):
            return ref
        m = re.match(r"(#?[A-Za-z]+?)(\d+)$", ref)
        return "%s%d" % (m.group(1), int(m.group(2)) + 100)

    sh = Sheet(PROJECT, "channel", "channel.kicad_sch", "A3",
               'Moscode "SuperIt" Rev D - audio channel',
               ["Sheet used twice (LEFT, RIGHT); right-channel refs are +100",
                "Values from ../sim/circuit.py - regenerate with gen_kicad.py"],
               instances=[("/%s/%s" % (root_uuid, sheet_uuids[0]), lambda r: r),
                          ("/%s/%s" % (root_uuid, sheet_uuids[1]), right)])
    W = sh.wire

    # ---- input: J1, cartridge loading switch S1A + R20..R23, R1, stand-in load
    Y = 58                                  # signal line of the first stage
    j1 = sh.sym("J1", "Connector:Conn_Coaxial", 10, Y, mirror="y", value="PHONO IN",
                exclude_sim=True, rp=(0, -2.4, None), vp=(0, -1.5, None))
    sh.gnd(j1.pin(2))
    sh.hlabel("IN", (15, 53), rot=90)
    W((15, 53), (15, Y))
    W(j1.pin(1), (54.5, Y))
    s1 = sh.sym("S1", "Switch:SW_DIP_x04", 23, 66, value="S1A  cartridge load", exclude_sim=True,
                rp=(0, -3.4, None), vp=(0, 3.2, None))
    W((20, Y), (20, 67))                    # switch pins 1..4 sit on this drop
    for i, ref in enumerate(("R20", "R21", "R22", "R23")):
        y = 64 + i
        r = res(sh, ref, 29.5, y, horiz=True, rp=(4.2, 0, "left"), vp=(7.6, 0, "left"))
        W((26, y), r.pin(1))
        W(r.pin(2), (32, y))
    W((32, 64), (32, 68))
    sh.gnd((32, 68))
    r1 = res(sh, "R1", 44, 63)
    W((44, Y), r1.pin(1))
    sh.gnd(r1.pin(2))
    rsw = res(sh, "RSW", 50, 63, name="RSW1")
    W((50, Y), rsw.pin(1))
    sh.gnd(rsw.pin(2))
    sh.text("RSW1: stand-in for the S1A\nload in use (simulation only)", (40, 66.8), size=1.0)
    r8 = res(sh, "R8", 56, Y, horiz=True)

    # ---- stage 1: Q7 under the paralleled halves of V1
    q7 = jfet(sh, "Q7", 66, Y)
    W(r8.pin(2), q7.pin(2))
    v1a = triode(sh, "V1", P["tube1"], 64, 40, unit=2, rp=(-1.6, -3.6, "right"), vp=(-1.6, -2.7, "right"))
    v1b = triode(sh, "V1", P["tube1"], 74, 40, unit=1, rp=(2.4, -0.6, "left"), vp=(2.4, 0.5, "left"))
    info("V1A", "V1B")
    ka, kb = v1a.pin(3), v1b.pin(8)
    W(ka, (ka[0], 48), (kb[0], 48), kb)                 # cathode bus
    W(q7.pin(1), (67, 48))
    sh.label("k1", (68, 48))
    aa, ab = v1a.pin(1), v1b.pin(6)
    W(aa, (aa[0], 32), (ab[0], 32), ab)                 # plate bus
    r5 = res(sh, "R5", 69, 25)
    W(r5.pin(2), (69, 32))
    W(r5.pin(1), (69, 18))
    sh.hlabel("BP1", (69, 18), rot=90)
    ga, gb = v1a.pin(2), v1b.pin(7)
    W(gb, (69, 40), (69, 46), (58, 46), (58, 40), ga)   # grid link (crosses V1 pin 3 lead)
    r3 = res(sh, "R3", 53, 40, horiz=True)
    W(r3.pin(2), (58, 40))
    W(r3.pin(1), (47, 40), (47, 26))
    r4 = res(sh, "R4", 41, 26, horiz=True)
    W(r4.pin(2), (47, 26))
    W(r4.pin(1), (36, 26), (36, 18))
    sh.hlabel("VH", (36, 18), rot=90)
    c3 = cap(sh, "C3", 42, 34, rp=(-1.4, -0.5, "right"), vp=(-1.4, 0.5, "right"))
    W((47, 31), (42, 31), c3.pin(1))
    sh.gnd(c3.pin(2))
    r27 = res(sh, "R27", 67, 63.5)
    W(q7.pin(3), r27.pin(1))
    r2 = res(sh, "R2", 67, 70)
    W(r27.pin(2), r2.pin(1))
    sh.gnd(r2.pin(2))
    c1 = cap(sh, "C1", 61, 70, rp=(-1.4, -0.5, "right"), vp=(-1.4, 0.5, "right"))
    W(c1.pin(1), (61, 67), (67, 67))
    sh.gnd(c1.pin(2))

    # ---- passive RIAA network between the stages
    r6 = res(sh, "R6", 83, 32, horiz=True)
    W((ab[0], 32), r6.pin(1))
    sh.label("p1", (76.5, 32))
    c4 = cap(sh, "C4", 90, 43)
    W(r6.pin(2), (90, 32), c4.pin(1))
    W(c4.pin(2), (90, Y))
    r7 = res(sh, "R7", 90, 64)
    c5 = cap(sh, "C5", 98, 64)
    W((90, Y), r7.pin(1))
    W((98, Y), c5.pin(1))
    W(r7.pin(2), (90, 68), (98, 68), c5.pin(2))
    c6 = cap(sh, "C6", 94, 72)
    W((94, 68), c6.pin(1))
    sh.gnd(c6.pin(2))
    r9 = res(sh, "R9", 106, 64)
    W((106, Y), r9.pin(1))
    sh.gnd(r9.pin(2))

    # ---- stage 2: Q6 under one half of V2, MOSFET follower Q5
    q6 = jfet(sh, "Q6", 116, Y)
    W((90, Y), q6.pin(2))
    sh.label("g6", (100, Y))
    v2 = triode(sh, "V2", P["tube2"], 118, 44, unit=2, inst_units=[2, 1])
    info("V2")
    W(v2.pin(3), q6.pin(1))
    W(v2.pin(2), (110, 44))
    sh.hlabel("VG2", (110, 44), rot=180)
    r19 = res(sh, "R19", 117, 64)
    W(q6.pin(3), r19.pin(1))
    W((117, 61), (123, 61))
    sh.hlabel("XS", (123, 61), rot=0)
    r11 = res(sh, "R11", 117, 70.5)
    W(r19.pin(2), r11.pin(1))
    sh.gnd(r11.pin(2))
    sh.text("BIAS", (118.2, 72.2), size=1.0)
    c8 = cap(sh, "C8", 111, 70.5, rp=(-1.4, -0.5, "right"), vp=(-1.4, 0.5, "right"))
    W(c8.pin(1), (111, 67), (117, 67))
    sh.gnd(c8.pin(2))
    r10 = res(sh, "R10", 118, 25)
    W(r10.pin(2), v2.pin(1))
    W(r10.pin(1), (118, 18))
    sh.hlabel("BP2", (118, 18), rot=90)
    q5 = nmos(sh, "Q5", 131, 32)
    W((118, 32), q5.pin("G"))
    sh.label("p2", (119, 32))
    W(q5.pin("D"), (132, 20), (118, 20))
    d10 = dio(sh, "D10", 127, 38, k="left", rp=(0, 1.5, None), vp=(0, 2.5, None))
    W(d10.pin(1), (124, 38), (124, 32))
    W(d10.pin(2), (132, 38))
    r12 = res(sh, "R12", 132, 52)
    W(q5.pin("S"), r12.pin(1))
    sh.gnd(r12.pin(2))
    sh.label("s5", (132, 42))

    # ---- output: C7, BAL, VOL, R25, J2
    c7 = cap(sh, "C7", 137.5, 44, horiz=True)
    W((132, 44), c7.pin(1))
    r13 = pot(sh, "R13", 142, 51, pos=1)
    W(c7.pin(2), (142, 44), r13.pin(3))
    sh.gnd(r13.pin(1))
    sh.text("BAL", (140.8, 52.2), size=1.0, just="right top")
    r14 = pot(sh, "R14", 149, 51, pos=1)
    W(r13.pin(2), (145, 51), (145, 44), (149, 44), r14.pin(3))
    sh.gnd(r14.pin(1))
    sh.text("VOL", (147.8, 52.2), size=1.0, just="right top")
    r25 = res(sh, "R25", 153.5, 51, horiz=True)
    W(r14.pin(2), r25.pin(1))
    j2 = sh.sym("J2", "Connector:Conn_Coaxial", 158, 57, value="OUT", exclude_sim=True,
                rp=(0, -2.4, None), vp=(0, -1.5, None))
    W(r25.pin(2), (156, 51), (156, 57))
    sh.gnd(j2.pin(2))
    W((156, 51), (156, 46))
    sh.hlabel("OUT", (156, 46), rot=90)

    # ---- notes
    sh.text('MOSCODE "SUPER IT" - NEW YORK AUDIO LABS   Rev D   -   AUDIO CIRCUIT, ONE CHANNEL',
            (8, 7), size=2.2, bold=True)
    sh.text(legend(CH, [
        "",
        "Q7 / Q6 are U310 metal-can JFETs (model: low-pinch-off corner of the data sheet, see superit.lib).",
        "R3 and R8 are wire links on the photographed board (1 mOhm here so the netlist keeps them).",
        "R13 / R14: pot wiper position is Sim.Params pos (1 = full level, 0 = off).",
        "S1 and J1 / J2 are excluded from simulation; RSW1 stands in for the selected S1A load.",
        "V1: both halves in parallel (pins 1,2,3 and 6,7,8).  V2: this channel uses one half,",
        "the other channel the other half (the stock ECC83 symbol letters the 1-2-3 half 'B').",
    ]), (8, 82), size=1.27)
    sh.text("STAGE 1: JFET + 12AX7 cascode", (58, 77), size=1.5)
    sh.text("PASSIVE RIAA", (90, 77), size=1.5)
    sh.text("STAGE 2: JFET + 12AX7 cascode,\nMOSFET follower", (110, 77), size=1.5)
    return sh


# ============================================================ root sheet
def build_root():
    sh = Sheet(PROJECT, "root", "superit.kicad_sch", "A3",
               'Moscode "SuperIt" Rev D - power supply and test fixture',
               ["Reconstructed from the Rev D scan; values from ../sim/circuit.py",
                "Simulate: Inspect > Simulator, then Run"],
               instances=None)
    sh.instances = [("/" + sh.uuid, lambda r: r)]
    sh._pwr = 300
    W = sh.wire

    # ---------------- high tension: T1 secondary, bridge, zener-referenced Darlington
    vht = vsrc(sh, "VHT1", 12, 33, "dc=%s" % P["vraw"], "%s V" % P["vraw"],
               note=info("VHT")[4], rp=(-1.8, -0.6, "right"), vp=(-1.8, 0.6, "right"))
    sh.text("T1 220 VAC winding,\nshown as its peak (DC)", (13.5, 35.6), size=1.0)
    l3 = ind(sh, "L3", 20, 28)
    l4 = ind(sh, "L4", 20, 40)
    W(vht.pin(1), (12, 28), l3.pin(1))
    W(vht.pin(2), (12, 40), l4.pin(1))
    d1 = dio(sh, "D1", 28, 24)
    d3 = dio(sh, "D3", 28, 33)
    d2 = dio(sh, "D2", 40, 24)
    d4 = dio(sh, "D4", 40, 33)
    W(d1.pin(2), d3.pin(1))
    W(d2.pin(2), d4.pin(1))
    W(l3.pin(2), (28, 28))
    W(l4.pin(2), (35, 40), (35, 30), (40, 30))
    sh.gnd(d3.pin(2))
    sh.gnd(d4.pin(2))
    RAWY = 20
    W(d1.pin(1), (28, RAWY), (76, RAWY))
    W(d2.pin(1), (40, RAWY))
    sh.label("RAW", (42, RAWY))
    c18 = cap(sh, "C18", 48, 26)
    W((48, RAWY), c18.pin(1))
    sh.gnd(c18.pin(2))
    r18 = res(sh, "R18", 55, 24)
    W((55, RAWY), r18.pin(1))
    d5 = dio(sh, "D5", 55, 31)
    d6 = dio(sh, "D6", 55, 36)
    W(r18.pin(2), d5.pin(1))
    W(d5.pin(2), d6.pin(1))
    sh.gnd(d6.pin(2))
    c17 = cap(sh, "C17", 62, 33)
    W((55, 27.5), (62, 27.5), c17.pin(1))
    sh.gnd(c17.pin(2))
    q1 = npn(sh, "Q1", 68, 27.5)
    W((62, 27.5), q1.pin("B"))
    W(q1.pin("C"), (69, RAWY))
    q2 = npn(sh, "Q2", 75, 29.5)
    W(q1.pin("E"), q2.pin("B"))
    W(q2.pin("C"), (76, RAWY))

    # ---------------- floating op-amp supply, reference, two follower regulators
    RY, NY = 50, 66
    W(q2.pin("E"), (76, RY))
    W((16, RY), (116, RY))
    sh.label("RAIL", (17, RY))
    flag(sh, (33.5, RY))
    c16 = cap(sh, "C16", 16, 55)
    W((16, RY), c16.pin(1))
    sh.gnd(c16.pin(2))
    d9 = dio(sh, "D9", 24, 58)
    W((24, RY), d9.pin(1))
    W(d9.pin(2), (24, NY))
    c15 = cap(sh, "C15", 30, 58)
    W((30, RY), c15.pin(1))
    W(c15.pin(2), (30, NY))
    r15 = res(sh, "R15", 24, 71)
    W((24, NY), r15.pin(1))
    sh.gnd(r15.pin(2))
    W((24, NY), (51, NY))
    sh.label("NEG", (31, NY))
    flag(sh, (27, NY))
    icf = {"Status": "%s - %s" % (info("IC2A", "IC2B")[3], TAGS[info("IC2A")[3]]),
           "Note": info("IC2A")[4] + "; model OPAMP_DUAL wraps two OPAMP sections",
           "Sim.Library": KLIB, "Sim.Name": "OPAMP_DUAL", "Sim.Device": "SUBCKT",
           "Sim.Pins": "1=OUTA 2=INNA 3=INPA 4=VN 5=INPB 6=INNB 7=OUTB 8=VP"}
    ic2c = sh.sym("IC2", "Amplifier_Operational:TL072", 38, 58, unit=3, value="LF353N",
                  fields=icf, rp=(0.6, -0.6, "left"), vp=(0.6, 0.6, "left"))
    W((37, RY), ic2c.pin(8))
    W(ic2c.pin(4), (37, NY))
    r17 = res(sh, "R17", 45, 54)
    r16 = res(sh, "R16", 45, 62)
    W((45, RY), r17.pin(1))
    W(r17.pin(2), r16.pin(1))
    W(r16.pin(2), (45, NY))
    d7 = dio(sh, "D7", 51, 54)
    d8 = dio(sh, "D8", 51, 62)
    W((51, RY), d7.pin(1))
    W(d7.pin(2), d8.pin(1))
    W(d8.pin(2), (51, NY))
    VY = 58
    W((45, VY), (51, VY))
    W((51, VY), (64, VY))
    sh.label("VREF", (59, VY))
    c14 = cap(sh, "C14", 58, 61.5)
    W((58, VY), c14.pin(1))
    sh.gnd(c14.pin(2))

    def follower(x0, unit, pins, qref, ce, cf, net, vref_from):
        op = sh.sym("IC2", "Amplifier_Operational:TL072", x0 + 4, 57, unit=unit, value="LF353N",
                    fields=icf, rp=(0.6, -2.3, "left"), vp=(0.6, 2.3, "left"))
        q = nmos(sh, qref, x0 + 13, 57)
        W(op.pin(pins[2]), q.pin("G"))
        W(q.pin("D"), (x0 + 14, RY))
        W(q.pin("S"), (x0 + 14, 61), (x0, 61), (x0, 58), op.pin(pins[1]))
        W(vref_from, op.pin(pins[0]))
        W((x0 + 14, 61), (x0 + 26, 61))
        c_e = cap(sh, ce, x0 + 19, 64.5)
        c_f = cap(sh, cf, x0 + 24, 64.5)
        W((x0 + 19, 61), c_e.pin(1))
        W((x0 + 24, 61), c_f.pin(1))
        sh.gnd(c_e.pin(2))
        sh.gnd(c_f.pin(2))
        sh.label(net, (x0 + 26, 61))

    W((64, VY), (64, 56))
    follower(68, 1, (3, 2, 1), "Q4", "C10", "C11", "BP1", (64, 56))
    W((64, VY), (64, 71), (100, 71), (100, 56))
    follower(102, 2, (5, 6, 7), "Q3", "C12", "C13", "BP2", (100, 56))

    # ---------------- heater supply
    vh = vsrc(sh, "VHTR1", 88, 33, "dc=%s" % P["vhtr"], "%s V" % P["vhtr"],
              note=info("VHTR")[4], rp=(-1.8, -0.6, "right"), vp=(-1.8, 0.6, "right"))
    sh.text("T1 14.5 VAC winding,\nshown as its peak (DC)", (89.5, 35.6), size=1.0)
    l1 = ind(sh, "L1", 95, 27)
    l2 = ind(sh, "L2", 95, 39)
    W(vh.pin(1), (88, 27), l1.pin(1))
    W(vh.pin(2), (88, 39), l2.pin(1))
    info("CR1A", "CR1B", "CR1C", "CR1D")
    cr1 = sh.sym("CR1", "Device:D_Bridge_+-AA", 104, 33, value="4 x 1N4007",
                 fields={"Status": "E - " + TAGS["E"], "Note": "bridge; model BRIDGE = 4 x D1N4007",
                         "Sim.Library": KLIB, "Sim.Name": "BRIDGE", "Sim.Device": "SUBCKT",
                         "Sim.Pins": "1=P 2=N 3=AC1 4=AC2"},
                 rp=(2.2, -3.6, "left"), vp=(2.2, 3.6, "left"))
    W(l1.pin(2), (104, 27), cr1.pin(3))
    W(l2.pin(2), (104, 39), cr1.pin(4))
    W(cr1.pin(2), (100, 33), (100, 34))
    sh.gnd((100, 34))
    HY = 24
    W(cr1.pin(1), (108, 33), (108, HY), (116, HY))
    flag(sh, (110, HY))
    c20 = cap(sh, "C20", 113, 29)
    W((113, HY), c20.pin(1))
    sh.gnd(c20.pin(2))
    ic1 = sh.sym("IC1", "Regulator_Linear:L7812", 119, HY, value="7812",
                 fields=notes("IC1", {"Sim.Library": LIB, "Sim.Name": "REG12", "Sim.Device": "SUBCKT",
                                      "Sim.Pins": "1=IN 2=GND 3=OUT"}),
                 rp=(0, -2.6, None), vp=(0, -1.6, None))
    sh.gnd(ic1.pin(2))
    W(ic1.pin(3), (130, HY), (130, 38), (153, 38))
    sh.label("VH", (123, HY))
    c19 = cap(sh, "C19", 126, 29)
    W((126, HY), c19.pin(1))
    sh.gnd(c19.pin(2))
    for ref, tube, x, rh, who in (("V1", P["tube1"], 136, "RH2", "V1 (L)"),
                                  ("V101", P["tube1"], 145, "RH1", "V1 (R)"),
                                  ("V2", P["tube2"], 154, "RH3", "V2")):
        info(rh)
        h = triode(sh, ref, tube, x, 30, unit=3, rp=(0, -4.2, None), vp=(0, -3.3, None))
        W(h.pin(4), (x - 1, 38))
        sh.noconnect(h.pin(9))
        sh.gnd(h.pin(5))
    sh.text("HEATERS, pins 4-5 (12.6 V).  The 84 ohm heater of each tube is inside its SPICE model\n"
            "(RH1..RH3 in circuit.py).", (131, 40), size=1.0)

    # ---------------- shared audio parts: V2 grid reference
    r24 = res(sh, "R24", 138, 56, horiz=True)
    W((133, 56), r24.pin(1))
    sh.label("VH", (133, 56))
    W(r24.pin(2), (152, 56))
    sh.label("VG2", (152, 56))
    c22 = cap(sh, "C22", 143, 60)
    c23 = cap(sh, "C23", 148.5, 60)
    W((143, 56), c22.pin(1))
    W((148.5, 56), c23.pin(1))
    sh.gnd(c22.pin(2))
    sh.gnd(c23.pin(2))
    sh.text("V2 grid reference (both halves)", (133, 51.5), size=1.0)

    # ---------------- the two channels with their test fixtures
    BY = 78

    def channel(name, x, tag, page, xs_side, src_params, src_shown):
        pins = [("IN", "L", 3), ("VH", "L", 7), ("VG2", "L", 10),
                ("BP1", "R", 7), ("BP2", "R", 10), ("OUT", "R", 3), ("XS", xs_side, 14)]
        su, pt = sh.subsheet(name, "channel.kicad_sch", x, BY, 16, 16, pins, page)
        n = {"L": "1", "R": "2"}[tag]
        v = vsrc(sh, "VIN" + n, x - 22, BY + 8, src_params, src_shown, sin=True,
                 note="cartridge: " + src_shown)
        sh.gnd(v.pin(2))
        rs = sh.sym("RSRC" + n, "Device:R", x - 13, BY + 3, rot=90, value=P["rsrc"],
                    fields={"Note": "cartridge source resistance (test fixture)"},
                    rp=(0, -1.2, None), vp=(0, 1.2, None))
        W(v.pin(1), (x - 22, BY + 3), rs.pin(1))
        W(rs.pin(2), pt["IN"])
        sh.label("IN" + tag, (x - 9.5, BY + 3))
        for pn in ("VH", "VG2"):
            W(pt[pn], (x - 4, pt[pn][1]))
            sh.label(pn, (x - 4, pt[pn][1]), rot=180, just="right bottom")
        for pn in ("BP1", "BP2"):
            W(pt[pn], (x + 20, pt[pn][1]))
            sh.label(pn, (x + 20, pt[pn][1]))
        rl = sh.sym("RLOAD" + n, "Device:R", x + 26, BY + 7.5, value=P["rload"],
                    fields={"Note": "next stage input resistance (test fixture)"})
        cl = sh.sym("CLOAD" + n, "Device:C", x + 33, BY + 7.5, value=P["cload"],
                    fields={"Note": "cable + input capacitance (test fixture)"},
                    rp=(1.4, -0.5, "left"), vp=(1.4, 0.5, "left"))
        W(pt["OUT"], (x + 33, BY + 3), cl.pin(1))
        W((x + 26, BY + 3), rl.pin(1))
        sh.gnd(rl.pin(2))
        sh.gnd(cl.pin(2))
        sh.label("OUT" + tag, (x + 20, BY + 3))
        return su, pt

    suL, ptL = channel("LEFT", 34, "L", 2, "R", "dc=0 ampl=0.5m f=1k ac=1",
                       "0.5 mV pk, 1 kHz, AC 1")
    suR, ptR = channel("RIGHT", 110, "R", 3, "L", "dc=0 ampl=0 f=1k ac=0",
                       "0 V (undriven)")
    c21 = cap(sh, "C21", 80, BY + 17, horiz=True, rp=(0, -1.6, None), vp=(0, 1.6, None))
    W(ptL["XS"], (56, BY + 14), (56, BY + 17), c21.pin(1))
    W(c21.pin(2), (104, BY + 17), (104, BY + 14), ptR["XS"])
    sh.label("XSL", (58, BY + 17))
    sh.label("XSR", (98, BY + 17))
    flag(sh, (8, 74))
    sh.gnd((8, 74))

    # ---------------- notes and the default analysis
    sh.text('MOSCODE "SUPER IT" - NEW YORK AUDIO LABS   Rev D   -   POWER SUPPLY (COMMON TO BOTH CHANNELS)',
            (5, 6), size=2.2, bold=True)
    rows = dict(PS)
    rows.update(SH)
    sh.text(legend(rows, [
        "T1 (transformer box), fuses F1 / F2 and the mains side are not drawn; VHT1 / VHTR1 stand for the two secondaries.",
        "IC2 is an LF353N (both sections follow the same filtered reference VREF; Q4 feeds stage 1, Q3 stage 2 + followers).",
    ]), (5, 9.5), size=1.1)
    sh.text(".ac dec 50 10 100k", (5, 99), size=1.6)
    sh.text(".options reltol=1e-5 abstol=1e-12 vntol=1e-6", (5, 100.6), size=1.1)
    sh.text("Simulation: the two lines above go into the netlist; the first is the analysis KiCad runs\n"
            "(Inspect > Simulator, Run).  Edit it, or set another analysis in the simulator, e.g.\n"
            "     .tran 5u 20m 10m      1 kHz, 0.5 mV sine from VIN1 (left channel); plot V(/OUTL)\n"
            "     .op                          DC operating point\n"
            "Useful signals: /OUTL  /OUTR  /INL  /LEFT/p1  /LEFT/g6  /LEFT/p2  /LEFT/s5  /BP1  /BP2  /VREF",
            (5, 102.2), size=1.1)
    return sh, (suL, suR)


# ============================================================ support files
def write_wrappers(path):
    tubes = sorted({P["tube1"], P["tube2"], "12AX7", "12AT7"})
    out = ["* KiCad-side wrappers for the SuperIt project (generated by gen_kicad.py).",
           "* KiCad attaches one SPICE model to a whole multi-unit symbol, so the dual",
           "* triode (with its heater), the dual op-amp and the bridge rectifier are",
           "* wrapped here around the single-section models in superit.lib.", ""]
    for t in tubes:
        out += ["* %s dual triode, heater pins 4-5 (12.6 V, 150 mA)" % t,
                ".subckt %s_DUAL A1 G1 K1 A2 G2 K2 H4 H5" % t,
                "XA A1 G1 K1 %s" % t, "XB A2 G2 K2 %s" % t, "RH H4 H5 84", ".ends", ""]
    out += ["* dual op-amp package, 8-pin DIP numbering order",
            ".subckt OPAMP_DUAL OUTA INNA INPA VN INPB INNB OUTB VP",
            "XA INPA INNA VP VN OUTA OPAMP", "XB INPB INNB VP VN OUTB OPAMP", ".ends", "",
            "* bridge rectifier",
            ".subckt BRIDGE P N AC1 AC2",
            "DA AC1 P D1N4007", "DB AC2 P D1N4007", "DC N AC1 D1N4007", "DD N AC2 D1N4007",
            ".ends", ""]
    with open(path, "w") as f:
        f.write("\n".join(out))


PIN_MAP = [  # KiCad default ERC matrix, except output-to-output (paralleled V1 anodes) is allowed
    [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2],
    [0, 0, 0, 1, 0, 0, 1, 0, 2, 2, 2, 2],
    [0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 2],
    [0, 1, 0, 0, 0, 0, 1, 1, 2, 1, 1, 2],
    [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2],
    [1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 2],
    [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 2],
    [0, 2, 1, 2, 0, 0, 1, 0, 2, 2, 2, 2],
    [0, 2, 0, 1, 0, 0, 1, 0, 2, 0, 0, 2],
    [0, 2, 1, 1, 0, 0, 1, 0, 2, 0, 0, 2],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]


def write_project(path, root, subs):
    pro = {
        "meta": {"filename": PROJECT + ".kicad_pro", "version": 3},
        "erc": {
            "pin_map": PIN_MAP,
            # Analogue circuit: gates, grids and op-amp inputs are fed through
            # passive parts, which KiCad's digital-minded rule would flag.
            "rule_severities": {"pin_not_driven": "ignore", "simulation_model_issue": "warning"},
        },
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "schematic": {
            "legacy_lib_dir": "", "legacy_lib_list": [],
            "ngspice": {"fix_include_paths": True, "meter_command": "",
                        "model_mode": 1, "workbook_filename": ""},
        },
        "sheets": [[root.uuid, "Root"], [subs[0], "LEFT"], [subs[1], "RIGHT"]],
        "text_variables": {},
    }
    with open(path, "w") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")


def main():
    root, subs = build_root()
    chan = build_channel(root.uuid, subs)
    every = set(CH) | set(SH) | set(PS)
    missing = sorted(every - placed)
    if missing:
        raise SystemExit("parts in circuit.py that are not drawn: " + " ".join(missing))
    with open(os.path.join(HERE, "superit.kicad_sch"), "w") as f:
        f.write(root.render(root=True))
    with open(os.path.join(HERE, "channel.kicad_sch"), "w") as f:
        f.write(chan.render())
    write_wrappers(os.path.join(HERE, KLIB))
    write_project(os.path.join(HERE, PROJECT + ".kicad_pro"), root, subs)
    print("wrote superit.kicad_pro, superit.kicad_sch, channel.kicad_sch, %s" % KLIB)


if __name__ == "__main__":
    main()
