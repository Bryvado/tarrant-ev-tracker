#!/usr/bin/env python3
"""Daily stacked-bar graphic: early voters each day by primary history (Democratic-leaning, Republican-leaning, no primary history).
Run from the repo root:  python3 scripts/make_category_chart.py [--out out/]
Democratic-leaning = Lean D + Reliable D; Republican-leaning = Lean R + Reliable R; 'No primary history' also holds the few early voters
with redacted IDs. Daily counts are each day's change in the running totals (Day 1 includes mail returned before early voting opened)."""
import argparse, glob, json, os
from datetime import date
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument('--out', default='out/'); a = ap.parse_args()
INK, MUTED, LINE = '#3A332F', '#6B6558', '#D9D4C7'; COL = ('#1F5C6F', '#8A1538', '#F0AC42')
plt.rcParams['font.family'] = 'DejaVu Sans'
days = [json.load(open(f)) for f in sorted(glob.glob('data/daily/day-*.json'))]
cum = []
for d in days:
    hm = d['history_method']; e = [x + y for x, y in zip(hm['inperson'], hm['mail'])]; n = d['history_nonprimary']
    red = n['inperson'][2] + n['mail'][2]
    cum.append((e[5] + e[6], e[2] + e[3], n['inperson'][1] + n['mail'][1] + red, red))
daily = [tuple(max(0, c - p) for c, p in zip(cum[i][:3], cum[i-1][:3] if i else (0, 0, 0))) for i in range(len(cum))]
last = days[-1]; t = date.fromisoformat(last['snapshot_date']); tot = sum(cum[-1][:3])
share = [v / tot * 100 for v in cum[-1][:3]]

W, H = 7.28, 7.0
fig = plt.figure(figsize=(W, H), dpi=200); fig.patch.set_facecolor('white')
fig.text(0.35/W, 1-0.50/H, "Who's voting, day by day", fontsize=21, fontweight='bold', color=INK, va='top')
fig.text(0.35/W, 1-0.98/H, f"Early voters each day by primary history  \u00b7  through {t.strftime('%b')} {t.day}", fontsize=11, color=MUTED, va='top')
ax = fig.add_axes([0.95/W, 2.3/H, 5.95/W, 3.05/H])
labels = ['Democratic-leaning', 'Republican-leaning', 'No primary history']
for i, (dd, day) in enumerate(zip(daily, days)):
    x = day['day']; bottom = 0
    for k in range(3):
        ax.bar(x, dd[k], bottom=bottom, width=0.68, color=COL[k], label=labels[k] if i == 0 else None)
        if dd[k] > max(map(sum, daily)) * 0.075:
            ax.text(x, bottom + dd[k] / 2, f"{dd[k] / 1000:.1f}k", ha='center', va='center', fontsize=7, fontweight='bold', color=INK if k == 2 else 'white')
        bottom += dd[k]
    ax.text(x, bottom + max(map(sum, daily)) * 0.02, f"{bottom:,}", ha='center', va='bottom', fontsize=8, fontweight='bold', color=INK)
ymax = max(map(sum, daily)) * 1.15
ax.set_xlim(0.4, 12.6); ax.set_ylim(0, ymax); ax.set_xticks(range(1, 13))
ax.set_xticklabels([f"{d}" for d in range(1, 13)], fontsize=9, color=MUTED)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v):,}")); ax.tick_params(axis='y', labelsize=8.5, colors=MUTED, length=0); ax.tick_params(axis='x', length=0)
ax.grid(axis='y', color=LINE, lw=0.8); ax.set_axisbelow(True)
for s in ax.spines.values(): s.set_visible(False)
ax.set_xlabel('Day of early voting', fontsize=9.5, color=INK, labelpad=5)
fig.legend(loc='upper left', bbox_to_anchor=(0.35/W, 1-1.28/H), ncol=3, frameon=False, fontsize=9, handlelength=1.1, columnspacing=1.6)
fig.text(0.35/W, 1.68/H, f"So far:  {share[0]:.0f}% Democratic-leaning  \u00b7  {share[1]:.0f}% Republican-leaning  \u00b7  {share[2]:.0f}% no primary history", fontsize=9, fontweight='bold', color=INK, va='center')
for i, line in enumerate(["Democratic-leaning = mostly voted in Democratic primaries since 2016; Republican-leaning likewise.",
                          "Day 1 includes mail ballots returned before early voting opened. No primary history includes the",
                          f"{cum[-1][3] / tot * 100:.1f}% of early voters whose IDs are redacted. Past primary choices, not how anyone votes in November."]):
    fig.text(0.35/W, (1.34 - 0.2 * i)/H, line, fontsize=7.2, color=MUTED, va='center')
lg = fig.add_axes([0.35/W, 0.10/H, 1.0/W, 0.27/H]); lg.imshow(Image.open('assets/logo.png').convert('RGBA')); lg.axis('off')
fig.text(1.5/W, 0.235/H, 'Tarrant County Early Voting Tracker', fontsize=9.5, color=INK, va='center', fontweight='bold')
fig.text((W-0.35)/W, 0.235/H, 'cesdatatx.com', fontsize=10.5, color=INK, va='center', ha='right', fontweight='bold')
os.makedirs(a.out, exist_ok=True); path = os.path.join(a.out, f"voters_by_day_day-{last['day']:02d}_{last['snapshot_date']}.png"); fig.savefig(path)
print(path, "| shares so far:", [f"{s:.1f}%" for s in share])
