from simlib import run
ctl = """
op
print v(raw) v(rail) v(neg) v(vref) v(bp1) v(bp2) v(vh) v(vg2)
print v(xchl.p1) v(xchl.k1) v(xchl.g1) v(xchl.s7) v(xchl.n2)
print v(xchl.p2) v(xchl.k2) v(xsl) v(xchl.n11) v(xchl.s5) v(xchl.g6)
print @j.xchl.jq7[id] @j.xchl.jq6[id] @j.xchl.jq7[gm] @j.xchl.jq6[gm]
print @m.xchl.mq5[id] @m.xchl.mq5[gm] @mq3[id] @mq4[id] v(gq3) v(zref) i(vvht) i(vvhtr)
"""
lines, vals = run("op", control=ctl)
for l in lines:
    if "=" in l and not l.startswith(("Note", "Doing", "Using")): print(l)
