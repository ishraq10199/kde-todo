import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

// Breaks use a label from the list. Adding a new label needs an extra step.
Kirigami.Dialog {
    id: dialog

    readonly property string newLabelText: "New label…"
    readonly property bool creating: labelBox.currentText === newLabelText

    title: "Add a break"
    padding: Kirigami.Units.largeSpacing
    preferredWidth: Kirigami.Units.gridUnit * 20
    standardButtons: Kirigami.Dialog.Cancel

    customFooterActions: Kirigami.Action {
        icon.name: "list-add"
        text: "Add break"
        enabled: !dialog.creating || newLabel.text.trim().length > 0
        onTriggered: {
            const label = dialog.creating ? newLabel.text.trim() : labelBox.currentText
            if (backend.addBreak(label, minutes.value, dialog.creating))
                dialog.close()
        }
    }

    onOpened: {
        newLabel.clear()
        minutes.value = 15
        labelBox.currentIndex = 0
    }

    Kirigami.FormLayout {
        QQC2.ComboBox {
            id: labelBox
            Kirigami.FormData.label: "Label:"
            model: [...backend.breakLabels, dialog.newLabelText]
        }
        QQC2.TextField {
            id: newLabel
            visible: dialog.creating
            Kirigami.FormData.label: "New label:"
            placeholderText: "Name"
        }
        Kirigami.InlineMessage {
            visible: dialog.creating
            Layout.fillWidth: true
            type: Kirigami.MessageType.Information
            text: `You have ${backend.breakLabels.length} labels already.`
        }
        QQC2.SpinBox {
            id: minutes
            Kirigami.FormData.label: "Minutes:"
            from: 5; to: 240; stepSize: 5
        }
    }
}
