from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QPushButton, QFrame, QFileDialog, QListWidget, QGridLayout, QScrollArea, QSizePolicy, QListWidgetItem, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QVariantAnimation
from PyQt5.QtGui import QIcon, QFont, QResizeEvent, QColor, QCursor
import os
import torch
from app.ui.settings import Settings
from app.ui.theme import get_theme_palette, scaled

class RecentFileItemWidget(QFrame):
    clicked = pyqtSignal(str)
    deleted = pyqtSignal(str)

    def __init__(self, path, timestamp):
        super().__init__()
        self.path = path
        
        c = get_theme_palette()
        
        self.setObjectName("RecentItem")
        self.setStyleSheet(f"""
            QFrame#RecentItem {{
                background-color: transparent;
                border-radius: {scaled(8)}px;
                border: 1px solid transparent;
            }}
            QFrame#RecentItem:hover {{
                background-color: {c['SURFACE_LIGHT']};
                border: 1px solid {c['BORDER_HOVER']};
            }}
        """)

        self.path = path
        
        c = get_theme_palette()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(scaled(10), scaled(5), scaled(10), scaled(5))
        layout.setSpacing(scaled(15))
        
        # Icon Container
        icon_container = QLabel("📄")
        icon_container.setAlignment(Qt.AlignCenter)
        icon_container.setFixedSize(scaled(36), scaled(36))
        icon_container.setStyleSheet(f"""
            QLabel {{
                background-color: {c['PRIMARY_LIGHT']};
                color: {c['PRIMARY']};
                border-radius: {scaled(18)}px;
                font-size: {scaled(16)}px;
            }}
        """)
        layout.addWidget(icon_container)
        
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

    def enterEvent(self, event):
        self.setCursor(QCursor(Qt.PointingHandCursor))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setCursor(QCursor(Qt.ArrowCursor))
        super().leaveEvent(event)

    def on_delete(self):
        self.deleted.emit(self.path)


class ActionCard(QFrame):
    clicked = pyqtSignal()
    
    def __init__(self, title, desc, icon_char, accent_color, bg_color):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("Card")
        # Relax sizing so it can flexibly scale on different DPI screens
        self.setMinimumSize(scaled(180), scaled(120))
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        c = get_theme_palette()
        self.default_border = c["BORDER"]
        self.hover_border = accent_color
        
        # Custom stylesheet to make sure it paints backgrounds 
        self.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {c['SURFACE']};
                border-radius: {scaled(16)}px;
                border: 1px solid {self.default_border};
            }}
            QFrame#Card:hover {{
                background-color: {c['SURFACE_LIGHT']};
                border: 1px solid {self.hover_border};
            }}
        """)
        
        # Shadow Effect
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(scaled(20))
        self.shadow.setColor(QColor(c["SHADOW"]))
        self.shadow.setOffset(0, scaled(6))
        self.setGraphicsEffect(self.shadow)
        
        # Inner Layout
        l = QVBoxLayout(self)
        l.setContentsMargins(scaled(25), scaled(25), scaled(25), scaled(25))
        l.setSpacing(scaled(12))
        
        # Header Row: Icon + Arrow
        header_lay = QHBoxLayout()
        icon_lbl = QLabel(icon_char)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setFixedSize(scaled(50), scaled(50))
        icon_lbl.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {accent_color};
                border-radius: {scaled(25)}px;
                font-size: {scaled(26)}px;
            }}
        """)
        header_lay.addWidget(icon_lbl)
        header_lay.addStretch()
        
        arrow = QLabel("➔")
        arrow.setStyleSheet(f"color: {c['TEXT_MUTED']}; font-size: {scaled(24)}px; font-weight: bold;")
        header_lay.addWidget(arrow)
        l.addLayout(header_lay)
        
        l.addSpacing(scaled(10))
        
        # Title
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"font-size: {scaled(20)}px; font-weight: bold; color: {c['TEXT_PRIMARY']};"
        )
        title_lbl.setWordWrap(True)
        l.addWidget(title_lbl)
        
        # Desc
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(
            f"font-size: {scaled(14)}px; color: {c['TEXT_SECONDARY']}; line-height: 1.5;"
        )
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        l.addWidget(desc_lbl)
        l.addStretch()

    def enterEvent(self, event):
        self.setCursor(QCursor(Qt.PointingHandCursor))
        # Animate shadow
        self.shadow.setBlurRadius(scaled(30))
        self.shadow.setOffset(0, scaled(10))
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setCursor(QCursor(Qt.ArrowCursor))
        self.shadow.setBlurRadius(scaled(20))
        self.shadow.setOffset(0, scaled(6))
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


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

        # Welcome Section + System Status
        self.setup_header()
        
        # System Stats Ribbon
        self.setup_system_stats()
        
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
        
        # Welcome Title with rich HTML gradient-like color
        title = QLabel(f"<span style='color: {c['PRIMARY']};'>Welcome to</span> NeuroSeg Pro")
        title.setTextFormat(Qt.RichText)
        title.setStyleSheet(
            f"font-size: {scaled(36)}px; font-weight: 800; color: {c['TEXT_PRIMARY']}; letter-spacing: -0.5px;"
        )
        
        # Subtitle with accent color
        subtitle = QLabel("Advanced Brain Tumor Segmentation & 3D Visualization")
        subtitle.setStyleSheet(
            f"font-size: {scaled(16)}px; color: {c['TEXT_SECONDARY']}; font-weight: 500; font-family: 'Segoe UI', Arial;"
        )
        
        l.addWidget(title)
        l.addWidget(subtitle)
        
        self.layout.addWidget(header_container)

    def setup_system_stats(self):
        c = get_theme_palette()
        
        # We wrap it in a horizontal layout with a stretch so the background doesn't spam the whole screen width
        wrapper_lay = QHBoxLayout()
        wrapper_lay.setContentsMargins(0, 0, 0, 0)
        
        stats_container = QFrame()
        stats_container.setAttribute(Qt.WA_StyledBackground, True)
        stats_container.setStyleSheet(f"""
            QFrame {{
                background-color: {c['SURFACE']};
                border-radius: {scaled(8)}px;
                border: 1px solid {c['BORDER']};
            }}
        """)
        sl = QHBoxLayout(stats_container)
        sl.setContentsMargins(scaled(12), scaled(8), scaled(12), scaled(8))
        sl.setSpacing(scaled(20))
        
        # Initial placeholders
        self.stat1 = QLabel("⏳ Hardware: <b>Checking...</b>")
        self.stat1.setStyleSheet(f"color: {c['TEXT_SECONDARY']}; font-size: {scaled(12)}px;")
        
        self.stat2 = QLabel("📦 Engine: <b>Loading...</b>")
        self.stat2.setStyleSheet(f"color: {c['TEXT_SECONDARY']}; font-size: {scaled(12)}px;")
        
        sl.addWidget(self.stat1)
        sl.addWidget(self.stat2)
        
        wrapper_lay.addWidget(stats_container)
        wrapper_lay.addStretch()
        
        self.layout.addLayout(wrapper_lay)
        
        # Defer the deep hardware checks so we don't freeze the GUI on startup
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.check_hardware_stats)

    def check_hardware_stats(self):
        c = get_theme_palette()
        has_cuda = torch.cuda.is_available()
        device_str = torch.cuda.get_device_name(0) if has_cuda else "CPU Mode"
        icon_str = "🟢" if has_cuda else "🟡"
        
        self.stat1.setText(f"{icon_str} Hardware: <b>{device_str}</b>")
        self.stat2.setText(f"📦 Engine: <b>v{torch.__version__.split('+')[0]}</b>")

    def setup_actions(self):
        grid_container = QWidget()
        grid = QGridLayout(grid_container)
        grid.setSpacing(scaled(25))
        grid.setContentsMargins(0,0,0,0)
        
        c = get_theme_palette()
        
        # Load Scan Card
        self.load_card = ActionCard(
            "Load MRI Scan", 
            "Import a NIfTI (.nii) file to begin 3D volumetric analysis and visualization.",
            "📂", c["PRIMARY"], c["PRIMARY_LIGHT"]
        )
        self.load_card.clicked.connect(lambda: self.browse_file('mri'))
        
        # Load Mask Card
        self.mask_card = ActionCard(
            "Load Segmentation Mask", 
            "Import a binary mask to overlay on the MRI scan for accurate visual comparison.",
            "🎭", c["SUCCESS"], "rgba(16, 185, 129, 0.15)"
        )
        self.mask_card.clicked.connect(lambda: self.browse_file('mask'))
        
        grid.addWidget(self.load_card, 0, 0)
        grid.addWidget(self.mask_card, 0, 1)
        
        # Patient Folder Card
        self.patient_card = ActionCard(
            "Open Patient Folder",
            "Instantly load a structured folder containing multiple registered MRI modalities (T1, T2, FLAIR, T1ce).",
            "📁", c["WARNING"], "rgba(245, 158, 11, 0.15)"
        )
        self.patient_card.clicked.connect(self.browse_folder)
        
        # Batch Processing Placeholder
        self.batch_card = ActionCard(
            "Batch Processing",
            "Automate segmentation across entire cohorts. (Feature Coming Soon)",
            "⚡", c["TEXT_MUTED"], c["SURFACE_LIGHT"]
        )
        self.batch_card.setEnabled(False)
        self.batch_card.setStyleSheet(f"QFrame#Card {{ opacity: 0.5; background-color: {c['SURFACE']}; }}")

        grid.addWidget(self.patient_card, 1, 0)
        grid.addWidget(self.batch_card, 1, 1)
        
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        
        self.layout.addWidget(grid_container)

    def setup_recent(self):
        c = get_theme_palette()
        panel = QFrame()
        panel.setObjectName("Card")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        panel.setAttribute(Qt.WA_StyledBackground, True)
        panel.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {c['SURFACE']};
                border-radius: {scaled(16)}px;
                border: 1px solid {c['BORDER']};
            }}
        """)
        
        # Add a subtle shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(scaled(20))
        shadow.setColor(QColor(c["SHADOW"]))
        shadow.setOffset(0, scaled(5))
        panel.setGraphicsEffect(shadow)

        l = QVBoxLayout(panel)
        l.setContentsMargins(scaled(25), scaled(25), scaled(25), scaled(25))
        l.setSpacing(scaled(15))
        
        header_layout = QHBoxLayout()
        icon_lbl = QLabel("🕒")
        icon_lbl.setStyleSheet(f"font-size: {scaled(20)}px;")
        
        lbl = QLabel("Recent Files")
        lbl.setStyleSheet(
            f"font-size: {scaled(20)}px; font-weight: bold; color: {c['TEXT_PRIMARY']};"
        )
        
        header_layout.addWidget(icon_lbl)
        header_layout.addWidget(lbl)
        header_layout.addStretch()
        l.addLayout(header_layout)
        
        self.recent_list = QListWidget()
        self.recent_list.setMinimumHeight(scaled(150))
        self.recent_list.setMaximumHeight(scaled(300))
        self.recent_list.setObjectName("RecentList")
        self.recent_list.setStyleSheet(f"QListWidget {{ border: none; background: transparent; }}")
        
        self.refresh_recent_list()
        self.recent_list.itemClicked.connect(self.on_recent_clicked)
        
        l.addWidget(self.recent_list)
        
        self.layout.addWidget(panel)

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
