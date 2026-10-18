#!/usr/bin/env python3
"""
Pattern commit planner/committer.

Pattern digits control the number of commits on each date:
  space = 0 commits
  1     = 1 commit
  2     = 2 commits
  3     = 3 commits (maximum)

The 53-week pattern begins on/after 1 August 2025. Dates before
2025-08-01 are skipped. GitHub controls contribution eligibility and shades;
this script cannot guarantee a specific graph appearance.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATTERN_FILE = ROOT / "pattern.json"
FILE_PATH = ROOT / "info.txt"
START_DATE = date(2025, 8, 1)
COMMITS_BY_DIGIT = {"1": 1, "2": 2, "3": 3}


def run_git(args, *, env=None, capture=False):
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=False,
    )
    if result.returncode:
        if capture and result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, ["git", *args])
    return result.stdout.strip() if capture else ""


def load_pattern():
    with PATTERN_FILE.open("r", encoding="utf-8") as f:
        pattern = json.load(f)
    if not isinstance(pattern, list) or len(pattern) != 7:
        raise ValueError("pattern.json must contain exactly 7 rows.")
    if not all(isinstance(row, str) for row in pattern):
        raise ValueError("Every row in pattern.json must be a string.")
    width = len(pattern[0])
    if any(len(row) != width for row in pattern):
        raise ValueError("All pattern rows must have equal width.")
    invalid = sorted({c for row in pattern for c in row if c != " " and c not in COMMITS_BY_DIGIT})
    if invalid:
        raise ValueError(f"Unsupported pattern characters: {invalid}")
    if width != 53:
        raise ValueError(f"Expected 53 columns, got {width}.")
    return pattern


def sunday_on_or_before(day):
    return day - timedelta(days=(day.weekday() + 1) % 7)


def planned_commits(pattern):
    first_sunday = sunday_on_or_before(START_DATE)
    jobs = []
    for row_idx, row in enumerate(pattern):
        for col_idx, char in enumerate(row):
            if char == " ":
                continue
            commit_day = first_sunday + timedelta(weeks=col_idx, days=row_idx)
            if commit_day < START_DATE:
                continue
            for number in range(1, COMMITS_BY_DIGIT[char] + 1):
                jobs.append((commit_day, char, number))
    return sorted(jobs, key=lambda item: (item[0], item[2]))


def preflight():
    run_git(["rev-parse", "--is-inside-work-tree"], capture=True)
    remotes = run_git(["remote"], capture=True).splitlines()
    if not remotes:
        raise RuntimeError("No Git remote is configured.")
    branch = run_git(["branch", "--show-current"], capture=True)
    if not branch:
        raise RuntimeError("Could not determine current branch.")
    name = run_git(["config", "user.name"], capture=True)
    email = run_git(["config", "user.email"], capture=True)
    if not name or not email:
        raise RuntimeError("Configure Git user.name and user.email first.")
    return branch, remotes[0]


def make_commit(day, digit, number):
    date_str = datetime.combine(day, datetime.min.time()).replace(hour=12).strftime("%Y-%m-%dT%H:%M:%S")
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = date_str
    env["GIT_COMMITTER_DATE"] = date_str

    FILE_PATH.write_text(
        f"Pattern date: {day.isoformat()}\n"
        f"Pattern digit: {digit}\n"
        f"Commit number: {number}/{COMMITS_BY_DIGIT[digit]}\n",
        encoding="utf-8",
    )
    run_git(["add", FILE_PATH.name])
    run_git(["commit", "-m", f"Pattern pixel {day.isoformat()} ({digit}) {number}/{COMMITS_BY_DIGIT[digit]}", "--date", date_str], env=env)


def main():
    parser = argparse.ArgumentParser(description="Generate commits from pattern.json starting August 2025.")
    parser.add_argument("--dry-run", action="store_true", help="Preview only; do not create commits or push.")
    args = parser.parse_args()

    try:
        pattern = load_pattern()
        jobs = planned_commits(pattern)
        print(f"Pattern: {len(pattern)} rows x {len(pattern[0])} columns")
        print(f"Start date: {START_DATE.isoformat()} (earlier dates skipped)")
        print("Digit mapping: 1 -> 1 commit, 2 -> 2 commits, 3 -> 3 commits; spaces -> 0")
        print(f"Planned commits: {len(jobs)}")
        if args.dry_run:
            print("\nDry run only; no files, commits, or pushes were changed.")
            for day, digit, number in jobs[:25]:
                print(f"{day.isoformat()} | digit {digit} | commit {number}/{COMMITS_BY_DIGIT[digit]}")
            if len(jobs) > 25:
                print(f"... and {len(jobs) - 25} more commits.")
            return

        branch, remote = preflight()
        print(f"\nBranch: {branch}")
        print(f"Remote selected: {remote}")
        print("Backdated commits can misrepresent when work was performed, and GitHub does not guarantee graph shades.")
        if input(f"Type CREATE to create {len(jobs)} commits and push them: ").strip() != "CREATE":
            print("Cancelled. No commits were created.")
            return

        for idx, (day, digit, number) in enumerate(jobs, 1):
            make_commit(day, digit, number)
            print(f"[{idx}/{len(jobs)}] {day.isoformat()} digit={digit} commit={number}")

        run_git(["push", remote, branch])
        print("\nFinished. Check the repository and contribution graph.")
    except (OSError, ValueError, json.JSONDecodeError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
