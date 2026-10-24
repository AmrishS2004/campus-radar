#!/usr/bin/env python3
"""Exam Radar: exam countdowns and spaced-repetition practice questions.

Standard library only. State lives in ~/.config/exam-radar/state.json.
Cubbie writes the questions (from the student's slides and syllabus); this script
stores them, decides which ones are due each day, and tracks right and wrong answers.

Leitner boxes: a new question is due right away. A right answer moves it up one box
(next review in 1, 2, 4, 7 or 14 days); a right answer in the last box retires it.
A wrong answer sends it back to box 1, due again tomorrow.

Exit codes: 0 ok, 2 nothing found (no exams, unknown exam id), 3 bad input.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_FILE = os.path.join(SKILL_DIR, "assets", "sample_state.json")
INTERVALS = [1, 2, 4, 7, 14]
MILESTONES = {14: "in 2 weeks", 7: "in 1 week", 3: "in 3 days", 1: "tomorrow", 0: "today"}


class UserError(Exception):
    def __init__(self, message, code=3):
        super().__init__(message)
        self.code = code


def state_path():
    base = os.environ.get("EXAM_RADAR_HOME") or os.path.join(os.path.expanduser("~"), ".config", "exam-radar")
    return os.path.join(base, "state.json")


def load(sample=False):
    path = SAMPLE_FILE if sample else state_path()
    if not os.path.exists(path):
        return {"exams": [], "questions": [], "next_exam": 1, "next_q": 1}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(state, sample=False):
    if sample:
        return
    path = state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)
    os.replace(path + ".tmp", path)


def parse_when(text, ref=None):
    raw = text.strip().replace("Z", "+00:00")
    if " " in raw and "T" not in raw:
        raw = raw.replace(" ", "T", 1)
    try:
        d = datetime.fromisoformat(raw)
    except ValueError:
        raise UserError("Can't read the date '%s'. Use YYYY-MM-DD or YYYY-MM-DDTHH:MM-07:00." % text)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        d = d.replace(hour=9)  # date-only exams: assume a morning slot for display
    if d.tzinfo is None:
        tz = ref.tzinfo if ref is not None and ref.tzinfo else datetime.now().astimezone().tzinfo
        d = d.replace(tzinfo=tz)
    return d


def now_from(arg):
    return parse_when(arg) if arg else datetime.now().astimezone()


def iso(d):
    return d.isoformat(timespec="minutes")


def fmt_day(d):
    return d.strftime("%a %b ") + str(d.day)


def days_left(now, when):
    return (when.date() - now.date()).days


def exam_label(e):
    return "%s %s" % (e["course"], e["name"]) if e.get("course") else e["name"]


def get_exam(state, exam_id):
    for e in state["exams"]:
        if e["id"] == exam_id:
            return e
    raise UserError("No exam #%s. Run exams to see the list." % exam_id, 2)


def upcoming(state, now):
    return sorted([e for e in state["exams"] if days_left(now, parse_when(e["date"])) >= 0],
                  key=lambda e: e["date"])


# ---------- exams ----------

def cmd_exam_add(args):
    state = load()
    now = now_from(args.now)
    when = parse_when(args.date, now)
    if days_left(now, when) < 0:
        raise UserError("That exam date has already passed.")
    for e in state["exams"]:
        if e["course"].lower() == (args.course or "").lower() and e["name"].lower() == args.name.lower():
            e["date"] = iso(when)
            if args.topics:
                e["topics"] = split_topics(args.topics)
            save(state)
            print("Updated #%d %s: %s (%d days away)" % (e["id"], exam_label(e), fmt_day(when), days_left(now, when)))
            return
    exam = {"id": state["next_exam"], "course": (args.course or "").strip(), "name": args.name.strip(),
            "date": iso(when), "topics": split_topics(args.topics or ""),
            "source": (args.source or "").strip(), "added": iso(now)}
    state["exams"].append(exam)
    state["next_exam"] += 1
    save(state)
    print("Added exam #%d: %s on %s (%d days away)" % (exam["id"], exam_label(exam), fmt_day(when),
                                                     days_left(now, when)))
    if exam["topics"]:
        print("Topics: " + ", ".join(exam["topics"]))


def split_topics(text):
    return [t.strip() for t in re.split(r"[;\n]", text) if t.strip()]


def cmd_exam_remove(args):
    state = load()
    exam = get_exam(state, args.id)
    state["exams"] = [e for e in state["exams"] if e["id"] != args.id]
    state["questions"] = [q for q in state["questions"] if q["exam"] != args.id]
    save(state)
    print("Removed %s and its questions." % exam_label(exam))


def cmd_exams(args):
    state = load(args.sample)
    now = now_from(args.now)
    ups = upcoming(state, now)
    if not ups:
        print("No upcoming exams saved.")
        return 2
    for e in ups:
        d = days_left(now, parse_when(e["date"]))
        qs = [q for q in state["questions"] if q["exam"] == e["id"]]
        print("#%d %s: %s (%s), %d practice questions" % (
            e["id"], exam_label(e), fmt_day(parse_when(e["date"])), when_text(d), len(qs)))
    return 0


def when_text(d):
    return {0: "today", 1: "tomorrow"}.get(d, "in %d days" % d)


def cmd_countdown(args):
    state = load(args.sample)
    now = now_from(args.now)
    lines = []
    for e in upcoming(state, now):
        when = parse_when(e["date"])
        d = days_left(now, when)
        if d in MILESTONES:
            st = topic_stats(state, e["id"])
            weak = [t for t, (r, n) in st if n and r / n < 0.7][:2]
            line = "%s is %s (%s)" % (exam_label(e), MILESTONES[d], fmt_day(when))
            if weak:
                line += "; weakest topics so far: " + ", ".join(weak)
            lines.append(line)
    print("\n".join(lines) if lines else "No countdown messages today.")


# ---------- questions ----------

def cmd_q_add(args):
    state = load()
    now = now_from(args.now)
    exam = get_exam(state, args.exam)
    items = []
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise UserError("The questions file should be a JSON list.")
        items = data
    else:
        items = [{"question": args.question, "answer": args.answer, "topic": args.topic, "source": args.source}]
    existing = {norm(q["question"]) for q in state["questions"] if q["exam"] == exam["id"]}
    added, skipped = 0, 0
    for it in items:
        qtext = (it.get("question") or "").strip()
        atext = (it.get("answer") or "").strip()
        if not qtext or not atext:
            raise UserError("Every question needs both a question and an answer.")
        if norm(qtext) in existing:
            skipped += 1
            continue
        state["questions"].append({
            "id": state["next_q"], "exam": exam["id"], "question": qtext, "answer": atext,
            "topic": (it.get("topic") or "general").strip(), "source": (it.get("source") or "").strip(),
            "box": 0, "due": iso(now), "right": 0, "wrong": 0, "retired": False, "added": iso(now)})
        state["next_q"] += 1
        existing.add(norm(qtext))
        added += 1
    save(state)
    msg = "Added %d question(s) for %s." % (added, exam_label(exam))
    if skipped:
        msg += " Skipped %d duplicate(s)." % skipped
    print(msg)


def norm(text):
    return re.sub(r"\W+", " ", text.lower()).strip()


def cmd_q_due(args):
    state = load(args.sample)
    now = now_from(args.now)
    exam_ids = [e["id"] for e in upcoming(state, now)]
    if args.exam:
        get_exam(state, args.exam)
        exam_ids = [args.exam] if args.exam in exam_ids else []
    if not exam_ids:
        print("No upcoming exams to practice for.")
        return 2
    pool = [q for q in state["questions"] if q["exam"] in exam_ids and not q["retired"]]
    reviews = sorted([q for q in pool if q["box"] > 0 and parse_when(q["due"]) <= now],
                     key=lambda q: q["due"])
    new = [q for q in pool if q["box"] == 0]
    # spread new questions across topics, least-practiced topic first
    attempts = {}
    for q in pool:
        attempts[q["topic"]] = attempts.get(q["topic"], 0) + q["right"] + q["wrong"]
    new.sort(key=lambda q: (attempts.get(q["topic"], 0), q["id"]))
    picked, seen_topics = [], set()
    for q in reviews:
        if len(picked) < args.n:
            picked.append(q)
    for q in new:
        if len(picked) >= args.n:
            break
        if q["topic"] in seen_topics and any(x["topic"] not in seen_topics for x in new if x not in picked):
            continue
        picked.append(q)
        seen_topics.add(q["topic"])
    for q in new:  # fill up if topic spreading left gaps
        if len(picked) >= args.n:
            break
        if q not in picked:
            picked.append(q)
    exams = {e["id"]: e for e in state["exams"]}
    for q in picked:
        kind = "review" if q["box"] > 0 else "new"
        print("#%d (%s, %s, %s)" % (q["id"], exam_label(exams[q["exam"]]), q["topic"], kind))
        print("Q: " + q["question"])
        print("Answer key (don't show the student): " + q["answer"])
        if q["source"]:
            print("Source: " + q["source"])
    unused_new = len([q for q in new if q not in picked])
    if len(picked) < args.n or unused_new < args.n:
        print("NEED_MORE: write %d more question(s) from the course materials." % max(args.n, args.n * 3 - unused_new))
    if not picked:
        return 2
    return 0


def cmd_q_grade(args):
    state = load()
    now = now_from(args.now)
    q = next((x for x in state["questions"] if x["id"] == args.id), None)
    if q is None:
        raise UserError("No question #%s." % args.id, 2)
    if args.result == "right":
        q["right"] += 1
        if q["box"] >= len(INTERVALS):
            q["retired"] = True
            nxt = "retired, you've got this one"
        else:
            q["box"] += 1
            q["due"] = iso(now + timedelta(days=INTERVALS[q["box"] - 1]))
            nxt = "next review " + fmt_day(parse_when(q["due"]))
    else:
        q["wrong"] += 1
        q["box"] = 1
        q["due"] = iso(now + timedelta(days=1))
        nxt = "back tomorrow"
    save(state)
    print("#%d %s: %s" % (q["id"], args.result, nxt))


def topic_stats(state, exam_id):
    st = {}
    for q in state["questions"]:
        if q["exam"] != exam_id:
            continue
        r, n = st.get(q["topic"], (0, 0))
        st[q["topic"]] = (r + q["right"], n + q["right"] + q["wrong"])
    return sorted(st.items(), key=lambda kv: (kv[1][0] / kv[1][1]) if kv[1][1] else 2)


def cmd_stats(args):
    state = load(args.sample)
    exam = get_exam(state, args.exam)
    qs = [q for q in state["questions"] if q["exam"] == exam["id"]]
    right = sum(q["right"] for q in qs)
    total = right + sum(q["wrong"] for q in qs)
    print("%s: %d questions, %d retired" % (exam_label(exam), len(qs), sum(1 for q in qs if q["retired"])))
    if total:
        print("Overall: %d of %d right (%d%%)" % (right, total, round(100 * right / total)))
    for topic, (r, n) in topic_stats(state, exam["id"]):
        print("- %s: %s" % (topic, ("%d/%d right" % (r, n)) if n else "not practiced yet"))


def build_parser():
    p = argparse.ArgumentParser(prog="practice.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("exam-add")
    sp.add_argument("--course", default="")
    sp.add_argument("--name", required=True)
    sp.add_argument("--date", required=True)
    sp.add_argument("--topics", help="topics separated by ;")
    sp.add_argument("--source", help="where the date came from")
    sp.add_argument("--now")
    sp.set_defaults(func=cmd_exam_add)

    sp = sub.add_parser("exam-remove")
    sp.add_argument("--id", type=int, required=True)
    sp.set_defaults(func=cmd_exam_remove)

    for name, func in (("exams", cmd_exams), ("countdown", cmd_countdown)):
        sp = sub.add_parser(name)
        sp.add_argument("--now")
        sp.add_argument("--sample", action="store_true")
        sp.set_defaults(func=func)

    sp = sub.add_parser("q-add")
    sp.add_argument("--exam", type=int, required=True)
    sp.add_argument("--question")
    sp.add_argument("--answer")
    sp.add_argument("--topic")
    sp.add_argument("--source")
    sp.add_argument("--file", help="JSON list of {question, answer, topic, source}")
    sp.add_argument("--now")
    sp.set_defaults(func=cmd_q_add)

    sp = sub.add_parser("q-due")
    sp.add_argument("--n", type=int, default=3)
    sp.add_argument("--exam", type=int)
    sp.add_argument("--now")
    sp.add_argument("--sample", action="store_true")
    sp.set_defaults(func=cmd_q_due)

    sp = sub.add_parser("q-grade")
    sp.add_argument("--id", type=int, required=True)
    sp.add_argument("--result", choices=("right", "wrong"), required=True)
    sp.add_argument("--now")
    sp.set_defaults(func=cmd_q_grade)

    sp = sub.add_parser("stats")
    sp.add_argument("--exam", type=int, required=True)
    sp.add_argument("--sample", action="store_true")
    sp.set_defaults(func=cmd_stats)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        code = args.func(args)
    except UserError as e:
        print(str(e))
        return e.code
    return code or 0


if __name__ == "__main__":
    sys.exit(main())
