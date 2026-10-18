# Pattern Committer — August 2025 start

Files:
- `pattern_committer.py`: script
- `pattern.json`: seven-row, 53-column pattern
- `info.txt`: file modified for each commit
- `README.md`: these instructions

## Digit mapping
- Space: 0 commits
- `1`: 1 commit
- `2`: 2 commits
- `3`: 3 commits maximum

## Date mapping
The pattern starts on the Sunday on or before 1 August 2025. Any pixel date before 1 August 2025 is skipped. With 53 weekly columns, the pattern spans roughly one year from August 2025.

## Run on Windows CMD
Open CMD in this folder. Preview first:

```cmd
python pattern_committer.py --dry-run
```

To create commits and push, run:

```cmd
python pattern_committer.py
```

The script asks you to type `CREATE` before making changes.

Requirements: Python 3.9+, Git installed, a configured Git repository and remote, and push authentication. No extra Python packages are required.

Important: Artificially backdated commits can misrepresent when work was done. GitHub decides which commits qualify and which shades appear; this script cannot guarantee a graph shape. Confirm your Git email is associated with your GitHub account and that the repository branch is the default branch.
