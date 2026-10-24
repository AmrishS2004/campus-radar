# Campus Radar

**Canvas shows you the tabs. Your inbox buries the rest. Cubbie catches all of it.**

Campus Radar is a set of eleven Cubbie Skills that work together. They read the parts of college life students
usually miss (lecture slides, syllabus fine print, discussion boards, club emails, grade feedback), keep a record of what the student
did, and step in at the right moment with a text, a phone call, a flowchart, a document or a draft. Turn on autopilot
once and it runs by itself.

## Install

Text this repository's link to Cubbie and reply "yes" when it asks. Cubbie installs all eleven Skills. Connect
Canvas and Google when Cubbie asks, then text "start Campus Radar" and say yes once to turn on autopilot. Discussion Radar's Ed features also ask for the student's own free Ed API
token, saved on Cubbie's secure page.

## The Skills

| Skill | What it does | Try texting |
| --- | --- | --- |
| [Radar Autopilot](skills/radar-autopilot) | One yes turns everything on: a morning sweep, an evening sweep, daily exam practice and a Sunday brief, texting only when something needs you. Also checks itself | "start Campus Radar", "check Campus Radar" |
| [Slide Radar](skills/slide-radar) | Finds homework mentioned only in slides, files or announcements, and the missing instructions for vague assignments | "did I miss anything in the slides?" |
| [Exam Radar](skills/exam-radar) | Exam countdowns, a wake-up call on exam morning, and 3 daily practice questions from your slides that repeat until you get them right | "my CSE 310 midterm is Nov 3, quiz me every day" |
| [Club Radar](skills/club-radar) | Club meetings, events, registrations and last-minute changes from your email, on your calendar, with texts or calls before the important ones | "what club stuff is happening this week?" |
| [Group Project Receipts](skills/group-project-receipts) | A dated log of who did what, follow-ups on promises, nudges you send, and a contribution record for peer evals | "Jake said he'd do the intro slides by Tuesday" |
| [Grade Radar](skills/grade-radar) | Checks each new grade against the rubric, tracks the regrade window, drafts the request, and does the final-exam math | "what do I need on the final?" |
| [Professor Radar](skills/professor-radar) | Logs office hours and strong work per professor, picks who knows you best, and builds the brag sheet for a rec letter | "who should I ask for a recommendation?" |
| [Discussion Radar](skills/discussion-radar) | Important Ed news, answers to your question from existing Ed threads or a drafted post, and deadlines for Yellowdig and Harmonize, which never notify you | "for HW 5 can we assume the graph is connected?" |
| [Inbox Radar](skills/inbox-radar) | Drafts replies to school emails in Gmail and keeps a Google Tasks to-do list from every ask and deadline | "what emails do I need to answer?" |
| [Catch Me Up](skills/catch-me-up) | One PDF of everything you missed while sick or away, drafted absence and extension emails, and an emergency mode that notifies every affected professor with one yes | "emergency, I'm in the hospital" |
| [Sunday Radar](skills/sunday-radar) | One Sunday text with your whole week as a flowchart, conflicts flagged, plus step-by-step flowcharts for big assignments | "what does my week look like?", "show HW 5 as a flowchart" |

## Ground rules

- Cubbie only texts its own student. Every message to a teammate, professor or TA is a draft the student sends.
- Nothing is submitted, registered for or paid without the student's yes.
- Recurring check-ins and phone calls start only after the student agrees, once for autopilot or per Skill, and pause with one text.
- Nothing is posted on Ed without the student's yes to that exact post.
- Everything stays on the student's own Cubbie drive. No servers of ours, and the only key is the student's own Ed token.

## How it's built

Each Skill is a standard Agent Skills folder. Four are instructions only and lean on Cubbie's own abilities
(Canvas, Gmail, Calendar, Drive, Tasks, reminders, calls, the browser, documents). Seven include a small Python
script (standard library only, nothing to install) for the parts that need exact math, an outside API, a picture, or a
record that must not drift between conversations: the group project log, the spaced-repetition practice tracker, the
grade calculator, the professor log, the Ed Discussion client, the flowchart renderer (it writes PDFs itself) and the
health check. Each script has a `--sample` mode.

```bash
python3 skills/group-project-receipts/scripts/receipts.py summary --sample --student Alex --now 2026-10-24T13:00-07:00
python3 skills/exam-radar/scripts/practice.py q-due --sample --now 2026-10-24T13:00-07:00
python3 skills/grade-radar/scripts/grade_math.py need --sample
python3 skills/professor-radar/scripts/professors.py rank --sample --now 2026-10-24T13:00-07:00
python3 skills/discussion-radar/scripts/ed.py search --sample --course "CSE 310" --query "can we assume the graph is connected"
python3 skills/sunday-radar/scripts/flow.py week --sample --out week.pdf
python3 skills/radar-autopilot/scripts/selfcheck.py
```

Tests: `for t in tests/*.py; do python3 "$t"; done`
(the Ed test runs the live code path against a local fake Ed server). Ed's API is in beta and
community-documented, so its endpoints may change.

Built for the Cubbie Hackathon (Track 1).
