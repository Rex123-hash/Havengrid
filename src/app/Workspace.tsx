import { useEffect, useRef, useState } from "react";
import {
  Link,
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import {
  ArrowRight,
  BarChart3,
  Building2,
  ChevronDown,
  Command,
  FileText,
  Folder,
  MapPin,
  Network,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import { BrandGlyph } from "../brand/BrandMark";
import { brand } from "../brand/brand.config";
import { WorkspaceProvider, useWorkspace } from "./provider";
import { pageInfo } from "./mock";
import { dataProvider, workspaceSource } from "./provider";
import { ProvenanceBadge, StateBadge, UnknownState } from "./components";
import {
  CaseWorkspace,
  Cases,
  EvidenceDetail,
  EvidenceInbox,
  Facilities,
  FacilityWorkspace,
  Intelligence,
  NetworkPage,
  OtherDistrict,
  Recovery,
  Settings,
  Situation,
} from "./pages";
import "./workspace.css";

const nav = [
  { path: "", label: "Situation", Icon: Target },
  { path: "network", label: "Network", Icon: Network },
  { path: "facilities", label: "Facilities", Icon: Building2 },
  { path: "cases", label: "Cases", Icon: Folder },
  { path: "evidence", label: "Evidence", Icon: FileText },
  { path: "recovery", label: "Recovery", Icon: ShieldCheck },
  { path: "intelligence", label: "Intelligence", Icon: BarChart3 },
];
function Lockup() {
  return (
    <span className="hv-lockup">
      <BrandGlyph size={36} />
      <span>
        <b>{brand.name.toUpperCase()}</b>
        <small>{brand.tagline.toUpperCase()}</small>
      </span>
    </span>
  );
}
export function HavenRail() {
  const { district } = useWorkspace();
  return (
    <aside className="hv-rail">
      <Link to="/" aria-label="Haven Grid home">
        <Lockup />
      </Link>
      <div className="hv-rail-dash" />
      <nav aria-label="Workspace navigation">
        {nav.map(({ path, label, Icon }) => (
          <NavLink
            end={!path}
            to={"/app" + (path ? "/" + path : "")}
            key={label}
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            <Icon size={19} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="hv-rail-bottom">
        <NavLink to="/app/settings">
          <Settings2 size={17} />
          <span>Workspace settings</span>
        </NavLink>
        <div className="hv-rail-dash" />
        <p>
          {district}, Odisha
          <br />
          District workspace
        </p>
        <div className="hv-rail-dash" />
        <p className="hv-motto">
          Turning
          <br />
          supply signals into
          <br />
          uninterrupted care.
        </p>
      </div>
    </aside>
  );
}
function ModeBadge() {
  const { mode } = useWorkspace();
  return (
    <label
      className={"hv-mode " + (mode === "OPERATIONAL" ? "operational" : "")}
      title={
        mode === "REHEARSAL"
          ? "Controlled rehearsal · canonical backend snapshot"
          : "Operational mode unavailable in this integration gate"
      }
    >
      <i className="hv-dot" />
      <select
        aria-label="Workspace mode"
        value={mode}
        disabled
      >
        <option>REHEARSAL</option>
        <option>OPERATIONAL</option>
      </select>
      <ChevronDown size={13} />
    </label>
  );
}
function DistrictSwitcher() {
  const { district, setDistrict } = useWorkspace();
  const navigate = useNavigate();
  return (
    <label className="hv-district">
      <MapPin size={15} />
      <select
        aria-label="District workspace"
        value={district}
        onChange={(e) => {
          setDistrict(e.target.value);
          navigate("/app");
        }}
      >
        {dataProvider.districts.map((d) => (
          <option key={d}>{d}</option>
        ))}
      </select>
      <ChevronDown size={13} />
    </label>
  );
}
function WorkspaceHeader({ ask }: { ask: () => void }) {
  const location = useLocation();
  const key = location.pathname.split("/")[2] || "situation";
  const info = pageInfo[key] || pageInfo.situation;
  const detail = location.pathname.split("/").filter(Boolean).length > 2;
  const { role, refreshing, scenario } = useWorkspace();
  return (
    <header className="hv-header">
      <div className="hv-header-title">
        {detail ? (
          <Link className="hv-micro" to={"/app/" + key}>
            {info[0]} / Workspace
          </Link>
        ) : (
          <>
            <span className="hv-micro">Operational intelligence</span>
            <h1>{info[0]}</h1>
            <p>{info[1]}</p>
          </>
        )}
      </div>
      <div className="hv-header-controls">
        <ModeBadge />
        <DistrictSwitcher />
        <span
          className="hv-sync"
          title="Canonical backend workspace snapshot"
        >
          <RefreshCw size={13} />
          <span>
            {refreshing ? "Refreshing…" : `Snapshot · ${scenario.snapshot}`}
          </span>
        </span>
        <button className="hv-ask-trigger" onClick={ask} disabled={workspaceSource === "api"} title={workspaceSource === "api" ? "Ask Haven is not connected to canonical API data" : undefined}>
          <Sparkles size={16} />
          Ask Haven
        </button>
        <Link className="hv-user" to="/app/settings">
          <span className="hv-avatar">AS</span>
          <span>
            <b>Ananya S.</b>
            <small>
              {role === "COORDINATOR"
                ? "District Team"
                : role === "VIEWER"
                  ? "Viewer"
                  : "Field Reviewer"}
            </small>
          </span>
          <ArrowRight size={15} />
        </Link>
      </div>
    </header>
  );
}
const questions = [
  "Why was Bonai rejected?",
  "Where did the 30-tablet value come from?",
  "Why is care exposure an estimate?",
  "Which data is missing for Lahunipada?",
  "What changed after the field observation?",
  "Why was Panposh selected?",
];
function AskHavenPanel({ close }: { close: () => void }) {
  const { scenario, district } = useWorkspace();
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState<number | null>(null);
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const before = document.activeElement as HTMLElement | null;
    dialog.current?.querySelector("input")?.focus();
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      if (e.key === "Tab") {
        const nodes = Array.from(
          dialog.current?.querySelectorAll<HTMLElement>(
            'button,a,input,[tabindex="0"]',
          ) || [],
        );
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", handler);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = overflow;
      before?.focus();
    };
  }, [close]);
  const responses = [
    {
      text: "Bonai’s confirmed rehearsal count changed from 120 to 20 tablets. The corrected inventory violates its own continuity threshold, so the donor plan was invalidated.",
      reason: "DONOR_ALREADY_AT_RISK",
      fact: scenario.facilities.find((f) => f.id === scenario.invalidatedId)!
        .stock,
      link: "/app/evidence/bonai-count",
      label: "Inspect confirmed observation",
    },
    {
      text: "The 30-tablet starting quantity is a controlled Lahunipada shelf observation, confirmed in the rehearsal. It is not an official facility inventory export.",
      reason: "CONFIRMED_REHEARSAL_OBSERVATION",
      fact: scenario.facilities.find((f) => f.id === scenario.recipientId)!
        .stock,
      link: "/app/facilities/" + scenario.recipientId,
      label: "Inspect facility evidence",
    },
    {
      text: "The 11–15 aggregate obligations are a controlled facility-session range. AMB provides public programme context, but its district KPI has no Lahunipada denominator.",
      reason: "FACILITY_DENOMINATOR_UNKNOWN",
      fact: scenario.exposure,
      link: "/app/facilities/" + scenario.recipientId,
      label: "Inspect care basis",
    },
    {
      text: "Official facility inventory, the beneficiary denominator, authoritative coordinates, operational batch details and physical issue packaging remain unavailable.",
      reason: "DATA_REQUIRED",
      fact: scenario.dispatchUnit,
      link: "/app/intelligence",
      label: "Inspect data gaps",
    },
    {
      text: "The Bonai donor plan was invalidated after its canonical count changed from 120 to 20. The rehearsal evaluator selected Panposh as the replacement.",
      reason: "PLAN_RECALCULATED",
      fact: scenario.transfer,
      link: "/app/cases/" + scenario.id,
      label: "Open intervention",
    },
    {
      text: "The approved rehearsal selected Panposh using the captured route and donor continuity evaluation. The transfer calculation is 47 tablets, with a post-transfer margin of 103. Physical packaging remains unknown.",
      reason: "DONOR_CONTINUITY_PRESERVED",
      fact: scenario.donors[0].distance,
      link: "/app/cases/" + scenario.id,
      label: "Compare donor candidates",
    },
  ];
  const submit = () => {
    const match = questions.findIndex(
      (q) => q.toLowerCase().includes(query.toLowerCase()) && query.length > 3,
    );
    setAnswer(match >= 0 ? match : -1);
  };
  return (
    <div
      className="hv-overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div
        ref={dialog}
        className="hv-ask-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="hv-ask-title"
      >
        <div className="hv-row">
          <span className="hv-ask-emblem">
            <Sparkles size={24} />
          </span>
          <button aria-label="Close Ask Haven" onClick={close}>
            <X size={21} />
          </button>
        </div>
        <span className="hv-micro">Your evidence, in context</span>
        <h2 id="hv-ask-title">Ask Haven</h2>
        <p>Clear answers. Traceable reasons.</p>
        <StateBadge>UI preview · scripted explanations</StateBadge>
        <form
          className="hv-ask-input"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <input
            aria-label="Ask a question"
            placeholder="What would you like to understand?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button aria-label="Submit question">
            <ArrowRight size={19} />
          </button>
        </form>
        {district !== "Sundargarh" ? (
          <UnknownState
            title="District evidence unavailable"
            text="No scenario answers are loaded for this district."
          />
        ) : (
          <>
            {answer === null ? (
              <div className="hv-question-list">
                {questions.map((q, i) => (
                  <button
                    key={q}
                    onClick={() => {
                      setQuery(q);
                      setAnswer(i);
                    }}
                  >
                    {q}
                    <ArrowUpIcon />
                  </button>
                ))}
              </div>
            ) : answer === -1 ? (
              <UnknownState
                title="This question has no scripted answer"
                text="The preview does not run an LLM. Choose a suggested question to inspect the evidence."
                action={
                  <button className="hv-button" onClick={() => setAnswer(null)}>
                    Suggested questions
                  </button>
                }
              />
            ) : (
              <div className="hv-answer" aria-live="polite">
                <span className="hv-micro">From the rehearsal evidence</span>
                <h3>{questions[answer]}</h3>
                <p>{responses[answer].text}</p>
                <code>{responses[answer].reason}</code>
                <ProvenanceBadge fact={responses[answer].fact} />
                <Link
                  className="hv-button primary"
                  to={responses[answer].link}
                  onClick={close}
                >
                  {responses[answer].label}
                  <ArrowRight size={15} />
                </Link>
                <button
                  className="hv-text-link"
                  onClick={() => setAnswer(null)}
                >
                  Explore another question
                </button>
              </div>
            )}
          </>
        )}
        <div className="hv-ask-footer">
          <ShieldCheck size={15} />
          No generated claims. No connected AI.<span>Esc to close</span>
        </div>
      </div>
    </div>
  );
}
function ArrowUpIcon() {
  return <ArrowRight size={14} />;
}
function Shell() {
  const [ask, setAsk] = useState(false);
  const { district, toast, mode } = useWorkspace();
  const location = useLocation();
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (workspaceSource === "mock" && (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setAsk((v) => !v);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
  useEffect(() => {
    const title =
      pageInfo[location.pathname.split("/")[2] || "situation"]?.[0] ||
      "Workspace";
    document.title = title + " · HAVEN GRID";
  }, [location.pathname]);
  return (
    <div className="hv-app">
      <HavenRail />
      <div className="hv-workspace">
        <WorkspaceHeader ask={() => setAsk(true)} />
        <main id="main-content" className="hv-content">
          {mode === "OPERATIONAL" && (
            <div className="hv-mode-notice">
              <ShieldCheck size={16} />
              Operational shell preview · controlled mock data · explicit local
              actions only
            </div>
          )}
          {district !== "Sundargarh" &&
          location.pathname !== "/app/settings" ? (
            <OtherDistrict />
          ) : (
            <Routes>
              <Route index element={<Situation />} />
              <Route path="network" element={<NetworkPage />} />
              <Route path="facilities" element={<Facilities />} />
              <Route
                path="facilities/:facilityId"
                element={<FacilityWorkspace />}
              />
              <Route path="cases" element={<Cases />} />
              <Route path="cases/:caseId" element={<CaseWorkspace />} />
              <Route path="evidence" element={<EvidenceInbox />} />
              <Route path="evidence/:evidenceId" element={<EvidenceDetail />} />
              <Route path="recovery" element={<Recovery />} />
              <Route path="intelligence" element={<Intelligence />} />
              <Route path="settings" element={<Settings />} />
              <Route
                path="*"
                element={
                  <UnknownState
                    title="Workspace page not found"
                    text="Use the Haven Rail to return to an available workspace."
                  />
                }
              />
            </Routes>
          )}
        </main>
        <footer className="hv-workspace-footer">
          <span>
            <i className="hv-dot" />
            {workspaceSource === "api" ? "Canonical backend rehearsal" : "Explicit mock rehearsal"}
          </span>
          <button onClick={() => setAsk(true)} disabled={workspaceSource === "api"}>
            <Command size={12} />K · Ask Haven
          </button>
        </footer>
        <div className="hv-toast" role="status" key={toast}>
          {toast}
        </div>
      </div>
      {ask && workspaceSource === "mock" && <AskHavenPanel close={() => setAsk(false)} />}
    </div>
  );
}
export default function Workspace() {
  return (
    <WorkspaceProvider>
      <Shell />
    </WorkspaceProvider>
  );
}
export function Login() {
  const [profile, setProfile] = useState("single");
  const [stage, setStage] = useState("login");
  const [org, setOrg] = useState("");
  const navigate = useNavigate();
  const enter = (district = "Sundargarh") => {
    sessionStorage.setItem("haven-ui-session", "preview");
    const previous = JSON.parse(
      sessionStorage.getItem("haven-ui-workspace") || "null",
    );
    if (previous)
      sessionStorage.setItem(
        "haven-ui-workspace",
        JSON.stringify({ ...previous, district }),
      );
    navigate("/app");
  };
  return (
    <div className="hv-app hv-login">
      <section className="hv-login-art">
        <Link to="/">
          <Lockup />
        </Link>
        <div className="hv-login-copy">
          <span className="hv-micro">Care-aware supply resilience</span>
          <h1>
            Keep care
            <br />
            in motion.
          </h1>
          <p>
            A clearer picture of your district.
            <br />A safer path from signal to response.
          </p>
          <div className="hv-login-network">
            <svg viewBox="0 0 540 220" aria-hidden="true">
              <g fill="none" stroke="#8bb69b">
                <path d="M50 150 Q140 60 230 130 T460 85 M230 130 Q290 0 400 40 M230 130 Q330 230 460 185" />
                <circle cx="50" cy="150" r="8" />
                <circle cx="400" cy="40" r="10" />
                <circle cx="460" cy="85" r="8" />
                <circle cx="460" cy="185" r="9" />
              </g>
              <circle cx="230" cy="130" r="30" fill="#8bb69b" opacity=".15" />
              <circle cx="230" cy="130" r="15" fill="#c6dcaa" />
            </svg>
            <span>One connected response.</span>
          </div>
        </div>
        <span className="hv-micro">HAVEN GRID · District intelligence</span>
      </section>
      <main id="main-content" className="hv-login-form">
        <Link to="/" className="hv-back">
          ← Back to Haven
        </Link>
        {stage === "login" ? (
          <>
            <span className="hv-micro">Your district awaits</span>
            <h2>Welcome to Haven.</h2>
            <p>A calm place to coordinate the work that keeps care moving.</p>
            <button
              className="hv-google-button"
              onClick={() =>
                profile === "single"
                  ? enter()
                  : setStage(profile === "multi" ? "chooser" : "onboard")
              }
            >
              <span className="hv-google-g">G</span>Continue with Google{" "}
              <ArrowRight size={17} />
            </button>
            <div className="hv-login-disclosure">
              <ShieldCheck size={17} />
              <span>
                Mock sign-in · no Google account connection.
                <br />
                No password or personal data required.
              </span>
            </div>
            <label className="hv-form-label">
              Preview experience
              <select
                value={profile}
                onChange={(e) => setProfile(e.target.value)}
              >
                <option value="single">Existing district team</option>
                <option value="multi">Multi-district coordinator</option>
                <option value="new">New district / organization</option>
              </select>
            </label>
          </>
        ) : stage === "chooser" ? (
          <>
            <span className="hv-micro">Your workspaces</span>
            <h2>Choose your district.</h2>
            <p>Each district keeps its own evidence and readiness.</p>
            {dataProvider.districts.map((d) => (
              <button
                key={d}
                className="hv-workspace-choice"
                onClick={() => {
                  sessionStorage.setItem("haven-ui-workspace", JSON.stringify({ district: d, role: "COORDINATOR", notifications: true }));
                  enter(d);
                }}
              >
                <MapPin size={21} />
                <span>
                  <b>{d}</b>
                  <small>
                    {d === "Sundargarh"
                      ? "Full rehearsal workspace"
                      : "Readiness preview"}
                  </small>
                </span>
                <ArrowRight size={17} />
              </button>
            ))}
          </>
        ) : (
          <>
            <span className="hv-micro">A considered beginning</span>
            <h2>Bring a district into view.</h2>
            <p>
              Start with a public roster, then verify the evidence needed for
              operational readiness.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setStage("requested");
              }}
            >
              <label className="hv-form-label">
                Organization or district
                <input
                  required
                  value={org}
                  onChange={(e) => setOrg(e.target.value)}
                  placeholder="Your district team"
                />
              </label>
              <button className="hv-button primary">
                Create local onboarding draft <ArrowRight size={16} />
              </button>
            </form>
            {stage === "requested" && (
              <div role="status" className="hv-note">
                <b>{org} · draft prepared</b>
                <p>
                  No organization was registered. Begin with the rehearsal
                  workspace to explore the onboarding model.
                </p>
                <button className="hv-button" onClick={() => enter()}>
                  Explore the rehearsal
                </button>
              </div>
            )}
          </>
        )}
        <div className="hv-login-bottom">
          <span>Evidence before action.</span>
          <span>Care before closure.</span>
        </div>
      </main>
    </div>
  );
}
export function DemoEntry() {
  useEffect(() => {
    sessionStorage.setItem("haven-ui-session", "preview");
  }, []);
  return <Navigate to="/app" replace />;
}
