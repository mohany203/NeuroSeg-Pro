import torch
import numpy as np
from monai.networks.nets import UNet
from monai.inferers import sliding_window_inference

class InferenceEngine:
    def __init__(self, model_path: str = None, device: str = None):
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.current_model_path = None
        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: str):
        """
        Loads the model from a .pth file.
        NOTE: This assumes a specific architecture (MONAI Basic UNet).
        If the user has a custom model class, this needs to be updated or dynamic loading implemented.
        """
        try:
            # Definition of the model architecture (Must match training)
            # Defaulting to a standard            # Load Custom Quantum Model
            from app.core.custom_model import DynUNet
            
            self.model = DynUNet(
                spatial_dims=3,
                in_channels=4,
                out_channels=4,
                deep_supervision=False, # No deep supervision needed for inference
                KD=False
            ).to(self.device)

            checkpoint = torch.load(model_path, map_location=self.device)
            
            # Determine the correct state dict
            state_dict = None
            if 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
            elif 'teacher_model' in checkpoint:
                state_dict = checkpoint['teacher_model']
            elif 'student_model' in checkpoint:
                state_dict = checkpoint['student_model']
            else:
                state_dict = checkpoint

            # Fix potential key mismatches (e.g. 'module.' prefix or missing 'model.' prefix)
            # MONAI UNet expects keys like 'model.0.conv...'
            # Use strict=False to allow loading partially matching models if needed, 
            # but ideally we want exact match. 
            
            # Sanitize keys if needed
            new_state_dict = {}
            for k, v in state_dict.items():
                # Remove 'module.' prefix if present (DataParallel)
                name = k.replace("module.", "")
                new_state_dict[name] = v
            
            # Attempt load
            try:
                self.model.load_state_dict(new_state_dict, strict=True)
            except RuntimeError as e:
                print(f"Strict load failed: {e}. Retrying with strict=False")
                self.model.load_state_dict(new_state_dict, strict=False)
            
            self.model.eval()
            self.current_model_path = model_path
            print(f"Model loaded from {model_path}")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise e

    def predict(self, input_data: np.ndarray):
        """
        Runs inference on the input data.
        input_data: 4D numpy array (Channels, D, H, W)
        """
        if self.model is None:
            raise ValueError("Model not loaded.")

        with torch.no_grad():
            # Input: (C, D, H, W) -> (B, C, D, H, W)
            input_tensor = torch.from_numpy(input_data).unsqueeze(0).float().to(self.device)

            # Use full-volume inference for moderate volumes and sliding-window for large ones.
            # This avoids destructive global resize that can collapse small enhancing regions.
            spatial_shape = input_tensor.shape[2:]
            max_dim = max(spatial_shape)
            if max_dim > 160:
                raw_output = sliding_window_inference(
                    inputs=input_tensor,
                    roi_size=(128, 128, 128),
                    sw_batch_size=1,
                    predictor=self.model,
                    overlap=0.5,
                    mode="gaussian",
                )
            else:
                raw_output = self.model(input_tensor)

            # ── Sigmoid-based hierarchical post-processing ──
            # Model outputs 4 channels: [BG, WT, TC, ET] via sigmoid (NOT softmax).
            # Apply sigmoid > 0.5 thresholding, then priority-based label assignment.
            # Priority: ET (3) overwrites TC/NCR (1) overwrites WT/ED (2).
            # Reference: github.com/AhmeddEmad7/Brain-Tumor-Segmentation-Advancing-Generalizability
            outputs = self._extract_logits(raw_output)
            if outputs.ndim != 5:
                raise ValueError(f"Unexpected model output shape {tuple(outputs.shape)}. Expected (B, C, D, H, W).")

            output_probs = (torch.sigmoid(outputs) > 0.5)
            output = output_probs[0]  # Remove batch dim → (C, D, H, W)

            _, D, H, W = output.shape
            seg_mask = torch.zeros((D, H, W), dtype=torch.float32, device=output.device)

            # Channel 1 = Whole Tumor  → assign label 2 (Edema) by default
            seg_mask[output[1] == 1] = 2
            # Channel 2 = Tumor Core   → overwrite with label 1 (Necrosis/NCR)
            seg_mask[output[2] == 1] = 1
            # Channel 3 = Enhancing    → overwrite with label 3 (Enhancing Tumor/ET)
            seg_mask[output[3] == 1] = 3

            return seg_mask.cpu().numpy().astype(np.uint8)

    def _extract_logits(self, raw_output: torch.Tensor):
        """Normalizes model outputs into a logits tensor of shape (B, C, D, H, W)."""
        if isinstance(raw_output, dict):
            # Prefer common segmentation keys.
            for key in ("pred", "logits", "output", "out"):
                if key in raw_output and torch.is_tensor(raw_output[key]):
                    return raw_output[key]

            # Fallback: first tensor value in dict.
            for value in raw_output.values():
                if torch.is_tensor(value):
                    return value

            raise ValueError("Model output dict does not contain a tensor prediction.")

        if isinstance(raw_output, (tuple, list)):
            for value in raw_output:
                if torch.is_tensor(value):
                    return value
            raise ValueError("Model output tuple/list does not contain a tensor prediction.")

        if torch.is_tensor(raw_output):
            return raw_output

        raise ValueError(f"Unsupported model output type: {type(raw_output)}")

    def run_inference(self, volume: np.ndarray, model_path: str):
        """
        Loads the model if necessary and runs inference.
        """
        if self.current_model_path != model_path:
            self.load_model(model_path)
            
        return self.predict(volume)