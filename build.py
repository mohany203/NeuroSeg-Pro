import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import shutil
import subprocess
import sys

def run_build():
    print("Starting NeuroSeg Pro Build Process...")
    
    # Check PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Clean previous builds
    if os.path.exists("dist"):
        try:
            shutil.rmtree("dist")
            print("Cleaned 'dist' directory.")
        except Exception as e:
            print(f"Could not clean 'dist': {e}")
            
    if os.path.exists("build"):
        try:
            shutil.rmtree("build")
            print("Cleaned 'build' directory.")
        except Exception as e:
            print(f"Could not clean 'build': {e}")

    # Run PyInstaller
    print("Building Executable...")
    try:
        subprocess.check_call([sys.executable, "-m", "PyInstaller", "build.spec", "--noconfirm"])
        print("Build Completed Successfully!")
        print("\n" + "="*50)
        print("Output Location: dist/NeuroSegPro")
        print("="*50)
        print("\nTo distribute: Compress the 'dist/NeuroSegPro' folder.")
        print("IMPORTANT: The 'models' folder is EXCLUDED.")
        print("   You MUST provide the 'models' folder alongside the .exe (or inside the folder) for the app to detect models.")
        
    except subprocess.CalledProcessError as e:
        print(f"Build Failed: {e}")

if __name__ == "__main__":
    run_build()
