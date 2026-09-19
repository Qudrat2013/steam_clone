"""Steam Clone Launcher v2 — 3D игровой лаунчер (PyQt6).

Возможности:
• 3D-заставка при запуске, тёмный 3D-интерфейс с неоновыми акцентами
• МАГАЗИН — каталог игр с ценами/скидками, покупка с баланса профиля
• БИБЛИОТЕКА — купленные игры, запуск .exe, живой таймер сессии
• ЧАТ — личные сообщения между пользователями (те же модели, что на сайте)
• Автозапуск Django-сервера, время игры пишется в базу сайта
"""
import json
import math
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PyQt6.QtCore import (
    QPointF, QPropertyAnimation, Qt, QThread, QTimer, pyqtSignal,
)
from PyQt6.QtGui import (
    QColor, QFont, QImage, QPainter, QPainterPath, QPixmap, QRadialGradient,
)
from PyQt6.QtWidgets import (
    QApplication, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout,
    QWidget,
)

SERVER_URL = os.environ.get("STEAM_CLONE_URL", "http://127.0.0.1:8000").rstrip("/")
HEARTBEAT_MS = 20000
CONFIG_DIR = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "SteamCloneLauncher"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text("utf-8"))
    except Exception:
        return {}


def save_config(cfg: dict) -> None:
    """Сливает поля с уже сохранённым конфигом (не затирает остальные)."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        merged = load_config()
        merged.update(cfg or {})
        CONFIG_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=2), "utf-8")
    except Exception:
        pass


def set_server_url(url: str) -> str:
    """Меняет адрес сервера (локальный или хостинг) и запоминает его."""
    global SERVER_URL
    url = (url or "").strip().rstrip("/")
    if url and not url.startswith(("http://", "https://")):
        url = "http://" + url
    if url:
        SERVER_URL = url
    return SERVER_URL


def api_request(path, method="GET", token=None, payload=None, timeout=10):
    url = SERVER_URL + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    if token:
        req.add_header("Authorization", f"Token {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}"), resp.status
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8") or "{}"), e.code
        except Exception:
            return {"detail": str(e)}, e.code
    except Exception as e:
        return {"detail": str(e)}, 0


def fmt_hms(seconds) -> str:
    h, rem = divmod(max(0, int(seconds)), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def fmt_wait_human(minutes) -> str:
    minutes = int(minutes)
    if minutes >= 60:
        h, m = divmod(minutes, 60)
        return f"{h} \u0447." + (f" {m} \u043c\u0438\u043d." if m else "")
    return f"{minutes} \u043c\u0438\u043d."


def server_alive() -> bool:
    try:
        urllib.request.urlopen(SERVER_URL + "/", timeout=2)
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def start_server_if_needed() -> None:
    if server_alive():
        return
    manage = _base_dir() / "manage.py"
    if not manage.exists():
        return
    python = sys.executable
    if getattr(sys, "frozen", False):
        python = shutil.which("python") or shutil.which("py") or ""
        if not python:
            return
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        subprocess.Popen(
            [python, str(manage), "runserver", "127.0.0.1:8000", "--noreload"],
            cwd=str(_base_dir()), creationflags=flags,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def rounded_pixmap(source, w, h, r=10):
    pm = QPixmap(source)
    if pm.isNull():
        return pm
    scaled = pm.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                       Qt.TransformationMode.SmoothTransformation)
    x = max(0, (scaled.width() - w) // 2)
    y = max(0, (scaled.height() - h) // 2)
    scaled = scaled.copy(x, y, min(w, scaled.width()), min(h, scaled.height()))
    img = QImage(w, h, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, w, h, r, r)
    p.setClipPath(path)
    p.drawPixmap(0, 0, scaled)
    p.end()
    return QPixmap.fromImage(img)


def fetch_pixmap(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = resp.read()
        pm = QPixmap()
        pm.loadFromData(data)
        return pm
    except Exception:
        return QPixmap()

QSS = """
QWidget { background: transparent; color: #dbe7f7;
          font-family: 'Segoe UI'; font-size: 13px; }
QMainWindow, QDialog { background: #0a0f1a; }
QStackedWidget { background: transparent; }
QLabel { background: transparent; }

/* ---------------- splash ---------------- */
#splash { background: qradialgradient(cx:0.5, cy:0.38, radius:1.3,
           stop:0 #16253f, stop:0.55 #0c1526, stop:1 #060a12); }
#splashLogo { color: #eaf4ff; font-size: 52px; font-weight: 900;
              letter-spacing: 3px; }
#splashSub  { color: #3ec6ff; font-size: 15px; font-weight: 700;
              letter-spacing: 9px; }
#splashStatus { color: #8fa6c4; font-size: 13px; }
#splashBar { background: #0e1829; border: none; border-radius: 4px;
             max-height: 7px; min-height: 7px; }
#splashBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #35d0ff, stop:1 #2f7cff); border-radius: 4px; }

/* ---------------- login ---------------- */
#loginBox { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
             stop:0 #131f34, stop:1 #0d1626);
            border: 1px solid #24406b; border-radius: 18px; }
#logo { color: #eaf4ff; font-size: 34px; font-weight: 900; letter-spacing: 2px; }
#sub  { color: #3ec6ff; font-size: 13px; letter-spacing: 4px; font-weight: 700; }
#error { color: #ff6b81; font-size: 12px; }

/* ---------------- inputs ---------------- */
QLineEdit { background: #0c1422; border: 1px solid #22344f;
            border-radius: 10px; padding: 8px 14px; color: #dbe7f7;
            selection-background-color: #2f7cff; }
QLineEdit:focus { border: 1px solid #3ec6ff;
                  background: #0f1a2c; }

/* ---------------- sidebar ---------------- */
#sidebar { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
             stop:0 #0d1526, stop:1 #0a1220);
           border-right: 1px solid #1c2c48; }
#sideLogo { color: #eaf4ff; font-size: 19px; font-weight: 900; letter-spacing: 1px; }
#sideLogoSub { color: #3ec6ff; font-size: 10px; letter-spacing: 5px; font-weight: 700; }
.navBtn { text-align: left; padding: 12px 18px; border: none;
          border-left: 3px solid transparent; border-radius: 0 10px 10px 0;
          color: #93a8c6; font-size: 14px; font-weight: 700; background: transparent; }
.navBtn:hover { color: #d7e6fa; background: #101c31; }
.navBtn:checked { color: #ffffff; background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                   stop:0 #17406b, stop:1 #102038);
                   border-left: 3px solid #3ec6ff; }
#userBox { background: #0e1a2d; border: 1px solid #22344f; border-radius: 14px; }
#avatar { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 #35d0ff, stop:1 #2f7cff); border-radius: 21px;
          color: white; font-size: 20px; font-weight: 900; }
#userName { color: #eaf4ff; font-weight: 800; font-size: 14px; }
#userBalance { color: #7cffce; font-weight: 800; font-size: 13px; }
#balanceCap { color: #6f85a3; font-size: 10px; }

/* ---------------- 3D buttons ---------------- */
QPushButton { background: #16263e; border: 1px solid #2a3f60; border-radius: 10px;
              color: #c9d9ef; padding: 7px 16px; font-weight: 700; }
QPushButton:hover { border-color: #3ec6ff; color: #ffffff; }
QPushButton:pressed { padding-top: 9px; padding-bottom: 5px; }
#playBtn { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
             stop:0 #46c44b, stop:1 #2f9a35); border: none;
           border-bottom: 4px solid #1d6e22; border-radius: 10px;
           color: white; font-weight: 800; letter-spacing: 1px; }
#playBtn:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                   stop:0 #55d45a, stop:1 #3aab40); }
#playBtn:pressed { border-bottom-width: 1px; }
#buyBtn { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
             stop:0 #35d0ff, stop:1 #1f8fe0); border: none;
           border-bottom: 4px solid #0f5a94; border-radius: 12px;
           color: white; font-weight: 900; font-size: 15px; letter-spacing: 1px; }
#buyBtn:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                  stop:0 #55dcff, stop:1 #2fa2ec); }
#buyBtn:pressed { border-bottom-width: 1px; }
#buyBtn:disabled { background: #1d2f4a; border-bottom: 4px solid #14263e; color: #6f85a3; }
"""

QSS += """
/* ---------------- cards / content ---------------- */
#page { background: transparent; }
#loginWrap { background: qradialgradient(cx:0.3, cy:0.2, radius:1.5,
               stop:0 #14233c, stop:0.55 #0b1424, stop:1 #060b14); }
#pageTitle { color: #eaf4ff; font-size: 24px; font-weight: 900; letter-spacing: 1px; }
#pageSub { color: #6f85a3; font-size: 12px; }
#card { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
          stop:0 #142238, stop:1 #0e1a2d);
         border: 1px solid #22344f; border-radius: 14px; }
#card:hover { border: 1px solid #3ec6ff; }
#cardTitle { color: #eaf4ff; font-weight: 800; font-size: 14px; }
#cardMeta { color: #7d93b2; font-size: 11px; }
#cardTime { color: #3ec6ff; font-weight: 700; font-size: 12px; }
#priceTag { color: #7cffce; font-weight: 900; font-size: 15px; }
#priceOld { color: #5b7395; font-size: 12px; text-decoration: line-through; }
#discountTag { background: #2f9a35; color: white; font-weight: 900;
               border-radius: 6px; padding: 2px 8px; font-size: 12px; }
#empty { color: #6c8099; font-size: 15px; padding: 40px; background: transparent; }
#detailTitle { color: #eaf4ff; font-size: 28px; font-weight: 900; }
#detailDev { color: #3ec6ff; font-weight: 700; }
#detailDesc { color: #a9bcd6; font-size: 13px; }

/* ---------------- chat ---------------- */
#chatList { background: #0c1422; border: 1px solid #1c2c48; border-radius: 12px;
            border: none; }
QListWidget::item { color: #c9d9ef; border-radius: 8px; padding: 6px; }
QListWidget::item:selected { background: #17406b; color: white; }
#bubbleMine { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #1f5fa8, stop:1 #17456f); border-radius: 12px;
              color: #eaf4ff; padding: 8px 12px; font-size: 13px; }
#bubbleTheirs { background: #182a44; border: 1px solid #22344f; border-radius: 12px;
                color: #dbe7f7; padding: 8px 12px; font-size: 13px; }
#bubbleTime { color: #6f85a3; font-size: 10px; background: transparent; }
#chatPartner { color: #eaf4ff; font-weight: 800; font-size: 15px; }

/* ---------------- play bar ---------------- */
#playBar { background: #14233a; border-top: 2px solid #3ec6ff; }
#barLabel { color: #3ec6ff; font-weight: 700; font-size: 15px; }
#barTimer { color: #eaf4ff; font-size: 20px; font-weight: 800; font-family: Consolas; }

/* ---------------- scrollbars ---------------- */
QScrollArea, #scroll { border: none; background: transparent; }
QScrollBar:vertical { background: #0b1220; width: 10px; }
QScrollBar::handle:vertical { background: #2b3d5c; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QScrollBar:horizontal { background: #0b1220; height: 10px; }
QScrollBar::handle:horizontal { background: #2b3d5c; border-radius: 5px; }
#stopBtn { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
            stop:0 #e05548, stop:1 #b93a30); border: none;
          border-bottom: 4px solid #7d2620; border-radius: 10px;
          color: white; font-weight: 800; padding: 0 18px; }
#stopBtn:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                  stop:0 #ef6a5c, stop:1 #cc4a3f); }
#stopBtn:pressed { border-bottom-width: 1px; }
#installBtn { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #3d6ea8, stop:1 #2c5484); border: none;
              border-bottom: 4px solid #1a3557; border-radius: 10px;
              color: #d6e8ff; font-weight: 800; }
#installBtn:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                      stop:0 #4a80bf, stop:1 #356298); }
#installBtn:pressed { border-bottom-width: 1px; }
QMessageBox { background: #0e1626; }
QMessageBox QLabel { color: #dbe7f7; font-size: 13px; background: transparent; }
QMessageBox QPushButton { min-width: 90px; min-height: 30px; }
QProgressBar { border: none; background: transparent; }
#bonusBtn { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
              stop:0 #f5b93e, stop:1 #c8871a); border: none;
            border-bottom: 4px solid #8a5a0d; border-radius: 10px;
            color: #2b1c00; font-weight: 900; letter-spacing: 1px; }
#bonusBtn:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #ffc954, stop:1 #d99a26); }
#bonusBtn:pressed { border-bottom-width: 1px; }
#toastOk { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
             stop:0 #1d8a55, stop:1 #13603d); border: 1px solid #3fd492;
           border-radius: 22px; color: #eafff5; font-weight: 800;
           padding: 0 22px; }
#toastWarn { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
               stop:0 #b94a3e, stop:1 #8a352c); border: 1px solid #ff8d80;
             border-radius: 22px; color: #fff1ee; font-weight: 800;
             padding: 0 22px; }
#sideCap { color: #5f7595; font-size: 10px; letter-spacing: 3px; font-weight: 700; }
#tabBtn { background: #0e1a2d; border: 1px solid #22344f; border-radius: 10px;
          color: #8fa6c4; font-weight: 800; font-size: 12px; }
#tabBtn:hover { color: #d7e6fa; border-color: #3ec6ff; }
#tabBtn:checked { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #1a4a7a, stop:1 #14324f); border-color: #3ec6ff;
                  color: white; }
#qrTimer { color: #3ec6ff; font-weight: 800; font-size: 14px; font-family: Consolas; }
#qrUrl { color: #8fa6c4; font-size: 11px; font-family: Consolas; }
#achCard { background: #101c31; border: 1px solid #22344f; border-radius: 12px; }
#achName { color: #ffd76b; font-weight: 800; }
#achDesc { color: #8fa6c4; font-size: 11px; }
#profRow { color: #c9d9ef; font-size: 14px; }
#profRow b, #profVal { color: #7cffce; font-weight: 900; font-size: 16px; }
"""


# --------------------------------------------------------------- loaders
class CoverLoader(QThread):
    loaded = pyqtSignal(int, QPixmap)

    def __init__(self, game_id, url):
        super().__init__()
        self.game_id, self.url = game_id, url

    def run(self):
        if self.url:
            pm = fetch_pixmap(self.url)
            if not pm.isNull():
                self.loaded.emit(self.game_id, pm)


class GameWatcher(QThread):
    finished_game = pyqtSignal(int)

    def __init__(self, process, game_id):
        super().__init__()
        self.process, self.game_id = process, game_id
        self._stop = False

    def run(self):
        while not self._stop and self.process.poll() is None:
            time.sleep(1)
        if not self._stop:
            self.finished_game.emit(self.game_id)

    def stop(self):
        self._stop = True


# --------------------------------------------------------------- splash
class SplashWidget(QWidget):
    done = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("splash")
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(10)

        logo = QLabel("STEAM CLONE")
        logo.setObjectName("splashLogo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        eff = QGraphicsDropShadowEffect(logo)
        eff.setBlurRadius(38)
        eff.setColor(QColor(62, 198, 255, 200))
        eff.setOffset(0, 4)
        logo.setGraphicsEffect(eff)
        lay.addWidget(logo)

        sub = QLabel("L A U N C H E R")
        sub.setObjectName("splashSub")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)
        lay.addSpacing(26)

        self.bar = QProgressBar()
        self.bar.setObjectName("splashBar")
        self.bar.setFixedWidth(300)
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        lay.addWidget(self.bar, alignment=Qt.AlignmentFlag.AlignCenter)

        self.status = QLabel("запуск...")
        self.status.setObjectName("splashStatus")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.status)

        self._val = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._anim)
        self.timer.start(28)

    def _anim(self):
        self._val = min(100, self._val + 2)
        self.bar.setValue(self._val)
        if self._val == 62:
            self.status.setText("загрузка библиотеки...")
        elif self._val == 100:
            self.timer.stop()
            QTimer.singleShot(220, self.done.emit)


# --------------------------------------------------------------- login
class QRPoller(QThread):
    approved = pyqtSignal(str, str)
    expired = pyqtSignal()

    def __init__(self, code):
        super().__init__()
        self.code = code
        self._stop = False

    def run(self):
        deadline = time.time() + 185
        while time.time() < deadline and not self._stop:
            data, status = api_request(
                "/launcher-api/client/qr/status/?code=" + urllib.parse.quote(self.code),
                timeout=6)
            if status == 200 and data.get("approved"):
                self.approved.emit(data.get("token", ""), data.get("username", ""))
                return
            if status == 404:
                self.expired.emit()
                return
            time.sleep(2)
        if not self._stop:
            self.expired.emit()

    def stop(self):
        self._stop = True


class LoginPage(QWidget):
    logged_in = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setObjectName("loginWrap")
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        box = QFrame()
        box.setObjectName("loginBox")
        box.setFixedWidth(470)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(34, 30, 34, 30)
        lay.setSpacing(10)

        logo = QLabel("STEAM CLONE")
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        glow = QGraphicsDropShadowEffect(logo)
        glow.setBlurRadius(30)
        glow.setColor(QColor(62, 198, 255, 190))
        glow.setOffset(0, 3)
        logo.setGraphicsEffect(glow)
        lay.addWidget(logo)

        sub = QLabel("\u0412\u0425\u041e\u0414 \u0412 \u041b\u0410\u0423\u041d\u0427\u0415\u0420")
        sub.setObjectName("sub")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)
        lay.addSpacing(6)

        tabs = QHBoxLayout()
        self.tab_login = QPushButton("\u0412\u0425\u041e\u0414")
        self.tab_reg = QPushButton("\u0420\u0415\u0413\u0418\u0421\u0422\u0420\u0410\u0426\u0418\u042f")
        self.tab_qr = QPushButton("QR-\u041a\u041e\u0414")
        self._tabs = (self.tab_login, self.tab_reg, self.tab_qr)
        for t in self._tabs:
            t.setObjectName("tabBtn")
            t.setCheckable(True)
            t.setFixedHeight(40)
            t.setCursor(Qt.CursorShape.PointingHandCursor)
            tabs.addWidget(t)
        self.tab_login.setChecked(True)
        self.tab_login.clicked.connect(lambda: self._switch_tab(0))
        self.tab_reg.clicked.connect(lambda: self._switch_tab(1))
        self.tab_qr.clicked.connect(lambda: self._switch_tab(2))
        lay.addLayout(tabs)

        self.stack = QStackedWidget()
        lay.addWidget(self.stack)

        # --- page 0: login ---
        pg = QWidget()
        v = QVBoxLayout(pg)
        v.setContentsMargins(0, 6, 0, 0)
        v.setSpacing(10)
        self.username = QLineEdit()
        self.username.setPlaceholderText("\u0418\u043c\u044f \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f")
        self.username.setFixedHeight(46)
        v.addWidget(self.username)
        self.password = QLineEdit()
        self.password.setPlaceholderText("\u041f\u0430\u0440\u043e\u043b\u044c")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setFixedHeight(46)
        v.addWidget(self.password)
        self.error = QLabel("")
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        v.addWidget(self.error)
        self.btn = QPushButton("\u0412\u041e\u0419\u0422\u0418")
        self.btn.setObjectName("playBtn")
        self.btn.setFixedHeight(48)
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.clicked.connect(self.do_login)
        v.addWidget(self.btn)
        self.stack.addWidget(pg)

        # --- page 1: register ---
        pg2 = QWidget()
        v2 = QVBoxLayout(pg2)
        v2.setContentsMargins(0, 6, 0, 0)
        v2.setSpacing(9)
        self.r_username = QLineEdit()
        self.r_username.setPlaceholderText("\u041f\u0440\u0438\u0434\u0443\u043c\u0430\u0439 \u043b\u043e\u0433\u0438\u043d (lat/\u0446\u0438\u0444\u0440\u044b/_)")
        self.r_username.setFixedHeight(44)
        v2.addWidget(self.r_username)
        self.r_email = QLineEdit()
        self.r_email.setPlaceholderText("Email (\u043d\u0435\u043e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u044c\u043d\u043e)")
        self.r_email.setFixedHeight(44)
        v2.addWidget(self.r_email)
        self.r_password = QLineEdit()
        self.r_password.setPlaceholderText("\u041f\u0430\u0440\u043e\u043b\u044c (\u043c\u0438\u043d. 6 \u0441\u0438\u043c\u0432\u043e\u043b\u043e\u0432)")
        self.r_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.r_password.setFixedHeight(44)
        v2.addWidget(self.r_password)
        self.r_password2 = QLineEdit()
        self.r_password2.setPlaceholderText("\u041f\u043e\u0432\u0442\u043e\u0440\u0438 \u043f\u0430\u0440\u043e\u043b\u044c")
        self.r_password2.setEchoMode(QLineEdit.EchoMode.Password)
        self.r_password2.setFixedHeight(44)
        v2.addWidget(self.r_password2)
        self.r_error = QLabel("")
        self.r_error.setObjectName("error")
        self.r_error.setWordWrap(True)
        v2.addWidget(self.r_error)
        self.r_btn = QPushButton("\u0421\u041e\u0417\u0414\u0410\u0422\u042c \u0410\u041a\u041a\u0410\u0423\u041d\u0422")
        self.r_btn.setObjectName("buyBtn")
        self.r_btn.setFixedHeight(48)
        self.r_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.r_btn.clicked.connect(self.do_register)
        v2.addWidget(self.r_btn)
        self.stack.addWidget(pg2)

        # --- page 2: QR ---
        pg3 = QWidget()
        v3 = QVBoxLayout(pg3)
        v3.setContentsMargins(0, 6, 0, 0)
        v3.setSpacing(8)
        self.qr_label = QLabel("\u25a6")
        self.qr_label.setFixedSize(240, 240)
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setStyleSheet("background:#f4f8ff; border-radius:10px; color:#2b3d5c; font-size:44px;")
        v3.addWidget(self.qr_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.qr_timer_label = QLabel("")
        self.qr_timer_label.setObjectName("qrTimer")
        self.qr_timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v3.addWidget(self.qr_timer_label)
        self.qr_status = QLabel("")
        self.qr_status.setObjectName("pageSub")
        self.qr_status.setWordWrap(True)
        self.qr_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_status.setText("\u041e\u0442\u043a\u0440\u043e\u0439 \u0441\u0430\u0439\u0442 \u0441 \u0442\u0435\u043b\u0435\u0444\u043e\u043d\u0430, \u0437\u0430\u0441\u043a\u0430\u043d\u0438\u0440\u0443\u0439 QR \u043a\u0430\u043c\u0435\u0440\u043e\u0439 \u0438\u043b\u0438\n\u0432\u0432\u0435\u0434\u0438 \u0441\u0441\u044b\u043b\u043a\u0443 \u0432 \u0431\u0440\u0430\u0443\u0437\u0435\u0440 \u2014 \u0438 \u043d\u0430\u0436\u043c\u0438 \u041f\u041e\u0414\u0422\u0412\u0415\u0420\u0414\u0418\u0422\u042c")
        v3.addWidget(self.qr_status)
        self.qr_url_label = QLabel("")
        self.qr_url_label.setObjectName("qrUrl")
        self.qr_url_label.setWordWrap(True)
        self.qr_url_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_url_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v3.addWidget(self.qr_url_label)
        self.qr_btn = QPushButton("\u21bb  \u041e\u0411\u041d\u041e\u0412\u0418\u0422\u042c QR")
        self.qr_btn.setObjectName("buyBtn")
        self.qr_btn.setFixedHeight(44)
        self.qr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.qr_btn.clicked.connect(self.start_qr)
        v3.addWidget(self.qr_btn)
        self.stack.addWidget(pg3)

        self.qr_code = None
        self.qr_deadline = 0
        self.poller = None
        self.qr_count_timer = QTimer(self)
        self.qr_count_timer.timeout.connect(self._qr_countdown)

        self.password.returnPressed.connect(self.do_login)
        self.username.returnPressed.connect(self.password.setFocus)
        outer.addWidget(box)

    def _switch_tab(self, idx):
        for i, t in enumerate(self._tabs):
            t.setChecked(i == idx)
        self.stack.setCurrentIndex(idx)
        if idx == 2:
            self.start_qr()
        else:
            self.stop_qr()

    def stop_qr(self):
        if self.poller:
            self.poller.stop()
            self.poller = None
        self.qr_count_timer.stop()

    def start_qr(self):
        if getattr(self, "_cd_left", 0) > 0:
            return
        self.stop_qr()
        data, status = api_request("/launcher-api/client/qr/create/", "POST", timeout=8)
        if status == 429:
            wait = int(data.get("retry_after") or 15)
            if data.get("detail") == "banned":
                mins = (wait + 59) // 60
                self.qr_status.setText("\u26d4 \u0421\u043b\u0438\u0448\u043a\u043e\u043c \u043c\u043d\u043e\u0433\u043e \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0439! \u041f\u043e\u0432\u0442\u043e\u0440\u0438 \u0447\u0435\u0440\u0435\u0437 " + fmt_wait_human(mins))
            else:
                self.qr_status.setText(f"\u0421\u043b\u0438\u0448\u043a\u043e\u043c \u0447\u0430\u0441\u0442\u043e! \u041f\u043e\u0434\u043e\u0436\u0434\u0438 {wait} \u0441\u0435\u043a.")
            self._qr_cooldown(wait)
            return
        if status != 200 or not data.get("code"):
            self.qr_status.setText("\u0421\u0435\u0440\u0432\u0435\u0440 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d \u2014 \u043d\u0430\u0436\u043c\u0438 \u041e\u0411\u041d\u041e\u0412\u0418\u0422\u042c")
            return
        self.qr_code = data["code"]
        self.qr_deadline = time.time() + int(data.get("ttl", 180))
        self.qr_url_label.setText(data.get("full_url") or (SERVER_URL + data.get("approve_url", "")))
        nb = int(data.get("next_ban_minutes") or 0)
        if nb:
            self.qr_status.setText("\u26a0\ufe0f \u042d\u0442\u043e \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0439 QR \u043d\u0430 \u0441\u0435\u0439\u0447\u0430\u0441! \u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u2014 \u0447\u0435\u0440\u0435\u0437 " + fmt_wait_human(nb))
        pm = fetch_pixmap(SERVER_URL + "/launcher-api/client/qr/img/?code=" + self.qr_code)
        if not pm.isNull():
            self.qr_label.setPixmap(rounded_pixmap(pm, 240, 240, 10))
        self.qr_timer_label.setText("")
        self.qr_count_timer.start(1000)
        self.poller = QRPoller(self.qr_code)
        self.poller.approved.connect(self._qr_approved)
        self.poller.expired.connect(self._qr_expired)
        self.poller.start()
        self._qr_cooldown(15)

    def _qr_cooldown(self, seconds):
        self.qr_btn.setEnabled(False)
        self._cd_left = int(seconds)
        self._cd_step = 30 if seconds > 90 else 1
        if not hasattr(self, "_cd_timer"):
            self._cd_timer = QTimer(self)
            self._cd_timer.timeout.connect(self._cd_tick)
        self._cd_timer.start(self._cd_step * 1000)
        self._cd_tick()

    def _cd_tick(self):
        self._cd_left = max(0, self._cd_left - self._cd_step)
        if self._cd_left <= 0:
            self._cd_timer.stop()
            self.qr_btn.setEnabled(True)
            self.qr_btn.setText("\u21bb  \u041e\u0411\u041d\u041e\u0412\u0418\u0422\u042c QR")
        elif self._cd_left > 90:
            self.qr_btn.setText("\u26d4 \u0416\u0414\u0418 (" + fmt_wait_human((self._cd_left + 59) // 60) + ")")
        else:
            self.qr_btn.setText(f"\u23f3 \u041f\u041e\u0414\u041e\u0416\u0414\u0418 ({self._cd_left})")

    def _qr_countdown(self):
        rem = int(self.qr_deadline - time.time())
        if rem <= 0:
            return
        m, s = divmod(rem, 60)
        self.qr_timer_label.setText(f"\u23f1 \u043a\u043e\u0434 \u0434\u0435\u0439\u0441\u0442\u0432\u0443\u0435\u0442: {m:02d}:{s:02d}")

    def _qr_approved(self, token, username):
        self.stop_qr()
        save_config({"token": token, "username": username})
        self.logged_in.emit(token, username)

    def _qr_expired(self):
        self.qr_label.setPixmap(QPixmap())
        self.qr_label.setText("\u23f1")
        self.qr_timer_label.setText("")
        self.qr_status.setText("QR-\u043a\u043e\u0434 \u0438\u0441\u0442\u0435\u043a. \u041d\u0430\u0436\u043c\u0438 \u041e\u0411\u041d\u041e\u0412\u0418\u0422\u042c QR")

    def do_login(self):
        user, pwd = self.username.text().strip(), self.password.text()
        if not user or not pwd:
            self.error.setText("\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u043b\u043e\u0433\u0438\u043d \u0438 \u043f\u0430\u0440\u043e\u043b\u044c")
            return
        self.btn.setEnabled(False)
        self.btn.setText("\u041f\u041e\u0414\u041a\u041b\u042e\u0427\u0415\u041d\u0418\u0415...")
        QApplication.processEvents()
        start_server_if_needed()
        data, status = api_request("/api/auth/login/", "POST",
                                   payload={"username": user, "password": pwd})
        self.btn.setEnabled(True)
        self.btn.setText("\u0412\u041e\u0419\u0422\u0418")
        if status == 200 and data.get("token"):
            save_config({"token": data["token"], "username": data.get("username", user)})
            self.logged_in.emit(data["token"], data.get("username", user))
        elif status == 0:
            self.error.setText("\u0421\u0435\u0440\u0432\u0435\u0440 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d. \u0417\u0430\u043f\u0443\u0441\u0442\u0438 Django: python manage.py runserver")
        else:
            self.error.setText(data.get("detail") or "\u041d\u0435\u0432\u0435\u0440\u043d\u044b\u0439 \u043b\u043e\u0433\u0438\u043d \u0438\u043b\u0438 \u043f\u0430\u0440\u043e\u043b\u044c")

    def do_register(self):
        u = self.r_username.text().strip()
        e = self.r_email.text().strip()
        p1 = self.r_password.text()
        p2 = self.r_password2.text()
        if not u or not p1:
            self.r_error.setText("\u0417\u0430\u043f\u043e\u043b\u043d\u0438 \u043b\u043e\u0433\u0438\u043d \u0438 \u043f\u0430\u0440\u043e\u043b\u044c")
            return
        if p1 != p2:
            self.r_error.setText("\u041f\u0430\u0440\u043e\u043b\u0438 \u043d\u0435 \u0441\u043e\u0432\u043f\u0430\u0434\u0430\u044e\u0442")
            return
        self.r_btn.setEnabled(False)
        self.r_btn.setText("\u0421\u041e\u0417\u0414\u0410\u0415\u041c...")
        QApplication.processEvents()
        start_server_if_needed()
        data, status = api_request("/launcher-api/client/register/", "POST",
                                   payload={"username": u, "password": p1, "email": e})
        self.r_btn.setEnabled(True)
        self.r_btn.setText("\u0421\u041e\u0417\u0414\u0410\u0422\u042c \u0410\u041a\u041a\u0410\u0423\u041d\u0422")
        if status == 200 and data.get("token"):
            save_config({"token": data["token"], "username": data.get("username", u)})
            self.logged_in.emit(data["token"], data.get("username", u))
        elif status == 0:
            self.r_error.setText("\u0421\u0435\u0440\u0432\u0435\u0440 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d")
        else:
            self.r_error.setText(data.get("detail") or "\u041e\u0448\u0438\u0431\u043a\u0430 \u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0430\u0446\u0438\u0438")


# ------------------------------------------------------- game card widget
class GameCard(QFrame):
    clicked = pyqtSignal(dict)
    play_clicked = pyqtSignal(dict)

    def __init__(self, game, store_mode=False):
        super().__init__()
        self.game = game
        self.setObjectName("card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(232, 260)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        self.cover = QLabel("\u25a6")
        self.cover.setFixedSize(208, 108)
        self.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover.setStyleSheet("background:#0c1422; border-radius:8px; color:#2b3d5c; font-size:30px;")
        lay.addWidget(self.cover)

        self.title = QLabel(game["title"])
        self.title.setObjectName("cardTitle")
        self.title.setWordWrap(True)
        lay.addWidget(self.title)

        if store_mode:
            row = QHBoxLayout()
            if int(game.get("discount") or 0) > 0:
                d = QLabel(f"-{game['discount']}%")
                d.setObjectName("discountTag")
                row.addWidget(d)
                old = QLabel(game["price"] + " UZS")
                old.setObjectName("priceOld")
                row.addWidget(old)
            price = QLabel(game["final_price"] + " UZS")
            price.setObjectName("priceTag")
            row.addWidget(price)
            row.addStretch(1)
            lay.addLayout(row)
            btn = QPushButton("\u041f\u041e\u0414\u0420\u041e\u0411\u041d\u0415\u0415")
            btn.setObjectName("buyBtn" if not game.get("owned") else "playBtn")
            btn.setFixedHeight(34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda: self.play_clicked.emit(self.game))
            lay.addWidget(btn)
        else:
            self.time_label = QLabel(f"\u23f1  {game.get('playtime_display', '0 \u0447.')}  \u00b7  {game.get('sessions', 0)} \u0437\u0430\u043f\u0443\u0441\u043a\u043e\u0432")
            self.time_label.setObjectName("cardTime")
            lay.addWidget(self.time_label)
            lay.addStretch(1)
            self.btn = QPushButton()
            self.btn.setFixedHeight(38)
            self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn.clicked.connect(lambda: self.play_clicked.emit(self.game))
            lay.addWidget(self.btn)
            self.set_playing(bool(game.get("is_playing")))

        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(0)
        glow.setColor(QColor(62, 198, 255, 150))
        self.setGraphicsEffect(glow)
        self._glow = glow
        self.mousePressEvent = lambda e: self.clicked.emit(self.game)

    def enterEvent(self, event):
        self._glow.setBlurRadius(30)
        self._glow.setOffset(0, 7)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._glow.setBlurRadius(0)
        super().leaveEvent(event)

    def set_cover(self, pm):
        self.cover.setPixmap(rounded_pixmap(pm, 208, 108, 8))

    def set_playing(self, playing):
        if not self.game.get("installed"):
            self.btn.setText("\u2935  \u0423\u0421\u0422\u0410\u041d\u041e\u0412\u0418\u0422\u042c")
            self.btn.setObjectName("installBtn")
        else:
            self.btn.setText("\u25a0  \u041e\u0421\u0422\u0410\u041d\u041e\u0412\u0418\u0422\u042c" if playing else "\u25b6  \u0418\u0413\u0420\u0410\u0422\u042c")
            self.btn.setObjectName("stopBtn" if playing else "playBtn")
        self.btn.style().unpolish(self.btn)
        self.btn.style().polish(self.btn)

    def update_time(self, display, sessions):
        self.game["playtime_display"] = display
        self.time_label.setText(f"\u23f1  {display}  \u00b7  {sessions} \u0437\u0430\u043f\u0443\u0441\u043a\u043e\u0432")


# ------------------------------------------------------------- main page
class MainPage(QWidget):
    logout_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.token = None
        self.username = ""
        self.process = None
        self.watcher = None
        self.session_id = None
        self.current_game = None
        self.started_at = 0.0
        self.cards = {}
        self.store_cards = {}
        self.loaders = []

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- sidebar ----
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(240)
        s = QVBoxLayout(side)
        s.setContentsMargins(18, 22, 18, 18)
        s.setSpacing(4)

        logo = QLabel("STEAM CLONE")
        logo.setObjectName("sideLogo")
        s.addWidget(logo)
        sub = QLabel("LAUNCHER")
        sub.setObjectName("sideLogoSub")
        s.addWidget(sub)
        s.addSpacing(18)

        self.btn_lib = QPushButton("\U0001f3ae  \u0411\u0418\u0411\u041b\u0418\u041e\u0422\u0415\u041a\u0410")
        self.btn_store = QPushButton("\U0001f6d2  \u041c\u0410\u0413\u0410\u0417\u0418\u041d")
        self.btn_chat = QPushButton("\U0001f4ac  \u0427\u0410\u0422")
        self.btn_prof = QPushButton("\U0001f464  \u041f\u0420\u041e\u0424\u0418\u041b\u042c")
        for i, b in enumerate((self.btn_lib, self.btn_store, self.btn_chat, self.btn_prof)):
            b.setCheckable(True)
            b.setProperty("class", "navBtn")
            b.setObjectName(f"nav{i}")
            b.setStyleSheet("")
            b.setFixedHeight(46)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            s.addWidget(b)
        self.btn_lib.setObjectName("navBtn")
        self.btn_store.setObjectName("navBtn")
        self.btn_chat.setObjectName("navBtn")
        self.btn_prof.setObjectName("navBtn")
        for b in (self.btn_lib, self.btn_store, self.btn_chat, self.btn_prof):
            b.style().unpolish(b)
            b.style().polish(b)
        self.btn_lib.setChecked(True)
        self.btn_lib.clicked.connect(lambda: self.switch_page("lib"))
        self.btn_store.clicked.connect(lambda: self.switch_page("store"))
        self.btn_chat.clicked.connect(lambda: self.switch_page("chat"))
        self.btn_prof.clicked.connect(lambda: self.switch_page("prof"))
        s.addStretch(1)

        self.userBox = QFrame()
        self.userBox.setObjectName("userBox")
        ub = QHBoxLayout(self.userBox)
        ub.setContentsMargins(12, 10, 12, 10)
        self.avatar = QLabel("S")
        self.avatar.setObjectName("avatar")
        self.avatar.setFixedSize(42, 42)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ub.addWidget(self.avatar)
        uc = QVBoxLayout()
        uc.setSpacing(0)
        self.user_label = QLabel("")
        self.user_label.setObjectName("userName")
        uc.addWidget(self.user_label)
        self.balance_label = QLabel("")
        self.balance_label.setObjectName("userBalance")
        uc.addWidget(self.balance_label)
        ub.addLayout(uc)
        ub.addStretch(1)
        s.addWidget(self.userBox)

        logout = QPushButton("\u0412\u042b\u0419\u0422\u0418")
        logout.setFixedHeight(36)
        logout.setCursor(Qt.CursorShape.PointingHandCursor)
        logout.clicked.connect(self.logout_requested.emit)
        s.addWidget(logout)
        root.addWidget(side)

        # ---- pages stack: 0 lib, 1 store, 2 chat, 3 detail ----
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.lib_page = self._make_lib_page()
        self.store_page = self._make_store_page()
        self.chat_page = self._make_chat_page()
        self.detail_page = self._make_detail_page()
        self.prof_page = self._make_prof_page()
        for w in (self.lib_page, self.store_page, self.chat_page, self.detail_page, self.prof_page):
            self.stack.addWidget(w)

        # ---- play bar (overlay on lib page) ----
        self.bar = QFrame()
        self.bar.setObjectName("playBar")
        self.bar.setFixedHeight(62)
        self.bar.hide()
        b = QHBoxLayout(self.bar)
        b.setContentsMargins(22, 0, 22, 0)
        self.bar_label = QLabel("")
        self.bar_label.setObjectName("barLabel")
        b.addWidget(self.bar_label)
        b.addStretch(1)
        self.bar_timer_label = QLabel("00:00:00")
        self.bar_timer_label.setObjectName("barTimer")
        tglow = QGraphicsDropShadowEffect(self.bar_timer_label)
        tglow.setBlurRadius(22)
        tglow.setColor(QColor(62, 198, 255, 190))
        tglow.setOffset(0, 2)
        self.bar_timer_label.setGraphicsEffect(tglow)
        b.addWidget(self.bar_timer_label)
        stop = QPushButton("\u041e\u0421\u0422\u0410\u041d\u041e\u0412\u0418\u0422\u042c")
        stop.setObjectName("stopBtn")
        stop.setFixedHeight(38)
        stop.setCursor(Qt.CursorShape.PointingHandCursor)
        stop.clicked.connect(self.stop_game)
        b.addSpacing(14)
        b.addWidget(stop)
        root.addWidget(self.bar)

        self.tick = QTimer(self)
        self.tick.timeout.connect(self._tick)
        self.beat = QTimer(self)
        self.beat.timeout.connect(self._heartbeat)
        self.chat_timer = QTimer(self)
        self.chat_timer.timeout.connect(self._chat_poll)
        self.chat_timer.start(6000)

        rnd = random.Random(7)
        self._orbs = []
        for i in range(5):
            self._orbs.append({
                'x': rnd.random(), 'y': rnd.random(),
                'r': 150 + rnd.random() * 180,
                'sx': (0.02 + rnd.random() * 0.05) * (1 if rnd.random() > 0.5 else -1),
                'sy': (0.015 + rnd.random() * 0.035) * (1 if rnd.random() > 0.5 else -1),
                'hue': [200, 260, 190, 280, 170][i],
                'a': 0.05 + rnd.random() * 0.06,
            })
        self._orb_timer = QTimer(self)
        self._orb_timer.timeout.connect(self._move_orbs)
        self._orb_timer.start(55)

    # ---------------- pages ----------------
    def _make_lib_page(self):
        w = QWidget()
        w.setObjectName("page")
        v = QVBoxLayout(w)
        v.setContentsMargins(28, 20, 28, 12)
        v.setSpacing(10)
        t = QLabel("\u041c\u041e\u042f \u0411\u0418\u0411\u041b\u0418\u041e\u0422\u0415\u041a\u0410")
        t.setObjectName("pageTitle")
        v.addWidget(t)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 8, 0, 8)
        self.grid.setSpacing(18)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.scroll.setWidget(self.grid_host)
        v.addWidget(self.scroll, 1)
        return w

    def _make_store_page(self):
        w = QWidget()
        w.setObjectName("page")
        v = QVBoxLayout(w)
        v.setContentsMargins(28, 20, 28, 12)
        v.setSpacing(10)
        head = QHBoxLayout()
        t = QLabel("\u041c\u0410\u0413\u0410\u0417\u0418\u041d")
        t.setObjectName("pageTitle")
        head.addWidget(t)
        head.addStretch(1)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("\U0001f50d \u041f\u043e\u0438\u0441\u043a \u0438\u0433\u0440...")
        self.search_box.setFixedWidth(260)
        self.search_box.setFixedHeight(40)
        self.search_box.textChanged.connect(self._filter_store)
        head.addWidget(self.search_box)
        self.bonus_btn = QPushButton("\U0001f381 \u0411\u041e\u041d\u0423\u0421")
        self.bonus_btn.setObjectName("bonusBtn")
        self.bonus_btn.setFixedSize(120, 40)
        self.bonus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bonus_btn.clicked.connect(self.claim_bonus)
        head.addWidget(self.bonus_btn)
        v.addLayout(head)
        self.store_scroll = QScrollArea()
        self.store_scroll.setWidgetResizable(True)
        self.store_host = QWidget()
        self.store_grid = QGridLayout(self.store_host)
        self.store_grid.setContentsMargins(0, 8, 0, 8)
        self.store_grid.setSpacing(18)
        self.store_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.store_scroll.setWidget(self.store_host)
        v.addWidget(self.store_scroll, 1)
        return w

    def _make_chat_page(self):
        w = QWidget()
        w.setObjectName("page")
        v = QVBoxLayout(w)
        v.setContentsMargins(28, 20, 28, 16)
        v.setSpacing(10)
        t = QLabel("\u0427\u0410\u0422")
        t.setObjectName("pageTitle")
        v.addWidget(t)

        split = QHBoxLayout()
        split.setSpacing(14)
        leftcol = QVBoxLayout()
        cap1 = QLabel("\u0414\u0418\u0410\u041b\u041e\u0413\u0418")
        cap1.setObjectName("sideCap")
        leftcol.addWidget(cap1)
        self.dialog_list = QListWidget()
        self.dialog_list.setObjectName("chatList")
        self.dialog_list.setFixedWidth(250)
        self.dialog_list.itemClicked.connect(self._open_dialog)
        leftcol.addWidget(self.dialog_list, 1)
        cap2 = QLabel("\u0418\u0413\u0420\u041e\u041a\u0418")
        cap2.setObjectName("sideCap")
        leftcol.addWidget(cap2)
        self.users_list = QListWidget()
        self.users_list.setObjectName("chatList")
        self.users_list.setFixedWidth(250)
        self.users_list.itemClicked.connect(self._open_dialog)
        leftcol.addWidget(self.users_list, 1)
        split.addLayout(leftcol)

        right = QVBoxLayout()
        self.chat_partner_label = QLabel("\u0412\u044b\u0431\u0435\u0440\u0438 \u0434\u0438\u0430\u043b\u043e\u0433")
        self.chat_partner_label.setObjectName("chatPartner")
        right.addWidget(self.chat_partner_label)
        self.msg_scroll = QScrollArea()
        self.msg_scroll.setWidgetResizable(True)
        self.msg_host = QWidget()
        self.msg_lay = QVBoxLayout(self.msg_host)
        self.msg_lay.setContentsMargins(6, 6, 6, 6)
        self.msg_lay.setSpacing(8)
        self.msg_lay.addStretch(1)
        self.msg_scroll.setWidget(self.msg_host)
        right.addWidget(self.msg_scroll, 1)

        row = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435...")
        self.chat_input.setFixedHeight(44)
        self.chat_input.returnPressed.connect(self._send_msg)
        row.addWidget(self.chat_input, 1)
        send = QPushButton("\u041e\u0422\u041f\u0420\u0410\u0412\u0418\u0422\u042c")
        send.setObjectName("buyBtn")
        send.setFixedHeight(44)
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.clicked.connect(self._send_msg)
        row.addWidget(send)
        right.addLayout(row)
        split.addLayout(right, 1)
        v.addLayout(split, 1)
        return w

    def _make_prof_page(self):
        w = QWidget()
        w.setObjectName("page")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(32, 22, 32, 16)
        outer.setSpacing(14)

        t = QLabel("\u041f\u0420\u041e\u0424\u0418\u041b\u042c")
        t.setObjectName("pageTitle")
        outer.addWidget(t)

        top = QHBoxLayout()
        top.setSpacing(18)
        self.prof_avatar = QLabel("S")
        self.prof_avatar.setObjectName("avatar")
        self.prof_avatar.setFixedSize(92, 92)
        self.prof_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prof_avatar.setStyleSheet("font-size:40px; border-radius:46px; background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #35d0ff, stop:1 #2f7cff);")
        top.addWidget(self.prof_avatar)

        info = QVBoxLayout()
        info.setSpacing(4)
        self.prof_name = QLabel("")
        self.prof_name.setObjectName("detailTitle")
        info.addWidget(self.prof_name)
        self.prof_status = QLabel("")
        self.prof_status.setObjectName("detailDev")
        info.addWidget(self.prof_status)
        lvlrow = QHBoxLayout()
        self.prof_lvl = QLabel("")
        self.prof_lvl.setObjectName("profRow")
        lvlrow.addWidget(self.prof_lvl)
        lvlrow.addSpacing(14)
        self.prof_points = QLabel("")
        self.prof_points.setObjectName("profRow")
        lvlrow.addWidget(self.prof_points)
        lvlrow.addStretch(1)
        info.addLayout(lvlrow)
        top.addLayout(info, 1)
        outer.addLayout(top)

        stats = QHBoxLayout()
        stats.setSpacing(14)
        self.stat_balance = QLabel("")
        self.stat_balance.setObjectName("profRow")
        self.stat_games = QLabel("")
        self.stat_games.setObjectName("profRow")
        self.stat_streak = QLabel("")
        self.stat_streak.setObjectName("profRow")
        for s_ in (self.stat_balance, self.stat_games, self.stat_streak):
            s_.setStyleSheet("background:#101c31; border:1px solid #22344f; border-radius:12px; padding:12px 18px;")
            stats.addWidget(s_)
        stats.addStretch(1)
        outer.addLayout(stats)

        ah = QLabel("\u0414\u041e\u0421\u0422\u0418\u0416\u0415\u041d\u0418\u042f")
        ah.setObjectName("sideCap")
        outer.addWidget(ah)
        asc = QScrollArea()
        asc.setWidgetResizable(True)
        ahost = QWidget()
        self.ach_lay = QVBoxLayout(ahost)
        self.ach_lay.setContentsMargins(0, 4, 0, 4)
        self.ach_lay.setSpacing(8)
        self.ach_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        asc.setWidget(ahost)
        outer.addWidget(asc, 1)
        return w

    def reload_profile(self):
        data, status = api_request("/launcher-api/client/profile/", token=self.token)
        if status != 200:
            return
        name = data.get("username", "")
        self.prof_name.setText(name)
        self.prof_avatar.setText(name[:1].upper())
        self.prof_status.setText(data.get("status", "") + (f"  ·  {data.get('email')}" if data.get("email") else ""))
        self.prof_lvl.setText(f"\u26a1 \u0423\u0440\u043e\u0432\u0435\u043d\u044c {data.get('level', 0)}  ·  {data.get('xp', 0)} XP")
        self.prof_points.setText(f"\u2b50 {data.get('steam_points', 0)} \u043e\u0447\u043a\u043e\u0432")
        self.stat_balance.setText(f"\u0411\u0410\u041b\u0410\u041d\u0421\n{data.get('balance', '0')} UZS")
        self.stat_games.setText(f"\u0418\u0413\u0420 \u0412 \u0411\u0418\u0411\u041b\u0418\u041e\u0422\u0415\u041a\u0415\n{data.get('games_owned', 0)}")
        self.stat_streak.setText(f"\u0421\u0415\u0420\u0418\u042f \u0411\u041e\u041d\u0423\u0421\u0410\n{data.get('daily_streak', 0)} \u0434\u043d.")
        while self.ach_lay.count():
            item = self.ach_lay.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        achs = data.get("achievements", [])
        if not achs:
            e = QLabel("\u041f\u043e\u043a\u0430 \u043d\u0435\u0442 \u0434\u043e\u0441\u0442\u0438\u0436\u0435\u043d\u0438\u0439. \u0418\u0433\u0440\u0430\u0439 \u0438 \u043f\u043e\u043a\u0443\u043f\u0430\u0439!")
            e.setObjectName("empty")
            self.ach_lay.addWidget(e)
        for a in achs:
            card = QFrame()
            card.setObjectName("achCard")
            h = QHBoxLayout(card)
            h.setContentsMargins(14, 10, 14, 10)
            ic = QLabel("\U0001f3c6")
            ic.setStyleSheet("font-size:24px; background:transparent;")
            h.addWidget(ic)
            col = QVBoxLayout()
            col.setSpacing(1)
            nm = QLabel(a.get("name", ""))
            nm.setObjectName("achName")
            col.addWidget(nm)
            ds = QLabel(a.get("description", ""))
            ds.setObjectName("achDesc")
            col.addWidget(ds)
            h.addLayout(col)
            h.addStretch(1)
            self.ach_lay.addWidget(card)

    def _make_detail_page(self):
        w = QWidget()
        w.setObjectName("page")
        self.detail_lay = QVBoxLayout(w)
        self.detail_lay.setContentsMargins(34, 24, 34, 24)
        self.detail_lay.setSpacing(12)
        return w

    def switch_page(self, which):
        for b in (self.btn_lib, self.btn_store, self.btn_chat, self.btn_prof):
            b.setChecked(False)
        if which == "lib":
            self.btn_lib.setChecked(True)
            self.stack.setCurrentWidget(self.lib_page)
            self.reload_library()
        elif which == "store":
            self.btn_store.setChecked(True)
            self.stack.setCurrentWidget(self.store_page)
            self.reload_store()
        elif which == "chat":
            self.btn_chat.setChecked(True)
            self.stack.setCurrentWidget(self.chat_page)
            self.reload_dialogs()
            self.reload_users()
        elif which == "prof":
            self.btn_prof.setChecked(True)
            self.stack.setCurrentWidget(self.prof_page)
            self.reload_profile()

    # ---------------- data ----------------
    def set_session(self, token, username):
        self.token, self.username = token, username
        self.user_label.setText(username)
        self.avatar.setText(username[0].upper())
        self.reload_library()
        self.reload_store()
        self.reload_dialogs()
        self.reload_users()

    def _clear_grid(self, grid):
        for i in reversed(range(grid.count())):
            w = grid.itemAt(i).widget()
            if w:
                w.setParent(None)

    def reload_library(self):
        self._clear_grid(self.grid)
        self.cards.clear()
        data, status = api_request("/launcher-api/client/library/", token=self.token)
        if status != 200:
            msg = QLabel("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0431\u0438\u0431\u043b\u0438\u043e\u0442\u0435\u043a\u0443")
            msg.setObjectName("empty")
            self.grid.addWidget(msg, 0, 0)
            return
        games = data.get("games", [])
        if not games:
            empty = QLabel("\u041f\u043e\u043a\u0430 \u043d\u0435\u0442 \u0438\u0433\u0440. \u0417\u0430\u0439\u0434\u0438 \u0432 \u041c\u0410\u0413\u0410\u0417\u0418\u041d \u0438 \u043a\u0443\u043f\u0438 \u043f\u0435\u0440\u0432\u0443\u044e!")
            empty.setObjectName("empty")
            self.grid.addWidget(empty, 0, 0)
            return
        for idx, g in enumerate(games):
            card = GameCard(g, store_mode=False)
            card.clicked.connect(self.show_detail)
            card.play_clicked.connect(self.toggle_game)
            self.grid.addWidget(card, idx // 4, idx % 4)
            self.cards[g["id"]] = card
            self._load_cover(g, card)
        self.update_balance()

    def reload_store(self):
        self._clear_grid(self.store_grid)
        self.store_cards.clear()
        data, status = api_request("/launcher-api/client/store/", token=self.token)
        if status != 200:
            msg = QLabel("\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u043c\u0430\u0433\u0430\u0437\u0438\u043d")
            msg.setObjectName("empty")
            self.store_grid.addWidget(msg, 0, 0)
            return
        self.update_balance()
        games = data.get("games", [])
        if not games:
            empty = QLabel("\u041c\u0430\u0433\u0430\u0437\u0438\u043d \u043f\u0443\u0441\u0442")
            empty.setObjectName("empty")
            self.store_grid.addWidget(empty, 0, 0)
            return
        for idx, g in enumerate(games):
            card = GameCard(g, store_mode=True)
            card.clicked.connect(self.show_detail)
            card.play_clicked.connect(self.on_store_btn)
            self.store_grid.addWidget(card, idx // 4, idx % 4)
            self.store_cards[g["id"]] = card
            self._load_cover(g, card)
        self._filter_store(self.search_box.text())

    def claim_bonus(self):
        data, status = api_request("/launcher-api/client/bonus/", "POST", token=self.token)
        if status == 200 and data.get("ok"):
            self.update_balance()
            self.toast_ok(f"\U0001f381 +{data.get('amount')} UZS! \u0421\u0435\u0440\u0438\u044f: {data.get('streak')} \u0434\u043d.")
        else:
            streak = data.get("streak", 0)
            self.toast_warn(f"\u0411\u043e\u043d\u0443\u0441 \u0443\u0436\u0435 \u043f\u043e\u043b\u0443\u0447\u0435\u043d \u0441\u0435\u0433\u043e\u0434\u043d\u044f (\u0441\u0435\u0440\u0438\u044f: {streak} \u0434\u043d.)")

    def _filter_store(self, text):
        text = (text or "").strip().lower()
        for gid, card in self.store_cards.items():
            g = card.game
            hay = (g.get("title", "") + " " + g.get("developer", "")).lower()
            card.setVisible(text in hay)

    def _load_cover(self, g, card):
        url = g.get("header_url") or ""
        if not url:
            return
        if not url.startswith("http"):
            url = SERVER_URL + url
        loader = CoverLoader(g["id"], url)
        loader.loaded.connect(lambda gid, pm, c=card: c.set_cover(pm))
        self.loaders.append(loader)
        loader.start()

    def update_balance(self):
        data, status = api_request("/launcher-api/client/store/", token=self.token)
        if status == 200:
            self.balance_label.setText(data.get("balance", "0") + " UZS")

    # ---------------- store actions ----------------
    def on_store_btn(self, game):
        if game.get("owned"):
            self.switch_page("lib")
        else:
            self.show_detail(game)

    def _detail_img(self, label, pm, w, h, r):
        try:
            label.setPixmap(rounded_pixmap(pm, w, h, r))
        except Exception:
            pass

    def _set_wl_btn(self, btn, in_wl):
        if in_wl:
            btn.setText("\u2605 \u0412 \u0436\u0435\u043b\u0430\u0435\u043c\u043e\u043c")
            btn.setObjectName("bonusBtn")
        else:
            btn.setText("\u2606 \u0412 \u0436\u0435\u043b\u0430\u0435\u043c\u043e\u0435")
            btn.setObjectName("ghostBtn")
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    def toggle_wishlist(self, game, btn):
        data, status = api_request("/launcher-api/client/wishlist/", "POST",
                                   token=self.token, payload={"game_id": game["id"]})
        if status == 200 and data.get("ok"):
            game["in_wishlist"] = data.get("in_wishlist")
            self._set_wl_btn(btn, game["in_wishlist"])
            if game["in_wishlist"]:
                self.toast_ok("\u2605 \u0414\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u043e \u0432 \u0436\u0435\u043b\u0430\u0435\u043c\u043e\u0435")
            else:
                self.toast_warn("\u0423\u0434\u0430\u043b\u0435\u043d\u043e \u0438\u0437 \u0436\u0435\u043b\u0430\u0435\u043c\u043e\u0433\u043e")

    def buy_game(self, game):
        data, status = api_request("/launcher-api/client/buy/", "POST",
                                   token=self.token, payload={"game_id": game["id"]})
        if status == 200 and data.get("ok"):
            self.toast_ok("✓ " + data.get("detail", "\u0418\u0433\u0440\u0430 \u043a\u0443\u043f\u043b\u0435\u043d\u0430!"))
            self.reload_store()
            self.reload_library()
        elif status == 402:
            QMessageBox.warning(self, "\u041d\u0435\u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u043e \u0441\u0440\u0435\u0434\u0441\u0442\u0432",
                                f"\u0426\u0435\u043d\u0430: {data.get('price')} UZS\n"
                                f"\u0411\u0430\u043b\u0430\u043d\u0441: {data.get('balance')} UZS\n\n"
                                "\u041f\u043e\u043f\u043e\u043b\u043d\u0438 \u0431\u0430\u043b\u0430\u043d\u0441 \u043d\u0430 \u0441\u0430\u0439\u0442\u0435.")
        else:
            detail = data.get("detail", "\u043e\u0448\u0438\u0431\u043a\u0430")
            if detail == "already_owned":
                QMessageBox.information(self, "\u0423\u0436\u0435 \u043a\u0443\u043f\u043b\u0435\u043d\u043e", "\u042d\u0442\u0430 \u0438\u0433\u0440\u0430 \u0443\u0436\u0435 \u0432 \u0442\u0432\u043e\u0435\u0439 \u0431\u0438\u0431\u043b\u0438\u043e\u0442\u0435\u043a\u0435.")
            else:
                QMessageBox.warning(self, "\u041e\u0448\u0438\u0431\u043a\u0430", str(detail))

    # ---------------- detail page ----------------
    def show_detail(self, game):
        while self.detail_lay.count():
            item = self.detail_lay.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
            elif item.layout():
                pass

        back = QPushButton("\u2190  \u041d\u0410\u0417\u0410\u0414")
        back.setFixedWidth(140)
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.clicked.connect(lambda: self.stack.setCurrentWidget(
            self.store_page if self.btn_store.isChecked() else self.lib_page))
        self.detail_lay.addWidget(back)

        title = QLabel(game["title"])
        title.setObjectName("detailTitle")
        title.setWordWrap(True)
        self.detail_lay.addWidget(title)

        dev = QLabel(game.get("developer", ""))
        dev.setObjectName("detailDev")
        self.detail_lay.addWidget(dev)

        if game.get("header_url"):
            cov = QLabel()
            cov.setFixedSize(480, 200)
            cov.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cov.setStyleSheet("background:#0c1422; border-radius:12px;")
            self.detail_lay.addWidget(cov)
            url = game["header_url"]
            if not url.startswith("http"):
                url = SERVER_URL + url
            loader = CoverLoader(-100 - int(game["id"]), url)
            loader.loaded.connect(lambda gid, pm, c=cov: self._detail_img(c, pm, 480, 200, 12))
            self.loaders.append(loader)
            loader.start()

        desc = QLabel(game.get("description") or game.get("short_description") or "")
        desc.setObjectName("detailDesc")
        desc.setWordWrap(True)
        desc.setMaximumWidth(700)
        self.detail_lay.addWidget(desc)
        self.detail_lay.addSpacing(8)

        shots = game.get("screenshots") or []
        if shots:
            srow = QHBoxLayout()
            srow.setSpacing(10)
            for i, u in enumerate(shots[:4]):
                lbl = QLabel()
                lbl.setFixedSize(170, 95)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("background:#0c1422; border-radius:8px;")
                if not u.startswith("http"):
                    u = SERVER_URL + u
                loader = CoverLoader(-300 - int(game["id"]) * 10 - i, u)
                loader.loaded.connect(lambda gid, pm, l=lbl: self._detail_img(l, pm, 170, 95, 8))
                self.loaders.append(loader)
                loader.start()
                srow.addWidget(lbl)
            self.detail_lay.addLayout(srow)
            self.detail_lay.addSpacing(8)

        row = QHBoxLayout()
        if game.get("owned") or game.get("installed") is not None and game.get("owned"):
            pass
        if game.get("owned"):
            lbl = QLabel("\u2714 \u0412 \u0431\u0438\u0431\u043b\u0438\u043e\u0442\u0435\u043a\u0435")
            lbl.setObjectName("priceTag")
            row.addWidget(lbl)
        else:
            if int(game.get("discount") or 0) > 0:
                d = QLabel(f"-{game['discount']}%")
                d.setObjectName("discountTag")
                row.addWidget(d)
                old = QLabel(game["price"] + " UZS")
                old.setObjectName("priceOld")
                row.addWidget(old)
            price = QLabel(game["final_price"] + " UZS")
            price.setObjectName("priceTag")
            row.addWidget(price)
            buy = QPushButton("\U0001f6d2  \u041a\u0423\u041f\u0418\u0422\u042c")
            buy.setObjectName("buyBtn")
            buy.setFixedSize(200, 52)
            buy.setCursor(Qt.CursorShape.PointingHandCursor)
            buy.clicked.connect(lambda: self.buy_game(game))
            row.addWidget(buy)
            wlb = QPushButton("")
            wlb.setCursor(Qt.CursorShape.PointingHandCursor)
            wlb.setFixedHeight(52)
            self._set_wl_btn(wlb, bool(game.get("in_wishlist")))
            wlb.clicked.connect(lambda: self.toggle_wishlist(game, wlb))
            row.addSpacing(10)
            row.addWidget(wlb)
        row.addStretch(1)
        self.detail_lay.addLayout(row)
        self.detail_lay.addStretch(1)
        self.stack.setCurrentWidget(self.detail_page)

    # ---------------- chat ----------------
    def reload_dialogs(self):
        self.dialog_list.clear()
        data, status = api_request("/launcher-api/client/chat/dialogs/", token=self.token)
        if status != 200:
            return
        for d in data.get("dialogs", []):
            label = f"\U0001f464 {d['username']}"
            if d.get("unread"):
                label += f"   [{d['unread']}]"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, d["username"])
            if d.get("unread"):
                item.setForeground(Qt.GlobalColor.cyan)
            self.dialog_list.addItem(item)
        total = sum(d.get("unread", 0) for d in data.get("dialogs", []))
        base = "💬  ЧАТ"
        self.btn_chat.setText(base + (f"  [{total}]" if total else ""))

    def reload_users(self):
        if not hasattr(self, "users_list"):
            return
        self.users_list.clear()
        data, status = api_request("/launcher-api/client/users/", token=self.token)
        if status != 200:
            return
        for u in data.get("users", []):
            icon = "\U0001f7e2" if u.get("online") else "\U0001f464"
            label = f"{icon} {u['username']}"
            if u.get("unread"):
                label += f"  [{u['unread']}]"
            item = QListWidgetItem(label)
            if u.get("unread"):
                item.setForeground(Qt.GlobalColor.cyan)
            item.setData(Qt.ItemDataRole.UserRole, u["username"])
            self.users_list.addItem(item)

    def _open_dialog(self, item):
        self.chat_partner = item.data(Qt.ItemDataRole.UserRole)
        self.chat_partner_label.setText("\U0001f464 " + self.chat_partner)
        self._load_messages()

    def _load_messages(self):
        partner = getattr(self, "chat_partner", None)
        if not partner:
            return
        data, status = api_request(
            "/launcher-api/client/chat/messages/?with=" + urllib.parse.quote(partner),
            token=self.token)
        if status != 200:
            return
        while self.msg_lay.count() > 1:
            item = self.msg_lay.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        for m in data.get("messages", []):
            self._append_bubble(m)
        sb = self.msg_scroll.verticalScrollBar()
        QTimer.singleShot(30, lambda: sb.setValue(sb.maximum()))

    def _append_bubble(self, m):
        wrap = QFrame()
        h = QHBoxLayout(wrap)
        h.setContentsMargins(0, 0, 0, 0)
        box = QFrame()
        box.setObjectName("bubbleMine" if m["mine"] else "bubbleTheirs")
        v = QVBoxLayout(box)
        v.setContentsMargins(10, 6, 10, 6)
        v.setSpacing(2)
        text = QLabel(m["text"])
        text.setWordWrap(True)
        text.setMaximumWidth(380)
        v.addWidget(text)
        tm = QLabel(m["time"])
        tm.setObjectName("bubbleTime")
        tm.setAlignment(Qt.AlignmentFlag.AlignRight)
        v.addWidget(tm)
        if m["mine"]:
            h.addStretch(1)
            h.addWidget(box)
        else:
            h.addWidget(box)
            h.addStretch(1)
        self.msg_lay.insertWidget(self.msg_lay.count() - 1, wrap)

    def _send_msg(self):
        partner = getattr(self, "chat_partner", None)
        text = self.chat_input.text().strip()
        if not partner or not text:
            return
        data, status = api_request("/launcher-api/client/chat/send/", "POST",
                                   token=self.token,
                                   payload={"to": partner, "text": text})
        if status == 200 and data.get("ok"):
            self.chat_input.clear()
            self._load_messages()
            self.reload_dialogs()

    def _chat_poll(self):
        if self.token and self.stack.currentWidget() == self.chat_page:
            self._load_messages()
            self.reload_dialogs()

    # ---------------- play ----------------
    def toggle_game(self, game):
        running = self.process and self.process.poll() is None
        if running and self.current_game and self.current_game["id"] == game["id"]:
            self.stop_game()
            return
        if running:
            QMessageBox.information(self, "\u0418\u0433\u0440\u0430 \u0443\u0436\u0435 \u0437\u0430\u043f\u0443\u0449\u0435\u043d\u0430",
                                    f"\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0437\u0430\u043a\u0440\u043e\u0439 \u00ab{self.current_game['title']}\u00bb.")
            return
        self.launch_game(game)

    def launch_game(self, game):
        exe = game.get("exe_path") or ""
        if not exe or not Path(exe).exists():
            QMessageBox.warning(self, "\u0424\u0430\u0439\u043b \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d",
                                f"\u041d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d .exe \u0444\u0430\u0439\u043b \u0438\u0433\u0440\u044b:\n{exe or '-'}")
            return
        if Path(exe).suffix.lower() != ".exe":
            QMessageBox.warning(self, "\u041d\u0435\u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u044b\u0439 \u0444\u0430\u0439\u043b \u0438\u0433\u0440\u044b",
                                "\u0412 \u043f\u043e\u043b\u0435 \u00ab\u0424\u0430\u0439\u043b \u0438\u0433\u0440\u044b\u00bb \u0437\u0430\u0433\u0440\u0443\u0436\u0435\u043d \u043d\u0435 .exe.\n"
                                "\u0417\u0430\u0433\u0440\u0443\u0437\u0438 \u043d\u0430\u0441\u0442\u043e\u044f\u0449\u0438\u0439 .exe \u0447\u0435\u0440\u0435\u0437 \u0430\u0434\u043c\u0438\u043d\u043a\u0443 \u0438\u043b\u0438 \u0432\n"
                                "installed_games/<\u043f\u0430\u043f\u043a\u0430 \u0438\u0433\u0440\u044b>/.")
            return
        data, status = api_request("/launcher-api/client/play/start/", "POST",
                                   token=self.token, payload={"game_id": game["id"]})
        if status != 200:
            QMessageBox.warning(self, "\u041e\u0448\u0438\u0431\u043a\u0430", str(data.get("detail", "\u043d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043d\u0430\u0447\u0430\u0442\u044c \u0441\u0435\u0441\u0441\u0438\u044e")))
            return
        self.session_id = data.get("session_id")
        try:
            self.process = subprocess.Popen([exe], cwd=str(Path(exe).parent))
        except OSError as e:
            if getattr(e, "winerror", None) == 740:
                try:
                    self.process = subprocess.Popen(
                        ["powershell", "-NoProfile", "-Command",
                         f'Start-Process -FilePath "{exe}" -Verb RunAs -Wait'],
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                except Exception as e2:
                    self._abort_session(str(e2))
                    return
            else:
                self._abort_session(str(e))
                return
        except Exception as e:
            self._abort_session(str(e))
            return
        self.current_game = game
        self.started_at = time.time()
        self.bar_label.setText(f"\u25cf  \u0418\u0433\u0440\u0430\u0435\u0448\u044c:  {game['title']}")
        self.bar_timer_label.setText("00:00:00")
        self.bar.show()
        self.tick.start(1000)
        self.beat.start(HEARTBEAT_MS)
        card = self.cards.get(game["id"])
        if card:
            card.set_playing(True)
        self.watcher = GameWatcher(self.process, game["id"])
        self.watcher.finished_game.connect(self.on_game_exit)
        self.watcher.start()

    def _abort_session(self, err):
        api_request("/launcher-api/client/play/end/", "POST", token=self.token,
                    payload={"session_id": self.session_id})
        self.session_id = None
        self.process = None
        QMessageBox.critical(self, "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c \u0438\u0433\u0440\u0443", str(err))

    def stop_game(self):
        if self.watcher:
            self.watcher.stop()
            self.watcher = None
        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass
            self.process = None
        if self.session_id:
            data, _ = api_request("/launcher-api/client/play/end/", "POST", token=self.token,
                                  payload={"session_id": self.session_id})
            self.session_id = None
            if self.current_game:
                card = self.cards.get(self.current_game["id"])
                if card:
                    card.set_playing(False)
                    if data.get("total_display"):
                        card.update_time(data["total_display"], data.get("sessions", 0))
        self.current_game = None
        self.bar.hide()
        self.tick.stop()
        self.beat.stop()

    def on_game_exit(self, game_id):
        self.stop_game()

    def _tick(self):
        if self.current_game:
            self.bar_timer_label.setText(fmt_hms(time.time() - self.started_at))

    def _heartbeat(self):
        if self.session_id:
            api_request("/launcher-api/client/play/heartbeat/", "POST", token=self.token,
                        payload={"session_id": self.session_id}, timeout=5)

    def shutdown(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass
        if self.watcher:
            self.watcher.stop()
        if self.session_id:
            api_request("/launcher-api/client/play/end/", "POST", token=self.token,
                        payload={"session_id": self.session_id}, timeout=3)


    def _move_orbs(self):
        for o in self._orbs:
            o["x"] += o["sx"] / 100
            o["y"] += o["sy"] / 100
            if o["x"] < -0.2 or o["x"] > 1.2:
                o["sx"] *= -1
            if o["y"] < -0.2 or o["y"] > 1.2:
                o["sy"] *= -1
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#0a0f1a"))
        for o in self._orbs:
            cx, cy = o["x"] * w, o["y"] * h
            g = QRadialGradient(cx, cy, o["r"])
            g.setColorAt(0, QColor.fromHsl(o["hue"], 200, 62, int(255 * o["a"])))
            g.setColorAt(1, QColor.fromHsl(o["hue"], 220, 40, 0))
            p.setBrush(g)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), o["r"], o["r"])
        p.end()

    def toast_ok(self, text):
        self._toast(text, True)

    def toast_warn(self, text):
        self._toast(text, False)

    def _toast(self, text, ok):
        win = self.window()
        if hasattr(win, "show_toast"):
            win.show_toast(text, ok)


# --------------------------------------------------------------- window
class LauncherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Steam Clone Launcher")
        self.resize(1280, 800)
        self.setMinimumSize(1020, 660)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_page = LoginPage()
        self.main_page = MainPage()
        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.main_page)

        self.login_page.logged_in.connect(self.on_logged_in)
        self.main_page.logout_requested.connect(self.on_logout)

        cfg = load_config()
        if cfg.get("server_url"):
            set_server_url(cfg["server_url"])
        else:
            # Адрес сервера можно положить рядом с exe в файл server.txt
            # (одна строка, например: https://логин.pythonanywhere.com)
            srv_file = _base_dir() / "server.txt"
            try:
                if srv_file.is_file():
                    set_server_url(srv_file.read_text("utf-8").strip())
            except Exception:
                pass
        if cfg.get("token"):
            data, status = api_request("/launcher-api/client/library/", token=cfg["token"])
            if status == 200:
                self.on_logged_in(cfg["token"], data.get("username", cfg.get("username", "")))

    def on_logged_in(self, token, username):
        self.main_page.set_session(token, username)
        self.stack.setCurrentWidget(self.main_page)

    def show_toast(self, text, ok=True):
        toast = QLabel(text)
        toast.setObjectName("toastOk" if ok else "toastWarn")
        toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toast.setFixedHeight(44)
        toast.adjustSize()
        w = max(220, toast.sizeHint().width() + 44)
        toast.setFixedWidth(w)
        toast.setParent(self)
        toast.move((self.width() - w) // 2, 20)
        toast.show()
        toast.raise_()
        op = QGraphicsOpacityEffect(toast)
        op.setOpacity(0.0)
        toast.setGraphicsEffect(op)
        anim = QPropertyAnimation(op, b"opacity", toast)
        anim.setDuration(260)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.start()

        def _fade():
            anim2 = QPropertyAnimation(op, b"opacity", toast)
            anim2.setDuration(420)
            anim2.setStartValue(1.0)
            anim2.setEndValue(0.0)
            anim2.finished.connect(toast.deleteLater)
            anim2.start()

        QTimer.singleShot(2400, _fade)

    def on_logout(self):
        self.main_page.shutdown()
        cfg = load_config()
        cfg.pop("token", None)
        cfg.pop("username", None)
        save_config(cfg)
        self.main_page.token = None
        self.login_page.password.clear()
        self.login_page.error.setText("")
        self.stack.setCurrentWidget(self.login_page)

    def closeEvent(self, event):
        self.main_page.shutdown()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Steam Clone Launcher")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(QSS)

    splash = SplashWidget()
    splash.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
    splash.setFixedSize(560, 380)
    splash.show()
    app.processEvents()

    def _boot():
        start_server_if_needed()
        win = LauncherWindow()

        def _finish():
            win.show()
            splash.close()

        splash.done.connect(_finish)

    QTimer.singleShot(50, _boot)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
