import sys
from PySide6.QtWidgets import QApplication
from app.main_window import MainWindow
from app.styles import APP_STYLESHEET

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Preparación Plena Studio")
    app.setOrganizationName("Preparación Plena")
    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
