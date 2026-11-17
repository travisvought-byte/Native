#!/usr/bin/env python3
"""Refresh data/nations.json from the Bureau of Indian Affairs Tribal Leaders Directory.

The BIA publishes the directory as an open dataset (linked from
https://www.bia.gov/service/tribal-leaders-directory). This script reads the
public feature layer and keeps only what helps a person reach a Nation's
government office: name, town, state, phone, website and map position.

Left out on purpose: the names of elected leaders, personal email addresses,
fax numbers and BIA's internal notes. Leaders change with every election and
this site is for finding a Nation, not a person.

Usage:
    python3 scripts/import_bia.py                 # download and rewrite data/nations.json
    python3 scripts/import_bia.py --from-file X   # use a saved copy of the query result
"""
import json, re, sys, urllib.parse, urllib.request, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYER = ('https://services1.arcgis.com/UxqqIfhng71wUT9x/arcgis/rest/services/'
         'TribalLeadership_Directory/FeatureServer/0')
DATASET_PAGE = ('https://opendata-1-bia-geospatial.hub.arcgis.com/datasets/'
                '3c6ae1b6fa9f414cbd36758905b196c3_0/explore')
FIELDS = ('OBJECTID,tribefullname,tribealternatename,tribalcomponent,tribeshortname,'
          'biaregion,biaagency,city,state,phone,website,longitude,latitude')

STATE_CODES = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'District of Columbia': 'DC',
    'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL',
    'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA',
    'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN',
    'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
    'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
    'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR',
    'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD',
    'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA',
    'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
}


def download():
    query = urllib.parse.urlencode({
        'where': '1=1', 'outFields': FIELDS, 'returnGeometry': 'false',
        'orderByFields': 'OBJECTID', 'f': 'json'})
    with urllib.request.urlopen(f'{LAYER}/query?{query}', timeout=120) as response:
        return json.load(response)


def clean(value):
    return re.sub(r'\s+', ' ', value).strip() if isinstance(value, str) else None


def display_name(full):
    """BIA carries old listings inside the name, e.g. '(previously listed as ...)'. Drop that part for display."""
    return clean(re.sub(r'\s*\((?:previously|formerly) listed as[^)]*\)', '', full, flags=re.I))


def website(value):
    value = clean(value)
    if not value or ' ' in value or '.' not in value:
        return None
    if not re.match(r'^https?://', value, flags=re.I):
        value = 'https://' + value
    return re.sub(r'^http://', 'https://', value, flags=re.I) if value.lower().startswith('http://www.') else value


def phone(value):
    value = clean(value)
    if not value:
        return None
    digits = re.sub(r'\D', '', value)
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    if len(digits) < 10:
        return None
    main, rest = digits[:10], digits[10:]
    shown = f'({main[:3]}) {main[3:6]}-{main[6:]}' + (f' ext. {rest}' if rest else '')
    return {'display': shown, 'tel': '+1' + main}


def slug(text):
    text = text.lower().replace('&', ' and ').replace("'", '').replace('’', '')
    return re.sub(r'[^a-z0-9]+', '-', text).strip('-')


def main():
    if '--from-file' in sys.argv:
        raw = json.loads(Path(sys.argv[sys.argv.index('--from-file') + 1]).read_text())
    else:
        raw = download()
    rows = [f['attributes'] for f in raw['features']]
    if len(rows) < 550:
        sys.exit(f'Only {len(rows)} rows came back; refusing to overwrite data/nations.json')

    located = [r for r in rows if r.get('state') in STATE_CODES]
    nations, seen = [], {}
    for r in rows:
        full = clean(r['tribefullname'])
        state = STATE_CODES.get(r.get('state'))
        state_from = 'bia'
        if not state:
            # A few rows carry no state. Use the state of the nearest office that has one.
            nearest = min(located, key=lambda o: (o['latitude'] - r['latitude']) ** 2 + (o['longitude'] - r['longitude']) ** 2)
            state, state_from = STATE_CODES[nearest['state']], 'nearest-office'
        base = slug(display_name(full))
        seen[base] = seen.get(base, 0) + 1
        nations.append({
            'id': base if seen[base] == 1 else f'{base}-{seen[base]}',
            'name': display_name(full),
            'listed_as': full,
            'also': clean(r.get('tribealternatename')),
            'kind': 'nation' if r.get('tribalcomponent') == 'Tribe' else 'community',
            'city': clean(r.get('city')),
            'state': state,
            'state_from': state_from,
            'phone': phone(r.get('phone')),
            'url': website(r.get('website')),
            'lat': round(r['latitude'], 4),
            'lon': round(r['longitude'], 4),
            'bia_region': clean(r.get('biaregion')),
            'bia_agency': clean(r.get('biaagency')),
        })
    nations.sort(key=lambda n: (n['state'], n['name'].lower()))
    out = {
        'source': 'Bureau of Indian Affairs, Tribal Leaders Directory (open dataset)',
        'source_page': 'https://www.bia.gov/service/tribal-leaders-directory',
        'dataset': DATASET_PAGE,
        'retrieved': datetime.date.today().isoformat() if '--date' not in sys.argv else sys.argv[sys.argv.index('--date') + 1],
        'note': ('The BIA says this directory is not the official list of federally recognized tribes; '
                 'the official list is the notice it publishes in the Federal Register. The directory '
                 'may contain errors.'),
        'nations': nations,
    }
    (ROOT / 'data').mkdir(exist_ok=True)
    (ROOT / 'data/nations.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{len(nations)} entries written to data/nations.json '
          f'({sum(1 for n in nations if n["kind"] == "nation")} Nations, '
          f'{sum(1 for n in nations if n["kind"] == "community")} bands and communities listed separately)')


if __name__ == '__main__':
    main()
