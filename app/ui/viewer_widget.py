import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, 
    QSlider, QCheckBox, QGridLayout, QFrame, QSplitter, QGroupBox, QSizePolicy,
    QToolBox, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QColor, QFont, QIcon

from app.ui.settings import Settings
from app.core.inference import InferenceEngine
from app.core.image_processor import ImageProcessor
from app.ui.theme import get_theme_palette, apply_theme

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
        
        # Create Grids
        gx = gl.GLGridItem()
        gx.rotate(90, 0, 1, 0)
        gx.translate(-100, 0, 0)
        view.addItem(gx)
        
        gy = gl.GLGridItem()
        gy.rotate(90, 1, 0, 0)
        gy.translate(0, -100, 0)
        view.addItem(gy)
        
        gz = gl.GLGridItem()
        gz.translate(0, 0, -100)
        view.addItem(gz)
        
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
        # 1. AI & Segmentation Section
        self.tools_box = QToolBox()
        self.tools_box.setStyleSheet("background: transparent;") # Allow theme to propagate
        self.tools_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding) # Ensure it expands

        
        # --- Page 1: Inference & Segmentation ---
        page_inference = QWidget()
        pi_layout = QVBoxLayout(page_inference)
        pi_layout.setSpacing(15)
        
        # Modality Selection
        self.add_control_row(pi_layout, "Modality:", self.create_info_button("Select the MRI sequence to view."))
        self.combo_modality = QComboBox()
        self.combo_modality.addItem("T1") 
        self.combo_modality.currentTextChanged.connect(self.change_modality)
        pi_layout.addWidget(self.combo_modality)
        
        # Model A Selection
        self.add_control_row(pi_layout, "Primary Model (A):", self.create_info_button("Main model for segmentation."))
        self.combo_model_a = QComboBox()
        self.combo_model_a.currentIndexChanged.connect(lambda i: self.on_model_changed(i, 'A'))
        pi_layout.addWidget(self.combo_model_a)

        # Model B Selection (For Comparison)
        self.add_control_row(pi_layout, "Secondary Model (B):", self.create_info_button("Optional model for comparison."))
        self.combo_model_b = QComboBox()
        self.combo_model_b.addItem("None (Single Model Mode)")
        self.combo_model_b.currentIndexChanged.connect(lambda i: self.on_model_changed(i, 'B'))
        pi_layout.addWidget(self.combo_model_b)
        
        # Run Button
        self.btn_run = QPushButton("Run Segmentation")
        self.btn_run.setObjectName("AccentButton") 
        self.btn_run.setFixedHeight(40)
        self.btn_run.clicked.connect(self.run_segmentation)
        pi_layout.addWidget(self.btn_run)
        
        pi_layout.addStretch()
        
        # Fix: Add a wrapper QScrollArea to ensure layout respects size hints in Toolbox
        page_inference_scroll = QScrollArea()
        page_inference_scroll.setWidget(page_inference)
        page_inference_scroll.setWidgetResizable(True)
        page_inference_scroll.setStyleSheet("background: transparent; border: none;")
        
        self.tools_box.addItem(page_inference_scroll, "AI Analysis")
         
        self.control_layout.addWidget(self.tools_box)
        
        # 2. Visualization Section
        # --- Page 2: Visualization Options ---
        page_viz = QWidget()
        viz_layout = QVBoxLayout(page_viz)
        viz_layout.setSpacing(12)
        
        # Comparison Toggle
        self.btn_compare = QPushButton("Enable Split Comparison")
        self.btn_compare.setCheckable(True)
        self.btn_compare.toggled.connect(self.toggle_comparison)
        viz_layout.addWidget(self.btn_compare)
        
        self.compare_options = QWidget()
        co_layout = QVBoxLayout(self.compare_options)
        co_layout.setContentsMargins(0,0,0,0)
        co_layout.addWidget(QLabel("Compare Mode:"))
        self.combo_compare_mode = QComboBox()
        self.combo_compare_mode.addItems(["Model A vs Model B", "Model A vs Ground Truth", "Overlay vs Raw"])
        self.combo_compare_mode.currentIndexChanged.connect(lambda: self.update_all_2d_views())
        co_layout.addWidget(self.combo_compare_mode)
        self.compare_options.setVisible(False)
        viz_layout.addWidget(self.compare_options)
        
        # Opacity
        viz_layout.addWidget(QLabel("Mask Transparency"))
        self.slider_opacity = QSlider(Qt.Horizontal)
        self.slider_opacity.setRange(0, 100)
        self.slider_opacity.setValue(50)
        self.slider_opacity.valueChanged.connect(self.update_opacity)
        viz_layout.addWidget(self.slider_opacity)
        
        self.chk_mask = QCheckBox("Show Overlay")
        self.chk_mask.setChecked(True)
        self.chk_mask.toggled.connect(self.toggle_mask)
        viz_layout.addWidget(self.chk_mask)
        
        # Active Overlay Selection (Single View)
        viz_layout.addWidget(QLabel("Active Overlay (Single View):"))
        self.combo_overlay_mode = QComboBox()
        self.combo_overlay_mode.addItems(["Model A", "Model B", "Ground Truth", "Difference (A vs GT)", "Difference (A vs B)"])
        self.combo_overlay_mode.currentIndexChanged.connect(self.on_overlay_mode_changed)
        viz_layout.addWidget(self.combo_overlay_mode)

        viz_layout.addStretch()
        self.tools_box.addItem(page_viz, "Visualization Control")
        
        # 3. Legend & Metrics
        # 3. Legend & Metrics (Combined)
        results_group = QGroupBox("Results & Metrics")
        self.results_layout = QVBoxLayout()
        
        # Comparison Table
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(3) # Metric, Model A, Model B
        self.metrics_table.setHorizontalHeaderLabels(["Metric", "Model A", "Model B"])
        self.metrics_table.verticalHeader().setVisible(False)
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.metrics_table.setFixedHeight(120)
        self.results_layout.addWidget(self.metrics_table)
        
        # Legend (Simplified)
        self.legend_container = QWidget()
        self.legend_layout = QVBoxLayout(self.legend_container)
        self.legend_layout.setContentsMargins(0, 0, 0, 0)
        self.legend_layout.setSpacing(5)
        self.results_layout.addWidget(self.legend_container)
        
        results_group.setLayout(self.results_layout)
        self.control_layout.addWidget(results_group)
        
        self.control_layout.addStretch()
        
        # 4. Navigation & Export
        nav_group = QGroupBox("Navigation & Export")
        nav_layout = QVBoxLayout()
        
        # Sliders
        # create_slice_slider now returns the container (QWidget) to prevent GC issues
        self.sl_control_axial = self.create_slice_slider("Axial")
        self.sl_control_sagittal = self.create_slice_slider("Sagittal")
        self.sl_control_coronal = self.create_slice_slider("Coronal")
        
        # Store direct slider references for logic
        self.sl_axial = self.sl_control_axial.slider
        self.sl_sagittal = self.sl_control_sagittal.slider
        self.sl_coronal = self.sl_control_coronal.slider
        
        nav_layout.addWidget(self.sl_control_axial)
        nav_layout.addWidget(self.sl_control_sagittal)
        nav_layout.addWidget(self.sl_control_coronal)
        
        # Export Buttons
        export_layout = QHBoxLayout()
        self.btn_export = QPushButton("Save .nii")
        self.btn_export.clicked.connect(self.export_mask)
        self.btn_export.setEnabled(False)
        
        self.btn_screenshot = QPushButton("Screenshot")
        self.btn_screenshot.clicked.connect(self.save_screenshot)
        
        export_layout.addWidget(self.btn_export)
        export_layout.addWidget(self.btn_screenshot)
        nav_layout.addLayout(export_layout)
        
        nav_group.setLayout(nav_layout)
        self.control_layout.addWidget(nav_group)
        
        # Initial Legend Update
        self.update_legend()

    def on_overlay_mode_changed(self):
        self.update_legend()
        self.update_all_2d_views()

    def update_legend(self):
        # Clear existing
        for i in reversed(range(self.legend_layout.count())): 
            item = self.legend_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
            
        overlay_text = self.combo_overlay_mode.currentText()
        
        def add_item(color, label):
            row = QWidget()
            l = QHBoxLayout(row)
            l.setContentsMargins(0,0,0,0)
            box = QLabel()
            box.setFixedSize(14, 14)
            # Use border-radius for cleaner look
            box.setStyleSheet(f"background-color: {color}; border-radius: 3px; border: 1px solid #333;")
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 10pt; padding-left: 5px;")
            l.addWidget(box)
            l.addWidget(lbl)
            l.addStretch()
            self.legend_layout.addWidget(row)
        
        # Add Header
        header = QLabel("Legend:")
        header.setStyleSheet("font-weight: bold; color: #8B5CF6; margin-bottom: 5px;")
        self.legend_layout.addWidget(header)
        
        if overlay_text == "Difference Map":
            add_item("#FF3B30", "False Positive (Red)")
            add_item("#007AFF", "False Negative (Blue)")
            add_item("#34C759", "True Positive (Green)")
        else:
            # Standard / GT / Intersection
            add_item("#FF3B30", "Necrosis (NCR) - Red")
            add_item("#34C759", "Edema (ED) - Green")
            add_item("#FFCC00", "Enhancing (ET) - Yellow")

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
        
        model_a_name = self.combo_model_a.currentText()
        model_b_name = self.combo_model_b.currentText()
        is_dual = self.combo_model_b.itemData(self.combo_model_b.currentIndex()) is not None
        
        self.btn_run.setText("Inference Running...")
        self.btn_run.setEnabled(False)
        QFrame.repaint(self)
        
        raw_vol = self.patient_data.get(self.active_modality, self.volume)
        
        # Run Model A
        print(f"Running Model A: {model_a_name}")
        self.prediction_a = self.inference_engine.run_inference(raw_vol, model_a_name)
        
        # Run Model B (if selected)
        if is_dual:
            print(f"Running Model B: {model_b_name}")
            self.prediction_b = self.inference_engine.run_inference(raw_vol, model_b_name)
        else:
            self.prediction_b = None
            
        # Metrics
        if 'seg' in self.patient_data:
            self.ground_truth = self.patient_data['seg']
            self.metrics_a = ImageProcessor.calculate_metrics(self.prediction_a, self.ground_truth)
            if self.prediction_b is not None:
                self.metrics_b = ImageProcessor.calculate_metrics(self.prediction_b, self.ground_truth)
        
        self.update_metrics_table()
        
        # Set View
        self.prediction = self.prediction_a # Default "Prediction" is A
        self.mask = self.prediction_a
        
        self.btn_run.setText("Run Segmentation")
        self.btn_run.setEnabled(True)
        self.btn_export.setEnabled(True)
        
        self.setup_sliders_and_views()

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
        
        # --- Logic for Comparison Mode (Split Screen) ---
        if self.comparison_mode:
            if mode == "Model A vs Model B":
                left_mask = self.prediction_a
                right_mask = self.prediction_b
            elif mode == "Model A vs Ground Truth":
                left_mask = self.prediction_a
                right_mask = self.ground_truth
            elif mode == "Overlay vs Raw":
                left_mask = self.prediction_a
                right_mask = None # Raw only
            
            # Update Left (Main) Views
            self.update_view('axial', dest_viewport=self.axial_view, override_mask=left_mask)
            self.update_view('sagittal', dest_viewport=self.sagittal_view, override_mask=left_mask)
            self.update_view('coronal', dest_viewport=self.coronal_view, override_mask=left_mask)
            
            # Update Right (Compare) Views
            self.update_view('axial', dest_viewport=self.compare_view_axial, override_mask=right_mask, force_no_mask=(right_mask is None))
            self.update_view('sagittal', dest_viewport=self.compare_view_sagittal, override_mask=right_mask, force_no_mask=(right_mask is None))
            self.update_view('coronal', dest_viewport=self.compare_view_coronal, override_mask=right_mask, force_no_mask=(right_mask is None))
            
        else:
            # --- Logic for Single Mode ---
            # Use 'active_overlay_mode' dropdown
            active_mask = None
            is_diff = False
            
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
            else: # Fallback Standard
                 active_mask = self.prediction_a if self.prediction_a is not None else self.mask
            
            self.update_view('axial', override_mask=active_mask, is_diff_map=is_diff)
            self.update_view('sagittal', override_mask=active_mask, is_diff_map=is_diff)
            self.update_view('coronal', override_mask=active_mask, is_diff_map=is_diff)

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
        target.img.setImage(img_data, autoLevels=False, levels=(0, 1)) 
        
        # Update Mask Overlay
        mask_to_use = override_mask if override_mask is not None else self.mask
        
        if mask_to_use is not None and (self.show_mask and not force_no_mask):
            mask_slice = ImageProcessor.get_slice(mask_to_use, plane, idx)
            
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
                rgba[idx1, 3] = 200 # A
                
                # Label 2 (ED)      -> Green
                idx2 = mask_slice == 2
                rgba[idx2, 1] = 255 # G
                rgba[idx2, 3] = 200 # A
                
                # Label 4 (ET)      -> Yellow
                idx4 = mask_slice == 4
                rgba[idx4, 0] = 255 # R
                rgba[idx4, 1] = 255 # G
                rgba[idx4, 3] = 200 # A
                
                # Fallback for any other positive value (e.g. 3 if present)
                idx_other = (mask_slice > 0) & (mask_slice != 1) & (mask_slice != 2) & (mask_slice != 4)
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
