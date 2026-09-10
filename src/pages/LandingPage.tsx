import { useCallback, useEffect, useRef, useState } from 'react';
import { landingScenario } from '../data/landingScenario';
import { deriveStoryState } from '../story/deriveStoryState';
import { STAGES, STAGE_ORDER, stageOpacity } from '../story/stages';
import { usePrefersReducedMotion, useStoryProgress, useViewportHeight } from '../hooks/useStoryProgress';
import { Navbar } from '../components/Navbar/Navbar';
import { NetworkStage } from '../components/NetworkStage/NetworkStage';
import { HorizonRail } from '../components/HorizonRail/HorizonRail';
import { SupportingBand } from '../components/SupportingBand/SupportingBand';
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

  const progress = useStoryProgress(storyRef);
  const reducedMotion = usePrefersReducedMotion();
  useViewportHeight(stageRef);

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
        <section id="story" ref={storyRef} className={styles.story} aria-label="How the system works">
          <div ref={stageRef} className={styles.stage}>
            <HorizonRail
              stops={landingScenario.horizonStops}
              day={state.horizonDay}
              exposed={state.careEventsExposed}
              visible={railVisible}
              onScrub={onScrub}
              scrubbing={userHorizon !== null}
            />

            <div className={styles.split}>
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
                    opacity={stageOpacity(progress, 'realityLens')}
                    scenario={landingScenario}
                    state={state}
                  />
                  <RecoveryBeat opacity={stageOpacity(progress, 'recovery')} scenario={landingScenario} state={state} />
                  <ClosingBeat opacity={stageOpacity(progress, 'closing', 0.18, 0)} scenario={landingScenario} />
                </div>
              </div>

              <div className={styles.netCol}>
                <p className={styles.sceneLabel}>Sundargarh, Odisha · illustrative district</p><Legend />
                <NetworkStage scenario={landingScenario} state={state} reducedMotion={reducedMotion} />
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
