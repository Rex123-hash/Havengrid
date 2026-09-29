/**
 * Environment integrity for the frontend.
 *
 *   VITE_APP_ENV          development | test | staging | judge | production   (default development)
 *   VITE_SCENARIO_SOURCE  local | backend                                       (default local in dev/test)
 *
 *   development / test    local seed permitted; backend optional
 *   staging / judge / prod backend REQUIRED · local seed FORBIDDEN · a backend bundle
 *                          that is itself synthetic is REJECTED → "unavailable" state
 *
 * Pure and dependency-free so it can be unit-tested and also evaluated at build
 * time from vite.config.ts.
 */

export type AppEnv = 'development' | 'test' | 'staging' | 'judge' | 'production';
export type SourceKind = 'local' | 'backend';
export type HavenGridMode = 'rehearsal' | 'operational';

export const PROD_LIKE: ReadonlySet<AppEnv> = new Set<AppEnv>(['staging', 'judge', 'production']);

export class ScenarioPolicyError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ScenarioPolicyError';
  }
}

export interface ScenarioPolicy {
  env: AppEnv;
  source: SourceKind;
  /** May the local seed be rendered at all? */
  syntheticPermitted: boolean;
  /** Must a backend bundle be non-synthetic to be accepted? */
  requireNonSynthetic: boolean;
  mode: HavenGridMode;
}

export function parseEnv(raw: string | undefined): AppEnv {
  const v = (raw ?? 'development').toLowerCase();
  if (v === 'development' || v === 'test' || v === 'staging' || v === 'judge' || v === 'production') return v;
  throw new ScenarioPolicyError(`Unknown VITE_APP_ENV "${raw}"`);
}

export function parseMode(raw: string | undefined): HavenGridMode {
  const v = (raw ?? 'rehearsal').toLowerCase();
  if (v === 'rehearsal' || v === 'operational') return v;
  throw new ScenarioPolicyError(`Unknown VITE_HAVENGRID_MODE "${raw}"`);
}

export function resolvePolicy(rawEnv: string | undefined, rawSource: string | undefined, rawMode?: string): ScenarioPolicy {
  const env = parseEnv(rawEnv);
  const mode = parseMode(rawMode);
  const prodLike = PROD_LIKE.has(env);
  const requested: SourceKind = (rawSource ?? '').toLowerCase() === 'backend' ? 'backend' : 'local';
  if ((prodLike || mode === 'operational') && requested !== 'backend') {
    throw new ScenarioPolicyError(
      `${mode === 'operational' ? 'VITE_HAVENGRID_MODE=operational' : `VITE_APP_ENV=${env}`} requires VITE_SCENARIO_SOURCE=backend. ` +
        'Synthetic data may test HAVEN GRID; it must not pretend to be the world HAVEN GRID observes.',
    );
  }
  return { env, source: requested, mode, syntheticPermitted: !prodLike && mode === 'rehearsal', requireNonSynthetic: prodLike || mode === 'operational' };
}

/** Is a backend bundle acceptable under this policy? Returns a reason when not. */
export function rejectBundle(policy: ScenarioPolicy, bundle: { synthetic: boolean; data_origin?: { origins: string[] } }): string | null {
  if (policy.requireNonSynthetic && bundle.synthetic) {
    return `The backend served synthetic_test data in ${policy.env}; refusing to display it as operational truth.`;
  }
  return null;
}
