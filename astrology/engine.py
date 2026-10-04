"""Deterministic Western tropical and Vedic Lahiri sidereal calculations.

This module deliberately has no network or geocoding behavior. It uses the
Moshier model bundled with Swiss Ephemeris so the engine does not depend on
downloaded ephemeris files. Coordinates are apparent, geocentric
ecliptic longitudes of date; local angles use the true equator/equinox of date.

Swiss Ephemeris exposes native process-global state. A module-level reentrant lock serializes each complete native calculation,
including explicit Lahiri initialization for each sidereal call and ayanamsa/house
calculation. Tropical calls never request the sidereal flag.

Swiss Ephemeris programming reference:
https://www.astro.com/swisseph/swephprg.htm
"""

from __future__ import annotations

from datetime import datetime, timezone
from importlib import metadata
import math
from threading import RLock
from typing import Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import swisseph as swe


SIGNS = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)

PLANETS = (
    ("Sun", swe.SUN),
    ("Moon", swe.MOON),
    ("Mercury", swe.MERCURY),
    ("Venus", swe.VENUS),
    ("Mars", swe.MARS),
    ("Jupiter", swe.JUPITER),
    ("Saturn", swe.SATURN),
    ("Uranus", swe.URANUS),
    ("Neptune", swe.NEPTUNE),
    ("Pluto", swe.PLUTO),
)

VEDIC_PLANETS = PLANETS[:7] + (("Rahu", swe.MEAN_NODE),)
NAKSHATRAS = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
)
NAKSHATRA_LORDS = ("Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury")


# Explicit engine policy. These are conventional, not astronomical facts.
# Dictionary order is also the tie-breaker if wide orbs ever overlap.
MAJOR_ASPECT_ORBS = {
    "conjunction": {"angle": 0.0, "orb": 8.0},
    "sextile": {"angle": 60.0, "orb": 5.0},
    "square": {"angle": 90.0, "orb": 7.0},
    "trine": {"angle": 120.0, "orb": 7.0},
    "opposition": {"angle": 180.0, "orb": 8.0},
}

_CALC_FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED
_MOSHIER_MIN_YEAR = 1  # Python's datetime has no BCE representation.
_MOSHIER_MAX_YEAR = 3000
_SWISSEPH_LOCK = RLock()


def _finite_float(value: object, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field} must be a finite number")
    return result


def _normalise_angle(value: object, field: str = "angle") -> float:
    angle = _finite_float(value, field) % 360.0
    # Avoid serializing 360 due to floating-point behavior at the boundary.
    return 0.0 if math.isclose(angle, 360.0, rel_tol=0.0, abs_tol=1e-12) else angle


def _angular_separation(first: float, second: float) -> float:
    difference = abs(_normalise_angle(first) - _normalise_angle(second))
    return min(difference, 360.0 - difference)


def _zodiac_position(longitude: float) -> dict[str, object]:
    normalised = _normalise_angle(longitude, "longitude")
    sign_index = min(int(normalised // 30.0), 11)
    return {
        "longitude": normalised,
        "sign": SIGNS[sign_index],
        "degrees_in_sign": normalised - sign_index * 30.0,
    }


def nakshatra_position(longitude: float) -> dict[str, object]:
    """27 equal sidereal sectors, each with four equal padas, starting at Aries 0."""
    # Multiplication before division keeps exact 40/3 and 10/3 boundaries stable.
    pada_index = min(int(_normalise_angle(longitude) * 3.0 / 10.0), 107)
    index = pada_index // 4
    return {"name": NAKSHATRAS[index], "index": index + 1,
            "pada": pada_index % 4 + 1, "lord": NAKSHATRA_LORDS[index % 9]}


def calculate_vedic_aspects(longitudes: Mapping[str, float]) -> list[dict[str, object]]:
    """Directional, sign-based full Parashari graha drishti; no node drishti."""
    aspects = []
    for body, _ in PLANETS[:7]:
        if body not in longitudes:
            continue
        distances = {7} | {"Mars": {4, 8}, "Jupiter": {5, 9}, "Saturn": {3, 10}}.get(body, set())
        for other, longitude in longitudes.items():
            distance = whole_sign_house(longitude, longitudes[body])
            if body != other and distance in distances:
                aspects.append({"body_1": body, "body_2": other,
                                "aspect": "graha drishti", "house_distance": distance})
    return aspects


def _validate_tradition(tradition: str) -> None:
    if tradition not in ("western", "vedic"):
        raise ValueError("tradition must be western or vedic")


def whole_sign_cusps(ascendant_longitude: float) -> list[float]:
    """Return the twelve Whole Sign cusp longitudes, starting with house 1."""

    ascendant = _normalise_angle(ascendant_longitude, "ascendant longitude")
    first_cusp = int(ascendant // 30.0) * 30.0
    return [(first_cusp + index * 30.0) % 360.0 for index in range(12)]


def whole_sign_house(longitude: float, ascendant_longitude: float) -> int:
    """Assign an ecliptic longitude to a Whole Sign house (1 through 12)."""

    body_sign = int(_normalise_angle(longitude, "longitude") // 30.0)
    ascendant_sign = int(
        _normalise_angle(ascendant_longitude, "ascendant longitude") // 30.0
    )
    return (body_sign - ascendant_sign) % 12 + 1


def calculate_major_aspects(
    longitudes: Mapping[str, float],
) -> list[dict[str, object]]:
    """Find major aspects using the fixed orbs in ``MAJOR_ASPECT_ORBS``."""

    bodies = [
        (name, _normalise_angle(value, f"{name} longitude"))
        for name, value in longitudes.items()
    ]
    aspects: list[dict[str, object]] = []
    for first_index, (first_name, first_longitude) in enumerate(bodies):
        for second_name, second_longitude in bodies[first_index + 1 :]:
            separation = _angular_separation(first_longitude, second_longitude)
            matches = []
            for aspect_name, policy in MAJOR_ASPECT_ORBS.items():
                orb = abs(separation - policy["angle"])
                if orb <= policy["orb"]:
                    matches.append((orb, aspect_name, policy))
            if not matches:
                continue
            orb, aspect_name, policy = min(matches, key=lambda item: item[0])
            aspects.append(
                {
                    "body_1": first_name,
                    "body_2": second_name,
                    "aspect": aspect_name,
                    "separation": separation,
                    "exact_angle": policy["angle"],
                    "orb": orb,
                    "orb_limit": policy["orb"],
                }
            )
    return aspects


def _lunar_phase(sun_longitude: float, moon_longitude: float) -> dict[str, object]:
    angle = (
        _normalise_angle(moon_longitude) - _normalise_angle(sun_longitude)
    ) % 360.0
    if angle < 22.5 or angle >= 337.5:
        label = "New Moon"
    elif angle < 67.5:
        label = "Waxing Crescent"
    elif angle < 112.5:
        label = "First Quarter"
    elif angle < 157.5:
        label = "Waxing Gibbous"
    elif angle < 202.5:
        label = "Full Moon"
    elif angle < 247.5:
        label = "Waning Gibbous"
    elif angle < 292.5:
        label = "Last Quarter"
    else:
        label = "Waning Crescent"
    return {"angle": angle, "label": label}


def resolve_local_datetime(
    text: str, iana_zone: str, fold: int | None = None
) -> datetime:
    """Resolve a naive ISO local time with explicit DST gap/fold handling.

    An ambiguous wall time requires ``fold=0`` (first occurrence) or ``fold=1``
    (second occurrence).  A nonexistent wall time is always rejected.
    """

    try:
        local = datetime.fromisoformat(text)
    except (TypeError, ValueError) as exc:
        raise ValueError("text must be a valid ISO local date and time") from exc
    if local.tzinfo is not None:
        raise ValueError("text must be a local date and time without a UTC offset")
    if isinstance(fold, bool) or fold not in (None, 0, 1):
        raise ValueError("fold must be 0, 1, or None")
    try:
        zone = ZoneInfo(iana_zone)
    except (TypeError, ZoneInfoNotFoundError) as exc:
        raise ValueError(f"unknown IANA time zone: {iana_zone!r}") from exc

    candidates: list[datetime] = []
    for candidate_fold in (0, 1):
        candidate = local.replace(tzinfo=zone, fold=candidate_fold)
        round_trip = candidate.astimezone(timezone.utc).astimezone(zone)
        if round_trip.replace(tzinfo=None) == local:
            candidates.append(candidate)

    # A gap maps to a different local time under both fold interpretations.
    if not candidates:
        raise ValueError(f"nonexistent local time in {iana_zone}: {text}")

    distinct_instants = {candidate.astimezone(timezone.utc) for candidate in candidates}
    if len(distinct_instants) > 1:
        if fold is None:
            raise ValueError(
                f"ambiguous local time in {iana_zone}; specify fold=0 or fold=1"
            )
        return local.replace(tzinfo=zone, fold=fold)

    # Outside a DST fold, the fold bit has no effect on the represented instant.
    return candidates[0]


def _binding_version() -> tuple[str, str]:
    for distribution in ("pysweph", "pyswisseph"):
        try:
            return distribution, metadata.version(distribution)
        except metadata.PackageNotFoundError:
            pass
    return "swisseph", str(getattr(swe, "__version__", "unknown"))


def _unpack_planet_result(result: tuple) -> tuple[tuple[float, ...], int, str]:
    """Support pysweph's warning-aware result and legacy pyswisseph results."""

    if len(result) == 3:
        values, returned_flags, warning = result
    elif len(result) == 2:
        values, returned_flags = result
        warning = ""
    else:  # pragma: no cover - guards a future incompatible binding contract.
        raise RuntimeError("unexpected swisseph.calc_ut return shape")
    return tuple(values), int(returned_flags), str(warning)


def _validate_instant(instant: datetime) -> datetime:
    if not isinstance(instant, datetime) or instant.tzinfo is None:
        raise ValueError("instant must be a timezone-aware datetime")
    try:
        offset = instant.utcoffset()
    except (OverflowError, ValueError) as exc:
        raise ValueError("instant must have a valid UTC offset") from exc
    if offset is None:
        raise ValueError("instant must be a timezone-aware datetime")
    try:
        utc = instant.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise ValueError("instant cannot be represented in UTC") from exc
    if not _MOSHIER_MIN_YEAR <= utc.year <= _MOSHIER_MAX_YEAR:
        raise ValueError("instant is outside this engine's Moshier range (1-3000 CE)")
    return utc


def _validate_chart_inputs(
    instant: datetime, latitude: object, longitude: object
) -> tuple[datetime, float, float]:
    utc = _validate_instant(instant)
    lat = _finite_float(latitude, "latitude")
    lon = _finite_float(longitude, "longitude")
    if not -90.0 < lat < 90.0:
        raise ValueError("latitude must be strictly between -90 and 90 degrees")
    if not -180.0 <= lon <= 180.0:
        raise ValueError("longitude must be between -180 and 180 degrees")
    return utc, lat, lon


def _calculate_planets_locked(
    utc: datetime, tradition: str = "western",
) -> tuple[float, float, dict[str, dict[str, object]], dict[str, int], list[str]]:
    """Calculate shared global facts while ``_SWISSEPH_LOCK`` is held."""

    seconds = utc.second + utc.microsecond / 1_000_000.0
    jd_tt, jd_ut1 = swe.utc_to_jd(
        utc.year,
        utc.month,
        utc.day,
        utc.hour,
        utc.minute,
        seconds,
        swe.GREG_CAL,
    )
    jd_tt = _finite_float(jd_tt, "Julian day TT")
    jd_ut1 = _finite_float(jd_ut1, "Julian day UT1")

    vedic = tradition == "vedic"
    if vedic:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
    calc_flags = _CALC_FLAGS | (swe.FLG_SIDEREAL if vedic else 0)
    raw_planets: dict[str, dict[str, object]] = {}
    returned_flags: dict[str, int] = {}
    warnings: list[str] = []
    for name, planet_id in (VEDIC_PLANETS if vedic else PLANETS):
        values, flags, warning = _unpack_planet_result(
            swe.calc_ut(jd_ut1, planet_id, calc_flags)
        )
        if not flags & swe.FLG_MOSEPH:
            raise RuntimeError(f"Swiss Ephemeris did not use Moshier for {name}")
        if not flags & swe.FLG_SPEED:
            raise RuntimeError(f"Swiss Ephemeris did not return speed for {name}")
        if vedic and not flags & swe.FLG_SIDEREAL:
            raise RuntimeError(f"Swiss Ephemeris did not return sidereal coordinates for {name}")
        longitude_value = _normalise_angle(values[0], f"{name} longitude")
        speed = _finite_float(values[3], f"{name} longitudinal speed")
        raw_planets[name] = {
            **_zodiac_position(longitude_value),
            "speed_degrees_per_day": speed,
            "retrograde": speed < 0.0,
        }
        if vedic:
            raw_planets[name]["nakshatra"] = nakshatra_position(longitude_value)
        returned_flags[name] = flags
        if warning and warning not in warnings:
            warnings.append(warning)
    if vedic:
        rahu = raw_planets["Rahu"]
        longitude_value = (float(rahu["longitude"]) + 180.0) % 360.0
        raw_planets["Ketu"] = {**_zodiac_position(longitude_value),
            "speed_degrees_per_day": rahu["speed_degrees_per_day"],
            "retrograde": rahu["retrograde"], "nakshatra": nakshatra_position(longitude_value)}
    return jd_tt, jd_ut1, raw_planets, returned_flags, warnings


def _engine_record() -> dict[str, object]:
    binding_name, binding_version = _binding_version()
    return {
        "library": "Swiss Ephemeris",
        "library_version": str(getattr(swe, "version", "unknown")),
        "binding": binding_name,
        "binding_version": binding_version,
        "ephemeris_model": "Moshier analytical ephemeris (explicit)",
    }


def _provenance_record(
    returned_flags: Mapping[str, int], warnings: list[str], *, local: bool
) -> dict[str, object]:
    result: dict[str, object] = {
        "coordinate_model": "apparent geocentric tropical ecliptic longitudes of date",
        "time_conversion": (
            "UTC via swe.utc_to_jd; calc_ut and houses use UT1"
            if local
            else "UTC via swe.utc_to_jd; calc_ut uses UT1"
        ),
        "planetary_flags_requested": int(_CALC_FLAGS),
        "planetary_flags_returned": dict(returned_flags),
    }
    if local:
        result["house_system"] = "Whole Sign (Swiss Ephemeris W)"
    result.update(
        {
            "aspect_orbs_degrees": {
                name: dict(policy) for name, policy in MAJOR_ASPECT_ORBS.items()
            },
            "warnings": list(warnings),
            "sources": [
                "https://www.astro.com/swisseph/swephprg.htm",
                "https://github.com/astrorigin/pyswisseph/tree/master/docs/programmers_manual",
            ],
            "limitations": [
                "Moshier model range is 3000 BCE to 3000 CE; this datetime interface supports 1-3000 CE.",
                "UT1/TT accuracy depends on Swiss Ephemeris Delta T and leap-second data.",
                "Aspect orbs and eight-phase labels are explicit interpretive conventions.",
            ],
        }
    )
    return result


def _global_result(
    instant: datetime,
    utc: datetime,
    jd_tt: float,
    jd_ut1: float,
    planets: dict[str, dict[str, object]],
    returned_flags: Mapping[str, int],
    warnings: list[str],
    *,
    local: bool,
    ayanamsa: float | None = None,
) -> dict[str, object]:
    longitudes = {name: float(data["longitude"]) for name, data in planets.items()}
    result = {
        "engine": _engine_record(),
        "provenance": _provenance_record(returned_flags, warnings, local=local),
        "inputs": {
            "instant": instant.isoformat(),
            "utc": utc.isoformat().replace("+00:00", "Z"),
            "julian_day_tt": jd_tt,
            "julian_day_ut1": jd_ut1,
        },
        "planets": planets,
        "major_aspects": calculate_major_aspects(longitudes) if ayanamsa is None else [],
        "lunar_phase": _lunar_phase(longitudes["Sun"], longitudes["Moon"]),
    }

    if ayanamsa is not None:
        result.update(tradition="vedic", zodiac="sidereal",
                      ayanamsa={"name": "Lahiri", "degrees": ayanamsa},
                      major_aspects=[], vedic_aspects=calculate_vedic_aspects(longitudes))
        provenance = result["provenance"]
        provenance.update(coordinate_model="apparent geocentric Lahiri sidereal ecliptic longitudes of date",
                          planetary_flags_requested=int(_CALC_FLAGS | swe.FLG_SIDEREAL),
                          sidereal_mode="SIDM_LAHIRI",
                          ayanamsa_method="swe.get_ayanamsa_ex_ut with FLG_MOSEPH", node_model="mean ascending node; Ketu exactly opposite",
                          aspect_policy="Sign-based full Parashari graha drishti; seven physical grahas only; no node drishti or conjunctions")
        provenance.pop("aspect_orbs_degrees", None)
        provenance["limitations"][-1] = "Graha drishti, nakshatras and eight-phase labels are interpretive conventions."
        provenance["derived_bodies"] = {"Ketu": "Rahu longitude + 180 degrees; same longitudinal speed"}
    return result


def calculate_sky(instant: datetime, *, tradition: str = "western") -> dict[str, object]:
    """Calculate global geocentric sky facts for one aware instant.

    The result intentionally contains no location, local angles, house cusps, or
    per-planet house assignments.
    """

    _validate_tradition(tradition)
    utc = _validate_instant(instant)
    with _SWISSEPH_LOCK:
        jd_tt, jd_ut1, planets, returned_flags, warnings = _calculate_planets_locked(
            utc, tradition
        )
        ayanamsa = swe.get_ayanamsa_ex_ut(jd_ut1, swe.FLG_MOSEPH)[1] if tradition == "vedic" else None
    return _global_result(
        instant,
        utc,
        jd_tt,
        jd_ut1,
        planets,
        returned_flags,
        warnings,
        local=False,
        ayanamsa=ayanamsa,
    )


def calculate_chart(
    instant: datetime, latitude: float, longitude: float, *, tradition: str = "western"
) -> dict[str, object]:
    """Calculate a JSON-safe current-sky chart for one instant and location."""

    _validate_tradition(tradition)
    utc, lat, lon = _validate_chart_inputs(instant, latitude, longitude)
    with _SWISSEPH_LOCK:
        jd_tt, jd_ut1, raw_planets, returned_flags, warnings = (
            _calculate_planets_locked(utc, tradition)
        )
        swiss_cusps, ascmc = swe.houses_ex(jd_ut1, lat, lon, b"W", swe.FLG_SIDEREAL if tradition == "vedic" else 0)
        ayanamsa = swe.get_ayanamsa_ex_ut(jd_ut1, swe.FLG_MOSEPH)[1] if tradition == "vedic" else None

    ascendant_longitude = _normalise_angle(ascmc[0], "ascendant")
    midheaven_longitude = _normalise_angle(ascmc[1], "midheaven")
    expected_cusps = whole_sign_cusps(ascendant_longitude)
    returned_cusps = tuple(
        swiss_cusps[1:] if len(swiss_cusps) == 13 else swiss_cusps
    )
    if len(returned_cusps) != 12:
        raise RuntimeError(
            "Swiss Ephemeris returned an unexpected number of house cusps"
        )
    for expected, returned in zip(expected_cusps, returned_cusps):
        if _angular_separation(expected, returned) > 1e-7:
            raise RuntimeError(
                "Swiss Ephemeris returned inconsistent Whole Sign cusps"
            )

    for planet in raw_planets.values():
        planet["whole_sign_house"] = whole_sign_house(
            float(planet["longitude"]), ascendant_longitude
        )

    ascendant = _zodiac_position(ascendant_longitude)
    midheaven = _zodiac_position(midheaven_longitude)
    if tradition == "vedic":
        ascendant["nakshatra"] = nakshatra_position(ascendant_longitude)
    cusp_records = [
        {"house": index + 1, **_zodiac_position(cusp)}
        for index, cusp in enumerate(expected_cusps)
    ]
    result = _global_result(
        instant,
        utc,
        jd_tt,
        jd_ut1,
        raw_planets,
        returned_flags,
        warnings,
        local=True,
        ayanamsa=ayanamsa,
    )
    return {
        **result,
        "inputs": {
            "instant": instant.isoformat(),
            "utc": utc.isoformat().replace("+00:00", "Z"),
            "latitude": lat,
            "longitude": lon,
            "julian_day_tt": jd_tt,
            "julian_day_ut1": jd_ut1,
        },
        "planets": raw_planets,
        "ascendant": ascendant,
        "midheaven": midheaven,
        "whole_sign_cusps": cusp_records,
        "major_aspects": result["major_aspects"],
        "lunar_phase": result["lunar_phase"],
    }
