#!/usr/bin/env bash
# Installer multi-distro untuk Nada Music Player (Direkomendasikan: Arch Linux)
# Dapat dijalankan langsung (./install.sh) atau via curl:
#   curl -fsSL https://raw.githubusercontent.com/Zeeynrs/Nada-Music-Player/main/install.sh | bash
set -euo pipefail

REPO_URL="https://github.com/Zeeynrs/Nada-Music-Player.git"
DEFAULT_INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/nada"
BIN_DIR="$HOME/.local/bin"
APP_DIR_DESKTOP="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

export PATH="$BIN_DIR:$HOME/.cargo/bin:$PATH"

# Warna output
if [ -t 1 ]; then
    BOLD="\033[1m"
    GREEN="\033[1;32m"
    CYAN="\033[1;36m"
    YELLOW="\033[1;33m"
    RED="\033[1;31m"
    RESET="\033[0m"
else
    BOLD="" GREEN="" CYAN="" YELLOW="" RED="" RESET=""
fi

info() { echo -e "${CYAN}::${RESET} ${BOLD}$*${RESET}"; }
ok()   { echo -e "${GREEN}✓${RESET} $*"; }
warn() { echo -e "${YELLOW}!${RESET} $*"; }
err()  { echo -e "${RED}✗${RESET} $*" >&2; }

usage() {
    cat <<EOF
Penggunaan: ./install.sh [OPSI]

Opsi:
  (tanpa opsi)   Pasang dependensi, launcher ~/.local/bin/nada, dan entri aplikasi
  --no-deps      Lewati pemasangan paket sistem (hanya buat launcher & desktop entry)
  --uninstall    Hapus launcher, ikon, dan entri menu Nada dari sistem
  -h, --help     Tampilkan bantuan ini
EOF
}

uninstall_nada() {
    info "Menghapus instalasi Nada..."
    rm -f "$BIN_DIR/nada"
    rm -f "$APP_DIR_DESKTOP/nada.desktop"
    rm -f "$ICON_DIR/nada.svg"
    if [ -d "$DEFAULT_INSTALL_DIR" ]; then
        rm -rf "$DEFAULT_INSTALL_DIR"
        ok "Direktori aplikasi $DEFAULT_INSTALL_DIR dihapus."
    fi
    update-desktop-database "$APP_DIR_DESKTOP" &>/dev/null || true
    ok "Nada berhasil dihapus. (Konfigurasi di ~/.config/nada & cache di ~/.cache/nada tetap disimpan)."
    exit 0
}

SKIP_DEPS=0
for arg in "$@"; do
    case "$arg" in
        --uninstall|uninstall|remove)
            uninstall_nada
            ;;
        --no-deps)
            SKIP_DEPS=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            err "Opsi tidak dikenal: $arg"
            usage
            exit 1
            ;;
    esac
done

# Deteksi distro Linux
DISTRO_ID="unknown"
DISTRO_LIKE=""
DISTRO_NAME="Linux"
if [ -f /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    DISTRO_ID="${ID:-unknown}"
    DISTRO_LIKE="${ID_LIKE:-}"
    DISTRO_NAME="${PRETTY_NAME:-${NAME:-Linux}}"
fi

is_arch() {
    [[ "$DISTRO_ID" == "arch" || "$DISTRO_ID" == "manjaro" || "$DISTRO_ID" == "endeavouros" || \
       "$DISTRO_ID" == "cachyos" || "$DISTRO_ID" == "garuda" || "$DISTRO_ID" == "artix" || \
       "$DISTRO_LIKE" == *"arch"* ]] || command -v pacman &>/dev/null
}

apt_has_pkg() {
    apt-cache show "$1" &>/dev/null
}

install_git_if_missing() {
    command -v git &>/dev/null && return 0
    info "Memasang git terlebih dahulu..."
    if command -v pacman &>/dev/null; then
        sudo pacman -S --needed git
    elif command -v apt-get &>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y git
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y git
    elif command -v zypper &>/dev/null; then
        sudo zypper install -y git
    elif command -v xbps-install &>/dev/null; then
        sudo xbps-install -Sy git
    elif command -v apk &>/dev/null; then
        sudo apk add git
    else
        err "git belum terpasang dan manajer paket tidak dikenali. Silakan pasang 'git' secara manual."
        exit 1
    fi
}

# Tentukan lokasi sumber kode Nada (lokal vs one-liner curl | bash)
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/run.py" ] && [ -d "$SCRIPT_DIR/nada" ]; then
    DIR="$SCRIPT_DIR"
else
    install_git_if_missing
    DIR="$DEFAULT_INSTALL_DIR"
    if [ -d "$DIR/.git" ]; then
        info "Memperbarui repositori Nada di $DIR..."
        git -C "$DIR" fetch origin main --quiet || true
        git -C "$DIR" reset --hard origin/main --quiet || true
    else
        info "Mengunduh Nada ke $DIR..."
        mkdir -p "$(dirname "$DIR")"
        rm -rf "$DIR"
        git clone "$REPO_URL" "$DIR"
    fi
fi

# Banner & rekomendasi distro
echo -e "${BOLD}============================================================${RESET}"
echo -e "${BOLD}  Nada Music Player — Pemutar Spotify Ringan untuk Linux${RESET}"
echo -e "${BOLD}============================================================${RESET}"
if is_arch; then
    ok "Distro terdeteksi: ${BOLD}${DISTRO_NAME}${RESET} ${GREEN}(Distro Utama & Direkomendasikan)${RESET}"
else
    info "Distro terdeteksi: ${BOLD}${DISTRO_NAME}${RESET}"
    warn "Catatan: ${BOLD}Arch Linux${RESET} adalah distro yang paling direkomendasikan untuk Nada"
    echo "  (semua paket tersedia native di repositori resmi), namun mode kompatibilitas"
    echo "  multi-distro akan menyiapkan kebutuhan untuk sistem Anda secara otomatis."
fi
echo ""

install_system_deps() {
    if is_arch; then
        local deps=(pyside6 librespot python-dbus cava)
        local missing=()
        for p in "${deps[@]}"; do
            pacman -Q "$p" &>/dev/null || missing+=("$p")
        done
        if ((${#missing[@]})); then
            info "Memasang dependensi Arch Linux: ${missing[*]}"
            sudo pacman -S --needed "${missing[@]}"
        else
            ok "Semua dependensi paket Arch Linux sudah terpasang."
        fi

    elif command -v apt-get &>/dev/null; then
        info "Memeriksa paket untuk Debian/Ubuntu (apt)..."
        sudo apt-get update -qq
        local apt_pkgs=(python3 python3-venv python3-pip python3-dbus)
        for opt_pkg in cava libxcb-cursor0 librespot \
            python3-pyside6.qtcore python3-pyside6.qtgui python3-pyside6.qtqml \
            python3-pyside6.qtquick python3-pyside6.qtquickcontrols2 \
            qml6-module-qtquick qml6-module-qtquick-controls \
            qml6-module-qtquick-layouts qml6-module-qtquick-window; do
            if apt_has_pkg "$opt_pkg"; then
                apt_pkgs+=("$opt_pkg")
            fi
        done
        info "Memasang paket apt: ${apt_pkgs[*]}"
        sudo apt-get install -y "${apt_pkgs[@]}"

    elif command -v dnf &>/dev/null; then
        info "Memasang paket untuk Fedora/RHEL (dnf)..."
        local dnf_pkgs=(python3 python3-dbus cava)
        sudo dnf install -y "${dnf_pkgs[@]}" || true
        sudo dnf install -y python3-pyside6 || true
        sudo dnf install -y librespot || true

    elif command -v zypper &>/dev/null; then
        info "Memasang paket untuk openSUSE (zypper)..."
        sudo zypper install -y python3 python3-dbus-python cava || true
        sudo zypper install -y python3-pyside6 || true
        sudo zypper install -y librespot || true

    elif command -v xbps-install &>/dev/null; then
        info "Memasang paket untuk Void Linux (xbps)..."
        sudo xbps-install -Sy python3 python3-PySide6 python3-dbus cava librespot

    elif command -v apk &>/dev/null; then
        info "Memasang paket untuk Alpine Linux (apk)..."
        sudo apk add python3 py3-pyside6 py3-dbus cava librespot || true

    elif command -v nix-env &>/dev/null; then
        warn "Nix terdeteksi. Pastikan python3, pyside6, librespot, python-dbus, dan cava tersedia di environment Anda."
    else
        warn "Manajer paket tidak dikenali. Melanjutkan dengan pengecekan Python & venv..."
    fi
}

if (( ! SKIP_DEPS )); then
    install_system_deps
fi

# Cek apakah PySide6 + QtQuickControls2 tersedia di Python sistem; jika tidak, buat .venv otomatis
PYTHON_CMD="python3 -I"
if python3 -I -c "import PySide6.QtCore, PySide6.QtGui, PySide6.QtQml, PySide6.QtQuickControls2" &>/dev/null; then
    ok "PySide6 (Qt6 QML) sistem siap digunakan."
    if [ -d "$DIR/.venv" ]; then
        rm -rf "$DIR/.venv"
    fi
else
    info "PySide6 sistem tidak ditemukan/belum lengkap. Menyiapkan virtualenv lokal di $DIR/.venv..."
    python3 -m venv --system-site-packages "$DIR/.venv"
    "$DIR/.venv/bin/pip" install --upgrade pip --quiet
    info "Mengunduh PySide6-Essentials melalui pip..."
    "$DIR/.venv/bin/pip" install PySide6-Essentials
    PYTHON_CMD="\"$DIR/.venv/bin/python3\""
    ok "PySide6 berhasil dipasang di $DIR/.venv."
fi

# Cek ketersediaan librespot (di luar Arch biasanya tidak ada di repo apt/dnf standar)
ensure_librespot() {
    if command -v librespot &>/dev/null || [ -x "$BIN_DIR/librespot" ] || [ -x "$HOME/.cargo/bin/librespot" ]; then
        ok "librespot terdeteksi: $(command -v librespot || echo "$HOME/.cargo/bin/librespot")"
        return 0
    fi

    warn "librespot belum terpasang di sistem Anda."
    echo "  librespot diperlukan agar Nada bisa memutar audio langsung di komputer ini."
    echo "  (Di Arch Linux tersedia langsung lewat 'sudo pacman -S librespot')."

    local do_cargo="n"
    if [ -t 0 ]; then
        read -r -p ":: Apakah Anda ingin memasang librespot sekarang menggunakan Cargo/Rust? [Y/n] " do_cargo </dev/tty || do_cargo="n"
        do_cargo="${do_cargo:-Y}"
    fi

    if [[ "$do_cargo" =~ ^[Yy]$ ]]; then
        if ! command -v cargo &>/dev/null; then
            info "Memasang cargo & pustaka pengembangan audio..."
            if command -v apt-get &>/dev/null; then
                sudo apt-get install -y cargo pkg-config libasound2-dev libpulse-dev build-essential
            elif command -v dnf &>/dev/null; then
                sudo dnf install -y cargo rust pkgconf-pkg-config alsa-lib-devel pulseaudio-libs-devel gcc
            elif command -v zypper &>/dev/null; then
                sudo zypper install -y cargo rust pkg-config alsa-devel libpulse-devel gcc
            fi
        else
            # Pastikan header audio terpasang untuk kompilasi librespot
            if command -v apt-get &>/dev/null; then
                sudo apt-get install -y pkg-config libasound2-dev libpulse-dev build-essential || true
            elif command -v dnf &>/dev/null; then
                sudo dnf install -y pkgconf-pkg-config alsa-lib-devel pulseaudio-libs-devel gcc || true
            elif command -v zypper &>/dev/null; then
                sudo zypper install -y pkg-config alsa-devel libpulse-devel gcc || true
            fi
        fi

        if command -v cargo &>/dev/null; then
            info "Mengompilasi librespot lewat cargo (proses ini membutuhkan beberapa menit)..."
            cargo install librespot --locked --features pulseaudio-backend || cargo install librespot --locked
            mkdir -p "$BIN_DIR"
            if [ -x "$HOME/.cargo/bin/librespot" ] && [ ! -e "$BIN_DIR/librespot" ]; then
                ln -sf "$HOME/.cargo/bin/librespot" "$BIN_DIR/librespot"
            fi
            ok "librespot berhasil dipasang!"
        else
            warn "Cargo tidak tersedia. Anda dapat memasang librespot nanti dengan: cargo install librespot --locked"
        fi
    else
        warn "Melewati pemasangan librespot. Anda tetap bisa memakai Nada sebagai remote Spotify Connect."
    fi
}

if (( ! SKIP_DEPS )); then
    ensure_librespot
fi

# Buat launcher, ikon, dan entri desktop
mkdir -p "$BIN_DIR" "$APP_DIR_DESKTOP" "$ICON_DIR"
cat > "$BIN_DIR/nada" <<SH
#!/bin/sh
export PATH="\$HOME/.local/bin:\$HOME/.cargo/bin:\$PATH"
exec $PYTHON_CMD "$DIR/run.py" "\$@"
SH
chmod +x "$BIN_DIR/nada"

cp "$DIR/data/nada.svg" "$ICON_DIR/nada.svg"
sed "s|@BIN@|$BIN_DIR/nada|" "$DIR/data/nada.desktop" > "$APP_DIR_DESKTOP/nada.desktop"
update-desktop-database "$APP_DIR_DESKTOP" &>/dev/null || true

echo ""
ok "Instalasi selesai! Jalankan '${BOLD}nada${RESET}' di terminal atau buka ${BOLD}Nada${RESET} dari menu aplikasi."
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "Pastikan '$BIN_DIR' ada di PATH shell Anda:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
