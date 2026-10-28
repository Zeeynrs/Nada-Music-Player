# Maintainer: Zeeynrs <https://github.com/Zeeynrs>
pkgname=nada-music-player-git
_pkgname=nada
pkgver=r5.8bf224b
pkgrel=1
pkgdesc="Pemutar Spotify ringan untuk desktop Linux (Wayland/Hyprland) dengan Qt Quick & librespot"
arch=('any')
url="https://github.com/Zeeynrs/Nada-Music-Player"
license=('GPL-3.0-only')
depends=('python' 'pyside6' 'librespot' 'python-dbus' 'cava' 'hicolor-icon-theme')
makedepends=('git')
provides=('nada-music-player')
conflicts=('nada-music-player')
source=("git+$url.git")
sha256sums=('SKIP')

pkgver() {
    cd "$srcdir/Nada-Music-Player"
    printf "r%s.%s" "$(git rev-list --count HEAD)" "$(git rev-parse --short HEAD)"
}

package() {
    cd "$srcdir/Nada-Music-Player"

    install -dm755 "$pkgdir/usr/lib/$_pkgname"
    cp -r nada qml data run.py "$pkgdir/usr/lib/$_pkgname/"

    install -dm755 "$pkgdir/usr/bin"
    cat > "$pkgdir/usr/bin/nada" << 'EOF'
#!/bin/sh
exec python3 -I /usr/lib/nada/run.py "$@"
EOF
    chmod 755 "$pkgdir/usr/bin/nada"

    install -Dm644 data/nada.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/nada.svg"
    sed "s|@BIN@|/usr/bin/nada|" data/nada.desktop > "$srcdir/nada.desktop"
    install -Dm644 "$srcdir/nada.desktop" "$pkgdir/usr/share/applications/nada.desktop"
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
