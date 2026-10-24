---
name: sunday-radar
description: Sends one Sunday-evening text with the student's whole week and catches conflicts like a club meeting the night before a midterm. It pulls in Canvas deadlines, tasks hidden in slides, discussion board deadlines, exam countdowns, club events, to-dos from email, overdue group project promises and closing regrade windows, and saves the full week as a Google Doc. Use whenever the student asks "what does my week look like", "plan my week", "what's coming up", asks to see their week or an assignment as a flowchart or visual, wants a weekly summary or Sunday brief, or asks to set up a weekly check-in.
---

# Sunday Radar

The other Campus Radar Skills each watch one part of college life. Sunday Radar puts them together once a week, so
the student starts every week knowing exactly what's coming, what clashes, and what to do first. It's one text, not
twelve notifications.

## When to use

- "what does my week look like?"
- "set up a weekly summary"
- "plan my week" (for the overview; Cubbie's built-in study plan Skill handles detailed study schedules)
- The Sunday check-in below

## Steps

### 1. Set up the weekly brief

Offer once: "Want a quick brief every Sunday at 7 pm with your whole week?" Let the student pick the day and time.
Create the check-in only after a yes, worded so it stands alone: "Sunday Radar weekly: build the student's brief
for the coming Monday to Sunday and text it."

### 2. Gather the week (Monday to Sunday ahead)

Collect each part that's available. Skip a part quietly if its account isn't connected or its Skill isn't installed.

1. **Canvas**: assignments, quizzes and exams due this week across all courses, with submission status.
2. **Hidden tasks**: if Slide Radar is installed, follow its scan steps for the last 7 days of course materials and
   include anything not in the Assignments tab.
3. **Exams**: if Exam Radar is installed, run its `practice.py exams` command (from that Skill's folder, with
   `--now`) for exams in the next 14 days, and its `practice.py stats` command for any exam this week to name the
   weakest topic.
4. **Clubs**: if Club Radar is installed, follow its scan steps for this week's club meetings, events and
   registration deadlines.
5. **Group projects**: if Group Project Receipts is installed, run its `receipts.py status` command (from that
   Skill's folder, with `--now`) for each active project and include overdue promises and quiet teammates.
6. **Grades**: if Grade Radar is installed, include any regrade window that closes this week.
7. **Discussions**: if Discussion Radar is installed, include this week's Yellowdig, Harmonize or other board
   deadlines it scheduled, and run its Ed digest for the last 7 days for anything that changed a deadline or exam.
8. **To-dos**: if Inbox Radar is installed, include open items due this week from the "Campus Radar" list in Google
   Tasks, and any email still waiting on a reply.
9. **Google Calendar**: the student's events this week, to find conflicts.

### 3. Find conflicts and crunch

- A club event, social or shift that overlaps a class or exam.
- An evening event the night before an exam or a big deadline.
- A day with three or more deadlines or exams (the crunch day).
- A deadline with no time on the calendar to work on it before it's due.

For each conflict, suggest one fix in a few words ("skip the GBM or study Tue night instead", "start HW 5 Mon,
Wed is packed"). Offer to block study time in Google Calendar for the crunch day or the night before an exam, and
add blocks only after a yes.

### 4. Send the brief

The text holds only what matters most, in this order, at most 8 short lines:

1. The crunch day, if there is one.
2. Exams this week, with days left.
3. Deadlines this week, soonest first (hidden ones marked "slides", discussion posts marked with the board's name).
4. Conflicts, with the suggested fix.
5. Club events worth knowing, and any registration closing.
6. Overdue group promises, a regrade window closing, or an email still waiting on a reply.

Then send the week as a flowchart (see "The week flowchart" below), and save the full week as a Google Doc in the student's Drive (a folder named "Campus Radar"), titled
"Week of <Monday date>", with a section per day, and send the link on its own line. If Google Drive isn't
connected, send a PDF instead.

End with one question that has an easy yes: "Want me to block Tue 6 to 9 pm for midterm review?"

```text
Your week (Oct 26 to Nov 1):
- Crunch day Wed: CSE 310 HW 5 + MKT 300 pitch draft
- CSE 310 Midterm 2 next Tue, 9 days. Weakest: hash tables
- Thu: reflection due before lecture (slides)
- Robotics GBM Wed 7 pm clashes with HW 5 night
- AI Club trip sign-up closes Fri
- Jake's intro slides still overdue
Full week:
https://docs.google.com/document/d/...
Block Tue 6 to 9 pm for HW 5?
```

## The week flowchart

Students take in a week faster as a picture. After gathering the week, write it to a JSON file and run, from this
Skill's folder:

```bash
python3 scripts/flow.py week --file <week.json>
```

The file has `title`, `start` (the Monday, YYYY-MM-DD), `crunch` (the crunch day's date, if any) and `items`, each with
`date`, `time`, `kind` (`exam`, `deadline`, `hidden` for slide-only tasks, `discussion`, `club`, `todo`, `class` or
`block` for a study block), `title`, `course`, a short `note`, and `conflict` (the clash and its fix, only when there
is one). See `assets/sample_week.json`. The script prints the PDF's path; send the PDF with the brief. It needs no
packages, and `--sample` draws the sample week.

For one big assignment ("break HW 5 into steps", "show me a plan for my essay"), make a step-by-step flowchart instead:
steps from the instructions and slides, each with a day and rough minutes, ending at the due date. Write it like
`assets/sample_steps.json` and run `python3 scripts/flow.py steps --file <steps.json>`. Steps help the student plan
their own work; never put answers or graded solutions in them.

If the script fails (exit code 3 means a field is missing or a date is unreadable), fix the JSON and run it once more;
if it still fails, send the text brief alone.

## Replies

- Short, plain text, no Markdown in the text. One item per line.
- If the week is light, say so in one or two lines and skip the document.

## When something fails

- Canvas not connected: build the brief from what's available and say Canvas wasn't checked.
- A Skill's command fails: leave that part out and mention it in one line at the end.
- Nothing this week: "Quiet week: nothing due and no exams. Enjoy it."

## With Radar Autopilot

If the student turned on Radar Autopilot, its scheduled sweeps already run this Skill, so don't offer this Skill's own
recurring check-in. Reminders and calendar entries for new finds are covered by the student's autopilot yes, so create
them without asking again (phone calls only if the student left calls on). Sending, posting, submitting, registering
and paying still need a yes every time.

## Outside Cubbie

Without Canvas or Google, ask the student what's on their plate this week and organize it the same way.
