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
pages = {p: parse(p) for p in paths + ['404.html']}

# 1. Every page has the basics.
if len(paths) != 7 + len(build.STATES):
    fail(f'expected {7 + len(build.STATES)} pages in the sitemap, found {len(paths)}')
for path, page in pages.items():
    if page.h1 != 1:
        fail(f'{path}: {page.h1} h1 headings')
    if not page.title.strip():
        fail(f'{path}: no title')
    if path != '404.html':
        if not page.description or not 50 <= len(page.description) <= 260:
            fail(f'{path}: meta description missing or an odd length')
        if page.canonical != base + ('' if path == 'index.html' else path):
            fail(f'{path}: canonical is {page.canonical}')
    if build.SITE['dedication'] not in page.text:
        fail(f'{path}: dedication missing')
    if 'goatcounter' not in page.text:
        fail(f'{path}: visit counter missing')
    if 'id="quick-exit"' not in page.text:
        fail(f'{path}: quick exit missing')
    # Crisis help leads the pages that list help (home, help, each state): one strip, with the 988 call and text links.
    # Shelter help is not repeated on every page; it lives in the housing section, which the strip links to.
    lists_help = path in ('index.html', 'help.html') or (path.startswith('states/') and path != 'states/index.html')
    if lists_help:
        if page.text.count('<aside class="urgent"') != 1 or 'href="tel:988"' not in page.text or 'href="sms:988"' not in page.text:
            fail(f'{path}: the crisis strip with the 988 call and text links must lead this page')
        if 'help.html#housing">Shelter and housing help</a>' not in page.text:
            fail(f'{path}: the crisis strip must link to shelter and housing help')
    if 'class="foothelp"' in page.text or 'No safe place to sleep tonight' in page.text.split('<main', 1)[0]:
        fail(f'{path}: help lines are not repeated in the page chrome')

# 2. Links inside the site lead somewhere, and links out are well formed.
for path, page in pages.items():
    if path == '404.html':
        continue
    folder = Path(path).parent
    for href in page.hrefs:
        if href.startswith(('mailto:', 'tel:', 'sms:')):
            if href.startswith('tel:') and not re.match(r'^tel:(\+1\d{10}|\d{3})$', href):
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
        if anchor and target_path in pages and anchor not in pages[target_path].ids:
            fail(f'{path}: link to missing anchor {href}')

# 3. Every listing is on the page it belongs to, with its phone number and its source.
for record in build.RES:
    path = 'help.html' if record['area'] == 'US' else f'states/{build.STATE_SLUG[record["area"]]}.html'
    page = pages[path]
    if f'r-{record["id"]}' not in page.ids:
        fail(f'{path}: listing {record["id"]} is missing')
        continue
    start = page.text.index(f'id="r-{record["id"]}"')
    block = page.text[start:page.text.index('</article>', start)]
    if record.get('phone') and f'tel:{build.tel(record["phone"])}' not in block:
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

# 6. The map covers every state and shows every office that could be placed.
home = pages['index.html']
for code, _ in build.STATES:
    if f'href="states/{build.STATE_SLUG[code]}.html"><title>' not in home.text:
        fail(f'index.html: map has no link for {code}')
if home.circles != len(build.MAP['points']):
    fail(f'index.html: {home.circles} dots on the map, expected {len(build.MAP["points"])}')
if {p['id'] for p in build.MAP['points']} - set(build.NATION):
    fail('data/map/us.json is out of date: run npm run map')

if problems:
    print(f'{len(problems)} problem(s):')
    for message in problems:
        print('  -', message)
    sys.exit(1)
print(f'ok: {len(pages)} pages, {len(build.RES)} listings, {len(build.NATIONS)} Nation offices checked')
