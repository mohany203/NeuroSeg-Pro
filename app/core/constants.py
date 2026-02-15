
# ROI Label Codes (BraTS Standard)
class Labels:
    NCR = 1  # Necrotic / Non-enhancing tumor core
    ED = 2   # Peritumoral Edema
    ET = 3   # Enhancing Tumor
    # Final labels: 0=BG, 1=NCR, 2=ED, 3=ET

# ROI Definitions (Name -> List of Labels)
ROI_DEFINITIONS = {
    "Whole Tumor": [Labels.NCR, Labels.ED, Labels.ET],
    "Tumor Core": [Labels.NCR, Labels.ET],
    "Enhancing Tumor": [Labels.ET],
    "Necrosis": [Labels.NCR],
    "Edema": [Labels.ED]
}

# Display Colors (RGBA 0-255)
# User Request: ET=Red, NC=Green, ED=Yellow
ROI_COLORS = {
    Labels.ET: (177, 122, 101, 255),     # Red
    Labels.NCR: (128, 174, 128, 255),    # Green (Necrosis)
    Labels.ED: (241, 214, 145, 255),   # Yellow
}

# For 3D Visualization (RGBA 0-1)
roi_colors_f = {k: (v[0]/255.0, v[1]/255.0, v[2]/255.0, v[3]/255.0) for k, v in ROI_COLORS.items()}
ROI_COLORS_3D = roi_colors_f
