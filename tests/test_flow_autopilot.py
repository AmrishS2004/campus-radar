"""Tests for the flowchart renderer and the autopilot health check."""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills")
FLOW = os.path.join(ROOT, "sunday-radar", "scripts", "flow.py")
CHECK = os.path.join(ROOT, "radar-autopilot", "scripts", "selfcheck.py")
TMP = tempfile.mkdtemp()
ENV = dict(os.environ, HOME=TMP)
fails = 0


def run(script, *args):
    p = subprocess.run([sys.executable, "-I", script, *args], capture_output=True, text=True, env=ENV)
    return p.returncode, (p.stdout + p.stderr).strip()


def check(name, cond, detail=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  -> " + detail))
    fails += 0 if cond else 1


def is_pdf(path):
    return os.path.isfile(path) and open(path, "rb").read(5) == b"%PDF-" and b"%%EOF" in open(path, "rb").read()[-32:]


out = os.path.join(TMP, "w.pdf")
code, o = run(FLOW, "week", "--sample", "--out", out)
check("flow: sample week renders", code == 0 and is_pdf(out) and "9 items, 1 clash" in o, o)
code, o = run(FLOW, "steps", "--sample", "--out", os.path.join(TMP, "s.pdf"))
check("flow: sample steps renders", code == 0 and is_pdf(os.path.join(TMP, "s.pdf")) and "6 steps" in o, o)
code, o = run(FLOW, "week", "--sample")
path = o.splitlines()[-1] if o else ""
check("flow: default output lands under HOME", code == 0 and path.startswith(TMP) and is_pdf(path), o)

empty = os.path.join(TMP, "empty.json")
json.dump({"start": "2026-11-02", "items": []}, open(empty, "w"))
code, o = run(FLOW, "week", "--file", empty, "--out", os.path.join(TMP, "e.pdf"))
check("flow: empty week still renders (all free days)", code == 0 and is_pdf(os.path.join(TMP, "e.pdf")), o)

weird = os.path.join(TMP, "weird.json")
json.dump({"start": "2026-11-02", "items": [
    {"date": "2026-11-03", "kind": "exam", "title": "Exam (part 1) \\ “quotes” — dash é " + "long " * 40},
    {"date": "2026-11-10", "kind": "exam", "title": "outside the week, ignored"}]}, open(weird, "w"))
code, o = run(FLOW, "week", "--file", weird, "--out", os.path.join(TMP, "x.pdf"))
check("flow: parentheses, quotes, accents and long titles don't break the PDF",
      code == 0 and is_pdf(os.path.join(TMP, "x.pdf")) and "1 item," in o, o)

for name, data, cmd in [
    ("bad kind", {"start": "2026-11-02", "items": [{"date": "2026-11-03", "kind": "party", "title": "x"}]}, "week"),
    ("bad date", {"start": "Monday", "items": []}, "week"),
    ("missing title", {"start": "2026-11-02", "items": [{"date": "2026-11-03"}]}, "week"),
    ("no steps", {"title": "x", "steps": []}, "steps"),
    ("step without text", {"steps": [{"when": "Mon"}]}, "steps")]:
    f = os.path.join(TMP, name.replace(" ", "_") + ".json")
    json.dump(data, open(f, "w"))
    code, o = run(FLOW, cmd, "--file", f, "--out", os.path.join(TMP, "bad.pdf"))
    check("flow: %s -> exit 3" % name, code == 3, o)
code, o = run(FLOW, "week")
check("flow: no input -> exit 3", code == 3, o)

code, o = run(CHECK)
check("selfcheck: all eleven Skills pass", code == 0 and o.count("OK   ") == 11 and "all passed" in o, o)

print("\n%d failure(s)" % fails)
sys.exit(1 if fails else 0)
