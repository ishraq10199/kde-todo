"""What the mascot says in its speech bubble, and how often. Every character has its own voice."""

import random
import re
import string
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

MIN_GAP = timedelta(minutes=2)  # between remarks, except celebrate and overtime
AMBIENT_MINUTES = (15, 30)  # range for an unprompted remark

# Chance that switching into a mood makes the mascot say something.
MOOD_CHANCE = {"celebrate": 1.0, "overtime": 1.0, "working": 0.4, "resting": 0.4, "sleepy": 0.3, "idle": 0.0}

# Lines per character: one list per mood, and one per kind of progress remark.
# Placeholders: {title} {minutes} {done} {total} {left} {ends} {percent}. A line whose
# placeholders can't be filled right now is skipped.
# <#!delay-300-ms!#> pauses the typing for that long at that point, for timing and emphasis.
VOICES = {
    "Mochi": {  # a lazy, smug cat who secretly cares
        "task_label": "the thing we're hunting",  # said instead of task names that are too long
        "idle": ["I saved you the warm spot.<#!delay-400-ms!#> Now pick a task.",
                 "*stretches*<#!delay-500-ms!#> What are we hunting next?",
                 "I'd help, but my paws are busy being cute.",
                 "Staring at the list won't scare it.<#!delay-400-ms!#> Trust me, I tried."],
        "working": ["*sits on your keyboard, supportively*", "Focus.<#!delay-300-ms!#> Like me watching a bird.",
                    "Purrrr.<#!delay-300-ms!#> You're doing the thing.", "I'll guard the snacks while you work."],
        "resting": ["Ah, nap o'clock.<#!delay-300-ms!#> My favourite o'clock.", "Stretch like you mean it.",
                    "*kneads the blanket*<#!delay-400-ms!#> Rest properly.",
                    "Good break.<#!delay-250-ms!#> Very cat of you."],
        "celebrate": ["Mrrp!<#!delay-200-ms!#> You caught one!", "That task never stood a chance.",
                      "*slow blink*<#!delay-600-ms!#> of approval.",
                      "Proud of you<#!delay-60-ms!#>.<#!delay-60-ms!#>.<#!delay-60-ms!#>."
                      " Don't tell anyone I said that! >w<"],
        "overtime": ["Mrow?!<#!delay-300-ms!#> We're past the time.",
                     "The bowl is empty<#!delay-300-ms!#> and so is the clock.",
                     "Wrap it up or give it more time. I'm not judging.<#!delay-600-ms!#> (I am.)",
                     "Time's up on {title}.<#!delay-300-ms!#> Pounce or extend?"],
        "sleepy": ["Zzz<#!delay-200-ms!#>.<#!delay-200-ms!#>.<#!delay-200-ms!#>. five more minutes...",
                   "*curls up on the task list*", "Nothing's running.<#!delay-400-ms!#> Perfect nap weather."],
        "none": ["No plans?<#!delay-300-ms!#> Same.<#!delay-300-ms!#> Want to add one anyway?"],
        "all_done": ["All done!<#!delay-300-ms!#> Now we both nap.",
                     "{total} for {total}.<#!delay-300-ms!#> You've earned a sunbeam."],
        "left_many": ["{left} left.<#!delay-300-ms!#> I believe in you,<#!delay-400-ms!#> mostly."],
        "one_left": ["Just one more,<#!delay-200-ms!#> then cuddles."],
        "none_done": ["{total} things on the list.<#!delay-300-ms!#> I'll supervise."],
        "first": ["First one down.<#!delay-300-ms!#> I watched the whole time."],
        "done_of": ["{done} of {total} done.<#!delay-300-ms!#> Good human."],
        "halfway": ["Halfway there.<#!delay-300-ms!#> I'd have napped twice by now."],
        "ends": ["At this pace we're done by {ends}.<#!delay-300-ms!#> Then dinner?"],
        "current": ["{minutes} min left on {title}.<#!delay-300-ms!#> I'm counting.<#!delay-400-ms!#> Sort of."],
    },
    "Blip": {  # a bouncy slime, excited about everything: quick, short pauses
        "task_label": "the current thingy",  # said instead of task names that are too long
        "idle": ["Bloop!<#!delay-150-ms!#> What are we doing?", "*wobbles expectantly*",
                 "Pick one!<#!delay-50-ms!#> Any one!<#!delay-100-ms!#> I'm excited!", "Squish me if you're stuck."],
        "working": ["Wobble wobble,<#!delay-100-ms!#> working working!",
                    "You're on a roll!<#!delay-200-ms!#> I'm also on a roll!",
                    "Go<#!delay-120-ms!#> go<#!delay-120-ms!#> go!", "*bounces quietly so you can focus*"],
        "resting": ["Sploosh.<#!delay-200-ms!#> Break time!", "Melt a little.<#!delay-300-ms!#> It helps.",
                    "Rest is squishy and good.", "Drink some water!<#!delay-200-ms!#> I'm mostly water!"],
        "celebrate": ["Boing!<#!delay-100-ms!#> Boing!<#!delay-100-ms!#> You did it!",
                      "Wheeeee!<#!delay-150-ms!#> Another one done!", "*happy jiggle*", "That was SO good!"],
        "overtime": ["Uh oh!<#!delay-200-ms!#> The timer went bloop!",
                     "We're over!<#!delay-200-ms!#> Wrap up or add time?",
                     "*nervous wobble*<#!delay-300-ms!#> Time's up on {title}!"],
        "sleepy": ["Zzz<#!delay-300-ms!#>... bloop<#!delay-300-ms!#>... zzz...", "*slowly flattens*",
                   "So quiet<#!delay-300-ms!#>... getting<#!delay-400-ms!#>... puddly..."],
        "none": ["The list is empty!<#!delay-150-ms!#> Fill it up!"],
        "all_done": ["ALL DONE!<#!delay-200-ms!#> *bounces off the walls*",
                     "{total} out of {total}!<#!delay-150-ms!#> Best day!"],
        "left_many": ["{left} more to go!<#!delay-150-ms!#> We can do it!"],
        "one_left": ["One left!<#!delay-100-ms!#> One!<#!delay-100-ms!#> Ahh!"],
        "none_done": ["{total} things today!<#!delay-150-ms!#> Let's bounce!"],
        "first": ["First one!<#!delay-100-ms!#> Woohoo!"],
        "done_of": ["{done} down, {total} total!<#!delay-150-ms!#> Boing!"],
        "halfway": ["Halfway!<#!delay-200-ms!#> That's like a whole half!"],
        "ends": ["Done by {ends}!<#!delay-200-ms!#> Then party?"],
        "current": ["{minutes} min left on {title}!<#!delay-150-ms!#> Keep going!"],
    },
    "Pip": {  # a literal-minded robot giving status reports: even, mechanical pauses
        "task_label": "the current task",  # said instead of task names that are too long
        "idle": ["Awaiting input.", "Standby mode.<#!delay-300-ms!#> Please select a task.",
                 "All systems idle.<#!delay-400-ms!#> This is inefficient.",
                 "I have run 0 tasks this minute.<#!delay-500-ms!#> Neither have you."],
        "working": ["Focus subroutine engaged.",
                    "Processing<#!delay-200-ms!#>.<#!delay-200-ms!#>.<#!delay-200-ms!#>. You're doing great.",
                    "Distraction filter:<#!delay-300-ms!#> ON.", "Productivity levels nominal."],
        "resting": ["Low-power mode recommended.", "Break detected.<#!delay-300-ms!#> Recharging human.",
                    "Cooling fans engaged.<#!delay-300-ms!#> Relax.",
                    "Hydration reminder: drink water.<#!delay-400-ms!#> I'll stick to oil."],
        "celebrate": ["Task complete.<#!delay-200-ms!#> Beep!", "Success logged.<#!delay-200-ms!#> Excellent work.",
                      "Achievement unlocked.",
                      "Updating records<#!delay-150-ms!#>.<#!delay-150-ms!#>.<#!delay-150-ms!#>."
                      " You're on fire.<#!delay-400-ms!#> Not literally."],
        "overtime": ["Warning:<#!delay-300-ms!#> time block exceeded.",
                     "Error 408:<#!delay-300-ms!#> task timed out. Extend or finish?",
                     "Alert!<#!delay-200-ms!#> {title} is over its allotted time."],
        "sleepy": ["Entering sleep mode<#!delay-300-ms!#>... zzzt.",
                   "No activity detected.<#!delay-300-ms!#> Screensaver: me.", "Ping?<#!delay-600-ms!#> ...Ping?"],
        "none": ["Task queue empty.<#!delay-300-ms!#> Please add data."],
        "all_done": ["Queue cleared.<#!delay-300-ms!#> 100% complete.",
                     "{total}/{total} tasks done.<#!delay-300-ms!#> Efficiency: maximum."],
        "left_many": ["{left} tasks remaining in queue."],
        "one_left": ["1 task remaining.<#!delay-300-ms!#> Almost there."],
        "none_done": ["{total} tasks loaded.<#!delay-300-ms!#> Ready to execute."],
        "first": ["First task complete.<#!delay-300-ms!#> Momentum initiated."],
        "done_of": ["Progress: {done}/{total}.<#!delay-300-ms!#> {percent}%."],
        "halfway": ["50% threshold passed.<#!delay-300-ms!#> Beep boop."],
        "ends": ["Estimated completion: {ends}."],
        "current": ["{title}: {minutes} min remaining."],
    },
    "Tock": {  # a punctual alarm clock, a little fussy about lateness: ticking rhythm
        "task_label": "the current block",  # said instead of task names that are too long
        "idle": ["Tick,<#!delay-300-ms!#> tock.<#!delay-300-ms!#> The day won't schedule itself.",
                 "Every idle minute is a minute I count.", "Ahem.<#!delay-500-ms!#> Something should be running.",
                 "I'm wound up and ready.<#!delay-300-ms!#> Are you?"],
        "working": ["Tick,<#!delay-300-ms!#> tock.<#!delay-300-ms!#> Right on schedule.",
                    "Steady pace.<#!delay-200-ms!#> Just how I like it.",
                    "Every second counted,<#!delay-200-ms!#> every second used.",
                    "Precisely.<#!delay-300-ms!#> Keep going."],
        "resting": ["A scheduled break.<#!delay-300-ms!#> Very proper.", "Rest now.<#!delay-300-ms!#> I'll keep time.",
                    "Breaks are on the schedule too.", "Let the gears cool a moment."],
        "celebrate": ["Ding!<#!delay-300-ms!#> Done on time.", "Punctual AND finished.<#!delay-300-ms!#> Bravo.",
                      "*proud ticking*", "That's how clockwork works."],
        "overtime": ["RIIING!<#!delay-300-ms!#> Time's up!",
                     "We are running late.<#!delay-400-ms!#> I don't like late.",
                     "Ring ring!<#!delay-200-ms!#> {title} has run over.",
                     "Overtime!<#!delay-300-ms!#> Extend it or close it out."],
        "sleepy": ["Tick<#!delay-500-ms!#>... tock<#!delay-500-ms!#>... tick...",
                   "Even clocks rest.<#!delay-400-ms!#> But not this long.", "*winding down*"],
        "none": ["An empty schedule?<#!delay-400-ms!#> Unthinkable. Add something."],
        "all_done": ["Schedule complete.<#!delay-300-ms!#> Ding<#!delay-150-ms!#> ding<#!delay-150-ms!#> ding!",
                     "{total} of {total},<#!delay-200-ms!#> every one on the clock."],
        "left_many": ["{left} left on the schedule."],
        "one_left": ["One more and the day is wound down."],
        "none_done": ["{total} blocks on today's schedule.<#!delay-300-ms!#> Shall we?"],
        "first": ["First one done.<#!delay-300-ms!#> Now the day has properly started."],
        "done_of": ["{done} of {total}.<#!delay-300-ms!#> Keeping good time."],
        "halfway": ["Halfway through the day's schedule."],
        "ends": ["At this rate, we finish at {ends}<#!delay-300-ms!#> sharp."],
        "current": ["{minutes} min left on {title}.<#!delay-300-ms!#> Tick,<#!delay-200-ms!#> tock."],
    },
    "Wisp": {  # a calm little flame who talks in fire: slow, long pauses
        "task_label": "the current candle",  # said instead of task names that are too long
        "idle": ["The ember waits.<#!delay-500-ms!#> What shall we light?",
                 "A quiet flicker.<#!delay-400-ms!#> Ready when you are.",
                 "Pick a spark.<#!delay-400-ms!#> Small ones catch best.", "*drifts gently*"],
        "working": ["Burning bright.", "Steady flame,<#!delay-300-ms!#> steady work.", "Keep feeding the fire.",
                    "I'll keep the warmth.<#!delay-400-ms!#> You keep going."],
        "resting": ["Even fires need air.<#!delay-500-ms!#> Breathe.", "Let the embers glow a while.",
                    "Rest.<#!delay-500-ms!#> The flame will wait.", "Soft light,<#!delay-400-ms!#> slow minutes."],
        "celebrate": ["Another log on the fire!", "*flares up warmly*", "That one burned clean.", "Bright work."],
        "overtime": ["The flame's burning past its candle.",
                     "We've burned past the time.<#!delay-400-ms!#> Rekindle or rest?",
                     "{title} is out of wick.<#!delay-400-ms!#> Extend it?"],
        "sleepy": ["*flickers low*", "Just embers now<#!delay-300-ms!#>.<#!delay-300-ms!#>.<#!delay-300-ms!#>.",
                   "The fire's dozing.<#!delay-500-ms!#> Wake it with a task?"],
        "none": ["No kindling yet.<#!delay-400-ms!#> Add a task to start the fire."],
        "all_done": ["All burned through.<#!delay-500-ms!#> Let the fire rest.",
                     "{total} of {total}.<#!delay-400-ms!#> What a warm day."],
        "left_many": ["{left} sparks left to light."],
        "one_left": ["One last ember."],
        "none_done": ["{total} candles to light today."],
        "first": ["The first spark caught."],
        "done_of": ["{done} of {total} lit."],
        "halfway": ["Half the candles glow already."],
        "ends": ["The last flame should settle around {ends}."],
        "current": ["{minutes} min of wick left on {title}."],
    },
}
MOODS = ("idle", "working", "resting", "celebrate", "overtime", "sleepy")
PROGRESS_KINDS = ("none", "all_done", "left_many", "one_left", "none_done", "first", "done_of", "halfway", "ends",
                  "current")


DELAY = re.compile(r"<#!delay-(\d+)-ms!#>")


def plain(line: str) -> str:
    """The text as shown, without delay markers."""
    return DELAY.sub("", line)


@dataclass
class Progress:
    done: int = 0
    total: int = 0
    current: str | None = None  # title of the running item, even when over time
    left_minutes: int | None = None  # time left on the running item, if it isn't over
    ends: str | None = None  # "HH:MM" the day's plan ends


TITLE_LIMIT = 22  # longer task names are replaced by the mascot's own label for them


def _fill(lines: list[str], values: dict) -> list[str]:
    """Format each line, skipping lines that need a value we don't have."""
    out = []
    for line in lines:
        fields = {name for _, name, _, _ in string.Formatter().parse(line) if name}
        if not all(values.get(name) is not None for name in fields):
            continue
        text = line.format(**values)
        if line.startswith("{title}") and values.get("title_is_label"):
            text = text[0].upper() + text[1:]  # "the current task: ..." starts a sentence
        out.append(text)
    return out


def _values(p: Progress, character: str) -> dict:
    long_title = p.current is not None and len(p.current) > TITLE_LIMIT
    return {"title": voice(character)["task_label"] if long_title else p.current, "title_is_label": long_title,
            "minutes": p.left_minutes if p.left_minutes and p.left_minutes > 0 else None,
            "done": p.done, "total": p.total, "left": p.total - p.done, "ends": p.ends,
            "percent": round(100 * p.done / p.total) if p.total else None}


def progress_kinds(p: Progress) -> list[str]:
    """Which kinds of progress remark fit the day right now."""
    if p.total == 0:
        return ["none"]
    if p.done == p.total:
        return ["all_done"]
    kinds = ["one_left" if p.total - p.done == 1 else "left_many"]
    kinds.append({0: "none_done", 1: "first"}.get(p.done, "done_of"))
    if p.done and p.done * 2 >= p.total:
        kinds.append("halfway")
    if p.ends:
        kinds.append("ends")
    if p.current and p.left_minutes and p.left_minutes > 0:
        kinds.append("current")
    return kinds


def voice(character: str) -> dict:
    return VOICES.get(character, VOICES["Mochi"])


def progress_lines(p: Progress, character: str = "Mochi") -> list[str]:
    v = voice(character)
    return _fill([line for kind in progress_kinds(p) for line in v[kind]], _values(p, character))


def mood_lines(mood: str, p: Progress, character: str = "Mochi") -> list[str]:
    v = voice(character)
    return _fill(v.get(mood, v["idle"]), _values(p, character))


class Chatter:
    def __init__(self, clock: Callable[[], datetime], character: Callable[[], str], rng: random.Random | None = None):
        self.clock = clock
        self.character = character
        self.rng = rng or random.Random()
        self.last: datetime | None = None
        self.last_line: str | None = None
        self.next_ambient = clock() + self._ambient_delay()

    def _ambient_delay(self) -> timedelta:
        return timedelta(minutes=self.rng.uniform(*AMBIENT_MINUTES))

    def _say(self, lines: list[str]) -> str:
        fresh = [line for line in lines if line != self.last_line] or lines
        line = self.rng.choice(fresh)
        now = self.clock()
        self.last, self.last_line = now, line
        self.next_ambient = now + self._ambient_delay()
        return line

    def on_mood(self, mood: str, progress: Progress) -> str | None:
        """Maybe remark on a mood change."""
        if self.rng.random() >= MOOD_CHANCE.get(mood, 0):
            return None
        urgent = mood in ("celebrate", "overtime")
        if not urgent and self.last and self.clock() - self.last < MIN_GAP:
            return None
        if mood == "celebrate" and self.rng.random() < 0.6:
            return self._say(progress_lines(progress, self.character()))
        return self._say(mood_lines(mood, progress, self.character()))

    def tick(self, mood: str, progress: Progress) -> str | None:
        """Called every minute. Says something once the ambient timer runs out."""
        if self.clock() < self.next_ambient:
            return None
        character = self.character()
        lines = progress_lines(progress, character) if self.rng.random() < 0.5 else mood_lines(mood, progress, character)
        return self._say(lines)

    def poke(self, mood: str, progress: Progress) -> str:
        """The user clicked the mascot."""
        character = self.character()
        return self._say(mood_lines(mood, progress, character) + progress_lines(progress, character))
