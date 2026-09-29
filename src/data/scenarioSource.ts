/**
 * Scenario source switch, governed by `scenarioPolicy`.
 *
 *   local    — the seeded landingScenario.ts (development/test only)
 *   backend  — replay the Sundargarh story on the backend and render its derived state
 *
 * There is NO fallback from backend to local. If the backend is unavailable,
 * degraded, or serves data the policy rejects, the page shows an honest
 * "unavailable" state. In development a failure is loud (the error is shown),
 * never quietly replaced by the old seed.
 */

import { useEffect, useState } from 'react';
import { landingScenario } from './landingScenario';
import { mapBundleToScenario, replayDemo, type DemoSnapshots } from './backendAdapter';
import { rejectBundle, resolvePolicy, type ScenarioPolicy } from './scenarioPolicy';
import type { LandingScenario } from './types';

export const policy: ScenarioPolicy = resolvePolicy(
  import.meta.env.VITE_APP_ENV as string | undefined,
  import.meta.env.VITE_SCENARIO_SOURCE as string | undefined,
  import.meta.env.VITE_HAVENGRID_MODE as string | undefined,
);

export type ScenarioStatus =
  | { status: 'ready'; scenario: LandingScenario; source: 'local' | 'backend'; policy: ScenarioPolicy }
  | { status: 'loading'; policy: ScenarioPolicy }
  | { status: 'unavailable'; reason: string; error?: Error; policy: ScenarioPolicy };

/**
 * One replay per page load, shared by every consumer. React StrictMode
 * double-invokes effects in development; two concurrent replays would race the
 * backend's single case (reset → propose → 409). The in-flight promise is the
 * dedupe; a failure clears it so a retry is possible.
 */
let inflight: Promise<DemoSnapshots> | null = null;
export function replayOnce(run: () => Promise<DemoSnapshots> = replayDemo): Promise<DemoSnapshots> {
  if (!inflight) {
    inflight = run().catch((e) => {
      inflight = null;
      throw e;
    });
  }
  return inflight;
}

/** Test seam. */
export function _resetReplayForTests(): void {
  inflight = null;
}

export function useScenario(): ScenarioStatus {
  const [state, setState] = useState<ScenarioStatus>(() =>
    policy.source === 'local'
      ? { status: 'ready', scenario: landingScenario, source: 'local', policy }
      : { status: 'loading', policy },
  );

  useEffect(() => {
    if (policy.source !== 'backend') return;
    let alive = true;
    if (policy.mode === 'operational') {
      // Operational page load is read-only. The narrative replay remains a
      // rehearsal-only adapter until the UI is migrated to official bundles.
      fetch('/api/demo/scenario')
        .then(async (r) => {
          if (!r.ok) throw new Error(`/api/demo/scenario → ${r.status}`);
          return r.json();
        })
        .then((bundle: { synthetic: boolean; data_origin?: { origins: string[] } }) => {
          if (!alive) return;
          const reason = rejectBundle(policy, bundle) ?? 'Operational read-only mode is connected; the landing narrative has not been migrated to official-data bundles yet.';
          setState({ status: 'unavailable', reason, policy });
        })
        .catch((error: Error) => {
          if (alive) setState({ status: 'unavailable', reason: error.message, error, policy });
        });
      return () => {
        alive = false;
      };
    }
    replayOnce()
      .then((snap) => {
        if (!alive) return;
        const reason = rejectBundle(policy, snap.initial);
        if (reason) {
          setState({ status: 'unavailable', reason, policy });
          return;
        }
        setState({ status: 'ready', scenario: mapBundleToScenario(snap, landingScenario), source: 'backend', policy });
      })
      .catch((error: Error) => {
        if (alive) setState({ status: 'unavailable', reason: error.message, error, policy });
      });
    return () => {
      alive = false;
    };
  }, []);

  return state;
}
