/**
 * BRAND + COPY ISOLATION LAYER
 * ────────────────────────────
 * The product name is NOT final. Every user-visible string and every reference
 * to the product's identity lives in this file so the rename is a one-file edit.
 *
 * Rule for contributors: no component may hardcode the product name, a tagline,
 * a nav label or a CTA label. Import from here instead.
 *
 * To rename the product: change `brand.name` (and optionally `shortName`,
 * `wordmarkAccentFrom`) below. Nothing else needs to be touched.
 */

export const brand = {
  /** Working name only — placeholder, pending final naming. */
  name: 'Haven Grid',
  /** Used where space is tight (mobile nav, footer meta). */
  shortName: 'Haven',
  /**
   * Index into `name` at which the accent colour starts, so the wordmark reads
   * as two tones. Set to 0 for a single-tone wordmark.
   */
  wordmarkAccentFrom: 6,
  tagline: 'Care-aware supply resilience',
  /** Shown once, in the footer. Not repeated through the page. */
  footerNote: 'Built for district health teams, facility managers and supply coordinators.',
} as const;

export const routes = {
  home: '/',
  demo: '/demo',
  signIn: '/sign-in',
} as const;

export const nav = {
  links: [
    { label: 'Product', href: '#story' },
    { label: 'How it works', href: '#capabilities' },
    { label: 'Impact', href: '#closing' },
  ],
  signIn: 'Sign in',
  primaryCta: 'Explore Demo District',
  /** Used where the full label cannot fit. */
  primaryCtaShort: 'Demo District',
} as const;

/**
 * All landing-page prose. Kept out of JSX so copy can be revised (or localised)
 * without touching layout or motion code.
 */
export const copy = {
  arrival: {
    eyebrow: 'Care-aware supply resilience',
    headline: 'Keep shortages from becoming missed care.',
    subhead: 'Predict. Prevent. Verify.',
    body: 'Anticipate supply gaps, understand the care at risk, and coordinate action across your healthcare network.',
    primaryCta: 'Explore Demo District',
    secondaryCta: 'Sign in',
    tertiaryCta: 'See how it works',
  },
  horizon: {
    eyebrow: 'The missing axis',
    headline: 'Today can look healthy. Tomorrow may not.',
    body: 'An inventory system knows what is on the shelf now. It cannot know what care is already scheduled against it.',
    aside: 'Push the horizon forward and the network answers for that day instead of this one.',
  },
  breach: {
    eyebrow: 'Predicted breach',
    headline: "The shelf isn't empty yet.",
    subhead: 'But the system already knows when it will be.',
  },
  blast: {
    eyebrow: 'Care blast radius',
    headline: "A shortage isn't a stock number.",
    subhead: "It's interrupted care.",
    body: 'Every point below is a scheduled appointment already recorded against this facility.',
  },
  candidates: {
    eyebrow: 'Candidate sources',
    headline: "The closest supply isn't always the safest choice.",
    body: 'Each option is tested against the donor’s own forecast, its safety floor, transit time and expiry pressure.',
  },
  intervention: {
    eyebrow: 'Recommended intervention',
    body: 'Rejected options stay visible. A recommendation you can audit is worth more than one you have to trust.',
  },
  realityLens: {
    eyebrow: 'Reality lens',
    headline: 'The record and the shelf disagree.',
    body: 'Field evidence from the donor facility. Extraction is automatic; the correction is not.',
    awaiting: 'Awaiting coordinator confirmation — nothing has recalculated',
    confirmed: 'Demo: coordinator confirmed — network recalculated',
    principle: 'Reliable decisions need verified evidence and human review.',
  },
  cascade: {
    eyebrow: 'Correction cascade',
    headline: 'The chosen donor was the wrong one.',
    body: 'One confirmed correction propagates through the same network: inventory, forecast, facility risk, care exposure, and the plan itself.',
  },
  recovery: {
    eyebrow: 'Verified recovery',
    headline: 'Dispatched is only the beginning.',
    subhead: 'Recovery needs evidence at both ends.',
  },
  closing: {
    eyebrow: 'Loop closed',
    headlineSuffix: 'care events protected.',
    subhead: 'Resilience loop closed.',
    body: 'Predict earlier. Intervene smarter. Verify reality.',
    note: 'Same district. Same fourteen facilities. Nothing on this map moved — only what we knew about it, and what we did about it.',
    primaryCta: 'Explore Demo District',
    secondaryCta: 'Sign in',
  },
  capabilities: {
    eyebrow: 'Built for real health-system decisions',
    items: [
      {
        key: 'predict',
        title: 'Predict',
        lead: 'Care-aware forecasting',
        body: 'Demand is read from scheduled care obligations, not from a reorder threshold. A facility can be flagged while its shelf still looks full.',
      },
      {
        key: 'intervene',
        title: 'Intervene',
        lead: 'Constraint-aware recovery',
        body: 'Every candidate donor is checked against its own forecast, safety floor, transit window and expiry pressure before it is proposed.',
      },
      {
        key: 'verify',
        title: 'Verify',
        lead: 'Evidence before closure',
        body: 'A dispatch is not a resolution. The loop closes only when source, destination, batch and protected care all confirm.',
      },
    ],
  },
  foundation: {
    eyebrow: 'Foundation',
    body: 'Designed to run on Google Cloud — Gemini for multimodal field evidence, BigQuery for demand and consumption history, Cloud Run for the forecasting and intervention services.',
    items: ['Gemini · multimodal evidence', 'BigQuery · demand history', 'Cloud Run · services', 'Firebase · hosting'],
  },
} as const;

/** Single place the demo-scenario disclosure is worded. */
export const disclosure =
  'All figures shown are from a fixed, seeded demonstration district. No live patient or facility data is used.';
