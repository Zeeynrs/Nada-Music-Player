# Nada

Pemutar Spotify ringan untuk desktop Linux (Wayland/Hyprland & X11), terinspirasi dari
[Swiftify](https://github.com/swiftify-org/swiftify). Ditulis dengan Python + Qt Quick,
memutar audio lewat [librespot](https://github.com/librespot-org/librespot).

- Beranda, pencarian, Lagu Disukai, playlist, album, halaman artis, antrean
- Tampilan penuh (Immersive Player): cover bergelombang, dual visualizer (cava), lirik tersinkron (LRCLIB), dan panel Equalizer
- Warna aksen otomatis dari cover album
- Pindah perangkat Spotify Connect (komputer ini, HP, speaker)
- Pembaruan otomatis langsung dari GitHub di dalam aplikasi
- MPRIS: `playerctl`, tombol media, hyprlock, dan widget bar bisa mengontrol Nada

## Distro yang Direkomendasikan & Kompatibilitas

> **Rekomendasi Utama: Arch Linux** (serta turunannya seperti EndeavourOS, CachyOS, Manjaro, Garuda).
> Seluruh dependensi utama (`pyside6`, `librespot`, `python-dbus`, `cava`) tersedia langsung secara native di repositori resmi Arch tanpa perlu kompilasi tambahan.

Meski demikian, **Nada kompatibel dengan berbagai distro Linux** (Debian, Ubuntu, Linux Mint, Pop!_OS, Fedora, Nobara, openSUSE, Void Linux, Alpine, dll.). Skrip `./install.sh` akan otomatis mendeteksi distro Anda, memasang paket yang sesuai, membuat *virtual environment* lokal (`.venv`) bila `PySide6` belum tersedia di repo distro Anda, serta membantu memasang `librespot` lewat Cargo bila diperlukan.

## Kebutuhan & Persiapan

1. **Akun Spotify Premium** (diperlukan untuk pemutaran via librespot / Spotify Connect).
2. **Spotify Developer Client ID** (gratis, sekali buat):
   - Masuk ke [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) dengan akun Spotify-mu.
   - Klik **Create app**.
   - Isi **App name** dan **Description** bebas (contoh: `Nada Player`).
   - Pada kolom **Redirect URIs**, masukkan:  
     `http://127.0.0.1:8898/login`
   - Pada bagian **Which API/SDKs are you planning to use?**, centang **Web API**.
   - Centang persetujuan Terms of Service, lalu klik **Save**.
   - Masuk ke menu **User Management**, tambahkan alamat email akun Spotify-mu.
   - Masuk ke menu **Settings** (tab Basic Information), salin **Client ID** (Client Secret **tidak** diperlukan).

---

## Cara Install (Instalasi)

Nada dapat dipasang di berbagai distro Linux. Pilih salah satu metode di bawah ini:

### Opsi 1: Instalasi Cepat Satu Baris (Semua Distro — Direkomendasikan)

Buka terminal dan jalankan perintah berikut:

```bash
curl -fsSL https://raw.githubusercontent.com/Zeeynrs/Nada-Music-Player/main/install.sh | bash
```

Perintah di atas akan:
- Mengunduh Nada ke `~/.local/share/nada`
- Mendeteksi distro Anda dan memasang paket dependensi yang dibutuhkan secara otomatis
- Membuat launcher di `~/.local/bin/nada`
- Memasang ikon dan entri menu aplikasi desktop (`.desktop`)

### Opsi 2: Clone Manual & Skrip `./install.sh` (Semua Distro)

Jika Anda ingin melihat atau mengedit kode secara lokal:

```bash
git clone https://github.com/Zeeynrs/Nada-Music-Player.git
cd Nada-Music-Player
./install.sh
```

### Opsi 3: Paket Native Arch Linux (`makepkg`)

Bagi pengguna **Arch Linux** dan turunannya (EndeavourOS, CachyOS, Manjaro, dll.), Anda bisa memasang Nada langsung sebagai paket sistem native `pacman` via PKGBUILD:

```bash
git clone https://github.com/Zeeynrs/Nada-Music-Player.git
cd Nada-Music-Player
makepkg -si
```

---

## Cara Menjalankan & Login Pertama Kali

1. **Jalankan Nada**:
   - Ketik `nada` di terminal, atau
   - Buka **Nada** melalui menu aplikasi / app launcher desktop Anda (Rofi, Wofi, KDE Application Launcher, GNOME, dsb.).
2. **Masukkan Client ID**: Tempel Client ID yang sudah Anda salin dari Spotify Developer Dashboard, lalu klik **Simpan & Lanjut**.
3. **Otentikasi Browser**:
   - Browser Anda akan otomatis terbuka untuk login Web API (port 8898). Klik **Agree / Setuju**.
   - Selanjutnya browser akan membuka port 5588 untuk otorisasi `librespot`.
4. Setelah selesai, sesi dan token disimpan di `~/.config/nada/` sehingga untuk penggunaan berikutnya Anda bisa langsung menikmati musik tanpa login ulang.

### Cara Memperbarui (Update)

- **Dari dalam aplikasi**: Masuk ke menu **Pengaturan** > periksa pembaruan di bagian **Pembaruan Aplikasi**. Jika ada versi baru, klik tombol pembaruan untuk update otomatis.
- **Manual (Git)**:
  ```bash
  cd Nada-Music-Player # atau cd ~/.local/share/nada
  git pull
  ./install.sh --no-deps
  ```

### Menghapus Instalasi (Uninstall)

```bash
./install.sh --uninstall
# atau jika dipasang via makepkg di Arch Linux:
sudo pacman -R nada-music-player-git
```

## Pintasan

| Tombol | Aksi |
|---|---|
| Spasi | Putar / jeda |
| Ctrl + → / ← | Berikutnya / sebelumnya |
| Ctrl + ↑ / ↓ | Volume |
| Ctrl + F | Cari |
| Ctrl + L | Tampilan penuh + lirik |
| Esc / Alt + ← | Tutup tampilan penuh / kembali |
| Ctrl + , | Pengaturan |

## Hyprland

App ID (class) jendelanya `nada`, bisa dipakai untuk window rule. Untuk tombol media,
arahkan bind ke `playerctl -p nada play-pause` (atau `playerctl play-pause` saja jika
Nada satu-satunya pemutar yang aktif).

## Catatan API Spotify (Februari 2026)

Spotify membatasi aplikasi pihak ketiga: isi playlist milik orang lain tidak bisa dibaca
(tapi tetap bisa diputar), endpoint "lagu populer artis" dihapus (Nada memakai pencarian
sebagai gantinya), dan pencarian maksimal 10 hasil per jenis.

Jika librespot gagal memutar dengan error `audio key`, Spotify menolak librespot untuk
akunmu. Kamu tetap bisa memakai Nada sebagai remote untuk perangkat lain lewat menu Perangkat.

## File

- Pengaturan & token: `~/.config/nada/` (token disimpan dengan izin 600)
- Cache librespot & cava: `~/.cache/nada/`

## Lisensi

GPL-3.0, lihat [LICENSE](LICENSE). Ikon dari [Material Design Icons](https://github.com/google/material-design-icons)
(Apache-2.0). Lirik dari [LRCLIB](https://lrclib.net).
