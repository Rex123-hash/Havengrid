import { describe, expect, it } from 'vitest';
import snapshots from './__fixtures__/backend-snapshots.json';
import { ScenarioContractError, mapBundleToScenario, type DemoSnapshots } from './backendAdapter';
import { landingScenario } from './landingScenario';

const snap = snapshots as unknown as DemoSnapshots;

describe('backend → LandingScenario adapter', () => {
  const s = mapBundleToScenario(snap, landingScenario);

  it('reads every semantic field from the backend, not the seed', () => {
    expect(s.item).toMatchObject({ currentStock: 143, projectedDemand: 191, coverageBreachDay: 8, stockoutDay: 11, replenishmentEtaDays: 13, minCoverDays: 3 });
    expect(s.careExposure).toEqual({ scheduled: 23, exposed: 13, unserved: 6 });
    expect(s.careCohorts.map((c) => [c.key, c.count, c.scheduled])).toEqual([['paediatric', 7, 11], ['maternal', 4, 7], ['scheduled', 2, 5]]);
    expect(s.totalCareEventsExposed).toBe(13);
    expect(s.scheduledCareEvents).toBe(86);
  });

  it('takes the initial plan from the first snapshot and the revised plan from the corrected one', () => {
    expect(s.candidates.find((c) => c.verdict === 'chosen')?.facilityId).toBe('chc-d');
    expect(s.candidates.map((c) => [c.facilityId, c.verdict])).toEqual([
      ['chc-d', 'chosen'], ['chc-b', 'held'], ['warehouse', 'held'], ['lahunipada', 'rejected'], ['kansbahal', 'rejected'],
    ]);
    expect(s.replan).toMatchObject({ facilityId: 'chc-b', transferUnits: 80, verdict: 'chosen' });
    expect(s.replan.justifications?.some((j) => j.includes('Protects 13'))).toBe(true);
  });

  it('derives the correction cascade from forecast deltas — CHC D only, no Remed', () => {
    expect(s.realityLens).toMatchObject({ facilityId: 'chc-d', digitalRecord: 286, fieldEvidence: 126, confidence: 0.83, breachDayBefore: null, breachDayAfter: 12 });
    expect(s.realityLens.cascadeFacilityIds).toEqual(['chc-d']);
    expect(s.realityLens.cascadeBreachDays).toEqual({ 'chc-d': 12 });
  });

  it('renders verification details from verified records and the protected count from reconciliation', () => {
    const byKey = Object.fromEntries(s.verification.map((v) => [v.key, v.detail]));
    expect(byKey.source).toBe('CHC B · Hemgir stock verified at 260 (expected 260)');
    expect(byKey.destination).toBe('Bhatpar PHC stock verified at 223 (expected 223)');
    expect(byKey.batch).toContain('AMX-2403-B');
    expect(byKey.care).toBe('13 exposed care events now covered');
  });

  it('keeps only presentational fields from the local seed', () => {
    expect(s.realityLens.registerRows).toBe(landingScenario.realityLens.registerRows);
    expect(s.horizonStops).toEqual(landingScenario.horizonStops);
    expect(s.facilities.map((f) => f.x)).toEqual(snap.initial.facilities.map((f) => f.x));
  });

  it('marks unknown inventory as maximally stale, never fresh', () => {
    expect(s.facilities.find((f) => f.id === 'kutra')).toMatchObject({ forecastStatus: 'unavailable', daysSinceVerified: 99, breachDay: null });
  });

  it('fails loudly when a backend-authoritative field is missing', () => {
    const broken = structuredClone(snap) as DemoSnapshots;
    delete (broken.initial.forecasts.bhatpar as Partial<typeof broken.initial.forecasts.bhatpar>).coverage_breach_day;
    expect(() => mapBundleToScenario(broken, landingScenario)).toThrow(ScenarioContractError);
    expect(() => mapBundleToScenario(broken, landingScenario)).toThrow(/coverage_breach_day/);
  });

  it('fails loudly when the story has not been replayed', () => {
    const early = structuredClone(snap) as DemoSnapshots;
    early.corrected.evidence = [];
    expect(() => mapBundleToScenario(early, landingScenario)).toThrow(/evidence/);
    const noPlan = structuredClone(snap) as DemoSnapshots;
    noPlan.initial.plan = null;
    expect(() => mapBundleToScenario(noPlan, landingScenario)).toThrow(/plan/);
  });

  it('refuses a reconciliation that did not reach care_protected', () => {
    const bad = structuredClone(snap) as DemoSnapshots;
    bad.closed.reconciliations[bad.closed.reconciliations.length - 1].outcome = 'still_exposed';
    expect(() => mapBundleToScenario(bad, landingScenario)).toThrow(/care_protected/);
  });
});
