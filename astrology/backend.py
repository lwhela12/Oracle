"""Lazy calculation-backend selection for the default-off astrology feature."""

import os


def selected_backend() -> str:
    """Return the configured backend without importing either calculation engine."""

    value = os.environ.get("ORACLE_ASTROLOGY_BACKEND", "jpl").strip().lower()
    if value not in ("swiss", "jpl"):
        raise ImportError("Unsupported astrology backend configuration")
    return value


def supported_traditions() -> tuple[str, ...]:
    selected_backend()  # validate configuration without loading a calculation library
    return ("western", "vedic")


def sidereal_convention() -> dict[str, str]:
    if selected_backend() == 'jpl':
        return {'id': 'iae-2021', 'name': 'Indian Astronomical Ephemeris (2021 convention)', 'label': 'IAE 2021'}
    return {'id': 'swiss-lahiri', 'name': 'Lahiri', 'label': 'Lahiri'}


def date_bounds() -> dict[str, str]:
    if selected_backend() == "jpl":
        return {"min": "1850-01-01", "max": "2149-12-31"}
    return {"min": "0001-01-01", "max": "3000-12-31"}


def calculate_sky(instant, *, tradition="western"):
    if selected_backend() == "jpl":
        from astrology.jpl_adapter import calculate_sky as calculate
    else:
        from astrology.engine import calculate_sky as calculate
    return calculate(instant, tradition=tradition)


def calculate_chart(instant, latitude, longitude, *, tradition="western"):
    if selected_backend() == "jpl":
        from astrology.jpl_adapter import calculate_chart as calculate
    else:
        from astrology.engine import calculate_chart as calculate
    return calculate(instant, latitude, longitude, tradition=tradition)
