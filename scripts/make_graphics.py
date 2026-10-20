# Builds the Substack graphics (2022 pace chart, partisan lean map, polling map, voter groups, schedule card) from index.html.
# Run from the repo root: python3 scripts/make_graphics.py   (writes PNGs to out/, which is not committed)
import json, re
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, FancyBboxPatch, Circle
import numpy as np
from PIL import Image

OUT = 'out/'
INK, MUTED, AMBER, CHAR, LINE, PAPER = '#3A332F', '#6B6558', '#F0AC42', '#504846', '#D9D4C7', '#F7F5EF'
plt.rcParams['font.family'] = 'DejaVu Sans'
LOGO = Image.open('assets/logo.png').convert('RGBA')
W = 7.28   # inches -> 1456 px at 200 dpi

html = open('index.html').read()
def grab(name):
    s = html.index(f'const {name} = ')+len(f'const {name} = ')
    return json.loads(html[s:html.index(';\n', s)])
PR, PART, POLLS, METHOD = grab('PRECINCTS'), {int(k):v for k,v in grab('PARTISAN').items()}, grab('POLLS'), grab('HIST_METHOD')
rows22 = re.findall(r'day:(\d+), date:"([^"]+)", inperson_daily:(\d+), inperson_cumulative:(\d+), mail_daily:(\d+), mail_cumulative:(\d+), total_cumulative:(\d+)', html)
D22 = [dict(day=int(r[0]), ipd=int(r[2]), ip=int(r[3]), mail=int(r[5]), tot=int(r[6])) for r in rows22]

def new_fig(h, title, subtitle):
    fig = plt.figure(figsize=(W, h), dpi=200); fig.patch.set_facecolor('white')
    t = fig.text(0.35/W, 1-0.50/h, title, fontsize=19, fontweight='bold', color=INK, va='top')
    r = fig.canvas.get_renderer()
    while t.get_window_extent(r).width/200 > W-0.7: t.set_fontsize(t.get_fontsize()-0.5)
    fig.text(0.35/W, 1-0.98/h, subtitle, fontsize=11, color=MUTED, va='top')
    return fig
def footer(fig, h, source):
    ax = fig.add_axes([0.35/W, 0.10/h, 1.0/W, 0.27/h]); ax.imshow(LOGO); ax.axis('off')
    fig.text(1.5/W, 0.235/h, 'Tarrant County Early Voting Tracker', fontsize=9.5, color=INK, va='center', fontweight='bold')
    fig.text(0.35/W, 0.62/h, source, fontsize=7.5, color=MUTED, va='center', ha='left')
    fig.text((W-0.35)/W, 0.235/h, 'cesdatatx.com', fontsize=10.5, color=INK, va='center', ha='right', fontweight='bold')
def axes_in(fig, h, l, b, w, hh): return fig.add_axes([l/W, b/h, w/W, hh/h])
def lean_color(r):
    t = max(-1, min(1, (r-0.5)*2))
    if t >= 0: c = (201-t*63, 196-t*175, 182-t*126)
    else: a = -t; c = (201-a*170, 196-a*104, 182-a*71)
    return tuple(v/255 for v in c)
def patches(precs, color_fn, edge='white', lw=0.25):
    out = []
    for pr in precs:
        verts, codes = [], []
        for ring in re.findall(r'M([^Z]*)Z', pr['d']):
            pts = [tuple(map(float, s.split(','))) for s in ring.split('L')]
            verts += pts+[pts[0]]; codes += [Path.MOVETO]+[Path.LINETO]*(len(pts)-1)+[Path.CLOSEPOLY]
        out.append(PathPatch(Path(verts, codes), facecolor=color_fn(pr), edgecolor=edge, lw=lw))
    return out
def draw_map(ax, color_fn, **kw):
    for p in patches(PR, color_fn, **kw): ax.add_patch(p)
    ax.set_xlim(0, 6344); ax.set_ylim(6420, 0); ax.set_aspect('equal'); ax.axis('off')

# ---------------------------------------------------------------- 1. 2022 pace chart
H = 6.2
fig = new_fig(H, "Early voting in 2022: how turnout built", "Cumulative early votes in Tarrant County, Day 1 (Oct. 24) to Day 12 (Nov. 4), 2022")
ax = axes_in(fig, H, 1.0, 2.25, 5.1, 2.5)
days = [d['day'] for d in D22]
for key, col, lw, lab, dy, tc in [('tot', INK, 3, 'Total', 19000, INK), ('ip', CHAR, 2.2, 'In-person', -23000, CHAR), ('mail', AMBER, 2.2, 'Mail', 0, '#B9801E')]:
    v = [d[key] for d in D22]; ax.plot(days, v, color=col, lw=lw, solid_capstyle='round')
    ax.text(12.3, v[-1]+dy, f"{lab}  {v[-1]:,}", color=tc, fontsize=9.5, fontweight='bold', va='center')
ax.set_xlim(0.6, 15.4); ax.set_ylim(-48000, 450000); ax.set_xticks(range(1, 13))
yt = list(range(0, 400001, 100000)); ax.set_yticks(yt); ax.set_yticklabels([f"{t:,}" for t in yt], fontsize=8.5, color=MUTED)
ax.tick_params(axis='x', labelsize=9, colors=MUTED, length=0); ax.tick_params(axis='y', length=0)
ax.grid(axis='y', color=LINE, lw=0.8); ax.set_axisbelow(True)
for sp in ax.spines.values(): sp.set_visible(False)
ax.set_xlabel('Day of early voting', fontsize=9.5, color=INK, labelpad=5)
def badge(x, y, n):
    ax.scatter([x], [y], s=210, color='white', edgecolor=INK, linewidth=1.4, zorder=5)
    ax.text(x, y, str(n), ha='center', va='center', fontsize=8.5, fontweight='bold', color=INK, zorder=6)
badge(1, -24000, 1); badge(7, D22[6]['tot']+42000, 2); badge(11.3, 420000, 3)
notes = [("1", f"Day 1: {D22[0]['mail']:,} mail ballots were already in, returned since late September. We count them on Day 1."),
         ("2", f"Day 7 (Sunday): the slowest day, with only {D22[6]['ipd']:,} in-person votes."),
         ("3", f"Day 12 (last day): the busiest, with {D22[11]['ipd']:,} in-person votes.")]
for i, (n, t) in enumerate(notes):
    fig.text(0.40/W, (1.78-0.32*i)/H, n, fontsize=9, fontweight='bold', color=INK, va='center')
    fig.text(0.65/W, (1.78-0.32*i)/H, t, fontsize=9, color=INK, va='center')
footer(fig, H, 'Source: Tarrant County Elections, Nov. 8, 2022 Early Voting Totals report. Mail = ballots returned by date.')
fig.savefig(OUT+'1_saturday_2022_pace.png'); plt.close(fig)

# ---------------------------------------------------------------- 2. partisan lean map
H = 9.2
fig = new_fig(H, "How Tarrant County's 707 precincts have voted", "Historical lean of each voting precinct, from past top-of-ballot races")
ax = axes_in(fig, H, 0.64, 1.85, 6.0, 6.0)
draw_map(ax, lambda pr: lean_color(PART[pr['p']]) if pr['p'] in PART else (0.79, 0.77, 0.71))
gax = axes_in(fig, H, 1.85, 1.38, 3.6, 0.17)
grad = np.array([[lean_color(r) for r in np.linspace(0, 1, 256)]]); gax.imshow(grad, aspect='auto', extent=[0, 1, 0, 1]); gax.set_yticks([])
gax.set_xticks([0.25, 0.5, 0.75]); gax.set_xticklabels(['D+50', 'Even', 'R+50'], fontsize=8.5, color=INK); gax.tick_params(length=2, pad=2)
for s in gax.spines.values(): s.set_visible(False)
fig.text(1.75/W, 1.465/H, 'More\nDemocratic', fontsize=8.5, color='#1F5C6F', ha='right', va='center', fontweight='bold', linespacing=0.95)
fig.text(5.55/W, 1.465/H, 'More\nRepublican', fontsize=8.5, color='#8A1538', ha='left', va='center', fontweight='bold', linespacing=0.95)
footer(fig, H, 'Source: historical precinct results (Republican share of the two-party vote). Gray = no history (new precinct).')
fig.savefig(OUT+'2_sunday_partisan_lean_map.png'); plt.close(fig)

# ---------------------------------------------------------------- 3. polling locations map
H = 8.4
fig = new_fig(H, "Where you can vote early", "The 47 early voting locations, numbered to match the county's list")
ax = axes_in(fig, H, 0.64, 1.05, 6.0, 6.0)
draw_map(ax, lambda pr: '#E6E1D4', edge='white', lw=0.3)
for p in POLLS:
    if p['x'] is None: continue
    ax.add_patch(Circle((p['x'], p['y']), 66, facecolor=AMBER, edgecolor=INK, lw=0.7, zorder=5))
    ax.text(p['x'], p['y']+2, str(p['n']), ha='center', va='center', fontsize=5.6, fontweight='bold', color=INK, zorder=6)
footer(fig, H, 'Source: Tarrant County Elections early voting schedule, Nov. 3, 2026')
fig.savefig(OUT+'3_sunday_polling_locations_map.png'); plt.close(fig)

# ---------------------------------------------------------------- 4. voter groups bar
H = 5.8
tot = METHOD['base'][0]; counts = METHOD['base'][2:]
names = ["Reliable Republican", "Lean Republican", "Even", "Lean Democratic", "Reliable Democratic"]
cols = ["#8A1538", "#A9705B", "#C9C4B6", "#6E9FA8", "#1F5C6F"]
fig = new_fig(H, "Who's on the primary-history list", f"{tot:,} Tarrant County voters who voted in at least one primary from 2016 to 2026")
ax = axes_in(fig, H, 2.4, 2.4, 4.2, 2.05)
y = np.arange(len(counts))[::-1]
ax.barh(y, counts, color=cols, height=0.62)
for yi, c in zip(y, counts): ax.text(c+4000, yi, f"{c:,}  ({c/tot*100:.1f}%)", va='center', fontsize=9.5, color=INK, fontweight='bold')
ax.set_yticks(y); ax.set_yticklabels(names, fontsize=10.5, color=INK); ax.set_xlim(0, max(counts)*1.62)
ax.tick_params(length=0); ax.set_xticks([])
for sp in ax.spines.values(): sp.set_visible(False)
for i, t in enumerate(["Reliable: three or more primary votes, all in one party.",
                       "Lean: more primary votes in one party than the other.  Even: the same number in each party.",
                       "This is a record of past primary choices, not how anyone votes in November."]):
    fig.text(0.35/W, (1.98-0.27*i)/H, t, fontsize=8.5, color=MUTED, va='center')
footer(fig, H, 'Source: Tarrant County voter primary history, 2016\u20132026 (totals only)')
fig.savefig(OUT+'4_monday_voter_groups.png'); plt.close(fig)

# ---------------------------------------------------------------- 5. schedule card
H = 5.9
fig = new_fig(H, "Early voting in Tarrant County", "Monday, October 19 through Friday, October 30, 2026")
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off'); ax.patch.set_alpha(0)
rows = [("Monday\u2013Friday", "Oct. 19\u201323", "8 a.m. \u2013 5 p.m."), ("Saturday", "Oct. 24", "7 a.m. \u2013 7 p.m."),
        ("Sunday", "Oct. 25", "10 a.m. \u2013 4 p.m."), ("Monday\u2013Friday", "Oct. 26\u201330", "7 a.m. \u2013 7 p.m.")]
top, rh = 4.05, 0.62
ax.add_patch(FancyBboxPatch((0.35, top-0.05), W-0.7, 0.5, boxstyle="round,pad=0,rounding_size=0.06", facecolor=CHAR, edgecolor='none'))
for x, t in [(0.6, 'DAYS'), (2.9, 'DATES'), (4.7, 'HOURS')]: ax.text(x, top+0.20, t, color='white', fontsize=9, fontweight='bold', va='center')
for i, (a, b, c) in enumerate(rows):
    yy = top - 0.25 - rh*i - 0.04
    ax.add_patch(FancyBboxPatch((0.35, yy-0.28), W-0.7, 0.56, boxstyle="round,pad=0,rounding_size=0.06", facecolor=PAPER if i % 2 == 0 else 'white', edgecolor=LINE, lw=0.8))
    ax.add_patch(plt.Rectangle((0.35, yy-0.28), 0.09, 0.56, facecolor=AMBER, edgecolor='none'))
    ax.text(0.6, yy, a, fontsize=12.5, fontweight='bold', color=INK, va='center'); ax.text(2.9, yy, b, fontsize=12.5, color=INK, va='center')
    ax.text(4.7, yy, c, fontsize=12.5, fontweight='bold', color=INK, va='center')
ax.add_patch(FancyBboxPatch((0.35, 0.88), W-0.7, 0.57, boxstyle="round,pad=0,rounding_size=0.06", facecolor=AMBER, edgecolor='none'))
ax.text(W/2, 1.165, "Election Day: Tuesday, Nov. 3  \u00b7  47 early voting locations countywide", fontsize=11.5, fontweight='bold', color=INK, ha='center', va='center')
footer(fig, H, 'Source: Tarrant County Elections early voting schedule')
fig.savefig(OUT+'5_monday_early_voting_schedule.png'); plt.close(fig)
print("done")
