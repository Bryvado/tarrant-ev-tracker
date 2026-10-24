#!/usr/bin/env python3
"""One-page district graphic: race context, key numbers, district map (past lean), who is voting vs. the district's registered voters, and the trend.
Run from the repo root:  python3 scripts/make_district_graphic.py [--field sen --key 9] [--out out/]
Context text for SD 9 is set below (sources: Ballotpedia, KERA / Fort Worth Report, Texas Tribune)."""
import argparse, glob, json, os, re
from datetime import date
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, FancyBboxPatch
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument('--field', default='sen'); ap.add_argument('--key', default='9'); ap.add_argument('--out', default='out/'); a = ap.parse_args()
CTX = {('sen', '9'): dict(name='Senate District 9', matchup='Taylor Rehmet (D, incumbent) vs. Leigh Wambsganss (R)',
        background=["Rehmet flipped this seat in a Jan. 31 special runoff, winning 57.3% to 42.7%, in a district", "Donald Trump carried by 17 points in 2024. This is the rematch, for a full four-year term."])}
ctx = CTX.get((a.field, a.key), dict(name=f"{a.field.upper()} {a.key}", matchup='', background=[]))
INK, MUTED, AMBER, CHAR, LINE, PAPER, TEAL, MAROON = '#3A332F', '#6B6558', '#F0AC42', '#504846', '#D9D4C7', '#F7F5EF', '#1F5C6F', '#8A1538'
plt.rcParams['font.family'] = 'DejaVu Sans'
html = open('index.html').read()
def grab(n):
    s = html.index(f'const {n} = ') + len(f'const {n} = '); return json.loads(html[s:html.index(';\n', s)])
PR = grab('PRECINCTS'); REG = {int(k): v for k, v in grab('REGISTERED').items()}; LEAN = {int(k): v for k, v in grab('PARTISAN').items()}
HB = {int(k): v for k, v in grab('HIST_BASE').items()}; HE = {int(k): v for k, v in grab('HIST_EARLY').items()}; NP = {int(k): v for k, v in grab('NP_BY_PRECINCT').items()}; T = {int(k): v for k, v in grab('TURNOUT_BY_PRECINCT').items()}
ids = [p['p'] for p in PR if p[a.field] == a.key]; S = set(ids); m = lambda x: (2 * x - 1) * 100
days = [json.load(open(f)) for f in sorted(glob.glob('data/daily/day-*.json'))]; last = days[-1]; t = date.fromisoformat(last['snapshot_date'])

reg = sum(REG.get(p, 0) for p in ids); votes = sum(T.get(p, 0) for p in ids); county_votes = sum(T.values()); county_reg = sum(REG.values())
Bs = [sum((HB.get(p) or [0] * 8)[i] for p in ids) for i in range(7)]; Es = [sum((HE.get(p) or [0] * 7)[i] for p in ids) for i in range(7)]
early_cat = [Es[5] + Es[6], Es[2] + Es[3], sum((NP.get(p) or [0, 0])[0] + (NP.get(p) or [0, 0])[1] for p in ids)]
reg_cat = [Bs[5] + Bs[6], Bs[2] + Bs[3], max(0, reg - Bs[0])]
rd_rate, rr_rate = Es[6] / Bs[6] * 100, Es[2] / Bs[2] * 100

def trend():
    rows = []
    rl = sum(REG[p] * LEAN[p] for p in ids if p in LEAN and REG.get(p)); rr = sum(REG[p] for p in ids if p in LEAN and REG.get(p))
    for d in days:
        P = {int(k): v for k, v in d['precincts'].items()}; he = d.get('history_early', {})
        vv = sum(P.get(p, 0) for p in ids if p in LEAN and REG.get(p)); vl = sum(P.get(p, 0) * LEAN[p] for p in ids if p in LEAN and REG.get(p))
        E = [sum((he.get(str(p)) or [0] * 7)[i] for p in ids) for i in range(2)]
        rows.append((d['day'], m(vl / vv) - m(rl / rr), -(E[1] / E[0] - Bs[1] / Bs[0]) * 100))   # (day, tilt toward R precincts, primary-history gap in points more Democratic)
    return rows
TR = trend()

def lean_color(r):
    tt = max(-1, min(1, (r - 0.5) * 2))
    c = (201 - tt * 63, 196 - tt * 175, 182 - tt * 126) if tt >= 0 else (201 + tt * 170, 196 + tt * 104, 182 + tt * 71)
    return tuple(v / 255 for v in c)
def patch(pr, fc, ec='white', lw=0.25):
    verts, codes = [], []
    for ring in re.findall(r'M([^Z]*)Z', pr['d']):
        pts = [tuple(map(float, s.split(','))) for s in ring.split('L')]
        verts += pts + [pts[0]]; codes += [Path.MOVETO] + [Path.LINETO] * (len(pts) - 1) + [Path.CLOSEPOLY]
    return PathPatch(Path(verts, codes), facecolor=fc, edgecolor=ec, lw=lw)

W, H = 7.28, 10.9
fig = plt.figure(figsize=(W, H), dpi=200); fig.patch.set_facecolor('white')
top = lambda y: 1 - y / H
fig.text(0.35 / W, top(0.50), f"{ctx['name']}: early voting so far", fontsize=19, fontweight='bold', color=INK, va='top')
fig.text(0.35 / W, top(0.98), f"{ctx['matchup']}  \u00b7  through {t.strftime('%b')} {t.day}", fontsize=9.5, color=MUTED, va='top')
bg = fig.add_axes([0, 0, 1, 1]); bg.set_xlim(0, W); bg.set_ylim(0, H); bg.axis('off'); bg.patch.set_alpha(0)
if ctx['background']:
    bg.add_patch(plt.Rectangle((0.35, H - 1.98), 0.07, 0.56, facecolor=AMBER, edgecolor='none'))
    for i, line in enumerate(ctx['background']): bg.text(0.55, H - 1.57 - 0.26 * i, line, fontsize=8.7, color=INK, va='center')
tiles = [(f"{votes:,}", "early votes", f"{votes / county_votes * 100:.1f}% of the county's"), (f"{votes / reg * 100:.1f}%", "of registered voters", f"county: {county_votes / county_reg * 100:.1f}%"),
         (f"{rd_rate:.0f}% vs. {rr_rate:.0f}%", "reliable D vs. R voters", "who have voted (3+ primaries)")]
tw, gap = 2.12, 0.14
for i, (big, lab, sub) in enumerate(tiles):
    x = 0.35 + i * (tw + gap); y = H - 3.28
    bg.add_patch(FancyBboxPatch((x, y), tw, 1.05, boxstyle="round,pad=0,rounding_size=0.06", facecolor=PAPER, edgecolor=LINE, lw=0.8)); bg.add_patch(plt.Rectangle((x, y), 0.08, 1.05, facecolor=AMBER, edgecolor='none'))
    bg.text(x + 0.22, y + 0.77, big, fontsize=17 if len(big) < 9 else 14.5, fontweight='bold', color=INK, va='center'); bg.text(x + 0.22, y + 0.46, lab, fontsize=8, fontweight='bold', color=MUTED, va='center'); bg.text(x + 0.22, y + 0.22, sub, fontsize=7.6, color=MUTED, va='center')

fig.text(0.35 / W, top(3.62), "Where the district leans (past results)", fontsize=9.6, fontweight='bold', color=INK, va='center')
fig.text(4.25 / W, top(3.62), "Who is voting early", fontsize=9.6, fontweight='bold', color=INK, va='center')
mp = fig.add_axes([0.3 / W, top(7.15) , 3.75 / W, 3.45 / H])
xs = [float(v) for pr in PR if pr['p'] in S for ring in re.findall(r'M([^Z]*)Z', pr['d']) for s in ring.split('L') for v in [s.split(',')[0]]]
ys = [float(v) for pr in PR if pr['p'] in S for ring in re.findall(r'M([^Z]*)Z', pr['d']) for s in ring.split('L') for v in [s.split(',')[1]]]
for pr in PR: mp.add_patch(patch(pr, lean_color(LEAN[pr['p']]) if pr['p'] in S and pr['p'] in LEAN else '#EAE6DB', ec='white', lw=0.2))
pad = 150; mp.set_xlim(min(xs) - pad, max(xs) + pad); mp.set_ylim(max(ys) + pad, min(ys) - pad); mp.set_aspect('equal'); mp.axis('off')
lg = fig.add_axes([0.55 / W, top(7.4), 2.4 / W, 0.1 / H]); lg.imshow(np.array([[lean_color(r) for r in np.linspace(0, 1, 200)]]), aspect='auto'); lg.set_xticks([]); lg.set_yticks([])
for s_ in lg.spines.values(): s_.set_visible(False)
fig.text(0.55 / W, top(7.58), "More Democratic", fontsize=7.4, color=TEAL, va='center', fontweight='bold'); fig.text(2.95 / W, top(7.58), "More Republican", fontsize=7.4, color=MAROON, va='center', ha='right', fontweight='bold')
fig.text(3.05 / W, top(7.4), f"{len(ids)} precincts", fontsize=7.2, color=MUTED, va='center')

fig.text(4.25 / W, top(3.85), "Share of each group by past primary voting\n(Democratic-leaning = mostly voted in\nDemocratic primaries since 2016).", fontsize=7.0, color=MUTED, va='top', linespacing=1.3)
bx = fig.add_axes([4.25 / W, top(6.2), 2.7 / W, 1.7 / H])
cols = [TEAL, MAROON, AMBER]; labs = ['Democratic-leaning', 'Republican-leaning', 'No primary history']
rows_ = [("All registered voters", reg_cat), ("Early voters so far", early_cat)]
for yi, (name, v) in enumerate(rows_[::-1]):
    tot = sum(v); left = 0
    for k in range(3):
        w = v[k] / tot * 100; bx.barh(yi, w, left=left, color=cols[k], height=0.5)
        bx.text(left + w / 2, yi, f"{w:.0f}%", ha='center', va='center', fontsize=8.4, fontweight='bold', color=INK if k == 2 else 'white'); left += w
    bx.text(0, yi + 0.36, name, ha='left', va='bottom', fontsize=8.2, fontweight='bold', color=INK)
bx.set_ylim(-0.45, 1.85); bx.set_xlim(0, 100); bx.set_xticks([]); bx.set_yticks([])
for s_ in bx.spines.values(): s_.set_visible(False)
fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c) for c in cols], labels=labs, loc='upper left', bbox_to_anchor=(4.25 / W, top(6.4)), ncol=1, frameon=False, fontsize=7.6, handlelength=1.0, labelspacing=0.3)

fig.text(0.35 / W, top(7.9), "How the early electorate has shifted, day by day (points)", fontsize=9.6, fontweight='bold', color=INK, va='center')
tx = fig.add_axes([0.9 / W, top(9.45), 5.7 / W, 1.35 / H])
dd = [r[0] for r in TR]; gp = [r[2] for r in TR]; tl = [r[1] for r in TR]
tx.plot(dd, gp, color=TEAL, lw=2.4, marker='o', ms=5); tx.plot(dd, tl, color=MAROON, lw=2.4, marker='o', ms=5)
tx.text(dd[-1] + 0.12, gp[-1], f"{gp[-1]:.1f}", color=TEAL, fontsize=8.5, fontweight='bold', va='center'); tx.text(dd[-1] + 0.12, tl[-1], f"{tl[-1]:+.1f}", color=MAROON, fontsize=8.5, fontweight='bold', va='center')
tx.text(dd[0], gp[0] + 0.9, f"{gp[0]:.1f}", color=TEAL, fontsize=8.5, fontweight='bold', ha='center'); tx.text(dd[0], tl[0] - 1.6, f"{tl[0]:+.1f}", color=MAROON, fontsize=8.5, fontweight='bold', ha='center')
tx.text(6.0, 8.3, "Early voters' own primary history:\npoints more Democratic than the\ndistrict's primary voters", color=TEAL, fontsize=7.4, fontweight='bold', va='center', linespacing=1.25)
tx.text(6.0, -0.4, "Early voters' precincts: points more\nRepublican-leaning than the registered base", color=MAROON, fontsize=7.4, fontweight='bold', va='center', linespacing=1.25)
tx.set_xlim(0.7, 12.4); tx.set_ylim(min(tl) - 3, max(gp) + 3); tx.set_xticks(range(1, 13)); tx.tick_params(axis='x', labelsize=8, colors=MUTED, length=0); tx.tick_params(axis='y', labelsize=8, colors=MUTED, length=0)
tx.grid(axis='y', color=LINE, lw=0.8); tx.set_axisbelow(True); tx.set_xlabel('Day of early voting', fontsize=8.2, color=INK, labelpad=2)
for s_ in tx.spines.values(): s_.set_visible(False)
for i, line in enumerate(["Teal: how many points more Democratic early voters' own primary history is than the district's primary voters.",
                          "Maroon: how many points more Republican-leaning early voters' precincts are than the district's registered voters.",
                          "Past voting and where people live, not how anyone votes in November."]):
    fig.text(0.35 / W, top(10.0 + 0.17 * i), line, fontsize=6.9, color=MUTED, va='center')
lgo = fig.add_axes([0.35 / W, 0.10 / H, 1.0 / W, 0.27 / H]); lgo.imshow(Image.open('assets/logo.png').convert('RGBA')); lgo.axis('off')
fig.text(1.5 / W, 0.235 / H, 'Tarrant County Early Voting Tracker', fontsize=9.5, color=INK, va='center', fontweight='bold'); fig.text((W - 0.35) / W, 0.235 / H, 'cesdatatx.com', fontsize=10.5, color=INK, va='center', ha='right', fontweight='bold')
os.makedirs(a.out, exist_ok=True); path = os.path.join(a.out, f"{a.field}{a.key}_spotlight_day-{last['day']:02d}_{last['snapshot_date']}.png"); fig.savefig(path)
print(path, f"| votes {votes:,} ({votes / county_votes * 100:.1f}% of county) | turnout {votes / reg * 100:.1f}% | habitual D/R voted {rd_rate:.1f}/{rr_rate:.1f} | early mix D/R/none", [f"{v / sum(early_cat) * 100:.0f}%" for v in early_cat], "| registered mix", [f"{v / sum(reg_cat) * 100:.0f}%" for v in reg_cat], "| trend", [(d, round(tl_, 1), round(g, 1)) for d, tl_, g in TR])
