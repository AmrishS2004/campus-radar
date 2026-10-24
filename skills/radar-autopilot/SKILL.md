---
name: radar-autopilot
description: Turns every Campus Radar Skill on at once with one yes, then runs them on a schedule so the student hears only what needs them, and checks itself when asked. One morning sweep, one evening sweep, daily exam practice and a Sunday brief with a flowchart of the week replace a dozen separate check-ins. Use whenever the student says "start Campus Radar", "turn on autopilot", "automate this", "set everything up", "run it automatically", "pause", "stop" or "resume Campus Radar", wants to change when it texts or calls, asks how Campus Radar works, or asks to check, test or diagnose Campus Radar ("is everything working?").
---

# Radar Autopilot

The other Campus Radar Skills each offer their own check-in, which means a lot of separate questions before anything
runs on its own. Autopilot replaces all of that with one setup message and one yes. After that, Campus Radar works in
the background: it reads Canvas, email and Ed twice a day, sets the reminders it finds, and texts the student only when
something needs them.

## When to use

- "start Campus Radar" / "turn on autopilot" / "set everything up"
- "pause Campus Radar" / "resume" / "stop calling me" / "move the morning text to 9"
- "how does Campus Radar work?"
- "check Campus Radar" / "is everything working?"

## 1. Turn on autopilot

1. Check the connections: read the student's Canvas courses and today's Google Calendar. Ed is optional: it needs
   `ED_API_TOKEN` (see Discussion Radar). Note what's missing, but don't block on Ed.
2. Send one setup message with the schedule below and the defaults, and ask for one yes. For example:

   ```text
   Campus Radar autopilot:
   - 7:30 am: morning sweep (email, clubs, what's due today)
   - 6 pm: evening sweep (new slides, grades, Ed)
   - 8 pm: 3 practice questions, only when an exam is close
   - Sun 7 pm: your week as a text + flowchart
   - Reminders for deadlines it finds, calls on exam mornings
   Texts only when something needs you. Never sends, posts or submits anything without asking.
   Yes to turn it on? (Or tell me what to change.)
   ```

3. If Canvas or Google isn't connected, say which and offer to connect it first; autopilot can start without Ed.
4. On yes, create the four scheduled check-ins below, each worded so it stands alone later, and remember the
   student's settings (times, calls on or off, quiet hours, paused or not). If the student changes anything ("no
   calls", "morning at 9"), apply it and confirm in one line.
5. Send a flowchart of their autopilot so they can see how it runs: write the schedule as steps (one step per check-in
   with its time) and run the Sunday Radar Skill's flowchart script (its `flow.py steps --file <autopilot.json>`
   command, from that Skill's folder) with the title "Your Campus Radar autopilot". Send the PDF with one line:
   "Autopilot is on."

## 2. The schedule

The student's one yes covers everything in this section, including creating the reminders and calendar entries the
sweeps find. It never covers sending an email, posting on Ed or any board, submitting work, registering, paying, or
changing calendar events Campus Radar didn't create. Those still need a yes each time.

Quiet hours: no texts from 11 pm to 7 am, except reminders and calls the student set for that time. Budget: at most
three autopilot texts a day; when there's more, fold it into the next sweep.

**Morning sweep (7:30 am daily).** "Radar Autopilot morning sweep: run Inbox Radar, Club Radar and today's deadlines,
then text one summary only if something needs the student."
- Inbox Radar: sort new email, save reply drafts in Gmail, update the "Campus Radar" Google Tasks list.
- Club Radar: new club events, registration deadlines and changes; add events for clubs the student marked important
  to Google Calendar, and move reminders when a meeting changes.
- Today: anything due today or tomorrow in Canvas, discussion board deadlines, and overdue group project promises
  (Group Project Receipts `status` for each active project).
- One text, at most 6 lines, most urgent first. Nothing to say means no text.

**Evening sweep (6 pm daily).** "Radar Autopilot evening sweep: run Slide Radar on today's new course materials, Grade
Radar on new grades, Discussion Radar's Ed digest and reply emails, and Exam Radar's exam search, then text one
summary only if something needs the student."
- Slide Radar: tasks in new slides or files that aren't in the Assignments tab. Set a reminder the evening before each.
- Grade Radar: check new grades; flag only points that look wrong, with the regrade deadline.
- Discussion Radar: important Ed posts since yesterday, Yellowdig or Harmonize reply windows, reply-to-you emails.
- Exam Radar: new or moved exam dates; save them and add them to Google Calendar.
- Professor Radar: if the student had office hours today, ask the one-line question about it.
- One text, at most 6 lines. Nothing to say means no text.

**Practice (8 pm daily, only with an exam in the next 21 days).** "Radar Autopilot practice: if an exam is within 21
days, run Exam Radar's countdown and send today's 3 practice questions." Skip silently on days with no exam coming.

**Sunday brief (7 pm Sunday).** "Radar Autopilot Sunday brief: run Sunday Radar for the coming week, including the
week flowchart." The flowchart PDF goes with the text.

**Reminders the sweeps create** (covered by the yes): the evening before and 3 hours before each hidden, discussion or
to-do deadline; the evening before each exam; a wake-up call on exam mornings and a call 20 minutes before meetings of
clubs marked important, only if calls are on. Each reminder names the Skill, the course and the item.

## 3. Controls

- **Pause**: "pause Campus Radar" deletes the four scheduled check-ins and remembers that autopilot is paused.
  Reminders already set for specific deadlines stay unless the student says to clear them too.
- **Resume**: recreate the check-ins with the saved settings.
- **Change**: times, quiet hours, calls on or off, the practice question count, or skipping a sweep. Update only the
  check-ins that changed.
- **Status**: list what's scheduled, when the next sweep runs, and what's paused.
- **Stop for good**: same as pause, plus clear the saved settings, after one confirmation.

## 4. Health check ("check Campus Radar")

Run the automatic check, then add what only Cubbie can see:

1. Run from this Skill's folder: `ED_API_TOKEN="$ED_API_TOKEN" python3 scripts/selfcheck.py --live-ed`
   It confirms all eleven Skills are installed, runs every script in its sample mode (nothing saved, no network),
   and tests the Ed token if one is saved. It prints one line per Skill.
2. Check Canvas (list the student's courses) and Google (read today's calendar and the latest email subject line).
3. If autopilot is on, compare the scheduled check-ins with the saved settings and fix any that are missing or
   duplicated, telling the student what changed.
4. Reply with a short report: one line each for Skills, Canvas, Google, Ed and autopilot, using OK, a problem with its
   one-step fix, or "off". Put the full script output in a document only if something failed.

```text
Campus Radar check:
- Skills: all 11 OK
- Canvas: OK, 4 courses
- Google: OK
- Ed: token works, 2 courses
- Autopilot: on, next sweep 6 pm
```

| selfcheck.py exit code | Meaning | What to do |
| --- | --- | --- |
| 0 | Every Skill and script passed | Report OK |
| 1 | At least one Skill is missing or a script failed | Report each FAIL line with its fix (usually: text the repo link again with "update to this") |

## 5. "How does Campus Radar work?"

Answer in three short lines (it reads Canvas, email and Ed twice a day; texts only when something needs you; never
sends or submits without asking), then offer the autopilot flowchart from step 1.5.

## Replies

- Short, plain text, no Markdown in texts. Lead with what needs the student.
- One sweep, one text. Never send a text that only says nothing happened, unless the student asked.

## Outside Cubbie

Without scheduled check-ins, give the student the schedule so they can set their own reminders, and run any sweep
when they ask ("run my evening sweep").
