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
    def z_score_normalize(data: np.ndarray, nonzero: bool = True):
        """
        Applies Z-Score normalization (mean=0, std=1).
        Args:
            data: Input image volume
            nonzero: If True, calculates statistics only on non-zero region.
                     If False, calculates statistics on entire volume (matches MONAI training).
        """
        if nonzero:
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
        else:
            # Normalize entire volume (including background)
            mean = data.mean()
            std = data.std()
            if std == 0:
                return data - mean
            return (data - mean) / std

    @staticmethod
    def get_slice(data: np.ndarray, plane: str, index: int):
        """
        Extracts a 2D slice from the 3D volume.
        plane: 'axial', 'sagittal', or 'coronal'
        Orientation follows radiological convention (RAS+ NIfTI).
        """
        # User Request: "Rotate 90 deg anticlockwise and flip vertically" relative to previous state.
        # Function to apply this transform to the base slice extraction
        def transform(s):
             # 1. Rotate 90 deg Anti-Clockwise
             rotated = np.rot90(s, k=1)
             # 2. Flip Vertically
             return np.flipud(rotated)

        if plane == 'axial':
            # Horizontal cut (xy plane) - z-axis index
            slice_data = data[:, :, index]
            # Previous: return np.flipud(slice_data)
            # New: Apply transform to the previous result
            return transform(np.flipud(slice_data))
            
        elif plane == 'sagittal':
            # Side view (yz plane) - x-axis index
            slice_data = data[index, :, :]
            # Sagittal: User requested "Rotate 90 deg anticlockwise and flip vertically" relative to previous state.
            current = np.flipud(slice_data)
            rotated = np.rot90(current, k=1)
            return np.flipud(rotated)

        elif plane == 'coronal':
            # Front view (xz plane) - y-axis index
            slice_data = data[:, index, :]
            # Previous: return np.flipud(slice_data)
            # New: Apply transform to the previous result
            return transform(np.flipud(slice_data))

        else:
            raise ValueError("Invalid plane. Use 'axial', 'sagittal', or 'coronal'.")

    @staticmethod
    def calculate_metrics(pred_mask: np.ndarray, gt_mask: np.ndarray, voxel_vol_mm3: float = 1.0):
        """
        Calculates comprehensive segmentation metrics for defined ROIs.
        ROIs: Whole Tumor (WT), Tumor Core (TC), Enhancing Tumor (ET), Necrosis (NC), Edema (ED).
        Metrics: Dice, IoU, Sensitivity, Specificity, Precision, HD95, Volume.
        """
        from app.core.constants import ROI_DEFINITIONS
        metrics = {}

        # Helper for surface distance (HD95)
        def compute_hd95(p, g):
            if not np.any(p) or not np.any(g):
                return -1.0 # Undefined
            
            try:
                from scipy.spatial.distance import directed_hausdorff
                # Get coordinates of boundary points (using slightly eroded mask XOR mask? or just all points)
                # Optimization: Use points from edges only if possible, but here we stick to simple point sets
                p_points = np.argwhere(p)
                g_points = np.argwhere(g)
                
                # Subsample if too large to speed up (approximate)
                max_points = 2000 
                if len(p_points) > max_points:
                    idx = np.random.choice(len(p_points), max_points, replace=False)
                    p_points = p_points[idx]
                if len(g_points) > max_points:
                    idx = np.random.choice(len(g_points), max_points, replace=False)
                    g_points = g_points[idx]
                
                d_forward = directed_hausdorff(p_points, g_points)[0]
                d_backward = directed_hausdorff(g_points, p_points)[0]
                return max(d_forward, d_backward)
            except ImportError:
                return -1.0 # Scipy not installed
            except Exception:
                return 0.0

        for roi_name, labels in ROI_DEFINITIONS.items():
            # Create Binary Masks for this ROI
            if len(labels) == 1:
                p = (pred_mask == labels[0])
                g = (gt_mask == labels[0])
            else:
                p = np.isin(pred_mask, labels)
                g = np.isin(gt_mask, labels)
            
            # Confusion Matrix
            tp = np.logical_and(p, g).sum()
            fp = np.logical_and(p, np.logical_not(g)).sum()
            fn = np.logical_and(np.logical_not(p), g).sum()
            tn = np.logical_and(np.logical_not(p), np.logical_not(g)).sum()
            
            # Metrics
            dice = (2. * tp) / (2. * tp + fp + fn + 1e-6)
            iou = tp / (tp + fp + fn + 1e-6)
            sensitivity = tp / (tp + fn + 1e-6)
            specificity = tn / (tn + fp + 1e-6)
            precision = tp / (tp + fp + 1e-6)
            
            # HD95 (Only if there is overlap or at least both have content)
            hd95 = compute_hd95(p, g) if (tp > 0 or (fp >0 and fn > 0)) else 0.0
        
            metrics[roi_name] = {
                "dice": dice,
                "iou": iou,
                "sensitivity": sensitivity,
                "specificity": specificity,
                "precision": precision,
                "hd95": hd95,
                "volume": p.sum() * voxel_vol_mm3
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
