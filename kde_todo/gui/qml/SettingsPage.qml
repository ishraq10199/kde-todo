import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page

    title: "Settings"

    Kirigami.FormLayout {
        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: "Mascot"
        }

        RowLayout {
            Kirigami.FormData.label: "Character:"
            spacing: Kirigami.Units.largeSpacing
            QQC2.ComboBox {
                id: characterBox
                model: backend.mascotCharacters
                currentIndex: backend.mascotCharacters.indexOf(backend.mascotCharacter)
                onActivated: backend.mascotCharacter = currentText
            }
            MascotSlot {
                character: characterBox.currentText
                mood: "idle"
                talks: false
                zoom: 3
            }
        }

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: "Break labels"
        }

        Repeater {
            model: backend.breakLabels
            RowLayout {
                required property string modelData
                Kirigami.FormData.label: "☕"
                QQC2.Label { text: parent.modelData; Layout.fillWidth: true }
                QQC2.ToolButton {
                    icon.name: "edit-delete-remove"
                    text: "Remove"
                    display: QQC2.AbstractButton.IconOnly
                    onClicked: backend.removeBreakLabel(parent.modelData)
                }
            }
        }

        Kirigami.ActionTextField {
            id: newLabel
            Kirigami.FormData.label: "New label:"
            placeholderText: "e.g. Stretch"
            onAccepted: add()
            function add() {
                if (text.trim()) {
                    backend.addBreakLabel(text.trim())
                    clear()
                }
            }
            rightActions: Kirigami.Action {
                icon.name: "list-add"
                enabled: newLabel.text.trim().length > 0
                onTriggered: newLabel.add()
            }
        }

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: "Records"
        }

        QQC2.Label {
            Kirigami.FormData.label: "Data folder:"
            text: dataDir
            textFormat: Text.PlainText
        }
        QQC2.Button {
            icon.name: "folder-open"
            text: "Open folder"
            onClicked: Qt.openUrlExternally("file://" + dataDir)
        }
        QQC2.Label {
            Layout.maximumWidth: Kirigami.Units.gridUnit * 18
            wrapMode: Text.Wrap
            opacity: 0.7
            font: Kirigami.Theme.smallFont
            text: "Each day is a JSON file with a Markdown copy beside it. Day start and default duration "
                + "live in config.json."
        }
    }
}
