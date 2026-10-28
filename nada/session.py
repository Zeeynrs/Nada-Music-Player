"""Login state and user-facing settings exposed to QML."""

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QGuiApplication

from . import auth
from .config import REDIRECT_URI


class Session(QObject):
    changed = Signal()
    loggedIn = Signal()
    loggedOut = Signal()
    toast = Signal(str)

    def __init__(self, tokens: auth.TokenStore, settings, worker, parent=None):
        super().__init__(parent)
        self.tokens = tokens
        self.settings = settings
        self.worker = worker
        self._busy = False
        self._message = ""
        worker.error.connect(self.toast)

    @Property(bool, notify=changed)
    def authenticated(self):
        return self.tokens.has_tokens

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(str, notify=changed)
    def message(self):
        return self._message

    @Property(str, constant=True)
    def redirectUri(self):
        return REDIRECT_URI

    def _set(self, busy, message):
        self._busy, self._message = busy, message
        self.changed.emit()

    @Slot(str)
    def login(self, client_id):
        client_id = client_id.strip()
        if len(client_id) != 32:
            self._set(False, "Client ID harus 32 karakter (salin dari Spotify Developer Dashboard).")
            return
        self.settings["client_id"] = client_id
        try:
            url, wait = auth.begin_login(client_id)
        except auth.AuthError as e:
            self._set(False, str(e))
            return
        self._set(True, "Menunggu login di browser…")
        QDesktopServices.openUrl(QUrl(url))

        def ok(token):
            self.tokens.save(client_id, token)
            self._set(False, "")
            self.loggedIn.emit()

        self.worker.run(wait, ok, lambda e: self._set(False, f"Gagal masuk: {e}"))

    @Slot()
    def logout(self):
        self.tokens.clear()
        self._set(False, "")
        self.loggedOut.emit()

    @Slot(str)
    def copy(self, text):
        QGuiApplication.clipboard().setText(text)
        self.toast.emit("Disalin ke clipboard")

    @Slot(str)
    def openUrl(self, url):
        QDesktopServices.openUrl(QUrl(url))

    # ---- settings ---------------------------------------------------------

    def _setting(key):
        def getter(self):
            return self.settings[key]

        def setter(self, value):
            self.settings[key] = value
            self.changed.emit()
        return getter, setter

    clientId = Property(str, *_setting("client_id"), notify=changed)
    deviceName = Property(str, *_setting("device_name"), notify=changed)
    bitrate = Property(int, *_setting("bitrate"), notify=changed)
    visualizerEnabled = Property(bool, *_setting("visualizer"), notify=changed)
    visualizerStyle = Property(str, *_setting("visualizer_style"), notify=changed)
    normalize = Property(bool, *_setting("normalize"), notify=changed)
    volumeRange = Property(int, *_setting("volume_range"), notify=changed)
    del _setting
