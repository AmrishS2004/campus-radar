#!/usr/bin/env python3
"""Receipts: a dated contribution log for one student's group projects.

Standard library only. State lives under ~/.config/group-project-receipts/ so it
survives restarts and Skill updates. Every command prints short plain text that
Cubbie can relay or turn into a document.

Exit codes:
  0  ok
  2  project not found
  3  bad input (unknown teammate, bad date, missing field, unknown entry id)
  4  a project with that name already exists
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_FILE = os.path.join(SKILL_DIR, "assets", "sample_project.json")

KINDS = ("did", "meeting", "message", "promised", "missed", "note")
ACTIVE_KINDS = ("did", "meeting", "message")  # things that count as showing up
KIND_LABEL = {"did": "work", "meeting": "meeting", "message": "message",
              "promised": "promised", "missed": "missed", "note": "note"}


class UserError(Exception):
    def __init__(self, message, code=3):
        super().__init__(message)
        self.code = code


# ---------- paths and storage ----------

def state_dir():
    base = os.environ.get("RECEIPTS_HOME") or os.path.join(
        os.path.expanduser("~"), ".config", "group-project-receipts")
    return base


def projects_dir():
    return os.path.join(state_dir(), "projects")


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "project"


def project_path(slug):
    return os.path.join(projects_dir(), slug + ".json")


def load_all():
    folder = projects_dir()
    if not os.path.isdir(folder):
        return []
    out = []
    for fname in sorted(os.listdir(folder)):
        if fname.endswith(".json"):
            with open(os.path.join(folder, fname), encoding="utf-8") as fh:
                out.append(json.load(fh))
    return out


def find_project(name, sample=False):
    if sample:
        with open(SAMPLE_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    projects = load_all()
    if not projects:
        raise UserError("No projects yet. Start one with the new command.", 2)
    if name is None:
        active = [p for p in projects if not p.get("archived")]
        if len(active) == 1:
            return active[0]
        names = ", ".join(p["name"] for p in active) or "none active"
        raise UserError("Which project? Active projects: " + names, 2)
    wanted = slugify(name)
    for p in projects:
        if p["slug"] == wanted or p["name"].lower() == name.lower():
            return p
    # loose match: every word of the query appears in the name
    words = [w for w in re.split(r"\W+", name.lower()) if w]
    hits = [p for p in projects if all(w in p["name"].lower() for w in words)]
    if len(hits) == 1:
        return hits[0]
    names = ", ".join(p["name"] for p in projects)
    raise UserError("No project called '%s'. Projects: %s" % (name, names), 2)


def save(project, sample=False):
    if sample:
        return  # sample runs never touch the student's saved state
    os.makedirs(projects_dir(), exist_ok=True)
    path = project_path(project["slug"])
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(project, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ---------- time ----------

def parse_when(text, ref=None, end_of_day=False):
    """Parse an ISO date or datetime. Naive values take ref's offset."""
    if text is None:
        return None
    raw = text.strip().replace("Z", "+00:00")
    if " " in raw and "T" not in raw:
        raw = raw.replace(" ", "T", 1)
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            d = datetime.fromisoformat(raw)
            d = d.replace(hour=23, minute=59) if end_of_day else d
        else:
            d = datetime.fromisoformat(raw)
    except ValueError:
        raise UserError("Can't read the date '%s'. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM-07:00." % text)
    if d.tzinfo is None:
        tz = ref.tzinfo if ref is not None and ref.tzinfo else datetime.now().astimezone().tzinfo
        d = d.replace(tzinfo=tz)
    return d


def now_from(arg):
    if arg:
        return parse_when(arg)
    return datetime.now().astimezone()


def iso(d):
    return d.isoformat(timespec="minutes")


def fmt_day(d):
    return d.strftime("%a %b ") + str(d.day)


def fmt_dt(d):
    hour = d.strftime("%I").lstrip("0") or "12"
    return "%s, %s:%s %s" % (fmt_day(d), hour, d.strftime("%M"), d.strftime("%p").lower())


def days_between(a, b):
    return (b.date() - a.date()).days


# ---------- people ----------

def resolve_who(project, who):
    if who is None:
        raise UserError("Say who this entry is about: me or a teammate's name.")
    w = who.strip()
    if w.lower() in ("me", "i", "myself", "self", "student"):
        return "me"
    for m in project["members"]:
        if m.lower() == w.lower():
            return m
    starts = [m for m in project["members"] if m.lower().startswith(w.lower())]
    if len(starts) == 1:
        return starts[0]
    raise UserError("'%s' isn't on the %s team (%s). Add them with: members --add \"%s\""
                    % (who, project["name"], ", ".join(project["members"]) or "no teammates yet", who))


def label(who):
    return "You" if who == "me" else who


# ---------- commands ----------

def cmd_new(args):
    if not args.project:
        raise UserError("Give the project a name with --project.")
    slug = slugify(args.project)
    if os.path.exists(project_path(slug)):
        raise UserError("A project called '%s' already exists." % args.project, 4)
    now = now_from(args.now)
    members = [m.strip() for m in (args.members or "").split(",") if m.strip()]
    if any(m.lower() == "me" for m in members):
        raise UserError("Leave the student out of --members; they are always 'me'.")
    project = {
        "name": args.project.strip(),
        "slug": slug,
        "course": (args.course or "").strip(),
        "members": members,
        "due": iso(parse_when(args.due, now, end_of_day=True)) if args.due else None,
        "peer_eval": iso(parse_when(args.peer_eval, now, end_of_day=True)) if args.peer_eval else None,
        "created": iso(now),
        "archived": False,
        "next_id": 1,
        "entries": [],
    }
    save(project)
    lines = ["Started receipts for %s." % project["name"]]
    if members:
        lines.append("Team: you, " + ", ".join(members))
    if project["due"]:
        lines.append("Due: " + fmt_dt(parse_when(project["due"])))
    if project["peer_eval"]:
        lines.append("Peer eval: " + fmt_dt(parse_when(project["peer_eval"])))
    print("\n".join(lines))


def cmd_members(args):
    project = find_project(args.project)
    changed = []
    for name in args.add or []:
        name = name.strip()
        if name and name.lower() not in [m.lower() for m in project["members"]] and name.lower() != "me":
            project["members"].append(name)
            changed.append("added " + name)
    for name in args.remove or []:
        before = len(project["members"])
        project["members"] = [m for m in project["members"] if m.lower() != name.strip().lower()]
        if len(project["members"]) < before:
            changed.append("removed " + name.strip())
    if args.due:
        project["due"] = iso(parse_when(args.due, now_from(args.now), end_of_day=True))
        changed.append("due date set")
    if args.peer_eval:
        project["peer_eval"] = iso(parse_when(args.peer_eval, now_from(args.now), end_of_day=True))
        changed.append("peer eval date set")
    save(project)
    print("%s team: you, %s" % (project["name"], ", ".join(project["members"]) or "(no teammates yet)"))
    if changed:
        print("Changed: " + ", ".join(changed))


def cmd_log(args):
    project = find_project(args.project)
    if args.kind not in KINDS:
        raise UserError("Kind must be one of: " + ", ".join(KINDS))
    if not args.text or not args.text.strip():
        raise UserError("Say what happened with --text.")
    now = now_from(args.now)
    when = parse_when(args.at, now) if args.at else now
    if when > now + timedelta(minutes=5):
        raise UserError("That time is in the future. Log things after they happen; use promised --by for plans.")
    who = resolve_who(project, args.who)
    entry = {
        "id": project["next_id"],
        "who": who,
        "kind": args.kind,
        "text": args.text.strip(),
        "at": iso(when),
        "recorded": iso(now),
    }
    if args.hours is not None:
        if args.hours <= 0 or args.hours > 24:
            raise UserError("Hours should be between 0 and 24 for one entry.")
        entry["hours"] = round(args.hours, 2)
    if args.kind == "promised":
        if not args.by:
            raise UserError("A promise needs a --by date.")
        entry["by"] = iso(parse_when(args.by, now, end_of_day=True))
        entry["status"] = "open"
    elif args.by:
        raise UserError("--by only goes with --kind promised.")
    if args.evidence:
        entry["evidence"] = store_evidence(project, args.evidence, entry["id"], when)
    if args.evidence_desc:
        entry["evidence_desc"] = args.evidence_desc.strip()
    project["entries"].append(entry)
    project["next_id"] += 1
    save(project)

    msg = "Logged #%d for %s: %s %s" % (entry["id"], project["name"], label(who), describe(entry))
    print(msg)
    if args.kind == "promised":
        print("Follow-up due: " + fmt_dt(parse_when(entry["by"])))
    late = days_between(when, now)
    if late >= 2:
        print("Note: logged %d days after it happened; the summary marks it as logged later." % late)


def store_evidence(project, path, entry_id, when):
    if not os.path.isfile(path):
        raise UserError("Can't find the evidence file '%s'." % path)
    folder = os.path.join(state_dir(), "evidence", project["slug"])
    os.makedirs(folder, exist_ok=True)
    ext = os.path.splitext(path)[1].lower() or ".bin"
    dest = os.path.join(folder, "%03d-%s%s" % (entry_id, when.strftime("%Y%m%d-%H%M"), ext))
    shutil.copy2(path, dest)
    return dest


def describe(entry):
    k = entry["kind"]
    t = entry["text"]
    if k == "did":
        return "did: " + t
    if k == "meeting":
        return "meeting: " + t
    if k == "message":
        return "message: " + t
    if k == "promised":
        return "promised: " + t
    if k == "missed":
        return "missed: " + t
    return "note: " + t


def cmd_kept(args):
    project = find_project(args.project)
    entry = get_entry(project, args.id)
    if entry["kind"] != "promised":
        raise UserError("#%d isn't a promise." % args.id)
    now = now_from(args.now)
    when = parse_when(args.at, now) if args.at else now
    entry["status"] = "kept"
    entry["closed"] = iso(when)
    if args.note:
        entry["close_note"] = args.note.strip()
    save(project)
    by = parse_when(entry["by"])
    timing = "on time" if when <= by else "%d day(s) late" % max(1, days_between(by, when))
    print("Marked #%d kept (%s): %s %s" % (entry["id"], timing, label(entry["who"]), entry["text"]))


def cmd_broke(args):
    project = find_project(args.project)
    entry = get_entry(project, args.id)
    if entry["kind"] != "promised":
        raise UserError("#%d isn't a promise." % args.id)
    now = now_from(args.now)
    entry["status"] = "not done"
    entry["closed"] = iso(now)
    if args.note:
        entry["close_note"] = args.note.strip()
    save(project)
    print("Marked #%d not done: %s %s" % (entry["id"], label(entry["who"]), entry["text"]))


def cmd_remove(args):
    project = find_project(args.project)
    entry = get_entry(project, args.id)
    project["entries"] = [e for e in project["entries"] if e["id"] != args.id]
    save(project)
    print("Removed #%d: %s %s" % (args.id, label(entry["who"]), describe(entry)))


def get_entry(project, entry_id):
    for e in project["entries"]:
        if e["id"] == entry_id:
            return e
    raise UserError("No entry #%s in %s." % (entry_id, project["name"]))


def cmd_archive(args):
    project = find_project(args.project)
    project["archived"] = not args.undo
    save(project)
    print(("Archived " if project["archived"] else "Reopened ") + project["name"])


def cmd_list(args):
    projects = [find_project(None, sample=True)] if args.sample else load_all()
    if not projects:
        print("No projects yet.")
        return
    for p in projects:
        state = " (archived)" if p.get("archived") else ""
        due = ""
        if p.get("due"):
            due = ", due " + fmt_day(parse_when(p["due"]))
        print("- %s%s: %d entries%s" % (p["name"], state, len(p["entries"]), due))


def last_active(project, who):
    times = []
    for e in project["entries"]:
        if e["who"] != who:
            continue
        if e["kind"] in ACTIVE_KINDS:
            times.append(parse_when(e["at"]))
        elif e["kind"] == "promised" and e.get("status") == "kept" and e.get("closed"):
            times.append(parse_when(e["closed"]))
    return max(times) if times else None


def compute_status(project, now, quiet_days):
    open_p, overdue = [], []
    for e in project["entries"]:
        if e["kind"] == "promised" and e.get("status") == "open":
            by = parse_when(e["by"])
            (overdue if by < now else open_p).append((by, e))
    open_p.sort(key=lambda x: x[0])
    overdue.sort(key=lambda x: x[0])
    created = parse_when(project["created"])
    quiet = []
    for m in project["members"]:
        last = last_active(project, m)
        since = last or created
        gap = days_between(since, now)
        if gap >= quiet_days:
            quiet.append((m, last, gap))
    return open_p, overdue, quiet


def cmd_status(args):
    project = find_project(args.project, sample=args.sample)
    now = now_from(args.now)
    open_p, overdue, quiet = compute_status(project, now, args.quiet_days)
    lines = [project["name"] + ((" (" + project["course"] + ")") if project.get("course") else "")]
    if project.get("due"):
        d = days_between(now, parse_when(project["due"]))
        lines.append("Due %s (%s)" % (fmt_day(parse_when(project["due"])), in_days(d)))
    if project.get("peer_eval"):
        d = days_between(now, parse_when(project["peer_eval"]))
        lines.append("Peer eval %s (%s)" % (fmt_day(parse_when(project["peer_eval"])), in_days(d)))
    if overdue:
        lines.append("Overdue promises:")
        for by, e in overdue:
            lines.append("- #%d %s: %s (was due %s)" % (e["id"], label(e["who"]), e["text"], fmt_day(by)))
    if open_p:
        lines.append("Open promises:")
        for by, e in open_p:
            lines.append("- #%d %s: %s (by %s)" % (e["id"], label(e["who"]), e["text"], fmt_day(by)))
    if quiet:
        lines.append("Quiet for %d+ days:" % args.quiet_days)
        for m, last, gap in quiet:
            when = ("last active " + fmt_day(last)) if last else "nothing logged yet"
            lines.append("- %s (%s)" % (m, when))
    mine = [e for e in project["entries"] if e["who"] == "me" and e["kind"] == "did"]
    lines.append("Your logged contributions: %d" % len(mine))
    if not overdue and not quiet:
        lines.append("Nothing needs a nudge right now.")
    print("\n".join(lines))


def in_days(d):
    if d == 0:
        return "today"
    if d == 1:
        return "tomorrow"
    if d < 0:
        return "%d days ago" % -d
    return "in %d days" % d


def person_stats(project, who):
    es = [e for e in project["entries"] if e["who"] == who]
    stats = {k: 0 for k in KINDS}
    for e in es:
        stats[e["kind"]] += 1
    hours = sum(e.get("hours", 0) for e in es)
    promises = [e for e in es if e["kind"] == "promised"]
    kept = sum(1 for e in promises if e.get("status") == "kept")
    broke = sum(1 for e in promises if e.get("status") == "not done")
    return stats, hours, len(promises), kept, broke, last_active(project, who)


def cmd_summary(args):
    project = find_project(args.project, sample=args.sample)
    now = now_from(args.now)
    student = args.student or "the student"
    people = ["me"] + project["members"]
    entries = sorted(project["entries"], key=lambda e: e["at"])
    _, overdue, _ = compute_status(project, now, 9999)
    overdue_ids = {e["id"] for _, e in overdue}

    out = []
    title = project["name"] + (" (" + project["course"] + ")" if project.get("course") else "")
    out.append("# Contribution record: " + title)
    out.append("")
    out.append("Team: %s, %s" % (student, ", ".join(project["members"]) or "no teammates listed"))
    meta = ["Record started " + fmt_day(parse_when(project["created"]))]
    if project.get("due"):
        meta.append("project due " + fmt_day(parse_when(project["due"])))
    meta.append("generated " + fmt_dt(now))
    out.append("; ".join(meta) + ".")
    out.append("")
    out.append("This record comes from %s's own log, written down as the project went along. "
               "Entries logged two or more days after the event are marked \"logged later\". "
               "Hours are self-reported." % student)
    out.append("")

    out.append("## At a glance")
    out.append("")
    out.append("| Person | Work logged | Meetings | Messages | Promises kept | Not done | Hours | Last active |")
    out.append("|---|---|---|---|---|---|---|---|")
    for who in people:
        stats, hours, n_prom, kept, broke, last = person_stats(project, who)
        name = student if who == "me" else who
        open_late = sum(1 for e in project["entries"] if e["who"] == who and e["id"] in overdue_ids)
        not_done = broke + open_late
        out.append("| %s | %d | %d | %d | %d of %d | %d | %s | %s |" % (
            name, stats["did"], stats["meeting"], stats["message"], kept, n_prom, not_done,
            ("%g" % hours) if hours else "-", fmt_day(last) if last else "-"))
    out.append("")

    mine = [e for e in entries if e["who"] == "me" and e["kind"] == "did"]
    out.append("## What %s did" % student)
    out.append("")
    if mine:
        for e in mine:
            out.append("- " + entry_line(e, include_who=False))
    else:
        out.append("- Nothing logged yet.")
    out.append("")

    promises = [e for e in entries if e["kind"] == "promised"]
    if promises:
        out.append("## Commitments")
        out.append("")
        for e in promises:
            by = parse_when(e["by"])
            status = e.get("status", "open")
            if status == "kept":
                closed = parse_when(e["closed"])
                status = "kept " + fmt_day(closed) + (
                    "" if closed <= by else " (%d day(s) late)" % max(1, days_between(by, closed)))
            elif status == "open" and e["id"] in overdue_ids:
                status = "not done yet, past due"
            elif status == "not done":
                status = "not done"
            note = (" Note: " + e["close_note"]) if e.get("close_note") else ""
            out.append("- %s promised on %s: %s (by %s). Status: %s.%s" % (
                name_of(e["who"], student), fmt_day(parse_when(e["at"])), e["text"], fmt_day(by), status, note))
        out.append("")

    out.append("## Timeline")
    out.append("")
    if entries:
        for e in entries:
            out.append("- " + entry_line(e, include_who=True, student=student))
    else:
        out.append("- No entries yet.")
    out.append("")

    ev = [e for e in entries if e.get("evidence") or e.get("evidence_desc")]
    if ev:
        out.append("## Evidence on file")
        out.append("")
        for e in ev:
            desc = e.get("evidence_desc") or os.path.basename(e.get("evidence", ""))
            out.append("- #%d (%s): %s" % (e["id"], fmt_day(parse_when(e["at"])), desc))
        out.append("")

    print("\n".join(out).rstrip())


def name_of(who, student):
    return student if who == "me" else who


def entry_line(e, include_who=True, student="the student"):
    d = parse_when(e["at"])
    if include_who:
        line = "%s: %s (%s) %s" % (fmt_day(d), name_of(e["who"], student), KIND_LABEL[e["kind"]], e["text"])
    else:
        line = "%s: %s" % (fmt_day(d), e["text"])
    if e.get("hours"):
        line += " (%gh)" % e["hours"]
    if e.get("evidence") or e.get("evidence_desc"):
        line += " [evidence]"
    if days_between(d, parse_when(e["recorded"])) >= 2:
        line += " [logged later]"
    return line


# ---------- cli ----------

def build_parser():
    p = argparse.ArgumentParser(prog="receipts.py", description="Dated contribution log for group projects.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, project=True):
        if project:
            sp.add_argument("--project", help="project name (optional when only one is active)")
        sp.add_argument("--now", help="student's local date and time, ISO with offset")

    sp = sub.add_parser("new", help="start a project")
    common(sp)
    sp.add_argument("--course")
    sp.add_argument("--members", help="comma-separated teammate names, not including the student")
    sp.add_argument("--due")
    sp.add_argument("--peer-eval", dest="peer_eval")
    sp.set_defaults(func=cmd_new)

    sp = sub.add_parser("members", help="add or remove teammates, set dates")
    common(sp)
    sp.add_argument("--add", action="append")
    sp.add_argument("--remove", action="append")
    sp.add_argument("--due")
    sp.add_argument("--peer-eval", dest="peer_eval")
    sp.set_defaults(func=cmd_members)

    sp = sub.add_parser("log", help="add an entry")
    common(sp)
    sp.add_argument("--who", required=True, help="me, or a teammate's name")
    sp.add_argument("--kind", required=True, choices=KINDS)
    sp.add_argument("--text", required=True)
    sp.add_argument("--at", help="when it happened, if not now")
    sp.add_argument("--hours", type=float)
    sp.add_argument("--by", help="for promised: when it was promised for")
    sp.add_argument("--evidence", help="path to a screenshot or file to keep")
    sp.add_argument("--evidence-desc", dest="evidence_desc", help="one line describing the evidence")
    sp.set_defaults(func=cmd_log)

    sp = sub.add_parser("kept", help="mark a promise kept")
    common(sp)
    sp.add_argument("--id", type=int, required=True)
    sp.add_argument("--at")
    sp.add_argument("--note")
    sp.set_defaults(func=cmd_kept)

    sp = sub.add_parser("broke", help="mark a promise not done")
    common(sp)
    sp.add_argument("--id", type=int, required=True)
    sp.add_argument("--note")
    sp.set_defaults(func=cmd_broke)

    sp = sub.add_parser("remove", help="delete a wrong entry")
    common(sp)
    sp.add_argument("--id", type=int, required=True)
    sp.set_defaults(func=cmd_remove)

    sp = sub.add_parser("archive", help="archive a finished project")
    common(sp)
    sp.add_argument("--undo", action="store_true")
    sp.set_defaults(func=cmd_archive)

    sp = sub.add_parser("list", help="list projects")
    sp.add_argument("--sample", action="store_true")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("status", help="open and overdue promises, quiet teammates")
    common(sp)
    sp.add_argument("--quiet-days", dest="quiet_days", type=int, default=4)
    sp.add_argument("--sample", action="store_true", help="use the bundled sample project")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("summary", help="Markdown contribution record")
    common(sp)
    sp.add_argument("--student", help="the student's first name for the report")
    sp.add_argument("--sample", action="store_true", help="use the bundled sample project")
    sp.set_defaults(func=cmd_summary)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except UserError as e:
        print(str(e))
        return e.code
    return 0


if __name__ == "__main__":
    sys.exit(main())
