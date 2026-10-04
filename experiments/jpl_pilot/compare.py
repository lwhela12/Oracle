"""Report observed residuals; never adjust pilot coefficients to fit Swiss output."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time
from engine import JPLPilot, signed_difference, mean_node, mean_ecliptic_rotation, angles
from sidereal import mean_ayanamsa
import math

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline', type=Path, default=Path('scratch/jpl-pilot/baseline.json'))
parser.add_argument('--output', type=Path, default=Path('scratch/jpl-pilot/report.json'))
parser.add_argument('--sidereal-convention', choices=['vedic','sidereal-experimental'], default='vedic')
args = parser.parse_args()
engine = JPLPilot('scratch/jpl-pilot/de440s.bsp')
rows, runtimes = [], []
for sample in json.loads(args.baseline.read_text()):
    case = sample['case']
    dt = datetime.fromisoformat(case['utc'])
    start = time.perf_counter()
    pilot = engine.chart(dt, case['latitude'], case['longitude'])
    runtimes.append((time.perf_counter()-start)*1000)
    experimental = engine.chart(dt, case['latitude'], case['longitude'], tradition=args.sidereal_convention)
    reference = sample['western']
    row = {'case': case, 'longitude_arcsec': {}, 'speed_deg_day': {},
           'sign_mismatches': [], 'house_mismatches': [], 'retrograde_mismatches': [],
           'sidereal_arcsec': {}, 'nakshatra_pada_mismatches': []}
    for name, point in pilot['planets'].items():
        other = reference['planets'][name]
        row['longitude_arcsec'][name] = abs(signed_difference(point['longitude'], other['longitude']))*3600
        row['speed_deg_day'][name] = abs(point['speed_degrees_per_day']-other['speed_degrees_per_day'])
        for field, mismatch in [('sign', 'sign_mismatches'), ('whole_sign_house', 'house_mismatches'), ('retrograde', 'retrograde_mismatches')]:
            if point[field] != other[field]: row[mismatch].append(name)
    for angle in ('ascendant', 'midheaven'):
        row[angle+'_arcsec'] = abs(signed_difference(pilot[angle]['longitude'], reference[angle]['longitude']))*3600
    row['ut1_difference_seconds'] = (pilot['inputs']['julian_day_ut1']-reference['inputs']['julian_day_ut1'])*86400
    row['tt_difference_seconds'] = (pilot['inputs']['julian_day_tt']-reference['inputs']['julian_day_tt'])*86400
    # Diagnostic only: distinguish time-model differences from position/geometry.
    # The engine never consumes Swiss time values during an actual calculation.
    aligned = engine._positions(engine.ts.tt_jd(reference['inputs']['julian_day_tt']), list(pilot['planets']))
    row['matched_tt_max_longitude_arcsec'] = max(abs(signed_difference(aligned[name],point['longitude']))*3600 for name,point in reference['planets'].items())
    aligned_angles = angles(engine.ts.ut1_jd(reference['inputs']['julian_day_ut1']), case['latitude'],case['longitude'])
    row['matched_ut1_max_angle_arcsec'] = max(abs(signed_difference(value,reference[name]['longitude']))*3600 for name,value in zip(('ascendant','midheaven'),aligned_angles))
    def aspect_keys(chart):
        return {(x['body_1'],x['body_2'],x['aspect']) for x in chart['major_aspects']}
    row['aspect_membership_difference'] = sorted(aspect_keys(pilot)^aspect_keys(reference))
    for name, point in experimental['planets'].items():
        other = sample['vedic']['planets'][name]
        row['sidereal_arcsec'][name] = abs(signed_difference(point['longitude'],other['longitude']))*3600
        if (point['nakshatra']['index'], point['nakshatra']['pada']) != (other['nakshatra']['index'], other['nakshatra']['pada']):
            row['nakshatra_pada_mismatches'].append(name)
    rows.append(row)

horizons = []
fixture = json.loads(Path(__file__).with_name('horizons_fixture.json').read_text())
for row in fixture['rows']:
    dt = datetime.strptime(row['utc_horizons'], '%Y-%b-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
    actual = engine.chart(dt)['planets'][row['body']]['longitude']
    horizons.append({'body': row['body'], 'utc': dt.isoformat(), 'reference_degrees': row['longitude'],
                     'pilot_degrees': actual, 'difference_arcsec': abs(signed_difference(actual,row['longitude']))*3600,
                     'reference_target': row['target'], 'reference_file': 'horizons_fixture.json'})

def summarize(subset):
    return {'charts': len(subset), 'max_longitude_arcsec': max(max(x['longitude_arcsec'].values()) for x in subset),
            'max_ascendant_arcsec': max(x['ascendant_arcsec'] for x in subset),
            'max_midheaven_arcsec': max(x['midheaven_arcsec'] for x in subset),
            'max_speed_deg_day': max(max(x['speed_deg_day'].values()) for x in subset),
            'matched_tt_max_longitude_arcsec': max(x['matched_tt_max_longitude_arcsec'] for x in subset),
            'matched_ut1_max_angle_arcsec': max(x['matched_ut1_max_angle_arcsec'] for x in subset),
            'sign_mismatches': sum(len(x['sign_mismatches']) for x in subset),
            'house_mismatches': sum(len(x['house_mismatches']) for x in subset),
            'retrograde_mismatches': sum(len(x['retrograde_mismatches']) for x in subset),
            'aspect_membership_differences': sum(len(x['aspect_membership_difference']) for x in subset),
            'max_sidereal_arcsec': max(max(x['sidereal_arcsec'].values()) for x in subset),
            'nakshatra_pada_mismatches': sum(len(x['nakshatra_pada_mismatches']) for x in subset)}

t = engine.ts.utc(2026,3,22)
v = mean_ecliptic_rotation(t) @ engine.sidereal_origin
mean_offset = math.degrees(math.atan2(v[1], v[0])) % 360
if args.sidereal_convention == 'vedic':
    mean_offset = mean_ayanamsa(t.tt)
pac_ayanamsa = 24+13/60+24/3600
pac_node = 313+42/60+25.31/3600
report = {'engine': engine.provenance, 'baseline': 'existing Swiss/Moshier engine, black-box output only',
          'sidereal_convention':args.sidereal_convention,
          'all_cases': summarize(rows),
          'modern_nonpolar': summarize([x for x in rows if '1972' <= x['case']['utc'] < '2027' and abs(x['case']['latitude'])<66]),
          'historical_before_1972': summarize([x for x in rows if x['case']['utc'] < '1972']),
          'horizons': {'count':len(horizons), 'max_arcsec':max(x['difference_arcsec'] for x in horizons),
                       'note':'Previously cached JPL Horizons apparent geocentric longitudes, three public epochs; planetary centers differ from DE440s barycenters.'},
          'latency_ms': {'median':statistics.median(runtimes),'max':max(runtimes)},
          'pac_reference': {'utc':'2026-03-22T00:00:00Z', 'mean_ayanamsa_reference':pac_ayanamsa,
                            'mean_ayanamsa_pilot':mean_offset, 'ayanamsa_difference_arcsec':(mean_offset-pac_ayanamsa)*3600,
                            'mean_rahu_reference':pac_node, 'mean_rahu_pilot':(mean_node(t.tt)-mean_offset)%360,
                            'rahu_difference_arcsec':signed_difference(mean_node(t.tt)-mean_offset,pac_node)*3600,
                            'verdict':'Measurement only; no exact Lahiri compliance claim.'},
          'rows':rows, 'horizons_rows':horizons}
args.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('rows','horizons_rows')},indent=2))
engine.close()
