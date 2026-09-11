import { Link } from 'react-router-dom';
import { BrandWordmark } from '../../brand/BrandMark';
import { brand, disclosure, nav, routes } from '../../brand/brand.config';
import styles from './FooterRefined.module.css';

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.top}>
          <div className={styles.brandBlock}>
            <Link to={routes.home} aria-label="Home"><BrandWordmark size={28} withTagline /></Link>
            <p>See the supply signal before it becomes missed care.</p>
            <span className={styles.location}>Illustrative district · Sundargarh, Odisha</span>
          </div>
          <div className={styles.columns}>
            <div className={styles.column}><span className={styles.label}>Explore</span>{nav.links.map((l) => <a key={l.href} href={l.href}>{l.label}</a>)}</div>
            <div className={styles.column}><span className={styles.label}>Inside the demo</span><a href="#connect">District connection</a><a href="#evidence">Reality Lens</a><a href="#closing">Verified recovery</a></div>
            <div className={styles.column}><span className={styles.label}>Access</span><Link to={routes.demo}>Demo District</Link><Link to={routes.signIn}>{nav.signIn}</Link></div>
          </div>
        </div>
        <div className={styles.bottom}><p>{brand.footerNote}</p><p>{disclosure}</p><span>© 2026 {brand.name} · Demonstration experience</span></div>
      </div>
    </footer>
  );
}
