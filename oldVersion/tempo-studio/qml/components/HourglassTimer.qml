import QtQuick

Item {
    id: root

    property real progress: 1
    property string timeText: "05:00"
    property color accentColor: "#8878ff"
    property color glassColor: "#dce5f5"
    property color frameColor: "#273044"
    property color textColor: "#f5f7fb"
    property color mutedColor: "#7e899e"
    property bool running: false
    property real phase: 0

    implicitWidth: 500
    implicitHeight: 510

    NumberAnimation on phase {
        from: 0
        to: 1
        duration: 1050
        loops: Animation.Infinite
        running: root.running
    }

    onPhaseChanged: glass.requestPaint()
    onProgressChanged: glass.requestPaint()
    onAccentColorChanged: glass.requestPaint()

    Canvas {
        id: glass
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        width: Math.min(parent.width * 0.72, 340)
        height: Math.min(parent.height * 0.74, 365)
        renderTarget: Canvas.FramebufferObject
        antialiasing: true

        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()

        function bottlePath(ctx, cx, cy, hw, hh) {
            var neck = hw * 0.10
            ctx.beginPath()
            ctx.moveTo(cx - hw, cy - hh)
            ctx.bezierCurveTo(cx - hw * 0.94, cy - hh * 0.46,
                              cx - hw * 0.23, cy - hh * 0.19,
                              cx - neck, cy)
            ctx.bezierCurveTo(cx - hw * 0.23, cy + hh * 0.19,
                              cx - hw * 0.94, cy + hh * 0.46,
                              cx - hw, cy + hh)
            ctx.lineTo(cx + hw, cy + hh)
            ctx.bezierCurveTo(cx + hw * 0.94, cy + hh * 0.46,
                              cx + hw * 0.23, cy + hh * 0.19,
                              cx + neck, cy)
            ctx.bezierCurveTo(cx + hw * 0.23, cy - hh * 0.19,
                              cx + hw * 0.94, cy - hh * 0.46,
                              cx + hw, cy - hh)
            ctx.closePath()
        }

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var cx = width / 2
            var cy = height / 2
            var hh = height * 0.405
            var hw = width * 0.315
            var p = Math.max(0, Math.min(1, root.progress))
            var received = 1 - p

            // Halo diffus autour du verre.
            bottlePath(ctx, cx, cy, hw, hh)
            ctx.lineWidth = 18
            ctx.strokeStyle = Qt.rgba(root.accentColor.r, root.accentColor.g,
                                      root.accentColor.b, 0.08)
            ctx.stroke()

            // Verre légèrement teinté.
            bottlePath(ctx, cx, cy, hw, hh)
            var glassGradient = ctx.createLinearGradient(cx - hw, 0, cx + hw, 0)
            glassGradient.addColorStop(0, Qt.rgba(root.glassColor.r,
                                                   root.glassColor.g,
                                                   root.glassColor.b, 0.02))
            glassGradient.addColorStop(0.28, Qt.rgba(root.glassColor.r,
                                                      root.glassColor.g,
                                                      root.glassColor.b, 0.13))
            glassGradient.addColorStop(0.58, Qt.rgba(root.glassColor.r,
                                                      root.glassColor.g,
                                                      root.glassColor.b, 0.025))
            glassGradient.addColorStop(1, Qt.rgba(root.glassColor.r,
                                                   root.glassColor.g,
                                                   root.glassColor.b, 0.09))
            ctx.fillStyle = glassGradient
            ctx.fill()

            // Limite tout le sable à l’intérieur du verre.
            ctx.save()
            bottlePath(ctx, cx, cy, hw - 4, hh - 5)
            ctx.clip()

            var sandGradient = ctx.createLinearGradient(0, cy - hh, 0, cy + hh)
            sandGradient.addColorStop(0, Qt.lighter(root.accentColor, 1.55))
            sandGradient.addColorStop(0.52, root.accentColor)
            sandGradient.addColorStop(1, Qt.darker(root.accentColor, 1.30))
            ctx.fillStyle = sandGradient

            // Chambre haute : surface plane, volume convergeant vers le goulot.
            if (p > 0.001) {
                var upperTop = cy - hh + 13
                var surfaceY = upperTop + (hh - 17) * (1 - p)
                var surfaceHalf = hw * (0.89 - 0.73 * (1 - p))
                ctx.beginPath()
                ctx.moveTo(cx - surfaceHalf, surfaceY)
                ctx.quadraticCurveTo(cx, surfaceY + 3, cx + surfaceHalf, surfaceY)
                ctx.lineTo(cx + hw * 0.085, cy - 3)
                ctx.lineTo(cx - hw * 0.085, cy - 3)
                ctx.closePath()
                ctx.fill()

                // Quelques grains sur la surface pour éviter l’aspect géométrique.
                ctx.fillStyle = Qt.lighter(root.accentColor, 1.35)
                for (var grain = 0; grain < 11; grain++) {
                    var gx = cx - surfaceHalf * 0.82
                             + (grain / 10) * surfaceHalf * 1.64
                    var gy = surfaceY - 1 - Math.sin(grain * 2.7) * 1.8
                    ctx.beginPath()
                    ctx.arc(gx, gy, 1.2 + (grain % 3) * 0.25, 0, Math.PI * 2)
                    ctx.fill()
                }
            }

            // Chambre basse : tas conique qui monte et s’élargit.
            var floorY = cy + hh - 10
            var pileHeight = received * hh * 0.79
            var pileHalf = hw * (0.15 + received * 0.74)
            if (received > 0.001) {
                ctx.fillStyle = sandGradient
                ctx.beginPath()
                ctx.moveTo(cx - pileHalf, floorY)
                ctx.quadraticCurveTo(cx - pileHalf * 0.56,
                                     floorY - pileHeight * 0.17,
                                     cx, floorY - pileHeight)
                ctx.quadraticCurveTo(cx + pileHalf * 0.56,
                                     floorY - pileHeight * 0.17,
                                     cx + pileHalf, floorY)
                ctx.closePath()
                ctx.fill()
            }

            // Filet continu et particules mobiles pendant l’écoulement.
            if (root.running && p > 0.001 && p < 0.999) {
                var streamEnd = floorY - pileHeight + 2
                ctx.beginPath()
                ctx.lineWidth = 3
                ctx.lineCap = "round"
                ctx.strokeStyle = root.accentColor
                ctx.moveTo(cx, cy - 2)
                ctx.lineTo(cx, streamEnd)
                ctx.stroke()

                var travel = Math.max(2, streamEnd - cy)
                ctx.fillStyle = Qt.lighter(root.accentColor, 1.55)
                for (var i = 0; i < 7; i++) {
                    var offset = (root.phase * 1.65 + i / 7) % 1
                    var py = cy + 2 + travel * offset
                    var px = cx + Math.sin(i * 3.7) * 1.9
                    ctx.beginPath()
                    ctx.arc(px, py, 1.1 + (i % 2) * 0.65, 0, Math.PI * 2)
                    ctx.fill()
                }
            }
            ctx.restore()

            // Contour et reflets du verre.
            bottlePath(ctx, cx, cy, hw, hh)
            ctx.lineWidth = 2
            ctx.strokeStyle = Qt.rgba(root.glassColor.r, root.glassColor.g,
                                      root.glassColor.b, 0.60)
            ctx.stroke()

            ctx.beginPath()
            ctx.moveTo(cx - hw * 0.76, cy - hh * 0.77)
            ctx.bezierCurveTo(cx - hw * 0.72, cy - hh * 0.46,
                              cx - hw * 0.28, cy - hh * 0.23,
                              cx - hw * 0.14, cy - hh * 0.07)
            ctx.lineWidth = 3.2
            ctx.lineCap = "round"
            ctx.strokeStyle = Qt.rgba(1, 1, 1, 0.48)
            ctx.stroke()

            // Socles métalliques.
            var capW = hw * 1.20
            var capH = 15
            var capGradient = ctx.createLinearGradient(cx - capW, 0, cx + capW, 0)
            capGradient.addColorStop(0, root.frameColor)
            capGradient.addColorStop(0.50, Qt.lighter(root.frameColor, 1.65))
            capGradient.addColorStop(1, root.frameColor)
            ctx.fillStyle = capGradient
            var capYs = [cy - hh - capH / 2, cy + hh - capH / 2]
            for (var c = 0; c < capYs.length; c++) {
                var y = capYs[c]
                ctx.beginPath()
                ctx.roundedRect(cx - capW, y, capW * 2, capH, 7, 7)
                ctx.fill()
            }
        }
    }

    Column {
        anchors.top: glass.bottom
        anchors.topMargin: 7
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 3

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.timeText
            color: root.textColor
            font.family: "Segoe UI Variable Display"
            font.pixelSize: 47
            font.weight: Font.DemiBold
            font.letterSpacing: 1
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "ÉCOULEMENT RÉEL"
            color: root.mutedColor
            font.family: "Segoe UI Variable Text"
            font.pixelSize: 9
            font.weight: Font.DemiBold
            font.letterSpacing: 2
        }
    }
}
