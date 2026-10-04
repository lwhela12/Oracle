"""Production packaging checks for the independent JPL astrology runtime."""

from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
KERNEL = ROOT / "astrology" / "jpl" / "data" / "de440s.bsp"
EXPECTED_KERNEL_SHA256 = "c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2"
JPL_RUNTIME_AVAILABLE = all(
    importlib.util.find_spec(name) is not None
    for name in ("numpy", "skyfield", "jplephem")
)
requires_jpl_runtime = unittest.skipUnless(
    JPL_RUNTIME_AVAILABLE,
    "optional JPL runtime dependencies are not installed",
)


class JPLReleaseTests(unittest.TestCase):
    def test_packaged_kernel_is_the_pinned_unmodified_de440s_file(self):
        self.assertTrue(KERNEL.is_file())
        digest = sha256()
        with KERNEL.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        self.assertEqual(digest.hexdigest(), EXPECTED_KERNEL_SHA256)

    def test_jpl_is_the_default_backend_and_uses_the_packaged_kernel(self):
        from astrology import backend
        from astrology import jpl_adapter

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ORACLE_ASTROLOGY_BACKEND", None)
            os.environ.pop("ORACLE_JPL_KERNEL_PATH", None)
            self.assertEqual(backend.selected_backend(), "jpl")
            self.assertEqual(jpl_adapter._kernel_path(), KERNEL)

    @requires_jpl_runtime
    def test_release_identity_range_and_limitations_are_explicit(self):
        from astrology.jpl import __version__
        from astrology.jpl.engine import ENGINE_VERSION, QuantumOracleEphemeris

        self.assertEqual(ENGINE_VERSION, "1.0.0")
        self.assertEqual(__version__, "1.0.0")
        engine = QuantumOracleEphemeris(KERNEL)
        try:
            chart = engine.chart(datetime(2000, 1, 1, 12, tzinfo=timezone.utc))
        finally:
            engine.close()
        self.assertEqual(chart["engine"]["library"], "Quantum Oracle Ephemeris")
        self.assertEqual(chart["engine"]["library_version"], "1.0.0")
        self.assertEqual(chart["engine"]["engine_version"], "1.0.0")
        self.assertEqual(chart["engine"]["range_utc"], "[1850-01-01, 2150-01-01)")
        warnings = chart["provenance"]["warnings"]
        self.assertFalse(any("not production-qualified" in item for item in warnings))
        self.assertTrue(any("system barycenters" in item for item in warnings))
        self.assertTrue(any("Earth rotation" in item for item in warnings))

    @requires_jpl_runtime
    def test_production_calculation_cannot_import_experiments_or_swiss(self):
        script = r'''
import importlib.abc
import os
import sys
from datetime import datetime, timezone

class BlockForbidden(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if (fullname == "experiments" or fullname.startswith("experiments.") or
                fullname == "swisseph" or fullname == "astrology.engine"):
            raise ImportError("forbidden production dependency: " + fullname)
        return None

sys.meta_path.insert(0, BlockForbidden())
os.environ.pop("ORACLE_ASTROLOGY_BACKEND", None)
os.environ.pop("ORACLE_JPL_KERNEL_PATH", None)
from astrology.backend import calculate_chart, selected_backend
assert selected_backend() == "jpl"
chart = calculate_chart(datetime(2000, 1, 1, 12, tzinfo=timezone.utc), 35, -110)
assert chart["engine"]["library"] == "Quantum Oracle Ephemeris"
assert chart["engine"]["library_version"] == "1.0.0"
assert not any(name == "experiments" or name.startswith("experiments.") for name in sys.modules)
assert "swisseph" not in sys.modules and "astrology.engine" not in sys.modules
'''
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    @requires_jpl_runtime
    def test_bad_kernel_hash_is_sanitized_by_the_api(self):
        from app import app

        with tempfile.NamedTemporaryFile(suffix="-PRIVATE-KERNEL.bsp") as bad:
            bad.write(b"not the pinned DE440s kernel")
            bad.flush()
            with patch.dict(
                os.environ,
                {
                    "ORACLE_ASTROLOGY_ENABLED": "1",
                    "ORACLE_ANALYTICS_ENABLED": "0",
                    "ORACLE_ASTROLOGY_BACKEND": "jpl",
                    "ORACLE_JPL_KERNEL_PATH": bad.name,
                },
            ):
                response = app.test_client().post(
                    "/astrology/chart",
                    json={"chart_kind": "current", "instant_utc": "2000-01-01T12:00:00Z"},
                )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["code"], "astrology_unavailable")
        body = response.get_data(as_text=True)
        self.assertNotIn("PRIVATE-KERNEL", body)
        self.assertNotIn("checksum", body.lower())

    @requires_jpl_runtime
    def test_unavailable_default_kernel_path_is_sanitized_by_the_api(self):
        from app import app
        from astrology import jpl_adapter

        missing = ROOT / "astrology" / "jpl" / "data" / "PRIVATE-MISSING.bsp"
        with patch.dict(
            os.environ,
            {
                "ORACLE_ASTROLOGY_ENABLED": "1",
                "ORACLE_ANALYTICS_ENABLED": "0",
                "ORACLE_ASTROLOGY_BACKEND": "jpl",
            },
        ), patch.object(jpl_adapter, "_DEFAULT_KERNEL", missing):
            os.environ.pop("ORACLE_JPL_KERNEL_PATH", None)
            response = app.test_client().post(
                "/astrology/chart",
                json={"chart_kind": "current", "instant_utc": "2000-01-01T12:00:00Z"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["code"], "astrology_unavailable")
        self.assertNotIn("PRIVATE-MISSING", response.get_data(as_text=True))

    @requires_jpl_runtime
    def test_experiment_modules_are_compatibility_shims(self):
        from astrology.jpl.engine import QuantumOracleEphemeris
        from experiments.jpl_pilot.engine import JPLPilot
        from experiments.jpl_pilot.sidereal import CONVENTION_ID

        self.assertIs(JPLPilot, QuantumOracleEphemeris)
        self.assertEqual(CONVENTION_ID, "iae-2021")


if __name__ == "__main__":
    unittest.main()
