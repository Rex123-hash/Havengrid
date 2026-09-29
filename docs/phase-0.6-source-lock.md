# Phase 0.6 — Source Lock & Operational Separation

Research and architecture only. No adapters, kernel changes, UI changes or Google/AI integrations were made.
UI baseline remains commit `8f9e79c`. Date of research: 2026-09-12.

Access verdicts are what was actually established from this workstation on that date; several
Odisha government hosts (`osmcl.nic.in`, `dhsodisha.nic.in`, `sundargarh.odisha.gov.in`,
`sundergarh.nic.in`, `nhp.gov.in`) were unreachable, and `data.gov.in` returned 500/502/504
from its backend API. Those are recorded as *not verified this session*, not as unavailable.

---

## 1. Executive conclusion

1. **No public source anywhere exposes facility-level medicine stock, batch or expiry for
   Odisha.** e-Niramaya / DVDMS is login-gated (username + password + CAPTCHA); the CAG itself
   records that e-Niramaya data for 2016-19 "was not made available to Audit". Inventory, batch
   and expiry therefore come from exactly two honest places: an **authorised operational export**
   (Option A) or **user-supplied evidence** captured through the Reality Lens (Option B).
   There is no third route, and none must be invented.

2. **The public data that does exist is service activity, not supply.** HMIS Standard Reports
   are downloadable without login down to **sub-district (block) month** — not facility — and
   the newest public item-wise zips observed are FY 2021-22 (provisional). This supports an
   **ESTIMATED / MODEL_DERIVED** Care Blast Radius only, never a DIRECT one.

3. **The 14-node Sundargarh graph is not geographically honest.** Three nodes are in other
   districts (Kuchinda → Sambalpur, Remed → Sambalpur, Tileibani → Deogarh); four "PHCs" are
   actually block-headquarter CHCs (Kutra, Koira, Bargaon, Lahunipada); Bonai is a
   Sub-Divisional Hospital; Bhatpar, Talsara, Kansbahal and Nuagaon could not be verified as
   public facilities of that type. A replacement set drawn from official Sundargarh records
   preserves the visual topology (1 warehouse → 4 hubs → 9 leaves) without falsifying geography.

4. **Amoxicillin 125 mg/5 ml oral suspension cannot honestly carry the judge-facing story.**
   Odisha STG 2018 doses it by body weight (80–90 mg/kg/day for pneumonia; 40 mg/kg/day for
   otitis). No authoritative record turns "an attendance" into "a bottle". National child
   pneumonia guidance has moved to amoxicillin dispersible tablets. It survives only as an
   ESTIMATED item with a wide interval.

5. **Recommended target: Iron + Folic Acid (60 mg elemental iron + 500 µg folic acid, "red IFA")
   for pregnant women.** It is the one commodity where a *published national policy* fixes the
   quantity per obligation (180 tablets per pregnancy, one per day from the second trimester),
   the obligation is a *scheduled* service (ANC visits / VHND), the public data exists (HMIS ANC
   registrations and "PW given 180 IFA"; Anemia Mukt Bharat dashboard), stock-outs are
   documented in Odisha's own assessments, it is dispensed at every tier down to sub-centre,
   needs no cold chain, and generalises across BRICS. Care consequence is truthful and
   non-sensational: *antenatal supplementation interrupted*.

6. **GO** for a first, read-only, OFFICIAL_PUBLIC_DATA adapter limited to (a) the official
   facility roster and (b) HMIS sub-district service activity, both **conditional** on one
   verification step (downloading and inspecting the actual HMIS zip headers, which timed out
   from this network). **NO-GO** for any inventory / batch / expiry adapter until either an
   authorised export is in hand or the Reality Lens evidence path is the declared source.

---

## 2. Source reliability hierarchy

Highest to lowest. A lower tier may *discover* a fact; only the tier named as final may *assert* it.

| Tier | Class | Examples found | May assert |
|---|---|---|---|
| 1 | Authorised operational system export (`OFFICIAL_SYSTEM_EXPORT`) | e-Niramaya/DVDMS facility stock & batch export; Ni-kshay Aushadhi; eVIN/U-WIN; RCH portal EDD lists | stock, batch, expiry, indents, dispensing, per-obligation demand |
| 2 | Official published dataset / report (`OFFICIAL_PUBLIC_DATA`) | HMIS Standard Reports (hmis.mohfw.gov.in); data.gov.in HMIS catalogues; AMB dashboard; Odisha STG 2018; DH&FW procurement guideline 2015; CAG 2024 Ch.4; ZSS Sundargarh FDS plan 2013-14; LGD | facility identity/type/block, aggregate service counts, policy norms, dosing rules |
| 3 | Live third-party API (`LIVE_EXTERNAL_API`) | Google Routes; Google Geocoding; IMD | route distance/time, coordinates when official ones are missing (labelled) |
| 4 | Human observation (`USER_SUPPLIED_EVIDENCE`) | Reality Lens photo/count, confirmation, dispatch/receipt counts | current stock at a facility at a moment, batch ids seen, receipt |
| 5 | Kernel computation (`MODEL_DERIVED`) | forecasts, CBR, candidates, monthly demand from annual policy | nothing observational — only derivations, with lineage |
| — | Secondary / discovery only | Wikipedia, Medindia, ESI.in, e-DantSeva listings, PIN-code sites, scribd copies | nothing; used to locate an official source |

Rule applied throughout: **a field exists only when a document or endpoint was seen to contain it.**

---

## 3. Authoritative source matrix

Legend — Access: PUB = public, no login; AUTH = credentials required; CAPTCHA = human-only public search.
Verdict: APPROVED · CONDITIONAL · ACCESS_NOT_ESTABLISHED · UNSUITABLE.

### 3.1 Facility roster, type/tier, geography (families 1–3)

| Source | Owner | URL | Access | Granularity | Fields seen | Missing for HAVEN | Freshness | Origin | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| HMIS Standard Reports → *Facility Master Report* (listed in portal menu) | MoHFW / NHM | https://hmis.mohfw.gov.in/#!/standardReports | Listed under real-time reports; menu visible without login, content not opened this session | facility | (menu only) | coordinates, HFR id | continuous | OFFICIAL_PUBLIC_DATA | CONDITIONAL — verify it opens without login |
| ZSS Sundargarh, *Fixed Day Static Service Delivery Sub-Plan 2013-14* | Zilla Swasthya Samiti, Sundargarh (DH&FW Odisha) | https://health.odisha.gov.in/sites/default/files/2020-02/Sundargarh_0.pdf | PUB (PDF) | facility | institution name, category (CHC/PHC-N/SDH/DHH/SC), level, block population; district counts: 2 DH, 19 CHC, 57 PHC(N), 390 SC | coordinates, ids, current status (2013 vintage) | static, 2013 | OFFICIAL_PUBLIC_DATA | APPROVED for name/type verification; CONDITIONAL for *current* tier |
| DH&FW Odisha homoeopathic dispensary list (Sundargarh) | DH&FW Odisha / Dir. of Indian Medicines | https://health.odisha.gov.in/sites/default/files/2020-03/sundergarh.pdf | PUB (PDF) | GP / block | official block spellings (Balisankara, Hemagiri, Kutra, Lefripada, Tangarpali, Baragaon, Rajagangapur, Laphripada, Bonaigarh, Gurundia, Bisra, Nuagaon, Lathikata, Kuarmunda, Panposh) | not an allopathic facility list | static | OFFICIAL_PUBLIC_DATA | APPROVED for block names only |
| IFC/GoO *Technical due diligence — Sundargarh* (2022 upload) | DH&FW Odisha | https://health.odisha.gov.in/sites/default/files/2022-10/Sundargarh.pdf | PUB (PDF) | district | 113 govt facilities, 34 private hospitals, CHC ≈ 50 % of govt OPD, avg OPD/CHC/day 88 (FY 2015-16) | facility list | static | OFFICIAL_PUBLIC_DATA | APPROVED as context |
| Sundargarh district facility list (indexed title: "Badgaon CHC Govt, Ekkma CHC Govt, Jarangloi PHC Govt, Birkera CHC Govt, Lathikata…") | District Administration, Sundargarh | https://sundargarh.odisha.gov.in/sites/default/files/2023-07/2021042567_0.pdf | PUB (host unreachable this session) | facility | (index snippet only) | — | 2023 | OFFICIAL_PUBLIC_DATA | CONDITIONAL — first thing to fetch when host reachable |
| ABDM Health Facility Registry public search | NHA | https://facility.abdm.gov.in/searchV2 (redirects to nhpr.abdm.gov.in) | CAPTCHA (human search) ; bulk/API needs ABDM sandbox credentials | facility | HFR id, name, type, address, status (via search) | bulk download | continuous | OFFICIAL_PUBLIC_DATA (per-facility, manual) | CONDITIONAL — manual lookup of ≤14 ids only; programmatic: ACCESS_NOT_ESTABLISHED |
| NIN-2-HFI (National Identification Number) | MoHFW CHI | https://nin.mohfw.gov.in | AUTH (state/district users only) | facility | NIN, MDDS codes, location | — | — | — | ACCESS_NOT_ESTABLISHED |
| Local Government Directory | MoPR | https://lgdirectory.gov.in ; data.gov.in LGD resources | PUB | district/sub-district/block/village codes | LGD codes | health facilities | continuous | OFFICIAL_PUBLIC_DATA | APPROVED for block/village codes |
| Coordinates | — | HFR entry (manual), Google Geocoding (LIVE_EXTERNAL_API), OSM (secondary, ODbL) | mixed | point | lat/lon | official bulk coordinates | — | mixed | CONDITIONAL — label source per facility; official coordinates not established |

### 3.2 Medicine / commodity catalogue (family 4)

| Source | Owner | URL | Access | Fields | Missing | Origin | Verdict |
|---|---|---|---|---|---|---|---|
| Odisha Essential Drug List 2024 ("FINAL - EDL - 2024") | DHS Odisha | https://dhsodisha.nic.in/sites/default/files/FINAL%20-%20EDL%20-%202024_compressed.pdf | PUB (host unreachable this session; existence confirmed via search index) | item, dosage form, facility applicability (per 2015 guideline the EDL is facility-wise) | unit pack, batch | OFFICIAL_PUBLIC_DATA | CONDITIONAL — must be opened to confirm formulation/level |
| Odisha STG 2018 | DH&FW Odisha | https://health.odisha.gov.in/sites/default/files/2020-02/STG-2018.pdf | PUB (verified, 338 pp) | dosing rules by condition | — | OFFICIAL_PUBLIC_DATA | APPROVED as `units_basis` citation |
| DH&FW *Guidelines on Procurement Planning & Management of Drugs* (2015) | DH&FW Odisha (hosted by NHM Odisha) | https://nhmodisha.gov.in/wp-content/uploads/2024/03/Guideline-on-Procurement-Planning-Management-of-Drugs.pdf | PUB (verified) | supply hierarchy (State DWH → District DWH → Block HQ Drug Warehouse → CHC/PHC/SC stores); annual indent via e-Aushadhi; **OSMC authorised to transfer inter-institution / inter-warehouse / inter-district stock**; DDC dispensing against prescription | quantities | OFFICIAL_PUBLIC_DATA | APPROVED as policy basis for redistribution and hierarchy |
| CAG Performance Audit 2024, Ch. 4 (Odisha) | CAG of India | https://cag.gov.in/uploads/download_audit_report/2024/14-Ch-4-Drugs-&-Equipment-067567e0a5927e4.42261532.pdf | PUB (verified, 35 pp) | **minimum stock norms: DHH 1 month, CHC 2 months, PHC 3 months**; EDL counts (DHH 542, CHC 542, PHC 295 items 2020-22); DHH Sundargarh stock-outs 12–18 drugs/yr, 90–365 days; e-Niramaya data 2016-19 not furnished to Audit | facility rows | OFFICIAL_PUBLIC_DATA | APPROVED as policy (min cover) and as evidence that the problem is real |
| OSMCL rate contracts / EDL page | OSMCL | https://osmcl.nic.in/?q=node/61 | host unreachable this session | pack sizes | — | OFFICIAL_PUBLIC_DATA | CONDITIONAL |

### 3.3 Consumption, inventory, indents, batches, expiry (families 5–9)

| Source | Owner | URL | Access | Contains (per official documents) | Public fields | Origin | Verdict |
|---|---|---|---|---|---|---|---|
| e-Niramaya / Odisha DVDMS (e-Aushadhi) | OSMCL / DH&FW Odisha (CDAC platform) | https://www.e-niramaya.odisha.gov.in/ ; https://niramaya-dvdms.odisha.gov.in/IMCS/init | AUTH (login + CAPTCHA; public pages are informational only) | procurement, warehouse stock, indents, issues, batch & expiry, DDC dispensing (documented in guideline 2015 & CAG 2024) | **none** | OFFICIAL_SYSTEM_EXPORT (only via authorised export) | ACCESS_NOT_ESTABLISHED |
| Ni-kshay Aushadhi | CTD / MoHFW | https://ni-kshayaushadhi.mohfw.gov.in/ | AUTH | TB drug stock, expiry, patient-wise consumption | none (reports.nikshay.in gives notifications only) | OFFICIAL_SYSTEM_EXPORT | ACCESS_NOT_ESTABLISHED |
| eVIN / U-WIN | MoHFW / UNDP | — | AUTH | vaccine stock, batch, expiry, sessions | none | OFFICIAL_SYSTEM_EXPORT | ACCESS_NOT_ESTABLISHED |
| Reality Lens (photo/count) | HAVEN GRID users | — | app | observed quantity, batch ids seen, timestamp, confidence | — | USER_SUPPLIED_EVIDENCE | APPROVED (already in kernel) |

There is **no** public facility-level stock, batch or expiry dataset for Odisha. Families 6–9 are Option A or evidence-only.

### 3.4 Service activity and scheduled care (families 10–11)

| Source | Owner | URL | Access | Granularity | Fields (observed / documented) | Missing | Freshness | Origin | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| HMIS Standard Reports → C2 *Data Itemwise Monthly (up to sub district)* → *4. All Districts Across Subdistricts* | MoHFW | https://hmis.mohfw.gov.in/#!/standardReports | **PUB — verified without login** | block-month | yearly zips 2008-09 … 2019-20 (up to 765 MB), folders 2020-21 and 2021-22 (provisional) with *A.MonthWise* / *B.Cummulative*; item families per HMIS facility format: ANC registrations, PW given 180 IFA, deliveries, immunisation doses, childhood diarrhoea/pneumonia, animal/snake bites, malaria, OPD/IPD | facility rows; anything after FY 2021-22 not seen in this folder; exact column headers not inspected (download timed out) | annual public dump; portal itself monthly | OFFICIAL_PUBLIC_DATA | CONDITIONAL — header verification is the first adapter task |
| data.gov.in *HMIS sub-district level item-wise monthly report of Odisha* and district-level catalogue | MeitY OGD / MoHFW | https://www.data.gov.in/catalog/hmis-sub-district-level-item-wise-monthly-report-odisha-0 ; https://odisha.data.gov.in/catalog/item-wise-monthly-hmis-report-district-level-odisha | PUB (catalog HTTP 200; backend API 500/502/504 this session) | block-month / district-month | CSV per district-year (e.g. `hmis-indicator-18-19-MonthUpToMarch-…csv` pattern) | same as above | catalogue vintage 2018-19–2019-20 observed | OFFICIAL_PUBLIC_DATA, Government Open Data License – India | CONDITIONAL |
| Anemia Mukt Bharat dashboard | MoHFW / UNICEF | https://www.anemiamuktbharat.info/ | PUB | state / district / block, monthly (numerators from HMIS) | IFA coverage KPIs, denominators | facility | monthly | OFFICIAL_PUBLIC_DATA | APPROVED (for IFA target) |
| RCH portal (EDD lists, ANC due lists) | MoHFW | — | AUTH | beneficiary | scheduled ANC / EDD | — | continuous | OFFICIAL_SYSTEM_EXPORT | ACCESS_NOT_ESTABLISHED (Option A only; PHI — must be aggregated before ingestion) |
| VHND / fixed-day schedules | Block PHC / CHC | not online | — | session | date, site | — | — | USER_SUPPLIED_EVIDENCE or SYSTEM_EXPORT | CONDITIONAL |

### 3.5 Forecast-policy values (family 12)

| Value | Basis | Source | Verdict |
|---|---|---|---|
| Minimum stock: DHH 1 month, CHC 2 months, PHC 3 months | Government norm (Table 4.2) | CAG 2024 Ch.4, "Data furnished by OSMCL" | APPROVED — replaces the synthetic `min_cover_days = 3` with tier-specific norms; HAVEN's 3-day cover becomes a *dispatch-lead* margin, not the policy floor |
| Annual indent based on previous/current consumption, seasonality, programmes | DH&FW guideline 2015 §1.5.3 | verified | APPROVED as `DemandProfile.method` citation |
| Inter-institution transfer permitted; OSMC authority | DH&FW guideline 2015 §2 | verified | APPROVED as redistribution policy reference |
| FEFO | assessment 2014 (practice reported), Ni-kshay Aushadhi alerts | verified | APPROVED as practice reference |

### 3.6 Route distance / travel time (families 13–14)

| Source | Access | Fields | Origin | Verdict |
|---|---|---|---|---|
| Google Routes API `computeRoutes` | API key (billable; Essentials SKU for basic, Pro when `TRAFFIC_AWARE`) | `distanceMeters`, `duration`, `staticDuration` | LIVE_EXTERNAL_API | APPROVED for later phase (see §16) |
| District road table | none found online | — | — | ACCESS_NOT_ESTABLISHED — the synthetic "district-road-table/2026" has no real counterpart |

### 3.7 Field evidence (family 15)

Reality Lens capture → Cloud Storage later. Origin USER_SUPPLIED_EVIDENCE. APPROVED (existing kernel path).

### 3.8 Weather / disruption (family 16)

IMD district nowcasts/warnings (mausam.imd.gov.in; data.gov.in IMD APIs). Useful only for route feasibility flags in monsoon. Not required for first adapter. CONDITIONAL, deferred.

---

## 4. Sundargarh facility audit

Verification sources: ZSS Sundargarh FDS Sub-Plan 2013-14 (official, lists all 19 CHCs and PHC(N)s of the district), DH&FW block list, CAG 2024 (Kuarmunda, Lahunipada test-checked in Sundargarh), Government Medical College Sundargarh; secondary discovery via PIN-code/GIS listings.

| Current HAVEN name | Officially verified name | Official id | District | Facility type (official) | Source | Result |
|---|---|---|---|---|---|---|
| Bhatpar PHC | — (no facility or village of this name found in Sundargarh; only "Bhatpar Rani", Deoria UP) | — | not Sundargarh | — | searches of DH&FW list, ZSS plan, district village index | **UNVERIFIED → REPLACE** |
| CHC B · Hemgir | Hemagiri (Hemgir) CHC, block HQ, Hemgir block | not obtained | Sundargarh | CHC (L2) | ZSS 2013-14 §A1.4/B1.1 | **KEEP** (drop the synthetic letter label) |
| CHC D · Kuchinda | Kuchinda — sub-divisional town of **Sambalpur** district | — | Sambalpur | (SDH/CHC of Sambalpur) | Wikipedia/PIN, not in Sundargarh CHC list | **WRONG_DISTRICT → REPLACE** |
| Kansbahal PHC | Kansbahal is an industrial town in Lathikata block; only *ESI Hospital, Kansbahal* (ESIC) found; the public PHC(N) of the block is **Lathikata PHC(N)** | — | Sundargarh | not a govt PHC on evidence seen | IFC due-diligence (ESI Hospital Kansbahal), ZSS (Lathikata PHC N) | **UNVERIFIED → REPLACE with Lathikata PHC(N)** |
| Lahunipada PHC | **Lahunipada CHC** (block HQ; CAG test-checked CHC) | — | Sundargarh | **CHC**, not PHC | ZSS 2013-14; CAG 2024 fn 85/95 | **KEEP name / REPLACE tier** |
| Nuagaon PHC | Nuagaon is a block of Sundargarh; its block CHC is **Laing CHC**; a "Nuagaon PHC" of that name not found in official lists | — | Sundargarh (block exists) | unverified | ZSS 2013-14 (Laing CHC), e-DantSeva govt listing "C.H.C Laing Sundargarh" | **UNVERIFIED → REPLACE with Laing CHC or a verified PHC(N)** |
| Remed PHC | Remed — post office in **Sambalpur Sadar** (PIN 768006) | — | Sambalpur | — | India Post PIN records | **WRONG_DISTRICT → REPLACE** |
| Koira PHC | **Koira CHC** (Koida block HQ) | — | Sundargarh | **CHC** | ZSS 2013-14 | **KEEP name / REPLACE tier** |
| Kutra PHC | **Kutra CHC** (block HQ) | — | Sundargarh | **CHC** | ZSS 2013-14 | **KEEP name / REPLACE tier** |
| Bargaon PHC | **Bargaon CHC** (block HQ) | — | Sundargarh | **CHC** | ZSS 2013-14; Medindia/ESI directories (secondary) | **KEEP name / REPLACE tier** |
| Tileibani PHC | Tileibani — block of **Deogarh** district | — | Deogarh | — | Deogarh district PDF, NHM Odisha | **WRONG_DISTRICT → REPLACE** |
| CHC A · Talsara | Talsara is an assembly constituency / GP; **not** among the 19 Sundargarh CHCs | — | Sundargarh (area) | — | ZSS 2013-14 CHC list | **UNVERIFIED → REPLACE** |
| CHC C · Bonai | **Boneigarh (Bonaigarh) SDH** — Sub-Divisional Hospital, L3 | — | Sundargarh | **SDH**, not CHC | ZSS 2013-14 | **KEEP location / REPLACE tier label** |
| District Warehouse | **OSMCL District Drug Warehouse, Sundargarh** (the DH&FW guideline defines District DWH → Block HQ Drug Warehouse → CHC/PHC/SC stores) | — | Sundargarh | DWH | DH&FW guideline 2015 §2.1; CAG 2024 (DWH per district) | **KEEP** (name/address to confirm) |

Official Sundargarh CHCs (ZSS 2013-14, 19 = district count): Bargaon, Birkera, Birmitrapur, Bisra, Gurundia, Hatibari, Hemagiri, Kinjirkela, Koira, Kuarmunda, Kutra, Lahunipada, Laing, Majhapara, Mangaspur, Rajgangpur, S. Balang, Sargipali, Subdega. Plus DHH Sundargarh, Boneigarh SDH, RGH Rourkela, Bileimunda AH, and (since 2021) GMCH Sundargarh.

Official PHC(N) names seen: Balisankara, Gopalpur (Hemgir), Kanika (Hemgir), K. Balang, Khuntagaon (Lefripada), Balijodi, Lathikata, Tangargaon (Bargaon), Andalijamabahal.

Caveat that must travel with this audit: the ZSS document is 2013-14. Facility upgrades since (e.g. PHC → CHC, HWC conversions) must be confirmed against the current NHM Odisha / HMIS facility master before any name is placed in the UI.

---

## 5. Recommended official facility graph

Topology preserved exactly: 1 warehouse → 4 hubs → 9 leaves; recipient is a leaf with two hub neighbours; the SVG stays schematic (positions unchanged). Tiers are made truthful.

| Slot (current id) | Proposed official facility | Tier (official) | Block | Verification status |
|---|---|---|---|---|
| warehouse | OSMCL District Drug Warehouse, Sundargarh | DWH | Sundargarh Sadar | policy-verified; address to confirm |
| chc-a | **Bargaon CHC** | CHC (block HQ = Block Drug Warehouse) | Bargaon | verified |
| chc-b | **Hemgir (Hemagiri) CHC** | CHC | Hemgir | verified |
| chc-c | **Bonaigarh SDH** (label "SDH", hub role unchanged) | SDH | Bonaigarh | verified |
| chc-d | **Kutra CHC** | CHC | Kutra | verified |
| koira → leaf | Kanika PHC(N) | PHC(N) | Hemgir | name verified (ZSS + block list); current status to confirm |
| kansbahal → leaf | Gopalpur PHC(N) | PHC(N) | Hemgir | name verified; status to confirm |
| bargaon → leaf | Tangargaon PHC(N) | PHC(N) | Bargaon | name verified; status to confirm |
| kutra → leaf | Balisankara PHC(N) | PHC(N) | Balisankara (adjacent to Bargaon/Subdega) | name verified; status to confirm |
| lahunipada → leaf | K. Balang PHC(N) | PHC(N) | Bonai sub-division | name verified; block to confirm |
| tileibani → leaf | Balijodi PHC(N) | PHC(N) | to confirm | name verified; block to confirm |
| **bhatpar → recipient** | **Khuntagaon PHC(N)** (Lefripada block, between Sundargarh Sadar, Bargaon and Kutra) | PHC(N) | Lefripada | name + block verified; status to confirm |
| nuagaon → leaf | Lathikata PHC(N) | PHC(N) | Lathikata | name + block verified |
| remed → leaf | Andalijamabahal PHC(N) | PHC(N) | to confirm | name verified; block to confirm |

Links: warehouse → the four hubs (matches the official District DWH → Block DWH flow); each PHC(N) → its own block CHC as the routine-resupply parent; the recipient (Khuntagaon) keeps two candidate donors, **Bargaon CHC** and **Kutra CHC**, both adjacent blocks in the district's central belt, so a 1–2 h peer transfer is geographically plausible once Google Routes supplies real times. All distances/durations in the fixture ("42 km · 1.5 h" etc.) are retired; none is asserted until §16 runs.

If a leaf's current status cannot be confirmed, the rule is *drop the slot's name and show an "unverified facility" placeholder*, not substitute a convenient one.

---

## 6. Amoxicillin data audit

| Question | Finding | Source |
|---|---|---|
| Stock unit | bottle (dry syrup/suspension) — pack size per OSMCL rate contract not verified this session | EDL 2024 / OSMCL (unreachable) |
| Dispensing unit | bottle per prescription; DDCs dispense against prescription only (no bottle-per-visit rule) | DH&FW guideline 2015 §3.1.2 |
| Consumption history | exists only inside e-Niramaya (facility issue/dispensing) | CAG 2024; guideline 2015 |
| Batch / expiry | e-Niramaya only | CAG 2024 |
| Service linkage | STG 2018: pneumonia 80–90 mg/kg/day BID; otitis media 40 mg/kg/day; durations 5–10 days → quantity depends on **weight, diagnosis and duration** | STG 2018 pp. 43, 48 |
| HMIS activity | childhood pneumonia / ARI *cases* are HMIS items; there is no "cases given amoxicillin" item | HMIS format (to be confirmed on header) |
| National guidance | SAANS / WHO: amoxicillin **dispersible tablets** are the recommended paediatric formulation — the 125 mg/5 ml suspension may not be the frontline product the state stocks at PHC level | WHO/UNICEF, SAANS references |
| Redistribution | plausible (ambient storage) | guideline 2015 §2 |
| Evidence grade achievable | **C** (UNSUPPORTED) with public data alone; **B** (ESTIMATED, wide interval) with an e-Niramaya utilisation ratio | §9 |

Conclusion: the synthetic "one attendance = one bottle" has **no authoritative basis** and cannot be labelled anything but synthetic. Amoxicillin is not viable as the judge-facing item.

---

## 7. Alternative commodity comparison

Scores 0–3 (3 = strongest). Candidates are real Odisha primary-care supply items.

| Criterion | Amoxicillin susp. | **IFA (PW, 60/500)** | Oxytocin 10 IU inj. | ORS + Zinc | Anti-rabies vaccine | Malaria RDT/ACT | Anti-TB FDC | UIP vaccines |
|---|---|---|---|---|---|---|---|---|
| Public data availability | 1 | **3** (HMIS ANC/IFA items; AMB dashboard) | 2 (HMIS deliveries) | 2 (HMIS diarrhoea cases) | 2 (HMIS dog-bite) | 2 (HMIS malaria) | 1 (notifications only) | 1 |
| Authorised logistics-data plausibility (Option A) | 2 (e-Niramaya) | **3** (e-Niramaya + RCH) | 2 | 2 | 2 | 2 (NVBDCP kits) | 3 (Ni-kshay Aushadhi) | 3 (eVIN/U-WIN) |
| Supply failure → care consequence linkage | 1 (weight/diagnosis dependent) | **3** (policy-fixed 180 tabs/pregnancy) | 3 (1 amp/delivery, STG p. AMTSL) | 2 (per case, seasonal) | 2 (course per bite) | 2 (1 RDT/fever; ACT by age band) | 3 (regimen per patient) | 3 (dose per child) |
| Published usage / service policy | 1 | **3** (AMB, MoHFW) | 3 (STG 2018) | 3 (IDCF/STG: zinc 14 days) | 2 | 3 | 3 | 3 |
| Redistribution plausibility | 3 | **3** (ambient, every tier) | 2 (cold chain 2–8 °C) | 3 | 1 (cold chain) | 2 | 1 (programme-controlled) | 1 (cold chain, programme) |
| Expiry relevance | 2 | 2 | 3 | 2 | 3 | 2 | 2 | 3 |
| Judge comprehension | 3 | **3** | 3 | 3 | 2 | 2 | 2 | 3 |
| Patient-safety / clinical-claim risk (3 = lowest) | 1 | **3** | 1 (PPH claims are grave) | 3 | 1 | 2 | 1 | 1 |
| Reality Lens suitability (countable, photographable) | 2 | **3** (strips, register) | 2 (fridge) | 3 | 2 | 2 | 2 | 1 |
| BRICS / generalisability | 3 | **3** | 3 | 3 | 2 | 2 | 2 | 3 |
| Obligations are *scheduled* | 0 | **3** (ANC visits, VHND) | 1 (EDD-based) | 0 | 0 | 0 | 3 | 3 |
| **Total** | 19 | **32** | 25 | 26 | 19 | 22 | 23 | 25 |

---

## 8. Recommended target commodity

**Tablet Iron 60 mg (elemental) + Folic Acid 500 µg — "red IFA" for pregnant women.**

Why it wins on the governing rule: the quantity per obligation is fixed by a *published national policy* (180 tablets per pregnancy, daily from the second trimester), the obligation is a scheduled antenatal contact, and both the numerator (PW given 180 IFA) and denominator (ANC registrations) are published HMIS items mirrored on the AMB dashboard. The care consequence — *antenatal supplementation interrupted for N registered women* — is truthful, quantifiable and does not require mortality claims. IFA stock-outs are recorded in Odisha's own 2014 assessment.

What changes for HAVEN (content only; no UI redesign): care categories become `antenatal` (dominant) with `walk-in` baseline; "13 exposed care events" becomes "N antenatal obligations exposed (ESTIMATED)"; the item card reads "IFA 60/500 tablets, strips of 30"; batch labels become IFA lot numbers.

Do **not** switch the fixture yet — that is a Phase 0.7 decision after this report is reviewed.
Oxytocin remains the strongest Option A stretch item once RCH EDD exports and cold-chain evidence exist.

---

## 9. Care Blast Radius evidence model

```
CareEvidenceGrade = DIRECT | ESTIMATED | UNSUPPORTED
```

| Grade | Requirement (all must hold) | Allowed statement | Origin stamped on CareImpact | Basis exposed by API |
|---|---|---|---|---|
| **A · DIRECT** | an authoritative record (ANC due list, TB regimen, delivery EDD list, immunisation session plan) links each obligation to the item **and** the quantity is either recorded or fixed by a cited policy | "13 scheduled care obligations are exposed." | OFFICIAL_SYSTEM_EXPORT (obligations) + MODEL_DERIVED (exposure) | obligation ids (opaque), policy ref, quantity rule |
| **B · ESTIMATED** | aggregate service activity for the facility/block (HMIS) **and** a cited policy or a facility-specific historical utilisation ratio; no per-obligation record | "An estimated 13 care encounters are at risk." | **MODEL_DERIVED** (mandatory label) | HMIS item ids + period, block→facility allocation method, ratio + its period, interval |
| **C · UNSUPPORTED** | neither of the above (e.g. amoxicillin with OPD counts only) | "Care Blast Radius unavailable for this item/source combination." | — | reason code `CBR_UNSUPPORTED_ITEM_SOURCE` |

Rules: grade is computed per (facility, item, source); the kernel never upgrades; the API returns `evidence_grade` and `basis`; the UI shows the grade word next to the number; a B-grade number is always shown with "estimated" and a range; a C-grade never renders a number.

---

## 10. Real-demand methodology

`units_per_attendance` is permitted only with an authoritative basis, so the field becomes:

```
UnitsRule = { kind: POLICY_FIXED | HISTORICAL_RATIO | UNAVAILABLE,
              value, unit, basis_ref, period, origin }
```

1. **Direct medication obligations** — available only in Option A (RCH/ANC due lists, Ni-kshay, U-WIN). Then `kind = POLICY_FIXED` with the obligation itself as the record.
2. **Historical item-utilisation ratios** — only from an e-Niramaya facility dispensing export: `units_dispensed(item, facility, month) / attendances(HMIS item, block→facility)`. `kind = HISTORICAL_RATIO`, origin MODEL_DERIVED, must carry the period and be recomputed per facility. Never a district constant.
3. **Cleaner deterministic commodity** — IFA: `POLICY_FIXED`, 180 tablets per registered pregnancy; monthly dispensing derived as 30 tablets per PW-month (this derivation is itself MODEL_DERIVED and labelled so, since the policy states the course, not the strip cadence).

Demand split (kernel unchanged): `baseline(d)` = walk-in dispensing from HISTORICAL_RATIO or e-Niramaya issues; `Σ units_required` = obligations × POLICY_FIXED. Block-level HMIS counts are allocated to a facility only with a stated method (facility share of block OPD from the facility master, or equal split) and the method is part of the lineage.

For amoxicillin: kind = UNAVAILABLE under Option B → CBR grade C.

---

## 11. Demo vs operational architecture

| Aspect | DEMO / REHEARSAL | OPERATIONAL |
|---|---|---|
| Config | `HAVENGRID_MODE=demo` (allowed in every env, incl. judge, but only against a sandbox store) | `HAVENGRID_MODE=operational` (default in staging/judge/prod) |
| Store | `SandboxRepository` — per-session in-memory clone; seeded from synthetic fixture (dev/test only) or from a **read-only snapshot** of operational records | `OperationalRepository` (Firestore later) |
| API namespace | `/api/sandbox/{sandbox_id}/…` incl. `reset`, `replay`, `advance` | `/api/…` — no `reset`, no `replay`; every mutation is a POST that requires `actor` + explicit command |
| Opening state | resettable; scripted evidence/recovery flow allowed | **READ-ONLY** on open: no auto-reset/propose/confirm/approve/dispatch/verify/reconcile/close |
| Mutations | never touch operational records (sandbox id is part of every key) | only via explicit user command; audited |
| Frontend | `VITE_SCENARIO_SOURCE=backend` + `mode=sandbox`; `replayDemo()` refuses unless the health bundle reports `mode: "sandbox"` **and** `sandbox_id` is non-empty | `replayDemo` is not bundled (tree-shaken behind `import.meta.env.VITE_ENABLE_SANDBOX`) |
| Protections | backend: `/api/demo/*` removed; sandbox router mounted only when `HAVENGRID_MODE=demo` or a sandbox header is present; a sandbox may be created **from** operational data, never written **to** it; Firestore: separate database id (`havengrid-sandbox`) and service account with no write scope on `havengrid-ops`; a startup guard fails if the sandbox client resolves to the ops database | audit trail; idempotent `command_id`; auth (later) |

Mode is orthogonal to `HAVENGRID_ENV`; the existing environment-integrity guard stays as is.

---

## 12. Derived-data lineage

Typed reference ids, not a generic graph:

```
DerivedFrom (embedded in every MODEL_DERIVED record)
  computed_at        datetime
  equation_ref       str        # e.g. "forecast.v1", "care_impact.v1", "sizing.v1"
  freshness          {oldest_input_observed_at, max_input_age_hours}
  inputs             typed ids below

CoverageAssessment.derived_from:
  inventory_record_id · demand_profile_id · care_obligation_ids[] · care_event_ids[]
  · incoming_supply_ids[] · policy_id · forecast_at
InterventionCandidate.derived_from:
  recipient_assessment_id · donor_assessment_id · route_estimate_id · batch_ids[] · transfer_policy_id
CareImpact.derived_from:
  coverage_assessment_id · care_obligation_ids[] · care_event_ids[] · units_rule_id · evidence_grade
```

Every observational record already carries `Provenance{origin, status, observed_at, source_ref}`.
"Why is this facility at risk?" is answered by walking one level: equation + each input's value, `observed_at`, origin and age. Ask Haven later reads this; it never computes.

---

## 13. Missing-data semantics

UNKNOWN never becomes 0, safe, no breach, no exposed care, no replenishment or no expiry risk.

| Missing input | Still possible | Unavailable | Result state | UI status |
|---|---|---|---|---|
| No current stock record | CBR *potential* (obligations known) | forecast, breach day, candidates | forecast `unavailable` | "No verified stock — request count" |
| Stale stock (> policy age, e.g. 7 d) | forecast from as-of, breach day | high-confidence claims | `low_confidence` | age badge + "count needed" |
| No consumption history | obligation-only demand | baseline, coverage | `unavailable` (or `low_confidence` if obligations dominate) | "No dispensing history" |
| Incoming supply, quantity unknown | forecast **without** credit | recovery day | `low_confidence`; supply shown `unknown` | "Indent pending — quantity unknown" |
| Incoming supply, timestamp unknown | forecast without credit | recovery day, donor protection window | `low_confidence` | "ETA unknown" |
| Missing batch | forecast, CBR, sizing | FEFO allocation, expiry relief rank | candidate `expiry_unknown` | "Batches not recorded" |
| Missing expiry | as above | expiry relief | `expiry_unknown` | same |
| Missing care activity | forecast, stockout | CBR | CBR grade C | "Care exposure unavailable" |
| Route unavailable | sizing, eligibility except transit | feasibility | candidate `ROUTE_UNAVAILABLE` | "Route not established" |
| Official source offline | last snapshot with age | refresh | bundle `stale_source` | banner with `retrieved_at` |
| Conflicting observations | both kept, none canonical until confirmed | forecast | `awaiting_confirmation` | "Conflict — confirm" |

---

## 14. Option A — authorised operational export

| Element | Source | Grade |
|---|---|---|
| Facilities | NHM Odisha facility master + HFR ids | OFFICIAL_PUBLIC_DATA |
| Inventory | e-Niramaya facility stock export (CSV/API under MoU) | OFFICIAL_SYSTEM_EXPORT |
| Historical dispensing | e-Niramaya DDC issues per item/facility/month | OFFICIAL_SYSTEM_EXPORT |
| Incoming supply | e-Niramaya indents/issues in transit | OFFICIAL_SYSTEM_EXPORT |
| Batches / expiry | e-Niramaya batch ledger | OFFICIAL_SYSTEM_EXPORT |
| Service activity | HMIS facility-level (login) + RCH ANC due lists **aggregated to counts before ingestion** | OFFICIAL_SYSTEM_EXPORT |
| Routes | Google Routes on official coordinates | LIVE_EXTERNAL_API |
| Evidence | Reality Lens | USER_SUPPLIED_EVIDENCE |

Derived directly: coverage, breach, stockout, CBR **grade A** (IFA/oxytocin/TB), donors, FEFO, transferable. Still simulated: the transfer itself (counterfactual), dispatch timing until a real dispatch. Privacy: RCH data is PHI — only aggregated `CareObligation` rows cross the boundary; DPDP-compliant MoU with DH&FW/OSMCL required. Demo strength: highest; deployment credibility: highest; cost: months of institutional access, not code.

## 15. Option B — open-data only

| Element | Source | Available | Unavailable |
|---|---|---|---|
| Facilities | ZSS/NHM lists, HFR manual ids, LGD codes | names, types, blocks | official coordinates, bulk ids |
| Service activity | HMIS Standard Reports (block-month), AMB dashboard | ANC registrations, PW-180-IFA, deliveries, diarrhoea, pneumonia, bites, OPD | facility rows, anything newer than the last public dump |
| Policy | STG 2018, DH&FW 2015, CAG 2024 norms | min-stock months, transfer authority, dosing | — |
| Inventory / batch / expiry / indents | **Reality Lens only** | observed counts, batch ids seen | ledger history |
| Routes | Google Routes | distance/time | — |

Fully functional: state machine, evidence lineage, verification, reconciliation, FEFO on *observed* batches, policy cover. **Estimated**: demand baseline (from HMIS proxies), CBR (grade B, IFA). **Disabled**: e-Niramaya-derived incoming supply (unless user-entered), historical dispensing curves, any grade-A claim. Amoxicillin: not appropriate (grade C). Stronger: IFA. Demo strength: honest, medium — the story becomes "real facilities, real policy, real activity counts, human-verified stock". Judges must be told: stock is user-observed, care exposure is estimated from block-level public counts, and public HMIS lags.

---

## 16. Google Routes future contract

```
RouteEstimateRequest  { origin_facility_id, destination_facility_id,
                        origin{lat,lon,source}, destination{lat,lon,source},
                        departure_time (RFC 3339) | null, travel_mode: DRIVE }
RouteEstimate         { id, from_id, to_id, distance_m, duration_s, static_duration_s,
                        retrieved_at, provider: "google_routes", sku: ESSENTIALS|PRO,
                        status: OK|NO_ROUTE|PROVIDER_ERROR|UNAVAILABLE,
                        provenance{origin: LIVE_EXTERNAL_API, source_ref: request hash} }
```

Field mask limited to `routes.distanceMeters, routes.duration, routes.staticDuration`; `departure_time` omitted by default (Essentials SKU); `TRAFFIC_AWARE` only when a dispatch is being timed. Estimates are cached per (pair, day) and expire; `status != OK` → `ROUTE_UNAVAILABLE` (never a default distance). The SVG network remains the interface; no map tiles.

## 17. Google / AI future compatibility

Vertex/Gemini read `DerivedFrom` + provenance to explain, extract register photos into `EvidenceRecord{observed_quantity, confidence}` (still confirmed by a human), and draft briefings. Cloud Storage holds evidence blobs referenced by `source_ref`. Firestore holds operational records with the sandbox/ops separation of §11. Cloud Run serves FastAPI unchanged. Firebase Auth supplies `actor` identity/roles into the existing free-text `actor` slot. Google Routes fills `RouteEstimate`. The kernel stays authoritative for arithmetic, safety, feasibility, transitions, verification and canonical mutations.

## 18. Judge-facing claims we can safely make

- Facility names, types and blocks come from official Government of Odisha records.
- Minimum-stock policy (DHH 1 / CHC 2 / PHC 3 months) and inter-facility transfer authority are official Odisha policy (CAG 2024; DH&FW 2015).
- Stock-outs and expiry are documented problems in Odisha public facilities, including DHH Sundargarh (CAG 2024).
- Service-activity denominators are public HMIS data at block level, with stated period.
- Every current stock figure shown is a human observation with a timestamp and confidence.
- Care exposure is **estimated** and labelled MODEL_DERIVED, with its basis viewable.
- Routes, once wired, are live Google Routes estimates with retrieval time.

## 19. Claims we must NOT make yet

- Any facility-level stock, batch or expiry "from the government system".
- "Real-time" anything; "connected to e-Niramaya"; "13 scheduled care events" without grade A.
- Any patient outcome (deaths averted, PPH prevented).
- Amoxicillin bottles per visit; any `units_per_attendance` without a `basis_ref`.
- Distances or travel times from the retired road table.
- That Sundargarh's current facility tiers match the 2013-14 list, until re-verified.

## 20. Exact sources to implement first

1. HMIS Standard Reports → C2 / 4. All Districts Across Subdistricts → latest FY zip (verify headers first; then Odisha → Sundargarh blocks; items: ANC registrations, PW given 180 IFA, OPD).
2. Official facility roster: NHM Odisha / HMIS facility master (public form) cross-checked with ZSS 2013-14 names; HFR ids by manual lookup for the 14 nodes.
3. Policy records: CAG 2024 min-stock norms; DH&FW 2015 transfer authority; STG 2018 / AMB IFA rule as `units_basis`.
4. Reality Lens as the declared inventory source (`origin = user_supplied_evidence`).
5. Google Routes (design in §16) — after 1–4.

## 21. GO / NO-GO for first real-data adapter

**GO — conditional.** Build `OfficialPublicSource` for families 1–3 and 10–12 only, read-only, with `retrieved_at` and period on every record, gated on: (a) inspecting the real HMIS zip headers, (b) confirming current facility tiers, (c) the commodity switch to IFA being approved.
**NO-GO** for any inventory / batch / expiry / incoming-supply adapter from public sources — none exists; those families stay `DataSourceUnavailable` until an authorised export (Option A) or are served as `USER_SUPPLIED_EVIDENCE`.
**NO-GO** for amoxicillin as the judge-facing item.

STOP. No adapter implemented.
