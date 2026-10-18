"""Turns a day's items into start and end times.

Items run back to back from the day start. Items with a fixed start stay at that
time. For today, pending items can't start before the current time, so an overrun
pushes everything after it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from .model import DONE, PENDING, RUNNING, SKIPPED, Day, Item


@dataclass
class Slot:
    item: Item
    start: datetime
    end: datetime
    overrun: bool = False  # running past its planned end
    conflict: Item | None = None  # earlier item whose block runs into this fixed item
    gap_before: int = 0  # unplanned minutes before this slot

    @property
    def minutes(self) -> int:
        return round((self.end - self.start).total_seconds() / 60)


def local_dt(d: date, t: time) -> datetime:
    """A local, timezone-aware datetime (DST-correct)."""
    return datetime.combine(d, t).astimezone()


def parse_hhmm(value: str) -> time:
    h, _, m = value.partition(":")
    return time(int(h), int(m or 0))


def compute(day: Day, day_start: time, now: datetime) -> list[Slot]:
    cursor = local_dt(day.date, day_start)
    is_today = day.date == now.date()
    slots: list[Slot] = []
    prev: Item | None = None

    for item in day.active:
        length = timedelta(minutes=item.total_minutes)
        overrun = False
        conflict = None

        if item.status in (DONE, SKIPPED, RUNNING) and item.actual_start:
            start = datetime.fromisoformat(item.actual_start)
            if item.status == RUNNING:
                end = start + length
                if now > end:
                    end, overrun = now, True
            elif item.actual_end:
                end = datetime.fromisoformat(item.actual_end)
            else:
                end = start + length
        elif item.status == SKIPPED:
            # Never started: takes no time.
            start = end = cursor
        elif item.fixed_start:
            start = local_dt(day.date, parse_hhmm(item.fixed_start))
            if prev is not None and cursor > start:
                conflict = prev
            end = start + length
        else:
            start = cursor
            if is_today and item.status == PENDING:
                start = max(start, now.replace(second=0, microsecond=0))
            end = start + length

        gap = max(0, round((start - cursor).total_seconds() / 60))
        slots.append(Slot(item, start, end, overrun, conflict, gap))
        cursor = max(cursor, end)
        if end > start:
            prev = item

    return slots


def current(slots: list[Slot], now: datetime) -> Slot | None:
    """The running slot, or else the pending slot that is due now."""
    for slot in slots:
        if slot.item.status == RUNNING:
            return slot
    for slot in slots:
        if slot.item.status == PENDING:
            return slot if slot.start <= now else None
    return None


def conflicts(slots: list[Slot]) -> list[Slot]:
    return [s for s in slots if s.conflict is not None]
