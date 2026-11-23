#!/usr/bin/env python3
"""The sourcing pipeline for Nina's Map.

    python3 scripts/mine.py check     # registry, queue, duplicates and evidence; exits 1 on a problem
    python3 scripts/mine.py report    # writes pipeline/COVERAGE.md and data/export/listings.csv
    python3 scripts/mine.py refresh   # re-runs the dataset imports listed in pipeline/sources.json (needs internet)

`report` uses only what is in data/, and dates everything from the newest check date in the data,
so the same data always gives the same files. CI runs check and report, then fails if a file changed.
See pipeline/README.md for how a run works from a cold start.
"""
import csv, io, json, re, subprocess, sys, unicodedata
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build  # noqa: E402  (reuses the site's own loaders and state list)

REVIEW_DAYS = 180   # a listing is due for a fresh read after this many days
LAYER_DAYS = 90     # a dataset is due for a refresh after this many days
OFFICIAL_HOSTS = ('.gov', '.mil', '.us', '.gc.ca', '.govt.nz', '.gov.au', '.gob.mx')


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def host(url):
    h = (urlparse(url or '').hostname or '').lower()
    return h[4:] if h.startswith('www.') else h


def norm(name):
    s = unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\b(the|inc|of|and)\b', ' ', s)
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', s).split())


def digits(phone):
    d = re.sub(r'\D', '', phone or '')
    return d[-10:] if len(d) >= 10 else d


def evidence(record):
    """official: a government page or a Nation's own site; first-party: the organization's own site; secondary: anything else."""
    src = host(record.get('source'))
    if src.endswith(OFFICIAL_HOSTS) or src.endswith('.gov.') or '.gov.' in src:
        return 'official'
    if src and src == host(record.get('url')):
        return 'first-party'
    return 'secondary'


def rows():
    """Every published place, normalized to one row shape."""
    out = []
    for r in build.RES + build.WORLD:
        out.append({'layer': 'listing', 'area': r['area'], 'id': r['id'], 'name': r['name'],
                    'city': r.get('place', ''), 'kind': ' '.join([r['need']] + r.get('also', [])),
                    'access': r['access'], 'phone': r.get('phone', ''), 'url': r.get('url', ''),
                    'source': r['source'], 'publisher': '', 'checked': r['checked'], 'evidence': evidence(r)})
    for n in build.NATIONS:
        out.append({'layer': 'nation', 'area': n['state'], 'id': n['id'], 'name': n['name'], 'city': n.get('city', ''),
                    'kind': 'nation', 'access': 'ask', 'phone': (n.get('phone') or {}).get('display', ''),
                    'url': n.get('url', ''), 'source': build.NATIONS_FILE['source_page'],
                    'publisher': 'Bureau of Indian Affairs', 'checked': build.NATIONS_FILE['retrieved'], 'evidence': 'official'})
    for code, entry in build.STATE_NATIONS.items():
        for n in entry['nations']:
            out.append({'layer': 'state-nation', 'area': code, 'id': f'st-{code.lower()}-{norm(n["name"]).replace(" ", "-")}',
                        'name': n['name'], 'city': n.get('city', ''), 'kind': 'nation', 'access': 'ask',
                        'phone': n.get('phone', ''), 'url': n.get('url', ''), 'source': entry['source'],
                        'publisher': entry['authority'], 'checked': entry['checked'], 'evidence': 'official'})
    for layer, f in (('clinic', build.CLINICS_FILE), ('college', build.COLLEGES_FILE)):
        for code, items in f['states'].items():
            for c in items:
                out.append({'layer': layer, 'area': code, 'id': '', 'name': c['name'], 'city': c.get('city', ''),
                            'kind': c.get('kind', layer) + (' ' + c['run'] if c.get('run') else ''), 'access': '',
                            'phone': c.get('phone', ''), 'url': c.get('url', ''), 'source': f['source_page'],
                            'publisher': f['publisher'], 'checked': f['retrieved'], 'evidence': 'official'})
    return out


def as_of(all_rows):
    return max(date.fromisoformat(r['checked']) for r in all_rows)


def check():
    problems, warnings = [], []
    reg = load('pipeline/sources.json')['sources']
    ids = Counter(s['id'] for s in reg)
    problems += [f'sources.json: id {k} used twice' for k, v in ids.items() if v > 1]
    for s in reg:
        for key in ('id', 'name', 'publisher', 'kind', 'evidence', 'covers', 'cadence_days'):
            if key not in s:
                problems.append(f'sources.json: {s.get("id")} has no {key}')
        if s.get('kind') not in ('dataset', 'roster', 'per-listing') or s.get('evidence') not in ('official', 'first-party', 'lead'):
            problems.append(f'sources.json: {s.get("id")} has an unknown kind or evidence level')
        if s.get('kind') == 'dataset' and not s.get('run'):
            problems.append(f'sources.json: dataset {s["id"]} needs the command that refreshes it')
    offices = load('pipeline/state-offices.json')['states']
    for code, _ in build.STATES:
        o = offices.get(code)
        if not o or o.get('status') not in ('published', 'queued', 'todo'):
            problems.append(f'state-offices.json: {code} needs a status')
        elif o['status'] != 'todo' and not (o.get('office') and o.get('checked')):
            problems.append(f'state-offices.json: {code} needs the office name and the date it was read')
    all_rows = rows()
    published = {(r['area'], norm(r['name'])) for r in all_rows}
    for item in load('pipeline/queue.json')['items']:
        for key in ('area', 'name', 'tried', 'missing', 'next'):
            if not item.get(key):
                problems.append(f'queue.json: "{item.get("name")}" has no {key}')
    # Duplicates among hand-made listings: same name in one area, or same phone in one area.
    seen_name, seen_phone = {}, {}
    for r in (x for x in all_rows if x['layer'] == 'listing'):
        key = (r['area'], norm(r['name']))
        if key in seen_name:
            problems.append(f'duplicate listing: {r["id"]} and {seen_name[key]} have the same name in {r["area"]}')
        seen_name[key] = r['id']
        if r['phone'] and len(digits(r['phone'])) == 10:
            pkey = (r['area'], digits(r['phone']))
            if pkey in seen_phone:
                warnings.append(f'same phone: {r["id"]} and {seen_phone[pkey]} in {r["area"]} (fine if one office runs both)')
            seen_phone[pkey] = r['id']
        if r['evidence'] == 'secondary':
            warnings.append(f'{r["id"]}: source is neither a government page nor the organization\'s own site')
    # A listing should not repeat a Nation office or a clinic already shown from a dataset.
    layered = {(r['area'], norm(r['name'])) for r in all_rows if r['layer'] in ('nation', 'clinic', 'college', 'state-nation')}
    for r in (x for x in all_rows if x['layer'] == 'listing'):
        if (r['area'], norm(r['name'])) in layered:
            warnings.append(f'{r["id"]} has the same name as a Nation, clinic or college already on its page')
    # State-recognized names must not repeat within a state.
    for code, entry in build.STATE_NATIONS.items():
        c = Counter(norm(n['name']) for n in entry['nations'])
        problems += [f'state-nations.json: {code} lists {k} twice' for k, v in c.items() if v > 1]
        for n in entry['nations']:
            if n.get('url') and not n['url'].startswith('https://') and not n['url'].startswith('http://'):
                problems.append(f'state-nations.json: {n["name"]} has a malformed website')
    for w in warnings:
        print('note:', w)
    for p in problems:
        print('problem:', p)
    print(f'{len(all_rows)} places checked, {len(problems)} problems, {len(warnings)} notes')
    return 1 if problems else 0


def report():
    all_rows = rows()
    today = as_of(all_rows)
    # 1. Normalized export of every published place.
    cols = ['layer', 'area', 'id', 'name', 'city', 'kind', 'access', 'phone', 'url', 'source', 'publisher', 'checked', 'evidence']
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator='\n')
    w.writeheader()
    for r in sorted(all_rows, key=lambda r: (r['area'], r['layer'], norm(r['name']), r['id'])):
        w.writerow(r)
    (ROOT / 'data/export').mkdir(parents=True, exist_ok=True)
    (ROOT / 'data/export/listings.csv').write_text(buf.getvalue(), encoding='utf-8')

    # 2. Coverage by state.
    per = defaultdict(Counter)
    for r in all_rows:
        per[r['area']][r['layer']] += 1
        if r['layer'] == 'listing':
            for k in r['kind'].split():
                per[r['area']]['need:' + k] += 1
    offices = load('pipeline/state-offices.json')['states']
    needs = [n['key'] for n in build.NEED_LIST]
    table = []
    for code, name in build.STATES:
        c = per[code]
        missing = [k for k in needs if not c['need:' + k]]
        table.append((c['listing'], c['nation'] + c['state-nation'] + c['clinic'], code, name, c, missing))
    table.sort(key=lambda t: (t[0], t[1], t[2]))
    due = sorted((r for r in all_rows if r['layer'] == 'listing'
                  and date.fromisoformat(r['checked']) + timedelta(days=REVIEW_DAYS) <= today),
                 key=lambda r: r['checked'])
    layers = [('Nation offices (BIA)', build.NATIONS_FILE['retrieved'], 'python3 scripts/import_bia.py'),
              ('Clinics (IHS)', build.CLINICS_FILE['retrieved'], 'python3 scripts/import_clinics.py'),
              ('Tribal colleges (BIA)', build.COLLEGES_FILE['retrieved'], 'python3 scripts/import_colleges.py'),
              ('Tribal lands (Census)', build.LANDS_FILE['retrieved'], 'npm run lands && python3 scripts/import_lands.py'),
              ('Canada communities (ISC)', build.CA_PLACES['retrieved'], 'python3 scripts/import_canada.py')]
    ev = Counter(r['evidence'] for r in all_rows if r['layer'] == 'listing')
    queue = load('pipeline/queue.json')['items']
    L = [f'# Coverage report', '',
         f'As of {today.isoformat()} (the newest check date in the data). Regenerate with `python3 scripts/mine.py report`; do not edit by hand.', '',
         f'{sum(1 for r in all_rows if r["layer"] == "listing")} hand-checked listings, '
         f'{sum(1 for r in all_rows if r["layer"] == "nation")} federally recognized Nation offices, '
         f'{sum(1 for r in all_rows if r["layer"] == "state-nation")} state-recognized Nations, '
         f'{sum(1 for r in all_rows if r["layer"] == "clinic")} clinics and '
         f'{sum(1 for r in all_rows if r["layer"] == "college")} tribal colleges. '
         f'Listing evidence: {ev["official"]} from a government page, {ev["first-party"]} from the organization\'s own site, '
         f'{ev["secondary"]} from another site (some are foreign government sites the check cannot tell apart; re-read these first).', '',
         '## Datasets', '', '| Layer | Retrieved | Due | Refresh |', '| --- | --- | --- | --- |']
    for label, got, cmd in layers:
        d = date.fromisoformat(got) + timedelta(days=LAYER_DAYS)
        L.append(f'| {label} | {got} | {d.isoformat()}{" (due)" if d <= today else ""} | `{cmd}` |')
    L += ['', '## States, thinnest first', '',
          'Work down this table. "Local" is hand-checked listings on the state page; "Offices" adds Nation offices, state-recognized Nations and clinics from the datasets. '
          '"State office" is whether the state\'s Indian affairs office and recognition list have been read (pipeline/state-offices.json).', '',
          '| State | Local | Offices | State office | Needs with no local listing |', '| --- | --- | --- | --- | --- |']
    for local, off, code, name, c, missing in table:
        so = offices.get(code, {}).get('status', 'todo')
        L.append(f'| {name} | {local} | {off} | {so} | {", ".join(missing) if local else "all"} |')
    L += ['', f'## Listings due for a fresh read ({REVIEW_DAYS} days)', '']
    L += [f'- {r["checked"]}: {r["name"]} ({r["area"]}), {r["source"]}' for r in due] or ['None.']
    L += ['', '## Queue: found but not published', '']
    L += [f'- **{q["area"]}: {q["name"]}** (tried {q["tried"]}). {q["missing"]} Next: {q["next"]}' for q in queue] or ['Empty.']
    (ROOT / 'pipeline/COVERAGE.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print(f'wrote pipeline/COVERAGE.md and data/export/listings.csv ({len(all_rows)} rows, as of {today})')
    return 0


def refresh():
    """Run every dataset import in the registry. Needs internet; stops at the first failure."""
    for s in load('pipeline/sources.json')['sources']:
        if s['kind'] == 'dataset':
            print(f'== {s["id"]}: {s["run"]}')
            if subprocess.call(s['run'], shell=True, cwd=ROOT) != 0:
                print(f'{s["id"]} failed: record the attempt in pipeline/queue.json; keep the old file.')
                return 1
    print('Datasets refreshed. Now: npm run map, python3 scripts/build.py, python3 scripts/mine.py report, python3 tests/test_site.py')
    return 0


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    sys.exit({'check': check, 'report': report, 'refresh': refresh}.get(cmd, lambda: print(__doc__) or 2)())
