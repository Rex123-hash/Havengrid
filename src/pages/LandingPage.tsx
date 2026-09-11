import { ArrowDown, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { routes } from '../brand/brand.config';
import { useCallback, useEffect, useRef, useState } from 'react';
import { landingScenario } from '../data/landingScenario';
import { deriveStoryState } from '../story/deriveStoryState';
import { STAGES, STAGE_ORDER, stageOpacity } from '../story/stages';
import { usePrefersReducedMotion, useStoryProgress, useViewportHeight } from '../hooks/useStoryProgress';
import { Navbar } from '../components/Navbar/Navbar';
import { NetworkStage } from '../components/NetworkStage/NetworkStage';
import { HorizonRail } from '../components/HorizonRail/HorizonRail';
import { SupportingBand } from '../components/SupportingBand/SupportingBand';
import { InteractiveFeatures } from '../components/InteractiveFeatures/InteractiveFeatures';
import { Footer } from '../components/Footer/Footer';
import {
  ArrivalBeat,
  BlastBeat,
  BreachBeat,
  CandidatesBeat,
  ClosingBeat,
  HorizonBeat,
  InterventionBeat,
  RealityLensBeat,
  RecoveryBeat,
} from '../story/beats/Beats';
import styles from './LandingPage.module.css';

export default function LandingPage() {
  const storyRef = useRef<HTMLElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const openingRef = useRef<HTMLElement>(null);
  const [handoff, setHandoff] = useState({ exit: 0, enter: 0 });

  const scrollProgress = useStoryProgress(storyRef);
  const [confirmed, setConfirmed] = useState(false);
  const progress = !confirmed && scrollProgress >= 0.705 ? 0.705 : scrollProgress;
  useEffect(() => { if (scrollProgress < 0.63) setConfirmed(false); }, [scrollProgress]);
  const confirmEvidence = () => {
    setConfirmed(true);
    const el = storyRef.current;
    if (el) window.scrollTo({top: el.offsetTop + (el.offsetHeight - window.innerHeight) * 0.743, behavior:'instant'});
  };
  const reducedMotion = usePrefersReducedMotion();
  useViewportHeight(stageRef);

  // Independent of story progress: animate only the approach to the district.
  // Native scroll remains in control and reversing direction reverses the reveal.
  useEffect(() => {
    let frame = 0;
    const measure = () => {
      frame = 0;
      const opening = openingRef.current;
      const story = storyRef.current;
      if (!opening || !story) return;
      const height = window.innerHeight;
      const clamp = (v: number) => Math.min(1, Math.max(0, v));
      const exit = clamp(-opening.getBoundingClientRect().top / (opening.offsetHeight * 0.85));
      const t = clamp((height - story.getBoundingClientRect().top) / (height * 0.8));
      const enter = t * t * (3 - 2 * t);
      setHandoff(previous => Math.abs(previous.exit - exit) + Math.abs(previous.enter - enter) < 0.002 ? previous : {exit, enter});
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(measure); };
    measure();
    window.addEventListener('scroll', schedule, {passive: true});
    window.addEventListener('resize', schedule);
    return () => {cancelAnimationFrame(frame);window.removeEventListener('scroll', schedule);window.removeEventListener('resize', schedule);};
  }, []);

  /* The visitor may take the horizon off the story and sweep it themselves.
     Scrolling hands control back, so the two modes never fight. */
  const [userHorizon, setUserHorizon] = useState<number | null>(null);

  useEffect(() => {
    if (userHorizon === null) return;
    const release = () => setUserHorizon(null);
    window.addEventListener('wheel', release, { passive: true });
    window.addEventListener('touchmove', release, { passive: true });
    window.addEventListener('keydown', onPageKey);
    function onPageKey(e: KeyboardEvent) {
      if (e.key === 'PageDown' || e.key === 'PageUp' || e.key === ' ') release();
    }
    return () => {
      window.removeEventListener('wheel', release);
      window.removeEventListener('touchmove', release);
      window.removeEventListener('keydown', onPageKey);
    };
  }, [userHorizon]);

  const onScrub = useCallback((day: number | null) => setUserHorizon(day), []);

  // One value in, the entire story out. Every visual below is a pure read of
  // this object, which is what makes the whole page reversible.
  const state = deriveStoryState(progress, landingScenario, userHorizon);

  // The rail appears once the horizon becomes relevant and rides out the story.
  const railVisible = 1;

  return (
    <>
      <Navbar />

      <div className={styles.aurora} aria-hidden="true">
        <i />
        <i />
        <i />
      </div>

      <main id="main-content">
        <section ref={openingRef} className={styles.opening} aria-labelledby="opening-title">
          <div className={styles.openingContent} style={reducedMotion ? undefined : {transform: `translateY(${handoff.exit * 36}px)`}}>
            <span className={styles.openingEyebrow}><i /> CARE-AWARE SUPPLY RESILIENCE</span>
            <h1 id="opening-title">Tomorrow’s care.<br /><em>Protected today.</em></h1>
            <p>See the shortage before the shelf is empty.<br />Protect the care that comes next.</p>
            <div className={styles.openingActions}><a href="#story">See the system in action <ArrowDown size={18} /></a><Link to={routes.demo}>Explore Demo District <ArrowRight size={17} /></Link></div>
            <div className={styles.openingLoop} aria-label="The resilience loop"><span><b>01</b> Anticipate demand</span><ArrowRight size={16} aria-hidden="true"/><span><b>02</b> Protect care</span><ArrowRight size={16} aria-hidden="true"/><span><b>03</b> Verify recovery</span></div>
          </div>
          <div className={styles.openingBottom}><span>Built around care continuity.</span><a href="#story">SCROLL TO ENTER THE DISTRICT <ArrowDown size={16}/></a><span>Predict · Prevent · Verify</span></div>
        </section>
        <section id="story" ref={storyRef} className={styles.story} aria-label="How the system works">
          <div className={styles.chapterSeam} aria-hidden="true"><span /><b>01 / ENTER THE DISTRICT</b><span /></div>
          <span id="closing" style={{position:"absolute",top:"82%"}} aria-hidden="true" />
          <div ref={stageRef} className={styles.stage}>


            <div className={styles.split} style={reducedMotion ? undefined : {transform: `translateY(${(1 - handoff.enter) * 70}px)`}}>
              <div className={styles.copyCol}>
                <div className={styles.copyWrap}>
                  <ArrivalBeat opacity={stageOpacity(progress, 'arrival', 0, 0.3)} scenario={landingScenario} />
                  <HorizonBeat opacity={stageOpacity(progress, 'horizon')} />
                  <BreachBeat opacity={stageOpacity(progress, 'breach')} scenario={landingScenario} />
                  <BlastBeat opacity={stageOpacity(progress, 'blast')} scenario={landingScenario} />
                  <CandidatesBeat
                    opacity={stageOpacity(progress, 'candidates')}
                    scenario={landingScenario}
                    revealed={state.candidatesRevealed}
                  />
                  <InterventionBeat
                    opacity={stageOpacity(progress, 'intervention')}
                    state={state}
                    scenario={landingScenario}
                  />
                  <RealityLensBeat
                    onConfirm={confirmEvidence}
                    opacity={stageOpacity(progress, 'realityLens')}
                    scenario={landingScenario}
                    state={state}
                  />
                  <RecoveryBeat opacity={stageOpacity(progress, 'recovery')} scenario={landingScenario} state={state} />
                  <ClosingBeat opacity={stageOpacity(progress, 'closing', 0.18, 0)} scenario={landingScenario} />
                </div>
              </div>

              <div className={styles.netCol}>
                <p className={styles.sceneLabel}>Sundargarh, Odisha <span>Illustrative district</span></p>
                <NetworkStage scenario={landingScenario} state={state} reducedMotion={reducedMotion} />
                <Legend />
            <HorizonRail
              stops={landingScenario.horizonStops}
              day={state.horizonDay}
              exposed={state.careEventsExposed}
              visible={railVisible}
              onScrub={onScrub}
              scrubbing={userHorizon !== null}
            />
              </div>
            </div>

            <nav className={styles.chapters} aria-label="Story chapters">
              {STAGE_ORDER.map((key,i)=><button key={key} aria-label={`Chapter ${i+1}: ${key.replace(/([A-Z])/g,' $1')}`} aria-current={progress >= STAGES[key][0] && progress < STAGES[key][1] ? 'step' : undefined} onClick={()=>{
                setUserHorizon(null);
                const el=storyRef.current;
                if(el) window.scrollTo({top:el.offsetTop+(el.offsetHeight-window.innerHeight)*(STAGES[key][0]+(key==='arrival'?0:.025)),behavior:reducedMotion?'instant':'smooth'});
              }}>{String(i+1).padStart(2,'0')}</button>)}
            </nav>
            <p className={styles.hint} style={{ opacity: Math.max(0, 1 - progress / 0.03) }} aria-hidden="true">
              <span>Scroll to follow one intervention</span>
              <b />
            </p>
          </div>
        </section>

        <InteractiveFeatures />
        <SupportingBand />
      </main>

      <Footer />
    </>
  );
}

/** Legend for the facility-state encoding. `no forecast` is the important one. */
function Legend() {
  return (
    <ul className={styles.legend} aria-hidden="true">
      <li>
        <i data-state="stable" /> on track
      </li>
      <li>
        <i data-state="watch" /> tight
      </li>
      <li>
        <i data-state="breach" /> breach
      </li>
      <li>
        <i data-state="unknown" /> no forecast
      </li>
    </ul>
  );
}
