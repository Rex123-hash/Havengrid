import { useState } from 'react';
import { ArrowDown, ArrowRight, Check, Clock3, ShieldCheck, SlidersHorizontal, RotateCcw, ScanLine } from 'lucide-react';
import { landingScenario as scenario } from '../../data/landingScenario';
import { deriveStoryState } from '../../story/deriveStoryState';
import { Link } from 'react-router-dom';
import { routes } from '../../brand/brand.config';
import styles from './InteractiveFeatures.module.css';

export function InteractiveFeatures() {
  const [day, setDay] = useState(7);
  const [facility, setFacility] = useState('bhatpar');
  const [donorId, setDonorId] = useState('cand-chc-d');
  const [corrected, setCorrected] = useState(false);
  const forecast = deriveStoryState(0, scenario, day);
  const selected = forecast.facilities.find(f => f.facility.id === facility)!;
  const breached = forecast.facilities.filter(f => f.risk === 'breach');
  const donor = scenario.candidates.find(c => c.id === donorId)!;
  const invalidated = corrected && donor.facilityId === scenario.realityLens.facilityId;
  const recommendedAfter = corrected && donor.facilityId === scenario.replan.facilityId;
  const verdict = recommendedAfter ? 'Recommended after verification' : invalidated ? 'Unavailable after verification' : donor.verdict === 'chosen' ? 'Recommended before verification' : donor.verdict === 'held' ? 'Viable alternative' : 'Not suitable';
  return <div className={styles.features} id="explore-features">
    <div className={styles.intro}>
      <span className={styles.eyebrow}>GO BEYOND THE STORY</span>
      <h2>Now put the system<br /><em>to the test.</em></h2>
      <p>Move time forward. Inspect a facility. Challenge a recommendation.<br />Explore the decisions behind a more resilient district.</p>
      <a href="#forecast-explorer">Start exploring <ArrowDown size={16} /></a>
    </div>

    <section id="forecast-explorer" className={styles.feature} aria-labelledby="forecast-heading">
      <div className={styles.description}>
        <span className={styles.eyebrow}>01 / LOOK AHEAD</span>
        <h2 id="forecast-heading">A healthy shelf.<br /><em>A different tomorrow.</em></h2>
        <p>See which facilities become vulnerable as scheduled demand reaches their available supply. Change the horizon to reveal what today’s inventory cannot show.</p>
        <ul><li><Clock3 size={18} /> Explore the next 30 days</li><li><ShieldCheck size={18} /> Missing evidence stays visible</li></ul>
        <span className={styles.disclosure}>Illustrative district · fixed demo forecasts</span>
      </div>
      <div className={styles.explorer}>
        <div className={styles.panelHeading}><span><SlidersHorizontal size={17} /> Forecast explorer</span><b>+{day} days</b></div>
        <label className={styles.sliderLabel} htmlFor="feature-horizon">Forecast horizon</label>
        <input id="feature-horizon" type="range" min="0" max="30" value={day} onChange={e => setDay(Number(e.target.value))} aria-valuetext={`${day} days ahead`} />
        <div className={styles.stops}>{[0,3,7,14,30].map(d=><button key={d} aria-pressed={day===d} onClick={()=>setDay(d)}>{d===0?'Today':`${d} days`}</button>)}</div>
        <div className={styles.metrics} aria-live="polite"><div><b>{breached.length}</b><span>facilities past shortage date</span></div><div><b>{forecast.careEventsExposed}</b><span>care events exposed</span></div><div><b>{forecast.facilities.filter(f=>f.risk==='unknown').length}</b><span>forecast unavailable</span></div></div>
        <div className={styles.facilities} aria-label="Choose a facility">{forecast.facilities.map(f=><button key={f.facility.id} data-risk={f.risk} aria-pressed={facility===f.facility.id} onClick={()=>setFacility(f.facility.id)}><i /><span>{f.facility.short}</span><small>{f.risk === 'unknown'?'No forecast':f.risk==='breach'?'Shortage':f.risk==='watch'?'Watch':'On track'}</small></button>)}</div>
        <div className={styles.facilityDetail} aria-live="polite"><div><strong>{selected.facility.name}</strong><p>{selected.risk==='unknown'?'Insufficient evidence to produce a forecast.':selected.effectiveBreachDay===null?'No shortage predicted within this demo’s 30-day window.':`Predicted shortage on day ${selected.effectiveBreachDay}. ${selected.facility.careEventsExposed} care events exposed if the shortage occurs.`}</p></div><span>Inventory verified<br /><b>{selected.facility.daysSinceVerified} days ago</b></span></div>
      </div>
    </section>

    <section id="intervention-explorer" className={`${styles.feature} ${styles.reverse}`} aria-labelledby="intervention-heading">
      <div className={styles.description}>
        <span className={styles.eyebrow}>02 / CHALLENGE THE PLAN</span>
        <h2 id="intervention-heading">The nearest donor<br /><em>isn’t the whole answer.</em></h2>
        <p>Compare the alternatives for Bhatpar’s 44-unit shortage. Each option has a different reserve, travel time, and consequence for neighbouring care.</p>
        <p className={styles.prompt}>Choose a source to inspect why it is accepted or rejected. Then bring in the field evidence.</p>
        <span className={styles.disclosure}>Comparison only · no real transfer is dispatched</span>
      </div>
      <div className={styles.comparison}>
        <div className={styles.panelHeading}><span><ShieldCheck size={18} /> Intervention workbench</span><span>BHATPAR PHC</span></div>
        <div className={styles.donors}>{scenario.candidates.map(c=><button key={c.id} aria-pressed={donorId===c.id} onClick={()=>setDonorId(c.id)}><span>{c.facilityName}</span><small>{c.distanceKm} km <ArrowRight size={13} /></small></button>)}</div>
        <div className={styles.decision} aria-live="polite"><span className={styles.verdict} data-rejected={invalidated||donor.verdict==='rejected'}>{verdict}</span><h3>{donor.facilityName}</h3><div className={styles.donorNumbers}><div><strong>{invalidated?'0':donor.surplus}</strong><span>releasable surplus · units</span></div><div><strong>{donor.transitHours}h</strong><span>dispatch / transit window</span></div></div><p>{invalidated?'The observed stock of 126 is below the 200-unit safety floor. This donor cannot release the proposed 80 units.':recommendedAfter?scenario.replan.reason:donor.reason}</p></div>
        <div className={styles.evidence}><ScanLine size={24} /><div><b>What if the inventory record is wrong?</b><p>CHC D: digital record <strong>286</strong> · observed count <strong>126</strong></p></div></div>
        <button className={styles.action} onClick={()=>{setCorrected(!corrected);setDonorId(corrected?'cand-chc-d':'cand-chc-b');}}>{corrected?<><RotateCcw size={16}/> Reset evidence comparison</>:<>Confirm demo count & compare again <ArrowRight size={16}/></>}</button>
        {corrected&&<p className={styles.confirmed} role="status"><Check size={16}/> Count confirmed. CHC D is ruled out; CHC B becomes the recommended source. Select CHC D to inspect the change.</p>}
      </div>
    </section>

    <section className={styles.finalInvite} aria-label="Explore the district">
      <span className={styles.eyebrow}>FROM INSIGHT TO CONTINUITY</span><h2>Fewer surprises.<br /><em>More care delivered.</em></h2><p>One connected view of demand, supply, and the evidence on the ground.</p><Link className={styles.action} to={routes.demo}>Explore Demo District <ArrowRight size={18}/></Link>
    </section>
  </div>;
}
