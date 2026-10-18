import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    title: "kde-todo"
    width: Kirigami.Units.gridUnit * 26
    height: Kirigami.Units.gridUnit * 40
    minimumWidth: Kirigami.Units.gridUnit * 20
    minimumHeight: Kirigami.Units.gridUnit * 24
    visible: false

    // Closing hides the window. Quit from the tray menu.
    onClosing: (close) => {
        close.accepted = false
        root.hide()
    }

    pageStack.globalToolBar.style: Kirigami.ApplicationHeaderStyle.ToolBar
    pageStack.initialPage: dayPage

    function showPage(page) {
        if (pageStack.currentItem !== page) {
            pageStack.clear()
            pageStack.push(page)
        }
    }

    function openDay(isoDate) {
        backend.viewDate = isoDate
        showPage(dayPage)
        dayAction.checked = true
    }

    DayPage { id: dayPage }
    CalendarPage { id: calendarPage; visible: false; onDayChosen: (isoDate) => root.openDay(isoDate) }
    StashPage { id: stashPage; visible: false }
    SettingsPage { id: settingsPage; visible: false }
    ExtendDialog { id: extendDialog }

    footer: Kirigami.NavigationTabBar {
        actions: [
            Kirigami.Action {
                id: dayAction
                icon.name: "view-calendar-day"
                text: "Day"
                checked: true
                onTriggered: root.showPage(dayPage)
            },
            Kirigami.Action {
                icon.name: "view-calendar-month"
                text: "Calendar"
                onTriggered: root.showPage(calendarPage)
            },
            Kirigami.Action {
                icon.name: "archive-insert"
                text: backend.stash.length > 0 ? `Stash (${backend.stash.length})` : "Stash"
                onTriggered: root.showPage(stashPage)
            },
            Kirigami.Action {
                icon.name: "configure"
                text: "Settings"
                onTriggered: root.showPage(settingsPage)
            }
        ]
    }

    Connections {
        target: backend
        function onError(message) { root.showPassiveNotification(message, "long") }
        function onWarning(message) { root.showPassiveNotification("⚠ " + message, "long") }
        function onInfo(message) { root.showPassiveNotification(message, "short") }
        function onExtendRequested() { if (backend.current.running) extendDialog.open() }
        function onRolledOver(count) {
            root.showPassiveNotification(`${count} unfinished item${count === 1 ? "" : "s"} carried over to today`)
        }
    }
}
