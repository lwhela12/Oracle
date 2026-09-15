"""Content-free operational logs and optional anonymous PostHog events.

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
                    'fallback_values', 'duration_ms'},
    'interpretation_usage': {'model', 'input_tokens', 'output_tokens', 'thinking_tokens',
                             'cached_tokens', 'total_tokens'},
}
SPREADS = {'tarot': {'3-card', 'yes-no', '5-card', 'celtic'},
           'runes': {'norns', 'single', 'five-cross', 'thor-hammer', 'nine-worlds'}}


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
    operational_log(record)
    if state and state['visitor_id'] and enabled():
        state['events'].append(record)


def flush(state):
    """One bounded synchronous batch; no serverless background thread to lose."""
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
             'events': []}
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
    # Update the pending analytics start event; stdout start is deliberately early.
    for event in g.oracle_telemetry['events']:
        if event['event'] == 'reading_started':
            event.update(details)
