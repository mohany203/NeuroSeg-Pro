
import sys
import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

try:
    print("Verifying imports...")
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    import pyqtgraph as pg
    import pyqtgraph.opengl as gl
    import numpy as np
    
    print("Core libraries (PyQt5, pyqtgraph, numpy) imported successfully.")
    
    # Check App Imports
    sys.path.append(os.getcwd())
    from app.ui.viewer_widget import ViewerWidget
    print("ViewerWidget imported successfully.")
    
    from app.ui.main_window import MainWindow
    print("MainWindow imported successfully.")
    
    print("VERIFICATION SUCCESS: Environment is ready.")
    
except ImportError as e:
    print(f"VERIFICATION FAILED: Missing module - {e}")
    sys.exit(1)
except Exception as e:
    print(f"VERIFICATION FAILED: Error - {e}")
    sys.exit(1)
