#!/usr/bin/env python3
"""Campus Radar health check: confirms every Skill is installed and every script works.

Standard library only. Runs each Skill's script in its --sample mode (nothing saved,
no network) and checks the output, then reports one line per Skill.

  python3 scripts/selfcheck.py
  ED_API_TOKEN="$ED_API_TOKEN" python3 scripts/selfcheck.py --live-ed   (also checks the Ed token)

Exit codes: 0 everything passed, 1 something failed (the report says what and how to fix it).
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_ROOT = os.path.dirname(HERE)
NOW = "2026-10-24T13:00-07:00"

SKILLS = [
    "slide-radar", "exam-radar", "club-radar", "group-project-receipts", "grade-radar",
    "professor-radar", "discussion-radar", "inbox-radar", "catch-me-up", "sunday-radar", "radar-autopilot",
]

SCRIPT_CHECKS = {
    "group-project-receipts": [(["scripts/receipts.py", "status", "--sample", "--now", NOW], "Overdue promises",
                                "group log")],
    "exam-radar": [(["scripts/practice.py", "q-due", "--sample", "--now", NOW], "Answer key", "practice tracker")],
    "grade-radar": [(["scripts/grade_math.py", "need", "--sample"], "current grade 82.7%", "grade math")],
    "professor-radar": [(["scripts/professors.py", "rank", "--sample", "--now", NOW], "1. Prof. Lee", "professor log")],
    "discussion-radar": [(["scripts/ed.py", "search", "--sample", "--course", "CSE 310", "--query",
                           "can we assume the graph is connected"], "#502", "Ed search")],
    "sunday-radar": [(["scripts/flow.py", "week", "--sample", "--out", "{tmp}/week.pdf"], "Week flowchart",
                      "week flowchart"),
                     (["scripts/flow.py", "steps", "--sample", "--out", "{tmp}/steps.pdf"], "Steps flowchart",
                      "steps flowchart")],
}


def skill_name(folder):
    try:
        with open(os.path.join(folder, "SKILL.md"), encoding="utf-8") as fh:
            head = fh.read(2000)
    except OSError:
        return None
    m = re.search(r"^name:\s*(\S+)", head, re.M)
    return m.group(1) if m else ""


def run(folder, argv, tmp, env):
    argv = [a.replace("{tmp}", tmp) for a in argv]
    try:
        p = subprocess.run([sys.executable, "-I"] + argv, cwd=folder, capture_output=True, text=True,
                           timeout=60, env=env)
    except subprocess.TimeoutExpired:
        return 99, "timed out"
    return p.returncode, (p.stdout + p.stderr).strip()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="selfcheck.py")
    ap.add_argument("--live-ed", dest="live_ed", action="store_true", help="also call Ed with the saved token")
    args = ap.parse_args(argv)

    tmp = tempfile.mkdtemp(prefix="radar-check-")
    env = dict(os.environ, HOME=tmp)  # sample runs can't touch the student's real saved state
    env.pop("ED_API_TOKEN", None)
    lines, failures = [], 0

    for name in SKILLS:
        folder = os.path.join(SKILLS_ROOT, name)
        found = skill_name(folder)
        if found is None:
            lines.append("FAIL %s: not installed. Text the Campus Radar repo link to Cubbie again." % name)
            failures += 1
            continue
        if found != name:
            lines.append("FAIL %s: SKILL.md name is '%s'. Reinstall from the repo." % (name, found))
            failures += 1
            continue
        problems, passed = [], []
        for argv_, expect, label in SCRIPT_CHECKS.get(name, []):
            code, out = run(folder, argv_, tmp, env)
            ok = code == 0 and expect in out
            if ok and argv_[1] in ("week", "steps"):
                pdf = argv_[-1].replace("{tmp}", tmp)
                ok = os.path.isfile(pdf) and open(pdf, "rb").read(5) == b"%PDF-"
            if ok:
                passed.append(label)
            else:
                first = out.splitlines()[0] if out else "no output"
                problems.append("%s failed (exit %s: %s)" % (label, code, first[:120]))
        if problems:
            failures += 1
            lines.append("FAIL %s: %s. Reinstall from the repo; if it still fails, tell the Skill's author."
                         % (name, "; ".join(problems)))
        else:
            lines.append("OK   %s%s" % (name, (": " + " and ".join(passed) + (" works" if len(passed) == 1 else " work"))
                                        if passed else ": instructions found"))

    if args.live_ed:
        token = os.environ.get("ED_API_TOKEN", "")
        folder = os.path.join(SKILLS_ROOT, "discussion-radar")
        if not token:
            lines.append("WARN Ed: no token saved. Discussion Radar's Ed features stay off until the student saves "
                         "ED_API_TOKEN (created at https://edstem.org/us/settings/api-tokens).")
        elif os.path.isdir(folder):
            live_env = dict(os.environ)
            code, out = run(folder, ["scripts/ed.py", "courses"], tmp, live_env)
            if code == 0:
                n = len([l for l in out.splitlines() if "(id " in l])
                lines.append("OK   Ed: token works, %d active course%s" % (n, "" if n == 1 else "s"))
            elif code == 5:
                failures += 1
                lines.append("FAIL Ed: token rejected. Create a new one and save it through the secure page.")
            elif code == 2:
                lines.append("WARN Ed: token works but no active Ed courses on this account.")
            else:
                lines.append("WARN Ed: couldn't reach Ed right now (%s)." % ((out.splitlines()[0][:100].rstrip(".")) if out else code))

    lines.append("")
    lines.append("Scripts: %s" % ("all passed" if not failures else "%d problem%s" % (failures, "" if failures == 1 else "s")))
    print("\n".join(lines))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
