"""Google Routes adapter with an explicit unavailable state.

The adapter never fabricates distance or duration.  A missing credential,
provider error, malformed response, or absent route produces a persisted
``ROUTE_UNAVAILABLE`` observation with the request hash and retrieval time.
Successful responses can be converted into the kernel's ``Route`` fact.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..domain.enums import Origin, ProvenanceStatus, RouteObservationStatus, SourceType
from ..domain.models import Coordinate, Provenance, Route, RouteObservation

ROUTES_ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"


def _canonical_request(origin: Coordinate, destination: Coordinate, *, travel_mode: str, routing_preference: str) -> dict[str, Any]:
    return {
        "origin": {"location": {"latLng": {"latitude": str(origin.latitude), "longitude": str(origin.longitude)}}},
        "destination": {"location": {"latLng": {"latitude": str(destination.latitude), "longitude": str(destination.longitude)}}},
        "travelMode": travel_mode,
        "routingPreference": routing_preference,
    }


def request_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


class GoogleRoutesAdapter:
    provider = "google_routes"

    def __init__(self, *, api_key: str | None = None, access_token: str | None = None,
                 endpoint: str = ROUTES_ENDPOINT,
                 transport: Callable[[str, dict[str, str], bytes], tuple[int, bytes]] | None = None) -> None:
        self.api_key = api_key or os.getenv("GOOGLE_ROUTES_API_KEY")
        self.access_token = access_token or os.getenv("GOOGLE_ROUTES_ACCESS_TOKEN")
        self.endpoint = endpoint
        self.transport = transport

    def _call(self, headers: dict[str, str], body: bytes) -> tuple[int, bytes]:
        if self.transport is not None:
            return self.transport(self.endpoint, headers, body)
        try:
            with urlopen(Request(self.endpoint, data=body, headers=headers, method="POST"), timeout=20) as response:
                return int(response.status), response.read()
        except HTTPError as e:
            return int(e.code), e.read()
        except (URLError, TimeoutError, OSError) as e:
            return 0, str(e).encode("utf-8")

    def compute_route(self, *, from_id: str, to_id: str, origin: Coordinate, destination: Coordinate,
                      retrieved_at: datetime | None = None, travel_mode: str = "DRIVE",
                      routing_preference: str = "TRAFFIC_UNAWARE") -> RouteObservation:
        retrieved = retrieved_at or datetime.now(timezone.utc)
        payload = _canonical_request(origin, destination, travel_mode=travel_mode, routing_preference=routing_preference)
        digest = request_hash(payload)
        headers = {"Content-Type": "application/json", "X-Goog-FieldMask": "routes.distanceMeters,routes.duration,routes.staticDuration"}
        if self.api_key:
            headers["X-Goog-Api-Key"] = self.api_key
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        if not self.api_key and not self.access_token:
            return self._unavailable(from_id, to_id, digest, retrieved, "missing Google Routes credential", endpoint=self.endpoint)
        status, raw = self._call(headers, json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            data = {}
        routes = data.get("routes") if isinstance(data, dict) else None
        if status != 200 or not isinstance(routes, list) or not routes:
            detail = data.get("error", {}).get("message") if isinstance(data, dict) and isinstance(data.get("error"), dict) else raw.decode("utf-8", errors="replace")[:300]
            return self._unavailable(from_id, to_id, digest, retrieved, detail or f"HTTP {status}", endpoint=self.endpoint)
        row = routes[0]
        try:
            distance = Decimal(str(row["distanceMeters"])) / Decimal("1000")
            duration = self._duration_hours(row["duration"])
            static_duration = self._duration_hours(row.get("staticDuration", row["duration"]))
        except (KeyError, TypeError, ValueError) as e:
            return self._unavailable(from_id, to_id, digest, retrieved, f"malformed Google Routes response: {e}", endpoint=self.endpoint)
        prov = Provenance(source_type=SourceType.ROUTE_ESTIMATE, status=ProvenanceStatus.OBSERVED, observed_at=retrieved,
                          source_ref=f"{self.endpoint}#{digest}", origin=Origin.LIVE_EXTERNAL_API,
                          publisher="Google Routes API", retrieved_at=retrieved, geographic_granularity="route",
                          source_hash=digest, note="Compute Routes response; traffic-unaware static estimate.")
        return RouteObservation(id=f"route-{from_id}-{to_id}-{digest[:10]}", from_id=from_id, to_id=to_id,
                                distance_km=distance, duration_hours=duration, static_duration_hours=static_duration,
                                retrieved_at=retrieved, provider=self.provider, request_hash=digest,
                                status=RouteObservationStatus.OK, provenance=prov)

    @staticmethod
    def _duration_hours(value: Any) -> Decimal:
        text = str(value)
        if not text.endswith("s"):
            raise ValueError("duration must use seconds suffix")
        return Decimal(text[:-1]) / Decimal("3600")

    @staticmethod
    def _unavailable(from_id: str, to_id: str, digest: str, retrieved: datetime, error: str, *, endpoint: str = ROUTES_ENDPOINT) -> RouteObservation:
        prov = Provenance(source_type=SourceType.ROUTE_ESTIMATE, status=ProvenanceStatus.OBSERVED, observed_at=retrieved,
                          source_ref=f"{endpoint}#{digest}", origin=Origin.LIVE_EXTERNAL_API,
                          publisher="Google Routes API", retrieved_at=retrieved, geographic_granularity="route",
                          source_hash=digest, note="No route value admitted; ROUTE_UNAVAILABLE.")
        return RouteObservation(id=f"route-{from_id}-{to_id}-{digest[:10]}", from_id=from_id, to_id=to_id,
                                retrieved_at=retrieved, provider="google_routes", request_hash=digest,
                                status=RouteObservationStatus.ROUTE_UNAVAILABLE, provenance=prov, error=error)

    def as_route(self, observation: RouteObservation) -> Route | None:
        if observation.status is not RouteObservationStatus.OK or observation.distance_km is None or observation.duration_hours is None:
            return None
        return Route(from_id=observation.from_id, to_id=observation.to_id, distance_km=observation.distance_km,
                     transit_hours=observation.duration_hours, static_transit_hours=observation.static_duration_hours,
                     provider=observation.provider, request_hash=observation.request_hash, status=observation.status,
                     retrieved_at=observation.retrieved_at, provenance=observation.provenance)


def compute_route_matrix(adapter: GoogleRoutesAdapter, *, recipient: tuple[str, Coordinate], donors: Iterable[tuple[str, Coordinate]],
                         retrieved_at: datetime | None = None) -> tuple[RouteObservation, ...]:
    to_id, destination = recipient
    return tuple(adapter.compute_route(from_id=from_id, to_id=to_id, origin=origin, destination=destination, retrieved_at=retrieved_at)
                 for from_id, origin in donors)


def load_captured_route_matrix(path: str | os.PathLike[str]) -> tuple[RouteObservation, ...]:
    """Replay a captured Google response without changing its provenance.

    Captures are fixtures for a rehearsal, not a fallback for a live failure.
    The response remains labelled ``LIVE_EXTERNAL_API`` and keeps its original
    retrieval timestamp and request hash.
    """
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    out: list[RouteObservation] = []
    for row in payload.get("routes", []):
        origin = Coordinate(latitude=Decimal(str(row["origin"]["latitude"])), longitude=Decimal(str(row["origin"]["longitude"])),
                            source_ref=f"capture:{row['from_id']}:origin", source="captured_coordinate")
        destination = Coordinate(latitude=Decimal(str(row["destination"]["latitude"])), longitude=Decimal(str(row["destination"]["longitude"])),
                                 source_ref=f"capture:{row['to_id']}:destination", source="captured_coordinate")
        response = row.get("response")
        raw = json.dumps(response or {}, separators=(",", ":")).encode("utf-8")
        adapter = GoogleRoutesAdapter(api_key="captured-response", transport=lambda _url, _headers, _body, raw=raw: (200, raw) if response else (503, raw))
        retrieved = datetime.fromisoformat(str(row["retrieved_at"]).replace("Z", "+00:00"))
        out.append(adapter.compute_route(from_id=str(row["from_id"]), to_id=str(row["to_id"]), origin=origin, destination=destination, retrieved_at=retrieved))
    return tuple(out)
