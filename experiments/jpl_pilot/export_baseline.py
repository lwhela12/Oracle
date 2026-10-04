"""Comparison-only harness; run in the EXISTING Swiss environment.

Calls the existing app as a black box. Not a dependency of the new engine.
No Swiss implementation or outputs are embedded in the pilot calculations.
"""
from datetime import datetime
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from astrology.engine import calculate_chart
from cases import cases

result = []
for case in cases():
    dt = datetime.fromisoformat(case['utc'])
    result.append({'case': case, 'western': calculate_chart(dt, case['latitude'], case['longitude']),
                   'vedic': calculate_chart(dt, case['latitude'], case['longitude'], tradition='vedic')})
path = Path(sys.argv[1])
path.write_text(json.dumps(result, indent=2)+'\n')
print(f'Exported {len(result)} synthetic black-box reference pairs to {path}')
