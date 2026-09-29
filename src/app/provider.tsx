import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ApiDataProvider, ApiError } from "./apiProvider";
import { mockProvider } from "./mock";
import { stateStep, type DistrictStockSignal, type Evidence, type Fact, type Mode, type Role, type Scenario, type WorkspaceData, type WorkspaceProvider as DataProvider } from "./contracts";
import { EvidenceDecisionController } from "./workspaceActions";
import { resolveWorkspaceSource } from "./workspaceSource";

export const workspaceSource = resolveWorkspaceSource(import.meta.env.VITE_WORKSPACE_SOURCE,
  import.meta.env.VITE_APP_ENV, import.meta.env.VITE_HAVENGRID_MODE);
export const dataProvider: DataProvider = workspaceSource === "mock" ? mockProvider : new ApiDataProvider();
const decisions = new EvidenceDecisionController(dataProvider);
const initialUi = () => {
  try {
    const saved = JSON.parse(sessionStorage.getItem("haven-ui-workspace") || "null") as { district?: string; role?: Role; notifications?: boolean } | null;
    return { district: saved?.district && dataProvider.districts.includes(saved.district) ? saved.district : "Sundargarh",
      role: saved?.role && ["VIEWER", "FIELD REVIEWER", "COORDINATOR"].includes(saved.role) ? saved.role : "COORDINATOR" as Role,
      notifications: saved?.notifications !== false };
  } catch { return { district: "Sundargarh", role: "COORDINATOR" as Role, notifications: true }; }
};
interface Context {
  district: string; role: Role; mode: Mode; step: number; evidence: Evidence[];
  notifications: boolean; scenario: Scenario; toast: string; source: "api" | "mock";
  caseState: WorkspaceData["caseState"]; domainLegalActions: string[]; authorizationStatus: "not_evaluated";
  completedActions: string[]; limitations: string[]; previousPlanInvalidated: boolean;
  coverageStatus: string; careProtected: boolean; careImpactExposed: Fact; districtStockSignals: DistrictStockSignal[];
  refreshing: boolean; pendingEvidenceId: string | null;
  setDistrict: (v: string) => void; setRole: (v: Role) => void;
  setNotifications: (v: boolean) => void; review: (id: string, status: Evidence["status"]) => Promise<void>;
  refresh: () => Promise<void>;
}
const WorkspaceContext = createContext<Context | null>(null);
export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [ui, setUi] = useState(initialUi);
  const [data, setData] = useState<WorkspaceData | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "refreshing" | "error">("loading");
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [pendingEvidenceId, setPendingEvidenceId] = useState<string | null>(null);
  const generation = useRef(0);
  const persistUi = (patch: Partial<typeof ui>) => setUi(prev => {
    const next = { ...prev, ...patch };
    sessionStorage.setItem("haven-ui-workspace", JSON.stringify(next));
    return next;
  });
  const refresh = useCallback(async () => {
    const request = ++generation.current;
    setStatus(prev => prev === "ready" ? "refreshing" : "loading");
    try {
      const next = await dataProvider.load(ui.district.toLowerCase());
      if (request !== generation.current) return;
      setData(next); setError(""); setStatus("ready");
    } catch (cause) {
      if (request !== generation.current) return;
      if (import.meta.env.DEV) console.error("HAVEN workspace load failed", cause);
      setError(cause instanceof Error ? cause.message : "Operational data is temporarily unavailable.");
      setStatus("error");
    }
  }, [ui.district]);
  useEffect(() => { void refresh(); return () => { generation.current++; }; }, [refresh]);
  const notify = (value: string) => { if (ui.notifications) setToast(value); };
  const review = async (id: string, decision: Evidence["status"]) => {
    if (decisions.pending || !data || (decision !== "Confirmed" && decision !== "Rejected")) return;
    const item = data.scenario.evidence.find(e => e.id === id);
    if (!item || item.status !== "Awaiting review" || ui.role === "VIEWER") return;
    setPendingEvidenceId(id);
    try {
      const next = await decisions.decide(ui.district.toLowerCase(), data.scenario.id, id, decision);
      if (next) { setData(next); setStatus("ready"); }
      notify(decision === "Confirmed" ? "Evidence confirmed. Canonical workspace refreshed." : "Evidence rejected. Canonical workspace refreshed.");
    } catch (cause) {
      if (import.meta.env.DEV) console.error("HAVEN evidence decision failed", cause);
      if (cause instanceof ApiError && cause.kind === "conflict") await refresh();
      notify(cause instanceof Error ? cause.message : "Evidence decision failed. Canonical state is unchanged.");
    } finally { setPendingEvidenceId(null); }
  };
  const context: Context | null = data ? {
    district: ui.district, role: ui.role, mode: data.mode, notifications: ui.notifications,
    scenario: data.scenario, evidence: data.scenario.evidence, step: stateStep[data.caseState],
    toast, source: data.source, caseState: data.caseState,
    domainLegalActions: data.domainLegalActions, authorizationStatus: data.authorizationStatus,
    completedActions: data.completedActions, limitations: data.limitations,
    previousPlanInvalidated: data.previousPlanInvalidated, refreshing: status === "refreshing", pendingEvidenceId,
    coverageStatus: data.coverageStatus, careProtected: data.careProtected,
    careImpactExposed: data.careImpactExposed, districtStockSignals: data.districtStockSignals,
    setDistrict: district => { setData(null); setStatus("loading"); persistUi({ district }); },
    setRole: role => persistUi({ role }),
    setNotifications: notifications => { persistUi({ notifications }); if (!notifications) setToast(""); },
    review, refresh,
  } : null;
  if (!context || status === "error") return (
    <div className="hv-app">
      <aside className="hv-rail">
        <Link className="hv-lockup" to="/">HAVEN GRID</Link>
        <div className="hv-rail-dash" />
        <nav><Link to="/">Haven home</Link><Link to="/login">Workspace entry</Link></nav>
      </aside>
      <div className="hv-workspace">
      <div className="hv-content" style={{ paddingTop: "18vh", maxWidth: 720, margin: "0 auto" }}>
        <span className="hv-micro">HAVEN GRID · {ui.district}</span>
        <h1>{status === "loading" ? "Opening the Situation Room" : "Operational data unavailable"}</h1>
        <p>{status === "loading" ? "Loading the canonical district workspace…" :
          error.includes("No rehearsal values") ? error : `${error} No rehearsal values were substituted.`}</p>
        {status === "error" && <button className="hv-button" onClick={() => void refresh()}>Retry connection</button>}
      </div></div></div>
  );
  return <WorkspaceContext.Provider value={context}>{children}</WorkspaceContext.Provider>;
}
export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("Workspace provider required");
  return value;
}
