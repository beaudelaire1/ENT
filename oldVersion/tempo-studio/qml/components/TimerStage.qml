pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts

Item {
    id: root

    required property var controller
    property color backgroundColor: "#0d1119"
    property color surfaceColor: "#111722"
    property color borderColor: "#242c3d"
    property color textColor: "#f5f7fb"
    property color mutedColor: "#7e899e"
    property color accentColor: "#8878ff"
    property color warningColor: "#ffb84d"
    property color dangerColor: "#ff4d6d"

    property color liveAccent: root.controller.finished ? dangerColor
                                                   : (root.controller.warning
                                                      ? warningColor : accentColor)
    property real ambientPhase: 0

    function flash(kind) {
        flashLayer.color = kind === "finished" ? dangerColor : warningColor
        cueFlash.restart()
    }

    NumberAnimation on ambientPhase {
        from: 0
        to: 1
        duration: root.controller.ambience === "Calme" ? 16000 : 10500
        loops: Animation.Infinite
        running: root.visible
    }

    Rectangle {
        anchors.fill: parent
        color: root.backgroundColor
        radius: 22
        clip: true

        Canvas {
            id: ambientCanvas
            anchors.fill: parent
            renderTarget: Canvas.FramebufferObject
            antialiasing: true

            property real phase: root.ambientPhase
            onPhaseChanged: requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()

                // Halo lent : anime l’ambiance sans attirer l’attention.
                var driftX = width * (0.48 + Math.sin(phase * Math.PI * 2) * 0.055)
                var driftY = height * (0.42 + Math.cos(phase * Math.PI * 2) * 0.035)
                var glow = ctx.createRadialGradient(
                            driftX, driftY, 0,
                            driftX, driftY, Math.min(width, height) * 0.63)
                glow.addColorStop(0, Qt.rgba(root.liveAccent.r,
                                             root.liveAccent.g,
                                             root.liveAccent.b, 0.115))
                glow.addColorStop(0.48, Qt.rgba(root.liveAccent.r,
                                                root.liveAccent.g,
                                                root.liveAccent.b, 0.025))
                glow.addColorStop(1, Qt.rgba(root.liveAccent.r,
                                             root.liveAccent.g,
                                             root.liveAccent.b, 0))
                ctx.fillStyle = glow
                ctx.fillRect(0, 0, width, height)

                // Grille technique extrêmement discrète.
                ctx.strokeStyle = Qt.rgba(root.borderColor.r,
                                          root.borderColor.g,
                                          root.borderColor.b, 0.28)
                ctx.lineWidth = 1
                var spacing = 52
                for (var x = 0; x <= width; x += spacing) {
                    ctx.beginPath()
                    ctx.moveTo(x, 0)
                    ctx.lineTo(x, height)
                    ctx.stroke()
                }
                for (var y = 0; y <= height; y += spacing) {
                    ctx.beginPath()
                    ctx.moveTo(0, y)
                    ctx.lineTo(width, y)
                    ctx.stroke()
                }

                // Points d’énergie lents et déterministes.
                for (var i = 0; i < 18; i++) {
                    var orbit = phase * Math.PI * 2 + i * 2.17
                    var px = ((i * 89) % Math.max(1, width))
                             + Math.sin(orbit) * 11
                    var py = ((i * 137) % Math.max(1, height))
                             + Math.cos(orbit * 0.72) * 8
                    ctx.beginPath()
                    ctx.fillStyle = Qt.rgba(root.liveAccent.r,
                                            root.liveAccent.g,
                                            root.liveAccent.b,
                                            0.10 + (i % 3) * 0.025)
                    ctx.arc(px, py, 1 + (i % 2) * 0.7, 0, Math.PI * 2)
                    ctx.fill()
                }
            }
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 26
            spacing: 0

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 38
                spacing: 9

                Rectangle {
                    Layout.preferredWidth: 7
                    Layout.preferredHeight: 7
                    radius: 4
                    color: root.liveAccent
                }
                Text {
                    text: root.controller.running ? "SESSION EN COURS"
                                             : (root.controller.finished
                                                ? "SESSION TERMINÉE"
                                                : "PRÊT POUR LA SCÈNE")
                    color: root.liveAccent
                    font.family: "Segoe UI Variable Text"
                    font.pixelSize: 9
                    font.weight: Font.Bold
                    font.letterSpacing: 1.6
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: root.controller.ambience.toUpperCase()
                          + "  ·  FOCUS " + root.controller.focusLevel
                    color: root.mutedColor
                    font.family: "Segoe UI Variable Text"
                    font.pixelSize: 9
                    font.weight: Font.DemiBold
                    font.letterSpacing: 1.2
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.topMargin: 4
                text: root.controller.sessionTitle.toUpperCase()
                color: root.mutedColor
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 10
                font.weight: Font.DemiBold
                font.letterSpacing: 2.1
            }

            Loader {
                id: timerLoader
                Layout.fillWidth: true
                Layout.fillHeight: true
                sourceComponent: {
                    if (root.controller.mode === "Sablier") return hourglassComponent
                    if (root.controller.mode === "Digital") return digitalComponent
                    if (root.controller.mode === "Zen") return zenComponent
                    return ringComponent
                }
            }

            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: statusText.implicitWidth + 32
                Layout.preferredHeight: 27
                radius: 14
                color: Qt.rgba(root.liveAccent.r, root.liveAccent.g,
                               root.liveAccent.b, 0.10)
                border.width: 1
                border.color: Qt.rgba(root.liveAccent.r, root.liveAccent.g,
                                      root.liveAccent.b, 0.34)

                Text {
                    id: statusText
                    anchors.centerIn: parent
                    text: root.controller.finished ? "TEMPS ÉCOULÉ"
                                              : (root.controller.running
                                                 ? "RESTEZ DANS VOTRE RYTHME"
                                                 : "ESPACE POUR DÉMARRER")
                    color: root.liveAccent
                    font.family: "Segoe UI Variable Text"
                    font.pixelSize: 9
                    font.weight: Font.Bold
                    font.letterSpacing: 1.6
                }
            }
        }

        Rectangle {
            id: flashLayer
            anchors.fill: parent
            radius: 22
            color: root.warningColor
            opacity: 0
        }

        SequentialAnimation {
            id: cueFlash
            NumberAnimation {
                target: flashLayer
                property: "opacity"
                from: 0
                to: 0.16
                duration: 170
                easing.type: Easing.OutQuad
            }
            NumberAnimation {
                target: flashLayer
                property: "opacity"
                to: 0
                duration: 850
                easing.type: Easing.OutCubic
            }
        }
    }

    Connections {
        target: root.controller
        function onCue(kind) { root.flash(kind) }
    }

    Component {
        id: ringComponent
        RingTimer {
            anchors.centerIn: parent
            width: Math.min(parent.width, parent.height) * 0.84
            height: width
            progress: root.controller.progress
            timeText: root.controller.formattedTime
            running: root.controller.running
            accentColor: root.liveAccent
            trackColor: root.borderColor
            textColor: root.textColor
            mutedColor: root.mutedColor
        }
    }

    Component {
        id: hourglassComponent
        HourglassTimer {
            anchors.centerIn: parent
            width: Math.min(parent.width, 590)
            height: Math.min(parent.height, 520)
            progress: root.controller.progress
            timeText: root.controller.formattedTime
            running: root.controller.running
            accentColor: root.liveAccent
            glassColor: root.textColor
            frameColor: root.borderColor
            textColor: root.textColor
            mutedColor: root.mutedColor
        }
    }

    Component {
        id: digitalComponent
        DigitalTimer {
            anchors.centerIn: parent
            width: Math.min(parent.width, 700)
            height: Math.min(parent.height, 390)
            progress: root.controller.progress
            timeText: root.controller.formattedTime
            accentColor: root.liveAccent
            surfaceColor: root.surfaceColor
            borderColor: root.borderColor
            textColor: root.textColor
            mutedColor: root.mutedColor
        }
    }

    Component {
        id: zenComponent
        ZenTimer {
            anchors.centerIn: parent
            width: Math.min(parent.width, 620)
            height: Math.min(parent.height, 520)
            progress: root.controller.progress
            timeText: root.controller.formattedTime
            running: root.controller.running
            warning: root.controller.warning
            focusLevel: root.controller.focusLevel
            accentColor: root.liveAccent
            textColor: root.textColor
            mutedColor: root.mutedColor
        }
    }
}
