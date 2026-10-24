"""End-to-end tests for Exam Radar, Grade Radar and Professor Radar scripts (throwaway HOME)."""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills")
HOME = tempfile.mkdtemp()
ENV = {k: v for k, v in os.environ.items() if not k.endswith("_HOME") or k == "HOME"}
ENV["HOME"] = HOME
fails = 0


def run(script, *args):
    p = subprocess.run([sys.executable, "-I", os.path.join(ROOT, script), *args],
                       capture_output=True, text=True, env=ENV)
    return p.returncode, (p.stdout + p.stderr).strip()


def check(name, cond, detail=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  -> " + detail))
    fails += 0 if cond else 1


# ---------- exam radar ----------
E = "exam-radar/scripts/practice.py"
N0 = "2026-10-20T19:00-07:00"
code, out = run(E, "exams", "--now", N0)
check("exam: empty -> exit 2", code == 2, out)
code, out = run(E, "exam-add", "--course", "CSE 310", "--name", "Midterm 2", "--date", "2026-11-03T10:30-07:00",
                "--topics", "Heaps; Hash tables", "--now", N0)
check("exam: add", code == 0 and "14 days away" in out, out)
code, out = run(E, "exam-add", "--course", "CSE 310", "--name", "midterm 2", "--date", "2026-11-04", "--now", N0)
check("exam: same name updates date", code == 0 and "Updated #1" in out, out)
code, out = run(E, "exam-add", "--name", "Old", "--date", "2026-10-01", "--now", N0)
check("exam: past date rejected", code == 3, out)
code, out = run(E, "countdown", "--now", "2026-10-28T08:00-07:00")
check("exam: 1-week countdown", "in 1 week" in out, out)
code, out = run(E, "countdown", "--now", "2026-10-29T08:00-07:00")
check("exam: no milestone day", "No countdown" in out, out)
code, out = run(E, "countdown", "--now", "2026-11-03T08:00-07:00")
check("exam: tomorrow", "tomorrow" in out, out)

qfile = os.path.join(HOME, "q.json")
json.dump([{"question": "BFS uses which structure?", "answer": "queue", "topic": "Graphs", "source": "L16 s6"},
           {"question": "Heap insert cost?", "answer": "O(log n)", "topic": "Heaps"},
           {"question": "Heap insert cost??", "answer": "dup", "topic": "Heaps"},
           {"question": "Chaining search cost?", "answer": "O(1+a)", "topic": "Hash tables"},
           {"question": "Build-heap cost?", "answer": "O(n)", "topic": "Heaps"}], open(qfile, "w"))
code, out = run(E, "q-add", "--exam", "1", "--file", qfile, "--now", N0)
check("exam: q-add skips duplicate", code == 0 and "Added 4" in out and "1 duplicate" in out, out)
bad = os.path.join(HOME, "bad.json")
json.dump([{"question": "no answer"}], open(bad, "w"))
code, out = run(E, "q-add", "--exam", "1", "--file", bad, "--now", N0)
check("exam: question without answer rejected", code == 3, out)
code, out = run(E, "q-add", "--exam", "9", "--question", "x", "--answer", "y", "--now", N0)
check("exam: unknown exam -> 2", code == 2, out)

code, out = run(E, "q-due", "--n", "3", "--now", N0)
ids = [l.split()[0] for l in out.splitlines() if l.startswith("#")]
topics = [l.split(", ")[1] for l in out.splitlines() if l.startswith("#")]
check("exam: 3 due", len(ids) == 3, out)
check("exam: new questions spread across topics", len(set(topics)) == 3, str(topics))
check("exam: answer key labelled", "Answer key (don't show the student)" in out, out)
check("exam: asks for more", "NEED_MORE" in out, out)

code, out = run(E, "q-grade", "--id", "1", "--result", "wrong", "--now", N0)
check("exam: wrong -> tomorrow", "back tomorrow" in out, out)
code, out = run(E, "q-grade", "--id", "2", "--result", "right", "--now", N0)
check("exam: right -> next review", "next review Wed Oct 21" in out, out)
code, out = run(E, "q-due", "--n", "1", "--now", "2026-10-21T19:00-07:00")
check("exam: reviews come first", out.startswith("#1 ") or out.startswith("#2 "), out)
# walk q2 through all boxes to retirement
t = ["2026-10-21", "2026-10-23", "2026-10-27", "2026-11-03", "2026-11-04"]
for day in t:
    code, out = run(E, "q-grade", "--id", "2", "--result", "right", "--now", day + "T20:00-07:00")
check("exam: retires after last box", "retired" in out, out)
code, out = run(E, "stats", "--exam", "1")
check("exam: stats", "Overall:" in out and "1 retired" in out, out)
code, out = run(E, "q-due", "--now", "2026-11-10T08:00-07:00")
check("exam: past exams excluded", code == 2, out)

# ---------- grade radar ----------
G = "grade-radar/scripts/grade_math.py"
code, out = run(G, "need", "--sample")
check("grade: sample current 82.7 B-", "82.7% (B-)" in out, out)
check("grade: B needs 84 (83.67 rounded up)", "- B: 84%" in out, out)
check("grade: A out of reach", "A: out of reach" in out, out)
code, out = run(G, "need", "--sample", "--final-score", "90")
check("grade: what-if", "84.9% overall (B)" in out, out)

pts = os.path.join(HOME, "pts.json")
json.dump({"course": "BIO 181", "scheme": "points", "groups": [
    {"name": "Labs", "items": [{"name": "L1", "earned": 45, "possible": 50}, {"name": "L2", "earned": 40, "possible": 50}]},
    {"name": "Final", "final": True, "items": [{"name": "Final", "earned": None, "possible": 100}]}]}, open(pts, "w"))
code, out = run(G, "need", "--file", pts)
# current 85/100 = 85%. For A (93): (0.93*200 - 85)/100 = 101 -> out of reach; A- (90): 95; B+ 87: 89
check("grade: points current", "85.0% (B)" in out, out)
check("grade: points A- needs 95", "- A-: 95%" in out, out)

locked = os.path.join(HOME, "locked.json")
json.dump({"scheme": "weighted", "groups": [
    {"name": "HW", "weight": 90, "items": [{"name": "a", "earned": 100, "possible": 100}]},
    {"name": "Final", "weight": 10, "final": True, "items": [{"name": "f", "possible": 100}]}]}, open(locked, "w"))
code, out = run(G, "need", "--file", locked)
check("grade: locked in", "already locked in" in out, out)

for name, data in [("noweight", {"groups": [{"name": "HW", "items": []}]}),
                   ("twofinals", {"groups": [{"name": "a", "weight": 50, "final": True, "items": []},
                                             {"name": "b", "weight": 50, "final": True, "items": []}]}),
                   ("nograded", {"groups": [{"name": "a", "weight": 100, "items": [{"name": "x", "possible": 10}]}]})]:
    f = os.path.join(HOME, name + ".json")
    json.dump(data, open(f, "w"))
    code, out = run(G, "need", "--file", f)
    check("grade: bad file %s -> 3" % name, code == 3, out)
code, out = run(G, "need", "--file", "/nope.json")
check("grade: missing file -> 3", code == 3, out)

# ---------- professor radar ----------
P = "professor-radar/scripts/professors.py"
code, out = run(P, "rank", "--now", N0)
check("prof: empty -> 2", code == 2, out)
code, out = run(P, "log", "--prof", "Prof. Lee", "--course", "CSE 310", "--kind", "oh", "--text", "graph project",
                "--now", N0)
check("prof: log", code == 0 and "1 interaction with them" in out, out)
code, out = run(P, "log", "--prof", "Dr Lee", "--course", "CSE 310", "--kind", "grade", "--text", "94 on midterm",
                "--now", N0)
check("prof: title-insensitive match", "2 interactions" in out, out)
run(P, "log", "--prof", "Dr. Patel", "--course", "CSE 360", "--kind", "email", "--text", "scope question",
    "--now", N0)
run(P, "log", "--prof", "Prof. Chen", "--course", "CSE 205", "--kind", "research", "--text", "lab work",
    "--at", "2025-01-10", "--now", N0)
code, out = run(P, "rank", "--now", N0)
lines = out.splitlines()
check("prof: Lee ranked first (recent beats old research)", lines[0].startswith("1. Prof. Lee"), out)
code, out = run(P, "brag", "--prof", "lee", "--student", "Amrish", "--purpose", "research internship",
                "--deadline", "2026-12-01")
check("prof: brag sheet", "CSE 310, Fall 2026" in out and "94 on midterm" in out and "Dec 1, 2026" in out, out)
code, out = run(P, "brag", "--prof", "nobody")
check("prof: unknown prof -> 2", code == 2, out)
code, out = run(P, "remove", "--id", "3")
check("prof: remove last entry drops professor", code == 0, out)
code, out = run(P, "list")
check("prof: Patel gone after removal", "Patel" not in out and "Lee" in out, out)
check("prof: state under HOME", os.path.isfile(os.path.join(HOME, ".config", "professor-radar", "log.json")))

# sample modes never write
before = set(os.listdir(os.path.join(HOME, ".config")))
run(E, "q-due", "--sample", "--now", "2026-10-24T13:00-07:00")
run(P, "rank", "--sample")
check("sample modes write nothing new", set(os.listdir(os.path.join(HOME, ".config"))) == before)

print("\n%d failure(s)" % fails)
sys.exit(1 if fails else 0)
