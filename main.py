"""
MotionSync - מניעת בחילות נסיעה באמצעות מצלמת הרשת.

קובץ ראשי: מחבר בין מנוע ה-Optical Flow, שכבת ה-Overlay,
סמל ה-System Tray ומסך ההגדרות.

הרצה:  python main.py
"""
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMessageBox

from config import Config
from motion_engine import MotionEngine
from overlay import Overlay
from settings_dialog import SettingsDialog
from tray_icon import TrayController


class MotionSyncApp:
    def __init__(self):
        self.config = Config.load()
        self.engine = None

        self.overlay = Overlay(self.config)
        self.tray = TrayController()
        self.tray.start_pause_requested.connect(self.toggle_running)
        self.tray.settings_requested.connect(self.open_settings)
        self.tray.exit_requested.connect(self.exit)
        self.tray.show()

        self.running = False
        self.start_engine()

    # ------------------------------------------------------------------
    def start_engine(self) -> None:
        if self.engine is not None:
            self.engine.stop()
            self.engine = None
        self.engine = MotionEngine(
            self.config.camera_index, self.config.target_fps
        )
        self.engine.motion.connect(self.overlay.set_motion)
        self.engine.error.connect(self._on_engine_error)
        self.engine.start()
        self.overlay.start()
        self.running = True
        self.tray.set_running(True)

    def stop_engine(self) -> None:
        if self.engine is not None:
            self.engine.stop()
            self.engine = None
        self.overlay.stop()
        self.running = False
        self.tray.set_running(False)

    def toggle_running(self) -> None:
        if self.running:
            self.stop_engine()
        else:
            self.start_engine()

    # ------------------------------------------------------------------
    def open_settings(self) -> None:
        was_running = self.running
        if was_running:
            self.stop_engine()

        dialog = SettingsDialog(self.config)
        if dialog.exec_() == SettingsDialog.Accepted:
            dialog.apply_to_config()
            self.start_engine()
        elif not was_running:
            # בוטל והיה מושהה - נשארים מושהים
            self.running = False
            self.tray.set_running(False)
        else:
            self.start_engine()

    # ------------------------------------------------------------------
    def _on_engine_error(self, message: str) -> None:
        self.stop_engine()
        QMessageBox.warning(
            None, "MotionSync - שגיאת מצלמה", message
        )

    def exit(self) -> None:
        self.stop_engine()
        self.tray.hide()
        QApplication.quit()


def main():
    # HiDPI - חדות טובה יותר במסכי רטינה/סקיילינג
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("MotionSync")
    app.setApplicationDisplayName("MotionSync")

    try:
        controller = MotionSyncApp()
    except Exception as exc:
        QMessageBox.critical(
            None, "MotionSync - שגיאת הפעלה",
            "התוכנה לא הצליחה לעלות:\n%s" % exc,
        )
        sys.exit(1)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
