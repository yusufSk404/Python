#!/usr/bin/env python3
"""
Pattern-based Git commit generator.

Digits in pattern.json control the number of commits for a date:
  space = no commits
  1     = 1 commit
  2     = 3 commits
  3     = 5 commits

Note: GitHub decides contribution-graph shades and eligibility. This script
cannot guarantee a particular shade or that every commit will count.
"""

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PATTERN_FILE = Path(__file__).with_name("pattern.json")
FILE_PATH = Path(__file__).with_name("info.txt")
COMMITS_BY_DIGIT = {"1": 1, "2": 3, "3": 5}


def run_git(args, *, env=None, capture=False):
    result = subprocess.run(
        ["git", *args],
        cwd=Path(__file__).parent,
        env=env,
        text=True,
        check=False,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if result.returncode != 0:
        if capture and result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, ["git", *args])
    return result.stdout.strip() if capture else ""


def load_pattern():
    if not PATTERN_FILE.exists():
        raise FileNotFoundError(f"Missing {PATTERN_FILE.name}")
    with PATTERN_FILE.open("r", encoding="utf-8") as f:
        pattern = json.load(f)

    if not isinstance(pattern, list) or not pattern:
        raise ValueError("pattern.json must contain a non-empty list of strings.")
    if not all(isinstance(row, str) for row in pattern):
        raise ValueError("Every pattern row must be a string.")
    if len(pattern) != 7:
        raise ValueError(f"Expected 7 rows (one per weekday), got {len(pattern)}.")

    width = len(pattern[0])
    if any(len(row) != width for row in pattern):
        raise ValueError("All pattern rows must have the same number of characters.")
    invalid = sorted({ch for row in pattern for ch in row if ch != " " and ch not in COMMITS_BY_DIGIT})
    if invalid:
        raise ValueError(f"Unsupported pattern characters: {invalid}. Use spaces, 1, 2, or 3.")
    return pattern


def sunday_on_or_before_jan1(year):
    jan1 = date(year, 1, 1)
    return jan1 - timedelta(days=(jan1.weekday() + 1) % 7)


def planned_commits(pattern, year):
    start_sunday = sunday_on_or_before_jan1(year)
    jobs = []
    for row_idx, row in enumerate(pattern):
        for col_idx, char in enumerate(row):
            if char == " ":
                continue
            commit_day = start_sunday + timedelta(weeks=col_idx, days=row_idx)
            if commit_day.year != year:
                continue
            for number in range(1, COMMITS_BY_DIGIT[char] + 1):
                jobs.append((commit_day, char, number))
    return jobs


def preflight():
    run_git(["rev-parse", "--is-inside-work-tree"], capture=True)
    remote = run_git(["remote"], capture=True)
    if not remote:
        raise RuntimeError("No Git remote is configured. Add your GitHub remote first.")
    branch = run_git(["branch", "--show-current"], capture=True)
    if not branch:
        raise RuntimeError("Could not determine the current branch; switch to a normal branch.")
    name = run_git(["config", "user.name"], capture=True)
    email = run_git(["config", "user.email"], capture=True)
    if not name or not email:
        raise RuntimeError("Set Git identity first: git config user.name and user.email.")
    return branch, remote.splitlines()[0]


def make_commit(message, commit_day, number):
    env = __import__("os").environ.copy()
    date_str = datetime.combine(commit_day, datetime.min.time()).replace(hour=12).strftime("%Y-%m-%dT%H:%M:%S")
    env["GIT_AUTHOR_DATE"] = date_str
    env["GIT_COMMITTER_DATE"] = date_str

    FILE_PATH.write_text(
        f"Pattern pixel date: {commit_day.isoformat()}\n"
        f"Digit: {number}\n"
        f"Commit message: {message}\n",
        encoding="utf-8",
    )
    run_git(["add", FILE_PATH.name])
    run_git([
        "-c", "core.quotepath=false",
        "commit", "-m", message, "--date", date_str
    ], env=env)


def main():
    parser = argparse.ArgumentParser(description="Generate Git commits from pattern.json.")
    parser.add_argument("--year", type=int, help="Year to map the pattern to (for example, 2026).")
    parser.add_argument("--dry-run", action="store_true", help="Preview planned commits without changing Git history.")
    args = parser.parse_args()

    try:
        pattern = load_pattern()
        year = args.year if args.year is not None else int(input("Enter year to map the pattern to: ").strip())
        if year < 1970 or year > 9998:
            raise ValueError("Choose a year between 1970 and 9998.")

        jobs = planned_commits(pattern, year)
        print(f"\nPattern: {len(pattern)} rows × {len(pattern[0])} columns")
        print(f"Year: {year}")
        print(f"Planned commits: {len(jobs)}")
        print("Digit mapping: 1 → 1 commit, 2 → 3 commits, 3 → 5 commits; spaces → 0")
        if not jobs:
            print("No commits are planned for this year.")
            return

        if args.dry_run:
            print("\nDry run only; no files or Git history were changed.")
            for day, digit, number in jobs[:20]:
                print(f"{day.isoformat()} | pattern digit {digit} | commit {number}/{COMMITS_BY_DIGIT[digit]}")
            if len(jobs) > 20:
                print(f"... and {len(jobs) - 20} more commits.")
            return

        branch, remote = preflight()
        print(f"\nCurrent branch: {branch}")
        print(f"Remote selected for push: {remote}")
        print("GitHub may not count every commit, and contribution shades are not guaranteed.")
        confirm = input(f"Type PUSH to create {len(jobs)} commits and push branch '{branch}': ").strip()
        if confirm != "PUSH":
            print("Cancelled. No commits were created.")
            return

        for index, (day, digit, number) in enumerate(jobs, start=1):
            message = f"Pattern pixel {day.isoformat()} ({digit}) {number}/{COMMITS_BY_DIGIT[digit]}"
            make_commit(message, day, number)
            print(f"[{index}/{len(jobs)}] committed {day.isoformat()} ({digit})")

        run_git(["push", remote, branch])
        print("\nFinished. Check the repository and GitHub contribution graph.")
    except (ValueError, FileNotFoundError, json.JSONDecodeError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
