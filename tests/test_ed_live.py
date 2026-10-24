"""Exercise ed.py's live code path against a local fake Ed API (no real network)."""
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "discussion-radar", "scripts", "ed.py")
SAMPLE = json.load(open(os.path.join(os.path.dirname(SCRIPT), "..", "assets", "sample_ed.json")))
seen = {}
fails = 0


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def authed(self):
        seen["auth"] = self.headers.get("Authorization")
        if self.headers.get("Authorization") != "Bearer good-token":
            self.reply(401, {"code": "bad_token"})
            return False
        return True

    def do_GET(self):
        if not self.authed():
            return
        path = self.path.split("?")[0]
        if path == "/api/user":
            self.reply(200, {"courses": [{"course": c, "role": {"role": "student"}} for c in SAMPLE["courses"]]})
        elif path.startswith("/api/courses/") and path.endswith("/threads"):
            cid = int(path.split("/")[3])
            seen["query"] = self.path.split("?")[1]
            self.reply(200, {"threads": [t for t in SAMPLE["threads"] if t["course_id"] == cid], "users": SAMPLE["users"]})
        elif path.startswith("/api/threads/"):
            tid = int(path.split("/")[3])
            t = next((t for t in SAMPLE["threads"] if t["id"] == tid), None)
            self.reply(200 if t else 404, {"thread": t, "users": SAMPLE["users"]} if t else {})
        else:
            self.reply(404, {})

    def do_POST(self):
        if not self.authed():
            return
        n = int(self.headers.get("Content-Length", 0))
        seen["post"] = json.loads(self.rfile.read(n))
        seen["post_path"] = self.path
        self.reply(200, {"status": "ok", "thread": {"id": 777, "course_id": 18001}})


srv = HTTPServer(("127.0.0.1", 0), Fake)
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = "http://127.0.0.1:%d/api/" % srv.server_address[1]


def run(*args, token="good-token"):
    env = dict(os.environ, ED_API_BASE=base, ED_API_TOKEN=token)
    p = subprocess.run([sys.executable, "-I", SCRIPT, *args], capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout + p.stderr).strip()


def check(name, cond, detail=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  -> " + detail))
    fails += 0 if cond else 1


code, out = run("courses")
check("live: courses", code == 0 and "CSE 310" in out and seen["auth"] == "Bearer good-token", out)
code, out = run("courses", token="bad")
check("live: bad token -> 5", code == 5, out)
code, out = run("digest", "--course", "CSE 310")
check("live: digest", code == 0 and "Midterm 2 moved" in out, out)
check("live: threads query params", "limit=100" in seen["query"] and "sort=new" in seen["query"], seen.get("query", ""))
code, out = run("search", "--course", "18001", "--query", "HW 5 deadline extended midterm")
check("live: search finds extension thread", code == 0 and "#503" in out, out)
code, out = run("thread", "--id", "503")
check("live: thread answer", "Saturday Nov 7" in out and "staff" in out, out)
code, out = run("thread", "--id", "999")
check("live: missing thread -> 2", code == 2, out)
code, out = run("post", "--course", "18001", "--title", "Lab 4 & late policy?", "--body",
                "Is Lab 4 accepted late?\n\nThe syllabus says <2 days>.", "--category", "Homework",
                "--anonymous", "--confirm")
post = seen.get("post", {}).get("thread", {})
check("live: post ok with link", code == 0 and "discussion/777" in out, out)
check("live: post path", seen.get("post_path") == "/api/courses/18001/threads", seen.get("post_path", ""))
check("live: post body fields", post.get("type") == "question" and post.get("is_anonymous") is True
      and post.get("is_private") is False and post.get("category") == "Homework", json.dumps(post))
check("live: content is escaped Ed XML",
      post.get("content") == '<document version="2.0"><paragraph>Is Lab 4 accepted late?</paragraph>'
                             '<paragraph>The syllabus says &lt;2 days&gt;.</paragraph></document>', post.get("content", ""))
# sample mode, no token at all
def run_sample(*args):
    env = {k: v for k, v in os.environ.items() if k not in ("ED_API_TOKEN", "ED_API_BASE")}
    p = subprocess.run([sys.executable, "-I", SCRIPT, *args, "--sample"], capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout + p.stderr).strip()


code, out = run_sample("search", "--course", "CSE 310", "--query", "late policy for labs")
check("sample: unrelated question -> NO_MATCH exit 2", code == 2 and "NO_MATCH" in out, out)
code, out = run_sample("digest", "--since", "2026-10-22")
check("sample: social post filtered out of digest", "Study group" not in out and "Midterm 2 moved" in out, out)
code, out = run_sample("thread", "--id", "502")
check("sample: accepted staff answer first", out.splitlines()[2].startswith("Answer (accepted, endorsed, staff)"), out)
env = {k: v for k, v in os.environ.items() if k != "ED_API_TOKEN"}
p = subprocess.run([sys.executable, "-I", SCRIPT, "courses"], capture_output=True, text=True, env=env)
check("no token -> exit 4", p.returncode == 4, p.stdout)
srv.shutdown()
print("\n%d failure(s)" % fails)
sys.exit(1 if fails else 0)
