# Moscode (New York Audio Labs) SuperIt phono preamp

A reverse-engineered model of the NYAL "SuperIt" hybrid phono preamplifier
(George Kaye, about 1985): a KiCad schematic that simulates, a scripted SPICE
model, and a study of what limits its linearity and how to improve it.

**Summary**

- Each stage is a JFET with a 12AX7 triode on top (a cascode) and a 100 kΩ
  load. One unbypassed source resistor per stage sets gain and linearity:
  **R27** in stage 1 and **R19** in stage 2. A bypassed resistor sets the
  bias: R2 and the trimmer R11.
- As built (R27 = 909 Ω), the model gives 58 dB gain at 1 kHz, 6 nV/√Hz input
  noise, and 0.31 % distortion at 5 mV input, nearly all second harmonic from
  stage 2.
- **R19 from 274 Ω to 1.5 kΩ**, with R11 re-trimmed, cuts distortion
  fifteen-fold (to 0.02 % at 5 mV) and gives 48 dB gain. Noise does not
  change.
- **R27 sets the noise.** For a low-output moving coil, 22 to 100 Ω gives 2.2
  to 2.6 nV/√Hz. A 2SK170/LSK170 at Q7 gives 1.4 nV/√Hz.
- **R7 from 22.1 kΩ to 24.3 kΩ** brings the RIAA error from ±0.5 dB to
  ±0.2 dB.

Nothing here has been checked against a measurement of the real unit.

The unit runs from a rectified 220 V winding: about 310 V DC on the reservoir
capacitor and about 250 V on the plate supplies. Unplug it and discharge C18
before touching the board.

## Contents

| Path | What it is |
|---|---|
| `sources/` | Two scans of the Rev D drawing (topology and designators only, no values), two board photos from the web, and photos of unit 1 (rev E board, 2-86) and unit 2 (earlier board, 38-85, partly stripped). |
| `readings/` | Enlarged crops of the parts whose markings were read. |
| `kicad/` | KiCad project `superit.kicad_pro`, SPICE models `superit.lib`, the schematic as `superit-schematic.pdf`. |
| `sim/circuit.py` | The parts list, the single source of every value. Each part is tagged K (known), P (read from a photo) or E (estimate). |
| `sim/` | Simulation scripts, charts (`plots/`) and results (`out/`). |

## The circuit

![Audio circuit, one channel](kicad/channel.png)

Full schematic with the power supply:
[kicad/superit-schematic.pdf](kicad/superit-schematic.pdf).

1. **Input.** J1, R1 (47.5 kΩ) to ground, and four switched loading
   resistors R20 to R23 for moving-coil cartridges.
2. **Stage 1.** Q7, a U310 JFET, with both halves of a 12AX7 (V1) in parallel
   as the cascode. The triode grids sit on the +12 V heater rail, which holds
   the JFET drain at about 13 V. Plate load R5 (100 kΩ) from B+1. In the
   source: R27 unbypassed, then R2 bypassed by C1.
3. **RIAA network**, passive: R6 (475 kΩ) in series, C4 coupling, then R7 in
   parallel with C5 (3300 pF), that pair in series with C6 (0.01 µF) to
   ground. R9 (681 kΩ), the gate leak of Q6, is part of the network.
4. **Stage 2.** Q6, another U310, with one half of the shared 12AX7 (V2) and
   R10 (100 kΩ) from B+2. In the source: R19 unbypassed, then the BIAS
   trimmer R11 (5 kΩ) bypassed by C8.
5. **Output.** Q5, a BSS101 MOSFET source follower loaded by R12 (75 kΩ), then
   C7, the balance pot R13 and volume pot R14 (100 kΩ each), and R25 (475 Ω).

The gain of each stage is close to `R_load / (R_unbypassed + 1/gm)`, with 1/gm
about 235 Ω for a U310 at 1 mA. That is 39 dB in stage 1; the RIAA network
loses 26 dB at 1 kHz; stage 2 gives 45.5 dB. Stage 2 sees the larger signal
and has the lighter degeneration, so it produces most of the distortion.

**Power supply.** 220 VAC, bridge, reservoir C18. Two zeners (D5, D6) and a
Darlington (Q1, Q2) make a pre-regulated rail. An LF353 (IC2) drives two
MOSFET followers (Q3, Q4) that copy a filtered reference (R17/R16, C14) to
B+1 and B+2. Heaters run from a 12 V regulator. The op-amp is in the supply
only, not in the signal path.

## Component values

The drawing has no values. These were read from the boards; the model uses
the unit 1 values. `sim/circuit.py` has the full list.

| Part | Unit 1 (rev E, 2-86) | Unit 2 (38-85) |
|---|---|---|
| Q7, Q6 | U310 | U310 |
| R27 | 909 Ω | not found |
| R2 | 1.00 kΩ | not legible |
| R19 | 274 Ω | 274 Ω |
| R11 | 5 kΩ trimmer | trimmer |
| R5 | 100 kΩ | about 150 kΩ |
| R10 | 100 kΩ | 100 kΩ |
| R6 | 475 kΩ | 475 kΩ |
| R7 | 22.1 kΩ | looks the same |
| R9 | 681 kΩ | not legible |
| C5, C6 | 3300 pF 1 %, 0.01 µF 2 % | same |
| C4 | 0.1 µF 400 V film | 0.1 µF 400 V |
| C1, C8 | 100 µF 16 V | not legible |
| R3, R8 | wire links | about 22 Ω |
| R4 | 1.00 kΩ | 475 kΩ |
| Q5 | BSS101 | TO-92, not read |
| R12 | 75 kΩ | 75 kΩ |
| Q3, Q4 | VN0220N2 | TO-92 parts |
| IC2 | LF353N | socket empty |
| C18 | 390 µF 350 V (2024 replacement) | missing |
| C14 | film | 1.0 µF 250 V film |
| Rail film capacitors | 0.22 µF 250 V | not read |
| C21 | not fitted | fitted |
| Pots | 100 kΩ | 100 kΩ |

Estimated: C3, C7, the zeners, R20 to R23, and most of the power-supply
resistors. B+ (247 V in the model) follows from the zener estimate.

- **R27 looks like the factory gain option.** A board photographed on the
  web has 10 Ω there. With 10 Ω and R2 re-selected the model gives 71 dB,
  which matches the 72 dB upgrade that owners report.
- **The U310s must be low-pinch-off samples.** With 909 Ω + 1.00 kΩ in the
  source, only a part near the 2.5 V end of the data-sheet range runs at
  1 mA. The model uses that corner. A centre-of-range part would draw 1.7 mA
  and drop the plate to 78 V.
- **Unit 2 does not fully match the Rev D drawing** around V1 (R4, R5). Trace
  it before assuming the model applies.

## Results: unit 1 as built

Simulated: left channel, 10 Ω source unless stated, 100 kΩ and 200 pF load,
volume at maximum.

| Quantity | Value |
|---|---|
| Gain at 1 kHz | 58.2 dB (stage 1 with EQ 12.7 dB, stage 2 45.5 dB) |
| Output for 5 mV at 1 kHz | 4.1 V rms |
| Input noise at 1 kHz | 6.0 nV/√Hz |
| S/N, A-weighted, re 5 mV, moving-magnet source (1 kΩ + 500 mH) | 78.9 dB |
| S/N, A-weighted, re 0.5 mV, 10 Ω source | 62.9 dB |
| THD at 1 kHz | 0.031 % at 0.5 mV, 0.31 % at 5 mV, 1.25 % at 20 mV |
| Input level for 1 % THD | 16 mV |
| RIAA error re 1 kHz | +0.3 to +0.45 dB from 20 to 200 Hz, +0.5 dB from 10 to 20 kHz |
| Raw-supply ripple to output | −47 dB at 60 Hz, −62 dB at 120 Hz |
| Crosstalk L to R | −75 dB at 100 Hz, below −100 dB above 1 kHz |

DC operating point: B+ 247 V; stage-1 plate 137 V (1.09 mA); Q7 drain 12.9 V,
1.09 V across R2; stage-2 plate 147 V (100 V across R10 as trimmed); Q5
source 145 V.

- **Distortion** is second harmonic from stage 2, in proportion to level.
  Stage 2 has only 274 Ω of degeneration for a signal that stage 1 has
  already amplified.
- **Noise** is set by R27: 909 Ω in the input source lead is 3.9 nV/√Hz by
  itself. With a moving-magnet cartridge the cartridge's own noise dominates.
- **The volume pot costs treble** when turned down: its output resistance (up
  to 25 kΩ) works against the cable capacitance.

![Treble loss from the volume pot](sim/plots/volume_pot_treble_loss.png)

- **RIAA.** R7 × (C5 + C6) is 294 µs against the standard 318 µs, which
  leaves the response 0.3 to 0.5 dB high on both sides of 1 kHz.

![RIAA error](sim/plots/riaa_error.png)

## Results: changes compared

| | Change from unit 1 as built | Gain, 1 kHz | Noise, 1 kHz | S/N(A) re 0.5 mV | THD at 0.5 mV | THD at 5 mV |
|---|---|---|---|---|---|---|
| A | none | 58.2 dB | 6.0 nV/√Hz | 62.9 dB | 0.031 % | 0.31 % |
| B | R27 10 Ω, R2 1.9 kΩ, C1 470 µF | 71.5 dB | 2.1 | 72.1 dB | 0.13 % | 1.3 % |
| C | R19 1.5 kΩ, R11 re-trimmed | 47.8 dB | 6.1 | 62.4 dB | 0.002 % | 0.020 % |
| D | B and C together | 61.1 dB | 2.1 | 72.0 dB | 0.016 % | 0.16 % |
| E | D with 2SK170 at Q7, R27 22 Ω, R2 about 310 Ω, C1 1000 µF | 70.1 dB | 1.36 | 76.1 dB | 0.033 % | 0.33 % |
| F | C8 removed, nothing else | 45.2 dB | 6.1 | 62.2 dB | 0.001 % | 0.010 % |

S/N re 5 mV with a moving-magnet source is 78.6 to 80.9 dB for all six.

![THD against level](sim/plots/thd_vs_level.png)

**R19** (stage 1 as built; R11 re-trimmed to keep 1 mA):

| R19 | R11 after trim | Gain | THD at 5 mV | Output at 5 mV |
|---|---|---|---|---|
| 274 Ω | 1.84 kΩ | 58.2 dB | 0.31 % | 4.1 V |
| 560 Ω | 1.55 kΩ | 54.4 dB | 0.12 % | 2.6 V |
| 1.0 kΩ | 1.11 kΩ | 50.7 dB | 0.047 % | 1.7 V |
| 1.5 kΩ | 0.61 kΩ | 47.8 dB | 0.020 % | 1.2 V |
| 2.0 kΩ | 0.11 kΩ | 45.6 dB | 0.011 % | 0.95 V |

**R27** (R2 re-selected so that R27 + R2 stays near 1.91 kΩ; C1 470 µF below
909 Ω; R19 = 1.5 kΩ):

| R27 | R2 | Gain | Noise, 1 kHz | S/N(A) re 0.5 mV | THD at 0.5 mV |
|---|---|---|---|---|---|
| 909 Ω | 1.00 kΩ | 47.8 dB | 6.1 nV/√Hz | 62.4 dB | 0.002 % |
| 470 Ω | 1.44 kΩ | 51.9 dB | 4.3 | 65.6 dB | 0.003 % |
| 220 Ω | 1.69 kΩ | 55.7 dB | 3.2 | 68.3 dB | 0.005 % |
| 100 Ω | 1.81 kΩ | 58.4 dB | 2.6 | 70.1 dB | 0.008 % |
| 47 Ω | 1.86 kΩ | 59.8 dB | 2.3 | 71.1 dB | 0.012 % |
| 22 Ω | 1.89 kΩ | 60.6 dB | 2.2 | 71.7 dB | 0.014 % |
| 10 Ω | 1.90 kΩ | 61.1 dB | 2.1 | 72.0 dB | 0.016 % |

With R19 left at 274 Ω the gains are 10.4 dB higher and the distortion is
8 to 15 times higher.

![Input noise](sim/plots/input_noise.png)

## Power supply

Several supply parts are estimates, so read these as the behaviour of this
kind of regulator. Rail capacitors C10 and C12 are 22 µF with 1 Ω series
resistance (ESR), typical of a new 350 to 450 V electrolytic.

| Frequency | B+1 rail impedance | Raw ripple to B+ | B+1 as an equivalent input | B+2 as an equivalent input | Raw supply as an equivalent input |
|---|---|---|---|---|---|
| 20 Hz | 0.63 Ω | −70 dB | −39 dB | −78 dB | −109 dB |
| 60 Hz | 0.21 Ω | −82 dB | −39 dB | −75 dB | −121 dB |
| 120 Hz | 0.10 Ω | −93 dB | −39 dB | −71 dB | −132 dB |
| 1 kHz | 0.006 Ω | −141 dB | −39 dB | −58 dB | −180 dB |
| 10 kHz | 0.15 Ω | −163 dB | −39 dB | −45 dB | −202 dB |
| 20 kHz | 0.30 Ω | −162 dB | −39 dB | −39 dB | −198 dB |
| 100 kHz | 0.89 Ω | −163 dB | −39 dB | −25 dB | −185 dB |
| 1 MHz | 0.60 Ω | −171 dB | −39 dB | +10 dB | −155 dB |

"As an equivalent input": a disturbance on that rail has the same effect on
the output as an input signal that many dB smaller.

![Supply rejection](sim/plots/psu_rejection.png)

- **The stages reject very little.** A cascode with a resistor load lets its
  plate follow the supply. Noise on B+1 is reduced only by the stage-1 gain
  (39 dB as built, 52 dB with R27 = 10 Ω); noise on B+2 reaches the output at
  unity gain.
- **The regulator makes up for it.** 0.1 V rms of reservoir ripple at 120 Hz
  comes out as 25 nV referred to the input. The LF353's own noise is worth
  0.2 nV/√Hz at the input.
- **The weak region is below 100 Hz**, where only C14 filters the reference:
  rail impedance 0.6 Ω and crosstalk −55 dB at 20 Hz. C14 at 4.7 µF improves
  ripple rejection by 13 dB and crosstalk to −68 dB at 20 Hz. C17 at 100 µF
  adds 10 dB of ripple rejection at 60 Hz.
- **Above about 25 kHz** the loop has no gain and the rail impedance is the
  ESR of C10 and C12. The high-frequency rejection figures will not be met
  on a real board, where stray coupling sets the floor.

![Rail impedance against capacitor ESR](sim/plots/psu_rail_impedance.png)

- **The ESR of C10 and C12 damps the loop.** With 0.3 Ω or more there is no
  peak. With 0.1 Ω the rail peaks at 1 Ω near 22 kHz; with a film capacitor
  (0.02 Ω) at 4.4 Ω, ringing for about half a millisecond. It stays stable in
  every case tried, and the audible effect is small (crosstalk of about
  −80 dB at the peak), but very low-ESR parts gain nothing there.

## Recommendations

In order of value for effort.

1. **Measure first**: see [What to measure](#what-to-measure).

2. **R19 from 274 Ω to 1.5 kΩ**, both channels, and re-trim R11 for the same
   voltage across R10. Distortion falls fifteen-fold, gain is 48 dB, and the
   volume control runs nearer the top, where it loses no treble. Other rows
   of the R19 table give more gain. Removing C8 instead (variant F) needs no
   parts, but then the gain depends on each trimmer's setting.

3. **Trim R11 for about 80 V across R10 instead of 100 V**, or try a 12AT7
   in V2. At 1 mA the V2 triode sits at −0.73 V grid to cathode, close to
   grid current, which the standard tube model leaves out. With a
   representative grid-current law, variant C's distortion at 5 mV rises
   from 0.02 % to 0.24 %; at 0.8 mA it is 0.013 %. A 12AT7 sits at −2.2 V
   with the same gain.

4. **Choose R27 for the cartridge**, changing R2 the other way so that
   R27 + R2 stays the same. Below about 220 Ω, raise C1 to 470 µF.
   - Moving magnet, about 5 mV: leave R27 at 909 Ω.
   - High-output moving coil, about 2 mV: 220 to 470 Ω.
   - Low-output moving coil, 0.3 to 0.5 mV: 22 to 100 Ω, with R19 = 1.5 kΩ
     (variant D): 58 to 61 dB, 2.2 to 2.6 nV/√Hz.

5. **For the quietest moving-coil stage, a 2SK170 or LSK170 at Q7** (variant
   E): 1.4 nV/√Hz. It needs R27 22 to 47 Ω, R2 about 300 Ω (aim for 100 to
   110 V across R5) and C1 1000 µF. With the present R2 it would run at
   0.23 mA. The pinout differs from the U310.

6. **Volume pot and cable.** At −6 dB the 100 kΩ pot loses 1.5 dB at 10 kHz
   and 4.2 dB at 20 kHz into 500 pF. Keep the cable short, or fit 25 kΩ
   pots: the loss at 20 kHz falls to 0.65 dB.

7. **R7 from 22.1 kΩ to 24.3 kΩ** brings the RIAA error within ±0.2 dB.
   220 µF at C1 and C8 as well brings it within ±0.1 dB.

8. **Leave C21 unfitted.** With 220 pF there, channel separation falls to
   54 dB at 10 kHz.

9. **Supply capacitors.** Use ordinary electrolytics for C10 and C12, not
   film or polymer; with film, add 0.5 to 1 Ω in series. Raise C14 to 4.7 µF
   film and C17 to 47 or 100 µF.

Changing the op-amp is not worth doing: it only regulates the supply.

## What to measure

| Measure | Model | Meaning |
|---|---|---|
| DC volts across R2 (1.00 kΩ) | 1.09 V | Stage-1 current in mA. Above about 1.3 V, the U310 is a higher-pinch-off part: raise R2 until it reads 1.0 to 1.1 V. |
| DC volts across R19 (274 Ω) | 0.274 V | Stage-2 current: 0.274 V per mA. |
| B+ (top of R5 or R10 to ground) | 247 V | High voltage. An error of 20 to 30 V changes the results very little. |

Also useful: R11 as set, the markings on C3 and C7, and the zener type
numbers. Put any of these into `sim/circuit.py` and re-run the scripts.

## Running the model

**KiCad**: open `kicad/superit.kicad_pro` and simulate from Inspect >
Simulator. Every symbol has hidden `Status` and `Note` fields with the K/P/E
tag and the reading. The schematic is generated from `sim/circuit.py`; edit
that file and regenerate:

```sh
cd kicad
python gen_kicad.py      # rebuild the project from sim/circuit.py
python verify_kicad.py   # ERC, then compare KiCad's netlist and results with the scripted model
python export.py         # superit-schematic.pdf and channel.png (needs kicad-cli and ImageMagick)
```

**Scripts**: Python 3 with numpy and matplotlib. They call the ngspice
library inside KiCad.app.

```sh
cd sim
python op_point.py       # DC voltages and currents
python variants.py       # bias point of each variant
python study.py          # gain, RIAA, noise, distortion for variants A to F
python extras.py         # pot and cable, crosstalk, sensitivities, R27 and R19 tables
python psu.py            # supply: rail impedance, ripple rejection, capacitor ESR
python plots.py          # charts -> plots/
```

`study.py` and `extras.py` each take several minutes.

## Limits

- Absolute figures are indicative. Differences between variants are more
  trustworthy, because the unknowns are common to all.
- The JFET model is a square-law device at one corner of the U310 data
  sheet.
- The triode model has no grid current (except in recommendation 3) and no
  microphony.
- Noise figures exclude hum pickup, heater-to-cathode leakage and tube
  flicker noise.
- KiCad's netlist matches the scripted model, but running from KiCad's own
  simulator window has not been tried.

## Sources

- <https://hifihaven.org/index.php?threads/new-ps-for-a-new-york-audio-labs-superit-phono-preamp.5806/>
- <https://www.diyaudio.com/community/threads/anyone-mod-a-nyal-moscode-superit.62147/>
- <https://www.diyaudio.com/community/threads/moscode-super-it-schematics-power-supply.291484/>
- <https://www.stereophile.com/content/new-york-audio-labs-superit-phono-preamplifier>
- <https://www.stereophile.com/content/new-york-audio-labs-superit-phono-preamplifier-anthony-h-cordesman-followup>
- <https://forum.audiogon.com/discussions/moscode-super-it-or-audio-research-ph3>
- <https://www.audiocircle.com/index.php?topic=19077.0>
