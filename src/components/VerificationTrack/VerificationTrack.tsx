import { Check } from 'lucide-react';
import type { VerificationStep } from '../../data/types';
import styles from './VerificationTrack.module.css';

interface Props {
  steps: VerificationStep[];
  /** How many steps have resolved. Driven by scroll, not by a timer. */
  complete: number;
  visible: number;
}

/**
 * The verification lifecycle, as a thin track rather than a card.
 *
 * Steps resolve at uneven intervals on purpose. A stepper that arrives
 * pre-completed, or completes evenly, quietly asserts "this always works" —
 * which contradicts the sentence printed above it.
 */
export function VerificationTrack({ steps, complete, visible }: Props) {
  const pct = steps.length > 1 ? (Math.max(0, complete - 1) / (steps.length - 1)) * 100 : 0;

  return (
    <ol className={styles.track} style={{ opacity: visible }} aria-label="Verification lifecycle">
      <span className={styles.spine} aria-hidden="true" />
      <span className={styles.spineFill} style={{ height: `${pct}%` }} aria-hidden="true" />

      {steps.map((step, i) => {
        const done = i < complete;
        const active = i === complete;
        return (
          <li key={step.key} className={styles.step} data-done={done} data-active={active}>
            <span className={styles.dot} aria-hidden="true">
              {done && <Check size={9} strokeWidth={3} />}
            </span>
            <span className={styles.label}>
              <b>{step.label}</b>
              <i>{step.detail}</i>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
