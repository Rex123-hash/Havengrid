import { Check, ScanLine } from 'lucide-react';
import { copy } from '../../brand/brand.config';
import type { RealityLensEvidence } from '../../data/types';
import styles from './RealityLens.module.css';

interface Props {
  evidence: RealityLensEvidence;
  /** Flipped by the story only after the confirmation threshold is crossed. */
  confirmed: boolean;
  onConfirm?: () => void;
}

/**
 * Reality Lens.
 *
 * The whole point of this component is the gate at the bottom: the extraction
 * is automatic, the correction is not. Until `confirmed` is true the network
 * must not have moved — so this component owns no side effects at all. It
 * renders evidence and a pending state; the story decides when a human agreed.
 */
export function RealityLens({ evidence, confirmed, onConfirm }: Props) {
  const delta = evidence.fieldEvidence - evidence.digitalRecord;

  return (
    <div className={styles.lens}>
      <div className={styles.grid}>
        {/* The evidence artefact: a transcribed ward stock register. */}
        <figure className={styles.register} aria-label="Photographed ward stock register">
          <figcaption className={styles.registerHead}>STOCK REGISTER</figcaption>
          <div className={styles.registerCols}>
            <span>DATE</span>
            <span>OUT</span>
            <span>BAL</span>
          </div>
          {evidence.registerRows.map((r) => (
            <div key={r.date} className={styles.registerRow}>
              <span>{r.date}</span>
              <span>{r.issued ?? '—'}</span>
              <span>{r.balance}</span>
            </div>
          ))}
          <span className={styles.registerVia}>
            <ScanLine size={10} strokeWidth={1.6} aria-hidden="true" />
            {evidence.capturedVia}
          </span>
        </figure>

        <div className={styles.readout}>
          <p className={styles.facility}>{evidence.facilityName}</p>

          <div className={styles.row}>
            <span>Digital record</span>
            <b className="num">{evidence.digitalRecord}</b>
          </div>
          <div className={styles.row}>
            <span>Field evidence</span>
            <b className="num">{evidence.fieldEvidence}</b>
          </div>
          <div className={`${styles.row} ${styles.rowCritical}`}>
            <span>Discrepancy</span>
            <b className="num">{delta}</b>
          </div>
          <div className={styles.row}>
            <span>Extraction confidence</span>
            <b className="num">{evidence.confidence.toFixed(2)}</b>
          </div>

          {/* Consequences appear only once a human has agreed to them. */}
          <div className={styles.cascade} data-shown={confirmed}>
            <div className={styles.row}>
              <span>Predicted breach</span>
              <b className="num">
                {evidence.breachDayBefore}d <span className={styles.arrow}>→</span>{' '}
                <em>{evidence.breachDayAfter}d</em>
              </b>
            </div>
            <p className={styles.cascadeNote}>Donor falls below its safety floor — the original plan is invalidated.</p>
          </div>
        </div>
      </div>

      {!confirmed && onConfirm && <button className={styles.confirmButton} onClick={onConfirm}>Confirm demo count · recalculate plan <Check size={16} /></button>}
      <p className={`${styles.gate} ${confirmed ? styles.gateDone : ''}`} role="status">
        {confirmed ? (
          <>
            <Check size={13} strokeWidth={2.2} aria-hidden="true" />
            {copy.realityLens.confirmed}
          </>
        ) : (
          <>
            <span className={styles.pendingDot} aria-hidden="true" />
            {copy.realityLens.awaiting}
          </>
        )}
      </p>
    </div>
  );
}
