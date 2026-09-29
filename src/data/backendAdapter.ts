/**
 * Backend → LandingScenario adapter (Phase 0).
 *
 * AUTHORITY RULES
 *   Backend-authoritative (read from the bundle, never from local seed):
 *     inventory · demand · gap · coverage breach · stockout · care exposure ·
 *     candidate feasibility/ranking/verdict · selected donor · transfer quantity ·
 *     evidence state · corrected canonical inventory · revised plan ·
 *     verification outcomes · protected-care count · inventory freshness.
 *   Local-only (presentational): layout coordinates, cohort labels/detail prose,
 *     the illustrative register rows, horizon stops, verification step labels.
 *
 * A missing backend field is a contract violation and throws — it is never
 * papered over with the local seed's stale value.
 */

import type { CandidateIntervention, CareCohortKey, Facility, LandingScenario, VerificationStep } from './types';

export class ScenarioContractError extends Error {
  constructor(public readonly missing: string) {
    super(`Backend scenario bundle is missing required field: ${missing}`);
    this.name = 'ScenarioContractError';
  }
}

/* ── minimal bundle typing (only what the adapter reads) ──────────────── */

interface BForecast {
  status: 'forecast' | 'unavailable';
  starting_inventory: number | null;
  coverage_breach_day: number | null;
  stockout_day: number | null;
  projected_demand_window: number | null;
  gap_window: number | null;
  projection: { day: number; credit: number }[];
}
interface BImpact {
  scheduled_in_window: number;
  exposed_total: number;
  exposed_by_category: Record<CareCategoryKey, number>;
  unserved_total: number;
}
type CareCategoryKey = 'paediatric' | 'maternal' | 'scheduled';
interface BCareEvent {
  id: string;
  category: CareCategoryKey;
  day: number;
  exposed: boolean;
  unserved: boolean;
}
interface BCandidate {
  donor_id: string;
  donor_name: string;
  quantity: number;
  transferable: number;
  donor_protection_window_days: number;
  donor_coverage_breach_day: number | null;
  distance_km: string | number;
  transit_hours: string | number;
  arrival_day: number;
  recipient_post_transfer_breach_day: number | null;
  allocations: { batch_id: string; quantity: number; expires_at: string | null }[];
  expiry_relief: boolean;
  feasible: boolean;
  rejection_reasons: string[];
  explanations: string[];
  rank: number | null;
  verdict: 'chosen' | 'held' | 'rejected';
}
interface BPlan {
  id: string;
  chosen_donor_id: string | null;
  candidates: BCandidate[];
  hold_through_day: number;
  invalidated: boolean;
}
interface BEvidence {
  facility_id: string;
  observed_quantity: number;
  confidence: string | number;
  captured_via: string;
  state: string;
  canonical_quantity_at_submission: number;
}
export interface ScenarioBundle {
  synthetic: boolean;
  district: { name: string; region: string; policy: { planning_window_days: number; horizon_days: number; min_cover_days: number } };
  item: { name: string; form: string; unit: string };
  facilities: { id: string; name: string; short_name: string; tier: Facility['tier']; x: number; y: number }[];
  links: { from_id: string; to_id: string }[];
  forecasts: Record<string, BForecast>;
  care_impacts: Record<string, BImpact>;
  focus_facility_id: string;
  focus_care_events: BCareEvent[];
  case: { id: string; state: string; originally_exposed_ids: string[]; care_protected_count: number | null };
  plan: BPlan | null;
  previous_plans: BPlan[];
  evidence: BEvidence[];
  verifications: { kind: string; expected: string; observed: string | null; outcome: string }[];
  reconciliations: { outcome: string; protected_count: number }[];
  inventory_freshness: Record<string, number | null>;
}

function req<T>(value: T | undefined | null, path: string): T {
  if (value === undefined || value === null) throw new ScenarioContractError(path);
  return value;
}

const num = (v: string | number) => (typeof v === 'number' ? v : Number(v));

/* ── candidates ────────────────────────────────────────────────────────── */

function justifications(c: BCandidate, focusName: string, protectedCount: number): string[] {
  const lines: string[] = [];
  const after = c.recipient_post_transfer_breach_day;
  lines.push(after === null
    ? `Prevents the projected coverage breach — ${focusName} stays covered through the forecast horizon`
    : `Moves the coverage breach to day ${after}`);
  lines.push(`Donor remains safe through its ${c.donor_protection_window_days}-day protection window — ${c.transferable} transferable, ${c.quantity} released`);
  if (c.expiry_relief) {
    const b = c.allocations.find((a) => a.expires_at);
    lines.push(`Relieves expiry pressure — batch ${b?.batch_id ?? ''} would otherwise expire inside the horizon`);
  }
  lines.push(`Arrives on day ${c.arrival_day}, before the coverage breach`);
  lines.push(`Protects ${protectedCount} exposed care events`);
  return lines;
}

function mapCandidate(c: BCandidate, plan: BPlan, focusName: string, protectedCount: number): CandidateIntervention {
  const base: CandidateIntervention = {
    id: `${plan.id}:${c.donor_id}`,
    facilityId: c.donor_id,
    facilityName: c.donor_name,
    transferable: c.transferable,
    distanceKm: num(c.distance_km),
    transitHours: num(c.transit_hours),
    verdict: c.verdict,
    reason: c.feasible
      ? c.verdict === 'chosen'
        ? `Ranked first${c.expiry_relief ? ' — relieves expiry pressure' : ''}; transit ${num(c.transit_hours)} h.`
        : `Feasible, ranked ${c.rank}${c.expiry_relief ? '' : ' — no expiry pressure to relieve'}; transit ${num(c.transit_hours)} h.`
      : c.explanations.join(' '),
  };
  if (c.verdict === 'chosen') {
    base.transferUnits = c.quantity;
    base.justifications = justifications(c, focusName, protectedCount);
    if (c.recipient_post_transfer_breach_day !== null) base.resultingBreachDay = c.recipient_post_transfer_breach_day;
  }
  return base;
}

/* ── main mapper ───────────────────────────────────────────────────────── */

/**
 * Three backend snapshots, one per story beat the page tells:
 *   initial   — after `propose`:  pre-correction network, plan-001 (CHC D chosen)
 *   corrected — after `confirm`:  CHC D canonical 126, plan-001 invalidated, plan-002 (CHC B)
 *   closed    — after `close`:    verifications + reconciliation (protected count)
 * Reading one bundle would show Bhatpar's post-reconciliation state as the opening frame.
 */
export interface DemoSnapshots {
  initial: ScenarioBundle;
  corrected: ScenarioBundle;
  closed: ScenarioBundle;
}

export function mapBundleToScenario(snap: DemoSnapshots, local: LandingScenario): LandingScenario {
  const b = snap.initial;
  for (const [k, v] of Object.entries(snap)) if (v.synthetic !== true) throw new ScenarioContractError(`${k}.synthetic (must be true in Phase 0)`);
  const focusId = req(b.focus_facility_id, 'focus_facility_id');
  const focusF = req(b.forecasts[focusId], `forecasts.${focusId}`);
  const focusI = req(b.care_impacts[focusId], `care_impacts.${focusId}`);
  const focusName = req(b.facilities.find((f) => f.id === focusId), 'facilities[focus]').name;

  const initialPlan = req(b.plan, 'initial.plan (case not yet proposed)');
  const revisedPlan = req(snap.corrected.plan, 'corrected.plan');
  if (!snap.corrected.previous_plans.some((p) => p.id === initialPlan.id && p.invalidated)) {
    throw new ScenarioContractError('corrected.previous_plans[initial].invalidated');
  }
  const evidence = req(snap.corrected.evidence[0], 'corrected.evidence[0]');

  const lastRec = req(snap.closed.reconciliations[snap.closed.reconciliations.length - 1], 'closed.reconciliations[last]');
  if (lastRec.outcome !== 'care_protected') throw new ScenarioContractError(`closed.reconciliations[last].outcome === 'care_protected' (got ${lastRec.outcome})`);
  const protectedCount = lastRec.protected_count;

  const firstCreditDay = focusF.projection.find((r) => r.credit > 0)?.day;

  const facilities: Facility[] = b.facilities.map((f) => {
    const fc = req(b.forecasts[f.id], `forecasts.${f.id}`);
    const ci = req(b.care_impacts[f.id], `care_impacts.${f.id}`);
    const fresh = b.inventory_freshness[f.id];
    return {
      id: f.id, name: f.name, short: f.short_name, tier: f.tier, x: f.x, y: f.y,
      breachDay: fc.coverage_breach_day,
      forecastStatus: fc.status,
      careEventsExposed: ci.exposed_total,
      // null freshness = no canonical record; render as maximally stale rather than fresh.
      daysSinceVerified: fresh ?? 99,
    };
  });

  const cohortLocal = new Map(local.careCohorts.map((c) => [c.key, c]));
  const scheduledByCat = (key: CareCategoryKey) => b.focus_care_events.filter((e) => e.category === key && e.day <= b.district.policy.planning_window_days).length;
  const careCohorts = (['paediatric', 'maternal', 'scheduled'] as CareCategoryKey[]).map((key) => ({
    key: key as CareCohortKey,
    label: cohortLocal.get(key)?.label ?? key,
    count: req(focusI.exposed_by_category[key], `care_impacts.${focusId}.exposed_by_category.${key}`),
    scheduled: scheduledByCat(key),
    detail: cohortLocal.get(key)?.detail ?? '',
  }));

  req(initialPlan.candidates.find((c) => c.verdict === 'chosen'), 'initial plan chosen candidate');
  const revisedChosen = req(revisedPlan.candidates.find((c) => c.verdict === 'chosen'), 'revised plan chosen candidate');
  const donorName = req(b.facilities.find((f) => f.id === evidence.facility_id), 'evidence facility').name;
  const donorForecastBefore = req(b.forecasts[evidence.facility_id], `initial.forecasts.${evidence.facility_id}`);
  const donorForecastAfter = req(snap.corrected.forecasts[evidence.facility_id], `corrected.forecasts.${evidence.facility_id}`);
  // The cascade is DERIVED: every facility whose coverage breach changed when the correction landed.
  const cascadeFacilityIds = b.facilities
    .map((f) => f.id)
    .filter((id) => b.forecasts[id]?.coverage_breach_day !== snap.corrected.forecasts[id]?.coverage_breach_day);

  const vSource = req(snap.closed.verifications.find((v) => v.kind === 'source' && v.outcome === 'verified'), 'closed.verifications[source=verified]');
  const vDest = req(snap.closed.verifications.find((v) => v.kind === 'destination' && v.outcome === 'verified'), 'closed.verifications[destination=verified]');
  const verification: VerificationStep[] = local.verification.map((step) => {
    const detail: Record<string, string> = {
      proposed: 'Plan generated from corrected inventory',
      approved: 'District coordinator · two-key authorisation',
      dispatched: `${revisedChosen.donor_name} — ${revisedChosen.quantity} units in transit`,
      source: `${revisedChosen.donor_name} stock verified at ${vSource.observed} (expected ${vSource.expected})`,
      destination: `${focusName} stock verified at ${vDest.observed} (expected ${vDest.expected})`,
      batch: `${revisedChosen.allocations.map((a) => a.batch_id).join(', ')} confirmed at both ends`,
      care: `${protectedCount} exposed care events now covered`,
      closed: 'Resilience loop closed',
    };
    return { ...step, detail: detail[step.key] ?? step.detail };
  });

  return {
    district: b.district.name,
    region: b.district.region,
    facilityCount: b.facilities.length,
    scheduledCareEvents: Object.values(b.care_impacts).reduce((n, c) => n + c.scheduled_in_window, 0),
    focusFacilityId: focusId,
    item: {
      name: b.item.name,
      form: b.item.form,
      unit: b.item.unit,
      currentStock: req(focusF.starting_inventory, `forecasts.${focusId}.starting_inventory`),
      projectedDemand: req(focusF.projected_demand_window, `forecasts.${focusId}.projected_demand_window`),
      demandWindowDays: b.district.policy.planning_window_days,
      replenishmentEtaDays: req(firstCreditDay, `forecasts.${focusId}.projection[credit>0]`) - 1,
      coverageBreachDay: req(focusF.coverage_breach_day, `forecasts.${focusId}.coverage_breach_day`),
      stockoutDay: focusF.stockout_day,
      minCoverDays: req(b.district.policy.min_cover_days, 'district.policy.min_cover_days'),
    },
    facilities,
    links: b.links.map((l) => ({ from: l.from_id, to: l.to_id })),
    careCohorts,
    careExposure: {
      scheduled: req(focusI.scheduled_in_window, `care_impacts.${focusId}.scheduled_in_window`),
      exposed: focusI.exposed_total,
      unserved: req(focusI.unserved_total, `care_impacts.${focusId}.unserved_total`),
    },
    totalCareEventsExposed: focusI.exposed_total,
    candidates: initialPlan.candidates.map((c) => mapCandidate(c, initialPlan, focusName, protectedCount)),
    realityLens: {
      facilityId: evidence.facility_id,
      facilityName: donorName,
      digitalRecord: evidence.canonical_quantity_at_submission,
      fieldEvidence: evidence.observed_quantity,
      confidence: num(evidence.confidence),
      capturedVia: evidence.captured_via,
      registerRows: local.realityLens.registerRows,           // illustrative visual only
      breachDayBefore: donorForecastBefore.coverage_breach_day,
      breachDayAfter: donorForecastAfter.coverage_breach_day,
      cascadeFacilityIds,
      cascadeBreachDays: Object.fromEntries(cascadeFacilityIds.map((id) => [id, snap.corrected.forecasts[id]?.coverage_breach_day ?? null])),
    },
    replan: mapCandidate(revisedChosen, revisedPlan, focusName, protectedCount),
    verification,
    horizonStops: local.horizonStops,
  };
}

/* ── demo replay ───────────────────────────────────────────────────────── */

async function post(path: string, body?: unknown) {
  const r = await fetch(path, { method: 'POST', headers: { 'content-type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
  if (!r.ok) throw new Error(`${path} → ${r.status} ${await r.text()}`);
  return r.json();
}

/** A run id makes every replay command idempotent on the backend: a duplicate
 *  POST with the same command_id is acknowledged, not re-applied. */
function newRunId(): string {
  return `replay-${Date.now().toString(36)}-${Math.floor(Math.random() * 1e6).toString(36)}`;
}

/**
 * Drives the backend through the full Sundargarh story so that every beat the
 * landing page tells has a real derived record behind it. Explicit and
 * idempotent: reset first, then replay. Used only when the backend source is
 * enabled.
 */
async function bundle(): Promise<ScenarioBundle> {
  const r = await fetch('/api/demo/scenario');
  if (!r.ok) throw new Error(`/api/demo/scenario → ${r.status}`);
  return r.json();
}

export async function replayDemo(): Promise<DemoSnapshots> {
  if ((import.meta.env.VITE_HAVENGRID_MODE as string | undefined)?.toLowerCase() === 'operational') {
    throw new Error('Rehearsal replay is disabled when VITE_HAVENGRID_MODE=operational.');
  }
  const run = newRunId();
  // Discover the case from the backend; never hardcode workflow identity.
  const reset = await post('/api/demo/reset');
  const CASE: string = reset.id;
  const adv = (action: string, extra: Record<string, unknown> = {}) =>
    post(`/api/cases/${CASE}/advance`, { action, command_id: `${run}:${action}`, ...extra });

  await adv('propose');
  const initial = await bundle();
  const ev = await post(`/api/cases/${CASE}/evidence`, { facility_id: 'chc-d', observed_quantity: 126, confidence: '0.83', command_id: `${run}:evidence` });
  await post(`/api/cases/${CASE}/evidence/${ev.id}/confirm`, { actor: 'district-pharmacist', command_id: `${run}:confirm` });
  const corrected = await bundle();
  await adv('approve', { actor: 'district-medical-officer' });
  await adv('dispatch', { actor: 'chc-b-pharmacist' });
  await adv('verify_source', { observed_quantity: 260, actor: 'chc-b-pharmacist' });
  await adv('verify_destination', { observed_quantity: 223, actor: 'bhatpar-pharmacist' });
  await adv('verify_batch', { observed_batch_ids: ['AMX-2403-B'], observed_quantity: 80, actor: 'bhatpar-pharmacist' });
  await adv('reconcile');
  await adv('close', { actor: 'district-medical-officer' });
  const closed = await bundle();
  return { initial, corrected, closed };
}
