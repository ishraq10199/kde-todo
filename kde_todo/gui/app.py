"""GUI entry point: `kde-todo gui`."""

from __future__ import annotations

import os
import shutil
import signal
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from ..planner import Planner
from ..storage import data_dir

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
SOCKET = f"kde-todo-{os.getuid()}"


def _data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")


def _install_desktop_entry() -> None:
    """The desktop portal looks the app up by its ID (org.kde.kdetodo) and logs an error when no
    matching .desktop file exists. Add one if missing; never replace the one install.sh writes."""
    target = _data_home() / "applications" / "org.kde.kdetodo.desktop"
    if target.exists():
        return
    command = shutil.which("kde-todo")
    if command:
        exec_line = f"{command} gui"
    else:  # running from the project folder with `python3 -m kde_todo`
        exec_line = f"env PYTHONPATH={HERE.parents[1]} {sys.executable} -m kde_todo gui"
    entry = (DATA / "org.kde.kdetodo.desktop").read_text(encoding="utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(f"Exec={exec_line}" if line.startswith("Exec=") else line
                                for line in entry.splitlines()) + "\n", encoding="utf-8")


def _install_notifyrc() -> None:
    """KNotification looks the event config up in XDG data dirs."""
    target = _data_home() / "knotifications6" / "kde-todo.notifyrc"
    source = DATA / "kde-todo.notifyrc"
    if not target.exists() or target.read_bytes() != source.read_bytes():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def pixel_font() -> str:
    """DepartureMono for the mascot's speech bubble, or its Nerd Font build, or any monospace font."""
    installed = set(QFontDatabase.families())
    for family in ("DepartureMono", "Departure Mono", "DepartureMono Nerd Font Mono", "DepartureMono Nerd Font"):
        if family in installed:
            return family
    return QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()


def _signal_running_instance(message: bytes) -> bool:
    sock = QLocalSocket()
    sock.connectToServer(SOCKET)
    if not sock.waitForConnected(300):
        return False
    sock.write(message)
    sock.waitForBytesWritten(300)
    sock.disconnectFromServer()
    return True


def main(argv: list[str] | None = None, *, hidden: bool = False) -> int:
    argv = argv if argv is not None else sys.argv
    QApplication.setApplicationName("kde-todo")
    QApplication.setApplicationDisplayName("kde-todo")
    QApplication.setOrganizationName("kde-todo")
    QApplication.setDesktopFileName("org.kde.kdetodo")
    _install_desktop_entry()  # before QApplication, which registers with the portal
    QQuickStyle.setStyle("org.kde.desktop")
    app = QApplication(argv)
    app.setWindowIcon(QIcon.fromTheme("view-task"))
    app.setQuitOnLastWindowClosed(False)

    if _signal_running_instance(b"show"):
        return 0  # the running instance shows itself
    QLocalServer.removeServer(SOCKET)
    server = QLocalServer(app)
    server.listen(SOCKET)

    _install_notifyrc()
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    from .backend import Backend
    from .notifier import Notifier
    from .tray import Tray

    from .i18n import LocalizedContext

    backend = Backend(Planner())
    engine = QQmlApplicationEngine()
    i18n = LocalizedContext(engine)
    engine.rootContext().setContextObject(i18n)
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("dataDir", str(data_dir()))
    engine.rootContext().setContextProperty("pixelFont", pixel_font())
    engine.load(QUrl.fromLocalFile(str(HERE / "qml" / "Main.qml")))
    if not engine.rootObjects():
        print("kde-todo: failed to load the UI", file=sys.stderr)
        return 1
    window = engine.rootObjects()[0]

    tray = Tray(backend, window, app.quit)
    notifier = Notifier(backend)
    backend.showRequested.connect(tray.show_window)
    backend.extendRequested.connect(tray.show_window)

    def on_connection():
        conn = server.nextPendingConnection()
        conn.readyRead.connect(lambda: conn.readAll() and tray.show_window())
    server.newConnection.connect(on_connection)

    if not hidden:
        tray.show_window()
    app._keep = (engine, backend, tray, notifier, server)  # keep Python wrappers alive
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
