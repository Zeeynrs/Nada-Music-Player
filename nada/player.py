"""Playback state and controls through the Spotify Connect Web API."""

import colorsys
import time
import urllib.request

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QImage

from . import api as sp
from .api import ApiError

DEFAULT_ACCENT = "#9ecaff"


def download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read()


def accent_from_image(data: bytes) -> str:
    """Pick a lively, readable-on-dark colour from album art.

    Runs on the UI thread: PySide6 types are not safe to first-use from worker threads.
    """
    img = QImage.fromData(data)
    if img.isNull():
        return DEFAULT_ACCENT
    img = img.scaled(24, 24)
    bins = [[0.0, 0.0, 0.0, 0.0] for _ in range(12)]  # weight, r, g, b
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            r, g, b = c.redF(), c.greenF(), c.blueF()
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            w = s * s * v + 0.002
            slot = bins[int(h * 12) % 12]
            slot[0] += w
            slot[1] += r * w
            slot[2] += g * w
            slot[3] += b * w
    w, r, g, b = max(bins, key=lambda b: b[0])
    h, s, v = colorsys.rgb_to_hsv(r / w, g / w, b / w)
    s = min(max(s, 0.35), 0.75) if s > 0.08 else s
    v = max(v, 0.82)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


class Player(QObject):
    stateChanged = Signal()
    positionChanged = Signal()
    devicesChanged = Signal()
    queueChanged = Signal()
    accentChanged = Signal()
    trackChanged = Signal()
    likedChanged = Signal(str, bool)

    def __init__(self, api: sp.SpotifyApi, worker, librespot, settings, parent=None):
        super().__init__(parent)
        self.api = api
        self.worker = worker
        self.librespot = librespot
        self.settings = settings
        self._state = {"hasTrack": False}
        self._devices = []
        self._queue = []
        self._accent = DEFAULT_ACCENT
        self._pos_base = 0
        self._pos_time = time.monotonic()
        self._polling = False
        self._fast = False
        self._last_command = 0.0
        self._inflight = 0
        self._device_cache = []  # raw /me/player/devices entries, refreshed by refreshDevices()
        self._pending_volume = None

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.refresh)
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(250)
        self.tick_timer.timeout.connect(self._tick)
        self.volume_timer = QTimer(self)
        self.volume_timer.setSingleShot(True)
        self.volume_timer.setInterval(200)
        self.volume_timer.timeout.connect(self._send_volume)
        librespot.ready.connect(lambda: QTimer.singleShot(1500, self.refreshDevices))

    # ---- properties -----------------------------------------------------

    @Property("QVariantMap", notify=stateChanged)
    def state(self):
        return self._state

    @Property(int, notify=positionChanged)
    def position(self):
        if not self._state.get("isPlaying"):
            return self._pos_base
        elapsed = int((time.monotonic() - self._pos_time) * 1000)
        return min(self._pos_base + elapsed, self._state.get("durationMs", 0))

    @Property("QVariantList", notify=devicesChanged)
    def devices(self):
        return self._devices

    @Property("QVariantList", notify=queueChanged)
    def queue(self):
        return self._queue

    @Property(str, notify=accentChanged)
    def accent(self):
        return self._accent

    # ---- polling --------------------------------------------------------

    def start(self):
        self.poll_timer.start(1500)
        self.tick_timer.start()
        self.refresh()
        self.refreshDevices()

    def stop(self):
        self.poll_timer.stop()
        self.tick_timer.stop()

    @Slot(bool)
    def setFastPolling(self, fast: bool):
        """Poll faster while the window is focused, slower in the background."""
        self.poll_timer.setInterval(1500 if fast else 5000)

    def _tick(self):
        if self._state.get("isPlaying"):
            self.positionChanged.emit()
            if self.position >= self._state.get("durationMs", 0) > 0:
                self._schedule_refresh(400)

    def _schedule_refresh(self, ms=350):
        QTimer.singleShot(ms, self.refresh)

    @Slot()
    def refresh(self):
        if self._polling:
            return
        self._polling = True
        started = time.monotonic()

        def fetch():
            return self.api.get("/me/player", additional_types="track")

        def done(data):
            self._polling = False
            # a command sent (or still running) while this poll was in flight makes it stale
            if started < self._last_command or self._inflight:
                return
            self._apply(data)

        def failed(e):
            self._polling = False

        self.worker.run(fetch, done, failed)

    def _apply(self, data):
        old_uri = self._state.get("uri")
        if not data or not data.get("item"):
            device = (data or {}).get("device") or {}
            self._state = {"hasTrack": False, "deviceName": device.get("name", ""),
                           "deviceId": device.get("id", "")}
            self._pos_base = 0
        else:
            t = sp.track(data["item"]) or {}
            device = data.get("device") or {}
            ctx = data.get("context") or {}
            self._state = {
                **t,
                "hasTrack": True,
                "isPlaying": bool(data.get("is_playing")),
                "shuffle": bool(data.get("shuffle_state")),
                "repeat": data.get("repeat_state", "off"),
                "volume": device.get("volume_percent") if device.get("volume_percent") is not None else -1,
                "supportsVolume": device.get("supports_volume", True),
                "deviceId": device.get("id", ""),
                "deviceName": device.get("name", ""),
                "deviceType": device.get("type", ""),
                "contextUri": ctx.get("uri", ""),
                "liked": self._state.get("liked", False) if self._state.get("uri") == t.get("uri") else False,
            }
            if self._pending_volume is not None:
                self._state["volume"] = self._pending_volume
            self._pos_base = data.get("progress_ms") or 0
            self._pos_time = time.monotonic()
        self.stateChanged.emit()
        self.positionChanged.emit()
        if self._state.get("uri") != old_uri:
            self.trackChanged.emit()
            self._on_track_changed()

    def _on_track_changed(self):
        uri = self._state.get("uri")
        if not uri:
            return
        self.worker.run(lambda: self.api.get("/me/library/contains", uris=uri),
                        lambda res: self._patch(liked=bool(res and res[0])) if self._state.get("uri") == uri else None,
                        lambda e: None)
        art = self._state.get("imageSmall")
        if art:
            self.worker.run(lambda: download(art), lambda data: self._set_accent(accent_from_image(data)),
                            lambda e: None)
        self.refreshQueue()

    def _set_accent(self, color):
        if color != self._accent:
            self._accent = color
            self.accentChanged.emit()

    def _patch(self, **values):
        self._state = {**self._state, **values}
        self.stateChanged.emit()

    # ---- commands -------------------------------------------------------

    def _command(self, method, path, params=None, body=None, refresh_ms=400, ensure_device=False):
        def call():
            p = dict(params or {})
            dev = self._target_device_id() if ensure_device else ""
            if dev:
                p["device_id"] = dev
            try:
                return self.api.request(method, path, p, body)
            except ApiError as e:
                if not dev or e.status not in (404, 502):
                    raise
                # an idle Connect device sometimes rejects a direct command: wake it, retry once
                self.api.request("PUT", "/me/player", body={"device_ids": [dev], "play": False})
                time.sleep(0.4)
                return self.api.request(method, path, p, body)

        self._run_command(call, refresh_ms)

    def _run_command(self, call, refresh_ms):
        self._last_command = time.monotonic()
        self._inflight += 1

        def finished():
            self._inflight -= 1
            self._last_command = time.monotonic()

        def ok(_):
            finished()
            self._schedule_refresh(refresh_ms)

        def failed(e):
            finished()
            msg = str(e)
            if isinstance(e, ApiError) and e.status == 404:
                msg = "Tidak ada perangkat aktif. Pilih perangkat dari tombol Perangkat."
            self.worker.error.emit(msg)
            self._schedule_refresh(100)

        self.worker.run(call, ok, failed)

    def _target_device_id(self) -> str:
        """Runs in a worker thread: "" if Spotify has an active device, else our librespot device."""
        if self._state.get("deviceId"):
            return ""
        devices = self._device_cache or (self.api.get("/me/player/devices") or {}).get("devices") or []
        if any(d.get("is_active") for d in devices):
            return ""
        name = self.settings["device_name"]
        for d in devices:
            if d.get("name") == name:
                return d.get("id")
        return devices[0].get("id") if devices else ""

    @Slot()
    def togglePlay(self):
        playing = self._state.get("isPlaying")
        if self._state.get("hasTrack"):
            self._pos_base = self.position
            self._pos_time = time.monotonic()
            self._patch(isPlaying=not playing)
        # a transfer with play=true is not used here: librespot often ignores it ("context is not available")
        self._command("PUT", "/me/player/pause" if playing else "/me/player/play", ensure_device=not playing)

    @Slot()
    def next(self):
        self._command("POST", "/me/player/next", refresh_ms=600)

    @Slot(int)
    def skip(self, count):
        """Jump forward `count` tracks (used to play an item from the queue)."""
        def call():
            for _ in range(max(1, count)):
                self.api.request("POST", "/me/player/next")

        self._run_command(call, 700)

    @Slot()
    def previous(self):
        if self.position > 4000:
            self.seek(0)
        else:
            self._command("POST", "/me/player/previous", refresh_ms=600)

    @Slot(int)
    def seek(self, ms):
        self._pos_base = max(0, int(ms))
        self._pos_time = time.monotonic()
        self.positionChanged.emit()
        self._command("PUT", "/me/player/seek", {"position_ms": int(ms)}, refresh_ms=800)

    @Slot(int)
    def setVolume(self, pct):
        self._pending_volume = max(0, min(100, int(pct)))
        self._patch(volume=self._pending_volume)
        self.volume_timer.start()

    def _send_volume(self):
        vol = self._pending_volume
        self._command("PUT", "/me/player/volume", {"volume_percent": vol}, refresh_ms=1200)
        QTimer.singleShot(1500, lambda: setattr(self, "_pending_volume", None)
                          if self._pending_volume == vol else None)

    @Slot()
    def toggleShuffle(self):
        value = not self._state.get("shuffle")
        self._patch(shuffle=value)
        self._command("PUT", "/me/player/shuffle", {"state": "true" if value else "false"})

    @Slot()
    def cycleRepeat(self):
        nxt = {"off": "context", "context": "track", "track": "off"}[self._state.get("repeat", "off")]
        self._patch(repeat=nxt)
        self._command("PUT", "/me/player/repeat", {"state": nxt})

    @Slot(str, str)
    def playContext(self, context_uri, offset_uri=""):
        body = {"context_uri": context_uri}
        if offset_uri:
            body["offset"] = {"uri": offset_uri}
        self._command("PUT", "/me/player/play", body=body, refresh_ms=700, ensure_device=True)

    @Slot("QVariantList", int)
    def playUris(self, uris, index=0):
        uris = [u for u in uris if u]
        start = max(0, index - 20)
        chunk = uris[start:start + 100]
        if not chunk:
            return
        body = {"uris": chunk, "offset": {"position": index - start}}
        self._command("PUT", "/me/player/play", body=body, refresh_ms=700, ensure_device=True)

    @Slot(str)
    def shufflePlay(self, context_uri):
        self._command("PUT", "/me/player/shuffle", {"state": "true"}, ensure_device=True)
        QTimer.singleShot(250, lambda: self.playContext(context_uri, ""))

    @Slot(str)
    def addToQueue(self, uri):
        self._command("POST", "/me/player/queue", {"uri": uri}, refresh_ms=500)
        QTimer.singleShot(800, self.refreshQueue)
        self.worker.error.emit("Ditambahkan ke antrean")

    @Slot()
    def toggleLike(self):
        uri = self._state.get("uri")
        if uri:
            self.setLiked(uri, not self._state.get("liked"))

    @Slot(str, bool)
    def setLiked(self, uri, liked):
        if uri == self._state.get("uri"):
            self._patch(liked=liked)
        self.worker.run(lambda: self.api.request("PUT" if liked else "DELETE", "/me/library", {"uris": uri}),
                        lambda _: self.likedChanged.emit(uri, liked))

    # ---- devices & queue --------------------------------------------------

    @Slot()
    def refreshDevices(self):
        def done(data):
            name = self.settings["device_name"]
            self._device_cache = (data or {}).get("devices") or []
            devs = []
            for d in (data or {}).get("devices") or []:
                devs.append({
                    "id": d.get("id") or "",
                    "name": d.get("name") or "",
                    "type": (d.get("type") or "").lower(),
                    "active": bool(d.get("is_active")),
                    "volume": d.get("volume_percent") or 0,
                    "local": d.get("name") == name,
                    "restricted": bool(d.get("is_restricted")),
                })
            self._devices = devs
            self.devicesChanged.emit()
        self.worker.run(lambda: self.api.get("/me/player/devices"), done, lambda e: None)

    @Slot(str)
    def transfer(self, device_id):
        self._command("PUT", "/me/player", body={"device_ids": [device_id], "play": True}, refresh_ms=900)
        QTimer.singleShot(1200, self.refreshDevices)

    @Slot()
    def refreshQueue(self):
        def done(data):
            self._queue = [t for t in (sp.track(x) for x in (data or {}).get("queue") or []) if t][:30]
            self.queueChanged.emit()
        self.worker.run(lambda: self.api.get("/me/player/queue"), done, lambda e: None)
