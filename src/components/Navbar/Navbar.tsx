import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { BrandWordmark } from '../../brand/BrandMark';
import { nav, routes } from '../../brand/brand.config';
import styles from './Navbar.module.css';

/**
 * Minimal top bar. Glass surface #1 of three.
 *
 * It gains a border and a stronger blur only after the page has left the top,
 * so the arrival frame is uninterrupted.
 */
export function Navbar() {
  const [lifted, setLifted] = useState(false);

  useEffect(() => {
    const onScroll = () => setLifted(window.scrollY > 24);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={styles.bar} data-lifted={lifted}>
      <nav className={styles.inner} aria-label="Primary">
        <Link to={routes.home} className={styles.brand} aria-label="Home">
          <BrandWordmark size={26} withTagline />
        </Link>

        <ul className={styles.links}>
          {nav.links.map((l) => (
            <li key={l.href}>
              <a href={l.href} className={styles.link}>
                {l.label}
              </a>
            </li>
          ))}
        </ul>

        <div className={styles.actions}>
          <Link to={routes.signIn} className={styles.signIn}>
            {nav.signIn}
          </Link>
          <Link to={routes.demo} className={styles.cta}>
            <span className={styles.ctaFull}>{nav.primaryCta}</span>
            <span className={styles.ctaShort}>{nav.primaryCtaShort}</span>
            <ArrowRight size={15} strokeWidth={1.8} aria-hidden="true" />
          </Link>
        </div>
      </nav>
    </header>
  );
}
