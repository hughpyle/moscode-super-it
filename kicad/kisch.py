"""Minimal KiCad schematic writer used by gen_kicad.py.

Coordinates in the API are in grid units (1 u = 2.54 mm, y down), so pins of
stock symbols land on whole or half units.  Symbols are copied from the
installed KiCad libraries and embedded in the sheet.  Junction dots are placed
automatically wherever three or more wire ends / pins meet, and wires are
split where another wire or a pin ends on them, so a "T" always connects.
"""
import os
import re
import uuid

U = 2.54
SYMDIR = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
NS = uuid.UUID("6f1d3c52-9a5e-4c0e-8f0b-5d2a51e0d0a1")


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(str(p) for p in parts)))


# ---------------------------------------------------------------- s-expressions
class Sym(str):
    pass


def parse(t):
    tok = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')
    st = [[]]
    for m in tok.finditer(t):
        s = m.group(0)
        if s == "(":
            n = []
            st[-1].append(n)
            st.append(n)
        elif s == ")":
            st.pop()
        elif s[0] == '"':
            body = s[1:-1]
            if "\\" in body:
                body = body.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
            st[-1].append(body)
        else:
            st[-1].append(Sym(s))
    return st[0][0]


def quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def dump(x, ind=0):
    pad = "\t" * ind
    if isinstance(x, list):
        if all(not isinstance(e, list) for e in x):
            return pad + "(" + " ".join(dump(e) for e in x) + ")"
        i = 0
        head = []
        while i < len(x) and not isinstance(x[i], list):
            head.append(dump(x[i]))
            i += 1
        body = "\n".join(dump(e, ind + 1) if isinstance(e, list) else "\t" * (ind + 1) + dump(e)
                         for e in x[i:])
        return pad + "(" + " ".join(head) + "\n" + body + "\n" + pad + ")"
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, str):
        return quote(x)
    if isinstance(x, float):
        return ("%.4f" % x).rstrip("0").rstrip(".") or "0"
    return str(x)


def S(*a):
    """Build a list whose first element (and any bare words) are symbols."""
    return [Sym(a[0])] + list(a[1:])


def find(x, key):
    return [e for e in x if isinstance(e, list) and e and e[0] == key]


# ---------------------------------------------------------------- library symbols
_libtext = {}
_symcache = {}


def _block(lib, name):
    if lib not in _libtext:
        with open(os.path.join(SYMDIR, lib + ".kicad_sym")) as f:
            _libtext[lib] = f.read()
    t = _libtext[lib]
    i = t.index('\n\t(symbol "%s"\n' % name) + 1
    depth, instr, j = 0, False, i
    while True:
        c = t[j]
        if instr:
            if c == "\\":
                j += 1
            elif c == '"':
                instr = False
        elif c == '"':
            instr = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return t[i:j + 1]
        j += 1


def load_symbol(lib_id):
    """Return the library symbol as an s-expr named lib:name (extends flattened)."""
    if lib_id in _symcache:
        return _symcache[lib_id]
    lib, name = lib_id.split(":")
    s = parse(_block(lib, name))
    ext = find(s, "extends")
    if ext:
        parent = load_symbol(lib + ":" + ext[0][1])
        pname = ext[0][1]
        props = {p[1]: p for p in find(s, "property")}
        out = []
        for e in parent:
            if isinstance(e, list) and e[0] == "property" and e[1] in props:
                out.append(props.pop(e[1]))
            elif isinstance(e, list) and e[0] == "symbol":
                e = list(e)
                e[1] = name + e[1][len(pname):]
                out.append(e)
            else:
                out.append(e)
        idx = next(i for i, e in enumerate(out) if isinstance(e, list) and e[0] == "symbol")
        out[idx:idx] = list(props.values())
        s = out
    s = list(s)
    s[1] = lib_id
    _symcache[lib_id] = s
    return s


def symbol_pins(lib_id):
    """{unit: {number: (x, y)}} in library coordinates (mm, y up); unit 0 = all."""
    s = load_symbol(lib_id)
    base = lib_id.split(":")[1]
    r = {}
    for sub in find(s, "symbol"):
        unit = int(sub[1][len(base) + 1:].split("_")[0])
        for p in find(sub, "pin"):
            at = find(p, "at")[0]
            r.setdefault(unit, {})[find(p, "number")[0][1]] = (float(at[1]), float(at[2]))
    return r


def xform(x, y, rot, mirror):
    """Library (y up, mm) -> sheet offset (y down, mm) for a placed symbol."""
    if mirror == "x":
        y = -y
    elif mirror == "y":
        x = -x
    if rot == 0:
        return x, -y
    if rot == 90:
        return -y, -x
    if rot == 180:
        return -x, y
    if rot == 270:
        return y, x
    raise ValueError(rot)


FONT = S("font", S("size", 1.27, 1.27))


def effects(just=None, hide=False, size=1.27, bold=False):
    font = S("font", S("size", size, size))
    if bold:
        font.append(S("bold", Sym("yes")))
    e = S("effects", font)
    if just:
        e.append(S("justify", *[Sym(j) for j in just.split()]))
    if hide:
        e.append(S("hide", Sym("yes")))
    return e


class Placed:
    def __init__(self, sheet, ref, lib_id, x, y, rot, mirror, unit):
        self.sheet, self.ref, self.lib_id = sheet, ref, lib_id
        self.x, self.y, self.rot, self.mirror, self.unit = x, y, rot, mirror, unit
        pins = symbol_pins(lib_id)
        self.pins = dict(pins.get(0, {}))
        self.pins.update(pins.get(unit, {}))

    def pin(self, num):
        px, py = self.pins[str(num)]
        dx, dy = xform(px, py, self.rot, self.mirror)
        return (round(self.x + dx / U, 4), round(self.y + dy / U, 4))

    p = pin


class Sheet:
    """One schematic sheet."""

    def __init__(self, project, name, filename, paper="A3", title="", comments=(),
                 instances=None):
        self.project, self.name, self.filename = project, name, filename
        self.paper, self.title, self.comments = paper, title, comments
        self.uuid = uid("sheet", filename)
        # instances: list of (path, refmap) where refmap(ref)->ref for that path
        self.instances = instances or []
        self.libs = {}
        self.items = []
        self.wires = []
        self.pinpts = []
        self.nolink = set()
        self._n = 0
        self._pwr = 0

    def _id(self, kind):
        self._n += 1
        return uid(self.filename, kind, self._n)

    # ---- symbols
    def sym(self, ref, lib_id, x, y, rot=0, mirror=None, value="", unit=1, fields=None,
            rp=None, vp=None, exclude_sim=False, show_value=True, inst_units=None,
            in_bom=True):
        """Place a symbol.  rp / vp = (dx, dy, justify) text offsets in u from the
        symbol origin, in sheet orientation.  inst_units: per-instance unit list."""
        self.libs.setdefault(lib_id, load_symbol(lib_id))
        pl = Placed(self, ref, lib_id, x, y, rot, mirror, unit)
        ang = 90 if rot in (90, 270) else 0     # stored so the text reads horizontally

        def prop(name, val, pos, hide=False):
            dx, dy, just = pos
            # KiCad draws field text through the symbol transform: these
            # orientations swap left and right, so pre-swap to get what was asked
            if just and (rot in (90, 180) or mirror == "y"):
                just = just.replace("left", "~").replace("right", "left").replace("~", "right")
            return S("property", name, val, S("at", (x + dx) * U, (y + dy) * U, ang),
                     effects(just, hide))

        rp = rp or (1.2, -0.5, "left")
        vp = vp or (1.2, 0.5, "left")
        e = S("symbol", S("lib_id", lib_id), S("at", x * U, y * U, rot))
        if mirror:
            e.append(S("mirror", Sym(mirror)))
        e += [S("unit", unit), S("exclude_from_sim", Sym("yes" if exclude_sim else "no")),
              S("in_bom", Sym("yes" if in_bom else "no")), S("on_board", Sym("yes")),
              S("dnp", Sym("no")), S("uuid", self._id("sym"))]
        e.append(prop("Reference", ref, rp, hide=ref.startswith("#")))
        e.append(prop("Value", value, vp, hide=not show_value))
        e.append(prop("Footprint", "", (0, 0, None), hide=True))
        e.append(prop("Datasheet", "", (0, 0, None), hide=True))
        e.append(prop("Description", "", (0, 0, None), hide=True))
        for k, v in (fields or {}).items():
            e.append(prop(k, v, (0, 0, None), hide=True))
        inst = S("instances")
        proj = S("project", self.project)
        for i, (path, refmap) in enumerate(self.instances):
            u = inst_units[i] if inst_units else unit
            proj.append(S("path", path, S("reference", refmap(ref)), S("unit", u)))
        inst.append(proj)
        e.append(inst)
        self.items.append(e)
        for num in pl.pins:
            self.pinpts.append(pl.pin(num))
        return pl

    def gnd(self, pt, rot=0):
        self._pwr += 1
        ref = "#PWR%02d" % self._pwr
        return self.sym(ref, "power:GND", pt[0], pt[1], rot=rot, value="GND",
                        vp=(0, 1.9, None), show_value=False)

    # ---- wires and labels
    def wire(self, *pts):
        """Polyline through points; consecutive points must share x or y."""
        for a, b in zip(pts, pts[1:]):
            a = (round(a[0], 4), round(a[1], 4))
            b = (round(b[0], 4), round(b[1], 4))
            if a == b:
                continue
            if abs(a[0] - b[0]) > 1e-6 and abs(a[1] - b[1]) > 1e-6:
                raise ValueError("diagonal wire %s -> %s on %s" % (a, b, self.name))
            self.wires.append((a, b))

    def label(self, name, pt, rot=0, just="left bottom"):
        self.items.append(S("label", name, S("at", pt[0] * U, pt[1] * U, rot),
                            effects(just), S("uuid", self._id("label"))))

    def hlabel(self, name, pt, shape="passive", rot=180):
        just = {0: "left", 180: "right", 90: "left", 270: "right"}[rot]
        self.items.append(S("hierarchical_label", name, S("shape", Sym(shape)),
                            S("at", pt[0] * U, pt[1] * U, rot), effects(just),
                            S("uuid", self._id("hlabel"))))

    def noconnect(self, pt):
        self.items.append(S("no_connect", S("at", pt[0] * U, pt[1] * U),
                            S("uuid", self._id("nc"))))

    def text(self, s, pt, size=1.27, just="left top", bold=False):
        self.items.append(S("text", s, S("exclude_from_sim", Sym("no")),
                            S("at", pt[0] * U, pt[1] * U, 0),
                            effects(just, size=size, bold=bold), S("uuid", self._id("text"))))

    def box(self, a, b, dash=True):
        self.items.append(S("rectangle", S("start", a[0] * U, a[1] * U),
                            S("end", b[0] * U, b[1] * U),
                            S("stroke", S("width", 0.15), S("type", Sym("dash" if dash else "solid"))),
                            S("fill", S("type", Sym("none"))), S("uuid", self._id("rect"))))

    def subsheet(self, name, filename, x, y, w, h, pins, page):
        """pins: list of (name, side 'L'|'R', offset in u from top)."""
        su = uid("sheetsym", self.filename, name)
        e = S("sheet", S("at", x * U, y * U), S("size", w * U, h * U),
              S("exclude_from_sim", Sym("no")), S("in_bom", Sym("yes")),
              S("on_board", Sym("yes")), S("dnp", Sym("no")),
              S("stroke", S("width", 0.1524), S("type", Sym("solid"))),
              S("fill", S("color", 255, 255, 194, 1.0)), S("uuid", su),
              S("property", "Sheetname", name, S("at", x * U, y * U - 0.7, 0),
                effects("left bottom")),
              S("property", "Sheetfile", filename, S("at", x * U, (y + h) * U + 0.6, 0),
                effects("left top")))
        pts = {}
        for pname, side, off in pins:
            px = x if side == "L" else x + w
            py = y + off
            e.append(S("pin", pname, Sym("passive"), S("at", px * U, py * U, 180 if side == "L" else 0),
                       S("uuid", uid("sheetpin", name, pname)),
                       effects("left" if side == "L" else "right")))
            pts[pname] = (px, py)
            self.pinpts.append((round(px, 4), round(py, 4)))
        e.append(S("instances", S("project", self.project,
                                  S("path", "/" + self.uuid, S("page", str(page))))))
        self.items.append(e)
        return su, pts

    # ---- output
    def _finish_wires(self):
        """Split wires at T points and return (segments, junction points)."""
        ends = set(self.pinpts)
        for a, b in self.wires:
            ends.add(a)
            ends.add(b)
        segs = []
        for a, b in self.wires:
            cuts = [a, b]
            for p in ends:
                if p in (a, b):
                    continue
                if a[0] == b[0] == p[0] and min(a[1], b[1]) < p[1] < max(a[1], b[1]):
                    cuts.append(p)
                elif a[1] == b[1] == p[1] and min(a[0], b[0]) < p[0] < max(a[0], b[0]):
                    cuts.append(p)
            cuts.sort()
            segs += list(zip(cuts, cuts[1:]))
        segs = sorted(set(segs))
        deg = {}
        for a, b in segs:
            deg[a] = deg.get(a, 0) + 1
            deg[b] = deg.get(b, 0) + 1
        for p in self.pinpts:
            if p in deg:
                deg[p] += 1
        return segs, sorted(p for p, n in deg.items() if n >= 3)

    def render(self, root=False, pages=()):
        segs, juncs = self._finish_wires()
        doc = S("kicad_sch", S("version", 20250114), S("generator", "eeschema"),
                S("generator_version", "9.0"), S("uuid", self.uuid), S("paper", self.paper))
        tb = S("title_block", S("title", self.title))
        for i, c in enumerate(self.comments):
            tb.append(S("comment", i + 1, c))
        doc.append(tb)
        doc.append(S("lib_symbols", *[self.libs[k] for k in sorted(self.libs)]))
        for p in juncs:
            doc.append(S("junction", S("at", p[0] * U, p[1] * U), S("diameter", 0),
                         S("color", 0, 0, 0, 0), S("uuid", uid(self.filename, "j", p))))
        for a, b in segs:
            doc.append(S("wire", S("pts", S("xy", a[0] * U, a[1] * U), S("xy", b[0] * U, b[1] * U)),
                         S("stroke", S("width", 0), S("type", Sym("default"))),
                         S("uuid", uid(self.filename, "w", a, b))))
        doc += self.items
        if root:
            si = S("sheet_instances", S("path", "/", S("page", "1")))
            doc.append(si)
        doc.append(S("embedded_fonts", Sym("no")))
        return dump(doc) + "\n"
