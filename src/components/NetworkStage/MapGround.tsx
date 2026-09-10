import styles from './NetworkStage.module.css';

/** An open schematic: geographic context fades away without a fabricated district boundary. */
export function MapGround() {
  return (
    <g aria-hidden="true" className={styles.ground}>
      <defs>
        <radialGradient id="terrain-fade">
          <stop offset="20%" stopColor="white" stopOpacity=".8" />
          <stop offset="70%" stopColor="white" stopOpacity=".35" />
          <stop offset="100%" stopColor="white" stopOpacity="0" />
        </radialGradient>
        <mask id="terrain-mask"><ellipse cx="500" cy="310" rx="480" ry="295" fill="url(#terrain-fade)" /></mask>
      </defs>
      <g mask="url(#terrain-mask)" fill="none" strokeLinecap="round">
        <path d="M-40 265 C100 214 185 296 300 258 S453 259 535 316 S689 338 756 380 S908 438 1040 416" stroke="#95cbb9" strokeWidth="3" />
        <path d="M215 675 C280 546 417 490 459 419 S488 340 535 316" stroke="#a9d2c2" strokeWidth="1.5" />
        <path d="M45 106 L183 150 266 133 350 172 406 219 515 231 596 191 733 215 879 162 1020 195 M34 421 L188 399 272 442 367 421 447 468 571 447 667 495 795 458 1030 507" stroke="#a5baaf" strokeWidth=".8" strokeDasharray="3 6" />
      </g>
      <text x="216" y="176" className={styles.groundLabel}>BONAI</text>
      <text x="560" y="136" className={styles.groundLabel}>HEMGIR</text>
      <text x="706" y="478" className={styles.groundLabel}>KUCHINDA</text>
      <text x="272" y="508" className={styles.groundLabel}>LAHUNIPADA</text>
    </g>
  );
}
