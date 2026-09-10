import { useEffect, useRef, useState } from 'react';

/**
 * The single scroll value that drives the entire story.
 *
 * Deliberately NOT a wheel handler. Nothing is intercepted, nothing calls
 * preventDefault, and native scrolling — trackpad, keyboard, scrollbar drag,
 * touch, find-in-page — behaves exactly as the user expects. The story is a
 * pure function of where the page happens to be.
 *
 * Returns 0 → 1 across the scrollable span of the referenced container.
 */
export function useStoryProgress(ref: React.RefObject<HTMLElement>) {
  const [progress, setProgress] = useState(0);
  const frame = useRef(0);
  const last = useRef(-1);

  useEffect(() => {
    const measure = () => {
      const el = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const span = rect.height - window.innerHeight;
      const next = span <= 0 ? 0 : Math.min(1, Math.max(0, -rect.top / span));
      // Skip sub-pixel churn so React is not re-rendered for invisible deltas.
      if (Math.abs(next - last.current) < 0.0004) return;
      last.current = next;
      setProgress(next);
    };

    const onScroll = () => {
      if (frame.current) return;
      frame.current = requestAnimationFrame(() => {
        frame.current = 0;
        measure();
      });
    };

    measure();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current);
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    };
  }, [ref]);

  return progress;
}

/**
 * Pins an element to the real viewport height.
 *
 * `100vh` is unreliable — mobile browser chrome changes it, and an embedded
 * frame can report a different value than it paints. Measuring the same
 * `innerHeight` the progress hook uses keeps the stage and the scroll maths in
 * agreement.
 */
export function useViewportHeight(ref: React.RefObject<HTMLElement>, min = 560) {
  useEffect(() => {
    const fit = () => {
      if (ref.current) ref.current.style.height = `${Math.max(min, window.innerHeight)}px`;
    };
    fit();
    window.addEventListener('resize', fit, { passive: true });
    window.addEventListener('orientationchange', fit);
    return () => {
      window.removeEventListener('resize', fit);
      window.removeEventListener('orientationchange', fit);
    };
  }, [ref, min]);
}

export function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(
    () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
  );
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const on = () => setReduced(mq.matches);
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);
  return reduced;
}
