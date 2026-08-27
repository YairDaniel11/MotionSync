"""
MotionSync - מסך ההגדרות.

רגישות תנועה, צבע/גודל/שקיפות הנקודות, מרווח הסריג ובחירת מצלמה.
"""
import cv2
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPixmap, QIcon
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QSpinBox, QDoubleSpinBox, QColorDialog,
)

from config import Config


def enumerate_cameras(max_index: int = 4):
    """סריקה מהירה של מצלמות זמינות (0..max_index-1)."""
    found = []
    for idx in range(max_index):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        ok = cap.isOpened()
        if ok:
            # ודא שאפשר לקרוא פריים (מצלמה "חסומה" נפתחת אך לא מחזירה תמונה)
            ok, _frame = cap.read()
        cap.release()
        if ok:
            found.append(idx)
    return found


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("MotionSync - הגדרות")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(380)

        layout = QFormLayout(self)

        # --- בחירת מצלמה ---
        self.camera_combo = QComboBox()
        cameras = enumerate_cameras()
        if cameras:
            for idx in cameras:
                self.camera_combo.addItem(f"מצלמה {idx}", idx)
            pos = cameras.index(config.camera_index) \
                if config.camera_index in cameras else 0
            self.camera_combo.setCurrentIndex(pos)
        else:
            self.camera_combo.addItem("לא זוהו מצלמות", -1)
            self.camera_combo.setEnabled(False)
        layout.addRow("מצלמה:", self.camera_combo)

        # --- רגישות ---
        self.sensitivity_spin = QDoubleSpinBox()
        self.sensitivity_spin.setRange(0.1, 3.0)
        self.sensitivity_spin.setSingleStep(0.1)
        self.sensitivity_spin.setValue(config.sensitivity)
        layout.addRow("רגישות תנועה:", self.sensitivity_spin)

        # --- צבע ---
        self.color = QColor(config.dot_color)
        self.color_btn = QPushButton()
        self.color_btn.setFixedWidth(60)
        self._update_color_btn()
        self.color_btn.clicked.connect(self._pick_color)
        layout.addRow("צבע הנקודות:", self.color_btn)

        # --- התאמת צבע אוטומטית ---
        self.adaptive_check = QCheckBox(
            "התאמה אוטומטית: שחור על רקע בהיר, לבן על רקע כהה"
        )
        self.adaptive_check.setChecked(config.adaptive_color)
        layout.addRow("", self.adaptive_check)

        # --- גודל ---
        self.size_spin = QSpinBox()
        self.size_spin.setRange(2, 12)
        self.size_spin.setValue(config.dot_size)
        layout.addRow("גודל נקודה (px):", self.size_spin)

        # --- שקיפות ---
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(5, 100)
        self.opacity_slider.setValue(int(config.dot_opacity * 100))
        self.opacity_label = QLabel(f"{self.opacity_slider.value()}%")
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_label.setText(f"{v}%")
        )
        row = QHBoxLayout()
        row.addWidget(self.opacity_slider)
        row.addWidget(self.opacity_label)
        layout.addRow("שקיפות:", row)

        # --- מרווח בין נקודות ---
        self.spacing_spin = QSpinBox()
        self.spacing_spin.setRange(40, 200)
        self.spacing_spin.setValue(config.dot_spacing)
        layout.addRow("מרווח בין נקודות (px):", self.spacing_spin)

        # --- כפתורי אישור/ביטול ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Ok).setText("אישור")
        buttons.button(QDialogButtonBox.Cancel).setText("ביטול")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _update_color_btn(self):
        pix = QPixmap(24, 24)
        pix.fill(self.color)
        self.color_btn.setIcon(QIcon(pix))

    def _pick_color(self):
        chosen = QColorDialog.getColor(self.color, self, "בחירת צבע")
        if chosen.isValid():
            self.color = chosen
            self._update_color_btn()

    def apply_to_config(self) -> None:
        self.config.camera_index = self.camera_combo.currentData() or 0
        self.config.sensitivity = float(self.sensitivity_spin.value())
        self.config.dot_color = self.color.name()
        self.config.adaptive_color = self.adaptive_check.isChecked()
        self.config.dot_size = int(self.size_spin.value())
        self.config.dot_opacity = self.opacity_slider.value() / 100.0
        self.config.dot_spacing = int(self.spacing_spin.value())
        self.config.save()
