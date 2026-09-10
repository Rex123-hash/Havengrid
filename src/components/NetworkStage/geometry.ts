import type { CareCohort, Facility } from '../../data/types';

export const VIEW_W = 1000;
export const VIEW_H = 640;

/** Flat-top hexagon for the warehouse tier. */
export function hexPath(cx: number, cy: number, r: number) {
  const pts: string[] = [];
  for (let i = 0; i < 6; i += 1) {
    const a = (Math.PI / 180) * (60 * i - 30);
    pts.push(`${(cx + r * Math.cos(a)).toFixed(2)},${(cy + r * Math.sin(a)).toFixed(2)}`);
  }
  return `M${pts.join('L')}Z`;
}

/** Diamond for the CHC tier — reads as a distinct rank from the PHC circle. */
export function diamondPath(cx: number, cy: number, r: number) {
  return `M${cx} ${cy - r}L${cx + r} ${cy}L${cx} ${cy + r}L${cx - r} ${cy}Z`;
}

/** Tier is legible from size alone, before colour or shape is read. */
export const nodeRadius = (tier: Facility['tier']) => (tier === 'warehouse' ? 20 : tier === 'chc' ? 14.5 : 11);

/**
 * A gently curved corridor between two facilities. The bow is perpendicular to
 * the run so links never sit exactly on top of one another.
 */
export function linkPath(ax: number, ay: number, bx: number, by: number, bow = 0.11) {
  const mx = (ax + bx) / 2;
  const my = (ay + by) / 2;
  const dx = bx - ax;
  const dy = by - ay;
  return `M${ax} ${ay} Q ${mx - dy * bow} ${my + dx * bow} ${bx} ${by}`;
}

export interface BlastPoint {
  id: string;
  cohort: CareCohort['key'];
  /** Resting position once the bloom completes. */
  tx: number;
  ty: number;
  /** Stagger order, 0–1. */
  delay: number;
}

export interface BlastCohortLabel {
  key: CareCohort['key'];
  count: number;
  label: string;
  x: number;
  y: number;
}

/**
 * Lays the exposed care events out as a fan below the affected facility,
 * grouped into cohort arcs. Positions are deterministic — derived from the
 * cohort counts in the scenario, never randomised.
 */
export function buildBlastLayout(originX: number, originY: number, cohorts: CareCohort[]) {
  // Angle bands in radians; 0 = due right, PI/2 = straight down.
  const bands: Record<string, [number, number]> = {
    paediatric: [0.6, 1.0],
    maternal: [0.3, 0.56],
    scheduled: [0.03, 0.26],
  };

  const points: BlastPoint[] = [];
  const labels: BlastCohortLabel[] = [];
  let ordinal = 0;
  const total = cohorts.reduce((n, c) => n + c.count, 0);

  cohorts.forEach((cohort) => {
    const [a0, a1] = bands[cohort.key] ?? [0.1, 0.9];
    let mx = 0;
    let my = 0;

    for (let i = 0; i < cohort.count; i += 1) {
      const f = cohort.count === 1 ? 0.5 : i / (cohort.count - 1);
      const angle = (a0 + (a1 - a0) * f) * Math.PI;
      const radius = 104 + (i % 3) * 13;
      const tx = originX + Math.cos(angle) * radius;
      const ty = originY + Math.sin(angle) * radius;
      mx += tx;
      my += ty;
      points.push({ id: `${cohort.key}-${i}`, cohort: cohort.key, tx, ty, delay: ordinal / total });
      ordinal += 1;
    }

    mx /= cohort.count;
    my /= cohort.count;
    const pull = 1.4;
    labels.push({
      key: cohort.key,
      count: cohort.count,
      label: cohort.label,
      x: originX + (mx - originX) * pull,
      y: originY + (my - originY) * pull,
    });
  });

  return { points, labels };
}

/** Mixes two rgb triples. Used for the amber → coral crossing. */
export function mixRgb(a: [number, number, number], b: [number, number, number], t: number) {
  const c = (i: number) => Math.round(a[i] + (b[i] - a[i]) * t);
  return `rgb(${c(0)}, ${c(1)}, ${c(2)})`;
}

export const RGB = {
  mint: [101, 205, 183] as [number, number, number],
  warning: [217, 155, 63] as [number, number, number],
  critical: [212, 91, 85] as [number, number, number],
};
