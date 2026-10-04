"""Default-off chart API. This module intentionally does not import Swiss Ephemeris."""
import json
import os
import uuid
from datetime import datetime, timezone
from flask import Blueprint, Response, jsonify, request, stream_with_context
from oracle_logic import GeminiOracle
from astrology.reading import build_interpretation_prompt
from astrology.service import ChartInputError, prepare_chart

blueprint = Blueprint('astrology', __name__, url_prefix='/astrology')
MAX_BODY_BYTES = 8192


def enabled():
    return os.environ.get('ORACLE_ASTROLOGY_ENABLED') == '1'


def _error(code, message, status):
    response = jsonify(error=True, code=code, message=message)
    response.status_code = status
    response.headers['Cache-Control'] = 'no-store'
    return response


@blueprint.after_request
def private_response(response):
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@blueprint.get('/capabilities')
def capabilities():
    active = enabled()
    configured = bool(os.environ.get('GEMINI_API_KEY'))
    return jsonify(enabled=active, chart_kinds=['natal', 'current', 'transit', 'horoscope'] if active else [],
                   traditions=['western', 'vedic'] if active else [],
                   configured=configured,
                   interpretation_available=active and configured, schema_version=1)


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('Duplicate field')
        obj[key] = value
    return obj


def _reject_constant(value):
    raise ValueError('Non-finite JSON number')


def _request_json():
    if request.content_length and request.content_length > MAX_BODY_BYTES:
        return None, _error('request_too_large', 'Astrology requests must be at most 8192 bytes.', 413)
    if not request.is_json:
        return None, _error('json_required', 'Send astrology inputs as application/json.', 415)
    raw = request.stream.read(MAX_BODY_BYTES + 1)
    if len(raw) > MAX_BODY_BYTES:
        return None, _error('request_too_large', 'Astrology requests must be at most 8192 bytes.', 413)
    try:
        payload = json.loads(raw, object_pairs_hook=_unique_object,
                             parse_constant=_reject_constant)
    except (ValueError, UnicodeError, RecursionError):
        return None, _error('invalid_json', 'Send a valid JSON object without duplicate fields or non-finite numbers.', 400)
    return payload, None


def _prepare(payload):
    try:
        if isinstance(payload, dict) and payload.get('chart_kind') == 'transit':
            from astrology.transits import prepare_transit
            return prepare_transit(payload), None
        if isinstance(payload, dict) and payload.get('chart_kind') == 'horoscope':
            from astrology.horoscopes import prepare_horoscope
            return prepare_horoscope(payload), None
        return prepare_chart(payload), None
    except ChartInputError as error:
        return None, _error(error.code, str(error), 400)
    except (ImportError, OSError):
        return None, _error('astrology_unavailable', 'The astrology calculation dependency is unavailable.', 503)
    except Exception:
        # Native/library failures must never echo birth data or provider/config details.
        return None, _error('calculation_failed', 'The chart could not be calculated.', 503)


@blueprint.post('/chart')
def chart():
    if not enabled():
        return _error('astrology_disabled', 'Astrology is not enabled.', 404)
    payload, error = _request_json()
    if error is not None:
        return error
    prepared, error = _prepare(payload)
    if error is not None:
        return error
    return jsonify(type='astrology', chart_kind=prepared['chart_kind'], chart=prepared,
                   chart_id=str(uuid.uuid4()), created_at=datetime.now(timezone.utc).isoformat())


def _sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


@blueprint.post('/read/stream')
def read_stream():
    if not enabled():
        return _error('astrology_disabled', 'Astrology is not enabled.', 404)
    payload, error = _request_json()
    if error is not None:
        return error
    if not isinstance(payload, dict) or set(payload) - {'chart_request', 'question'}:
        return _error('invalid_request', 'The request must contain only chart_request and optional question.', 400)
    if 'chart_request' not in payload:
        return _error('invalid_request', 'chart_request is required.', 400)
    question = payload.get('question')
    if question is not None and (not isinstance(question, str) or len(question) > 2000):
        return _error('invalid_question', 'question must be a string of at most 2000 characters.', 400)

    prepared, error = _prepare(payload['chart_request'])
    if error is not None:
        return error
    if prepared['chart_kind'] == 'transit':
        from astrology.transits import build_transit_prompt
        prompt = build_transit_prompt(prepared, question)
    elif prepared['chart_kind'] == 'horoscope':
        from astrology.horoscopes import build_horoscope_prompt
        prompt = build_horoscope_prompt(prepared, question)
    else:
        prompt = build_interpretation_prompt(prepared, question)
    metadata = {
        'type': 'astrology',
        'chart_kind': prepared['chart_kind'],
        'chart': prepared,
        'canonical_reading_id': str(uuid.uuid4()),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'content_format_version': 1,
    }

    def generate():
        yield _sse('metadata', metadata)
        try:
            oracle = GeminiOracle()
        except Exception:
            yield _sse('error', {
                'error': True,
                'code': 'interpretation_unavailable',
                'message': 'Astrology interpretation is not available right now.',
            })
            return
        try:
            for token in oracle.stream_chat(prompt):
                yield _sse('token', {'token': token})
            yield _sse('done', {'done': True})
        except Exception:
            yield _sse('error', {
                'error': True,
                'code': 'interpretation_failed',
                'message': 'The chart was calculated, but its interpretation could not be completed.',
            })

    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-store',
        'X-Accel-Buffering': 'no',
    })


def reject_astrology_chat():
    """Direct astrology callers to its chart-specific request contract."""
    body = request.get_json(silent=True)
    if isinstance(body, dict) and body.get('mode') == 'astrology':
        if not enabled():
            return _error('astrology_disabled', 'Astrology is not enabled.', 404)
        return _error('astrology_endpoint_required',
                      'Use /astrology/read/stream with chart_request for astrology readings.', 409)
    return None
