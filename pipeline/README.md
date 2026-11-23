# How Nina's Map finds and checks its listings

This folder is the sourcing pipeline: where the site's information comes from, what has been read, what is waiting, and which states are thinnest. It follows the same rule as the rest of the site: every published fact can be traced to a named page, read on a recorded date.

## Files

| File | What it is |
| --- | --- |
| `sources.json` | The source registry: every place the site reads from, who publishes it, how it is read (`dataset`, `roster` or `per-listing`), its evidence level and how often to re-read it. |
| `state-offices.json` | For each state: its Indian affairs office and its own list of state-recognized Nations, the page each was read from and the date, and whether it is `published`, `queued` or `todo`. |
| `queue.json` | Leads and blocked reads that are not on the site yet, each with what is missing and the next step. |
| `COVERAGE.md` | Generated. Dataset ages, every state ranked thinnest first, listings due for a fresh read, and the queue. |
| `../data/export/listings.csv` | Generated. Every published place in one normalized table: layer, area, id, name, city, kind, access, phone, url, source, publisher, checked, evidence. |

## Evidence levels

- **official**: a government page, or a Nation publishing about itself. Rosters (Indian Health Service, Bureau of Indian Affairs, a state's own recognition list) are official.
- **first-party**: the organization's own website.
- **lead**: a directory, news story, search result, social post or AI answer. A lead tells you where to look. It is never the `source` of a published listing.

`mine.py check` labels each listing from its `source` address. A listing whose source is neither a government site nor the organization's own site is printed as a note so it can be re-read against a better source first.

## A run, from a cold start

Needs Python 3. Reading the web needs a machine or browser with internet (the cloud build machine has none, so rosters there are read with a browser).

1. **Look at the gaps.** `python3 scripts/mine.py report`, then open `COVERAGE.md`. Start at the top of "States, thinnest first".
2. **Refresh the datasets when due.** `python3 scripts/mine.py refresh` re-runs every `dataset` import in `sources.json` (Nation offices, clinics, colleges, lands, Canada). If one fails, keep the old file and add the attempt to `queue.json`.
3. **Work the rosters for the thinnest state.** In this order, each read from the publisher's own page:
   1. the state's Indian affairs office and its own list of recognized Nations (`state-offices.json`, then `data/state-nations.json`);
   2. urban Indian organizations (IHS roster) and Native community centers;
   3. housing, legal aid, work, elders and veterans programs from the federal rosters in `sources.json`;
   4. Native-led nonprofits, each from its own site.
4. **Write the listing** in `data/resources/<state>.json` using the format in the top-level README. Write in plain words of your own; keep only what the page says; no staff names, personal phones or personal emails; nothing about ceremonies or sacred places. Use each Nation's name exactly as the Nation or the state publishes it.
5. **Anything you could not confirm** goes in `queue.json` with the date tried. A blocked page, a bot check or a broken link is an attempt, not a check: never give a listing a fresh `checked` date from it, and do not work around the block.
6. **Check and rebuild.**

   ```
   python3 scripts/mine.py check     # duplicates, missing fields, evidence; must say 0 problems
   python3 scripts/build.py
   python3 scripts/mine.py report
   python3 tests/test_site.py
   ```

7. **Re-reads.** "Listings due for a fresh read" in `COVERAGE.md` lists every listing older than 180 days. Re-read the source; if nothing changed, update `checked`; if the program closed, remove the listing and say so in the commit message.

## Duplicates

`mine.py check` stops on two listings with the same name in one state, and on a state-recognized Nation listed twice. It notes (without stopping) a shared phone number in one state and a listing with the same name as a Nation office, clinic or college already on the page; urban Indian organizations are often both, on purpose, because the listing explains how to start.

## Suggested rhythm

- Every week: one pass down the thinnest states (step 3), about five states a pass.
- Every month: work the queue and the listings due for a re-read.
- Every quarter: `refresh` the datasets.
