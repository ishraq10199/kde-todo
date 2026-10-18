import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

// A small rounded label. The colour lives in the tint and border; the text keeps the normal
// text colour, so it stays readable in any colour scheme.
Rectangle {
    id: pill

    property alias text: label.text
    property string tag: ""  // when set, shows the tag and picks its colour
    property color tint: tag ? tagTint(tag) : Kirigami.Theme.highlightColor
    property string iconName: ""
    property bool removable: false

    signal removeClicked()

    // The same tag always gets the same colour, picked from the theme.
    function tagTint(name) {
        const colours = [Kirigami.Theme.highlightColor, Kirigami.Theme.linkColor,
                         Kirigami.Theme.visitedLinkColor, Kirigami.Theme.neutralTextColor]
        let hash = 0
        for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) >>> 0
        return colours[hash % colours.length]
    }

    implicitWidth: content.implicitWidth + Kirigami.Units.largeSpacing
    implicitHeight: content.implicitHeight + Kirigami.Units.smallSpacing / 2
    radius: height / 2
    color: Qt.alpha(tint, 0.2)
    border.width: 1
    border.color: Qt.alpha(tint, 0.6)

    Row {
        id: content
        anchors.centerIn: parent
        spacing: Kirigami.Units.smallSpacing / 2

        Kirigami.Icon {
            visible: pill.iconName !== ""
            source: pill.iconName
            width: visible ? label.font.pixelSize || Kirigami.Units.iconSizes.small : 0
            height: width
            anchors.verticalCenter: parent.verticalCenter
            color: pill.tint
            isMask: true
        }
        QQC2.Label {
            id: label
            text: pill.tag
            font: Kirigami.Theme.smallFont
            color: Kirigami.Theme.textColor
        }
        QQC2.AbstractButton {
            visible: pill.removable
            width: visible ? label.implicitHeight : 0
            height: width
            anchors.verticalCenter: parent.verticalCenter
            onClicked: pill.removeClicked()
            contentItem: Kirigami.Icon {
                source: "edit-delete-remove"
                color: Kirigami.Theme.textColor
                isMask: true
                opacity: parent.hovered ? 1 : 0.6
            }
            QQC2.ToolTip.text: `Remove ${pill.tag}`
            QQC2.ToolTip.visible: hovered
            QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
        }
    }
}
