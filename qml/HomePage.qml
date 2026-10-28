import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: page
    readonly property string pageKey: "home"
    readonly property var home: library.home

    Flickable {
        id: flick
        anchors.fill: parent
        contentHeight: col.implicitHeight + 48
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: NScrollBar {}

        Column {
            id: col
            x: 20
            y: 52
            width: flick.width - 40
            spacing: 28

            RowLayout {
                width: parent.width
                Label {
                    Layout.fillWidth: true
                    Layout.leftMargin: 12
                    text: Theme.greeting() + (library.me.name ? ", " + library.me.name.split(" ")[0] : "")
                    font.pixelSize: 36
                    font.weight: Font.Black
                    elide: Text.ElideRight
                }
                IconButton { iconName: "refresh"; tip: "Muat ulang"; onClicked: library.refreshAll() }
            }

            // quick tiles: the first playlists, Spotify-home style
            GridLayout {
                width: parent.width
                columns: width > 900 ? 4 : 2
                columnSpacing: 10
                rowSpacing: 10
                visible: library.playlists.length > 0
                Repeater {
                    model: [{ kind: "liked", id: "", name: "Lagu yang Disukai", imageSmall: "" }].concat(library.playlists.slice(0, 7))
                    AbstractButton {
                        id: tile
                        Layout.fillWidth: true
                        implicitHeight: 64
                        hoverEnabled: true
                        focusPolicy: Qt.NoFocus
                        onClicked: Nav.go(modelData.kind, modelData.id)
                        background: Rectangle {
                            radius: 14
                            color: tile.hovered ? Theme.alpha(Theme.text, 0.12) : Theme.alpha(Theme.text, 0.06)
                            Behavior on color { ColorAnimation { duration: 140 } }
                        }
                        contentItem: RowLayout {
                            spacing: 12
                            Cover {
                                Layout.preferredWidth: 64
                                Layout.preferredHeight: 64
                                radius: 14
                                source: modelData.imageSmall
                                fallbackIcon: modelData.kind === "liked" ? "heart" : "note"
                            }
                            Label {
                                Layout.fillWidth: true
                                text: modelData.name
                                elide: Text.ElideRight
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                            }
                        }
                    }
                }
            }

            CardGrid { width: parent.width; title: "Baru saja diputar"; items: page.home.recent || []; rows: 1 }

            Column {
                width: parent.width
                visible: (page.home.topTracks || []).length > 0
                spacing: 4
                Label {
                    text: "Lagu favoritmu akhir-akhir ini"
                    font.pixelSize: 22
                    font.weight: Font.Bold
                    leftPadding: 12
                    bottomPadding: 6
                }
                Repeater {
                    model: (page.home.topTracks || []).slice(0, 5)
                    TrackRow {
                        width: col.width
                        track: modelData
                        number: index + 1
                        onPlay: player.playUris(page.home.topTracks.map(x => x.uri), index)
                    }
                }
            }

            CardGrid { width: parent.width; title: "Artis favoritmu"; items: page.home.topArtists || []; rows: 1 }
            CardGrid { width: parent.width; title: "Playlist kamu"; items: library.playlists; rows: 2 }
        }
    }
}
