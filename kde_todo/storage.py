"""Reading and writing the JSON records and their Markdown copies.

Callers hold Store.lock for each read-modify-write, so the GUI and the CLI can
write at the same time.
"""

import json
import os
from datetime import date
from pathlib import Path

from filelock import FileLock
from platformdirs import user_data_path

from .model import Day, Stash

DEFAULT_CONFIG = {
    "day_start": "09:00",
    "default_duration": 30,
    "break_labels": ["Eating", "Resting", "Walk", "Coffee"],
    "mascot": "Mochi",
}


def data_dir() -> Path:
    return Path(os.environ.get("KDE_TODO_DATA_DIR") or user_data_path("kde-todo"))


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")  # safe: writers hold the lock
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class Store:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else data_dir()
        self.root.mkdir(parents=True, exist_ok=True)
        self.days_dir = self.root / "days"
        self.lock = FileLock(self.root / ".lock")  # re-entrant

    def day_path(self, d: date, ext: str = "json") -> Path:
        return self.days_dir / f"{d:%Y}" / f"{d:%m}" / f"{d.isoformat()}.{ext}"

    def list_days(self) -> list[date]:
        return sorted(date.fromisoformat(p.stem) for p in self.days_dir.glob("*/*/????-??-??.json"))

    def _read(self, path: Path) -> str | None:
        return path.read_text(encoding="utf-8") if path.exists() else None

    def load_day(self, d: date) -> Day:
        text = self._read(self.day_path(d))
        return Day.model_validate_json(text) if text else Day(date=d)

    def save_day(self, day: Day, markdown: str) -> None:
        write_atomic(self.day_path(day.date), day.model_dump_json(indent=2) + "\n")
        write_atomic(self.day_path(day.date, "md"), markdown)

    def load_stash(self) -> Stash:
        text = self._read(self.root / "stash.json")
        return Stash.model_validate_json(text) if text else Stash()

    def save_stash(self, stash: Stash, markdown: str) -> None:
        write_atomic(self.root / "stash.json", stash.model_dump_json(indent=2) + "\n")
        write_atomic(self.root / "stash.md", markdown)

    def _load_json(self, name: str) -> dict:
        text = self._read(self.root / name)
        return json.loads(text) if text else {}

    def _save_json(self, name: str, data: dict) -> None:
        write_atomic(self.root / name, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    def load_config(self) -> dict:
        return DEFAULT_CONFIG | self._load_json("config.json")

    def save_config(self, config: dict) -> None:
        self._save_json("config.json", config)

    def load_state(self) -> dict:
        return self._load_json("state.json")

    def save_state(self, state: dict) -> None:
        self._save_json("state.json", state)
