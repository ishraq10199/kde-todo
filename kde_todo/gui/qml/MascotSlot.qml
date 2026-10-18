import QtQuick
import QtQuick.Window
import org.kde.kirigami as Kirigami
import "sprites.js" as Sprites

// The mascot: a 16x16 pixel sprite coloured from the theme, plus a pixel speech bubble.
// `mood` comes from backend.mascotState: idle, working, resting, celebrate, overtime or sleepy.
Item {
    id: slot

    property string mood: "idle"
    property string character: "Mochi"
    property bool talks: true  // false for previews
    property int zoom: 4
    property int bubbleWidth: 0  // widest the bubble under the mascot may be
    property int frame: 0

    // Body, background and text come from the focused-window palette, so the mascot doesn't
    // fade when the window loses focus but still follows colour scheme changes live.
    // Effect colours aren't in that palette: take them from Kirigami while the window is focused.
    readonly property bool windowActive: slot.Window.active
    readonly property var liveEffects: ({
        positive: String(Kirigami.Theme.positiveTextColor),
        neutral: String(Kirigami.Theme.neutralTextColor),
        negative: String(Kirigami.Theme.negativeTextColor),
    })
    property var effects: liveEffects
    onLiveEffectsChanged: if (windowActive) effects = liveEffects
    onWindowActiveChanged: if (windowActive) effects = liveEffects
    Component.onCompleted: effects = liveEffects

    SystemPalette { id: activePalette; colorGroup: SystemPalette.Active }

    readonly property var theme: ({
        body: String(activePalette.highlight),
        background: String(activePalette.base),
        text: String(activePalette.text),
        positive: effects.positive,
        neutral: effects.neutral,
        negative: effects.negative,
    })

    implicitWidth: Sprites.SIZE * zoom
    implicitHeight: Sprites.SIZE * zoom
    z: 2  // keep the bubble above whatever sits next to the mascot

    onThemeChanged: canvas.requestPaint()
    onMoodChanged: canvas.requestPaint()
    onCharacterChanged: canvas.requestPaint()

    Timer {
        // Animate only while the window is on screen, and not at all when animations are turned off.
        interval: 250
        repeat: true
        running: slot.visible && slot.Window.window !== null && slot.Window.window.visible
                 && Kirigami.Units.longDuration > 0
        onTriggered: {
            slot.frame++
            canvas.requestPaint()
        }
    }

    Canvas {
        id: canvas
        anchors.fill: parent
        onPaint: Sprites.draw(getContext("2d"), slot.character, slot.mood, slot.frame, slot.theme, slot.zoom)
    }

    MouseArea {
        anchors.fill: parent
        enabled: slot.talks
        cursorShape: Qt.PointingHandCursor
        onClicked: backend.pokeMascot()
    }

    Connections {
        target: slot.talks ? backend : null
        function onMascotSaid(text) { bubble.say(text) }
    }

    // Under the mascot, centred, tail pointing up. It floats over the card instead of taking
    // layout space, so the card doesn't change size when it appears.
    PixelBubble {
        id: bubble
        tailSide: "up"
        maxWidth: slot.bubbleWidth
        fill: slot.theme.background
        outline: slot.theme.body
        textColor: slot.theme.text
        x: Math.round((slot.width - width) / 2)
        y: slot.height - slot.zoom
    }
}
