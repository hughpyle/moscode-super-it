"""Export the schematic for reading without KiCad.

    python3 export.py

writes superit-schematic.pdf (three pages: power supply and test fixture,
left channel, right channel) and channel.png (the audio circuit of one
channel, used in the README).  Needs kicad-cli and ImageMagick (magick)
on the PATH.  Run it after gen_kicad.py whenever sim/circuit.py changes.
"""
import os, subprocess, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCH = os.path.join(HERE, "superit.kicad_sch")
# Part of the A3 channel sheet that holds the circuit (fractions of width, height).
CROP = (0.035, 0.040, 0.985, 0.690)
DENSITY = 150          # A3 at 150 dpi is 2480 px wide


def sh(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("%s failed:\n%s" % (cmd[0], r.stderr))


def main():
    sh("kicad-cli", "sch", "export", "pdf", "-o", os.path.join(HERE, "superit-schematic.pdf"), SCH)
    with tempfile.TemporaryDirectory() as tmp:
        sh("kicad-cli", "sch", "export", "svg", "-e", "-o", tmp, SCH)
        svg = os.path.join(tmp, "superit-LEFT.svg")
        size = subprocess.run(["magick", "-density", str(DENSITY), svg, "-format", "%w %h", "info:"],
                              check=True, capture_output=True, text=True).stdout.split()
        w, h = int(size[0]), int(size[1])
        x0, y0, x1, y1 = CROP
        geom = "%dx%d+%d+%d" % ((x1 - x0)*w, (y1 - y0)*h, x0*w, y0*h)
        sh("magick", "-density", str(DENSITY), "-background", "white", svg, "-flatten",
           "-crop", geom, "+repage", "-strip", os.path.join(HERE, "channel.png"))
    print("wrote superit-schematic.pdf, channel.png")


if __name__ == "__main__":
    main()
