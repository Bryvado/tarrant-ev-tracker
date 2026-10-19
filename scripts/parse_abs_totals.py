#!/usr/bin/env python3
"""Parse the county's 'Absentee Voting Totals' PDF (ballots SENT and RECEIVED by date, split FPCA / Regular Mail) into JSON.

usage: parse_abs_totals.py ABS_Daily_Totals.pdf --out data/mail/abs-2026-10-17.json
Checks every row's daily numbers add up to its stated total, and that FPCA + Regular = Total on every date; exits non-zero if not.
Aggregates only. Dates are m/d in the PDF; the year comes from the report's own date stamp.
"""
import argparse, json, re, sys
from collections import defaultdict
import pdfplumber

ap = argparse.ArgumentParser(); ap.add_argument('pdf'); ap.add_argument('--out', required=True); a = ap.parse_args()
pdf = pdfplumber.open(a.pdf); pg = pdf.pages[0]
text = pg.extract_text() or ''
stamp = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', text); clock = re.search(r'(\d{1,2}:\d{2}):\d{2}\s*([AP]M)', text)
year = int(stamp.group(3)); asof = f"{year}-{int(stamp.group(1)):02d}-{int(stamp.group(2)):02d} {clock.group(1)} {clock.group(2)}" if clock else None

rows = defaultdict(list)
for w in pg.extract_words(): rows[round(w['top'] / 2) * 2].append(w)
nums = lambda ws: [int(w['text'].replace(',', '')) for w in sorted(ws, key=lambda w: w['x0']) if re.fullmatch(r'[\d,]+', w['text'])]
dates_of = lambda ws: [w['text'] for w in sorted(ws, key=lambda w: w['x0']) if re.fullmatch(r'\d{1,2}/\d{1,2}', w['text'])]
label = lambda ws: ' '.join(w['text'] for w in sorted(ws, key=lambda w: w['x0']) if not re.fullmatch(r'[\d,/]+', w['text']))
iso = lambda d: f"{year}-{int(d.split('/')[0]):02d}-{int(d.split('/')[1]):02d}"

hdrs = sorted(y for y, ws in rows.items() if len(dates_of(ws)) >= 10)
out, ok = {'report_asof': asof, 'year': year}, True
for name, hy in zip(('sent', 'received'), hdrs):
    dts = dates_of(rows[hy]); res = {}
    for y in sorted(rows):
        if hy < y <= hy + 80:
            lab, n = label(rows[y]), nums(rows[y])
            if lab in ('Total', 'FPCA', 'Regular Mail') and len(n) == len(dts) + 1:
                res[lab] = {'total': n[0], 'by_date': {iso(d): v for d, v in zip(dts, n[1:])}}
    for lab, d in res.items():
        if sum(d['by_date'].values()) != d['total']: ok = False; print(f"MISMATCH {name} {lab}: days sum to {sum(d['by_date'].values())}, stated {d['total']}")
    if set(res) == {'Total', 'FPCA', 'Regular Mail'}:
        t, f, r = (res[k]['by_date'] for k in ('Total', 'FPCA', 'Regular Mail'))
        if not all(f[d] + r[d] == t[d] for d in t): ok = False; print(f"MISMATCH {name}: FPCA + Regular != Total on some date")
    else: ok = False; print(f"MISSING rows in {name} table: found {sorted(res)}")
    out[name] = res
json.dump(out, open(a.out, 'w'), indent=1)
print(f"{a.out}: as of {asof} | sent {out['sent']['Total']['total']:,} | received {out['received']['Total']['total']:,} | checks {'OK' if ok else 'FAILED'}")
sys.exit(0 if ok else 1)
