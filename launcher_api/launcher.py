import sys
import os
import subprocess
import ctypes
from PyQt6.QtCore import Qt, QUrl, pyqtSlot, QObject
from PyQt6.QtGui import QAction
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

# URL вашего локального Django-сервера
SITE_URL = "http://127.0.0.1:8000/"


class GameBridge(QObject):
    """Класс-мост для приема команд из JavaScript в Python"""
    def __init__(self, launcher):
        super().__init__()
        self.launcher = launcher

    @pyqtSlot(str)
    def launchGame(self, game_path):
        """Вызывается из JS для запуска EXE"""
        self.launcher.run_game_process(game_path)

    @pyqtSlot()
    def stopGame(self):
        """Вызывается из JS для закрытия игры"""
        self.launcher.terminate_game_process()


class SteamLauncher(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Steam Clone")
        self.resize(1400, 900)
        self.setMinimumSize(1100, 700)

        self.game_process = None

        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        central.setLayout(layout)

        # Боковое меню
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("""
            background: #171a21;
            border-right: 1px solid #2a475e;
        """)
        sidebar_layout = QVBoxLayout()
        sidebar.setLayout(sidebar_layout)
        sidebar_layout.addStretch()

        # Браузерный движок
        self.browser = QWebEngineView()

        # WebChannel — мост между JS и Python
        self.channel = QWebChannel()
        self.bridge = GameBridge(self)
        self.channel.registerObject("pyBridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)

        # Инжектируем qwebchannel.js + инициализацию моста на каждой странице
        self.browser.loadFinished.connect(self.on_page_loaded)

        self.browser.setUrl(QUrl(SITE_URL))

        layout.addWidget(sidebar)
        layout.addWidget(self.browser)

        # Верхнее меню навигации
        menubar = self.menuBar()
        nav_menu = menubar.addMenu("Навигация")

        back_action = QAction("Назад", self)
        back_action.triggered.connect(self.browser.back)

        forward_action = QAction("Вперёд", self)
        forward_action.triggered.connect(self.browser.forward)

        reload_action = QAction("Обновить", self)
        reload_action.triggered.connect(self.browser.reload)

        nav_menu.addAction(back_action)
        nav_menu.addAction(forward_action)
        nav_menu.addAction(reload_action)

    def on_page_loaded(self, ok):
        """Инжектируем WebChannel мост после загрузки каждой страницы"""
        if not ok:
            return

        js = """
        (function() {
            var script = document.createElement('script');
            script.src = 'qrc:///qtwebchannel/qwebchannel.js';
            script.onload = function() {
                window._pyBridge = null;
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    window._pyBridge = channel.objects.pyBridge;
                    console.log('[Launcher] Мост с Python установлен!');
                    document.querySelectorAll('.btn_launch_game').forEach(function(btn) {
                        btn.style.pointerEvents = 'auto';
                        btn.style.opacity = '1';
                    });
                });
            };
            document.head.appendChild(script);
        })();
        """
        self.browser.page().runJavaScript(js)

    def run_game_process(self, game_path):
        """Запуск игры с правами администратора (WinError 740 fix)"""
        if not os.path.isabs(game_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(base_dir, game_path)
            if os.path.exists(full_path):
                game_path = full_path

        if not os.path.exists(game_path):
            QMessageBox.critical(self, "Ошибка", f"Файл не найден:\n{game_path}")
            return

        try:
            # ShellExecuteW с "runas" — запуск с правами администратора
            # Windows покажет UAC окно подтверждения
            result = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", game_path, None, None, 1
            )
            if result <= 32:
                QMessageBox.critical(self, "Ошибка", f"Не удалось запустить игру (код {result})")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось запустить игру:\n{str(e)}")

    def terminate_game_process(self):
        """Принудительное закрытие запущенной игры"""
        if self.game_process and self.game_process.poll() is None:
            self.game_process.terminate()
            self.game_process = None
        else:
            QMessageBox.information(self, "Инфо", "Нет активных игр.")

    def closeEvent(self, event):
        """Закрываем игру при выходе из лаунчера"""
        if self.game_process and self.game_process.poll() is None:
            self.game_process.terminate()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SteamLauncher()
    window.show()
    sys.exit(app.exec())