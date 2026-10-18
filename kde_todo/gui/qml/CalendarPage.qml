import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page

    signal dayChosen(string isoDate)

    property int year: new Date().getFullYear()
    property int month: new Date().getMonth() + 1  // 1-12
    property var cells: []

    readonly property int firstDay: Qt.locale().firstDayOfWeek === 0 ? 7 : Qt.locale().firstDayOfWeek

    function reload() { cells = backend.month(year, month, firstDay) }
    function shift(delta) {
        let m = month + delta, y = year
        if (m < 1) { m = 12; y-- }
        if (m > 12) { m = 1; y++ }
        year = y; month = m
        reload()
    }

    title: new Date(year, month - 1, 1).toLocaleDateString(Qt.locale(), "MMMM yyyy")
    onVisibleChanged: if (visible) reload()
    Connections {
        target: backend
        function onChanged() { if (page.visible) page.reload() }
    }

    actions: [
        Kirigami.Action {
            icon.name: "go-previous"; text: "Previous month"
            displayHint: Kirigami.DisplayHint.IconOnly
            onTriggered: page.shift(-1)
        },
        Kirigami.Action {
            icon.name: "go-jump-today"; text: "This month"
            displayHint: Kirigami.DisplayHint.IconOnly
            onTriggered: {
                const now = new Date()
                page.year = now.getFullYear(); page.month = now.getMonth() + 1
                page.reload()
            }
        },
        Kirigami.Action {
            icon.name: "go-next"; text: "Next month"
            displayHint: Kirigami.DisplayHint.IconOnly
            onTriggered: page.shift(1)
        }
    ]

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        GridLayout {
            id: grid
            Layout.fillWidth: true
            columns: 7
            rowSpacing: Kirigami.Units.smallSpacing
            columnSpacing: Kirigami.Units.smallSpacing

            Repeater {
                model: [0, 1, 2, 3, 4, 5, 6].map(i => Qt.locale().dayName((page.firstDay + i) % 7, Locale.ShortFormat))
                QQC2.Label {
                    required property string modelData
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    horizontalAlignment: Text.AlignHCenter
                    text: modelData
                    font: Kirigami.Theme.smallFont
                    opacity: 0.6
                }
            }

            Repeater {
                model: page.cells
                delegate: QQC2.AbstractButton {
                    id: cell
                    required property var modelData
                    readonly property color stateColor: ({
                        complete: Kirigami.Theme.positiveTextColor,
                        partial: Kirigami.Theme.neutralTextColor,
                        planned: Kirigami.Theme.highlightColor,
                    })[modelData.state] ?? "transparent"

                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    Layout.preferredHeight: width
                    Layout.maximumHeight: Kirigami.Units.gridUnit * 3.5
                    opacity: modelData.inMonth ? 1 : 0.35
                    hoverEnabled: true
                    onClicked: page.dayChosen(modelData.date)

                    background: Rectangle {
                        radius: Kirigami.Units.cornerRadius
                        color: cell.hovered ? Qt.alpha(Kirigami.Theme.highlightColor, 0.15)
                             : cell.modelData.state !== "empty" ? Qt.alpha(cell.stateColor, 0.12) : "transparent"
                        border.width: cell.modelData.isToday ? 2 : 0
                        border.color: Kirigami.Theme.highlightColor
                    }

                    contentItem: ColumnLayout {
                        spacing: 0
                        QQC2.Label {
                            Layout.alignment: Qt.AlignHCenter
                            text: cell.modelData.day
                            font.bold: cell.modelData.isToday
                        }
                        QQC2.Label {
                            Layout.alignment: Qt.AlignHCenter
                            visible: cell.modelData.total > 0
                            text: `${cell.modelData.done}/${cell.modelData.total}`
                            font: Kirigami.Theme.smallFont
                            color: cell.stateColor
                        }
                    }

                    QQC2.ToolTip.text: backend.dayTitle(modelData.date)
                    QQC2.ToolTip.visible: hovered
                    QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                }
            }
        }

        Flow {
            Layout.fillWidth: true
            spacing: Kirigami.Units.largeSpacing
            Repeater {
                model: [
                    { label: "all done", color: Kirigami.Theme.positiveTextColor },
                    { label: "unfinished", color: Kirigami.Theme.neutralTextColor },
                    { label: "planned", color: Kirigami.Theme.highlightColor },
                ]
                RowLayout {
                    required property var modelData
                    Rectangle {
                        implicitWidth: Kirigami.Units.gridUnit * 0.6
                        implicitHeight: implicitWidth
                        radius: width / 2
                        color: parent.modelData.color
                    }
                    QQC2.Label { text: parent.modelData.label; font: Kirigami.Theme.smallFont; opacity: 0.7 }
                }
            }
        }
    }
}
