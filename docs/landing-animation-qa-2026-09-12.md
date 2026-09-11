# Landing interaction QA — 12 September 2026

This pass preserves the existing visual direction and the approved 0.8-second card entry/return timing.

## Fixed

- Chapter navigation disappears as the footer approaches (80px early), then returns above the footer.
- Visible section numbering now follows all seven chapters.
- Repeated chapter clicks cancel the previous smooth scroll. The final click determines the destination; previously the URL could say District while scrolling stopped at Connect.
- Card drags clean up after release, pointer cancellation, lost capture, or window focus loss. Selecting another card remains exclusive.
- Hover effects apply to hover-capable pointers; touch interaction no longer flattens the resting card.
- Every supply corridor and facility reaches its full reveal at the end of Connect, and scroll reversal rewinds the reveal.
- The sleeve has one close arrow above its content, retains keyboard focus on closing, and each map uses distinct SVG/panel IDs.
- The exposure caption sits below facility names instead of crossing CHC A and CHC B.
- Small informational labels were raised to 12px in the principal landing, network, horizon and footer styles. Footer metadata contrast was increased.

## Browser checks

Checked the local page in Microsoft Edge using an isolated browser profile.

| Check | Result |
| --- | --- |
| Footer approach, footer bottom, and reverse scrolling | Pass |
| Seven section numbers and chapter destinations | Pass |
| Drag beyond the card, release, cancellation, lost capture, focus loss | Pass |
| Rapid card switching; outside press returns cards | Pass |
| Single-card hover and 0.8s selected-card transition | Pass |
| Fast Connect traversal; halfway reverse; start and end geometry | Pass |
| Repeated Play/Pause; pause holds value; stop at 30; replay from start | Pass |
| Open/close sleeve during playback; arrow hit target; Escape/focus | Pass |
| Keyboard slider takeover stops playback | Pass |
| Confirmation gates receipt completion; reset clears confirmation | Pass |
| Actual chapter-link clicks and rapid changes of destination | Pass |
| Reduced-motion transitions and amber pulse | Pass |
| 390 × 844 horizontal layout and horizon containment | Pass |
| 1366 × 768 Connect labels clear of chapter navigation | Pass |
| Runtime exceptions during the checks | None |
| TypeScript and production build | Pass (`npm run build`) |

The captures are a UI demonstration, not evidence of real medical outcomes or a validation of backend calculations. Separate backend/scenario edits were present during this pass and are excluded from this UI commit.

## Recording and readability

The Desktop screenshot folder has a QA subfolder containing:

- PNG and heavily compressed JPEG captures at 1920 × 1080.
- `animation-1080p-compressed.mp4`: a roughly 15-second browser capture of Connect reversing, horizon playback, and the sleeve. H.264 CRF 36, 4:2:0, encoded at 30fps.
- `projector-stress-proxy.mp4`: the same capture downsampled to 720p and enlarged to 1080p, with slight blur, lower contrast/saturation, lifted blacks, and another compression pass.
- `final-connect.png`, JSON check results, and extracted video frames.

Main headings, facility names, values and controls remain readable in the proxy. Small metadata softens noticeably under the strongest degradation; the faint geographical labels remain decorative. A real projector/room check is still necessary. Browser capture uses variable frame delivery, so the encoded 30fps file is a readability stress test, not a claim of measured 30fps or 60fps application performance.

## CSS cleanup

ConnectionSceneFix was folded into ConnectionScene; LayerLayoutFix into LandingPageNew; TimelineFix and TimelineGlow into RecoveryTimeline. SleeveFix was removed after repairing the original close control. Unused selectors targeting CSS-module class names from global CSS were removed.

Older component styles remain where unrelated to this pass. The cleanup does not claim to have rewritten every historical stylesheet.
