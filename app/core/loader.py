import nibabel as nib
import numpy as np
import os

class NiftiLoader:
    @staticmethod
    def load_file(file_path: str):
        """
        Loads a .nii or .nii.gz file using nibabel.
        Returns:
            data (np.ndarray): The 3D image data.
            affine (np.ndarray): The affine matrix.
            header (nib.Nifti1Header): The file header.
        Raises:
            ValueError: If file does not exist or format is invalid.
        """
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
        
        try:
            img = nib.load(file_path)
            # Ensure it's canonical orientation
            img = nib.as_closest_canonical(img)
            data = img.get_fdata()
            return data, img.affine, img.header
        except Exception as e:
            raise ValueError(f"Failed to load NIfTI file: {str(e)}")

    @staticmethod
    def get_metadata(file_path: str):
        """Returns basic metadata for display."""
        img = nib.load(file_path)
        header = img.header
        return {
            "dims": header.get_data_shape(),
            "voxel_size": header.get_zooms(),
            "descrip": str(header['descrip'])
        }

    @staticmethod
    def save_file(file_path: str, data: np.ndarray, affine: np.ndarray):
        """
        Saves 3D data to a .nii.gz file.
        """
        if not file_path.endswith('.nii') and not file_path.endswith('.nii.gz'):
             file_path += '.nii'
             
        # Create Nifti Image
        # Ensure data is in standard float or int format if needed, but nibabel handles numpy well.
        img = nib.Nifti1Image(data, affine)
        nib.save(img, file_path)
        return file_path

    @staticmethod
    def load_patient_folder(folder_path: str):
        """
        Scans a folder for BraTS specific modalities (t1, t2, t1ce, flair).
        Returns a dictionary: {'t1': ..., 't2': ..., 't1ce': ..., 'flair': ..., 'affine': ...}
        """
        modalities = {}
        affine = None
        
        # Standard BraTS suffixes
        # Standard BraTS suffixes (including pediatric variations)
        suffixes = {
            't1': ['t1.nii', 't1.nii.gz', 't1n.nii', 't1n.nii.gz'],
            't2': ['t2.nii', 't2.nii.gz', 't2w.nii', 't2w.nii.gz'],
            't1ce': ['t1ce.nii', 't1ce.nii.gz', 't1c.nii', 't1c.nii.gz'],
            'flair': ['flair.nii', 'flair.nii.gz', 't2f.nii', 't2f.nii.gz'],
            'seg': ['seg.nii', 'seg.nii.gz', 'mask.nii', 'mask.nii.gz']
        }

        files = os.listdir(folder_path)
        
        for f in files:
            lower_f = f.lower()
            for mod, suf_list in suffixes.items():
                if any(lower_f.endswith(s) for s in suf_list):
                    # Found a modality
                    path = os.path.join(folder_path, f)
                    try:
                        data, aff, _ = NiftiLoader.load_file(path)
                        modalities[mod] = data
                        if affine is None: affine = aff
                    except Exception as e:
                        print(f"Error loading {mod}: {e}")
        
        if not modalities:
            raise ValueError("No valid NIfTI scans found in this folder.")
            
        modalities['affine'] = affine
        return modalities
