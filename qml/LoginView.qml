import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0; color: "#1a2233" }
            GradientStop { position: 1; color: Theme.bg }
        }
    }

    Flickable {
        anchors.fill: parent
        contentHeight: Math.max(height, card.height + 80)
        boundsBehavior: Flickable.StopAtBounds

        Rectangle {
            id: card
            anchors.centerIn: parent
            width: Math.min(560, parent.width - 48)
            height: col.implicitHeight + 64
            radius: 28
            color: Theme.surface
            border.color: Theme.alpha(Theme.text, 0.06)

            ColumnLayout {
                id: col
                anchors.fill: parent
                anchors.margins: 32
                spacing: 14

                Image {
                    source: Qt.resolvedUrl("../data/nada.svg")
                    Layout.preferredWidth: 64
                    Layout.preferredHeight: 64
                    sourceSize: Qt.size(128, 128)
                }
                Label { text: "Selamat datang di Nada"; font.pixelSize: 30; font.weight: Font.Black }
                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    color: Theme.dim
                    font.pixelSize: 14
                    text: "Pemutar Spotify ringan untuk desktop. Butuh <b>Spotify Premium</b> dan Client ID dari aplikasi developer milikmu sendiri (gratis, sekali saja):"
                    textFormat: Text.StyledText
                }

                Repeater {
                    model: [
                        "Buka Spotify Developer Dashboard lalu klik <b>Create app</b>.",
                        "Isi Redirect URI dengan alamat di bawah, centang <b>Web API</b>, lalu simpan.",
                        "Di tab <b>User Management</b>, tambahkan email akun Spotify-mu.",
                        "Salin <b>Client ID</b> dan tempel di bawah. Client secret tidak diperlukan."
                    ]
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Rectangle {
                            Layout.alignment: Qt.AlignTop
                            implicitWidth: 26; implicitHeight: 26; radius: 13
                            color: Theme.alpha(Theme.accent, 0.18)
                            Label { anchors.centerIn: parent; text: index + 1; color: Theme.accent; font.weight: Font.Bold }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: modelData
                            textFormat: Text.StyledText
                            wrapMode: Text.WordWrap
                            font.pixelSize: 14
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    NButton { text: "Buka Dashboard"; onClicked: session.openUrl("https://developer.spotify.com/dashboard") }
                    Item { Layout.fillWidth: true }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 48
                    radius: 14
                    color: Theme.bg
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 16
                        anchors.rightMargin: 6
                        Label {
                            Layout.fillWidth: true
                            text: session.redirectUri
                            font.family: Theme.mono
                            font.pixelSize: 13
                            color: Theme.accent
                        }
                        NButton { text: "Salin"; onClicked: session.copy(session.redirectUri) }
                    }
                }

                NTextField {
                    id: clientField
                    Layout.fillWidth: true
                    Layout.topMargin: 6
                    placeholderText: "Client ID (32 karakter)"
                    text: session.clientId
                    font.family: Theme.mono
                    onAccepted: session.login(text)
                }

                NButton {
                    Layout.fillWidth: true
                    primary: true
                    enabled: !session.busy
                    text: session.busy ? "Menunggu browser…" : "Masuk dengan Spotify"
                    onClicked: session.login(clientField.text)
                }

                Label {
                    Layout.fillWidth: true
                    visible: session.message !== ""
                    text: session.message
                    wrapMode: Text.WordWrap
                    color: session.busy ? Theme.dim : Theme.danger
                    font.pixelSize: 13
                }
            }
        }
    }
}
