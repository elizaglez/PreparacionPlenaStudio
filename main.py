import sys

from dotenv import load_dotenv
from PySide6.QtWidgets import QApplication

from app.config import ROOT_DIR
from app.main_window import MainWindow
from app.styles import APP_STYLESHEET


def main():
    load_dotenv(ROOT_DIR / ".env")
    app = QApplication(sys.argv)
    app.setApplicationName("Preparación Plena Studio")
    app.setOrganizationName("Preparación Plena")
    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
