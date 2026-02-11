from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QPushButton, QFrame, QFileDialog, QListWidget, QGridLayout, QScrollArea, QSizePolicy, QListWidgetItem)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFont, QResizeEvent
from app.ui.settings import Settings

class DashboardWidget(QWidget):
    file_loaded = pyqtSignal(str, str) # Signal to emit when a file is selected (path, type='mri'|'mask')
    recent_file_clicked = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.settings = Settings()
        # Scroll Area for flexibility
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.content_widget = QWidget()
        self.layout = QVBoxLayout(self.content_widget)
        # Dynamic margins - Reduced for better fit on laptop screens
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(30)
        self.content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.scroll.setWidget(self.content_widget)
        
        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.addWidget(self.scroll)

        # Welcome Section
        self.setup_header()
        
        # Actions Grid
        self.setup_actions()
        
        # Recent Files Section
        self.setup_recent()
        
        self.layout.addStretch()

    def setup_header(self):
        header_container = QWidget()
        l = QVBoxLayout(header_container)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(15)
        
        title = QLabel("Welcome to NeuroSeg Pro")
        title.setObjectName("WelcomeTitle") # Themed in theme.py
        
        subtitle = QLabel("Advanced Brain Tumor Segmentation & 3D Visualization")
        subtitle.setObjectName("WelcomeSubtitle") # Themed in theme.py
        
        l.addWidget(title)
        l.addWidget(subtitle)
        
        self.layout.addWidget(header_container)

    def setup_actions(self):
        # Container to center the grid
        grid_container = QWidget()
        grid = QGridLayout(grid_container)
        grid.setSpacing(20) # Reduced from 40
        grid.setContentsMargins(0,0,0,0)
        
        # Load Scan Card
        self.load_card = self.create_action_card(
            "Load MRI Scan", 
            "Import a NIfTI (.nii) file to begin 3D volumetric analysis and visualization.",
            "Open Scan",
            lambda: self.browse_file('mri')
        )
        
        # Load Mask Card
        self.mask_card = self.create_action_card(
            "Load Segmentation Mask", 
            "Import a binary mask to overlay on the MRI scan for comparison.",
            "Load Mask",
            lambda: self.browse_file('mask')
        )
        
        # Batch Process (Placeholder)
        self.batch_card = self.create_action_card(
            "Batch Processing", 
            "Run segmentation on multiple files automatically (Coming Soon).",
            "Batch Run",
            None
        )
        self.batch_card.setObjectName("CardDisabled")
        self.batch_card.setEnabled(False) 

        # Add to grid with column stretch to prevent extreme width but allow growth
        grid.addWidget(self.load_card, 0, 0)
        grid.addWidget(self.mask_card, 0, 1)
        
        # New: Patient Folder Card
        self.patient_card = self.create_action_card(
            "Open Patient Folder",
            "Load a folder containing multiple MRI modalities (T1, T2, FLAIR, T1ce).",
            "Open Folder",
            self.browse_folder
        )
        grid.addWidget(self.patient_card, 1, 0, 1, 2) # Span 2 columns
        
        # grid.addWidget(self.batch_card, 0, 2) # Simplify grid for now if wanted, or keep
        # grid.addWidget(self.batch_card, 0, 2)
        
        # Ensure columns share space equally
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        # grid.setColumnStretch(2, 1)
        
        self.layout.addWidget(grid_container)

    def setup_recent(self):
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(20)
        
        lbl = QLabel("Recent Files")
        lbl.setObjectName("SectionHeader")
        
        self.recent_list = QListWidget()
        self.recent_list.setFixedHeight(250) 
        self.recent_list.setObjectName("RecentList") # For styling
        
        # Populate
        self.refresh_recent_list()
        
        self.recent_list.itemClicked.connect(self.on_recent_clicked)
        
        l.addWidget(lbl)
        l.addWidget(self.recent_list)
        
        self.layout.addWidget(container)

    def refresh_recent_list(self):
        self.recent_list.clear()
        recents = self.settings.get("recent_files")
        
        if not recents:
            item = QListWidgetItem("No recent files.")
            item.setFlags(Qt.NoItemFlags)
            self.recent_list.addItem(item)
        else:
            for path in recents:
                item = QListWidgetItem(path)
                item.setToolTip(path)
                self.recent_list.addItem(item)

    def on_recent_clicked(self, item):
        path = item.text()
        if path and path != "No recent files.":
             self.recent_file_clicked.emit(path)
             
    def refresh(self):
        """Called when dashboard is shown to update dynamic content."""
        self.refresh_recent_list()

    def create_action_card(self, title, desc, btn_text, callback):
        card = QFrame()
        card.setObjectName("Card")
        # Use Minimum Size instead of Fixed to allow expansion
        card.setMinimumSize(250, 250) # Reduced to allow fit on smaller screens
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Allow vertical expansion too
        
        l = QVBoxLayout(card)
        l.setContentsMargins(30, 30, 30, 30) # Reduced cushion
        l.setSpacing(15)
        
        # Icon
        icon_lbl = QLabel("📂" if "Scan" in title else "🎭" if "Mask" in title else "⚡")
        icon_lbl.setObjectName("CardIcon")
        icon_lbl.setAlignment(Qt.AlignLeft)
        
        title_lbl = QLabel(title)
        title_lbl.setObjectName("CardTitle")
        title_lbl.setWordWrap(True)
        
        desc_lbl = QLabel(desc)
        desc_lbl.setObjectName("CardDesc")
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        btn = QPushButton(btn_text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(50) # Taller button
        if callback:
            btn.clicked.connect(callback)
        else:
            btn.setEnabled(False)
        
        l.addWidget(icon_lbl)
        l.addWidget(title_lbl)
        l.addWidget(desc_lbl)
        l.addStretch()
        l.addWidget(btn)
        
        return card

    def browse_file(self, file_type):
        title = "Open MRI Scan" if file_type == 'mri' else "Open Segmentation Mask"
        file_path, _ = QFileDialog.getOpenFileName(
            self, title, "", "NIfTI Files (*.nii *.nii.gz)"
        )
        if file_path:
            self.file_loaded.emit(file_path, file_type)

    def browse_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Patient Folder")
        if folder_path:
            self.file_loaded.emit(folder_path, 'folder')
