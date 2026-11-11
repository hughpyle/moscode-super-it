"""Supporting checks: pots/cable, PSRR, crosstalk, HF overload, sensitivities."""
import json, numpy as np
from measure import thd, ac, noise, at, riaa_err, snr_a
from simlib import run, table
from variants import build, clean, tune, GONE, LINK

V = build()
pick = lambda letter: clean([v for k, v in V.items() if k.startswith(letter)][0])
A, C, E = pick("A"), pick("C"), pick("E")
out = {}
SPOTS = (20, 50, 100, 500, 2000, 10000, 20000)


def summary(P, tag="s", extra=""):
    a = ac(tag, params=P, extra=extra); n = noise(tag + "_n", params=P, extra=extra)
    t05 = thd(tag + "_t", 0.5e-3, params=P, extra=extra); t5 = thd(tag + "_t", 5e-3, params=P, extra=extra)
    n_mm = noise(tag + "_nm", params=dict(P, rsrc="1k", lsrc="500m"), extra=extra)
    a_mm = ac(tag + "_am", params=dict(P, rsrc="1k", lsrc="500m"), extra=extra)
    e = riaa_err(a)
    return dict(gain=at(a, "out", 1000), en=float(np.interp(1000, n["f"], n["inn"]))*1e9,
                snr_mc=snr_a(n, a, 0.5e-3), snr_mm=snr_a(n_mm, a_mm, 5e-3),
                thd05=t05["out"]["thd"]*100, thd5=t5["out"]["thd"]*100,
                riaa={fx: float(np.interp(np.log10(fx), np.log10(a["f"]), e)) for fx in SPOTS})


def show(nm, r, riaa=False):
    s = (f"   {nm}: gain {r['gain']:.1f} dB, en {r['en']:.2f} nV/rtHz, S/N(A) MC {r['snr_mc']:.1f} / MM {r['snr_mm']:.1f} dB, "
         f"THD 0.5 mV {r['thd05']:.4f}%  5 mV {r['thd5']:.3f}%")
    if riaa:
        s += "\n        RIAA error: " + ", ".join(f"{k} Hz {v:+.2f}" for k, v in r["riaa"].items())
    print(s)


print("== 1. volume-pot position x cable capacitance (as built), response re full volume")
out["pot"] = {}
for cl in ("200p", "500p", "1n"):
    ref = None
    for att_db in (0, -6, -12, -20):
        k = 10**(att_db/20); ra = 100e3*(1-k) + 1e-3; rb = 100e3*k
        a = ac("pot", params=dict(A, r14a=f"{ra:.6g}", r14b=f"{rb:.6g}", cload=cl))
        y = (at(a, "out", 10000)-at(a, "out", 1000), at(a, "out", 20000)-at(a, "out", 1000))
        if ref is None: ref = y
        out["pot"][f"{cl},{att_db}"] = (y[0]-ref[0], y[1]-ref[1])
        print(f"   load {cl:>4}  volume {att_db:>4} dB: 10 kHz {y[0]-ref[0]:+.2f} dB   20 kHz {y[1]-ref[1]:+.2f} dB")

print("== 2. supply rejection and channel separation (as built)")
ctl = """
alter vinl ac=0
alter vvht ac=1
ac dec 10 10 100k
wrdata psrr_ht.txt vdb(outl) vdb(bp1) vdb(bp2) vdb(rail)
"""
run("psrr", params=A, control=ctl)
d = table("psrr_ht.txt"); f = d[:, 0]; g = lambda col, fx: float(np.interp(np.log10(fx), np.log10(f), d[:, col]))
for fx in (60, 120, 1000, 10000):
    print(f"   HT raw -> out {g(1,fx):6.1f} dB | -> B+1 {g(3,fx):6.1f} dB | -> B+2 {g(5,fx):6.1f} dB | -> rail {g(7,fx):6.1f} dB   @ {fx} Hz")
a = ac("xt", params=A)
print("   L->R crosstalk (shared supplies and shared V2 grid node; C21 not fitted): " + ", ".join(f"{fx} Hz {at(a,'outr',fx)-at(a,'out',fx):.0f} dB" for fx in (100, 1000, 10000, 20000)))
a = ac("xt2", params=dict(A, c21="220p"))
print("   same if a 220 pF C21 is fitted (unit 2 has a part there): " + ", ".join(f"{fx} Hz {at(a,'outr',fx)-at(a,'out',fx):.0f} dB" for fx in (100, 1000, 10000, 20000)))

print("== 3. treble overload: 10 kHz and 20 kHz tones at the level a 5 mV/1 kHz cartridge gives for equal recorded velocity")
for nm, P in (("A", A), ("C", C)):
    for f0, lev in ((10000, 5e-3*10**(13.734/20)), (20000, 5e-3*10**(19.62/20))):
        t = thd("hf", lev, f0=f0, params=P, cycles=40, settle=0.02)
        print(f"   {nm:5s} {f0/1000:.0f} kHz {lev*1e3:.1f} mV in: stage-1 plate {t['p1']['v']:.2f} V rms THD {t['p1']['thd']*100:.3f}%, output {t['out']['v']:.2f} V THD {t['out']['thd']*100:.3f}%")

print("== 4. sensitivity to the readings that are still uncertain (as-built circuit)")
show("as built (reference)", summary(A), riaa=True)
show("R7 = 24.3k", summary(dict(A, r7="24.3k")), riaa=True)
show("R7 = 24.3k and C1 = C8 = 220u", summary(dict(A, r7="24.3k", c1="220u", c8="220u")), riaa=True)
show("C1 = C8 = 220u only", summary(dict(A, c1="220u", c8="220u")), riaa=True)
show("R5 = 150k as on unit 2 (R11 re-trimmed)", summary(clean(tune(dict(r5="150k"), None))), riaa=True)
show("R9 = 560k instead of 681k", summary(dict(A, r9="560k")), riaa=True)
P = clean(tune(dict(jfet1="U310TYP", jfet2="U310TYP"), None))
lines, _ = run("typ_op", params=P, control="op\nprint @j.xchl.jq7[id] v(xchl.p1) v(xchl.k1) v(xchl.g1)")
print("   centre-of-data-sheet U310 (Vp -4 V, Idss 40 mA) with the fitted R27 + R2 (stage 2 re-trimmed): " + "; ".join(l.strip() for l in lines if "=" in l and "xchl" in l))
show("   ... its performance", summary(P))
show("12AT7 in V2 (R11 re-trimmed)", summary(clean(tune(dict(tube2="12AT7"), None))))
show("B+ 30 V lower (2 x 115 V zeners)", summary(clean(tune(dict(dz="DZ115"), None))))

print("== 5. channel-gain change if both JFETs have 30 % more beta and the resistors are left alone")
hi = (".model U310_HI NJF(Beta=4.6m Lambda=17m Vto=-2.6 Rd=1 Rs=1 Is=193.9f Cgd=4.11p Cgs=5.5p Pb=1 Fc=.5 Kf=13.56e-18 Af=1)")
gain = lambda P, extra="": at(ac("gs", params=P, extra=extra), "out", 1000)
for nm, P in (("A", A), ("C", C), ("F (C8 removed)", pick("F"))):
    print(f"   {nm}: {gain(dict(P, jfet1='U310_HI', jfet2='U310_HI'), hi)-gain(P):+.2f} dB")

print("== 6. grid current in the cascode triodes (representative law, not in the standard model)")
def gc(nm, P, tubes, lab):
    PP = clean(tune(dict(P, **tubes), None))
    t = thd("gc", 5e-3, params=PP); n = noise("gc_n", params=PP)
    lines, _ = run("gc_op", params=PP, control="op\nprint v(xchl.k1)-v(xchl.g1) v(xchl.k2)-v(vg2)")
    vals = [float(l.split("=")[1]) for l in lines if "=" in l and "xchl" in l]
    print(f"   {nm:3s} {lab:34s}: THD @5 mV {t['out']['thd']*100:.3f}% (H2 {t['out']['h2']*100:.3f}%), en {np.interp(1000,n['f'],n['inn'])*1e9:.2f} nV/rtHz, -Vgk V1 {vals[0]:.2f} V, V2 {vals[1]:.2f} V")
for nm, P in (("A", A), ("C", C)):
    gc(nm, P, dict(), "standard model (no grid current)")
    gc(nm, P, dict(tube1="12AX7G"), "grid current in V1 only")
    gc(nm, P, dict(tube2="12AX7G"), "grid current in V2 only")
    gc(nm, P, dict(tube2="12AT7"), "12AT7 in V2 (standard model)")

print("== 7. R27 as the gain / noise / linearity knob (U310 at Q7, R2 re-selected each time)")
out["r27"] = {}
for r19, r11 in (("274", "1.8k"), ("1.5k", "600")):
    print(f"   -- stage 2 with R19 = {r19}")
    for r27 in ("909", "470", "220", "100", "47", "22", "10"):
        P = clean(tune(dict(r27=r27, r2=f"{1909-float(r27):.0f}", r19=r19, r11=r11, c1=("100u" if r27 == "909" else "470u")), "r2"))
        r = summary(P); out["r27"][f"{r19},{r27}"] = dict(r, r2=P["r2"])
        show(f"R27={r27:>3} R2={float(P['r2']):5.0f}", r)

print("== 8. 2SK170 / LSK170 at Q7 (variant E): R27")
for r27 in ("10", "22", "47", "100"):
    P = clean(tune(dict(E, r27=r27), "r2"))
    show(f"R27={r27:>3} R2={float(P['r2']):5.0f}", summary(P))

print("== 9. stage 2: R19 as the gain / linearity knob (stage 1 as built)")
for r19, r11 in (("274", "1.8k"), ("560", "1.5k"), ("1k", "1.1k"), ("1.5k", "600"), ("2k", "100")):
    P = clean(tune(dict(r19=r19, r11=r11), None))
    show(f"R19={r19:>4} R11={float(P['r11']):5.0f}", summary(P))
json.dump(out, open("out/extras.json", "w"))
