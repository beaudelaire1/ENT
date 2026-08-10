import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: window

    width: 1360
    height: 840
    minimumWidth: 1080
    minimumHeight: 700
    visible: true
    title: "Tempo Studio — Chronomètre d’orateur"
    color: palette.appBackground

    property bool stageMode: false
    readonly property var controller: timerController

    function enterStageMode() {
        stageMode = true
        showFullScreen()
    }

    function leaveStageMode() {
        if (!stageMode)
            return
        stageMode = false
        showNormal()
    }

    QtObject {
        id: palette

        readonly property color appBackground: {
            switch (window.controller.ambience) {
            case "Calme": return "#061318"
            case "Énergie": return "#100B08"
            case "Nocturne": return "#05070C"
            default: return "#07090E"
            }
        }
        readonly property color panel: {
            switch (window.controller.ambience) {
            case "Calme": return "#0A1B21"
            case "Énergie": return "#18110C"
            case "Nocturne": return "#0A0D14"
            default: return "#0D1119"
            }
        }
        readonly property color surface: {
            switch (window.controller.ambience) {
            case "Calme": return "#10262D"
            case "Énergie": return "#241810"
            case "Nocturne": return "#111722"
            default: return "#151B28"
            }
        }
        readonly property color stage: {
            switch (window.controller.ambience) {
            case "Calme": return "#07171D"
            case "Énergie": return "#120D09"
            case "Nocturne": return "#070A10"
            default: return "#090D14"
            }
        }
        readonly property color border: {
            switch (window.controller.ambience) {
            case "Calme": return "#193A43"
            case "Énergie": return "#3A291D"
            case "Nocturne": return "#20283A"
            default: return "#242D40"
            }
        }
        readonly property color text: "#F3F6FC"
        readonly property color muted: {
            switch (window.controller.ambience) {
            case "Calme": return "#7FA4AD"
            case "Énergie": return "#A08D7E"
            default: return "#7E899E"
            }
        }
        readonly property color accent: {
            switch (window.controller.ambience) {
            case "Calme": return "#37D6B0"
            case "Énergie": return "#FF9D45"
            case "Nocturne": return "#4FC3FF"
            default: return "#8878FF"
            }
        }
        readonly property color warning: "#FFB84D"
        readonly property color danger: "#FF4D6D"
    }

    background: Rectangle {
        color: palette.appBackground

        Rectangle {
            width: parent.width * 0.55
            height: width
            radius: width / 2
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.rightMargin: -width * 0.28
            anchors.topMargin: -height * 0.55
            color: Qt.rgba(palette.accent.r, palette.accent.g,
                           palette.accent.b, 0.035)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: window.stageMode ? 0 : 20
        spacing: window.stageMode ? 0 : 14

        Item {
            id: header
            Layout.fillWidth: true
            Layout.preferredHeight: window.stageMode ? 0 : 58
            visible: !window.stageMode

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 4
                anchors.rightMargin: 2
                spacing: 12

                Image {
                    source: "../assets/tempo_mark.svg"
                    sourceSize.width: 36
                    sourceSize.height: 36
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    fillMode: Image.PreserveAspectFit
                }

                Column {
                    spacing: -2
                    Text {
                        text: "TEMPO"
                        color: palette.text
                        font.family: "Segoe UI Variable Display"
                        font.pixelSize: 20
                        font.weight: Font.Bold
                        font.letterSpacing: 3.5
                    }
                    Text {
                        text: "SPEAKER  /  STUDIO"
                        color: palette.muted
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: 8
                        font.weight: Font.Bold
                        font.letterSpacing: 2.2
                    }
                }

                Rectangle {
                    Layout.leftMargin: 16
                    Layout.preferredWidth: 1
                    Layout.preferredHeight: 26
                    color: palette.border
                }

                Text {
                    text: "Un rythme clair. Une présence calme."
                    color: palette.muted
                    font.family: "Segoe UI Variable Text"
                    font.pixelSize: 11
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    Layout.preferredWidth: statusHeader.implicitWidth + 28
                    Layout.preferredHeight: 30
                    radius: 15
                    color: Qt.rgba(palette.accent.r, palette.accent.g,
                                   palette.accent.b, 0.10)
                    border.width: 1
                    border.color: Qt.rgba(palette.accent.r, palette.accent.g,
                                          palette.accent.b, 0.40)

                    Text {
                        id: statusHeader
                        anchors.centerIn: parent
                        text: window.controller.running ? "●  EN DIRECT" : "●  PRÊT"
                        color: palette.accent
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: 9
                        font.weight: Font.Bold
                        font.letterSpacing: 0.8
                    }
                }

                NeoButton {
                    text: "Mode scène  ⛶"
                    accentColor: palette.accent
                    surfaceColor: palette.surface
                    borderColor: palette.border
                    textColor: palette.text
                    onClicked: window.enterStageMode()
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: window.stageMode ? 0 : 14

            Sidebar {
                Layout.preferredWidth: window.stageMode ? 0 : 304
                Layout.fillHeight: true
                visible: !window.stageMode
                controller: window.controller
                backgroundColor: palette.panel
                surfaceColor: palette.surface
                borderColor: palette.border
                textColor: palette.text
                mutedColor: palette.muted
                accentColor: palette.accent
                dangerColor: palette.danger
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: window.stageMode ? 0 : 12

                TimerStage {
                    id: stage
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    controller: window.controller
                    backgroundColor: palette.stage
                    surfaceColor: palette.surface
                    borderColor: palette.border
                    textColor: palette.text
                    mutedColor: palette.muted
                    accentColor: palette.accent
                    warningColor: palette.warning
                    dangerColor: palette.danger
                }

                ControlBar {
                    Layout.fillWidth: true
                    Layout.preferredHeight: window.stageMode ? 0 : 78
                    visible: !window.stageMode
                    controller: window.controller
                    backgroundColor: palette.panel
                    surfaceColor: palette.surface
                    borderColor: palette.border
                    textColor: palette.text
                    accentColor: window.controller.finished ? palette.danger
                                                         : (window.controller.warning
                                                            ? palette.warning
                                                            : palette.accent)
                }
            }
        }
    }

    Shortcut {
        sequence: "Space"
        enabled: !window.activeFocusItem
                 || window.activeFocusItem.objectName !== "tempoTextEditor"
        onActivated: window.controller.startPause()
    }
    Shortcut {
        sequence: "R"
        enabled: !window.activeFocusItem
                 || window.activeFocusItem.objectName !== "tempoTextEditor"
        onActivated: window.controller.reset()
    }
    Shortcut {
        sequence: "F11"
        onActivated: window.stageMode ? window.leaveStageMode()
                                      : window.enterStageMode()
    }
    Shortcut {
        sequence: "Escape"
        enabled: window.stageMode
        onActivated: window.leaveStageMode()
    }
}
