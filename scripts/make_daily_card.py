#!/usr/bin/env python3
"""Make the shareable daily card (PNG, 1456 px wide) from the saved daily data. Run from the repo root:
    python3 scripts/make_daily_card.py [--day N] [--out out/]
Reads data/daily/day-NN.json, data/comparison_2022.json, data/mail/abs-*.json (latest) and data/registered_voters.json."""
import argparse, glob, json, os
from datetime import date
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument('--day', type=int); ap.add_argument('--out', default='out/'); a = ap.parse_args()
INK, MUTED, AMBER, CHAR, LINE, PAPER = '#3A332F', '#6B6558', '#F0AC42', '#504846', '#D9D4C7', '#F7F5EF'
plt.rcParams['font.family'] = 'DejaVu Sans'
days = [json.load(open(f)) for f in sorted(glob.glob('data/daily/day-*.json'))]
d = next(x for x in days if x['day'] == a.day) if a.day else days[-1]
c22 = json.load(open('data/comparison_2022.json')); r22 = next(x for x in c22 if x['day'] == d['day'])
reg = sum(json.load(open('data/registered_voters.json'))['registered'].values())
mail_abs = json.load(open(sorted(glob.glob('data/mail/abs-*.json'))[-1])); m22 = json.load(open('data/mail/2022_sent_returned.json'))

tot = d['in_person_cumulative'] + d['mail_cumulative']; ip = d['in_person_cumulative']
pct = lambda x, y: f"{(x / y - 1) * 100:+.0f}%"

def series(rows, election):   # cumulative sent/received with days-before-election
    s = r = 0; out = []
    for row in rows:
        s += row[1]; r += row[2]; out.append((row[0], (date.fromisoformat(election) - date.fromisoformat(row[0])).days, s, r))
    return out
S, R = mail_abs['sent']['Total']['by_date'], mail_abs['received']['Total']['by_date']
s26 = series([[k, S.get(k, 0), R.get(k, 0)] for k in sorted(set(S) | set(R))], '2026-11-03'); s22 = series(m22['days'], '2022-11-08')
cur = s26[-1]; mail_rate = cur[3] / cur[2]
cmp22 = None
for p in reversed(s26):
    q = next((x for x in s22 if x[1] == p[1]), None)
    if q: cmp22 = (p, q); break

W, H = 7.28, 7.9
fig = plt.figure(figsize=(W, H), dpi=200); fig.patch.set_facecolor('white')
t = date.fromisoformat(d['snapshot_date'])
fig.text(0.35/W, 1-0.50/H, f"Early voting, Day {d['day']}", fontsize=24, fontweight='bold', color=INK, va='top')
fig.text(0.35/W, 1-1.03/H, f"{t.strftime('%A, %B')} {t.day} \u00b7 Tarrant County", fontsize=11.5, color=MUTED, va='top')
fig.text(0.35/W, 1-1.95/H, f"{tot:,}", fontsize=54, fontweight='bold', color=INK, va='center')
fig.text(0.38/W, 1-2.50/H, f"ballots cast so far  \u00b7  {tot / reg * 100:.1f}% of registered voters", fontsize=11.5, color=MUTED, va='center')

tiles = [("IN PERSON", f"{ip:,}", f"{pct(ip, r22['inperson_cumulative'])} vs. 2022, Day {d['day']}"),
         ("MAIL RETURNED", f"{d['mail_cumulative']:,}", f"{mail_rate * 100:.1f}% of mail ballots sent are back"),
         ("TOTAL VS. 2022", pct(tot, r22['total_cumulative']), f"{tot:,} vs. {r22['total_cumulative']:,} on Day {d['day']}")]
tw, gap, x0 = 2.12, 0.14, 0.35
ax0 = fig.add_axes([0, 0, 1, 1]); ax0.set_xlim(0, W); ax0.set_ylim(0, H); ax0.axis('off'); ax0.patch.set_alpha(0)
for i, (lab, val, sub) in enumerate(tiles):
    x = x0 + i * (tw + gap); y = H - 4.05
    ax0.add_patch(FancyBboxPatch((x, y), tw, 1.1, boxstyle="round,pad=0,rounding_size=0.06", facecolor=PAPER, edgecolor=LINE, lw=0.8))
    ax0.add_patch(plt.Rectangle((x, y), 0.08, 1.1, facecolor=AMBER, edgecolor='none'))
    ax0.text(x + 0.22, y + 0.88, lab, fontsize=8, fontweight='bold', color=MUTED, va='center')
    ax0.text(x + 0.22, y + 0.55, val, fontsize=21, fontweight='bold', color=INK, va='center')
    ax0.text(x + 0.22, y + 0.2, sub, fontsize=7.6, color=MUTED, va='center')

fig.text(0.35/W, 3.55/H, "Cumulative ballots cast, 2026 vs. 2022", fontsize=10.5, fontweight='bold', color=INK, va='center')
ax = fig.add_axes([0.95/W, 1.2/H, 5.0/W, 2.1/H])
x22 = [r['day'] for r in c22]; y22 = [r['total_cumulative'] for r in c22]
ax.plot(x22, y22, color=CHAR, lw=2, ls=(0, (4, 3)), alpha=0.75)
ax.text(12.25, y22[-1], f"2022\n{y22[-1]:,}", color=CHAR, fontsize=8.5, fontweight='bold', va='center')
xs = [x['day'] for x in days]; ys = [x['in_person_cumulative'] + x['mail_cumulative'] for x in days]
ax.plot(xs, ys, color=AMBER, lw=3, marker='o', ms=6, markeredgecolor=INK, markeredgewidth=0.8)
ax.text(xs[-1], ys[-1] + 30000, f"{ys[-1]:,}", color='#B9801E', fontsize=9, fontweight='bold', ha='center' if xs[-1] > 1 else 'left')
ax.set_xlim(0.6, 15.2); ax.set_ylim(0, 450000); ax.set_xticks(range(1, 13)); yt = [0, 100000, 200000, 300000, 400000]
ax.set_yticks(yt); ax.set_yticklabels([f"{v:,}" for v in yt], fontsize=8, color=MUTED); ax.tick_params(axis='x', labelsize=8.5, colors=MUTED, length=0); ax.tick_params(axis='y', length=0)
ax.grid(axis='y', color=LINE, lw=0.8); ax.set_axisbelow(True)
for sp in ax.spines.values(): sp.set_visible(False)
ax.set_xlabel('Day of early voting', fontsize=9, color=INK, labelpad=4)

lg = fig.add_axes([0.35/W, 0.10/H, 1.0/W, 0.27/H]); lg.imshow(Image.open('assets/logo.png').convert('RGBA')); lg.axis('off')
fig.text(1.5/W, 0.235/H, 'Tarrant County Early Voting Tracker', fontsize=9.5, color=INK, va='center', fontweight='bold')
fig.text((W-0.35)/W, 0.235/H, 'cesdatatx.com', fontsize=10.5, color=INK, va='center', ha='right', fontweight='bold')
note = f"Totals through {t.strftime('%b')} {t.day}. Mail includes ballots returned before early voting opened. Source: Tarrant County Elections."
fig.text(0.35/W, 0.62/H, note, fontsize=7.2, color=MUTED, va='center')
os.makedirs(a.out, exist_ok=True)
path = os.path.join(a.out, f"daily_card_day-{d['day']:02d}_{d['snapshot_date']}.png"); fig.savefig(path)
print(path, "| total", f"{tot:,}", "| vs 2022", pct(tot, r22['total_cumulative']), "| mail rate", f"{mail_rate*100:.1f}%", "| 2022 mail comparison:",
      (f"{cmp22[1][3]/cmp22[1][2]*100:.1f}% at {cmp22[1][1]} days out" if cmp22 else "n/a"))
