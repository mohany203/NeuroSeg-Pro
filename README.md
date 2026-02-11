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
- Python 3.8+
- [Git](https://git-scm.com/)

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/NeuroSeg-Pro.git
cd NeuroSeg-Pro
```

### 2. Create a Virtual Environment (Recommended)
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Models
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

To launch the main application interface:

```bash
python -m app.main
```

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
