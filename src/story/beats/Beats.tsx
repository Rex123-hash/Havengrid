import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ChevronDown } from 'lucide-react';
import { copy, routes } from '../../brand/brand.config';
import type { CandidateIntervention, LandingScenario } from '../../data/types';
import type { StoryState } from '../deriveStoryState';
import { RealityLens } from '../../components/RealityLens/RealityLens';
import { VerificationTrack } from '../../components/VerificationTrack/VerificationTrack';
import styles from './Beats.module.css';

/* ── shared primitives ──────────────────────────────────────────── */

function Beat({ opacity, children, label }: { opacity: number; children: ReactNode; label: string }) {
  const shown = opacity > 0.5;
  return (
    <section
      className={styles.beat}
      style={{
        opacity,
        transform: `translateY(calc(-50% + ${(1 - opacity) * 42}px))`,
        // A fully faded beat is pulled out of the tab order as well as the
        // accessibility tree, so its CTAs can never become a keyboard trap
        // behind whichever beat is actually on screen.
        visibility: shown ? 'visible' : 'hidden',
      }}
      aria-label={label}
      aria-hidden={!shown}
    >
      {children}
    </section>
  );
}

function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`${styles.card} ${className}`}>{children}</div>;
}

function Row({ label, value, tone }: { label: string; value: string; tone?: 'critical' | 'stable' }) {
  return (
    <div className={`${styles.row} ${tone ? styles[tone] : ''}`}>
      <span>{label}</span>
      <b className="num">{value}</b>
    </div>
  );
}

/* ── 1 · arrival ────────────────────────────────────────────────── */

export function ArrivalBeat({ opacity, scenario }: { opacity: number; scenario: LandingScenario }) {
  const c = copy.arrival;
  return (
    <Beat opacity={opacity} label="Introduction">
      <span className={`eyebrow ${styles.kicker}`}>{c.eyebrow}</span>
      <h1 className={styles.h1}>Keep shortages<br />from becoming<br /><em>missed care.</em></h1>
      <p className={styles.subhead}>{c.subhead}</p>
      <p className={styles.body}>{c.body}</p>

      <div className={styles.ctaRow}>
        <Link to={routes.demo} className={styles.primaryCta}>
          {c.primaryCta}
          <ArrowRight size={16} strokeWidth={1.8} aria-hidden="true" />
        </Link>
        <Link to={routes.signIn} className={styles.secondaryCta}>
          {c.secondaryCta}
        </Link>
      </div>

      <a href="#capabilities" className={styles.tertiaryCta}>
        {c.tertiaryCta}
        <ChevronDown size={14} strokeWidth={1.8} aria-hidden="true" />
      </a>

      <p className={styles.meta}>
        <span className="num">{scenario.facilityCount}</span> facilities ·{' '}
        <span className="num">{scenario.scheduledCareEvents.toLocaleString('en-IN')}</span> scheduled care events ·{' '}
        {scenario.district}, {scenario.region}
      </p>
    </Beat>
  );
}

/* ── 2 · horizon ────────────────────────────────────────────────── */

export function HorizonBeat({ opacity }: { opacity: number }) {
  const c = copy.horizon;
  return (
    <Beat opacity={opacity} label="The horizon opens">
      <span className={`eyebrow ${styles.kicker}`}>{c.eyebrow}</span>
      <h2 className={styles.h2}>{c.headline}</h2>
      <p className={styles.lead}>{c.body}</p>
      <p className={styles.body}>{c.aside}</p>
    </Beat>
  );
}

/* ── 3 · predicted breach ───────────────────────────────────────── */

export function BreachBeat({ opacity, scenario }: { opacity: number; scenario: LandingScenario }) {
  const c = copy.breach;
  const { item } = scenario;
  const focus = scenario.facilities.find((f) => f.id === scenario.focusFacilityId)!;
  const deficit = item.projectedDemand - item.currentStock;

  return (
    <Beat opacity={opacity} label="Predicted breach">
      <span className={`eyebrow ${styles.kicker}`}>{c.eyebrow}</span>
      <h2 className={styles.h2}>{c.headline}</h2>
      <p className={styles.lead}>{c.subhead}</p>

      <Card>
        <div className={styles.cardHead}>
          <div>
            <h3 className={styles.cardTitle}>{focus.name}</h3>
            <span className={styles.cardSub}>
              {item.name} · {item.form}
            </span>
          </div>
          <span className={`${styles.pill} ${styles.pillRisk}`}>At risk</span>
        </div>

        <Row label="Current stock" value={`${item.currentStock} ${item.unit}`} />
        <Row label={`Projected demand · ${item.demandWindowDays}d`} value={`${item.projectedDemand} ${item.unit}`} />
        <Row label="Deficit" value={`${deficit} ${item.unit}`} />
        <Row label="Next replenishment" value={`+${item.replenishmentEtaDays} days`} />
        <Row label="Predicted breach" value={`day ${item.breachDay}`} tone="critical" />

        <p className={styles.stale}>
          ◍ inventory last verified <span className="num">{focus.daysSinceVerified}</span> days ago
        </p>
      </Card>
    </Beat>
  );
}

/* ── 4 · care blast radius ──────────────────────────────────────── */

export function BlastBeat({ opacity, scenario }: { opacity: number; scenario: LandingScenario }) {
  const c = copy.blast;
  return (
    <Beat opacity={opacity} label="Care blast radius">
      <span className={`eyebrow ${styles.kicker}`}>{c.eyebrow}</span>
      <h2 className={styles.h2}>{c.headline}</h2>
      <p className={styles.lead}>{c.subhead}</p>
      <p className={styles.body}>{c.body}</p>

      <Card>
        {scenario.careCohorts.map((cohort) => (
          <div key={cohort.key} className={styles.cohort}>
            <span className={`${styles.cohortCount} num`}>{cohort.count}</span>
            <span className={styles.cohortBody}>
              <b>{cohort.label}</b>
              <i>{cohort.detail}</i>
            </span>
          </div>
        ))}
      </Card>
    </Beat>
  );
}

/* ── 5 · candidate sources ──────────────────────────────────────── */

export function CandidatesBeat({
  opacity,
  scenario,
  revealed,
}: {
  opacity: number;
  scenario: LandingScenario;
  revealed: number;
}) {
  const c = copy.candidates;
  return (
    <Beat opacity={opacity} label="Candidate supply sources">
      <span className={`eyebrow ${styles.kicker}`}>{c.eyebrow}</span>
      <h2 className={styles.h2}>{c.headline}</h2>
      <p className={styles.body}>{c.body}</p>

      <Card>
        {scenario.candidates.map((cand, i) => (
          <CandidateRow key={cand.id} candidate={cand} shown={i < revealed} />
        ))}
      </Card>
    </Beat>
  );
}

function CandidateRow({ candidate, shown }: { candidate: CandidateIntervention; shown: boolean }) {
  const verdictClass =
    candidate.verdict === 'chosen' ? styles.pillOk : candidate.verdict === 'held' ? styles.pillHold : styles.pillRisk;
  const verdictLabel = candidate.verdict === 'chosen' ? 'Chosen' : candidate.verdict === 'held' ? 'Held' : 'No';

  return (
    <div
      className={`${styles.candidate} ${candidate.verdict === 'rejected' ? styles.candidateOut : ''}`}
      style={{ opacity: shown ? 1 : 0 }}
    >
      <span className={`${styles.pill} ${verdictClass}`}>{verdictLabel}</span>
      <span className={styles.candidateBody}>
        <b>{candidate.facilityName}</b>
        <i>
          <span className="num">{candidate.surplus}</span> surplus ·{' '}
          <span className="num">{candidate.distanceKm}</span> km — {candidate.reason}
        </i>
      </span>
    </div>
  );
}

/* ── 6 · intervention ───────────────────────────────────────────── */

export function InterventionBeat({
  opacity,
  state,
  scenario,
}: {
  opacity: number;
  state: StoryState;
  scenario: LandingScenario;
}) {
  const c = copy.intervention;
  const plan = state.activePlan;
  const focus = scenario.facilities.find((f) => f.id === scenario.focusFacilityId)!;

  return (
    <Beat opacity={opacity} label="Recommended intervention">
      <span className={`eyebrow ${styles.kicker}`}>{c.eyebrow}</span>
      <h2 className={styles.h2}>
        Transfer <span className="num">{plan.transferUnits}</span> units.
      </h2>
      <p className={styles.route}>
        {plan.facilityName} <ArrowRight size={15} strokeWidth={1.8} aria-hidden="true" /> {focus.name}
      </p>

      <Card>
        <ul className={styles.checks}>
          {(plan.justifications ?? []).map((j, i) => (
            <li key={j} className={i < state.justificationsResolved ? styles.checkDone : undefined}>
              {j}
            </li>
          ))}
        </ul>
      </Card>

      <p className={styles.footnote}>{c.body}</p>
    </Beat>
  );
}

/* ── 7 · reality lens + correction cascade ──────────────────────── */

export function RealityLensBeat({
  opacity,
  scenario,
  state,
}: {
  opacity: number;
  scenario: LandingScenario;
  state: StoryState;
}) {
  const c = state.evidenceConfirmed ? copy.cascade : copy.realityLens;
  return (
    <Beat opacity={opacity} label="Reality lens">
      <span className={`eyebrow ${styles.kicker}`}>{c.eyebrow}</span>
      <h2 className={styles.h2}>{c.headline}</h2>
      <p className={styles.body}>{c.body}</p>
      <RealityLens evidence={scenario.realityLens} confirmed={state.evidenceConfirmed} />
      <p className={styles.footnote}>{copy.realityLens.principle}</p>
    </Beat>
  );
}

/* ── 8 · verified recovery ──────────────────────────────────────── */

export function RecoveryBeat({
  opacity,
  scenario,
  state,
}: {
  opacity: number;
  scenario: LandingScenario;
  state: StoryState;
}) {
  const c = copy.recovery;
  return (
    <Beat opacity={opacity} label="Verified recovery">
      <span className={`eyebrow ${styles.kicker}`}>{c.eyebrow}</span>
      <h2 className={styles.h2}>{c.headline}</h2>
      <p className={styles.lead}>{c.subhead}</p>
      <VerificationTrack
        steps={scenario.verification}
        complete={state.stepsComplete}
        visible={state.verificationVisible}
      />
    </Beat>
  );
}

/* ── 9 · closing ────────────────────────────────────────────────── */

export function ClosingBeat({ opacity, scenario }: { opacity: number; scenario: LandingScenario }) {
  const c = copy.closing;
  return (
    <Beat opacity={opacity} label="Resilience loop closed">
      <span className={`eyebrow ${styles.kicker}`}>{c.eyebrow}</span>
      <h2 className={styles.h2}>
        <span className="num">{scenario.totalCareEventsExposed}</span> {c.headlineSuffix}
      </h2>
      <p className={styles.lead}>{c.subhead}</p>
      <p className={styles.body}>{c.body}</p>
      <p className={styles.footnote}>{c.note}</p>

      <div className={styles.ctaRow}>
        <Link to={routes.demo} className={styles.primaryCta}>
          {c.primaryCta}
          <ArrowRight size={16} strokeWidth={1.8} aria-hidden="true" />
        </Link>
        <Link to={routes.signIn} className={styles.secondaryCta}>
          {c.secondaryCta}
        </Link>
      </div>
    </Beat>
  );
}
