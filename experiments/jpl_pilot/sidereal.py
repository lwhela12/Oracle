"""Compatibility shim for the promoted IAE 2021 sidereal implementation."""

from pathlib import Path
import sys


_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from astrology.jpl.sidereal import *  # noqa: F401,F403
