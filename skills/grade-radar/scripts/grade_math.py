#!/usr/bin/env python3
"""Grade Radar: exact current grade and what the student needs on the final.

Standard library only, no saved state. Cubbie writes the student's Canvas grades to a
JSON file (see assets/sample_grades.json) and passes its path.

  python3 scripts/grade_math.py need --file grades.json
  python3 scripts/grade_math.py need --file grades.json --final-score 82
  python3 scripts/grade_math.py need --sample

Exit codes: 0 ok, 3 bad or incomplete grade file.
"""

import argparse
import json
import math
import os
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_FILE = os.path.join(SKILL_DIR, "assets", "sample_grades.json")
DEFAULT_CUTOFFS = {"A": 93, "A-": 90, "B+": 87, "B": 83, "B-": 80, "C+": 77, "C": 70, "D": 60}


class UserError(Exception):
    pass


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise UserError("Can't find the grade file '%s'." % path)
    except json.JSONDecodeError as e:
        raise UserError("The grade file isn't valid JSON (%s)." % e)
    if not isinstance(data.get("groups"), list) or not data["groups"]:
        raise UserError("The grade file needs a non-empty 'groups' list.")
    scheme = data.get("scheme", "weighted")
    if scheme not in ("weighted", "points"):
        raise UserError("'scheme' must be 'weighted' or 'points'.")
    finals = [g for g in data["groups"] if g.get("final")]
    if len(finals) > 1:
        raise UserError("Mark only one group as the final.")
    for g in data["groups"]:
        if not isinstance(g.get("items", []), list):
            raise UserError("Group '%s' needs an 'items' list." % g.get("name"))
        if scheme == "weighted" and not isinstance(g.get("weight"), (int, float)):
            raise UserError("Group '%s' needs a numeric 'weight' for a weighted course." % g.get("name"))
        for it in g.get("items", []):
            if not isinstance(it.get("possible"), (int, float)) or it["possible"] < 0:
                raise UserError("Item '%s' in '%s' needs 'possible' points." % (it.get("name"), g.get("name")))
            if it.get("earned") is not None and not isinstance(it["earned"], (int, float)):
                raise UserError("Item '%s' has a non-numeric 'earned'." % it.get("name"))
    return data


def graded(group):
    items = [i for i in group.get("items", []) if i.get("earned") is not None and not i.get("excused")
             and i["possible"] > 0]
    drop = int(group.get("drop_lowest", 0) or 0)
    if drop and len(items) > drop:
        items = sorted(items, key=lambda i: i["earned"] / i["possible"])[drop:]
    return items


def ungraded(group):
    return [i for i in group.get("items", []) if i.get("earned") is None and not i.get("excused")]


def pct(items):
    possible = sum(i["possible"] for i in items)
    return (sum(i["earned"] for i in items) / possible * 100) if possible else None


def analyse(data):
    scheme = data.get("scheme", "weighted")
    groups = data["groups"]
    final = next((g for g in groups if g.get("final")), None)
    notes = []

    if scheme == "weighted":
        scored = [(g, pct(graded(g))) for g in groups]
        have = [(g, p) for g, p in scored if p is not None]
        if not have:
            raise UserError("No graded work yet, so there's no current grade to work from.")
        wsum = sum(g["weight"] for g, _ in have)
        current = sum(g["weight"] * p for g, p in have) / wsum
        # projection: every non-final group keeps its current average; empty ones assume the current grade
        total_w = sum(g["weight"] for g in groups)
        if abs(total_w - 100) > 0.5:
            notes.append("group weights add up to %g, not 100; worked with them as given" % total_w)
        fixed = 0.0
        for g, p in scored:
            if g is final:
                continue
            if p is None:
                notes.append("nothing graded yet in %s, assumed you score your current %.1f%% there" % (g["name"], current))
                p = current
            elif ungraded(g):
                notes.append("assumed you keep %.1f%% on the rest of %s" % (p, g["name"]))
            fixed += g["weight"] * p
        if final is None:
            return current, None, notes
        if graded(final):
            notes.append("the final group already has grades; treating the remaining final work as the unknown")

        def total_with(x):
            return (fixed + final["weight"] * x) / total_w

        def needed(c):
            return (c * total_w - fixed) / final["weight"] if final["weight"] else None
        return current, (total_with, needed, final), notes

    # points scheme
    all_graded = [i for g in groups for i in graded(g)]
    if not all_graded:
        raise UserError("No graded work yet, so there's no current grade to work from.")
    earned = sum(i["earned"] for i in all_graded)
    possible = sum(i["possible"] for i in all_graded)
    current = earned / possible * 100
    e_all, p_all = earned, possible
    for g in groups:
        if g is final:
            continue
        rest = ungraded(g)
        if rest:
            gp = pct(graded(g))
            gp = current if gp is None else gp
            notes.append("assumed you keep %.1f%% on the %d remaining item(s) in %s" % (gp, len(rest), g["name"]))
            p = sum(i["possible"] for i in rest)
            e_all += p * gp / 100
            p_all += p
    if final is None:
        return current, None, notes
    final_points = sum(i["possible"] for i in ungraded(final))
    if final_points <= 0:
        raise UserError("The final group needs an ungraded item with its 'possible' points.")
    e_fixed = e_all + sum(i["earned"] for i in graded(final))
    p_fixed = p_all + sum(i["possible"] for i in graded(final))
    total_p = p_fixed + final_points

    def total_with(x):
        return (e_fixed + final_points * x / 100) / total_p * 100

    def needed(c):
        return (c / 100 * total_p - e_fixed) / final_points * 100
    return current, (total_with, needed, final), notes


def cmd_need(args):
    data = load(SAMPLE_FILE if args.sample else args.file)
    cutoffs = data.get("cutoffs") or DEFAULT_CUTOFFS
    current, fin, notes = analyse(data)
    course = data.get("course", "This course")
    lines = ["%s: current grade %.1f%% (%s)" % (course, current, letter(current, cutoffs))]
    if fin is None:
        lines.append("No final exam is marked in the grade data, so this is the whole picture.")
    else:
        total_with, needed, final = fin
        if args.final_score is not None:
            t = total_with(args.final_score)
            lines.append("With %g%% on the %s: %.1f%% overall (%s)" % (
                args.final_score, final["name"], t, letter(t, cutoffs)))
        else:
            lines.append("On the %s (%g%% of the grade) you need:" % (
                final["name"], final.get("weight", 0)) if data.get("scheme", "weighted") == "weighted"
                else "On the %s you need:" % final["name"])
            shown = 0
            for name, cut in sorted(cutoffs.items(), key=lambda kv: -kv[1]):
                n = needed(cut)
                if n is None:
                    continue
                if n > 100:
                    if shown == 0 and name == max(cutoffs, key=cutoffs.get):
                        lines.append("- %s: out of reach (would need %.0f%%)" % (name, n))
                    continue
                if n <= 0:
                    lines.append("- %s: already locked in, even with a 0" % name)
                    break
                lines.append("- %s: %d%%" % (name, math.ceil(n - 1e-9)))  # round up: needing 83.4 means 84
                shown += 1
                if shown >= args.max_lines:
                    break
    for n in notes:
        lines.append("Note: " + n)
    print("\n".join(lines))


def letter(p, cutoffs):
    for name, cut in sorted(cutoffs.items(), key=lambda kv: -kv[1]):
        if p >= cut - 1e-9:
            return name
    return "below " + min(cutoffs, key=cutoffs.get)


def main(argv=None):
    p = argparse.ArgumentParser(prog="grade_math.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("need", help="current grade and what you need on the final")
    sp.add_argument("--file")
    sp.add_argument("--sample", action="store_true")
    sp.add_argument("--final-score", dest="final_score", type=float, help="what-if score on the final, in percent")
    sp.add_argument("--max-lines", dest="max_lines", type=int, default=4)
    args = p.parse_args(argv)
    if not args.sample and not args.file:
        print("Pass --file with the grade data, or --sample.")
        return 3
    try:
        cmd_need(args)
    except UserError as e:
        print(str(e))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
