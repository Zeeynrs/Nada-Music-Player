"""Minimal Spotify Web API client (Feb 2026 API: /items, /me/library, search limit 10)."""

import http.client
import json
import threading
import time
import urllib.parse

from .auth import TokenStore

HOST = "api.spotify.com"
BASE = f"https://{HOST}/v1"


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class SpotifyApi:
    """Keeps one HTTPS connection per worker thread: a fresh TLS handshake costs ~180 ms
    per request, which made play/pause feel sluggish."""

    def __init__(self, tokens: TokenStore):
        self.tokens = tokens
        self._local = threading.local()

    def _send(self, method, target, data, headers):
        """Send on this thread's kept-alive connection, reconnecting once if it went stale."""
        for attempt in (0, 1):
            conn = getattr(self._local, "conn", None)
            if conn is None:
                conn = self._local.conn = http.client.HTTPSConnection(HOST, timeout=15)
            try:
                conn.request(method, target, body=data, headers=headers)
                resp = conn.getresponse()
                return resp.status, resp.headers, resp.read()
            except (http.client.HTTPException, OSError) as e:
                conn.close()
                self._local.conn = None
                if attempt:
                    raise ApiError(0, f"Jaringan bermasalah: {e}") from e

    def request(self, method: str, path: str, params: dict | None = None, body=None, _retry: int = 0):
        url = path if path.startswith("http") else BASE + path
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None})
        target = url[len(f"https://{HOST}"):]
        headers = {"Authorization": f"Bearer {self.tokens.access_token(force_refresh=_retry == 1)}"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        elif method in ("PUT", "POST", "DELETE"):
            data = b""
        status, resp_headers, raw = self._send(method, target, data, headers)
        if status >= 400:
            if status == 401 and _retry == 0:
                return self.request(method, path, params, body, 1)
            if status in (502, 503) and _retry < 2:
                # Spotify answers 502 when a Connect device is slow to respond; usually fine on retry
                time.sleep(0.6)
                return self.request(method, path, params, body, _retry + 2)
            if status == 429 and _retry < 3:
                time.sleep(min(int(resp_headers.get("Retry-After", "1") or 1), 5))
                return self.request(method, path, params, body, _retry + 2)
            raise ApiError(status, _error_message(status, raw))
        # player commands reply 200 with a plain-text id instead of JSON
        try:
            return json.loads(raw) if raw.strip() else None
        except ValueError:
            return None

    def get(self, path, **params):
        return self.request("GET", path, params)

    def paged(self, path, max_items: int = 2000, **params):
        """Collect all `items` of an offset-paged endpoint."""
        items = []
        page = self.get(path, **params)
        while page:
            items.extend(page.get("items") or [])
            if not page.get("next") or len(items) >= max_items:
                break
            page = self.get(page["next"])
        return items


def _error_message(status: int, raw: bytes) -> str:
    try:
        err = json.loads(raw).get("error", {})
        msg = err.get("message") if isinstance(err, dict) else str(err)
    except (ValueError, AttributeError):
        msg = ""
    known = {
        403: "Spotify menolak permintaan ini (perlu Premium, atau dibatasi API)",
        404: "Tidak ada perangkat aktif / item tidak ditemukan",
        502: "Perangkat tidak merespons. Coba lagi, atau pilih perangkat lain di menu Perangkat.",
        503: "Spotify sedang sibuk, coba lagi sebentar lagi.",
    }
    if status in (502, 503):
        return known[status]
    return msg or known.get(status, f"HTTP {status}")


# ---- JSON normalisation -------------------------------------------------

def _images(images) -> tuple[str, str, str]:
    """Return (small, medium, large) image URLs from a Spotify images array."""
    imgs = sorted((i for i in images or [] if i.get("url")), key=lambda i: i.get("width") or 0)
    if not imgs:
        return "", "", ""
    small = next((i["url"] for i in imgs if (i.get("width") or 0) >= 64), imgs[0]["url"])
    medium = next((i["url"] for i in imgs if (i.get("width") or 0) >= 300), imgs[-1]["url"])
    return small, medium, imgs[-1]["url"]


def track(t: dict, album: dict | None = None) -> dict | None:
    if not t or t.get("type", "track") != "track" or not t.get("uri"):
        return None
    alb = t.get("album") or album or {}
    small, medium, large = _images(alb.get("images"))
    artists = t.get("artists") or []
    return {
        "uri": t["uri"],
        "id": t.get("id") or "",
        "name": t.get("name") or "",
        "artists": ", ".join(a.get("name", "") for a in artists),
        "artistId": artists[0].get("id", "") if artists else "",
        "album": alb.get("name") or "",
        "albumId": alb.get("id") or "",
        "imageSmall": small,
        "image": medium,
        "imageLarge": large,
        "durationMs": t.get("duration_ms") or 0,
        "explicit": bool(t.get("explicit")),
        "playable": t.get("is_playable", True) is not False,
    }


def wrapped_track(entry: dict) -> dict | None:
    """Playlist/library entries wrap the track in `item` (new) or `track` (legacy)."""
    return track(entry.get("item") or entry.get("track") or {})


def album(a: dict) -> dict:
    small, medium, large = _images(a.get("images"))
    return {
        "kind": "album",
        "id": a.get("id", ""),
        "uri": a.get("uri", ""),
        "name": a.get("name", ""),
        "subtitle": ", ".join(x.get("name", "") for x in a.get("artists") or []),
        "year": (a.get("release_date") or "")[:4],
        "albumType": a.get("album_type", "album"),
        "imageSmall": small,
        "image": medium,
        "imageLarge": large,
    }


def artist(a: dict) -> dict:
    small, medium, large = _images(a.get("images"))
    return {
        "kind": "artist",
        "id": a.get("id", ""),
        "uri": a.get("uri", ""),
        "name": a.get("name", ""),
        "subtitle": "Artis",
        "genres": ", ".join((a.get("genres") or [])[:3]),
        "imageSmall": small,
        "image": medium,
        "imageLarge": large,
    }


def playlist(p: dict) -> dict:
    small, medium, large = _images(p.get("images"))
    owner = (p.get("owner") or {})
    count = (p.get("items") or p.get("tracks") or {}).get("total")
    return {
        "kind": "playlist",
        "id": p.get("id", ""),
        "uri": p.get("uri", ""),
        "name": p.get("name", ""),
        "subtitle": owner.get("display_name") or owner.get("id") or "",
        "ownerId": owner.get("id", ""),
        "description": p.get("description") or "",
        "count": count if count is not None else -1,
        "imageSmall": small,
        "image": medium,
        "imageLarge": large,
    }
