const { chromium } = require("C:/Users/OMEN/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const fs = require("node:fs");
const path = require("node:path");

(async () => {
  const out = path.join(process.env.TEMP || ".", "haven-gate3-qa");
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ headless: true,
    executablePath: "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  const errors = [], requests = [];
  page.on("pageerror", e => errors.push(e.message));
  page.on("request", r => { if (r.url().includes("/api/")) requests.push(`${r.method()} ${r.url()}`); });
  const base = "http://127.0.0.1:5173";
  try {
    await page.goto(base + "/login");
    await page.getByRole("button", { name: /Continue with Google/ }).click();
    await page.getByText("Situation Room", { exact: true }).first().waitFor();
    const before = await page.locator("body").innerText();
    await page.screenshot({ path: path.join(out, "before-situation.png"), fullPage: true });
    for (const route of ["network", "facilities/chc-lahunipada", "cases", "cases/case-lahunipada-ifa-red-rehearsal-001", "evidence", "recovery", "intelligence"]) {
      await page.goto(base + "/app/" + route);
      await page.locator(".hv-header").waitFor();
      await page.waitForTimeout(650);
      await page.screenshot({ path: path.join(out, `before-${route.replaceAll("/", "-")}.png`), fullPage: true });
    }
    await page.goto(base + "/app/evidence/ev-002");
    await page.getByText("120", { exact: true }).first().waitFor();
    await page.waitForTimeout(650);
    const evidenceBefore = await page.locator("body").innerText();
    await page.screenshot({ path: path.join(out, "before-bonai-evidence.png"), fullPage: true });
    await page.getByRole("button", { name: "Confirm observation", exact: true }).click();
    await page.getByRole("button", { name: "Confirm observation", exact: true }).last().click();
    await page.getByText("Confirmed", { exact: true }).first().waitFor({ timeout: 10000 });
    await page.waitForTimeout(650);
    const evidenceAfter = await page.locator("body").innerText();
    await page.screenshot({ path: path.join(out, "after-bonai-evidence.png"), fullPage: true });
    const afterPages = {};
    for (const route of ["network", "cases/case-lahunipada-ifa-red-rehearsal-001", "recovery", ""]) {
      await page.goto(base + "/app/" + route);
      await page.locator(".hv-header").waitFor();
      await page.waitForTimeout(650);
      afterPages[route || "situation"] = (await page.locator("body").innerText()).slice(0, 3000);
      await page.screenshot({ path: path.join(out, `after-${(route || "situation").replaceAll("/", "-")}.png`), fullPage: true });
    }
    await page.reload();
    await page.locator(".hv-header").waitFor();
    await page.waitForTimeout(650);
    const reload = await page.locator("body").innerText();
    if (!before.includes("AWAITING EVIDENCE CONFIRMATION") || !before.includes("SDH Bonai") ||
        !evidenceBefore.includes("Awaiting review") || !evidenceBefore.includes("120") ||
        !evidenceAfter.includes("PLAN_RECALCULATED") ||
        !afterPages.network.includes("SDH Bonai\nDonor · invalidated\nSDH Panposh\nDonor · selected") ||
        !afterPages["cases/case-lahunipada-ifa-red-rehearsal-001"].includes("PLAN RECALCULATED") ||
        !afterPages["cases/case-lahunipada-ifa-red-rehearsal-001"].includes("Invalidated") ||
        !afterPages.recovery.includes("PLAN RECALCULATED") ||
        !afterPages.situation.includes("PLAN RECALCULATED") ||
        !reload.includes("PLAN RECALCULATED") ||
        !requests.some(r => r.includes("POST ") && r.endsWith("/ev-002/confirm")) || errors.length) {
      throw new Error("Gate 3 browser assertions failed: " + JSON.stringify({ afterPages, reload, requests, errors }));
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.screenshot({ path: path.join(out, "after-situation-1440.png"), fullPage: true });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    if (overflow) throw new Error("Situation Room overflows at 1440px");
    const unavailable = await browser.newPage();
    await unavailable.route("**/api/**", route => route.abort());
    await unavailable.goto(base + "/app");
    await unavailable.getByText("Operational data unavailable").waitFor();
    const failureText = await unavailable.locator("body").innerText();
    if (!failureText.includes("No rehearsal values were substituted") || failureText.includes("SDH Bonai"))
      throw new Error("API failure did not remain explicit");
    await unavailable.waitForTimeout(650);
    await unavailable.screenshot({ path: path.join(out, "backend-unavailable.png"), fullPage: true });
    await unavailable.close();
    const report = { beforeState: "AWAITING_EVIDENCE_CONFIRMATION", beforeDonor: "sdh-bonai",
      beforeEvidence: "120 canonical / 20 observed / pending", post: requests.find(r => r.includes("POST ")),
      afterState: "PLAN_RECALCULATED", afterDonor: "sdh-panposh", afterEvidence: "confirmed / canonical 20",
      pages: ["situation", "network", "facility", "cases", "case", "evidence", "recovery", "intelligence"],
      reload: "server state retained", unavailable: "explicit, no mock fallback", overflow1440: false,
      pageErrors: errors, screenshots: out };
    fs.writeFileSync(path.join(out, "qa-report.json"), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
