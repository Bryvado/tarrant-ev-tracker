#!/usr/bin/env python3
"""Day-by-day numbers for one district (default: State Senate District 9) from the saved daily files. Run from the repo root:
    python3 scripts/district_spotlight.py [--field sen] [--key 9] [--name "State Senate District 9"]
field = com | sen | hse | cong | sboe | jp.  Prints a table by day plus the latest-day detail used in the Friday post."""
import argparse, glob, json

ap = argparse.ArgumentParser(); ap.add_argument('--field', default='sen'); ap.add_argument('--key', default='9'); ap.add_argument('--name', default='State Senate District 9'); a = ap.parse_args()
html = open('index.html').read()
def grab(name):
    s = html.index(f'const {name} = ') + len(f'const {name} = '); return json.loads(html[s:html.index(';\n', s)])
PR = grab('PRECINCTS'); REG = {int(k): v for k, v in grab('REGISTERED').items()}; LEAN = {int(k): v for k, v in grab('PARTISAN').items()}; HB = grab('HIST_BASE')
ids = [p['p'] for p in PR if p[a.field] == a.key]; idset = set(ids)
days = [json.load(open(f)) for f in sorted(glob.glob('data/daily/day-*.json'))]
reg = sum(REG.get(p, 0) for p in ids); county_reg = sum(REG.values())
B = [sum((HB.get(str(p)) or [0] * 8)[i] for p in ids) for i in range(7)]
m = lambda x: (2 * x - 1) * 100
rl = sum(REG[p] * LEAN[p] for p in ids if p in LEAN and REG.get(p)); rr = sum(REG[p] for p in ids if p in LEAN and REG.get(p))
tiers = [('Reliable R', 0), ('Lean R', 1), ('Lean D', 3), ('Reliable D', 4)]   # data slot 2 (former Even) is always 0
print(f"{a.name}: {len(ids)} precincts | {reg:,} registered ({reg/county_reg*100:.0f}% of county) | baseline lean R{m(rl/rr):+.1f} | list voters {B[0]:,} (R share {B[1]/B[0]*100:.1f}%)\n")
print("day | date    | early votes | share of county | turnout | early-vote lean | tilt   | early R primary hist (vs base) | Rel.D vs Rel.R voted")
for d in days:
    P = {int(k): v for k, v in d['precincts'].items()}
    v = sum(P.get(p, 0) for p in ids); county = sum(P.values())
    vv = sum(P.get(p, 0) for p in ids if p in LEAN and REG.get(p)); vl = sum(P.get(p, 0) * LEAN[p] for p in ids if p in LEAN and REG.get(p))
    he = d.get('history_early', {}); E = [sum((he.get(str(p)) or [0] * 7)[i] for p in ids) for i in range(7)]
    hist = f"{E[1]/E[0]*100:.1f}% vs {B[1]/B[0]*100:.1f}% ({(E[1]/E[0]-B[1]/B[0])*100:+.1f})" if E[0] else "n/a"
    rates = f"{E[6]/B[6]*100:.1f}% vs {E[2]/B[2]*100:.1f}%" if E[0] else "n/a"
    print(f"{d['day']:>3} | {d['snapshot_date'][5:]} | {v:>11,} | {v/county*100:>13.1f}% | {v/reg*100:>6.2f}% | R{m(vl/vv):+.1f}{'':>11} | {m(vl/vv)-m(rl/rr):+.1f} | {hist:<30} | {rates}")
d = days[-1]; he = d.get('history_early', {}); E = [sum((he.get(str(p)) or [0] * 7)[i] for p in ids) for i in range(7)]
if E[0]:
    print("\nLatest day, by primary-history group (share of that group's list voters who have voted early | share of SD's early voters | share of SD's list):")
    for t, k in tiers: print(f"  {t:<11} {E[2+k]/B[2+k]*100:5.1f}% | {E[2+k]/E[0]*100:4.0f}% | {B[2+k]/B[0]*100:4.0f}%")
