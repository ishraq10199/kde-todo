import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

RowLayout {
    id: bar

    signal breakRequested()

    spacing: Kirigami.Units.smallSpacing

    Kirigami.ActionTextField {
        id: field
        Layout.fillWidth: true
        placeholderText: backend.isPast ? "Add to a past day…" : "Add a block, e.g. Write report 45m @14:00 #work"
        onAccepted: bar.submit()
        rightActions: Kirigami.Action {
            icon.name: "list-add"
            text: "Add"
            enabled: field.text.trim().length > 0
            onTriggered: bar.submit()
        }
    }

    QQC2.Button {
        icon.name: "media-playback-pause"
        text: "Break"
        onClicked: bar.breakRequested()
        QQC2.ToolTip.text: "Add a labelled break"
        QQC2.ToolTip.visible: hovered
        QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
    }

    function submit() {
        if (field.text.trim() && backend.quickAdd(field.text))
            field.clear()
    }
}
