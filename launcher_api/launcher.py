import sys
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QHBoxLayout,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView


SITE_URL = "http://127.0.0.1:8000"


class SteamLauncher(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Steam Clone")
        self.resize(1400, 900)

        self.setMinimumSize(1100, 700)

        # CENTRAL
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        central.setLayout(layout)

        # SIDEBAR
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("""
            background: #171a21;
            border-right: 1px solid #2a475e;
        """)

        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(10)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)

        sidebar.setLayout(sidebar_layout)

        # WEB VIEW
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(SITE_URL))

        # BUTTON STYLE
        button_style = """
            QPushButton {
                background:#1b2838;
                color:white;
                border:none;
                padding:12px;
                text-align:left;
                font-size:14px;
                border-radius:6px;
            }

            QPushButton:hover {
                background:#2a475e;
            }
        """



       

        sidebar_layout.addStretch()

        layout.addWidget(sidebar)
        layout.addWidget(self.browser)

        # TOP MENU
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


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = SteamLauncher()
    window.show()

    sys.exit(app.exec())