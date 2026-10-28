import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: p
    width: 340
    padding: 14
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    onOpened: player.refreshDevices()

    function deviceIcon(type) {
        if (type === "smartphone") return "smartphone"
        if (type === "computer") return "computer"
        return "speaker"
    }

    background: Rectangle {
        color: Theme.surface3
        radius: 20
        border.color: Theme.alpha(Theme.text, 0.07)
    }

    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 140 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 120 } }

    contentItem: ColumnLayout {
        spacing: 6
        RowLayout {
            Layout.fillWidth: true
            Label {
                Layout.fillWidth: true
                text: "Putar di perangkat"
                font.pixelSize: 17
                font.weight: Font.Bold
            }
            IconButton { iconName: "refresh"; size: 18; tip: "Muat ulang"; onClicked: player.refreshDevices() }
        }

        Repeater {
            model: player.devices
            AbstractButton {
                id: d
                Layout.fillWidth: true
                implicitHeight: 54
                hoverEnabled: true
                focusPolicy: Qt.NoFocus
                enabled: !modelData.restricted
                onClicked: { player.transfer(modelData.id); p.close() }
                background: Rectangle {
                    radius: 12
                    color: modelData.active ? Theme.alpha(Theme.accent, 0.14) : d.hovered ? Theme.alpha(Theme.text, 0.07) : "transparent"
                }
                contentItem: RowLayout {
                    spacing: 12
                    Icon {
                        Layout.leftMargin: 10
                        glyph: p.deviceIcon(modelData.type)
                        size: 24
                        color: modelData.active ? Theme.accent : Theme.dim
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Label {
                            Layout.fillWidth: true
                            text: modelData.name
                            elide: Text.ElideRight
                            font.pixelSize: 15
                            font.weight: Font.Medium
                            color: modelData.active ? Theme.accent : Theme.text
                        }
                        Label {
                            text: modelData.active ? "Sedang diputar" : modelData.local ? "Komputer ini" : modelData.type
                            font.pixelSize: 12
                            color: Theme.dim
                        }
                    }
                }
            }
        }

        Label {
            visible: player.devices.length === 0
            Layout.fillWidth: true
            Layout.margins: 8
            wrapMode: Text.WordWrap
            color: Theme.dim
            font.pixelSize: 13
            text: "Belum ada perangkat. Tunggu perangkat lokal siap, atau buka Spotify di HP."
        }

        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.alpha(Theme.text, 0.08); Layout.topMargin: 4 }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 4
            spacing: 8
            Rectangle {
                implicitWidth: 8; implicitHeight: 8; radius: 4
                color: librespot.status === "ready" ? "#7ee08f" : librespot.status === "error" || librespot.status === "missing" ? Theme.danger : "#ffd36e"
            }
            Label {
                Layout.fillWidth: true
                text: "Perangkat lokal “" + session.deviceName + "”: " + Theme.librespotStatus(librespot.status)
                font.pixelSize: 12
                color: Theme.dim
                elide: Text.ElideRight
            }
        }
    }
}
