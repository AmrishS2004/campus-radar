---
name: group-project-receipts
description: Keeps a dated log of who did what in a student's group project and turns it into calm, evidence-backed receipts for peer evaluations. Use whenever the student mentions a group project, teammates or a group member not doing their part, wants to log what they did ("finished slides 5 to 9"), says a teammate promised something ("Jake said he'd do the intro by Thursday") or skipped a meeting, sends a screenshot of their part of the work, needs a nudge for a quiet teammate, or has a peer evaluation or peer review coming up. Use it even when the student is just venting about a group member, since that is often the moment worth logging.
---

# Group Project Receipts

Group projects go wrong quietly. Nobody remembers who built the template or who promised the intro slides three
weeks ago, and when peer evaluations open, the student who did the work has only a feeling. This Skill keeps a
dated record as the project happens, so the student ends up with facts instead of a feeling.

It does three things:

1. **Logs** what the student did, what teammates did, what was promised and what was missed, in a few words per text.
2. **Follows up** on promises and on teammates who have gone quiet, with nudges the student sends themselves.
3. **Hands over receipts** when peer evaluations or the deadline come around: a clean contribution record as a PDF,
   plus drafted peer evaluation answers.

## When to use

- "starting a group project for MKT 300 with Priya, Jake and Sam"
- "finished slides 5 to 9 tonight, took like 3 hours"
- "Jake said he'd do the intro slides by Tuesday"
- "Sam skipped the meeting again and isn't answering the group chat"
- A screenshot of a shared doc, a commit list or a group chat, with or without a caption
- "Jake hasn't done anything, what do I say to him?"
- "peer evals are due Monday, help"

Do not use it for solo assignments, for grading or ranking teammates on the student's behalf, or for contacting
teammates directly. Cubbie only texts its own student; everything addressed to a teammate is a draft the student sends.

## The log script

Every project's log is kept by `scripts/receipts.py` (Python 3, standard library only, nothing to install). It
stores each project under `~/.config/group-project-receipts/`, so the log survives restarts and Skill updates.

Always pass the student's current local date and time as `--now` (ISO with UTC offset, for example
`--now 2026-10-24T20:15-07:00`), because the sandbox clock may be in another time zone. Run commands from this
Skill's folder. `--project` can be left out when the student has only one active project; otherwise use the
project's name or a clear part of it.

| Goal | Command |
| --- | --- |
| Start a project | `python3 scripts/receipts.py new --project "<name>" --course "<course>" --members "Priya,Jake,Sam" --due <YYYY-MM-DD> --peer-eval <YYYY-MM-DD> --now <now>` |
| Log something | `python3 scripts/receipts.py log --project "<name>" --who <me or teammate> --kind <kind> --text "<what happened>" --now <now>` |
| ...that happened earlier | add `--at <when it happened>` (for "yesterday", "last night", "at Monday's meeting") |
| ...with time spent | add `--hours <number>` |
| ...a promise | `--kind promised --by <date it was promised for>` |
| ...with a screenshot or file | add `--evidence <path to the saved file> --evidence-desc "<one line describing it>"` |
| A promise was kept | `python3 scripts/receipts.py kept --project "<name>" --id <n> --now <now>` |
| A promise was not done | `python3 scripts/receipts.py broke --project "<name>" --id <n> --note "<short reason if given>" --now <now>` |
| Fix a wrong entry | `python3 scripts/receipts.py remove --project "<name>" --id <n>` |
| Teammates or dates changed | `python3 scripts/receipts.py members --project "<name>" --add "<name>" --remove "<name>" --due <date> --peer-eval <date>` |
| What needs attention | `python3 scripts/receipts.py status --project "<name>" --now <now>` |
| The full record | `python3 scripts/receipts.py summary --project "<name>" --student "<student's first name>" --now <now>` |
| All projects | `python3 scripts/receipts.py list` |
| Project finished | `python3 scripts/receipts.py archive --project "<name>"` |

Kinds:

- `did`: finished work ("built the deck template", "fixed the login bug", "wrote the methods section")
- `meeting`: attended or ran a meeting
- `message`: a message that matters ("said he'd catch up this weekend", "I reminded everyone in the group chat")
- `promised`: someone committed to something by a date (needs `--by`)
- `missed`: a skipped meeting, a missed deadline, no reply
- `note`: anything else worth remembering

To try the script without touching real data, add `--sample` to `status`, `summary` or `list`. It uses
`assets/sample_project.json` and saves nothing.

## Steps

### 1. Start a project

When the student first mentions a group project, or logs something for a project the script does not know:

1. Get the project name and course from what they said. Ask only for what is missing, one question at a time.
2. Look in the student's Canvas for the matching group assignment: its due date, and any peer evaluation or peer
   review assignment with its due date. If Canvas shows the student's group members, use them as the team.
   If Canvas is not connected or shows nothing, ask the student for the teammates' first names and the due date,
   and carry on without a peer evaluation date.
3. Confirm in one line ("Logging MKT 300 pitch: you, Priya, Jake, Sam. Due Nov 6, peer evals Nov 9. Right?"),
   then run `new`.
4. Offer the check-ins in step 5 once. Create them only after the student says yes.

### 2. Log what happens (the main loop)

Most texts the student sends are entries. Turn each one into one or more `log` commands without making the
student fill in a form:

- One text can hold several entries. "Met with Priya, Sam didn't show, I finished the budget sheet" is three entries.
- `--who me` for anything the student did; a teammate's name for theirs. If a name is not on the team, ask whether
  to add them, then run `members --add`.
- Use `--at` when they say when it happened. Use `--hours` only when they mention time spent.
- A teammate's good work gets logged too. A fair record is what makes it believable later.
- If the student is venting ("Jake is useless, he did NOTHING"), log the concrete fact underneath it, phrased
  neutrally, and confirm it: "Logged: Jake, intro slides not started as of today. Sound right?" Ask what
  specifically happened if there is no concrete fact yet.
- Write entries as plain facts, never judgments: "didn't reply to 3 messages since Monday", not "lazy".
  Use only what the student told you or what a screenshot clearly shows. Never invent details.

After logging, reply with one short confirmation line. Don't recap the whole log.

### 3. Screenshots, files and voice notes

When the student sends a screenshot (a shared doc, slides, a commit history, a group chat) or a file:

1. Read it and write one neutral line describing what it shows, with any visible names and dates
   ("Google Slides version history: Amrish edited slides 5 to 9 on Oct 19").
2. Save the file to the student's drive and log it with `--evidence <path> --evidence-desc "<that line>"`, using the
   kind that fits (usually `did`). The script keeps its own copy.
3. If it's a group chat screenshot, log only facts that matter for the project (who agreed to what, who didn't reply),
   and never copy private messages unrelated to the project.

Transcribe voice notes first, then log them like a text.

### 4. Follow up on promises

When a teammate (or the student) commits to something, log it as `promised` with `--by`.

At setup, ask once whether the student wants a check-back after each promise deadline, and remember the answer.
If yes, create a one-time reminder for the morning after each `--by` date, worded so it makes sense on its own:
"Group Project Receipts: did Jake finish the intro and problem slides for Marketing Final Pitch (promise #3, due
Oct 20)? Reply yes or no." When the student answers, run `kept` or `broke` for that id. If they say "kind of",
ask what was done, log it as `did` for that teammate, and leave the promise open or mark it `broke` with a note.

### 5. Check-ins

Offer one recurring check-in per active project. Suggest twice a week at 8 pm (Mondays and Thursdays) and let the
student change it. Each check-in runs `status` and texts at most three lines: the most overdue promise, anyone
quiet for 4 or more days, and "Anything to log?" Word it so it stands alone later:
"Group Project Receipts check-in for Marketing Final Pitch: run status and ask the student what to log."

If `status` says nothing needs a nudge, keep the check-in to one line asking whether there's anything to log.

Also offer a one-time reminder two days before the peer evaluation due date to build the receipts (step 7).
Stop all check-ins for a project when it's archived.

### 6. Nudge a quiet teammate

When `status` shows an overdue promise or a quiet teammate, or the student asks what to say, draft a message the
student can copy and send. Offer up to three, from gentle to firm, each two or three sentences, in a casual
student voice:

1. **Friendly check-in**: assumes good intent, asks how it's going, restates the promise and date.
2. **Clear ask**: names the task and a new specific time, offers to help or swap parts.
3. **Group-chat version**: a neutral update to the whole group that lists who has what and by when.

Never send it. After the student says they sent one, log it as `--who me --kind message`
("nudged Jake about the intro slides"). If a teammate has done nothing close to the deadline, offer to draft a short
factual email to the instructor with the record attached, using Cubbie's usual way of drafting professor emails, and
send only after the student's yes.

### 7. Build the receipts

Two days before the peer evaluation (from the check-in), or whenever the student asks for their receipts:

1. Run `summary` with the student's first name. It prints Markdown: a who-did-what table, the student's own work,
   commitments and whether they were kept, a dated timeline and the evidence on file.
2. Make a PDF from that Markdown, titled "Contribution record: <project>", and send it with a one-line text.
   Attach the evidence screenshots in the same PDF when there are any.
3. Look in Canvas for the peer evaluation questions or rubric. Draft a short, factual answer for each teammate based
   only on the record ("Priya delivered the competitor research a day early and added the survey chart"). Credit
   what teammates did well before stating what was missed. Send the drafts as text or a short doc.
4. The student submits peer evaluations themselves. Never submit or fill in a Canvas form.

When the project is done, offer to archive it.

## Replies

- Short, plain text, no Markdown symbols in texts. One idea per message.
- After logging: one line ("Logged: you finished slides 5 to 9, 3.5h. That's 3 contributions so far.").
- Lead with what needs action. Show at most three items in a text; anything longer goes in the PDF.
- Calm and factual about teammates, even when the student is angry. Supportive toward the student.
- Ask one question at a time, with a default they can accept with "yes".

Example check-in:

```text
Marketing Final Pitch check-in:
- Jake's intro slides were due Tue, still open
- Sam quiet since Sat
Want a nudge for Jake? Anything to log?
```

## When something fails

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 2 | Project not found, or several active and none named | Text the project names the script printed and ask which one, or offer to start a new one |
| 3 | Bad input: unknown teammate, unreadable date, missing detail, unknown entry id | Fix it from what the student said, or ask the one missing thing; offer `members --add` for a new name |
| 4 | A project with that name already exists | Ask whether to log to the existing one or pick a new name |

If the script fails for another reason, tell the student the log couldn't be saved right now and keep their text so
it can be logged on the next try. Never claim something was logged when the command failed.

## With Radar Autopilot

If the student turned on Radar Autopilot, its scheduled sweeps already run this Skill, so don't offer this Skill's own
recurring check-in. Reminders and calendar entries for new finds are covered by the student's autopilot yes, so create
them without asking again (phone calls only if the student left calls on). Sending, posting, submitting, registering
and paying still need a yes every time.

## Outside Cubbie

The script works anywhere Python 3 runs. Without Canvas, ask the student for the due dates and teammates. Without
reminders, list the promise dates and check-in times so the student can set reminders themselves. Without document
tools, give the summary Markdown as it is.
