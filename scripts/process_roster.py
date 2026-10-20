#!/usr/bin/env python3
"""Turn one day's roster files into an AGGREGATE-ONLY daily history file. No voter rows are ever written.

Rules (agreed with the project owner):
  * Each roster is a full end-of-day snapshot. Cumulative = row count of the latest file; never add rows across files.
  * Precinct = first 4 digits of the roster's 6-digit Precinct code; it must exist in data/precincts.json.
  * Redacted rows (name/IDs blanked) are COUNTED; their precinct is intact. We never try to match them across days.
  * Day 1 rolls up: mail ballots returned before early voting began count as Day 1's mail (mail_new = cumulative on Day 1;
    afterwards mail_new = change in cumulative). Same rule as the 2022 comparison line. mail_returned_that_day (by Return Date) is kept too.
  * In-person has no date column: daily = this snapshot minus the previous day's. Mail daily = rows whose Return Date
    equals --date (accepts 2025-10-07 and 10/7/2025 formats).
  * Redaction rule (confirmed by the election administrator and by the data): rows are redacted when their 6-digit roster
    precinct code has only 1-2 rows in that file (cumulative). Codes reach 3 rows -> later files show real IDs. The script
    checks this and warns if the redacted count ever differs from the rule (a sign the file format or policy changed).
  * Warn if a cumulative count goes DOWN versus the previous day.

Also saves 'primary_split': ballots that are primary voters / non-primary voters / redacted ID (total, in-person, mail, by precinct).
Optional primary-history step (--history FILE.xlsx, columns VUID, PRECINCT, PE2016..PE2026 with R/D/N): matches early voters to the
owner's list of voters with primary history by SOS Voter ID (zero-padded to 10 digits) and saves AGGREGATES per precinct:
[voters, sum of each voter's R share of primary votes, tier counts (Reliable R, Lean R, Even, Lean D, Reliable D)].
Tiers: Reliable = 3+ primary votes all in one party; Lean = more votes in one party; Even = equal. The list itself is private and
must never be committed; --history-base-out writes the all-voters aggregate (same format, plus sum of squared shares).

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
ap.add_argument('--history'); ap.add_argument('--history-base-out');
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

def expected_redactions(rows):
    c = Counter(r['Precinct'] for r in rows)
    return sum(n for n in c.values() if n <= 2)
red_check = {k: (sum(map(redacted, rs)) == expected_redactions(rs)) for k, rs in (('in_person', inp), ('mail', mail))}
for k, ok in red_check.items():
    if not ok: print(f"WARNING: {k} redacted-row count does not match the 1-2 vote rule; check the file")

def tier(r, d):
    if r == d: return 2
    if r > d: return 0 if (d == 0 and r >= 3) else 1
    return 4 if (r == 0 and d >= 3) else 3
def history_frame(path):
    import pandas as pd
    df = pd.read_excel(path, dtype=str)
    df['VUID'] = df.VUID.str.zfill(10)
    pe = [c for c in df.columns if c.startswith('PE')]
    df['R'] = (df[pe] == 'R').sum(axis=1); df['D'] = (df[pe] == 'D').sum(axis=1)
    df['share'] = df.R / (df.R + df.D); df['tier'] = [tier(r, d) for r, d in zip(df.R, df.D)]
    df['p'] = df.PRECINCT.astype(int); df['sq'] = df.share ** 2
    df.attrs['pe'] = pe
    return df
def total_agg(d):
    t = d.tier.value_counts()
    return [int(len(d)), round(float(d.share.sum()), 3)] + [int(t.get(i, 0)) for i in range(5)]
def cross_groups(d, pe):
    # Switchers: voted in the latest primary (PE2026) in one party, but had more votes in the OTHER party in all earlier primaries.
    prior = [c for c in pe if c != 'PE2026']
    pR, pD = (d[prior] == 'R').sum(axis=1), (d[prior] == 'D').sum(axis=1)
    g1 = (d.PE2026 == 'R') & (pD > pR); g3 = (d.PE2026 == 'D') & (pR > pD)
    g2 = (d.PE2026 == 'R') & ~g1; g4 = (d.PE2026 == 'D') & ~g3
    return [int(g.sum()) for g in (g1, g2, g3, g4)]   # R-from-D, other R, D-from-R, other D
def history_agg(d, with_sq=False):
    res = {}
    for p, g in d.groupby('p'):
        t = g.tier.value_counts()
        row = [int(len(g)), round(float(g.share.sum()), 3)] + [int(t.get(i, 0)) for i in range(5)]
        if with_sq: row.append(round(float(g.sq.sum()), 3))
        res[str(int(p))] = row
    return res
hist_out = {}
if a.history:
    hdf = history_frame(a.history)
    ids = {r['SOS Voter ID'].strip().zfill(10) for r in inp + mail if r['SOS Voter ID'].strip()}
    early = hdf[hdf.VUID.isin(ids)]
    ids_in = {r['SOS Voter ID'].strip().zfill(10) for r in inp if r['SOS Voter ID'].strip()}
    ids_ml = {r['SOS Voter ID'].strip().zfill(10) for r in mail if r['SOS Voter ID'].strip()}
    pe = hdf.attrs['pe']; E_, B_ = total_agg(early), total_agg(hdf)
    # Every ballot is one of: primary voter (ID on the list), non-primary voter (visible ID, not on the list), or redacted ID.
    # Counted by ballot (row), with the roster's precinct, so the shares add up to the day's total.
    list_ids = set(hdf.VUID)
    def split(rows):
        t = [0, 0, 0]
        for r in rows:
            v = r['SOS Voter ID'].strip().zfill(10) if r['SOS Voter ID'].strip() else ''
            t[2 if not v else (0 if v in list_ids else 1)] += 1
        return t
    by_p = {}
    for r in inp + mail:
        pc = int(r['Precinct'][:4])
        if pc not in known: continue
        v = r['SOS Voter ID'].strip().zfill(10) if r['SOS Voter ID'].strip() else ''
        by_p.setdefault(str(pc), [0, 0, 0])[2 if not v else (0 if v in list_ids else 1)] += 1
    PS = {'total': split(inp + mail), 'inperson': split(inp), 'mail': split(mail), 'by_precinct': dict(sorted(by_p.items()))}
    hist_out = {'primary_split': PS, 'history_early': history_agg(early),
                'history_method': {'base': B_, 'inperson': total_agg(hdf[hdf.VUID.isin(ids_in)]), 'mail': total_agg(hdf[hdf.VUID.isin(ids_ml)])},
                'history_cross': {'base': cross_groups(hdf, pe), 'early': cross_groups(early, pe)},
                'history_summary': {'early_r_share': round(E_[1] / E_[0] * 100, 1), 'base_r_share': round(B_[1] / B_[0] * 100, 1),
                                    'divergence_pts': round((E_[1] / E_[0] - B_[1] / B_[0]) * 100, 1), 'early_voters_on_list': E_[0]},
                'history_coverage': {'early_voters_on_list': int(len(early)), 'roster_rows': len(inp) + len(mail),
                                     'rows_without_visible_id': sum(1 for r in inp + mail if not r['SOS Voter ID'].strip())}}
    # Primary voters vs. non-primary voters vs. redacted IDs among early voters (non-primary = ID not on the history list)
    hset = set(hdf.VUID)
    def split(rows):
        on = no = red = 0; by = {}
        for r in rows:
            i = r['SOS Voter ID'].strip().zfill(10) if r['SOS Voter ID'].strip() else None
            if i is None: red += 1; k = 1
            elif i in hset: on += 1; continue
            else: no += 1; k = 0
            pc = int(r['Precinct'][:4])
            if pc in known: by.setdefault(str(pc), [0, 0])[k] += 1
        return [on, no, red], by
    s_in, by_in = split(inp); s_ml, by_ml = split(mail); by_all = {}
    for by in (by_in, by_ml):
        for k, v in by.items(): by_all.setdefault(k, [0, 0]); by_all[k][0] += v[0]; by_all[k][1] += v[1]
    hist_out['history_nonprimary'] = {'inperson': s_in, 'mail': s_ml, 'by_precinct': dict(sorted(by_all.items()))}
    if a.history_base_out:
        json.dump(history_agg(hdf, with_sq=True), open(a.history_base_out, 'w'), separators=(',', ':'))

out = {
    'label': a.label, 'day': a.day, 'snapshot_date': a.date,
    'in_person_cumulative': len(inp), 'mail_cumulative': len(mail),
    'mail_returned_that_day': sum(1 for r in mail if pdate(r['Return Date']) == day),
    'redacted_rows': {'in_person': sum(map(redacted, inp)), 'mail': sum(map(redacted, mail))},
    'redaction_rule_holds': red_check,
    'rows_unmatched_to_precinct': unmatched,
    'precincts': {str(k): v for k, v in sorted(counts.items())},
    **hist_out,
}
if a.prev:
    prev = json.load(open(a.prev))
    out['in_person_new'] = len(inp) - prev['in_person_cumulative']
    out['mail_new'] = len(mail) - prev['mail_cumulative']
    for k in ('in_person', 'mail'):
        if out[k + '_cumulative'] < prev[k + '_cumulative']:
            print(f"WARNING: {k} cumulative dropped from {prev[k+'_cumulative']} to {out[k+'_cumulative']}")
else:
    out['in_person_new'] = len(inp)
    out['mail_new'] = len(mail)
json.dump(out, open(a.out, 'w'), indent=1)
print(f"{a.out}: in-person {len(inp):,} (+{out['in_person_new']:,}), mail {len(mail):,} ({out['mail_returned_that_day']} returned that day), "
      f"redacted {out['redacted_rows']}, unmatched {unmatched:,}")
