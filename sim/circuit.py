"""Moscode / NYAL "SuperIt" Rev D/E - circuit description (single source of truth).

The scanned schematic gives the topology and reference designators but NO
component values or semiconductor types.  Every value below is therefore
tagged:

  K  known      - from the drawing or from owners' published notes
  P  photo      - read from board photographs (colour bands / markings); the note
                  says which unit and how sure the reading is.  "unit 1" is the
                  owner's complete rev-E board (dated 2-86), "unit 2" the owner's
                  earlier board (38-85, partly stripped), "web" the two photos
                  found on line.  The model follows unit 1.
  E  estimate   - engineering estimate; replace with the value read off the board

Parts are listed per block as  (ref, kind, nets, value, tag, note).
Kinds: R C CE(electrolytic, value "C,ESR") L D NJF(d g s) TRI(a g k)
       NMOS(d g s) NPN(c b e) X(subckt) V
`value` may contain {name} placeholders filled from PARAMS, so decks can be
re-generated with different values for sweeps and for the upgrade studies.
"""

PARAMS = dict(
    # ---- stage 1
    jfet1="U310", r27="909", r2="1k", c1="100u", r5="100k",
    tube1="12AX7", r8="1m",
    # ---- RIAA network (one passive network between the stages)
    r6="475k", c4="0.1u", r7="22.1k", c5="3.3n", c6="10n", r9="681k",
    # ---- stage 2
    jfet2="U310", r19="274", r11="1.836k", c8="100u", r10="100k", tube2="12AX7",
    r12="75k", c7="4.7u", c21="0.01p",
    # ---- output controls: pots written as upper/lower halves
    r13a="1m", r13b="100k",      # balance, shown at "no cut"
    r14a="1m", r14b="100k",      # volume, shown at maximum
    r25="475",
    # ---- test fixture
    rsrc="10", rin_load="1G", rload="100k", cload="200p",   # lsrc="500m" adds cartridge inductance (studies only)
    vraw="311", vhtr="20.5", dz="DZ130",
)

# One audio channel.  Ports: IN OUT BP1 BP2 VH VG2 XS
#   BP1/BP2 regulated B+ for stage 1 / stage 2,  VH +12 V heater rail,
#   VG2 shared V2 grid reference,  XS Q6 source (C21 goes to the other channel)
CHANNEL = [
    ("R1", "R", "IN 0", "47.5k", "P", "MM load; bands yellow-violet-green-red, clear"),
    ("R20", "R",   "IN sw20",     "10",      "E", "MC load, via S1A-1 (open)"),
    ("R21", "R",   "IN sw21",     "33",      "E", "MC load, via S1A-2 (open)"),
    ("R22", "R",   "IN sw22",     "100",     "E", "MC load, via S1A-3 (open)"),
    ("R23", "R",   "IN sw23",     "1k",      "E", "MC load, via S1A-4 (open)"),
    ("RSW", "R",   "IN 0",        "{rin_load}", "E", "stand-in for whichever S1A load is switched in"),
    ("R8", "R", "IN g7", "{r8}", "P", "0R link (tan body, single black band) on unit 1 and web; a real low-value resistor (about 22R) on unit 2"),
    ("Q7", "NJF", "k1 g7 s7", "{jfet1}", "P", "U310, marking clear on unit 1 (metal can)"),
    ("R27", "R", "s7 n2", "{r27}", "P", "909R on unit 1 (white-black-white-black-red, clear). 10R on the web photo: this unbypassed resistor sets the stage-1 gain"),
    ("R2", "R", "n2 0", "{r2}", "P", "1.00k on unit 1 and web (brown-black-black-brown-brown). Sets the bias with R27; selected on test per owners' notes"),
    ("C1", "CE", "n2 0", "{c1},0.5", "P", "source bypass across R2 only; 100 uF 16 V, same purple can as C8 (unit 1, IMG_5001: 16 V legible, value read on the unit by the owner)"),
    ("V1A", "TRI", "p1 g1 k1",    "{tube1}", "K", "pins 1,2,3"),
    ("V1B", "TRI", "p1 g1 k1",    "{tube1}", "K", "pins 6,7,8 - paralleled with V1A"),
    ("R5", "R", "BP1 p1", "{r5}", "P", "100k on unit 1 and web (owner note: 100 V drop at 1 mA). Unit 2 appears to have 150k 2 %"),
    ("R3", "R", "vg1 g1", "1m", "P", "0R link on unit 1 and web; about 22R on unit 2"),
    ("R4", "R", "VH vg1", "1k", "P", "1.00k on unit 1. Unit 2 has 475k in the R4 position"),
    ("C3",  "CE",  "vg1 0",       "100u,1",  "E", "grid reference decoupling"),
    ("R6", "R", "p1 n6", "{r6}", "P", "475k (yellow-violet-green-orange), clear on units 1 and 2"),
    ("C4", "C", "n6 g6", "{c4}", "P", "WIMA MKP 10, 0.1 uF 400 V on unit 1 (IMG_4993); 0.1 uF 400 V blue box on unit 2"),
    ("R7", "R", "g6 n7", "{r7}", "P", "22.1k 1 % on unit 1 (red-red-brown-red, brown; close-up IMG_4994, multiplier band checked by colour sample). Unit 2 looks the same"),
    ("C5", "C", "g6 n7", "{c5}", "P", "marked .0033/100V 332F (1 %), clear on the second photo"),
    ("C6", "C", "n7 0", "{c6}", "P", "marked .01 100V 103G (2 %), clear"),
    ("R9", "R", "g6 0", "{r9}", "P", "681k 1 % on unit 1: six bands, blue-grey-brown-orange, brown, red (close-up IMG_4996; the blue band is faint on the blue body)"),
    ("Q6", "NJF", "k2 g6 XS", "{jfet2}", "P", "U310, marking clear on unit 2; unit 1 has the same can (only the date code faces up)"),
    ("R19", "R", "XS n11", "{r19}", "P", "274R, red-violet-yellow-black on all boards. Unbypassed: sets the stage-2 gain"),
    ("R11", "R", "n11 0", "{r11}", "P", "BIAS trimmer marked 502 = 5k (unit 1, IMG_4998); shown set for 1 mA (100 V) in R10"),
    ("C8", "CE", "n11 0", "{c8},0.5", "P", "source bypass across the trimmer only; 100 uF 16 V, marking clear (unit 1, IMG_4999)"),
    ("V2",  "TRI", "p2 VG2 k2",   "{tube2}", "K", "V2A pins 1,2,3 (V2B 6,7,8 other channel)"),
    ("R10", "R", "BP2 p2", "{r10}", "P", "100k, bands clear on units 1 and 2"),
    ("Q5", "NMOS", "BP2 p2 s5", "BSS101", "P", "BSS101 (Siemens TO-92), marking clear on unit 1"),
    ("D10", "D",   "s5 p2",       "DZ12",    "E", "gate protection zener"),
    ("R12", "R", "s5 0", "{r12}", "P", "75k J power resistor, marking clear on units 1 and 2"),
    ("C7", "C", "s5 n13", "{c7}", "E", "output coupling: large red film box, value not legible"),
    ("R13A", "R", "n13 w13", "{r13a}", "P", "BAL pot 100k MN, upper part (shown at centre = no cut)"),
    ("R13B", "R", "w13 0", "{r13b}", "P", "BAL pot 100k MN, lower part"),
    ("R14A", "R", "w13 w14", "{r14a}", "P", "VOL pot 100k dual, upper part (shown at maximum)"),
    ("R14B", "R", "w14 0", "{r14b}", "P", "VOL pot 100k dual, lower part"),
    ("R25", "R", "w14 OUT", "{r25}", "P", "475R, probable"),
]
CHANNEL_PORTS = "IN OUT BP1 BP2 VH VG2 XS"

# Parts shared by both channels (audio side)
SHARED = [
    ("R24", "R", "VH VG2", "1k", "P", "1.00k probable (same pattern as R4 on unit 1)"),
    ("C22", "CE", "VG2 0", "33u,2", "P", "marked 33 uF"),
    ("C23", "C", "VG2 0", "1u", "E", "large red film box beside C22"),
    ("C21", "C", "XSL XSR", "{c21}", "P", "not fitted on unit 1 or the web boards (empty pads); 0.01p = open. Unit 2 has a small axial part here, value unread. On the drawing it links the two Q6 sources"),
]

# Power supply, common to both channels
PSU = [
    # high tension
    ("VHT", "V",   "hta htb",    "DC {vraw}", "K", "T1 220 VAC secondary, shown as its peak (DC) so the operating point solves"),
    ("L3",  "L",   "hta ac1",    "100u",    "E", ""),
    ("L4",  "L",   "htb ac2",    "100u",    "E", ""),
    ("D1",  "D",   "ac1 RAW",    "D1N4007", "E", ""),
    ("D2",  "D",   "ac2 RAW",    "D1N4007", "E", ""),
    ("D3",  "D",   "0 ac1",      "D1N4007", "E", ""),
    ("D4",  "D",   "0 ac2",      "D1N4007", "E", ""),
    ("C18", "CE",  "RAW 0",      "390u,0.3", "P", "reservoir: 390 uF 350 V on unit 1 (a 2024 replacement; original value unknown). Missing on unit 2"),
    ("R18", "R",   "RAW zref",   "47k",     "E", ""),
    ("D5",  "D",   "zmid zref",  "{dz}",    "E", "reference zener; voltage is an estimate (B+ must stay under the 250 V rating of C14)"),
    ("D6",  "D",   "0 zmid",     "{dz}",    "E", "reference zener"),
    ("C17", "CE",  "zref 0",     "10u,2",   "E", ""),
    ("Q1",  "NPN", "RAW zref e1", "HVNPN",  "E", ""),
    ("Q2",  "NPN", "RAW e1 RAIL", "HVNPN",  "E", ""),
    ("C16", "CE",  "RAIL 0",     "22u,2",   "E", ""),
    # floating supply and reference for IC2
    ("D9",  "D",   "NEG RAIL",   "DZ24",    "E", "op-amp supply zener"),
    ("C15", "CE",  "RAIL NEG",   "10u,2",   "E", ""),
    ("R15", "R", "NEG 0", "47k", "P", "marked 47K ohm J, clear (unit 1)"),
    ("R17", "R",   "RAIL VREF",  "100k",    "E", ""),
    ("R16", "R",   "VREF NEG",   "100k",    "E", ""),
    ("D7",  "D",   "VREF RAIL",  "D1N4148", "E", "input clamp"),
    ("D8",  "D",   "NEG VREF",   "D1N4148", "E", "input clamp"),
    ("C14", "C", "VREF 0", "1u", "P", "reference filter: WIMA 1.0 uF 250 V, marking clear on unit 2"),
    # two follower regulators sharing the reference
    ("IC2B", "X", "VREF BP2 RAIL NEG gq3", "OPAMP", "P", "LF353N on unit 1 and web; socket empty on unit 2"),
    ("Q3",  "NMOS", "RAIL gq3 BP2", "HVNMOS", "P", "VN0220N2 (TO-39) on unit 1; TO-92 part on unit 2. Generic model"),
    ("C12", "CE",  "BP2 0",      "22u,1",   "E", ""),
    ("C13", "C",   "BP2 0",      "0.22u",   "P", "WIMA MKP 10, 0.22 uF 250 V (unit 1, IMG_4995). The board silkscreen may number the rail films C11 and C12"),
    ("IC2A", "X", "VREF BP1 RAIL NEG gq4", "OPAMP", "P", "LF353N, marking clear"),
    ("Q4",  "NMOS", "RAIL gq4 BP1", "HVNMOS", "P", "VN0220N2 (TO-39) on unit 1; TO-92 part on unit 2. Generic model"),
    ("C10", "CE",  "BP1 0",      "22u,1",   "E", ""),
    ("C11", "C",   "BP1 0",      "0.22u",   "P", "WIMA MKP 10, 0.22 uF 250 V (unit 1, IMG_4995)"),
    # heaters
    ("VHTR", "V",  "hb hg",      "DC {vhtr}", "K", "T1 14.5 VAC secondary, shown as its peak (DC)"),
    ("L1",  "L",   "hb hac1",    "100u",    "E", ""),
    ("L2",  "L",   "hg hac2",    "100u",    "E", ""),
    ("CR1A", "D",  "hac1 hraw",  "D1N4007", "E", "CR1 bridge"),
    ("CR1B", "D",  "hac2 hraw",  "D1N4007", "E", "CR1 bridge"),
    ("CR1C", "D",  "0 hac1",     "D1N4007", "E", "CR1 bridge"),
    ("CR1D", "D",  "0 hac2",     "D1N4007", "E", "CR1 bridge"),
    ("C20", "CE",  "hraw 0",     "4700u,0.1", "E", ""),
    ("IC1", "X",   "hraw 0 VH",  "REG12",   "E", "12 V regulator"),
    ("C19", "CE",  "VH 0",       "100u,0.5", "E", ""),
    ("RH1", "R",   "VH 0",       "84",      "K", "V1 (R) heater, pins 4-5, 12.6 V 150 mA"),
    ("RH2", "R",   "VH 0",       "84",      "K", "V1 (L) heater"),
    ("RH3", "R",   "VH 0",       "84",      "K", "V2 heater"),
]


def _line(ref, kind, nets, value, p, prefix=""):
    v = value.format(**p)
    name = prefix + ref
    if kind == "R":
        return f"R{name} {nets} {v}"
    if kind == "C":
        return f"C{name} {nets} {v}"
    if kind == "L":
        return f"L{name} {nets} {v}"
    if kind == "CE":
        c, esr = v.split(",")
        return f"X{name} {nets} ELCAP C={c} ESR={esr}"
    if kind == "D":
        return f"D{name} {nets} {v}"
    if kind == "NJF":
        return f"J{name} {nets} {v}"
    if kind == "NMOS":
        return f"M{name} {nets} {v}"
    if kind == "NPN":
        return f"Q{name} {nets} {v}"
    if kind in ("TRI", "X"):
        return f"X{name} {nets} {v}"
    if kind == "V":
        return f"V{name} {nets} {v}"
    raise ValueError(kind)


def deck(title="SuperIt", params=None, source_l="AC 1", source_r="DC 0",
         extra="", control="", lib="../kicad/superit.lib"):
    """Return a complete two-channel + PSU ngspice deck."""
    p = dict(PARAMS)
    p.update(params or {})
    out = [f"* {title}", f".include {lib}", ""]
    out.append(f".subckt CHANNEL {CHANNEL_PORTS}")
    out += [_line(r, k, n, v, p) for r, k, n, v, *_ in CHANNEL]
    out.append(".ends CHANNEL\n")
    out.append("* --- test fixture: cartridge source and amplifier-input load, per channel")
    for ch, src in (("L", source_l), ("R", source_r)):
        out += [
            f"VIN{ch} gen{ch} 0 {src}",
            (f"RSRC{ch} gen{ch} IN{ch} {p['rsrc']}" if not p.get("lsrc") else
             f"LSRC{ch} gen{ch} gl{ch} {p['lsrc']}\nRSRC{ch} gl{ch} IN{ch} {p['rsrc']}"),
            f"XCH{ch} IN{ch} OUT{ch} BP1 BP2 VH VG2 XS{ch} CHANNEL",
            f"RLOAD{ch} OUT{ch} 0 {p['rload']}",
            f"CLOAD{ch} OUT{ch} 0 {p['cload']}",
        ]
    out.append("\n* --- shared audio parts")
    out += [_line(r, k, n, v, p) for r, k, n, v, *_ in SHARED]
    out.append("\n* --- power supply")
    out += [_line(r, k, n, v, p) for r, k, n, v, *_ in PSU]
    out += ["", ".options reltol=1e-5 abstol=1e-12 vntol=1e-6", extra, ""]
    if control:
        out += [".control", control.strip("\n"), ".endc"]
    out.append(".end\n")
    return "\n".join(out)


if __name__ == "__main__":
    print(deck())
