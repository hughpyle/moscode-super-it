"""Run the comparison study and save results to out/study.json."""
import json, numpy as np
from measure import thd, ac, noise, at, riaa_err, integ, a_weight_db, snr_a
from variants import build, clean

LEVELS = [0.1e-3, 0.2e-3, 0.5e-3, 1e-3, 2e-3, 5e-3, 10e-3, 20e-3, 50e-3]
res = {}
for i, (name, p) in enumerate(build().items()):
    tag = "v" + name[0]
    pp = clean(p)
    a = ac(tag + "_ac", params=pp)
    err = riaa_err(a)
    m = (a["f"] >= 20) & (a["f"] <= 20000)
    n_mc = noise(tag + "_nmc", params=pp)                               # 10 ohm source
    n_mm = noise(tag + "_nmm", params=dict(pp, rsrc="1k", lsrc="500m"))  # typical MM
    a_mm = ac(tag + "_acmm", params=dict(pp, rsrc="1k", lsrc="500m"))
    r = dict(params=pp, op=p["_op"],
             gain1k=at(a, "out", 1000), st1=at(a, "g6", 1000), st2=at(a, "out", 1000)-at(a, "g6", 1000),
             p1gain1k=at(a, "p1", 1000), p1gain20k=at(a, "p1", 20000),
             riaa_max=float(np.abs(err[m]).max()),
             riaa_spots={str(fx): float(np.interp(np.log10(fx), np.log10(a["f"]), err)) for fx in (20, 50, 100, 200, 500, 2000, 5000, 10000, 20000)}, f=a["f"].tolist(), out=a["out"].tolist(), err=err.tolist(),
             en1k=float(np.interp(1000, n_mc["f"], n_mc["inn"])), en100=float(np.interp(100, n_mc["f"], n_mc["inn"])),
             nf=n_mc["f"].tolist(), inn=n_mc["inn"].tolist(),
             snr_mc=snr_a(n_mc, a, 0.5e-3), snr_mm=snr_a(n_mm, a_mm, 5e-3),
             levels=LEVELS, thd=[], h2=[], h3=[], vout=[], thd_p1=[], thd_g6=[])
    for v in LEVELS:
        t = thd(f"{tag}_thd", v, params=pp)
        r["thd"].append(t["out"]["thd"]); r["h2"].append(t["out"]["h2"]); r["h3"].append(t["out"]["h3"])
        r["vout"].append(t["out"]["v"]); r["thd_p1"].append(t["p1"]["thd"]); r["thd_g6"].append(t["g6"]["thd"])
    res[name] = r
    lv = np.array(LEVELS); th = np.array(r["thd"])
    ov = float(np.exp(np.interp(np.log(0.01), np.log(th), np.log(lv)))) if th.max() > 0.01 else float("nan")
    r["vin_1pct"] = ov
    print(f"{name}\n   gain {r['gain1k']:.1f} dB (st1+EQ {r['st1']:.1f}, st2 {r['st2']:.1f}) RIAA +-{r['riaa_max']:.2f} dB | en@1k {r['en1k']*1e9:.2f} nV/rtHz"
          f" | S/N(A) MC 0.5mV {r['snr_mc']:.1f} dB, MM 5mV {r['snr_mm']:.1f} dB | THD 0.5mV {r['thd'][2]*100:.4f}%  5mV {r['thd'][5]*100:.3f}%  20mV {r['thd'][7]*100:.2f}% | 1% THD at {ov*1e3:.1f} mV in"
          f" | out @5mV {r['vout'][5]:.2f} V | en@100 {r['en100']*1e9:.2f}\n   RIAA error re 1 kHz: "
          + ", ".join(f"{k} Hz {v:+.2f}" for k, v in r["riaa_spots"].items()))
json.dump(res, open("out/study.json", "w"))
