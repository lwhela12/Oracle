"""Compare public reference epochs against NASA JPL Horizons, sequentially.

Sources: https://ssd-api.jpl.nasa.gov/doc/horizons.html and
https://ssd.jpl.nasa.gov/horizons/manual.html (observer quantity 31).
No user data, API keys, or production endpoints are used.
"""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import requests
import swisseph as swe
from experiments.astrology.calculations import calculate_chart

BODIES = {"Sun": "10", "Moon": "301", "Mercury": "199", "Venus": "299", "Mars": "499",
          "Jupiter": "599", "Saturn": "699", "Uranus": "799", "Neptune": "899", "Pluto": "999"}
DATES = [datetime(2000, 1, 1, 12, tzinfo=timezone.utc),
         datetime(2024, 4, 15, 12, tzinfo=timezone.utc),
         datetime(2026, 10, 4, 12, tzinfo=timezone.utc)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "scratch/astrology-prototype/reference")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    charts = [calculate_chart(date, 0, 0) for date in DATES]
    jds = [swe.julday(d.year, d.month, d.day, d.hour, swe.GREG_CAL) for d in DATES]
    report = {"source": "NASA JPL Horizons live API", "quantity": "31: apparent geocentric ecliptic longitude of date",
        "comparison": "Swiss Ephemeris Moshier vs Horizons numerical ephemerides",
        "tolerance_degrees": 0.01, "tolerance_note": "Exploratory threshold, not a universal accuracy guarantee. Frame models differ.",
        "scope": "Ten planetary longitudes at three public reference epochs; does not validate houses/aspects or hosted AstroAPI.",
        "rows": [], "failures": []}
    for name, body_id in BODIES.items():
        params = {"format": "json", "COMMAND": body_id, "OBJ_DATA": "NO", "MAKE_EPHEM": "YES",
            "EPHEM_TYPE": "OBSERVER", "CENTER": "500@399", "TLIST": "'" + ",".join(map(str, jds)) + "'",
            "QUANTITIES": "31", "CSV_FORMAT": "YES", "ANG_FORMAT": "DEG", "EXTRA_PREC": "YES", "CAL_TYPE": "GREGORIAN"}
        started = time.monotonic()
        cache = args.output / f"horizons-{name.lower()}.json"
        try:
            if cache.exists():
                saved = json.loads(cache.read_text())
                if saved["request"] != params:
                    raise ValueError("Cached request differs")
                payload = saved["response"]
                duration = saved["duration_ms"]
            else:
                response = requests.get("https://ssd.jpl.nasa.gov/api/horizons.api", params=params, timeout=(5, 30))
                response.raise_for_status()
                payload = response.json()
                duration = round((time.monotonic() - started) * 1000)
                cache.write_text(json.dumps({"request": params, "response": payload, "duration_ms": duration}, indent=2))
            if "error" in payload:
                raise ValueError(payload["error"])
            result = payload["result"]
            if "ObsEcLon" not in result or "GEOCENTRIC" not in result:
                raise ValueError("Unexpected coordinate frame")
            lines = result.split("$$SOE", 1)[1].split("$$EOE", 1)[0].strip().splitlines()
            if len(lines) != len(DATES):
                raise ValueError("Unexpected epoch count")
            for date, chart, line in zip(DATES, charts, lines):
                fields = next(csv.reader([line]))
                expected_time = date.strftime("%Y-%b-%d %H:%M:%S")
                if not fields[0].strip().startswith(expected_time):
                    raise ValueError("Reference epoch mismatch")
                reference = float(fields[3])
                actual = chart["planets"][name]["longitude"]
                delta = abs((actual - reference + 180) % 360 - 180)
                report["rows"].append({"body": name, "utc": date.isoformat(), "local_degrees": actual,
                    "reference_degrees": reference, "difference_arcseconds": delta * 3600,
                    "within_tolerance": delta <= report["tolerance_degrees"], "request_duration_ms": duration,
                    "reference_file": cache.name, "api_signature": payload.get("signature")})
            print(f"Checked {name}", flush=True)
        except Exception as error:
            report["failures"].append({"body": name, "error": str(error)[:300]})
            print(f"Reference failed: {name} ({type(error).__name__})", flush=True)
    report["complete"] = len(report["rows"]) == 30 and not report["failures"]
    report["passed"] = report["complete"] and all(row["within_tolerance"] for row in report["rows"])
    report["maximum_difference_arcseconds"] = max((r["difference_arcseconds"] for r in report["rows"]), default=None)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("rows",)}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
