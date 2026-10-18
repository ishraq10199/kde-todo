import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.Dialog {
    id: dialog

    title: backend.current.title ? `Extend ${backend.current.title}` : "Extend"
    padding: Kirigami.Units.largeSpacing
    preferredWidth: Kirigami.Units.gridUnit * 18
    standardButtons: Kirigami.Dialog.Cancel

    onOpened: {
        minutes.value = 10
        minutes.forceActiveFocus()
    }

    customFooterActions: [
        Kirigami.Action {
            icon.name: "checkmark"
            text: "Mark done"
            onTriggered: {
                backend.doneCurrent()
                dialog.close()
            }
        },
        Kirigami.Action {
            icon.name: "chronometer"
            text: "Extend"
            onTriggered: {
                backend.extend(-1, minutes.value)
                dialog.close()
            }
        }
    ]

    Kirigami.FormLayout {
        QQC2.SpinBox {
            id: minutes
            Kirigami.FormData.label: "Minutes:"
            from: 1; to: 480; stepSize: 5
            editable: true
        }
    }
}
