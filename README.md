# Nada

Pemutar Spotify ringan untuk desktop Linux (Wayland/Hyprland), terinspirasi dari
[Swiftify](https://github.com/swiftify-org/swiftify). Ditulis dengan Python + Qt Quick,
memutar audio lewat [librespot](https://github.com/librespot-org/librespot).

- Beranda, pencarian, Lagu Disukai, playlist, album, halaman artis, antrean
- Tampilan penuh: cover blur bergerak, lirik tersinkron (LRCLIB), visualizer (cava)
- Warna aksen otomatis dari cover album
- Pindah perangkat Spotify Connect (komputer ini, HP, speaker)
- MPRIS: `playerctl`, tombol media, hyprlock, dan widget bar bisa mengontrol Nada

## Kebutuhan

- Spotify **Premium**
- Client ID dari aplikasi di [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
  dengan Redirect URI `http://127.0.0.1:8898/login`, API "Web API", dan email akunmu
  ditambahkan di User Management
- Arch Linux: `pyside6 librespot python-dbus cava`

## Pasang & jalankan

```bash
git clone https://github.com/Zeeynrs/Nada-Music-Player.git
cd Nada-Music-Player
./install.sh   # pasang dependensi yang kurang + launcher ~/.local/bin/nada + entri menu
nada
```

Saat pertama kali jalan kamu login dua kali di browser: sekali untuk Web API (port 8898),
sekali untuk librespot (port 5588). Keduanya disimpan, jadi berikutnya langsung masuk.

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
