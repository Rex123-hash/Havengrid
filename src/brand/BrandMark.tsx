import { brand } from './brand.config';
import styles from './BrandMark.module.css';

/**
 * The only place the product mark is drawn.
 *
 * The glyph is deliberately geometric — a node with two supply links resolving
 * into it — rather than a leaf, cross or heart. It reads as infrastructure, and
 * it survives a rename because it carries no letterform.
 */
export function BrandGlyph({ size = 28 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className={styles.glyph}
    >
      <path
        d="M16 3.4 27 9.7v12.6L16 28.6 5 22.3V9.7z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
        opacity="0.42"
      />
      <path d="M10.4 19.6 16 16l5.6-3.6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" opacity="0.7" />
      <path d="M16 16v6.6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" opacity="0.7" />
      <circle cx="16" cy="16" r="3.1" fill="currentColor" />
      <circle cx="10.4" cy="19.6" r="1.7" fill="currentColor" opacity="0.55" />
      <circle cx="21.6" cy="12.4" r="1.7" fill="currentColor" opacity="0.55" />
    </svg>
  );
}

type WordmarkProps = {
  size?: number;
  withTagline?: boolean;
};

export function BrandWordmark({ size = 28, withTagline = false }: WordmarkProps) {
  const head = brand.name.slice(0, brand.wordmarkAccentFrom);
  const tail = brand.name.slice(brand.wordmarkAccentFrom);

  return (
    <span className={styles.lockup}>
      <span className={styles.mark} style={{ width: size, height: size }}>
        <BrandGlyph size={size} />
      </span>
      <span className={styles.text}>
        <span className={styles.word} style={{ fontSize: size * 0.62 }}>
          {head}
          {tail && <span className={styles.accent}>{tail}</span>}
        </span>
        {withTagline && <span className={styles.tagline}>{brand.tagline}</span>}
      </span>
    </span>
  );
}
