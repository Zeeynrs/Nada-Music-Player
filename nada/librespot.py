"""Runs librespot as the local Spotify Connect device that actually plays audio."""

import os
import shutil
import subprocess
from collections import deque
from pathlib import Path

from PySide6.QtCore import Property, QObject, QProcess, QTimer, Signal, Slot

from .config import CACHE_DIR, LIBRESPOT_CACHE

LOG_FILE = CACHE_DIR / "librespot.log"
_BACKEND_CACHE: dict[str, str | None] = {}


def _find_librespot() -> str | None:
    exe = shutil.which("librespot")
    if exe:
        return exe
    for candidate in (Path.home() / ".local" / "bin" / "librespot", Path.home() / ".cargo" / "bin" / "librespot"):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _preferred_backend(exe: str) -> str | None:
    if exe in _BACKEND_CACHE:
        return _BACKEND_CACHE[exe]
    backend = None
    try:
        res = subprocess.run([exe, "--backend", "?"], capture_output=True, text=True, timeout=3)
        out = (res.stdout or "") + "\n" + (res.stderr or "")
        if "pulseaudio" in out:
            backend = "pulseaudio"
    except Exception:
        backend = "pulseaudio"
    _BACKEND_CACHE[exe] = backend
    return backend


def _distro_install_hint() -> str:
    if shutil.which("pacman"):
        return "Pasang dulu: sudo pacman -S librespot"
    if shutil.which("xbps-install"):
        return "Pasang dulu: sudo xbps-install -S librespot"
    if shutil.which("apk"):
        return "Pasang dulu: sudo apk add librespot"
    return "Pasang dulu lewat ./install.sh atau: cargo install librespot --locked"


class Librespot(QObject):
    statusChanged = Signal()
    logChanged = Signal()
    problem = Signal(str)
    ready = Signal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._status = "off"
        self._log = deque(maxlen=200)
        self._logfile = None
        self._buf = ""
        self._stopping = False
        self._restarts = 0
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(self._finished)
        self.proc.errorOccurred.connect(self._error)

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    @Property(bool, constant=True)
    def installed(self):
        return _find_librespot() is not None

    @Property(str, constant=True)
    def installHint(self):
        return _distro_install_hint()

    @Property(str, notify=logChanged)
    def log(self):
        return "\n".join(self._log)

    def _set_status(self, s):
        if s != self._status:
            self._status = s
            self.statusChanged.emit()

    @Slot()
    def start(self):
        exe = _find_librespot()
        if not exe:
            self._set_status("missing")
            return
        if self.proc.state() != QProcess.NotRunning:
            return
        LIBRESPOT_CACHE.mkdir(parents=True, exist_ok=True)
        args = [
            "--name", self.settings["device_name"],
            "--device-type", "computer",
        ]
        backend = _preferred_backend(exe)
        if backend:
            args.extend(["--backend", backend])
        args.extend([
            "--bitrate", str(self.settings["bitrate"]),
            "--cache", str(LIBRESPOT_CACHE),
            "--system-cache", str(LIBRESPOT_CACHE),
            "--cache-size-limit", "1G",
            "--enable-oauth",  # only used when no cached credentials exist
            "--initial-volume", "80",
            "--volume-ctrl", "log",
            "--volume-range", str(self.settings["volume_range"]),
        ])
        if self.settings["normalize"]:
            args.append("--enable-volume-normalisation")
        self._stopping = False
        try:
            self._logfile = open(LOG_FILE, "w", buffering=1)
        except OSError:
            self._logfile = None
        self._set_status("authenticating" if not (LIBRESPOT_CACHE / "credentials.json").exists() else "starting")
        self.proc.start(exe, args)

    @Slot()
    def restart(self):
        self.stop()
        self._restarts = 0
        QTimer.singleShot(300, self.start)

    @Slot()
    def stop(self):
        if self.proc.state() == QProcess.NotRunning:
            return
        self._stopping = True
        self.proc.terminate()
        if not self.proc.waitForFinished(2000):
            self.proc.kill()
            self.proc.waitForFinished(1000)

    @Slot()
    def forgetLogin(self):
        self.stop()
        (LIBRESPOT_CACHE / "credentials.json").unlink(missing_ok=True)
        QTimer.singleShot(300, self.start)

    def _read(self):
        self._buf += bytes(self.proc.readAllStandardOutput()).decode(errors="replace")
        *lines, self._buf = self._buf.split("\n")
        for line in lines:
            line = line.rstrip()
            if not line:
                continue
            self._log.append(line)
            if self._logfile:
                self._logfile.write(line + "\n")
            low = line.lower()
            if "authenticated as" in low:
                self._restarts = 0
                self._set_status("ready")
                self.ready.emit()
            elif "audio key" in low and "error" in low:
                self.problem.emit("librespot tidak diberi kunci audio oleh Spotify untuk lagu ini. "
                                  "Coba putar lewat perangkat lain (menu Perangkat).")
            elif "bad credentials" in low or "failed to authenticate" in low:
                self._set_status("error")
                self.problem.emit("Login librespot gagal. Buka Pengaturan → 'Login ulang perangkat'.")
        self.logChanged.emit()

    def _finished(self, *_):
        if self._stopping:
            self._set_status("off")
            return
        self._set_status("crashed")
        if self._restarts < 3:
            self._restarts += 1
            QTimer.singleShot(2000 * self._restarts, self.start)
        else:
            self.problem.emit("librespot berhenti terus-menerus. Lihat log di Pengaturan.")

    def _error(self, err):
        if err == QProcess.FailedToStart:
            self._set_status("missing")
