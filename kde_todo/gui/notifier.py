"""Desktop notifications via KNotification (events are declared in kde-todo.notifyrc).

Only started items notify: when they start, at the halfway point, and when the
time block runs out. Extending an item gives it a new end, which notifies again.
"""

from datetime import datetime, timedelta

from KNotifications import KNotification
from PySide6.QtCore import QObject, QTimer

from ..model import RUNNING
from ..parse import format_minutes
from .backend import Backend

COMPONENT = "kde-todo"


class Notifier(QObject):
    def __init__(self, backend: Backend, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.p = backend.p
        self._fired: set[tuple] = set()
        self._live: dict[tuple, KNotification] = {}  # key -> notification still on screen
        self._launched = self.p.now()

        self._timer = QTimer(self, interval=5000)
        self._timer.timeout.connect(self.check)
        self._timer.start()
        backend.changed.connect(self.check)
        backend.rolledOver.connect(self._rolled_over)

    def _send(self, event: str, key: tuple, title: str, text: str, icon: str, actions=(),
              persistent: bool = False) -> None:
        if key in self._fired:
            return
        self._fired.add(key)
        flag = KNotification.NotificationFlag
        # PySide owns every KNotification it creates, so KNotification must not delete itself
        # too (that double free crashed the app when a notification button was pressed).
        # Python drops its reference once the notification has closed, below.
        n = KNotification(event, flag.Persistent if persistent else flag.CloseOnTimeout)
        n.setAutoDelete(False)
        n.setComponentName(COMPONENT)
        n.setTitle(title)
        n.setText(text)
        n.setIconName(icon)
        if persistent:
            n.setUrgency(KNotification.Urgency.HighUrgency)
        # Handlers run on the next event loop turn, outside KNotification's own click handling:
        # they close notifications, which must not happen while KNotification is still using them.
        later = lambda handler: (lambda: QTimer.singleShot(0, handler))
        for label, handler in actions:
            n.addAction(label).activated.connect(later(handler))
        n.addDefaultAction("Open").activated.connect(later(self.backend.showRequested.emit))
        n.closed.connect(lambda: QTimer.singleShot(0, lambda: self._live.pop(key, None)))
        self._live[key] = n
        n.sendEvent()

    def _close(self, stale) -> None:
        for key, n in list(self._live.items()):
            if key[0] != "rollover" and stale(key):
                n.close()

    def check(self) -> None:
        try:
            slot = self.p.current()
        except Exception:
            return
        if not slot or slot.item.status != RUNNING:
            self._close(lambda key: True)
            return

        item, now = slot.item, self.p.now()
        start = datetime.fromisoformat(item.actual_start)
        end = start + timedelta(minutes=item.total_minutes)
        block = format_minutes(item.total_minutes)
        end_key = ("end", item.uid, end.isoformat())
        # Close notifications for other items, and a "time's up" made stale by an extension.
        self._close(lambda key: key[1] != item.uid or (key[0] == "end" and key != end_key))

        if start >= self._launched - timedelta(seconds=5):  # don't announce items started before the app ran
            self._send("taskStarted", ("start", item.uid), f"Started: {item.title}",
                       f"{start:%H:%M} - {end:%H:%M} ({block} block)", "media-playback-start")
        if start + (end - start) / 2 <= now < end:
            left = format_minutes(max(1, round((end - now).total_seconds() / 60)))
            self._send("halfway", ("half", item.uid), f"Halfway: {item.title}",
                       f"{left} left, until {end:%H:%M}", "chronometer")
        if now >= end:
            self._send("timeUp", end_key, f"Time's up: {item.title}",
                       f"The {block} block ended at {end:%H:%M}. Extend it, or mark it done?",
                       "chronometer-pause", persistent=True,
                       actions=[("Done", self.backend.doneCurrent),
                                ("+5 min", lambda: self.backend.extend(-1, 5)),
                                ("+15 min", lambda: self.backend.extend(-1, 15)),
                                ("Extend…", self.backend.askExtend)])

    def _rolled_over(self, count: int) -> None:
        self._send("rollover", ("rollover", self.p.today().isoformat()), "New day",
                   f"{count} unfinished item{'s' if count != 1 else ''} carried over to today", "go-next")
