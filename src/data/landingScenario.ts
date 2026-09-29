import type { LandingScenario } from './types';

/**
 * LOCAL PRESENTATION SEED — development/test only.
 *
 * Every figure here mirrors what the deterministic backend derives from the
 * synthetic Sundargarh fixture (backend/havengrid/synthetic/sundargarh.py).
 * It is NOT an independent source of truth: in backend mode the adapter
 * replaces every semantic field from the API and throws if one is missing.
 * The environment guard forbids this file from serving staging/judge/production.
 *
 * Approved derived values (Phase 0A gate):
 *   demand 191 · stock 143 · gap 48
 *   coverage breach day 8 · physical stockout day 11 · recovery day 14
 *   23 scheduled · 13 exposed (7 paediatric · 4 maternal · 2 scheduled) · 6 unserved
 *   transfer 80 (72 rounded to a carton of 10)
 *   CHC D chosen (expiry relief) · CHC B rank 2 · warehouse rank 3 (arrives 24 h before breach)
 *   Kansbahal DONOR_ALREADY_AT_RISK · Lahunipada INSUFFICIENT_TRANSFERABLE_STOCK
 *   after 126 confirmed: CHC D's own coverage breaches day 12 · CHC B chosen
 *   after reconciliation: Bhatpar 223, no breach in 30 days · 13 protected
 */
export const landingScenario: LandingScenario = {
  district: 'Sundargarh',
  region: 'Odisha',
  facilityCount: 14,
  scheduledCareEvents: 86,
  focusFacilityId: 'bhatpar',

  item: {
    name: 'Amoxicillin',
    form: 'oral suspension · 125 mg / 5 ml',
    unit: 'dispensing units',
    currentStock: 143,
    projectedDemand: 191,
    demandWindowDays: 14,
    replenishmentEtaDays: 13,
    coverageBreachDay: 8,
    stockoutDay: 11,
    minCoverDays: 3,
  },

  /* Layout coordinates sit in a 1000 × 640 viewBox. Positions are fixed for
     the lifetime of the page — the network is mounted once and never moves. */
  facilities: [
    { id: 'warehouse', name: 'District Warehouse', short: 'Warehouse', tier: 'warehouse', x: 498, y: 78,  breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 1 },
    { id: 'chc-a',     name: 'CHC A · Talsara',    short: 'CHC A',     tier: 'chc',       x: 330, y: 182, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 2 },
    { id: 'chc-b',     name: 'CHC B · Hemgir',     short: 'CHC B',     tier: 'chc',       x: 636, y: 172, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 1 },
    { id: 'chc-c',     name: 'CHC C · Bonai',      short: 'CHC C',     tier: 'chc',       x: 188, y: 308, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 4 },
    { id: 'chc-d',     name: 'CHC D · Kuchinda',   short: 'CHC D',     tier: 'chc',       x: 762, y: 338, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 9 },
    { id: 'koira',     name: 'Koira PHC',          short: 'Koira',     tier: 'phc',       x: 252, y: 108, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 3 },
    { id: 'kansbahal', name: 'Kansbahal PHC',      short: 'Kansbahal', tier: 'phc',       x: 118, y: 196, breachDay: 7,    forecastStatus: 'forecast',    careEventsExposed: 3,  daysSinceVerified: 2 },
    { id: 'bargaon',   name: 'Bargaon PHC',        short: 'Bargaon',   tier: 'phc',       x: 848, y: 108, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 2 },
    { id: 'kutra',     name: 'Kutra PHC',          short: 'Kutra',     tier: 'phc',       x: 402, y: 262, breachDay: null, forecastStatus: 'unavailable', careEventsExposed: 0,  daysSinceVerified: 99 },
    { id: 'lahunipada',name: 'Lahunipada PHC',     short: 'Lahunipada',tier: 'phc',       x: 250, y: 408, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 5 },
    { id: 'tileibani', name: 'Tileibani PHC',      short: 'Tileibani', tier: 'phc',       x: 142, y: 462, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 3 },
    { id: 'bhatpar',   name: 'Bhatpar PHC',        short: 'Bhatpar',   tier: 'phc',       x: 500, y: 362, breachDay: 8,    forecastStatus: 'forecast',    careEventsExposed: 13, daysSinceVerified: 3 },
    { id: 'nuagaon',   name: 'Nuagaon PHC',        short: 'Nuagaon',   tier: 'phc',       x: 866, y: 232, breachDay: 11,   forecastStatus: 'forecast',    careEventsExposed: 2,  daysSinceVerified: 4 },
    { id: 'remed',     name: 'Remed PHC',          short: 'Remed',     tier: 'phc',       x: 858, y: 438, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 2 },
  ],

  links: [
    { from: 'warehouse', to: 'chc-a' },
    { from: 'warehouse', to: 'chc-b' },
    { from: 'warehouse', to: 'chc-c' },
    { from: 'warehouse', to: 'chc-d' },
    { from: 'chc-a', to: 'koira' },
    { from: 'chc-a', to: 'kansbahal' },
    { from: 'chc-a', to: 'kutra' },
    { from: 'chc-b', to: 'bargaon' },
    { from: 'chc-b', to: 'nuagaon' },
    { from: 'chc-b', to: 'bhatpar' },
    { from: 'chc-c', to: 'tileibani' },
    { from: 'chc-c', to: 'lahunipada' },
    { from: 'chc-d', to: 'remed' },
    { from: 'chc-d', to: 'bhatpar' },
  ],

  careCohorts: [
    { key: 'paediatric', label: 'paediatric', count: 7, scheduled: 11, detail: 'second-dose follow-ups from the outreach camp, due days 7–12' },
    { key: 'maternal',   label: 'maternal',   count: 4, scheduled: 7,  detail: 'ANC/PNC clinic visits with a prescribed course' },
    { key: 'scheduled',  label: 'scheduled',  count: 2, scheduled: 5,  detail: 'routine outpatient reviews already booked' },
  ],
  careExposure: { scheduled: 23, exposed: 13, unserved: 6 },
  totalCareEventsExposed: 13,

  candidates: [
    {
      id: 'plan-001:chc-d',
      facilityId: 'chc-d',
      facilityName: 'CHC D · Kuchinda',
      transferable: 136,
      distanceKm: 42,
      transitHours: 1.5,
      verdict: 'chosen',
      transferUnits: 80,
      reason: 'Ranked first — relieves expiry pressure; transit 1.5 h.',
      justifications: [
        'Prevents the projected coverage breach — Bhatpar PHC stays covered through the forecast horizon',
        'Donor remains safe through its 14-day protection window — 136 transferable, 80 released',
        'Relieves expiry pressure — batch AMX-2401-K would otherwise expire inside the horizon',
        'Arrives on day 1, before the coverage breach',
        'Protects 13 exposed care events',
      ],
    },
    {
      id: 'plan-001:chc-b',
      facilityId: 'chc-b',
      facilityName: 'CHC B · Hemgir',
      transferable: 215,
      distanceKm: 68,
      transitHours: 2.6,
      verdict: 'held',
      reason: 'Feasible, ranked 2 — no expiry pressure to relieve; transit 2.6 h.',
    },
    {
      id: 'plan-001:warehouse',
      facilityId: 'warehouse',
      facilityName: 'District Warehouse',
      transferable: 1100,
      distanceKm: 96,
      transitHours: 144,
      verdict: 'held',
      reason: 'Feasible, ranked 3 — no expiry pressure to relieve; transit 144 h.',
    },
    {
      id: 'plan-001:lahunipada',
      facilityId: 'lahunipada',
      facilityName: 'Lahunipada PHC',
      transferable: 20,
      distanceKm: 27,
      transitHours: 1.0,
      verdict: 'rejected',
      reason: 'The donor’s transferable surplus is smaller than the required quantity; releasing it would breach the donor’s own coverage.',
    },
    {
      id: 'plan-001:kansbahal',
      facilityId: 'kansbahal',
      facilityName: 'Kansbahal PHC',
      transferable: -33,
      distanceKm: 31,
      transitHours: 1.1,
      verdict: 'rejected',
      reason: 'The donor’s own coverage breaches inside its protection window even without a transfer.',
    },
  ],

  realityLens: {
    facilityId: 'chc-d',
    facilityName: 'CHC D · Kuchinda',
    digitalRecord: 286,
    fieldEvidence: 126,
    confidence: 0.83,
    capturedVia: 'Field photograph · ward stock register',
    registerRows: [
      { date: '10/03', issued: null, balance: 286 },
      { date: '12/03', issued: 46, balance: 240 },
      { date: '15/03', issued: 62, balance: 178 },
      { date: '18/03', issued: 52, balance: 126 },
    ],
    breachDayBefore: null,
    breachDayAfter: 12,
    cascadeFacilityIds: ['chc-d'],
    cascadeBreachDays: { 'chc-d': 12 },
  },

  replan: {
    id: 'plan-002:chc-b',
    facilityId: 'chc-b',
    facilityName: 'CHC B · Hemgir',
    transferable: 215,
    distanceKm: 68,
    transitHours: 2.6,
    verdict: 'chosen',
    transferUnits: 80,
    reason: 'Ranked first; transit 2.6 h.',
    justifications: [
      'Prevents the projected coverage breach — Bhatpar PHC stays covered through the forecast horizon',
      'Donor remains safe through its 14-day protection window — 215 transferable, 80 released',
      'Arrives on day 1, before the coverage breach',
      'Protects 13 exposed care events',
    ],
  },

  verification: [
    { key: 'proposed',    label: 'Proposed',            detail: 'Plan generated from corrected inventory' },
    { key: 'approved',    label: 'Approved',            detail: 'District coordinator · two-key authorisation' },
    { key: 'dispatched',  label: 'Dispatched',          detail: 'CHC B · Hemgir — 80 units in transit' },
    { key: 'source',      label: 'Source verified',     detail: 'CHC B · Hemgir stock verified at 260 (expected 260)' },
    { key: 'destination', label: 'Destination verified',detail: 'Bhatpar PHC stock verified at 223 (expected 223)' },
    { key: 'batch',       label: 'Batch matched',       detail: 'AMX-2403-B confirmed at both ends' },
    { key: 'care',        label: 'Care protected',      detail: '13 exposed care events now covered' },
    { key: 'closed',      label: 'Closed',              detail: 'Resilience loop closed' },
  ],

  horizonStops: [0, 3, 7, 14, 30],
};
