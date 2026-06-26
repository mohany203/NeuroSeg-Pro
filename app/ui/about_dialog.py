from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QDesktopServices, QIcon
from PyQt5.QtCore import QUrl
from app.ui.theme import get_theme_palette, scaled

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        c = get_theme_palette()
        
        self.setWindowTitle("About NeuroSeg-Pro")
        self.resize(scaled(650), scaled(550))
        self.setStyleSheet(f"background-color: {c['BACKGROUND']}; color: {c['TEXT_PRIMARY']};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(scaled(24), scaled(24), scaled(24), scaled(24))
        layout.setSpacing(scaled(16))
        
        # Header Box
        header_layout = QHBoxLayout()
        title_lbl = QLabel("NeuroSeg-Pro")
        title_lbl.setStyleSheet(f"font-size: {scaled(26)}px; font-weight: 800; color: {c['PRIMARY']};")
        ver_lbl = QLabel("v1.0.0 Clinical Edition")
        ver_lbl.setStyleSheet(f"font-size: {scaled(14)}px; font-weight: 600; color: {c['TEXT_SECONDARY']}; align-self: flex-end;")
        
        header_layout.addWidget(title_lbl)
        header_layout.addWidget(ver_lbl)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {c['BORDER']};")
        layout.addWidget(sep)
        
        # Scrollable Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, scaled(10), 0)
        c_layout.setSpacing(scaled(16))
        
        # Description
        desc_box = self._create_section("🧬 Mission & Description", 
            "NeuroSeg-Pro is an advanced, AI-powered volumetric brain tumor evaluation platform designed for rapid clinical inference and state-of-the-art 3D deep learning model research.\n\n"
            "Leveraging 3D U-Net architectures and Knowledge Distillation paradigms, it simultaneously ingests multi-modal MRI scans (T1, T1c, T2, FLAIR) to accurately segment Enhancing Tumors (ET), Tumor Core (TC), and Peritumoral Edema (WT).", c)
        c_layout.addWidget(desc_box)
        
        # Usage Instructions
        usage_box = self._create_section("💡 How to Use", 
            "1. Open Study: Click 'Open Study' to load a patient folder containing NIfTI MRI sequences.\n"
            "2. Select Model: Pick one or multiple pre-trained AI models from the sidebar.\n"
            "3. Execute Segmentation: Click the primary run button to compute volumetric segmentation.\n"
            "4. Analyze & Export: Review Axial, Coronal, Sagittal, and 3D rendered slices. Compare Model A vs Model B or Ground Truth annotations, and click 'Export Report' to generate a clinical PDF summary.", c)
        c_layout.addWidget(usage_box)
        
        # Team Showcase
        team_box = self._create_section("👥 Meet the Team", 
            "• Mohamed Hany — Project Lead & AI Architect\n"
            "• Ahmed Samy — Deep Learning & Volumetric Rendering\n"
            "• Omar Eldash — Data Preprocessing & Clinical Validation", c)
        c_layout.addWidget(team_box)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # Bottom Actions (GitHub & Close)
        btn_layout = QHBoxLayout()
        
        btn_github = QPushButton("🌐 View GitHub Repository")
        btn_github.setCursor(Qt.PointingHandCursor)
        btn_github.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['SURFACE_LIGHT']};
                color: {c['PRIMARY']};
                border: 1px solid {c['PRIMARY']};
                border-radius: {scaled(6)}px;
                padding: {scaled(8)}px {scaled(16)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {c['PRIMARY_LIGHT']}; }}
        """)
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/mohany203/NeuroSeg-Pro")))
        
        btn_close = QPushButton("Close")
        btn_close.setObjectName("AccentButton")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_github)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _create_section(self, title, text, c):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {c['SURFACE']}; border: 1px solid {c['BORDER']}; border-radius: {scaled(8)}px; padding: {scaled(12)}px;")
        f_layout = QVBoxLayout(frame)
        f_layout.setContentsMargins(scaled(8), scaled(8), scaled(8), scaled(8))
        f_layout.setSpacing(scaled(8))
        
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"font-size: {scaled(16)}px; font-weight: bold; color: {c['PRIMARY']}; border: none; background: transparent;")
        
        txt_lbl = QLabel(text)
        txt_lbl.setWordWrap(True)
        txt_lbl.setStyleSheet(f"font-size: {scaled(13)}px; color: {c['TEXT_SECONDARY']}; line-height: 1.4; border: none; background: transparent;")
        
        f_layout.addWidget(t_lbl)
        f_layout.addWidget(txt_lbl)
        return frame
