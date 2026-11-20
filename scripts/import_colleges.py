#!/usr/bin/env python3
"""Build data/colleges.json: tribal colleges and universities.

Source: the Bureau of Indian Affairs layer behind its Tribal Colleges and Universities dashboard. This script
only reads it. The president's name, extension and email are not kept: only the school's name, kind, town,
main phone and website. Run by hand to refresh: python3 scripts/import_colleges.py [saved-query.json]
"""
import json, sys, urllib.request
from datetime import date
from pathlib import Path

LAYER = 'https://services1.arcgis.com/UxqqIfhng71wUT9x/arcgis/rest/services/TCU_Colleges/FeatureServer/0'
PAGE = 'https://www.arcgis.com/apps/dashboards/76eb5474cc1548d69d2f4a0fe76d4e3e'
ROOT = Path(__file__).resolve().parent.parent


def main():
    raw = json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else json.loads(
        urllib.request.urlopen(LAYER + '/query?where=1%3D1&outFields=*&returnGeometry=true&outSR=4326&f=json', timeout=120).read())
    out = {}
    for f in raw['features']:
        x = f['attributes']
        rec = {'name': ' '.join(x['school_name'].split()), 'kind': x.get('operation_type'), 'city': x.get('city'),
               'phone': x.get('telephone_1'), 'url': x.get('website')}
        g = f.get('geometry') or {}
        if g.get('y') and g.get('x'):
            rec['lat'], rec['lon'] = round(g['y'], 4), round(g['x'], 4)
        out.setdefault(x['state_abbre'], []).append({k: v for k, v in rec.items() if v})
    for v in out.values():
        v.sort(key=lambda r: r['name'])
    data = {'source': LAYER, 'source_page': PAGE, 'publisher': 'Bureau of Indian Affairs',
            'retrieved': date.today().isoformat(), 'states': dict(sorted(out.items()))}
    (ROOT / 'data/colleges.json').write_text(json.dumps(data, ensure_ascii=False, indent=0) + '\n', encoding='utf-8')
    print(sum(len(v) for v in out.values()), 'colleges in', len(out), 'states')


if __name__ == '__main__':
    main()
