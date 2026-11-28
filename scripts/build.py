#!/usr/bin/env python3
"""Builds every page of the site from the files in data/.

    python3 scripts/build.py

Needs only Python 3. Edit the data files, never the built pages.
"""
import html, json, re, sys, urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def E(value):
    return html.escape(str(value), quote=True)


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


SITE = load('data/site.json')
NEEDS_FILE = load('data/needs.json')
NEED_LIST = NEEDS_FILE['needs']
NEED = {n['key']: n for n in NEED_LIST}
ACCESS = NEEDS_FILE['access']
NATIONS_FILE = load('data/nations.json')
NATIONS = NATIONS_FILE['nations']
STATE_NATIONS = load('data/state-nations.json')['states']
LANDS_FILE = load('data/lands.json')
CLINICS_FILE = load('data/clinics.json')
COLLEGES_FILE = load('data/colleges.json')
COLLEGES = COLLEGES_FILE['states']
CLINICS = CLINICS_FILE['states']
LANDS = LANDS_FILE['states']
NATION = {n['id']: n for n in NATIONS}
STATE_NOTES = load('data/states.json')
MAP = load('data/map/us.json')
COUNTRIES_FILE = load('data/world/countries.json')
COUNTRIES = COUNTRIES_FILE['countries']
COUNTRY = {c['code']: c for c in COUNTRIES}
CA_PLACES = load('data/world/ca-places.json')
# Native historic and cultural sites that are open to visitors, each with the official page of whoever runs it.
HISTORIC_FILE = load('data/historic-sites.json')
HISTORIC = HISTORIC_FILE['sites']

STATES = [
    ('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'), ('CA', 'California'),
    ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'), ('DC', 'District of Columbia'),
    ('FL', 'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'), ('ID', 'Idaho'), ('IL', 'Illinois'),
    ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'), ('KY', 'Kentucky'), ('LA', 'Louisiana'),
    ('ME', 'Maine'), ('MD', 'Maryland'), ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'),
    ('MS', 'Mississippi'), ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'),
    ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), ('NY', 'New York'),
    ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'), ('OK', 'Oklahoma'), ('OR', 'Oregon'),
    ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'), ('SD', 'South Dakota'),
    ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'), ('VT', 'Vermont'), ('VA', 'Virginia'),
    ('WA', 'Washington'), ('WV', 'West Virginia'), ('WI', 'Wisconsin'), ('WY', 'Wyoming'),
]
STATE_NAME = dict(STATES)
STATE_SLUG = {code: name.lower().replace(' ', '-') for code, name in STATES}
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
          'October', 'November', 'December']


def load_resources():
    records = []
    for path in sorted((ROOT / 'data/resources').glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        for record in data['records']:
            record['area'] = data['area']
            records.append(record)
    return records


RES = load_resources()
RES_BY_ID = {r['id']: r for r in RES}


def load_world():
    records = []
    for c in COUNTRIES:
        path = ROOT / f'data/world/{c["code"].lower()}.json'
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        for record in data['records']:
            record['area'] = data['area']
            records.append(record)
    return records


WORLD = load_world()


# ---------- free community pages: one data file per group, written and maintained by that group ----------

COMMUNITY_KINDS = {
    'nation': 'Nation', 'reservation': 'Reservation community', 'program': 'Tribal program',
    'urban': 'Urban Indian organization', 'powwow': 'Powwow committee', 'language': 'Language program',
    'business': 'Native-owned business', 'grassroots': 'Community group',
}
ASK_KINDS = {
    'donate': 'Donate', 'volunteer': 'Volunteer', 'attend': 'Come to an event', 'buy': 'Buy from us',
    'share': 'Share the word', 'supplies': 'Supplies needed',
}
ASK_ICON = {'donate': 'coins', 'volunteer': 'clock', 'attend': 'calendar', 'buy': 'bag', 'share': 'share', 'supplies': 'box'}


def load_communities():
    out = []
    for path in sorted((ROOT / 'data/communities').glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        data['_file'] = path.name
        out.append(data)
    return out


COMMUNITIES = load_communities()
LIVE_COMMUNITIES = [c for c in COMMUNITIES if not c.get('demo')]
COMMUNITY_BY_NATION = {c['nation_id']: c for c in LIVE_COMMUNITIES if c.get('nation_id')}
COMMUNITY_BY_LISTING = {c['listing_id']: c for c in LIVE_COMMUNITIES if c.get('listing_id')}


def check_communities():
    """A community page exists only at the group's own request, says who maintains it, and points only at real files."""
    problems = []
    date = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    slugs = Counter(c.get('slug') for c in COMMUNITIES)
    for c in COMMUNITIES:
        f = c['_file']
        for field in ('slug', 'name', 'kind', 'place', 'maintained_by', 'requested', 'updated', 'intro'):
            if not c.get(field):
                problems.append(f'communities/{f}: missing {field}')
        if c.get('slug') and f != c['slug'] + '.json':
            problems.append(f'communities/{f}: file name must be the slug')
        if slugs[c.get('slug')] > 1 or c.get('slug') in ('index', 'example') and not c.get('demo'):
            problems.append(f'communities/{f}: slug is taken')
        if c.get('kind') not in COMMUNITY_KINDS:
            problems.append(f'communities/{f}: unknown kind {c.get("kind")}')
        for field in ('requested', 'updated'):
            if c.get(field) and not date.match(c[field]):
                problems.append(f'communities/{f}: {field} must be a date like 2026-11-23')
        if not c.get('demo') and not c.get('request_note'):
            problems.append(f'communities/{f}: say how the group asked for this page (request_note); pages are made only at a group\'s own request')
        if c.get('nation_id') and c['nation_id'] not in NATION:
            problems.append(f'communities/{f}: no Nation with id {c["nation_id"]}')
        if c.get('listing_id') and c['listing_id'] not in RES_BY_ID:
            problems.append(f'communities/{f}: no listing with id {c["listing_id"]}')
        for ask in c.get('help', []):
            if ask.get('kind') not in ASK_KINDS or not ask.get('text'):
                problems.append(f'communities/{f}: each "help" entry needs a kind ({", ".join(ASK_KINDS)}) and text')
            if ask.get('until') and not date.match(ask['until']):
                problems.append(f'communities/{f}: help "until" must be a date')
        for ev in c.get('events', []):
            if not ev.get('title') or not date.match(ev.get('date', '')):
                problems.append(f'communities/{f}: each event needs a title and a date')
        for img in ([c['logo']] if c.get('logo') else []) + c.get('photos', []):
            if not img.get('alt'):
                problems.append(f'communities/{f}: every picture needs alt text')
            if not (ROOT / 'assets/communities' / c.get('slug', '') / img.get('src', '')).is_file():
                problems.append(f'communities/{f}: picture not found: assets/communities/{c.get("slug")}/{img.get("src")}')
        for link in [x.get('url') for x in c.get('links', []) + c.get('help', []) + c.get('events', []) + c.get('programs', [])] + [c.get('contact', {}).get('url')]:
            if link and not link.startswith('https://'):
                problems.append(f'communities/{f}: links must start with https:// ({link})')
    return problems


def check_data():
    """Stop the build on data mistakes that would put a wrong or broken listing on a page."""
    problems = []
    if len(RES_BY_ID) != len(RES):
        problems.append('two listings share an id: ' + ', '.join(k for k, v in Counter(r['id'] for r in RES).items() if v > 1))
    ids = Counter(r['id'] for r in RES + WORLD)
    if max(ids.values()) > 1:
        problems.append('two listings share an id: ' + ', '.join(k for k, v in ids.items() if v > 1))
    for r in RES + WORLD:
        for field in ('id', 'name', 'need', 'access', 'what', 'who', 'start', 'source', 'checked'):
            if not r.get(field):
                problems.append(f'{r.get("id", "?")}: missing {field}')
        if r.get('need') not in NEED:
            problems.append(f'{r.get("id")}: unknown need {r.get("need")}')
        for key in r.get('also', []):
            if key not in NEED:
                problems.append(f'{r["id"]}: unknown need in also: {key}')
        if r.get('access') not in ACCESS:
            problems.append(f'{r.get("id")}: unknown access {r.get("access")}')
        if r['area'] != 'US' and r['area'] not in STATE_NAME and r['area'] not in COUNTRY:
            problems.append(f'{r["id"]}: unknown area {r["area"]}')
        if not (r.get('phone') or r.get('sms') or r.get('url') or r.get('email')):
            problems.append(f'{r["id"]}: no way to reach it')
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', r.get('checked', '')):
            problems.append(f'{r.get("id")}: checked must be a date like 2026-11-17')
    for c in COUNTRIES:
        if c['code'] in STATE_NAME:
            problems.append(f'countries.json: {c["code"]} is also a state code; use another code')
    for code, note in STATE_NOTES.items():
        if code not in STATE_NAME:
            problems.append(f'states.json: unknown state {code}')
        for nid in note.get('ties', []):
            if nid not in NATION:
                problems.append(f'states.json {code}: no Nation with id {nid}')
    for n in NATIONS:
        if n['state'] not in STATE_NAME:
            problems.append(f'nations.json: {n["id"]} has unknown state {n["state"]}')
    problems += check_communities()
    if problems:
        sys.exit('Data problems:\n  ' + '\n  '.join(problems))


def tel(number):
    digits = re.sub(r'\D', '', number)
    if len(digits) == 10:
        return '+1' + digits
    if len(digits) == 11 and digits.startswith('1'):
        return '+' + digits
    return digits


def nice_date(iso):
    year, month, day = iso.split('-')
    return f'{MONTHS[int(month) - 1]} {int(day)}, {year}'


def records_for(area, need=None, primary_only=True):
    out = []
    for r in RES:
        if r['area'] != area:
            continue
        if need and not (r['need'] == need or (not primary_only and need in r.get('also', []))):
            continue
        out.append(r)
    return sorted(out, key=lambda r: (r.get('urgent', 99), 0))  # stable: keeps file order


# ---------- pieces ----------

def tel_of(r):
    """A listing outside North America carries its own dialable number in 'tel'."""
    return r.get('tel') or tel(r['phone'])


def actions(r):
    out = []
    if r.get('phone'):
        out.append(f'<a class="btn call" href="tel:{tel_of(r)}">Call {E(r["phone"])}</a>')
    if r.get('sms'):
        s = r['sms']
        href = 'sms:' + s['to'] + ('?&body=' + urllib.parse.quote(s['body']) if s.get('body') else '')
        out.append(f'<a class="btn text" href="{E(href)}">{E(s["label"])}</a>')
    if r.get('email'):
        out.append(f'<a class="btn line" href="mailto:{E(r["email"])}">Email {E(r["email"])}</a>')
    if r.get('url'):
        out.append(f'<a class="btn line" href="{E(r["url"])}">{E(r.get("url_label") or "Website")}</a>')
    return out


def card(r, level=3, up=''):
    h = f'h{level}'
    access = ACCESS[r['access']]
    tags = f'<span class="tag acc-{r["access"]}">{E(access["label"])}</span>'
    if r.get('place'):
        tags += f' <span class="tag place">{E(r["place"])}</span>'
    parts = [f'<article class="card" id="r-{r["id"]}" data-access="{r["access"]}">',
             f'<{h}>{E(r["name"])}</{h}>', f'<p class="tags">{tags}</p>', f'<p>{E(r["what"])}</p>', '<dl>',
             f'<dt>Who it is for</dt><dd>{E(r["who"])}</dd>', f'<dt>How to start</dt><dd>{E(r["start"])}</dd>']
    if r.get('address'):
        parts.append(f'<dt>Address</dt><dd>{E(r["address"])}</dd>')
    parts.append('</dl>')
    if r.get('note'):
        parts.append(f'<p class="note">{E(r["note"])}</p>')
    acts = actions(r)
    if acts:
        parts.append('<p class="actions">' + ' '.join(acts) + '</p>')
    if r.get('phone_note'):
        parts.append(f'<p class="meta">{E(r["phone"])}: {E(r["phone_note"])}.</p>')
    if r['id'] in COMMUNITY_BY_LISTING:
        cp = COMMUNITY_BY_LISTING[r['id']]
        parts.append(f'<p class="cplink"><a href="{up}communities/{cp["slug"]}.html">{E(cp["name"])}: their own community page</a></p>')
    if r.get('more'):
        parts.append('<p class="more">More: ' + ' · '.join(
            f'<a href="{E(m["url"])}">{E(m["label"])}</a>' for m in r['more']) + '</p>')
    parts.append(f'<p class="meta">Checked {nice_date(r["checked"])}. <a href="{E(r["source"])}">Source</a></p></article>')
    return ''.join(parts)


def prep(need, level=3):
    h = f'h{level}'
    return ('<details class="prep"><summary>Before you call: what to have ready and what to ask</summary>'
            f'<{h}>Have ready</{h}><ul>' + ''.join(f'<li>{E(x)}</li>' for x in need['ready']) + '</ul>'
            f'<{h}>Ask</{h}><ul>' + ''.join(f'<li>{E(x)}</li>' for x in need['ask']) + '</ul>'
            '<p class="meta">General reminders written for this site. Each program sets its own rules.</p></details>')


def nation_item(n, show_state=False, up=''):
    where = ', '.join(x for x in [n.get('city'), STATE_NAME[n['state']] if show_state else None] if x)
    contact = []
    if n.get('phone'):
        contact.append(f'<a href="tel:{n["phone"]["tel"]}">{E(n["phone"]["display"])}</a>')
    if n.get('url'):
        contact.append(f'<a href="{E(n["url"])}">Website</a>')
    if n['id'] in COMMUNITY_BY_NATION:
        contact.append(f'<a href="{up}communities/{COMMUNITY_BY_NATION[n["id"]]["slug"]}.html">Community page</a>')
    key = ' '.join(x for x in [n['name'], n.get('also') or '', n.get('city') or '', STATE_NAME[n['state']]]).lower()
    out = f'<li id="n-{n["id"]}" data-k="{E(key)}"><span class="nm">{E(n["name"])}</span>'
    if n.get('also'):
        out += f' <span class="aka">(also listed as {E(n["also"])})</span>'
    if where:
        out += f' <span class="where">{E(where)}</span>'
    if contact:
        out += ' <span class="contact">' + ' · '.join(contact) + '</span>'
    return out + '</li>'


def map_svg(up=''):
    counts = Counter(n['state'] for n in NATIONS)
    shapes = []
    for s in MAP['states']:
        n = counts.get(s['code'], 0)
        label = f'{s["name"]}: ' + (f'{n} government office{"s" if n != 1 else ""} listed' if n else 'national help')
        shapes.append(f'<a href="{up}states/{STATE_SLUG[s["code"]]}.html"><title>{E(label)}</title><path d="{s["d"]}"/></a>')
    dots = ''.join(f'<circle cx="{p["x"]}" cy="{p["y"]}" r="2.3"/>' for p in MAP['points'])
    return (f'<svg class="usmap" viewBox="0 0 {MAP["width"]} {MAP["height"]}" role="group" aria-labelledby="map-t map-d">'
            '<title id="map-t">Map of the United States</title>'
            '<desc id="map-d">Each dot marks the government office of a federally recognized Nation. '
            'Each state is a link to that state\'s page. The same links are in the list after the map.</desc>'
            f'<g class="st">{"".join(shapes)}</g><g class="dots" aria-hidden="true">{dots}</g></svg>')


# ---------- pictures: symbols, charts and step diagrams ----------
# Every picture re-presents what the page or the data already says, and the words or numbers are always on the page
# as text too. Symbols are drawn for this site in assets/icons.svg; nothing is loaded from elsewhere.

NEED_ICON = {'safety': 'safety', 'health': 'health', 'recovery': 'recovery', 'family': 'family', 'school': 'school',
             'housing': 'housing', 'money': 'money', 'work': 'work', 'legal': 'legal', 'nation': 'nation',
             'elders': 'elders', 'veterans': 'veterans', 'community': 'community'}


def icon(name, up='', cls='ico'):
    """A small symbol beside words that already say the same thing, so screen readers skip it."""
    if not name:
        return ''
    return (f'<svg class="{cls}" width="20" height="20" aria-hidden="true" focusable="false">'
            f'<use href="{up}assets/icons.svg#i-{name}"/></svg>')


def need_icon(key, up='', cls='ico'):
    return icon(NEED_ICON.get(key), up, cls)


def bar_chart(caption, rows, scale=None, note='', side=False):
    """A bar chart drawn in HTML. Each row is a label, a bar and its number written out, so the chart is its own text
    equivalent and reflows on a small screen. rows: (label HTML, value, value as words). scale: the value of a full
    bar (the largest value if not given). side: short labels sit beside their bars on wider screens."""
    top = scale or max(v for _, v, _ in rows) or 1
    items = ''.join(
        f'<li><span class="lab">{label}</span><span class="row"><span class="track" aria-hidden="true">'
        f'<span class="bar" style="width:{100 * v / top:.1f}%"></span></span><span class="num">{text}</span></span></li>'
        for label, v, text in rows)
    return f'<figure class="chart"><figcaption>{caption}</figcaption><ul class="bars{" side" if side else ""}">{items}</ul>{note}</figure>'


# A square for each state, placed roughly where the state is (column, row), so every state reads the same size.
TILE_GRID = {
    'AK': (0, 0), 'ME': (11, 0), 'WI': (6, 1), 'VT': (10, 1), 'NH': (11, 1),
    'WA': (1, 2), 'ID': (2, 2), 'MT': (3, 2), 'ND': (4, 2), 'MN': (5, 2), 'IL': (6, 2), 'MI': (7, 2), 'NY': (9, 2), 'MA': (10, 2),
    'OR': (1, 3), 'NV': (2, 3), 'WY': (3, 3), 'SD': (4, 3), 'IA': (5, 3), 'IN': (6, 3), 'OH': (7, 3), 'PA': (8, 3), 'NJ': (9, 3),
    'CT': (10, 3), 'RI': (11, 3),
    'CA': (1, 4), 'UT': (2, 4), 'CO': (3, 4), 'NE': (4, 4), 'MO': (5, 4), 'KY': (6, 4), 'WV': (7, 4), 'VA': (8, 4), 'MD': (9, 4),
    'DE': (10, 4),
    'AZ': (2, 5), 'NM': (3, 5), 'KS': (4, 5), 'AR': (5, 5), 'TN': (6, 5), 'NC': (7, 5), 'SC': (8, 5), 'DC': (9, 5),
    'OK': (4, 6), 'LA': (5, 6), 'MS': (6, 6), 'AL': (7, 6), 'GA': (8, 6),
    'HI': (0, 7), 'TX': (4, 7), 'FL': (9, 7),
}
TILE_BINS = [(0, 0, 'None listed'), (1, 4, '1 to 4'), (5, 19, '5 to 19'), (20, 99, '20 to 99'), (100, 10 ** 9, '100 or more')]


def tile_bin(n):
    return next(i for i, (lo, hi, _) in enumerate(TILE_BINS) if lo <= n <= hi)


def nations_tile_map():
    """Nations directory: how many government offices are listed in each state, as a tile map with a key and a table."""
    counts = Counter(n['state'] for n in NATIONS)
    cell, size = 50, 46
    tiles = ''
    for code, (col, row) in TILE_GRID.items():
        n = counts.get(code, 0)
        x, y = col * cell + 2, row * cell + 2
        num = f'<text class="nu" x="{x + size // 2}" y="{y + 39}">{n}</text>' if n else ''
        tiles += (f'<g class="tb{tile_bin(n)}"><rect x="{x}" y="{y}" width="{size}" height="{size}" rx="5"/>'
                  f'<text x="{x + size // 2}" y="{y + (19 if n else 28)}">{code}</text>{num}</g>')
    ranked = sorted(((n, STATE_NAME[c]) for c, n in counts.items()), key=lambda t: (-t[0], t[1]))
    top = and_list([f'{name} ({n})' for n, name in ranked[:5]])
    none = [STATE_NAME[c] for c, _ in STATES if not counts.get(c)]
    none_states = [x for x in none if x != 'District of Columbia']
    none_line = f'{len(none_states)} states' + (' and the District of Columbia' if 'District of Columbia' in none else '')
    svg = (f'<svg class="tilemap" viewBox="0 0 {12 * cell} {8 * cell}" width="600" height="400" role="img" aria-labelledby="tm-t tm-d">'
           f'<title id="tm-t">Map: Nation government offices listed in each state</title>'
           f'<desc id="tm-d">One square for each state and the District of Columbia, placed roughly where it is, shaded by how many offices are listed there. '
           f'The five with the most: {top}. {len(counts)} states have at least one; {none_line} have none listed. The numbers are also in the table after the map.</desc>'
           f'{tiles}</svg>')
    key = ''.join(f'<li><span class="sw tb{i}" aria-hidden="true"></span>{E(label)}</li>' for i, (_, _, label) in enumerate(TILE_BINS))
    rows = ''.join(f'<tr><th scope="row"><a href="#{STATE_SLUG[c]}">{E(STATE_NAME[c])}</a></th><td>{n}</td></tr>'
                   for n, c in sorted(((n, c) for c, n in counts.items()), key=lambda t: (-t[0], STATE_NAME[t[1]])))
    return (f'<figure class="chart tilefig"><figcaption><strong>Where the Nations\' governments are</strong> '
            f'How many Nation government offices the directory below lists in each state ({len(NATIONS)} offices in all).</figcaption>'
            f'{svg}<ul class="tilekey" aria-label="Key: offices listed in the state">{key}</ul>'
            f'<details class="chartdata"><summary>The numbers as a table</summary><table><thead><tr><th scope="col">State</th>'
            f'<th scope="col">Offices listed</th></tr></thead><tbody>{rows}</tbody></table>'
            f'<p>None listed: {E(and_list(none))}.</p></details></figure>')


def state_locator(code, nations):
    """State pages: a small locator map, the same squares as the Nations page tile map, with this state marked by its
    fill, a heavy outline and its letters, so it reads without color. The caption says the same in words."""
    name = STATE_NAME[code]
    cell, size = 50, 46
    others, here = '', ''
    for c, (col, row) in TILE_GRID.items():
        x, y = col * cell + 2, row * cell + 2
        if c == code:
            here = (f'<g class="here"><rect x="{x - 1}" y="{y - 1}" width="{size + 2}" height="{size + 2}" rx="6"/>'
                    f'<text x="{x + size // 2}" y="{y + 32}" font-size="26" font-weight="700" text-anchor="middle">{c}</text></g>')
        else:
            others += f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="5"/>'
    count = (f'{len(nations)} Nation government office{"s are" if len(nations) != 1 else " is"} listed here.' if nations
             else 'No Nation has its government office here; the <a href="../nations.html">Nations directory</a> lists every one.')
    svg = (f'<svg class="locmap" viewBox="-4 -4 {12 * cell + 8} {8 * cell + 8}" width="300" height="200" role="img" aria-labelledby="loc-t">'
           f'<title id="loc-t">Map: where {E(name)} is in the United States</title>'
           f'<g class="oth">{others}</g>{here}</svg>')
    return (f'<figure class="locfig">{svg}<figcaption><strong>Where {E(name)} is</strong> '
            f'One square for each state and D.C., placed roughly where it is. {E(name)} is the dark square with a heavy outline and its letters, {code}. '
            f'{count}</figcaption></figure>')  # count is built here, not from data, so it is not escaped


def state_options(up=''):
    return '<option value="">Choose a state</option>' + ''.join(
        f'<option value="{up}states/{STATE_SLUG[c]}.html">{E(n)}</option>' for c, n in STATES)


NAV = [('help.html', 'Get help'), ('nations.html', 'Nations'), ('states/index.html', 'By state'),
       ('find-your-nation.html', 'Finding your Nation'), ('community.html', 'Community'), ('proud-history.html', 'Proud history'), ('what-works.html', 'What works'), ('world/index.html', 'World'), ('about.html', 'About')]
PAGES = []


def structured_data(path, title, description, canonical):
    """Search-engine description of the page: the site on the home page, a web page everywhere else."""
    site_id = SITE['base_url'] + '#website'
    if path == 'index.html':
        data = {
            '@context': 'https://schema.org', '@type': 'WebSite', '@id': site_id,
            'name': SITE['name'], 'url': SITE['base_url'], 'description': SITE['description'],
            'inLanguage': 'en',
            'publisher': {'@type': 'Person', 'name': SITE['maintainer'], 'url': SITE['maintainer_url']},
        }
    else:
        data = {
            '@context': 'https://schema.org', '@type': 'WebPage', 'name': title, 'url': canonical,
            'description': description, 'inLanguage': 'en',
            'isPartOf': {'@type': 'WebSite', '@id': site_id, 'name': SITE['name'], 'url': SITE['base_url']},
        }
    text = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return f'<script type="application/ld+json">{text}</script>'


def page(path, title, description, body, head='', noindex=False):
    up = '../' * path.count('/')
    canonical = SITE['base_url'] + ('' if path == 'index.html' else path)
    current = ' aria-current="page"'
    nav = ''.join(
        f'<li><a href="{up}{href}"{current if href == path else ""}>{E(label)}</a></li>'
        for href, label in NAV)
    doc = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(description)}">
<link rel="canonical" href="{E(canonical)}">{'<meta name="robots" content="noindex">' if noindex else ''}
<meta property="og:type" content="website"><meta property="og:site_name" content="{E(SITE['name'])}"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(description)}"><meta property="og:url" content="{E(canonical)}">
<meta property="og:image" content="{E(SITE['base_url'])}assets/share.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{E(SITE['name'])}: a map of Nation government offices across the United States">
<meta name="twitter:card" content="summary_large_image">
{structured_data(path, title, description, canonical)}
<link rel="icon" href="{up}assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{up}assets/site.css">
<script>window.goatcounter={{path:function(p){{return "/"+location.hostname.replace(/^www\\./,"")+p.replace(/[?#].*$/,"")}},referrer:function(){{try{{var u=new URL(document.referrer);return u.origin+u.pathname}}catch(e){{return ""}}}}}};</script><script data-goatcounter="{E(SITE['counter'])}" async src="https://gc.zgo.at/count.js"></script>
<script src="{up}assets/site.js" defer></script>{head}</head>
<body><a class="skip" href="#main">Skip to main content</a>
<header class="top"><a class="brand" href="{up}index.html">{E(SITE['name'])}</a><nav aria-label="Main"><ul>{nav}</ul></nav></header>
<main id="main">
{body}
</main>
<footer><p><strong>{E(SITE['dedication'])}</strong> Built and maintained by <a href="{E(SITE['maintainer_url'])}">{E(SITE['maintainer'])}</a>. <a href="mailto:{E(SITE['email'])}">Send a correction</a> · <a href="{up}about.html">About and sources</a> · <a href="{up}free-page.html">Free pages for Native communities</a> · <a href="{up}help.html#safety">Help lines</a></p>
<p class="related">More free guides: <a href="https://guide.vethomeguard.org/">Veteran Resource Guide</a> (Native veterans and their families) · <a href="https://mobilitytalk.org/">Mobility Talk</a> (disability and mobility help) · <a href="https://www.yogamomtalk.com/">Yoga Mom Talk</a> (help for moms and families)</p>
<p>Listings come from tribal governments, government agencies and the organizations themselves, with the date each was checked. This site is not a tribal government, does not speak for any Nation, is not legal advice and does not decide who qualifies for anything. Nations and organizations can ask to have a listing corrected or removed.</p></footer>
</body></html>
'''
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(doc, encoding='utf-8')
    if not noindex:
        PAGES.append(path)


# ---------- pages ----------

def need_section(need, area='US', level=2, compact=False, up=''):
    """One kind of help with its listings. State pages use the compact form; the full form is on the help page."""
    cards = records_for(area, need['key'])
    also = [r for r in records_for(area, need['key'], primary_only=False) if r['need'] != need['key']]
    if not cards and not also:
        return ''
    h = f'h{level}'
    out = f'<section class="need" id="{need["key"]}" aria-labelledby="h-{need["key"]}"><{h} id="h-{need["key"]}">{need_icon(need["key"], up, "ico hico")}{E(need["label"])}</{h}>'
    if not compact:
        out += f'<p>{E(need["blurb"])}</p>{prep(need, level + 1)}'
    if cards:
        out += '<div class="cards">' + ''.join(card(r, level + 1, up) for r in cards) + '</div>'
    if need['key'] == 'safety' and area == 'US' and not compact:
        out += f'<p>In immediate danger, call 911. Outside the United States, each <a href="{up}world/index.html">country page</a> lists its own help lines.</p>'
    if also:
        out += '<p class="also">Also useful here: ' + ' · '.join(
            f'<a href="#r-{r["id"]}">{E(r["name"])}</a>' for r in also) + '</p>'
    return out + '</section>'


def build_help():
    chips = ''.join(f'<li><a href="#{n["key"]}">{need_icon(n["key"])}{E(n["short"])}</a></li>' for n in NEED_LIST if records_for('US', n['key']))
    labels = ''.join(f'<dt><span class="tag acc-{k}">{E(v["label"])}</span></dt><dd>{E(v["explain"])}</dd>' for k, v in ACCESS.items())
    sections = ''.join(need_section(n) for n in NEED_LIST)
    national = records_for('US')
    by_access = Counter(r['access'] for r in national)
    who_chart = bar_chart(f'<strong>Who can use the {len(national)} listings on this page</strong> Each listing carries one of these labels, taken from what the program itself says.',
                          [(f'<span class="tag acc-{k}">{E(v["label"])}</span>', by_access[k], f'{by_access[k]} listing{"s" if by_access[k] != 1 else ""}')
                           for k, v in ACCESS.items() if by_access.get(k)])
    body = f'''<h1>Get help</h1>
<p class="lede">Whatever brought you here, start with what you need: help for Native people anywhere in the United States, sorted by need. Many listings do not ask for a tribal card, and the filter below can show only those.</p>
<p>For your Nation, the clinics near you and Native community in your area, <a href="states/index.html">choose your state</a>.</p>
<nav class="chips" aria-label="Kinds of help"><ul>{chips}</ul></nav>
<p class="filter"><label for="who-filter">Show</label> <select id="who-filter" data-access-filter>
<option value="">Every listing</option>
<option value="anyone native descendants">Listings that do not ask for tribal enrollment</option>
<option value="anyone">Open to anyone</option>
<option value="enrolled ask">Listings for enrolled members, or where rules differ</option>
</select> <span id="filter-count" role="status"></span></p>
<details class="prep"><summary>What the labels on each listing mean</summary><dl class="labels">{labels}</dl></details>
{who_chart}
{sections}
<section class="panel"><h2>Did we miss something?</h2><p>Tell us about a program that belongs here, or a listing that is wrong: <a href="mailto:{E(SITE['email'])}">{E(SITE['email'])}</a>.</p></section>'''
    page('help.html', f'Help for Native people: health, housing, legal | {SITE["name"]}',
         'National help for Native people by need: crisis and safety lines, Indian Health Service and urban Indian clinics, recovery, family and ICWA, scholarships, housing, food and money, work, legal help, elders and veterans.', body)


def national_links(up):
    """Short list of national help by need, for state pages."""
    out = '<ul class="natlinks">'
    for need in NEED_LIST:
        recs = records_for('US', need['key'])
        if not recs:
            continue
        links = ' · '.join(f'<a href="{up}help.html#r-{r["id"]}">{E(r["name"])}</a>' for r in recs)
        out += f'<li><strong>{need_icon(need["key"], up)}<a href="{up}help.html#{need["key"]}">{E(need["label"])}</a>:</strong> {links}</li>'
    return out + '</ul>'


def state_nation_item(code, n):
    """A Nation recognized by a state and not on the federal list, shown as that state's own page names it."""
    slug = re.sub(r'[^a-z0-9]+', '-', n['name'].lower()).strip('-')
    item = {'id': f'st-{code.lower()}-{slug}', 'name': n['name'], 'city': n.get('city'), 'state': code, 'url': n.get('url')}
    if n.get('phone'):
        item['phone'] = {'display': n['phone'], 'tel': tel(n['phone'])}
    return nation_item(item)


def state_nations_section(code, level=2, linked=False):
    entry = STATE_NATIONS.get(code)
    if not entry:
        return ''
    name = STATE_NAME[code]
    head = f'<a href="states/{STATE_SLUG[code]}.html">{E(name)}</a>' if linked else f'Nations recognized by the state of {E(name)}'
    # Under "Nations recognized by a state" the heading is only the state's name, so the section's name adds that
    # list's title and does not repeat the federal section for the same state.
    named = f'hsr-{code} sr-h' if linked else f'hsr-{code}'
    return (f'<section class="st" id="sr-{STATE_SLUG[code]}" aria-labelledby="{named}"><h{level} id="hsr-{code}">{head}</h{level}>'
            '<ul class="nations">' + ''.join(state_nation_item(code, n) for n in entry['nations']) + '</ul>'
            f'<p class="meta">Recognized by the state and not on the federal list. From the <a href="{E(entry["source"])}">{E(entry["authority"])}</a>, checked {nice_date(entry["checked"])}. '
            'Names are shown as the state lists them. Programs that require enrollment in a federally recognized tribe may not accept these memberships; each listing on this site says who can use it.</p></section>')


LAND_KINDS = [
    ('reservation', 'Reservations and trust lands'),
    ('state-reservation', 'Reservations recognized by the state'),
    ('alaska', 'Alaska Native village areas'),
    ('hawaiian', 'Hawaiian home lands'),
    ('oklahoma', 'Oklahoma tribal areas'),
    ('joint', 'Joint-use areas'),
    ('state-area', 'Areas of state-recognized tribes (drawn for statistics; not reservations)'),
    ('tribal-area', 'Tribal areas drawn for statistics (not reservations)'),
]


def land_item(a):
    counties = a['counties'][:3]
    where = ', '.join(counties) + (f' and {len(a["counties"]) - 3} more' if len(a['counties']) > 3 else '')
    size = 'under 0.1 square miles' if a['sq_mi'] < 0.1 else f'about {a["sq_mi"]:,.1f} square miles'.replace('.0 ', ' ')
    return f'<li><span class="nm">{E(a["name"])}</span> <span class="where">{E(where)}</span> <span class="contact">{size} in this state</span></li>'


CLINIC_KINDS = [('hospital', 'Hospitals'), ('clinic', 'Clinics and health centers'),
                ('behavioral', 'Mental health and recovery'), ('dental', 'Dental clinics'), ('elder', 'Elder care')]
RUN_LABEL = {'ihs': 'Run by the Indian Health Service', 'tribal': 'Run by a tribe or tribal health organization',
             'urban': 'Urban Indian health program', 'partner': 'Partner facility that serves Native patients'}


PHONE_RE = re.compile(r'(?:\+?1[-. ]?)?\(?(\d{3})\)?[-. ]*(\d{3})[-. ]*(\d{4})(?:\s*(?:ext\.?|x)\s*(\d{1,6}))?', re.I)


def phone_links(text):
    """Every number in a phone field becomes its own link; the words around them stay as written."""
    out, last = '', 0
    for m in PHONE_RE.finditer(text):
        out += E(text[last:m.start()])
        num = '+1' + ''.join(m.group(1, 2, 3)) + (f',{m.group(4)}' if m.group(4) else '')
        out += f'<a href="tel:{num}">{E(m.group(0).strip())}</a>'
        last = m.end()
    return out + E(text[last:])


def clinic_item(c):
    name = E(c['name']) + (f' <span class="where">({E(c["alias"])})</span>' if c.get('alias') else '')
    if c.get('url', '').startswith('http'):
        name = f'<a href="{E(c["url"])}">{name}</a>'
    bits = [E(c['city'])] if c.get('city') else []
    if c.get('phone'):
        bits.append(phone_links(c['phone']))
    detail = [RUN_LABEL[c['run']] + (f': {E(c["by"])}' if c.get('by') and c['run'] in ('tribal', 'partner') else '')]
    if c.get('offers'):
        detail.append('Services: ' + ', '.join(E(o if i == 0 else o[0].lower() + o[1:]) for i, o in enumerate(c['offers'])))
    if c.get('hours'):
        detail.append(E(c['hours']))
    return (f'<li><span class="nm">{name}</span> <span class="where">{" · ".join(bits)}</span>'
            f'<span class="contact">{". ".join(detail)}</span></li>')


def clinics_section(code):
    items = CLINICS.get(code)
    if not items:
        return ''
    name = STATE_NAME[code]
    out = (f'<section aria-labelledby="clinics-h"><h2 id="clinics-h">Indian health clinics and hospitals in {E(name)}</h2>'
           f'<p>{len(items)} places listed by the Indian Health Service. Clinics run by the Indian Health Service or a tribe mostly serve '
           'members and descendants of federally recognized tribes; some serve everyone in the area. Urban Indian programs often serve any Native person. '
           'Call first and ask whether you can be seen and what to bring.</p>')
    for kind, label in CLINIC_KINDS:
        group = [c for c in items if c['kind'] == kind]
        if not group:
            continue
        lst = '<ul class="nations">' + ''.join(clinic_item(c) for c in group) + '</ul>'
        out += (f'<details><summary>{E(label)} ({len(group)})</summary>{lst}</details>' if len(group) > 12
                else f'<h3>{E(label)}</h3>{lst}')
    return out + (f'<p class="meta">From the <a href="{E(CLINICS_FILE["source_page"])}">{E(CLINICS_FILE["publisher"])} Find Health Care map</a>, '
                  f'retrieved {nice_date(CLINICS_FILE["retrieved"])}. Hours and services change; call before you go. '
                  'The <a href="https://www.ihs.gov/findhealthcaremap/">map</a> also gives directions.</p></section>')


def lands_section(code):
    areas = LANDS.get(code)
    if not areas:
        return ''
    name = STATE_NAME[code]
    out = f'<section aria-labelledby="lands-h"><h2 id="lands-h">Reservations and tribal lands in {E(name)}</h2>'
    for kind, label in LAND_KINDS:
        items = [a for a in areas if a['kind'] == kind]
        if not items:
            continue
        lst = '<ul class="nations">' + ''.join(land_item(a) for a in items) + '</ul>'
        if len(items) > 30:
            out += f'<details><summary>{E(label)} ({len(items)})</summary>{lst}</details>'
        else:
            out += f'<h3>{E(label)}</h3>{lst}'
    return out + (f'<p class="meta">Names, counties and land area from the <a href="{E(LANDS_FILE["source_page"])}">{E(LANDS_FILE["publisher"])}</a> '
                  f'({E(LANDS_FILE["vintage"])} boundaries), retrieved {nice_date(LANDS_FILE["retrieved"])}. Counties are listed largest share first. '
                  'These are the areas the Census Bureau maps; a Nation may hold other land, and boundaries can be in dispute. To reach a Nation, use its government office above or the <a href="../nations.html">Nations directory</a>.</p></section>')


def state_intro(code, nations, records):
    """The sourced background note for a state, from data/states.json, below the opening written to the visitor."""
    name = STATE_NAME[code]
    note = STATE_NOTES.get(code, {})
    parts = []
    if note.get('intro'):
        parts.append(f'<p>{E(note["intro"])}</p>')
        if note.get('intro_sources'):
            parts.append('<p class="meta">Sources: ' + ' · '.join(
                f'<a href="{E(s["url"])}">{E(s["label"])}</a>' for s in note['intro_sources'])
                + f'. Checked {nice_date(note["checked"])}.</p>')
    if not records:
        missing = 'Local Native organizations and state programs are' if STATE_NATIONS.get(code) else 'Local Native organizations, state programs and state-recognized Nations are'
        parts.append(f'<p>{missing} not listed for {E(name)} yet. If you know one that belongs here, <a href="mailto:{E(SITE["email"])}">tell us</a>.</p>')
    return ''.join(parts)


# ---------- landing pages: each page opens by speaking to the person most likely to arrive there ----------

def and_list(items):
    items = [x for x in items if x]
    if len(items) <= 2:
        return ' and '.join(items)
    return ', '.join(items[:-1]) + ' and ' + items[-1]


def plain(text):
    """Text without tags, for meta descriptions."""
    return html.unescape(re.sub(r'<[^>]+>', '', text))


def fit(*options, limit=60):
    """The first title that fits in a search result (about 60 characters), else the last one."""
    return next((t for t in options if len(t) <= limit), options[-1])


def clip(text, limit=255):
    """A description cut at a sentence end, so it never stops mid-thought."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind('. '), cut.rfind('.'))
    if end >= 60:
        return cut[:end + 1]
    comma = cut.rfind(', ')
    cut = cut[:comma] if comma >= 60 else cut[:cut.rfind(' ')]
    return re.sub(r'\s+(?:and|or|the|a|of|for|to|in)$', '', cut.rstrip(',;: ')) + '.'


STATE_WORDS = '|'.join(sorted((re.escape(n) for _, n in STATES), key=len, reverse=True))
ARTICLE_WORDS = re.compile(r'\b(?:Tribe|Nation|Band|Community|Pueblo|Indians|Village|Tribes|Colony|Rancheria|Council|'
                           r'Confederated|Oyate|Chapter|Commission|Center|Coalition|Collective|Association|Department|Office)\b')


def short_nation(name):
    """A Nation's name as the Bureau lists it, without the trailing state names and repeated reservation names
    the Bureau adds. Returns None for combined entries (several bands in one line) that read badly in a sentence."""
    if ';' in name or 'constituent' in name or 'component' in name:
        return None
    n = re.sub(r'\s*\((?:previously|formerly|See)[^)]*\)+', '', name).strip()
    band = re.match(r'^(.*?),\s*(?:' + STATE_WORDS + r')\s*\(([^()]+ Band)\)$', n)
    if band:
        return f'{band.group(2)} of the {band.group(1)}'
    if '(' in n:
        return None
    n = re.sub(r',\s*(?:' + STATE_WORDS + r')(?:(?:\s*(?:,|&|and)\s*)+(?:' + STATE_WORDS + r'))*\s*$', '', n)
    m = re.search(r' of the ((?:(?! of the ).)*?)\s*(?:Indian )?Reservation\b', n)
    if m and m.group(1).split()[0].lower() in n[:m.start()].lower():
        n = n[:m.start()]
    return n.strip(' ,')


def with_article(name):
    if name.startswith('The '):
        return 'the ' + name[4:]
    return 'the ' + name if ARTICLE_WORDS.search(name) else name


def land_core(name):
    core = re.sub(r'\s*\([^)]*\)', '', name)
    core = re.sub(r'\s+(?:Indian Reservation|Reservation|Trust Land|ANVSA|OTSA|TDSA|SDTSA|Settlement)$', '', core)
    return core.lower().strip()


def pick_nations(code, nations, limit=3):
    """Nations to name first: those whose lands are largest in the state, then the rest in directory order."""
    chosen = []

    def fresh(short):
        # Skip a second entry for the same Nation (a division or a band office listed beside the Nation itself).
        return all(short.split()[:2] != c.split()[:2] for c in chosen)

    for a in sorted(LANDS.get(code, []), key=lambda a: -a['sq_mi']):
        if a['kind'] in ('state-area', 'tribal-area', 'state-reservation'):
            continue
        core = land_core(a['name'])
        if len(core) < 4:
            continue
        for n in nations:
            short, full = short_nation(n['name']), n['name'].lower()
            if short and fresh(short) and (full.startswith(core) or re.search(r'of the ' + re.escape(core) + r'( indian)? reservation', full)):
                chosen.append(short)
                break
        if len(chosen) >= limit:
            return chosen
    for n in nations:
        short = short_nation(n['name'])
        if short and fresh(short):
            chosen.append(short)
        if len(chosen) >= limit:
            break
    return chosen


def state_cities(code, records):
    """Cities with an urban Indian program, from the state's listings and the Indian Health Service map."""
    cities = []
    for r in records:
        if is_urban_center(r) and r.get('place'):
            cities += [c.strip() for c in re.split(r'\band\b|,', r['place']) if c.strip()]
    for c in CLINICS.get(code, []):
        if c['run'] == 'urban' and c.get('city'):
            cities.append(c['city'])
    out = []
    for c in cities:
        c = re.sub(r'^Saint ', 'St. ', c)
        if c not in out:
            out.append(c)
    return out


def local_profile(records):
    urban = [r for r in records if is_urban_center(r)]
    community = [r for r in records if not is_urban_center(r) and (r['need'] == 'community' or 'community' in r.get('also', []))]
    other = [r for r in records if not is_urban_center(r) and r not in community]
    return urban, community, other


def state_order(code, nations, records):
    """The sections of a state page, in the order a visitor most likely wants them. Where a state has local
    community listings, or no Nation of its own, those come first; otherwise the Nations' offices do."""
    urban, community, other = local_profile(records)
    if len(community + other) >= 2 or not nations:
        order = ['local', 'ties', 'nations', 'state', 'clinics', 'colleges', 'lands']
    else:
        order = ['nations', 'local', 'state', 'clinics', 'colleges', 'lands']
    present = {'local': bool(records), 'ties': bool(STATE_NOTES.get(code, {}).get('ties')), 'nations': bool(nations),
               'state': bool(STATE_NATIONS.get(code)), 'clinics': bool(CLINICS.get(code)), 'colleges': bool(COLLEGES.get(code)),
               'lands': bool(LANDS.get(code))}
    return [k for k in order if present[k]]


def state_landing(code, nations, records):
    """H1, title, description and opening lines for a state page, built from what that state's page actually holds."""
    name = STATE_NAME[code]
    note = STATE_NOTES.get(code, {})
    the_name = 'the District of Columbia' if code == 'DC' else name
    urban, community, other = local_profile(records)
    cities = state_cities(code, records)
    state_rec = [n['name'] for n in STATE_NATIONS.get(code, {}).get('nations', [])]
    clinics = CLINICS.get(code, [])
    hospitals = []
    for c in clinics:
        if c['kind'] == 'hospital' and c['run'] in ('ihs', 'tribal') and c.get('city') and c['city'] not in hospitals:
            hospitals.append(c['city'])
    colleges = [c['name'] for c in COLLEGES.get(code, [])]
    lands = sorted(LANDS.get(code, []), key=lambda a: -a['sq_mi'])
    land_kinds = {a['kind'] for a in lands}

    # What the page offers, in the order it appears on the page, for the heading and the title.
    labels = {'local': 'community' if community else 'local help' if other else 'urban Indian health',
              'ties': f'Nations with {name} homelands', 'nations': 'Alaska Native tribes' if code == 'AK' else 'tribal Nations',
              'state': 'state-recognized Nations', 'clinics': 'Indian health care', 'colleges': 'tribal colleges',
              'lands': 'Hawaiian home lands' if 'hawaiian' in land_kinds else 'tribal lands'}
    features = [labels[k] for k in state_order(code, nations, records)
                if k != 'lands' or land_kinds & {'reservation', 'oklahoma', 'alaska', 'hawaiian'}][:3]
    if 0 < len(features) < 3:
        features.append('help')

    # The opening: who this page is for, then what is here for them.
    if note.get('lede'):
        lede = E(note['lede'])
    else:
        sentences = []
        if nations:
            picked = [with_article(n) for n in pick_nations(code, nations)]
            if len(nations) == 1:
                sentences.append(f'{picked[0][0].upper() + picked[0][1:]} has its government in {the_name}. If you are a citizen or a descendant, its office is on this page with a way to reach it.')
            elif len(nations) <= 3 and len(picked) == len(nations):
                lst = and_list(picked)
                sentences.append(f'{lst[0].upper() + lst[1:]} have their governments in {the_name}. If one of them is your Nation, its office is on this page with a way to reach it.')
            else:
                sentences.append(f'{name} is home to the governments of Nations such as {and_list(picked)}. If your Nation is here, its office is on this page with a way to reach it.')
        elif state_rec:
            sentences.append(f'No federally recognized Nation has its government in {the_name}, but the state recognizes Nations of its own, among them {and_list([with_article(n) for n in state_rec[:2]])}. If you belong to one, it is listed here with the official source.')
        else:
            sentences.append(f'No federally recognized Nation has its government in {the_name}, so if you are enrolled, your Nation\'s office is in another state; the <a href="../nations.html">Nations directory</a> has every one.')
        bits = []
        if cities:
            bits.append(f'urban Indian programs in {and_list(cities[:3])}, which often serve any Native person')
        for r in (community + other)[:2]:
            where = f' in {r["place"]}' if r.get('place') and r['place'] not in r['name'] else ''
            bits.append(f'{with_article(r["name"])}{where}')
        if hospitals:
            bits.append(f'Indian health hospitals in {and_list(hospitals[:3])}')
        elif {c['run'] for c in clinics} & {'tribal', 'ihs'}:
            runs = {c['run'] for c in clinics}
            bits.append('tribal and Indian Health Service clinics' if {'tribal', 'ihs'} <= runs else
                        'tribal health clinics' if 'tribal' in runs else 'Indian Health Service clinics')
        if colleges:
            bits.append(f'tribal colleges such as {and_list(colleges[:2])}' if len(colleges) > 1 else f'a tribal college, {colleges[0]}')
        if 'reservation' in land_kinds and len(bits) < 3:
            res = [a['name'] for a in lands if a['kind'] == 'reservation'][:2]
            bits.append(f'tribal lands such as the {and_list(res)}')
        if bits:
            lead = 'Also on this page' if nations or state_rec else 'What is here'
            bits = bits[:3]
            joined = '; '.join(bits[:-1]) + '; and ' + bits[-1] if len(bits) > 2 or (len(bits) == 2 and ', ' in bits[0]) else and_list(bits)
            sentences.append(f'{lead}: {joined}.')
        elif not nations:
            sentences.append('The help further down works from anywhere in the country.')
        lede = ' '.join(sentences)
    h1 = note.get('h1') or (f'Native {name}: {and_list(features)}' if features else f'Native people in {the_name}: help and how to reach your Nation')
    # Short enough that Google shows all of it; the description carries the rest of what is on the page.
    title = note.get('title') or (fit(f'{name} tribal Nations and Native resources | {SITE["name"]}',
                                      f'{name} tribal Nations and Native resources', f'{name} tribal Nations and Native help')
                                  if nations or state_rec else fit(f'Native resources in {name} | {SITE["name"]}',
                                                                   f'Native resources in {name}'))
    description = clip(plain(lede))
    if len(description) < 80:
        description = clip(description + f' Crisis lines, health care, school, housing and legal help for Native people in {the_name}.')
    return {'h1': h1, 'title': title, 'description': description, 'lede': lede}


def is_urban_center(r):
    return 'urban-indian-organizations' in r.get('source', '')


def college_item(c, show_state=False):
    name = f'<a href="{E(c["url"])}">{E(c["name"])}</a>' if c.get('url') else E(c['name'])
    bits = [E(c['city'])] if c.get('city') else []
    if show_state:
        bits[-1:] = [bits[-1] + ', ' + E(STATE_NAME[show_state])] if bits else [E(STATE_NAME[show_state])]
    if c.get('phone'):
        bits.append(phone_links(c['phone']))
    return f'<li><span class="nm">{name}</span> <span class="where">{" · ".join(bits)}</span><span class="contact">{E(c.get("kind", ""))}</span></li>'


def colleges_note():
    return (f'<p class="meta">From the <a href="{E(COLLEGES_FILE["source_page"])}">{E(COLLEGES_FILE["publisher"])} tribal colleges dashboard</a>, '
            f'retrieved {nice_date(COLLEGES_FILE["retrieved"])}. Most are open to everyone; many have no or low tuition for Native students and host community events, language classes and gatherings.</p>')


def colleges_section(code):
    items = COLLEGES.get(code)
    if not items:
        return ''
    return (f'<section aria-labelledby="tcu-h"><h2 id="tcu-h">Tribal colleges in {E(STATE_NAME[code])}</h2>'
            '<ul class="nations">' + ''.join(college_item(c) for c in items) + '</ul>' + colleges_note() + '</section>')


JUMP = {'local': ('local-h', 'Community and help'), 'ties': ('ties-h', 'Nations tied to this state'),
        'colleges': ('tcu-h', 'Tribal colleges'), 'clinics': ('clinics-h', 'Clinics'), 'lands': ('lands-h', 'Lands')}


JUMP_ICON = {'local': 'community', 'ties': 'nation', 'nations': 'nation', 'state': 'nation', 'colleges': 'cap',
             'clinics': 'health', 'lands': 'land', 'nat': 'phone'}


def jump_bar(code, nations, records):
    """The "On this page" row of a state page: a symbol and the number of entries for each part, as an at-a-glance view."""
    count = {'local': len(records), 'ties': len(STATE_NOTES.get(code, {}).get('ties', [])), 'nations': len(nations),
             'state': len(STATE_NATIONS.get(code, {}).get('nations', [])), 'colleges': len(COLLEGES.get(code, [])),
             'clinics': len(CLINICS.get(code, [])), 'lands': len(LANDS.get(code, [])), 'nat': len(records_for('US'))}
    links = []
    for key in state_order(code, nations, records):
        if key == 'nations':
            links.append(('nations-h', 'Nations', key))
        elif key == 'state':
            if not nations:
                links.append(('hsr-' + code, 'Nations', key))
        else:
            links.append(JUMP[key] + (key,))
    links.append(('nat-h', 'Help anywhere', 'nat'))
    return ('<nav class="chips glance" aria-label="On this page"><ul>' + ''.join(
        f'<li><a href="#{i}">{icon(JUMP_ICON[k], "../")}{E(l)} <span class="n">{count[k]}</span></a></li>' for i, l, k in links)
        + '</ul></nav>')


def build_states():
    by_state = defaultdict(list)
    for n in NATIONS:
        by_state[n['state']].append(n)
    index_items = ''
    for code, name in STATES:
        nations = by_state.get(code, [])
        records = [r for r in RES if r['area'] == code]
        note = STATE_NOTES.get(code, {})
        up = '../'
        land = state_landing(code, nations, records)
        body = (f'<p class="crumb"><a href="index.html">All states</a></p><h1>{E(land["h1"])}</h1>'
                f'<div class="statehead"><div><p class="lede">{land["lede"]}</p>{state_intro(code, nations, records)}</div>'
                f'{state_locator(code, nations)}</div>')
        body += jump_bar(code, nations, records)
        sections = {}
        if records:
            sections['local'] = (f'<section aria-labelledby="local-h"><h2 id="local-h">Native community and help in {E(name)}</h2>'
                                 + ''.join(need_section(need, code, level=3, compact=True, up=up) for need in NEED_LIST) + '</section>')
        sections['colleges'] = colleges_section(code)
        if nations:
            sections['nations'] = (f'<section aria-labelledby="nations-h"><h2 id="nations-h">Nations with their government in {E(name)}</h2>'
                                   '<ul class="nations">' + ''.join(nation_item(n, up=up) for n in nations) + '</ul>'
                                   f'<p class="meta">From the <a href="{E(NATIONS_FILE["source_page"])}">Bureau of Indian Affairs Tribal Leaders Directory</a>, retrieved {nice_date(NATIONS_FILE["retrieved"])}. '
                                   'Names are shown as the Bureau lists them. Nations: tell us if you want a listing changed.</p></section>')
        sections['state'] = state_nations_section(code)
        sections['clinics'] = clinics_section(code)
        sections['lands'] = lands_section(code)
        if note.get('ties'):
            sections['ties'] = (f'<section aria-labelledby="ties-h"><h2 id="ties-h">{E(note["ties_title"])}</h2><p>{E(note["ties_intro"])}</p>'
                                '<ul class="nations">' + ''.join(nation_item(NATION[i], show_state=True, up=up) for i in note['ties']) + '</ul>'
                                f'<p class="meta">List of Nations: <a href="{E(note["ties_source"]["url"])}">{E(note["ties_source"]["label"])}</a>, checked {nice_date(note["checked"])}. '
                                f'Phone numbers and websites: Bureau of Indian Affairs directory, retrieved {nice_date(NATIONS_FILE["retrieved"])}.</p></section>')
        body += ''.join(sections.get(k, '') for k in state_order(code, nations, records))
        body += historic_state_section(code, up)
        body += (f'<section aria-labelledby="nat-h"><h2 id="nat-h">Help that works in every state</h2>{national_links(up)}</section>'
                 f'<section class="panel"><h2>Know something that belongs on this page?</h2><p>A Nation, a community group, a clinic, a program: write to <a href="mailto:{E(SITE["email"])}">{E(SITE["email"])}</a>.</p></section>')
        page(f'states/{STATE_SLUG[code]}.html', land['title'], land['description'], body)
        count = f' <span class="count">{len(nations)} government office{"s" if len(nations) != 1 else ""}</span>' if nations else ''
        local = ' <span class="count">local listings</span>' if records else ''
        index_items += f'<li><a href="{STATE_SLUG[code]}.html">{E(name)}</a>{count}{local}</li>'
    body = f'''<h1>Find help by state</h1>
<p class="lede">Choose the state where you live, or where your family is from. Each page starts with what is there for Native people: the Nations whose governments are there, local community and help where we have it, Indian health clinics, tribal colleges and tribal lands.</p>
<p class="picker"><label for="state-pick">Go to a state</label> <select id="state-pick" data-go>{state_options("../")}</select></p>
<p>Every page also has the national help that works anywhere. More local listings are being filled in.</p>
<ul class="statelist big">{index_items}</ul>
<section aria-labelledby="map-h"><h2 id="map-h">Where Nations have their governments</h2>
<p>Each dot is the government office of a federally recognized Nation, from the Bureau of Indian Affairs directory. Each state is a link to its page. For a map you can zoom, search and use near you, <a href="../index.html">open the main map</a>.</p>
{map_svg("../")}
<p class="meta">Office locations: <a href="{E(NATIONS_FILE['source_page'])}">Bureau of Indian Affairs Tribal Leaders Directory</a>, retrieved {nice_date(NATIONS_FILE['retrieved'])}. A dot shows where a government office is, not the extent of a Nation's homelands.</p></section>'''
    page('states/index.html', f'Native resources by state | {SITE["name"]}',
         'Choose your state to see the Nations with governments there, local Native community and help, Indian health clinics, tribal colleges and tribal lands.', body)


def build_nations():
    by_state = defaultdict(list)
    for n in NATIONS:
        by_state[n['state']].append(n)
    chips = ''.join(f'<li><a href="#{STATE_SLUG[c]}">{E(STATE_NAME[c])}</a></li>' for c, _ in STATES if c in by_state)
    sections = ''
    for code, name in STATES:
        if code not in by_state:
            continue
        sections += (f'<section class="st" id="{STATE_SLUG[code]}" aria-labelledby="hs-{code}"><h2 id="hs-{code}">'
                     f'<a href="states/{STATE_SLUG[code]}.html">{E(name)}</a></h2><ul class="nations">'
                     + ''.join(nation_item(n) for n in by_state[code]) + '</ul></section>')
    state_recognized = ('<section id="state-recognized" aria-labelledby="sr-h"><h2 id="sr-h">Nations recognized by a state</h2>'
                        '<p>These Nations are recognized by their state government and are not on the federal list. So far: '
                        + ', '.join(STATE_NAME[c] for c, _ in STATES if c in STATE_NATIONS) + '. More states are being added.</p>'
                        + ''.join(state_nations_section(c, level=3, linked=True) for c, _ in STATES) + '</section>')
    body = f'''<h1>Nations directory: find your Nation's office</h1>
<p class="lede">Looking for your Nation's office, to ask about enrollment, services or events? Search by name, town or state; each Nation's government office is here with a phone number and website where the directory has one.</p>
<p class="search"><label for="q">Search by name, town or state</label> <input id="q" type="search" autocomplete="off" data-nation-search> <span id="q-count" role="status"></span></p>
<p>This list is built from the <a href="{E(NATIONS_FILE['source_page'])}">Bureau of Indian Affairs Tribal Leaders Directory</a>, retrieved {nice_date(NATIONS_FILE['retrieved'])}. The Bureau counts 575 federally recognized tribes as of January 30, 2026, and lists some bands and communities separately. It says the directory is not the official list (that is the notice it publishes in the Federal Register) and may contain errors. A Nation is listed under the state where its government office is; its homelands and citizens may reach far beyond that state.</p>
<p>Names appear as the Bureau lists them. Nations recognized by a state and not on the federal list are in <a href="#state-recognized">their own section below</a>, added one state at a time from the official list of each state. Nations with neither kind of recognition are not listed yet; write to us to be added. If you speak for a Nation and want its listing changed, write to <a href="mailto:{E(SITE['email'])}">{E(SITE['email'])}</a>.</p>
{nations_tile_map()}
<nav class="chips" aria-label="States with Nations listed"><ul>{chips}</ul></nav>
{sections}
{state_recognized}'''
    page('nations.html', f'Find your Nation: tribal Nations by state | {SITE["name"]}',
         'Find your Nation\'s government office: phone numbers and websites for every federally recognized tribal Nation in the United States, by state, and a separate section for Nations recognized by a state.', body)


def build_find():
    mail = E(SITE['email'])
    body = f'''<h1>Finding your Nation</h1>
<p class="lede">If you are reconnecting with your family's Nation, whether you grew up away from it, were adopted, or have only a name and a family story to go on, this page walks you through tracing your family and how enrollment works.</p>
<p>Enrollment is a legal status that each Nation decides for itself. Finding community is a separate thing, and you can start on both at once: see <a href="community.html">Finding community</a>.</p>

<section aria-labelledby="f1"><h2 id="f1">What enrollment is</h2>
<p>Each tribe sets its own rules for who can be a member, and only the tribe can enroll you. The Department of the Interior says two rules are common: descending directly from someone named on the tribe's base roll, or being related to a member who does. Some tribes also look at blood quantum, where you live, or whether your family has stayed in contact with the tribe.</p>
<p>The Bureau of Indian Affairs (BIA) does not keep a list of enrolled members and does not do family research for people. Each tribe keeps its own records. The BIA also says the rules for federal services differ from program to program, so being a descendant, being enrolled and being eligible for a given program are three different questions. The labels on our <a href="help.html">help listings</a> say which one each program asks about.</p>
<p class="meta">Sources: <a href="https://www.doi.gov/tribes/enrollment">Department of the Interior, Tribal Enrollment Process</a> · <a href="https://www.bia.gov/guide/tracing-american-indian-and-alaska-native-aian-ancestry">BIA, Tracing American Indian and Alaska Native Ancestry</a> · <a href="https://www.bia.gov/frequently-asked-questions">BIA, Frequently Asked Questions</a>. Checked November 17, 2026.</p></section>

<section aria-labelledby="f2"><h2 id="f2">Tracing your family, step by step</h2>
<ol class="steps" role="list">
<li>{icon("notes")}<strong>Write down what your family knows.</strong> Names, birth dates and birthplaces of parents, grandparents and great-grandparents, and any papers kept at home. Note who told you which Nation the family comes from.</li>
<li>{icon("search")}<strong>Work out which Nation your ancestor belonged to.</strong> You will be dealing with that tribe's government, so this is the question everything else depends on.</li>
<li>{icon("papers")}<strong>Build the paper trail.</strong> The BIA says you need to show your link to an ancestor with records the tribe accepts. Birth and death certificates come from the vital records office of the state where the person was born or died. The BIA also points to the National Archives (federal census records, including the Bureau's own censuses, the Dawes Rolls and military records), county courthouses, and town, school and church records, newspapers, libraries and historical societies.</li>
<li>{icon("phone")}<strong>Contact the tribe's enrollment office.</strong> Ask for its membership rules and the papers it accepts. Our <a href="nations.html">Nations directory</a> has a phone number and website for each government office.</li>
<li>{icon("apply")}<strong>Apply to the tribe</strong> if you meet its rules. The tribe decides.</li>
</ol>
<p class="meta">Source: <a href="https://www.bia.gov/guide/tracing-american-indian-and-alaska-native-aian-ancestry">BIA, Tracing American Indian and Alaska Native Ancestry</a>. Checked November 17, 2026.</p></section>

<section aria-labelledby="f3"><h2 id="f3">About DNA tests</h2>
<p>The BIA says blood and DNA tests cannot show that you descend from a particular tribe. A test may show that you are related to a tribal member, and that only helps if the tribe accepts such tests. Ask the tribe before paying for one.</p></section>

<section aria-labelledby="f4"><h2 id="f4">The CDIB card</h2>
<p>A Certificate of Degree of Indian Blood (CDIB) is issued by the BIA. To get one you must show a direct line, through a parent, grandparent or great-grandparent, to an ancestor who is listed with a degree of Indian blood on official tribal rolls. Aunts, uncles and cousins cannot be used. The links are shown with birth and death certificates. Applications are handled by enrollment staff at BIA regional and agency offices.</p>
<p class="meta">Sources: <a href="https://www.bia.gov/guide/tracing-american-indian-and-alaska-native-aian-ancestry">BIA ancestry guide</a> · <a href="https://www.bia.gov/bia/ois/tgs">BIA Division of Tribal Government Services</a>. Checked November 17, 2026.</p></section>

<section aria-labelledby="f5"><h2 id="f5">If you were adopted, in foster care, or your family was separated</h2>
<ul>
<li>The <a href="help.html#r-nicwa">National Indian Child Welfare Association</a> hears every year from people tracing their Native ancestry and has guides for families.</li>
<li>If a child welfare case is open now, read about the <a href="help.html#r-icwa-rights">Indian Child Welfare Act</a>. The child's tribe has a right to be told and to take part.</li>
<li>If your relatives were sent to an Indian boarding school, the <a href="help.html#r-boarding-school-archive">National Indian Boarding School Digital Archive</a> holds digitized school records and student name lists.</li>
<li>In Michigan, state <a href="states/michigan.html#r-mi-outreach-services">Native American Outreach Services</a> workers help families identify their heritage and tribal enrollment, including people who are not sure of their tribal affiliation.</li>
</ul></section>

<section aria-labelledby="f6"><h2 id="f6">If your family's story starts in Ohio</h2>
<p>No federally recognized Nation has its government in Ohio today, but dozens of Nations are tied to Ohio by homelands and treaties, and their governments are in other states now. The <a href="states/ohio.html#ties-h">Ohio page</a> lists the Nations the Ohio History Connection names, with a phone number for each.</p></section>

<section aria-labelledby="f7"><h2 id="f7">If your Nation is not federally recognized</h2>
<p>Nations recognized by a state have <a href="nations.html#state-recognized">their own section of the Nations directory</a>, added one state at a time from each state's official list. Nations still seeking recognition are not listed yet. Some help does not depend on federal recognition: the American Indian College Fund, for example, accepts members and descendants of state-recognized tribes. On the <a href="help.html">help page</a> you can show only the listings that do not ask for tribal enrollment.</p></section>

<section class="panel"><h2>Something here wrong, or missing?</h2><p>If you work in tribal enrollment, or you have walked this road yourself and see a step we got wrong, write to <a href="mailto:{mail}">{mail}</a>.</p></section>'''
    page('find-your-nation.html', f'Tracing Native ancestry and tribal enrollment | {SITE["name"]}',
         'How to work out which Nation your family comes from, how tribal enrollment works, what a CDIB card and DNA tests can and cannot do, and who can help if you were adopted or in foster care.', body)


def build_community():
    community_states = [name for code, name in STATES if any(
        r['area'] == code and (r['need'] == 'community' or 'community' in r.get('also', [])) for r in RES)]
    local = ''
    for code, name in STATES:
        recs = [r for r in RES if r['area'] == code and (r['need'] == 'community' or 'community' in r.get('also', []))]
        if not recs:
            continue
        local += (f'<section aria-labelledby="c-{code}"><h3 id="c-{code}"><a href="states/{STATE_SLUG[code]}.html">{E(name)}</a></h3>'
                  '<div class="cards">' + ''.join(card(r, 4) for r in recs) + '</div></section>')
    anywhere = [r for r in RES if r['area'] == 'US' and (r['need'] == 'community' or 'community' in r.get('also', []))]
    urban = defaultdict(list)
    for r in RES:
        if is_urban_center(r):
            urban[r['area']].append(r)
    urban_html = ''.join(f'<h3><a href="states/{STATE_SLUG[c]}.html">{E(STATE_NAME[c])}</a></h3><ul class="nations">'
                         + ''.join(f'<li><span class="nm"><a href="states/{STATE_SLUG[c]}.html#r-{E(r["id"])}">{E(r["name"])}</a></span> <span class="where">{E(r.get("place", ""))}'
                                   + (f' · {phone_links(r["phone"])}' if r.get('phone') else '') + '</span></li>' for r in urban[c]) + '</ul>'
                         for c, _ in STATES if c in urban)
    colleges_html = '<ul class="nations">' + ''.join(college_item(x, show_state=c) for c, _ in STATES for x in COLLEGES.get(c, [])) + '</ul>'
    per_state = sorted(((len(v), c) for c, v in COLLEGES.items()), key=lambda t: (-t[0], STATE_NAME[t[1]]))
    colleges_chart = bar_chart(f'<strong>Tribal colleges by state</strong> The {sum(n for n, _ in per_state)} colleges listed below, in {len(per_state)} states.',
                               [(f'<a href="states/{STATE_SLUG[c]}.html">{E(STATE_NAME[c])}</a>', n, f'{n} college{"s" if n != 1 else ""}') for n, c in per_state], side=True)
    jump = [('c-pages', 'Community pages', 'layout'), ('c-local', 'Centers and groups', 'community'), ('c-urban', 'Urban Indian centers', 'city'),
            ('c-tcu', 'Tribal colleges', 'cap'), ('c-any', 'From anywhere', 'phone'), ('c-nation', 'Your own Nation', 'nation')]
    jump_nav = '<nav class="chips" aria-label="On this page"><ul>' + ''.join(f'<li><a href="#{i}">{icon(k)}{E(l)}</a></li>' for i, l, k in jump) + '</ul></nav>'
    body = f'''<h1>Finding community</h1>
<p class="lede">If you want to be around Native people where you live, whether you are new to a city or coming back to your culture, here are the places and groups where Native people gather: community centers, youth councils, recovery circles and tribal colleges.</p>
<p>Local groups and state Native affairs offices are listed so far for {and_list(community_states)}. Urban Indian centers and tribal colleges are further down, and every state page lists its Nations, clinics and tribal lands.</p>
{jump_nav}
{community_pages_section()}
<section aria-labelledby="c-local"><h2 id="c-local">{icon('community', cls='ico hico')}Community centers and groups, by state</h2>{local}
<p>In another state? Start with the <a href="help.html#r-urban-indian-health">map of Urban Indian Organizations</a>, whose services can include youth, elder and community programs, or <a href="states/index.html">open your state's page</a>.</p></section>
<section aria-labelledby="c-urban"><h2 id="c-urban">{icon('city', cls='ico hico')}Urban Indian centers</h2>
<p>Funded by the Indian Health Service to serve Native people living in cities. Many run community programs, youth and elder activities and gatherings as well as health care. Any Native person can usually walk in; ask what they need from you.</p>{urban_html}</section>
<section aria-labelledby="c-tcu"><h2 id="c-tcu">{icon('cap', cls='ico hico')}Tribal colleges</h2>
<p>Colleges chartered by Nations. They are community anchors: classes, language programs, powwows and events, often open to the public.</p>{colleges_chart}{colleges_html}{colleges_note()}</section>
<section aria-labelledby="c-any"><h2 id="c-any">{icon('phone', cls='ico hico')}From anywhere</h2><div class="cards">{''.join(card(r, 3) for r in anywhere)}</div></section>
<section aria-labelledby="c-nation"><h2 id="c-nation">{icon('nation', cls='ico hico')}Your own Nation</h2>
<p>If you know which Nation you come from, call its government office and ask what gatherings, classes or events are coming up, and whether descendants are welcome. The <a href="nations.html">Nations directory</a> has the numbers. If you are not sure which Nation, start with <a href="find-your-nation.html">Finding your Nation</a>.</p></section>
<section class="panel"><h2>Run a Native community group?</h2><p>We would like to list it, the way you want it described. Write to <a href="mailto:{E(SITE['email'])}">{E(SITE['email'])}</a>.</p></section>'''
    page('community.html', f'Native community centers, youth and recovery | {SITE["name"]}',
         'Find Native people near you: urban Indian centers, Native community groups, youth councils, Wellbriety recovery circles and tribal colleges, for Native people in cities and those coming back to their culture.', body)


def about_stats():
    """About page: what the site covers, counted from the data, as a row of tiles. The numbers are written out."""
    guides = sum(1 for c in COUNTRIES if c['slug'])
    tiles = [('nation', len(NATIONS), 'Nation government offices, from the Bureau of Indian Affairs directory'),
             ('land', len(STATES), 'state pages: every state and the District of Columbia'),
             ('notes', len(RES) + len(WORLD), 'listings of help, each with its source and the date it was checked'),
             ('globe', guides, 'country guides beyond the United States')]
    return ('<ul class="stats" aria-label="What the site covers, in numbers">' + ''.join(
        f'<li>{icon(i)}<span class="big">{n}</span> <span class="what">{E(t)}</span></li>' for i, n, t in tiles) + '</ul>')


def build_about():
    mail = E(SITE['email'])
    labels = ''.join(f'<dt><span class="tag acc-{k}">{E(v["label"])}</span></dt><dd>{E(v["explain"])}</dd>' for k, v in ACCESS.items())
    body = f'''<h1>About this site</h1>
<p class="lede">{E(SITE['name'])} is a free guide for Native people looking for help, for their Nation, or for community.</p>
<p><strong>{E(SITE['dedication'])}</strong></p>

<section aria-labelledby="a1"><h2 id="a1">Who is behind it</h2>
<p>The site was built and is maintained by <a href="{E(SITE['maintainer_url'])}">{E(SITE['maintainer'])}</a>, an individual. It is not a tribal government or a government agency, and it does not speak for any Nation. It gathers in one place what Nations, agencies and Native organizations publish about themselves, in plain language.</p>
<p>It needs Native people to look it over. If you are a tribal citizen or descendant, or you work for a Nation, a tribal program or a Native organization, your corrections and your judgment about what belongs here are wanted: <a href="mailto:{mail}">{mail}</a>.</p></section>

<section aria-labelledby="a2"><h2 id="a2">What it covers so far</h2>
<p>The United States is covered in the most detail: national help by need, the government office of every federally recognized Nation, Nations recognized by a state (one state at a time), and a page for every state. Ohio and Michigan also list community groups and state programs, and more states are being filled in. <a href="world/index.html">Country guides</a> carry the map beyond the United States.</p>
{about_stats()}
<p>Not here yet: Nations still seeking recognition, and most local organizations outside Ohio and Michigan.</p></section>

<section aria-labelledby="a3"><h2 id="a3">Where the listings come from</h2>
<ul>
<li><strong>Nations:</strong> the <a href="{E(NATIONS_FILE['source_page'])}">Bureau of Indian Affairs Tribal Leaders Directory</a>, retrieved {nice_date(NATIONS_FILE['retrieved'])}. We keep the name, town, state, phone number, website and map position of each government office. We leave out the names of elected leaders, which change with every election. The Bureau says the directory is not the official list of federally recognized tribes and may contain errors.</li>
<li><strong>Programs and organizations:</strong> each one's own website, or a page from a government agency that lists it. Every listing shows the date it was checked and links to the page it came from.</li>
<li><strong>Map shapes:</strong> U.S. Census Bureau state outlines.</li>
</ul>
<p>Listings are read from published sources. When something is wrong or out of date, <a href="mailto:{mail}">tell us</a> and it will be fixed.</p>
<h3 id="a3s">How a listing gets here</h3>
<ol class="steps" role="list" aria-labelledby="a3s">
<li>{icon("search")}<strong>Read from the source.</strong> A Nation's, agency's or organization's own published page, or a government page that lists it.</li>
<li>{icon("notes")}<strong>Written in plain words,</strong> with a link to the page it came from and the date it was checked.</li>
<li>{icon("check")}<strong>Labeled with who can use it,</strong> taken from what the program itself says (the labels are explained below).</li>
<li>{icon("update")}<strong>Corrected or removed</strong> when a Nation or organization asks, or when something is found to be wrong or out of date.</li>
</ol></section>

<section aria-labelledby="a4"><h2 id="a4">What the labels mean</h2>
<p>Programs differ on who they serve. Some are open to anyone, some serve descendants, and some ask for proof of enrollment in a federally recognized tribe. Each listing carries one of these labels, taken from what the program itself says:</p>
<dl class="labels">{labels}</dl></section>

<section aria-labelledby="a5"><h2 id="a5">For Nations and organizations</h2>
<p>You decide how you are described. Names appear as the Bureau of Indian Affairs or the organization itself writes them. If you want a name, a description or a contact changed, or a listing removed, write to <a href="mailto:{mail}">{mail}</a>.</p>
<p>This site does not publish ceremonial knowledge, the locations of sacred places, or anything else a Nation has not chosen to make public.</p></section>

<section aria-labelledby="a6"><h2 id="a6">Your privacy</h2>
<p>There are no accounts and no forms, and the site stores nothing about you. One counter (GoatCounter) counts page views without cookies. Phone and text links open your own phone's apps.</p>
<p>The map on the home page can use your location to show what is near you, but only if you press "Use my location" and your browser asks you first. Your location stays on your device and is never sent to this site. The map pictures are loaded from OpenStreetMap's servers, which, like any website, can see which part of the map is being looked at. Directions open in the maps app you choose.</p></section>

<section aria-labelledby="a7"><h2 id="a7">Limits</h2>
<p>This is general information, not legal, medical or financial advice. It does not decide who qualifies for a program; the program does. Phone numbers and rules change, so confirm details with the program before you rely on them.</p></section>

<section aria-labelledby="a8"><h2 id="a8">Reuse</h2>
<p>The site's data and code are public at <a href="{E(SITE['repo'])}">{E(SITE['repo'].replace('https://', ''))}</a>. The compiled data is licensed CC BY 4.0 and the code under the MIT License. Tribal programs and Native organizations are welcome to copy, adapt and republish it.</p></section>'''
    page('about.html', f'About {SITE["name"]}: who made it and the sources',
         'Who built this guide for Native people, where its listings come from, what the labels mean, how Nations and organizations can correct or remove a listing, and how your privacy is handled.', body)


def build_404():
    base = E(SITE['base_url'])
    body = f'''<h1>That page is not here</h1>
<p class="lede">The link may be old, or the address may have a typo.</p>
<ul class="ways">{''.join(f'<li><a href="{base}{href}">{icon(sym)}{label}</a></li>' for href, sym, label in [('', 'layout', 'Home'), ('help.html', 'heart', 'Get help'), ('nations.html', 'nation', 'Nations directory'), ('states/index.html', 'land', 'Find help by state')])}</ul>'''
    # 404 pages are served from any depth, so every link in the page chrome must be absolute.
    page('404.html', f'Page not found | {SITE["name"]}', 'That page is not here.', body)
    path = ROOT / '404.html'
    text = path.read_text(encoding='utf-8')
    for target in ['assets/', 'index.html', 'about.html', 'free-page.html'] + [href for href, _ in NAV]:
        text = text.replace(f'href="{target}', f'href="{SITE["base_url"]}{target}').replace(f'src="{target}', f'src="{SITE["base_url"]}{target}')
    text = text.replace(f'<link rel="canonical" href="{E(SITE["base_url"])}404.html">', '<meta name="robots" content="noindex">')
    path.write_text(text, encoding='utf-8')
    PAGES.remove('404.html')


WORKS = [
    {'title': 'Diabetes care run by tribes and clinics: the Special Diabetes Program for Indians',
     'what': 'Since 1997 Congress has funded diabetes prevention and treatment that tribes, urban Indian programs and Indian Health Service clinics run themselves. The Indian Health Service counts 301 program sites in 35 states.',
     'results': ['New cases of diabetes-related kidney failure in Native adults fell 54 percent from 1996 to 2013.',
                 'Hospital stays for uncontrolled diabetes fell 84 percent from 2000 to 2015.',
                 'Deaths related to diabetes fell 37 percent from 1999 to 2017.',
                 'The share of Native adults with diabetes went down, from 15.4 percent in 2013 to 14.6 percent in 2017.'],
     # The same three results as a chart: what fell, over which years, and by how many percent.
     'chart': [('New cases of diabetes-related kidney failure in Native adults, 1996 to 2013', 54),
               ('Hospital stays for uncontrolled diabetes, 2000 to 2015', 84),
               ('Deaths related to diabetes, 1999 to 2017', 37)],
     'use': 'Ask your tribal or urban Indian clinic whether it runs a diabetes program under this funding. Most do.',
     'sources': [('Indian Health Service: Special Diabetes Program for Indians fact sheet, 2020', 'https://www.ihs.gov/sites/sdpi/themes/responsive2017/display_objects/documents/factsheets/SDPIFactSheet2020.pdf'),
                 ('Indian Health Service: reports to Congress', 'https://www.ihs.gov/sdpi/reports-to-congress/')]},
    {'title': 'Home visits for young families by local Native health workers: Family Spirit',
     'what': 'Trained home visitors from the community meet with mothers from pregnancy until the child is three. Johns Hopkins designed and tested it together with the Navajo, White Mountain Apache and San Carlos Apache communities.',
     'results': ['The U.S. Department of Health and Human Services reviewed the research and rates Family Spirit an evidence-based home visiting model, including for Indigenous communities.',
                 'Four of the studies it reviewed were rated high or moderate quality.'],
     'use': 'Ask your tribal health department or urban Indian program whether it offers Family Spirit or another home visiting program.',
     'sources': [('U.S. Department of Health and Human Services: Home Visiting Evidence of Effectiveness, Family Spirit', 'https://homvee.acf.gov/models/family-spiritr')]},
    {'title': 'Nations running their own programs: self-governance',
     'what': 'Since the 1970s federal law has let Nations take over programs the federal government used to run for them, such as clinics, schools, police and land management.',
     'results': ['Researchers at Harvard who have studied Native nations since the 1980s find that when Nations make their own decisions they consistently do better than outside decision-makers.',
                 'Their awards program has documented 148 tribal government programs from more than 100 Nations that solved a problem at home, from school health centers to air quality.'],
     'use': 'If you work for a Nation or a tribal program, the awards library is a place to find a program like the one you need and the people who built it.',
     'sources': [('Harvard Kennedy School: Foundations of Indigenous nation building', 'https://www.hks.harvard.edu/faculty-research/policy-topics/democracy-governance/foundations-indigenous-nation-building'),
                 ('Harvard Project on Indigenous Governance and Development: Honoring Nations', 'https://indigenousgov.hks.harvard.edu/honoring-nations')]},
]
WORKS_CHECKED = '2026-11-18'


PROUD = [
    ('Government', 'One of the oldest living democracies: the Haudenosaunee Confederacy',
     'The Mohawk, Oneida, Onondaga, Cayuga and Seneca Nations, later joined by the Tuscarora, united under the Great Law of Peace, a constitution kept on wampum belts and recited from memory. Its Grand Council of 50 chiefs still meets. Women hold real power in it: clan mothers choose each chief and can remove one who does not serve the people.',
     'In 1988 both houses of Congress passed a resolution acknowledging the contribution of the Iroquois Confederacy to the development of the United States Constitution. Historians still debate how much the framers borrowed; the Confederacy itself has governed continuously since long before the United States existed.',
     [('Haudenosaunee Confederacy: how the Confederacy is structured', 'https://www.haudenosauneeconfederacy.com/chiefs.html'),
      ('Congress.gov: H.Con.Res. 331 (1988)', 'https://www.congress.gov/bill/100th-congress/house-concurrent-resolution/331')]),
    ('Language', 'A whole writing system, invented by one man: Sequoyah',
     'Sequoyah spent about twelve years creating a syllabary for the Cherokee language, finished in 1821: a symbol for each syllable, simple enough to learn in days. The Cherokee people took it up fast.',
     'In 1828 the Cherokee Nation printed the Cherokee Phoenix, the first newspaper published in a Native language in North America, in Cherokee and English side by side.',
     [('Britannica: Cherokee language', 'https://www.britannica.com/topic/Cherokee-language')]),
    ('Food', 'Feeding the world',
     'Corn, beans, squash, potatoes, tomatoes, chile peppers, peanuts, cassava, sweet potatoes, cacao and vanilla were all developed by Indigenous farmers in the Americas over thousands of years. Corn was bred from a wild grass. Andean farmers developed potatoes for every climate from the coast to the high mountains.',
     'Italian tomatoes, Irish potatoes and much of the world\'s chocolate trace back to Native farmers.',
     [('Britannica: 18 food crops developed in the Americas', 'https://www.britannica.com/story/18-food-crops-developed-in-the-americas')]),
    ('Service', 'Serving at the highest rate',
     'American Indians, Alaska Natives and Native Hawaiians have served in every American war since the Revolution, and serve in the armed forces at one of the highest rates of any group.',
     'In 2020 the National Native American Veterans Memorial opened on the grounds of the Smithsonian\'s National Museum of the American Indian in Washington, the first national memorial to Native veterans.',
     [('Smithsonian: National Native American Veterans Memorial opens', 'https://torch.si.edu/2020/11/national-native-american-veterans-memorial-opens-to-the-public/')]),
    ('Service', 'The code that was never broken',
     'In World War II, Navajo Marines built a code from the Navajo language and carried messages through the Pacific that the enemy never deciphered. Code talkers from many other Nations, including Comanche, Choctaw, Hopi and others, served in both world wars.',
     'The code stayed secret until 1968. In 2001 the original 29 Navajo Code Talkers received the Congressional Gold Medal, and later laws honored code talkers from other Nations as well.',
     [('National Archives, Prologue: Semper Fidelis, Code Talkers', 'https://www.archives.gov/publications/prologue/2001/winter/navajo-code-talkers.html')]),
    ('Science', 'Into space',
     'Mary Golda Ross, a citizen of the Cherokee Nation, is considered the first Native American engineer in the U.S. space program. She worked in Lockheed\'s top-secret design team on rockets and spacecraft for the Gemini and Apollo programs. The 2019 Native American dollar coin shows her at work.',
     'In 2002 John Herrington, an enrolled citizen of the Chickasaw Nation, became the first Native American in space, with three spacewalks to build the International Space Station.',
     [('U.S. Mint: 2019 Native American $1 coin, American Indians in the space program', 'https://www.usmint.gov/learn/coins-and-medals/collectible-coins/native-american-dollar-coins/2019-american-indians-in-space'),
      ('NASA: John Herrington performs a spacewalk', 'https://www.nasa.gov/image-article/john-herrington-performs-a-spacewalk/')]),
    ('Sport', 'The greatest upset in Olympic history',
     'Billy Mills, Oglala Lakota, grew up on the Pine Ridge Reservation and lost both parents young. At the 1964 Tokyo Olympics, a Marine lieutenant almost nobody had heard of, he passed the world-record holder in the last stretch to win the 10,000 meters.',
     'He is still the only American ever to win it. He went on to spend his life working for Native youth.',
     [('U.S. Olympic & Paralympic Museum Hall of Fame: Billy Mills', 'https://usopm.org/billy-mills/')]),
]


PROUD_ICON = {'Government': 'council', 'Language': 'speech', 'Food': 'food', 'Service': 'veterans', 'Science': 'rocket',
              'Sport': 'stopwatch'}
# The timeline on the Proud history page: only dates that the stories themselves give, each pointing to its story (index in PROUD).
PROUD_DATES = [
    (1821, 1, 'Sequoyah finishes his syllabary for the Cherokee language.'),
    (1828, 1, 'The Cherokee Nation prints the Cherokee Phoenix, the first newspaper published in a Native language in North America.'),
    (1964, 6, 'Billy Mills, Oglala Lakota, wins the 10,000 meters at the Tokyo Olympics.'),
    (1968, 4, 'The code that Navajo Marines built in World War II is no longer kept secret.'),
    (1988, 0, 'Both houses of Congress pass a resolution acknowledging the contribution of the Iroquois Confederacy to the development of the United States Constitution.'),
    (2001, 4, 'The original 29 Navajo Code Talkers receive the Congressional Gold Medal.'),
    (2002, 5, 'John Herrington, a citizen of the Chickasaw Nation, becomes the first Native American in space.'),
    (2019, 5, 'The Native American dollar coin shows Mary Golda Ross, a citizen of the Cherokee Nation, at work.'),
    (2020, 3, 'The National Native American Veterans Memorial opens in Washington.'),
]


def proud_timeline():
    items = ''.join(f'<li><span class="yr">{year}</span><span class="ev">{icon(PROUD_ICON[PROUD[i][0]])}'
                    f'<a href="#p{i}">{E(text)}</a></span></li>' for year, i, text in PROUD_DATES)
    return ('<figure class="timeline-fig"><figcaption><strong>On a timeline</strong> The dates given in the stories below. '
            f'Each links to its story and sources.</figcaption><ol class="timeline" role="list">{items}</ol></figure>')


def build_proud():
    cats = ''
    body = ('<h1>Proud history</h1><p class="lede">For anyone looking for stories to be proud of, or to teach: some of what First Peoples built, invented, defended and won. A few to start; there are thousands more.</p>'
            '<p>Every entry links to the museum, government or Nation source it comes from. If your Nation or family has a story that belongs here, '
            f'<a href="mailto:{E(SITE["email"])}">send it</a>, told the way you want it told.</p>') + proud_timeline()
    for i, (cat, title, what, more, sources) in enumerate(PROUD):
        body += (f'<section aria-labelledby="p{i}"><p class="kicker">{icon(PROUD_ICON[cat])}{E(cat)}</p><h2 id="p{i}">{E(title)}</h2><p>{E(what)}</p><p>{E(more)}</p>'
                 '<p class="meta">Sources: ' + ' · '.join(f'<a href="{E(u)}">{E(l)}</a>' for l, u in sources) + '. Checked November 18, 2026.</p></section>')
    body += historic_sites_section()
    body += '<p>Nations running their own programs have a record of results too: see <a href="what-works.html">What works</a>.</p>'
    page('proud-history.html', f'Proud history: what First Peoples gave America | {SITE["name"]}',
         'The Haudenosaunee Great Law of Peace, Sequoyah\'s Cherokee syllabary, the crops Native farmers gave the world, the code talkers, Native astronauts and engineers, Billy Mills, and Native historic sites you can visit, like Serpent Mound, each with its source.', body)


def historic_item(h, up=''):
    whose = f'<span class="sub">{E(h["whose"])}</span>' if h.get('whose') else ''
    return (f'<li id="hs-{h["id"]}"><a href="{E(h["url"])}" rel="noopener">{E(h["name"])}</a>{whose}'
            f'<span class="sub"><a href="{up}index.html#hs-{h["id"]}">See it on the map</a></span></li>')


HISTORIC_CARE = ('Every place here is open to visitors and links to the park, agency or Nation that runs it, for hours and directions. '
                 'Many ancestral places are kept private by the Nations they belong to, and they are not listed. '
                 'When you visit, stay on marked paths and leave everything as you found it.')


def historic_sites_section():
    by_state = defaultdict(list)
    for h in HISTORIC:
        by_state[h['state']].append(h)
    groups = ''.join(f'<h3>{E(STATE_NAME[code])}</h3><ul class="hsites">' + ''.join(historic_item(h) for h in sorted(items, key=lambda h: h['name'])) + '</ul>'
                     for code, items in sorted(by_state.items(), key=lambda kv: STATE_NAME[kv[0]]))
    return (f'<section aria-labelledby="sites"><h2 id="sites">Historic and cultural sites you can visit</h2><p>{E(HISTORIC_CARE)}</p>'
            f'<p>The same {len(HISTORIC)} places are on the <a href="index.html">map</a> under Historic sites.</p>{groups}'
            f'<p class="meta">Each name links to the official page of the site. Who the place belongs to is given only where that page or another public source says so. Checked {nice_date(HISTORIC_FILE["checked"])}.</p></section>')


def historic_state_section(code, up='../'):
    items = sorted((h for h in HISTORIC if h['state'] == code), key=lambda h: h['name'])
    if not items:
        return ''
    return (f'<section aria-labelledby="hist-h"><h2 id="hist-h">Native historic and cultural sites to visit in {E(STATE_NAME[code])}</h2>'
            f'<ul class="hsites">' + ''.join(historic_item(h, up) for h in items) + '</ul>'
            f'<p class="meta">{E(HISTORIC_CARE)} <a href="{up}proud-history.html#sites">Sites in other states</a>. Checked {nice_date(HISTORIC_FILE["checked"])}.</p></section>')


def build_works():
    body = ('<h1>What has worked</h1><p class="lede">If you run a program for a Nation or a Native community, or want to start one, these programs have measured, published results behind them, for families, clinics and tribal governments.</p>'
            '<p>This page lists only programs whose results were measured and published by the agency or university named in each entry. It is short on purpose and will grow one sourced entry at a time. '
            f'If you know a program with results to show, <a href="mailto:{E(SITE["email"])}">tell us</a>.</p>')
    for i, w in enumerate(WORKS):
        body += (f'<section aria-labelledby="w{i}"><h2 id="w{i}">{E(w["title"])}</h2><p>{E(w["what"])}</p>'
                 '<h3>What the results show</h3><ul>' + ''.join(f'<li>{E(r)}</li>' for r in w['results']) + '</ul>'
                 + (bar_chart('<strong>How much each fell</strong> The results above, in percent. A full bar would be 100 percent.',
                              [(E(label), v, f'fell {v}%') for label, v in w['chart']], scale=100) if w.get('chart') else '')
                 + f'<p><strong>How to use this:</strong> {E(w["use"])}</p>'
                 '<p class="meta">Sources: ' + ' · '.join(f'<a href="{E(u)}">{E(l)}</a>' for l, u in w['sources'])
                 + f'. Checked {nice_date(WORKS_CHECKED)}.</p></section>')
    page('what-works.html', f'Programs that worked in Native communities | {SITE["name"]}',
         'Programs with measured, published results in Native communities: tribal diabetes programs, home visiting for young families, and Nations running their own services.', body)


# ---------- the map finder and the world ----------

FINDER_NEEDS = ['safety', 'health', 'recovery', 'family', 'school', 'housing', 'money', 'work', 'legal', 'nation',
                'elders', 'veterans', 'community']
CLINIC_NEED = {'hospital': ['health'], 'clinic': ['health'], 'behavioral': ['recovery', 'health'],
               'dental': ['health'], 'elder': ['elders', 'health']}
KIND_LABEL = {'nation': 'Nation government office', 'fn': 'First Nation', 'inuit': 'Inuit community',
              'clinic': 'Health care', 'college': 'Tribal college', 'land': 'Reservation or tribal land',
              'place': 'Community and help', 'history': 'Historic or cultural site', 'guide': 'Country guide'}
# Map choices that are not a kind of help, so they have no page section of their own in data/needs.json.
FINDER_EXTRA = {'history': 'Historic sites'}
LAND_LABEL = {'reservation': 'Reservation', 'hawaiian': 'Hawaiian home land', 'alaska': 'Alaska Native village area',
              'oklahoma': 'Oklahoma tribal area', 'state-area': 'State-designated tribal area', 'tribal-area': 'Tribal designated area',
              'joint': 'Joint-use area', 'state-reservation': 'State reservation'}


REGIONS = ['North America', 'Latin America', 'Arctic and Europe', 'Pacific', 'Asia', 'Africa', 'Worldwide']


def country_cards(prefix='', lines=True, level=3):
    """Country cards grouped by region, for the home page and the world page."""
    out = ''
    for region in REGIONS:
        here = [c for c in COUNTRIES if c['slug'] and c.get('region') == region]
        if not here:
            continue
        cards = ''
        for c in here:
            first = c['urgent'][0] if c['urgent'] and lines else None
            line = f'<span class="meta">{E(first["label"])}: {E(first["phone"])}</span>' if first else ''
            cards += f'<li id="{c["slug"]}"><a href="{prefix}{c["slug"]}.html"><strong>{E(c["name"])}</strong><span>{E(c["peoples"])}</span>{line}</a></li>'
        out += f'<h{level} class="region">{E(region)}</h{level}><ul class="needs world-cards">{cards}</ul>'
    return out


def country_names():
    names = [c['name'] for c in COUNTRIES if c['slug'] and c['code'] != 'WORLD']
    return ', '.join(names[:-1]) + ' and ' + names[-1]


def world_slug(code):
    return COUNTRY[code]['slug']


def finder_data():
    """Everything the map shows, as one compact file the home page loads. Columns are listed in 'cols'."""
    pts = []

    def add(lat, lon, kind, name, sub, needs, country, phone=None, telno=None, url=None, page=None, access=None, pin=None):
        pts.append([lat, lon, kind, name, sub or '', ','.join(needs), country, phone or '', telno or '', url or '',
                    page or '', access or '', pin or ''])

    for n in NATIONS:
        if n.get('lat') is None:
            continue
        add(n['lat'], n['lon'], 'nation', n['name'], ', '.join(x for x in [n.get('city'), STATE_NAME[n['state']]] if x),
            ['nation'], 'US', n['phone']['display'] if n.get('phone') else None, n['phone']['tel'] if n.get('phone') else None,
            n.get('url'), f'states/{STATE_SLUG[n["state"]]}.html#n-{n["id"]}')
    for code, items in CLINICS.items():
        for c in items:
            if 'lat' not in c:
                continue
            m = PHONE_RE.search(c.get('phone') or '')
            sub = ' · '.join(x for x in [RUN_LABEL[c['run']].replace('Run by the ', '').replace('Run by a ', ''),
                                          f'{c["city"]}, {STATE_NAME[code]}' if c.get('city') else STATE_NAME[code]] if x)
            add(c['lat'], c['lon'], 'clinic', c['name'], sub, CLINIC_NEED[c['kind']], 'US',
                m.group(0).strip() if m else None, ('+1' + ''.join(m.group(1, 2, 3))) if m else None,
                c.get('url') if (c.get('url') or '').startswith('http') else None, f'states/{STATE_SLUG[code]}.html#clinics-h',
                'ask' if c['run'] != 'urban' else 'native')
    for code, items in COLLEGES.items():
        for c in items:
            if 'lat' in c:
                m = PHONE_RE.search(c.get('phone') or '')
                add(c['lat'], c['lon'], 'college', c['name'], f'{c.get("city", "")}, {STATE_NAME[code]}', ['school', 'community'], 'US',
                    m.group(0).strip() if m else None, ('+1' + ''.join(m.group(1, 2, 3))) if m else None, c.get('url'),
                    f'states/{STATE_SLUG[code]}.html#tcu-h', 'anyone')
    seen = set()
    for code, items in LANDS.items():
        for a in items:
            if 'lat' not in a or (a['name'], a['lat']) in seen:
                continue
            seen.add((a['name'], a['lat']))
            add(a['lat'], a['lon'], 'land', a['name'], LAND_LABEL.get(a['kind'], 'Tribal land') + f' · {STATE_NAME[code]}',
                ['nation'], 'US', page=f'states/{STATE_SLUG[code]}.html#lands-h')
    for r in RES:
        if 'lat' in r:
            add(r['lat'], r['lon'], 'place', r['name'], r.get('place') or STATE_NAME.get(r['area'], ''), [r['need']] + r.get('also', []),
                'US', r.get('phone'), tel_of(r) if r.get('phone') else None, r.get('url'),
                f'states/{STATE_SLUG[r["area"]]}.html#r-{r["id"]}', r['access'], r.get('pin'))
    for n in CA_PLACES['first_nations']['items']:
        add(n['lat'], n['lon'], 'fn', n['name'], 'Canada', ['nation'], 'CAN', url=n['url'],
            page='world/canada.html#first-nations')
    for n in CA_PLACES['inuit']['items']:
        sub = ' · '.join(x for x in [n.get('inuktut') if n.get('inuktut') != n['name'] else None, n.get('region'), n.get('province')] if x)
        add(n['lat'], n['lon'], 'inuit', n['name'], sub, ['nation', 'community'], 'CAN', page='world/canada.html#inuit')
    for r in WORLD:
        if 'lat' in r:
            add(r['lat'], r['lon'], 'place', r['name'], r.get('place', ''), [r['need']] + r.get('also', []), r['area'],
                r.get('phone'), tel_of(r) if r.get('phone') else None, r.get('url'),
                f'world/{world_slug(r["area"])}.html#r-{r["id"]}', r['access'], r.get('pin'))

    for h in HISTORIC:
        add(h['lat'], h['lon'], 'history', h['name'], STATE_NAME[h['state']], ['history'], 'US', url=h['url'],
            page=f'proud-history.html#hs-{h["id"]}')

    for c in COUNTRIES:
        if c['slug'] and c['code'] != 'WORLD':
            add(c['center'][0], c['center'][1], 'guide', f'{c["name"]}: country guide', c['peoples'], FINDER_NEEDS, c['code'],
                page=f'world/{c["slug"]}.html')

    def wide(r, page_path):
        return {'id': r['id'], 'name': r['name'], 'needs': [r['need']] + r.get('also', []), 'what': r['what'],
                'access': r['access'], 'phone': r.get('phone'), 'tel': tel_of(r) if r.get('phone') else None,
                'sms': r['sms']['to'] if r.get('sms') else None, 'url': r.get('url'), 'label': r.get('url_label'),
                'page': page_path, 'urgent': r.get('urgent')}

    national = {'US': [wide(r, f'help.html#r-{r["id"]}') for r in RES if r['area'] == 'US']}
    for r in WORLD:
        if 'lat' not in r:
            national.setdefault(r['area'], []).append(wide(r, f'world/{world_slug(r["area"])}.html#r-{r["id"]}'))
    countries = [{k: c.get(k) for k in ('code', 'name', 'peoples', 'center', 'zoom', 'emergency', 'urgent')}
                 | {'page': f'world/{c["slug"]}.html' if c['slug'] else 'help.html'} for c in COUNTRIES]
    needs = [{'key': k, 'label': NEED[k]['short']} for k in FINDER_NEEDS] + [{'key': k, 'label': v} for k, v in FINDER_EXTRA.items()]
    access = {k: v['label'] for k, v in ACCESS.items()}
    data = {'cols': ['lat', 'lon', 'kind', 'name', 'sub', 'needs', 'country', 'phone', 'tel', 'url', 'page', 'access', 'pin'],
            'kinds': KIND_LABEL, 'points': pts, 'national': national, 'countries': countries, 'needs': needs, 'access': access}
    out = ROOT / 'assets/finder'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'data.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    (out / 'lands.geojson').write_text((ROOT / 'data/map/lands.geojson').read_text(encoding='utf-8'), encoding='utf-8')
    return data


# The "I'm..." chooser on the home page. Each person gets a short line and links to what already exists on the site.
WHO = [
    ('land', 'living on a reservation or tribal land',
     'Your Nation\'s own offices come first, then the clinics, colleges and programs that serve tribal lands.',
     [('nations.html', 'Your Nation\'s government office'), ('states/index.html', 'Tribal lands, Indian health clinics and tribal colleges in your state'),
      ('help.html#r-tribal-housing', 'Tribal housing programs'), ('help.html#r-fdpir', 'Food Distribution Program on Indian Reservations'),
      ('what-works.html', 'Programs that have worked in Native communities')]),
    ('urban', 'Native and living in a city',
     'Urban Indian centers and health programs, and Native community groups near you.',
     [('community.html#c-urban', 'Urban Indian centers'), ('help.html#r-urban-indian-health', 'Urban Indian health programs'),
      ('community.html#c-local', 'Community centers and groups by state'), ('nations.html', 'Reach your Nation from wherever you live')]),
    ('reconnect', 'reconnecting with my family or my heritage',
     'How to trace your family, how enrollment works, and how to find community while you look.',
     [('find-your-nation.html', 'Finding your Nation'), ('find-your-nation.html#f5', 'If you were adopted, in foster care, or your family was separated'),
      ('help.html#r-boarding-school-archive', 'Indian boarding school records'), ('community.html', 'Finding community')]),
    ('nonfed', 'from a Nation without federal recognition',
     'Nations recognized by a state have their own section, and much of the help here does not ask for a tribal card.',
     [('nations.html#state-recognized', 'Nations recognized by a state'), ('find-your-nation.html#f7', 'If your Nation is not federally recognized'),
      ('help.html', 'Help, with a filter for listings that do not ask for enrollment')]),
    ('veteran', 'a Native veteran',
     'VA help written for Native veterans, and the crisis line for veterans.',
     [('help.html#veterans', 'Help for veterans'), ('help.html#r-va-copay-exemption', 'No VA copays for Native veterans'),
      ('help.html#r-va-nadl', 'VA home loans on trust land'), ('help.html#r-homeless-veterans-call-center', 'If you are a veteran with no place to stay'),
      ('help.html#r-veterans-crisis-line', 'Veterans Crisis Line'),
      ('proud-history.html#p3', 'Serving at the highest rate')]),
    ('student', 'a Native student',
     'Scholarships, tribal colleges, and youth councils and resources for Native young people.',
     [('help.html#school', 'School and scholarships'), ('community.html#c-tcu', 'Tribal colleges'),
      ('help.html#r-unity', 'UNITY youth councils'), ('help.html#r-we-r-native', 'We R Native')]),
    ('family', 'raising Native children',
     'Your family\'s rights under the Indian Child Welfare Act, and help for parents and young families.',
     [('help.html#family', 'Children, youth and family'), ('help.html#r-icwa-rights', 'The Indian Child Welfare Act: your family\'s rights'),
      ('help.html#r-nicwa', 'National Indian Child Welfare Association'), ('what-works.html#w1', 'Home visits for young families')]),
    ('elder', 'an elder, or caring for one',
     'Elder programs run by tribes, and help with food, bills and health care.',
     [('help.html#elders', 'Elders'), ('help.html#r-title-vi-elders', 'Elder programs run by tribes'),
      ('help.html#money', 'Food, money and bills'), ('help.html#health', 'Health care')]),
    ('recovery', 'in recovery, or want to be',
     'Wellbriety circles, treatment for Native youth, and the national helpline.',
     [('help.html#recovery', 'Recovery and wellness'), ('help.html#r-wellbriety-circles', 'Wellbriety circles'),
      ('help.html#r-ihs-yrtc', 'Youth Regional Treatment Centers'), ('help.html#r-samhsa-helpline', 'SAMHSA National Helpline')]),
    ('staff', 'working for a Nation or a tribal program',
     'A free page for your Nation or program, programs with measured results, and how to correct your listing.',
     [('free-page.html', 'Get a free page for your community'), ('what-works.html', 'What has worked'),
      ('about.html#a5', 'For Nations and organizations'), ('nations.html', 'Nations directory')]),
    ('ally', 'looking for ways to support Native-led groups',
     'What groups are asking for, in their own words, and how to give in ways that help.',
     [('support.html', 'Support Native-led groups'), ('community.html#c-pages', 'Community pages'), ('what-works.html', 'What has worked')]),
    ('world', 'Indigenous, outside the United States',
     'Country guides in each people\'s own terms, from Canada and Mexico to Aotearoa, Sápmi and beyond.',
     [('world/index.html', 'First Peoples around the world'), ('world/canada.html', 'Canada'), ('world/aotearoa-new-zealand.html', 'Aotearoa New Zealand'),
      ('world/australia.html', 'Australia')]),
]


def who_chooser():
    """The short "I'm..." row near the top of the home page; each choice opens its own panel lower down."""
    return ('<nav class="chips iam" aria-labelledby="iam-h"><p id="iam-h" class="iam-h">I\'m…</p><ul>'
            + ''.join(f'<li><a href="#who-{k}">{E(label)}</a></li>' for k, label, _, _ in WHO)
            + '<li><a href="help.html#safety">in danger, or in crisis right now</a></li></ul></nav>')


WHO_ICON = {'land': 'land', 'urban': 'city', 'reconnect': 'tree', 'nonfed': 'nation', 'veteran': 'veterans', 'student': 'cap',
            'family': 'family', 'elder': 'elders', 'recovery': 'recovery', 'staff': 'work', 'ally': 'heart', 'world': 'globe'}


def who_panels():
    out = ''
    for k, label, line, links in WHO:
        lst = ''.join(f'<li><a href="{E(href)}">{E(text)}</a></li>' for href, text in links)
        out += f'<article id="who-{k}"><h3>{icon(WHO_ICON.get(k), cls="ico hico")}I\'m {E(label)}</h3><p>{E(line)}</p><ul>{lst}</ul></article>'
    # Collapsed until someone picks an "I'm..." choice at the top, so the opening page stays clean; the links stay in the page.
    return f'<section class="who-sec" aria-labelledby="paths-h"><h2 id="paths-h">Start where you are</h2><div class="paths who">{out}</div></section>'


def build_home():
    data = finder_data()
    country_opts = ''.join(f'<option value="{c["code"]}">{E(c["name"])}</option>' for c in COUNTRIES)
    need_btns = '<button type="button" class="chip" aria-pressed="true" data-need="">Everything</button>' + ''.join(
        f'<button type="button" class="chip" aria-pressed="false" data-need="{k}">{E(NEED[k]["short"])}</button>' for k in FINDER_NEEDS) + ''.join(
        f'<button type="button" class="chip" aria-pressed="false" data-need="{k}">{E(label)}</button>' for k, label in FINDER_EXTRA.items())
    counts = Counter(p[2] for p in data['points'])
    legend = ''.join(f'<li><span class="key k-{k}" aria-hidden="true"></span>{E(label)} <span class="count">{counts.get(k, 0):,}</span></li>'
                     for k, label in KIND_LABEL.items() if counts.get(k))
    world_cards = country_cards('world/', lines=False)
    body = f'''<section class="finder" aria-labelledby="find-h">
<div class="finder-head"><h1 id="find-h">Find help, your Nation and your people</h1>
<p class="lede">A free map for First Peoples: Nations, clinics, community centers, tribal colleges, tribal lands and historic sites. Tap a place to call, get directions or open its website. <span class="dedication">{E(SITE['dedication'])}</span></p></div>
{who_chooser()}
<form class="finder-controls" role="search" onsubmit="return false">
<p class="ctl"><label for="f-country">Where</label> <select id="f-country">{country_opts}</select></p>
<p class="ctl"><button type="button" class="btn" id="f-locate">Use my location</button></p>
<p class="ctl grow"><label for="f-search">Search</label> <input id="f-search" type="search" autocomplete="off" placeholder="A Nation, a clinic, a town"></p>
</form>
<div class="chips needs-bar" role="group" aria-label="What do you need?">{need_btns}</div>
<p class="ctl small"><label><input type="checkbox" id="f-open"> Only places that do not ask for a tribal card</label>
 <label><input type="checkbox" id="f-lands" checked> Show reservation and tribal land outlines</label></p>
<p id="f-status" class="pick-prompt" role="status">Choose what you need, search for a Nation, clinic or town, use your location, or zoom into your area. The places will be listed next to the map.</p>
<div class="finder-body start">
<div class="mapwrap"><div id="map" role="region" aria-label="Map of Nations, help and community. Once you choose what you need, search or zoom in, the same places are listed next to the map."></div>
<ul class="legend" aria-label="Map key">{legend}</ul>
<p class="meta">Your location, if you share it, stays on your device. The map pictures come from OpenStreetMap, which sees which area you look at. <a href="about.html#a6">Privacy</a></p></div>
<div class="results" id="f-results" hidden>
<h2 id="near-h">Closest to the middle of the map</h2>
<ol id="f-list" class="hits"></ol>
<h2 id="wide-h">Help anywhere in <span id="f-cname">the United States</span></h2>
<ul id="f-wide" class="wide"></ul>
<p><a id="f-more" href="help.html">All help for this country</a></p>
</div></div>
<noscript><p class="panel">The map needs JavaScript. Everything on it is also on the <a href="states/index.html">state pages</a>, the <a href="nations.html">Nations directory</a> and the <a href="world/index.html">country pages</a>.</p></noscript>
</section>
{who_panels()}
<section aria-labelledby="world-h"><h2 id="world-h">First Peoples around the world</h2>
<p>Nina's Map started in the United States and is growing country by country, each one in its own peoples' terms.</p>
{world_cards}</section>
<section class="panel" aria-labelledby="who-h"><h2 id="who-h">Who made this, and who it needs</h2>
<p>This guide was built by {E(SITE['maintainer'])} from what Nations, governments and Indigenous organizations publish about themselves. It is not a tribal government and does not speak for any Nation. It covers the United States in the most detail, with Ohio and Michigan the deepest, and now reaches {len([c for c in COUNTRIES if c['slug'] and c['code'] != 'WORLD'])} more countries and homelands: {E(country_names())}.</p>
<p>It needs Indigenous people to look it over. If you work for a Nation, a tribal program or an Indigenous organization, or you know something here is wrong or missing, <a href="mailto:{E(SITE['email'])}">write to us</a>. <a href="about.html">Read how the site is put together</a>.</p></section>'''
    head = ('<link rel="stylesheet" href="assets/vendor/leaflet.css"><link rel="stylesheet" href="assets/vendor/markercluster.css">'
            '<script src="assets/vendor/leaflet.js" defer></script><script src="assets/vendor/leaflet.markercluster.js" defer></script>'
            '<script src="assets/finder.js" defer></script>')
    page('index.html', f'{SITE["name"]}: help, Nations and community for First Peoples', SITE['description'], body, head)


def build_world():
    up = '../'
    cards = ''
    for c in COUNTRIES:
        if not c['slug']:
            continue
        recs = [r for r in WORLD if r['area'] == c['code']]
        h1 = (f'{c["name"]}: help and community for {c["peoples"]}' if recs else f'{c["peoples"]} in {c["name"]}: where to start')
        body = (f'<p class="crumb"><a href="index.html">All countries</a></p><h1>{E(h1)}</h1>'
                + (f'<p class="lede">{E(c["welcome"])}</p><p>{E(c["intro"])}</p>' if c.get('welcome') else f'<p class="lede">{E(c["intro"])}</p>'))
        if c.get('intro_sources'):
            body += '<p class="meta">Sources: ' + ' · '.join(f'<a href="{E(s["url"])}">{E(s["label"])}</a>' for s in c['intro_sources']) + '.</p>'
        if c.get('report'):
            body += (f'<p class="panel report">Background: <a href="{E(c["report"])}">read the {E(c["name"])} chapter of <em>The Indigenous World {c.get("report_year", 2026)}</em></a>, '
                     'the yearly report of the International Work Group for Indigenous Affairs (IWGIA), on land, rights, health and recent events.</p>')
        body += f'<p><a class="btn" href="../index.html#{c["slug"]}">See {E(c["name"])} on the map</a></p>'
        for need in NEED_LIST:
            here = [r for r in recs if r['need'] == need['key']]
            if here:
                label = 'Peoples, Nations and their governments' if need['key'] == 'nation' else need['label']
                body += (f'<section class="need" id="{need["key"]}" aria-labelledby="h-{need["key"]}"><h2 id="h-{need["key"]}">{need_icon(need["key"], up, "ico hico")}{E(label)}</h2>'
                         '<div class="cards">' + ''.join(card(r, 3, up) for r in here) + '</div>'
                         + (f'<p>In immediate danger, call {E(c["emergency"])}.</p>' if need['key'] == 'safety' and c.get('emergency') else '')
                         + '</section>')
        if c['code'] == 'CAN':
            fns = CA_PLACES['first_nations']
            body += (f'<section id="first-nations" aria-labelledby="fn-h"><h2 id="fn-h">First Nations ({len(fns["items"])})</h2>'
                     '<p>Each name links to the First Nation\'s official profile from Indigenous Services Canada, with its address, phone and more. '
                     'Names are written as the department registers them.</p>'
                     '<p class="search"><label for="q">Search by name</label> <input id="q" type="search" autocomplete="off" data-nation-search> <span id="q-count" role="status"></span></p>'
                     '<section class="st"><ul class="nations cols">' + ''.join(
                         f'<li data-k="{E(n["name"].lower())}"><a href="{E(n["url"])}">{E(n["name"])}</a></li>' for n in fns['items']) + '</ul></section>'
                     f'<p class="meta">From <a href="{E(fns["source_page"])}">First Nations Location</a>, {E(fns["publisher"])}, retrieved {nice_date(CA_PLACES["retrieved"])}. Open Government Licence – Canada.</p></section>')
            inuit = CA_PLACES['inuit']
            regions = defaultdict(list)
            for n in inuit['items']:
                regions[n.get('region', 'Other')].append(n)
            body += f'<section id="inuit" aria-labelledby="inuit-h"><h2 id="inuit-h">Inuit communities ({len(inuit["items"])})</h2><p>Inuit Nunangat, the Inuit homeland, has four regions. Names are shown in English and in Inuktut where the dataset gives them.</p>'
            for region in sorted(regions):
                body += f'<h3>{E(region)}</h3><ul class="nations cols">' + ''.join(
                    f'<li><span class="nm">{E(n["name"])}</span>'
                    + (f' <span class="aka">{E(n["inuktut"])}{" · " + E(n["syllabics"]) if n.get("syllabics") else ""}</span>' if n.get('inuktut') and n['inuktut'] != n['name'] else '')
                    + f' <span class="where">{E(n.get("province", ""))}</span></li>' for n in regions[region]) + '</ul>'
            body += f'<p class="meta">From <a href="{E(inuit["source_page"])}">Inuit Communities Location</a>, {E(inuit["publisher"])}, retrieved {nice_date(CA_PLACES["retrieved"])}.</p></section>'
        body += (f'<section class="panel"><h2>Help us fill in {E(c["name"])}</h2><p>This page is new and short on purpose: everything on it is read from the organization\'s own page or a government page. '
                 f'If you know a program, a community center or a correction that belongs here, write to <a href="mailto:{E(SITE["email"])}">{E(SITE["email"])}</a>.</p></section>')
        desc = clip(c.get('welcome') or f'Help for {c["peoples"]} in {c["name"]}, with sources.')
        page(f'world/{c["slug"]}.html', fit(f'{h1} | {SITE["name"]}', h1, f'{c["name"]}: Indigenous help and community'), desc, body)
        first = c['urgent'][0] if c['urgent'] else None
        line = f'<span class="meta">{E(first["label"])}: {E(first["phone"])}</span>' if first else ''
        cards += f'<li><a href="{c["slug"]}.html"><strong>{E(c["name"])}</strong><span>{E(c["peoples"])}</span>{line}</a></li>'
    body = f'''<h1>First Peoples around the world</h1>
<p class="lede">If you are Indigenous outside the United States, find your country or homeland below. Each page uses its peoples' own terms and starts with the help we could confirm there.</p>
<p>Nina's Map began in the United States and is growing one country at a time. Every listing shows where it came from and when it was checked.</p>
<p>Country pages so far: {E(country_names())}, and help that reaches Indigenous peoples anywhere. Some pages are starters, with background and the help we could confirm; more are on the way. If you want your country next, or know what belongs on its page, <a href="mailto:{E(SITE['email'])}">tell us</a>.</p>
{country_cards(level=2)}
<p><a class="btn" href="../index.html">Open the map</a> <a class="btn line" href="../help.html">Help in the United States</a></p>'''
    page('world/index.html', f'Indigenous help and community worldwide | {SITE["name"]}',
         'Help lines, health care, family support and Nation and community directories for Indigenous peoples in Canada, Mexico, Australia, Aotearoa New Zealand, Sápmi and worldwide.', body)


def build_sitemap():
    dates = [r['checked'] for r in RES + WORLD] + [NATIONS_FILE['retrieved']]
    lastmod = max(dates)
    urls = ''.join(
        f'<url><loc>{E(SITE["base_url"] + ("" if p == "index.html" else p))}</loc><lastmod>{lastmod}</lastmod></url>\n'
        for p in PAGES)
    (ROOT / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + '</urlset>\n',
        encoding='utf-8')
    # IndexNow key file: proves the site is ours when .github/workflows/indexnow.yml tells Bing which pages changed
    (ROOT / 'c35dba3c0b0747ccfdcaa1c2e416e828.txt').write_text('c35dba3c0b0747ccfdcaa1c2e416e828', encoding='utf-8')
    (ROOT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {SITE["base_url"]}sitemap.xml\n', encoding='utf-8')


# ---------- free community pages, the offer, and ways to help ----------

INTAKE = SITE['intake_email']  # The one address for page requests. Change it in data/site.json.

HELP_SOURCES = [
    ('Federal Trade Commission: Donating safely and avoiding scams', 'https://consumer.ftc.gov/features/donating-safely-and-avoiding-scams'),
    ('Federal Trade Commission: Buying American Indian arts and crafts', 'https://consumer.ftc.gov/articles/buying-american-indian-arts-and-crafts'),
    ('Indian Arts and Crafts Board: Consumer tips', 'https://www.doi.gov/iacb/consumer-tips'),
    ('Indian Arts and Crafts Board: Source Directory of Arts and Crafts Businesses', 'https://www.doi.gov/iacb/source-directory'),
    ('FEMA: Three ways to help after Hurricane Maria', 'https://www.fema.gov/press-release/20250121/three-ways-help-after-hurricane-maria'),
    ('The Bridgespan Group with Native Americans in Philanthropy: The impact and opportunity of investing in Native communities', 'https://www.bridgespan.org/insights/the-impact-and-opportunity-of-investing-in-native-communities'),
]
HELP_CHECKED = '2026-11-23'


def intake_mailto(subject, body):
    return f'mailto:{INTAKE}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}'


def ask_item(c, ask, up, show_group=False):
    """One "how you can help" entry, in the group's own words. Dated asks drop off the page once their date passes."""
    until = f' data-until="{ask["until"]}"' if ask.get('until') else ''
    out = f'<li class="ask ask-{ask["kind"]}"{until}><strong>{icon(ASK_ICON[ask["kind"]], up)}{E(ASK_KINDS[ask["kind"]])}'
    if show_group:
        out += f': <a href="{up}communities/{c["slug"]}.html">{E(c["name"])}</a>'
    out += f'</strong> <span>{E(ask["text"])}</span>'
    if ask.get('items'):
        out += '<ul>' + ''.join(f'<li>{E(i)}</li>' for i in ask['items']) + '</ul>'
    if ask.get('until'):
        out += f'<span class="meta"> Through {nice_date(ask["until"])}.</span>'
    if ask.get('url'):
        out += f' <a class="btn line" href="{E(ask["url"])}">{E(ask.get("label") or ASK_KINDS[ask["kind"]])}</a>'
    return out + '</li>'


def community_contact_buttons(c):
    ct = c.get('contact', {})
    out = []
    if ct.get('phone'):
        out.append(f'<a class="btn call" href="tel:{tel(ct["phone"])}">Call {E(ct["phone"])}</a>')
    if ct.get('email'):
        out.append(f'<a class="btn line" href="mailto:{E(ct["email"])}">Email {E(ct["email"])}</a>')
    if ct.get('url'):
        out.append(f'<a class="btn line" href="{E(ct["url"])}">Website</a>')
    return '<p class="actions">' + ' '.join(out) + '</p>' if out else ''


def community_page(c):
    up = '../'
    slug, name = c['slug'], c['name']
    kind = COMMUNITY_KINDS[c['kind']]
    body = f'<p class="crumb"><a href="{up}community.html">Community</a> · <a href="{up}free-page.html">Get a free page for your community</a></p>'
    if c.get('demo'):
        body += ('<aside class="demo" aria-label="This is a demonstration page"><strong>Example page.</strong> Everything here is made up to show '
                 'what a free community page looks like. It is not a real group. '
                 f'<a href="{up}free-page.html">Get a real page for your community</a>.</aside>')
    logo = f'<img class="cp-logo" src="{up}assets/communities/{slug}/{E(c["logo"]["src"])}" alt="{E(c["logo"]["alt"])}" width="96" height="96">' if c.get('logo') else ''
    body += f'<div class="cp-head">{logo}<div><h1>{E(name)}</h1><p class="meta">{E(kind)} · {E(c["place"])}</p></div></div>'
    body += f'<p class="lede">{E(c["intro"])}</p>' + community_contact_buttons(c)
    body += (f'<p class="owner">This page is written and maintained by {E(c["maintained_by"])}. Last updated {nice_date(c["updated"])}. '
             f'{E(SITE["name"])} hosts it for free and does not speak for {E(name)}. To change or remove it, {E(c["maintained_by"])} can write to '
             f'<a href="mailto:{E(INTAKE)}">{E(INTAKE)}</a>.</p>')
    chips = []
    sections = ''
    if c.get('message'):
        sections += '<section aria-labelledby="cp-msg"><h2 id="cp-msg">In our words</h2>' + ''.join(f'<p>{E(x)}</p>' for x in c['message']) + '</section>'
    if c.get('announcements'):
        chips.append(('cp-news', 'News'))
        sections += ('<section aria-labelledby="cp-news"><h2 id="cp-news">News and announcements</h2>' + ''.join(
            f'<article class="card"><h3>{E(a["title"])}</h3><p class="meta">{nice_date(a["date"])}</p><p>{E(a["text"])}</p></article>'
            for a in sorted(c['announcements'], key=lambda a: a['date'], reverse=True)) + '</section>')
    if c.get('events'):
        chips.append(('cp-events', 'Events'))
        items = ''
        for ev in sorted(c['events'], key=lambda e: e['date']):
            when = nice_date(ev['date']) + (f' to {nice_date(ev["end"])}' if ev.get('end') else '') + (f', {ev["time"]}' if ev.get('time') else '')
            more = f' <a href="{E(ev["url"])}">More about it</a>' if ev.get('url') else ''
            items += (f'<li data-until="{ev.get("end") or ev["date"]}"><strong>{E(ev["title"])}</strong> <span class="where">{E(when)}'
                      + (f' · {E(ev["where"])}' if ev.get('where') else '') + f'</span> <span>{E(ev.get("text", ""))}</span>{more}</li>')
        sections += (f'<section aria-labelledby="cp-events"><h2 id="cp-events">Coming up</h2><ul class="events" data-expiring>{items}</ul>'
                     '<p class="meta" data-none hidden>No upcoming events are posted right now.</p></section>')
    if c.get('help'):
        chips.append(('cp-help', 'How you can help'))
        sections += ('<section aria-labelledby="cp-help" class="panel helpbox"><h2 id="cp-help">How you can help</h2>'
                     f'<p>In {E(c["maintained_by"])}\'s own words: what would help right now.</p><ul class="asks" data-expiring>'
                     + ''.join(ask_item(c, a, up) for a in c['help']) + '</ul><p class="meta" data-none hidden>Nothing is posted right now.</p></section>')
    if c.get('programs'):
        chips.append(('cp-programs', 'Programs'))
        sections += ('<section aria-labelledby="cp-programs"><h2 id="cp-programs">Programs</h2><div class="cards">' + ''.join(
            f'<article class="card"><h3>{E(pr["name"])}</h3><p>{E(pr["text"])}</p>'
            + (f'<p class="actions"><a class="btn line" href="{E(pr["url"])}">Learn more</a></p>' if pr.get('url') else '') + '</article>'
            for pr in c['programs']) + '</div></section>')
    if c.get('photos'):
        sections += ('<section aria-labelledby="cp-photos"><h2 id="cp-photos">Photos</h2><div class="cp-photos">' + ''.join(
            f'<figure><img src="{up}assets/communities/{slug}/{E(ph["src"])}" alt="{E(ph["alt"])}" loading="lazy">'
            + (f'<figcaption>{E(ph["caption"])}</figcaption>' if ph.get('caption') else '') + '</figure>' for ph in c['photos']) + '</div></section>')
    ct = c.get('contact', {})
    contact = ''
    if ct.get('address'):
        contact += f'<p><strong>Address:</strong> {E(ct["address"])}</p>'
    contact += community_contact_buttons(c)
    if c.get('links'):
        contact += '<ul>' + ''.join(f'<li><a href="{E(l["url"])}">{E(l["label"])}</a></li>' for l in c['links']) + '</ul>'
    if contact:
        chips.append(('cp-contact', 'Contact'))
        sections += f'<section aria-labelledby="cp-contact"><h2 id="cp-contact">Contact and links</h2>{contact}</section>'
    if chips:
        body += '<nav class="chips" aria-label="On this page"><ul>' + ''.join(f'<li><a href="#{i}">{E(l)}</a></li>' for i, l in chips) + '</ul></nav>'
    body += sections
    if c.get('nation_id'):
        n = NATION[c['nation_id']]
        body += f'<p class="meta">{E(name)} in the <a href="{up}states/{STATE_SLUG[n["state"]]}.html#n-{n["id"]}">Nations directory</a>.</p>'
    body += (f'<section class="panel"><h2>Want a page like this?</h2><p>Nations, tribal programs, urban Indian organizations, powwow committees, language programs, '
             f'Native-owned businesses and community groups can have one for free. <a href="{up}free-page.html">Here is how</a>.</p></section>')
    if c.get('demo'):
        title = f'Example community page (demo) | {SITE["name"]}'
        desc = 'A made-up example of a free community page on Nina\'s Map, showing what a Native community group can post: news, events, programs, photos and how people can help.'
    else:
        title = fit(f'{name}: {kind.lower() if c["kind"] != "nation" else "Nation"} in {c["place"]} | {SITE["name"]}',
                    f'{name}: {kind.lower() if c["kind"] != "nation" else "Nation"} in {c["place"]}', f'{name} | {SITE["name"]}', name)
        desc = clip(c['intro'])
    page(f'communities/{slug}.html', title, desc, body, noindex=bool(c.get('demo')))


def build_community_pages():
    for c in COMMUNITIES:
        community_page(c)


def community_pages_section():
    """The list of community pages on the Community hub."""
    if LIVE_COMMUNITIES:
        lst = '<ul class="nations">' + ''.join(
            f'<li><span class="nm"><a href="communities/{c["slug"]}.html">{E(c["name"])}</a></span> <span class="where">{E(COMMUNITY_KINDS[c["kind"]])} · {E(c["place"])}</span></li>'
            for c in sorted(LIVE_COMMUNITIES, key=lambda c: c['name'].lower())) + '</ul>'
    else:
        lst = '<p>No group has a page yet. The first ones are being set up; each will be listed here.</p>'
    return ('<section aria-labelledby="c-pages"><h2 id="c-pages">' + icon('layout', cls='ico hico') + 'Community pages, in each group\'s own words</h2>'
            '<p>Pages written and kept up by the groups themselves: their news, events, programs and what would help.</p>'
            f'{lst}<p><a class="btn" href="free-page.html">Get a free page for your community</a> <a class="btn line" href="communities/example.html">See an example page</a></p></section>')


def build_offer():
    mail = E(INTAKE)
    body_text = ('Name of our Nation, program or group:\n'
                 'Town and state (or country):\n'
                 'Who we are, in a few sentences:\n'
                 'Contact we want shown (phone, email, website):\n'
                 'Upcoming events or news:\n'
                 'How people can help (donate, volunteer, attend, buy, share, supplies):\n'
                 'My name and my role with the group:\n'
                 'A phone number or email where you can confirm this request with us:\n')
    href = E(intake_mailto('Free community page request', body_text))
    share = (f'Free pages for Native communities: {SITE["name"]} will set up a page for your Nation, tribal program, urban Indian organization, '
             f'powwow committee, language program, Native-owned business or community group, at no cost. You decide what it says and can remove it '
             f'at any time. Details: {SITE["base_url"]}free-page.html')
    body = f'''<h1>Get a free page for your community</h1>
<p class="lede">If you work for a Nation or a tribal program, or you organize a Native community group, powwow, language class or business, {E(SITE['name'])} will set up a page for you, free. You say what goes on it; it is there for your news, your events and what you need.</p>
<p class="actions"><a class="btn" href="{href}">Ask for a page by email</a> <a class="btn line" href="communities/example.html">See an example page</a></p>

<section aria-labelledby="o1"><h2 id="o1">What you get</h2>
<ul>
<li>Your own page at an address like {E(SITE['base_url'])}communities/your-name.html, with your name, logo and photos.</li>
<li>Your message, in your own words, and your announcements and events. Past events drop off on their own.</li>
<li>Your programs, your contact details and your links.</li>
<li>A "How you can help" section for what you need right now: donations, volunteers, people at your events, customers, people to share the word, or a list of supplies.</li>
<li>Links to your page from your listing on {E(SITE['name'])}, from the Community page, and, when you post an ask, from <a href="support.html">Support Native-led groups</a>.</li>
</ul></section>

<section aria-labelledby="o2"><h2 id="o2">Free, with no catch</h2>
<ul>
<li>There is no fee, now or later, and nothing to sign up for.</li>
<li>The page is yours. It says what you want it to say, and it says on the page that you wrote it and keep it up.</li>
<li>You can change it whenever you like, and have it taken down at any time, for any reason. Just ask.</li>
<li>{E(SITE['name'])} does not speak for your Nation or your group, and does not add anything to your page that you did not send or approve.</li>
<li>The page has no ads. Visits are counted without cookies, as on the rest of the site, and nothing about your visitors is sold.</li>
</ul></section>

<section aria-labelledby="o3"><h2 id="o3">What to send</h2>
<p>Send whatever you have; a name and a few sentences are enough to start.</p>
<ul class="checklist">
<li>Your group's name as you want it written, and your town and state or country.</li>
<li>A few sentences about who you are and who you serve.</li>
<li>The phone number, email and website you want shown. Only contacts you want public.</li>
<li>Upcoming events and news, with dates.</li>
<li>Programs you run, and how people can join.</li>
<li>How people can help, and until when.</li>
<li>Your logo and a few photos, if you like, with a line about each. Send only photos you have the right to share, and only of people who agreed to be shown.</li>
<li>Your name and your role, and a way to confirm the request with you.</li>
</ul></section>

<section aria-labelledby="o4"><h2 id="o4">How we help you set it up</h2>
<ol class="steps" role="list">
<li>{icon("mail")}<strong>You send what you have</strong> by email, in any form: a flyer, a website, a few lines.</li>
<li>{icon("shield")}<strong>We check that the request comes from your group,</strong> using your group's public phone or email. For a Nation, that means its government office. A page is never made for a group that did not ask for one.</li>
<li>{icon("layout")}<strong>We put the page together</strong> from what you sent, and send you a preview.</li>
<li>{icon("check")}<strong>You approve it,</strong> or tell us what to change. It goes live only when you say so.</li>
<li>{icon("update")}<strong>Send updates any time:</strong> a new event, a new ask, a new photo. Each page shows the date it was last updated.</li>
</ol>
<p>If you are not sure what to say, or what kind of help to ask for, say so, and we will work it out with you.</p></section>

<section aria-labelledby="o5"><h2 id="o5">Send your request</h2>
<p>Email <a href="{href}">{mail}</a>. The link opens an email with a short list of questions; answer the ones you can.</p></section>

<section aria-labelledby="o6" class="panel share-box"><h2 id="o6">Share this offer</h2>
<p>Know a group that should have a page? Pass this along, or print this page and post it.</p>
<p><label for="share-text">Text to copy and share</label></p>
<textarea id="share-text" readonly rows="5">{E(share)}</textarea>
<p><button type="button" class="btn" data-print hidden>Print this page</button></p></section>'''
    page('free-page.html', f'Free web pages for Nations and Native groups | {SITE["name"]}',
         'For tribal staff and Native community organizers: a free page on Nina\'s Map for your Nation, program or group, with your news, events and what you need. You own it and can remove it any time.', body)


def build_support():
    asks = [(c, a) for c in sorted(LIVE_COMMUNITIES, key=lambda c: c['name'].lower()) for a in c.get('help', [])]
    if asks:
        current = ('<ul class="asks" data-expiring>' + ''.join(ask_item(c, a, '', show_group=True) for c, a in asks) + '</ul>'
                   '<p class="meta" data-none hidden>Nothing is posted right now. Check back, or see the general advice below.</p>')
    else:
        current = ('<p>No group has posted an ask yet. As Nations and Native-led groups set up their free pages, what they ask for will appear here, '
                   'in their own words, with a link to their page. Until then, the advice below is a good place to start.</p>')
    sources = ' · '.join(f'<a href="{E(u)}">{E(l)}</a>' for l, u in HELP_SOURCES)
    body = f'''<h1>Support Native-led groups</h1>
<p class="lede">If you want to help Native communities, the surest way is to ask Native-led groups what they need and give that. This page gathers what groups on {E(SITE['name'])} are asking for, and how to give in ways that help.</p>
<nav class="chips glance" aria-label="Ways to help, on this page"><ul>{''.join(f'<li><a href="#{i}">{icon(k)}{l}</a></li>' for i, k, l in [('s1', 'community', 'What groups ask for'), ('s2', 'coins', 'Money'), ('s3', 'box', 'Things'), ('s4', 'bag', 'Buying'), ('s5', 'clock', 'Time')])}</ul></nav>

<section aria-labelledby="s1"><h2 id="s1">{icon('community', cls='ico hico')}What groups are asking for now</h2>
{current}
<p>Run a Native-led group? <a href="free-page.html">Get a free page</a> and post what would help.</p></section>

<section aria-labelledby="s2"><h2 id="s2">{icon('coins', cls='ico hico')}Giving money</h2>
<ul>
<li>Only a small share of philanthropy goes to Native communities, and Native-led organizations receive only part of that share, research by the Bridgespan Group with Native Americans in Philanthropy finds. Giving directly to groups led by Native people is one way to change that.</li>
<li>Before you give, the Federal Trade Commission suggests searching the group's name with words like "complaint", "review" or "scam", and using the IRS Tax Exempt Organization Search to see whether a gift is tax deductible.</li>
<li>Pay by credit card or check. The FTC warns against anyone who asks for donations in cash, by gift card or by wire transfer, and against anyone who rushes you.</li>
</ul>
<h3 id="s2s">Before you give, in three steps</h3>
<ol class="steps" role="list" aria-labelledby="s2s">
<li>{icon('speech')}<strong>Ask the group what it needs,</strong> and give that.</li>
<li>{icon('search')}<strong>Look the group up:</strong> its name with "complaint", "review" or "scam", and the IRS Tax Exempt Organization Search if you want to know whether a gift is tax deductible.</li>
<li>{icon('shield')}<strong>Pay by credit card or check.</strong> Not cash, gift cards or wire transfers, and never because someone rushes you.</li>
</ol></section>

<section aria-labelledby="s3"><h2 id="s3">{icon('box', cls='ico hico')}Giving things</h2>
<p>Ask first. After disasters, FEMA advises that money usually helps most, and that unrequested goods can pull volunteers away from helping people because they have to be sorted, moved and stored. Confirm with the group exactly what it needs before you collect or ship anything. When a group on this site posts a supplies list, it says what is needed and until when.</p></section>

<section aria-labelledby="s4"><h2 id="s4">{icon('bag', cls='ico hico')}Buying from Native artists and businesses</h2>
<ul>
<li>Under federal law, work made after 1935 can be sold as "Indian", "Native American" or as the work of a particular Tribe only if the maker is a member of a federally or state-recognized Tribe, or is certified as an Indian artisan by their Tribe. The FTC says to be careful with words like "descent", "heritage" or "ancestry" next to a Tribe's name.</li>
<li>Get written proof of any claim about who made a piece, and a receipt that lists the maker and their Tribe.</li>
<li>The Indian Arts and Crafts Board keeps a Source Directory of arts and crafts businesses.</li>
</ul></section>

<section aria-labelledby="s5"><h2 id="s5">{icon('clock', cls='ico hico')}Giving time and attention</h2>
<p>Go to the events groups invite the public to. Share their pages and their news. Offer the skills a group asks for, on its terms.</p></section>
<p class="meta">Sources: {sources}. Checked {nice_date(HELP_CHECKED)}.</p>'''
    page('support.html', f'Support Native-led groups: ways to help | {SITE["name"]}',
         'How to help Native communities: what Native-led groups on Nina\'s Map are asking for, in their own words, and how to give money, goods, time and business in ways that help.', body)



def main():
    check_data()
    build_home()
    build_help()
    build_nations()
    build_states()
    build_find()
    build_community()
    build_proud()
    build_works()
    build_world()
    build_about()
    build_community_pages()
    build_offer()
    build_support()
    build_404()
    build_sitemap()
    print(f'{len(PAGES)} pages, {len(RES) + len(WORLD)} listings, {len(NATIONS)} Nation offices')


if __name__ == '__main__':
    main()
