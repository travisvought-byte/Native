# Coverage report

As of 2026-11-23 (the newest check date in the data). Regenerate with `python3 scripts/mine.py report`; do not edit by hand.

170 hand-checked listings, 602 federally recognized Nation offices, 48 state-recognized Nations, 1143 clinics and 33 tribal colleges. Listing evidence: 95 from a government page, 59 from the organization's own site, 16 from another site (some are foreign government sites the check cannot tell apart; re-read these first).

## Datasets

| Layer | Retrieved | Due | Refresh |
| --- | --- | --- | --- |
| Nation offices (BIA) | 2026-11-17 | 2027-02-15 | `python3 scripts/import_bia.py` |
| Clinics (IHS) | 2026-11-20 | 2027-02-18 | `python3 scripts/import_clinics.py` |
| Tribal colleges (BIA) | 2026-11-20 | 2027-02-18 | `python3 scripts/import_colleges.py` |
| Tribal lands (Census) | 2026-11-20 | 2027-02-18 | `npm run lands && python3 scripts/import_lands.py` |
| Canada communities (ISC) | 2026-11-20 | 2027-02-18 | `python3 scripts/import_canada.py` |

## States, thinnest first

Work down this table. "Local" is hand-checked listings on the state page; "Offices" adds Nation offices, state-recognized Nations and clinics from the datasets. "State office" is whether the state's Indian affairs office and recognition list have been read (pipeline/state-offices.json).

| State | Local | Offices | State office | Needs with no local listing |
| --- | --- | --- | --- | --- |
| Arkansas | 0 | 0 | todo | all |
| District of Columbia | 0 | 0 | todo | all |
| Pennsylvania | 0 | 0 | todo | all |
| Tennessee | 0 | 0 | todo | all |
| West Virginia | 0 | 0 | todo | all |
| Delaware | 0 | 2 | published | all |
| Iowa | 0 | 2 | todo | all |
| Rhode Island | 0 | 3 | todo | all |
| Vermont | 0 | 4 | published | all |
| Connecticut | 0 | 6 | published | all |
| Florida | 0 | 7 | todo | all |
| Mississippi | 0 | 10 | todo | all |
| Alabama | 0 | 11 | published | all |
| Wyoming | 0 | 11 | todo | all |
| Maine | 0 | 12 | todo | all |
| Idaho | 0 | 13 | todo | all |
| Virginia | 0 | 18 | published | all |
| Louisiana | 0 | 21 | published | all |
| North Carolina | 0 | 24 | published | all |
| Georgia | 1 | 0 | published | safety, health, recovery, family, school, housing, money, work, legal, elders, veterans |
| Indiana | 1 | 0 | published | safety, health, recovery, family, school, housing, money, work, legal, elders, veterans |
| Kentucky | 1 | 0 | published | safety, health, recovery, family, school, housing, money, work, legal, nation, elders, veterans |
| New Hampshire | 1 | 0 | published | safety, health, recovery, family, school, housing, money, work, legal, nation, elders, veterans |
| New Jersey | 1 | 0 | published | safety, health, recovery, family, school, housing, money, work, legal, elders, veterans |
| Maryland | 1 | 1 | todo | safety, recovery, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Missouri | 1 | 1 | todo | safety, health, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Illinois | 1 | 2 | todo | safety, recovery, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Colorado | 1 | 6 | todo | safety, recovery, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Texas | 1 | 8 | todo | safety, recovery, family, school, housing, money, work, legal, nation, elders, veterans, community |
| South Carolina | 1 | 12 | published | safety, health, recovery, family, school, housing, money, work, legal, elders, veterans |
| Kansas | 1 | 13 | todo | safety, recovery, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Nebraska | 1 | 14 | todo | safety, family, school, housing, money, work, legal, nation, elders, veterans, community |
| North Dakota | 1 | 17 | published | safety, health, recovery, family, school, housing, money, work, legal, elders, veterans, community |
| New York | 1 | 18 | todo | safety, recovery, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Utah | 1 | 32 | todo | safety, recovery, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Oregon | 1 | 37 | todo | safety, family, school, housing, money, work, legal, nation, elders, veterans, community |
| South Dakota | 1 | 39 | todo | safety, recovery, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Nevada | 1 | 50 | todo | safety, recovery, family, school, housing, money, work, legal, nation, elders, veterans, community |
| New Mexico | 1 | 69 | todo | safety, recovery, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Massachusetts | 2 | 5 | published | safety, recovery, family, housing, money, work, legal, elders, veterans, community |
| Wisconsin | 2 | 38 | todo | safety, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Minnesota | 2 | 51 | todo | safety, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Washington | 2 | 97 | todo | safety, recovery, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Oklahoma | 2 | 124 | todo | safety, recovery, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Hawaii | 3 | 0 | todo | safety, work, legal, elders, veterans, community |
| Arizona | 4 | 123 | todo | safety, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Montana | 5 | 48 | todo | safety, recovery, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Alaska | 5 | 558 | todo | housing, nation, elders, veterans, community |
| Ohio | 8 | 0 | todo | safety, health, housing, money, legal, nation, elders, veterans |
| California | 9 | 249 | todo | safety, family, school, housing, money, work, legal, nation, elders, veterans, community |
| Michigan | 12 | 37 | todo | housing, money, elders, veterans |

## Listings due for a fresh read (180 days)

None.

## Queue: found but not published

- **LA: Grand Caillou/Dulac Band of Biloxi Chitimacha Choctaw, Jean Charles Choctaw Nation, Natchitoches Tribe of Louisiana: websites** (tried 2026-11-23). The state's links to these tribes' sites are broken relative links. Next: Confirm each tribe's own site, then add url in data/state-nations.json.
- **LA: Governor's Office of Indian Affairs (listing)** (tried 2026-11-23). Office description and contact not read. Next: Read the office page and add a listing to data/resources/la.json.
- **GA: Georgia state-recognized tribes** (tried 2026-11-23). The page does not clearly say which groups the General Assembly recognized. Next: Find the General Assembly resolutions or the council's own recognized list.
- **NJ: New Jersey state-recognized tribes** (tried 2026-11-23). The commission page names tribes as seats, not as recognized. Next: Find the state's own recognition statement (Attorney General settlement releases, 2018-2019) and publish as the state names them.
- **SC: South Carolina Indian groups and special interest organizations** (tried 2026-11-23). The state lists these separately from tribes; each needs its own page read for what it offers. Next: Read each group's own site and add community listings to data/resources/sc.json where they offer help.
- **US: Federal rosters not reachable from the build machine** (tried 2026-11-23). The cloud build machine has no direct internet; rosters were not pulled in this run. Next: Read each roster page (browser or a machine with internet), one state at a time, thinnest states first per pipeline/COVERAGE.md.
- **CT: Connecticut General Statutes chapter 824 (tribes the statute names)** (tried 2026-11-23). The legislature's site did not answer. The state list published comes from DEEP Tribal Affairs instead. Next: Read chapter 824 and confirm the names match the DEEP page.
