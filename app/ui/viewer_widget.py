import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, 
    QSlider, QCheckBox, QGridLayout, QFrame, QSplitter, QGroupBox, QSizePolicy,
    QToolBox, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QProgressBar, QMessageBox, QToolButton
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QThread
from PyQt5.QtGui import QColor, QFont, QIcon

from app.ui.settings import Settings
from app.core.inference import InferenceEngine
from app.core.image_processor import ImageProcessor
from app.ui.theme import get_theme_palette, apply_theme

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
                print(f"Worker: Running Model A ({self.model_a_config['name']})...")
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
        
        # 3 Viewports + 3D View (Grid)
        self.view_container = QWidget()
        self.view_grid = QGridLayout(self.view_container)
        self.view_grid.setSpacing(4)
        self.view_grid.setContentsMargins(4,4,4,4)
        
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
        
        # Link Viewports (Pan/Zoom Sync)
        self.axial_view.view.setXLink(self.compare_view_axial.view)
        self.axial_view.view.setYLink(self.compare_view_axial.view)
        
        self.sagittal_view.view.setXLink(self.compare_view_sagittal.view)
        self.sagittal_view.view.setYLink(self.compare_view_sagittal.view)
        
        self.coronal_view.view.setXLink(self.compare_view_coronal.view)
        self.coronal_view.view.setYLink(self.compare_view_coronal.view)
        
        self.threed_view = self.create_3d_viewport()
        
        # Default Layout
        self.setup_grid_layout()
        
        # Controls Panel
        self.controls = QFrame()
        self.controls.setObjectName("Sidebar")
        # self.controls.setFixedWidth(350) # Remove fixed width to allow splitter resizing
        self.controls.setMinimumWidth(300) # Set minimum constraint
        self.control_layout = QVBoxLayout(self.controls)
        self.control_layout.setContentsMargins(25, 25, 25, 25)
        self.control_layout.setSpacing(20)
        
        self.setup_controls()
        

        
        # Scroll Area for Controls
        from PyQt5.QtWidgets import QScrollArea
        self.scroll_controls = QScrollArea()
        self.scroll_controls.setWidget(self.controls)
        self.scroll_controls.setWidgetResizable(True)
        self.scroll_controls.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_controls.setStyleSheet("border: none; background: transparent;") # Allow theme to propagate

        # Splitter for Resizable Sidebar
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.view_container)
        self.splitter.addWidget(self.scroll_controls) # Add scroll area instead of frame directly
        
        # Set stretch factors: Viewport (index 0) gets all extra space (1), Sidebar (index 1) gets 0
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        
        # Set initial sizes [large width, sidebar width]
        self.splitter.setSizes([800, 350]) 
        
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
            # 3-Plane Comparison (2 Columns x 3 Rows)
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
            
            # Hide 3D view in this dense mode to save space
            self.threed_view.hide()
            
            # Fix Resizing: Equal Stretch
            self.view_grid.setRowStretch(0, 1)
            self.view_grid.setRowStretch(1, 1)
            self.view_grid.setRowStretch(2, 1)
            self.view_grid.setColumnStretch(0, 1)
            self.view_grid.setColumnStretch(1, 1)
            
        else:
            # Standard Quad View
            self.compare_view_axial.hide()
            self.compare_view_sagittal.hide()
            self.compare_view_coronal.hide()
            
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

    def create_3d_viewport(self):
        view = gl.GLViewWidget()
        view.opts['distance'] = 200
        view.opts['azimuth'] = 45
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
        # --- Section 1: AI Analysis ---
        ai_group = QGroupBox("AI Analysis")
        ai_layout = QVBoxLayout()
        ai_layout.setSpacing(10)
        
        # Modality Selection
        self.add_control_row(ai_layout, "Modality:", self.create_info_button("Select the MRI sequence to view."))
        self.combo_modality = QComboBox()
        self.combo_modality.addItem("T1") 
        self.combo_modality.currentTextChanged.connect(self.change_modality)
        ai_layout.addWidget(self.combo_modality)
        
        # Model A Selection
        self.add_control_row(ai_layout, "Primary Model (A):", self.create_info_button("Main model for segmentation."))
        self.combo_model_a = QComboBox()
        self.combo_model_a.currentIndexChanged.connect(lambda i: self.on_model_changed(i, 'A'))
        ai_layout.addWidget(self.combo_model_a)

        # Model B Selection
        self.add_control_row(ai_layout, "Secondary Model (B):", self.create_info_button("Optional model for comparison."))
        self.combo_model_b = QComboBox()
        self.combo_model_b.addItem("None (Single Model Mode)")
        self.combo_model_b.currentIndexChanged.connect(lambda i: self.on_model_changed(i, 'B'))
        ai_layout.addWidget(self.combo_model_b)
        
        # Run Button & Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { height: 5px; text-align: center; }")
        ai_layout.addWidget(self.progress_bar)
        
        self.btn_run = QPushButton("Run Segmentation")
        self.btn_run.setObjectName("AccentButton")
        self.btn_run.setFixedHeight(35)
        self.btn_run.clicked.connect(self.run_segmentation)
        ai_layout.addWidget(self.btn_run)
        
        ai_group.setLayout(ai_layout)
        self.control_layout.addWidget(ai_group)
        
        # --- Section 2: Visualization Control ---
        viz_group = QGroupBox("Visualization Control")
        viz_layout = QVBoxLayout()
        viz_layout.setSpacing(8)
        
        # Mask Opacity
        viz_layout.addWidget(QLabel("Mask Transparency"))
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setValue(50)
        self.slider_opacity.valueChanged.connect(self.update_opacity)
        viz_layout.addWidget(self.slider_opacity)

        # View Toggles
        toggles_layout = QHBoxLayout()
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
        viz_layout.addLayout(toggles_layout)
        
        # Comparison Controls
        self.btn_compare = QPushButton("Enable Split Comparison")
        self.btn_compare.setCheckable(True)
        self.btn_compare.toggled.connect(self.toggle_comparison)
        viz_layout.addWidget(self.btn_compare)
        
        self.compare_options = QWidget()
        co_layout = QVBoxLayout(self.compare_options)
        co_layout.setContentsMargins(0,0,0,0)
        self.combo_compare_mode = QComboBox()
        self.combo_compare_mode.addItems(["Model A vs Model B", "Model A vs Ground Truth", "Overlay vs Raw"])
        self.combo_compare_mode.currentIndexChanged.connect(lambda: self.update_all_2d_views())
        co_layout.addWidget(self.combo_compare_mode)
        self.compare_options.setVisible(False)
        viz_layout.addWidget(self.compare_options)

        # Active Overlay (Single Mode)
        hbox_overlay = QHBoxLayout()
        hbox_overlay.addWidget(QLabel("Overlay:"))
        self.combo_overlay_mode = QComboBox()
        self.combo_overlay_mode.addItems(["Model A", "Model B", "Ground Truth", "Difference (A vs GT)", "Difference (A vs B)"])
        self.combo_overlay_mode.currentIndexChanged.connect(self.on_overlay_mode_changed)
        hbox_overlay.addWidget(self.combo_overlay_mode)
        viz_layout.addLayout(hbox_overlay)
        
        viz_group.setLayout(viz_layout)
        self.control_layout.addWidget(viz_group)

        # --- Section 3: Results & Metrics ---
        results_group = QGroupBox()
        results_layout = QVBoxLayout()
        results_layout.setSpacing(5)
        
        # Custom Header with Info Button
        r_header = QHBoxLayout()
        r_label = QLabel("Results & Metrics")
        r_label.setStyleSheet("font-weight: bold;")
        r_header.addWidget(r_label)
        r_header.addStretch()
        self.btn_info = QToolButton()
        self.btn_info.setText("?")
        self.btn_info.setObjectName("InfoButton")
        self.btn_info.setFixedSize(20, 20)
        self.btn_info.clicked.connect(self.show_metrics_info)
        r_header.addWidget(self.btn_info)
        results_layout.addLayout(r_header)
        
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(3)
        self.metrics_table.setHorizontalHeaderLabels(["Metric", "Model A", "Model B"])
        self.metrics_table.verticalHeader().setVisible(False)
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.metrics_table.setFixedHeight(100) # Slightly shorter
        results_layout.addWidget(self.metrics_table)
        
        # Legend container
        self.legend_container = QWidget()
        self.legend_layout = QVBoxLayout(self.legend_container)
        self.legend_layout.setContentsMargins(0, 5, 0, 0)
        self.legend_layout.setSpacing(2)
        results_layout.addWidget(self.legend_container)
        
        results_group.setLayout(results_layout)
        self.control_layout.addWidget(results_group)
        
        self.control_layout.addStretch()

        # --- Section 4: Navigation & Export ---
        nav_group = QGroupBox("Navigation")
        nav_layout = QVBoxLayout()
        
        self.sl_control_axial = self.create_slice_slider("Axial")
        self.sl_control_sagittal = self.create_slice_slider("Sagittal")
        self.sl_control_coronal = self.create_slice_slider("Coronal")
        
        self.sl_axial = self.sl_control_axial.slider
        self.sl_sagittal = self.sl_control_sagittal.slider
        self.sl_coronal = self.sl_control_coronal.slider
        
        nav_layout.addWidget(self.sl_control_axial)
        nav_layout.addWidget(self.sl_control_sagittal)
        nav_layout.addWidget(self.sl_control_coronal)
        
        btns_layout = QHBoxLayout()
        self.btn_export = QPushButton("Save .nii")
        self.btn_export.setObjectName("AccentButton")
        self.btn_export.clicked.connect(self.export_mask)
        self.btn_export.setEnabled(False)
        btns_layout.addWidget(self.btn_export)
        
        self.btn_screenshot = QPushButton("Screenshot")
        self.btn_screenshot.clicked.connect(self.save_screenshot)
        btns_layout.addWidget(self.btn_screenshot)
        
        nav_layout.addLayout(btns_layout)
        nav_group.setLayout(nav_layout)
        self.control_layout.addWidget(nav_group)
        
        # Initialize Toggles
        self.show_grid = False
        self.show_crosshair = False
        self.show_mri = True
        
        # Initial Legend Update
        self.update_legend()

    def on_overlay_mode_changed(self):
        self.update_legend()
        self.update_all_2d_views()

    # --- New Visualization Methods ---
    def toggle_grid(self, checked):
        self.show_grid = checked
        for v in [self.axial_view, self.sagittal_view, self.coronal_view,
                  self.compare_view_axial, self.compare_view_sagittal, self.compare_view_coronal]:
            # ViewBox doesn't support showGrid directly, use GridItem
            if not hasattr(v, 'grid_item'):
                v.grid_item = pg.GridItem()
                v.view.addItem(v.grid_item)
            
            v.grid_item.setVisible(checked)

    def toggle_crosshair(self, checked):
        self.show_crosshair = checked
        self.update_all_2d_views() # Repaint to add/remove lines

    def toggle_mri(self, checked):
        self.show_mri = checked
        self.update_all_2d_views()

    def show_metrics_info(self):
        info_text = """
        <b>Dice Coefficient:</b> Measures overlap between prediction and ground truth (1.0 is perfect).<br>
        <b>Sensitivity (Recall):</b> Percentage of actual tumor correctly detected.<br>
        <b>Specificity:</b> Percentage of healthy tissue correctly identified.<br>
        <b>Hausdorff Distance:</b> Maximum distance between prediction boundary and ground truth boundary (lower is better).
        """
        QMessageBox.information(self, "Metrics Explanation", info_text)

    def update_legend(self, mode=None):
        # Clear existing
        for i in reversed(range(self.legend_layout.count())): 
            item = self.legend_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        
        current_combo = self.combo_overlay_mode.currentText()
        target_mode = mode if mode else current_combo
        
        def add_item(color, label):
            row = QWidget()
            l = QHBoxLayout(row)
            l.setContentsMargins(0,0,0,0)
            box = QLabel()
            box.setFixedSize(14, 14)
            box.setStyleSheet(f"background-color: {color}; border-radius: 3px; border: 1px solid #333;")
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 10pt; padding-left: 5px;")
            l.addWidget(box)
            l.addWidget(lbl)
            l.addStretch()
            self.legend_layout.addWidget(row)
        
        # Define Known Classes
        # 1: NCR (Red), 2: ED (Green), 4/3: ET (Yellow)
        
        if target_mode == "Difference Map":
             add_item("#FF3B30", "False Positive (Red)")
             add_item("#007AFF", "False Negative (Blue)")
             add_item("#34C759", "True Positive (Green)")
        else:
             # DYNAMIC LEGEND for Standard Mode
             # If we have a mask, check its values
             active_mask = self.prediction_a if self.prediction_a is not None else self.mask
             
             present_classes = set()
             if active_mask is not None:
                 present_classes = set(np.unique(active_mask).astype(int))
            
             # Keep legend simplified if no mask loaded yet, otherwise show only present
             if not present_classes and active_mask is None:
                 # Show all by default if nothing loaded
                 add_item("#FF3B30", "Necrosis (NCR)")
                 add_item("#34C759", "Edema (ED)")
                 add_item("#FFCC00", "Enhancing (ET)")
             else:
                 if 1 in present_classes: add_item("#FF3B30", "Necrosis (NCR)")
                 if 2 in present_classes: add_item("#34C759", "Edema (ED)")
                 if 4 in present_classes or 3 in present_classes: add_item("#FFCC00", "Enhancing (ET)")
                 
                 if len(present_classes) <= 1 and 0 in present_classes:
                     lbl = QLabel("No tumor detected")
                     lbl.setStyleSheet("color: #777; font-style: italic;")
                     self.legend_layout.addWidget(lbl)
        



    def create_slice_slider(self, label):
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(5)
        
        lbl_widget = QLabel(f"{label}: 0")
        s = QSlider(Qt.Horizontal)
        s.setEnabled(False)
        s.valueChanged.connect(lambda v: self.update_slice(label.lower(), v, lbl_widget))
        
        l.addWidget(lbl_widget)
        l.addWidget(s)
        
        container.slider = s # Keep reference
        return container

    
    def toggle_comparison(self, checked):
        self.comparison_mode = checked
        self.setup_grid_layout()
        self.compare_options.setVisible(checked)
        self.update_all_2d_views()

    def update_slice(self, plane, value, label_widget):
        self.current_slice[plane] = value
        label_widget.setText(f"{plane.capitalize()}: {value}")
        # If in comparison mode, we update both views if axial
        if self.comparison_mode and plane == 'axial':
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

            
    def run_segmentation(self):
        if self.volume is None: return
        
        model_a_data = self.combo_model_a.currentData()
        model_b_data = self.combo_model_b.currentData()
        
        self.btn_run.setText("Inference Running...")
        self.btn_run.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Indeterminate
        QFrame.repaint(self)
        
        # --- Prepare Multimodal Input (4 Channels) ---
        # BraTS models expect [T1, T1ce, T2, FLAIR]
        required_keys = ['t1', 't1ce', 't2', 'flair']
        channels = []
        
        # Determine base shape/volume to use for zeros
        base_vol = self.volume if self.volume is not None else list(self.patient_data.values())[0]
        base_shape = base_vol.shape
             
        # Case-insensitive lookup
        patient_data_lower = {k.lower(): v for k, v in self.patient_data.items()}

        for key in required_keys:
             if key in patient_data_lower:
                 vol = patient_data_lower[key]
                 channels.append(ImageProcessor.normalize(vol))
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
            if len(unique) == 1 and unique[0] == 0:
                QMessageBox.warning(self, "Inference Result", "Model returned empty segmentation (all zeros). Check input data orientation or normalization.")
        
        # Metrics
        if 'seg' in self.patient_data:
            self.ground_truth = self.patient_data['seg']
            if self.prediction_a is not None:
                self.metrics_a = ImageProcessor.calculate_metrics(self.prediction_a, self.ground_truth)
            if self.prediction_b is not None:
                self.metrics_b = ImageProcessor.calculate_metrics(self.prediction_b, self.ground_truth)
        
        self.update_metrics_table()
        
        # Set View
        self.prediction = self.prediction_a # Default "Prediction" is A
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

    def update_metrics_table(self):
        self.metrics_table.clearContents()
        self.metrics_table.setRowCount(0)
        
        if not self.metrics_a: return
        
        # Rows: NCR, ED, ET, WT
        metrics_keys = ["Necrosis", "Edema", "Enhancing", "Whole Tumor"]
        self.metrics_table.setRowCount(len(metrics_keys))
        
        for i, key in enumerate(metrics_keys):
            # Metric Name
            self.metrics_table.setItem(i, 0, QTableWidgetItem(key))
            
            # Model A
            val_a = self.metrics_a.get(key, {}).get("dice", 0.0)
            self.metrics_table.setItem(i, 1, QTableWidgetItem(f"{val_a:.3f}"))
            
            # Model B
            if self.metrics_b:
                val_b = self.metrics_b.get(key, {}).get("dice", 0.0)
                self.metrics_table.setItem(i, 2, QTableWidgetItem(f"{val_b:.3f}"))
            else:
                self.metrics_table.setItem(i, 2, QTableWidgetItem("-"))

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
            
            if self.mask is not None:
                self.update_3d_view(self.mask, is_mask=True)

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
                
            elif mode == "Overlay vs Raw":
                left_mask = self.prediction_a
                right_mask = None # Raw only
                left_title_suffix = " (Overlay)"
                right_title_suffix = " (Raw MRI)"
            
            # Update Titles
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
            
            # Update Right (Compare) Views
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
            # Assuming update_legend exists (it's called elsewhere potentially)
            if hasattr(self, 'update_legend'):
                legend_mode = "Difference Map" if is_diff else "Standard"
                self.update_legend(legend_mode)

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
                # Standard Multi-class coloring
                # Label 1 (NCR/NET) -> Red
                idx1 = mask_slice == 1
                rgba[idx1, 0] = 255 # R
                rgba[idx1, 3] = 200 
                
                # Label 2 (ED)      -> Green
                idx2 = mask_slice == 2
                rgba[idx2, 1] = 255 # G
                rgba[idx2, 3] = 200 
                
                # Label 4 (ET) OR Label 3 -> Yellow
                # Some models output 3, some 4 for Enhancing Tumor
                idx4 = (mask_slice == 4) | (mask_slice == 3)
                rgba[idx4, 0] = 255 # R
                rgba[idx4, 1] = 255 # G
                rgba[idx4, 3] = 200 
                
                # Fallback for any unexpected positive value
                idx_other = (mask_slice > 0) & (mask_slice != 1) & (mask_slice != 2) & (mask_slice != 4) & (mask_slice != 3)
                rgba[idx_other, 0] = 255
                rgba[idx_other, 2] = 255 # Magenta
                rgba[idx_other, 3] = 200
            
            target.mask.setImage(rgba.transpose(1, 0, 2), autoLevels=False, levels=[0, 255]) 
            target.mask.setVisible(True)
        else:
            target.mask.setVisible(False)

    def update_3d_view(self, data, is_mask=False):
        # Clean up old items
        if not is_mask:
             # Basic Volume Rendering (Placeholder: Orthogonal Planes in 3D)
             pass
        else:
             # Isosurface or Point Cloud
             # For performance, maybe just a center slice or simplified mesh
             try:
                 # Thresholding for generating isosurface
                 # This is heavy for python, normally use vtk or marching cubes
                 # For now, let's just clear
                 for i in self.threed_view.items:
                     if isinstance(i, gl.GLMeshItem) or isinstance(i, gl.GLScatterPlotItem):
                         self.threed_view.removeItem(i)
                 
                 # Simple Point Cloud for tumor
                 # Downsample
                 d = data[::4, ::4, ::4]
                 pos = np.argwhere(d > 0)
                 if len(pos) > 0:
                     # Center
                     pos = pos * 4
                     pos = pos - np.array(data.shape)/2
                     
                     # Ensure Float32 for OpenGL position and color
                     pos = pos.astype(np.float32)
                     
                     cols = np.zeros((len(pos), 4), dtype=np.float32)
                     cols[:] = [1.0, 0.0, 0.0, 0.5] # Default Red
                     
                     # Check for NaN or Inf
                     if np.isnan(pos).any() or np.isinf(pos).any():
                         print("Warning: NaN or Inf in 3D data")
                         return

                     sp = gl.GLScatterPlotItem(pos=pos, color=cols, size=5, pxMode=True)
                     self.threed_view.addItem(sp)
             except Exception as e:
                 print(f"3D Error: {e}")

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
