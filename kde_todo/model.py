"""Data model: items, days and the stash."""

import datetime as dt
import uuid

from pydantic import BaseModel, Field

TASK = "task"
BREAK = "break"

PENDING = "pending"
RUNNING = "running"
DONE = "done"
SKIPPED = "skipped"
ROLLED = "rolled"
MOVED = "moved"
STASHED = "stashed"

# Statuses whose item still occupies a slot in its day's timeline.
ACTIVE = (PENDING, RUNNING, DONE, SKIPPED)
# Statuses whose item has left the day (kept only as history).
GONE = (ROLLED, MOVED, STASHED)
UNFINISHED = (PENDING, RUNNING)


class Item(BaseModel):
    id: int = 0
    title: str
    duration: int  # planned minutes, without extensions
    kind: str = TASK
    status: str = PENDING
    fixed_start: str | None = None  # "HH:MM", anchors the item in the timeline
    notes: str = ""
    tags: list[str] = []
    extensions: list[int] = []  # minutes added while running
    actual_start: str | None = None  # ISO datetime
    actual_end: str | None = None
    target: str | None = None  # where a GONE item went: a date, or "stash"
    origin: str | None = None  # where this item came from: a date, or "stash"
    uid: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])

    @property
    def total_minutes(self) -> int:
        return self.duration + sum(self.extensions)

    def fresh_copy(self, *, origin: str, keep_fixed: bool = True) -> "Item":
        """A new pending copy of this item, for rolling, moving or stashing."""
        fields = self.model_dump(include={"title", "duration", "kind", "notes", "tags", "fixed_start"})
        return Item(**fields | ({} if keep_fixed else {"fixed_start": None}), origin=origin)


class _Items:
    def add(self, item: Item, position: int | None = None) -> Item:
        item.id = max((i.id for i in self.items), default=0) + 1
        self.items.insert(len(self.items) if position is None else position, item)
        return item

    def get(self, item_id: int | str) -> Item:
        for item in self.items:
            if str(item.id) == str(item_id) or item.uid == str(item_id):
                return item
        raise KeyError(item_id)

    def remove(self, item: Item) -> None:
        self.items.remove(item)


class Day(_Items, BaseModel):
    version: int = 1
    date: dt.date
    items: list[Item] = []

    @property
    def running(self) -> Item | None:
        return next((i for i in self.items if i.status == RUNNING), None)

    @property
    def active(self) -> list[Item]:
        return [i for i in self.items if i.status in ACTIVE]


class Stash(_Items, BaseModel):
    version: int = 1
    items: list[Item] = []
