from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QComboBox, QSpinBox, QCheckBox, QPushButton, QMessageBox,
                                 QTabWidget, QListWidget, QFileDialog, QInputDialog, QScrollArea, QFrame, QSlider)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtSvg import QSvgWidget
import os
import shutil
from app.ui.settings import Settings
from app.ui.theme import get_theme_palette, scaled

class ModelCard(QFrame):
    def __init__(self, model_data, is_active, manager):
        super().__init__()
        self.model_data = model_data
        self.manager = manager
        c = get_theme_palette()
        
        bg_color = c['PRIMARY'] + "22" if is_active else c['SURFACE']
        border = f"2px solid {c['PRIMARY']}" if is_active else f"1px solid {c['BORDER']}"
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: {border};
                border-radius: 8px;
            }}
            QLabel {{ border: none; background: transparent; color: {c['TEXT_PRIMARY']}; }}
            QPushButton {{ border: 1px solid {c['BORDER']}; background: {c['SURFACE_LIGHT']}; color: {c['TEXT_PRIMARY']}; border-radius: 4px; padding: 6px 14px; font-weight: bold; font-size: 12px; }}
            QPushButton:hover {{ background: {c['SURFACE_HOVER']}; }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(scaled(16), scaled(16), scaled(16), scaled(16))
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(scaled(4))
        
        name_lbl = QLabel(model_data["name"])
        name_lbl.setStyleSheet(f"font-weight: bold; font-size: 15px; color: {c['TEXT_PRIMARY']};")
        
        path_name = os.path.basename(model_data.get("path", ""))
        path_lbl = QLabel(path_name)
        path_lbl.setStyleSheet(f"color: {c['TEXT_MUTED']}; font-size: 12px;")
        
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(path_lbl)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        if is_active:
            def_lbl = QLabel("★ Default Model")
            def_lbl.setStyleSheet("color: #0284C7; font-weight: bold; font-size: 13px; margin-right: 15px;")
            layout.addWidget(def_lbl)
        
        if not is_active:
            btn_def = QPushButton("Set Default")
            btn_def.setCursor(Qt.PointingHandCursor)
            btn_def.setStyleSheet("QPushButton { background: #3B82F6; color: white; border: none; border-radius: 4px; padding: 6px 14px; font-weight: bold; } QPushButton:hover { background: #2563EB; }")
            btn_def.clicked.connect(lambda: self.manager.set_default(model_data["id"]))
            layout.addWidget(btn_def)
            
        btn_rename = QPushButton("Rename")
        btn_rename.setCursor(Qt.PointingHandCursor)
        btn_rename.clicked.connect(lambda: self.manager.rename_model_ui(model_data))
        layout.addWidget(btn_rename)
            
        btn_del = QPushButton("Delete")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("QPushButton { background: #FEE2E2; color: #DC2626; border: 1px solid #FECACA; border-radius: 4px; padding: 6px 14px; font-weight: bold; } QPushButton:hover { background: #FECACA; }")
        btn_del.clicked.connect(lambda: self.manager.delete_model(model_data))
        layout.addWidget(btn_del)

class ModelManagerWidget(QWidget):
    models_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(scaled(16))
        
        header = QLabel("Manage AI Models")
        header.setObjectName("SubHeader")
        self.layout.addWidget(header)
        
        # Scroll Area for Cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(scaled(300))
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, scaled(10), 0)
        self.container_layout.setSpacing(scaled(10))
        self.container_layout.setAlignment(Qt.AlignTop)
        
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)
        
        self.refresh_list()
        
        # Checkbox
        self.chk_ask = QCheckBox("Always ask for model selection before segmentation")
        self.chk_ask.setChecked(self.settings.get("ask_model_on_run"))
        self.chk_ask.toggled.connect(lambda v: self.settings.set("ask_model_on_run", v))
        self.layout.addWidget(self.chk_ask)

        # Import & Open Folder Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(scaled(12))
        c = get_theme_palette()
        self.btn_import = QPushButton("➕ Import New Model (.pth)")
        self.btn_import.setFixedHeight(scaled(38))
        self.btn_import.setCursor(Qt.PointingHandCursor)
        self.btn_import.setStyleSheet(f"QPushButton {{ background: {c['PRIMARY']}; color: white; border: none; border-radius: 6px; padding: 8px 18px; font-weight: bold; font-size: 13px; }} QPushButton:hover {{ background: {c['PRIMARY_HOVER']}; }}")
        self.btn_import.clicked.connect(self.import_model)
        
        self.btn_open_folder = QPushButton("📂 Open Models Folder")
        self.btn_open_folder.setFixedHeight(scaled(38))
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
        self.btn_open_folder.setStyleSheet(f"QPushButton {{ background: {c['SURFACE_LIGHT']}; color: {c['TEXT_PRIMARY']}; border: 1px solid {c['BORDER']}; border-radius: 6px; padding: 8px 18px; font-weight: bold; font-size: 13px; }} QPushButton:hover {{ background: {c['SURFACE_HOVER']}; }}")
        self.btn_open_folder.clicked.connect(self.open_models_dir)
        
        btn_layout.addWidget(self.btn_import)
        btn_layout.addWidget(self.btn_open_folder)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)
        
    def open_models_dir(self):
        from app.ui.settings import APP_DATA_DIR
        app_models_dir = os.path.join(APP_DATA_DIR, "models")
        os.makedirs(app_models_dir, exist_ok=True)
        
        # Ensure path is formatted specifically for Windows Explorer
        clean_path = os.path.normpath(app_models_dir)
        
        if sys.platform == 'win32':
            try:
                os.startfile(clean_path)
            except Exception as e:
                # Ultimate fallback to force Windows Explorer
                import subprocess
                subprocess.Popen(['explorer', clean_path])
        
    def refresh_list(self):
        # Clear existing cards
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        models = self.settings.get_models()
        active_id = self.settings.get("active_model_id")
        
        if not models:
            lbl = QLabel("No models found. Please import a PyTorch (.pth) model.")
            lbl.setStyleSheet("color: #a0aec0; font-style: italic; font-size: 14px; padding: 20px;")
            lbl.setAlignment(Qt.AlignCenter)
            self.container_layout.addWidget(lbl)
            return

        for m in models:
            is_active = (m.get('id') == active_id)
            card = ModelCard(m, is_active, self)
            self.container_layout.addWidget(card)

    def set_default(self, model_id):
        self.settings.set_active_model(model_id)
        self.refresh_list()
        self.models_changed.emit()
            
    def import_model(self):
        from app.ui.settings import APP_DATA_DIR
        app_models_dir = os.path.join(APP_DATA_DIR, "models")
        os.makedirs(app_models_dir, exist_ok=True)
        
        path, _ = QFileDialog.getOpenFileName(self.window(), "Import Model (.pth)", os.path.expanduser("~"), "PyTorch Model (*.pth *.pt *.onnx)")
        if path:
            name, ok = QInputDialog.getText(self, "Model Name", "Enter a display name for this model:")
            if ok and name:
                filename = os.path.basename(path)
                dest = os.path.join(app_models_dir, filename)
                try:
                    if not os.path.exists(dest) or not os.path.samefile(path, dest):
                        shutil.copy(path, dest)
                    self.settings.add_model(name, dest)
                    self.refresh_list()
                    self.models_changed.emit()
                except Exception as e:
                     QMessageBox.critical(self, "Error", f"Failed to import model: {e}")

    def rename_model_ui(self, model_data):
        new_name, ok = QInputDialog.getText(self, "Rename Model", "Enter new display name:", text=model_data["name"])
        if ok and new_name and new_name != model_data["name"]:
            self.settings.rename_model(model_data["id"], new_name)
            self.refresh_list()
            self.models_changed.emit()

    def delete_model(self, model_data):
        confirm = QMessageBox.question(self, "Confirm Delete", 
                                       f"Are you sure you want to permanently delete '{model_data['name']}' and remove its physical model file from the folder?",
                                       QMessageBox.Yes | QMessageBox.No)
        
        if confirm == QMessageBox.Yes:
            if self.settings.remove_model(model_data['id'], delete_disk_file=True):
                self.refresh_list()
                self.models_changed.emit()

class SettingsWidget(QWidget):
    settings_saved = pyqtSignal()
    models_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(scaled(30), scaled(30), scaled(30), scaled(30))
        self.layout.setSpacing(scaled(15))
        
        # Header
        header = QLabel("Configuration")
        header.setObjectName("Header")
        self.layout.addWidget(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        
        # Tab 1: General Settings
        self.general_tab = QWidget()
        self.setup_general_tab()
        self.tabs.addTab(self.general_tab, "General")
        
        # Tab 2: AI Models
        self.model_tab = ModelManagerWidget()
        self.model_tab.models_changed.connect(self.models_changed.emit)
        self.tabs.addTab(self.model_tab, "AI Models")
        
        # Save Button
        self.layout.addStretch()
        self.save_btn = QPushButton("💾 Save All Configuration Settings")
        self.save_btn.setFixedHeight(scaled(42))
        self.save_btn.setCursor(Qt.PointingHandCursor)
        c = get_theme_palette()
        self.save_btn.setStyleSheet(f"QPushButton {{ background: {c['PRIMARY']}; color: white; border: none; border-radius: 8px; font-weight: bold; font-size: 15px; }} QPushButton:hover {{ background: {c['PRIMARY_HOVER']}; }}")
        self.save_btn.clicked.connect(self.save_settings)
        self.layout.addWidget(self.save_btn)

    def setup_general_tab(self):
        c = get_theme_palette()
        main_layout = QVBoxLayout(self.general_tab)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setSpacing(scaled(18))
        layout.setContentsMargins(scaled(16), scaled(16), scaled(16), scaled(16))
        
        # --- CARD 1: THEME SELECTION ---
        theme_card = QFrame()
        theme_card.setStyleSheet(f"background: {c['SURFACE']}; border: 1px solid {c['BORDER']}; border-radius: {scaled(12)}px; padding: {scaled(14)}px;")
        tc_layout = QVBoxLayout(theme_card)
        tc_layout.setContentsMargins(scaled(8), scaled(8), scaled(8), scaled(8))
        tc_layout.setSpacing(scaled(12))
        
        t_header = QLabel("🎨 Theme & Interface Mode")
        t_header.setStyleSheet(f"font-size: {scaled(16)}px; font-weight: 800; color: {c['PRIMARY']}; border: none; background: transparent;")
        tc_layout.addWidget(t_header)
        
        cards_row = QHBoxLayout()
        cards_row.setSpacing(scaled(14))
        
        self.selected_theme = self.settings.get("theme") or "Light"
        
        # Dark Theme Card
        self.dark_card = QFrame()
        self.dark_card.setCursor(Qt.PointingHandCursor)
        dc_layout = QVBoxLayout(self.dark_card)
        dc_layout.setContentsMargins(scaled(12), scaled(12), scaled(12), scaled(12))
        
        if os.path.exists("assets/icons/Dark-moon-Theme.svg"):
            d_svg = QSvgWidget("assets/icons/Dark-moon-Theme.svg")
            d_svg.setFixedSize(scaled(36), scaled(36))
            dc_layout.addWidget(d_svg, 0, Qt.AlignCenter)
            
        d_title = QLabel("🌙 Dark Theme")
        d_title.setStyleSheet("font-size: 14px; font-weight: bold; border: none; background: transparent;")
        d_desc = QLabel("Deep Space Medical palette optimized for radiology evaluation.")
        d_desc.setWordWrap(True)
        d_desc.setStyleSheet(f"font-size: 11px; color: {c['TEXT_SECONDARY']}; border: none; background: transparent;")
        dc_layout.addWidget(d_title, 0, Qt.AlignCenter)
        dc_layout.addWidget(d_desc, 0, Qt.AlignCenter)
        cards_row.addWidget(self.dark_card)
        
        # Light Theme Card
        self.light_card = QFrame()
        self.light_card.setCursor(Qt.PointingHandCursor)
        lc_layout = QVBoxLayout(self.light_card)
        lc_layout.setContentsMargins(scaled(12), scaled(12), scaled(12), scaled(12))
        
        if os.path.exists("assets/icons/Light-Sun-Theme.svg"):
            l_svg = QSvgWidget("assets/icons/Light-Sun-Theme.svg")
            l_svg.setFixedSize(scaled(36), scaled(36))
            lc_layout.addWidget(l_svg, 0, Qt.AlignCenter)
            
        l_title = QLabel("☀️ Light Theme")
        l_title.setStyleSheet("font-size: 14px; font-weight: bold; border: none; background: transparent;")
        l_desc = QLabel("Warm Clinical palette with high contrast for bright rooms.")
        l_desc.setWordWrap(True)
        l_desc.setStyleSheet(f"font-size: 11px; color: {c['TEXT_SECONDARY']}; border: none; background: transparent;")
        lc_layout.addWidget(l_title, 0, Qt.AlignCenter)
        lc_layout.addWidget(l_desc, 0, Qt.AlignCenter)
        cards_row.addWidget(self.light_card)
        
        tc_layout.addLayout(cards_row)
        layout.addWidget(theme_card)
        
        def update_theme_cards():
            d_border = f"2px solid {c['PRIMARY']}" if self.selected_theme == "Dark" else f"1px solid {c['BORDER']}"
            d_bg = c['PRIMARY'] + "1A" if self.selected_theme == "Dark" else c['SURFACE_LIGHT']
            self.dark_card.setStyleSheet(f"QFrame {{ background: {d_bg}; border: {d_border}; border-radius: {scaled(10)}px; }}")
            
            l_border = f"2px solid {c['PRIMARY']}" if self.selected_theme == "Light" else f"1px solid {c['BORDER']}"
            l_bg = c['PRIMARY'] + "1A" if self.selected_theme == "Light" else c['SURFACE_LIGHT']
            self.light_card.setStyleSheet(f"QFrame {{ background: {l_bg}; border: {l_border}; border-radius: {scaled(10)}px; }}")
            
        self.dark_card.mousePressEvent = lambda e: (setattr(self, 'selected_theme', 'Dark'), update_theme_cards())
        self.light_card.mousePressEvent = lambda e: (setattr(self, 'selected_theme', 'Light'), update_theme_cards())
        update_theme_cards()
        
        # --- CARD 2: TYPOGRAPHY & FONT ---
        font_card = QFrame()
        font_card.setStyleSheet(f"background: {c['SURFACE']}; border: 1px solid {c['BORDER']}; border-radius: {scaled(12)}px; padding: {scaled(14)}px;")
        fc_layout = QVBoxLayout(font_card)
        fc_layout.setContentsMargins(scaled(8), scaled(8), scaled(8), scaled(8))
        fc_layout.setSpacing(scaled(12))
        
        f_header = QLabel("🔤 Typography & Font Customization")
        f_header.setStyleSheet(f"font-size: {scaled(16)}px; font-weight: 800; color: {c['PRIMARY']}; border: none; background: transparent;")
        fc_layout.addWidget(f_header)
        
        f_row = QHBoxLayout()
        f_row.addWidget(QLabel("Font Family:", styleSheet="border: none; background: transparent; font-weight: bold;"))
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Segoe UI", "Inter", "Roboto", "Arial", "Tahoma"])
        curr_font = self.settings.get("font_family") or "Segoe UI"
        self.font_combo.setCurrentText(curr_font)
        f_row.addWidget(self.font_combo)
        f_row.addSpacing(scaled(16))
        
        f_row.addWidget(QLabel("Base Font Size:", styleSheet="border: none; background: transparent; font-weight: bold;"))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 24)
        self.font_spin.setValue(self.settings.get("font_size") or 14)
        self.font_slider = QSlider(Qt.Horizontal)
        self.font_slider.setRange(8, 24)
        self.font_slider.setValue(self.font_spin.value())
        self.font_spin.valueChanged.connect(self.font_slider.setValue)
        self.font_slider.valueChanged.connect(self.font_spin.setValue)
        f_row.addWidget(self.font_slider)
        f_row.addWidget(self.font_spin)
        fc_layout.addLayout(f_row)
        
        z_row = QHBoxLayout()
        z_row.addWidget(QLabel("Interface Zoom / Scale:", styleSheet="border: none; background: transparent; font-weight: bold;"))
        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["75% (Compact)", "85% (Small)", "100% (Default)", "115% (Large)", "125% (Extra Large)"])
        curr_zoom = self.settings.get("ui_zoom")
        if curr_zoom is None:
            curr_zoom = 1.0
        zoom_map_rev = {0.75: "75% (Compact)", 0.85: "85% (Small)", 1.0: "100% (Default)", 1.15: "115% (Large)", 1.25: "125% (Extra Large)"}
        self.zoom_combo.setCurrentText(zoom_map_rev.get(float(curr_zoom), "100% (Default)"))
        z_row.addWidget(self.zoom_combo)
        z_row.addStretch()
        fc_layout.addLayout(z_row)
        
        # Live Preview Box
        self.preview_lbl = QLabel("Live Preview: Axial Plane [L-R / A-P]  |  Slice: 78 / 155  |  Dice Quality: 0.924")
        self.preview_lbl.setAlignment(Qt.AlignCenter)
        self.preview_lbl.setStyleSheet(f"background: {c['SURFACE_LIGHT']}; border: 1px dashed {c['PRIMARY']}; border-radius: {scaled(6)}px; padding: {scaled(10)}px; color: {c['TEXT_PRIMARY']};")
        fc_layout.addWidget(self.preview_lbl)
        
        def update_preview(*args):
            f_fam = self.font_combo.currentText()
            f_size = self.font_spin.value()
            self.preview_lbl.setFont(QFont(f_fam, f_size))
            
        self.font_combo.currentIndexChanged.connect(update_preview)
        self.font_spin.valueChanged.connect(update_preview)
        update_preview()
        
        layout.addWidget(font_card)
        
        # --- CARD 3: 3D RENDERING QUALITY ---
        viz_card = QFrame()
        viz_card.setStyleSheet(f"background: {c['SURFACE']}; border: 1px solid {c['BORDER']}; border-radius: {scaled(12)}px; padding: {scaled(14)}px;")
        vc_layout = QVBoxLayout(viz_card)
        vc_layout.setContentsMargins(scaled(8), scaled(8), scaled(8), scaled(8))
        vc_layout.setSpacing(scaled(12))
        
        v_header = QLabel("🧊 3D Volumetric Rendering Quality")
        v_header.setStyleSheet(f"font-size: {scaled(16)}px; font-weight: 800; color: {c['PRIMARY']}; border: none; background: transparent;")
        vc_layout.addWidget(v_header)
        
        v_row = QHBoxLayout()
        v_row.addWidget(QLabel("Mesh Quality:", styleSheet="border: none; background: transparent; font-weight: bold;"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Low", "Medium", "High"])
        self.quality_combo.setCurrentText(self.settings.get("visual_quality") or "High")
        v_row.addWidget(self.quality_combo)
        v_row.addStretch()
        vc_layout.addLayout(v_row)
        
        layout.addWidget(viz_card)
        layout.addStretch()
        
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def save_settings(self):
        self.settings.set("font_size", self.font_spin.value())
        self.settings.set("font_family", self.font_combo.currentText())
        self.settings.set("theme", self.selected_theme)
        self.settings.set("visual_quality", self.quality_combo.currentText())
        zoom_map = {"75% (Compact)": 0.75, "85% (Small)": 0.85, "100% (Default)": 1.0, "115% (Large)": 1.15, "125% (Extra Large)": 1.25}
        self.settings.set("ui_zoom", zoom_map.get(self.zoom_combo.currentText(), 1.0))
        
        self.settings_saved.emit()
        QMessageBox.information(self, "Settings Saved", "Settings saved successfully.")
