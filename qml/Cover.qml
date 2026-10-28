import QtQuick
import QtQuick.Effects
import QtQuick.Window

// Album/artist art with rounded corners and a placeholder while loading.
Item {
    id: root
    property url source
    property real radius: 8
    property bool round: false
    property bool simple: false  // plain square image, cheaper for long lists
    property string fallbackIcon: "note"
    readonly property bool ready: img.status === Image.Ready
    readonly property real cornerRadius: round ? width / 2 : radius
    readonly property int loadSize: Math.ceil(Math.max(width, height) * Screen.devicePixelRatio)

    Rectangle {
        anchors.fill: parent
        radius: root.cornerRadius
        color: Theme.surface3
        visible: !root.ready
        Icon {
            anchors.centerIn: parent
            glyph: root.fallbackIcon
            size: Math.max(14, Math.min(root.width * 0.38, 64))
            color: Theme.faint
        }
    }

    Image {
        id: img
        anchors.fill: parent
        source: root.source
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        sourceSize.width: root.loadSize
        sourceSize.height: root.loadSize
        visible: root.simple && root.ready
        smooth: true
    }

    Loader {
        anchors.fill: parent
        active: !root.simple && root.ready
        sourceComponent: MultiEffect {
            source: img
            maskEnabled: true
            maskSource: mask
            maskThresholdMin: 0.5
            maskSpreadAtMin: 1.0
            NumberAnimation on opacity { from: 0; to: 1; duration: 220 }
        }
    }

    Item {
        id: mask
        anchors.fill: parent
        layer.enabled: true
        layer.smooth: true
        visible: false
        Rectangle {
            anchors.fill: parent
            radius: root.cornerRadius
        }
    }
}
