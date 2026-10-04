"""Timezone-only helpers shared by optional astrology calculation backends."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def resolve_local_datetime(
    text: str, iana_zone: str, fold: int | None = None
) -> datetime:
    """Resolve a naive ISO local time with explicit DST gap/fold handling."""

    try:
        local = datetime.fromisoformat(text)
    except (TypeError, ValueError) as exc:
        raise ValueError("text must be a valid ISO local date and time") from exc
    if local.tzinfo is not None:
        raise ValueError("text must be a local date and time without a UTC offset")
    if isinstance(fold, bool) or fold not in (None, 0, 1):
        raise ValueError("fold must be 0, 1, or None")
    try:
        zone = ZoneInfo(iana_zone)
    except (TypeError, ZoneInfoNotFoundError) as exc:
        raise ValueError(f"unknown IANA time zone: {iana_zone!r}") from exc

    candidates = []
    for candidate_fold in (0, 1):
        candidate = local.replace(tzinfo=zone, fold=candidate_fold)
        round_trip = candidate.astimezone(timezone.utc).astimezone(zone)
        if round_trip.replace(tzinfo=None) == local:
            candidates.append(candidate)

    if not candidates:
        raise ValueError(f"nonexistent local time in {iana_zone}: {text}")

    distinct_instants = {candidate.astimezone(timezone.utc) for candidate in candidates}
    if len(distinct_instants) > 1:
        if fold is None:
            raise ValueError(
                f"ambiguous local time in {iana_zone}; specify fold=0 or fold=1"
            )
        return local.replace(tzinfo=zone, fold=fold)

    return candidates[0]
