"""GitHub update checker and one-click self-updater."""

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from .config import CACHE_DIR

ROOT = Path(__file__).resolve().parent.parent
CHECK_INTERVAL_MS = 180_000  # 3 minutes


def _git(*args: str, timeout: int = 15) -> str:
    res = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if res.returncode != 0:
        err = (res.stderr or res.stdout or "").strip()
        raise RuntimeError(err or f"git {' '.join(args)} gagal")
    return res.stdout.strip()


def _send_desktop_notification(title: str, body: str) -> None:
    if not shutil.which("notify-send"):
        return
    try:
        subprocess.Popen(
            ["notify-send", "-a", "Nada", "-i", "nada", title, body],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


class Updater(QObject):
    changed = Signal()
    toast = Signal(str)
    restartRequested = Signal()

    def __init__(self, worker, parent=None):
        super().__init__(parent)
        self.worker = worker
        self._checking = False
        self._updating = False
        self._current_hash = ""
        self._current_msg = ""
        self._remote_hash = ""
        self._remote_msg = ""
        self._commits_behind = 0
        self._changelog = ""
        self._last_checked = "Belum diperiksa"
        self._notified_hash = ""
        self._dismissed_hash = ""

        self._is_git_repo = (ROOT / ".git").exists()
        self._read_local_head()

        self._timer = QTimer(self)
        self._timer.setInterval(CHECK_INTERVAL_MS)
        self._timer.timeout.connect(lambda: self.check(True))
        if self._is_git_repo:
            self._timer.start()
            QTimer.singleShot(2500, lambda: self.check(True))

    def _read_local_head(self):
        if not self._is_git_repo:
            self._current_hash = "paket sistem"
            self._current_msg = "Dipasang lewat paket"
            return
        try:
            self._current_hash = _git("rev-parse", "--short", "HEAD", timeout=3)
            self._current_msg = _git("log", "-1", "--format=%s", "HEAD", timeout=3)
        except Exception:
            self._current_hash = "unknown"
            self._current_msg = ""

    @Property(bool, notify=changed)
    def checking(self):
        return self._checking

    @Property(bool, notify=changed)
    def updating(self):
        return self._updating

    @Property(bool, notify=changed)
    def updateAvailable(self):
        return self._commits_behind > 0

    @Property(bool, notify=changed)
    def bannerVisible(self):
        return self._commits_behind > 0 and self._remote_hash != self._dismissed_hash

    @Property(int, notify=changed)
    def commitsBehind(self):
        return self._commits_behind

    @Property(str, notify=changed)
    def currentHash(self):
        return self._current_hash

    @Property(str, notify=changed)
    def currentMessage(self):
        return self._current_msg

    @Property(str, notify=changed)
    def remoteHash(self):
        return self._remote_hash

    @Property(str, notify=changed)
    def remoteMessage(self):
        return self._remote_msg

    @Property(str, notify=changed)
    def changelog(self):
        return self._changelog

    @Property(str, notify=changed)
    def lastChecked(self):
        return self._last_checked

    @Property(str, notify=changed)
    def statusText(self):
        if self._updating:
            return "Mengunduh & memasang pembaruan…"
        if self._checking:
            return "Memeriksa commit terbaru di GitHub…"
        if self._commits_behind > 0:
            return f"Tersedia {self._commits_behind} commit baru ({self._remote_hash})"
        return f"Sudah versi terbaru ({self._current_hash})"

    @Slot()
    def dismissBanner(self):
        self._dismissed_hash = self._remote_hash
        self.changed.emit()

    @Slot()
    @Slot(bool)
    def check(self, silent: bool = False):
        if not self._is_git_repo:
            if not silent:
                self.toast.emit("Nada dipasang lewat paket sistem. Gunakan manajer paket atau ./install.sh untuk memperbarui.")
            return
        if self._checking or self._updating:
            return
        self._checking = True
        self.changed.emit()

        def job():
            branch = _git("rev-parse", "--abbrev-ref", "HEAD", timeout=5) or "main"
            if branch == "HEAD":
                branch = "main"
            _git("fetch", "origin", branch, "--quiet", timeout=20)
            local_hash = _git("rev-parse", "--short", "HEAD", timeout=5)
            local_msg = _git("log", "-1", "--format=%s", "HEAD", timeout=5)
            remote_ref = f"origin/{branch}"
            remote_hash = _git("rev-parse", "--short", remote_ref, timeout=5)
            remote_msg = _git("log", "-1", "--format=%s", remote_ref, timeout=5)
            behind_str = _git("rev-list", "--count", f"HEAD..{remote_ref}", timeout=5)
            behind = int(behind_str) if behind_str.isdigit() else 0
            log_lines = ""
            if behind > 0:
                log_lines = _git("log", "--format=• %h — %s (%cr)", f"HEAD..{remote_ref}", timeout=5)
            return {
                "local_hash": local_hash,
                "local_msg": local_msg,
                "remote_hash": remote_hash,
                "remote_msg": remote_msg,
                "behind": behind,
                "changelog": log_lines,
            }

        def on_ok(info):
            self._checking = False
            self._current_hash = info["local_hash"]
            self._current_msg = info["local_msg"]
            self._remote_hash = info["remote_hash"]
            self._remote_msg = info["remote_msg"]
            self._commits_behind = info["behind"]
            self._changelog = info["changelog"]
            self._last_checked = datetime.now().strftime("%H:%M")
            self.changed.emit()

            if self._commits_behind > 0:
                if self._remote_hash != self._notified_hash:
                    self._notified_hash = self._remote_hash
                    msg = f"Update GitHub tersedia ({self._commits_behind} commit): {self._remote_msg}"
                    self.toast.emit(msg)
                    _send_desktop_notification(
                        "Pembaruan Nada Tersedia",
                        f"{self._remote_msg}\n({self._commits_behind} commit baru di GitHub)",
                    )
                elif not silent:
                    self.toast.emit(f"Tersedia {self._commits_behind} commit baru: {self._remote_msg}")
            elif not silent:
                self.toast.emit("Nada sudah berada di commit terbaru")

        def on_err(err):
            self._checking = False
            self.changed.emit()
            if not silent:
                self.toast.emit(f"Gagal memeriksa update: {err}")

        self.worker.run(job, on_ok, on_err)

    @Slot()
    def applyUpdate(self):
        if not self._is_git_repo:
            self.toast.emit("Nada dipasang lewat paket sistem. Gunakan manajer paket atau ./install.sh untuk memperbarui.")
            return
        if self._updating:
            return
        self._updating = True
        self.changed.emit()
        self.toast.emit("Mengunduh commit terbaru dari GitHub…")

        def job():
            branch = _git("rev-parse", "--abbrev-ref", "HEAD", timeout=5) or "main"
            if branch == "HEAD":
                branch = "main"
            _git("fetch", "origin", branch, "--quiet", timeout=25)
            dirty = _git("status", "--porcelain", timeout=5)
            stashed = False
            if dirty:
                _git("stash", "push", "--include-untracked", "-m", "nada-auto-update", timeout=10)
                stashed = True
            try:
                _git("merge", "--ff-only", f"origin/{branch}", timeout=20)
            except Exception:
                _git("reset", "--hard", f"origin/{branch}", timeout=20)
            if stashed:
                try:
                    _git("stash", "pop", timeout=10)
                except Exception:
                    pass

            # Clear QML bytecode cache so updated QML files load fresh
            qmlcache = CACHE_DIR / "Nada" / "qmlcache"
            if qmlcache.exists():
                shutil.rmtree(qmlcache, ignore_errors=True)

            # Keep launcher & icon up to date
            bin_dir = Path.home() / ".local" / "bin"
            if bin_dir.exists():
                launcher = bin_dir / "nada"
                venv_py = ROOT / ".venv" / "bin" / "python3"
                if venv_py.exists():
                    py_cmd = f'"{venv_py}"'
                else:
                    py_cmd = "python3 -I"
                launcher.write_text(
                    '#!/bin/sh\n'
                    'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"\n'
                    f'exec {py_cmd} "{ROOT / "run.py"}" "$@"\n'
                )
                launcher.chmod(0o755)
            icon_src = ROOT / "data" / "nada.svg"
            icon_dst = Path.home() / ".local" / "share" / "icons" / "hicolor" / "scalable" / "apps" / "nada.svg"
            if icon_src.exists() and icon_dst.parent.exists():
                shutil.copy2(icon_src, icon_dst)

            new_hash = _git("rev-parse", "--short", "HEAD", timeout=5)
            new_msg = _git("log", "-1", "--format=%s", "HEAD", timeout=5)
            return {"hash": new_hash, "msg": new_msg}

        def on_ok(res):
            self._updating = False
            self._current_hash = res["hash"]
            self._current_msg = res["msg"]
            self._remote_hash = res["hash"]
            self._remote_msg = res["msg"]
            self._commits_behind = 0
            self._changelog = ""
            self.changed.emit()
            self.toast.emit(f"Berhasil diperbarui ke {res['hash']}! Memulai ulang Nada…")
            _send_desktop_notification(
                "Nada Berhasil Diperbarui",
                f"Berjalan di commit {res['hash']}: {res['msg']}",
            )
            QTimer.singleShot(900, self.restartRequested.emit)

        def on_err(err):
            self._updating = False
            self.changed.emit()
            self.toast.emit(f"Gagal memperbarui: {err}")

        self.worker.run(job, on_ok, on_err)
