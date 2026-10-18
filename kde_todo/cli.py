"""kde-todo command-line interface."""

import calendar
import json
import sys
from datetime import date, timedelta
from functools import cache
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from . import markdown, schedule
from .model import BREAK, DONE, GONE, MOVED, PENDING, ROLLED, RUNNING, SKIPPED, STASHED, TASK
from .parse import format_minutes, parse_date, parse_duration, parse_quick, parse_tags, parse_time
from .planner import Planner, TodoError

app = typer.Typer(help="Time-blocked daily todos.", add_completion=False, pretty_exceptions_enable=False)
out = Console(highlight=False, soft_wrap=True)
err = Console(stderr=True, highlight=False, soft_wrap=True)

DateOpt = Annotated[Optional[str], typer.Option("--date", "-d", help="day to act on (default: today)")]
IdArg = Annotated[Optional[str], typer.Argument(help="item ID (default: the running item)")]


@cache
def planner() -> Planner:
    return Planner()


def to_date(text: str | None) -> date:
    return parse_date(text, planner().today()) if text else planner().today()


def maybe_date(text: str | None) -> date | None:
    return to_date(text) if text else None


def title(item) -> str:
    return ("☕ " if item.kind == BREAK else "") + escape(item.title)


def warn(slots: list[schedule.Slot]) -> None:
    for slot in schedule.conflicts(slots):
        err.print(f"[red]⚠ {escape(slot.conflict.title)} now runs into fixed {escape(slot.item.title)} "
                  f"at {slot.item.fixed_start}[/]")


def print_day(d: date, show_gone: bool = True) -> None:
    p = planner()
    day, now = p.day(d), p.now()
    slots = {s.item.uid: s for s in p.slots(d)}
    tasks = [i for i in day.active if i.kind != BREAK and i.status != SKIPPED]
    done = sum(i.status == DONE for i in tasks)
    out.print(f"[bold]{d:%a %d %b %Y}[/]" + (f"  · now {now:%H:%M}" if d == now.date() else "")
              + f"[dim]  · done {done}/{len(tasks)}[/]")
    if not day.items:
        out.print("[dim]  nothing planned yet, try `kde-todo add`[/]")
        return

    grid = Table.grid(padding=(0, 1), pad_edge=True)
    grid.add_column(justify="right")
    for item in day.items:
        if item.status in GONE and not show_gone:
            continue
        slot = slots.get(item.uid)
        span = f"{slot.start:%H:%M} - {slot.end:%H:%M}" if slot and (slot.end > slot.start or item.actual_start) else ""
        if slot and slot.gap_before and item.status == PENDING and slot.start > now:
            grid.add_row("", "", "", f"[dim]┊ {format_minutes(slot.gap_before)} unplanned[/]")

        extras = [f"@{item.fixed_start}"] if item.fixed_start else []
        extras += [f"+{format_minutes(sum(item.extensions))}"] if item.extensions else []
        extras += [f"#{t}" for t in item.tags]
        label = title(item) + (f"  [dim]{escape(' '.join(extras))}[/]" if extras else "")

        if item.status == RUNNING:
            left = round((slot.end - now).total_seconds() / 60)
            state = f"[red]over {format_minutes(-left)}[/]" if slot.overrun else f"[yellow]{format_minutes(left)} left[/]"
            row = ["[yellow]▶[/]", span, f"[bold]{label}[/]  {state}"]
        elif item.status == DONE:
            row = ["[green]✓[/]", f"[dim]{span}[/]", label]
        elif item.status == PENDING:
            row = ["·", span, label]
        else:
            mark = {SKIPPED: "-", ROLLED: "→", MOVED: "→", STASHED: "⇣"}[item.status]
            where = f" to {item.target}" if item.status in (ROLLED, MOVED) else ""
            row = [f"[dim]{mark}[/]", "", f"[dim]{title(item)}  ({item.status}{where})[/]"]
        if slot and slot.conflict:
            row[2] += f"  [red]⚠ overlapped by {escape(slot.conflict.title)}[/]"
        grid.add_row(str(item.id), *row)
    out.print(grid)


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        print_day(planner().today())


@app.command()
def add(text: Annotated[list[str], typer.Argument(help="e.g. Write report 45m @14:00 #work, or: break Eating 30m")],
        duration: Annotated[Optional[str], typer.Option("--duration", "-t", help="45m, 1h30m, ...")] = None,
        at: Annotated[Optional[str], typer.Option(help="fixed start time (HH:MM)")] = None,
        brk: Annotated[bool, typer.Option("--break", help="add a break; the text is its label")] = False,
        new_label: Annotated[bool, typer.Option(help="allow creating a new break label")] = False,
        notes: Annotated[str, typer.Option("--notes", "-n")] = "",
        day: DateOpt = None):
    """Add an item."""
    q, on = parse_quick(" ".join(text)), to_date(day)
    item = planner().add(q.title, parse_duration(duration) if duration else q.duration, on=on,
                         at=parse_time(at) if at else q.at, kind=BREAK if brk or q.is_break else TASK,
                         notes=notes, tags=q.tags, new_label=new_label)
    out.print(f"added #{item.id} {escape(item.title)} ({format_minutes(item.duration)})")
    warn(planner().slots(on))


@app.command("list")
def list_(when: Annotated[Optional[str], typer.Argument()] = None,
          week: Annotated[bool, typer.Option("--week", "-w", help="show 7 days")] = False,
          hide_gone: Annotated[bool, typer.Option(help="hide rolled, moved and stashed items")] = False):
    """Show a day's timeline."""
    for n in range(7 if week else 1):
        print_day(to_date(when) + timedelta(days=n), not hide_gone)
        if week:
            out.print()


app.command("ls", hidden=True)(list_)


@app.command()
def show(when: Annotated[Optional[str], typer.Argument()] = None,
         fmt: Annotated[str, typer.Option("--format", "-f", help="md or json")] = "md"):
    """Print a day as Markdown or JSON."""
    p, d = planner(), to_date(when)
    if fmt == "json":
        print(p.day(d).model_dump_json(indent=2))
    else:
        print(markdown.render_day(p.day(d), p.slots(d), p.now()), end="")


@app.command()
def now(as_json: Annotated[bool, typer.Option("--json")] = False):
    """What's running or due right now."""
    p = planner()
    slot, current = p.current(), p.now()
    left = round((slot.end - current).total_seconds() / 60) if slot else 0
    if as_json:
        print(json.dumps(slot and {"id": slot.item.id, "title": slot.item.title, "status": slot.item.status,
                                   "start": slot.start.isoformat(), "end": slot.end.isoformat(),
                                   "remaining_minutes": left, "overrun": slot.overrun}, ensure_ascii=False))
    elif not slot:
        out.print("nothing running")
    elif slot.item.status == RUNNING:
        state = f"over by {format_minutes(-left)}" if slot.overrun else f"{format_minutes(left)} left"
        out.print(f"▶ {escape(slot.item.title)}: {state} (until {slot.end:%H:%M})")
    else:
        out.print(f"due: #{slot.item.id} {escape(slot.item.title)} (since {slot.start:%H:%M}), "
                  f"run `kde-todo start {slot.item.id}`")


@app.command()
def start(item_id: Annotated[str, typer.Argument(metavar="ID")],
          switch: Annotated[bool, typer.Option(help="finish whatever is running first")] = False):
    """Start an item."""
    out.print(f"▶ started {escape(planner().start(item_id, switch=switch).title)}")


@app.command()
def done(item_id: IdArg = None, day: DateOpt = None):
    """Finish an item."""
    out.print(f"✓ {escape(planner().done(item_id, on=maybe_date(day)).title)}")


@app.command()
def skip(item_id: IdArg = None, day: DateOpt = None):
    """Skip an item."""
    out.print(f"- skipped {escape(planner().skip(item_id, on=maybe_date(day)).title)}")


@app.command()
def reopen(item_id: Annotated[str, typer.Argument(metavar="ID")], day: DateOpt = None):
    """Mark a done or skipped item pending again."""
    out.print(f"reopened {escape(planner().reopen(item_id, on=to_date(day)).title)}")


@app.command()
def extend(duration: Annotated[str, typer.Argument(help="e.g. 15m")], item_id: IdArg = None, day: DateOpt = None):
    """Add time to an item, pushing later items back."""
    item, conflicts = planner().extend(parse_duration(duration), item_id, on=maybe_date(day))
    out.print(f"extended {escape(item.title)} to {format_minutes(item.total_minutes)}")
    warn(conflicts)


@app.command()
def edit(item_id: Annotated[str, typer.Argument(metavar="ID")],
         new_title: Annotated[Optional[str], typer.Option("--title")] = None,
         duration: Annotated[Optional[str], typer.Option("--duration", "-t")] = None,
         at: Annotated[Optional[str], typer.Option(help="fixed start (HH:MM), or 'none' to clear")] = None,
         notes: Annotated[Optional[str], typer.Option("--notes", "-n")] = None,
         tags: Annotated[Optional[str], typer.Option(help="replace the tags, e.g. 'work code' ('' clears them)")] = None,
         day: DateOpt = None):
    """Change an item."""
    fixed = False if at is None else None if at in ("", "none", "-") else parse_time(at)
    item = planner().edit(item_id, on=to_date(day), title=new_title, at=fixed, notes=notes,
                          tags=None if tags is None else parse_tags(tags),
                          duration=parse_duration(duration) if duration else None)
    out.print(f"updated #{item.id} {escape(item.title)}")


@app.command()
def mv(item_id: Annotated[str, typer.Argument(metavar="ID")],
       position: Annotated[int, typer.Argument(help="1-based position among the day's items")], day: DateOpt = None):
    """Reorder an item within its day."""
    item = planner().reorder(item_id, position - 1, on=to_date(day))
    out.print(f"moved {escape(item.title)} to position {position}")


@app.command()
def rm(item_id: Annotated[str, typer.Argument(metavar="ID")], day: DateOpt = None):
    """Delete an item."""
    out.print(f"removed {escape(planner().remove(item_id, on=to_date(day)).title)}")


@app.command()
def move(item_id: Annotated[str, typer.Argument(metavar="ID")],
         to: Annotated[str, typer.Argument(help="tomorrow, fri, +3 or 2026-10-25")], day: DateOpt = None):
    """Send a pending item to another day."""
    target = to_date(to)
    item = planner().move(item_id, target, on=to_date(day))
    out.print(f"→ moved {escape(item.title)} to {target:%a %d %b}")


@app.command()
def stash(item_id: Annotated[Optional[str], typer.Argument(metavar="[ID]", help="no ID: list the stash")] = None,
          day: DateOpt = None):
    """Stash an item away, or list the stash."""
    if item_id:
        item = planner().stash(item_id, on=to_date(day))
        out.print(f"⇣ stashed {escape(item.title)} (stash #{item.id})")
        return
    items = planner().stash_items().items
    out.print("[bold]Stash[/]" if items else "[bold]Stash[/]\n[dim]  empty[/]")
    for item in items:
        origin = f"  [dim]from {item.origin}[/]" if item.origin else ""
        out.print(f"  {item.id:>2} ⇣ {title(item)}  [dim]{format_minutes(item.duration)}[/]{origin}")


@app.command()
def unstash(stash_id: Annotated[str, typer.Argument(metavar="ID", help="stash item ID")],
            to: Annotated[Optional[str], typer.Argument(help="day to put it on (default: today)")] = None):
    """Bring a stashed item back into a day."""
    target = to_date(to)
    item = planner().unstash(stash_id, target)
    out.print(f"⇡ {escape(item.title)} → {target:%a %d %b} (#{item.id})")


@app.command()
def labels(action: Annotated[Optional[str], typer.Argument(help="add or rm")] = None,
           name: Annotated[Optional[str], typer.Argument()] = None):
    """List or manage break labels."""
    p = planner()
    if action not in (None, "add", "rm") or (action and not name):
        raise typer.BadParameter("use: labels [add|rm NAME]")
    found = {"add": p.add_break_label, "rm": p.remove_break_label}[action](name) if action else p.break_labels()
    for label in found:
        out.print(f"☕ {escape(label)}")


@app.command()
def cal(month: Annotated[Optional[str], typer.Argument(help="any date in the month")] = None):
    """Month overview."""
    p = planner()
    today, first = p.today(), to_date(month).replace(day=1)
    recorded = set(p.days())
    table = Table(title=f"{first:%B %Y}", box=None, padding=(0, 1), caption="[green]✓[/] all done   [yellow]•[/] unfinished")
    for name in calendar.day_abbr:
        table.add_column(name[:2], justify="right")
    for week in calendar.Calendar().monthdatescalendar(first.year, first.month):
        cells = []
        for d in week:
            tasks = [i for i in p.day(d).active if i.kind != BREAK and i.status != SKIPPED] if d in recorded else []
            cell = "" if d.month != first.month else (
                f"[green]{d.day}✓[/]" if tasks and all(i.status == DONE for i in tasks)
                else f"[yellow]{d.day}•[/]" if tasks else str(d.day))
            cells.append(f"[bold underline]{cell}[/]" if d == today else cell)
        table.add_row(*cells)
    out.print(table)


@app.command()
def export(fmt: Annotated[str, typer.Option("--format", "-f", help="md or json")] = "md",
           since: Optional[str] = None, until: Optional[str] = None,
           output: Annotated[Optional[str], typer.Option("--output", "-o")] = None):
    """Export records as Markdown or JSON."""
    p = planner()
    days = [d for d in p.days() if (not since or d >= to_date(since)) and (not until or d <= to_date(until))]
    if fmt == "json":
        text = json.dumps({"days": [p.day(d).model_dump(mode="json") for d in days],
                           "stash": p.stash_items().model_dump(mode="json")}, indent=2, ensure_ascii=False) + "\n"
    else:
        text = "\n".join([*(markdown.render_day(p.day(d), p.slots(d), p.now()) for d in days),
                          markdown.render_stash(p.stash_items())])
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(text)
        out.print(f"exported {len(days)} day(s) to {escape(output)}")
    else:
        print(text, end="")


@app.command()
def gui(hidden: Annotated[bool, typer.Option(help="start in the tray only (for autostart)")] = False):
    """Open the app, or bring the running one forward."""
    from .gui.app import main as gui_main
    raise typer.Exit(gui_main([sys.argv[0]], hidden=hidden))


@app.command()
def path():
    """Print the data directory."""
    print(planner().store.root)


def main() -> None:
    try:
        app()
    except (TodoError, ValueError) as e:
        err.print(f"[red]kde-todo: {escape(str(e))}[/]")
        sys.exit(1)
