"""
MotionSync - סמל System Tray ותפריט קליק-ימני.

אפשרויות: הפעל/השהה, הגדרות, יציאה.
"""
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import QMenu, QSystemTrayIcon


def make_tray_icon(active: bool = True) -> QIcon:
    """מייצר סמל פשוט: עיגול ירוק (פעיל) / אפור (מושהה)."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    color = QColor("#2ecc71") if active else QColor("#95a5a6")
    p.setBrush(color)
    p.setPen(Qt.NoPen)
    p.drawEllipse(4, 4, 24, 24)
    # "נקודות" לבנות - סמליל התנועה
    p.setBrush(QColor("white"))
    for (x, y) in ((10, 11), (16, 16), (10, 21)):
        p.drawEllipse(x, y, 4, 4)
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
