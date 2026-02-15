from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QPushButton, QFrame, QFileDialog, QListWidget, QGridLayout, QScrollArea, QSizePolicy, QListWidgetItem, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFont, QResizeEvent, QColor
import os
from app.ui.settings import Settings
from app.ui.theme import get_theme_palette, scaled

class RecentFileItemWidget(QWidget):
    clicked = pyqtSignal(str)
    deleted = pyqtSignal(str)

    def __init__(self, path, timestamp):
        super().__init__()
        self.path = path
        
        c = get_theme_palette()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(scaled(10), scaled(5), scaled(10), scaled(5))
        layout.setSpacing(scaled(15))
        
        # Icon
        icon_lbl = QLabel("📄")
        icon_lbl.setStyleSheet(f"font-size: {scaled(20)}px;")
        layout.addWidget(icon_lbl)
        
        # Text Container
        text_layout = QVBoxLayout()
        text_layout.setSpacing(scaled(2))
        
        name_lbl = QLabel(os.path.basename(path))
        name_lbl.setStyleSheet(f"font-size: {scaled(14)}px; font-weight: bold; color: {c['TEXT_PRIMARY']};")
        
        # Shorten path for display if too long?
        display_path = path if len(path) < 50 else "..." + path[-47:]
        meta_lbl = QLabel(f"{display_path} • {timestamp}")
        meta_lbl.setStyleSheet(f"font-size: {scaled(11)}px; color: {c['TEXT_SECONDARY']};")
        
        text_layout.addWidget(name_lbl)
        text_layout.addWidget(meta_lbl)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # Delete Button
        del_btn = QPushButton("✕")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setFixedSize(scaled(24), scaled(24))
        del_btn.setStyleSheet(f"QPushButton {{ background: transparent; color: {c['TEXT_SECONDARY']}; border: none; font-weight: bold; border-radius: {scaled(12)}px; }} QPushButton:hover {{ background: {c['DANGER_BG']}; color: {c['DANGER_FG']}; }}")
        del_btn.clicked.connect(self.on_delete)
        layout.addWidget(del_btn)
        
    def mousePressEvent(self, event):
        self.clicked.emit(self.path)
        super().mousePressEvent(event)

    def on_delete(self):
        self.deleted.emit(self.path)


class DashboardWidget(QWidget):
    file_loaded = pyqtSignal(str, str)
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
        self.layout.setContentsMargins(scaled(40), scaled(40), scaled(40), scaled(40))
        self.layout.setSpacing(scaled(30))
        self.content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.scroll.setWidget(self.content_widget)
        
        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
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
        l.setContentsMargins(0, scaled(10), 0, scaled(20))
        l.setSpacing(scaled(8))
        
        c = get_theme_palette()
        
        # Welcome Title
        title = QLabel("Welcome to NeuroSeg Pro")
        title.setStyleSheet(
            f"font-size: {scaled(36)}px; font-weight: 800; color: {c['TEXT_PRIMARY']}; letter-spacing: -0.5px;"
        )
        
        # Subtitle with accent color
        subtitle = QLabel("Advanced Brain Tumor Segmentation & 3D Visualization")
        subtitle.setStyleSheet(
            f"font-size: {scaled(16)}px; color: {c['TEXT_SECONDARY']}; font-weight: 500;"
        )
        
        l.addWidget(title)
        l.addWidget(subtitle)
        
        self.layout.addWidget(header_container)

    def setup_actions(self):
        grid_container = QWidget()
        grid = QGridLayout(grid_container)
        grid.setSpacing(scaled(20))
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

        grid.addWidget(self.load_card, 0, 0)
        grid.addWidget(self.mask_card, 0, 1)
        
        # Patient Folder Card
        self.patient_card = self.create_action_card(
            "Open Patient Folder",
            "Load a folder containing multiple MRI modalities (T1, T2, FLAIR, T1ce).",
            "Open Folder",
            self.browse_folder
        )
        grid.addWidget(self.patient_card, 1, 0, 1, 2)
        
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        
        self.layout.addWidget(grid_container)

    def setup_recent(self):
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(0, scaled(10), 0, 0)
        l.setSpacing(scaled(15))
        
        c = get_theme_palette()
        
        lbl = QLabel("Recent Files")
        lbl.setStyleSheet(
            f"font-size: {scaled(20)}px; font-weight: bold; color: {c['TEXT_PRIMARY']}; margin-bottom: {scaled(5)}px;"
        )
        
        self.recent_list = QListWidget()
        self.recent_list.setMinimumHeight(scaled(150))
        self.recent_list.setMaximumHeight(scaled(300))
        self.recent_list.setObjectName("RecentList")
        
        # Theme-aware list styling (handled globally now by QListWidget styles in theme.py)
        # No inline override needed — the global styles apply
        
        self.refresh_recent_list()
        self.recent_list.itemClicked.connect(self.on_recent_clicked)
        
        l.addWidget(lbl)
        l.addWidget(self.recent_list)
        
        self.layout.addWidget(container)

    def refresh_recent_list(self):
        self.recent_list.clear()
        # Use new method that guarantees dicts
        recents = self.settings.get_recent_files()
        
        if not recents:
            item = QListWidgetItem("No recent files.")
            item.setFlags(Qt.NoItemFlags)
            self.recent_list.addItem(item)
        else:
            for entry in recents:
                path = entry['path']
                timestamp = entry.get('timestamp', 'Unknown')
                
                item = QListWidgetItem(self.recent_list)
                item.setSizeHint(QSize(0, scaled(60)))  # Adjust height
                
                # Create custom widget
                widget = RecentFileItemWidget(path, timestamp)
                widget.clicked.connect(self.on_recent_item_clicked)
                widget.deleted.connect(self.on_recent_item_deleted)
                
                self.recent_list.setItemWidget(item, widget)

    def on_recent_item_clicked(self, path):
        self.recent_file_clicked.emit(path)

    def on_recent_item_deleted(self, path):
        if self.settings.remove_recent(path):
            self.refresh_recent_list()

    def on_recent_clicked(self, item):
        # Legacy handler, might not be needed if using setItemWidget everywhere, 
        # but good to keep for the "No recent files" item
        path = item.text()
        if path and path != "No recent files.":
             pass # Handled by widget signal now
             
    def refresh(self):
        """Called when dashboard is shown to update dynamic content."""
        self.refresh_recent_list()

    def create_action_card(self, title, desc, btn_text, callback):
        c = get_theme_palette()
        
        card = QFrame()
        card.setObjectName("Card")
        card.setMinimumSize(scaled(280), scaled(240))
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Shadow Effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(scaled(25))
        shadow.setColor(QColor(c["SHADOW"]))
        shadow.setOffset(0, scaled(8))
        card.setGraphicsEffect(shadow)
        
        # Inner Layout
        l = QVBoxLayout(card)
        l.setContentsMargins(scaled(25), scaled(25), scaled(25), scaled(25))
        l.setSpacing(scaled(15))
        
        # Icon
        icon_lbl = QLabel("📂" if "Scan" in title else "🎭" if "Mask" in title else "📁" if "Folder" in title else "⚡")
        icon_lbl.setStyleSheet(f"font-size: {scaled(32)}px;")
        icon_lbl.setAlignment(Qt.AlignLeft)
        
        # Title
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"font-size: {scaled(18)}px; font-weight: bold; color: {c['TEXT_PRIMARY']};"
        )
        title_lbl.setWordWrap(True)
        
        # Desc
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(
            f"font-size: {scaled(13)}px; color: {c['TEXT_SECONDARY']}; line-height: 1.4;"
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        # Button
        btn = QPushButton(btn_text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(scaled(45))
        
        if callback:
            btn.clicked.connect(callback)
        else:
            btn.setEnabled(False)
        
        l.addWidget(icon_lbl)
        l.addWidget(title_lbl)
        l.addWidget(desc_lbl)
        l.addStretch()
        l.addWidget(btn)
        
        # Card style uses global theme QSS — no inline override needed
        
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
