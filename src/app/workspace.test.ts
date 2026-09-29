import { describe, expect, it } from "vitest";
import { mockProvider } from "./mock";
import {
  canAdvance,
  canReview,
  classificationLabels,
  nextRecoveryStep,
  recoverySteps,
} from "./contracts";

describe("workspace presentation boundary", () => {
  const scenario = mockProvider.getScenario();
  it("preserves the approved provenance distinctions", () => {
    expect(scenario.exposure.classification).toBe("REHEARSAL_ASSUMPTION");
    expect(scenario.baseline.classification).toBe("REHEARSAL_ASSUMPTION");
    expect(scenario.programmeKpi.classification).toBe("REAL_PUBLIC");
    expect(scenario.donors[0].distance.classification).toBe(
      "LIVE_EXTERNAL_API",
    );
    expect(scenario.transfer.classification).toBe("MODEL_DERIVED");
    expect(scenario.dispatchUnit.classification).toBe("UNKNOWN");
  });
  it("resolves every candidate to a roster entry without obsolete illustrative facilities", () => {
    expect(
      scenario.donors.every((d) =>
        scenario.facilities.some((f) => f.id === d.facilityId),
      ),
    ).toBe(true);
    for (const forbidden of ["bhatpar", "kuchinda", "remed", "tileibani"])
      expect(JSON.stringify(scenario.facilities).toLowerCase()).not.toContain(
        forbidden,
      );
    expect(
      scenario.facilities
        .filter((f) => f.currentness === "Corroborated")
        .map((f) => f.id),
    ).toEqual(["chc-laing", "chc-mangaspur"]);
  });
  it("all display facts have source, class and explanation", () => {
    function visit(value: unknown) {
      if (!value || typeof value !== "object") return;
      if (
        "value" in value &&
        "classification" in value &&
        "source" in value &&
        "explanation" in value
      ) {
        const f = value as {
          classification: keyof typeof classificationLabels;
          source: string;
          explanation: string;
        };
        expect(classificationLabels[f.classification]).toBeTruthy();
        expect(f.source).toBeTruthy();
        expect(f.explanation).toBeTruthy();
      }
      for (const child of Object.values(value)) visit(child);
    }
    visit(scenario);
  });
  it("keeps coverage and care milestones separate", () => {
    expect(recoverySteps[9]).toBe("Coverage restored");
    for (const outcome of ["UNKNOWN", "NOT_DELIVERED", "DEFERRED"])
      expect(nextRecoveryStep(9, outcome)).toBe(9);
    expect(nextRecoveryStep(9, "DELIVERED")).toBe(10);
    expect(recoverySteps[10]).toBe("Care delivery verified");
    expect(nextRecoveryStep(12)).toBe(12);
  });
  it("viewer capabilities are read-only and reviewers cannot approve or close", () => {
    expect(canReview("VIEWER")).toBe(false);
    recoverySteps.forEach((_, step) =>
      expect(canAdvance("VIEWER", step)).toBe(false),
    );
    expect(canAdvance("FIELD REVIEWER", 3)).toBe(false);
    expect(canAdvance("FIELD REVIEWER", 5)).toBe(true);
    expect(canAdvance("FIELD REVIEWER", 11)).toBe(false);
    expect(canAdvance("COORDINATOR", 3)).toBe(true);
  });
  it("retains previous values after a pending evidence observation", () => {
    const pending = scenario.evidence.find(
      (e) => e.status === "Awaiting review",
    )!;
    expect(
      scenario.facilities.find((f) => f.id === pending.facilityId)?.stock.value,
    ).toBe(pending.previous);
    expect(pending.observed).not.toBe(pending.previous);
  });
});
