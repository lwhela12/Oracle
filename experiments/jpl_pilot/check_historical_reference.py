"""Sequential, cached NASA Horizons check using synthetic public epochs only."""
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import subprocess

DATES = ['1850-01-15T12:00:00', '1900-04-15T12:00:00', '1950-07-15T12:00:00',
         '1961-03-01T00:00:00', '1962-03-01T00:00:00', '1965-08-15T12:00:00',
         '1968-02-01T00:00:00', '1971-12-31T23:59:59', '1972-01-01T00:00:00',
         '2016-12-31T23:59:59', '2017-01-01T00:00:00', '2026-10-04T12:00:00']
cache = Path('scratch/jpl-pilot/historical-reference')
cache.mkdir(parents=True,exist_ok=True)
jds = []
for text in DATES:
    dt = datetime.fromisoformat(text)
    jds.append(dt.toordinal()+1721424.5+(dt.hour*3600+dt.minute*60+dt.second)/86400)
fixture={'source':'NASA JPL Horizons, geocentric apparent ecliptic longitude of date, quantity 31',
         'time_note':'Horizons UT means UT1 before 1962, UTC thereafter; the pilot uses USNO historical UTC starting 1961. The 1961 sample is therefore a convention-difference diagnostic.',
         'rows':[]}
for name,target in [('Sun','10'),('Moon','301')]:
    params={'format':'json','COMMAND':target,'OBJ_DATA':'NO','MAKE_EPHEM':'YES',
            'EPHEM_TYPE':'OBSERVER','CENTER':'500@399','TLIST':"'"+','.join(map(str,jds))+"'",
            'QUANTITIES':'31','TIME_TYPE':'UT','CSV_FORMAT':'YES','ANG_FORMAT':'DEG',
            'EXTRA_PREC':'YES','CAL_TYPE':'GREGORIAN'}
    file=cache/f'{name.lower()}.json'
    if file.exists():
        saved=json.loads(file.read_text())
        if saved['request']!=params: raise ValueError('Cached reference request differs')
        payload=saved['response']
    else:
        # curl uses this Mac's configured certificate trust. Never disable TLS verification.
        payload=json.loads(subprocess.check_output(['curl','--fail','--silent','--show-error','--max-time','60',
                    '--user-agent','QuantumOracle-JPL-Pilot/0.1 (+https://github.com/lwhela12/Oracle)',
                    'https://ssd.jpl.nasa.gov/api/horizons.api?'+urlencode(params)]))
        file.write_text(json.dumps({'request':params,'response':payload},indent=2)+'\n')
    if 'error' in payload: raise ValueError(payload['error'])
    result=payload['result']
    if 'ObsEcLon' not in result or 'GEOCENTRIC' not in result: raise ValueError('Unexpected reference frame')
    rows=result.split('$$SOE')[1].split('$$EOE')[0].strip().splitlines()
    if len(rows)!=len(DATES): raise ValueError('Unexpected epoch count')
    for text,line in zip(DATES,rows):
        fields=next(csv.reader([line]))
        actual=datetime.strptime(fields[0].strip(),'%Y-%b-%d %H:%M:%S.%f')
        if abs((actual-datetime.fromisoformat(text)).total_seconds())>.001: raise ValueError('Epoch mismatch')
        fixture['rows'].append({'body':name,'utc':text+'+00:00','longitude':float(fields[3]),'target':target})
Path(__file__).with_name('historical_fixture.json').write_text(json.dumps(fixture,indent=2)+'\n')
print('Recorded',len(fixture['rows']),'public reference positions')
