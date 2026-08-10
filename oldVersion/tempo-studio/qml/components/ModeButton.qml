import QtQuick
import QtQuick.Controls

Button {
    id: control

    property color accentColor: "#8878ff"
    property color surfaceColor: "#151a26"
    property color borderColor: "#242c3d"
    property color textColor: "#f5f7fb"
    property color mutedColor: "#7e899e"
    property string iconText: "◉"

    checkable: true
    implicitHeight: 66
    implicitWidth: 72
    padding: 4

    contentItem: Column {
        spacing: 3
        anchors.centerIn: parent

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: control.iconText
            color: control.checked || control.hovered
                   ? control.accentColor : control.mutedColor
            font.family: "Segoe UI Symbol"
            font.pixelSize: control.iconText === "01" ? 14 : 18
            font.weight: Font.DemiBold
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: control.text
            color: control.checked ? control.textColor : control.mutedColor
            font.family: "Segoe UI Variable Text"
            font.pixelSize: 10
            font.weight: Font.DemiBold
        }
    }

    background: Rectangle {
        radius: 11
        color: control.checked
               ? Qt.rgba(control.accentColor.r, control.accentColor.g,
                         control.accentColor.b, 0.13)
               : (control.hovered ? Qt.lighter(control.surfaceColor, 1.12)
                                  : control.surfaceColor)
        border.width: 1
        border.color: control.checked || control.hovered
                      ? control.accentColor : control.borderColor

        Behavior on color { ColorAnimation { duration: 160 } }
        Behavior on border.color { ColorAnimation { duration: 160 } }
    }
}
