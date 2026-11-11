"""Charts for the study.  Reads out/study.json; writes plots/*.png."""
import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from measure import ac, at
from variants import build, clean

SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
# colour follows the variant, in every chart
COL = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a", "D": "#eda100", "E": "#e87ba4"}
SHORT = {"A": "A  as built (R27 909 Ω, R19 274 Ω)", "B": "B  high-gain build (R27 10 Ω)",
         "C": "C  A with R19 = 1.5 kΩ", "D": "D  B with R19 = 1.5 kΩ",
         "E": "E  D with 2SK170 input JFET"}
plt.rcParams.update({"font.family": "Helvetica Neue", "font.size": 10.5, "axes.edgecolor": AXIS,
                     "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
                     "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF})
res = json.load(open("out/study.json"))
R = {k[0]: v for k, v in res.items()}


def frame(ax, title, sub):
    ax.grid(True, which="major", color=GRID, lw=0.7); ax.set_axisbelow(True)
    ax.set_title(title, loc="left", color=INK, fontsize=13, fontweight="bold", pad=24)
    ax.text(0, 1.035, sub, transform=ax.transAxes, color=INK2, fontsize=10)


# ---- 1. distortion against input level
fig, ax = plt.subplots(figsize=(9.6, 5.8), dpi=150)
for k in "ABCDE":
    lv = np.array(R[k]["levels"])*1e3; th = np.array(R[k]["thd"])*100
    ok = np.isfinite(th) & (th < 12)
    ax.plot(lv[ok], th[ok], color=COL[k], lw=2, marker="o", ms=4.5, label=SHORT[k])
    j = np.where(ok)[0][-1]
    ax.annotate(k, (lv[j], th[j]), xytext=(7, 0), textcoords="offset points", color=INK, fontsize=11, fontweight="bold", va="center")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(0.08, 90); ax.set_ylim(2e-4, 15)
for x, lab in ((0.5, "typical MC\n0.5 mV"), (5, "typical MM\n5 mV")):
    ax.axvline(x, color=AXIS, lw=1, ls=(0, (4, 3)))
    ax.text(x*1.07, 5.2, lab, color=MUTED, fontsize=9, va="center")
ax.set_xticks([0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50]); ax.set_xticklabels(["0.1", "0.2", "0.5", "1", "2", "5", "10", "20", "50"])
ax.set_yticks([0.001, 0.01, 0.1, 1, 10]); ax.set_yticklabels(["0.001", "0.01", "0.1", "1", "10"])
ax.set_xlabel("input level at 1 kHz, mV rms"); ax.set_ylabel("total harmonic distortion at the output, %")
frame(ax, "More unbypassed source resistance in stage 2 cuts distortion about tenfold",
      "Simulated THD at the output (almost all 2nd harmonic). Lower is better; curves end where a stage clips.")
ax.legend(frameon=False, loc="lower right", labelcolor=INK2, fontsize=9.5)
fig.tight_layout(); fig.savefig("plots/thd_vs_level.png"); plt.close(fig)

# ---- 2. treble loss from the output pot + cable
A = clean([v for k, v in build().items() if k.startswith("A")][0])
fig, axs = plt.subplots(1, 3, figsize=(11.5, 4.3), dpi=150, sharey=True)
POS = [(0, "#0d366b", "full"), (-20, "#256abf", "-20 dB"), (-12, "#5598e7", "-12 dB"), (-6, "#9ec5f4", "-6 dB")]
for ax, cl in zip(axs, ("200p", "500p", "1n")):
    ref = None; ends = []
    for att, col, lab in POS:
        k = 10**(att/20)
        a = ac("pot", params=dict(A, r14a=f"{100e3*(1-k)+1e-3:.6g}", r14b=f"{100e3*k:.6g}", cload=cl))
        y = a["out"] - at(a, "out", 1000)
        if ref is None: ref = y.copy()          # full volume = the stage's own response
        m = (a["f"] >= 1000) & (a["f"] <= 20000)
        ax.plot(a["f"][m]/1e3, (y-ref)[m], color=col, lw=2)
        ends.append(((y-ref)[m][-1], lab))
    ypos = None                                  # keep end labels at least 0.6 dB apart
    for yv, lab in sorted(ends, reverse=True):
        ypos = yv if ypos is None else min(yv, ypos - 0.6)
        ax.annotate(lab, (20, ypos), xytext=(5, 0), textcoords="offset points", color=INK2, fontsize=9, va="center")
    ax.set_xscale("log"); ax.set_xlim(1, 20); ax.set_ylim(-9.5, 0.6)
    ax.set_xticks([1, 2, 5, 10, 20]); ax.set_xticklabels(["1k", "2k", "5k", "10k", "20k"])
    ax.grid(True, color=GRID, lw=0.7); ax.set_axisbelow(True)
    ax.set_title({"200p": "200 pF  (short cable)", "500p": "500 pF  (2-3 m cable)", "1n": "1 nF  (long cable)"}[cl], loc="left", color=INK, fontsize=10.5)
    ax.set_xlabel("frequency, Hz"); ax.margins(x=0)
    ax.spines["right"].set_visible(False)
axs[0].set_ylabel("level relative to full volume, dB")
fig.suptitle("The 100 k volume pot rolls off the treble at mid settings", x=0.012, ha="left", color=INK, fontsize=13, fontweight="bold")
fig.text(0.012, 0.9, "Response change against volume-control setting, for three cable + amplifier-input capacitances. Shade = pot setting.", color=INK2, fontsize=10)
fig.tight_layout(rect=(0, 0, 0.985, 0.9)); fig.savefig("plots/volume_pot_treble_loss.png"); plt.close(fig)

# ---- 3. input-referred noise
fig, ax = plt.subplots(figsize=(8.6, 5.0), dpi=150)
for k in "ABE":
    f = np.array(R[k]["nf"]); n = np.array(R[k]["inn"])*1e9
    m = (f >= 20) & (f <= 20000)
    ax.plot(f[m], n[m], color=COL[k], lw=2, label=SHORT[k])
    ax.annotate(k, (20000, n[m][-1]), xytext=(6, 0), textcoords="offset points", color=INK, fontsize=11, fontweight="bold", va="center")
ax.set_xscale("log"); ax.set_xlim(20, 20000); ax.set_ylim(0, 12)
ax.set_xticks([20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]); ax.set_xticklabels(["20", "50", "100", "200", "500", "1k", "2k", "5k", "10k", "20k"])
ax.set_xlabel("frequency, Hz"); ax.set_ylabel("input-referred noise, nV/√Hz")
frame(ax, "R27 sets the noise floor; the JFET type matters only once R27 is small",
      "Simulated input-referred noise, 10 Ω source (a low-output moving-coil cartridge).")
ax.legend(frameon=False, loc="upper right", labelcolor=INK2, fontsize=9.5)
fig.tight_layout(); fig.savefig("plots/input_noise.png"); plt.close(fig)
# ---- 4. RIAA accuracy with the values as read, and with the two uncertain readings changed
fig, ax = plt.subplots(figsize=(8.6, 4.6), dpi=150)
f = np.array(R["A"]["f"]); m = (f >= 20) & (f <= 20000)
ax.axhline(0, color=AXIS, lw=1)
ax.plot(f[m], np.array(R["A"]["err"])[m], color=COL["A"], lw=2)
ax.annotate("as built", (f[m][-1], np.array(R["A"]["err"])[m][-1]), xytext=(-6, 9), textcoords="offset points", color=INK, fontsize=9.5, ha="right")
from measure import riaa_err
a2 = ac("riaa_alt", params=dict(A, r7="24.3k", c1="220u", c8="220u")); e2 = riaa_err(a2)
ax.plot(a2["f"][m], e2[m], color=MUTED, lw=2, ls=(0, (5, 2)))
ax.annotate("R7 24.3 kΩ; C1, C8 220 µF", (a2["f"][m][-1], e2[m][-1]), xytext=(-6, -13), textcoords="offset points", color=INK2, fontsize=9.5, ha="right")
ax.set_xscale("log"); ax.set_xlim(20, 20000); ax.set_ylim(-1.5, 1.5)
ax.set_xticks([20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]); ax.set_xticklabels(["20", "50", "100", "200", "500", "1k", "2k", "5k", "10k", "20k"])
ax.set_xlabel("frequency, Hz"); ax.set_ylabel("deviation from RIAA, dB (0 at 1 kHz)")
frame(ax, "One resistor and two capacitors bring the RIAA error within ±0.1 dB",
      "Simulated equalisation error of the as-built circuit, 10 Ω source, volume at maximum.")
fig.tight_layout(); fig.savefig("plots/riaa_error.png"); plt.close(fig)
# ---- 5, 6. power supply (needs out/psu.json from psu.py)
import os
if os.path.exists("out/psu.json"):
    P = json.load(open("out/psu.json"))
    fig, ax = plt.subplots(figsize=(8.8, 5.0), dpi=150)
    SEQ = [("10", "#9ec5f4", "10 Ω  (tired electrolytic)"), ("1", "#5598e7", "1 Ω  (new electrolytic)"),
           ("0.1", "#256abf", "0.1 Ω"), ("0.02", "#0d366b", "0.02 Ω  (film)")]
    for esr, col, lab in SEQ:
        d = P["esr"][f"22u,{esr}"]; f = np.array(d["f"]); z = 10**(np.array(d["z1"])/20)
        ax.plot(f, z, color=col, lw=2, label=lab)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(10, 1e7); ax.set_ylim(1e-3, 20)
    ax.axvspan(20, 20000, color=GRID, alpha=0.35, lw=0); ax.text(630, 12, "audio band", color=MUTED, fontsize=9, ha="center")
    ax.set_xticks([10, 100, 1e3, 1e4, 1e5, 1e6, 1e7]); ax.set_xticklabels(["10", "100", "1k", "10k", "100k", "1M", "10M"])
    ax.set_yticks([1e-3, 1e-2, 1e-1, 1, 10]); ax.set_yticklabels(["0.001", "0.01", "0.1", "1", "10"])
    ax.set_xlabel("frequency, Hz"); ax.set_ylabel("output impedance of the B+1 rail, Ω")
    frame(ax, "Very low-ESR rail capacitors make the regulator peak near 20 kHz",
          "Simulated impedance of the stage-1 supply rail for four series resistances of C10 (22 µF).")
    ax.legend(frameon=False, loc="lower right", labelcolor=INK2, fontsize=9.5, title="ESR of C10", title_fontsize=9.5)
    fig.tight_layout(); fig.savefig("plots/psu_rail_impedance.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.8, 5.2), dpi=150)
    q = P["sens"]["A"]; f = np.array(q["f"]); sig = np.array(q["sig"])
    LINES = [("g1", "#2a78d6", "B+1 rail (stage 1)"), ("g2", "#eb6834", "B+2 rail (stage 2, follower)"),
             ("gh", "#1baf7a", "12 V heater rail"), ("raw_out", "#eda100", "raw supply, through the regulator")]
    for key, col, lab in LINES:
        y = np.array(q[key]) - sig; m = (f >= 20) & (f <= 1e6)
        ax.plot(f[m], y[m], color=col, lw=2, label=lab)
    ax.set_xscale("log"); ax.set_xlim(20, 1e6); ax.set_ylim(-220, 20)
    ax.axvspan(20, 20000, color=GRID, alpha=0.35, lw=0); ax.text(630, 8, "audio band", color=MUTED, fontsize=9, ha="center")
    ax.set_xticks([20, 100, 1e3, 1e4, 1e5, 1e6]); ax.set_xticklabels(["20", "100", "1k", "10k", "100k", "1M"])
    ax.set_xlabel("frequency, Hz"); ax.set_ylabel("disturbance on the rail as an equivalent input signal, dB")
    frame(ax, "The stages reject little supply noise; the regulator does the work",
          "Simulated, unit 1 as built. 0 dB = one volt on the rail acts like one volt at the cartridge input. Lower is better.")
    ax.legend(frameon=False, loc="center right", bbox_to_anchor=(0.89, 0.367), labelcolor=INK2, fontsize=9.5)
    fig.tight_layout(); fig.savefig("plots/psu_rejection.png"); plt.close(fig)
print("plots written")
