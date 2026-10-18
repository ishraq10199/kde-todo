"""Operations on the records, used by both the CLI and the GUI.

Each public method holds the data lock for its whole read-modify-write, and runs
the rollover check first.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from functools import wraps

from . import markdown, schedule
from .model import (ACTIVE, BREAK, DONE, MOVED, PENDING, ROLLED, RUNNING, SKIPPED, STASHED, TASK, UNFINISHED, Day, Item,
                    Stash)
from .storage import Store


class TodoError(Exception):
    pass


def keep_started_first(day: Day) -> None:
    """Done, skipped and running items always come before pending ones, keeping their order.
    Rolled, moved and stashed rows are history and keep their places."""
    places = [n for n, item in enumerate(day.items) if item.status in ACTIVE]
    ordered = sorted((day.items[n] for n in places), key=lambda item: item.status == PENDING)
    for n, item in zip(places, ordered):
        day.items[n] = item


def local_now() -> datetime:
    return datetime.now().astimezone()


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def transaction(method):
    @wraps(method)
    def wrapper(self: Planner, *args, **kwargs):
        with self.store.lock:
            self._roll_over_and_notify()
            return method(self, *args, **kwargs)
    return wrapper


@dataclass
class Rolled:
    source: date
    item: Item


class Planner:
    def __init__(self, store: Store | None = None, clock: Callable[[], datetime] = local_now):
        self.store = store or Store()
        self.clock = clock
        # Called with the rolled items when a rollover moves anything.
        self.on_rollover: Callable[[list[Rolled]], None] | None = None

    def now(self) -> datetime:
        return self.clock()

    def today(self) -> date:
        return self.now().date()

    @property
    def config(self) -> dict:
        return self.store.load_config()

    def _day_start(self) -> time:
        return schedule.parse_hhmm(self.config["day_start"])

    def _slots(self, day: Day) -> list[schedule.Slot]:
        return schedule.compute(day, self._day_start(), self.now())

    def _save(self, day: Day) -> None:
        keep_started_first(day)
        self.store.save_day(day, markdown.render_day(day, self._slots(day), self.now()))

    def _save_stash(self, stash: Stash) -> None:
        self.store.save_stash(stash, markdown.render_stash(stash))

    def _get(self, day: Day, item_id) -> Item:
        try:
            return day.get(item_id)
        except KeyError:
            raise TodoError(f"no item {item_id} on {day.date}") from None

    def _find_running(self) -> tuple[Day, Item] | None:
        # A block running at midnight stays on the day it started.
        for d in (self.today(), self.today() - timedelta(days=1)):
            day = self.store.load_day(d)
            if day.running:
                return day, day.running
        return None

    def _roll_over(self) -> list[Rolled]:
        """Copy unfinished tasks from past days into today. Idempotent."""
        today = self.today()
        state = self.store.load_state()
        through = state.get("rolled_through")
        through = date.fromisoformat(through) if through else None
        if through is not None and through >= today - timedelta(days=1):
            return []

        rolled: list[Rolled] = []
        target = self.store.load_day(today)
        for d in self.store.list_days():
            if d >= today or (through is not None and d <= through):
                continue
            day = self.store.load_day(d)
            changed = False
            for item in day.items:
                if item.status == PENDING and item.kind == TASK:
                    copy = target.add(item.fresh_copy(origin=d.isoformat(), keep_fixed=False))
                    item.status, item.target = ROLLED, today.isoformat()
                    rolled.append(Rolled(d, copy))
                    changed = True
            if changed:
                self._save(day)
        if rolled:
            self._save(target)
        state["rolled_through"] = (today - timedelta(days=1)).isoformat()
        self.store.save_state(state)
        return rolled

    def _roll_over_and_notify(self) -> list[Rolled]:
        rolled = self._roll_over()
        if rolled and self.on_rollover:
            self.on_rollover(rolled)
        return rolled

    def roll_over(self) -> list[Rolled]:
        """Run the rollover now. Other public methods also run it."""
        with self.store.lock:
            return self._roll_over_and_notify()

    @transaction
    def day(self, d: date | None = None) -> Day:
        return self.store.load_day(d or self.today())

    @transaction
    def slots(self, d: date | None = None) -> list[schedule.Slot]:
        return self._slots(self.store.load_day(d or self.today()))

    @transaction
    def current(self) -> schedule.Slot | None:
        found = self._find_running()
        if found:
            day, item = found
            return next(s for s in self._slots(day) if s.item.uid == item.uid)
        return schedule.current(self._slots(self.store.load_day(self.today())), self.now())

    @transaction
    def stash_items(self) -> Stash:
        return self.store.load_stash()

    def days(self) -> list[date]:
        return self.store.list_days()

    @transaction
    def add(self, title: str, duration: int | None = None, *, on: date | None = None, at: str | None = None,
            kind: str = TASK, notes: str = "", tags: list[str] | None = None, new_label: bool = False,
            position: int | None = None) -> Item:
        title = title.strip()
        if not title:
            raise TodoError("title is empty")
        if kind == BREAK:
            title = self._break_label(title, new_label)
        day = self.store.load_day(on or self.today())
        item = day.add(Item(title=title, duration=duration or self.config["default_duration"], kind=kind,
                            fixed_start=at, notes=notes, tags=tags or []), position)
        self._save(day)
        return item

    def _break_label(self, label: str, new_label: bool) -> str:
        config = self.config
        labels = config["break_labels"]
        match = next((existing for existing in labels if existing.lower() == label.lower()), None)
        if match:
            return match
        if not new_label:
            raise TodoError(f"unknown break label {label!r}. Choose one of: {', '.join(labels)} "
                            f"(add it with --new-label)")
        config["break_labels"] = [*labels, label]
        self.store.save_config(config)
        return label

    @transaction
    def start(self, item_id, *, switch: bool = False) -> Item:
        day = self.store.load_day(self.today())
        item = self._get(day, item_id)
        if item.status != PENDING:
            raise TodoError(f"{item.title!r} is {item.status}, not pending")
        running, other_day = day.running, None
        if running is None:
            yesterday = self.store.load_day(day.date - timedelta(days=1))
            running, other_day = yesterday.running, yesterday
        if running:
            if not switch:
                raise TodoError(f"{running.title!r} is running. Finish or skip it first, or use --switch.")
            self._finish(running, DONE)
            if other_day:
                self._save(other_day)
        item.status, item.actual_start = RUNNING, _iso(self.now())
        self._save(day)
        return item

    def _finish(self, item: Item, status: str) -> None:
        now = _iso(self.now())
        if item.status == RUNNING:
            item.actual_end = now
        elif status == DONE:
            item.actual_end = now  # never started, so the schedule keeps its planned slot
        item.status = status

    def _resolve(self, item_id, on: date | None) -> tuple[Day, Item]:
        if item_id is None and on is None:
            found = self._find_running()
            if not found:
                raise TodoError("nothing is running")
            return found
        day = self.store.load_day(on or self.today())
        if item_id is None:
            if not day.running:
                raise TodoError(f"nothing is running on {day.date}")
            return day, day.running
        return day, self._get(day, item_id)

    @transaction
    def done(self, item_id=None, *, on: date | None = None) -> Item:
        day, item = self._resolve(item_id, on)
        if item.status not in UNFINISHED:
            raise TodoError(f"{item.title!r} is already {item.status}")
        self._finish(item, DONE)
        self._save(day)
        return item

    @transaction
    def skip(self, item_id=None, *, on: date | None = None) -> Item:
        day, item = self._resolve(item_id, on)
        if item.status not in UNFINISHED:
            raise TodoError(f"{item.title!r} is already {item.status}")
        self._finish(item, SKIPPED)
        self._save(day)
        return item

    @transaction
    def reopen(self, item_id, *, on: date | None = None) -> Item:
        day = self.store.load_day(on or self.today())
        item = self._get(day, item_id)
        if item.status not in (DONE, SKIPPED):
            raise TodoError(f"{item.title!r} is {item.status}; only done or skipped items can be reopened")
        item.status, item.actual_start, item.actual_end, item.extensions = PENDING, None, None, []
        self._save(day)
        return item

    @transaction
    def extend(self, minutes: int, item_id=None, *, on: date | None = None) -> tuple[Item, list[schedule.Slot]]:
        """Lengthen a block (the running one by default). Returns any fixed-item conflicts it causes."""
        if minutes <= 0:
            raise TodoError("extension must be positive")
        day, item = self._resolve(item_id, on)
        if item.status not in UNFINISHED:
            raise TodoError(f"{item.title!r} is {item.status}; only unfinished items can be extended")
        if item.status == RUNNING:
            item.extensions.append(minutes)
        else:
            item.duration += minutes
        self._save(day)
        return item, schedule.conflicts(self._slots(day))

    @transaction
    def edit(self, item_id, *, on: date | None = None, title: str | None = None, duration: int | None = None,
             at: str | None | bool = False, notes: str | None = None, tags: list[str] | None = None) -> Item:
        """Change fields. Pass at=None to clear the fixed start; at=False leaves it."""
        day = self.store.load_day(on or self.today())
        item = self._get(day, item_id)
        if title is not None:
            item.title = self._break_label(title, False) if item.kind == BREAK else title
        if duration is not None:
            item.duration = duration
        if at is not False:
            item.fixed_start = at
        if notes is not None:
            item.notes = notes
        if tags is not None:
            item.tags = tags
        self._save(day)
        return item

    @transaction
    def reorder(self, item_id, position: int, *, on: date | None = None) -> Item:
        """Move a pending item to `position` among the day's active items. It can't go above
        done, skipped or running items."""
        day = self.store.load_day(on or self.today())
        item = self._get(day, item_id)
        if item.status != PENDING:
            raise TodoError(f"{item.title!r} is {item.status}; only pending items can be reordered")
        active = [i for i in day.active if i is not item]
        position = max(0, min(position, len(active)))
        anchor = active[position] if position < len(active) else None
        day.items.remove(item)
        day.items.insert(day.items.index(anchor) if anchor else len(day.items), item)
        self._save(day)
        return item

    @transaction
    def remove(self, item_id, *, on: date | None = None) -> Item:
        day = self.store.load_day(on or self.today())
        item = self._get(day, item_id)
        day.remove(item)
        self._save(day)
        return item

    @transaction
    def move(self, item_id, to: date, *, on: date | None = None) -> Item:
        day = self.store.load_day(on or self.today())
        if to == day.date:
            raise TodoError("item is already on that day")
        item = self._get(day, item_id)
        if item.status != PENDING:
            raise TodoError(f"{item.title!r} is {item.status}; only pending items can be moved")
        target = self.store.load_day(to)
        copy = target.add(item.fresh_copy(origin=day.date.isoformat()))
        item.status, item.target = MOVED, to.isoformat()
        self._save(target)
        self._save(day)
        return copy

    @transaction
    def stash(self, item_id, *, on: date | None = None) -> Item:
        day = self.store.load_day(on or self.today())
        item = self._get(day, item_id)
        if item.status != PENDING:
            raise TodoError(f"{item.title!r} is {item.status}; only pending items can be stashed")
        stash = self.store.load_stash()
        copy = stash.add(item.fresh_copy(origin=day.date.isoformat()))
        item.status, item.target = STASHED, "stash"
        self._save_stash(stash)
        self._save(day)
        return copy

    @transaction
    def unstash(self, stash_id, to: date | None = None, position: int | None = None) -> Item:
        stash = self.store.load_stash()
        try:
            item = stash.get(stash_id)
        except KeyError:
            raise TodoError(f"no item {stash_id} in the stash") from None
        day = self.store.load_day(to or self.today())
        copy = day.add(item.fresh_copy(origin="stash"), position)
        stash.remove(item)
        self._save(day)
        self._save_stash(stash)
        return copy

    @transaction
    def set_config(self, key: str, value) -> None:
        config = self.config
        config[key] = value
        self.store.save_config(config)

    def break_labels(self) -> list[str]:
        return list(self.config["break_labels"])

    @transaction
    def add_break_label(self, label: str) -> list[str]:
        self._break_label(label.strip(), True)
        return self.break_labels()

    @transaction
    def remove_break_label(self, label: str) -> list[str]:
        config = self.config
        remaining = [x for x in config["break_labels"] if x.lower() != label.lower()]
        if len(remaining) == len(config["break_labels"]):
            raise TodoError(f"no break label {label!r}")
        config["break_labels"] = remaining
        self.store.save_config(config)
        return remaining
