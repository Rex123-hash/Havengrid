import { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { LandingScenario, TrackedItem } from '../../data/types';
import type { FacilityState, StoryState } from '../../story/deriveStoryState';
import { MapGround } from './MapGround';
import {
  RGB,
  buildBlastLayout,
  diamondPath,
  hexPath,
  linkPath,
  mixRgb,
  nodeRadius,
} from './geometry';
import styles from './NetworkStage.module.css';
import sleeveFixStyles from './SleeveFix.module.css';
import focusPulseStyles from './FocusPulse.module.css';

interface Props {
  scenario: LandingScenario;
  state: StoryState;
  reducedMotion: boolean;
  /** Optional scroll-driven assembly of the district corridors. */
  connectionProgress?: number;
}

/** Where a hovered facility's detail card should sit, in wrapper coordinates. */
interface HoverTarget {
  fs: FacilityState;
  x: number;
  y: number;
  flip: boolean;
}

/**
 * THE PERSISTENT NETWORK.
 *
 * Mounted once for the lifetime of the page. Facility coordinates come from the
 * scenario and are never recomputed, so the first frame and the last frame show
 * the same district in the same place. Only *state* changes — that constancy is
 * what makes the page read as one world rather than a run of illustrations.
 */
export function NetworkStage({ scenario: sourceScenario, state: sourceState, reducedMotion, connectionProgress = 1 }: Props) {
  // A wide presentation layout keeps the network legible in its landscape panel.
  // Only display coordinates change; forecasts and facility identities stay intact.
  const scenario = useMemo(() => ({...sourceScenario, facilities: sourceScenario.facilities.map(f => ({...f, y: 54 + (f.y - 78) * 0.65}))}), [sourceScenario]);
  const state = {...sourceState, facilities: sourceState.facilities.map(fs => ({...fs, facility: scenario.facilities.find(f => f.id === fs.facility.id)!}))};
  const [sleeveOpen, setSleeveOpen] = useState(false);
  const [hover, setHover] = useState<HoverTarget | null>(null);
  const focus = scenario.facilities.find((f) => f.id === scenario.focusFacilityId)!;
  const byId = useMemo(
    () => Object.fromEntries(scenario.facilities.map((f) => [f.id, f])),
    [scenario.facilities],
  );

  // Layout is derived once. It depends only on seed data, never on progress.
  const blast = useMemo(
    () => buildBlastLayout(focus.x, focus.y, scenario.careCohorts),
    [focus.x, focus.y, scenario.careCohorts],
  );

  const links = useMemo(
    () =>
      scenario.links.map((l) => {
        const a = byId[l.from];
        const b = byId[l.to];
        return { ...l, d: linkPath(a.x, a.y, b.x, b.y), touchesFocus: l.from === focus.id || l.to === focus.id };
      }),
    [scenario.links, byId, focus.id],
  );

  const routeD = useMemo(() => {
    const donor = byId[state.activePlan.facilityId];
    return linkPath(donor.x, donor.y, focus.x, focus.y, 0.16);
  }, [byId, state.activePlan.facilityId, focus.x, focus.y]);

  // Dim the wider network while the story is focused on one facility, so the
  // eye is led without anything being hidden.
  const dim = Math.max(state.blastVisible, state.routeVisible * 0.72);

  return (
    <div className={styles.wrap} data-sleeve-open={sleeveOpen} onPointerLeave={() => setHover(null)}>
      <div className={styles.networkHeader}><span><i /> DISTRICT NETWORK</span><b>14 facilities <em>/</em> hover to inspect</b></div>
      <svg
        className={styles.svg}
        viewBox="65 12 865 440"
        preserveAspectRatio="xMidYMid meet"
        shapeRendering="geometricPrecision"
        role="img"
        aria-label={`${scenario.district} district supply network — ${scenario.facilityCount} facilities with predicted stock states`}
      >
        <defs>
          <radialGradient id="bloom-breach">
            <stop offset="0%" stopColor="rgba(212,91,85,0.5)" />
            <stop offset="48%" stopColor="rgba(212,91,85,0.15)" />
            <stop offset="100%" stopColor="rgba(212,91,85,0)" />
          </radialGradient>
          <radialGradient id="bloom-watch">
            <stop offset="0%" stopColor="rgba(217,155,63,0.44)" />
            <stop offset="48%" stopColor="rgba(217,155,63,0.13)" />
            <stop offset="100%" stopColor="rgba(217,155,63,0)" />
          </radialGradient>
          <radialGradient id="bloom-resolve">
            <stop offset="0%" stopColor="rgba(101,205,183,0.55)" />
            <stop offset="48%" stopColor="rgba(101,205,183,0.16)" />
            <stop offset="100%" stopColor="rgba(101,205,183,0)" />
          </radialGradient>

        </defs>

        <MapGround />

        {/* ── supply corridors ─────────────────────────────────────── */}
        <g>
          {links.map((l, index) => {
            const lineProgress = Math.max(0, Math.min(1, connectionProgress * 1.35 - index * 0.035));
            return (
            <path
              key={`${l.from}-${l.to}`}
              d={l.d}
              fill="none"
              stroke={l.touchesFocus ? '#81d6b4' : '#6aa58f'}
              strokeWidth={l.touchesFocus ? 2 : 1.2}
              strokeLinecap="round"
              opacity={(l.touchesFocus ? 0.85 : 0.45 - dim * 0.22) * Math.max(.08, lineProgress)}
              pathLength={1}
              strokeDasharray="1"
              strokeDashoffset={1 - lineProgress}
            />
            );
          })}
        </g>

        <g opacity={state.candidatesRevealed > 0 ? 0.65 : 0}>
          {scenario.candidates.slice(0,state.candidatesRevealed).map(c => {
            const donor = byId[c.facilityId];
            return <path key={c.id} d={linkPath(donor.x,donor.y,focus.x,focus.y)} fill="none" stroke={c.verdict === 'chosen' ? 'var(--teal-700)' : 'var(--ink-muted)'} strokeWidth={c.verdict === 'chosen' ? 2.5 : 1.2} strokeDasharray="5 7" />;
          })}
        </g>
        <circle cx={focus.x} cy={focus.y} r={37} fill={state.resolved ? 'url(#bloom-resolve)' : 'url(#bloom-watch)'} />
        <circle className={focusPulseStyles.focusRing} cx={focus.x} cy={focus.y} r={25} fill="none" stroke={state.resolved ? 'var(--teal-500)' : 'var(--warning)'} strokeWidth={1.5} strokeDasharray="3 5" />
        {/* ── the intervention route, drawn by scroll progress ─────── */}
        <RoutePath d={routeD} progress={state.routeProgress} visible={state.routeVisible} />

        {/* ── care blast radius ────────────────────────────────────── */}
        <BlastRadius
          origin={{ x: focus.x, y: focus.y }}
          layout={blast}
          progress={state.blastProgress}
          visible={state.blastVisible}
          total={scenario.totalCareEventsExposed}
          reducedMotion={reducedMotion}
        />

        {/* ── facilities ───────────────────────────────────────────── */}
        <g>
          {state.facilities.map((fs, index) => (
            <FacilityNode
              key={fs.facility.id}
              fs={fs}
              isFocus={fs.facility.id === focus.id}
              resolveGlow={state.resolveGlow}
              hovered={hover?.fs.facility.id === fs.facility.id}
              onHover={setHover}
              connectionOpacity={Math.max(0, Math.min(1, connectionProgress * 1.55 - index * 0.045))}
            />
          ))}
        </g>
      </svg>

      <div className={styles.networkFooter}><span>SCHEMATIC VIEW</span><b>{state.resolved ? 'Recovery verified' : state.evidenceConfirmed ? 'Evidence updated · replanning' : state.routeVisible > .5 ? 'Intervention proposed' : 'Care-aware forecasting'}</b><span>{String(Math.round(state.horizonDay)).padStart(2,'0')}D HORIZON</span></div>
      <aside className={styles.sleeve} data-open={sleeveOpen} aria-label="Bhatpar forecast" onKeyDown={e => {if(e.key === 'Escape') {setSleeveOpen(false); e.currentTarget.querySelector('button')?.focus();}}}>
        <button className={styles.sleeveTab} aria-expanded={sleeveOpen} aria-controls="bhatpar-forecast" onClick={() => {setHover(null);setSleeveOpen(v => !v);}} aria-label={sleeveOpen ? 'Close Bhatpar forecast' : 'Open Bhatpar forecast'}>
          {sleeveOpen ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          <span>{state.resolved ? 'CARE PROTECTED' : 'BHATPAR FORECAST'}</span>
          <b>{state.resolved ? scenario.totalCareEventsExposed : `${scenario.item.breachDay}D`}</b>
        </button>
      <div className={styles.sleeveReveal} aria-hidden={!sleeveOpen}>
      <div id="bhatpar-forecast" className={styles.forecast} data-resolved={state.resolved}>
        {sleeveOpen && <button className={sleeveFixStyles.closeButton} aria-label="Close Bhatpar forecast" onClick={() => setSleeveOpen(false)}><ChevronRight size={18} strokeWidth={2.2} /></button>}
        <div className={styles.forecastHeading}><span>{focus.name}</span><i>{state.resolved ? 'VERIFIED' : 'FORECAST'}</i></div>
        <p>{state.resolved ? 'Care continuity restored' : state.horizonDay < 1 ? 'Stock available today' : `Looking ${Math.round(state.horizonDay)} days ahead`}</p>
        <strong>{state.resolved ? scenario.totalCareEventsExposed : scenario.item.breachDay}<small>{state.resolved ? 'care events protected' : 'days · predicted shortage'}</small></strong>
        {!state.resolved && <div className={styles.forecastCare}><b>{scenario.totalCareEventsExposed}</b> future care events exposed</div>}
        <div className={styles.stockComparison}><span>Stock <b>{scenario.item.currentStock + (state.resolved ? state.activePlan.transferUnits! : 0)}</b></span><span>14-day need <b>{scenario.item.projectedDemand}</b></span></div>
        <span className={styles.forecastNote}>Illustrative demo · {scenario.item.name}</span>
      </div>
        </div>
      </aside>
      {hover && <FacilityCard target={hover} item={scenario.item} isFocus={hover.fs.facility.id === focus.id} />}
    </div>
  );
}

/**
 * Floating facility detail. Glass, and the only thing on the page that appears
 * because of a pointer rather than because something in the system changed.
 *
 * It states the forecast, the care exposure and — importantly — how stale the
 * inventory figure behind that forecast actually is.
 */
function FacilityCard({ target, item, isFocus }: { target: HoverTarget; item: TrackedItem; isFocus: boolean }) {
  const { fs } = target;
  const f = fs.facility;
  const tier = f.tier === 'warehouse' ? 'District warehouse' : f.tier === 'chc' ? 'Community health centre' : 'Primary health centre';

  const label =
    fs.risk === 'unknown'
      ? 'No forecast'
      : fs.risk === 'breach'
        ? `Breach · day ${fs.effectiveBreachDay}`
        : fs.risk === 'watch'
          ? `Tight · day ${fs.effectiveBreachDay}`
          : 'On track';

  return (
    <div
      className={styles.card}
      style={{ left: target.x, top: target.y, transform: `translate(${target.flip ? '-100%' : '0'}, -50%)` }}
      role="tooltip"
    >
      <div className={styles.cardHead}>
        <span className={styles.cardName}>{f.name}</span>
        <span className={styles.cardState} data-risk={fs.risk}>
          {label}
        </span>
      </div>
      <span className={styles.cardTier}>{tier}</span>

      {isFocus && (
        <div className={styles.cardRows}>
          <div>
            <span>Stock</span>
            <b className="num">{item.currentStock}</b>
          </div>
          <div>
            <span>Need · {item.demandWindowDays}d</span>
            <b className="num">{item.projectedDemand}</b>
          </div>
        </div>
      )}

      {f.careEventsExposed > 0 && fs.risk !== 'stable' && fs.risk !== 'unknown' && (
        <p className={styles.cardCare}>
          <b className="num">{f.careEventsExposed}</b> care events exposed
        </p>
      )}

      {fs.risk === 'unknown' && <p className={styles.cardWarn}>No forecast could be produced — this is not "healthy".</p>}

      <p className={styles.cardFresh} data-stale={f.daysSinceVerified >= 7}>
        inventory verified <span className="num">{f.daysSinceVerified}</span>d ago
      </p>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════ */

function RoutePath({ d, progress, visible }: { d: string; progress: number; visible: number }) {
  // A generous constant beats measuring getTotalLength on every render; the
  // dash simply needs to exceed the path length for the reveal to read cleanly.
  const LEN = 900;
  return (
    <g opacity={visible}>
      <path d={d} fill="none" stroke="var(--mint-200)" strokeWidth={6} strokeLinecap="round" opacity={0.5 * progress} />
      <path
        d={d}
        fill="none"
        stroke="var(--teal-500)"
        strokeWidth={2.4}
        strokeLinecap="round"
        strokeDasharray={LEN}
        strokeDashoffset={LEN * (1 - progress)}
      />
    </g>
  );
}

function BlastRadius({
  origin,
  layout,
  progress,
  visible,
  total,
  reducedMotion,
}: {
  origin: { x: number; y: number };
  layout: ReturnType<typeof buildBlastLayout>;
  progress: number;
  visible: number;
  total: number;
  reducedMotion: boolean;
}) {
  if (visible <= 0.001) return null;

  // Under reduced motion the points are simply present at rest rather than
  // travelling — the same information, without the flight.
  const settle = (delay: number) => {
    if (reducedMotion) return progress > 0.05 ? 1 : 0;
    const t = Math.min(1, Math.max(0, (progress - delay * 0.5) / 0.5));
    return t * t * (3 - 2 * t);
  };

  const labelOpacity = Math.min(1, Math.max(0, (progress - 0.55) / 0.4));
  const shown = Math.round(progress * total);

  return (
    <g opacity={visible} aria-hidden="true">
      <text
        x={origin.x}
        y={origin.y - 118}
        textAnchor="middle"
        className={styles.blastTotal}
        opacity={Math.min(1, progress / 0.5)}
      >
        {shown} care events exposed
      </text>

      {layout.points.map((pt) => {
        const t = settle(pt.delay);
        return (
          <circle
            key={pt.id}
            cx={origin.x + (pt.tx - origin.x) * t}
            cy={origin.y + (pt.ty - origin.y) * t}
            r={4.2}
            fill="var(--critical)"
            opacity={0.25 + 0.75 * t}
          />
        );
      })}

      {layout.labels.map((l) => (
        <text key={l.key} x={l.x} y={l.y + 4} textAnchor="middle" className={styles.blastLabel} opacity={labelOpacity}>
          {l.count} {l.label}
        </text>
      ))}
    </g>
  );
}

function FacilityNode({
  fs,
  isFocus,
  resolveGlow,
  hovered,
  onHover,
  connectionOpacity = 1,
}: {
  fs: FacilityState;
  isFocus: boolean;
  resolveGlow: number;
  hovered: boolean;
  onHover: (t: HoverTarget | null) => void;
  connectionOpacity?: number;
}) {
  const { facility: f, risk, transition, severity, freshness } = fs;
  const r = nodeRadius(f.tier) * 1.4;

  let stroke = 'var(--mint-400)';
  let fill: string = 'var(--mint-400)';
  let dashed = false;

  if (risk === 'unknown') {
    stroke = 'var(--border-strong)';
    fill = 'none';
    dashed = true;
  } else if (risk === 'breach') {
    const c = mixRgb(RGB.warning, RGB.critical, severity);
    stroke = c;
    fill = c;
  } else if (risk === 'watch') {
    const c = mixRgb(RGB.mint, RGB.warning, severity);
    stroke = c;
    fill = c;
  }

  const glow = isFocus && resolveGlow > 0 ? resolveGlow : transition;
  const bloom = isFocus && resolveGlow > 0 ? 'bloom-resolve' : risk === 'breach' ? 'bloom-breach' : 'bloom-watch';
  const hot = risk === 'breach' || risk === 'watch';

  const labelLeft = f.x > 640;

  const enter = (e: React.PointerEvent<SVGGElement> | React.FocusEvent<SVGGElement>) => {
    // Measure the node itself so the card lands exactly on it regardless of how
    // the viewBox happens to be letterboxed at this viewport.
    const node = e.currentTarget.getBoundingClientRect();
    const host = e.currentTarget.ownerSVGElement?.parentElement?.getBoundingClientRect();
    if (!host) return;
    const flip = node.left + node.width / 2 - host.left > host.width * 0.62;
    onHover({
      fs,
      x: node.left + node.width / 2 - host.left + (flip ? -16 : 16),
      y: node.top + node.height / 2 - host.top,
      flip,
    });
  };

  return (
    <g
      className={styles.node}
      opacity={Math.max(0.42, connectionOpacity)}
      data-hovered={hovered}
      tabIndex={0}
      role="img"
      aria-label={`${f.name} — ${risk === 'unknown' ? 'no forecast available' : risk === 'breach' ? `predicted breach on day ${fs.effectiveBreachDay}` : risk === 'watch' ? `tight, predicted breach on day ${fs.effectiveBreachDay}` : 'on track'}`}
      onPointerEnter={enter}
      onPointerLeave={() => onHover(null)}
      onFocus={enter}
      onBlur={() => onHover(null)}
    >
      {/* Generous invisible hit area — a 9px circle is not a pointer target. */}
      <circle cx={f.x} cy={f.y} r={22} fill="transparent" />
      {/* Glow means exactly one thing: this node just changed state. */}
      {glow > 0.004 && (
        <circle cx={f.x} cy={f.y} r={r * 2.1 + glow * 13} fill={`url(#${bloom})`} opacity={glow * 0.95} />
      )}

      {/* One shape, one colour, and a ground-coloured outline that separates the
          marker from whatever sits under it. That outline is the whole trick —
          plates, cores and drop shadows only add clutter at this size. */}
      <g opacity={Math.max(0.7, freshness)}>
        
        <circle cx={f.x} cy={f.y} r={r + 2} fill="#163b32" stroke="#8cd4b8" strokeWidth={0.6} />
        {f.tier === 'warehouse' && (
          <path d={hexPath(f.x, f.y, r)} fill={fill} stroke="#163b32" strokeWidth={3} strokeLinejoin="round" />
        )}
        {f.tier === 'chc' && (
          <path d={diamondPath(f.x, f.y, r)} fill={fill} stroke="#163b32" strokeWidth={3} strokeLinejoin="round" />
        )}
        {f.tier === 'phc' &&
          (dashed ? (
            <circle cx={f.x} cy={f.y} r={r} fill="none" stroke={stroke} strokeWidth={2} strokeDasharray="3.5 3.5" />
          ) : (
            <circle cx={f.x} cy={f.y} r={r} fill={fill} stroke="#163b32" strokeWidth={3} />
          ))}
      </g>

      {f.tier !== 'phc' && <path d={`M${f.x-4} ${f.y}h8 M${f.x} ${f.y-4}v8`} stroke="white" strokeWidth={1.8} />}
      <text
        x={f.x + (labelLeft ? -(r + 8) : r + 8)}
        y={f.y + 4}
        textAnchor={labelLeft ? 'end' : 'start'}
        className={hot ? `${styles.nodeLabel} ${styles.nodeLabelHot}` : styles.nodeLabel}
      >
        {f.short}
      </text>
    </g>
  );
}
