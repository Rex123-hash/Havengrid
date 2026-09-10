import type { LandingScenario } from './types';

/**
 * THE SINGLE SOURCE OF TRUTH FOR THE LANDING STORY.
 *
 * Every number rendered anywhere on the landing page is read from this object.
 * Nothing is generated, incremented on a timer, or randomised — the "23 care
 * events" on screen are 11 + 7 + 5 below, and the 44-unit deficit is
 * projectedDemand − currentStock. If a figure cannot be traced to this file,
 * it is a bug.
 *
 * Internal consistency, for reviewers:
 *   deficit            187 − 143 = 44 units
 *   care events        11 + 7 + 5 = 23
 *   chosen plan        CHC D · Kuchinda, 80 units, breach 6d → 18d
 *   correction         CHC D digital 286 vs field 126 = −160
 *   donor safety floor 200 → 126 is below it, so CHC D can no longer donate
 *   replan             CHC B · Hemgir, 80 units, breach 6d → 16d (longer transit)
 */
export const landingScenario: LandingScenario = {
  district: 'Sundargarh',
  region: 'Odisha',
  facilityCount: 14,
  scheduledCareEvents: 4180,
  focusFacilityId: 'bhatpar',

  item: {
    name: 'Amoxicillin',
    form: 'oral suspension · 125 mg / 5 ml',
    unit: 'units',
    currentStock: 143,
    projectedDemand: 187,
    demandWindowDays: 14,
    replenishmentEtaDays: 13,
    breachDay: 6,
  },

  /* Layout coordinates sit in a 1000 × 640 viewBox. Positions are fixed for
     the lifetime of the page — the network is mounted once and never moves. */
  facilities: [
    { id: 'warehouse', name: 'District Warehouse', short: 'Warehouse', tier: 'warehouse', x: 498, y: 78,  breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 1 },
    { id: 'chc-a',     name: 'CHC A · Talsara',    short: 'CHC A',     tier: 'chc',       x: 330, y: 182, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 2 },
    { id: 'chc-b',     name: 'CHC B · Hemgir',     short: 'CHC B',     tier: 'chc',       x: 636, y: 172, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 1 },
    { id: 'chc-c',     name: 'CHC C · Bonai',      short: 'CHC C',     tier: 'chc',       x: 188, y: 308, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 4 },
    { id: 'chc-d',     name: 'CHC D · Kuchinda',   short: 'CHC D',     tier: 'chc',       x: 762, y: 338, breachDay: 19,   forecastStatus: 'forecast',    careEventsExposed: 14, daysSinceVerified: 9 },
    { id: 'koira',     name: 'Koira PHC',          short: 'Koira',     tier: 'phc',       x: 252, y: 108, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 3 },
    { id: 'kansbahal', name: 'Kansbahal PHC',      short: 'Kansbahal', tier: 'phc',       x: 118, y: 196, breachDay: 9,    forecastStatus: 'forecast',    careEventsExposed: 17, daysSinceVerified: 2 },
    { id: 'bargaon',   name: 'Bargaon PHC',        short: 'Bargaon',   tier: 'phc',       x: 848, y: 108, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 2 },
    { id: 'kutra',     name: 'Kutra PHC',          short: 'Kutra',     tier: 'phc',       x: 402, y: 262, breachDay: null, forecastStatus: 'unavailable', careEventsExposed: 0,  daysSinceVerified: 16 },
    { id: 'lahunipada',name: 'Lahunipada PHC',     short: 'Lahunipada',tier: 'phc',       x: 250, y: 408, breachDay: 22,   forecastStatus: 'forecast',    careEventsExposed: 6,  daysSinceVerified: 5 },
    { id: 'tileibani', name: 'Tileibani PHC',      short: 'Tileibani', tier: 'phc',       x: 142, y: 462, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 0,  daysSinceVerified: 3 },
    { id: 'bhatpar',   name: 'Bhatpar PHC',        short: 'Bhatpar',   tier: 'phc',       x: 500, y: 362, breachDay: 6,    forecastStatus: 'forecast',    careEventsExposed: 23, daysSinceVerified: 3 },
    { id: 'nuagaon',   name: 'Nuagaon PHC',        short: 'Nuagaon',   tier: 'phc',       x: 866, y: 232, breachDay: 13,   forecastStatus: 'forecast',    careEventsExposed: 11, daysSinceVerified: 4 },
    { id: 'remed',     name: 'Remed PHC',          short: 'Remed',     tier: 'phc',       x: 858, y: 438, breachDay: null, forecastStatus: 'forecast',    careEventsExposed: 9,  daysSinceVerified: 6 },
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
    { key: 'paediatric', label: 'paediatric', count: 11, detail: 'second-dose follow-ups due between day 7 and day 12' },
    { key: 'maternal',   label: 'maternal',   count: 7,  detail: 'antenatal and postnatal visits with a prescribed course' },
    { key: 'scheduled',  label: 'scheduled',  count: 5,  detail: 'routine outpatient appointments already booked' },
  ],
  totalCareEventsExposed: 23,

  candidates: [
    {
      id: 'cand-kansbahal',
      facilityId: 'kansbahal',
      facilityName: 'Kansbahal PHC',
      surplus: 120,
      distanceKm: 31,
      transitHours: 1.1,
      verdict: 'rejected',
      reason: 'Transfer would create a second shortage — Kansbahal breaches on day 9 without it.',
    },
    {
      id: 'cand-lahunipada',
      facilityId: 'lahunipada',
      facilityName: 'Lahunipada PHC',
      surplus: 22,
      distanceKm: 27,
      transitHours: 1.0,
      verdict: 'rejected',
      reason: 'Surplus of 22 falls short of the 44-unit deficit and would breach its own safety floor.',
    },
    {
      id: 'cand-warehouse',
      facilityId: 'warehouse',
      facilityName: 'District Warehouse',
      surplus: 1240,
      distanceKm: 96,
      transitHours: 144,
      verdict: 'rejected',
      reason: 'Six-day dispatch window arrives after the predicted breach on day 6.',
    },
    {
      id: 'cand-chc-b',
      facilityId: 'chc-b',
      facilityName: 'CHC B · Hemgir',
      surplus: 165,
      distanceKm: 68,
      transitHours: 2.6,
      verdict: 'held',
      reason: 'Viable but further out. Held in reserve — no expiry pressure to relieve.',
    },
    {
      id: 'cand-chc-d',
      facilityId: 'chc-d',
      facilityName: 'CHC D · Kuchinda',
      surplus: 86,
      distanceKm: 42,
      transitHours: 1.5,
      verdict: 'chosen',
      transferUnits: 80,
      resultingBreachDay: 18,
      reason: 'Nearest viable donor, and the transfer relieves a batch nearing expiry.',
      justifications: [
        'Prevents the projected shortage — breach moves from day 6 to day 18',
        'Donor remains above its safety floor — 86 surplus, 80 released',
        'Reduces expiry pressure — consumes a batch expiring in 21 days',
        'Preserves neighbouring reserves — Kansbahal and CHC B untouched',
        'Protects 23 future care events',
      ],
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
    breachDayBefore: 19,
    breachDayAfter: 6,
    cascadeFacilityIds: ['chc-d', 'remed'],
  },

  replan: {
    id: 'replan-chc-b',
    facilityId: 'chc-b',
    facilityName: 'CHC B · Hemgir',
    surplus: 165,
    distanceKm: 68,
    transitHours: 2.6,
    verdict: 'chosen',
    transferUnits: 80,
    resultingBreachDay: 16,
    reason: 'The option held in reserve becomes the plan once CHC D is ruled out.',
    justifications: [
      'Prevents the projected shortage — breach moves from day 6 to day 16',
      'Donor remains above its safety floor — 165 surplus, 80 released',
      'Longer transit accepted — 68 km, 2.6 h, still inside the window',
      'Protects 23 future care events',
    ],
  },

  verification: [
    { key: 'proposed',    label: 'Proposed',            detail: 'Plan generated from corrected inventory' },
    { key: 'approved',    label: 'Approved',            detail: 'District coordinator · two-key authorisation' },
    { key: 'dispatched',  label: 'Dispatched',          detail: 'CHC B · Hemgir — 80 units in transit' },
    { key: 'source',      label: 'Source verified',     detail: 'CHC B stock decreased by 80' },
    { key: 'destination', label: 'Destination verified',detail: 'Bhatpar PHC stock increased by 80' },
    { key: 'batch',       label: 'Batch matched',       detail: 'AMX-2403-B confirmed at both ends' },
    { key: 'care',        label: 'Care protected',      detail: '23 exposed care events now covered' },
    { key: 'closed',      label: 'Closed',              detail: 'Resilience loop closed' },
  ],

  horizonStops: [0, 3, 7, 14, 30],
};
