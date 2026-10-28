"""Audio spectrum bars from cava (reads the PipeWire or PulseAudio output monitor)."""

import os
import shutil
from pathlib import Path

from PySide6.QtCore import Property, QObject, QProcess, Signal, Slot

from .config import CACHE_DIR

BARS = 64


def _cava_config(method: str) -> str:
    return f"""
[general]
bars = {BARS}
framerate = 60
autosens = 1
lower_cutoff_freq = 35
higher_cutoff_freq = 14000

[input]
method = {method}
source = auto

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 1000
bar_delimiter = 59
frame_delimiter = 10
channels = mono

[smoothing]
noise_reduction = 62
"""


def _default_input_method() -> str:
    runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    if Path(runtime, "pipewire-0").exists():
        return "pipewire"
    return "pulse"


class Visualizer(QObject):
    barsChanged = Signal()
    activeChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bars = [0.0] * BARS
        self._active = False
        self._buf = b""
        self._method = _default_input_method()
        self._tried_fallback = False
        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(self._on_finished)

    @Property(bool, constant=True)
    def available(self):
        return shutil.which("cava") is not None

    @Property(int, constant=True)
    def count(self):
        return BARS

    @Property("QVariantList", notify=barsChanged)
    def bars(self):
        return self._bars

    def _get_active(self):
        return self._active

    def _launch_cava(self):
        exe = shutil.which("cava")
        if not exe:
            return
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        conf = CACHE_DIR / "cava.conf"
        conf.write_text(_cava_config(self._method))
        self._buf = b""
        self.proc.start(exe, ["-p", str(conf)])

    def _on_finished(self, exit_code, _exit_status):
        # If cava on another distro was built without PipeWire support, retry once with PulseAudio
        if self._active and exit_code != 0 and not self._tried_fallback and self._method == "pipewire":
            self._tried_fallback = True
            self._method = "pulse"
            self._launch_cava()

    @Slot(bool)
    def _set_active(self, on):
        on = bool(on) and self.available
        if on == self._active:
            return
        self._active = on
        if on:
            self._launch_cava()
        else:
            self.stop()
            self._bars = [0.0] * BARS
            self.barsChanged.emit()
        self.activeChanged.emit()

    active = Property(bool, _get_active, _set_active, notify=activeChanged)

    def _read(self):
        self._buf += bytes(self.proc.readAllStandardOutput())
        frames = self._buf.split(b"\n")
        self._buf = frames[-1]
        if len(frames) < 2:
            return
        last = frames[-2].decode(errors="ignore").strip(";").split(";")
        if len(last) == BARS:
            try:
                self._bars = [int(v) / 1000 for v in last]
            except ValueError:
                return
            self.barsChanged.emit()

    def stop(self):
        if self.proc.state() != QProcess.NotRunning:
            self.proc.terminate()
            if not self.proc.waitForFinished(1000):
                self.proc.kill()
