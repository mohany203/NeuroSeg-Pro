from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QPushButton, QStackedWidget, QFrame, QWidget, QSizePolicy)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QFont, QColor, QPalette

class TutorialSlide(QWidget):
    def __init__(self, title, description, image_path=None, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)
        self.layout.setAlignment(Qt.AlignCenter)

        # Title
        self.lbl_title = QLabel(title)
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        # Font size 34 as requested, colorful
        self.lbl_title.setStyleSheet("font-size: 34px; font-weight: bold; color: #0A84FF; margin-bottom: 10px;")
        self.layout.addWidget(self.lbl_title)

        # Image Container
        if image_path:
            self.img_label = QLabel()
            self.img_label.setAlignment(Qt.AlignCenter)
            self.img_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.img_label.setStyleSheet("border: 2px solid #333; border-radius: 12px; background: #000;")
            
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                # Scale nicely - keeping aspect ratio
                # We defer scaling to resizeEvent or just set a reasonable fixed maximum
                scaled = pixmap.scaled(600, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.img_label.setPixmap(scaled)
            else:
                 self.img_label.setText(f"[Image not found: {image_path}]")
                 self.img_label.setStyleSheet("color: red; border: 1px dashed red;")
            
            self.layout.addWidget(self.img_label)

        # Description
        self.lbl_desc = QLabel(description)
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setAlignment(Qt.AlignCenter)
        self.lbl_desc.setStyleSheet("font-size: 18px; color: #E0E0E0; line-height: 1.4;")
        self.layout.addWidget(self.lbl_desc)

class TutorialDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("NeuroSeg Pro - Interactive Tutorial")
        self.resize(1000, 750) # Larger size for better visuals
        self.setStyleSheet("background-color: #1E1E1E;")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Header (Optional, maybe just integrate into slides)
        # self.header = QLabel("NeuroSeg Pro Guide")
        # self.header.setStyleSheet("background: #252525; color: #FFF; padding: 15px; font-size: 16px; font-weight: bold;")
        # self.layout.addWidget(self.header)

        # Helper to get image path safely
        self.demo_image_path = "assets/tutorial_viz.png"

        # Content Slider
        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)
        
        # --- Slides ---
        
        # 1. Welcome
        self.add_slide(
            "Welcome to NeuroSeg Pro",
            "Your advanced solution for Brain Tumor Segmentation using Deep Learning.\n\n"
            "This tool allows you to visualize multi-modal MRI scans and automatically identify tumor regions with high precision.",
            image_path=None # Could add a logo here if we had one
        )
        
        # 2. Data Loading
        self.add_slide(
            "Step 1: Efficient Data Loading",
            "Click 'Open Patient Folder' on the Dashboard.\n\n"
            "Simply select a folder containing your NIfTI files (t1, t2, t1ce, flair).\n"
            "The system automatically detects and organizes the modalities for you.",
            image_path=None # Placeholder
        )

        # 3. Visualization (Using User Image)
        self.add_slide(
            "Step 2: Interactive Visualization",
            "Explore your data in 2D and 3D.\n\n"
            "- Use the Modality Dropdown to switch views.\n"
            "- Right-Click & Drag to Pan 2D views.\n"
            "- Scroll to Zoom in/out.\n"
            "- Rotate the 3D volume by dragging.",
            image_path=self.demo_image_path 
        )
        
        # 4. AI Segmentation
        self.add_slide(
            "Step 3: AI-Powered Segmentation",
            "Select an AI Model from the sidebar and click 'Run Segmentation'.\n\n"
            "The model processes all 4 modalities to generate a precise 3D mask of the tumor regions.\n"
            "You can choose to set a Default Model in Settings for faster access.",
            image_path=None
        )

        # 5. Advanced Comparison
        self.add_slide(
            "Step 4: Advanced Validation",
            "Compare AI predictions against Ground Truth data.\n\n"
            "- Use 'Active Overlay' to toggle between Prediction and Ground Truth.\n"
            "- Enable 'Split Screen Comparison' to see them side-by-side.\n"
            "- Validate detection accuracy instantly.",
            image_path=None
        )
        
        # 6. Interpretation
        self.add_slide(
            "Understanding the Results",
            "The segmentation mask highlights different tumor regions:\n\n"
            "Red: Enhancing Tumor (ET)\n"
            "Blue: Peritumoral Edema (ED)\n"
            "Green: Necrotic/Non-Enhancing Tumor (NCR/NET)",
            image_path=None
        )

        # --- Navigation Bar ---
        nav_bar = QWidget()
        nav_bar.setStyleSheet("background-color: #252525; border-top: 1px solid #333;")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(20, 15, 20, 15)
        
        self.btn_skip = QPushButton("Skip Tutorial")
        self.btn_skip.setStyleSheet("color: #888; border: none; font-size: 14px;")
        self.btn_skip.setCursor(Qt.PointingHandCursor)
        self.btn_skip.clicked.connect(self.accept)
        
        self.btn_prev = QPushButton("Previous")
        self.btn_prev.setStyleSheet("""
            QPushButton {
                background-color: #444; 
                color: white; 
                border-radius: 6px; 
                padding: 8px 16px; 
                font-size: 16px;
            }
            QPushButton:hover { background-color: #555; }
            QPushButton:disabled { background-color: #333; color: #555; }
        """)
        
        self.btn_next = QPushButton("Next")
        self.btn_next.setStyleSheet("""
            QPushButton {
                background-color: #0A84FF; 
                color: white; 
                border-radius: 6px; 
                padding: 8px 24px; 
                font-size: 16px; 
                font-weight: bold;
            }
            QPushButton:hover { background-color: #007AFF; }
        """)
        
        self.btn_prev.clicked.connect(self.prev_slide)
        self.btn_next.clicked.connect(self.next_slide)
        
        nav_layout.addWidget(self.btn_skip)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addSpacing(10)
        nav_layout.addWidget(self.btn_next)
        
        self.layout.addWidget(nav_bar)
        
        self.update_buttons()

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
        idx = self.stack.currentIndex()
        count = self.stack.count()
        
        self.btn_prev.setEnabled(idx > 0)
        
        if idx == count - 1:
            self.btn_next.setText("Get Started")
            self.btn_next.setStyleSheet("""
                QPushButton {
                    background-color: #34C759; 
                    color: white; 
                    border-radius: 6px; 
                    padding: 8px 24px; 
                    font-size: 16px; 
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #2DAF4F; }
            """)
        else:
            self.btn_next.setText("Next")
            # Restore blue style
            self.btn_next.setStyleSheet("""
                QPushButton {
                    background-color: #0A84FF; 
                    color: white; 
                    border-radius: 6px; 
                    padding: 8px 24px; 
                    font-size: 16px; 
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #007AFF; }
            """)
