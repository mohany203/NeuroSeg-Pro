from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor, QFont
from app.ui.settings import Settings

# --- Premium Palette (Tailwind-inspired) ---

# Dark Mode: "Deep Space Medical"
DARK_THEME = {
    "PRIMARY": "#3B82F6",       # Blue-500
    "PRIMARY_HOVER": "#2563EB", # Blue-600
    "ACCENT": "#8B5CF6",        # Violet-500
    "BACKGROUND": "#09090B",    # Zinc-950
    "SURFACE": "#18181B",       # Zinc-900
    "SURFACE_LIGHT": "#27272A", # Zinc-800
    "TEXT_PRIMARY": "#FAFAFA",  # Zinc-50
    "TEXT_SECONDARY": "#A1A1AA",# Zinc-400
    "BORDER": "#27272A",        # Zinc-800
    "SUCCESS": "#10B981",       # Emerald-500
    "WARNING": "#F59E0B",       # Amber-500
    "ERROR": "#EF4444"          # Red-500
}

# Light Mode: "Clean Clinical"
LIGHT_THEME = {
    "PRIMARY": "#2563EB",       # Blue-600
    "PRIMARY_HOVER": "#1D4ED8", # Blue-700
    "ACCENT": "#7C3AED",        # Violet-600
    "BACKGROUND": "#F8FAFC",    # Slate-50
    "SURFACE": "#FFFFFF",       # White
    "SURFACE_LIGHT": "#F1F5F9", # Slate-100
    "TEXT_PRIMARY": "#0F172A",  # Slate-900
    "TEXT_SECONDARY": "#64748B",# Slate-500
    "BORDER": "#E2E8F0",        # Slate-200
    "SUCCESS": "#059669",       # Emerald-600
    "WARNING": "#D97706",       # Amber-600
    "ERROR": "#DC2626"          # Red-600
}

def get_theme_palette():
    """Returns the current theme palette dictionary."""
    settings = Settings()
    start_theme = settings.get("theme")
    return DARK_THEME if start_theme == "Dark" else LIGHT_THEME

def apply_theme(app: QApplication):
    """Applies a modern, rich theme (Light/Dark) to the application."""
    settings = Settings()
    base_font_size = settings.get("font_size") # e.g. 14
    start_theme = settings.get("theme")
    
    # Select Palette
    c = DARK_THEME if start_theme == "Dark" else LIGHT_THEME
    
    app.setStyle("Fusion")
    
    # Set Global Font
    font = QFont("Segoe UI")
    font.setPixelSize(base_font_size)
    app.setFont(font)
    
    # Standard Palette (for non-styled widgets)
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(c["BACKGROUND"]))
    palette.setColor(QPalette.WindowText, QColor(c["TEXT_PRIMARY"]))
    palette.setColor(QPalette.Base, QColor(c["BACKGROUND"]))
    palette.setColor(QPalette.AlternateBase, QColor(c["SURFACE"]))
    palette.setColor(QPalette.ToolTipBase, QColor(c["SURFACE_LIGHT"]))
    palette.setColor(QPalette.ToolTipText, QColor(c["TEXT_PRIMARY"]))
    palette.setColor(QPalette.Text, QColor(c["TEXT_PRIMARY"]))
    palette.setColor(QPalette.Button, QColor(c["SURFACE"]))
    palette.setColor(QPalette.ButtonText, QColor(c["TEXT_PRIMARY"]))
    palette.setColor(QPalette.BrightText, QColor(c["ACCENT"]))
    palette.setColor(QPalette.Link, QColor(c["PRIMARY"]))
    palette.setColor(QPalette.Highlight, QColor(c["PRIMARY"]))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    
    app.setPalette(palette)
    
    # --- SCALING FACTORS & QSS ---
    
    app.setStyleSheet(f"""
        QMainWindow {{
            background-color: {c["BACKGROUND"]};
        }}
        QWidget {{
            font-family: 'Segoe UI', 'Inter', sans-serif;
            font-size: {base_font_size}px;
            color: {c["TEXT_PRIMARY"]};
        }}
        
        /* ToolTips */
        QToolTip {{
            background-color: {c["SURFACE_LIGHT"]};
            color: {c["TEXT_PRIMARY"]};
            border: 1px solid {c["BORDER"]};
            border-radius: 4px;
            padding: 5px;
        }}

        /* Frames & Cards */
        QFrame#Card {{
            background-color: {c["SURFACE"]};
            border-radius: 16px;
            border: 1px solid {c["BORDER"]};
        }}
        QFrame#Card:hover {{
            border: 1px solid {c["PRIMARY"]}80; /* Semi-transparent border on hover */
        }}
        
        QFrame#Sidebar {{
            background-color: {c["SURFACE"]};
            border-right: 1px solid {c["BORDER"]};
        }}
        
        /* 3D/2D Viewports - Add a subtle glow/border */
        QFrame#ViewportFrame {{
            background-color: #000;
            border: 1px solid {c["BORDER"]};
            border-radius: 8px;
        }}
        
        /* GroupBox - Modern & Minimal */
        QGroupBox {{
            background-color: {c["SURFACE"]};
            border: 1px solid {c["BORDER"]};
            border-radius: 12px;
            margin-top: 24px;
            padding-top: 10px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            left: 10px;
            color: {c["ACCENT"]};
            font-weight: bold;
            font-size: {base_font_size + 1}px;
        }}
        
        /* Buttons */
        QPushButton {{
            background-color: {c["SURFACE_LIGHT"]};
            color: {c["TEXT_PRIMARY"]};
            border: 1px solid {c["BORDER"]};
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {c["BORDER"]};
            border: 1px solid {c["PRIMARY"]};
        }}
        QPushButton:pressed {{
            background-color: {c["PRIMARY"]}30;
        }}
        QPushButton:checked {{
            background-color: {c["PRIMARY"]};
            color: white;
            border: 1px solid {c["PRIMARY"]};
        }}
        
        /* Primary/Action Button */
        QPushButton#AccentButton {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c["PRIMARY"]}, stop:1 {c["ACCENT"]});
            color: white;
            border: none;
            padding: 10px 20px;
        }}
        QPushButton#AccentButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c["PRIMARY_HOVER"]}, stop:1 {c["ACCENT"]});
        }}
        
        /* Navigation Buttons (Sidebar) */
        QPushButton#NavButton {{
            background-color: transparent;
            border: none;
            text-align: left;
            padding-left: 20px;
            font-size: {base_font_size + 1}px;
            color: {c["TEXT_SECONDARY"]};
            border-radius: 8px;
        }}
        QPushButton#NavButton:hover {{
            background-color: {c["SURFACE_LIGHT"]};
            color: {c["TEXT_PRIMARY"]};
        }}
        QPushButton#NavButton:checked {{
            background-color: {c["PRIMARY"]}15; /* 15% opacity */
            color: {c["PRIMARY"]};
            border-right: 3px solid {c["PRIMARY"]};
            font-weight: bold;
        }}
        
        /* Info Button (Small ?) */
        QPushButton#InfoButton {{
            background-color: transparent;
            color: {c["TEXT_SECONDARY"]};
            border: 1px solid {c["BORDER"]};
            border-radius: 10px; /* Circular */
            font-weight: bold;
            padding: 0px;
        }}
        QPushButton#InfoButton:hover {{
            color: {c["PRIMARY"]};
            border: 1px solid {c["PRIMARY"]};
            background-color: {c["PRIMARY"]}20;
        }}

        /* Combo Boxes */
        QComboBox {{
            background-color: {c["BACKGROUND"]};
            color: {c["TEXT_PRIMARY"]};
            border: 1px solid {c["BORDER"]};
            border-radius: 8px;
            padding: 6px 10px;
            padding-right: 20px;
        }}
        QComboBox:hover {{
             border: 1px solid {c["PRIMARY"]};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 25px;
            border-left-width: 0px;
        }}
        
        /* ToolBox */
        QToolBox {{
            background: transparent;
            spacing: 5px; /* Space between tabs */
        }}
        QToolBox::tab {{
            background: {c["SURFACE"]};
            border: 1px solid {c["BORDER"]};
            border-radius: 8px;
            color: {c["TEXT_PRIMARY"]};
            font-weight: bold;
            padding-left: 10px;
        }}
        QToolBox::tab:selected {{
            background: {c["SURFACE_LIGHT"]};
            color: {c["PRIMARY"]};
            border: 1px solid {c["PRIMARY"]};
        }}
        QToolBox::tab:hover {{
            border: 1px solid {c["ACCENT"]};
        }}

        QComboBox::down-arrow {{
            image: url(assets/icons/chevron_down.svg); /* If you have icons, else standard arrow */
            width: 12px;
            height: 12px;
        }}
        /* Fallback arrow styling if no SVG */
        QComboBox::down-arrow {{ 
            width: 0; 
            height: 0; 
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {c["TEXT_SECONDARY"]};
            margin-right: 10px;
        }}
        
        QComboBox QAbstractItemView {{
            border: 1px solid {c["BORDER"]};
            background-color: {c["SURFACE"]};
            selection-background-color: {c["PRIMARY"]}30;
            selection-color: {c["TEXT_PRIMARY"]};
            border-radius: 8px;
            outline: none;
        }}

        /* Sliders */
        QSlider::groove:horizontal {{
            border: 1px solid {c["BORDER"]};
            height: 6px;
            background: {c["SURFACE_LIGHT"]};
            margin: 2px 0;
            border-radius: 3px;
        }}
        QSlider::sub-page:horizontal {{
            background: {c["PRIMARY"]};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {c["SURFACE"]};
            border: 2px solid {c["PRIMARY"]};
            width: 18px;
            height: 18px;
            margin: -7px 0;
            border-radius: 9px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {c["PRIMARY"]};
        }}

        /* Scrollbars */
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {c["SURFACE_LIGHT"]};
            min-height: 30px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {c["TEXT_SECONDARY"]};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        
        /* Checkbox */
        QCheckBox {{
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid {c["BORDER"]};
            background-color: {c["BACKGROUND"]};
        }}
        QCheckBox::indicator:checked {{
            background-color: {c["PRIMARY"]};
            border: 1px solid {c["PRIMARY"]};
            image: url(assets/icons/check.svg); 
        }}
        /* Fallback check */
        QCheckBox::indicator:checked {{
            background-color: {c["PRIMARY"]};
        }}
    """)
