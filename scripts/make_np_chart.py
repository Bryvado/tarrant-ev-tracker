#!/usr/bin/env python3
"""Graphic: where early voters with no primary history live, by precinct lean, versus where registered voters without a primary history live.
Run from the repo root:  python3 scripts/make_np_chart.py [--out out/]   (reads the data constants from index.html)"""
import argparse, glob, json, os
from datetime import date
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out/'); a = ap.parse_args()
INK, MUTED, AMBER, LINE, GRAY = '#3A332F', '#6B6558', '#F0AC42', '#D9D4C7', '#B9B2A4'
plt.rcParams['font.family'] = 'DejaVu Sans'
html = open('index.html').read()
def grab(name):
    s = html.index(f'const {name} = ') + len(f'const {name} = '); return json.loads(html[s:html.index(';\n', s)])
REG = {int(k): v for k, v in grab('REGISTERED').items()}; LEAN = {int(k): v for k, v in grab('PARTISAN').items()}
HB = {int(k): v for k, v in grab('HIST_BASE').items()}; HE = {int(k): v for k, v in grab('HIST_EARLY').items()}
NP = {int(k): v for k, v in grab('NP_BY_PRECINCT').items()}; T = {int(k): v for k, v in grab('TURNOUT_BY_PRECINCT').items()}
ok = [p for p in LEAN if REG.get(p)]; m = lambda x: (2 * x - 1) * 100
listn = lambda p: HB.get(p, [0])[0]; regnp = lambda p: max(0, REG[p] - listn(p)); enp = lambda p: NP.get(p, [0, 0])[0]; epr = lambda p: HE.get(p, [0])[0]
lean = lambda w: m(sum(w(p) * LEAN[p] for p in ok) / sum(w(p) for p in ok))
b_np, e_np, b_pr, e_pr = lean(regnp), lean(enp), lean(listn), lean(epr)
tiers = [("Strong D\n(under 40% R)", lambda l: l < .40), ("Lean D\n(40\u201348% R)", lambda l: .40 <= l < .48), ("Competitive\n(48\u201352% R)", lambda l: .48 <= l <= .52),
         ("Lean R\n(52\u201360% R)", lambda l: .52 < l <= .60), ("Strong R\n(over 60% R)", lambda l: l > .60)]
tE, tR = sum(enp(p) for p in ok), sum(regnp(p) for p in ok)
share_e = [sum(enp(p) for p in ok if f(LEAN[p])) / tE * 100 for _, f in tiers]; share_r = [sum(regnp(p) for p in ok if f(LEAN[p])) / tR * 100 for _, f in tiers]
days = [json.load(open(f)) for f in sorted(glob.glob('data/daily/day-*.json'))]; last = days[-1]; t = date.fromisoformat(last['snapshot_date'])
tot = last['in_person_cumulative'] + last['mail_cumulative']; npshare = tE / tot * 100
fmt = lambda x: ('R+' if x >= 0 else 'D+') + f"{abs(x):.1f}"

W, H = 7.28, 7.9
fig = plt.figure(figsize=(W, H), dpi=200); fig.patch.set_facecolor('white')
fig.text(0.35/W, 1-0.50/H, "Where no-primary voters live", fontsize=21, fontweight='bold', color=INK, va='top')
fig.text(0.35/W, 1-0.98/H, f"Early voters with no primary history vs. registered voters without one, by precinct lean  \u00b7  through {t.strftime('%b')} {t.day}", fontsize=8.6, color=MUTED, va='top')
fig.text(0.35/W, 1-1.45/H, f"They are {npshare:.0f}% of early voters. Their precincts average {fmt(e_np)},", fontsize=9.8, fontweight='bold', color=INK, va='top')
fig.text(0.35/W, 1-1.72/H, f"against {fmt(b_np)} for their registered base: a tilt of {e_np - b_np:+.1f} points toward R.", fontsize=9.8, fontweight='bold', color=INK, va='top')
fig.text(0.35/W, 1-1.99/H, f"Voters with a primary history match their base ({fmt(e_pr)} vs. {fmt(b_pr)}).", fontsize=9.8, color=INK, va='top')
ax = fig.add_axes([0.9/W, 2.05/H, 5.95/W, 3.1/H])
x = range(len(tiers)); w = 0.36
b1 = ax.bar([i - w/2 for i in x], share_r, w, color=GRAY, label="Registered voters without a primary history")
b2 = ax.bar([i + w/2 for i in x], share_e, w, color=AMBER, label="Early voters with no primary history")
for rects in (b1, b2):
    for r in rects: ax.text(r.get_x() + r.get_width()/2, r.get_height() + 0.6, f"{r.get_height():.0f}%", ha='center', va='bottom', fontsize=8.5, fontweight='bold', color=INK)
ax.set_xticks(list(x)); ax.set_xticklabels([n for n, _ in tiers], fontsize=8.6, color=INK); ax.set_ylim(0, max(share_e + share_r) * 1.18)
ax.set_yticks([]); ax.tick_params(length=0)
for s in ax.spines.values(): s.set_visible(False)
ax.axhline(0, color=LINE, lw=1)
fig.legend(loc='upper left', bbox_to_anchor=(0.35/W, 1-2.42/H), ncol=2, frameon=False, fontsize=8.6, handlelength=1.1, columnspacing=1.6)
for i, line in enumerate(["Share of each group living in precincts of that lean (each group adds to 100%). Past general-election results by precinct.",
                          "No primary history includes first-time voters, new registrants, general-election-only voters and people who moved in.",
                          "This shows where these voters live, not how they vote. Registered base = registered voters minus voters on the history list."]):
    fig.text(0.35/W, (1.2 - 0.2 * i)/H, line, fontsize=7.0, color=MUTED, va='center')
lg = fig.add_axes([0.35/W, 0.10/H, 1.0/W, 0.27/H]); lg.imshow(Image.open('assets/logo.png').convert('RGBA')); lg.axis('off')
fig.text(1.5/W, 0.235/H, 'Tarrant County Early Voting Tracker', fontsize=9.5, color=INK, va='center', fontweight='bold')
fig.text((W-0.35)/W, 0.235/H, 'cesdatatx.com', fontsize=10.5, color=INK, va='center', ha='right', fontweight='bold')
os.makedirs(a.out, exist_ok=True); path = os.path.join(a.out, f"no_primary_history_day-{last['day']:02d}_{last['snapshot_date']}.png"); fig.savefig(path)
print(path, "| early NP lean", fmt(e_np), "vs base", fmt(b_np), "| primary", fmt(e_pr), "vs", fmt(b_pr), "| shares early", [f"{v:.1f}" for v in share_e], "registered", [f"{v:.1f}" for v in share_r])
