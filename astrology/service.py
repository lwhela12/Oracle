"""Validated calculation requests; no Gemini, random draws, storage, or network I/O."""
from datetime import datetime, timezone
import math
import re
from zoneinfo import ZoneInfo


class ChartInputError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _fail(code, message):
    raise ChartInputError(code, message)


def _keys(value, allowed, label):
    if not isinstance(value, dict) or set(value) - allowed:
        _fail('invalid_request', f'{label} must be an object containing only supported fields.')


def _location(value, required=False):
    if value is None:
        if required:
            _fail('location_required', 'A birth chart requires latitude and longitude.')
        return None
    _keys(value, {'latitude', 'longitude'}, 'Location')
    result = {}
    for key, limit in [('latitude', 90), ('longitude', 180)]:
        n = value.get(key)
        if isinstance(n, bool) or not isinstance(n, (int, float)):
            _fail('invalid_location', 'Latitude and longitude must be finite numbers.')
        try:
            n = float(n)
        except (ValueError, OverflowError):
            _fail('invalid_location', 'Latitude and longitude must be finite numbers.')
        if not math.isfinite(n) or abs(n) > limit or (key == 'latitude' and abs(n) == 90):
            _fail('invalid_location', 'Latitude must be between -90 and 90 (exclusive); longitude between -180 and 180.')
        result[key] = n
    return result


def validate_tradition(payload):
    tradition = payload.get('tradition', 'western')
    if tradition not in ('western', 'vedic'):
        _fail('invalid_tradition', 'Choose tradition western or vedic.')
    return tradition


def prepare_chart(payload, *, now=None):
    """Build schema v1 from explicit inputs; imports native code only when called.

    A ``place_id`` resolves through the packaged GeoNames city catalogue.  The
    original coordinates/timezone contract remains available as an advanced
    caller-supplied path.
    """
    _keys(payload, {'chart_kind', 'birth', 'location', 'place_id', 'instant_utc', 'tradition'}, 'Request')
    tradition = validate_tradition(payload)
    kind = payload.get('chart_kind')
    if kind not in ('natal', 'current'):
        _fail('invalid_chart_kind', 'Choose chart_kind natal or current.')
    has_place = 'place_id' in payload
    place_id = payload.get('place_id')
    if has_place and (not isinstance(place_id, str) or
                      not re.fullmatch(r'geonames:[1-9]\d{0,11}', place_id)):
        _fail('invalid_place_id', 'Place id must use the geonames:<number> format.')
    if has_place and 'location' in payload:
        _fail('conflicting_location', 'Use either place_id or location coordinates, not both.')
    location = _location(payload.get('location'), required=kind == 'natal' and not has_place)
    local_text = zone = fold = None
    if kind == 'natal':
        if 'instant_utc' in payload:
            _fail('invalid_request', 'Birth charts use birth.local_datetime and birth.timezone, not instant_utc.')
        birth = payload.get('birth')
        _keys(birth, {'local_datetime', 'timezone', 'fold'}, 'Birth')
        if has_place and 'timezone' in birth:
            _fail('conflicting_timezone', 'A selected place supplies the birth timezone; do not also send birth.timezone.')
        local_text, zone, fold = birth.get('local_datetime'), birth.get('timezone'), birth.get('fold')
        if not isinstance(local_text, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?', local_text):
            _fail('invalid_birth_time', 'Enter a local birth date and time in YYYY-MM-DDTHH:mm[:ss] format without an offset.')
        if not has_place and (not isinstance(zone, str) or not zone or len(zone) > 128):
            _fail('invalid_timezone', 'Provide an IANA timezone such as America/Phoenix.')
        if fold is not None and (type(fold) is not int or fold not in (0, 1)):
            _fail('invalid_fold', 'For repeated clock times, fold must be 0 (first) or 1 (second).')
    else:
        if 'birth' in payload:
            _fail('invalid_request', 'Current-sky requests do not accept birth information.')
        supplied = payload.get('instant_utc')
        if 'instant_utc' in payload:
            if not isinstance(supplied, str) or len(supplied) > 64:
                _fail('invalid_instant', 'instant_utc must be an ISO date-time with an explicit UTC offset.')
            try:
                instant = datetime.fromisoformat(supplied)
                if instant.tzinfo is None or instant.utcoffset() is None:
                    raise ValueError()
                instant = instant.astimezone(timezone.utc)
            except (ValueError, OverflowError):
                _fail('invalid_instant', 'instant_utc must be a valid ISO date-time with an explicit UTC offset.')
        else:
            instant = now if now is not None else datetime.now(timezone.utc)

    place = None
    if has_place:
        from astrology.places import PlaceLookupError, get_place
        try:
            place = get_place(place_id)
        except PlaceLookupError as error:
            _fail(error.code, str(error))
        location = {'latitude': place['latitude'], 'longitude': place['longitude']}
        zone = place['timezone']

    from astrology.engine import calculate_chart, calculate_sky, resolve_local_datetime
    if kind == 'natal':
        try:
            instant = resolve_local_datetime(local_text, zone, fold)
        except (ValueError, OverflowError) as error:
            message = str(error)
            if message.startswith('ambiguous local time'):
                _fail('ambiguous_birth_time', 'This clock time occurred twice. Choose the first or second occurrence below.')
            if message.startswith('nonexistent local time'):
                _fail('nonexistent_birth_time', 'This clock time did not exist because of a timezone transition. Check the recorded birth time.')
            if message.startswith('unknown IANA'):
                _fail('invalid_timezone', 'The supplied IANA timezone is not recognized.')
            _fail('invalid_birth_time', 'The birth date and time could not be resolved.')
    try:
        options = {'tradition': tradition} if tradition == 'vedic' else {}
        chart = calculate_chart(instant, **location, **options) if location else calculate_sky(instant, **options)
    except (ValueError, OverflowError):
        _fail('unsupported_chart_input', 'The date or location is outside the supported calculation range.')
    chart['tradition'] = tradition
    chart['zodiac'] = 'sidereal' if tradition == 'vedic' else 'tropical'
    chart['schema_version'] = 1
    chart['chart_kind'] = kind
    chart['location_precision'] = ('city_center' if place else
                                   ('provided_coordinates' if location else 'global_no_location'))
    chart['input_resolution'] = {
        'time_source': 'birth_local_time' if kind == 'natal' else ('supplied_instant' if 'instant_utc' in payload else 'server_clock'),
        'location_source': 'geonames' if place else ('caller_supplied' if location else None),
    }
    if place:
        chart['place'] = place
    if kind == 'natal':
        chart['input_resolution'].update(timezone=zone, utc_offset_seconds=int(instant.utcoffset().total_seconds()),
                                         local_datetime=local_text, fold=instant.fold,
                                         timezone_source=('geonames_iana_history' if place else
                                                          'caller_supplied_iana_history'))
    elif place:
        local = instant.astimezone(ZoneInfo(zone))
        chart['input_resolution'].update(
            timezone=zone,
            utc_offset_seconds=int(local.utcoffset().total_seconds()),
            local_datetime=local.isoformat(),
            fold=local.fold,
            timezone_source='geonames_iana_history',
        )
    return chart
