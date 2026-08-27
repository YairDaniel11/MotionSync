"""
MotionSync - סמל System Tray ותפריט קליק-ימני.

אפשרויות: הפעל/השהה, הגדרות, יציאה.
"""
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import QMenu, QSystemTrayIcon

from resources import app_icon


def make_tray_icon(active: bool = True) -> QIcon:
    """אייקון האפליקציה עם נקודת מצב: ירוקה (פעיל) / אפורה (מושהה)."""
    size = 64
    pix = app_icon().pixmap(size, size)
    if pix.isNull():
        pix = QPixmap(size, size)
        pix.fill(QColor("#1b6f8c"))

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    dot = size // 3
    margin = size // 16
    p.setBrush(QColor("#2ecc71") if active else QColor("#95a5a6"))
    p.setPen(QColor("white"))
    p.drawEllipse(size - dot - margin, size - dot - margin, dot, dot)
    p.end()
    return QIcon(pix)


class TrayController(QSystemTrayIcon):
    start_pause_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    exit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(make_tray_icon(True), parent)
        self.setToolTip("MotionSync - מניעת בחילות נסיעה")
        self._running = True

        menu = QMenu()
        self.toggle_action = menu.addAction("השהה")
        menu.addSeparator()
        settings_action = menu.addAction("הגדרות")
        exit_action = menu.addAction("יציאה")

        self.toggle_action.triggered.connect(self.start_pause_requested.emit)
        settings_action.triggered.connect(self.settings_requested.emit)
        exit_action.triggered.connect(self.exit_requested.emit)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.settings_requested.emit()

    def set_running(self, running: bool) -> None:
        self._running = running
        self.setIcon(make_tray_icon(running))
        self.toggle_action.setText("השהה" if running else "הפעל")
