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
CLINICS = CLINICS_FILE['states']
LANDS = LANDS_FILE['states']
NATION = {n['id']: n for n in NATIONS}
STATE_NOTES = load('data/states.json')
MAP = load('data/map/us.json')

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


def check_data():
    """Stop the build on data mistakes that would put a wrong or broken listing on a page."""
    problems = []
    if len(RES_BY_ID) != len(RES):
        problems.append('two listings share an id: ' + ', '.join(k for k, v in Counter(r['id'] for r in RES).items() if v > 1))
    for r in RES:
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
        if r['area'] != 'US' and r['area'] not in STATE_NAME:
            problems.append(f'{r["id"]}: unknown area {r["area"]}')
        if not (r.get('phone') or r.get('sms') or r.get('url') or r.get('email')):
            problems.append(f'{r["id"]}: no way to reach it')
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', r.get('checked', '')):
            problems.append(f'{r.get("id")}: checked must be a date like 2026-11-17')
    for code, note in STATE_NOTES.items():
        if code not in STATE_NAME:
            problems.append(f'states.json: unknown state {code}')
        for nid in note.get('ties', []):
            if nid not in NATION:
                problems.append(f'states.json {code}: no Nation with id {nid}')
    for n in NATIONS:
        if n['state'] not in STATE_NAME:
            problems.append(f'nations.json: {n["id"]} has unknown state {n["state"]}')
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

def actions(r):
    out = []
    if r.get('phone'):
        out.append(f'<a class="btn call" href="tel:{tel(r["phone"])}">Call {E(r["phone"])}</a>')
    if r.get('sms'):
        s = r['sms']
        href = 'sms:' + s['to'] + ('?&body=' + urllib.parse.quote(s['body']) if s.get('body') else '')
        out.append(f'<a class="btn text" href="{E(href)}">{E(s["label"])}</a>')
    if r.get('email'):
        out.append(f'<a class="btn line" href="mailto:{E(r["email"])}">Email {E(r["email"])}</a>')
    if r.get('url'):
        out.append(f'<a class="btn line" href="{E(r["url"])}">{E(r.get("url_label") or "Website")}</a>')
    return out


def card(r, level=3):
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


def urgent(up=''):
    """The help strip near the top of every page that lists programs: suicide and crisis, violence, trafficking.

    Shelter help is not repeated here (owner direction, November 17, 2026). It is one tap away through the
    link at the end of the strip, in the housing section of the help page."""
    return ('<aside class="urgent" aria-labelledby="urgent-h"><h2 id="urgent-h">Need help right now?</h2><ul>'
            '<li>Thinking about suicide, or in any crisis: <a href="tel:988">call 988</a> or <a href="sms:988">text 988</a>, any time. '
            'Veterans: dial 988, then press 1.</li>'
            '<li>Hurt or threatened by a partner or family member, or sexually assaulted: '
            '<a href="tel:+18447628483">call</a> or <a href="sms:+18447628483">text</a> the StrongHearts Native Helpline, 1-844-762-8483.</li>'
            '<li>Being made to work or sell sex: <a href="tel:+18883737888">call 1-888-373-7888</a> or <a href="sms:233733">text 233733</a>.</li>'
            '<li>In immediate danger, call 911.</li></ul>'
            f'<p><a href="{up}help.html#safety">All crisis and safety lines</a> · <a href="{up}help.html#housing">Shelter and housing help</a></p></aside>')


def nation_item(n, show_state=False):
    where = ', '.join(x for x in [n.get('city'), STATE_NAME[n['state']] if show_state else None] if x)
    contact = []
    if n.get('phone'):
        contact.append(f'<a href="tel:{n["phone"]["tel"]}">{E(n["phone"]["display"])}</a>')
    if n.get('url'):
        contact.append(f'<a href="{E(n["url"])}">Website</a>')
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


def state_options(up=''):
    return '<option value="">Choose a state</option>' + ''.join(
        f'<option value="{up}states/{STATE_SLUG[c]}.html">{E(n)}</option>' for c, n in STATES)


NAV = [('help.html', 'Get help'), ('nations.html', 'Nations'), ('states/index.html', 'By state'),
       ('find-your-nation.html', 'Finding your Nation'), ('community.html', 'Community'), ('what-works.html', 'What works'), ('about.html', 'About')]
PAGES = []


def page(path, title, description, body):
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
<link rel="canonical" href="{E(canonical)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{E(SITE['name'])}"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(description)}"><meta property="og:url" content="{E(canonical)}">
<link rel="icon" href="{up}assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{up}assets/site.css">
<script data-goatcounter="{E(SITE['counter'])}" async src="https://gc.zgo.at/count.js"></script>
<script src="{up}assets/site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to main content</a>
<div class="exit"><a id="quick-exit" href="{E(SITE['exit_url'])}" rel="noreferrer">Leave this site now</a> <span>or press Esc twice. This does not clear your browser history.</span></div>
<header class="top"><a class="brand" href="{up}index.html">{E(SITE['name'])}</a><nav aria-label="Main"><ul>{nav}</ul></nav></header>
<main id="main">
{body}
</main>
<footer><p><strong>{E(SITE['dedication'])}</strong> Built and maintained by <a href="{E(SITE['maintainer_url'])}">{E(SITE['maintainer'])}</a>. <a href="mailto:{E(SITE['email'])}">Send a correction</a> · <a href="{up}about.html">About and sources</a></p>
<p>Listings come from tribal governments, government agencies and the organizations themselves, with the date each was checked. This site is not a tribal government, does not speak for any Nation, is not legal advice and does not decide who qualifies for anything. Nations and organizations can ask to have a listing corrected or removed.</p></footer>
</body></html>
'''
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(doc, encoding='utf-8')
    PAGES.append(path)


# ---------- pages ----------

def build_home():
    tiles = ''.join(
        f'<li><a href="help.html#{n["key"]}"><strong>{E(n["label"])}</strong><span>{E(n["blurb"])}</span></a></li>'
        for n in NEED_LIST)
    states = ''.join(f'<li><a href="states/{STATE_SLUG[c]}.html">{E(n)}</a></li>' for c, n in STATES)
    body = f'''<section class="hero"><h1>A map for First Peoples to find help, Nations and community</h1>
<p class="lede">Free, plain-language listings for Native people anywhere in the United States. Every listing shows where it came from and when it was checked. Start with what you need, where you live, or the Nation you come from.</p>
<p class="dedication">{E(SITE['dedication'])}</p></section>
{urgent()}
<section aria-labelledby="needs-h"><h2 id="needs-h">What do you need?</h2><ul class="needs">{tiles}</ul></section>
<section aria-labelledby="paths-h"><h2 id="paths-h">Start where you are</h2><div class="paths">
<article><h3>I am not sure which Nation I come from</h3><p>How to trace your family, what enrollment is, and who can help you look.</p><p><a class="btn" href="find-your-nation.html">Finding your Nation</a></p></article>
<article><h3>I want to be around Native people near me</h3><p>Community centers, youth councils, recovery circles and tribal colleges.</p><p><a class="btn" href="community.html">Find community</a></p></article>
<article><h3>I know my Nation and need to reach it</h3><p>The phone number and website of the government office of every federally recognized Nation.</p><p><a class="btn" href="nations.html">Nations directory</a></p></article>
</div></section>
<section aria-labelledby="map-h"><h2 id="map-h">Where Nations have their governments</h2>
<p>Each dot is the government office of a federally recognized Nation, from the Bureau of Indian Affairs directory. Choose a state to see its Nations and the help listed there.</p>
<p class="picker"><label for="state-pick">Go to a state</label> <select id="state-pick" data-go>{state_options()}</select></p>
{map_svg()}
<details class="statebox"><summary>All states as a list</summary><ul class="statelist">{states}</ul></details>
<p class="meta">Office locations: <a href="{E(NATIONS_FILE['source_page'])}">Bureau of Indian Affairs Tribal Leaders Directory</a>, retrieved {nice_date(NATIONS_FILE['retrieved'])}. A dot shows where a government office is, not the extent of a Nation's homelands.</p></section>
<section class="panel" aria-labelledby="who-h"><h2 id="who-h">Who made this, and who it needs</h2>
<p>This guide was built by {E(SITE['maintainer'])} from what Nations, government agencies and Native organizations publish about themselves. It is not a tribal government and does not speak for any Nation. This first version covers the United States, with the most local detail for Ohio and Michigan. Canada and Mexico come next.</p>
<p>It needs Native people to look it over. If you work for a Nation, a tribal program or a Native organization, or you simply know something here is wrong or missing, <a href="mailto:{E(SITE['email'])}">write to us</a>. <a href="about.html">Read how the site is put together</a>.</p></section>'''
    page('index.html', f'{SITE["name"]}: help, Nations and community for First Peoples', SITE['description'], body)


def need_section(need, area='US', level=2, compact=False):
    """One kind of help with its listings. State pages use the compact form; the full form is on the help page."""
    cards = records_for(area, need['key'])
    also = [r for r in records_for(area, need['key'], primary_only=False) if r['need'] != need['key']]
    if not cards and not also:
        return ''
    h = f'h{level}'
    out = f'<section class="need" id="{need["key"]}" aria-labelledby="h-{need["key"]}"><{h} id="h-{need["key"]}">{E(need["label"])}</{h}>'
    if not compact:
        out += f'<p>{E(need["blurb"])}</p>{prep(need, level + 1)}'
    if cards:
        out += '<div class="cards">' + ''.join(card(r, level + 1) for r in cards) + '</div>'
    if also:
        out += '<p class="also">Also useful here: ' + ' · '.join(
            f'<a href="#r-{r["id"]}">{E(r["name"])}</a>' for r in also) + '</p>'
    return out + '</section>'


def build_help():
    chips = ''.join(f'<li><a href="#{n["key"]}">{E(n["short"])}</a></li>' for n in NEED_LIST if records_for('US', n['key']))
    labels = ''.join(f'<dt><span class="tag acc-{k}">{E(v["label"])}</span></dt><dd>{E(v["explain"])}</dd>' for k, v in ACCESS.items())
    sections = ''.join(need_section(n) for n in NEED_LIST)
    body = f'''<h1>Get help</h1>
<p class="lede">National help for Native people, sorted by what you need. For Nations, community groups and programs near you, <a href="states/index.html">choose your state</a>.</p>
{urgent()}
<nav class="chips" aria-label="Kinds of help"><ul>{chips}</ul></nav>
<p class="filter"><label for="who-filter">Show</label> <select id="who-filter" data-access-filter>
<option value="">Every listing</option>
<option value="anyone native descendants">Listings that do not ask for tribal enrollment</option>
<option value="anyone">Open to anyone</option>
<option value="enrolled ask">Listings for enrolled members, or where rules differ</option>
</select> <span id="filter-count" role="status"></span></p>
<details class="prep"><summary>What the labels on each listing mean</summary><dl class="labels">{labels}</dl></details>
{sections}
<section class="panel"><h2>Did we miss something?</h2><p>Tell us about a program that belongs here, or a listing that is wrong: <a href="mailto:{E(SITE['email'])}">{E(SITE['email'])}</a>.</p></section>'''
    page('help.html', f'Help for Native people: crisis lines, health, housing, school, legal | {SITE["name"]}',
         'National help for Native people by need: crisis and safety lines, Indian Health Service and urban Indian clinics, recovery, family and ICWA, scholarships, housing, food and money, work, legal help, elders and veterans.', body)


def national_links(up):
    """Short list of national help by need, for state pages."""
    out = '<ul class="natlinks">'
    for need in NEED_LIST:
        recs = records_for('US', need['key'])
        if not recs:
            continue
        links = ' · '.join(f'<a href="{up}help.html#r-{r["id"]}">{E(r["name"])}</a>' for r in recs)
        out += f'<li><strong><a href="{up}help.html#{need["key"]}">{E(need["label"])}</a>:</strong> {links}</li>'
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
    return (f'<section class="st" id="sr-{STATE_SLUG[code]}" aria-labelledby="hsr-{code}"><h{level} id="hsr-{code}">{head}</h{level}>'
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
    name = STATE_NAME[code]
    note = STATE_NOTES.get(code, {})
    parts = []
    if note.get('intro'):
        first, _, rest = note['intro'].partition('. ')
        parts.append(f'<p class="lede">{E(first)}.</p>' if rest else f'<p class="lede">{E(first)}</p>')
        if rest:
            parts.append(f'<p>{E(rest)}</p>')
        if note.get('intro_sources'):
            parts.append('<p class="meta">Sources: ' + ' · '.join(
                f'<a href="{E(s["url"])}">{E(s["label"])}</a>' for s in note['intro_sources'])
                + f'. Checked {nice_date(note["checked"])}.</p>')
    elif nations:
        parts.append(f'<p class="lede">Nations with their governments in {E(name)}, with the national help that works here too.</p>')
    else:
        parts.append(f'<p class="lede">The Bureau of Indian Affairs directory lists no federally recognized Nation with its government in {E(name)}. Native people live in every state, and the national help on this page works here.</p>')
    if not records:
        parts.append(f'<p>Local Native organizations, state programs and state-recognized Nations are not listed for {E(name)} yet. If you know one that belongs here, <a href="mailto:{E(SITE["email"])}">tell us</a>.</p>')
    return ''.join(parts)


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
        body = f'<p class="crumb"><a href="index.html">All states</a></p><h1>{E(name)}: Nations and help for Native people</h1>'
        body += state_intro(code, nations, records) + urgent(up)
        if nations:
            body += (f'<section aria-labelledby="nations-h"><h2 id="nations-h">Nations with their government in {E(name)}</h2>'
                     '<ul class="nations">' + ''.join(nation_item(n) for n in nations) + '</ul>'
                     f'<p class="meta">From the <a href="{E(NATIONS_FILE["source_page"])}">Bureau of Indian Affairs Tribal Leaders Directory</a>, retrieved {nice_date(NATIONS_FILE["retrieved"])}. '
                     'Names are shown as the Bureau lists them. Nations: tell us if you want a listing changed.</p></section>')
        body += state_nations_section(code)
        body += clinics_section(code)
        body += lands_section(code)
        if note.get('ties'):
            body += (f'<section aria-labelledby="ties-h"><h2 id="ties-h">{E(note["ties_title"])}</h2><p>{E(note["ties_intro"])}</p>'
                     '<ul class="nations">' + ''.join(nation_item(NATION[i], show_state=True) for i in note['ties']) + '</ul>'
                     f'<p class="meta">List of Nations: <a href="{E(note["ties_source"]["url"])}">{E(note["ties_source"]["label"])}</a>, checked {nice_date(note["checked"])}. '
                     f'Phone numbers and websites: Bureau of Indian Affairs directory, retrieved {nice_date(NATIONS_FILE["retrieved"])}.</p></section>')
        if records:
            body += f'<section aria-labelledby="local-h"><h2 id="local-h">Help and community in {E(name)}</h2>'
            body += ''.join(need_section(need, code, level=3, compact=True) for need in NEED_LIST) + '</section>'
        body += (f'<section aria-labelledby="nat-h"><h2 id="nat-h">Help that works in every state</h2>{national_links(up)}</section>'
                 f'<section class="panel"><h2>Know something that belongs on this page?</h2><p>A Nation, a community group, a clinic, a program: write to <a href="mailto:{E(SITE["email"])}">{E(SITE["email"])}</a>.</p></section>')
        if nations:
            description = f'Federally recognized Nations with their governments in {name}, with phone numbers and websites, plus help for Native people in {name}: crisis lines, health care, school, housing, legal help and community.'
        else:
            description = f'Help for Native people living in {name}: crisis lines, health care, recovery, school, housing, legal help and how to reach your Nation.'
        page(f'states/{STATE_SLUG[code]}.html', f'{name}: Native resources and tribal Nations | {SITE["name"]}', description, body)
        count = f' <span class="count">{len(nations)} government office{"s" if len(nations) != 1 else ""}</span>' if nations else ''
        local = ' <span class="count">local listings</span>' if records else ''
        index_items += f'<li><a href="{STATE_SLUG[code]}.html">{E(name)}</a>{count}{local}</li>'
    body = f'''<h1>Find help by state</h1>
<p class="lede">Every state has a page with the Nations whose governments are there and the national help that works anywhere. Ohio and Michigan also list community groups and state programs, and 21 more states list their urban Indian health programs. More is being filled in.</p>
<p class="picker"><label for="state-pick">Go to a state</label> <select id="state-pick" data-go>{state_options("../")}</select></p>
<ul class="statelist big">{index_items}</ul>'''
    page('states/index.html', f'Native resources by state | {SITE["name"]}',
         'Choose a state to see the federally recognized Nations with governments there, and help for Native people who live there.', body)


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
    body = f'''<h1>Nations directory</h1>
<p class="lede">The government office of every federally recognized Nation in the United States, by state, with a phone number and website where the directory has one.</p>
<p>This list is built from the <a href="{E(NATIONS_FILE['source_page'])}">Bureau of Indian Affairs Tribal Leaders Directory</a>, retrieved {nice_date(NATIONS_FILE['retrieved'])}. The Bureau counts 575 federally recognized tribes as of January 30, 2026, and lists some bands and communities separately. It says the directory is not the official list (that is the notice it publishes in the Federal Register) and may contain errors. A Nation is listed under the state where its government office is; its homelands and citizens may reach far beyond that state.</p>
<p>Names appear as the Bureau lists them. Nations recognized by a state and not on the federal list are in <a href="#state-recognized">their own section below</a>, added one state at a time from the official list of each state. Nations with neither kind of recognition are not listed yet; write to us to be added. If you speak for a Nation and want its listing changed, write to <a href="mailto:{E(SITE['email'])}">{E(SITE['email'])}</a>.</p>
<p class="search"><label for="q">Search by name, town or state</label> <input id="q" type="search" autocomplete="off" data-nation-search> <span id="q-count" role="status"></span></p>
<nav class="chips" aria-label="States with Nations listed"><ul>{chips}</ul></nav>
{sections}
{state_recognized}'''
    page('nations.html', f'Directory of federally recognized tribal Nations by state | {SITE["name"]}',
         'Phone numbers and websites for the government office of every federally recognized tribal Nation in the United States, listed by state, from the Bureau of Indian Affairs directory.', body)


def build_find():
    mail = E(SITE['email'])
    body = f'''<h1>Finding your Nation</h1>
<p class="lede">If you grew up away from your Nation, or you are not sure which Nation your family comes from, this page explains how to trace your family and how enrollment works.</p>
<p>Enrollment is a legal status that each Nation decides for itself. Finding community is a separate thing, and you can start on both at once: see <a href="community.html">Finding community</a>.</p>

<section aria-labelledby="f1"><h2 id="f1">What enrollment is</h2>
<p>Each tribe sets its own rules for who can be a member, and only the tribe can enroll you. The Department of the Interior says two rules are common: descending directly from someone named on the tribe's base roll, or being related to a member who does. Some tribes also look at blood quantum, where you live, or whether your family has stayed in contact with the tribe.</p>
<p>The Bureau of Indian Affairs (BIA) does not keep a list of enrolled members and does not do family research for people. Each tribe keeps its own records. The BIA also says the rules for federal services differ from program to program, so being a descendant, being enrolled and being eligible for a given program are three different questions. The labels on our <a href="help.html">help listings</a> say which one each program asks about.</p>
<p class="meta">Sources: <a href="https://www.doi.gov/tribes/enrollment">Department of the Interior, Tribal Enrollment Process</a> · <a href="https://www.bia.gov/guide/tracing-american-indian-and-alaska-native-aian-ancestry">BIA, Tracing American Indian and Alaska Native Ancestry</a> · <a href="https://www.bia.gov/frequently-asked-questions">BIA, Frequently Asked Questions</a>. Checked November 17, 2026.</p></section>

<section aria-labelledby="f2"><h2 id="f2">Tracing your family, step by step</h2>
<ol class="steps">
<li><strong>Write down what your family knows.</strong> Names, birth dates and birthplaces of parents, grandparents and great-grandparents, and any papers kept at home. Note who told you which Nation the family comes from.</li>
<li><strong>Work out which Nation your ancestor belonged to.</strong> You will be dealing with that tribe's government, so this is the question everything else depends on.</li>
<li><strong>Build the paper trail.</strong> The BIA says you need to show your link to an ancestor with records the tribe accepts. Birth and death certificates come from the vital records office of the state where the person was born or died. The BIA also points to the National Archives (federal census records, including the Bureau's own censuses, the Dawes Rolls and military records), county courthouses, and town, school and church records, newspapers, libraries and historical societies.</li>
<li><strong>Contact the tribe's enrollment office.</strong> Ask for its membership rules and the papers it accepts. Our <a href="nations.html">Nations directory</a> has a phone number and website for each government office.</li>
<li><strong>Apply to the tribe</strong> if you meet its rules. The tribe decides.</li>
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
<p>Our directory comes from the federal list, so Nations recognized only by a state, and Nations still seeking recognition, are not in it yet. Some help does not depend on federal recognition: the American Indian College Fund, for example, accepts members and descendants of state-recognized tribes. On the <a href="help.html">help page</a> you can show only the listings that do not ask for tribal enrollment.</p></section>

<section class="panel"><h2>Something here wrong, or missing?</h2><p>If you work in tribal enrollment, or you have walked this road yourself and see a step we got wrong, write to <a href="mailto:{mail}">{mail}</a>.</p></section>'''
    page('find-your-nation.html', f'Finding your Nation: tracing Native ancestry and tribal enrollment | {SITE["name"]}',
         'How to work out which Nation your family comes from, how tribal enrollment works, what a CDIB card and DNA tests can and cannot do, and who can help if you were adopted or in foster care.', body)


def build_community():
    local = ''
    for code, name in STATES:
        recs = [r for r in RES if r['area'] == code and (r['need'] == 'community' or 'community' in r.get('also', []))]
        if not recs:
            continue
        local += (f'<section aria-labelledby="c-{code}"><h3 id="c-{code}"><a href="states/{STATE_SLUG[code]}.html">{E(name)}</a></h3>'
                  '<div class="cards">' + ''.join(card(r, 4) for r in recs) + '</div></section>')
    anywhere = [r for r in RES if r['area'] == 'US' and (r['need'] == 'community' or 'community' in r.get('also', []))]
    body = f'''<h1>Finding community</h1>
<p class="lede">Places and groups where Native people gather: community centers, youth councils, recovery circles and tribal colleges.</p>
<p>Local listings so far cover Ohio and Michigan. The national groups further down work from anywhere, and every state page lists the Nations whose governments are there.</p>
<section aria-labelledby="c-local"><h2 id="c-local">Community centers and groups, by state</h2>{local}
<p>In another state? Start with the <a href="help.html#r-urban-indian-health">map of Urban Indian Organizations</a>, whose services can include youth, elder and community programs, or <a href="states/index.html">open your state's page</a>.</p></section>
<section aria-labelledby="c-any"><h2 id="c-any">From anywhere</h2><div class="cards">{''.join(card(r, 3) for r in anywhere)}</div></section>
<section aria-labelledby="c-nation"><h2 id="c-nation">Your own Nation</h2>
<p>If you know which Nation you come from, call its government office and ask what gatherings, classes or events are coming up, and whether descendants are welcome. The <a href="nations.html">Nations directory</a> has the numbers. If you are not sure which Nation, start with <a href="find-your-nation.html">Finding your Nation</a>.</p></section>
<section class="panel"><h2>Run a Native community group?</h2><p>We would like to list it, the way you want it described. Write to <a href="mailto:{E(SITE['email'])}">{E(SITE['email'])}</a>.</p></section>'''
    page('community.html', f'Native community centers, youth councils and recovery circles | {SITE["name"]}',
         'Find Native community: urban Indian centers and Native organizations in Ohio and Michigan, national youth councils, Wellbriety recovery circles and tribal colleges.', body)


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
<p>This first version covers the United States: national help by need, the government office of every federally recognized Nation, and a page for every state. Ohio and Michigan also list community groups and state programs. More states are being filled in. Help for First Nations, Inuit and Métis people in Canada and for Indigenous peoples in Mexico comes next.</p>
<p>Not here yet: Nations recognized only by a state, Nations still seeking recognition, and most local organizations outside Ohio and Michigan.</p></section>

<section aria-labelledby="a3"><h2 id="a3">Where the listings come from</h2>
<ul>
<li><strong>Nations:</strong> the <a href="{E(NATIONS_FILE['source_page'])}">Bureau of Indian Affairs Tribal Leaders Directory</a>, retrieved {nice_date(NATIONS_FILE['retrieved'])}. We keep the name, town, state, phone number, website and map position of each government office. We leave out the names of elected leaders, which change with every election. The Bureau says the directory is not the official list of federally recognized tribes and may contain errors.</li>
<li><strong>Programs and organizations:</strong> each one's own website, or a page from a government agency that lists it. Every listing shows the date it was checked and links to the page it came from.</li>
<li><strong>Map shapes:</strong> U.S. Census Bureau state outlines.</li>
</ul>
<p>Listings are read from published sources. When something is wrong or out of date, <a href="mailto:{mail}">tell us</a> and it will be fixed.</p></section>

<section aria-labelledby="a4"><h2 id="a4">What the labels mean</h2>
<p>Programs differ on who they serve. Some are open to anyone, some serve descendants, and some ask for proof of enrollment in a federally recognized tribe. Each listing carries one of these labels, taken from what the program itself says:</p>
<dl class="labels">{labels}</dl></section>

<section aria-labelledby="a5"><h2 id="a5">For Nations and organizations</h2>
<p>You decide how you are described. Names appear as the Bureau of Indian Affairs or the organization itself writes them. If you want a name, a description or a contact changed, or a listing removed, write to <a href="mailto:{mail}">{mail}</a>.</p>
<p>This site does not publish ceremonial knowledge, the locations of sacred places, or anything else a Nation has not chosen to make public.</p></section>

<section aria-labelledby="a6"><h2 id="a6">Your privacy and safety</h2>
<p>There are no accounts and no forms, and the site stores nothing about you. One counter (GoatCounter) counts page views without cookies. Phone and text links open your own phone's apps.</p>
<p>The "Leave this site now" bar at the top of every page takes you to a weather page. It cannot clear your browser history. If someone checks your phone or computer, use a private browsing window, or a device they cannot get to.</p></section>

<section aria-labelledby="a7"><h2 id="a7">Limits</h2>
<p>This is general information, not legal, medical or financial advice. It does not decide who qualifies for a program; the program does. Phone numbers and rules change, so confirm details with the program before you rely on them.</p></section>

<section aria-labelledby="a8"><h2 id="a8">Reuse</h2>
<p>The site's data and code are public at <a href="{E(SITE['repo'])}">{E(SITE['repo'].replace('https://', ''))}</a>. The compiled data is licensed CC BY 4.0 and the code under the MIT License. Tribal programs and Native organizations are welcome to copy, adapt and republish it.</p></section>'''
    page('about.html', f'About {SITE["name"]}: who made it and where the listings come from',
         'Who built this guide for Native people, where its listings come from, what the labels mean, how Nations and organizations can correct or remove a listing, and how your privacy is handled.', body)


def build_404():
    base = E(SITE['base_url'])
    body = f'''<h1>That page is not here</h1>
<p class="lede">The link may be old, or the address may have a typo.</p>
<ul><li><a href="{base}">Home</a></li><li><a href="{base}help.html">Get help</a></li><li><a href="{base}nations.html">Nations directory</a></li><li><a href="{base}states/index.html">Find help by state</a></li></ul>
<p>In a crisis, <a href="tel:988">call</a> or <a href="sms:988">text 988</a>.</p>'''
    # 404 pages are served from any depth, so every link in the page chrome must be absolute.
    page('404.html', f'Page not found | {SITE["name"]}', 'That page is not here.', body)
    path = ROOT / '404.html'
    text = path.read_text(encoding='utf-8')
    for target in ['assets/', 'index.html', 'about.html'] + [href for href, _ in NAV]:
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


def build_works():
    body = ('<h1>What has worked</h1><p class="lede">Programs with published results behind them, for Native families, clinics and tribal governments.</p>'
            '<p>This page lists only programs whose results were measured and published by the agency or university named in each entry. It is short on purpose and will grow one sourced entry at a time. '
            f'If you know a program with results to show, <a href="mailto:{E(SITE["email"])}">tell us</a>.</p>')
    for i, w in enumerate(WORKS):
        body += (f'<section aria-labelledby="w{i}"><h2 id="w{i}">{E(w["title"])}</h2><p>{E(w["what"])}</p>'
                 '<h3>What the results show</h3><ul>' + ''.join(f'<li>{E(r)}</li>' for r in w['results']) + '</ul>'
                 f'<p><strong>How to use this:</strong> {E(w["use"])}</p>'
                 '<p class="meta">Sources: ' + ' · '.join(f'<a href="{E(u)}">{E(l)}</a>' for l, u in w['sources'])
                 + f'. Checked {nice_date(WORKS_CHECKED)}.</p></section>')
    page('what-works.html', f'Programs that have worked in Native communities, with their results | {SITE["name"]}',
         'Programs with measured, published results in Native communities: tribal diabetes programs, home visiting for young families, and Nations running their own services.', body)


def build_sitemap():
    dates = [r['checked'] for r in RES] + [NATIONS_FILE['retrieved']]
    lastmod = max(dates)
    urls = ''.join(
        f'<url><loc>{E(SITE["base_url"] + ("" if p == "index.html" else p))}</loc><lastmod>{lastmod}</lastmod></url>\n'
        for p in PAGES)
    (ROOT / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + '</urlset>\n',
        encoding='utf-8')
    (ROOT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {SITE["base_url"]}sitemap.xml\n', encoding='utf-8')


def main():
    check_data()
    build_home()
    build_help()
    build_nations()
    build_states()
    build_find()
    build_community()
    build_works()
    build_about()
    build_404()
    build_sitemap()
    print(f'{len(PAGES)} pages, {len(RES)} listings, {len(NATIONS)} Nation offices')


if __name__ == '__main__':
    main()
