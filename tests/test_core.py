import json
import tempfile
import unittest
from datetime import date, datetime, timedelta

from kde_todo import schedule
from kde_todo.model import BREAK, DONE, MOVED, PENDING, ROLLED, RUNNING, STASHED
from kde_todo.parse import parse_date, parse_duration, parse_quick, parse_tags, parse_time
from kde_todo.planner import Planner, TodoError
from kde_todo.storage import Store


class Clock:
    def __init__(self, dt: datetime):
        self.dt = dt

    def __call__(self):
        return self.dt

    def advance(self, **kw):
        self.dt += timedelta(**kw)


def local(y, mo, d, h=0, mi=0):
    return datetime(y, mo, d, h, mi).astimezone()


class PlannerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)
        self.clock = Clock(local(2026, 10, 18, 9, 0))
        self.p = Planner(self.store, self.clock)

    def tearDown(self):
        self.tmp.cleanup()

    def spans(self, d=None):
        return [(s.item.title, f"{s.start:%H:%M}", f"{s.end:%H:%M}") for s in self.p.slots(d)]


class TestParse(unittest.TestCase):
    def test_duration(self):
        self.assertEqual(parse_duration("45m"), 45)
        self.assertEqual(parse_duration("1h30m"), 90)
        self.assertEqual(parse_duration("1.5h"), 90)
        self.assertEqual(parse_duration("2h"), 120)
        self.assertEqual(parse_duration("20"), 20)
        for bad in ("", "abc", "0m", "h"):
            with self.assertRaises(ValueError):
                parse_duration(bad)

    def test_time(self):
        self.assertEqual(parse_time("9"), "09:00")
        self.assertEqual(parse_time("@14:05"), "14:05")
        with self.assertRaises(ValueError):
            parse_time("25:00")

    def test_date(self):
        today = date(2026, 10, 18)  # a Sunday
        self.assertEqual(parse_date("tomorrow", today), date(2026, 10, 19))
        self.assertEqual(parse_date("+3", today), date(2026, 10, 21))
        self.assertEqual(parse_date("fri", today), date(2026, 10, 23))
        self.assertEqual(parse_date("sunday", today), date(2026, 10, 25))
        self.assertEqual(parse_date("10-01", today), date(2027, 10, 1))
        self.assertEqual(parse_date("2026-11-02", today), date(2026, 11, 2))

    def test_tags(self):
        self.assertEqual(parse_tags("#work, code  #Work ##review"), ["work", "code", "review"])
        self.assertEqual(parse_tags("  "), [])

    def test_quick(self):
        q = parse_quick("Standup @9:30 15m #work")
        self.assertEqual((q.title, q.at, q.duration, q.tags), ("Standup", "09:30", 15, ["work"]))
        q = parse_quick("break Eating 30m")
        self.assertTrue(q.is_break)
        self.assertEqual(q.title, "Eating")
        self.assertEqual(parse_quick("Read 2 chapters 1h").title, "Read 2 chapters")


class TestSchedule(PlannerTest):
    def test_back_to_back_from_now(self):
        self.p.add("A", 30)
        self.p.add("B", 45)
        self.clock.advance(minutes=10)  # 09:10, nothing started yet
        self.assertEqual(self.spans(), [("A", "09:10", "09:40"), ("B", "09:40", "10:25")])

    def test_future_day_starts_at_day_start(self):
        tomorrow = date(2026, 10, 19)
        self.p.add("A", 60, on=tomorrow)
        self.assertEqual(self.spans(tomorrow), [("A", "09:00", "10:00")])

    def test_fixed_item_and_gap(self):
        self.p.add("A", 30)
        self.p.add("Meeting", 30, at="11:00")
        self.p.add("B", 15)
        slots = self.p.slots()
        self.assertEqual(self.spans(), [("A", "09:00", "09:30"), ("Meeting", "11:00", "11:30"),
                                        ("B", "11:30", "11:45")])
        self.assertEqual(slots[1].gap_before, 90)

    def test_extend_pushes_later_items(self):
        self.p.add("A", 30)
        self.p.add("B", 30)
        self.p.start(1)
        self.p.extend(15)
        self.assertEqual(self.spans(), [("A", "09:00", "09:45"), ("B", "09:45", "10:15")])

    def test_overrun_pushes_later_items(self):
        self.p.add("A", 30)
        self.p.add("B", 30)
        self.p.start(1)
        self.clock.advance(minutes=50)
        slots = self.p.slots()
        self.assertTrue(slots[0].overrun)
        self.assertEqual(self.spans(), [("A", "09:00", "09:50"), ("B", "09:50", "10:20")])

    def test_extend_into_fixed_reports_conflict(self):
        self.p.add("A", 50)
        self.p.add("Meeting", 30, at="10:00")
        self.p.start(1)
        _, conflicts = self.p.extend(20)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].item.title, "Meeting")
        self.assertEqual(conflicts[0].conflict.title, "A")

    def test_current(self):
        self.p.add("A", 30)
        self.assertEqual(self.p.current().item.title, "A")  # due
        self.p.start(1)
        self.assertEqual(self.p.current().item.status, RUNNING)


class TestRunning(PlannerTest):
    def test_only_one_running(self):
        self.p.add("A", 30)
        self.p.add("B", 30)
        self.p.start(1)
        with self.assertRaises(TodoError):
            self.p.start(2)
        self.p.start(2, switch=True)
        day = self.p.day()
        self.assertEqual([i.status for i in day.items], [DONE, RUNNING])

    def test_done_defaults_to_running(self):
        self.p.add("A", 30)
        self.p.start(1)
        self.clock.advance(minutes=20)
        self.assertEqual(self.p.done().status, DONE)
        self.assertEqual(self.spans(), [("A", "09:00", "09:20")])
        with self.assertRaises(TodoError):
            self.p.done()

    def test_start_reorders_after_finished(self):
        for t in "ABC":
            self.p.add(t, 10)
        self.p.start(3)
        self.assertEqual([i.title for i in self.p.day().items], ["C", "A", "B"])


class TestOrder(PlannerTest):
    def titles(self):
        return [i.title for i in self.p.day().items]

    def setUp(self):
        super().setUp()
        for t in "ABC":
            self.p.add(t, 10)

    def test_pending_cannot_move_above_done(self):
        self.p.done(1)                     # A done
        self.p.reorder(3, 0)               # try to put C first
        self.assertEqual(self.titles(), ["A", "C", "B"])

    def test_done_items_cannot_be_reordered(self):
        self.p.done(1)
        with self.assertRaises(TodoError):
            self.p.reorder(1, 2)

    def test_done_in_the_middle_moves_up(self):
        self.p.done(2)                     # B done while A is still pending
        self.assertEqual(self.titles(), ["B", "A", "C"])
        self.p.skip(3)
        self.assertEqual(self.titles(), ["B", "C", "A"])

    def test_reopen_goes_to_top_of_pending(self):
        self.p.done(1); self.p.done(2)
        self.p.reopen(1)
        self.assertEqual(self.titles(), ["B", "A", "C"])

    def test_history_rows_keep_their_place(self):
        self.p.stash(2)                    # B stays as a "stashed" row between A and C
        self.p.done(3)
        self.assertEqual(self.titles(), ["C", "B", "A"])
        self.assertEqual(self.p.day().items[1].status, STASHED)


class TestEdit(PlannerTest):
    def test_edit_replaces_tags(self):
        self.p.add("A", 10, tags=["work"])
        self.p.edit(1, tags=["work", "code"])
        self.assertEqual(self.p.day().items[0].tags, ["work", "code"])
        self.p.edit(1, title="B")              # tags untouched when not given
        self.assertEqual(self.p.day().items[0].tags, ["work", "code"])
        self.p.edit(1, tags=[])
        self.assertEqual(self.p.day().items[0].tags, [])


class TestBreaks(PlannerTest):
    def test_labels_are_deliberate(self):
        item = self.p.add("eating", 30, kind=BREAK)
        self.assertEqual(item.title, "Eating")  # normalised to the existing label
        with self.assertRaises(TodoError):
            self.p.add("Gaming", 30, kind=BREAK)
        self.p.add("Gaming", 30, kind=BREAK, new_label=True)
        self.assertIn("Gaming", self.p.break_labels())
        self.p.add("Gaming", 30, kind=BREAK)  # now allowed without the flag


class TestRollover(PlannerTest):
    def test_midnight_rollover(self):
        self.p.add("Done thing", 30)
        self.p.add("Unfinished", 30, at="14:00")
        self.p.add("Eating", 30, kind=BREAK)
        self.p.done(1)

        rolled = []
        self.p.on_rollover = rolled.append
        self.clock.dt = local(2026, 10, 19, 0, 0)
        self.p.roll_over()

        old = self.p.day(date(2026, 10, 18))
        self.assertEqual([i.status for i in old.items], [DONE, ROLLED, PENDING])
        self.assertEqual(old.items[1].target, "2026-10-19")
        today = self.p.day()
        self.assertEqual([i.title for i in today.items], ["Unfinished"])
        self.assertIsNone(today.items[0].fixed_start)  # rolled items lose their anchor
        self.assertEqual(today.items[0].origin, "2026-10-18")
        self.assertEqual(len(rolled), 1)

        self.p.roll_over()  # idempotent
        self.assertEqual(len(self.p.day().items), 1)

    def test_catch_up_after_days_off(self):
        self.p.add("A", 30)
        self.p.add("B", 30, on=date(2026, 10, 20))
        self.clock.dt = local(2026, 10, 23, 8, 0)
        self.assertEqual(sorted(i.title for i in self.p.day().items), ["A", "B"])

    def test_running_item_stays_on_its_day(self):
        self.p.add("Late night", 120)
        self.clock.dt = local(2026, 10, 18, 23, 30)
        self.p.start(1)
        self.clock.dt = local(2026, 10, 19, 0, 30)
        self.assertEqual(self.p.day().items, [])
        self.assertEqual(self.p.current().item.title, "Late night")
        self.p.done()
        self.assertEqual(self.p.day(date(2026, 10, 18)).items[0].status, DONE)


class TestMoveAndStash(PlannerTest):
    def test_move(self):
        self.p.add("A", 30)
        copy = self.p.move(1, date(2026, 10, 25))
        self.assertEqual(self.p.day().items[0].status, MOVED)
        self.assertEqual(self.p.day(date(2026, 10, 25)).items[0].uid, copy.uid)

    def test_stash_round_trip(self):
        self.p.add("A", 30, notes="keep me")
        self.p.stash(1)
        self.assertEqual(self.p.day().items[0].status, STASHED)
        self.assertEqual(len(self.p.stash_items().items), 1)

        # Stashed items don't roll over...
        self.clock.dt = local(2026, 10, 21, 9, 0)
        self.assertEqual(self.p.day().items, [])
        # ...and come back wherever asked.
        item = self.p.unstash(1, date(2026, 10, 22))
        self.assertEqual((item.title, item.notes, item.status), ("A", "keep me", PENDING))
        self.assertEqual(self.p.stash_items().items, [])


class TestFiles(PlannerTest):
    def test_json_and_markdown_written(self):
        self.p.add("Write report", 45)
        self.p.add("Eating", 30, kind=BREAK)
        json_path = self.store.day_path(date(2026, 10, 18))
        md_path = self.store.day_path(date(2026, 10, 18), "md")
        data = json.loads(json_path.read_text())
        self.assertEqual([i["title"] for i in data["items"]], ["Write report", "Eating"])
        md = md_path.read_text()
        self.assertIn("# Sunday, 18 Oct 2026", md)
        self.assertIn("- [ ] 09:00 - 09:45  Write report", md)
        self.assertIn("☕ Break: Eating", md)

    def test_unknown_json_keys_are_tolerated(self):
        self.p.add("A", 30)
        path = self.store.day_path(date(2026, 10, 18))
        data = json.loads(path.read_text())
        data["items"][0]["future_field"] = 1
        path.write_text(json.dumps(data))
        self.assertEqual(self.p.day().items[0].title, "A")


if __name__ == "__main__":
    unittest.main()
