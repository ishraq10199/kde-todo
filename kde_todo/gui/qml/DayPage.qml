import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import org.kde.kirigamiaddons.dateandtime as DateAndTime

Kirigami.ScrollablePage {
    id: page

    title: backend.viewTitle

    actions: [
        Kirigami.Action {
            icon.name: "go-previous"
            text: "Previous day"
            displayHint: Kirigami.DisplayHint.IconOnly
            onTriggered: backend.shiftDay(-1)
        },
        Kirigami.Action {
            icon.name: "go-jump-today"
            text: "Today"
            enabled: !backend.isToday
            displayHint: Kirigami.DisplayHint.IconOnly
            onTriggered: backend.goToday()
        },
        Kirigami.Action {
            icon.name: "go-next"
            text: "Next day"
            displayHint: Kirigami.DisplayHint.IconOnly
            onTriggered: backend.shiftDay(1)
        }
    ]

    // Copied into a ListModel because the drag handle needs model.move().
    ListModel { id: itemsModel }

    function reload() {
        const items = backend.items
        // Same rows in the same order: update in place so hover and open menus survive.
        if (items.length === itemsModel.count && items.every((item, i) => itemsModel.get(i).uid === item.uid)) {
            items.forEach((item, i) => itemsModel.set(i, item))
            return
        }
        itemsModel.clear()
        items.forEach(item => itemsModel.append(item))
    }

    function firstPendingSlot() {
        let last = -1
        for (let i = 0; i < itemsModel.count; i++) {
            if (["done", "skipped", "running"].includes(itemsModel.get(i).status))
                last = i
        }
        return last + 1
    }

    Component.onCompleted: reload()
    Connections {
        target: backend
        function onChanged() { page.reload() }
    }

    header: ColumnLayout {
        spacing: 0
        visible: backend.isToday

        NowCard {
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.largeSpacing
            Layout.bottomMargin: Kirigami.Units.smallSpacing
        }
        Kirigami.Separator { Layout.fillWidth: true }
    }

    ListView {
        id: list
        model: itemsModel
        reuseItems: false
        spacing: 0
        moveDisplaced: Transition { YAnimator { duration: Kirigami.Units.longDuration; easing.type: Easing.OutCubic } }

        // The drag handle moves the row inside this wrapper and animates it back to y = 0 on drop,
        // so the row must not be the delegate itself (Kirigami's ListItemDragHandle docs).
        delegate: Item {
            id: wrapper
            required property var model
            required property int index
            width: ListView.view.width
            height: row.height

            TodoDelegate {
                id: row
                width: parent.width
                model: wrapper.model
                index: wrapper.index
                listView: list
                // Pending items can't be dragged above done, skipped or running ones.
                onMoveRequested: (from, to) => { if (to >= page.firstPendingSlot()) itemsModel.move(from, to, 1) }
                onDropped: (itemId, newIndex) => {
                    // Position among the day's active items (rolled/moved/stashed rows don't count).
                    let position = 0
                    for (let i = 0; i < newIndex; ++i) {
                        if (["pending", "running", "done", "skipped"].includes(itemsModel.get(i).status))
                            position++
                    }
                    backend.reorder(itemId, position)
                }
                onEditRequested: (data) => editDialog.openFor(data)
                onMoveDateRequested: (itemId) => {
                    datePopup.itemId = itemId
                    datePopup.value = new Date()
                    datePopup.open()
                }
            }
        }

        Kirigami.PlaceholderMessage {
            anchors.centerIn: parent
            width: parent.width - Kirigami.Units.gridUnit * 4
            visible: list.count === 0
            icon.name: backend.isPast ? "view-history" : "view-task-add"
            text: backend.isPast ? "Nothing was planned" : "Nothing planned yet"
            explanation: backend.isPast ? "" : "Type something like: Write report 45m, or Standup @9:30 15m"
        }
    }

    footer: ColumnLayout {
        spacing: 0
        Kirigami.Separator { Layout.fillWidth: true }

        QQC2.Label {
            Layout.fillWidth: true
            Layout.topMargin: Kirigami.Units.smallSpacing
            Layout.leftMargin: Kirigami.Units.largeSpacing
            text: backend.summary
            opacity: 0.7
            font: Kirigami.Theme.smallFont
            elide: Text.ElideRight
        }

        QuickAddBar {
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.largeSpacing
            Layout.topMargin: Kirigami.Units.smallSpacing
            onBreakRequested: breakDialog.open()
        }
    }

    BreakDialog { id: breakDialog }
    EditDialog { id: editDialog }

    DateAndTime.DatePopup {
        id: datePopup
        property int itemId: -1
        autoAccept: true
        onAccepted: {
            const d = datePopup.value
            const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
            backend.moveTo(itemId, iso)
        }
    }
}
