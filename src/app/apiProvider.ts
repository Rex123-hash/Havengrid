import type { CaseState, WorkspaceData, WorkspaceProvider } from "./contracts";
import { mapWorkspaceSnapshot } from "./workspaceAdapter";

export interface ProvenanceDto { source_ref: string; origin: string; note: string; observed_at: string; }
export interface InventoryDto { quantity: number; provenance: ProvenanceDto; }
export interface ForecastDto {
  status: "forecast" | "unavailable"; coverage_breach_day: number | null;
  stockout_day: number | null; projected_demand_window: number | null;
  starting_inventory: number | null; drivers: string[]; as_of: string;
}
export interface CareImpactDto { status: "forecast" | "unavailable"; exposed_total: number | null; }
export interface FacilityDto {
  facility: { id: string; name: string; short_name: string; tier: string; block: string | null;
    currentness: string; x: number; y: number; coordinate_source: string; };
  inventory_status: "available" | "source_stale" | "inventory_required";
  canonical_inventory: InventoryDto | null; forecast: ForecastDto; care_impact: CareImpactDto;
  days_since_physical_count: number | null;
}
export interface CandidateDto {
  donor_id: string; quantity: number; distance_km: string; transit_hours: string;
  donor_inventory: number | null; donor_post_transfer_margin: number;
  feasible: boolean; verdict: string; rejection_reasons: string[]; explanations: string[];
  allocations: { batch_id: string; expires_at: string | null }[];
}
export interface PlanDto {
  id: string; chosen_donor_id: string | null; invalidated: boolean;
  candidates: CandidateDto[];
}
export interface EvidenceDto {
  id: string; facility_id: string; observed_quantity: number;
  canonical_quantity_at_submission: number | null; confidence: string;
  captured_via: string; evidence_class: string; observed_at: string;
  state: "awaiting_confirmation" | "confirmed" | "rejected";
}
export interface WorkspaceSnapshotDto {
  metadata: { district: { id: string; name: string }; mode: string; designation: string;
    commodity: { id: string; name: string; form: string; physical_dispatch_unit: string };
    clock_now: string; data_origin: { source_id: string; origins: string[] } };
  network: { facilities: FacilityDto[]; route_observations: {
    from_id: string; to_id: string; status: string; provider: string;
    distance_km: string | null; duration_hours: string | null; retrieved_at: string;
  }[] };
  active_case: { id: string; state: CaseState; recipient_id: string; item_id: string };
  recipient_forecast: ForecastDto;
  recipient_care_impact: CareImpactDto;
  current_plan: PlanDto | null; previous_plans: PlanDto[];
  evidence: { evidence: EvidenceDto; current_canonical_quantity: number | null }[];
  recovery: { state: CaseState; domain_legal_actions: string[];
    authorization_status: "not_evaluated"; completed_audit_actions: string[];
    coverage_status: string; care_protected: boolean };
  intelligence: { readiness: Record<string, string | string[]>;
    stock_signals: { id: string; item_id: string; period: string; unit: string;
      geographic_granularity: string; available: string | null; quality_flags: string[];
      source_ref: string; provenance: ProvenanceDto }[];
    programme_activity: { indicator: string; value: string | null; period: string;
      provenance: ProvenanceDto }[];
    care_obligations: { facility_id: string; expected_attendance: number; estimated_population_min: number | null;
      estimated_population_max: number | null; facility_denominator_status: string;
      numeric_basis_origin: string; uncertainty_note: string; provenance: ProvenanceDto }[];
    profile: { source_catalog: { title: string; authority: string; publisher?: string; uri: string;
      source_period?: string; supported_fields: string[]; origin: string; notes: string }[] } | null };
  limitations: string[];
}

export class ApiError extends Error {
  constructor(public readonly kind: "network" | "not_found" | "conflict" | "forbidden" | "validation" | "unavailable",
              public readonly status: number | null, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

function isSnapshot(value: unknown): value is WorkspaceSnapshotDto {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  const meta = v.metadata as Record<string, unknown> | undefined;
  const network = v.network as Record<string, unknown> | undefined;
  const current = v.active_case as Record<string, unknown> | undefined;
  const recovery = v.recovery as Record<string, unknown> | undefined;
  return Boolean(meta && typeof meta.clock_now === "string" && meta.commodity &&
    network && Array.isArray(network.facilities) && current && typeof current.id === "string" &&
    recovery && Array.isArray(recovery.domain_legal_actions) &&
    Array.isArray(v.evidence) && Array.isArray(v.previous_plans) && v.intelligence);
}

export class ApiDataProvider implements WorkspaceProvider {
  readonly districts = ["Sundargarh"];
  constructor(private readonly baseUrl = import.meta.env.VITE_API_BASE_URL || "",
              private readonly transport: typeof fetch = fetch) {}

  private async request(path: string, init?: RequestInit): Promise<unknown> {
    let response: Response;
    try {
      const transport = this.transport;
      response = await transport(`${this.baseUrl.replace(/\/$/, "")}${path}`, init);
    } catch (error) {
      if (import.meta.env.DEV) console.error("HAVEN API network failure", error);
      throw new ApiError("network", null, "Cannot reach the HAVEN backend. No rehearsal values were substituted.");
    }
    if (!response.ok) {
      const kind = response.status === 404 ? "not_found" : response.status === 409 ? "conflict" :
        response.status === 403 ? "forbidden" : response.status === 422 ? "validation" : "unavailable";
      if (import.meta.env.DEV) console.error("HAVEN API request failed", response.status, path);
      const message = kind === "conflict" ? "The case changed on the server. Current data was refreshed." :
        kind === "forbidden" ? "This action is not permitted by the backend." :
        kind === "validation" ? "The backend could not accept this evidence decision." :
        kind === "not_found" ? "The requested workspace or evidence was not found." :
        "Operational data is temporarily unavailable. No rehearsal values were substituted.";
      throw new ApiError(kind, response.status, message);
    }
    try { return await response.json() as unknown; }
    catch (error) {
      if (import.meta.env.DEV) console.error("HAVEN API invalid JSON", error);
      throw new ApiError("validation", response.status, "The backend returned an unreadable workspace response.");
    }
  }

  async load(districtId: string): Promise<WorkspaceData> {
    const dto = await this.request(`/api/districts/${encodeURIComponent(districtId)}/workspace`);
    if (!isSnapshot(dto)) throw new ApiError("validation", null, "The backend workspace response was incomplete.");
    try { return mapWorkspaceSnapshot(dto); }
    catch (error) {
      if (import.meta.env.DEV) console.error("HAVEN workspace contract mismatch", error);
      throw new ApiError("validation", null, "The backend workspace response could not be interpreted.");
    }
  }
  async confirmEvidence(caseId: string, evidenceId: string): Promise<void> {
    await this.decision(caseId, evidenceId, "confirm");
  }
  async rejectEvidence(caseId: string, evidenceId: string): Promise<void> {
    await this.decision(caseId, evidenceId, "reject");
  }
  private async decision(caseId: string, evidenceId: string, action: "confirm" | "reject") {
    await this.request(`/api/cases/${encodeURIComponent(caseId)}/evidence/${encodeURIComponent(evidenceId)}/${action}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ actor: "workspace-preview-reviewer" }),
    });
  }
}
