import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

QQC2.ItemDelegate {
    id: row

    required property var model
    required property int index
    property ListView listView

    signal moveRequested(int from, int to)
    signal dropped(int itemId, int newIndex)
    signal editRequested(var data)
    signal moveDateRequested(int itemId)

    readonly property bool pending: model.status === "pending"
    readonly property bool running: model.status === "running"
    readonly property bool finished: model.status === "done"
    readonly property bool gone: ["rolled", "moved", "stashed"].includes(model.status)
    readonly property bool unfinished: pending || running
    readonly property color barColor: finished ? Kirigami.Theme.positiveTextColor
        : model.overrun || model.conflict ? Kirigami.Theme.negativeTextColor
        : model.isBreak ? Kirigami.Theme.neutralTextColor
        : running ? Kirigami.Theme.highlightColor
        : Qt.alpha(Kirigami.Theme.textColor, 0.35)

    hoverEnabled: !gone

    // A light accent tint instead of the theme's full highlight: text keeps its normal colour,
    // and a tinted normal background keeps the same contrast in any colour scheme.
    background: Rectangle {
        color: row.running ? Qt.alpha(Kirigami.Theme.highlightColor, 0.18)
             : row.down ? Qt.alpha(Kirigami.Theme.highlightColor, 0.14)
             : row.hovered ? Qt.alpha(Kirigami.Theme.highlightColor, 0.08)
             : "transparent"
        border.width: row.visualFocus ? 1 : 0
        border.color: Kirigami.Theme.focusColor
        Behavior on color { ColorAnimation { duration: Kirigami.Units.shortDuration } }
    }
    opacity: gone || model.status === "skipped" ? 0.5 : 1
    onClicked: if (!gone) editRequested(Object.assign({}, model))

    contentItem: ColumnLayout {
        spacing: Kirigami.Units.smallSpacing

        // Unplanned time before this block.
        QQC2.Label {
            visible: row.model.gapBefore > 0
            Layout.leftMargin: Kirigami.Units.gridUnit * 3
            text: `┊  ${row.model.gapBefore >= 60 ? Math.floor(row.model.gapBefore / 60) + "h " : ""}${row.model.gapBefore % 60}m unplanned`
            font: Kirigami.Theme.smallFont
            opacity: 0.6
        }

        RowLayout {
            spacing: Kirigami.Units.smallSpacing

            Kirigami.ListItemDragHandle {
                listItem: row
                listView: row.listView
                visible: row.pending && !backend.isPast
                onMoveRequested: (oldIndex, newIndex) => row.moveRequested(oldIndex, newIndex)
                onDropped: row.dropped(row.model.id, row.index)
            }
            Item {
                visible: !(row.pending && !backend.isPast)
                implicitWidth: Kirigami.Units.iconSizes.smallMedium
            }

            ColumnLayout {
                spacing: 0
                Layout.preferredWidth: Kirigami.Units.gridUnit * 2.5
                QQC2.Label {
                    text: row.model.start || "-"
                    font.features: { "tnum": 1 }
                    font.bold: row.running
                }
                QQC2.Label {
                    text: row.model.end
                    font: Kirigami.Theme.smallFont
                    opacity: 0.6
                }
            }

            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 4
                radius: 2
                color: row.barColor
                Behavior on color { ColorAnimation { duration: Kirigami.Units.longDuration } }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 0

                QQC2.Label {
                    Layout.fillWidth: true
                    text: (row.model.isBreak ? "☕ " : "") + row.model.title
                    font.strikeout: row.gone || row.model.status === "skipped"
                    font.bold: row.running
                    elide: Text.ElideRight
                }
                QQC2.Label {
                    Layout.fillWidth: true
                    font: Kirigami.Theme.smallFont
                    opacity: row.model.conflict ? 1 : 0.7
                    color: row.model.conflict || row.model.overrun ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.textColor
                    elide: Text.ElideRight
                    text: {
                        const m = row.model
                        if (m.status === "rolled") return `rolled over to ${m.target}`
                        if (m.status === "moved") return `moved to ${m.target}`
                        if (m.status === "stashed") return "stashed"
                        if (m.status === "skipped") return "skipped"
                        const bits = [m.lengthText]
                        if (m.extended > 0) bits.push(`+${m.extended}m extended`)
                        if (m.fixedStart) bits.push(`📌 ${m.fixedStart}`)
                        if (m.overrun) bits.push("over time")
                        if (m.conflict) bits.push(`⚠ overlaps ${m.conflict}`)
                        if (m.origin) bits.push(m.origin === "stash" ? "from stash" : `from ${m.origin}`)
                        return bits.join(" · ")
                    }
                }

                Flow {
                    readonly property var tags: row.model.tagsText ? row.model.tagsText.split(" ") : []
                    Layout.fillWidth: true
                    Layout.topMargin: visible ? Kirigami.Units.smallSpacing / 2 : 0
                    spacing: Kirigami.Units.smallSpacing
                    visible: row.finished || tags.length > 0

                    Pill {
                        visible: row.finished
                        text: "done"
                        iconName: "checkmark"
                        tint: Kirigami.Theme.positiveTextColor
                    }
                    Repeater {
                        model: parent.tags
                        Pill {
                            required property string modelData
                            tag: modelData.slice(1)
                        }
                    }
                }
            }

            QQC2.ToolButton {
                visible: row.pending && backend.isToday
                icon.name: "media-playback-start"
                display: QQC2.AbstractButton.IconOnly
                text: "Start"
                onClicked: backend.start(row.model.id)
                QQC2.ToolTip.text: text
                QQC2.ToolTip.visible: hovered
                QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
            }
            QQC2.ToolButton {
                visible: row.unfinished
                icon.name: "checkmark"
                display: QQC2.AbstractButton.IconOnly
                text: "Done"
                onClicked: backend.done(row.model.id)
                QQC2.ToolTip.text: text
                QQC2.ToolTip.visible: hovered
                QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
            }
            QQC2.ToolButton {
                visible: !row.gone
                icon.name: "overflow-menu"
                display: QQC2.AbstractButton.IconOnly
                text: "More"
                onClicked: menu.popup()
            }
        }
    }

    QQC2.Menu {
        id: menu

        QQC2.MenuItem {
            visible: row.pending && backend.isToday
            height: visible ? implicitHeight : 0
            icon.name: "media-playback-start"; text: "Start"
            onTriggered: backend.start(row.model.id)
        }
        QQC2.MenuItem {
            visible: row.unfinished
            height: visible ? implicitHeight : 0
            icon.name: "checkmark"; text: "Done"
            onTriggered: backend.done(row.model.id)
        }
        QQC2.Menu {
            title: "Extend"
            icon.name: "chronometer"
            enabled: row.unfinished
            Repeater {
                model: [5, 10, 15, 30, 60]
                QQC2.MenuItem {
                    required property int modelData
                    text: `+${modelData} min`
                    onTriggered: backend.extend(row.model.id, modelData)
                }
            }
        }
        QQC2.MenuItem {
            icon.name: "document-edit"; text: "Edit…"
            onTriggered: row.editRequested(Object.assign({}, row.model))
        }
        QQC2.MenuSeparator {}
        QQC2.MenuItem {
            enabled: row.pending
            icon.name: "go-next"; text: "Move to next day"
            onTriggered: backend.moveToTomorrow(row.model.id)
        }
        QQC2.MenuItem {
            enabled: row.pending
            icon.name: "view-calendar"; text: "Move to date…"
            onTriggered: row.moveDateRequested(row.model.id)
        }
        QQC2.MenuItem {
            enabled: row.pending
            icon.name: "archive-insert"; text: "Stash"
            onTriggered: backend.stashItem(row.model.id)
        }
        QQC2.MenuSeparator {}
        QQC2.MenuItem {
            visible: row.unfinished
            height: visible ? implicitHeight : 0
            icon.name: "media-skip-forward"; text: "Skip"
            onTriggered: backend.skip(row.model.id)
        }
        QQC2.MenuItem {
            visible: row.finished || row.model.status === "skipped"
            height: visible ? implicitHeight : 0
            icon.name: "edit-undo"; text: "Reopen"
            onTriggered: backend.reopen(row.model.id)
        }
        QQC2.MenuItem {
            icon.name: "edit-delete"; text: "Delete"
            onTriggered: backend.remove(row.model.id)
        }
    }
}
