# kde-todo spec, v0.1

A daily todo app for KDE Plasma 6 where every item is a time block. It has a tray icon, notifications
and a CLI. Records are JSON files, with a Markdown copy written next to each one.

## Concepts

- **Day**: one list per calendar date, stored in one file per date.
- **Item**: a block in a day's timeline.
  - `kind`: `task` or `break`
  - `title`: free text for tasks. For breaks, one of the break labels.
  - `duration` in minutes, optional `fixed_start` (HH:MM), `notes`, `tags`
  - `status`: `pending`, `running`, `done`, `skipped`, `rolled`, `moved` or `stashed`
  - `actual_start`, `actual_end`, and `extensions` (minutes added while it was running)
- **Schedule**: items run back to back in list order, starting at the day start time. An item with a
  `fixed_start` stays at that time and is never pushed. There are no implicit gaps. Idle time is either a
  break item or shows up as unplanned time.
- **Break labels**: a short list of reusable labels (defaults: Eating, Resting, Walk, Coffee). A break
  must use one of them. Adding a new label is a separate step on purpose, to keep the list short. The day
  view shows total break time.
- **Stash**: a place for items that don't belong to any day yet. Stashing removes an item from its day's
  timeline. You can later put it on any day. Stashed items never roll over.

## Features

1. **Add item**: a quick-add bar that understands `Write report 45m`, `Standup @9:30 15m` and tags like
   `#work`. In the day view, tags show as coloured pills (the same tag always gets the same theme colour),
   and done items get a "done" pill.
2. **Time blocks**: each item has a duration and an optional fixed start. Rows can be dragged to reorder.
3. **System clock**: shows the running item with a countdown, and flags overruns. On today's view,
   pending items never start in the past, so the timeline moves with the clock.
4. **Extend**: add 5, 15 or 30 minutes (or any amount) to the running item. Later items move back. If an
   item would run into a fixed-time item, the app warns you.
5. **Tray**: the icon draws a progress ring for the running block. The menu has Done, Extend, Skip,
   Start, Quick add, Show/Hide and Quit.
6. **Theming**: uses the Plasma colour scheme and accent colour, and follows changes live.
7. **Mascot**: a 16x16 pixel-art character (Mochi the cat by default; Blip, Pip, Tock or Wisp can be picked
   in Settings, saved as `mascot` in `config.json`). Its body is the theme's accent colour and its outlines and
   eyes are mixed from the theme's darkest colour, so it recolours live when the colour scheme changes. It
   animates per mood: `idle`, `working`, `resting`, `celebrate`, `overtime`, `sleepy`.
   - **Speech bubble**: it always says something on `celebrate` (often about progress, like "3 of 5 done")
     and on `overtime`, sometimes when starting work, a break or getting sleepy, and otherwise once every
     15 to 30 minutes. Casual remarks are at least 2 minutes apart. Clicking the mascot makes it talk.
     The bubble sits under the mascot with its tail pointing up and wraps to the mascot's column. Task
     names longer than 22 characters are replaced by the mascot's own label for them ("the current
     task" for Pip, "the thing we're hunting" for Mochi). It is drawn in pixel steps and its text types
     out in DepartureMono at 11px, then stays for
     about 2 to 3 seconds. Clicking it skips the typing, a second click closes it.
   - **Voices**: each character has its own lines for every mood and progress remark. Mochi is a lazy,
     smug cat; Blip a bouncy slime; Pip a literal robot giving status reports; Tock a punctual, fussy clock;
     Wisp a calm flame that talks in fire metaphors.
   - **Speech timing**: text types out with pauses like speech. `<#!delay-300-ms!#>` in a line pauses
     there for that long. Without a marker, commas get a short pause and sentence ends a longer one.
8. **Calendar**: a month view with done/total counts per day. Clicking a day opens it.
9. **Rollover and moving**
   - **Rollover**: at local midnight, pending tasks move to the new day and the originals are marked
     `rolled`. Breaks don't roll over, and rolled items lose their fixed start time. If the app wasn't
     running at midnight, the next run (GUI or CLI) rolls over every past day it missed.
   - **Move**: send a pending item to another date. The original is marked `moved`.
   - **Stash and unstash**: see Concepts.
   - An item still running at midnight stays on the day it started.
10. **CLI**: `kde-todo` (see below). Works with or without the GUI running.
11. **Notifications**: only for started items, three per item: when it starts (time range and block
    length), at the halfway point (time left), and when the block runs out. The last one stays on screen
    and asks: Done, +5 min, +15 min, or Extend… (opens the app to pick any duration). Extending gives the
    item a new end, so "time's up" comes again at that point. Items that haven't started never notify.
    A rollover notice appears once a day when items carry over. All respect Do Not Disturb.
12. **Storage**: JSON is the source of truth. The Markdown copy is rewritten on every save.

## Storage

```text
~/.local/share/kde-todo/
  days/2026/10/2026-10-18.json   source of truth
  days/2026/10/2026-10-18.md     generated, don't edit
  stash.json, stash.md
  config.json                    day start, default duration, break labels, mascot
```

Markdown example:

```markdown
# Sunday, 18 Oct 2026
- [x] 09:00 - 09:45  Write report  (+15m)
- [ ] 09:45 - 10:15  ☕ Break: Eating
- [ ] 14:00 - 14:30  Standup  📌
```

Files are written to a temp file and renamed into place, under a lock on the data folder. The GUI and
any number of CLI calls can write at the same time without corrupting anything.

## CLI

```text
kde-todo                              today's timeline (same as `list`)
kde-todo add Write report 45m @14:00 #work [--date fri] [--notes ...]
kde-todo add break Eating 30m [--new-label]
kde-todo list|ls [DATE] [--week]      kde-todo show [DATE] [-f md|json]
kde-todo now [--json]                 what's running or due (useful for status bars)
kde-todo start ID [--switch]          kde-todo done|skip [ID]     kde-todo reopen ID
kde-todo extend 15m [ID]              defaults to the running item
kde-todo edit ID [--title --duration --at --notes --tags]
kde-todo mv ID POS                    reorder        kde-todo rm ID
kde-todo move ID DATE                 kde-todo stash [ID]          kde-todo unstash ID [DATE]
kde-todo labels [add|rm NAME]         kde-todo cal [MONTH]
kde-todo export [-f md|json] [--since D] [--until D] [-o FILE]
kde-todo gui [--hidden]
```

DATE can be anything dateparser understands (`tomorrow`, `fri`, `oct 25`, `in 3 days`, `2026-10-25`),
or `+3` / `-1` for a day offset.

The CLI and the GUI use the same `Planner` class. The CLI writes the files directly. The GUI watches the
data folder, reloads when something changes, and checks notifications again.

## Stack

- Python 3.14 with PySide6 and QML/Kirigami, all from Fedora packages. Don't install PySide6 from pip.
- `python3-kf6-knotifications` for notifications, configured by `kde-todo.notifyrc`
- `python3-kf6-kstatusnotifieritem` for the tray icon
- `kf6-kirigami-addons` for the date picker. KI18n has no Python bindings on Fedora, so `gui/i18n.py`
  provides the `i18n()` functions it calls (English only).
- `typer` and `rich` for the CLI. `QFileSystemWatcher` picks up CLI changes in the GUI.
- `pydantic` for the record models, `filelock` for the data folder lock, `platformdirs` for the data path,
  `dateparser` for dates typed by the user.
- `QLocalServer` keeps a single instance. `install.sh` adds `~/.local/bin/kde-todo`, an app menu entry and
  autostart.
- If a virtualenv is ever needed, create it with `--system-site-packages`.

## Out of scope for v1

CalDAV or Google Calendar sync, repeating tasks, syncing between devices.
