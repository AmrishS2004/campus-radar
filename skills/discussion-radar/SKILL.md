---
name: discussion-radar
description: Texts the student what matters on class discussion boards, finds answers in existing Ed threads, and reminds them of Yellowdig and Harmonize deadlines that never show up. If nobody asked their question yet, it drafts an Ed post and posts it only after the student's yes. Use whenever the student mentions Ed, Ed Discussion, Edstem, Yellowdig, Harmonize, Packback, Perusall, a class discussion board, discussion posts or replies, participation points, "is there anything new on Ed", or has a question about a course (homework, exam, policy) that classmates or TAs may have already answered.
---

# Discussion Radar

A lot of what matters in a course happens on discussion boards, and none of them reach the student well. On Ed, the
TA's answer that changes the homework is buried under 200 threads. On Yellowdig and Harmonize it's worse: points and
reply windows count toward the grade, but there are no deadlines in Canvas and no notifications, so students have to
remember to go check. Discussion Radar watches the boards and texts the student only what matters, when it matters.

## When to use

- "anything important on Ed?"
- "for HW 5 can we assume the graph is connected?" (a course question that may already be answered on Ed)
- "post this question on Ed for CSE 310"
- "I keep forgetting my Yellowdig posts" / "when is my Harmonize reply due?"
- The daily Ed digest and weekly participation check-ins below, and Sunday Radar's brief

## Part 1: Ed Discussion

### Key

This part needs the student's own Ed API token, saved in Cubbie as `ED_API_TOKEN`. They create it at
https://edstem.org/us/settings/api-tokens (free, about a minute: sign in to Ed, create a token, copy it). If it isn't
saved yet, send the student the secure link to save it. Never ask them to paste the token into the chat.
Ed's API is in beta and community-documented, so if it starts failing, say so plainly rather than guessing.

Run every command from this Skill's folder, naming the key so the command receives it:

```bash
ED_API_TOKEN="$ED_API_TOKEN" python3 scripts/ed.py <command> ...
```

| Goal | Command (after the key part above) |
| --- | --- |
| The student's Ed courses and ids | `courses` |
| Important threads | `digest --course all --since <ISO date of the last digest>` |
| Has someone asked this already? | `search --course "<course code or id>" --query "<the student's question>"` |
| Read a thread with its answers | `thread --id <thread id>` |
| Post a question (only after the student's yes) | `post --course "<code or id>" --title "<title>" --body "<text>" --category "<category>" [--anonymous] [--private] --confirm` |

`--sample` on `courses`, `digest`, `search` or `thread` uses `assets/sample_ed.json` and needs no token.
Students at Australian Ed instances set `ED_REGION=au` in front of the command.

### Important news

1. Run `digest` for all courses since the last digest (the first time, the last 7 days). It ranks threads by what
   usually matters: staff announcements, pinned posts, posts by staff, and threads about exams, deadlines,
   extensions, corrections, room changes or solutions.
2. For each item worth texting, read it with `thread` if the title alone doesn't say what changed.
3. Text at most three items, each one line saying what changed and the course, with the link on its own line.
   If a deadline or exam date changed, offer to update reminders (and hand exam dates to Exam Radar if installed).
4. Offer a daily digest once (default 6 pm), worded so it stands alone: "Discussion Radar daily: run the Ed digest
   since yesterday and text only what changed for the student." Create it only after a yes. Skip the text when
   nothing important came up.

### The student's question

When the student asks something about a course that classmates or staff could have answered (homework
clarifications, exam scope, policies, setup problems):

1. Run `search` for that course with the question in the student's words. Also try once with different key words
   if the first search finds nothing.
2. **Found a match**: the percentage is only word overlap, so check that the thread really asks the same thing before
   using it. Run `thread` on the best one or two matches. If there's an accepted, endorsed or staff answer,
   text it in a sentence or two with the link. If classmates answered but staff didn't, say that it's a student
   answer. If the match has no answer yet, tell the student and offer to follow it.
3. **No match (NO_MATCH)**: draft a short, clear Ed post: a specific title, the question, what the student already
   tried or checked (ask them in one question if that's missing), and no graded-solution code or answers. Pick the
   category from the "Categories seen" line. Show the draft, and ask whether to post it normally, anonymously to
   classmates, or privately to staff.
4. Post only after the student says yes to that draft, by running `post` with `--confirm`. Text the link. Offer to
   check back for an answer: a reminder later the same day to run `thread` on the new id and text the answer if
   one arrived.

## Part 2: Yellowdig, Harmonize and other boards without notifications

These boards have no student API, so work from what Cubbie can see: Canvas, the student's email, and the board
itself in Cubbie's browser when the student wants that.

### Find the rules

For each course that uses a board (look for Yellowdig, Harmonize, Packback, Perusall or a graded discussion tool in
Canvas modules, assignments and the syllabus):

1. Read the syllabus, the board's Canvas assignment, and the course's announcements for the participation rules:
   - Yellowdig: usually a weekly point goal (for example 1,000 points by Sunday 11:59 pm), earned by posting,
     commenting and getting reactions.
   - Harmonize and graded discussions: usually an initial post deadline plus reply deadlines ("post by Wednesday,
     reply to two classmates by Sunday", or "reply within 24 hours").
2. Work out the real deadlines for the next two weeks in the student's time zone, even when Canvas shows only one
   due date or none.
3. Confirm the rules with the student in a short text before scheduling anything: "Harmonize in COM 230: initial
   post Wed 11:59 pm, 2 replies by Sun 11:59 pm, weekly. Want reminders?" If the rules aren't written anywhere,
   ask the student what they are.

### Remind

With a yes, create recurring reminders, each worded so it stands alone later:

- **Initial post**: the evening before the post deadline, and 3 hours before it.
- **Replies**: the morning of the reply deadline, and 3 hours before it.
- **"Reply within 24 hours" rules**: when the window starts (from the rule, or when a reply-to-you email arrives),
  remind at 12 hours and 20 hours into the window.
- **Yellowdig weekly points**: a midweek nudge to post (Wednesday) and a last-call reminder the day the week ends.

Example: "Discussion Radar: COM 230 Harmonize, 2 replies to classmates due tonight 11:59 pm."

### Use the inbox

Yellowdig and Harmonize can email notifications when someone replies to or mentions the student. Check the
student's email for these during the daily check-in. A reply to the student's post can start a reply window or earn
easy points, so text it with the link. If the student gets no such emails, tell them once that turning on email
notifications in the board's settings lets Cubbie catch replies too.

### Check progress (optional)

If the student wants their real point total or what's still missing, open the board from its Canvas link in Cubbie's
browser. The student signs in themselves (secure login page or taking over the browser, including any two-factor
step). Read only the weekly points or the list of required posts and replies, then text a one-line status
("Yellowdig: 620 of 1,000 points this week, 2 days left"). Never post on these boards for the student.

## Replies

- Short, plain text, no Markdown in texts. One item per line, course first, links on their own line.
- Quote at most a sentence of someone's post; summarize the rest.

## When something fails

| Exit code | Meaning | What to do |
| --- | --- | --- |
| 2 | No courses, no match (`NO_MATCH`), nothing important, or an unknown course or thread | For a question, go to the drafting step; otherwise say nothing new in one line, only when asked |
| 3 | Bad input, or a post without `--confirm` | Fix the command; post only after the student's yes |
| 4 | `ED_API_TOKEN` not saved | Send the secure link to save the Ed token, with the page where it's created |
| 5 | Token rejected | Ask the student to create a new token and save it through the secure page |
| 6 | Ed unreachable or another Ed error | Say Ed isn't responding right now and try once more later; don't retry in a loop |

Never invent an answer to a course question. If Ed and the course materials don't answer it, say so and offer to post.

## Outside Cubbie

With `ED_API_TOKEN` set in the shell, the Ed commands work anywhere Python 3 runs. Without reminders, list the
discussion deadlines so the student can set their own.
