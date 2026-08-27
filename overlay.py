r"""
MotionSync - שכבת התצוגה (Overlay).

חלון שקוף בגודל מסך מלא, נטול מסגרת, Always-on-Top ו-Click-Through
(WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE).

פריסת הנקודות: מסגרת לאורך ארבעת שולי המסך (בהשראת מוקאפ ההדגמה).
הנקודות זזות לאורך השוליים בהתאם לוקטור התנועה עם אינטרפולציה חלקה
ועטיפה (wrap-around), ובמצב תאורה חלשה מוצג חיווי אדום עדין בפינה.

צבע אדפטיבי: דגימת בהירות הרקע שמתחת לכל נקודה (צילום מסך בתדירות
נמוכה וברזולוציה מוקטנת) - נקודה שחורה על רקע בהיר ולבנה על רקע כהה.
"""
import ctypes
import sys

from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import QApplication, QWidget

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000

ANIM_INTERVAL_MS = 16        # קצב אנימציית ה-Overlay
SAMPLE_INTERVAL_MS = 800     # קצב דגימת בהירות הרקע (צבע אדפטיבי)
BRIGHTNESS_THRESHOLD = 128   # מעליו רקע "בהיר" -> נקודה שחורה
TOPMOST_REASSERT_FRAMES = 125  # אימות Topmost מחדש מדי ~2 שניות
SAMPLE_SCALE = 6             # מקדם הקטנת צילום המסך לדגימה
EDGE_BAND = 110              # רוחב רצועת השוליים שבה מצוירות נקודות
FADE_ZONE = 35               # אזור דהייה בכניסה/יציאה של נקודה מהרצועה


class Overlay(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # מחוץ ל-Windows: החלון שקוף לקלט דרך Qt (macOS/Linux)
        if sys.platform != "win32":
            self.setWindowFlag(Qt.WindowTransparentForInput, True)

        self._offset = QPointF(0.0, 0.0)    # מיקום נוכחי (מוחלק)
        self._target = QPointF(0.0, 0.0)    # יעד מהמנוע
        self._active = False                # האם יש זיהוי תנועה תקין
        self._fade = 0.0                    # דהייה בין מצבים (0..1)
        self._tick_count = 0

        self._bg_img = None                 # צילום מסך מדוגם לצבע אדפטיבי

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(ANIM_INTERVAL_MS)
        self._anim_timer.timeout.connect(self._tick)

        self._sample_timer = QTimer(self)
        self._sample_timer.setInterval(SAMPLE_INTERVAL_MS)
        self._sample_timer.timeout.connect(self._sample_background)

        # התאמה אוטומטית לשינוי רזולוציה / מסך
        screen = QApplication.primaryScreen()
        if screen is not None:
            screen.geometryChanged.connect(self._fit_to_screen)
            QApplication.instance().primaryScreenChanged.connect(
                self._on_primary_screen_changed
            )

    def start(self) -> None:
        self._fit_to_screen()
        self.show()
        self._make_click_through()
        self._anim_timer.start()
        self._sample_timer.start()
        self._sample_background()

    def stop(self) -> None:
        self._anim_timer.stop()
        self._sample_timer.stop()
        self.close()

    def _on_primary_screen_changed(self, screen):
        if screen is not None:
            try:
                screen.geometryChanged.disconnect(self._fit_to_screen)
            except TypeError:
                pass
            screen.geometryChanged.connect(self._fit_to_screen)
            self._fit_to_screen()

    def _fit_to_screen(self, *args) -> None:
        screen = QApplication.primaryScreen()
        if screen is not None:
            self.setGeometry(screen.geometry())

    def _make_click_through(self) -> None:
        """שקיפות לקלט עכבר/מקלדת + העלאה ל-Topmost (Windows: Win32 API)."""
        if sys.platform != "win32":
            return  # ב-macOS/Linux מטופל דרך Qt.WindowTransparentForInput
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE,
            )
            user32.SetWindowPos(
                hwnd, ctypes.c_void_p(-1), 0, 0, 0, 0,
                0x0001 | 0x0002 | 0x0010 | 0x0040,  # NOSIZE|NOMOVE|NOACTIVATE|SHOWWINDOW
            )
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._make_click_through()

    def set_motion(self, vx: float, vy: float, active: bool) -> None:
        sens = max(0.0, self.config.sensitivity)
        self._target = QPointF(vx * sens * 4.0, vy * sens * 4.0)
        self._active = active

    def _tick(self) -> None:
        # אינטרפולציה לכיוון היעד -> אנימציה חלקה
        self._offset += (self._target - self._offset) * 0.12
        # דהייה עדינה של הנקודות כשאין זיהוי
        target_fade = 1.0 if self._active else 0.0
        self._fade += (target_fade - self._fade) * 0.06

        # אימות Topmost מחדש מדי כמה שניות (חלונות מסוימים "גונבים" את המקום)
        self._tick_count += 1
        if self._tick_count % TOPMOST_REASSERT_FRAMES == 0:
            self._make_click_through()

        self.update()

    def _sample_background(self) -> None:
        """צילום מסך מוקטן לשימוש בבחירת צבע אדפטיבי."""
        try:
            screen = QApplication.primaryScreen()
            if screen is None:
                return
            grab = screen.grabWindow(0)
            if grab.isNull():
                return
            scaled = grab.scaled(
                max(1, grab.width() // SAMPLE_SCALE),
                max(1, grab.height() // SAMPLE_SCALE),
                Qt.IgnoreAspectRatio, Qt.SmoothTransformation,
            )
            img = scaled.toImage()
            if not img.isNull():
                self._bg_img = img
        except Exception:
            self._bg_img = None

    def _bg_brightness(self, x: float, y: float) -> float:
        """בהירות ממוצעת (0-255) של הרקע סביב נקודת מסך נתונה. -1 = אין דגימה."""
        img = self._bg_img
        if img is None:
            return -1.0
        w, h = self.width(), self.height()
        iw, ih = img.width(), img.height()
        if iw == 0 or ih == 0:
            return -1.0
        sx = int(x / w * (iw - 1))
        sy = int(y / h * (ih - 1))
        total, count = 0, 0
        for dy in (-2, -1, 0, 1, 2):
            for dx in (-2, -1, 0, 1, 2):
                px, py = sx + dx, sy + dy
                if 0 <= px < iw and 0 <= py < ih:
                    c = img.pixelColor(px, py)
                    total += (c.red() + c.green() + c.blue()) // 3
                    count += 1
        return total / count if count else -1.0

    def _frame_positions(self, spacing: int):
        """מיקומי נקודות לאורך שולי המסך.

        ההיגיון (בהשראת Vehicle Motion Cues של אפל ועקרון ה-vection):
        כל הנקודות נעות יחד כשדה זרימה דו-ממדי אחיד - בדיוק כמו הסביבה
        האמיתית שזזה מול העין בזמן נסיעה. פנייה ימינה/שמאלה מזיזה את
        הסריג אופקית (נקודות נכנסות מצידי המסך), והאצה/בלימה מזיזה
        אנכית. הנקודות מצוירות רק כשהן נמצאות ברצועת השוליים.
        """
        w, h = self.width(), self.height()
        ox, oy = self._offset.x(), self._offset.y()
        pts = []

        # סריג מלא על פני המסך, מוזז בוקטור התנועה עם עטיפה
        cols = int(w // spacing) + 2
        rows = int(h // spacing) + 2
        for j in range(rows):
            y = (j * spacing + oy) % (rows * spacing) - (spacing / 2)
            for i in range(cols):
                x = (i * spacing + ox) % (cols * spacing) - (spacing / 2)
                pts.append((x, y))
        return pts

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)

        cfg = self.config
        spacing = max(40, int(cfg.dot_spacing))
        radius = max(2, int(cfg.dot_size))
        base_alpha = int(max(0.05, min(1.0, cfg.dot_opacity)) * 255)
        global_alpha = base_alpha * self._fade

        if global_alpha > 2:
            adaptive = bool(cfg.adaptive_color) and self._bg_img is not None
            for (x, y) in self._frame_positions(spacing):
                # מרחק מקצה המסך הקרוב ביותר
                d = min(x, self.width() - x, y, self.height() - y)
                if d >= EDGE_BAND:
                    continue  # מחוץ לרצועת השוליים - לא מצויר
                # דהייה עדינה בכניסה לרצועה ובקצה החיצוני (כמו באנימציה של אפל)
                t = min(d, EDGE_BAND - d) / FADE_ZONE
                alpha = int(global_alpha * max(0.0, min(1.0, t)))
                if alpha <= 2:
                    continue

                if adaptive:
                    bright = self._bg_brightness(x, y)
                    if bright < 0:
                        color = QColor("#FFFFFF")
                    elif bright >= BRIGHTNESS_THRESHOLD:
                        color = QColor(0, 0, 0)   # רקע בהיר -> נקודה שחורה
                    else:
                        color = QColor("#FFFFFF")  # רקע כהה -> נקודה לבנה
                else:
                    color = QColor(cfg.dot_color)
                color.setAlpha(alpha)
                painter.setBrush(color)
                painter.drawEllipse(int(x) - radius, int(y) - radius,
                                    radius * 2, radius * 2)

        # חיווי "אין זיהוי" - נקודה אדומה שקופה בפינה
        if self._fade < 0.6:
            indicator_alpha = int(120 * (1.0 - self._fade))
            painter.setBrush(QColor(255, 40, 40, indicator_alpha))
            r = 4
            painter.drawEllipse(self.width() - 16, self.height() - 16, r * 2, r * 2)

        painter.end()

