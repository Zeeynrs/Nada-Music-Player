import os
import signal
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from .api import SpotifyApi
from .auth import TokenStore
from .config import Settings
from .librespot import Librespot
from .library import Library
from .lyrics import Lyrics
from .player import Player
from .session import Session
from .visualizer import Visualizer
from .worker import Async

ROOT = Path(__file__).resolve().parent.parent


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "wayland;xcb")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Nada")
    app.setOrganizationName("nada")
    app.setDesktopFileName("nada")  # Wayland app_id, for Hyprland window rules
    app.setWindowIcon(QIcon(str(ROOT / "data" / "nada.svg")))
    app.setFont(QFont(["Google Sans Flex", "Google Sans", "Noto Sans", "sans-serif"], 10))
    QQuickStyle.setStyle("Basic")
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    keepalive = QTimer()  # lets Python handle Ctrl+C while Qt's loop runs
    keepalive.timeout.connect(lambda: None)
    keepalive.start(500)

    settings = Settings()
    tokens = TokenStore()
    worker = Async()
    api = SpotifyApi(tokens)
    session = Session(tokens, settings, worker)
    librespot = Librespot(settings)
    player = Player(api, worker, librespot, settings)
    library = Library(api, worker)
    lyrics = Lyrics(player, worker)
    visualizer = Visualizer()
    librespot.problem.connect(session.toast)

    def on_logged_in():
        if settings["start_librespot"]:
            librespot.start()
        library.refreshAll()
        player.start()

    session.loggedIn.connect(on_logged_in)
    session.loggedOut.connect(player.stop)

    engine = QQmlApplicationEngine()
    engine.warnings.connect(lambda ws: [print("QML:", w.toString(), file=sys.stderr) for w in ws])
    ctx = engine.rootContext()
    for name, obj in (("session", session), ("player", player), ("library", library),
                      ("lyrics", lyrics), ("visualizer", visualizer), ("librespot", librespot)):
        ctx.setContextProperty(name, obj)
    engine.load(str(ROOT / "qml" / "Main.qml"))
    if not engine.rootObjects():
        sys.exit("Nada: gagal memuat antarmuka (lihat pesan QML di atas)")

    window = engine.rootObjects()[0]
    try:
        from .mpris import Mpris
        mpris = Mpris(player, lambda: (window.show(), window.raise_(), window.requestActivate()), app.quit)
    except Exception as e:  # MPRIS is optional: no dbus-python or no session bus
        print(f"MPRIS tidak aktif: {e}", file=sys.stderr)
        mpris = None

    if tokens.has_tokens:
        on_logged_in()

    def shutdown():
        player.stop()
        visualizer.stop()
        librespot.stop()
        worker.shutdown()

    app.aboutToQuit.connect(shutdown)
    code = app.exec()
    del window, engine  # tear down QML before the Python objects it binds to
    sys.exit(code)


if __name__ == "__main__":
    main()
