"""Compatibility shim for the promoted Quantum Oracle Ephemeris engine."""

from pathlib import Path
import sys


_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from astrology.jpl.engine import *  # noqa: F401,F403
