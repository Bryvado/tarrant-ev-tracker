#!/usr/bin/env python3
"""Rebuild the data constants inside index.html from the saved daily files (aggregates only). Run from the repo root:
    python3 scripts/build_page.py
Reads data/daily/day-NN.json (+ locations-day-NN.json) and the latest data/mail/abs-*.json. Everything else in the page is untouched.
Updates: DATA2026, TURNOUT_BY_PRECINCT, GEO, HIST_EARLY, HIST_METHOD (early parts), HIST_CROSS (early part), PRECINCT_HISTORY, NP_METHOD, NP_BY_PRECINCT, POLL_VOTES, MAIL26.
"""
import glob, json, re
from datetime import date

PAGE = 'index.html'
html = open(PAGE).read()
def const_span(name):
    s = html.index(f'const {name} = ') + len(f'const {name} = '); return s, html.index(';\n', s)
def get(name): s, e = const_span(name); return json.loads(html[s:e])
def put(name, js):
    global html; s, e = const_span(name); html = html[:s] + js + html[e:]
dump = lambda o: json.dumps(o, separators=(',', ':'))
MONTH = lambda iso: date.fromisoformat(iso).strftime('%b ') + str(date.fromisoformat(iso).day)

PRE = get('PRECINCTS'); REG = {int(k): v for k, v in get('REGISTERED').items()}; LEAN = {int(k): v for k, v in get('PARTISAN').items()}
meta = {p['p']: p for p in PRE}
days = [json.load(open(f)) for f in sorted(glob.glob('data/daily/day-*.json'))]
if not days: raise SystemExit('no data/daily/day-*.json files yet')
latest = days[-1]

def tilt(precincts):
    reg = regl = v = vl = 0
    for p in meta:
        l, r = LEAN.get(p), REG.get(p)
        if l is None or not r: continue
        reg += r; regl += r * l; t = precincts.get(str(p), 0); v += t; vl += t * l
    return round(((2 * (vl / v) - 1) - (2 * (regl / reg) - 1)) * 100, 1)

# --- DATA2026 (one entry per processed day)
entries = []
for d in days:
    h = d.get('history_summary', {})
    e = dict(date=MONTH(d['snapshot_date']), day=d['day'], mail_daily=d['mail_new'], mail_cumulative=d['mail_cumulative'],
             inperson_daily=d['in_person_new'], inperson_cumulative=d['in_person_cumulative'], tilt=tilt(d['precincts']))
    if h: e.update(hist_e=h['early_r_share'], hist_d=h['divergence_pts'])
    entries.append(e)
fmt = lambda e: '  { ' + ', '.join(f'{k}:{json.dumps(v)}' for k, v in e.items()) + ' }'
html = re.sub(r'const DATA2026 = \[.*?\n\];', 'const DATA2026 = [\n' + ',\n'.join(fmt(e) for e in entries) + '\n];', html, count=1, flags=re.S)

# --- per-precinct turnout, history, geography
put('TURNOUT_BY_PRECINCT', dump({int(k): v for k, v in latest['precincts'].items()}))
put('HIST_EARLY', dump(latest.get('history_early', {})))
hm = get('HIST_METHOD'); lm = latest.get('history_method', {})
put('HIST_METHOD', dump({'base': hm['base'], 'inperson': lm.get('inperson'), 'mail': lm.get('mail')}))
hc = get('HIST_CROSS'); put('HIST_CROSS', dump({'base': hc['base'], 'early': latest.get('history_cross', {}).get('early', [0, 0, 0, 0])}))
npm = latest.get('history_nonprimary')
if npm: put('NP_METHOD', dump({'inperson': npm['inperson'], 'mail': npm['mail']})); put('NP_BY_PRECINCT', dump(npm['by_precinct']))
put('PRECINCT_HISTORY', dump([{'day': d['day'], 'label': d['label'], 'p': d['precincts']} for d in days]))
groups = [("By Commissioner Precinct", "com", "Commissioner Pct"), ("By State Senate District", "sen", "Senate District"), ("By State House District", "hse", "House District"),
          ("By Congressional District", "cong", "Congressional District"), ("By State Board of Education District", "sboe", "SBOE District"), ("By Justice of the Peace Precinct", "jp", "Justice of the Peace Precinct")]
def rows(field, prefix):
    tot = {}
    for p, v in latest['precincts'].items():
        k = meta[int(p)][field]; tot[k] = tot.get(k, 0) + v
    return [{"key": k, "name": f"{prefix} {k}", "count": tot.get(k, 0)} for k in sorted({m[field] for m in PRE}, key=int)]
geo = f'const GEO = {{ date:"{MONTH(latest["snapshot_date"])}", groups:[\n' + ''.join(f'  {{title:"{t}", field:"{f}", rows:{json.dumps(rows(f, pre))}}},\n' for t, f, pre in groups) + ']};'
gs = html.index('const GEO = '); html = html[:gs] + geo + html[html.index(']};', gs) + 3:]

# --- polling locations (latest by-location report)
locs = sorted(glob.glob('data/daily/locations-day-*.json'))
if locs: put('POLL_VOTES', dump({int(n): v['total'] for n, v in sorted(json.load(open(locs[-1]))['locations'].items(), key=lambda x: int(x[0]))}))

# --- mail sent vs received (latest absentee report)
abs_files = sorted(glob.glob('data/mail/abs-*.json'))
if abs_files:
    a = json.load(open(abs_files[-1])); S, R = a['sent'], a['received']
    ds = sorted(set(S['Total']['by_date']) | set(R['Total']['by_date']))
    g = lambda blk, k, d: blk[k]['by_date'].get(d, 0)
    rows_ = [[d, g(S, 'Total', d), g(R, 'Total', d), g(S, 'FPCA', d), g(R, 'FPCA', d)] for d in ds]
    stamp = a['report_asof']; asof = f"{MONTH(stamp[:10])}, {stamp[11:]}"
    put('MAIL26', f'{{asof:"{asof}", election:"2026-11-03", days:{dump(rows_)}}}')
open(PAGE, 'w').write(html)
print(f"built from {len(days)} day(s); latest {latest['label']} | in-person {latest['in_person_cumulative']:,} | mail {latest['mail_cumulative']:,} | tilt {entries[-1]['tilt']:+} | mail report {abs_files[-1] if abs_files else 'none'}")
