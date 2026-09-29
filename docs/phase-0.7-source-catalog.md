# Phase 0.7 source catalog

The first captured public source is the AMB stock dashboard. Raw rendered
captures and the manifest live under `data/raw/official/amb/`. They are parsed
by `backend/havengrid/ingest/amb.py` into district aggregate signals only.

| Family | Source | Granularity | Status | Unsupported in this slice |
|---|---|---|---|---|
| AMB stock | https://www.anemiamuktbharat.info/reports/stock | district × commodity × month | captured for Sundargarh, Sambalpur, Kalahandi FY 2025–26 | facility allocation, batch/expiry |
| AMB KPI | https://www.anemiamuktbharat.info/reports/key-performance-indicators | district/month indicator cards | schema identified; numeric Sundargarh activity not admitted yet | facility rows, care linkage |
| HMIS | https://hmis.mohfw.gov.in/#!/standardReports | district/block report | source family configured; old export retained for inspection | current clean machine-readable Sundargarh IFA rows |
| Facility registry | Odisha Health / GJAY directories | facility metadata | seven Sundargarh facilities corroborated | official IDs/coordinates for every row |
| DVDMS | https://niramaya-dvdms.odisha.gov.in/IMCS/init | operational inventory | login-gated; no public export captured | inventory, batch, expiry |
| Routes | Google Routes | facility pair | future source seam | route timings |

No district aggregate is promoted to `InventoryRecord`. Facility inventory must
arrive as confirmed field evidence or an authorised operational export.
