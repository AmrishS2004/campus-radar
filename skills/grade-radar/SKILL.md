---
name: grade-radar
description: Checks each new Canvas grade against the rubric and syllabus, flags points that look wrong, and drafts a regrade request before the window closes. It also works out exactly what the student needs on the final. Use whenever a grade posts or the student mentions a grade, says points were taken off unfairly, asks about a regrade, asks "what do I need on the final", "can I still get an A", what-if scores, or their current grade in a course.
---

# Grade Radar

Grading mistakes happen, and most students never catch them, or catch them after the regrade window in the syllabus
has quietly closed. Grade Radar looks at each new grade the day it posts, tells the student when something doesn't
add up and how long they have to ask, and keeps the "what do I need on the final" math exact.

## When to use

- A new grade appears in Canvas (from the daily check-in below)
- "I got a 72 on the midterm, that seems low"
- "they took 5 points off for something I did"
- "can I still get an A in CSE 310?" / "what do I need on the final?"
- "what if I get an 85 on the final?"

Do not use it to argue about grades in general or to email anyone without the student's yes.

## Steps

### 1. Watch for new grades (optional daily check-in)

Offer once: "Want me to check each new grade the day it posts? I'll only text if something looks off or a regrade
window is closing." With a yes, create a daily check-in at a quiet time the student picks (default 6 pm), worded so
it stands alone: "Grade Radar daily: check Canvas for newly graded work since the last check and review each one."
Remember which graded assignments were already reviewed so each grade is checked once.

If Canvas isn't connected, ask the student to connect it and stop. They can still paste a grade and feedback.

### 2. Check a grade

For each newly graded assignment, quiz or exam:

1. Read the score, the instructor's comments, the rubric and the rubric ratings if Canvas has them, and the
   assignment instructions. Read the student's submission when it's available.
2. Check the arithmetic first: rubric ratings that don't add up to the score, points deducted twice for the same
   issue, a late penalty applied to an on-time submission, or a score that doesn't match the posted total.
3. Then check substance, carefully and humbly: a rubric criterion marked missing that the submission clearly
   contains, or a deduction that contradicts the instructions or an announcement.
4. Find the regrade policy in the syllabus or the announcements: how many days after grades post, and how to ask
   (email, Canvas comment, form, office hours). Work out the exact closing date from when the grade posted.
5. If nothing looks wrong, don't text about it, unless the student asked. If something looks off, text one short
   summary: what looks wrong, how many points, and when the window closes.

Only flag things you can point to in the rubric, instructions or submission. When unsure, say "might be worth asking
about" rather than "this is wrong". Never suggest asking for points the student didn't earn.

### 3. Help with the regrade

If the student wants to ask:

1. Set a reminder for the day before the window closes, if it's more than a day away, worded so it stands alone:
   "Grade Radar: regrade window for CSE 310 HW 4 closes tomorrow 11:59 pm. Ask the student whether they sent it."
2. Draft the request: polite, short, specific. Name the assignment, quote the rubric line or instruction, point to
   where the submission meets it, and ask the grader to take another look. No demands, no grade-grubbing tone.
   Use Cubbie's usual way of drafting professor or TA emails when the request goes by email; use a Canvas comment
   draft if the syllabus says to ask there.
3. The student sends it. Never send or post it without their yes.

Example draft:

```text
Hi Professor Lee, could you take another look at HW 4, problem 3? The rubric gives 5 points for "states the
recurrence and solves it." My submission states the recurrence on page 2 and solves it with the master theorem
right below, but the rubric shows 0 of 5 for that line. Thanks for checking!
```

### 4. What do I need on the final

1. Read the course's grades from Canvas: every assignment group with its weight (or a points-only course), each
   item's earned and possible points, excused items, and any "drop lowest" rules. Take the letter cutoffs from the
   syllabus; leave them out to use the usual 93/90/87/83/80/77/70/60 scale, and say so.
2. Write them to a JSON file shaped like `assets/sample_grades.json`: `scheme` is `weighted` or `points`; each group
   has `name`, `weight` (weighted only), optional `drop_lowest`, and `items` with `name`, `earned` (null if not
   graded yet) and `possible`; mark the final's group with `"final": true`.
3. Run from this Skill's folder:

   ```bash
   python3 scripts/grade_math.py need --file <grades.json>
   ```

   For a what-if, add `--final-score <percent>`. Try it without data with `--sample`.
4. Text the current grade and the two or three letters that matter (the one they're near, the one above, the one
   below). Include any `Note:` line about assumptions in one short sentence.

If Canvas's own total differs from the script's current grade by more than a point, say so and ask the student to
check whether some grades are hidden or the syllabus weights differ from Canvas.

## Replies

- Short, plain text, no Markdown. Lead with the number or the problem.
- "HW 4 looks 5 points short: the rubric shows 0/5 for the recurrence but it's on page 2. Regrades close Thu.
  Want a draft?"
- "CSE 310 now: 82.7% (B-). On the final: 84% for a B, 74% to keep a B-. An A is out of reach."

## When something fails

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 3 | The grade file is missing something (weights, possible points, the final's group) or there's no graded work yet | Re-read Canvas for the missing piece, or ask the student; never guess weights |

If the syllabus has no regrade policy, say so and suggest asking within a week, which is common, by the method the
course uses for questions.

## With Radar Autopilot

If the student turned on Radar Autopilot, its scheduled sweeps already run this Skill, so don't offer this Skill's own
recurring check-in. Reminders and calendar entries for new finds are covered by the student's autopilot yes, so create
them without asking again (phone calls only if the student left calls on). Sending, posting, submitting, registering
and paying still need a yes every time.

## Outside Cubbie

Without Canvas, ask the student to paste the score, rubric and feedback, or their grade breakdown, and build the
JSON file from that.
