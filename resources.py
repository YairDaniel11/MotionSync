"""
MotionSync - איתור קבצי משאבים (אייקונים) גם בהרצה רגילה וגם בתוך PyInstaller.

PyInstaller פורק את הקבצים המצורפים לתיקייה זמנית שנתיבה ב-sys._MEIPASS,
ולכן אי אפשר להסתמך על מיקום קובץ המקור.
"""
import os
import sys

from PyQt5.QtGui import QIcon


def resource_path(relative: str) -> str:
    """נתיב מלא למשאב, יחסית לשורש הפרויקט או לחבילה הארוזה."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def app_icon() -> QIcon:
    """האייקון הרשמי של MotionSync. QIcon ריק אם הקובץ חסר משום מה."""
    return QIcon(resource_path(os.path.join("assets", "icon.png")))
