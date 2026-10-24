---
name: slide-radar
description: Finds homework and deadlines that professors mention only in lecture slides, files or announcements and that never show up in the Canvas Assignments tab. It also finds the real instructions for assignments whose Canvas description is empty or vague. Use whenever the student asks what's due, says they missed something that wasn't on Canvas, asks where the instructions for an assignment are, says an assignment has no details, asks "did the professor assign anything in the slides", or wants their courses checked for hidden work.
---

# Slide Radar

Plenty of professors announce work on slide 37 of Tuesday's lecture ("reflection due before Thursday", "read
chapter 6 for Monday", "bring a draft to lab") and never create a Canvas assignment for it. Others create an
assignment with a title and a due date but put the actual instructions in the slides. Students who look only at the
Assignments tab miss both. Slide Radar reads the rest of the course so they don't.

## When to use

- "what's due this week?" (run this alongside the normal assignment list)
- "the assignment says 'see lecture' but there's nothing there"
- "where are the instructions for Lab 4?"
- "did I miss anything in the slides?"
- The weekly scan below, and Sunday Radar's weekly brief

## Steps

### 1. Scan the course

If Canvas isn't connected, ask the student to connect it and stop. For each current course (or the one the student
named):

1. Read the Assignments tab: titles, due dates, descriptions and submission status.
2. Search the course materials posted or updated in the last 14 days (or since the last scan): lecture slides and
   PDFs in Files and Modules, course Pages, announcements, and the syllabus schedule for the coming two weeks.
3. Look for anything the student must do or bring, with a time attached: "due", "submit", "turn in", "bring",
   "read ... before", "prepare", "complete", "quiz on", "exam", "by Friday", "next class", "for Monday", a date, or
   a weekday. Work out the actual date from the slide's lecture date or the syllabus schedule.
4. Compare each find against the Assignments tab:
   - **Hidden task**: nothing in the tab matches it. Report it.
   - **Missing instructions**: an assignment in the tab with an empty, one-line or "see slides" description, where
     the slides or a page hold the real instructions. Report where they are and summarize them in two or three lines.
   - **Changed date**: an announcement or slide gives a different date than the tab. Report both dates and which
     source is newer.
   - Already in the tab with full instructions: skip it.
5. Remember what was already reported to the student, so the same hidden task isn't reported twice.

Be precise about the source: course, file name, and slide or page number. Only report what the material actually
says. If a slide is ambiguous ("homework next week?"), report it as "might be homework, worth asking" instead of
inventing a deadline.

### 2. Tell the student

Text the finds, most urgent first, at most three in the text. If there are more, put the full list in a short
document and send it with the text.

```text
Found 2 things that aren't in your Canvas Assignments tab:
- CSE 310: one-paragraph reflection, due before Thu's lecture (Lecture 14 slides, slide 37)
- MKT 300: read chapter 6 for Mon (Week 9 slides, slide 2)
Want reminders for both?
```

For missing instructions:

```text
Lab 4 has no details in Canvas, but Lab 4 slides (slides 3 to 6) spell it out: build a linked list with insert and
delete, include tests, submit a zip. Due Fri 11:59 pm.
```

### 3. Follow through

- With the student's yes, set a reminder for each hidden task (the evening before by default), worded so it stands
  alone later: "Slide Radar: CSE 310 reflection (Lecture 14 slide 37) is due before Thursday's lecture."
- Offer to add hidden deadlines to Google Calendar. Add them only after a yes.
- For a big assignment, offer a step-by-step flowchart of the instructions you found, made with the Sunday Radar
  Skill's flowchart script (its `flow.py steps` command, run from that Skill's folder), when that Skill is installed.
- If a find is an exam or quiz date, hand it to Exam Radar to save it and offer countdowns, when that Skill is
  installed.
- Offer a weekly scan once (default Sunday at 6 pm, before Sunday Radar's brief), worded so it stands alone:
  "Slide Radar weekly: scan every current Canvas course for tasks that aren't in the Assignments tab and text any
  new finds." Create it only after a yes. If a scan finds nothing new, don't text.

## Replies

- Short, plain text, no Markdown. Course first, then the task, the date, and the source in parentheses.
- Lead with the soonest deadline. Say clearly when nothing hidden was found.

## When something fails

- Canvas not connected: ask the student to connect it and stop.
- A file can't be opened or read: say which one, and ask the student to send a screenshot or the file if it matters.
- No new finds: "Checked all 4 courses, nothing hidden outside the Assignments tab this week."

## With Radar Autopilot

If the student turned on Radar Autopilot, its scheduled sweeps already run this Skill, so don't offer this Skill's own
recurring check-in. Reminders and calendar entries for new finds are covered by the student's autopilot yes, so create
them without asking again (phone calls only if the student left calls on). Sending, posting, submitting, registering
and paying still need a yes every time.

## Outside Cubbie

Without Canvas, ask the student to send the slides or files and scan those the same way.
