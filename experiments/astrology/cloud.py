"""Isolated AstroAPI.cloud client and chart comparison helpers.

This prototype deliberately fixes the calculation conventions used by the
experiment.  It does not read credentials from disk or the environment, and it
does not retry requests (a caller may decide how to handle quota responses).
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
from time import monotonic
from typing import Any, Mapping

import requests


ENDPOINT = "https://api.astroapi.cloud/api/calc/natal"
REQUEST_TIMEOUT_SECONDS = (3.05, 15.0)
PLANET_IDS = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
)
DEFAULT_TOLERANCE_DEGREES = 0.01

_USAGE_HEADERS = (
    "X-RateLimit-Limit",
    "X-RateLimit-Remaining",
    "X-RateLimit-Reset",
    "Retry-After",
    "X-Quota-Limit",
    "X-Quota-Remaining",
    "X-Quota-Reset",
    "X-Api-Version",
)


class AstroApiError(RuntimeError):
    """A safe client error that never includes the API key or response body."""


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _validate_inputs(
    instant: datetime, latitude: float, longitude: float, api_key: str
) -> tuple[datetime, float, float, str]:
    if not isinstance(instant, datetime) or instant.tzinfo is None:
        raise ValueError("instant must be a timezone-aware datetime")
    if instant.utcoffset() is None:
        raise ValueError("instant must have a valid UTC offset")

    latitude_value = _number(latitude)
    longitude_value = _number(longitude)
    if latitude_value is None or not -90.0 <= latitude_value <= 90.0:
        raise ValueError("latitude must be a finite number from -90 through 90")
    if longitude_value is None or not -180.0 <= longitude_value <= 180.0:
        raise ValueError("longitude must be a finite number from -180 through 180")
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("api_key must be a non-empty string")
    return instant.astimezone(timezone.utc), latitude_value, longitude_value, api_key


def _usage_from_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return only telemetry the provider actually supplied."""
    usage: dict[str, str] = {}
    for name in _USAGE_HEADERS:
        value = headers.get(name)
        if value is not None:
            usage[name] = value
    return usage


def _validated_data(raw: Any) -> Mapping[str, Any]:
    if not isinstance(raw, Mapping) or not isinstance(raw.get("data"), Mapping):
        raise AstroApiError("AstroAPI returned a malformed success response")
    data = raw["data"]
    points = data.get("points")
    if not isinstance(points, Mapping):
        raise AstroApiError("AstroAPI success response has no valid planet data")

    invalid: list[str] = []
    for planet_id in PLANET_IDS:
        point = points.get(planet_id)
        if not isinstance(point, Mapping):
            invalid.append(planet_id)
            continue
        longitude = _number(point.get("longitude"))
        if longitude is None or not 0.0 <= longitude < 360.0:
            invalid.append(planet_id)
            continue
        speed = point.get("speedLongitude")
        if speed is not None and _number(speed) is None:
            invalid.append(planet_id)
            continue
        retrograde = point.get("retrograde")
        if retrograde is not None and not isinstance(retrograde, bool):
            invalid.append(planet_id)
    if invalid:
        names = ", ".join(invalid)
        raise AstroApiError(f"AstroAPI success response has invalid planet data: {names}")
    return data


def fetch_chart(
    instant: datetime,
    latitude: float,
    longitude: float,
    api_key: str,
) -> dict[str, Any]:
    """Fetch one fixed-convention chart from AstroAPI.cloud.

    The returned ``request`` contains only the JSON payload, never credentials.
    Network, HTTP, JSON, and schema failures raise :class:`AstroApiError` with a
    deliberately bounded message that excludes response bodies.
    """
    utc_instant, latitude_value, longitude_value, key = _validate_inputs(
        instant, latitude, longitude, api_key
    )
    if utc_instant.second or utc_instant.microsecond:
        raise ValueError("AstroAPI accepts minute precision only; align both comparison charts explicitly")
    payload = {
        "dateTime": utc_instant.strftime("%Y-%m-%dT%H:%M"),
        "location": {
            "latitude": latitude_value,
            "longitude": longitude_value,
            "timezone": "UTC",
        },
        "houseSystem": "whole",
        "moonCenter": "geocentric",
        "includeText": False,
        "includeReadableEntities": False,
        "points": list(PLANET_IDS),
    }

    started = monotonic()
    try:
        response = requests.post(
            ENDPOINT,
            headers={"X-Api-Key": key, "Content-Type": "application/json"},
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        raise AstroApiError(f"AstroAPI request failed ({type(exc).__name__})") from None
    duration_ms = round((monotonic() - started) * 1000.0, 3)

    if not 200 <= response.status_code < 300:
        raise AstroApiError(f"AstroAPI request failed with HTTP {response.status_code}")
    try:
        raw = response.json()
    except (ValueError, TypeError):
        raise AstroApiError("AstroAPI returned invalid JSON") from None
    _validated_data(raw)

    return {
        "request": payload,
        "response": raw,
        "duration_ms": duration_ms,
        "status": response.status_code,
        "usage": _usage_from_headers(response.headers),
    }


def _longitude(container: Any, key: str) -> float | None:
    if not isinstance(container, Mapping):
        return None
    item = container.get(key)
    if not isinstance(item, Mapping):
        return None
    value = _number(item.get("longitude"))
    return value if value is not None and 0.0 <= value < 360.0 else None


def _hosted_cusp_longitudes(chart: Mapping[str, Any]) -> list[float | None] | None:
    houses = chart.get("houses")
    cusps = houses.get("cusps") if isinstance(houses, Mapping) else None
    if not isinstance(cusps, (list, tuple)):
        return None
    result: list[float | None] = []
    for cusp in cusps:
        value = (
            _number(cusp.get("longitude"))
            if isinstance(cusp, Mapping)
            else _number(cusp)
        )
        result.append(value if value is not None and 0.0 <= value < 360.0 else None)
    return result


def _local_cusp_longitudes(chart: Mapping[str, Any]) -> list[float | None] | None:
    cusps = chart.get("whole_sign_cusps")
    if not isinstance(cusps, (list, tuple)):
        return None
    result: list[float | None] = []
    for cusp in cusps:
        value = _number(cusp.get("longitude")) if isinstance(cusp, Mapping) else None
        result.append(value if value is not None and 0.0 <= value < 360.0 else None)
    return result


def _angular_deviation(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)


def _speed_sign(speed: float) -> str:
    if speed < 0.0:
        return "negative"
    if speed > 0.0:
        return "positive"
    return "stationary"


def compare_chart(
    local_chart: Mapping[str, Any],
    hosted_result: Mapping[str, Any],
    tolerance_degrees: float = DEFAULT_TOLERANCE_DEGREES,
) -> dict[str, Any]:
    """Compare local and hosted longitudes, failing closed on missing fields.

    ``0.01`` degree is an exploratory consistency threshold for this prototype,
    not a claim of universal astrological correctness or provider accuracy.
    """
    tolerance = _number(tolerance_degrees)
    if tolerance is None or tolerance < 0.0 or tolerance > 180.0:
        raise ValueError("tolerance_degrees must be a finite number from 0 through 180")
    if not isinstance(local_chart, Mapping) or not isinstance(hosted_result, Mapping):
        raise ValueError("charts must be mappings")

    raw = hosted_result.get("response")
    try:
        hosted = _validated_data(raw)
    except AstroApiError as exc:
        return {
            "complete": False,
            "within_tolerance": False,
            "tolerance_degrees": tolerance,
            "missing": [str(exc)],
            "deviations": {"planets": {}, "angles": {}, "cusps": []},
        }

    deviations: dict[str, Any] = {"planets": {}, "angles": {}, "cusps": []}
    missing: list[str] = []

    local_points = local_chart.get("planets")
    hosted_points = hosted.get("points")
    for planet_id in PLANET_IDS:
        local_name = planet_id.capitalize()
        local_value = _longitude(local_points, local_name)
        hosted_value = _longitude(hosted_points, planet_id)
        local_point = (
            local_points.get(local_name) if isinstance(local_points, Mapping) else None
        )
        hosted_point = (
            hosted_points.get(planet_id)
            if isinstance(hosted_points, Mapping)
            else None
        )
        local_speed = (
            _number(local_point.get("speed_degrees_per_day"))
            if isinstance(local_point, Mapping)
            else None
        )
        hosted_speed = (
            _number(hosted_point.get("speedLongitude"))
            if isinstance(hosted_point, Mapping)
            else None
        )
        local_retrograde = (
            local_point.get("retrograde")
            if isinstance(local_point, Mapping)
            and isinstance(local_point.get("retrograde"), bool)
            else None
        )
        hosted_retrograde = (
            hosted_point.get("retrograde")
            if isinstance(hosted_point, Mapping)
            and isinstance(hosted_point.get("retrograde"), bool)
            else None
        )
        if local_value is None:
            missing.append(f"local.planets.{local_name}.longitude")
        if hosted_value is None:
            missing.append(f"hosted.data.points.{planet_id}.longitude")
        if local_speed is None:
            missing.append(f"local.planets.{local_name}.speed_degrees_per_day")
        if hosted_speed is None:
            missing.append(f"hosted.data.points.{planet_id}.speedLongitude")
        if local_retrograde is None:
            missing.append(f"local.planets.{local_name}.retrograde")
        if hosted_retrograde is None:
            missing.append(f"hosted.data.points.{planet_id}.retrograde")
        if (
            local_value is not None
            and hosted_value is not None
            and local_speed is not None
            and hosted_speed is not None
            and local_retrograde is not None
            and hosted_retrograde is not None
        ):
            delta = _angular_deviation(local_value, hosted_value)
            local_speed_sign = _speed_sign(local_speed)
            hosted_speed_sign = _speed_sign(hosted_speed)
            retrograde_match = local_retrograde == hosted_retrograde
            speed_sign_match = local_speed_sign == hosted_speed_sign
            deviations["planets"][planet_id] = {
                "local": local_value,
                "hosted": hosted_value,
                "deviation_degrees": delta,
                "local_speed_degrees_per_day": local_speed,
                "hosted_speed_degrees_per_day": hosted_speed,
                "speed_deviation_degrees_per_day": abs(local_speed - hosted_speed),
                "local_speed_sign": local_speed_sign,
                "hosted_speed_sign": hosted_speed_sign,
                "speed_sign_match": speed_sign_match,
                "local_retrograde": local_retrograde,
                "hosted_retrograde": hosted_retrograde,
                "retrograde_match": retrograde_match,
                "within_tolerance": (
                    delta <= tolerance and retrograde_match and speed_sign_match
                ),
            }

    hosted_angles = hosted.get("angles")
    for angle_id in ("ascendant", "midheaven"):
        local_value = _number(
            local_chart.get(angle_id, {}).get("longitude")
            if isinstance(local_chart.get(angle_id), Mapping)
            else None
        )
        if local_value is not None and not 0.0 <= local_value < 360.0:
            local_value = None
        hosted_value = _longitude(hosted_angles, angle_id)
        if local_value is None:
            missing.append(f"local.{angle_id}.longitude")
        if hosted_value is None:
            missing.append(f"hosted.data.angles.{angle_id}.longitude")
        if local_value is not None and hosted_value is not None:
            delta = _angular_deviation(local_value, hosted_value)
            deviations["angles"][angle_id] = {
                "local": local_value,
                "hosted": hosted_value,
                "deviation_degrees": delta,
                "within_tolerance": delta <= tolerance,
            }

    local_cusps = _local_cusp_longitudes(local_chart)
    hosted_cusps = _hosted_cusp_longitudes(hosted)
    if local_cusps is None or len(local_cusps) != 12:
        missing.append("local.whole_sign_cusps[12]")
    if hosted_cusps is None or len(hosted_cusps) != 12:
        missing.append("hosted.data.houses.cusps[12]")
    if local_cusps is not None and hosted_cusps is not None:
        for index in range(12):
            local_value = local_cusps[index] if index < len(local_cusps) else None
            hosted_value = hosted_cusps[index] if index < len(hosted_cusps) else None
            if local_value is None:
                missing.append(f"local.whole_sign_cusps[{index}].longitude")
            if hosted_value is None:
                missing.append(f"hosted.data.houses.cusps[{index}].longitude")
            if local_value is not None and hosted_value is not None:
                delta = _angular_deviation(local_value, hosted_value)
                deviations["cusps"].append(
                    {
                        "house": index + 1,
                        "local": local_value,
                        "hosted": hosted_value,
                        "deviation_degrees": delta,
                        "within_tolerance": delta <= tolerance,
                    }
                )

    compared = [
        *deviations["planets"].values(),
        *deviations["angles"].values(),
        *deviations["cusps"],
    ]
    complete = not missing and len(compared) == len(PLANET_IDS) + 2 + 12
    return {
        "complete": complete,
        "within_tolerance": complete
        and all(item["within_tolerance"] for item in compared),
        "tolerance_degrees": tolerance,
        "missing": missing,
        "deviations": deviations,
    }
