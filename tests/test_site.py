#!/usr/bin/env python3
"""Checks the built pages against the data they were built from.

    python3 scripts/build.py && python3 tests/test_site.py

Needs only Python 3. Exits with an error and a list of problems if anything is off.
"""
import json, re, sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build  # noqa: E402  (the builder's own data loaders and helpers)

problems = []


def fail(message):
    problems.append(message)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.hrefs, self.h1, self.title, self.description, self.canonical = set(), [], 0, '', None, None
        self._in_title = False
        self.circles = 0
        self.svgs, self.uses, self.figures = [], [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            if a['id'] in self.ids:
                fail(f'{self.name}: id used twice: {a["id"]}')
            self.ids.add(a['id'])
        if tag in ('a', 'link') and a.get('href') and a.get('rel') != 'canonical':
            self.hrefs.append(a['href'])
        if tag == 'link' and a.get('rel') == 'canonical':
            self.canonical = a.get('href')
        if tag == 'meta' and a.get('name') == 'description':
            self.description = a.get('content')
        if tag == 'h1':
            self.h1 += 1
        if tag == 'title' and not self.title:
            self._in_title = True
        if tag == 'circle':
            self.circles += 1
        if tag == 'svg':
            self.svgs.append(a)
        if tag == 'use':
            self.uses.append(a.get('href') or '')

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def parse(path):
    page = Page()
    page.name = path
    page.text = (ROOT / path).read_text(encoding='utf-8')
    page.feed(page.text)
    return page


sitemap = (ROOT / 'sitemap.xml').read_text(encoding='utf-8')
base = build.SITE['base_url']
paths = [u[len(base):] or 'index.html' for u in re.findall(r'<loc>([^<]+)</loc>', sitemap)]
demo_pages = [f'communities/{c["slug"]}.html' for c in build.COMMUNITIES if c.get('demo')]
pages = {p: parse(p) for p in paths + ['404.html'] + demo_pages}

# 1. Every page has the basics.
world_pages = 1 + sum(1 for c in build.COUNTRIES if c['slug'])
expected = 11 + world_pages + len(build.STATES) + len(build.LIVE_COMMUNITIES)
if len(paths) != expected:
    fail(f'expected {expected} pages in the sitemap, found {len(paths)}')
for path, page in pages.items():
    if page.h1 != 1:
        fail(f'{path}: {page.h1} h1 headings')
    if not page.title.strip():
        fail(f'{path}: no title')
    if path != '404.html':
        if path in demo_pages:
            if '<meta name="robots" content="noindex">' not in page.text or 'Example page.' not in page.text:
                fail(f'{path}: an example page must say so and be noindex')
        if not page.description or not 50 <= len(page.description) <= 260:
            fail(f'{path}: meta description missing or an odd length')
        if page.canonical != base + ('' if path == 'index.html' else path):
            fail(f'{path}: canonical is {page.canonical}')
    if build.SITE['dedication'] not in page.text:
        fail(f'{path}: dedication missing')
    if 'goatcounter' not in page.text:
        fail(f'{path}: visit counter missing')
    # No quick-exit bar and no crisis box on any page: the pages read as ordinary resource guides.
    # Help lines stay in the listings, reached from one plain footer link.
    if 'quick-exit' in page.text or 'class="exit"' in page.text or 'aria-label="Quick exit"' in page.text:
        fail(f'{path}: the quick exit bar should not be on the page')
    if '<aside class="urgent' in page.text or 'Need help right now?' in page.text:
        fail(f'{path}: the crisis box should not be on the page')
    if 'help.html#safety">Help lines</a>' not in page.text.split('<footer', 1)[-1]:
        fail(f'{path}: the footer must link to the help lines')
    if 'class="foothelp"' in page.text or 'No safe place to sleep tonight' in page.text.split('<main', 1)[0]:
        fail(f'{path}: help lines are not repeated in the page chrome')

# Crisis and safety lines stay findable in the help page's own safety section, where the footer link points.
safety = pages['help.html'].text.split('id="safety"', 1)[-1].split('<section class="need"', 1)[0]
for line in ('href="tel:988"', 'href="sms:988"', 'href="tel:+18447628483"', 'href="tel:+18883737888"'):
    if line not in safety:
        fail(f'help.html: {line} is missing from the safety section')

# 1b. Every landing page is its own: no two pages share a title, a description or a heading, and each opens with a lede.
for label, getter in (('title', lambda pg: pg.title.strip()), ('description', lambda pg: pg.description),
                      ('h1', lambda pg: re.search(r'<h1[^>]*>(.*?)</h1>', pg.text).group(1))):
    seen = {}
    for path, page in pages.items():
        if path == '404.html':
            continue
        value = getter(page)
        if value in seen:
            fail(f'{path}: same {label} as {seen[value]}')
        seen[value] = path
for path, page in pages.items():
    if path not in ('404.html', 'about.html') and '<p class="lede">' not in page.text:
        fail(f'{path}: no opening lede')
if 'class="chips iam"' not in pages['index.html'].text:
    fail('index.html: the "I\'m..." chooser is missing')

# 1c. Free community pages: each says who writes it and when it was updated, and is linked from the group's listing and the hub.
for c in build.COMMUNITIES:
    path = f'communities/{c["slug"]}.html'
    text = pages[path].text
    if f'This page is written and maintained by {build.E(c["maintained_by"])}. Last updated {build.nice_date(c["updated"])}.' not in text:
        fail(f'{path}: the "written and maintained by" line is missing')
    if not c.get('demo'):
        if f'communities/{c["slug"]}.html' not in pages['community.html'].text:
            fail(f'community.html: no link to {path}')
        if c.get('nation_id') and f'communities/{c["slug"]}.html' not in pages['nations.html'].text:
            fail(f'nations.html: no link to {path}')
        if c.get('help') and f'communities/{c["slug"]}.html' not in pages['support.html'].text:
            fail(f'support.html: no link to {path}')
if f'mailto:{build.SITE["intake_email"]}' not in pages['free-page.html'].text:
    fail('free-page.html: the request address is missing')

# 2. Links inside the site lead somewhere, and links out are well formed.
for path, page in pages.items():
    if path == '404.html':
        continue
    folder = Path(path).parent
    for href in page.hrefs:
        if href.startswith(('mailto:', 'tel:', 'sms:')):
            if href.startswith('tel:') and not re.match(r'^tel:(\+1\d{10}(,\d{1,6})?|\+(?!1)\d{8,14}|\*?\d{3,6})$', href):
                fail(f'{path}: odd phone link {href}')
            continue
        if href.startswith('http://') or href.startswith('https://'):
            if ' ' in href:
                fail(f'{path}: space in link {href}')
            continue
        target, _, anchor = href.partition('#')
        target_path = path if not target else str((folder / target)).replace('\\', '/')
        target_path = re.sub(r'(^|/)[^/]+/\.\./', r'\1', target_path)
        if not (ROOT / target_path).is_file():
            fail(f'{path}: link to missing file {href}')
            continue
        # The map opens a historic site from index.html#hs-<id> in the browser; there is no element with that id.
        if target_path == 'index.html' and anchor.startswith('hs-') and anchor[3:] in {h['id'] for h in build.HISTORIC}:
            continue
        if anchor and target_path in pages and anchor not in pages[target_path].ids:
            fail(f'{path}: link to missing anchor {href}')

# 3. Every listing is on the page it belongs to, with its phone number and its source.
for record in build.RES + build.WORLD:
    if record['area'] in build.COUNTRY and build.COUNTRY[record['area']]['slug']:
        path = f'world/{build.COUNTRY[record["area"]]["slug"]}.html'
    else:
        path = 'help.html' if record['area'] == 'US' else f'states/{build.STATE_SLUG[record["area"]]}.html'
    page = pages[path]
    if f'r-{record["id"]}' not in page.ids:
        fail(f'{path}: listing {record["id"]} is missing')
        continue
    start = page.text.index(f'id="r-{record["id"]}"')
    block = page.text[start:page.text.index('</article>', start)]
    if record.get('phone') and f'tel:{build.tel_of(record)}' not in block:
        fail(f'{path}: {record["id"]} has no phone link')
    if build.E(record['source']) not in block or 'Checked ' not in block:
        fail(f'{path}: {record["id"]} has no source or date')
    if build.ACCESS[record['access']]['label'] not in block:
        fail(f'{path}: {record["id"]} has no label saying who can use it')

# 4. Every Nation office is in the directory and on its own state's page, and nowhere it should not be.
directory = pages['nations.html']
for nation in build.NATIONS:
    if f'n-{nation["id"]}' not in directory.ids:
        fail(f'nations.html: {nation["id"]} is missing')
    home = f'states/{build.STATE_SLUG[nation["state"]]}.html'
    if f'n-{nation["id"]}' not in pages[home].ids:
        fail(f'{home}: {nation["id"]} is missing')
# Nations recognized by a state: each is on its own state's page and in the directory's own section, never mixed into the federal list.
for code, entry in build.STATE_NATIONS.items():
    if not entry['source'].startswith('https://') or not entry.get('checked') or not entry.get('authority'):
        fail(f'state-nations.json: {code} needs an official source, authority and check date')
    federal = {n['name'].lower() for n in build.NATIONS}
    for n in entry['nations']:
        if n['name'].lower() in federal:
            fail(f'state-nations.json: {n["name"]} is already on the federal list')
        if n['name'] not in pages[f'states/{build.STATE_SLUG[code]}.html'].text or n['name'] not in directory.text:
            fail(f'{n["name"]} is missing from its state page or the directory')
# Clinics: every facility in data/clinics.json is on its state's page, and no staff names or emails are kept.
raw_clinics = (ROOT / 'data/clinics.json').read_text() if 'ROOT' in globals() else open('data/clinics.json', encoding='utf-8').read()
if 'POC_' in raw_clinics or 'mailto:' in raw_clinics:
    fail('data/clinics.json must not hold staff contacts')
for code, items in build.CLINICS.items():
    text = pages[f'states/{build.STATE_SLUG[code]}.html'].text
    if 'id="clinics-h"' not in text:
        fail(f'{code}: the clinics section is missing')
    for c in items:
        if build.E(c['name']) not in text:
            fail(f'{code}: clinic {c["name"]} is missing')
# Tribal colleges: each on its state page and on the community page; no staff names or emails kept.
raw_colleges = open('data/colleges.json', encoding='utf-8').read()
if '@' in raw_colleges or 'President' in raw_colleges:
    fail('data/colleges.json must not hold staff contacts')
for code, items in build.COLLEGES.items():
    text = pages[f'states/{build.STATE_SLUG[code]}.html'].text
    for c in items:
        if build.E(c['name']) not in text or build.E(c['name']) not in pages['community.html'].text:
            fail(f'{code}: tribal college {c["name"]} is missing')
# Reservations and tribal lands: every area in the Census file is on its state's page.
for code, areas in build.LANDS.items():
    text = pages[f'states/{build.STATE_SLUG[code]}.html'].text
    if 'id="lands-h"' not in text:
        fail(f'{code}: the tribal lands section is missing')
    for a in areas:
        if build.E(a['name']) not in text:
            fail(f'{code}: {a["name"]} is missing from the state page')
if 'id="state-recognized"' not in directory.text:
    fail('nations.html: the state-recognized section is missing')
for code, _ in build.STATES:
    path = f'states/{build.STATE_SLUG[code]}.html'
    allowed = {n['id'] for n in build.NATIONS if n['state'] == code} | set(build.STATE_NOTES.get(code, {}).get('ties', []))
    for found in pages[path].ids:
        if found.startswith(f'n-st-{code.lower()}-'):
            continue  # recognized by this state, from data/state-nations.json; checked below
        if found.startswith('n-') and found[2:] not in allowed:
            fail(f'{path}: lists {found[2:]}, which belongs to another state')

# 5. The Nations data holds offices, not people.
raw = (ROOT / 'data/nations.json').read_text(encoding='utf-8')
for banned in ('firstname', 'lastname', 'salutation', 'jobtitle', '"email"', '"fax"'):
    if banned in raw:
        fail(f'data/nations.json contains {banned}; leader names and personal contacts must stay out')
if len(build.NATIONS) < 550:
    fail('data/nations.json looks truncated')

# 6. The state map covers every state and shows every office that could be placed.
statemap = pages['states/index.html']
for code, _ in build.STATES:
    if f'href="../states/{build.STATE_SLUG[code]}.html"><title>' not in statemap.text:
        fail(f'states/index.html: map has no link for {code}')
if statemap.circles != len(build.MAP['points']):
    fail(f'states/index.html: {statemap.circles} dots on the map, expected {len(build.MAP["points"])}')

# 7. The map finder on the home page: every place has a position and a way in, and nothing is left off.
finder = json.loads((ROOT / 'assets/finder/data.json').read_text(encoding='utf-8'))
col = {name: i for i, name in enumerate(finder['cols'])}
home = pages['index.html']
for asset in ('assets/finder.js', 'assets/vendor/leaflet.js', 'assets/vendor/leaflet.markercluster.js', 'assets/finder/lands.geojson'):
    if not (ROOT / asset).is_file():
        fail(f'{asset} is missing')
if 'assets/finder.js' not in home.text or 'id="map"' not in home.text:
    fail('index.html: the map finder is missing')
# A clean opening page: the list stays hidden until someone picks, and a visible prompt says how to start.
if not re.search(r'<div class="results" id="f-results" hidden>', home.text):
    fail('index.html: the results list should start hidden until a pick')
if not re.search(r'<p id="f-status" class="pick-prompt" role="status">[^<]{20,}</p>', home.text):
    fail('index.html: the prompt telling people how to start is missing')
if 'class="who-sec"' not in home.text:
    fail('index.html: the "Start where you are" panels should open only from the chooser')
codes = {c['code'] for c in finder['countries']}
for row in finder['points']:
    lat, lon = row[col['lat']], row[col['lon']]
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        fail(f'finder: {row[col["name"]]} has a bad position')
    if row[col['country']] not in codes or row[col['kind']] not in finder['kinds']:
        fail(f'finder: {row[col["name"]]} has an unknown country or kind')
    if not (row[col['tel']] or row[col['url']] or row[col['page']]):
        fail(f'finder: {row[col["name"]]} has no way to reach it')
    page_link = row[col['page']].partition('#')[0]
    if page_link and not (ROOT / page_link).is_file():
        fail(f'finder: {row[col["name"]]} links to missing page {page_link}')
    for need in filter(None, row[col['needs']].split(',')):
        if need not in build.NEED and need not in build.FINDER_EXTRA:
            fail(f'finder: {row[col["name"]]} has unknown need {need}')
# Historic sites: each one is open to visitors, has its official page and a place on the map and on the history page.
hs_ids = set()
proud = pages['proud-history.html'].text
for h in build.HISTORIC:
    if h['id'] in hs_ids or not re.fullmatch(r'[a-z0-9-]+', h['id']):
        fail(f'historic site {h["name"]}: id is missing, bad or used twice')
    hs_ids.add(h['id'])
    if not h['url'].startswith('https://') or h['state'] not in build.STATE_NAME:
        fail(f'historic site {h["name"]}: needs an https official page and a state')
    if f'id="hs-{h["id"]}"' not in proud:
        fail(f'proud-history.html: {h["name"]} is not listed')
if sum(1 for r in finder['points'] if r[col['kind']] == 'history') != len(build.HISTORIC):
    fail('finder: not every historic site is on the map')
placed = sum(1 for n in build.NATIONS if n.get('lat') is not None)
if sum(1 for r in finder['points'] if r[col['kind']] == 'nation') != placed:
    fail('finder: not every placed Nation office is on the map')
if sum(1 for r in finder['points'] if r[col['kind']] == 'fn') != len(build.CA_PLACES['first_nations']['items']):
    fail('finder: not every First Nation in Canada is on the map')
canada = pages['world/canada.html'].text
for n in build.CA_PLACES['first_nations']['items']:
    if build.E(n['name']) not in canada:
        fail(f'world/canada.html: {n["name"]} is missing')
for c in build.COUNTRIES:
    for u in (c['urgent'] or []) if c['slug'] else []:
        if f'href="tel:{u["tel"]}"' not in pages[f'world/{c["slug"]}.html'].text:
            fail(f'world/{c["slug"]}.html: the help line {u["phone"]} is not listed on the page')
if {p['id'] for p in build.MAP['points']} - set(build.NATION):
    fail('data/map/us.json is out of date: run npm run map')

# 8. Pictures: every symbol exists, every picture is either hidden as decoration or named, and charts keep their words.
symbols = set(re.findall(r'<symbol id="([^"]+)"', (ROOT / 'assets/icons.svg').read_text(encoding='utf-8')))
for path, page in pages.items():
    folder = Path(path).parent
    for href in page.uses:
        file, _, sym = href.removeprefix(base).partition('#')  # the 404 page links from the site's root
        target = re.sub(r'(^|/)[^/]+/\.\./', r'\1', str(folder / file).replace('\\', '/'))
        if target != 'assets/icons.svg' or sym not in symbols:
            fail(f'{path}: symbol {href} not found in assets/icons.svg')
    for a in page.svgs:
        if a.get('aria-hidden') == 'true':
            if a.get('role') or a.get('focusable') != 'false':
                fail(f'{path}: a decorative picture must be hidden only (aria-hidden, focusable="false")')
        elif a.get('role') in ('img', 'group'):
            names = (a.get('aria-labelledby') or '').split()
            if not names or any(n not in page.ids for n in names):
                fail(f'{path}: a picture with role {a["role"]} needs aria-labelledby pointing at its title')
        else:
            fail(f'{path}: every picture needs aria-hidden="true" or a role and a name')
    for fig in re.findall(r'<figure class="chart[^"]*">(.*?)</figure>', page.text, re.S):
        if '<figcaption>' not in fig:
            fail(f'{path}: a chart has no caption')
        if '<svg' in fig and '<table>' not in fig:
            fail(f'{path}: a drawn chart needs its numbers in a table too')
        for num in re.findall(r'<span class="num">(.*?)</span>', fig):
            if not re.search(r'\d', num):
                fail(f'{path}: a bar has no number written beside it')
tiles = pages['nations.html'].text
for code, _ in build.STATES:
    if f'>{code}</text>' not in tiles:
        fail(f'nations.html: the tile map has no square for {code}')
for code, name in build.STATES:
    text = pages[f'states/{build.STATE_SLUG[code]}.html'].text
    if f'<g class="here">' not in text or f'>{code}</text></g>' not in text or f'Where {build.E(name)} is' not in text:
        fail(f'states/{build.STATE_SLUG[code]}.html: the locator map does not mark {name}')
# The timeline uses only dates its stories give, and the What works chart only numbers its results list.
for year, i, _ in build.PROUD_DATES:
    _, _, what, more, _ = build.PROUD[i]
    if str(year) not in what + more:
        fail(f'proud-history.html: {year} on the timeline is not in the story it links to')
for w in build.WORKS:
    for label, value in w.get('chart', []):
        if not any(f'{value} percent' in r for r in w['results']):
            fail(f'what-works.html: the chart shows {value} percent, which is not in the results')

if problems:
    print(f'{len(problems)} problem(s):')
    for message in problems:
        print('  -', message)
    sys.exit(1)
print(f'ok: {len(pages)} pages, {len(build.RES) + len(build.WORLD)} listings, {len(finder["points"])} map places, {len(build.NATIONS)} Nation offices checked')
