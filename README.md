# NeuroSeg-Pro: MRI Segmentation & Visualization Tool

NeuroSeg-Pro is a PyQt5-based application designed for visualizing and segmenting brain MRI scans using deep learning models. It provides a rich interface for comparing model outputs, ground truth, and difference maps.

## 🚀 Key Features

### Visualization
- **Multi-Planar Reconstruction (MPR):** View Axial, Sagittal, and Coronal planes simultaneously.
- **3D Viewport:** Interactive 3D visualization of segmentation masks (if enabled).
- **Advanced Tools:** 
  - **Grid Overlay:** Helper grid for alignment.
  - **Crosshair:** Navigate specific coordinates across all views.
  - **MRI Visibility Toggle:** Focus on the mask by hiding the background MRI.

### AI Analysis
- **Model Selection:** Choose between different pre-trained models (e.g., Teacher/Student variants).
- **Comparison Modes:**
  - **Model A vs Model B:** Side-by-side comparison.
  - **Model A vs Ground Truth:** Validate predictions against expert annotations.
  - **Overlay vs Raw:** Compare active segmentation with the raw scan.
- **Metrics:** Real-time calculation of Dice Coefficient, Sensitivity, Specificity, and Hausdorff Distance.

### User Interface
- **Modern Dark Theme:** "Deep Space Medical" theme for comfortable viewing.
- **Dynamic Legend:** Legend updates automatically based on the classes present in the current view.
- **One-Click Export:** Save segmentation masks as `.nii.gz` files.

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+ (Ensure Python is added to your PATH during installation)
- [Git](https://git-scm.com/) (Optional, for cloning)

### 1. Download the Application
If you have Git installed, clone the repository:
```bash
git clone https://github.com/mohany203/NeuroSeg-Pro.git
cd NeuroSeg-Pro
```
*(Alternatively, you can download the project as a ZIP file from GitHub and extract it).*

### 2. Run Setup (Automated)
We provide an automated setup script that creates a virtual environment, installs all necessary libraries, and creates a desktop shortcut for you.

1. Locate the **`setup.bat`** file in the project folder.
2. **Double-click** `setup.bat`.
3. It will prompt for Administrator privileges (required to install libraries and create shortcuts). Click **Yes**.
4. Wait for the installation to finish.

### 3. Setup Models
> **Note:** Due to file size limits, pre-trained model weights (`.pth` files) are NOT included in this repository.
> Please place your model files in the `models/` directory.

Example structure:
```
NeuroSeg-Pro/
├── app/
├── models/
│   ├── Teacher_model_50.pth
│   └── ...
├── assets/
└── ...
```

---

## ▶️ Running the Application

After running the setup, you can launch the application by double-clicking the **NeuroSeg-Pro** shortcut on your Desktop!

Alternatively, you can run the application directly from the folder:
- Double-click the **`run_app.bat`** file.

---

## 📂 Project Structure

- `app/` - Source code.
  - `main.py` - Entry point.
  - `ui/` - Interface widgets and themes.
  - `core/` - Logic for inference and image processing.
- `assets/` - Icons and resources.
- `models/` - Directory for model weights (ignored by git).
- `model_output/` - Saved segmentation masks.

---

## 🤝 Contributing
Contributions are welcome! Please open an issue or submit a pull request for any improvements.

## 📄 License
MIT License
