import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

// Top of the day view: mascot, current or next item, countdown and buttons.
Kirigami.AbstractCard {
    id: card

    readonly property var cur: backend.current
    readonly property bool hasCurrent: cur.title !== undefined
    readonly property bool running: hasCurrent && cur.running
    readonly property color accent: !running ? Kirigami.Theme.disabledTextColor
        : cur.overrun ? Kirigami.Theme.negativeTextColor
        : cur.isBreak ? Kirigami.Theme.neutralTextColor
        : Kirigami.Theme.highlightColor

    contentItem: RowLayout {
        spacing: Kirigami.Units.largeSpacing

        // A fixed-width column: the mascot on top, room for its speech bubble underneath.
        Item {
            Layout.alignment: Qt.AlignTop
            Layout.preferredWidth: Kirigami.Units.gridUnit * 7
            Layout.preferredHeight: mascot.height
            z: 2  // keep the bubble above whatever sits next to it

            MascotSlot {
                id: mascot
                anchors.horizontalCenter: parent.horizontalCenter
                mood: backend.mascotState
                character: backend.mascotCharacter
                bubbleWidth: parent.width
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            QQC2.Label {
                Layout.fillWidth: true
                text: !card.hasCurrent ? "Nothing running" : card.running ? (card.cur.isBreak ? "On a break" : "Now") : "Up next"
                font: Kirigami.Theme.smallFont
                opacity: 0.7
            }

            Kirigami.Heading {
                Layout.fillWidth: true
                level: 2
                text: card.hasCurrent ? (card.cur.isBreak ? "☕ " : "") + card.cur.title : backend.nowText
                elide: Text.ElideRight
            }

            RowLayout {
                Layout.fillWidth: true
                visible: card.hasCurrent

                QQC2.Label {
                    text: card.running ? card.cur.remainingText : `${card.cur.start} - ${card.cur.end} · ${card.cur.lengthText}`
                    font.pointSize: card.running ? Kirigami.Theme.defaultFont.pointSize * 1.6 : Kirigami.Theme.defaultFont.pointSize
                    font.features: { "tnum": 1 }
                    color: card.running && card.cur.overrun ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.textColor
                }
                Item { Layout.fillWidth: true }
                QQC2.Label {
                    visible: card.running
                    text: `until ${card.cur.end}`
                    opacity: 0.7
                }
            }

            QQC2.ProgressBar {
                Layout.fillWidth: true
                visible: card.running
                from: 0; to: 1
                value: card.running ? card.cur.progress : 0
                Behavior on value { NumberAnimation { duration: Kirigami.Units.longDuration } }
            }

            Flow {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                visible: card.hasCurrent

                QQC2.Button {
                    visible: !card.running
                    icon.name: "media-playback-start"
                    text: "Start"
                    onClicked: backend.start(card.cur.id)
                }
                QQC2.Button {
                    visible: card.running
                    icon.name: "checkmark"
                    text: "Done"
                    onClicked: backend.doneCurrent()
                }
                Repeater {
                    model: card.running ? [5, 15, 30] : []
                    QQC2.Button {
                        required property int modelData
                        text: `+${modelData}m`
                        onClicked: backend.extend(-1, modelData)
                        QQC2.ToolTip.text: `Extend by ${modelData} minutes, pushing later blocks back`
                        QQC2.ToolTip.visible: hovered
                        QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                    }
                }
                QQC2.Button {
                    visible: card.running
                    text: "+…"
                    onClicked: backend.askExtend()
                    QQC2.ToolTip.text: "Extend by any number of minutes"
                    QQC2.ToolTip.visible: hovered
                    QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                }
                QQC2.Button {
                    icon.name: "media-skip-forward"
                    text: "Skip"
                    display: QQC2.AbstractButton.IconOnly
                    onClicked: card.running ? backend.skipCurrent() : backend.skip(card.cur.id)
                    QQC2.ToolTip.text: "Skip"
                    QQC2.ToolTip.visible: hovered
                }
            }
        }
    }
}
