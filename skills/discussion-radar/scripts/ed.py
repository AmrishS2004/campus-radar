#!/usr/bin/env python3
"""Discussion Radar: read and search Ed Discussion, and post a question after the student says yes.

Standard library only. Needs the student's own Ed API token in ED_API_TOKEN
(created at https://edstem.org/us/settings/api-tokens). Ed's API is in beta and
community-documented, so endpoints may change.

  courses                       active Ed courses with their ids
  digest  --course ID|all       important threads since a date
  search  --course ID --query   existing threads that match a question
  thread  --id N                one thread with its answers
  post    --course ID ... --confirm   create a thread (only after the student's yes)

Every command but post has --sample, which reads assets/sample_ed.json and needs no token.

Exit codes: 0 ok, 2 nothing found, 3 bad input, 4 token missing,
5 token rejected, 6 Ed unreachable or another Ed error.
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_FILE = os.path.join(SKILL_DIR, "assets", "sample_ed.json")
REGION = os.environ.get("ED_REGION", "us")
API = os.environ.get("ED_API_BASE") or "https://%s.edstem.org/api/" % REGION  # override only for tests
WEB = "https://edstem.org/%s/courses/%%s/discussion/%%s" % REGION

IMPORTANT_WORDS = {
    "exam": 3, "midterm": 3, "final": 2, "quiz": 2, "due": 2, "deadline": 3, "extension": 3, "extended": 3,
    "cancelled": 3, "canceled": 3, "moved": 2, "reschedule": 3, "rescheduled": 3, "postponed": 3,
    "homework": 1, "hw": 1, "assignment": 1, "project": 1, "clarification": 2, "correction": 3,
    "typo": 2, "errata": 3, "office hours": 2, "grades": 2, "regrade": 2, "solution": 2, "solutions": 2,
    "important": 2, "reminder": 1, "room": 1, "zoom": 1,
}
STOP = set("a an the is are was were be been to of in on for and or but with at by from it this that what "
           "how do does did can could should would will i we you my our your me about any there when which "
           "who why if so as not no yes get got have has had".split())


class EdError(Exception):
    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


# ---------- data access ----------

class Live:
    def __init__(self):
        self.token = os.environ.get("ED_API_TOKEN", "").strip()
        if not self.token:
            raise EdError("ED_API_TOKEN is not set. The student needs to save their Ed API token.", 4)

    def call(self, method, path, params=None, body=None):
        url = API + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": "Bearer " + self.token, "Content-Type": "application/json",
            "User-Agent": "campus-radar-discussion-radar"})
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise EdError("Ed rejected the API token (HTTP %d). It may be expired or revoked." % e.code, 5)
            if e.code == 404:
                raise EdError("Ed says that course or thread doesn't exist (HTTP 404).", 2)
            detail = e.read().decode(errors="replace")[:200]
            raise EdError("Ed returned HTTP %d: %s" % (e.code, detail), 6)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise EdError("Can't reach Ed right now (%s)." % getattr(e, "reason", e), 6)

    def courses(self):
        data = self.call("GET", "user")
        out = []
        for c in data.get("courses", []):
            course = c.get("course", c)
            out.append({"id": course.get("id"), "code": course.get("code", ""), "name": course.get("name", ""),
                        "status": course.get("status", ""), "role": (c.get("role") or {}).get("role", "")})
        return out

    def threads(self, course_id, pages=1):
        threads, users = [], {}
        for page in range(pages):
            data = self.call("GET", "courses/%d/threads" % course_id,
                             {"limit": 100, "offset": page * 100, "sort": "new"})
            for u in data.get("users", []):
                users[u["id"]] = u
            batch = data.get("threads", [])
            threads.extend(batch)
            if len(batch) < 100:
                break
        return threads, users

    def thread(self, thread_id):
        data = self.call("GET", "threads/%d" % thread_id)
        users = {u["id"]: u for u in data.get("users", [])}
        return data["thread"], users

    def post(self, course_id, thread):
        data = self.call("POST", "courses/%d/threads" % course_id, body={"thread": thread})
        return data.get("thread", {})


class Sample:
    def __init__(self):
        with open(SAMPLE_FILE, encoding="utf-8") as fh:
            self.data = json.load(fh)

    def courses(self):
        return self.data["courses"]

    def threads(self, course_id, pages=1):
        ts = [t for t in self.data["threads"] if t["course_id"] == course_id]
        return ts, {u["id"]: u for u in self.data["users"]}

    def thread(self, thread_id):
        for t in self.data["threads"]:
            if t["id"] == thread_id:
                return t, {u["id"]: u for u in self.data["users"]}
        raise EdError("No thread %d." % thread_id, 2)

    def post(self, course_id, thread):
        raise EdError("Posting isn't available in sample mode.", 3)


# ---------- helpers ----------

def parse_when(text):
    if not text:
        return None
    raw = text.strip().replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(raw)
    except ValueError:
        # Ed timestamps can carry fractional seconds with more digits than Python accepts
        m = re.match(r"(.*?)(\.\d+)?([+-]\d\d:\d\d)?$", raw)
        try:
            d = datetime.fromisoformat(m.group(1) + (m.group(3) or ""))
        except (ValueError, AttributeError):
            raise EdError("Can't read the date '%s'." % text, 3)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def text_of(t):
    return re.sub(r"\s+", " ", (t.get("document") or strip_xml(t.get("content", "")))).strip()


def strip_xml(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s or ""))


def is_staff(user):
    return bool(user) and (user.get("course_role") or "student").lower() not in ("student", "")


def snippet(s, n=160):
    s = s.strip()
    return s if len(s) <= n else s[:n - 1].rsplit(" ", 1)[0] + "..."


def url_of(t):
    return WEB % (t["course_id"], t["id"])


def tokens(s):
    return [w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 1]


def pick_courses(src, course):
    cs = [c for c in src.courses() if c.get("status", "active") != "archived"]
    if course in (None, "all"):
        return cs
    for c in cs:
        if str(c["id"]) == str(course) or c["code"].lower().replace(" ", "") == str(course).lower().replace(" ", ""):
            return [c]
    raise EdError("No active Ed course matching '%s'. Run courses to see them." % course, 2)


# ---------- commands ----------

def cmd_courses(src, args):
    cs = [c for c in src.courses() if c.get("status", "active") != "archived"]
    if not cs:
        print("No active Ed courses on this account.")
        return 2
    for c in cs:
        print("%s: %s (id %s)" % (c["code"], c["name"], c["id"]))
    return 0


def importance(t, users):
    score, why = 0, []
    if t.get("type") == "announcement":
        score += 6
        why.append("announcement")
    if t.get("is_pinned"):
        score += 4
        why.append("pinned")
    if is_staff(users.get(t.get("user_id"))):
        score += 3
        why.append("from staff")
    blob = (t.get("title", "") + " " + text_of(t)).lower()
    hits = [w for w in IMPORTANT_WORDS if re.search(r"\b" + re.escape(w) + r"\b", blob)]
    if hits:
        score += min(6, sum(IMPORTANT_WORDS[w] for w in hits))
        why.append("mentions " + ", ".join(hits[:3]))
    if t.get("is_staff_answered") or t.get("is_endorsed"):
        score += 1
    score += min(3, (t.get("vote_count") or 0) // 3)
    return score, why


def cmd_digest(src, args):
    since = parse_when(args.since) if args.since else None
    found = []
    for c in pick_courses(src, args.course):
        threads, users = src.threads(c["id"], pages=1)
        for t in threads:
            created = parse_when(t.get("created_at"))
            if since and created and created < since:
                continue
            score, why = importance(t, users)
            if score >= args.min_score:
                found.append((score, created, c, t, why))
    if not found:
        print("Nothing important on Ed%s." % (" since " + args.since if args.since else ""))
        return 2
    found.sort(key=lambda x: (-x[0], -(x[1].timestamp() if x[1] else 0)))
    for score, created, c, t, why in found[:args.limit]:
        when = created.strftime("%b %d") if created else ""
        print("[%s] %s (%s; %s)" % (c["code"], t.get("title", "(untitled)"), when, ", ".join(why)))
        print("  " + snippet(text_of(t)))
        print("  " + url_of(t))
    if len(found) > args.limit:
        print("(%d more lower-priority threads not shown)" % (len(found) - args.limit))
    return 0


def cmd_search(src, args):
    q = tokens(args.query)
    if not q:
        raise EdError("The question needs some words to search for.", 3)
    courses = pick_courses(src, args.course)
    results, categories = [], set()
    for c in courses:
        threads, users = src.threads(c["id"], pages=args.pages)
        for t in threads:
            if t.get("category"):
                categories.add(t["category"])
            title_t = set(tokens(t.get("title", "")))
            body_t = set(tokens(text_of(t)))
            overlap_title = len(set(q) & title_t)
            overlap_body = len(set(q) & body_t)
            score = (2 * overlap_title + overlap_body) / (2 * len(set(q)))
            if score >= args.min_match:
                results.append((score, c, t))
    results.sort(key=lambda r: -r[0])
    if categories:
        print("Categories seen: " + ", ".join(sorted(categories)))
    if not results:
        print("NO_MATCH: no existing thread looks like this question.")
        return 2
    for score, c, t in results[:args.limit]:
        status = "answered by staff" if t.get("is_staff_answered") else \
            "answered" if t.get("is_answered") or t.get("is_student_answered") else \
            "no answer yet" if t.get("type") == "question" else t.get("type", "post")
        print("#%d [%s] %s (match %d%%, %s, %d replies)" % (
            t["id"], c["code"], t.get("title", ""), round(100 * score), status, t.get("reply_count") or 0))
        print("  " + snippet(text_of(t), 120))
        print("  " + url_of(t))
    return 0


def cmd_thread(src, args):
    t, users = src.thread(args.id)
    print("%s (%s)" % (t.get("title", ""), url_of(t)))
    print("Question: " + snippet(text_of(t), 600))
    answers = sorted(t.get("answers", []) or [], key=lambda a: (
        not a.get("is_endorsed"), not is_staff(users.get(a.get("user_id"))), -(a.get("vote_count") or 0)))
    if t.get("accepted_id"):
        answers.sort(key=lambda a: a.get("id") != t["accepted_id"])
    if not answers:
        print("No answers yet.")
    for a in answers[:3]:
        tag = []
        if a.get("id") == t.get("accepted_id"):
            tag.append("accepted")
        if a.get("is_endorsed"):
            tag.append("endorsed")
        if is_staff(users.get(a.get("user_id"))):
            tag.append("staff")
        print("Answer%s: %s" % ((" (" + ", ".join(tag) + ")") if tag else "", snippet(text_of(a), 700)))
    staff_comments = [cm for cm in (t.get("comments") or []) if is_staff(users.get(cm.get("user_id")))]
    for cm in staff_comments[:2]:
        print("Staff comment: " + snippet(text_of(cm), 400))
    return 0


def to_ed_document(body):
    paras = [p.strip() for p in re.split(r"\n\s*\n", body.strip()) if p.strip()]
    inner = "".join("<paragraph>%s</paragraph>" % html.escape(p.replace("\n", " "), quote=False) for p in paras)
    return '<document version="2.0">%s</document>' % inner


def cmd_post(src, args):
    if not args.confirm:
        raise EdError("Refusing to post without --confirm. Show the student the draft and post only after their yes.", 3)
    if not args.title.strip() or not args.body.strip():
        raise EdError("A post needs a title and a body.", 3)
    c = pick_courses(src, args.course)[0]
    thread = {
        "type": args.type, "title": args.title.strip(), "category": args.category,
        "subcategory": args.subcategory or "", "subsubcategory": "", "content": to_ed_document(args.body),
        "is_pinned": False, "is_private": bool(args.private), "is_anonymous": bool(args.anonymous),
        "is_megathread": False, "anonymous_comments": False,
    }
    t = src.post(c["id"], thread)
    tid = t.get("id")
    print("Posted to %s: %s" % (c["code"], args.title.strip()))
    if tid:
        print(WEB % (c["id"], tid))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="ed.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("courses")
    sp.add_argument("--sample", action="store_true")
    sp.set_defaults(func=cmd_courses)

    sp = sub.add_parser("digest")
    sp.add_argument("--course", default="all")
    sp.add_argument("--since", help="ISO date or time; only threads created after it")
    sp.add_argument("--limit", type=int, default=6)
    sp.add_argument("--min-score", dest="min_score", type=int, default=4)
    sp.add_argument("--sample", action="store_true")
    sp.set_defaults(func=cmd_digest)

    sp = sub.add_parser("search")
    sp.add_argument("--course", required=True)
    sp.add_argument("--query", required=True)
    sp.add_argument("--pages", type=int, default=3, help="pages of 100 threads to search")
    sp.add_argument("--limit", type=int, default=3)
    sp.add_argument("--min-match", dest="min_match", type=float, default=0.35)
    sp.add_argument("--sample", action="store_true")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("thread")
    sp.add_argument("--id", type=int, required=True)
    sp.add_argument("--sample", action="store_true")
    sp.set_defaults(func=cmd_thread)

    sp = sub.add_parser("post")
    sp.add_argument("--course", required=True)
    sp.add_argument("--title", required=True)
    sp.add_argument("--body", required=True)
    sp.add_argument("--category", required=True)
    sp.add_argument("--subcategory")
    sp.add_argument("--type", default="question", choices=("question", "post"))
    sp.add_argument("--anonymous", action="store_true", help="anonymous to classmates, if the course allows it")
    sp.add_argument("--private", action="store_true", help="visible only to course staff")
    sp.add_argument("--confirm", action="store_true", help="the student said yes to this exact post")
    sp.set_defaults(func=cmd_post, sample=False)

    args = p.parse_args(argv)
    if args.cmd == "post" and not args.confirm:
        print("Refusing to post without --confirm. Show the student the draft and post only after their yes.")
        return 3
    try:
        src = Sample() if args.sample else Live()
        return args.func(src, args) or 0
    except EdError as e:
        print(str(e))
        return e.code


if __name__ == "__main__":
    sys.exit(main())
