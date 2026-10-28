import QtQuick
import QtQuick.Controls

Item {
    id: lv

    ListView {
        id: list
        anchors.fill: parent
        clip: true
        model: lyrics.lines
        spacing: 18
        currentIndex: lyrics.synced ? lyrics.current : -1
        highlightRangeMode: lyrics.synced ? ListView.ApplyRange : ListView.NoHighlightRange
        preferredHighlightBegin: height * 0.32
        preferredHighlightEnd: height * 0.32 + 80
        highlightMoveDuration: 550
        highlightMoveVelocity: -1
        boundsBehavior: Flickable.StopAtBounds
        header: Item { width: 1; height: list.height * 0.3 }
        footer: Item { width: 1; height: list.height * 0.5 }
        ScrollBar.vertical: NScrollBar {}

        delegate: Label {
            id: line
            readonly property bool isCurrent: lyrics.synced && index === lyrics.current
            readonly property bool past: lyrics.synced && index < lyrics.current
            width: list.width - 16
            text: modelData.text || "♪"
            wrapMode: Text.WordWrap
            font.pixelSize: lyrics.synced ? 30 : 22
            font.weight: Font.Bold
            color: !lyrics.synced ? Theme.alpha(Theme.text, 0.85)
                 : isCurrent ? Theme.text
                 : past ? Theme.alpha(Theme.text, 0.42) : Theme.alpha(Theme.text, 0.28)
            transformOrigin: Item.Left
            scale: isCurrent ? 1.04 : 1
            Behavior on color { ColorAnimation { duration: 300 } }
            Behavior on scale { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
            HoverHandler { cursorShape: lyrics.synced ? Qt.PointingHandCursor : Qt.ArrowCursor }
            TapHandler { onTapped: if (lyrics.synced) player.seek(modelData.t) }
        }
    }

    Column {
        anchors.centerIn: parent
        spacing: 12
        visible: lyrics.status !== "ready"
        BusyIndicator { anchors.horizontalCenter: parent.horizontalCenter; running: lyrics.status === "loading"; visible: running }
        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: ({ "loading": "Memuat lirik…", "none": "Lirik tidak ditemukan untuk lagu ini",
                     "error": "Gagal memuat lirik", "idle": "Putar lagu untuk melihat lirik" })[lyrics.status] || ""
            color: Theme.dim
            font.pixelSize: 18
        }
    }

    Label {
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        visible: lyrics.status === "ready"
        text: lyrics.synced ? "Lirik tersinkron • LRCLIB" : "Lirik • LRCLIB"
        color: Theme.faint
        font.pixelSize: 11
    }
}
