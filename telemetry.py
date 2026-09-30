"""Content-free operational logs, PostgreSQL events, and optional PostHog events.

No prompts, response text, symbols, IPs, URLs, or session history are accepted.
"""
import json
import os
import time
import uuid
from datetime import datetime, timezone
from functools import wraps

import requests
from flask import g, has_request_context, make_response, request, stream_with_context

FIELDS = {
    'app_opened': set(),
    'reading_started': {'mode', 'spread', 'transport'},
    'reading_finished': {'mode', 'spread', 'transport', 'outcome', 'duration_ms'},
    'qrng_result': {'provider', 'source', 'reason', 'http_status', 'requested',
                    'fallback_values', 'duration_ms', 'failovers'},
    'interpretation_usage': {'model', 'input_tokens', 'output_tokens', 'thinking_tokens',
                             'cached_tokens', 'total_tokens'},
}
SPREADS = {'tarot': {'3-card', 'yes-no', '5-card', 'celtic'},
           'runes': {'norns', 'single', 'five-cross', 'thor-hammer', 'nine-worlds'}}
DATABASE_BUDGET_SECONDS = 0.5
MAX_DATABASE_BATCH = 50


def write_database_events(records, *, timeout_seconds):
    # No database driver or connection is needed when collection is unconfigured.
    started = time.monotonic()
    from analytics_store import write_events
    remaining = timeout_seconds - (time.monotonic() - started)
    if remaining <= 0:
        raise TimeoutError()
    return write_events(records, timeout_seconds=remaining)


def flush_database(state):
    """Spend one cumulative request budget, without threads or deferred retries."""
    events, state['database_events'] = state['database_events'], []
    if not events or state['database_failed']:
        return
    remaining = DATABASE_BUDGET_SECONDS - state['database_seconds']
    started = time.monotonic()
    try:
        if remaining <= 0:
            raise TimeoutError()
        write_database_events(events, timeout_seconds=remaining)
    except Exception:
        state['database_failed'] = True
        # Never include driver errors, DSNs, payloads, or provider response text.
        operational_log({'schema': 'oracle.telemetry.v1',
                         'event': 'telemetry_delivery_failed', 'sink': 'postgres',
                         'reason': 'budget_exhausted' if remaining <= 0 else 'delivery_error',
                         'event_count': len(events), 'attempt_id': state['attempt_id']})
    finally:
        state['database_seconds'] += time.monotonic() - started


def reading_prepared():
    """Identity for the actual draw, independent of optional audience analytics."""
    state = getattr(g, 'oracle_telemetry', None) if has_request_context() else None
    if state and state.get('reading_metadata'):
        return dict(state['reading_metadata'])
    metadata = {'canonical_reading_id': str(uuid.uuid4()),
                'created_at': datetime.now(timezone.utc).isoformat(),
                'content_format_version': 1}
    if state:
        state['reading_metadata'] = metadata
        flush_database(state)  # QRNG evidence survives a later generation timeout.
    return dict(metadata)


def enabled():
    return os.getenv('ORACLE_ANALYTICS_ENABLED', '1' if os.getenv('VERCEL_ENV') == 'production' else '0') == '1'


def valid_id(value):
    try:
        return str(uuid.UUID(value)) if isinstance(value, str) else None
    except ValueError:
        return None


def operational_log(record):
    try:
        print(json.dumps(record, separators=(',', ':')), flush=True)
    except Exception:
        pass  # Observability must never break a reading.


def emit(event, **fields):
    """Allowlisted events; request state is isolated by Flask's request context."""
    if event not in FIELDS:
        raise ValueError('Unknown telemetry event')
    state = getattr(g, 'oracle_telemetry', None) if has_request_context() else None
    record = {
        'schema': 'oracle.telemetry.v1', 'event': event,
        'event_id': str(uuid.uuid4()),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'environment': os.getenv('VERCEL_ENV', 'local'),
        **{k: v for k, v in fields.items() if k in FIELDS[event] and v is not None},
    }
    if state:
        record.update(attempt_id=state['attempt_id'], reading_id=state['reading_id'])
        record.update(state.get('details', {}))
        if state['visitor_id']:
            record['visitor_id'] = state['visitor_id']
        if state.get('reading_metadata'):
            record['schema'] = 'oracle.telemetry.v2'
            record['canonical_reading_id'] = state['reading_metadata']['canonical_reading_id']
    operational_log(record)
    if state and state['visitor_id'] and enabled():
        state['events'].append(dict(record))
    if state and state['database_enabled'] and not state['database_failed']:
        # Unlike the audience queue, operational storage does not require identity.
        stored = dict(record, traffic_class=state['traffic_class'])
        state['database_events'].append(stored)
        if len(state['database_events']) >= MAX_DATABASE_BATCH:
            flush_database(state)


def flush(state):
    """One bounded synchronous batch; no serverless background thread to lose."""
    flush_database(state)
    events, state['events'] = state['events'], []
    token = os.getenv('POSTHOG_PROJECT_TOKEN')
    if not events or not token or not enabled():
        return
    host = os.getenv('POSTHOG_HOST', 'https://us.i.posthog.com').rstrip('/')
    if host not in ('https://us.i.posthog.com', 'https://eu.i.posthog.com'):
        operational_log({'schema': 'oracle.telemetry.v1', 'event': 'telemetry_delivery_failed', 'reason': 'invalid_host'})
        return
    batch = []
    for event in events:
        props = {k: v for k, v in event.items() if k not in ('event', 'timestamp', 'visitor_id')}
        props.update(distinct_id=state['visitor_id'], **{
            '$process_person_profile': False, '$geoip_disable': True,
            '$ip': None, '$insert_id': event['event_id'],
        })
        batch.append({'event': event['event'], 'timestamp': event['timestamp'], 'properties': props})
    try:
        result = requests.post(host + '/batch/', json={'api_key': token, 'batch': batch},
                               timeout=(0.5, 1.0), allow_redirects=False)
        if not 200 <= result.status_code < 300:
            raise ValueError('delivery failed')
    except Exception:
        operational_log({'schema': 'oracle.telemetry.v1', 'event': 'telemetry_delivery_failed',
                         'reason': 'delivery_error', 'event_count': len(batch),
                         'attempt_id': state['attempt_id']})


def begin(data):
    opted_out = (data.get('analytics_opt_out') is True or request.headers.get('DNT') == '1'
                 or request.headers.get('Sec-GPC') == '1')
    state = {'attempt_id': str(uuid.uuid4()),
             'reading_id': valid_id(data.get('reading_id')) or str(uuid.uuid4()),
             'visitor_id': valid_id(data.get('visitor_id')) if enabled() and not opted_out else None,
             'events': [], 'database_events': [], 'database_seconds': 0.0,
             'database_failed': False,
             'database_enabled': bool(os.getenv('ORACLE_DATABASE_URL')),
             'traffic_class': os.getenv('ORACLE_TRAFFIC_CLASS', 'public')}
    g.oracle_telemetry = state
    return state


def track_reading(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            data = {}
        if str(data.get('message', '')).strip().lower() in {'quit', 'exit', 'bye'}:
            return function(*args, **kwargs)
        state = begin(data)
        # The route sets the actual inferred mode/spread before drawing.
        initial_mode = data.get('mode') if data.get('mode') in ('tarot', 'runes', 'iching', 'number', 'oracle') else 'unknown'
        initial_spread = data.get('spread_type')
        details = {'mode': initial_mode, 'spread': initial_spread if isinstance(initial_spread, str) and initial_spread in SPREADS.get(initial_mode, set()) else 'default',
                   'transport': 'stream' if request.path.endswith('/stream') else 'sync'}
        state['details'] = details
        started = time.monotonic()
        emit('reading_started', **details)
        finished = False

        def finish(outcome):
            nonlocal finished
            if finished:
                return
            finished = True
            emit('reading_finished', **details, outcome=outcome,
                 duration_ms=round((time.monotonic() - started) * 1000))
            flush(state)

        try:
            response = make_response(function(*args, **kwargs))
        except Exception:
            finish('failed')
            raise
        if response.mimetype != 'text/event-stream':
            payload = response.get_json(silent=True)
            if response.status_code < 400 and isinstance(payload, dict) and not payload.get('error') and not payload.get('terminate'):
                payload.update(reading_prepared())
                response.set_data(json.dumps(payload))
            finish('completed' if response.status_code < 400 else 'failed')
            return response
        original = response.response

        def observed():
            outcome = 'interrupted'
            try:
                for chunk in original:
                    text = chunk.decode() if isinstance(chunk, bytes) else chunk
                    if text.startswith('event: done\n'):
                        outcome = 'completed'
                        finish(outcome)
                    elif text.startswith('event: error\n'):
                        outcome = 'failed'
                        finish(outcome)
                    yield chunk
            except GeneratorExit:
                raise
            except Exception:
                outcome = 'failed'
                raise
            finally:
                try:
                    if hasattr(original, 'close'):
                        original.close()
                finally:
                    finish(outcome)
        response.response = stream_with_context(observed())
        return response
    return wrapped


def reading_details(mode, spread):
    if not has_request_context() or not getattr(g, 'oracle_telemetry', None):
        return
    details = g.oracle_telemetry['details']
    details['mode'] = 'number' if mode == 'oracle' else mode if mode in {'tarot', 'runes', 'iching', 'number'} else 'unknown'
    details['spread'] = spread if isinstance(spread, str) and spread in SPREADS.get(mode, set()) else {'tarot': '3-card', 'runes': 'norns'}.get(mode, 'default')
    # Stdout records the request immediately. Buffered sinks receive the actual
    # inferred dimensions before the draw or any provider call begins.
    for queue in ('events', 'database_events'):
        for event in g.oracle_telemetry[queue]:
            if event['event'] == 'reading_started':
                event.update(details)
    flush_database(g.oracle_telemetry)
