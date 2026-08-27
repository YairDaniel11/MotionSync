"""
MotionSync - מנוע זיהוי התנועה (Optical Flow Engine).

קריאה ממצלמת הרשת ברזולוציה נמוכה (640x480), חישוב שטף אופטי דליל
(Lucas-Kanade) על "נקודות עניין" ברקע, תוך:
  * מיסוך אזור הפנים של המשתמש (כדי להתעלם מתנועות ראש).
  * חישוב וקטור תנועה דומיננטי באמצעות חציון (עמיד לרעשים).
  * החלקה אקספוננציאלית (EMA) לאנימציה חלקה.
  * זיהוי חשיפה נמוכה / מעט נקודות -> דגל active=False (מצב "תאורה חלשה").
"""
import sys
import time

import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

# סף בהירות ממוצעת מתחתיו נחשב "חשיכה" (נסיעת לילה)
LOW_LIGHT_BRIGHTNESS = 18.0
# מספר נקודות מזערי כדי לסמוך על הווקטור
MIN_FEATURES = 10
# בכל כמה פריימים מריצים זיהוי פנים (חיסכון במעבד)
FACE_DETECT_EVERY = 10
# מקדם הגדלה של מסכת הפנים
FACE_MARGIN = 1.4


class MotionEngine(QThread):
    """רץ ברקע, דוגם את המצלמה ופולט וקטור תנועה מוחלק."""

    # vx, vy - וקטור בפיקסלים/פריים; active - האם יש זיהוי תקין
    motion = pyqtSignal(float, float, bool)
    error = pyqtSignal(str)

    def __init__(self, camera_index: int = 0, target_fps: int = 30,
                 parent=None):
        super().__init__(parent)
        self.camera_index = int(camera_index)
        self.target_fps = max(15, int(target_fps))
        self._running = True
        self._smooth_x = 0.0
        self._smooth_y = 0.0
        self._frame_count = 0
        self._face_rects = []  # רשימת מלבני פנים (x, y, w, h)
        self._prev_corners = None  # נקודות מעקב מהפריים הקודם
        # זיהוי פנים אופציונלי - לא קיים ב-OpenCV 5 (הוסר CascadeClassifier).
        # אם אין - fallback למיסוך האזור המרכזי (ראה _build_feature_image).
        self.face_cascade = None
        try:
            cls = getattr(cv2, "CascadeClassifier", None)
            if cls is not None:
                cascade = cls(
                    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                )
                if not cascade.empty():
                    self.face_cascade = cascade
        except Exception:
            self.face_cascade = None

    # ------------------------------------------------------------------
    def stop(self) -> None:
        self._running = False
        self.wait(3000)

    # ------------------------------------------------------------------
    def _build_feature_image(self, gray: np.ndarray) -> np.ndarray:
        """מחזיר עותק של הפריים כשאזורי הפנים "מאופסים" - כך שלא
        ייבחרו נקודות מעקב על הפנים/הראש של המשתמש.

        אם זיהוי פנים זמין - מוסיפים מסך סביב המלבנים שזוהו.
        בנוסף תמיד ממסכים את האזור המרכזי (שבו הראש מופיע בדרך כלל
        מול מצלמת לפטופ) - כך נשארים למעשה "פינות הפריים" עם הרקע,
        כאמור באפיון."""
        h, w = gray.shape
        feat = gray.copy()

        # אזור מרכזי קבוע (חצי רוחב, 55% גובה, מרכוז אנכי קל למעלה)
        cx0, cx1 = int(w * 0.25), int(w * 0.75)
        cy0, cy1 = int(h * 0.15), int(h * 0.70)
        feat[cy0:cy1, cx0:cx1] = 0

        # מסך מדויק סביב פנים שזוהו (עם שוליים)
        for (x, y, fw, fh) in self._face_rects:
            mx, my = int(fw * (FACE_MARGIN - 1) / 2), int(fh * (FACE_MARGIN - 1) / 2)
            x0 = max(0, x - mx)
            y0 = max(0, y - my)
            x1 = min(w, x + fw + mx)
            y1 = min(h, y + fh + my)
            feat[y0:y1, x0:x1] = 0
        return feat

    # ------------------------------------------------------------------
    def run(self) -> None:
        """עוטף את הלולאה ומוודא שכל חריגה תדווח ולא תקרוס בשקט."""
        try:
            self._run_impl()
        except Exception as exc:
            self.error.emit("אירעה שגיאה במנוע התנועה: %s" % exc)

    # ------------------------------------------------------------------
    def _run_impl(self) -> None:
        # CAP_DSHOW - פתיחה מהירה ב-Windows; ב-macOS משתמשים בברירת המחדל (AVFoundation)
        if sys.platform == "win32":
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(self.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        if not cap.isOpened():
            self.error.emit(
                "לא ניתן לפתוח את המצלמה.\n"
                "ודא שאין יישום אחר שמשתמש בה, וש-Windows מאפשר גישה "
                "למצלמה (הגדרות פרטיות -> מצלמה)."
            )
            return

        prev_gray = None
        frame_interval = 1.0 / self.target_fps
        consecutive_failures = 0

        while self._running:
            loop_start = time.perf_counter()
            ok, frame = cap.read()

            if not ok or frame is None:
                consecutive_failures += 1
                if consecutive_failures >= 30:
                    self.error.emit(
                        "אבדה הקריאה מהמצלמה (נותקה או נחסמה).\n"
                        "בדוק את החיבור וההרשאות והפעל מחדש."
                    )
                    break
                time.sleep(0.05)
                continue
            consecutive_failures = 0

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            self._frame_count += 1

            # --- זיהוי פנים מדי פריים-עשירי (חיסכון מעבד, אם זמין) ---
            if self.face_cascade is not None and self._frame_count % FACE_DETECT_EVERY == 1:
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.3, minNeighbors=5, minSize=(80, 80)
                )
                self._face_rects = list(faces) if faces is not None else []

            brightness = float(gray.mean())

            if prev_gray is not None:
                # מעקב LK סטנדרטי: הנקודות זוהו בפריים הקודם
                prev_corners = self._prev_corners
                active = (
                    prev_corners is not None and len(prev_corners) >= MIN_FEATURES
                    and brightness >= LOW_LIGHT_BRIGHTNESS
                )

                if active:
                    p1, st, _err = cv2.calcOpticalFlowPyrLK(
                        prev_gray, gray, prev_corners, None,
                        winSize=(21, 21), maxLevel=3,
                        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
                                  30, 0.01),
                    )
                    good = st.flatten() == 1
                    if int(good.sum()) >= MIN_FEATURES:
                        vectors = (p1[good] - prev_corners[good]).reshape(-1, 2)
                        # חציון = עמידות לפריטים חריגים (יד, חפץ נע וכו')
                        vx, vy = np.median(vectors, axis=0)
                        # החלקה אקספוננציאלית
                        self._smooth_x = 0.75 * self._smooth_x + 0.25 * float(vx)
                        self._smooth_y = 0.75 * self._smooth_y + 0.25 * float(vy)
                    else:
                        active = False
                if not active:
                    # דעיכה עדינה של הוקטור כשאין זיהוי
                    self._smooth_x *= 0.85
                    self._smooth_y *= 0.85

                self.motion.emit(self._smooth_x, self._smooth_y, active)

            # בחירת נקודות עניין חדשות על הפריים הנוכחי (בלי אזור הפנים)
            # לשימוש במעקב של האיטרציה הבאה
            feat_img = self._build_feature_image(gray)
            self._prev_corners = cv2.goodFeaturesToTrack(
                feat_img, maxCorners=120, qualityLevel=0.01,
                minDistance=10, blockSize=7,
            )

            prev_gray = gray

            # קצב דגימה קבוע
            elapsed = time.perf_counter() - loop_start
            if elapsed < frame_interval:
                time.sleep(frame_interval - elapsed)

        cap.release()
