.pragma library

// 16x16 mascot sprites, drawn in a 20x20 cell (room above and beside for effects).
// Grid keys: . empty, o outline, b body, l body light, d body shade,
//            w white, k eye ink, s screen, p cheek/pink, a antenna light.

var CHARACTERS = ["Mochi", "Blip", "Pip", "Tock", "Wisp"]
var SIZE = 20, PAD_X = 2, PAD_Y = 4

var MASCOTS = {
    Blip: {
        eyes: [[5, 9], [9, 9]], mouth: [7, 12],
        grid: [
            "................",
            "................",
            "................",
            "................",
            "......oooo......",
            "....oolllboo....",
            "...olllbbbbbo...",
            "..olbbbbbbbbbo..",
            "..obbbbbbbbbbo..",
            ".obbbbbbbbbbbbo.",
            ".obbbbbbbbbbbbo.",
            ".obbbbbbbbbbbdo.",
            "obbbbbbbbbbbbddo",
            "odbbbbbbbbbbbddo",
            ".oddddddddddddo.",
            "..oooooooooooo..",
        ],
        hook: function (g, mood, f) {
            if ((mood === "celebrate" && f % 6 === 0) || (mood === "working" && f % 2 === 1)) {
                g[4] = "................"; g[5] = "....oooooooo....";
            }
        },
    },
    Pip: {
        eyes: [[5, 6], [9, 6]], mouth: [7, 9], eyeInk: "l", onScreen: true,
        grid: [
            "................",
            ".......a........",
            ".......o........",
            "..oooooooooooo..",
            "..ollllllllllo..",
            "..olsssssssslo..",
            "..obssssssssdo..",
            "..obssssssssdo..",
            "..obssssssssdo..",
            "..obssssssssdo..",
            "..oddddddddddo..",
            "..oooooooooooo..",
            "....obbbbbbo....",
            "...obbbbbbbbo...",
            "...oddddddddo...",
            "...oo......oo...",
        ],
        hook: function (g, mood, f, pal, t) {
            var lights = {
                working: f % 2 ? t.positive : pal.l,
                overtime: f % 2 ? t.negative : t.neutral,
                sleepy: pal.d,
                celebrate: [t.positive, t.neutral, t.negative, pal.l][f % 4],
            }
            pal.a = lights[mood] || pal.l
        },
    },
    Tock: {
        eyes: [[5, 7], [9, 7]], mouth: [7, 10],
        grid: [
            "................",
            "..ooo......ooo..",
            ".obbdo....odbbo.",
            ".oo.oooooooo.oo.",
            "...obbbbbbbbo...",
            "..obllllllllbo..",
            ".obllllllllllbo.",
            ".obllllllllllbo.",
            ".obllllllllllbo.",
            ".obllllllllllbo.",
            ".obllllllllllbo.",
            "..obllllllllbo..",
            "...obbbbbbbbo...",
            "....oooooooo....",
            "...oo......oo...",
            "..ooo......ooo..",
        ],
        hook: function (g, mood, f) {
            if (mood === "overtime" || mood === "celebrate") {
                var shift = f % 2 ? 1 : -1
                g[1] = shiftRow(g[1], shift); g[2] = shiftRow(g[2], shift)
            }
            if (mood === "working") g[5] = setAt(g[5], f % 2 ? 7 : 8, "k")
        },
    },
    Mochi: {
        eyes: [[4, 7], [10, 7]], mouth: [7, 9], catMouth: true,
        grid: [
            "................",
            "................",
            "..oo........oo..",
            "..opo......opo..",
            "..obboooooobbo..",
            "..obbbbbbbbbbo..",
            ".obbbbbbbbbbbbo.",
            ".obbbbbbbbbbbbo.",
            ".obbbbbbbbbbbbo.",
            ".obbbbbbbbbbbdo.",
            "..obbbbbbbbbdo..",
            "...obbbbbbbbo...",
            "..obbllllbbbbo..",
            "..obbllllbbbbo..",
            "..obdddddddbdo..",
            "..oooooooooooo..",
        ],
        hook: function (g, mood, f) {
            var fast = mood === "working" || mood === "celebrate" || mood === "overtime"
            var up = fast ? f % 2 : Math.floor(f / 2) % 2
            if (mood === "sleepy") { g[14] = setAt(g[14], 14, "d"); g[15] = setAt(g[15], 15, "d"); return }
            var tail = up ? [[14, 12], [15, 11], [15, 10]] : [[14, 12], [15, 12], [15, 11]]
            for (var i = 0; i < tail.length; i++) g[tail[i][1]] = setAt(g[tail[i][1]], tail[i][0], "d")
        },
    },
    Wisp: {
        eyes: [[5, 9], [9, 9]], mouth: [7, 12],
        grid: [
            "................",
            ".......oo.......",
            "......olbo......",
            "......olbo......",
            ".....olbbbo.....",
            "....olbbbbbo....",
            "...olbbbbbbbo...",
            "..olbbbbbbbbbo..",
            "..obbbbbbbbbbo..",
            ".olbbbbbbbbbbbo.",
            ".obbbbbbbbbbbbo.",
            ".obbbbbbbbbbbdo.",
            ".obbbbbbbbbbbdo.",
            "..obbbbbbbbbdo..",
            "...oddddddddo...",
            "....oo.oo.oo....",
        ],
        hook: function (g, mood, f) {
            var shift = mood === "sleepy" ? 0 : (f % 2 ? 1 : 0) * (mood === "overtime" ? 2 : 1)
            for (var r = 1; r <= 3; r++) g[r] = shiftRow(g[r], shift)
            if (mood === "working" && f % 2 === 0) g[0] = ".......oo......."
            if (f % 2) g[15] = ".....oo.oo.oo..."
        },
    },
}

// Vertical bob per mood, one entry per frame (4 frames a second).
var BOB = {
    idle: [0, 0, 0, 0, 1, 1, 1, 1], working: [0, 1], resting: [0, 0, 0, 1, 1, 1],
    celebrate: [0, -2, -3, -3, -2, 0], overtime: [0, 0], sleepy: [0, 0, 0, 0, 1, 1, 1, 1],
}
var SHAKE = { overtime: [-1, 1] }

function shiftRow(row, n) {
    if (n > 0) return new Array(n + 1).join(".") + row.slice(0, row.length - n)
    if (n < 0) return row.slice(-n) + new Array(-n + 1).join(".")
    return row
}

function setAt(row, x, ch) { return row.slice(0, x) + ch + row.slice(x + 1) }

function hexToRgb(h) {
    var n = parseInt(h.slice(1, 7), 16)
    return [n >> 16, (n >> 8) & 255, n & 255]
}

function mix(a, b, t) {
    var A = hexToRgb(a), B = hexToRgb(b), out = "#"
    for (var i = 0; i < 3; i++) {
        var v = Math.round(A[i] + (B[i] - A[i]) * t).toString(16)
        out += v.length < 2 ? "0" + v : v
    }
    return out
}

function luminance(h) {
    var c = hexToRgb(h)
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
}

// Theme colours come in as "#rrggbb" strings: body (accent), background, text,
// positive, neutral, negative. Darks use the "soft" level: mixed toward the
// theme's darkest colour instead of black.
function palette(t) {
    var dark = luminance(t.background) < luminance(t.text) ? t.background : t.text
    return {
        b: t.body,
        l: mix(t.body, "#ffffff", 0.45),
        d: mix(t.body, "#000000", 0.3),
        o: mix(t.body, dark, 0.62),
        k: mix(t.body, dark, 0.72),
        s: mix(t.body, dark, 0.8),
        w: "#f8f9ff",
        p: t.negative,
        a: mix(t.body, "#ffffff", 0.45),
    }
}

function face(m, mood, f, t) {
    var px = []
    function put(x, y, c) { px.push([x, y, c]) }
    var ink = m.eyeInk || "k"
    var blink = mood === "idle" && f % 16 === 15
    for (var i = 0; i < m.eyes.length; i++) {
        var ex = m.eyes[i][0], ey = m.eyes[i][1]
        if (mood === "celebrate") {
            put(ex, ey + 1, ink); put(ex + 1, ey, ink); put(ex + 2, ey + 1, ink)
        } else if (mood === "resting" || mood === "sleepy" || blink) {
            put(ex, ey + 1, ink); put(ex + 1, ey + 1, ink)
        } else if (mood === "working") {
            put(ex, ey + 1, ink); put(ex + 1, ey + 1, ink); put(ex, ey, ink); put(ex + 1, ey, m.onScreen ? ink : "o")
        } else if (mood === "overtime") {
            var white = m.onScreen ? "l" : "w"
            put(ex, ey, white); put(ex + 1, ey, white); put(ex, ey + 1, white)
            put(ex + 1, ey + 1, m.onScreen ? t.negative : "k")
        } else {
            put(ex, ey, "w"); put(ex + 1, ey, ink); put(ex, ey + 1, ink); put(ex + 1, ey + 1, ink)
        }
    }
    if ((mood === "resting" || mood === "celebrate") && !m.onScreen) {
        put(m.eyes[0][0] - 1, m.eyes[0][1] + 2, "p"); put(m.eyes[1][0] + 2, m.eyes[1][1] + 2, "p")
    }
    var mx = m.mouth[0], my = m.mouth[1]
    if (m.catMouth && mood !== "celebrate" && mood !== "overtime") {
        put(mx - 1, my, ink); put(mx, my + 1, ink); put(mx + 1, my + 1, ink); put(mx + 2, my, ink)
        put(mx, my, "p"); put(mx + 1, my, "p")
    } else if (mood === "celebrate") {
        put(mx, my, ink); put(mx + 1, my, ink); put(mx, my + 1, "p"); put(mx + 1, my + 1, "p")
    } else if (mood === "overtime") {
        put(mx - 1, my + 1, ink); put(mx, my, ink); put(mx + 1, my + 1, ink); put(mx + 2, my, ink)
    } else if (mood === "sleepy") {
        put(mx + (f % 8 < 4 ? 0 : 1), my, ink)
    } else if (mood === "resting") {
        put(mx - 1, my, ink); put(mx, my + 1, ink); put(mx + 1, my + 1, ink); put(mx + 2, my, ink)
    } else {
        put(mx, my, ink); put(mx + 1, my, ink)
    }
    return px
}

var Z = [[0, 0], [1, 0], [2, 0], [1, 1], [0, 2], [1, 2], [2, 2]]
var SMALL_Z = [[0, 0], [1, 0], [1, 1], [0, 2], [1, 2]]

// Effects in cell coordinates.
function effects(mood, f, pal, t) {
    var px = [], i
    if (mood === "sleepy") {
        var rise = f % 8
        for (i = 0; i < Z.length; i++) px.push([15 + Z[i][0], 4 - Math.floor(rise / 2) + Z[i][1], mix(pal.w, pal.b, 0.3)])
        if (rise > 3) for (i = 0; i < SMALL_Z.length; i++)
            px.push([12 + SMALL_Z[i][0], 2 - (rise - 4) + SMALL_Z[i][1], mix(pal.w, pal.b, 0.5)])
    } else if (mood === "celebrate") {
        var colours = [t.positive, t.neutral, t.negative, pal.l]
        var spots = [[1, 3], [17, 2], [3, 0], [15, 6], [0, 9], [18, 10], [9, 0], [12, 1]]
        for (i = 0; i < spots.length; i++)
            if ((i + f) % 3 !== 0) px.push([spots[i][0], (spots[i][1] + f) % 12, colours[(i + f) % colours.length]])
    } else if (mood === "overtime") {
        if (f % 2 === 0) { px.push([17, 1, t.negative]); px.push([17, 2, t.negative]); px.push([17, 3, t.negative]); px.push([17, 5, t.negative]) }
        var drop = [[2, 6], [1, 7], [2, 7], [1, 8], [2, 8]]
        for (i = 0; i < drop.length; i++) px.push([drop[i][0], drop[i][1] + (f % 2), pal.w])
    } else if (mood === "resting") {
        var steam = f % 6
        for (i = 0; i < 3; i++) px.push([16 + ((i + steam) % 2), 6 - i - Math.floor(steam / 2), mix(pal.w, pal.b, 0.4)])
        var cup = [[15, 8], [16, 8], [17, 8], [15, 9], [16, 9], [17, 9], [18, 9]]
        for (i = 0; i < cup.length; i++) px.push([cup[i][0], cup[i][1], t.neutral])
    } else if (mood === "working") {
        var dots = [[17, 4], [18, 5], [17, 6], [16, 5]]
        px.push([dots[f % 4][0], dots[f % 4][1], t.positive])
    }
    return px
}

function draw(ctx, name, mood, f, theme, zoom) {
    var m = MASCOTS[name] || MASCOTS.Mochi
    var pal = palette(theme)
    var g = m.grid.slice()
    if (m.hook) m.hook(g, mood, f, pal, theme)
    var bob = BOB[mood] || [0], shake = SHAKE[mood]
    var dy = bob[f % bob.length], dx = shake ? shake[f % shake.length] : 0
    function colour(c) { return c.charAt(0) === "#" ? c : pal[c] }
    function dot(x, y, c) {
        if (x < 0 || y < 0 || x >= SIZE || y >= SIZE) return
        ctx.fillStyle = colour(c)
        ctx.fillRect(x * zoom, y * zoom, zoom, zoom)
    }
    ctx.clearRect(0, 0, SIZE * zoom, SIZE * zoom)
    for (var y = 0; y < g.length; y++)
        for (var x = 0; x < g[y].length; x++)
            if (g[y].charAt(x) !== ".") dot(x + PAD_X + dx, y + PAD_Y + dy, g[y].charAt(x))
    var fp = face(m, mood, f, theme)
    for (var i = 0; i < fp.length; i++) dot(fp[i][0] + PAD_X + dx, fp[i][1] + PAD_Y + dy, fp[i][2])
    var fx = effects(mood, f, pal, theme)
    for (var j = 0; j < fx.length; j++) dot(fx[j][0], fx[j][1], fx[j][2])
}
