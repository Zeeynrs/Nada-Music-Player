import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: side
    property string currentKey

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        anchors.topMargin: 16
        spacing: 4

        Row {
            Layout.leftMargin: 10
            Layout.bottomMargin: 14
            spacing: 10
            Image {
                source: Qt.resolvedUrl("../data/nada.svg")
                width: 32; height: 32
                sourceSize: Qt.size(64, 64)
            }
            Label {
                text: "nada"
                font.pixelSize: 24
                font.weight: Font.Black
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        NavItem { Layout.fillWidth: true; text: "Beranda"; iconName: "home"; active: side.currentKey === "home"; onClicked: Nav.go("home") }
        NavItem { Layout.fillWidth: true; text: "Cari"; iconName: "search"; active: side.currentKey === "search"; onClicked: Nav.go("search") }
        NavItem { Layout.fillWidth: true; text: "Lagu Disukai"; iconName: "heart"; active: side.currentKey === "liked:"; onClicked: Nav.go("liked") }

        Label {
            text: "Playlist"
            color: Theme.faint
            font.pixelSize: 12
            font.weight: Font.Bold
            font.capitalization: Font.AllUppercase
            font.letterSpacing: 1.2
            Layout.leftMargin: 14
            Layout.topMargin: 18
            Layout.bottomMargin: 4
        }

        ListView {
            id: pl
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: library.playlists
            spacing: 2
            ScrollBar.vertical: NScrollBar {}
            delegate: AbstractButton {
                id: d
                width: pl.width
                height: 56
                hoverEnabled: true
                focusPolicy: Qt.NoFocus
                readonly property bool active: side.currentKey === "playlist:" + modelData.id
                readonly property bool playingHere: player.state.contextUri === modelData.uri
                onClicked: Nav.go("playlist", modelData.id)
                background: Rectangle {
                    radius: 12
                    color: d.active ? Theme.alpha(Theme.accent, 0.14) : d.hovered ? Theme.alpha(Theme.text, 0.06) : "transparent"
                }
                contentItem: RowLayout {
                    spacing: 12
                    Cover {
                        Layout.leftMargin: 6
                        Layout.preferredWidth: 42
                        Layout.preferredHeight: 42
                        radius: 8
                        source: modelData.imageSmall
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Label {
                            Layout.fillWidth: true
                            text: modelData.name
                            elide: Text.ElideRight
                            font.pixelSize: 14
                            font.weight: Font.Medium
                            color: d.playingHere ? Theme.accent : Theme.text
                        }
                        Label {
                            Layout.fillWidth: true
                            text: modelData.subtitle
                            elide: Text.ElideRight
                            font.pixelSize: 12
                            color: Theme.dim
                        }
                    }
                    Icon {
                        visible: d.playingHere && player.state.isPlaying
                        glyph: "volume"
                        size: 16
                        color: Theme.accent
                        Layout.rightMargin: 8
                    }
                }
            }
        }

        AbstractButton {
            id: updateCard
            visible: updater.updateAvailable
            Layout.fillWidth: true
            Layout.topMargin: 4
            implicitHeight: 54
            hoverEnabled: true
            focusPolicy: Qt.NoFocus
            enabled: !updater.updating
            onClicked: updater.applyUpdate()

            background: Rectangle {
                radius: 14
                color: updateCard.hovered ? Theme.alpha(Theme.accent, 0.22) : Theme.alpha(Theme.accent, 0.14)
                border.width: 1
                border.color: Theme.alpha(Theme.accent, 0.35)
                Behavior on color { ColorAnimation { duration: 140 } }
            }

            contentItem: RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 10

                Icon {
                    glyph: "download"
                    size: 18
                    color: Theme.accent
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 1
                    Label {
                        Layout.fillWidth: true
                        text: updater.updating ? "Memperbarui Nada…" : "Update tersedia (" + updater.commitsBehind + ")"
                        font.pixelSize: 13
                        font.weight: Font.Bold
                        color: Theme.accent
                        elide: Text.ElideRight
                    }
                    Label {
                        Layout.fillWidth: true
                        text: updater.remoteMessage
                        font.pixelSize: 11
                        color: Theme.dim
                        elide: Text.ElideRight
                    }
                }
            }
        }

        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.alpha(Theme.text, 0.06); Layout.topMargin: 4 }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 4
            spacing: 8
            Cover {
                Layout.leftMargin: 8
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                round: true
                source: library.me.image || ""
                fallbackIcon: "speaker"
            }
            Label {
                Layout.fillWidth: true
                text: library.me.name || "…"
                elide: Text.ElideRight
                font.pixelSize: 14
                font.weight: Font.Medium
            }
            IconButton {
                iconName: updater.updateAvailable ? "download" : "refresh"
                tint: updater.updateAvailable ? Theme.accent : Theme.dim
                enabled: !updater.checking && !updater.updating
                tip: updater.updateAvailable
                     ? "Perbarui ke commit terbaru (" + updater.remoteHash + ")"
                     : "Periksa pembaruan GitHub (" + updater.currentHash + ")"
                onClicked: updater.updateAvailable ? updater.applyUpdate() : updater.check(false)
            }
            IconButton {
                iconName: "settings"
                tip: "Pengaturan (Ctrl+,)"
                active: side.currentKey === "settings"
                onClicked: Nav.go("settings")
            }
        }
    }
}
