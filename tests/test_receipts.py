"""End-to-end tests for receipts.py, run with a throwaway HOME."""
import json
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "group-project-receipts", "scripts", "receipts.py")
HOME = tempfile.mkdtemp()
ENV = dict(os.environ, HOME=HOME)
ENV.pop("RECEIPTS_HOME", None)
STATE = os.path.join(HOME, ".config", "group-project-receipts")
fails = 0


def run(*args):
    p = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, env=ENV)
    return p.returncode, p.stdout.strip() + p.stderr.strip()


def check(name, cond, detail=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  -> " + detail))
    if not cond:
        fails += 1


N = "--now"
T0 = "2026-10-13T19:00-07:00"

# sample mode leaves state alone
code, out = run("status", "--sample", N, "2026-10-24T13:00-07:00")
check("sample status works", code == 0 and "Jake" in out, out)
check("sample writes nothing", not os.path.exists(STATE))

# no projects yet
code, out = run("status", N, T0)
check("no projects -> exit 2", code == 2, out)

code, out = run("new", "--project", "CSE 310 App", "--course", "CSE 310",
                "--members", "Priya, Jake,Sam", "--due", "2026-11-06", "--peer-eval", "2026-11-09", N, T0)
check("new project", code == 0 and "Priya, Jake, Sam" in out, out)
check("state under HOME", os.path.isfile(os.path.join(STATE, "projects", "cse-310-app.json")))

code, out = run("new", "--project", "cse 310 app", N, T0)
check("duplicate -> exit 4", code == 4, out)
code, out = run("new", "--project", "X", "--members", "me,Bo", N, T0)
check("me in members rejected", code == 3, out)

# logging (project omitted: only one active)
code, out = run("log", "--who", "me", "--kind", "did", "--text", "built template", "--hours", "2",
                N, "2026-10-14T22:00-07:00")
check("log mine", code == 0 and "#1" in out, out)
code, out = run("log", "--who", "jake", "--kind", "promised", "--text", "intro slides", "--by", "2026-10-20",
                N, "2026-10-14T22:05-07:00")
check("promise, case-insensitive name", code == 0 and "Follow-up due: Tue Oct 20" in out, out)
code, out = run("log", "--who", "Pri", "--kind", "promised", "--text", "research", "--by", "2026-10-19",
                N, "2026-10-14T22:06-07:00")
check("prefix name match", code == 0 and "Priya" in out, out)
code, out = run("log", "--who", "Bob", "--kind", "did", "--text", "x", N, T0)
check("unknown teammate -> exit 3", code == 3 and "members --add" in out, out)
code, out = run("log", "--who", "me", "--kind", "promised", "--text", "x", N, T0)
check("promise needs --by", code == 3, out)
code, out = run("log", "--who", "me", "--kind", "did", "--text", "x", "--by", "2026-10-20", N, T0)
check("--by only with promised", code == 3, out)
code, out = run("log", "--who", "me", "--kind", "did", "--text", "x", "--at", "2026-12-01", N, T0)
check("future --at rejected", code == 3, out)
code, out = run("log", "--who", "me", "--kind", "did", "--text", "x", "--at", "Tuesday", N, T0)
check("bad date -> exit 3", code == 3, out)
code, out = run("log", "--who", "me", "--kind", "did", "--text", "x", "--hours", "30", N, T0)
check("silly hours rejected", code == 3, out)

# backfilled entry gets flagged
code, out = run("log", "--who", "Sam", "--kind", "missed", "--text", "skipped kickoff",
                "--at", "2026-10-13T18:00-07:00", N, "2026-10-17T10:00-07:00")
check("backfill note", code == 0 and "logged 4 days after" in out, out)

# evidence
shot = os.path.join(HOME, "shot.png")
open(shot, "wb").write(b"\x89PNG fake")
code, out = run("log", "--who", "me", "--kind", "did", "--text", "slides 5-9", "--evidence", shot,
                "--evidence-desc", "version history shows slides 5-9", N, "2026-10-19T23:00-07:00")
ev_dir = os.path.join(STATE, "evidence", "cse-310-app")
check("evidence copied", code == 0 and os.path.isdir(ev_dir) and len(os.listdir(ev_dir)) == 1, out)
code, out = run("log", "--who", "me", "--kind", "did", "--text", "x", "--evidence", "/nope.png", N, T0)
check("missing evidence -> exit 3", code == 3, out)

# promises
code, out = run("kept", "--id", "3", N, "2026-10-18T16:00-07:00")
check("kept on time", code == 0 and "on time" in out, out)
code, out = run("kept", "--id", "1", N, T0)
check("kept on non-promise -> exit 3", code == 3, out)
code, out = run("kept", "--id", "99", N, T0)
check("unknown id -> exit 3", code == 3, out)

# status
code, out = run("status", N, "2026-10-24T13:00-07:00")
check("overdue promise shown", "Overdue" in out and "#2 Jake" in out, out)
check("quiet teammates shown", "Jake (nothing logged yet)" in out and "Sam" in out, out)
check("kept promise counts as activity", "Priya (last active Sun Oct 18)" in out, out)

# broke + summary
code, out = run("broke", "--id", "2", "--note", "said he forgot", N, "2026-10-24T13:05-07:00")
check("broke", code == 0, out)
code, out = run("summary", "--student", "Amrish", N, "2026-10-24T13:10-07:00")
check("summary table", "| Amrish | 2 |" in out and "| Jake | 0 |" in out, out)
check("summary commitments", "Status: not done. Note: said he forgot" in out, out)
check("summary logged-later flag", "[logged later]" in out, out)
check("summary evidence", "version history shows slides 5-9" in out, out)
check("summary under 8000 chars", len(out) < 8000, str(len(out)))

# remove, members, multi-project, archive
code, out = run("remove", "--id", "1")
check("remove", code == 0 and "built template" in out, out)
code, out = run("members", "--add", "Lena", "--remove", "Sam")
check("members change", code == 0 and "Lena" in out and "Sam" not in out.split("Changed")[0], out)
run("new", "--project", "BIO Lab Report", "--members", "Ana", N, T0)
code, out = run("status", N, T0)
check("two projects, none named -> exit 2", code == 2 and "BIO Lab Report" in out, out)
code, out = run("status", "--project", "bio", N, T0)
check("loose project match", code == 0 and "BIO Lab Report" in out, out)
code, out = run("archive", "--project", "BIO Lab Report")
check("archive", code == 0, out)
code, out = run("status", N, T0)
check("archived ignored for default", code == 0 and "CSE 310 App" in out, out)
code, out = run("list")
check("list", "(archived)" in out and "CSE 310 App" in out, out)

data = json.load(open(os.path.join(STATE, "projects", "cse-310-app.json")))
check("ids keep increasing", data["next_id"] == 6, str(data["next_id"]))

print("\n%d failure(s)" % fails)
sys.exit(1 if fails else 0)
