import { useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowRight, Check, Layers3, Package, CalendarDays, Truck, ScanLine, ShieldCheck, RotateCcw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Navbar } from '../components/Navbar/Navbar';
import { Footer } from '../components/Footer/Footer';
import { NetworkStage } from '../components/NetworkStage/NetworkStage';
import { HorizonRail } from '../components/HorizonRail/HorizonRail';
import { landingScenario as s } from '../data/landingScenario';
import { deriveStoryState } from '../story/deriveStoryState';
import { usePrefersReducedMotion } from '../hooks/useStoryProgress';
import { routes } from '../brand/brand.config';
import styles from './LandingPageNew.module.css';
import './ConnectionScene.css';
import './ConnectionSceneFix.css';
import './TimelineFix.css';
import './TimelineGlow.css';
import layerCardStyles from './LayerCards.module.css';

const chapters = [['opening','Begin'],['care','Care'],['connect','Connect'],['story','District'],['explore-features','Act'],['evidence','Verify'],['closing','Recover']];
const layers = [
  { label: 'Scheduled care', value: s.item.projectedDemand, unit: 'units needed', icon: CalendarDays, detail: 'Demand across the next 14 days, connected to appointments already scheduled.' },
  { label: 'Available stock', value: s.item.currentStock, unit: 'units on hand', icon: Package, detail: 'Current inventory at Bhatpar PHC. Enough for today, but not for the full care window.' },
  { label: 'Incoming supply', value: s.item.replenishmentEtaDays, unit: 'days to arrival', icon: Truck, detail: 'The next replenishment arrives after the predicted shortage on day 6.' },
];

function useSceneProgress(ref: React.RefObject<HTMLElement>) {
  const [progress, setProgress] = useState(0);
  useEffect(() => {
    let frame = 0;
    const measure = () => {
      const el = ref.current;
      if (!el) return;
      const span = Math.max(1, el.offsetHeight - window.innerHeight);
      setProgress(Math.max(0, Math.min(1, -el.getBoundingClientRect().top / span)));
    };
    const onScroll = () => { if (!frame) frame = requestAnimationFrame(() => { frame = 0; measure(); }); };
    measure();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', measure);
    return () => { cancelAnimationFrame(frame); window.removeEventListener('scroll', onScroll); window.removeEventListener('resize', measure); };
  }, [ref]);
  return progress;
}

export default function LandingPage() {
  const root = useRef<HTMLElement>(null);
  const connectionRef = useRef<HTMLElement>(null);
  const closingRef = useRef<HTMLElement>(null);
  const [active, setActive] = useState('opening');
  const [layer, setLayer] = useState<number | null>(null);
  const [cohort, setCohort] = useState(0);
  const [day, setDay] = useState(7);
  const [mapMode, setMapMode] = useState('Risk');
  const [donor, setDonor] = useState('chc-d');
  const [confirmed, setConfirmed] = useState(false);
  const [step, setStep] = useState(0);
  const reducedMotion = usePrefersReducedMotion();
  const connectionProgress = useSceneProgress(connectionRef);
  const recoveryProgress = useSceneProgress(closingRef);
  const mapState = deriveStoryState(confirmed ? .81 : mapMode === 'Supply routes' ? .59 : .3, s, day);
  const displayedLayer = layer ?? 0;
  const candidate = s.candidates.find(c => c.facilityId === donor)!;
  const invalidated = confirmed && donor === 'chc-d';
  const revised = confirmed && donor === 'chc-b';
  const reason = invalidated ? 'Field count is below the donor safety floor. This source can no longer release stock.' : revised ? s.replan.reason : candidate.reason;
  const scrollStep = Math.min(s.verification.length, Math.floor(recoveryProgress * (s.verification.length + 1)));
  const shownStep = Math.max(step, scrollStep);
  const complete = shownStep === s.verification.length;
  useEffect(() => {
    const sections = root.current?.querySelectorAll<HTMLElement>('[data-scene]');
    if (!sections) return;
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add(styles.entered); setActive(entry.target.id); } });
    }, { rootMargin: '-20% 0px -35% 0px', threshold: 0 });
    sections.forEach(el => observer.observe(el));
    return () => observer.disconnect();
  }, []);
  return <><Navbar/><main ref={root} id="main-content" className={styles.experience}>
    <section id="opening" data-scene className={`${styles.scene} ${styles.opening}`}>
      <div className={styles.heroCopy}><p className={styles.eyebrow}>CARE-AWARE SUPPLY RESILIENCE</p><h1>Tomorrow’s care.<br/><em>Protected today.</em></h1><p className={styles.lead}>A full shelf today can hide a shortage tomorrow. See what care will need next—and act while there’s still time.</p><a className={styles.primary} href="#care">Follow one care journey <ArrowDown size={19}/></a><p className={styles.caption}>Sundargarh, Odisha · Illustrative district</p></div>
      <div className={styles.layerScene} onClick={e => { if (!(e.target as HTMLElement).closest('button')) setLayer(null); }}><div className={styles.orbit}/><div className={styles.layerStack}>
        {layers.map((l,i) => <button key={l.label} aria-pressed={layer === i} onClick={() => setLayer(i)} className={`${styles.plane} ${layerCardStyles.card}`} data-selected={layer===i} data-active={layer===i} style={{'--i':i} as React.CSSProperties}><span className={styles.planeTop}><l.icon size={24}/><span>0{i+1} / {l.label}</span><ArrowRight size={19}/></span><strong>{l.value}<small>{l.unit}</small></strong><span className={styles.miniBars}>{Array.from({length:14},(_,j)=><i key={j} style={{height:`${24+((j*17+i*11)%48)}px`}}/>)}</span></button>)}
      </div><div className={styles.layerNote} aria-live="polite"><Layers3 size={19}/><p><b>{layers[displayedLayer].label}</b>{layers[displayedLayer].detail}</p></div></div>
      <div className={styles.heroFoot}><span>01 — See the signals together</span><a href="#care">Discover the gap <ArrowDown size={16}/></a></div>
    </section>
    <section id="care" data-scene className={`${styles.scene} ${styles.consequence}`}>
      <div className={styles.bridge}><span>THE SIGNAL BECOMES A CONSEQUENCE</span><i/><ArrowDown size={20}/></div>
      <div className={styles.sectionHead}><p className={styles.eyebrow}>02 / THE CARE BEHIND THE COUNT</p><h2>A shortage is never<br/>just a number.</h2><p>{s.item.projectedDemand} needed. {s.item.currentStock} available. A gap of {s.item.projectedDemand-s.item.currentStock} units puts {s.totalCareEventsExposed} scheduled care events at risk.</p></div>
      <div className={styles.impactStage}><span className={styles.giant} aria-hidden="true">44</span><div className={styles.cohorts}>{s.careCohorts.map((c,i)=><button key={c.key} onClick={()=>setCohort(i)} aria-pressed={cohort===i} data-selected={cohort===i}><span>0{i+1} / {c.label}</span><strong>{c.count}</strong><p>{c.detail}</p><ArrowRight size={22}/></button>)}</div><div className={styles.people} aria-live="polite"><div>{Array.from({length:23},(_,i)=><i key={i} data-lit={i<s.careCohorts[cohort].count}/>)}</div><p><b>{s.careCohorts[cohort].count} of {s.totalCareEventsExposed}</b> care events · {s.careCohorts[cohort].label}</p></div></div>
    </section>
    <section id="connect" data-scene ref={connectionRef} className="connectionScene">
      <div className="connectionSticky">
        <div className="connectionCopy"><p className={styles.eyebrow}>03 / BUILD THE PICTURE</p><h2>Watch the district<br/><em>come online.</em></h2><p>As the horizon opens, facilities surface, corridors connect, and one care risk becomes visible across the whole network.</p><div className="connectionMeter"><span style={{width:`${connectionProgress*100}%`}}/><b>{connectionProgress < .33 ? 'Finding facilities' : connectionProgress < .7 ? 'Tracing corridors' : 'District connected'}</b></div><div className="connectionSteps"><span data-active={connectionProgress>.08}><i>01</i>Facilities</span><span data-active={connectionProgress>.36}><i>02</i>Supply corridors</span><span data-active={connectionProgress>.72}><i>03</i>Care risk</span></div><p className="scrollPrompt"><ArrowDown size={15}/> Continue scrolling to enter the district</p></div>
        <div className="connectionMap"><NetworkStage scenario={s} state={deriveStoryState(connectionProgress*.44, s, connectionProgress*14)} reducedMotion={reducedMotion} connectionProgress={connectionProgress}/></div>
      </div>
    </section>
    <section id="story" data-scene className={`${styles.scene} ${styles.district}`}>
      <div className={styles.sectionHead}><p className={styles.eyebrow}>03 / THE DISTRICT IN VIEW</p><h2>See where time<br/><em>is running short.</em></h2><p>Move the horizon. Inspect a facility. Find the point where supply stops keeping pace with care.</p></div>
      <div className={styles.mapMeta}><span>SUNDARGARH, ODISHA <small>ILLUSTRATIVE DISTRICT</small></span><div className={styles.segment}>{['Risk','Supply routes','Freshness'].map(m=><button key={m} aria-pressed={mapMode===m} onClick={()=>setMapMode(m)}>{m}</button>)}</div></div>
      <div className={styles.mapFrame}><NetworkStage scenario={s} state={mapState} reducedMotion={reducedMotion}/></div>
      <div className={styles.legend}><span><i/>On track</span><span><i/>Tight</span><span><i/>Breach</span><span><i/>No forecast</span></div>
      <HorizonRail stops={s.horizonStops} day={day} exposed={mapState.careEventsExposed} visible={1} onScrub={d=>setDay(d??7)} scrubbing/>
      {mapMode==='Freshness' && <div className={styles.freshness}>{s.facilities.map(f=><span key={f.id}><b>{f.short}</b>{f.daysSinceVerified}d since verified</span>)}</div>}
    </section>
    <section id="explore-features" data-scene className={`${styles.scene} ${styles.intervention}`}>
      <div className={styles.sectionHead}><p className={styles.eyebrow}>04 / INTERVENTION STUDIO</p><h2>The nearest stock<br/>isn’t always the answer.</h2><p>Compare possible donors. Protect Bhatpar without creating a shortage somewhere else.</p></div>
      <div className={styles.donorStudio}><div className={styles.donorList}>{s.candidates.map(c=><button key={c.id} aria-pressed={donor===c.facilityId} onClick={()=>setDonor(c.facilityId)}><span>{c.facilityName}<small>{c.distanceKm} km · {c.transitHours} h transit</small></span><ArrowRight size={20}/></button>)}</div><div className={styles.donorDetail} aria-live="polite"><span className={styles.eyebrow}>{invalidated?'SOURCE RULED OUT':revised?'REVISED PLAN':candidate.verdict==='chosen'?'INITIAL PLAN':candidate.verdict==='held'?'FALLBACK OPTION':'NOT VIABLE'}</span><h3>{candidate.facilityName}</h3><div className={styles.transfer}><Package size={40}/><span/><Truck size={32}/><span/><ShieldCheck size={40}/></div><div className={styles.metrics}><div><strong>{invalidated?0:candidate.surplus}</strong><span>units above reserve</span></div><div><strong>{candidate.transitHours}<small>h</small></strong><span>estimated transit</span></div></div><p>{reason}</p>{(revised||(!confirmed&&donor==='chc-d'))&&<div className={styles.plan}>Proposed transfer <b>{s.replan.transferUnits} units → Bhatpar PHC</b></div>}<a href="#evidence">Check the field evidence <ArrowDown size={17}/></a></div></div>
    </section>
    <section id="evidence" data-scene className={`${styles.scene} ${styles.evidence}`}>
      <div className={styles.sectionHead}><p className={styles.eyebrow}>05 / REALITY LENS</p><h2>A plan is only as good<br/>as its <em>ground truth.</em></h2><p>The digital record says {s.realityLens.digitalRecord}. The field register says {s.realityLens.fieldEvidence}. Review the evidence before changing the plan.</p></div>
      <div className={styles.evidenceGrid}><div className={styles.register}><div><ScanLine size={26}/><span>WARD STOCK REGISTER<small>CHC D · Kuchinda / sample transcription</small></span></div><table><thead><tr><th>Date</th><th>Issued</th><th>Balance</th></tr></thead><tbody>{s.realityLens.registerRows.map(r=><tr key={r.date}><td>{r.date}</td><td>{r.issued??'—'}</td><td>{r.balance}</td></tr>)}</tbody></table><p>Amoxicillin · oral suspension</p><span className={styles.paperStamp}>FIELD EVIDENCE</span></div><div className={styles.confirmPanel}><p className={styles.eyebrow}>HUMAN REVIEW REQUIRED</p><div className={styles.countChange}><span>{s.realityLens.digitalRecord}<small>digital record</small></span><ArrowRight/><span>{s.realityLens.fieldEvidence}<small>observed count</small></span></div><p>{Math.round(s.realityLens.confidence*100)}% extraction confidence. This correction removes CHC D as a viable donor and brings CHC B into the plan.</p><button className={styles.primary} disabled={confirmed} onClick={()=>{setConfirmed(true);setDonor('chc-b');setStep(1);}}>{confirmed?'Correction confirmed':'Confirm the observed count'}{confirmed?<Check size={20}/>:<ArrowRight size={20}/>}</button><p className={styles.confirmStatus} role="status">{confirmed?'Plan updated: CHC B · Hemgir → Bhatpar, 80 units.':'The original plan remains unchanged until you confirm.'}</p>{confirmed&&<a href="#closing">Follow the revised shipment <ArrowDown size={17}/></a>}</div></div>
    </section>
    <section id="closing" data-scene ref={closingRef} className={`${styles.scene} ${styles.recovery}`}>
      <div className={styles.sectionHead}><p className={styles.eyebrow}>06 / CLOSE THE LOOP</p><h2>{complete?'Care protected.':'Delivery is a step.'}<br/><em>{complete?'Evidence connected.':'Recovery is the outcome.'}</em></h2><p>Follow the illustrative shipment from corrected inventory to a matched batch and care covered.</p></div>
      <div className={styles.recoveryGrid}><div className={styles.receipt}><span className={styles.eyebrow}>TRANSFER RECORD / AMX-2403-B</span><h3>CHC B · Hemgir <ArrowDown/> Bhatpar PHC</h3><div className={styles.metrics}><div><strong>{s.replan.transferUnits}</strong><span>units to transfer</span></div><div><strong>{complete?s.totalCareEventsExposed:'—'}</strong><span>care events protected</span></div></div><div className={styles.progress}><i style={{width:`${shownStep/s.verification.length*100}%`}}/></div><p role="status">{!confirmed?'Awaiting confirmed field evidence':complete?'Illustrative resilience loop closed':s.verification[Math.max(0,shownStep-1)].detail}</p>{!confirmed?<a className={styles.primary} href="#evidence">Review evidence first <ArrowRight size={18}/></a>:<button className={styles.primary} disabled={complete} onClick={()=>setStep(n=>Math.min(Math.max(n,shownStep)+1,s.verification.length))}>{complete?'Recovery verified':`Advance demo: ${s.verification[shownStep].label}`}<Check size={18}/></button>}<button className={styles.reset} onClick={()=>{setConfirmed(false);setStep(0);setDonor('chc-d');}}><RotateCcw size={14}/> Reset demonstration</button></div><ol className={`${styles.timeline} timelineStrong`}>{s.verification.map((v,i)=><li key={v.key} data-done={i<shownStep}><span>{i<shownStep?<Check size={16}/>:String(i+1).padStart(2,'0')}</span><div><b>{v.label}</b><p>{v.detail}</p></div></li>)}</ol></div>
      <div className={styles.finalCta}><h3>Keep shortages from<br/>becoming missed care.</h3><Link className={styles.primary} to={routes.demo}>Explore Demo District <ArrowRight size={20}/></Link></div>
    </section>
    <nav className={styles.chapterNav} aria-label="Story chapters">{chapters.map(([id,label],i)=><a key={id} href={`#${id}`} aria-current={active===id?'location':undefined}><span>0{i+1}</span><b>{label}</b></a>)}</nav>
  </main><Footer/></>;
}
