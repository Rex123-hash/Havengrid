import styles from './NetworkStage.module.css';
import { hexPath } from './geometry';
/** A quiet coordinate lattice, not invented geographic boundaries or live coverage. */
export function MapGround() {
  return <g aria-hidden="true" className={styles.ground}>
    <defs><radialGradient id="lattice-fade"><stop offset="20%" stopColor="white"/><stop offset="100%" stopColor="white" stopOpacity="0"/></radialGradient><mask id="lattice-mask"><ellipse cx="480" cy="310" rx="510" ry="340" fill="url(#lattice-fade)"/></mask></defs>
    <g mask="url(#lattice-mask)">
      {Array.from({length:19},(_,col)=>Array.from({length:12},(_,row)=>{
        const x=col*55,y=row*63.5+(col%2?31.75:0)-40;
        return <path key={`${col}-${row}`} d={hexPath(x,y,35)} fill="none" stroke="#85cdb3" strokeWidth=".65" opacity=".12"/>;
      }))}
      <path d="M-40 265 C100 214 185 296 300 258 S453 259 535 316 S689 338 756 380 S908 438 1040 416" fill="none" stroke="#82bfa9" strokeWidth="2" opacity=".12"/>
    </g>
    <text x="195" y="175" className={styles.groundLabel}>BONAI</text><text x="550" y="128" className={styles.groundLabel}>HEMGIR</text><text x="725" y="485" className={styles.groundLabel}>KUCHINDA</text>
  </g>;
}
