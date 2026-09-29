import { useEffect } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import { MotionConfig } from "motion/react";
import { routes } from "./brand/brand.config";
import LandingPage from "./pages/LandingPage";
import Placeholder from "./pages/Placeholder";
import Workspace, { Login, DemoEntry } from "./app/Workspace";

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
        <Route path="/app/*" element={<Workspace />} />
        <Route path="/login" element={<Login />} />
        <Route path={routes.demo} element={<DemoEntry />} />
        <Route path={routes.signIn} element={<Login />} />
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
