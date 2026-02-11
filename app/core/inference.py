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
            # Prepare Input
            input_tensor = torch.from_numpy(input_data).unsqueeze(0).float().to(self.device) # (1, 4, D, H, W)
            
            # --- 1. RESIZE TO MODEL INPUT SIZE (128, 128, 128) ---
            original_shape = input_tensor.shape[2:] # (D, H, W)
            target_size = (128, 128, 128)
            
            needs_resize = (original_shape != target_size)
            
            if needs_resize:
                # Trilinear for continuous image data; align_corners=False is safer for size preservation
                input_tensor = torch.nn.functional.interpolate(input_tensor, size=target_size, mode='trilinear', align_corners=False)
                
            outputs_dict = self.model(input_tensor)
            
            # Depending on model wrapper, output might be dict or tensor
            if isinstance(outputs_dict, dict):
                outputs = outputs_dict['pred'] # (B, 4, 128, 128, 128)
            else:
                outputs = outputs_dict
                
            # --- 2. RESIZE BACK TO ORIGINAL SHAPE ---
            if needs_resize:
                # Nearest for class labels (or interpolate logits then argmax)
                # Better to interpolate logits (trilinear) then argmax to preserve boundaries smoothly
                outputs = torch.nn.functional.interpolate(outputs, size=original_shape, mode='trilinear', align_corners=False)
                
            return torch.argmax(outputs, dim=1).detach().cpu().numpy()[0] # Remove batch dim

    def run_inference(self, volume: np.ndarray, model_path: str):
        """
        Loads the model if necessary and runs inference.
        """
        if self.current_model_path != model_path:
            self.load_model(model_path)
            
        return self.predict(volume)
