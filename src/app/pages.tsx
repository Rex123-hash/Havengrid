import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  FileText,
  Filter,
  Network,
  Package,
  Search,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import { useWorkspace } from "./provider";
import {
  canReview,
  type Evidence,
} from "./contracts";
import {
  EvidenceComparison,
  FactValue,
  FreshnessBadge,
  Icons,
  NetworkCanvas,
  PageHeader,
  Panel,
  PanelTitle,
  PriorityFacilityCard,
  ProvenanceBadge,
  ReadinessRows,
  RecoveryTimeline,
  SignalCard,
  SourceBadge,
  StateBadge,
  UnknownState,
} from "./components";

export function Situation() {
  const { scenario, evidence, step, caseState, previousPlanInvalidated } = useWorkspace();
  const bonaiEvidence = evidence.find(e => e.facilityId === "sdh-bonai");
  const selected = scenario.facilities.find(f => f.id === scenario.selectedId);
  const pending = evidence.filter((e) =>
    ["Awaiting review", "Conflict"].includes(e.status),
  ).length;
  const gaps = scenario.facilities.filter(
    (f) => f.stock.value === null || f.currentness === "Corroborated",
  ).length;
  return (
    <>
      <div className="hv-signals">
        <SignalCard
          title="Care at Risk"
          value={step >= 9 ? "Coverage restored" : "1 priority facility"}
          detail={step >= 10 ? "Care delivery verified" : "Needs attention now"}
          href={"/app/facilities/" + scenario.recipientId}
          tone="sage"
          icon={Icons.risk}
        />
        <SignalCard
          title="Active Recovery"
          value={step === 12 ? "Case closed" : "1 case"}
          detail={caseState.replace(/_/g, " ")}
          href="/app/recovery"
          tone="forest"
          icon={Icons.recovery}
        />
        <SignalCard
          title="Evidence Review"
          value={pending + " pending"}
          detail={pending ? "Requires verification" : "No pending review"}
          href="/app/evidence"
          icon={Icons.evidence}
        />
        <SignalCard
          title="Data Gaps"
          value={gaps + " facilities"}
          detail="Incomplete or unverified"
          href="/app/intelligence"
          icon={Icons.network}
        />
      </div>
      <div className="hv-situation-main">
        <NetworkCanvas />
        <PriorityFacilityCard />
      </div>
      <div className="hv-situation-bottom">
        <Panel>
          <PanelTitle
            icon={<Package size={19} />}
            right={
              <Link to="/app/recovery" aria-label="Open recovery">
                <ArrowRight size={17} />
              </Link>
            }
          >
            Active recovery
          </PanelTitle>
          <RecoveryTimeline compact />
          <Link className="hv-note hv-row" to={"/app/cases/" + scenario.id}>
            <FileText size={18} />
            <span>
              <b>{previousPlanInvalidated ? `Rerouted from Bonai to ${selected?.short ?? "selected donor"}` : `${selected?.short ?? "No donor"} currently selected`}</b>
              <small>{previousPlanInvalidated ? "Based on confirmed field evidence" : "Awaiting field evidence confirmation"}</small>
            </span>
            <StateBadge tone="mint">
              {step === 12 ? "Closed" : "In progress"}
            </StateBadge>
          </Link>
        </Panel>
        <Panel>
          <PanelTitle
            right={
              <Link to="/app/evidence">
                <span className="hv-micro">{pending} to review →</span>
              </Link>
            }
          >
            Evidence inbox
          </PanelTitle>
          {bonaiEvidence && <Link to={"/app/evidence/" + bonaiEvidence.id} className="hv-evidence-mini">
            <div className="hv-row">
              <b>
                <i className="hv-dot coral" />
                Bonai SDH
              </b>
              <StateBadge tone={bonaiEvidence.status === "Confirmed" ? "mint" : "amber"}>{bonaiEvidence.status}</StateBadge>
            </div>
            <p>Stock count mismatch · rehearsal</p>
            <EvidenceComparison evidence={bonaiEvidence} />
          </Link>}
          <Link className="hv-inline-note" to={"/app/cases/" + scenario.id}>
            <FileText size={17} />
            <span>
              {previousPlanInvalidated ? `Plan invalidated → ${selected?.short ?? "donor"} selected` : `${selected?.short ?? "Donor"} plan awaiting evidence`}
              <small>{caseState.replace(/_/g, " ")}</small>
            </span>
          </Link>
        </Panel>
        <Panel>
          <PanelTitle icon={<Network size={19} />}>
            District readiness
          </PanelTitle>
          <ReadinessRows compact />
        </Panel>
      </div>
    </>
  );
}
export function NetworkPage() {
  const { scenario } = useWorkspace();
  const [layer, setLayer] = useState("Risk");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState("");
  const f = scenario.facilities.find((f) => f.id === selected);
  return (
    <>
      <div className="hv-toolbar">
        <div className="hv-segment" aria-label="Network layer">
          {["Risk", "Supply routes", "Freshness", "Programme"].map((l) => (
            <button
              key={l}
              aria-pressed={l === layer}
              className={l === layer ? "active" : ""}
              onClick={() => setLayer(l)}
            >
              {l}
            </button>
          ))}
        </div>
        <label className="hv-search">
          <Search size={16} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Find a facility"
            aria-label="Find a facility"
          />
        </label>
        <StateBadge>IFA Red · 14-day plan</StateBadge>
      </div>
      <div className={"hv-network-explorer " + (f ? "inspecting" : "")}>
        <NetworkCanvas
          large
          layer={layer}
          search={search}
          onInspect={setSelected}
        />
        {f && (
          <Panel className="hv-inspector">
            <div className="hv-row">
              <span className="hv-micro">Facility inspection</span>
              <button
                onClick={() => setSelected("")}
                aria-label="Close inspection"
              >
                ✕
              </button>
            </div>
            <h2>{f.short}</h2>
            <p>{f.block} · Sundargarh</p>
            <StateBadge
              tone={
                f.risk === "At risk"
                  ? "coral"
                  : f.risk === "Watch"
                    ? "amber"
                    : "mint"
              }
            >
              {f.risk}
            </StateBadge>
            <FactValue fact={f.stock} unit="tablets" label="Rehearsal stock" />
            <p>
              {f.currentness} identity · {f.inventoryStatus}
            </p>
            <FreshnessBadge>{f.evidenceAge}</FreshnessBadge>
            {f.active ? (
              <>
                <FactValue
                  fact={scenario.exposure}
                  label="Aggregate care exposure"
                />
                <Link
                  className="hv-button primary"
                  to={"/app/cases/" + scenario.id}
                >
                  Open active case <ArrowRight size={15} />
                </Link>
              </>
            ) : (
              <UnknownState
                title="No linked care estimate"
                text="This mock has no facility-level care denominator."
              />
            )}
            <Link className="hv-button" to={"/app/facilities/" + f.id}>
              View facility <ArrowRight size={15} />
            </Link>
          </Panel>
        )}
      </div>
      <div className="hv-note hv-row">
        <Network size={20} />
        <p>
          Schematic relationships, not geographic boundaries. Route facts are
          captured Google responses. Watch states include currentness gaps.
        </p>
      </div>
    </>
  );
}
export function Facilities() {
  const { scenario } = useWorkspace();
  const [search, setSearch] = useState("");
  const [risk, setRisk] = useState("All risk");
  const [tier, setTier] = useState("All types");
  const [inventory, setInventory] = useState("All inventory");
  const [fresh, setFresh] = useState("All freshness");
  const [active, setActive] = useState(false);
  const filtered = scenario.facilities.filter(
    (f) =>
      (f.short + " " + f.block).toLowerCase().includes(search.toLowerCase()) &&
      (risk === "All risk" || f.risk === risk) &&
      (tier === "All types" || f.tier === tier) &&
      (inventory === "All inventory" || f.inventoryStatus === inventory) &&
      (fresh === "All freshness" ||
        (fresh === "Needs review"
          ? f.currentness === "Corroborated" || f.stock.value === null
          : f.currentness === "Verified" && f.stock.value !== null)) &&
      (!active || f.active),
  );
  return (
    <>
      <div className="hv-directory-banner">
        <div>
          <span className="hv-micro">District care infrastructure</span>
          <strong>
            {scenario.facilities.length}
            <span> facilities. One connected response.</span>
          </strong>
        </div>
        <span>
          <ShieldCheck size={24} />
          Public identities
          <br />
          <small>Rehearsal inventory layer</small>
        </span>
      </div>
      <div className="hv-toolbar wrap">
        <label className="hv-search">
          <Search size={16} />
          <input
            aria-label="Search facilities"
            placeholder="Search facilities or blocks"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        {[
          [
            risk,
            setRisk,
            ["All risk", "At risk", "Watch", "Stable", "Unknown"],
          ],
          [tier, setTier, ["All types", "CHC", "SDH", "DHH"]],
          [
            inventory,
            setInventory,
            [
              "All inventory",
              "Available",
              "Source stale",
              "Inventory required",
            ],
          ],
          [
            fresh,
            setFresh,
            ["All freshness", "Count available", "Needs review"],
          ],
        ].map(([value, set, options], i) => (
          <select
            key={i}
            aria-label={
              [
                "Risk filter",
                "Facility type filter",
                "Inventory filter",
                "Freshness filter",
              ][i]
            }
            value={value as string}
            onChange={(e) => (set as (v: string) => void)(e.target.value)}
          >
            {(options as string[]).map((o) => (
              <option key={o}>{o}</option>
            ))}
          </select>
        ))}
        <button
          className={"hv-button " + (active ? "primary" : "")}
          onClick={() => setActive(!active)}
          aria-pressed={active}
        >
          <Filter size={14} />
          Active recovery
        </button>
      </div>
      <div className="hv-directory">
        {filtered.map((f) => (
          <Link
            className="hv-facility-row"
            key={f.id}
            to={"/app/facilities/" + f.id}
          >
            <span
              className={
                "hv-facility-symbol " + (f.risk === "At risk" ? "coral" : "")
              }
            >
              <Network size={22} />
            </span>
            <div>
              <h3>{f.short}</h3>
              <small>
                {f.block} · {f.tier} · {f.currentness}
              </small>
            </div>
            <div>
              <StateBadge
                tone={
                  f.risk === "At risk"
                    ? "coral"
                    : f.risk === "Watch"
                      ? "amber"
                      : "mint"
                }
              >
                {f.risk}
              </StateBadge>
              <small>{f.active ? "Active recovery" : "No active case"}</small>
            </div>
            <div>
              <b>
                {f.stock.value === null
                  ? "Stock unavailable"
                  : f.stock.value + " tablets"}
              </b>
              <small>
                {f.stock.value === null
                  ? "Inventory required"
                  : "Rehearsal field evidence"}
              </small>
            </div>
            <FreshnessBadge>{f.evidenceAge}</FreshnessBadge>
            <ArrowUpRight size={20} />
          </Link>
        ))}
      </div>
      {!filtered.length && (
        <UnknownState
          title="No facilities match"
          text="Try a different block, risk state or evidence filter."
          action={
            <button
              className="hv-button"
              onClick={() => {
                setSearch("");
                setRisk("All risk");
                setTier("All types");
                setInventory("All inventory");
                setFresh("All freshness");
                setActive(false);
              }}
            >
              Clear filters
            </button>
          }
        />
      )}
    </>
  );
}
export function FacilityWorkspace() {
  const { facilityId } = useParams();
  const { scenario, evidence, caseState } = useWorkspace();
  const [tab, setTab] = useState("Overview");
  const f = scenario.facilities.find((f) => f.id === facilityId);
  if (!f)
    return (
      <UnknownState
        title="Facility not found"
        text="This identifier is not in the current backend facility roster."
        action={<Link to="/app/facilities">Return to facilities →</Link>}
      />
    );
  const primary = f.id === scenario.recipientId;
  const observations = evidence.filter((e) => e.facilityId === f.id);
  return (
    <>
      <Link className="hv-back" to="/app/facilities">
        ← All facilities
      </Link>
      <PageHeader
        eyebrow={f.tier + " · " + f.block + " · Sundargarh"}
        title={f.short}
        subtitle={f.name}
      >
        <StateBadge tone={f.currentness === "Verified" ? "mint" : "amber"}>
          {f.currentness}
        </StateBadge>
      </PageHeader>
      <div className="hv-tabs" role="tablist" aria-label="Facility sections">
        {["Overview", "Supply", "Care", "Evidence", "History"].map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            className={tab === t ? "active" : ""}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>
      <div role="tabpanel" aria-label={tab} className="hv-tab-body">
        {tab === "Overview" && (
          <>
            <div className="hv-fact-strip">
              <FactValue
                fact={f.stock}
                unit="tablets"
                label="Usable stock"
              />
              {primary ? (
                <>
                  <FactValue
                    fact={scenario.breach}
                    label="Initial continuity breach"
                  />
                  <FactValue
                    fact={scenario.stockout}
                    label="Initial stockout forecast"
                  />
                  <FactValue
                    fact={scenario.exposure}
                    label="Care exposure · estimate"
                  />
                </>
              ) : (
                <UnknownState
                  title="Care impact unavailable"
                  text="No care obligation has been linked to this facility."
                />
              )}
            </div>
            <div className="hv-two">
              <Panel>
                <PanelTitle icon={<Package size={18} />}>
                  Supply outlook
                </PanelTitle>
                {primary ? (
                  <>
                    <FactValue
                      fact={scenario.incoming}
                      label="Scheduled rehearsal supply"
                    />
                    <FactValue
                      fact={scenario.baseline}
                      label="Baseline dispensing assumption"
                    />
                  </>
                ) : (
                  <UnknownState
                    title="Incoming supply not displayed"
                    text="No operational schedule is available in this presentation contract."
                  />
                )}
              </Panel>
              <Panel>
                <PanelTitle>Recovery work</PanelTitle>
                {primary ? (
                  <>
                    <h2>{caseState.replace(/_/g, " ")}</h2>
                    <p>
                      One care-aware intervention, with separate supply and care
                      verification.
                    </p>
                    <Link
                      className="hv-button primary"
                      to={"/app/cases/" + scenario.id}
                    >
                      Open intervention <ArrowRight size={16} />
                    </Link>
                  </>
                ) : (
                  <UnknownState
                    title="No active cases"
                    text="No recovery case is linked to this facility in the mock snapshot."
                  />
                )}
              </Panel>
            </div>
          </>
        )}
        {tab === "Supply" && (
          <>
            <div className="hv-two">
              <Panel>
                <PanelTitle>Inventory truth</PanelTitle>
                <FactValue
                  fact={f.stock}
                  unit="tablets"
                  label="Canonical rehearsal observation"
                />
                <FreshnessBadge>{f.evidenceAge}</FreshnessBadge>
                <UnknownState
                  title="Official facility stock unavailable"
                  text="AMB district totals cannot be substituted for a facility count."
                />
              </Panel>
              <Panel>
                <PanelTitle>Issue and replenishment</PanelTitle>
                <FactValue
                  fact={scenario.dispatchUnit}
                  label="Physical dispatch unit"
                />
                {primary && (
                  <FactValue
                    fact={scenario.incoming}
                    label="Incoming rehearsal supply"
                  />
                )}
                <p className="hv-muted">
                  Operational batch and expiry records are unavailable.
                </p>
              </Panel>
            </div>
            <Panel>
              <PanelTitle>District context</PanelTitle>
              <p>
                AMB stock is a district aggregate for FY 2025–26, as on June 3.
                It does not establish this facility's usable stock.
              </p>
              <Link className="hv-text-link" to="/app/intelligence">
                Inspect public sources <ArrowUpRight size={14} />
              </Link>
            </Panel>
          </>
        )}
        {tab === "Care" && (
          <div className="hv-two">
            <Panel className="hv-care-panel">
              <span className="hv-micro">Antenatal supplementation</span>
              {primary ? (
                <>
                  <FactValue
                    fact={scenario.exposure}
                    label="Aggregate obligations"
                  />
                  <p>Rehearsal estimate · programme context</p>
                  <div className="hv-note">
                    No patient identities. The public district KPI does not
                    derive a facility count.
                  </div>
                </>
              ) : (
                <UnknownState
                  title="Care not supported"
                  text="This facility has no aggregate session estimate in the scenario."
                />
              )}
            </Panel>
            <Panel>
              <PanelTitle>Programme basis</PanelTitle>
              <FactValue
                fact={scenario.programmeKpi}
                label="District programme KPI"
              />
              <p>
                Public AMB policy: {scenario.formulation}. Facility denominator:{" "}
                <b>unavailable</b>.
              </p>
              <ProvenanceBadge fact={scenario.exposure} />
            </Panel>
          </div>
        )}
        {tab === "Evidence" && (
          <Panel>
            <PanelTitle>Observations & confirmations</PanelTitle>
            {observations.length ? (
              observations.map((e) => (
                <Link
                  className="hv-evidence-line"
                  key={e.id}
                  to={"/app/evidence/" + e.id}
                >
                  <span>
                    {e.source}
                    <small>{e.captured}</small>
                  </span>
                  <StateBadge>{e.status}</StateBadge>
                  <ArrowRight size={16} />
                </Link>
              ))
            ) : (
              <UnknownState
                title="No attached evidence artifact"
                text="The scenario stock value has no uploaded photograph. Add a labelled observation when a real evidence provider is available."
              />
            )}
          </Panel>
        )}
        {tab === "History" && (
          <Panel>
            <PanelTitle>Inventory lineage & audit</PanelTitle>
            {observations.map((e) => (
              <div key={e.id} className="hv-audit-row">
                <FileText size={18} />
                <span>
                  <b>
                    {e.previous ?? "Unavailable"} →{" "}
                    {e.status === "Confirmed"
                      ? e.observed
                      : "Awaiting confirmation"}
                  </b>
                  <small>
                    {e.status} · {e.source}
                  </small>
                </span>
              </div>
            ))}
            {primary && <RecoveryTimeline />}
            {!observations.length && !primary && (
              <UnknownState
                title="No recorded transitions"
                text="History will appear when verified evidence or recovery actions are recorded."
              />
            )}
          </Panel>
        )}
      </div>
    </>
  );
}
export function Cases() {
  const { scenario, step, caseState, previousPlanInvalidated } = useWorkspace();
  const [filter, setFilter] = useState("Active");
  const visible =
    filter === "All" ||
    (filter === "Recently closed" ? step === 12 : step < 12);
  return (
    <>
      <div className="hv-toolbar">
        <div className="hv-segment">
          {["Active", "Needs attention", "Recently closed", "All"].map((x) => (
            <button
              key={x}
              className={filter === x ? "active" : ""}
              onClick={() => setFilter(x)}
            >
              {x}
            </button>
          ))}
        </div>
        <span className="hv-muted">Recovery work · controlled scenario</span>
      </div>
      {visible ? (
        <article className="hv-case-story">
          <div className="hv-case-story-main">
            <span className="hv-micro">IFA continuity · Sundargarh</span>
            <h2>
              Keep antenatal care
              <br />
              in motion.
            </h2>
            <p>Lahunipada CHC · {scenario.commodity}</p>
            <StateBadge tone="amber">{caseState.replace(/_/g, " ")}</StateBadge>
            <Link className="hv-text-link" to={"/app/cases/" + scenario.id}>
              Open Intervention Studio <ArrowRight size={19} />
            </Link>
          </div>
          <div className="hv-case-story-facts">
            <FactValue fact={scenario.breach} label="Initial breach" />
            <FactValue fact={scenario.exposure} label="Rehearsal obligations" />
            <FactValue
              fact={scenario.transfer}
              unit="tablets"
              label="Transfer calculation"
            />
          </div>
          {previousPlanInvalidated && <div className="hv-case-story-path">
            <span>
              Bonai SDH <s>Initial donor</s>
            </span>
            <ArrowRight />
            <span>
              {scenario.facilities.find(f => f.id === scenario.selectedId)?.short} <b>Replacement selected</b>
            </span>
          </div>}
        </article>
      ) : (
        <UnknownState
          title="No cases in this view"
          text="The rehearsal contains one primary case. Its stage determines where it appears."
        />
      )}
    </>
  );
}
export function CaseWorkspace() {
  const { caseId } = useParams();
  const { scenario, caseState, previousPlanInvalidated } = useWorkspace();
  const selected = scenario.facilities.find(f => f.id === scenario.selectedId);
  const bonaiEvidence = scenario.evidence.find(e => e.facilityId === "sdh-bonai");
  if (caseId !== scenario.id)
    return (
      <UnknownState
        title="Case not found"
        text="Choose a recovery case from the district index."
        action={<Link to="/app/cases">All cases →</Link>}
      />
    );
  return (
    <>
      <Link className="hv-back" to="/app/cases">
        ← Recovery cases
      </Link>
      <PageHeader
        eyebrow="Intervention Studio · controlled rehearsal"
        title="A safer path to care."
        subtitle={"Lahunipada CHC · " + scenario.commodity}
      >
        <StateBadge tone="mint">{caseState.replace(/_/g, " ")}</StateBadge>
      </PageHeader>
      <div className="hv-case-risk-strip">
        <FactValue fact={scenario.breach} label="Initial continuity breach" />
        <FactValue fact={scenario.stockout} label="Initial physical stockout" />
        <FactValue
          fact={scenario.exposure}
          label="Rehearsal estimate · obligations"
        />
        <FactValue
          fact={scenario.demand}
          unit="tablets"
          label="14-day demand"
        />
      </div>
      <div className="hv-studio-grid">
        <div>
          <div className="hv-section-head">
            <h2>Candidate donors</h2>
            <span className="hv-micro">Safety before proximity</span>
          </div>
          <div className="hv-donors">
            {scenario.donors.map((d) => {
              const f = scenario.facilities.find((f) => f.id === d.facilityId)!;
              return (
                <Panel
                  key={d.facilityId}
                  className={
                    "hv-donor " +
                    (d.verdict === "Recommended"
                      ? "recommended"
                      : d.verdict === "Invalidated"
                        ? "invalidated"
                        : "")
                  }
                >
                  <div className="hv-row">
                    <div>
                      <h3>{f.short}</h3>
                      <small>
                        {f.currentness} · {f.evidenceAge}
                      </small>
                    </div>
                    <StateBadge
                      tone={
                        d.verdict === "Invalidated"
                          ? "coral"
                          : d.verdict === "Recommended"
                            ? "mint"
                            : "amber"
                      }
                    >
                      {d.verdict}
                    </StateBadge>
                  </div>
                  <div className="hv-donor-stats">
                    <FactValue
                      fact={d.distance}
                      label={"Route · " + d.duration}
                    />
                    <FactValue
                      fact={d.quantity}
                      unit="tablets"
                      label="Candidate transfer"
                    />
                    <FactValue fact={d.margin} label="Post-transfer margin" />
                  </div>
                  <p className="hv-donor-reason">
                    {d.verdict === "Invalidated" ? (
                      <TriangleAlert size={15} />
                    ) : (
                      <Check size={15} />
                    )}{" "}
                    {d.reason}
                  </p>
                  <div className="hv-row">
                    <ProvenanceBadge
                      fact={d.expiry}
                      label={"Batch expiry · " + d.expiry.value}
                    />
                    <Link
                      className="hv-text-link"
                      to={"/app/facilities/" + d.facilityId}
                    >
                      Inspect <ArrowUpRight size={13} />
                    </Link>
                  </div>
                </Panel>
              );
            })}
          </div>
        </div>
        <div className="hv-studio-aside">
          <Panel className="hv-forest-panel">
            <span className="hv-micro">Recommended intervention</span>
            <h2>
              {selected?.short ?? "No selected donor"} →<br />
              {scenario.facilities.find(f => f.id === scenario.recipientId)?.short}
            </h2>
            <FactValue
              fact={scenario.transfer}
              unit="tablets"
              label="Transfer calculation"
            />
            <p>Recipient and donor continuity evaluated together.</p>
            <div className="hv-dark-note">
              <b>Physical dispatch unit: {scenario.dispatchUnit.value}</b>
              <p>
                Resolve packaging before any operational dispatch. This is a
                rehearsal calculation.
              </p>
            </div>
            <Link className="hv-button light" to="/app/recovery">
              Open recovery track <ArrowRight size={16} />
            </Link>
            <small>
              Backend plan · role authorization not evaluated · no physical transfer
            </small>
          </Panel>
          <Panel>
            <PanelTitle>What changed?</PanelTitle>
            <p>{previousPlanInvalidated ? "Confirmed field evidence invalidated the previous Bonai plan. The backend selected a replacement." : "Bonai field evidence is awaiting confirmation. The current plan remains selected by the backend."}</p>
            {bonaiEvidence && <EvidenceComparison evidence={bonaiEvidence} />}
            <Link className="hv-text-link" to={"/app/evidence/" + bonaiEvidence?.id}>
              Inspect evidence lineage <ArrowUpRight size={14} />
            </Link>
          </Panel>
        </div>
      </div>
    </>
  );
}
function EvidenceCard({ e }: { e: Evidence }) {
  const { scenario } = useWorkspace();
  const f = scenario.facilities.find((f) => f.id === e.facilityId)!;
  return (
    <Panel className="hv-evidence-card">
      <div className="hv-row">
        <h3>{f.short}</h3>
        <StateBadge
          tone={
            e.status === "Conflict"
              ? "coral"
              : e.status === "Confirmed"
                ? "mint"
                : "amber"
          }
        >
          {e.status}
        </StateBadge>
      </div>
      <p>
        {scenario.commodity} · {e.source}
      </p>
      <EvidenceComparison evidence={e} />
      <SourceBadge kind="REHEARSAL_EVIDENCE" />
      <div className="hv-actions">
        <Link className="hv-button primary" to={"/app/evidence/" + e.id}>
          {e.status === "Awaiting review" ? "Review evidence" : "Inspect evidence"} <ArrowRight size={15} />
        </Link>
      </div>
    </Panel>
  );
}
export function EvidenceInbox() {
  const { evidence } = useWorkspace();
  const [filter, setFilter] = useState("All");
  const groups = ["Awaiting review", "Conflicts", "Recently confirmed"];
  return (
    <>
      <div className="hv-toolbar">
        <div className="hv-segment">
          {["All", ...groups].map((x) => (
            <button
              key={x}
              className={filter === x ? "active" : ""}
              onClick={() => setFilter(x)}
            >
              {x}
            </button>
          ))}
        </div>
        <span className="hv-muted">Confirmation changes canonical truth.</span>
      </div>
      <div
        className={
          filter === "All" ? "hv-evidence-board" : "hv-evidence-board filtered"
        }
      >
        {groups
          .filter((g) => filter === "All" || g === filter)
          .map((g) => {
            const items = evidence.filter((e) =>
              g === "Awaiting review"
                ? ["Awaiting review", "Recount requested"].includes(e.status)
                : g === "Conflicts"
                  ? e.status === "Conflict"
                  : ["Confirmed", "Rejected"].includes(e.status),
            );
            return (
              <section key={g} className="hv-evidence-section">
                <div className="hv-section-head">
                  <h2>{g}</h2>
                  <span className="hv-count">{items.length}</span>
                </div>
                {items.length ? (
                  <div className="hv-evidence-grid">
                    {items.map((e) => (
                      <EvidenceCard key={e.id} e={e} />
                    ))}
                  </div>
                ) : (
                  <UnknownState
                    title="All clear here"
                    text="No observations in this review state."
                  />
                )}
              </section>
            );
          })}
      </div>
    </>
  );
}
export function EvidenceDetail() {
  const { evidenceId } = useParams();
  const { scenario, evidence, role, review, pendingEvidenceId, previousPlanInvalidated, caseState } = useWorkspace();
  const [confirming, setConfirming] = useState(false);
  const e = evidence.find((e) => e.id === evidenceId);
  if (!e)
    return (
      <UnknownState
        title="Evidence not found"
        text="Select a record from the evidence inbox."
        action={<Link to="/app/evidence">Evidence inbox →</Link>}
      />
    );
  const f = scenario.facilities.find((f) => f.id === e.facilityId)!;
  const actionable = !["Confirmed", "Rejected"].includes(e.status);
  return (
    <>
      <Link className="hv-back" to="/app/evidence">
        ← Evidence inbox
      </Link>
      <PageHeader
        eyebrow="Reality Lens · human verification"
        title={f.short + " observation"}
        subtitle={e.captured}
      >
        <StateBadge tone={e.status === "Confirmed" ? "mint" : "amber"}>
          {e.status}
        </StateBadge>
      </PageHeader>
      <div className="hv-evidence-detail">
        <div>
          <div className="hv-artifact">
            <div className="hv-artifact-corner" />
            <span className="hv-micro">Evidence artifact</span>
            <div className="hv-artifact-paper">
              <FileText size={38} />
              <h2>
                A count from
                <br />
                the field.
              </h2>
              <p>
                {f.short}
                <br />
                {scenario.commodity}
              </p>
              <span className="hv-micro">Human-entered observation</span>
              <hr />
              <b>
                {e.observed} <small>tablets observed</small>
              </b>
            </div>
            <div className="hv-artifact-caption">
              <ShieldCheck size={19} />
              <span>
                No photograph uploaded.
                <br />
                Controlled rehearsal field observation.
              </span>
            </div>
          </div>
          <div className="hv-note">
            <b>Confirmation changes canonical truth.</b>
            <p>
              Extraction alone does not. No AI extraction is running in this
              preview.
            </p>
          </div>
        </div>
        <Panel className="hv-observation">
          <PanelTitle>Observation details</PanelTitle>
          <dl className="hv-detail-list">
            {[
              ["Commodity", scenario.commodity],
              ["Observed quantity", e.observed + " tablets"],
              ["Batch", e.batch],
              ["Expiry", e.expiry],
              ["Timestamp", e.captured],
              ["Confidence", e.confidence],
              ["Source", e.source],
            ].map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
          <SourceBadge kind="REHEARSAL_EVIDENCE" />
          <div className="hv-comparison-box">
            <span className="hv-micro">
              {e.status === "Confirmed"
                ? "Recorded inventory lineage"
                : "Current canonical comparison"}
            </span>
            <EvidenceComparison evidence={e} />
          </div>
          <div className="hv-consequence">
            <TriangleAlert size={20} />
            <p>
              {e.status === "Confirmed" && previousPlanInvalidated
                ? `Backend correction invalidated the previous donor plan. Current case: ${caseState}.`
                : e.status === "Awaiting review"
                  ? "Confirmation will send this observation to the backend. The current plan remains unchanged until the server responds."
                  : `Backend evidence status: ${e.status}.`}
            </p>
          </div>
          {canReview(role) && actionable ? (
            <>
              {confirming ? (
                <div className="hv-confirm">
                  <b>
                    Confirm {e.observed} tablets as the canonical count?
                  </b>
                  <p>
                    The backend will evaluate the effect on inventory and the intervention plan.
                  </p>
                  <div className="hv-actions">
                    <button
                      className="hv-button primary"
                      disabled={pendingEvidenceId !== null}
                      onClick={() => { void review(e.id, "Confirmed"); setConfirming(false); }}
                    >
                      {pendingEvidenceId === e.id ? "Submitting…" : "Confirm observation"}
                    </button>
                    <button
                      className="hv-button"
                      onClick={() => setConfirming(false)}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  className="hv-button primary"
                  onClick={() => setConfirming(true)}
                >
                  <Check size={16} />
                  Confirm observation
                </button>
              )}
              <div className="hv-actions">
                <button
                  className="hv-button"
                  disabled={pendingEvidenceId !== null}
                  onClick={() => void review(e.id, "Rejected")}
                >
                  Reject
                </button>
              </div>
            </>
          ) : (
            <p className="hv-note">
              {role === "VIEWER"
                ? "Viewer access · read-only evidence review."
                : "This record is finalized. Its original observation remains in the lineage."}
            </p>
          )}
        </Panel>
      </div>
    </>
  );
}
export function Recovery() {
  const { scenario, step, caseState, domainLegalActions, authorizationStatus, completedActions,
    coverageStatus, careProtected, careImpactExposed } = useWorkspace();
  return (
    <>
      <div className="hv-recovery-banner">
        <div>
          <span className="hv-micro">The continuity promise</span>
          <h2>
            {step >= 9 ? "Supply restored." : "Restore the supply."}
            <br />
            <em>
              {step >= 10 ? "Care delivery verified." : "Then verify the care."}
            </em>
          </h2>
          <p>One recovery. Two distinct verifications.</p>
        </div>
        <div>
          <StateBadge tone="mint">{caseState.replace(/_/g, " ")}</StateBadge>
          <p>Lahunipada CHC · {scenario.commodity}</p>
          <Link to={"/app/cases/" + scenario.id} className="hv-text-link">
            View intervention <ArrowRight size={16} />
          </Link>
        </div>
      </div>
      <div className="hv-recovery-layout">
        <Panel>
          <PanelTitle icon={<ShieldCheck size={18} />}>
            Recovery lifecycle
          </PanelTitle>
          <RecoveryTimeline />
        </Panel>
        <div className="hv-recovery-work">
          <Panel>
            <PanelTitle icon={<Package size={18} />}>
              01 · Supply recovery
            </PanelTitle>
            <h2>{step >= 9 ? "Coverage restored" : "Verify the transfer"}</h2>
            <p>
              Source count, destination count and batch verification must
              precede reconciliation.
            </p>
            <div className="hv-verification-pills">
              {[
                ["Source", 6],
                ["Destination", 7],
                ["Batch", 8],
                ["Coverage", 9],
              ].map(([label, n]) => (
                <StateBadge key={label} tone={step >= Number(n) ? "mint" : ""}>
                  {step >= Number(n) ? "✓ " : ""}
                  {label}
                </StateBadge>
              ))}
            </div>
            <div className="hv-fact-strip">
              <FactValue
                fact={scenario.transfer}
                unit="tablets"
                label="Calculated transfer"
              />
              <FactValue
                fact={scenario.dispatchUnit}
                label="Physical packaging"
              />
            </div>
          </Panel>
          <Panel className={step >= 10 ? "hv-care-verified" : ""}>
            <PanelTitle icon={<ShieldCheck size={18} />}>
              02 · Care recovery
            </PanelTitle>
            <h2>{step >= 10 ? "Delivery verified" : "Was care delivered?"}</h2>
            <p>
              Coverage recovery does not prove that the aggregate
              supplementation obligation was delivered.
            </p>
            <FactValue
              fact={scenario.exposure}
              label="Rehearsal aggregate obligation"
            />
            <FactValue fact={careImpactExposed} label="Backend-exposed obligations" />
          </Panel>
          <Panel>
            <PanelTitle>Backend lifecycle</PanelTitle>
            <h3>{caseState.replace(/_/g, " ")}</h3>
            <p>Later recovery commands are read-only in this integration gate.</p>
            <p>Coverage: {coverageStatus.replace(/_/g, " ")} · Care protected: {careProtected ? "verified" : "not verified"}.</p>
            <p className="hv-note">Domain legal actions: {domainLegalActions.join(", ") || "none"}. Role authorization: {authorizationStatus.replace(/_/g, " ")}.</p>
            {completedActions.length > 0 && <p>Completed audit actions: {completedActions.join(", ")}</p>}
          </Panel>
        </div>
      </div>
    </>
  );
}
export function Intelligence() {
  const { scenario, limitations, districtStockSignals } = useWorkspace();
  const latestStock = districtStockSignals[districtStockSignals.length - 1];
  return (
    <>
      <div className="hv-intelligence-hero">
        <div>
          <span className="hv-micro">
            A district is only as clear as its evidence
          </span>
          <h2>
            Confidence, with
            <br />
            <em>the gaps in view.</em>
          </h2>
          <p>Public context. Field truth. Visible uncertainty.</p>
        </div>
        <div className="hv-confidence-ring">
          <ShieldCheck size={32} />
          <b>Partial</b>
          <small>Operational readiness</small>
        </div>
      </div>
      <div className="hv-two">
        <Panel>
          <PanelTitle>District readiness</PanelTitle>
          <ReadinessRows />
        </Panel>
        <Panel>
          <PanelTitle icon={<TriangleAlert size={18} />}>Data gaps</PanelTitle>
          <div className="hv-gap-list">
            {limitations.map((text, index) => (
              <div key={index}>
                <CircleIcon />
                <span>
                  <b>Data limitation {index + 1}</b>
                  <p>{text}</p>
                </span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
      <div className="hv-section-head">
        <h2>Source catalog</h2>
        <span className="hv-micro">Authority is visible</span>
      </div>
      {latestStock && <Panel>
        <PanelTitle>District public stock context</PanelTitle>
        <FactValue fact={latestStock.available} label={`Latest captured period · ${latestStock.period}`} />
        <p>{latestStock.granularity} aggregate only. This does not establish current facility inventory.</p>
        {latestStock.qualityFlags.length > 0 && <small>Source flags: {latestStock.qualityFlags.join(", ")}</small>}
      </Panel>}
      <div className="hv-source-grid">
        {scenario.sources.map((s) => (
          <Panel key={s.name}>
            <SourceBadge kind={s.classification} />
            <h3>{s.name}</h3>
            <p>{s.authority}</p>
            <small>{s.period}</small>
            <p>{s.fields}</p>
            <a
              className="hv-text-link"
              href={s.url}
              target="_blank"
              rel="noreferrer"
            >
              Inspect source <ArrowUpRight size={15} />
            </a>
          </Panel>
        ))}
      </div>
      <Panel>
        <PanelTitle icon={<Sparkles size={18} />}>
          Candidate source review
        </PanelTitle>
        <div className="hv-two">
          <div>
            <StateBadge tone="amber">Future intelligence workflow</StateBadge>
            <h3>Two identities need a current source.</h3>
            <p>
              Laing and Mangaspur remain historically corroborated. No AI
              discovery is running.
            </p>
          </div>
          <div>
            <h3>A newer source could close the gap.</h3>
            <p>
              Future suggestions will carry authority, timestamps and conflicts
              before human verification.
            </p>
          </div>
        </div>
      </Panel>
    </>
  );
}
function CircleIcon() {
  return <span className="hv-gap-icon">!</span>;
}
export function Settings() {
  const {
    role,
    setRole,
    mode,
    refresh,
    notifications,
    setNotifications,
  } = useWorkspace();
  return (
    <div className="hv-settings">
      <Panel>
        <PanelTitle>Your workspace</PanelTitle>
        <h2>Ananya S.</h2>
        <p>District team · preview identity</p>
        <label className="hv-form-label">
          Mock role
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as typeof role)}
          >
            {["VIEWER", "FIELD REVIEWER", "COORDINATOR"].map((r) => (
              <option key={r}>{r}</option>
            ))}
          </select>
        </label>
        <p>
          This is a preview role. Backend authorization has not been evaluated.
        </p>
        <label className="hv-form-label">
          Workspace mode
          <select value={mode} disabled>
            <option>REHEARSAL</option>
            <option>OPERATIONAL</option>
          </select>
        </label>
        <p>
          The current backend workspace is a controlled rehearsal.
        </p>
      </Panel>
      <Panel>
        <PanelTitle>Rehearsal controls</PanelTitle>
        <h3>Refresh canonical state.</h3>
        <p>
          Reload the current case and evidence from FastAPI.
        </p>
        <button className="hv-button" onClick={() => void refresh()}>Refresh workspace</button>
        <hr />
        <h3>Notification preference</h3>
        <label className="hv-check">
          <input
            type="checkbox"
            checked={notifications !== false}
            onChange={(e) => setNotifications(e.target.checked)}
          />
          Show local action confirmations
        </label>
        <p className="hv-muted">
          No external notifications, accounts or credentials are configured.
        </p>
        <Link to="/login" className="hv-text-link">
          Return to mock login <ArrowRight size={16} />
        </Link>
      </Panel>
    </div>
  );
}
export function OtherDistrict() {
  const { district, setDistrict } = useWorkspace();
  return (
    <>
      <div className="hv-intelligence-hero">
        <div>
          <span className="hv-micro">District workspace · preview</span>
          <h2>
            {district}
            <br />
            <em>Start with what is known.</em>
          </h2>
          <p>
            Public district context is available. Facility-level workflows await
            evidence.
          </p>
        </div>
        <StateBadge tone="amber">Onboarding readiness</StateBadge>
      </div>
      <div className="hv-two">
        <Panel>
          <PanelTitle>District readiness</PanelTitle>
          {[
            "Facility roster",
            "Facility inventory",
            "Routes",
            "Care obligations",
          ].map((l) => (
            <div className="hv-evidence-line" key={l}>
              <b>{l}</b>
              <StateBadge>Unavailable</StateBadge>
            </div>
          ))}
        </Panel>
        <Panel>
          <UnknownState
            title="No active cases"
            text="This lightweight district mock has no facility scenario. Sundargarh case data is not reused here."
            action={
              <button
                className="hv-button primary"
                onClick={() => setDistrict("Sundargarh")}
              >
                Explore Sundargarh rehearsal <ArrowRight size={16} />
              </button>
            }
          />
        </Panel>
      </div>
    </>
  );
}
