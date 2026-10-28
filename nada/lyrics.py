"""Synced lyrics from LRCLIB (https://lrclib.net), a free public lyrics database."""

import bisect
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from PySide6.QtCore import Property, QObject, Signal

LRC_LINE = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")
HEADERS = {"User-Agent": "Nada/0.1 (desktop music player)"}


def _get(path, **params):
    url = "https://lrclib.net/api" + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def parse_lrc(text: str):
    lines = []
    for raw in text.splitlines():
        stamps = LRC_LINE.findall(raw)
        words = LRC_LINE.sub("", raw).strip()
        for m, s in stamps:
            lines.append({"t": int((int(m) * 60 + float(s)) * 1000), "text": words})
    lines.sort(key=lambda l: l["t"])
    return lines


def fetch_lyrics(track: dict):
    params = {"track_name": track["name"], "artist_name": track["artists"].split(",")[0]}
    hit = _get("/get", **params, album_name=track.get("album", ""),
               duration=round(track.get("durationMs", 0) / 1000))
    if not hit or not (hit.get("syncedLyrics") or hit.get("plainLyrics")):
        results = _get("/search", **params) or []
        hit = next((r for r in results if r.get("syncedLyrics")), None) or \
            next((r for r in results if r.get("plainLyrics")), None)
    if not hit:
        return {"synced": False, "lines": []}
    if hit.get("syncedLyrics"):
        return {"synced": True, "lines": parse_lrc(hit["syncedLyrics"])}
    if hit.get("instrumental"):
        return {"synced": False, "lines": [{"t": 0, "text": "♪ Instrumental ♪"}]}
    return {"synced": False, "lines": [{"t": 0, "text": l} for l in hit["plainLyrics"].splitlines()]}


class Lyrics(QObject):
    changed = Signal()
    currentChanged = Signal()

    def __init__(self, player, worker, parent=None):
        super().__init__(parent)
        self.player = player
        self.worker = worker
        self._cache = {}
        self._uri = ""
        self._lines = []
        self._times = []
        self._synced = False
        self._status = "idle"
        self._current = -1
        player.trackChanged.connect(self._on_track)
        player.positionChanged.connect(self._on_position)

    @Property("QVariantList", notify=changed)
    def lines(self):
        return self._lines

    @Property(bool, notify=changed)
    def synced(self):
        return self._synced

    @Property(str, notify=changed)
    def status(self):
        return self._status  # idle | loading | ready | none | error

    @Property(int, notify=currentChanged)
    def current(self):
        return self._current

    def _set(self, uri, data, status):
        if uri != self._uri:
            return
        self._lines = data.get("lines", [])
        self._times = [l["t"] for l in self._lines]
        self._synced = data.get("synced", False)
        self._status = status if self._lines or status != "ready" else "none"
        self._current = -1
        self.changed.emit()
        self._on_position()

    def _on_track(self):
        st = self.player.state
        self._uri = st.get("uri", "")
        if not self._uri:
            self._set("", {}, "idle")
            return
        if self._uri in self._cache:
            self._set(self._uri, self._cache[self._uri], "ready")
            return
        uri = self._uri
        self._set(uri, {}, "loading")
        track = dict(st)

        def done(data):
            self._cache[uri] = data
            self._set(uri, data, "ready")
        self.worker.run(lambda: fetch_lyrics(track), done, lambda e: self._set(uri, {}, "error"))

    def _on_position(self):
        if not self._synced:
            return
        idx = bisect.bisect_right(self._times, self.player.position + 250) - 1
        if idx != self._current:
            self._current = idx
            self.currentChanged.emit()
