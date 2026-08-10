import QtQuick

Item {
    id: root

    property real progress: 1
    property string timeText: "05:00"
    property color accentColor: "#8878ff"
    property color trackColor: "#232a39"
    property color textColor: "#f5f7fb"
    property color mutedColor: "#7e899e"
    property bool running: false

    implicitWidth: 460
    implicitHeight: 460

    Canvas {
        id: canvas
        anchors.fill: parent
        renderTarget: Canvas.FramebufferObject
        antialiasing: true

        property real sweep: root.progress
        Behavior on sweep {
            NumberAnimation { duration: 320; easing.type: Easing.OutCubic }
        }
        onSweepChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var cx = width / 2
            var cy = height / 2
            var radius = Math.min(width, height) * 0.385
            var line = Math.max(14, radius * 0.075)
            var start = -Math.PI / 2
            var end = start + Math.PI * 2 * sweep

            ctx.beginPath()
            ctx.lineWidth = line
            ctx.lineCap = "round"
            ctx.strokeStyle = root.trackColor
            ctx.arc(cx, cy, radius, 0, Math.PI * 2)
            ctx.stroke()

            if (sweep > 0.001) {
                ctx.beginPath()
                ctx.lineWidth = line + 18
                ctx.strokeStyle = Qt.rgba(root.accentColor.r, root.accentColor.g,
                                          root.accentColor.b, 0.07)
                ctx.arc(cx, cy, radius, start, end)
                ctx.stroke()

                ctx.beginPath()
                ctx.lineWidth = line + 8
                ctx.strokeStyle = Qt.rgba(root.accentColor.r, root.accentColor.g,
                                          root.accentColor.b, 0.15)
                ctx.arc(cx, cy, radius, start, end)
                ctx.stroke()

                var gradient = ctx.createLinearGradient(
                            cx - radius, cy - radius, cx + radius, cy + radius)
                gradient.addColorStop(0, Qt.lighter(root.accentColor, 1.55))
                gradient.addColorStop(0.55, root.accentColor)
                gradient.addColorStop(1, Qt.darker(root.accentColor, 1.22))
                ctx.beginPath()
                ctx.lineWidth = line
                ctx.strokeStyle = gradient
                ctx.arc(cx, cy, radius, start, end)
                ctx.stroke()

                var dx = cx + radius * Math.cos(end)
                var dy = cy + radius * Math.sin(end)
                ctx.beginPath()
                ctx.fillStyle = Qt.lighter(root.accentColor, 1.45)
                ctx.arc(dx, dy, line * 0.25, 0, Math.PI * 2)
                ctx.fill()
            }
        }

        Connections {
            target: root
            function onAccentColorChanged() { canvas.requestPaint() }
            function onTrackColorChanged() { canvas.requestPaint() }
        }
    }

    Column {
        anchors.centerIn: parent
        spacing: 8

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.timeText
            color: root.textColor
            font.family: "Segoe UI Variable Display"
            font.pixelSize: Math.max(58, Math.min(82, root.width * 0.17))
            font.weight: Font.DemiBold
            font.letterSpacing: 1
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "TEMPS RESTANT"
            color: root.mutedColor
            font.family: "Segoe UI Variable Text"
            font.pixelSize: 10
            font.weight: Font.DemiBold
            font.letterSpacing: 2.2
        }
    }
}
