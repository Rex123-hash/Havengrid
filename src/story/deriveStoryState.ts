import type { CandidateIntervention, Facility, LandingScenario } from '../data/types';
import { CONFIRM_AT, RECOVERY, STAGES, clamp, smoothstep, within } from './stages';

/** Visual state of a facility at a given horizon. Order matters for severity. */
export type FacilityRisk = 'stable' | 'watch' | 'breach' | 'unknown';

export interface FacilityState {
  facility: Facility;
  risk: FacilityRisk;
  /** Effective breach day after any confirmed correction. */
  effectiveBreachDay: number | null;
  /**
   * 0–1 transition intensity. Non-zero only while a facility is crossing into a
   * new state; decays as the horizon moves past. This is the ONLY thing allowed
   * to drive glow.
   */
  transition: number;
  /** 0–1, how far through the amber→coral colour crossing this node is. */
  severity: number;
  /** Inventory confidence, from days since physical verification. */
  freshness: number;
}

export interface StoryState {
  progress: number;
  /** Days ahead the horizon currently reaches. */
  horizonDay: number;
  facilities: FacilityState[];
  /** Summed from facilities currently past the horizon — never a counter. */
  careEventsExposed: number;
  /** Focus facility, always resolved for convenience. */
  focus: FacilityState;

  /** 0–1 bloom progress for the care blast radius. */
  blastProgress: number;
  blastVisible: number;

  /** How many candidate rows have been revealed. */
  candidatesRevealed: number;

  /** The plan currently on the table (swaps after the correction). */
  activePlan: CandidateIntervention;
  /** 0–1 draw progress of the active route path. */
  routeProgress: number;
  routeVisible: number;
  /** How many justification lines have resolved. */
  justificationsResolved: number;

  /** Reality Lens */
  evidenceVisible: number;
  evidenceConfirmed: boolean;
  /** 0–1, used to animate the corrected figures as the confirmation lands. */
  correctionAmount: number;

  /** Verification lifecycle */
  verificationVisible: number;
  stepsComplete: number;

  /** True once the focus facility has been restored. */
  resolved: boolean;
  /** 0–1 resolve glow on the focus node. */
  resolveGlow: number;
}

/**
 * Pure. No refs, no DOM, no time. Given scroll progress and the scenario, this
 * returns everything every visual on the page needs.
 *
 * Because it is a function of progress alone, the whole story is reversible:
 * scrolling back un-ignites facilities, retracts the route and returns the
 * blast-radius points to their node.
 */
export function deriveStoryState(
  progress: number,
  s: LandingScenario,
  horizonOverride: number | null = null,
): StoryState {
  const p = clamp(progress);

  /* ── Horizon ─────────────────────────────────────────────────────
     Sweeps 0 → 14 days across the horizon and breach stages, then holds
     while the story deals with the consequences, then resets at the close
     so the final frame matches the opening frame. */
  let horizonDay: number;
  if (p < STAGES.horizon[0]) {
    horizonDay = 0;
  } else if (p < STAGES.breach[1]) {
    horizonDay = within(p, STAGES.horizon[0] + 0.012, STAGES.breach[1]) * 14;
  } else if (p < STAGES.closing[0]) {
    horizonDay = 14;
  } else {
    horizonDay = 14 * (1 - within(p, STAGES.closing[0], STAGES.closing[0] + 0.045));
  }

  // A visitor steering the rail outranks the story. Everything downstream —
  // facility states, glow, the exposure total — recomputes from this one number,
  // so manual control and scroll control are literally the same code path.
  if (horizonOverride !== null) horizonDay = clamp(horizonOverride, 0, 30);

  /* ── Correction ──────────────────────────────────────────────────
     Nothing recalculates until the confirmation lands. This gate is the
     product principle expressed as a single boolean. */
  const correctionAmount = smoothstep(CONFIRM_AT, CONFIRM_AT + 0.022, p);
  const evidenceConfirmed = correctionAmount > 0.5;

  /* ── Recovery ────────────────────────────────────────────────────  */
  const replanning = p >= RECOVERY.replanDraw[0];
  const verifyP = within(p, RECOVERY.verify[0], RECOVERY.verify[1]);
  // Steps resolve at uneven intervals — the third takes visibly longer, because
  // a stepper that arrives evenly says "this always works".
  const stepGates = [0.05, 0.15, 0.27, 0.46, 0.61, 0.73, 0.86, 0.96];
  const stepsComplete = stepGates.filter((g) => verifyP >= g).length;

  const resolved = stepsComplete >= s.verification.length;
  const resolveGlow = resolved ? Math.max(0, 1 - within(p, RECOVERY.verify[1], RECOVERY.verify[1] + 0.05)) : 0;

  /* ── Facility states ─────────────────────────────────────────────  */
  const cascade = new Set(s.realityLens.cascadeFacilityIds);
  const focusId = s.focusFacilityId;

  const facilities: FacilityState[] = s.facilities.map((f) => {
    // The confirmed correction rewrites the donor's forecast and drags its
    // dependent with it. This is the cascade — same network, worse reality.
    let breach = f.breachDay;
    if (evidenceConfirmed && cascade.has(f.id)) {
      breach = f.id === s.realityLens.facilityId ? s.realityLens.breachDayAfter : 8;
    }
    // Once the recovery verifies, the focus facility is restored.
    if (resolved && f.id === focusId) breach = null;

    const freshness = clamp(1 - f.daysSinceVerified / 18, 0.34, 1);

    if (f.forecastStatus === 'unavailable') {
      return { facility: f, risk: 'unknown', effectiveBreachDay: null, transition: 0, severity: 0, freshness };
    }
    if (breach === null) {
      return { facility: f, risk: 'stable', effectiveBreachDay: null, transition: 0, severity: 0, freshness };
    }

    const lead = breach - horizonDay;
    if (lead <= 0) {
      // Past the threshold. Glow fires at the crossing and decays within ~2.5 days.
      const transition = Math.max(0, 1 - -lead / 2.5);
      const severity = clamp(-lead / 0.9);
      return { facility: f, risk: 'breach', effectiveBreachDay: breach, transition, severity, freshness };
    }
    if (lead <= 3) {
      const t = 1 - lead / 3;
      return { facility: f, risk: 'watch', effectiveBreachDay: breach, transition: t * 0.3, severity: t, freshness };
    }
    return { facility: f, risk: 'stable', effectiveBreachDay: breach, transition: 0, severity: 0, freshness };
  });

  const careEventsExposed = facilities
    .filter((f) => f.risk === 'breach')
    .reduce((sum, f) => sum + f.facility.careEventsExposed, 0);

  const focus = facilities.find((f) => f.facility.id === focusId)!;

  /* ── Blast radius ────────────────────────────────────────────────  */
  const blastVisible = beat(p, STAGES.blast[0], STAGES.blast[1], 0.24, 0.2);
  const blastProgress = within(p, STAGES.blast[0] + 0.014, STAGES.blast[0] + 0.082);

  /* ── Candidates ──────────────────────────────────────────────────  */
  const candP = within(p, STAGES.candidates[0] + 0.012, STAGES.candidates[1] - 0.012);
  const candidatesRevealed = Math.round(candP * s.candidates.length);

  /* ── Plan + route ────────────────────────────────────────────────  */
  const chosen = s.candidates.find((c) => c.verdict === 'chosen')!;
  const activePlan = replanning ? s.replan : chosen;

  const routeProgress = replanning
    ? within(p, RECOVERY.replanDraw[0], RECOVERY.replanDraw[1])
    : within(p, STAGES.intervention[0] + 0.008, STAGES.intervention[1] - 0.014);

  // The first route stays faintly on screen through the Reality Lens stage so
  // the viewer can see the plan that is about to be invalidated.
  let routeVisible = beat(p, STAGES.intervention[0], RECOVERY.verify[1] + 0.02, 0.05, 0.09);
  if (!replanning && p > STAGES.realityLens[0] + 0.03) routeVisible *= 0.24;

  const justCount = activePlan.justifications?.length ?? 0;
  const justificationsResolved = Math.floor(routeProgress * (justCount + 0.4));

  /* ── Reality Lens ────────────────────────────────────────────────  */
  const evidenceVisible = beat(p, STAGES.realityLens[0], STAGES.recovery[0] + 0.03, 0.16, 0.2);

  const verificationVisible = beat(p, RECOVERY.verify[0] - 0.03, STAGES.closing[0] + 0.01, 0.14, 0.2);

  return {
    progress: p,
    horizonDay,
    facilities,
    careEventsExposed,
    focus,
    blastProgress,
    blastVisible,
    candidatesRevealed,
    activePlan,
    routeProgress,
    routeVisible,
    justificationsResolved,
    evidenceVisible,
    evidenceConfirmed,
    correctionAmount,
    verificationVisible,
    stepsComplete,
    resolved,
    resolveGlow,
  };
}

function beat(p: number, a: number, b: number, fadeIn: number, fadeOut: number) {
  const t = (p - a) / (b - a || 1e-6);
  if (t < -0.03 || t > 1.03) return 0;
  return Math.min(smoothstep(0, fadeIn, t), 1 - smoothstep(1 - fadeOut, 1, t));
}
