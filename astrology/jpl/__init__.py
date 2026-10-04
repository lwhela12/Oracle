"""Independent, offline astrology calculations backed by JPL DE440s."""

from .engine import ENGINE_VERSION, QuantumOracleEphemeris

__version__ = ENGINE_VERSION

__all__ = ("ENGINE_VERSION", "QuantumOracleEphemeris", "__version__")
