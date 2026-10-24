---
name: professor-radar
description: Logs the student's office hours, strong grades and projects with each professor, then picks who knows them best and builds a brag sheet when they need a recommendation letter. It also drafts the request email. Use whenever the student mentions office hours, talking to a professor, a professor praising their work, needing a recommendation or reference letter, asking who to ask for a rec, or applying to internships, research, scholarships or grad school that need letters.
---

# Professor Radar

Two years from now, a student will need a recommendation letter, and the professor will barely remember them. The
result is a generic letter. Professor Radar fixes that by quietly writing down the moments that matter as they
happen, so when the time comes the student knows exactly who to ask and hands that professor a page of specifics.

## When to use

- "just went to Prof. Lee's office hours"
- "Dr. Patel said my design doc was the best in the class"
- "I need a recommendation letter for a research internship, who should I ask?"
- "make a brag sheet for Prof. Lee"
- A strong grade that Grade Radar or the student mentions

## The log script

`scripts/professors.py` (Python 3, standard library only) keeps the log in `~/.config/professor-radar/log.json`.
Run it from this Skill's folder and pass the student's local date and time as `--now` (ISO with UTC offset).

| Goal | Command |
| --- | --- |
| Log an interaction | `python3 scripts/professors.py log --prof "Prof. Lee" --course "CSE 310" --kind oh --text "<what happened>" --now <now>` |
| ...from earlier | add `--at <when it happened>` |
| Who knows me best | `python3 scripts/professors.py rank --top 3 --now <now>` |
| Brag sheet facts | `python3 scripts/professors.py brag --prof "Lee" --student "<first name>" --purpose "<what the letter is for>" --deadline <YYYY-MM-DD>` |
| Everyone logged | `python3 scripts/professors.py list` |
| Fix a wrong entry | `python3 scripts/professors.py remove --id <n>` |

Kinds: `oh` (office hours or a one-on-one), `grade` (a strong grade or score), `project` (notable work they saw),
`research` (worked with them on research), `email` (a meaningful exchange), `class` (stood out in class), `note`.
Ranking weighs research, office hours and projects most, and recent contact more than old contact.
`--sample` on `rank`, `brag` or `list` uses `assets/sample_log.json` and saves nothing.

## Steps

### 1. Capture the moments

- **Office hours.** Offer once to watch the student's Google Calendar and Canvas course calendars for office hours
  they attend. With a yes, after each office hours event the student had, text one short question an hour later:
  "How was Prof. Lee's office hours? One line on what you talked about and I'll save it." Log the answer as `oh`.
  If they don't answer, let it go. Don't ask again for that visit.
- **Strong grades.** When a grade of about 90% or higher posts on a major assignment or exam, or the student shares
  one, log it as `grade` with the score and anything notable (top of the range, a professor's comment).
- **Praise and emails.** When the student mentions a professor complimenting their work, or an email thread with a
  professor that went beyond logistics (Gmail), log it as `project`, `email` or `class`.
- Write entries as specific facts in the student's words, including names of projects and topics. Specifics are what
  make a letter strong.

Confirm each log with one line. Don't make the student fill in a form.

### 2. When they need a letter

1. Ask what it's for and the deadline, if they didn't say.
2. Run `rank` and suggest the top one or two, with the reason in a few words ("Prof. Lee: 2 office hours, a 94 on
   the midterm, the graph project she called out in lecture").
   If the log is thin, also look at Canvas for courses where the student did very well, and say the log is thin.
3. When they pick someone, run `brag` with the purpose and deadline. Turn its facts into a one-page brag sheet PDF:
   keep every fact as given, and add a short "What I'm applying for" and "What I'd love you to mention" section based
   on what the student tells you about the opportunity. Ask them for a resume if they want it attached.
4. Draft the request email: polite, short, asks whether they'd be comfortable writing a strong letter, gives the
   deadline and how to submit, and mentions the brag sheet is attached. Use Cubbie's usual way of drafting professor
   emails. The student sends it.
5. Offer two reminders: a gentle follow-up draft about one week before the deadline, and a thank-you note draft
   after it.

## Replies

- Short, plain text, no Markdown. One line per logged moment.
- "Saved: office hours with Prof. Lee about the graph project. That's 3 visits this semester."
- Never inflate. The brag sheet is only as good as it is true.

## When something fails

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 2 | No professors logged yet, or no match for a name or entry | Say what's logged (the script lists names) and offer to start from Canvas grades instead |
| 3 | Bad input, such as an unreadable date or missing text | Ask for the one missing piece |

## With Radar Autopilot

If the student turned on Radar Autopilot, its scheduled sweeps already run this Skill, so don't offer this Skill's own
recurring check-in. Reminders and calendar entries for new finds are covered by the student's autopilot yes, so create
them without asking again (phone calls only if the student left calls on). Sending, posting, submitting, registering
and paying still need a yes every time.

## Outside Cubbie

Without the calendar, the student logs visits by texting. Without document tools, give the brag sheet as text.
