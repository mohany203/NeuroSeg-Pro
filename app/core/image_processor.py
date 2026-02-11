import numpy as np

class ImageProcessor:
    @staticmethod
    def normalize(data: np.ndarray):
        """Normalizes data to 0-1 range (Min-Max)."""
        min_val = np.min(data)
        max_val = np.max(data)
        if max_val - min_val == 0:
            return np.zeros_like(data)
        return (data - min_val) / (max_val - min_val)

    @staticmethod
    def z_score_normalize(data: np.ndarray):
        """
        Applies Z-Score normalization (mean=0, std=1).
        Calculates statistics only on non-zero region to avoid background bias.
        """
        mask = data > 0
        if not np.any(mask):
            return data
            
        mean = data[mask].mean()
        std = data[mask].std()
        
        if std == 0:
            return data
            
        normalized = np.zeros_like(data)
        normalized[mask] = (data[mask] - mean) / std
        return normalized

    @staticmethod
    def get_slice(data: np.ndarray, plane: str, index: int):
        """
        Extracts a 2D slice from the 3D volume.
        plane: 'axial', 'sagittal', or 'coronal'
        """
        if plane == 'axial':
            # Horizontal cut (xy plane) - usually z-axis
            # Transpose to make it visually correct if needed
            slice_data = data[:, :, index]
            return np.rot90(slice_data) 
        elif plane == 'sagittal':
            # Side view (yz plane) - usually x-axis
            slice_data = data[index, :, :]
            return np.rot90(slice_data)
        elif plane == 'coronal':
            # Front view (xz plane) - usually y-axis
            slice_data = data[:, index, :]
            return np.rot90(slice_data)
        else:
            raise ValueError("Invalid plane. Use 'axial', 'sagittal', or 'coronal'.")

    @staticmethod
    def calculate_metrics(pred_mask: np.ndarray, gt_mask: np.ndarray, voxel_vol_mm3: float = 1.0):
        """
        Calculates Dice Score and Tumor Volume for each class.
        Classes: 1 (NCR), 2 (ED), 4 (ET)
        """
        metrics = {}
        classes = {1: "Necrosis", 2: "Edema", 4: "Enhancing"}
        
        for label, name in classes.items():
            p = (pred_mask == label)
            g = (gt_mask == label)
            
            # Dice
            intersection = np.logical_and(p, g).sum()
            union = p.sum() + g.sum()
            dice = (2. * intersection) / (union + 1e-6) # Add epsilon to avoid div by zero
            
            # Volume
            vol = p.sum() * voxel_vol_mm3
            
            metrics[name] = {
                "dice": dice,
                "volume": vol
            }
            
        # Whole Tumor (1+2+4)
        p_wt = (pred_mask > 0)
        g_wt = (gt_mask > 0)
        intersection_wt = np.logical_and(p_wt, g_wt).sum()
        union_wt = p_wt.sum() + g_wt.sum()
        dice_wt = (2. * intersection_wt) / (union_wt + 1e-6)
        
        metrics["Whole Tumor"] = {
            "dice": dice_wt,
            "volume": p_wt.sum() * voxel_vol_mm3
        }
        
        return metrics

    @staticmethod
    def calculate_difference_map(prediction: np.ndarray, ground_truth: np.ndarray) -> np.ndarray:
        """
        Generates a Difference Map for visualization.
        Returns a mask with codes:
        0: Background / Correct Negative
        1: False Positive (Red) - Model predicted tumor, but there is none.
        2: False Negative (Blue) - Model missed tumor.
        3: True Positive (Green) - Agreement.
        """
        # Binarize inputs (Focus on Whole Tumor for visual simplicity first)
        p_bin = (prediction > 0).astype(np.uint8)
        g_bin = (ground_truth > 0).astype(np.uint8)
        
        diff_map = np.zeros_like(prediction, dtype=np.uint8)
        
        # False Positive (Pred=1 - GT=0 = 1) -> Map 1
        fp = (p_bin == 1) & (g_bin == 0)
        diff_map[fp] = 1
        
        # False Negative (GT=1 - Pred=0 = 1) -> Map 2
        fn = (p_bin == 0) & (g_bin == 1)
        diff_map[fn] = 2
        
        # True Positive (Intersection) -> Map 3
        tp = (p_bin == 1) & (g_bin == 1)
        diff_map[tp] = 3
        
        return diff_map

    @staticmethod
    def to_uint8(data: np.ndarray):
        """Converts normalized (0-1) data to uint8 (0-255) for display."""
        return (data * 255).astype(np.uint8)
