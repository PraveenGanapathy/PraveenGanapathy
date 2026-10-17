"""Wrap Platane/snk's contribution snake in an arcade-style game screen.

Usage: snake_game.py <snk.svg> <out.svg> [score] [player]
"""
import re
import sys
from datetime import datetime, timezone
from xml.sax.saxutils import escape

src, out = sys.argv[1], sys.argv[2]
score = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3].isdigit() else None
player = sys.argv[4] if len(sys.argv) > 4 else "PLAYER 1"

snk = open(src, encoding="utf-8").read()
m = re.match(r"\s*<svg([^>]*)>(.*)</svg>\s*$", snk, re.S)
if not m:
    sys.exit(f"{src}: not an SVG")
view_box = re.search(r'viewBox="([^"]+)"', m.group(1)).group(1)
_, _, vw, vh = (float(v) for v in view_box.split())
inner = m.group(2)

W, PAD, HUD, FOOT = 1000, 40, 64, 48
gw = W - 2 * PAD
gh = round(gw * vh / vw)
H = HUD + gh + FOOT

FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"
score_txt = f"{int(score):06d}" if score else "------"
level = datetime.now(timezone.utc).year

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Snake game eating {escape(player)}'s GitHub contributions">
  <defs>
    <linearGradient id="g-bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#070b18"/><stop offset="1" stop-color="#0d1430"/>
    </linearGradient>
    <linearGradient id="g-edge" x1="0" x2="1">
      <stop offset="0" stop-color="#22d3ee"/><stop offset=".5" stop-color="#a855f7"/><stop offset="1" stop-color="#ec4899"/>
    </linearGradient>
    <radialGradient id="g-vignette" cx=".5" cy=".5" r=".75">
      <stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".55"/>
    </radialGradient>
    <pattern id="g-grid" width="16" height="16" patternUnits="userSpaceOnUse">
      <path d="M16 0H0V16" fill="none" stroke="#22d3ee" stroke-opacity=".05"/>
    </pattern>
    <pattern id="g-scan" width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="1" fill="#000" fill-opacity=".28"/>
    </pattern>
    <clipPath id="g-clip"><rect width="{W}" height="{H}" rx="18"/></clipPath>
  </defs>
  <style>
    .s {{ filter: drop-shadow(0 0 3px #e879f9) drop-shadow(0 0 8px #a855f7); }}
    .hud {{ font-family: {FONT}; font-weight: 700; letter-spacing: 2px; }}
    .blink {{ animation: g-blink 1.1s steps(1) infinite; }}
    @keyframes g-blink {{ 50% {{ opacity: 0; }} }}
    .sweep {{ animation: g-sweep 7s linear infinite; }}
    @keyframes g-sweep {{ from {{ transform: translateY(-120px); }} to {{ transform: translateY({H + 40}px); }} }}
    .edge {{ animation: g-glow 3s ease-in-out infinite alternate; }}
    @keyframes g-glow {{ from {{ stroke-opacity: .45; }} to {{ stroke-opacity: 1; }} }}
    @media (prefers-reduced-motion: reduce) {{ .blink, .sweep, .edge {{ animation: none; }} }}
  </style>
  <g clip-path="url(#g-clip)">
    <rect width="{W}" height="{H}" fill="url(#g-bg)"/>
    <rect width="{W}" height="{H}" fill="url(#g-grid)"/>

    <g class="hud" font-size="14">
      <text x="{PAD}" y="40" fill="#22d3ee">SNAKE<tspan fill="#a855f7">.EXE</tspan></text>
      <text x="{W / 2}" y="40" text-anchor="middle" fill="#64748b">SCORE <tspan fill="#f8fafc" font-size="18">{score_txt}</tspan></text>
      <text x="{W - PAD}" y="40" text-anchor="end" fill="#64748b">LEVEL <tspan fill="#f8fafc">{level}</tspan></text>
    </g>
    <line x1="{PAD}" y1="{HUD - 6}" x2="{W - PAD}" y2="{HUD - 6}" stroke="url(#g-edge)" stroke-opacity=".35"/>

    <svg x="{PAD}" y="{HUD}" width="{gw}" height="{gh}" viewBox="{view_box}">{inner}</svg>

    <g class="hud" font-size="12">
      <text x="{PAD}" y="{H - 20}" fill="#475569">{escape(player.upper())}  ·  AUTO-PILOT</text>
      <text class="blink" x="{W - PAD}" y="{H - 20}" text-anchor="end" fill="#ec4899">● EATING COMMITS</text>
    </g>

    <rect width="{W}" height="{H}" fill="url(#g-scan)" pointer-events="none"/>
    <rect class="sweep" width="{W}" height="90" fill="#a5f3fc" fill-opacity=".035"/>
    <rect width="{W}" height="{H}" fill="url(#g-vignette)"/>
  </g>
  <rect class="edge" x="1" y="1" width="{W - 2}" height="{H - 2}" rx="17" fill="none" stroke="url(#g-edge)" stroke-width="2"/>
</svg>
"""

open(out, "w", encoding="utf-8").write(svg)
print(f"wrote {out} ({W}x{H}, score={score_txt})")
