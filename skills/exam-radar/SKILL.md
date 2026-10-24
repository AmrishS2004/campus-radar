---
name: exam-radar
description: Counts down to every exam and sends three practice questions a day from the student's own lecture slides, bringing back missed ones until they stick. Countdown texts go out at 2 weeks, 1 week, 3 days and the night before, with an optional wake-up call on exam morning. Use whenever the student mentions an exam, midterm, final or quiz date, asks to be quizzed or for practice questions, wants daily practice, asks how ready they are, or says they have a test coming up. This adds daily spaced practice; for a full day-by-day study schedule, Cubbie's built-in study plan Skill fits better.
---

# Exam Radar

Students usually find out an exam is close when it's already close, and then cram. Exam Radar finds exam dates
early, counts down to them, and gets the student practicing a little every day from their actual course material,
so the night before is review instead of panic.

## When to use

- "my CSE 310 midterm is Nov 3"
- "quiz me for my midterm" / "give me practice questions"
- "send me questions every day until the final"
- "how ready am I for the bio exam?"
- When another Campus Radar Skill (Slide Radar, Sunday Radar) finds an exam date

Do not use it to answer graded quiz or exam questions the student is taking right now.

## The practice script

`scripts/practice.py` (Python 3, standard library only) stores exams and questions in
`~/.config/exam-radar/state.json`. Run it from this Skill's folder and always pass the student's current local
date and time as `--now` (ISO with UTC offset), since the sandbox clock may be in another time zone.

| Goal | Command |
| --- | --- |
| Save an exam | `python3 scripts/practice.py exam-add --course "CSE 310" --name "Midterm 2" --date 2026-11-03T10:30-07:00 --topics "Heaps; Hash tables; Graph traversal" --source "syllabus p.3" --now <now>` |
| List upcoming exams | `python3 scripts/practice.py exams --now <now>` |
| Which countdown texts are due today | `python3 scripts/practice.py countdown --now <now>` |
| Save questions you wrote | `python3 scripts/practice.py q-add --exam <id> --file <questions.json> --now <now>` |
| Today's questions | `python3 scripts/practice.py q-due --n 3 --now <now>` (add `--exam <id>` for one exam) |
| Record an answer | `python3 scripts/practice.py q-grade --id <question id> --result right` (or `wrong`) `--now <now>` |
| Topic-by-topic readiness | `python3 scripts/practice.py stats --exam <id>` |
| Remove an exam | `python3 scripts/practice.py exam-remove --id <id>` |

Saving the same course and exam name again updates its date, so a moved exam just needs `exam-add` again.
`--sample` on `exams`, `countdown`, `q-due` or `stats` uses `assets/sample_state.json` and saves nothing.

The questions file is a JSON list, for example:

```json
[{"question": "Which data structure does BFS use?", "answer": "A FIFO queue.",
  "topic": "Graph traversal", "source": "Lecture 16 slides, slide 6"}]
```

## Steps

### 1. Find the exams

1. Read the student's Canvas: the syllabus, course calendar events, announcements and assignments for anything
   called exam, midterm, final, test or quiz worth a real share of the grade. Note which topics or lectures each
   exam covers when the syllabus or an announcement says so.
2. Read the student's Google Calendar for exams they added themselves.
3. Save each exam with `exam-add`, including `--source` (where the date came from). Use the exam's start time when
   it's known. If Canvas isn't connected, ask the student for the course, exam and date.
4. Tell the student in one short text what you found and ask before anything recurring starts:
   "Found 2 exams: CSE 310 Midterm 2 Tue Nov 3, BIO 181 Exam 3 Thu Nov 12. Want countdown texts and 3 practice
   questions a day? 8 pm work?"

### 2. Countdown

With the student's yes, create one daily check-in at the time they chose, worded so it stands alone later:
"Exam Radar daily: run countdown and q-due, text the countdown lines and today's practice questions."

- The check-in runs `countdown` and sends any line it prints. Most days it prints nothing, and that's fine.
- On the day before an exam, also add the exam to Google Calendar if it isn't there yet (ask first), and offer a
  wake-up phone call on exam morning ("Want me to call you at 7:30 tomorrow?"). Only call with the student's yes.
- When an exam has passed, stop sending its questions. Remove the daily check-in once no exams are left, and tell
  the student.

### 3. Daily practice

1. Run `q-due --n 3`. It returns review questions that are due first, then new ones spread across topics.
2. If it prints `NEED_MORE`, write that many new questions before texting: search the student's course materials in
   Canvas (lecture slides, notes, practice exams, the readings the syllabus lists for that exam) for the exam's
   topics. Each question must come from the material, include a short answer key and a `source` like
   "Lecture 12 slides, slide 9". Mix recall, why/how and small applied questions, the way the course asks them.
   Save them with `q-add`, then run `q-due` again.
3. Text the questions, numbered, without the answer keys. Keep each one short enough for a phone.
4. When the student answers, judge each answer against the answer key and the source. Be generous with wording and
   strict on substance. Run `q-grade` for each, then reply with what was right, a one-line correction for anything
   wrong, and the source so they can look it up. If they skip a question or say "idk", grade it `wrong` (it comes
   back tomorrow, no judgment).
5. If the student asks for more ("give me 5 more on heaps"), run `q-due --n 5 --exam <id>` or write new questions on
   that topic.

### 4. Readiness

When the student asks how ready they are, or in the 3-day and night-before countdown, run `stats` and reply in two
or three lines: overall accuracy and the one or two weakest topics, with the slides to review for each.

## Replies

- Short, plain text, no Markdown symbols. Questions numbered 1 to 3.
- Never show the answer key before the student answers.
- Encouraging and specific: "2 of 3. Hash tables again: chaining search is O(1 + load factor), Lecture 12 slide 9."
- Countdown texts are one line each, plus at most one suggestion.

## When something fails

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 2 | No upcoming exams, or an unknown exam or question id | Say no exams are saved and offer to look in Canvas or take the date from the student |
| 3 | Bad input, such as an unreadable or past date, or a question without an answer | Fix it from what the student said, or ask for the one missing piece |

If the course materials don't cover a topic, say so and ask the student for notes or slides instead of inventing
questions. Never make up exam dates; use only what Canvas, the calendar or the student said.

## With Radar Autopilot

If the student turned on Radar Autopilot, its scheduled sweeps already run this Skill, so don't offer this Skill's own
recurring check-in. Reminders and calendar entries for new finds are covered by the student's autopilot yes, so create
them without asking again (phone calls only if the student left calls on). Sending, posting, submitting, registering
and paying still need a yes every time.

## Outside Cubbie

Without Canvas, ask for exam dates and paste-in notes. Without scheduled check-ins, give the student the countdown
dates so they can set reminders themselves, and run practice whenever they ask.
