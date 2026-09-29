import { describe, expect, it } from 'vitest';
import { PROD_LIKE, ScenarioPolicyError, rejectBundle, resolvePolicy } from './scenarioPolicy';

describe('environment integrity policy', () => {
  it('defaults to development + local', () => {
    const p = resolvePolicy(undefined, undefined);
    expect(p).toMatchObject({ env: 'development', source: 'local', syntheticPermitted: true, requireNonSynthetic: false });
  });

  it.each(['development', 'test'])('%s permits the local seed and optional backend', (env) => {
    expect(resolvePolicy(env, 'local').syntheticPermitted).toBe(true);
    expect(resolvePolicy(env, 'backend').source).toBe('backend');
  });

  it.each([...PROD_LIKE])('%s forbids the local seed outright', (env) => {
    expect(() => resolvePolicy(env, 'local')).toThrow(ScenarioPolicyError);
    expect(() => resolvePolicy(env, undefined)).toThrow(ScenarioPolicyError);
    const p = resolvePolicy(env, 'backend');
    expect(p).toMatchObject({ source: 'backend', syntheticPermitted: false, requireNonSynthetic: true });
  });

  it('rejects unknown environments', () => {
    expect(() => resolvePolicy('prod', 'backend')).toThrow(/Unknown VITE_APP_ENV/);
  });

  it.each([...PROD_LIKE])('%s rejects a synthetic backend bundle', (env) => {
    const p = resolvePolicy(env, 'backend');
    expect(rejectBundle(p, { synthetic: true })).toMatch(/synthetic_test/);
    expect(rejectBundle(p, { synthetic: false })).toBeNull();
  });

  it('development accepts a synthetic backend bundle', () => {
    expect(rejectBundle(resolvePolicy('development', 'backend'), { synthetic: true })).toBeNull();
  });

  it('operational mode requires a backend and marks bundles non-synthetic', () => {
    const p = resolvePolicy('development', 'backend', 'operational');
    expect(p).toMatchObject({ mode: 'operational', requireNonSynthetic: true, syntheticPermitted: false });
    expect(() => resolvePolicy('development', 'local', 'operational')).toThrow(/requires VITE_SCENARIO_SOURCE=backend/);
  });
});
