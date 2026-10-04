"""Deterministic astrology calculations.

Import :mod:`astrology.engine` explicitly to use the calculator. Keeping this
package initializer import-light lets the rest of the application start when
the optional Swiss Ephemeris binding is not installed.
"""

__all__ = ["engine"]
