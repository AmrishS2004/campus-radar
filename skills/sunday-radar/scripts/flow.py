#!/usr/bin/env python3
"""Campus Radar flowcharts: a student's week, or one assignment's steps, as a phone-friendly PDF.

Standard library only (it writes the PDF itself), so it runs on Cubbie with nothing to install.

  python3 scripts/flow.py week  --file week.json  [--out week.pdf]
  python3 scripts/flow.py steps --file steps.json [--out plan.pdf]
  python3 scripts/flow.py week --sample      (uses assets/sample_week.json)
  python3 scripts/flow.py steps --sample     (uses assets/sample_steps.json)

week.json:
  {"title": "Your week", "start": "2026-10-26", "crunch": "2026-10-28",
   "items": [{"date": "2026-10-28", "time": "11:59 pm", "kind": "deadline", "title": "HW 5",
              "course": "CSE 310", "note": "graph traversal", "conflict": "Robotics GBM 7 pm; start Mon"}]}
  kind is one of: deadline, exam, hidden, discussion, club, todo, class, block

steps.json:
  {"title": "HW 5: graph traversal", "course": "CSE 310", "due": "Sat Nov 7, 11:59 pm",
   "source": "HW 5 PDF and Lecture 16 slides",
   "steps": [{"text": "Read the spec and the Ed clarification", "when": "Mon", "minutes": 30}]}

Prints the PDF path. Exit codes: 0 ok, 3 bad input.
"""

import argparse
import json
import os
import re
import sys
import zlib
from datetime import date, datetime, timedelta

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "campus-radar", "flowcharts")

KINDS = {
    "exam": ("Exam", (0.48, 0.25, 0.77)),
    "deadline": ("Due", (0.04, 0.38, 0.79)),
    "hidden": ("From slides", (0.85, 0.45, 0.05)),
    "discussion": ("Discussion", (0.06, 0.55, 0.55)),
    "club": ("Club", (0.18, 0.55, 0.34)),
    "todo": ("To-do", (0.36, 0.40, 0.46)),
    "class": ("Class", (0.54, 0.58, 0.64)),
    "block": ("Study block", (0.70, 0.25, 0.50)),
}
INK = (0.09, 0.13, 0.17)
MUTED = (0.36, 0.40, 0.46)
LINE = (0.80, 0.83, 0.87)
PAPER = (1, 1, 1)
CARD = (0.97, 0.98, 0.99)
RED = (0.76, 0.21, 0.17)
RED_BG = (0.99, 0.92, 0.91)
GREEN = (0.12, 0.54, 0.30)


class BadInput(Exception):
    pass


# ---------- text measuring (Helvetica AFM widths, 1/1000 em) ----------

_W = {}
for ch, w in zip(" !\"#$%&'()*+,-./", [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278]):
    _W[ch] = w
for ch in "0123456789":
    _W[ch] = 556
for ch, w in zip(":;<=>?@", [278, 278, 584, 584, 584, 556, 1015]):
    _W[ch] = w
for ch, w in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                 [667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667,
                  611, 722, 667, 944, 667, 667, 611]):
    _W[ch] = w
for ch, w in zip("[\\]^_`", [278, 278, 278, 469, 556, 333]):
    _W[ch] = w
for ch, w in zip("abcdefghijklmnopqrstuvwxyz",
                 [556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500,
                  278, 556, 500, 722, 500, 500, 500]):
    _W[ch] = w
for ch, w in zip("{|}~", [334, 260, 334, 584]):
    _W[ch] = w

SUBS = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
        "…": "...", " ": " ", "→": "->", "•": "-"}


def clean(s):
    s = "".join(SUBS.get(c, c) for c in str(s or ""))
    return "".join(c if 32 <= ord(c) < 127 or 160 <= ord(c) < 256 else "?" for c in s).strip()


def width(s, size, bold=False):
    w = sum(_W.get(c, 556) for c in s) * size / 1000.0
    return w * (1.06 if bold else 1.0)


def wrap(s, size, maxw, bold=False, max_lines=4):
    words, lines, cur = clean(s).split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if width(trial, size, bold) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines[-1] and width(lines[-1] + "...", size, bold) > maxw:
            lines[-1] = lines[-1][:-1]
        lines[-1] = lines[-1].rstrip() + "..."
    return lines or [""]


# ---------- tiny PDF canvas (top-left coordinates) ----------

class Canvas:
    def __init__(self, w):
        self.w, self.ops = w, []

    def _c(self, rgb, stroke=False):
        return "%.3f %.3f %.3f %s" % (rgb[0], rgb[1], rgb[2], "RG" if stroke else "rg")

    def rect(self, x, y, w, h, fill=None, stroke=None, lw=1, r=0, dash=False):
        self.ops.append(("rect", x, y, w, h, fill, stroke, lw, r, dash))

    def line(self, x1, y1, x2, y2, color=LINE, lw=1.2):
        self.ops.append(("line", x1, y1, x2, y2, color, lw))

    def arrow(self, x, y1, y2, color=LINE):
        self.line(x, y1, x, y2 - 5, color, 1.4)
        self.ops.append(("tri", x, y2, color))

    def circle(self, cx, cy, r, fill):
        self.ops.append(("circle", cx, cy, r, fill))

    def text(self, x, y, s, size=10, bold=False, color=INK, align="left"):
        s = clean(s)
        if align == "right":
            x -= width(s, size, bold)
        elif align == "center":
            x -= width(s, size, bold) / 2
        self.ops.append(("text", x, y, s, size, bold, color))

    def render(self, h):
        out = []
        Y = lambda y: h - y
        k = 0.5523
        for op in self.ops:
            kind = op[0]
            if kind == "rect":
                _, x, y, w, hh, fill, stroke, lw, r, dash = op
                x0, y0, x1, y1 = x, Y(y + hh), x + w, Y(y)
                r = min(r, w / 2, hh / 2)
                parts = []
                if fill:
                    parts.append(self._c(fill))
                if stroke:
                    parts.append(self._c(stroke, True))
                    parts.append("%.2f w" % lw)
                parts.append("[3 3] 0 d" if dash else "[] 0 d")
                if r:
                    c = r * k
                    path = ("%.2f %.2f m %.2f %.2f l %.2f %.2f %.2f %.2f %.2f %.2f c %.2f %.2f l "
                            "%.2f %.2f %.2f %.2f %.2f %.2f c %.2f %.2f l %.2f %.2f %.2f %.2f %.2f %.2f c "
                            "%.2f %.2f l %.2f %.2f %.2f %.2f %.2f %.2f c h") % (
                        x0 + r, y0, x1 - r, y0, x1 - r + c, y0, x1, y0 + r - c, x1, y0 + r, x1, y1 - r,
                        x1, y1 - r + c, x1 - r + c, y1, x1 - r, y1, x0 + r, y1, x0 + r - c, y1, x0, y1 - r + c,
                        x0, y1 - r, x0, y0 + r, x0, y0 + r - c, x0 + r - c, y0, x0 + r, y0)
                else:
                    path = "%.2f %.2f %.2f %.2f re" % (x0, y0, w, hh)
                paint = "B" if fill and stroke else "f" if fill else "S"
                parts.append(path + " " + paint)
                out.append(" ".join(parts))
            elif kind == "line":
                _, x1, y1, x2, y2, color, lw = op
                out.append("%s %.2f w [] 0 d %.2f %.2f m %.2f %.2f l S" % (self._c(color, True), lw, x1, Y(y1), x2, Y(y2)))
            elif kind == "tri":
                _, x, y, color = op
                out.append("%s %.2f %.2f m %.2f %.2f l %.2f %.2f l h f" % (
                    self._c(color), x - 4.5, Y(y - 6), x + 4.5, Y(y - 6), x, Y(y)))
            elif kind == "circle":
                _, cx, cy, r, fill = op
                c = r * k
                cy = Y(cy)
                out.append("%s %.2f %.2f m %.2f %.2f %.2f %.2f %.2f %.2f c %.2f %.2f %.2f %.2f %.2f %.2f c "
                           "%.2f %.2f %.2f %.2f %.2f %.2f c %.2f %.2f %.2f %.2f %.2f %.2f c f" % (
                               self._c(fill), cx + r, cy, cx + r, cy + c, cx + c, cy + r, cx, cy + r,
                               cx - c, cy + r, cx - r, cy + c, cx - r, cy, cx - r, cy - c, cx - c, cy - r, cx, cy - r,
                               cx + c, cy - r, cx + r, cy - c, cx + r, cy))
            elif kind == "text":
                _, x, y, s, size, bold, color = op
                esc = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                out.append("BT /%s %.1f Tf %s %.2f %.2f Td (%s) Tj ET" % (
                    "F2" if bold else "F1", size, self._c(color), x, Y(y), esc))
        return "\n".join(out)

    def save(self, path, h):
        content = zlib.compress(self.render(h).encode("latin-1", "replace"))
        objs = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] /Contents 4 0 R "
             "/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>" % (self.w, h)).encode(),
            b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(content) + content + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        ]
        data, offsets = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n", []
        for i, o in enumerate(objs, 1):
            offsets.append(len(data))
            data += b"%d 0 obj\n" % i + o + b"\nendobj\n"
        xref = len(data)
        data += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
        for off in offsets:
            data += b"%010d 00000 n \n" % off
        data += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)


# ---------- helpers ----------

def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise BadInput("Can't find '%s'." % path)
    except json.JSONDecodeError as e:
        raise BadInput("'%s' isn't valid JSON (%s)." % (path, e))


def parse_day(s, field):
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        raise BadInput("%s '%s' should be a date like 2026-10-26." % (field, s))


def time_key(t):
    m = re.match(r"\s*(\d{1,2})(?::(\d{2}))?\s*([ap]\.?m\.?)?", str(t or "").lower())
    if not m:
        return 24 * 60 + 1
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ap:
        h = h % 12 + (12 if ap.startswith("p") else 0)
    return h * 60 + mi


def fmt_day(d):
    return d.strftime("%a"), d.strftime("%b ") + str(d.day)


def header(cv, x, y, title, subtitle, maxw):
    lines = wrap(title, 20, maxw, True, 2)
    for i, ln in enumerate(lines):
        cv.text(x, y + 20 + i * 24, ln, 20, True)
    y += 20 + (len(lines) - 1) * 24 + 8
    for ln in wrap(subtitle, 10.5, maxw, False, 2):
        y += 15
        cv.text(x, y, ln, 10.5, False, MUTED)
    return y + 14


def legend(cv, x, y, kinds, maxw):
    cx = x
    for k in kinds:
        label = KINDS[k][0]
        w = width(label, 9, True) + 22
        if cx + w > x + maxw:
            cx, y = x, y + 20
        cv.rect(cx, y, w, 16, fill=CARD, stroke=LINE, lw=0.6, r=8)
        cv.circle(cx + 9, y + 8, 3.2, KINDS[k][1])
        cv.text(cx + 16, y + 11.5, label, 9, True, MUTED)
        cx += w + 6
    return y + 28


# ---------- week flowchart ----------

def build_week(data, out):
    if not isinstance(data.get("items"), list):
        raise BadInput("week.json needs an 'items' list (it can be empty).")
    start = parse_day(data.get("start") or min((i.get("date") for i in data["items"]), default=None)
                      or date.today().isoformat(), "start")
    days = [start + timedelta(days=i) for i in range(7)]
    crunch = parse_day(data["crunch"], "crunch") if data.get("crunch") else None
    by_day = {d: [] for d in days}
    used_kinds = []
    for it in data["items"]:
        if not it.get("title"):
            raise BadInput("Every item needs a 'title'.")
        k = it.get("kind", "deadline")
        if k not in KINDS:
            raise BadInput("Unknown kind '%s'. Use one of: %s." % (k, ", ".join(KINDS)))
        d = parse_day(it.get("date"), "date")
        if d in by_day:
            by_day[d].append(it)
            if k not in used_kinds:
                used_kinds.append(k)
    for d in days:
        by_day[d].sort(key=lambda i: time_key(i.get("time")))

    W, M = 420, 22
    cv = Canvas(W)
    title = data.get("title") or "Your week"
    sub = "%s to %s" % (fmt_day(days[0])[1], fmt_day(days[-1])[1])
    n = sum(len(v) for v in by_day.values())
    clashes = sum(1 for v in by_day.values() for i in v if i.get("conflict"))
    sub += " | %d item%s" % (n, "" if n == 1 else "s")
    if clashes:
        sub += " | %d clash%s" % (clashes, "" if clashes == 1 else "es")
    y = header(cv, M, 8, title, sub, W - 2 * M)
    order = [k for k in KINDS if k in used_kinds]
    if order:
        y = legend(cv, M, y, order, W - 2 * M)

    pill_w, spine = 70, M + 35
    cx0, cw = M + pill_w + 16, W - M - (M + pill_w + 16)
    prev_bottom = None
    for d in days:
        items = by_day[d]
        is_crunch = crunch == d
        if prev_bottom is not None:
            cv.arrow(spine, prev_bottom + 2, y - 2)
        # cards
        cards, cy = [], y
        for it in items:
            k = it.get("kind", "deadline")
            label, color = KINDS[k]
            t_lines = wrap(it["title"], 11, cw - 24, True, 3)
            meta = " | ".join(clean(p) for p in (it.get("course"), it.get("note")) if p)
            m_lines = wrap(meta, 9, cw - 24, False, 2) if meta else []
            c_lines = wrap("Clash: " + it["conflict"], 9, cw - 24, True, 3) if it.get("conflict") else []
            h = 12 + 11 + len(t_lines) * 14 + len(m_lines) * 12 + (len(c_lines) * 12 + 6 if c_lines else 0) + 6
            cards.append((it, k, label, color, t_lines, m_lines, c_lines, cy, h))
            cy += h + 8
        block_h = max(46, (cy - 8 - y) if items else 46)
        # day pill
        fill = RED_BG if is_crunch else CARD
        stroke = RED if is_crunch else LINE
        cv.rect(M, y, pill_w, 46, fill=fill, stroke=stroke, lw=1.2 if is_crunch else 0.8, r=12)
        wd, md = fmt_day(d)
        cv.text(M + pill_w / 2, y + 20, wd, 13, True, RED if is_crunch else INK, "center")
        cv.text(M + pill_w / 2, y + 35, md, 9, False, MUTED, "center")
        if is_crunch:
            cv.text(M + pill_w / 2, y + 60, "Crunch day", 8.5, True, RED, "center")
        if not items:
            cv.rect(cx0, y + 8, cw, 30, stroke=LINE, lw=0.8, r=8, dash=True)
            cv.text(cx0 + 12, y + 27, "Nothing due. Free day.", 9.5, False, MUTED)
            cv.line(M + pill_w, y + 23, cx0, y + 23, LINE, 0.8)
        for (it, k, label, color, t_lines, m_lines, c_lines, top, h) in cards:
            clash = bool(c_lines)
            cv.line(M + pill_w, y + 23, cx0, top + 14, LINE, 0.8)
            cv.rect(cx0, top, cw, h, fill=PAPER, stroke=RED if clash else LINE, lw=1.4 if clash else 0.8, r=8)
            cv.rect(cx0, top, 5, h, fill=color, r=2)
            tag = label + ((" | " + clean(it["time"])) if it.get("time") else "")
            ty = top + 15
            cv.text(cx0 + 14, ty, tag.upper(), 8, True, color)
            for ln in t_lines:
                ty += 14
                cv.text(cx0 + 14, ty, ln, 11, True)
            for ln in m_lines:
                ty += 12
                cv.text(cx0 + 14, ty, ln, 9, False, MUTED)
            if c_lines:
                ty += 6
                for ln in c_lines:
                    ty += 12
                    cv.text(cx0 + 14, ty, ln, 9, True, RED)
        bottom = y + max(block_h, 66 if is_crunch else 46)
        prev_bottom = y + (68 if is_crunch else 46)
        y = bottom + 18
    cv.text(M, y + 6, "Made by Campus Radar. Check important dates against Canvas.", 8, False, MUTED)
    cv.save(out, y + 22)
    return n, clashes


# ---------- assignment steps flowchart ----------

def build_steps(data, out):
    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        raise BadInput("steps.json needs a non-empty 'steps' list.")
    W, M = 420, 22
    cv = Canvas(W)
    sub = " | ".join(clean(p) for p in (data.get("course"), ("due " + data["due"]) if data.get("due") else None) if p)
    y = header(cv, M, 8, data.get("title") or "Your plan", sub or "Step by step", W - 2 * M)
    bw, bx = W - 2 * M, M
    total = 0
    # start node
    cv.rect(bx + bw / 2 - 70, y, 140, 26, fill=CARD, stroke=LINE, lw=0.8, r=13)
    cv.text(bx + bw / 2, y + 17, "Start", 10, True, MUTED, "center")
    y += 26
    for i, st in enumerate(steps, 1):
        if not st.get("text"):
            raise BadInput("Step %d needs 'text'." % i)
        cv.arrow(bx + bw / 2, y + 2, y + 20)
        y += 22
        when = clean(st.get("when", ""))
        mins = st.get("minutes")
        if isinstance(mins, (int, float)) and mins > 0:
            total += mins
        right = " | ".join(p for p in (when, ("%d min" % mins) if isinstance(mins, (int, float)) and mins else "") if p)
        rw = width(right, 9, True) + 12 if right else 0
        lines = wrap(st["text"], 11, bw - 52 - rw, False, 4)
        h = max(40, 16 + len(lines) * 14 + 6)
        cv.rect(bx, y, bw, h, fill=PAPER, stroke=LINE, lw=0.9, r=10)
        cv.circle(bx + 20, y + 20, 11, KINDS["deadline"][1])
        cv.text(bx + 20, y + 24, str(i), 10, True, PAPER, "center")
        ty = y + 9
        for ln in lines:
            ty += 14
            cv.text(bx + 40, ty, ln, 11)
        if right:
            cv.text(bx + bw - 10, y + 23, right, 9, True, MUTED, "right")
        y += h
    cv.arrow(bx + bw / 2, y + 2, y + 20)
    y += 22
    end = "Submit it yourself" + ((" by " + clean(data["due"])) if data.get("due") else "")
    ew = min(bw, width(end, 10.5, True) + 40)
    cv.rect(bx + bw / 2 - ew / 2, y, ew, 30, fill=(0.89, 0.96, 0.92), stroke=GREEN, lw=1.2, r=15)
    cv.text(bx + bw / 2, y + 19.5, end, 10.5, True, GREEN, "center")
    y += 48
    foot = []
    if total:
        foot.append("About %s of work" % (("%d min" % total) if total < 90 else ("%.1f hours" % (total / 60.0))))
    if data.get("source"):
        foot.append("From " + clean(data["source"]))
    for ln in wrap(". ".join(foot), 8.5, bw, False, 3) if foot else []:
        cv.text(M, y, ln, 8.5, False, MUTED)
        y += 12
    cv.text(M, y + 4, "Made by Campus Radar. Follow your course's rules on AI and collaboration.", 8, False, MUTED)
    cv.save(out, y + 20)
    return len(steps), total


def default_out(kind):
    return os.path.join(OUT_DIR, "%s-%s.pdf" % (kind, datetime.now().strftime("%Y%m%d-%H%M%S")))


def main(argv=None):
    p = argparse.ArgumentParser(prog="flow.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("week", "steps"):
        sp = sub.add_parser(name)
        sp.add_argument("--file")
        sp.add_argument("--out")
        sp.add_argument("--sample", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.sample:
            src = os.path.join(SKILL_DIR, "assets", "sample_%s.json" % args.cmd)
        elif args.file:
            src = args.file
        else:
            raise BadInput("Pass --file with the data, or --sample.")
        data = load(src)
        out = args.out or default_out(args.cmd)
        if args.cmd == "week":
            n, clashes = build_week(data, out)
            print("Week flowchart: %d item%s, %d clash%s" % (n, "" if n == 1 else "s", clashes, "" if clashes == 1 else "es"))
        else:
            n, total = build_steps(data, out)
            print("Steps flowchart: %d steps" % n + (", about %d min" % total if total else ""))
        print(os.path.abspath(out))
    except BadInput as e:
        print(str(e))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
