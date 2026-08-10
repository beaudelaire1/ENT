pragma ComponentBehavior: Bound

import QtQuick

Item {
    id: root

    property real progress: 1
    property string timeText: "05:00"
    property color accentColor: "#8878ff"
    property color textColor: "#f5f7fb"
    property color mutedColor: "#7e899e"
    property bool running: false
    property bool warning: false
    property int focusLevel: 2

    implicitWidth: 520
    implicitHeight: 480
    property real breath: 0

    SequentialAnimation on breath {
        loops: Animation.Infinite
        running: root.visible
        NumberAnimation {
            from: 0
            to: 1
            duration: 3900
            easing.type: Easing.InOutSine
        }
        NumberAnimation {
            from: 1
            to: 0
            duration: 4200
            easing.type: Easing.InOutSine
        }
    }

    Item {
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) * 0.72
        height: width

        Repeater {
            model: 3
            Rectangle {
                id: breathRing
                required property int index
                anchors.centerIn: parent
                width: parent.width * (0.58 + breathRing.index * 0.16)
                       + root.breath * (28 + breathRing.index * 10)
                height: width
                radius: width / 2
                color: "transparent"
                border.width: index === 0 ? 1.5 : 1
                border.color: Qt.rgba(root.accentColor.r, root.accentColor.g,
                                      root.accentColor.b,
                                      0.32 - breathRing.index * 0.075)
            }
        }

        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.48 + root.breath * 20
            height: width
            radius: width / 2
            color: Qt.rgba(root.accentColor.r, root.accentColor.g,
                           root.accentColor.b, 0.075 + root.breath * 0.035)

            Column {
                anchors.centerIn: parent
                spacing: 7

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: root.focusLevel < 3 || root.warning
                    text: root.timeText
                    color: root.textColor
                    font.family: "Segoe UI Variable Display"
                    font.pixelSize: 50
                    font.weight: Font.DemiBold
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: root.running
                          ? (root.breath > 0.52 ? "EXPIREZ" : "INSPIREZ")
                          : "CENTREZ-VOUS"
                    color: root.accentColor
                    font.family: "Segoe UI Variable Text"
                    font.pixelSize: 9
                    font.weight: Font.Bold
                    font.letterSpacing: 2.2
                }
            }
        }
    }

    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        text: root.focusLevel === 3
              ? "Le temps reste volontairement discret"
              : "Respirez · gardez votre rythme · regardez votre public"
        color: root.mutedColor
        font.family: "Segoe UI Variable Text"
        font.pixelSize: 10
        font.letterSpacing: 0.5
    }
}
