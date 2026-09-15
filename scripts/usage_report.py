#!/usr/bin/env python3
"""Summarize exported Oracle JSON/NDJSON runtime events; no external services."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo


def extract(value):
    if isinstance(value, list):
        for item in value:
            yield from extract(item)
    elif isinstance(value, dict):
        if value.get('schema') == 'oracle.telemetry.v1':
            yield value
        else:
            for key in ('message', 'text', 'logs', 'events', 'data'):
                if key in value:
                    yield from extract(value[key])
    elif isinstance(value, str):
        try:
            yield from extract(json.loads(value))
        except (ValueError, TypeError):
            for line in value.splitlines():
                start = line.find('{')
                if start >= 0:
                    try:
                        yield from extract(json.loads(line[start:]))
                    except ValueError:
                        pass


def summarize(events, timezone='America/Los_Angeles', environment='production'):
    zone = ZoneInfo(timezone)
    seen = set()
    records = []
    for event in events:
        if event.get('environment') != environment:
            continue
        identity = event.get('event_id') or json.dumps(event, sort_keys=True)
        if identity not in seen:
            records.append(event)
            seen.add(identity)
    completed = {}
    attempts = set()
    attempt_outcomes = Counter()
    visitors = set()
    readers = set()
    qrng = []
    usage = []
    timestamps = []
    for event in records:
        if event.get('timestamp'):
            timestamps.append(event['timestamp'])
        if event.get('visitor_id'):
            visitors.add(event['visitor_id'])
        if event['event'] == 'reading_started':
            attempts.add(event['attempt_id'])
            if event.get('visitor_id'):
                readers.add(event['visitor_id'])
        if event['event'] == 'reading_finished':
            attempt_outcomes[event['outcome']] += 1
            if event.get('visitor_id'):
                readers.add(event['visitor_id'])
            if event['outcome'] == 'completed':
                completed.setdefault((event.get('visitor_id'), event['reading_id']), event)
        if event['event'] == 'qrng_result':
            qrng.append(event)
        if event['event'] == 'interpretation_usage':
            usage.append(event)
    days = defaultdict(lambda: {'readings': 0, 'readers': Counter()})
    for event in completed.values():
        day = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')).astimezone(zone).date().isoformat()
        days[day]['readings'] += 1
        if event.get('visitor_id'):
            days[day]['readers'][event['visitor_id']] += 1
    daily = []
    for day, counts in sorted(days.items()):
        histogram = Counter(str(n) if n < 5 else '5+' for n in counts['readers'].values())
        repeat = sum(n >= 2 for n in counts['readers'].values())
        daily.append({'day': day, 'completed_readings': counts['readings'],
                      'anonymous_readers': len(counts['readers']), 'readers_with_2plus': repeat,
                      'readings_per_reader_distribution': dict(sorted(histogram.items()))})
    fallback = sum(r.get('fallback_values', 0) > 0 for r in qrng)
    return {'environment': environment, 'timezone': timezone,
            'observed_first_event': min(timestamps) if timestamps else None,
            'observed_last_event': max(timestamps) if timestamps else None,
            'anonymous_visitors_in_export': len(visitors), 'anonymous_readers_in_export': len(readers),
            'reading_attempts': len(attempts), 'attempt_outcomes': dict(attempt_outcomes),
            'completed_readings': len(completed),
            'completed_readings_without_visitor_id': sum(not r.get('visitor_id') for r in completed.values()),
            'popular_modes': dict(Counter(r.get('mode', 'unknown') for r in completed.values())),
            'popular_spreads': dict(Counter(r.get('mode', 'unknown') + ':' + r.get('spread', 'default') for r in completed.values())),
            'qrng_requests': len(qrng), 'qrng_requests_with_fallback': fallback,
            'qrng_fallback_percent': round(100 * fallback / len(qrng), 2) if qrng else None,
            'qrng_fallback_reasons': dict(Counter(r['reason'] for r in qrng if r.get('fallback_values', 0))),
            'interpretation_calls_with_usage': len(usage),
            'reported_token_totals': {key: sum(r.get(key, 0) for r in usage) for key in ('input_tokens', 'output_tokens', 'thinking_tokens', 'cached_tokens', 'total_tokens')},
            'daily': daily,
            'limitations': ['Counts cover only events present in this export; this is not lifetime usage.',
                           'Browser identifiers estimate users. Cleared storage, devices, opt-outs and bots affect counts.',
                           'Completed means the server finished generation, not proof the user read it.',
                           'Missing finish events may be hard timeouts or missing logs. Missing token reports are not zero cost.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export', type=Path)
    parser.add_argument('--timezone', default='America/Los_Angeles')
    parser.add_argument('--environment', default='production')
    args = parser.parse_args()
    print(json.dumps(summarize(extract(args.export.read_text()), args.timezone, args.environment), indent=2))
