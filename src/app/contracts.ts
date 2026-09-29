/** UI-1 presentation contracts. No operational API or auth dependencies. */
export type FactClass =
  | "REAL_PUBLIC"
  | "OFFICIAL_SYSTEM_EXPORT"
  | "LIVE_EXTERNAL_API"
  | "REHEARSAL_EVIDENCE"
  | "REHEARSAL_ASSUMPTION"
  | "MODEL_DERIVED"
  | "UNKNOWN";
export interface Fact<T = string | number> {
  value: T;
  classification: FactClass;
  source: string;
  asOf?: string;
  explanation: string;
}
export type Role = "VIEWER" | "FIELD REVIEWER" | "COORDINATOR";
export type Mode = "REHEARSAL" | "OPERATIONAL";
export type Risk = "At risk" | "Watch" | "Stable" | "Unknown";
export interface Facility {
  id: string;
  name: string;
  short: string;
  tier: "CHC" | "SDH" | "DHH";
  block: string;
  currentness: "Verified" | "Corroborated";
  risk: Risk;
  stock: Fact<number | null>;
  evidenceAge: string;
  inventoryStatus: "Available" | "Source stale" | "Inventory required";
  active: boolean;
  x: number;
  y: number;
}
export interface Donor {
  facilityId: string;
  distance: Fact;
  duration: string;
  quantity: Fact;
  margin: Fact;
  verdict: string;
  reason: string;
  expiry: Fact;
}
export interface Evidence {
  id: string;
  facilityId: string;
  previous: number | null;
  observed: number;
  status:
    | "Confirmed"
    | "Awaiting review"
    | "Conflict"
    | "Rejected"
    | "Recount requested";
  captured: string;
  source: string;
  confidence: string;
  batch: string;
  expiry: string;
}
export interface Readiness {
  label: string;
  state: string;
  detail: string;
  classification: FactClass;
}
export interface Source {
  name: string;
  authority: string;
  period: string;
  fields: string;
  url: string;
  classification: FactClass;
}
export interface DistrictStockSignal {
  period: string;
  available: Fact;
  granularity: string;
  qualityFlags: string[];
}
export interface Scenario {
  id: string;
  title: string;
  snapshot: string;
  commodity: string;
  formulation: string;
  facilities: Facility[];
  donors: Donor[];
  evidence: Evidence[];
  readiness: Readiness[];
  sources: Source[];
  recipientId: string;
  selectedId: string;
  invalidatedId: string;
  breach: Fact;
  stockout: Fact;
  exposure: Fact;
  baseline: Fact;
  demand: Fact;
  transfer: Fact;
  recoveredStock: Fact;
  dispatchUnit: Fact;
  programmeKpi: Fact;
  incoming: Fact;
}
export interface WorkspaceProvider {
  load(districtId: string): Promise<WorkspaceData>;
  confirmEvidence(caseId: string, evidenceId: string): Promise<void>;
  rejectEvidence(caseId: string, evidenceId: string): Promise<void>;
  districts: readonly string[];
}
export type CaseState =
  | "FORECASTED" | "INTERVENTION_PROPOSED" | "AWAITING_EVIDENCE_CONFIRMATION"
  | "EVIDENCE_CONFIRMED" | "PLAN_INVALIDATED" | "PLAN_RECALCULATED"
  | "APPROVED" | "DISPATCHED" | "SOURCE_VERIFIED" | "DESTINATION_VERIFIED"
  | "BATCH_MATCHED" | "COVERAGE_RESTORED" | "CARE_PROTECTED" | "CLOSED";
export interface WorkspaceData {
  scenario: Scenario;
  mode: Mode;
  caseState: CaseState;
  domainLegalActions: string[];
  authorizationStatus: "not_evaluated";
  completedActions: string[];
  limitations: string[];
  previousPlanInvalidated: boolean;
  coverageStatus: string;
  careProtected: boolean;
  careImpactExposed: Fact;
  districtStockSignals: DistrictStockSignal[];
  source: "api" | "mock";
}
export const stateStep: Record<CaseState, number> = {
  FORECASTED: 0, INTERVENTION_PROPOSED: 0, AWAITING_EVIDENCE_CONFIRMATION: 0,
  EVIDENCE_CONFIRMED: 1, PLAN_INVALIDATED: 2, PLAN_RECALCULATED: 3,
  APPROVED: 4, DISPATCHED: 5, SOURCE_VERIFIED: 6, DESTINATION_VERIFIED: 7,
  BATCH_MATCHED: 8, COVERAGE_RESTORED: 9, CARE_PROTECTED: 11, CLOSED: 12,
};
export const classificationLabels: Record<FactClass, string> = {
  REAL_PUBLIC: "Public source",
  OFFICIAL_SYSTEM_EXPORT: "Official system",
  LIVE_EXTERNAL_API: "Captured route",
  REHEARSAL_EVIDENCE: "Field evidence",
  REHEARSAL_ASSUMPTION: "Rehearsal input",
  MODEL_DERIVED: "Model-derived",
  UNKNOWN: "Unavailable",
};
export const recoverySteps = [
  "Forecasted",
  "Evidence confirmed",
  "Plan invalidated",
  "Replanned",
  "Approved",
  "Dispatched",
  "Source verified",
  "Destination verified",
  "Batch verified",
  "Coverage restored",
  "Care delivery verified",
  "Care protected",
  "Closed",
] as const;
export function canReview(role: Role) {
  return role === "FIELD REVIEWER" || role === "COORDINATOR";
}
export function canAdvance(role: Role, step: number) {
  return step >= 5 && step <= 9 ? canReview(role) : role === "COORDINATOR";
}
export function nextRecoveryStep(step: number, outcome: string = "DELIVERED") {
  if (step === 9 && outcome !== "DELIVERED") return step;
  return Math.min(step + 1, recoverySteps.length - 1);
}
