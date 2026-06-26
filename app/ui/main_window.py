from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                               QPushButton, QLabel, QFrame, QStackedWidget, QApplication, QFileDialog, QDialog)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QFont
from app.ui.dashboard import DashboardWidget
from app.ui.viewer_widget import ViewerWidget
from app.ui.settings_widget import SettingsWidget
from app.ui.theme import apply_theme, get_theme_palette, scaled
from app.core.loader import NiftiLoader
from app.ui.settings import Settings
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.setWindowTitle("NeuroSeg-Pro Volumetric Clinical Platform")
        self.resize(scaled(1380), scaled(900))
        
        # Central Container
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Top Header Strip
        self.setup_header()
        
        # Content Area Stack
        self.content_area = QStackedWidget()
        self.main_layout.addWidget(self.content_area)
        
        # Pages
        self.dashboard_page = DashboardWidget()
        self.viewer_page = ViewerWidget()
        
        self.content_area.addWidget(self.dashboard_page) # Index 0
        self.content_area.addWidget(self.viewer_page)    # Index 1
        
        # Signal Connections
        self.dashboard_page.file_loaded.connect(self.on_file_loaded)
        self.dashboard_page.recent_file_clicked.connect(self.on_recent_file_clicked)
        
        # Land directly on the 3D Viewer page (Index 1) to match professional clinical workflow
        self.content_area.setCurrentIndex(1)
        self.refresh_theme()

    def setup_header(self):
        c = get_theme_palette()
        self.header_frame = QFrame()
        self.header_frame.setFixedHeight(scaled(54))
        self.header_frame.setStyleSheet(f"background-color: {c['HEADER_BG']}; border-bottom: 1px solid {c['BORDER']};") 
        
        hl = QHBoxLayout(self.header_frame)
        hl.setContentsMargins(scaled(16), 0, scaled(16), 0)
        hl.setSpacing(scaled(10))
        
        # Title Logo
        self.logo_label = QLabel("🧠  NeuroSeg-Pro")
        self.logo_label.setStyleSheet(f"font-size: {scaled(20)}px; font-weight: 800; color: {c['PRIMARY']}; letter-spacing: 0.5px;")
        hl.addWidget(self.logo_label)
        
        hl.addStretch()
        
        # Header Action Buttons
        btn_open = self._create_header_btn("📂 Open Study", self.open_study_dialog, c)
        hl.addWidget(btn_open)
        
        btn_export = self._create_header_btn("📄 Export Report", lambda: self.viewer_page.export_mask(), c)
        hl.addWidget(btn_export)
        
        btn_settings = self._create_header_btn("⚙️ Settings", self.show_settings_modal, c)
        hl.addWidget(btn_settings)
        
        btn_help = self._create_header_btn("❓ Help", self.show_tutorial, c)
        hl.addWidget(btn_help)
        
        btn_about = self._create_header_btn("ℹ️ About", self.show_about_dialog, c)
        hl.addWidget(btn_about)
        
        self.main_layout.addWidget(self.header_frame)

    def _create_header_btn(self, text, callback, c):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(scaled(34))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c['TEXT_PRIMARY']};
                border: none;
                border-radius: {scaled(6)}px;
                padding: {scaled(4)}px {scaled(14)}px;
                font-weight: 600;
                font-size: {scaled(13)}px;
            }}
            QPushButton:hover {{
                background-color: {c['SURFACE_LIGHT']};
                color: {c['PRIMARY']};
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def open_study_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "Select NIfTI Patient Folder")
        if folder:
            self.on_file_loaded(folder, 'folder')

    def show_settings_modal(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Preferences & AI Models")
        dlg.resize(scaled(900), scaled(700))
        c = get_theme_palette()
        dlg.setStyleSheet(f"background-color: {c['BACKGROUND']};")
        l = QVBoxLayout(dlg)
        l.setContentsMargins(0, 0, 0, 0)
        
        sw = SettingsWidget()
        sw.settings_saved.connect(self.refresh_theme)
        sw.models_changed.connect(self.viewer_page.populate_models)
        sw.settings_saved.connect(dlg.accept)
        l.addWidget(sw)
        dlg.exec_()

    def show_tutorial(self):
        from app.ui.tutorial_dialog import TutorialDialog
        dlg = TutorialDialog(self)
        dlg.exec_()

    def show_about_dialog(self):
        from app.ui.about_dialog import AboutDialog
        dlg = AboutDialog(self)
        dlg.exec_()

    def on_recent_file_clicked(self, file_path):
        file_type = 'folder' if os.path.isdir(file_path) else 'mri'
        self.on_file_loaded(file_path, file_type)

    def on_file_loaded(self, file_path, file_type):
        print(f"Loading {file_type}: {file_path}")
        self.settings.add_recent(file_path)
        
        try:
            if file_type == 'folder':
                modalities = NiftiLoader.load_patient_folder(file_path)
                self.viewer_page.load_patient_data(modalities)
            else:
                data, affine, header = NiftiLoader.load_file(file_path)
                is_mask = (file_type == 'mask')
                self.viewer_page.load_data(data, affine, is_mask=is_mask)
            
            self.content_area.setCurrentIndex(1)
        except Exception as e:
            print(f"Error loading file: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Load Error", f"Could not load data:\n{e}")

    def refresh_theme(self):
        app = QApplication.instance()
        from app.ui.theme import get_dpi_scale
        apply_theme(app, dpi_scale=get_dpi_scale())
        self.viewer_page.refresh_theme()
        
        c = get_theme_palette()
        if hasattr(self, 'header_frame'):
            self.header_frame.setStyleSheet(f"background-color: {c['HEADER_BG']}; border-bottom: 1px solid {c['BORDER']};")
        if hasattr(self, 'logo_label'):
            self.logo_label.setStyleSheet(f"font-size: {scaled(20)}px; font-weight: 800; color: {c['PRIMARY']}; letter-spacing: 0.5px;")
