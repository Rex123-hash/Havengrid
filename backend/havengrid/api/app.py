"""FastAPI surface. Thin: every route delegates to HavenGridService.

    GET  /health
    GET  /api/demo/scenario                       one bundle for the frontend adapter
    GET  /api/districts/{district_id}/workspace    current typed workspace snapshot
    POST /api/demo/reset
    GET  /api/districts/{district_id}/network
    GET  /api/districts/{district_id}/forecast?horizon_days=
    GET  /api/facilities/{facility_id}
    GET  /api/facilities/{facility_id}/care-impact
    GET  /api/cases/{case_id}
    GET  /api/cases/{case_id}/interventions
    GET  /api/cases/{case_id}/audit
    POST /api/cases/{case_id}/evidence
    POST /api/cases/{case_id}/evidence/{evidence_id}/confirm
    POST /api/cases/{case_id}/evidence/{evidence_id}/reject
    POST /api/cases/{case_id}/advance                {action, actor?, observed_quantity?, observed_batch_ids?, command_id?}
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .. import __version__
from ..bootstrap import Bootstrapped, bootstrap
from ..domain.enums import CaseAction, CaseState
from ..domain.errors import CommandNotAuthorized, DomainError, IllegalTransition, InvariantViolation, NotFound, VerificationFailed
from ..service import HavenGridService
from ..settings import Settings, validate
from ..settings import HavenGridMode
from ..profiles import sundargarh_profile
from ..domain.enums import FacilityInventoryStatus, ReadinessStatus
from ..domain.models import DistrictReadiness
from ..kernel.state_machine import legal_actions
from . import mappers as M
from . import schemas as S

STATUS = {NotFound: 404, IllegalTransition: 409, InvariantViolation: 422, VerificationFailed: 409, CommandNotAuthorized: 403, DomainError: 400}


def create_app(service: HavenGridService | None = None, settings: Settings | None = None) -> FastAPI:
    """`service` short-circuits bootstrap (tests). Otherwise Settings decide, and a
    forbidden synthetic configuration raises EnvironmentIntegrityError here —
    the process must not start."""
    cfg = settings or Settings.from_env()
    validate(cfg)
    if service is not None:
        service.mode = cfg.mode
        boot = Bootstrapped(settings=cfg, service=service, source_id="injected", source_origin="injected", degraded_reason=None)
    else:
        boot = bootstrap(cfg)
    svc = boot.service  # None when degraded
    app = FastAPI(title=f"HAVEN GRID backend — {cfg.env.value} — source: {boot.source_id}", version=__version__)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.state.service = svc
    app.state.boot = boot

    @app.middleware("http")
    async def _degraded_guard(request: Request, call_next):
        # An unavailable data source answers honestly on every data route. Nothing is invented.
        if boot.degraded and request.url.path.startswith("/api/"):
            return JSONResponse(status_code=503, content=S.ErrorOut(
                code="data_source_unavailable",
                message="No operational data source is available in this environment; synthetic fallback is forbidden.",
                detail={"environment": cfg.env.value, "source": boot.source_id, "reason": boot.degraded_reason or ""},
            ).model_dump(mode="json"))
        if cfg.mode is HavenGridMode.OPERATIONAL and request.url.path.startswith("/api/") and request.method not in {"GET", "HEAD", "OPTIONS"}:
            # Demo reset/replay is never an operational capability, even when
            # an explicit command capability is supplied.
            if request.url.path.startswith("/api/demo/"):
                return JSONResponse(status_code=409, content=S.ErrorOut(
                    code="operational_read_only",
                    message="demo reset/replay endpoints do not exist in operational mode",
                    detail={"mode": cfg.mode.value},
                ).model_dump(mode="json"))
            capability = request.headers.get("X-HavenGrid-Command-Capability")
            if capability != svc.command_authorizer.capability:
                return JSONResponse(status_code=403, content=S.ErrorOut(
                    code="command_not_authorized",
                    message="explicit operational commands require the temporary actor capability",
                    detail={"mode": cfg.mode.value},
                ).model_dump(mode="json"))
        return await call_next(request)

    def origin_out() -> S.DataOriginOut:
        origins = svc.data_origins() if svc else []
        return S.DataOriginOut(source_id=boot.source_id, origins=origins, synthetic=bool(origins) and origins == ["synthetic_test"], environment=cfg.env.value)

    @app.get("/api/districts/{district_id}/profile", response_model=S.DistrictProfileOut)
    def district_profile(district_id: str) -> S.DistrictProfileOut:
        district_or_404(district_id)
        profile = repo().state().district_profile
        if profile is None:
            profile = sundargarh_profile()
        return M.district_profile(profile)

    @app.get("/api/districts/{district_id}/stock-signals", response_model=list[S.DistrictCommodityStockSignalOut])
    def stock_signals(district_id: str) -> list[S.DistrictCommodityStockSignalOut]:
        district_or_404(district_id)
        return [M.stock_signal(x) for x in repo().state().district_stock_signals.values() if x.district_id == district_id]

    @app.get("/api/districts/{district_id}/official-facilities", response_model=list[S.FacilityOut])
    def official_facilities(district_id: str) -> list[S.FacilityOut]:
        district_or_404(district_id)
        return [M.facility(x) for x in repo().state().facilities.values()]

    @app.get("/api/districts/{district_id}/readiness", response_model=S.DistrictReadinessOut)
    def readiness(district_id: str) -> S.DistrictReadinessOut:
        district_or_404(district_id)
        st = repo().state()
        readiness_state = st.readiness or DistrictReadiness(
            district_id=district_id,
            facility_roster=ReadinessStatus.READY if st.facilities else ReadinessStatus.UNKNOWN,
            programme_activity=ReadinessStatus.UNKNOWN,
            district_stock_context=ReadinessStatus.READY if st.district_stock_signals else ReadinessStatus.UNKNOWN,
            facility_inventory=ReadinessStatus.UNKNOWN,
            routes=ReadinessStatus.UNKNOWN,
            care_obligations=ReadinessStatus.UNKNOWN,
            policy=ReadinessStatus.READY,
            reasons=("No district readiness assessment was supplied by this source.",),
        )
        return M.readiness(readiness_state)

    @app.get("/api/districts/{district_id}/programme-activity", response_model=list[S.ProgrammeActivityOut])
    def programme_activity(district_id: str) -> list[S.ProgrammeActivityOut]:
        district_or_404(district_id)
        return [M.programme_activity(x) for x in repo().state().programme_activity.values() if x.district_id == district_id]

    @app.get("/api/districts/{district_id}/route-observations", response_model=list[S.RouteObservationOut])
    def route_observations(district_id: str) -> list[S.RouteObservationOut]:
        if district_id != repo().state().district.id:
            raise HTTPException(status_code=404, detail=f"district route observations '{district_id}' not configured")
        return [M.route_observation(x) for x in repo().state().route_observations.values()]

    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        code = next((c for t, c in STATUS.items() if isinstance(exc, t)), 400)
        return JSONResponse(status_code=code, content=S.ErrorOut(code=exc.code, message=exc.message, detail=exc.detail).model_dump(mode="json"))

    def repo():
        return svc.repo

    def active_case():
        cases = tuple(repo().state().cases.values())
        if len(cases) != 1:
            raise InvariantViolation("the active scenario must contain exactly one case")
        return cases[0]

    def active_item_id() -> str:
        return active_case().item_id

    def district_or_404(district_id: str):
        d = repo().state().district
        if d.id != district_id:
            raise NotFound(f"district '{district_id}' not found")
        return d

    def inventory_status(facility_id: str, item_id: str) -> FacilityInventoryStatus:
        canonical = repo().canonical_inventory(facility_id, item_id)
        if canonical is None:
            return FacilityInventoryStatus.INVENTORY_REQUIRED
        age = M.days_since_count(repo(), facility_id, item_id)
        return FacilityInventoryStatus.SOURCE_STALE if age is not None and age > 30 else FacilityInventoryStatus.AVAILABLE

    @app.get("/health")
    def health() -> dict:
        base = {"version": __version__, "environment": cfg.env.value, "mode": cfg.mode.value, "data_source": boot.source_id, "source_origin": boot.source_origin}
        if boot.degraded:
            return {"status": "degraded", "reason": boot.degraded_reason, **base}
        o = origin_out()
        return {"status": "ok", "synthetic": o.synthetic, "origins": o.origins, "clock_now": svc.now().isoformat(), **base}

    @app.get("/api/demo/scenario", response_model=S.ScenarioBundle)
    def scenario() -> S.ScenarioBundle:
        st = repo().state()
        d = st.district
        case = active_case()
        item_id = case.item_id
        forecasts = svc.network_forecast(item_id)
        impacts = svc.network_care_impact(item_id)
        focus = case.recipient_id
        plan = svc.current_plan(case.id)
        prev = [M.plan(repo().plan(pid), repo()) for pid in case.previous_plan_ids]
        lineage_ids = {focus, *(c.donor_id for p in ([plan] if plan else []) for c in p.candidates)}
        o = origin_out()
        return S.ScenarioBundle(
            synthetic=o.synthetic, data_origin=o,
            district=M.district(d), item=M.item(repo().item(item_id)),
            facilities=[M.facility(f) for f in st.facilities.values()], links=[M.link(l) for l in st.links],
            forecasts={fid: M.forecast(a, d) for fid, a in forecasts.items()},
            care_impacts={fid: M.care_impact(c) for fid, c in impacts.items()},
            focus_facility_id=focus,
            focus_care_events=[M.care_event(e, d, impacts[focus]) for e in sorted(repo().care_events_for(focus, item_id), key=lambda e: (e.scheduled_at, e.id))],
            case=M.case(case), plan=M.plan(plan, repo()) if plan else None, previous_plans=prev,
            evidence=[M.evidence(repo().evidence(e)) for e in case.evidence_ids],
            inventory_lineage={fid: [M.inventory(r) for r in repo().inventory_lineage(fid, item_id)] for fid in sorted(lineage_ids)},
            verifications=[M.verification(st.verifications[v]) for v in case.verification_ids],
            reconciliations=[M.reconciliation(st.reconciliations[r]) for r in case.reconciliation_ids],
            inventory_freshness={fid: M.days_since_count(repo(), fid, item_id) for fid in st.facilities},
            clock_now=svc.now(), route_observations=[M.route_observation(x) for x in st.route_observations.values()],
        )

    @app.post("/api/demo/reset", response_model=S.CaseOut)
    def reset() -> S.CaseOut:
        svc.reset()
        return M.case(active_case())

    @app.get("/api/districts/{district_id}/network", response_model=S.NetworkOut)
    def network(district_id: str) -> S.NetworkOut:
        d = district_or_404(district_id)
        st = repo().state()
        o = origin_out()
        item_id = active_item_id()
        return S.NetworkOut(district=M.district(d), item=M.item(repo().item(item_id)),
                            facilities=[M.facility(f) for f in st.facilities.values()], links=[M.link(l) for l in st.links],
                            forecasts={fid: M.forecast(a, d) for fid, a in svc.network_forecast(item_id).items()},
                            care_impacts={fid: M.care_impact(c) for fid, c in svc.network_care_impact(item_id).items()},
                            data_origin=o, synthetic=o.synthetic)

    @app.get("/api/districts/{district_id}/workspace", response_model=S.WorkspaceSnapshotOut)
    def workspace(district_id: str) -> S.WorkspaceSnapshotOut:
        district = district_or_404(district_id)
        st = repo().state()
        case = active_case()
        item_id = case.item_id
        forecasts = svc.network_forecast(item_id)
        impacts = svc.network_care_impact(item_id)
        plan = svc.current_plan(case.id)
        obligations = [x for x in st.care_obligations.values() if x.facility_id == case.recipient_id and x.item_id == item_id]
        limitations = [*st.readiness.reasons] if st.readiness else []
        limitations.extend(x.uncertainty_note for x in obligations if x.uncertainty_note)
        if any(x.facility_denominator_status == "UNKNOWN" for x in obligations):
            limitations.append("Facility care denominator is UNKNOWN; aggregate attendance is a controlled rehearsal estimate.")
        if repo().item(item_id).physical_dispatch_unit == "UNKNOWN":
            limitations.append("Physical dispatch packaging is UNKNOWN.")
        if any(repo().canonical_inventory(f.id, item_id) is None for f in st.facilities.values()):
            limitations.append("Some facilities have no canonical inventory; their forecasts and care impact are unavailable.")
        last_reconciliation = st.reconciliations[case.reconciliation_ids[-1]] if case.reconciliation_ids else None
        return S.WorkspaceSnapshotOut(
            metadata=S.WorkspaceMetadataOut(district=M.district(district), mode=cfg.mode.value,
                                            designation="controlled_rehearsal" if boot.source_id == "rehearsal/sundargarh-ifa-red" else boot.source_id,
                                            commodity=M.item(repo().item(item_id)), clock_now=svc.now(), data_origin=origin_out()),
            network=S.WorkspaceNetworkOut(
                facilities=[S.WorkspaceFacilityOut(facility=M.facility(f), inventory_status=inventory_status(f.id, item_id),
                                                   canonical_inventory=M.inventory(c) if (c := repo().canonical_inventory(f.id, item_id)) else None,
                                                   forecast=M.forecast(forecasts[f.id], district), care_impact=M.care_impact(impacts[f.id]),
                                                   days_since_physical_count=M.days_since_count(repo(), f.id, item_id)) for f in st.facilities.values()],
                links=[M.link(x) for x in st.links],
                route_observations=[M.route_observation(x) for x in st.route_observations.values()]),
            active_case=M.case(case), recipient_forecast=M.forecast(forecasts[case.recipient_id], district),
            recipient_care_impact=M.care_impact(impacts[case.recipient_id]),
            current_plan=M.plan(plan, repo()) if plan else None,
            previous_plans=[M.plan(repo().plan(pid), repo()) for pid in case.previous_plan_ids],
            evidence=[S.WorkspaceEvidenceOut(evidence=M.evidence(ev), current_canonical_quantity=c.quantity if c else None,
                                             current_inventory_status=inventory_status(ev.facility_id, item_id))
                      for eid in case.evidence_ids for ev in [repo().evidence(eid)]
                      for c in [repo().canonical_inventory(ev.facility_id, item_id)]],
            recovery=S.WorkspaceRecoveryOut(state=case.state, completed_audit_actions=[x.action for x in repo().audit_for(case.id)],
                                            domain_legal_actions=legal_actions(case.state),
                                            coverage_status=last_reconciliation.coverage_status if last_reconciliation else "not_verified",
                                            care_protected=case.state in (CaseState.CARE_PROTECTED, CaseState.CLOSED),
                                            care_delivery=[M.care_delivery(st.care_delivery[x]) for x in case.care_delivery_ids]),
            intelligence=S.WorkspaceIntelligenceOut(
                profile=district_profile(district_id), readiness=readiness(district_id), stock_signals=stock_signals(district_id),
                programme_activity=programme_activity(district_id),
                care_obligations=[S.CareObligationBasisOut(id=x.id, facility_id=x.facility_id,
                                                           expected_attendance=x.expected_attendance,
                                                           estimated_population_min=x.estimated_population_min,
                                                           estimated_population_max=x.estimated_population_max,
                                                           evidence_grade=x.evidence_grade, numeric_basis_origin=x.numeric_basis_origin,
                                                           public_programme_basis=x.public_programme_basis,
                                                           facility_denominator_status=x.facility_denominator_status,
                                                           basis=x.basis, uncertainty_note=x.uncertainty_note,
                                                           provenance=M.provenance(x.provenance)) for x in obligations]),
            limitations=limitations,
        )

    @app.get("/api/districts/{district_id}/forecast", response_model=dict[str, S.ForecastOut])
    def district_forecast(district_id: str, horizon_days: int = Query(default=30, ge=1, le=30)) -> dict[str, S.ForecastOut]:
        d = district_or_404(district_id)
        out = {}
        for fid, a in svc.network_forecast(active_item_id()).items():
            trimmed = a.model_copy(update={"projection": tuple(r for r in a.projection if r.day <= horizon_days),
                                           "coverage_breach_day": a.coverage_breach_day if (a.coverage_breach_day is not None and a.coverage_breach_day <= horizon_days) else None})
            out[fid] = M.forecast(trimmed, d)
        return out

    @app.get("/api/facilities/{facility_id}", response_model=S.FacilityDetailOut)
    def facility(facility_id: str) -> S.FacilityDetailOut:
        f = repo().facility(facility_id)
        d = repo().state().district
        item_id = active_item_id()
        a = svc.forecast(facility_id, item_id)
        impact = svc.care_impact(facility_id, item_id)
        canonical = repo().canonical_inventory(facility_id, item_id)
        days_since = M.days_since_count(repo(), facility_id, item_id)
        return S.FacilityDetailOut(
            facility=M.facility(f), canonical_inventory=M.inventory(canonical) if canonical else None,
            inventory_lineage=[M.inventory(r) for r in repo().inventory_lineage(facility_id, item_id)],
            forecast=M.forecast(a, d), care_impact=M.care_impact(impact),
            care_events=[M.care_event(e, d, impact) for e in sorted(repo().care_events_for(facility_id, item_id), key=lambda e: (e.scheduled_at, e.id))],
            days_since_physical_count=days_since,
            inventory_status=inventory_status(facility_id, item_id),
        )

    @app.get("/api/facilities/{facility_id}/care-impact", response_model=S.CareImpactOut)
    def facility_care_impact(facility_id: str) -> S.CareImpactOut:
        repo().facility(facility_id)
        return M.care_impact(svc.care_impact(facility_id, active_item_id()))

    @app.get("/api/cases/{case_id}", response_model=S.CaseOut)
    def get_case(case_id: str) -> S.CaseOut:
        return M.case(repo().case(case_id))

    @app.get("/api/cases/{case_id}/interventions", response_model=list[S.PlanOut])
    def interventions(case_id: str) -> list[S.PlanOut]:
        c = repo().case(case_id)
        ids = [*c.previous_plan_ids, *([c.plan_id] if c.plan_id else [])]
        return [M.plan(repo().plan(pid), repo()) for pid in ids]

    @app.get("/api/cases/{case_id}/audit", response_model=list[S.AuditOut])
    def audit(case_id: str) -> list[S.AuditOut]:
        repo().case(case_id)
        return [M.audit(a) for a in repo().audit_for(case_id)]

    @app.get("/api/cases/{case_id}/care-delivery", response_model=list[S.CareDeliveryOut])
    def care_delivery(case_id: str) -> list[S.CareDeliveryOut]:
        c = repo().case(case_id)
        return [M.care_delivery(repo().state().care_delivery[x]) for x in c.care_delivery_ids]

    @app.post("/api/cases/{case_id}/care-delivery", response_model=S.CareDeliveryOut, status_code=201)
    def submit_care_delivery(case_id: str, body: S.CareDeliveryIn) -> S.CareDeliveryOut:
        _, record = svc.record_care_delivery(case_id, exposure_kind=body.exposure_kind, exposure_id=body.exposure_id,
                                             outcome=body.outcome, verified_by=body.verified_by, source_ref=body.source_ref,
                                             note=body.note, command_id=body.command_id)
        return M.care_delivery(record)

    @app.post("/api/cases/{case_id}/evidence", response_model=S.EvidenceOut, status_code=201)
    def submit_evidence(case_id: str, body: S.EvidenceIn) -> S.EvidenceOut:
        _, ev = svc.submit_evidence(case_id, facility_id=body.facility_id, observed_quantity=body.observed_quantity,
                                    confidence=body.confidence, captured_via=body.captured_via, evidence_class=body.evidence_class,
                                    command_id=body.command_id)
        return M.evidence(ev)

    @app.post("/api/cases/{case_id}/evidence/{evidence_id}/confirm", response_model=S.CaseOut)
    def confirm(case_id: str, evidence_id: str, body: S.DecisionIn) -> S.CaseOut:
        return M.case(svc.confirm_evidence(case_id, evidence_id, confirmed_by=body.actor, note=body.note, command_id=body.command_id))

    @app.post("/api/cases/{case_id}/evidence/{evidence_id}/reject", response_model=S.CaseOut)
    def reject(case_id: str, evidence_id: str, body: S.DecisionIn) -> S.CaseOut:
        return M.case(svc.reject_evidence(case_id, evidence_id, rejected_by=body.actor, note=body.note, command_id=body.command_id))

    @app.post("/api/cases/{case_id}/advance", response_model=S.CaseOut)
    def advance(case_id: str, body: S.AdvanceIn, request: Request) -> S.CaseOut:
        if body.action in (CaseAction.SUBMIT_EVIDENCE, CaseAction.CONFIRM_EVIDENCE, CaseAction.REJECT_EVIDENCE):
            raise HTTPException(status_code=422, detail=f"'{body.action.value}' has a dedicated endpoint under /evidence")
        payload = {"actor": body.actor, "observed_quantity": body.observed_quantity, "observed_batch_ids": body.observed_batch_ids}
        capability = request.headers.get("X-HavenGrid-Command-Capability")
        return M.case(svc.advance(case_id, body.action, payload, command_id=body.command_id, capability=capability))

    return app


app = create_app()
