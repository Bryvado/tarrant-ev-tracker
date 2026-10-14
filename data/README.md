# Data folder

Aggregate-only history for the Tarrant County early voting tracker. **No voter rows are stored here, ever.**

- `precincts.json` - the 707 voting precincts and their district codes (no geometry).
- `daily/day-NN.json` - one file per real early voting day (Oct 19-30, 2026).
- `test/` - dry-run files from the Nov 2025 election. Deleted before real early voting starts.

Each daily file holds: label, day number, the voting date the snapshot covers, cumulative in-person and mail counts,
mail ballots returned that day, in-person votes added that day, redacted-row counts, rows that did not match a precinct,
and cumulative votes per precinct (mail + in-person).

Produced by `scripts/process_roster.py` (rules are documented at the top of that file). To add a day, run it with the
day's two roster files and the voting date, then rebuild the page.

Redaction: the county redacts identity fields for any 6-digit roster precinct code with only 1-2 rows in a file, to protect ballot
secrecy. Precinct and district codes stay intact, so counts here are unaffected. The script verifies the rule on every file.

Primary history: `history_base.json` holds per-precinct aggregates of the owner's primary-history list (voters, sum of R share,
tier counts, sum of squared shares). Daily files add `history_early` for that day's early voters. The voter-level list itself is
private, is never committed (`.gitignore`), and is supplied to the script with `--history` each time.
