import sys
import os
import ctypes

# Fix for OMP: Error #15 (Multiple OpenMP runtimes)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Suppress TensorFlow oneDNN logs
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

def main():
    # --- High-DPI Scaling (MUST be before QApplication) ---
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Fix for Windows Taskbar Icon
    if os.name == 'nt':
        myappid = 'gradproject.neuroseg.pro.v1'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    app.setApplicationName("Brain Tumor Segmentation Pro")
    app.setOrganizationName("GraduationProject")
    app.setWindowIcon(QIcon("assets/NeuroSeg_App_Icon.png"))
    
    # Compute DPI scale factor and store it for the whole app
    screen = app.primaryScreen()
    logical_dpi = screen.logicalDotsPerInch() if screen else 96.0
    dpi_scale = max(logical_dpi / 96.0, 1.0)  # 1.0 for 96 DPI, 1.5 for 144, 2.0 for 192
    
    # Apply Rich Theme with DPI scaling
    from app.ui.theme import apply_theme
    apply_theme(app, dpi_scale=dpi_scale)
    
    from app.ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
