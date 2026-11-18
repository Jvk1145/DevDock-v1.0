"""Timestamp helpers. All timestamps are stored as UTC 'YYYY-MM-DD HH:MM:SS' strings."""
from __future__ import annotations

from datetime import datetime, timezone

FORMAT = "%Y-%m-%d %H:%M:%S"


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def now_str() -> str:
    return utc_now().strftime(FORMAT)


def parse(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("T", " ")
    for fmt in (FORMAT, "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def humanize(value: str | datetime | None, now: datetime | None = None) -> str:
    """'just now', '5 min ago', '2 hours ago', 'yesterday', '3 days ago', 'Mar 4, 2025'."""
    moment = value if isinstance(value, datetime) else parse(value)
    if moment is None:
        return ""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    now = now or utc_now()
    seconds = max(0, int((now - moment).total_seconds()))
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return "1 hour ago" if hours == 1 else f"{hours} hours ago"
    days = hours // 24
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    local = moment.astimezone()
    return f"{local:%b} {local.day}, {local.year}"
