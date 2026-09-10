import { useEffect } from 'react';
import { Route, Routes, useLocation } from 'react-router-dom';
import { MotionConfig } from 'motion/react';
import { routes } from './brand/brand.config';
import LandingPage from './pages/LandingPage';
import Placeholder from './pages/Placeholder';

/** Routed pages should open at the top, not wherever the story was left. */
function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

export default function App() {
  return (
    <MotionConfig reducedMotion="user">
      <ScrollToTop />
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <Routes>
        <Route path={routes.home} element={<LandingPage />} />
        <Route
          path={routes.demo}
          element={
            <Placeholder
              eyebrow="Next phase"
              title="Demo District — coming next"
              body="The seeded Sundargarh district and its operational surface are the next phase of work. This phase covers the welcome experience only, so there is deliberately nothing behind this button yet."
            />
          }
        />
        <Route
          path={routes.signIn}
          element={
            <Placeholder
              eyebrow="Not yet connected"
              title="Sign in — coming next"
              body="Accounts and roles arrive with the operational surface. Exploring the demo district will not require an account."
            />
          }
        />
        <Route
          path="*"
          element={
            <Placeholder
              eyebrow="404"
              title="Page not found"
              body="That page does not exist yet. Only the welcome experience has been built so far."
            />
          }
        />
      </Routes>
    </MotionConfig>
  );
}
