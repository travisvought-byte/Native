#!/usr/bin/env python3
"""Draw the picture shown when someone shares a Nina's Map link (assets/share.png, 1200x630).

Uses the same state outlines and Nation office points as the home-page map, so the
picture always matches the site. Needs rsvg-convert (librsvg) to turn the SVG into a PNG.
Run it after scripts/build_map.mjs changes the map:  python3 scripts/build_share.py
"""
import json
import pathlib
import subprocess
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / 'data/site.json').read_text(encoding='utf-8'))
MAP = json.loads((ROOT / 'data/map/us.json').read_text(encoding='utf-8'))

W, H = 1200, 630
# Place the map on the right half of the card.
scale = 610 / MAP['width']
mx, my = W - 610 - 24, (H - MAP['height'] * scale) / 2 + 20

states = ''.join(f'<path d="{s["d"]}"/>' for s in MAP['states'])
points = ''.join(f'<circle cx="{p["x"]}" cy="{p["y"]}" r="3.4"/>' for p in MAP['points'])

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="{W}" height="{H}" fill="#0e4a5a"/>
<rect x="0" y="{H-14}" width="{W}" height="14" fill="#9c4421"/>
<g transform="translate({mx:.1f},{my:.1f}) scale({scale:.4f})">
  <g fill="#14596b" stroke="#2f7487" stroke-width="1.2" stroke-linejoin="round">{states}</g>
  <g fill="#f2b880" fill-opacity="0.92">{points}</g>
</g>
<g transform="translate(70,150)">
  <path d="M28 0c-15.4 0-28 12.3-28 27.5C0 48.1 28 71.8 28 71.8s28-23.7 28-44.3C56 12.3 43.4 0 28 0z" fill="#f7f3ea"/>
  <circle cx="28" cy="28" r="11.4" fill="#9c4421"/>
</g>
<text x="70" y="300" font-family="Bitter" font-weight="800" font-size="84" fill="#f7f3ea">{escape(SITE['name'])}</text>
<text font-family="Source Sans 3" font-size="34" fill="#e7dcc4">
  <tspan x="72" y="358">Help, Nations and community</tspan>
  <tspan x="72" y="400">for First Peoples, state by state</tspan>
</text>
<text x="72" y="500" font-family="Source Sans 3" font-weight="600" font-size="26" fill="#f2b880">Free. No sign-up. Every listing sourced.</text>
<text x="72" y="545" font-family="Source Sans 3" font-size="26" fill="#b9d3d9">ninas-map.com</text>
</svg>'''

out_svg = ROOT / 'assets/share.svg'
out_png = ROOT / 'assets/share.png'
out_svg.write_text(svg, encoding='utf-8')
subprocess.run(['rsvg-convert', '-w', str(W), '-h', str(H), '-o', str(out_png), str(out_svg)], check=True)
out_svg.unlink()
print(f'wrote {out_png.relative_to(ROOT)}')
