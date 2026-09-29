import { Navbar } from '../Navbar/Navbar';
import type { ScenarioStatus } from '../../data/scenarioSource';
import styles from './ScenarioGate.module.css';

/**
 * Loading / unavailable states for the scenario.
 *
 * "Unavailable" is a first-class outcome, not an error page to apologise for:
 * it means the environment forbids synthetic data and no operational source
 * could be reached. Nothing invented is shown.
 */
export function ScenarioGate({ state }: { state: Exclude<ScenarioStatus, { status: 'ready' }> }) {
  const loading = state.status === 'loading';
  return (
    <>
      <Navbar />
      <main className={styles.gate} role={loading ? 'status' : 'alert'} aria-live="polite">
        <div className={styles.card} data-loading={loading}>
          <span className={`eyebrow ${styles.eyebrow}`}>{loading ? 'Connecting to the district' : 'Operational data unavailable'}</span>
          <h1 className={styles.title}>{loading ? 'Loading the current network state…' : 'No operational data source is available.'}</h1>
          {loading ? (
            <p className={styles.body}>Replaying the scenario on the backend and reading its derived state.</p>
          ) : (
            <>
              <p className={styles.body}>
                This deployment is <b className="num">{state.policy.env}</b>, where synthetic demonstration data is not permitted to stand in for
                the world the system observes. Nothing has been substituted.
              </p>
              <p className={styles.reason}>{state.reason}</p>
            </>
          )}
          <p className={styles.meta}>source policy: {state.policy.source} · synthetic permitted: {state.policy.syntheticPermitted ? 'yes' : 'no'}</p>
        </div>
      </main>
    </>
  );
}
