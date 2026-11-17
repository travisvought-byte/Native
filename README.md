# Native Resource Map

A free guide for Native people looking for help, for their Nation, or for community.

**Dedicated to Nina, and hers to share.** Built and maintained by Travis Vought. Corrections: travis@vethomeguard.org.

Live site: https://travisvought-byte.github.io/Native/ (once GitHub Pages is turned on for this repository).

This first version covers the United States, with the most local detail for Ohio and Michigan. Canada and Mexico come next.

## What is on the site

- `index.html`: urgent help lines, a grid of thirteen kinds of help, three ways to start, and a map of where Nations have their government offices. Every state on the map links to its page.
- `help.html`: national help by need (crisis and safety, health care, recovery, family, school, housing, food and money, work, legal help, enrollment, elders, veterans, community). Each listing says who can use it, how to start, when it was checked and where it came from. A filter shows only listings that do not ask for tribal enrollment.
- `nations.html`: the government office of every federally recognized Nation, by state, with search.
- `states/`: a page for every state and D.C. with the Nations whose governments are there, local listings where we have them (Ohio and Michigan so far), and links to national help. The Ohio page also lists Nations with ties to Ohio whose governments are now elsewhere.
- `find-your-nation.html`: tracing your family, how enrollment works, CDIB cards, DNA tests, and help for people who were adopted or in foster care.
- `community.html`: Native community centers and groups, youth councils, recovery circles and tribal colleges.
- `about.html`: who made it, sources, labels, privacy, and how a Nation or organization can correct or remove a listing.

## Build and test

Needs only Python 3.

```
python3 scripts/build.py     # rebuilds every page from data/
python3 tests/test_site.py   # checks the pages against the data
```

Edit the files in `data/`, never the built pages. The workflow in `.github/workflows/validate.yml` runs both commands on every push and fails if a built page is out of date.

## The data

| File | What it holds |
| --- | --- |
| `data/site.json` | Site name, address, contact, dedication, visit counter. |
| `data/needs.json` | The kinds of help, the "before you call" reminders, and the labels for who can use a listing. |
| `data/resources/us.json` | National listings. |
| `data/resources/<state>.json` | Listings for one state, for example `mi.json`. Add a file to start a new state. |
| `data/states.json` | A short introduction for a state, with sources, and for Ohio the Nations with ties to the state. |
| `data/nations.json` | Nation government offices, from the Bureau of Indian Affairs Tribal Leaders Directory. Do not edit by hand. |
| `data/map/us.json` | State outlines and the map position of each office. Do not edit by hand. |

### Adding a listing

```json
{"id": "short-unique-id", "name": "Name as the organization writes it", "place": "City (optional)",
 "need": "health", "also": ["recovery"], "access": "native",
 "what": "What it is, in one or two plain sentences.",
 "who": "Who it serves, as the source says.",
 "start": "The first step a person should take.",
 "phone": "313-555-0100", "phone_note": "optional", "email": "optional", "address": "optional",
 "url": "https://...", "url_label": "optional",
 "source": "https://the page these facts were read from", "checked": "2026-11-17"}
```

`access` is one of `anyone`, `native`, `descendants`, `enrolled` or `ask`. Use what the program itself says. When it is not clear, use `ask`.

Rules for listings:

1. Read it from the organization's own page or a government page, and put that page in `source`.
2. Write it in your own plain words. Leave out anything you cannot find in the source.
3. No names of individual staff, no personal phone numbers or emails.
4. Nothing about ceremonies, sacred places, or anything a Nation has not chosen to publish.
5. If a Nation or organization asks for a change or a removal, make it.

### Refreshing the Nations directory

```
python3 scripts/import_bia.py   # downloads the Bureau's open dataset and rewrites data/nations.json
npm install && npm run map      # redraws data/map/us.json (needs Node; only for this step)
python3 scripts/build.py && python3 tests/test_site.py
```

The import keeps each office's name, town, state, phone, website and map position. It leaves out the names of elected leaders, fax numbers, email addresses and the Bureau's internal notes.

## Moving to a domain

Change `base_url` in `data/site.json`, add a `CNAME` file with the domain, run the build, and set the custom domain in the repository's Pages settings.

## What comes next

- State-recognized Nations and Nations seeking recognition.
- Local listings for the states around Ohio and Michigan, then the rest.
- Urban Indian Organizations and Indian Health Service clinics on the map.
- Canada (First Nations, Inuit, Métis) and Mexico.
- Review by Native people. The site asks for it on every page.

## License

Listing data CC BY 4.0, code MIT. The Nations data is from the Bureau of Indian Affairs and the map shapes from us-atlas. See `LICENSE`.
