"""Power supply across the audio band and above: rail impedance, ripple
rejection, supply-to-output gain of the amplifier, regulator stability.

The rail capacitors C10 / C12 (and C16, C17, C15) are estimates, so they are
swept here: value and series resistance (ESR).  Results -> out/psu.json.
"""
import json, numpy as np
import circuit
from simlib import run, table
from variants import tune, clean

A = clean(tune(dict(), None))
BASE = list(circuit.PSU)
INJ = "IZ1 0 BP1 DC 0 AC 0\nIZ2 0 BP2 DC 0 AC 0"
SPOTS = (20, 60, 120, 1000, 10000, 20000, 100000, 1000000)


def caps(**kw):
    """Replace electrolytic values in the PSU table: caps(C10="22u,0.1", ...)."""
    circuit.PSU[:] = [(r, k, n, kw.get(r, v), t, note) for r, k, n, v, t, note in BASE]


def sweep(tag, params=A):
    ctl = f"""
alter vinl ac=0
alter iz1 ac=1
ac dec 40 1 10Meg
wrdata {tag}_z1.txt vdb(bp1) vdb(outl) vdb(outr) vdb(bp2)
alter iz1 ac=0
alter iz2 ac=1
ac dec 40 1 10Meg
wrdata {tag}_z2.txt vdb(bp2) vdb(outl)
alter iz2 ac=0
alter vvht ac=1
ac dec 40 1 10Meg
wrdata {tag}_ln.txt vdb(rail) vdb(vref) vdb(bp1) vdb(bp2) vdb(outl)
alter vvht ac=0
alter vinl ac=1
ac dec 40 1 10Meg
wrdata {tag}_sg.txt vdb(outl) vdb(xchl.p1)
"""
    run(tag, params=params, control=ctl, extra=INJ)
    z1, z2, ln, sg = (table(f"{tag}_{s}.txt") for s in ("z1", "z2", "ln", "sg"))
    f = z1[:, 0]
    return dict(f=f, z1=z1[:, 1], out_i1=z1[:, 3], outr_i1=z1[:, 5], z2=z2[:, 1], out_i2=z2[:, 3],
                rail=ln[:, 1], vref=ln[:, 3], bp1=ln[:, 5], bp2=ln[:, 7], out_ln=ln[:, 9],
                sig=sg[:, 1], p1=sg[:, 3])


def at(r, key, fx):
    return float(np.interp(np.log10(fx), np.log10(r["f"]), r[key]))


def ringing(esr, params=A):
    """0.1 mA load step on both rails; size of the ringing left 0.2-0.5 ms and 1-1.7 ms later (uV)."""
    caps(C10=f"22u,{esr}", C12=f"22u,{esr}")
    run("psu_st", params=params, control="tran 0.5u 3m 0.95m 0.5u\nlinearize v(bp1) v(bp2)\nwrdata psu_st.txt v(bp1) v(bp2)",
        extra="IZ1 0 BP1 DC 0 AC 0 PULSE(0 -0.1m 1m 1u 1u 20m 40m)\nIZ2 0 BP2 DC 0 AC 0 PULSE(0 -0.1m 1m 1u 1u 20m 40m)")
    d = table("psu_st.txt"); t = d[:, 0]; res = {}
    for nm, v in (("B+1", d[:, 1]), ("B+2", d[:, 3])):
        w = v - np.convolve(v, np.ones(400)/400, mode="same")       # remove the slow drift
        seg = lambda t0, t1: float(np.abs(w[(t > t0) & (t < t1)]).max()*1e6)
        res[nm] = (seg(1.2e-3, 1.5e-3), seg(2.0e-3, 2.7e-3))
    return res


def cx(d, i):
    return d[:, 3*i+1] + 1j*d[:, 3*i+2]


def separate(tag, params):
    """Gain from each supply rail, taken alone, to the output (two injections, solved together)."""
    ctl = f"""
alter vinl ac=0
alter iz1 ac=1
ac dec 20 10 1Meg
wrdata {tag}_a.txt v(bp1) v(bp2) v(outl)
alter iz1 ac=0
alter iz2 ac=1
ac dec 20 10 1Meg
wrdata {tag}_b.txt v(bp1) v(bp2) v(outl)
alter iz2 ac=0
alter izh ac=1
ac dec 20 10 1Meg
wrdata {tag}_h.txt v(vh) v(outl)
alter izh ac=0
alter vinl ac=1
ac dec 20 10 1Meg
wrdata {tag}_s.txt v(outl) v(outr)
alter vinl ac=0
alter vvht ac=1
ac dec 20 10 1Meg
wrdata {tag}_l.txt v(outl) v(bp1)
"""
    run(tag, params=params, control=ctl, extra=INJ + "\nIZH 0 VH DC 0 AC 0")
    a, b, h, sg, ln = (table(f"{tag}_{x}.txt") for x in "abhsl")
    v1a, v2a, oa, v1b, v2b, ob = cx(a, 0), cx(a, 1), cx(a, 2), cx(b, 0), cx(b, 1), cx(b, 2)
    det = v1a*v2b - v2a*v1b
    db = lambda z: 20*np.log10(np.abs(z))
    return dict(f=a[:, 0], g1=db((oa*v2b - ob*v2a)/det), g2=db((v1a*ob - v1b*oa)/det), gh=db(cx(h, 1)/cx(h, 0)),
                sig=db(cx(sg, 0)), xt=db(cx(sg, 1)/cx(sg, 0)), raw_out=db(cx(ln, 0)), raw_bp1=db(cx(ln, 1)))


out = {}
print("== 1. as modelled (C10 = C12 = 22 uF with 1 ohm ESR, 0.22 uF film in parallel)")
caps()
r = sweep("psu0"); out["base"] = {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in r.items()}
print("   freq      Zout B+1   Zout B+2 | raw->rail  raw->B+1  raw->out")
for fx in SPOTS:
    z1, z2 = 10**(at(r, "z1", fx)/20), 10**(at(r, "z2", fx)/20)
    print(f"   {fx:>7} Hz {z1:8.3f} ohm {z2:7.3f} ohm | {at(r,'rail',fx):7.1f} dB {at(r,'bp1',fx):7.1f} dB {at(r,'out_ln',fx):7.1f} dB")

print("== 1b. the amplifier's own supply rejection: gain from each rail alone to the output, and the same referred to the input")
out["sens"] = {}
for lab, P in (("A as built", A), ("B high-gain build (R27 10R)", clean(tune(dict(r27="10", r2="1.9k", c1="470u"), "r2"))),
               ("C (R19 1.5k)", clean(tune(dict(r19="1.5k", r11="600"), None)))):
    q = separate("psus", P); out["sens"][lab[0]] = {k: v.tolist() for k, v in q.items()}
    print("   " + lab)
    for fx in SPOTS:
        g = lambda k: float(np.interp(np.log10(fx), np.log10(q["f"]), q[k]))
        print(f"   {fx:>8} Hz: B+1->out {g('g1'):+6.1f}  B+2->out {g('g2'):+6.1f}  12V->out {g('gh'):+6.1f}  signal {g('sig'):+6.1f} dB |"
              f" referred to input: B+1 {g('g1')-g('sig'):+6.1f}  B+2 {g('g2')-g('sig'):+6.1f}  12V {g('gh')-g('sig'):+6.1f}  raw supply {g('raw_out')-g('sig'):+7.1f} dB | L->R crosstalk {g('xt'):+7.1f} dB")

print("== 2. rail capacitor ESR and value: highest rail impedance between 100 Hz and 1 MHz")
out["esr"] = {}
for c in ("22u", "47u", "100u"):
    for esr in ("10", "3", "1", "0.3", "0.1", "0.02"):
        caps(C10=f"{c},{esr}", C12=f"{c},{esr}")
        r = sweep("psue")
        m = (r["f"] >= 100) & (r["f"] <= 1e6)
        row = {}
        for rail, key in (("B+1", "z1"), ("B+2", "z2")):
            z = 10**(r[key][m]/20); i = int(np.argmax(z))
            row[rail] = dict(zpk=float(z.max()), fpk=float(r["f"][m][i]), z1k=10**(at(r, key, 1000)/20), z20k=10**(at(r, key, 20000)/20))
        out["esr"][f"{c},{esr}"] = dict(row, f=r["f"].tolist(), z1=r["z1"].tolist(), z2=r["z2"].tolist(), bp1=r["bp1"].tolist())
        a, b = row["B+1"], row["B+2"]
        print(f"   C {c:>4} ESR {esr:>4} ohm: B+1 highest {a['zpk']:6.2f} ohm at {a['fpk']/1e3:6.1f} kHz (1 kHz {a['z1k']:.3f}, 20 kHz {a['z20k']:.2f})"
              f" | B+2 highest {b['zpk']:6.2f} ohm at {b['fpk']/1e3:6.1f} kHz (20 kHz {b['z20k']:.2f})")
print("   ringing left on the rails after a 0.1 mA load step, 22 uF (uV at 0.2-0.5 ms, then at 1-1.7 ms):")
for esr in ("1", "0.1", "0.02"):
    q = ringing(esr)
    print(f"   ESR {esr:>4} ohm: " + "; ".join(f"{k} {v[0]:.1f} then {v[1]:.1f}" for k, v in q.items()))

print("== 3. pre-regulator capacitors (C16 rail, C17 zener, C15 op-amp supply, C18 reservoir): effect on ripple rejection")
for lab, kw in (("as modelled", dict()),
                ("all four with 0.1 ohm ESR", dict(C16="22u,0.1", C17="10u,0.1", C15="10u,0.1", C18="390u,0.1")),
                ("C17 100 uF", dict(C17="100u,1")),
                ("C16 100 uF", dict(C16="100u,1")),
                ("C14 (reference) 4.7 uF", dict(C14="4.7u")),
                ("C18 100 uF (a guess at the original)", dict(C18="100u,2"))):
    caps(**kw); r = sweep("psup")
    print(f"   {lab:38s}: raw->B+1 " + ", ".join(f"{fx} Hz {at(r,'bp1',fx):.0f}" for fx in (60, 120, 1000, 10000)) +
          " | raw->out " + ", ".join(f"{fx} Hz {at(r,'out_ln',fx):.0f}" for fx in (60, 120, 1000, 10000)) + " dB")
caps()
json.dump(out, open("out/psu.json", "w"))
