"""System tray entry (KStatusNotifierItem) with a live progress ring."""

from __future__ import annotations

from KStatusNotifierItem import KStatusNotifierItem
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QInputDialog, QMenu

from .backend import Backend

APP_ICON = "view-task"


class Tray:
    def __init__(self, backend: Backend, window, quit_fn):
        self.backend = backend
        self.window = window
        self.sni = KStatusNotifierItem("kde-todo")
        self.sni.setCategory(KStatusNotifierItem.ItemCategory.ApplicationStatus)
        self.sni.setStatus(KStatusNotifierItem.ItemStatus.Active)
        self.sni.setTitle("kde-todo")
        self.sni.setStandardActionsEnabled(False)
        self.sni.activateRequested.connect(lambda active, pos: self.toggle_window())
        self.sni.secondaryActivateRequested.connect(lambda pos: self.backend.doneCurrent())

        self.menu = QMenu()
        self.sni.setContextMenu(self.menu)
        self.menu.aboutToShow.connect(self._build_menu)
        self._quit = quit_fn
        self._last_key = None

        backend.tick.connect(self.update)
        self.update()

    def toggle_window(self) -> None:
        if self.window.isVisible() and self.window.isActive():
            self.window.hide()
        else:
            self.show_window()

    def show_window(self) -> None:
        self.window.show()
        self.window.raise_()
        self.window.requestActivate()

    def _build_menu(self) -> None:
        m, b = self.menu, self.backend
        m.clear()
        cur = b.current
        if cur:
            header = m.addAction(f"{'▶' if cur['running'] else '◦'} {cur['title']}  ({cur['remainingText']})")
            header.setEnabled(False)
            if cur["running"]:
                m.addAction(QIcon.fromTheme("checkmark"), "Done", b.doneCurrent)
                ext = m.addMenu(QIcon.fromTheme("chronometer"), "Extend")
                for minutes in (5, 10, 15, 30):
                    ext.addAction(f"+{minutes} min", lambda mm=minutes: b.extend(-1, mm))
                m.addAction(QIcon.fromTheme("media-skip-forward"), "Skip", b.skipCurrent)
            else:
                m.addAction(QIcon.fromTheme("media-playback-start"), f"Start {cur['title']}",
                            lambda i=cur["id"]: b.start(i))
        else:
            m.addAction("Nothing planned right now").setEnabled(False)
        m.addSeparator()

        upcoming = [i for i in b.items if i["status"] == "pending" and i["uid"] != cur.get("uid")] if b.isToday else []
        if upcoming:
            start_menu = m.addMenu(QIcon.fromTheme("media-playback-start"), "Start…")
            for item in upcoming[:12]:
                start_menu.addAction(f"{item['start']}  {item['title']}", lambda i=item["id"]: b.start(i))
        m.addAction(QIcon.fromTheme("list-add"), "Quick add…", self._quick_add)
        m.addSeparator()
        m.addAction(QIcon.fromTheme("window"), "Show / hide window", self.toggle_window)
        m.addAction(QIcon.fromTheme("application-exit"), "Quit", self._quit)

    def _quick_add(self) -> None:
        text, ok = QInputDialog.getText(None, "Quick add", "Add to today, e.g. Write report 45m @14:00")
        if ok and text.strip():
            if not self.backend.isToday:
                self.backend.goToday()
            self.backend.quickAdd(text)

    def update(self) -> None:
        cur = self.backend.current
        running = bool(cur and cur.get("running"))
        progress = round(cur.get("progress", 0) * 40) / 40 if running else None
        overrun = running and cur.get("overrun")
        key = (progress, overrun)
        if key != self._last_key:
            self._last_key = key
            self.sni.setIconByPixmap(self._icon(progress, overrun))
        if cur:
            self.sni.setToolTip(APP_ICON, cur["title"], f"{cur['remainingText']} · {cur['start']} - {cur['end']}")
        else:
            self.sni.setToolTip(APP_ICON, "kde-todo", "Nothing running")

    def _icon(self, progress: float | None, overrun: bool) -> QIcon:
        base = QIcon.fromTheme(APP_ICON)
        if progress is None:
            return base
        palette = QApplication.palette()
        accent = QColor("#da4453") if overrun else palette.color(QPalette.ColorRole.Highlight)
        track = palette.color(QPalette.ColorRole.WindowText)
        track.setAlpha(60)
        icon = QIcon()
        for size in (16, 22, 24, 32, 48, 64):
            pm = QPixmap(size, size)
            pm.fill(Qt.GlobalColor.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            width = max(2.0, size / 8)
            rect = QRectF(width / 2, width / 2, size - width, size - width)
            p.setPen(QPen(track, width))
            p.drawEllipse(rect)
            pen = QPen(accent, width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawArc(rect, 90 * 16, -int((1.0 if overrun else progress) * 360 * 16))
            inner = int(size * 0.5)
            off = (size - inner) // 2
            base.paint(p, off, off, inner, inner)
            p.end()
            icon.addPixmap(pm)
        return icon
