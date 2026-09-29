# UI-1 implementation and review notes

The authenticated workspace runs from `src/app/mock.ts` through a typed
`WorkspaceProvider` boundary. It makes no backend requests. Google sign-in,
operational mode, roles, evidence decisions and recovery actions are explicitly
local UI previews.

## Review entry points

- `/login`: mock Google entry, district chooser and onboarding draft.
- `/app`: Situation Room, closest to the approved visual reference.
- `/app/network`: selectable schematic facility graph and context inspector.
- `/app/facilities` and `/app/facilities/:facilityId`: filters and five workspaces.
- `/app/cases` and `/app/cases/:caseId`: intervention comparison and lineage.
- `/app/evidence` and `/app/evidence/:evidenceId`: review lanes, comparison and confirmation.
- `/app/recovery`: explicit supply and care milestones.
- `/app/intelligence`: readiness, sources, gaps and future source review.
- `/app/settings`: mock role, mode, notifications and coordinator reset.
- Ask Haven: header button or Ctrl/Command+K; Escape dismisses the panel.

The full scenario identifier is `case-lahunipada-ifa-red-rehearsal-001`.
Useful evidence identifiers are `bonai-count`, `laing-recount` and
`mangaspur-conflict`.

## Visual construction

Scoped `hv-` styles keep the public landing page's visual rules isolated.
Ivory/sage raised surfaces use multiple inset highlights, low-opacity ambient
shadows and restrained gradients. The forest network has a vignette, schematic
subdivision outlines, radial lighting, spherical node gradients and directional
routes. These are responsive SVG/CSS, not a flattened reference screenshot.
The schematic is intentionally not an authoritative district boundary map.

The reference's illustrative graph labels are not reused. The seven approved
verified/corroborated roster identities replace them. Laing and Mangaspur retain
corroborated currentness. Supplemental pending recounts are labelled UI rehearsal
fixtures and are not public or backend-derived facts.

## State and provenance boundaries

Six provenance classes map to human-readable disclosure badges. Route values
are explicitly captured responses rather than live traffic. Unknown packaging,
official facility inventory and facility denominators remain visible.

Evidence confirmation changes the local canonical display and preserves the
previous count in the record. Only the primary approved intervention has a
scripted recovery lifecycle. Supplemental recounts do not claim to recalculate
the deterministic backend. A future adapter must reevaluate affected plans.

Coverage restored and care delivery verified are separate milestones.
UNKNOWN, NOT_DELIVERED and DEFERRED cannot advance care verification.
Viewers have no evidence/recovery write controls; field reviewers can perform
verification; coordinators approve and close. These are UI capabilities,
not security enforcement. No Auth, Firestore, Vertex or Gemini is connected.

District selection, role, mode and local decisions persist in sessionStorage.
Sambalpur and Kalahandi have lightweight readiness shells with no leaked
Sundargarh facility or case content. New organization onboarding creates only
an on-screen draft, not an account or external organization.

## Validation

`npm test`: 32 passing tests, including all 26 existing frontend tests.
`npm run build`: TypeScript and Vite production build pass.
No lint script is configured.

Browser QA is in `scripts/qa-workspace.cjs`. This local runner uses the bundled
Playwright runtime and installed Edge, and writes `qa-results.json`.
It checks 12 major pages at both 1440×900 and 1920×1080, plus narrower
Situation Room views. It also exercises evidence confirmation, role restrictions,
district persistence, mode visibility, recovery gates, global Ask Haven,
facility filters/tabs, keyboard node inspection, mock login and onboarding.

Screenshots are in `docs/ui-1/screenshots/`. Long workspaces deliberately scroll
vertically. The primary judging layouts have no horizontal overflow.
Reduced-motion rules suppress decorative transitions and route animation.

## Integration expected later

Replace the mock provider with an adapter for JudgeScenarioContract,
DistrictProfile, DistrictReadiness, Facility, CoverageAssessment, CareImpact,
EvidenceRecord, RecoveryCase and CareDeliveryRecord. The UI must retain source
class, source timestamp, uncertainty, canonical lineage and distinct coverage/
care milestones. Authentication and server-authorized commands are separate
future work.

## Scope protection

No backend or raw data files were changed during UI-1.
The public landing component and its visual assets were not edited.
Only App routing changed to replace the old demo/sign-in placeholders and
add the new workspace routes. Pre-existing repository changes were preserved.

## Known limits

This is a frontend mock workspace, not an authenticated operational deployment.
The main rehearsal begins after Bonai confirmation/replanning. Historical
invalidation is shown with the original evidence and route treatment; this
phase does not replay the backend's deterministic recalculation.
The narrow mobile graph is a compact overview; facility inspection/list views
provide readable detail. Uploaded artifacts, live refresh and AI answers are
intentionally absent.
