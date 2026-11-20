#!/usr/bin/env python3
"""Build data/lands.json: reservations, trust lands and other tribal areas in each state.

Source: the U.S. Census Bureau's 2020 relationship file of American Indian, Alaska Native and
Native Hawaiian areas by county. It is a public file; this script only reads it. Names are kept as
the Census Bureau writes them. Run by hand when the Bureau publishes a new file.
Map positions come from data/map/land-points.json (npm run lands).
"""
import json, sys, urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

URL = 'https://www2.census.gov/geo/docs/maps-data/data/rel2020/aiannh/tab20_aiannh20_county20_natl.txt'
PAGE = 'https://www.census.gov/geographies/reference-files/time-series/geo/relationship-files.2020.html'
ROOT = Path(__file__).resolve().parent.parent
KIND = {'G2100': 'reservation', 'G2120': 'hawaiian', 'G2130': 'alaska', 'G2140': 'oklahoma',
        'G2150': 'state-area', 'G2160': 'tribal-area', 'G2170': 'joint'}
SQMI = 2589988.11


def main():
    text = Path(sys.argv[1]).read_text(encoding='utf-8-sig') if len(sys.argv) > 1 else \
        urllib.request.urlopen(URL, timeout=120).read().decode('utf-8-sig')
    point = {p['GEOID']: (p['lat'], p['lon']) for p in json.loads((ROOT / 'data/map/land-points.json').read_text())}
    fips = json.loads((ROOT / 'scripts/state_fips.json').read_text())
    areas = defaultdict(lambda: {'land': 0, 'counties': [], 'geoid': None})
    for line in text.splitlines()[1:]:
        c = line.split('|')
        if len(c) < 18 or not c[2]:
            continue
        state = fips.get(c[9][:2])
        if not state or c[5] not in KIND:
            continue
        kind = 'state-reservation' if (c[5], c[6]) == ('G2100', 'D4') else KIND[c[5]]  # D4: reservation recognized by a state
        key = (state, c[2], kind)
        part = int(c[16] or 0)
        areas[key]['land'] += part
        areas[key]['geoid'] = c[1]
        areas[key]['counties'].append((part, c[10]))
    out = defaultdict(list)
    for (state, name, kind), v in sorted(areas.items()):
        counties = [n for _, n in sorted(v['counties'], reverse=True)]
        rec = {'name': name, 'kind': kind, 'sq_mi': round(v['land'] / SQMI, 1), 'counties': counties}
        if v['geoid'] in point:
            rec['lat'], rec['lon'] = point[v['geoid']]
        out[state].append(rec)
    data = {'source': URL, 'source_page': PAGE, 'publisher': 'U.S. Census Bureau', 'vintage': '2020',
            'retrieved': date.today().isoformat(), 'states': out}
    (ROOT / 'data/lands.json').write_text(json.dumps(data, ensure_ascii=False, indent=0) + '\n', encoding='utf-8')
    print(sum(len(v) for v in out.values()), 'areas in', len(out), 'states')


if __name__ == '__main__':
    main()
