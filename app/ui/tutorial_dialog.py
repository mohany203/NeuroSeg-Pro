from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QPushButton, QStackedWidget, QFrame, QWidget, QSizePolicy)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QFont, QColor, QPalette
from app.ui.theme import get_theme_palette, scaled

class TutorialSlide(QWidget):
    def __init__(self, title, description, image_path=None, parent=None):
        super().__init__(parent)
        c = get_theme_palette()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(scaled(40), scaled(40), scaled(40), scaled(40))
        self.layout.setSpacing(scaled(20))
        self.layout.setAlignment(Qt.AlignCenter)

        # Title
        self.lbl_title = QLabel(title)
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet(
            f"font-size: {scaled(34)}px; font-weight: bold; color: {c['PRIMARY']}; margin-bottom: {scaled(10)}px;"
        )
        self.layout.addWidget(self.lbl_title)

        # Image Container
        if image_path:
            self.img_label = QLabel()
            self.img_label.setAlignment(Qt.AlignCenter)
            self.img_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.img_label.setStyleSheet(
                f"border: 2px solid {c['BORDER']}; border-radius: {scaled(12)}px; background: #000;"
            )
            
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                s = scaled(600)
                h = scaled(400)
                img_scaled = pixmap.scaled(s, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.img_label.setPixmap(img_scaled)
            else:
                 self.img_label.setText(f"[Image not found: {image_path}]")
                 self.img_label.setStyleSheet(f"color: {c['ERROR']}; border: 1px dashed {c['ERROR']};")
            
            self.layout.addWidget(self.img_label)

        # Description
        self.lbl_desc = QLabel(description)
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setAlignment(Qt.AlignCenter)
        self.lbl_desc.setStyleSheet(
            f"font-size: {scaled(18)}px; color: {c['TEXT_SECONDARY']}; line-height: 1.4;"
        )
        self.layout.addWidget(self.lbl_desc)

class TutorialDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        c = get_theme_palette()
        
        self.setWindowTitle("NeuroSeg Pro - Interactive Tutorial")
        self.resize(scaled(1000), scaled(750))
        self.setStyleSheet(f"background-color: {c['BACKGROUND']};")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.demo_image_path = "assets/tutorial_viz.png"

        # Content Slider
        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)
        
        # --- Slides ---
        self.add_slide(
            "Welcome to NeuroSeg Pro",
            "Your advanced solution for Brain Tumor Segmentation using Deep Learning.\n\n"
            "This tool allows you to visualize multi-modal MRI scans and automatically identify tumor regions with high precision.",
            image_path=None
        )
        
        self.add_slide(
            "Step 1: Efficient Data Loading",
            "Click 'Open Patient Folder' on the Dashboard.\n\n"
            "Simply select a folder containing your NIfTI files (t1, t2, t1ce, flair).\n"
            "The system automatically detects and organizes the modalities for you.",
            image_path=None
        )

        self.add_slide(
            "Step 2: Interactive Visualization",
            "Explore your data in 2D and 3D.\n\n"
            "- Use the Modality Dropdown to switch views.\n"
            "- Right-Click & Drag to Pan 2D views.\n"
            "- Scroll to Zoom in/out.\n"
            "- Rotate the 3D volume by dragging.",
            image_path=self.demo_image_path 
        )
        
        self.add_slide(
            "Step 3: AI-Powered Segmentation",
            "Select an AI Model from the sidebar and click 'Run Segmentation'.\n\n"
            "The model processes all 4 modalities to generate a precise 3D mask of the tumor regions.\n"
            "You can choose to set a Default Model in Settings for faster access.",
            image_path=None
        )

        self.add_slide(
            "Step 4: Advanced Validation",
            "Compare AI predictions against Ground Truth data.\n\n"
            "- Use 'Active Overlay' to toggle between Prediction and Ground Truth.\n"
            "- Enable 'Split Screen Comparison' to see them side-by-side.\n"
            "- Validate detection accuracy instantly.",
            image_path=None
        )
        
        self.add_slide(
            "Understanding the Results",
            "The segmentation mask highlights different tumor regions:\n\n"
            "Red: Enhancing Tumor (ET)\n"
            "Yellow: Peritumoral Edema (ED)\n"
            "Green: Necrotic/Non-Enhancing Tumor (NCR/NET)",
            image_path=None
        )

        # --- Navigation Bar ---
        nav_bar = QWidget()
        nav_bar.setStyleSheet(
            f"background-color: {c['SURFACE']}; border-top: 1px solid {c['BORDER']};"
        )
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(scaled(20), scaled(15), scaled(20), scaled(15))
        
        self.btn_skip = QPushButton("Skip Tutorial")
        self.btn_skip.setStyleSheet(
            f"color: {c['TEXT_MUTED']}; border: none; font-size: {scaled(14)}px; background: transparent;"
        )
        self.btn_skip.setCursor(Qt.PointingHandCursor)
        self.btn_skip.clicked.connect(self.accept)
        
        self.btn_prev = QPushButton("Previous")
        self._style_prev_btn(c)
        
        self.btn_next = QPushButton("Next")
        self._style_next_btn(c)
        
        self.btn_prev.clicked.connect(self.prev_slide)
        self.btn_next.clicked.connect(self.next_slide)
        
        nav_layout.addWidget(self.btn_skip)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addSpacing(scaled(10))
        nav_layout.addWidget(self.btn_next)
        
        self.layout.addWidget(nav_bar)
        
        self.update_buttons()

    def _style_prev_btn(self, c):
        self.btn_prev.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['SURFACE_LIGHT']}; 
                color: {c['TEXT_PRIMARY']}; 
                border-radius: {scaled(6)}px; 
                padding: {scaled(8)}px {scaled(16)}px; 
                font-size: {scaled(16)}px;
                border: 1px solid {c['BORDER']};
            }}
            QPushButton:hover {{ background-color: {c['SURFACE_HOVER']}; }}
            QPushButton:disabled {{ background-color: {c['SURFACE']}; color: {c['TEXT_MUTED']}; }}
        """)

    def _style_next_btn(self, c, green=False):
        bg = c['SUCCESS'] if green else c['PRIMARY']
        bg_hover = "#2DAF4F" if green else c['PRIMARY_HOVER']
        self.btn_next.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg}; 
                color: white; 
                border-radius: {scaled(6)}px; 
                padding: {scaled(8)}px {scaled(24)}px; 
                font-size: {scaled(16)}px; 
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ background-color: {bg_hover}; }}
        """)

    def add_slide(self, title, description, image_path=None):
        slide = TutorialSlide(title, description, image_path, self)
        self.stack.addWidget(slide)

    def prev_slide(self):
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
        self.update_buttons()

    def next_slide(self):
        idx = self.stack.currentIndex()
        if idx < self.stack.count() - 1:
            self.stack.setCurrentIndex(idx + 1)
        else:
            self.accept()
        self.update_buttons()

    def update_buttons(self):
        c = get_theme_palette()
        idx = self.stack.currentIndex()
        count = self.stack.count()
        
        self.btn_prev.setEnabled(idx > 0)
        
        if idx == count - 1:
            self.btn_next.setText("Get Started")
            self._style_next_btn(c, green=True)
        else:
            self.btn_next.setText("Next")
            self._style_next_btn(c, green=False)
