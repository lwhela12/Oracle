"""Privacy-preserving POST endpoint for the offline astrology place catalogue."""
import json
import os

from flask import Blueprint, jsonify, request

from astrology.places import ATTRIBUTION, PlaceQueryError, search_places


blueprint = Blueprint('astrology_places', __name__, url_prefix='/astrology')
MAX_BODY_BYTES = 1024


def _enabled():
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


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate field')
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError('Non-finite JSON number')


@blueprint.post('/places')
def places():
    if not _enabled():
        return _error('astrology_disabled', 'Astrology is not enabled.', 404)
    if request.content_length and request.content_length > MAX_BODY_BYTES:
        return _error('request_too_large', 'Place searches must be at most 1024 bytes.', 413)
    if not request.is_json:
        return _error('json_required', 'Send the place query as application/json.', 415)
    raw = request.stream.read(MAX_BODY_BYTES + 1)
    if len(raw) > MAX_BODY_BYTES:
        return _error('request_too_large', 'Place searches must be at most 1024 bytes.', 413)
    try:
        payload = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (ValueError, UnicodeError, RecursionError):
        return _error('invalid_json', 'Send a valid JSON object without duplicate fields.', 400)
    if not isinstance(payload, dict) or set(payload) != {'query'}:
        return _error('invalid_request', 'Send an object containing only query.', 400)
    try:
        matches = search_places(payload['query'])
    except PlaceQueryError as error:
        return _error(error.code, str(error), 400)
    except (ImportError, OSError):
        return _error('astrology_unavailable', 'The local place catalogue is unavailable.', 503)
    except Exception:
        return _error('place_search_failed', 'The place search could not be completed.', 503)
    return jsonify(places=matches, attribution=ATTRIBUTION)
