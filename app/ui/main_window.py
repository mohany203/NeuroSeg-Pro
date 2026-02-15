from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                                 QPushButton, QLabel, QFrame, QStackedWidget, QApplication)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from app.ui.dashboard import DashboardWidget
from app.ui.viewer_widget import ViewerWidget
from app.ui.settings_widget import SettingsWidget
from app.ui.theme import apply_theme, get_theme_palette, scaled
from app.core.loader import NiftiLoader

from app.ui.settings import Settings

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.sidebar_expanded_width = scaled(220)
        self.sidebar_collapsed_width = scaled(60)
        self.sidebar_collapsed = bool(self.settings.get("sidebar_collapsed") or False)
        self.setWindowTitle("Brain Tumor Segmentation Pro")
        self.resize(scaled(1280), scaled(850))
        
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Sidebar
        self.setup_sidebar()
        
        # Right Side Container (VBox: Header | Content Area)
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)
        
        # Top Header
        self.setup_header()
        
        # Apply sidebar state AFTER both sidebar and header are created
        self.apply_sidebar_state()
        
        # Content Area
        self.content_area = QStackedWidget()
        self.right_layout.addWidget(self.content_area)
        
        self.main_layout.addWidget(self.right_container)
        
        # Add Pages
        self.dashboard_page = DashboardWidget()
        self.viewer_page = ViewerWidget()
        self.settings_page = SettingsWidget()
        
        self.content_area.addWidget(self.dashboard_page)
        self.content_area.addWidget(self.viewer_page)
        self.content_area.addWidget(self.settings_page)
        
        # Signal Connections
        self.dashboard_page.file_loaded.connect(self.on_file_loaded)
        self.dashboard_page.recent_file_clicked.connect(self.on_recent_file_clicked)
        self.settings_page.settings_saved.connect(self.refresh_theme)
        self.settings_page.models_changed.connect(self.viewer_page.populate_models)
        
        # Default Logic
        self.current_page_index = 0

    def _header_toggle_style(self):
        c = get_theme_palette()
        fs = scaled(24)
        return f"""
            QPushButton {{
                background: transparent; 
                border: none; 
                font-size: {fs}px; 
                color: {c["PRIMARY"]};
            }}
            QPushButton:hover {{ 
                background: {c["SURFACE_LIGHT"]}; 
                border-radius: {scaled(8)}px; 
            }}
        """

    def setup_header(self):
        c = get_theme_palette()
        self.header_frame = QFrame()
        self.header_frame.setFixedHeight(scaled(50))
        self.header_frame.setStyleSheet(f"background-color: {c['HEADER_BG']}; border-bottom: 1px solid {c['BORDER']};") 
        hl = QHBoxLayout(self.header_frame)
        hl.setContentsMargins(scaled(10), 0, scaled(10), 0)
        
        # Sidebar Toggle Button
        self.btn_toggle_sidebar = QPushButton("☰")
        self.btn_toggle_sidebar.setFixedSize(scaled(40), scaled(40))
        self.btn_toggle_sidebar.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_sidebar.setToolTip("Toggle Sidebar")
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)
        self.btn_toggle_sidebar.setStyleSheet(self._header_toggle_style())
        
        hl.addWidget(self.btn_toggle_sidebar)
        hl.addStretch()
        
        self.right_layout.addWidget(self.header_frame)

    def toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        self.settings.set("sidebar_collapsed", self.sidebar_collapsed)
        self.apply_sidebar_state()

    def apply_sidebar_state(self):
        if self.sidebar_collapsed:
            self.sidebar.setFixedWidth(self.sidebar_collapsed_width)
            if hasattr(self, 'title_label'):
                self.title_label.setVisible(False)
            if hasattr(self, 'btn_toggle_sidebar'):
                self.btn_toggle_sidebar.setText("☷")
            for btn in [self.btn_dashboard, self.btn_viewer, self.btn_help, self.btn_settings]:
                btn.setText("")
                btn.setToolTip(btn.property("full_text"))
        else:
            self.sidebar.setFixedWidth(self.sidebar_expanded_width)
            if hasattr(self, 'title_label'):
                self.title_label.setVisible(True)
            if hasattr(self, 'btn_toggle_sidebar'):
                self.btn_toggle_sidebar.setText("☰")
            for btn in [self.btn_dashboard, self.btn_viewer, self.btn_help, self.btn_settings]:
                btn.setText(btn.property("full_text"))
                btn.setToolTip("")

    def on_recent_file_clicked(self, file_path):
        import os
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
            
            self.switch_page(1)
        except Exception as e:
            print(f"Error loading file: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Load Error", f"Could not load data:\n{e}")

    def refresh_theme(self):
        """Re-applies the theme to the entire application and updates widgets."""
        app = QApplication.instance()
        from app.ui.theme import get_dpi_scale
        apply_theme(app, dpi_scale=get_dpi_scale())
        self.viewer_page.refresh_theme()
        
        # Update dynamic inline styles
        c = get_theme_palette()
        self.btn_toggle_sidebar.setStyleSheet(self._header_toggle_style())
        self.header_frame.setStyleSheet(f"background-color: {c['HEADER_BG']}; border-bottom: 1px solid {c['BORDER']};")
        
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(
                f"font-size: {scaled(26)}px; font-weight: bold; color: {c['PRIMARY']}; letter-spacing: 2px;"
            )

    def setup_sidebar(self):
        c = get_theme_palette()
        
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(self.sidebar_expanded_width)
        
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(scaled(14), scaled(30), scaled(14), scaled(14))
        self.sidebar_layout.setSpacing(scaled(6))
        
        # App Title
        self.title_label = QLabel("NEURO SEG")
        self.title_label.setStyleSheet(
            f"font-size: {scaled(22)}px; font-weight: bold; color: {c['PRIMARY']}; letter-spacing: 1px;"
        )
        self.title_label.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(self.title_label)
        
        self.sidebar_layout.addSpacing(scaled(20))
        
        # Navigation Buttons
        self.btn_dashboard = self.create_nav_button("Dashboard", "home")
        self.btn_viewer = self.create_nav_button("3D Viewer", "view_in_ar")
        self.btn_settings = self.create_nav_button("Settings", "settings")
        self.btn_help = self.create_nav_button("Tutorial", "help_outline")
        
        self.sidebar_layout.addWidget(self.btn_dashboard)
        self.sidebar_layout.addWidget(self.btn_viewer)
        self.sidebar_layout.addStretch()
        self.sidebar_layout.addWidget(self.btn_help)
        self.sidebar_layout.addWidget(self.btn_settings)
        
        self.main_layout.addWidget(self.sidebar)
        
        # Connections
        self.btn_dashboard.clicked.connect(lambda: self.switch_page(0))
        self.btn_viewer.clicked.connect(lambda: self.switch_page(1))
        self.btn_settings.clicked.connect(lambda: self.switch_page(2))
        self.btn_help.clicked.connect(self.show_tutorial)

    def show_tutorial(self):
        from app.ui.tutorial_dialog import TutorialDialog
        dlg = TutorialDialog(self)
        dlg.exec_()

    def create_nav_button(self, text, icon_name=None):
        btn = QPushButton(text)
        btn.setProperty("full_text", text)
        btn.setCheckable(True)
        btn.setFixedHeight(scaled(42))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setObjectName("NavButton") 
        return btn

    def switch_page(self, index):
        self.content_area.setCurrentIndex(index)
        
        if index == 0:
            self.dashboard_page.refresh()
        
        self.btn_dashboard.setChecked(index == 0)
        self.btn_viewer.setChecked(index == 1)
        self.btn_settings.setChecked(index == 2)
