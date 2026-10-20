#!/usr/bin/env python3
"""Parse the county's 'Early Voting In Person Totals' PDF (votes by location, one column per voting day) into JSON keyed by the
numbered location list (data/polling_locations.json), using data/location_aliases.json for renamed sites.

usage: parse_location_totals.py Early_Voting_Daily_Totals.pdf --out data/daily/locations-day-01.json
Verifies every row's daily numbers add up to its Total and that locations add up to the report's Total row. Names that do not match
the numbered list are reported (never guessed); locations in the list with no row are reported as well. Exits non-zero on a failed check.
"""
import argparse, json, re, subprocess, sys

ap = argparse.ArgumentParser(); ap.add_argument('pdf'); ap.add_argument('--out', required=True)
ap.add_argument('--locations', default='data/polling_locations.json'); ap.add_argument('--aliases', default='data/location_aliases.json'); a = ap.parse_args()
txt = subprocess.check_output(['pdftotext', '-layout', a.pdf, '-'], text=True)
dates = re.search(r'Total\s+((?:\d+/\d+\s*)+)\n', txt).group(1).split()
rows = {}
for line in txt.splitlines():
    m = re.match(r'^(\S.*?)\s{2,}((?:[\d,]+\s*)+)$', line.rstrip())
    if not m: continue
    n = [int(x.replace(',', '')) for x in m.group(2).split()]
    if len(n) == len(dates) + 1: rows[m.group(1).strip()] = n
total = rows.pop('Total')
ok = True
bad = [k for k, v in rows.items() if sum(v[1:]) != v[0]]
if bad: ok = False; print("Rows whose days do not add to their total:", bad)
for i, d in enumerate(['Total'] + dates):
    if sum(v[i] for v in rows.values()) != total[i]: ok = False; print(f"Locations do not add up to the report total for column {d}")

polls = json.load(open(a.locations)); aliases = json.load(open(a.aliases)); aliases.pop('_note', None)
norm = lambda s: re.sub(r'\s+', ' ', re.sub(r'sub\s*courthouse', 'subcourthouse', s.lower().replace('\u2019', "'").replace('.', '').replace('-', ' ').replace('/', ' '))).strip()
by = {norm(p['name']): p['n'] for p in polls}
matched, unmatched = {}, []
for name, v in rows.items():
    n = aliases.get(name) or by.get(norm(name))
    if n: matched[str(n)] = {'name': name, 'total': v[0], 'by_day': dict(zip(dates, v[1:]))}
    else: unmatched.append(name)
missing = sorted(p['n'] for p in polls if str(p['n']) not in matched)
out = {'dates': dates, 'report_total': total[0], 'locations': matched, 'unmatched_names': unmatched, 'list_locations_without_a_row': missing}
json.dump(out, open(a.out, 'w'), indent=1)
print(f"{a.out}: {len(matched)} of {len(polls)} numbered locations matched | report total {total[0]:,} | unmatched names: {unmatched or 'none'} | no row for #: {missing or 'none'} | checks {'OK' if ok else 'FAILED'}")
sys.exit(0 if ok else 1)
