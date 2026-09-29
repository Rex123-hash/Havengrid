import type { WorkspaceData, WorkspaceProvider } from "./contracts";

/** One in-flight evidence decision; only the subsequent GET supplies new workspace truth. */
export class EvidenceDecisionController {
  private inFlight = false;
  constructor(private readonly provider: WorkspaceProvider) {}
  get pending() { return this.inFlight; }
  async decide(districtId: string, caseId: string, evidenceId: string,
    decision: "Confirmed" | "Rejected"): Promise<WorkspaceData | null> {
    if (this.inFlight) return null;
    this.inFlight = true;
    try {
      if (decision === "Confirmed") await this.provider.confirmEvidence(caseId, evidenceId);
      else await this.provider.rejectEvidence(caseId, evidenceId);
      return await this.provider.load(districtId);
    } finally { this.inFlight = false; }
  }
}
