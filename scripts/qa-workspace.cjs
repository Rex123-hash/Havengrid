const {
  chromium,
} = require("C:/Users/OMEN/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const fs = require("node:fs");
const path = require("node:path");
(async () => {
  const dir = path.resolve("docs/ui-1/screenshots");
  fs.mkdirSync(dir, { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    executablePath:
      "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  });
  const page = await browser.newPage();
  const errors = [];
  const api = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (r.url().includes("/api/")) api.push(r.url());
  });
  const routes = [
    ["login", "/login"],
    ["situation", "/app"],
    ["network", "/app/network"],
    ["facilities", "/app/facilities"],
    ["facility", "/app/facilities/chc-lahunipada"],
    ["cases", "/app/cases"],
    ["case", "/app/cases/case-lahunipada-ifa-red-rehearsal-001"],
    ["evidence", "/app/evidence"],
    ["evidence-detail", "/app/evidence/laing-recount"],
    ["recovery", "/app/recovery"],
    ["intelligence", "/app/intelligence"],
    ["settings", "/app/settings"],
  ];
  const results = [];
  for (const width of [1440, 1920]) {
    await page.setViewportSize({ width, height: width === 1440 ? 900 : 1080 });
    for (const [name, url] of routes) {
      await page.goto("http://127.0.0.1:5173" + url);
      await page.waitForTimeout(450);
      await page.evaluate(() => document.fonts.ready);
      const dimensions = await page.evaluate(() => ({
        scroll: document.documentElement.scrollWidth,
        viewport: innerWidth,
        height: document.documentElement.scrollHeight,
      }));
      if (dimensions.scroll > width)
        errors.push(name + " overflows at " + width);
      await page.screenshot({
        path: path.join(dir, name + "-" + width + ".png"),
        fullPage: true,
      });
      results.push({ page: name, width, ...dimensions });
    }
  }
  // Review confirmation persists on the linked facility, without backend I/O.
  await page.goto("http://127.0.0.1:5173/app/evidence/laing-recount");
  await page
    .getByRole("button", { name: "Confirm observation", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Confirm local observation", exact: true })
    .click();
  await page.goto("http://127.0.0.1:5173/app/facilities/chc-laing");
  if (!(await page.locator(".hv-fact").first().innerText()).includes("198"))
    errors.push("Confirmed count did not reach facility");
  // Role state: viewers cannot mutate evidence or recovery.
  await page.goto("http://127.0.0.1:5173/app/settings");
  await page.getByLabel("Mock role").selectOption("VIEWER");
  await page.goto("http://127.0.0.1:5173/app/evidence/mangaspur-conflict");
  if (
    await page
      .getByRole("button", { name: "Confirm observation", exact: true })
      .count()
  )
    errors.push("Viewer can confirm");
  await page.goto("http://127.0.0.1:5173/app/recovery");
  if (
    await page
      .getByRole("button", { name: "Approve mock plan", exact: true })
      .count()
  )
    errors.push("Viewer can approve");
  // District switching cannot leak Sundargarh scenario details.
  await page.getByLabel("District workspace").selectOption("Sambalpur");
  if (await page.getByText("Lahunipada CHC", { exact: true }).count())
    errors.push("District scenario leaked");
  await page.reload();
  if (
    (await page.getByLabel("District workspace").inputValue()) !== "Sambalpur"
  )
    errors.push("District did not persist");
  await page.getByLabel("District workspace").selectOption("Sundargarh");
  await page.goto("http://127.0.0.1:5173/app/settings");
  await page.getByLabel("Mock role").selectOption("COORDINATOR");
  await page
    .getByRole("button", { name: "Reset local rehearsal", exact: true })
    .click();
  await page
    .getByLabel("Workspace mode", { exact: true })
    .selectOption("OPERATIONAL");
  if (
    !(await page
      .getByText(
        "Operational shell preview · controlled mock data · explicit local actions only",
        { exact: true },
      )
      .count())
  )
    errors.push("Operational notice missing");
  await page
    .getByLabel("Workspace mode", { exact: true })
    .selectOption("REHEARSAL");
  // Recovery: unknown outcomes do not cross the care-delivery gate.
  await page.goto("http://127.0.0.1:5173/app/recovery");
  for (const label of [
    "Approve mock plan",
    "Record mock dispatch",
    "Verify source count",
    "Verify destination count",
    "Verify batch match",
    "Reconcile coverage",
  ])
    await page.getByRole("button", { name: label, exact: true }).click();
  await page.getByLabel("Care-delivery outcome").selectOption("UNKNOWN");
  await page
    .getByRole("button", { name: "Record care outcome", exact: true })
    .click();
  if (!(await page.getByLabel("Care-delivery outcome").count()))
    errors.push("Unknown care advanced");
  await page.getByLabel("Care-delivery outcome").selectOption("DELIVERED");
  await page
    .getByRole("button", { name: "Record care outcome", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Record care protection", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Close rehearsal case", exact: true })
    .click();
  if (!(await page.getByText("Rehearsal closed", { exact: true }).count()))
    errors.push("Recovery closure failed");
  // Global command surface: shortcut, scripted source-backed answer, escape.
  await page.goto("http://127.0.0.1:5173/app");
  await page.getByRole("button", { name: "Ask Haven", exact: true }).waitFor();
  await page.keyboard.press("Control+k");
  await page
    .getByRole("button", { name: "Why was Bonai rejected?", exact: true })
    .click();
  if (!(await page.getByText("DONOR_ALREADY_AT_RISK", { exact: true }).count()))
    errors.push("Ask answer missing");
  await page.screenshot({
    path: path.join(dir, "ask-haven-1920.png"),
    fullPage: true,
  });
  await page.keyboard.press("Escape");
  if (await page.getByRole("dialog").count())
    errors.push("Escape did not close");
  // Facility filters and tabs.
  await page.goto("http://127.0.0.1:5173/app/facilities");
  await page
    .getByLabel("Search facilities", { exact: true })
    .fill("no-such-facility");
  if (!(await page.getByText("No facilities match", { exact: true }).count()))
    errors.push("Empty filter not shown");
  await page
    .getByRole("button", { name: "Clear filters", exact: true })
    .click();
  await page.goto("http://127.0.0.1:5173/app/facilities/chc-lahunipada");
  for (const tab of ["Supply", "Care", "Evidence", "History"]) {
    await page.getByRole("tab", { name: tab, exact: true }).click();
    if (!(await page.getByRole("tabpanel", { name: tab }).isVisible()))
      errors.push("Tab failed " + tab);
  }
  // Keyboard node selection.
  await page.goto("http://127.0.0.1:5173/app/network");
  await page.getByRole("button", { name: /Lahunipada CHC,.*Verified/ }).focus();
  await page.keyboard.press("Enter");
  if (!(await page.getByText("Facility inspection", { exact: true }).count()))
    errors.push("Keyboard network inspection failed");
  // Graceful laptop/mobile and reduced motion.
  for (const width of [1100, 768, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("http://127.0.0.1:5173/app");
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.screenshot({
      path: path.join(dir, "situation-" + width + ".png"),
      fullPage: true,
    });
    if (
      await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      )
    )
      errors.push("Narrow overflow " + width);
  }
  // Restore clean demo snapshot.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("http://127.0.0.1:5173/login");
  await page.getByLabel("Preview experience").selectOption("multi");
  await page.getByRole("button", { name: /Continue with Google/ }).click();
  await page.getByText("Choose your district.", { exact: true }).waitFor();
  await page.screenshot({ path: path.join(dir, "workspace-chooser-1440.png"), fullPage: true });
  await page.getByRole("button", { name: /Kalahandi/ }).click();
  await page.getByLabel("District workspace").waitFor();
  if (await page.getByLabel("District workspace").inputValue() !== "Kalahandi") errors.push("Multi-district login failed");
  await page.goto("http://127.0.0.1:5173/login");
  await page.getByLabel("Preview experience").selectOption("new");
  await page.getByRole("button", { name: /Continue with Google/ }).click();
  await page.getByLabel("Organization or district").fill("District preview team");
  await page.getByRole("button", { name: /Create local onboarding draft/ }).click();
  await page.getByText("District preview team · draft prepared", { exact: true }).waitFor();
  await page.screenshot({ path: path.join(dir, "onboarding-1440.png"), fullPage: true });
  await page.getByRole("button", { name: "Explore the rehearsal", exact: true }).click();
  await page.getByLabel("District workspace").waitFor();
  if (await page.getByLabel("District workspace").inputValue() !== "Sundargarh") errors.push("Onboarding entry failed");
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("http://127.0.0.1:5173/app/settings");
  await page
    .getByRole("button", { name: "Reset local rehearsal", exact: true })
    .click();
  fs.writeFileSync(
    path.resolve("docs/ui-1/qa-results.json"),
    JSON.stringify(
      {
        results,
        errors,
        backendRequests: api,
        checks: [
          "Evidence confirmation and persistence",
          "Viewer restrictions",
          "District persistence and isolation",
          "Mode visibility",
          "Separate coverage/care gates",
          "Ask shortcut and escape",
          "Facility filters and tabs",
          "Keyboard network selection",
          "Reduced motion and narrow layouts",
          "Multi-district mock login and onboarding draft",
        ],
      },
      null,
      2,
    ),
  );
  console.log(
    JSON.stringify(
      { pages: results.length, errors, backendRequests: api },
      null,
      2,
    ),
  );
  await browser.close();
  if (errors.length || api.length) process.exitCode = 1;
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
