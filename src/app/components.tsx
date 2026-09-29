import { useState, useId, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  CircleHelp,
  Clock3,
  FileText,
  Maximize2,
  Minimize2,
  Network,
  Package,
  ShieldCheck,
  TriangleAlert,
  LocateFixed,
  X,
} from "lucide-react";
import {
  classificationLabels,
  recoverySteps,
  type Fact,
  type FactClass,
  type Facility,
  type Evidence,
} from "./contracts";
import { useWorkspace } from "./provider";

export function ProvenanceBadge({
  fact,
  label,
}: {
  fact: Pick<
    Fact<unknown>,
    "classification" | "source" | "explanation" | "asOf"
  >;
  label?: string;
}) {
  return (
    <details className="hv-provenance">
      <summary>
        <span className={"hv-provenance-dot " + fact.classification} />
        {label || classificationLabels[fact.classification]}
        <CircleHelp size={11} />
      </summary>
      <div className="hv-provenance-pop">
        <b>{fact.source}</b>
        <p>{fact.explanation}</p>
        {fact.asOf && <small>{fact.asOf}</small>}
      </div>
    </details>
  );
}
export function SourceBadge({ kind }: { kind: FactClass }) {
  return (
    <span className="hv-source">
      <span className={"hv-provenance-dot " + kind} />
      {classificationLabels[kind]}
    </span>
  );
}
export function StateBadge({
  children,
  tone,
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={"hv-state " + (tone || "")}>{children}</span>;
}
export function FreshnessBadge({ children }: { children: ReactNode }) {
  return (
    <span className="hv-fresh">
      <Clock3 size={12} />
      {children}
    </span>
  );
}
export function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={"hv-panel " + className}>{children}</section>;
}
export function PanelTitle({
  children,
  right,
  icon = <FileText size={18} />,
}: {
  children: ReactNode;
  right?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="hv-panel-title">
      <span>
        {icon}
        <span className="hv-micro">{children}</span>
      </span>
      {right}
    </div>
  );
}
export function PageHeader({
  eyebrow,
  title,
  subtitle,
  children,
}: {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  children?: ReactNode;
}) {
  return (
    <div className="hv-page-title">
      <div>
        <span className="hv-micro">
          {eyebrow || "Operational intelligence"}
        </span>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}
export function UnknownState({
  title,
  text,
  action,
}: {
  title: string;
  text: string;
  action?: ReactNode;
}) {
  return (
    <div className="hv-unknown">
      <span className="hv-unknown-icon">
        <CircleHelp size={22} />
      </span>
      <div>
        <h3>{title}</h3>
        <p>{text}</p>
        {action}
      </div>
    </div>
  );
}
export function FactValue({
  fact,
  unit,
  label,
}: {
  fact: Fact<unknown>;
  unit?: string;
  label?: string;
}) {
  return (
    <div className="hv-fact">
      {label && <small>{label}</small>}
      <strong>
        {String(fact.value ?? "Unavailable")}
        {unit && <em> {unit}</em>}
      </strong>
      <ProvenanceBadge fact={fact} />
    </div>
  );
}
export function EvidenceComparison({ evidence }: { evidence: Evidence }) {
  return (
    <div className="hv-comparison">
      {[
        ["Previous", evidence.previous],
        ["Observed", evidence.observed],
        ["Difference", evidence.previous === null ? "Unavailable" : evidence.observed - evidence.previous],
      ].map(([label, value]) => (
        <div key={label}>
          <small>{label}</small>
          <strong>{String(value ?? "Unavailable").replace("-", "−")}</strong>
          <small>tablets</small>
        </div>
      ))}
    </div>
  );
}
export function ReadinessRows({ compact = false }: { compact?: boolean }) {
  const { scenario } = useWorkspace();
  return (
    <div className="hv-readiness">
      {scenario.readiness
        .filter((r) => !compact || r.label !== "Policy")
        .map((r) => (
          <div key={r.label} title={r.detail}>
            <span>{r.label}</span>
            <span
              className={
                ["Partial", "Estimated"].includes(r.state)
                  ? "hv-amber-text"
                  : "hv-green-text"
              }
            >
              {["Partial", "Estimated"].includes(r.state) ? (
                <CircleHelp size={14} />
              ) : (
                <Check size={14} />
              )}{" "}
              {r.state}
            </span>
            {!compact && <small>{r.detail}</small>}
          </div>
        ))}
    </div>
  );
}
export function RecoveryTimeline({ compact = false }: { compact?: boolean }) {
  const { step, caseState } = useWorkspace();
  const indices = compact
    ? [0, 1, 3, 5, 9, 10]
    : recoverySteps.map((_, i) => i);
  return (
    <ol className={"hv-timeline " + (compact ? "compact" : "vertical")}>
      {indices.map((i) => (
        <li key={i} className={i < step ? "done" : i === step ? "current" : ""}>
          <span className="hv-timeline-node">
            {i < step ? <Check size={12} /> : null}
          </span>
          <div>
            <b>{recoverySteps[i]}</b>
            <small>
              {i < step
                ? "Recorded"
                : i === step
                  ? caseState.replace(/_/g, " ")
                  : "Awaiting action"}
            </small>
          </div>
        </li>
      ))}
    </ol>
  );
}
export function PriorityFacilityCard() {
  const { scenario, step } = useWorkspace();
  const f = scenario.facilities.find((f) => f.id === scenario.recipientId)!;
  const recovered = step >= 9;
  return (
    <Panel className="hv-priority">
      <div className="hv-row">
        <span className="hv-micro">Priority facility</span>
        <StateBadge tone={recovered ? "mint" : "coral"}>
          {recovered ? "Coverage restored" : "✦ At risk"}
        </StateBadge>
      </div>
      <h2>{f.short}</h2>
      <p className="hv-muted">Sundargarh, Odisha</p>
      <dl className="hv-facility-facts">
        <div>
          <dt>
            <Network size={16} />
            Commodity
          </dt>
          <dd>{scenario.commodity}</dd>
        </div>
        <div>
          <dt>
            <FileText size={16} />
            Usable stock
          </dt>
          <dd>
            {String(f.stock.value ?? "Unavailable")}{f.stock.value !== null ? " tablets" : ""}
            <ProvenanceBadge fact={f.stock} />
          </dd>
        </div>
        <div>
          <dt>
            <Clock3 size={16} />
            Continuity breach
          </dt>
          <dd className={recovered ? "" : "hv-coral-text"}>
            {recovered ? "Resolved" : scenario.breach.value}
            <ProvenanceBadge fact={scenario.breach} />
          </dd>
        </div>
        <div>
          <dt>
            <Package size={16} />
            Physical stockout
          </dt>
          <dd className={recovered ? "" : "hv-coral-text"}>
            {recovered ? "Resolved" : scenario.stockout.value}
          </dd>
        </div>
        <div>
          <dt>
            <FileText size={16} />
            Care impact
          </dt>
          <dd>
            {scenario.exposure.value}
            <ProvenanceBadge
              fact={scenario.exposure}
              label="Rehearsal estimate"
            />
          </dd>
        </div>
        <div>
          <dt>
            <ShieldCheck size={16} />
            Status
          </dt>
          <dd>
            {step >= 11
              ? "Care protected"
              : recovered
                ? "Awaiting care verification"
                : "Active recovery"}
            <small>
              {recovered
                ? "Supply and care verified separately"
                : "Under resolution"}
            </small>
          </dd>
        </div>
      </dl>
      <div className="hv-actions">
        <Link className="hv-button primary" to={"/app/cases/" + scenario.id}>
          Open case <ArrowRight size={15} />
        </Link>
        <Link className="hv-button" to={"/app/facilities/" + f.id}>
          View facility <ArrowRight size={15} />
        </Link>
      </div>
    </Panel>
  );
}
export function FacilityNode({
  facility,
  selected,
  recovered,
  onSelect,
}: {
  facility: Facility;
  selected: boolean;
  recovered: boolean;
  onSelect: (id: string) => void;
}) {
  const { scenario } = useWorkspace();
  const recipient = facility.id === scenario.recipientId,
    donor = facility.id === scenario.selectedId,
    invalid = facility.id === scenario.invalidatedId;
  const nid = "node-" + facility.id;
  const color =
    recipient && !recovered
      ? "#ff8b7b"
      : invalid
        ? "#d79272"
        : facility.risk === "Watch"
          ? "#f4c26a"
          : facility.risk === "Unknown"
            ? "#a4bab0"
            : "#8dd2ac";
  return (
    <g
      className={"hv-map-node " + (selected ? "selected" : "")}
      transform={"translate(" + facility.x + " " + facility.y + ")"}
      role="button"
      tabIndex={0}
      aria-label={
        facility.short +
        ", " +
        (recipient && recovered ? "Coverage restored" : facility.risk) +
        ", " +
        facility.currentness
      }
      onClick={() => onSelect(facility.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(facility.id);
        }
      }}
    >
      <title>
        {facility.name} · {facility.currentness} · {facility.risk}
      </title>
      <defs>
        <radialGradient id={nid + "sphere"} cx="30%" cy="22%" r="80%">
          <stop offset="0" stopColor="#ffffff" stopOpacity=".7" />
          <stop offset=".22" stopColor={color} />
          <stop offset=".7" stopColor={color} />
          <stop offset="1" stopColor={color} stopOpacity=".55" />
        </radialGradient>
        <radialGradient id={nid + "halo"}>
          <stop stopColor={color} stopOpacity=".28" />
          <stop offset=".5" stopColor={color} stopOpacity=".08" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </radialGradient>
      </defs>
      <circle
        r={recipient ? 76 : donor ? 52 : 38}
        fill={"url(#" + nid + "halo)"}
      />
      {(donor || invalid) && (
        <rect
          x={invalid ? -151 : 25}
          y="-28"
          width={invalid ? 136 : 151}
          height="57"
          rx="7"
          fill={invalid ? "#29362a" : "#103728"}
          stroke={invalid ? "#8f6650" : "#51775a"}
          strokeOpacity=".6"
          fillOpacity=".8"
        />
      )}
      <circle r={recipient ? 45 : donor ? 34 : 27} fill={color} opacity=".06" />
      <circle
        r={recipient ? 27 : donor ? 23 : 18}
        fill="none"
        stroke={color}
        opacity={recipient || donor ? ".65" : ".16"}
      />
      <circle
        r={recipient ? 16 : donor ? 17 : invalid ? 13 : 11}
        fill={
          invalid ? "#193c30" : donor ? "#367c55" : "url(#" + nid + "sphere)"
        }
        stroke={color}
        strokeWidth="2"
      />
      {invalid ? (
        <path d="m-5 -5 10 10 m0 -10 -10 10" stroke={color} strokeWidth="2" />
      ) : donor ? (
        <g stroke="#ddf8e5" fill="#25553e" strokeWidth="1.5">
          <path d="m0 -10 10 5 v11 l-10 5 -10 -5 v-11z M-10 -5 0 0 10 -5 M0 0 v11 M-5 -7 5 -2" />
        </g>
      ) : null}
      <text
        x={invalid ? -136 : recipient ? 40 : donor ? 39 : 24}
        y="-2"
        fill="#f5f9ef"
        fontSize={recipient ? 16 : 14}
        fontWeight={recipient || donor ? 600 : 400}
      >
        {facility.short}
      </text>
      {(recipient || donor || invalid) && (
        <text
          x={invalid ? -136 : recipient ? 40 : donor ? 39 : 24}
          y="18"
          fill={recipient && !recovered ? "#f8b29a" : "#9ebbab"}
          fontSize="12"
        >
          {recipient
            ? recovered
              ? "Coverage restored"
              : "Priority recipient"
            : donor
              ? "Donor · selected"
              : "Donor · invalidated"}
        </text>
      )}
    </g>
  );
}
export function NetworkCanvas({
  large = false,
  layer = "Risk",
  search = "",
  onInspect,
}: {
  large?: boolean;
  layer?: string;
  search?: string;
  onInspect?: (id: string) => void;
}) {
  const { scenario, step } = useWorkspace();
  const [selected, setSelected] = useState("");
  const [expanded, setExpanded] = useState(false);
  const uid = useId().replace(/:/g, "");
  const select = (id: string) => {
    setSelected(id);
    onInspect?.(id);
  };
  const active = scenario.facilities.find((f) => f.id === selected);
  return (
    <section
      className={
        "hv-network " + (large ? "large " : "") + (expanded ? "expanded" : "")
      }
      aria-label="Schematic district network"
    >
      <div className="hv-network-heading">
        <div>
          <span className="hv-micro">
            <i className="hv-dot" />
            District network
          </span>
          <p>Facilities, supply flows and risk status</p>
        </div>
        <span>
          {scenario.facilities.length} facilities <i /> Schematic view
        </span>
      </div>
      <svg
        viewBox="0 0 1040 460"
        className="hv-network-svg"
        aria-label="Sundargarh schematic facility graph"
      >
        <defs>
          <radialGradient id={uid + "glow"}>
            <stop stopColor="#488560" stopOpacity=".3" />
            <stop offset="1" stopColor="#163e2c" stopOpacity="0" />
          </radialGradient>
          <pattern
            id={uid + "grid"}
            width="26"
            height="26"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="1" cy="1" r=".7" fill="#acc8ad" opacity=".13" />
          </pattern>
          <marker
            id={uid + "arrow"}
            markerWidth="7"
            markerHeight="7"
            refX="6"
            refY="3"
            orient="auto"
          >
            <path d="m0 0 6 3 -6 3z" fill="#afd5ad" />
          </marker>
        </defs>
        <rect width="1040" height="460" fill={"url(#" + uid + "grid)"} />
        <ellipse
          cx="555"
          cy="232"
          rx="485"
          ry="245"
          fill={"url(#" + uid + "glow)"}
        />
        <g fill="none" stroke="#859465" strokeWidth=".9" opacity=".17">
          <path d="M49 271 57 256 52 247 64 231 62 219 76 212 80 196 71 188 65 171 84 166 91 154 114 157 128 143 129 132 146 118 162 116 178 125 197 129 203 114 219 116 230 99 249 105 264 97 277 102 286 83 300 69 316 79 338 76 357 86 367 65 380 69 387 41 401 47 414 41 435 58 450 48 463 45 475 59 487 78 508 64 522 72 544 63 556 51 576 48 588 62 608 61 622 80 636 75 644 62 655 63 664 80 686 84 702 73 721 78 733 64 745 82 761 86 773 104 790 101 804 89 822 90 839 105 842 119 857 126 878 118 893 134 910 134 918 153 934 178 924 190 926 209 907 223 926 225 940 240 958 247 945 260 948 281 923 298 938 318 938 333 917 339 910 355 891 356 875 375 848 392 831 380 815 386 797 378 778 395 769 391 750 416 730 407 715 414 699 401 680 417 668 409 643 423 626 405 614 410 599 391 580 402 565 397 551 414 532 404 517 411 501 397 480 409 470 402 458 420 440 408 421 417 401 401 387 414 372 405 350 416 336 396 321 401 311 381 291 391 276 382 257 387 242 365 226 350 207 365 192 358 172 370 155 346 142 349 128 335 110 344 91 336 82 316 64 304Z" />
          <path d="M197 129 203 161 191 176 223 197 212 224 233 243 215 277 237 305 226 350 M357 86 368 123 352 142 371 167 353 190 381 217 360 246 375 279 358 312 350 352 350 416 M487 78 499 110 474 131 492 156 476 182 496 209 478 239 502 259 487 289 509 316 492 341 511 368 501 397 M655 63 648 106 666 122 643 152 661 180 642 208 660 236 649 267 675 293 654 329 670 349 651 379 643 423 M822 90 804 129 821 148 798 177 817 196 801 225 815 252 796 275 810 304 798 336 797 378 M65 171 119 187 137 179 166 191 191 176 242 194 275 182 310 198 353 190 401 204 430 189 476 182 521 194 557 181 602 196 661 180 709 198 753 181 798 177 855 192 881 181 926 209 M49 271 102 263 141 279 181 262 215 277 272 264 310 281 360 246 412 262 451 249 478 239 537 251 580 242 619 259 649 267 711 252 750 269 815 252 873 273 901 264 948 281" />
        </g>
        <g fill="#91a986" fontSize="11" letterSpacing="3" opacity=".26">
          <text x="469" y="236">
            SUNDARGARH
          </text>
          <text x="133" y="190">
            TANGARPALI
          </text>
          <text x="790" y="243">
            HEMGIR
          </text>
        </g>
        <g
          fill="none"
          strokeWidth="1.3"
          markerEnd={"url(#" + uid + "arrow)"}
          className={layer === "Freshness" ? "hv-map-muted" : ""}
        >
          <path
            d={(() => {
              const from = scenario.facilities.find(f => f.id === scenario.selectedId);
              const to = scenario.facilities.find(f => f.id === scenario.recipientId);
              return from && to ? `M${from.x} ${from.y} Q${Math.round((from.x + to.x) / 2)} ${Math.min(from.y, to.y) + 100} ${to.x - 20} ${to.y - 11}` : "";
            })()}
            stroke="#a9d6ad"
            className="hv-route-active"
          />
          <path d="M145 265 Q285 379 520 120" stroke="#88b696" opacity=".4" />
          {scenario.invalidatedId && <path
            d={(() => {
              const from = scenario.facilities.find(f => f.id === scenario.invalidatedId);
              const to = scenario.facilities.find(f => f.id === scenario.recipientId);
              return from && to ? `M${from.x} ${from.y} Q${Math.round((from.x + to.x) / 2)} ${Math.round((from.y + to.y) / 2) + 25} ${to.x - 24} ${to.y}` : "";
            })()}
            stroke="#dcae84"
            strokeDasharray="5 6"
            opacity=".48"
          />}
          <path
            d="M821 130 Q740 172 683 259"
            stroke="#8cb997"
            strokeDasharray="3 4"
            opacity=".4"
          />
          <path d="M846 321 Q748 360 681 292" stroke="#8cb997" opacity=".4" />
          <path d="M318 348 Q478 430 642 297" stroke="#8cb997" opacity=".25" />
        </g>
        {scenario.facilities
          .filter(
            (f) =>
              !search || f.short.toLowerCase().includes(search.toLowerCase()),
          )
          .map((f) => (
            <FacilityNode
              key={f.id}
              facility={f}
              selected={selected === f.id}
              recovered={step >= 9}
              onSelect={select}
            />
          ))}
      </svg>
      {active && !onInspect && (
        <div className="hv-map-tooltip">
          <b>{active.short}</b>
          <span>
            {active.currentness} · {active.stock.value ?? "Unknown"}{" "}
            {active.stock.value !== null ? "tablets" : ""}
          </span>
          <Link to={"/app/facilities/" + active.id}>
            Inspect facility <ArrowUpRight size={13} />
          </Link>
          <button
            aria-label="Dismiss facility selection"
            onClick={() => setSelected("")}
          >
            <X size={13} />
          </button>
        </div>
      )}
      <div className="hv-network-footer">
        <div className="hv-legend">
          {[
            ["At risk", "coral"],
            ["Watch", "amber"],
            ["Stable", "mint"],
            ["Unknown", "unknown"],
          ].map(([label, c]) => (
            <span key={label}>
              <i className={"hv-dot " + c} />
              {label}
            </span>
          ))}
        </div>
        <div>
          <button
            title="Fit to district"
            onClick={() => {
              setSelected("");
              setExpanded(false);
            }}
          >
            <LocateFixed size={14} />
            <span>Fit to district</span>
          </button>
          <button
            aria-label={expanded ? "Exit expanded network" : "Expand network"}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
          </button>
        </div>
      </div>
      {layer !== "Risk" && (
        <span className="hv-map-layer">
          {layer === "Freshness"
            ? "Counts: rehearsal Sep 12 · routes: captured Sep 11"
            : layer === "Programme"
              ? "IFA Red · antenatal supplementation · aggregate estimates"
              : "Solid: candidate link · dashed: invalidated / held"}
        </span>
      )}
    </section>
  );
}
export function SignalCard({
  title,
  value,
  detail,
  href,
  tone,
  icon,
}: {
  title: string;
  value: string;
  detail: string;
  href: string;
  tone?: string;
  icon: ReactNode;
}) {
  return (
    <Link className={"hv-signal " + (tone || "")} to={href}>
      <span className="hv-signal-icon">{icon}</span>
      <div>
        <span>{title}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
      <ArrowRight size={17} />
    </Link>
  );
}
export const Icons = {
  risk: <TriangleAlert />,
  recovery: <Package />,
  evidence: <FileText />,
  network: <Network />,
};
