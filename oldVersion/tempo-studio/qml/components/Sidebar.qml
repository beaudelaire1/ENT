pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    required property var controller
    property color backgroundColor: "#0d1119"
    property color surfaceColor: "#141a26"
    property color borderColor: "#242c3d"
    property color textColor: "#f5f7fb"
    property color mutedColor: "#7e899e"
    property color accentColor: "#8878ff"
    property color dangerColor: "#ff4d6d"
    property bool durationError: false

    radius: 20
    color: backgroundColor
    border.width: 1
    border.color: borderColor
    implicitWidth: 304

    component FieldCaption: Text {
        color: root.mutedColor
        font.family: "Segoe UI Variable Text"
        font.pixelSize: 9
        font.weight: Font.Bold
        font.letterSpacing: 1.45
    }

    component ModernField: TextField {
        id: field
        objectName: "tempoTextEditor"
        color: root.textColor
        selectionColor: root.accentColor
        selectedTextColor: "#ffffff"
        placeholderTextColor: Qt.rgba(root.mutedColor.r, root.mutedColor.g,
                                      root.mutedColor.b, 0.76)
        font.family: "Segoe UI Variable Text"
        font.pixelSize: 13
        leftPadding: 13
        rightPadding: 13
        implicitHeight: 42

        background: Rectangle {
            radius: 10
            color: root.surfaceColor
            border.width: 1
            border.color: field.activeFocus ? root.accentColor : root.borderColor
            Behavior on border.color { ColorAnimation { duration: 130 } }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 22
        spacing: 0

        Text {
            text: "CONFIGURATION"
            color: root.accentColor
            font.family: "Segoe UI Variable Text"
            font.pixelSize: 9
            font.weight: Font.Bold
            font.letterSpacing: 1.8
        }
        Text {
            Layout.topMargin: 3
            text: "Votre session"
            color: root.textColor
            font.family: "Segoe UI Variable Display"
            font.pixelSize: 25
            font.weight: Font.DemiBold
        }

        FieldCaption {
            Layout.topMargin: 23
            text: "INTERVENTION"
        }
        ModernField {
            Layout.fillWidth: true
            Layout.topMargin: 7
            text: root.controller.sessionTitle
            placeholderText: "Nom de la session"
            onEditingFinished: root.controller.setSessionTitle(text)
        }

        FieldCaption {
            Layout.topMargin: 17
            text: "DURÉE"
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 7
            spacing: 7

            ModernField {
                id: durationField
                Layout.fillWidth: true
                text: "05:00"
                horizontalAlignment: TextInput.AlignHCenter
                font.pixelSize: 18
                font.weight: Font.DemiBold
                onAccepted: applyDuration()

                function applyDuration() {
                    if (root.controller.setDuration(text)) {
                        text = root.controller.formattedTime
                        root.durationError = false
                    } else {
                        root.durationError = true
                        errorTimer.restart()
                    }
                }

                background: Rectangle {
                    radius: 10
                    color: root.surfaceColor
                    border.width: 1
                    border.color: root.durationError ? root.dangerColor
                                                     : (durationField.activeFocus
                                                        ? root.accentColor
                                                        : root.borderColor)
                }
            }

            NeoButton {
                text: "OK"
                implicitWidth: 52
                primary: true
                accentColor: root.accentColor
                surfaceColor: root.surfaceColor
                borderColor: root.borderColor
                textColor: root.textColor
                onClicked: durationField.applyDuration()
            }
        }

        Timer {
            id: errorTimer
            interval: 800
            onTriggered: root.durationError = false
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 7
            spacing: 6

            Repeater {
                model: [1, 3, 5, 10]
                NeoButton {
                    required property int modelData
                    Layout.fillWidth: true
                    implicitWidth: 44
                    implicitHeight: 35
                    text: modelData + "m"
                    accentColor: root.accentColor
                    surfaceColor: root.surfaceColor
                    borderColor: root.borderColor
                    textColor: root.textColor
                    onClicked: {
                        root.controller.setPreset(modelData)
                        durationField.text = root.controller.formattedTime
                    }
                }
            }
        }

        FieldCaption {
            Layout.topMargin: 19
            text: "VISUALISATION"
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 7
            spacing: 6

            ButtonGroup { id: modeGroup }

            ModeButton {
                Layout.fillWidth: true
                text: "Anneau"
                iconText: "◉"
                checked: root.controller.mode === text
                ButtonGroup.group: modeGroup
                accentColor: root.accentColor
                surfaceColor: root.surfaceColor
                borderColor: root.borderColor
                textColor: root.textColor
                mutedColor: root.mutedColor
                onClicked: root.controller.setMode(text)
            }
            ModeButton {
                Layout.fillWidth: true
                text: "Sablier"
                iconText: "⌛"
                checked: root.controller.mode === text
                ButtonGroup.group: modeGroup
                accentColor: root.accentColor
                surfaceColor: root.surfaceColor
                borderColor: root.borderColor
                textColor: root.textColor
                mutedColor: root.mutedColor
                onClicked: root.controller.setMode(text)
            }
            ModeButton {
                Layout.fillWidth: true
                text: "Digital"
                iconText: "01"
                checked: root.controller.mode === text
                ButtonGroup.group: modeGroup
                accentColor: root.accentColor
                surfaceColor: root.surfaceColor
                borderColor: root.borderColor
                textColor: root.textColor
                mutedColor: root.mutedColor
                onClicked: root.controller.setMode(text)
            }
            ModeButton {
                Layout.fillWidth: true
                text: "Zen"
                iconText: "◎"
                checked: root.controller.mode === text
                ButtonGroup.group: modeGroup
                accentColor: root.accentColor
                surfaceColor: root.surfaceColor
                borderColor: root.borderColor
                textColor: root.textColor
                mutedColor: root.mutedColor
                onClicked: root.controller.setMode(text)
            }
        }

        FieldCaption {
            Layout.topMargin: 19
            text: "AMBIANCE"
        }
        ComboBox {
            id: ambienceCombo
            Layout.fillWidth: true
            Layout.topMargin: 7
            implicitHeight: 42
            model: ["Concentration", "Calme", "Énergie", "Nocturne"]
            currentIndex: model.indexOf(root.controller.ambience)
            onActivated: root.controller.setAmbience(currentText)

            contentItem: Text {
                leftPadding: 13
                text: ambienceCombo.displayText
                color: root.textColor
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 13
                verticalAlignment: Text.AlignVCenter
            }
            indicator: Text {
                x: ambienceCombo.width - width - 13
                anchors.verticalCenter: parent.verticalCenter
                text: "⌄"
                color: root.mutedColor
                font.pixelSize: 17
            }
            background: Rectangle {
                radius: 10
                color: root.surfaceColor
                border.width: 1
                border.color: ambienceCombo.activeFocus
                              ? root.accentColor : root.borderColor
            }
            popup: Popup {
                y: ambienceCombo.height + 5
                width: ambienceCombo.width
                implicitHeight: contentItem.implicitHeight + 10
                padding: 5

                contentItem: ListView {
                    clip: true
                    implicitHeight: contentHeight
                    model: ambienceCombo.popup.visible
                           ? ambienceCombo.delegateModel : null
                    currentIndex: ambienceCombo.highlightedIndex
                }
                background: Rectangle {
                    radius: 10
                    color: root.surfaceColor
                    border.width: 1
                    border.color: root.borderColor
                }
            }
            delegate: ItemDelegate {
                id: ambienceDelegate
                required property int index
                required property string modelData
                width: ambienceCombo.width - 10
                height: 36
                highlighted: ambienceCombo.highlightedIndex === index
                contentItem: Text {
                    text: ambienceDelegate.modelData
                    color: ambienceDelegate.highlighted
                           ? root.accentColor : root.textColor
                    font.family: "Segoe UI Variable Text"
                    font.pixelSize: 12
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 7
                    color: ambienceDelegate.highlighted
                           ? Qt.rgba(root.accentColor.r, root.accentColor.g,
                                     root.accentColor.b, 0.12)
                           : "transparent"
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 8
            spacing: 7

            NeoButton {
                Layout.fillWidth: true
                text: root.controller.soundEnabled
                      ? "◉  Son ambiant" : "○  Son ambiant"
                accentColor: root.accentColor
                surfaceColor: root.surfaceColor
                borderColor: root.borderColor
                textColor: root.textColor
                onClicked: root.controller.toggleSound()
            }

            Row {
                spacing: 4
                Repeater {
                    model: 3
                    Rectangle {
                        id: focusChip
                        required property int index
                        width: 25
                        height: 36
                        radius: 8
                        color: root.controller.focusLevel === focusChip.index + 1
                               ? Qt.rgba(root.accentColor.r, root.accentColor.g,
                                         root.accentColor.b, 0.15)
                               : root.surfaceColor
                        border.width: 1
                        border.color: root.controller.focusLevel === focusChip.index + 1
                                      ? root.accentColor : root.borderColor

                        Text {
                            anchors.centerIn: parent
                            text: focusChip.index + 1
                            color: root.controller.focusLevel === focusChip.index + 1
                                   ? root.accentColor : root.mutedColor
                            font.pixelSize: 10
                            font.weight: Font.Bold
                        }
                        TapHandler {
                            onTapped: root.controller.setFocusLevel(focusChip.index + 1)
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 16

            FieldCaption { text: "ALERTE FINALE" }
            Item { Layout.fillWidth: true }
            Text {
                text: root.controller.warningSeconds + " s"
                color: root.accentColor
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 10
                font.weight: Font.Bold
            }
        }

        Slider {
            id: warningSlider
            Layout.fillWidth: true
            Layout.topMargin: 2
            from: 10
            to: 180
            stepSize: 5
            value: root.controller.warningSeconds
            onMoved: root.controller.setWarningSeconds(Math.round(value))

            background: Rectangle {
                x: warningSlider.leftPadding
                y: warningSlider.topPadding + warningSlider.availableHeight / 2 - 2
                width: warningSlider.availableWidth
                height: 4
                radius: 2
                color: root.borderColor

                Rectangle {
                    width: warningSlider.visualPosition * parent.width
                    height: parent.height
                    radius: 2
                    color: root.accentColor
                }
            }
            handle: Rectangle {
                x: warningSlider.leftPadding
                   + warningSlider.visualPosition
                   * (warningSlider.availableWidth - width)
                y: warningSlider.topPadding
                   + warningSlider.availableHeight / 2 - height / 2
                width: 16
                height: 16
                radius: 8
                color: root.textColor
                border.width: 3
                border.color: root.accentColor
            }
        }

        Item { Layout.fillHeight: true }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 53
            radius: 11
            color: root.surfaceColor
            border.width: 1
            border.color: root.borderColor

            Text {
                anchors.centerIn: parent
                text: "ESPACE  ·  lecture / pause\nR  ·  reprise     F11  ·  mode scène"
                color: root.mutedColor
                horizontalAlignment: Text.AlignHCenter
                lineHeight: 1.35
                font.family: "Segoe UI Variable Text"
                font.pixelSize: 9
            }
        }
    }
}
