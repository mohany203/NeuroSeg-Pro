from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor, QFont
from app.ui.settings import Settings

# --- Global DPI Scale Factor ---
_dpi_scale = 1.0

def get_dpi_scale():
    """Returns the global DPI scale factor computed at app startup."""
    return _dpi_scale

def scaled(px):
    """Scale a pixel value by the global DPI factor. Returns int."""
    return max(1, int(round(px * _dpi_scale)))

def scaled_font(px):
    return max(5, scaled(px))


# --- Premium Palette (Tailwind-inspired) ---

# Dark Mode: "Deep Space Medical"
DARK_THEME = {
    "PRIMARY": "#3B82F6",        # Blue-500
    "PRIMARY_HOVER": "#2563EB",  # Blue-600
    "PRIMARY_LIGHT": "#3B82F620",# Blue-500 @ 12%
    "ACCENT": "#8B5CF6",         # Violet-500
    "ACCENT_LIGHT": "#8B5CF620", # Violet @ 12%
    "BACKGROUND": "#0F0F12",     # Rich deep black
    "SURFACE": "#1A1A22",        # Card surface
    "SURFACE_LIGHT": "#252530",  # Hover surface
    "SURFACE_HOVER": "#2E2E3A",  # Active hover
    "TEXT_PRIMARY": "#F0F0F5",   # Near-white
    "TEXT_SECONDARY": "#9898A8", # Muted
    "TEXT_MUTED": "#65657A",     # Very muted
    "BORDER": "#2A2A38",         # Subtle border
    "BORDER_HOVER": "#3B82F680", # Blue border on hover
    "SUCCESS": "#10B981",        # Emerald-500
    "WARNING": "#F59E0B",        # Amber-500
    "ERROR": "#EF4444",          # Red-500
    "GRADIENT_PRIMARY": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3B82F6, stop:1 #8B5CF6)",
    "GRADIENT_SURFACE": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1A1A22, stop:1 #15151D)",
    "GRADIENT_ACCENT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8B5CF6, stop:1 #EC4899)",
    "CARD_BG": "#1E1E28",
    "SHADOW": "rgba(0, 0, 0, 180)",
    "SIDEBAR_BG": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #14141C, stop:1 #0F0F16)",
    "HEADER_BG": "#121218",
    "SCROLLBAR_BG": "#252530",
    "SCROLLBAR_HANDLE": "#3A3A4A",
    "INPUT_BG": "#15151E",
    "BADGE_BG": "#3B82F630",
    "BADGE_TEXT": "#93C5FD",
    "DANGER_BG": "#7F1D1D",      # Dark Red
    "DANGER_FG": "#FECACA",      # Light Red Text
}

# Light Mode: "Warm Clinical" — NOT plain white, warm tints + gradients
LIGHT_THEME = {
    "PRIMARY": "#2563EB",        # Blue-600
    "PRIMARY_HOVER": "#1D4ED8",  # Blue-700
    "PRIMARY_LIGHT": "#2563EB18",# Blue @ 10%
    "ACCENT": "#7C3AED",         # Violet-600
    "ACCENT_LIGHT": "#7C3AED18", # Violet @ 10%
    "BACKGROUND": "#F0F2F8",     # Warm blue-gray (not white)
    "SURFACE": "#FAFBFF",        # Very light blue-white
    "SURFACE_LIGHT": "#EEF0F7",  # Slightly darker
    "SURFACE_HOVER": "#E4E7F0",  # Hover state
    "TEXT_PRIMARY": "#1A1D2E",   # Deep navy
    "TEXT_SECONDARY": "#5B6078", # Muted navy
    "TEXT_MUTED": "#9098B0",     # Very muted
    "BORDER": "#D8DCE8",         # Soft border
    "BORDER_HOVER": "#2563EB60", # Blue border on hover
    "SUCCESS": "#059669",        # Emerald-600
    "WARNING": "#D97706",        # Amber-600
    "ERROR": "#DC2626",          # Red-600
    "GRADIENT_PRIMARY": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2563EB, stop:1 #7C3AED)",
    "GRADIENT_SURFACE": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FAFBFF, stop:1 #F0F2F8)",
    "GRADIENT_ACCENT": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7C3AED, stop:1 #DB2777)",
    "CARD_BG": "#FFFFFF",
    "SHADOW": "rgba(30, 40, 80, 60)",
    "SIDEBAR_BG": "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F8F9FF, stop:1 #ECEEF8)",
    "HEADER_BG": "#F5F6FC",
    "SCROLLBAR_BG": "#E8EAF2",
    "SCROLLBAR_HANDLE": "#C8CCDA",
    "INPUT_BG": "#F5F6FC",
    "BADGE_BG": "#2563EB20",
    "BADGE_TEXT": "#1D4ED8",
    "DANGER_BG": "#FEE2E2",      # Light Red
    "DANGER_FG": "#991B1B",      # Dark Red Text
}

def get_theme_palette():
    """Returns the current theme palette dictionary."""
    settings = Settings()
    start_theme = settings.get("theme")
    return DARK_THEME if start_theme == "Dark" else LIGHT_THEME

def apply_theme(app: QApplication, dpi_scale: float = 1.0):
    """Applies a modern, rich theme (Light/Dark) with DPI-aware scaling."""
    global _dpi_scale
    _dpi_scale = dpi_scale
    
    settings = Settings()
    base_font_size = settings.get("font_size")  # e.g. 14
    start_theme = settings.get("theme")
    
    # Scale the base font size by DPI
    fs = scaled(base_font_size)
    
    # Select Palette
    c = DARK_THEME if start_theme == "Dark" else LIGHT_THEME
    
    app.setStyle("Fusion")
    
    # Set Global Font
    font = QFont("Segoe UI")
    font.setPixelSize(max(5, fs))
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
    
    # --- Helper pixel values (all DPI-scaled) ---
    s = lambda px: scaled(px)  # shortcut
    sf = lambda v: max(5, int(v)) # Min font size helper
    
    app.setStyleSheet(f"""
        /* === GLOBAL === */
        QMainWindow {{
            background-color: {c["BACKGROUND"]};
        }}
        QWidget {{
            font-family: 'Segoe UI', 'Inter', sans-serif;
            font-size: {sf(fs)}px;
            color: {c["TEXT_PRIMARY"]};
        }}
        
        /* ToolTips */
        QToolTip {{
            background-color: {c["SURFACE"]};
            color: {c["TEXT_PRIMARY"]};
            border: 1px solid {c["BORDER"]};
            border-radius: {s(6)}px;
            padding: {s(6)}px {s(10)}px;
            font-size: {sf(fs - s(1))}px;
        }}

        /* === CARDS & FRAMES === */
        QFrame#Card {{
            background: {c["GRADIENT_SURFACE"]};
            border-radius: {s(16)}px;
            border: 1px solid {c["BORDER"]};
        }}
        QFrame#Card:hover {{
            border: 1px solid {c["BORDER_HOVER"]};
        }}
        
        QFrame#Sidebar {{
            background: {c["SIDEBAR_BG"]};
            border-right: 1px solid {c["BORDER"]};
        }}
        
        QFrame#ViewportFrame {{
            background-color: #000;
            border: 1px solid {c["BORDER"]};
            border-radius: {s(8)}px;
        }}
        
        /* === GROUP BOX === */
        QGroupBox {{
            background: {c["GRADIENT_SURFACE"]};
            border: 1px solid {c["BORDER"]};
            border-radius: {s(8)}px;
            margin-top: {s(10)}px;
            padding-top: {s(20)}px;
            padding-bottom: {s(4)}px;
            padding-left: {s(8)}px;
            padding-right: {s(8)}px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: {s(1)}px {s(6)}px;
            left: {s(8)}px;
            bottom: 0px;
            color: {c["PRIMARY"]};
            font-weight: 700;
            font-size: {sf(fs - s(2))}px;
            background-color: {c["SURFACE"]};
            border-radius: {s(3)}px;
        }}
        
        /* === BUTTONS === */
        QPushButton {{
            background-color: {c["SURFACE_LIGHT"]};
            color: {c["TEXT_PRIMARY"]};
            border: 1px solid {c["BORDER"]};
            border-radius: {s(6)}px;
            padding: {s(5)}px {s(10)}px;
            font-weight: 600;
            font-size: {sf(fs - s(2))}px;
        }}
        QPushButton:hover {{
            background-color: {c["SURFACE_HOVER"]};
            border: 1px solid {c["BORDER_HOVER"]};
        }}
        QPushButton:pressed {{
            background-color: {c["PRIMARY_LIGHT"]};
        }}
        QPushButton:checked {{
            background-color: {c["PRIMARY"]};
            color: white;
            border: 1px solid {c["PRIMARY"]};
        }}
        
        /* Primary/Action Button */
        QPushButton#AccentButton {{
            background: {c["GRADIENT_PRIMARY"]};
            color: white;
            border: none;
            padding: {s(8)}px {s(16)}px;
            border-radius: {s(6)}px;
            font-weight: 700;
            font-size: {sf(fs - s(1))}px;
        }}
        QPushButton#AccentButton:hover {{
            background: {c["GRADIENT_ACCENT"]};
        }}
        QPushButton#AccentButton:disabled {{
            background: {c["SURFACE_LIGHT"]};
            color: {c["TEXT_MUTED"]};
        }}
        
        /* Navigation Buttons (Sidebar) */
        QPushButton#NavButton {{
            background-color: transparent;
            border: none;
            text-align: left;
            padding-left: {s(20)}px;
            font-size: {sf(fs + s(1))}px;
            color: {c["TEXT_SECONDARY"]};
            border-radius: {s(12)}px;
            margin-bottom: {s(4)}px;
        }}
        QPushButton#NavButton:hover {{
            background-color: {c["SURFACE_LIGHT"]};
            color: {c["TEXT_PRIMARY"]};
            padding-left: {s(24)}px;
        }}
        QPushButton#NavButton:checked {{
            background: {c["PRIMARY_LIGHT"]};
            color: {c["PRIMARY"]};
            border-left: {s(4)}px solid {c["PRIMARY"]};
            font-weight: bold;
        }}
        
        /* Tool Buttons (Info ?) */
        QToolButton#InfoButton {{
            background-color: transparent;
            color: {c["TEXT_SECONDARY"]};
            border: 1px solid {c["BORDER"]};
            border-radius: {s(12)}px;
            font-weight: bold;
            font-size: {sf(fs)}px;
            padding: 0px;
        }}
        QToolButton#InfoButton:hover {{
            color: {c["PRIMARY"]};
            border: 1px solid {c["PRIMARY"]};
            background-color: {c["PRIMARY_LIGHT"]};
        }}

        /* === COMBO BOXES === */
        QComboBox {{
            background-color: {c["INPUT_BG"]};
            color: {c["TEXT_PRIMARY"]};
            border: 1px solid {c["BORDER"]};
            border-radius: {s(8)}px;
            padding: {s(4)}px {s(8)}px;
            padding-right: {s(20)}px;
            font-size: {sf(fs - s(2))}px;
            min-height: {s(18)}px;
        }}
        QComboBox:hover {{
            border: 1px solid {c["BORDER_HOVER"]};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: {s(28)}px;
            border-left-width: 0px;
        }}
        QComboBox::down-arrow {{ 
            width: 0; 
            height: 0; 
            border-left: {s(5)}px solid transparent;
            border-right: {s(5)}px solid transparent;
            border-top: {s(5)}px solid {c["TEXT_SECONDARY"]};
            margin-right: {s(10)}px;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {c["BORDER"]};
            background-color: {c["SURFACE"]};
            selection-background-color: {c["PRIMARY_LIGHT"]};
            selection-color: {c["TEXT_PRIMARY"]};
            border-radius: {s(8)}px;
            outline: none;
            padding: {s(4)}px;
        }}

        /* === SPIN BOX === */
        QSpinBox {{
            background-color: {c["INPUT_BG"]};
            color: {c["TEXT_PRIMARY"]};
            border: 1px solid {c["BORDER"]};
            border-radius: {s(6)}px;
            padding: {s(4)}px {s(8)}px;
            font-size: {sf(fs - s(1))}px;
            min-height: {s(24)}px;
        }}
        QSpinBox:hover {{
            border: 1px solid {c["BORDER_HOVER"]};
        }}

        /* === TOOLBOX === */
        QToolBox {{
            background: transparent;
            spacing: {s(5)}px;
        }}
        QToolBox::tab {{
            background: {c["SURFACE"]};
            border: 1px solid {c["BORDER"]};
            border-radius: {s(8)}px;
            color: {c["TEXT_PRIMARY"]};
            font-weight: bold;
            padding-left: {s(12)}px;
        }}
        QToolBox::tab:selected {{
            background: {c["SURFACE_LIGHT"]};
            color: {c["PRIMARY"]};
            border: 1px solid {c["PRIMARY"]};
        }}
        QToolBox::tab:hover {{
            border: 1px solid {c["ACCENT"]};
        }}

        /* === SLIDERS === */
        QSlider::groove:horizontal {{
            border: 1px solid {c["BORDER"]};
            height: {s(6)}px;
            background: {c["SURFACE_LIGHT"]};
            margin: {s(2)}px 0;
            border-radius: {s(3)}px;
        }}
        QSlider::sub-page:horizontal {{
            background: {c["GRADIENT_PRIMARY"]};
            border-radius: {s(3)}px;
        }}
        QSlider::handle:horizontal {{
            background: {c["SURFACE"]};
            border: {s(2)}px solid {c["PRIMARY"]};
            width: {s(18)}px;
            height: {s(18)}px;
            margin: {s(-7)}px 0;
            border-radius: {s(9)}px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {c["PRIMARY"]};
        }}

        /* === SCROLLBARS === */
        QScrollBar:vertical {{
            background: {c["SCROLLBAR_BG"]};
            width: {s(8)}px;
            margin: 0px;
            border-radius: {s(4)}px;
        }}
        QScrollBar::handle:vertical {{
            background: {c["SCROLLBAR_HANDLE"]};
            min-height: {s(30)}px;
            border-radius: {s(4)}px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {c["TEXT_SECONDARY"]};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar:horizontal {{
            background: {c["SCROLLBAR_BG"]};
            height: {s(8)}px;
            margin: 0px;
            border-radius: {s(4)}px;
        }}
        QScrollBar::handle:horizontal {{
            background: {c["SCROLLBAR_HANDLE"]};
            min-width: {s(30)}px;
            border-radius: {s(4)}px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {c["TEXT_SECONDARY"]};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
        
        /* === CHECKBOX === */
        QCheckBox {{
            spacing: {s(8)}px;
            color: {c["TEXT_PRIMARY"]};
        }}
        QCheckBox::indicator {{
            width: {s(18)}px;
            height: {s(18)}px;
            border-radius: {s(4)}px;
            border: 1px solid {c["BORDER"]};
            background-color: {c["INPUT_BG"]};
        }}
        QCheckBox::indicator:checked {{
            background-color: {c["PRIMARY"]};
            border: 1px solid {c["PRIMARY"]};
        }}
        QCheckBox::indicator:hover {{
            border: 1px solid {c["PRIMARY"]};
        }}

        /* === TABLE WIDGET === */
        QTableWidget {{
            background-color: {c["SURFACE"]};
            border: 1px solid {c["BORDER"]};
            border-radius: {s(8)}px;
            gridline-color: {c["BORDER"]};
            color: {c["TEXT_PRIMARY"]};
        }}
        QHeaderView::section {{
            background: {c["GRADIENT_SURFACE"]};
            padding: {s(4)}px;
            border: none;
            border-bottom: 1px solid {c["BORDER"]};
            color: {c["TEXT_SECONDARY"]};
            font-weight: bold;
            font-size: {sf(fs - s(2))}px;
        }}
        QTableWidget::item {{
            padding: {s(3)}px {s(6)}px;
            font-size: {sf(fs - s(1))}px;
            color: {c["TEXT_PRIMARY"]};
        }}
        QTableWidget::item:selected {{
            background-color: {c["PRIMARY_LIGHT"]};
            color: {c["TEXT_PRIMARY"]};
        }}
        QTableWidget::item:alternate {{
            background-color: {c["SURFACE_LIGHT"]};
        }}

        /* === TAB WIDGET === */
        QTabWidget::pane {{
            border: 1px solid {c["BORDER"]};
            border-radius: {s(8)}px;
            background: {c["SURFACE"]};
        }}
        QTabBar::tab {{
            background: {c["SURFACE_LIGHT"]};
            color: {c["TEXT_SECONDARY"]};
            border: 1px solid {c["BORDER"]};
            border-bottom: none;
            border-top-left-radius: {s(8)}px;
            border-top-right-radius: {s(8)}px;
            padding: {s(8)}px {s(18)}px;
            font-weight: 600;
            font-size: {sf(fs - s(1))}px;
            margin-right: {s(2)}px;
        }}
        QTabBar::tab:selected {{
            background: {c["SURFACE"]};
            color: {c["PRIMARY"]};
            border-bottom: {s(2)}px solid {c["PRIMARY"]};
        }}
        QTabBar::tab:hover {{
            background: {c["SURFACE_HOVER"]};
            color: {c["TEXT_PRIMARY"]};
        }}

        /* === LIST WIDGET === */
        QListWidget {{
            background-color: {c["SURFACE"]};
            border: 1px solid {c["BORDER"]};
            border-radius: {s(8)}px;
            outline: none;
            color: {c["TEXT_PRIMARY"]};
        }}
        QListWidget::item {{
            padding: {s(8)}px;
            border-radius: {s(6)}px;
            color: {c["TEXT_SECONDARY"]};
        }}
        QListWidget::item:hover {{
            background-color: {c["SURFACE_LIGHT"]};
            color: {c["TEXT_PRIMARY"]};
        }}
        QListWidget::item:selected {{
            background-color: {c["PRIMARY_LIGHT"]};
            color: {c["PRIMARY"]};
        }}

        /* === PROGRESS BAR === */
        QProgressBar {{
            border: 1px solid {c["BORDER"]};
            border-radius: {s(4)}px;
            text-align: center;
            background-color: {c["SURFACE_LIGHT"]};
            height: {s(8)}px;
            color: {c["TEXT_PRIMARY"]};
        }}
        QProgressBar::chunk {{
            background: {c["GRADIENT_PRIMARY"]};
            border-radius: {s(4)}px;
        }}

        /* === LABELS === */
        QLabel {{
            color: {c["TEXT_PRIMARY"]};
        }}
        QLabel#SectionLabel {{
            color: {c["TEXT_SECONDARY"]};
            font-size: {sf(max(fs - s(3), s(10)))}px;
            font-weight: 600;
            padding: {s(2)}px 0px;
        }}
        QLabel#Header {{
            font-size: {sf(fs + s(10))}px;
            font-weight: 800;
            color: {c["TEXT_PRIMARY"]};
            padding: {s(10)}px 0;
        }}
        QLabel#SubHeader {{
            font-size: {sf(fs + s(4))}px;
            font-weight: 700;
            color: {c["PRIMARY"]};
            padding: {s(5)}px 0;
        }}

        /* === LEGEND CHIP === */
        QFrame#LegendChip {{
            background-color: {c["SURFACE_LIGHT"]};
            border: 1px solid {c["BORDER"]};
            border-radius: {s(6)}px;
            padding: {s(4)}px {s(8)}px;
        }}

        /* === STATUS PILL === */
        QLabel#StatusPill {{
            background-color: {c["BADGE_BG"]};
            border: 1px solid {c["BORDER"]};
            border-radius: {s(10)}px;
            padding: {s(3)}px {s(10)}px;
            font-size: {sf(fs - s(1))}px;
            font-weight: 600;
            color: {c["BADGE_TEXT"]};
        }}

        /* === MESSAGE BOX === */
        QMessageBox {{
            background-color: {c["SURFACE"]};
        }}
        QMessageBox QLabel {{
            color: {c["TEXT_PRIMARY"]};
            font-size: {sf(fs)}px;
        }}
    """)
