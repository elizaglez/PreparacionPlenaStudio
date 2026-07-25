from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME, APP_VERSION
from app.pages.history_page import HistoryPage
from app.pages.home_page import HomePage
from app.pages.master_editor_page import MasterEditorPage
from app.pages.new_project_page import NewProjectPage
from app.pages.project_workspace import ProjectWorkspace
from app.pages.settings_page import SettingsPage
from app.project_service import ProjectError, load_project
from app.storage import ensure_app_data


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ensure_app_data()
        self.current_project = None
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1320, 820)
        self.setMinimumSize(980, 650)
        self.build_actions()
        self.build_menu()
        self.build_ui()
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Listo")

    def build_actions(self):
        self.new_action = QAction("Nuevo proyecto", self)
        self.new_action.setShortcut("Ctrl+N")
        self.new_action.triggered.connect(lambda: self.navigate("new"))

        self.open_action = QAction("Abrir proyecto", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_dialog)

        self.exit_action = QAction("Salir", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)

        self.about_action = QAction("Acerca de", self)
        self.about_action.triggered.connect(self.about)

    def build_menu(self):
        file_menu = self.menuBar().addMenu("Archivo")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        help_menu = self.menuBar().addMenu("Ayuda")
        help_menu.addAction(self.about_action)

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(245)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 22, 16, 16)

        brand = QLabel("Preparación Plena\nStudio")
        brand.setObjectName("BrandTitle")
        sidebar_layout.addWidget(brand)
        sidebar_layout.addSpacing(18)

        self.nav = QListWidget()
        self.nav.setFrameShape(QFrame.NoFrame)
        items = [
            ("Inicio", "home"),
            ("Nuevo proyecto", "new"),
            ("Proyecto abierto", "workspace"),
            ("Editor del MASTER", "editor"),
            ("Historial", "history"),
            ("Configuración", "settings"),
        ]
        for title, key in items:
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, key)
            self.nav.addItem(item)

        self.nav.currentItemChanged.connect(self.nav_changed)
        sidebar_layout.addWidget(self.nav, 1)

        version = QLabel(f"Versión {APP_VERSION}")
        version.setObjectName("Muted")
        sidebar_layout.addWidget(version)

        self.stack = QStackedWidget()
        self.pages = {
            "home": HomePage(),
            "new": NewProjectPage(),
            "workspace": ProjectWorkspace(),
            "editor": MasterEditorPage(),
            "history": HistoryPage(),
            "settings": SettingsPage(),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)

        self.pages["home"].navigate.connect(self.home_navigate)
        self.pages["new"].project_created.connect(self.project_loaded)
        self.pages["history"].open_project.connect(self.open_path)

        root.addWidget(sidebar)
        root.addWidget(self.stack, 1)
        self.nav.setCurrentRow(0)

    def nav_changed(self, current, previous):
        if current:
            self.navigate(current.data(Qt.UserRole), False)

    def navigate(self, page, update=True):
        if page not in self.pages:
            return

        if page == "editor":
            if not self.current_project:
                QMessageBox.information(
                    self,
                    "Editor del MASTER",
                    "Abre un proyecto y genera el MASTER antes de entrar al editor.",
                )
                self.navigate("workspace" if self.current_project else "home")
                return
            self.pages["editor"].set_project(self.current_project)

        self.stack.setCurrentWidget(self.pages[page])

        if page == "history":
            self.pages["history"].refresh()
        if page == "settings":
            self.pages["settings"].reload()

        if update:
            for index in range(self.nav.count()):
                if self.nav.item(index).data(Qt.UserRole) == page:
                    self.nav.setCurrentRow(index)
                    break

    def home_navigate(self, page):
        if page == "open":
            self.open_dialog()
        else:
            self.navigate(page)

    def open_dialog(self):
        selected = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta del proyecto",
        )
        if selected:
            self.open_path(selected)

    def open_path(self, path):
        try:
            project = load_project(path)
        except ProjectError as exc:
            QMessageBox.warning(self, "No se pudo abrir", str(exc))
            return
        self.project_loaded(project)

    def project_loaded(self, project):
        self.current_project = project
        self.pages["workspace"].set_project(project)
        self.pages["history"].refresh()
        self.navigate("workspace")
        self.statusBar().showMessage(
            "Proyecto abierto: " + project.name,
            5000,
        )

    def about(self):
        QMessageBox.information(
            self,
            "Acerca de",
            (
                f"{APP_NAME}\nVersión {APP_VERSION}\n\n"
                "Aplicación de escritorio con metodología PPA."
            ),
        )
