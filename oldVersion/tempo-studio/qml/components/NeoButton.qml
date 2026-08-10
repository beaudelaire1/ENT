import QtQuick
import QtQuick.Controls

Button {
    id: control

    property color accentColor: "#8878ff"
    property color surfaceColor: "#151a26"
    property color borderColor: "#242c3d"
    property color textColor: "#f5f7fb"
    property bool primary: false
    property bool quiet: false
    property int cornerRadius: 11

    implicitHeight: 44
    implicitWidth: 112
    leftPadding: 16
    rightPadding: 16

    contentItem: Text {
        text: control.text
        color: control.primary ? "#ffffff"
                               : (control.hovered ? control.accentColor : control.textColor)
        font.family: "Segoe UI Variable Text"
        font.pixelSize: 13
        font.weight: Font.DemiBold
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight

        Behavior on color {
            ColorAnimation { duration: 140 }
        }
    }

    background: Rectangle {
        radius: control.cornerRadius
        color: {
            if (control.primary)
                return control.down ? Qt.darker(control.accentColor, 1.18)
                                    : (control.hovered ? Qt.lighter(control.accentColor, 1.10)
                                                       : control.accentColor)
            if (control.quiet)
                return control.hovered ? Qt.rgba(control.accentColor.r,
                                                  control.accentColor.g,
                                                  control.accentColor.b, 0.10)
                                       : "transparent"
            return control.hovered ? Qt.lighter(control.surfaceColor, 1.18)
                                   : control.surfaceColor
        }
        border.width: control.primary || control.quiet ? 0 : 1
        border.color: control.hovered ? control.accentColor : control.borderColor

        Behavior on color {
            ColorAnimation { duration: 140 }
        }
        Behavior on border.color {
            ColorAnimation { duration: 140 }
        }
    }
}
