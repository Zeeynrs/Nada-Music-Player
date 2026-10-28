#!/usr/bin/env bash
# Installs Nada's dependencies (Arch) and a launcher + desktop entry for the current user.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

deps=(pyside6 librespot python-dbus cava)
missing=()
for p in "${deps[@]}"; do pacman -Q "$p" &>/dev/null || missing+=("$p"); done
if ((${#missing[@]})); then
    echo ":: Memasang: ${missing[*]}"
    sudo pacman -S --needed "${missing[@]}"
fi

mkdir -p ~/.local/bin ~/.local/share/applications ~/.local/share/icons/hicolor/scalable/apps
cat > ~/.local/bin/nada <<SH
#!/bin/sh
exec python3 -I "$DIR/run.py" "\$@"
SH
chmod +x ~/.local/bin/nada
cp "$DIR/data/nada.svg" ~/.local/share/icons/hicolor/scalable/apps/nada.svg
sed "s|@BIN@|$HOME/.local/bin/nada|" "$DIR/data/nada.desktop" > ~/.local/share/applications/nada.desktop
update-desktop-database ~/.local/share/applications &>/dev/null || true
echo ":: Selesai. Jalankan 'nada' atau buka dari launcher aplikasi."
