import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, 
    QSlider, QCheckBox, QGridLayout, QFrame, QSplitter, QGroupBox, QSizePolicy,
    QToolBox, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QProgressBar, QMessageBox, QToolButton
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QThread, QTimer
from PyQt5.QtGui import QColor, QFont, QIcon, QPixmap, QPainter

from app.ui.settings import Settings
from app.core.inference import InferenceEngine
from app.core.image_processor import ImageProcessor
from app.ui.theme import get_theme_palette, apply_theme, scaled, scaled_font
from app.core.constants import ROI_COLORS, ROI_DEFINITIONS, ROI_COLORS_3D, Labels

class InferenceWorker(QThread):
    finished = pyqtSignal(dict) # {model_name: prediction_array}
    error = pyqtSignal(str)

    def __init__(self, engine, input_vol, model_a_config, model_b_config=None):
        super().__init__()
        self.engine = engine
        self.input_vol = input_vol
        self.model_a_config = model_a_config
        self.model_b_config = model_b_config

    def run(self):
        try:
            results = {}
            
            # Run Model A
            if self.model_a_config and "path" in self.model_a_config:
                print(f"Worker: Running Model A ({self.model_a_config['name']}) on {self.engine.device}...")
                pred_a = self.engine.run_inference(self.input_vol, self.model_a_config["path"])
                results['A'] = pred_a
            
            # Run Model B
            if self.model_b_config and "path" in self.model_b_config:
                print(f"Worker: Running Model B ({self.model_b_config['name']})...")
                pred_b = self.engine.run_inference(self.input_vol, self.model_b_config["path"])
                results['B'] = pred_b
                
            self.finished.emit(results)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

class ViewerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.inference_engine = InferenceEngine() 
        c = get_theme_palette()
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Data
        self.patient_data = {}  # Dictionary for multi-modal {t1: ..., t2: ...}
        self.active_modality = 't1' 
        self.volume = None      # Current viewing volume (Normalized 0-1)
        self.mask = None        # Currently active Segmentation Mask (0 or 1)
        self.ground_truth = None # Ground Truth Mask
        
        # Dual Model State
        self.model_a_name = None
        self.model_b_name = None
        
        
        self.prediction = None   # Current active prediction (for display)
        self.prediction_a = None # Result from Model A
        self.prediction_b = None # Result from Model B
        
        self.metrics_a = None
        self.metrics_b = None
        
        self.affine = None      # Affine Matrix for Export
        self.current_slice = {'axial': 0, 'sagittal': 0, 'coronal': 0}
        
        # UI State
        self.show_mask = True
        self.comparison_mode = False # If True, showing Model A vs Model B (or other split)
        self.mask_opacity = 0.5
        self.active_overlay_type = "Standard (Prediction)" # Or "Model A", "Model B", "Compare"
        
        # 3 Viewports + 3D View (Grid) with Toolbar
        self.view_container = QWidget()
        view_main_layout = QVBoxLayout(self.view_container)
        view_main_layout.setContentsMargins(0, 0, 0, 0)
        view_main_layout.setSpacing(0)
        
        # --- Viewport Toolbar ---
        self.viewport_toolbar = QFrame()
        self.viewport_toolbar.setObjectName("ViewportToolbar")
        self.viewport_toolbar.setStyleSheet(f"""
            #ViewportToolbar {{
                background-color: {c['SURFACE']};
                border-bottom: 1px solid {c['BORDER']};
                min-height: {scaled(48)}px;
                padding: {scaled(4)}px {scaled(8)}px;
            }}
            #ViewportToolbar QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: {scaled(6)}px;
                padding: {scaled(6)}px {scaled(12)}px;
                color: {c['TEXT_SECONDARY']};
                font-size: {scaled_font(14)}px;
                font-weight: 600;
            }}
            #ViewportToolbar QToolButton:hover {{
                background-color: {c['SURFACE_LIGHT']};
                border-color: {c['BORDER']};
                color: {c['TEXT_PRIMARY']};
            }}
            #ViewportToolbar QToolButton:checked {{
                background-color: {c['PRIMARY']}33;
                border-color: {c['PRIMARY']};
                color: {c['PRIMARY']};
            }}
        """)
        tb_layout = QHBoxLayout(self.viewport_toolbar)
        tb_layout.setContentsMargins(scaled(8), scaled(4), scaled(8), scaled(4))
        tb_layout.setSpacing(scaled(8))
        
        # View All button
        self.btn_view_all = QToolButton()
        self.btn_view_all.setText("\U0001f50d Fit All")
        self.btn_view_all.setCursor(Qt.PointingHandCursor)
        self.btn_view_all.clicked.connect(self.view_all_viewports)
        tb_layout.addWidget(self.btn_view_all)
        
        # Separator
        sep_tb = QFrame()
        sep_tb.setFrameShape(QFrame.VLine)
        sep_tb.setStyleSheet(f"color: {c['BORDER']};")
        tb_layout.addWidget(sep_tb)
        
        # Toggle buttons (checkable)
        self.tb_grid = QToolButton()
        self.tb_grid.setText("\u229E Grid")
        self.tb_grid.setCheckable(True)
        self.tb_grid.setCursor(Qt.PointingHandCursor)
        self.tb_grid.toggled.connect(self._toolbar_toggle_grid)
        tb_layout.addWidget(self.tb_grid)
        
        self.tb_crosshair = QToolButton()
        self.tb_crosshair.setText("\u271B Cross")
        self.tb_crosshair.setCheckable(True)
        self.tb_crosshair.setCursor(Qt.PointingHandCursor)
        self.tb_crosshair.toggled.connect(self._toolbar_toggle_crosshair)
        tb_layout.addWidget(self.tb_crosshair)
        
        self.tb_mri = QToolButton()
        self.tb_mri.setText("\U0001f9e0 MRI")
        self.tb_mri.setCheckable(True)
        self.tb_mri.setChecked(True)
        self.tb_mri.setCursor(Qt.PointingHandCursor)
        self.tb_mri.toggled.connect(self._toolbar_toggle_mri)
        tb_layout.addWidget(self.tb_mri)
        
        tb_layout.addStretch()
        
        view_main_layout.addWidget(self.viewport_toolbar)
        
        # --- Grid for Viewports ---
        self.grid_widget = QWidget()
        self.view_grid = QGridLayout(self.grid_widget)
        self.view_grid.setSpacing(4)
        self.view_grid.setContentsMargins(4, 4, 4, 4)
        view_main_layout.addWidget(self.grid_widget, 1)  # stretch=1 so grid takes all space
        
        # Interactive Viewports (pyqtgraph)
        self.axial_view = self.create_interactive_viewport("Axial")
        self.sagittal_view = self.create_interactive_viewport("Sagittal")
        self.coronal_view = self.create_interactive_viewport("Coronal")
        
        # Compare Viewports (Interactive)
        self.compare_view_axial = self.create_interactive_viewport("Axial (Compare)")
        self.compare_view_axial.hide()
        
        self.compare_view_sagittal = self.create_interactive_viewport("Sagittal (Compare)")
        self.compare_view_sagittal.hide()
        
        self.compare_view_coronal = self.create_interactive_viewport("Coronal (Compare)")
        self.compare_view_coronal.hide()

        # Compare Viewports 2 (Rightmost - for 3-way compare)
        self.compare_view2_axial = self.create_interactive_viewport("Axial (GT)")
        self.compare_view2_axial.hide()
        
        self.compare_view2_sagittal = self.create_interactive_viewport("Sagittal (GT)")
        self.compare_view2_sagittal.hide()
        
        self.compare_view2_coronal = self.create_interactive_viewport("Coronal (GT)")
        self.compare_view2_coronal.hide()
        
        # Link Viewports (Pan/Zoom Sync)
        self.axial_view.view.setXLink(self.compare_view_axial.view)
        self.axial_view.view.setYLink(self.compare_view_axial.view)
        
        self.sagittal_view.view.setXLink(self.compare_view_sagittal.view)
        self.sagittal_view.view.setYLink(self.compare_view_sagittal.view)
        
        self.coronal_view.view.setXLink(self.compare_view_coronal.view)
        self.coronal_view.view.setYLink(self.compare_view_coronal.view)

        # Link Viewports 2
        self.axial_view.view.setXLink(self.compare_view2_axial.view)
        self.axial_view.view.setYLink(self.compare_view2_axial.view)
        
        self.sagittal_view.view.setXLink(self.compare_view2_sagittal.view)
        self.sagittal_view.view.setYLink(self.compare_view2_sagittal.view)
        
        self.coronal_view.view.setXLink(self.compare_view2_coronal.view)
        self.coronal_view.view.setYLink(self.compare_view2_coronal.view)
        
        # Playback Timer
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.update_playback)
        self.is_playing = False
        
        self.threed_view = self.create_3d_viewport()
        
        # Default Layout
        self.setup_grid_layout()
        
        # Controls Panel — compact sidebar (flex: stretches to fill container width)
        self.controls = QFrame()
        self.controls.setObjectName("Sidebar")
        self.controls.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.control_layout = QVBoxLayout(self.controls)
        self.control_layout.setContentsMargins(scaled(6), scaled(6), scaled(6), scaled(6))
        self.control_layout.setSpacing(scaled(3))
        
        self.setup_controls()
        
        # Scroll Area for Controls — no horizontal scroll, content stretches to fit
        from PyQt5.QtWidgets import QScrollArea
        self.scroll_controls = QScrollArea()
        self.scroll_controls.setWidget(self.controls)
        self.scroll_controls.setWidgetResizable(True)
        self.scroll_controls.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_controls.setMinimumWidth(scaled(180))
        self.scroll_controls.setMaximumWidth(scaled(400))
        self.scroll_controls.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.scroll_controls.setStyleSheet("border: none; background: transparent;")

        # Splitter for Resizable Sidebar
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.view_container)
        self.splitter.addWidget(self.scroll_controls)
        
        # Viewport gets all extra space, sidebar stays fixed
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setChildrenCollapsible(False)
        
        # Set initial sizes [viewport, sidebar]
        self.splitter.setSizes([scaled(780), scaled(260)]) 
        
        self.layout.addWidget(self.splitter)
        
        self.refresh_theme()
        
        # Populate models from settings
        self.populate_models()

    def create_interactive_viewport(self, title):
        """Creates a pyqtgraph-based 2D viewport with Pan/Zoom support."""
        # Container
        container = QWidget()
        # Fix resizing issues: Force widget to expand
        from PyQt5.QtWidgets import QSizePolicy
        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        container.setMinimumSize(QSize(100, 100)) # Prevent collapsing to 0
        l = QVBoxLayout(container)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(0)
        
        # Header (Simple Label overlay logic could be cleaner, but VBox is fine)
        header_lbl = QLabel(title)
        header_lbl.setStyleSheet("color: #0A84FF; font-weight: bold; background: transparent; padding: 4px;")
        l.addWidget(header_lbl)
        
        # Graphics Layout
        win = pg.GraphicsLayoutWidget()
        win.ci.layout.setContentsMargins(0,0,0,0)
        # Background handled in refresh_theme
        
        view = win.addViewBox()
        view.setAspectLocked(True)
        view.setMouseEnabled(x=True, y=True) # Pan/Zoom enabled
        
        # Image Item (Main)
        img_item = pg.ImageItem()
        view.addItem(img_item)
        
        # Mask Item (Overlay)
        mask_item = pg.ImageItem()
        mask_item.setZValue(10) # Draw on top
        mask_item.setOpacity(self.mask_opacity)
        # Composition mode for overlay? Default ‘result = src * alpha + dest * (1-alpha)’ is usually fine if handled correctly
        # pg.ImageItem doesn't do direct RGBA blending perfectly without LUT, so we will use RGBA textures
        view.addItem(mask_item)
        
        l.addWidget(win)
        
        # Store refs
        container.view = view
        container.img = img_item
        container.mask = mask_item
        container.win = win
        container.title = header_lbl
        
        # Override resizeEvent to auto-center
        original_resize = container.resizeEvent
        def auto_center_resize(event):
            original_resize(event)
            view.autoRange()
        
        container.resizeEvent = auto_center_resize
        
        return container

    def setup_grid_layout(self):
        # Clear specific positions (widgets remain ownership)
        for i in reversed(range(self.view_grid.count())): 
            item = self.view_grid.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
            
        if self.comparison_mode:
            mode = self.combo_compare_mode.currentText()
            
            if mode == "Model A vs Model B vs Ground Truth":
                 # 3-Column Layout (3 Columns x 3 Rows)
                 # Col 0: Model A, Col 1: Model B, Col 2: GT
                 
                 # Row 0: Axial
                 self.view_grid.addWidget(self.axial_view, 0, 0)
                 self.compare_view_axial.show()
                 self.view_grid.addWidget(self.compare_view_axial, 0, 1)
                 self.compare_view2_axial.show()
                 self.view_grid.addWidget(self.compare_view2_axial, 0, 2)

                 # Row 1: Sagittal
                 self.sagittal_view.show()
                 self.view_grid.addWidget(self.sagittal_view, 1, 0)
                 self.compare_view_sagittal.show()
                 self.view_grid.addWidget(self.compare_view_sagittal, 1, 1)
                 self.compare_view2_sagittal.show()
                 self.view_grid.addWidget(self.compare_view2_sagittal, 1, 2)

                 # Row 2: Coronal
                 self.coronal_view.show()
                 self.view_grid.addWidget(self.coronal_view, 2, 0)
                 self.compare_view_coronal.show()
                 self.view_grid.addWidget(self.compare_view_coronal, 2, 1)
                 self.compare_view2_coronal.show()
                 self.view_grid.addWidget(self.compare_view2_coronal, 2, 2)

                 self.threed_view.hide()
                 
                 # Stretching
                 for r in range(3): self.view_grid.setRowStretch(r, 1)
                 for c in range(3): self.view_grid.setColumnStretch(c, 1)

            else:
                # 2-Column Comparison (2 Columns x 3 Rows)
                # Row 0: Axial
                self.view_grid.addWidget(self.axial_view, 0, 0)
                self.compare_view_axial.show()
                self.view_grid.addWidget(self.compare_view_axial, 0, 1)
                
                # Row 1: Sagittal
                self.sagittal_view.show()
                self.view_grid.addWidget(self.sagittal_view, 1, 0)
                self.compare_view_sagittal.show()
                self.view_grid.addWidget(self.compare_view_sagittal, 1, 1)
                
                # Row 2: Coronal
                self.coronal_view.show()
                self.view_grid.addWidget(self.coronal_view, 2, 0)
                self.compare_view_coronal.show()
                self.view_grid.addWidget(self.compare_view_coronal, 2, 1)
                
                self.compare_view2_axial.hide()
                self.compare_view2_sagittal.hide()
                self.compare_view2_coronal.hide() # Hide 3rd column
                
                self.threed_view.hide()
                
                # Fix Resizing: Equal Stretch
                self.view_grid.setRowStretch(0, 1)
                self.view_grid.setRowStretch(1, 1)
                self.view_grid.setRowStretch(2, 1)
                self.view_grid.setColumnStretch(0, 1)
                self.view_grid.setColumnStretch(1, 1)
                self.view_grid.setColumnStretch(2, 0) # No 3rd col
            
        else:
            # Standard Quad View
            self.compare_view_axial.hide()
            self.compare_view_sagittal.hide()
            self.compare_view_coronal.hide()
            self.compare_view2_axial.hide()
            self.compare_view2_sagittal.hide()
            self.compare_view2_coronal.hide()
            
            self.sagittal_view.show()
            self.coronal_view.show()
            self.threed_view.show()
            
            self.view_grid.addWidget(self.axial_view, 0, 0)
            self.view_grid.addWidget(self.sagittal_view, 0, 1)
            self.view_grid.addWidget(self.coronal_view, 1, 0)
            self.view_grid.addWidget(self.threed_view, 1, 1)

            # Fix Resizing: Equal Stretch for 2x2
            self.view_grid.setRowStretch(0, 1)
            self.view_grid.setRowStretch(1, 1)
            # Reset row 2 stretch (unused here)
            self.view_grid.setRowStretch(2, 0) 
            self.view_grid.setColumnStretch(0, 1)
            self.view_grid.setColumnStretch(1, 1)
            self.view_grid.setColumnStretch(2, 0)

    def create_3d_viewport(self):
        view = gl.GLViewWidget()
        view.opts['distance'] = 200
        view.opts['azimuth'] = 225  # Corrected: flip 180° to fix inverted orientation
        view.opts['elevation'] = 30
        
        # REMOVED: GLAxisItem and GLGridItem causing shader errors on some systems.
        # Starting with clean empty view.
        
        return view

    def refresh_theme(self):
        theme = self.settings.get("theme")
        is_light = (theme == "Light")
        
        # 3D View Background
        bg_color = [255, 255, 255, 255] if is_light else [0, 0, 0, 255]
        self.threed_view.setBackgroundColor(bg_color[0], bg_color[1], bg_color[2], 255)
        
        # 2D Graph Backgrounds
        # pyqtgraph global config is tricky, usually set background per instance
        # 'w' for white, 'k' for black
        pg_bg = 'w' if is_light else 'k'
        
        for v in [self.axial_view, self.sagittal_view, self.coronal_view, self.compare_view_axial, self.compare_view_sagittal, self.compare_view_coronal]:
            v.win.setBackground(pg_bg)
            # v.title.setStyleSheet(f"color: {'#000' if is_light else '#fff'}; ...") # Optional text update

    def setup_controls(self):
        c = get_theme_palette()
        
        # --- Section 1: AI Analysis ---
        ai_group = QGroupBox("\U0001f9e0 AI Analysis")
        ai_layout = QVBoxLayout()
        ai_layout.setSpacing(scaled(3))
        
        # Modality Selection
        mod_label = QLabel("MRI MODALITY")
        mod_label.setObjectName("SectionLabel")
        ai_layout.addWidget(mod_label)
        self.combo_modality = QComboBox()
        self.combo_modality.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_modality.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_modality.addItem("T1") 
        self.combo_modality.currentTextChanged.connect(self.change_modality)
        ai_layout.addWidget(self.combo_modality)
        
        # Thin separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet(f"background-color: {c['BORDER']}; max-height: 1px;")
        ai_layout.addWidget(sep1)
        
        # Model A Selection
        lbl_a = QLabel("PRIMARY MODEL (A)")
        lbl_a.setObjectName("SectionLabel")
        ai_layout.addWidget(lbl_a)
        self.combo_model_a = QComboBox()
        self.combo_model_a.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_model_a.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_model_a.currentIndexChanged.connect(lambda i: self.on_model_changed(i, 'A'))
        ai_layout.addWidget(self.combo_model_a)

        # Model B Selection
        lbl_b = QLabel("SECONDARY MODEL (B)")
        lbl_b.setObjectName("SectionLabel")
        ai_layout.addWidget(lbl_b)
        self.combo_model_b = QComboBox()
        self.combo_model_b.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_model_b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_model_b.addItem("None (Single Model)")
        self.combo_model_b.currentIndexChanged.connect(lambda i: self.on_model_changed(i, 'B'))
        ai_layout.addWidget(self.combo_model_b)
        
        # Import Model Button
        self.btn_import_model = QPushButton("\u2b05  Import .pth Model")
        self.btn_import_model.setCursor(Qt.PointingHandCursor)
        self.btn_import_model.clicked.connect(self.import_model_dialog)
        ai_layout.addWidget(self.btn_import_model)
        
        # Run Button & Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setFixedHeight(scaled(6))
        ai_layout.addWidget(self.progress_bar)
        
        self.btn_run = QPushButton("\u25B6  Run Segmentation")
        self.btn_run.setObjectName("AccentButton")
        self.btn_run.setFixedHeight(scaled(30))
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.clicked.connect(self.run_segmentation)
        ai_layout.addWidget(self.btn_run)
        
        ai_group.setLayout(ai_layout)
        self.control_layout.addWidget(ai_group)
        
        # --- Section 2: Visualization Control ---
        viz_group = QGroupBox("\U0001f441 Visualization")
        viz_layout = QVBoxLayout()
        viz_layout.setSpacing(scaled(3))
        
        # Mask Opacity
        opacity_header = QHBoxLayout()
        opacity_label = QLabel("Mask Transparency")
        opacity_label.setStyleSheet(f"font-size: {scaled_font(12)}px; font-weight: 600; color: {c['TEXT_PRIMARY']};")
        self.opacity_value_lbl = QLabel("50%")
        self.opacity_value_lbl.setStyleSheet(f"color: {c['PRIMARY']}; font-weight: bold; font-size: {scaled_font(12)}px;")
        opacity_header.addWidget(opacity_label)
        opacity_header.addStretch()
        opacity_header.addWidget(self.opacity_value_lbl)
        viz_layout.addLayout(opacity_header)
        
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setValue(50)
        self.slider_opacity.valueChanged.connect(self.update_opacity)
        self.slider_opacity.valueChanged.connect(lambda v: self.opacity_value_lbl.setText(f"{v}%"))
        viz_layout.addWidget(self.slider_opacity)

        # View Toggles — in a card-like row
        toggles_frame = QFrame()
        toggles_frame.setStyleSheet(f"background-color: {c['BACKGROUND']}; border-radius: 6px; padding: 2px;")
        toggles_layout = QHBoxLayout(toggles_frame)
        toggles_layout.setContentsMargins(4, 2, 4, 2)
        toggles_layout.setSpacing(6)
        self.chk_grid = QCheckBox("Grid")
        self.chk_grid.toggled.connect(self.toggle_grid)
        toggles_layout.addWidget(self.chk_grid)
        
        self.chk_crosshair = QCheckBox("Crosshair")
        self.chk_crosshair.toggled.connect(self.toggle_crosshair)
        toggles_layout.addWidget(self.chk_crosshair)
        
        self.chk_mri = QCheckBox("MRI")
        self.chk_mri.setChecked(True)
        self.chk_mri.toggled.connect(self.toggle_mri)
        toggles_layout.addWidget(self.chk_mri)
        viz_layout.addWidget(toggles_frame)
        
        # Comparison Controls
        self.btn_compare = QPushButton("\u2194  Compare")
        self.btn_compare.setCheckable(True)
        self.btn_compare.setCursor(Qt.PointingHandCursor)
        self.btn_compare.toggled.connect(self.toggle_comparison)
        viz_layout.addWidget(self.btn_compare)
        
        self.compare_options = QWidget()
        co_layout = QVBoxLayout(self.compare_options)
        co_layout.setContentsMargins(0,0,0,0)
        self.combo_compare_mode = QComboBox()
        self.combo_compare_mode.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_compare_mode.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_compare_mode.addItems(["Model A vs Model B", "Model A vs Ground Truth", "Model A vs Model B vs Ground Truth", "Overlay vs Raw"])
        self.combo_compare_mode.currentIndexChanged.connect(lambda: self.update_all_2d_views())
        self.combo_compare_mode.currentIndexChanged.connect(lambda: self.setup_grid_layout()) # Re-setup grid on change
        co_layout.addWidget(self.combo_compare_mode)
        self.compare_options.setVisible(False)
        viz_layout.addWidget(self.compare_options)

        # Active Overlay (Single Mode)
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet(f"background-color: {c['BORDER']}; max-height: 1px;")
        viz_layout.addWidget(sep2)
        
        hbox_overlay = QHBoxLayout()
        overlay_lbl = QLabel("Overlay:")
        overlay_lbl.setStyleSheet("font-weight: 600;")
        hbox_overlay.addWidget(overlay_lbl)
        self.combo_overlay_mode = QComboBox()
        self.combo_overlay_mode.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_overlay_mode.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_overlay_mode.addItems(["Model A", "Model B", "Ground Truth", "Difference (A vs GT)", "Difference (A vs B)"])
        self.combo_overlay_mode.currentIndexChanged.connect(self.on_overlay_mode_changed)
        hbox_overlay.addWidget(self.combo_overlay_mode)
        viz_layout.addLayout(hbox_overlay)
        
        viz_group.setLayout(viz_layout)
        self.control_layout.addWidget(viz_group)

        # --- Section 3: Results & Metrics ---
        results_group = QGroupBox("\U0001f4ca Results & Metrics")
        results_group.setObjectName("ResultsGroup")
        results_layout = QVBoxLayout()
        results_layout.setSpacing(scaled(3))
        
        # Header row with info button
        r_header = QHBoxLayout()
        self.btn_info = QToolButton()
        self.btn_info.setText("?")
        self.btn_info.setObjectName("InfoButton")
        self.btn_info.setFixedSize(scaled(24), scaled(24))
        self.btn_info.setCursor(Qt.PointingHandCursor)
        self.btn_info.clicked.connect(self.show_metrics_info)
        r_header.addStretch()
        r_header.addWidget(self.btn_info)
        results_layout.addLayout(r_header)
        
        # Region Selector
        region_label = QLabel("REGION OF INTEREST")
        region_label.setObjectName("SectionLabel")
        results_layout.addWidget(region_label)
        self.combo_metric_class = QComboBox()
        self.combo_metric_class.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_metric_class.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_metric_class.addItems(list(ROI_DEFINITIONS.keys()))
        self.combo_metric_class.currentTextChanged.connect(self.on_roi_changed)
        results_layout.addWidget(self.combo_metric_class)
        
        # Detailed Metrics Table — stretches columns to fit panel width
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(3)
        self.metrics_table.setHorizontalHeaderLabels(["Metric", "Model A", "Model B"])
        self.metrics_table.verticalHeader().setVisible(False)
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.metrics_table.horizontalHeader().setStretchLastSection(True)
        self.metrics_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.metrics_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.metrics_table.setRowCount(8)
        
        # Helper to create colored circular icons
        def create_legend_icon(color_tuple):
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            c = QColor(*color_tuple)
            painter.setBrush(c)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, 12, 12)
            painter.end()
            return QIcon(pixmap)

        # -- Row Configuration --
        # Row 0: Header "Dice Score"
        # Rows 1-3: ET, NCR, ED Dice
        # Row 4: Header "HD95 (mm)"
        # Rows 5-7: ET, NCR, ED HD95
        
        # 1. Setup Section Headers
        for row, title in [(0, "Dice Score"), (4, "HD95 (mm)")]:
            self.metrics_table.setItem(row, 0, QTableWidgetItem(title))
            self.metrics_table.setSpan(row, 0, 1, 3) # Merge 3 columns
            
            # Styling for Header
            item = self.metrics_table.item(row, 0)
            item.setTextAlignment(Qt.AlignCenter)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setBackground(QColor(40, 40, 40)) # Darker background for header
            item.setFlags(Qt.ItemIsEnabled) # No select, no edit

        # 2. Setup Data Rows
        # Map: (Row Index, Label, Color Key)
        data_rows = [
            (1, "Enhancing Tumor", Labels.ET),
            (2, "Necrosis", Labels.NCR),
            (3, "Edema", Labels.ED),
            (5, "Enhancing Tumor", Labels.ET),
            (6, "Necrosis", Labels.NCR),
            (7, "Edema", Labels.ED),
        ]

        for r, label, color_key in data_rows:
            # Col 0: Label + Icon
            color = ROI_COLORS.get(color_key, (128, 128, 128, 255))
            icon = create_legend_icon(color)
            
            item_name = QTableWidgetItem(label)
            item_name.setIcon(icon)
            item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
            self.metrics_table.setItem(r, 0, item_name)
            
            # Col 1 & 2: Placeholders
            for c in [1, 2]:
                item = QTableWidgetItem("\u2014")
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.metrics_table.setItem(r, c, item)

        self.metrics_table.setMinimumHeight(scaled(280))
        self.metrics_table.setMaximumHeight(scaled(350))
        self.metrics_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # No scroll
        self.metrics_table.setAlternatingRowColors(True)
        self.metrics_table.setSelectionMode(QTableWidget.NoSelection)
        self.metrics_table.setEditTriggers(QTableWidget.NoEditTriggers)
        results_layout.addWidget(self.metrics_table)
        
        # Legend container — will hold chip-style labels
        self.legend_container = QWidget()
        self.legend_layout = QVBoxLayout(self.legend_container)
        self.legend_layout.setContentsMargins(0, scaled(5), 0, 0)
        self.legend_layout.setSpacing(scaled(4))
        results_layout.addWidget(self.legend_container)
        
        results_group.setLayout(results_layout)
        self.control_layout.addWidget(results_group)
        
        # --- Section 4: Navigation & Export ---
        nav_group = QGroupBox("\U0001f9ed Navigation")
        nav_layout = QVBoxLayout()
        nav_layout.setSpacing(scaled(3))
        
        self.sl_control_axial = self.create_slice_slider("Axial")
        self.sl_control_sagittal = self.create_slice_slider("Sagittal")
        self.sl_control_coronal = self.create_slice_slider("Coronal")
        
        self.sl_axial = self.sl_control_axial.slider
        self.sl_sagittal = self.sl_control_sagittal.slider
        self.sl_coronal = self.sl_control_coronal.slider
        
        nav_layout.addWidget(self.sl_control_axial)
        nav_layout.addWidget(self.sl_control_sagittal)
        nav_layout.addWidget(self.sl_control_coronal)

        # Smart Playback Controls
        pb_group = QHBoxLayout()
        pb_group.setSpacing(scaled(4))
        
        # Play/Pause Button
        self.btn_play = QPushButton("\u25B6")
        self.btn_play.setCheckable(True)
        self.btn_play.setFixedWidth(scaled(40))
        self.btn_play.setCursor(Qt.PointingHandCursor)
        self.btn_play.clicked.connect(self.toggle_playback)
        self.btn_play.setStyleSheet(f"""
            QPushButton:checked {{
                background-color: {c['ERROR']};
                border-color: {c['ERROR']};
                color: white;
            }}
        """)
        pb_group.addWidget(self.btn_play)
        
        # Speed Slider
        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(1, 30) # 1 to 30 FPS
        self.slider_speed.setValue(10)
        self.slider_speed.setToolTip("Playback Speed (FPS)")
        self.slider_speed.valueChanged.connect(self.update_playback_interval)
        pb_group.addWidget(self.slider_speed)
        
        # Repeat Checkbox
        self.chk_repeat = QCheckBox("Loop")
        self.chk_repeat.setChecked(True)
        pb_group.addWidget(self.chk_repeat)
        
        nav_layout.addLayout(pb_group)
        
        # Export buttons with icons
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.HLine)
        sep3.setStyleSheet(f"background-color: {c['BORDER']}; max-height: 1px;")
        nav_layout.addWidget(sep3)
        
        btns_layout = QHBoxLayout()
        btns_layout.setSpacing(scaled(8))
        self.btn_export = QPushButton("\U0001F4BE Save .nii")
        self.btn_export.setObjectName("AccentButton")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self.export_mask)
        self.btn_export.setEnabled(False)
        btns_layout.addWidget(self.btn_export)
        
        self.btn_screenshot = QPushButton("\U0001F4F7 Screenshot")
        self.btn_screenshot.setCursor(Qt.PointingHandCursor)
        self.btn_screenshot.clicked.connect(self.save_screenshot)
        btns_layout.addWidget(self.btn_screenshot)
        
        nav_layout.addLayout(btns_layout)
        nav_group.setLayout(nav_layout)
        self.control_layout.addWidget(nav_group)
        self.control_layout.addStretch()
        
        # Initialize Toggles
        self.show_grid = False
        self.show_crosshair = False
        self.show_mri = True
        
        # Initial Legend Update
        self.update_legend()

    def _get_current_visualization_state(self):
        """
        Determines the active mask and appropriate color scheme based on current UI state.
        Returns: (mask, is_diff, custom_colors)
        """
        overlay_mode = self.combo_overlay_mode.currentText()
        # Default behavior (Single Mode Logic)
        active_mask = None
        is_diff = False
        custom_colors = None

        if overlay_mode == "Model A":
            active_mask = self.prediction_a
        elif overlay_mode == "Model B":
            active_mask = self.prediction_b
        elif overlay_mode == "Ground Truth":
            active_mask = self.ground_truth
        elif overlay_mode == "Difference (A vs GT)":
            if self.prediction_a is not None and self.ground_truth is not None:
                active_mask = ImageProcessor.calculate_difference_map(self.prediction_a, self.ground_truth)
                is_diff = True
        elif overlay_mode == "Difference (A vs B)":
            if self.prediction_a is not None and self.prediction_b is not None:
                active_mask = ImageProcessor.calculate_difference_map(self.prediction_a, self.prediction_b)
                is_diff = True
        else:
            active_mask = self.prediction_a if self.prediction_a is not None else self.mask

        if is_diff:
            # 1=FP (Red), 2=FN (Blue), 3=TP (Green)
            custom_colors = {
                1: {"name": "False Positive", "color": (1.0, 0.2, 0.2, 0.8)},
                2: {"name": "False Negative", "color": (0.0, 0.4, 1.0, 0.8)},
                3: {"name": "True Positive", "color": (0.2, 0.85, 0.3, 0.8)}
            }
        
        return active_mask, is_diff, custom_colors

    def on_overlay_mode_changed(self):
        self.update_legend()
        self.update_all_2d_views()
        
        # Update 3D View
        mask, is_diff, colors = self._get_current_visualization_state()
        self.update_3d_view(mask, is_mask=True, custom_colors=colors, is_diff=is_diff)

    # --- New Visualization Methods ---
    def toggle_grid(self, checked):
        self.show_grid = checked
        # Sync toolbar button
        if hasattr(self, 'tb_grid'):
            self.tb_grid.blockSignals(True)
            self.tb_grid.setChecked(checked)
            self.tb_grid.blockSignals(False)
        for v in [self.axial_view, self.sagittal_view, self.coronal_view,
                  self.compare_view_axial, self.compare_view_sagittal, self.compare_view_coronal]:
            # ViewBox doesn't support showGrid directly, use GridItem
            if not hasattr(v, 'grid_item'):
                v.grid_item = pg.GridItem()
                v.view.addItem(v.grid_item)
            
            v.grid_item.setVisible(checked)

    def toggle_crosshair(self, checked):
        self.show_crosshair = checked
        if hasattr(self, 'tb_crosshair'):
            self.tb_crosshair.blockSignals(True)
            self.tb_crosshair.setChecked(checked)
            self.tb_crosshair.blockSignals(False)
        self.update_all_2d_views() # Repaint to add/remove lines

    def toggle_mri(self, checked):
        self.show_mri = checked
        if hasattr(self, 'tb_mri'):
            self.tb_mri.blockSignals(True)
            self.tb_mri.setChecked(checked)
            self.tb_mri.blockSignals(False)
        self.update_all_2d_views()

    # --- Toolbar quick-action methods ---
    def view_all_viewports(self):
        """Auto-range (fit) all 2D viewports at once."""
        for v in [self.axial_view, self.sagittal_view, self.coronal_view,
                  self.compare_view_axial, self.compare_view_sagittal, self.compare_view_coronal]:
            if v.isVisible():
                v.view.autoRange()
    
    def _toolbar_toggle_grid(self, checked):
        """Bridge: toolbar Grid button -> sidebar checkbox."""
        if hasattr(self, 'chk_grid'):
            self.chk_grid.blockSignals(True)
            self.chk_grid.setChecked(checked)
            self.chk_grid.blockSignals(False)
        self.toggle_grid(checked)
    
    def _toolbar_toggle_crosshair(self, checked):
        """Bridge: toolbar Crosshair button -> sidebar checkbox."""
        if hasattr(self, 'chk_crosshair'):
            self.chk_crosshair.blockSignals(True)
            self.chk_crosshair.setChecked(checked)
            self.chk_crosshair.blockSignals(False)
        self.toggle_crosshair(checked)
    
    def _toolbar_toggle_mri(self, checked):
        """Bridge: toolbar MRI button -> sidebar checkbox."""
        if hasattr(self, 'chk_mri'):
            self.chk_mri.blockSignals(True)
            self.chk_mri.setChecked(checked)
            self.chk_mri.blockSignals(False)
        self.toggle_mri(checked)

    def show_metrics_info(self):
        info_text = """
        <h3>Segmentation Metrics</h3>
        <b>Dice Coefficient (F1):</b> Overlap similarity (0–1). Higher is better.<br>
        <b>IoU (Jaccard):</b> Intersection over Union. Stricter than Dice.<br>
        <b>Sensitivity (Recall):</b> % of actual tumor correctly found.<br>
        <b>Specificity:</b> % of healthy tissue correctly identified.<br>
        <b>Precision:</b> % of predicted tumor that is actually tumor.<br>
        <b>HD95 (Hausdorff):</b> 95th percentile boundary distance. <b>Lower is better</b> (mm).
        """
        QMessageBox.information(self, "Metrics Explanation", info_text)

    def update_legend(self, mode=None):
        c = get_theme_palette()
        # Clear existing
        for i in reversed(range(self.legend_layout.count())): 
            item = self.legend_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        
        current_combo = self.combo_overlay_mode.currentText()
        target_mode = mode if mode else current_combo
        
        def add_chip(color, label):
            chip = QFrame()
            chip.setObjectName("LegendChip")
            l = QHBoxLayout(chip)
            l.setContentsMargins(8, 4, 8, 4)
            l.setSpacing(8)
            dot = QLabel()
            dot.setFixedSize(12, 12)
            dot.setStyleSheet(f"background-color: {color}; border-radius: 6px; border: none;")
            lbl = QLabel(label)
            lbl.setStyleSheet(f"font-size: 11px; font-weight: 500; color: {c['TEXT_PRIMARY']}; border: none; background: transparent;")
            l.addWidget(dot)
            l.addWidget(lbl)
            l.addStretch()
            self.legend_layout.addWidget(chip)
        
        # Title for legend section
        legend_title = QLabel("LEGEND")
        legend_title.setObjectName("SectionLabel")
        self.legend_layout.addWidget(legend_title)
        
        if target_mode.startswith("Difference"):
             add_chip("#FF3B30", "False Positive")
             add_chip("#007AFF", "False Negative")
             add_chip("#34C759", "True Positive")
        else:
             active_mask = self.prediction_a if self.prediction_a is not None else self.mask
             
             # Determine which labels are actually present in the 3D volume
             present_classes = set()
             if active_mask is not None:
                 present_classes = set(np.unique(active_mask).astype(int))
             
             # Get the currently selected ROI to determine which sub-regions to show
             roi = self.combo_metric_class.currentText() if hasattr(self, 'combo_metric_class') else "Whole Tumor"
             target_labels = ROI_DEFINITIONS.get(roi, [Labels.NCR, Labels.ED, Labels.ET])
             
             # Map label IDs to display names
             label_names = {
                 Labels.ET: "Enhancing (ET)",
                 Labels.NCR: "Necrosis (NCR)",
                 Labels.ED: "Edema (ED)",
             }
             
             if active_mask is None:
                 # No mask loaded — show all expected sub-regions as static legend
                 for label_id in target_labels:
                     if label_id in ROI_COLORS:
                         c_hex = QColor(*ROI_COLORS[label_id]).name()
                         name = label_names.get(label_id, f"Label {label_id}")
                         add_chip(c_hex, name)
             else:
                 # Mask is loaded — show all sub-regions, dim ones not detected
                 any_found = False
                 for label_id in target_labels:
                     if label_id in ROI_COLORS:
                         c_hex = QColor(*ROI_COLORS[label_id]).name()
                         name = label_names.get(label_id, f"Label {label_id}")
                         if label_id in present_classes:
                             add_chip(c_hex, name)
                             any_found = True
                         else:
                             add_chip(c_hex, f"{name} (not detected)")
                 
                 if not any_found:
                     status = QLabel("\u26A0  No tumor regions detected in current mask")
                     status.setStyleSheet(f"color: {c['WARNING']}; font-style: italic; padding: 4px;")
                     self.legend_layout.addWidget(status)
        
        # Trust indicators
        if self.prediction_b is None and self.combo_model_b.currentIndex() == 0:
            note = QLabel("Model B: Not loaded")
            note.setObjectName("StatusPill")
            note.setStyleSheet(f"color: {c['TEXT_SECONDARY']}; font-style: italic; padding: 2px 8px;")
            self.legend_layout.addWidget(note)
        if self.ground_truth is None and hasattr(self, 'patient_data') and 'seg' not in getattr(self, 'patient_data', {}):
            note2 = QLabel("\u26A0  Ground truth not available")
            note2.setStyleSheet(f"color: {c['WARNING']}; font-style: italic; padding: 2px;")
            self.legend_layout.addWidget(note2)
        



    def create_slice_slider(self, label):
        c = get_theme_palette()
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(0, 2, 0, 2)
        l.setSpacing(3)
        
        header = QHBoxLayout()
        plane_lbl = QLabel(f"{label}")
        plane_lbl.setStyleSheet(f"font-weight: 600; color: {c['TEXT_PRIMARY']};")
        val_lbl = QLabel("0")
        val_lbl.setStyleSheet(f"color: {c['PRIMARY']}; font-weight: bold; font-size: {scaled_font(13)}px;")
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(plane_lbl)
        header.addStretch()
        header.addWidget(val_lbl)
        l.addLayout(header)
        
        s = QSlider(Qt.Horizontal)
        s.setEnabled(False)
        s.valueChanged.connect(lambda v: self.update_slice(label.lower(), v, val_lbl))
        l.addWidget(s)
        
        container.slider = s
        return container

    
    def toggle_comparison(self, checked):
        self.comparison_mode = checked
        self.setup_grid_layout()
        self.compare_options.setVisible(checked)
        self.update_all_2d_views()

    def update_slice(self, plane, value, label_widget):
        self.current_slice[plane] = value
        label_widget.setText(str(value))
        # In comparison mode every slice affects both panes.
        if self.comparison_mode:
            self.update_all_2d_views()
        else:
            self.update_view(plane)

    # --- Helper UI Methods ---
    def add_control_row(self, layout, label_text, info_btn):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        row.addWidget(lbl)
        row.addWidget(info_btn)
        row.addStretch()
        layout.addLayout(row)

    def create_info_button(self, text):
        btn = QPushButton("?")
        btn.setObjectName("InfoButton")
        btn.setFixedSize(20, 20)
        btn.setToolTip(text)
        return btn

    def populate_models(self):
        # Update both dropdowns
        models = self.settings.get_models()
        active_id = self.settings.get("active_model_id")
        
        self.combo_model_a.blockSignals(True)
        self.combo_model_b.blockSignals(True)
        self.combo_model_a.clear()
        self.combo_model_b.clear()
        
        # Model B Default
        self.combo_model_b.addItem("None (Single Model)", None)
        
        if models:
            for m in models:
                self.combo_model_a.addItem(m["name"], m)
                self.combo_model_b.addItem(m["name"], m)
                
                # Set Active Model A
                if m["id"] == active_id:
                    self.combo_model_a.setCurrentText(m["name"])
        else:
             self.combo_model_a.addItem("No Models Found")
             
        self.combo_model_a.blockSignals(False)
        self.combo_model_b.blockSignals(False)

    def on_model_changed(self, index, which='A'):
        if which == 'A':
            data = self.combo_model_a.itemData(index)
            if data:
                self.settings.set("active_model_id", data["id"]) # Persist main model
        # Model B just changes state for next run

    def import_model_dialog(self):
        """Allows user to import a new model file."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import PyTorch Model", "", 
            "PyTorch Models (*.pth);;All Files (*)", options=options
        )
        
        if file_path:
            import shutil
            import os
            import sys
            
            # Determine models dir
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.abspath(".")
            
            models_dir = os.path.join(base_dir, "models")
            if not os.path.exists(models_dir):
                os.makedirs(models_dir)
                
            filename = os.path.basename(file_path)
            dest_path = os.path.join(models_dir, filename)
            
            try:
                # Copy file
                shutil.copy2(file_path, dest_path)
                
                # Register in settings
                self.settings.add_model(name=filename, path=dest_path)
                
                # Refresh UI
                self.populate_models()
                
                QMessageBox.information(self, "Success", f"Model '{filename}' imported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import model: {e}")

            
    def run_segmentation(self):
        if self.volume is None: return
        
        model_a_data = self.combo_model_a.currentData()
        model_b_data = self.combo_model_b.currentData()
        
        self.btn_run.setText("Inference Running...")
        self.btn_run.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Indeterminate
        self.repaint()
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()  # Force UI to update before worker starts
        
        # --- Prepare Multimodal Input (4 Channels) ---
        # BraTS models expect [T1, T1ce, T2, FLAIR]
        # Model expects: (Batch, Channel, D, H, W)
        # Channel order MUST match training: [t1ce, t1, flair, t2]
        required_keys = ['t1ce', 't1', 'flair', 't2']
        channels = []
        
        # Determine base shape/volume to use for zeros
        base_vol = self.volume if self.volume is not None else list(self.patient_data.values())[0]
        base_shape = base_vol.shape
             
        # Case-insensitive lookup
        patient_data_lower = {k.lower(): v for k, v in self.patient_data.items()}

        for key in required_keys:
             if key in patient_data_lower:
                 vol = patient_data_lower[key]
                 # Use Z-Score normalization for inference (matches training: nonzero=False)
                 channels.append(ImageProcessor.z_score_normalize(vol, nonzero=False))
             else:
                 # Missing modality -> Zero channel
                 channels.append(np.zeros(base_shape, dtype=np.float32))

        input_vol = np.stack(channels, axis=0) # (4, D, H, W)
        
        # Start Worker
        self.worker = InferenceWorker(self.inference_engine, input_vol, model_a_data, model_b_data)
        self.worker.finished.connect(self.on_inference_finished)
        self.worker.error.connect(self.on_inference_error)
        self.worker.start()

    def on_inference_finished(self, results):
        self.progress_bar.setVisible(False)
        self.btn_run.setText("Run Segmentation")
        self.btn_run.setEnabled(True)
        
        self.prediction_a = results.get('A')
        
        self.prediction_b = results.get('B')
        
        # Debug Output
        if self.prediction_a is not None:
            unique = np.unique(self.prediction_a)
            print(f"Prediction A Stats: Shape={self.prediction_a.shape}, Unique Values={unique}")
            values, counts = np.unique(self.prediction_a, return_counts=True)
            summary = ", ".join([f"{int(v)}:{int(c)}" for v, c in zip(values, counts)])
            print(f"Prediction A Label Histogram -> {summary}")
            if len(unique) == 1 and unique[0] == 0:
                QMessageBox.warning(self, "Inference Result", "Model returned empty segmentation (all zeros). Check input data orientation or normalization.")
            elif len([u for u in unique if u > 0]) <= 1:
                # Binary models (0/1) are valid — just log, no popup
                print("Note: Prediction has a single tumor class (binary segmentation).")
        
        # Metrics Calculation
        if 'seg' in self.patient_data:
            self.ground_truth = self.patient_data['seg']
            print("Calculating detailed metrics...")
            if self.prediction_a is not None:
                self.metrics_a = ImageProcessor.calculate_metrics(self.prediction_a, self.ground_truth)
            if self.prediction_b is not None:
                self.metrics_b = ImageProcessor.calculate_metrics(self.prediction_b, self.ground_truth)
        
        self.update_metrics_display()
        self.update_legend()
        
        # Set View
        self.prediction = self.prediction_a
        self.mask = self.prediction_a
        
        self.btn_export.setEnabled(True)
        
        self.setup_sliders_and_views()
        QMessageBox.information(self, "Success", "Segmentation completed successfully.")

    def on_inference_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.btn_run.setText("Run Segmentation")
        self.btn_run.setEnabled(True)
        QMessageBox.critical(self, "Inference Error", f"An error occurred during inference:\n{error_msg}")
        print(f"Worker Error: {error_msg}")

    def on_roi_changed(self, text):
        """Called when the Region of Interest combo changes. Updates metrics, 2D views, and 3D view."""
        self.update_metrics_display()
        self.update_all_2d_views()
        # Also refresh 3D view
        mask, is_diff, colors = self._get_current_visualization_state()
        self.update_3d_view(mask, is_mask=True, custom_colors=colors, is_diff=is_diff)

    def update_metrics_display(self, *args):
        """Updates the metrics table with fixed ET, Necrosis, and Edema scores."""
        # Row Config: (ROI Name, Metric Key, Row Index)
        # Section 1: Dice (Rows 1-3)
        # Section 2: HD95 (Rows 5-7)
        # Rows 0 and 4 are headers.
        
        row_config = [
            ("Enhancing Tumor", "dice", 1),
            ("Necrosis", "dice", 2),
            ("Edema", "dice", 3),
            ("Enhancing Tumor", "hd95", 5),
            ("Necrosis", "hd95", 6),
            ("Edema", "hd95", 7),
        ]
        
        for roi_name, metric_key, row_idx in row_config:
            # Model A
            val_a = "-"
            if self.metrics_a and roi_name in self.metrics_a:
                raw_a = self.metrics_a[roi_name].get(metric_key, 0.0)
                if metric_key == "hd95":
                    val_a = f"{raw_a:.2f}" # Remove 'mm' to save space since header has it
                else:
                    val_a = f"{raw_a:.3f}"
            
            item_a = self.metrics_table.item(row_idx, 1)
            # Ensure item exists
            if not item_a:
                item_a = QTableWidgetItem()
                item_a.setTextAlignment(Qt.AlignCenter)
                item_a.setFlags(item_a.flags() & ~Qt.ItemIsEditable)
                self.metrics_table.setItem(row_idx, 1, item_a)
            item_a.setText(str(val_a))

            # Model B
            val_b = "-"
            if self.metrics_b and roi_name in self.metrics_b:
                raw_b = self.metrics_b[roi_name].get(metric_key, 0.0)
                if metric_key == "hd95":
                    val_b = f"{raw_b:.2f}"
                else:
                    val_b = f"{raw_b:.3f}"
            
            item_b = self.metrics_table.item(row_idx, 2)
            if not item_b:
                item_b = QTableWidgetItem()
                item_b.setTextAlignment(Qt.AlignCenter)
                item_b.setFlags(item_b.flags() & ~Qt.ItemIsEditable)
                self.metrics_table.setItem(row_idx, 2, item_b)
            item_b.setText(str(val_b))

    def show_metrics_context_menu(self, pos):
        from PyQt5.QtWidgets import QMenu, QAction
        menu = QMenu(self)
        copy_action = QAction("Copy Table to Clipboard", self)
        copy_action.triggered.connect(self.copy_metrics_to_clipboard)
        menu.addAction(copy_action)
        menu.exec_(self.metrics_table.mapToGlobal(pos))

    def copy_metrics_to_clipboard(self):
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        text = "Metric\tModel A\tModel B\n"
        for r in range(self.metrics_table.rowCount()):
            m = self.metrics_table.item(r, 0).text() if self.metrics_table.item(r, 0) else ""
            a = self.metrics_table.item(r, 1).text() if self.metrics_table.item(r, 1) else ""
            b = self.metrics_table.item(r, 2).text() if self.metrics_table.item(r, 2) else ""
            text += f"{m}\t{a}\t{b}\n"
        clipboard.setText(text)
        QMessageBox.information(self, "Copied", "Metrics copied to clipboard.")

    def load_patient_data(self, modalities):
        self.patient_data = modalities
        # Priorities: t1, t1ce, t2, flair
        for m in ['t1', 't1ce', 't2', 'flair']:
            if m in modalities:
                self.active_modality = m
                break
        
        self.combo_modality.blockSignals(True)
        self.combo_modality.clear()
        for k in modalities.keys():
            if k not in ['affine', 'seg']:
                self.combo_modality.addItem(k.upper())
        self.combo_modality.blockSignals(False)
        self.combo_modality.setCurrentText(self.active_modality.upper())
        
        self.volume = ImageProcessor.normalize(modalities[self.active_modality])
        self.affine = modalities.get('affine')
        
        if 'seg' in modalities:
            self.ground_truth = modalities['seg']
            # Default to showing GT if no prediction yet
            if self.prediction is None:
                self.mask = self.ground_truth
                self.combo_overlay_mode.setCurrentText("Ground Truth")
        
        self.setup_sliders_and_views()

    def change_modality(self, text):
        """Switches the displayed MRI modality."""
        if not text: return
        
        modality = text.lower()
        
        # Handle case where keys might be upper/lower
        # effective_key search
        effective_key = None
        for k in self.patient_data.keys():
            if k.lower() == modality:
                effective_key = k
                break
                
        if effective_key:
            self.active_modality = effective_key
            self.volume = ImageProcessor.normalize(self.patient_data[effective_key])
            
            # Update Views
            self.update_all_2d_views()
            
            # Update 3D View if necessary (usually just shows mask, but if showing vol...)
            # self.update_3d_view(self.mask)

    def load_data(self, volume, affine, is_mask=False):
        if not is_mask:
            self.volume = ImageProcessor.normalize(volume)
            self.affine = affine
            self.patient_data['t1'] = volume # Fallback
            
            # Reset
            self.mask = None # Reset mask
            self.btn_export.setEnabled(False)
            
            self.combo_modality.blockSignals(True)
            self.combo_modality.clear()
            self.combo_modality.addItem("T1")
            self.combo_modality.blockSignals(False)
        
        if self.volume is None and not is_mask: return
        elif self.volume is None and is_mask:
             # Case: Loading mask without volume
             self.update_3d_view(self.mask, is_mask=True)
             self.update_all_2d_views()
             return

        if self.volume is not None and not is_mask:
            self.setup_sliders_and_views()

    def setup_sliders_and_views(self):
            dims = self.volume.shape
            # Set slider ranges
            self.sl_axial.setRange(0, dims[2]-1)
            self.sl_axial.setValue(dims[2]//2)
            self.sl_axial.setEnabled(True)
            
            self.sl_sagittal.setRange(0, dims[0]-1)
            self.sl_sagittal.setValue(dims[0]//2)
            self.sl_sagittal.setEnabled(True)
            
            self.sl_coronal.setRange(0, dims[1]-1)
            self.sl_coronal.setValue(dims[1]//2)
            self.sl_coronal.setEnabled(True)
            
            self.update_3d_view(self.volume, is_mask=False)
            
            # Use shared helper to determine what to show in 3D
            mask, is_diff, colors = self._get_current_visualization_state()
            if mask is not None:
                self.update_3d_view(mask, is_mask=True, custom_colors=colors, is_diff=is_diff)

            self.update_all_2d_views()
            
            # Force auto-range to ensure image is visible
            self.axial_view.view.autoRange()
            self.sagittal_view.view.autoRange()
            self.coronal_view.view.autoRange()
            self.compare_view_axial.view.autoRange()
            self.compare_view_sagittal.view.autoRange()
            self.compare_view_coronal.view.autoRange()

    # LEGACY: mask source
    def change_mask_source(self, index):
        pass 

    def update_opacity(self, value):
        self.mask_opacity = value / 100.0
        # Update 2D overlays directly
        views = [
            self.axial_view, self.sagittal_view, self.coronal_view,
            self.compare_view_axial, self.compare_view_sagittal, self.compare_view_coronal
        ]
        for v in views:
            v.mask.setOpacity(self.mask_opacity)

    def toggle_mask(self, checked):
        self.show_mask = checked
        # Toggle 2D Visibility
        views = [
            self.axial_view, self.sagittal_view, self.coronal_view,
            self.compare_view_axial, self.compare_view_sagittal, self.compare_view_coronal
        ]
        for v in views:
            v.mask.setVisible(checked)

    def update_all_2d_views(self):
        # Determine "Primary" and "Secondary" contents based on mode
        mode = self.combo_compare_mode.currentText()
        overlay_mode = self.combo_overlay_mode.currentText()
        
        left_mask = self.prediction_a
        right_mask = None
        left_title_suffix = " (Prediction A)"
        right_title_suffix = ""
        
        # --- Logic for Comparison Mode (Split Screen) ---
        if self.comparison_mode:
            if mode == "Model A vs Model B":
                left_mask = self.prediction_a
                right_mask = self.prediction_b
                left_title_suffix = " (Model A)"
                right_title_suffix = " (Model B)"
                if self.prediction_b is None: right_title_suffix += " [Not Run]"
                
            elif mode == "Model A vs Ground Truth":
                left_mask = self.prediction_a
                right_mask = self.ground_truth
                left_title_suffix = " (Model A)"
                right_title_suffix = " (Ground Truth)"
                if self.ground_truth is None: right_title_suffix += " [Missing]"
                
            elif mode == "Model A vs Model B vs Ground Truth":
                # 3-way logic
                left_mask = self.prediction_a # Model A
                middle_mask = self.prediction_b # Model B
                right_mask = self.ground_truth # GT
                
                left_title_suffix = " (Model A)"
                middle_title_suffix = " (Model B)"
                right_title_suffix = " (Ground Truth)"
                
                # Update 3rd column viewports
                self.compare_view2_axial.title.setText(f"Axial{right_title_suffix}")
                self.compare_view2_sagittal.title.setText(f"Sagittal{right_title_suffix}")
                self.compare_view2_coronal.title.setText(f"Coronal{right_title_suffix}")
                
                self.update_view('axial', dest_viewport=self.compare_view2_axial, override_mask=right_mask)
                self.update_view('sagittal', dest_viewport=self.compare_view2_sagittal, override_mask=right_mask)
                self.update_view('coronal', dest_viewport=self.compare_view2_coronal, override_mask=right_mask)
                
                # Update Middle Column (repurposing 'right_mask' var for 2nd column in standard logic below)
                right_mask = middle_mask
                right_title_suffix = middle_title_suffix

            elif mode == "Overlay vs Raw":
                left_mask = self.prediction_a
                right_mask = None # Raw only
                left_title_suffix = " (Overlay)"
                right_title_suffix = " (Raw MRI)"
            
            # Update Titles (Cols 1 & 2)
            self.axial_view.title.setText(f"Axial{left_title_suffix}")
            self.sagittal_view.title.setText(f"Sagittal{left_title_suffix}")
            self.coronal_view.title.setText(f"Coronal{left_title_suffix}")
            
            self.compare_view_axial.title.setText(f"Axial{right_title_suffix}")
            self.compare_view_sagittal.title.setText(f"Sagittal{right_title_suffix}")
            self.compare_view_coronal.title.setText(f"Coronal{right_title_suffix}")

            # Update Left (Main) Views
            self.update_view('axial', dest_viewport=self.axial_view, override_mask=left_mask)
            self.update_view('sagittal', dest_viewport=self.sagittal_view, override_mask=left_mask)
            self.update_view('coronal', dest_viewport=self.coronal_view, override_mask=left_mask)
            
            # Update Right (Compare) Views (Column 2)
            force_no_right = (right_mask is None)
            self.update_view('axial', dest_viewport=self.compare_view_axial, override_mask=right_mask, force_no_mask=force_no_right)
            self.update_view('sagittal', dest_viewport=self.compare_view_sagittal, override_mask=right_mask, force_no_mask=force_no_right)
            self.update_view('coronal', dest_viewport=self.compare_view_coronal, override_mask=right_mask, force_no_mask=force_no_right)
            
        else:
            # --- Logic for Single Mode ---
            active_mask = None
            is_diff = False
            title_suffix = ""
            
            if overlay_mode == "Model A":
                active_mask = self.prediction_a
                title_suffix = " (Model A)"
            elif overlay_mode == "Model B":
                active_mask = self.prediction_b
                title_suffix = " (Model B)"
            elif overlay_mode == "Ground Truth":
                active_mask = self.ground_truth
                title_suffix = " (Ground Truth)"
            elif overlay_mode == "Difference (A vs GT)":
                if self.prediction_a is not None and self.ground_truth is not None:
                    active_mask = ImageProcessor.calculate_difference_map(self.prediction_a, self.ground_truth)
                    is_diff = True
                    title_suffix = " (Diff A vs GT)"
                else:
                    title_suffix = " (Diff - Missing Data)"
            elif overlay_mode == "Difference (A vs B)":
                 if self.prediction_a is not None and self.prediction_b is not None:
                    active_mask = ImageProcessor.calculate_difference_map(self.prediction_a, self.prediction_b)
                    is_diff = True
                    title_suffix = " (Diff A vs B)"
                 else:
                    title_suffix = " (Diff - Missing Data)"
            else: # Fallback Standard
                 active_mask = self.prediction_a if self.prediction_a is not None else self.mask
                 title_suffix = " (Prediction)"
            
            # Update Titles
            self.axial_view.title.setText(f"Axial{title_suffix}")
            self.sagittal_view.title.setText(f"Sagittal{title_suffix}")
            self.coronal_view.title.setText(f"Coronal{title_suffix}")

            self.update_view('axial', override_mask=active_mask, is_diff_map=is_diff)
            self.update_view('sagittal', override_mask=active_mask, is_diff_map=is_diff)
            self.update_view('coronal', override_mask=active_mask, is_diff_map=is_diff)
            
            # Update Legend
            if hasattr(self, 'update_legend'):
                legend_mode = "Difference Map" if is_diff else "Standard"
                self.update_legend(legend_mode)
            
            # Removed explicit update_3d_view from here to prevent huge lag on scrolling slices.
            # 3D view is updated only on ROI change, Inference Finish, or Overlay Mode change.

    def update_view(self, plane, dest_viewport=None, override_mask=None, force_no_mask=False, is_diff_map=False):
        if self.volume is None: return
        
        target = dest_viewport
        if target is None:
            if plane == 'axial': target = self.axial_view
            elif plane == 'sagittal': target = self.sagittal_view
            elif plane == 'coronal': target = self.coronal_view
            else: return

        idx = self.current_slice[plane]
        slice_img = ImageProcessor.get_slice(self.volume, plane, idx)
        
        # Update Main Image Use Float32 and levels=(0,1)
        img_data = slice_img.T.astype(np.float32)
        
        if self.show_mri:
            target.img.setImage(img_data, autoLevels=False, levels=(0, 1)) 
            target.img.setVisible(True)
        else:
            target.img.setVisible(False)
            
        # Draw Crosshair if enabled
        # Remove old crosshair lines if any
        if hasattr(target, 'crosshair_v'):
            target.view.removeItem(target.crosshair_v)
            target.view.removeItem(target.crosshair_h)
            del target.crosshair_v
            del target.crosshair_h
            
        if self.show_crosshair:
            # Add new lines
            v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('y', width=1, style=Qt.DashLine))
            h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('y', width=1, style=Qt.DashLine))
            
            # Position based on current slices in OTHER planes. 
            # Axial View (X=Sagittal Slice, Y=Coronal Slice) - Approximate mapping
            # This is complex without affine. For now, center on current slice or middle? 
            # Ideally crosshair should point to where the other views are slicing.
            # But here we just want a visual center or cursor? 
            # User likely wants to see WHERE the other 2 views are intersecting.
            
            # Simple implementation: Center of view (D/2, W/2 etc) or just middle marker?
            # Better: Crosshair tracks the cursor? Or shows the intersection of the other 2 planes.
            # Let's assume standard Ortho:
            # Axial View shows X/Y. The "Z" is the slice index.
            # The intersection point is (Sag_Slice, Cor_Slice).
            
            # Need strict dimension mapping:
            # Dim Order: (Sag, Cor, Axial) -> (0, 1, 2)
            # Axial View (Plane 'axial', index 2): Shows dims (0, 1) -> (Sag, Cor)
            # Correct? default behavior of slice(volume, 'axial', z) depends on get_slice
            # ImageProcessor.get_slice:
            # if plane == 'axial': return vol[:, :, idx] -> (Sag, Cor)
            
            x_pos = 0
            y_pos = 0
            
            if plane == 'axial':
                x_pos = self.current_slice['sagittal']
                y_pos = self.current_slice['coronal']
            elif plane == 'sagittal': # (Cor, Axial)
                 # get_slice 'sagittal' -> vol[idx, :, :] -> (Cor, Axial)
                x_pos = self.current_slice['coronal']
                y_pos = self.current_slice['axial']
            elif plane == 'coronal': # (Sag, Axial)
                 # get_slice 'coronal' -> vol[:, idx, :] -> (Sag, Axial)
                x_pos = self.current_slice['sagittal']
                y_pos = self.current_slice['axial']
            
            v_line.setPos(x_pos)
            h_line.setPos(y_pos)
            
            target.view.addItem(v_line)
            target.view.addItem(h_line)
            target.crosshair_v = v_line
            target.crosshair_h = h_line 
        
        # Update Mask Overlay
        mask_to_use = override_mask if override_mask is not None else self.mask
        
        if mask_to_use is not None and (self.show_mask and not force_no_mask):
            mask_slice = ImageProcessor.get_slice(mask_to_use, plane, idx)
            
            # DEBUG: Print unique values ONLY for axial center slice to avoid spam
            if plane == 'axial' and idx == self.current_slice['axial']:
                pass # print(f"DEBUG: Mask Slice Unique Values: {np.unique(mask_slice)}")

            h, w = mask_slice.shape
            rgba = np.zeros((h, w, 4), dtype=np.uint8)
            
            if is_diff_map:
                # 1=FP (Red), 2=FN (Blue), 3=TP (Green)
                rgba[mask_slice == 1, 0] = 255 # Red
                rgba[mask_slice == 1, 3] = 200
                
                rgba[mask_slice == 2, 2] = 255 # Blue
                rgba[mask_slice == 2, 3] = 200
                
                rgba[mask_slice == 3, 1] = 255 # Green
                rgba[mask_slice == 3, 3] = 200
                
            else:
                # Determine which classes to show based on selected ROI
                roi = self.combo_metric_class.currentText() if hasattr(self, 'combo_metric_class') else "Whole Tumor"
                
                # Get relevant labels for this ROI
                target_labels = ROI_DEFINITIONS.get(roi, [])
                
                # Apply colors for each label if it exists in the slice AND is part of the ROI
                # (Or if ROI is "Whole Tumor", show all sub-components)
                # Actually, standard behavior: Show the sub-components that make up the ROI.
                
                for label_id in target_labels:
                    if label_id in ROI_COLORS:
                        idx = (mask_slice == label_id)
                        if np.any(idx):
                            c_val = ROI_COLORS[label_id]
                            rgba[idx, 0] = c_val[0]
                            rgba[idx, 1] = c_val[1]
                            rgba[idx, 2] = c_val[2]
                            rgba[idx, 3] = c_val[3] 

            
            target.mask.setImage(rgba.transpose(1, 0, 2), autoLevels=False, levels=[0, 255]) 
            target.mask.setVisible(True)
        else:
            target.mask.setVisible(False)

    def update_3d_view(self, data, is_mask=False, custom_colors=None, is_diff=False):
        """Renders a 3D isosurface mesh of the segmentation mask with per-class coloring."""
        # Clean up ALL old mesh/scatter/line/text items
        items_to_remove = []
        for item in self.threed_view.items:
            if isinstance(item, (gl.GLMeshItem, gl.GLScatterPlotItem, gl.GLLinePlotItem)):
                items_to_remove.append(item)
        for item in items_to_remove:
            self.threed_view.removeItem(item)
        # Remove text items too
        if hasattr(self, '_3d_text_items'):
            for t in self._3d_text_items:
                try:
                    self.threed_view.removeItem(t)
                except Exception:
                    pass
        self._3d_text_items = []
        
        if not is_mask or data is None:
            return
            
        try:
            # Determine which classes to render based on ROI combo
            roi = "Whole Tumor"
            if hasattr(self, 'combo_metric_class'):
                roi = self.combo_metric_class.currentText() or "Whole Tumor"
            
            # Use shared 3D colors OR custom colors (for diff map)
            class_config = {}
            if custom_colors:
                for lbl, props in custom_colors.items():
                    class_config[lbl] = {"color": props["color"]}
            else:
                for lbl, color in ROI_COLORS_3D.items():
                    class_config[lbl] = {"color": color}
            
            # Filter classes by ROI (only if not diff map)
            if is_diff:
                render_classes = [1, 2, 3] # Diff Map labels are always 1, 2, 3
            else:
                render_classes = ROI_DEFINITIONS.get(roi, [])

            
            # Downsample for performance (factor 2)
            step = 2
            d = data[::step, ::step, ::step]
            center_offset = np.array(data.shape, dtype=np.float32) / 2.0
            
            # Try marching cubes (scikit-image)
            use_mesh = True
            try:
                from skimage.measure import marching_cubes
            except ImportError:
                use_mesh = False
                print("Warning: scikit-image not found, using scatter plot fallback for 3D view.")
            
            for cls in render_classes:
                cls_mask = (d == cls)
                if not np.any(cls_mask):
                    continue
                
                color = class_config.get(cls, {"color": (1.0, 0.0, 1.0, 0.6)})["color"]
                
                if use_mesh:
                    try:
                        # Pad to avoid open edges at boundaries
                        padded = np.pad(cls_mask, 1, mode='constant', constant_values=0)
                        verts, faces, normals, _ = marching_cubes(
                            padded.astype(np.float32), level=0.5,
                            step_size=1, allow_degenerate=False
                        )
                        # Remove padding offset and scale back
                        verts = (verts - 1) * step  # undo pad + downsample
                        verts = verts - center_offset  # center at origin
                        verts[:, 0] = -verts[:, 0]  # Flip X-axis to correct 180° rotation
                        
                        verts = verts.astype(np.float32)
                        faces = faces.astype(np.uint32)
                        
                        # Create mesh colors (per-face)
                        face_colors = np.zeros((len(faces), 4), dtype=np.float32)
                        face_colors[:] = color
                        
                        mesh = gl.GLMeshItem(
                            vertexes=verts,
                            faces=faces,
                            faceColors=face_colors,
                            smooth=True,
                            drawEdges=False,
                            shader='shaded'
                        )
                        mesh.setGLOptions('translucent')
                        self.threed_view.addItem(mesh)
                    except Exception as e:
                        print(f"3D Mesh Error for class {cls}: {e}")
                        self._add_scatter_for_class(d, cls, color, center_offset, step)
                else:
                    self._add_scatter_for_class(d, cls, color, center_offset, step)
            
            # Add bounding box wireframe
            self._add_3d_bounding_box(data.shape)
            
            # Add orientation labels
            self._add_orientation_labels(data.shape)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"3D View Error: {e}")
    
    def _add_scatter_for_class(self, downsampled_data, cls, color, center_offset, step):
        """Fallback: add scatter plot for a single class."""
        pos = np.argwhere(downsampled_data == cls)
        if len(pos) == 0:
            return
        pos = (pos * step).astype(np.float32)
        pos = pos - center_offset
        
        cols = np.zeros((len(pos), 4), dtype=np.float32)
        cols[:] = color
        
        if np.isnan(pos).any() or np.isinf(pos).any():
            return
        
        sp = gl.GLScatterPlotItem(pos=pos, color=cols, size=4, pxMode=True)
        self.threed_view.addItem(sp)
    
    def _add_3d_bounding_box(self, shape):
        """Draw a wireframe bounding box around the volume."""
        s = np.array(shape, dtype=np.float32)
        half = s / 2.0
        
        # 8 corners of the box
        corners = np.array([
            [-half[0], -half[1], -half[2]],
            [ half[0], -half[1], -half[2]],
            [ half[0],  half[1], -half[2]],
            [-half[0],  half[1], -half[2]],
            [-half[0], -half[1],  half[2]],
            [ half[0], -half[1],  half[2]],
            [ half[0],  half[1],  half[2]],
            [-half[0],  half[1],  half[2]],
        ], dtype=np.float32)
        
        # 12 edges of the box
        edges = [
            (0,1),(1,2),(2,3),(3,0),  # bottom face
            (4,5),(5,6),(6,7),(7,4),  # top face
            (0,4),(1,5),(2,6),(3,7),  # vertical edges
        ]
        
        for a, b in edges:
            line = gl.GLLinePlotItem(
                pos=np.array([corners[a], corners[b]], dtype=np.float32),
                color=(0.5, 0.5, 0.6, 0.4),
                width=1.0,
                antialias=True
            )
            self.threed_view.addItem(line)
    
    def _add_orientation_labels(self, shape):
        """Add S/I/R/L/A/P text labels at the bounding box faces."""
        try:
            from pyqtgraph.opengl import GLTextItem
        except ImportError:
            return  # GLTextItem not available in older pyqtgraph
        
        half = np.array(shape, dtype=np.float32) / 2.0
        offset = 10  # extra offset beyond the box
        
        labels = [
            ("R", (-half[0] - offset, 0, 0)),
            ("L", ( half[0] + offset, 0, 0)),
            ("A", (0, -half[1] - offset, 0)),
            ("P", (0,  half[1] + offset, 0)),
            ("I", (0, 0, -half[2] - offset)),
            ("S", (0, 0,  half[2] + offset)),
        ]
        
        self._3d_text_items = []
        for text, pos in labels:
            try:
                txt = GLTextItem(
                    pos=np.array(pos, dtype=np.float32),
                    text=text,
                    color=(255, 255, 255, 200),
                    font=QFont("Arial", scaled(14), QFont.Bold)
                )
                self.threed_view.addItem(txt)
                self._3d_text_items.append(txt)
            except Exception:
                pass  # Skip if GLTextItem causes issues

    def save_screenshot(self):
        # Grab the viewport image
        # Using pyqtgraph export
        from pyqtgraph.exporters import ImageExporter
        
        # Determine which view is "active" or just save the axial
        exporter = ImageExporter(self.axial_view.view)
        exporter.parameters()['width'] = 1024
        
        import os
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", "", "PNG Images (*.png)")
        if path:
            exporter.export(path)

    def export_mask(self):
        if self.mask is None or self.affine is None: return
        
        from app.core.loader import NiftiLoader
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Export Mask", "segmentation.nii.gz", "NIfTI Files (*.nii.gz)")
        if path:
            NiftiLoader.save_file(path, self.mask.astype(np.float32), self.affine)

    def toggle_playback(self, checked):
        if checked:
            self.is_playing = True
            self.btn_play.setText("\u23F8") # Pause icon
            interval = int(1000 / self.slider_speed.value())
            self.playback_timer.start(interval)
        else:
            self.is_playing = False
            self.btn_play.setText("\u25B6") # Play icon
            self.playback_timer.stop()

    def update_playback_interval(self, val):
        if self.playback_timer.isActive():
            interval = int(1000 / val)
            self.playback_timer.start(interval) # Restart with new interval

    def update_playback(self):
        # Advance all sliders by 1
        # Loop if max reached and repeat is on
        
        # Advance Axial
        if self.sl_axial and self.sl_axial.isVisible():
            next_val = self.sl_axial.value() + 1
            if next_val > self.sl_axial.maximum():
                if self.chk_repeat.isChecked():
                    next_val = 0
                else:
                    next_val = self.sl_axial.maximum()
                    # Only stop if this is the primary view or we want to stop on any end
                    # For now, let's stop only if all are at end? Or just loop individual?
                    # "Smart" play usually plays all. If one ends, it loops or stops.
                    # Let's simple-loop axial for now as it's the main usage.
                    # If we aren't looping, we should likely stop the timer if all reached end.
                    self.btn_play.click() # Stop
                    return
            self.sl_axial.setValue(next_val)
        
        # Advance Sagittal
        if self.sl_sagittal and self.sl_sagittal.isVisible():
            next_val = self.sl_sagittal.value() + 1
            if next_val > self.sl_sagittal.maximum():
                if self.chk_repeat.isChecked(): next_val = 0
                else: next_val = self.sl_sagittal.maximum()
            self.sl_sagittal.setValue(next_val)

        # Advance Coronal
        if self.sl_coronal and self.sl_coronal.isVisible():
            next_val = self.sl_coronal.value() + 1
            if next_val > self.sl_coronal.maximum():
                if self.chk_repeat.isChecked(): next_val = 0
                else: next_val = self.sl_coronal.maximum()
            self.sl_coronal.setValue(next_val)
