from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QComboBox, QSpinBox, QCheckBox, QPushButton, QMessageBox,
                                 QTabWidget, QListWidget, QFileDialog, QInputDialog, QScrollArea, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
import os
import shutil
from app.ui.settings import Settings
from app.ui.theme import get_theme_palette, scaled

class ModelCard(QFrame):
    def __init__(self, model_data, is_active, manager):
        super().__init__()
        self.model_data = model_data
        self.manager = manager
        
        bg_color = "rgba(79, 209, 197, 0.15)" if is_active else "rgba(255, 255, 255, 0.05)"
        border = "1px solid #4fd1c5" if is_active else "1px solid rgba(255, 255, 255, 0.1)"
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: {border};
                border-radius: 8px;
            }}
            QFrame:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
            QLabel {{ border: none; background: transparent; }}
            QPushButton {{ border: none; background: rgba(255,255,255,0.1); border-radius: 4px; padding: 6px 14px; font-weight: bold; }}
            QPushButton:hover {{ background: rgba(255,255,255,0.2); }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(scaled(16), scaled(16), scaled(16), scaled(16))
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(scaled(4))
        
        name_lbl = QLabel(model_data["name"])
        name_lbl.setStyleSheet("font-weight: bold; font-size: 15px; color: white;")
        
        path_name = os.path.basename(model_data.get("path", ""))
        path_lbl = QLabel(path_name)
        path_lbl.setStyleSheet("color: #a0aec0; font-size: 12px;")
        
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(path_lbl)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        if is_active:
            def_lbl = QLabel("★ Default Model")
            def_lbl.setStyleSheet("color: #4fd1c5; font-weight: bold; font-size: 13px; margin-right: 15px;")
            layout.addWidget(def_lbl)
        
        if not is_active:
            btn_def = QPushButton("Set Default")
            btn_def.setCursor(Qt.PointingHandCursor)
            btn_def.clicked.connect(lambda: self.manager.set_default(model_data["id"]))
            layout.addWidget(btn_def)
            
        btn_rename = QPushButton("Rename")
        btn_rename.setCursor(Qt.PointingHandCursor)
        btn_rename.clicked.connect(lambda: self.manager.rename_model_ui(model_data))
        layout.addWidget(btn_rename)
            
        btn_del = QPushButton("Delete")
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("QPushButton { background: rgba(229, 62, 62, 0.2); color: #fc8181; } QPushButton:hover { background: rgba(229, 62, 62, 0.4); }")
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

        # Import Button
        btn_layout = QHBoxLayout()
        self.btn_import = QPushButton("Import New Model (.pth)")
        self.btn_import.setObjectName("AccentButton")
        self.btn_import.setFixedHeight(scaled(36))
        self.btn_import.setCursor(Qt.PointingHandCursor)
        self.btn_import.clicked.connect(self.import_model)
        
        self.btn_open_folder = QPushButton("📂 Open Models Folder")
        self.btn_open_folder.setFixedHeight(scaled(36))
        self.btn_open_folder.setCursor(Qt.PointingHandCursor)
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
        
        path, _ = QFileDialog.getOpenFileName(self, "Import Model", "", "PyTorch Model (*.pth)")
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
        self.save_btn = QPushButton("Save All Settings")
        self.save_btn.setObjectName("AccentButton")
        self.save_btn.setFixedHeight(scaled(42))
        self.save_btn.clicked.connect(self.save_settings)
        self.layout.addWidget(self.save_btn)

    def setup_general_tab(self):
        layout = QVBoxLayout(self.general_tab)
        layout.setSpacing(scaled(16))
        layout.setContentsMargins(scaled(15), scaled(15), scaled(15), scaled(15))
        
        # Appearance Section
        layout.addWidget(QLabel("Appearance", objectName="SubHeader"))
        
        # Font Size
        fs_lbl = QLabel("Font Size (requires restart)")
        layout.addWidget(fs_lbl)
        self.font_spin = QSpinBox()
        self.font_spin.setRange(6, 45)
        self.font_spin.setValue(self.settings.get("font_size"))
        self.font_spin.setFixedHeight(scaled(32))
        layout.addWidget(self.font_spin)
        
        # Theme
        layout.addWidget(QLabel("Theme"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentText(self.settings.get("theme"))
        layout.addWidget(self.theme_combo)
        
        layout.addSpacing(scaled(20))
        
        # Visualization Section
        layout.addWidget(QLabel("Visualization", objectName="SubHeader"))
        
        # 3D Quality
        layout.addWidget(QLabel("3D Quality"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Low", "Medium", "High"])
        self.quality_combo.setCurrentText(self.settings.get("visual_quality"))
        layout.addWidget(self.quality_combo)
        
        layout.addStretch()

    def save_settings(self):
        self.settings.set("font_size", self.font_spin.value())
        self.settings.set("theme", self.theme_combo.currentText())
        self.settings.set("visual_quality", self.quality_combo.currentText())
        
        self.settings_saved.emit()
        QMessageBox.information(self, "Settings Saved", "Settings saved successfully.")
