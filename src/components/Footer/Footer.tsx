import { Link } from 'react-router-dom';
import { BrandWordmark } from '../../brand/BrandMark';
import { brand, nav, routes } from '../../brand/brand.config';
import styles from './Footer.module.css';

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <Link to={routes.home} aria-label="Home">
          <BrandWordmark size={24} withTagline />
        </Link>

        <nav className={styles.links} aria-label="Footer">
          {nav.links.map((l) => (
            <a key={l.href} href={l.href}>
              {l.label}
            </a>
          ))}
          <Link to={routes.demo}>Demo District</Link>
          <Link to={routes.signIn}>{nav.signIn}</Link>
        </nav>

        <p className={styles.note}>{brand.footerNote}</p>
      </div>
    </footer>
  );
}
