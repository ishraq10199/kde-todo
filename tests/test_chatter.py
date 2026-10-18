import random
import string
import unittest
from datetime import datetime, timedelta

from kde_todo.gui.chatter import MOODS, PROGRESS_KINDS, VOICES, Chatter, Progress, mood_lines, plain, progress_lines


class Clock:
    def __init__(self):
        self.dt = datetime(2026, 10, 18, 9, 0)

    def __call__(self):
        return self.dt


class TestChatter(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.chatter = Chatter(self.clock, lambda: "Mochi", random.Random(1))
        self.progress = Progress(done=2, total=5, ends="17:30")

    def test_celebrate_and_overtime_always_speak(self):
        for _ in range(20):
            self.assertIsNotNone(self.chatter.on_mood("celebrate", self.progress))
            self.assertIsNotNone(self.chatter.on_mood("overtime", self.progress))

    def test_idle_never_speaks_on_mood_change(self):
        self.assertTrue(all(self.chatter.on_mood("idle", self.progress) is None for _ in range(50)))

    def test_minimum_gap_between_casual_remarks(self):
        self.chatter.on_mood("celebrate", self.progress)
        self.assertTrue(all(self.chatter.on_mood("working", self.progress) is None for _ in range(50)))
        self.clock.dt += timedelta(minutes=3)
        self.assertTrue(any(self.chatter.on_mood("working", self.progress) for _ in range(50)))

    def test_ambient_remarks_are_rare(self):
        said = []
        for _ in range(240):  # four hours, one tick a minute
            self.clock.dt += timedelta(minutes=1)
            if line := self.chatter.tick("idle", self.progress):
                said.append(line)
        self.assertTrue(8 <= len(said) <= 16, len(said))

    def test_no_immediate_repeats(self):
        lines = [self.chatter.poke("idle", self.progress) for _ in range(30)]
        self.assertTrue(all(a != b for a, b in zip(lines, lines[1:])))

    def test_every_voice_is_complete(self):
        allowed = {"title", "minutes", "done", "total", "left", "ends", "percent"}
        for name, v in VOICES.items():
            self.assertTrue(v.get("task_label"), f"{name} has no task_label")
            for kind in (*MOODS, *PROGRESS_KINDS):
                self.assertTrue(v.get(kind), f"{name} has no {kind} lines")
                for line in v[kind]:
                    fields = {f for _, f, _, _ in string.Formatter().parse(line) if f}
                    self.assertLessEqual(fields, allowed, line)
                    shown = plain(line)
                    self.assertNotIn("<#!", shown, f"malformed delay marker: {line}")
                    self.assertNotIn("!#>", shown, f"malformed delay marker: {line}")
                    self.assertNotIn("\u2014", shown)  # no em dashes
                    self.assertLessEqual(len(shown), 64, line)

    def test_voices_differ(self):
        p = Progress(done=1, total=4)
        said = {name: set(map(plain, mood_lines("idle", p, name) + progress_lines(p, name))) for name in VOICES}
        names = list(said)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                self.assertFalse(said[a] & said[b], f"{a} and {b} share lines")

    def test_delay_markers_are_removed_for_display(self):
        self.assertEqual(plain("Pick one!<#!delay-50-ms!#> Any one!<#!delay-100-ms!#> I'm excited!"),
                         "Pick one! Any one! I'm excited!")

    def test_progress_lines_fit_the_day(self):
        lines = lambda p: [plain(line) for line in progress_lines(p, "Pip")]
        self.assertEqual(lines(Progress()), ["Task queue empty. Please add data."])
        self.assertIn("Queue cleared. 100% complete.", lines(Progress(done=3, total=3)))
        day = lines(Progress(done=3, total=5, current="Write report", left_minutes=12, ends="17:30"))
        for expected in ("2 tasks remaining in queue.", "Progress: 3/5. 60%.", "50% threshold passed. Beep boop.",
                         "Estimated completion: 17:30.", "Write report: 12 min remaining."):
            self.assertIn(expected, day)
        self.assertIn("1 task remaining. Almost there.", lines(Progress(done=4, total=5)))

    def test_title_lines_only_when_there_is_a_title(self):
        self.assertFalse(any("{" in line or "None" in line for line in mood_lines("overtime", Progress(), "Tock")))
        said = [plain(line) for line in mood_lines("overtime", Progress(current="Write report"), "Tock")]
        self.assertIn("Ring ring! Write report has run over.", said)

    def test_long_titles_use_the_mascots_label(self):
        long = Progress(current="Prepare the quarterly finance report", left_minutes=12)
        said = lambda name, kind: [plain(line) for line in (mood_lines(kind, long, name) if kind in MOODS
                                                             else progress_lines(long, name))]
        self.assertIn("Ring ring! the current block has run over.", said("Tock", "overtime"))
        self.assertIn("The current task: 12 min remaining.", [plain(x) for x in progress_lines(
            Progress(done=1, total=3, current=long.current, left_minutes=12), "Pip")])
        self.assertIn("The current candle is out of wick. Extend it?", said("Wisp", "overtime"))
        self.assertIn("Time's up on the thing we're hunting. Pounce or extend?", said("Mochi", "overtime"))
        # Exactly at the limit (22 characters), the real name is still used.
        at_limit = [plain(x) for x in mood_lines("overtime", Progress(current="Twenty-two characters!"), "Tock")]
        self.assertIn("Ring ring! Twenty-two characters! has run over.", at_limit)

if __name__ == "__main__":
    unittest.main()
