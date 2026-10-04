"""Adapt Quantum Oracle Ephemeris to the application's chart contract."""

import atexit
from datetime import timezone
import os
from pathlib import Path
from threading import RLock


_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_KERNEL = Path(__file__).resolve().parent / "jpl" / "data" / "de440s.bsp"
_INSTANCE_LOCK = RLock()
_INSTANCES = {}


def _close_instances() -> None:
    with _INSTANCE_LOCK:
        instances = list(_INSTANCES.values())
        _INSTANCES.clear()
    for instance in instances:
        instance.close()


atexit.register(_close_instances)


def _kernel_path() -> Path:
    configured = os.environ.get("ORACLE_JPL_KERNEL_PATH")
    path = Path(configured).expanduser() if configured else _DEFAULT_KERNEL
    if not path.is_absolute():
        path = _ROOT / path
    return path.resolve()


def _engine():
    """Return one verified engine per resolved kernel path, safe across threads."""

    path = _kernel_path()
    with _INSTANCE_LOCK:
        instance = _INSTANCES.get(path)
        if instance is None:
            from astrology.jpl.engine import QuantumOracleEphemeris

            try:
                instance = QuantumOracleEphemeris(path)
            except ValueError as exc:
                # Kernel-integrity/configuration failures are service failures, not
                # user chart-range errors. The API layer emits a sanitized message.
                raise ImportError("The configured JPL kernel failed validation") from exc
            _INSTANCES[path] = instance
        return instance


# Compatibility for local code written against the opt-in pilot adapter.
_pilot = _engine


def _lunar_phase(sun_longitude: float, moon_longitude: float) -> dict:
    angle = (float(moon_longitude) - float(sun_longitude)) % 360.0
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


def _adapt(result: dict, instant) -> dict:
    """Add the stable fields consumed by API, prompts, exports, and strict UI checks."""

    engine = dict(result.get("engine", {}))
    engine.setdefault("library", "Quantum Oracle Ephemeris")
    engine.setdefault("library_version", "1.0.0")
    engine.setdefault("binding", "jplephem")
    engine.setdefault("binding_version", engine.get("jplephem_version", "unknown"))
    engine.setdefault("ephemeris_model", "JPL DE440s")
    result["engine"] = engine

    utc = instant.astimezone(timezone.utc)
    inputs = dict(result.get("inputs", {}))
    inputs["instant"] = instant.isoformat()
    inputs["utc"] = utc.isoformat().replace("+00:00", "Z")
    result["inputs"] = inputs
    result.setdefault("major_aspects", [])
    result["lunar_phase"] = _lunar_phase(
        result["planets"]["Sun"]["longitude"],
        result["planets"]["Moon"]["longitude"],
    )
    return result


def _require_tradition(tradition: str) -> None:
    if tradition not in ('western', 'vedic'):
        raise ValueError("Unsupported JPL tradition")


def calculate_sky(instant, *, tradition="western") -> dict:
    _require_tradition(tradition)
    return _adapt(_engine().chart(instant, tradition=tradition), instant)


def calculate_chart(instant, latitude, longitude, *, tradition="western") -> dict:
    _require_tradition(tradition)
    return _adapt(
        _engine().chart(
            instant,
            latitude=latitude,
            longitude=longitude,
            tradition=tradition,
        ),
        instant,
    )
