from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QComboBox, QSpinBox, QCheckBox, QPushButton, QMessageBox,
                                 QTabWidget, QListWidget, QFileDialog, QInputDialog)
import os
import shutil
from app.ui.settings import Settings
from app.ui.theme import get_theme_palette, scaled

from PyQt5.QtCore import pyqtSignal

class ModelManagerWidget(QWidget):
    models_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(scaled(12))
        
        c = get_theme_palette()
        
        header = QLabel("Manage AI Models")
        header.setObjectName("SubHeader")
        self.layout.addWidget(header)
        
        # Model List
        self.model_list = QListWidget()
        self.model_list.setMinimumHeight(scaled(150))
        self.layout.addWidget(self.model_list)
        self.refresh_list()
        
        # Checkbox
        self.chk_ask = QCheckBox("Always ask for model selection before segmentation")
        self.chk_ask.setChecked(self.settings.get("ask_model_on_run"))
        self.chk_ask.toggled.connect(lambda v: self.settings.set("ask_model_on_run", v))
        self.layout.addWidget(self.chk_ask)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_import = QPushButton("Import Model (.pth)")
        self.btn_set_default = QPushButton("Set as Default")
        self.btn_delete = QPushButton("Delete Selected")
        
        self.btn_import.clicked.connect(self.import_model)
        self.btn_set_default.clicked.connect(self.set_default)
        self.btn_delete.clicked.connect(self.delete_model)
        
        btn_layout.addWidget(self.btn_import)
        btn_layout.addWidget(self.btn_set_default)
        btn_layout.addWidget(self.btn_delete)
        self.layout.addLayout(btn_layout)
        
    def refresh_list(self):
        self.model_list.clear()
        models = self.settings.get_models()
        active_id = self.settings.get("active_model_id")
        
        for m in models:
            display = f"{m['name']}"
            if m['id'] == active_id:
                display += " (Default)"
            self.model_list.addItem(display)

    def set_default(self):
        row = self.model_list.currentRow()
        if row < 0: return
        
        models = self.settings.get_models()
        model_id = models[row]['id']
        self.settings.set_active_model(model_id)
        self.refresh_list()
        self.models_changed.emit()
        QMessageBox.information(self, "Success", f"'{models[row]['name']}' is now the default model.")
            
    def import_model(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Model", "", "PyTorch Model (*.pth)")
        if path:
            name, ok = QInputDialog.getText(self, "Model Name", "Enter a name for this model:")
            if ok and name:
                os.makedirs("models", exist_ok=True)
                filename = os.path.basename(path)
                dest = os.path.join("models", filename)
                try:
                    shutil.copy(path, dest)
                    self.settings.add_model(name, dest)
                    self.refresh_list()
                    self.models_changed.emit()
                    QMessageBox.information(self, "Success", f"Model '{name}' imported successfully.")
                except Exception as e:
                     QMessageBox.critical(self, "Error", f"Failed to import model: {e}")

    def delete_model(self):
        row = self.model_list.currentRow()
        if row < 0: return
        
        models = self.settings.get_models()
        model_to_delete = models[row]
        
        confirm = QMessageBox.question(self, "Confirm Delete", 
                                       f"Are you sure you want to delete '{model_to_delete['name']}'?",
                                       QMessageBox.Yes | QMessageBox.No)
        
        if confirm == QMessageBox.Yes:
            if self.settings.remove_model(model_to_delete['id']):
                self.refresh_list()
                self.models_changed.emit()
                QMessageBox.information(self, "Deleted", "Model removed from registry.")

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
