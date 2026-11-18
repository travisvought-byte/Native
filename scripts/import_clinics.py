#!/usr/bin/env python3
"""Build data/clinics.json: Indian Health Service, tribal, urban Indian and partner health facilities by state.

Source: the Indian Health Service's own facility layer, the one behind its Find Health Care map
(https://www.ihs.gov/findhealthcaremap/). This script only reads it. Staff names, staff emails and fax
numbers are not kept. Administrative offices that do not see patients are left out.
Run by hand to refresh: python3 scripts/import_clinics.py [saved-query.json]
"""
import json, sys, urllib.request
from datetime import date
from pathlib import Path

LAYER = 'https://services2.arcgis.com/VFLAJVozK0rtzQmT/arcgis/rest/services/ITU_Health_Facilities_View/FeatureServer/0'
QUERY = LAYER + '/query?where=1%3D1&outFields=*&returnGeometry=false&f=json'
PAGE = 'https://www.ihs.gov/findhealthcaremap/'
ROOT = Path(__file__).resolve().parent.parent
RUN = {'I': 'ihs', 'T': 'tribal', 'U': 'urban', 'N': 'partner'}
SKIP = {'Tribal Health Administration'}


def kind(x):
    t = (x.get('SERVICE_TYPE') or '').lower()
    f = (x.get('FHC_Facility_Type') or '').lower()
    if 'hospital' in t or 'acute' in t or f == 'hospital':
        return 'hospital'
    if 'substance' in t or 'behavioral' in t or 'youth regional' in t or f == 'behavioral health':
        return 'behavioral'
    if 'dental' in t or f == 'dental clinic':
        return 'dental'
    if 'assisted living' in t or 'long term' in t:
        return 'elder'
    return 'clinic'


def clean(s):
    return ' '.join(str(s).split()) if s else None


def main():
    raw = json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else \
        json.loads(urllib.request.urlopen(QUERY, timeout=120).read())
    rows = [f['attributes'] for f in raw['features']]
    out = {}
    for x in rows:
        if x.get('STATUS') != 'Active' or x.get('SERVICE_TYPE') in SKIP or not x.get('STATE'):
            continue
        flags = [k for k, v in (('Emergency room', x.get('ER_FLAG')), ('Urgent care', x.get('URG_FLAG')),
                                ('Dental', x.get('DENTAL_FLAG')), ('Behavioral health', x.get('BH_FLAG')),
                                ('Pharmacy', x.get('PHARM_FLAG')), ("Women's health", x.get('WOMEN_FLAG'))) if v == '1']
        rec = {'name': clean(x['FACILITY_NAME']), 'alias': clean(x.get('FACILITY_ALIAS')), 'city': clean(x.get('CITY')),
               'phone': clean(x.get('PHONE')), 'hours': clean(x.get('HOURS')), 'type': clean(x.get('SERVICE_TYPE')),
               'kind': kind(x), 'run': RUN.get(x.get('ITU_CODE'), 'partner'), 'by': clean(x.get('TRIBAL_ENTITY')),
               'offers': flags, 'url': clean(x.get('WEBSITE_URL'))}
        out.setdefault(x['STATE'], []).append({k: v for k, v in rec.items() if v})
    for v in out.values():
        v.sort(key=lambda r: ((r.get('city') or '').lower(), r['name'].lower()))
    data = {'source': LAYER, 'source_page': PAGE, 'publisher': 'Indian Health Service',
            'retrieved': date.today().isoformat(), 'states': dict(sorted(out.items()))}
    (ROOT / 'data/clinics.json').write_text(json.dumps(data, ensure_ascii=False, indent=0) + '\n', encoding='utf-8')
    print(sum(len(v) for v in out.values()), 'facilities in', len(out), 'states')


if __name__ == '__main__':
    main()
