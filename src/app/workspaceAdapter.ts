import type { Fact, FactClass, Facility, WorkspaceData } from "./contracts";
import type { CandidateDto, ProvenanceDto, WorkspaceSnapshotDto } from "./apiProvider";

const positions: Record<string, [number, number]> = {
  "dhh-sundargarh": [145, 265], "sdh-bonai": [330, 207],
  "sdh-panposh": [535, 107], "chc-lahunipada": [660, 277],
  "chc-sargipali": [318, 348], "chc-laing": [821, 130],
  "chc-mangaspur": [846, 321],
};
const unknown = (why: string): Fact => ({ value: "Unavailable", classification: "UNKNOWN",
  source: "Backend workspace snapshot", explanation: why });
const fact = (value: string | number, classification: FactClass, source: string,
  explanation: string, asOf?: string): Fact => ({ value, classification, source, explanation, asOf });
const originClass = (origin: string): FactClass => origin === "official_public_data" ? "REAL_PUBLIC" :
  origin === "official_system_export" ? "OFFICIAL_SYSTEM_EXPORT" :
  origin === "live_external_api" ? "LIVE_EXTERNAL_API" : origin === "model_derived" ? "MODEL_DERIVED" :
  origin === "user_supplied_evidence" ? "REHEARSAL_EVIDENCE" : "UNKNOWN";
const provenanceFact = (value: number | null, provenance: ProvenanceDto | undefined): Fact<number | null> => ({
  value, classification: value === null ? "UNKNOWN" : originClass(provenance?.origin ?? ""),
  source: provenance?.source_ref ?? "No canonical inventory record",
  explanation: provenance?.note ?? "Facility inventory is unavailable in the backend snapshot.",
  asOf: provenance?.observed_at,
});
const facilityName = (id: string, facilities: Facility[]) => facilities.find(f => f.id === id)?.short ?? id;

export function mapWorkspaceSnapshot(dto: WorkspaceSnapshotDto): WorkspaceData {
  if (dto.metadata.mode !== "rehearsal" && dto.metadata.mode !== "operational")
    throw new Error("Unrecognized backend workspace mode");
  const recipientId = dto.active_case.recipient_id;
  const facilities: Facility[] = dto.network.facilities.map((row, index) => {
    const f = row.facility;
    const [x, y] = positions[f.id] ?? [100 + (index % 5) * 150, 100 + Math.floor(index / 5) * 150];
    const stock = row.canonical_inventory;
    return {
      id: f.id, name: f.name, short: f.short_name,
      tier: f.id.startsWith("dhh-") ? "DHH" : f.id.startsWith("sdh-") ? "SDH" : "CHC",
      block: f.block ?? "Unavailable", x, y,
      currentness: f.currentness === "current_verified" ? "Verified" : "Corroborated",
      risk: row.forecast.status === "unavailable" ? "Unknown" :
        row.forecast.coverage_breach_day !== null ? "At risk" : "Stable",
      stock: provenanceFact(stock?.quantity ?? null, stock?.provenance),
      evidenceAge: row.days_since_physical_count === null ? "No canonical count" :
        `${row.days_since_physical_count} days since count`,
      inventoryStatus: row.inventory_status === "available" ? "Available" :
        row.inventory_status === "source_stale" ? "Source stale" : "Inventory required",
      active: f.id === recipientId,
    };
  });
  const previous = dto.previous_plans.find(p => p.invalidated);
  const invalidatedId = previous?.chosen_donor_id ?? "";
  const selectedId = dto.current_plan?.chosen_donor_id ?? "";
  const donor = (c: CandidateDto) => {
    const route = dto.network.route_observations.find(r => r.from_id === c.donor_id && r.to_id === recipientId);
    const expiry = c.allocations[0]?.expires_at;
    return {
      facilityId: c.donor_id,
      distance: route?.status.toUpperCase() === "OK" && route.distance_km !== null ?
        fact(`${route.distance_km} km`, "LIVE_EXTERNAL_API", route.provider,
          "Persisted route observation; not a live traffic refresh.", route.retrieved_at) :
        fact(`${c.distance_km} km`, "MODEL_DERIVED", "Backend intervention candidate",
          "Distance used by the current deterministic plan."),
      duration: `${Math.round(Number(c.transit_hours) * 60)} min`,
      quantity: fact(c.quantity, "MODEL_DERIVED", "Backend intervention plan", "Proposed transfer quantity."),
      margin: fact(c.donor_post_transfer_margin, "MODEL_DERIVED", "Backend intervention plan", "Protected donor margin after transfer."),
      verdict: c.donor_id === invalidatedId && previous?.invalidated ? "Invalidated" :
        c.donor_id === selectedId ? "Recommended" : c.verdict === "rejected" ? "Rejected" : "Held",
      reason: c.rejection_reasons.join(", ") || c.explanations.join(" ") ||
        (c.donor_id === selectedId ? "Selected by the backend plan." : "Candidate retained for comparison."),
      expiry: expiry ? fact(new Date(expiry).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }),
        "REHEARSAL_EVIDENCE", "Backend batch allocation", "Expiry recorded in the plan.") :
        unknown("No allocated batch expiry in the current plan."),
    };
  };
  const evidence = dto.evidence.map(({ evidence: e }) => ({
    id: e.id, facilityId: e.facility_id, previous: e.canonical_quantity_at_submission,
    observed: e.observed_quantity,
    status: e.state === "confirmed" ? "Confirmed" as const : e.state === "rejected" ? "Rejected" as const : "Awaiting review" as const,
    captured: new Date(e.observed_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }),
    source: `${e.evidence_class} · ${e.captured_via}`, confidence: e.confidence,
    batch: "Unavailable", expiry: "Unavailable",
  }));
  const forecast = dto.recipient_forecast;
  const care = dto.intelligence.care_obligations.find(c => c.facility_id === recipientId);
  const programme = dto.intelligence.programme_activity[0];
  const readinessLabels: Record<string, string> = {
    facility_roster: "Facility roster", programme_activity: "Programme activity",
    district_stock_context: "District stock", facility_inventory: "Facility inventory",
    routes: "Routes", care_obligations: "Care obligations", policy: "Policy",
  };
  const readiness = Object.entries(readinessLabels).map(([key, label]) => ({
    label, state: String(dto.intelligence.readiness[key] ?? "unknown").replace(/_/g, " ").replace(/^./, c => c.toUpperCase()),
    detail: key === "care_obligations" ? "Programme-estimated aggregate; facility denominator unavailable" :
      key === "facility_inventory" ? "Facility-level canonical records only" : "Backend readiness assessment",
    classification: key === "care_obligations" ? "REHEARSAL_ASSUMPTION" as const :
      key === "facility_inventory" ? "REHEARSAL_EVIDENCE" as const : "REAL_PUBLIC" as const,
  }));
  const sources = (dto.intelligence.profile?.source_catalog ?? []).map(s => ({
    name: s.title, authority: s.publisher ?? s.authority, period: s.source_period ?? "Period unavailable",
    fields: s.supported_fields.join(", ") || s.notes || "See source", url: s.uri,
    classification: originClass(s.origin),
  }));
  const scenario = {
    id: dto.active_case.id,
    title: `${facilityName(recipientId, facilities)} · ${dto.metadata.commodity.name} continuity`,
    snapshot: new Date(dto.metadata.clock_now).toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric" }),
    commodity: dto.metadata.commodity.name, formulation: dto.metadata.commodity.form,
    facilities, donors: (dto.current_plan?.candidates ?? []).map(donor), evidence, readiness, sources,
    recipientId, selectedId, invalidatedId,
    breach: forecast.coverage_breach_day === null ? unknown("No forecast breach day is available.") :
      fact(`Day ${forecast.coverage_breach_day}`, "MODEL_DERIVED", "Backend recipient forecast", "Coverage breach day."),
    stockout: forecast.stockout_day === null ? unknown("No forecast stockout day is available.") :
      fact(`Day ${forecast.stockout_day}`, "MODEL_DERIVED", "Backend recipient forecast", "Physical stockout day."),
    exposure: care?.estimated_population_min != null && care.estimated_population_max != null ?
      fact(`${care.estimated_population_min}–${care.estimated_population_max}`, "REHEARSAL_ASSUMPTION",
        care.provenance.source_ref, care.uncertainty_note) :
      dto.recipient_care_impact.exposed_total === null ? unknown("Care exposure is unavailable.") :
      fact(dto.recipient_care_impact.exposed_total, "MODEL_DERIVED", "Backend care impact", "Aggregate exposed obligations."),
    baseline: unknown("A presentation-safe daily baseline is not supplied by the workspace snapshot."),
    demand: forecast.projected_demand_window === null ? unknown("Projected demand is unavailable.") :
      fact(forecast.projected_demand_window, "MODEL_DERIVED", "Backend recipient forecast", "Planning-window demand."),
    transfer: dto.current_plan?.candidates.find(c => c.donor_id === selectedId) ?
      fact(dto.current_plan.candidates.find(c => c.donor_id === selectedId)!.quantity,
        "MODEL_DERIVED", "Backend current plan", "Selected candidate transfer quantity.") : unknown("No selected intervention."),
    recoveredStock: unknown("No destination verification has been completed."),
    dispatchUnit: dto.metadata.commodity.physical_dispatch_unit === "UNKNOWN" ?
      unknown("Physical dispatch packaging is unknown.") :
      fact(dto.metadata.commodity.physical_dispatch_unit, "REAL_PUBLIC", "Backend commodity profile", "Physical dispatch unit."),
    programmeKpi: programme?.value != null ? fact(`${programme.value}%`, originClass(programme.provenance.origin),
      programme.provenance.source_ref, `${programme.indicator}; district aggregate, not facility denominator.`, programme.period) :
      unknown("District programme KPI is unavailable."),
    incoming: unknown("No recipient supply schedule is included in the workspace snapshot."),
  };
  return {
    scenario, mode: dto.metadata.mode === "rehearsal" ? "REHEARSAL" : "OPERATIONAL",
    caseState: dto.active_case.state,
    domainLegalActions: dto.recovery.domain_legal_actions,
    authorizationStatus: dto.recovery.authorization_status,
    completedActions: dto.recovery.completed_audit_actions,
    limitations: dto.limitations,
    previousPlanInvalidated: Boolean(previous),
    coverageStatus: dto.recovery.coverage_status, careProtected: dto.recovery.care_protected,
    careImpactExposed: dto.recipient_care_impact.exposed_total === null ?
      unknown("Recipient care impact is unavailable from the backend forecast.") :
      fact(dto.recipient_care_impact.exposed_total, "MODEL_DERIVED", "Backend recipient care impact",
        "Aggregate exposed obligations computed from the controlled rehearsal inputs."),
    districtStockSignals: dto.intelligence.stock_signals.map(signal => ({
      period: signal.period, granularity: signal.geographic_granularity,
      qualityFlags: signal.quality_flags,
      available: signal.available === null ? unknown("Public district stock signal unavailable.") :
        fact(`${signal.available} ${signal.unit}`, originClass(signal.provenance.origin), signal.source_ref,
          `${signal.geographic_granularity} aggregate only; never facility inventory. ${signal.provenance.note}`,
          signal.provenance.observed_at),
    })), source: "api",
  };
}
