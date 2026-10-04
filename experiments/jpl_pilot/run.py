"""Print an independent JPL pilot chart. No network, LLM, or production access."""
import argparse
from datetime import datetime
import json
from pathlib import Path
from engine import JPLPilot

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--kernel', type=Path, default=Path('scratch/jpl-pilot/de440s.bsp'))
parser.add_argument('--utc', default='2000-01-01T12:00:00+00:00')
parser.add_argument('--latitude', type=float)
parser.add_argument('--longitude', type=float)
parser.add_argument('--tradition', choices=['western', 'vedic', 'sidereal-experimental'], default='western')
args = parser.parse_args()
engine = JPLPilot(args.kernel)
try:
    print(json.dumps(engine.chart(datetime.fromisoformat(args.utc.replace('Z', '+00:00')),
                                 args.latitude, args.longitude, tradition=args.tradition), indent=2))
finally:
    engine.close()
