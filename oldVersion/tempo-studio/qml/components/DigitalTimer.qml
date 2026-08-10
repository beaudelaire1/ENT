import QtQuick

Item {
    id: root

    property real progress: 1
    property string timeText: "05:00"
    property color accentColor: "#8878ff"
    property color surfaceColor: "#0a0d14"
    property color borderColor: "#242c3d"
    property color textColor: "#f5f7fb"
    property color mutedColor: "#7e899e"

    implicitWidth: 650
    implicitHeight: 330

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width * 0.92, 650)
        height: Math.min(parent.height * 0.76, 275)
        radius: 26
        color: root.surfaceColor
        border.width: 1
        border.color: root.borderColor

        Rectangle {
            anchors.fill: parent
            anchors.margins: -12
            radius: 35
            z: -1
            color: Qt.rgba(root.accentColor.r, root.accentColor.g,
                           root.accentColor.b, 0.055)
        }

        Canvas {
            anchors.fill: parent
            opacity: 0.42
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.strokeStyle = root.borderColor
                ctx.lineWidth = 1
                for (var x = 38; x < width; x += 58) {
                    ctx.beginPath()
                    ctx.moveTo(x, 24)
                    ctx.lineTo(x, height - 24)
                    ctx.stroke()
                }
            }
        }

        Column {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -8
            spacing: 8

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: root.timeText
                color: root.textColor
                font.family: "Segoe UI Variable Display"
                font.pixelSize: Math.max(62, Math.min(92, root.width * 0.14))
                font.weight: Font.DemiBold
                font.letterSpacing: 4
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "CHRONOMÈTRE DE SCÈNE"
                color: root.mutedColor
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 9
                font.weight: Font.DemiBold
                font.letterSpacing: 2.4
            }
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: 44
            anchors.rightMargin: 44
            anchors.bottomMargin: 28
            height: 5
            radius: 3
            color: root.borderColor

            Rectangle {
                width: parent.width * root.progress
                height: parent.height
                radius: parent.radius
                color: root.accentColor

                Behavior on width {
                    NumberAnimation { duration: 300; easing.type: Easing.OutCubic }
                }
            }
        }
    }
}
