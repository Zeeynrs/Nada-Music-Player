"""Library browsing: home, playlists, albums, artists, liked songs and search."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from . import api as sp
from .api import ApiError


class Library(QObject):
    meChanged = Signal()
    playlistsChanged = Signal()
    homeChanged = Signal()
    loaded = Signal(str, "QVariantMap")  # page key, data
    searchFinished = Signal(str, "QVariantMap")  # query, results

    def __init__(self, api: sp.SpotifyApi, worker, parent=None):
        super().__init__(parent)
        self.api = api
        self.worker = worker
        self._me = {}
        self._playlists = []
        self._home = {}

    @Property("QVariantMap", notify=meChanged)
    def me(self):
        return self._me

    @Property("QVariantList", notify=playlistsChanged)
    def playlists(self):
        return self._playlists

    @Property("QVariantMap", notify=homeChanged)
    def home(self):
        return self._home

    @Slot()
    def refreshAll(self):
        self.worker.run(self._fetch_me, self._set_me)
        self.worker.run(lambda: self.api.paged("/me/playlists", max_items=500, limit=50), self._set_playlists)
        self.worker.run(self._fetch_home, self._set_home)

    def _fetch_me(self):
        me = self.api.get("/me") or {}
        small, medium, _ = sp._images(me.get("images"))
        return {"id": me.get("id", ""), "name": me.get("display_name") or me.get("id", ""), "image": small}

    def _set_me(self, me):
        self._me = me
        self.meChanged.emit()

    def _set_playlists(self, items):
        self._playlists = [sp.playlist(p) for p in items if p]
        self.playlistsChanged.emit()

    def _fetch_home(self):
        home = {"recent": [], "topTracks": [], "topArtists": []}
        try:
            seen = set()
            for entry in (self.api.get("/me/player/recently-played", limit=50) or {}).get("items") or []:
                t = (entry.get("track") or {})
                alb = t.get("album") or {}
                if alb.get("id") and alb["id"] not in seen:
                    seen.add(alb["id"])
                    home["recent"].append(sp.album(alb))
            home["recent"] = home["recent"][:12]
        except ApiError:
            pass
        try:
            items = (self.api.get("/me/top/tracks", limit=10, time_range="short_term") or {}).get("items") or []
            home["topTracks"] = [t for t in map(sp.track, items) if t]
        except ApiError:
            pass
        try:
            items = (self.api.get("/me/top/artists", limit=12, time_range="medium_term") or {}).get("items") or []
            home["topArtists"] = [sp.artist(a) for a in items]
        except ApiError:
            pass
        return home

    def _set_home(self, home):
        self._home = home
        self.homeChanged.emit()

    # ---- pages ------------------------------------------------------------

    @Slot(str, str)
    def load(self, kind, item_id):
        key = f"{kind}:{item_id}"
        fetch = {
            "playlist": self._fetch_playlist,
            "album": self._fetch_album,
            "artist": self._fetch_artist,
            "liked": lambda _: self._fetch_liked(),
        }[kind]
        self.worker.run(lambda: fetch(item_id),
                        lambda data: self.loaded.emit(key, data),
                        lambda e: self.loaded.emit(key, {"error": str(e)}))

    def _fetch_playlist(self, pid):
        meta = sp.playlist(self.api.get(f"/playlists/{pid}") or {})
        note = ""
        tracks = []
        try:
            items = self.api.paged(f"/playlists/{pid}/items", limit=50, additional_types="track")
            tracks = [t for t in map(sp.wrapped_track, items) if t]
        except ApiError as e:
            if e.status not in (403, 404):
                raise
            note = ("Spotify hanya membuka daftar lagu playlist milikmu sendiri untuk aplikasi pihak ketiga. "
                    "Playlist ini tetap bisa diputar.")
        return {**meta, "typeLabel": "Playlist", "tracks": tracks, "note": note,
                "playUri": meta["uri"]}

    def _fetch_album(self, aid):
        a = self.api.get(f"/albums/{aid}") or {}
        meta = sp.album(a)
        items = list((a.get("tracks") or {}).get("items") or [])
        nxt = (a.get("tracks") or {}).get("next")
        while nxt:
            page = self.api.get(nxt) or {}
            items.extend(page.get("items") or [])
            nxt = page.get("next")
        tracks = [t for t in (sp.track(x, album=a) for x in items) if t]
        label = {"single": "Single", "compilation": "Kompilasi"}.get(meta["albumType"], "Album")
        sub = " • ".join(x for x in (meta["subtitle"], meta["year"], f"{len(tracks)} lagu") if x)
        return {**meta, "typeLabel": label, "subtitle": sub, "artistId": (a.get("artists") or [{}])[0].get("id", ""),
                "tracks": tracks, "playUri": meta["uri"]}

    def _fetch_artist(self, aid):
        a = sp.artist(self.api.get(f"/artists/{aid}") or {})
        albums = self.api.get(f"/artists/{aid}/albums", include_groups="album,single", limit=50) or {}
        # /artists/{id}/top-tracks was removed in Feb 2026; search is the closest substitute
        popular = []
        try:
            res = self.api.get("/search", q=f'artist:"{a["name"]}"', type="track", limit=10) or {}
            popular = [t for t in map(sp.track, (res.get("tracks") or {}).get("items") or [])
                       if t and t["artistId"] == aid]
        except ApiError:
            pass
        return {**a, "tracks": popular, "albums": [sp.album(x) for x in albums.get("items") or []],
                "playUri": a["uri"]}

    def _fetch_liked(self):
        items = self.api.paged("/me/tracks", limit=50)
        tracks = [t for t in map(sp.wrapped_track, items) if t]
        return {"kind": "liked", "name": "Lagu yang Disukai", "typeLabel": "Playlist",
                "subtitle": f"{len(tracks)} lagu", "tracks": tracks, "playUri": ""}

    # ---- search -----------------------------------------------------------

    @Slot(str)
    def search(self, query):
        query = query.strip()
        if not query:
            return

        def fetch():
            # the Web API caps search at 10 results per type since Feb 2026
            res = self.api.get("/search", q=query, type="track,artist,album,playlist", limit=10) or {}
            pick = lambda k: [x for x in (res.get(k) or {}).get("items") or [] if x]
            return {
                "tracks": [t for t in map(sp.track, pick("tracks")) if t],
                "artists": [sp.artist(a) for a in pick("artists")],
                "albums": [sp.album(a) for a in pick("albums")],
                "playlists": [sp.playlist(p) for p in pick("playlists")],
            }

        self.worker.run(fetch, lambda r: self.searchFinished.emit(query, r),
                        lambda e: self.searchFinished.emit(query, {"error": str(e)}))
