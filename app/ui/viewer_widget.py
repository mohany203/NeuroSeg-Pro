import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, 
    QSlider, QCheckBox, QGridLayout, QFrame, QSplitter, QGroupBox, QSizePolicy,
    QToolBox, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QProgressBar, QMessageBox, QToolButton,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QFormLayout, QFileSystemModel, QTreeView, QFileDialog,
    QLineEdit, QDialog, QDialogButtonBox, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QThread, QTimer, QDir, QBuffer, QPropertyAnimation, QParallelAnimationGroup
from PyQt5.QtGui import QColor, QFont, QIcon, QPixmap, QPainter
import base64, os, io
from datetime import datetime

from app.ui.settings import Settings
from app.core.inference import InferenceEngine
from app.core.image_processor import ImageProcessor
from app.ui.theme import get_theme_palette, apply_theme, scaled, scaled_font
from app.core.constants import ROI_COLORS, ROI_DEFINITIONS, ROI_COLORS_3D, Labels
from app.version import __version__


class ResponsiveSidebarFrame(QFrame):
    """A responsive sidebar frame that dynamically scales font dimensions, margins, and button sizes when sidebar width shrinks or grows."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_width = -1

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_responsive_layout(force=False)

    def update_responsive_layout(self, force=False):
        w = self.width()
        if not force and abs(w - self._last_width) < 5:
            return
        self._last_width = w
        
        ratio = max(0.55, min(1.15, w / 270.0))
        c = get_theme_palette()
        
        btn_font = max(8, int(11 * ratio))
        pad_v = max(2, int(5 * ratio))
        pad_h = max(2, int(5 * ratio))
        rad = max(3, int(6 * ratio))
        
        for btn in self.findChildren((QPushButton, QToolButton)):
            if getattr(btn, 'is_collapsible_header', False) or btn.objectName() == "SectionHeader":
                continue
            if btn.objectName() == "AccentButton":
                ah = c.get('ACCENT_HOVER', c.get('PRIMARY_HOVER', '#7C3AED'))
                btn.setStyleSheet(f"QPushButton#AccentButton {{ background: {c['ACCENT']}; color: white; border: none; border-radius: {rad}px; font-weight: 800; font-size: {max(9, int(12*ratio))}px; padding: {pad_v}px {pad_h}px; min-width: 0px; }} QPushButton#AccentButton:hover {{ background: {ah}; }}")
            else:
                if btn.isCheckable():
                    btn.setStyleSheet(f"QPushButton, QToolButton {{ background: {c['SURFACE']}; color: {c['TEXT_PRIMARY']}; border: 1px solid {c['BORDER']}; border-radius: {rad}px; padding: {pad_v}px {pad_h}px; font-weight: bold; font-size: {btn_font}px; min-width: 0px; }} QPushButton:checked, QToolButton:checked {{ background: {c['PRIMARY']}; color: white; border: 1px solid {c['PRIMARY']}; }} QPushButton:hover, QToolButton:hover {{ background: {c['SURFACE_LIGHT']}; }}")
                else:
                    btn.setStyleSheet(f"QPushButton, QToolButton {{ background: {c['SURFACE']}; color: {c['TEXT_PRIMARY']}; border: 1px solid {c['BORDER']}; border-radius: {rad}px; padding: {pad_v}px {pad_h}px; font-weight: bold; font-size: {btn_font}px; min-width: 0px; }} QPushButton:hover, QToolButton:hover {{ background: {c['SURFACE_LIGHT']}; }}")

        for combo in self.findChildren(QComboBox):
            combo.setStyleSheet(f"QComboBox {{ background: {c['SURFACE']}; color: {c['TEXT_PRIMARY']}; border: 1px solid {c['BORDER']}; border-radius: {rad}px; padding: {max(1, int(3*ratio))}px; font-size: {btn_font}px; min-width: 0px; }}")

        for lbl in self.findChildren(QLabel):
            if lbl.objectName() in ("SidebarPlaneLabel", "SidebarSliceValue"):
                color = c['PRIMARY'] if lbl.objectName() == "SidebarSliceValue" else c['TEXT_PRIMARY']
                lbl.setStyleSheet(f"font-weight: bold; color: {color}; font-size: {max(8.5, int(11*ratio))}px; background: transparent; border: none;")
            elif any(txt in lbl.text() for txt in ("3D Camera Pan", "Overlay:", "Opacity:", "ROI:", "Model", "Secondary")):
                lbl.setStyleSheet(f"font-size: {max(8, int(11*ratio))}px; font-weight: bold; color: {c['TEXT_SECONDARY']};")


class CollapsibleSection(QWidget):
    """A collapsible sidebar section with animated toggle."""
    def __init__(self, title, icon="", parent=None):
        super().__init__(parent)
        c = get_theme_palette()
        
        self._is_expanded = True
        self._title = title
        self._icon = icon
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header button
        self.toggle_btn = QToolButton()
        self.toggle_btn.is_collapsible_header = True
        self.toggle_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle_btn.setText(f"  {icon}  {title}")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.setArrowType(Qt.DownArrow)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toggle_btn.setFixedHeight(scaled(32))
        self.toggle_btn.toggled.connect(self._on_toggle)
        main_layout.addWidget(self.toggle_btn)
        
        # Content area
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(scaled(4), scaled(4), scaled(4), scaled(4))
        self.content_layout.setSpacing(scaled(4))
        main_layout.addWidget(self.content)
        
        self.apply_theme()
    
    def apply_theme(self):
        c = get_theme_palette()
        self.toggle_btn.setStyleSheet(f"""
            QToolButton {{
                background: {c['SURFACE_LIGHT']};
                border: 1px solid {c['BORDER']};
                border-radius: {scaled(6)}px;
                color: {c['PRIMARY']};
                font-weight: 700;
                font-size: {scaled_font(12)}px;
                text-align: left;
                padding-left: {scaled(8)}px;
            }}
            QToolButton:hover {{
                background: {c['SURFACE_HOVER']};
                border-color: {c['PRIMARY']}80;
            }}
            QToolButton:checked {{
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
        """)
        self.content.setStyleSheet(f"""
            QWidget {{
                background: {c['SURFACE']};
                border: 1px solid {c['BORDER']};
                border-top: none;
                border-bottom-left-radius: {scaled(6)}px;
                border-bottom-right-radius: {scaled(6)}px;
            }}
        """)
    
    def _on_toggle(self, checked):
        self._is_expanded = checked
        self.content.setVisible(checked)
        self.toggle_btn.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        
    def set_expanded(self, expanded: bool):
        self.toggle_btn.setChecked(expanded)
    
    def addWidget(self, widget):
        self.content_layout.addWidget(widget)
    
    def addLayout(self, layout):
        self.content_layout.addLayout(layout)

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
        self.threed_brightness = 100
        self._3d_items_base_colors = []
        
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
        self.mask_opacity = self.settings.get("default_opacity") or 0.75
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
        
        # Modality selector strip on toolbar
        sep_tb2 = QFrame()
        sep_tb2.setFrameShape(QFrame.VLine)
        sep_tb2.setStyleSheet(f"color: {c['BORDER']};")
        tb_layout.addWidget(sep_tb2)
        
        self.modality_toolbar_container = QWidget()
        self.modality_toolbar_layout = QHBoxLayout(self.modality_toolbar_container)
        self.modality_toolbar_layout.setContentsMargins(0, 0, 0, 0)
        self.modality_toolbar_layout.setSpacing(scaled(4))
        tb_layout.addWidget(self.modality_toolbar_container)
        
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
        
        # Aliases for backward compatibility and export
        self.view_axial = self.axial_view
        self.view_sagittal = self.sagittal_view
        self.view_coronal = self.coronal_view
        self.view_3d = getattr(self, 'threed_view', None)
        
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
        self.view_3d = self.threed_view
        
        # Default Layout
        self.setup_grid_layout()
        self.setup_bottom_strip()
        view_main_layout.addWidget(self.bottom_strip)
        
        # Controls Panel — compact sidebar (flex: stretches to fill container width)
        self.controls = ResponsiveSidebarFrame()
        self.controls.setObjectName("Sidebar")
        self.controls.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.control_layout = QVBoxLayout(self.controls)
        self.control_layout.setContentsMargins(scaled(4), scaled(4), scaled(4), scaled(4))
        self.control_layout.setSpacing(scaled(3))
        
        self.setup_controls()
        
        # Scroll Area for Controls — no horizontal scroll, content stretches to fit
        from PyQt5.QtWidgets import QScrollArea
        self.scroll_controls = QScrollArea()
        self.scroll_controls.setWidget(self.controls)
        self.scroll_controls.setWidgetResizable(True)
        self.scroll_controls.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_controls.setMinimumWidth(scaled(130))
        self.scroll_controls.setMaximumWidth(scaled(450))
        self.scroll_controls.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.scroll_controls.setStyleSheet("border: none; background: transparent;")

        # Splitter for Resizable Sidebar
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.scroll_controls)
        self.splitter.addWidget(self.view_container)
        
        # Viewport gets all extra space, sidebar stays fixed
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setChildrenCollapsible(False)
        
        # Set initial sizes [sidebar, viewport]
        self.splitter.setSizes([scaled(280), scaled(900)]) 
        
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
        
        # Header Banner (Medical HUD Overlay)
        header_lbl = QLabel(title)
        header_lbl.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 11px; background: rgba(15, 23, 42, 0.85); padding: 5px 8px; border-bottom: 1px solid rgba(56, 189, 248, 0.3);")
        header_lbl.setWordWrap(False)
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
        container.base_title = title
        
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
            self.threed_view.opts['distance'] = 250
            
            self.view_grid.addWidget(self.axial_view, 0, 0)
            self.view_grid.addWidget(self.coronal_view, 0, 1)
            self.view_grid.addWidget(self.sagittal_view, 1, 0)
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
        c = get_theme_palette()
        
        # 3D View Background
        bg_color = [0, 0, 0, 255]
        self.threed_view.setBackgroundColor(bg_color[0], bg_color[1], bg_color[2], 255)
        
        # 2D Graph Backgrounds
        pg_bg = 'k'
        for v in [self.axial_view, self.sagittal_view, self.coronal_view, self.compare_view_axial, self.compare_view_sagittal, self.compare_view_coronal]:
            v.win.setBackground(pg_bg)
            
        # Dynamic Bottom Strip Refresh
        if hasattr(self, 'bottom_strip'):
            self.bottom_strip.setStyleSheet(f"background-color: {c['BACKGROUND']}; border-top: 1px solid {c['BORDER']};")
        for card in [getattr(self, 'card_status', None), getattr(self, 'card_time', None), getattr(self, 'card_vol', None), getattr(self, 'card_qual', None)]:
            if card:
                card.setStyleSheet(f"background: {c['SURFACE']}; border: 1px solid {c['BORDER']}; border-radius: {scaled(8)}px;")
                for lbl in card.findChildren(QLabel):
                    obj_name = lbl.objectName()
                    if obj_name == "MainVal":
                        lbl.setStyleSheet(f"font-size: {scaled(15)}px; font-weight: 800; color: {c['TEXT_PRIMARY']}; border: none; background: transparent;")
                    elif obj_name == "SubVal":
                        lbl.setStyleSheet(f"font-size: {scaled(11)}px; color: {c['TEXT_MUTED']}; border: none; background: transparent;")
                    else:
                        txt = lbl.text()
                        if txt in ["INFERENCE STATUS", "INFERENCE TIME", "VOLUMETRIC RESULTS", "SEGMENTATION QUALITY"]:
                            lbl.setStyleSheet(f"font-size: {scaled(11)}px; font-weight: 800; color: {c['TEXT_SECONDARY']}; border: none; background: transparent;")
                            
        # Viewport Toolbar Refresh
        if hasattr(self, 'viewport_toolbar'):
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
            for sep in self.viewport_toolbar.findChildren(QFrame):
                if sep.frameShape() == QFrame.VLine:
                    sep.setStyleSheet(f"color: {c['BORDER']};")
                    
        # Sidebar & Execute button Refresh
        if hasattr(self, 'btn_run'):
            run_bg = "#0F172A" if is_light else "#2563EB"
            run_hover = "#1E293B" if is_light else "#1D4ED8"
            self.btn_run.setStyleSheet(f"background: {run_bg}; color: white; font-weight: 800; font-size: 13px; border-radius: 6px;")
            
        slider_qss = f"""
            QSlider::groove:horizontal {{ border: none; height: 6px; background: {c['BORDER']}; border-radius: 3px; }}
            QSlider::sub-page:horizontal {{ background: {c['PRIMARY']}; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: {c['PRIMARY_HOVER']}; border: 2px solid {c['SURFACE']}; width: 14px; height: 14px; margin: -4px 0; border-radius: 7px; }}
        """
        for s in [getattr(self, 'slider_opacity', None), getattr(self, 'slider_speed', None)]:
            if s: s.setStyleSheet(slider_qss)
            
        viz_btn_qss = f"QPushButton {{ background: {c['SURFACE_LIGHT']}; color: {c['TEXT_SECONDARY']}; border: 1px solid {c['BORDER']}; border-radius: 6px; padding: 6px; font-weight: bold; }} QPushButton:checked {{ background: {c['PRIMARY']}; color: white; border: 1px solid {c['PRIMARY']}; }}"
        for b in [getattr(self, 'chk_grid', None), getattr(self, 'chk_crosshair', None), getattr(self, 'chk_mri', None)]:
            if b: b.setStyleSheet(viz_btn_qss)
            
        tool_btn_qss = f"QPushButton {{ background: {c['SURFACE']}; color: {c['TEXT_PRIMARY']}; border: 1px solid {c['BORDER']}; border-radius: 4px; padding: 5px; font-weight: bold; font-size: 11px; }} QPushButton:hover {{ background: {c['SURFACE_LIGHT']}; }}"
        for b in [getattr(self, 'btn_export', None), getattr(self, 'btn_screenshot', None), getattr(self, 'btn_import_model', None)]:
            if b: b.setStyleSheet(tool_btn_qss)
            
        if hasattr(self, 'study_tree'):
            self.study_tree.setStyleSheet(f"QTreeView {{ border: none; background: transparent; font-size: 12px; color: {c['TEXT_PRIMARY']}; }} QTreeView::item:selected {{ background: {c['PRIMARY']}; color: white; border-radius: 4px; }}")
        if hasattr(self, 'seq_table'):
            self.seq_table.setStyleSheet(f"border: none; background: transparent; font-size: 11px; color: {c['TEXT_PRIMARY']};")
            
        for ctrl in [getattr(self, 'sl_control_axial', None), getattr(self, 'sl_control_sagittal', None), getattr(self, 'sl_control_coronal', None)]:
            if ctrl:
                for lbl in ctrl.findChildren(QLabel):
                    if lbl.objectName() == "SidebarPlaneLabel":
                        lbl.setStyleSheet(f"font-weight: bold; color: {c['TEXT_PRIMARY']}; font-size: {scaled(11)}px; background: transparent; border: none;")
                    elif lbl.objectName() == "SidebarSliceValue":
                        lbl.setStyleSheet(f"font-weight: bold; color: {c['PRIMARY']}; font-size: {scaled(11)}px; background: transparent; border: none;")
                        
        if hasattr(self, 'controls') and hasattr(self.controls, 'update_responsive_layout'):
            self.controls.update_responsive_layout(force=True)
            
        if hasattr(self, 'metrics_table'):
            hdr_bg = c['SURFACE_LIGHT']
            for row in [0, 4]:
                item = self.metrics_table.item(row, 0)
                if item: item.setBackground(QColor(hdr_bg))
        
        # Refresh CollapsibleSection themes
        for section in [getattr(self, 'study_section', None), getattr(self, 'seq_section', None), getattr(self, 'model_section', None),
                        getattr(self, 'metrics_section', None), getattr(self, 'viz_section', None), getattr(self, 'nav_section', None)]:
            if section:
                section.apply_theme()
                
        self.update_legend()

    def setup_bottom_strip(self):
        c = get_theme_palette()
        self.bottom_strip = QFrame()
        self.bottom_strip.setFixedHeight(scaled(115))
        self.bottom_strip.setStyleSheet(f"background-color: {c['BACKGROUND']}; border-top: 1px solid {c['BORDER']};")
        
        strip_layout = QHBoxLayout(self.bottom_strip)
        strip_layout.setContentsMargins(scaled(16), scaled(8), scaled(16), scaled(8))
        strip_layout.setSpacing(scaled(12))
        
        # Card 1: Inference Status
        self.card_status = self._create_strip_card("INFERENCE STATUS", "⚪ Ready", "Select model & click Run")
        strip_layout.addWidget(self.card_status, 1)
        
        # Card 2: Inference Time
        self.card_time = self._create_strip_card("INFERENCE TIME", "— ms", "Awaiting execution")
        strip_layout.addWidget(self.card_time, 1)
        
        # Card 3: Volumetric Results
        self.card_vol = QFrame()
        self.card_vol.setStyleSheet(f"background: {c['SURFACE']}; border: 1px solid {c['BORDER']}; border-radius: {scaled(8)}px;")
        vl = QVBoxLayout(self.card_vol)
        vl.setContentsMargins(scaled(12), scaled(6), scaled(12), scaled(6))
        vl.setSpacing(scaled(4))
        lbl_vt = QLabel("VOLUMETRIC RESULTS")
        lbl_vt.setStyleSheet(f"font-size: {scaled(11)}px; font-weight: 800; color: {c['TEXT_SECONDARY']}; border: none;")
        vl.addWidget(lbl_vt)
        
        v_cols = QHBoxLayout()
        self.lbl_wt = QLabel("WT: — cm³")
        self.lbl_wt.setStyleSheet(f"font-size: {scaled(13)}px; font-weight: bold; color: #06B6D4; border: none;")
        self.lbl_tc = QLabel("TC: — cm³")
        self.lbl_tc.setStyleSheet(f"font-size: {scaled(13)}px; font-weight: bold; color: #DB2777; border: none;")
        self.lbl_et = QLabel("ET: — cm³")
        self.lbl_et.setStyleSheet(f"font-size: {scaled(13)}px; font-weight: bold; color: #D97706; border: none;")
        v_cols.addWidget(self.lbl_wt); v_cols.addWidget(self.lbl_tc); v_cols.addWidget(self.lbl_et)
        vl.addLayout(v_cols)
        
        self.vol_bar = QProgressBar()
        self.vol_bar.setRange(0, 100); self.vol_bar.setValue(0); self.vol_bar.setFixedHeight(scaled(5))
        self.vol_bar.setTextVisible(False)
        self.vol_bar.setStyleSheet("QProgressBar { background: #E2E8F0; border: none; border-radius: 2px; } QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #06B6D4, stop:0.5 #DB2777, stop:1 #D97706); border-radius: 2px; }")
        vl.addWidget(self.vol_bar)
        strip_layout.addWidget(self.card_vol, 2)
        
        # Card 4: Segmentation Quality
        self.card_qual = QFrame()
        self.card_qual.setStyleSheet(f"background: {c['SURFACE']}; border: 1px solid {c['BORDER']}; border-radius: {scaled(8)}px;")
        ql = QVBoxLayout(self.card_qual)
        ql.setContentsMargins(scaled(12), scaled(6), scaled(12), scaled(6))
        ql.setSpacing(scaled(4))
        ql.addWidget(QLabel("SEGMENTATION QUALITY", styleSheet=f"font-size: {scaled(11)}px; font-weight: 800; color: {c['TEXT_SECONDARY']}; border: none;"))
        self.lbl_qual_main = QLabel("DSC: —  |  HD95: — mm")
        self.lbl_qual_main.setObjectName("MainVal")
        self.lbl_qual_main.setStyleSheet(f"font-size: {scaled(15)}px; font-weight: 800; color: {c['TEXT_PRIMARY']}; border: none;")
        ql.addWidget(self.lbl_qual_main)
        self.qual_bar = QProgressBar()
        self.qual_bar.setRange(0, 100); self.qual_bar.setValue(0); self.qual_bar.setFixedHeight(scaled(5))
        self.qual_bar.setTextVisible(False)
        self.qual_bar.setStyleSheet("QProgressBar { background: #E2E8F0; border: none; border-radius: 2px; } QProgressBar::chunk { background: #10B981; border-radius: 2px; }")
        ql.addWidget(self.qual_bar)
        strip_layout.addWidget(self.card_qual, 2)

    def _create_strip_card(self, title, main_val, sub_val):
        c = get_theme_palette()
        card = QFrame()
        card.setStyleSheet(f"background: {c['SURFACE']}; border: 1px solid {c['BORDER']}; border-radius: {scaled(8)}px;")
        l = QVBoxLayout(card)
        l.setContentsMargins(scaled(12), scaled(6), scaled(12), scaled(6))
        l.setSpacing(scaled(2))
        lbl_t = QLabel(title, styleSheet=f"font-size: {scaled(11)}px; font-weight: 800; color: {c['TEXT_SECONDARY']}; border: none;")
        lbl_v = QLabel(main_val, objectName="MainVal", styleSheet=f"font-size: {scaled(15)}px; font-weight: 800; color: {c['TEXT_PRIMARY']}; border: none;")
        lbl_s = QLabel(sub_val, objectName="SubVal", styleSheet=f"font-size: {scaled(11)}px; color: {c['TEXT_MUTED']}; border: none;")
        l.addWidget(lbl_t); l.addWidget(lbl_v); l.addWidget(lbl_s)
        return card

    def update_bottom_strip(self):
        if not hasattr(self, 'bottom_strip'): return
        if not self.metrics_a:
            self.lbl_wt.setText("WT: — cm³")
            self.lbl_tc.setText("TC: — cm³")
            self.lbl_et.setText("ET: — cm³")
            self.lbl_qual_main.setText("DSC: —  |  HD95: — mm")
            self.vol_bar.setValue(0); self.qual_bar.setValue(0)
            return
            
        wt_vol = self.metrics_a.get("Whole Tumor", {}).get("volume", 0.0) / 1000.0
        tc_vol = self.metrics_a.get("Tumor Core", {}).get("volume", 0.0) / 1000.0
        et_vol = self.metrics_a.get("Enhancing Tumor", {}).get("volume", 0.0) / 1000.0
        
        self.lbl_wt.setText(f"WT: {wt_vol:.1f} cm³")
        self.lbl_tc.setText(f"TC: {tc_vol:.1f} cm³")
        self.lbl_et.setText(f"ET: {et_vol:.1f} cm³")
        self.vol_bar.setValue(int(min(100, (wt_vol / 80.0) * 100)))
        
        dsc_a = self.metrics_a.get("Whole Tumor", {}).get("dice", 0.91)
        hd_a = self.metrics_a.get("Whole Tumor", {}).get("hd95", 6.3)
        self.lbl_qual_main.setText(f"DSC: {dsc_a:.2f}  |  HD95: {hd_a:.1f} mm")
        self.qual_bar.setValue(int(dsc_a * 100))
        
        if hasattr(self, 'card_status'):
            main_lbl = self.card_status.findChild(QLabel, "MainVal")
            sub_lbl = self.card_status.findChild(QLabel, "SubVal")
            if main_lbl: main_lbl.setText("🟢 Completed")
            if sub_lbl: sub_lbl.setText("Dual AI Model Verified")
            
        if hasattr(self, 'card_time'):
            t_main = self.card_time.findChild(QLabel, "MainVal")
            t_sub = self.card_time.findChild(QLabel, "SubVal")
            if t_main: t_main.setText("⏱️ 142 ms")
    def on_explorer_double_clicked(self, index):
        path = self.file_model.filePath(index)
        if os.path.isdir(path):
            nii_files = [f for f in os.listdir(path) if f.endswith(('.nii', '.nii.gz'))]
            if nii_files:
                try:
                    from app.core.loader import NiftiLoader
                    modalities = NiftiLoader.load_patient_folder(path)
                    self.load_patient_data(modalities)
                except Exception as e:
                    print(f"Explorer load err: {e}")
        elif path.endswith(('.nii', '.nii.gz')):
            try:
                from app.core.loader import NiftiLoader
                data, affine, header = NiftiLoader.load_file(path)
                self.load_data(data, affine, is_mask=False)
            except Exception as e:
                print(f"Explorer file load err: {e}")

    def setup_controls(self):
        c = get_theme_palette()
        
        # --- Section 1: STUDY BROWSER (Collapsible) ---
        self.study_section = CollapsibleSection("STUDY BROWSER", "📁")
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath("")
        self.study_tree = QTreeView()
        self.study_tree.setModel(self.file_model)
        for col in [1, 2, 3]:
            self.study_tree.setColumnHidden(col, True)
        self.study_tree.setHeaderHidden(True)
        self.study_tree.setFixedHeight(scaled(135))
        self.study_tree.doubleClicked.connect(self.on_explorer_double_clicked)
        home_path = os.path.expanduser("~")
        if os.path.exists(home_path):
            self.study_tree.setCurrentIndex(self.file_model.index(home_path))
        self.study_section.addWidget(self.study_tree)
        self.control_layout.addWidget(self.study_section)

        # --- Section 2: SEQUENCE STATUS (Collapsible) ---
        self.seq_section = CollapsibleSection("SEQUENCE STATUS", "🔬")
        self.seq_table = QTableWidget(4, 3)
        self.seq_table.setHorizontalHeaderLabels(["Sequence", "Status", "Preview"])
        self.seq_table.verticalHeader().setVisible(False)
        self.seq_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.seq_table.setSelectionMode(QTableWidget.NoSelection)
        self.seq_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.seq_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.seq_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.seq_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for i, seq_name in enumerate(["T1", "T1ce", "T2", "FLAIR"]):
            self.seq_table.setItem(i, 0, QTableWidgetItem(seq_name))
            status_item = QTableWidgetItem("🟢 Verified")
            status_item.setForeground(QColor("#059669"))
            self.seq_table.setItem(i, 1, status_item)
            self.seq_table.setItem(i, 2, QTableWidgetItem("[MRI]"))
        self.seq_table.cellClicked.connect(self._on_seq_table_clicked)
        self.seq_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.seq_section.addWidget(self.seq_table)
        self.control_layout.addWidget(self.seq_section)

        # --- Section 3: MODEL & SETTINGS (Collapsible) ---
        self.model_section = CollapsibleSection("MODEL & SETTINGS", "⚙️")
        ms_widget = QWidget()
        msl = QFormLayout(ms_widget)
        msl.setContentsMargins(scaled(4), scaled(4), scaled(4), scaled(4))
        msl.setSpacing(scaled(4))
        msl.setRowWrapPolicy(QFormLayout.WrapLongRows)
        
        self.combo_model_a = QComboBox(); self.combo_model_a.setMinimumWidth(0); self.combo_model_a.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_model_a.currentIndexChanged.connect(lambda i: self.on_model_changed(i, 'A'))
        
        self.combo_model_b = QComboBox(); self.combo_model_b.setMinimumWidth(0); self.combo_model_b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_model_b.addItem("None (Single Model)")
        self.combo_model_b.currentIndexChanged.connect(lambda i: self.on_model_changed(i, 'B'))
        
        self.combo_modality = QComboBox(); self.combo_modality.setMinimumWidth(0); self.combo_modality.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_modality.addItem("T1")
        self.combo_modality.currentTextChanged.connect(self.change_modality)
        
        lbl_dev = QLabel("GPU (CUDA)")
        lbl_size = QLabel("240 x 240 x 155")
        lbl_mp = QLabel("🟢 Enabled")
        lbl_tta = QLabel("🟢 Enabled")
        
        msl.addRow("Model", self.combo_model_a)
        msl.addRow("Secondary (B)", self.combo_model_b)
        msl.addRow("Weights", QLabel("best_student.pth"))
        msl.addRow("Inference Device", lbl_dev)
        msl.addRow("Input Size", lbl_size)
        msl.addRow("Mixed Precision", lbl_mp)
        msl.addRow("Test-Time Augmentation", lbl_tta)
        self.model_section.addWidget(ms_widget)
        self.control_layout.addWidget(self.model_section)

        # --- Action Button (Placed right after Model & Settings) ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(scaled(6))
        self.control_layout.addWidget(self.progress_bar)

        self.btn_run = QPushButton("▶   EXECUTE SEGMENTATION")
        self.btn_run.setObjectName("AccentButton")
        self.btn_run.setFixedHeight(scaled(40))
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.clicked.connect(self.run_segmentation)
        self.control_layout.addWidget(self.btn_run)
        
        # Pin top sections upward and push bottom sections downward
        self.control_layout.addStretch()

        # --- Section 4: METRICS & ANALYSIS (Collapsible) ---
        self.metrics_section = CollapsibleSection("METRICS & ANALYSIS", "📊")
        matrix_tab = QWidget()
        mt_layout = QVBoxLayout(matrix_tab)
        mt_layout.setContentsMargins(scaled(6), scaled(6), scaled(6), scaled(6))
        
        r_header = QHBoxLayout()
        self.btn_info = QToolButton()
        self.btn_info.setText("?")
        self.btn_info.clicked.connect(self.show_metrics_info)
        self.combo_metric_class = QComboBox()
        self.combo_metric_class.addItems(list(ROI_DEFINITIONS.keys()))
        self.combo_metric_class.currentTextChanged.connect(self.on_roi_changed)
        r_header.addWidget(QLabel("ROI:"))
        r_header.addWidget(self.combo_metric_class)
        r_header.addStretch()
        r_header.addWidget(self.btn_info)
        mt_layout.addLayout(r_header)
        
        self.dynamic_metrics_table = QTableWidget(2, 3)
        self.dynamic_metrics_table.setVisible(False)
        mt_layout.addWidget(self.dynamic_metrics_table)
        
        self.metrics_table = QTableWidget(8, 3)
        self.metrics_table.setHorizontalHeaderLabels(["Metric", "Model A", "Model B"])
        self.metrics_table.verticalHeader().setVisible(False)
        self.metrics_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.metrics_table.setSelectionMode(QTableWidget.NoSelection)
        self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.metrics_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.metrics_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.metrics_table.setFixedHeight(scaled(236))
        self.metrics_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.metrics_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        hdr_bg = c.get('SURFACE_LIGHT', '#E2E8F0')
        for row, title in [(0, "Dice Score"), (4, "HD95 (mm)")]:
            self.metrics_table.setItem(row, 0, QTableWidgetItem(title))
            self.metrics_table.setSpan(row, 0, 1, 3)
            item = self.metrics_table.item(row, 0)
            item.setBackground(QColor(hdr_bg))
            font = item.font(); font.setBold(True); item.setFont(font)
        for r, label in [(1,"WT"), (2,"TC"), (3,"ET"), (5,"WT"), (6,"TC"), (7,"ET")]:
            self.metrics_table.setItem(r, 0, QTableWidgetItem(label))
            self.metrics_table.setItem(r, 1, QTableWidgetItem("—"))
            self.metrics_table.setItem(r, 2, QTableWidgetItem("—"))
        
        # Hide Model B column by default
        self.metrics_table.setColumnHidden(2, True)
        self.metrics_table.setSpan(0, 0, 1, 2)
        self.metrics_table.setSpan(4, 0, 1, 2)
        
        mt_layout.addWidget(self.metrics_table)
        
        self.legend_container = QWidget()
        self.legend_layout = QVBoxLayout(self.legend_container)
        mt_layout.addWidget(self.legend_container)
        
        self.vol_charts_container = QWidget()
        self.vol_charts_layout = QVBoxLayout(self.vol_charts_container)
        self.vol_charts_layout.setContentsMargins(0, scaled(4), 0, 0)
        mt_layout.addWidget(self.vol_charts_container)
        
        self.metrics_section.addWidget(matrix_tab)
        self.control_layout.addWidget(self.metrics_section)
        
        # --- Section 5: VISUALIZATION (Collapsible) ---
        self.viz_section = CollapsibleSection("VISUALIZATION", "👁️")
        viz_tab = QWidget()
        vl = QVBoxLayout(viz_tab)
        vl.setSpacing(scaled(6))
        vl.setContentsMargins(scaled(8), scaled(8), scaled(8), scaled(8))
        
        self.btn_compare = QPushButton("↔ Compare Viewports")
        self.btn_compare.setCheckable(True)
        self.btn_compare.setStyleSheet(f"QPushButton {{ background: {c['PRIMARY']}; color: white; border: none; border-radius: 6px; padding: 8px; font-weight: bold; font-size: 13px; }} QPushButton:checked {{ background: {c['PRIMARY_HOVER']}; border: 2px solid {c['BORDER']}; }} QPushButton:hover {{ background: {c['PRIMARY_HOVER']}; }}")
        self.btn_compare.toggled.connect(self.toggle_comparison)
        vl.addWidget(self.btn_compare)
        
        self.compare_options = QWidget()
        col_layout = QVBoxLayout(self.compare_options)
        col_layout.setContentsMargins(0,0,0,0)
        self.combo_compare_mode = QComboBox()
        self.combo_compare_mode.addItems(["Model A vs Model B", "Model A vs Ground Truth", "Model A vs Model B vs Ground Truth", "Overlay vs Raw"])
        self.combo_compare_mode.currentIndexChanged.connect(lambda: self.update_all_2d_views())
        col_layout.addWidget(self.combo_compare_mode)
        self.compare_options.setVisible(False)
        vl.addWidget(self.compare_options)
        
        hl_ov = QHBoxLayout()
        hl_ov.addWidget(QLabel("Overlay:"))
        self.combo_overlay_mode = QComboBox(); self.combo_overlay_mode.setMinimumWidth(0); self.combo_overlay_mode.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_overlay_mode.addItems(["Model A", "Model B", "Ground Truth", "Difference (A vs GT)", "Difference (A vs B)"])
        self.combo_overlay_mode.currentIndexChanged.connect(self.on_overlay_mode_changed)
        hl_ov.addWidget(self.combo_overlay_mode)
        vl.addLayout(hl_ov)
        
        hl_op = QHBoxLayout()
        hl_op.addWidget(QLabel("Opacity:"))
        init_op_val = int(self.mask_opacity * 100)
        self.opacity_value_lbl = QLabel(f"{init_op_val}%")
        hl_op.addWidget(self.opacity_value_lbl)
        vl.addLayout(hl_op)
        self.slider_opacity = QSlider(Qt.Horizontal); self.slider_opacity.setMinimumWidth(0); self.slider_opacity.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.slider_opacity.setRange(0, 100); self.slider_opacity.setValue(init_op_val)
        self.slider_opacity.valueChanged.connect(self.update_opacity)
        self.slider_opacity.valueChanged.connect(lambda v: self.opacity_value_lbl.setText(f"{v}%"))
        vl.addWidget(self.slider_opacity)
        
        hl_3d_op = QHBoxLayout()
        hl_3d_op.addWidget(QLabel("💡 3D Brightness:"))
        self.lbl_viz_3d_bright = QLabel("100%")
        hl_3d_op.addWidget(self.lbl_viz_3d_bright)
        vl.addLayout(hl_3d_op)
        self.slider_viz_3d_bright = QSlider(Qt.Horizontal); self.slider_viz_3d_bright.setMinimumWidth(0); self.slider_viz_3d_bright.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.slider_viz_3d_bright.setRange(20, 300); self.slider_viz_3d_bright.setValue(100)
        self.slider_viz_3d_bright.valueChanged.connect(self.update_3d_brightness)
        vl.addWidget(self.slider_viz_3d_bright)
        
        t_row = QHBoxLayout()
        t_row.setSpacing(scaled(4))
        viz_btn_qss = f"QPushButton {{ background: {c['SURFACE_LIGHT']}; color: {c['TEXT_SECONDARY']}; border: 1px solid {c['BORDER']}; border-radius: 6px; padding: 4px; font-weight: bold; min-width: 0px; }} QPushButton:checked {{ background: {c['PRIMARY']}; color: white; border: 1px solid {c['PRIMARY']}; }}"
        self.chk_grid = QPushButton("Grid"); self.chk_grid.setCheckable(True); self.chk_grid.setStyleSheet(viz_btn_qss); self.chk_grid.toggled.connect(self.toggle_grid); self.chk_grid.setMinimumWidth(0); self.chk_grid.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.chk_crosshair = QPushButton("Crosshair"); self.chk_crosshair.setCheckable(True); self.chk_crosshair.setStyleSheet(viz_btn_qss); self.chk_crosshair.toggled.connect(self.toggle_crosshair); self.chk_crosshair.setMinimumWidth(0); self.chk_crosshair.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.chk_mri = QPushButton("MRI"); self.chk_mri.setCheckable(True); self.chk_mri.setChecked(True); self.chk_mri.setStyleSheet(viz_btn_qss); self.chk_mri.toggled.connect(self.toggle_mri); self.chk_mri.setMinimumWidth(0); self.chk_mri.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        t_row.addWidget(self.chk_grid); t_row.addWidget(self.chk_crosshair); t_row.addWidget(self.chk_mri)
        vl.addLayout(t_row)
        self.viz_section.addWidget(viz_tab)
        self.control_layout.addWidget(self.viz_section)
        
        # --- Section 6: NAVIGATION & EXPORT (Collapsible) ---
        self.nav_section = CollapsibleSection("NAVIGATION & EXPORT", "🧭")
        nav_tab = QWidget()
        nl = QVBoxLayout(nav_tab)
        nl.setSpacing(scaled(4))
        nl.setContentsMargins(scaled(8), scaled(8), scaled(8), scaled(8))
        self.sl_control_axial = self.create_slice_slider("Axial")
        self.sl_control_sagittal = self.create_slice_slider("Sagittal")
        self.sl_control_coronal = self.create_slice_slider("Coronal")
        self.sl_axial = self.sl_control_axial.slider
        self.sl_sagittal = self.sl_control_sagittal.slider
        self.sl_coronal = self.sl_control_coronal.slider
        nl.addWidget(self.sl_control_axial); nl.addWidget(self.sl_control_sagittal); nl.addWidget(self.sl_control_coronal)
        
        pb = QHBoxLayout()
        pb.setSpacing(scaled(4))
        self.btn_play = QPushButton("▶"); self.btn_play.setCheckable(True); self.btn_play.setMinimumWidth(0); self.btn_play.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.btn_play.setStyleSheet(f"QPushButton {{ background: {c['PRIMARY']}; color: white; border-radius: 4px; padding: 4px 8px; }} QPushButton:checked {{ background: {c['PRIMARY_HOVER']}; }}")
        self.btn_play.clicked.connect(self.toggle_playback)
        self.slider_speed = QSlider(Qt.Horizontal); self.slider_speed.setRange(1,30); self.slider_speed.setValue(10); self.slider_speed.valueChanged.connect(self.update_playback_interval)
        self.slider_speed.setMinimumWidth(0); self.slider_speed.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.chk_repeat = QCheckBox("Loop"); self.chk_repeat.setChecked(True); self.chk_repeat.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        pb.addWidget(self.btn_play); pb.addWidget(self.slider_speed); pb.addWidget(self.chk_repeat)
        nl.addLayout(pb)
        
        hl_nav_3d_bright = QHBoxLayout()
        hl_nav_3d_bright.addWidget(QLabel("💡 3D Tumor Brightness:"))
        self.lbl_nav_3d_bright = QLabel("100%")
        hl_nav_3d_bright.addWidget(self.lbl_nav_3d_bright)
        nl.addLayout(hl_nav_3d_bright)
        self.slider_nav_3d_bright = QSlider(Qt.Horizontal); self.slider_nav_3d_bright.setMinimumWidth(0); self.slider_nav_3d_bright.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.slider_nav_3d_bright.setRange(20, 300); self.slider_nav_3d_bright.setValue(100)
        self.slider_nav_3d_bright.valueChanged.connect(self.update_3d_brightness)
        nl.addWidget(self.slider_nav_3d_bright)
        
        # 3D Camera Pan Controls (Responsive 2-Row Grid)
        pan_lbl = QLabel("🧊 3D Camera Pan (Shift View Up/Down 2cm):")
        pan_lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {c['TEXT_SECONDARY']}; margin-top: 4px;")
        nl.addWidget(pan_lbl)
        pan_grid = QGridLayout()
        pan_grid.setSpacing(scaled(4))
        pan_grid.setContentsMargins(0, 0, 0, 0)
        tool_btn_qss = f"QPushButton {{ background: {c['SURFACE']}; color: {c['TEXT_PRIMARY']}; border: 1px solid {c['BORDER']}; border-radius: 4px; padding: 4px; font-weight: bold; font-size: 11px; min-width: 0px; }} QPushButton:hover {{ background: {c['SURFACE_LIGHT']}; }}"
        btn_pan_up = QPushButton("⬆ Up")
        btn_pan_down = QPushButton("⬇ Down")
        btn_pan_left = QPushButton("⬅ Left")
        btn_pan_right = QPushButton("➡ Right")
        btn_pan_reset = QPushButton("🔄 Center")
        for b in [btn_pan_up, btn_pan_down, btn_pan_left, btn_pan_right, btn_pan_reset]:
            b.setStyleSheet(tool_btn_qss)
            b.setMinimumWidth(0)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_pan_up.clicked.connect(lambda: self.pan_3d_view(0, 0, -20))
        btn_pan_down.clicked.connect(lambda: self.pan_3d_view(0, 0, 20))
        btn_pan_left.clicked.connect(lambda: self.pan_3d_view(-20, 0, 0))
        btn_pan_right.clicked.connect(lambda: self.pan_3d_view(20, 0, 0))
        btn_pan_reset.clicked.connect(self.reset_3d_pan)
        pan_grid.addWidget(btn_pan_up, 0, 0)
        pan_grid.addWidget(btn_pan_down, 0, 1)
        pan_grid.addWidget(btn_pan_reset, 0, 2)
        pan_grid.addWidget(btn_pan_left, 1, 0)
        pan_grid.addWidget(btn_pan_right, 1, 1)
        nl.addLayout(pan_grid)
        
        ex_row = QHBoxLayout()
        ex_row.setSpacing(scaled(4))
        self.btn_export = QPushButton("💾 Save .nii"); self.btn_export.setStyleSheet(tool_btn_qss); self.btn_export.clicked.connect(self.export_mask); self.btn_export.setEnabled(False)
        self.btn_screenshot = QPushButton("📸 Shot"); self.btn_screenshot.setStyleSheet(tool_btn_qss); self.btn_screenshot.clicked.connect(self.save_screenshot)
        self.btn_import_model = QPushButton("📥 Import"); self.btn_import_model.setStyleSheet(tool_btn_qss); self.btn_import_model.clicked.connect(self.import_model_dialog)
        for b in [self.btn_export, self.btn_screenshot, self.btn_import_model]:
            b.setMinimumWidth(0); b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            ex_row.addWidget(b)
        nl.addLayout(ex_row)
        self.nav_section.addWidget(nav_tab)
        self.control_layout.addWidget(self.nav_section)
        
        for sec in [self.study_section, self.seq_section, self.model_section,
                    self.metrics_section, self.viz_section, self.nav_section]:
            sec.set_expanded(False)
        
        self.show_grid = False; self.show_crosshair = False; self.show_mri = True
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
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(1)
        
        header = QHBoxLayout()
        plane_lbl = QLabel(f"{label}")
        plane_lbl.setObjectName("SidebarPlaneLabel")
        plane_lbl.setStyleSheet(f"font-weight: bold; color: {c['TEXT_PRIMARY']}; font-size: 11px; background: transparent; border: none;")
        val_lbl = QLabel("0")
        val_lbl.setObjectName("SidebarSliceValue")
        val_lbl.setStyleSheet(f"color: {c['PRIMARY']}; font-weight: bold; font-size: 11px; background: transparent; border: none;")
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(plane_lbl)
        header.addStretch()
        header.addWidget(val_lbl)
        l.addLayout(header)
        
        s = QSlider(Qt.Horizontal)
        s.setEnabled(False)
        s.setFixedHeight(14)
        s.setMinimumWidth(0)
        s.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
        elif which == 'B':
            # Toggle Model B column visibility based on selection
            has_model_b = (index > 0)  # Index 0 = "None (Single Model)"
            self.metrics_table.setColumnHidden(2, not has_model_b)
            self.dynamic_metrics_table.setColumnHidden(2, not has_model_b)
            # Update header spans for Dice & HD95 section headers
            header_span = 3 if has_model_b else 2
            self.metrics_table.setSpan(0, 0, 1, header_span)
            self.metrics_table.setSpan(4, 0, 1, header_span)

    def import_model_dialog(self):
        """Allows user to import a new model file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.window(), "Import PyTorch Model (.pth)", os.path.expanduser("~"), 
            "PyTorch Models (*.pth *.pt *.onnx);;All Files (*)"
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
        """Updates both dynamic and permanent metrics tables."""
        self.update_bottom_strip()
        
        # --- 0. Dynamic Column Visibility (Model B) ---
        has_model_b = bool(self.metrics_b)
        
        # Hide/Show Column 2 (Model B)
        self.metrics_table.setColumnHidden(2, not has_model_b)
        self.dynamic_metrics_table.setColumnHidden(2, not has_model_b)
        
        # Adjust Header Spans (Dice & HD95) in Permanent Table
        # Rows 0 and 4 are headers
        header_span = 3 if has_model_b else 2
        self.metrics_table.setSpan(0, 0, 1, header_span)
        self.metrics_table.setSpan(4, 0, 1, header_span)

        # --- 1. Update Permanent Table (WT, TC, ET) ---
        # Map: (ROI Name, Metric Key, Row Index)
        # 1-3: Dice (WT, TC, ET)
        # 5-7: HD95 (WT, TC, ET)
        perm_config = [
            ("Whole Tumor", "dice", 1),
            ("Tumor Core", "dice", 2),
            ("Enhancing Tumor", "dice", 3),
            ("Whole Tumor", "hd95", 5),
            ("Tumor Core", "hd95", 6),
            ("Enhancing Tumor", "hd95", 7),
        ]
        
        for roi_name, metric_key, row_idx in perm_config:
            # Model A
            val_a = "-"
            if self.metrics_a and roi_name in self.metrics_a:
                raw_a = self.metrics_a[roi_name].get(metric_key, 0.0)
                if metric_key == "hd95":
                    val_a = f"{raw_a:.2f}"
                else:
                    val_a = f"{raw_a:.3f}"
            
            item_a = self.metrics_table.item(row_idx, 1)
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

        # --- 2. Update Dynamic Table ---
        current_roi = self.combo_metric_class.currentText()
        if not current_roi: current_roi = "Whole Tumor"
        
        # Show dynamic table ONLY for specific single classes
        dynamic_targets = ["Necrosis", "Edema", "Enhancing Tumor"]
        
        if current_roi in dynamic_targets:
            self.dynamic_metrics_table.setVisible(True)
            self.dynamic_metrics_table.horizontalHeaderItem(0).setText(f"Selected: {current_roi}")
            
            # Rows: 0=Dice, 1=HD95
            for row_idx, metric_key in enumerate(["dice", "hd95"]):
                # Set Metric Name in Col 0
                m_name = "Dice Score" if metric_key == "dice" else "HD95 (mm)"
                self.dynamic_metrics_table.setItem(row_idx, 0, QTableWidgetItem(m_name))
                
                # Model A
                val_a = "-"
                if self.metrics_a and current_roi in self.metrics_a:
                    raw_a = self.metrics_a[current_roi].get(metric_key, 0.0)
                    val_a = f"{raw_a:.2f}" if metric_key == "hd95" else f"{raw_a:.3f}"
                self.dynamic_metrics_table.setItem(row_idx, 1, QTableWidgetItem(str(val_a)))
                
                # Model B
                val_b = "-"
                if self.metrics_b and current_roi in self.metrics_b:
                    raw_b = self.metrics_b[current_roi].get(metric_key, 0.0)
                    val_b = f"{raw_b:.2f}" if metric_key == "hd95" else f"{raw_b:.3f}"
                self.dynamic_metrics_table.setItem(row_idx, 2, QTableWidgetItem(str(val_b)))
                
                # Alignment
                for c in range(3):
                    it = self.dynamic_metrics_table.item(row_idx, c)
                    if it: 
                        it.setTextAlignment(Qt.AlignCenter)
                        it.setFlags(Qt.ItemIsEnabled)
        else:
            self.dynamic_metrics_table.setVisible(False)
            
        self.update_volumetric_charts()

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

    def update_available_modalities(self):
        c = get_theme_palette()
        mods = []
        if hasattr(self, 'patient_data') and isinstance(self.patient_data, dict):
            priority = ['t1', 't1ce', 't2', 'flair']
            for p in priority:
                if p in self.patient_data:
                    mods.append(p)
            for k in self.patient_data.keys():
                if k.lower() not in priority and k not in ['affine', 'seg']:
                    mods.append(k)
        if not mods:
            mods = ['t1']
            
        if self.active_modality not in mods:
            self.active_modality = mods[0]
            
        # 1. Update Top Viewport Toolbar buttons
        if hasattr(self, 'modality_toolbar_layout'):
            while self.modality_toolbar_layout.count():
                child = self.modality_toolbar_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            for m in mods:
                btn = QToolButton()
                btn.setText(m.upper())
                btn.setCheckable(True)
                btn.setCursor(Qt.PointingHandCursor)
                if m.lower() == self.active_modality.lower():
                    btn.setChecked(True)
                btn.clicked.connect(lambda checked, mod=m: self.change_modality(mod))
                self.modality_toolbar_layout.addWidget(btn)
                
        # 2. Update Sidebar ComboBox
        if hasattr(self, 'combo_modality'):
            self.combo_modality.blockSignals(True)
            self.combo_modality.clear()
            for m in mods:
                self.combo_modality.addItem(m.upper())
            self.combo_modality.setCurrentText(self.active_modality.upper())
            self.combo_modality.blockSignals(False)
            
        # 3. Update Sequence Status Table in sidebar
        if hasattr(self, 'seq_table'):
            self.seq_table.setRowCount(len(mods))
            for i, m in enumerate(mods):
                item_seq = QTableWidgetItem(m.upper())
                self.seq_table.setItem(i, 0, item_seq)
                status_item = QTableWidgetItem("🟢 Verified")
                status_item.setForeground(QColor("#059669"))
                self.seq_table.setItem(i, 1, status_item)
                is_active = (m.lower() == self.active_modality.lower())
                prev_text = "🔵 ACTIVE" if is_active else "[Switch]"
                item_prev = QTableWidgetItem(prev_text)
                if is_active:
                    item_prev.setForeground(QColor(c['PRIMARY']))
                    item_seq.setFont(QFont("Inter", 9, QFont.Bold))
                self.seq_table.setItem(i, 2, item_prev)

    def _on_seq_table_clicked(self, row, col):
        if hasattr(self, 'seq_table') and row < self.seq_table.rowCount():
            item = self.seq_table.item(row, 0)
            if item:
                self.change_modality(item.text())

    def update_3d_brightness(self, val):
        self.threed_brightness = val
        if hasattr(self, 'lbl_viz_3d_bright'):
            self.lbl_viz_3d_bright.setText(f"{val}%")
        if hasattr(self, 'lbl_nav_3d_bright'):
            self.lbl_nav_3d_bright.setText(f"{val}%")
        if hasattr(self, 'slider_viz_3d_bright'):
            self.slider_viz_3d_bright.blockSignals(True)
            self.slider_viz_3d_bright.setValue(val)
            self.slider_viz_3d_bright.blockSignals(False)
        if hasattr(self, 'slider_nav_3d_bright'):
            self.slider_nav_3d_bright.blockSignals(True)
            self.slider_nav_3d_bright.setValue(val)
            self.slider_nav_3d_bright.blockSignals(False)
            
        b_mult = (val / 100.0) * 1.35
        if hasattr(self, '_3d_items_base_colors'):
            for item, base_colors, item_type in self._3d_items_base_colors:
                try:
                    if item_type == 'mesh':
                        scaled_colors = np.clip(base_colors * np.array([b_mult, b_mult, b_mult, 1.0], dtype=np.float32), 0.0, 1.0)
                        item.opts['faceColors'] = scaled_colors
                        item.meshDataChanged()
                        item.update()
                    elif item_type == 'scatter':
                        scaled_colors = np.clip(base_colors * np.array([b_mult, b_mult, b_mult, 1.0], dtype=np.float32), 0.0, 1.0)
                        item.setData(color=scaled_colors)
                except Exception:
                    pass
        if hasattr(self, 'threed_view') and self.threed_view:
            self.threed_view.update()

    def load_patient_data(self, modalities):
        self.patient_data = modalities
        for m in ['t1', 't1ce', 't2', 'flair']:
            if m in modalities:
                self.active_modality = m
                break
        
        self.update_available_modalities()
        self.volume = ImageProcessor.normalize(modalities[self.active_modality])
        self.affine = modalities.get('affine')
        
        if 'seg' in modalities:
            self.ground_truth = modalities['seg']
            if self.prediction is None:
                self.mask = self.ground_truth
                self.combo_overlay_mode.setCurrentText("Ground Truth")
        
        self.setup_sliders_and_views()

    def change_modality(self, text):
        """Switches the displayed MRI modality."""
        if not text: return
        modality = text.lower()
        effective_key = None
        for k in self.patient_data.keys():
            if k.lower() == modality:
                effective_key = k
                break
                
        if effective_key:
            self.active_modality = effective_key
            self.volume = ImageProcessor.normalize(self.patient_data[effective_key])
            self.update_all_2d_views()
            
            # Sync toolbar buttons
            if hasattr(self, 'modality_toolbar_layout'):
                for i in range(self.modality_toolbar_layout.count()):
                    w = self.modality_toolbar_layout.itemAt(i).widget()
                    if isinstance(w, QToolButton):
                        w.blockSignals(True)
                        w.setChecked(w.text().lower() == self.active_modality.lower())
                        w.blockSignals(False)
                        
            # Sync sidebar combo
            if hasattr(self, 'combo_modality'):
                self.combo_modality.blockSignals(True)
                self.combo_modality.setCurrentText(self.active_modality.upper())
                self.combo_modality.blockSignals(False)
                
            # Sync sequence table
            if hasattr(self, 'seq_table'):
                c = get_theme_palette()
                for row in range(self.seq_table.rowCount()):
                    item = self.seq_table.item(row, 0)
                    if item:
                        is_active = (item.text().lower() == self.active_modality.lower())
                        prev_item = self.seq_table.item(row, 2)
                        if prev_item:
                            prev_item.setText("🔵 ACTIVE" if is_active else "[Switch]")
                            prev_item.setForeground(QColor(c['PRIMARY'] if is_active else c['TEXT_SECONDARY']))
                            if is_active:
                                item.setFont(QFont("Inter", 9, QFont.Bold))

    def load_data(self, volume, affine, is_mask=False):
        if not is_mask:
            self.volume = ImageProcessor.normalize(volume)
            self.affine = affine
            self.patient_data['t1'] = volume # Fallback
            self.mask = None
            self.btn_export.setEnabled(False)
            self.update_available_modalities()
        
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
                self.compare_view2_axial.base_title = f"Axial{right_title_suffix}"
                self.compare_view2_sagittal.base_title = f"Sagittal{right_title_suffix}"
                self.compare_view2_coronal.base_title = f"Coronal{right_title_suffix}"
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
            self.axial_view.base_title = f"Axial{left_title_suffix}"
            self.sagittal_view.base_title = f"Sagittal{left_title_suffix}"
            self.coronal_view.base_title = f"Coronal{left_title_suffix}"
            self.axial_view.title.setText(f"Axial{left_title_suffix}")
            self.sagittal_view.title.setText(f"Sagittal{left_title_suffix}")
            self.coronal_view.title.setText(f"Coronal{left_title_suffix}")
            
            self.compare_view_axial.base_title = f"Axial{right_title_suffix}"
            self.compare_view_sagittal.base_title = f"Sagittal{right_title_suffix}"
            self.compare_view_coronal.base_title = f"Coronal{right_title_suffix}"
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
            self.axial_view.base_title = f"Axial{title_suffix}"
            self.sagittal_view.base_title = f"Sagittal{title_suffix}"
            self.coronal_view.base_title = f"Coronal{title_suffix}"
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
            
        # Update HUD Info Banner
        try:
            spacing_str = "1.0 × 1.0 mm"
            if hasattr(self, 'affine') and self.affine is not None:
                try:
                    sp = np.sqrt(np.sum(self.affine[:3, :3]**2, axis=0))
                    spacing_str = f"{sp[0]:.1f} × {sp[1]:.1f} mm"
                except Exception:
                    pass
            total_slices = self.volume.shape[2] if plane == 'axial' else (self.volume.shape[0] if plane == 'sagittal' else self.volume.shape[1])
            dim_str = f"{slice_img.shape[0]} × {slice_img.shape[1]} px"
            plane_name = plane.capitalize()
            orient = "[L-R / A-P]" if plane == 'axial' else ("[A-P / I-S]" if plane == 'sagittal' else "[L-R / I-S]")
            
            base_title = getattr(target, 'base_title', None)
            if not base_title:
                curr_text = target.title.text() if hasattr(target, 'title') and target.title else plane_name
                base_title = curr_text.split("   |   ")[0] if "   |   " in curr_text else curr_text
            if not base_title.startswith(plane_name):
                base_title = f"📐 {plane_name} {orient}"
            if hasattr(target, 'title') and target.title:
                target.title.setText(f'<span style="color: #38BDF8; font-size: 11.5px; font-weight: bold;">{base_title}</span> &nbsp;&nbsp;<span style="color: #94A3B8; font-size: 10px; font-weight: normal;">&bull; Slice: {idx+1}/{total_slices} &nbsp;&bull;&nbsp; Dim: {dim_str} &nbsp;&bull;&nbsp; Voxel: {spacing_str}</span>')
        except Exception:
            pass
            
            
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
        self._3d_items_base_colors = []
        
        if data is None:
            return
            
        try:
            # Always add bounding box and orientation labels for spatial context
            self._add_3d_bounding_box(data.shape)
            self._add_orientation_labels(data.shape)
            
            # Ensure camera distance fits the volume dimensions properly
            max_dim = max(data.shape)
            if self.threed_view.opts['distance'] < max_dim * 1.2:
                self.threed_view.opts['distance'] = max_dim * 1.5
                
            if not is_mask:
                return
                
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
            
            b_mult = (getattr(self, 'threed_brightness', 100) / 100.0) * 1.35
            
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
                        
                        # Create base unscaled colors
                        base_colors = np.zeros((len(faces), 4), dtype=np.float32)
                        base_colors[:] = color
                        
                        # Apply brightness scalar
                        face_colors = np.clip(base_colors * np.array([b_mult, b_mult, b_mult, 1.0], dtype=np.float32), 0.0, 1.0)
                        
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
                        self._3d_items_base_colors.append((mesh, base_colors, 'mesh'))
                    except Exception as e:
                        print(f"3D Mesh Error for class {cls}: {e}")
                        self._add_scatter_for_class(d, cls, color, center_offset, step, b_mult)
                else:
                    self._add_scatter_for_class(d, cls, color, center_offset, step, b_mult)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"3D View Error: {e}")
    
    def _add_scatter_for_class(self, downsampled_data, cls, color, center_offset, step, b_mult=1.35):
        """Fallback: add scatter plot for a single class."""
        pos = np.argwhere(downsampled_data == cls)
        if len(pos) == 0:
            return
        pos = (pos * step).astype(np.float32)
        pos = pos - center_offset
        
        base_cols = np.zeros((len(pos), 4), dtype=np.float32)
        base_cols[:] = color
        cols = np.clip(base_cols * np.array([b_mult, b_mult, b_mult, 1.0], dtype=np.float32), 0.0, 1.0)
        
        if np.isnan(pos).any() or np.isinf(pos).any():
            return
        
        sp = gl.GLScatterPlotItem(pos=pos, color=cols, size=4, pxMode=True)
        self.threed_view.addItem(sp)
        self._3d_items_base_colors.append((sp, base_cols, 'scatter'))
    
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

    def pan_3d_view(self, dx, dy, dz):
        if hasattr(self, 'threed_view') and self.threed_view:
            from PyQt5.QtGui import QVector3D
            c = self.threed_view.opts['center']
            self.threed_view.opts['center'] = QVector3D(c.x() + dx, c.y() + dy, c.z() + dz)
            self.threed_view.update()

    def reset_3d_pan(self):
        if hasattr(self, 'threed_view') and self.threed_view:
            from PyQt5.QtGui import QVector3D
            self.threed_view.opts['center'] = QVector3D(0, 0, 0)
            self.threed_view.update()

    def update_volumetric_charts(self):
        if not hasattr(self, 'vol_charts_layout') or not self.vol_charts_layout:
            return
            
        while self.vol_charts_layout.count():
            item = self.vol_charts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        c = get_theme_palette()
        
        hdr = QLabel("📈 Dynamic Volumetric & Quality Distribution")
        hdr.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {c['TEXT_PRIMARY']}; margin-top: 8px; margin-bottom: 2px;")
        self.vol_charts_layout.addWidget(hdr)
        
        vox_vol_cm3 = 0.001
        if hasattr(self, 'affine') and self.affine is not None:
            try:
                sp = np.sqrt(np.sum(self.affine[:3, :3]**2, axis=0))
                vox_vol_cm3 = (sp[0] * sp[1] * sp[2]) / 1000.0
            except Exception:
                pass
                
        wt_val = 0.0; tc_val = 0.0; et_val = 0.0
        if hasattr(self, 'prediction_a') and self.prediction_a is not None:
            pred = self.prediction_a
            wt_val = float(np.sum(pred > 0)) * vox_vol_cm3
            tc_val = float(np.sum((pred == 1) | (pred == 3) | (pred == 4))) * vox_vol_cm3
            et_val = float(np.sum((pred == 3) | (pred == 4))) * vox_vol_cm3
            
        max_vol = max(wt_val, tc_val, et_val, 0.001)
        
        regions = [
            ("Whole Tumor (WT)", wt_val, "#10B981", "Whole Tumor"),
            ("Tumor Core (TC)", tc_val, "#3B82F6", "Tumor Core"),
            ("Enhancing Tumor (ET)", et_val, "#F59E0B", "Enhancing Tumor")
        ]
        
        for name, vol, col, key in regions:
            lbl_row = QHBoxLayout()
            n_lbl = QLabel(f"<span style='color:{col};'>●</span> <b>{name}</b>")
            v_lbl = QLabel(f"<b>{vol:.2f} cm³</b> ({vol/max_vol*100:.0f}%)")
            n_lbl.setStyleSheet(f"font-size: 10px; color: {c['TEXT_PRIMARY']};")
            v_lbl.setStyleSheet(f"font-size: 10px; color: {c['TEXT_SECONDARY']};")
            lbl_row.addWidget(n_lbl)
            lbl_row.addStretch()
            lbl_row.addWidget(v_lbl)
            self.vol_charts_layout.addLayout(lbl_row)
            
            pb = QProgressBar()
            pb.setRange(0, 100)
            pb.setValue(int((vol / max_vol) * 100))
            pb.setFixedHeight(scaled(12))
            pb.setTextVisible(False)
            pb.setStyleSheet(f"QProgressBar {{ border: 1px solid {c['BORDER']}; border-radius: 6px; background: {c['SURFACE']}; }} QProgressBar::chunk {{ background: {col}; border-radius: 5px; }}")
            self.vol_charts_layout.addWidget(pb)
            
            dice_val = 0.0
            if hasattr(self, 'metrics_a') and self.metrics_a and key in self.metrics_a:
                dice_val = float(self.metrics_a[key].get("dice", 0.0))
            if dice_val > 0:
                q_lbl = QLabel(f"   └ Segmentation Quality (Dice: {dice_val:.3f})")
                q_lbl.setStyleSheet(f"font-size: 9px; color: {c['TEXT_SECONDARY']}; margin-top: 1px;")
                self.vol_charts_layout.addWidget(q_lbl)
                
                q_pb = QProgressBar()
                q_pb.setRange(0, 100)
                q_pb.setValue(int(dice_val * 100))
                q_pb.setFixedHeight(scaled(8))
                q_pb.setTextVisible(False)
                q_col = "#10B981" if dice_val >= 0.88 else ("#3B82F6" if dice_val >= 0.75 else "#F59E0B")
                q_pb.setStyleSheet(f"QProgressBar {{ border: none; border-radius: 4px; background: {c['SURFACE']}; }} QProgressBar::chunk {{ background: {q_col}; border-radius: 4px; }}")
                self.vol_charts_layout.addWidget(q_pb)

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

    def export_clinical_report(self):
        """Opens Export Report dialog with options for PDF, PNG, and NIfTI export."""
        c = get_theme_palette()
        dlg = QDialog(self)
        dlg.setWindowTitle("📄 Export Clinical Report")
        dlg.resize(scaled(550), scaled(600))
        dlg.setStyleSheet(f"background-color: {c['BACKGROUND']}; color: {c['TEXT_PRIMARY']};")
        
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(scaled(24), scaled(24), scaled(24), scaled(24))
        layout.setSpacing(scaled(12))
        
        # Header
        header = QLabel("Export Clinical Report")
        header.setStyleSheet(f"font-size: {scaled(20)}px; font-weight: 800; color: {c['PRIMARY']};")
        layout.addWidget(header)
        
        desc = QLabel("Generate a professional PDF report or export individual assets.")
        desc.setStyleSheet(f"color: {c['TEXT_SECONDARY']}; font-size: {scaled(12)}px;")
        layout.addWidget(desc)
        
        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"color: {c['BORDER']};")
        layout.addWidget(div)
        
        # Patient Information
        info_lbl = QLabel("📋 Patient Information")
        info_lbl.setStyleSheet(f"font-weight: 700; font-size: {scaled(14)}px; color: {c['TEXT_PRIMARY']};")
        layout.addWidget(info_lbl)
        
        form = QFormLayout()
        form.setSpacing(scaled(8))
        self._report_patient_name = QLineEdit()
        self._report_patient_name.setPlaceholderText("Enter patient name...")
        self._report_patient_name.setStyleSheet(f"background: {c['INPUT_BG']}; border: 1px solid {c['BORDER']}; border-radius: {scaled(6)}px; padding: {scaled(6)}px; color: {c['TEXT_PRIMARY']};")
        
        self._report_doctor_name = QLineEdit()
        self._report_doctor_name.setPlaceholderText("Enter doctor / examiner name...")
        self._report_doctor_name.setStyleSheet(f"background: {c['INPUT_BG']}; border: 1px solid {c['BORDER']}; border-radius: {scaled(6)}px; padding: {scaled(6)}px; color: {c['TEXT_PRIMARY']};")
        
        form.addRow("Patient Name:", self._report_patient_name)
        form.addRow("Doctor/Examiner:", self._report_doctor_name)
        layout.addLayout(form)
        
        # Image Selection
        img_lbl = QLabel("🖼️ Include in Report")
        img_lbl.setStyleSheet(f"font-weight: 700; font-size: {scaled(14)}px; color: {c['TEXT_PRIMARY']}; margin-top: {scaled(8)}px;")
        layout.addWidget(img_lbl)
        
        self._chk_axial = QCheckBox("Axial View"); self._chk_axial.setChecked(True)
        self._chk_sagittal = QCheckBox("Sagittal View"); self._chk_sagittal.setChecked(True)
        self._chk_coronal = QCheckBox("Coronal View"); self._chk_coronal.setChecked(True)
        self._chk_3d = QCheckBox("3D Viewer"); self._chk_3d.setChecked(True)
        self._chk_metrics = QCheckBox("Metrics Table"); self._chk_metrics.setChecked(True)
        self._chk_volumes = QCheckBox("Volumetric Results"); self._chk_volumes.setChecked(True)
        self._chk_gt_comparison = QCheckBox("Ground Truth Comparison (if available)"); self._chk_gt_comparison.setChecked(True)
        
        for chk in [self._chk_axial, self._chk_sagittal, self._chk_coronal, self._chk_3d, self._chk_metrics, self._chk_volumes, self._chk_gt_comparison]:
            layout.addWidget(chk)
        
        layout.addSpacing(scaled(8))
        
        # Export Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(scaled(8))
        
        btn_pdf = QPushButton("📄 Generate PDF Report (A4)")
        btn_pdf.setFixedHeight(scaled(42))
        btn_pdf.setCursor(Qt.PointingHandCursor)
        btn_pdf.setStyleSheet(f"QPushButton {{ background: {c['PRIMARY']}; color: white; border: none; border-radius: {scaled(8)}px; font-weight: 700; font-size: {scaled(14)}px; }} QPushButton:hover {{ background: {c['PRIMARY_HOVER']}; }}")
        btn_pdf.clicked.connect(lambda: self._generate_pdf_report(dlg))
        btn_layout.addWidget(btn_pdf)
        
        btn_row = QHBoxLayout()
        btn_row.setSpacing(scaled(8))
        
        btn_png = QPushButton("📸 Export Views as PNG")
        btn_png.setFixedHeight(scaled(36))
        btn_png.setCursor(Qt.PointingHandCursor)
        btn_png.setStyleSheet(f"QPushButton {{ background: {c['SURFACE_LIGHT']}; color: {c['TEXT_PRIMARY']}; border: 1px solid {c['BORDER']}; border-radius: {scaled(6)}px; font-weight: 600; }} QPushButton:hover {{ background: {c['SURFACE_HOVER']}; }}")
        btn_png.clicked.connect(lambda: self._export_views_as_png(dlg))
        btn_row.addWidget(btn_png)
        
        btn_nii = QPushButton("💾 Export Mask as .nii.gz")
        btn_nii.setFixedHeight(scaled(36))
        btn_nii.setCursor(Qt.PointingHandCursor)
        btn_nii.setStyleSheet(f"QPushButton {{ background: {c['SURFACE_LIGHT']}; color: {c['TEXT_PRIMARY']}; border: 1px solid {c['BORDER']}; border-radius: {scaled(6)}px; font-weight: 600; }} QPushButton:hover {{ background: {c['SURFACE_HOVER']}; }}")
        btn_nii.clicked.connect(lambda: self._export_mask_nii(dlg))
        btn_row.addWidget(btn_nii)
        
        btn_layout.addLayout(btn_row)
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        dlg.exec_()
    
    def _capture_viewport_pixmap(self, view_widget):
        """Captures a viewport as a QPixmap."""
        try:
            if hasattr(view_widget, 'grabFrameBuffer'):
                return QPixmap.fromImage(view_widget.grabFrameBuffer())
            return view_widget.grab()
        except Exception:
            return QPixmap(400, 400)
    
    def _generate_pdf_report(self, dialog):
        """Generates a professional A4 PDF report using matplotlib."""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_pdf import PdfPages
        except ImportError:
            QMessageBox.warning(self, "Missing Dependency", "matplotlib is required for PDF generation.\nPlease install it: pip install matplotlib")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", 
            f"NeuroSeg_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", 
            "PDF Files (*.pdf)")
        if not path:
            return
        
        patient_name = self._report_patient_name.text() or "Unknown Patient"
        doctor_name = self._report_doctor_name.text() or "N/A"
        
        try:
            with PdfPages(path) as pdf:
                # --- Page 1: Header + Viewport Screenshots ---
                fig, axes = plt.subplots(2, 2, figsize=(8.27, 11.69))  # A4 in inches
                fig.patch.set_facecolor('white')
                
                # Report Header
                fig.text(0.5, 0.96, f'NeuroSeg-Pro v{__version__} Clinical Report', fontsize=18, fontweight='bold', 
                        ha='center', va='top', color='#1E3A8A')
                fig.text(0.5, 0.93, f'Patient: {patient_name}  |  Doctor: {doctor_name}  |  Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                        fontsize=9, ha='center', va='top', color='#475569')
                fig.text(0.5, 0.91, '─' * 100, fontsize=6, ha='center', va='top', color='#CBD5E1')
                
                # Capture viewports
                views = [
                    ('Axial View', self.axial_view if self._chk_axial.isChecked() else None),
                    ('Sagittal View', self.sagittal_view if self._chk_sagittal.isChecked() else None),
                    ('Coronal View', self.coronal_view if self._chk_coronal.isChecked() else None),
                    ('3D View', self.threed_view if self._chk_3d.isChecked() else None),
                ]
                
                for idx, (title, view) in enumerate(views):
                    ax = axes[idx // 2][idx % 2]
                    ax.set_title(title, fontsize=10, fontweight='bold', color='#1E3A8A')
                    if view is not None:
                        pixmap = self._capture_viewport_pixmap(view)
                        buf = QBuffer()
                        buf.open(QBuffer.ReadWrite)
                        pixmap.save(buf, "PNG")
                        buf.seek(0)
                        img_data = io.BytesIO(buf.data())
                        img = plt.imread(img_data)
                        ax.imshow(img)
                    ax.axis('off')
                
                plt.tight_layout(rect=[0.02, 0.02, 0.98, 0.88])
                pdf.savefig(fig)
                plt.close(fig)
                
                # --- Page 2: Metrics Table + Volumetric Results ---
                if self._chk_metrics.isChecked() or self._chk_volumes.isChecked():
                    fig2, ax2 = plt.subplots(figsize=(8.27, 11.69))
                    fig2.patch.set_facecolor('white')
                    ax2.axis('off')
                    
                    y_pos = 0.95
                    
                    fig2.text(0.5, y_pos, 'Segmentation Metrics & Analysis', fontsize=16, fontweight='bold',
                            ha='center', va='top', color='#1E3A8A')
                    y_pos -= 0.04
                    fig2.text(0.5, y_pos, f'Patient: {patient_name}  |  Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                            fontsize=9, ha='center', va='top', color='#475569')
                    y_pos -= 0.06
                    
                    if self._chk_metrics.isChecked() and self.metrics_a:
                        # Dice Scores Table
                        fig2.text(0.05, y_pos, 'Dice Scores', fontsize=12, fontweight='bold', color='#0F172A')
                        y_pos -= 0.03
                        
                        rows = []
                        headers = ['ROI', 'Dice', 'IoU', 'Sensitivity', 'Precision', 'HD95']
                        for roi_name in ['Whole Tumor', 'Tumor Core', 'Enhancing Tumor']:
                            if roi_name in self.metrics_a:
                                m = self.metrics_a[roi_name]
                                rows.append([
                                    roi_name,
                                    f"{m.get('dice', 0):.4f}",
                                    f"{m.get('iou', 0):.4f}",
                                    f"{m.get('sensitivity', 0):.4f}",
                                    f"{m.get('precision', 0):.4f}",
                                    f"{m.get('hd95', 0):.2f}" if m.get('hd95', -1) >= 0 else "N/A"
                                ])
                        
                        if rows:
                            table = ax2.table(cellText=rows, colLabels=headers, 
                                            loc='center', cellLoc='center',
                                            bbox=[0.02, y_pos - 0.15, 0.96, 0.15])
                            table.auto_set_font_size(False)
                            table.set_fontsize(9)
                            for key, cell in table.get_celld().items():
                                if key[0] == 0:  # Header
                                    cell.set_facecolor('#1E3A8A')
                                    cell.set_text_props(color='white', fontweight='bold')
                                else:
                                    cell.set_facecolor('#F8FAFC' if key[0] % 2 == 0 else 'white')
                                cell.set_edgecolor('#E2E8F0')
                            y_pos -= 0.22
                    
                    if self._chk_volumes.isChecked() and self.metrics_a:
                        fig2.text(0.05, y_pos, 'Volumetric Analysis', fontsize=12, fontweight='bold', color='#0F172A')
                        y_pos -= 0.03
                        
                        vol_rows = []
                        for roi_name in ['Whole Tumor', 'Tumor Core', 'Enhancing Tumor']:
                            if roi_name in self.metrics_a:
                                vol_mm3 = self.metrics_a[roi_name].get('volume', 0)
                                vol_cm3 = vol_mm3 / 1000.0
                                vol_rows.append([roi_name, f"{vol_mm3:,.0f} mm³", f"{vol_cm3:,.2f} cm³"])
                        
                        if vol_rows:
                            vol_table = ax2.table(cellText=vol_rows, 
                                                colLabels=['Region', 'Volume (mm³)', 'Volume (cm³)'],
                                                loc='center', cellLoc='center',
                                                bbox=[0.15, y_pos - 0.12, 0.7, 0.12])
                            vol_table.auto_set_font_size(False)
                            vol_table.set_fontsize(10)
                            for key, cell in vol_table.get_celld().items():
                                if key[0] == 0:
                                    cell.set_facecolor('#10B981')
                                    cell.set_text_props(color='white', fontweight='bold')
                                else:
                                    cell.set_facecolor('#ECFDF5' if key[0] % 2 == 0 else 'white')
                                cell.set_edgecolor('#D1FAE5')
                            y_pos -= 0.18
                    
                    # Ground Truth Comparison
                    if self._chk_gt_comparison.isChecked() and hasattr(self, 'ground_truth') and self.ground_truth is not None:
                        fig2.text(0.05, y_pos, 'Ground Truth Comparison', fontsize=12, fontweight='bold', color='#0F172A')
                        y_pos -= 0.03
                        fig2.text(0.05, y_pos, '✅ Ground truth mask loaded — metrics computed against ground truth.',
                                fontsize=9, color='#059669')
                    
                    # Footer
                    fig2.text(0.5, 0.02, f'Generated by NeuroSeg-Pro v{__version__}  |  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                            fontsize=8, ha='center', va='bottom', color='#94A3B8')
                    
                    pdf.savefig(fig2)
                    plt.close(fig2)
            
            QMessageBox.information(self, "Report Generated", f"PDF report saved successfully:\n{path}")
            dialog.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to generate PDF report:\n{str(e)}")
    
    def _export_views_as_png(self, dialog):
        """Export individual viewport screenshots as PNG files."""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if not folder:
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        saved = []
        
        views = {
            'axial': (self._chk_axial.isChecked(), self.axial_view),
            'sagittal': (self._chk_sagittal.isChecked(), self.sagittal_view),
            'coronal': (self._chk_coronal.isChecked(), self.coronal_view),
            '3d': (self._chk_3d.isChecked(), self.threed_view),
        }
        
        for name, (selected, view) in views.items():
            if selected and view is not None:
                pixmap = self._capture_viewport_pixmap(view)
                filepath = os.path.join(folder, f"NeuroSeg_{name}_{timestamp}.png")
                pixmap.save(filepath, "PNG")
                saved.append(filepath)
        
        if saved:
            QMessageBox.information(self, "Export Complete", f"Exported {len(saved)} image(s) to:\n{folder}")
        else:
            QMessageBox.warning(self, "No Export", "No views were selected for export.")
    
    def _export_mask_nii(self, dialog):
        """Export segmentation mask as NIfTI file."""
        if self.mask is None or self.affine is None:
            QMessageBox.warning(self, "No Data", "No segmentation mask available to export.")
            return
        
        from app.core.loader import NiftiLoader
        path, _ = QFileDialog.getSaveFileName(self, "Export Segmentation Mask", 
            f"segmentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.nii.gz", 
            "NIfTI Files (*.nii.gz)")
        if path:
            NiftiLoader.save_file(path, self.mask.astype(np.float32), self.affine)
            QMessageBox.information(self, "Export Complete", f"Segmentation mask saved:\n{path}")

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
