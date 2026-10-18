import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import org.kde.kirigamiaddons.dateandtime as DateAndTime

Kirigami.ScrollablePage {
    id: page

    title: "Stash"

    ListView {
        id: list
        model: backend.stash

        delegate: QQC2.ItemDelegate {
            id: row
            required property var modelData
            width: ListView.view.width
            hoverEnabled: false

            contentItem: RowLayout {
                spacing: Kirigami.Units.largeSpacing
                Kirigami.Icon {
                    source: "archive-insert"
                    implicitWidth: Kirigami.Units.iconSizes.smallMedium
                    implicitHeight: implicitWidth
                    opacity: 0.6
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 0
                    QQC2.Label {
                        Layout.fillWidth: true
                        text: (row.modelData.isBreak ? "☕ " : "") + row.modelData.title
                        elide: Text.ElideRight
                    }
                    QQC2.Label {
                        Layout.fillWidth: true
                        text: row.modelData.lengthText + (row.modelData.origin ? ` · stashed from ${row.modelData.origin}` : "")
                        font: Kirigami.Theme.smallFont
                        opacity: 0.7
                    }
                }
                QQC2.Button {
                    icon.name: "go-jump-today"
                    text: "Today"
                    onClicked: {
                        backend.goToday()
                        backend.unstash(row.modelData.id, "")
                    }
                }
                QQC2.ToolButton {
                    icon.name: "view-calendar"
                    text: "Pick a day…"
                    display: QQC2.AbstractButton.IconOnly
                    onClicked: {
                        datePopup.stashId = row.modelData.id
                        datePopup.value = new Date()
                        datePopup.open()
                    }
                    QQC2.ToolTip.text: text
                    QQC2.ToolTip.visible: hovered
                }
            }
        }

        Kirigami.PlaceholderMessage {
            anchors.centerIn: parent
            width: parent.width - Kirigami.Units.gridUnit * 4
            visible: list.count === 0
            icon.name: "archive-insert"
            text: "The stash is empty"
            explanation: "Items you stash from a day show up here."
        }
    }

    DateAndTime.DatePopup {
        id: datePopup
        objectName: "stashDatePopup"
        property int stashId: -1
        autoAccept: true
        onAccepted: {
            const d = datePopup.value
            const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
            backend.unstash(stashId, iso)
        }
    }
}
