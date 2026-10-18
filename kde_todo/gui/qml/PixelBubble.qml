import QtQuick
import org.kde.kirigami as Kirigami

// A speech bubble drawn in pixel steps, with game-style typed-out text.
// The tail sits on the left side (pointing left) or on top (pointing up).
Item {
    id: bubble

    property string fullText: ""  // the text as shown, without delay markers
    property var pauses: []  // extra milliseconds to wait before typing each character
    property int typed: 0  // characters shown so far
    property int typingSpeed: 28  // milliseconds per character
    property int unit: 2  // outline pixel size
    property string tailSide: "left"  // "left" or "up"
    property int maxWidth: 0  // whole bubble, including padding; 0 means about 26 characters
    property color fill: Kirigami.Theme.backgroundColor
    property color outline: Kirigami.Theme.highlightColor
    property color textColor: Kirigami.Theme.textColor
    readonly property int tail: unit * 3  // how far the tail sticks out
    readonly property bool up: tailSide === "up"
    readonly property bool active: typed > 0

    // Speech rhythm: "<#!delay-300-ms!#>" in a line pauses there for that long. Without a marker,
    // punctuation adds a natural pause: a short one after commas, a longer one after a sentence.
    function parse(text) {
        const marker = /<#!delay-(\d+)-ms!#>/g
        let shown = "", last = 0, m
        const waits = [], marked = []
        const add = (chunk) => {
            for (const ch of chunk) {
                waits[shown.length] = waits[shown.length] || 0  // keep a marker's pause
                shown += ch
            }
        }
        while ((m = marker.exec(text)) !== null) {
            add(text.slice(last, m.index))
            // The pause comes before the next character.
            waits[shown.length] = (waits[shown.length] || 0) + Number(m[1])
            marked[shown.length] = true
            last = marker.lastIndex
        }
        add(text.slice(last))
        waits.length = shown.length
        for (let i = 1; i < shown.length; i++) {
            if (marked[i])
                continue  // the line sets its own timing here
            const prev = shown[i - 1], next = shown[i]
            if (".!?".includes(prev) && (next === " " || next === "\n")) waits[i] += 220
            else if (".!?".includes(prev) && ".!?".includes(next)) waits[i] += 90
            else if (",;:".includes(prev) && next === " ") waits[i] += 110
        }
        return { shown: shown, waits: waits }
    }

    function say(text) {
        const parsed = parse(text)
        fullText = parsed.shown
        pauses = parsed.waits
        typed = 0
        holdTimer.stop()
        typeTimer.interval = typingSpeed + (pauses[0] || 0)
        typeTimer.restart()
    }

    function dismiss() {
        typeTimer.stop()
        holdTimer.stop()
        typed = 0
    }

    function snap(v) { return Math.ceil(v / unit) * unit }

    // Size from the full text, so the bubble doesn't grow while typing.
    readonly property int padX: unit * 4
    readonly property int padY: unit * 3
    readonly property int maxTextWidth: maxWidth > 0 ? maxWidth - padX * 2 : 26 * metrics.averageCharacterWidth
    readonly property int textWidth: Math.ceil(Math.min(measure.implicitWidth, maxTextWidth))
    readonly property int boxWidth: snap(textWidth + padX * 2)
    readonly property int boxHeight: snap(sizer.implicitHeight + padY * 2)

    width: boxWidth + (up ? 0 : tail)
    height: boxHeight + (up ? tail : 0)
    visible: active

    FontMetrics {
        id: metrics
        font: measure.font
    }
    Text {
        id: measure
        visible: false
        text: bubble.fullText
        font.family: pixelFont
        font.pixelSize: 11
    }
    Text {
        id: sizer
        visible: false
        width: bubble.textWidth
        text: bubble.fullText
        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        font: measure.font
    }

    Timer {
        id: typeTimer
        onTriggered: {
            bubble.typed++
            if (bubble.typed >= bubble.fullText.length) {
                holdTimer.interval = 1800 + bubble.fullText.length * 35
                holdTimer.restart()
            } else {
                interval = bubble.typingSpeed + (bubble.pauses[bubble.typed] || 0)
                restart()
            }
        }
    }
    Timer {
        id: holdTimer
        onTriggered: bubble.typed = 0
    }

    Canvas {
        id: canvas
        anchors.fill: parent
        onPaint: {
            const ctx = getContext("2d"), u = bubble.unit, up = bubble.up
            ctx.reset()
            // Drawn as a bubble with its tail on the left. For a tail on top, x and y are swapped:
            // the same drawing, mirrored across the diagonal.
            const px = (x, y, w, h, c) => {
                ctx.fillStyle = c
                if (up) ctx.fillRect(y, x, h, w)
                else ctx.fillRect(x, y, w, h)
            }
            const x0 = bubble.tail
            const w = up ? bubble.boxHeight : bubble.boxWidth
            const h = up ? bubble.boxWidth : bubble.boxHeight
            // Where the tail joins: near the bottom on the left, near the middle on top.
            const ty = up ? Math.max(2 * u, bubble.snap(bubble.boxWidth / 2) - 2 * u) : h - 6 * u
            const f = bubble.fill, o = bubble.outline
            // Fill with one-step notched corners.
            px(x0 + 2 * u, u, w - 4 * u, h - 2 * u, f)
            px(x0 + u, 2 * u, w - 2 * u, h - 4 * u, f)
            // Outline: straight edges plus a pixel at each inner corner.
            px(x0 + 2 * u, 0, w - 4 * u, u, o)
            px(x0 + 2 * u, h - u, w - 4 * u, u, o)
            px(x0 + w - u, 2 * u, u, h - 4 * u, o)
            px(x0 + u, u, u, u, o); px(x0 + w - 2 * u, u, u, u, o)
            px(x0 + u, h - 2 * u, u, u, o); px(x0 + w - 2 * u, h - 2 * u, u, u, o)
            // The tail's side, with an opening where the tail joins.
            px(x0, 2 * u, u, ty - 2 * u, o)
            px(x0, ty + 2 * u, u, h - 4 * u - ty, o)
            // Stepped tail.
            px(x0 - u, ty, u, u, o); px(x0, ty, u, u, f)
            px(x0 - 2 * u, ty + u, u, u, o); px(x0 - u, ty + u, 2 * u, u, f)
            px(x0 - 3 * u, ty + 2 * u, 3 * u, u, o)
        }
        Component.onCompleted: requestPaint()
    }
    onWidthChanged: canvas.requestPaint()
    onHeightChanged: canvas.requestPaint()
    onFillChanged: canvas.requestPaint()
    onOutlineChanged: canvas.requestPaint()

    Text {
        x: (bubble.up ? 0 : bubble.tail) + bubble.padX
        y: (bubble.up ? bubble.tail : 0) + bubble.padY
        width: bubble.textWidth
        text: bubble.fullText.slice(0, bubble.typed)
        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        color: bubble.textColor
        font: measure.font
        renderType: Text.NativeRendering
    }

    MouseArea {
        anchors.fill: parent
        onClicked: {
            // First click finishes typing, the next one closes the bubble.
            if (typeTimer.running) {
                typeTimer.stop()
                bubble.typed = bubble.fullText.length
                holdTimer.interval = 1800 + bubble.fullText.length * 35
                holdTimer.restart()
            } else {
                bubble.dismiss()
            }
        }
    }
}
