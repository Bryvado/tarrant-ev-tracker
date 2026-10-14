#!/usr/bin/env python3
"""Turn one day's roster files into an AGGREGATE-ONLY daily history file. No voter rows are ever written.

Rules (agreed with the project owner):
  * Each roster is a full end-of-day snapshot. Cumulative = row count of the latest file; never add rows across files.
  * Precinct = first 4 digits of the roster's 6-digit Precinct code; it must exist in data/precincts.json.
  * Redacted rows (name/IDs blanked) are COUNTED; their precinct is intact. We never try to match them across days.
  * In-person has no date column: daily = this snapshot minus the previous day's. Mail daily = rows whose Return Date
    equals --date (accepts 2025-10-07 and 10/7/2025 formats).
  * Warn if a cumulative count goes DOWN versus the previous day.

usage: process_roster.py --label "Day 3" --day 3 --date 2026-10-21 --inperson FILE --mail FILE \
         [--prev data/daily/day-02.json] --out data/daily/day-03.json
"""
import argparse, csv, json
from collections import Counter
from datetime import datetime

def load(path): return list(csv.DictReader(open(path, encoding='utf-8', errors='replace'), delimiter='\t'))
def pdate(s):
    for f in ('%Y-%m-%d', '%m/%d/%Y'):
        try: return datetime.strptime(s.strip(), f).date()
        except ValueError: pass
    return None
def redacted(r): return any('redact' in (v or '').lower() for v in r.values())

ap = argparse.ArgumentParser()
ap.add_argument('--label', required=True); ap.add_argument('--day', type=int, required=True)
ap.add_argument('--date', required=True, help='voting day the snapshot covers, YYYY-MM-DD')
ap.add_argument('--inperson', required=True); ap.add_argument('--mail', required=True)
ap.add_argument('--prev'); ap.add_argument('--precincts', default='data/precincts.json'); ap.add_argument('--out', required=True)
a = ap.parse_args()

known = {p['p'] for p in json.load(open(a.precincts))}
inp, mail = load(a.inperson), load(a.mail)
day = datetime.strptime(a.date, '%Y-%m-%d').date()

counts, unmatched = Counter(), 0
for r in inp + mail:
    p = int(r['Precinct'][:4])
    if p in known: counts[p] += 1
    else: unmatched += 1

out = {
    'label': a.label, 'day': a.day, 'snapshot_date': a.date,
    'in_person_cumulative': len(inp), 'mail_cumulative': len(mail),
    'mail_returned_that_day': sum(1 for r in mail if pdate(r['Return Date']) == day),
    'redacted_rows': {'in_person': sum(map(redacted, inp)), 'mail': sum(map(redacted, mail))},
    'rows_unmatched_to_precinct': unmatched,
    'precincts': {str(k): v for k, v in sorted(counts.items())},
}
if a.prev:
    prev = json.load(open(a.prev))
    out['in_person_new'] = len(inp) - prev['in_person_cumulative']
    for k in ('in_person', 'mail'):
        if out[k + '_cumulative'] < prev[k + '_cumulative']:
            print(f"WARNING: {k} cumulative dropped from {prev[k+'_cumulative']} to {out[k+'_cumulative']}")
else:
    out['in_person_new'] = len(inp)
json.dump(out, open(a.out, 'w'), indent=1)
print(f"{a.out}: in-person {len(inp):,} (+{out['in_person_new']:,}), mail {len(mail):,} ({out['mail_returned_that_day']} returned that day), "
      f"redacted {out['redacted_rows']}, unmatched {unmatched:,}")
