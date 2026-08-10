import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    required property var controller
    property color backgroundColor: "#0d1119"
    property color surfaceColor: "#141a26"
    property color borderColor: "#242c3d"
    property color textColor: "#f5f7fb"
    property color accentColor: "#8878ff"

    implicitHeight: 78
    color: backgroundColor
    border.width: 1
    border.color: borderColor
    radius: 18

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 18
        anchors.rightMargin: 18
        spacing: 8

        Item { Layout.fillWidth: true }

        NeoButton {
            text: "− 1 min"
            accentColor: root.accentColor
            surfaceColor: root.surfaceColor
            borderColor: root.borderColor
            textColor: root.textColor
            onClicked: root.controller.adjust(-60)
        }

        NeoButton {
            Layout.preferredWidth: 190
            implicitHeight: 48
            cornerRadius: 13
            primary: true
            text: root.controller.finished ? "↻   RECOMMENCER"
                                      : (root.controller.running
                                         ? "Ⅱ   PAUSE"
                                         : "▶   DÉMARRER")
            accentColor: root.accentColor
            surfaceColor: root.surfaceColor
            borderColor: root.borderColor
            textColor: root.textColor
            onClicked: root.controller.startPause()
        }

        NeoButton {
            text: "↻  Réinitialiser"
            accentColor: root.accentColor
            surfaceColor: root.surfaceColor
            borderColor: root.borderColor
            textColor: root.textColor
            onClicked: root.controller.reset()
        }

        NeoButton {
            text: "+ 1 min"
            accentColor: root.accentColor
            surfaceColor: root.surfaceColor
            borderColor: root.borderColor
            textColor: root.textColor
            onClicked: root.controller.adjust(60)
        }

        Item { Layout.fillWidth: true }
    }
}
