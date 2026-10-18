"""QObject exposed to QML as `backend`. Wraps Planner."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Property, QFileSystemWatcher, QObject, QTimer, Signal, Slot

from .. import schedule
from ..model import BREAK, DONE, PENDING, RUNNING, SKIPPED
from ..parse import format_minutes, parse_duration, parse_quick, parse_tags, parse_time
from ..planner import Planner, Rolled, TodoError
from .chatter import Chatter, Progress

CHARACTERS = ("Mochi", "Blip", "Pip", "Tock", "Wisp")

CELEBRATE_SECONDS = 4
SLEEPY_AFTER_MINUTES = 15


class Backend(QObject):
    changed = Signal()  # day contents / schedule
    tick = Signal()  # clock-only updates (countdowns)
    stashChanged = Signal()
    labelsChanged = Signal()
    mascotChanged = Signal()
    error = Signal(str)
    warning = Signal(str)
    info = Signal(str)
    rolledOver = Signal(int)
    showRequested = Signal()
    extendRequested = Signal()  # ask the UI for a custom extension
    characterChanged = Signal()
    mascotSaid = Signal(str)

    def __init__(self, planner: Planner, parent=None):
        super().__init__(parent)
        self.p = planner
        self.p.on_rollover = self._on_rollover
        self._view_date = self.p.today()
        self._today = self.p.today()
        self._minute = None
        self._items: list[dict] = []
        self._summary = ""
        self._current: dict = {}
        self._current_slot: schedule.Slot | None = None
        self._stash: list[dict] = []
        self._snapshot = None
        self._records = None
        self._character = self._read_character()
        self._chatter = Chatter(self.p.now, lambda: self._character)
        self._mascot = "idle"
        self._celebrate_until: datetime | None = None
        self._idle_since: datetime | None = None

        self._watcher = QFileSystemWatcher(self)
        self._watcher.directoryChanged.connect(lambda _: self._reload_timer.start())
        self._reload_timer = QTimer(self, singleShot=True, interval=150)
        self._reload_timer.timeout.connect(self._reload_if_changed)

        self._clock = QTimer(self, interval=1000)
        self._clock.timeout.connect(self._on_clock)
        self._clock.start()
        self.refresh()

    def _get_view_date(self) -> str:
        return self._view_date.isoformat()

    def _set_view_date(self, value: str) -> None:
        d = date.fromisoformat(value)
        if d != self._view_date:
            self._view_date = d
            self.refresh()

    viewDate = Property(str, _get_view_date, _set_view_date, notify=changed)
    isToday = Property(bool, lambda self: self._view_date == self._today, notify=changed)
    isPast = Property(bool, lambda self: self._view_date < self._today, notify=changed)
    viewTitle = Property(str, lambda self: self._day_title(self._view_date), notify=changed)
    items = Property("QVariantList", lambda self: self._items, notify=changed)
    summary = Property(str, lambda self: self._summary, notify=changed)
    current = Property("QVariantMap", lambda self: self._current, notify=tick)
    nowText = Property(str, lambda self: f"{self.p.now():%H:%M}", notify=tick)
    stash = Property("QVariantList", lambda self: self._stash, notify=stashChanged)
    breakLabels = Property("QVariantList", lambda self: self.p.break_labels(), notify=labelsChanged)
    mascotState = Property(str, lambda self: self._mascot, notify=mascotChanged)
    defaultDuration = Property(int, lambda self: int(self.p.config["default_duration"]), constant=True)
    mascotCharacters = Property("QVariantList", lambda self: list(CHARACTERS), constant=True)

    def _read_character(self) -> str:
        name = self.p.config.get("mascot", "Mochi")
        return name if name in CHARACTERS else "Mochi"

    def _set_character(self, name: str) -> None:
        if name in CHARACTERS and name != self._character:
            self._run(self.p.set_config, "mascot", name)

    mascotCharacter = Property(str, lambda self: self._character, _set_character, notify=characterChanged)

    def _day_title(self, d: date) -> str:
        delta = (d - self._today).days
        name = {0: "Today", 1: "Tomorrow", -1: "Yesterday"}.get(delta)
        return f"{name} · {d:%a %d %b}" if name else f"{d:%A %d %B %Y}"

    def _watch(self) -> None:
        root = self.p.store.root
        root.mkdir(parents=True, exist_ok=True)
        wanted = {str(root)}
        for d in {self._today, self._view_date, self._today - timedelta(days=1)}:
            folder = self.p.store.day_path(d).parent
            if folder.exists():
                wanted.add(str(folder))
        for path in wanted - set(self._watcher.directories()):
            self._watcher.addPath(path)

    def _record_mtimes(self) -> list:
        """Only JSON records count. Reading takes the lock, which touches .lock in the same folder."""
        return sorted((str(f), f.stat().st_mtime_ns) for d in self._watcher.directories() for f in Path(d).glob("*.json"))

    def _reload_if_changed(self) -> None:
        if self._record_mtimes() != self._records:
            self.refresh()

    @Slot()
    def refresh(self) -> None:
        try:
            self._today = self.p.today()
            slots = self.p.slots(self._view_date)
            day = self.p.day(self._view_date)
            stash = [self._stash_dict(i) for i in self.p.stash_items().items]
        except Exception as e:  # e.g. a hand-edited JSON file that no longer parses
            self.error.emit(f"Could not read records: {e}")
            return
        by_uid = {s.item.uid: s for s in slots}
        now = self.p.now()
        items = [self._item_dict(i, by_uid.get(i.uid), now) for i in day.items]

        tasks = [i for i in day.active if i.kind != BREAK and i.status != SKIPPED]
        done = sum(i.status == DONE for i in tasks)
        planned = sum(s.minutes for s in slots if s.item.kind != BREAK and s.item.status != SKIPPED)
        breaks = sum(s.minutes for s in slots if s.item.kind == BREAK)
        ends = [s.end for s in slots if s.end > s.start]
        summary = (f"{done}/{len(tasks)} done · {format_minutes(planned)} planned · "
                   f"{format_minutes(breaks)} breaks" + (f" · ends {max(ends):%H:%M}" if ends else ""))
        self._watch()
        self._records = self._record_mtimes()
        character = self._read_character()
        if character != self._character:
            self._character = character
            self.characterChanged.emit()

        # Only signal real changes; every signal makes the views update.
        snapshot = (self._view_date, self._today, items, summary)
        if snapshot != self._snapshot:
            self._snapshot, self._items, self._summary = snapshot, items, summary
            self.changed.emit()
        if stash != self._stash:
            self._stash = stash
            self.stashChanged.emit()
        self._update_current()

    def _update_current(self) -> None:
        try:
            self._current_slot = self.p.current()
        except Exception:
            self._current_slot = None
        self._recompute_current()

    def _recompute_current(self) -> None:
        slot, now = self._current_slot, self.p.now()
        if slot is None:
            self._current = {}
        else:
            total = max(1.0, (slot.end - slot.start).total_seconds())
            remaining = (slot.end - now).total_seconds()
            if slot.item.status == RUNNING and not slot.overrun:
                planned_end = slot.end
            else:
                planned_end = slot.start + timedelta(minutes=slot.item.total_minutes)
            self._current = {
                **self._item_dict(slot.item, slot, now),
                "running": slot.item.status == RUNNING,
                "progress": min(1.0, max(0.0, 1 - remaining / total)) if slot.item.status == RUNNING else 0.0,
                "remainingText": self._remaining_text(slot, now, planned_end),
                "remainingSeconds": int(remaining),
            }
        self._update_mascot(now)
        self.tick.emit()

    @staticmethod
    def _remaining_text(slot: schedule.Slot, now: datetime, planned_end: datetime) -> str:
        if slot.item.status != RUNNING:
            return "up next"
        if slot.overrun:
            over = int((now - planned_end).total_seconds())
            return f"over by {over // 60}:{over % 60:02d}"
        left = int((slot.end - now).total_seconds())
        h, rest = divmod(left, 3600)
        return f"{h}:{rest // 60:02d}:{rest % 60:02d}" if h else f"{rest // 60}:{rest % 60:02d}"

    def _on_clock(self) -> None:
        now = self.p.now()
        minute = now.replace(second=0, microsecond=0)
        if minute != self._minute:
            self._minute = minute
            if now.date() != self._today:
                was_today = self._view_date == self._today
                self.p.roll_over()
                if was_today:
                    self._view_date = now.date()
            self.refresh()
            self._speak(self._chatter.tick(self._mascot, self._progress()))
        else:
            self._recompute_current()

    def _update_mascot(self, now: datetime) -> None:
        cur = self._current_slot
        if self._celebrate_until and now < self._celebrate_until:
            state = "celebrate"
        elif cur and cur.item.status == RUNNING:
            self._idle_since = None
            state = "overtime" if cur.overrun else ("resting" if cur.item.kind == BREAK else "working")
        else:
            self._idle_since = self._idle_since or now
            idle = (now - self._idle_since).total_seconds() / 60
            state = "sleepy" if cur and idle >= SLEEPY_AFTER_MINUTES else "idle"
        if state != self._mascot:
            self._mascot = state
            self.mascotChanged.emit()
            self._speak(self._chatter.on_mood(state, self._progress()))

    def _progress(self) -> Progress:
        try:
            today = self.p.today()
            day, slots = self.p.day(today), self.p.slots(today)
        except Exception:
            return Progress()
        tasks = [i for i in day.active if i.kind != BREAK and i.status != SKIPPED]
        ends = [s.end for s in slots if s.end > s.start]
        cur = self._current_slot
        running = cur if cur and cur.item.status == RUNNING else None
        return Progress(
            done=sum(i.status == DONE for i in tasks), total=len(tasks),
            current=running.item.title if running else None,
            left_minutes=round((running.end - self.p.now()).total_seconds() / 60)
            if running and not running.overrun else None,
            ends=f"{max(ends):%H:%M}" if ends else None,
        )

    def _speak(self, line: str | None) -> None:
        if line:
            self.mascotSaid.emit(line)

    @Slot()
    def pokeMascot(self) -> None:
        self._speak(self._chatter.poke(self._mascot, self._progress()))

    def _celebrate(self) -> None:
        self._celebrate_until = self.p.now() + timedelta(seconds=CELEBRATE_SECONDS)

    def _item_dict(self, item, slot: schedule.Slot | None, now: datetime) -> dict:
        shown = slot is not None and (slot.end > slot.start or bool(item.actual_start))
        return {
            "id": item.id,
            "uid": item.uid,
            "title": item.title,
            "kind": item.kind,
            "isBreak": item.kind == BREAK,
            "status": item.status,
            "duration": item.duration,
            "total": item.total_minutes,
            "extended": sum(item.extensions),
            "fixedStart": item.fixed_start or "",
            "notes": item.notes,
            "tagsText": " ".join(f"#{t}" for t in item.tags),
            "target": item.target or "",
            "origin": item.origin or "",
            "start": f"{slot.start:%H:%M}" if shown else "",
            "end": f"{slot.end:%H:%M}" if shown else "",
            "minutes": slot.minutes if slot else 0,
            "overrun": bool(slot and slot.overrun),
            "conflict": slot.conflict.title if slot and slot.conflict else "",
            "gapBefore": slot.gap_before if slot and item.status == PENDING and slot.start > now else 0,
            "lengthText": format_minutes(item.total_minutes),
        }

    def _stash_dict(self, item) -> dict:
        return {"id": item.id, "title": item.title, "isBreak": item.kind == BREAK, "notes": item.notes,
                "lengthText": format_minutes(item.duration), "origin": item.origin or ""}

    def _run(self, fn, *args, **kwargs):
        try:
            result = fn(*args, **kwargs)
        except (TodoError, ValueError) as e:
            self.error.emit(str(e))
            return None
        self.refresh()
        return result

    def _on(self):
        return self._view_date

    @Slot(str, result=bool)
    def quickAdd(self, text: str) -> bool:
        try:
            q = parse_quick(text)
        except ValueError as e:
            self.error.emit(str(e))
            return False
        if q.is_break:
            self.error.emit("Use the break button to add breaks")
            return False
        return self._run(self.p.add, q.title, q.duration, on=self._on(), at=q.at, tags=q.tags) is not None

    @Slot(str, int, bool, result=bool)
    def addBreak(self, label: str, minutes: int, new_label: bool) -> bool:
        item = self._run(self.p.add, label, minutes, on=self._on(), kind=BREAK, new_label=new_label)
        if item and new_label:
            self.labelsChanged.emit()
        return item is not None

    @Slot(int)
    def start(self, item_id: int) -> None:
        self._run(self.p.start, item_id, switch=True)

    @Slot(int)
    def done(self, item_id: int) -> None:
        if self._run(self.p.done, item_id, on=self._on()):
            self._celebrate()
            self._update_mascot(self.p.now())

    @Slot()
    def doneCurrent(self) -> None:
        if self._run(self.p.done):
            self._celebrate()
            self._update_mascot(self.p.now())

    @Slot(int)
    def skip(self, item_id: int) -> None:
        self._run(self.p.skip, item_id, on=self._on())

    @Slot()
    def skipCurrent(self) -> None:
        self._run(self.p.skip)

    @Slot(int)
    def reopen(self, item_id: int) -> None:
        self._run(self.p.reopen, item_id, on=self._on())

    @Slot(int)
    def remove(self, item_id: int) -> None:
        self._run(self.p.remove, item_id, on=self._on())

    @Slot(int, int)
    def extend(self, item_id: int, minutes: int) -> None:
        """item_id < 0 extends the running item."""
        kwargs = {"on": self._on()} if item_id >= 0 else {}
        result = self._run(self.p.extend, minutes, item_id if item_id >= 0 else None, **kwargs)
        if result:
            _, conflicts = result
            for slot in conflicts:
                self.warning.emit(f"{slot.conflict.title} now overlaps {slot.item.title} at {slot.item.fixed_start}")

    @Slot()
    def askExtend(self) -> None:
        self.extendRequested.emit()

    @Slot(int, int)
    def reorder(self, item_id: int, position: int) -> None:
        self._run(self.p.reorder, item_id, position, on=self._on())

    @Slot(int, str, str, str, str, str)
    def edit(self, item_id: int, title: str, duration: str, at: str, notes: str, tags: str) -> None:
        try:
            minutes = parse_duration(duration) if duration.strip() else None
            fixed = parse_time(at) if at.strip() else None
        except ValueError as e:
            self.error.emit(str(e))
            return
        self._run(self.p.edit, item_id, on=self._on(), title=title.strip() or None, duration=minutes, at=fixed,
                  notes=notes, tags=parse_tags(tags))

    @Slot(int, str)
    def moveTo(self, item_id: int, iso_date: str) -> None:
        to = date.fromisoformat(iso_date)
        if self._run(self.p.move, item_id, to, on=self._on()):
            self.info.emit(f"Moved to {self._day_title(to)}")

    @Slot(int)
    def moveToTomorrow(self, item_id: int) -> None:
        self.moveTo(item_id, (self._view_date + timedelta(days=1)).isoformat())

    @Slot(int)
    def stashItem(self, item_id: int) -> None:
        if self._run(self.p.stash, item_id, on=self._on()):
            self.info.emit("Stashed")

    @Slot(int, str)
    def unstash(self, stash_id: int, iso_date: str) -> None:
        to = date.fromisoformat(iso_date) if iso_date else self._view_date
        if self._run(self.p.unstash, stash_id, to):
            self.info.emit(f"Added to {self._day_title(to)}")

    @Slot(str)
    def addBreakLabel(self, label: str) -> None:
        if self._run(self.p.add_break_label, label) is not None:
            self.labelsChanged.emit()

    @Slot(str)
    def removeBreakLabel(self, label: str) -> None:
        if self._run(self.p.remove_break_label, label) is not None:
            self.labelsChanged.emit()

    @Slot()
    def goToday(self) -> None:
        self._set_view_date(self._today.isoformat())

    @Slot(int)
    def shiftDay(self, delta: int) -> None:
        self._set_view_date((self._view_date + timedelta(days=delta)).isoformat())

    @Slot(int, int, int, result="QVariantList")
    def month(self, year: int, month: int, first_weekday: int) -> list[dict]:
        """Day cells for the calendar, padded to whole weeks. first_weekday uses Qt numbering (1 = Monday, 7 = Sunday)."""
        recorded = set(self.p.days())
        cells = []
        for d in calendar.Calendar(first_weekday - 1).itermonthdates(year, month):
            cell = {"date": d.isoformat(), "day": d.day, "inMonth": d.month == month,
                    "isToday": d == self._today, "total": 0, "done": 0, "state": "empty"}
            if d in recorded:
                day = self.p.day(d)
                tasks = [i for i in day.active if i.kind != BREAK and i.status != SKIPPED]
                cell["total"] = len(tasks)
                cell["done"] = sum(i.status == DONE for i in tasks)
                if tasks:
                    cell["state"] = "complete" if cell["done"] == len(tasks) else (
                        "partial" if d < self._today else "planned")
            cells.append(cell)
        return cells

    @Slot(str, result=str)
    def dayTitle(self, iso_date: str) -> str:
        return self._day_title(date.fromisoformat(iso_date))

    def _on_rollover(self, rolled: list[Rolled]) -> None:
        self.rolledOver.emit(len(rolled))
