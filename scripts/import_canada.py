#!/usr/bin/env python3
"""Build data/world/ca-places.json: First Nations and Inuit communities in Canada, with map positions.

Sources (Government of Canada open data, Open Government Licence - Canada):
  - First Nations Location, Indigenous Services Canada. Each point is the First Nation's administrative office
    as registered with the department.
  - Inuit Communities Location, Crown-Indigenous Relations and Northern Affairs Canada / Indigenous Services Canada.
Only the name, band number, community names in Inuktut, region, province or territory and map position are kept.
Each First Nation links to its official First Nation Profile, which has its address and phone.

Run by hand to refresh:  python3 scripts/import_canada.py
"""
import json, urllib.parse, urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = 'https://data.sac-isc.gc.ca/geomatics/rest/services/Donnees_Ouvertes-Open_Data/'
FN = BASE + 'Premiere_Nation_First_Nation/MapServer/0'
INUIT = BASE + 'Inuit_Community/MapServer/0'
FN_PAGE = 'https://open.canada.ca/data/en/dataset/b6567c5c-8339-4055-99fa-63f92114d9e4'
INUIT_PAGE = 'https://open.canada.ca/data/en/dataset/2bcf34b5-4e9a-431b-9e43-1eace6c873bd'
PROFILE = 'https://fnp-ppn.aadnc-aandc.gc.ca/fnp/Main/Search/FNMain.aspx?BAND_NUMBER={}&lang=eng'


def query(layer):
    rows, offset = [], 0
    while True:
        q = urllib.parse.urlencode({'where': '1=1', 'outFields': '*', 'returnGeometry': 'true', 'outSR': 4326,
                                    'f': 'json', 'resultOffset': offset, 'resultRecordCount': 1000})
        data = json.loads(urllib.request.urlopen(f'{layer}/query?{q}', timeout=120).read())
        rows += data['features']
        if not data.get('exceededTransferLimit'):
            return rows
        offset += len(data['features'])


def main():
    nations = []
    for f in query(FN):
        a, g = f['attributes'], f.get('geometry') or {}
        if not g.get('y'):
            continue
        # The service sends the glottal stop (ʔ) in some names as '?'; put it back.
        nations.append({'name': ' '.join(a['BAND_NAME'].split()).replace('?', 'ʔ'), 'band': a['BAND_NUMBER'],
                        'url': PROFILE.format(a['BAND_NUMBER']), 'lat': round(g['y'], 4), 'lon': round(g['x'], 4)})
    inuit = []
    for f in query(INUIT):
        a, g = f['attributes'], f.get('geometry') or {}
        lat, lon = g.get('y') or a.get('LATITUDE'), g.get('x') or a.get('LONGITUDE')
        if not lat:
            continue
        rec = {'name': a['NAME'], 'inuktut': a.get('NAME_INUKTUT_ROMAN'), 'syllabics': a.get('NAME_INUKTUT_SYLLABIC'),
               'region': a.get('REGION'), 'province': a.get('PROVINCE_NAME'), 'lat': round(lat, 4), 'lon': round(lon, 4)}
        inuit.append({k: v for k, v in rec.items() if v and str(v).strip()})
    nations.sort(key=lambda r: r['name'])
    inuit.sort(key=lambda r: r['name'])
    data = {'retrieved': date.today().isoformat(),
            'first_nations': {'source': FN, 'source_page': FN_PAGE, 'publisher': 'Indigenous Services Canada', 'items': nations},
            'inuit': {'source': INUIT, 'source_page': INUIT_PAGE,
                      'publisher': 'Crown-Indigenous Relations and Northern Affairs Canada', 'items': inuit}}
    (ROOT / 'data/world/ca-places.json').write_text(json.dumps(data, ensure_ascii=False, indent=0) + '\n', encoding='utf-8')
    print(len(nations), 'First Nations,', len(inuit), 'Inuit communities')


if __name__ == '__main__':
    main()
