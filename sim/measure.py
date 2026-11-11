"""Measurement routines built on simlib.run: THD, gain/RIAA, noise, op point."""
import numpy as np
from simlib import run, table
from riaa import riaa_db

NODES = "v(outl) v(xchl.p1) v(xchl.g6) v(xchl.p2) v(outr)"


def harmonics(t, y, f0, n=8):
    """Least-squares fit of DC + drift + n harmonics; returns amplitudes (peak)."""
    cols = [np.ones_like(t), t - t.mean()]
    for k in range(1, n + 1):
        cols += [np.sin(2*np.pi*k*f0*t), np.cos(2*np.pi*k*f0*t)]
    c, *_ = np.linalg.lstsq(np.stack(cols, 1), y, rcond=None)
    return np.hypot(c[2::2], c[3::2])


def thd(name, vin_rms, f0=1000.0, params=None, cycles=20, settle=0.04, extra=""):
    """Transient at one level. Returns dict per node: fundamental (rms), h2, h3, thd (ratios)."""
    per = 1.0/f0
    tstep = per/400
    tstart = np.ceil(settle/per)*per
    tstop = tstart + cycles*per
    ctl = f"""
tran {tstep:.6e} {tstop:.6e} {tstart:.6e} {tstep:.6e}
linearize {NODES}
wrdata {name}.txt {NODES}
"""
    import os
    from simlib import OUT
    path = os.path.join(OUT, name + ".txt")
    if os.path.exists(path):
        os.remove(path)
    run(name, params=params, control=ctl, extra=extra,
        source_l=f"DC 0 AC 1 SIN(0 {vin_rms*np.sqrt(2):.6e} {f0})")
    if not os.path.exists(path):            # simulator gave up (gross overload)
        nan = dict(v=np.nan, h2=np.nan, h3=np.nan, thd=np.nan)
        return {k: dict(nan) for k in ("out", "p1", "g6", "p2", "outr")}
    d = table(name + ".txt")
    t = d[:, 0]
    res = {}
    for i, node in enumerate(("out", "p1", "g6", "p2", "outr")):
        a = harmonics(t, d[:, 2*i+1], f0)
        res[node] = dict(v=a[0]/np.sqrt(2), h2=a[1]/a[0], h3=a[2]/a[0],
                         thd=np.sqrt((a[1:]**2).sum())/a[0])
    return res


def ac(name, params=None, extra="", pre=""):
    ctl = f"""
{pre}
ac dec 40 2 1Meg
wrdata {name}.txt vdb(outl) vdb(xchl.g6) vdb(xchl.p1) vdb(outr) vp(outl)
"""
    run(name, params=params, control=ctl, extra=extra)
    d = table(name + ".txt")
    return dict(f=d[:, 0], out=d[:, 1], g6=d[:, 3], p1=d[:, 5], outr=d[:, 7], ph=d[:, 9])


def at(a, key, fx):
    return float(np.interp(np.log10(fx), np.log10(a["f"]), a[key]))


def riaa_err(a):
    return a["out"] - at(a, "out", 1000) - riaa_db(a["f"])


def a_weight_db(f):
    f = np.asarray(f, float)
    ra = (12194**2*f**4)/((f**2+20.6**2)*np.sqrt((f**2+107.7**2)*(f**2+737.9**2))*(f**2+12194**2))
    return 20*np.log10(ra) + 2.0


def noise(name, params=None, extra=""):
    """Output and input-referred noise.  Returns f, onoise density, gain(f), and helpers."""
    ctl = f"""
noise v(outl) vinl dec 30 10 100k
setplot noise1
wrdata {name}.txt onoise_spectrum inoise_spectrum
"""
    run(name, params=params, control=ctl, extra=extra)
    d = table(name + ".txt")
    f, on, inn = d[:, 0], d[:, 1], d[:, 3]
    return dict(f=f, on=on, inn=inn)


def integ(f, dens, lo=20, hi=20000, weight=None):
    """rms of a noise density (V/rtHz) over [lo,hi] with optional weighting in dB."""
    m = (f >= lo) & (f <= hi)
    p = dens[m]**2
    if weight is not None:
        p = p*10**(weight[m]/10)
    return float(np.sqrt(np.trapezoid(p, f[m])))


def snr_a(n, a, vin_ref):
    """A-weighted S/N (dB) of the output re the output produced by vin_ref at 1 kHz."""
    vout_ref = vin_ref*10**(at(a, "out", 1000)/20)
    vn = integ(n["f"], n["on"], weight=a_weight_db(n["f"]))
    return 20*np.log10(vout_ref/vn)
