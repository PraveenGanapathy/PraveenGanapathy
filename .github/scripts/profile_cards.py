"""Render the GitHub stats, top-languages, and profile-visits SVG cards.

Usage: GITHUB_TOKEN=... profile_cards.py <user> <out_dir> [previous visits.json]

Visit totals come from the hits.sh counter shown in the README. Each run records
today's total in visits.json so the card can chart daily visits over time.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

USER, OUT = sys.argv[1], Path(sys.argv[2])
PREV = Path(sys.argv[3]) if len(sys.argv) > 3 else None
TOKEN = os.environ["GITHUB_TOKEN"]
HITS_URL = f"https://hits.sh/github.com/{USER}.svg"
OUT.mkdir(parents=True, exist_ok=True)

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def graphql():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    res = json.loads(fetch("https://api.github.com/graphql", body,
                           {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"}))
    if "errors" in res:
        sys.exit(f"GraphQL error: {res['errors']}")
    return res["data"]["user"]


def fmt(n):
    return f"{n / 1000:.1f}k" if n >= 10000 else f"{n:,}"


def pct(part, whole):
    p = 100 * part / whole
    return "<0.1%" if 0 < p < .05 else f"{p:.1f}%"


def streaks(days):
    counts = [d["contributionCount"] for d in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current = 0
    tail = counts[:-1] if counts and counts[-1] == 0 else counts  # today may not have commits yet
    for c in reversed(tail):
        if not c:
            break
        current += 1
    return current, longest


THEME = """
    .bg { fill: #ffffff; stroke: #d0d7de; }
    .t1 { fill: #1f2328; } .t2 { fill: #59636e; } .t3 { fill: #8c959f; }
    .tile { fill: #f6f8fa; stroke: #d0d7de; }
    .gridl { stroke: #d0d7de; }
    .track { fill: #eaeef2; }
    @media (prefers-color-scheme: dark) {
      .bg { fill: #0d1117; stroke: #30363d; }
      .t1 { fill: #f0f6fc; } .t2 { fill: #9198a1; } .t3 { fill: #6e7681; }
      .tile { fill: #161b22; stroke: #30363d; }
      .gridl { stroke: #30363d; }
      .track { fill: #21262d; }
    }
    .fade { opacity: 0; animation: fade .7s ease-out forwards; }
    @keyframes fade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
    .draw { stroke-dasharray: 1; stroke-dashoffset: 1; animation: draw 2.2s ease-out .3s forwards; }
    @keyframes draw { to { stroke-dashoffset: 0; } }
    .rise { transform-box: fill-box; transform-origin: bottom; animation: rise .9s cubic-bezier(.2,.7,.2,1) both; }
    @keyframes rise { from { transform: scaleY(0); } }
    .grow { transform-box: fill-box; transform-origin: left; animation: grow 1.1s cubic-bezier(.2,.7,.2,1) both; }
    @keyframes grow { from { transform: scaleX(0); } }
    @media (prefers-reduced-motion: reduce) { * { animation: none !important; opacity: 1 !important; stroke-dashoffset: 0 !important; } }
"""

GRADIENTS = """
    <linearGradient id="accent" x1="0" x2="1"><stop offset="0" stop-color="#22d3ee"/><stop offset=".5" stop-color="#6366f1"/><stop offset="1" stop-color="#a855f7"/></linearGradient>
    <linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6366f1" stop-opacity=".35"/><stop offset="1" stop-color="#6366f1" stop-opacity="0"/></linearGradient>
    <linearGradient id="bar" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#6366f1"/><stop offset="1" stop-color="#a855f7"/></linearGradient>
"""


def frame(w, h, label, body, chip=None):
    chip_svg = ""
    if chip:
        cw = 7 * len(chip) + 22
        chip_svg = (f'<rect class="tile" x="{w - 28 - cw}" y="22" width="{cw}" height="24" rx="12"/>'
                    f'<text class="t2" x="{w - 28 - cw / 2}" y="38" font-size="12" text-anchor="middle">{escape(chip)}</text>')
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}">
  <defs>{GRADIENTS}<clipPath id="c"><rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="14"/></clipPath></defs>
  <style>{THEME}</style>
  <rect class="bg" x="1" y="1" width="{w - 2}" height="{h - 2}" rx="14"/>
  <g clip-path="url(#c)"><rect width="{w}" height="4" fill="url(#accent)"/></g>
  <g font-family="{FONT}">
    <text class="t2" x="28" y="40" font-size="13" font-weight="600" letter-spacing="1.5">{escape(label.upper())}</text>
    {chip_svg}
    {body}
  </g>
</svg>
"""


def smooth_path(pts):
    """Catmull-Rom spline through pts, as cubic Bézier segments."""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def stats_card(u):
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    current, longest = streaks(days)
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])

    kpis = [
        ("Contributions", fmt(cal["totalContributions"])),
        ("Active days", fmt(sum(1 for d in days if d["contributionCount"]))),
        ("Longest streak", f"{longest}d"),
        ("Current streak", f"{current}d"),
        ("Public repos", fmt(u["repositories"]["totalCount"])),
        ("Stars earned", fmt(stars)),
    ]
    W, tw, gap = 1000, 147, 11
    tiles = []
    for i, (label, value) in enumerate(kpis):
        x = 28 + i * (tw + gap)
        tiles.append(
            f'<g class="fade" style="animation-delay:{i * .08:.2f}s">'
            f'<rect class="tile" x="{x}" y="62" width="{tw}" height="78" rx="12"/>'
            f'<text class="t1" x="{x + 16}" y="104" font-size="28" font-weight="700">{escape(value)}</text>'
            f'<text class="t2" x="{x + 16}" y="126" font-size="12">{escape(label)}</text></g>')

    weeks = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]
    first_days = [w["contributionDays"][0]["date"] for w in cal["weeks"]]
    cx0, cx1, cy0, cy1 = 28, W - 28, 170, 300
    peak = max(weeks) or 1
    step = (cx1 - cx0) / max(len(weeks) - 1, 1)
    pts = [(cx0 + i * step, cy1 - (v / peak) * (cy1 - cy0)) for i, v in enumerate(weeks)]
    line = smooth_path(pts)
    area = f"{line} L{cx1},{cy1} L{cx0},{cy1} Z"

    months, seen = [], set()
    for i, d in enumerate(first_days):
        m = d[:7]
        if m not in seen and i > 0:
            seen.add(m)
            months.append(f'<text class="t3" x="{cx0 + i * step:.1f}" y="{cy1 + 20}" font-size="11">'
                          f'{datetime.strptime(d, "%Y-%m-%d").strftime("%b")}</text>')
        seen.add(m)
    pk = max(range(len(weeks)), key=weeks.__getitem__)
    px, py = pts[pk]
    chart = f"""
    <line class="gridl" x1="{cx0}" y1="{cy1}" x2="{cx1}" y2="{cy1}"/>
    <line class="gridl" x1="{cx0}" y1="{cy0}" x2="{cx1}" y2="{cy0}" stroke-dasharray="3 5"/>
    <text class="t3" x="{cx1}" y="{cy0 - 8}" font-size="11" text-anchor="end">peak {peak}/week</text>
    <path class="fade" style="animation-delay:.6s" d="{area}" fill="url(#area)"/>
    <path class="draw" d="{line}" pathLength="1" fill="none" stroke="url(#accent)" stroke-width="2.5" stroke-linecap="round"/>
    <circle class="fade" style="animation-delay:2s" cx="{px:.1f}" cy="{py:.1f}" r="5" fill="#a855f7" stroke="#fff" stroke-width="2"/>
    {"".join(months)}"""
    body = "".join(tiles) + chart + (
        f'<text class="t3" x="28" y="{cy1 + 44}" font-size="11">Weekly contributions</text>')
    return frame(W, cy1 + 62, "GitHub stats", body, chip="last 12 months")


def languages_card(u):
    totals = {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            name, color = e["node"]["name"], e["node"]["color"] or "#8c959f"
            size, _ = totals.get(name, (0, color))
            totals[name] = (size + e["size"], color)
    ranked = sorted(totals.items(), key=lambda kv: -kv[1][0])
    top, rest = ranked[:7], ranked[7:]
    if sum(v[0] for _, v in rest):
        top = top[:6]
        rest = ranked[6:]
        top.append(("Other", (sum(v[0] for _, v in rest), "#8c959f")))
    total = sum(v[0] for _, v in top) or 1

    W, bx, bw = 480, 28, 424
    bar, x = [], bx
    for i, (name, (size, color)) in enumerate(top):
        w = bw * size / total
        bar.append(f'<rect class="grow" style="animation-delay:{i * .1:.1f}s" x="{x:.1f}" y="66" width="{max(w - 2, 0):.1f}" height="12" fill="{color}"/>')
        x += w
    legend = []
    for i, (name, (size, color)) in enumerate(top):
        col, row = i % 2, i // 2
        lx, ly = bx + col * 212, 112 + row * 28
        legend.append(
            f'<g class="fade" style="animation-delay:{.3 + i * .06:.2f}s">'
            f'<circle cx="{lx + 6}" cy="{ly - 4}" r="5" fill="{color}"/>'
            f'<text class="t1" x="{lx + 18}" y="{ly}" font-size="13">{escape(name)}</text>'
            f'<text class="t2" x="{lx + 196}" y="{ly}" font-size="13" text-anchor="end">{escape(pct(size, total))}</text></g>')
    body = (f'<clipPath id="bc"><rect x="{bx}" y="66" width="{bw}" height="12" rx="6"/></clipPath>'
            f'<rect class="track" x="{bx}" y="66" width="{bw}" height="12" rx="6"/>'
            f'<g clip-path="url(#bc)">{"".join(bar)}</g>' + "".join(legend))
    return frame(W, 252, "Top languages", body, chip="by code size")


def visits_card(history):
    W, H = 480, 252
    dates = sorted(history)
    total = history[dates[-1]] if dates else 0
    # One bar per day for the last 30 days; each run's own counter fetch is subtracted.
    today = date.fromisoformat(dates[-1]) if dates else datetime.now(timezone.utc).date()
    daily = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        cur, prev = history.get(d.isoformat()), history.get((d - timedelta(days=1)).isoformat())
        daily.append(max(cur - prev - 1, 0) if cur is not None and prev is not None else None)
    known = [v for v in daily if v is not None]
    week = sum(v for v in daily[-7:] if v is not None)

    head = (f'<text class="t1 fade" x="28" y="104" font-size="40" font-weight="800">{fmt(total)}</text>'
            f'<text class="t2" x="30" y="126" font-size="12">total profile views</text>'
            f'<text class="t1 fade" x="{W - 28}" y="96" font-size="20" font-weight="700" text-anchor="end">+{fmt(week)}</text>'
            f'<text class="t2" x="{W - 28}" y="116" font-size="12" text-anchor="end">last 7 days</text>')
    cx0, cx1, cy0, cy1 = 28, W - 28, 148, 214
    slot = (cx1 - cx0) / len(daily)
    peak = max(known) if known else 0
    bars = []
    for i, v in enumerate(daily):
        x = cx0 + i * slot + 2
        if v is None:
            bars.append(f'<rect class="track" x="{x:.1f}" y="{cy1 - 3}" width="{slot - 4:.1f}" height="3" rx="1.5"/>')
        else:
            h = max(3, (v / peak) * (cy1 - cy0)) if peak else 3
            bars.append(f'<rect class="rise" style="animation-delay:{i * .02:.2f}s" x="{x:.1f}" y="{cy1 - h:.1f}" '
                        f'width="{slot - 4:.1f}" height="{h:.1f}" rx="3" fill="url(#bar)"><title>{v}</title></rect>')
    note = ("Daily views · last 30 days" if len(known) >= 2
            else "Collecting data — the chart fills in daily")
    body = head + "".join(bars) + f'<text class="t3" x="28" y="{cy1 + 24}" font-size="11">{note}</text>'
    return frame(W, H, "Profile visits", body, chip="updated daily")


def main():
    u = graphql()
    (OUT / "stats.svg").write_text(stats_card(u))
    (OUT / "languages.svg").write_text(languages_card(u))

    history = {}
    if PREV and PREV.is_file() and PREV.read_text().strip():
        history = json.loads(PREV.read_text())
    try:
        m = re.search(r'aria-label="[^"]*?([\d,]+)"', fetch(HITS_URL))
        if m:
            history[datetime.now(timezone.utc).date().isoformat()] = int(m.group(1).replace(",", ""))
    except OSError as e:
        print(f"warning: could not read visit counter: {e}", file=sys.stderr)
    (OUT / "visits.json").write_text(json.dumps(history, indent=1, sort_keys=True))
    (OUT / "visits.svg").write_text(visits_card(history))
    print(f"wrote stats.svg, languages.svg, visits.svg ({len(history)} days of visit history)")


if __name__ == "__main__":
    main()
