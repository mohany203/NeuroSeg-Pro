from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                                 QPushButton, QLabel, QFrame, QStackedWidget, QApplication)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from app.ui.dashboard import DashboardWidget
from app.ui.viewer_widget import ViewerWidget
from app.ui.settings_widget import SettingsWidget
from app.ui.theme import apply_theme
from app.core.loader import NiftiLoader

from app.ui.settings import Settings

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.sidebar_expanded_width = 260
        self.sidebar_collapsed_width = 76
        self.sidebar_collapsed = bool(self.settings.get("sidebar_collapsed") or False)
        self.setWindowTitle("Brain Tumor Segmentation Pro")
        self.resize(1280, 850) # Slightly larger default
        
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        # Main Container (HBox: Sidebar | Content)
        # Central Widget Layout
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
        
        # Top Header (for Toggle Button)
        self.setup_header()
        
        # Content Area
        self.content_area = QStackedWidget()
        self.right_layout.addWidget(self.content_area)
        
        # Add Right Container to Main Layout
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
        
        # Default Logic
        self.current_page_index = 0

    def setup_header(self):
        self.header_frame = QFrame()
        self.header_frame.setFixedHeight(50)
        self.header_frame.setStyleSheet("background-color: transparent;") 
        hl = QHBoxLayout(self.header_frame)
        hl.setContentsMargins(10, 0, 10, 0)
        
        # Sidebar Toggle Button
        self.btn_toggle_sidebar = QPushButton("☰")
        self.btn_toggle_sidebar.setFixedSize(40, 40)
        self.btn_toggle_sidebar.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_sidebar.setToolTip("Toggle Sidebar")
        self.btn_toggle_sidebar.clicked.connect(self.toggle_sidebar)
        
        # Use theme palette for color
        from app.ui.theme import get_theme_palette
        c = get_theme_palette()
        
        self.btn_toggle_sidebar.setStyleSheet(f"""
            QPushButton {{
                background: transparent; 
                border: none; 
                font-size: 24px; 
                color: {c["PRIMARY"]};
            }}
            QPushButton:hover {{ background: {c["SURFACE_LIGHT"]}; border-radius: 5px; }}
        """)
        
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
            self.title_label.setVisible(False)
            self.btn_toggle_sidebar.setText("☷")
            for btn in [self.btn_dashboard, self.btn_viewer, self.btn_help, self.btn_settings]:
                btn.setText("")
                btn.setToolTip(btn.property("full_text"))
        else:
            self.sidebar.setFixedWidth(self.sidebar_expanded_width)
            self.title_label.setVisible(True)
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
        self.settings.add_recent(file_path) # Update history
        
        try:
            if file_type == 'folder':
                # Multi-modal loading
                modalities = NiftiLoader.load_patient_folder(file_path)
                self.viewer_page.load_patient_data(modalities) # New method for dict input
            else:
                # Legacy single file loading
                data, affine, header = NiftiLoader.load_file(file_path)
                is_mask = (file_type == 'mask')
                self.viewer_page.load_data(data, affine, is_mask=is_mask)
            
            self.switch_page(1) # Go to viewer
        except Exception as e:
            # Simple error dialog/print for now
            print(f"Error loading file: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Load Error", f"Could not load data:\n{e}")

    def refresh_theme(self):
        """Re-applies the theme to the entire application and updates widgets."""
        app = QApplication.instance()
        apply_theme(app)
        self.viewer_page.refresh_theme()
        
        # Update dynamic inline styles in MainWindow
        c = get_theme_palette()
        # Header Button
        self.btn_toggle_sidebar.setStyleSheet(f"""
            QPushButton {{
                background: transparent; 
                border: none; 
                font-size: 24px; 
                color: {c["PRIMARY"]};
            }}
            QPushButton:hover {{ background: {c["SURFACE_LIGHT"]}; border-radius: 5px; }}
        """)
        # Title Label
        if hasattr(self, 'title_label'):
             self.title_label.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {c['PRIMARY']}; letter-spacing: 2px;")


    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(self.sidebar_expanded_width)
        
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(20, 40, 20, 20)
        self.sidebar_layout.setSpacing(10)
        
        # App Title/Logo
        # Use Dynamic Theme Color
        from app.ui.theme import get_theme_palette
        c = get_theme_palette()
        
        self.title_label = QLabel("NEURO SEG")
        self.title_label.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {c['PRIMARY']}; letter-spacing: 2px;")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.sidebar_layout.addWidget(self.title_label)
        
        self.sidebar_layout.addSpacing(30)
        
        # Navigation Buttons
        self.btn_dashboard = self.create_nav_button("Dashboard", "home")
        self.btn_viewer = self.create_nav_button("3D Viewer", "view_in_ar")
        self.btn_settings = self.create_nav_button("Settings", "settings")
        self.btn_help = self.create_nav_button("Tutorial", "help_outline")
        
        self.sidebar_layout.addWidget(self.btn_dashboard)
        self.sidebar_layout.addWidget(self.btn_viewer)
        self.sidebar_layout.addStretch() # Push settings to bottom
        self.sidebar_layout.addWidget(self.btn_help)
        self.sidebar_layout.addWidget(self.btn_settings)
        
        self.main_layout.addWidget(self.sidebar)
        
        # Connections
        self.btn_dashboard.clicked.connect(lambda: self.switch_page(0))
        self.btn_viewer.clicked.connect(lambda: self.switch_page(1))
        self.btn_settings.clicked.connect(lambda: self.switch_page(2))
        self.btn_help.clicked.connect(self.show_tutorial)

        self.apply_sidebar_state()

    def show_tutorial(self):
        from app.ui.tutorial_dialog import TutorialDialog
        dlg = TutorialDialog(self)
        dlg.exec_()

    def create_nav_button(self, text, icon_name=None):
        btn = QPushButton(text)
        btn.setProperty("full_text", text)
        btn.setCheckable(True)
        btn.setFixedHeight(50)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setObjectName("NavButton") 
        return btn

    def switch_page(self, index):
        self.content_area.setCurrentIndex(index)
        
        if index == 0:
            self.dashboard_page.refresh()
        
        # Update Button States
        self.btn_dashboard.setChecked(index == 0)
        self.btn_viewer.setChecked(index == 1)
        self.btn_settings.setChecked(index == 2)
