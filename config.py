r"""
MotionSync - קונפיגורציה (שמירה/טעינה של הגדרות המשתמש).
ההגדרות נשמרות ב-JSON תחת %APPDATA%\MotionSync\config.json
"""
import json
import os
from dataclasses import dataclass, asdict, fields

CONFIG_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "MotionSync"
)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


@dataclass
class Config:
    camera_index: int = 0        # אינדקס המצלמה
    sensitivity: float = 1.0     # מכפיל רגישות תנועה (0.1 - 3.0)
    dot_color: str = "#FFFFFF"   # צבע הנקודות (כשההתאמה האוטומטית כבויה)
    adaptive_color: bool = True  # שחור על רקע בהיר / לבן על רקע כהה
    dot_size: int = 5            # רדיוס הנקודות בפיקסלים
    dot_opacity: float = 0.6     # שקיפות הנקודות (0.05 - 1.0)
    dot_spacing: int = 140       # מרווח בין נקודות בפיקסלים
    target_fps: int = 30         # קצב דגימת המצלמה

    @classmethod
    def load(cls) -> "Config":
        cfg = cls()
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                valid = {f.name for f in fields(cls)}
                for key, value in data.items():
                    if key in valid:
                        setattr(cfg, key, value)
        except (OSError, json.JSONDecodeError):
            # קובץ פגום -> ממשיכים עם ברירות מחדל
            pass
        return cfg

    def save(self) -> None:
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2, ensure_ascii=False)
        except OSError:
            pass
