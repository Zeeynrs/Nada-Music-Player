import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Layouts

// Full-window "now playing": blurred art, big cover, synced lyrics, visualizer.
Item {
    id: im
    objectName: "immersive"
    property bool open: false
    property string panel: "lyrics"  // lyrics | queue
    readonly property var s: player.state
    readonly property bool wide: width > 1050
    property bool panelOpen: false  // narrow windows (e.g. tiled): lyrics/queue replace the cover
    readonly property bool showPanel: wide || panelOpen
    readonly property bool shown: y < height
    signal close()

    function togglePanel(name) {
        if (!wide && panelOpen && panel === name)
            panelOpen = false
        else {
            panel = name
            panelOpen = true
        }
    }

    y: open ? 0 : height
    visible: shown
    Behavior on y { NumberAnimation { duration: 460; easing.type: Easing.OutQuint } }

    // swallow input so nothing underneath reacts
    MouseArea { anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.AllButtons; onWheel: (w) => w.accepted = true }

    Rectangle { anchors.fill: parent; color: Theme.bg }

    Image {
        id: bgArt
        anchors.fill: parent
        source: im.s.image || ""
        fillMode: Image.PreserveAspectCrop
        sourceSize: Qt.size(256, 256)  // tiny on purpose: it's blurred anyway
        asynchronous: true
        visible: false
    }
    MultiEffect {
        anchors.fill: parent
        source: bgArt
        blurEnabled: true
        blur: 1.0
        blurMax: 64
        saturation: 0.25
        brightness: -0.32
        opacity: bgArt.status === Image.Ready ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 600 } }
        SequentialAnimation on scale {
            running: im.shown
            loops: Animation.Infinite
            NumberAnimation { from: 1.15; to: 1.32; duration: 24000; easing.type: Easing.InOutSine }
            NumberAnimation { from: 1.32; to: 1.15; duration: 24000; easing.type: Easing.InOutSine }
        }
    }
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Theme.alpha(Theme.bg, 0.25) }
            GradientStop { position: 0.7; color: Theme.alpha(Theme.bg, 0.45) }
            GradientStop { position: 1.0; color: Theme.alpha(Theme.bg, 0.9) }
        }
    }

    // spectrum bars along the bottom
    Row {
        id: bars
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        visible: visualizer.active
        spacing: 3
        Repeater {
            model: visualizer.count
            Rectangle {
                anchors.bottom: parent.bottom
                width: (im.width - (visualizer.count - 1) * 3) / visualizer.count
                height: 2 + (visualizer.bars[index] || 0) * im.height * 0.3
                radius: Math.min(width / 2, 4)
                color: Theme.alpha(Theme.accent, 0.28)
            }
        }
    }

    // top bar
    RowLayout {
        id: top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 20
        IconButton { iconName: "chevron-down"; size: 28; tip: "Tutup (Esc)"; onClicked: im.close() }
        Label {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: im.s.deviceName ? "Diputar di " + im.s.deviceName : ""
            color: Theme.dim
            font.pixelSize: 13
            font.weight: Font.DemiBold
            font.capitalization: Font.AllUppercase
            font.letterSpacing: 1.5
        }
        IconButton { iconName: "lyrics"; active: im.showPanel && im.panel === "lyrics"; tip: "Lirik"; onClicked: im.togglePanel("lyrics") }
        IconButton { iconName: "queue"; active: im.showPanel && im.panel === "queue"; tip: "Antrean"; onClicked: im.togglePanel("queue") }
    }

    RowLayout {
        anchors.top: top.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 48
        anchors.topMargin: 16
        anchors.bottomMargin: 56
        spacing: 64

        // now playing column
        ColumnLayout {
            visible: im.wide || !im.panelOpen
            Layout.preferredWidth: im.wide ? Math.min(520, im.width * 0.4) : -1
            Layout.fillWidth: !im.wide
            Layout.fillHeight: true
            spacing: 18

            Item { Layout.fillHeight: true }
            Cover {
                id: bigCover
                // sized from the window, not the layout, to avoid a layout feedback loop
                readonly property real side: Math.max(120, Math.min(im.wide ? Math.min(520, im.width * 0.4) : im.width - 96,
                                                                    im.height - 400, 520))
                Layout.preferredWidth: side
                Layout.preferredHeight: side
                Layout.alignment: Qt.AlignHCenter
                radius: 28
                source: im.s.imageLarge || ""
                scale: im.s.isPlaying ? 1 : 0.94
                Behavior on scale { NumberAnimation { duration: 500; easing.type: Easing.OutBack } }
                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowBlur: 1.0
                    shadowOpacity: 0.6
                    shadowVerticalOffset: 18
                }
            }
            RowLayout {
                Layout.preferredWidth: bigCover.side
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: 8
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Label {
                        Layout.fillWidth: true
                        text: im.s.name || "Tidak ada yang diputar"
                        font.pixelSize: 30
                        font.weight: Font.Black
                        elide: Text.ElideRight
                    }
                    LinkLabel {
                        Layout.fillWidth: true
                        text: im.s.artists || ""
                        font.pixelSize: 18
                        onClicked: { im.close(); Nav.go("artist", im.s.artistId) }
                    }
                }
                IconButton {
                    visible: !!im.s.hasTrack
                    iconName: im.s.liked ? "heart" : "heart-outline"
                    tint: im.s.liked ? Theme.accent : Theme.text
                    size: 26
                    onClicked: player.toggleLike()
                }
            }
            SeekBar {
                Layout.preferredWidth: bigCover.side + 100
                Layout.alignment: Qt.AlignHCenter
                fontSize: 13
            }
            TransportControls {
                Layout.alignment: Qt.AlignHCenter
                size: 28
            }
            VolumeControl {
                Layout.alignment: Qt.AlignHCenter
                sliderWidth: 160
            }
            Item { Layout.fillHeight: true }
        }

        // lyrics / queue column
        ColumnLayout {
            visible: im.showPanel
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16
            Loader {
                Layout.fillWidth: true
                Layout.fillHeight: true
                active: im.shown && im.showPanel
                sourceComponent: im.panel === "lyrics" ? lyricsComp : queueComp
            }
            // compact controls when the panel has taken the cover's place
            RowLayout {
                visible: !im.wide
                Layout.fillWidth: true
                spacing: 16
                Cover {
                    Layout.preferredWidth: 56
                    Layout.preferredHeight: 56
                    radius: 12
                    source: im.s.image || ""
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Label { Layout.fillWidth: true; text: im.s.name || ""; elide: Text.ElideRight; font.pixelSize: 16; font.weight: Font.Bold }
                    SeekBar { Layout.fillWidth: true }
                }
                TransportControls { size: 20 }
            }
        }
    }

    Component { id: lyricsComp; LyricsView {} }
    Component { id: queueComp; QueueView {} }
}
