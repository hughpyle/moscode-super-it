# Moscode (New York Audio Labs) SuperIt phono preamp

A reverse-engineered model of the NYAL "SuperIt" hybrid phono preamplifier
(George Kaye, about 1985): a KiCad schematic that simulates, a scripted SPICE
model, and a study of what limits its linearity and how to improve it.

**Short version**

- Each stage is a JFET with a 12AX7 triode on top (a cascode) and a 100 kΩ load.
  One unbypassed source resistor per stage sets that stage's gain and
  linearity: **R27** in stage 1 and **R19** in stage 2. A second, bypassed
  resistor per stage sets the bias: R2 and the trimmer R11. Every change
  recommended here is a change to one of those resistors.
- Unit 1 (the complete one) is a low-gain build: R27 is 909 Ω, not the 10 Ω seen
  on another board. As built, the model gives 58 dB gain at 1 kHz, 6 nV/√Hz
  input noise, and 0.31 % distortion at 5 mV input, nearly all of it second
  harmonic from stage 2.
- Changing **R19 from 274 Ω to 1.5 kΩ** and re-trimming R11 cuts distortion
  about fifteen-fold (0.31 % to 0.02 % at 5 mV) and brings the gain down to
  48 dB, which suits a moving-magnet cartridge. Noise does not change.
- For a low-output moving-coil cartridge, **R27 is the noise knob**: 22 to 100 Ω
  (with R2 raised by the same amount) takes the noise from 6 to about
  2.3 nV/√Hz. A 2SK170/LSK170 input JFET takes it to 1.4 nV/√Hz, but only with
  R2 re-selected.
- The numbers come from a model in which several parts are still estimates.
  A few measurements on the real unit would pin it down; see
  [What to measure](#what-to-measure).

The unit runs from a rectified 220 V winding: about 310 V DC on the reservoir
capacitor and about 250 V on the plate supplies. Unplug it and discharge C18
before touching the board.

## Contents

| Path | What it is |
|---|---|
| `sources/schematic-scan-1.jpg`, `schematic-scan-2.webp` | Two scans of the same Rev D drawing. Topology and designators only: the drawing carries no values and no transistor types. |
| `sources/moscode-1.webp` | Board photo found on line: stock unit, board rev E. |
| `sources/moscode-2.jpg` | Board photo found on line: modified unit. |
| `sources/IMG_4981` to `IMG_4985` | Unit 1: complete rev E board dated 2-86. |
| `sources/IMG_4986` to `IMG_4988` | Unit 2: earlier board (593-008004, dated 38-85), partly stripped. |
| `readings/` | Enlarged crops of the parts whose markings and colour bands were read, with the reading written on each. |
| `kicad/` | KiCad project `superit.kicad_pro`. Root sheet: power supply and test sources. `channel.kicad_sch`: one audio channel, used twice. `superit.lib`: SPICE models. |
| `sim/circuit.py` | The parts list, the single source of every value. Each part is tagged K (known), P (read from a photo) or E (estimate), with a note. |
| `sim/*.py` | Simulation scripts; see [Running the model](#running-the-model). |
| `sim/plots/` | The charts below. |
| `sim/out/` | Results: `study.json`, `extras.json`, `study.log`, `extras.log`. The scripts also write their decks and raw tables here; those are not kept in the repository. |

## The circuit

Signal path, one channel (designators from the Rev D drawing):

1. **Input.** J1, with R1 (47.5 kΩ) to ground and four switched loading
   resistors R20 to R23 on DIP switch S1 for moving-coil cartridges. R8 is in
   series with the gate of Q7.
2. **Stage 1.** Q7, a U310 JFET, with both halves of a 12AX7 (V1) in parallel
   on top of it as a cascode. The triode grids sit on the +12 V heater rail
   through R4 and R3, decoupled by C3, which holds the JFET drain at about 13 V.
   The plate load is R5 (100 kΩ) from B+1. In the source: R27 unbypassed, then
   R2 bypassed by C1.
3. **RIAA network**, passive, between the stages: R6 (475 kΩ) in series, C4
   coupling, then R7 in parallel with C5 (3300 pF), that pair in series with C6
   (0.01 µF) to ground. R9 (560 kΩ) is the gate leak of Q6 and is part of the
   network.
4. **Stage 2.** Q6, another U310, with one half of the shared 12AX7 (V2) as the
   cascode and R10 (100 kΩ) from B+2. In the source: R19 unbypassed, then the
   BIAS trimmer R11 bypassed by C8.
5. **Output.** Q5, a BSS101 MOSFET source follower loaded by R12 (75 kΩ), then
   C7, the balance pot R13 (100 kΩ), the volume pot R14 (100 kΩ) and R25
   (475 Ω) to J2.

The gain of each stage is close to `R_load / (R_unbypassed + 1/gm)`, with 1/gm
about 235 Ω for a U310 at 1 mA. As built that is 100k / (909 + 235), or 39 dB,
in stage 1; the RIAA network loses 26 dB at 1 kHz; and stage 2 gives 45.5 dB.
Stage 2 therefore sees the larger signal and has the lighter degeneration,
which is why it produces most of the distortion.

**Power supply.** 220 VAC, bridge D1 to D4, reservoir C18. R18 and two zeners
(D5, D6) feed a Darlington (Q1, Q2) that makes a pre-regulated rail. The
LF353 (IC2) floats on that rail from zener D9 and R15, and drives two MOSFET
followers (Q3, Q4) that copy a filtered reference (R17/R16, C14) to B+1 and
B+2. Heaters: 14.5 VAC, bridge, C20, a 12 V regulator, three 12AX7 heaters in
parallel. The op-amp is in the supply only, not in the signal path.

## Where the values come from

The drawing has no values, so every value was read from photographs or
estimated. `sim/circuit.py` has the full list with a note on each part. The
readings that matter most:

| Part | Unit 1 (rev E, 2-86) | Unit 2 (38-85) | Web photos | In the model |
|---|---|---|---|---|
| Q7, Q6 | U310 metal can (Q7 marking clear) | U310 (Q6 marking clear) | unmarked cans | U310 |
| R27 | **909 Ω** (clear) | not found | 10 Ω | 909 Ω |
| R2 | 1.00 kΩ | not legible | 1.00 kΩ | 1.00 kΩ |
| R19 | 274 Ω | 274 Ω | 274 Ω | 274 Ω |
| R11 | trimmer, value not visible | same | same | set for 1 mA (about 1.8 kΩ) |
| R5 | 100 kΩ | looks like 150 kΩ 2 % | 100 kΩ | 100 kΩ |
| R10 | 100 kΩ | 100 kΩ | 100 kΩ | 100 kΩ |
| R6 | 475 kΩ | 475 kΩ | 475 kΩ (tentative) | 475 kΩ |
| R7 | not legible | looks like 22.0 kΩ, **not certain** | not legible | 22 kΩ |
| R9 | 560 kΩ (two bands hard to see) | not legible | not legible | 560 kΩ |
| C5, C6 | 3300 pF 1 %, 0.01 µF 2 % | same, markings clear | same | as marked |
| C4 | red film box, unmarked side up | 0.1 µF 400 V | red film box | 0.1 µF |
| R3, R8 | 0 Ω links | real resistors, about 22 Ω | 0 Ω links | links |
| R4 | 1.00 kΩ | 475 kΩ in that position | 1 kΩ | 1.00 kΩ |
| Q5 | BSS101 | TO-92, not read | TO-92 | BSS101-class model |
| R12 | 75 kΩ power resistor | 75 kΩ | not legible | 75 kΩ |
| Q3, Q4 | VN0220N2 (TO-39) | TO-92 parts | TO-92 | generic 200 V MOSFET |
| IC2 | LF353N | **socket empty** | LF353N | LF353 model |
| C18 | 390 µF 350 V, dated 2024 (a replacement) | **missing** | original can | 390 µF |
| C14 | red film box | WIMA 1.0 µF 250 V | red film box | 1 µF |
| C21 | not fitted | a small axial part is fitted | not fitted | open |
| Pots | 100 kΩ MN, 100 kΩ dual | same | same | 100 kΩ |

Still estimates: C1, C8, C3 and C7 (values not legible), the zeners D5, D6, D9
and D10, the loading resistors R20 to R23, and most of the power-supply
resistors. B+ is therefore an estimate too: 247 V in the model. It cannot be
much higher, because C14 sits at B+ and is rated 250 V.

Three points about these readings:

- **R27 explains the different boards.** With R27 = 909 Ω the model gives 58 dB;
  with 10 Ω and R2 re-selected it gives 71 dB. Owners report that the factory
  offered a 72 dB gain upgrade, and reviewers found the unit quiet with
  higher-output cartridges and noisy with low-output moving coils. All of that
  is consistent with R27 being the factory's gain option. This is my inference,
  not a documented fact.
- **The U310s must be low-pinch-off samples.** The data sheet allows a pinch-off
  of 2.5 to 6 V. With 909 Ω + 1.00 kΩ in the source, only a part near 2.5 V runs
  at about 1 mA, which is what owners report (100 V across R5). The model uses
  that corner (2.6 V, 24 mA Idss). A centre-of-range part would draw 1.7 mA,
  drop the plate to 78 V and push the triode to the edge of grid current, so
  this is worth checking on the unit.
- **Unit 2 is an earlier board and does not fully match the Rev D drawing.**
  R4 = 475 kΩ and R5 = 150 kΩ suggest a different arrangement around V1. Trace it
  before assuming the model applies. To run again it needs at least an LF353
  and a reservoir capacitor.

## Results: unit 1 as built

All figures are simulated: left channel, 10 Ω source unless stated, 100 kΩ and
200 pF load, volume at maximum.

| Quantity | Value |
|---|---|
| Gain at 1 kHz | 58.2 dB (stage 1 with EQ 12.6 dB, stage 2 45.5 dB) |
| Output for 5 mV at 1 kHz | 4.0 V rms |
| Input noise at 1 kHz | 6.0 nV/√Hz |
| S/N, A-weighted, re 5 mV, moving-magnet source (1 kΩ + 500 mH) | 78.9 dB |
| S/N, A-weighted, re 0.5 mV, 10 Ω source | 62.8 dB |
| THD at 1 kHz | 0.031 % at 0.5 mV, 0.31 % at 5 mV, 1.2 % at 20 mV |
| Input level for 1 % THD | 16 mV |
| RIAA error re 1 kHz | +0.3 dB at 100 to 200 Hz, +0.6 dB at 10 to 20 kHz |
| Raw-supply ripple to output | −47 dB at 60 Hz, −62 dB at 120 Hz |
| Crosstalk L to R | −75 dB at 100 Hz, below −100 dB above 1 kHz |

DC operating point in the model: B+ 247 V; stage-1 plate 137 V (109 V across
R5, 1.09 mA); Q7 drain 12.9 V, source 2.09 V, 1.09 V across R2; stage-2 plate
147 V (100 V across R10 as trimmed); Q6 source 2.11 V; Q5 source 145 V at
1.9 mA.

What limits it:

- **Distortion is second harmonic from stage 2**, in proportion to level. A
  JFET at 1 mA is a square-law device, and stage 2 has only 274 Ω of
  degeneration for a signal that stage 1 has already amplified.
- **Noise is set by R27.** 909 Ω of unbypassed resistance in the input source
  lead is 3.9 nV/√Hz by itself, and the low stage-1 gain lets the RIAA network
  and stage 2 add as much again. For a moving-magnet cartridge this does not
  matter: the cartridge's own noise dominates (78.9 dB against 80.9 dB for the
  quietest variant).
- **The volume pot costs treble.** At full volume there is no loss. Turned
  down, the pot's output resistance (up to 25 kΩ) works against the cable and
  amplifier input capacitance. With 58 dB of gain the pot will usually be well
  down.

![Treble loss from the volume pot](sim/plots/volume_pot_treble_loss.png)

- **RIAA accuracy depends on R7**, the reading I am least sure of. If it is
  22.0 kΩ the error is the solid line; if it is 23.7 kΩ the treble error halves
  and the bass falls 0.5 dB at 20 Hz.

![RIAA error](sim/plots/riaa_error.png)

## Results: changes compared

| | Change from unit 1 as built | Gain, 1 kHz | Noise, 1 kHz | S/N(A) re 0.5 mV | THD at 0.5 mV | THD at 5 mV |
|---|---|---|---|---|---|---|
| A | none | 58.2 dB | 6.0 nV/√Hz | 62.8 dB | 0.031 % | 0.31 % |
| B | R27 10 Ω, R2 1.9 kΩ (the high-gain build) | 71.4 dB | 2.1 | 72.1 dB | 0.13 % | 1.3 % |
| C | R19 1.5 kΩ, R11 re-trimmed | 47.7 dB | 6.1 | 62.4 dB | 0.002 % | 0.020 % |
| D | B and C together | 61.0 dB | 2.15 | 71.9 dB | 0.016 % | 0.16 % |
| E | D with 2SK170 at Q7, R27 22 Ω, R2 about 310 Ω, C1 1000 µF | 70.0 dB | 1.36 | 76.1 dB | 0.033 % | 0.33 % |
| F | C8 removed, nothing else | 45.1 dB | 6.2 | 62.2 dB | 0.001 % | 0.010 % |

S/N re 5 mV with a moving-magnet source is 78.6 to 80.9 dB for all six.

![THD against level](sim/plots/thd_vs_level.png)

**R19, the stage-2 knob** (stage 1 as built; R11 re-trimmed to keep 1 mA):

| R19 | R11 after trim | Gain | THD at 5 mV | Output at 5 mV |
|---|---|---|---|---|
| 274 Ω | 1.84 kΩ | 58.2 dB | 0.31 % | 4.0 V |
| 560 Ω | 1.55 kΩ | 54.4 dB | 0.12 % | 2.6 V |
| 1.0 kΩ | 1.11 kΩ | 50.6 dB | 0.046 % | 1.7 V |
| 1.5 kΩ | 0.61 kΩ | 47.7 dB | 0.020 % | 1.2 V |
| 2.0 kΩ | 0.11 kΩ | 45.5 dB | 0.011 % | 0.9 V |

**R27, the stage-1 knob** (U310 at Q7; R2 re-selected so that R27 + R2 stays
near 1.91 kΩ; stage 2 with R19 = 1.5 kΩ):

| R27 | R2 | Gain | Noise, 1 kHz | S/N(A) re 0.5 mV | THD at 0.5 mV |
|---|---|---|---|---|---|
| 909 Ω | 1.00 kΩ | 47.7 dB | 6.1 nV/√Hz | 62.4 dB | 0.002 % |
| 470 Ω | 1.44 kΩ | 51.9 dB | 4.3 | 65.6 dB | 0.003 % |
| 220 Ω | 1.69 kΩ | 55.7 dB | 3.2 | 68.3 dB | 0.005 % |
| 100 Ω | 1.81 kΩ | 58.3 dB | 2.6 | 70.1 dB | 0.008 % |
| 47 Ω | 1.86 kΩ | 59.8 dB | 2.35 | 71.1 dB | 0.012 % |
| 22 Ω | 1.89 kΩ | 60.6 dB | 2.2 | 71.6 dB | 0.014 % |
| 10 Ω | 1.90 kΩ | 61.0 dB | 2.15 | 71.9 dB | 0.016 % |

With R19 left at 274 Ω the gains are 10.5 dB higher and the distortion is
8 to 15 times higher.

![Input noise](sim/plots/input_noise.png)

## Recommendations

In order of value for effort. Items 2 to 4 need two resistors per channel and
a meter.

1. **Measure first.** The checks in [What to measure](#what-to-measure) tell
   you whether the model's operating point is right for your unit.

2. **Stage 2: change R19 from 274 Ω to 1.5 kΩ**, 1 % metal film, both
   channels, and re-trim R11 for the same voltage across R10 as before. Leave
   C8 in place. Result: distortion down about fifteen-fold, gain 48 dB, and
   1.2 V out for 5 mV in, so the volume control runs nearer the top, where it
   loses no treble. Pick another row of the R19 table if you want more gain.
   Removing C8 instead (variant F) gives a similar result with no new parts,
   but then the gain depends on where each trimmer ends up, which differs
   between channels when the JFETs differ.

3. **Stage 2 bias: trim R11 for about 80 V across R10 instead of 100 V**, or
   try a 12AT7 in the V2 socket. Reason: at 1 mA the V2 triode sits at only
   −0.73 V grid to cathode, close to where a 12AX7 starts to draw grid current.
   The standard tube model has no grid current. With a representative
   grid-current law added, variant C's distortion at 5 mV rises from 0.02 % to
   0.24 %; at 0.8 mA (−1.04 V) it falls back to 0.013 %. A 12AT7 sits at
   −2.2 V with the same gain and distortion. How much grid current your V2
   draws depends on the individual tube, so treat this as a hedge. It also
   suggests that V2 is the socket where swapping tubes changes the sound most.

4. **Stage 1: choose R27 for the cartridge.** Always change R2 in the opposite
   direction so that R27 + R2 stays the same and the current does not move.
   - Moving magnet, about 5 mV: leave R27 at 909 Ω. Lower values add
     distortion and gain you do not need, for at most 2 dB of S/N.
   - High-output moving coil, about 2 mV: R27 220 to 470 Ω.
   - Low-output moving coil, 0.3 to 0.5 mV: R27 22 to 100 Ω and R2 about 1.8 to
     1.9 kΩ, with R19 = 1.5 kΩ (variant D): 58 to 61 dB, 2.2 to 2.6 nV/√Hz,
     70 to 72 dB S/N re 0.5 mV.

5. **For the quietest moving-coil stage, fit a 2SK170 or LSK170 at Q7**
   (variant E): 1.4 nV/√Hz and 76 dB S/N re 0.5 mV. It needs R27 22 to 47 Ω,
   R2 re-selected (about 300 Ω; aim for 100 to 110 V across R5) and C1 raised
   to 1000 µF. Do not fit one without re-selecting R2: with the present
   909 Ω + 1.00 kΩ it would run at 0.23 mA and starve the triode. Check the
   pinout; it differs from the U310 can.

6. **Volume pot and cable.** At −6 dB the 100 kΩ pot loses 1.5 dB at 10 kHz
   and 4.2 dB at 20 kHz into 500 pF. Keep the cable short, or replace the
   balance and volume pots with 25 kΩ parts: the loss at 20 kHz falls to
   0.65 dB and the follower drives them without added distortion. 10 kΩ pots
   reduce it to 0.15 dB but lose 0.5 dB at 20 Hz unless C7 is larger than the
   4.7 µF I assumed.

7. **RIAA trim, only after measuring R7.** If R7 is 22 kΩ and the other values
   are as read, the error is within ±0.6 dB. R7 = 24.3 kΩ, R9 = 649 kΩ and
   C4 = 0.22 µF bring the model within ±0.1 dB from 20 Hz to 20 kHz.

8. **Leave C21 unfitted.** On the drawing it links the two Q6 sources. With
   220 pF there, channel separation falls to 54 dB at 10 kHz and 48 dB at
   20 kHz. Unit 2 has a part in that position.

Not worth doing: changing the op-amp. It regulates the supply, and the model
shows 82 dB of rejection from the raw supply to B+ at 60 Hz with the LF353.
The small electrolytics carry 1984 date codes; replacing C1, C8, C3, C22 and
the supply capacitors is ordinary maintenance and was not simulated.

## What to measure

With the unit on, these low-voltage points give the two stage currents
directly:

| Measure | Model | Meaning |
|---|---|---|
| DC volts across R2 (1.00 kΩ) | 1.09 V | Stage-1 current in mA. Above about 1.3 V means the U310 is a higher-pinch-off part: raise R2 until it reads 1.0 to 1.1 V. |
| DC volts across R19 (274 Ω) | 0.274 V | Stage-2 current: 0.274 V per mA. |
| DC volts from the top of R5 or R10 to ground (B+) | 247 V | High voltage. Sets the headroom. The estimate could be 20 to 30 V out, which changes the results very little. |

With the unit off and C18 discharged:

- **R7**, in circuit. Its far end connects only to C5 and C6, so a meter
  across it reads the resistor alone.
- R11 as set, the values of C1, C8, C3 and C7 if the markings can be seen, and
  the zener type numbers.

Put any of these into `sim/circuit.py` and re-run the scripts.

## Running the model

**KiCad**: open `kicad/superit.kicad_pro` and simulate from Inspect >
Simulator. Every symbol has hidden `Status` and `Note` fields with the K/P/E
tag and the reading. The schematic is generated, so edit `sim/circuit.py` and
regenerate; do not edit the schematic:

```sh
cd kicad
python gen_kicad.py      # rebuild the project from sim/circuit.py
python verify_kicad.py   # ERC, then compare KiCad's netlist and results with the scripted model
```

If KiCad has the project open, close and reopen it after regenerating. The
project was regenerated for this writeup, so reopen it now.

**Scripts**: any Python 3 with numpy and matplotlib. They call the ngspice
library inside KiCad.app, so nothing else needs installing.

```sh
cd sim
python op_point.py       # DC voltages and currents
python variants.py       # bias point of each variant
python study.py          # gain, RIAA, noise, distortion for variants A to F  -> out/study.json
python extras.py         # pot and cable, supply rejection, crosstalk, sensitivities, R27 and R19 tables
python plots.py          # charts -> plots/
```

`study.py` and `extras.py` each take several minutes.

## Limits of this work

- Absolute figures are indicative. Differences between variants are more
  trustworthy than any single number, because the unknowns are common to all.
- The JFET model is a square-law device at one corner of the U310 data sheet.
  A centre-of-range model with the same resistors gives nearly the same gain,
  noise and distortion, at a different operating point.
- The triode model has no grid current and no microphony. Grid current is
  covered only by the sensitivity run in recommendation 3.
- Noise figures exclude hum pickup, heater-to-cathode leakage and tube flicker
  noise.
- The latest verification passes: ERC clean, 217 netlist elements identical
  between KiCad and the scripted model, operating points equal. Running the
  simulation from KiCad's own simulator window has not been tried.
- Nothing here has been checked against a measurement of the real unit.

## Sources

- <https://hifihaven.org/index.php?threads/new-ps-for-a-new-york-audio-labs-superit-phono-preamp.5806/>
- <https://www.diyaudio.com/community/threads/anyone-mod-a-nyal-moscode-superit.62147/>
- <https://www.diyaudio.com/community/threads/moscode-super-it-schematics-power-supply.291484/>
- <https://www.stereophile.com/content/new-york-audio-labs-superit-phono-preamplifier>
- <https://www.stereophile.com/content/new-york-audio-labs-superit-phono-preamplifier-anthony-h-cordesman-followup>
- <https://forum.audiogon.com/discussions/moscode-super-it-or-audio-research-ph3>
- <https://www.audiocircle.com/index.php?topic=19077.0>

Facts taken from them: three 12AX7s; R5 is 100 kΩ with about 100 V across it;
R2 is selected on test; restorers fit 2SK170s and swap the op-amp; a 72 dB
gain upgrade was offered; reviewers found it quiet with higher-output
cartridges and noisy with low-output moving coils. The Stereophile and
DIYAudio pages refused automated access, so for those I relied on search
excerpts only.
