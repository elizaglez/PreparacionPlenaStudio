from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QFrame,QLabel,QListWidget,QListWidgetItem,QStackedWidget,QFileDialog,QMessageBox,QStatusBar
from app.config import APP_NAME,APP_VERSION
from app.storage import ensure_app_data
from app.project_service import load_project,ProjectError
from app.pages.home_page import HomePage
from app.pages.new_project_page import NewProjectPage
from app.pages.history_page import HistoryPage
from app.pages.settings_page import SettingsPage
from app.pages.project_workspace import ProjectWorkspace

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        ensure_app_data()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1320,820)
        self.setMinimumSize(980,650)
        self.build_actions(); self.build_menu(); self.build_ui()
        self.setStatusBar(QStatusBar()); self.statusBar().showMessage("Listo")

    def build_actions(self):
        self.new_action=QAction("Nuevo proyecto",self); self.new_action.setShortcut("Ctrl+N"); self.new_action.triggered.connect(lambda:self.navigate("new"))
        self.open_action=QAction("Abrir proyecto",self); self.open_action.setShortcut("Ctrl+O"); self.open_action.triggered.connect(self.open_dialog)
        self.exit_action=QAction("Salir",self); self.exit_action.setShortcut("Ctrl+Q"); self.exit_action.triggered.connect(self.close)
        self.about_action=QAction("Acerca de",self); self.about_action.triggered.connect(self.about)

    def build_menu(self):
        f=self.menuBar().addMenu("Archivo"); f.addAction(self.new_action); f.addAction(self.open_action); f.addSeparator(); f.addAction(self.exit_action)
        h=self.menuBar().addMenu("Ayuda"); h.addAction(self.about_action)

    def build_ui(self):
        central=QWidget(); self.setCentralWidget(central)
        root=QHBoxLayout(central); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        sidebar=QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(245)
        sl=QVBoxLayout(sidebar); sl.setContentsMargins(16,22,16,16)
        brand=QLabel("Preparación Plena\nStudio"); brand.setObjectName("BrandTitle"); sl.addWidget(brand); sl.addSpacing(18)
        self.nav=QListWidget(); self.nav.setFrameShape(QFrame.NoFrame)
        for title,key in [("Inicio","home"),("Nuevo proyecto","new"),("Proyecto abierto","workspace"),("Historial","history"),("Configuración","settings")]:
            item=QListWidgetItem(title); item.setData(Qt.UserRole,key); self.nav.addItem(item)
        self.nav.currentItemChanged.connect(self.nav_changed); sl.addWidget(self.nav,1)
        version=QLabel(f"Versión {APP_VERSION}"); version.setObjectName("Muted"); sl.addWidget(version)
        self.stack=QStackedWidget()
        self.pages={"home":HomePage(),"new":NewProjectPage(),"workspace":ProjectWorkspace(),"history":HistoryPage(),"settings":SettingsPage()}
        for page in self.pages.values(): self.stack.addWidget(page)
        self.pages["home"].navigate.connect(self.home_navigate)
        self.pages["new"].project_created.connect(self.project_loaded)
        self.pages["history"].open_project.connect(self.open_path)
        root.addWidget(sidebar); root.addWidget(self.stack,1)
        self.nav.setCurrentRow(0)

    def nav_changed(self,current,previous):
        if current: self.navigate(current.data(Qt.UserRole),False)

    def navigate(self,page,update=True):
        if page not in self.pages: return
        self.stack.setCurrentWidget(self.pages[page])
        if page=="history": self.pages["history"].refresh()
        if page=="settings": self.pages["settings"].reload()
        if update:
            for i in range(self.nav.count()):
                if self.nav.item(i).data(Qt.UserRole)==page:
                    self.nav.setCurrentRow(i); break

    def home_navigate(self,page):
        self.open_dialog() if page=="open" else self.navigate(page)

    def open_dialog(self):
        selected=QFileDialog.getExistingDirectory(self,"Seleccionar carpeta del proyecto")
        if selected: self.open_path(selected)

    def open_path(self,path):
        try: p=load_project(path)
        except ProjectError as exc:
            QMessageBox.warning(self,"No se pudo abrir",str(exc)); return
        self.project_loaded(p)

    def project_loaded(self,p):
        self.pages["workspace"].set_project(p); self.pages["history"].refresh(); self.navigate("workspace")
        self.statusBar().showMessage("Proyecto abierto: "+p.get("name",""),5000)

    def about(self):
        QMessageBox.information(self,"Acerca de",f"{APP_NAME}\nVersión {APP_VERSION}\n\nAplicación de escritorio con metodología PPA.")
