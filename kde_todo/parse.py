"""Parsing of durations, clock times, dates and quick-add text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

import dateparser

_DURATION = re.compile(r"^(?:(\d+(?:\.\d+)?)h)?(?:(\d+)m(?:in)?)?$", re.I)
_TIME = re.compile(r"^@?(\d{1,2})(?::(\d{2}))?$")


def parse_duration(text: str) -> int:
    """'45m', '1h', '1h30m', '1.5h', '90' -> minutes."""
    text = text.strip()
    if text.isdigit():
        minutes = int(text)
    else:
        m = _DURATION.match(text)
        if not m or not any(m.groups()):
            raise ValueError(f"not a duration: {text!r}")
        minutes = round(float(m.group(1) or 0) * 60) + int(m.group(2) or 0)
    if minutes <= 0:
        raise ValueError(f"duration must be positive: {text!r}")
    return minutes


def is_duration(text: str) -> bool:
    try:
        parse_duration(text)
    except ValueError:
        return False
    return not text.isdigit()  # bare numbers are words in quick-add text


def parse_time(text: str) -> str:
    """'9', '9:30', '@14:05' -> 'HH:MM'."""
    m = _TIME.match(text.strip())
    if not m:
        raise ValueError(f"not a time: {text!r}")
    h, mins = int(m.group(1)), int(m.group(2) or 0)
    if h > 23 or mins > 59:
        raise ValueError(f"not a time: {text!r}")
    return f"{h:02d}:{mins:02d}"


def parse_date(text: str, today: date) -> date:
    """'today', 'tomorrow', 'fri', 'oct 25', 'in 3 days', '2026-10-25', and '+3' / '-1' as day offsets."""
    if re.fullmatch(r"\s*[+-]\d+\s*", text):
        return today + timedelta(days=int(text))
    settings = {"PREFER_DATES_FROM": "future", "RELATIVE_BASE": datetime.combine(today, time())}
    parsed = dateparser.parse(text, languages=["en"], settings=settings)
    if parsed is None:
        raise ValueError(f"not a date: {text!r}")
    return parsed.date()


@dataclass
class QuickAdd:
    title: str
    duration: int | None = None
    at: str | None = None
    is_break: bool = False
    tags: list[str] = field(default_factory=list)


def parse_quick(text: str) -> QuickAdd:
    """'Standup @9:30 15m #work' / 'break Eating 30m'."""
    words = text.split()
    result = QuickAdd(title="")
    if words and words[0].lower() == "break":
        result.is_break = True
        words = words[1:]
    rest = []
    for word in words:
        if result.duration is None and is_duration(word):
            result.duration = parse_duration(word)
        elif result.at is None and word.startswith("@") and _TIME.match(word):
            result.at = parse_time(word)
        elif word.startswith("#") and len(word) > 1:
            result.tags.append(word[1:])
        else:
            rest.append(word)
    result.title = " ".join(rest)
    return result


def parse_tags(text: str) -> list[str]:
    """'#work, code  #Work' -> ['work', 'code']. Commas or spaces separate tags; duplicates are dropped."""
    tags, seen = [], set()
    for word in text.replace(",", " ").split():
        tag = word.lstrip("#")
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            tags.append(tag)
    return tags


def format_minutes(minutes: int) -> str:
    sign = "-" if minutes < 0 else ""
    h, m = divmod(abs(minutes), 60)
    if h and m:
        return f"{sign}{h}h{m:02d}m"
    return f"{sign}{h}h" if h else f"{sign}{m}m"
