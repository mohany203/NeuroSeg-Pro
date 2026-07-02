"""
NeuroSeg Pro v4.0.0 First-Launch Experience & System Initialization
Verifies configuration directories, migrates legacy user settings, validates required runtime resources, and creates default clinical configuration before launching the UI.
"""

import os
import json
import logging
from datetime import datetime
from app.version import __version__

def initialize_application_environment():
    """
    Performs first-launch validation, directory setup, settings migration, and resource verification.
    """
    app_data_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "NeuroSegPro")
    models_dir = os.path.join(app_data_dir, "models")
    reports_dir = os.path.join(app_data_dir, "reports")
    cache_dir = os.path.join(app_data_dir, "cache")
    logs_dir = os.path.join(app_data_dir, "logs")
    
    for folder in [app_data_dir, models_dir, reports_dir, cache_dir, logs_dir]:
        os.makedirs(folder, exist_ok=True)
        
    # Configure logging
    log_file = os.path.join(logs_dir, "startup.log")
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s"
    )
    logging.info(f"=== Initializing NeuroSeg Pro v{__version__} ===")
    logging.info(f"Application Data Directory: {app_data_dir}")

    # Settings verification and migration
    settings_path = os.path.join(app_data_dir, "settings.json")
    default_settings = {
        "app_version": __version__,
        "theme": "Dark",
        "default_modality": "FLAIR",
        "tumor_opacity": 75,
        "ui_zoom_level": 100,
        "last_opened_folder": "",
        "auto_check_updates": True,
        "created_at": datetime.now().isoformat()
    }
    
    if not os.path.exists(settings_path):
        logging.info("First launch detected: Creating default clinical settings.json...")
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(default_settings, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to write default settings: {e}")
    else:
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                current_settings = json.load(f)
            
            # Migrate legacy version settings if upgrading
            legacy_version = current_settings.get("app_version", "1.0.0")
            if legacy_version != __version__:
                logging.info(f"Migrating user settings from v{legacy_version} to v{__version__}...")
                current_settings["app_version"] = __version__
                # Ensure new keys exist without overwriting user customizations
                for k, v in default_settings.items():
                    if k not in current_settings:
                        current_settings[k] = v
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(current_settings, f, indent=4)
        except Exception as e:
            logging.warning(f"Corrupted settings.json detected ({e}). Resetting to default clinical settings...")
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(default_settings, f, indent=4)

    # Runtime verification
    logging.info("Verifying core scientific runtime libraries...")
    try:
        import torch
        logging.info(f"PyTorch runtime validated: v{torch.__version__} (CUDA available: {torch.cuda.is_available()})")
    except Exception as e:
        logging.error(f"PyTorch verification error: {e}")
        
    logging.info("Initialization completed successfully.")
    return app_data_dir
