"""
NeuroSeg-Pro Version Management
Whenever a major update happens, update __version__ accordingly.
"""

__version__ = "4.0.0"
__edition__ = "Clinical Edition"
__app_name__ = "NeuroSeg-Pro"

def get_version_string():
    return f"v{__version__} {__edition__}"
