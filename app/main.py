import sys
import os

# Fix for OMP: Error #15 (Multiple OpenMP runtimes)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Suppress TensorFlow oneDNN logs
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtGui import QIcon
from app.ui.theme import apply_theme
from app.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Brain Tumor Segmentation Pro")
    app.setOrganizationName("GraduationProject")
    
    # Apply Rich Dark Theme
    apply_theme(app)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
