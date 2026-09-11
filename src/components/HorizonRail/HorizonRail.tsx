import { useCallback, useRef } from 'react';
import { Pause, Play } from 'lucide-react';
import styles from './HorizonRail.module.css';
import playStyles from './HorizonPlay.module.css';

interface Props {
  stops: number[];
  /** Current horizon in days. */
  day: number;
  /** Care events exposed at this horizon — summed, never counted up. */
  exposed: number;
  visible: number;
  /**
   * Called when the visitor takes manual control of the horizon. `null` hands
   * control back to the story.
   */
  onScrub?: (day: number | null) => void;
  /** True while the visitor is steering rather than the scroll. */
  scrubbing?: boolean;
  playing?: boolean;
  onPlayToggle?: () => void;
}

/**
 * The horizon rail.
 *
 * Not a tab bar and not a scrubber for hidden state: it is a threshold. As it
 * advances, facilities ignite in the order they are predicted to fail, and the
 * exposure total to its right is the sum of everything already past it.
 *
 * It is genuinely interactive — drag it, or focus it and use the arrow keys —
 * because the whole argument of the product is that time-to-failure is
 * something an operator should be able to interrogate, not just watch.
 */
export function HorizonRail({ stops, day, exposed, visible, onScrub, scrubbing = false, playing = false, onPlayToggle }: Props) {
  const trackRef = useRef<HTMLDivElement>(null);
  const max = stops[stops.length - 1];
  const pct = (day / max) * 100;
  const atNow = day < 0.4;
  const interactive = !!onScrub && visible > 0.6;

  const dayFromClientX = useCallback(
    (clientX: number) => {
      const el = trackRef.current;
      if (!el) return 0;
      const r = el.getBoundingClientRect();
      const t = Math.min(1, Math.max(0, (clientX - r.left) / r.width));
      return Math.round(t * max * 10) / 10;
    },
    [max],
  );

  const onPointerDown = (e: React.PointerEvent) => {
    if (!interactive) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    onScrub?.(dayFromClientX(e.clientX));
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!interactive || !e.currentTarget.hasPointerCapture?.(e.pointerId)) return;
    onScrub?.(dayFromClientX(e.clientX));
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!interactive) return;
    const step = e.shiftKey ? 5 : 1;
    if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
      e.preventDefault();
      onScrub?.(Math.min(max, day + step));
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
      e.preventDefault();
      onScrub?.(Math.max(0, day - step));
    } else if (e.key === 'Home') {
      e.preventDefault();
      onScrub?.(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      onScrub?.(max);
    } else if (e.key === 'Escape') {
      onScrub?.(null);
    }
  };

  return (
    <div className={styles.rail} style={{ opacity: visible }} aria-hidden={visible < 0.4}>
      <div className={styles.box} data-scrubbing={scrubbing}>
        <span className={styles.caption}>HORIZON</span>
        {onPlayToggle && <button type="button" className={playStyles.playButton} onClick={onPlayToggle} aria-pressed={playing} aria-label={playing ? 'Pause horizon playback' : 'Play horizon playback'}>{playing ? <Pause size={13} fill="currentColor" /> : <Play size={13} fill="currentColor" />}<span>{playing ? 'Pause' : 'Play'}</span></button>}

        <div
          ref={trackRef}
          className={styles.track}
          data-interactive={interactive}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onKeyDown={onKeyDown}
          role={interactive ? 'slider' : undefined}
          tabIndex={interactive ? 0 : -1}
          aria-label="Forecast horizon in days"
          aria-valuemin={0}
          aria-valuemax={max}
          aria-valuenow={Math.round(day)}
          aria-valuetext={atNow ? 'Today' : `${Math.round(day)} days ahead — ${exposed} care events exposed`}
        >
          <span className={styles.bar} />
          <span className={styles.fill} style={{ width: `${pct}%` }} />
          {stops.map((s) => (
            <span key={s} className={styles.stop} style={{ left: `${(s / max) * 100}%` }}>
              <em>{s === 0 ? 'NOW' : `${s}D`}</em>
            </span>
          ))}
          <span className={styles.head} style={{ left: `${pct}%` }} />
        </div>

        <span className={`${styles.day} num`}>{atNow ? 'NOW' : `+${day.toFixed(1)} d`}</span>

        <span className={`${styles.exposed} num`} style={{ opacity: exposed > 0 ? 1 : 0 }}>
          {exposed} care events exposed
        </span>
      </div>

      <span className={styles.affordance} data-shown={interactive}>
        {scrubbing ? 'Esc or scroll to resume the story' : 'Drag the horizon — or use ← →'}
      </span>
    </div>
  );
}
