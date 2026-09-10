import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { BrandWordmark } from '../brand/BrandMark';
import { routes } from '../brand/brand.config';
import styles from './Placeholder.module.css';

interface Props {
  eyebrow: string;
  title: string;
  body: string;
}

/**
 * Honest placeholder.
 *
 * Phase UI-0 covers the welcome experience only. These routes exist so the
 * primary CTA lands somewhere real rather than a dead anchor — deliberately
 * NOT a mock dashboard, which would misrepresent what has been built.
 */
export default function Placeholder({ eyebrow, title, body }: Props) {
  return (
    <main className={styles.page}>
      <div className={styles.aurora} aria-hidden="true">
        <i />
        <i />
      </div>
      <div className={styles.card}>
        <BrandWordmark size={30} withTagline />
        <span className={`eyebrow ${styles.eyebrow}`}>{eyebrow}</span>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.body}>{body}</p>
        <Link to={routes.home} className={styles.back}>
          <ArrowLeft size={15} strokeWidth={1.8} aria-hidden="true" />
          Back to the story
        </Link>
      </div>
    </main>
  );
}
