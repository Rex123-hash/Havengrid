import { Activity, ShieldCheck, Waypoints } from 'lucide-react';
import { copy, disclosure } from '../../brand/brand.config';
import styles from './SupportingBand.module.css';

const ICONS = {
  predict: Activity,
  intervene: Waypoints,
  verify: ShieldCheck,
} as const;

/**
 * The only section after the story.
 *
 * Three concepts and one foundation line — deliberately not a feature grid.
 * The story above already demonstrated the product; this exists to name the
 * three things it demonstrated.
 */
export function SupportingBand() {
  return (
    <section id="capabilities" className={styles.band}>
      <div className={styles.inner}>
        <span className="eyebrow">{copy.capabilities.eyebrow}</span>

        <div className={styles.grid}>
          {copy.capabilities.items.map((item, i) => {
            const Icon = ICONS[item.key as keyof typeof ICONS];
            return (
              <article key={item.key} className={styles.item}>
                <span className={styles.index}>{String(i + 1).padStart(2, '0')}</span>
                <span className={styles.icon}>
                  <Icon size={18} strokeWidth={1.5} aria-hidden="true" />
                </span>
                <h3 className={styles.title}>{item.title}</h3>
                <p className={styles.lead}>{item.lead}</p>
                <p className={styles.body}>{item.body}</p>
              </article>
            );
          })}
        </div>

        <div className={styles.foundation}>
          <div className={styles.foundationCopy}>
            <span className="eyebrow">{copy.foundation.eyebrow}</span>
            <p>{copy.foundation.body}</p>
          </div>
          <ul className={styles.chips}>
            {copy.foundation.items.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        </div>

        <p className={styles.disclosure}>{disclosure}</p>
      </div>
    </section>
  );
}
