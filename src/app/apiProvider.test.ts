import { describe, expect, it, vi } from "vitest";
import before from "./fixtures/workspace-before.json";
import after from "./fixtures/workspace-after.json";
import { ApiDataProvider, ApiError, type WorkspaceSnapshotDto } from "./apiProvider";
import { mapWorkspaceSnapshot } from "./workspaceAdapter";
import { mockProvider } from "./mock";
import { stateStep, type WorkspaceProvider } from "./contracts";
import { EvidenceDecisionController } from "./workspaceActions";
import { resolveWorkspaceSource } from "./workspaceSource";

const initial = before as unknown as WorkspaceSnapshotDto;
const corrected = after as unknown as WorkspaceSnapshotDto;
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value),
  { status, headers: { "Content-Type": "application/json" } });

describe("workspace API seam", () => {
  it("maps the real backend checkpoint, including canonical case and chosen Bonai plan", () => {
    const mapped = mapWorkspaceSnapshot(initial);
    expect(mapped.caseState).toBe("AWAITING_EVIDENCE_CONFIRMATION");
    expect(mapped.scenario.selectedId).toBe("sdh-bonai");
    expect(mapped.scenario.evidence.find(e => e.id === "ev-002")).toMatchObject({
      previous: 120, observed: 20, status: "Awaiting review",
    });
    expect(mapped.scenario.facilities.find(f => f.id === "sdh-bonai")?.stock.value).toBe(120);
    expect(mapped.domainLegalActions).toEqual(initial.recovery.domain_legal_actions);
    expect(mapped.authorizationStatus).toBe("not_evaluated");
    expect(mapped.mode).toBe("REHEARSAL");
    expect(mapped.coverageStatus).toBe(initial.recovery.coverage_status);
    expect(mapped.careProtected).toBe(false);
    expect(mapped.districtStockSignals[mapped.districtStockSignals.length - 1]?.granularity).toBe("district");
    expect(mapped.districtStockSignals[mapped.districtStockSignals.length - 1]?.available.classification).toBe("REAL_PUBLIC");
    expect(mapped.scenario.sources.find(s => s.name === "HMIS standard reports")?.classification).toBe("OFFICIAL_SYSTEM_EXPORT");
  });
  it("preserves unknown inventory and provenance rather than turning it into zero", () => {
    const mapped = mapWorkspaceSnapshot(initial);
    const unknownFacility = mapped.scenario.facilities.find(f => f.stock.value === null);
    expect(unknownFacility?.stock.value).toBeNull();
    expect(unknownFacility?.stock.classification).toBe("UNKNOWN");
    expect(mapped.scenario.dispatchUnit.value).toBe("Unavailable");
    expect(mapped.scenario.baseline.value).toBe("Unavailable");
    const withZero = structuredClone(initial);
    const bonai = withZero.network.facilities.find(f => f.facility.id === "sdh-bonai");
    if (!bonai?.canonical_inventory) throw new Error("Bonai fixture missing canonical stock");
    bonai.canonical_inventory.quantity = 0;
    expect(mapWorkspaceSnapshot(withZero).scenario.facilities.find(f => f.id === "sdh-bonai")?.stock.value).toBe(0);
  });
  it("does not fall back to mock when the API fails", async () => {
    const provider = new ApiDataProvider("", vi.fn(async () => { throw new TypeError("offline"); }) as typeof fetch);
    await expect(provider.load("sundargarh")).rejects.toMatchObject({ kind: "network" });
  });
  it("keeps mock mode explicit", async () => {
    const mock = await mockProvider.load("Sundargarh");
    expect(mock.source).toBe("mock");
    expect(mockProvider.districts).toContain("Sundargarh");
    expect(resolveWorkspaceSource(undefined, "development", "rehearsal")).toBe("api");
    expect(resolveWorkspaceSource("mock", "development", "rehearsal")).toBe("mock");
    expect(() => resolveWorkspaceSource("mock", "production", "rehearsal")).toThrow();
    expect(() => resolveWorkspaceSource("mock", "development", "operational")).toThrow();
  });
  it("sends confirmation, waits for success, then GETs backend correction without computing a donor", async () => {
    const calls: string[] = [];
    const transport = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input); calls.push(`${init?.method ?? "GET"} ${url}`);
      if (init?.method === "POST") return json({ state: "PLAN_RECALCULATED" });
      return json(calls.some(c => c.startsWith("POST")) ? corrected : initial);
    }) as typeof fetch;
    const provider = new ApiDataProvider("", transport);
    const baseline = await provider.load("sundargarh");
    const controller = new EvidenceDecisionController(provider);
    const result = await controller.decide("sundargarh", baseline.scenario.id, "ev-002", "Confirmed");
    expect(calls).toEqual([
      "GET /api/districts/sundargarh/workspace",
      `POST /api/cases/${baseline.scenario.id}/evidence/ev-002/confirm`,
      "GET /api/districts/sundargarh/workspace",
    ]);
    expect(result?.scenario.selectedId).toBe("sdh-panposh");
    expect(result?.scenario.facilities.find(f => f.id === "sdh-bonai")?.stock.value).toBe(20);
    expect(result?.caseState).toBe("PLAN_RECALCULATED");
    expect(result?.previousPlanInvalidated).toBe(true);
    expect(baseline.scenario.selectedId).toBe("sdh-bonai");
    expect(mapWorkspaceSnapshot(initial).scenario.selectedId).toBe("sdh-bonai");
  });
  it("sends rejection and reads the returned canonical workspace", async () => {
    const calls: string[] = [];
    const provider = new ApiDataProvider("", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push(`${init?.method ?? "GET"} ${String(input)}`);
      return init?.method === "POST" ? json({ state: "rejected" }) : json(initial);
    }) as typeof fetch);
    const result = await new EvidenceDecisionController(provider).decide("sundargarh", initial.active_case.id, "ev-002", "Rejected");
    expect(calls).toEqual([
      `POST /api/cases/${initial.active_case.id}/evidence/ev-002/reject`,
      "GET /api/districts/sundargarh/workspace",
    ]);
    expect(result?.scenario.selectedId).toBe("sdh-bonai");
  });
  it("derives display progress only from backend CaseState", () => {
    expect(stateStep[mapWorkspaceSnapshot(initial).caseState]).toBe(0);
    expect(stateStep[mapWorkspaceSnapshot(corrected).caseState]).toBe(3);
  });
  it("prevents duplicate submissions while the first command is pending", async () => {
    let release!: () => void;
    const blocked = new Promise<void>(resolve => { release = resolve; });
    const confirm = vi.fn(async () => { await blocked; });
    const provider: WorkspaceProvider = { districts: ["Sundargarh"],
      load: async () => mapWorkspaceSnapshot(corrected), confirmEvidence: confirm,
      rejectEvidence: async () => {} };
    const controller = new EvidenceDecisionController(provider);
    const first = controller.decide("sundargarh", initial.active_case.id, "ev-002", "Confirmed");
    expect(controller.pending).toBe(true);
    expect(await controller.decide("sundargarh", initial.active_case.id, "ev-002", "Confirmed")).toBeNull();
    expect(confirm).toHaveBeenCalledTimes(1);
    release(); await first;
    expect(controller.pending).toBe(false);
  });
  it("does not show a successful canonical mutation when a command fails", async () => {
    const provider: WorkspaceProvider = { districts: ["Sundargarh"],
      load: async () => mapWorkspaceSnapshot(initial),
      confirmEvidence: async () => { throw new ApiError("unavailable", 503, "Unavailable"); },
      rejectEvidence: async () => {} };
    const controller = new EvidenceDecisionController(provider);
    await expect(controller.decide("sundargarh", initial.active_case.id, "ev-002", "Confirmed")).rejects.toMatchObject({ status: 503 });
    expect(controller.pending).toBe(false);
    expect((await provider.load("sundargarh")).scenario.selectedId).toBe("sdh-bonai");
  });
  it("classifies conflict, forbidden, validation, missing and server errors centrally", async () => {
    for (const [status, kind] of [[409, "conflict"], [403, "forbidden"], [422, "validation"], [404, "not_found"], [503, "unavailable"]] as const) {
      const provider = new ApiDataProvider("", vi.fn(async () => json({}, status)) as typeof fetch);
      await expect(provider.load("sundargarh")).rejects.toMatchObject({ status, kind });
    }
  });
});
