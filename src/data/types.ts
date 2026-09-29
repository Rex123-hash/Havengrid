/**
 * Contracts for the landing-page scenario.
 *
 * These shapes are intentionally written the way a real API response would be,
 * not the way this particular animation happens to need. When the forecasting
 * service exists, `landingScenario.ts` is replaced by a fetch and the story
 * components are unchanged.
 */

export type FacilityTier = 'warehouse' | 'chc' | 'phc';

/** Six-state evidence vocabulary. `unknown` must never render as healthy. */
export type ForecastStatus = 'forecast' | 'unavailable';

export interface Facility {
  id: string;
  name: string;
  /** Short form used on the map when space is tight. */
  short: string;
  tier: FacilityTier;
  /** Normalised layout coordinates in the network viewBox (0–1000 × 0–640). */
  x: number;
  y: number;
  /**
   * Days from now until predicted stock-out for the tracked item.
   * `null` = no breach predicted inside the 30-day window.
   * A facility whose forecast could not be produced carries
   * `forecastStatus: 'unavailable'` and must render as unknown, never green.
   */
  breachDay: number | null;
  forecastStatus: ForecastStatus;
  /** Care events exposed if this facility breaches. */
  careEventsExposed: number;
  /** Days since the inventory figure was last physically verified. */
  daysSinceVerified: number;
}

export interface SupplyLink {
  from: string;
  to: string;
}

export type CareCohortKey = 'paediatric' | 'maternal' | 'scheduled';

export interface CareCohort {
  key: CareCohortKey;
  label: string;
  /** EXPOSED encounters in this cohort (inside the uncovered interval). */
  count: number;
  /** Scheduled encounters in this cohort inside the planning window. */
  scheduled: number;
  /** Plain-language detail shown beside the cohort. */
  detail: string;
}

/** The three-tier care statement: scheduled · exposed · would be unserved. */
export interface CareExposure {
  scheduled: number;
  exposed: number;
  unserved: number;
}

export interface TrackedItem {
  name: string;
  form: string;
  unit: string;
  currentStock: number;
  projectedDemand: number;
  demandWindowDays: number;
  replenishmentEtaDays: number;
  /** First day-end at which stock cannot cover the next `minCoverDays` of care. */
  coverageBreachDay: number;
  /** First day-end at which stock is physically exhausted. Distinct from coverage. */
  stockoutDay: number | null;
  minCoverDays: number;
}

export type CandidateVerdict = 'chosen' | 'held' | 'rejected';

export interface CandidateIntervention {
  id: string;
  facilityId: string;
  facilityName: string;
  /** Units the donor can release and still stay covered through its protection window. */
  transferable: number;
  distanceKm: number;
  transitHours: number;
  verdict: CandidateVerdict;
  /** Why it was chosen, held or rejected. Deterministic, not model-authored. */
  reason: string;
  /** Present only on a chosen plan. */
  transferUnits?: number;
  /** Reasons the chosen plan holds up, derived from component checks. */
  justifications?: string[];
  /** Breach day after this plan executes. */
  resultingBreachDay?: number;
}

export interface RealityLensEvidence {
  facilityId: string;
  facilityName: string;
  /** What the system believed. */
  digitalRecord: number;
  /** What the photographed register shows. */
  fieldEvidence: number;
  /** Extraction confidence from the multimodal read, 0–1. */
  confidence: number;
  capturedVia: string;
  /** Rows transcribed from the register, shown as the evidence artefact. */
  registerRows: { date: string; issued: number | null; balance: number }[];
  /** Effect on the donor's own forecast once a human confirms. `null` = no breach inside the horizon. */
  breachDayBefore: number | null;
  breachDayAfter: number | null;
  /** Facilities whose coverage changes as a consequence of the correction, with their corrected breach day. */
  cascadeFacilityIds: string[];
  cascadeBreachDays: Record<string, number | null>;
}

export interface VerificationStep {
  key: string;
  label: string;
  detail: string;
}

export interface LandingScenario {
  district: string;
  region: string;
  facilityCount: number;
  scheduledCareEvents: number;
  focusFacilityId: string;
  item: TrackedItem;
  facilities: Facility[];
  links: SupplyLink[];
  careCohorts: CareCohort[];
  careExposure: CareExposure;
  totalCareEventsExposed: number;
  candidates: CandidateIntervention[];
  realityLens: RealityLensEvidence;
  /** The plan generated after the correction invalidates the first one. */
  replan: CandidateIntervention;
  verification: VerificationStep[];
  /** Horizon rail stops, in days. */
  horizonStops: number[];
}
