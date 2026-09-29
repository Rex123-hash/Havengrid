/** Authenticated workspace source policy, separate from the historical landing replay. */
export function resolveWorkspaceSource(source: string | undefined, env: string | undefined,
  mode: string | undefined): "api" | "mock" {
  const selected = (source ?? "api").toLowerCase();
  if (selected !== "api" && selected !== "mock") throw new Error(`Unknown VITE_WORKSPACE_SOURCE "${source}"`);
  if (selected === "mock" && (!["development", "test"].includes((env ?? "development").toLowerCase()) ||
    (mode ?? "rehearsal").toLowerCase() !== "rehearsal")) {
    throw new Error("Mock workspace data is allowed only in development/test rehearsal.");
  }
  return selected;
}
