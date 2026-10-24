#!/usr/bin/env python3
"""Professor Radar: a running log of the student's interactions with each professor.

Standard library only. State lives in ~/.config/professor-radar/log.json.

  log    add an interaction (office hours, a strong grade, an email, a project, research)
  rank   who knows the student best, weighted by kind of interaction and how recent it is
  brag   the facts for a recommendation brag sheet, as Markdown
  list   everyone in the log
  remove delete a wrong entry

Exit codes: 0 ok, 2 professor or entry not found / log empty, 3 bad input.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_FILE = os.path.join(SKILL_DIR, "assets", "sample_log.json")
KINDS = {"research": 4, "oh": 3, "project": 3, "grade": 2, "email": 1, "class": 1, "note": 0.5}
KIND_LABEL = {"research": "research", "oh": "office hours", "project": "project", "grade": "grade",
              "email": "email", "class": "in class", "note": "note"}
HALF_LIFE_DAYS = 180


class UserError(Exception):
    def __init__(self, message, code=3):
        super().__init__(message)
        self.code = code


def log_path():
    base = os.environ.get("PROFESSOR_RADAR_HOME") or os.path.join(
        os.path.expanduser("~"), ".config", "professor-radar")
    return os.path.join(base, "log.json")


def load(sample=False):
    path = SAMPLE_FILE if sample else log_path()
    if not os.path.exists(path):
        return {"professors": {}, "next_id": 1}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(data):
    path = log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(path + ".tmp", path)


def parse_when(text, ref=None):
    raw = text.strip().replace("Z", "+00:00")
    if " " in raw and "T" not in raw:
        raw = raw.replace(" ", "T", 1)
    try:
        d = datetime.fromisoformat(raw)
    except ValueError:
        raise UserError("Can't read the date '%s'. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM-07:00." % text)
    if d.tzinfo is None:
        tz = ref.tzinfo if ref is not None and ref.tzinfo else datetime.now().astimezone().tzinfo
        d = d.replace(tzinfo=tz)
    return d


def now_from(arg):
    return parse_when(arg) if arg else datetime.now().astimezone()


def key_of(name):
    cleaned = re.sub(r"^(dr|prof|professor|mr|mrs|ms)\.?\s+", "", name.strip().lower())
    return re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")


def term_of(d):
    season = "Spring" if d.month <= 5 else "Summer" if d.month <= 7 else "Fall"
    return "%s %d" % (season, d.year)


def fmt_day(d):
    return d.strftime("%b ") + str(d.day) + d.strftime(", %Y")


def find_prof(data, name):
    if not data["professors"]:
        raise UserError("No professors logged yet.", 2)
    k = key_of(name)
    if k in data["professors"]:
        return data["professors"][k]
    hits = [p for pk, p in data["professors"].items() if k and (k in pk or pk in k)]
    if len(hits) == 1:
        return hits[0]
    names = ", ".join(p["name"] for p in data["professors"].values())
    raise UserError("No professor matching '%s'. Logged: %s" % (name, names), 2)


def cmd_log(args):
    data = load()
    now = now_from(args.now)
    when = parse_when(args.at, now) if args.at else now
    if args.kind not in KINDS:
        raise UserError("Kind must be one of: " + ", ".join(KINDS))
    if not args.text.strip():
        raise UserError("Say what happened with --text.")
    k = key_of(args.prof)
    if not k:
        raise UserError("Give the professor's name with --prof.")
    prof = data["professors"].get(k)
    if prof is None:
        prof = {"name": args.prof.strip(), "courses": [], "entries": []}
        data["professors"][k] = prof
    if args.course and args.course.strip() not in prof["courses"]:
        prof["courses"].append(args.course.strip())
    entry = {"id": data["next_id"], "kind": args.kind, "text": args.text.strip(),
             "course": (args.course or "").strip(), "at": when.isoformat(timespec="minutes")}
    prof["entries"].append(entry)
    data["next_id"] += 1
    save(data)
    n = len(prof["entries"])
    print("Logged #%d for %s: %s, %s. That's %d interaction%s with them." % (
        entry["id"], prof["name"], KIND_LABEL[args.kind], entry["text"], n, "" if n == 1 else "s"))


def score(prof, now):
    total = 0.0
    for e in prof["entries"]:
        age = max(0, (now - parse_when(e["at"])).days)
        total += KINDS.get(e["kind"], 0.5) * 0.5 ** (age / HALF_LIFE_DAYS)
    return total


def counts(prof):
    c = {}
    for e in prof["entries"]:
        c[e["kind"]] = c.get(e["kind"], 0) + 1
    return c


def cmd_rank(args):
    data = load(args.sample)
    if not data["professors"]:
        print("No professors logged yet.")
        return 2
    now = now_from(args.now)
    ranked = sorted(data["professors"].values(), key=lambda p: -score(p, now))
    for i, p in enumerate(ranked[:args.top], 1):
        c = counts(p)
        parts = ["%d %s" % (c[k], KIND_LABEL[k]) for k in KINDS if c.get(k)]
        last = max(parse_when(e["at"]) for e in p["entries"])
        print("%d. %s (%s): %s; last contact %s; score %.1f" % (
            i, p["name"], ", ".join(p["courses"]) or "no course", ", ".join(parts), fmt_day(last), score(p, now)))
    return 0


def cmd_brag(args):
    data = load(args.sample)
    prof = find_prof(data, args.prof)
    student = args.student or "The student"
    entries = sorted(prof["entries"], key=lambda e: e["at"])
    terms = []
    for e in entries:
        t = (e["course"] or "", term_of(parse_when(e["at"])))
        if t[0] and t not in terms:
            terms.append(t)
    out = ["# Brag sheet for %s" % prof["name"], ""]
    out.append("From: %s" % student)
    if args.purpose:
        out.append("For: %s" % args.purpose)
    if args.deadline:
        out.append("Letter due: %s" % fmt_day(parse_when(args.deadline)))
    out.append("")
    out.append("## How you know me")
    out.append("")
    if terms:
        for course, term in terms:
            out.append("- %s, %s" % (course, term))
    c = counts(prof)
    summary = ", ".join("%d %s" % (c[k], KIND_LABEL[k]) for k in KINDS if c.get(k))
    out.append("- Our interactions: %s" % summary)
    out.append("")
    sections = [("Office hours and conversations", ("oh", "email", "class")),
                ("Work and results", ("grade", "project")),
                ("Research", ("research",)),
                ("Other", ("note",))]
    for title, kinds in sections:
        rows = [e for e in entries if e["kind"] in kinds]
        if not rows:
            continue
        out.append("## " + title)
        out.append("")
        for e in rows:
            course = (" (%s)" % e["course"]) if e["course"] else ""
            out.append("- %s%s: %s" % (fmt_day(parse_when(e["at"])), course, e["text"]))
        out.append("")
    print("\n".join(out).rstrip())
    return 0


def cmd_list(args):
    data = load(args.sample)
    if not data["professors"]:
        print("No professors logged yet.")
        return 2
    for p in sorted(data["professors"].values(), key=lambda p: p["name"]):
        print("- %s (%s): %d entries" % (p["name"], ", ".join(p["courses"]) or "no course", len(p["entries"])))
    return 0


def cmd_remove(args):
    data = load()
    for p in data["professors"].values():
        for e in p["entries"]:
            if e["id"] == args.id:
                p["entries"].remove(e)
                if not p["entries"]:
                    data["professors"] = {k: v for k, v in data["professors"].items() if v is not p}
                save(data)
                print("Removed #%d (%s): %s" % (args.id, p["name"], e["text"]))
                return 0
    raise UserError("No entry #%s." % args.id, 2)


def main(argv=None):
    p = argparse.ArgumentParser(prog="professors.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("log")
    sp.add_argument("--prof", required=True)
    sp.add_argument("--course")
    sp.add_argument("--kind", required=True, choices=list(KINDS))
    sp.add_argument("--text", required=True)
    sp.add_argument("--at")
    sp.add_argument("--now")
    sp.set_defaults(func=cmd_log)

    sp = sub.add_parser("rank")
    sp.add_argument("--top", type=int, default=3)
    sp.add_argument("--now")
    sp.add_argument("--sample", action="store_true")
    sp.set_defaults(func=cmd_rank)

    sp = sub.add_parser("brag")
    sp.add_argument("--prof", required=True)
    sp.add_argument("--student")
    sp.add_argument("--purpose")
    sp.add_argument("--deadline")
    sp.add_argument("--sample", action="store_true")
    sp.set_defaults(func=cmd_brag)

    sp = sub.add_parser("list")
    sp.add_argument("--sample", action="store_true")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("remove")
    sp.add_argument("--id", type=int, required=True)
    sp.set_defaults(func=cmd_remove)

    args = p.parse_args(argv)
    try:
        return args.func(args) or 0
    except UserError as e:
        print(str(e))
        return e.code


if __name__ == "__main__":
    sys.exit(main())
